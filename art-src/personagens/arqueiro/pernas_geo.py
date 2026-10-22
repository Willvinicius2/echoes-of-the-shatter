"""Geometria procedural de Calca e Botas do Arqueiro (Blender -b). Importado por build_calca.py / build_botas.py.
Cria a malha no espaco final (pos-proporcao): Z para cima, personagem olha para -Y, perna esquerda em +X.
Pesos por regra de altura/posicao nos mesmos 27 ossos do Rig_Humanoid_Chibi (sem transferencia, sem esticar).
"""
import os, sys, math, random
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c
import proporcao
from pernas_atlas import *

TAU = math.tau


def lin(x, a, b):
    t = (x - a) / (b - a)
    return max(0.0, min(1.0, t))


def interp(tab, z, k):
    """tab = [(z, v1, v2..)] ordenada; devolve coluna k interpolada."""
    if z <= tab[0][0]:
        return tab[0][k]
    for a, b in zip(tab, tab[1:]):
        if z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return a[k] + (b[k] - a[k]) * t
    return tab[-1][k]


class Malha:
    def __init__(self):
        self.v, self.part, self.f = [], [], []  # f: (indices, uvs, liso)

    def add_v(self, p, part):
        self.v.append(Vector(p)); self.part.append(part)
        return len(self.v) - 1

    def face(self, idx, uvs, liso=True, fora=None):
        """fora: ponto de referencia; se a normal apontar para ele, inverte (garante normais para fora)."""
        if fora is not None:
            p = [self.v[i] for i in idx]
            n = (p[1] - p[0]).cross(p[2] - p[0])
            cen = sum(p, Vector()) / len(p)
            ref = fora(cen) if callable(fora) else Vector(fora)
            if n.dot(cen - ref) < 0:
                idx, uvs = idx[::-1], uvs[::-1]
        self.f.append((list(idx), list(uvs), liso))

    def grade(self, aneis, uvf, part, fechado=True, liso=True, fora=None):
        """aneis: lista de aneis (listas de pontos). uvf(i, j) -> UV; j pode ser m (costura)."""
        base = []
        for i, an in enumerate(aneis):
            base.append([self.add_v(p, part) for p in an])
        m = len(aneis[0])
        n = len(aneis)
        for i in range(n - 1):
            for j in range(m if fechado else m - 1):
                j2 = (j + 1) % m
                idx = [base[i][j], base[i][j2], base[i + 1][j2], base[i + 1][j]]
                uvs = [uvf(i, j), uvf(i, j + 1), uvf(i + 1, j + 1), uvf(i + 1, j)]
                self.face(idx, uvs, liso, fora)
        return base

    def leque(self, pts, centro, uvf, part, fora, liso=False):
        ic = self.add_v(centro, part)
        ip = [self.add_v(p, part) for p in pts]
        m = len(pts)
        for j in range(m):
            self.face([ic, ip[j], ip[(j + 1) % m]], [uvf(None, centro), uvf(j, pts[j]), uvf(j + 1, pts[(j + 1) % m])], liso, fora)

    def obj(self, nome, mat_flat=False):
        me = bpy.data.meshes.new(nome)
        vs, fs = [], []
        # vertices separados por face-loop de UV nao sao necessarios: UV por loop
        me.from_pydata([tuple(v) for v in self.v], [], [tuple(f[0]) for f in self.f])
        uv = me.uv_layers.new(name="UVMap")
        k = 0
        for p, (idx, uvs, liso) in zip(me.polygons, self.f):
            p.use_smooth = liso
            for u in uvs:
                uv.data[k].uv = u
                k += 1
        me.update()
        o = bpy.data.objects.new(nome, me)
        bpy.context.scene.collection.objects.link(o)
        return o


