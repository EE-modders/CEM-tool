bl_info = {
    "name" : "Empire Earth CEM-tool",
    "author" : "zocker_160",
    "description" : "addon for importing and exporting Empire Earth CEM files",
    "blender" : (4, 2, 3),
    "version" : (1, 0),
    "location" : "File > Import",
    "warning" : "This addon is still WiP and will contain bugs!",
    "category" : "Import-Export",
    "tracker_url": "https://github.com/EE-modders/CEM-tool/issues"
}

import bpy

from .CEMimport import cemImport, EMPTY_SIZE
from .CEMexport import cemExport
from . import utils

from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper, path_reference_mode


class ImportCEM(bpy.types.Operator, ImportHelper):
#class ImportCEM(bpy.types.Operator):
    """Import an Empire Earth CEM file"""
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
        print(self.filepath, self.setting_cleanup, self.lod_lvl)

        if self.setting_cleanup:
            print("cleaning up")
            utils.cleanup()

        cemImport(self.filepath, int(self.lod_lvl))
        return {'FINISHED'}


#class ExportCEM(bpy.types.Operator):
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

    def execute(self, context):
        cemExport(self.filepath)
        return {'FINISHED'}


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
        tmp_obj.empty_display_size = EMPTY_SIZE
        tmp_obj.empty_display_type = 'PLAIN_AXES'

        collection.objects.link(tmp_obj)

    def execute(self, context):
        print("creating fresh CEM structure")

        currScene = bpy.context.scene

        mainCol = bpy.data.collections.new("M:newUnit.cem.LOD 0")
        currScene.collection.children.link(mainCol)

        sceneRoot = bpy.data.collections.new("1:Scene Root")
        mainCol.children.link(sceneRoot)

        tagPoints = bpy.data.collections.new("tag points")
        sceneRoot.children.link(tagPoints)

        self.add_cube_placeholder(name="1:none-tmp:0", collection=sceneRoot)
        self.add_cube_placeholder(name="2:player color-tmp:0", collection=sceneRoot)

        self.add_empty_placeholder(name="attack", collection=tagPoints)
        self.add_empty_placeholder(name="damage_trail_1", collection=tagPoints)
        self.add_empty_placeholder(name="weapon_mount_1", collection=tagPoints)

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
    bpy.utils.register_class(PrepareCemOperator)
    bpy.utils.register_class(ImportCEM)
    bpy.utils.register_class(ExportCEM)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

    bpy.utils.register_class(ErrorMessage)

def unregister():
    bpy.utils.unregister_class(PrepareCemOperator)
    bpy.utils.unregister_class(ImportCEM)
    bpy.utils.unregister_class(ExportCEM)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    bpy.utils.unregister_class(ErrorMessage)


if __name__ == "__main__":
    register()
