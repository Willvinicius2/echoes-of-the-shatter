"""Nicho frontal (+Y) do pilar da Cripta: cortador ogival, moldura em aduelas, mísulas, tímpano, fundo de blocos, plinto,
estátua encapuzada com dobras em pregas vivas e espada. Usa só pilar_lib (L). Coordenadas do pilar: centro (0,0), face frontal y=0.95."""
import math
import bmesh
from mathutils import Vector, noise

Z0 = 1.25           # piso do nicho
W = 0.55            # meia-largura útil
HS = 1.35           # altura dos lados antes da ponta
R = 2 * W           # raio das curvas ogivais
ATIP = math.acos((R - W) / R)
FACE = 0.95
SX, SY, SZ = 0.0, 0.76, 1.45   # origem local da estátua (centro, y, topo do plinto)


def _poly(L, n=10):
    return [(x, z + Z0) for x, z in L.ogive(W, HS, 0, n)]


def cutter(L):
    """Prisma ogival (largura 1.1 m, altura ~2.3 m a partir de z=1.25) até y=0.55, para subtrair do núcleo."""
    return L.prism(_poly(L, 12), 0.55, FACE + 0.2, L.MAT["escura"])


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


def _ground_noise(p, f, a):
    return noise.noise(p * f) * a


# ---------------------------------------------------------------- moldura em aduelas
def _blocks_along(L, o0, o1, y1, seed_len, chip=0.014, side=1, base_len=0.34):
    """Anel de blocos que acompanha a ogiva (lado reto + arco) entre os recuos o0..o1 da abertura, de um lado (side=±1)."""
    M = L.MAT["pedra"]
    thick = o1 - o0
    depth = y1 - (FACE - 0.07)
    yc = (y1 + FACE - 0.07) / 2
    ext = 0.10                                    # desce abaixo do piso: base da ombreira
    # trecho reto
    total = HS + ext
    cuts = _split(total, base_len, seed_len)
    z = -ext
    for ln in cuts:
        ln_v = ln - 0.016
        t = thick * L.rnd.choice([0.92, 1.0, 1.06])
        L.rock((side * (W + o0 + t / 2), yc, Z0 + z + ln / 2), (t, depth, ln_v), M, chip=chip, rough=0.0, bev=0.014, cuts_pre=1, seg=1)
        z += ln
    # trecho em arco
    omid = (o0 + o1) / 2
    arc = (R + omid) * ATIP
    cuts = _split(arc, base_len * 0.95, seed_len + 1)
    s = 0.0
    for ln in cuts:
        a = (s + ln / 2) / (R + omid)
        t = thick * L.rnd.choice([0.94, 1.0, 1.08])
        rr = R + o0 + t / 2
        c = (side * (-W + rr * math.cos(a)), yc, Z0 + HS + rr * math.sin(a))
        rot = -a if side > 0 else a
        L.rock(c, (t, depth, ln - 0.016), M, rot=(0, rot, 0), chip=chip, rough=0.0, bev=0.014, cuts_pre=1, seg=1)
        s += ln


def _split(total, base, seed):
    n = max(2, round(total / base))
    ws = [0.8 + 0.4 * ((math.sin(seed * 7.3 + i * 2.9) + 1) / 2) for i in range(n)]
    k = total / sum(ws)
    return [w * k for w in ws]


def _frame(L):
    for side in (-1, 1):
        _blocks_along(L, 0.0, 0.13, FACE + 0.06, 3 + side, side=side)        # ordem interna
        _blocks_along(L, 0.13, 0.30, FACE + 0.13, 11 + side, side=side)      # ordem externa, mais saliente
    # pedra-chave no ápice das duas ordens
    ytop = Z0 + HS + R * math.sin(ATIP)
    L.rock((0, FACE + 0.035, ytop + 0.07), (0.2, 0.17, 0.26), L.MAT["pedra"], chip=0.02, rough=0.004, bev=0.015, cuts_pre=1, seg=1)
    L.rock((0, FACE + 0.085, ytop + 0.24), (0.26, 0.2, 0.22), L.MAT["pedra"], rot=(0, 0.0, 0), chip=0.024, rough=0.004, bev=0.016, cuts_pre=1, seg=1)
    # mísulas sob o arranque do arco, em degraus
    zs = Z0 + HS
    for side in (-1, 1):
        cx = side * (W + 0.15)
        L.rock((cx, FACE + 0.1, zs + 0.0), (0.46, 0.26, 0.10), L.MAT["pedra"], chip=0.02, rough=0.004, bev=0.014, cuts_pre=1, seg=1)
        L.rock((cx + side * 0.0, FACE + 0.095, zs - 0.105), (0.36, 0.22, 0.10), L.MAT["pedra"], chip=0.018, rough=0.004, bev=0.012, cuts_pre=1, seg=1)
        L.rock((cx, FACE + 0.085, zs - 0.21), (0.26, 0.18, 0.10), L.MAT["escura"], chip=0.016, rough=0.004, bev=0.012, cuts_pre=1, seg=1)
        L.rock((cx, FACE + 0.075, zs - 0.31), (0.16, 0.14, 0.10), L.MAT["pedra"], rot=(0, 0, 0), chip=0.014, rough=0.003, bev=0.01, cuts_pre=1)
    # soleira em frente ao nicho
    L.rock((0, FACE + 0.07, Z0 - 0.06), (1.46, 0.24, 0.12), L.MAT["pedra"], chip=0.03, rough=0.005, bev=0.02, cuts_pre=2, seg=1)


