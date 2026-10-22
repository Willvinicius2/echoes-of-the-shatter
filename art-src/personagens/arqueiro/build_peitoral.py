"""Exporta Arqueiro_Peitoral.glb: gibao verde e couro, correias cruzadas, cinto com bolsas e fivela, fecho de osso, CAPA DE
PENAS longa nas costas (fileiras crescendo para baixo, ate o joelho), mantel de penas no pescoco, ASAS de penas nos ombros,
ombreiras e braceletes de osso com espessura e chanfro. Tudo procedural (semente fixa), 1 malha skinada nos MESMOS 27 ossos do
Rig_Humanoid_Chibi (sem animacao), 1 material com textura propria T_Arqueiro_Peitoral_BC.png (python peitoral_textura.py).
Rodar: python peitoral_textura.py ; blender -b -P build_peitoral.py
Eixos Blender (Z-up): rosto -Y, costas +Y. O corpo ja e chibi (1,5 m): a malha e modelada direto no espaco chibi, depois que
proporcao.aplicar(arm, []) deu aos ossos o repouso novo (mesma funcao dos outros build_*.py; as malhas daqui nao precisam de
deformacao porque ja nascem no espaco chibi).
"""
import os, sys, math, random
import bpy, bmesh
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c

TEX = os.path.join(c.SAIDA, "T_Arqueiro_Peitoral_BC.png")
RNG = random.Random(20261022)
CY = 0.07  # eixo Y do tronco (ossos)

bm = None
UVL = None
GRUPOS = ["Hips", "Spine", "Chest", "Neck", "LeftShoulder", "RightShoulder", "LeftUpperArm", "RightUpperArm",
          "LeftLowerArm", "RightLowerArm"]
LU = LV = DL = None


# ---------------------------------------------------------------- util
def interp(tab, x):
    if x <= tab[0][0]:
        return tab[0][1]
    for (a, va), (b, vb) in zip(tab, tab[1:]):
        if x <= b:
            return va + (vb - va) * (x - a) / (b - a)
    return tab[-1][1]


def lerp(a, b, t):
    return a + (b - a) * t


def rodar(v, eixo, ang):
    return Matrix.Rotation(ang, 3, eixo.normalized()) @ v


# slots do atlas
def uv_pena(cel, u, v):
    """u,v em 0..1 dentro da celula da pena (v=0 raiz, v=1 ponta)."""
    return ((cel + 0.04 + 0.92 * u) / 8.0, 0.5 + 0.01 + 0.48 * v)


def uv_amostra(k, a, b):
    """k: 0 tecido, 1 couro, 2 osso, 3 metal; a,b em 0..1 dentro da amostra."""
    a = min(max(a, 0.0), 1.0); b = min(max(b, 0.0), 1.0)
    return ((k + 0.02 + 0.96 * a) / 4.0, 0.01 + 0.48 * b)


def W_z(z):
    tab = [(0.42, {"Hips": 1.0}), (0.54, {"Hips": 0.5, "Spine": 0.5}), (0.64, {"Spine": 1.0}),
           (0.78, {"Spine": 0.5, "Chest": 0.5}), (0.90, {"Chest": 1.0})]
    if z <= tab[0][0]:
        return dict(tab[0][1])
    if z >= tab[-1][0]:
        return dict(tab[-1][1])
    for (a, wa), (b, wb) in zip(tab, tab[1:]):
        if z <= b:
            t = (z - a) / (b - a)
            r = {}
            for k in set(wa) | set(wb):
                r[k] = wa.get(k, 0) * (1 - t) + wb.get(k, 0) * t
            return r


def vert(p, uv, w=None):
    v = bm.verts.new(p)
    v[LU], v[LV] = uv
    poe_peso(v, w if w is not None else W_z(p.z))
    return v


def poe_peso(v, w):
    for k in list(v[DL].keys()):
        del v[DL][k]
    tot = sum(w.values())
    for k, x in w.items():
        if x > 1e-4:
            v[DL][GRUPOS.index(k)] = x / tot


def face(vs, out=None):
    """Cria a face; se `out` (direcao desejada da normal), vira o enrolamento quando preciso."""
    try:
        f = bm.faces.new(vs)
    except ValueError:
        return None
    f.normal_update()
    if out is not None and f.normal.dot(out) < 0:
        f.normal_flip()
    for l in f.loops:
        l[UVL].uv = (l.vert[LU], l.vert[LV])
    return f


