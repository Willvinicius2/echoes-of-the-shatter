"""Exporta Arqueiro_Capuz.glb (v3, volume de pano): capuz verde-musgo com 5-6 dobras grandes caindo, aba da testa grossa,
ponta curva com flop, moldura de osso em placas chanfradas (V), mascara de cranio de corvo com crista dupla e bico longo,
olhos verdes grandes (amendoados, palpebras, sobrancelha), lenco enrolado e cabelo em mechas.
Geometria procedural, normais suaves (arestas vivas marcadas), tudo skinado ao osso Head (peso 1.0), Rig_Humanoid_Chibi.
Rodar: python pintar_capuz.py  (texturas)  e depois  blender -b -P build_capuz.py
Eixos Blender (Z-up): rosto olha para -Y, cabeca em (0, 0.06, 1.30). O capuz e construido no espaco antigo e
c.proporcao.aplicar() leva tudo para o chibi no fim.
"""
import os, sys, math, bisect, random
import bpy, bmesh
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c

TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "texturas_capuz")
C = Vector((0.0, 0.06, 1.30))  # centro da cabeca


# ---------- materiais ----------
def mat(nome, cor=None, tex=None, normal=None, rough=0.85, emis_png=None, emis=0.6, dupla=False):
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = 0.0

    def img(nome_png, cs):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEX, nome_png), check_existing=True)
        t.image.colorspace_settings.name = cs
        t.image.pack()
        return t
    if tex:
        t = img(tex, "sRGB")
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = cor
    if emis_png:
        e = img(emis_png, "sRGB")
        nt.links.new(e.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emis
    if normal:
        n = img(normal, "Non-Color")
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 1.0
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    m.use_backface_culling = not dupla
    return m


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ---------- capuz ----------
# abertura em V (losango achatado) em coordenadas unitarias (x, z) da esfera
POLY = [(0.0, 0.60), (-0.54, 0.28), (-0.70, -0.12), (-0.62, -0.64), (0.62, -0.64), (0.70, -0.12), (0.54, 0.28)]


def dentro(x, z):
    ok = False
    for (x1, z1), (x2, z2) in zip(POLY, POLY[1:] + POLY[:1]):
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            ok = not ok
    return ok


def raio_poly(phi):
    """distancia da origem ao contorno do POLY na direcao phi."""
    dx, dz = math.cos(phi), math.sin(phi)
    melhor = 9.0
    for (x1, z1), (x2, z2) in zip(POLY, POLY[1:] + POLY[:1]):
        ex, ez = x2 - x1, z2 - z1
        den = dx * ez - dz * ex
        if abs(den) < 1e-9:
            continue
        t = (x1 * ez - z1 * ex) / den
        s = (x1 * dz - z1 * dx) / den
        if t > 0 and -1e-6 <= s <= 1 + 1e-6:
            melhor = min(melhor, t)
    return melhor


D_PONTA = Vector((0, 0.50, 0.87)).normalized()


def fold_f(psi, z):
    """perfil das dobras (-1 vale vincado .. +1 crista redonda). Mesma formula em pintar_capuz.py (sombra pintada)."""
    ph = psi * 3.0 + 1.1 * z + (0.55 if psi > 0 else -0.55) + 0.7 * math.sin(psi * 2.0 + z * 2.0)
    return 2.0 * abs(math.sin(ph)) ** 1.15 - 1.0 + 0.30 * math.sin(psi * 7.0 + z * 3.3 + 0.7) + 0.15 * math.sin(psi * 11.0 + 1.3)


def dobra(p, folds=True):
    """deformacao do capuz em coordenadas unitarias: ponta curva com flop, aba da testa, dobras de pano, bainha."""
    p = p.copy()
    k = max(0.0, p.dot(D_PONTA)) ** 3.5
    p += D_PONTA * 1.0 * k
    p.y += 0.50 * k      # a ponta vai para tras
    p.z -= 0.55 * k      # e cai (flop)
    p.x += 0.10 * k * math.sin(p.z * 2.0 + 1.0)
    if p.y < 0 and p.z > 0.05:  # aba da testa grossa, projetada
        p.y -= 0.30 * min(1.0, (p.z - 0.05) / 0.5) * min(1.0, -p.y / 0.45)
    if p.z < -0.28:  # bainha alargada
        f = 1 + 0.16 * (-0.28 - p.z)
        p.x *= f; p.y *= f
    if folds:
        psi = math.atan2(p.x, -p.y)
        env = smoothstep(0.55, 1.35, abs(psi))
        zc = max(-0.6, min(1.0, p.z))
        kt = max(0.0, p.dot(D_PONTA))
        amp = 0.40 * env * (1 - 0.85 * smoothstep(0.35, 0.75, kt)) * (0.18 + 0.82 * smoothstep(0.85, -0.45, zc))
        f = fold_f(psi, zc)
        if p.z < -0.28:   # barra em ondas pendendo
            p.z -= 0.07 * env * (0.5 + 0.5 * f) * smoothstep(-0.28, -0.55, p.z)
        p *= 1 + amp * f
        # vinco do topo para a ponta (crista nas costas)
        vinco = math.exp(-(p.x / 0.20) ** 2) * smoothstep(0.1, 0.75, p.dot(D_PONTA))
        p *= 1 + 0.06 * vinco
        n = noise.noise(p * 1.7 + Vector((3, 1, 7)))
        p *= 1 + 0.025 * n
    return p


def esc(p, f=1.0):
    return Vector((p.x * 0.172 * f, p.y * 0.165 * f, p.z * 0.175 * f)) + C


def arco_len(pts):
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + (b - a).length)
    return cum


