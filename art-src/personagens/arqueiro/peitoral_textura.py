"""Pinta T_Arqueiro_Peitoral_BC.png (512x512, numpy + PIL, python do sistema; sem luz assada).
Rodar: python peitoral_textura.py   -> godot/art/models/personagens/arqueiro/T_Arqueiro_Peitoral_BC.png
Atlas (v=1 e o topo da imagem):
  metade de cima (v 0.5..1): 8 celulas de pena de 64x256 (u = i/8..(i+1)/8; v=1 ponta, v=0.5 raiz)
     0 verde-musgo  1 oliva  2 pinho escuro  3 musgo + ponta dourada  4 oliva + ponta dourada
     5 bege-marfim  6 marfim + ponta dourada  7 marfim com listras verdes
  metade de baixo (v 0..0.5): 4 amostras de 128x256: tecido verde-escuro | couro | osso | metal/ouro
Osso: borda amarelada nas bordas da amostra (as pecas de osso mapeiam a caixa delas na amostra inteira).
"""
import os
import numpy as np
from PIL import Image, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "..", "..", "..", "godot", "art", "models", "personagens", "arqueiro", "T_Arqueiro_Peitoral_BC.png")
rng = np.random.default_rng(2026)


def ruido(w, h, escala, seed):
    r = np.random.default_rng(seed)
    g = r.random((max(2, int(h / escala)), max(2, int(w / escala))))
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im, dtype=np.float32) / 255.0


def fbm(w, h, seed, base=32):
    return sum(ruido(w, h, base / (2 ** i), seed + i) * a for i, a in enumerate((0.5, 0.3, 0.2)))


def mix(a, b, t):
    t = np.clip(t, 0, 1)[..., None]
    return a * (1 - t) + b * t


C = lambda r, g, b: np.array([r, g, b], np.float32) / 255.0
MUSGO, OLIVA, PINHO = C(78, 98, 44), C(106, 112, 52), C(40, 62, 38)
OURO, MARFIM, BEGE = C(214, 170, 62), C(232, 222, 190), C(196, 176, 130)
CASTANHO = C(92, 60, 36)

# (cor raiz, cor meio, usa ponta dourada, listras)
PENAS = [
    (C(46, 66, 34), MUSGO, 0.0, 0),
    (C(62, 70, 34), OLIVA, 0.0, 0),
    (C(26, 44, 30), PINHO * 1.35, 0.0, 0),
    (C(46, 66, 34), MUSGO, 1.0, 0),
    (C(62, 70, 34), OLIVA, 1.0, 0),
    (C(170, 150, 108), MARFIM, 0.0, 0),
    (C(170, 150, 108), MARFIM, 1.0, 0),
    (C(176, 156, 112), MARFIM, 0.0, 1),
]


def pena(i, w=64, h=256):
    raiz, meio, ouro, listras = PENAS[i]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    t = 1.0 - y / (h - 1)                 # 0 raiz (baixo) .. 1 ponta (cima)
    u = (x - (w - 1) / 2) / ((w - 1) / 2)  # -1..1
    img = mix(np.broadcast_to(raiz, (h, w, 3)).copy(), np.broadcast_to(meio, (h, w, 3)).copy(), (t * 1.6) ** 0.8)
    # barbas: linhas oblíquas a partir da nervura
    barb = np.sin((t * 46 - np.abs(u) * 9) * 1.0)
    barb2 = np.sin((t * 90 - np.abs(u) * 22) + rng.random() * 6)
    img *= (1 + 0.10 * barb[..., None] + 0.05 * barb2[..., None])
    n = fbm(w, h, 100 + i * 7, 8)
    img *= (0.88 + 0.24 * n)[..., None]
    if listras:
        faixa = (np.sin(t * 24 + u * 3) > 0.55).astype(np.float32)
        img = mix(img, mix(np.broadcast_to(MUSGO, img.shape).copy(), img, 0.15), faixa * 0.85)
    if ouro:
        img = mix(img, np.broadcast_to(OURO, img.shape).copy() * (0.85 + 0.2 * n[..., None]), (t - 0.70) / 0.12)
        img *= (1 + 0.08 * barb[..., None])
    # nervura central clara e engrossada
    rib = np.exp(-(u / 0.07) ** 2)
    ribc = mix(img, np.broadcast_to(BEGE, img.shape).copy() * 0.95, rib * 0.7 * (1 - 0.3 * t))
    img = ribc
    # bordas escurecidas e raiz escura
    img *= (1 - 0.30 * np.clip((np.abs(u) - 0.72) / 0.28, 0, 1))[..., None]
    img *= (0.72 + 0.28 * np.clip(t * 4, 0, 1))[..., None]
    return img


