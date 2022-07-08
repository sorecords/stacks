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

"""Blender «Stacks» add-on support for Operators, update functions, handlers, etc."""

from __future__ import annotations
import random
from bpy.types import Object, Scene, BlenderRNA, PropertyGroup, Context, Modifier, Mesh
from bpy.props import *
from bpy.utils import register_class
from bpy.ops import _BPyOpsSubModOp
from mathutils import Vector
from typing import List, Union, Tuple, Set, Dict
from bpy.app.handlers import frame_change_post as FrameChange
from _ctypes import PyObj_FromPtr as Pointer
from functools import wraps

if __name__ == '__main__':
    try:  # PyCharm import
        import stacks_exe
        from stacks_support_common import *
        from stacks_exe import STACKS_OpExec
        from stacks_constants import *
    except ModuleNotFoundError:  # Blender Text Editor import
        from . import stacks_exe
        from stacks.stacks_support_common import *
        from stacks.stacks_exe import STACKS_OpExec
        from stacks.stacks_constants import *
else:  # Add-on import
    from . import stacks_exe
    from .stacks_support_common import *
    from .stacks_exe import STACKS_OpExec
    from .stacks_constants import *


# ---------------------------------------------- UPD OBJECT SETUP SUPPORT ----------------------------------------------


class STACKS_ObjectSetup:
    """
    To be inherited by STACKS_ExecuteStacks
    Determines which object is used as Stacks Object and which as its Mesh reference
    """

    @staticmethod
    def __mesh_from_ref(context: Context, ref: Object) -> Mesh:
        """Get Mesh from Reference object if possible return None if not"""
        try:
            return bpy.data.meshes.new_from_object(ref, preserve_all_data_layers=True,
                                                   depsgraph=context.evaluated_depsgraph_get())
        except RuntimeError:
            return None

    def __iterable_copy(self, props_trg, props_src, prop: str) -> None:
        try:
            iterable_trg = getattr(props_trg, prop)
            iterable_src = getattr(props_src, prop)
            if type(iterable_trg) == str:
                return
            for s in iterable_src:
                index = len(iterable_trg)
                try:
                    iterable_trg.add()
                    iterable_trg[index].index = index
                except AttributeError as exp:
                    pass
                try:
                    setattr(iterable_trg, s, getattr(iterable_src, s))
                except AttributeError:
                    continue
                self.__iterable_copy(getattr(iterable_trg[index], iterable_src[index], s))
        except TypeError:
            return

    def __ob_copy(self, context: Context, ob: Object) -> Object:
        """Return a deep copy of the Object"""
        mesh = self.__mesh_from_ref(context, ob)
        if mesh is None:
            return None
        new = bpy.data.objects.new(ob.name, mesh)
        for a in dir(ob):
            if a.startswith(("__", "bl_")) or callable(getattr(ob, a)) or a in {"data", "name"}:
                continue
            try:
                setattr(new, a, getattr(ob, a))
            except AttributeError:
                self.__iterable_copy(new, ob, a)
        for src, trg in zip(ob.stacks, new.stacks):
            trg.stack = src.stack
        for src, trg in zip(ob.stacks_c, new.stacks_c):
            trg.stack_index = src.stack_index
        return new

    @staticmethod
    def __copy_modifiers(trg: Object, src: Object) -> None:
        """Copy modifiers from src object to trg object"""
        for sm in src.modifiers:
            try:
                tm = trg.modifiers.new(sm.name, sm.type)
                for a in dir(sm):
                    setattr_protected(tm, a, sm)
            except TypeError as exp:
                print(exp)
                continue

    @staticmethod
    def __copy_constraints(trg: Object, src: Object) -> None:
        """Copy modifiers from src object to trg object"""
        for sc in src.constraints:
            try:
                tc = trg.constraints.new(sc.type)
                for a in dir(sc):
                    setattr_protected(tc, a, sc)
            except TypeError as exp:
                print(exp)
                continue

    @staticmethod
    def __copy_animation_data(trg: Object, src: Object) -> None:
        """Copy Animation data from src object to trg object"""
        if src.animation_data is not None:
            ad = trg.animation_data_create()
            for a in dir(ad):
                setattr_protected(ad, a, src.animation_data)

    @staticmethod
    def __swap_names(new: Object, ob: Object) -> None:
        """Swap objects names and data names"""
        new.name, ob.name = ob.name, new.name
        new.data.name, ob.data.name = ob.data.name, new.data.name

    @staticmethod
    def __fix_ref_name(new: Object, ob: Object) -> None:
        """Fix original Object's name by adding constant SUFFIX to the New object name"""
        ob.name = new.name + SUFFIX
        ob.data.name = new.data.name + SUFFIX

    @staticmethod
    def __set_select_and_active(context: Context, new: Object, ob: Object) -> None:
        """Deselect the original Object, Select the new object and make it active"""
        ob.select_set(False)
        new.select_set(True)
        set_active_obj(context, new)

    def __make_ref(self, context: Context, ob: Object) -> Object:
        """
        Replace ob Object in the project with its deep copy. Use ob as the new object's reference.
        1. Switch to OBJECT mode
        2. Create a deep copy of the original Object.
        3. Set the original Object as the new Object ob_reference.
        4. Link the new Object to the same Scenes and Collections as the original one.
        5. Swap their names and data names.
        6. Fix original Object's name by adding the constant SUFFIX to the original name
        7. Select the new Object and deselect the original Object. Make the new Object active object.
        """
        new = self.__ob_copy(context, ob)
        if new is None:
            return None
        new.stacks_common.ob_reference = ob
        obj_col_link(ob, new)
        self.__copy_modifiers(new, ob)
        self.__copy_constraints(new, ob)
        self.__copy_animation_data(new, ob)
        self.__swap_names(new, ob)
        self.__fix_ref_name(new, ob)
        self.__set_select_and_active(context, new, ob)
        return new

    def __ob_ref(self, context: Context) -> Tuple[Object, Object]:
        """Return object and its reference (create a copy if it has no reference)"""
        ob = self.__make_ref(context, context.object) \
            if context.object.stacks_common.ob_reference is None \
            else context.object
        if ob is None:
            return None, None
        ref = ob.stacks_common.ob_reference
        ob.stacks_common.ob_stacks = None
        ref.stacks_common.ob_stacks = ob
        ref.stacks_common.ob_reference = None
        return ob, ref

    def __mesh_copy(self, context: Context, ob: Object, ref: Object) -> Tuple[Object, Object]:
        """Replace mesh data in the ob with mesh data from the ref"""
        mesh = self.__mesh_from_ref(context, ref)
        if mesh is None:
            return None, None
        d = ob.data
        ob.data = mesh
        bpy.data.meshes.remove(d)
        return ob, ref

    @staticmethod
    def __show_ref(sc: Scene, ob: Object, ref: Object) -> None:
        """Show or hide original reference Object"""
        if ob.stacks_common.show_reference:
            obj_col_link(ob, ref)
            obj_lock(ref, True)
            ref.use_fake_user = False
        elif ref.name in sc.objects:
            ref.use_fake_user = True
            obj_unlink(ref)

    def ob_ref(self, context: Context, sc: Scene) -> Object:
        """
        If this is the first time:
            1. Make copy of the original object
            2. Set the original object as new obj's reference
            3. Hide and protect original object
        Get initial Object data from the reference Object
        """
        setmode(context, 'OBJECT')
        ob, ref = self.__ob_ref(context)
        if ob is None or ref is None:
            return None, None
        ob, ref = self.__mesh_copy(context, ob, ref)
        if ob is None or ref is None:
            return None, None
        self.__show_ref(sc, ob, ref)
        return ob, ref


