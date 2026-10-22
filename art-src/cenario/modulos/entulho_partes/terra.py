"""Parte 5 (terra): disco irregular de terra escura sob o monte, mais alto no centro para enterrar as bases das pedras
e baixando até o chão nas bordas (a pilha se funde ao piso da Cripta)."""
import bpy, bmesh, math
from mathutils import Vector, noise
from comum import rnd

def construir(M, centro=(0, 0), raio=1.3):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=16, y_segments=16, size=raio)
    for v in bm.verts: v.co.x += centro[0]; v.co.y += centro[1]
    off = Vector((rnd.uniform(0, 50), rnd.uniform(0, 50), 0))
    rem = []
    for v in bm.verts:
        r = math.hypot(v.co.x - centro[0], v.co.y - centro[1]); lim = raio * (0.72 + 0.28 * noise.noise(Vector((v.co.x, v.co.y, 0)) * 1.8 + off))
        if r > lim:        # projeta na borda irregular (contorno liso e orgânico, sem dentes)
            k = lim / r; v.co.x = centro[0] + (v.co.x - centro[0]) * k; v.co.y = centro[1] + (v.co.y - centro[1]) * k; r = lim
        # perfil do outeiro = cone de apoio da física (0,36 m no centro, 1,2 m de raio), um pouco acima para enterrar as bases
        cone = max(0.0, 0.36 * (1 - r / 1.2)) + 0.02
        borda = min(1.0, max(0.0, (lim - r) / 0.25))             # bordas se diluem no chão
        v.co.z = cone * borda + (noise.noise(Vector((v.co.x, v.co.y, 3)) * 4.0 + off)) * 0.012 - 0.012 * (1 - borda)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.004)
    me = bpy.data.meshes.new("terra"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("terra", me); bpy.context.collection.objects.link(o); me.materials.append(M["terra"])
    for p in me.polygons: p.use_smooth = False
    return o