def amostra(pts, cum, s):
    s = max(0.0, min(cum[-1], s))
    i = min(bisect.bisect_right(cum, s) - 1, len(pts) - 2)
    f = (s - cum[i]) / max(1e-9, cum[i + 1] - cum[i])
    return pts[i].lerp(pts[i + 1], f)


def aresta_viva(bm, a, b):
    e = bm.edges.get((a, b))
    if e:
        e.smooth = False


PERFIL_MOLD = [(-1.0, 0.0), (-0.55, 1.0), (0.55, 1.0), (1.0, 0.0)]


def moldura(bm, uv, linha, rng):
    """borda de osso: placas chanfradas em V ao longo da abertura, com frestas (rachaduras) entre elas."""
    cum = arco_len(linha)
    L = cum[-1]
    Q = C + Vector((0, -0.10, 0.0))
    nplacas = 14
    pesos = [rng.uniform(0.55, 1.5) for _ in range(nplacas)]
    gap = 0.0065
    util = L - gap * (nplacas - 1)
    tot = sum(pesos)
    s = 0.0
    for idx in range(nplacas):
        comp = util * pesos[idx] / tot
        ta, tb = s, s + comp
        s = tb + gap
        wmul = rng.uniform(0.92, 1.18)
        skew = (rng.uniform(-1, 1), rng.uniform(-1, 1))
        v0 = rng.uniform(0.0, 0.7)
        aneis = []
        NR = 3
        for r in range(NR):
            fr = r / (NR - 1)
            sr = ta + comp * fr
            P = amostra(linha, cum, sr)
            tg = (amostra(linha, cum, sr + 0.006) - amostra(linha, cum, sr - 0.006)).normalized()
            n = (P - Q).normalized()
            sd = n.cross(tg).normalized()
            taper = 0.78 + 0.22 * math.sin(math.pi * (0.12 + 0.76 * fr)) ** 0.5
            w = 0.0195 * wmul * taper
            h = 0.009 * (0.85 + 0.15 * math.sin(math.pi * fr))
            anel = []
            for (wx, hy) in PERFIL_MOLD:
                kk = skew[0] if r == 0 else (skew[1] if r == NR - 1 else 0.0)
                if r == 0 or r == NR - 1:
                    Pk = amostra(linha, cum, sr + kk * wx * 0.016)
                    anel.append(bm.verts.new(Pk + sd * (wx * w) + n * (hy * h + 0.003)))
                else:
                    anel.append(bm.verts.new(P + sd * (wx * w) + n * (hy * h + 0.003)))
            aneis.append(anel)
        nk = len(PERFIL_MOLD)
        faces = []
        for r in range(NR - 1):
            for k in range(nk):
                q = [aneis[r][k], aneis[r][(k + 1) % nk], aneis[r + 1][(k + 1) % nk], aneis[r + 1][k]]
                f = bm.faces.new(q)
                f.material_index = 1
                faces.append((f, q, r, k))
        for (f, q, r, k) in faces:
            vv = lambda rr: v0 + 0.25 * rr / (NR - 1)
            uvs = [((PERFIL_MOLD[k][0] + 1) / 2 * 0.9 + 0.05, vv(r)),
                   ((PERFIL_MOLD[(k + 1) % nk][0] + 1) / 2 * 0.9 + 0.05, vv(r)),
                   ((PERFIL_MOLD[(k + 1) % nk][0] + 1) / 2 * 0.9 + 0.05, vv(r + 1)),
                   ((PERFIL_MOLD[k][0] + 1) / 2 * 0.9 + 0.05, vv(r + 1))]
            for l, uu in zip(f.loops, uvs):
                l[uv].uv = uu
            aresta_viva(bm, q[0], q[3])   # arestas longitudinais vivas = chanfro marcado
        for cap, rev in ((aneis[0], True), (aneis[-1], False)):
            f = bm.faces.new(cap[::-1] if rev else cap)
            f.material_index = 1
            for l in f.loops:
                l[uv].uv = (0.5, v0 + (0.0 if rev else 0.25))
            for a, b in zip(cap, cap[1:] + cap[:1]):
                aresta_viva(bm, a, b)


