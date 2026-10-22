"""Parte 1 (forma): fragmentos de pedra de formas naturais. Nada de caixas com bisel:
- laje quebrada: caixa com cantos deslocados, cortada por 3-5 planos de fratura em ângulos livres e fechada pelo casco convexo;
- cascalho: casco convexo de nuvem de pontos achatada;
chanfros de larguras desiguais só em parte das arestas (pedra lascada, não usinada)."""
import bpy, bmesh, math
from mathutils import Vector
from comum import rnd

def _bevel_desigual(bm, base):
    arestas = [e for e in bm.edges if len(e.link_faces) == 2]
    for e in arestas: e.select = False
    escolha = [e for e in arestas if rnd.random() < 0.8]
    if not escolha: return
    # duas passadas com larguras diferentes: arestas “gastas” e arestas “vivas”
    gastas = [e for e in escolha if rnd.random() < 0.4]
    vivas = [e for e in escolha if e not in gastas]
    if vivas: bmesh.ops.bevel(bm, geom=vivas, offset=base * rnd.uniform(0.02, 0.05), segments=1, affect='EDGES')
    gastas = [e for e in gastas if e.is_valid]
    if gastas: bmesh.ops.bevel(bm, geom=gastas, offset=base * rnd.uniform(0.06, 0.13), segments=2, affect='EDGES')

def _hull(bm):
    r = bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    bmesh.ops.delete(bm, geom=list(set(r["geom_interior"] + r["geom_unused"])), context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

def _rugoso(bm, base, sub, amp=0.045):
    """Nenhuma face plana: subdivide e desloca os vértices com ruído em duas escalas (fratura grossa + grão), arestas ficam irregulares."""
    from mathutils import noise
    if sub > 0:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=sub, use_grid_fill=True)
    bm.normal_update()
    off = Vector((rnd.uniform(0, 99), rnd.uniform(0, 99), rnd.uniform(0, 99)))
    f1 = 3.0 / base; f2 = 11.0 / base
    for v in bm.verts:
        d = noise.noise(v.co * f1 + off) * amp + noise.noise(v.co * f2 + off) * amp * 0.45
        v.co += v.normal * d * base
    bm.normal_update()

def laje(size, fraturas=4, bev=True, sub=1):
    """Fragmento grande/médio de laje: tamanho (x,y,z) aproximado."""
    bm = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                j = lambda s: rnd.uniform(-0.10, 0.10) * s
                bm.verts.new((sx * size[0] / 2 + j(size[0]), sy * size[1] / 2 + j(size[1]), sz * size[2] / 2 + j(size[2])))
    _hull(bm)
    for _ in range(fraturas):
        n = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1) * 0.7)).normalized()
        d = Vector((n.x * size[0], n.y * size[1], n.z * size[2])).length * 0.5
        co = n * d * rnd.uniform(0.72, 0.97)
        res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=n, clear_outer=True)
        bord = [e for e in bm.edges if e.is_boundary]
        if bord: bmesh.ops.holes_fill(bm, edges=bord)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    # pontas quebradas: desloca poucos vértices para tirar a retidão perfeita das fraturas
    for v in bm.verts:
        v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.012 * min(size)
    _hull(bm)
    if bev: _bevel_desigual(bm, min(size))
    _rugoso(bm, min(size), sub, amp=0.08 if sub >= 2 else 0.06)
    return bm

def cascalho(r, achatado=0.6, pontos=10, sub=0):
    bm = bmesh.new()
    for _ in range(pontos):
        v = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1) * achatado))
        v.normalize(); v *= r * rnd.uniform(0.7, 1.15)
        bm.verts.new((v.x * rnd.uniform(0.8, 1.5), v.y, v.z))
    _hull(bm)
    _rugoso(bm, r, sub, amp=0.07)
    return bm

def para_objeto(bm, nome, mat, loc, rot):
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(nome, me); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot; me.materials.append(mat)
    for p in me.polygons: p.use_smooth = False
    return o
