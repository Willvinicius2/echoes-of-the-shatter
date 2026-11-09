#!/usr/bin/env python3
"""Gera o atlas de piso da Pedreira dos Ecos (godot/art2d/tiles/cripta_pedreira.png) a partir do atlas de gramado da
Cripta (cripta_grama.png): mesma grade (4 variantes de chão na linha 0, 4 variantes de laje de caminho na linha 1),
mesmos pixels, só a cor muda (direção do Jev: a Pedreira é seca e poeirenta, a paleta-base da área 1 fica, o verde vira
ocre/terra, o capim amarelo vira palha clara, a pedra cinza esquenta um pouco).

O chão não é mais um giro de matiz: cada pixel de grama passa por uma rampa de ocres pela luminância dele (mapa de
degradê), então o que era sombra do gramado vira terra escura, o miolo vira ocre e as folhas claras viram palha de poeira:
3 tons de ocre bem separados em vez de um marrom-oliva chapado (revisão do Jev e do revisor de arte, 08/11/2026).

Uso: python3 -I tools/sprites2d/recolorir_piso_pedreira.py
Só precisa de PIL e numpy. Mesma saída a cada execução (sem aleatório).
"""
import colorsys
import os

import numpy as np
from PIL import Image

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
ENTRADA = os.path.join(R, "godot", "art2d", "tiles", "cripta_grama.png")
SAIDA = os.path.join(R, "godot", "art2d", "tiles", "cripta_pedreira.png")

LUM = np.array([0.299, 0.587, 0.114])
# luminância do gramado original (chão: 0,23 a 0,41; mediana 0,28) -> RGB do ocre: terra escura, ocre, ocre claro, palha de poeira
RAMPA = [
    (0.20, (66, 46, 30)),
    (0.24, (90, 64, 38)),
    (0.276, (112, 80, 44)),
    (0.31, (132, 96, 52)),
    (0.37, (168, 130, 70)),
    (0.42, (206, 170, 104)),
]
DESSATURAR = 0.12   # parte da cor que volta para o cinza da mesma luz: tira o ar de doce do ocre puro
LIMITE_PEDRA = 0.13   # abaixo desta saturação o pixel é pedra cinza (laje), não grama


def _rampa(luma):
    xs = [p[0] for p in RAMPA]
    return tuple(float(np.interp(luma, xs, [p[1][k] for p in RAMPA])) for k in range(3))


def recolorir(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < LIMITE_PEDRA:
        # pedra cinza (laje): só um calor leve, sem mudar a luz
        r2, g2, b2 = min(r * 1.06 + 0.012, 1.0), g * 1.0, max(b * 0.92 - 0.004, 0.0)
        return tuple(int(round(c * 255)) for c in (r2, g2, b2))
    luma = float(np.dot((r, g, b), LUM))
    cor = _rampa(luma)
    cinza = float(np.dot(cor, LUM))
    return tuple(int(round(cinza + (c - cinza) * (1.0 - DESSATURAR))) for c in cor)


def main():
    im = Image.open(ENTRADA).convert("RGBA")
    a = np.array(im)
    cache = {}
    out = a.copy()
    for y in range(a.shape[0]):
        for x in range(a.shape[1]):
            c = tuple(int(v) for v in a[y, x, :3])
            if c not in cache:
                cache[c] = recolorir(c)
            out[y, x, :3] = cache[c]
    Image.fromarray(out, "RGBA").save(SAIDA)
    print("gravado", os.path.relpath(SAIDA, R), im.size, "cores distintas:", len(cache))


if __name__ == "__main__":
    main()