# ----------------------------------- CALCULATE OPERATORS' VALUES FOR INTERPOLATION ------------------------------------


class STACKS_Value:
    """
    Interpolation Feature.
    Storage for the initial value and a list of the interpolated values for the single Operator property.
    To be used as STACKS_Values's attribute.
    """

    def __init__(self, prop: str):
        self.prop = prop
        self.init = None
        self.values = []


class STACKS_Values:
    """
    Interpolation Feature.
    Acts as a list of STACKS_Value's.
    To be returned on STACKS_PropValues calls.
    """

    def __init__(self):
        pass

    def __iter__(self):
        return iter([getattr(self, p) for p in dir(self) if not p.startswith("__")])


class STACKS_PropValues:
    """
    Interpolation Feature.
    Get a list of Values for the Operator parameter during the interpolation between iterations
    """

    def __init__(self, op: PropertyGroup, repeat: int, optype: str, opfunc: str) -> None:
        self.op = op
        self.repeat = repeat
        self.propdict = INTERPOLATE[optype][opfunc]

    def __call__(self):
        """Sets up and returns STACKS_Values with STACKS_Value objects as attributes"""
        values = STACKS_Values()
        for i in range(self.repeat):
            num = 0
            for src, props in self.propdict.items():
                num += 1
                if not hasattr(values, src):
                    setattr(values, src, STACKS_Value(src))
                value = getattr(values, src)
                if value.init is None:
                    value.init = getattr(self.op, src)
                if self.op.interp_type == 'RANDOM':
                    value.values.append(self.__interp_random(props, i*num))
                else:
                    value.values.append(self.__interp_ease(props, i))
        return values

    def __interp_random(self, props: Tuple[str], ind: int) -> Union[float, Tuple[float, float, float]]:
        """
        Get list of the randomly interpolated values.

        args*::
        props:: ('min_val', 'max_val', __syncable/optional, always True/):
        ind:: iteration index
        """
        seed = self.op.interp_seed + ind
        val_min = getattr(self.op, props[0])
        val_max = getattr(self.op, props[1])
        try:
            len(val_min)
            if self.op.value_sync and len(props) > 2:
                random.seed(seed)
                seed += 1
                x = map_range(random.random(), 0, 1, val_min[0], val_max[0])
                if type(val_min[0]) == int:
                    x = int(x)
                return x, x, x
            else:
                random.seed(seed)
                seed += 1
                x = map_range(random.random(), 0, 1, val_min[0], val_max[0])
                random.seed(seed)
                seed += 1
                y = map_range(random.random(), 0, 1, val_min[1], val_max[1])
                random.seed(seed)
                seed += 1
                z = map_range(random.random(), 0, 1, val_min[2], val_max[2])
                if type(val_min[0]) == int:
                    x = int(x)
                    y = int(y)
                    z = int(z)
                return x, y, z
        except TypeError:
            random.seed(seed)
            seed += 1
            x = map_range(random.random(), 0, 1, val_min, val_max)
            if type(val_min) == int:
                x = int(x)
            return x

    def __interp_ease(self, props: Tuple[str], ind: int) -> Union[float, Tuple[float, float, float]]:
        """
        Get list of the values interpolated with Ease In, Ease Out ot Ease In/Out algorithms.

        args*::
        props:: ('min_val', 'max_val', __syncable/optional, always True/):
        ind:: iteration index
        """
        value = ind if self.op.interpolate == 'STRAIGHT' else self.repeat - ind
        v = value / self.repeat
        ease_in = self.op.interp_ease_in
        ease_out = self.op.interp_ease_out
        if self.op.interp_ease == 'INOUT':  # Ease In/Out
            x = (1 - v) * ease_in + v * ease_out if v <= 0.5 else v * ease_in + (1 - v) * ease_out
        elif self.op.interp_ease == 'IN':  # Ease In
            x = (1 - v) * ease_in + v * ease_out
        else:  # Ease Out
            x = v * ease_in + (1 - v) * ease_out
        val_min = getattr(self.op, props[0])
        val_max = getattr(self.op, props[1])
        try:
            len(val_min)
            if self.op.value_sync and len(props) > 2:
                x_norm = map_range(x, 0, 1, val_min[0], val_max[0])
                if type(val_min[0]) == int:
                    x_norm = int(x_norm)
                return x_norm, x_norm, x_norm
            else:
                minx, miny, minz = val_min
                maxx, maxy, maxz = val_max

                x_norm = map_range(x, 0, 1, minx, maxx)
                y_norm = map_range(x, 0, 1, miny, maxy)
                z_norm = map_range(x, 0, 1, minz, maxz)

                if type(val_min[0]) == int:
                    x_norm = int(x_norm)
                    y_norm = int(y_norm)
                    z_norm = int(z_norm)
                return x_norm, y_norm, z_norm

        except TypeError:
            x_norm = map_range(x, 0, 1, val_min, val_max)
            if type(val_min) == int:
                x_norm = int(x_norm)
            return x_norm


