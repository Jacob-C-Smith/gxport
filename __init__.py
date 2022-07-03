import bpy
import bmesh
import math
import json 
import sys
import time
import os
from struct import pack
import getpass
from dataclasses import dataclass
from timeit import default_timer as timer
from bpy_extras.io_utils import ExportHelper
from bpy.props import (
    StringProperty,
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    IntProperty,
    FloatProperty,
    CollectionProperty,   
)
from bpy.types import Operator

bl_info = {
    "name": "gxport",
    "description": "Exports Blender scene to G10 scene",
    "author" : "Jacob Smith",
    "version" : (0,1),
    "blender": (3, 0, 0),
    "warning": "This software has not been rigorously tested and may not meet commercial software completeness standards",
    "doc_url": "https://github.com/Jacob-C-Smith/GXPort/",
    "category": "Import-Export",
}

materials: dict = {}

class Light:

    '''
        gxport.Light
    '''

    # Uninitialized data
    name      : str  = None
    location  : list = None
    color     : list = None
    light_type: str  = None

    json_data : dict = None

    # Constructor
    def __init__(self, object: bpy.types.Object):

        '''
            Constructs a gxport.Light from a bpy.types.Object 
        '''

        # Type check
        if isinstance(object.data, bpy.types.Light) == False:
            return

        # Set class data

        # Name
        self.name                  = object.name

        # Location
        self.location = [ None, None, None ]
        self.location[0]           = object.location[0]
        self.location[1]           = object.location[1]
        self.location[2]           = object.location[2]
        
        # Color
        self.color    = [ None, None, None ]
        self.color[0]              = object.data.color[0] * object.data.energy
        self.color[1]              = object.data.color[1] * object.data.energy
        self.color[2]              = object.data.color[2] * object.data.energy
        
        # Set up the dictionary
        self.json_data             = { }
        self.json_data["$schema"]  = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/light-schema.json"
        self.json_data["name"]     = self.name
        self.json_data["location"] = self.location.copy()
        self.json_data["color"]    = self.color.copy()

        return

    # Returns file JSON
    def json(self):

        '''           
            Returns a G10 readable JSON object as a string
        '''

        # Dump the dictionary as a JSON object string
        return json.dumps(self.json_data, indent=4)

    # Writes JSON to a specified file
    def write_to_file(self, path: str):
        
        ''' 
            Write a G10 readable JSON object text to a file path
        '''

        # Write the JSON data to the specified path
        with open(path, "w+") as f:
            try: f.write(self.json())
            except FileExistsError: pass

        return

    @staticmethod
    def import_from_file(path: str):
        
        # Uninitialized data
        light_json    : dict = None

        light_name    : str  = None
        light_location: list = None
        light_color   : list = None
        light_comment : str  = None
        
        # Open the light file from the path
        with open(path, "r") as f:

            # Make a dictionary from the JSON
            light_json = json.load(f)

        # Copy out important properties
        light_name     = light_json['name']
        light_location = light_json['location']
        light_color    = light_json['color']

        # Create a new light
        light_data = bpy.data.lights.new(name=light_name+" data", type='POINT')

        # Create a new object
        light_object = bpy.data.objects.new(name=light_name, object_data=light_data)
        
        # Add the new object to the current scene
        bpy.context.collection.objects.link(light_object)

        # Set the light properties
        light_object.location = light_location

class Camera:

    '''
        - Camera
    '''

    name     : str   = None
    fov      : float = None
    near     : float = None
    far      : float = None
    target   : list  = None
    up       : list  = None
    where    : list  = None

    json_data: dict  = None

    def __init__(self, object: bpy.types.Camera):

        # Type check
        if isinstance(object.data, bpy.types.Camera) == False:
            return

        # Set the name
        self.name                = object.name

        # Set the FOV

        # Make a temporary variable for the unit type
        tmp                       = object.data.lens_unit

        object.data.lens_unit     = 'FOV'
        self.fov                  = object.data.lens

        # Restore the correct unit from the temp
        object.data.lens_unit     = tmp

        # Set the near clip
        self.near                 = object.data.clip_start

        # Set the far clip
        self.far                  = object.data.clip_end

        # Set the target
        self.target               = [ None, None, None ]
        self.target[0]            = object.matrix_world[0][2] * -1
        self.target[1]            = object.matrix_world[1][2] * -1
        self.target[2]            = object.matrix_world[2][2] * -1

        # Set the up 
        self.up                   = [ None, None, None ]
        self.up[0]                = object.matrix_world[0][1]
        self.up[1]                = object.matrix_world[1][1]
        self.up[2]                = object.matrix_world[2][1]

        # Set the location
        self.where                = [ None, None, None ]
        self.where[0]             = object.matrix_world[0][3]
        self.where[1]             = object.matrix_world[1][3]
        self.where[2]             = object.matrix_world[2][3]

        # Set up the dictionary
        self.json_data            = { }
        self.json_data["$schema"] = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/camera-schema.json"
        self.json_data["name"]    = self.name
        self.json_data["fov"]     = self.fov
        self.json_data["near"]    = self.near
        self.json_data["far"]     = self.far
        self.json_data["target"]  = (self.target.copy())
        self.json_data["up"]      = (self.up.copy())
        self.json_data["where"]   = (self.where.copy())

        return

    def json(self):

        return json.dumps(self.json_data, indent=4)

    # Writes JSON to a specified file
    def write_to_file(self, path: str):
        
        ''' 
            Write a G10 readable JSON object text to a file path
        '''

        with open(path, "w+") as f:
            try: f.write(self.json())
            except FileExistsError: pass

        return

