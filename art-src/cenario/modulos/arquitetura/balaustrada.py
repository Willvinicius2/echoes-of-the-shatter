"""Balaustrada de escada 3,0 x 0,5 x 1,2 m (horizontal; a montagem inclina): laje de base, balaústres torneados, corrimão de pedra, pilarete de ponta e pedestal com esfera na outra."""
import bpy, bmesh, math
from muro_baixo import cbox
from _pedra import cut
GLB = 'SM_Cripta_Balaustrada'
VISTAS = {
    "frente": ((0, 5.0, 0.7), (0, 0, 0.6), 900, 600),
    "tres_quartos": ((-2.8, 3.0, 2.2), (0, 0, 0.55), 900, 700),
    "close_pedestal": ((0.8, 1.6, 1.4), (1.25, 0, 0.8), 800, 800),
    "close_balaustres": ((-1.5, 1.4, 1.1), (-0.5, 0, 0.55), 800, 700),
}
HEROI_X, HEROI_Y = 2.0, 1.3
W = 3.0; D = 0.5

def lathe(L, name, prof, loc, m, sides=12, smooth=True):
    """Peça torneada: prof = [(raio, z)] de baixo para cima (raio 0 fecha o topo/base)."""
    bm = bmesh.new(); rings = []
    for r, z in prof:
        if r <= 1e-5: rings.append([bm.verts.new((0, 0, z))])
        else: rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / sides), r * math.sin(2 * math.pi * i / sides), z)) for i in range(sides)])
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1:
            for i in range(sides): bm.faces.new((a[0], b[(i + 1) % sides], b[i]))
        elif len(b) == 1:
            for i in range(sides): bm.faces.new((a[i], a[(i + 1) % sides], b[0]))
        else:
            for i in range(sides):
                j = (i + 1) % sides; bm.faces.new((a[i], a[j], b[j], b[i]))
    if len(rings[0]) > 1: bm.faces.new(rings[0][::-1])
    if len(rings[-1]) > 1: bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.location = loc
    for p in me.polygons: p.use_smooth = smooth
    L.add(o, m); return o

def build(L):
    sd, sc = L.stone('escura'), L.stone('clara')
    r = L.rng(11)
    # laje de base + friso inferior
    cbox(L, (0, 0, 0.07), (W, D, 0.14), sc, (6, 0.11, 3), bev=0.014)
    cbox(L, (-0.1, 0, 0.215), (2.6, D - 0.18, 0.15), sd, (4, 0.09, 4), bev=0.012)
    # balaústres torneados (9), um quebrado
    prof = [(0.07, 0.29), (0.07, 0.31), (0.052, 0.34), (0.05, 0.38), (0.085, 0.45), (0.095, 0.50), (0.06, 0.58), (0.05, 0.64), (0.075, 0.67), (0.075, 0.70)]
    for i in range(9):
        x = -1.1 + i * 0.245 + r.uniform(-0.006, 0.006)
        pr = prof
        if i == 5:   # quebrado: perde o topo, ponta irregular
            pr = prof[:6] + [(0.075, 0.55), (0.04, 0.585)]
        o = lathe(L, f"bal{i}", pr, (x, 0, 0), sd, 12)
        o.rotation_euler = (0, 0, r.uniform(0, 1))
        bpy.context.view_layer.objects.active = o
        L.bevel_obj(o, 0.004, 1, 40) if False else None
        # tampa fechada (base/topo) para volume
        bm = bmesh.new(); bm.from_mesh(o.data); bm.to_mesh(o.data); bm.free()
    # corrimão: duas camadas, a de cima arredondada
    cbox(L, (-0.1, 0, 0.745), (2.6, 0.3, 0.09), sc, (5, 0.1, 5), bev=0.03)
    cbox(L, (-0.1, 0, 0.82), (2.62, 0.38, 0.08), sc, (6, 0.1, 6), bev=0.03)
    cbox(L, (-0.1, 0.0, 0.9), (2.64, 0.28, 0.07), sc, (5, 0.1, 7), bev=0.03)
    # pilarete de ponta (-X): fuste + cornija + capa piramidal curta
    px = -1.4
    cbox(L, (px, 0, 0.45), (0.2, 0.34, 0.62), sd, (4, 0.1, 21), bev=0.012)
    cbox(L, (px, 0, 0.82), (0.26, 0.4, 0.1), sc, (4, 0.08, 22), bev=0.013)
    cbox(L, (px, 0, 0.94), (0.19, 0.3, 0.14), sc, (3, 0.08, 23), bev=0.013)
    # pedestal (+X) com esfera
    qx = 1.25
    cbox(L, (qx, 0, 0.18), (0.5, 0.5, 0.08), sc, (3, 0.09, 31), bev=0.012)
    f = cbox(L, (qx, 0, 0.53), (0.4, 0.4, 0.78), sd, (4, 0.1, 32), bev=0.012)
    for yy in (-1, 1):
        L.box((qx, yy * 0.206, 0.55), (0.2, 0.012, 0.42), sc, bev=0.004, seg=1)
    L.box((qx + 0.206, 0, 0.55), (0.012, 0.2, 0.42), sc, bev=0.004, seg=1)
    cbox(L, (qx, 0, 0.945), (0.5, 0.5, 0.09), sc, (5, 0.09, 33), bev=0.013)
    cbox(L, (qx, 0, 1.01), (0.38, 0.38, 0.05), sd, (3, 0.08, 34), bev=0.01)
    lathe(L, "colo", [(0.0001, 1.03), (0.12, 1.035), (0.08, 1.055), (0.07, 1.07), (0.0001, 1.07)], (qx, 0, 0), sc, 16)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, segments=36, ring_count=22, location=(qx, 0, 1.08))
    sp = bpy.context.object
    for p in sp.data.polygons: p.use_smooth = True
    L.add(sp, sc)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.1205, minor_radius=0.007, major_segments=36, minor_segments=8, location=(qx, 0, 1.08)); L.add(bpy.context.object, sd)
    L.col_box((0, 0, 0.6), (W, D, 1.2))
