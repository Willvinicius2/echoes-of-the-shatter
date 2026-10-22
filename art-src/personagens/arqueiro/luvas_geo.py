"""Geometria das luvas do Arqueiro (modulo Luvas): coordenadas do mundo Blender (Z cima, frente = -Y), repouso chibi.
Usado por build_luvas.py. Tudo procedural (bmesh/mathutils), sem dependencia dos FBX de malha.

Mao esquerda: PUNHO FECHADO em volta do cabo do arco (eixo vertical Z) em G = pulso + (0,-0,085,0). O arco precisa
entrar deslocado nesse vetor em relacao a socket_weapon_l (ver orcamento.md): o pulso fica atras do cabo.
Mao direita: relaxada, dedos em gancho (indicador/medio/anelar) prontos para puxar a corda.
Pesos: braçadeira/cintas -> LowerArm; punho (cuff) -> mistura LowerArm/Hand pelo eixo do antebraco; resto -> Hand.
(O rig nao tem ossos de dedo: dedos 100% Hand, sem esticar.)
"""
import math
import bpy
import bmesh
from mathutils import Vector

M = 0.006
ZONAS = {  # (u0,v0,u1,v1) iguais as de luvas_tex.py, com margem
    "couro": (0.0, 0.5, 0.5, 1.0), "osso": (0.5, 0.5, 1.0, 1.0), "pele": (0.0, 0.25, 0.25, 0.5),
    "cinta": (0.25, 0.25, 0.5, 0.5), "metal": (0.5, 0.25, 0.75, 0.5), "pano": (0.75, 0.25, 1.0, 0.5),
    "palma": (0.0, 0.0, 0.5, 0.25),
}


def zona(z):
    u0, v0, u1, v1 = ZONAS[z]
    return u0 + M, v0 + M, u1 - M, v1 - M


class Parte:
    def __init__(s, nome, bevel=False):
        s.nome, s.bevel = nome, bevel
        s.v, s.f, s.uv = [], [], []

    def vert(s, p):
        s.v.append(Vector(p)); return len(s.v) - 1

    def face(s, idx, uvs):
        s.f.append(idx); s.uv.append(uvs)

    def objeto(s, bw=None):
        me = bpy.data.meshes.new(s.nome)
        me.from_pydata([tuple(p) for p in s.v], [], s.f)
        me.update()
        uvl = me.uv_layers.new(name="UVMap")
        k = 0
        for uvs in s.uv:
            for uv in uvs:
                uvl.data[k].uv = uv; k += 1
        ob = bpy.data.objects.new(s.nome, me)
        bpy.context.scene.collection.objects.link(ob)
        if s.bevel:
            bm = bmesh.new(); bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me); bm.free()
        return ob


def frames(pts, hint):
    n = len(pts)
    T = [((pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)])).normalized() for i in range(n)]
    h = Vector(hint)
    N0 = h - T[0] * h.dot(T[0])
    if N0.length < 1e-6:
        N0 = Vector((0, 0, 1)) - T[0] * T[0].z
    N = [N0.normalized()]
    for i in range(1, n):
        N.append((T[i - 1].rotation_difference(T[i]) @ N[-1]).normalized())
    B = [T[i].cross(N[i]) for i in range(n)]
    return T, N, B


def tubo(P, pts, rad, lados, z, hint, cap0=True, cap1=True, fase=0.0):
    """Varredura de secao elipse (rN, rB) ao longo de pts. rad: lista de float ou (rN, rB)."""
    pts = [Vector(p) for p in pts]
    T, N, B = frames(pts, hint)
    u0, v0, u1, v1 = zona(z)
    n = len(pts)
    ids = []
    for i in range(n):
        r = rad[i]; rn, rb = (r, r) if not isinstance(r, tuple) else r
        row = []
        for j in range(lados):
            a = 2 * math.pi * j / lados + fase
            row.append(P.vert(pts[i] + N[i] * (math.cos(a) * rn) + B[i] * (math.sin(a) * rb)))
        ids.append(row)
    for i in range(n - 1):
        for j in range(lados):
            j2 = (j + 1) % lados
            uu0 = u0 + (u1 - u0) * j / lados; uu1 = u0 + (u1 - u0) * (j + 1) / lados
            va = v0 + (v1 - v0) * i / (n - 1); vb = v0 + (v1 - v0) * (i + 1) / (n - 1)
            P.face([ids[i][j], ids[i][j2], ids[i + 1][j2], ids[i + 1][j]], [(uu0, va), (uu1, va), (uu1, vb), (uu0, vb)])
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    for flag, i, rev in ((cap0, 0, True), (cap1, n - 1, False)):
        if not flag:
            continue
        c = P.vert(pts[i])
        for j in range(lados):
            j2 = (j + 1) % lados
            tri = [ids[i][j], ids[i][j2], c]
            if rev:
                tri = [ids[i][j2], ids[i][j], c]
            P.face(tri, [(cu, cv)] * 3)


