"""Botas v3 (rodada 2: cano fino, bico aberto em leque e curvo, calcanhar redondo, colarinho redondo, cinta inclinada).
Botas v2: pe em loft unico (sola fina com vira + cabedal), calcanhar chanfrado, bico redondo com biqueira, cano com dobras.
Rodar via regenerar_rodada7.py (antes: src/textura_botas.py com ARQ_SAIDA=<ARQ_TRAB>)"""
import os, sys, math, random
import os as _os
_AQUI = _os.path.dirname(_os.path.abspath(__file__))
_R7 = _os.path.dirname(_AQUI)
_RAIZ = _os.path.abspath(_os.path.join(_R7, "..", "..", "..", ".."))
FONTE = _os.environ.get("ARQ_FONTE_ORIG", _os.path.join(_R7, "_fonte_original"))   # GLBs/texturas pre-polida (somente leitura)
SAIDA = _os.environ.get("ARQ_SAIDA", _os.path.join(_RAIZ, "godot", "art", "models", "personagens", "arqueiro"))
TRAB = _os.environ.get("ARQ_TRAB", _os.path.join(_R7, "_trabalho", "botas"))   # intermediarios (fora do git)
_os.makedirs(TRAB, exist_ok=True)
HERE = _AQUI
sys.path.insert(0, os.path.join(HERE, "src"))
import bpy
from mathutils import Vector
import pernas_geo as G
from pernas_geo import Malha, placa, cinta, caixa, pt, interp, cl_bota, TAU, lin
from pernas_atlas import BOTAS, uvmap
OLD = os.path.join(FONTE, "Arqueiro_Botas.glb")
OUT = SAIDA
TEXBOTAS = os.path.join(TRAB, "T_Arqueiro_Botas_BC.png")
XC = 0.165; Y_HEEL = 0.160; Y_TOE = -0.255; LEN = Y_HEEL - Y_TOE
# (t, hw, zt, z0, s)  t: 0 calcanhar .. 1 bico ; s = espessura da sola
SEC = [(0.000, 0.058, 0.112, 0.000, 0.030),
       (0.012, 0.070, 0.138, 0.000, 0.030),
       (0.045, 0.080, 0.152, 0.000, 0.030),
       (0.400, 0.090, 0.136, 0.000, 0.024),   # arco do pe (cintura)
       (0.740, 0.116, 0.118, 0.002, 0.020),   # ante-pe, parte mais larga
       (0.860, 0.102, 0.104, 0.012, 0.018),
       (0.940, 0.084, 0.090, 0.024, 0.017),
       (0.985, 0.056, 0.078, 0.038, 0.016)]
SPL = 0.052   # abertura do bico para fora (m) no fim do pe
BR2 = [(0.07, 0.076, 0.080), (0.115, 0.071, 0.075), (0.15, 0.069, 0.073), (0.19, 0.073, 0.078), (0.232, 0.078, 0.083), (0.27, 0.084, 0.089)]


def rad2(z):
    return interp(BR2, z, 1), interp(BR2, z, 2)
TM = [0.0, 0.05, 0.10, 0.45, 0.78, 0.88, 0.95, 0.985]
E_WELT = 0.0065


def anel(sx, sec):
    t, hw, zt, z0, s = sec
    y = Y_HEEL - LEN * t
    e = E_WELT
    w = hw
    H = zt - s
    s0 = z0 + s
    P = [(0.78 * w, z0), (w + e, z0 + 0.35 * s), (w + e, z0 + s), (w - 0.001, s0 + 0.004),
         (0.90 * w, s0 + H * 0.47), (0.55 * w, s0 + H * 0.86), (0.16 * w, zt + 0.001)]
    L = [(-x, z) for x, z in reversed(P)]
    pts = P + L
    dx = sx * SPL * t ** 1.7
    return [(sx * (XC + x) + dx, y, z) for x, z in pts]


# tipo de cada faixa entre pontos k..k+1 (14 pontos, anel fechado; 13->0 e a base)
def tipo_faixa(k):
    if k in (0, 6 + 1 - 1 + 0) and False:
        pass
    return None


BANDA = {0: ("SOLEW", 0.04, 0.24), 1: ("SOLEW", 0.30, 0.68), 2: ("SOLEW", 0.74, 0.96)}  # lado direito, k=0..2 ; esquerdo 13-k


