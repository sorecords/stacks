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


"""
TODO: Vertex group assignment needs exact stack index to work properly with multiple stacks
Blender 3.1+ add-on «Stacks». Collect Blender operators to stacks and execute them. Init module registers add-on
internal Blender classes.

FOR DEVELOPERS.
Adding other Blender Operators to the Stacks add-on must be performed in the following modules:
    stacks_props.py:
        - STACKS_PROP_Operator > operator_type > items.
          Operator's type. Use existing type or add your own.
          The new operators' type must be added to the "items" Set as a Tuple consisting of:
            - Enum ID (str), also used to define operator's subtype and executing class,
            - Name (str), to be shown in the Blender UI Enum menus,
            - Description (str), to be shown in the Blender UI hint with the mouse cursor above it,
            - Blender Icon ID (str), use "BLANK1" for empty icon,
            - Index ID (int), used to keep order when reloading project.
          Determines:
            - stacks_props > STACKS_PROP_Operator > f"ops_{STACKS_PROP_Operator.operator_type.lower()}":
              Operator property name
            - stacks_ui.py > STACKS_UI_OpsType > __type(): UI Enum property draw
            - stacks_exe.py: capitalized first str in items determines the first part of the Blender Operator
              executing class's name. Being set up in stacks_support.py > STACKS_Stack > __funcs() > __optype() call
            - stacks_constants > INTERPOLATED: first str in items determines operator type for parameters
              that are supposed to be interpolated (see below)

        - STACKS_PROP_Operator > f"ops_{STACKS_PROP_Operator.operator_type.lower()}" > items.
          Operator. Use existing subtype or add your own, the same way as for the operators_type.
          Settings are drawn in UI by stacks_ui.py and are used to execute Blender Operators by stacks_exe.py classes
          Determines:
            - stacks_ui.py > STACKS_UI_OpsType > __type(): UI Enum property draw
            - stacks_ui.py > f"class STACKS_UI_OPS_{STACKS_PROP_Operator.operator_type.capitalize()}":
              UI panel draw function of the Operator depending on this parameter's value
            - stacks_exe.py: capitalized first str in items determines the last part of the Blender Operator
              executing class's name. Being set up in stacks_support.py > STACKS_Stack > __funcs() > __opfunc() call
            - stacks_constants > INTERPOLATED: first str in items determines operator type for parameters
              that are supposed to be interpolated (see below)

        - STACKS_PROP_Operator > interp_...
          Define interpolation common behavior of the operators while executing stack iterations.
          Operator's type and subtype must be added to the stacks_constants.py > INTERPOLATE as described below
          in order to give an operator possibility to be affected by the interpolation

        - STACKS_PROP_Operator > value_..., angle_..., scale_...
          Determine min and max ranges for operators' certain properties while executing stack iterations.
          Relationships must be defined in stacks_constants.py > INTERPOLATE as an internal operator's Dict containing
          {operator_property: (min property, max property)}

        - STACKS_PROP_Operator > value_sync
          Determines if some Operator's multidimensional value is synced, e.g. Scale
          The exact property affected by this parameter is defined in the operator's UI drawing methods and
          executing classes

        - STACKS_PROP_Operator > *** (other properties)
          The properties from this class are used in the Blender UI to determine Blender operators behavior
          defined in the stacks_exe.py as described below. Use existing ones or add yours own.
          Keep in mind! The properties defined above sel_rand_ratio are reserved for the Stacks internal work;
          using them as operators parameters leads to conflicts. Please use the properties starting from
          sel_rand_ratio and below or add your own bpy.props Properties to this class if needed

    stacks_ui.py:
        - STACKS_UI_OpsType > __type()
          Draws operator type and operator subtype Enum Properties defined in stacks_props.py
        -  f"class STACKS_UI_OPS_{STACKS_PROP_Operator.operator_type.capitalize()}"
          Draws Operator settings. Commonly has several drawing functions for different operators subtypes

    stacks_exe.py:
        Defines classes which use add-on settings defined in stacks_props.py and drawn in UI by stacks_ui.py to
        determine original Blender Operators' settings while executing.
        Adding a new class:
            The class must:
             - inherit from stacks_exe.py > STACKS_Op abstract class;
             - define "operator" method taking no arguments and returning None;
             - the class name must consist of 2 parts:
               1. Capitalized STACKS_PROP_Operator.operator_type.items[any][0]
               2. Capitalized getattr(STACKS_PROP_Operator,
                                      f"ops_{STACKS_PROP_Operator.operator_type.lower()}").items[any][0]
               e.g. GenerateExtrude.
             The operator properties used in Blender Operators in operator(self): are taken from self.op attributes.
             To give user the ability to set them the same properties should be drawn in stacks_ui.py
             as described above.

    stacks_constants.py:
        INTERPOLATE:
        Dictionary defines minimum and maximum values properties for specified property of the certain operator of
        certain type to be used for interpolation while stack loop executing iteration.
        {"OPERATOR_TYPE":  # e.g. "GENERATE"
            {"OPERATOR_SUBTYPE:  # e.g. "EXTRUDE"
                {"property_1": ("min_value_1", "max_value_1")},
                {"property_2": ("min_value_2", "max_value_2"), __syncable},
            "}
        }
        Optional __syncable (always True) is used for the multidimensional properties to define
        if they can be syncable (affected by op.value_sync) or not.

EXAMPLE:
    To define completely new operator:
    1. Properties (stacks_props.py):
        1. Add new operator_type item to the stacks_props.STACKS_PROP_Operator.operator_type.items (or use existing)
        2. Create new operator subtype property using one of operator_type items
           stacks_props.STACKS_PROP_Operator.f"ops_{stacks_props.STACKS_PROP_Operator.operator_type.lower()}"
           (or use existing)
        3. Add new item to the operator subtype property items - this will be your operator
    2. UI (stacks_ui.py):
        1. Add operator type and subtype properties to stacks_ui.STACKS_UI_OpsType if they are not there already
        2. Add drawing operator_type class to STACKS_UI_OpSettings.__settings if it is not there already.
           You can use existing drawing operator_type class and add a drawing function with operator properties there
           or create the new one if needed.
    3. Execute (stacks_exe.py):
        1. Create new class with name f"{operator_type.capitalize()}{ops_`operator_type`.capitalize()}"
           (exact operator type and subtype values are stored in their items, the first str in each item)
        2. Define operator(self) method which takes properties from self.op (those you decided to use in UI for the
           operator) and use them for bpy.ops operators parameters.
        3. Consider the Blender context mode is automatically set to Edit Mode before operator starts, so if you need
           to perform anything in other modes be sure to manually set context mode to the one you need inside
           operator(self) method
    4. Interpolate (stacks_constant.py):
        1. If any parameters are supposed to be interpolated while executing stack in loop, they should be defined
           in INTERPOLATE dictionary as described above
"""