class Part:

    '''
        Part
    '''

    name       : str            = None
 
    json_data  : dict           = None
    mesh       : bpy.types.Mesh = None
    path       : str            = None
    ply_path   : str            = None
    shader_name: str            = "G10/shaders/G10 PBR.json"

    # Constructor
    def __init__(self, object: bpy.types.Object):

        # Type check
        if isinstance(object.data, bpy.types.Mesh) == False:
            return

        # Set class data
        self.material_name = object.material_slots[0].name
        
        # Name
        self.name                  = object.name

        # Blender mesh
        self.mesh = object

        # Set up the dictionary
        self.json_data             = { }
        self.json_data["$schema"]  = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/part-schema.json"
        self.json_data["name"]     = self.name
        self.json_data["shader"]   = self.shader_name
        self.json_data["material"] = self.material_name

        return

    # Returns file JSON
    def json(self):

        self.json_data['path'] = self.ply_path

        return json.dumps(self.json_data, indent=4)

    # Writes JSON to a specified file
    def write_to_file(self, path: str):

        self.json_data["path"] = self.ply_path

        # Write the JSON data to the specified path
        with open(path, "w+") as f:
            try: f.write(self.json())
            except FileExistsError: pass

    # PLY exporter 
    def export_ply ( self, file_path, comment="Written from gxport" ):

        # Convinience 
        active_uv_layer         = self.mesh.data.uv_layers.active.data
        active_col_layer        = None
        bone_groups_and_weights = None
        bone_groups             = None
        bone_weights            = None

        use_geometry    : bool  = True
        use_uv_coords   : bool  = True
        use_normals     : bool  = True
        use_tangents    : bool  = False 
        use_bitangents  : bool  = False
        use_colors      : bool  = False
        use_bone_groups : bool  = False
        use_bone_weights: bool  = False

        if use_colors is True:
            active_col_layer = self.mesh.vertex_colors.active.data

        # Make a new bmesh from the parameter
        bm = bmesh.new()
        bm.from_mesh(self.mesh.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])

        # Buffer lookup tables
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()

        # Dict for vertices and faces
        vertices = { }

        vertex_counter = 0

        faces   = { }

        if use_bone_groups is True or use_bone_weights is True:
            bone_groups_and_weights = self.get_bone_groups_and_weights()
            bone_groups  = bone_groups_and_weights[0]
            bone_weights = bone_groups_and_weights[1]


        # Iterate over all faces (faces are triangulated)
        for i, f in enumerate(bm.faces):

            # Face vertex attributes
            t             = [ None, None, None ]
            b             = [ None, None, None ]

            # Face indicies
            face_indicies = [ 0, 0, 0 ]

            # Compute the tangent and bitangent of the face        
            if use_tangents is True or use_bitangents is True:

                # < x, y, z > coordinates for each vertex in the face
                pos1                = (f.verts[0].co)
                pos2                = (f.verts[1].co)
                pos3                = (f.verts[2].co)    

                # < s, t > coordinates for each vertex
                uv1                 = active_uv_layer[f.loops[0].index].uv
                uv2                 = active_uv_layer[f.loops[1].index].uv
                uv3                 = active_uv_layer[f.loops[2].index].uv

                # Compute the edges 
                edge1               = pos2 - pos1
                edge2               = pos3 - pos1

                # Compute the difference in UVs
                delta1              = uv2 - uv1
                delta2              = uv3 - uv1

                # Compute the inverse determinant
                inverse_determinant = float(1) / float(delta1[0] * delta2[1] - delta2[0] * delta1[1])

                # Finally, construct the < tx, ty, tz > and < bx, by, bz > vectors
                t = [
                    inverse_determinant * float( delta2[1] * edge1[0] - delta1[1] * edge2[0] ),
                    inverse_determinant * float( delta2[1] * edge1[1] - delta1[1] * edge2[1] ),
                    inverse_determinant * float( delta2[1] * edge1[2] - delta1[1] * edge2[2] )
                ]

                b = [
                    inverse_determinant * float( -delta2[0] * edge1[0] + delta1[0] * edge2[0] ),
                    inverse_determinant * float( -delta2[0] * edge1[1] + delta1[0] * edge2[1] ),
                    inverse_determinant * float( -delta2[0] * edge1[2] + delta1[0] * edge2[2] )
                ]

            # Iterate over each vertex in the face
            for j, v in enumerate(f.verts):

                # Vertex attributes
                g  = [ None, None, None ]       # < x, y, z >
                uv = [ None, None ]             # < s, t >
                n  = [ None, None, None ]       # < nx, ny, nz >
                c  = [ None, None, None, None ] # < r, g, b, a >
                bg = [ None, None, None, None ] # < g0, g1, g2, g3 > 
                bw = [ None, None, None, None ] # < w0, w1, w2, w3 >

                # < x, y, z > of current vert
                if use_geometry is True:
                    g  = f.verts[j].co

                # < s, t > of current vert
                if use_uv_coords is True:
                    uv = active_uv_layer[f.loops[j].index].uv

                # < nx, ny, nz > of current vert
                if use_normals is True:
                    n  = f.verts[j].normal

                # < r, g, b, a >
                if use_colors is True:
                    c  = active_col_layer[f.loops[j].index].color

                # TODO: Bone groups and weights
                if use_bone_groups is True:
                    bg = bone_groups[f.verts[j].index]

                if use_bone_weights is True:
                    bw = bone_weights[f.verts[j].index]              

                # Combine < x, y, z >
                #         < s, t >
                #         < nx, ny, nz >
                #         < tx, ty, tz >
                #         < bx, by, bz >
                #         < r, g, b, a >
                #         < g0, g1, g2, g3 >
                #         < w0, w1, w2, w3 >

                combined_vertex = (
                                    g[0] , g[1] , g[2],         # 0  : < x, y, z >
                                    uv[0], uv[1],               # 3  : < s, t >
                                    n[0] , n[1] , n[2],         # 5  : < nx, ny, nz >
                                    t[0] , t[1] , t[2],         # 8  : < tx, ty, tz >
                                    b[0] , b[1] , b[2],         # 11 : < bx, by, bz >
                                    c[0] , c[1] , c[2] , c[3],  # 14 : < r, g, b, a >
                                    bg[0], bg[1], bg[2], bg[3], # 18 : < g0, g1, g2, g3 >
                                    bw[0], bw[1], bw[2], bw[3], # 22 : < w0, w1, w2, w3 >
                                  )

                index = vertices.get(combined_vertex)

                if index is not None:
                    face_indicies[j] = index
                else:            
                    face_indicies[j] = vertex_counter
                    vertices[combined_vertex] = vertex_counter

                    vertex_counter = vertex_counter + 1

            faces[i] = face_indicies

        with open(file_path, "wb") as file:
            fw = file.write

            fw(b"ply\n")
            fw(b"format binary_little_endian 1.0\n")

            if comment is not None:
                fw(b"comment " + bytes(comment, 'ascii') + b"\n")

            fw(b"element vertex %d\n" % vertex_counter)

            if use_geometry is True:
                fw(
                    b"property float x\n"
                    b"property float y\n"
                    b"property float z\n"
                )
                
            if use_uv_coords is True:
                fw(
                    b"property float s\n"
                    b"property float t\n"
                )
            if use_normals is True:
                fw(
                    b"property float nx\n"
                    b"property float ny\n"
                    b"property float nz\n"
                )
            if use_tangents is True:
                fw(
                    b"property float tx\n"
                    b"property float ty\n"
                    b"property float tz\n"
                )
            if use_bitangents is True:
                fw(
                    b"property float bx\n"
                    b"property float by\n"
                    b"property float bz\n"
                )
            if use_colors is True:
                fw(
                    b"property uchar red\n"
                    b"property uchar green\n"
                    b"property uchar blue\n"
                    b"property uchar alpha\n"
                )
            if use_bone_groups is True:
                fw(
                    b"property uchar b0\n"
                    b"property uchar b1\n"
                    b"property uchar b2\n"
                    b"property uchar b3\n"
                )
            if use_bone_weights is True:
                fw(
                    b"property uchar w0\n"
                    b"property uchar w1\n"
                    b"property uchar w2\n"
                    b"property uchar w3\n"
                )

            fw(b"element face %d\n" % len(faces))
            fw(b"property list uchar uint vertex_indices\n")
            fw(b"end_header\n")

            # Iterate over vertices
            for v in vertices:

                # Write < x, y, z >
                if use_geometry is True:
                    fw(pack("<3f", v[0] , v[1], v[2] ))

                # Write < s, t >
                if use_uv_coords is True:
                    fw(pack("<2f", v[3] , v[4] ))

                # Write < nx, ny, nz >
                if use_normals is True:
                    fw(pack("<3f", v[5] , v[6] , v[7] ))

                # Write < tx, ty, tz >
                if use_tangents is True:
                    fw(pack("<3f", v[8] , v[9] , v[10]))

                # Write < bx, by, bz >
                if use_bitangents is True:
                    fw(pack("<3f", v[11], v[12], v[13]))

                # Write < r, g, b, a >
                if use_colors is True:
                    fw(pack("<4B", v[14], v[15], v[16], v[17]))

                if use_bone_groups is True:
                    fw(pack("<4i", v[18], v[19], v[20], v[21]))


                if use_bone_weights is True:
                    fw(pack("<4f", v[22], v[23], v[24], v[25]))

            # Iterate over faces
            for i, f in enumerate(faces):
                w = "<3I"
                fw(pack("<b", 3))
                lf = faces[f] 
                fw(pack(w, lf[0], lf[1], lf[2]))

        return     

    # This function gives me anxiety 
    def get_bone_groups_and_weights(self, object):

        bone_vertex_indices_and_weights = { }
        bone_group_array  = []
        bone_weight_array = []

        if len(o.vertex_groups) == 0:
            return None

        # Find vertex indices and bone weights for each bone    
        for g in o.vertex_groups:

            # Make a dictionary key for each bone
            bone_vertex_indices_and_weights[g.name] = []

            # And a convenience variable
            working_bone = bone_vertex_indices_and_weights[g.name]

            for v in o.data.vertices:
                for vg in v.groups:
                    if vg.group == g.index:
                        working_bone.append((v.index, vg.weight))

        '''
            bone_vertex_indices_and_weights now looks like
            {
                "bone name" : [ (1, 0.6), (2, 0.4), (3, 0.2), ... ],
                "spine"     : [ (9, 0.2), ... ],
                ...
                "head"      : [ ... , (3302, 0.23), (3303, 0.34), (3304, 0.6) ]
            }
        '''
        # This exporter only writes the 4 most heavily weighted bones to each vertex

        # Iterate over every vert
        for v in o.data.vertices:

            # Keep track of the 4 most heavy weights and their vertex groups
            heaviest_groups  = [ -1, -1, -1, -1 ] 
            heaviest_weights = [ 0, 0, 0, 0 ]

            # Iterate through bones
            for c in bone_vertex_indices_and_weights.keys():
                d = bone_vertex_indices_and_weights[c]

                for i in d:
                    if v.index == i[0]:
                        if i[1] > heaviest_weights[0]:
                            heaviest_groups[0]  = o.vertex_groups[c].index
                            heaviest_weights[0] = i[1]
                        elif i[1] > heaviest_weights[1]:
                            heaviest_groups[1]  = o.vertex_groups[c].index
                            heaviest_weights[1] = i[1]
                        elif i[1] > heaviest_weights[2]:
                            heaviest_groups[2]  = o.vertex_groups[c].index
                            heaviest_weights[2] = i[1]
                        elif i[1] > heaviest_weights[3]:
                            heaviest_groups[3]  = o.vertex_groups[c].index
                            heaviest_weights[3] = i[1]
                        else:
                            None
            bone_group_array.append(heaviest_groups)
            bone_weight_array.append(heaviest_weights)

        return (bone_group_array, bone_weight_array)

    # Writes JSON and ply to a directory 
    def write_to_directory(self, directory: str):

        parts_directory = directory + "/parts/"

        self.ply_path   = (parts_directory + self.name + ".ply")
        self.path       = (parts_directory + self.name + ".json")

        self.export_ply(self.ply_path, "")

        self.write_to_file(self.path)
        
        return

