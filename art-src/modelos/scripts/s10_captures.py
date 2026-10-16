"""Etapa 10 (Python do venv): capturas para o Art Director e prancha.

Le work/captura_base.png (camera do jogo, transparente), recorta pela caixa do personagem e reduz com INTER_AREA para
512, 88 e 65 px de altura (mip 0, jogo a 1080p e Steam Deck) sobre cinza neutro. Grava final/previews/<asset>_captura_<N>px.png.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from mdl_common import *

cfg = load_cfg()
img = cv2.imread(wpath(cfg, "captura_base.png"), cv2.IMREAD_UNCHANGED)
a = img[..., 3] > 8
ys, xs = np.where(a)
crop = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32) / 255.0
for h in (512, 88, 65):
    w = max(1, round(crop.shape[1] * h / crop.shape[0]))
    r = cv2.resize(crop, (w, h), interpolation=cv2.INTER_AREA)
    pad = 6
    canvas = np.full((h + 2 * pad, w + 2 * pad, 3), 0.42, np.float32)
    al = r[..., 3:4]
    canvas[pad:pad + h, pad:pad + w] = r[..., :3] * al + canvas[pad:pad + h, pad:pad + w] * (1 - al)
    cv2.imwrite(fpath(cfg, f"previews/{cfg['asset']}_captura_{h}px.png"), (np.clip(canvas, 0, 1) * 255 + 0.5).astype(np.uint8))
print("S10 ok")