# --------------------------------------------------- SINGLE OPERATOR --------------------------------------------------


class STACKS_SingleOperator:
    """Single Operator Setup and Call"""
    def __init__(self, context: Context, op: PropertyGroup, stack: PropertyGroup,
                 optype: str = "", opfunc: str = "") -> None:
        self.context = context
        self.op = op
        self.stack = stack
        self.optype = optype  # Operator type used in Enum
        self.opfunc = opfunc  # Operator used in Enum
        self.repeat = self.stack.repeat  # Number of operator calls during stack execution
        self.stacktype = self.stack.type  # Enum in {'STACK', 'SELECT'}
        self.interptype = self.op.interp_type if self.stacktype == 'STACK' else None  # {'CONSTANT', 'BEZIER', 'RANDOM'}
        self.func = self.__func()
        self.repeatable = self.__repeatable()
        self.values = STACKS_PropValues(self.op, self.repeat, optype, opfunc)() if self.repeatable else None

    def __call__(self):
        return self.func()

    def __func(self) -> callable:
        """Return Preloaded Operator Function Ready to execute"""
        if self.stacktype == 'SELECT':
            return STACKS_OpExec(stacks_exe.SelectSet(self.context, self.op))
        else:
            operator = getattr(stacks_exe, f'{self.optype.capitalize()}{self.opfunc.capitalize()}')
            return STACKS_OpExec(operator(self.context, self.op))

    def __repeatable(self) -> bool:
        """Return True or False if function is repeatable or not"""
        return True if self.repeat > 1 \
                       and self.interptype != 'CONSTANT' \
                       and self.optype in INTERPOLATE.keys() \
                       and self.opfunc in INTERPOLATE[self.optype].keys() \
                       else False


