"""Renderizador de pedra para o Arauto de Pedra: peças convexas (planos) e esferas, câmera ortográfica de cima (3/4),
sombreado em degraus com paleta curta, contorno de 1 px. Tudo em numpy, sem serviço pago e sem GPU.

Coordenadas do mundo: x para a direita da tela, y para cima, z para a câmera (a frente do modelo é +z). Origem no centro dos pés.
O desenho é feito com SS amostras por pixel; cada pixel final recebe a cor mais frequente entre as amostras (nada de meio-tom:
só cores da paleta), e o contorno de 1 px sai depois, já na grade final.
"""
import math
import numpy as np

QUADRO = 176
PIVO = (88, 132)
ESC = 31.0                      # px por metro
SS = 3                          # amostras por pixel (por eixo)
PITCH = math.radians(35.0)      # a câmera olha para baixo 35 graus
D = np.array([0.0, -math.sin(PITCH), -math.cos(PITCH)])     # direção dos raios
U = np.array([0.0, math.cos(PITCH), -math.sin(PITCH)])      # "para cima" da tela
RX = np.array([1.0, 0.0, 0.0])
LUZ = np.array([-0.52, 0.78, 0.46])
LUZ = LUZ / np.linalg.norm(LUZ)

# materiais
PEDRA, TERRA, OLHO, CINZA = 0, 1, 2, 3

PAL = {
    # pedra cinza-areia (revisão do Jev em 10/11: 15 a 20% mais escura e menos creme que a primeira prévia) e musgo mais escuro e saturado;
    # o olho âmbar continua sendo o ponto mais claro do desenho
    'pedra': [(182, 175, 158), (152, 145, 130), (120, 111, 100), (88, 79, 77), (60, 51, 57)],
    'musgo': [(140, 166, 50), (98, 126, 40), (68, 90, 36), (46, 62, 34)],
    'terra': [(160, 114, 78), (122, 84, 60), (88, 60, 46), (58, 42, 36)],
    'olho': [(255, 226, 112), (255, 156, 40), (220, 92, 26), (120, 44, 20)],
    'pupila': (50, 16, 8),
    'linha': (40, 30, 28),
    'contorno': (0, 0, 0),
    'cinza': [(140, 134, 126), (110, 104, 100), (82, 76, 76), (58, 54, 56)],
}

# paleta global (índice 0 = vazio)
PALETA = [(0, 0, 0)]
IDX = {}


def _reg(chave, cores):
    IDX[chave] = []
    for c in cores:
        PALETA.append(tuple(c))
        IDX[chave].append(len(PALETA) - 1)


for _k in ('pedra', 'musgo', 'terra', 'olho', 'cinza'):
    _reg(_k, PAL[_k])
_reg('pupila', [PAL['pupila']])
_reg('linha', [PAL['linha']])
_reg('contorno', [PAL['contorno']])
PALETA_NP = np.array(PALETA, np.uint8)


