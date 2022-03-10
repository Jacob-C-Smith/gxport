import bpy
import time
import os

def materialAsJSON(o, path, resolution, bake_albedo, bake_normal, bake_rough, bake_metal, bake_ao, bake_height):

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
    
    # 1     Add n image texture nodes for each material where n is the number of textures to bake
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
    
    # 2     Bake albedo
    
    # 2.1   Iterate through each material slot
    for i, s in enumerate(o.material_slots):
        bpy.context.object.active_material_index=i
        material                 = s.material
        material_name            = str(material.name)
        
        base_color_input         = None
        metal_input              = None
        specular_input           = None
        
        metal_link_to            = None
        specular_link_to         = None
        
        principled               = None
         
        node_tree = material.node_tree

        for n in node_tree.nodes:
                n.select = False
        
        for n in node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                principled       = n
                base_color_input = n.inputs['Base Color']

                metal_node       = n.inputs['Metallic']
                specular_node    = n.inputs['Specular']
                
                default_metal    = metal_node.default_value 
                default_specular = specular_node.default_value
                metal_spec_input_nodes
                # 2.1.1 Copy metal and specular input node
                # 2.1.2 Disconnect metal and specular input
                # 2.1.3 Set metal and specular input to 0.0
                
                if len(metal_node.links) >= 1:
                    metal_link_to = metal_node.links[0].from_socket
                    node_tree.links.remove(metal_node.links[0])
                
                        
                if len(specular_node.links) >= 1:
                    specular_link_to = specular_node.links[0].from_socket
                    node_tree.links.remove(specular_node.links[0])
                    
                metal_node.default_value    = 0.0
                specular_node.default_value = 0.0

                material.update_tag(refresh={'TIME'})

                tp = (metal_link_to, specular_link_to, default_metal, default_specular)
 
                metal_spec_input_nodes[material_name] = tp   
    
    # 2.1.4 Select each albedo image node
    for i in image_nodes:
        for j in image_nodes[i]:
            if j[0]=='albedo':
                j[1].select=True
    
    # 2.2   Configure image
    # 2.2.1 Color space = sRGB
    albedo_image.colorspace_settings.name = 'sRGB'        
    albedo_image.file_format = 'PNG'
    
    # 2.3   Bake the texture
    # 2.3.1 Bake type = diffuse
    # 2.3.2 Contributaions = Color
    # 2.3.3 Run the bake operation
    bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'}, margin=32, use_clear=False)
        
    # 2.4   Save the image
    albedo_image.save_render(str(path + "/albedo.png"))
    
    # 2.5   Iterate through each material slot

    for i, s in enumerate(o.material_slots):
        bpy.context.object.active_material_index=i
        material      = s.material
        material_name = str(material.name)
        node_tree     = material.node_tree
        
        for n in node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                # 2.6.1 Reconnect each metal and specular input to their respective node structures
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

                material.update_tag(refresh={'TIME'})
    
                

    # 2.6   Deselect every node
    
    # 3     Bake metal
    # 3.1   Iterate through each material slot
    for i in image_nodes:
        for j in image_nodes[i]:
            # 3.1.1 Select each metal image node
            if j[0]=='metal':
                j[1].select=True
    
    # 3.2   Configure image
    metal_image.colorspace_settings.name = 'Linear'        
    metal_image.file_format = 'PNG'
    
    # 3.2.1 Bake type = glossy
    # 3.2.2 Contributaions = Color
    # 3.    linear
    # 2.3.3 Run the bake operation
    bpy.ops.object.bake(type='GLOSSY',pass_filter={'COLOR'}, margin=32, use_clear=False)
        
    # 2.4   Save the image
    metal_image.save_render(str(path + "/metal.png"))
    
    # 3.2.1 Bake type = glossy
    
    # 3.2.3 Color space = 
    # 3.3   Run the bake operation
    # 3.4   Flip the image vertically
    # 3.5   Save the image
    # 3.6   Deselect every node
    
    # 4     Bake rough
    # 4.1   Iterate through each material slot
    # 4.1.1 Select each metal image node
    # 4.2   Configure image
    # 4.2.1 Bake type = rough
    # 4.2.2 Color space = linear
    # 4.3   Run the bake operation
    # 4.4   Flip the image vertically
    # 4.5   Save the image
    # 4.6   Deselect every node
    
    # 5     Bake AO
    # 5.1   Iterate through each material slot
    # 5.1.1 Select each metal image node
    # 5.2   Configure image
    # 5.2.1 Bake type = ao
    # 5.2.2 Color space = linear
    # 5.3   Run the bake operation
    # 5.4   Flip the image vertically
    # 5.5   Save the image
    # 5.6   Deselect every node

    # 6     Bake normal
    # 6.1   Iterate through each material slot
    # 6.1.1 Select each metal image node
    # 6.2   Configure image
    # 6.2.1 Bake type = (multires) ? multires normal bake : normal bake
    # 6.3   Run the bake operation
    # 6.4   Flip the image vertically
    # 6.5   Invert G channel (R?)
    # 6.6   Save the image
    # 6.7   Deselect every node
  

    '''
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
    
    for s in o.material_slots:
        # Define paths and objects

    
    # Process material
    if material.node_tree.nodes['Principled BSDF'] is not None:
        
        # Is the material output linked to a principled shader?
        if material.node_tree.nodes['Principled BSDF'].type == 'BSDF_PRINCIPLED':

            # Bake out albedo, normal, rough, metal, ao, and height maps selectively


            # Convenience variables
            activeMat    = material
            materialName = activeMat.name
            shaderInputs = material.node_tree.nodes['Principled BSDF'].inputs
            shaderNodes  = material.node_tree.nodes
            
            # Define the material and its working directory
            materialPath = str(texturewd) + "/" + str(materialName) + "/" 
            


            # Create a directory for the material textures
            try:
                os.mkdir(os.path.join(texturewd,materialPath))
            except FileExistsError:
                print("[G10] [Export] [Material] Material directory already exists")
            
            ###################
            # Bake the albedo #
            ###################
            
            # Deselect lighting passes. Albedo is only color data.
            bpy.context.scene.render.bake.use_pass_indirect = False
            bpy.context.scene.render.bake.use_pass_direct   = False
            bpy.context.scene.render.bake.use_pass_color    = True
        
            # Log the material name
            print("[G10] [Export] [Material] Exporting \"" + materialName + "\" albedo")        
        
            # Are there any links from the base color input to other nodes?
            if len(shaderInputs['Base Color'].links) != 0:
                
                # Is the link real?
                if shaderInputs['Base Color'].links[0] is not None:
                    
                    # Is the node linked to a texture image?
                    if shaderInputs['Base Color'].links[0].from_node.type =='TEX_IMAGE':
                        
                        # Is there a texture on the node?
                        if shaderInputs['Base Color'].links[0].from_node.image is not None:

                            # If all these conditions are satisfied, we can copy the image to the albedo node
                            albedo.image = shaderInputs['Base Color'].links[0].from_node.image.copy()
                        
                        # If there isn't one, throw an error
                        else:
                            print("[G10] [Export] [Material] No texture connnected to image texture node")   
            
                # 
                else:
                    albedo.image = bpy.data.images.new(materialName + ".albedo", 1024, 1024)
                    # Process the albedo
                    activeMat.node_tree.nodes.active = albedo
                    albedo.select                    = True
                    
                    # Set the bake parameters and bake the albedo texture 
                    bpy.context.scene.render.bake.use_pass_color = True
                
                    # Albedos are sRGBbbbb

                
                    try:
                        bpy.ops.object.bake(type='DIFFUSE', width=1024, height=1024, target='IMAGE_TEXTURES')
                    except:
                        None            
        
                    print("[G10] [Export] [Material] Exporting albedo image to " + albedoPath)
                        
    else:
        print("[G10] [Export] [Material] Material \"" + materialName + "\" has no usable BSDF shader")        
     
    if albedo.image is not None:
        ret["albedo"] = albedoPath
    if normal.image is not None:
        ret["albedo"] = albedoPath
    if rough.image is not None:
        ret["rough"] = roughPath
    if metal.image is not None:
        ret["metal"] = metalPath
    if ao.image is not None:
        ret["ao"] = aoPath

    for s in o.material_slots:
        s.material.node_tree.nodes.remove(albedo)
        s.material.node_tree.nodes.remove(normal)
        s.material.node_tree.nodes.remove(rough)
        s.material.node_tree.nodes.remove(metal)
        s.material.node_tree.nodes.remove(ao)
        s.material.node_tree.nodes.remove(height)
    
    return ret
    '''
    # 7     Remove every image node from every shader
    for i in image_nodes:
        for j in image_nodes[i]:
            if j[1] is not None:
                if j[1].image is not None:
                    bpy.data.images.remove(j[1].image)
                o.material_slots[i].material.node_tree.nodes.remove(j[1])
 
    
    
    return

materialAsJSON(bpy.data.objects['laptop'],"C:/Users/j/Desktop/laptop/material",4096,True,True,True,True,True,False)
        
