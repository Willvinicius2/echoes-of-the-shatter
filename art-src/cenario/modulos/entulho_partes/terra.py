"""Parte 5 (terra): disco irregular de terra escura sob o monte, mais alto no centro para enterrar as bases das pedras
e baixando até o chão nas bordas (a pilha se funde ao piso da Cripta)."""
import bpy, bmesh, math
from mathutils import Vector, noise
from comum import rnd

def construir(M, centro=(0, 0), raio=1.3):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=26, y_segments=26, size=raio)
    for v in bm.verts: v.co.x += centro[0]; v.co.y += centro[1]
    off = Vector((rnd.uniform(0, 50), rnd.uniform(0, 50), 0))
    rem = []
    for v in bm.verts:
        r = math.hypot(v.co.x - centro[0], v.co.y - centro[1]); lim = raio * (0.78 + 0.22 * noise.noise(Vector((v.co.x, v.co.y, 0)) * 1.3 + off))
        if r > lim: rem.append(v); continue
        t = 1 - r / lim
        v.co.z = 0.36 * min(1.0, t * 1.05 / 1.0) * (0.85 + 0.3 * abs(noise.noise(Vector((v.co.x, v.co.y, 3)) * 3.0 + off))) - 0.02 if r < 1.25 else -0.015
    bmesh.ops.delete(bm, geom=rem, context='VERTS')
    me = bpy.data.meshes.new("terra"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("terra", me); bpy.context.collection.objects.link(o); me.materials.append(M["terra"])
    for p in me.polygons: p.use_smooth = False
    return o