def cone(P, base, dire, raio, comp, lados, z):
    d = Vector(dire).normalized()
    T, N, B = frames([Vector(base), Vector(base) + d], (0, 0, 1) if abs(d.z) < 0.9 else (1, 0, 0))
    u0, v0, u1, v1 = zona(z)
    ring = [P.vert(Vector(base) + N[0] * math.cos(2 * math.pi * j / lados) * raio + B[0] * math.sin(2 * math.pi * j / lados) * raio) for j in range(lados)]
    ap = P.vert(Vector(base) + d * comp)
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    for j in range(lados):
        j2 = (j + 1) % lados
        P.face([ring[j], ring[j2], ap], [(u0 + (u1 - u0) * j / lados, v0), (u0 + (u1 - u0) * (j + 1) / lados, v0), (cu, v1)])
    P.face(list(reversed(ring)), [(cu, cv)] * lados)


def caixa(P, c, ex, ey, ez, meio, z):
    """Caixa com semi-lados meio=(hx,hy,hz) nos eixos ex,ey,ez (unitarios)."""
    c = Vector(c); ax = [Vector(ex).normalized(), Vector(ey).normalized(), Vector(ez).normalized()]
    u0, v0, u1, v1 = zona(z)
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    k = 0.46 * (u1 - u0) / max(meio)
    ids = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                ids[(sx, sy, sz)] = P.vert(c + ax[0] * (sx * meio[0]) + ax[1] * (sy * meio[1]) + ax[2] * (sz * meio[2]))
    for eixo in range(3):
        for s in (-1, 1):
            a, b = [i for i in range(3) if i != eixo]
            quad = []
            for (sa, sb) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                key = [0, 0, 0]; key[eixo] = s; key[a] = sa; key[b] = sb
                quad.append(tuple(key))
            idx = [ids[q] for q in quad]
            # orientacao: normal = ax[eixo]*s
            p0, p1, p2 = [P.v[i] for i in idx[:3]]
            if (p1 - p0).cross(p2 - p1).dot(ax[eixo] * s) < 0:
                idx.reverse(); quad.reverse()
            uvs = [(cu + q[a] * meio[a] * k, cv + q[b] * meio[b] * k * (v1 - v0) / (u1 - u0)) for q in quad]
            P.face(idx, uvs)


def placa_arco(P, centros, eixo, fora, r_in, esp, meio_ang, m, z, ck=None, flip=False):
    """Placa curva (arco de cilindro) com espessura e CHANFRO embutido: ck[i] = fator da espessura em cada anel (anel de ponta
    fino = chanfro no comprimento); as duas pontas angulares ficam com metade da espessura (chanfro lateral)."""
    ax = Vector(eixo).normalized()
    out = (Vector(fora) - ax * Vector(fora).dot(ax)).normalized()
    side = ax.cross(out)
    u0, v0, u1, v1 = zona(z)
    n = len(centros)
    ck = ck or [1.0] * n
    ids = []
    for i in range(n):
        ring = []
        for j in range(m + 1):  # externa
            a = math.radians(-meio_ang + 2 * meio_ang * j / m)
            ca = 0.5 if j in (0, m) else 1.0
            ring.append(P.vert(centros[i] + (out * math.cos(a) + side * math.sin(a)) * (r_in[i] + esp[i] * ck[i] * ca)))
        for j in range(m, -1, -1):  # interna
            a = math.radians(-meio_ang + 2 * meio_ang * j / m)
            ring.append(P.vert(centros[i] + (out * math.cos(a) + side * math.sin(a)) * r_in[i]))
        ids.append(ring)
    L = len(ids[0])
    for i in range(n - 1):
        for k in range(L):
            k2 = (k + 1) % L
            va = v0 + (v1 - v0) * i / (n - 1); vb = v0 + (v1 - v0) * (i + 1) / (n - 1)
            if k < m:   # face externa: usa a largura toda da zona (borda amarelada nas pontas); o resto vai para a faixa da borda
                ua = u0 + (u1 - u0) * k / m; ub = u0 + (u1 - u0) * (k + 1) / m
            else:
                ua = ub = u1 - 0.004
            q = [(ua, va), (ub, va), (ub, vb), (ua, vb)]
            if flip:
                q = [(u0 + (u1 - u0) * (1 - (t[0] - u0) / (u1 - u0)), t[1]) for t in q]
            P.face([ids[i][k], ids[i][k2], ids[i + 1][k2], ids[i + 1][k]], q)
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    for i, rev in ((0, True), (n - 1, False)):
        idx = ids[i][:]
        if rev:
            idx.reverse()
        P.face(idx, [(cu, cv)] * len(idx))


