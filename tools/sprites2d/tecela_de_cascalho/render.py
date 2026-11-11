"""Renderizador por código das aranhas da Ponte do Sino (Tecelã de Cascalho e Filhote de Cascalho), adaptado do renderizador do
Arauto de Pedra (tools/sprites2d/arauto_de_pedra/render.py): peças convexas (planos) e esferas, câmera ortográfica de cima (3/4),
sombreado em degraus com paleta curta, contorno de 1 px. Tudo em numpy, sem serviço pago e sem GPU.

Coordenadas do mundo: x para a direita da tela, y para cima, z para a câmera (a frente do modelo é +z). Origem no centro dos pés.
O desenho é feito com SS amostras por pixel; cada pixel final recebe a cor mais frequente entre as amostras (nada de meio-tom:
só cores da paleta), e o contorno de 1 px sai depois, já na grade final.
"""
import math
import numpy as np

QUADRO = 256
PIVO = (128, 176)
ESC = 42.0                      # px por metro (ver configurar)
SS = 3                          # amostras por pixel (por eixo)
PITCH = math.radians(35.0)      # a câmera olha para baixo 35 graus
D = np.array([0.0, -math.sin(PITCH), -math.cos(PITCH)])     # direção dos raios
U = np.array([0.0, math.cos(PITCH), -math.sin(PITCH)])      # "para cima" da tela
RX = np.array([1.0, 0.0, 0.0])
LUZ = np.array([-0.52, 0.78, 0.46])
LUZ = LUZ / np.linalg.norm(LUZ)

# materiais
BRONZE, ESCURO, OLHO, FIO, CASCALHO, VAO = 0, 1, 2, 3, 4, 5   # VAO: o oco do sino, sempre na sombra

PAL = {
    # bronze de sino (quente, o corpo da Tecelã) com pátina verde-azulada nas faces de cima; ferro escuro azulado nas pernas e juntas;
    # fio de teia claro e frio (o brilho das pernas); cascalho cinza-azulado (o Filhote); olhos âmbar: o ponto mais claro e quente
    'bronze': [(214, 164, 92), (176, 124, 66), (136, 90, 52), (98, 62, 44), (64, 42, 40)],
    'patina': [(120, 190, 170), (78, 150, 140), (52, 110, 112), (38, 76, 86)],
    'escuro': [(92, 96, 116), (66, 68, 88), (46, 46, 64), (32, 30, 44)],
    'olho': [(255, 226, 112), (255, 156, 40), (220, 92, 26), (120, 44, 20)],
    'fio': [(226, 246, 250), (160, 214, 232), (104, 160, 196)],
    'cascalho': [(160, 170, 186), (126, 136, 156), (96, 104, 126), (70, 74, 96), (48, 48, 68)],
    'pupila': (50, 16, 8),
    'linha': (30, 26, 36),
    'contorno': (0, 0, 0),
}

# paleta global (índice 0 = vazio)
PALETA = [(0, 0, 0)]
IDX = {}


def _reg(chave, cores):
    IDX[chave] = []
    for c in cores:
        PALETA.append(tuple(c))
        IDX[chave].append(len(PALETA) - 1)


for _k in ('bronze', 'patina', 'escuro', 'olho', 'fio', 'cascalho'):
    _reg(_k, PAL[_k])
_reg('pupila', [PAL['pupila']])
_reg('linha', [PAL['linha']])
_reg('contorno', [PAL['contorno']])
PALETA_NP = np.array(PALETA, np.uint8)


def configurar(quadro, pivo, esc):
    """Troca o quadro, o pivô e a escala (px por metro): a Tecelã e o Filhote usam câmeras diferentes."""
    global QUADRO, PIVO, ESC
    QUADRO, PIVO, ESC = int(quadro), tuple(pivo), float(esc)


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


def eixo(v, a):
    """Rotação de `a` graus em torno do eixo `v` (Rodrigues)."""
    v = np.array(v, float)
    v = v / np.linalg.norm(v)
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + s * K + (1 - c) * (K @ K)


def _mat(ang):
    """Ângulo de pose: tupla de Euler (graus) ou matriz 3x3 pronta."""
    return ang if isinstance(ang, np.ndarray) else euler(*ang)


def _nulo(ang):
    return (not isinstance(ang, np.ndarray)) and not any(ang)


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


def caixa(nome, c, h, mat=BRONZE, rot=(0, 0, 0), ch=0.12, jit=0.03, musgo=0.0, cadeia=(), seed=0, grupo=None, R=None):
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
    R = euler(*rot) if R is None else R
    n = n @ R.T
    c = np.array(c, float)
    d = d + n @ c
    p = Parte(nome, mat, n=n, d=d, musgo=musgo, cadeia=cadeia, grupo=grupo)
    p.c0 = c
    p.raio = float(np.linalg.norm(h)) * (1.0 + jit)
    return p


def esfera(nome, c, r, mat=OLHO, musgo=0.0, cadeia=(), grupo=None):
    p = Parte(nome, mat, c=np.array(c, float), r=float(r), musgo=musgo, cadeia=cadeia, grupo=grupo)
    p.c0 = np.array(c, float)
    p.raio = float(r)
    return p


def _base_y(d):
    """Matriz cujo eixo y local aponta para `d` (os outros dois eixos ficam estáveis)."""
    d = np.array(d, float)
    d = d / np.linalg.norm(d)
    a = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    x = np.cross(d, a)
    x = x / np.linalg.norm(x)
    z = np.cross(x, d)
    return np.stack([x, d, z], axis=1)


