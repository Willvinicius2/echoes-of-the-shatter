"""Gaiola do aro: dois anéis, ripas com rebites e losangos, cantoneiras altas e espigões de alturas variadas."""
from ._lib import *

Z0, Z1 = 1.12, 1.40

def anel(z, R, rr, m, seed, seg=36):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=rr, major_segments=seg, minor_segments=8, location=(0, 0, z))
    t = bpy.context.object; r = rng(seed)
    for v in t.data.vertices: v.co += Vector((r.uniform(-.004, .004), r.uniform(-.004, .004), r.uniform(-.004, .004)))
    return add(t, m, PARTE[0])

def build():
    r = rng(301)
    anel(Z0 + 0.03, 0.68, 0.042, ENVELH, 1); anel(Z1 - 0.03, 0.68, 0.042, ENVELH, 2); anel(Z0 + 0.09, 0.705, 0.014, FERRO, 3, 48)
    N = 14
    for i in range(N):
        a = i * 2 * math.pi / N + r.uniform(-.015, .015)
        x, y = 0.68 * math.cos(a), 0.68 * math.sin(a)
        fbox(FERRO, (x, y, (Z0 + Z1) / 2), (0.05, 0.05, Z1 - Z0 + r.uniform(-.01, .01)), (0, 0, a), cuts=3, amp=0.0025, bev=0.006, seed=310 + i)
        if i % 2 == 0:
            fbox(ENVELH, (x, y, (Z0 + Z1) / 2 + 0.02), (0.075, 0.075, 0.075), (math.pi / 4, 0, a), cuts=1, amp=0.002, bev=0.007, seed=330 + i)
        else:
            rebite(ENVELH, (x + 0.027 * math.cos(a), y + 0.027 * math.sin(a), (Z0 + Z1) / 2 + r.uniform(-.02, .02)), (math.cos(a), math.sin(a), 0), 0.018, seed=350 + i)
    # espigões do aro: 8, alturas e inclinações variadas
    for i in range(8):
        a = (i + 0.5) * 2 * math.pi / 8 + r.uniform(-.05, .05)
        tilt = r.uniform(0.0, 0.18)
        espigao(FERRO, (0.70 * math.cos(a), 0.70 * math.sin(a), Z1 - 0.02), (math.cos(a) * tilt, math.sin(a) * tilt, 1), 0.075, r.uniform(0.18, 0.28), seed=370 + i)
    # cantoneiras altas com espinhos laterais
    for i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)]):
        a = math.atan2(sy, sx); x, y = 0.74 * math.cos(a), 0.74 * math.sin(a)
        fbox(FERRO, (x, y, 1.20), (0.14, 0.14, 0.40), (0, 0, a), cuts=3, amp=0.003, bev=0.010, seed=390 + i)
        fbox(ENVELH, (x, y, 1.40), (0.19, 0.19, 0.045), (0, 0, a), cuts=1, amp=0.003, bev=0.008, seed=395 + i)
        espigao(FERRO, (x, y, 1.42), (0, 0, 1), 0.11, r.uniform(0.27, 0.34), seed=400 + i)
        for sgn in (-1, 1):
            d = (sgn * -math.sin(a) * 1.0, sgn * math.cos(a) * 1.0, 0.25)
            espigao(FERRO, (x + sgn * 0.075 * -math.sin(a), y + sgn * 0.075 * math.cos(a), 1.26), d, 0.05, r.uniform(0.13, 0.19), seed=410 + i * 2 + (sgn > 0))
        for z in (1.12, 1.30):
            rebite(ENVELH, (x + 0.073 * math.cos(a), y + 0.073 * math.sin(a), z), (math.cos(a), math.sin(a), 0), 0.02, seed=420 + i)