# ---------------- rotações ----------------
def rot_x(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def euler(rx=0.0, ry=0.0, rz=0.0):
    """Aplica x, depois y, depois z (graus)."""
    return rot_z(rz) @ rot_y(ry) @ rot_x(rx)


# ---------------- geometria ----------------
class Parte:
    """Uma peça rígida: poliedro convexo (planos n.x = d) ou esfera. `cadeia` lista as juntas da raiz até a ponta (a pose aplica da ponta para a raiz)."""

    def __init__(self, nome, mat, n=None, d=None, c=None, r=None, musgo=0.0, cadeia=(), grupo=None):
        self.nome, self.mat, self.musgo, self.cadeia = nome, mat, musgo, tuple(cadeia)
        self.n, self.d, self.c, self.r = n, d, c, r
        self.grupo = grupo or nome
        self.c0 = None
        self.raio = 0.0     # raio da esfera que contém a peça (para recortar os raios)


def _semente(nome, seed):
    return (seed * 7919 + sum((i + 1) * ord(ch) for i, ch in enumerate(nome))) % (2 ** 31)


def caixa(nome, c, h, mat=PEDRA, rot=(0, 0, 0), ch=0.12, jit=0.03, musgo=0.0, cadeia=(), seed=0, grupo=None):
    """Caixa chanfrada (pedra lascada): 6 faces, 12 chanfros de aresta e 8 de canto, com leve irregularidade nas distâncias."""
    rng = np.random.RandomState(_semente(nome, seed))
    h = np.array(h, float)
    ch = min(ch, 0.72 * float(h.min()))
    ns, ds = [], []
    for i in range(3):
        for s in (-1, 1):
            n = np.zeros(3)
            n[i] = s
            ns.append(n)
            ds.append(h[i])
    for i in range(3):
        for j in range(i + 1, 3):
            for si in (-1, 1):
                for sj in (-1, 1):
                    n = np.zeros(3)
                    n[i], n[j] = si, sj
                    ns.append(n / math.sqrt(2))
                    ds.append((h[i] + h[j] - ch) / math.sqrt(2))
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                ns.append(np.array([sx, sy, sz]) / math.sqrt(3))
                ds.append((h.sum() - 1.7 * ch) / math.sqrt(3))
    n = np.array(ns)
    d = np.array(ds) * (1.0 + jit * (rng.random_sample(len(ds)) * 2 - 1))
    R = euler(*rot)
    n = n @ R.T
    c = np.array(c, float)
    d = d + n @ c
    p = Parte(nome, mat, n=n, d=d, musgo=musgo, cadeia=cadeia, grupo=grupo)
    p.c0 = c
    p.raio = float(np.linalg.norm(h)) * (1.0 + jit)
    return p


def esfera(nome, c, r, mat=TERRA, musgo=0.0, cadeia=(), grupo=None):
    p = Parte(nome, mat, c=np.array(c, float), r=float(r), musgo=musgo, cadeia=cadeia, grupo=grupo)
    p.c0 = np.array(c, float)
    p.raio = float(r)
    return p


# ---------------- pose ----------------
def aplicar_junta(n, d, c, R, pivo, t=(0, 0, 0)):
    """x' = R (x - pivo) + pivo + t, para planos (n, d) e centro de esfera c."""
    pivo = np.array(pivo, float)
    t = np.array(t, float)
    if n is not None:
        n2 = n @ R.T
        d2 = d - n @ pivo + n2 @ (pivo + t)
    else:
        n2 = d2 = None
    c2 = None if c is None else R @ (c - pivo) + pivo + t
    return n2, d2, c2


def montar_cena(partes, juntas, pose, raiz_R, raiz_t, extra=None):
    """Lista de peças já na pose: dicts com n, d (ou c, r), mat, musgo, A, b (modelo -> mundo: x = A x0 + b), centro e raio.
    `extra[grupo] = (R, centro, t)` move o grupo inteiro depois das juntas (centro None = centroide do grupo já na pose)."""
    # 1) juntas
    itens = []
    soma, cont = {}, {}
    for p in partes:
        n, d, c = p.n, p.d, p.c
        A = np.eye(3)
        b = np.zeros(3)
        for nome in reversed(p.cadeia):
            pivo = juntas[nome]
            ang = pose.get(nome, (0, 0, 0))
            if not any(ang):
                continue
            R = euler(*ang)
            n, d, c = aplicar_junta(n, d, c, R, pivo)
            b = R @ (b - pivo) + pivo
            A = R @ A
        itens.append((p, n, d, c, A, b))
        cw = A @ p.c0 + b
        soma[p.grupo] = soma.get(p.grupo, 0) + cw
        cont[p.grupo] = cont.get(p.grupo, 0) + 1
    # 2) extras por grupo e raiz
    cena = []
    for p, n, d, c, A, b in itens:
        if extra and p.grupo in extra:
            R, cen, t = extra[p.grupo]
            if cen is None:
                cen = soma[p.grupo] / cont[p.grupo]
            n, d, c = aplicar_junta(n, d, c, R, cen, t)
            b = R @ (b - cen) + cen + np.array(t)
            A = R @ A
        n, d, c = aplicar_junta(n, d, c, raiz_R, (0, 0, 0), raiz_t)
        b = raiz_R @ b + np.array(raiz_t)
        A = raiz_R @ A
        cen_w = A @ p.c0 + b
        cena.append(dict(n=n, d=d, c=c, r=p.r, mat=p.mat, musgo=p.musgo, A=A, b=b, nome=p.nome, cen=cen_w, raio=p.raio))
    return cena


def centroides(partes, juntas, pose):
    """Centroide de cada grupo na pose (antes dos extras e da raiz)."""
    soma, cont = {}, {}
    for p in partes:
        A = np.eye(3)
        b = np.zeros(3)
        for nome in reversed(p.cadeia):
            pivo = juntas[nome]
            ang = pose.get(nome, (0, 0, 0))
            if not any(ang):
                continue
            R = euler(*ang)
            b = R @ (b - pivo) + pivo
            A = R @ A
        cw = A @ p.c0 + b
        soma[p.grupo] = soma.get(p.grupo, 0) + cw
        cont[p.grupo] = cont.get(p.grupo, 0) + 1
    return {g: soma[g] / cont[g] for g in soma}


# ---------------- ruído ----------------
def _hash3(ix, iy, iz):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def ruido3(p, esc):
    """Ruído de valor suave em [0, 1]; p é (R, 3)."""
    q = p * esc
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)
    acc = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                acc = acc + w * _hash3(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz)
    return acc


