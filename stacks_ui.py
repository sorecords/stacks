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

"""Draw UI of the Blender «Stacks» add-on"""

from bpy.types import Panel, ViewLayer, UIList, UILayout, PropertyGroup, Object, Scene
from bpy.utils import register_class, unregister_class
if __name__ == '__main__':
    try:  # PyCharm import
        from stacks_constants import INTERPOLATE
    except ModuleNotFoundError:  # Blender Text Editor import
        from stacks.stacks_constants import INTERPOLATE
else:  # Add-on import
    from .stacks_constants import INTERPOLATE


# ----------------------------------------- INTERPOLATED VALUES DRAWING SUPPORT ----------------------------------------


def interp(optype: str, opfunc: str, prop: str, col: UILayout, op: PropertyGroup,
           stack_ob: PropertyGroup = None, label: str = "Offset") -> None:
    """To be used in panel drawing function for interpolated parameters"""
    prop_names = INTERPOLATE[optype][opfunc][prop]
    syncable = True if len(prop_names) > 2 else False
    if op.interp_type == 'CONSTANT' or stack_ob.repeat <= 1:
        if syncable:
            col.label(text=label)
            row = col.row(align=True)
            rcol = row.column(align=True)
            if op.value_sync:
                rcol.prop(op, prop, text="", index=0),
            else:
                rcol.prop(op, prop, text=""),
            rcol = row.column(align=True)
            rcol.prop(op, "value_sync", text="", icon="LINKED", toggle=True)
        else:
            col.prop(op, prop, text=label)
    else:
        try:
            len(getattr(op, prop_names[0]))
            iterable = True
        except TypeError:
            iterable = False

        # if iterable and syncable and op.value_sync:
        col.label(text=f"{label}:")
        row = col.row(align=True)
        layout = row.column(align=True) if iterable else row
        layout.prop(op, prop_names[0],
                    text="Min",
                    index=0 if iterable and syncable and op.value_sync else -1)
        if stack_ob.repeat > 1:
            layout = row.column(align=True) if iterable else row
            layout.prop(op, prop_names[1], text="Max",
                        index=0 if iterable and syncable and op.value_sync else -1)
            if op.interpolate == 'RANDOM':
                col.prop(op, "interp_seed", text="Seed")
        if iterable and syncable:
            rcol = row.column(align=True)
            if not op.value_sync:
                rrow = rcol.row(align=True)
                rrow.enabled = False
                rrow.prop(stack_ob, "dummy", text="", icon="BLANK1", toggle=False, emboss=False)
            rcol.prop(op, "value_sync", text="", icon="LINKED", toggle=True)


# ----------------------------------------------- OBJECT STACKS UI LISTS -----------------------------------------------


class STACKS_UL_ObStacks(UIList):
    
    def draw_item(self, _context, layout, _data, item, icon, _active_data, _active_propname, _index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            ob = _context.object
            sc = _context.scene
            stack = ob.stacks_c[item.index]
            sc_stack = sc.stacks[stack.stack_index] if stack.stack_index < len(sc.stacks) else stack
            if stack.type == 'SELECT':
                if stack.selection == "f-f-t|[]-[]-[]":
                    row = layout.row()
                    row.alignment = 'CENTER'
                    col = row.column()
                    col.enabled = False
                    col.prop(stack, "dummy", text="", emboss=True, icon='ERROR')
                    row.label(text="Selection is Not Set")
                    col = row.column()
                    col.enabled = False
                    col.prop(stack, "dummy", text="", emboss=True, icon='ERROR')
                else:
                    row = layout.row(align=True)
                    row.prop(stack, "name", text="", emboss=False, icon_value=icon)
                    row.prop(
                        stack, "enabled", text="", emboss=False,
                        icon='CHECKBOX_HLT' if stack.enabled else 'CHECKBOX_DEHLT'
                    )
            else:
                row = layout.row(align=True)
                row.prop(sc_stack, "name", text="", emboss=False, icon_value=icon)
                row.prop(
                    stack, "enabled", text="", emboss=False,
                    icon='CHECKBOX_HLT' if stack.enabled else 'CHECKBOX_DEHLT'
                )
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon="FILE_VOLUME")
            

# --------------------------------------------- OPERATORS STACKS UI LISTS ----------------------------------------------


class STACKS_UL_Stacks(UIList):
    
    def draw_item(self, _context, layout, _data, item, icon, _active_data, _active_propname, _index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.prop(item, "name", text="", emboss=False, icon_value=icon)
            row.prop(
                item, "enabled", text="", emboss=False,
                icon='CHECKBOX_HLT' if item.enabled else 'CHECKBOX_DEHLT'
            )
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon="FILE_VOLUME")


# ------------------------------------------------------ TOP MENU ------------------------------------------------------


class STACKS_UI_TopMenu:
    """UI Layout: Panel Top Menu Drawing"""
    def __init__(self, ob: Object, col: UILayout, sc_common: PropertyGroup):
        self.ob = ob
        if self.ob.stacks_common.ob_stacks is not None:
            self.ob = self.ob.stacks_common.ob_stacks
            col.label(text="EDITING ORIGINAL", icon='ERROR')

        row = col.row(align=True)
        row.prop(self.ob.stacks_common, "show_reference", text="Show Original", toggle=True)
        row.prop(self.ob.stacks_common, "edit_reference", text="Edit Original", toggle=True)
        row.prop(sc_common, "animatable", text="", icon="KEYFRAME_HLT", toggle=True)
        if sc_common.animatable:
            col.operator("stacks.render")

    def __call__(self):
        return self.ob


# ----------------------------------------------------- STACK LIST -----------------------------------------------------


class STACKS_UI_StackList:
    """UI Layout: Stack List Drawing"""
    def __init__(self, layout: UILayout, ob: Object):
        self.interrupt = False
        mainrow = layout.row(align=True)
        col = mainrow.column()
        col.template_list("STACKS_UL_ObStacks", "name", ob, "stacks", ob, "stacks_active",
                          rows=(5 if len(ob.stacks) > 1 else 3) if len(ob.stacks) else 1)
        ops = mainrow.column(align=True)
        op_add = ops.operator("stacks.slot_add", text="", icon="ADD")
        op_add.prop = "stacks"
        op_add.active = "stacks_active"
        op_add.source = "object"
        op_rem = ops.operator("stacks.slot_remove", text="", icon="REMOVE")
        op_rem.prop = "stacks"
        op_rem.active = "stacks_active"
        op_rem.source = "object"
        if not len(ob.stacks):
            self.interrupt = True
            return
        elif len(ob.stacks) > 1:
            ops.separator()
            op_move_up = ops.operator("stacks.slot_ob_move", text="", icon="TRIA_UP")
            op_move_up.direction = True
            op_move_down = ops.operator("stacks.slot_ob_move", text="", icon="TRIA_DOWN")
            op_move_down.direction = False
        ops.separator()
        ops.operator("stacks.apply", text="", icon="EVENT_RETURN")
        ops.operator("stacks.clear", text="", icon="TRASH")

    def __call__(self):
        return self.interrupt


