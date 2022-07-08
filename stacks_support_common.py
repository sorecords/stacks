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

"""Blender «Stacks» add-on mixins"""

import bpy
from bpy.types import Context, Object, Scene

MODES = {
    'EDIT': 'EDIT_MESH',
    'OBJECT': 'OBJECT',
    'SCULPT': 'SCULPT',
    'VERTEX_PAINT': 'PAINT_VERTEX',
    'WEIGHT_PAINT': 'PAINT_WEIGHT',
    'TEXTURE_PAINT': 'PAINT_TEXTURE',
}


def map_range(value, oldmin, oldmax, newmin, newmax):
    assert oldmax - oldmin != 0
    return (value - oldmin) * (newmax - newmin) / (oldmax - oldmin) + newmin


def setmode(context: Context, mode: str) -> None:
    """Set context Blender mode to mode arg."""
    if context.mode in MODES.values():
        if not context.mode == MODES[mode]:
            bpy.ops.object.mode_set(mode=mode)
    elif not context.mode == mode:
        bpy.ops.object.mode_set(mode=mode)


def getmode(context: Context) -> str:
    """Return proper context mode to be set later"""
    if context.mode == 'EDIT_MESH':
        return 'EDIT'
    elif context.mode == 'PAINT_VERTEX':
        return 'VERTEX_PAINT'
    elif context.mode == 'PAINT_WEIGHT':
        return 'WEIGHT_PAINT'
    elif context.mode == 'PAINT_TEXTURE':
        return 'TEXTURE_PAINT'
    else:
        return context.mode


def setattr_protected(trg, atr, src) -> None:
    try:
        setattr(trg, atr, getattr(src, atr))
    except TypeError:
        return
    except RuntimeError:
        return
    except AttributeError:
        return


def set_selection(context: Context, sel: str = ""):
    """
    sel = "T-T-F|0,1,2-0,1,2-0,1,2"
           v e f|verts edges faces
           SMode| Element indices
    """
    setmode(context, 'EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    if not sel:
        return
    data = sel.split('|')
    modes = data[0].split('-')
    mode = (True if modes[0] == 'T' else False,
            True if modes[1] == 'T' else False,
            True if modes[2] == 'T' else False)
    context.tool_settings.mesh_select_mode = mode
    setmode(context, 'OBJECT')

    mesh = context.object.data
    mesh_data = data[1].split('-')
    verts = [int(v) for v in mesh_data[0].split(',')]
    edges = [int(v) for v in mesh_data[1].split(',')]
    faces = [int(v) for v in mesh_data[2].split(',')]
    for v in verts:
        mesh.vertices[v].select = True
    for e in edges:
        mesh.edges[e].select = True
    for f in faces:
        mesh.polygons[f].select = True


def get_override(context, area_t: str = 'VIEW_3D',
                 region_t: str = 'WINDOW') -> dict:
    win = context.window
    screen = win.screen
    area = [a for a in screen.areas if a.type == area_t][0]
    region = [r for r in area.regions if r.type == region_t][0]
    scene = context.scene
    override = {'window': win,
                'screen': screen,
                'area': area,
                'region': region,
                'scene': scene}
    return override


def obj_col_link(src: Object, trg: Object) -> None:
    """Link trg object to src object's collections"""
    for c in bpy.data.collections:
        if trg.name in c.objects:
            c.objects.unlink(trg)
        if src.name in c.objects:
            c.objects.link(trg)
    for sc in bpy.data.scenes:
        if trg.name in sc.collection.objects:
            sc.collection.objects.unlink(trg)
        if src.name in sc.collection.objects:
            sc.collection.objects.link(trg)


def obj_unlink(trg: Object) -> None:
    """Unlink trg Object from all collections and scenes"""
    for c in bpy.data.collections:
        if trg.name in c.objects:
            c.objects.unlink(trg)
    for sc in bpy.data.scenes:
        if trg.name in sc.collection.objects:
            sc.collection.objects.unlink(trg)


def obs_swap_names(ob1: Object, ob2: Object) -> None:
    """Swap objects names"""
    ob1.name, ob2.name = ob2.name, ob1.name
    ob1.data.name, ob2.data.name = ob2.data.name, ob1.data.name


def set_active_obj(context: Context, obj: Object) -> None:
    """Set object as context active object"""
    context.view_layer.objects.active = obj


def obj_lock(ob: Object, lock: bool) -> None:
    """Disable the ob object for selection"""
    ob.hide_select = lock