def _tympanum(L):
    """Placa em relevo acima do arco com rosácea de quatro lóbulos."""
    ytop = Z0 + HS + (R + 0.30) * math.sin(ATIP)
    zc = ytop + 0.20
    yb = FACE + 0.01
    L.rock((0, yb + 0.035, zc), (0.74, 0.09, 0.34), L.MAT["pedra"], chip=0.02, rough=0.004, bev=0.014, cuts_pre=2, seg=1)
    # moldura da placa (filetes)
    L.rock((0, yb + 0.075, zc + 0.15), (0.66, 0.04, 0.035), L.MAT["escura"], bev=0.008)
    L.rock((0, yb + 0.075, zc - 0.15), (0.66, 0.04, 0.035), L.MAT["escura"], bev=0.008)
    _rosette(L, 0.0, yb + 0.08, zc, 0.09)


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


# ---------------------------------------------------------------- fundo do nicho, piso, plinto
def _back(L):
    """Fundo de blocos escuros (parede em y≈0.55), arco interno em relevo e rosáceas."""
    mort = L.prism([(x * 0.995, (z - Z0) * 0.995 + Z0) for x, z in _poly(L, 12)], 0.545, 0.565, L.MAT["escura"])
    z = Z0
    row = 0
    while z < Z0 + HS + 1.0:
        h = [0.30, 0.34, 0.27, 0.32][row % 4]
        x = -0.62 + (0.0 if row % 2 else 0.17)
        while x < 0.62:
            ln = L.rnd.choice([0.32, 0.42, 0.37, 0.50])
            xe = min(x + ln, 0.62)
            xc = (x + xe) / 2
            top = Z0 + _arch_top(max(abs(x), abs(xe)) * 0.96)
            if z + 0.05 < top + 0.02 and z < top - 0.03:
                L.rock((xc, 0.545 + 0.0, z + h / 2), (xe - x - 0.014, 0.10, h - 0.014), L.MAT["escura"], chip=0.014, rough=0.005, bev=0.01, cuts_pre=1)
            x = xe
        z += h
        row += 1
    # arco interno em relevo (aduelas finas) copiando a ogiva
    for side in (-1, 1):
        o0, o1 = -0.13, -0.05
        omid = (o0 + o1) / 2
        arc = (R + omid) * ATIP
        s = 0.0
        for ln in _split(arc, 0.28, 5 + side):
            a = (s + ln / 2) / (R + omid)
            rr = R + omid
            c = (side * (-W + rr * math.cos(a)), 0.568, Z0 + HS + rr * math.sin(a))
            L.rock(c, (o1 - o0, 0.05, ln - 0.014), L.MAT["pedra"], rot=(0, -a if side > 0 else a, 0), chip=0.01, rough=0.003, bev=0.008, cuts_pre=1)
            s += ln
        # ombreira interna em relevo
        L.rock((side * (W - 0.09), 0.568, Z0 + HS / 2 + 0.05), (0.08, 0.05, HS - 0.1), L.MAT["pedra"], chip=0.01, bev=0.008, cuts_pre=1)
    yz = 0.585
    for side in (-1, 1):
        _rosette(L, side * 0.33, yz, 3.05, 0.075)
    # lajes do piso
    L.rock((-0.3, 0.76, Z0 + 0.015), (0.56, 0.42, 0.06), L.MAT["pedra"], chip=0.015, rough=0.003, bev=0.012, cuts_pre=1, seg=1)
    L.rock((0.3, 0.74, Z0 + 0.015), (0.56, 0.44, 0.06), L.MAT["escura"], chip=0.015, rough=0.003, bev=0.012, cuts_pre=1, seg=1)


