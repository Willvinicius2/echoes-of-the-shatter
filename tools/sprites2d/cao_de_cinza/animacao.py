"""Poses e animações do Cão de Cinza a partir das partes recortadas (partes.py). Só desloca pixels da base aprovada."""
import math
import zlib
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import rig
import partes
from rig import PAD, Q, colar, vazio, opaco, deslocar

CACHE = {}
FRENTE = {'E': (1.0, 0.0), 'NE': (0.8, -0.45), 'SE': (0.8, 0.45), 'S': (0.0, 0.9), 'N': (0.0, -0.9)}
DIRS = ['S', 'SE', 'E', 'NE', 'N']

# mandíbula: caixa (x0, y0, x1, y1) na grade de 64 px; a parte de baixo desce e a boca aparece no vão
MANDIBULA = {'E': (52, 29, 61, 33), 'NE': (53, 26, 62, 30), 'SE': (43, 28, 55, 32), 'S': (10, 28, 22, 32)}
# cabeça caída: (x onde o focinho começa a descer, x da ponta do focinho) na grade de 64 px; N (de costas) não tem
CABECA = {'E': (38, 62), 'NE': (38, 62), 'SE': (30, 56), 'S': (28, 8)}
BOCA = (122, 28, 30, 255)
DENTE = (226, 218, 200, 255)
BOCA_ESC = (0, 0, 0, 255)

# cor do olho e das brasas na base aprovada (laranja vivo, amarelo, laranja avermelhado)
BRASA_CORES = [(255, 154, 48), (255, 217, 120), (224, 86, 26)]


def camadas(nome):
    if nome not in CACHE:
        CACHE[nome] = partes.partes(nome)
    return CACHE[nome]


def limpar(a, min_px=5):
    """Tira fiapos soltos de poucos pixels (restos do recorte)."""
    m = a[..., 3] > 0
    lab, k = ndi.label(m, structure=np.ones((3, 3)))
    if k == 0:
        return a
    tam = ndi.sum(m, lab, range(1, k + 1))
    out = a.copy()
    for i, t in enumerate(tam, 1):
        if t < min_px:
            out[lab == i] = 0
    return out


