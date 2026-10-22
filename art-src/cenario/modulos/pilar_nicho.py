"""Nicho frontal (+Y) do pilar da Cripta: cortador ogival, moldura em duas ordens de aduelas (com filete escuro entre elas),
mísulas e pedra-chave salientes, tímpano, fundo de blocos retos com juntas, plinto próprio em dois degraus, estátua
encapuzada (capuz de volume com cavidade e rosto liso, braços cruzados em X com mangas em pregas, mãos de dedos em bloco)
e espada de ponta para baixo. Usa só pilar_lib (L). Coordenadas do pilar: centro (0,0), face frontal y=0.95."""
import math
import bmesh
from mathutils import Vector, Matrix, noise

Z0 = 1.25           # piso do nicho
W = 0.55            # meia-largura útil
HS = 1.60           # altura dos lados antes da ponta
R = 2 * W           # raio das curvas ogivais
ATIP = math.acos((R - W) / R)
FACE = 0.95
BACK = 0.45         # plano do fundo do nicho (profundidade 0.5 m)
SX, SY, SZ = 0.0, 0.69, 1.49   # origem local da estátua (centro, y, topo do plinto)
S = 1.10                       # escala da estátua (altura ~2.18 m)
YF = 0.88                      # achatamento em Y (estátua de nicho, menos funda)
OUT = 0.32                     # espessura total das duas ordens da moldura


def _poly(L, n=10):
    return [(x, z + Z0) for x, z in L.ogive(W, HS, 0, n)]


def cutter(L):
    """Prisma ogival (largura 1.1 m, altura ~2.55 m a partir de z=1.25) até y=0.45, para subtrair do núcleo."""
    return L.prism(_poly(L, 12), BACK, FACE + 0.2, L.MAT["escura"])


# ---------------------------------------------------------------- utilitários
def _arch_top(x):
    """Altura (z) do contorno da abertura em x, relativa ao piso do nicho."""
    x = abs(x)
    if x >= W: return HS
    return HS + math.sqrt(max(0.0, R * R - (x + W) ** 2))


def _prof(tab, z):
    if z <= tab[0][0]: return tab[0][1]
    for (z0, v0), (z1, v1) in zip(tab, tab[1:]):
        if z <= z1: return v0 + (v1 - v0) * (z - z0) / (z1 - z0)
    return tab[-1][1]


def _sharp(bm, ang=0.30):
    """Marca arestas vivas (ângulo grande) para o sombreado liso não amaciar as dobras."""
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > ang: e.smooth = False