# ----------------------------------------------------- STACK TYPE -----------------------------------------------------


class STACKS_UI_StackType:
    """UI Layout: Stack Type Menu Drawing"""
    def __init__(self, ob: Object, col: UILayout, stack_ob: PropertyGroup):
        col.separator()
        col.prop(stack_ob, 'type', text='Type')


# ---------------------------------------------------- SELECT MENU -----------------------------------------------------


class STACKS_UI_SelectMenu:
    """UI Layout: Select Menu Drawing"""
    def __init__(self, col: UILayout):
        col.separator()
        col.operator("stacks.select_store", text='Set Selection', icon='IMPORT')
        ops = col.operator('stacks.remove', text='Clear Selection', icon='PANEL_CLOSE')
        ops.type = 'SELECT'


# ----------------------------------------------------- STACK MENU -----------------------------------------------------


class STACKS_UI_StackMenu:
    """UI Layout: Stack Menu Drawing"""
    def __init__(self, layout: UILayout, ob: Object, stack_ob: PropertyGroup, sc_common: PropertyGroup, sc: Scene):
        self.interrupt = False
        stack, self.active_index, self.stack_sc = self.__active_stack(ob, sc)

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(ob.stacks_common, "live_update", text='Live Update', toggle=True)
        row.prop(ob.stacks_common, "update_all", text='Update All', toggle=True)

        row = col.row(align=True)
        row.prop(sc_common, "op_stck_closed", text="", emboss=False,
                 icon="RIGHTARROW" if sc_common.op_stck_closed else "DOWNARROW_HLT")
        row.label(text="Stack:")
        if sc_common.op_stck_closed:
            return

        col.prop(stack_ob, 'type', text='Type')
        if stack_ob.type == 'SELECT':
            STACKS_UI_SelectMenu(col)
            self.interrupt = True
            return

        row = col.row(align=True)
        row.prop(stack, 'stack', text="Stack")
        if self.active_index < len(sc.stacks):
            row.operator('stacks.duplicate', text="", icon="DUPLICATE")
            row.operator('stacks.remove', text='', icon='PANEL_CLOSE')

        col.separator()
        col.operator('stacks.new', text="New Stack", icon="FILE_NEW")

    def __call__(self):
        if self.interrupt:
            return None, None
        else:
            return self.stack_sc, self.active_index

    @staticmethod
    def __active_stack(ob: Object, sc: Scene):
        stack = ob.stacks[ob.stacks_active]
        active_index = int(stack.stack)
        stack_sc = sc.stacks[active_index] if active_index < len(sc.stacks) else None
        return stack, active_index, stack_sc


# ------------------------------------------------------- PRESETS ------------------------------------------------------


class STACKS_UI_Presets:
    """UI Layout: Presets Menu Drawing"""
    def __init__(self, col: UILayout, sc_common: PropertyGroup):
        row = col.row(align=True)
        row.prop(sc_common, "presets_closed", text="", emboss=False,
                 icon="RIGHTARROW" if sc_common.presets_closed else "DOWNARROW_HLT")
        row.label(text="Presets:")
        if sc_common.presets_closed:
            return

        col.separator()
        row = col.row(align=True)
        row.prop(sc_common, "save_preset", text="Save Stack", toggle=True)
        row.prop(sc_common, "load_preset", text="Load Stack", toggle=True)
        if sc_common.save_preset:
            self.__save(col, sc_common)
        elif sc_common.load_preset:
            self.__load(col, sc_common)

    @staticmethod
    def __save(col: UILayout, sc_common: PropertyGroup):
        col.separator()
        row = col.row(align=True)
        rspl = row.split(factor=.74, align=True)
        rspl.prop(sc_common, "save_to", text="")
        rspl.operator("stacks.del_text", text="", icon="X")
        rspl.operator("stacks.new_text", text="", icon="FILE_NEW")
        col.prop(sc_common, "overwrite", text="Overwrite")
        col.operator("stacks.preset_save", text="Save")

    @staticmethod
    def __load(col: UILayout, sc_common: PropertyGroup):
        col.separator()
        col.prop(sc_common, "load_from", text="")
        col.separator()
        col.operator("stacks.preset_load")


# --------------------------------------------------- OPERATORS LIST ---------------------------------------------------


class STACKS_UI_OpsList:
    """UI Layout: Stack Operators List Drawing"""
    def __init__(self, col: UILayout, stack_ob: PropertyGroup, stack_sc: PropertyGroup,
                 ob: Object, active_index: int, sc_common: PropertyGroup):

        self.__header(col, sc_common)
        if sc_common.op_list_closed:
            return

        self.__repeat(col, stack_ob)
        col.separator(factor=.3)
        row = col.row(align=True)
        self.__ulist(row, stack_sc, ob)
        ops = row.column()
        self.__slots_ops(ops, active_index)
        if len(stack_sc.ops) > 1:
            self.__slots_move(ops, active_index)

    @staticmethod
    def __header(col: UILayout, sc_common: PropertyGroup) -> None:
        """Stack Menu Header"""
        row = col.row(align=True)
        rcol1 = row.column(align=True)
        rcol1.prop(sc_common, "op_list_closed", text="", emboss=False,
                   icon="RIGHTARROW" if sc_common.op_list_closed else "DOWNARROW_HLT")
        rcol2 = row.column(align=True)
        rcol2.label(text="Stack Operators:")

    @staticmethod
    def __repeat(col: UILayout, stack_ob) -> None:
        """Repeat Stack Property"""
        col.prop(stack_ob, "repeat", text="Repeat")

    @staticmethod
    def __ulist(row: UILayout, stack_sc: PropertyGroup, ob: Object) -> None:
        """Operators UI List draw"""
        rcol = row.column()
        rcol.template_list("STACKS_UL_Stacks", "name", stack_sc, "ops", stack_sc, "ops_active",
                           rows=3 if len(ob.stacks) else 1)

    @staticmethod
    def __slots_ops(ops: UILayout, active_index: int) -> None:
        """Add/Remove Slots buttons"""
        bop_add = ops.operator("stacks.slot_add", text="", icon="ADD")
        bop_add.prop = f"stacks[{active_index}].ops"
        bop_add.active = f"stacks[{active_index}].ops_active"
        bop_add.source = "scene"
        bop_rem = ops.operator("stacks.slot_remove", text="", icon="REMOVE")
        bop_rem.prop = f"stacks[{active_index}].ops"
        bop_rem.active = f"stacks[{active_index}].ops_active"
        bop_rem.source = "scene"

    @staticmethod
    def __slots_move(ops: UILayout, active_index: int) -> None:
        """Move Slots Up/Down buttons"""
        bop_move_up = ops.operator("stacks.slot_ops_move", text="", icon="TRIA_UP")
        bop_move_up.st_index = active_index
        bop_move_up.direction = True
        bop_move_down = ops.operator("stacks.slot_ops_move", text="", icon="TRIA_DOWN")
        bop_move_down.st_index = active_index
        bop_move_down.direction = False


