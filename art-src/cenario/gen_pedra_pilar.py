"""Gera T_Env_Pilar.png: pedra lisa e inteira para pilares (sem tijolos): manchas largas, veios verticais finos e poucas lascas escuras. Periodica."""
import sys
import numpy as np
from PIL import Image
out = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 1024

def pnoise(shape, fx, fy, seed):
    r = np.random.default_rng(seed)
    f = np.fft.fft2(r.standard_normal(shape))
    ky = np.fft.fftfreq(shape[0]) * shape[0]; kx = np.fft.fftfreq(shape[1]) * shape[1]
    kxg, kyg = np.meshgrid(kx, ky)
    f *= np.exp(-((kxg / fx) ** 2 + (kyg / fy) ** 2) / 2)
    n = np.real(np.fft.ifft2(f)); return n / np.abs(n).max()

base = np.array([0.44, 0.41, 0.37])
blot = pnoise((N, N), 3, 3, 1) * 0.16 + pnoise((N, N), 9, 9, 2) * 0.04
veins = pnoise((N, N), 40, 2, 3) * 0.09        # veios verticais (u rapido, v lento)
strata = pnoise((N, N), 2, 14, 4) * 0.04       # camadas largas na horizontal
speck = pnoise((N, N), 120, 120, 5) * 0.015
v = 1 + blot + veins + strata + speck
img = base[None, None, :] * v[..., None]
# poucas lascas escuras, finas, verticais
r = np.random.default_rng(9)
for _ in range(14):
    x0 = r.integers(0, N); y0 = r.integers(0, N); L = r.integers(N // 8, N // 3)
    for t in range(L):
        yy = (y0 + t) % N; xx = int(x0 + 6 * np.sin(t / 25.0 + x0)) % N
        img[yy, xx] *= 0.72
        img[yy, (xx + 1) % N] *= 0.88
img = np.clip(img, 0, 1)
Image.fromarray((img * 255 + .5).astype(np.uint8)).save(out); print("ok", img.mean((0, 1)) * 255)
