"""Etapa 2 (Python do venv com pymeshlab): malha alta -> malha de jogo.

Decimacao quadrica em dois passos (alta -> 80k -> alvo) preservando topologia (sem buracos), com quadrica planar
e normais preservadas. Depois ajusta o numero de triangulos na faixa do 04 (5.500 a 6.500) e confere que a
malha continua fechada. Grava work/game_raw.ply.
Uso: python s2_decimate.py m01_guerreiro
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymeshlab
from mdl_common import *

cfg = load_cfg()
t0 = time.time()
ms = pymeshlab.MeshSet()
ms.load_new_mesh(wpath(cfg, "high.ply"))
print("alta:", ms.current_mesh().face_number())
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=80000, preservetopology=True, planarquadric=True,
                                            preservenormal=True, qualitythr=0.4, optimalplacement=True)
print("meio:", ms.current_mesh().face_number(), round(time.time() - t0))
# suaviza o ruido da decimacao sem encolher o volume (Taubin): volumes arredondados, sem lascas
ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53, stepsmoothnum=cfg.get("taubin_pre", 10))
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=cfg["tris_target"], preservetopology=True, planarquadric=True,
                                            preservenormal=True, qualitythr=0.5, optimalplacement=True)
ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53, stepsmoothnum=cfg.get("taubin_post", 6))
ms.meshing_remove_duplicate_vertices()
ms.meshing_remove_unreferenced_vertices()
m = ms.current_mesh()
tm = ms.get_topological_measures()
print("jogo:", m.face_number(), "vertices", m.vertex_number(), "medidas", tm, round(time.time() - t0), "s")
ms.save_current_mesh(wpath(cfg, "game_raw.ply"), binary=True)
