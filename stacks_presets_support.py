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

"""Blender «Stacks» Add-on algorithms for saving and loading Presets to/from Blender Text"""

import bpy
import addon_utils
from bpy.types import PropertyGroup, Context, Text, Material, Object, BlenderRNA, bpy_struct_meta_idprop
from typing import List, Tuple, Union
from mathutils import Euler, Vector
if __name__ == '__main__':
    try:  # PyCharm import
        from stacks_support import upd_ops
    except ModuleNotFoundError:  # Blender Text Editor import
        from stacks.stacks_support import upd_ops
else:  # Add-on import
    from .stacks_support import upd_ops


class STACKS_PresetsOps:

    def __init__(self, bl_text: Text) -> None:
        self.bl_text = bl_text
        self.addon_version = self.__addon_version()
        self.header = self.__header(self.addon_version)
        self.body = None
    
    @staticmethod
    def __addon_version() -> Tuple[int]:
        """Returns tuple with add-on's version"""
        return [a.bl_info['version'] for a in addon_utils.modules() if a.bl_info["name"] == "Stacks"][0]

    @staticmethod
    def __header(addon_version: Tuple[int]) -> str:
        """Returns standard 3 lines in the beginning of the Preset file"""
        line1 = "is_stacks_preset = True"
        line2 = "stack_type = 'OPERATORS'"
        line3 = f"stacks_version = {addon_version}"
        line4 = "import bpy"
        return f"{line1}\n{line2}\n{line3}\n\n{line4}\n\n"

    @staticmethod
    def __check_version(preset: Text, addon_version: Tuple[int]) -> bool:
        """Compare preset and addon versions"""
        prv = preset.stacks_version
        comp = tuple([p <= a for p, a in zip(prv, addon_version)])
        return all(comp)

    def __preset_check(self) -> Union[None, Text]:
        """Check if selected Blender Text is valid Stacks preset"""
        preset = self.bl_text.as_module()
        if not hasattr(preset, "is_stacks_preset"):
            msg = f"{self.bl_text.name} is not Stacks preset"
            bpy.ops.stacks.warning('INVOKE_DEFAULT', msg=msg, type='ERROR')
            return False
        elif preset.ops_number == 0:
            msg = f"No Operators found in {self.bl_text.name} preset"
            bpy.ops.stacks.warning('INVOKE_DEFAULT', msg=msg, type='ERROR')
            return False

        if not self.__check_version(preset, self.addon_version):
            msg = f"{self.bl_text.name} this preset has been created in the newer version of the Stacks add-on.\
\nIt can not be loaded. Please get newer add-on version"
            bpy.ops.stacks.warning('INVOKE_DEFAULT', msg=msg, type='ERROR')
        return preset

    def __add_op_as_str(self, op: PropertyGroup, index: int) -> None:
        """
        Convert Operator Stack, e.g. bpy.context.scene.stacks[0].ops[0]
        to string for .py file
        """
        self.body += (f'op{index:03d} = '+'{\n')
        for item in dir(op):
            if item.startswith(("__", "bl_", "id_", "rna_")) or callable(getattr(op, item)):
                continue
            value = getattr(op, item)
            if type(value) in {Euler, Vector}:
                value = tuple(value)
            elif type(type(value)) == bpy_struct_meta_idprop:  # for PointerProperty, e.g. Material, Object, etc.
                value_type = str(type(value)).replace("<class 'bpy.types.", "").replace("'>", "")
                value = f'"___stacks_{value_type.lower()}s.{value.name}"'
            elif type(value) == str:
                value = f'"{value}"'
            self.body += f'"{item}":{value},\n'
        self.body += '}\n\n'
    
    def __set_preset_body(self, ops: PropertyGroup, stack_name: str):
        self.body = self.header + f'stack_name = "{stack_name}"\n\n'
        for i, op in enumerate(ops):
            self.__add_op_as_str(op, i)
        self.body += f'ops_number = {len(ops)}'
    
    @staticmethod
    def __get_ops(preset: Text) -> List[dict]:
        """Return Operators Settings dictionaries"""
        return [getattr(preset, f'op{i:03d}') for i in range(preset.ops_number)]
    
    @staticmethod
    def __new_stack(context: Context) -> PropertyGroup:
        bpy.ops.stacks.slot_add()
        return context.scene.stacks[-1]
    
    @staticmethod
    def __add_ops(stack: PropertyGroup, ops_num: int) -> None:
        """Add operators Slots to the new scene Stack"""
        prop = f"stacks[{stack.index}].ops"
        active = f"stacks[{stack.index}].ops_active"
        for _ in range(ops_num):
            bpy.ops.stacks.slot_add(prop=prop, active=active, source="scene")

    @staticmethod
    def __get_bl_rna_item(item: str) -> BlenderRNA:
        """Get BlenderRNA from str item for PointerProperty, e.g. Object, Material, etc."""
        namelist = item.split(".")
        bl_type_name = namelist[0].replace("___stacks_", "")
        bl_type = getattr(bpy.data, bl_type_name)
        itemname = item.replace(namelist[0], "")[1:]
        if itemname in bl_type:
            return bl_type[itemname]
        else:
            msg = f'No {bl_type_name[:-1]} "{itemname}" found in project'
            bpy.ops.stacks.warning('INVOKE_DEFAULT', msg=msg, type="WARNING")
            return None

    def __set_ops(self, stack: PropertyGroup, ops: List[dict]) -> None:
        """Set up Operators values in the stack"""
        success = True
        num = 0
        for op in ops:
            for prop, item in op.items():
                try:
                    if type(item) == str and item.startswith("___"):
                        item = self.__get_bl_rna_item(item)
                    setattr(stack.ops[num], prop, item)
                except AttributeError:
                    success = False
                    continue
            num += 1
        if not success:
            preset = self.bl_text.as_module()
            msg = f"Some properties haven't been set correctly. The result may be different." \
                  f"It could probably happened because add-on and preset versions are different." \
                  f"Add-on version is {self.addon_version} and preset was saved in version {preset.stack_version}"
            bpy.ops.stacks.warning('INVOKE_DEFAULT', msg=msg, type="WARNING")
    
    def store_preset(self, ops: PropertyGroup, stack_name: str):
        self.bl_text.clear()
        self.__set_preset_body(ops, stack_name)
        self.bl_text.write(self.body)
        
    def load_preset(self, context: Context):
        ob = context.object
        live_update = ob.stacks_common.live_update
        ob.stacks_common.live_update = False
        preset = self.__preset_check()
        if not preset:
            return
        ops = self.__get_ops(preset)
        stack = self.__new_stack(context)
        self.__add_ops(stack, preset.ops_number)
        self.__set_ops(stack, ops)
        context.scene.stacks[-1].name = preset.stack_name
        ob.stacks_common.live_update = live_update
        upd_ops(self, context)
