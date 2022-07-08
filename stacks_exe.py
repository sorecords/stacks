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
Blender «Stacks» add-on Operators Execute

Operator Class names to be used in the STACKS_OpExec:
    "STACKS_PROP_Operator.operator_type.Enum ID.capitalize()" +
    "STACKS_PROP_Operator.ops_***.Enum ID.capitalize()"

"NONE" and "SKIP" operators are blocked outside this class, no need to define them here.
"""
from __future__ import annotations
from mathutils import Euler
from abc import ABC, abstractmethod
from functools import wraps

if __name__ == '__main__':
    try:  # PyCharm import
        from stacks_support_common import *
    except ModuleNotFoundError:  # Blender Text Editor import
        from stacks.stacks_support_common import *
else:  # Add-on import
    from .stacks_support_common import *


class STACKS_OpExec:
    def __init__(self, opexec: STACKS_Op):
        self.opexec = opexec

    def __call__(self) -> None:
        """Execute Operator"""
        return self.opexec()


class STACKS_Op(ABC):
    """Operator Main Abstract Class"""

    def __init__(self, *args):
        self.context = args[0]
        self.op = args[1]

    def __call__(self):
        setmode(self.context, 'EDIT')
        self.operator()

    @abstractmethod
    def operator(self) -> None:
        pass


# ----------------------------------------------------- Decorators -----------------------------------------------------


def select_mode(operator: callable):
    """Select Operators Decorator"""

    @wraps(operator)
    def wrapper(self, *args) -> None:
        """Set Select Mode and execute Select Operator"""
        self.context.tool_settings.mesh_select_mode = (
            self.op.sel_mode_verts,
            self.op.sel_mode_edges,
            self.op.sel_mode_faces
        )
        return operator(self, *args)

    return wrapper


def pivot_point(operator: callable):
    """Change Pivot Point Decorator"""

    @wraps(operator)
    def wrapper(self) -> None:
        """Set Select Mode and execute Select Operator"""
        if not self.op.pivot_point == 'NONE':
            self.context.scene.tool_settings.transform_pivot_point = self.op.pivot_point
        return operator(self, override=get_override(self.context))

    return wrapper


# ------------------------------------------------------- SELECT -------------------------------------------------------


class SelectSkip(STACKS_Op):
    """Ignore Selecting"""

    @select_mode
    def operator(self) -> None:
        pass


class SelectAll(STACKS_Op):
    """Select all unhidden elements in the context mesh"""

    @select_mode
    def operator(self) -> None:
        bpy.ops.mesh.select_all(action='SELECT')


class SelectNone(STACKS_Op):
    """Unselect all unhidden elements in the context mesh"""

    @select_mode
    def operator(self) -> None:
        bpy.ops.mesh.select_all(action='DESELECT')


class SelectRandom(STACKS_Op):
    """Randomly select elements in the context mesh according to the context operator settings"""

    @select_mode
    def operator(self) -> None:
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_random(ratio=self.op.sel_rand_ratio, seed=self.op.sel_rand_seed, action='SELECT')
        if self.op.sel_rand_invert:
            bpy.ops.mesh.select_all(action='INVERT')


class SelectSharp(STACKS_Op):
    """Select Sharp Edges in the context mesh"""

    @select_mode
    def operator(self) -> None:
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.edges_select_sharp(sharpness=self.op.sel_sharp)


class SelectInvert(STACKS_Op):
    """Invert selection in the context mesh"""

    @select_mode
    def operator(self) -> None:
        bpy.ops.mesh.select_all(action='INVERT')


class SelectMore(STACKS_Op):
    """Select More/Less Adjacent Elements in the context mesh"""

    @select_mode
    def operator(self) -> None:
        if self.op.sel_more == 0:
            return
        func = getattr(bpy.ops.mesh, "select_more" if self.op.sel_more > 0 else "select_less")
        for _ in range(abs(self.op.sel_more)):
            func()


class SelectLoose(STACKS_Op):
    """Select Loose Elements in the context mesh"""

    @select_mode
    def operator(self) -> None:
        bpy.ops.mesh.select_loose()


class SelectNonmanifold(STACKS_Op):
    """Select Non-Manifold Elements in the context mesh"""

    @select_mode
    def operator(self) -> None:
        try:
            bpy.ops.mesh.select_non_manifold()
        except RuntimeError as exp:
            bpy.ops.stacks.warning('INVOKE_DEFAULT', msg=str(exp), type='ERROR')


class SelectBoundary(STACKS_Op):
    """Select Boundary of the selected elements in the context mesh"""

    @select_mode
    def operator(self) -> None:
        bpy.ops.mesh.region_to_loop()


class SelectVgroup(STACKS_Op):
    """Select unhidden Vertex Group vertices in the context mesh"""

    @select_mode
    def operator(self) -> None:
        if self.op.gen_subd_ngon:
            bpy.ops.mesh.select_all(action='DESELECT')
        vgroups = self.context.object.vertex_groups
        if self.op.sel_vgroup in vgroups:
            vgroups.active = vgroups[self.op.sel_vgroup]
            if self.op.sel_rand_invert:
                bpy.ops.object.vertex_group_deselect()
            else:
                bpy.ops.object.vertex_group_select()


class SelectInterior(STACKS_Op):
    """Select Interior Faces in the context mesh"""

    @select_mode
    def operator(self) -> None:
        bpy.ops.mesh.select_interior_faces()


class SelectBysides(STACKS_Op):
    """Select Faces by sides in the context mesh"""

    @select_mode
    def operator(self) -> None:
        if self.op.gen_ins_interp:
            bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_face_by_sides(
            number=self.op.fill_holes,
            type=self.op.sel_bysides_type,
            extend=self.op.gen_subd_ngon)


class SelectCustom(STACKS_Op):
    """Select custom elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.stacks.custom_select(
            clear_previous_selection=self.op.sel_cstm_clear_previous_selection,
            deselect=self.op.sel_cstm_deselect,
            element_type=self.op.sel_cstm_element_type,
            sel_mode_verts=self.op.sel_mode_verts,
            sel_mode_edges=self.op.sel_mode_edges,
            sel_mode_faces=self.op.sel_mode_faces,
            vert_type=self.op.sel_cstm_vert_type,
            edge_type=self.op.sel_cstm_edge_type,
            face_type=self.op.sel_cstm_face_type,
            axis=self.op.sel_cstm_axis,
            pivot=self.op.sel_cstm_pivot,
            orientation=self.op.orientation_type,
            center=self.op.sel_cstm_center,
            center_target=self.op.sel_cstm_target.name if self.op.sel_cstm_target is not None else "",
            sphere_size=self.op.sel_cstm_sphere_size,
            noise_threshold=self.op.sel_cstm_noise_threshold,
            noise_seed=self.op.sel_rand_seed,
            noise_scale=self.op.sel_cstm_noise_scale,
            noise_falloff=self.op.sel_cstm_noise_falloff,
            more_than=self.op.gen_ins_outset,
            edge_facenum=self.op.sel_cstm_edge_facenum,
            face_vnum=self.op.sel_cstm_face_vnum
        )


