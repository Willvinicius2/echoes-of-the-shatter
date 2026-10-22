"""Piso da Cripta, parte LAJOTAS E JUNTAS (v2: desnivel, rachaduras abertas, quinas faltando).
Cada lajota e um contorno XY proprio (quinas mordidas, entalhes, juntas de largura irregular), topo triangulado por Delaunay
com altura propria (desnivel, inclinacao, afundadas, lascas rasas) e chanfro irregular; algumas se partem ao meio por uma
fenda aberta com as metades defasadas. plano() expoe o que foi decidido (usado pelo desgaste para pôr cascalho).
VELHO:
Cada lajota do comum.layout() vira uma malha real: topo ondulado com altura propria, chanfro irregular e desigual
por aresta (largura e profundidade variam ao longo da aresta), lascas/dentes, cantos arredondados e gastos, laterais
verticais ruidosas. A junta e uma placa de argamassa/terra afundada ~3 cm, com ruido de altura periodico (emenda sem costura).
Materiais: M_Piso_Laje_A..D (azul-ardosia escuro) + M_Piso_Junta. Determinístico (seed fixo)."""
import bpy, bmesh, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum
from comum import TILE

SEED = 20261022
PROF_JUNTA = 0.045         # topo da junta abaixo do topo das lajotas
CORES = {                  # azul-ardosia escuro, linear sRGB; tons diferentes por lajota
    "A": (0.052, 0.068, 0.100),
    "B": (0.040, 0.054, 0.082),
    "C": (0.068, 0.082, 0.115),
    "D": (0.058, 0.066, 0.084),
}
COR_JUNTA = (0.011, 0.010, 0.010)

# ---------------------------------------------------------------- utilidades
from mathutils import Vector, geometry

class Onda:
    """Ruido suave 2D como soma de senos com fases aleatorias (barato e deterministico)."""
    def __init__(self, r, n=4, f0=1.0, f1=9.0):
        self.t = [(r.uniform(f0, f1), r.uniform(0, 6.283), r.uniform(0.4, 1.0), r.uniform(0, 6.283)) for _ in range(n)]
        self.norm = sum(a for _, _, a, _ in self.t)
    def v2(self, x, y):
        return sum(a * math.sin(f * (x * math.cos(q) + y * math.sin(q)) + p) for f, p, a, q in self.t) / self.norm

Z_BASE = -0.13
Z_MEIO = -0.06

# ---------------------------------------------------------------- planejamento (quem e desnivelada, rachada, mordida)
_PLANO = {}

def _jag(r, a, b, n=None):
    """Caminho irregular de (a,0) a (0,b) em coords locais do canto (mordida angulosa que entra na lajota)."""
    n = n or r.choice([3, 4, 4, 5])
    pts = [(a, 0.0)]
    for k in range(1, n + 1):
        t = k / (n + 1)
        bulge = r.uniform(0.55, 1.15) * (1 - t) ** 0.6 * t ** 0.6 * 2.0   # puxa para dentro
        px = a * (1 - t) * r.uniform(0.75, 1.1) + a * 0.0
        py = b * t * r.uniform(0.75, 1.1)
        px = a * (1 - t); py = b * t
        px += bulge * 0.22 * a * r.uniform(0.3, 1.0); py += bulge * 0.22 * b * r.uniform(0.3, 1.0)
        px += r.uniform(-0.12, 0.12) * a; py += r.uniform(-0.12, 0.12) * b
        pts.append((max(px, 0.01), max(py, 0.01)))
    pts.append((0.0, b))
    return pts

