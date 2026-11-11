"""Geometria das aranhas da Ponte do Sino, em metros (origem no centro dos pés, +y para cima, +z para a frente).

Duas variantes, com a mesma árvore de juntas (8 pernas de fêmur e tíbia, abdômen e presas):
  - `tecela`: a Tecelã de Cascalho, chefe da área. Direção do Jev (10/11/2026): corpo de BRONZE DE SINO com pátina verde-azulada,
    abdômen em forma de sino quebrado (boca virada para trás, um pedaço da borda faltando, badalo à mostra), pernas de ferro
    escuro com fios de teia luminosos e olhos âmbar. Não repete a pedra do Arauto.
  - `filhote`: o Filhote de Cascalho, inimigo comum em ninhadas. Corpo de cascalho cinza-azulado, pernas bem abertas e pontos
    âmbar nas costas (para não se confundir com o morcego da cripta).
"""
import math
import numpy as np
from render import caixa, esfera, segmento, tronco_cone, eixo, BRONZE, ESCURO, OLHO, FIO, CASCALHO, VAO

CIMA = np.array([0.0, 1.0, 0.0])
# pernas: (z do quadril, ângulo no chão a partir do lado, em graus: + para a frente)
PERNAS_TECELA = [(0.84, 58.0), (0.60, 22.0), (0.36, -18.0), (0.12, -52.0)]
PERNAS_FILHOTE = [(0.72, 62.0), (0.52, 24.0), (0.32, -20.0), (0.14, -58.0)]

CONFIG = {
    # quadro, pivô e px por metro de cada variante (render.configurar)
    'tecela': dict(quadro=256, pivo=(128, 164), esc=42.0),
    'filhote': dict(quadro=96, pivo=(48, 58), esc=8.9),
}


