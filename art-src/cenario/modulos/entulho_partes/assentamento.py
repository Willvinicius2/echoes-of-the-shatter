"""Parte 6 (assentamento final): nenhuma pedra flutua. Depois da física e da terra, cada pedra (de baixo para cima) desce
até tocar a terra, o chão ou uma pedra já assentada, e afunda um pouco (parcialmente enterrada)."""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def _bvh(objs):
    vs, ps = [], []
    for o in objs:
        b = len(vs); vs += [o.matrix_world @ v.co for v in o.data.vertices]
        ps += [tuple(b + i for i in p.vertices) for p in o.data.polygons]
    return BVHTree.FromPolygons(vs, ps) if ps else None

def assentar(pedras, terra, afundar=0.02, passes=2):
    bpy.context.view_layer.update()
    for _ in range(passes):
        ordem = sorted(pedras, key=lambda o: min((o.matrix_world @ v.co).z for v in o.data.vertices))
        feitas = [terra]
        for o in ordem:
            ws = [o.matrix_world @ v.co for v in o.data.vertices]
            zmin = min(w.z for w in ws)
            base = [w for w in ws if w.z < zmin + 0.12]
            bvh = _bvh(feitas); gap = None
            for w in base:
                d = w.z - 0.0                                  # chão em z=0
                if bvh:
                    h = bvh.ray_cast(Vector((w.x, w.y, w.z + 0.001)), Vector((0, 0, -1)), 3.0)
                    if h[0] is not None: d = min(d, w.z - h[0].z)
                gap = d if gap is None else min(gap, d)
            if gap is not None and gap > -0.2:
                o.location.z -= gap - afundar
                bpy.context.view_layer.update()
            feitas.append(o)
