bl_info = {
    "name" : "Empire Earth CEM-tool",
    "author" : "zocker_160",
    "description" : "addon for importing and exporting Empire Earth CEM files",
    "blender" : (2, 91, 2),
    "version" : (0, 23),
    "location" : "File > Import",
    "warning" : "This addon is still WiP and will contain bugs!",
    "category" : "Import-Export",
    "tracker_url": "https://github.com/EE-modders/CEM-tool/issues"
}

import bpy
import importlib

from . import CEMimporter as CEMi
from . import CEMexporter as CEMex

from bpy.props import StringProperty, BoolProperty, EnumProperty
# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper, path_reference_mode


importlib.reload(CEMimporter)

def import_cem(context, filepath: str, bTagPoints: bool, bCleanup: bool, bTransform: bool, bValidate: bool, lod_level: str, frame_num: str):
    print("starting import of", filepath)

    if bCleanup:
        print("CLEANING UP")
        CEMi.cleanup()
    return CEMi.main_function_import_file(filename=filepath, bTagPoints=bTagPoints, bTransform=bTransform, bValidate=bValidate, lod_lvl=int(lod_level), frame_num=int(frame_num))

def export_cem(context, filepath: str):
    print("starting export of", filepath)

    return CEMex.main_function_export_file(filename=filepath)

class ImportCEM(bpy.types.Operator, ImportHelper):
    """Import an Empire Earth (AoC) CEM file"""
    bl_idname = "import_scene.cem"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import CEM"

    # ImportHelper mixin class uses this
    filename_ext = ".cem"

    filter_glob: StringProperty(
        default="*.cem",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    setting_matrix_transform: BoolProperty(
        name="apply transformation matrix",
        description="if enabled, the included transformation matrix will get applied to the objects",
        default=True,
    )
    setting_tag_points: BoolProperty(
        name="import Tag Points",
        description="imports all Tag Points stored in the CEM file",
        default=True,
    )
    setting_validate: BoolProperty(
        name="validate vertex",
        description="lets Blender validate the imported vertex (disabling can fix broken imports)",
        default=True,
    )

    setting_cleanup: BoolProperty(
        name="clean whole scene (!)",
        description="removes all objects and collections before import",
        default=False,
    )

    lod_lvl: EnumProperty(
        name="LOD Level",
        description="select LOD level [1-10] with 1: highest poly; 10: lowest poly",
        items=(
            ('0', "1 (default)", "LOD level 1 (default)"),
            ('1', "2", "LOD level 2"),
            ('2', "3", "LOD level 3"),
            ('3', "4", "LOD level 4"),
            ('4', "5", "LOD level 5"),
            ('5', "6", "LOD level 6"),
            ('6', "7", "LOD level 7"),
            ('7', "8", "LOD level 8"),
            ('8', "9", "LOD level 9"),
            ('9', "10", "LOD level 10"),
        ),
        default='0',
    )

    frame_num: EnumProperty(
        name="Number of frames",
        description="select number of frames to be imported",
        items=(
            ('0', "all", "Import all frames"),
            ('1', "1", "single Frame"),
            ('2', "2", "2 Frames"),
            ('3', "3", "3 Frames"),
            ('4', "4", "4 Frames"),
            ('5', "5", "5 Frames"),
            ('6', "6", "6 Frames"),
            ('7', "7", "7 Frames"),
            ('8', "8", "8 Frames"),
            ('9', "9", "9 Frames"),
            ('10', "10", "10 Frames"),
        ),
        default='0',
    )

    def execute(self, context):
        print(self.filepath, self.setting_cleanup, self.setting_tag_points, self.lod_lvl)
        if import_cem(
            context,
            filepath=self.filepath,
            bCleanup=self.setting_cleanup,
            bTagPoints=self.setting_tag_points,
            bTransform=self.setting_matrix_transform,
            bValidate=self.setting_validate,
            lod_level=self.lod_lvl, 
            frame_num=self.frame_num
            ):
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

class ExportCEM(bpy.types.Operator, ImportHelper):
    """Export an Empire Earth (AoC) CEM file"""
    bl_idname = "export_scene.cem"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export CEM"

    # ImportHelper mixin class uses this
    filename_ext = ".cem"
    check_extension = True
    path_mode: path_reference_mode

    filter_glob: StringProperty(
        default="*.cem",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    #setting_matrix_transform: BoolProperty(
    #    name="apply transformation matrix",
    #    description="if enabled, the included transformation matrix will get applied to the objects",
    #    default=True,
    #)

    def execute(self, context):
        print(self.filepath)
        if export_cem(context, filepath=self.filepath):
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

class PrepareCemOperator(bpy.types.Operator):
    bl_idname = "sequencer.collection_operator"
    bl_label = "Create New CEM Structure"
    bl_description = "Creates new CEM structure needed for exporting"

    def add_cube_placeholder(self, name: str, collection: bpy.types.Collection):
        tmp_obj = bpy.data.objects.new(name, None)
        tmp_obj.empty_display_type = 'CUBE'

        collection.objects.link(tmp_obj)

    def add_empty_placeholder(self, name: str, collection: bpy.types.Collection):
        tmp_obj = bpy.data.objects.new(name, None)
        tmp_obj.empty_display_size = CEMi.empty_size
        tmp_obj.empty_display_type = 'PLAIN_AXES'

        collection.objects.link(tmp_obj)

    def execute(self, context):
        print("creating fresh CEM structure")

        main_col = CEMi.add_collection("M:newUnit.cem.LOD 0")
        scene_root_col = CEMi.add_collection_child(name="1:Scene Root", parent_collection=main_col)
        tag_point_col = CEMi.add_collection_child(name="tag points", parent_collection=scene_root_col)

        self.add_cube_placeholder(name="1:none-tmp:0", collection=scene_root_col)
        self.add_cube_placeholder(name="2:player color-tmp:0", collection=scene_root_col)

        self.add_empty_placeholder(name="attack", collection=tag_point_col)
        self.add_empty_placeholder(name="damage_trail_1", collection=tag_point_col)
        self.add_empty_placeholder(name="weapon_mount_1", collection=tag_point_col)

        return {'FINISHED'}

class ErrorMessage(bpy.types.Operator):
    bl_idname = 'ui.error_message'
    bl_label = "Test error"
    bl_description = "Some useless text"

    def execute(self, context):
        self.report({'INFO'}, message="ERROR: SOME STUPID  MESSAGE")
        return {'CANCELLED'}


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportCEM.bl_idname, text="Empire Earth (.cem)")

def menu_func_export(self, context):
    self.layout.operator(ExportCEM.bl_idname, text="Empire Earth (.cem)")

def register():
    bpy.utils.register_class(ImportCEM)
    bpy.utils.register_class(ExportCEM)
    bpy.utils.register_class(PrepareCemOperator)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

    bpy.utils.register_class(ErrorMessage)

def unregister():
    bpy.utils.unregister_class(ImportCEM)
    bpy.utils.unregister_class(ExportCEM)
    bpy.utils.unregister_class(PrepareCemOperator)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    bpy.utils.unregister_class(ErrorMessage)


if __name__ == "__main__":
    register()
