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

"""Blender «Stacks» add-on Properties"""

import bpy
from math import pi, radians
from bpy.types import PropertyGroup, Object, Scene, Text, Material
from bpy.props import *
from bpy.utils import register_class, unregister_class
from bpy.app.handlers import persistent, \
    render_init as RenderInit, \
    render_complete as RenderComplete, \
    frame_change_post as FrameChange, \
    render_cancel as RenderCancel, \
    depsgraph_update_post as DepsgraphUpdate, \
    load_post as LoadPost
from _ctypes import PyObj_FromPtr as Pointer

if __name__ == '__main__':
    try:  # PyCharm import
        from stacks_support import EnumStackItemsRegister, upd_ops, upd_obj, upd_edit_original, upd_show_original, \
            upd_save_preset, upd_load_preset, STACKS_frame_change, STACKS_render_complete, STACKS_render_init
    except ModuleNotFoundError:  # Blender Text Editor import
        from stacks.stacks_support import EnumStackItemsRegister, upd_ops, upd_obj, upd_edit_original, \
            upd_show_original, upd_save_preset, upd_load_preset, STACKS_frame_change, STACKS_render_complete, \
            STACKS_render_init
else:  # Add-on import
    from .stacks_support import EnumStackItemsRegister, upd_ops, upd_obj, upd_edit_original, upd_show_original, \
        upd_save_preset, upd_load_preset, STACKS_frame_change, STACKS_render_complete, STACKS_render_init


# ------------------------------------------------- UPDATERS/HANDLERS --------------------------------------------------

@persistent
def stacks_enum_register(self, context):
    ob = context.object
    live_update = bool(ob.stacks_common.live_update)
    ob.stacks_common.live_update = False
    EnumStackItemsRegister()
    ob.stacks_common.live_update = live_update


@persistent
def STACKS_animatable(self, context):
    """Updater for Animatable button"""
    sc = context.scene

    def anim(scene: Scene):
        return STACKS_frame_change(scene, anim.context)

    def complete(scene: Scene):
        return STACKS_render_complete(scene, complete.context)

    def r_init(scene: Scene):
        return STACKS_render_init(scene, r_init.context)

    anim.context = context
    complete.context = context
    r_init.context = context

    if sc.stacks_common.animatable:
        sc.stacks_common.frame_change_id = str(id(anim))
        sc.stacks_common.render_complete_id = str(id(complete))
        sc.stacks_common.render_init_id = str(id(r_init))
        FrameChange.append(Pointer(int(sc.stacks_common.frame_change_id)))
        RenderCancel.append(Pointer(int(sc.stacks_common.render_complete_id)))
        RenderComplete.append(Pointer(int(sc.stacks_common.render_complete_id)))
        RenderInit.append(Pointer(int(sc.stacks_common.render_init_id)))
    else:
        if not sc.stacks_common.frame_change_id \
                or not sc.stacks_common.render_complete_id \
                or not sc.stacks_common.render_init_id:
            return
        anim = Pointer(int(sc.stacks_common.frame_change_id))
        complete = Pointer(int(sc.stacks_common.render_complete_id))
        r_init = Pointer(int(sc.stacks_common.render_init_id))
        while anim in FrameChange:
            FrameChange.remove(anim)
        while complete in RenderCancel:
            RenderCancel.remove(complete)
        while complete in RenderComplete:
            RenderComplete.remove(complete)
        while r_init in RenderInit:
            RenderInit.remove(r_init)


@persistent
def STACKS_on_load(self, context):
    EnumStackItemsRegister()
    if STACKS_on_load in DepsgraphUpdate:
        if bpy.context.scene.stacks_common.animatable:
            STACKS_animatable(self, bpy.context)
        while STACKS_on_load in DepsgraphUpdate:
            DepsgraphUpdate.remove(STACKS_on_load)
    elif STACKS_on_load in LoadPost:
        if bpy.context.scene.stacks_common.animatable:
            STACKS_animatable(self, bpy.context)


# ------------------------------------------------------ OPERATOR ------------------------------------------------------