# ---------------- raios ----------------
def lancar(cena, quadro=QUADRO, ss=SS):
    """Z-buffer em resolução quadro*ss: profundidade t, índice da peça e normal do mundo."""
    n_px = quadro * ss
    melhor_t = np.full((n_px, n_px), np.inf)
    melhor_i = np.full((n_px, n_px), -1, np.int32)
    melhor_n = np.zeros((n_px, n_px, 3))
    for k, p in enumerate(cena):
        cx, cy = float(p['cen'] @ RX), float(p['cen'] @ U)
        rb = p['raio'] + 0.02
        x0 = int(math.floor((PIVO[0] + (cx - rb) * ESC) * ss))
        x1 = int(math.ceil((PIVO[0] + (cx + rb) * ESC) * ss))
        y0 = int(math.floor((PIVO[1] - (cy + rb) * ESC) * ss))
        y1 = int(math.ceil((PIVO[1] - (cy - rb) * ESC) * ss))
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, n_px), min(y1, n_px)
        if x1 <= x0 or y1 <= y0:
            continue
        ys, xs = np.mgrid[y0:y1, x0:x1]
        sx = ((xs + 0.5) / ss - PIVO[0]) / ESC
        sy = (PIVO[1] - (ys + 0.5) / ss) / ESC
        O = sx.reshape(-1, 1) * RX[None, :] + sy.reshape(-1, 1) * U[None, :] - 30.0 * D[None, :]
        cur_t = melhor_t[y0:y1, x0:x1].reshape(-1)
        if p['r'] is not None:
            oc = O - p['c'][None, :]
            b = oc @ D
            cc = (oc * oc).sum(1) - p['r'] ** 2
            disc = b * b - cc
            ok = disc >= 0
            t = -b - np.sqrt(np.where(ok, disc, 0))
            ok &= t < cur_t
            if not ok.any():
                continue
            pos = O[ok] + t[ok, None] * D[None, :]
            nn = (pos - p['c'][None, :]) / p['r']
        else:
            n, d = p['n'], p['d']
            den = n @ D
            num = d[None, :] - O @ n.T
            ent = den < -1e-9
            sai = den > 1e-9
            par = ~(ent | sai)
            with np.errstate(divide='ignore', invalid='ignore'):
                t_all = num / den[None, :]
            t_in = np.where(ent[None, :], t_all, -np.inf)
            t_out = np.where(sai[None, :], t_all, np.inf)
            ti = t_in.max(1)
            to = t_out.min(1)
            ok = ti < to
            if par.any():
                ok &= ~((num[:, par] < 0).any(1))
            ok &= ti < cur_t
            if not ok.any():
                continue
            t = ti
            idx = t_in[ok].argmax(1)
            nn = n[idx]
        sel_t = melhor_t[y0:y1, x0:x1]
        sel_i = melhor_i[y0:y1, x0:x1]
        sel_n = melhor_n[y0:y1, x0:x1]
        okm = ok.reshape(y1 - y0, x1 - x0)
        sel_t[okm] = t[ok]
        sel_i[okm] = k
        sel_n[okm] = nn
    return melhor_t, melhor_i, melhor_n


# ---------------- sombreado ----------------
def banda(v, limites):
    """v em [0,1] -> índice da banda (0 = mais clara)."""
    b = np.full(v.shape, len(limites), np.int32)
    for i in range(len(limites) - 1, -1, -1):
        b = np.where(v > limites[i], i, b)
    return b


def _o(grupo, bd):
    return np.array(IDX[grupo], np.int16)[bd]


def moda(ci, ss, vazio=0):
    """Reduz (H*ss, W*ss) -> (H, W) pela cor mais frequente entre as amostras cobertas; devolve (valor, cobertura)."""
    H = ci.shape[0] // ss
    W = ci.shape[1] // ss
    b = ci.reshape(H, ss, W, ss).transpose(0, 2, 1, 3).reshape(H, W, ss * ss)
    cobre = (b != vazio).sum(-1)
    best = np.full((H, W), vazio, ci.dtype)
    bestn = np.zeros((H, W), np.int16)
    for k in np.unique(ci):
        if k == vazio:
            continue
        n = (b == k).sum(-1)
        m = n > bestn
        best[m] = k
        bestn[m] = n[m]
    best[cobre * 2 < ss * ss] = vazio
    return best, cobre