class SelectSet(STACKS_Op):
    """
    Set Selection (Vertices, Edges and Faces) stored in the Operator settings to the context mesh
    Warning! As some Blender Operators each time recalculate mesh elements order differently,
    this function may be inefficient and perform different result on ech Operator Stack call.
    """

    def operator(self) -> None:
        bpy.ops.mesh.select_all(action='DESELECT')

        data = self.op.selection.split('|')
        modes = data[0].split('-')
        m1 = True if modes[0] == 'T' else False
        m2 = True if modes[1] == 'T' else False
        m3 = True if modes[2] == 'T' else False
        self.context.tool_settings.mesh_select_mode = (m1, m2, m3)

        setmode(self.context, 'OBJECT')

        mesh_data = data[1].split('-')
        verts = [int(v.strip()) for v in mesh_data[0][1:-1].split(',')]
        edges = [int(e.strip()) for e in mesh_data[1][1:-1].split(',')]
        faces = [int(f.strip()) for f in mesh_data[2][1:-1].split(',')]
        try:
            for v in verts:
                self.context.object.data.vertices[v].select = True
            for e in edges:
                self.context.object.data.edges[e].select = True
            for f in faces:
                self.context.object.data.polygons[f].select = True
        except IndexError:
            msg = "Can not set selection. The stored vertex data indices are out of range"
            bpy.ops.stacks.warning('INVOKE_DEFAULT', type="ERROR", msg=msg)


# -------------------------------------------------------- HIDE --------------------------------------------------------