class STACKS_PROP_Operator(PropertyGroup):
    """Single Operator Settings"""
    name: StringProperty(default="Operator")
    index: IntProperty(default=0)
    enabled: BoolProperty(default=True, options={'HIDDEN'}, update=upd_ops)
    operator_type: EnumProperty(name='Type', items={
        ('NONE', 'None', 'None', 'BLANK1', 0),
        ('SELECT', 'Select', 'Select', 'RESTRICT_SELECT_ON', 1),
        ('HIDE', 'Hide', 'Hide', 'HIDE_OFF', 2),
        ('GENERATE', 'Generate', 'Generate', 'VIEW_PERSPECTIVE', 3),
        ('DEFORM', 'Deform', 'Deform', 'OUTLINER_OB_GREASEPENCIL', 4),
        ('TRANSFORM', 'Transform', 'Transform', 'EMPTY_DATA', 5),
        ('CLEANUP', 'Cleanup', 'Cleanup', 'BRUSH_DATA', 6),
        ('NORMALS', 'Normals', 'Normals', 'SHADING_RENDERED', 7),
        ('ASSIGN', 'Assign', 'Assign', 'IMPORT', 8),
        ('ADD', 'Add Primitive', 'Add Primitive', 'MESH_CUBE', 9),
        ('FILL', 'Fill', 'Fill', 'SNAP_FACE', 10)
    }, default='NONE', options={'HIDDEN'}, update=upd_ops)
    ops_select: EnumProperty(name='Select', items={
        ('SKIP', 'Skip', 'Skip', 'BLANK1', 0),
        ('ALL', 'All', 'All', 'SELECT_EXTEND', 1),
        ('NONE', 'None', 'None', 'SELECT_SET', 2),
        ('RANDOM', 'Random', 'Random', 'STICKY_UVS_DISABLE', 3),
        ('SHARP', 'Sharp', 'Sharp', 'HANDLE_VECTOR', 4),
        ('INVERT', 'Invert', 'Invert', 'ARROW_LEFTRIGHT', 5),
        ('MORE', 'More', 'More', 'FORCE_CHARGE', 6),
        ('LOOSE', 'Loose', 'Loose Geometry', 'NORMALS_VERTEX', 7),
        ('NONMANIFOLD', 'Non Manifold', 'Non Manifold', 'OUTLINER_DATA_META', 8),
        ('BOUNDARY', 'Boundary Loop', 'Boundary Loop', 'OBJECT_HIDDEN', 9),
        ('CUSTOM', 'Custom', 'Custom', 'SETTINGS', 10),
        ('VGROUP', 'Vertex Group', 'Vertex Group', 'GROUP_VERTEX', 11),
        ('INTERIOR', 'Interior Faces', 'Interior Faces', 'MOD_TRIANGULATE', 12),
        ('BYSIDES', 'Faces By Sides', 'Faces By Sides', 'SNAP_VOLUME', 13)
    }, default='SKIP', options={'HIDDEN'}, update=upd_ops)
    ops_hide: EnumProperty(name='Hide', items={
        ('SKIP', 'Skip', 'Skip', 'BLANK1', 0),
        ('SELECTED', 'Selected', 'Selected', 'SELECT_EXTEND', 1),
        ('UNSELECTED', 'Unselected', 'Unselected', 'SELECT_SUBTRACT', 2),
        ('REVEAL', 'Reveal', 'Reveal', 'SELECT_DIFFERENCE', 3),
    }, default='SKIP', options={'HIDDEN'}, update=upd_ops)
    ops_generate: EnumProperty(name='Generate', items={
        ('SKIP', 'Skip', 'Skip', 'BLANK1', 0),
        ('EXTRUDE', 'Extrude', 'Extrude', 'FACE_MAPS', 1),
        ('SUBDIVIDE', 'Subdivide', 'Subdivide', 'MOD_LATTICE', 2),
        ('BEVEL', 'Bevel', 'Bevel', 'MOD_BEVEL', 3),
        ('SOLIDIFY', 'Solidify', 'Solidify', 'MOD_SOLIDIFY', 4),
        ('WIREFRAME', 'Wireframe', 'Wireframe', 'MOD_WIREFRAME', 5),
        ('MIRROR', 'Mirror', 'Mirror', 'MOD_MIRROR', 6),
        ('DUPLICATE', 'Duplicate', 'Duplicate', 'DUPLICATE', 7),
        ('SPLIT', 'Split', 'Split', 'MOD_EDGESPLIT', 8),
        ('LOOPCUT', 'Loop Cut', 'Loop Cut', 'MOD_MULTIRES', 9),
        ('INSET', 'Inset', 'Inset', 'FULLSCREEN_EXIT', 10),
        ('TRIANGULATE', 'Triangulate', 'Triangulate', 'MOD_TRIANGULATE', 11),
        ('QUADS', 'To Quads', 'To Quads', 'IMGDISPLAY', 12),
        ('POKE', 'Poke', 'Poke', 'DECORATE_ANIMATE', 13),
        ('BOOLEAN', 'Boolean', 'Boolean', 'MOD_BOOLEAN', 14)
    }, default='SKIP', options={'HIDDEN'}, update=upd_ops)
    ops_deform: EnumProperty(name='Deform', items={
        ('SKIP', 'Skip', 'Skip', 'BLANK1', 0),
        ('SPHERE', 'To Sphere', 'To Sphere', 'MESH_UVSPHERE', 1),
        ('RANDOMIZE', 'Randomize', 'Randomize', 'BOIDS', 2),
        ('SMOOTH', 'Smooth', 'Smooth', 'MOD_SMOOTH', 3),
        ('SHRINK', 'Shrink/Fatten', 'Shrink/Fatten', 'FULLSCREEN_EXIT', 4),
        ('PUSH', 'Push/Pull', 'Push/Pull', 'META_DATA', 5),
        ('WARP', 'Warp', 'Warp', 'MOD_WARP', 6),
        ('SHEAR', 'Shear', 'Shear', 'MOD_LATTICE', 7),
    }, default='SKIP', options={'HIDDEN'}, update=upd_ops)
    ops_transform: EnumProperty(name='Transform', items={
        ('GRAB', 'Grab', 'Grab', 'ARROW_LEFTRIGHT', 0),
        ('ROTATE', 'Rotate', 'Rotate', 'FILE_REFRESH', 1),
        ('SCALE', 'Scale', 'Scale', 'MOD_LENGTH', 2),
    }, default='GRAB', options={'HIDDEN'}, update=upd_ops)
    ops_cleanup: EnumProperty(name='Delete', items={
        ('SKIP', 'Skip', 'Skip', 'BLANK1', 0),
        ('DELETE', 'Delete', 'Delete', 'X', 1),
        ('DISSOLVE', 'Dissolve', 'Dissolve', 'SNAP_MIDPOINT', 2),
        ('DECIMATE', 'Decimate', 'Geometry', 'MOD_DECIM', 3),
        ('LOOSE', 'Loose Geometry', 'Delete', 'NORMALS_VERTEX', 4),
        ('MERGE', 'Merge', 'Merge', 'AUTOMERGE_ON', 5),
    }, default='SKIP', options={'HIDDEN'}, update=upd_ops)
    ops_normals: EnumProperty(name='Shading', items={
        ('SKIP', 'Skip', 'Skip', 'BLANK1', 0),
        ('FLAT', 'Shade Flat', 'Shade Flat', 'MESH_PLANE', 1),
        ('SMOOTH', 'Shade Smooth', 'Shade Smooth', 'MESH_CIRCLE', 2),
        ('FLIP', 'Flip Normals', 'Flip Normals', 'FILE_TICK', 3),
        ('OUTSIDE', 'Recalculate Outside', 'Normals', 'FULLSCREEN_ENTER', 4),
        ('INSIDE', 'Recalculate Inside', 'Normals', 'FULLSCREEN_EXIT', 5),
        ('MARKSHARP', 'Mark/Clear Sharp', 'Edges', 'SHARPCURVE', 6),
    }, default='SKIP', options={'HIDDEN'}, update=upd_ops)
    ops_assign: EnumProperty(name='Assign', items={
        ('SKIP', 'Skip', 'Skip', 'BLANK1', 0),
        ('MATERIAL', 'Material', 'Material', 'NODE_MATERIAL', 1),
        ('BEVEL', 'Bevel', 'Bevel', 'MOD_BEVEL', 2),
        ('CREASE', 'Crease', 'Crease', 'ROOTCURVE', 3),
        ('SKIN', 'Skin', 'For Skin Modifier', 'MOD_SKIN', 4),
        ('SEAM', 'Seam', 'Mark UV Seam', 'DRIVER_DISTANCE', 5),
        ('SHARP', 'Sharp', 'Mark Sharp', 'SHARPCURVE', 6),
        ('VGROUP', 'Vertex Group', 'Vertex Group', 'GROUP_VERTEX', 7)
    }, default='SKIP', options={'HIDDEN'}, update=upd_ops)
    ops_add: EnumProperty(name='Add Primitive', items={
        ('SKIP', 'Skip', 'Skip', 'BLANK1', 0),
        ('PLANE', 'Plane', 'Plane', 'MESH_PLANE', 1),
        ('CUBE', 'Cube', 'Cube', 'MESH_CUBE', 2),
        ('CIRCLE', 'Circle', 'Circle', 'MESH_CIRCLE', 3),
        ('UVSPHERE', 'UV Sphere', 'UV Sphere', 'MESH_UVSPHERE', 4),
        ('ICOSPHERE', 'Ico Sphere', 'Ico Sphere', 'MESH_ICOSPHERE', 5),
        ('CYLINDER', 'Cylinder', 'Cylinder', 'MESH_CYLINDER', 6),
        ('CONE', 'Cone', 'Cone', 'MESH_CONE', 7),
        ('TORUS', 'Torus', 'Torus', 'MESH_TORUS', 8),
        ('GRID', 'Grid', 'Grid', 'MESH_GRID', 9),
        ('MONKEY', 'Monkey', 'Monkey', 'MESH_MONKEY', 10),
    }, default='SKIP', options={'HIDDEN'}, update=upd_ops)
    ops_fill: EnumProperty(name='Fill', items={
        ('SKIP', 'Skip', 'Skip', 'BLANK1', 0),
        ('EDGEFACE', 'Edge/Face', 'Edge/Face', 'MATPLANE', 1),
        ('GRIDFILL', 'Grid Fill', 'Grid Fill', 'VIEW_ORTHO', 2),
        ('BRIDGEEDGE', 'Bridge Edge Loops', 'Bridge Edge Loops', 'SORTSIZE', 3),
        ('FILL', 'Fill', 'Fill', 'MOD_TRIANGULATE', 4),
        ('FILLHOLES', 'Fill Holes', 'Fill Holes', 'LATTICE_DATA', 5)
    }, default='SKIP', update=upd_ops)
    pivot_point: EnumProperty(name='Pivot Point', items={
        ('NONE', 'Same', 'Same', 'BLANK1', 0),
        ('CURSOR', 'Cursor', 'Cursor', 'PIVOT_CURSOR', 1),
        ('BOUNDING_BOX_CENTER', 'Bounding Box', 'Bounding Box', 'PIVOT_BOUNDBOX', 2),
        ('INDIVIDUAL_ORIGINS', 'Individual Origins', 'Individual Origins', 'PIVOT_INDIVIDUAL', 3),
        ('MEDIAN_POINT', 'Median Point', 'Median Point', 'PIVOT_MEDIAN', 4),
        ('ACTIVE_ELEMENT', 'Active Element', 'Active Element', 'PIVOT_ACTIVE', 5),
    }, default='NONE', options={'HIDDEN'}, update=upd_ops)
    orientation_type: EnumProperty(name="Orientation", items={
        ('GLOBAL', 'Global', 'Global', 'ORIENTATION_GLOBAL', 0),
        ('LOCAL', 'Local', 'Local', 'ORIENTATION_LOCAL', 1),
    }, default='LOCAL', options={'HIDDEN'}, update=upd_ops)
    interpolate: EnumProperty(name="Interpolate", items={
        ('STRAIGHT', 'Straight', 'Straight', 'FORWARD', 0),
        ('REVERSED', 'Reversed', 'Reversed', 'BACK', 1),
    }, default='STRAIGHT', options={'HIDDEN'}, update=upd_ops)
    interp_type: EnumProperty(name="Curve", items={
        ('CONSTANT', 'Constant', 'Constant', 'IPO_CONSTANT', 0),
        ('BEZIER', 'Bezier', 'Bezier', 'IPO_EASE_IN_OUT', 1),
        ('RANDOM', 'Random', 'Random', 'TRACKING', 2),
    }, default='CONSTANT', options={'HIDDEN'}, update=upd_ops)
    interp_ease: EnumProperty(name="Curve", items={
        ('INOUT', 'Easy Ease', 'Easy Ease', 'IPO_EASE_IN_OUT', 0),
        ('IN', 'Ease In', 'Ease In', 'IPO_EASE_IN', 1),
        ('OUT', 'Ease Out', 'Ease Out', 'IPO_EASE_OUT', 2),
    }, default='INOUT', update=upd_ops)
    interp_ease_in: FloatProperty(default=0, step=.5, update=upd_ops)
    interp_ease_out: FloatProperty(default=1, step=.5, update=upd_ops)
    interp_seed: IntProperty(default=1, min=1, update=upd_ops)
    interp_even: BoolProperty(default=True, update=upd_ops)
    value_min: FloatProperty(default=.01, update=upd_ops)
    value_max: FloatProperty(default=.5, update=upd_ops)
    value_min2: FloatProperty(default=.01, update=upd_ops)
    value_max2: FloatProperty(default=.5, update=upd_ops)
    value_min3: FloatProperty(default=.01, update=upd_ops)
    value_max3: FloatProperty(default=.5, update=upd_ops)
    value_min_int: IntProperty(default=0, update=upd_ops)
    value_max_int: IntProperty(default=0, update=upd_ops)
    value_min_int2: IntProperty(default=0, update=upd_ops)
    value_max_int2: IntProperty(default=0, update=upd_ops)
    value_vec_min: FloatVectorProperty(default=(0, 0, 0), subtype='TRANSLATION', update=upd_ops)
    value_vec_max: FloatVectorProperty(default=(0, 0, 0), subtype='TRANSLATION', update=upd_ops)
    angle_vec_min: FloatVectorProperty(default=(0, 0, 0), subtype='EULER', update=upd_ops)
    angle_vec_max: FloatVectorProperty(default=(0, 0, 0), subtype='EULER', update=upd_ops)
    scale_vec_min: FloatVectorProperty(default=(1, 1, 1), subtype='XYZ', update=upd_ops)
    scale_vec_max: FloatVectorProperty(default=(1, 1, 1), subtype='XYZ', update=upd_ops)
    value_sync: BoolProperty(default=False, update=upd_ops)

    sel_rand_ratio: FloatProperty(default=0, min=0, max=1, subtype='FACTOR', update=upd_ops)
    sel_rand_invert: BoolProperty(default=False, update=upd_ops)
    sel_rand_seed: IntProperty(default=0, min=0, update=upd_ops)

    sel_mode_verts: BoolProperty(default=False, update=upd_ops)
    sel_mode_edges: BoolProperty(default=False, update=upd_ops)
    sel_mode_faces: BoolProperty(default=True, update=upd_ops)

    sel_sharp: FloatProperty(default=radians(30), min=0, max=pi, step=radians(10) * 100, subtype='ANGLE',
                             update=upd_ops)

    sel_more: IntProperty(default=1, update=upd_ops)
    sel_weight: FloatProperty(default=1, min=0, max=1, subtype='FACTOR', update=upd_ops)
    sel_vgroup: StringProperty(default="", update=upd_ops)

    sel_bysides_type: EnumProperty(name='Type', items={
        ('EQUAL', 'Equal', 'Equal', 0),
        ('LESS', 'Less Than', 'Less Than', 1),
        ('GREATER', 'Greater Than', 'Greater Than', 2),
        ('NOTEQUAL', 'Not Equal', 'Not Equal', 3)
    }, default='EQUAL', update=upd_ops)

    sel_cstm_clear_previous_selection: BoolProperty(name="Clear Previous Selection", default=True, update=upd_ops)
    sel_cstm_deselect: BoolProperty(name="Deselect", default=False, update=upd_ops)
    sel_cstm_element_type: EnumProperty(name="Element Type", items={
        ("VERTS", "Vertices", "Vertices", "VERTEXSEL", 0),
        ("EDGES", "Edges", "Edges", "EDGESEL", 1),
        ("FACES", "Faces", "Faces", "FACESEL", 2),
    }, default="VERTS", update=upd_ops)
    sel_cstm_vert_type: EnumProperty(name="Selection Type", items={
        ("BELOW", "Below", "Below", "SORT_ASC", 0),
        ("ABOVE", "Above", "Above", "SORT_DESC", 1),
        ("SPHERE", "Sphere", "Sphere", "SHADING_SOLID", 2),
        ("EDGENUM", "Edges Connected", "Number of adjacent edges", "UV_EDGESEL", 3),
        ("FACENUM", "Faces Connected", "Number of adjacent faces", "UV_FACESEL", 4),
    }, default="BELOW", update=upd_ops)
    sel_cstm_edge_type: EnumProperty(name="Selection Type", items={
        ("BELOW", "Below", "Below", "SORT_ASC", 0),
        ("ABOVE", "Above", "Above", "SORT_DESC", 1),
        ("SPHERE", "Sphere", "Sphere", "SHADING_SOLID", 2),
        ("LENGTH", "Length", "Length", "DRIVER_DISTANCE", 3),
        ("FACENUM", "Faces number", "Number of adjacent faces", "UV_EDGESEL", 4)
    }, default="LENGTH", update=upd_ops)
    sel_cstm_face_type: EnumProperty(name="Selection Type", items={
        ("BELOW", "Below", "Below", "SORT_ASC", 0),
        ("ABOVE", "Above", "Above", "SORT_DESC", 1),
        ("SPHERE", "Sphere", "Sphere", "SHADING_SOLID", 2),
        ("VNUM", "Vertex number", "Number of vertices", 3),
        ("AREA", "Area", "Area", "FULLSCREEN_ENTER", 4)
    }, default="VNUM", update=upd_ops)
    sel_cstm_axis: EnumProperty(name="Axis", items={
        ("X", "X", "X", "EVENT_X", 0),
        ("Y", "Y", "Y", "EVENT_Y", 1),
        ("Z", "Z", "Z", "EVENT_Z", 2),
    }, default="Z", update=upd_ops)
    sel_cstm_pivot: EnumProperty(name="Pivot Point", items={
        ("MANUAL", "Manual", "Manual", "EMPTY_ARROWS", 0),
        ("OBJECT", "Object", "Object", "MESH_CUBE", 1),
    }, default="MANUAL", update=upd_ops)
    sel_cstm_center: FloatVectorProperty(name="Center", default=(0, 0, 0), subtype='TRANSLATION', update=upd_ops)
    sel_cstm_target: PointerProperty(type=Object, update=upd_ops)
    sel_cstm_noise_threshold: FloatProperty(name="Noise Threshold", default=0, min=0, update=upd_ops)
    sel_cstm_sphere_size: FloatProperty(name="Noise Threshold", default=1, min=0, update=upd_ops)
    sel_cstm_noise_scale: FloatProperty(name="Noise Scale", default=1, min=0, update=upd_ops)
    sel_cstm_noise_falloff: FloatProperty(name="Noise Falloff", default=1, min=0.001, update=upd_ops)
    sel_cstm_edge_facenum: IntProperty(name="Number of Faces", default=1, min=0, update=upd_ops)
    sel_cstm_face_vnum: IntProperty(name="Number of Vertices", default=3, min=0, update=upd_ops)

    gen_grab: FloatVectorProperty(default=(0, 0, 0), subtype='TRANSLATION', update=upd_ops)
    gen_rotate: FloatVectorProperty(default=(0, 0, 0), subtype='EULER', update=upd_ops)
    gen_scale: FloatVectorProperty(default=(1, 1, 1), subtype='XYZ', update=upd_ops)
    gen_extr_ind: BoolProperty(default=False, update=upd_ops)
    gen_extr_value: FloatVectorProperty(default=(0, 0, 0), subtype='TRANSLATION', update=upd_ops)
    gen_extr_indval: FloatProperty(default=0, update=upd_ops)

    gen_subd_cuts: IntProperty(default=0, min=0, step=1, update=upd_ops)
    gen_subd_smooth: FloatProperty(default=0, min=0, soft_max=1, subtype='FACTOR', update=upd_ops)
    gen_subd_ngon: BoolProperty(default=True, update=upd_ops)
    gen_subd_quad: EnumProperty(name="Quad Corner", items={
        ('FAN', 'Fan', 'Fan', 'BLANK1', 0),
        ('INNERVERT', 'Inner Vert', 'Inner Vert', 'BLANK1', 1),
        ('STRAIGHT_CUT', 'Straight Cut', 'Straight Cut', 'BLANK1', 2),
        ('PATH', 'Path', 'Path', 'BLANK1', 3)
    }, default='STRAIGHT_CUT', update=upd_ops)
    gen_subd_fractal: FloatProperty(default=0, min=0, update=upd_ops)
    gen_subd_fr_norm: FloatProperty(default=0, min=0, max=1, subtype='FACTOR', update=upd_ops)
    gen_subd_seed: IntProperty(default=0, min=0, update=upd_ops)

    gen_b_off_type: EnumProperty(name="Offset Type", items={
        ('OFFSET', 'Offset', 'Offset', 'EVENT_O', 0),
        ('WIDTH', 'Width', 'Width', 'EVENT_W', 1),
        ('DEPTH', 'Depth', 'Depth', 'EVENT_D', 2),
        ('PERCENT', 'Percent', 'Percent', 'EVENT_P', 3),
        ('ABSOLUTE', 'Absolute', 'Absolute', 'EVENT_A', 4)
    }, default='OFFSET', update=upd_ops)
    gen_b_offset: FloatProperty(default=0, min=0, update=upd_ops)
    gen_b_prof_type: EnumProperty(name="Profile Type", items={
        ('SUPERELLIPSE', 'Superellipse', 'Superellipse', 'MESH_CAPSULE', 0),
        ('CUSTOM', 'Custom', 'Custom', 'TOOL_SETTINGS', 1),
    }, default='SUPERELLIPSE', update=upd_ops)
    gen_b_offset_pct: FloatProperty(default=0, min=0, max=100, update=upd_ops)  # for Percent Method
    gen_b_segments: IntProperty(default=1, min=1, max=1000, update=upd_ops)
    gen_b_profile: FloatProperty(default=0.5, min=0, max=1, subtype='FACTOR', update=upd_ops)
    gen_b_affect: EnumProperty(name="Affect", items={
        ('VERTICES', 'Vertices', 'Vertices', 'VERTEXSEL', 0),
        ('EDGES', 'Edges', 'Edges', 'EDGESEL', 1),
    }, default='EDGES', update=upd_ops)
    gen_b_clmp_ovrlp: BoolProperty(default=False, update=upd_ops)
    gen_b_loop_slide: BoolProperty(default=True, update=upd_ops)
    gen_b_mark_seam: BoolProperty(default=False, update=upd_ops)
    gen_b_mark_sharp: BoolProperty(default=False, update=upd_ops)
    gen_b_material: IntProperty(default=-1, min=-1, update=upd_ops)
    gen_b_hard_norm: BoolProperty(default=False, update=upd_ops)
    gen_b_f_str_mode: EnumProperty(name="Face Strength Mode", items={
        ('NONE', 'None', 'None', 'BLANK1', 0),
        ('NEW', 'New', 'New', 'FILE_NEW', 1),
        ('AFFECTED', 'Affected', 'Affected', 'SELECT_INTERSECT', 2),
        ('ALL', 'All', 'All', 'SELECT_EXTEND', 3),
    }, default='NONE', update=upd_ops)
    gen_b_mtr_outer: EnumProperty(name="Miter Outer", items={
        ('SHARP', 'Sharp', 'Sharp', 'SHARPCURVE', 0),
        ('PATCH', 'Patch', 'Patch', 'MOD_WARP', 1),
        ('ARC', 'Arc', 'Arc', 'INVERSESQUARECURVE', 2),
    }, default='SHARP', update=upd_ops)
    gen_b_mtr_inner: EnumProperty(name="Miter Inner", items={
        ('SHARP', 'Sharp', 'Sharp', 'SHARPCURVE', 0),
        ('ARC', 'Arc', 'Arc', 'INVERSESQUARECURVE', 2),
    }, default='SHARP', update=upd_ops)
    gen_b_spread: FloatProperty(default=0.1, min=0, update=upd_ops)
    gen_b_vmesh_met: EnumProperty(name="VMesh Method", items={
        ('ADJ', 'Grid Fill', 'Grid Fill', 'VIEW_ORTHO', 0),
        ('CUTOFF', 'Cutoff', 'Cutoff', 'MESH_PLANE', 1),
    }, default='ADJ', update=upd_ops)
    gen_b_rl_confirm: BoolProperty(default=False, update=upd_ops)

    gen_solidify: FloatProperty(default=0, update=upd_ops)

    gen_wrf_boundary: BoolProperty(default=True, update=upd_ops)
    gen_wrf_even: BoolProperty(default=True, update=upd_ops)
    gen_wrf_relative: BoolProperty(default=False, update=upd_ops)
    gen_wrf_replace: BoolProperty(default=True, update=upd_ops)
    gen_wrf_thick: FloatProperty(default=0.01, min=0, max=10000, update=upd_ops)
    gen_wrf_offset: FloatProperty(default=0.01, min=0, max=10000, update=upd_ops)
    gen_wrf_crease: BoolProperty(default=False, update=upd_ops)
    gen_wrf_crs_wght: FloatProperty(default=0.01, min=0, max=1000, update=upd_ops)

    gen_mir_pivot: EnumProperty(name="Orient Type", items={
        ('OBJECT', 'Object', 'Object', 'OBJECT_DATAMODE', 0),
        ('CURSOR', '3D Cursor', '3D Cursor', 'PIVOT_CURSOR', 1),
        ('CENTER', 'World Center', 'World Center', 'WORLD', 2),
        ('MANUAL', 'Manual', 'Manual', 'MODIFIER_OFF', 3)
    }, default='OBJECT', update=upd_ops)
    gen_mir_object: PointerProperty(type=Object, update=upd_ops)
    gen_mir_constr_x: BoolProperty(name="X", default=False, update=upd_ops)
    gen_mir_constr_y: BoolProperty(name="Y", default=False, update=upd_ops)
    gen_mir_constr_z: BoolProperty(name="Z", default=False, update=upd_ops)
    gen_mir_center: FloatVectorProperty(default=(0, 0, 0), subtype='TRANSLATION', update=upd_ops)
    gen_mir_accurate: BoolProperty(default=False, update=upd_ops)

    gen_dupli_mode: EnumProperty(name="Mode", items={
        ('1', 'Vertices', 'Vertices', 'VERTEXSEL', 0),
        ('2', 'Edges', 'Edges', 'EDGESEL', 1),
        ('3', 'Faces', 'Faces', 'FACESEL', 2),
    }, default='3', update=upd_ops)

    gen_split_type: EnumProperty(name="Split Type", items={
        ('SELECT', 'Selected', 'Selected', 'RESTRICT_SELECT_ON', 0),
        ('EDGE', 'By Edges', 'By Edges', 'UV_EDGESEL', 1),
        ('VERT', 'By Verts', 'By Verts', 'UV_VERTEXSEL', 2),
    }, default='SELECT', update=upd_ops)

    gen_loop_edge: IntProperty(default=-1, min=-1, update=upd_ops)
    gen_loop_cuts: IntProperty(default=1, min=1, max=1000000, update=upd_ops)
    gen_loop_smooth: FloatProperty(default=0, min=-1000, max=1000, update=upd_ops)
    gen_loop_falloff: EnumProperty(name="Split Type", items={
        ('SMOOTH', 'Smooth', 'Smooth', 'SMOOTHCURVE', 0),
        ('SPHERE', 'Sphere', 'Sphere', 'SPHERECURVE', 1),
        ('ROOT', 'Root', 'Root', 'ROOTCURVE', 2),
        ('INVERSE_SQUARE', 'Inverse Square', 'Inverse Square', 'INVERSESQUARECURVE', 3),
        ('SHARP', 'Sharp', 'Sharp', 'SHARPCURVE', 4),
        ('LINEAR', 'Linear', 'Linear', 'LINCURVE', 5),
    }, default='INVERSE_SQUARE', update=upd_ops)

    gen_ins_boundary: BoolProperty(default=True, update=upd_ops)
    gen_ins_even: BoolProperty(default=True, update=upd_ops)
    gen_ins_relative: BoolProperty(default=False, update=upd_ops)
    gen_ins_edgerail: BoolProperty(default=False, update=upd_ops)
    gen_ins_thick: FloatProperty(default=0, min=0, update=upd_ops)
    gen_ins_depth: FloatProperty(default=0, update=upd_ops)
    gen_ins_outset: BoolProperty(default=False, update=upd_ops)
    gen_ins_selinset: BoolProperty(default=False, update=upd_ops)
    gen_ins_individ: BoolProperty(default=False, update=upd_ops)
    gen_ins_interp: BoolProperty(default=True, update=upd_ops)

    gen_tri_face: FloatProperty(default=radians(40), step=radians(10) * 100, subtype='ANGLE', update=upd_ops)
    gen_tri_shape: FloatProperty(default=radians(40), step=radians(10) * 100, subtype='ANGLE', update=upd_ops)

    gen_bool_subject: EnumProperty(name="Subject", items={
        ("SELECTION", "Selection", "Selection", 0),
        ("OBJECT", "Object", "Object", 1),
    }, default="OBJECT", update=upd_ops)
    gen_bool_operation: EnumProperty(name="Subject", items={
        ("INTERSECT", "Intersect", "Intersect", 0),
        ("UNION", "Union", "Union", 1),
        ("DIFFERENCE", "Difference", "Difference", 2),
    }, default="DIFFERENCE", update=upd_ops)
    gen_bool_object: PointerProperty(type=Object, update=upd_ops)
    gen_bool_solver: EnumProperty(name="Solver", items={
        ("FAST", "Fast", "Fast", 0),
        ("EXACT", "Exact", "Exact", 1),
    }, default="FAST", update=upd_ops)
    gen_bool_overlap_threshold: FloatProperty(default=0.000001, min=0, precision=6, step=.00001, subtype='DISTANCE')

    def_warp_angle1: FloatProperty(default=radians(360), step=radians(10) * 100, subtype='ANGLE', update=upd_ops)
    def_warp_angle2: FloatProperty(default=0, step=radians(10) * 100, subtype='ANGLE', update=upd_ops)
    def_warp_min: FloatProperty(default=-1, update=upd_ops)
    def_warp_max: FloatProperty(default=1, update=upd_ops)
    def_warp_center: FloatVectorProperty(default=(1, 0, 0), subtype='TRANSLATION', update=upd_ops)
    def_warp_rotate: FloatVectorProperty(default=(0, 0, 0), subtype='EULER', update=upd_ops)
    def_shrink_fac: FloatProperty(default=.1, subtype="DISTANCE", update=upd_ops)
    def_shrink_even: BoolProperty(default=False, update=upd_ops)
    def_shear_axis: EnumProperty(name="Axis", items={
        ("X", "X", "X", "EVENT_X", 1),
        ("Y", "Y", "Y", "EVENT_Y", 2),
        ("Z", "Z", "Z", "EVENT_Z", 3),
    }, default='Z', update=upd_ops)
    def_shear_ax_ort: EnumProperty(name="Axis", items={
        ("X", "X", "X", "EVENT_X", 1),
        ("Y", "Y", "Y", "EVENT_Y", 2),
        ("Z", "Z", "Z", "EVENT_Z", 3),
    }, default='X', update=upd_ops)

    cln_delete: EnumProperty(name="Mode", items={
        ('VERT', 'Vertices', 'Delete', 'VERTEXSEL', 0),
        ('EDGE', 'Edges', 'Delete', 'EDGESEL', 1),
        ('FACE', 'Faces', 'Delete', 'FACESEL', 2),
        ('FACE_EDGE', 'Only Edges & Faces', 'Delete', 'BLANK1', 3),
        ('ONLY_FACE', 'Only Faces', 'Delete', 'BLANK1', 4),
    }, default='VERT', update=upd_ops)
    cln_dissolve: EnumProperty(name="Mode", items={
        ('VERT', 'Vertices', 'Dissolve', 'VERTEXSEL', 0),
        ('EDGE', 'Edges', 'Dissolve', 'EDGESEL', 1),
        ('FACE', 'Faces', 'Dissolve', 'FACESEL', 2),
        ('LIMITED', 'Limited Dissolve', 'Dissolve', 'BLANK1', 3),
    }, default='VERT', update=upd_ops)
    cln_decimate: EnumProperty(name="Mode", items={
        ('COLLAPSE', 'Collapse', 'Collapse', 'AUTOMERGE_ON', 0),
        ('PLANAR', 'Planar', 'Planar', 'NORMALS_VERTEX_FACE', 1),
    }, default='COLLAPSE', update=upd_ops)

    cln_mrg_type: EnumProperty(name="Type", items={
        ('CENTER', 'At Center', 'At Center', 'SNAP_FACE_CENTER', 0),
        ('CURSOR', 'At Cursor', 'At Cursor', 'PIVOT_CURSOR', 1),
        ('COLLAPSE', 'Collapse', 'Collapse', 'SNAP_MIDPOINT', 2),
        ('BY_DISTANCE', 'By Distance', 'By Distance', 'STICKY_UVS_DISABLE', 3)
    }, default='BY_DISTANCE', update=upd_ops)
    cln_mrg_thresh: FloatProperty(default=0.0001, min=0, update=upd_ops)
    cln_mrg_unselect: BoolProperty(default=False, update=upd_ops)

    asn_material: PointerProperty(type=Material, update=upd_ops)
    asn_crease_v: FloatProperty(default=0, min=0, max=1, subtype='FACTOR', update=upd_ops)
    asn_crease_e: FloatProperty(default=0, min=0, max=1, subtype='FACTOR', update=upd_ops)

    add_size: FloatProperty(default=2, min=0, update=upd_ops)
    add_radius: FloatProperty(default=1, min=0, update=upd_ops)
    add_radius2: FloatProperty(default=2, min=0, update=upd_ops)
    add_circ_verts: IntProperty(default=32, min=3, update=upd_ops)
    add_circ_fill: EnumProperty(name="Fill Type", items={
        ('NOTHING', 'Nothing', 'Nothing', 'BLANK1', 0),
        ('NGON', 'N-Gon', 'N-Gon', 'BLANK1', 1),
        ('TRIFAN', 'Triangles', 'Triangles', 'BLANK1', 2)
    }, default='NOTHING', update=upd_ops)
    add_sphr_rings: IntProperty(default=16, min=3, update=upd_ops)
    add_sphr_ico: IntProperty(default=2, min=1, update=upd_ops)
    add_tor_seg_maj: IntProperty(default=48, min=3, update=upd_ops)
    add_tor_seg_min: IntProperty(default=12, min=3, update=upd_ops)
    add_tor_mode: EnumProperty(name="Mode", items={
        ('MAJOR_MINOR', 'Major/Minor', 'Major/Minor', 'BLANK1', 0),
        ('EXT_INT', 'Exterior/Interior', 'Exterior/Interior', 'BLANK1', 1),
    }, default='MAJOR_MINOR', update=upd_ops)
    add_tor_rad_maj: FloatProperty(default=1, min=0, update=upd_ops)
    add_tor_rad_min: FloatProperty(default=.25, min=0, update=upd_ops)
    add_tor_rad_abso_maj: FloatProperty(default=1.25, min=0, update=upd_ops)
    add_tor_rad_abso_min: FloatProperty(default=.75, min=0, update=upd_ops)
    add_grid_x: IntProperty(default=10, min=1, update=upd_ops)
    add_grid_y: IntProperty(default=10, min=1, update=upd_ops)

    fill_bridge_type: EnumProperty(name='Connect Loops', items={
        ('SINGLE', 'Open Loop', 'Open Loop', 0),
        ('CLOSED', 'Closed Loop', 'Closed Loop', 1),
        ('PAIRS', 'Loop Pairs', 'Loop Pairs', 2),
    }, default='SINGLE', update=upd_ops)
    fill_bridge_interp: EnumProperty(name='Interpolation', items={
        ('LINEAR', 'Linear', 'Linear', 0),
        ('PATH', 'Blend Path', 'Blend Path', 1),
        ('SURFACE', 'Blend Surface', 'Blend Surface', 2),
    }, default='LINEAR', update=upd_ops)
    fill_bridge_smooth: FloatProperty(default=1, min=0, soft_max=2, update=upd_ops)
    fill_bridge_profile: FloatProperty(default=0, soft_min=-1, soft_max=1, update=upd_ops)
    fill_holes: IntProperty(default=4, min=0, update=upd_ops)


