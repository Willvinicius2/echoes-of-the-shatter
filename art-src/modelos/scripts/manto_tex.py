"""Pinta o atlas do torso (BC, M, normal). Penas e base: procedural (cores medidas da imagem de entrada). Colete, correias, cinto,
gola e tabardo: PROJETADOS (recortes de arq3d_manto, ampliados e afiados). Python do venv.
Uso: python -I manto_tex.py <final_dir> <work_dir> <nome_textura> <imagem_entrada_rgba>"""
import sys, os
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manto_atlas import *
final, work, tex, src_png = sys.argv[1:5]
rng = np.random.default_rng(7)
SRCIMG = cv2.imread(src_png)[..., ::-1].astype(np.float32)           # RGB
C = np.zeros((N, N, 3), np.float32); C[:] = (30, 27, 32)
H = np.zeros((N, N), np.float32)


def noise(h, w, sc, amp):
    n = rng.standard_normal((max(2, h // sc), max(2, w // sc))).astype(np.float32)
    return cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) * amp


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def rect_hw(k):
    x0, y0, x1, y1 = R[k]
    return y1 - y0, x1 - x0


def crop_to(k, sharpen=0.8, hgain=0.5):
    """recorte da imagem de entrada ampliado ao retangulo k do atlas; devolve (rgb, altura)."""
    x0, y0, x1, y1 = SRC[k]
    c = SRCIMG[y0:y1, x0:x1]
    h, w = rect_hw(k)
    c = cv2.resize(c, (w, h), interpolation=cv2.INTER_LANCZOS4)
    bl = cv2.GaussianBlur(c, (0, 0), 2.0)
    c = np.clip(c + sharpen * (c - bl), 0, 255)
    lum = c.mean(2)
    hh = (cv2.GaussianBlur(lum, (0, 0), 1.2) - cv2.GaussianBlur(lum, (0, 0), 9)) / 40.0 * hgain
    return c, hh


def put(k, img, hh=None):
    x0, y0, x1, y1 = R[k]
    C[y0:y1, x0:x1] = img
    if hh is not None:
        H[y0:y1, x0:x1] = hh


# media real das penas e das pontas rosadas na imagem (cantos do manto, esquerda)
reg = SRCIMG[300:700, 70:300].reshape(-1, 3)
lum = reg.mean(1)
dark = reg[(lum > 25) & (lum < 90) & (reg[:, 0] - reg[:, 2] < 25)]
pinkpx = reg[(reg[:, 0] - reg[:, 1] > 60)]
BASE = dark.mean(0) if len(dark) else np.array((55, 52, 57), np.float32)
PINK = np.array((170, 56, 92), np.float32)
print("cores", BASE.round(), PINK.round())

cw, ch = FEATHER_CELL
for cell in range(FEATHER_COLS * FEATHER_ROWS):
    c, r = cell % FEATHER_COLS, cell // FEATHER_COLS
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    t = yy / ch
    u = (xx / (cw - 1)) * 2 - 1
    sway = 0.07 * np.sin(t * 3.0 + cell) * (0.3 + t)
    ua = u - sway
    rach = np.exp(-(ua / 0.04) ** 2)
    bph = (t * 52 - np.abs(ua) * 20 + cell * 0.37) % 1.0
    barb = smooth(0.30, 0.5, bph) * smooth(0.97, 0.78, bph)
    edge = smooth(0.0, 0.3, 1 - np.abs(ua))
    tone = 0.75 + 0.5 * rng.random()
    img = np.zeros((ch, cw, 3), np.float32) + BASE * tone * 0.8
    img *= (0.72 + 0.45 * barb[..., None]) * (0.85 + 0.15 * edge[..., None])
    img += noise(ch, cw, 5, 3.0)[..., None]
    img += rach[..., None] * np.array((40, 36, 36), np.float32)
    img *= (0.80 + 0.28 * smooth(0.0, 0.5, t))[..., None]
    pk = (0.35 + 0.65 * rng.random()) * (1.0 if cell % 5 else 0.30)
    pm = smooth(0.66 - 0.1 * pk, 0.96, t + noise(ch, cw, 8, 0.03) + np.abs(ua) * 0.08) * min(1.0, pk * 1.1)
    pink = PINK * (0.70 + 0.45 * barb[..., None]) + rach[..., None] * np.array((50, 25, 30), np.float32)
    img = img * (1 - pm[..., None]) + pink * pm[..., None]
    hh = rach * 1.0 + barb * 0.45 - (1 - edge) * 0.35
    C[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw] = img
    H[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw] = hh

# projetados
for k in ("vest", "belt", "scarf"):
    img, hh = crop_to(k, 0.9 if k != "scarf" else 0.4, 0.6 if k != "scarf" else 0.15)
    put(k, img, hh)
# tabardo: painel escuro com borda rosada e losango (cores medidas; o recorte da imagem tem fundo cinza)
h, w = rect_hw("tabard")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
img = np.zeros((h, w, 3), np.float32) + BASE * 0.65 + noise(h, w, 4, 3)[..., None]
bd = np.minimum.reduce([xx, w - 1 - xx, yy, h - 1 - yy])
m = smooth(22, 17, bd)
img = img * (1 - m[..., None]) + PINK * (0.9 + 0.1 * noise(h, w, 8, 1)[..., None]) * m[..., None]
ln = np.exp(-((bd - 30) / 1.6) ** 2)
img = img * (1 - ln[..., None] * 0.7) + PINK * 0.6 * ln[..., None] * 0.7
hh = -ln * 0.5 + m * 0.3
dm = np.abs(xx - w / 2) / 62 + np.abs(yy - h * 0.72) / 100
for rr, wd in ((1.0, 0.04), (0.6, 0.035)):
    l = np.exp(-((dm - rr) / wd) ** 2)
    img = img * (1 - l[..., None]) + PINK * l[..., None] * 0.9
    hh -= l * 0.6
put("tabard", img, hh)
# base do tabardo na borda e tecido liso (media do colete, escurecida)
h, w = rect_hw("plain")
vc = SRCIMG[260:330, 430:470].reshape(-1, 3).mean(0) * 0.9
put("plain", np.zeros((h, w, 3), np.float32) + vc + noise(h, w, 3, 2.5)[..., None], noise(h, w, 3, 0.1))
# base do manto: preto das penas, forro rosado em baixo
h, w = rect_hw("shell")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
img = np.zeros((h, w, 3), np.float32) + BASE * 0.55 + noise(h, w, 3, 2.5)[..., None]
pm = smooth(0.78, 1.0, yy / h)[..., None]
img = img * (1 - pm * 0.6) + PINK * 0.8 * pm * 0.6
put("shell", img)
h, w = rect_hw("lining")
put("lining", np.zeros((h, w, 3), np.float32) + PINK * 0.9 + noise(h, w, 6, 4)[..., None])
h, w = rect_hw("leather")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
img = np.zeros((h, w, 3), np.float32) + (74, 46, 34) + noise(h, w, 4, 5)[..., None]
st = ((xx % 16) < 10) & (np.abs(yy - 14) < 2)
img[st] = (176, 132, 96)
put("leather", img, noise(h, w, 3, 0.2))
# metal: prata escuro com brilho e arranhoes
h, w = rect_hw("metal")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
base = np.array((150, 140, 138), np.float32)
img = np.zeros((h, w, 3), np.float32) + base * (0.8 + 0.15 * np.sin(xx / 40 + yy / 70)[..., None]) + noise(h, w, 3, 5)[..., None]
img = img * (0.85 + 0.25 * np.clip(noise(h, w, 20, 1.0), -1, 1)[..., None] * 0.5)
put("metal", img, noise(h, w, 3, 0.15))

bc = np.clip(C, 0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(final, f"T_{tex}_BC.png"), bc[..., ::-1])
cv2.imwrite(os.path.join(final, f"T_{tex}_M.png"), np.zeros((N, N, 3), np.uint8))
Hs = cv2.GaussianBlur(H, (0, 0), 0.8)
dx = cv2.Sobel(Hs, cv2.CV_32F, 1, 0, ksize=3) / 8
dy = cv2.Sobel(Hs, cv2.CV_32F, 0, 1, ksize=3) / 8
s = 2.2
nrm = np.dstack([-dx * s, dy * s, np.ones_like(dx)])
nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
cv2.imwrite(os.path.join(work, "bake_normal.png"), ((nrm * 0.5 + 0.5) * 255).astype(np.uint8)[..., ::-1])
cv2.imwrite(os.path.join(work, "atlas_preview.png"), cv2.resize(bc[..., ::-1], (1024, 1024), interpolation=cv2.INTER_AREA))
print("TEX ok")