def anel(P, c0, c1, rn, rb, lados, z, hint):
    tubo(P, [c0, c1], [(rn, rb), (rn, rb)], lados, z, hint, cap0=False, cap1=False)


def arco_pontos(G, phi0, phi1, n, R, zh):
    return [Vector((G.x + R * math.sin(math.radians(phi0 + (phi1 - phi0) * i / max(n - 1, 1))),
                    G.y + R * math.cos(math.radians(phi0 + (phi1 - phi0) * i / max(n - 1, 1))), G.z + zh)) for i in range(n)]


def dedo_arco(S, G, phi0, comp, R, zh, rho, sinal, cortes=0.72, lados=5, hint=(0, 0, 1)):
    """Dedo que enrola no cabo (planta XY): couro ate 'cortes' do comprimento, ponta de pele exposta."""
    ang = math.degrees(comp / R) * sinal
    fr = [0.0, 0.34, cortes]
    pts_l = arco_pontos(G, phi0, phi0 + ang * 1.0, 2, R, zh)  # so para tipos
    ph = lambda f: phi0 + ang * f
    pt = lambda f, rr=R: arco_pontos(G, ph(f), ph(f), 1, rr, zh)[0]
    couro = [pt(f) for f in fr]
    tubo(S["soft_H"], couro, [(rho * 0.93, rho), (rho * 0.95, rho * 1.0), (rho * 0.95, rho * 1.06)], lados, "couro", (0, 0, 1), cap0=False, cap1=True)
    pele = [pt(f) for f in (cortes, 1.0)]
    tubo(S["soft_H"], pele, [(rho * 0.86, rho * 0.9), (rho * 0.7, rho * 0.72)], lados, "pele", (0, 0, 1), cap0=False, cap1=True)


def dedo_livre(S, base, u, n, comp, th, rho, cortes=0.72, lados=5):
    """Dedo no espaco (mao relaxada): 3 segmentos que curvam para o lado n (palma) com angulos acumulados th (graus)."""
    fr = (0.40, 0.33, 0.27)
    p = [Vector(base)]
    for k in range(3):
        d = (u * math.cos(math.radians(th[k])) + n * math.sin(math.radians(th[k]))).normalized()
        p.append(p[-1] + d * comp * fr[k])
    # ponto de corte: 'cortes' do comprimento total, dentro do 2o/3o segmento
    pm = p[2] + (p[3] - p[2]) * 0.1
    tubo(S["soft_H"], [p[0], p[1], pm], [(rho, rho), (rho * 1.0, rho), (rho * 1.05, rho * 1.05)], lados, "couro", n, cap0=False, cap1=True)
    tubo(S["soft_H"], [pm, p[2], p[3]], [(rho * 0.88, rho * 0.88), (rho * 0.84, rho * 0.84), (rho * 0.7, rho * 0.7)], lados, "pele", n, cap0=False, cap1=True)
    return p


