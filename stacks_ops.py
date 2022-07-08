# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

#  Stacks
#  Collect Blender operators to stacks and execute them. Blender 3.1+ add-on
#  (c) 2022 Andrey Sokolov (so_records)

"""Blender «Stacks» add-on Operators"""

import bpy
from bpy.types import Operator, Object, Scene, BlenderRNA, ViewLayer, PropertyGroup, UIList, BlendData, Context, Event
from bpy.props import StringProperty
from bpy.utils import unregister_class
from typing import List, Set
from bpy.app.handlers import render_init as RenderInit, render_complete as RenderComplete, \
    render_cancel as RenderCancel, depsgraph_update_post as DepsgraphUpdate, render_pre as RenderPre

# The following are being imported from the stacks_support:
# bpy.utils.register_class,
# bpy.app.handlers.frame_change_post as FrameChange
# _ctypes.PyObj_FromPtr as Pointer

if __name__ == '__main__':
    try:
        # For PyCharm
        from stacks_support import *
        from stacks_support_common import *
        from stacks_presets_support import *
        from stacks_support_custom import *
    except ModuleNotFoundError:
        # For Blender
        from stacks.stacks_support import *
        from stacks.stacks_support_common import *
        from stacks.stacks_presets_support import *
        from stacks.stacks_support_custom import *
else:
    # For add-on
    from .stacks_support import *
    from .stacks_support_common import *
    from .stacks_presets_support import *
    from .stacks_support_custom import *


# ---------------------------------------------------- USER WARNING ----------------------------------------------------


class STACKS_OT_Warning(Operator):
    """Raise User Warning"""
    bl_idname = "stacks.warning"
    bl_label = "Warning!"
    type: StringProperty(default="ERROR")
    msg: StringProperty(default="")

    @classmethod
    def poll(cls, context: Context):
        """Conditions enabling execution of the Blender operator"""
        return True

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        return {'FINISHED'}

    def modal(self, context: Context, event: Event) -> Set[str]:
        """Blender operators' predeclared modal method"""
        if event:
            self.report({self.type}, self.msg)
        return {'FINISHED'}

    def invoke(self, context, event: Event) -> Set[str]:
        """Blender operators' predeclared invoke method"""
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


# ------------------------------ UPDATE FROM UI: EXECUTE ACTIVE OBJECT'S OPERATORS STACKS ------------------------------


class STACKS_OT_Update(Operator):
    """Execute active Object's Stacks Operators Stacks"""
    bl_idname = "stacks.update"
    bl_label = "Update"
    bl_options = {'UNDO'}

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        bpy.ops.ed.undo_push()
        STACKS_ExecuteStacks(context)
        return {'FINISHED'}


# ------------------------------------------------------ SLOT ADD ------------------------------------------------------


class STACKS_OT_SlotAdd(Operator):
    """Add new slot"""
    bl_idname = "stacks.slot_add"
    bl_label = "Add Slot"
    bl_options = {"UNDO"}
    prop: StringProperty(default="stacks")
    active: StringProperty(default="stacks_active")
    source: StringProperty(default="scene")

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        bpy.ops.ed.undo_push()
        STACKS_SlotAdd(getattr(context, self.source), self.prop, self.active)
        return {'FINISHED'}

    def invoke(self, context: Context, event: Event) -> Set[str]:
        """Blender operators' predeclared invoke method"""
        return self.execute(context)


# ----------------------------------------------------- SLOT REMOVE ----------------------------------------------------


class STACKS_OT_SlotRemove(Operator):
    """Remove active slot"""
    bl_idname = "stacks.slot_remove"
    bl_label = "Remove Slot"
    bl_options = {"UNDO"}
    prop: StringProperty(default="stacks")
    active: StringProperty(default="stacks_active")
    source: StringProperty(default="scene")

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        bpy.ops.ed.undo_push()
        STACKS_SlotRemove(getattr(context, self.source), self.prop, self.active)
        return {'FINISHED'}

    def invoke(self, context: Context, event: Event) -> Set[str]:
        """Blender operators' predeclared invoke method"""
        return self.execute(context)


