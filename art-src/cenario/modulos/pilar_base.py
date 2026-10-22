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
            hh = h * r.uniform(0.93, 1.0)
            pp = prof * r.uniform(0.96, 1.0)
            vv = half - pp / 2 + r.uniform(-desal, desal)
            if r.random() < 0.18:                    # bloco quebrado: mais baixo e curto
                hh *= r.uniform(0.7, 0.88); w *= r.uniform(0.8, 0.95)
            c, s_ = math.cos(a), math.sin(a)
            x = uc * c - vv * s_; y = uc * s_ + vv * c
            m = L.MAT["escura"] if r.random() < 0.12 else L.MAT["pedra"]
            _r(L, (x, y, z0 + hh / 2 + r.uniform(0, 0.012)), (w - 0.035, pp, hh), m,
                   rot=(r.uniform(-0.012, 0.012), r.uniform(-0.012, 0.012), a + r.uniform(-0.02, 0.02)),
                   jit=0.012, bev=0.012, seg=1, chip=r.uniform(0.02, 0.04), rough=0.01, cuts_pre=2 if w > 0.75 else 1)


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
                   jit=0.01, bev=0.01, seg=1, chip=0.05, rough=0.01, cuts_pre=1)


def _entulho(L, n, rmin, rmax, zmax_fn, tam=(0.1, 0.34), musgo_p=0.3):
    """Pedaços caídos e lascas em volta; alguns com musgo por cima."""
    r = L.rnd
    for _ in range(n):
        a = r.uniform(0, 2 * math.pi); d = r.uniform(rmin, rmax)
        x, y = d * math.cos(a), d * math.sin(a)
        s = r.uniform(*tam)
        sz = (s * r.uniform(0.8, 1.5), s * r.uniform(0.7, 1.3), s * r.uniform(0.5, 1.0))
        z = zmax_fn(x, y) + max(sz) * 0.5 + 0.03
        m = L.MAT["escura"] if r.random() < 0.2 else L.MAT["pedra"]
        L.boulder((x, y, z), (s * 1.6, s * 1.5, s * 1.3), m, rot=(r.uniform(-.4, .4), r.uniform(-.4, .4), r.uniform(0, 6.28)), pts=r.randint(10, 16), bev=0.008 + 0.02 * s)
        if r.random() < musgo_p:
            _r(L, (x, y, z + sz[2] * 0.4), (sz[0] * 0.7, sz[1] * 0.7, 0.035), L.MAT["musgo"],
                   rot=(0, 0, r.uniform(0, 6.28)), jit=0.12, bev=0.0, cuts=1)


def _musgo(L, n, rmin, rmax, zfn):
    """Tufos de musgo: montinhos achatados de várias camadas."""
    r = L.rnd
    for _ in range(n):
        a = r.uniform(0, 2 * math.pi); d = r.uniform(rmin, rmax)
        x, y = d * math.cos(a), d * math.sin(a)
        z = zfn(x, y)
        for k in range(r.randint(2, 4)):
            s = r.uniform(0.07, 0.2)
            _r(L, (x + r.uniform(-.1, .1), y + r.uniform(-.1, .1), z + 0.012 + k * 0.012),
                   (s, s * r.uniform(.7, 1.3), r.uniform(0.03, 0.06)), L.MAT["musgo"],
                   rot=(0, 0, r.uniform(0, 6.28)), jit=0.12, bev=0.0, cuts=1)


def _rachadura(L, x, y, z, comp, a):
    """Fissura: lasca fina e escura rente à face (girada no plano da face, a = lado)."""
    r = L.rnd
    ty = r.uniform(-1.0, 1.0)
    for k in range(3):
        t = (k - 1) * comp / 3
        tx, ty2 = math.cos(a) * t * math.cos(ty), math.sin(a) * t * math.cos(ty)
        _r(L, (x + tx, y + ty2, z + t * math.sin(ty) + r.uniform(-.01, .01)), (comp / 3 * 1.15, 0.03, 0.028),
           L.MAT["escura"], rot=(0, ty + r.uniform(-.3, .3), a), jit=0.05, bev=0.0, cuts=0)


def build(L):
    r = L.rnd
    # degraus: (meia pegada, z0, altura da fiada, profundidade, largura min, max)
    deg = [(1.6, 0.0, 0.40, 0.55, 0.45, 0.95),
           (1.38, 0.40, 0.30, 0.45, 0.35, 0.8),
           (1.15, 0.70, 0.27, 0.40, 0.35, 0.7)]
    for half, z0, h, prof, mn, mx in deg:
        _fiada(L, half, z0, h, prof, mn, mx)
    # miolos escuros por degrau (aparecem nas juntas e onde falta bloco)
    for hf, z0, z1 in ((1.12, 0, 0.4), (0.96, 0.4, 0.7), (0.80, 0.7, 0.99)):
        _r(L, (0, 0, (z0 + z1) / 2), (2 * hf, 2 * hf, z1 - z0), L.MAT["escura"], bev=0.0, cuts=0)
    # lajes do tampo do 3.º degrau (z=0.97) sob a cornija
    _laje(L, 0.8, 1.0, 0.06, 3, 3)
    # cornija de base do fuste: 2 fiadas (1.0-1.07 e 1.07-1.15)
    _fiada(L, 1.05, 0.97, 0.10, 0.28, 0.35, 0.7, falta=0.0, desal=0.01)
    _fiada(L, 0.97, 1.06, 0.09, 0.22, 0.3, 0.6, falta=0.0, desal=0.01)
    # zonas: z do chão/degrau em função da posição (para o entulho)
    def zf(x, y):
        m = max(abs(x), abs(y))
        return 0.0 if m > 1.6 else 0.4 if m > 1.38 else 0.7 if m > 1.15 else 0.97
    _entulho(L, 6, 1.68, 1.75, lambda x, y: 0.0, (0.12, 0.3))        # no chão, em volta
    _entulho(L, 4, 1.42, 1.58, lambda x, y: 0.4, (0.1, 0.24))         # sobre o 1.º degrau
    _entulho(L, 3, 1.2, 1.34, lambda x, y: 0.7, (0.08, 0.2))        # sobre o 2.º
    _entulho(L, 2, 1.08, 1.14, lambda x, y: 0.97, (0.07, 0.15))      # sobre o 3.º
    # lascas pequenas espalhadas
    _entulho(L, 12, 1.0, 1.72, zf, (0.04, 0.08), 0.1)
    # rachaduras nas faces do soco
    for a in (0.0, 1.57, 3.14, 4.71):
        c, s = math.cos(a), math.sin(a)
        for (rad, z) in ((1.62, 0.2), (1.4, 0.55), (1.17, 0.83)):
            u = r.uniform(-0.5, 0.5)
            _rachadura(L, u * c - (rad + 0.005) * s, u * s + (rad + 0.005) * c, z, r.uniform(.2, .4), a)
    # musgo nas juntas, nos degraus e na base
    _musgo(L, 12, 1.3, 1.7, lambda x, y: 0.0)
    _musgo(L, 10, 1.2, 1.5, lambda x, y: 0.4)
    _musgo(L, 8, 1.0, 1.3, lambda x, y: 0.7)
    _musgo(L, 6, 0.9, 1.1, lambda x, y: 0.97)
