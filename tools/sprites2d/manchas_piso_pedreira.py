#!/usr/bin/env python3
"""Manchas de poeira e de terra do piso da Pedreira dos Ecos (godot/art2d/tiles/pedreira_mancha_0..3.png).

O gramado da Cripta ganha manchas grandes e suaves de tom (radiais com degradê) em `room_2d.gd::_tons_do_gramado`. Na
Pedreira isso virava borrão: o piso é pixel art de 1 px de grade, então as manchas são PNG pintados aqui, em branco com alfa
binário (0 ou 255): o miolo é chapado, a beira se desfaz em dither de Bayer 4x4 (nada de degradê) e o miolo tem falhas
esparsas de pó. O motor tinge cada mancha por `modulate` (poeira clara, ocre, terra escura ou ferrugem, com alfa baixo para
a palha do chão aparecer por baixo) e cola sempre a 1:1, em px inteiros, só com giro de 0/180 graus por espelho.

Uso: python3 -I tools/sprites2d/manchas_piso_pedreira.py
Só precisa de PIL e numpy. Mesma saída a cada execução (semente fixa).
"""
import math
import os
import random

import numpy as np
from PIL import Image

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
PASTA = os.path.join(R, "godot", "art2d", "tiles")
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) / 16.0 + 1.0 / 32.0
LARGURA_BEIRA = 18.0   # px de dither entre o miolo chapado e o vazio

# (largura, altura, nº de elipses, semente): quatro silhuetas bem diferentes
FORMAS = [(256, 184, 4, 11), (224, 176, 3, 23), (288, 152, 5, 37), (196, 196, 4, 53)]

_DISCOS = {}


def _discos(raio):
    if raio not in _DISCOS:
        offs = []
        for dy in range(-raio, raio + 1):
            for dx in range(-raio, raio + 1):
                d = math.hypot(dx, dy)
                if 0 < d <= raio:
                    offs.append((d, dx, dy))
        offs.sort()
        _DISCOS[raio] = offs
    return _DISCOS[raio]


def _distancia_ate(alvo, raio):
    """Distância de cada pixel ao `alvo` mais próximo, limitada a `raio` (`raio + 1` quando não há nenhum perto)."""
    h, w = alvo.shape
    res = np.full((h, w), raio + 1.0, dtype=np.float32)
    res[alvo] = 0.0
    pad = np.pad(alvo, raio, constant_values=False)
    feito = alvo.copy()
    for d, dx, dy in _discos(raio):
        desl = pad[raio + dy:raio + dy + h, raio + dx:raio + dx + w]
        novo = desl & ~feito
        if novo.any():
            res[novo] = d
            feito |= novo
            if feito.all():
                break
    return res


def _ruido(h, w, passo, rng):
    """Ruído de valor suave em [0, 1] (grade grosseira interpolada)."""
    gh, gw = h // passo + 3, w // passo + 3
    g = np.array([[rng.random() for _ in range(gw)] for _ in range(gh)], dtype=np.float32)
    ys = np.arange(h) / float(passo)
    xs = np.arange(w) / float(passo)
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    a, b = g[y0][:, x0], g[y0][:, x0 + 1]
    c, d = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def pintar_mancha(w, h, n_elipses, semente):
    rng = random.Random(semente)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # união de elipses e borda ondulada por ruído (a silhueta nunca é uma elipse)
    dentro = np.zeros((h, w), dtype=bool)
    for k in range(n_elipses):
        cx = w * (0.28 + 0.44 * rng.random())
        cy = h * (0.3 + 0.4 * rng.random())
        rx = w * rng.uniform(0.16, 0.3)
        ry = h * rng.uniform(0.18, 0.32)
        ang = rng.uniform(0, math.pi)
        dx, dy = xx - cx, yy - cy
        u = (dx * math.cos(ang) + dy * math.sin(ang)) / rx
        v = (-dx * math.sin(ang) + dy * math.cos(ang)) / ry
        dentro |= (u * u + v * v) < 1.0
    onda = _ruido(h, w, 22, rng) - 0.5
    borda = _distancia_ate(~dentro, 24)
    # empurra a borda para dentro ou para fora até ~5 px segundo o ruído
    dentro2 = dentro & (borda > 3.0 - onda * 10.0) | (~dentro & (_distancia_ate(dentro, 8) < 2.0 + onda * 8.0))
    d_in = _distancia_ate(~dentro2, int(LARGURA_BEIRA) + 2)
    cobertura = np.clip(d_in / LARGURA_BEIRA, 0.0, 1.0) ** 0.85
    cobertura[~dentro2] = 0.0
    # falhas esparsas de pó no miolo
    poeira = _ruido(h, w, 14, rng)
    cobertura = np.where(d_in >= LARGURA_BEIRA, 0.84 + 0.16 * poeira, cobertura)
    # moldura da imagem: nada encosta na borda do PNG
    cobertura[:3, :] = cobertura[-3:, :] = 0.0
    cobertura[:, :3] = cobertura[:, -3:] = 0.0
    bay = np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w]
    visivel = bay < cobertura
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[..., :3] = 255
    img[..., 3] = np.where(visivel, 255, 0)
    return Image.fromarray(img, "RGBA")


def main():
    for i, (w, h, n, sem) in enumerate(FORMAS):
        im = pintar_mancha(w, h, n, sem)
        caminho = os.path.join(PASTA, "pedreira_mancha_%d.png" % i)
        im.save(caminho)
        opaco = int((np.array(im)[..., 3] > 0).sum())
        print("gravado", os.path.relpath(caminho, R), im.size, "px opacos:", opaco)


if __name__ == "__main__":
    main()