def plano():
    """dict indice_da_lajota -> spec. Cacheado, deterministico."""
    if _PLANO: return _PLANO
    lajes = comum.layout()
    r = random.Random(SEED + 5)
    cand = [i for i, l in enumerate(lajes) if not l["cortada"] and min(l["x1"] - l["x0"], l["y1"] - l["y0"]) > 0.8]
    r.shuffle(cand)
    sunk = set(cand[:2]); tilt = set(cand[2:9]); low = set(cand[9:16])
    crackable = [i for i in cand[16:] if max(lajes[i]["x1"] - lajes[i]["x0"], lajes[i]["y1"] - lajes[i]["y0"]) > 1.25 and min(lajes[i]["x1"] - lajes[i]["x0"], lajes[i]["y1"] - lajes[i]["y0"]) > 0.85]
    crack = set(crackable[:13])
    # garante rachadas tambem entre as inclinadas/baixas para legibilidade variada
    for i, l in enumerate(lajes):
        rl = random.Random(SEED * 131 + i * 17 + 3)
        W = l["x1"] - l["x0"]; H = l["y1"] - l["y0"]
        s = dict(i=i, l=l, rng_seed=SEED * 977 + i * 31, dz=-rl.uniform(0.0, 0.004), tx=0.0, ty=0.0, bites=[], flat=True, crack=None,
                 inset={k: (rl.uniform(0.0, 0.006) if rl.random() < 0.6 else rl.uniform(0.012, 0.026)) for k in "lrbt"})
        if l["cortada"]:
            s["dz"] = -random.Random(SEED + l["id"] * 13).uniform(0.0, 0.004)
            s["inset"] = {k: 0.0 for k in "lrbt"}
            _PLANO[i] = s; continue
        if i in sunk:
            s["dz"] = -rl.uniform(0.032, 0.040); s["tx"] = rl.uniform(-0.012, 0.012) / W; s["ty"] = rl.uniform(-0.012, 0.012) / H; s["flat"] = False
        elif i in tilt:
            m = rl.uniform(0.022, 0.038); ang = rl.uniform(0, 6.283)   # queda maxima nos cantos (m)
            s["tx"] = math.cos(ang) * m / (W / 2); s["ty"] = math.sin(ang) * m / (H / 2); s["dz"] = -m * 0.55; s["flat"] = False
        elif i in low:
            s["dz"] = -rl.uniform(0.024, 0.040); s["flat"] = False
        elif rl.random() < 0.3:
            s["dz"] = -rl.uniform(0.010, 0.018); s["flat"] = False
        # mordidas de canto
        cantos = [(l["x0"], l["y0"], 1, 1), (l["x1"], l["y0"], -1, 1), (l["x1"], l["y1"], -1, -1), (l["x0"], l["y1"], 1, -1)]
        big = rl.random() < 0.25
        for ci, (cx, cy, sx, sy) in enumerate(cantos):
            if rl.random() < (0.4 if not big else 0.8):
                a = rl.uniform(0.14, 0.36) * (1.4 if big and rl.random() < 0.5 else 1.0); b = rl.uniform(0.14, 0.36) * (1.4 if big and rl.random() < 0.5 else 1.0)
                a = min(a, W * 0.45); b = min(b, H * 0.45)
                s["bites"].append(dict(ci=ci, cx=cx, cy=cy, sx=sx, sy=sy, a=a, b=b, path=_jag(rl, a, b)))
        if i in crack:
            horiz = H > W
            if horiz: P = (l["x0"], l["y0"] + rl.uniform(0.35, 0.65) * H); Q = (l["x1"], l["y0"] + rl.uniform(0.35, 0.65) * H)
            else:     P = (l["x0"] + rl.uniform(0.35, 0.65) * W, l["y0"]); Q = (l["x0"] + rl.uniform(0.35, 0.65) * W, l["y1"])
            s["crack"] = dict(P=P, Q=Q, gap=rl.uniform(0.022, 0.034), d1=rl.uniform(-0.016, 0.0), d2=rl.uniform(-0.016, 0.004),
                              t1=rl.uniform(-0.012, 0.012), t2=rl.uniform(-0.012, 0.012)); s["flat"] = False
        _PLANO[i] = s
    return _PLANO

