"""Cabeca nova do arqueiro dark (Blender -b): corta a malha de jogo no pescoco (z=ZC), remove o capuz de cabelo
e reconstroi pescoco+cabeca com aneis (rosto esculpido por gaussianas, ~1000 tris), material 1 (cabeca), UV cilindrica
com mais texel na frente. Pesos Head/Neck. Grava head_v2.blend e head_geo.npz."""
import bpy, bmesh, numpy as np, math, sys, os, json
from mathutils import Vector
W = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\corpo\work"
OUT = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\cabeca"
ZC = 1.47
NYC = 0.015
S = 0.000576            # m por pixel da imagem do close (frente)
bpy.ops.wm.open_mainfile(filepath=W + r"\game_uv.blend")
ob = bpy.data.objects["game"]; me = ob.data
bm = bmesh.new(); bm.from_mesh(me)
n0 = len(bm.faces)
r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, ZC), plane_no=(0, 0, 1), clear_outer=True)
bm.verts.ensure_lookup_table()
bnd = [v for v in bm.verts if any(e.is_boundary for e in v.link_edges)]
print("faces antes", n0, "depois", len(bm.faces), "boundary verts", len(bnd), "z", min(v.co.z for v in bnd), max(v.co.z for v in bnd))
cx = 0.0; cy = NYC
def phi(v): return math.atan2(v.co.x - cx, -(v.co.y - cy))
A = sorted([(phi(v), v) for v in bnd], key=lambda t: t[0])
ymn = min(v.co.y for v in bnd); ymx = max(v.co.y for v in bnd); xm = max(abs(v.co.x) for v in bnd)
print("anel velho: y", ymn, ymx, "xmax", xm, "cx,cy", cx, cy)

dl = bm.verts.layers.deform.verify()
ob_vg = {g.name: g.index for g in ob.vertex_groups}
uvl = bm.loops.layers.uv.verify()

ang = [-160, -135, -110, -90] + list(range(-70, 71, 10)) + [90, 110, 135, 160, 180]
ANG = [math.radians(a) for a in ang]
N = len(ANG)
# perfil: z, a (meia largura), df (frente), db (tras)
P = np.array([
 [1.5225, 0.047, 0.040, 0.050],
 [1.545, 0.032, 0.090, 0.056],
 [1.5625, 0.046, 0.094, 0.070],
 [1.58, 0.058, 0.095, 0.082],
 [1.595, 0.066, 0.097, 0.088],
 [1.61, 0.071, 0.096, 0.092],
 [1.625, 0.074, 0.095, 0.095],
 [1.64, 0.077, 0.094, 0.097],
 [1.652, 0.078, 0.093, 0.098],
 [1.665, 0.078, 0.092, 0.099],
 [1.678, 0.078, 0.094, 0.099],
 [1.69, 0.078, 0.092, 0.099],
 [1.705, 0.076, 0.087, 0.098],
 [1.72, 0.073, 0.080, 0.095],
 [1.735, 0.067, 0.069, 0.087],
 [1.75, 0.056, 0.057, 0.074],
 [1.763, 0.040, 0.041, 0.054],
 [1.773, 0.020, 0.021, 0.030]])
Z = P[:, 0]
def g(x, z, x0, z0, sx, sz): return math.exp(-0.5 * (((x - x0) / sx) ** 2 + ((z - z0) / sz) ** 2))
def sculpt(x, z):
    """delta y (negativo = para a frente) do rosto"""
    d = 0.0
    d += -0.030 * g(x, z, 0, 1.610, 0.011, 0.012)                  # ponta do nariz
    d += -0.014 * g(x, z, 0, 1.635, 0.007, 0.022)                  # dorso do nariz
    d += -0.010 * g(x, z, 0, 1.658, 0.008, 0.008)                  # raiz
    for s in (-1, 1):
        d += -0.012 * g(x, z, s * 0.016, 1.604, 0.007, 0.007)       # asas
        d += 0.005 * g(x, z, s * 0.041, 1.665, 0.018, 0.012)        # orbita
        d += -0.005 * g(x, z, s * 0.042, 1.686, 0.026, 0.010)       # arco da sobrancelha
        d += -0.006 * g(x, z, s * 0.057, 1.636, 0.020, 0.014)       # maca do rosto
        d += 0.006 * g(x, z, s * 0.030, 1.590, 0.008, 0.014)        # sulco nasolabial
        d += 0.0         # mandibula afinando
    d += -0.011 * g(x, z, 0, 1.589, 0.022, 0.006)                  # labio superior
    d += -0.010 * g(x, z, 0, 1.572, 0.020, 0.007)                  # labio inferior
    d += 0.004 * g(x, z, 0, 1.581, 0.024, 0.002)                   # linha da boca
    d += 0.004 * g(x, z, 0, 1.560, 0.012, 0.005)                   # sulco do queixo
    d += -0.007 * g(x, z, 0, 1.545, 0.013, 0.010)                  # queixo
    return d