def _plinth(L):
    M = L.MAT["pedra"]
    L.rock((0, 0.755, Z0 + 0.09), (0.94, 0.40, 0.12), M, chip=0.03, rough=0.006, bev=0.018, cuts_pre=2, seg=1)
    L.rock((-0.17, 0.755, Z0 + 0.19), (0.46, 0.34, 0.10), M, chip=0.026, rough=0.006, bev=0.016, rot=(0, 0, 0.02), cuts_pre=2, seg=1)
    L.rock((0.25, 0.755, Z0 + 0.19), (0.38, 0.34, 0.10), L.MAT["escura"], chip=0.026, rough=0.006, bev=0.016, rot=(0, 0, -0.03), cuts_pre=2, seg=1)
    # lascas caídas
    L.rock((0.43, 0.84, Z0 + 0.07), (0.13, 0.10, 0.07), M, rot=(0.2, 0.3, 0.7), chip=0.02, rough=0.005, bev=0.01, cuts_pre=1, seg=1)
    L.rock((-0.45, 0.82, Z0 + 0.06), (0.11, 0.09, 0.06), M, rot=(0.1, 0.2, 2.0), chip=0.02, rough=0.005, bev=0.01, cuts_pre=1, seg=1)


# ---------------------------------------------------------------- estátua
def P(x, y, z):
    return Vector((SX + x, SY + y, SZ + z))


def _pleat(t, z, k, depth, phase=0.0, warp=0.12):
    """Prega viva: sulco em V (abs(sin)) com crista larga; retorna recuo radial em metros (>=0)."""
    tw = t + warp * math.sin(2.1 * z + 1.3 * math.cos(t) + phase)
    g = abs(math.sin(k * tw + phase)) ** 0.5
    return depth * (1.0 - g)


_RX = [(0, 0.38), (0.05, 0.365), (0.3, 0.315), (0.6, 0.26), (0.9, 0.23), (1.15, 0.245), (1.28, 0.275), (1.36, 0.22), (1.42, 0.12)]
_RY = [(0, 0.19), (0.05, 0.185), (0.3, 0.176), (0.6, 0.162), (0.9, 0.145), (1.15, 0.145), (1.28, 0.155), (1.36, 0.13), (1.42, 0.09)]


def _manto(L):
    N = 72; rows = 34; ZT = 1.42
    rings = []
    for j in range(rows + 1):
        z = ZT * j / rows
        rx, ry = _prof(_RX, z), _prof(_RY, z)
        depth = 0.034 + 0.075 * (1 - z / ZT) ** 1.0
        ring = []
        for i in range(N):
            t = 2 * math.pi * i / N
            c, s = math.cos(t), math.sin(t)
            d = _pleat(t, z, 7, depth, 0.3) + _pleat(t, z, 12, depth * 0.38, 1.7, 0.2)
            kick = max(0.0, 0.07 - z) * 0.5
            zz = z
            if j == 0:
                zz = 0.005 + 0.012 * (noise.noise(Vector((c * 2, s * 2, 3.1))) + 0.4) + 0.012 * abs(math.sin(5 * t))
            rr_x = rx - d + kick; rr_y = ry - d + kick
            ring.append(P(rr_x * c, rr_y * s, zz))
        rings.append(ring)
    o = _grid(L, rings, [L.MAT["estatua"]], "manto", cap0=True, cap1=True)
    _chisel(o, 0.003)
    return o


def _chisel(o, a):
    """Irregularidade fina de cinzel."""
    for v in o.data.vertices:
        v.co += Vector((noise.noise(v.co * 23 + Vector((1, 2, 3))), noise.noise(v.co * 23 + Vector((4, 5, 6))), noise.noise(v.co * 23 + Vector((7, 8, 9))))) * a


