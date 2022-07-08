 ##### BEGIN GPL LICENSE BLOCK #####
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

"""Blender «Stacks» add-on support for Custom Operators"""

from __future__ import annotations
import bpy
from bpy.types import Object, MeshVertices, Context, Operator, MeshEdges, MeshPolygons
from mathutils import Vector, Matrix
import numpy as np
from typing import Union

if __name__ == '__main__':
    try:  # PyCharm import
        from stacks_support_common import setmode, getmode
    except ModuleNotFoundError:  # Blender Text Editor import
        from stacks.stacks_support_common import setmode, getmode
else:  # Add-on import
    from .stacks_support_common import setmode, getmode


class STACKS_CUSTOM_Select_Vertices:
    def __init__(self, context: Context, op: Operator):
        self.context = context
        self.ob = context.object
        assert self.ob.type == "MESH"
        self.op = op
        self.verts = self.ob.data.vertices
        self.edges = self.ob.data.edges
        self.faces = self.ob.data.polygons
        self.clear_previous_selection = op.clear_previous_selection
        self.deselect = op.deselect
        self.vert_type = op.vert_type
        self.axis = op.axis
        self.pivot = op.pivot
        self.orientation = op.orientation
        self.center = Vector(op.center)
        self.target = bpy.data.objects[op.center_target] if op.center_target != "" \
                                                            and op.center_target in bpy.data.objects else None
        if self.vert_type in {"SPHERE", "ABOVE", "BELOW"} and self.pivot == "OBJECT" and self.target is None:
            return
        self.edgenum = op.edge_facenum
        self.facenum = op.face_vnum
        self.sphere_size = op.sphere_size
        self.more_than = op.more_than
        self.noise_threshold = op.noise_threshold  # for random noise
        self.noise_seed = op.noise_seed
        self.noise_scale = op.noise_scale
        self.noise_falloff = op.noise_falloff
        self.__select_vertices()

    def __select_vertices(self) -> None:
        """Get and select vertices"""
        setmode(self.context, "OBJECT")
        if not self.clear_previous_selection:
            already_selected = self.__already_selected()
        self.__deselect_all()
        selected = self.__get_selected_indices()
        if not self.clear_previous_selection:
            selected = self.__fix_selected(selected, already_selected, self.deselect)
        # print(f"Selected: {selected}")
        self.verts.foreach_set("select", selected)
        setmode(self.context, "EDIT")
        self.context.tool_settings.mesh_select_mode = (True, False, False)
        self.context.tool_settings.mesh_select_mode = (
            self.op.sel_mode_verts,
            self.op.sel_mode_edges,
            self.op.sel_mode_faces
        )

    def __already_selected(self) -> np.ndarray:
        verts = np.empty(len(self.verts), dtype=bool)
        self.verts.foreach_get("select", verts)
        edges = np.empty(len(self.edges), dtype=bool)
        self.edges.foreach_get("select", edges)
        faces = np.empty(len(self.faces), dtype=bool)
        self.faces.foreach_get("select", faces)
        return verts, edges, faces

    def __deselect_all(self) -> None:
        verts = np.empty(len(self.verts), dtype=bool)
        verts.fill(False)
        self.verts.foreach_set("select", verts)
        edges = np.empty(len(self.edges), dtype=bool)
        edges.fill(False)
        self.edges.foreach_set("select", edges)
        faces = np.empty(len(self.faces), dtype=bool)
        faces.fill(False)
        self.faces.foreach_set("select", faces)

    @staticmethod
    def __fix_selected(selected: np.ndarray, already_selected: np.ndarray, deselect: bool):
        """Sum or subtract new selection from already selected"""
        if deselect:
            selected = np.logical_not(selected)
            return np.logical_and(already_selected[0], selected)
        else:
            return np.logical_or(already_selected[0], selected)

    def __get_selected_indices(self) -> np.ndarray:
        """Get indices of vertices that are meant to be selected"""
        if self.vert_type in {"BELOW", "ABOVE", "SPHERE"}:
            selected = STACKS_CUSTOM_Select_Centered(self)
        elif self.vert_type == "EDGENUM":
            selected = STACKS_CUSTOM_Select_VertsByEdges(self)
        elif self.vert_type == "FACENUM":
            selected = STACKS_CUSTOM_Select_VertsByFaces(self)
        else:
            def selected():
                return []
        return selected()