class Texture:
    '''
        - Texture
    '''

    json_data  : dict            = None

    image      : bpy.types.Image = None
    name       : str             = None
    path       : str             = None
    addressing : str             = 'repeat'
    filter_mode: str             = 'linear'
    generated  : bool            = None

    def __init__(self, *args):

        if len(args) > 1 or len(args) < 1:
            pass
        
        self.json_data = { }

        # Texture Image node
        if isinstance(args[0], bpy.types.ShaderNodeTexImage):
            
            if args[0].image is None:
                # TODO: Set missing texture
                print("Missing Texture")
                return
            image = args[0]

            # Set the image name
            self.name  = image.image.name

            # Set the image object
            self.image = image.image

            # Get the filter mode
            if   image.interpolation == 'Linear':
                self.filter_mode = 'linear'
            elif image.interpolation == 'Closest':
                self.filter_mode = 'nearest'

            # Get the addressing mode
            if   image.extension == 'REPEAT':
                self.addressing = 'repeat'
            elif image.extension == 'EXTEND':
                self.addressing = 'clamp edge'
            elif image.extension == 'CLIP':
                self.addressing = 'clamp border'

            self.generated = False

        # Image
        elif isinstance(args[0], bpy.types.Image):
            
            image = args[0]

            # Set the image name
            self.name = image.name
         
            # Set the image object
            self.image = image

            # Default to repeat addressing with linear filtering

            self.generated = True

        self.json_data['$schema']    = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/texture-schema.json"
        self.json_data['name']       = self.name
        
        self.json_data['addressing'] = self.addressing
        self.json_data['filter']     = self.filter_mode
        print("CONSTRUCTING " + self.name)

        return

    # Save texture
    def save_texture(self,  path: str):
        self.path              = path
        self.json_data['path'] = self.path

        if self.image is not None:
            print("SAVING " + self.name)
            self.image.save_render(self.path)

        return
        
    # Returns JSON text of object
    def json(self):
        
        return json.dumps(self.json_data, indent=4)

    # Destructor
    def __del__(self):
        if self.image is not None:
            if self.generated is True:
                print("DELETING " + self.name)
                bpy.data.images.remove(self.image)

        return

