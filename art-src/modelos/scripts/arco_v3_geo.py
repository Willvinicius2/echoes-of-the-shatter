"""Arco v3, etapa 1 (venv do TripoSG, CPU): alinha a malha alta (high.ply) a silhueta da imagem de entrada,
afina pontas e esporoes (vertices fora da silhueta sao puxados para dentro; profundidade limitada pela espessura local),
decima para o orcamento (haste + pontas) e grava high2.ply (alvo do bake) e low.ply.
Uso: python arco_v3_geo.py [tris_alvo]
v3: depois da decimacao corta as pontas curtas (plano perpendicular ao membro em |z|=ZC) em high3/low3 e grava as bordas
(loops) e a tangente em cut.json para arco_v3_blade.py construir as laminas."""
import os, sys, json, math
import numpy as np, cv2, pymeshlab as pml
from PIL import Image
from scipy import ndimage as ndi
ARCO = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\arco"
W2 = os.path.join(ARCO, "work3"); os.makedirs(W2, exist_ok=True)
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 2700

im = Image.open(os.path.join(ARCO, "arco_entrada_rgba.png")); a = np.array(im)
mask = a[..., 3] > 128
H, Wd = mask.shape
ys, xs = np.where(mask)
ms = pml.MeshSet(); ms.load_new_mesh(os.path.join(ARCO, "work", "high.ply"))
V = ms.current_mesh().vertex_matrix().astype(np.float64); F = ms.current_mesh().face_matrix()

def sil(par, sub=3):
    sx, sz, tx, tz = par
    u = tx + V[:, 0] * sx; v = tz - V[:, 2] * sz
    s = np.zeros((H, Wd), np.uint8)
    for t in np.stack([u[F[::sub]], v[F[::sub]]], -1).astype(np.int32):
        cv2.fillConvexPoly(s, np.ascontiguousarray(t), 1)
    return s > 0

def iou(par):
    s = sil(par); return (s & mask).sum() / (s | mask).sum()

sz0 = (ys.max() - ys.min()) / 1.1
par = np.array([sz0, sz0, (xs.min() + xs.max()) / 2, ys.max() - 0.55 * sz0])
best = iou(par); step = np.array([0.02 * sz0, 0.02 * sz0, 3.0, 3.0])
for it in range(5):
    for k in range(4):
        for sg in (1, -1):
            while True:
                p2 = par.copy(); p2[k] += sg * step[k]
                i2 = iou(p2)
                if i2 > best + 1e-4: par, best = p2, i2
                else: break
    step /= 2
print("IoU alinhado", round(best, 3), "par", par.round(2))
sx, sz, tx, tz = par
U = tx + V[:, 0] * sx; Vv = tz - V[:, 2] * sz       # pixels
# --- puxa para dentro da silhueta
inside = ndi.binary_erosion(mask, iterations=1)
dt_in = ndi.distance_transform_edt(inside)
dt_out, idx = ndi.distance_transform_edt(~inside, return_indices=True)
ui = np.clip(np.round(U).astype(int), 0, Wd - 1); vi = np.clip(np.round(Vv).astype(int), 0, H - 1)
out = ~inside[vi, ui]
U2 = U.copy(); V2 = Vv.copy()
U2[out] = idx[1][vi[out], ui[out]]; V2[out] = idx[0][vi[out], ui[out]]
print("vertices movidos", int(out.sum()), "de", len(V))
V[:, 0] = (U2 - tx) / sx; V[:, 2] = (tz - V2) / sz
# --- espessura em Y limitada pela largura local (lamina nas pontas)
dtm = dt_in[np.clip(np.round(V2).astype(int), 0, H - 1), np.clip(np.round(U2).astype(int), 0, Wd - 1)] / sx
lim = np.maximum(0.0028, 1.15 * dtm)
V[:, 1] = lim * np.tanh(V[:, 1] / lim)
ms = pml.MeshSet(); ms.add_mesh(pml.Mesh(V, F), "h")
ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53, stepsmoothnum=6)
# haste (regiao larga) bem mais lisa: o ruido do TripoSG nao gasta triangulos; pontas e esporoes ficam como estao
Vs = V.copy(); ms.add_mesh(pml.Mesh(ms.current_mesh().vertex_matrix(), F), "hs")
ms.apply_coord_taubin_smoothing(lambda_=0.6, mu=-0.64, stepsmoothnum=40)
Vh = ms.current_mesh().vertex_matrix(); Vl = ms.mesh(0).vertex_matrix() if False else None
wgt = np.clip((dtm - 0.011) / 0.008, 0, 1)[:, None]
ms.set_current_mesh(0); Vl = ms.current_mesh().vertex_matrix()
ms.current_mesh().vertex_matrix()[:] = Vl
mix = Vl * (1 - wgt) + Vh * wgt
ms = pml.MeshSet(); ms.add_mesh(pml.Mesh(mix, F), "h")
ms.save_current_mesh(os.path.join(W2, "high2.ply"))
# --- decimacao
ms.meshing_remove_duplicate_vertices(); ms.meshing_remove_unreferenced_vertices()
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=TARGET, qualitythr=0.6, preserveboundary=True, preservenormal=True,
                                           optimalplacement=True, planarquadric=True, autoclean=True)
