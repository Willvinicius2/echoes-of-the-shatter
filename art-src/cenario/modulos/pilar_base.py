"""Soco do pilar da Cripta: 3 degraus de blocos em fiadas, cornija de base do fuste, entulho, lascas e musgo.
Usa só pilar_lib (L). Pivô z=0 no chão, frente = +Y."""
import math


def _r(L, loc, size, m, chip=0.0, **kw):
    """Bloco com lasca limitada a 30% da menor dimensão (evita estilhaços invertidos)."""
    return L.rock(loc, size, m, chip=min(chip, 0.3 * min(size)) if chip else 0.0, **kw)


def _fiada(L, half, z0, h, prof, minw, maxw, falta=0.08, desal=0.025):
    """Uma fiada em anel: blocos de larguras diferentes nos 4 lados; alguns quebrados ou faltando."""
    r = L.rnd
    for lado in range(4):
        a = lado * math.pi / 2
        # lado em coordenadas locais (u ao longo, v para fora); frente = +Y -> a=0 com v em +Y
        ext = half - (prof if lado % 2 else 0)      # laterais encurtadas para não sobrepor os cantos
        u = -ext
        while u < ext - 0.05:
            w = min(r.uniform(minw, maxw), ext - u)
            if ext - u - w < minw * 0.5: w = ext - u
            uc = u + w / 2
            u += w
            if r.random() < falta: continue          # bloco faltando
            hh = h * r.uniform(0.97, 1.0)
            pp = prof * r.uniform(0.96, 1.0)
            vv = half - pp / 2 + r.uniform(-desal, desal)
            if r.random() < 0.10:                    # bloco quebrado: mais baixo e curto
                hh *= r.uniform(0.7, 0.88); w *= r.uniform(0.8, 0.95)
            c, s_ = math.cos(a), math.sin(a)
            x = uc * c - vv * s_; y = uc * s_ + vv * c
            m = L.MAT["escura"] if r.random() < 0.12 else L.MAT["pedra"]
            _r(L, (x, y, z0 + hh / 2 + r.uniform(0, 0.004)), (w - 0.035, pp, hh), m,
                   rot=(0, 0, a + r.uniform(-0.006, 0.006)),
                   jit=0.004, bev=0.02, seg=1, chip=r.uniform(0.02, 0.04) if r.random() < 0.55 else 0.0, rough=0.0, cuts_pre=1)


def _laje(L, half, z0, h, nx=3, ny=3):
    """Tampo de degrau: lajes irregulares sobre o miolo."""
    r = L.rnd
    xs = [-half]; 
    for i in range(nx - 1): xs.append(-half + 2 * half * (i + 1) / nx + r.uniform(-0.12, 0.12))
    xs.append(half)
    for i in range(nx):
        ys = [-half]
        for j in range(ny - 1): ys.append(-half + 2 * half * (j + 1) / ny + r.uniform(-0.12, 0.12))
        ys.append(half)
        for j in range(ny):
            w = xs[i + 1] - xs[i]; d = ys[j + 1] - ys[j]
            if r.random() < 0.1: continue
            _r(L, ((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2, z0 - h / 2 + r.uniform(0, 0.02)),
                   (w - 0.03, d - 0.03, h), L.MAT["pedra"], rot=(0, 0, r.uniform(-0.02, 0.02)),
                   jit=0.004, bev=0.01, seg=1, chip=0.05, rough=0.004, cuts_pre=1)


def _rachadura(L, x, y, z, comp, a):
    """Fissura: lasca fina e escura rente à face (girada no plano da face, a = lado)."""
    r = L.rnd
    ty = r.uniform(-1.0, 1.0)
    for k in range(3):
        t = (k - 1) * comp / 3
        tx, ty2 = math.cos(a) * t * math.cos(ty), math.sin(a) * t * math.cos(ty)
        _r(L, (x + tx, y + ty2, z + t * math.sin(ty) + r.uniform(-.01, .01)), (comp / 3 * 1.15, 0.03, 0.028),
           L.MAT["escura"], rot=(0, ty + r.uniform(-.3, .3), a), jit=0.05, bev=0.0, cuts=0)


def _calota(L, x, y, z, rx, ry, rz, ph=0.0):
    """Calota de musgo: meia esfera achatada de poucas faces, meio enterrada."""
    import bmesh
    from mathutils import Matrix
    lim = 1.69 - max(rx, ry) * 1.1
    x = max(-lim, min(lim, x)); y = max(-lim, min(lim, y))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=1.0)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z < -0.15], context='FACES')
    for v in bm.verts:
        v.co.x *= rx; v.co.y *= ry; v.co.z *= rz
        v.co.x += L.rnd.uniform(-.1, .1) * rx; v.co.y += L.rnd.uniform(-.1, .1) * ry
    bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y, z)) @ Matrix.Rotation(ph, 4, 'Z'), verts=bm.verts)
    return L.from_bm(bm, L.MAT["musgo"], "musgo")


