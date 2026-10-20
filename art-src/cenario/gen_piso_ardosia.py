"""Gera T_Env_PisoA.png a partir da referencia do Will (terreno.png): ardosia escura com lajotas retangulares de tamanhos variados em
amarracao, chanfro pintado, desgaste nas arestas, manchas umidas e fios de musgo nas juntas. Periodico; 1 tile = 16 m (ver _FloorTile)."""
import sys
import numpy as np
from PIL import Image
out = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
TILE = 16.0
rng = np.random.default_rng(11)

def pnoise(res, cells, seed):
    r = np.random.default_rng(seed)
    f = np.fft.fft2(r.standard_normal((res, res)))
    k = np.fft.fftfreq(res) * res; kx, ky = np.meshgrid(k, k)
    f *= np.exp(-((kx ** 2 + ky ** 2) / (2 * cells ** 2)))
    n = np.real(np.fft.ifft2(f)); return n / np.abs(n).max()

# layout: fileiras de alturas variadas somando 16 m, lajotas de comprimentos variados somando 16 m por fileira
row_h = []
while True:
    left = TILE - sum(row_h)
    if left < 0.01: break
    h = float(rng.choice([1.0, 1.5, 2.0, 2.5]))
    if left - h < 0.9 and left - h > 0.01: h = left
    row_h.append(min(h, left))
slabs = []  # (y0,y1,x0,x1)
y = 0.0
for h in row_h:
    x = 0.0
    while x < TILE - 0.01:
        w = float(rng.choice([1.5, 2.0, 2.5, 3.0, 4.0]))
        left = TILE - x
        if left - w < 1.2 and left - w > 0.01: w = left
        w = min(w, left)
        slabs.append((y, y + h, x, x + w)); x += w
    y += h

px = N / TILE
sid = np.zeros((N, N), np.int32)
dist = np.zeros((N, N), np.float32)     # distancia (m) a borda mais proxima
nx = np.zeros((N, N), np.float32); ny = np.zeros((N, N), np.float32)
yy, xx = (np.mgrid[0:N, 0:N] + 0.5) / px
for i, (y0, y1, x0, x1) in enumerate(slabs):
    m = (yy >= y0) & (yy < y1) & (xx >= x0) & (xx < x1)
    sid[m] = i
    d = np.minimum(np.minimum(xx - x0, x1 - xx), np.minimum(yy - y0, y1 - yy))
    dist[m] = d[m]
    # lado da borda mais proxima (para luz de cima-esquerda)
    left = (xx - x0 < y1 - yy) & (xx - x0 < yy - y0) & (xx - x0 < x1 - xx)
    top = (yy - y0 < xx - x0) & (yy - y0 < x1 - xx) & (yy - y0 < y1 - yy)
    nx[m & left] = 1; ny[m & top] = 1

warp = pnoise(N, 40, 1) * 0.035
dist = np.clip(dist + warp, 0, None)
base = np.array([0.30, 0.325, 0.37])
tone = rng.uniform(-0.09, 0.09, len(slabs))[sid]
img = base[None, None, :] * (1 + tone)[..., None]
img *= (1 + pnoise(N, 12, 2) * 0.16 + pnoise(N, 60, 3) * 0.08 + pnoise(N, 250, 4) * 0.025)[..., None]
# manchas umidas mais claras e azuladas
wet = np.clip(pnoise(N, 7, 5) * 1.6, 0, 1)
img += (wet[..., None] * np.array([0.02, 0.035, 0.06]))
# chanfro pintado
g = 0.035; bev = 0.13
t = np.clip((dist - g) / bev, 0, 1); t = t * t * (3 - 2 * t)
lit = nx * 0.55 + ny * 0.55
img *= (1 + (1 - t)[..., None] * (lit[..., None] * 0.45 - 0.16))
# junta escura + musgo fino
gr = np.clip(dist / g, 0, 1); gr = gr * gr * (3 - 2 * gr)
moss_mask = np.clip(pnoise(N, 18, 6) * 2.0 - 0.7, 0, 1) * (1 - gr)
groutc = np.array([0.045, 0.05, 0.06])
img = img * gr[..., None] + groutc * (1 - gr[..., None])
img = img * (1 - 0.8 * moss_mask[..., None]) + np.array([0.11, 0.16, 0.07]) * 0.8 * moss_mask[..., None]
# lascas nas arestas e rachaduras finas
chip = (pnoise(N, 120, 7) > 0.55) & (dist < 0.10) & (dist > g)
img[chip] *= 0.7
for _ in range(10):
    x0 = rng.integers(0, N); y0 = rng.integers(0, N); L = rng.integers(N // 14, N // 6); a = rng.uniform(0, 6.28)
    for s in range(L):
        a += rng.normal(0, 0.12)
        xx_ = int(x0 + s * np.cos(a)) % N; yy_ = int(y0 + s * np.sin(a)) % N
        img[yy_, xx_] *= 0.55
img = np.clip(img, 0, 1)
Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(out)
print("ok", out, len(slabs), "lajotas", (img.mean((0, 1)) * 255).round())
