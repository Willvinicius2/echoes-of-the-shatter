"""Poses e animações do Carcereiro do Ossuário (idle 6, run 8, attack 8, hit 3, death 8 quadros; 5 direções).

Cada função devolve um estado: dict(pose=juntas em graus, t=deslocamento da raiz no referencial do golem, tilt=(rx, rz) do corpo
todo, olho, extra, cinza, partes_extra). O quadro 3D sai de `quadro(estado, yaw)`.
"""
import math
import zlib
import numpy as np
import render as R
import carcereiro as G

YAW = {'S': 0.0, 'SE': 45.0, 'E': 90.0, 'NE': 135.0, 'N': 180.0}
ORDEM = ['S', 'SE', 'E', 'NE', 'N']
PARTES = G.construir()
SUP = ['tronco', 'cabeca', 'ombreiraL', 'ombreiraR', 'bracoL', 'bracoR', 'antebracoL', 'antebracoR']
I3 = np.eye(3)


def suave(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, k):
    return a + (b - a) * k


def mistura(a, b, k):
    """Mistura dois dicts de pose (graus)."""
    out = {}
    for j in set(a) | set(b):
        x = a.get(j, (0, 0, 0))
        y = b.get(j, (0, 0, 0))
        out[j] = tuple(lerp(x[i], y[i], k) for i in range(3))
    return out


def estado(pose=None, t=(0, 0, 0), tilt=(0, 0), olho=0, extra=None, cinza=None, partes_extra=None, fx=None):
    return dict(pose=pose or {}, t=t, tilt=tilt, olho=olho, extra=extra or {}, cinza=cinza, partes_extra=partes_extra or [], fx=fx)


def elevar_tronco(dy):
    """Sobe (ou desce) o tronco, a cabeça, as ombreiras e os braços sem mexer no quadril."""
    return {g: (I3, None, (0, dy, 0)) for g in SUP}


# ---------------- idle ----------------
def idle(f, n=6):
    p = 2 * math.pi * f / n
    s, c = math.sin(p), math.cos(p)
    pose = {
        'tronco': (1.0 + 1.6 * s, 2.0 * s, 0),
        'cabeca': (-1.0 - 1.4 * s, -2.5 * s, 0),
        'ombroL': (-3 + 2.0 * s, 0, -2.0 - 1.5 * s), 'ombroR': (-3 + 2.0 * s, 0, 2.0 + 1.5 * s),
        'cotoL': (-6 - 2.0 * s, 0, 0), 'cotoR': (-6 - 2.0 * s, 0, 0),
        'ombroPL': (0, 0, 2.0 * s), 'ombroPR': (0, 0, -2.0 * s),
    }
    return estado(pose, extra=elevar_tronco(0.035 * s), olho=1 if f in (4, 5) else 0)


# ---------------- run ----------------
def run(f, n=8):
    p = 2 * math.pi * f / n
    pose = {}
    A = 26.0
    for L, ph in (('L', p), ('R', p + math.pi)):
        sw = math.sin(ph)
        q = -A * sw
        lift = max(0.0, math.cos(ph))
        k = 8 + 42 * lift ** 1.3
        pose['quad' + L] = (q, 0, 0)
        pose['joe' + L] = (k, 0, 0)
        pose['pe' + L] = (-(q + k), 0, 0)
    lean = 6.0
    pose['tronco'] = (lean, 10.0 * math.sin(p), 3.0 * math.cos(2 * p))
    pose['cabeca'] = (-lean * 0.6, -4.0 * math.sin(p), 0)
    for L, ph, sg in (('L', p + math.pi, -1), ('R', p, 1)):
        sw = math.sin(ph)
        pose['ombro' + L] = (-lean - 3 - 8 * sw, 0, sg * (3 + 1.5 * abs(sw)))
        pose['coto' + L] = (-8 - 7 * max(0.0, sw), 0, 0)
        pose['ombroP' + L] = (0, 0, sg * 1.5 * -sw)
    bob = 0.05 * math.cos(2 * p)
    return estado(pose, t=(0, bob, 0), olho=0)


