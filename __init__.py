import bpy
import json 
import os
import getpass
from dataclasses import dataclass

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

@dataclass
class GXPortContext:
    albedo           : bool
    normal           : bool
    rough            : bool
    metal            : bool
    ao               : bool
    height           : bool
    relativePaths    : bool
    textureResolution: int
    

# Export to blend file location
basedir   = None

# Working directoriy, asset directories
sceneName     = None

wd            = None
wdrel         = None

materialwd    = None
materialwdrel = None

texturewd     = None
texturewdrel  = None

partswd       = None
partswdrel    = None

entitieswd    = None
entitieswdrel = None

# Set up a couple of variables
view_layer = None
obj_active = None
selection  = None

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
        "name"     : sceneName,
        "comment"  : "",
        "entities" : [
            
        ],
        "cameras"  : [
        
        ],
        "lights"   : [
        
        ]
    }
    
    print("[G10] [Export] [Scene] Exporting scene " + str(bpy.context.scene.name))

    for o in scene.objects:
        if o.select_get():    
            if o.type == 'MESH':
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
            elif o.type == 'LIGHT':
                ret["lights"].append(lightAsJSON(o))
            elif o.type == 'CAMERA':
                ret["cameras"].append(cameraAsJSON(o))
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


def entityAsJSON(entity):
    
    if entity.type != "MESH":
        return {}
    
    # Create the entity json
    ret = {
        "name"      : entity.name,
        "parts"     : [],
        "materials" : []
    }
    
    print("[G10] [Export] [Entity] Exporting entity " + entity.name)
    
    # export parts
    
    # export shader
#    ret["shader"] = GXPortContext.

    # export transform
    ret["transform"] = transformAsJSON(entity)
    
    
    bpy.context.view_layer.objects.active = entity
    view_layer = entity
    selection  = entity
    
    # export materials
    for m in entity.material_slots:
        mJSON = materialAsJSON(m.material)
    
        if mJSON is not None:
            ret["materials"].append(mJSON)
            
    # export rigidbody
    if entity.rigid_body is not None:
        ret["rigid body"] = rigidbodyAsJSON(entity)
    
    
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
def materialAsJSON(material):
    ret = {
        "name" : material.name
    }
    materialName    = material.name
    materialPath    = str(texturewd) + "\\" + str(materialName) + "\\" 
    global texturewdrel
    materialPathRel = texturewdrel + "/" + str(materialName) + "/"
    albedoPath      = materialPathRel + "albedo.png"
    normalPath      = materialPathRel + "normal.png"
    roughPath       = materialPathRel + "rough.png"
    metalPath       = materialPathRel + "metal.png"
    aoPath          = materialPathRel + "ao.png"
    heightPath      = materialPathRel + "height.png"
    
    # Process material
    if material.node_tree.nodes['Principled BSDF'] is not None:
        if material.node_tree.nodes['Principled BSDF'].type == 'BSDF_PRINCIPLED':

            # Convenience variables
            activeMat    = material
            materialName = activeMat.name
            shaderInputs = material.node_tree.nodes['Principled BSDF'].inputs
            shaderNodes  = material.node_tree.nodes
            
            # Define the material and its working directory
            materialPath = str(texturewd) + "/" + str(materialName) + "/" 
            
            # Define paths and objects
            albedo       = material.node_tree.nodes.new('ShaderNodeTexImage')
            normal       = material.node_tree.nodes.new('ShaderNodeTexImage')
            rough        = material.node_tree.nodes.new('ShaderNodeTexImage')
            metal        = material.node_tree.nodes.new('ShaderNodeTexImage')
            ao           = material.node_tree.nodes.new('ShaderNodeTexImage')
        

            # Create a directory for the material textures
            try:
                os.mkdir(os.path.join(texturewd,materialPath))
            except FileExistsError:
                print("[G10] [Export] [Material] Material directory already exists")
            
            # Unset all passes
            bpy.context.scene.render.bake.use_pass_indirect = False
            bpy.context.scene.render.bake.use_pass_direct   = False
            bpy.context.scene.render.bake.use_pass_color    = True
        
            # Process the albedo. If there is a texture plugged into the albedo input, we use that.
            # If not, we bake the albedo and in every case we save the image.
            print("[G10] [Export] [Material] Exporting \"" + materialName + "\" albedo")
        
            # Are there any links from the socket to other nodes?
            if len(shaderInputs['Base Color'].links) != 0:
                # Is the link real?
                if shaderInputs['Base Color'].links[0] is not None:
                    # Is the node linked to a texture image?
                    if shaderInputs['Base Color'].links[0].from_node.type =='TEX_IMAGE':
                        # Is there a texture on the node?
                        if shaderInputs['Base Color'].links[0].from_node.image is not None:
                            albedo.image = shaderInputs['Base Color'].links[0].from_node.image.copy()
                        else:
                            print("[G10] [Export] [Material] No texture connnected to image texture node")   
            else:
                albedo.image = bpy.data.images.new(materialName + ".albedo", 1024, 1024)
                # Process the albedo
                activeMat.node_tree.nodes.active = albedo
                albedo.select                    = True
                
                # Set the bake parameters and bake the albedo texture 
                bpy.context.scene.render.bake.use_pass_color = True
                albedo.image.colorspace_settings.name = 'sRGB'
                albedo.image.file_format = 'PNG'
                albedo.image.filepath = str(os.path.join(texturewd,materialPath))+"/albedo.png"
                albedo.image.save()
                
                try:
                    bpy.ops.object.bake(type='DIFFUSE', width=1024, height=1024, target='IMAGE_TEXTURES')
                except:
                    None            
        
            print("[G10] [Export] [Material] Exporting albedo image to " + albedoPath)
        
            if albedo.image is not None:        
                activeMat.node_tree.nodes.remove(albedo)
                albedo = 1
                
    else:
        print("[G10] [Export] [Material] Material \"" + materialName + "\" has no usable BSDF shader")        
     
    if albedo == 1:
        ret["albedo"] = albedoPath
    if normal.image is not None:
        ret["albedo"] = albedoPath
    if rough.image is not None:
        ret["rough"] = roughPath
    if metal.image is not None:
        ret["metal"] = metalPath
    if ao.image is not None:
        ret["ao"] = aoPath

    return ret