YC0 = 0.0
rows = []
for k, (z, a, df, db) in enumerate(P):
    ring = []
    t = min(1.0, max(0.0, (z - 1.5225) / 0.04))
    yc = (1 - t) * cy + t * YC0
    for ps in ANG:
        c = math.cos(ps); s_ = math.sin(ps)
        x = a * s_; y = yc - (df if c > 0 else db) * c
        if c > 0.2:    # rosto
            wface = min(1.0, (c - 0.2) / 0.5)
            y += sculpt(x, z) * wface
        v = bm.verts.new((x, y, z))
        wh = min(1.0, max(0.0, (z - 1.51) / 0.05)); wh = wh * wh * (3 - 2 * wh)
        v[dl][ob_vg["Head"]] = wh; v[dl][ob_vg["Neck"]] = 1 - wh
        ring.append((ps if ps < math.pi - 1e-6 else math.pi, v))
    rows.append(ring)
apex = bm.verts.new((0, YC0 + 0.01, 1.781)); apex[dl][ob_vg["Head"]] = 1.0
new_faces = []
def zip_rings(A, B):
    M, Nn = len(A), len(B)
    def ang_(L, k): return L[k % len(L)][0] + (2 * math.pi if k >= len(L) else 0)
    i = j = 0
    while i < M or j < Nn:
        if i >= M: adv = 'B'
        elif j >= Nn: adv = 'A'
        else: adv = 'A' if ang_(A, i + 1) <= ang_(B, j + 1) else 'B'
        if adv == 'A':
            tri = (A[i % M][1], A[(i + 1) % M][1], B[j % Nn][1]); i += 1
        else:
            tri = (A[i % M][1], B[(j + 1) % Nn][1], B[j % Nn][1]); j += 1
        new_faces.append(bm.faces.new(tri))
zip_rings(A, rows[0])
for k in range(len(rows) - 1):
    zip_rings(rows[k], rows[k + 1])
last = rows[-1]
for i in range(N):
    new_faces.append(bm.faces.new((last[i][1], last[(i + 1) % N][1], apex)))
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
new_faces = [f for f in new_faces if f.is_valid]
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.normal_update()
# material e UV nas faces novas
def U_of(x, y):
    u = math.atan2(x, -(y - YC0)) / math.pi
    return u
def remap(u): return 0.5 + 0.5 * math.copysign(abs(u) ** 0.6, u)
VZ0, VZ1 = 1.47, 1.80
geo = []
for f in new_faces:
    f.material_index = 1
    us = []
    for l in f.loops:
        v = l.vert
        us.append(U_of(v.co.x, v.co.y) if v is not apex else None)
    known = [u for u in us if u is not None]
    if known and max(known) - min(known) > 1.0:
        us = [u + 2 if (u is not None and u < 0) else u for u in us]
    known = [u for u in us if u is not None]
    um = sum(known) / len(known)
    for l, u in zip(f.loops, us):
        uu = um if u is None else u
        l[uvl].uv = (remap(uu), (l.vert.co.z - VZ0) / (VZ1 - VZ0))
    geo.append(([tuple(l[uvl].uv) for l in f.loops], [tuple(l.vert.co) for l in f.loops], [tuple(l.vert.normal) for l in f.loops]))
for f in bm.faces: f.smooth = True
bm.to_mesh(me); bm.free()
me.update()
if len(me.materials) < 2: me.materials.append(None)
uv = np.array([g_[0] for g_ in geo]); pos = np.array([g_[1] for g_ in geo]); nor = np.array([g_[2] for g_ in geo])
np.savez(OUT + r"\head_geo.npz", uv=uv, pos=pos, nor=nor)
print("TRIS TOTAL", len(me.polygons), "novas", len(geo), "head N", N, "rows", len(rows))
bpy.ops.wm.save_as_mainfile(filepath=OUT + r"\head_v2.blend")