# ---------------------------------------------------------------- pesos
def pesos_perna(co, part):
    side = "Left" if co.x >= 0 else "Right"
    z = co.z
    w = {}
    if part in ("pant", "knee", "wrap", "strapc"):
        h = lin(z, 0.43, 0.53)
        up = lin(z, 0.21, 0.30)
        w["Hips"] = h
        w[side + "UpperLeg"] = (1 - h) * up
        w[side + "LowerLeg"] = (1 - h) * (1 - up)
    elif part == "pelv":
        h = max(lin(z, 0.47, 0.56), 1 - lin(abs(co.x), 0.03, 0.12))
        w["Hips"] = h
        w[side + "UpperLeg"] = 1 - h
    elif part == "skirt":
        d = lin(0.56 - z, 0.0, 0.15) * lin(abs(co.x), 0.03, 0.14)
        w["Hips"] = 1 - 0.75 * d
        w[side + "UpperLeg"] = 0.75 * d
    elif part in ("cano", "plate", "strap", "cuff"):
        ll = lin(z, 0.06, 0.14)
        toe = 0.0
        w[side + "LowerLeg"] = ll
        w[side + "Foot"] = 1 - ll
    else:  # shell, sole
        toe = lin(-co.y, 0.02, 0.09)
        ll = lin(z, 0.06, 0.14) * (1 - toe)
        w[side + "LowerLeg"] = ll
        w[side + "Foot"] = (1 - ll) * (1 - toe)
        w[side + "Toes"] = (1 - ll) * toe
    tot = sum(w.values())
    return {k: v / tot for k, v in w.items() if v / tot > 1e-3}


def aplicar_pesos(o, mal, arm):
    grupos = {}
    for i, (v, part) in enumerate(zip(mal.v, mal.part)):
        for nome, peso in pesos_perna(v, part).items():
            if nome not in grupos:
                grupos[nome] = o.vertex_groups.new(name=nome)
            grupos[nome].add([i], peso, "REPLACE")
    o.parent = arm
    md = o.modifiers.new("Armature", "ARMATURE")
    md.object = arm


# ---------------------------------------------------------------- calca
def pt(th, cx, cy, z, rx, ry):
    return (cx + rx * math.cos(th), cy + ry * math.sin(th), z)


def perna(M, sx, rng, nseg=12):
    """Tubo da calca (uma perna) com dobras; devolve funcao de raio para reaproveitar nas ataduras."""
    aneis = []
    for z in PANT_Z:
        cx, cy = interp(CL, z, 1), interp(CL, z, 2)
        rx, ry = interp(PR, z, 1), interp(PR, z, 2)
        f = CREASE.get(z, 1.0)
        an = []
        for j in range(nseg):
            th = -math.pi + TAU * j / nseg
            # dobra: pronuncia na frente/tras do joelho + assimetria
            g = f * (1 + 0.035 * math.sin(3 * th + z * 40 + rng.random()) * (0.5 + 0.5 * math.cos(th * 2)))
            if z in (0.355, 0.44):
                g *= 1 - 0.04 * (math.sin(th) ** 2)
            p = pt(th, cx, cy, z, rx * g, ry * g)
            an.append((sx * p[0], p[1], p[2]))
        aneis.append(an)
    zs = PANT_Z

    def uvf(i, j):
        return uvmap(CALCA["PANT"], j / nseg, (zs[i] - Z_HEM) / (Z_TOP - Z_HEM))
    M.grade(aneis, uvf, "pant", True, True, fora=lambda p: Vector((sx * interp(CL, p.z, 1), interp(CL, p.z, 2), p.z)))


def placa_pt(cl_fn, rad_fn, th, z, off):
    cx, cy = cl_fn(z)
    rx, ry = rad_fn(z)
    return Vector(pt(th, cx, cy, z, rx + off, ry + off))