def bakeMaterialTextures(material):
    
    return 0

# Transform format: 
# {
#     "location"   : [ 2, 0, 1.25 ],
#     "quaternion" : [ 0.707, 0.707, 0, 0 ] - or - "rotation" : [ 90, 0 , 0 ]
#     "scale"      : [ 1, 1, 1 ]
# }

def transformAsJSON(object):
    ret = {
        "location"  : [ object.location[0], object.location[1], object.location[2] ],
        "quaternion": [ object.rotation_quaternion[0], object.rotation_quaternion[1], object.rotation_quaternion[2], object.rotation_quaternion[3] ],
        "scale"     : [ object.scale[0], object.scale[1], object.scale[2] ]
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
        "where"       : [ camera.location.x, camera.location.y, camera.location.z ],
        "target"      : [ camera.matrix_world.to_4x4()[0][2], camera.matrix_world.to_4x4()[1][2],camera.matrix_world.to_4x4()[2][2] ],
        "up"          : [ camera.matrix_world.to_4x4()[0][1], camera.matrix_world.to_4x4()[1][1],camera.matrix_world.to_4x4()[2][1] ],
        "fov"         : camera.data.lens,
        "near"        : camera.data.clip_start,
        "far"         : camera.data.clip_end
    }
    
    return ret

def lightAsJSON(light):
    # Create the light json
    
    loc = light.location
    rgb = light.data.color
    
    ret = {
        "name"     : light.name,
        "location" : [ loc.x, loc.y, loc.z ],
        "color"    : [ rgb[0], rgb[1], rgb[2] ] 
    }
    
    return ret
    
class ExportSomeData(Operator, ExportHelper):
    """
       GXPort will export lights, cameras, and meshes from a blend file to a G10 directory. Lights
       and cameras will be exported as explicit text in scene.json, whereas meshes will be exported
       into files referenced by path in scene.json. Entities will export PBR materials, rigid bodies, 
       collision detection, skeletons, animation, etc. Props are static objects for which lighting
       is precalculated. *As a rule of thumb, anything that won't move is probably a prop*.  
    """
    # TODO: Rename before shipping 1.0
    bl_idname = "export_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export G10 Data"
    
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
    

    # Properties used in the exporter. ln. 442 - 582

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

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
        default=1024,
        min=1,
        max=65535,
        step=1,
        subtype='PIXEL'
    )

    # Execute 
    def execute(self, context):

        view_layer = bpy.context.view_layer
        obj_active = view_layer.objects.active
        selection  = bpy.context.selected_objects

        # Export to blend file location
        basedir   = os.path.dirname(bpy.data.filepath)

        # Here, we define a working directory to start exporting things in
        sceneName  = bpy.context.scene.name
        wd         = os.path.join(basedir, sceneName)
        wdrel      = sceneName
        
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
        print("[G10] [Export] Absolute working directory: \"" + wd + "\"")
        print("[G10] [Export] Relative working directory: \"" + wdrel + "\"")
        print("[G10] [Export] Absolute material directory: \"" + materialwd + "\"")
        print("[G10] [Export] Relative working directory: \"" + materialwdrel + "\"")
        print("[G10] [Export] Absolute textures directory: \"" + texturewd + "\"")
        print("[G10] [Export] Relative working directory: \"" + texturewdrel + "\"")
        print("[G10] [Export] Absolute parts directory: \"" + partswd + "\"")
        print("[G10] [Export] Relative working directory: \"" + partswdrel + "\"")
        print("[G10] [Export] Absolute entities directory: \"" + entitieswd + "\"")
        print("[G10] [Export] Relative working directory: \"" + entitieswdrel + "\"")
        
        # Generate the JSON token
        sceneJSON = sceneAsJSON(bpy.context.scene)
        
        # Dump the JSON, and load it back, and dump it again so we can truncate floats.
        sceneText = json.dumps(json.loads(json.dumps(sceneJSON), parse_float=lambda x: round(float(x), 3)), indent=4)

        # Create the path to the JSON file
        scenePath = os.path.join(basedir, sceneName + ".json")

        # If we don't have garbage in the sceneText variable, we can probably write it 
        if sceneText is not None:
            print("[G10] [Export] Scene exported successfully. Writing " + sceneName + ".json to \"" + scenePath + "\"")
        else: 
            return 0
        

        with open(scenePath, "w+") as outfile:
            try:
                outfile.write(sceneText)
            except FileExistsError:
                print("[G10] [Export] Can not export " + sceneName + ".json")

        return 0
    
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
            self.shader_path = "G10/G10 PBR.json"
        elif self.shader_option == 'Diffuse':
            self.shader_path = "G10/G10 Phong.json"
        elif self.shader_option == 'Textured':
            self.shader_path = "G10/G10 Textured.json"     
        box.label(text=str(self.shader_path))
        
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
    self.layout.operator(ExportSomeData.bl_idname, text="Export G10 Scene (.json)")

def register():
    bpy.utils.register_class(ExportSomeData)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ExportSomeData)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    
# TODO: Remove before shipping version 1.0
if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_test.some_data('INVOKE_DEFAULT')
    