# ----------------------------------- Add-on ----------------------------------- ADD-ON

bl_info = {
    "name": "Stacks",
    "author": "Andrey Sokolov",
    "version": (1, 0, 0),
    "blender": (2, 90, 0),
    "location": "View 3D > N-Panel > Stacks",
    "description": "Create Operators Sequences",
    "warning": "",
    "wiki_url": "https://github.com/sorecords/stacks/blob/main/README.md",
    "tracker_url": "https://github.com/sorecords/stacks/issues",
    "category": "Mesh"
}


if __name__ == '__main__':
    import sys
    import os
    rootdir = os.path.dirname(os.path.realpath(__file__))
    if rootdir not in sys.path:
        sys.path.append(rootdir)
    try:
        # Pycharm import
        import stacks_props
        import stacks_ops
        import stacks_ops_custom
        import stacks_ui
    except ModuleNotFoundError:
        # Blender Text Editor import
        from stacks import stacks_props, stacks_ops, stacks_ops_custom, stacks_ui
else:
    # Add-on import
    from . import stacks_props, stacks_ops, stacks_ops_custom, stacks_ui


def register():
    stacks_props.register()
    stacks_ops.register()
    stacks_ops_custom.register()
    stacks_ui.register()
    

def unregister():
    stacks_ui.unregister()
    stacks_ops.unregister()
    stacks_ops_custom.unregister()
    stacks_props.unregister()
    

if __name__ == '__main__':
    register()
