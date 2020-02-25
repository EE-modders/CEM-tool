bl_info = {
    "name" : "Empire Earth CEM-tool",
    "author" : "zocker_160",
    "description" : "addon for importing and exporting Empire Earth CEM files",
    "blender" : (2, 82, 7),
    "version" : (0, 0, 5),
    "location" : "File > Import",
    "warning" : "only import of CEM v2 files is supported (for now) the export is still WiP!",
    "category" : "Import-Export"
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

def import_cem(context, filepath: str, bTagPoints: bool, bCleanup: bool, bTransform: bool, lod_level: str):
    print("starting import of %s" % filepath)

    if bCleanup:
        print("CLEANING UP")
        CEMi.cleanup()
    return CEMi.main_function_import_file(filename=filepath, bTagPoints=bTagPoints, bTransform=bTransform, lod_lvl=int(lod_level) )

def export_cem(context, filepath: str):
    print("starting export of %s" % filepath)

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

    def execute(self, context):
        print(self.filepath, self.setting_cleanup, self.setting_tag_points, self.lod_lvl)
        if import_cem(context, filepath=self.filepath, bCleanup=self.setting_cleanup, bTagPoints=self.setting_tag_points, bTransform=self.setting_matrix_transform, lod_level=self.lod_lvl):
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

# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportCEM.bl_idname, text="Empire Earth (.cem)")

def menu_func_export(self, context):
    self.layout.operator(ExportCEM.bl_idname, text="Empire Earth (.cem)")

def register():
    bpy.utils.register_class(ImportCEM)
    bpy.utils.register_class(ExportCEM)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ImportCEM)
    bpy.utils.unregister_class(ExportCEM)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