# ---------------------------------------------------------------- pena
def pena(raiz, d, n, L, W, cel, curl=0.08, tip=0.0, w=None, rib=0.007):
    """Lamina afilada de 10 tris: 3 aneis (esq, nervura elevada, dir) + ponta. d desce pela pena, n e a normal da superficie."""
    d = d.normalized()
    n = (n - d * n.dot(d)).normalized()
    side = d.cross(n).normalized()
    perfil = [(0.0, 0.46), (0.34, 0.95), (0.68, 0.56)]
    aneis = []
    for t, hw in perfil:
        p = raiz + d * (L * t) + n * (curl * L * t * t)
        h = W * 0.5 * hw
        q = rib * (1.0 - 0.3 * t)
        a = vert(p - side * h - n * 0.002, uv_pena(cel, 0.5 - 0.5 * hw, t), w)
        b = vert(p + n * q, uv_pena(cel, 0.5, t), w)
        cc = vert(p + side * h - n * 0.002, uv_pena(cel, 0.5 + 0.5 * hw, t), w)
        aneis.append((a, b, cc))
    pt = raiz + d * L + n * (curl * L) + side * (tip * W)
    ap = vert(pt, uv_pena(cel, 0.5 + tip, 1.0), w)
    for (a0, b0, c0), (a1, b1, c1) in zip(aneis, aneis[1:]):
        face([a0, b0, b1, a1], n)
        face([b0, c0, c1, b1], n)
    a, b, cc = aneis[-1]
    face([a, b, ap], n)
    face([b, cc, ap], n)


# ---------------------------------------------------------------- capa de costas
Y0 = [(0.25, 0.380), (0.45, 0.360), (0.60, 0.335), (0.72, 0.300), (0.85, 0.255), (1.0, 0.215)]
HWT = [(0.25, 0.36), (0.50, 0.32), (0.70, 0.275), (0.85, 0.235), (1.0, 0.19)]
BEND = 0.085


def cape_pt(u, z):
    return Vector((interp(HWT, z) * u, interp(Y0, z) - BEND * u * u, z))


def cape_frame(u, z):
    pz = (cape_pt(u, z + 0.01) - cape_pt(u, z - 0.01)).normalized()
    pu = (cape_pt(u + 0.02, z) - cape_pt(u - 0.02, z)).normalized()
    n = pu.cross(pz)
    if n.y < 0:
        n = -n
    return -pz, n.normalized()


# (z da raiz, comprimento, largura) - penas curtas no ombro, longas na barra
FILEIRAS = [(0.930, 0.095, 0.042), (0.868, 0.118, 0.049), (0.802, 0.140, 0.056), (0.726, 0.160, 0.063),
            (0.643, 0.178, 0.070), (0.555, 0.195, 0.077), (0.465, 0.205, 0.084), (0.452, 0.185, 0.052)]
CEL_FILEIRA = [[0, 1, 2], [0, 1, 3, 2], [1, 0, 3, 2, 5], [0, 1, 4, 2, 2, 5], [1, 2, 0, 4, 0, 5, 6], [0, 1, 2, 4, 3, 6, 5, 0], [1, 0, 3, 4, 6, 2, 7, 1], [2, 0, 3, 1, 4, 6, 5, 7]]


def capa_penas():
    for k, (zr, L, Wf) in enumerate(FILEIRAS):
        hw = interp(HWT, zr)
        n = int(round(2 * hw * 1.25 / (Wf * (0.88 if k < 7 else 1.5))))
        for j in range(n):
            u = -1 + (j + 0.5 + (0.5 if k % 2 else 0.0)) * 2.0 / (n + (0.5 if k % 2 else 0.0))
            u = max(-1.0, min(1.0, u + RNG.uniform(-0.35, 0.35) / n))
            z = zr + RNG.uniform(-0.012, 0.012)
            d, nn = cape_frame(u, z)
            alpha = math.radians(RNG.uniform(7, 14) + 2.2 * k)
            d2 = (d * math.cos(alpha) + nn * math.sin(alpha)).normalized()
            d2 = rodar(d2, nn, math.radians(u * 16 + RNG.uniform(-9, 9)))
            Lf = L * RNG.uniform(0.84, 1.16)
            if k >= 4 and RNG.random() < 0.30:
                Lf *= 1.22          # franja: algumas penas bem mais longas e finas
            if k >= 6:
                Lf *= RNG.choice([0.72, 0.95, 1.0, 1.2])   # barra irregular: pontas longas e curtas alternadas
            Wf2 = Wf * RNG.uniform(0.88, 1.10) * (0.85 if Lf > L * 1.2 else 1.0)
            cel = RNG.choice(CEL_FILEIRA[k])
            root = cape_pt(u, z) + nn * (0.012 - 0.0022 * k)
            pena(root, d2, nn, Lf, Wf2, cel, curl=RNG.uniform(0.05, 0.11), tip=RNG.uniform(-0.18, 0.18))