class HideSelected(STACKS_Op):
    """Hide selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.hide(unselected=False)


class HideUnselected(STACKS_Op):
    """Hide unselected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.hide(unselected=True)


class HideReveal(STACKS_Op):
    """Reveal hidden elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.reveal()


# ------------------------------------------------------ GENERATE ------------------------------------------------------


class GenerateExtrude(STACKS_Op):
    """Make extrusion from the selected elements in the context mesh"""

    @pivot_point
    def operator(self, override: dict) -> None:
        if self.op.gen_extr_ind:
            bpy.ops.mesh.extrude_faces_move(
                override,
                MESH_OT_extrude_faces_indiv={
                    "mirror": False},
                TRANSFORM_OT_shrink_fatten={
                    "value": self.op.gen_extr_indval,
                    "use_even_offset": False,
                    "mirror": False,
                    "use_proportional_edit": False,
                    "proportional_edit_falloff": 'SMOOTH',
                    "proportional_size": 1,
                    "use_proportional_connected": False,
                    "use_proportional_projected": False,
                    "snap": False,
                    "snap_target": 'CLOSEST',
                    "snap_point": (0, 0, 0),
                    "snap_align": False,
                    "snap_normal": (0, 0, 0),
                    "release_confirm": False,
                    "use_accurate": False}
            )
        else:
            bpy.ops.mesh.extrude_region_move(
                override,
                MESH_OT_extrude_region={
                    "use_normal_flip": False,
                    "use_dissolve_ortho_edges": False,
                    "mirror": False},
                TRANSFORM_OT_translate={
                    "value": self.op.gen_extr_value,
                    "orient_axis_ortho": 'X',
                    "orient_type": 'NORMAL',
                    "orient_matrix": Euler((0, 0, 0)).to_matrix(),
                    "orient_matrix_type": 'NORMAL',
                    "constraint_axis": (False, False, False),
                    "mirror": False,
                    "use_proportional_edit": False,
                    "proportional_edit_falloff": 'SMOOTH',
                    "proportional_size": 1,
                    "use_proportional_connected": False,
                    "use_proportional_projected": False,
                    "snap": False,
                    "snap_target": 'CLOSEST',
                    "snap_point": (0, 0, 0),
                    "snap_align": False,
                    "snap_normal": (0, 0, 0),
                    "gpencil_strokes": False,
                    "cursor_transform": False,
                    "texture_space": False,
                    "remove_on_cancel": False,
                    "view2d_edge_pan": False,
                    "release_confirm": False,
                    "use_accurate": False,
                    "use_automerge_and_split": False}
            )


class GenerateSubdivide(STACKS_Op):
    """Subdivide selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.subdivide(
            number_cuts=self.op.gen_subd_cuts,
            smoothness=self.op.gen_subd_smooth,
            ngon=self.op.gen_subd_ngon,
            quadcorner=self.op.gen_subd_quad,
            fractal=self.op.gen_subd_fractal,
            fractal_along_normal=self.op.gen_subd_fr_norm,
            seed=self.op.gen_subd_seed
        )


class GenerateBevel(STACKS_Op):
    """Bevel selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.bevel(
            offset_type=self.op.gen_b_off_type,
            offset=self.op.gen_b_offset,
            profile_type=self.op.gen_b_prof_type,
            offset_pct=self.op.gen_b_offset_pct,
            segments=self.op.gen_b_segments,
            profile=self.op.gen_b_profile,
            affect=self.op.gen_b_affect,
            clamp_overlap=self.op.gen_b_clmp_ovrlp,
            loop_slide=self.op.gen_b_loop_slide,
            mark_seam=self.op.gen_b_mark_seam,
            mark_sharp=self.op.gen_b_mark_sharp,
            material=self.op.gen_b_material,
            harden_normals=self.op.gen_b_hard_norm,
            face_strength_mode=self.op.gen_b_f_str_mode,
            miter_outer=self.op.gen_b_mtr_outer,
            miter_inner=self.op.gen_b_mtr_inner,
            spread=self.op.gen_b_spread,
            vmesh_method=self.op.gen_b_vmesh_met,
            release_confirm=self.op.gen_b_rl_confirm
        )


class GenerateSolidify(STACKS_Op):
    """Solidify selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.solidify(thickness=self.op.gen_solidify)