def sombrear(cena, olho=0, quadro=QUADRO, ss=SS, cinza=None, linhas=True, rachaduras=True):
    """Imagem RGBA (quadro x quadro) da cena. `olho` apaga o olho: 0 vivo, 1 e 2 em brasa, 3 morto.
    `cinza` (0 a 1) mistura a pedra com tons de cinza (morte); None desliga."""
    t, idx, nw = lancar(cena, quadro, ss)
    n_px = quadro * ss
    ci = np.zeros((n_px, n_px), np.int16)
    hit = idx >= 0
    for k, p in enumerate(cena):
        m = idx == k
        if not m.any():
            continue
        nwm = nw[m]
        A, b = p['A'], p['b']
        ys, xs = np.nonzero(m)
        sx = ((xs + 0.5) / ss - PIVO[0]) / ESC
        sy = (PIVO[1] - (ys + 0.5) / ss) / ESC
        O = sx[:, None] * RX[None, :] + sy[:, None] * U[None, :] - 30.0 * D[None, :]
        pos = O + t[m][:, None] * D[None, :]
        loc = (pos - b[None, :]) @ A
        nloc = nwm @ A
        lam = np.clip(nwm @ LUZ, 0, 1)
        v = 0.12 + 0.78 * lam + 0.14 * np.clip(nwm[:, 1], 0, 1)
        if p['mat'] != OLHO:
            v = v + 0.16 * (ruido3(loc + 11.3, 2.4) - 0.5)       # as bordas das faixas ondulam um pouco (pedra irregular)
        if p['mat'] == OLHO:
            nv = np.clip(-(nwm @ D), 0, 1)
            niv = np.where(nv > 0.9, 0, np.where(nv > 0.72, 1, np.where(nv > 0.42, 2, 3)))
            niv = np.minimum(3, niv + olho)
            if olho >= 3:
                c = np.array([IDX['terra'][1], IDX['terra'][2], IDX['terra'][2], IDX['terra'][3]], np.int16)[niv]
            else:
                c = np.array(IDX['olho'], np.int16)[niv]
                if olho == 0:
                    c = np.where(nv > 0.955, IDX['pupila'][0], c)
            ci[m] = c
            continue
        if p['mat'] == PEDRA:
            bd = banda(v, (0.80, 0.56, 0.34, 0.18))
            c = _o('pedra', bd)
            if p['musgo'] > 0:
                topo = nloc[:, 1] > 0.50
                rr = ruido3(loc, 3.6)
                fino = ruido3(loc + 7.7, 9.0)
                mm = topo & (rr * 0.75 + fino * 0.25 < p['musgo'] * (0.30 + 0.55 * np.clip(nloc[:, 1], 0, 1)))
                bm = banda(v, (0.78, 0.50, 0.28))
                c[mm] = _o('musgo', bm)[mm]
            if rachaduras:
                rr = ruido3(loc + 5.5, 2.6)
                mr = (np.abs(rr - 0.5) < 0.022) & (ruido3(loc + 9.1, 1.7) > 0.45)
                c[mr] = np.minimum(c[mr] + 2, IDX['pedra'][-1])
            if cinza is not None and cinza > 0:
                bc = banda(v, (0.78, 0.50, 0.28))
                rr = ruido3(loc + 3.1, 5.0)
                mc = rr < cinza
                c[mc] = _o('cinza', bc)[mc]
            ci[m] = c
        elif p['mat'] == CINZA:
            bd = banda(v, (0.78, 0.50, 0.28))
            ci[m] = _o('cinza', bd)
        else:
            bd = banda(v, (0.78, 0.50, 0.28))
            ci[m] = _o('terra', bd)
    cor, cobre = moda(ci, ss)
    pid, _ = moda((idx + 1).astype(np.int16), ss)
    tt = np.where(hit, t, 0.0)
    cnt = np.maximum(hit.reshape(quadro, ss, quadro, ss).sum((1, 3)), 1)
    prof = tt.reshape(quadro, ss, quadro, ss).sum((1, 3)) / cnt
    mask = cor > 0
    if linhas:
        # linhas internas: pixel vizinho de uma peça mais próxima (a linha fica no pixel de trás)
        linha = np.zeros((quadro, quadro), bool)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            vz_t = np.roll(prof, (dy, dx), (0, 1))
            vz_i = np.roll(pid, (dy, dx), (0, 1))
            vz_m = np.roll(mask, (dy, dx), (0, 1))
            linha |= mask & vz_m & (vz_i != pid) & (vz_t < prof - 0.06)
        # não risca em cima do olho
        olho_px = np.isin(cor, IDX['olho'] + IDX['pupila'])
        linha &= ~olho_px
        cor = np.where(linha, IDX['linha'][0], cor)
    # contorno externo de 1 px
    viz = np.zeros_like(mask)
    viz[1:, :] |= mask[:-1, :]
    viz[:-1, :] |= mask[1:, :]
    viz[:, 1:] |= mask[:, :-1]
    viz[:, :-1] |= mask[:, 1:]
    borda = viz & ~mask
    cor = np.where(borda, IDX['contorno'][0], cor)
    rgba = np.zeros((quadro, quadro, 4), np.uint8)
    ocupado = cor > 0
    rgba[ocupado, :3] = PALETA_NP[cor[ocupado]]
    rgba[ocupado, 3] = 255
    return rgba
