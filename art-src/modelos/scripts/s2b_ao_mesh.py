"""Etapa 2b (venv, pymeshlab): malha alta reduzida (~150 mil triangulos) so para os raios de AO e cavidade (s6).
A BVH de 1 M de triangulos pedia > 6 GB livres; com 150 mil o assado cabe em < 1 GB. Grava work/high_ao.ply."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymeshlab
from mdl_common import *
cfg = load_cfg()
ms = pymeshlab.MeshSet()
ms.load_new_mesh(wpath(cfg, "high.ply"))
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=cfg.get("ao_mesh_faces", 150000), preservetopology=False, planarquadric=True, qualitythr=0.4)
print("S2b", ms.current_mesh().face_number())
ms.save_current_mesh(wpath(cfg, "high_ao.ply"), binary=True)