def capa_forro():
    """Forro verde-escuro liso sob as penas: fecha os vaos; barra em dentes (coberta pelas penas)."""
    zs = [0.915, 0.86, 0.80, 0.70, 0.60, 0.52, 0.46]
    us = [-0.88 + 1.76 * i / 8 for i in range(9)]
    g = []
    for zi, z in enumerate(zs):
        lin = []
        for ui, u in enumerate(us):
            d, nn = cape_frame(u, z)
            zz = z - (0.03 if (zi == len(zs) - 1 and ui % 2) else 0.0)
            p = cape_pt(u, zz) - nn * 0.022
            lin.append(vert(p, uv_amostra(0, (ui / 8) * 0.9 + 0.05, (zi / 6) * 0.9 + 0.05)))
        g.append(lin)
    for zi in range(len(zs) - 1):
        for ui in range(8):
            face([g[zi][ui], g[zi][ui + 1], g[zi + 1][ui + 1], g[zi + 1][ui]], Vector((0, 1, 0)))


# ---------------------------------------------------------------- mantel (colar de penas na frente/ombros)
def mantel():
    rows = [(0.945, 0.088, 0.046, 12, [0, 1, 3, 2]), (0.895, 0.112, 0.056, 13, [1, 0, 2, 5, 4])]
    for k, (zr, L, Wf, n, cels) in enumerate(rows):
        for j in range(n):
            ph = math.radians(-125 + 250 * (j + 0.5 * (k % 2)) / n)   # 0 = frente; so a metade da frente e dos lados
            rx = 0.170 + 1.0 * (0.985 - zr) + 0.01
            ry = 0.165 + 0.50 * (0.985 - zr) + 0.01
            base = Vector((math.sin(ph) * rx, CY - math.cos(ph) * ry, zr + RNG.uniform(-0.008, 0.008)))
            rad = Vector((math.sin(ph) / rx, -math.cos(ph) / ry, 0.0)).normalized()
            nn = (rad + Vector((0, 0, 0.55))).normalized()
            d = (-Vector((0, 0, 1)) * 0.9 + rad * 0.45)
            d = d.normalized()
            alpha = math.radians(RNG.uniform(6, 12))
            d2 = (d * math.cos(alpha) + nn * math.sin(alpha)).normalized()
            w = {"Chest": 0.85, "Neck": 0.15}
            pena(base, d2, nn, L * RNG.uniform(0.85, 1.15), Wf * RNG.uniform(0.9, 1.1), RNG.choice(cels), curl=0.08,
                 tip=RNG.uniform(-0.15, 0.15), w=w)


