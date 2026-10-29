"""Gera godot/art2d/tiles/cripta_grama.png: 4 gramados e 4 lajes de caminho (64 px, repetem sem emenda).

As lajes usam a textura do piso de pedra da Cripta (cripta_tiles.png), recortada em células irregulares.
Uso: python tools/sprites2d/gerar_chao_grama.py [saida.png]
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

T = 64
SS = 4  # supersampling
rng = np.random.default_rng(2910)
atlas = Image.open("godot/art2d/tiles/cripta_tiles.png").convert("RGB")
pedra = [atlas.crop((i * T, 0, i * T + T, T)) for i in range(4)]


def ruido_periodico(n, escala):
    g = rng.random((escala, escala))
    img = Image.fromarray((g * 255).astype("uint8")).resize((n, n), Image.BICUBIC)
    return np.asarray(img, dtype=float) / 255.0


def grama(variante):
    n = T * SS
    base = np.zeros((n, n, 3))
    verde_esc = np.array([40, 54, 34]); verde_cl = np.array([74, 90, 48])
    r = 0.55 * ruido_periodico(n, 6) + 0.45 * ruido_periodico(n, 14)
    base[:] = verde_esc[None, None] * (1 - r[..., None]) + verde_cl[None, None] * r[..., None]
    im = Image.fromarray(base.astype("uint8"))
    d = ImageDraw.Draw(im)
    for _ in range(420):  # lâminas, desenhadas com cópia nas bordas para repetir sem emenda
        x, y = rng.integers(0, n), rng.integers(0, n)
        h = rng.integers(5, 12) * SS // 2
        dx = rng.integers(-3, 4) * SS // 2
        t = rng.random()
        cor = tuple(int(v) for v in (np.array([70, 92, 42]) * (0.8 + 0.5 * t) if rng.random() > 0.12 else np.array([128, 112, 58]) * (0.8 + 0.3 * t)))
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                d.line([(x + ox, y + oy), (x + ox + dx, y + oy - h)], fill=cor, width=SS // 2 + 1)
    return im.resize((T, T), Image.LANCZOS)


def laje(variante, verde):
    n = T * SS
    pts = rng.random((4, 2)) * n
    yy, xx = np.mgrid[0:n, 0:n]
    dist = np.full((2, n, n), 1e9)
    idx = np.zeros((n, n), int)
    best = np.full((n, n), 1e9); second = np.full((n, n), 1e9)
    for i, (px, py) in enumerate(pts):
        dx = np.minimum(abs(xx - px), n - abs(xx - px)); dy = np.minimum(abs(yy - py), n - abs(yy - py))
        d = np.hypot(dx, dy)
        nova = d < best
        second = np.where(nova, best, np.minimum(second, d))
        idx = np.where(nova, i, idx); best = np.where(nova, d, best)
    borda = (second - best)  # perto de 0 na divisa entre células
    mascara = np.clip((borda - 4.0 * SS) / (1.5 * SS), 0, 1)
    tex = np.asarray(pedra[variante].resize((n, n), Image.BICUBIC), dtype=float)
    tom = (0.85 + 0.3 * rng.random(4))[idx]
    tex = tex * tom[..., None]
    sombra = np.clip(1 - np.clip((borda - 3 * SS) / (9 * SS), 0, 1), 0, 1)
    tex = tex * (1 - 0.35 * sombra[..., None])  # laje mais escura na borda
    verde_n = np.asarray(verde.resize((n, n), Image.BICUBIC), dtype=float) * 0.75
    out = tex * mascara[..., None] + verde_n * (1 - mascara[..., None])
    return Image.fromarray(out.clip(0, 255).astype("uint8")).resize((T, T), Image.LANCZOS)


if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else "godot/art2d/tiles/cripta_grama.png"
    gs = [grama(i) for i in range(4)]
    ls = [laje(i, gs[i]) for i in range(4)]
    atl = Image.new("RGB", (T * 4, T * 2))
    for i in range(4):
        atl.paste(gs[i], (i * T, 0)); atl.paste(ls[i], (i * T, T))
    atl.save(saida)