# ------------------------------------------------ SCENE STACKS STORAGE ------------------------------------------------


class STACKS_PROP_Stacks(PropertyGroup):
    """Scene Stacks Storage"""
    name: StringProperty(default="Stack", update=stacks_enum_register)
    index: IntProperty(default=0)
    ops: CollectionProperty(type=STACKS_PROP_Operator)
    ops_active: IntProperty(default=0)


# ------------------------------------------------ SCENE COMMON SETTINGS -----------------------------------------------


class STACKS_PROP_ScCommon(PropertyGroup):
    save_preset: BoolProperty(default=False, options={'HIDDEN'}, update=upd_save_preset)
    load_preset: BoolProperty(default=False, options={'HIDDEN'}, update=upd_load_preset)
    overwrite: BoolProperty(default=False, options={'HIDDEN'})
    preset_name: StringProperty(default="")
    load_from: PointerProperty(type=Text)
    save_to: PointerProperty(type=Text)
    op_stck_closed: BoolProperty(default=False, options={'HIDDEN'})
    op_list_closed: BoolProperty(default=False, options={'HIDDEN'})
    op_type_closed: BoolProperty(default=False, options={'HIDDEN'})
    op_intr_closed: BoolProperty(default=False, options={'HIDDEN'})
    op_sets_closed: BoolProperty(default=False, options={'HIDDEN'})
    presets_closed: BoolProperty(default=True, options={'HIDDEN'})
    animatable: BoolProperty(default=False, options={'HIDDEN'}, name="Animatable", update=STACKS_animatable,
                             description="Take into account add-on settings' animation  while Render and Playback.\
\n\nWARNING!\nAnimation of this add-on's settings may significantly\nslow down performance, lead to unstable work \
 and crashes.\nUse at your own risk")
    render_init_id: StringProperty(default="")
    render_complete_id: StringProperty(default="")
    frame_change_id: StringProperty(default="")