# ---------------------------------------------------------------- asas nos ombros
def asa(side):
    cs = Vector((side * 0.172, CY, 0.862))
    sh = "LeftShoulder" if side > 0 else "RightShoulder"
    ua = "LeftUpperArm" if side > 0 else "RightUpperArm"
    rows = [(math.radians(48), 0.118, 0.140, 0.062, 6, {sh: 0.65, "Chest": 0.35}, [0, 1, 3]),
            (math.radians(68), 0.122, 0.180, 0.072, 6, {sh: 0.45, ua: 0.55}, [1, 0, 2, 4, 5]),
            (math.radians(88), 0.128, 0.225, 0.082, 6, {ua: 0.8, sh: 0.2}, [0, 1, 4, 5, 6, 3]),
            (math.radians(104), 0.130, 0.265, 0.088, 5, {ua: 1.0}, [5, 6, 1, 7, 4])]
    ex, ey, ez = Vector((side, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    for k, (phi, R, L, Wf, n, w, cels) in enumerate(rows):
        for j in range(n):
            psi = math.radians(-112 + 224 * (j + 0.5 * (k % 2) * 0.8) / n)
            dire = ex * math.cos(psi) + ey * math.sin(psi)
            rad = dire * math.sin(phi) + ez * math.cos(phi)
            root = cs + rad * R
            td = dire * math.cos(phi) - ez * math.sin(phi)      # meridiano: desce para fora
            alpha = math.radians(RNG.uniform(8, 16))
            d2 = (td * math.cos(alpha) + rad * math.sin(alpha)).normalized()
            d2 = rodar(d2, rad, math.radians(RNG.uniform(-9, 9)))
            pena(root, d2, rad, L * RNG.uniform(0.86, 1.14), Wf * RNG.uniform(0.9, 1.1), RNG.choice(cels),
                 curl=RNG.uniform(0.06, 0.12), tip=RNG.uniform(-0.2, 0.2), w=w)


# ---------------------------------------------------------------- gibao, saia, cinto
ANEIS = [(0.58, 0.228, 0.222, 0.222), (0.64, 0.200, 0.185, 0.185), (0.72, 0.165, 0.152, 0.158), (0.82, 0.186, 0.150, 0.150),
         (0.91, 0.146, 0.116, 0.122), (0.965, 0.112, 0.100, 0.100)]


def ell(z, ph, off=0.0):
    rx = interp([(a[0], a[1]) for a in ANEIS], z)
    ryf = interp([(a[0], a[2]) for a in ANEIS], z)
    ryb = interp([(a[0], a[3]) for a in ANEIS], z)
    ry = ryf if math.cos(ph) > 0 else ryb
    p = Vector((math.sin(ph) * (rx + off), CY - math.cos(ph) * (ry + off), z))
    nn = Vector((math.sin(ph) / rx, -math.cos(ph) / ry, 0)).normalized()
    return p, nn


def gibao():
    n = 14
    g = []
    for ri, (z, rx, ryf, ryb) in enumerate(ANEIS):
        lin = []
        for j in range(n + 1):
            ph = 2 * math.pi * j / n
            p, nn = ell(z, ph, 0.0)
            lin.append(vert(p, uv_amostra(0, j / n, ri / (len(ANEIS) - 1))))
        g.append(lin)
    for ri in range(len(ANEIS) - 1):
        for j in range(n):
            q = [g[ri][j], g[ri][j + 1], g[ri + 1][j + 1], g[ri + 1][j]]
            f = face(q)
            if f:
                cen = f.calc_center_median()
                if f.normal.dot(Vector((cen.x, cen.y - CY, 0))) < 0:
                    f.normal_flip()
                    for l in f.loops:
                        l[UVL].uv = (l.vert[LU], l.vert[LV])
    # saia da frente: panos pontiagudos, barra rasgada (verde-escuro)
    cols = 9
    z0, z1 = 0.585, 0.385
    for j in range(cols):
        ph0 = math.radians(-78 + 156 * j / cols)
        ph1 = math.radians(-78 + 156 * (j + 1) / cols)
        pm = (ph0 + ph1) / 2
        def P(ph, z, ex=0.0):
            k = (z0 - z) / (z0 - z1)
            rx = 0.205 + 0.05 * k + ex
            ry = 0.205 + 0.04 * k + ex
            return Vector((math.sin(ph) * rx, CY - math.cos(ph) * ry, z))
        zb = z1 - RNG.uniform(0.0, 0.05) + (0.03 if j % 2 else 0.0)
        zmid = lerp(z0, zb, 0.5)
        a = [vert(P(ph0, z0), uv_amostra(0, j / cols, 0.95)), vert(P(ph1, z0), uv_amostra(0, (j + 1) / cols, 0.95))]
        m = [vert(P(ph0, zmid, 0.012), uv_amostra(0, j / cols, 0.5)), vert(P(ph1, zmid, 0.012), uv_amostra(0, (j + 1) / cols, 0.5))]
        tip = vert(P(pm, zb, 0.022) + Vector((0, 0, 0)), uv_amostra(0, (j + 0.5) / cols, 0.05))
        out = Vector((math.sin(pm), -math.cos(pm), 0))
        wz = {"Hips": 1.0}
        for v in a + m + [tip]:
            poe_peso(v, wz)
        face([a[0], a[1], m[1], m[0]], out)
        face([m[0], m[1], tip], out)


def tira(pontos, larg, off, k_uv=1, w=None, seg_w=None):
    """Fita de couro seguindo uma lista de (z, fase). Fica sobre o gibao (+off). Retorna os pontos centrais."""
    L = []
    for i, (z, ph) in enumerate(pontos):
        p, nn = ell(z, ph, off)
        L.append((p, nn))
    verts = []
    for i, (p, nn) in enumerate(L):
        t = (L[min(i + 1, len(L) - 1)][0] - L[max(i - 1, 0)][0]).normalized()
        sd = t.cross(nn).normalized()
        b = i / (len(L) - 1)
        verts.append((vert(p - sd * larg / 2, uv_amostra(k_uv, 0.05, b), w), vert(p + sd * larg / 2, uv_amostra(k_uv, 0.95, b), w), nn))
    for (a0, b0, n0), (a1, b1, n1) in zip(verts, verts[1:]):
        face([a0, b0, b1, a1], n0)


def caixa(centro, ex, ey, ez, tam, k_uv, w, chanfro=0.0):
    """Caixa (bolsa/fivela) com 6 faces; ex,ey,ez eixos ortonormais; tam=(sx,sy,sz) meias medidas."""
    sx, sy, sz = tam
    vs = {}
    for a in (-1, 1):
        for b in (-1, 1):
            for cc in (-1, 1):
                p = centro + ex * (a * sx) + ey * (b * sy) + ez * (cc * sz)
                vs[(a, b, cc)] = vert(p, uv_amostra(k_uv, (a + 1) / 2 * 0.8 + 0.1, (b + 1) / 2 * 0.8 + 0.1), w)
    for (axis, sgn, nrm) in ((0, 1, ex), (0, -1, -ex), (1, 1, ey), (1, -1, -ey), (2, 1, ez), (2, -1, -ez)):
        keys = [k for k in vs if k[axis] == sgn]
        if axis == 0:
            order = [(sgn, -1, -1), (sgn, 1, -1), (sgn, 1, 1), (sgn, -1, 1)]
        elif axis == 1:
            order = [(-1, sgn, -1), (1, sgn, -1), (1, sgn, 1), (-1, sgn, 1)]
        else:
            order = [(-1, -1, sgn), (1, -1, sgn), (1, 1, sgn), (-1, 1, sgn)]
        face([vs[o] for o in order], nrm)


def bolsa(z, ph, tam, w):
    p, nn = ell(z, ph, 0.055)
    up = Vector((0, 0, 1))
    sd = up.cross(nn).normalized()
    # corpo + aba + trava de osso
    caixa(p, sd, nn, up, (tam[0], 0.022, tam[1]), 1, w)
    caixa(p + nn * 0.020 + up * (tam[1] * 0.35), sd, nn, up, (tam[0] * 1.02, 0.006, tam[1] * 0.62), 1, w)
    caixa(p + nn * 0.029 + up * (tam[1] * 0.05), sd, nn, up, (0.009, 0.005, 0.014), 2, w)


def cinto():
    n = 18
    w = {"Spine": 0.5, "Hips": 0.5}
    aneis = []
    for j in range(n + 1):
        ph = 2 * math.pi * j / n
        rx, ry = 0.240, 0.240
        pts = []
        for zz, v in ((0.620, 0.95), (0.568, 0.05)):
            p = Vector((math.sin(ph) * rx, CY - math.cos(ph) * ry, zz))
            pts.append(vert(p, uv_amostra(1, j / n, v), w))
        aneis.append(pts)
    for j in range(n):
        f = face([aneis[j][0], aneis[j + 1][0], aneis[j + 1][1], aneis[j][1]])
        cen = f.calc_center_median()
        if f.normal.dot(Vector((cen.x, cen.y - CY, 0))) < 0:
            f.normal_flip()
            for l in f.loops:
                l[UVL].uv = (l.vert[LU], l.vert[LV])
    # fivela de metal na frente e dois reforcos
    cf = Vector((0, CY - 0.252, 0.594))
    ex, ey, ez = Vector((1, 0, 0)), Vector((0, -1, 0)), Vector((0, 0, 1))
    caixa(cf, ex, ey, ez, (0.030, 0.009, 0.028), 3, w)
    caixa(cf + ey * 0.007, ex, ey, ez, (0.019, 0.006, 0.017), 2, w)
    # bolsas nas laterais e atras
    for ph, tam in ((math.radians(42), (0.030, 0.034)), (math.radians(-40), (0.026, 0.030)), (math.radians(150), (0.032, 0.034))):
        bolsa(0.585, ph, tam, w)
    # penas pendentes no quadril (amuleto): marfim com ponta dourada
    for ph, cel in ((math.radians(-35), 6), (math.radians(-44), 5)):
        p, nn = ell(0.58, ph, 0.058)
        pena(p, Vector((0, 0, -1)) + nn * 0.12, nn, 0.150, 0.050, cel, curl=0.05, tip=0.05, w=w)


def correias():
    # bandoleira: do ombro direito (do personagem, -X) ate o quadril esquerdo, sobre o gibao e sob a gola
    pts = [(0.935 - 0.0575 * i, math.radians(-52 + 12 * i)) for i in range(0, 6)]
    pts = [(z, ph) for z, ph in pts]
    pts = [(0.93 - (0.93 - 0.60) * i / 7, math.radians(-62 + (62 + 36) * i / 7)) for i in range(8)]
    tira(pts, 0.036, 0.011, 1, None)
    pts2 = [(0.93 - (0.93 - 0.60) * i / 7, math.radians(62 - (62 + 36) * i / 7)) for i in range(8)]
    tira(pts2, 0.030, 0.016, 1, None)
    # cruzamento: placa de osso redonda no peito
    p, nn = ell(0.775, 0.0, 0.026)
    placa_osso_disco(p, nn, 0.026, {"Chest": 1.0})


def placa_osso_disco(p, nn, r, w, esp=0.010):
    nn = nn.normalized()
    up = Vector((0, 0, 1))
    sd = up.cross(nn).normalized()
    up = nn.cross(sd).normalized()
    N = 7
    base = [vert(p + (sd * math.cos(2 * math.pi * i / N) + up * math.sin(2 * math.pi * i / N)) * r, uv_amostra(2, 0.04, 0.04), w) for i in range(N)]
    mid = [vert(p + nn * (esp * 0.6) + (sd * math.cos(2 * math.pi * i / N) + up * math.sin(2 * math.pi * i / N)) * r, uv_amostra(2, 0.04, 0.04), w) for i in range(N)]
    top = [vert(p + nn * esp + (sd * math.cos(2 * math.pi * i / N) + up * math.sin(2 * math.pi * i / N)) * r * 0.62, uv_amostra(2, 0.5, 0.5), w) for i in range(N)]
    ctr = vert(p + nn * (esp * 1.05), uv_amostra(2, 0.5, 0.5), w)
    for i in range(N):
        j = (i + 1) % N
        face([base[i], base[j], mid[j], mid[i]], nn * 0.2 + (mid[i].co - p))
        face([mid[i], mid[j], top[j], top[i]], nn)
        face([top[i], top[j], ctr], nn)


# ---------------------------------------------------------------- osso com espessura e chanfro
def placa(A, a, ref, R, esp, s0, s1, l0, l1, taper, w, bis=0.006, nu=3, nv=2):
    """Placa curva de osso sobre um cilindro (eixo a por A, raio R, angulos s0..s1 a partir de ref, comprimento l0..l1) com
    espessura `esp` e chanfro `bis`. O UV mapeia a caixa da placa na amostra de osso inteira (borda amarelada nas arestas)."""
    a = a.normalized()
    e0 = (ref - a * ref.dot(a)).normalized()
    e1 = a.cross(e0)

    def pos(ang, l, h):
        return A + a * l + (e0 * math.cos(ang) + e1 * math.sin(ang)) * (R + h)

    def dom(v, dif):
        # v 0..1 ao longo; largura angular reduz com taper para o fim
        k = 1.0 - taper * (v ** 2)
        mid = (s0 + s1) / 2
        half = (s1 - s0) / 2 * k - dif
        return mid - half, mid + half

    inset = bis / R
    top = []
    for iv in range(nv + 1):
        v = iv / nv
        lv = lerp(l0 + bis, l1 - bis, v)
        sa, sb = dom(v, inset)
        lin = []
        for iu in range(nu + 1):
            u = iu / nu
            ang = lerp(sa, sb, u)
            lin.append(vert(pos(ang, lv, esp), uv_amostra(2, 0.1 + 0.8 * u, 0.1 + 0.8 * v), w))
        top.append(lin)
    for iv in range(nv):
        for iu in range(nu):
            face([top[iv][iu], top[iv][iu + 1], top[iv + 1][iu + 1], top[iv + 1][iu]], pos((s0 + s1) / 2, (l0 + l1) / 2, esp * 3) - A)
    # contorno: anel do chanfro (altura 0.55 esp, tamanho cheio) e anel da base (altura 0, tamanho cheio)
    def contorno(h, uvb):
        pts = []
        # percorre: base inferior (v=0) esq->dir, lado dir sobe, topo dir->esq, lado esq desce
        for iu in range(nu + 1):
            u = iu / nu; sa, sb = dom(0.0, 0.0); pts.append((lerp(sa, sb, u), l0, u, 0.0))
        for iv in range(1, nv + 1):
            v = iv / nv; sa, sb = dom(v, 0.0); pts.append((sb, lerp(l0, l1, v), 1.0, v))
        for iu in range(nu - 1, -1, -1):
            u = iu / nu; sa, sb = dom(1.0, 0.0); pts.append((lerp(sa, sb, u), l1, u, 1.0))
        for iv in range(nv - 1, 0, -1):
            v = iv / nv; sa, sb = dom(v, 0.0); pts.append((sa, lerp(l0, l1, v), 0.0, v))
        return [vert(pos(ang, l, h), uv_amostra(2, uvb(u, v)[0], uvb(u, v)[1]), w) for ang, l, u, v in pts]
    mid = contorno(esp * 0.5, lambda u, v: (0.04 + 0.92 * u, 0.04 + 0.92 * v))
    bas = contorno(0.0, lambda u, v: (0.01 + 0.98 * u, 0.01 + 0.98 * v))
    # contorno interno do topo (anel externo da grade)
    anel_top = []
    for iu in range(nu + 1):
        anel_top.append(top[0][iu])
    for iv in range(1, nv + 1):
        anel_top.append(top[iv][nu])
    for iu in range(nu - 1, -1, -1):
        anel_top.append(top[nv][iu])
    for iv in range(nv - 1, 0, -1):
        anel_top.append(top[iv][0])
    N = len(anel_top)
    cen = pos((s0 + s1) / 2, (l0 + l1) / 2, esp * 3) - A
    for i in range(N):
        j = (i + 1) % N
        face([anel_top[i], anel_top[j], mid[j], mid[i]], (anel_top[i].co + anel_top[j].co) / 2 - (A + a * ((l0 + l1) / 2)))
        face([mid[i], mid[j], bas[j], bas[i]], (mid[i].co + mid[j].co) / 2 - (A + a * ((l0 + l1) / 2)))


def ombreira(side):
    cs = Vector((side * 0.172, CY, 0.862))
    sh = "LeftShoulder" if side > 0 else "RightShoulder"
    ua = "LeftUpperArm" if side > 0 else "RightUpperArm"
    # lamas empilhadas sobre o ombro; eixo = frente-tras (Y); angulo medido a partir do alto (+Z) para fora (+side X)
    ref = Vector((0, 0, 1))
    eixo = Vector((0, 1, 0)) * (side)   # gira de +Z para +X do lado esquerdo
    # com a=Y, e0=Z, e1=a x e0 = Y x Z = +X (lado esquerdo); no direito inverte-se o sinal do eixo
    lamas = [(-0.15, 0.72, 0.066, {sh: 1.0}), (0.56, 1.22, 0.074, {sh: 0.5, ua: 0.5}), (1.06, 1.68, 0.080, {ua: 1.0})]
    for s0, s1, hl, w in lamas:
        placa(cs, eixo, ref, 0.104, 0.021, s0, s1, -hl, hl, 0.30, w, bis=0.009, nu=3, nv=2)


def braceletes(side):
    ua = "LeftLowerArm" if side > 0 else "RightLowerArm"
    a0 = Vector((side * 0.249, 0.06, 0.636)); a1 = Vector((side * 0.281, 0.014, 0.52))
    ax = (a1 - a0)
    Lh = ax.length
    axn = ax.normalized()
    ref = Vector((0, -1, 0))   # frente do antebraco
    w = {ua: 1.0}
    for t0, t1, sp in ((0.06, 0.34, 1.9), (0.30, 0.58, 1.9)):
        A = a0
        placa(A, axn, ref, 0.070, 0.011, -sp / 2 - 0.25, sp / 2 - 0.25, Lh * t0, Lh * t1, 0.0, w, bis=0.005, nu=3, nv=2)
    # correia de couro entre as placas
    N = 10
    for t in (0.0, 1.0):
        pass
    centro = a0 + axn * (Lh * 0.30)
    e0 = (ref - axn * ref.dot(axn)).normalized(); e1 = axn.cross(e0)
    anel = []
    for i in range(N + 1):
        ang = 2 * math.pi * i / N
        for l in (Lh * 0.275, Lh * 0.335):
            p = a0 + axn * l + (e0 * math.cos(ang) + e1 * math.sin(ang)) * 0.067
            anel.append(vert(p, uv_amostra(1, i / N, 0.5 if l < Lh * 0.3 else 0.6), w))
    for i in range(N):
        a_, b_, c_, d_ = anel[2 * i], anel[2 * i + 1], anel[2 * i + 3], anel[2 * i + 2]
        face([a_, b_, c_, d_], (a_.co + c_.co) / 2 - (a0 + axn * Lh * 0.3))


def fecho_osso():
    """Fecho de osso no pescoco: anel + garra pendente."""
    c0 = Vector((0, CY - 0.150, 0.953))
    w = {"Chest": 0.7, "Neck": 0.3}
    N, M = 8, 5
    R, r = 0.026, 0.0085
    nrm = Vector((0, -0.25, -0.1)).normalized()
    rings = []
    ex, ez = Vector((1, 0, 0)), Vector((0, 0, 1))
    for i in range(N):
        a = 2 * math.pi * i / N
        cen = c0 + (ex * math.cos(a) + ez * math.sin(a)) * R
        rad = (ex * math.cos(a) + ez * math.sin(a))
        ring = []
        for j in range(M):
            b = 2 * math.pi * j / M
            ring.append(vert(cen + rad * (r * math.cos(b)) + Vector((0, -1, 0)) * (r * math.sin(b)), uv_amostra(2, 0.5, 0.5 + 0.4 * math.sin(a)), w))
        rings.append(ring)
    for i in range(N):
        i2 = (i + 1) % N
        for j in range(M):
            j2 = (j + 1) % M
            f = face([rings[i][j], rings[i2][j], rings[i2][j2], rings[i][j2]])
            cen = f.calc_center_median()
            ringc = c0 + (Vector((cen.x - c0.x, 0, cen.z - c0.z)).normalized() * R)
            if f.normal.dot(cen - ringc) < 0:
                f.normal_flip()
                for l in f.loops:
                    l[UVL].uv = (l.vert[LU], l.vert[LV])
    # dente/garra pendurado
    base = c0 + Vector((0, -0.008, -R))
    ponta = base + Vector((0, -0.012, -0.060))
    s = [vert(base + Vector((dx, dy, 0)), uv_amostra(2, 0.2 + 0.6 * (dx > 0), 0.9), w) for dx, dy in ((-0.011, -0.004), (0.011, -0.004), (0.0, 0.009))]
    pt = vert(ponta, uv_amostra(2, 0.5, 0.1), w)
    face([s[0], s[1], pt], Vector((0, -1, 0)))
    face([s[1], s[2], pt], Vector((1, 1, 0)))
    face([s[2], s[0], pt], Vector((-1, 1, 0)))


# ---------------------------------------------------------------- montagem
def construir():
    global bm, UVL, LU, LV, DL
    c.limpar()
    c.importar(f"{c.FINAL}/SK_Archer_Chest_Starter.fbx")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    for o in [o for o in bpy.data.objects if o.type == "MESH"]:
        bpy.data.objects.remove(o)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    arm.animation_data_clear()
    c.aplicar_rotacao([arm])
    c.proporcao.aplicar(arm, [])      # so os ossos: repouso chibi igual ao dos outros modulos
    bm = bmesh.new()
    UVL = bm.loops.layers.uv.verify()
    LU = bm.verts.layers.float.new("u"); LV = bm.verts.layers.float.new("v")
    DL = bm.verts.layers.deform.verify()
    partes = {}

    def fase(nome, fn, *a):
        n0 = len(bm.faces)
        t0 = sum(len(f.verts) - 2 for f in bm.faces)
        fn(*a)
        partes[nome] = partes.get(nome, 0) + sum(len(f.verts) - 2 for f in bm.faces) - t0
    fase("forro", capa_forro)
    fase("capa_penas", capa_penas)
    fase("mantel", mantel)
    for s in (1, -1):
        fase("asas", asa, s)
        fase("ombreiras", ombreira, s)
        fase("braceletes", braceletes, s)
    fase("gibao+saia", gibao)
    fase("cinto+bolsas", cinto)
    fase("correias", correias)
    fase("fecho", fecho_osso)
    me = bpy.data.meshes.new("SK_Archer_Peitoral")
    ob = bpy.data.objects.new("SK_Archer_Peitoral", me)
    bpy.context.scene.collection.objects.link(ob)
    for n in GRUPOS:
        ob.vertex_groups.new(name=n)
    bm.to_mesh(me)
    bm.free()
    ob.parent = arm
    md = ob.modifiers.new("Armature", "ARMATURE"); md.object = arm
    # sombreamento: penas, ossos e couro facetados; tecido liso
    for p in me.polygons:
        p.use_smooth = False
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print("TRIS_PARTES", partes)
    print("TRIS_TOTAL", tris)
    c.material_simples(ob, "M_Arqueiro_Peitoral", TEX)
    ob.data.materials[0].use_backface_culling = False
    c.exportar("Arqueiro_Peitoral.glb", [arm, ob])
    c.externalizar_textura(os.path.join(c.SAIDA, "Arqueiro_Peitoral.glb"), "T_Arqueiro_Peitoral_BC.png")
    vs = [v.co for v in me.vertices]
    print("BOUNDS", [round(min(v[i] for v in vs), 3) for i in range(3)], [round(max(v[i] for v in vs), 3) for i in range(3)])


construir()