# ------------------------------------------ SCENE'S SINGLE STACK OF OPERATORS -----------------------------------------


class STACKS_Stack:
    """Scene's single Stack of Operators"""

    def __init__(self, context: Context, stack: PropertyGroup, sc_stacks: PropertyGroup) -> None:
        self.type = 'STACK'
        self.context = context
        self.stack = stack
        self.repeat = self.stack.repeat
        self.sc_stacks = sc_stacks
        self.ops = self.sc_stacks[stack.stack_index].ops
        self.funcs = self.__funcs()

    def __funcs(self) -> List[STACKS_SingleOperator]:
        """Return list of STACKS_Operator, set Operators proper names"""
        funcs = []
        num = 0
        for op in self.ops:
            optype = self.__optype(op)
            opfunc = self.__opfunc(op, optype)
            op.name = self.__opname(optype, opfunc)  # Set Operator Name
            if not op.enabled or optype == 'NONE' or opfunc == 'SKIP':
                continue
            func = STACKS_SingleOperator(self.context, op, self.stack, optype=optype, opfunc=opfunc)
            funcs.append(func)
            num += 1
        return funcs

    @staticmethod
    def __optype(op: PropertyGroup) -> str:
        """Return str converted from Enum Operator type"""
        return op.operator_type

    @staticmethod
    def __opfunc(op: PropertyGroup, optype: str) -> str:
        """Return str converted from Enum Operator subtype"""
        return 'SKIP' if optype == 'NONE' else str(getattr(op, f'ops_{optype.lower()}'))

    @staticmethod
    def __opname(optype: str, opfunc: str) -> str:
        """
        Generate Operator's name from its capitalized type and subtype
        Return str "None" if the Operator's type is set to "NONE" or the Operator's subtype is set to "SKIP"
        """
        return "None" if optype == 'NONE' or opfunc == 'SKIP' else f'{optype.capitalize()} {opfunc.capitalize()}'


# ------------------------------------------ SCENE'S SINGLE STACK OF OPERATORS -----------------------------------------


class STACKS_StackSelect:
    """Single Stack"""

    def __init__(self, context: Context, stack: PropertyGroup) -> None:
        self.type = 'SELECT'
        self.context = context
        self.stack = stack
        self.repeat = self.stack.repeat
        self.funcs = [STACKS_SingleOperator(context, stack, stack)]


# --------------------------------------- EXECUTE CONTEXT OBJECT OPERATORS STACKS --------------------------------------