def _collar(L):
    """Gola/capa sobre os ombros, com pregas fundas."""
    N = 80; rows = 14
    rings = []
    for j in range(rows + 1):
        u = j / rows
        z = 1.40 - 0.24 * u               # de cima (pescoço) para baixo (ombros)
        rx = 0.19 + 0.13 * (u ** 0.8); ry = 0.15 + 0.06 * (u ** 0.8)
        depth = 0.012 + 0.032 * u
        ring = []
        for i in range(N):
            t = 2 * math.pi * i / N
            d = _pleat(t, z, 6, depth, 0.9) + _pleat(t, z, 10, depth * 0.3, 0.2, 0.2)
            ring.append(P((rx - d) * math.cos(t), (ry - d) * math.sin(t) + 0.005, z - (0.025 if (0.3 < t < 2.84) else 0.0) * u))
        rings.append(ring)
    o = _grid(L, rings, [L.MAT["estatua"]], "gola", cap0=True, cap1=False)
    _chisel(o, 0.003)
    return o


def _sweep_pts(path, up=Vector((0, 1, 0))):
    """Quadros (N,B) ao longo do caminho."""
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


def _sleeve(L, side):
    """Manga larga: do ombro, cotovelo para fora, antebraço cruzando o peito até o lado oposto (esquerda por baixo, direita por cima)."""
    over = side > 0
    e = P(-side * 0.055, 0.245 if over else 0.20, 1.035 if over else 1.07)
    p0 = P(side * 0.27, -0.01, 1.31); p1 = P(side * 0.40, 0.0, 1.06); p2 = P(side * 0.20, 0.17, 1.06 + (0.0 if over else 0.03)); p3 = e
    n = 26; sides = 20
    path = [_bez(p0, p1, p2, p3, i / (n - 1)) for i in range(n)]
    fr = _sweep_pts(path)
    rings = []
    for i, p in enumerate(path):
        t = i / (n - 1)
        r = _prof([(0, 0.09), (0.25, 0.095), (0.55, 0.09), (0.8, 0.105), (0.93, 0.125), (1.0, 0.105)], t)   # boca da manga alargada
        depth = 0.026 + 0.05 * t
        nn, bb = fr[i]
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            d = _pleat(a, t * 3, 5, depth, side * 0.7, 0.25)
            rr = r - d
            ring.append(p + (nn * math.cos(a) * rr * 1.0 + bb * math.sin(a) * rr * 0.86))
        rings.append(ring)
    o = _grid(L, rings, [L.MAT["estatua"]], "manga", cap0=True, cap1=True)
    _chisel(o, 0.002)
    return o


def _hands(L):
    """Mãos juntas sobre o punho: dorso, quatro dedos em cunha, nós dos dedos e polegares."""
    M = L.MAT["estatua"]
    cx, cy, cz = 0.0, 0.205, 0.985
    L.rock(P(cx, cy, cz), (0.19, 0.10, 0.12), M, bev=0.016, chip=0.012, rough=0.0, cuts_pre=1, seg=1)
    for k in range(4):                        # dedos da mão de cima, fechados sobre o punho
        zf = cz + 0.048 - k * 0.031
        L.rock(P(cx - 0.004, cy + 0.058, zf), (0.16, 0.04, 0.030), M, bev=0.011, seg=1)
    for sx in (-1, 1):                        # nós dos dedos da mão de baixo, nas laterais
        L.rock(P(sx * 0.088, cy + 0.03, cz + 0.015), (0.05, 0.05, 0.07), M, rot=(0, 0, sx * 0.3), bev=0.012, seg=1)
    L.rock(P(0.0, cy + 0.083, cz + 0.07), (0.09, 0.035, 0.03), M, rot=(0.3, 0, 0), bev=0.009, seg=1)   # polegar