class STACKS_CUSTOM_Select_Centered:
    def __init__(self, op: STACKS_CUSTOM_Select_Vertices):
        self.op = op
        self.selected = self.__centered()

    def __call__(self):
        return self.selected

    def __centered(self) -> np.array:
        """
        Return a list of indices of vertices that should be selected

        vert_type: {"BELOW", "ABOVE", "SPHERE", "EDGENUM", "FACENUM"}
        pivot: {"MANUAL", "OBJECT"}
            center: FloatVector
            target: Object
            threshold: Float
        orientation: {"GLOBAL", "LOCAL"}
        axis: {"X","Y","Z"}
        """
        assert self.op.vert_type in {"BELOW", "ABOVE", "SPHERE"}
        center = self.__get_center()
        verts = self.__get_verts_co()
        if self.op.vert_type in {"BELOW", "ABOVE"}:
            direction = {"BELOW": np.less, "ABOVE": np.greater}[self.op.vert_type]
            axis = {"X": 0, "Y": 1, "Z": 2}[self.op.axis]
            selected = self.__select_by_axis(center, verts, axis, direction, self.op.noise_threshold,
                                             self.op.noise_seed, self.op.noise_scale, self.op.noise_falloff)
        elif self.op.vert_type == "SPHERE":
            selected = self.__select_sphere(center, verts, self.op.sphere_size, self.op.noise_threshold,
                                            self.op.noise_seed, self.op.noise_scale, self.op.noise_falloff)
        else:
            raise NotImplementedError
        return selected

    def __get_center(self) -> Vector:
        """Get affect center"""
        if self.op.pivot == "MANUAL":
            center = self.op.center if self.op.orientation == "GLOBAL" else self.op.center + self.op.ob.location
        elif self.op.pivot == "OBJECT":
            center = self.op.target.location if self.op.target is not None else Vector((0, 0, 0))
        else:
            print(f"{self.op.pivot} pivot point is not implemented")
            raise NotImplementedError
        return center

    def __get_verts_co(self) -> np.ndarray:
        """Return numpy array with object vertices coordinates considering orientation"""
        verts = self.__verts_np(self.op.verts)
        if self.op.pivot == "MANUAL":
            if self.op.orientation == "GLOBAL":
                self.__vectors_transpose(verts, self.op.ob.matrix_world)
                self.__vectors_translate(verts, self.op.ob.matrix_world)
        elif self.op.pivot == "OBJECT":
            self.__vectors_transpose(verts, self.op.ob.matrix_world)
            if self.op.orientation == "LOCAL":
                self.__vectors_transpose(verts, self.op.target.matrix_world.inverted())
            self.__vectors_translate(verts, self.op.ob.matrix_world)
        else:
            print(f"{self.op.pivot} pivot point is not implemented")
            raise NotImplementedError
        return verts

    @staticmethod
    def __select_by_axis(center: Vector, verts: np.ndarray, axis: int, compare: Union[np.less, np.greater],
                         threshold: float, seed: int, scale: float, falloff: float) -> np.ndarray:
        """
        TODO: Implement Randomness

        :param center: mathutils.Vector, selection boarder
        :param verts: numpy array of 3D vertices coordinates
        :param axis: index of column
        :param compare: np.less or np.greater - function to compare 2 algorithms
        :param threshold: distance around the center to select vertices randomly
        :param threshold:
        """
        selected = compare(verts[:, axis], center[axis])
        if threshold > 0:
            pass
            # msg = "Selection blurring is not implemented yet"
            # bpy.ops.stacks.warning('INVOKE_DEFAULT', msg=msg, type="ERROR")
        return selected

    def __select_sphere(self, center: Vector, verts: np.ndarray, sphere_size: float,
                        threshold: float, seed: int, scale: float, falloff: float) -> np.ndarray:
        """
        TODO: Implement

        :param center: mathutils.Vector, selection boarder
        :param verts: numpy array of 3D vertices coordinates
        :param axis: index of column
        :param compare: np.less or np.greater - function to compare 2 algorithms
        :param threshold: distance around the center to select vertices randomly
        """
        distances = self.__distances(verts, center)
        if threshold > 0:
            msg = "Selection blurring is not implemented yet"
            bpy.ops.stacks.warning('INVOKE_DEFAULT', msg=msg, type="ERROR")
        return np.less(distances, sphere_size)

    @staticmethod
    def __distances(verts: np.ndarray, center: Vector) -> np.ndarray:
        """Return np array with distances from center to each vert"""
        vectors = verts-center
        return np.sqrt(np.einsum('ij,ij->i', vectors, vectors))

    @staticmethod
    def __verts_np(vertices: MeshVertices) -> np.ndarray:
        """Return vertices local coordinates as numpy array"""
        assert len(vertices)
        placeholder = np.zeros([len(vertices)*3], dtype="f")
        vertices.foreach_get("co", placeholder)
        verts = np.zeros([len(vertices), 3], dtype="f")
        verts[:, 0] = placeholder[0::3]
        verts[:, 1] = placeholder[1::3]
        verts[:, 2] = placeholder[2::3]
        return verts

    @staticmethod
    def __vectors_transpose(vectors: np.ndarray, matrix: Matrix) -> None:
        """
        Apply Rotation and Scale matrix to list of vectors

        :param vectors: numpy array with 3d vertex coordinates
        :param matrix: 4x4 object transformations mathutils.Matrix
        """
        vectors[:] = np.matmul(vectors, matrix.to_3x3().transposed())[:]

    @staticmethod
    def __vectors_translate(vectors: np.ndarray, matrix: Matrix) -> None:
        """
        Apply Location offset to list of vectors

        :param vectors: numpy array with 3d vertex coordinates
        :param matrix: 4x4 object transformations mathutils.Matrix
        """
        vectors[:] += matrix.translation