class STACKS_ExecuteStacks(STACKS_ObjectSetup):
    """
    Execute Operators Stacks
    """

    def __init__(self, context: Context):
        self.context = context
        if not self.live_update:
            return
        self.live_update = False
        self.sc = context.scene
        self.mode = getmode(context)
        self.ob, self.ref = self.ob_ref(self.context, self.sc)
        if self.ob is None:
            msg = "Can not create mesh from this type of object"
            bpy.ops.stacks.warning("INVOKE_DEFAULT", msg=msg, type="ERROR")
            self.live_update = True
            setmode(self.context, self.mode)
            return
        self._modifiers = self.modifiers
        self.__enable_modifiers(enable=False)
        self.ob_stacks = self.ob.stacks_c
        self.ob_active = self.ob.stacks_active
        self.sc_stacks = self.sc.stacks
        self.stacks = self._stacks()
        self.execute()
        self.restore()
        self.__enable_modifiers()

    @property
    def modifiers(self) -> Dict[Modifier, bool]:
        """Read-only. Return dict of object modifiers containing their enable status"""
        return {m: bool(m.show_viewport) for m in self.ob.modifiers}

    def __enable_modifiers(self, enable=True) -> None:
        """Enable/Disable modifiers according to its initial status"""
        for m, e in self._modifiers.items():
            m.show_viewport = e if enable else False

    @staticmethod
    def dummy(context: Context):
        pass

    def execute(self) -> None:
        """Execute Operators Stacks"""
        vl_update = _BPyOpsSubModOp._view_layer_update
        _BPyOpsSubModOp._view_layer_update = self.dummy
        for stack in self.stacks:
            for i in range(stack.repeat):
                for f in stack.funcs:
                    if f.repeatable:
                        for v in f.values:
                            setattr(f.op, v.prop, v.values[i])
                            self.sc.update_tag()
                    f()
        _BPyOpsSubModOp._view_layer_update = vl_update

    def restore(self) -> None:
        """Restore scene settings"""
        for stack in self.stacks:
            for f in stack.funcs:
                if f.repeatable:
                    for v in f.values:
                        setattr(f.op, v.prop, v.init)
        setmode(self.context, self.mode)
        self.live_update = True

    def _stacks(self) -> List[Union[STACKS_Stack, STACKS_StackSelect]]:
        """Return list of STACKS_Stack Classes for each stack"""
        stacks = []
        for ind, stack in enumerate(self.ob_stacks):
            if stack.enabled:
                if stack.type == 'SELECT':
                    st = STACKS_StackSelect(self.context, stack)
                elif len(self.sc_stacks) <= stack.stack_index:
                    continue
                else:
                    st = STACKS_Stack(self.context, stack, self.sc_stacks)
                stacks.append(st)
        return stacks

    @property
    def live_update(self) -> bool:
        return self.context.object.stacks_common.live_update

    @live_update.setter
    def live_update(self, enabled: bool) -> None:
        self.context.object.stacks_common.live_update = enabled


# --------------------------------------- UPDATERS FOR BPY.PROPS ---------------------------------------

def upd_ops(self, context):
    """Main Mesh Updater on any property change"""
    ob = context.object
    if ob.stacks_common.update_all:
        STACKS_ExecuteStacks(context)  # Execute Stacks on active object
        stacks = [stack.stack_index for stack in ob.stacks_c]  # Get active objects stacks
        active = context.view_layer.objects.active  # remember active object
        selected = context.selected_objects[:]  # remember selected objects
        mode = getmode(context)  # remember context mode
        setmode(context, "OBJECT")  # set object mode
        bpy.ops.object.select_all(action="DESELECT")  # deselect all objects

        for o in context.view_layer.objects:
            if o == active or not len([stack for stack in o.stacks_c if stack.stack_index in stacks]):
                # if object is active (already processed) or if it doesn't have the same stacks as the active one
                continue
            if len(o.stacks):
                context.view_layer.objects.active = o  # set object as active
                STACKS_ExecuteStacks(context)  # Execute Stacks on object
        context.view_layer.objects.active = active
        for o in selected:
            o.select_set(True)
        setmode(context, mode)
    else:
        STACKS_ExecuteStacks(context)


def upd_obj(self, context):
    """Update Object Stack Enum Property"""
    if context.object.stacks_common.live_update:
        ob_stack_index_update(self, context)
        if context.object:
            upd_ops(self, context)


def upd_save_preset(self, context):
    """Update Save Preset"""
    sc = context.scene.stacks_common
    if sc.save_preset and sc.load_preset:
        sc.load_preset = False


def upd_load_preset(self, context):
    """Update Load Preset"""
    sc = context.scene.stacks_common
    if sc.save_preset and sc.load_preset:
        sc.save_preset = False


def ob_stack_index_update(self, context):
    """Update Stacks Backup indices and Object Stacks names"""
    ob = context.object
    if ob is None:
        return
    stacks = ob.stacks
    bckups = ob.stacks_c
    for src, trg in zip(stacks, bckups):
        trg.stack_index = int(src.stack)
    for ob in bpy.context.scene.objects:
        if ob.type == 'MESH':
            for trg in ob.stacks:
                sc = bpy.context.scene
                trg.name = "None" if int(trg.stack) >= len(sc.stacks) \
                    else sc.stacks[int(trg.stack)].name


