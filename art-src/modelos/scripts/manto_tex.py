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

# penas: atlas gerado (alpha, barbas); o resto do atlas e opaco
PEN = cv2.imread(os.path.join(os.path.dirname(src_png), "pen", "pen_atlas_rgba.png"), cv2.IMREAD_UNCHANGED)
A = np.full((N, N), 255, np.float32)
A[0:2048, 0:1024] = PEN[..., 3]
C[0:2048, 0:1024] = PEN[..., :3][..., ::-1]
pk_ = np.clip((C[0:2048, 0:1024, 0] - C[0:2048, 0:1024, 1] - 30) / 60, 0, 1)[..., None]
C[0:2048, 0:1024] = C[0:2048, 0:1024] * (1 - pk_) + pk_ * C[0:2048, 0:1024] * np.array((0.74, 0.58, 0.66), np.float32)
plum = PEN[..., 3] > 128
lumf = C[0:2048, 0:1024].mean(2)
H[0:2048, 0:1024] = (cv2.GaussianBlur(lumf, (0, 0), 1.0) - cv2.GaussianBlur(lumf, (0, 0), 6)) / 18.0
H[0:2048, 0:1024] *= plum

# projetados
for k in ("vest", "belt", "scarf"):
    img, hh = crop_to(k, 0.9 if k != "scarf" else 0.2, 0.6 if k != "scarf" else 0.15)
    put(k, img, hh)
# gola de linho/la: tira o brilho de cetim (contraste e brilho comprimidos), tinge de creme e acrescenta trama
x0, y0, x1, y1 = R["scarf"]
sc = C[y0:y1, x0:x1]
lum = sc.mean(2, keepdims=True)
bl = cv2.GaussianBlur(lum, (0, 0), 6)[..., None] if lum.ndim == 2 else cv2.GaussianBlur(lum[..., 0], (0, 0), 6)[..., None]
flat = bl + (lum - bl) * 0.55
flat = 150 + (flat - 150) * 0.55
h_, w_ = sc.shape[:2]
yy, xx = np.mgrid[0:h_, 0:w_].astype(np.float32)
weave = (np.sin(xx * 1.9) * np.sin(yy * 1.9) * 0.5 + 0.5)[..., None] * 5 + noise(h_, w_, 3, 1.8)[..., None]
cream = np.array((214, 200, 178), np.float32) / 190.0
C[y0:y1, x0:x1] = np.clip(flat * cream + weave, 0, 255)
H[y0:y1, x0:x1] += (weave[..., 0] - 4) * 0.12
# tabardo: painel escuro com borda rosada e losango (cores medidas; o recorte da imagem tem fundo cinza)
h, w = rect_hw("tabard")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
img = np.zeros((h, w, 3), np.float32) + BASE * 0.65 + noise(h, w, 4, 3)[..., None]
bd = np.minimum.reduce([xx, w - 1 - xx, yy, h - 1 - yy])
m = smooth(22, 17, bd)
WINE = np.array((104, 34, 58), np.float32)
img = img * (1 - m[..., None]) + WINE * (0.9 + 0.1 * noise(h, w, 8, 1)[..., None]) * m[..., None]
ln = np.exp(-((bd - 30) / 1.6) ** 2)
img = img * (1 - ln[..., None] * 0.7) + WINE * 0.7 * ln[..., None] * 0.7
hh = -ln * 0.5 + m * 0.3
dm = np.abs(xx - w / 2) / 62 + np.abs(yy - h * 0.72) / 100
for rr, wd in ((1.0, 0.04), (0.6, 0.035)):
    l = np.exp(-((dm - rr) / wd) ** 2)
    img = img * (1 - l[..., None]) + WINE * 1.1 * l[..., None] * 0.9
    hh -= l * 0.6
put("tabard", img, hh)
# base do tabardo na borda e tecido liso (media do colete, escurecida)
h, w = rect_hw("plain")
vc = np.array((36, 31, 36), np.float32)
put("plain", np.zeros((h, w, 3), np.float32) + vc + noise(h, w, 3, 2.5)[..., None], noise(h, w, 3, 0.1))
# base do manto (forro visto pela frente aberta): preto-vinho com penas escurecidas por cima
h, w = rect_hw("shell")
img = np.zeros((h, w, 3), np.float32) + np.array((30, 24, 28), np.float32) + noise(h, w, 3, 2.5)[..., None]
hh = noise(h, w, 3, 0.1)
for k in range(10):
    cx = int(PEN.shape[1] * 0)  # celulas do atlas
    c_, r_ = k % 4, (k // 4) % 2
    cell = PEN[r_ * 1024:(r_ + 1) * 1024, c_ * 256:(c_ + 1) * 256]
    ys, xs = np.where(cell[..., 3] > 128)
    cr = cell[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    cr = cv2.resize(cr, (46, 150), interpolation=cv2.INTER_AREA)
    ox, oy = (k * 29) % (w - 46), (k * 53) % (h - 150)
    al = (cr[..., 3:4] / 255.0)
    img[oy:oy + 150, ox:ox + 46] = img[oy:oy + 150, ox:ox + 46] * (1 - al) + cr[..., :3][..., ::-1] * 0.62 * al
put("shell", img, hh)
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
base = np.array((190, 182, 178), np.float32)
img = np.zeros((h, w, 3), np.float32) + base * (0.8 + 0.15 * np.sin(xx / 40 + yy / 70)[..., None]) + noise(h, w, 3, 5)[..., None]
img = img * (0.62 + 0.38 * np.clip(0.5 + noise(h, w, 18, 0.9), 0, 1)[..., None])
put("metal", img, noise(h, w, 3, 0.15))

bc = np.clip(C, 0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(final, f"T_{tex}_BC.png"), np.dstack([bc[..., ::-1], A.astype(np.uint8)]))
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