class GenerateWireframe(STACKS_Op):
    """Solidify selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.wireframe(
            use_boundary=self.op.gen_wrf_boundary,
            use_even_offset=self.op.gen_wrf_even,
            use_relative_offset=self.op.gen_wrf_relative,
            use_replace=self.op.gen_wrf_replace,
            thickness=self.op.gen_wrf_thick,
            offset=self.op.gen_wrf_offset,
            use_crease=self.op.gen_wrf_crease,
            crease_weight=self.op.gen_wrf_crs_wght
        )


class GenerateMirror(STACKS_Op):
    """Mirror selected elements in the context mesh along the axis specified in the Operator settings"""

    def operator(self) -> None:
        if self.op.gen_mir_pivot == 'OBJECT':
            ob = self.context.object if self.op.gen_mir_object is None \
                else self.op.gen_mir_object
            center = ob.location if self.op.orientation_type == 'GLOBAL' \
                else self.context.object.matrix_world.decompose()[0]
        elif self.op.gen_mir_pivot == 'CURSOR':
            center = self.context.scene.cursor.location
        elif self.op.gen_mir_pivot == 'MANUAL':
            center = self.op.gen_mir_center
        else:
            center = (0, 0, 0)
        bpy.ops.transform.mirror(
            orient_type=self.op.orientation_type,
            orient_matrix=((0, 0, 0), (0, 0, 0), (0, 0, 0)),
            orient_matrix_type='GLOBAL',
            constraint_axis=(self.op.gen_mir_constr_x, self.op.gen_mir_constr_y, self.op.gen_mir_constr_z),
            gpencil_strokes=False,
            center_override=center,
            release_confirm=False,
            use_accurate=self.op.gen_mir_accurate
        )


class GenerateDuplicate(STACKS_Op):
    """Duplicate and transform selected elements in the context mesh"""

    def operator(self) -> None:
        override = get_override(self.context)
        sc = self.op.gen_scale
        scale = (sc[0], sc[0], sc[0]) if self.op.value_sync else sc
        if not self.op.pivot_point == 'NONE':
            self.context.scene.tool_settings.transform_pivot_point = self.op.pivot_point

        bpy.ops.mesh.duplicate_move(override, MESH_OT_duplicate={"mode": int(self.op.gen_dupli_mode)})
        bpy.ops.transform.translate(value=self.op.gen_grab, orient_type=self.op.orientation_type)
        bpy.ops.transform.rotate(override,
                                 value=self.op.gen_rotate[0],
                                 orient_axis='X',
                                 orient_type=self.op.orientation_type)
        bpy.ops.transform.rotate(override,
                                 value=self.op.gen_rotate[1],
                                 orient_axis='Y',
                                 orient_type=self.op.orientation_type)
        bpy.ops.transform.rotate(override,
                                 value=self.op.gen_rotate[2],
                                 orient_axis='Z',
                                 orient_type=self.op.orientation_type)
        bpy.ops.transform.resize(override, value=scale, orient_type=self.op.orientation_type)


class GenerateSplit(STACKS_Op):
    """Split selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.split() if self.op.gen_split_type == 'SELECT' \
            else bpy.ops.mesh.edge_split(type=self.op.gen_split_type)


class GenerateLoopcut(STACKS_Op):
    """Create faces Loop Cut in the context mesh according to the Operator settings"""

    def operator(self) -> None:
        override = get_override(self.context)
        bpy.ops.mesh.loopcut(
            override,
            number_cuts=self.op.gen_loop_cuts,
            smoothness=self.op.gen_loop_smooth,
            falloff=self.op.gen_loop_falloff,
            object_index=0,
            edge_index=self.op.gen_loop_edge
        )


class GenerateInset(STACKS_Op):
    """Generate inset for selected polygons in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.inset(
            use_boundary=self.op.gen_ins_boundary,
            use_even_offset=self.op.gen_ins_even,
            use_relative_offset=self.op.gen_ins_relative,
            use_edge_rail=self.op.gen_ins_edgerail,
            thickness=self.op.gen_ins_thick,
            depth=self.op.gen_ins_depth,
            use_outset=self.op.gen_ins_outset,
            use_select_inset=self.op.gen_ins_selinset,
            use_individual=self.op.gen_ins_individ,
            use_interpolate=self.op.gen_ins_interp
        )


class GenerateTriangulate(STACKS_Op):
    """Triangulate selected polygons in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')