def altura_base(s, x, y):
    """altura do plano da lajota (sem ruido) no ponto; para apoiar cascalho."""
    l = s["l"]; cx = (l["x0"] + l["x1"]) / 2; cy = (l["y0"] + l["y1"]) / 2
    return s["dz"] + s["tx"] * (x - cx) + s["ty"] * (y - cy)

# ---------------------------------------------------------------- contorno XY
def _edge(r, A, B, n_in, notch=None):
    """pontos intermediarios entre A e B (exclusivos), densos o bastante para variar o chanfro; n_in = normal interna."""
    A = Vector(A); B = Vector(B); L = (B - A).length; d = (B - A) / max(L, 1e-9)
    out = []
    ts = []
    n = max(1, int(L / 0.16)); ts = [(k + r.uniform(-0.2, 0.2)) / n for k in range(1, n)]
    if notch:
        tc, w, dep = notch; ts = [t for t in ts if abs(t - tc) > (w * 1.2) / L]
        for f, dd in ((-1.0, 0.0), (-0.55, 0.45), (-0.2, 1.0), (0.25, 0.85), (0.6, 0.4), (1.0, 0.0)):
            ts.append(tc + f * w / L)
        ts = sorted(ts)
        pts = []
        for t in ts:
            p = A + d * (t * L)
            if abs(t - tc) <= w / L * 1.0001:
                f = (t - tc) * L / w; dd = max(0.0, 1 - abs(f)) ** 0.7 * dep * r.uniform(0.8, 1.15)
                p = p + n_in * dd
            pts.append(p)
        return [(p.x, p.y) for p in pts]
    for t in ts:
        p = A + d * (t * L) + n_in * r.uniform(-0.003, 0.003); out.append((p.x, p.y))
    return out

def _contorno(s, r):
    """Poligono CCW da lajota inteira (sem rachadura): retangulo com insets irregulares, mordidas e entalhes."""
    l = s["l"]; ins = s["inset"]
    x0, x1 = l["x0"] + ins["l"], l["x1"] - ins["r"]; y0, y1 = l["y0"] + ins["b"], l["y1"] - ins["t"]
    W = x1 - x0; H = y1 - y0
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    bites = {b["ci"]: b for b in s["bites"]}
    # pontos de saida/entrada de cada canto, em CCW: entrada (vindo da aresta anterior) e saida (indo para a proxima)
    entr, said, meio = {}, {}, {}
    for ci in range(4):
        cx, cy = corners[ci]; sx = 1 if ci in (0, 3) else -1; sy = 1 if ci in (0, 1) else -1
        b = bites.get(ci)
        if not b: entr[ci] = [(cx, cy)]; continue
        a, bb = b["a"], b["b"]
        loc = [(cx + sx * px, cy + sy * py) for px, py in b["path"]]       # de (a,0) [perna x] a (0,b) [perna y]
        entr[ci] = loc if ci in (1, 3) else list(reversed(loc))             # BR,TL: x->y ; BL,TR: y->x
    out = []
    notch_done = False
    for ci in range(4):
        out += entr[ci]
        cj = (ci + 1) % 4
        A = entr[ci][-1]; B = entr[cj][0]
        n_in = [Vector((0, 1)), Vector((-1, 0)), Vector((0, -1)), Vector((1, 0))][ci]
        notch = None
        if not b_has_crack(s) and not notch_done and r.random() < 0.28 and (Vector(B) - Vector(A)).length > 0.7:
            L = (Vector(B) - Vector(A)).length
            notch = (r.uniform(0.3, 0.7), r.uniform(0.05, 0.11), r.uniform(0.035, 0.085)); notch_done = True
            tp = Vector(A) + (Vector(B) - Vector(A)) * notch[0]
            s["bites"].append(dict(ci=-1, cx=tp.x, cy=tp.y, sx=0, sy=0, a=notch[1], b=notch[2], path=None))
        out += _edge(r, A, B, n_in, notch)
    return out

def b_has_crack(s): return s["crack"] is not None