def eh_brasa(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (a[..., 3] > 0) & (r > 190) & (g > 60) & (b < 130) & (r - b > 120)


# degraus do brilho (todos da paleta da base, mais o vermelho-brasa do degrau 2)
DEGRAU = {1: (224, 86, 26), 2: (150, 52, 30), 3: (84, 57, 44)}


def apagar_brasas(a, nivel):
    """nivel 0 mantém; 1 a 3 trocam toda brasa (olho e fagulhas presas) pelo degrau de brilho, sempre com cores da paleta."""
    if not nivel:
        return a
    out = a.copy()
    out[eh_brasa(a), :3] = DEGRAU[min(3, nivel)]
    return out


def flash(a, k):
    out = a.copy()
    m = a[..., 3] > 0
    for c in range(3):
        out[..., c][m] = (a[..., c][m] * (1 - k) + 255 * k).clip(0, 255).astype(np.uint8)
    return out


def montar(nome, corpo=(0, 0), pitch=0.0, pernas=None, caudas=None, seguir=1.0, pitch_ref=32, boca=0, brasa=0, queda=0.0):
    """Uma pose. `pernas` mapeia o nome da perna a (dx_pe, dy_pe): dy<0 encurta (pé sobe), dy>0 desce a perna.
    `caudas` mapeia o nome a (amplitude, fase). `boca` abre a mandíbula em px. `brasa` é o degrau de brilho das brasas
    (0 = pleno, 1 a 3 = apagando). `queda` abaixa o focinho em px (cabeça caída). Corpo que desce (dy > 0) encolhe as
    pernas: os pés ficam no chão."""
    cfg = partes.CFG[nome]
    base, cam = camadas(nome)
    pernas = pernas or {}
    caudas = caudas or {}
    out = vazio()
    bx, by = corpo
    for p in cfg['pernas']:
        c = cam[p['nome']]
        fx, fy = pernas.get(p['nome'], (0, 0))
        fx, fy = int(round(fx)), int(round(fy))
        desce = max(0, int(round(by * seguir)))
        ys = np.where(c[..., 3].any(axis=1))[0]
        comp = int(ys.max()) - (p['quadril'] + PAD) if len(ys) else 0
        ajuste = max(0, min(desce, comp - 7))      # o quanto a perna encolhe; o que sobra o corpo cobre
        baixa = max(0, fy)                       # pé que desce: até 3 px por deslocamento (o corpo cobre a emenda), o resto estica
        c = rig.deformar_perna(c, p['quadril'] + PAD, fx, min(0, fy) - ajuste + max(0, baixa - 3))
        if baixa:
            c = deslocar(c, 0, min(baixa, 3))
        c = deslocar(c, bx * seguir, (ajuste if desce else by * seguir))
        colar(out, c)
    for t in cfg['caudas']:
        c = cam[t['nome']]
        amp, fase = caudas.get(t['nome'], (0, 0))
        if amp:
            rx, ry = t['raiz']
            if t['nome'] == 'cA':
                c = rig.ondular(c, ry + PAD, ry + PAD - 20, amp, fase)
            else:
                sentido = 10 if nome == 'S' else -14
                c = rig.ondular_v(c, rx + PAD, rx + PAD + sentido, amp, fase)
        c = deslocar(c, bx, by)
        if pitch:
            c = rig.cisalhar_colunas(c, lambda x: round(pitch * (x - PAD - pitch_ref)))
        colar(out, c)
    c = cam['corpo']
    if boca > 0 and nome in MANDIBULA:
        c = abrir_boca(c, nome, boca)
    if queda and nome in CABECA:
        xi, xf = CABECA[nome]
        c = rig.cisalhar_colunas(c, lambda x: round(queda * min(1.0, max(0.0, (x - PAD - xi) / (xf - xi))) ** 1.4))
    c = deslocar(c, bx, by)
    if pitch:
        c = rig.cisalhar_colunas(c, lambda x: round(pitch * (x - PAD - pitch_ref)))
    colar(out, c)
    if brasa:
        out = apagar_brasas(out, brasa)
    return out


def abrir_boca(c, nome, d):
    """Desce a parte de baixo do focinho d px e enche o vão: contorno preto, interior vermelho e presas."""
    x0, y0, x1, y1 = MANDIBULA[nome]
    x0, x1, y0, y1 = x0 + PAD, x1 + PAD, y0 + PAD, y1 + PAD
    out = c.copy()
    jaw = vazio()
    reg = c[y0:y1 + 1, x0:x1 + 1]
    jaw[y0:y1 + 1, x0:x1 + 1] = reg
    out[y0:y1 + 1, x0:x1 + 1] = 0
    cols = np.where(reg[..., 3].any(axis=0))[0]
    if len(cols):
        cmin, cmax = cols.min() + x0, cols.max() + x0
        for yy in range(y0, y0 + d):
            for xx in range(cmin + 1, cmax):
                if yy == y0 or yy == y0 + d - 1:
                    out[yy, xx] = BOCA_ESC
                else:
                    out[yy, xx] = BOCA
        # presas de cima (a da frente desce 2 px) e dentes de baixo
        for k, xx in enumerate(range(cmin + 2, cmax - 1, 2)):
            out[y0, xx] = DENTE
            if k == 0 and d >= 4:
                out[y0 + 1, xx] = DENTE
        if d >= 3:
            for xx in range(cmin + 3, cmax - 1, 3):
                out[y0 + d - 1, xx] = DENTE
    j = deslocar(jaw, 0, d)
    m = j[..., 3] > 0
    out[m] = j[m]
    return out


def tira(quadros, saida, Z=3, rotulos=True, fundo=(52, 52, 58, 255), recorte=(6, 4, 86, 84), colunas=8):
    x0, y0, x1, y1 = recorte
    w, h = (x1 - x0) * Z, (y1 - y0) * Z
    n = len(quadros)
    cols = min(n, colunas)
    lin = (n + cols - 1) // cols
    s = Image.new('RGBA', (w * cols, h * lin), fundo)
    d = ImageDraw.Draw(s)
    for i, q in enumerate(quadros):
        im = Image.fromarray(q[y0:y1, x0:x1], 'RGBA').resize((w, h), Image.NEAREST)
        cx, cy = (i % cols) * w, (i // cols) * h
        s.alpha_composite(im, (cx, cy))
        if rotulos:
            d.text((cx + 3, cy + 2), str(i), fill=(255, 255, 0, 255))
        d.line([(cx, cy + (74 - y0) * Z), (cx + w, cy + (74 - y0) * Z)], fill=(255, 255, 255, 40))
    s.save(saida)
    return s


# ---------------- parâmetros por direção ----------------
# por perna: (grupo +1/-1, (alcance x, alcance y) do pé à frente, levantar em px). Grupos opostos fazem a tesoura do trote:
# quando uma pata está toda à frente, a outra está toda atrás (quadros 2 e 6 do ciclo de 8 são a passada aberta).
CORRIDA = {
    'E': {'T': (-1, (8, 0), 5), 'F': (1, (8, 0), 5)},
    'NE': {'T': (-1, (7, -2), 5), 'F': (1, (7, -2), 5)},
    'SE': {'A': (1, (6, 2), 4), 'B': (-1, (6, 2), 5), 'C': (1, (6, 2), 5)},
    'S': {'A': (1, (0, 3), 4), 'B': (-1, (0, 3), 4), 'C': (1, (0, 3), 3)},
    'N': {'A': (1, (0, -3), 3), 'B': (-1, (0, -3), 3), 'C': (-1, (0, -3), 3)},
}


def passo(nome, u):
    """Pés da corrida no instante u (radianos): {perna: (dx, dy)}. A pata vai à frente com seno e sobe enquanto avança."""
    pernas = {}
    for nm, (g, (ax, ay), lev) in CORRIDA[nome].items():
        sn, cs = g * math.sin(u), g * math.cos(u)
        lift = lev * max(0.0, cs)
        dx, dy = round(ax * sn), round(ay * sn)
        pernas[nm] = (dx, dy - round(lift) if dy <= 0 or lift > 0.5 else dy)
    return pernas


def correr(nome, n=8):
    q = []
    for t in range(n):
        u = 2 * math.pi * t / n
        bob = -round(2.0 * abs(math.cos(u)))              # sobe com as patas sob o corpo, desce na passada aberta
        caudas = {'cA': (3, u), 'cB': (2, u + 1.0)}
        pitch = 0.04 * math.sin(2 * u) if nome in ('E', 'NE', 'SE') else 0.0
        q.append(limpar(montar(nome, corpo=(0, bob), pernas=passo(nome, u), caudas=caudas, pitch=pitch)))
    return q



# ---------------- fagulhas ----------------
FAGULHA_CORES = [(255, 217, 120, 255), (255, 154, 48, 255), (224, 86, 26, 255), (106, 74, 57, 255)]


def pontos_de_brasa(nome):
    """Pixels de brasa soltos da base (fora do olho 2x2), usados como origem das fagulhas."""
    a, _ = camadas(nome)
    m = eh_brasa(a)
    lab, k = ndi.label(m, structure=np.ones((3, 3)))
    pts = []
    for i in range(1, k + 1):
        ys, xs = np.where(lab == i)
        if len(ys) == 1:
            pts.append((int(xs[0]), int(ys[0])))
    pts.sort(key=lambda p: (p[1], p[0]))
    return pts


def fagulhas(a, nome, t, n, qtd=3, vida=4, subida=1, desvio=(0, 0)):
    """Fagulhas que sobem das brasas da base; cada uma vive `vida` quadros e se repete a cada n quadros."""
    pts = pontos_de_brasa(nome)
    if not pts:
        return a
    passo = max(1, len(pts) // qtd)
    escolhidas = pts[::passo][:qtd]
    out = a.copy()
    for i, (x, y) in enumerate(escolhidas):
        idade = (t - (i * n) // max(1, len(escolhidas))) % n
        if idade >= vida:
            continue
        px = x + desvio[0] + (1 if (i + idade) % 3 == 0 else 0) - (1 if (i + idade) % 5 == 0 else 0)
        py = y + desvio[1] - subida * idade - 1
        if 0 <= px < Q and 0 <= py < Q and out[py, px, 3] == 0:
            out[py, px] = FAGULHA_CORES[min(idade, len(FAGULHA_CORES) - 1)]
    return out


# ---------------- parado ----------------
def parado(nome, n=6):
    q = []
    for t in range(n):
        u = 2 * math.pi * t / n
        resp = -1 if math.sin(u) > 0.5 else 0
        caudas = {'cA': (2, u), 'cB': (1, u + 1.0)}
        pitch = 0.04 * math.sin(u + 1.0) if nome in ('E', 'NE', 'SE') else 0.0
        brasa = 1 if math.sin(u + 0.6) < -0.75 else 0
        f = montar(nome, corpo=(0, resp), seguir=0.0, caudas=caudas, pitch=pitch, brasa=brasa)
        q.append(fagulhas(limpar(f), nome, t, n))
    return q


# ---------------- morder ----------------
# (avanço px, altura extra, agachar, balanço das pernas, boca, inclinação)
MORDIDA = [
    (-3, 0, 1, -0.4, 0, -0.5),
    (-5, 0, 2, -0.7, 0, -0.9),
    (1, -1, 0, 0.5, 2, 0.2),
    (10, -2, 0, 1.0, 5, 0.9),
    (12, -1, 0, 0.9, 5, 1.0),
    (8, 0, 0, 0.5, 3, 0.6),
    (4, 0, 0, 0.1, 1, 0.2),
    (1, 0, 0, -0.1, 0, 0.0),
]


def morder(nome):
    fx, fy = FRENTE[nome]
    q = []
    for t, (av, alt, agach, bal, boca, incl) in enumerate(MORDIDA):
        pernas = {}
        for nm, (g, (ax, ay), lev) in CORRIDA[nome].items():
            dx, dy = round(ax * g * bal), round(ay * g * bal)
            pernas[nm] = (dx, dy)
        corpo = (round(fx * av), round(fy * av) + alt + agach)
        pitch = 0.05 * incl if nome in ('E', 'NE', 'SE') else 0.0
        u = 2 * math.pi * t / len(MORDIDA)
        caudas = {'cA': (3 if t < 3 else 2, u * 1.5), 'cB': (2, u * 1.5 + 1.0)}
        f = montar(nome, corpo=corpo, pernas=pernas, caudas=caudas, pitch=pitch, boca=boca, seguir=1.0)
        q.append(limpar(f))
    return q


# ---------------- ferido ----------------
# (recuo px, agachar px, abrir pernas, cabeça caída px)
FERIDA = [(3, 2, 0.5, 2.0), (2, 1, 0.3, 1.0), (1, 0, 0.0, 0.0)]
ESPALHAR = {'E': {'T': -1, 'F': 1}, 'NE': {'T': -1, 'F': 1}, 'SE': {'A': -1, 'B': 0, 'C': 1},
            'S': {'A': -1, 'B': 0, 'C': 1}, 'N': {'A': -1, 'B': 0, 'C': 1}}


def espalhar(nome, abre):
    """Pés abertos `abre` px para os lados (frente e trás nas vistas laterais)."""
    return {nm: (round(sg * abre), 0) for nm, sg in ESPALHAR[nome].items()}


def ferido(nome):
    fx, fy = FRENTE[nome]
    q = []
    for t, (rec, ag, abre, cab) in enumerate(FERIDA):
        corpo = (round(-fx * rec), round(-fy * rec) + ag)
        f = montar(nome, corpo=corpo, pernas=espalhar(nome, abre * 4), caudas={'cA': (2, t), 'cB': (1, t)}, queda=cab)
        q.append(limpar(f))
    return q


# ---------------- morrer ----------------
# (afundar px, abrir pernas px, cabeça caída px, degrau das brasas, progresso das cinzas)
MORTE = [
    (0, 0, 0.0, 0, 0.00),
    (3, 2, 2.0, 0, 0.00),
    (7, 4, 4.0, 1, 0.00),
    (10, 6, 6.0, 2, 0.10),
    (12, 7, 7.0, 2, 0.28),
    (12, 7, 7.0, 3, 0.46),
    (12, 7, 7.0, 3, 0.62),
    (12, 7, 7.0, 3, 0.80),
]
CINZAS = [(136, 128, 122, 255), (114, 107, 102, 255), (89, 84, 80, 255), (67, 63, 61, 255)]


def cinzas(a, p, nome, t):
    """Dissolve o quadro em cinzas de cima para baixo: p é o progresso (0 a 1). O que já virou cinza some; a faixa que
    está virando solta flocos que sobem 1 a 3 px (alguns ainda brasa); o monte de baixo fica."""
    if p <= 0:
        return a
    rng = np.random.RandomState(zlib.crc32(nome.encode()) % 9973 + 17)
    ys, xs = np.where(a[..., 3] > 0)
    if len(ys) == 0:
        return a
    y0, y1 = ys.min(), ys.max()
    r = rng.random_sample(a.shape[:2])
    linha = np.clip((np.arange(Q)[:, None] - y0) / max(1, y1 - y0), 0, 1) * np.ones((1, Q))
    thr = 0.74 * linha + 0.26 * r      # de cima (cedo) para baixo (tarde); o ruído deixa a frente irregular
    m = a[..., 3] > 0
    larg = 0.09
    some = m & (thr < p - larg)
    voa = m & (thr >= p - larg) & (thr < p)
    out = a.copy()
    out[some | voa] = 0
    for y, x in zip(*np.where(voa)):
        k = (thr[y, x] - (p - larg)) / larg
        dy = -int(1 + 2 * (1 - k))
        dx = int(rng.randint(-1, 2))
        ny, nx = y + dy, x + dx
        if 0 <= ny < Q and 0 <= nx < Q and out[ny, nx, 3] == 0:
            sorte = rng.random_sample()
            if sorte < 0.14:
                out[ny, nx] = FAGULHA_CORES[1 if k < 0.5 else 2]
            else:
                out[ny, nx] = CINZAS[int(rng.randint(0, len(CINZAS)))]
    return out


def monte(a, solo, cx, larg, alt, nome, t):
    """Monte de cinzas no chão (contorno preto de 1 px, 4 tons de cinza e algumas brasas) que cresce enquanto o cão some."""
    if alt <= 0:
        return a
    rng = np.random.RandomState(zlib.crc32(nome.encode()) % 7919 + 31)
    out = a.copy()
    meia = larg / 2.0
    topo = {}
    for x in range(int(cx - meia), int(cx + meia) + 1):
        u = (x - cx) / meia
        if abs(u) >= 1:
            continue
        h = int(round(alt * (1 - u * u) ** 0.7 + rng.random_sample() * 0.8))
        topo[x] = h
    for x, h in topo.items():
        for k in range(h + 1):
            y = solo - k
            if not (0 <= y < Q and 0 <= x < Q):
                continue
            if k == h and h > 0:
                out[y, x] = (0, 0, 0, 255)
            elif k == h - 1:
                out[y, x] = CINZAS[0] if rng.random_sample() < 0.6 else CINZAS[1]
            else:
                out[y, x] = CINZAS[int(1 + rng.randint(0, 3))]
    for _ in range(3):
        x = int(rng.choice(list(topo)))
        y = solo - max(0, topo[x] - 1 - int(rng.randint(0, 2)))
        if t >= 5 and 0 <= y < Q and out[y, x, 3] > 0:
            out[y, x] = FAGULHA_CORES[int(rng.randint(1, 3))]
    return out


MONTE = [0, 0, 0, 0, 2, 3, 4, 5]


def morrer(nome):
    q = []
    for t, (afunda, abre, cab, brasa, prog) in enumerate(MORTE):
        fx, fy = FRENTE[nome]
        rec = 3 if t == 0 else (2 if t == 1 else 1)
        corpo = (round(-fx * rec), round(-fy * rec) + afunda)
        caudas = {'cA': (2 if t < 3 else 1, t), 'cB': (1 if t < 3 else 0, t)}
        f = limpar(montar(nome, corpo=corpo, pernas=espalhar(nome, abre), caudas=caudas, queda=cab, brasa=brasa), 3 if t < 4 else 1)
        ys, xs = np.where(f[..., 3] > 0)
        solo, cx, larg = int(ys.max()), int((xs.min() + xs.max()) // 2), int((xs.max() - xs.min()) * 0.62)
        q.append(monte(cinzas(f, prog, nome, t), solo, cx, larg, MONTE[t], nome, t))
    return q


if __name__ == '__main__':
    import sys
    # uso: python3 animacao.py <direção> <saida.png>   (tira de conferência da corrida)
    d = sys.argv[1] if len(sys.argv) > 1 else 'E'
    tira(correr(d), sys.argv[2] if len(sys.argv) > 2 else f'run_{d}.png', Z=5, colunas=4, recorte=(6, 10, 80, 82))