def construir(variante='tecela'):
    """Devolve (partes, juntas, pernas). `pernas[nome] = dict(h=direção no chão, lado=-1|1, i=índice, eixo=eixo de erguer)`."""
    tec = variante == 'tecela'
    P, J, pernas = [], {}, {}
    add = P.append
    mat_corpo = BRONZE if tec else CASCALHO
    # ---------------- cefalotórax ----------------
    y_c = 0.98 if tec else 0.86
    J['corpo'] = (0.0, y_c, 0.45)
    if tec:
        add(caixa('torax', (0, y_c, 0.50), (0.50, 0.30, 0.52), BRONZE, ch=0.34, jit=0.04, musgo=0.38, seed=1, grupo='corpo'))
        add(caixa('escudo', (0, y_c + 0.24, 0.42), (0.34, 0.14, 0.36), BRONZE, rot=(-8, 0, 0), ch=0.16, jit=0.04, musgo=0.42, seed=2, grupo='corpo'))
        add(caixa('cara', (0, y_c - 0.10, 1.04), (0.34, 0.22, 0.16), BRONZE, rot=(14, 0, 0), ch=0.16, jit=0.04, musgo=0.25, cadeia=('cabeca',), seed=3, grupo='corpo'))
        add(caixa('ventre', (0, y_c - 0.30, 0.42), (0.36, 0.14, 0.40), ESCURO, ch=0.14, jit=0.04, seed=4, grupo='corpo'))
    else:
        add(caixa('torax', (0, y_c, 0.46), (0.50, 0.34, 0.50), CASCALHO, ch=0.36, jit=0.07, seed=1, grupo='corpo'))
        add(caixa('cara', (0, y_c - 0.10, 0.98), (0.34, 0.24, 0.18), CASCALHO, rot=(14, 0, 0), ch=0.18, jit=0.06, cadeia=('cabeca',), seed=3, grupo='corpo'))
    J['cabeca'] = (0.0, y_c - 0.05, 0.92)
    # olhos âmbar: dois grandes e (na Tecelã) quatro pequenos
    z_o = 1.17 if tec else 1.12
    r_o = 0.115 if tec else 0.17
    for s in (-1, 1):
        add(esfera('olho%d' % (s + 1), (s * (0.17 if tec else 0.20), y_c + 0.02, z_o), r_o, OLHO, cadeia=('cabeca',), grupo='corpo'))
        if tec:
            add(esfera('olhinhoA%d' % (s + 1), (s * 0.33, y_c - 0.03, 1.08), 0.07, OLHO, cadeia=('cabeca',), grupo='corpo'))
            add(esfera('olhinhoB%d' % (s + 1), (s * 0.09, y_c + 0.17, 1.10), 0.065, OLHO, cadeia=('cabeca',), grupo='corpo'))
    # presas (quelíceras)
    J['presa'] = (0.0, y_c - 0.22, 1.10)
    for s in (-1, 1):
        if tec:
            add(segmento('presa%d' % (s + 1), (s * 0.15, y_c - 0.20, 1.14), (s * 0.10, y_c - 0.62, 1.26), 0.075, ESCURO,
                         cadeia=('cabeca', 'presa'), seed=5, grupo='corpo'))
        else:
            add(segmento('presa%d' % (s + 1), (s * 0.16, y_c - 0.22, 1.08), (s * 0.12, y_c - 0.56, 1.20), 0.10, ESCURO,
                         cadeia=('cabeca', 'presa'), seed=5, grupo='corpo'))
    # ---------------- abdômen ----------------
    J['abd'] = (0.0, y_c + 0.02, 0.02)
    a = ('abd',)
    if tec:
        # sino: a coroa presa ao tórax, o corpo abrindo para trás e para cima, a borda (boca) no fim
        d = np.array([0.0, 0.42, -1.0])
        d = d / np.linalg.norm(d)
        o = np.array([0.0, y_c + 0.06, 0.06])
        add(tronco_cone('sino_coroa', o, d, 0.20, 0.44, 0.22, BRONZE, lados=10, musgo=0.5, cadeia=a, grupo='abd'))
        add(tronco_cone('sino_ombro', o + d * 0.22, d, 0.44, 0.60, 0.30, BRONZE, lados=10, musgo=0.75, cadeia=a, grupo='abd'))
        add(tronco_cone('sino_cintura', o + d * 0.52, d, 0.60, 0.68, 0.46, BRONZE, lados=10, musgo=0.6, cadeia=a, grupo='abd'))
        add(tronco_cone('sino_friso', o + d * 0.74, d, 0.70, 0.71, 0.07, ESCURO, lados=10, cadeia=a, grupo='abd'))
        add(tronco_cone('sino_saia', o + d * 0.98, d, 0.68, 0.84, 0.20, BRONZE, lados=10, musgo=0.45, cadeia=a, grupo='abd'))
        # borda em gomos: faltam dois (o pedaço quebrado, em cima à direita)
        B = _base(d)
        n_g = 12
        for k in range(n_g):
            if k in (7, 8, 9):
                continue
            th = 2 * math.pi * (k + 0.5) / n_g
            rad = B[:, 0] * math.cos(th) + B[:, 2] * math.sin(th)
            tang = np.cross(d, rad)
            c = o + d * 1.24 + rad * 0.83
            add(caixa('gomo%d' % k, c, (0.075, 0.09, 0.235), BRONZE, R=np.stack([rad, d, tang], axis=1), ch=0.06, jit=0.05,
                      musgo=0.35, cadeia=a, seed=20 + k, grupo='abd'))
        # dentro do sino: escuro, com o badalo
        add(tronco_cone('sino_dentro', o + d * 1.15, d, 0.72, 0.74, 0.06, VAO, lados=10, cadeia=a, grupo='abd'))
        add(segmento('badalo_haste', o + d * 0.95, o + d * 1.34, 0.05, ESCURO, cadeia=a, seed=40, grupo='abd'))
        add(caixa('badalo', o + d * 1.40 - B[:, 2] * 0.05, (0.13, 0.13, 0.13), BRONZE, ch=0.10, jit=0.05, cadeia=a, seed=41, grupo='abd'))
        # alça da coroa
        add(caixa('alca', o + d * 0.02 + CIMA * 0.30, (0.10, 0.12, 0.10), ESCURO, ch=0.08, jit=0.04, cadeia=a, seed=42, grupo='abd'))
    else:
        add(caixa('abd', (0, y_c + 0.20, -0.48), (0.62, 0.46, 0.62), CASCALHO, rot=(-14, 0, 0), ch=0.46, jit=0.08, cadeia=a, seed=10, grupo='abd'))
        add(caixa('abd_ponta', (0, y_c + 0.26, -1.02), (0.36, 0.30, 0.30), CASCALHO, rot=(-24, 0, 0), ch=0.28, jit=0.08, cadeia=a, seed=11, grupo='abd'))
        # pontos âmbar nas costas (a assinatura do Filhote)
        for i, (x, y, z, r) in enumerate([(0.0, 0.66, -0.34, 0.20), (-0.30, 0.56, -0.66, 0.17), (0.30, 0.56, -0.66, 0.17), (0.0, 0.52, -1.00, 0.16)]):
            add(esfera('ponto%d' % i, (x, y_c + y, z), r, OLHO, cadeia=a, grupo='abd'))
    # ---------------- pernas ----------------
    tab = PERNAS_TECELA if tec else PERNAS_FILHOTE
    x_q = 0.44
    y_q = y_c - 0.04
    alt_joelho = 1.62 if tec else 1.30
    dist_joelho = 0.80 if tec else 0.95
    dist_pe = 1.72 if tec else 2.15
    e_f = 0.105 if tec else 0.20          # meia-espessura do fêmur
    e_t = 0.085 if tec else 0.17          # e da tíbia
    for lado, L in ((-1, 'L'), (1, 'R')):
        for i, (zq, ang) in enumerate(tab):
            nome = '%s%d' % (L, i)
            h = np.array([lado * math.cos(math.radians(ang)), 0.0, math.sin(math.radians(ang))])
            quad = np.array([lado * x_q, y_q, zq])
            k_alt = alt_joelho * (1.0 if i in (0, 3) else 0.90)
            joe = quad + h * dist_joelho * (1.0 if i in (0, 3) else 0.92) + CIMA * (k_alt - y_q)
            pe = quad + h * dist_pe * (1.0 if i in (0, 3) else 0.92)
            pe[1] = 0.0
            J['q' + nome] = tuple(quad)
            J['j' + nome] = tuple(joe)
            cq, cj = ('q' + nome,), ('q' + nome, 'j' + nome)
            g = 'perna' + nome
            add(caixa('anca' + nome, quad + h * 0.08, (0.15, 0.13, 0.15) if tec else (0.22, 0.20, 0.22), mat_corpo if tec else ESCURO,
                      ch=0.12, jit=0.05, cadeia=cq, seed=60 + i, grupo=g))
            add(segmento('femur' + nome, quad + h * 0.10, joe, e_f, ESCURO, cadeia=cq, seed=61 + i, grupo=g))
            add(caixa('joelho' + nome, joe, (0.14, 0.14, 0.14) if tec else (0.22, 0.22, 0.22), mat_corpo, ch=0.10, jit=0.06,
                      musgo=0.5, cadeia=cj, seed=62 + i, grupo=g))
            add(segmento('tibia' + nome, joe, pe + CIMA * 0.10, e_t, ESCURO, cadeia=cj, seed=63 + i, grupo=g))
            add(caixa('garra' + nome, pe + CIMA * 0.07, (0.10, 0.07, 0.10) if tec else (0.17, 0.10, 0.17), mat_corpo, ch=0.06, jit=0.05,
                      cadeia=cj, seed=64 + i, grupo=g))
            if tec:
                # fios de teia luminosos: anéis claros no fêmur e na tíbia
                for k, (pa, pb, f, e) in enumerate([(quad + h * 0.10, joe, 0.55, e_f), (joe, pe, 0.34, e_t), (joe, pe, 0.66, e_t)]):
                    c = pa + (pb - pa) * f
                    dseg = (pb - pa) / np.linalg.norm(pb - pa)
                    Bs = _base(dseg)
                    add(caixa('fio%s%d' % (nome, k), c, (e + 0.035, 0.045, e + 0.035), FIO, R=Bs, ch=0.04, jit=0.0,
                              cadeia=cq if k == 0 else cj, seed=70 + k, grupo=g))
            pernas[nome] = dict(h=h, lado=lado, i=i, eixo=np.cross(h, CIMA), alcance=float(np.linalg.norm((pe - quad)[[0, 2]])))
    return P, J, pernas


def _base(d):
    from render import _base_y
    return _base_y(d)
