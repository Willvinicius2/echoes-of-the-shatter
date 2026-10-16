"""Etapa 7a (Blender): exporta para a pintura (Python com numpy/scipy/cv2) a geometria da malha de jogo.

work/game_geo.npz: vertices, triangulos, posicao/normal/validade de cada texel da UV (1024) e a normal de canto.
"""
import bpy, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *

cfg = load_cfg()
bpy.ops.wm.open_mainfile(filepath=wpath(cfg, "game_uv.blend"))
ob = bpy.data.objects["game"]
v, f = mesh_arrays(ob)
g = texel_geometry(ob, cfg["tex_size"])
np.savez_compressed(wpath(cfg, "game_geo.npz"), verts=v.astype(np.float32), faces=f, valid=g["valid"],
                    pos=g["pos"].astype(np.float32), nrm=g["nrm"].astype(np.float32), tri=g["tri"].astype(np.int32))
print("S7a ok", v.shape, f.shape, int(g["valid"].sum()))