def _meia_pecas(s, poly, r):
    """Divide o contorno pela rachadura; devolve [(poly, dz_extra, tx, ty)]. Sem rachadura: [(poly,0,0,0)]."""
    c = s["crack"]
    if not c: return [(poly, 0.0, 0.0, 0.0)]
    P, Q = Vector(c["P"]), Vector(c["Q"])
    # caminho em ziguezague de P a Q
    L = (Q - P).length; d = (Q - P) / L; n = Vector((-d.y, d.x))
    m = max(5, int(L / 0.075)); path = [P]
    off = 0.0
    for k in range(1, m):
        off += r.gauss(0, 0.014); off *= 0.8
        if r.random() < 0.15: off += r.choice([-1, 1]) * r.uniform(0.02, 0.045)
        off = max(-0.12, min(0.12, off))
        path.append(P + d * (L * k / m + r.uniform(-0.01, 0.01)) + n * off)
    path.append(Q)
    # insere P e Q (projetados) no contorno
    def inserir(poly, p):
        best = None
        for k in range(len(poly)):
            a = Vector(poly[k]); b = Vector(poly[(k + 1) % len(poly)]); ab = b - a
            t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-12))); q = a + ab * t
            dd = (q - p).length
            if best is None or dd < best[0]: best = (dd, k, q, ab.normalized())
        _, k, q, ed = best
        poly = poly[:k + 1] + [(q.x, q.y)] + poly[k + 1:]
        return poly, k + 1, q, ed
    poly, ip, Pp, edP = inserir(list(poly), P)
    poly, iq, Qp, edQ = inserir(poly, Q)
    if iq <= ip: ip += 1 if False else 0
    # reencontra indices (a insercao de Q pode ter deslocado ip)
    ip = next(k for k, p in enumerate(poly) if abs(p[0] - Pp.x) < 1e-9 and abs(p[1] - Pp.y) < 1e-9)
    iq = next(k for k, p in enumerate(poly) if abs(p[0] - Qp.x) < 1e-9 and abs(p[1] - Qp.y) < 1e-9)
    def trecho(i, j):
        out = [poly[i]]; k = i
        while k != j: k = (k + 1) % len(poly); out.append(poly[k])
        return out
    g = c["gap"] / 2
    def lado(sign, ini, fim):
        # caminho deslocado para o lado 'sign' (+1 esquerda de P->Q)
        pp = []
        for k, p in enumerate(path):
            a = path[max(k - 1, 0)]; b = path[min(k + 1, len(path) - 1)]
            t = (b - a).normalized(); nn = Vector((-t.y, t.x)) * sign
            pp.append(p + nn * g * r.uniform(0.75, 1.25) if 0 < k < len(path) - 1 else p + nn * g)
        pp[0] = Pp + edP * ((pp[0] - Pp).dot(edP)); pp[-1] = Qp + edQ * ((pp[-1] - Qp).dot(edQ))
        return pp
    # metade A = contorno de P a Q (CCW) + caminho de volta; metade B = contorno de Q a P + caminho de ida
    A = trecho(ip, iq); B = trecho(iq, ip)
    cA = Vector(c_centroide(A)); sA = 1 if (cA - P).dot(n) > 0 else -1
    pa = lado(sA, 0, 0); pb = lado(-sA, 0, 0)
    pecaA = A[1:-1] if False else A
    # troca extremos pelas pontas deslocadas
    pecaA = [(pa[0].x, pa[0].y)] + A[1:-1] + [(pa[-1].x, pa[-1].y)] + [(p.x, p.y) for p in reversed(pa[1:-1])]
    pecaB = [(pb[-1].x, pb[-1].y)] + B[1:-1] + [(pb[0].x, pb[0].y)] + [(p.x, p.y) for p in pb[1:-1]]
    return [(pecaA, c["d1"], c["t1"], c["t1"] * 0.4), (pecaB, c["d2"], -c["t2"], c["t2"] * 0.7)]

