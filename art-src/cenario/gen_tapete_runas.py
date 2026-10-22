"""Gera T_Cripta_Tapete.png (tapete vermelho rasgado com barra dourada) e T_Cripta_Runas.png (moldura de runas com alpha, para Decal).
python gen_tapete_runas.py <pasta_saida>"""
import sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
out = sys.argv[1]
rng = np.random.default_rng(5)

def noise(h, w, cells, seed):
    r = np.random.default_rng(seed)
    f = np.fft.fft2(r.standard_normal((h, w)))
    ky = np.fft.fftfreq(h) * h; kx = np.fft.fftfreq(w) * w
    kx, ky = np.meshgrid(kx, ky)
    f *= np.exp(-((kx**2 + ky**2) / (2 * cells**2)))
    n = np.real(np.fft.ifft2(f)); return n / np.abs(n).max()

# tapete: 256 x 1024 (largura x comprimento)
W, H = 256, 1024
base = np.zeros((H, W, 3), np.float32)
base[:] = (0.36, 0.05, 0.07)
n = noise(H, W, 40, 1) * 0.5 + noise(H, W, 8, 2) * 0.5
base *= (0.85 + 0.25 * n[..., None])
img = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8))
d = ImageDraw.Draw(img)
gold = (176, 134, 52)
for x in (14, 22, W - 22, W - 14):
    d.line([(x, 0), (x, H)], fill=gold, width=3)
cx = W // 2
for y in range(60, H, 170):  # medalhões
    for r, wd in ((44, 3), (30, 2)):
        d.ellipse([cx - r, y - r, cx + r, y + r], outline=gold, width=wd)
    for k in range(8):
        a = k * math.pi / 4
        d.line([(cx, y), (cx + 40 * math.cos(a), y + 40 * math.sin(a))], fill=gold, width=2)
arr = np.asarray(img).astype(np.float32) / 255
arr *= (0.8 + 0.2 * noise(H, W, 20, 3)[..., None])
# rasgos nas pontas
alpha = np.ones((H, W), np.float32)
for edge in (0, H - 1):
    for i in range(W):
        depth = int(abs(noise(1, W, 6, 7 + edge)[0][i]) * 28 * rng.random() + rng.integers(0, 6))
        if edge == 0: alpha[:depth, i] = 0
        else: alpha[H - depth:, i] = 0
for i in range(H):
    depth = int(rng.integers(0, 5))
    alpha[i, :depth] = 0; alpha[i, W - depth:] = 0
rgba = np.dstack([arr, alpha])
Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), 'RGBA').save(f"{out}/T_Cripta_Tapete.png")

# runas: moldura quadrada com estrela, 1024, alpha
S = 1024
im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
col = (150, 140, 120, 200)
for inset, wd in ((20, 10), (60, 4), (130, 4)):
    d.rectangle([inset, inset, S - inset, S - inset], outline=col, width=wd)
c = S // 2
for r, wd in ((300, 5), (220, 3)):
    d.ellipse([c - r, c - r, c + r, c + r], outline=col, width=wd)
pts = [(c + 300 * math.cos(math.radians(a - 90)), c + 300 * math.sin(math.radians(a - 90))) for a in range(0, 360, 72)]
for i in range(5): d.line([pts[i], pts[(i + 2) % 5]], fill=col, width=5)
for i in range(64):  # runas na faixa entre molduras
    t = i / 64; side = int(t * 4); u = (t * 4) % 1
    p = [(60 + u * (S - 120), 40), (S - 40, 60 + u * (S - 120)), (S - 60 - u * (S - 120), S - 40), (40, S - 60 - u * (S - 120))][side]
    rx = rng.integers(8, 16)
    d.line([(p[0], p[1] - rx), (p[0] + rng.integers(-8, 8), p[1] + rx)], fill=col, width=3)
    d.line([(p[0] - rx / 2, p[1]), (p[0] + rx / 2, p[1] + rng.integers(-6, 6))], fill=col, width=2)
im = im.filter(ImageFilter.GaussianBlur(0.8))
a = np.asarray(im).astype(np.float32); a[..., 3] *= (0.55 + 0.45 * (noise(S, S, 25, 9) * 0.5 + 0.5))
Image.fromarray(a.astype(np.uint8), 'RGBA').save(f"{out}/T_Cripta_Runas.png")
print("ok")
