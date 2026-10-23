"""Pinta o atlas do torso (BC, M, normal) por codigo. Python do venv. Uso: python -I manto_tex.py <final_dir> <work_dir> <nome_textura>"""
import sys, os
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manto_atlas import *
final, work, tex = sys.argv[1:4]
rng = np.random.default_rng(7)
C = np.zeros((N, N, 3), np.float32)
C[:] = (30, 27, 32)
H = np.zeros((N, N), np.float32)


def noise(h, w, sc, amp):
    n = rng.standard_normal((max(2, h // sc), max(2, w // sc))).astype(np.float32)
    return cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) * amp


def put(rect, img, hh=None):
    x0, y0, x1, y1 = rect
    C[y0:y1, x0:x1] = img
    if hh is not None:
        H[y0:y1, x0:x1] = hh


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def rect_hw(k):
    x0, y0, x1, y1 = R[k]
    return y1 - y0, x1 - x0


# penas: 32 celulas 128 x 512
cw, ch = FEATHER_CELL
for cell in range(FEATHER_COLS * FEATHER_ROWS):
    c, r = cell % FEATHER_COLS, cell // FEATHER_COLS
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    t = yy / ch
    u = (xx / (cw - 1)) * 2 - 1
    sway = 0.06 * np.sin(t * 3.0 + cell) * (0.3 + t)
    ua = u - sway
    rach = np.exp(-(ua / 0.045) ** 2)
    bph = (t * 64 - np.abs(ua) * 22 + cell * 0.37) % 1.0
    barb = smooth(0.35, 0.5, bph) * smooth(0.95, 0.8, bph)
    edge = smooth(0.0, 0.25, 1 - np.abs(ua))
    base = np.array((40, 38, 43), np.float32) * (0.85 + 0.35 * rng.random())
    img = np.zeros((ch, cw, 3), np.float32) + base
    img *= (0.80 + 0.30 * barb[..., None]) * (0.9 + 0.1 * edge[..., None])
    img += noise(ch, cw, 6, 2.5)[..., None]
    img += rach[..., None] * np.array((38, 34, 34), np.float32)
    img += (1 - t)[..., None] * np.array((6, 6, 8), np.float32)
    pk = (0.45 + 0.55 * rng.random()) * (1.0 if cell % 4 else 0.25)
    pm = smooth(0.50, 0.92, t + noise(ch, cw, 10, 0.02)) * pk
    pink = np.array((178, 50, 86), np.float32) * (0.75 + 0.35 * barb[..., None]) + rach[..., None] * np.array((40, 20, 24), np.float32)
    img = img * (1 - pm[..., None]) + pink * pm[..., None]
    hh = rach * 1.0 + barb * 0.35 - (1 - edge) * 0.3
    C[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw] = img
    H[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw] = hh

# couro (correias e cinto): marrom, costura nas bordas
h, w = rect_hw("leather")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
img = np.zeros((h, w, 3), np.float32) + (58, 36, 30)
img += noise(h, w, 4, 5)[..., None] + noise(h, w, 24, 6)[..., None]
hh = noise(h, w, 3, 0.25)
for yc in (22, h - 22):
    st = ((xx % 18) < 11) & (np.abs(yy - yc) < 2.5)
    img[st] = (176, 132, 96)
    hh[st] += 0.8
img[:6] *= 0.6
img[-6:] *= 0.6
put(R["leather"], img, hh)

# tecido escuro do colete: losangos acolchoados
h, w = rect_hw("cloth")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
img = np.zeros((h, w, 3), np.float32) + (36, 31, 36) + noise(h, w, 5, 3)[..., None]
d = np.minimum(np.abs(((xx + yy) % 64) - 32), np.abs(((xx - yy) % 64) - 32))
seam = smooth(3, 0, d)
img *= (1 - 0.35 * seam[..., None])
img += seam[..., None] * np.array((14, 8, 10), np.float32)
put(R["cloth"], img, -seam * 0.5 + noise(h, w, 4, 0.1))

# painel do tabardo: borda rosada, losango gravado
h, w = rect_hw("panel")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
img = np.zeros((h, w, 3), np.float32) + (40, 33, 38) + noise(h, w, 5, 2.5)[..., None]
bd = np.minimum.reduce([xx, w - 1 - xx, yy, h - 1 - yy])
pink = np.array((168, 52, 84), np.float32)
m = smooth(40, 34, bd)
img = img * (1 - m[..., None]) + pink * m[..., None]
ln = np.exp(-((bd - 52) / 2.0) ** 2)
img = img * (1 - ln[..., None] * 0.8) + np.array((120, 40, 62), np.float32) * ln[..., None] * 0.8
hh = -ln * 0.5 + m * 0.3
cx, cy = w / 2, h * 0.70
dm = np.abs(xx - cx) / 120 + np.abs(yy - cy) / 190
for rr, wd in ((1.0, 0.025), (0.62, 0.02)):
    l = np.exp(-((dm - rr) / wd) ** 2)
    img = img * (1 - l[..., None]) + pink[None, None] * l[..., None] * 0.9
    hh -= l * 0.6
put(R["panel"], img, hh)

# gola de tecido claro com dobras
h, w = rect_hw("scarf")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
fold = np.sin(xx / 22 + 2 * np.sin(yy / 90)) * 0.5 + 0.5
img = np.zeros((h, w, 3), np.float32) + np.array((226, 214, 200), np.float32) * (0.86 + 0.14 * fold[..., None]) + noise(h, w, 3, 2)[..., None]
img = np.ascontiguousarray(img)
for (sx, sy, s) in ((120, 110, 34), (360, 200, 30), (200, 380, 28), (420, 420, 26)):
    for a in range(4):
        ang = a * np.pi / 4
        for sg in (-1, 1):
            p2 = (int(sx + sg * s * np.cos(ang)), int(sy + sg * s * np.sin(ang)))
            cv2.line(img, (sx, sy), p2, (92, 74, 66), 2, cv2.LINE_AA)
put(R["scarf"], img, fold * 0.4 + noise(h, w, 3, 0.05))

# metal e brasao
h, w = rect_hw("metal")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
img = np.zeros((h, w, 3), np.float32) + np.array((158, 152, 154), np.float32) * (0.9 + 0.1 * np.sin(yy / 16)[..., None]) + noise(h, w, 4, 4)[..., None]
put(R["metal"], img, noise(h, w, 4, 0.1))
h, w = rect_hw("emblem")
img = np.ascontiguousarray(np.zeros((h, w, 3), np.float32) + (146, 140, 144) + noise(h, w, 4, 4)[..., None])
cv2.line(img, (w // 2, 20), (w // 2, h - 20), (60, 52, 56), 5, cv2.LINE_AA)
cv2.line(img, (30, h // 2 - 20), (w - 30, h // 2 - 20), (60, 52, 56), 5, cv2.LINE_AA)
put(R["emblem"], img)

# base do manto (por baixo das penas) e forro rosado
h, w = rect_hw("shell")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
img = np.zeros((h, w, 3), np.float32) + (26, 24, 29) + noise(h, w, 3, 3)[..., None] + (np.sin(xx / 5) * 3)[..., None]
pm = smooth(0.7, 1.0, yy / h)[..., None]
img = img * (1 - pm * 0.6) + np.array((120, 40, 64), np.float32) * pm * 0.6
put(R["shell"], img)
h, w = rect_hw("lining")
put(R["lining"], np.zeros((h, w, 3), np.float32) + (150, 48, 78) + noise(h, w, 6, 4)[..., None])

# saidas
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