def c_centroide(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

# ---------------------------------------------------------------- uma peca (poligono CCW -> malha)
def _area(poly):
    return 0.5 * sum(poly[k][0] * poly[(k + 1) % len(poly)][1] - poly[(k + 1) % len(poly)][0] * poly[k][1] for k in range(len(poly)))

def _dentro(poly, x, y):
    c = False; n = len(poly)
    for k in range(n):
        ax, ay = poly[k]; bx, by = poly[(k + 1) % n]
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax: c = not c
    return c

def _dist_borda(poly, x, y):
    best = 9.0; n = len(poly)
    for k in range(n):
        ax, ay = poly[k]; bx, by = poly[(k + 1) % n]; dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / max(dx * dx + dy * dy, 1e-12)))
        best = min(best, math.hypot(x - ax - dx * t, y - ay - dy * t))
    return best

def _inset(poly, ch):
    n = len(poly); out = []
    for k in range(n):
        p0 = Vector(poly[k - 1]); p1 = Vector(poly[k]); p2 = Vector(poly[(k + 1) % n])
        e1 = (p1 - p0).normalized(); e2 = (p2 - p1).normalized()
        n1 = Vector((-e1.y, e1.x)); n2 = Vector((-e2.y, e2.x))      # normal interna (CCW)
        m = n1 + n2
        if m.length < 1e-6: m = n1
        m.normalize(); k_ = ch[k] / max(0.5, m.dot(n1))
        out.append((p1.x + m.x * k_, p1.y + m.y * k_))
    return out

def peca(bm, poly, s, r, dz, tx, ty):
    """poly CCW. Topo: anel externo (pe do chanfro) + anel interno + Delaunay com pontos internos; paredes ate a base."""
    if _area(poly) < 0: poly = list(reversed(poly))
    # limpa pontos quase repetidos
    lim = []
    for p in poly:
        if not lim or math.hypot(p[0] - lim[-1][0], p[1] - lim[-1][1]) > 0.006: lim.append(p)
    if len(lim) > 2 and math.hypot(lim[0][0] - lim[-1][0], lim[0][1] - lim[-1][1]) <= 0.006: lim.pop()
    poly = lim
    l = s["l"]; cx0 = (l["x0"] + l["x1"]) / 2; cy0 = (l["y0"] + l["y1"]) / 2
    on = Onda(r, 3, 2.0, 9.0)
    flakes = []
    for _ in range(r.choice([0, 1, 1, 2]) if not l["cortada"] else r.choice([0, 1])):
        k = r.randrange(len(poly)); px, py = poly[k]
        ang = r.uniform(0, 6.283); flakes.append((px, py, math.cos(ang), math.sin(ang), r.uniform(0.12, 0.28), r.uniform(0.012, 0.028), r.uniform(0.8, 1.4)))
    def zf(x, y):
        z = s["dz"] + dz + (tx + s["tx"]) * (x - cx0) + (ty + s["ty"]) * (y - cy0) + 0.0022 * on.v2(x, y)
        for px, py, nx, ny, sz, dep, kl in flakes:
            dx, dy = x - px, y - py; t = dx * nx + dy * ny; lat = abs(-dx * ny + dy * nx)
            zc = s["dz"] + dz - dep + (max(t, 0.0) + kl * lat) * dep / sz * 1.1
            if zc < z: z = zc
        return min(z, 0.0)
    n = len(poly)
    ch = [0.009 + 0.011 * (0.5 + 0.5 * math.sin(k * 1.7 + r.uniform(0, 6))) * r.uniform(0.6, 1.2) for k in range(n)]
    inner = _inset(poly, ch)
    if _area(inner) <= 0.002: inner = _inset(poly, [min(c, 0.004) for c in ch])
    # pontos internos
    xs = [p[0] for p in inner]; ys = [p[1] for p in inner]
    step = 0.105; pts = list(inner)
    gx = min(xs) + step / 2
    while gx < max(xs):
        gy = min(ys) + step / 2
        while gy < max(ys):
            x = gx + r.uniform(-0.03, 0.03); y = gy + r.uniform(-0.03, 0.03)
            if _dentro(inner, x, y) and _dist_borda(inner, x, y) > 0.05: pts.append((x, y))
            gy += step
        gx += step
    vin = [Vector(p) for p in pts]
    res = geometry.delaunay_2d_cdt(vin, [(k, (k + 1) % len(inner)) for k in range(len(inner))], [], 3, 1e-5)
    rv, rf = res[0], res[2]
    # tipo 3 = apenas triangulos dentro do contorno fechado (arestas obrigatorias)
    top = [bm.verts.new((v.x, v.y, zf(v.x, v.y))) for v in rv]
    for f in rf:
        if len(f) == 3:
            ff = [top[f[0]], top[f[1]], top[f[2]]]
            a_, b_, c_ = (v.co for v in ff)
            if (b_ - a_).cross(c_ - a_).z < 0: ff.reverse()
            try: bm.faces.new(ff)
            except ValueError: pass
    # anel externo (pe do chanfro), meio e base
    O = [bm.verts.new((p[0], p[1], zf(p[0], p[1]) - ch[k] * r.uniform(0.7, 1.3) * 0.9)) for k, p in enumerate(poly)]
    M = [bm.verts.new((p[0] + r.uniform(-0.002, 0.002), p[1] + r.uniform(-0.002, 0.002), Z_MEIO + r.uniform(-0.004, 0.004))) for p in poly]
    B = [bm.verts.new((p[0], p[1], Z_BASE)) for p in poly]
    for k in range(n):
        k2 = (k + 1) % n
        for a, b, c, d in ((O[k], O[k2], top[k2], top[k]), (M[k], M[k2], O[k2], O[k]), (B[k], B[k2], M[k2], M[k])):
            try: bm.faces.new((a, b, c, d))
            except ValueError: pass