# -------------------------------------------------- SLOT MOVE UP/DOWN -------------------------------------------------


class STACKS_OT_SlotMove:
    """Move active slot up/down base class"""
    bl_label = "Move Slot Up/Down"
    bl_options = {"UNDO"}
    direction: BoolProperty(default=True)


class STACKS_OT_OpsSlotMove(Operator, STACKS_OT_SlotMove):
    """Move active Scene's active Stacks Operators Stack slot up/down"""
    bl_idname = "stacks.slot_ops_move"
    st_index: IntProperty()  # Stack index

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        bpy.ops.ed.undo_push()
        STACKS_OpsSlotMove(context, self.st_index, self.direction)
        return {'FINISHED'}

    def invoke(self, context: Context, event: Event) -> Set[str]:
        """Blender operators' predeclared invoke method"""
        return self.execute(context)


class STACKS_OT_ObSlotMove(Operator, STACKS_OT_SlotMove):
    """Move active Object's active Stacks Stack slot up/down"""
    bl_idname = "stacks.slot_ob_move"

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        bpy.ops.ed.undo_push()
        STACKS_ObSlotMove(context, self.direction)
        return {'FINISHED'}


# -------------------------------------------- NEW SCENE'S OPERATORS STACK ---------------------------------------------


class STACKS_OT_New(Operator):
    """Add New Stack to Scene"""
    bl_idname = 'stacks.new'
    bl_label = 'New Stack'
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Conditions enabling execution of the Blender operator"""
        return context.object is not None

    @staticmethod
    def __get_stack_name(sc: Scene) -> str:
        """Generate new unique Scene's Operators Stack's name"""
        stack_base_name = 'Stack'
        stack_name = str(stack_base_name)
        num = 1
        while stack_name in [st.name for st in sc.stacks]:
            stack_name = f'{stack_base_name} {num:02d}'
            num += 1
        return stack_name

    @staticmethod
    def __new_stack(sc: Scene, ob: Object, stack_name: str) -> None:
        """Create new Scene's Operators Stack"""
        bpy.ops.stacks.slot_add(prop='stacks', active='stacks_active', source='scene')
        stack = sc.stacks[sc.stacks_active]
        stack.name = stack_name
        new_index = len(sc.stacks) - 1
        ob.stacks[ob.stacks_active].stack = f'{new_index:03d}'
        ob.stacks_c[ob.stacks_active].stack_index = new_index

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        bpy.ops.ed.undo_push()
        sc = context.scene
        ob = context.object
        live_update = bool(ob.stacks_common.live_update)
        ob.stacks_common.live_update = False
        stack_name = self.__get_stack_name(sc)
        self.__new_stack(sc, ob, stack_name)
        context.object.stacks_common.live_update = live_update
        return {'FINISHED'}


# ------------------------------------- DUPLICATE ACTIVE SCENE'S OPERATORS STACK ---------------------------------------


