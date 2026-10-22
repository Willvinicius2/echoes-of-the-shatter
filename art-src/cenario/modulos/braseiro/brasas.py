"""Leito de brasas: cinza irregular no fundo, carvão rachado com veios incandescentes e gravetos carbonizados."""
from ._lib import *

def build():
    r = rng(601)
    # cinza: disco subdividido e ondulado
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=28, radius1=0.60, radius2=0.60, depth=0.06)
    subdiv(bm, 2)
    for v in bm.verts:
        if v.co.z > 0: v.co.z += 0.02 * math.sin(v.co.x * 11) * math.cos(v.co.y * 9) + r.uniform(-.008, .008)
    new("cinza", bm, (0, 0, 1.19), (0, 0, 0), CINZA, 0, flat=False)
    # carvão: poliedros irregulares com variação de tamanho
    for i in range(14):
        rr = 0.33 * math.sqrt(r.random()); a = r.random() * 2 * math.pi
        sz = r.uniform(0.07, 0.15)
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=sz)
        for v in bm.verts:
            f = 1 + r.uniform(-0.28, 0.28); v.co *= f; v.co.z *= 0.65
        new("carvao", bm, (rr * math.cos(a), rr * math.sin(a), 1.22 + r.uniform(0, 0.07)), (r.uniform(0, 3), r.uniform(0, 3), r.uniform(0, 3)), BRASA, 0.01, seg=1, ang=40)
    # gravetos carbonizados
    for i in range(4):
        a = r.random() * math.pi
        fcyl(FUL, (0.12 * r.uniform(-1, 1), 0.12 * r.uniform(-1, 1), 1.24 + 0.02 * i), 0.022, 0.45, rot=(math.pi / 2 + r.uniform(-.15, .15), r.uniform(-.25, .25), a), sides=7, cuts=3, amp=0.006, bev=0.004, seed=610 + i)
