"""Etapa 1p (Python do venv com trimesh, scipy, pymeshlab): GLB de uma peca modular -> malha alta encaixada no corpo.

As GLB de peca vem normalizadas numa caixa de +-0,95 (escala arbitraria). Aqui: converte glTF (Y cima) para o Blender
(x, -z, y), gira (rot_z_deg), tira pedacos soltos, e encaixa no espaco do corpo base (1,50 m, pes em z = 0, frente -Y):
  fit.mode "box": mapeia a caixa da peca para fit.box = [x0, x1, y0, y1, z0, z1] (escala por eixo, ate fit.uniform_xy);
  fit.mode "uniform": escala uniforme pelo eixo fit.match ("x","y","z") ate fit.size e alinha por fit.anchor.
Mirror de maos e pes: s8 faz o par. Grava work/high.ply (<= high_faces) e work/norm.json.
Uso: python -I s1p_piece_prepare.py <personagem>
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh, pymeshlab
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from mdl_common import *

cfg = load_cfg()
m = trimesh.load(cfg["src_glb"], force="mesh", process=False)
V = np.asarray(m.vertices, np.float64); F = np.asarray(m.faces)
V = np.stack([V[:, 0], -V[:, 2], V[:, 1]], 1)                   # glTF -> Blender
a = np.radians(cfg.get("rot_z_deg", 0.0))
R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
V = V @ R.T
if cfg.get("flip_x"):
    V[:, 0] *= -1; F = F[:, ::-1]
# pedacos soltos
n = len(V)
e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]]])
g = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n))
nc, lab = connected_components(g, directed=False)
fl = lab[F[:, 0]]
cnt = np.bincount(fl, minlength=nc)
keep = cnt >= max(cfg.get("min_component_faces", 0), cfg.get("min_component_ratio", 0.005) * cnt.max())
F = F[keep[fl]]
used = np.unique(F)
remap = -np.ones(n, int); remap[used] = np.arange(len(used))
V = V[used]; F = remap[F]
lo, hi = V.min(0), V.max(0)
fit = cfg["fit"]
if fit["mode"] == "box":
    b = np.array(fit["box"], float).reshape(3, 2)
    s = (b[:, 1] - b[:, 0]) / (hi - lo)
    if fit.get("uniform_xy"):
        sxy = np.sqrt(s[0] * s[1]) if fit["uniform_xy"] == "geo" else min(s[0], s[1])
        s[0] = s[1] = sxy
    V = (V - (lo + hi) / 2) * s + (b[:, 0] + b[:, 1]) / 2
else:
    ax = {"x": 0, "y": 1, "z": 2}[fit["match"]]
    s = fit["size"] / (hi[ax] - lo[ax])
    c = (lo + hi) / 2
    V = (V - c) * s
    lo2, hi2 = V.min(0), V.max(0)
    for i, k in enumerate("xyz"):
        an = fit.get("anchor", {}).get(k)
        if an is None:
            continue
        if isinstance(an, (int, float)):
            V[:, i] += an - (lo2[i] + hi2[i]) / 2
        else:       # ["min", valor] ou ["max", valor]
            V[:, i] += an[1] - (lo2[i] if an[0] == "min" else hi2[i])
V += np.array(fit.get("offset", [0, 0, 0]))
ms = pymeshlab.MeshSet()
ms.add_mesh(pymeshlab.Mesh(vertex_matrix=V, face_matrix=F.astype(np.int32)))
hf = cfg.get("high_faces", 800000)
if ms.current_mesh().face_number() > hf:
    ms.meshing_decimation_quadric_edge_collapse(targetfacenum=hf, preservetopology=False, qualitythr=0.4)
ms.save_current_mesh(wpath(cfg, "high.ply"), binary=True)
Vh = ms.current_mesh().vertex_matrix()
info = dict(faces_src=int(len(m.faces)), faces_kept=int(len(F)), faces_high=int(ms.current_mesh().face_number()),
            bbox_min=Vh.min(0).tolist(), bbox_max=Vh.max(0).tolist(), height_total=float(Vh[:, 2].max()))
save_json(wpath(cfg, "norm.json"), info)
print("S1p", info)