# ---------------- ataque: bate com os dois punhos no chão ----------------
def _braco(mundo, tronco_rx):
    """Ângulo do ombro para o braço ficar em `mundo` graus (negativo = para a frente) com o tronco inclinado."""
    return mundo - tronco_rx


ATAQUE = [
    # tronco, braço (mundo), cotovelo, y da raiz, z da raiz, coxa, joelho, cabeça, olho,
    # giro do tronco (ty) e abertura entre os braços (ds, em graus de ombro: o direito sobe mais, o esquerdo fica mais à frente).
    # Vistos de lado (direção E) os dois braços erguidos se sobrepunham num poste; o giro e a abertura os separam.
    dict(tr=-7, br=-40, co=-24, y=0.00, z=0.00, qd=0, jo=4, ca=3, ol=0, ty=0, ds=0),
    dict(tr=-13, br=-92, co=-30, y=0.05, z=-0.03, qd=0, jo=0, ca=6, ol=0, ty=7, ds=5),
    dict(tr=-19, br=-108, co=-34, y=0.11, z=-0.06, qd=3, jo=-2, ca=9, ol=0, ty=13, ds=10),
    dict(tr=-22, br=-114, co=-26, y=0.13, z=-0.08, qd=4, jo=-3, ca=10, ol=0, ty=13, ds=10),
    dict(tr=12, br=-100, co=-26, y=-0.05, z=0.04, qd=-14, jo=40, ca=-4, ol=0, ty=5, ds=3),
    dict(tr=36, br=-24, co=-10, y=-0.16, z=0.12, qd=-26, jo=62, ca=-16, ol=0, ty=0, ds=0),
    dict(tr=38, br=-22, co=-8, y=-0.18, z=0.13, qd=-26, jo=66, ca=-14, ol=0, ty=0, ds=0),
    dict(tr=18, br=-18, co=-12, y=-0.08, z=0.06, qd=-20, jo=47, ca=-5, ol=0, ty=0, ds=0),
]


def ataque(f, n=8):
    a = ATAQUE[f]
    pose = {'tronco': (a['tr'], a['ty'], 0), 'cabeca': (a['ca'], -0.5 * a['ty'], 0)}
    for L, sg in (('L', -1), ('R', 1)):
        br = a['br'] - sg * a['ds'] * 0.5     # direito (sg = 1): mais para o alto (mais negativo); esquerdo: mais à frente
        pose['ombro' + L] = (_braco(br, a['tr']), 0, sg * 3)
        pose['coto' + L] = (a['co'], 0, 0)
        pose['ombroP' + L] = (_braco(br, a['tr']) * 0.28, 0, 0)
        pose['quad' + L] = (a['qd'], 0, 0)
        pose['joe' + L] = (a['jo'], 0, 0)
        pose['pe' + L] = (-(a['qd'] + a['jo']), 0, 0)
    fx = ('impacto', f) if f >= 5 else None
    return estado(pose, t=(0, a['y'], a['z']), olho=a['ol'], fx=fx)


# ---------------- ferido ----------------
HIT = [
    dict(tr=-10, y=-0.02, z=-0.10, br=8, qd=4, jo=8, ca=-12),
    dict(tr=-16, y=-0.06, z=-0.17, br=14, qd=8, jo=14, ca=-18),
    dict(tr=-6, y=-0.02, z=-0.07, br=4, qd=2, jo=5, ca=-6),
]


def ferido(f, n=3):
    a = HIT[f]
    pose = {'tronco': (a['tr'], 0, 0), 'cabeca': (a['ca'], 0, 0)}
    for L, sg in (('L', -1), ('R', 1)):
        pose['ombro' + L] = (_braco(a['br'] - 10, a['tr']), 0, sg * (8 + 2 * f))
        pose['coto' + L] = (-14, 0, 0)
        pose['ombroP' + L] = (0, 0, sg * -3)
        pose['quad' + L] = (a['qd'], 0, 0)
        pose['joe' + L] = (a['jo'], 0, 0)
        pose['pe' + L] = (-(a['qd'] + a['jo']), 0, 0)
    return estado(pose, t=(0, a['y'], a['z']), olho=0)


