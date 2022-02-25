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

# Export to blend file location
basedir            = None

# Working directoriy, asset directories
sceneName          = None
glob_comment       = None

wd                 = None
wdrel              = None

materialwd         = None
materialwdrel      = None

texturewd          = None
texturewdrel       = None

partswd            = None
partswdrel         = None

entitieswd         = None
entitieswdrel      = None

glob_shader_path   = "G10/shaders/G10 PBR.json"

# Material bake
glob_use_albedo    = True
glob_use_normal    = True
glob_use_rough     = True
glob_use_metal     = True
glob_use_ao        = True
glob_use_height    = True

# Texture bake resolution
glob_texture_dim   = 2048

# Vertex groups
glob_use_geometry  = True
glob_use_uv        = True
glob_use_normal    = True
glob_use_bitangent = False
glob_use_tangent   = False
glob_use_color     = False
glob_use_bgroups   = False
glob_use_bweights  = False

# Set up a couple of variables
view_layer         = None
obj_active         = None
selection          = None

# TODO: This function will write the scene.json file
def write_some_data(context, filepath, use_some_setting):
    f = open(filepath, 'w')
    f.write("")
    f.close()
    return 

# Get Export Helper, Properties, Operator
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

def sceneAsJSON(scene):
    
    # TODO: 
    ret = {
        "name"     : bpy.context.scene.name
    }
    
    print("[G10] [Export] [Scene] Exporting scene " + str(bpy.context.scene.name))
    
    global glob_comment
    
    # Add comment
    if glob_comment is not None:
        ret["comment"] = glob_comment

    ret["entities"] = []
    ret["cameras"] = []
    ret["lights"] = []
    
    l = []
    for o in scene.objects:
        if o.select_get(): 
            l.append(o)  
            o.select_set(False)
    
    for o in l:
        if o.type == 'LIGHT':
            ret["lights"].append(lightAsJSON(o))
        elif o.type == 'CAMERA':
            ret["cameras"].append(cameraAsJSON(o))
               
        elif o.type == 'MESH':
            o.select_set(True)                    
            # TODO: Update to write entity to file, write file path to entities array
            entityPath = entitieswd + "/" + o.name + ".json"
            entityPathRel = entitieswdrel + "/" + o.name + ".json"
            entity = entityAsJSON(o)
            entityText = json.dumps(json.loads(json.dumps(entity), parse_float=lambda x: round(float(x), 3)), indent=4)
                
            with open(entityPath, "w+") as f:
                try:
                    f.write(entityText)
                except:
                    None
            ret["entities"].append(str(entityPathRel))
            o.select_set(False)                    

                
                
    return ret
'''
{
    "name"       : "Tank",
    "parts"      : [
        {
            "name"     : "body",
            "path"     : "Tanks/tanks common/parts/tank body.ply",
            "material" : "Tank body"
        },
        {
            "name"     : "cockpit",
            "path"     : "Tanks/tanks common/parts/tank cockpit.ply",
            "material" : "Tank cockpit"
        },
        {
            "name"     : "gun",
            "path"     : "Tanks/tanks common/parts/tank gun.ply",
            "material" : "Tank gun"
        }
    ],
    "shader"     : "G10/shaders/G10 PBR.json",
    "materials"  : [
        {
            ...
        },
        ... ,
        {
            ...
        }
    ],
    "rigid body" : { ... },
    "transform"  : { ... },
    "collider"   : {
        "shape"      : "plane",
        "dimensions" : [ 2.0, 1.125, 1.3875 ]
    }    
}
'''

def recenterMesh(o):
    exit = False
    iter = 128
    
    while exit == False and iter > 0:
        # TODO: Replace with float min and float max constants
        mx=-sys.float_info.max
        my=-sys.float_info.max
        mz=-sys.float_info.max

        Mx=sys.float_info.max
        My=sys.float_info.max
        Mz=sys.float_info.max
    
        # Find minimum and maximum dimensions
        for v in o.data.vertices:
        
            if v.co[0] > mx:
                mx = v.co[0]
            if v.co[1] > my:
                my = v.co[1]
            if v.co[2] > mz:
                mz = v.co[2]
        
            if v.co[0] < Mx:
                Mx = v.co[0]
            if v.co[1] < My:
                My = v.co[1]
            if v.co[2] < Mz:
                Mz = v.co[2]        
    
        # Calculate a new median point
        medianx = (mx + Mx) / 2
        mediany = (my + My) / 2
        medianz = (mz + Mz) / 2

        if medianx < 0.0001 and medianx > -0.0001 and mediany < 0.0001 and mediany > -0.0001 and medianz < 0.0001 and medianz > -0.0001:
            exit = True 
            

        print(o.name)
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='EDIT')
            
        bpy.ops.transform.translate(value=(-(1/2)*medianx, -(1/2)*mediany, -(1/2)*medianz))
    
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.transform.translate(value=((1/2)*medianx, (1/2)*mediany, (1/2)*medianz))
    
        iter = iter - 1
        