class STACKS_OT_Duplicate(Operator):
    """Create a copy of the active Scene's Operators stack"""
    bl_idname = 'stacks.duplicate'
    bl_label = 'Duplicate Stack'
    bl_options = {"UNDO"}

    @property
    def active_index(self) -> int:
        ob = self.context.object
        return ob.stacks_c[ob.stacks_active].stack_index

    @property
    def stack(self) -> PropertyGroup:
        """Return active Scene's Stack"""
        return self.context.scene.stacks[self.active_index]

    def __copy_settings(self, src: PropertyGroup, trg: PropertyGroup) -> None:
        for op in src.ops:
            bpy.ops.stacks.slot_add(
                prop=f"stacks[{self.active_index}].ops",
                active=f"stacks[{self.active_index}].ops_active"
            )
            trg_op = trg.ops[trg.ops_active]
            for item in dir(op):
                if item.startswith(("__", "bl_", "id_", "rna_")) or callable(getattr(op, item)):
                    continue
                setattr(trg_op, item, getattr(op, item))

    @staticmethod
    def __set_ob_stack_index(context: Context) -> None:
        new_index = len(context.scene.stacks) - 1
        context.object.stacks_c[context.object.stacks_active].stack_index = new_index
        context.object.stacks[context.object.stacks_active].stack = str(f"{new_index:03d}")

    def execute(self, context: Context) -> Set[str]:
        bpy.ops.ed.undo_push()
        ob = context.object
        live_update = bool(ob.stacks_common.live_update)
        ob.stacks_common.live_update = False
        self.context = context
        src_stack = self.stack
        bpy.ops.stacks.new()
        trg_stack = self.stack
        trg_stack.name = src_stack.name+".copy"
        self.__copy_settings(src_stack, trg_stack)
        self.__set_ob_stack_index(context)
        context.scene.update_tag()
        ob.stacks_common.live_update = live_update
        upd_ops(self, context)
        return {'FINISHED'}


# ---------------------------------------- REMOVE SCENE'S ACTIVE OPERATORS STACK ---------------------------------------


class STACKS_OT_Remove(Operator):
    """Remove active Stack from Scene's Stacks"""
    bl_idname = 'stacks.remove'
    bl_label = 'Remove Stack'
    bl_options = {'UNDO'}
    type: StringProperty(default='STACK')

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Conditions enabling execution of the Blender operator"""
        return context.object is not None and context.object.type == 'MESH'

    @staticmethod
    def __remove_stack(context: Context) -> None:
        """Remove Scene Stack"""
        sc = context.scene
        ob = context.object
        sc.stacks_active = ob.stacks_c[ob.stacks_active].stack_index
        bpy.ops.stacks.slot_remove(
            prop='stacks',
            active='stacks_active',
            source='scene'
        )

    @staticmethod
    def __remove_selection(context: Context) -> None:
        """Remove Scene Selection"""
        ob = context.object
        ob_stack = ob.stacks_c[ob.stacks_active]
        ob_stack.selection = "f-f-t|[]-[]-[]"

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        bpy.ops.ed.undo_push()
        if self.type == 'STACK':
            self.__remove_stack(context)
        else:
            self.__remove_selection(context)
        return {'FINISHED'}


# ---------------------------------------- CLEAR ACTIVE OBJECT'S OPERATORS STACKS --------------------------------------


class STACKS_OT_Clear(Operator):
    """
    Clear all Stacks Operators Stacks from the active object.
    The Stacks remain available in the Scene.
    """
    bl_idname = 'stacks.clear'
    bl_label = 'Clear Stacks'
    bl_options = {"UNDO"}

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        bpy.ops.ed.undo_push()
        ob = context.object
        ref = ob.stacks_common.ob_reference
        obj_col_link(ob, ref)
        obs_swap_names(ob, ref)
        ref.use_fake_user = False
        ref.hide_select = False
        set_active_obj(context, ref)
        ref.stacks_common.ob_stacks = None
        ref.stacks_common.ob_reference = None
        ref.stacks.clear()
        ref.stacks_c.clear()
        ref.stacks_common.live_update = True
        mesh = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(mesh)
        return {'FINISHED'}


# ---------------------------------------- APPLY ACTIVE OBJECT'S OPERATORS STACKS --------------------------------------


class STACKS_OT_Apply(Operator):
    """Apply Operators Stacks"""
    bl_idname = 'stacks.apply'
    bl_label = 'Apply'
    bl_options = {'UNDO'}

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        bpy.ops.ed.undo_push()
        ob = context.object
        ob.stacks_common.live_update = False
        ob.stacks.clear()
        ob.stacks_c.clear()
        ref = ob.stacks_common.ob_reference
        mesh = ref.data
        bpy.data.objects.remove(ref)
        bpy.data.meshes.remove(mesh)
        return {'FINISHED'}


# ----------------------------- STORE SELECTED MESH ELEMENTS INTO OPERATOR'S STRING PROPERTY ---------------------------


class STACKS_OT_SelectStore(Operator):
    """Store selected mesh elements"""
    bl_idname = 'stacks.select_store'
    bl_label = 'Store'

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Conditions enabling execution of the Blender operator"""
        return context.object is not None and context.object.type == 'MESH'

    @staticmethod
    def __modes(context: Context) -> str:
        """Interpret context selection mode as a string in the specified format"""
        modes = context.tool_settings.mesh_select_mode
        m1 = 'T' if modes[0] else 'S'
        m2 = 'T' if modes[1] else 'S'
        m3 = 'T' if modes[2] else 'S'
        return f"{m1}-{m2}-{m3}"

    @staticmethod
    def __data(context: Context) -> str:
        """Interpret context selection data as a string in the specified format"""
        verts = [v.index for v in context.object.data.vertices if v.select]
        edges = [e.index for e in context.object.data.edges if e.select]
        faces = [f.index for f in context.object.data.polygons if f.select]
        return f"|{verts}-{edges}-{faces}"

    def __get_selection(self, context: Context) -> str:
        """
        Get current mesh selection data as a string in the specified format:
        T-T-T|[List of vertices indices]-[List of edges indices]-[List of faces indices]
        """
        assert context.mode == 'EDIT_MESH'
        modes = self.__modes(context)
        setmode(context, 'OBJECT')
        data = self.__data(context)
        setmode(context, 'EDIT')
        return modes + data

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        if not context.mode == 'EDIT_MESH':
            setmode(context, 'EDIT')
            return {'FINISHED'}
        ob = context.object
        ob.stacks_c[ob.stacks_active].selection = self.__get_selection(context)
        return {'FINISHED'}