# ---------------- poeira (desenhada em 2D, só nos pixels vazios) ----------------
def _px(p):
    """Ponto do mundo -> pixel do quadro."""
    return (R.PIVO[0] + float(p @ R.RX) * R.ESC, R.PIVO[1] - float(p @ R.U) * R.ESC)


def _bolha(img, cx, cy, r, rng, claro=0):
    """Nuvem de pó: círculos que se sobrepõem, tom médio, brilho em cima à esquerda e sombra embaixo à direita."""
    H, W = img.shape[:2]
    cy = min(cy, H - 4 - r * 1.35)      # a nuvem nunca passa da folga de borda do quadro
    cx = min(max(cx, 4 + r * 1.3), W - 4 - r * 1.3)
    ys, xs = np.mgrid[0:H, 0:W]
    tons = [R.IDX['pedra'][0], R.IDX['pedra'][1], R.IDX['pedra'][2]]
    tons = [R.PALETA_NP[i] for i in tons]
    livre = img[..., 3] == 0
    lobos = [(0.0, 0.0, 1.0)]
    for _ in range(2):
        a = rng.uniform(0, 2 * math.pi)
        lobos.append((math.cos(a) * r * 0.55, math.sin(a) * r * 0.35, rng.uniform(0.55, 0.8)))
    corpo = np.zeros((H, W), bool)
    for dx, dy, k in lobos:
        corpo |= ((xs + 0.5 - cx - dx) ** 2 + ((ys + 0.5 - cy - dy) * 1.15) ** 2) <= (r * k) ** 2
    luz = np.zeros((H, W), bool)
    for dx, dy, k in lobos:
        luz |= ((xs + 0.5 - cx - dx + r * 0.28) ** 2 + ((ys + 0.5 - cy - dy + r * 0.3) * 1.15) ** 2) <= (r * k * 0.62) ** 2
    sombra = corpo & ~(((xs + 0.5 - cx + r * 0.2) ** 2 + ((ys + 0.5 - cy - r * 0.35) * 1.15) ** 2) <= (r * 0.95) ** 2)
    m = corpo & livre
    t = 1 + claro
    img[m, :3] = tons[min(t, 2)]
    img[m, 3] = 255
    ml = luz & corpo & livre
    img[ml, :3] = tons[max(t - 1, 0)]
    ms = sombra & corpo & livre
    img[ms, :3] = tons[min(t + 1, 2)]
    return img


def _poeira(img, pontos, tam, espalha, n, seed, claro=0):
    rng = np.random.RandomState(seed)
    for (cx, cy) in pontos:
        for i in range(n):
            a = rng.uniform(0, 2 * math.pi)
            d = rng.uniform(0.3, 1.0) * espalha
            _bolha(img, cx + math.cos(a) * d, cy + math.sin(a) * d * 0.55, tam * rng.uniform(0.7, 1.15), rng, claro)
    return img


