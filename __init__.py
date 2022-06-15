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
    "name": "GXPort",
    "description": "Exports Blender scene to G10 scene",
    "author" : "Jacob Smith",
    "version" : (0,1),
    "blender": (3, 0, 0),
    "warning": "This software has not been rigorously tested and may not meet commercial software completeness standards",
    "doc_url": "https://github.com/Jacob-C-Smith/GXPort/",
    "category": "Import-Export",
}

class Light:

    '''
        Light
    '''

    name      : str  = ""
    location  : list = [ None, None, None ]
    color     : list = [ None, None, None ]
    light_type: str  = ""

    json_data : dict = { }

    # Constructor
    def __init__(self, object: bpy.types.Object):

        # Type check
        if isinstance(object.data, bpy.types.Light) == False:
            return

        # Set class data

        # Name
        self.name                  = object.name

        # Location
        self.location[0]           = object.location[0]
        self.location[1]           = object.location[1]
        self.location[2]           = object.location[2]
        
        # Color
        self.color[0]              = object.data.color[0] * object.data.energy
        self.color[1]              = object.data.color[1] * object.data.energy
        self.color[2]              = object.data.color[2] * object.data.energy
        
        # Set up the dictionary
        self.json_data["$schema"]  = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/light-schema.json"
        self.json_data["name"]     = self.name
        self.json_data["location"] = self.location.copy()
        self.json_data["color"]    = self.color.copy()

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

class Camera:

    '''
        - Camera
    '''

    name     : str   = ""
    fov      : float = 0
    near     : float = 0
    far      : float = 0
    target   : list  = [ None, None, None ]
    up       : list  = [ None, None, None ]
    where    : list  = [ None, None, None ]

    json_data: dict  = { }

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
        self.target[0]            = object.matrix_world[0][2] * -1
        self.target[1]            = object.matrix_world[1][2] * -1
        self.target[2]            = object.matrix_world[2][2] * -1

        # Set the up 
        self.up[0]                = object.matrix_world[0][1]
        self.up[1]                = object.matrix_world[1][1]
        self.up[2]                = object.matrix_world[2][1]

        # Set the location
        self.where[0]             = object.matrix_world[0][3]
        self.where[1]             = object.matrix_world[1][3]
        self.where[2]             = object.matrix_world[2][3]

        # Set up the dictionary
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
        
        # Write the JSON data to the specified path
        with open(path, "w+") as f:
            try:
                f.write(self.json())
            except FileExistsError:
                pass

        return

