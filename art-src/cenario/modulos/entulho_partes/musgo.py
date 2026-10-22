"""Parte 3 (musgo): almofadas volumétricas (icosfera subdividida, achatada e deslocada por ruído) nas frestas e topos,
com satélites menores ao redor para bordas irregulares; assentam alinhadas à superfície e afundam um pouco na pedra."""
import bpy, bmesh
from mathutils import Vector, noise
from comum import rnd

def _almofada(c, nw, r, sub, M):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    off = Vector((rnd.uniform(0, 50), rnd.uniform(0, 50), rnd.uniform(0, 50)))
    ex, ey = rnd.uniform(0.7, 1.6), rnd.uniform(0.7, 1.3)
    for v in bm.verts:
        n = noise.noise(v.co * (7.0 / r) + off) * 0.35 + 1.0
        v.co = Vector((v.co.x * ex * n, v.co.y * ey * n, v.co.z * 0.42 * (0.7 + 0.6 * abs(noise.noise(v.co * (11.0 / r) + off)) + 0.3)))
    me = bpy.data.meshes.new("m"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("m", me); bpy.context.collection.objects.link(o)
    o.location = c - nw * r * 0.12
    o.rotation_euler = nw.to_track_quat('Z', 'Y').to_euler(); o.rotation_euler.rotate_axis('Z', rnd.uniform(0, 6.28))
    me.materials.append(M["musgo"])
    for p in me.polygons: p.use_smooth = rnd.random() < 0.0
    return o

def construir(M, blocos, n=8):
    cand = []
    for o in blocos:
        mw = o.matrix_world
        for p in o.data.polygons:
            nw = (mw.to_3x3() @ p.normal).normalized(); c = mw @ p.center
            if nw.z > 0.3 and p.area > 0.002 and c.z > 0.03:
                cand.append((c, nw, p.area * (1.25 - min(c.z, 1.0)) * (0.4 + nw.z)))   # prefere frestas baixas e topos
    if not cand: return []
    out = []
    for _ in range(n):
        c, nw, _a = rnd.choices(cand, weights=[a for *_x, a in cand])[0]
        out.append(_almofada(c, nw, rnd.uniform(0.05, 0.09), 2, M))
        for _k in range(4):      # satélites: bordas irregulares e mistura com a pedra
            d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized() * rnd.uniform(0.05, 0.1)
            q = nw.to_track_quat('Z', 'Y'); d = q @ d
            out.append(_almofada(c + d, nw, rnd.uniform(0.025, 0.045), 1, M))
    return out