class Material:

    '''
        - Material
    '''

    json_data: dict = None

    name:      str  = None

    path:      str  = None

    principled_node: bpy.types.ShaderNodeBsdfPrincipled = None
    node_tree: bpy.types.ShaderNodeTree = None

    albedo_node = None
    rough_node  = None
    metal_node  = None
    normal_node = None
    
    albedo: Texture = None
    rough : Texture = None
    metal : Texture = None
    normal: Texture = None
    ao    : Texture = None
    height: Texture = None

    def __init__(self, material: bpy.types.Material):

         # Set the node tree
        self.node_tree = material.node_tree

        self.name      = material.name

        self.json_data = { }

        # Right now, only principled BSDF is supported
        if self.node_tree.nodes.find('Principled BSDF') != -1:    
            
            self.principled_node = self.node_tree.nodes["Principled BSDF"]
            
            if isinstance(self.principled_node, bpy.types.ShaderNodeBsdfPrincipled) == False:
                print("ERROR NO PRINCIPLED NODE")
                return
        else:
            print("ERROR ONLY SUPPORTS PRINCIPLED BSDF" + material.name)
            return
        
        #################
        # Export albedo #
        #################

        # Set the albedo node
        self.albedo_node = self.principled_node.inputs["Base Color"]

        # Are there links on the node?
        if bool(self.albedo_node.links):

            # This branch is for exporting images
            if isinstance(self.albedo_node.links[0].from_node, bpy.types.ShaderNodeTexImage):
                self.albedo = Texture(self.albedo_node.links[0].from_node)

            # This branch is for baking images
            else:
                print("LINKED TO NODE SETUP")
        
        # If there are no links, make a new 1x1 image with the color in "Base Color"
        else:
            c = self.albedo_node.default_value
            bpy.ops.image.new(name=self.name + " albedo", width=1, height=1, color=(c[0], c[1], c[2], 1.0), alpha=False, generated_type='BLANK', float=True)
            self.albedo = Texture(bpy.data.images[self.name + " albedo"])
        
        ################
        # Export rough #
        ################
        
        # Set the rough node
        self.rough_node = self.principled_node.inputs["Roughness"]

        # Are there any links on the roughness input?
        if bool(self.rough_node.links):

            # Export an image
            if isinstance(self.rough_node.links[0].from_node, bpy.types.ShaderNodeTexImage):
                self.rough = Texture(self.rough_node.links[0].from_node)

            # Bake an image
            else:
                print("LINKED TO NODE SETUP")
        
        # If there are no links, make a new 1x1 image with the color in "Roughness"
        else:
            c = self.rough_node.default_value
            bpy.ops.image.new(name=self.name+" rough", width=1, height=1, color=(c,c,c,1.0), alpha=False, generated_type='BLANK', float=True)
            self.rough = Texture(bpy.data.images[self.name+' rough'])
        
        ################
        # Export metal #
        ################

        # Set the metal node
        self.metal_node = self.principled_node.inputs["Metallic"]

        # Are there any links on the metalness input?
        if bool(self.metal_node.links):

            # Export an image
            if isinstance(self.metal_node.links[0].from_node, bpy.types.ShaderNodeTexImage):
                self.metal = Texture(self.metal_node.links[0].from_node)

            # Bake an image
            else:
                print("LINKED TO NODE SETUP")
        
        # If there are no links, make a new 1x1 image with the color in "Metalness"
        else:
            c = self.metal_node.default_value
            print(self.name+" metal")
            bpy.ops.image.new(name=self.name+" metal", width=1, height=1, color=(c,c,c,1.0), alpha=False, generated_type='BLANK', float=True)
            self.metal = Texture(bpy.data.images[self.name+' metal'])
        
        #################
        # Export normal #
        #################

        # Set the normal node
        self.normal_node = self.principled_node.inputs["Normal"]

        # Are there any links on the normal input?
        if bool(self.normal_node.links):

            # Export an image
            if isinstance(self.normal_node.links[0].from_node, bpy.types.ShaderNodeTexImage):
                self.normal = Texture(self.normal_node.links[0].from_node)

            # Bake an image
            else:
                print("LINKED TO NODE SETUP")
        
        #############
        # Export AO #
        #############
        
        #################
        # Export Height #
        #################
        


        self.json_data['$schema']  = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/material-schema.json"
        self.json_data['name']     = material.name
        self.json_data['textures'] = []

        materials[material.name] = self

        return

    # Bake images
    def bake(self, path: str):

        return

    def bake_albedo(self):
        pass
    def bake_rough(self):
        pass
    def bake_metal(self):
        pass
    def bake_normal(self):
        pass
    def bake_ao(self):
        pass
    def bake_height(self):
        pass

    # Save all textures
    def save_textures(self, directory: str):

        # Construct a texture
        texture_directory: str = directory + "/textures/" + self.name 

        # Make a directory for the textures
        try:    os.mkdir(texture_directory)
        except: pass

        # Save the albedo texture
        if self.albedo is not None:
            self.albedo.save_texture(texture_directory + "/albedo." + "png")

        # Save the roughness texture
        if self.rough is not None:
            self.rough.save_texture(texture_directory + "/rough." + "png")

        # Save the metal texture
        if self.metal is not None:
            self.metal.save_texture(texture_directory + "/metal." + "png")

        # Save the normal texture
        if self.normal is not None:
            self.normal.save_texture(texture_directory + "/normal." + "png")

        # Save the ambient occlusion texture
        if self.ao is not None:
            self.ao.save_texture(texture_directory + "/ao." + "png")

        # Save the height texture
        if self.height is not None:
            self.height.save_texture(texture_directory + "/height." + "png")

        return

    # Save each material texture to a directory
    def save_material(self,  path: str):
        
        self.path              = path
        self.json_data['path'] = self.path
        self.json_data['textures'] = []

        if self.albedo:
            self.json_data['textures'].append(json.loads(self.albedo.json()))
        if self.rough:
            self.json_data['textures'].append(json.loads(self.rough.json()))
        if self.metal:
            self.json_data['textures'].append(json.loads(self.metal.json()))
        if self.normal:
            self.json_data['textures'].append(json.loads(self.normal.json()))
        if self.ao:
            self.json_data['textures'].append(json.loads(self.ao.json()))
        if self.height:
            self.json_data['textures'].append(json.loads(self.height.json()))

        self.write_to_file(self.path)

        return

    def write_to_file(self, path: str):
        
        # Write the JSON data to the specified path
        with open(path, "w+") as f:
            try:
                f.write(self.json())
            except FileExistsError:
                pass

        return

    # Returns JSON text of object
    def json(self):

        return json.dumps(self.json_data, indent=4)

    # Destructor
    def __del__(self):

        # Delete all the textures
        if self.albedo is not None:
            del(self.albedo)

        if self.rough is not None:
            del(self.rough)

        if self.metal is not None:
            del(self.metal)

        if self.normal is not None:
            del(self.normal)

        if self.ao is not None:
            del(self.ao)

        if self.height is not None:
            del(self.height)
        
        return

class LightProbe:

    '''
        - Light Probes
    '''

    json_data: dict = None

    def __init__(self, object: bpy.types.Object):
        self.json_data = { }

        pass

    # Bake a scaled down sphere with an equirectangular UV? Maybe use a cubemap?
    pass

class Transform:
    
    '''
        - Transform
    '''

    # Class data
    location : list = None
    rotation : list = None
    scale    : list = None

    json_data: dict = None
    # Class methods

    # Constructor
    def __init__(self, object: bpy.types.Object):

        self.json_data = { }

        # Location
        self.location = [ None, None, None ]
        self.location[0]             = object.location[0]
        self.location[1]             = object.location[1]
        self.location[2]             = object.location[2]

        # Save the rotation mode
        temp                         = object.rotation_mode

        # Set the rotation mode to quaternion
        object.rotation_mode         = 'QUATERNION'

        # Rotation 
        self.rotation = [ None, None, None, None ]
        self.rotation[0]             = object.rotation_quaternion[0]
        self.rotation[1]             = object.rotation_quaternion[1]
        self.rotation[2]             = object.rotation_quaternion[2]
        self.rotation[3]             = object.rotation_quaternion[3]
        
        # Restore the rotation mode
        object.rotation_mode         = temp

        # Scale
        self.scale = [ None, None, None ]
        self.scale[0]                = object.scale[0]
        self.scale[1]                = object.scale[1]
        self.scale[2]                = object.scale[2]

        # Set up the dictionary
        self.json_data["$schema"]    = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/transform-schema.json"
        self.json_data["location"]   = self.location.copy()
        self.json_data["quaternion"] = self.rotation.copy()
        self.json_data["scale"]      = self.scale.copy()

        return 

    # Returns class as JSON text
    def json(self):
        
        return json.dumps(self.json_data, indent=4)

class Rigidbody:
    
    '''
        - Rigidbody
    '''

    # Class data
    mass     : float = None
    active   : bool  = None

    json_data: dict  = None

    # Class methods

    @staticmethod
    def has_rigidbody(object: bpy.types.Object) -> bool:
        return True if isinstance(object.rigid_body, bpy.types.RigidBodyObject) else False

    def __init__(self, object: bpy.types.Object):
        
        # Exit if there is no rigidbody
        if Rigidbody.has_rigidbody(object) == False:
            return
        
        self.json_data = { }

        # Set class data
        self.mass   = object.rigid_body.mass 
        self.active = object.rigid_body.type 

        # Set up the dictionary
        self.json_data["$schema"] = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/rigidbody-schema.json"
        self.json_data["mass"]    = self.mass
        self.json_data["active"]  = self.active

        return 

    # Returns class as JSON text
    def json(self):
        
        return json.dumps(self.json_data, indent=4)

    def write_to_file(self, path: str):
        
        # Write the JSON data to the specified path
        with open(path, "w+") as f:
            try:
                f.write(self.json())
            except FileExistsError:
                pass

        return