def upd_edit_original(self, context):
    """
    Update for Edit Original button
    Hide Stacks object, make original object editable
    """
    ob = context.object
    if ob.stacks_common.ob_reference is not None:
        # Edit Original has been just pressed in Stacks object
        assert ob.stacks_common.edit_reference is True
        ob.stacks_common.live_update = False
        ref = ob.stacks_common.ob_reference
        setmode(context, 'OBJECT')
        obj_col_link(ob, ref)
        ob.use_fake_user = True
        obj_unlink(ob)
        ref.hide_select = False
        obs_swap_names(ob, ref)
        set_active_obj(context, ref)
        setmode(context, 'EDIT')
    elif ob.stacks_common.ob_stacks is not None:
        assert ob.stacks_common.edit_reference is False
        stacksob = ob.stacks_common.ob_stacks
        setmode(context, 'OBJECT')
        obj_col_link(ob, stacksob)
        ob.use_fake_user = True
        stacksob.use_fake_user = False
        ob.hide_select = True
        obj_unlink(ob)
        set_active_obj(context, stacksob)
        obs_swap_names(ob, stacksob)
        stacksob.stacks_common.live_update = True
        STACKS_ExecuteStacks(context)
    else:
        raise ValueError("Stacks Unexpected Object")


def upd_show_original(self, context):
    """
    Update for Show Original button
    Link Reference object back to scene and rename it
    """
    ob = context.object
    props = ob.stacks_common
    ref = props.ob_reference
    setmode(context, 'OBJECT')
    if props.show_reference:
        obj_col_link(ob, ref)
        ref.name = ob.name + '_stacks_ref'
        ref.data.name = ob.data.name + '_stacks_ref'
        ref.hide_select = True
    else:
        obj_unlink(ref)

# ----------------------------------------- FRAME CHANGE HANDLER FOR ANIMATION -----------------------------------------


