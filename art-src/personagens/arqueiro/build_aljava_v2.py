"""Arqueiro_Aljava.glb versao 2: reaproveita pintura, bolsa e bandoleira de build_aljava.py e troca:
- corpo: 16 lados, ventre abaulado, base em cupula, cintas em degrau (sem aspecto de cilindro);
- flechas: sete flechas SEPARADAS (haste, penas em tres palhetas e nock de latao) em cada posicao;
  as pontas ficam dentro da aljava, so as penas aparecem na boca.
Rodar: blender -b --factory-startup -P build_aljava_v2.py   (TEMP/TMP no disco D)
Variante por raridade: ARQ_ALJ_RAR=0 (comum), 1 (incomum, cintas de metal), 2 (rara, latao e penas cinza-azuladas).
"""
import os, sys, math, random
import bpy, bmesh
from mathutils import Vector, Matrix

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import build_aljava as B  # pintura, bolsa, bandoleira, finalize e exportar

NT2 = 16                        # lados do corpo
RAR = int(os.environ.get("ARQ_ALJ_RAR", "0"))
random.seed(7)


def rad(z):
    """raio (x, y) do corpo em z: base mais estreita, ventre abaulado, boca um pouco mais larga."""
    t = (z - B.ZB) / (B.ZT - B.ZB)
    t = min(max(t, 0.0), 1.0)
    bulge = 1.0 + 0.13 * math.sin(math.pi * (0.20 + 0.65 * t)) ** 1.6
    return (0.046 + 0.018 * t) * bulge, (0.040 + 0.014 * t) * bulge


def ring(z, rx, ry, cx=0.0, cy=0.0):
    return [Vector((cx + math.cos(2 * math.pi * k / NT2) * rx, cy + math.sin(2 * math.pi * k / NT2) * ry, z))
            for k in range(NT2)]


def body(M):
    zs = [B.ZB + (B.ZT - B.ZB) * i / 10 for i in range(11)]
    M.ring_tube([ring(z, *rad(z)) for z in zs], "A", smooth=True, cap_bot=False, u_scale=1.0)
    # fundo em cupula: tres aneis que fecham a base com couro escuro
    z0 = B.ZB
    rx, ry = rad(z0)
    M.ring_tube([ring(z0, rx, ry), ring(z0 - 0.012, rx * 0.80, ry * 0.80), ring(z0 - 0.020, rx * 0.42, ry * 0.42)],
                "B", smooth=True, cap_top=False, cap_bot=True)
    # forro escuro da boca (um pouco abaixo da borda)
    zi = B.ZT - 0.010
    M.poly(list(reversed(ring(zi, *[r - 0.005 for r in rad(zi)]))), "B", 0.2, 0.2)

    def band(za, zb, grow, reg):
        rr = []
        for z, g in ((za, 0.0), (za + 0.003, grow), (zb - 0.003, grow), (zb, 0.0)):
            rx, ry = rad(z)
            rr.append(ring(z, rx + g, ry + g))
        M.ring_tube(rr, reg, smooth=False, u_scale=0.9)
    # borda da boca (rolo), cinta do meio e cinta baixa
    band(B.ZT - 0.040, B.ZT + 0.006, 0.0085, "B")
    band(-0.030, -0.005, 0.0062, "B")
    band(B.ZB + 0.030, B.ZB + 0.052, 0.0062, "B")
    if RAR >= 1:  # cintas de latao na versao incomum e rara
        band(B.ZB + 0.060, B.ZB + 0.066, 0.0075, "Dl")
        band(B.ZT - 0.060, B.ZT - 0.054, 0.0075, "Dl")


def feather_colors():
    if RAR == 2:
        return ["Cm", "Cg", "Cm", "Cg", "Cm", "Cg", "Cm"]
    return ["Cg", "Cm", "Cg", "Cg", "Cm", "Cg", "Cm"]


def arrows(M):
    """Sete flechas separadas. Haste, tres penas e nock; a ponta fica dentro do tubo."""
    spec = [  # (angulo em graus ao redor do eixo, inclinacao para fora, altura acima da boca, comprimento)
        (-78, 0.20, 0.215, 0.50), (-20, 0.16, 0.255, 0.52), (38, 0.22, 0.200, 0.49), (92, 0.14, 0.270, 0.53),
        (150, 0.20, 0.225, 0.50), (206, 0.17, 0.245, 0.51), (262, 0.13, 0.265, 0.52)]
    FS = 1.7  # escala das penas (legiveis a distancia 3/4)
    cols = feather_colors()
    for i, (deg, lean, h, L) in enumerate(spec):
        a = math.radians(deg + random.uniform(-4, 4))
        ca, sa = math.cos(a), math.sin(a)
        rx, ry = rad(B.ZT)
        base_r = 0.030
        P_top = Vector((ca * (rx * 0.62 + lean * h * 0.25), sa * (ry * 0.62 + lean * h * 0.25), B.ZT + h))
        d = Vector((ca * lean, sa * lean, 1.0)).normalized()
        P_bot = P_top - d * L
        # haste fina (seis lados) entre a ponta enterrada e a boca
        M.cone(P_bot, P_top - d * 0.004, 0.0021, 0.0021, 6, "Dw", cap0=True, cap1=True)
        # nock de latao no topo
        M.cone(P_top - d * 0.004, P_top, 0.0030, 0.0022, 6, "Dl", cap0=True, cap1=True)
        # penas: tres palhetas em 120 graus, da nock para baixo
        u = d.cross(Vector((0, 0, 1))).normalized()
        if u.length < 0.5:
            u = d.cross(Vector((1, 0, 0))).normalized()
        n2 = d.cross(u).normalized()
        reg = cols[i]
        for k in range(3):
            phi = math.radians(120 * k + 30 + i * 17)
            s = u * math.cos(phi) + n2 * math.sin(phi)
            q0 = P_top - d * 0.004
            pts = [q0,
                   q0 - d * 0.012 * FS + s * 0.0075 * FS,
                   q0 - d * 0.050 * FS + s * 0.0060 * FS,
                   q0 - d * 0.072 * FS + s * 0.0010 * FS,
                   q0 - d * 0.066 * FS + s * 0.0000]
            # uma palheta com dupla face (sem culling no material)
            M.poly(pts, reg, 0.5, 0.5)
            M.poly(list(reversed(pts)), reg, 0.5, 0.5)
        # fio de amarra da pena, pequeno anel de latao
        M.cone(P_top - d * 0.030, P_top - d * 0.026, 0.0045, 0.0045, 6, "Dl", cap0=True, cap1=True)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    img_bc, img_n = B.make_images()
    mat = B.A.mk_mat("M_Arqueiro_Aljava", img_bc, img_n, rough=0.78)
    mat.use_backface_culling = False
    M = B.Mesh()
    body(M)
    B.build_pouch(M)
    B.build_strap(M)
    arrows(M)
    return B.finalize(M, mat)


if __name__ == "__main__":
    ob = build()
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("TRIS", tris, "dim", tuple(round(d, 3) for d in ob.dimensions), "RAR", RAR)
    B.exportar(ob)
