"""Textura 2048 das bracadeiras do arqueiro dark: albedo (T_ArcherDark_Bracers_BC.png), normal (_N.png, OpenGL) e metal/rugosidade (_MR.png).
Cores e detalhe de couro vem da imagem de entrada (recortes projetados); cintas, metal e rosado pintados com as cores medidas.
Uso: python brac_tex.py <entrada.png> <pasta_saida>"""
import sys, os
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brac_atlas import *

src_png, outd = sys.argv[1], sys.argv[2]
os.makedirs(outd, exist_ok=True)
rng = np.random.default_rng(7)
IMG = cv2.imread(src_png)[..., ::-1].astype(np.float32)
C = np.zeros((N, N, 3), np.float32); C[:] = (30, 26, 28)
H = np.zeros((N, N), np.float32)
MR = np.zeros((N, N, 3), np.float32); MR[..., 1] = 235          # G = rugosidade, B = metal (0..255)


def noise(h, w, sc, amp):
    n = rng.standard_normal((max(2, h // sc + 2), max(2, w // sc + 2))).astype(np.float32)
    return cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) * amp


def rect_hw(k):
    x0, y0, x1, y1 = R[k]
    return y1 - y0, x1 - x0


def put(k, img, hh=None, mr=None):
    x0, y0, x1, y1 = R[k]
    C[y0:y1, x0:x1] = np.clip(img, 0, 255)
    if hh is not None:
        H[y0:y1, x0:x1] = hh
    if mr is not None:
        MR[y0:y1, x0:x1] = mr


def ridge(h, w, sc, seed_amp=1.0):
    n = noise(h, w, sc, 1.0)
    return 1.0 - np.clip(np.abs(n) * 2.2, 0, 1)         # linhas finas onde o ruido cruza zero (rachaduras)


# ---- amostras reais de couro: recortes da imagem (antebraco entre cintas, dorso da luva), media e detalhe
patches = [IMG[690:760, 440:500]]
reg = IMG[100:600, 400:620].reshape(-1, 3); lm = reg.mean(1)
mean_leather = reg[(lm < 75) & (lm > 20)].mean(0)
print("BTEX couro medio", mean_leather.round(1))
BASE = np.clip(mean_leather * 1.05, 28, 80)
COPPER = np.array((168, 98, 62), np.float32)
detail = np.zeros((1536, 1024), np.float32)
for i, p in enumerate(patches):
    lum = p.mean(2)
    hp = lum - cv2.GaussianBlur(lum, (0, 0), 6)
    big = cv2.resize(hp, (256, 384), interpolation=cv2.INTER_CUBIC)
    m2 = np.concatenate([np.concatenate([big, big[:, ::-1]], 1), np.concatenate([big[::-1], big[::-1, ::-1]], 1)], 0)   # 768 x 512, espelhado
    reps = np.tile(m2, (3, 3))
    oy, ox = (i * 211) % 700, (i * 331) % 400
    detail += reps[oy:oy + 1536, ox:ox + 1024] * 0.07

# ---- couro (antebraco, cuff, luva): u = em volta (0 = dentro, 0.5 = dorso), v = cuff -> dedos
h, w = rect_hw("leather")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
img = np.zeros((h, w, 3), np.float32) + BASE + noise(h, w, 10, 2.6)[..., None] + noise(h, w, 4, 0.7)[..., None]
img += (detail * 0.9)[..., None]
crack = ridge(h, w, 22) * ridge(h, w, 9)
img *= (1 - 0.30 * crack)[..., None]
hh = -crack * 0.9 + detail * 0.02 + noise(h, w, 6, 0.12)
# nervuras de cobre rosado (veios finos da imagem)
veins = np.zeros((h, w), np.float32)
for _ in range(70):
    x, y = rng.uniform(0, w), rng.uniform(0, h)
    pts = [(x, y)]
    ang = rng.uniform(0, 6.28)
    for _k in range(rng.integers(4, 9)):
        ang += rng.normal(0, 0.7); x += np.cos(ang) * rng.uniform(10, 26); y += np.sin(ang) * rng.uniform(10, 26)
        pts.append((x, y))
    cv2.polylines(veins, [np.array(pts, np.int32)], False, 1.0, 1, cv2.LINE_AA)
veins = cv2.GaussianBlur(veins, (0, 0), 0.8)
img = img * (1 - 0.55 * veins[..., None]) + COPPER * 0.55 * veins[..., None] * 0.55
# costuras (cobre) em duas linhas verticais no dorso e ao redor do pulso/dedos
for u in (0.30, 0.70):
    xs = int(u * w)
    for y in range(0, h, 16):
        cv2.line(img, (xs, y), (xs, y + 9), tuple(float(c) for c in COPPER), 2, cv2.LINE_AA)
        hh[y:y + 9, xs - 1:xs + 2] -= 0.5
# dobras do pulso e dos nos dos dedos (faixas escuras com cristas)
for v_, wd in ((0.33, 18), (0.46, 12), (0.52, 10), (0.58, 9)):
    yc = int(v_ * h)
    m = np.exp(-((yy - yc) / wd) ** 2)
    img *= (1 - 0.35 * m)[..., None]
    hh -= m * 0.7
# desgaste nas bordas e brilho de couro (leve)
img *= (0.9 + 0.2 * np.clip(noise(h, w, 40, 1.0), -1, 1))[..., None]
put("leather", img, hh)
x0, y0, x1, y1 = R["leather"]
MR[y0:y1, x0:x1, 1] = 205

# ---- cintas: borda de cobre nos dois lados, miolo marrom, costura
h, w = rect_hw("strap")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
v = yy / h
STRAP = np.array((78, 54, 44), np.float32)
img = np.zeros((h, w, 3), np.float32) + STRAP + noise(h, w, 5, 4)[..., None]
edge = np.clip(np.minimum(v, 1 - v) / 0.14, 0, 1)
img = img * edge[..., None] + COPPER * (1 - edge[..., None]) * 0.9
for vv in (0.24, 0.76):
    yc = int(vv * h)
    for x in range(0, w, 22):
        cv2.line(img, (x, yc), (x + 11, yc), (190, 124, 84), 2, cv2.LINE_AA)
img *= (1 - 0.22 * ridge(h, w, 14))[..., None]
hh = (edge - 1) * 1.1 + noise(h, w, 4, 0.2)
put("strap", img, hh)
MR[R["strap"][1]:R["strap"][3], R["strap"][0]:R["strap"][2], 1] = 190

# ---- metal: recorte REAL da ponta de flecha da imagem (a malha usa a mesma silhueta); fora da silhueta, bronze liso
h, w = rect_hw("metal")
ox_, oy_ = ARROW_CROP_ORIGIN
bx0, by0, bx1, by1 = ARROW_BOX
crop = IMG[oy_ + by0:oy_ + by1 + 1, ox_ + bx0:ox_ + bx1 + 1].copy()
cm = np.zeros(crop.shape[:2], np.uint8)
cv2.fillPoly(cm, [np.array([(x - bx0, y - by0) for x, y in ARROW_PX], np.int32)], 255)
outside = (cv2.dilate(cm, np.ones((11, 11), np.uint8)) == 0).astype(np.uint8) * 255
crop8 = np.clip(crop, 0, 255).astype(np.uint8)
crop8 = cv2.inpaint(crop8, outside, 6, cv2.INPAINT_TELEA).astype(np.float32)     # tira o cinza de fundo e o couro da borda
img = cv2.resize(crop8, (w, h), interpolation=cv2.INTER_LANCZOS4)
bl = cv2.GaussianBlur(img, (0, 0), 2.5)
img = np.clip(img + 0.7 * (img - bl), 0, 255)
lum = img.mean(2)
hh = (cv2.GaussianBlur(lum, (0, 0), 1.3) - cv2.GaussianBlur(lum, (0, 0), 7)) / 22.0
BRONZE = np.array((112, 96, 80), np.float32)
cv2.rectangle(img, (0, 0), (int(w * 0.08), int(h * 0.08)), tuple(float(c) for c in BRONZE * 0.95), -1)   # canto liso: fivelas
hh[:int(h * 0.08), :int(w * 0.08)] = 0.3
put("metal", img, hh)
x0, y0, x1, y1 = R["metal"]
MR[y0:y1, x0:x1, 1] = 140; MR[y0:y1, x0:x1, 2] = 60
ROSE = np.array((132, 66, 84), np.float32)

# ---- rosado (vazado) e couro escuro liso
h, w = rect_hw("rose")
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
img = np.zeros((h, w, 3), np.float32) + ROSE * (0.85 + 0.25 * (yy / h))[..., None] + noise(h, w, 6, 4)[..., None]
put("rose", img, noise(h, w, 4, 0.1))
x0, y0, x1, y1 = R["rose"]; MR[y0:y1, x0:x1, 1] = 140; MR[y0:y1, x0:x1, 2] = 60
h, w = rect_hw("dark")
put("dark", np.zeros((h, w, 3), np.float32) + (36, 29, 31) + noise(h, w, 4, 3)[..., None], noise(h, w, 4, 0.15))

# ---- normal map (OpenGL: +Y para cima na imagem) a partir da altura
Hs = cv2.GaussianBlur(H, (0, 0), 0.9)
gx = cv2.Sobel(Hs, cv2.CV_32F, 1, 0, ksize=3) / 8.0
gy = cv2.Sobel(Hs, cv2.CV_32F, 0, 1, ksize=3) / 8.0
STR = 2.2
nx, ny = -gx * STR, gy * STR
nz = np.ones_like(nx)
ln = np.sqrt(nx * nx + ny * ny + nz * nz)
Nn = np.stack([nx / ln, ny / ln, nz / ln], -1) * 0.5 + 0.5
cv2.imwrite(os.path.join(outd, "T_ArcherDark_Bracers_BC.png"), np.clip(C, 0, 255).astype(np.uint8)[..., ::-1])
cv2.imwrite(os.path.join(outd, "T_ArcherDark_Bracers_N.png"), (Nn * 255).astype(np.uint8)[..., ::-1])
cv2.imwrite(os.path.join(outd, "T_ArcherDark_Bracers_MR.png"), np.clip(MR, 0, 255).astype(np.uint8)[..., ::-1])
print("BTEX ok", outd)