# ------------------------------------------------------- PRESETS ------------------------------------------------------

# -------------------------------------------------- NEW BLENDER TEXT --------------------------------------------------


class STACKS_OT_NewTextPopup(Operator):
    """Create New Blender Text and save Preset into it"""
    bl_idname = "stacks.new_text"
    bl_label = "Create New Blender Text"
    name: bpy.props.StringProperty(name="Enter Name", default="Stacks Preset")

    @staticmethod
    def __set_name(tname: str) -> str:
        """Generate unique Text name with proper index"""
        num = 1
        text_name = tname
        while text_name in bpy.data.texts:
            text_name = f"{tname} {num:03d}"
            num += 1
        return text_name

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        text_name = self.__set_name(self.name)
        new = bpy.data.texts.new(text_name)
        context.scene.stacks_common.save_to = new
        bpy.ops.stacks.preset_save()
        msg = f'Preset "{text_name}" has been added to Blender Texts'
        self.report({'INFO'}, msg)
        return {'FINISHED'}

    def invoke(self, context: Context, event: Event) -> Set[str]:
        """Blender operators' predeclared invoke method"""
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


# ------------------------------------ POP UP DIALOG: DELETE BLENDER TEXT ANYWAY?  -------------------------------------


class STACKS_OT_TextDeletePopup(Operator):
    """Delete Blender Text Popup"""
    bl_idname = "stacks.del_text_popup"
    bl_label = "WARNING: Text is not empty!"
    delete: BoolProperty(
        name="Delete Anyway?",
        default=False
    )

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        props = context.scene.stacks_common
        text = props.save_to if props.save_preset else props.load_from
        text_name = str(text.name)
        if self.delete:
            bpy.data.texts.remove(text)
        self.report({'INFO'}, f'Text "{text_name}" deleted')
        return {'FINISHED'}

    def invoke(self, context: Context, event: Event) -> Set[str]:
        """Blender operators' predeclared invoke method"""
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


# ------------------------------------------------ DELETE BLENDER TEXT -------------------------------------------------