class GenerateQuads(STACKS_Op):
    """Convert the polygons selected in the context mesh to quads"""

    def operator(self) -> None:
        bpy.ops.mesh.tris_convert_to_quads(
            face_threshold=self.op.gen_tri_face,
            shape_threshold=self.op.gen_tri_shape
        )


class GeneratePoke(STACKS_Op):
    """Poke selected polygons in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.poke(offset=self.op.gen_extr_indval)


class GenerateBoolean(STACKS_Op):
    """Apply Boolean modifier with self selection or another object to the context mesh"""

    def operator(self) -> None:
        bpy.ops.stacks.custom_boolean(
            subject=self.op.gen_bool_subject,
            operation=self.op.gen_bool_operation,
            object_name=self.op.gen_bool_object.name if self.op.gen_bool_object is not None else "",
            solver=self.op.gen_bool_solver,
            overlap_threshold=self.op.gen_bool_overlap_threshold,
            self_intersection=self.op.gen_extr_ind,
            hole_tolerant=self.op.gen_b_hard_norm
        )


# ------------------------------------------------------- DEFORM -------------------------------------------------------


class DeformSphere(STACKS_Op):
    """Deform selected elements in the context mesh to sphere"""

    def operator(self) -> None:
        bpy.ops.transform.tosphere(value=self.op.sel_rand_ratio)


class DeformRandomize(STACKS_Op):
    """Randomly deform selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.transform.vertex_random(
            offset=self.op.gen_extr_indval,
            uniform=self.op.sel_rand_ratio,
            normal=self.op.gen_subd_smooth,
            seed=self.op.sel_rand_seed
        )


class DeformSmooth(STACKS_Op):
    """Smooth selected vertices in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.vertices_smooth(factor=self.op.gen_subd_smooth)


class DeformShrink(STACKS_Op):
    """Shrink/Fatten selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.transform.shrink_fatten(
            value=self.op.def_shrink_fac,
            use_even_offset=self.op.def_shrink_even
        )


class DeformPush(STACKS_Op):
    """Push/Pull selected elements in the context mesh along their normals"""

    def operator(self) -> None:
        bpy.ops.transform.push_pull(value=self.op.gen_extr_indval)


class DeformWarp(STACKS_Op):
    """Warp selected vertices in the context mesh"""

    def operator(self) -> None:
        bpy.ops.transform.vertex_warp(
            warp_angle=self.op.def_warp_angle1,
            offset_angle=self.op.def_warp_angle2,
            min=self.op.def_warp_min,
            max=self.op.def_warp_max,
            viewmat=self.op.def_warp_rotate.to_matrix().to_4x4(),
            center=self.op.def_warp_center
        )


class DeformShear(STACKS_Op):
    """Shear selected elements in the context mesh"""

    @pivot_point
    def operator(self, override: dict) -> None:
        if not self.op.def_shear_ax_ort == self.op.def_shear_axis:  # the operator raises exception if they are equal
            bpy.ops.transform.shear(
                override,
                value=self.op.def_shrink_fac,
                orient_axis=self.op.def_shear_axis,
                orient_axis_ortho=self.op.def_shear_ax_ort,
                orient_matrix_type=self.op.orientation_type
            )


# ------------------------------------------------------ TRANSFORM -----------------------------------------------------


class TransformGrab(STACKS_Op):
    """Grab selected elements in the context mesh"""

    @pivot_point
    def operator(self, override: dict) -> None:
        bpy.ops.transform.translate(override, value=self.op.gen_grab, orient_type=self.op.orientation_type)


class TransformRotate(STACKS_Op):
    """Rotate selected elements in the context mesh"""

    @pivot_point
    def operator(self, override: dict) -> None:
        bpy.ops.transform.rotate(override, value=self.op.gen_rotate[0], orient_axis='X',
                                 orient_type=self.op.orientation_type)
        bpy.ops.transform.rotate(override, value=self.op.gen_rotate[1], orient_axis='Y',
                                 orient_type=self.op.orientation_type)
        bpy.ops.transform.rotate(override, value=self.op.gen_rotate[2], orient_axis='Z',
                                 orient_type=self.op.orientation_type)