class STACKS_CUSTOM_Select_VertsByEdges:
    """Select vertices with specified number of adjacent edges"""
    def __init__(self, op: STACKS_CUSTOM_Select_Vertices):
        self.op = op
        self.selected = self.__by_edgenum()

    def __call__(self):
        return self.selected

    def __by_edgenum(self) -> np.array:
        """Return a list of indices of vertices that should be selected"""
        vert_indices = self.__verts_indices(self.op.verts)
        used_in_edges = self.__verts_edge_indices(self.op.edges)
        unique, count_num = np.unique(used_in_edges, return_counts=True)
        compare = {False: np.less, True: np.greater_equal}[self.op.more_than]
        after_threshold = compare(count_num, self.op.edgenum)
        filtered = unique[after_threshold]
        return np.isin(vert_indices, filtered)

    @staticmethod
    def __verts_indices(verts: MeshVertices) -> np.ndarray:
        """Numpy array with all vertices indices"""
        vert_indices = np.empty(len(verts), dtype=int)
        verts.foreach_get("index", vert_indices)
        return vert_indices

    @staticmethod
    def __verts_edge_indices(edges: MeshEdges) -> np.ndarray:
        """Numpy array with all edge vertices indices in mesh"""
        edge_vert_indices = np.empty(len(edges)*2, dtype=int)
        edges.foreach_get("vertices", edge_vert_indices)
        return edge_vert_indices