def pe(M, sx):
    an = [anel(sx, s) for s in SEC]
    nS, n = len(an), len(an[0])
    ids = [[M.add_v(p, "shell") for p in a] for a in an]
    # u ao redor para o cabedal (pontos 3..10 -> u 0..1 por comprimento de arco)
    arc = [0.0]
    a0 = an[3]
    for k in range(3, 10):  # 7 passos
        arc.append(arc[-1] + (Vector(a0[k + 1]) - Vector(a0[k])).length)
    arc = [x / arc[-1] for x in arc]
    ctr = lambda p: Vector((sx * XC, p.y, 0.09))
    for i in range(nS - 1):
        ta, tb = TM[i], TM[i + 1]
        for k in range(n):
            k2 = (k + 1) % n
            idx = [ids[i][k], ids[i][k2], ids[i + 1][k2], ids[i + 1][k]]
            if k == 13:     # base: planar na textura da sola
                def UV(ii, kk):
                    p = M.v[ids[ii][kk]]
                    return uvmap(BOTAS["SOLE"], (abs(p.x - sx * XC) * 4.6 + 0.12) % 1.0, 1 - SEC[ii][0] * 0.95 - 0.02)
                uvs = [UV(i, 13), UV(i, 0), UV(i + 1, 0), UV(i + 1, 13)]
            elif k <= 2 or 10 <= k <= 12:
                kk = k if k <= 2 else 12 - k
                _, v0, v1 = BANDA[kk]
                ua, ub = ta * 0.9, tb * 0.9
                uvs = [uvmap(BOTAS["SOLEW"], ua, v0), uvmap(BOTAS["SOLEW"], ua, v1), uvmap(BOTAS["SOLEW"], ub, v1), uvmap(BOTAS["SOLEW"], ub, v0)]
                if k >= 10:   # lado esquerdo: ordem do anel inverte o sentido do v
                    uvs = [uvmap(BOTAS["SOLEW"], ua, v1), uvmap(BOTAS["SOLEW"], ua, v0), uvmap(BOTAS["SOLEW"], ub, v0), uvmap(BOTAS["SOLEW"], ub, v1)]
            else:           # cabedal: k 3..10
                ua, ub = arc[k - 3], arc[k - 2]
                uvs = [uvmap(BOTAS["UPPER"], ua, ta), uvmap(BOTAS["UPPER"], ub, ta), uvmap(BOTAS["UPPER"], ub, tb), uvmap(BOTAS["UPPER"], ua, tb)]
            M.face(idx, uvs, True, ctr)
    # tampas: calcanhar (atras) e bico
    def tampa(i, frente):
        pts = an[i]
        cen = sum((Vector(p) for p in pts), Vector()) / n
        ic = M.add_v(cen + Vector((0, -0.016 if frente else 0.024, 0)), "shell")
        uv = (lambda p: uvmap(BOTAS["UPPER"], 0.5 + (p[0] - sx * (XC + SPL)) * sx * 0.9, 0.62 + (p[2] - 0.05) * 0.5)) if frente else (lambda p: uvmap(BOTAS["UPPER"], 0.20 + (p[0] - sx * XC) * sx * 0.9, 0.105 + (p[2] - 0.08) * 0.5))
        sg = -1 if frente else 1
        for k in range(n):
            k2 = (k + 1) % n
            M.face([ic, ids[i][k2], ids[i][k]], [uv(cen), uv(pts[k2]), uv(pts[k])], True,
                   lambda p, sg=sg: Vector((sx * XC, p.y - sg, p.z)))
    tampa(0, False)
    tampa(nS - 1, True)


def cinta2(M, sx, z, alt, off, tilt, nseg=14):
    """Cinta inclinada (mais baixa na frente, sobe atras) com leve ondulacao: nao e mais um anel reto."""
    aneis = []
    for dz in (-alt / 2, alt / 2):
        an = []
        for j in range(nseg):
            th = -math.pi + TAU * j / nseg
            zz = z + dz + tilt * math.sin(th + 0.35) + 0.0025 * math.sin(3 * th)
            cx, cy = cl_bota(zz)
            rx, ry = rad2(zz)
            p = pt(th, cx, cy, zz, rx + off, ry + off)
            an.append((sx * p[0], p[1], p[2]))
        aneis.append(an)
    M.grade(aneis, lambda i, j: uvmap(BOTAS["STRAP"], j / nseg, i), "strap", True, True,
            fora=lambda p: Vector((sx * cl_bota(p.z)[0], cl_bota(p.z)[1], p.z)))