def preparar():
    """Calcula contornos (e entalhes) de todas as lajotas uma vez; desgaste chama isto antes de ler plano()."""
    for i, s in plano().items():
        if "_c" not in s:
            r = random.Random(s["rng_seed"]); s["_c"] = _contorno(s, r); s["_rs"] = r.getstate()

def lajota(bm, s):
    preparar()
    r = random.Random(); r.setstate(s["_rs"])
    poly = s["_c"]
    for pol, dz, tx, ty in _meia_pecas(s, poly, r):
        peca(bm, pol, s, r, dz, tx, ty)

# ---------------------------------------------------------------- junta
def junta(bm):
    r = random.Random(SEED + 99)
    # ondas com numero de ciclos inteiro em TILE => periodico
    ondas = [(r.randint(2, 9), r.randint(2, 9), r.uniform(0, 6.28), r.uniform(0.4, 1)) for _ in range(6)]
    fino = [(r.randint(14, 30), r.randint(14, 30), r.uniform(0, 6.28), r.uniform(0.4, 1)) for _ in range(5)]
    def z(x, y):
        s = sum(a * math.sin(2 * math.pi * (i * x + j * y) / TILE + p) for i, j, p, a in ondas) / 3.2
        t = sum(a * math.sin(2 * math.pi * (i * x + j * y) / TILE + p) for i, j, p, a in fino) / 3.0
        return -PROF_JUNTA + 0.003 * s + 0.002 * t
    n = 64
    V = {}
    for i in range(n):
        for j in range(n):
            V[(i, j)] = bm.verts.new((TILE * i / n, TILE * j / n, z(TILE * i / n, TILE * j / n)))
    # a ultima linha/coluna repete a primeira: valores identicos por periodicidade
    for i in range(n): V[(i, n)] = bm.verts.new((TILE * i / n, TILE, z(TILE * i / n, TILE)))
    for j in range(n + 1): V[(n, j)] = bm.verts.new((TILE, TILE * j / n, z(TILE, TILE * j / n)))
    for i in range(n):
        for j in range(n):
            bm.faces.new((V[(i, j)], V[(i + 1, j)], V[(i + 1, j + 1)], V[(i, j + 1)]))