def hood(rng):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    bmesh.ops.create_uvsphere(bm, u_segments=34, v_segments=17, radius=1.0)
    bm.faces.ensure_lookup_table()
    morrer, marca = [], set()
    for f in bm.faces:
        p = f.calc_center_median()
        if p.y < -0.15 and dentro(p.x, p.z):
            morrer.append(f); marca.update(f.verts)
        elif p.z < -0.58:
            morrer.append(f)
    bmesh.ops.delete(bm, geom=morrer, context="FACES")
    borda = [v for v in marca if v.is_valid and v.link_faces]
    ang, zu = {}, {}
    for v in borda:
        phi = math.atan2(v.co.z, v.co.x)
        r = raio_poly(phi)
        x, z = r * math.cos(phi), r * math.sin(phi)
        v.co.x, v.co.z = x, z
        v.co.y = -math.sqrt(max(0.02, 1 - x * x - z * z))
        ang[v] = (phi + math.pi / 3) % (2 * math.pi)
        zu[v] = z
    # UV (u = angulo, 0.5 frente; v = altura) com os valores ANTES da deformacao
    for f in bm.faces:
        us = []
        for l in f.loops:
            co = l.vert.co
            us.append(math.atan2(co.x, -co.y) / (2 * math.pi) + 0.5)
        if max(us) - min(us) > 0.5:
            us = [u + 1 if u < 0.25 else u for u in us]
        for l, u in zip(f.loops, us):
            l[uv].uv = (u, (max(-1.0, min(1.0, l.vert.co.z)) + 1) / 2 * 0.96 + 0.02)
    for v in bm.verts:
        v.co = esc(dobra(v.co))
    # borda enrolada: os vertices da abertura sobem um pouco (labio grosso de pano)
    Q = C + Vector((0, -0.10, 0.0))
    ordem = [v for v, a in sorted(ang.items(), key=lambda kv: kv[1]) if zu[v] > -0.50]
    for v in ordem:
        v.co += (v.co - Q).normalized() * 0.010
    linha = [v.co.copy() for v in ordem]
    # alisa a linha (media movel) para as placas nao seguirem o serrilhado da malha
    lis = []
    for i in range(len(linha)):
        a = linha[max(0, i - 1)]; b = linha[i]; d = linha[min(len(linha) - 1, i + 1)]
        lis.append(a * 0.25 + b * 0.5 + d * 0.25 if 0 < i < len(linha) - 1 else b)
    moldura(bm, uv, lis, rng)
    # casca interna escura (baixa resolucao) para o interior do capuz nao ficar vazado
    bm2 = bmesh.new()
    bmesh.ops.create_uvsphere(bm2, u_segments=12, v_segments=7, radius=1.0)
    mor2 = [f for f in bm2.faces if (f.calc_center_median().y < -0.15 and dentro(f.calc_center_median().x, f.calc_center_median().z)) or f.calc_center_median().z < -0.38]
    bmesh.ops.delete(bm2, geom=mor2, context="FACES")
    mp_v = {}
    for v in bm2.verts:
        mp_v[v] = bm.verts.new(esc(dobra(v.co, folds=False), 0.78))
    for f in bm2.faces:
        nf = bm.faces.new([mp_v[v] for v in f.verts])
        nf.material_index = 2
        nf.normal_flip()  # normais para dentro (para o rosto)
        for l in nf.loops:
            l[uv].uv = (0.5, 0.5)
    bm2.free()
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f.material_index == 0])
    me = bpy.data.meshes.new("SK_Archer_Capuz")
    bm.to_mesh(me); bm.free()
    return me


