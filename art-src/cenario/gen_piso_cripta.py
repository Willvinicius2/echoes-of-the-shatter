"""Gera T_Env_PisoA.png: lajota limpa e uniforme da Cripta (sem emenda, sem rachadura, sem simbolo).
Tile de 8 m = 4 fileiras x 4 lajotas de 2 m, fileiras alternadas deslocadas 1 m (junta em amarracao). Periodico em x e y.
Uso: python gen_piso_cripta.py <saida.png> [tamanho=2048]"""
import sys
import numpy as np
from PIL import Image

out = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
rng = np.random.default_rng(7)

def pnoise(res, cells, seed):
    """Ruido periodico suave (FFT) com `cells` ondas por tile, normalizado em [-1,1]."""
    r = np.random.default_rng(seed)
    w = r.standard_normal((res, res))
    f = np.fft.fft2(w)
    k = np.fft.fftfreq(res) * res
    kx, ky = np.meshgrid(k, k)
    f *= np.exp(-((kx**2 + ky**2) / (2 * cells**2)))
    n = np.real(np.fft.ifft2(f))
    return n / np.abs(n).max()

y, x = np.mgrid[0:N, 0:N].astype(np.float64) / N * 8.0   # unidades de lajota (2 m)
warp = 0.012
x = x + pnoise(N, 6, 1) * warp
y = y + pnoise(N, 6, 2) * warp
row = np.floor(y).astype(int) % 8
xs = x + (row % 2) * 0.5
col = np.floor(xs).astype(int) % 8
u = xs - np.floor(xs)
v = y - np.floor(y)

# SDF de retangulo arredondado (0 no centro da juntas, cresce para dentro)
d = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
grout = 0.03          # largura da junta (fracao da lajota)
bevel = 0.08           # largura do chanfro pintado
t = np.clip((d - grout) / bevel, 0, 1)
t = t * t * (3 - 2 * t)

# cor base por lajota: variacao discreta e suave
slab_id = row * 8 + col
tone = rng.uniform(-0.02, 0.02, 64)[slab_id]
hue = rng.uniform(-0.02, 0.02, 64)[slab_id]
base = np.array([0.285, 0.285, 0.34])
img = np.empty((N, N, 3))
for c in range(3):
    img[..., c] = base[c] * (1 + tone + hue * (c - 1))

# mancha pintada de baixa frequencia dentro de cada lajota (pincelada, sem ruido fino)
mott = pnoise(N, 14, 3) * 0.025
img *= (1 + mott)[..., None]

# chanfro: luz de cima-esquerda (borda superior/esquerda clara, inferior/direita escura)
edge_lit = ((u < np.minimum(1 - u, np.minimum(v, 1 - v))) | (v < np.minimum(1 - v, np.minimum(u, 1 - u)))).astype(float)
edge_dark = 1.0 - edge_lit
rim = (1 - t)
shade = 1 + rim * (edge_lit * 0.12 - edge_dark * 0.10)
img *= shade[..., None]

# centro levemente abaulado (volume pintado)
cx = (u - 0.5) * 2; cy = (v - 0.5) * 2
img *= (1 + 0.05 * (1 - np.clip(cx**2 + cy**2, 0, 1)))[..., None]

# junta escura
g = np.clip(d / grout, 0, 1)
g = g * g * (3 - 2 * g)
groutcol = np.array([0.075, 0.09, 0.12])
img = img * g[..., None] + groutcol * (1 - g[..., None])

img = np.clip(img, 0, 1)
Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(out)
print("ok", out, img.mean((0, 1)) * 255)
