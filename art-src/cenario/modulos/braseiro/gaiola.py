"""Parte do braseiro: gaiola. build() acrescenta as malhas a _lib.objs."""
from ._lib import *


def build():
    random.seed(11)
    # ---- gaiola: dois anéis, ripas com rebites e cintas verticais
    Z0, Z1 = 1.12, 1.40
    ring(Z0 + 0.03, 0.68, 0.04); ring(Z1 - 0.03, 0.68, 0.04)
    ring(Z0 + 0.075, 0.70, 0.014, m=WORN, seg=32)
    N = 14
    for i in range(N):
        a = i * 2 * math.pi / N
        x, y = 0.68 * math.cos(a), 0.68 * math.sin(a)
        box((x, y, (Z0 + Z1) / 2), (0.05, 0.05, Z1 - Z0), rot=(0, 0, a), m=IRON, bev=0.008, wear=0.003, seed=50 + i, cut=0.2)
        if i % 2 == 0:
            box((x, y, (Z0 + Z1) / 2 + 0.02), (0.075, 0.075, 0.075), rot=(math.pi / 4, 0, a), m=TRIM, bev=0.008, wear=0.003, seed=70 + i, cut=0.2)
        else:
            rivet((x + 0.027 * math.cos(a), y + 0.027 * math.sin(a), (Z0 + Z1) / 2), r=0.018, rot=(0, math.pi / 2, a))
    # ---- espigões no aro: 8 médios + 4 altos nos cantos com espinhos laterais
    for i in range(8):
        a = (i + 0.5) * 2 * math.pi / 8
        cone((0.70 * math.cos(a), 0.70 * math.sin(a), Z1 - 0.02), 0.075, 0.20 + 0.04 * ((i * 7) % 3), sides=4, rot=(0, 0, a), seed=80 + i)
    for i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)]):
        a = math.atan2(sy, sx)
        x, y = 0.74 * math.cos(a), 0.74 * math.sin(a)
        box((x, y, 1.20), (0.14, 0.14, 0.40), rot=(0, 0, a), m=IRON, bev=0.016, wear=0.008, seed=90 + i)
        box((x, y, 1.40), (0.18, 0.18, 0.04), rot=(0, 0, a), m=WORN, bev=0.008, seed=94 + i)
        cone((x, y, 1.42), 0.11, 0.30, sides=4, rot=(0, 0, a), seed=98 + i)
        for sgn in (-1, 1):
            cone((x + sgn * 0.11 * -math.sin(a), y + sgn * 0.11 * math.cos(a), 1.26), 0.05, 0.16, sides=4, rot=(sgn * math.pi / 2 * 0.9, 0, a), seed=100 + i)
        for z in (1.12, 1.30):
            rivet((x + 0.073 * math.cos(a), y + 0.073 * math.sin(a), z), r=0.02, rot=(0, math.pi / 2, a))