def construir(W, E, lado):
    """Retorna dict de Parte para um lado. W = pulso (cabeca de Hand), E = cotovelo (cabeca de LowerArm). lado=+1 esquerda, -1 direita."""
    S = {"soft_L": Parte("soft_L"), "soft_C": Parte("soft_C"), "soft_H": Parte("soft_H"),
         "hard_L": Parte("hard_L"), "hard_H": Parte("hard_H")}
    W = Vector(W); E = Vector(E)
    ax = (W - E).normalized()                       # cotovelo -> pulso
    L = (W - E).length
    fora = Vector((lado, 0, 0))
    out = (fora - ax * fora.dot(ax)).normalized()
    side = ax.cross(out)
    at = lambda d: E + ax * d

    # ---- punho alto de couro (cuff): flare no pulso
    cuff = [at(L * 0.50), at(L * 0.97), at(L * 1.14)]
    tubo(S["soft_C"], cuff, [0.0335, 0.0385, 0.041], 8, "couro", out, cap0=False, cap1=False)
    # cintas de couro + fivelas no punho
    for d in (L * 0.86, L * 1.03):
        anel(S["soft_C"], at(d - 0.005), at(d + 0.005), 0.0385 if d < L * 0.955 else 0.0415, 0.0385 if d < L * 0.955 else 0.0415, 8, "cinta", out)
        rr = 0.0445 if d < L * 0.955 else 0.0465
        caixa(S["hard_L" if d < L * 0.95 else "hard_H"], at(d) + out * (rr + 0.0015), side, ax, out, (0.0065, 0.0075, 0.0033), "metal")

    # ---- braçadeira de osso (LowerArm): 2 placas chanfradas + nervura central + espinhos + cintas largas com fivela
    def placa(d0, d1, rin0, rin1, esp_, half, flip=False):
        ds = [d0, d0 + 0.0045, d1 - 0.0045, d1]
        f = lambda k: rin0 + (rin1 - rin0) * k
        placa_arco(S["hard_L"], [at(d) for d in ds], ax, out, [f(0), f(0.1), f(0.9), f(1.0)], [esp_] * 4, half, 4, "osso",
                   ck=[0.4, 1.0, 1.0, 0.4], flip=flip)
    placa(L * 0.07, L * 0.40, 0.0385, 0.0365, 0.0105, 96)
    placa(L * 0.53, L * 0.79, 0.0365, 0.0355, 0.0095, 96, flip=True)
    # nervura central elevada na placa de cima
    placa_arco(S["hard_L"], [at(d) for d in (L * 0.12, L * 0.135, L * 0.335, L * 0.35)], ax, out,
               [0.049, 0.049, 0.0475, 0.0475], [0.0075] * 4, 24, 2, "osso", ck=[0.4, 1.0, 1.0, 0.4])
    for d, tam in ((L * 0.20, 0.022), (L * 0.31, 0.017)):
        cone(S["soft_L"], at(d) + out * 0.0555, out * 1.0 - ax * 0.45, 0.0068, tam, 4, "osso")
    # cintas de couro (elipse justa: por fora da placa e rente ao braço no lado aberto) + fivela
    for d, rr in ((L * 0.465, 0.0475), (L * 0.815, 0.0455)):
        cen = out * (rr - 0.0405) / 1.0
        anel(S["soft_L"], at(d - 0.0065) + cen, at(d + 0.0065) + cen, (rr + 0.037) / 2 + 0.001, 0.043, 8, "cinta", out)
    caixa(S["hard_L"], at(L * 0.465) + out * 0.0505, side, ax, out, (0.0085, 0.0075, 0.0035), "metal")
    # tira de pano verde por baixo, aparece no lado aberto
    tubo(S["soft_L"], [at(L * 0.10), at(L * 0.56)], [0.0345, 0.033], 6, "pano", out, cap0=False, cap1=False)
    return S, ax, out, side, L