ms.meshing_repair_non_manifold_edges(); ms.meshing_remove_unreferenced_vertices()
m = ms.current_mesh(); print("low tris", m.face_number(), "verts", m.vertex_number())

mlow = ms.current_mesh(); VL = mlow.vertex_matrix().copy(); FL = mlow.face_matrix().copy()
VH = mix.copy(); FH = F.copy()
ZC = 0.385
def slab_center(Vx, zz, sg):
    m = np.abs(sg * Vx[:, 2] - zz) < 0.012
    return Vx[m][:, 0].mean()
cut = {}
planes = {}
for sg in (1, -1):
    x1 = slab_center(VL, 0.33, sg); x2 = slab_center(VL, ZC, sg)
    th = math.atan2(x2 - x1, ZC - 0.33)
    T = np.array([math.sin(th), math.cos(th)])
    planes[sg] = (np.array([x2, ZC]), T, th)
    print("ponta", sg, "c0", round(x2, 4), "theta graus", round(math.degrees(th), 1))
def do_cut(Vx, Fx):
    keep = np.ones(len(Fx), bool)
    cen = Vx[Fx].mean(1)
    for sg in (1, -1):
        c0, T, th = planes[sg]
        d = (sg * cen[:, 2] - c0[1]) * T[1] + (cen[:, 0] - c0[0]) * T[0]
        keep &= ~((sg * cen[:, 2] > 0.2) & (d > 0))
    Fk = Fx[keep]
    # maior componente por conectividade
    import scipy.sparse as sp
    from scipy.sparse.csgraph import connected_components
    n = len(Vx); e = np.concatenate([Fk[:, [0, 1]], Fk[:, [1, 2]]])
    g = sp.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n))
    _, lab = connected_components(g, directed=False)
    cnt = np.bincount(lab[Fk[:, 0]]); big = cnt.argmax()
    Fk = Fk[lab[Fk[:, 0]] == big]
    return Fk
FLk = do_cut(VL, FL); FHk = do_cut(VH, FH)
def loops(Vx, Fx):
    ed = np.sort(np.concatenate([Fx[:, [0, 1]], Fx[:, [1, 2]], Fx[:, [2, 0]]]), 1)
    u, c = np.unique(ed, axis=0, return_counts=True)
    b = u[c == 1]; vs = np.unique(b)
    return vs, b
vs, b = loops(VL, FLk)
out = {}
for sg in (1, -1):
    c0, T, th = planes[sg]
    sel = [v for v in vs if sg * VL[v, 2] > 0.2]
    P = VL[sel].astype(float)
    print("loop", sg, "verts", len(sel), "zrange", P[:, 2].min().round(3), P[:, 2].max().round(3))
    out[str(sg)] = dict(c0=c0.tolist(), T=T.tolist(), theta=th, loop=P.tolist())
json.dump(out, open(os.path.join(W2, "cut.json"), "w"))
def save(Vx, Fx, name):
    m2 = pml.MeshSet(); m2.add_mesh(pml.Mesh(Vx, Fx), "x"); m2.meshing_remove_unreferenced_vertices()
    m2.save_current_mesh(os.path.join(W2, name)); return m2.current_mesh().face_number()
print("high3", save(VH, FHk, "high3.ply"), "low3 (haste) tris", save(VL, FLk, "low3.ply"))
json.dump(dict(par=par.tolist(), iou=best, tris=int(len(FLk))), open(os.path.join(W2, "geo_report.json"), "w"))
