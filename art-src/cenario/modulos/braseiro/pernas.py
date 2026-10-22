"""Parte do braseiro: pernas. build() acrescenta as malhas a _lib.objs."""
from ._lib import *


def build():
    random.seed(11)
    # ---- pernas: 4 colunas com sapata escalonada, cintas, rebites, capitel e ponta de canto
    LEG = 0.42
    for i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)]):
        x, y = sx * LEG, sy * LEG
        box((x, y, 0.045), (0.46, 0.46, 0.09), m=IRON, bev=0.02, wear=0.01, seed=i)                 # sapata baixa
        box((x, y, 0.145), (0.38, 0.38, 0.11), m=TRIM, bev=0.016, seed=i + 4)                       # sapata alta
        box((x, y, 0.62), (0.22, 0.22, 0.80), m=IRON, bev=0.018, wear=0.008, seed=i + 8)            # fuste
        box((x, y, 0.30), (0.27, 0.27, 0.05), m=WORN, bev=0.01, seed=i + 12)                        # cinta de ferro vivo
        box((x, y, 0.80), (0.27, 0.27, 0.05), m=WORN, bev=0.01, seed=i + 16)
        box((x, y, 0.96), (0.32, 0.32, 0.10), m=TRIM, bev=0.016, seed=i + 20)                       # capitel
        cone((x, y, 1.01), 0.11, 0.22, rot=(0, 0, math.pi / 4), seed=i)                              # ponta de canto
        for k in range(4):                                                                           # rebites nas faces do fuste
            a = k * math.pi / 2
            for z in (0.40, 0.70):
                rivet((x + 0.114 * math.cos(a), y + 0.114 * math.sin(a), z), rot=(0, math.pi / 2, a))
    # ---- travessas em X e diamante central
    for j, ang in enumerate((math.pi / 4, -math.pi / 4)):
        box((0, 0, 0.38), (1.28, 0.075, 0.075), rot=(0, 0, ang), m=IRON, bev=0.012, seed=30 + j, cut=0.1)
    box((0, 0, 0.38), (0.22, 0.22, 0.22), rot=(math.pi / 4, 0, math.pi / 4), m=TRIM, bev=0.02, seed=33)
    cone((0, 0, 0.14), 0.12, 0.24, rot=(math.pi, 0, math.pi / 4), seed=34)
    ring(0.38, 0.17, 0.018, m=WORN, seg=16)