# ------------------------------------------------- OBJECT LOOP CUT DATA -----------------------------------------------


class STACKS_PROP_ObLoopCutEdges(PropertyGroup):
    """Loop Cut edges for object's operators stacks"""
    name: StringProperty(default="Empty")
    index: IntProperty(default=0)
    edge: IntProperty(default=-1, min=-1, options={'HIDDEN'}, update=upd_ops)
    op_index: IntProperty(default=0)


# ------------------------------------------------- OBJECT SINGLE STACK ------------------------------------------------


class STACKS_PROP_ObStackBackup(PropertyGroup):
    """Object Stacks Backup and Commons"""
    name: StringProperty(default="Empty")
    index: IntProperty(default=0)
    enabled: BoolProperty(default=True, options={'HIDDEN'}, update=upd_ops)
    type: EnumProperty(name="Stack Type", items={
        ('STACK', 'Stack', 'Stack', 'LONGDISPLAY', 0),
        ('SELECT', 'Select', 'Select', 'RESTRICT_SELECT_OFF', 1),
    }, default='STACK')
    stack_index: IntProperty(default=0)
    op_index: IntProperty(default=0)
    selection: StringProperty(default="f-f-t|[]-[]-[]")
    repeat: IntProperty(default=1, min=0, max=10000, soft_max=10, options={'HIDDEN'}, update=upd_ops)
    dummy: BoolProperty(default=True)
    loopcut_edges: CollectionProperty(type=STACKS_PROP_ObLoopCutEdges)
    loopcut_active: IntProperty(default=0)


