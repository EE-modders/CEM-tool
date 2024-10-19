import bpy

def ShowMessageBox(message="", title="Message Box", icon='INFO'):

    def execute(self, context):
        self.report({'INFO'}, message)

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

"""
import bpy
 
class MessageBox(bpy.types.Operator):
    bl_idname = "ui.error"
    bl_label = "LABEL"
 
    message = "SOME CRAZY MESSAGE"
 
    def execute(self, context):
        self.ShowMessageBox(context)
        self.report({'ERROR'}, self.message)
                
        #print(self.message)
        return {'FINISHED'}
 
    def invoke(self, context, event):
        return self.execute(context)    

    def ShowMessageBox(self, context, message="another Message", title="", icon='NONE'):
        def draw(self, context):
            self.layout.label()
            self.layout.label()
            self.layout.label(text="__________")
            self.layout.label(text=message)
            self.layout.label(text="operator1")
            self.layout.label(text="operator2")

        bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)
 
def register():
    bpy.utils.register_class(MessageBox)
 
def unregister():
    bpy.utils.unregister_class(MessageBox)


register()


################


def displaySEMREFLink(self, context, err_type: str, err_message: str):
    def draw(self, context):
        # self.layout.label(text=self.p_text)
        # self.layout.label()
        self.layout.label()
        self.layout.label( )
        self.layout.operator('wm.get_update', icon='IMPORT', text='Open GitHub page')

    self.report({err_type}, err_message)
    print(err_message)
    bpy.context.window_manager.popup_menu(draw, title=err_message, icon='NONE')


"""