def placa(M, sx, th0, th1, zbase, ztop, nu, nv, off, esp, tile, part, uvrect, cl_fn, rad_fn, forma=None, uvsub=(0, 0, 1, 1)):
    """Placa curva sobre um tubo com espessura (superficie + parede lateral). forma(u)-> (zb, zt) varia por coluna (pontas)."""
    gu = []
    for j in range(nu + 1):
        u = j / nu
        zb, zt = forma(u) if forma else (zbase, ztop)
        col = []
        for i in range(nv + 1):
            z = zb + (zt - zb) * i / nv
            th = th0 + (th1 - th0) * u
            # bordas afundam (chanfro); centro mais alto
            e = min(u, 1 - u, i / nv, 1 - i / nv)
            o = off + esp * min(1.0, e * 3.0 + 0.35)
            p = placa_pt(cl_fn, rad_fn, th, z, o)
            col.append(Vector((sx * p.x, p.y, p.z)))
        gu.append(col)
    u0, t0, u1, t1 = uvsub

    def U(i, j):
        return uvmap(uvrect, u0 + (u1 - u0) * j / nu, t0 + (t1 - t0) * i / nv)
    ctr = lambda p: Vector((sx * cl_fn(p.z)[0], cl_fn(p.z)[1], p.z))
    # superficie
    ids = [[M.add_v(gu[j][i], part) for i in range(nv + 1)] for j in range(nu + 1)]
    for j in range(nu):
        for i in range(nv):
            M.face([ids[j][i], ids[j + 1][i], ids[j + 1][i + 1], ids[j][i + 1]],
                   [U(i, j), U(i, j + 1), U(i + 1, j + 1), U(i + 1, j)], True, ctr)
    # parede lateral (borda) descendo para o tubo
    borda = []
    for j in range(nu + 1):
        borda.append((j, 0))
    for i in range(1, nv + 1):
        borda.append((nu, i))
    for j in range(nu - 1, -1, -1):
        borda.append((j, nv))
    for i in range(nv - 1, 0, -1):
        borda.append((0, i))
    inner = {}
    for (j, i) in borda:
        p = gu[j][i]
        cx, cy = cl_fn(p.z)
        q = Vector((sx * cx, cy, p.z))
        inner[(j, i)] = M.add_v(p + (q - p).normalized() * (esp * 1.4), part)
    n = len(borda)
    for k in range(n):
        a, b = borda[k], borda[(k + 1) % n]
        M.face([ids[a[0]][a[1]], ids[b[0]][b[1]], inner[b], inner[a]],
               [U(a[1], a[0]), U(b[1], b[0]), U(b[1], b[0]), U(a[1], a[0])], False, ctr)


def cl_calca(z):
    return interp(CL, z, 1), interp(CL, z, 2)


def rad_calca(z):
    return interp(PR, z, 1) * 1.0, interp(PR, z, 2) * 1.0


def ataduras(M, sx, rng, z0=0.245, z1=0.335, voltas=2.4, passos=26, larg=0.034):
    """Faixa verde enrolada em espiral na canela (mais folgada que a calca)."""
    aneis = []
    for k in range(passos + 1):
        s = k / passos
        z = z0 + (z1 - z0) * s
        th = -math.pi * 0.5 + TAU * voltas * s
        cx, cy = cl_calca(z)
        rx, ry = rad_calca(z)
        off = 0.009 + 0.002 * math.sin(s * 25 + sx)
        par = []
        for dz in (-larg / 2, larg / 2):
            zz = z + dz
            r = (rx + off, ry + off)
            p = pt(th, cx, cy, zz, r[0], r[1])
            par.append((sx * p[0], p[1], p[2]))
        aneis.append(par)

    def uvf(i, j):
        return uvmap(CALCA["WRAP"], i / passos, j)
    M.grade(aneis, uvf, "wrap", False, True, fora=lambda p: Vector((sx * cl_calca(p.z)[0], cl_calca(p.z)[1], p.z)))


def cinta(M, sx, z, alt, off, uvrect, part, cl_fn, rad_fn, nseg=12, rect_t=(0, 1)):
    aneis = []
    for dz in (-alt / 2, alt / 2):
        zz = z + dz
        cx, cy = cl_fn(zz)
        rx, ry = rad_fn(zz)
        an = []
        for j in range(nseg):
            th = -math.pi + TAU * j / nseg
            p = pt(th, cx, cy, zz, rx + off, ry + off)
            an.append((sx * p[0], p[1], p[2]))
        aneis.append(an)
    M.grade(aneis, lambda i, j: uvmap(uvrect, j / nseg, rect_t[i]), part, True, True,
            fora=lambda p: Vector((sx * cl_fn(p.z)[0], cl_fn(p.z)[1], p.z)))


