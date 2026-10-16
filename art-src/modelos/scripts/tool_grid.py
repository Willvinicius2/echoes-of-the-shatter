"""Ferramenta (Blender): vistas frente e lado da malha de jogo com grade de 0,1 m * size_scale para ler marcos do esqueleto.

Grava work/grid_front.png e work/grid_side.png (1000 px; centro da caixa no meio; linhas finas a cada 0,1 m, grossas a
cada 0,5 m, a linha azul e z = 0; vermelha e x = 0 ou y = 0). Se cfg tiver markers (e quiser conferir), desenha as juntas.
"""
import bpy, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *

cfg = load_cfg()
bpy.ops.wm.open_mainfile(filepath=wpath(cfg, "game.blend"))
ob = bpy.data.objects["game"]
v, f = mesh_arrays(ob)
lo, hi = v.min(0), v.max(0); ctr = (lo + hi) / 2
EXT = 1.15 * float((hi - lo).max()); S = 1000; px = EXT / S
step = 0.1 * cfg["size_scale"]


def render(view):
    cols = {"front": (0, 2, 1), "side": (1, 2, 0)}[view]      # eixos horizontal, vertical, profundidade
    sx = 1 if view == "front" else -1
    u = (sx * (v[:, cols[0]] - ctr[cols[0]]) / px + S / 2)
    w = S / 2 - (v[:, cols[1]] - ctr[cols[1]]) / px
    img = np.full((S, S, 3), 0.25, np.float32)
    tris = np.stack([u[f], w[f]], -1)
    idx, _ = raster_tris(tris, S)
    sh = np.clip(0.35 + 0.5 * (idx >= 0) * 1.0, 0, 1)
    img[idx >= 0] = 0.75
    def col(a, c):
        img[:, a:a + 1] = c
    for k in range(-30, 31):
        c = k * step
        xx = int(S / 2 + sx * (c - (0 if view == "front" else 0) ) / px - sx * (ctr[cols[0]]) / px)
        if 0 <= xx < S:
            img[:, xx] = (1, 0.2, 0.2) if k == 0 else ((1, 0.7, 0.2) if k % 5 == 0 else (0.5, 0.35, 0.35))
        yy = int(S / 2 - (c - ctr[cols[1]]) / px)
        if 0 <= yy < S:
            img[yy, :] = (0.2, 0.3, 1) if k == 0 else ((1, 0.7, 0.2) if k % 5 == 0 else (0.35, 0.35, 0.5))
    return img
for view in ("front", "side"):
    save_png(render(view), wpath(cfg, f"grid_{view}.png"))
print("GRID ctr", ctr.round(3), "lo", lo.round(3), "hi", hi.round(3), "px/m", round(1 / px, 1), "step px", round(step / px, 1))
