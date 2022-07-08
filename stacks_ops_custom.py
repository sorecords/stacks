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
from bpy.props import *
from bpy.utils import register_class, unregister_class
from typing import Set
from math import radians, pi

if __name__ == '__main__':
    try:
        # For PyCharm
        from stacks_support_common import *
        from stacks_support_custom import *
        from stacks_support import upd_ops
    except ModuleNotFoundError:
        # For Blender
        from stacks.stacks_support_common import *
        from stacks.stacks_support_custom import *
        from stacks.stacks_support import upd_ops
else:
    # For add-on
    from .stacks_support_common import *
    from .stacks_support_custom import *
    from .stacks_support import upd_ops

# --------------------------------------------------- CUSTOM SELECT ----------------------------------------------------


class STACKS_OT_CUSTOM_Select(Operator):
    """Custom Selection Operator"""
    bl_idname = "stacks.custom_select"
    bl_label = "Custom Select"
    clear_previous_selection: BoolProperty(name="Clear Previous Selection", default=False)
    deselect: BoolProperty(name="Deselect", default=False)
    element_type: EnumProperty(name="Element Type", items={
        ("VERTS", "Vertices", "Vertices", "VERTEXSEL", 0),
        ("EDGES", "Edges", "Edges", "EDGESEL", 1),
        ("FACES", "Faces", "Faces", "FACESEL", 2),
    }, default="VERTS")
    sel_mode_verts: BoolProperty(name="Element Type", default=True)
    sel_mode_edges: BoolProperty(name="Element Type", default=False)
    sel_mode_faces: BoolProperty(name="Element Type", default=False)
    vert_type: EnumProperty(name="Selection Type", items={
        ("BELOW", "Below", "Below", "SORT_ASC", 0),
        ("ABOVE", "Above", "Above", "SORT_DESC", 1),
        ("SPHERE", "Sphere", "Sphere", "SHADING_SOLID", 2),
        ("EDGENUM", "Edges Number", "Number of adjacent edges", "UV_EDGESEL", 3),
        ("FACENUM", "Faces Number", "Number of adjacent faces", "UV_FACESEL", 4),
    }, default="SPHERE")
    edge_type: EnumProperty(name="Selection Type", items={
        ("BELOW", "Below", "Below", "SORT_ASC", 0),
        ("ABOVE", "Above", "Above", "SORT_DESC", 1),
        ("SPHERE", "Sphere", "Sphere", "SHADING_SOLID", 2),
        ("LENGTH", "Length", "Length", "DRIVER_DISTANCE", 3),
        ("FACENUM", "Faces number", "Number of adjacent faces", "UV_EDGESEL", 4)
    }, default="LENGTH")
    face_type: EnumProperty(name="Selection Type", items={
        ("BELOW", "Below", "Below", "SORT_ASC", 0),
        ("ABOVE", "Above", "Above", "SORT_DESC", 1),
        ("SPHERE", "Sphere", "Sphere", "SHADING_SOLID", 2),
        ("VNUM", "Vertex number", "Number of vertices", 3),
        ("AREA", "Area", "Area", "FULLSCREEN_ENTER", 4)
    }, default="VNUM")
    axis: EnumProperty(name="Axis", items={
        ("X", "X", "X", "EVENT_X", 0),
        ("Y", "Y", "Y", "EVENT_Y", 1),
        ("Z", "Z", "Z", "EVENT_Z", 2),
    }, default="Z")
    pivot: EnumProperty(name="Pivot Point", items={
        ("MANUAL", "Manual", "Manual", "EMPTY_ARROWS", 0),
        ("OBJECT", "Object", "Object", "MESH_CUBE", 1),
    }, default="MANUAL")
    orientation: EnumProperty(name="Orientation", items={
        ("LOCAL", "Local", "Local", "ORIENTATION_LOCAL", 0),
        ("GLOBAL", "Global", "Global", "ORIENTATION_GLOBAL", 1),
    }, default="LOCAL")
    center: FloatVectorProperty(name="Center", default=(0, 0, 0))
    center_target: StringProperty(name="Target Object Name", default="")
    sphere_size: FloatProperty(name="Noise Threshold", default=1, min=0)
    noise_threshold: FloatProperty(name="Noise Threshold", default=0.1, min=0)
    noise_seed: IntProperty(name="Noise Seed", default=0, min=0)
    noise_scale: FloatProperty(name="Noise Scale", default=1, min=0)
    noise_falloff: FloatProperty(name="Noise Falloff", default=1, min=0.001)
    more_than: BoolProperty(name="More Than", default=False)
    edge_facenum: IntProperty(name="Number of Faces", default=1, min=0)
    face_vnum: IntProperty(name="Number of Vertices", default=3, min=0)

    def execute(self, context: Context) -> Set[str]:
        mode = getmode(context)
        setmode(context, "EDIT")
        if self.element_type == "VERTS":
            STACKS_CUSTOM_Select_Vertices(context, self)
        elif self.element_type == "EDGES":
            context.tool_settings.mesh_select_mode = (False, True, False)
            bpy.ops.stacks.warning(msg="Not Implemented Yet", type="WARNING")
            # STACKS_CUSTOM_Select_Edges(context, self)
        elif self.element_type == "FACES":
            context.tool_settings.mesh_select_mode = (False, False, True)
            bpy.ops.stacks.warning(msg="Not Implemented Yet", type="WARNING")
            # STACKS_CUSTOM_Select_Faces(context, self)
        setmode(context, "EDIT")

        setmode(context, mode)
        return {'FINISHED'}