def caixa(M, centro, tam, uvrect, part, rot_th=0.0, sx=1):
    """Caixa pequena (fivela) com UV planar no retangulo."""
    cx, cy, cz = centro
    hx, hy, hz = tam[0] / 2, tam[1] / 2, tam[2] / 2
    c, s = math.cos(rot_th), math.sin(rot_th)

    def P(a, b, d):
        x, y = a * hx, b * hy
        return Vector((cx + (x * c - y * s), cy + (x * s + y * c), cz + d * hz))
    cantos = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
    ids = [M.add_v(P(*k), part) for k in cantos]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    for q in quads:
        M.face([ids[i] for i in q], [uvmap(uvrect, a, b) for a, b in ((0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9))],
               False, Vector((cx, cy, cz)))


def pelvis(M, rng):
    zs = [0.49, 0.52, 0.55, 0.585]
    rxy = [(0.205, 0.108), (0.215, 0.114), (0.218, 0.116), (0.212, 0.113)]
    nseg = 16
    aneis = []
    for z, (rx, ry) in zip(zs, rxy):
        an = []
        for j in range(nseg):
            th = -math.pi + TAU * j / nseg
            g = 1 + 0.02 * math.sin(5 * th + z * 30)
            an.append(pt(th, PELV_C[0], PELV_C[1], z, rx * g, ry * g))
        aneis.append(an)
    M.grade(aneis, lambda i, j: uvmap(CALCA["PELV"], j / nseg, i / (len(zs) - 1)), "pelv", True, True,
            fora=lambda p: Vector((0, 0.08, p.z)))


def saia_penas(M, rng):
    """Barra de penas/folhas: lâminas de pontas variadas, comprimentos e larguras diferentes, duas camadas."""
    camadas = [(22, 0.0, 0.0), (20, 0.5, 0.012)]
    for n, fase, drop in camadas:
        for k in range(n):
            a = TAU * (k + fase + rng.uniform(-0.28, 0.28)) / n
            # a=0 -> +x ; frente = -y => a = -pi/2
            fr = max(0.0, -math.sin(a))      # 1 na frente
            costas = max(0.0, math.sin(a))
            comp = rng.uniform(0.09, 0.15) + 0.05 * costas + (0.03 if abs(math.cos(a)) > 0.8 else 0)
            comp *= 1.0 if fase == 0.0 else 1.12
            if fr > 0.6:
                comp = min(comp, 0.145)
            larg = rng.uniform(0.045, 0.075)
            ez, ey = 0.232, 0.122
            pc = Vector((PELV_C[0] + ez * math.cos(a), PELV_C[1] + ey * math.sin(a), 0.560 - drop))
            nor = Vector((math.cos(a) / ez, math.sin(a) / ey, 0)).normalized()
            tan = Vector((-nor.y, nor.x, 0))
            lado = rng.uniform(-0.45, 0.45) * larg   # ponta torta
            pts = []
            filas = [(0.0, 1.0, 0.0), (0.38, 1.1, 0.012), (0.72, 0.85, 0.03), (1.0, 0.0, 0.055)]
            filas_pts = []
            for fk, (t, wf, out) in enumerate(filas):
                cen = pc + nor * (out + 0.004) + Vector((0, 0, -comp * t))
                cen += tan * (lado * t * t)
                if wf == 0.0:
                    filas_pts.append([cen])
                else:
                    filas_pts.append([cen - tan * (larg / 2 * wf), cen + tan * (larg / 2 * wf)])
            tile = rng.choice(["F0", "F0", "F1", "F2"])
            r = CALCA[tile]
            ids = [[M.add_v(p, "skirt") for p in fila] for fila in filas_pts]
            oc = lambda p: Vector((PELV_C[0], PELV_C[1], p.z))
            def UV(fi, ci, n):
                t = filas[fi][0]
                u = 0.5 if n == 1 else (0.1 + 0.8 * ci)
                return uvmap(r, u, 1 - t)
            for fi in range(len(filas) - 1):
                A, B = ids[fi], ids[fi + 1]
                if len(B) == 1:
                    M.face([A[0], A[1], B[0]], [UV(fi, 0, 2), UV(fi, 1, 2), UV(fi + 1, 0, 1)], True, oc)
                else:
                    M.face([A[0], A[1], B[1], B[0]], [UV(fi, 0, 2), UV(fi, 1, 2), UV(fi + 1, 1, 2), UV(fi + 1, 0, 2)], True, oc)