class TransformScale(STACKS_Op):
    """Resize selected elements in the context mesh"""

    @pivot_point
    def operator(self, override: dict) -> None:
        sc = self.op.gen_scale
        bpy.ops.transform.resize(
            override,
            value=(sc[0], sc[0], sc[0]) if self.op.value_sync else sc,
            orient_type=self.op.orientation_type
        )


# ------------------------------------------------------ CLEAN UP ------------------------------------------------------


class CleanupDelete(STACKS_Op):
    """Delete selected Vertices, Edges or Faces, depending on the Operator settings, in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.delete(type=self.op.cln_delete)


class CleanupDissolve(STACKS_Op):
    """Dissolve selected Vertices, Edges or Faces, depending on the Operator settings, in the context mesh"""

    def operator(self) -> None:
        if self.op.cln_dissolve == 'VERT':
            bpy.ops.mesh.dissolve_verts()
        elif self.op.cln_dissolve == 'EDGE':
            bpy.ops.mesh.dissolve_edges()
        elif self.op.cln_dissolve == 'FACE':
            bpy.ops.mesh.dissolve_faces()
        elif self.op.cln_dissolve == 'LIMITED':
            bpy.ops.mesh.dissolve_limited(
                angle_limit=self.op.sel_sharp,
                use_dissolve_boundaries=self.op.gen_ins_boundary
            )


class CleanupDecimate(STACKS_Op):
    """Decimate the context mesh geometry"""

    def operator(self) -> None:
        if self.op.cln_decimate == 'COLLAPSE':
            bpy.ops.mesh.decimate(ratio=self.op.gen_b_profile)
        elif self.op.cln_decimate == 'PLANAR':
            bpy.ops.stacks.custom_decimate(limit_angle=self.op.sel_sharp)


class CleanupLoose(STACKS_Op):
    """Remove Loose geometry from the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.delete_loose(
            use_verts=self.op.sel_mode_verts,
            use_edges=self.op.sel_mode_edges,
            use_faces=self.op.sel_mode_faces
        )


class CleanupMerge(STACKS_Op):
    """Merge selected elements in the context mesh"""

    def operator(self) -> None:
        if self.op.cln_mrg_type == 'BY_DISTANCE':
            bpy.ops.mesh.remove_doubles(threshold=self.op.cln_mrg_thresh, use_unselected=self.op.cln_mrg_unselect)
        else:
            bpy.ops.mesh.merge(type=self.op.cln_mrg_type)


# ------------------------------------------------------ NORMALS -------------------------------------------------------


class NormalsFlat(STACKS_Op):
    """Set flat shading for the selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.faces_shade_flat()


class NormalsSmooth(STACKS_Op):
    """Set smooth shading for the selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.faces_shade_smooth()
        ob = self.context.object
        ob.data.use_auto_smooth = self.op.gen_extr_ind
        ob.data.auto_smooth_angle = self.op.sel_sharp


class NormalsFlip(STACKS_Op):
    """Flip normals of the selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.flip_normals()


class NormalsOutside(STACKS_Op):
    """Recalculate normals of the selected elements in the context mesh outside"""

    def operator(self) -> None:
        bpy.ops.mesh.normals_make_consistent(inside=False)


class NormalsInside(STACKS_Op):
    """Recalculate normals of the selected elements in the context mesh inside"""

    def operator(self) -> None:
        bpy.ops.mesh.normals_make_consistent(inside=True)


class NormalsMarksharp(STACKS_Op):
    """Mark/Clear sharp from the edges of the selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.mark_sharp(clear=not self.op.gen_b_loop_slide)


# ------------------------------------------------------ ASSIGN -------------------------------------------------------


class AssignMaterial(STACKS_Op):
    """Assign the material specified in the Operator settings to the selected elements in the context mesh"""

    def operator(self) -> None:
        ob = self.context.object
        mslots = ob.material_slots
        mats = [i for i, ms in enumerate(mslots) if ms.material == self.op.asn_material]
        if len(mats):
            ob.active_material_index = mats[0]
            bpy.ops.object.material_slot_assign()
        else:
            bpy.ops.object.material_slot_add()
            bpy.ops.object.material_slot_assign()
            if self.op.asn_material is not None:
                mslots[ob.active_material_index].material = self.op.asn_material


