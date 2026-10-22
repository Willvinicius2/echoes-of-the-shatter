"""Pedra pintada da estátua (albedo + normal, numpy/PIL, 1024², ladrilhável). Cinza-violeta com manchas largas, veios,
rachaduras, pinceladas e desgaste assimétrico; sem luz assada. O normal vem de um mapa de altura (cinzel, rachaduras)."""
import numpy as np, os
from PIL import Image

def _ruido(n, escala, rng):
    """Ruído suave ladrilhável (soma de senoides em FFT)."""
    f = np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2
    ph = np.fft.fft2(rng.standard_normal((n, n)))
    h = np.real(np.fft.ifft2(ph * np.exp(-f * (escala ** 2) * 40)))
    return (h - h.mean()) / (h.std() + 1e-9)

def pedra(pasta, n=1024, seed=5):
    os.makedirs(pasta, exist_ok=True)
    rng = np.random.default_rng(seed)
    grande = _ruido(n, 90, rng); medio = _ruido(n, 24, rng); fino = _ruido(n, 6, rng)
    veio = 1 - np.abs(_ruido(n, 40, rng)); veio = np.clip((veio - 0.93) * 8, 0, 1) * 0.25
    # rachaduras: caminhadas aleatórias ladrilháveis
    rach = np.zeros((n, n), np.float32)
    for _ in range(16):
        x, y = rng.integers(0, n, 2); ang = rng.uniform(0, 6.28)
        for _ in range(rng.integers(60, 220)):
            ang += rng.normal(0, 0.10) + (0.9 if rng.random() < 0.012 else 0); x = (x + np.cos(ang) * 2) % n; y = (y + np.sin(ang) * 2) % n
            xi, yi = int(x), int(y); rach[yi, xi] = 1; rach[(yi + 1) % n, xi] = 0.6
    from PIL import ImageFilter
    rach = np.asarray(Image.fromarray((rach * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0)), np.float32) / 255
    rach = np.clip(rach * 3.2, 0, 1)
    base = np.array([0.43, 0.41, 0.47])
    graos = rng.standard_normal((n, n))
    fio = _ruido(n, 4, rng)
    riscas = np.roll(_ruido(n, 6, rng), 0, 0)
    f = np.fft.fftfreq(n); mask = np.exp(-(f[:, None] ** 2) * 6000 - (f[None, :] ** 2) * 40)   # estrias verticais (desgaste de chuva)
    estr = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * mask)); estr = (estr - estr.mean()) / (estr.std() + 1e-9)
    t = 1 + 0.13 * grande + 0.07 * medio + 0.04 * fino + 0.03 * graos * 0.4 + 0.06 * estr
    img = base[None, None, :] * t[..., None]
    img *= (1 - 0.35 * rach)[..., None]                       # rachaduras escuras
    img[..., 0] += 0.04 * veio; img[..., 1] += 0.03 * veio    # veios quentes
    puro = np.clip(_ruido(n, 60, rng) - 0.9, 0, 1)            # manchas de desgaste claras e assimétricas
    img += 0.07 * puro[..., None]
    sujo = np.clip(-_ruido(n, 120, rng) - 0.6, 0, 1)          # sujeira escura
    img *= (1 - 0.30 * sujo)[..., None]
    img = np.clip(img, 0, 1)
    alb = os.path.join(pasta, "estatua_pedra_albedo.png"); Image.fromarray((img * 255).astype(np.uint8)).save(alb)
    # altura -> normal OpenGL (+Y)
    h = 0.5 * medio + 0.3 * fino + 0.35 * _ruido(n, 3, rng) + 0.25 * estr + 0.2 * graos - 2.6 * rach
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5; gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    k = 0.9
    nx, ny, nz = -gx * k, gy * k, np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz); nrm = np.stack([nx / l, ny / l, nz / l], -1) * 0.5 + 0.5
    nor = os.path.join(pasta, "estatua_pedra_normal.png"); Image.fromarray((nrm * 255).astype(np.uint8)).save(nor)
    return alb, nor