class Part:

    '''
        Part
    '''

    name      : str  = ""

    json_data : dict = { }
    ply_path  : str  = ""
    shader_name:str = "G10/shaders/G10 PBR.json"

    # Constructor
    def __init__(self, object: bpy.types.Object):

        # Type check
        if isinstance(object.data, bpy.types.Mesh) == False:
            return

        # Set class data
        self.material_name = object.material_slots[0].name
        
        # Name
        self.name                  = object.name

        # Set up the dictionary
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

        self.export_ply()

        # Write the JSON data to the specified path
        with open(path, "w+") as f:
            try:
                f.write(self.json())
            except FileExistsError:
                pass

    # PLY exporter 
    def export_ply ( mesh, file_path:str, comment:str=None, use_geometry:bool=True, use_uv_coords:bool=True, use_normals:bool=False, use_tangents:bool=False, use_bitangents:bool=False, use_colors:bool=False, use_bone_groups:bool=False, use_bone_weights:bool=False):

        # Convinience 
        active_uv_layer         = self.mesh.data.uv_layers.active.data
        active_col_layer        = None
        bone_groups_and_weights = None
        bone_groups             = None
        bone_weights            = None

        if use_colors:
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

        if use_bone_groups or use_bone_weights:
            bone_groups_and_weights = get_bone_groups_and_weights(self.mesh)
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
            if use_tangents or use_bitangents:

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
                if use_geometry:
                    g  = f.verts[j].co

                # < s, t > of current vert
                if use_uv_coords:
                    uv = active_uv_layer[f.loops[j].index].uv

                # < nx, ny, nz > of current vert
                if use_normals:
                    n  = f.verts[j].normal

                # < r, g, b, a >
                if use_colors:
                    c  = active_col_layer[f.loops[j].index].color

                # TODO: Bone groups and weights
                if use_bone_groups:
                    bg = bone_groups[f.verts[j].index]

                if use_bone_weights:
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

            if use_geometry:
                fw(
                    b"property float x\n"
                    b"property float y\n"
                    b"property float z\n"
                )
            if use_uv_coords:
                fw(
                    b"property float s\n"
                    b"property float t\n"
                )
            if use_normals:
                fw(
                    b"property float nx\n"
                    b"property float ny\n"
                    b"property float nz\n"
                )
            if use_tangents:
                fw(
                    b"property float tx\n"
                    b"property float ty\n"
                    b"property float tz\n"
                )
            if use_bitangents:
                fw(
                    b"property float bx\n"
                    b"property float by\n"
                    b"property float bz\n"
                )
            if use_colors:
                fw(
                    b"property uchar red\n"
                    b"property uchar green\n"
                    b"property uchar blue\n"
                    b"property uchar alpha\n"
                )
            if use_bone_groups:
                fw(
                    b"property uchar b0\n"
                    b"property uchar b1\n"
                    b"property uchar b2\n"
                    b"property uchar b3\n"
                )
            if use_bone_weights:
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
                if use_geometry:
                    fw(pack("<3f", v[0] , v[1], v[2] ))

                # Write < s, t >
                if use_uv_coords:
                    fw(pack("<2f", v[3] , v[4] ))

                # Write < nx, ny, nz >
                if use_normals:
                    fw(pack("<3f", v[5] , v[6] , v[7] ))

                # Write < tx, ty, tz >
                if use_tangents:
                    fw(pack("<3f", v[8] , v[9] , v[10]))

                # Write < bx, by, bz >
                if use_bitangents:
                    fw(pack("<3f", v[11], v[12], v[13]))

                # Write < r, g, b, a >
                if use_colors:
                    fw(pack("<4B", v[14], v[15], v[16], v[17]))

                if use_bone_groups:
                    fw(pack("<4i", v[18], v[19], v[20], v[21]))


                if use_bone_weights:
                    fw(pack("<4f", v[22], v[23], v[24], v[25]))

            # Iterate over faces
            for i, f in enumerate(faces):
                w = "<3I"
                fw(pack("<b", 3))
                lf = faces[f] 
                fw(pack(w, lf[0], lf[1], lf[2]))

        return     

    # This function gives me anxiety 
    def get_bone_groups_and_weights(o):

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

    pass

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

    def __init__(self, *args):

        if len(args) > 1 or len(args) < 1:
            pass
        
        self.json_data = {}

        # Texture Image node
        if isinstance(args[0], bpy.types.ShaderNodeTexImage):
            
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

        # Image
        elif isinstance(args[0], bpy.types.Image):
            
            image = args[0]

            # Set the image name
            self.name = image.name
         
            # Set the image object
            self.image = image

            # Default to repeat addressing with linear filtering

        self.json_data['$schema']    = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/texture-schema.json"
        self.json_data['name']       = self.name
        
        self.json_data['addressing'] = self.addressing
        self.json_data['filter']     = self.filter_mode

        return

    # Save texture
    def save_texture(self,  path: str):
        self.path              = path
        self.json_data['path'] = self.path

        if self.image is not None:
            self.image.save_render(self.path)

        return
        
    # Returns JSON text of object
    def json(self):
        
        return json.dumps(self.json_data, indent=4)

    # Destructor
    def __del__(self):
        if self.image is not None:
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

        self.json_data = {}

        # Right now, only principled BSDF is supported
        if self.node_tree.nodes.find('Principled BSDF') != -1:    
            
            self.principled_node = self.node_tree.nodes["Principled BSDF"]
            
            if isinstance(self.principled_node, bpy.types.ShaderNodeBsdfPrincipled) == False:
                print("ERROR NO PRINCIPLED NODE")
                return
        else:
            print("ERROR ONLY SUPPORTS PRINCIPLED BSDF" + material.name)
            return
        
        # Set the albedo node
        self.albedo_node = self.principled_node.inputs["Base Color"]

        # Are there links on the node?
        if bool(self.albedo_node.links):
            print("LINKED NODE")

            # This branch is for exporting images
            if isinstance(self.albedo_node.links[0].from_node, bpy.types.ShaderNodeTexImage):
                self.albedo = Texture(self.albedo_node.links[0].from_node)

            # This branch is for baking images
            else:
                print("LINKED TO NODE SETUP")
        
        # If there are no links, make a new 1x1 image with the color in "Base Color"
        else:
            print("SOLID COLOR")

            c = self.albedo_node.default_value
            bpy.ops.image.new(name=self.name+"TEMPORARY_ALBEDO", width=1, height=1, color=(c[0], c[1], c[2], 1.0), alpha=False, generated_type='BLANK', float=True)
            self.albedo = Texture(bpy.data.images[self.name+"TEMPORARY_ALBEDO"])
        
        print(self.albedo.json())

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
            bpy.ops.image.new(name=self.name+"TEMPORARY_ROUGH", width=1, height=1, color=(c,c,c,1.0), alpha=False, generated_type='BLANK', float=True)
            self.rough = Texture(bpy.data.images[self.name+'TEMPORARY_ROUGH'])
        
        print(self.rough.json())

        self.json_data['$schema'] = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/material-schema.json"
        self.json_data['textures'] = []

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

        self.write_to_file(path)

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
            del self.albedo
        if self.rough is not None:
            del self.rough
        if self.metal is not None:
            del self.metal
        if self.normal is not None:
            del self.normal
        if self.ao is not None:
            del self.ao
        if self.height is not None:
            del self.height
        

        return