def entityAsJSON(entity):
    
    bpy.context.view_layer.objects.active = entity
    view_layer = entity
    selection  = entity
    
    if entity.type != "MESH":
        return None
    
    # Create the entity json
    ret = {
        "name"      : entity.name,
        "materials" : [],
        "parts"     : []
    }
    
    print("[G10] [Export] [Entity] Exporting entity " + entity.name)
    
    # export parts
    
    # export shader
    ret["shader"] = glob_shader_path
    
    # export transform
    ret["transform"] = transformAsJSON(entity)
    
        
    ret["parts"].append(partAsJSON(entity))
        
    # export rigidbody and collider
    if entity.rigid_body is not None:
        ret["rigid body"] = rigidbodyAsJSON(entity)
        ret["collider"]   = colliderAsJSON(entity)
    

    
    # export materials
    if(len(entity.material_slots)):
        material_path_rel = materialwdrel + "/" 
        
        mJSON = materialAsJSON(entity)
        material_path_rel = material_path_rel + mJSON["name"] + ".json"
        material_path = materialwd + "/" + mJSON["name"] + ".json"
        
        with open(material_path, "w") as f:
            try:
                f.write(json.dumps(mJSON, indent=4))
            except:
                None   
        
        # TODO: Write material to material directory
        if mJSON is not None:
            ret["materials"].append(material_path_rel)
            
    
    return ret

def entityDimensions(o):
    
    Mx=sys.float_info.max
    My=sys.float_info.max
    Mz=sys.float_info.max
    
    # Find minimum and maximum dimensions
    for v in o.data.vertices:
        
        if v.co[0] < Mx:
            Mx = v.co[0]
        if v.co[1] < My:
            My = v.co[1]
        if v.co[2] < Mz:
            Mz = v.co[2]       
    
    # Return dimensions
    return [ abs(Mx), abs(My), abs(Mz) ]


def colliderAsJSON(o):
    
    ret = {
    
    }
    
    if      o.rigid_body.collision_shape == 'BOX':
        ret["type"] = "box"
    elif o.rigid_body.collision_shape == 'SPHERE':
        ret["type"] = "sphere"
    elif o.rigid_body.collision_shape == 'CAPSULE':
        ret["type"] = "capsule"
    elif o.rigid_body.collision_shape == 'CYLINDER':
        ret["type"] = "cylinder"
    elif o.rigid_body.collision_shape == 'CONE':
        ret["type"] = "cone"
    elif o.rigid_body.collision_shape == 'CONVEX_HULL':
        ret["type"] = "convex hull"

    l = [ o.location[0],o.location[1],o.location[2] ]
    r = [ o.rotation_euler[0],o.rotation_euler[1],o.rotation_euler[2] ]
    s = [ o.scale[0], o.scale[1], o.scale[2] ]

    o.location[0]=0
    o.location[1]=0
    o.location[2]=0
    
    o.rotation_euler[0]=0
    o.rotation_euler[1]=0
    o.rotation_euler[2]=0
    
    o.scale[0] = 1
    o.scale[1] = 1
    o.scale[2] = 1

    dim = entityDimensions(o)

    ret["dimensions"] = dim
        
    o.location = l
    o.rotation_euler = r
    o.scale    = s
    
    return ret

#
# Part format
#
# {
#   "name"     : "gun",
#   "path"     : "Tanks/tanks common/parts/tank gun.ply",
#   "material" : "Tank gun"
# }
#
def partAsJSON(o):
    
    lpath = partswd + "/" + o.name + ".ply"
    lpathrel = partswdrel + "/" + o.name + ".ply"

    l = [ o.location[0],o.location[1],o.location[2] ]
    r = [ o.rotation_euler[0],o.rotation_euler[1],o.rotation_euler[2] ]
    s = [ o.scale[0], o.scale[1], o.scale[2] ]

    o.location[0]=0
    o.location[1]=0
    o.location[2]=0
    
    o.rotation_euler[0]=0
    o.rotation_euler[1]=0
    o.rotation_euler[2]=0
    
    o.scale[0] = 1
    o.scale[1] = 1
    o.scale[2] = 1

    bpy.ops.export_mesh.ply(axis_forward='Y', axis_up='Z',filepath=lpath,check_existing=False,use_ascii=False,use_selection=True,use_mesh_modifiers=False, use_colors=False)
    
    o.location = l
    o.rotation_euler = r
    o.scale    = s
    
    # TODO: Replace with new exporter

    ret = {
        "name"     : o.name,
        "path"     : lpathrel,
        "material" : o.name
    }

    return ret


# Transform format: 
# {
#     "location"   : [ 2, 0, 1.25 ],
#     "quaternion" : [ 0.707, 0.707, 0, 0 ] - or - "rotation" : [ 90, 0 , 0 ]
#     "scale"      : [ 1, 1, 1 ]
# }

def transformAsJSON(o):
    
    n = entityDimensions(o)
    
    
    
    ret = {
        "location"  : [ o.location[0], o.location[1], o.location[2] ],
        "quaternion": [ o.rotation_quaternion[0], o.rotation_quaternion[1], o.rotation_quaternion[2], o.rotation_quaternion[3] ],
        "scale"     : [ o.scale[0], o.scale[1], o.scale[2] ]
    }
    return ret