class Collider:
    '''
        - Collider
    '''

    # Class data
    dimensions : list = None
    shape      : str  = None
    convex_hull: str  = None

    json_data  : dict = None

    # Class methods

    # Constructor
    def __init__ (self, object: bpy.types.Object):
        
        # Check for a rigidbody
        if Rigidbody.has_rigidbody(object) == False:
            return

        # Set the shape
        self.shape = object.rigid_body.collision_shape

        # Set the dimensions
        self.dimensions = [ None, None, None ]
        # TODO

        # Set the JSON
        self.json_data               = { }
        self.json_data["$schema"]    = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/collider-schema.json"
        self.json_data["type"]       = self.shape
        self.json_data["dimensions"] = self.dimensions

        # Write the convex hull
        if self.convex_hull is not None:
            self.json_data["convex hull path"] = self.convex_hull
        
        return
    
    def json(self):

        return json.dumps(self.json_data, indent=4)

    def write_to_file(self, path: str):
        
        # Write the JSON data to the specified path
        with open(path, "w+") as f:
            try:
                f.write(self.json())
            except FileExistsError:
                pass

        return

class Entity:
    '''
        - Entity
    '''

    name     : str       = None
    part     : Part      = None
    material : Material  = None
    transform: Transform = None
    rigidbody: Rigidbody = None
    collider : Collider  = None

    json_data: dict      = None

    path     : str       = None

    def __init__(self, object: bpy.types.Object):
        if isinstance(object.data, bpy.types.Mesh) == False:
            return
        
        self.name      = object.name
        self.part      = Part(object)
        self.material  = materials.get(object.material_slots[0].material.name) if materials.get(object.material_slots[0].material.name) is not None else Material(object.material_slots[0].material)
        self.transform = Transform(object)
        self.rigidbody = Rigidbody(object)
        self.collider  = Collider(object)
        self.rig       = Rig(object)

        self.json_data = { }

        self.json_data['$schema']   = 'https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/entity-schema.json'
        self.json_data['name']      = self.name

        if bool(self.part.json_data):
            self.json_data['parts'] = []
            self.json_data['parts'].append(json.loads(self.part.json()))

        if bool(self.material.json_data):
            self.json_data['materials'] = []
            self.json_data['materials'].append(json.loads(self.material.json()))

        self.json_data['shader'] = 'G10/shaders/G10 PBR.json'

        if bool(self.transform.json_data):
            self.json_data['transform'] = json.loads(self.transform.json())

        if bool(self.rigidbody.json_data):
            self.json_data['rigidbody'] = json.loads(self.rigidbody.json())

        if bool(self.collider.json_data):
            self.json_data['collider'] = json.loads(self.collider.json())

        return
    
    def json (self):
        
        return (json.dumps(self.json_data, indent=4))

    def write_to_file(self, path: str):
        
        # Write the JSON data to the specified path
        with open(path, "w+") as f:
            try:
                f.write(self.json())
            except FileExistsError:
                pass

        return

    def write_to_directory(self, directory: str):

        # Set the path to the entity json
        self.path = directory + "/entities/" + self.name + ".json"

        # Directories for exports
        material_dir = directory + "/materials/"
        part_dir     = directory + "/part/"
        collider_dir = directory + "/collider/"

        # Save the textures
        self.material.save_textures(directory)
        
        # Write the material to a directory
        self.material.save_material(material_dir + self.material.name + ".json")
        self.json_data["materials"] = [ self.material.path ]
        
        # Save the part
        self.part.write_to_directory(directory)
        self.json_data["parts"]     = [ self.part.path ]
        
        # Write the entity to a directory
        self.write_to_file(self.path)

        # Clean up
        del self.part
        del self.material

        return

class Skybox:

    '''
        - Skybox
    '''

    json_data: dict            = None
    image:     bpy.types.Image = None
    name :     str             = None

    def __init__ (self, world: bpy.types.World):
        
        # Check if there is a node to grab the equirectangular image from
        if bool(world.node_tree.nodes.find('Environment Texture')) == False:

            # If not, bail
            return

        self.name = world.name

        # Make a copy of the image
        self.json_data                = {}
        self.json_data['$schema']     = 'https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/skybox-schema.json'
        self.json_data['name']        = self.name
        self.json_data['environment'] = ""

        self.image = world.node_tree.nodes['Environment Texture'].image.copy()

        return

    def save_image (self, path: str):
        
        if self.image is not None:

            # Preserve the image rendering type
            tmp = bpy.context.scene.render.image_settings.file_format

            # Set the image type to Radiance HDR
            bpy.context.scene.render.image_settings.file_format = 'HDR'
            
            # Save the image to the specified path
            self.image.save_render(path)

            # Restore the image type
            bpy.context.scene.render.image_settings.file_format = tmp

            self.json_data['environment'] = path
        else:
            print("[GXPort] [Skybox] Failed to export skybox")

        return
    
    def json (self):

        return (json.dumps(self.json_data, indent=4))

    def write_to_file(self, path: str):
        
        # Write the JSON data to the specified path
        with open(path, "w+") as f:

            # Try to write the file
            try:
                f.write(self.json())

            # Exceptions
            except FileExistsError:

                pass

        return

    def __del__ (self):

        # Check if there is an image to remove
        if self.image is not None:

            # Remove the copy made in the constructor
            bpy.data.images.remove(self.image)
        
        return

