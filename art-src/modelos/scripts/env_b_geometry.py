"""Etapa b (Python do venv: numpy, scipy, skimage, pymeshlab): geometria do cenario.

1. Limpeza da malha alta: componentes conexos; tira os fios horizontais flutuantes (pedacos finos, que vem das
   fatias da folha que entraram no alfa da imagem) e os pedacos soltos pequenos.
2. Solido externo (voxeliza, enche o exterior, marching cubes: some camada interna e fresta) -> malha de jogo por
   decimacao quadrica ate `tris`; a mesma casca, decimada a ~120 k, e a malha alta usada na AO.
3. Normalizacao: M = escala NAO uniforme minima * rotacao (piso: topo para +Z; canto: yaw que alinha o L) e pivo.
   Eixos com dims dadas recebem fator proprio; os demais, o fator uniforme medio (mantem a proporcao da IA).
Pecas `proc` (geometria da IA recusada) nascem de um superelipsoide com ruido, ja no quadro final.
Grava work/game_src.ply, work/high_src.ply (pose da fonte) e work/norm.json (M = A*src + t, caixa, componentes).
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pymeshlab
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from skimage import measure
from env_common import *

c = load_cfg()
t0 = time.time()
rep = {}


def save_ply(path, V, F):
    ms = pymeshlab.MeshSet(); ms.add_mesh(pymeshlab.Mesh(vertex_matrix=np.asarray(V, np.float64), face_matrix=np.asarray(F, np.int32)))
    ms.save_current_mesh(path, binary=True)


def noise3(P, seed, octaves=(1.0,)):
    rng = np.random.default_rng(seed)
    out = np.zeros(len(P))
    for oi, f in enumerate(octaves):
        d = rng.normal(size=(5, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
        ph = rng.uniform(0, 6.28, 5)
        out += (np.sin((P @ d.T) * 2.3 * f + ph).sum(1) / 5) / (oi + 1)
    return out


def superellipsoid(dims, p, noise, k, seed, hi=False):
    """Cubo-esfera k x k por face -> superelipsoide (p grande = bloco) com ruido; base achatada. Triangulos para fora."""
    pts = []
    g = np.linspace(-1, 1, k + 1)
    gu, gv = np.meshgrid(g, g, indexing="ij")
    one = np.ones_like(gu)
    for a in range(3):
        for s in (-1, 1):
            q = [None] * 3
            q[a] = s * one; q[(a + 1) % 3] = gu; q[(a + 2) % 3] = gv
            pts.append(np.stack(q, -1).reshape(-1, 3))
    P = np.concatenate(pts)
    key = np.round(P * 1e4).astype(np.int64)
    _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    D = P[idx]; D /= np.linalg.norm(D, axis=1, keepdims=True)
    # faces
    F = []
    n1 = (k + 1) * (k + 1); base = 0
    for _f in range(6):
        for i in range(k):
            for j in range(k):
                a_, b_, c_, d_ = (base + i * (k + 1) + j, base + (i + 1) * (k + 1) + j, base + (i + 1) * (k + 1) + j + 1, base + i * (k + 1) + j + 1)
                F += [[inv[a_], inv[b_], inv[c_]], [inv[a_], inv[c_], inv[d_]]]
        base += n1
    F = np.array(F)
    r = (np.abs(D) ** p).sum(1) ** (-1.0 / p)
    X = D * r[:, None]
    amp = noise * (noise3(X, seed, (1.0, 2.1)) + (0.5 * noise3(X * 2.7, seed + 1) if hi else 0))
    X = X * (1 + amp)[:, None]
    X = X * (np.array(dims) / 2)
    X[:, 2] = np.maximum(X[:, 2], -0.72 * dims[2] / 2)     # base achatada
    cen = X[F].mean(1); nrm = np.cross(X[F[:, 1]] - X[F[:, 0]], X[F[:, 2]] - X[F[:, 0]])
    flip = (nrm * (cen - X.mean(0))).sum(1) < 0
    F[flip] = F[flip][:, ::-1]
    return X, F


def pivot_t(c, lo, hi):
    if c["pivot"] == "floor_top":
        return np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -hi[2]])
    if c["pivot"] == "wall_outer":
        return np.array([-(lo[0] + hi[0]) / 2, -lo[1], -lo[2]])
    return np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])


if "proc" in c:
    pr = c["proc"]
    Vg, Fg = superellipsoid(pr["dims"], pr["p"], pr["noise"], pr["k"], pr["seed"])
    Vh, Fh = superellipsoid(pr["dims"], pr["p"], pr["noise"], 28, pr["seed"], hi=True)
    # a malha alta usa o mesmo ruido de baixa frequencia + um oitavo de relevo: reaplica a base achatada
    lo, hi = Vg.min(0), Vg.max(0)
    t = pivot_t(c, lo, hi)
    A = np.eye(3)
    norm = dict(A=A.tolist(), t=t.tolist(), src_lo=lo.tolist(), src_hi=hi.tolist(), final_lo=(lo + t).tolist(), final_hi=(hi + t).tolist(), final_dims=(hi - lo).tolist(), proc=True)
    save_ply(wpath(c, "game_src.ply"), Vg, Fg); save_ply(wpath(c, "high_src.ply"), Vh, Fh)
    save_json(wpath(c, "norm.json"), norm)
    print("EB proc", len(Fg), "tris", norm["final_dims"])
    raise SystemExit(0)

ms = pymeshlab.MeshSet(); ms.load_new_mesh(wpath(c, "raw.ply"))
m = ms.current_mesh(); V = m.vertex_matrix().astype(np.float64); F = m.face_matrix()
nv = len(V)
print("alta:", len(F), "faces", flush=True)

# 1. componentes conexos: tira fios finos flutuantes e pedacos soltos pequenos
e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]]])
G = coo_matrix((np.ones(len(e), np.int8), (e[:, 0], e[:, 1])), shape=(nv, nv))
nc, lab = connected_components(G, directed=False)
fl = lab[F[:, 0]]
cnt = np.bincount(fl, minlength=nc)
big = cnt.max()
full_ext = V.max(0) - V.min(0)
keep = np.ones(nc, bool); comp_rep = []
for ci in np.argsort(-cnt)[:40]:
    if cnt[ci] == 0: continue
    vs = V[lab == ci]; ext = np.sort(vs.max(0) - vs.min(0))
    thin = ext[0] < 0.025 * full_ext.max()             # folha ou fio flutuante (fatia da folha no alfa)
    small = cnt[ci] < c.get("min_ratio", 0.02) * big
    drop = (ci != np.argmax(cnt)) and (small or thin)
    if drop: keep[ci] = False
    comp_rep.append(dict(faces=int(cnt[ci]), ext=np.round(ext, 3).tolist(), dropped=bool(drop), thin=bool(thin)))
keep[cnt == 0] = False
smallest_dropped = int((~keep & (cnt > 0)).sum())
Fk = F[keep[fl]]
used = np.unique(Fk); remap = -np.ones(nv, np.int64); remap[used] = np.arange(len(used))
V = V[used]; F = remap[Fk]
rep["components"] = nc; rep["components_dropped"] = smallest_dropped; rep["faces_after_clean"] = len(F)
rep["top_components"] = comp_rep[:8]
print("componentes", nc, "removidos", smallest_dropped, "faces", len(F), round(time.time() - t0), "s", flush=True)

# 2. solido externo + decimacao
pitch = max(V.max(0) - V.min(0)) / c.get("shell_res", 340)
pad = 6
origin = V.min(0) - pad * pitch
pts = np.concatenate([V, V[F].mean(1), V[F[:, :2]].mean(1), V[F[:, 1:]].mean(1)])
idx = np.floor((pts - origin) / pitch).astype(int)
shape = tuple(idx.max(0) + pad + 1)
vox = np.zeros(shape, bool); vox[idx[:, 0], idx[:, 1], idx[:, 2]] = True
del pts, idx
vox = ndi.binary_closing(vox, iterations=c.get("shell_close", 2))
lab3, _ = ndi.label(~vox)
solid = ~(lab3 == lab3[0, 0, 0])
del lab3, vox
field = ndi.gaussian_filter(solid.astype(np.float32), c.get("shell_blur", 1.2))
vv, ff, _, _ = measure.marching_cubes(field, 0.5)
vv = origin + (vv + 0.5) * pitch
vol = np.einsum('ij,ij->i', vv[ff[:, 0]], np.cross(vv[ff[:, 1]], vv[ff[:, 2]])).sum() / 6
if vol < 0: ff = ff[:, ::-1]          # marching cubes devolve normais para dentro: orienta para fora
del field, solid
print("casca: voxel", round(pitch * 1000, 1), "mm, faces", len(ff), round(time.time() - t0), "s", flush=True)
ms = pymeshlab.MeshSet()
ms.add_mesh(pymeshlab.Mesh(vertex_matrix=vv, face_matrix=ff.astype(np.int32)))
ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53, stepsmoothnum=c.get("taubin_shell", 10))
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=min(120000, ms.current_mesh().face_number()), preservetopology=False,
                                            planarquadric=True, qualitythr=0.4, optimalplacement=True)
ms.meshing_remove_duplicate_vertices(); ms.meshing_remove_unreferenced_vertices()
ms.save_current_mesh(wpath(c, "high_src.ply"), binary=True)
Hv = ms.current_mesh().vertex_matrix().astype(np.float64)
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=max(2000, 6 * c["tris"]), preservetopology=False, planarquadric=True,
                                            qualitythr=0.4, optimalplacement=True)
ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53, stepsmoothnum=c.get("taubin_pre", 2))
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=c["tris"], preservetopology=False, planarquadric=True,
                                            preservenormal=True, qualitythr=0.5, optimalplacement=True)
ms.meshing_remove_duplicate_vertices(); ms.meshing_remove_unreferenced_vertices()
mg = ms.current_mesh(); Vg = mg.vertex_matrix().astype(np.float64); Fg = mg.face_matrix()
tm = ms.get_topological_measures()
rep["game_tris"] = int(len(Fg)); rep["closed"] = bool(tm["boundary_edges"] == 0)
print("jogo:", len(Fg), "tris, fechada", rep["closed"], "manifold", tm["is_mesh_two_manifold"], round(time.time() - t0), "s", flush=True)
ms.save_current_mesh(wpath(c, "game_src.ply"), binary=True)

# 3. normalizacao
R = np.eye(3)
if c.get("rot") == "floor":
    R = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)       # (x,y,z) -> (x,z,-y): a face da imagem (-Y) vira o topo (+Z)
yaw = 0.0
if c.get("auto_yaw"):
    best = None
    sub = Hv[:: max(1, len(Hv) // 20000)] @ R.T
    for a in np.arange(-90, 90.5, 1.0):
        th = np.radians(a); Rz = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
        q = sub @ Rz.T; ar = np.ptp(q[:, 0]) * np.ptp(q[:, 1])
        if best is None or ar < best[0]: best = (ar, a)
    yaw = best[1]; th = np.radians(yaw)
    R = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]]) @ R
rep["yaw_deg"] = yaw
Q = Hv @ R.T
ext = Q.max(0) - Q.min(0)
fac = [d / ext[i] if d else None for i, d in enumerate(c["dims"])]
given = [f for f in fac if f]
uni = float(np.exp(np.mean(np.log(given)))) if given else 1.0
fac = np.array([f if f else uni for f in fac])
A = np.diag(fac) @ R
Qf = Hv @ A.T
t = pivot_t(c, Qf.min(0), Qf.max(0))
lo, hi = Qf.min(0) + t, Qf.max(0) + t
rep["scale_factors"] = np.round(fac, 3).tolist(); rep["uniform_fill"] = round(uni, 3)
rep["nonuniform_ratio"] = round(float(fac.max() / fac.min()), 3)
norm = dict(A=A.tolist(), t=t.tolist(), src_lo=Hv.min(0).tolist(), src_hi=Hv.max(0).tolist(), final_lo=lo.tolist(), final_hi=hi.tolist(),
            final_dims=(hi - lo).tolist(), report=rep)
save_json(wpath(c, "norm.json"), norm)
print("EB", rep["game_tris"], "tris; final", np.round(hi - lo, 3).tolist(), "fatores", rep["scale_factors"], round(time.time() - t0), "s")