def mao_esquerda(S, W, ax):
    """Punho fechado em volta do cabo (eixo Z em G)."""
    G = W + Vector((0, -0.085, 0))
    # palma (arco phi 8..62 graus, R 0.062), secao radial 0.016 x vertical 0.054
    pts = arco_pontos(G, 6, 64, 5, 0.062, 0.0)
    tubo(S["soft_H"], pts, [(0.016, 0.052), (0.0175, 0.055), (0.018, 0.056), (0.0175, 0.055), (0.016, 0.053)], 8, "couro",
         (math.sin(math.radians(6)), math.cos(math.radians(6)), 0), cap0=True, cap1=True)
    # cinta atravessada na palma + fivela
    a0 = arco_pontos(G, 33, 41, 2, 0.062, 0.0)
    tubo(S["soft_H"], a0, [(0.0192, 0.0575), (0.0192, 0.0575)], 8, "cinta", (math.sin(math.radians(33)), math.cos(math.radians(33)), 0), cap0=False, cap1=False)
    ph = math.radians(37)
    caixa(S["hard_H"], G + Vector((0.083 * math.sin(ph), 0.083 * math.cos(ph), 0)),
          (math.sin(ph), math.cos(ph), 0), (math.cos(ph), -math.sin(ph), 0), (0, 0, 1), (0.0035, 0.009, 0.014), "metal")
    # dedos: indicador no topo -> minimo embaixo
    zs = (0.0405, 0.0135, -0.0135, -0.0405)
    comp = (0.112, 0.120, 0.113, 0.095)
    rho = (0.0135, 0.0135, 0.0132, 0.0118)
    for z, c, r in zip(zs, comp, rho):
        dedo_arco(S, G, 60, c, 0.056, z, r, +1)
        ph = math.radians(66)
        base = G + Vector((0.0745 * math.sin(ph), 0.0745 * math.cos(ph), z))
        d = Vector((math.sin(ph), math.cos(ph), 0)) * 0.5 + Vector((math.cos(ph), -math.sin(ph), 0)) * 0.7 + Vector((0, 0, 0.0))
        cone(S["soft_H"], base, d, 0.0078 if r > 0.0125 else 0.0065, 0.027 if r > 0.0125 else 0.02, 5, "osso")
    # polegar: nasce na base da palma (lado de dentro) e envolve ate a frente
    dedo_arco(S, G, 12, 0.118, 0.056, 0.036, 0.0148, -1)
    return G


def mao_direita(S, W, ax):
    """Mao relaxada, dedos em gancho para a corda. u = continuacao do antebraco."""
    n0 = len(S["soft_H"].v); h0 = len(S["hard_H"].v)
    u = (ax + Vector((0, -0.12, 0))).normalized()
    n = (Vector((1, 0, 0)) - u * u.x).normalized()      # palma voltada para o corpo (+X)
    t = n.cross(u)
    if t.y > 0:
        t = -t
    P = lambda a, b, c: W + u * a + n * b + t * c
    palm = [P(0.0, 0, 0), P(0.025, 0, 0), P(0.045, 0, 0), P(0.062, 0, 0)]
    tubo(S["soft_H"], palm, [(0.038, 0.024), (0.041, 0.026), (0.0435, 0.026), (0.041, 0.023)], 6, "couro", t, cap0=False, cap1=True)
    # cinta no dorso da mao + fivela
    anel(S["soft_H"], P(0.028, 0, 0), P(0.039, 0, 0), 0.0445, 0.0275, 8, "cinta", t)
    caixa(S["hard_H"], P(0.0335, -0.0295, 0), t, u, n, (0.012, 0.0095, 0.0035), "metal")
    cs = (0.0285, 0.0095, -0.0095, -0.0285)
    comp = (0.064, 0.070, 0.064, 0.052)
    rho = (0.0108, 0.0108, 0.0105, 0.0092)
    th = ((16, 62, 104), (16, 66, 108), (14, 60, 100), (10, 44, 80))
    for c, L_, r, tt in zip(cs, comp, rho, th):
        dedo_livre(S, P(0.058, 0.002, c), u, n, L_, tt, r)
        base = P(0.052, -0.0215 + (0.002 if r < 0.01 else 0), c)
        cone(S["soft_H"], base, u * 0.8 - n * 0.55, 0.0075 if r > 0.01 else 0.0062, 0.026 if r > 0.01 else 0.019, 5, "osso")
    # polegar recolhido
    base = P(0.020, 0.004, 0.040)
    d1 = (u * 0.9 + t * 0.30 + n * 0.25).normalized()
    d2 = (u * 0.65 + t * 0.10 + n * 0.75).normalized()
    p0 = base; p1 = p0 + d1 * 0.030; p2 = p1 + d2 * 0.028; p3 = p2 + (u * 0.3 + n * 0.95).normalized() * 0.022
    pm = p2 + (p3 - p2) * 0.2
    tubo(S["soft_H"], [p0, p1, pm], [(0.0128, 0.0128), (0.0128, 0.0128), (0.0136, 0.0136)], 5, "couro", n, cap0=False, cap1=True)
    tubo(S["soft_H"], [pm, p2, p3], [(0.0112, 0.0112), (0.0106, 0.0106), (0.0088, 0.0088)], 5, "pele", n, cap0=False, cap1=True)
    K = 1.16
    for Pt, i0 in ((S["soft_H"], n0), (S["hard_H"], h0)):
        for i in range(i0, len(Pt.v)):
            Pt.v[i] = W + (Pt.v[i] - W) * K
    return u, n, t