def construir_calca(seed=7):
    rng = random.Random(seed)
    M = Malha()
    for sx in (1, -1):
        perna(M, sx, rng)
        ataduras(M, sx, rng)
        # joelheira (frente do joelho)
        placa(M, sx, -math.pi * 0.5 - 0.62, -math.pi * 0.5 + 0.62, 0.315, 0.405, 4, 3, 0.012, 0.010, "KNEE", "knee",
              CALCA["KNEE"], cl_calca, rad_calca,
              forma=lambda u: (0.318 + 0.012 * math.sin(u * math.pi), 0.402 - 0.012 * (1 - math.sin(u * math.pi))))
        # cintas de couro na atadura (base e topo) + fivela
        cinta(M, sx, 0.243, 0.016, 0.014, CALCA["STRAP"], "strapc", cl_calca, rad_calca)
        cinta(M, sx, 0.338, 0.016, 0.014, CALCA["STRAP"], "strapc", cl_calca, rad_calca)
        cx, cy = cl_calca(0.338)
        rx, ry = rad_calca(0.338)
        th = -math.pi * 0.5 + 0.5
        caixa(M, (sx * (cx + (rx + 0.020) * math.cos(th)), cy + (ry + 0.020) * math.sin(th), 0.338), (0.020, 0.008, 0.022),
              CALCA["METAL"], "strapc", rot_th=(th if sx > 0 else math.pi - th) + math.pi / 2)
    pelvis(M, rng)
    saia_penas(M, rng)
    return M


# ---------------------------------------------------------------- botas
XC = 0.165          # centro X do pe
Y_HEEL, Y_TOE = 0.160, -0.275
LEN = Y_HEEL - Y_TOE
# t: posicao ao longo do pe (0 calcanhar, 1 bico)
FT = [0.0, 0.22, 0.42, 0.60, 0.76, 0.90, 0.975]
FHW = [0.090, 0.100, 0.110, 0.119, 0.120, 0.100, 0.058]
FZT = [0.150, 0.148, 0.132, 0.116, 0.104, 0.092, 0.076]
Z_SOLA = 0.040


def cl_bota(z):
    return interp(CL, z, 1), interp(CL, z, 2)  # mesma linha do osso/perna


BR = [(0.07, 0.086, 0.090), (0.12, 0.094, 0.098), (0.17, 0.090, 0.095), (0.22, 0.090, 0.094), (0.26, 0.092, 0.096)]


def rad_bota(z):
    return interp(BR, z, 1), interp(BR, z, 2)


def planar_u(p, sx, reg):
    """UV planar (x local, z) para as tampas do pe: usa um trecho liso do couro do atlas."""
    off = (p[0] - sx * XC) * sx
    return uvmap(BOTAS[reg], 0.3 + (off + 0.1) / 0.2 * 0.3, 0.2 + (p[2] - 0.03) / 0.12 * 0.5)


