"""Etapa 2 (Python do venv com numpy, scipy, skimage, pymeshlab): malha alta -> malha de jogo.

1. Solido externo: voxeliza a malha alta (passo = maior dimensao / shell_res), enche o exterior por inundacao a
   partir da borda e fica so com o que o exterior nao alcanca. Camadas internas (corpo sob a armadura, folgas
   fechadas, cavidades) somem; frestas mais finas que o voxel fecham. A superficie volta por marching cubes (campo
   suavizado) e um Taubin leve limpa a escada dos voxels e as bordas finas da pluma e da silhueta.
2. Decimacao quadrica em dois passos (-> 80 k -> alvo) preservando topologia, quadrica planar e normais.
A malha alta original (work/high.ply) continua sendo a fonte de AO, cavidade e cor; so a malha de jogo nasce do
solido externo. Grava work/shell.ply e work/game_raw.ply.
Uso: python -I s2_decimate.py m01_guerreiro
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pymeshlab
from scipy import ndimage as ndi
from skimage import measure
from mdl_common import *

cfg = load_cfg()
t0 = time.time()
ms = pymeshlab.MeshSet()
ms.load_new_mesh(wpath(cfg, "high.ply"))
m = ms.current_mesh()
V = m.vertex_matrix().astype(np.float64); F = m.face_matrix()
print("alta:", len(F))

if cfg.get("outer_shell", True):
    pitch = max(V.max(0) - V.min(0)) / cfg.get("shell_res", 420)
    pad = 6
    origin = V.min(0) - pad * pitch
    pts = np.concatenate([V, V[F].mean(1), V[F[:, :2]].mean(1), V[F[:, 1:]].mean(1)])
    idx = np.floor((pts - origin) / pitch).astype(int)
    shape = tuple(idx.max(0) + pad + 1)
    vox = np.zeros(shape, bool)
    vox[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    body_in = None
    if cfg.get("body_fill_ply"):
        # peca modular: o corpo base preenche a cavidade (o miolo oco deixa de ser alcancavel pelo exterior); o solido
        # da peca e o que sobra tirando o volume do corpo. Corpo voxelizado em grade propria de 4 mm e lido por indice.
        bms = pymeshlab.MeshSet(); bms.load_new_mesh(cfg["body_fill_ply"])
        bV = bms.current_mesh().vertex_matrix().astype(np.float64); bF = bms.current_mesh().face_matrix()
        bp = 0.004 * cfg["size_scale"]
        bo = bV.min(0) - 3 * bp
        bpts = np.concatenate([bV, bV[bF].mean(1)] + [bV[bF][:, [i, j]].mean(1) for i, j in ((0, 1), (1, 2), (0, 2))])
        # amostra densa nas faces (triangulos grandes da malha de jogo): subdivide por baricentricas
        for a_, b_ in ((0.25, 0.25), (0.5, 0.25), (0.25, 0.5), (0.1, 0.1), (0.8, 0.1), (0.1, 0.8)):
            bpts = np.concatenate([bpts, bV[bF[:, 0]] * a_ + bV[bF[:, 1]] * b_ + bV[bF[:, 2]] * (1 - a_ - b_)])
        bi = np.floor((bpts - bo) / bp).astype(int)
        bshape = tuple(bi.max(0) + 4)
        bv = np.zeros(bshape, bool); bv[bi[:, 0], bi[:, 1], bi[:, 2]] = True
        bv = ndi.binary_closing(bv, iterations=2)
        bl, _ = ndi.label(~bv)
        bsolid = ~(bl == bl[0, 0, 0])
        gi = np.stack(np.meshgrid(*[np.arange(n_) for n_ in shape], indexing="ij"), -1)
        cen = origin + (gi + 0.5) * pitch
        bidx = np.floor((cen - bo) / bp).astype(int)
        okb = np.all((bidx >= 0) & (bidx < np.array(bshape)), -1)
        body_in = np.zeros(shape, bool)
        body_in[okb] = bsolid[bidx[okb][:, 0], bidx[okb][:, 1], bidx[okb][:, 2]]
        del gi, cen, bidx
        vox = vox | body_in
    vox = ndi.binary_closing(vox, iterations=cfg.get("shell_close", 1))
    lab, n = ndi.label(~vox)
    ext = lab == lab[0, 0, 0]
    solid = ~ext
    if body_in is not None:
        solid = solid & ~body_in
    inner = int(((~ext) & ~vox).sum())      # voxels vazios fechados (cavidades) que viram solido
    field = ndi.gaussian_filter(solid.astype(np.float32), cfg.get("shell_blur", 1.0))
    vv, ff, _, _ = measure.marching_cubes(field, cfg.get("shell_level", 0.5))
    vv = origin + (vv + 0.5) * pitch
    print("casca externa: voxel", round(pitch * 1000, 1), "mm, cavidades fechadas preenchidas", inner, "voxels, faces", len(ff),
          round(time.time() - t0), "s")
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(vertex_matrix=vv, face_matrix=ff.astype(np.int32)))
    ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53, stepsmoothnum=cfg.get("taubin_shell", 8))
    ms.save_current_mesh(wpath(cfg, "shell.ply"), binary=True)

ms.meshing_decimation_quadric_edge_collapse(targetfacenum=min(80000, ms.current_mesh().face_number()), preservetopology=cfg.get("preserve_topology", True),
                                            planarquadric=True, preservenormal=True, qualitythr=0.4, optimalplacement=True)
print("meio:", ms.current_mesh().face_number(), round(time.time() - t0))
ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53, stepsmoothnum=cfg.get("taubin_pre", 3))
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=cfg.get("tris_target_pre", cfg["tris_target"]), preservetopology=cfg.get("preserve_topology", True), planarquadric=True,
                                            preservenormal=True, qualitythr=0.5, optimalplacement=True)
ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53, stepsmoothnum=cfg.get("taubin_post", 2))
ms.meshing_remove_duplicate_vertices()
ms.meshing_remove_unreferenced_vertices()
m = ms.current_mesh()
tm = ms.get_topological_measures()
print("jogo:", m.face_number(), "vertices", m.vertex_number(), "genus", tm["genus"], "fechada", tm["boundary_edges"] == 0,
      "manifold", tm["is_mesh_two_manifold"], round(time.time() - t0), "s")
ms.save_current_mesh(wpath(cfg, "game_raw.ply"), binary=True)