def STACKS_frame_change(scene: Scene, context: Context):
    """Main animation function for frame_change handler"""
    sc = context.scene
    # check if any operator is animated
    if not sc.animation_data or not sc.animation_data.action:
        return
    fcs = [fc.data_path for fc in sc.animation_data.action.fcurves
           if fc.data_path.startswith('stacks')]
    if not len(fcs):
        return

    # remember initial context
    vl = context.view_layer
    active_obj = vl.objects.active
    selected = list(context.selected_objects)
    mode = getmode(context)

    # process objects
    setmode(context, 'OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for ob in sc.objects:
        if not len(ob.stacks_c):
            continue
        stack_indices = [f"stacks[{st.stack_index}]" for st in ob.stacks_c]
        # check if animated scene stack is used in the object stacks
        stacks = False
        for ind in stack_indices:
            for fc in fcs:
                if fc.startswith(ind):
                    stacks = True
                    break
        if not stacks:
            continue
        # process object
        select = bool(ob.hide_select)
        viewport = bool(ob.hide_viewport)
        ob.hide_select = False
        ob.hide_viewport = False
        vl.objects.active = ob
        ob.select_set(True)
        upd_ops(sc, context)
        ob.hide_select = select
        ob.hide_viewport = viewport
        ob.select_set(False)
    # restore initial context
    vl.objects.active = active_obj
    for ob in selected:
        ob.select_set(True)
    setmode(context, mode)


# --------------------------------------------------- RENDER HANDLERS --------------------------------------------------


def STACKS_render_init(scene: Scene, context: Context):
    """To be used in render_init handler. Prevent crashes on original render"""
    sc = context.scene
    assert sc.stacks_common.render_init_id != ""
    assert sc.stacks_common.frame_change_id != ""
    assert sc.stacks_common.animatable
    frame_change = Pointer(int(sc.stacks_common.frame_change_id))
    while frame_change in FrameChange:
        FrameChange.remove(frame_change)


def STACKS_render_complete(scene: Scene, context: Context):
    """
    To be used in render_complete and render_cancel handlers.
    Set back frame_change handler after the render is finished and Stacks animation is turned back on
    """
    sc = context.scene
    assert sc.stacks_common.animatable

    def frame_change(sc_: Scene):
        return STACKS_frame_change(sc_, frame_change.context)

    frame_change.context = context
    sc.stacks_common.frame_change_id = str(id(frame_change))
    FrameChange.append(Pointer(int(sc.stacks_common.frame_change_id)))


# ------------------------------------------- SCENE STACK ITEMS ENUM UPDATE --------------------------------------------


class EnumStackItems:
    """
    Updating items for Scene Stacks Enum to be shown in Objects.
    Adding/Removing Scene and Object stack slots.
    """

    @staticmethod
    def _get_enum_items() -> Set[Tuple[str, str, str, str, int], Tuple]:
        """Generate Enum items for STACKS_PROP_ObStack `stack` property"""
        stacks = bpy.context.scene.stacks
        result = set()
        for s in stacks:
            result.add((f'{s.index:03d}', s.name, s.name, "DOT", s.index))
        assert len(result) == len(stacks)
        result.add((f'{len(stacks):03d}', "None", "None", "BLANK1", len(stacks)))
        return result

    @staticmethod
    def update_ob_enum() -> None:
        """Re-Register EnumProperty used in Objects to select stacks"""

        class STACKS_PROP_ObStack(PropertyGroup):
            """RE-REGISTERABLE! Object Single Stack"""
            name: StringProperty(default="Stack")
            index: IntProperty(default=0)
            stack: EnumProperty(
                name="Stack Select",
                items=EnumStackItems._get_enum_items(),
                default=f'{len(bpy.context.scene.stacks):03d}',
                update=upd_obj)

        register_class(STACKS_PROP_ObStack)
        Object.stacks = CollectionProperty(type=STACKS_PROP_ObStack)

    @staticmethod
    def update_project(op: str = 'ADD', old_index: int = 0) -> None:
        """
        Update settings in objects after add/remove scene stack
        args:
        op          : operator (enum in {'ADD', 'REMOVE'})
        old_index   : used for remove only to fix indices higher than it
        """
        for ob in bpy.context.scene.objects:
            if ob.type == 'MESH':
                for trg, src in zip(ob.stacks, ob.stacks_c):
                    if op == 'REMOVE':
                        if 0 > src.stack_index >= old_index:
                            src.stack_index -= 1
                    trg.stack = f'{src.stack_index:03d}'
                    sc = bpy.context.scene
                    trg.name = sc.stacks[src.stack_index].name if \
                        src.stack_index != len(sc.stacks) else "None"

    @staticmethod
    def project_stack_add() -> None:
        """
        Add new Scene Stack slot.
        Update Enum property for Objects.
        Update Objects' stack indices for internal and UI classes
        """
        props = bpy.context.scene.stacks
        props.add()
        index = len(props) - 1
        bpy.context.scene.stacks_active = props[index].index = index
        EnumStackItems.update_ob_enum()
        EnumStackItems.update_project()

    @staticmethod
    def project_stack_remove() -> None:
        """
        Remove Active Scene Stack from project.
        Update Enum property for Objects.
        Update Objects' stack indices for internal and UI classes
        """
        props = bpy.context.scene.stacks
        old_index = bpy.context.scene.stacks_active
        props.remove(old_index)
        for i, ar in enumerate(props):
            ar.index = i
        bpy.context.scene.stacks_active = old_index - 1 if old_index else 0
        EnumStackItems.update_ob_enum()
        EnumStackItems.update_project(op='REMOVE', old_index=old_index)

    @staticmethod
    def object_stack_add() -> None:
        """
        Add new Object Stack slot
        """
        stacks = bpy.context.object.stacks
        bckups = bpy.context.object.stacks_c
        stacks.add()
        bckups.add()
        index = len(stacks) - 1
        stacks[index].index = bckups[index].index = \
            bpy.context.object.stacks_active = index
        bckups[index].stack_index = len(bpy.context.scene.stacks)

    @staticmethod
    def object_stack_remove() -> None:
        """Remove Object Active Stack Slot"""
        stacks = bpy.context.object.stacks
        bckups = bpy.context.object.stacks_c
        old_index = bpy.context.object.stacks_active
        stacks.remove(old_index)
        bckups.remove(old_index)
        for i, ar in enumerate(stacks):
            ar.index = i
        for i, ar in enumerate(bckups):
            ar.index = i
        bpy.context.object.stacks_active = old_index - 1 if old_index else 0
        EnumStackItems.update_project()


class EnumStackItemsRegister(EnumStackItems):
    """
    Updates Scene Stacks Enum used in Objects.
    Update objects settings - indices and names.
    To be used in Updaters and Handlers
    """

    def __init__(self):
        self.update_ob_enum()
        self.update_project()


# ------------------------------------------ SLOTS ADD/REMOVE, MOVE UP/DOWN --------------------------------------------


class PropPathParse:
    """To be used in SlotAdd/SlotRemove Operators with multiple CollectionProperty() hierarchies"""

    @staticmethod
    def __prop_list(prop: str) -> List[str]:
        """Convert prop string into list of proper props strings"""
        splitted = prop.split('.')
        result = []
        short_name = ""
        append_to = 'main'
        for s in splitted:
            if "'[" in s or '"[' in s:
                short_name += s
                append_to = 'short'
            elif append_to == 'short':
                short_name += s
                if "]'" in s or ']"' in s:
                    append_to = 'main'
                    result.append(short_name)
                    short_name = ""
            elif "[" in s and "]" in s:
                split_index = s.split('[')
                result.append(split_index[0])
                result.append('...' + split_index[-1][:-1])
            else:
                result.append(s)
        return result

    def get_prop(self, source: Union[Object, Scene], prop: str) -> BlenderRNA:
        prop_list = self.__prop_list(prop)
        for p in prop_list:
            if p.startswith('...'):
                source = source[int(p[3:])]
            else:
                source = getattr(source, p)
        return source

    def set_prop(self, source: Union[Object, Scene], prop: str,
                 value: Union[int, float, Vector]) -> None:
        prop_list = self.__prop_list(prop)
        if len(prop_list) == 0:
            return
        elif len(prop_list) == 1:
            setattr(source, prop, value)
        else:
            num = 0
            while num < len(prop_list) - 1:
                if prop_list[num].startswith('...'):
                    source = source[int(prop_list[num][3:])]
                else:
                    source = getattr(source, prop_list[num])
                num += 1
            setattr(source, prop_list[-1], value)
            return source


# --------------------------------------------------- SLOT ADD/REMOVE --------------------------------------------------


class STACKS_SlotAdd(PropPathParse, EnumStackItems):
    """Slot Add"""

    def __init__(self, src: str, prop: str, active: str):
        if type(src) == Scene and prop == 'stacks':
            self.project_stack_add()
            return
        elif type(src) == Object and prop == 'stacks':
            self.object_stack_add()
            return
        props = self.get_prop(src, prop)
        props.add()
        index = len(props) - 1
        self.set_prop(src, active, index)
        props[index].index = index


class STACKS_SlotRemove(PropPathParse, EnumStackItems):
    """Slot Remove"""

    def __init__(self, src: str, prop: str, active: str):
        if type(src) == Scene and prop == 'stacks':
            self.project_stack_remove()
            return
        elif type(src) == Object and prop == 'stacks':
            self.object_stack_remove()
            return
        index = self.get_prop(src, active)
        props = self.get_prop(src, prop)
        props.remove(index)
        for i, ar in enumerate(props):
            ar.index = i
        new_index = index - 1 if index else 0
        self.set_prop(src, active, new_index)


# ------------------------------------------------- SLOTS MOVE UP/DOWN -------------------------------------------------


class STACKS_OpsSlotMove(PropPathParse, EnumStackItems):
    """Operators Slot Move"""

    def __init__(self, context: Context, st_index: int, direction: bool):
        stack = context.scene.stacks[st_index]
        active = int(stack.ops_active)
        if direction and active > 0:
            stack.ops.move(active, active - 1)
            stack.ops_active -= 1
        elif not direction and active < len(stack.ops) - 1:
            stack.ops.move(active, active + 1)
            stack.ops_active += 1
        EnumStackItemsRegister()


class STACKS_ObSlotMove(PropPathParse, EnumStackItems):
    """Object Slot Move"""

    def __init__(self, context: Context, direction: bool):
        ob = context.object
        stack = ob.stacks
        stack_c = ob.stacks_c
        active = ob.stacks_active
        if direction and active > 0:
            stack.move(active, active - 1)
            stack[active].index, stack[active - 1].index = \
                stack[active - 1].index, stack[active].index
            stack_c.move(active, active - 1)
            stack_c[active].index, stack_c[active - 1].index = \
                stack_c[active - 1].index, stack_c[active].index

            ob.stacks_active -= 1
        elif not direction and active < len(stack) - 1:
            stack.move(active, active + 1)
            stack[active].index, stack[active + 1].index = \
                stack[active + 1].index, stack[active].index
            stack_c.move(active, active + 1)
            stack_c[active].index, stack_c[active + 1].index = \
                stack_c[active + 1].index, stack_c[active].index
            ob.stacks_active += 1