def _mesh(L, bm, mats, name):
    """Fecha o bmesh num objeto; mats = lista de materiais (índice por face)."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _sharp(bm)
    o = L.from_bm(bm, mats[0], name)
    for m in mats[1:]: o.data.materials.append(m)
    o["liso"] = 1
    return o


def _grid(L, rings, mats, name, closed_u=True, closed_v=False, cap0=True, cap1=True, midx=None):
    """Malha em grade: rings = lista de anéis (listas de Vector). midx(j,i) -> índice de material da face."""
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(vs[0]); m = len(vs)
    for j in range(m - 1 + (1 if closed_v else 0)):
        a, b = vs[j], vs[(j + 1) % m]
        for i in range(n if closed_u else n - 1):
            f = bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
            if midx: f.material_index = midx(j, i)
    if cap0 and not closed_v: bm.faces.new(vs[0][::-1])
    if cap1 and not closed_v: bm.faces.new(vs[-1])
    return _mesh(L, bm, mats, name)


def _sm(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _box(L, c, size, m, ex=(1, 0, 0), ez=(0, 0, 1), bev=0.006, scale=True):
    """Bloco simples orientado (ex = eixo longo, ez = 'para cima'), com chanfro; size em unidades locais da estátua."""
    ex = Vector(ex).normalized(); ez = Vector(ez)
    ey = ez.cross(ex).normalized(); ez = ex.cross(ey).normalized()
    k = S if scale else 1.0
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0] * k, v.co.y * size[1] * k, v.co.z * size[2] * k))
    if bev: L.bevel_bm(bm, min(bev * k, 0.3 * min(size) * k), 1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    R3 = Matrix((ex, ey, ez)).transposed().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ R3, verts=bm.verts)
    return L.from_bm(bm, m, "bloco")


# ---------------------------------------------------------------- moldura em aduelas
def _split(total, base, seed):
    n = max(2, round(total / base))
    ws = [0.8 + 0.4 * ((math.sin(seed * 7.3 + i * 2.9) + 1) / 2) for i in range(n)]
    k = total / sum(ws)
    return [w * k for w in ws]


def _blocks_along(L, o0, o1, y1, seed_len, chip=0.014, side=1, base_len=0.34, m=None, y0=None):
    """Anel de blocos que acompanha a ogiva (lado reto + arco) entre os recuos o0..o1 da abertura, de um lado (side=±1).
    y1 = frente da ordem; y0 = trás (padrão: embutido 7 cm no núcleo)."""
    M = m or L.MAT["pedra"]
    thick = o1 - o0
    y0 = FACE - 0.07 if y0 is None else y0
    depth = y1 - y0
    yc = (y1 + y0) / 2
    ext = 0.10
    total = HS + ext
    cuts = _split(total, base_len, seed_len)
    z = -ext
    for ln in cuts:
        ln_v = ln - 0.016
        t = thick * L.rnd.choice([0.94, 1.0, 1.05])
        L.rock((side * (W + o0 + t / 2), yc, Z0 + z + ln / 2), (t, depth, ln_v), M, chip=chip, rough=0.0, bev=0.014, cuts_pre=1, seg=1)
        z += ln
    omid = (o0 + o1) / 2
    arc = (R + omid) * ATIP
    cuts = _split(arc, base_len * 0.95, seed_len + 1)
    s = 0.0
    for ln in cuts:
        a = (s + ln / 2) / (R + omid)
        t = thick * L.rnd.choice([0.96, 1.0, 1.06])
        rr = R + o0 + t / 2
        c = (side * (-W + rr * math.cos(a)), yc, Z0 + HS + rr * math.sin(a))
        rot = -a if side > 0 else a
        L.rock(c, (t, depth, ln - 0.016), M, rot=(0, rot, 0), chip=chip, rough=0.0, bev=0.014, cuts_pre=1, seg=1)
        s += ln


def _frame(L):
    P_, E_ = L.MAT["pedra"], L.MAT["escura"]
    for side in (-1, 1):
        # ordem interna (recuada), filete escuro e ordem externa 10 cm mais saliente
        _blocks_along(L, 0.0, 0.12, FACE + 0.035, 3 + side, side=side)
        _blocks_along(L, 0.12, 0.155, FACE + 0.012, 21 + side, side=side, m=E_, base_len=0.5, chip=0.006)
        _blocks_along(L, 0.155, OUT, FACE + 0.14, 11 + side, side=side)
    # pedra-chave: bloco alto que atravessa as duas ordens, mais saliente que tudo
    rk = R + (0.0 + OUT) / 2
    zk = Z0 + HS + math.sqrt(rk * rk - W * W)
    L.rock((0, FACE + 0.085, zk), (0.24, 0.30, 0.40), P_, chip=0.02, rough=0.004, bev=0.018, cuts_pre=1, seg=1)
    L.rock((0, FACE + 0.19, zk - 0.02), (0.17, 0.10, 0.30), P_, chip=0.016, rough=0.004, bev=0.014, cuts_pre=1, seg=1)
    L.rock((0, FACE + 0.19, zk + 0.215), (0.30, 0.15, 0.06), P_, chip=0.012, rough=0.003, bev=0.012, cuts_pre=1, seg=1)  # capitel da chave
    # mísulas sob o arranque do arco, em degraus que avançam
    zs = Z0 + HS
    for side in (-1, 1):
        cx = side * (W + 0.15)
        L.rock((cx, FACE + 0.105, zs + 0.0), (0.46, 0.31, 0.10), P_, chip=0.02, rough=0.004, bev=0.014, cuts_pre=1, seg=1)
        L.rock((cx, FACE + 0.105, zs - 0.105), (0.38, 0.28, 0.10), P_, chip=0.018, rough=0.004, bev=0.012, cuts_pre=1, seg=1)
        L.rock((cx, FACE + 0.09, zs - 0.21), (0.28, 0.24, 0.10), E_, chip=0.016, rough=0.004, bev=0.012, cuts_pre=1, seg=1)
        L.rock((cx, FACE + 0.08, zs - 0.31), (0.19, 0.20, 0.10), P_, chip=0.014, rough=0.003, bev=0.01, cuts_pre=1)
        L.rock((cx, FACE + 0.07, zs - 0.405), (0.11, 0.17, 0.09), E_, chip=0.01, rough=0.003, bev=0.01, cuts_pre=1)
    # soleira em frente ao nicho
    L.rock((0, FACE + 0.07, Z0 - 0.06), (1.46, 0.24, 0.12), P_, chip=0.03, rough=0.005, bev=0.02, cuts_pre=2, seg=1)


def _tympanum(L):
    """Placa em relevo acima do arco com rosácea de quatro lóbulos."""
    ytop = Z0 + HS + math.sqrt((R + OUT) ** 2 - W * W)
    zc = ytop + 0.19
    yb = FACE + 0.01
    L.rock((0, yb + 0.035, zc), (0.74, 0.09, 0.30), L.MAT["pedra"], chip=0.02, rough=0.004, bev=0.014, cuts_pre=2, seg=1)
    L.rock((0, yb + 0.075, zc + 0.135), (0.66, 0.04, 0.035), L.MAT["escura"], bev=0.008)
    L.rock((0, yb + 0.075, zc - 0.135), (0.66, 0.04, 0.035), L.MAT["escura"], bev=0.008)
    _rosette(L, 0.0, yb + 0.08, zc, 0.085)


def _disc(L, cx, y, cz, r, depth, mat, n=12):
    p0 = [Vector((cx + r * math.cos(a), y, cz + r * math.sin(a))) for a in [2 * math.pi * i / n for i in range(n)]]
    p1 = [Vector((cx + r * 0.82 * math.cos(a), y + depth, cz + r * 0.82 * math.sin(a))) for a in [2 * math.pi * i / n for i in range(n)]]
    bm = bmesh.new()
    a = [bm.verts.new(p) for p in p0]; b = [bm.verts.new(p) for p in p1]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return L.from_bm(bm, mat, "disc")


def _rosette(L, cx, y, cz, r):
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        _disc(L, cx + r * math.cos(a), y, cz + r * math.sin(a), r * 0.62, 0.05, L.MAT["escura"], 10)
    _disc(L, cx, y, cz, r * 0.42, 0.065, L.MAT["pedra"], 10)


# ---------------------------------------------------------------- fundo do nicho, plinto
def _back(L):
    """Fundo de blocos retos escuros com juntas (parede em y≈0.5), arco interno em relevo e rosáceas."""
    yb = BACK + 0.02
    mort = L.prism([(x * 0.995, (z - Z0) * 0.995 + Z0) for x, z in _poly(L, 12)], BACK - 0.01, yb + 0.03, L.MAT["escura"])
    z = Z0
    row = 0
    while z < Z0 + HS + 1.05:
        h = [0.34, 0.30, 0.38, 0.32][row % 4]
        x = -0.62 + (0.0 if row % 2 else 0.19)
        while x < 0.62:
            ln = L.rnd.choice([0.36, 0.44, 0.40, 0.52])
            xe = min(x + ln, 0.62)
            xc = (x + xe) / 2
            top = Z0 + _arch_top(max(abs(x), abs(xe)) * 0.96)
            if z + 0.05 < top + 0.02 and z < top - 0.03:
                m = L.MAT["pedra"] if L.rnd.random() < 0.22 else L.MAT["escura"]
                L.rock((xc, yb + 0.05, z + h / 2), (xe - x - 0.03, 0.10, h - 0.03), m, chip=0.008, rough=0.0, bev=0.01, cuts_pre=1)
            x = xe
        z += h
        row += 1
    for side in (-1, 1):
        o0, o1 = -0.13, -0.05
        omid = (o0 + o1) / 2
        arc = (R + omid) * ATIP
        s = 0.0
        for ln in _split(arc, 0.28, 5 + side):
            a = (s + ln / 2) / (R + omid)
            rr = R + omid
            c = (side * (-W + rr * math.cos(a)), yb + 0.115, Z0 + HS + rr * math.sin(a))
            L.rock(c, (o1 - o0, 0.05, ln - 0.014), L.MAT["pedra"], rot=(0, -a if side > 0 else a, 0), chip=0.01, rough=0.003, bev=0.008, cuts_pre=1)
            s += ln
        L.rock((side * (W - 0.09), yb + 0.115, Z0 + HS / 2 + 0.05), (0.08, 0.05, HS - 0.1), L.MAT["pedra"], chip=0.01, bev=0.008, cuts_pre=1)
        _rosette(L, side * 0.43, yb + 0.115, 3.0, 0.07)


def _plinth(L):
    """Plinto próprio: bloco de pedra em dois degraus com filete escuro e cantos lascados, avançado até a frente do nicho."""
    M, E = L.MAT["pedra"], L.MAT["escura"]
    L.rock((0, 0.72, Z0 + 0.06), (1.02, 0.54, 0.12), M, chip=0.04, rough=0.006, bev=0.024, cuts_pre=2, seg=1)        # degrau 1
    L.rock((0, 0.725, Z0 + 0.125), (0.90, 0.50, 0.035), E, chip=0.0, rough=0.0, bev=0.008, seg=1)                     # filete escuro entre degraus
    L.rock((0, 0.73, Z0 + 0.18), (0.84, 0.46, 0.12), M, chip=0.035, rough=0.006, bev=0.022, cuts_pre=2, seg=1)         # degrau 2
    for sx in (-1, 1):                                    # lascas e pedaços caídos
        L.rock((sx * 0.50, 0.99, Z0 + 0.03), (0.12, 0.10, 0.06), M, rot=(0.2, 0.3, 0.7 * sx), chip=0.02, rough=0.005, bev=0.01, cuts_pre=1, seg=1)
    L.rock((0.30, 1.0, Z0 + 0.12), (0.09, 0.07, 0.05), M, rot=(0.1, 0.5, 0.4), chip=0.012, bev=0.008, cuts_pre=1, seg=1)


# ---------------------------------------------------------------- estátua
def P(x, y, z):
    return Vector((SX + x * S, SY + y * S * YF, SZ + z * S))


def _pleat(t, z, k, depth, phase=0.0, warp=0.12):
    """Prega viva: sulco em V (abs(sin)) com crista larga; retorna recuo radial em metros (>=0)."""
    tw = t + warp * math.sin(2.1 * z + 1.3 * math.cos(t) + phase)
    g = abs(math.sin(k * tw + phase)) ** 0.5
    return depth * (1.0 - g)


_RX = [(0, 0.46), (0.05, 0.44), (0.3, 0.385), (0.6, 0.32), (0.9, 0.29), (1.15, 0.30), (1.28, 0.33), (1.36, 0.26), (1.42, 0.14)]
_RY = [(0, 0.21), (0.05, 0.20), (0.3, 0.19), (0.6, 0.175), (0.9, 0.16), (1.15, 0.16), (1.28, 0.17), (1.36, 0.14), (1.42, 0.10)]


def _manto(L):
    N = 72; rows = 34; ZT = 1.42
    rings = []
    for j in range(rows + 1):
        z = ZT * j / rows
        rx, ry = _prof(_RX, z), _prof(_RY, z)
        depth = 0.045 + 0.085 * (1 - z / ZT)
        ring = []
        for i in range(N):
            t = 2 * math.pi * i / N
            c, s = math.cos(t), math.sin(t)
            d = _pleat(t, z, 8, depth, 0.3) + _pleat(t, z, 13, depth * 0.38, 1.7, 0.2)
            kick = max(0.0, 0.07 - z) * 0.5
            zz = z
            if j == 0:
                zz = 0.005 + 0.012 * (noise.noise(Vector((c * 2, s * 2, 3.1))) + 0.4) + 0.012 * abs(math.sin(5 * t))
            ring.append(P((rx - d + kick) * c, (ry - d + kick) * s, zz))
        rings.append(ring)
    o = _grid(L, rings, [L.MAT["estatua"]], "manto", cap0=True, cap1=True)
    _chisel(o, 0.003)
    return o


def _chisel(o, a):
    """Irregularidade fina de cinzel."""
    for v in o.data.vertices:
        v.co += Vector((noise.noise(v.co * 23 + Vector((1, 2, 3))), noise.noise(v.co * 23 + Vector((4, 5, 6))), noise.noise(v.co * 23 + Vector((7, 8, 9))))) * a


def _sweep_frames(path, up=Vector((0, 1, 0))):
    fr = []
    for i, p in enumerate(path):
        tg = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        ref = up if abs(tg.dot(up)) < 0.9 else Vector((1, 0, 0))
        n = ref.cross(tg).normalized(); b = tg.cross(n).normalized()
        fr.append((n, b))
    return fr


def _bez(p0, p1, p2, p3, t):
    u = 1 - t
    return p0 * u ** 3 + p1 * 3 * u * u * t + p2 * 3 * u * t * t + p3 * t ** 3


def _limb(L, path, rad, name, k=5, depth=0.02, phase=0.0, sides=20, flat=0.9, cap0=True, cap1=True, up=Vector((0, 1, 0))):
    """Tubo de manga ao longo do caminho; rad(t) em unidades locais; pregas longitudinais em V."""
    fr = _sweep_frames(path, up)
    n = len(path)
    rings = []
    for i, p in enumerate(path):
        t = i / (n - 1)
        r = rad(t) * S
        dd = depth * S * (0.5 + 0.8 * t)
        nn, bb = fr[i]
        ring = []
        for q in range(sides):
            a = 2 * math.pi * q / sides
            d = _pleat(a, t * 3, k, dd, phase, 0.25)
            rr = r - d
            ring.append(p + (nn * math.cos(a) * rr + bb * math.sin(a) * rr * flat))
        rings.append(ring)
    o = _grid(L, rings, [L.MAT["estatua"]], name, cap0=cap0, cap1=cap1)
    _chisel(o, 0.002)
    return o


# braço: (cotovelo, punho) em coordenadas locais; o da direita (+1) passa POR CIMA do outro (y maior), cruzando o peito em X
def _arm_pts(side):
    over = side > 0
    sh = (side * 0.33, 0.0, 1.29)
    el = (side * 0.37, 0.19 if over else 0.145, 0.935 if over else 0.92)
    wr = (-side * 0.005, 0.28 if over else 0.20, 1.10 if over else 1.065)
    return sh, el, wr


def _arms(L, side):
    sh, el, wr = _arm_pts(side)
    sh, el, wr = P(*sh), P(*el), P(*wr)
    mid = P(side * 0.385, 0.08, 1.12)
    up_path = [_bez(sh, sh * 0.6 + mid * 0.4 + Vector((0, 0, 0)), mid * 0.5 + el * 0.5 + (mid - el) * 0.2, el, i / 15) for i in range(16)]
    _limb(L, up_path, lambda t: 0.095 + 0.0 * t - 0.006 * t, "braco", k=4, depth=0.022, phase=side * 0.5, cap0=True, cap1=True)
    path = [el + (wr - el) * (i / 19) for i in range(20)]
    # antebraço cilíndrico: ombro de manga no cotovelo, mais fino no meio e boca larga com punho
    rad = lambda t: _prof([(0, 0.09), (0.25, 0.078), (0.62, 0.075), (0.86, 0.093), (0.94, 0.112), (1.0, 0.098)], t)
    o = _limb(L, path, rad, "antebraco", k=5, depth=0.026, phase=side * 1.1 + 0.4, sides=24, flat=0.92, up=Vector((0, 0, 1)))
    # punho de pano: faixa fina saliente na boca da manga
    _limb(L, [wr - (wr - el).normalized() * 0.03 * S + (wr - el) * 0.0, wr + (wr - el).normalized() * 0.02 * S], lambda t: 0.1, "punho", k=0, depth=0.0, sides=24, flat=0.92, up=Vector((0, 0, 1)))
    _drape(L, el + (wr - el) * 0.24, side)
    return o


def _drape(L, c, side):
    """Pano da manga que cai em pregas verticais, pendurado sob o antebraço."""
    rows = 20; n = 30
    w0, th = 0.09, 0.034
    ztop = c.z - 0.02
    length = 0.40 * S
    rings = []
    for j in range(rows + 1):
        u = j / rows
        z = ztop - length * u
        ww = (w0 * (0.95 + 0.30 * u)) * S
        A = (0.02 + 0.05 * u) * S
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            xr = math.cos(a)
            fold = 0.5 + 0.5 * math.cos(3.2 * math.pi * xr + side * 0.8 + 2.0 * u)
            tt = th * S + A * fold
            jag = 0.05 * S * abs(math.sin(3 * a + side)) * _sm(0.8, 1.0, u) + 0.02 * S * _sm(0.5, 1.0, u) * abs(math.sin(5 * a))
            ring.append(Vector((c.x + ww * xr + 0.02 * S * u * side, c.y + 0.0 * u + tt * math.sin(a) - 0.01 * S, z - jag)))
        rings.append(ring)
    o = _grid(L, rings, [L.MAT["estatua"]], "pano_manga", cap0=True, cap1=True)
    _chisel(o, 0.002)


def _hand(L, wrist, d, over):
    """Mão de blocos: dorso, nós, quatro dedos em dois segmentos (o distal dobra para baixo) e polegar."""
    M = L.MAT["estatua"]
    d = Vector(d).normalized()
    ex = d.copy(); ex.z = 0; ex.normalize()
    c = wrist + d * 0.050 * S
    _box(L, c, (0.095, 0.045, 0.092), M, ex=d, bev=0.009)                                  # dorso
    _box(L, wrist + d * 0.1 * S + Vector((0, 0.002, 0.0)), (0.030, 0.050, 0.095), M, ex=d, bev=0.008)   # nós dos dedos
    for k in range(4):
        zo = (k - 1.5) * 0.0225
        base = wrist + d * 0.118 * S + Vector((0, 0, zo * S))
        d1 = (ex * 1.0 + Vector((0, 0, -0.35))).normalized()
        _box(L, base + d1 * 0.026 * S, (0.056, 0.021, 0.0205), M, ex=d1, bev=0.005)
        tip = base + d1 * 0.054 * S
        d2 = (ex * 1.0 + Vector((0, 0, -1.1))).normalized()
        _box(L, tip + d2 * 0.02 * S, (0.042, 0.0195, 0.0195), M, ex=d2, bev=0.005)
    th = wrist + d * 0.075 * S + Vector((0, 0.0 + (-0.012 if not over else 0.012), 0.062 * S))     # polegar
    _box(L, th + ex * 0.02 * S, (0.06, 0.024, 0.025), M, ex=(ex + Vector((0, 0.1, 0.25))), bev=0.006)


def _hands(L):
    for side in (1, -1):
        sh, el, wr = _arm_pts(side)
        w = P(*wr); e = P(*el)
        _hand(L, w, (w - e), side > 0)


# ---------------------------------------------------------------- espada
def _ringloft(L, rings, m, name, sm=False):
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(vs[0])
    for j in range(len(vs) - 1):
        for i in range(n):
            a, b = vs[j], vs[j + 1]
            ids = [a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]]
            seen = []
            for v in ids:
                if v not in seen: seen.append(v)
            if len(seen) >= 3: bm.faces.new(seen)
    bm.faces.new(vs[0][::-1])
    if len(set(tuple(v.co) for v in vs[-1])) > 2: bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for e in bm.edges: e.smooth = sm
    return L.from_bm(bm, m, name)


def _sword(L):
    """Espada de ponta para baixo: ponta no plinto, lâmina com friso, guarda com gavião e remates, empunhadura com fios, pomo."""
    M = L.MAT["ferro"]; E = L.MAT["estatua"]; D = L.MAT["escura"]
    x0, y0 = 0.0, 0.235
    zg = 0.935
    # lâmina (seção em losango achatado, ponta para baixo); topo em zg
    zs = [zg - 0.01, zg - 0.05, 0.55, 0.30, 0.12, 0.04, 0.0]
    hw = [0.040, 0.040, 0.037, 0.031, 0.021, 0.010, 0.0]
    rings = []
    for z, w in zip(zs, hw):
        t = 0.012 if w > 0 else 0.0
        if w == 0:
            rings.append([P(x0, y0, z + 0.0)] * 6)
        else:
            rings.append([P(x0 + w, y0, z), P(x0 + w * 0.4, y0 + t, z), P(x0 - w * 0.4, y0 + t, z),
                          P(x0 - w, y0, z), P(x0 - w * 0.4, y0 - t, z), P(x0 + w * 0.4, y0 - t, z)])
    _ringloft(L, rings, M, "lamina")
    L.rock(P(x0, y0 + 0.011 * YF, 0.50), (0.012 * S, 0.006, 0.78 * S), D, bev=0.002)       # friso (sulco)
    # guarda: barra, centro, quillons curvos com remates
    _box(L, P(x0, y0, zg), (0.32, 0.050, 0.040), M, bev=0.008)
    _box(L, P(x0, y0, zg), (0.085, 0.072, 0.062), M, bev=0.01)
    _box(L, P(x0, y0 + 0.03 * YF, zg), (0.045, 0.014, 0.036), E, bev=0.004)                   # gema/boss
    for sx in (-1, 1):
        _box(L, P(sx * 0.165, y0, zg + 0.018), (0.06, 0.046, 0.04), M, ex=(sx, 0, 0.55), bev=0.007)
        _box(L, P(sx * 0.195, y0, zg + 0.045), (0.032, 0.05, 0.05), M, ex=(sx, 0, 1.2), bev=0.007)   # remate virado para cima
        _box(L, P(sx * 0.075, y0, zg - 0.03), (0.04, 0.05, 0.03), M, ex=(sx, 0, -0.5), bev=0.006)    # gavião inferior
    # empunhadura de couro (anéis) e pomo
    gp = [P(x0, y0, zg + 0.032 + 0.17 * i / 11) for i in range(12)]
    rings = []
    for i, p in enumerate(gp):
        r = (0.021 + (0.005 if i % 2 else 0.0)) * S
        rings.append([p + Vector((r * math.cos(2 * math.pi * k / 8), r * math.sin(2 * math.pi * k / 8) * YF, 0)) for k in range(8)])
    _ringloft(L, rings, D, "punho")
    pz = zg + 0.205
    rings = []
    for z, r in ((0.0, 0.026), (0.012, 0.047), (0.03, 0.054), (0.05, 0.046), (0.066, 0.03), (0.075, 0.012)):
        rings.append([P(x0 + r * math.cos(2 * math.pi * k / 8 + 0.4), y0 + r * math.sin(2 * math.pi * k / 8 + 0.4), pz + z) for k in range(8)])
    _ringloft(L, rings, M, "pomo")


# ---------------------------------------------------------------- capuz
HZ0, HZ1 = 1.08, 2.0           # base do capelo (sobre os ombros) e ponta do capuz
FZ, FA, FB = 1.655, 0.255, 0.66  # centro do rosto e semieixos (z, ângulo) da abertura
HOODR = [(1.08, 0.23), (1.30, 0.22), (1.42, 0.23), (1.52, 0.262), (1.66, 0.268), (1.80, 0.205), (1.92, 0.10), (2.0, 0.012)]


def _hood_r(t, z):
    """Posição (x,y) do capuz+capelo em ângulo t e altura z; devolve a máscara da cavidade (0..1) e a do rosto (0..1)."""
    Rr = _prof(HOODR, z)
    sh = max(0.0, min(1.0, (1.42 - z) / 0.30))             # 1 = ombros (largos), 0 = cabeça
    rx = Rr * (1.0 + 0.55 * sh); ry = Rr * (1.08 - 0.25 * sh)
    t01 = max(0.0, (z - 1.5) / (HZ1 - 1.5))
    cy = -0.15 * t01 ** 2.0                                # a ponta tomba para trás
    dt = math.atan2(math.sin(t - math.pi / 2), math.cos(t - math.pi / 2))
    d = math.sqrt((dt / FB) ** 2 + ((z - FZ) / FA) ** 2)
    g = 1.0 - _sm(0.45, 1.0, d)                            # 1 no fundo da cavidade, 0 na borda
    depth = 0.022 + 0.06 * sh + 0.02 * (1 - t01)
    pl = _pleat(t, z, 6, depth, 0.4, 0.14) + _pleat(t, z, 11, depth * 0.35, 1.1, 0.2)
    pl *= 1.0 - min(1.0, g * 4.0)                          # interior liso
    rimb = 0.014 * math.exp(-((d - 1.1) / 0.22) ** 2)
    face = max(0.0, 1.0 - (dt / 0.52) ** 2 - ((z - FZ + 0.02) / 0.135) ** 2)    # máscara lisa: oval levemente convexo
    fb = 0.10 * _sm(0.0, 0.45, face)
    k = rimb - 0.185 * g + fb - pl
    x, y = (rx + k) * math.cos(t), cy + (ry + k) * math.sin(t)
    jb = 1 - _sm(1.08, 1.17, z)
    mx, my = _prof(_RX, z) * math.cos(t) * 0.97, _prof(_RY, z) * math.sin(t) * 0.97
    return (x * (1 - jb) + mx * jb, y * (1 - jb) + my * jb), g, face


def _hood(L):
    N = 80; rows = 56
    rings = []; msk = []
    for j in range(rows + 1):
        z = HZ0 + (HZ1 - HZ0) * j / rows
        ring = []; cr = []
        for i in range(N):
            t = 2 * math.pi * i / N
            (x, y), g, f = _hood_r(t, z)
            ring.append(P(x, y, z)); cr.append((g, f))
        rings.append(ring); msk.append(cr)

    def midx(j, i):
        q = [msk[j][i], msk[j + 1][i], msk[j][(i + 1) % N], msk[j + 1][(i + 1) % N]]
        if max(c[1] for c in q) > 0.02: return 0              # rosto: pedra clara da estátua
        if max(c[0] for c in q) > 0.04: return 1              # paredes internas: pedra média
        return 0
    o = _grid(L, rings, [L.MAT["estatua"], L.MAT["sombra"]], "capuz", cap0=False, cap1=True, midx=midx)
    _chisel(o, 0.0025)
    # aba espessa: tubo ao longo do contorno da abertura, mais grosso no alto (dobra do capuz)
    M = 56
    path = []; rad = []
    for k in range(M):
        ph = 2 * math.pi * k / M
        t = math.pi / 2 + FB * 1.02 * math.cos(ph)
        z = FZ + FA * 1.02 * math.sin(ph)
        (x, y), g, f = _hood_r(t, z)
        path.append(P(x, y, z))
        rad.append((0.026 + 0.020 * max(0.0, math.sin(ph)) + 0.004 * abs(math.cos(ph)) + 0.004 * math.sin(7 * ph)) * S)
    rings = []
    for k in range(M):
        p = path[k]
        tg = (path[(k + 1) % M] - path[k - 1]).normalized()
        out = Vector((p.x - SX, p.y - SY, 0)).normalized()
        nn = tg.cross(out).normalized(); bb = tg.cross(nn).normalized()
        r = rad[k]
        rings.append([p + out * 0.012 + (nn * math.cos(2 * math.pi * s / 10) + bb * math.sin(2 * math.pi * s / 10)) * r for s in range(10)])
    _grid(L, rings, [L.MAT["estatua"]], "aba", closed_v=True, cap0=False, cap1=False)
    return o


def _cracks(L, objs):
    """Rachaduras: sulcos finos no manto."""
    segs = []
    r = L.rnd
    for start in ((0.12, 0.17, 0.75), (-0.2, 0.15, 0.45), (0.0, -0.17, 0.9)):
        p = Vector(start); pts = [p]
        for _ in range(7):
            p = p + Vector((r.uniform(-0.03, 0.03), 0, -r.uniform(0.04, 0.09))); pts.append(p)
        segs += list(zip(pts, pts[1:]))
    for o in objs:
        for v in o.data.vertices:
            q = Vector(((v.co.x - SX) / S, (v.co.y - SY) / (S * YF), (v.co.z - SZ) / S))
            for a, b in segs:
                ab = b - a; tt = max(0, min(1, (q - a).dot(ab) / ab.length_squared)); dd = (q - (a + ab * tt)).length
                if dd < 0.013:
                    n = Vector((q.x / 0.3, q.y / 0.17, 0)); n.normalize()
                    v.co -= Vector((n.x * S, n.y * S * YF, 0)) * 0.012 * (1 - dd / 0.013)
                    break


def _statue(L):
    parts = [_manto(L)]
    _cracks(L, parts)
    _arms(L, -1)
    _arms(L, 1)
    _hood(L)
    _hands(L)
    _sword(L)


def build(L):
    """Tudo que fica dentro e em volta do nicho. O núcleo do fuste e o cortador ficam fora daqui."""
    L.MAT["sombra"] = L.mat("M_Sombra", (0.34, 0.33, 0.31), rough=1.0)     # interior do capuz: cinza-pedra médio, não preto
    L.MAT["estatua"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.56, 0.54, 0.50, 1)  # estátua clara contra o fundo escuro
    _frame(L)
    _tympanum(L)
    _back(L)
    _plinth(L)
    _statue(L)
