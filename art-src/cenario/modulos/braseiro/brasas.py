"""Leito de brasas: cinza clara com pó nas bordas, pilha volumétrica de carvão anguloso rachado (frio nas bordas, núcleo
incandescente no centro), brasas miúdas e gravetos carbonizados. Nada de seixos redondos: blocos facetados e jitterados."""
from ._lib import *

def pedaco(r, tam, loc, mat, seed):
    """Bloco angular de carvão: cubo subdividido com deslocamento forte, achatado e girado, bevel só nas quinas vivas."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    sx, sy, sz = tam * r.uniform(0.8, 1.2), tam * r.uniform(0.8, 1.2), tam * r.uniform(0.6, 1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    for v in bm.verts:
        k = 1 + r.uniform(-0.32, 0.32)
        v.co = Vector((v.co.x * sx * k + r.uniform(-.2, .2) * tam * 0.4, v.co.y * sy * k + r.uniform(-.2, .2) * tam * 0.4, v.co.z * sz * k))
    return new("carvao", bm, loc, (r.uniform(-.5, .5), r.uniform(-.5, .5), r.uniform(0, 6.28)), mat, 0.012, seg=1, ang=35)

def build():
    r = rng(601)
    # cinza: concha côncava que acompanha o fundo da bacia (metal escurecido por baixo), mais alta no aro
    def sup(d): return 0.88 + 0.12 * (min(d, 0.6) / 0.6) ** 2
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=36, radius1=0.62, radius2=0.62, depth=0.06)
    subdiv(bm, 3)
    for v in bm.verts:
        d = math.hypot(v.co.x, v.co.y)
        v.co.z = sup(d) + (0.0 if v.co.z > 0 else -0.04) + (r.uniform(-.006, .006) + 0.012 * math.sin(v.co.x * 13) * math.cos(v.co.y * 11) if v.co.z > 0 else 0)
    new("cinza", bm, (0, 0, 0), (0, 0, 0), CINZA, 0, flat=False)
    # carvão em camadas sobre a concha: cobre quase toda a área; núcleo quente no centro, frio no aro
    camadas = [(0.50, 52, 0.09, 0.05, 0.03), (0.40, 40, 0.095, 0.11, 0.04), (0.30, 28, 0.10, 0.17, 0.04), (0.20, 16, 0.095, 0.23, 0.04), (0.09, 6, 0.09, 0.29, 0.03)]
    for raio, qtd, tam, off, dz in camadas:
        for i in range(qtd):
            rr = raio * math.sqrt(r.random()); a = r.random() * 2 * math.pi
            d = rr
            m = BRASA_NUCLEO if d < 0.16 and r.random() < 0.7 else (BRASA if d < 0.38 else (BRASA_FRIA if r.random() < 0.8 else BRASA))
            pedaco(r, tam * r.uniform(0.6, 1.25), (rr * math.cos(a), rr * math.sin(a), sup(d) + off + r.uniform(-dz, dz) * 0.5), m, 700 + i)
    # brasas miúdas, vivas
    for i in range(60):
        rr = 0.56 * math.sqrt(r.random()); a = r.random() * 2 * math.pi
        pedaco(r, r.uniform(0.022, 0.05), (rr * math.cos(a), rr * math.sin(a), sup(rr) + 0.02 + 0.2 * max(0, 1 - rr / 0.4) * r.random()), BRASA_NUCLEO if rr < 0.3 else BRASA, 800 + i)
    # gravetos carbonizados cruzando o leito
    for i in range(5):
        a = r.random() * math.pi; c = (0.14 * r.uniform(-1, 1), 0.14 * r.uniform(-1, 1), sup(0.1) + 0.2 + 0.03 * i)
        fcyl(FUL, c, 0.02 + 0.006 * r.random(), r.uniform(0.35, 0.5), rot=(math.pi / 2 + r.uniform(-.2, .2), r.uniform(-.3, .3), a), sides=7, cuts=3, amp=0.007, bev=0.004, seed=610 + i)