class STACKS_CUSTOM_Select_VertsByFaces:
    """Select vertices with specified number of adjacent edges"""
    def __init__(self, op: STACKS_CUSTOM_Select_Vertices):
        self.op = op
        self.selected = self.__by_facenum()

    def __call__(self):
        return self.selected

    def __by_facenum(self) -> np.array:
        """Return a list of indices of vertices that should be selected"""
        vert_indices = self.__verts_indices(self.op.verts)
        all_faces_verts_indices = self.__verts_face_indices(self.op.faces)
        unique, count_num = np.unique(all_faces_verts_indices, return_counts=True)
        compare = {False: np.less, True: np.greater_equal}[self.op.more_than]
        after_threshold = compare(count_num, self.op.facenum)
        filtered = unique[after_threshold]
        selected = np.isin(vert_indices, filtered)
        return selected

    @staticmethod
    def __verts_indices(verts: MeshVertices) -> np.ndarray:
        """Numpy array with all vertices indices"""
        vert_indices = np.empty(len(verts), dtype=int)
        verts.foreach_get("index", vert_indices)
        return vert_indices

    @staticmethod
    def __verts_face_indices(faces: MeshPolygons) -> np.ndarray:
        """Numpy array with all edge vertices indices in mesh"""
        faces_verts_nums = np.empty(len(faces), dtype=int)
        faces.foreach_get("loop_total", faces_verts_nums)  # Array with number of vertices for each face
        all_faces_verts_indices = np.empty(np.sum(faces_verts_nums), dtype=int)
        faces.foreach_get("vertices", all_faces_verts_indices)  # Array with all vertices indices in all faces
        return all_faces_verts_indices


class STACKS_CUSTOM_Select_Edges:
    pass


class STACKS_CUSTOM_Select_Faces:
    pass


class STACKS_CUSTOM_Decimate:
    def __init__(self, context: Context, op: Operator):
        mode = getmode(context)
        setmode(context, "OBJECT")
        self.context = context
        self.ob = context.object
        self.op = op
        self.limit_angle = op.limit_angle
        self.__decimate()
        setmode(context, mode)

    def __decimate(self) -> None:
        m = self.ob.modifiers.new("Decimate", "DECIMATE")
        m.decimate_type = 'DISSOLVE'
        m.angle_limit = self.limit_angle
        bpy.ops.object.modifier_apply(modifier=m.name)


class STACKS_CUSTOM_Boolean:
    def __init__(self, context: Context, op: Operator):
        mode = getmode(context)
        setmode(context, "OBJECT")
        self.context = context
        self.op = op
        self.ob = context.object
        self.object = None if op.object_name not in bpy.data.objects else bpy.data.objects[op.object_name]
        if op.subject == "OBJECT" and self.object is None:
            return
        if op.subject == "SELECTION":
            self.object = self.__ob_from_selection(self.context, self.ob)
        self.__boolean()
        setmode(context, mode)

    @staticmethod
    def __ob_from_selection(context: Context, ob: Object):
        selected = context.selected_objects[:]
        bpy.ops.object.select_all(action="DESELECT")
        setmode(context, "EDIT")
        bpy.ops.mesh.separate(type="SELECTED")
        setmode(context, "OBJECT")
        obj = [o for o in context.selected_objects if o != ob][0]
        for ob in selected:
            ob.select_set(True)
        return obj

    def __boolean(self):
        m = self.ob.modifiers.new('StacksBool', type='BOOLEAN')
        m.show_viewport = False
        m.operation = self.op.operation
        m.object = self.object
        m.solver = self.op.solver
        if self.op.solver == 'FAST':
            m.double_threshold = self.op.overlap_threshold
        elif self.op.solver == 'EXACT':
            m.use_self = self.op.self_intersection
            m.use_hole_tolerant = self.op.hole_tolerant
        bpy.ops.object.modifier_apply(modifier=m.name)
        if self.op.subject == 'SELECTION':
            bpy.data.objects.remove(self.object)
