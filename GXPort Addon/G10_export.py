
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