# ---------- mascara ----------
SS = [0.0, 0.06, 0.13, 0.21, 0.30, 0.40, 0.52, 0.64, 0.76, 0.87, 0.95, 1.0]
# secao transversal (xn, nn): aresta, asa, asa, CRISTA D, encosta, VALE do V, encosta, CRISTA E, asa, asa, aresta, verso x3
SECAO = [(1.0, 0.0), (0.84, 0.30), (0.55, 0.62), (0.26, 1.35), (0.07, 0.80), (0.0, 0.30),
         (-0.07, 0.80), (-0.26, 1.35), (-0.55, 0.62), (-0.84, 0.30), (-1.0, 0.0),
         (-0.55, -0.55), (0.0, -0.75), (0.55, -0.55)]
IDX_ARESTA = (0, 10)
UK = [k / 10 * 0.5 for k in range(11)] + [0.625, 0.75, 0.875]   # u da textura por vertice da secao


def lerp_tab(tab, x):
    for (a, va), (b, vb) in zip(tab, tab[1:]):
        if x <= b:
            return va + (vb - va) * (x - a) / (b - a)
    return tab[-1][1]


Y0 = -0.100


def perfil(s):
    pts_w = [(0, 0.064), (0.06, 0.088), (0.13, 0.102), (0.22, 0.090), (0.32, 0.064), (0.46, 0.040), (0.60, 0.028), (0.80, 0.015), (1.0, 0.0015)]
    pts_d = [(0, 0.016), (0.15, 0.022), (0.35, 0.029), (0.60, 0.026), (0.85, 0.015), (1.0, 0.004)]
    w, dd = lerp_tab(pts_w, s), lerp_tab(pts_d, s)
    y = Y0 - 0.125 * s ** 1.7
    z = 1.390 - 0.225 * s - 0.012 * math.sin(s * math.pi)
    return w, dd, y, z