class Scene:

    '''
        - Scene
    '''


    name         : str           = None
    entities     : list          = None
    cameras      : list          = None
    lights       : list          = None
    light_probes : list          = None

    skybox       : Skybox        = None

    json_data    : dict          = None

    def __init__(self, scene: bpy.types.Scene):

        # Check for the right type
        if isinstance(scene, bpy.types.Scene) == False:
            # TODO: Throw an exception?
            return

        self.name         = scene.name

        self.entities     = []
        self.cameras      = []
        self.lights       = []
        self.light_probes = []
        self.json_data    = { }

        self.json_data["$schema"]      = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/scene-schema.json"
        self.json_data["name"]         = scene.name
        self.json_data["entities"]     = []
        self.json_data["cameras"]      = []
        self.json_data["lights"]       = []
        self.json_data["light probes"] = []
        self.json_data["skybox"]       = {}
        
        # Iterate over each object in the scene
        for object in scene.objects:

            # Construct a light 
            if object.type == 'LIGHT':
                self.lights.append(Light(object))

            # Construct a camera
            elif object.type == 'CAMERA':
                self.cameras.append(Camera(object))

            # Construct an entity
            elif object.type == 'MESH':
                self.entities.append(Entity(object))

            # Construct a light probe 
            elif object.type == 'LIGHT_PROBE':
                self.light_probes.append(LightProbe(object))            

            # Default case
            else:
                print("[gxport] [Scene] Unrecognized object in scene \"" + scene.name + "\"")

        # Construct the skybox
        if isinstance(scene.world, bpy.types.World):
            self.skybox = Skybox(scene.world)
            

        return

    def json(self):

        return json.dumps(self.json_data,indent=4)

    def write_to_directory(self, directory: str):
        
        """
            Writes a scene to a directory, with entities, materials, parts, colliders, and skyboxes.
        """

        # Make scene directories

        # This is where the scene is exported
        try   : os.mkdir(directory)
        except: pass
    
        # This is where convex hulls are exported
        try   : os.mkdir(directory + "/colliders/")
        except: pass
        
        # This is where entities are exported
        try   : os.mkdir(directory + "/entities/")
        except: pass
        
        # This is where materials are exported
        try   : os.mkdir(directory + "/materials/")
        except: pass
        
        # This is where 3D models are exported
        try   : os.mkdir(directory + "/parts/")
        except: pass
        
        # This is where the skybox is exported
        try   : os.mkdir(directory + "/skybox/")
        except: pass
        
        # This is where material textures are exported
        # NOTE: Material textures are written to "textures/[material name]/". 
        try   : os.mkdir(directory + "/textures/")
        except: pass
        
        # Write entities
        if bool(self.entities) == True:

            # Make an entity array in the json object
            self.json_data["entities"] = []

            # Save each entity
            for entity in self.entities:

                # Write the entity and all its data
                entity.write_to_directory(directory)

                # Write the entity path into the entities array
                self.json_data["entities"].append(entity.path)

                # Destruct the entity
                del entity

        # Write cameras
        if bool(self.cameras) == True:

            # Make a camera array in the json object
            self.json_data["cameras"] = []

            # Save each camera
            for camera in self.cameras:

                # Write the camera json object into the cameras array
                self.json_data["cameras"].append(json.loads(camera.json()))

                # Destruct the camera
                del camera

        # Write lights
        if bool(self.lights) == True:

            # Make a light array in the json object
            self.json_data["lights"] = []

            # Save each light
            for light in self.lights:

                # Write the light json object into the lights array
                self.json_data["lights"].append(json.loads(light.json()))

                # Destruct the light
                del light


        # Write light probes
        if bool(self.light_probes) == False:

            # Make a light probe array in the json object
            self.json_data["light probes"] = []

            # Save each light probe
            for light_probe in self.light_probes:

                #self.json_data["light probes"].append(light_probe.json())

                #del light_probe
                pass

        # Write the skybox
        if bool(self.skybox) == True:
            
            # Save the skybox image
            self.skybox.save_image(directory + "/skybox/" + self.skybox.name + ".hdr")

            # Save the skybox json
            self.skybox.write_to_file(directory + "/skybox/" + self.skybox.name + ".json")

            # Make a reference to the skybox json file in the json object
            self.json_data["skybox"]       = directory + "/skybox/" + self.skybox.name + ".json"


        # The path to the scene
        path = directory + "/" + self.name + ".json"

        # Write the JSON data to the path
        with open(path, "w+") as f:
            try:
                f.write(self.json())
            except FileExistsError:
                pass

        return

class Bone:
    '''
        - Bone
    '''

    name        : str  = None

    bone_matrix : list = None
    bone_head   : list = None
    bone_tail   : list = None
    json_data   : dict = None
    
    # Constructor
    def __init__(self, bone: bpy.types.Bone):
        
        self.name        = bone.name
        self.bone_matrix = bone.matrix_local 
        self.bone_head   = [ bone.head_local[0], bone.head_local[1], bone.head_local[2] ]
        self.bone_tail   = [ bone.tail_local[0], bone.tail_local[1], bone.tail_local[2] ]

        self.json_data['name'] = self.name
        self.json_data['head'] = self.bone_head
        self.json_data['tail'] = self.bone_tail

        return

    # Returns file JSON
    def json(self):

        return json.dumps(self.json_data, indent=4)

    # Writes JSON to a specified file
    def write_to_file(self, path: str):
        
        # Write the JSON data to the specified path
        with open(path, "w+") as f:
            try:
                f.write(self.json())
            except FileExistsError:
                pass

        return

class Pose:

    '''
        - Pose
    '''

    name      : str  = None

    json_data : dict = None
    # Constructor
    def __init__(self, object: bpy.types.Object):

        # Type check
        if isinstance(object.data, bpy.types.Light) == False:
            return


        return

    # Returns file JSON
    def json(self):

        return json.dumps(self.json_data, indent=4)

    # Writes JSON to a specified file
    def write_to_file(self, path: str):
        
        # Write the JSON data to the specified path
        with open(path, "w+") as f:
            try:
                f.write(self.json())
            except FileExistsError:
                pass

        return

class Rig:

    '''
        - Rig
    '''

    name       : str  = None

    json_data  : dict = None
    bones             = None
    bones_json : dict = None

    # Constructor
    def __init__(self, object: bpy.types.Object):

        # Type check
        if isinstance(object.data, bpy.types.Armature) == False:
            return

        # Construct a dictionary
        self.json_data = { }

        # Grab a random bone
        b = object.data.bones[0]

        # Find the root bone 
        while b.parents != None:
            b = b.parents[0]

        # Set 'bones' to the root bone
        self.bones = b

        json_data['$schema'] = 'https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/rig-schema.json'

        return

    # Returns file JSON
    def json(self):

        return json.dumps(self.json_data, indent=4)

    def recursive_bone_json(self, ret : dict):
        
        ret = [ ]
        
        b    = Bone(self.bones[0])
        json = b.json()
        
        print(str(json))

        for b_i in self.bones[0].childern:
            pass


        return ret

    # Writes JSON to a specified file
    def write_to_file(self, path: str):
        
        # Write the JSON data to the specified path
        with open(path, "w+") as f:
            try:
                f.write(self.json())
            except FileExistsError:
                pass

        return