# Rigidbody format:
# {
#        "active"               : true,
#        "mass"                 : 50.0,
#        "friction"             : 0.1
# }
def rigidbodyAsJSON(object):
    if object.rigid_body == None: 
        return None    
    
    active = False if object.rigid_body.type == 'PASSIVE' else True
    
    ret = {
        "active"   : active,
        "mass"     : object.rigid_body.mass,
        "friction" : object.rigid_body.friction
    }
    
    return ret

def cameraAsJSON(camera):
    ret = {
        "name"        : camera.name,
        "fov"         : camera.data.angle * (180/math.pi),
        "near"        : camera.data.clip_start,
        "far"         : camera.data.clip_end
    }
    
    from mathutils import Vector
    targ = camera.matrix_world @ Vector((0,-1,0,1))
    targ.normalize()
    
    ret["target"] = [ camera.location[0]+targ[0], camera.location[1]+targ[1], camera.location[2]+targ[2] ]
    ret["up"]     = [ 0, 0, 1 ],
    ret["where"]  = [ camera.location[0], camera.location[1], camera.location[2] ] 
    return ret

def lightAsJSON(light):
    # Create the light json
    
    loc = light.location
    rgb = light.data.color
    w   = light.data.energy
    ret = {
        "name"     : light.name,
        "location" : [ loc.x, loc.y, loc.z ],
        "color"    : [ rgb[0] * w, rgb[1] * w, rgb[2] * w ] 
    }
    
    return ret

#
# Material format
# {
#     "name"   : "Tank gun",
#     "albedo" : "Tanks/tanks common/textures/tank gun/albedo.png",
#     "normal" : "Tanks/tanks common/textures/tank gun/normal.png",
#     "rough"  : "Tanks/tanks common/textures/tank gun/rough.png",
#     "metal"  : "Tanks/tanks common/textures/tank gun/metal.png",
#     "AO"     : "Tanks/tanks common/textures/tank gun/ao.png"
# }
#
#
#
def materialAsJSON(o):
    
    # Construct a path string
    lpath = texturewd + "\\" + o.name 
    lpathrel = texturewdrel + "/" + o.name

    # Make a directory from the path string for the material
    try:
        os.mkdir(lpath)
    except FileExistsError:
        pass
    # Material JSON
    ret = {
        "name"   : o.name
    }
    
    # Global state variables
    global glob_use_albedo
    global glob_use_normal
    global glob_use_rough
    global glob_use_metal
    global glob_use_ao
    global glob_use_height

    global glob_texture_dim

    # Add the correct tokens to the JSON object
    if glob_use_albedo:
        ret["albedo"] = lpathrel + "/albedo.png"
    
    if glob_use_normal:
        ret["normal"] = lpathrel + "/normal.png"
    
    if glob_use_rough:
        ret["rough"]  = lpathrel + "/rough.png"
        
    if glob_use_metal:
        ret["metal"]  = lpathrel + "/metal.png"
        
    if glob_use_ao:
        ret["ao"]     = lpathrel + "/ao.png"
        
    #if glob_use_height:
    #    ret["height"] = lpathrel + "/height.png"
    
    # Bake the textures
    bakeTextures(o, lpath, glob_texture_dim, glob_use_albedo, glob_use_normal, glob_use_rough, glob_use_metal, glob_use_ao, glob_use_height)

    return ret