class STACKS_OT_TextDelete(Operator):
    """Delete Blender Text"""
    bl_idname = "stacks.del_text"
    bl_label = "Delete Blender Text"

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Conditions enabling execution of the Blender operator"""
        props = context.scene.stacks_common
        return all((props.save_preset, props.save_to))

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        props = context.scene.stacks_common
        preset_file = props.save_to
        if len(preset_file.lines) > 1 or preset_file.lines[0].body:
            bpy.ops.stacks.del_text_popup('INVOKE_DEFAULT')
        return {'FINISHED'}


# ----------------------------------------------------- PRESET SAVE ----------------------------------------------------


class STACKS_OT_PresetSave(Operator):
    """Save Stacks Preset into the specified Blender Text"""
    bl_idname = 'stacks.preset_save'
    bl_label = 'Store'

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Conditions enabling execution of the Blender operator"""
        sc = context.scene
        ob = context.object
        props = sc.stacks_common
        index = ob.stacks_c[ob.stacks_active].stack_index
        return all((props.save_preset, props.save_to, index < len(sc.stacks)))

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        sc = context.scene
        ob = context.object
        props = sc.stacks_common
        sc_stack = sc.stacks[ob.stacks_c[ob.stacks_active].stack_index]
        ops = sc.stacks[ob.stacks_c[ob.stacks_active].stack_index].ops
        preset_file = props.save_to
        if (len(preset_file.lines) > 1 or preset_file.lines[0].body) and not props.overwrite:
            msg = 'Selected Text is not empty. Enable "Overwrite" or select another Text or create new one'
            bpy.ops.stacks.warning("INVOKE_DEFAULT", msg=msg, type='ERROR')
        else:
            preset = STACKS_PresetsOps(preset_file)
            preset.store_preset(ops, sc_stack.name)
            props.save_preset = False
            msg = f'Preset has been saved to "{preset.bl_text.name}" Blender Text'
            bpy.ops.stacks.warning("INVOKE_DEFAULT", msg=msg, type='INFO')
        return {'FINISHED'}


# ----------------------------------------------------- PRESET LOAD ----------------------------------------------------