# --------------------------------------------------- OPERATORS TYPE ---------------------------------------------------


class STACKS_UI_OpsType:
    """UI Layout: Operators Type Menu drawing"""
    def __init__(self, col: UILayout, op: PropertyGroup, sc_common: PropertyGroup):
        self.__header(col, sc_common)
        if not sc_common.op_type_closed:
            self.__type(col, op)

    @staticmethod
    def __header(col: UILayout, sc_common: PropertyGroup) -> None:
        """Operator Type Menu Header"""
        row = col.row(align=True)
        rcol1 = row.column(align=True)
        rcol1.prop(sc_common, "op_type_closed", text="", emboss=False,
                   icon="RIGHTARROW" if sc_common.op_type_closed else "DOWNARROW_HLT")
        rcol2 = row.column(align=True)
        rcol2.label(text="Operator Type:")

    @staticmethod
    def __type(col: UILayout, op: PropertyGroup) -> None:
        """Operator Type Property"""
        box = col.box()
        rcol2 = box.column(align=True)
        rcol2.prop(op, "operator_type")
        if op.operator_type == 'SELECT':
            rcol2.prop(op, "ops_select")
        elif op.operator_type == 'HIDE':
            rcol2.prop(op, "ops_hide")
        elif op.operator_type == 'GENERATE':
            rcol2.prop(op, "ops_generate")
        elif op.operator_type == 'DEFORM':
            rcol2.prop(op, "ops_deform")
        elif op.operator_type == 'TRANSFORM':
            rcol2.prop(op, "ops_transform")
        elif op.operator_type == 'CLEANUP':
            rcol2.prop(op, "ops_cleanup")
        elif op.operator_type == 'NORMALS':
            rcol2.prop(op, "ops_normals")
        elif op.operator_type == 'ASSIGN':
            rcol2.prop(op, "ops_assign")
        elif op.operator_type == 'ADD':
            rcol2.prop(op, "ops_add")
        elif op.operator_type == 'FILL':
            rcol2.prop(op, "ops_fill")


# ---------------------------------------------------- INTERPOLATION ---------------------------------------------------


class STACKS_UI_Interpolate:
    """UI Layout: Interpolate Menu drawing"""
    def __init__(self, col: UILayout, op: PropertyGroup, sc_common: PropertyGroup):
        if not self.__is_valid(op):
            return

        self.__header(col, sc_common)
        if sc_common.op_intr_closed:
            return

        box = col.box()
        bcol = box.column(align=True)
        self.__type(bcol, op)
        if op.interp_type == 'RANDOM':
            self.__random(bcol, op)
        elif op.interp_type == "BEZIER":
            self.__bezier(bcol, op)

    @staticmethod
    def __is_valid(op: PropertyGroup) -> bool:
        """Can Operator use interpolation. Return True or False"""
        if op.operator_type == 'NONE':
            return False
        elif getattr(op, f"ops_{op.operator_type.lower()}") == 'NONE':
            return False
        elif op.operator_type in {'HIDE', 'NORMALS', 'ASSIGN'}:
            return False
        elif op.operator_type == 'SELECT' and op.ops_select not in {'RANDOM', 'MORE'}:
            return False
        return True

    @staticmethod
    def __header(col: UILayout, sc_common: PropertyGroup) -> None:
        """Operator Type Menu Header"""
        row = col.row(align=True)
        rcol1 = row.column(align=True)
        rcol1.prop(sc_common, "op_intr_closed", text="", emboss=False,
                   icon="RIGHTARROW" if sc_common.op_intr_closed else "DOWNARROW_HLT")
        bcol = row.column(align=True)
        bcol.label(text="Interpolation:")

    @staticmethod
    def __type(col: UILayout, op: PropertyGroup) -> None:
        """Interpolate Type Select Menu"""
        col.prop(op, "interpolate", text='Interpol')
        col.prop(op, "interp_type", text='Type')

    @staticmethod
    def __random(col: UILayout, op: PropertyGroup) -> None:
        """Random interpolation Menu"""
        col.separator()
        col.prop(op, "interp_seed", text='Seed')

    @staticmethod
    def __bezier(col: UILayout, op: PropertyGroup) -> None:
        """Bezier interpolation Menu"""
        col.prop(op, "interp_ease", text='Ease')
        col.separator()
        brow = col.row(align=True)
        brow.prop(op, "interp_ease_in", text='In')
        brow.prop(op, "interp_ease_out", text='Out')


# -------------------------------------------------- OPERATOR SETTINGS -------------------------------------------------