def bakeTextures(o, path, resolution, bake_albedo, bake_normal, bake_rough, bake_metal, bake_ao, bake_height):

    image_nodes            = { }
    metal_spec_input_nodes = { }
    
    albedo_image = None
    normal_image = None
    rough_image  = None
    metal_image  = None
    ao_image     = None
    height_image = None
    
    if bake_albedo:
        albedo_image = bpy.data.images.new(o.name + ".albedo", resolution, resolution) if bake_albedo else None
    else:
        albedo_image = None
    
    
    if bake_normal:
        normal_image = bpy.data.images.new(o.name + ".normal", resolution, resolution) if bake_normal else None
    else:
        normal_image = None
        
        
    if bake_rough:
        rough_image  = bpy.data.images.new(o.name + ".rough" , resolution, resolution) if bake_rough  else None
    else:
        rough_image  = None
    
    
    if bake_metal:
        metal_image  = bpy.data.images.new(o.name + ".metal" , resolution, resolution) if bake_metal  else None
    else:
        metal_imge   = None
        
        
    if bake_ao:
        ao_image     = bpy.data.images.new(o.name + ".ao"    , resolution, resolution) if bake_ao     else None
    else:
        ao_image     = None
        
    if bake_height:    
        height_image = bpy.data.images.new(o.name + ".height", resolution, resolution) if bake_height else None
    else:
        height_image = None
    
    for i, s in enumerate(o.material_slots):
        bpy.context.object.active_material_index=i
        material      = s.material
        material_name = str(material.name)
        
        image_nodes[material_name] = [ ]
        
        albedo = None
        normal = None
        rough  = None
        metal  = None
        ao     = None
        height = None
        
        if bake_albedo:
            albedo       = s.material.node_tree.nodes.new('ShaderNodeTexImage')
            albedo.image = albedo_image
            
        image_nodes[material_name].append(("albedo", albedo))
        
        
        if bake_normal:
            normal       = s.material.node_tree.nodes.new('ShaderNodeTexImage')
            normal.image = normal_image
 
        image_nodes[material_name].append(("normal", normal))

        
        if bake_rough:
            rough        = s.material.node_tree.nodes.new('ShaderNodeTexImage')
            rough.image  = rough_image

        image_nodes[material_name].append(("rough", rough))
        
        if bake_metal:
            metal        = s.material.node_tree.nodes.new('ShaderNodeTexImage')
            metal.image  = metal_image

        image_nodes[material_name].append(("metal", metal))
        
        
        if bake_ao:            
            ao           = s.material.node_tree.nodes.new('ShaderNodeTexImage')
            ao.image     = ao_image
            
        image_nodes[material_name].append(("ao", ao))
        
        if bake_height:
            height       = s.material.node_tree.nodes.new('ShaderNodeTexImage')
            height.image = height_image
            
        image_nodes[material_name].append(("height", height))
    
    # Bake the albedo
    if bake_albedo:
        for i, s in enumerate(o.material_slots):
            bpy.context.object.active_material_index = i
            material                 = s.material
            material_name            = str(material.name)
        
            base_color_input         = None
            metal_input              = None
            specular_input           = None
        
            metal_link_to            = None
            specular_link_to         = None
        
            principled               = None
         
            node_tree = material.node_tree
        
            # Deselect all the nodes
            for n in node_tree.nodes:
                n.select = False
        
            
            # Save metal and specular from each node, and set metal and specular to zero
            for n in node_tree.nodes:
                
                # Only for principled shader
                if n.type == 'BSDF_PRINCIPLED':
                    principled       = n
                    base_color_input = n.inputs['Base Color']
                    albedo_to        = None
                
                    metal_node       = n.inputs['Metallic']
                    specular_node    = n.inputs['Specular']
                    albedo_node      = n.inputs['Base Color']
                
                    default_metal    = metal_node.default_value 
                    default_specular = specular_node.default_value
                    default_albedo   = albedo_node.default_value

                    if len(metal_node.links) >= 1:
                        metal_link_to = metal_node.links[0].from_socket
                        node_tree.links.remove(metal_node.links[0])
                
                        
                    if len(specular_node.links) >= 1:
                        specular_link_to = specular_node.links[0].from_socket
                        node_tree.links.remove(specular_node.links[0])
                    
                    metal_node.default_value    = 0.0
                    specular_node.default_value = 0.0

                    material.node_tree.interface_update(bpy.context)
                    material.update_tag(refresh={'TIME'})

                    tp = (metal_link_to, specular_link_to, default_metal, default_specular)

                    metal_spec_input_nodes[material_name] = tp   

        # select all the albedo textures
        for i in image_nodes:
            for j in image_nodes[i]:
                if j[0]=='albedo':
                    j[1].select=True

        # Set up the bake
        albedo_image.colorspace_settings.name = 'sRGB'        
        albedo_image.file_format = 'PNG'
        bpy.context.scene.cycles.bake_type = 'DIFFUSE'
        bpy.context.scene.render.bake_margin = 32
        bpy.ops.object.bake(type='DIFFUSE')
        
        # Save the albedo
        albedo_image.save_render(str(path + "/albedo.png"))



        # Restore specular and metal
        for i, s in enumerate(o.material_slots):
            bpy.context.object.active_material_index = i
            material      = s.material
            material_name = str(material.name)
            node_tree     = material.node_tree
            
            for n in node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    metal_in         = n.inputs['Metallic']
                    specular_in      = n.inputs['Specular']
                        
                        
                    metal_out        = metal_spec_input_nodes[material_name][0]
                    specular_out     = metal_spec_input_nodes[material_name][1]
                
                    default_metal    = metal_spec_input_nodes[material_name][2]
                    default_specular = metal_spec_input_nodes[material_name][3]
                                
                    if metal_out is not None:
                        node_tree.links.new(metal_in, metal_out)
                    
                    if specular_out is not None:
                        node_tree.links.new(specular_in, specular_out)
                
                    metal_in.default_value    = default_metal
                    specular_in.default_value = default_specular

                    material.node_tree.interface_update(bpy.context)
                    material.update_tag(refresh={'TIME'})

    if bake_metal:
        for i in image_nodes:
            for j in image_nodes[i]:
                if j[0]=='metal':
                    print(j)
                    j[1].select=True
        
        albedo_image.colorspace_settings.name = 'Linear'        
        albedo_image.file_format = 'PNG'
 
        bpy.context.scene.render.bake.use_pass_indirect = False
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_color = True

        bpy.ops.object.bake(type='GLOSSY', margin=32, use_clear=True)

        albedo_image.save_render(str(path + "/metal.png"))

    if bake_rough:
        for i in image_nodes:
            for j in image_nodes[i]:
                if j[0]=='rough':
                    print(j)
                    j[1].select=True

        albedo_image.colorspace_settings.name = 'Linear'        
        albedo_image.file_format = 'PNG'

        bpy.ops.object.bake(type='ROUGHNESS', margin=32, use_clear=True)

        albedo_image.save_render(str(path + "/rough.png"))
    
    
    if bake_ao:
        for i in image_nodes:
            for j in image_nodes[i]:
                if j[0]=='ao':
                    j[1].select=True

        albedo_image.colorspace_settings.name = 'Linear'        
        albedo_image.file_format = 'PNG'
    
        bpy.ops.object.bake(type='AO', margin=32, use_clear=True)
        
        albedo_image.save_render(str(path + "/ao.png"))

    if bake_normal:
        for i in image_nodes:
            for j in image_nodes[i]:
                if j[0]=='normal':
                    j[1].select=True

        albedo_image.colorspace_settings.name = 'sRGB'        
        albedo_image.file_format = 'PNG'
        
        multi = False

        for modifier in o.modifiers:
            if modifier.type == "MULTIRES":
                multi = True
            
        if multi == True:
            bpy.context.scene.render.use_bake_multires = True
            bpy.context.scene.render.bake_margin = 32
        

            bpy.ops.object.bake_image()
        else:
            bpy.context.scene.render.use_bake_multires = False
            bpy.context.scene.cycles.bake_type = 'NORMAL'
            bpy.context.scene.render.bake_margin = 32
            
            bpy.ops.object.bake_image()
            
        
        albedo_image.save_render(str(path + "/normal.png"))

        bpy.ops.image.external_edit(filepath=str(path + "/normal.png"))
        bpy.ops.image.invert(invert_r=True)

        albedo_image.save_render(str(path + "/normal.png"))

    # Remove all the image nodes
    for i in image_nodes:
        for j in image_nodes[i]:
            if j[1] is not None:
                if j[1].image is not None:
                    bpy.data.images.remove(j[1].image)
                o.material_slots[i].material.node_tree.nodes.remove(j[1])
 
    
    
    return