# ---------------------------------------------------------------- API
def _aresta_viva(bm, graus=0):
    """Sombreamento plano: facetas e arestas vivas, sem suavizar normais."""
    for f in bm.faces: f.smooth = False

def construir():
    r = random.Random(SEED)
    mats = {k: comum.material("M_Piso_Laje_" + k, c, rough=0.78) for k, c in CORES.items()}
    mj = comum.material("M_Piso_Junta", COR_JUNTA, rough=1.0)
    bms = {k: bmesh.new() for k in CORES}
    sp = plano()
    for i in sorted(sp):
        l = sp[i]["l"]
        k = "ABCD"[(l["id"] * 5 + 1) % 4] if l["cortada"] else random.Random(SEED * 31 + i * 7).choice("ABCD")
        lajota(bms[k], sp[i])
    objs = []
    for k, bm in bms.items():
        _aresta_viva(bm)
        objs.append(comum.novo_objeto("Lajotas_" + k, bm, [mats[k]]))
    bj = bmesh.new(); junta(bj); _aresta_viva(bj)
    objs.append(comum.novo_objeto("Junta", bj, [mj]))
    return objs

# ---------------------------------------------------------------- previa (nos procedurais so aqui)
def _materiais_previa():
    for m in bpy.data.materials:
        if not m.name.startswith("M_Piso_") or not m.use_nodes: continue
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        base = tuple(b.inputs["Base Color"].default_value)[:3]
        tc = nt.nodes.new("ShaderNodeTexCoord")
        n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 9 if "Junta" not in m.name else 40
        n1.inputs["Detail"].default_value = 10; n1.inputs["Roughness"].default_value = 0.7
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 160; n2.inputs["Detail"].default_value = 6
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (base[0] * 0.55, base[1] * 0.55, base[2] * 0.6, 1)
        ramp.color_ramp.elements[1].color = (base[0] * 1.45, base[1] * 1.45, base[2] * 1.4, 1)
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.01
        mx = nt.nodes.new("ShaderNodeMath"); mx.operation = 'MULTIPLY_ADD'; mx.inputs[1].default_value = 0.5; mx.inputs[2].default_value = 0.3
        nt.links.new(tc.outputs["Object"], n1.inputs["Vector"]); nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
        nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(n2.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])

def _luz_fria():
    """Luz fria rasante extra (so prévia): realça facetas e chanfros sem a tocha quente."""
    s2 = bpy.data.objects.new("lua_rasante", bpy.data.lights.new("lua_rasante", 'SUN')); s2.data.energy = 3.0; s2.data.color = (0.55, 0.68, 1.0)
    s2.rotation_euler = (math.radians(74), 0, math.radians(-30)); bpy.context.collection.objects.link(s2)

if __name__ == "__main__":
    comum.limpar_cena()
    objs = construir()
    tris = 0
    for o in objs:
        bm = bmesh.new(); bm.from_mesh(o.data); tris += sum(len(f.verts) - 2 for f in bm.faces); bm.free()
    print("TRIANGULOS", tris)
    _materiais_previa()
    bpy.context.scene.view_settings.exposure = 0.0
    saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "previas", "piso")
    saida = os.path.normpath(saida)
    _luz_fria()
    comum.previa(os.path.join(saida, "lajotas_3q.png"), olhar=(4, 4, 0), cam=(9.5, -3.5, 8.5), luz_quente=False)
    comum.previa(os.path.join(saida, "lajotas_rasante.png"), olhar=(3.5, 3.5, 0), cam=(6.5, 0.2, 0.55), lente=40, luz_quente=False)
    comum.previa(os.path.join(saida, "lajotas_close.png"), olhar=(3, 3, 0), cam=(4.0, 1.6, 1.4), lente=50, luz_quente=False)
