"""Pinta a textura da cabeca (2048) por projecao frontal do close gerado + normal map do rosto (olhos, sobrancelhas, nariz,
narinas, boca) em espaco tangente. Python de CPU (numpy + PIL). Uso: python head_paint.py"""
import numpy as np, math
from PIL import Image, ImageFilter
D = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\cabeca"
TS = 2048; S = 0.000576; CXI, CYI = 271.0, 651.0
geo = np.load(D + r"\head_geo.npz"); UV, POS, NOR = geo["uv"], geo["pos"], geo["nor"]
P = np.zeros((TS, TS, 3), np.float32); Nn = np.zeros((TS, TS, 3), np.float32); M = np.zeros((TS, TS), bool)
Tt = np.zeros((TS, TS, 3), np.float32); Bt = np.zeros((TS, TS, 3), np.float32)
for f in range(len(UV)):
    uv = UV[f].copy(); pp = POS[f]; nn = NOR[f]
    d1, d2 = pp[1] - pp[0], pp[2] - pp[0]; du1, du2 = uv[1] - uv[0], uv[2] - uv[0]
    det = du1[0] * du2[1] - du2[0] * du1[1]
    if abs(det) < 1e-12:
        continue
    tg = (d1 * du2[1] - d2 * du1[1]) / det; bt = (d2 * du1[0] - d1 * du2[0]) / det
    tg /= (np.linalg.norm(tg) + 1e-12); bt /= (np.linalg.norm(bt) + 1e-12)
    for sh in (-1, 0, 1):
        q = uv.copy(); q[:, 0] += sh
        X = q[:, 0] * TS; Y = (1 - q[:, 1]) * TS
        x0, x1 = int(max(0, math.floor(X.min()))), int(min(TS - 1, math.ceil(X.max())))
        y0, y1 = int(max(0, math.floor(Y.min()))), int(min(TS - 1, math.ceil(Y.max())))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        a = (X[1] - X[0]) * (Y[2] - Y[0]) - (X[2] - X[0]) * (Y[1] - Y[0])
        if abs(a) < 1e-9:
            continue
        w1 = ((gx - X[0]) * (Y[2] - Y[0]) - (X[2] - X[0]) * (gy - Y[0])) / a
        w2 = ((X[1] - X[0]) * (gy - Y[0]) - (gx - X[0]) * (Y[1] - Y[0])) / a
        w0 = 1 - w1 - w2
        eps = -0.02
        ins = (w0 >= eps) & (w1 >= eps) & (w2 >= eps)
        if not ins.any():
            continue
        ys, xs = np.where(ins); W0, W1, W2 = w0[ins], w1[ins], w2[ins]
        P[y0 + ys, x0 + xs] = W0[:, None] * pp[0] + W1[:, None] * pp[1] + W2[:, None] * pp[2]
        Nn[y0 + ys, x0 + xs] = W0[:, None] * nn[0] + W1[:, None] * nn[1] + W2[:, None] * nn[2]
        Tt[y0 + ys, x0 + xs] = tg; Bt[y0 + ys, x0 + xs] = bt
        M[y0 + ys, x0 + xs] = True
Nn /= (np.linalg.norm(Nn, axis=2, keepdims=True) + 1e-9)
print("texels cobertos", M.mean())
X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
img = Image.open(D + r"\cab_rostos.png").convert("RGB"); I = np.asarray(img, np.float32)


def bil(px, py, A=None):
    A = I if A is None else A
    px = np.clip(px, 0, A.shape[1] - 1.01); py = np.clip(py, 0, A.shape[0] - 1.01)
    x0 = px.astype(int); y0 = py.astype(int); fx = (px - x0); fy = (py - y0)
    if A.ndim == 3:
        fx = fx[..., None]; fy = fy[..., None]
    return (A[y0, x0] * (1 - fx) * (1 - fy) + A[y0, x0 + 1] * fx * (1 - fy) + A[y0 + 1, x0] * (1 - fx) * fy + A[y0 + 1, x0 + 1] * fx * fy)


PX = CXI + X / S; PY = CYI - (Z - 1.54) / S
face = bil(PX, PY)
skin = I[700:770, 220:320].reshape(-1, 3).mean(0); print("pele", skin)
scalp = np.array([128, 96, 62], np.float32); shirt = np.array([52, 46, 42], np.float32)