# ---------------- quadro 3D ----------------
def quadro(est, yaw, quadro_px=R.QUADRO):
    Ry = R.rot_y(yaw)
    rx, rz = est['tilt']
    Rt = R.euler(rx, 0, rz) if (rx or rz) else I3
    raiz_R = Ry @ Rt
    t = Ry @ np.array(est['t'], float)
    partes = PARTES + est['partes_extra'] if est['partes_extra'] else PARTES
    cena = R.montar_cena(partes, G.JUNTAS, est['pose'], raiz_R, t, est['extra'])
    img = R.sombrear(cena, olho=est['olho'], cinza=est['cinza'])
    fx = est.get('fx')
    if fx:
        tipo, f = fx[0], fx[1]
        seed = zlib.crc32(('%s-%d-%d' % (tipo, f, int(yaw))).encode())
        if tipo == 'impacto':
            d = {c['nome']: c['cen'] for c in cena}
            pts = []
            for nome in ('punhoL', 'marreta'):
                c = d[nome].copy()
                c[1] = 0.0
                pts.append(_px(c))
            if f == 5:
                _poeira(img, pts, 5.0, 7, 4, seed)
            elif f == 6:
                _poeira(img, pts, 7.5, 12, 5, seed)
            elif f == 7:
                _poeira(img, pts, 6.5, 16, 4, seed, claro=-1)
        elif tipo == 'desmoronar':
            pts = []
            for g, (pf, ang, fs, fe) in FINAL.items():
                if abs(f - fe) < 0.75 or (0 < f - fe <= 1.75):
                    c = Ry @ np.array([pf[0], 0.0, pf[2]]) + t * 0
                    pts.append((_px(c), 1.0 if f - fe <= 0.75 else 0.0))
            frescos = [p for p, fr in pts if fr]
            velhos = [p for p, fr in pts if not fr]
            if frescos:
                _poeira(img, frescos, 4.4, 7, 2, seed)
            if velhos:
                _poeira(img, velhos, 5.4, 10, 2, seed + 1, claro=-1)
    return img


ANIMS = {
    'idle': (idle, 6, 8, True),
    'run': (run, 8, 8, True),
    'attack': (ataque, 8, 10, False),
    'hit': (ferido, 3, 12, False),
}


# ---------------- morte: o golem desmorona num monte de pedras ----------------
# grupo: (posição final do centroide, ângulos finais, quadro em que começa a cair, quadro em que pousa)
FINAL = {
    'cabeca': ((0.10, 0.92, 0.40), (-35, 20, 14), 1.0, 5.0),
    'ombreiraL': ((-0.98, 0.34, -0.15), (10, 25, 38), 1.0, 4.0),
    'ombreiraR': ((0.96, 0.34, -0.20), (10, -20, -34), 1.5, 4.5),
    'bracoL': ((-1.24, 0.26, 0.20), (0, 0, 82), 1.5, 4.5),
    'bracoR': ((1.20, 0.26, 0.12), (0, 0, -78), 2.0, 5.0),
    'antebracoL': ((-0.84, 0.30, 0.92), (-72, 18, 10), 2.0, 5.5),
    'antebracoR': ((0.90, 0.20, 0.86), (-80, -24, -8), 2.5, 6.0),
    'tronco': ((0.0, 0.62, -0.05), (-18, 8, 4), 2.5, 6.0),
    'pelvis': ((0.0, 0.30, -0.02), (0, 14, 0), 3.0, 6.0),
    'coxaL': ((-0.52, 0.30, 0.62), (-14, 28, 18), 3.0, 6.0),
    'coxaR': ((0.50, 0.30, 0.66), (-10, -24, -14), 3.5, 6.5),
    'canelaL': ((-0.84, 0.28, 0.46), (0, 20, 78), 3.5, 6.5),
    'canelaR': ((0.82, 0.28, 0.40), (0, -16, -80), 4.0, 6.5),
    'peL': ((-0.40, 0.14, 1.12), (0, -20, 8), 4.0, 7.0),
    'peR': ((0.42, 0.14, 1.08), (0, 22, -8), 4.5, 7.0),
}

# pedrinhas que saltam: (grupo, posição inicial, velocidade inicial, quadro de saída, raio)
SEIXOS = [
    ((-0.9, 2.5, 0.1), (-1.4, 2.2, 0.8), 1.0, 0.09), ((0.95, 2.45, -0.1), (1.5, 2.0, 0.4), 1.0, 0.08),
    ((0.2, 2.7, 0.2), (0.6, 2.8, 1.4), 1.0, 0.07), ((-0.3, 1.9, 0.4), (-0.8, 1.2, 1.6), 2.0, 0.10),
    ((0.4, 2.0, 0.4), (1.0, 1.0, 1.4), 2.0, 0.09), ((-1.1, 1.5, 0.2), (-1.8, 1.4, 0.6), 2.0, 0.08),
    ((1.1, 1.4, 0.1), (1.6, 1.6, 0.5), 3.0, 0.08), ((0.0, 1.5, 0.5), (0.2, 0.8, 1.8), 3.0, 0.10),
    ((-0.5, 1.2, 0.5), (-1.2, 1.4, 1.2), 3.0, 0.07), ((0.6, 1.3, 0.5), (1.3, 1.2, 1.0), 4.0, 0.07),
]
SEIXO_FINAL = [(-1.3, 0.07, 0.9), (1.3, 0.06, 0.5), (0.7, 0.05, 1.6), (-0.6, 0.08, 1.4), (0.9, 0.07, 1.3), (-1.4, 0.06, 0.4),
               (1.4, 0.06, 0.3), (0.3, 0.08, 1.7), (-1.1, 0.05, 1.2), (1.1, 0.05, 1.1)]
