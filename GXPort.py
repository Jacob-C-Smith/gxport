import bpy

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
    FloatProperty,
    CollectionProperty,   
)
from bpy.types import Operator


class ExportSomeData(Operator, ExportHelper):
    """
       GXPort will export lights, cameras, and meshes from a blend file to a G10 directory. Lights
       and cameras will be exported as explicit text in scene.json, whereas meshes will be exported
       into files referenced by path in scene.json. Entities will export PBR materials, rigidbodies, 
       collision detection, skeletons, animation, etc. Props are static objects for which lighting
       is precalculated. *As a rule of thumb, anything that won't move is probably a prop*.  
    """
    bl_idname = "export_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export G10 Data"

    # ExportHelper mixin class uses this
    filename_ext = ".txt"
    
    filter_glob: StringProperty(
        default="*.txt",
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
        ("Bake","Bake options","Bake")
    }
    
    SCENE_OBJECTS = {
        ("All","All","All"),
        ("Entities","Entities","Entities"),
        ("Cameras","Cameras","Cameras"),
        ("Lights","Lights","Lights"),
        ("Props","Props","Props")
    }

    MATERIAL_TYPES = {
        ("PBR","PBR","PBR"),
        ("Prop","Prop","Prop"),
    }

    # All the exporter tab properties
    context_tab: EnumProperty(
        name="Context tab", default="General", items = CONTEXT_TABS,
        description="Configure your scene"
    )
    
    # Scene object filter properties
    scene_objects: EnumProperty(
        name="Scene objects", default="All",items=SCENE_OBJECTS,
        description="Filter by objects"
    )
    
    # Propertiy for material types

    material_types: EnumProperty(
        name="Material types", default='PBR',items=MATERIAL_TYPES,
        description='Material types'
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
     

    # Execute
    def execute(self, context):
        return write_some_data(context, self.filepath, self.use_setting)
    
    # Draw export config box
    def draw_export_config(self, context):
        layout = self.layout
        box    = layout.box()
        
        box.label(text="Export Paths:", icon='EXPORT')
        row = box.row()
        row.active = bpy.data.is_saved
        box.prop(self, "relative_paths")
        
        #box.prop(self, "")
        return

    # Draw global orientation ocnfig box
    def draw_global_orientation_config(self, context):
        layout = self.layout
        box    = layout.box()
        
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
        layout.label(text="Preview selected items to be exported.")
        box = layout.box()
        for o in bpy.data.objects:
            if o in bpy.context.selected_objects:                  
                
                # Draw a camera label
                if o.type == 'CAMERA' and (self.scene_objects == 'All' or self.scene_objects == 'Cameras'):
                    row = box.row()
                    row.label(text=str(o.name),icon='CAMERA_DATA')
                    
                # Draw a mesh label
                elif o.type == 'MESH':
                    # Not a prop
                    prop = False
                    
                    # Test if the prop is in the prop collection
                    if o.name in bpy.data.collections['Props'].all_objects:
                        # TODO: Make boxes with collection names as labels and populate with selected objects
                        prop = True
                        print(o.name + " is a Prop")
                    print(o.name + str(prop) + "PROP")
                    # We are displaying all mesehs
                    if self.scene_objects == 'All':
                        if prop == True:
                            row = box.row()
                            row.label(text=str(o.name),icon='OUTLINER_OB_MESH')
                        else:
                            row = box.row()
                            row.label(text=str(o.name),icon='OBJECT_DATA')
                    # We are displaying props only
                    elif self.scene_objects == 'Entities':
                        if prop == False:
                            row = box.row()
                            row.label(text=str(o.name),icon='OBJECT_DATA',color='red')
                        
                    # We are displaying entities only
                    elif self.scene_objects == 'Props':
                        if prop == True:
                            row = box.row()
                            row.label(text=str(o.name),icon='OUTLINER_OB_MESH')                            
                
                # Draw a light
                elif o.type == 'LIGHT' and (self.scene_objects == 'All' or self.scene_objects == 'Lights'):
                    row = box.row()
                    row.label(text=str(o.name),icon='LIGHT_DATA')
        
        
        
    def draw_material_settings(self, context):
        layout = self.layout
        box = layout.box()
        
        box.label(text='Material settings', icon='MATERIAL_DATA')
        box.prop(self, "material_types", expand=True)
        box.prop(self, "use_albedo")

        box.prop(self, "use_normal")

        box.prop(self, "use_rough")

        box.prop(self, "use_metal")

        box.prop(self, "use_ao")
        return
    
    def draw_texture_bake_settings(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text='Texture baking', icon='TEXTURE_DATA')
        
        return    
    
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
            self.draw_material_settings(context)
            self.draw_texture_bake_settings(context)
        return 
    
# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportSomeData.bl_idname, text="Text Export Operator")


def register():
    bpy.utils.register_class(ExportSomeData)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ExportSomeData)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    

if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_test.some_data('INVOKE_DEFAULT')