class STACKS_UI_OpSettings:
    """UI Layout: Operator Settings Menu drawing"""
    def __init__(self, ob: Object, col: UILayout, op: PropertyGroup,
                 sc_common: PropertyGroup, stack_ob: PropertyGroup):

        self.__header(col, sc_common)
        if sc_common.op_sets_closed:
            return

        box = col.box()
        bcol = box.column()
        self.__settings(ob, bcol, op, stack_ob)

    @staticmethod
    def __header(col: UILayout, sc_common: PropertyGroup) -> None:
        row = col.row(align=True)
        rcol1 = row.column(align=True)
        rcol1.prop(sc_common, "op_sets_closed", text="", emboss=False,
                   icon="RIGHTARROW" if sc_common.op_sets_closed else "DOWNARROW_HLT")
        rcol2 = row.column(align=True)
        rcol2.label(text="Operator Settings:")

    @staticmethod
    def __settings(ob: Object, col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        if op.operator_type == 'SELECT':
            STACKS_UI_OPS_Select(ob, col, op, stack_ob)
        elif op.operator_type == 'GENERATE':
            STACKS_UI_OPS_Generate(col, op, stack_ob)
        elif op.operator_type == 'DEFORM':
            STACKS_UI_OPS_Deform(col, op, stack_ob)
        elif op.operator_type == 'TRANSFORM':
            STACKS_UI_OPS_Transform(col, op, stack_ob)
        elif op.operator_type == 'CLEANUP':
            STACKS_UI_OPS_Cleanup(col, op)
        elif op.operator_type == 'NORMALS':
            STACKS_UI_OPS_Normals(col, op)
        elif op.operator_type == 'ASSIGN':
            STACKS_UI_OPS_Assign(ob, col, op)
        elif op.operator_type == 'ADD':
            STACKS_UI_OPS_Add(col, op, stack_ob)
        elif op.operator_type == 'FILL':
            STACKS_UI_OPS_Fill(col, op)


# ----------------------------------------------------- OPS SELECT -----------------------------------------------------


class STACKS_UI_OPS_Select:
    """UI Layout: Select Operators panels drawing"""
    def __init__(self, ob: Object, col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        """Select Operator Settings"""
        row = col.row(align=True)
        row.label(text="Edit Type:")
        row.separator()
        row.prop(op, 'sel_mode_verts', text="", emboss=True, icon='VERTEXSEL')
        row.prop(op, 'sel_mode_edges', text="", emboss=True, icon='EDGESEL')
        row.prop(op, 'sel_mode_faces', text="", emboss=True, icon='FACESEL')

        if op.ops_select == 'RANDOM':
            self.__random(col, op, stack_ob)
        elif op.ops_select == 'ALL':
            col.label(text="Select All")
        elif op.ops_select == 'DESELECT':
            col.label(text="Deselect All")
        elif op.ops_select == 'INVERT':
            col.label(text="Invert Selection")
        elif op.ops_select == 'LOOSE':
            col.label(text="Select Loose Geometry")
        elif op.ops_select == 'NON_MANIFOLD':
            col.label(text="Select Non-Manifold Geometry")
        elif op.ops_select == 'BOUNDARY':
            col.label(text="Select Boundary Loop")
        elif op.ops_select == 'SHARP':
            col.prop(op, 'sel_sharp')
        elif op.ops_select == 'MORE':
            col.alignment = 'CENTER'
            col.prop(op, 'sel_more', text="", emboss=True,
                     icon='ADD' if op.sel_more else 'REMOVE')
        elif op.ops_select == 'CUSTOM':
            self.__custom(col, op)
        elif op.ops_select == 'VGROUP':
            col.prop(op, "gen_subd_ngon", text="Clear Previous Selection")
            col.prop(op, "sel_rand_invert", text="Deselect", toggle=True)
            col.prop_search(op, "sel_vgroup", ob, "vertex_groups", text="Group")
        elif op.ops_select == 'BYSIDES':
            col.prop(op, "gen_ins_interp", text="Clear Selection")
            col.prop(op, "fill_holes", text="Vertices")
            col.prop(op, "sel_bysides_type")
            col.prop(op, "gen_subd_ngon", text="Extend")

    @staticmethod
    def __random(col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup) -> None:
        col.prop(op, 'sel_rand_invert', text="Invert")
        interp("SELECT", "RANDOM", 'sel_rand_ratio', col, op, stack_ob=stack_ob, label='Ratio')
        interp("SELECT", "RANDOM", 'sel_rand_seed', col, op, stack_ob=stack_ob, label='Seed')

    @staticmethod
    def __custom(col: UILayout, op: PropertyGroup) -> None:
        """Custom Select"""
        col.prop(op, "sel_cstm_clear_previous_selection")
        if not op.sel_cstm_clear_previous_selection:
            col.prop(op, "sel_cstm_deselect", toggle=True)
        col.prop(op, "orientation_type", text="Orientation")
        # col.prop(op, "sel_cstm_element_type")  # Not implemented yet
        if op.sel_cstm_element_type == "VERTS":
            col.prop(op, "sel_cstm_vert_type", text="Mode")
            if op.sel_cstm_vert_type in {"EDGENUM", "FACENUM"}:
                col.separator()
                row = col.row(align=True)
                row.prop(op, "sel_cstm_edge_facenum" if op.sel_cstm_vert_type == "EDGENUM" else "sel_cstm_face_vnum",
                         text=f"{dict({True: 'More or equal:', False: 'Less than:'})[op.gen_ins_outset]}")
                row.prop(op, "gen_ins_outset", text="", toggle=True, icon="UV_SYNC_SELECT")
                return
        # # Following is not implemented yet:
        # elif op.sel_cstm_element_type == "EDGES":
        #     col.prop(op, "sel_cstm_edge_type")
        #     if op.sel_cstm_edge_type == "LENGTH":
        #         col.prop(op, "sel_cstm_noise_threshold", text="Maximum Length")
        #         return
        #     elif op.sel_cstm_edge_type == "FACENUM":
        #         col.prop(op, "sel_cstm_edge_facenum", text="Adjacent Faces Number")
        #         return
        # elif op.sel_cstm_element_type == "FACES":
        #     col.prop(op, "sel_cstm_face_type")
        #     if op.sel_cstm_face_type == "VNUM":
        #         col.prop(op, "sel_cstm_face_vnum", text="Number of Vertices")
        #         return
        #     elif op.sel_cstm_face_type == "AREA":
        #         col.prop(op, "sel_cstm_noise_threshold", text="Maximum Face Area")
        #         return
        else:
            print("Unexpected custom selection element type")
            raise NotImplementedError

        col.prop(op, "sel_cstm_pivot", text="Pivot")
        if op.sel_cstm_vert_type in {"BELOW", "ABOVE"}:
            col.prop(op, "sel_cstm_axis")
            if op.sel_cstm_pivot == "MANUAL":
                axis = {"X": 0, "Y": 1, "Z": 2}[op.sel_cstm_axis]
                col.prop(op, "sel_cstm_center", index=axis)
            else:
                col.prop(op, "sel_cstm_target", text="Target")
        elif op.sel_cstm_vert_type == "SPHERE":
            col.prop(op, "sel_cstm_sphere_size", text="Size")
            if op.sel_cstm_pivot == "MANUAL":
                col.prop(op, "sel_cstm_center", text="Center")
            else:
                col.prop(op, "sel_cstm_target", text="Target")
        # # Following is not implemented yet:
        # col.prop(op, "sel_cstm_noise_threshold")
        # col.prop(op, "sel_rand_seed")
        # col.prop(op, "sel_cstm_noise_scale")
        # col.prop(op, "sel_cstm_noise_falloff")


# ---------------------------------------------------- OPS GENERATE ----------------------------------------------------


class STACKS_UI_OPS_Generate:
    """UI Layout: Generate Operators panels drawing"""
    def __init__(self, col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        if op.ops_generate == 'EXTRUDE':
            self.__extrude(col, op, stack_ob)
        elif op.ops_generate == 'SUBDIVIDE':
            self.__subdivide(col, op, stack_ob)
        elif op.ops_generate == 'BEVEL':
            self.__bevel(col, op, stack_ob)
        elif op.ops_generate == 'SOLIDIFY':
            self.__solidify(col, op, stack_ob)
        elif op.ops_generate == 'WIREFRAME':
            self.__wireframe(col, op, stack_ob)
        elif op.ops_generate == 'MIRROR':
            self.__mirror(col, op)
        elif op.ops_generate == 'DUPLICATE':
            self.__duplicate(col, op, stack_ob)
        elif op.ops_generate == 'SPLIT':
            self.__split(col, op)
        elif op.ops_generate == 'LOOPCUT':
            self.__loopcut(col, op)
        elif op.ops_generate == 'INSET':
            self.__inset(col, op, stack_ob)
        elif op.ops_generate == 'QUADS':
            self.__quads(col, op)
        elif op.ops_generate == 'BOOLEAN':
            self.__boolean(col, op)

    @staticmethod
    def __extrude(col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        """Generate Extrude"""
        col.prop(op, "gen_extr_ind", text="Individual Faces")
        if op.gen_extr_ind:
            interp("GENERATE", "EXTRUDE", "gen_extr_indval", col, op, stack_ob=stack_ob)
        else:
            col.prop(op, "pivot_point", text="Pivot")
            interp("GENERATE", "EXTRUDE", "gen_extr_value", col, op, stack_ob=stack_ob)

    @staticmethod
    def __subdivide(col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        """Generate Subdivide"""
        interp("GENERATE", "SUBDIVIDE", "gen_subd_cuts", col, op, stack_ob=stack_ob, label="Number Cuts")
        interp("GENERATE", "SUBDIVIDE", "gen_subd_smooth", col, op, stack_ob=stack_ob, label="Smooth")
        col.prop(op, "gen_subd_ngon", text="Create Ngons")
        col.prop(op, "gen_subd_quad", text="Quad Corner Type")
        col.prop(op, "gen_subd_fractal", text="Fractal")
        col.prop(op, "gen_subd_fr_norm", text="Fractal Along Normals")
        col.prop(op, "gen_subd_seed", text="Seed")

    @staticmethod
    def __bevel(col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        """Generate Bevel"""
        col.prop(op, "gen_b_affect", text="Affect")
        col.prop(op, "gen_b_off_type", text="Type")
        row = col.row(align=True)
        row.prop(op, "gen_b_clmp_ovrlp", text="Clamp Overlap")
        row.prop(op, "gen_b_loop_slide", text="Loop Slide")
        interp("GENERATE", "BEVEL", "gen_b_offset_pct" if op.gen_b_off_type == 'PERCENT' else "gen_b_offset",
               col, op, stack_ob=stack_ob)
        col.prop(op, "gen_b_segments", text="Segments")
        col.prop(op, "gen_b_profile", text="Profile")
        row = col.row(align=True)
        rcol = row.column(align=True)
        rcol.label(text='Miter Out:')
        rcol.prop(op, "gen_b_mtr_outer", text="")
        rcol = row.column(align=True)
        rcol.label(text='Miter In:')
        rcol.prop(op, "gen_b_mtr_inner", text="")
        if op.gen_b_mtr_inner == 'ARC':
            col.prop(op, "gen_b_spread", text="Spread")
        else:
            col.separator()
        row = col.row(align=True)
        rcol = row.column(align=True)
        rcol.label(text="Intersections:")
        rcol.prop(op, "gen_b_vmesh_met", text="")
        rcol = row.column(align=True)
        rcol.label(text="Face Strength:")
        rcol.prop(op, "gen_b_f_str_mode", text="")
        rcol.prop(op, "gen_b_hard_norm", text="Harden Normals")
        col.prop(op, "gen_b_material", text="Material Offset")
        row = col.row(align=True)
        row.prop(op, "gen_b_mark_seam", text="Mark Seam")
        row.prop(op, "gen_b_mark_sharp", text="Mark Sharp")

    @staticmethod
    def __solidify(col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        """Generate Solidify"""
        interp("GENERATE", "SOLIDIFY", "gen_solidify", col, op, stack_ob=stack_ob)

    @staticmethod
    def __wireframe(col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        """Generate Wireframe"""
        interp("GENERATE", "WIREFRAME", "gen_wrf_thick", col, op, stack_ob=stack_ob, label="Thickness")
        col.prop(op, "gen_wrf_offset", text="Offset")
        row = col.row(align=True)
        if op.gen_wrf_crease:
            row.prop(op, "gen_wrf_crease", text="")
            row.prop(op, "gen_wrf_crs_wght", text="Weight")
        else:
            row.prop(op, "gen_wrf_crease", text="Use Crease")
        col.prop(op, "gen_wrf_boundary", text="Boundary")
        col.prop(op, "gen_wrf_even", text="Even")
        col.prop(op, "gen_wrf_relative", text="Relative")
        col.prop(op, "gen_wrf_replace", text="Replace")

    @staticmethod
    def __mirror(col: UILayout, op: PropertyGroup):
        """Generate Mirror"""
        col.label(text="Axis Constraints:")
        row = col.row(align=True)
        row.prop(op, "gen_mir_constr_x", text="X", toggle=True)
        row.prop(op, "gen_mir_constr_y", text="Y", toggle=True)
        row.prop(op, "gen_mir_constr_z", text="Z", toggle=True)
        col.prop(op, "orientation_type", text="Orient")
        col.prop(op, "gen_mir_pivot", text="Pivot")
        if op.gen_mir_pivot == 'OBJECT':
            col.prop(op, "gen_mir_object", text="Object")
        elif op.gen_mir_pivot == 'MANUAL':
            col.prop(op, "gen_mir_center", text="Center Override")
        col.prop(op, "gen_mir_accurate", text="Accurate")

    @staticmethod
    def __duplicate(col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        """Generate Duplicate"""
        col.prop(op, "pivot_point", text="Pivot")
        col.prop(op, "gen_dupli_mode", text="Mode")
        col.prop(op, "orientation_type", text="Orient")
        interp("GENERATE", "DUPLICATE", "gen_grab", col, op, stack_ob=stack_ob)
        interp("GENERATE", "DUPLICATE", "gen_rotate", col, op, stack_ob=stack_ob, label="Rotate")
        interp("GENERATE", "DUPLICATE", "gen_scale", col, op, stack_ob=stack_ob, label="Scale")

    @staticmethod
    def __split(col: UILayout, op: PropertyGroup):
        """Generate Split"""
        col.prop(op, "gen_split_type", text="Type")

    @staticmethod
    def __loopcut(col: UILayout, op: PropertyGroup):
        """Generate Loop Cut"""
        col.prop(op, "gen_loop_falloff", text="Falloff")
        row = col.row(align=True)
        row.prop(op, "gen_loop_edge", text="Edge")
        row.operator('stacks.loopcut_set')
        col.prop(op, "gen_loop_cuts", text="Cuts")
        col.prop(op, "gen_loop_smooth", text="Smooth")

    @staticmethod
    def __inset(col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        """Generate Inset"""
        col.prop(op, "gen_ins_boundary", text="Boundary")
        col.prop(op, "gen_ins_even", text="Even Offset")
        col.prop(op, "gen_ins_relative", text="Relative Offset")
        col.prop(op, "gen_ins_edgerail", text="Edge Rail")
        interp("GENERATE", "INSET", "gen_ins_thick", col, op, stack_ob=stack_ob, label="Thickness")
        interp("GENERATE", "INSET", "gen_ins_depth", col, op, stack_ob=stack_ob, label="Depth")
        col.prop(op, "gen_ins_outset", text="Outset")
        col.prop(op, "gen_ins_selinset", text="Select Inset")
        col.prop(op, "gen_ins_individ", text="Individual")
        col.prop(op, "gen_ins_interp", text="Interpolate")

    @staticmethod
    def __quads(col: UILayout, op: PropertyGroup):
        """Generate Quads"""
        col.prop(op, "gen_tri_face", text="Face Threshold")
        col.prop(op, "gen_tri_shape", text="Shape Threshold")

    @staticmethod
    def __boolean(col: UILayout, op: PropertyGroup):
        """Generate Boolean"""
        col = col.column()
        col.label(text="Subject:")
        row = col.row(align=True)
        row.prop_enum(op, "gen_bool_subject", "SELECTION")
        row.prop_enum(op, "gen_bool_subject", "OBJECT")
        col = col.column()
        col.label(text="Operation:")
        row = col.row(align=True)
        row.prop_enum(op, "gen_bool_operation", "INTERSECT")
        row.prop_enum(op, "gen_bool_operation", "UNION")
        row.prop_enum(op, "gen_bool_operation", "DIFFERENCE")
        if op.gen_bool_subject == 'OBJECT':
            col.prop(op, "gen_bool_object", text="Object")
        col = col.column()
        col.label(text="Solver:")
        row = col.row(align=True)
        row.prop_enum(op, "gen_bool_solver", "FAST")
        row.prop_enum(op, "gen_bool_solver", "EXACT")
        if op.gen_bool_solver == 'FAST':
            col.prop(op, "gen_bool_overlap_threshold", text="Overlap")
        elif op.gen_bool_solver == 'EXACT':
            col.prop(op, "gen_extr_ind", text="Self Intersection")
            col.prop(op, "gen_b_hard_norm", text="Hole Tolerant")


# ----------------------------------------------------- OPS DEFORM -----------------------------------------------------


class STACKS_UI_OPS_Deform:
    """UI Layout: Deform Operators panels drawing"""
    def __init__(self, col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        if op.ops_deform == 'SPHERE':
            interp("DEFORM", "SPHERE", "sel_rand_ratio", col, op, stack_ob=stack_ob, label="Factor")
        elif op.ops_deform == 'RANDOMIZE':
            self.__randomize(col, op, stack_ob)
        elif op.ops_deform == 'SMOOTH':
            interp("DEFORM", "SMOOTH", "gen_subd_smooth", col, op, stack_ob=stack_ob, label="Factor")
        elif op.ops_deform == 'PUSH':
            interp("DEFORM", "PUSH", "gen_extr_indval", col, op, stack_ob=stack_ob, label="Factor")
        elif op.ops_deform == 'WARP':
            self.__warp(col, op)
        elif op.ops_deform == 'SHRINK':
            self.__shrink(col, op, stack_ob)
        elif op.ops_deform == 'SHEAR':
            self.__shear(col, op, stack_ob)

    @staticmethod
    def __randomize(col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        """Deform Randomize"""
        interp("DEFORM", "RANDOMIZE", "gen_extr_indval", col, op, stack_ob=stack_ob)
        col.prop(op, "sel_rand_ratio", text="Uniform")
        col.prop(op, "gen_subd_smooth", text="Normal")
        col.prop(op, "sel_rand_seed", text="Seed")

    @staticmethod
    def __warp(col: UILayout, op: PropertyGroup):
        """Deform Warp"""
        col.prop(op, "def_warp_angle1", text="Warp Angle")
        col.prop(op, "def_warp_angle2", text="Offset Angle")
        col.prop(op, "def_warp_min", text="Min")
        col.prop(op, "def_warp_max", text="Max")
        col.prop(op, "def_warp_center", text="Center")
        col.prop(op, "def_warp_rotate", text="Rotate")

    @staticmethod
    def __shrink(col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        """Deform Shrink/Fatten"""
        interp("DEFORM", "SHRINK", "def_shrink_fac", col, op, stack_ob=stack_ob)
        col.prop(op, "def_shrink_even", text="Offset Even")

    @staticmethod
    def __shear(col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        """Deform Shear"""
        interp("DEFORM", "SHEAR", "def_shrink_fac", col, op, stack_ob=stack_ob)
        col.prop(op, "orientation_type", text="Orientation")
        col.prop(op, "def_shear_axis", text="Orient Axis")
        col.prop(op, "def_shear_ax_ort", text="Axis Ortho")


# --------------------------------------------------- OPS TRANSFORM ----------------------------------------------------


class STACKS_UI_OPS_Transform:
    """UI Layout: Transform Operators panels drawing"""
    def __init__(self, col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        col.prop(op, "orientation_type", text="Orient")
        col.prop(op, "pivot_point", text="Pivot")
        if op.ops_transform == 'GRAB':
            interp("TRANSFORM", "GRAB", "gen_grab", col, op, stack_ob=stack_ob)
        elif op.ops_transform == 'ROTATE':
            interp("TRANSFORM", "ROTATE", "gen_rotate", col, op, stack_ob=stack_ob)
        elif op.ops_transform == 'SCALE':
            interp("TRANSFORM", "SCALE", "gen_scale", col, op, stack_ob=stack_ob)


# ---------------------------------------------------- OPS CLEAN UP ----------------------------------------------------


class STACKS_UI_OPS_Cleanup:
    """UI Layout: Clean Up Operators panels drawing"""
    def __init__(self, col: UILayout, op: PropertyGroup):
        if op.ops_cleanup == 'DELETE':
            col.prop(op, "cln_delete", text="Delete")
        elif op.ops_cleanup == 'DISSOLVE':
            self.__dissolve(col, op)
        elif op.ops_cleanup == 'LOOSE':
            self.__loose(col, op)
        elif op.ops_cleanup == 'DECIMATE':
            self.__decimate(col, op)
        elif op.ops_cleanup == 'MERGE':
            self.__merge(col, op)

    @staticmethod
    def __dissolve(col: UILayout, op: PropertyGroup):
        col.prop(op, "cln_dissolve", text="Delete")
        if op.cln_dissolve == 'LIMITED':
            col.prop(op, "sel_sharp", text="Limit Angle")
            col.prop(op, "gen_ins_boundary", text="Use Boundaries")

    @staticmethod
    def __loose(col: UILayout, op: PropertyGroup):
        row = col.row()
        row.prop(op, "sel_mode_verts", text="", icon="VERTEXSEL", toggle=True)
        row.prop(op, "sel_mode_edges", text="", icon="EDGESEL", toggle=True)
        row.prop(op, "sel_mode_faces", text="", icon="FACESEL", toggle=True)

    @staticmethod
    def __decimate(col: UILayout, op: PropertyGroup):
        col.prop(op, "cln_decimate")
        if op.cln_decimate == 'COLLAPSE':
            col.prop(op, "gen_b_profile", text='Ratio')
        elif op.cln_decimate == 'PLANAR':
            col.prop(op, "sel_sharp", text='Angel Limit')

    @staticmethod
    def __merge(col: UILayout, op: PropertyGroup):
        """Generate Merge"""
        col.prop(op, "cln_mrg_type", text="Type")
        if op.cln_mrg_type == 'BY_DISTANCE':
            col.prop(op, "cln_mrg_thresh", text="Thresh.")
            col.prop(op, "cln_mrg_unselect", text="Use Unselected")


# ---------------------------------------------------- OPS NORMALS ----------------------------------------------------


class STACKS_UI_OPS_Normals:
    """UI Layout: Normals Operators panels drawing"""
    def __init__(self, col: UILayout, op: PropertyGroup):
        if op.ops_normals == 'FLAT':
            col.label(text="Shade Flat")
        elif op.ops_normals == 'SMOOTH':
            col.label(text="Shade Smooth")
            row = col.row()
            row.prop(op, "gen_extr_ind", text="Auto-Smooth")
            row.prop(op, "sel_sharp", text="")
        elif op.ops_normals == 'FLIP':
            col.label(text="Flip Normals")
        elif op.ops_normals == 'OUTSIDE':
            col.label(text="Recalculate Normals Outside")
        elif op.ops_normals == 'INSIDE':
            col.label(text="Recalculate Normals Inside")
        elif op.ops_normals == 'MARKSHARP':
            col.prop(op, "gen_b_loop_slide", text="Mark Sharp")
        elif op.ops_normals == 'SHARP_CLEAR':
            col.label(text="Clear Edges Sharp")


# ---------------------------------------------------- OPS ASSIGN -----------------------------------------------------


class STACKS_UI_OPS_Assign:
    """UI Layout: Assign Operators panels drawing"""
    def __init__(self, ob: Object, col: UILayout, op: PropertyGroup):
        if op.ops_assign == "MATERIAL":
            self.__material(col, op)
        elif op.ops_assign == "SKIN":
            col.prop(op, "asn_crease_v", text="Skin Resize")
        elif op.ops_assign == "CREASE":
            col.prop(op, "asn_crease_v", text="Vertices Crease")
            col.prop(op, "asn_crease_e", text="Edges Crease")
        elif op.ops_assign == "BEVEL":
            col.prop(op, "asn_crease_v", text="Vertices Weight")
            col.prop(op, "asn_crease_e", text="Edges Weight")
        elif op.ops_assign == "SEAM":
            col.prop(op, "gen_b_loop_slide", text="Mark Seam", toggle=True)
        elif op.ops_assign == "SHARP":
            col.prop(op, "gen_b_loop_slide", text="Mark Sharp", toggle=True)
        elif op.ops_assign == 'VGROUP':
            self.__vgroup(ob, col, op)

    @staticmethod
    def __material(col: UILayout, op: PropertyGroup):
        col.prop(op, "asn_material", text="Material")
        col.operator("stacks.update", text="Assign")

    @staticmethod
    def __vgroup(ob: Object, col: UILayout, op: PropertyGroup):
        col.prop(op, "sel_rand_invert", text="Remove", toggle=True)
        row = col.row(align=True)
        row.prop_search(op, "sel_vgroup", ob, "vertex_groups", text="Group")
        row.operator("stacks.new_vgroup", text="", icon="FILE_NEW").op_index = op.index
        col.prop(op, "sel_weight", text="Weight")


# ------------------------------------------------------ OPS ADD -------------------------------------------------------


class STACKS_UI_OPS_Add:
    """UI Layout: Assign Operators panels drawing"""
    def __init__(self, col: UILayout, op: PropertyGroup, stack_ob: PropertyGroup):
        if op.ops_add in {"PLANE", "CUBE", "MONKEY"}:
            self.__plane_cube_monkey(col, op, op.ops_add, stack_ob)
        elif op.ops_add == "CIRCLE":
            self.__circle(col, op, op.ops_add, stack_ob)
        elif op.ops_add == "UVSPHERE":
            self.__uv_sphere(col, op, op.ops_add, stack_ob)
        elif op.ops_add == "ICOSPHERE":
            self.__ico_sphere(col, op, op.ops_add, stack_ob)
        elif op.ops_add == "CYLINDER":
            self.__cylinder(col, op, op.ops_add, stack_ob)
        elif op.ops_add == "CONE":
            self.__cone(col, op, op.ops_add, stack_ob)
        elif op.ops_add == "TORUS":
            self.__torus(col, op, op.ops_add, stack_ob)
        elif op.ops_add == "GRID":
            self.__grid(col, op, op.ops_add, stack_ob)

    @staticmethod
    def __transforms(col: UILayout, op: PropertyGroup, op_type: str, stack_ob: PropertyGroup):
        interp("ADD", op_type, "gen_grab", col, op, stack_ob=stack_ob, label="Location")
        interp("ADD", op_type, "gen_rotate", col, op, stack_ob=stack_ob, label="Rotation")
        interp("ADD", op_type, "gen_scale", col, op, stack_ob=stack_ob, label="Scale")

    def __plane_cube_monkey(self, col: UILayout, op: PropertyGroup, op_type: str, stack_ob: PropertyGroup):
        """Settings are the same for Plane, Cube and Monkey Primitives"""
        interp("ADD", op_type, "add_size", col, op, stack_ob=stack_ob, label="Size")
        self.__transforms(col, op, op_type, stack_ob)

    def __circle(self, col: UILayout, op: PropertyGroup, op_type: str, stack_ob: PropertyGroup):
        interp("ADD", op_type, "add_circ_verts", col, op, stack_ob=stack_ob, label="Vertices")
        interp("ADD", op_type, "add_radius", col, op, stack_ob=stack_ob, label="Radius")
        col.prop(op, "add_circ_fill", text="Fill")
        self.__transforms(col, op, op_type, stack_ob)

    def __uv_sphere(self, col: UILayout, op: PropertyGroup, op_type: str, stack_ob: PropertyGroup):
        interp("ADD", op_type, "add_circ_verts", col, op, stack_ob=stack_ob, label="Segments")
        interp("ADD", op_type, "add_sphr_rings", col, op, stack_ob=stack_ob, label="Ring Count")
        interp("ADD", op_type, "add_radius", col, op, stack_ob=stack_ob, label="Radius")
        self.__transforms(col, op, op_type, stack_ob)

    def __ico_sphere(self, col: UILayout, op: PropertyGroup, op_type: str, stack_ob: PropertyGroup):
        interp("ADD", op_type, "add_sphr_ico", col, op, stack_ob=stack_ob, label="Subdivisions")
        interp("ADD", op_type, "add_radius", col, op, stack_ob=stack_ob, label="Radius")
        self.__transforms(col, op, op_type, stack_ob)

    def __cylinder(self, col: UILayout, op: PropertyGroup, op_type: str, stack_ob: PropertyGroup):
        interp("ADD", op_type, "add_circ_verts", col, op, stack_ob=stack_ob, label="Vertices")
        interp("ADD", op_type, "add_radius", col, op, stack_ob=stack_ob, label="Radius")
        interp("ADD", op_type, "add_radius2", col, op, stack_ob=stack_ob, label="Depth")
        col.separator()
        col.prop(op, "add_circ_fill", text="Fill")
        self.__transforms(col, op, op_type, stack_ob)

    def __cone(self, col: UILayout, op: PropertyGroup, op_type: str, stack_ob: PropertyGroup):
        interp("ADD", op_type, "add_circ_verts", col, op, stack_ob=stack_ob, label="Vertices")
        interp("ADD", op_type, "add_radius", col, op, stack_ob=stack_ob, label="Radius 1")
        interp("ADD", op_type, "gen_ins_thick", col, op, stack_ob=stack_ob, label="Radius 2")
        interp("ADD", op_type, "add_sphr_ico", col, op, stack_ob=stack_ob, label="Depth")
        col.separator()
        col.prop(op, "add_circ_fill", text="Fill")
        self.__transforms(col, op, op_type, stack_ob)

    @staticmethod
    def __torus(col: UILayout, op: PropertyGroup, op_type: str, stack_ob: PropertyGroup):
        interp("ADD", op_type, "add_tor_seg_maj", col, op, stack_ob=stack_ob, label="Major Segments")
        interp("ADD", op_type, "add_tor_seg_min", col, op, stack_ob=stack_ob, label="Minor Segments")
        col.separator()
        col.prop(op, "add_tor_mode")
        interp("ADD", op_type, f"add_tor_rad{'_abso' if op.add_tor_mode == 'EXT_INT' else ''}_maj",
               col, op, stack_ob=stack_ob, label="Major Radius")
        interp("ADD", op_type, f"add_tor_rad{'_abso' if op.add_tor_mode == 'EXT_INT' else ''}_min",
               col, op, stack_ob=stack_ob, label="Minor Radius")
        interp("ADD", op_type, "gen_grab", col, op, stack_ob=stack_ob, label="Location")
        interp("ADD", op_type, "gen_rotate", col, op, stack_ob=stack_ob, label="Rotation")

    def __grid(self, col: UILayout, op: PropertyGroup, op_type: str, stack_ob: PropertyGroup):
        interp("ADD", op_type, "add_grid_x", col, op, stack_ob=stack_ob, label="X Subdivisions")
        interp("ADD", op_type, "add_grid_y", col, op, stack_ob=stack_ob, label="Y Subdivisions")
        interp("ADD", op_type, "add_size", col, op, stack_ob=stack_ob, label="Size")
        self.__transforms(col, op, op_type, stack_ob)


# ----------------------------------------------------- OPS FILL -------------------------------------------------------


class STACKS_UI_OPS_Fill:
    """UI Layout: Assign Operators panels drawing"""
    def __init__(self, col: UILayout, op: PropertyGroup):
        if op.ops_fill == 'FILL':
            col.prop(op, 'gen_subd_ngon', text='Beauty')
        elif op.ops_fill == 'GRIDFILL':
            self.__gridfill(col, op)
        elif op.ops_fill == 'BRIDGEEDGE':
            self.__bridgeedge(col, op)
        elif op.ops_fill == 'FILLHOLES':
            col.prop(op, "fill_holes", text="Sides")

    @staticmethod
    def __gridfill(col: UILayout, op: PropertyGroup) -> None:
        col.prop(op, 'gen_b_segments', text='Span')
        col.prop(op, 'sel_more', text='Offset')
        col.prop(op, 'gen_b_clmp_ovrlp', text='Simple Blending')

    @staticmethod
    def __bridgeedge(col: UILayout, op: PropertyGroup) -> None:
        col.prop(op, 'fill_bridge_type')
        col.prop(op, 'gen_extr_ind', text='Merge')
        col.prop(op, 'gen_b_profile', text='Merge Fac.')
        col.prop(op, 'gen_loop_smooth', text='Twist')
        col.prop(op, 'gen_subd_cuts', text='Cuts')
        col.prop(op, 'fill_bridge_interp')
        col.prop(op, 'fill_bridge_smooth', text='Smooth')
        col.prop(op, 'fill_bridge_profile', text='Profile')
        col.prop(op, 'gen_loop_falloff', text='Shape')


# ---------------------------------------------------- MAIN PANEL ------------------------------------------------------


class STACKS_PT_Panel(Panel):
    bl_label = 'Stacks'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Stacks'
    
    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context):
        """Main Panel Draw Function"""
        layout = self.layout
        ob = context.object
        sc = context.scene
        sc_common = sc.stacks_common
        col = layout.column()
        topmenu = STACKS_UI_TopMenu(ob, col, sc_common)
        ob = topmenu()  # If in EDITING ORIGINAL mode, continue drawing Stacks object parameters instead of original
        stacklist = STACKS_UI_StackList(col, ob)
        if stacklist():
            return
            
        stack_ob = ob.stacks_c[ob.stacks_active]
        stack_type = STACKS_UI_StackMenu(col, ob, stack_ob, sc_common, sc)
        stack_sc, active_index = stack_type()
        # col = layout.column(align=True)
        if stack_sc is None or active_index is None:
            STACKS_UI_Presets(col, sc_common)
            return

        if active_index >= len(sc.stacks):
            STACKS_UI_Presets(col, sc_common)
            return
        
        STACKS_UI_OpsList(col, stack_ob, stack_sc, ob, active_index, sc_common)
        if not len(stack_sc.ops):
            STACKS_UI_Presets(col, sc_common)
            return

        op = stack_sc.ops[stack_sc.ops_active]
        STACKS_UI_OpsType(col, op, sc_common)
        if stack_ob.repeat > 1:
            STACKS_UI_Interpolate(col, op, sc_common)
        STACKS_UI_OpSettings(ob, col, op, sc_common, stack_ob)
        # col = layout.column(align=True)
        STACKS_UI_Presets(col, sc_common)
            

classes = [
    STACKS_UL_Stacks,
    STACKS_UL_ObStacks,
    STACKS_PT_Panel,
]


def register():
    for cl in classes:
        register_class(cl)
        

def unregister():
    for cl in reversed(classes):
        unregister_class(cl)
        

if __name__ == '__main__':
    register()