def _sword(L):
    """Espada de ponta para baixo: pomo facetado, empunhadura com fios, guarda reta com pontas, lâmina com friso."""
    M = L.MAT["ferro"]; E = L.MAT["estatua"]
    x0, y0 = 0.0, 0.215
    # lâmina (seção hexagonal achatada, ponta para baixo)
    zs = [0.80, 0.78, 0.5, 0.25, 0.08, 0.02]
    hw = [0.040, 0.040, 0.036, 0.030, 0.018, 0.0]
    rings = []
    for z, w in zip(zs, hw):
        t = 0.011 if w > 0 else 0.0
        if w == 0:
            rings.append([P(x0, y0, z)] * 6)
        else:
            rings.append([P(x0 + w, y0, z), P(x0 + w * 0.45, y0 + t, z), P(x0 - w * 0.45, y0 + t, z),
                          P(x0 - w, y0, z), P(x0 - w * 0.45, y0 - t, z), P(x0 + w * 0.45, y0 - t, z)])
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    for j in range(len(vs) - 1):
        for i in range(6):
            a, b = vs[j], vs[j + 1]
            ids = [a[i], a[(i + 1) % 6], b[(i + 1) % 6], b[i]]
            seen = []
            for v in ids:
                if v not in seen: seen.append(v)
            if len(seen) >= 3: bm.faces.new(seen)
    bm.faces.new(vs[0][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for e in bm.edges: e.smooth = False
    o = L.from_bm(bm, M, "lamina")
    # friso central escuro (sulco) e guarda
    L.rock(P(x0, y0 + 0.012, 0.46), (0.012, 0.006, 0.60), L.MAT["escura"], bev=0.002)
    L.rock(P(x0, y0, 0.805), (0.34, 0.05, 0.045), M, bev=0.008, chip=0.0)
    for sx in (-1, 1):                         # pontas da guarda curvadas para cima
        L.rock(P(sx * 0.175, y0, 0.825), (0.05, 0.045, 0.06), M, rot=(0, sx * 0.4, 0), bev=0.008)
    L.rock(P(x0, y0, 0.78), (0.07, 0.06, 0.03), M, bev=0.006)
    # empunhadura de couro (anéis) e pomo
    gp = [P(x0, y0, 0.81 + 0.19 * i / 7) for i in range(8)]
    rings = []
    for i, p in enumerate(gp):
        r = 0.020 + (0.004 if i % 2 else 0.0)
        rings.append([p + Vector((r * math.cos(2 * math.pi * k / 8), r * math.sin(2 * math.pi * k / 8), 0)) for k in range(8)])
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    for j in range(len(vs) - 1):
        for i in range(8): bm.faces.new((vs[j][i], vs[j][(i + 1) % 8], vs[j + 1][(i + 1) % 8], vs[j + 1][i]))
    bm.faces.new(vs[0][::-1]); bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for e in bm.edges: e.smooth = False
    L.from_bm(bm, L.MAT["escura"], "punho")
    # pomo: disco facetado largo com aro
    rings = []
    for z, r in ((1.0, 0.030), (1.012, 0.045), (1.03, 0.047), (1.05, 0.038), (1.065, 0.02)):
        rings.append([P(x0 + r * math.cos(2 * math.pi * k / 8 + 0.4), y0 + r * math.sin(2 * math.pi * k / 8 + 0.4), z) for k in range(8)])
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    for j in range(len(vs) - 1):
        for i in range(8): bm.faces.new((vs[j][i], vs[j][(i + 1) % 8], vs[j + 1][(i + 1) % 8], vs[j + 1][i]))
    bm.faces.new(vs[0][::-1]); bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for e in bm.edges: e.smooth = False
    L.from_bm(bm, M, "pomo")


HZ0, HZ1 = 1.08, 1.98          # base do capelo (sobre os ombros) e ponta do capuz
FZ, FA, FB = 1.63, 0.165, 0.74  # centro e semieixos (z, ângulo) da abertura do rosto


def _sm(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _hood_r(t, z):
    """Posição (x,y) da superfície do capuz+capelo em ângulo t e altura z; devolve também a máscara da abertura (0..1)."""
    Rr = _prof([(1.08, 0.215), (1.30, 0.205), (1.42, 0.215), (1.55, 0.235), (1.70, 0.228), (1.84, 0.16), (1.94, 0.07), (1.98, 0.012)], z)
    sh = max(0.0, min(1.0, (1.42 - z) / 0.30))             # 1 = ombros (largos), 0 = cabeça
    rx = Rr * (0.98 + 0.52 * sh); ry = Rr * (1.17 - 0.38 * sh)
    t01 = max(0.0, (z - 1.5) / (HZ1 - 1.5))
    cy = 0.005 - 0.17 * t01 ** 2.2
    dt = math.atan2(math.sin(t - math.pi / 2), math.cos(t - math.pi / 2))
    d2 = (dt / FB) ** 2 + ((z - FZ) / FA) ** 2
    cave = max(0.0, 1.0 - d2)
    front = math.exp(-(dt / 0.8) ** 2) * (1 - sh * 0.3)
    depth = (0.020 + 0.060 * sh + 0.018 * (1 - t01)) * (1 - 0.5 * front * (1 - sh))
    pl = _pleat(t, z, 6, depth, 0.4, 0.14) + _pleat(t, z, 11, depth * 0.35, 1.1, 0.2)
    dtf = dt / 0.46; zf = (z - (FZ - 0.02)) / 0.125
    face = max(0.0, 1.0 - dtf * dtf - zf * zf)                # volume liso do rosto dentro da cavidade
    pl *= 1.0 - min(1.0, cave * 3.0)                          # interior liso, sem pregas
    k = 1 - 0.40 * math.sqrt(cave) + 0.15 * face ** 0.8
    x, y = (rx - pl) * math.cos(t), cy + (ry - pl) * math.sin(t)
    # barra do capelo se junta ao manto
    jb = 1 - _sm(1.08, 1.17, z)
    mx, my = _prof(_RX, z) * math.cos(t) * 0.97, _prof(_RY, z) * math.sin(t) * 0.97
    return ((x * (1 - jb) + mx * jb) * k, (y * (1 - jb) + my * jb) * k), cave, d2


def _hood(L):
    N = 64; rows = 52
    rings = []; cav = []
    for j in range(rows + 1):
        z = HZ0 + (HZ1 - HZ0) * j / rows
        ring = []; cr = []
        for i in range(N):
            t = 2 * math.pi * i / N
            (x, y), c, d2 = _hood_r(t, z)
            ring.append(P(x, y, z)); cr.append(c)
        rings.append(ring); cav.append(cr)
    o = _grid(L, rings, [L.MAT["estatua"], L.MAT["sombra"]], "capuz", cap0=False, cap1=True,
              midx=lambda j, i: 1 if max(cav[j][i], cav[j + 1][i], cav[j][(i + 1) % N], cav[j + 1][(i + 1) % N]) > 0.03 else 0)
    _chisel(o, 0.0025)
    # aba espessa: tubo fechado ao longo do contorno da abertura
    M = 40
    path = []; rad = []
    for k in range(M):
        ph = 2 * math.pi * k / M
        t = math.pi / 2 + FB * 1.0 * math.cos(ph)
        z = FZ + FA * 1.0 * math.sin(ph)
        (x, y), c, d2 = _hood_r(t, z)
        path.append(P(x, y, z))
        rad.append(0.019 + 0.022 * max(0.0, math.sin(ph)) + 0.004 * abs(math.cos(ph)))
    rings = []
    for k in range(M):
        p = path[k]
        tg = (path[(k + 1) % M] - path[k - 1]).normalized()
        out = Vector((p.x - SX, p.y - SY, 0)).normalized()
        nn = tg.cross(out).normalized(); bb = tg.cross(nn).normalized()
        r = rad[k]
        rings.append([p + out * 0.008 + (nn * math.cos(2 * math.pi * s / 8) + bb * math.sin(2 * math.pi * s / 8)) * r for s in range(8)])
    _grid(L, rings, [L.MAT["estatua"]], "aba", closed_v=True, cap0=False, cap1=False)
    return o


def _cracks(L, objs):
    """Rachaduras: sulcos finos no manto e capuz."""
    segs = []
    r = L.rnd
    for start in ((0.12, 0.17, 0.75), (-0.2, 0.15, 0.45), (0.0, -0.17, 0.9)):
        p = Vector(start); pts = [p]
        for _ in range(7):
            p = p + Vector((r.uniform(-0.03, 0.03), 0, -r.uniform(0.04, 0.09))); pts.append(p)
        segs += list(zip(pts, pts[1:]))
    for o in objs:
        for v in o.data.vertices:
            q = v.co - Vector((SX, SY, SZ))
            for a, b in segs:
                ab = b - a; tt = max(0, min(1, (q - a).dot(ab) / ab.length_squared)); dd = (q - (a + ab * tt)).length
                if dd < 0.013:
                    n = Vector((q.x / 0.3, q.y / 0.17, 0)); n.normalize()
                    v.co -= n * 0.012 * (1 - dd / 0.013)
                    break


def _statue(L):
    parts = [_manto(L), _sleeve(L, -1), _sleeve(L, 1), _hood(L)]
    _cracks(L, parts[:1])
    _hands(L)
    _sword(L)


def build(L):
    """Tudo que fica dentro e em volta do nicho. O núcleo do fuste e o cortador ficam fora daqui."""
    L.MAT["sombra"] = L.mat("M_Sombra", (0.22, 0.21, 0.20), rough=1.0)     # interior do capuz: cinza-pedra, não preto
    L.MAT["estatua"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.52, 0.50, 0.47, 1)  # estátua clara contra o fundo escuro
    _frame(L)
    _tympanum(L)
    _back(L)
    _plinth(L)
    _statue(L)
