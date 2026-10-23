"""Pinta as texturas do capuz v4 (numpy + PIL). Saida: texturas_capuz_v4/*.png
  T_Capuz_BC (1024, pano verde-musgo pintado a mao; u = angulo, 0.5 = frente; v alto = topo), T_Ouro_BC (256, friso dourado),
  T_Mascara_BC (512, osso: u = 0.5 + x/0.30, v = altura da mascara), T_Lenco_BC (256, pano verde escuro).
Rodar: python pintar_capuz_v4.py
"""
import os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "texturas_capuz_v4")
os.makedirs(OUT, exist_ok=True)


def ruido(w, h, escala, seed, sx=1.0, sy=1.0):
    r = np.random.default_rng(seed)
    gw, gh = max(2, int(w / (escala * sx))), max(2, int(h / (escala * sy)))
    g = r.random((gh, gw)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im, np.float32) / 255.0


def fbm(w, h, esc, seed, sx=1.0, sy=1.0, oit=4):
    t = np.zeros((h, w), np.float32)
    a, s = 1.0, 0
    for k in range(oit):
        t += a * ruido(w, h, esc / (2 ** k), seed + k, sx, sy)
        s += a
        a *= 0.5
    return t / s


def mistura(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


def salvar(arr, nome):
    a = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(a, "RGB").save(os.path.join(OUT, nome))
    print("ok", nome, a.shape)


def pano(W, H, seed, escuro, medio, claro, listras=0.55):
    """pano pintado: pinceladas verticais longas + manchas + trama."""
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    xx = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    longa = fbm(W, H, 80, seed, sx=0.7, sy=1.0)                       # pinceladas compridas na vertical
    manch = fbm(W, H, 160, seed + 20, 1.0, 1.0)
    fina = fbm(W, H, 10, seed + 40, sx=0.35, sy=1.4, oit=2)
    trama = 0.5 + 0.5 * np.sin(xx * W * 0.9) * np.sin(yy * H * 0.9)
    t = np.clip(0.55 * longa + 0.35 * manch + 0.10 * fina, 0, 1)
    t = (t - t.min()) / (t.max() - t.min() + 1e-6)
    t = np.clip((t - 0.5) * 1.5 + 0.5, 0, 1)
    c1 = mistura(np.array(escuro, np.float32), np.array(medio, np.float32), np.clip(t * 2, 0, 1))
    c2 = mistura(c1, np.array(claro, np.float32) + 0 * c1, np.clip(t * 2 - 1, 0, 1))
    c2 = c2 * (1 - 0.06 * listras + 0.06 * listras * trama[..., None] * 2)
    return c2


def smooth01(a, b, x):
    q = np.clip((x - a) / (b - a), 0, 1)
    return q * q * (3 - 2 * q)


def sem_emenda(img):
    """torna a textura continua nas bordas esquerda/direita (u envolve o capuz)."""
    H, W = img.shape[:2]
    w = (np.sin(np.pi * np.arange(W) / W) ** 2)[None, :, None].astype(np.float32)
    return img * w + np.roll(img, W // 2, axis=1) * (1 - w)


def capuz():
    W = H = 1024
    # imagem y=0 e o topo (v=1): luz vem de cima -> topo claro, barra (y=H) escura
    topo = np.linspace(1.18, 0.62, H, dtype=np.float32)[:, None, None]
    img = pano(W, H, 3, (20, 38, 22), (46, 76, 36), (100, 130, 60)) * topo
    # dobras pintadas: mesma formula das dobras da geometria (build_capuz_v4.hood): vales escuros, cristas claras
    psi = (np.linspace(0, 1, W, dtype=np.float32)[None, :] - 0.5) * 2 * np.pi
    tt = np.clip((1 - np.linspace(0, 1, H, dtype=np.float32)[:, None] - 0.02) / 0.96, 0, 1)
    env = smooth01(0.45, 1.3, np.abs(psi))
    cr = np.abs(np.sin(psi * 2.6 + 4.0 * tt + 0.5 * np.sin(psi * 2.0))) ** 0.55 - 0.55
    cr2 = np.abs(np.sin(psi * 4.7 - 3.0 * tt + 1.0)) ** 0.7 - 0.55
    f = (cr * 0.75 + cr2 * 0.35) * (0.35 + 0.65 * env)
    img = img * (1.0 + 0.55 * f)[..., None]
    # pinceladas de luz amarelada
    r = np.random.default_rng(5)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(140):
        x = r.integers(0, W)
        y = r.integers(0, H - 80)
        L = r.integers(30, 120)
        d.line([(x, y), (x + r.integers(-8, 9), y + L)], fill=(150, 176, 88, int(r.integers(10, 26))), width=int(r.integers(2, 6)))
    for _ in range(110):
        x = r.integers(0, W)
        y = r.integers(0, H - 80)
        L = r.integers(30, 120)
        d.line([(x, y), (x + r.integers(-8, 9), y + L)], fill=(10, 24, 12, int(r.integers(12, 30))), width=int(r.integers(2, 6)))
    img = np.asarray(im, np.float32)
    # topo: dissolve num tom unico (polo da UV)
    n = int(H * 0.16)
    media = img[:n].mean(axis=(0, 1))
    for y in range(n):
        a = (y / n) ** 1.5
        img[y] = media * (1 - a) + img[y] * a
    # barra: faixa mais escura com costura
    y0 = int(H * 0.90)
    img[y0:] *= 0.80
    img = sem_emenda(img)
    salvar(img, "T_Capuz_BC.png")


def ouro():
    W, H = 256, 256
    t = fbm(W, H, 30, 31, 1.0, 0.4, 3)
    base = mistura(np.array((140, 100, 38), np.float32) + np.zeros((H, W, 3), np.float32), np.array((226, 186, 88), np.float32) + np.zeros((H, W, 3), np.float32), t)
    r = np.random.default_rng(9)
    im = Image.fromarray(base.astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    for x in range(8, W, 24):  # pontos de costura
        d.ellipse([x, 120, x + 8, 128], fill=(90, 58, 20, 150))
    for _ in range(60):
        x = r.integers(0, W)
        d.line([(x, 0), (x + r.integers(-3, 4), H)], fill=(255, 230, 150, 20), width=2)
    salvar(np.asarray(im, np.float32), "T_Ouro_BC.png")


def mascara():
    W = H = 512
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = xx / W
    v = 1 - yy / H            # v alto = testa
    t = fbm(W, H, 70, 51, 1.0, 1.0, 4)
    osso = mistura(np.array((196, 178, 140), np.float32) + np.zeros((H, W, 3), np.float32),
                   np.array((240, 230, 202), np.float32) + np.zeros((H, W, 3), np.float32), np.clip((t - 0.2) * 1.6, 0, 1))
    # bico mais quente/escuro, testa mais clara
    osso = osso * (0.90 + 0.14 * v[..., None])
    # escurece nas bordas laterais e embaixo
    borda = np.clip(np.abs(u - 0.5) * 2, 0, 1) ** 2.2
    osso = osso * (1 - 0.22 * borda[..., None])
    im = Image.fromarray(np.clip(osso, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    r = np.random.default_rng(13)
    # rachaduras finas e manchas verdes de musgo na base do bico
    for _ in range(26):
        x, y = r.integers(60, W - 60), r.integers(10, H - 10)
        pts = [(x, y)]
        for k in range(r.integers(4, 9)):
            x += r.integers(-14, 15)
            y += r.integers(6, 22)
            pts.append((x, y))
        d.line(pts, fill=(88, 66, 40, 150), width=2)
    # friso verde pintado em volta dos olhos (tracado da folha) e sobrancelha escura
    for s in (-1, 1):
        cx = (0.5 + s * 0.060 / 0.30) * W
        cz = (1 - (1.318 - 1.15) / (1.395 - 1.15)) * H
        d.ellipse([cx - 62, cz - 30, cx + 62, cz + 30], outline=(70, 52, 30, 120), width=5)
    # veios verdes junto ao bico
    for _ in range(30):
        x = r.integers(int(W * 0.40), int(W * 0.60))
        y = r.integers(int(H * 0.55), H)
        d.line([(x, y), (x + r.integers(-4, 5), y + r.integers(10, 30))], fill=(104, 140, 70, 60), width=3)
    im = im.filter(ImageFilter.GaussianBlur(0.7))
    salvar(np.asarray(im, np.float32), "T_Mascara_BC.png")


def lenco():
    W = H = 256
    img = pano(W, H, 77, (26, 46, 28), (52, 82, 40), (92, 124, 60))   # pregas finas
    salvar(img, "T_Lenco_BC.png")


if __name__ == "__main__":
    capuz()
    ouro()
    mascara()
    lenco()
