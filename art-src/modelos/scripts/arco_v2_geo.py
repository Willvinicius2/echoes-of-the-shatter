"""Arco do Arqueiro Dark v2, etapa 1 (venv do TripoSG, CPU): alinha a malha alta (high.ply) a silhueta da imagem de entrada,
afina pontas e esporoes (vertices fora da silhueta sao puxados para dentro; profundidade limitada pela espessura local),
decima para o orcamento (haste + pontas) e grava high2.ply (alvo do bake) e low.ply.
Uso: python arco_v2_geo.py [tris_alvo]"""
import os, sys, json
import numpy as np, cv2, pymeshlab as pml
from PIL import Image
from scipy import ndimage as ndi
ARCO = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\arco"
W2 = os.path.join(ARCO, "work2"); os.makedirs(W2, exist_ok=True)
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
ms.save_current_mesh(os.path.join(W2, "low.ply"))
json.dump(dict(par=par.tolist(), iou=best, tris=m.face_number()), open(os.path.join(W2, "geo_report.json"), "w"))