# ---------------------------------------------- OBJECT SINGLE STACK UI ------------------------------------------------

class STACKS_PROP_ObStack(PropertyGroup):
    """RE-REGISTABLE! Object Single Stack"""
    name: StringProperty(default="Empty")
    index: IntProperty(default=0)
    stack: EnumProperty(name='Stack Select', items={('000', 'None', 'None', "BLANK1", 0)}, default='000',
                        update=upd_obj)


# ----------------------------------------------- OBJECT COMMON SETTINGS -----------------------------------------------

class STACKS_PROP_ObCommon(PropertyGroup):
    """Object common static properties"""
    ob_reference: PointerProperty(type=Object)
    ob_stacks: PointerProperty(type=Object)
    live_update: BoolProperty(default=True, options={'HIDDEN'})
    update_all: BoolProperty(default=True, options={'HIDDEN'}, description="Update all objects using current stack")
    show_reference: BoolProperty(default=False, options={'HIDDEN'}, update=upd_show_original)
    edit_reference: BoolProperty(default=False, options={'HIDDEN'}, update=upd_edit_original)


# ------------------------------------------------------ REGISTER ------------------------------------------------------

classes = [
    STACKS_PROP_Operator,
    STACKS_PROP_Stacks,
    STACKS_PROP_ScCommon,
    STACKS_PROP_ObLoopCutEdges,
    STACKS_PROP_ObStackBackup,
    STACKS_PROP_ObStack,
    STACKS_PROP_ObCommon,

]


def register():
    for cl in classes:
        register_class(cl)
    Object.stacks = CollectionProperty(type=STACKS_PROP_ObStack)
    Object.stacks_c = CollectionProperty(type=STACKS_PROP_ObStackBackup)
    Object.stacks_active = IntProperty(default=0)
    Object.stacks_common = PointerProperty(type=STACKS_PROP_ObCommon)
    Scene.stacks = CollectionProperty(type=STACKS_PROP_Stacks)
    Scene.stacks_active = IntProperty(default=0)
    Scene.stacks_common = PointerProperty(type=STACKS_PROP_ScCommon)
    LoadPost.append(STACKS_on_load)
    DepsgraphUpdate.append(STACKS_on_load)


def unregister():
    del Object.stacks_active
    del Scene.stacks_active
    for cl in reversed(classes):
        unregister_class(cl)


# ----------------------------------------------------------------------------- TEST

if __name__ == '__main__':
    register()
