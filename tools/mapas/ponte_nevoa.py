#!/usr/bin/env python3
"""Névoa do abismo e arcos distantes da Ponte do Sino, pintados por código (pedido dos revisores, 11/11/2026).

A névoa antiga eram manchas radiais macias; aqui ela vira degradê em pixel art: três tons de azul frio, com os degraus entre
eles em pontilhado ordenado (Bayer 4x4), na grade de 1 px de mundo. Os arcos distantes são a silhueta de outra ponte lá no fundo,
escura e esfumada, que some na névoa pelos pés. Tudo determinístico (sementes fixas), sem custo.

Uso: python3 -I tools/mapas/ponte_nevoa.py [pasta_saida]
Escreve godot/art2d/ponte/nevoa_<0..2>.png (512x176, névoa que sobe e some em cima e embaixo) e arco_distante_<0..1>.png (608x150)."""
import os
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ponte_pixel as P

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SAIDA = os.path.join(RAIZ, 'godot', 'art2d', 'ponte')
# tons da névoa: do mais ralo ao mais denso (RGBA); o mais claro fica no miolo
NEVOA = [(70, 88, 122, 96), (96, 118, 154, 124), (130, 154, 188, 150)]
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) / 16.0


def _bayer(w, h):
    return np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w]


def nevoa(semente, w=512, h=176):
    rng = np.random.default_rng(100 + semente)
    x = np.arange(w)[None, :].astype(np.float32)
    y = np.arange(h)[:, None].astype(np.float32)
    # faixa horizontal que engrossa e afina ao longo do comprimento (lóbulos de fase própria), e some em cima e embaixo
    campo = np.zeros((1, w), np.float32)
    for k in range(4):
        campo += np.sin(x / w * np.pi * 2 * (k + 1) + rng.uniform(0, 6.28)) / (k + 1.5)
    campo = (campo - campo.min()) / (campo.max() - campo.min() + 1e-6)
    centro = h * 0.5 + (campo - 0.5) * h * 0.25
    meia = h * (0.18 + 0.2 * campo)
    d = 1.0 - np.abs(y - centro) / meia
    d = np.clip(d, 0.0, 1.0)
    ruido = rng.random((h // 6 + 2, w // 10 + 2)).astype(np.float32)   # bordas em degraus irregulares (blocos de 10x6 px), não retas
    ruido = np.kron(ruido, np.ones((6, 10), np.float32))[:h, :w]
    d = np.clip(d * 0.85 + (ruido - 0.5) * 0.45 * (d > 0.0) * (1.0 - d), 0.0, 1.0)
    d = d * (0.45 + 0.55 * np.clip(np.sin(x / w * np.pi) ** 0.5, 0, 1))   # as pontas do quadro somem de lado
    v = d * 3.4
    nivel = np.floor(v + _bayer(w, h) - 0.2).astype(int).clip(0, 3)
    img = np.zeros((h, w, 4), np.uint8)
    for n, cor in enumerate(NEVOA, start=1):
        img[nivel == n] = cor
    return img


def arco(semente, w=608, h=150):
    img = np.zeros((h, w, 4), np.uint8)
    rng = np.random.default_rng(200 + semente)
    massa = (28, 36, 58, 255)       # pedra distante, já esfumada pelo ar
    luz = (46, 58, 86, 255)
    vao = 96
    pilar = 18
    n = 5
    x0 = (w - (n * vao + (n + 1) * pilar)) // 2
    topo = 14
    cornija = 8
    base = h - 6
    for i in range(n + 1):   # pilares
        px = x0 + i * (vao + pilar)
        img[topo + cornija:base, px:px + pilar] = massa
        img[topo + cornija:base, px:px + 2] = luz
    img[topo:topo + cornija, x0:x0 + n * vao + (n + 1) * pilar] = massa
    img[topo, x0:x0 + n * vao + (n + 1) * pilar] = luz
    for i in range(n):   # arcos: o miolo do vão é abismo (vazado) e o de cima é semicírculo
        ax = x0 + pilar + i * (vao + pilar)
        cy = topo + cornija + vao // 2
        for yy in range(topo + cornija, base):
            for xx in range(ax, ax + vao):
                dx = xx - (ax + vao / 2.0)
                if yy >= cy:
                    img[yy, xx] = massa if False else (0, 0, 0, 0)
                elif dx * dx + (yy - cy) ** 2 <= (vao / 2.0 - 1) ** 2:
                    img[yy, xx] = (0, 0, 0, 0)
                else:
                    img[yy, xx] = massa
    # alguns blocos mais claros e falhas, para não ficar liso
    for _ in range(40):
        bx, by = int(rng.integers(x0, x0 + n * (vao + pilar))), int(rng.integers(topo, base - 10))
        if img[by, bx, 3] > 0:
            img[by:by + 3, bx:bx + 6] = luz if rng.random() < 0.6 else (20, 26, 44, 255)
    # os pés somem na névoa: pontilhado ordenado de baixo para cima
    ys = np.arange(h)[:, None].astype(np.float32)
    f = np.clip((base - ys) / 58.0, 0.0, 1.0)
    manter = (f + (_bayer(w, h) - 0.5) * 0.9) > 0.5
    img[..., 3] = np.where(manter, img[..., 3], 0)
    return img


def main():
    saida = sys.argv[1] if len(sys.argv) > 1 else SAIDA
    os.makedirs(saida, exist_ok=True)
    for i in range(3):
        Image.fromarray(nevoa(i), 'RGBA').save(os.path.join(saida, 'nevoa_%d.png' % i))
    for i in range(2):
        Image.fromarray(arco(i), 'RGBA').save(os.path.join(saida, 'arco_distante_%d.png' % i))
    print('ok')


if __name__ == '__main__':
    main()