def ponto(s, k, folga=0.0):
    w, dd, y, z = perfil(s)
    xn, nn = SECAO[k]
    if k in (1, 2, 8, 9) and 0.10 < s < 0.34:   # orbitas fundas
        nn *= 0.28
    if k in (3, 7) and 0.0 < s:                 # cristas gemeas convergem para o bico
        xn *= 1.0 - 0.55 * s
    if k in (4, 5, 6):                           # o V do meio vai sumindo no bico
        alvo = 1.10 if k != 5 else 1.10
        nn += (alvo - nn) * smoothstep(0.55, 1.0, s)
        if k in (4, 6):
            xn *= 1.0 - 0.5 * s
    x = (w + folga) * xn
    s2 = min(1.0, s + 0.01)
    _, _, y2, z2 = perfil(s2)
    t = Vector((0, y2 - y, z2 - z)).normalized()
    fw = Vector((0, -t.z, t.y))
    if fw.y > 0:
        fw = -fw
    wrap = 0.030 * (x / 0.07) ** 2 * (1 - smoothstep(0.25, 0.55, s))
    return Vector((x, y, z)) + fw * ((dd + folga) * nn) + Vector((0, wrap, 0))


def laje(bm, uv, c0, ex, ey, en, w, l, h, inset, mi, uvc=(0.5, 0.5)):
    """placa de osso chanfrada (tronco de piramide) assentada na mascara; ex/ey eixos no plano, en normal."""
    base = [c0 + ex * (sx * w) + ey * (sy * l) - en * 0.004 for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    topo = [c0 + ex * (sx * w * inset) + ey * (sy * l * inset) + en * h for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    vb = [bm.verts.new(p) for p in base]
    vt = [bm.verts.new(p) for p in topo]
    quads = [[vb[0], vb[1], vt[1], vt[0]], [vb[1], vb[2], vt[2], vt[1]], [vb[2], vb[3], vt[3], vt[2]],
             [vb[3], vb[0], vt[0], vt[3]], [vt[0], vt[1], vt[2], vt[3]]]
    for q in quads:
        f = bm.faces.new(q)
        f.material_index = mi
        f.normal_update()
        if f.normal.dot(f.calc_center_median() - c0) < 0:
            f.normal_flip()
        for l_ in f.loops:
            l_[uv].uv = uvc


def mascara(rng):
    bm = bmesh.new()
    N = len(SECAO)
    uv = bm.loops.layers.uv.verify()
    aneis = [[bm.verts.new(ponto(s, k)) for k in range(N)] for s in SS]
    # UV: u = k/(N-1)*0.5 (frente), v = 1 - s
    for i in range(len(SS) - 1):
        for k in range(N):
            k2 = (k + 1) % N
            q = [aneis[i][k], aneis[i][k2], aneis[i + 1][k2], aneis[i + 1][k]]
            ua = UK[k]
            ub = UK[k2] if k2 != 0 else 1.0
            vv0, vv1 = 1 - SS[i], 1 - SS[i + 1]
            f = bm.faces.new(q); f.material_index = 0
            for l, (u, v) in zip(f.loops, [(ua, vv0), (ub, vv0), (ub, vv1), (ua, vv1)]):
                l[uv].uv = (u, v)
            if k in IDX_ARESTA or k2 in IDX_ARESTA:
                if k in IDX_ARESTA:
                    aresta_viva(bm, aneis[i][k], aneis[i + 1][k])
    f = bm.faces.new(aneis[0][::-1]); f.material_index = 0
    for l in f.loops: l[uv].uv = (0.25, 1.0)
    f = bm.faces.new(aneis[-1]); f.material_index = 0
    for l in f.loops: l[uv].uv = (0.25, 0.0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    # placas de osso na testa e entre os olhos (assentadas sobre as cristas, inclinadas como o V)
    for sx in (-1, 1):
        k = 3 if sx > 0 else 7
        for s0, w, l, h, rot in ((0.060, 0.026, 0.010, 0.0045, 12), (0.150, 0.020, 0.009, 0.004, 8)):
            P = ponto(s0, k)
            P2 = ponto(min(1.0, s0 + 0.02), k)
            ey = (P2 - P).normalized()
            en = Vector((1, 0, 0)).cross(ey).normalized()
            if en.y > 0:
                en = -en
            ex = ey.cross(en).normalized()
            if ex.x * sx < 0:
                ex = -ex
            r = math.radians(rot * sx)
            ex2 = ex * math.cos(r) + ey * math.sin(r)
            ey2 = ey * math.cos(r) - ex * math.sin(r)
            laje(bm, uv, P, ex2, ey2, en, w, l, h, 0.86, 0, (0.14, 0.52))
    me = bpy.data.meshes.new("SK_Archer_Mascara")
    bm.to_mesh(me); bm.free()
    return me


# ---------- rosto (pele, olhos, palpebras, lenco, cabelo) ----------
def uvq(l, uv, u, v, quad=0):
    ox, oy = [(0, 0.5), (0.5, 0.5), (0, 0), (0.5, 0)][quad]
    l[uv].uv = (ox + u * 0.5 * 0.96 + 0.02, oy + v * 0.5 * 0.96 + 0.02)


EYE_Y = -0.090
EYE_Z = 1.312


def olho(bm, uv, sx):
    a, b = 0.050, 0.029
    ce = Vector((0.074 * sx, EYE_Y, EYE_Z))
    tilt = math.radians(11) * sx  # canto externo mais alto
    def P(t, rr=1.0, dy=0.0):
        x = a * math.cos(t) * rr
        z = b * math.sin(t) * (1 - 0.34 * abs(math.cos(t))) * rr
        xr = x * math.cos(tilt) - z * math.sin(tilt)
        zr = x * math.sin(tilt) + z * math.cos(tilt)
        return Vector((xr, dy, zr)) + ce, (0.5 + 0.5 * x / a / max(rr, 1e-6) * rr, 0.5 + 0.5 * z / b / max(rr, 1e-6) * rr)
    NJ = 12
    cent = bm.verts.new(ce + Vector((0, -0.007, 0)))
    ring1, ring2 = [], []
    for j in range(NJ):
        t = 2 * math.pi * j / NJ
        p1, u1 = P(t, 0.55, -0.0045)
        p2, u2 = P(t, 1.0, 0.0)
        ring1.append((bm.verts.new(p1), u1)); ring2.append((bm.verts.new(p2), u2))
    def face(q, uvs, mi):
        f = bm.faces.new(q); f.material_index = mi
        f.normal_update()
        if f.normal.y > 0:
            f.normal_flip()
        mp = {id(v): u for v, u in zip(q, uvs)}
        for l in f.loops:
            l[uv].uv = mp[id(l.vert)]
        return f
    for j in range(NJ):
        j2 = (j + 1) % NJ
        face([cent, ring1[j2][0], ring1[j][0]], [(0.5, 0.5), ring1[j2][1], ring1[j][1]], 1)
        face([ring1[j][0], ring1[j2][0], ring2[j2][0], ring2[j][0]], [ring1[j][1], ring1[j2][1], ring2[j2][1], ring2[j][1]], 1)
    # palpebra superior grossa (arco acima do contorno)
    top = []
    for j in range(8):
        t = math.pi * j / 7
        pos, _ = P(t)
        e = math.sin(t)
        top.append((bm.verts.new(pos + Vector((0, -0.0035, 0.0))), bm.verts.new(pos + Vector((0, -0.0085, 0.0085 * e + 0.003)))))
    for j in range(7):
        f = bm.faces.new([top[j][0], top[j + 1][0], top[j + 1][1], top[j][1]]); f.material_index = 2
        f.normal_update()
        if f.normal.y > 0: f.normal_flip()
        for l in f.loops: uvq(l, uv, 0.5, 0.5, 3)
    # palpebra inferior fina
    bot = []
    for j in range(6):
        t = math.pi + math.pi * j / 5
        pos, _ = P(t)
        bot.append((bm.verts.new(pos + Vector((0, -0.003, 0))), bm.verts.new(pos + Vector((0, -0.005, -0.0045 * abs(math.sin(t)) - 0.0015)))))
    for j in range(5):
        f = bm.faces.new([bot[j][0], bot[j + 1][0], bot[j + 1][1], bot[j][1]]); f.material_index = 2
        f.normal_update()
        if f.normal.y > 0: f.normal_flip()
        for l in f.loops: uvq(l, uv, 0.5, 0.5, 3)
    # sobrancelha: fita inclinada, mais grossa no meio, acima da palpebra
    br = []
    for j in range(6):
        t = j / 5
        x = (-0.038 + 0.088 * t) * 1.0
        zc = 0.0285 + 0.010 * math.sin(t * math.pi) + 0.006 * t
        pc = Vector((x, -0.0, zc))
        xr = pc.x * math.cos(tilt) - pc.z * math.sin(tilt)
        zr = pc.x * math.sin(tilt) + pc.z * math.cos(tilt)
        base = Vector((xr * 1.0, EYE_Y - 0.008, zr)) + Vector((ce.x, 0, ce.z))
        w = 0.0075 * (0.5 + 0.5 * math.sin(math.pi * (0.1 + 0.8 * t)))
        br.append((bm.verts.new(base + Vector((0, 0, -w))), bm.verts.new(base + Vector((0, -0.002, w)))))
    for j in range(5):
        f = bm.faces.new([br[j][0], br[j + 1][0], br[j + 1][1], br[j][1]]); f.material_index = 2
        f.normal_update()
        if f.normal.y > 0: f.normal_flip()
        for l in f.loops: uvq(l, uv, 0.5, 0.5, 1)


def rosto():
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    # pele (ovoide atras da mascara) - slot 0
    g = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
    for v in g["verts"]:
        v.co = Vector((v.co.x * 0.118, v.co.y * 0.090, v.co.z * 0.095)) + Vector((0, -0.016, 1.302))
    for f in bm.faces:
        f.material_index = 0
        for l in f.loops: uvq(l, uv, 0.5, 0.5, 2)
    for sx in (-1, 1):
        olho(bm, uv, sx)
    # lenco: rolos de pano em volta da boca e do nariz (slot 2), com pregas diagonais
    cols, rows = 12, 7
    gv = []
    for j in range(rows + 1):
        t = j / rows
        fila = []
        for i in range(cols + 1):
            span = 118 - 34 * t
            a = math.radians(-span + 2 * span * i / cols)
            fr = math.cos(a) ** 2
            ztopo = 1.282 + 0.030 * fr - 0.020 * (1 - fr)
            zbase = 1.212 - 0.055 * fr + 0.014 * math.sin(i * 1.3)
            z = ztopo + (zbase - ztopo) * t
            r = (0.092 + 0.012 * t + 0.016 * abs(math.sin(3 * math.pi * t + 0.9 * a)) + 0.003 * math.sin(i * 1.7 + j))
            fila.append(bm.verts.new(Vector((math.sin(a) * r * 1.04, -math.cos(a) * r * 1.0 - 0.006, z))))
        gv.append(fila)
    for j in range(rows):
        for i in range(cols):
            q = [gv[j][i], gv[j][i + 1], gv[j + 1][i + 1], gv[j + 1][i]]
            f = bm.faces.new(q); f.material_index = 2
            for l, (u, v) in zip(f.loops, [(i / cols, 1 - j / rows), ((i + 1) / cols, 1 - j / rows), ((i + 1) / cols, 1 - (j + 1) / rows), (i / cols, 1 - (j + 1) / rows)]):
                uvq(l, uv, u, v, 0)
    # mechas de cabelo: fitas curvas nas laterais da testa (slot 2)
    mechas = [(-1, 0.092, 1.392, 0.075, 0.012), (-1, 0.104, 1.372, 0.070, 0.020), (-1, 0.080, 1.380, 0.050, 0.008),
              (1, 0.094, 1.394, 0.065, -0.010), (1, 0.106, 1.366, 0.075, -0.018), (1, 0.082, 1.382, 0.048, -0.008)]
    for sx, x0, z0, comp, curva in mechas:
        vs = []
        for k in range(4):
            t = k / 3
            p = Vector((sx * (x0 + 0.010 * t + curva * math.sin(t * 3.0)), -0.092 + 0.022 * t, z0 - comp * t))
            w = 0.0130 * [0.40, 1.0, 0.70, 0.12][k]
            vs.append((bm.verts.new(p + Vector((-w, 0, 0))), bm.verts.new(p + Vector((w, 0, 0)))))
        for k in range(3):
            f = bm.faces.new([vs[k][0], vs[k][1], vs[k + 1][1], vs[k + 1][0]])
            f.material_index = 2
            for l, (u, v) in zip(f.loops, [(0.2, k / 3), (0.8, k / 3), (0.8, (k + 1) / 3), (0.2, (k + 1) / 3)]):
                uvq(l, uv, u, v, 1)
    me = bpy.data.meshes.new("SK_Archer_Rosto")
    bm.to_mesh(me); bm.free()
    return me


# ---------- montagem ----------
def objeto(me, nome, arm, mats):
    ob = bpy.data.objects.new(nome, me)
    bpy.context.scene.collection.objects.link(ob)
    for m in mats:
        me.materials.append(m)
    vg = ob.vertex_groups.new(name="Head")
    vg.add([v.index for v in me.vertices], 1.0, "REPLACE")
    ob.parent = arm
    md = ob.modifiers.new("Armature", "ARMATURE"); md.object = arm
    return ob


def main():
    rng = random.Random(7)
    c.limpar()
    c.importar(f"{c.FINAL}/SK_Archer_Head_Starter.fbx")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    antigas = [o for o in bpy.data.objects if o.type == "MESH"]
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    arm.animation_data_clear()
    c.aplicar_rotacao([arm] + antigas)
    for o in antigas:
        bpy.data.objects.remove(o)
    m_capuz = mat("M_Arqueiro_Capuz", tex="T_Capuz_BC.png", normal="T_Capuz_N.png", rough=0.93, dupla=True)
    m_ouro = mat("M_Arqueiro_CapuzOuro", tex="T_Ouro_BC.png", normal="T_Ouro_N.png", rough=0.55, dupla=True)
    m_int = mat("M_Arqueiro_CapuzInterior", cor=(0.022, 0.040, 0.022, 1), rough=0.95, dupla=True)
    m_masc = mat("M_Arqueiro_Mascara", tex="T_Mascara_BC.png", normal="T_Mascara_N.png", rough=0.55)
    m_det = mat("M_Arqueiro_CapuzDetalhe", tex="T_CapuzDetalhe_BC.png", rough=0.9, dupla=True)
    m_olho = mat("M_Arqueiro_OlhoVerde", tex="T_Olho_BC.png", rough=0.2, emis_png="T_Olho_E.png", emis=0.7)
    ob = objeto(hood(rng), "SK_Archer_Capuz", arm, [m_capuz, m_ouro, m_int])
    for p in ob.data.polygons:
        p.use_smooth = True
    mk = objeto(mascara(rng), "SK_Archer_Mascara", arm, [m_masc, m_ouro])
    for p in mk.data.polygons:
        p.use_smooth = (p.material_index == 0)
    ro = objeto(rosto(), "SK_Archer_Rosto", arm, [m_det, m_olho, m_det])
    for p in ro.data.polygons:
        p.use_smooth = True
    tris = 0
    for o in (ob, mk, ro):
        t = sum(len(p.vertices) - 2 for p in o.data.polygons)
        print("TRIS", o.name, t); tris += t
    print("TRIS_TOTAL", tris)
    vs = [v.co for o in (ob, mk, ro) for v in o.data.vertices]
    print("BOUNDS", [round(min(v[i] for v in vs), 3) for i in range(3)], [round(max(v[i] for v in vs), 3) for i in range(3)])
    c.proporcao.aplicar(arm, [ob, mk, ro])   # mesma deformacao chibi do corpo: a cabeca maior leva o capuz junto
    c.exportar("Arqueiro_Capuz.glb", [arm, ob, mk, ro])


main()