class gxport(Operator, ExportHelper):

    """
       GXPort
       TODO: skeletons 
       TODO: animation
       TODO: light probes
    """
    # TODO: Rename before shipping 1.0
    bl_idname = "gxport.export"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label  = "Write G10 scene"
    
    # A few constant tuples used for EnumProperties and dropdowns
    OFFSET_MODES    = (
        ('X+', "X+", "Side by Side to the Left"),
        ('Y+', "Y+", "Side by Side, Downward"),
        ('Z+', "Z+", "Stacked Above"),
        ('X-', "X-", "Side by Side to the Right"),
        ('Y-', "Y-", "Side by Side, Upward"),
        ('Z-', "Z-", "Stacked Below"),
    )
    
    CONTEXT_TABS    = {
        ("General", "General", "General"),
        ("Scene"  , "Scene"  , "Scene"),
        ("Bake"   , "Bake"   , "Bake"),
        ("Mesh"   , "Mesh"   , "Mesh"),
        ("Physics", "Physics", "Physics")
    }
    
    SCENE_OBJECTS   = {
        ("All"         , "All"         , "All"),
        ("Entities"    , "Entities"    , "Entities"),
        ("Cameras"     , "Cameras"     , "Cameras"),
        ("Lights"      , "Lights"      , "Lights"),
        ("Light probes", "Light probes", "Light probes" )
    }

    DEFAULT_SHADERS = {
        ("PBR"         , "Automatic PBR"   , "Auto PBR"),
        ("Forward PBR" , "Forward PBR"     , "Forward PBR"),
        ("Deferred PBR", "Deferred PBR"    , "Deferred PBR"),
        ("Diffuse"     , "Default Phong"   , "Diffuse"),
        ("Textured"    , "Default Textured", "Textured"),
        ("PBR Height"  , "PBR + Height"    , "PBR Height"),
        ("Custom"      , "Custom"          , "Custom")
    }

    IMAGE_FORMATS = {
        ("PNG", "PNG", "PNG"),
        ("JPG", "JPG", "JPG"),
        ("BMP", "BMP", "BMP"),
        ("QOI", "QOI", "QOI")
    }

    # ExportHelper mixin class uses this
    filename_ext = ""
    
    # Properties used in the exporter.
    filter_glob: StringProperty(
        default = "*.json",
        options = {'HIDDEN'},
        maxlen  = 255,  # Max internal buffer length, longer would be clamped.
    )
    
    filepath = StringProperty(
        name        = "File Path", 
        description = "file path", 
        maxlen      =  1024,
        default     =  ""
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    relative_paths: BoolProperty(
        name        = "Relative Paths",
        description = "Use relative file paths",
        default     = True,
    )
    
    # All the exporter tab properties
    context_tab: EnumProperty(
        name        = "Context tab",
        default     = "General",
        items       = CONTEXT_TABS,
        description = "Configure your scene"
    )
    
    # Scene object filter properties
    scene_objects: EnumProperty(
        name        = "Scene objects",
        default     = "All",
        items       = SCENE_OBJECTS,
        description = "Filter by objects"
    )

    # Comment
    comment: StringProperty(
        default = "Created by " + getpass.getuser() 
    )
    
    # Properties for global orientation
    forward_axis: EnumProperty(
        name        =  "Forward",
        default     = 'Y+',
        items       = OFFSET_MODES,
        description = "Global foraward axis"
    )

    up_axis: EnumProperty(
        name        = "Up",
        default     = "Z+",
        items       = OFFSET_MODES,
        description = "Global up axis"
    )

    # Properties for shaders
    shader_option: EnumProperty(
        name        = "",
        default     = "PBR",
        items       = DEFAULT_SHADERS,
        description = "The shader that will be used to draw entities"
    )
    
    shader_path: StringProperty(
        name    = "Path",
        default = "G10/G10 PBR.json"
    )
    
    # Properties for PBR material export
    use_albedo: BoolProperty(
        name        = "Albedo",
        description = "The albedo map is the base color input that defines the diffuse reflectivity of the surface.",
        default     = True
    )
    
    use_normal: BoolProperty(
        name        = "Normal",
        description = "The normal map give your object texture by changing the direction light is reflected off of surfaces.",
        default     = True
    )
    
    use_rough: BoolProperty(
        name        = "Rough",
        description = "The rough map defines how light scatters across the surface.",
        default     = True
    )
    
    use_metal: BoolProperty(
        name        = "Metal",
        description = "The metal map defines where the surface is made of metal.",
        default     = True
    )
    
    use_ao: BoolProperty(
        name        = "Ambient Occlusion",
        description = "The ambient occlusion map creates softer & more realistic global shadows around the edges of objects.",
        default     = True
    )
    
    use_height: BoolProperty(
        name        = "Height",
        description = "Height maps alter the geometry of an object.",
        default     = False
    )
    
    # Vertex group properties
    use_geometric: BoolProperty(
        name        ="< x, y, z >",
        description ="Geometric coordinates.",
        default     =True
    )

    use_uv: BoolProperty(
        name        = "< u, v >",
        description = "Texture coordinates.",
        default     = True
    )

    use_normals: BoolProperty(
        name        = "< nx, ny, nz >",
        description = "Normals",
        default     = True
    )

    use_tangents: BoolProperty(
        name        = "< tx, ty, tz >",
        description = "Tangents",
        default     = False
    )

    use_bitangents: BoolProperty(
        name        = "< bx, by, bz >",
        description = "Bitangents",
        default     = False
    )

    use_color: BoolProperty(
        name        = "< r, g, b, a >",
        description = "Color",
        default     = False
    )

    use_bone_groups: BoolProperty(
        name        = "< b0, b1, b2, b3 >",
        description = "Bone groups",
        default     = False
    )

    use_bone_weights: BoolProperty(
        name        = "< w0, w1, w2, w3 >",
        description = "Bone weights",
        default     = False
    )
    
    # Texture export resolution property
    texture_resolution: IntProperty(
        name    = "",
        default = 2048,
        min     = 1,
        max     = 65535,
        step    = 1,
        subtype = 'PIXEL',
        description = "Texture resolution for baking"
    )

    image_format: EnumProperty(
        name        = "",
        default     = "PNG",
        items       = IMAGE_FORMATS,
        description = "The image format"
    )

    # Lighting probe properties
    light_probe_dim: IntProperty(
        name    = "",
        default = 512,
        min     = 1,
        max     = 2048,
        step    = 1,
        subtype = 'PIXEL'
    )

    # Execute 
    def execute(self, context):

        # Time how long it takes to export the scene
        start = timer()

        state: dict = { }

        # General state
        state['relative paths']         = self.relative_paths
        state['comment']                = self.comment

        # Global orientation
        state['forward axis']           = self.forward_axis
        state['up axis']                = self.up_axis

        # Vertex groups
        state['vertex groups']          = []
        state['vertex groups'].append("xyz"  if self.use_geometric    else None)
        state['vertex groups'].append("uv"   if self.use_uv           else None)
        state['vertex groups'].append("nxyz" if self.use_normals      else None)
        state['vertex groups'].append("txyz" if self.use_tangents     else None)
        state['vertex groups'].append("bxyz" if self.use_bitangents   else None)
        state['vertex groups'].append("rgba" if self.use_color        else None)
        state['vertex groups'].append("bg"   if self.use_bone_groups  else None)
        state['vertex groups'].append("bw"   if self.use_bone_weights else None)
        
        # Material settings
        state['material textures']      = []
        state['material textures'].append("albedo"  if self.use_albedo else None)
        state['material textures'].append("normal"  if self.use_normal else None)
        state['material textures'].append("rough"   if self.use_rough  else None)
        state['material textures'].append("metal"   if self.use_metal  else None)
        state['material textures'].append("ao"      if self.use_ao     else None)
        state['material textures'].append("height"  if self.use_height else None)

        # Shader settings
        state['shader']                 = self.shader_path

        # Bake settings
        state['texture resolution']     = self.texture_resolution
        state['image format']           = self.image_format
        state['light probe resolution'] = self.light_probe_dim

        # Create a scene object
        scene = Scene(bpy.context.scene)

        # Write it to the directory
        scene.write_to_directory(self.filepath)
        
        # Stop the timer
        end=timer()
        seconds = end-start

        # Write the time
        print( "[G10] [Export] Export Finished in " + str(int(seconds/3600)) + "h " + str(int(seconds/60)) + "m " + str(int(seconds%60)) + "s ")

        return {'FINISHED'}
        return {'CANCELLED'}

    # Draw general configuration tab
    
    # Draw export config box
    def draw_export_config(self, context):
        layout = self.layout
        box    = layout.box()
        
        # Export configuration box
        box.label(text="Export options", icon='EXPORT')
        row = box.row()
        row.active = bpy.data.is_saved
        box.prop(self, "relative_paths")
        #box.prop(self, "update_overwrite")
        box.prop(self, "comment")
        return

    # Draw global orientation config box
    def draw_global_orientation_config(self, context):
        layout = self.layout
        box    = layout.box()
        
        # Global orientation box
        box.label(text="Global Orientation", icon='ORIENTATION_GLOBAL') 

        row = box.row()
        row.label(text="Forward Axis:", icon='AXIS_FRONT')
        row = box.row()
        row.prop(self,"forward_axis",expand=True)

        row = box.row()
        row.label(text="Up Axis:", icon='AXIS_TOP')
        row = box.row()
        row.prop(self,"up_axis",expand=True)
        
        return

    def draw_objects_in_scene(self, context):        
        layout = self.layout
        box    = layout.box()

        # Iterate over all selected objects        
        for o in bpy.data.objects:
            if o in bpy.context.selected_objects:                  
                
                # Draw a camera label
                if o.type == 'CAMERA' and (self.scene_objects == 'All' or self.scene_objects == 'Cameras'):
                    row = box.row()
                    row.label(text=str(o.name),icon='CAMERA_DATA')
            
                # Draw a light
                elif o.type == 'LIGHT' and (self.scene_objects == 'All' or self.scene_objects == 'Lights'):
                    row = box.row()
                    row.label(text=str(o.name),icon='LIGHT_DATA')
                
                # Draw a mesh label
                elif o.type == 'MESH' and (self.scene_objects == 'All' or self.scene_objects == 'Entities'):
                    row = box.row()
                    row.label(text=str(o.name),icon='OBJECT_DATA')

                # Draw a lighting probe
                elif o.type == 'LIGHT_PROBE' and (self.scene_objects == 'All' or self.scene_objects == 'Light probes'):
                    row = box.row()
                    row.label(text=str(o.name),icon='OUTLINER_OB_LIGHTPROBE')

    # Draw material and bake tab
    
    # Draw shader options
    def draw_shader_settings(self, context):
        layout = self.layout
        box    = layout.box() 

        box.label(text='Shader', icon='NODE_MATERIAL')

        box.prop(self,"shader_option")
        if   self.shader_option == 'Custom':
            box.prop(self,"shader_path")
        elif self.shader_option == 'PBR':
            self.shader_path = "G10/shaders/G10 PBR.json"
            
            self.use_albedo = True
            self.use_normal = True
            self.use_metal  = True
            self.use_rough  = True
            self.use_ao     = True
            self.use_height = False
        elif self.shader_option == 'Diffuse':
            self.shader_path = "G10/shaders/G10 Phong.json" 
            
            self.use_albedo = True
            self.use_normal = True
            self.use_metal  = True
            self.use_rough  = False
            self.use_ao     = False
            self.use_height = False
        elif self.shader_option == 'Textured':
            self.shader_path = "G10/shaders/G10 Textured.json"     

            self.use_albedo = True
            self.use_normal = False
            self.use_metal  = False
            self.use_rough  = False
            self.use_ao     = False
            self.use_height = False
        box.label(text=str(self.shader_path))

        global glob_shader_path
        glob_shader_path = self.shader_path
        
        return
    
    # Draw the material export options
    def draw_material_settings(self, context):
        layout = self.layout
        box = layout.box()
        
        box.label(text='Material settings', icon='MATERIAL_DATA')
        
        box.prop(self, "use_albedo")
        box.prop(self, "use_normal")
        box.prop(self, "use_rough")
        box.prop(self, "use_metal")
        box.prop(self, "use_ao")
        box.prop(self, "use_height")
        
        return
    
    # Draw the world settings
    def draw_world_settings(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text='World', icon='WORLD')
        return

    # Draw texture resolution box
    def draw_texture_bake_settings(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text='Texture', icon='TEXTURE_DATA')
        box.prop(self, "texture_resolution")
        box.prop(self, "image_format")
        return    
    
    # Draw light probe box
    def draw_light_probe_settings(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text='Light probe dimensions', icon='OUTLINER_OB_LIGHTPROBE')
        box.prop(self, "light_probe_dim")
        
        return
    
    # Draw mesh tab
    
    # Draw vertex group settings
    def draw_mesh_settings(self, context):
        layout = self.layout
        box    = layout.box()
        box.label(text='Vertex groups', icon='GROUP_VERTEX')
        
        box.prop(self,"use_geometric")

        box.prop(self,"use_uv")

        box.prop(self,"use_normals")
        
        box.prop(self,"use_tangents")
    
        box.prop(self,"use_bitangents")
    
        box.prop(self,"use_color")

        box.prop(self,"use_bone_groups")

        box.prop(self,"use_bone_weights")    

        return
    
    def draw_rig_settings(self, context):
        layout = self.layout
        box    = layout.box()
        box.label(text='Rig', icon='ARMATURE_DATA')
        
        return
    
    def draw_collision_config(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text='Collision', icon='SELECT_INTERSECT')
        for o in bpy.data.objects:
            if o in bpy.context.selected_objects:                  
                if o.type == 'MESH':
                    if o.rigid_body is not None:
                        if o.rigid_body.type == 'ACTIVE':
                            if o.rigid_body.collision_shape == 'CONVEX_HULL':
                                row = box.row()
                                row.label(text=str(o.name),icon='MESH_ICOSPHERE')
                            elif o.rigid_body.collision_shape == 'BOX':
                                row = box.row()
                                row.label(text=str(o.name),icon='MESH_CUBE')
                            elif o.rigid_body.collision_shape == 'SPHERE':
                                row = box.row()
                                row.label(text=str(o.name),icon='MESH_UVSPHERE')
                            elif o.rigid_body.collision_shape == 'CAPSULE':
                                row = box.row()
                                row.label(text=str(o.name),icon='MESH_CAPSULE')
                            elif o.rigid_body.collision_shape == 'CYLINDER':
                                row = box.row()
                                row.label(text=str(o.name),icon='MESH_CYLINDER')
                            elif o.rigid_body.collision_shape == 'BOX':
                                row = box.row()
                                row.label(text=str(o.name),icon='MESH_CUBE')
                            elif o.rigid_body.collision_shape == 'CONE':
                                row = box.row()
                                row.label(text=str(o.name),icon='MESH_CONE')
                        else:
                            row = box.row()
                            row.label(text=str(o.name),icon='GHOST_ENABLED')    
                    else:
                        row = box.row()
                        row.label(text=str(o.name),icon='GHOST_DISABLED')
    
    # Draw everything
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "context_tab",expand=True)
    
        if self.context_tab == 'Scene':
            self.layout.prop(self, "scene_objects", expand=True)
            self.draw_objects_in_scene(context)
        if self.context_tab == 'General':
            self.draw_export_config(context)        
            self.draw_global_orientation_config(context)
        if self.context_tab == 'Bake':
            self.draw_shader_settings(context)
            self.draw_material_settings(context)
            self.draw_texture_bake_settings(context)
            self.draw_light_probe_settings(context)
            self.draw_world_settings(context)
        if self.context_tab == 'Mesh':
            self.draw_mesh_settings(context)
            self.draw_rig_settings(context)
        if self.context_tab == 'Physics':
            self.draw_collision_config(context)
        
        return 
        
# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(gxport.bl_idname, text="Export G10 Scene (.json)")

def register():
    bpy.utils.register_class(gxport)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(gxport)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    
if __name__ == "__main__":
    register()
    
    # test call
    # TODO: Remove before shipping version 1.0
    bpy.ops.gxport.export('INVOKE_DEFAULT')
    