def segmento(nome, p0, p1, esp, mat=ESCURO, esp2=None, **kw):
    """Barra chanfrada de p0 a p1 (perna, presa): caixa fina alinhada ao segmento. `esp` é a meia-espessura."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    comp = float(np.linalg.norm(p1 - p0))
    return caixa(nome, (p0 + p1) / 2, (esp, comp / 2 + esp * 0.5, esp2 or esp), mat, R=_base_y(p1 - p0), ch=kw.pop('ch', esp * 0.9), **kw)


def tronco_cone(nome, base, direcao, r0, r1, comp, mat=BRONZE, lados=10, musgo=0.0, cadeia=(), grupo=None, giro=0.0):
    """Tronco de cone facetado (convexo): da `base` (raio r0) ao longo de `direcao` por `comp` (raio r1). Peças de sino."""
    B = _base_y(direcao)
    ns, ds = [np.array([0.0, -1.0, 0.0]), np.array([0.0, 1.0, 0.0])], [0.0, comp]
    for k in range(lados):
        th = 2 * math.pi * (k + 0.5) / lados + giro
        n = np.array([math.cos(th) * comp, -(r1 - r0), math.sin(th) * comp])
        n = n / np.linalg.norm(n)
        ns.append(n)
        ds.append(float(n @ np.array([r0 * math.cos(th), 0.0, r0 * math.sin(th)])))
    n = np.array(ns) @ B.T
    base = np.array(base, float)
    d = np.array(ds) + n @ base
    p = Parte(nome, mat, n=n, d=d, musgo=musgo, cadeia=cadeia, grupo=grupo)
    p.c0 = base + B[:, 1] * comp * 0.5
    p.raio = float(math.hypot(comp * 0.5, max(r0, r1))) * 1.05
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
            if _nulo(ang):
                continue
            R = _mat(ang)
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
            if _nulo(ang):
                continue
            R = _mat(ang)
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
def lancar(cena, quadro=None, ss=SS):
    """Z-buffer em resolução quadro*ss: profundidade t, índice da peça e normal do mundo."""
    quadro = quadro or QUADRO
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


def sombrear(cena, olho=0, quadro=None, ss=SS, cinza=None, linhas=True, rachaduras=True):
    """Imagem RGBA (quadro x quadro) da cena. `olho` apaga os olhos e os pontos âmbar: 0 vivo, 1 e 2 em brasa, 3 morto.
    `cinza` (0 a 1) apaga o fio de teia (morte): o brilho vira ferro escuro; None desliga."""
    quadro = quadro or QUADRO
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
        mat = p['mat']
        if mat == OLHO:
            nv = np.clip(-(nwm @ D), 0, 1)
            niv = np.where(nv > 0.9, 0, np.where(nv > 0.72, 1, np.where(nv > 0.42, 2, 3)))
            niv = np.minimum(3, niv + olho)
            if olho >= 3:
                c = np.array([IDX['escuro'][1], IDX['escuro'][2], IDX['escuro'][2], IDX['escuro'][3]], np.int16)[niv]
            else:
                c = np.array(IDX['olho'], np.int16)[niv]
                if olho == 0 and p['r'] is not None and p['r'] * ESC > 3.2:
                    c = np.where(nv > 0.955, IDX['pupila'][0], c)
            ci[m] = c
            continue
        if mat == VAO:
            ci[m] = np.where(ruido3(loc + 2.2, 3.0) > 0.62, IDX['escuro'][2], IDX['escuro'][3])
            continue
        if mat == FIO:
            if cinza is not None and cinza >= 1.0:
                ci[m] = _o('escuro', banda(v, (0.78, 0.50, 0.28)))
            else:
                bd = banda(v, (0.62, 0.30))
                if cinza:
                    bd = np.minimum(bd + 1, 2)
                ci[m] = _o('fio', bd)
            continue
        v = v + 0.16 * (ruido3(loc + 11.3, 2.4) - 0.5)       # as bordas das faixas ondulam um pouco (metal batido, pedra irregular)
        if mat in (BRONZE, CASCALHO):
            chave = 'bronze' if mat == BRONZE else 'cascalho'
            bd = banda(v, (0.80, 0.56, 0.34, 0.18))
            c = _o(chave, bd)
            if mat == BRONZE and p['musgo'] > 0:
                # pátina: nas faces viradas para cima e em manchas que escorrem pelas laterais
                rr = ruido3(loc, 3.2)
                fino = ruido3(loc + 7.7, 8.0)
                mm = (rr * 0.75 + fino * 0.25) < p['musgo'] * (0.22 + 0.60 * np.clip(nloc[:, 1] * 0.5 + 0.5, 0, 1))
                bm = banda(v, (0.78, 0.50, 0.28))
                c[mm] = _o('patina', bm)[mm]
            if rachaduras:
                rr = ruido3(loc + 5.5, 2.6)
                mr = (np.abs(rr - 0.5) < 0.022) & (ruido3(loc + 9.1, 1.7) > 0.45)
                c[mr] = np.minimum(c[mr] + 2, IDX[chave][-1])
            ci[m] = c
        else:
            ci[m] = _o('escuro', banda(v, (0.78, 0.50, 0.28)))
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
        olho_px = np.isin(cor, IDX['olho'] + IDX['pupila'] + IDX['fio'])
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