class LightProbe:

    '''
        - Light Probes
    '''

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
    dimensions : list = [ None, None, None ]
    shape      : str  = ""
    convex_hull: str  = ""

    json_data  : dict = {}

    # Class methods

    # Constructor
    def __init__ (self, object: bpy.types.Object):
        
        if Rigidbody.has_rigidbody(object) == False:
            return

        self.shape = object.rigid_body.collision_shape

        self.json_data["$schema"]    = "https://raw.githubusercontent.com/Jacob-C-Smith/G10-Schema/main/collider-schema.json"
        self.json_data["type"]       = self.shape
        self.json_data["dimensions"] = self.dimensions

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
        self.material  = Material(object.material_slots[0].material)
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
            self.json_data['materials'].append(json.loads(self.part.json()))

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
        self.path = directory + "/entities/" + self.name + ".json"

        # Save the part
        #self.part.write_to_directory(directory)

        # Save the textures
        self.material.save_textures(directory)
        
        # Write the material JSON
        self.material.save_material(directory + "/materials/" + self.name + ".json")

        self.write_to_file(self.path)

        del self.part
        del self.material

        return

class Skybox:

    '''
        - Skybox
    '''

    json_data: dict            = {}
    image:     bpy.types.Image = None
    name :     str             = None

    def __init__ (self, world: bpy.types.World):
        
        # Check if there is a node to grab the equirectangular image from
        if bool(world.node_tree.nodes.find('Environment Texture')) == False:

            # If not, bail
            return

        self.name = world.name

        # Make a copy of the image
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
                light = (Light(object))
                light_json = light.json_data.copy()
                self.json_data["lights"].append(light_json)
                self.lights.append(light)

            # Construct a camera
            elif object.type == 'CAMERA':
                camera = (Camera(object))
                camera_json = camera.json_data.copy()
                self.json_data["cameras"].append(camera_json)
                self.cameras.append(camera)

            # Construct an entity
            elif object.type == 'MESH':
                entity      = (Entity(object))
                entity_json = entity.json_data.copy()
                self.json_data["entities"].append(entity_json)
                self.entities.append(entity)
                pass
            elif object.type == 'LIGHT_PROBE':
                light_probe      = (LightProbe(object))
                light_probe_json = light_probe.json_data.copy()
                self.json_data["light probes"].append(light_probe_json)
                self.light_probes.append(light_probe)            
            # Default case
            else:
                print("[G10] [Export] Unrecognized object")

        # Construct the skybox
        if isinstance(scene.world, bpy.types.World):
            self.skybox = Skybox(scene.world)
            self.json_data["skybox"] = self.skybox.json_data.copy()

        # Get rid of unneccisary keys
        if bool(self.json_data["lights"]) == False:
            self.json_data.pop("lights")

        if bool(self.json_data["cameras"]) == False:
            self.json_data.pop("cameras")

        if bool(self.json_data["entities"]) == False:
            self.json_data.pop("entities")

        if bool(self.json_data["skybox"]) == False:
            self.json_data.pop("skybox")

        if bool(self.json_data["light probes"]) == False:
            self.json_data.pop("light probes")

        return

    def json(self):

        return json.dumps(self.json_data,indent=4)

    def write_to_directory(self, directory: str):
        
        """
            Writes a scene to a directory. 
        """

        # Make scene directories
        try   : os.mkdir(directory)
        except: pass
    
        try   : os.mkdir(directory + "/colliders/")
        except: pass
        
        try   : os.mkdir(directory + "/entities/")
        except: pass
        
        try   : os.mkdir(directory + "/materials/")
        except: pass
        
        try   : os.mkdir(directory + "/parts/")
        except: pass
        
        try   : os.mkdir(directory + "/skybox/")
        except: pass
        
        try   : os.mkdir(directory + "/textures/")
        except: pass
        
        self.json_data["entities"] = []

        # Save each entity
        for entity in self.entities:

            # Write the entity and all its data
            entity.write_to_directory(directory)

            # Add the entity path to the list
            self.json_data["entities"].append(entity.path)

            del entity

        # Save the skybox image
        self.skybox.save_image(directory + "/skybox/" + self.skybox.name + ".hdr")
        self.skybox.write_to_file(directory + "/skybox/" + self.skybox.name + ".json")

        self.json_data["skybox"]       = directory + "/skybox/" + self.skybox.name + ".json"

        path = directory + "/" + self.name + ".json"

        # Write the JSON data to the specified path
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

    name        : str  = ""

    bone_matrix        = None
    bone_head          = None
    bone_tail          = None
    json_data   : dict = { }
    
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

    name      : str  = ""

    json_data : dict = { }

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

    name       : str  = ""

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
        ("PBR"       , "Default PBR"     , "PBR"),
        ("Diffuse"   , "Default Phong"   , "Diffuse"),
        ("Textured"  , "Default Textured", "Textured"),
        ("PBR Height", "PBR + Height"    , "PBR Height"),
        ("Custom"    , "Custom"          , "Custom")
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
        name        = "Shader",
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
        description = "albedo.",
        default     = True
    )
    
    use_normal: BoolProperty(
        name        = "Normal",
        description = "normal",
        default     = True
    )
    
    use_rough: BoolProperty(
        name        = "Rough",
        description = "roughness",
        default     = True
    )
    
    use_metal: BoolProperty(
        name        = "Metal",
        description = "metal",
        default     = True
    )
    
    use_ao: BoolProperty(
        name        = "Ambient Occlusion",
        description = "AO",
        default     = True
    )
    
    use_height: BoolProperty(
        name        = "Height",
        description = "height",
        default     = False
    )
    
    # Vertex group properties
    use_geometric: BoolProperty(
        name        ="Geometric",
        description ="Geometry",
        default     =True
    )

    use_uv: BoolProperty(
        name        = "UV",
        description = "Texture coordinates",
        default     = True
    )

    use_normals: BoolProperty(
        name        = "Normals",
        description = "Normals",
        default     = True
    )

    use_tangents: BoolProperty(
        name        = "Tangents",
        description = "Tangents",
        default     = False
    )

    use_bitangents: BoolProperty(
        name        = "Bitangents",
        description = "Bitangents",
        default     = False
    )

    use_color: BoolProperty(
        name        = "Color",
        description = "vertex colors",
        default     = False
    )

    use_bone_groups: BoolProperty(
        name        = "Bone groups",
        description = "Bone groups",
        default     = False
    )

    use_bone_weights: BoolProperty(
        name        = "Bone weights",
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
        subtype = 'PIXEL'
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

        # Create a scene object
        scene = Scene(bpy.context.scene)

        # Write it to the directory
        scene.write_to_directory(self.filepath)
        
        end=timer()
        seconds = end-start
        print( "[G10] [Export] Export Finished in " + str(int(seconds/3600)) + "h " + str(int(seconds%3600)) + "m " + str(int(seconds%60)) + "s ")


        return {'CANCELLED'}


        return {'FINISHED'}
    
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
    
# TODO: Remove before shipping version 1.0
if __name__ == "__main__":
    register()
    
    # test call
    bpy.ops.gxport.export('INVOKE_DEFAULT')
    