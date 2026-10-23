"""Texturas procedurais (CPU) da aljava v2: flechas (alpha), alca, emblema, e 2048+normal do corpo.
uso: python aljava_v2_tex.py <out_dir> <corpo_bc_512.png>"""
import sys, os, numpy as np
from PIL import Image, ImageFilter
out, body_src = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
rng = np.random.default_rng(7)

def noise(h, w, k):
    a = rng.random((h // k + 2, w // k + 2)).astype(np.float32)
    return np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255

def save(a, name): Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(out, name))

# ---------------- flechas 512x512 RGBA ----------------
H = W = 512
img = np.zeros((H, W, 4), np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
# pena: metade esquerda (0..255), topo = ponta (y=0 e o topo da imagem; v=1)
fx = xx[:, :256] / 255.0; fy = yy[:, :256] / 511.0   # fy 0 topo .. 1 base
cx = 0.5
# silhueta: ponta afilada em cima, largura max ~ 60% da altura, base reta
prof = np.where(fy < 0.55, 0.5 * np.sin(np.clip(fy / 0.55, 0, 1) * np.pi / 2) ** 0.8, 0.5 - 0.06 * (fy - 0.55) / 0.45)
prof = prof * 0.92
serr = 0.018 * np.sign(np.sin(fy * 120)) * (fy > 0.08)
mask = (np.abs(fx - cx) < prof + serr) & (fy > 0.005)
base = np.zeros((H, 256, 3), np.float32) + np.array([22, 18, 26])
bar = np.sin((np.abs(fx - cx) * 60 + fy * 90 * np.sign(fx - cx)) * 1.0)  # barbas diagonais
base += (bar[..., None] * 7 + noise(H, 256, 6)[..., None] * 14)
rach = np.abs(fx - cx) < 0.012
base[rach] = [92, 70, 62]
pink = np.clip((0.42 - fy) / 0.30, 0, 1) ** 1.3          # ponta rosa
pinkc = np.array([214, 86, 120], np.float32)
base = base * (1 - pink[..., None] * 0.9) + pinkc * pink[..., None] * 0.9 * (0.75 + 0.25 * noise(H, 256, 5)[..., None])
img[:, :256, :3] = base; img[:, :256, 3] = mask * 255
# haste: x 256..383 (madeira escura, aneis rosa)
sh = np.zeros((H, 128, 3), np.float32) + np.array([54, 38, 30]) + noise(H, 128, 4)[..., None] * 22
gx = np.linspace(-1, 1, 128)[None, :]
sh *= (1 - 0.35 * gx ** 2)[..., None]
for y0 in (40, 70, 440, 470): sh[y0:y0 + 8] = [200, 80, 112]
img[:, 256:384, :3] = sh; img[:, 256:384, 3] = 255
# ponta: x 384..511 (metal rosado com gradiente e fio claro)
hd = np.zeros((H, 128, 3), np.float32)
g = (np.linspace(0, 1, 128)[None, :] * np.ones((H, 1)))
hd += np.array([150, 52, 84]) + (np.abs(g - 0.5) < 0.06)[..., None] * 70 + (1 - np.abs(g - 0.5) * 2)[..., None] * 60
hd += noise(H, 128, 8)[..., None] * 12
img[:, 384:, :3] = hd; img[:, 384:, 3] = 255
# dilata cor sob transparencia (evita borda)
save(img, "T_ArcherDark_Arrows_BC.png")

# ---------------- alca 512: couro (esq) + metal (dir) ----------------
S = 512
t = np.zeros((S, S, 3), np.float32)
leather = np.array([66, 44, 34], np.float32) + noise(S, S, 3)[..., None] * 18 + noise(S, S, 24)[..., None] * 14
leather[..., 0] += 4
t[:, :256] = leather[:, :256]
# costura: 2 linhas tracejadas perto das bordas (u 0.06 e 0.44 de 0..0.5 -> x 30 e 226), vertical (v ao longo da fita)
for x0 in (26, 230):
    for y0 in range(0, S, 16):
        t[y0:y0 + 9, x0 - 1:x0 + 2] = [150, 120, 92]
t[:, :6] *= 0.55; t[:, 250:256] *= 0.55   # borda queimada
metal = np.array([138, 104, 70], np.float32) + noise(S, S, 4)[..., None] * 26 + (noise(S, S, 40)[..., None] - 0.5) * 40
t[:, 256:] = metal[:, 256:]
save(t, "T_ArcherDark_Strap_BC.png")

# ---------------- emblema 512: placa de bronze + gema rosa ----------------
e = np.array([104, 78, 58], np.float32) + noise(S, S, 3)[..., None] * 22 + (noise(S, S, 50)[..., None] - .5) * 40
e[:300] += (noise(300, S, 90)[..., None] - .4) * 60
grad = np.linspace(0.6, 1.25, S)[None, :, None]
e[:300] = e[:300] * grad + (grad - 1) * 25
e[300:, :] = [196, 70, 104]   # faixa inferior = gema rosa
e[300:, :] += noise(S - 300, S, 6)[..., None] * 30
save(e, "T_ArcherDark_Emblem_BC.png")

# ---------------- corpo 2048 + normal ----------------
b = Image.open(body_src).convert("RGB")
big = b.resize((2048, 2048), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 90, 2))
ba = np.asarray(big, np.float32)
ba += (noise(2048, 2048, 2)[..., None] - 0.5) * 10      # microdetalhe
# repinta a zona do emblema borrado com couro liso
mj = os.path.join(out, "emblem_mask.json")
if os.path.exists(mj):
    import json
    from PIL import ImageDraw
    mk = Image.new("L", (2048, 2048), 0); d = ImageDraw.Draw(mk)
    for poly in json.load(open(mj)):
        d.polygon([(u * 2048, (1 - v) * 2048) for u, v in poly], fill=255)
    mk = mk.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(5))
    m = np.asarray(mk, np.float32)[..., None] / 255
    ref = ba[1300:1900, 100:400].reshape(-1, 3)             # trecho de couro limpo (corpo baixo)
    leather = np.median(ref, 0) * 1.08 + (noise(2048, 2048, 5)[..., None] - 0.5) * 26 + (noise(2048, 2048, 60)[..., None] - 0.5) * 18
    ba = ba * (1 - m) + leather * m
big = Image.fromarray(np.clip(ba, 0, 255).astype(np.uint8))
big.save(os.path.join(out, "T_ArcherDark_Quiver_Body_BC.png"))
lum = ba.mean(2)
hgt = np.asarray(Image.fromarray(lum.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.4)), np.float32) / 255
hgt = hgt + 0.5 * noise(2048, 2048, 3) * 0.08 + 0.2 * (np.maximum(ba[..., 0] - ba[..., 2], 0) > 60) * 0.0
gy, gx_ = np.gradient(hgt)
k = 9.0
nx, ny, nz = -gx_ * k, gy * k, np.ones_like(hgt)   # glTF: +Y verde para cima na imagem
l = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
nrm = np.stack([nx / l, ny / l, nz / l], -1) * 0.5 + 0.5
save(nrm * 255, "T_ArcherDark_Quiver_Body_N.png")
print("tex ok", out)