class STACKS_OT_CUSTOM_Decimate(Operator):
    """Custom Decimate Operator"""
    bl_idname = "stacks.custom_decimate"
    bl_label = "Custom Select"
    limit_angle: FloatProperty(default=radians(30), min=0, max=pi, step=radians(10) * 100, subtype='ANGLE')

    def execute(self, context: Context) -> Set[str]:
        STACKS_CUSTOM_Decimate(context, self)
        return {'FINISHED'}

    def invoke(self, context: Context, event: Event) -> callable:
        return self.execute(context)


class STACKS_OT_CUSTOM_Boolean(Operator):
    """Custom Boolean Operator"""
    bl_idname = "stacks.custom_boolean"
    bl_label = "Custom Select"
    subject: EnumProperty(name="Subject", items={
        ("NONE", "None", "None", "BLANK1", 0),
        ("SELECTION", "Selection", "Selection", "BLANK1", 1),
        ("OBJECT", "Object", "Object", "BLANK1", 2),
    }, default="NONE")
    operation: EnumProperty(name="Subject", items={
        ("INTERSECT", "Intersect", "Intersect", "BLANK1", 0),
        ("UNION", "Union", "Union", "BLANK1", 1),
        ("DIFFERENCE", "Difference", "Difference", "BLANK1", 2),
    }, default="DIFFERENCE")
    object_name: StringProperty(default="")
    solver: EnumProperty(name="Solver", items={
        ("FAST", "Fast", "Fast", "BLANK1", 0),
        ("EXACT", "Exact", "Exact", "BLANK1", 1),
    }, default="FAST")
    overlap_threshold: FloatProperty(default=0.000001)
    self_intersection: BoolProperty(default=False)
    hole_tolerant: BoolProperty(default=False)

    def execute(self, context: Context) -> Set[str]:
        STACKS_CUSTOM_Boolean(context, self)
        return {'FINISHED'}

    def invoke(self, context: Context, event: Event) -> callable:
        return self.execute(context)


class STACKS_OT_NewVgroupPopup(Operator):
    """Create New Vertex Group and assign selection to it"""
    bl_idname = "stacks.new_vgroup"
    bl_label = "New Vertex Group"
    vg_name: bpy.props.StringProperty(name="Enter Name", default="Stacks Selection")
    op_index: IntProperty(default=0, options={'HIDDEN'})

    def draw(self, context: Context):
        layout = self.layout
        layout.prop(self, "vg_name")

    @staticmethod
    def __set_name(context: Context, vg_name: str) -> str:
        """Generate unique Text name with proper index"""
        num = 1
        vgroup_name = vg_name
        while vgroup_name in context.object.vertex_groups:
            vgroup_name = f"{vg_name} {num:02d}"
            num += 1
        return vgroup_name

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        ob = context.object
        sc = context.scene
        stack_index = ob.stacks_c[ob.stacks_active].stack_index
        stack = sc.stacks[stack_index]
        op = stack.ops[self.op_index]
        vg_name = self.__set_name(context, self.vg_name)

        vg = ob.vertex_groups.new(name=vg_name)
        ob.vertex_groups.active = vg

        live_update = bool(ob.stacks_common.live_update)
        ob.stacks_common.live_update = False
        op.sel_vgroup = vg_name
        ob.stacks_common.live_update = live_update

        mode = getmode(context)
        setmode(context, 'EDIT')
        bpy.ops.stacks.assign_vgroup(sel_weight=op.sel_weight, sel_vgroup=vg_name)
        setmode(context, mode)

        msg = f'Vertex Group "{vg_name}" has been added to {context.object.name}'
        self.report({'INFO'}, msg)
        return {'FINISHED'}

    def invoke(self, context: Context, event: Event) -> Set[str]:
        """Blender operators' predeclared invoke method"""
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class STACKS_OT_AssignVgroup(Operator):
    """Create New Vertex Group and assign selection to it"""
    bl_idname = "stacks.assign_vgroup"
    bl_label = "Assign"
    sel_weight: FloatProperty(default=1)
    sel_vgroup: StringProperty(default="")
    sel_remove: BoolProperty(default=False)

    def execute(self, context: Context) -> Set[str]:
        """Blender operators' predeclared execute method"""
        vgroups = context.object.vertex_groups
        context.scene.tool_settings.vertex_group_weight = self.sel_weight
        vg = vgroups[self.sel_vgroup]
        vgroups.active = vg
        if self.sel_remove:
            bpy.ops.object.vertex_group_remove_from()
        else:
            bpy.ops.object.vertex_group_assign()
        return {'FINISHED'}


classes = [
    STACKS_OT_CUSTOM_Select,
    STACKS_OT_CUSTOM_Decimate,
    STACKS_OT_CUSTOM_Boolean,
    STACKS_OT_NewVgroupPopup,
    STACKS_OT_AssignVgroup
]


def register():
    for cl in classes:
        register_class(cl)


def unregister():
    for cl in reversed(classes):
        unregister_class(cl)


if __name__ == '__main__':
    register()