def exportPLY (filepath, mesh=bpy.context.selected_objects[0], comment=None, useGeometry=True, useUV=True):
    
    # Vertex groups 
    
    # Flags for vertex groups
    useGeometry       = True
    useUV             = False
    useNormals        = True
    useBitangents     = False
    useColors         = False
    useBoneGroups     = True
    useBoneWeights    = True
    
    # Vertex arrays
    geometry_array    = []
    tuv_array         = []
    uv_array          = []
    normal_array      = []
    bitangent_array   = []
    color_array       = []
    bone_group_array  = []
    bone_weight_array = []
    
    # The UV 
    active_uv         = mesh.data.uv_layers.active.data
    
    # Make a bmesh to access faces, edges, and verts
    bm                = bmesh.new()

    # Point the bmesh to the right mesh
    bm.from_mesh(mesh.data)

    # Buffer faces, edges, and vertices in the array
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    
    # Vertex data
    vertices      = {}
    vertices_count = len(mesh.data.vertices)
    
    if useGeometry == True:
        vertices['xyz']  = []
    
    if useUV == True:
        vertices['st'] = []
    
    if useNormals == True:
        vertices['nxyz'] = []
        
    if useBitangents == True:
        vertices['bxyz'] = []
        
    if useColors == True:
        vertices['rgba'] = []
        
    if useBoneGroups == True:
        vertices['bgroups'] = []
        
    if useBoneWeights == True:
        vertices['bweights'] = []
    
    
    # Face data
    faces_count   = len(mesh.data.polygons)
    faces         = []
    
    # Populate the vertices dictionary
    for v in bm.verts:
        
        if useGeometry == True:
            geometry_array.append(v.co)
        
       
        if useNormals == True:
            normal_array.append(v.normal)
    
    for f in mesh.data.polygons:
         if useUV == True:    
            tuv_array = [
                active_uv[l].uv[:]
                for l in range(f.loop_start, f.loop_start + f.loop_total)
            ]
            print(str(tuv_array))
    
    bone_weights_and_groups = get_bone_groups_and_weights(mesh)
    
    if bone_weights_and_groups is not None:
        bone_group_array = bone_weights_and_groups[0]
        bone_weight_array = bone_weights_and_groups[1]
    else:
        bone_group_array = None
        bone_weight_array = None
        
    #for j, v in enumerate(f.vertices):
    #    uv_array.append((tuv_array[j][0], tuv_array[j][1]))
            
    print(str(uv_array))
    
    if useGeometry == True:
        vertices['xyz'] = geometry_array
        
    if useUV == True:
        vertices['st'] = uv_array
        
    if useNormals == True:
        vertices['nxyz'] = normal_array
    #, uv_array, normal_array, bitangent_array, color_array, bone_group_array, bone_weight_array ) )
    

    vertices['bgroups']  = bone_group_array
    vertices['bweights'] = bone_weight_array
    
    print(str(bone_group_array))
    
    # Populate the faces list
    for f in mesh.data.polygons:
        face = []
        for i in f.vertices:
            face.append(i)
        faces.append(face)
            

    print(str(vertices))

    # Write the PLY file
    with open(filepath, "wb") as file:
        
        # Shorthand for file write
        wr = file.write
        
        # Construct the header
        
        # Signature
        wr(b"ply\n") 
        
        # Format
        wr(b"format binary_little_endian 1.0\n")
        
        if comment is not None:
            
            # Split the comments on newlines
            comments = comment.split('\n')
            
            # Iterate through the split comments, wrting one per line
            for c in comments:
                comment = str("comment " + str(c) + '\n')        
                wr(comment.encode('utf-8'))
        
        
        # Write vertex groups
        wr(b"element vertex %d\n" % vertices_count)
        
        # Geometry
        if useGeometry == True and vertices['xyz'] is not None:
            wr(b"property float x\n")
            wr(b"property float y\n")
            wr(b"property float z\n")
        
        # UV
        if useUV == True and vertices['st'] is not None:
            wr(b"property float s\n")
            wr(b"property float t\n")
        
        # Normals
        if useNormals == True and vertices['nxyz'] is not None:
            wr(b"property float nx\n")
            wr(b"property float ny\n")
            wr(b"property float nz\n")

        # Bitangents
        if useBitangents == True and vertices['bxyz'] is not None:
            wr(b"property float bx\n")
            wr(b"property float by\n")
            wr(b"property float bz\n")

        # Colors
        if useColors == True  and vertices['rgba'] is not None:
            wr(b"property uchar r\n")
            wr(b"property uchar g\n")
            wr(b"property uchar b\n")
            wr(b"property uchar a\n")
            
        # Bone groups
        if useBoneGroups == True and vertices['bgroups'] is not None:
            wr(b"property uint b0\n")
            wr(b"property uint b1\n")
            wr(b"property uint b2\n")
            wr(b"property uint b3\n")
        
        # Bone weights
        if useBoneWeights == True and vertices['bweights'] is not None:
            wr(b"property float w0\n")
            wr(b"property float w1\n")
            wr(b"property float w2\n")
            wr(b"property float w3\n")
        
        # Face list
        wr(b"element face %d\n" % len(mesh.data.polygons))
        
        # Face indices
        wr(b"property list uchar int vertex_indices\n")
        
        # You can continue to add aditional elements here.
        # Not sure what or why yet, but its a possibility
        
        # Done writing the header
        wr(b"end_header\n")
        
        # Start writing vertices
        for i in range(0,vertices_count):

            # Write the geometry data for the vertex on the iterator
            if useGeometry == True:
                g = vertices['xyz'][i]
                wr(pack("<3f", *g))
            
            # Write texture coordinates for the vertex on the iterator
            if useUV == True:
                uv = vertices['st'][i]
                wr(pack("<2f", *uv))
            
            # Write normal vector for the vertex on the iterator
            if useNormals == True:
                n = vertices['nxyz'][i]
                wr(pack("<3f", *n))
            '''
            # Write bitangent vector for the vertex on the iterator                
            if bitangent is not None:
                wr(pack("<3f", *bitangent))
            
            # Write color data  for the vertex on the iterator
            if colors is not None:
                wr(pack("<4B", *colors))
            '''
            # Write bone groups for the vertex on the iterator
            if useBoneGroups == True:
                bg = vertices['bgroups'][i]
                wr(pack("<4i", *bg))
            
            # Write bone weights for the vertex on the iterator
            if useBoneWeights == True:
                bw = vertices['bweights'][i]
                wr(pack("<4f", *bw))
                None
        
        # 

        # Start writing faces
        for face in faces:
            verts_in_face = len(face)
            facew = "<" + str(verts_in_face) + "I"
            wr(pack("<b", verts_in_face))
            wr(pack(facew, *face))


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

