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
    # cinza: disco irregular, mais alto no fundo da bacia
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=32, radius1=0.52, radius2=0.52, depth=0.07)
    subdiv(bm, 2)
    for v in bm.verts:
        if v.co.z > 0: v.co.z += 0.025 * math.sin(v.co.x * 11) * math.cos(v.co.y * 9) + r.uniform(-.012, .012)
    new("cinza", bm, (0, 0, 1.19), (0, 0, 0), CINZA, 0, flat=False)
    # carvão em camadas: cada camada mais alta e mais estreita; núcleo quente no centro, frio no aro
    camadas = [(0.40, 44, 0.095, 1.23, 0.03), (0.32, 34, 0.10, 1.29, 0.04), (0.23, 24, 0.10, 1.35, 0.04), (0.14, 12, 0.095, 1.41, 0.04), (0.06, 4, 0.09, 1.46, 0.03)]
    for raio, qtd, tam, z0, dz in camadas:
        for i in range(qtd):
            rr = raio * math.sqrt(r.random()); a = r.random() * 2 * math.pi
            d = math.hypot(rr * math.cos(a), rr * math.sin(a))
            m = BRASA_NUCLEO if d < 0.16 and r.random() < 0.7 else (BRASA if d < 0.38 else (BRASA_FRIA if r.random() < 0.8 else BRASA))
            z = z0 + r.uniform(-dz, dz) - 0.12 * (d / 0.55) ** 2           # as bordas caem em direção à parede
            pedaco(r, tam * r.uniform(0.6, 1.25), (rr * math.cos(a), rr * math.sin(a), z), m, 700 + i)
    # brasas miúdas, vivas
    for i in range(34):
        rr = 0.46 * math.sqrt(r.random()); a = r.random() * 2 * math.pi
        pedaco(r, r.uniform(0.025, 0.05), (rr * math.cos(a), rr * math.sin(a), 1.25 + 0.18 * (1 - rr / 0.5) + r.uniform(0, 0.08)), BRASA_NUCLEO if rr < 0.3 else BRASA, 800 + i)
    # gravetos carbonizados cruzando o leito
    for i in range(5):
        a = r.random() * math.pi; c = (0.14 * r.uniform(-1, 1), 0.14 * r.uniform(-1, 1), 1.27 + 0.03 * i)
        fcyl(FUL, c, 0.02 + 0.006 * r.random(), r.uniform(0.35, 0.5), rot=(math.pi / 2 + r.uniform(-.2, .2), r.uniform(-.3, .3), a), sides=7, cuts=3, amp=0.007, bev=0.004, seed=610 + i)