def construir(seed=11):
    M = Malha()
    for sx in (1, -1):
        sr = random.Random(seed + (0 if sx > 0 else 5))
        zc = [0.075, 0.150, 0.200, 0.240, 0.262, 0.274]
        offc = [0.0, -0.002, 0.001, 0.003, 0.009, 0.006]
        nseg = 16
        aneis = []
        for z, o in zip(zc, offc):
            cx, cy = cl_bota(z)
            rx, ry = rad2(z)
            an = []
            for j in range(nseg):
                th = -math.pi + TAU * j / nseg
                g = 1 + 0.012 * math.sin(3 * th + z * 55 + sr.random() * 2)
                p = pt(th, cx, cy, z, (rx + o) * g, (ry + o) * g)
                an.append((sx * p[0], p[1], p[2]))
            aneis.append(an)
        # dobras: v da textura CANO por anel
        tv = [0.0, 0.30, 0.55, 0.92]
        fo = lambda p, sx=sx: Vector((sx * cl_bota(p.z)[0], cl_bota(p.z)[1], p.z))
        M.grade(aneis[:4], lambda i, j: uvmap(BOTAS["CANO"], j / nseg, tv[i]), "cano", True, True, fora=fo)
        cv = [0.04, 0.55, 0.95]
        M.grade(aneis[3:], lambda i, j: uvmap(BOTAS["CUFF"], j / nseg, cv[i]), "cano", True, True, fora=fo)
        pe(M, sx)
        L = lambda z0, z1, k=1.0: (lambda u: (z0 + (z1 - z0) * 0.5 * (1 - math.sin(u * math.pi)) * 0.0 + (z0 - 0.0) * 0 + 0.0, 0.0))
        def lente(zc, hh, sk=0.0):
            return lambda u: (zc - hh * math.sin(u * math.pi) ** 0.7 + sk * (u - 0.5), zc + hh * math.sin(u * math.pi) ** 0.7 + sk * (u - 0.5))
        placa(M, sx, -0.62, 0.62, 0.0, 0.0, 4, 1, 0.008, 0.010, "PLATE", "plate", BOTAS["PLATE_O"], cl_bota, rad2, forma=lente(0.172, 0.060, 0.03))
        placa(M, sx, -math.pi * 0.5 - 0.46, -math.pi * 0.5 + 0.46, 0.0, 0.0, 4, 1, 0.009, 0.010, "PLATE", "plate", BOTAS["PLATE_F"], cl_bota, rad2, forma=lente(0.178, 0.052))
        cinta2(M, sx, 0.212, 0.021, 0.011, 0.011)
    return M


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=OLD)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    for o in list(bpy.data.objects):
        if o.type == "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    for me_ in list(bpy.data.meshes): bpy.data.meshes.remove(me_)
    for m_ in list(bpy.data.materials): bpy.data.materials.remove(m_)
    for i_ in list(bpy.data.images): bpy.data.images.remove(i_)
    M = construir()
    o = M.obj("SK_Archer_Botas")
    G.aplicar_pesos(o, M, arm)
    import _comum as c
    c.material_simples(o, "M_Arqueiro_Botas", TEXBOTAS)
    o.data.materials[0].use_backface_culling = False
    por = {}
    for f in M.f:
        k = M.part[f[0][0]]; por[k] = por.get(k, 0) + len(f[0]) - 2
    print("TRIS", sum(por.values()), por)
    c.SAIDA = OUT
    c.exportar("Arqueiro_Botas.glb", [arm, o])
    c.externalizar_textura(os.path.join(OUT, "Arqueiro_Botas.glb"), "T_Arqueiro_Botas_BC.png")
    import shutil
    shutil.copyfile(TEXBOTAS, os.path.join(OUT, "T_Arqueiro_Botas_BC.png"))


main()
