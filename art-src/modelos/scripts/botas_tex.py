"""Pinta o atlas das botas (BC, M, normal). Frente, tiras e metais: PROJETADOS do recorte da bota da direita de arq3d_botas.png (ampliado, afiado,
fundo cinza preenchido pelo couro vizinho). Couro liso (costas/laterais), madeira (sola e salto) e forro: procedurais com cores medidas da imagem.
Uso: python -I botas_tex.py <final_dir> <work_dir> <nome_textura> <imagem_entrada>"""
import sys, os
import numpy as np, cv2
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from botas_atlas import *
final, work, tex, src_png = sys.argv[1:5]
rng = np.random.default_rng(11)
IMG = cv2.imread(src_png)[..., ::-1].astype(np.float32)
C = np.zeros((N, N, 3), np.float32); C[:] = (34, 27, 25)
H = np.zeros((N, N), np.float32)


def noise(h, w, sc, amp):
    n = rng.standard_normal((max(2, h // sc), max(2, w // sc))).astype(np.float32)
    return cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) * amp


def rect_hw(k):
    x0, y0, x1, y1 = R[k]
    return y1 - y0, x1 - x0


# recorte frontal: tira o fundo cinza (preenche com o couro vizinho) e amplia
x0, y0, x1, y1 = SRCB
crop = IMG[y0:y1, x0:x1].copy()
bg = np.median(np.concatenate([IMG[:20].reshape(-1, 3), IMG[-20:].reshape(-1, 3)]), axis=0)
fg = np.sqrt(((crop - bg) ** 2).sum(-1)) > 26
fg = ndi.binary_erosion(ndi.binary_fill_holes(fg), iterations=3)
idx = ndi.distance_transform_edt(~fg, return_distances=False, return_indices=True)
crop = crop[idx[0], idx[1]]
h, w = rect_hw("front")
big = cv2.resize(crop, (w, h), interpolation=cv2.INTER_LANCZOS4)
bl = cv2.GaussianBlur(big, (0, 0), 2.2)
big = np.clip(big + 0.7 * (big - bl), 0, 255)
lum = big.mean(2)
hh = (cv2.GaussianBlur(lum, (0, 0), 1.2) - cv2.GaussianBlur(lum, (0, 0), 10)) / 55.0
fx0, fy0, fx1, fy1 = R["front"]
C[fy0:fy1, fx0:fx1] = big; H[fy0:fy1, fx0:fx1] = hh

# cores medidas: couro escuro liso (cano, sem tiras), marrom das tiras, rosa do forro
allc = crop[fg_small].reshape(-1, 3) if False else crop.reshape(-1, 3)
lum_l = allc.mean(1)
LEATH = np.median(allc[(lum_l > 28) & (lum_l < 80)], axis=0) * 0.95
print("couro", LEATH.round())
yy, xx = np.mgrid[0:512, 0:512].astype(np.float32)
img = np.zeros((512, 512, 3), np.float32) + LEATH
crack = np.abs(noise(512, 512, 24, 1.0)); crack = np.exp(-(crack / 0.05) ** 2)
img *= (0.88 + 0.22 * np.clip(noise(512, 512, 40, 0.6), -1, 1) * 0.5 + 0.12)[..., None]
img += noise(512, 512, 3, 2.5)[..., None]
img = img * (1 - 0.25 * crack[..., None]) + np.array((90, 50, 36), np.float32) * 0.25 * crack[..., None]
px0, py0, px1, py1 = R["plain"]
C[py0:py1, px0:px1] = img; H[py0:py1, px0:px1] = -crack * 0.22 + noise(512, 512, 5, 0.035)
# tira (nao usada na projecao, mas fica o couro marrom)
sx0, sy0, sx1, sy1 = R["strap"]
sh, sw = sy1 - sy0, sx1 - sx0
img = np.zeros((sh, sw, 3), np.float32) + (78, 50, 38) + noise(sh, sw, 4, 4)[..., None]
C[sy0:sy1, sx0:sx1] = img; H[sy0:sy1, sx0:sx1] = noise(sh, sw, 3, 0.1)
# metal
mx0, my0, mx1, my1 = R["metal"]
mh, mw = my1 - my0, mx1 - mx0
yy2, xx2 = np.mgrid[0:mh, 0:mw].astype(np.float32)
img = np.zeros((mh, mw, 3), np.float32) + np.array((150, 138, 132), np.float32) * (0.82 + 0.14 * np.sin(xx2 / 40 + yy2 / 70)[..., None]) + noise(mh, mw, 3, 5)[..., None]
C[my0:my1, mx0:mx1] = img; H[my0:my1, mx0:mx1] = noise(mh, mw, 3, 0.15)
# madeira da sola e do salto (listras de veio)
wx0, wy0, wx1, wy1 = R["wood"]
wh, ww = wy1 - wy0, wx1 - wx0
yy3, xx3 = np.mgrid[0:wh, 0:ww].astype(np.float32)
grain = np.sin(xx3 / 6.0 + 4 * noise(wh, ww, 40, 1.0)) * 0.5 + 0.5
img = np.zeros((wh, ww, 3), np.float32) + np.array((58, 40, 30), np.float32) * (0.8 + 0.35 * grain[..., None]) + noise(wh, ww, 3, 3)[..., None]
C[wy0:wy1, wx0:wx1] = img; H[wy0:wy1, wx0:wx1] = grain * 0.25 + noise(wh, ww, 3, 0.08)
# forro (borda interna do cano): rosa escuro
lx0, ly0, lx1, ly1 = R["lining"]
lh, lw = ly1 - ly0, lx1 - lx0
C[ly0:ly1, lx0:lx1] = np.array((96, 44, 58), np.float32) + noise(lh, lw, 5, 4)[..., None]

bc = np.clip(C, 0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(final, f"T_{tex}_BC.png"), bc[..., ::-1])
cv2.imwrite(os.path.join(final, f"T_{tex}_M.png"), np.zeros((N, N, 3), np.uint8))
Hs = cv2.GaussianBlur(H, (0, 0), 0.8)
dx = cv2.Sobel(Hs, cv2.CV_32F, 1, 0, ksize=3) / 8
dy = cv2.Sobel(Hs, cv2.CV_32F, 0, 1, ksize=3) / 8
s = 2.4
nrm = np.dstack([-dx * s, dy * s, np.ones_like(dx)])
nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
cv2.imwrite(os.path.join(work, "bake_normal.png"), ((nrm * 0.5 + 0.5) * 255).astype(np.uint8)[..., ::-1])
cv2.imwrite(os.path.join(work, "atlas_preview.png"), cv2.resize(bc[..., ::-1], (1024, 1024), interpolation=cv2.INTER_AREA))
print("TEX ok")