#exportPLY(filepath="C:/Users/j/Desktop/test.ply", comment="Written by Jake Smith\n12/8/2021")


    
class GXPort(Operator, ExportHelper):
    """
       GXPort will export lights, cameras, and entities from a blend file to a G10 directory. Lights
       and cameras will be exported as explicit text in scene.json, however meshes will be exported as entities
       into files referenced by relative paths in scene.json. Base color, normal, rough, metal, AO, and height 
       textures are baked and written to material directories. Rigid bodies, collision data, are also exported. 
       TODO: skeletons, 
       TODO: animation,
       
    """
    # TODO: Rename before shipping 1.0
    bl_idname = "gxport.export"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Write G10 scene"
    
    # A few constant tuples used for EnumProperties and dropdowns
    OFFSET_MODES = (
        ('X+', "X+", "Side by Side to the Left"),
        ('Y+', "Y+", "Side by Side, Downward"),
        ('Z+', "Z+", "Stacked Above"),
        ('X-', "X-", "Side by Side to the Right"),
        ('Y-', "Y-", "Side by Side, Upward"),
        ('Z-', "Z-", "Stacked Below"),
    )
    
    CONTEXT_TABS = {
        ("General","General","General"),
        ("Scene","Scene","Scene"),
        ("Bake","Bake","Bake"),
        ("Mesh","Mesh","Mesh"),
        ("Physics","Physics","Physics")
    }
    
    SCENE_OBJECTS = {
        ("All","All","All"),
        ("Entities","Entities","Entities"),
        ("Cameras","Cameras","Cameras"),
        ("Lights","Lights","Lights"),
    }

    DEFAULT_SHADERS = {
        ("PBR", "Default PBR", "PBR"),
        ("Diffuse", "Default Phong", "Diffuse"),
        ("Textured", "Default Textured", "Textured"),
        ("Custom", "Custom", "Custom")
    }

    # ExportHelper mixin class uses this
    filename_ext = ".json"
    

    # Properties used in the exporter.

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )
    
    filepath = StringProperty(
        name="File Path", 
        description="file path", 
        maxlen= 1024,
        default= "")

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    relative_paths: BoolProperty(
        name        ="Relative Paths",
        description ="Use relative file paths",
        default     =True,
    )
    
    update_overwrite: BoolProperty(
        name        = "Overwrite",
        description = "Overwrites the current scene json file to only include what is selected. \nIf this option is deselected, the selected entities will be updated and the scene json file will be unaltered.",
        default     = False
    )

    # All the exporter tab properties
    context_tab: EnumProperty(
        name="Context tab", default="General", items=CONTEXT_TABS,
        description="Configure your scene"
    )
    
    # Scene object filter properties
    scene_objects: EnumProperty(
        name="Scene objects", default="All",items=SCENE_OBJECTS,
        description="Filter by objects"
    )

    # Comment
    comment: StringProperty(
        default="Created by " + getpass.getuser() 
    )
    
    # Properties for global orientation
    forward_axis: EnumProperty(
        name="Forward", default='Y+', items=OFFSET_MODES,
        description="Global foraward axis"
    )

    up_axis: EnumProperty(
        name="Up", default="Z+", items=OFFSET_MODES,
        description="Global up axis"
    )

    # Properties for shaders
    shader_option: EnumProperty(
        name="", default="PBR", items=DEFAULT_SHADERS,
        description="Select a shader for the entities"
    )
    
    shader_path: StringProperty(
        name="Path", default="G10/G10 PBR.json"
    )
    
    # Properties for PBR material export
    use_albedo: BoolProperty(
        name="Albedo",
        description="Use albedo textures",
        default=True
    )
    
    use_normal: BoolProperty(
        name="Normal",
        description="Use normal textures",
        default=True
    )
    
    use_rough: BoolProperty(
        name="Rough",
        description="Use roughness textures",
        default=True
    )
    
    use_metal: BoolProperty(
        name="Metal",
        description="Use metal textures",
        default=True
    )
    
    use_ao: BoolProperty(
        name="AO",
        description="Use AO textures",
        default=True
    )
    
    use_height: BoolProperty(
        name="Height",
        description="Use height maps",
        default=True
    )
    
    # Vertex group properties
    use_geometric: BoolProperty(
        name="Geometric",
        description="Export geometric vertices",
        default=True
    )
    use_uv: BoolProperty(
        name="UV",
        description="Export texture coordinates",
        default=True
    )

    use_normals: BoolProperty(
        name="Normals",
        description="Export vertex normals",
        default=True
    )

    use_bitangents: BoolProperty(
        name="Bitangents",
        description="Export vertex bitangents",
        default=False
    )

    use_color: BoolProperty(
        name="Color",
        description="Export vertex colors",
        default=False
    )

    use_bone_groups: BoolProperty(
        name="Bone groups",
        description="Export vertex bitangents",
        default=False
    )

    use_bone_weights: BoolProperty(
        name="Bone weights",
        description="Export vertex bitangents",
        default=False
    )
    
    # Texture export resolution property
    texture_resolution: IntProperty(
        name="",
        default=2048,
        min=1,
        max=65535,
        step=1,
        subtype='PIXEL'
    )

    # Execute 
    def execute(self, context):
        start = timer()
        
        view_layer = bpy.context.view_layer
        obj_active = view_layer.objects.active
        selection  = bpy.context.selected_objects

        bpy.context.scene.render.engine = "CYCLES"
        bpy.context.view_layer.objects.active = None

        # Export to blend file location
        basedir   = os.path.dirname(self.filepath)

        # Here, we define a working directory to start exporting things in
        sceneName  = bpy.context.scene.name
        wd         = os.path.join(basedir, sceneName)
        wdrel      = sceneName

        global glob_comment        
        
        global glob_use_albedo
        global glob_use_normal
        global glob_use_rough
        global glob_use_metal
        global glob_use_ao
        global glob_use_height

        global glob_texture_dim

        glob_comment    = self.comment
                
        glob_use_albedo = self.use_albedo
        glob_use_normal = self.use_normal
        glob_use_rough  = self.use_rough
        glob_use_metal  = self.use_metal
        glob_use_ao     = self.use_ao
        glob_use_height = self.use_height

        glob_texture_dim = self.texture_resolution      
        
        
        
        # With the working directory in hand, we can start creating directories for materials, textures, etc
        global materialwd
        global materialwdrel
        global texturewd
        global texturewdrel
        global partswd
        global partswdrel
        global entitieswd
        global entitieswdrel
        
        materialwd    = os.path.join(wd, "materials")
        materialwdrel = wdrel + "/materials"
        texturewd     = os.path.join(wd, "textures")
        texturewdrel  = wdrel + "/textures"
        partswd       = os.path.join(wd, "parts")
        partswdrel    = wdrel + "/parts"
        entitieswd    = os.path.join(wd, "entities")
        entitieswdrel = wdrel + "/entities"

        # With how much Blender crashes, especially during computationally intensive tasks, I think this is fair to 
        # Not do anything unless the file is saved. 
        if not basedir:
            raise Exception("Blend file is not saved")

        # Make the working direcrory we defined above, if it doesn't exist
        try:
            os.mkdir(wd)
        except FileExistsError:
            print("[G10] [Export] Directory " + sceneName + " already exists" )

        try:
            os.mkdir(materialwd)
        except FileExistsError:
            print("[G10] [Export] Directory " + sceneName + "/materials" + " already exists" )

        try:
            os.mkdir(texturewd)
        except FileExistsError:
            print("[G10] [Export] Directory " + sceneName + "/textures" + " already exists" )

        try:
            os.mkdir(partswd)
        except FileExistsError:
            print("[G10] [Export] Directory " + sceneName + "/parts"  + " already exists" )

        try:
            os.mkdir(entitieswd)
        except FileExistsError:
            print("[G10] [Export] Directory " + sceneName + "/entities"  + " already exists" )

        # Log the working directories
        print("[G10] [Export] Absolute working  directory : \"" + wd + "\"")
        print("[G10] [Export] Relative working  directory : \"" + wdrel + "\"")
        print("[G10] [Export] Absolute material directory : \"" + materialwd + "\"")
        print("[G10] [Export] Relative working  directory : \"" + materialwdrel + "\"")
        print("[G10] [Export] Absolute textures directory : \"" + texturewd + "\"")
        print("[G10] [Export] Relative working  directory : \"" + texturewdrel + "\"")
        print("[G10] [Export] Absolute parts    directory : \"" + partswd + "\"")
        print("[G10] [Export] Relative working  directory : \"" + partswdrel + "\"")
        print("[G10] [Export] Absolute entities directory : \"" + entitieswd + "\"")
        print("[G10] [Export] Relative working  directory : \"" + entitieswdrel + "\"")
                
        # Generate the JSON token
        sceneJSON = sceneAsJSON(bpy.context.scene)
        
        # Dump the JSON, and load it back, and dump it again to truncate floats.
        sceneText = json.dumps(json.loads(json.dumps(sceneJSON), parse_float=lambda x: round(float(x), 3)), indent=4)

        # Create the path to the JSON file
        scenePath = os.path.join(basedir, sceneName)

        # If we don't have garbage in the sceneText variable, we can probably write it 
        if sceneText is not None:
            print("[G10] [Export] Scene exported successfully. Writing " + sceneName + ".json to \"" + scenePath + "\"")
        else: 
            return {'CANCELLED'}
        

        with open(self.filepath, "w+") as outfile:
            try:
                outfile.write(sceneText)
            except FileExistsError:
                pass
                
        end=timer()
        
        print( "EXPORT FINISHED: TOOK " + str(end-start) + " seconds")

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
        box.prop(self, "update_overwrite")
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
    
    # Draw material and bake tab
    
    # Draw shader options
    def draw_shader_settings(self, context):
        layout = self.layout
        box = layout.box() 
        box.label(text='Shader', icon='NODE_MATERIAL')
        box.prop(self,"shader_option")
        if self.shader_option == 'Custom':
            box.prop(self,"shader_path")
        elif self.shader_option == 'PBR':
            self.shader_path = "G10/shaders/G10 PBR.json"
            
            self.use_albedo = True
            self.use_normal = True
            self.use_metal  = True
            self.use_rough  = True
            self.use_ao     = True
            self.use_height = True
            
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
    

    # Draw texture resolution box
    def draw_texture_bake_settings(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text='Texture dimensions', icon='TEXTURE_DATA')
        box.prop(self, "texture_resolution")
        
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
        if self.context_tab == 'Mesh':
            self.draw_mesh_settings(context)
            self.draw_rig_settings(context)
        if self.context_tab == 'Physics':
            self.draw_collision_config(context)
        
        return 
    
        
# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(GXPort.bl_idname, text="Export G10 Scene (.json)")

def register():
    bpy.utils.register_class(GXPort)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(GXPort)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    
# TODO: Remove before shipping version 1.0
if __name__ == "__main__":
    register()
    
    # test call
    bpy.ops.GXPort.export('INVOKE_DEFAULT')
    