def _tufo(L, x, y, z, r, n=5, dir=None):
    """Tufo irregular: várias calotas pequenas sobrepostas. dir=(dx,dy): empurra para fora (musgo em junta de face vertical)."""
    rr = L.rnd
    for _ in range(n):
        ox, oy = rr.uniform(-r, r), rr.uniform(-r, r)
        s = r * rr.uniform(0.45, 0.9)
        _calota(L, x + ox, y + oy, z + rr.uniform(0, 0.02), s, s * rr.uniform(.7, 1.3), s * rr.uniform(.35, .6), rr.uniform(0, 6.28))


def _pedaco(L, x, y, z, s, grande=False):
    """Pedaço caído: casco lascado achatado."""
    r = L.rnd
    lim = 1.69 - s * 1.4
    x = max(-lim, min(lim, x)); y = max(-lim, min(lim, y))
    m = L.MAT["escura"] if r.random() < 0.15 else L.MAT["pedra"]
    L.boulder((x, y, z + s * 0.35), (s * 1.5, s * 1.3, s * 1.1), m,
              rot=(r.uniform(-.3, .3), r.uniform(-.3, .3), r.uniform(0, 6.28)), pts=r.randint(12, 16), bev=0.01, flat=0.3)


def build(L):
    r = L.rnd
    # degraus de lajes retas: (meia pegada, z0, altura total, profundidade, largura min, max)
    deg = [(1.68, 0.0, 0.38, 0.50, 0.55, 1.05),
           (1.50, 0.38, 0.32, 0.45, 0.5, 0.95),
           (1.30, 0.70, 0.27, 0.40, 0.45, 0.85)]
    for half, z0, h, prof, mn, mx in deg:
        if z0 == 0.0:      # 1.º degrau em duas fiadas com juntas desencontradas
            _fiada(L, half, z0, h / 2, prof, mn, mx, falta=0.0, desal=0.015)
            _fiada(L, half, z0 + h / 2, h / 2, prof, mn * 0.9, mx, falta=0.0, desal=0.015)
        else:
            _fiada(L, half, z0, h, prof, mn, mx, falta=0.0, desal=0.015)
    # miolos escuros por degrau (aparecem nas juntas)
    for hf, z0, z1 in ((1.30, 0, 0.38), (1.12, 0.38, 0.70), (0.95, 0.70, 0.97)):
        _r(L, (0, 0, (z0 + z1) / 2), (2 * hf, 2 * hf, z1 - z0), L.MAT["escura"], bev=0.0, cuts=0)
    _laje(L, 0.95, 1.0, 0.06, 3, 3)
    # cornija de base do fuste: 2 fiadas (1.0-1.07 e 1.07-1.15)
    _fiada(L, 1.05, 0.97, 0.10, 0.28, 0.35, 0.7, falta=0.0, desal=0.01)
    _fiada(L, 0.97, 1.06, 0.09, 0.22, 0.3, 0.6, falta=0.0, desal=0.01)
    # entulho pouco: só nos 4 cantos (1 médio + 1-2 pequenos) e 2 lascas nas bordas
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        _pedaco(L, sx * 1.52, sy * 1.52, 0.38, r.uniform(0.17, 0.22))
        _pedaco(L, sx * 1.60, sy * 1.36, 0.38, r.uniform(0.07, 0.1))
        if r.random() < 0.6: _pedaco(L, sx * 1.36, sy * 1.60, 0.38, r.uniform(0.06, 0.09))
    _pedaco(L, 0.5, 1.62, 0.38, 0.08)
    _pedaco(L, -0.9, -1.44, 0.70, 0.07)
    # rachaduras nas faces do soco
    for a in (0.0, 1.57, 3.14, 4.71):
        c, s = math.cos(a), math.sin(a)
        for (rad, z) in ((1.68, 0.19), (1.50, 0.54), (1.30, 0.83)):
            u = r.uniform(-0.5, 0.5)
            _rachadura(L, u * c - (rad + 0.005) * s, u * s + (rad + 0.005) * c, z, r.uniform(.2, .4), a)
    # musgo: concentrado nos cantos e na base, tufos nas frestas
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        _tufo(L, sx * 1.58, sy * 1.58, 0.38, 0.17, 7)
        _tufo(L, sx * 1.38, sy * 1.38, 0.70, 0.14, 6)
        _tufo(L, sx * 1.14, sy * 1.14, 0.97, 0.11, 5)
    for half, z in ((1.62, 0.38), (1.42, 0.70), (1.22, 0.97)):
        for _ in range(6):
            a = r.randint(0, 3) * math.pi / 2; u = r.uniform(-half * .8, half * .8)
            c, s = math.cos(a), math.sin(a)
            _tufo(L, u * c - half * s, u * s + half * c, z, 0.1, 4)
    # junta vertical da face do 1.º degrau (musgo colado à pedra)
    for a in (0.0, 1.57, 3.14, 4.71):
        c, s = math.cos(a), math.sin(a)
        for _ in range(2):
            u = r.uniform(-1.3, 1.3)
            _tufo(L, u * c - 1.66 * s, u * s + 1.66 * c, r.uniform(0.06, 0.2), 0.09, 4)
