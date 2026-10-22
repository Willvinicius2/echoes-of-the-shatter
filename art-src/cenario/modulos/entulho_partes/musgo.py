"""Parte 3: musgo em tufos irregulares (blobs facetados, achatados e sobrepostos) nas faces de cima e nas quinas laterais."""
import bpy, bmesh
from mathutils import Vector
from comum import rnd

def _tufo(c, nw, r, M):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
    for v in bm.verts:
        v.co = Vector((v.co.x * rnd.uniform(0.6, 2.0), v.co.y * rnd.uniform(0.6, 2.0), v.co.z * 0.38 * rnd.uniform(0.6, 1.8)))
    me = bpy.data.meshes.new("m"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("m", me); bpy.context.collection.objects.link(o)
    o.location = c - nw * 0.004 + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * r * 0.5
    o.rotation_euler = (rnd.uniform(-.2, .2), rnd.uniform(-.2, .2), rnd.uniform(0, 6.28))
    me.materials.append(M["musgo"])
    for p in me.polygons: p.use_smooth = False
    return o

def construir(M, blocos, n=22):
    cand = []
    for o in blocos:
        mw = o.matrix_world
        for p in o.data.polygons:
            nw = (mw.to_3x3() @ p.normal).normalized()
            if nw.z > 0.2 and p.area > 0.004: cand.append((mw @ p.center, nw, p.area))
    if not cand: return []
    out = []
    for _ in range(n):
        c, nw, _a = rnd.choices(cand, weights=[a for *_x, a in cand])[0]
        for _k in range(3):      # dois blobs por ponto: mancha de borda irregular
            out.append(_tufo(c, nw, rnd.uniform(0.035, 0.085), M))
    return out