class AssignBevel(STACKS_Op):
    """Assign Bevel Weight value for the Bevel Modifier to the selected elements in the context mesh"""

    def operator(self) -> None:
        setmode(self.context, 'OBJECT')
        me = self.context.object.data
        me.use_customdata_vertex_bevel = True if self.op.asn_crease_v > 0 else False
        for v in self.context.object.data.vertices:
            if v.select:
                v.bevel_weight = self.op.asn_crease_v

        setmode(self.context, 'EDIT')
        bpy.ops.transform.edge_bevelweight(value=self.op.asn_crease_e * 2 - 1)


class AssignCrease(STACKS_Op):
    """Assign Crease value for the Subdivision Surface Modifier to the selected elements in the context mesh"""

    def operator(self) -> None:
        bpy.ops.transform.vert_crease(value=self.op.asn_crease_v * 2 - 1)
        bpy.ops.transform.edge_crease(value=self.op.asn_crease_e * 2 - 1)


class AssignSkin(STACKS_Op):
    """Assign Vertex Skin value for the Skin Modifier to the selected elements in the context mesh"""

    def operator(self) -> None:
        val = float(self.op.asn_crease_v)
        bpy.ops.transform.skin_resize(value=[val, val, val])


class AssignSeam(STACKS_Op):
    """Mark/Clear the edges of the selected elements in the context mesh as UV seams"""

    def operator(self) -> None:
        bpy.ops.mesh.mark_seam(clear=not self.op.gen_b_loop_slide)


class AssignSharp(STACKS_Op):
    """Mark/Clear the edges of the selected elements in the context mesh as sharp"""

    def operator(self) -> None:
        bpy.ops.mesh.mark_sharp(clear=not self.op.gen_b_loop_slide)


class AssignVgroup(STACKS_Op):
    """Assign selected vertices to the selected Vertex group"""

    def operator(self) -> None:
        print("Assign vertex group:")
        if self.op.sel_vgroup == "":
            return
        elif self.op.sel_vgroup in self.context.object.vertex_groups:
            bpy.ops.stacks.assign_vgroup(sel_weight=self.op.sel_weight,
                                          sel_vgroup=self.op.sel_vgroup,
                                          sel_remove=self.op.sel_rand_invert)
        else:
            bpy.ops.stacks.new_vgroup(vg_name=self.op.sel_vgroup, op_index=self.op.index)


# --------------------------------------------------- ADD PRIMITIVE ----------------------------------------------------


class AddPlane(STACKS_Op):
    """Add Plane primitive"""

    def operator(self) -> None:
        synced = self.op.value_sync
        scale = [self.op.gen_scale[0]] * 3 if synced else self.op.gen_scale
        bpy.ops.mesh.primitive_plane_add(
            size=self.op.add_size,
            location=self.op.gen_grab,
            rotation=self.op.gen_rotate,
            scale=scale
        )


class AddCube(STACKS_Op):
    """Add Cube primitive"""

    def operator(self) -> None:
        synced = self.op.value_sync
        scale = [self.op.gen_scale[0]] * 3 if synced else self.op.gen_scale
        bpy.ops.mesh.primitive_cube_add(
            size=self.op.add_size,
            location=self.op.gen_grab,
            rotation=self.op.gen_rotate,
            scale=scale
        )


class AddCircle(STACKS_Op):
    """Add Circle primitive"""

    def operator(self) -> None:
        synced = self.op.value_sync
        scale = [self.op.gen_scale[0]] * 3 if synced else self.op.gen_scale
        bpy.ops.mesh.primitive_circle_add(
            vertices=self.op.add_circ_verts,
            radius=self.op.add_radius,
            fill_type=self.op.add_circ_fill,
            location=self.op.gen_grab,
            rotation=self.op.gen_rotate,
            scale=scale
        )


class AddUvsphere(STACKS_Op):
    """Add UV Sphere primitive"""

    def operator(self) -> None:
        synced = self.op.value_sync
        scale = [self.op.gen_scale[0]] * 3 if synced else self.op.gen_scale
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=self.op.add_circ_verts,
            ring_count=self.op.add_sphr_rings,
            radius=self.op.add_radius,
            location=self.op.gen_grab,
            rotation=self.op.gen_rotate,
            scale=scale
        )


