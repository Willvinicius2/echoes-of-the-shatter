"""Correntes sob a bacia: elos ovais alternados, desgaste desigual, uma corrente quebrada e placas de ancoragem."""
from ._lib import *

def elo(m, loc, ang, giro, escala, seed):
    r = rng(seed)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.05 * escala, minor_radius=0.021 * escala, major_segments=16, minor_segments=8, location=loc,
                                     rotation=(math.pi / 2, 0, ang + giro))
    o = bpy.context.object; o.scale = (1, 1.55, 1); bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for v in o.data.vertices: v.co += Vector((r.uniform(-.002, .002), r.uniform(-.002, .002), r.uniform(-.002, .002)))
    return add(o, r.choice((ENVELH, ENVELH, FERRO)), PARTE[0])

def build():
    r = rng(501)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        n = 5 if k != 2 else 3                                           # a corrente de trás está quebrada
        base = (0.34 * math.cos(a), 0.34 * math.sin(a))
        fbox(ENVELH, (base[0], base[1], 0.955), (0.07, 0.07, 0.035), (0, 0, a), cuts=1, amp=0.002, bev=0.006, seed=510 + k)   # placa
        rebite(FERRO, (base[0], base[1], 0.936), (0, 0, -1), 0.016, seed=515 + k)
        z = 0.925
        for j in range(n):
            z -= 0.078 * r.uniform(0.92, 1.05)
            elo(None, (base[0] + r.uniform(-.004, .004), base[1] + r.uniform(-.004, .004), z), a, (j % 2) * math.pi / 2 + r.uniform(-.08, .08), r.uniform(0.9, 1.1), 520 + k * 10 + j)
        if k == 2:                                                       # último elo aberto, caído
            elo(None, (base[0] * 1.15, base[1] * 1.15, 0.55), a, 0.6, 1.0, 560)