class STACKS_OT_PresetLoad(Operator):
    """Load Stacks Preset from the specified Blender Text"""
    bl_idname = 'stacks.preset_load'
    bl_label = 'Load'

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Conditions enabling execution of the Blender operator"""
        props = context.scene.stacks_common
        return all((props.load_preset, props.load_from))

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        sc = context.scene
        props = sc.stacks_common
        preset_file = props.load_from
        preset = STACKS_PresetsOps(preset_file)
        preset.load_preset(context)
        props.load_preset = False
        return {'FINISHED'}


# -------------------------------------------------- RENDER ANIMATION --------------------------------------------------


class STACKS_OT_RenderAnimation(Operator):
    """
    Stacks add-on Render Animation.
    To be used instead of native Blender Render Animation operator
    """
    bl_idname = 'stacks.render'
    bl_label = 'Render Animation'
    rendering = False
    render_started = False
    render_cancelled = False
    render_finished = False
    timer = None
    render_pre = None
    render_cancel = None
    render_complete = None
    frame = None
    frames = None
    frame_change = None
    render_path = None
    sc = None
    wm = None
    win = None
    handlers_store = []

    @classmethod
    def poll(cls, context: Context):
        """Conditions enabling execution of the Blender operator"""
        ps = context.scene.stacks_common
        return ps.animatable and ps.frame_change_id

    def __structure(self) -> None:
        """Setup self variables, handlers and timer instead of __init__()"""
        self.render_path = self.sc.render.filepath
        self.frame = self.sc.frame_current
        self.frames = self.__frames()
        self.frame_change = Pointer(int(self.sc.stacks_common.frame_change_id))
        assert callable(self.frame_change)
        self.__pre_render_handlers_clear()
        self.__pre_render_handlers_append()
        self.rendering = False
        self.render_started = False
        self.render_cancelled = False
        self.render_finished = True
        self.__timer_add()

    def __pre_render_handlers_clear(self) -> None:
        """Remove regular limiting functions from render handlers"""
        r_init = Pointer(int(self.sc.stacks_common.render_init_id))
        r_complete = Pointer(int(self.sc.stacks_common.render_complete_id))

        # just to keep links to the original limiting functions in the memory
        # so that they are not cleaned up by the garbage collector:
        self.handlers_store = [r_init, r_complete]

        while r_init in RenderInit:
            RenderInit.remove(r_init)
        while r_complete in RenderComplete:
            RenderComplete.remove(r_complete)
        while r_complete in RenderCancel:
            RenderCancel.remove(r_complete)

    def __pre_render_handlers_append(self) -> None:
        """Append internal functions to render handlers. Store them as class call's attributes"""

        def render_pre(self_) -> None:
            """To be used in bpy.app.handlers.render_pre"""
            self_.rendering = True
            self_.render_finished = False

        def render_cancel(self_) -> None:
            """To be used in bpy.app.handlers.render_cancel"""
            self_.rendering = False
            if self_.render_started:
                self_.render_started = False
            self_.render_cancelled = True
            self_.render_finished = True

        def render_complete(self_) -> None:
            """To be used in bpy.app.handlers.render_complete"""
            self_.rendering = False
            if self_.render_started:
                self_.render_started = False
            self_.render_finished = True

        self.render_pre = lambda x: render_pre(self)
        self.render_cancel = lambda x: render_cancel(self)
        self.render_complete = lambda x: render_complete(self)
        RenderPre.append(self.render_pre)
        RenderCancel.append(self.render_cancel)
        RenderComplete.append(self.render_complete)

    def __post_render_handlers_clear(self) -> None:
        """Remove internal functions from render handlers"""
        while self.render_pre in RenderPre:
            RenderPre.remove(self.render_pre)
        while self.render_cancel in RenderCancel:
            RenderCancel.remove(self.render_cancel)
        while self.render_complete in RenderComplete:
            RenderComplete.remove(self.render_complete)

    def __post_render_handlers_append(self) -> None:
        """Append regular limiting functions to render handlers"""
        RenderInit.append(Pointer(int(self.sc.stacks_common.render_init_id)))
        RenderComplete.append(Pointer(int(self.sc.stacks_common.render_complete_id)))
        RenderCancel.append(Pointer(int(self.sc.stacks_common.render_complete_id)))

    def __fix_write_still(self) -> None:
        """
        Sets render.render()'s write_sill parameter to False. This is done via adding
        this to the depsgraph_update_post handler, because write_still becomes True once
        the current operator is finished if it is called from the current operator.
        """

        def fix_write_still(self_, context) -> None:
            """Functions used in bpy.app.handlers must have two positional arguments"""
            try:
                op = bpy.context.window_manager.operator_properties_last("render.render")
            except AttributeError:  # probably there may be other Errors
                return
            if op.write_still is True:
                op.write_still = False
                bpy.context.scene.update_tag()
                while fix_write_still in DepsgraphUpdate:
                    DepsgraphUpdate.remove(fix_write_still)

        self.wm.operator_properties_last("render.render").write_still = False
        DepsgraphUpdate.append(fix_write_still)

    def __timer_add(self, tick: float = .1) -> None:
        """Add timer to active Blender Window Manager to update events on modal loop"""
        self.timer = self.wm.event_timer_add(time_step=tick, window=self.win)

    def __timer_remove(self) -> None:
        """Remove timer from active Blender Window Manager"""
        try:
            for _ in range(3):
                self.wm.event_timer_remove(self.timer)
        except Exception as e:
            print(f'Exception {e} passed in STACKS_OT_RenderAnimation while attempt to delete')

    def __frames(self) -> List[int]:
        """Return active Scene's Timeline as list of frames to be rendered"""
        return list(range(self.sc.frame_start, self.sc.frame_end + 1))

    def __set_path(self, frame) -> None:
        """Fix current Output render path by adding current frame number to the file name"""
        self.sc.render.filepath = self.render_path + f'{frame:04d}'

    def __fr_change_off(self) -> None:
        """Remove Stacks Execute function from the bpy.app.handlers.frame_change_post handler"""
        assert self.frame_change == Pointer(int(self.sc.stacks_common.frame_change_id))
        for f in FrameChange:
            if f == self.frame_change:
                while f in FrameChange:
                    FrameChange.remove(f)

    def __fr_change_on(self) -> None:
        """Append Stacks Execute function to the bpy.app.handlers.frame_change_post handler"""
        self.frame_change = Pointer(int(self.sc.stacks_common.frame_change_id))
        for f in FrameChange:
            if f == self.frame_change:
                return
        FrameChange.append(self.frame_change)

    def __set_new_frame(self) -> None:
        """
        Pop a new frame from self.frames.
        Set index in the filepath.
        Set the frame as Scene's current frame
        """
        frame = self.frames.pop(0)
        self.__set_path(frame)
        self.__fr_change_on()
        self.sc.frame_set(frame)
        self.__fr_change_off()
        self.sc.update_tag()

    def __render_new_frame(self) -> None:
        """Render current frame"""
        self.render_started = True
        bpy.ops.render.render('INVOKE_DEFAULT', animation=False, write_still=True)

    def __cleanup(self, context: Context):
        """
        Clean Up project after render:
        - restore filepath
        - restore current frame
        - remove timer
        - restore FrameChange handler function
        - restore Render limiting handler functions
        - reset Blender's bpy.ops.render.render() operator's write_still parameter
        """
        self.sc.render.filepath = self.render_path
        self.sc.frame_set(self.frame)
        self.__timer_remove()
        self.__fr_change_off()  # in case cancelled
        self.__fr_change_on()
        self.__post_render_handlers_clear()
        self.__post_render_handlers_append()
        self.__fix_write_still()
        self.sc.update_tag()

    def invoke(self, context: Context, event: Event) -> Set[str]:
        """Blender operators' predeclared invoke method"""
        return self.execute(context)

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        self.wm = context.window_manager
        self.win = context.window
        self.sc = context.scene
        self.__structure()
        self.wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context: Context, event: Event) -> Set[str]:
        """Blender operators' predeclared modal method"""
        if event.type == 'ESC':
            print('Render Escaped')
            self.__cleanup(context)
            return {'FINISHED'}
        elif event.type == 'TIMER':
            if self.render_cancelled:
                print('Render Cancelled')
                self.__cleanup(context)
                return {'FINISHED'}
            elif self.render_started and not self.rendering:
                # force render launch if not started
                self.__render_new_frame()
            elif self.render_finished:
                if len(self.frames):
                    self.__set_new_frame()
                    self.__render_new_frame()
                else:
                    self.__cleanup(context)
                    return {'FINISHED'}
        return {'PASS_THROUGH'}


# ------------------------------------------------------ REGISTER ------------------------------------------------------


classes = [
    STACKS_OT_Warning,
    STACKS_OT_SlotAdd,
    STACKS_OT_SlotRemove,
    STACKS_OT_OpsSlotMove,
    STACKS_OT_ObSlotMove,
    STACKS_OT_New,
    STACKS_OT_Duplicate,
    STACKS_OT_Remove,
    STACKS_OT_Clear,
    STACKS_OT_Apply,
    STACKS_OT_SelectStore,
    STACKS_OT_NewTextPopup,
    STACKS_OT_PresetSave,
    STACKS_OT_PresetLoad,
    STACKS_OT_TextDeletePopup,
    STACKS_OT_TextDelete,
    STACKS_OT_Update,
    STACKS_OT_RenderAnimation,
]


def register():
    for cl in classes:
        register_class(cl)


def unregister():
    for cl in reversed(classes):
        unregister_class(cl)


if __name__ == '__main__':
    register()
