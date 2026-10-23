"""Silhueta por linha da bota direita da imagem (boot B, personagem esquerda +X) de arq3d_botas.png -> botas_sil.json (xl, xr por py). Python do venv."""
import sys, json, numpy as np
from PIL import Image
from scipy import ndimage as ndi
im = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(np.float32)
bg = np.median(np.concatenate([im[:20].reshape(-1, 3), im[-20:].reshape(-1, 3)]), axis=0)
fg = np.sqrt(((im - bg) ** 2).sum(-1)) > 26
fg = ndi.binary_fill_holes(ndi.binary_opening(fg, iterations=1))
fg = ndi.binary_opening(fg, structure=np.ones((1, 41)))
sub = fg[:, 770:1110]
rows = []
for y in range(1024):
    xs = np.where(sub[y])[0]
    rows.append([int(xs.min() + 770), int(xs.max() + 770)] if len(xs) > 20 else None)
ys = [y for y, r in enumerate(rows) if r]
print("bg", bg, "y", ys[0], ys[-1])
for y in range(ys[0], ys[-1], 100): print(y, rows[y])
json.dump(dict(rows=rows, y0=ys[0], y1=ys[-1]), open(sys.argv[2], "w"))
