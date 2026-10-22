"""Corrente de elos de ferro forjado em catenaria, com graos de fixacao (placa + olhal + grilhao).
Uso: from cc_corrente import build_corrente
Medidas em metros. Cada elo e um estadio (retas + semicirculos) varrido com secao
retangular chanfrada (octogono achatado), shade flat. Elos vizinhos alternam 90 graus e se
encadeiam de verdade (folga calculada a partir do furo interno do elo).
build_corrente(p0, p1, flecha, seed, M, escala=1.0) -> lista de objetos (so usa M['ferro'] e M['ferro_escuro']).
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix


# ----------------------------------------------------------------------------- malha de elo
def _link_mesh(name, L, W, a, b, c, seg, rng, noise, weld_bump=1.0):
    """Estadio no plano XY (eixo longo = X), secao chanfrada: a = meia espessura radial,
    b = meia espessura em Z, c = chanfro. L, W = comprimento e largura externos."""
    r = (W - 2 * a) / 2.0                 # raio da linha central
    s = (L - W) / 2.0                     # meio comprimento da parte reta
    rings = []                            # (centro, radial)
    for i in range(seg + 1):              # semicirculo direito
        t = -math.pi / 2 + math.pi * i / seg
        rings.append(((s + r * math.cos(t), r * math.sin(t)), (math.cos(t), math.sin(t)), 1.0))
    rings.append(((0.0, r), (0.0, 1.0), weld_bump))
    for i in range(seg + 1):              # semicirculo esquerdo
        t = math.pi / 2 + math.pi * i / seg
        rings.append(((-s + r * math.cos(t), r * math.sin(t)), (math.cos(t), math.sin(t)), 1.0))
    rings.append(((0.0, -r), (0.0, -1.0), 1.0))
    sec = [(a, -(b - c)), (a, b - c), (a - c, b), (-(a - c), b),
           (-a, b - c), (-a, -(b - c)), (-(a - c), -b), (a - c, -b)]
    verts, faces = [], []
    nr = len(rings)
    ph = [rng.uniform(0, 6.28) for _ in range(4)]
    for ri, ((cx, cy), (rx, ry), k) in enumerate(rings):
        t = 2 * math.pi * ri / nr
        # espessura forjada: variacao suave ao longo do arame (martelado) + ruido pequeno
        lf = 1.0 + 1.1 * noise * math.sin(2 * t + ph[0]) + 0.7 * noise * math.sin(3 * t + ph[1])
        lg = 1.0 + 1.0 * noise * math.sin(2 * t + ph[2]) + 0.6 * noise * math.sin(5 * t + ph[3])
        for (u, v) in sec:
            f = lf + rng.uniform(-noise, noise) * 0.35
            g = lg + rng.uniform(-noise, noise) * 0.35
            u2, v2 = u * f * k, v * g * k
            verts.append((cx + rx * u2 + rng.uniform(-noise, noise) * 0.004,
                          cy + ry * u2 + rng.uniform(-noise, noise) * 0.004, v2))
    n, m = len(rings), len(sec)
    for k in range(n):
        k2 = (k + 1) % n
        for i in range(m):
            i2 = (i + 1) % m
            faces.append((k * m + i, k * m + i2, k2 * m + i2, k2 * m + i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = False
    return me


def _box_mesh(name, size, bev, rng=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]; v.co.y *= size[1]; v.co.z *= size[2]
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev, segments=1, affect='EDGES')
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = False
    return me


def _rivet_mesh(name, r, h):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=8,
                          radius1=r, radius2=r * 0.7, depth=h)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = False
    return me


# ----------------------------------------------------------------------------- catenaria
class _Cat:
    """Catenaria y(u) = a*(cosh((u-x0)/a) - cosh(x0/a)) de (0,0) a (D,H)."""
    def __init__(self, D, H, flecha=None, arco=None):
        self.D, self.H = D, H
        lo, hi = D / 25.0, D * 60.0
        def solve_x0(a):
            l, h = -3 * D, 4 * D
            for _ in range(70):
                x = (l + h) / 2
                g = a * (math.cosh((D - x) / a) - math.cosh(x / a))
                if g > H: l = x
                else: h = x
            return (l + h) / 2
        def sag(a):
            x0 = solve_x0(a)
            return H / 2 - a * (math.cosh((D / 2 - x0) / a) - math.cosh(x0 / a))
        def arc(a):
            x0 = solve_x0(a)
            return a * (math.sinh((D - x0) / a) + math.sinh(x0 / a))
        f = (lambda a: sag(a) - flecha) if arco is None else (lambda a: arc(a) - arco)
        l, h = lo, hi                      # sag e arco diminuem quando a cresce
        for _ in range(80):
            m = math.sqrt(l * h)
            if f(m) > 0: l = m
            else: h = m
        self.a = math.sqrt(l * h)
        self.x0 = solve_x0(self.a)
        self.L = arc(self.a)
        self._tab = []
        N = 3000; acc = 0.0; prev = self.pt(0)
        self._tab.append((0.0, 0.0))
        for i in range(1, N + 1):
            u = D * i / N; q = self.pt(u)
            acc += math.hypot(q[0] - prev[0], q[1] - prev[1]); prev = q
            self._tab.append((acc, u))

    def pt(self, u):
        a = self.a
        return (u, a * (math.cosh((u - self.x0) / a) - math.cosh(self.x0 / a)))

    def tan(self, u):
        t = math.sinh((u - self.x0) / self.a)
        n = math.hypot(1, t); return (1 / n, t / n)

    def u_at(self, s):
        tab = self._tab
        lo, hi = 0, len(tab) - 1
        s = max(0.0, min(s, tab[-1][0]))
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if tab[mid][0] < s: lo = mid
            else: hi = mid
        s0, u0 = tab[lo]; s1, u1 = tab[hi]
        return u0 if s1 == s0 else u0 + (u1 - u0) * (s - s0) / (s1 - s0)


# ----------------------------------------------------------------------------- principal
def _frame(X, Z, loc):
    X = X.normalized(); Z = (Z - X * Z.dot(X)).normalized(); Y = Z.cross(X)
    m = Matrix([[X.x, Y.x, Z.x, loc.x], [X.y, Y.y, Z.y, loc.y],
                [X.z, Y.z, Z.z, loc.z], [0, 0, 0, 1]])
    return m


def _put(name, me, mat, mw, out):
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.matrix_world = mw
    out.append(o)
    return o


def build_corrente(p0, p1, flecha, seed, M, escala=1.0):
    S = escala
    rng = random.Random(seed)
    p0 = Vector(p0); p1 = Vector(p1)
    out = []
    ferro, escuro = M['ferro'], M['ferro_escuro']
    up = Vector((0, 0, 1))
    dh = Vector((p1.x - p0.x, p1.y - p0.y, 0.0))
    D0 = dh.length
    dh = dh.normalized() if D0 > 1e-6 else Vector((1, 0, 0))
    side = dh.cross(up).normalized()      # normal do plano vertical da corrente

    # dimensoes (m)
    LC, WC, AC, BC, CC = 0.200 * S, 0.156 * S, 0.0235 * S, 0.0225 * S, 0.0110 * S   # elo
    LS, WS, AS, BS, CS = 0.260 * S, 0.175 * S, 0.0250 * S, 0.0240 * S, 0.0120 * S   # grilhao
    LE, WE, AE, BE, CE = 0.130 * S, 0.100 * S, 0.0145 * S, 0.0140 * S, 0.0060 * S   # olhal
    plate = 0.026 * S
    hook_d = (plate + 0.056 * S)          # ponto onde o grilhao se prende, a partir de p (ao longo de dh)

    # catenaria entre os pontos de gancho (flecha medida contra a corda)
    h0 = p0 + dh * hook_d; h1 = p1 - dh * hook_d
    D = (h1 - h0).xy.length; H = h1.z - h0.z
    cat = _Cat(D, H, flecha=flecha)
    e = LS / 2 - AS                       # centro do grilhao a partir do gancho (ao longo do arco)
    ps = (LS / 2 + LC / 2) - 2 * AS - 2 * AC   # passo tenso grilhao->elo: Ls/2 + Lc/2 - espessura de cada arame
    ps -= 0.008 * S                       # folga
    pitch_nom = (LC - 4 * AC) - 0.018 * S  # passo tenso (= furo interno) menos folga
    avail = cat.L - 2 * e - 2 * ps
    n = max(3, int(round(avail / pitch_nom)) + 1)
    pitch = avail / (n - 1)

    # variantes de elo (copias de malha instanciadas)
    variants = []
    for k, (dl, dw, mt) in enumerate([(0.000, 0.000, ferro), (0.004, -0.003, ferro),
                                      (-0.004, 0.003, escuro), (0.002, 0.002, ferro)]):
        me = _link_mesh("cc_elo%d_%d" % (seed, k), LC + dl * S, WC + dw * S, AC, BC, CC, 8,
                        random.Random(seed * 17 + k), 0.022, weld_bump=1.10 if k == 2 else 1.0)
        me.materials.append(mt)
        variants.append(me)

    def world(u, y):
        return h0 + dh * u + up * y

    def basis(u):
        tx, ty = cat.tan(u)
        return (dh * tx + up * ty)

    # elos
    for i in range(n):
        s = e + ps + i * pitch
        u = cat.u_at(s); y = cat.pt(u)[1]
        T = basis(u); pos = world(u, y)
        Z = side if i % 2 == 0 else T.cross(side)
        roll = Matrix.Rotation(math.radians(rng.uniform(-1.0, 1.0)), 3, T)
        Z = roll @ Z
        T2 = (Matrix.Rotation(math.radians(rng.uniform(-1.5, 1.5)), 3, side) @ T)
        pos = pos + side * rng.uniform(-0.0015, 0.0015) * S
        v = variants[rng.choice([0, 0, 1, 1, 2, 3])]
        o = bpy.data.objects.new("cc_elo_%d_%d" % (seed, i), v)
        bpy.context.scene.collection.objects.link(o)
        o.matrix_world = _frame(T2, Z, pos)
        out.append(o)

    # pontas: placa + rebites + olhal + grilhao
    for end, (p, d, sgn) in enumerate([(p0, dh, 1), (p1, -dh, -1)]):
        sgnu = 0.0 if end == 0 else cat.D
        if end == 0:
            u = cat.u_at(e); T = basis(u); pos = world(u, cat.pt(u)[1])
        else:
            u = cat.u_at(cat.L - e); T = -basis(u); pos = world(u, cat.pt(u)[1])
        # grilhao: plano com normal perpendicular a side (vira 90 graus em relacao ao olhal vertical)
        Zs = T.cross(side)
        me = _link_mesh("cc_grilhao%d_%d" % (seed, end), LS, WS, AS, BS, CS, 8,
                        random.Random(seed * 31 + end), 0.02)
        _put("cc_grilhao_%d_%d" % (seed, end), me, escuro, _frame(T, Zs, pos), out)
        # olhal (plano vertical, eixo longo = d)
        ce = p + d * (plate + LE / 2 - 0.02 * S)
        me = _link_mesh("cc_olhal%d_%d" % (seed, end), LE, WE, AE, BE, CE, 6,
                        random.Random(seed * 37 + end), 0.02)
        _put("cc_olhal_%d_%d" % (seed, end), me, escuro, _frame(d, side, ce), out)
        # placa e rebites (normal = d)
        pm = _box_mesh("cc_placa%d_%d" % (seed, end), (plate, 0.15 * S, 0.17 * S), 0.006 * S)
        mw = _frame(d, up, p + d * plate / 2)
        _put("cc_placa_%d_%d" % (seed, end), pm, escuro, mw, out)
        for sy in (-1, 1):
            for sz in (-1, 1):
                rm = _rivet_mesh("cc_rebite%d_%d_%d%d" % (seed, end, sy, sz), 0.012 * S, 0.012 * S)
                loc = p + d * (plate + 0.004 * S) + side * (sy * 0.050 * S) + up * (sz * 0.062 * S)
                # cone tem eixo Z: alinhar Z com d
                Zr = d
                Xr = up.cross(d).normalized() if abs(d.dot(up)) < 0.99 else Vector((1, 0, 0))
                Yr = Zr.cross(Xr)
                mr = Matrix([[Xr.x, Yr.x, Zr.x, loc.x], [Xr.y, Yr.y, Zr.y, loc.y],
                             [Xr.z, Yr.z, Zr.z, loc.z], [0, 0, 0, 1]])
                _put("cc_rebite_%d_%d_%d%d" % (seed, end, sy, sz), rm, ferro, mr, out)
    return out