def construir_botas(seed=11):
    rng = random.Random(seed)
    M = Malha()
    for sx in (1, -1):
        sr = random.Random(seed + (0 if sx > 0 else 5))
        # ---- cano (com cuff dobrado no topo)
        zc = [0.075, 0.12, 0.165, 0.21, 0.245, 0.262]
        offc = [0.0, 0.003, -0.002, 0.004, 0.016, 0.006]
        nseg = 10
        aneis = []
        for z, o in zip(zc, offc):
            cx, cy = cl_bota(z)
            rx, ry = rad_bota(z)
            an = []
            for j in range(nseg):
                th = -math.pi + TAU * j / nseg
                g = 1 + 0.018 * math.sin(4 * th + z * 55 + sr.random() * 2)
                p = pt(th, cx, cy, z, (rx + o) * g, (ry + o) * g)
                an.append((sx * p[0], p[1], p[2]))
            aneis.append(an)
        parte_uv = {0: ("CANO", 0.0), 1: ("CANO", 0.2), 2: ("CANO", 0.4), 3: ("CANO", 0.6), 4: ("CANO", 0.78), 5: ("CUFF", 0.0), 6: ("CUFF", 1.0)}

        def uvc(i, j):
            if i <= 3:
                return uvmap(BOTAS["CANO"], j / nseg, i / 3)
            return uvmap(BOTAS["CUFF"], j / nseg, 0.2 if i == 4 else 1.0)
        M.grade(aneis, uvc, "cano", True, True, fora=lambda p, sx=sx: Vector((sx * cl_bota(p.z)[0], cl_bota(p.z)[1], p.z)))
        # ---- peito do pe (shell): aneis ao longo de Y
        nj = 10
        aneis = []
        for t, hw, zt in zip(FT, FHW, FZT):
            y = Y_HEEL - LEN * t
            zc_ = (zt + Z_SOLA - 0.004) / 2
            hh = (zt - (Z_SOLA - 0.004)) / 2
            an = []
            for j in range(nj):
                th = TAU * j / nj
                cs, sn = math.cos(th), math.sin(th)
                x = hw * math.copysign(abs(cs) ** (0.62 if sn > 0 else 0.32), cs)
                zz = zc_ + hh * math.copysign(abs(sn) ** 0.62, sn)
                an.append((sx * (XC + x), y, zz))
            aneis.append(an)
        ids = M.grade(aneis, lambda i, j: uvmap(BOTAS["UPPER"], j / nj, FT[i] if i < len(FT) else 1.0), "shell", True, True,
                      fora=lambda p, sx=sx: Vector((sx * XC, p.y, 0.09)))
        # calcanhar fechado (leque atras)
        M.leque(aneis[0], (sx * XC, Y_HEEL + 0.004, (FZT[0] + Z_SOLA) / 2), lambda j, p, sx=sx: planar_u(p, sx, "CANO"), "shell",
                lambda p, sx=sx: Vector((sx * XC, 0.0, p.z)) + Vector((0, -2, 0)), True)
        # bico arredondado: leque na frente
        yb = Y_TOE - 0.020
        pts = aneis[-1]
        cen = (sx * XC, yb, (FZT[-1] + Z_SOLA) / 2 - 0.004)
        M.leque(pts, cen, lambda j, p, sx=sx: planar_u(p, sx, "UPPER"), "shell", lambda p, sx=sx: Vector((sx * XC, 0.0, p.z)), True)
        # ---- sola com chanfro
        perfil = [(0.0, 0.100), (0.22, 0.114), (0.5, 0.131), (0.76, 0.133), (0.92, 0.112), (1.0, 0.066), (1.03, 0.016)]
        lado_d = [(t, w) for t, w in perfil]
        pol = [(XC + w, Y_HEEL - LEN * t) for t, w in lado_d] + [(XC - w, Y_HEEL - LEN * t) for t, w in reversed(lado_d)]
        pol = [(sx * x, y) for x, y in pol]
        ymid = Y_HEEL - LEN * 0.5
        np_ = len(pol)

        def escala(f):
            return [(sx * XC + (x - sx * XC) * f, ymid + (y - ymid) * f) for x, y in pol]
        aneis = [[(x, y, z) for x, y in escala(f)] for f, z in ((0.93, 0.0), (1.0, 0.010), (1.0, 0.040))]
        per = [0.0]
        for k in range(np_):
            a, b = pol[k], pol[(k + 1) % np_]
            per.append(per[-1] + math.hypot(a[0] - b[0], a[1] - b[1]))
        M.grade(aneis, lambda i, j: uvmap(BOTAS["SOLEW"], per[j] / per[-1], [0.0, 0.25, 1.0][i]), "sole", True, False,
                fora=lambda p, sx=sx: Vector((sx * XC, ymid, 0.017)))
        # tampas (planar): embaixo com banda de rodagem, em cima
        def planar(i, p):
            return uvmap(BOTAS["SOLE"], (abs(p[0]) - 0.04) / 0.26, (p[1] + 0.30) / 0.45)
        for zc2, f, dirn in ((0.0, 0.93, -1), (0.040, 1.0, 1)):
            pts = [(x, y, zc2) for x, y in escala(f)]
            M.leque(pts, (sx * XC, ymid, zc2), planar, "sole", lambda p, d=dirn, zc2=zc2: Vector((sx * XC, ymid, zc2 - d)))
        # ---- placas de osso no cano (lado externo, interno, frente)
        def pontaS(u):
            return (0.100 + 0.028 * abs(math.sin(u * 3.1)) , 0.222 - 0.02 * (1 - math.sin(u * math.pi)))
        placa(M, sx, -0.50, 0.55, 0.0, 0.0, 3, 2, 0.010, 0.012, "PLATE", "plate", BOTAS["PLATE_O"], cl_bota, rad_bota,
              forma=lambda u: (0.105 + 0.045 * u, 0.232 - 0.03 * u))
        placa(M, sx, math.pi - 0.55, math.pi + 0.45, 0.0, 0.0, 3, 2, 0.010, 0.012, "PLATE", "plate", BOTAS["PLATE_I"], cl_bota, rad_bota,
              forma=lambda u: (0.150 - 0.04 * u, 0.215 + 0.02 * u))
        placa(M, sx, -math.pi * 0.5 - 0.50, -math.pi * 0.5 + 0.50, 0.0, 0.0, 4, 2, 0.011, 0.012, "PLATE", "plate", BOTAS["PLATE_F"], cl_bota, rad_bota,
              forma=lambda u: (0.115 + 0.055 * (1 - abs(2 * u - 1)), 0.238 - 0.01 * abs(2 * u - 1)))
        # ---- cintas de couro + fivela
        for zs_, alt in ((0.182, 0.018),):
            cinta(M, sx, zs_, alt, 0.021, BOTAS["STRAP"], "strap", cl_bota, rad_bota, nseg=10)
        cx, cy = cl_bota(0.18)
        rx, ry = rad_bota(0.18)
        th = -math.pi * 0.5 + 0.55
        caixa(M, (sx * (cx + (rx + 0.030) * math.cos(th)), cy + (ry + 0.030) * math.sin(th), 0.180), (0.022, 0.009, 0.024),
              BOTAS["METAL"], "strap", rot_th=(th if sx > 0 else math.pi - th) + math.pi / 2)
    return M


# ---------------------------------------------------------------- fluxo
def peca_pernas(fbx_nome, nome_malha, material, glb, construtor, textura):
    limpar = c.limpar
    limpar()
    c.importar(f"{c.FINAL}/{fbx_nome}")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    doador = [o for o in bpy.data.objects if o.type == "MESH"][0]
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    arm.animation_data_clear()
    c.aplicar_rotacao([arm, doador])
    proporcao.aplicar(arm, [doador])        # arm vira o rig chibi comum; o doador so serve para isso
    bpy.data.objects.remove(doador, do_unlink=True)
    mal = construtor()
    o = mal.obj(nome_malha)
    aplicar_pesos(o, mal, arm)
    c.material_simples(o, material, textura)
    o.data.materials[0].use_backface_culling = False
    ntris = sum(len(f[0]) - 2 for f in mal.f)
    por = {}
    for f in mal.f:
        k = mal.part[f[0][0]]
        por[k] = por.get(k, 0) + len(f[0]) - 2
    print("TRIS", nome_malha, ntris, por)
    c.exportar(glb, [arm, o])
    c.externalizar_textura(os.path.join(c.SAIDA, glb), os.path.basename(textura))
    return o
