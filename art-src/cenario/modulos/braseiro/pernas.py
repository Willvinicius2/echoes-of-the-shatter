"""Pernas: sapatas de pedra lascada, fustes de ferro afunilados, cintas enferrujadas, capitéis, rebites, travessas em X."""
from ._lib import *

LEG = 0.42

def build():
    r = rng(101)
    for i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)]):
        x, y = sx * LEG + r.uniform(-.012, .012), sy * LEG + r.uniform(-.012, .012)
        k = r.uniform(0.97, 1.05); yaw = r.uniform(-0.04, 0.04); lean = (r.uniform(-.015, .015), r.uniform(-.015, .015), yaw)
        # sapata: dois blocos de pedra empilhados e lascados (boolean real)
        b1 = fbox(PEDRA, (x, y, 0.05), (0.50 * k, 0.48 * k, 0.10), (0, 0, yaw), cuts=1, amp=0.004, bev=0.012, seed=10 + i)
        chip_corners(b1, 6, 0.07, 20 + i)
        b2 = fbox(PEDRA, (x, y, 0.15), (0.40 * k, 0.40 * k, 0.10), (0, 0, yaw + 0.05), cuts=1, amp=0.004, bev=0.012, seed=30 + i)
        chip_corners(b2, 5, 0.055, 40 + i)
        # fuste afunilado em ferro, com facetas de martelo
        fbox((FERRO, FERRO2, FERRO3, FERRO2)[i], (x, y, 0.60), (0.23 * k, 0.23 * k, 0.86), lean, cuts=4, amp=0.004, bev=0.010, seed=50 + i, taper=0.9)
        for z, mm in ((0.30, ENVELH), (0.80, ENVELH)):                     # cintas
            fbox(mm, (x, y, z + r.uniform(-.015, .015)), (0.29 * k, 0.29 * k, 0.05), (0, 0, yaw), cuts=2, amp=0.003, bev=0.008, seed=60 + i)
        fbox(ENVELH, (x, y, 0.965), (0.33 * k, 0.33 * k, 0.10), (0, 0, yaw), cuts=2, amp=0.004, bev=0.012, seed=70 + i)   # capitel
        fbox(FERRO, (x, y, 1.03), (0.26 * k, 0.26 * k, 0.04), (0, 0, yaw + math.pi / 4), cuts=1, amp=0.003, bev=0.008, seed=80 + i)
        espigao(FERRO, (x, y, 1.05), (r.uniform(-.06, .06), r.uniform(-.06, .06), 1), 0.095 * k, 0.20 + r.uniform(-.02, .04), seed=90 + i)
        for kf in range(4):
            a = kf * math.pi / 2 + yaw
            for z in (0.42, 0.68):
                rebite(ENVELH, (x + 0.12 * k * math.cos(a), y + 0.12 * k * math.sin(a), z + r.uniform(-.01, .01)), (math.cos(a), math.sin(a), 0), 0.017, seed=100 + i * 10 + kf)
    # travessas em X + diamante central
    for j, ang in enumerate((math.pi / 4, -math.pi / 4)):
        fbox(FERRO, (0, 0, 0.38 + j * 0.004), (1.30, 0.075, 0.075), (0, 0, ang), cuts=6, amp=0.003, bev=0.008, seed=120 + j)
    fbox(ENVELH, (0, 0, 0.38), (0.20, 0.20, 0.20), (math.pi / 4, 0, math.pi / 4), cuts=2, amp=0.004, bev=0.014, seed=130)
    espigao(FERRO, (0, 0, 0.27), (0, 0, -1), 0.10, 0.18, seed=131)