_SEIXO_PARTES = [R.caixa('seixo%d' % i, (0, 0, 0), (s[3], s[3] * 0.8, s[3]), R.PEDRA, ch=0.08, jit=0.08, seed=40 + i, grupo='seixo%d' % i)
                 for i, s in enumerate(SEIXOS)]
G_GRAV = 16.0


def morte(f, n=8):
    # balanço antes de ceder: o corpo recua e depois afunda um pouco
    sag = suave(f / 3.0)
    pose = {'tronco': (-8 * math.sin(min(f, 2) * math.pi / 2) + 6 * sag, 0, 0), 'cabeca': (-10 * (1 - sag) + 8 * sag, 0, 0)}
    for L, sg in (('L', -1), ('R', 1)):
        pose['ombro' + L] = (6 * sag, 0, sg * (6 + 8 * sag))
        pose['coto' + L] = (-8 + 6 * sag, 0, 0)
        pose['quad' + L] = (-8 * sag, 0, 0)
        pose['joe' + L] = (14 * sag, 0, 0)
        pose['pe' + L] = (-6 * sag, 0, 0)
        pose['ombroP' + L] = (0, 0, sg * 10 * sag)
    t = (0, -0.18 * sag, -0.05 * sag)
    cen = R.centroides(PARTES, G.JUNTAS, pose)
    extra = {}
    for g, (pf, ang, fs, fe) in FINAL.items():
        w = suave((f - fs) / (fe - fs))
        if w <= 0:
            continue
        c0 = cen[g]
        # compensa a raiz (descida) para o monte ficar no chão
        dest = np.array(pf) - np.array(t) * (1 - w) * 0
        dxz = (dest - c0) * w
        dy = (dest[1] - c0[1]) * (w * w)
        Rg = R.euler(ang[0] * w, ang[1] * w, ang[2] * w)
        extra[g] = (Rg, None, (dxz[0], dy, dxz[2]))
    seixos = []
    for i, ((p0, v0, fs, r), fin) in enumerate(zip(SEIXOS, SEIXO_FINAL)):
        if f < fs:
            continue
        tau = (f - fs) * 0.1
        pos = np.array([p0[0] + v0[0] * tau, p0[1] + v0[1] * tau - 0.5 * G_GRAV * tau * tau, p0[2] + v0[2] * tau])
        if pos[1] <= fin[1]:
            # no chão: fica onde caiu (ou no ponto final combinado)
            tpouso = (v0[1] + math.sqrt(v0[1] ** 2 + 2 * G_GRAV * (p0[1] - fin[1]))) / G_GRAV
            pos = np.array([p0[0] + v0[0] * tpouso, fin[1], p0[2] + v0[2] * tpouso])
        pp = _SEIXO_PARTES[i]
        # a peça nasce na origem: o extra leva até a posição
        extra['seixo%d' % i] = (np.eye(3), None, tuple(pos))
        seixos.append(pp)
    olho = 0 if f == 0 else (1 if f == 1 else (2 if f == 2 else 3))
    return estado(pose, t=t, olho=olho, extra=extra, partes_extra=seixos, fx=('desmoronar', f) if f >= 3 else None)


ANIMS['death'] = (morte, 8, 10, False)