def sm(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


nfront = -Nn[..., 1]
wf = sm(0.30, 0.62, nfront) * sm(1.532, 1.55, Z) * (1 - sm(1.700, 1.735, Z)) * (1 - sm(0.070, 0.092, np.abs(X)))
hairz = np.clip(sm(1.66, 1.70, Z) + sm(0.30, -0.2, nfront) * sm(1.55, 1.62, Z) * 0.9, 0, 1)[..., None]
base = skin * (1 - hairz) + scalp * hairz
col = base * (1 - wf[..., None]) + face * wf[..., None]
# fios pintados no couro cabeludo (espaco UV: fluem para baixo)
from PIL import ImageDraw
srng = np.random.default_rng(5)
lay = Image.new("RGBA", (TS, TS), (0, 0, 0, 0)); dr = ImageDraw.Draw(lay)
PAL = [np.array(c, np.float32) for c in ((108, 76, 40), (150, 112, 62), (196, 156, 98), (228, 196, 136))]
for i in range(3800):
    u = srng.uniform(0, TS); y = srng.uniform(0.02, 0.8) * TS; ln = srng.uniform(120, 420)
    t = srng.uniform(0, 1); c = PAL[int(t * 2.99)] * (1 - (t * 2.99) % 1) + PAL[min(3, int(t * 2.99) + 1)] * ((t * 2.99) % 1)
    c = np.clip(c * srng.uniform(0.92, 1.1), 0, 255); ph = srng.uniform(0, 6.28); wv = srng.uniform(3, 9)
    pts = [(u + wv * math.sin(ph + k * 0.35), y + ln * k / 12) for k in range(13)]
    dr.line(pts, fill=tuple(int(x) for x in c) + (255,), width=int(srng.integers(3, 7)))
lay = np.asarray(lay, np.float32)
hm = np.clip((hairz[..., 0] - 0.25) * 2, 0, 1) * (1 - wf)
col = col * (1 - hm[..., None] * (lay[..., 3:4] / 255)) + lay[..., :3] * (hm[..., None] * (lay[..., 3:4] / 255))
sh = (1 - sm(1.488, 1.508, Z))[..., None]
rng = np.random.default_rng(3); gr = rng.normal(0, 3.0, (TS, TS, 1)).astype(np.float32)
col = col * (1 - sh) + (shirt + gr) * sh
col *= (1 - 0.25 * sm(1.545, 1.51, Z) * (1 - sh[..., 0]))[..., None]


def gau(px, py, cx, cy, sx, sy):
    return np.exp(-0.5 * (((px - cx) / sx) ** 2 + ((py - cy) / sy) ** 2))


def Hfun(PXa, PYa):
    h = np.zeros_like(PXa)
    for sgn, ex, ey in ((-1, 200, 434), (1, 342, 434)):
        h += -0.0010 * gau(PXa, PYa, ex, ey, 34, 11) + 0.0010 * gau(PXa, PYa, ex, ey - 16, 36, 4) + 0.0006 * gau(PXa, PYa, ex, ey + 14, 32, 4)
        h += 0.0014 * gau(PXa, PYa, ex + sgn * (-6), ey - 34, 38, 6)
        h += -0.0010 * gau(PXa, PYa, 271 + sgn * 22, 534, 7, 5) + 0.0009 * gau(PXa, PYa, 271 + sgn * 25, 528, 9, 8) - 0.0007 * gau(PXa, PYa, 271 + sgn * 52, 560, 5, 38)
    h += 0.0012 * gau(PXa, PYa, 271, 490, 7, 40) + 0.0016 * gau(PXa, PYa, 271, 527, 11, 9) - 0.0014 * gau(PXa, PYa, 270, 577, 40, 2.6)
    h += 0.0014 * gau(PXa, PYa, 270, 567, 34, 7) + 0.0016 * gau(PXa, PYa, 270, 590, 30, 9) - 0.0007 * gau(PXa, PYa, 270, 606, 18, 4)
    h += -0.0006 * gau(PXa, PYa, 271, 548, 6, 10) + 0.0006 * gau(PXa, PYa, 270, 636, 18, 10)
    return h


L = np.asarray(img.convert("L").filter(ImageFilter.GaussianBlur(1.6)), np.float32)
e = 1.0
gxp = (Hfun(PX + e, PY) - Hfun(PX - e, PY)) / (2 * e)
gyp = (Hfun(PX, PY + e) - Hfun(PX, PY - e)) / (2 * e)
dx_ = (bil(PX + 1, PY, L) - bil(PX - 1, PY, L)) / 2 / 255 * 0.0016 * 0.5
dy_ = (bil(PX, PY + 1, L) - bil(PX, PY - 1, L)) / 2 / 255 * 0.0016 * 0.5
gxp = (gxp + dx_) * wf
gyp = (gyp + dy_) * wf
dHt = (gxp * Tt[..., 0] - gyp * Tt[..., 2]) / S
dHb = (gxp * Bt[..., 0] - gyp * Bt[..., 2]) / S
K = 1.0
nt = np.stack([-K * dHt, -K * dHb, np.ones_like(dHt)], -1)
nt /= np.linalg.norm(nt, axis=2, keepdims=True)
nrm = ((nt * 0.5 + 0.5) * 255)
nrm[~M] = (128, 128, 255)


def dilate(a, m, it=10):
    a = a.copy(); m = m.copy()
    for _ in range(it):
        acc = np.zeros_like(a); cnt = np.zeros(m.shape, np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                mm = np.roll(np.roll(m, dy, 0), dx, 1); aa = np.roll(np.roll(a, dy, 0), dx, 1)
                acc += aa * mm[..., None]; cnt += mm
        new = (~m) & (cnt > 0)
        a[new] = acc[new] / cnt[new][..., None]; m = m | new
    return a


col = np.clip(col, 0, 255)
col[~M] = 0; col = dilate(col, M); nrm = dilate(nrm, M)
Image.fromarray(col.astype(np.uint8)).save(D + r"\T_ArcherDark_Head_BC.png")
Image.fromarray(nrm.astype(np.uint8)).save(D + r"\T_ArcherDark_Head_N.png")
print("ok")
