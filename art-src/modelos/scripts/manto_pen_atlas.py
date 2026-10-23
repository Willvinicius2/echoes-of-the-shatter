"""Recorta o atlas de penas gerado (fundo azul chapado #0000FF, 2 linhas x 4 colunas) em alpha, descontamina a borda (sem halo azul),
puxa o rosa para vinho e monta o atlas 1024x2048 (celulas 256x1024, raiz da pena em cima). Grava pen_atlas_rgba.png e scripts/manto_penas.json
(retangulo da pena em cada celula). Python do venv. Uso: python -I manto_pen_atlas.py <pen_atlas.png> <saida_png>"""
import sys, os, json
import numpy as np, cv2
from scipy import ndimage as ndi
src, out = sys.argv[1:3]
im = cv2.imread(src)[..., ::-1].astype(np.float32)
H, W, _ = im.shape
blue = im[..., 2] - np.maximum(im[..., 0], im[..., 1])
a = np.clip(1 - (blue - 70) / 80, 0, 1)
a = np.clip((a - 0.2) / 0.8, 0, 1)
solid = a > 0.95
rgb = im.copy()
for _ in range(6):                                   # decontaminacao: cor das bordas vem do interior opaco
    acc = np.zeros_like(rgb); cnt = np.zeros(a.shape, np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            m = np.roll(np.roll(solid, dy, 0), dx, 1)
            acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * m[..., None]; cnt += m
    new = (~solid) & (cnt > 0)
    rgb[new] = acc[new] / cnt[new][:, None]; solid = solid | new
rgb[..., 2] = np.minimum(rgb[..., 2], np.maximum(rgb[..., 0], rgb[..., 1]) * 0.98)
# rosa -> vinho/framboesa menos saturado
pk = np.clip((rgb[..., 0] - rgb[..., 1] - 40) / 60, 0, 1)[..., None]
rgb = rgb * (1 - pk * 0.75) + pk * 0.75 * np.array((150, 44, 76), np.float32) * (rgb.mean(2, keepdims=True) / 165)
lab, n = ndi.label(a > 0.5)
sizes = ndi.sum(a > 0.5, lab, range(1, n + 1))
keep = np.argsort(-sizes)[:8] + 1
objs = ndi.find_objects(lab)
items = []
for k in keep:
    sl = objs[k - 1]
    items.append((sl[1].start, sl[0].start, sl))
rows = sorted(items, key=lambda t: t[1])
r0 = sorted(rows[:4], key=lambda t: t[0]); r1 = sorted(rows[4:], key=lambda t: t[0])
cw, chh = 256, 1024
AT = np.zeros((2048, 1024, 4), np.float32)
rects = []
for idx, (_, _, sl) in enumerate(r0 + r1):
    y0, y1, x0, x1 = sl[0].start - 2, sl[0].stop + 2, sl[1].start - 2, sl[1].stop + 2
    crop = np.dstack([rgb[y0:y1, x0:x1], a[y0:y1, x0:x1] * 255])
    h, w = crop.shape[:2]
    s = min((cw - 6) / w, (chh - 6) / h)
    nw, nh = max(1, int(w * s)), max(1, int(h * s))
    cr = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    cr[..., 3] = np.clip(cr[..., 3], 0, 255)
    c, r = idx % 4, idx // 4
    ox = c * cw + (cw - nw) // 2; oy = r * chh + 3
    AT[oy:oy + nh, ox:ox + nw] = cr
    rects.append([(cw - nw) // 2, 3, (cw - nw) // 2 + nw, 3 + nh])
AT[..., :3] = np.clip(AT[..., :3], 0, 255)
cv2.imwrite(out, np.dstack([AT[..., 2], AT[..., 1], AT[..., 0], AT[..., 3]]).astype(np.uint8))
json.dump(dict(rects=rects), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "manto_penas.json"), "w"))
print("PEN rects", rects)