def tecido(w=128, h=256):
    n = fbm(w, h, 300, 16)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    base = mix(np.broadcast_to(C(34, 58, 36), (h, w, 3)).copy(), np.broadcast_to(C(60, 84, 44), (h, w, 3)).copy(), n)
    trama = (np.sin(x * 1.9) * np.sin(y * 1.9))[..., None]
    base *= (1 + 0.06 * trama)
    desg = fbm(w, h, 330, 24)
    base = mix(base, np.broadcast_to(OLIVA, base.shape).copy() * 0.9, (desg - 0.62) * 3)
    # remendos e costuras
    for yy in (60, 150, 220):
        base[yy:yy + 1, ::6] *= 0.6
    return base


def couro(w=128, h=256):
    n = fbm(w, h, 400, 6)
    base = mix(np.broadcast_to(C(70, 44, 26), (h, w, 3)).copy(), np.broadcast_to(C(130, 86, 50), (h, w, 3)).copy(), n)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    base *= (0.9 + 0.1 * np.sin(y * 0.7 + n * 6))[..., None]
    base[:, :4] *= 0.55; base[:, -4:] *= 0.55            # bordas escuras do couro
    base[:, 7:8:1] *= 0.65; base[:, -8:-7] *= 0.65      # linha de costura (picotada)
    base[::5, 7] = base[::5, 7] * 0.6
    gasto = fbm(w, h, 420, 20)
    base = mix(base, np.broadcast_to(C(160, 118, 72), base.shape).copy(), (gasto - 0.66) * 3)
    return base


def osso(w=128, h=256):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    n = fbm(w, h, 500, 24)
    base = mix(np.broadcast_to(C(222, 208, 170), (h, w, 3)).copy(), np.broadcast_to(C(240, 232, 204), (h, w, 3)).copy(), n)
    # veios longitudinais do osso e grao fino
    veio = 0.5 + 0.5 * np.sin(x * 0.55 + fbm(w, h, 520, 40) * 9)
    base *= (0.93 + 0.10 * veio)[..., None]
    base *= (0.96 + 0.08 * ruido(w, h, 2, 510))[..., None]
    # centro mais claro, laterais e fundo mais amarelos (arestas legiveis)
    cx = 1 - np.abs(x - (w - 1) / 2) / ((w - 1) / 2)
    base *= (0.88 + 0.14 * cx)[..., None]
    bx = np.minimum(x, w - 1 - x) / 20.0
    by = np.minimum(y, h - 1 - y) / 20.0
    borda = 1 - np.clip(np.minimum(bx, by), 0, 1)
    base = mix(base, np.broadcast_to(C(184, 140, 66), base.shape).copy(), borda ** 1.3 * 0.95)
    base *= (1 - 0.25 * (borda ** 4))[..., None]
    # rachaduras escuras e ramificadas
    r = np.random.default_rng(77)
    for _ in range(11):
        px, py = r.uniform(12, w - 12), r.uniform(12, h - 12)
        ang = r.uniform(0, 6.28)
        for k in range(r.integers(24, 60)):
            ang += r.normal(0, 0.35)
            px += np.cos(ang) * 1.5; py += np.sin(ang) * 1.5
            ix, iy = int(px), int(py)
            if 1 <= ix < w - 1 and 1 <= iy < h - 1:
                base[iy, ix] *= 0.30
                base[iy, ix + 1] *= 0.62
                base[iy + 1, ix] *= 0.75
    base = mix(base, np.broadcast_to(C(140, 106, 62), base.shape).copy(), (fbm(w, h, 530, 18) - 0.66) * 2.6)
    return base


def metal(w=128, h=256):
    n = fbm(w, h, 600, 12)
    base = mix(np.broadcast_to(C(150, 110, 40), (h, w, 3)).copy(), np.broadcast_to(C(232, 190, 80), (h, w, 3)).copy(), n)
    base[:, :3] *= 0.6; base[:, -3:] *= 0.6
    return base


def main():
    atlas = np.zeros((512, 512, 3), np.float32)
    for i in range(8):
        atlas[0:256, i * 64:(i + 1) * 64] = pena(i)
    for k, f in enumerate((tecido, couro, osso, metal)):
        atlas[256:512, k * 128:(k + 1) * 128] = f()
    im = Image.fromarray((np.clip(atlas, 0, 1) * 255).astype(np.uint8))
    # bleed: leve borrao so em cima (evita costura nas bordas das celulas)
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    im.save(SAIDA, optimize=True)
    print("OK", os.path.abspath(SAIDA), im.size)


main()