class AddIcosphere(STACKS_Op):
    """Add Ico Sphere primitive"""

    def operator(self) -> None:
        synced = self.op.value_sync
        scale = [self.op.gen_scale[0]] * 3 if synced else self.op.gen_scale
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=self.op.add_sphr_ico,
            radius=self.op.add_radius,
            location=self.op.gen_grab,
            rotation=self.op.gen_rotate,
            scale=scale
        )


class AddCylinder(STACKS_Op):
    """Add Cylinder primitive"""

    def operator(self) -> None:
        synced = self.op.value_sync
        scale = [self.op.gen_scale[0]] * 3 if synced else self.op.gen_scale
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=self.op.add_circ_verts,
            radius=self.op.add_radius,
            depth=self.op.add_radius2,
            end_fill_type=self.op.add_circ_fill,
            location=self.op.gen_grab,
            rotation=self.op.gen_rotate,
            scale=scale
        )


class AddCone(STACKS_Op):
    """Add Cone primitive"""

    def operator(self) -> None:
        synced = self.op.value_sync
        scale = [self.op.gen_scale[0]] * 3 if synced else self.op.gen_scale
        bpy.ops.mesh.primitive_cone_add(
            vertices=self.op.add_circ_verts,
            radius1=self.op.add_radius,
            radius2=self.op.gen_ins_thick,
            depth=self.op.add_radius2,
            end_fill_type=self.op.add_circ_fill,
            location=self.op.gen_grab,
            rotation=self.op.gen_rotate,
            scale=scale
        )


class AddTorus(STACKS_Op):
    """Add Torus primitive"""

    def operator(self) -> None:
        bpy.ops.mesh.primitive_torus_add(
            major_segments=self.op.add_tor_seg_maj,
            minor_segments=self.op.add_tor_seg_min,
            mode=self.op.add_tor_mode,
            major_radius=self.op.add_tor_rad_maj,
            minor_radius=self.op.add_tor_rad_min,
            abso_major_rad=self.op.add_tor_rad_abso_maj,
            abso_minor_rad=self.op.add_tor_rad_abso_min,
            location=self.op.gen_grab,
            rotation=self.op.gen_rotate,
        )


class AddGrid(STACKS_Op):
    """Add Grid primitive"""

    def operator(self) -> None:
        synced = self.op.value_sync
        scale = [self.op.gen_scale[0]] * 3 if synced else self.op.gen_scale
        bpy.ops.mesh.primitive_grid_add(
            x_subdivisions=self.op.add_grid_x,
            y_subdivisions=self.op.add_grid_y,
            size=self.op.add_size,
            location=self.op.gen_grab,
            rotation=self.op.gen_rotate,
            scale=scale
        )


class AddMonkey(STACKS_Op):
    """Add Monkey primitive"""

    def operator(self) -> None:
        synced = self.op.value_sync
        scale = [self.op.gen_scale[0]] * 3 if synced else self.op.gen_scale
        bpy.ops.mesh.primitive_monkey_add(
            size=self.op.add_size,
            location=self.op.gen_grab,
            rotation=self.op.gen_rotate,
            scale=scale
        )


# ------------------------------------------------------- FILL ---------------------------------------------------------


class FillEdgeface(STACKS_Op):
    """Make face/edge from selected in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.edge_face_add()


class FillGridfill(STACKS_Op):
    """Fill selected gap with grid of polygons in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.fill_grid(
            span=self.op.gen_b_segments,
            offset=self.op.sel_more,
            use_interp_simple=self.op.gen_b_clmp_ovrlp)


class FillBridgeedge(STACKS_Op):
    """Bridge selected edge loops in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.bridge_edge_loops(
            type=self.op.fill_bridge_type,
            use_merge=self.op.gen_extr_ind,
            merge_factor=self.op.gen_b_profile,
            twist_offset=int(self.op.gen_loop_smooth),
            number_cuts=self.op.gen_subd_cuts,
            interpolation=self.op.fill_bridge_interp,
            smoothness=self.op.fill_bridge_smooth,
            profile_shape_factor=self.op.fill_bridge_profile,
            profile_shape=self.op.gen_loop_falloff)


class FillFill(STACKS_Op):
    """Fill selected with triangles in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.fill(use_beauty=self.op.gen_subd_ngon)


class FillFillholes(STACKS_Op):
    """Try to fill missing polygons in the context mesh"""

    def operator(self) -> None:
        bpy.ops.mesh.fill_holes(sides=self.op.fill_holes)
