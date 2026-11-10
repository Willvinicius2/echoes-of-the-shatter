"""Geometria do Carcereiro do Ossuário (esqueleto alto de carcereiro: caveira com coroa de ferro, caixa torácica aberta, ombreiras
de ferro com espinhos, correntes cruzadas no peito, argolas de chaves no cinto, algemas nos punhos e uma marreta de ferro na mão direita), em metros.

Origem no centro dos pés, +y para cima, +z para a frente. Mesmas juntas e grupos do Arauto (a animação é compartilhada), mas
com peças finas: o que o distingue do golem é a silhueta de ossos com vãos, não só a paleta.
Materiais: PEDRA = osso, TERRA = sombra do interior e panos, CINZA = ferro, OLHO = brasa nas órbitas.
"""
import numpy as np
from render import caixa, esfera, PEDRA, TERRA, OLHO, CINZA

JUNTAS = {
    'tronco': (0.0, 1.40, 0.0),
    'cabeca': (0.0, 2.20, 0.0),
    'ombroL': (-0.62, 2.12, 0.0), 'ombroR': (0.62, 2.12, 0.0),
    'ombroPL': (-0.62, 2.12, 0.0), 'ombroPR': (0.62, 2.12, 0.0),
    'cotoL': (-0.70, 1.52, 0.0), 'cotoR': (0.70, 1.52, 0.0),
    'quadL': (-0.24, 1.30, 0.0), 'quadR': (0.24, 1.30, 0.0),
    'joeL': (-0.24, 0.80, 0.02), 'joeR': (0.24, 0.80, 0.02),
    'peL': (-0.24, 0.26, 0.04), 'peR': (0.24, 0.26, 0.04),
}


def construir(variante=0):
    P = []
    add = P.append
    # ---------------- pelve (raiz) ----------------
    add(caixa('pelvis', (0, 1.34, 0.0), (0.30, 0.12, 0.17), PEDRA, ch=0.10, jit=0.05, seed=1, grupo='pelvis'))
    for s in (-1, 1):
        add(caixa('ilio%d' % s, (s * 0.27, 1.40, -0.02), (0.10, 0.15, 0.15), PEDRA, rot=(0, 0, s * -22), ch=0.07, jit=0.05, seed=2, grupo='pelvis'))
    add(caixa('cinto', (0, 1.46, 0.0), (0.33, 0.045, 0.20), TERRA, ch=0.03, jit=0.03, seed=3, grupo='pelvis'))
    add(caixa('fivela', (0, 1.46, 0.205), (0.07, 0.06, 0.03), CINZA, ch=0.02, jit=0.03, seed=4, grupo='pelvis'))
    # argola de chaves no quadril esquerdo (pende do cinto)
    add(caixa('argola', (-0.34, 1.34, 0.08), (0.04, 0.10, 0.10), CINZA, ch=0.03, jit=0.04, seed=5, grupo='pelvis'))
    for i, (dy, dz) in enumerate(((1.14, 0.10), (1.10, 0.02), (1.16, -0.04))):
        add(caixa('chave%d' % i, (-0.37, dy, dz), (0.025, 0.12, 0.04), CINZA, rot=(0, 0, 0), ch=0.02, jit=0.04, seed=6 + i, grupo='pelvis'))
        add(caixa('dentes%d' % i, (-0.37, dy - 0.13, dz), (0.025, 0.04, 0.07), CINZA, ch=0.015, jit=0.04, seed=9 + i, grupo='pelvis'))
    for s, L in ((-1, 'L'), (1, 'R')):
        q = ('quad' + L,)
        j = ('quad' + L, 'joe' + L)
        p = ('quad' + L, 'joe' + L, 'pe' + L)
        # ---------------- perna ----------------
        add(caixa('coxa' + L, (s * 0.24, 1.06, 0.0), (0.075, 0.26, 0.085), PEDRA, ch=0.06, jit=0.05, cadeia=q, seed=11, grupo='coxa' + L))
        add(caixa('joelho' + L, (s * 0.24, 0.82, 0.04), (0.105, 0.085, 0.105), PEDRA, ch=0.07, jit=0.06, cadeia=q, seed=12, grupo='coxa' + L))
        add(caixa('canela' + L, (s * 0.24, 0.54, 0.02), (0.060, 0.28, 0.070), PEDRA, ch=0.05, jit=0.05, cadeia=j, seed=13, grupo='canela' + L))
        add(caixa('perneira' + L, (s * 0.24, 0.50, 0.075), (0.085, 0.12, 0.045), CINZA, rot=(-4, 0, 0), ch=0.04, jit=0.05, cadeia=j, seed=14, grupo='canela' + L))
        add(caixa('pe' + L, (s * 0.24, 0.10, 0.12), (0.10, 0.075, 0.26), PEDRA, ch=0.06, jit=0.06, cadeia=p, seed=15, grupo='pe' + L))
        add(caixa('bota' + L, (s * 0.24, 0.15, 0.20), (0.115, 0.07, 0.18), CINZA, ch=0.05, jit=0.04, cadeia=p, seed=16, grupo='pe' + L))
        # ---------------- ombreira de ferro com espinho ----------------
        add(caixa('ombreira' + L, (s * 0.60, 2.31, 0.0), (0.19, 0.075, 0.21), CINZA, rot=(0, 0, s * -24), ch=0.12, jit=0.05, cadeia=('tronco', 'ombroP' + L), seed=17, grupo='ombreira' + L))
        add(caixa('espinho' + L, (s * 0.72, 2.45, 0.0), (0.045, 0.16, 0.045), CINZA, rot=(0, 0, s * -30), ch=0.04, jit=0.04, cadeia=('tronco', 'ombroP' + L), seed=18, grupo='ombreira' + L))
        # ---------------- braço ----------------
        a = ('tronco', 'ombro' + L)
        c = ('tronco', 'ombro' + L, 'coto' + L)
        add(caixa('umero' + L, (s * 0.66, 1.84, 0.0), (0.060, 0.30, 0.065), PEDRA, ch=0.05, jit=0.05, cadeia=a, seed=19, grupo='braco' + L))
        add(caixa('cotovelo' + L, (s * 0.68, 1.52, 0.0), (0.090, 0.075, 0.090), PEDRA, ch=0.06, jit=0.06, cadeia=a, seed=20, grupo='braco' + L))
        add(caixa('antebraco' + L, (s * 0.70, 1.14, 0.02), (0.052, 0.31, 0.060), PEDRA, ch=0.045, jit=0.05, cadeia=c, seed=21, grupo='antebraco' + L))
        add(caixa('algema' + L, (s * 0.70, 0.84, 0.02), (0.115, 0.07, 0.115), CINZA, ch=0.05, jit=0.04, cadeia=c, seed=22, grupo='antebraco' + L))
        add(caixa('punho' + L, (s * 0.70, 0.66, 0.04), (0.10, 0.10, 0.11), PEDRA, ch=0.07, jit=0.06, cadeia=c, seed=23, grupo='antebraco' + L))
        for i, dx in enumerate((-0.07, -0.023, 0.023, 0.07)):
            add(caixa('dedo%s%d' % (L, i), (s * 0.70 + dx, 0.55, 0.12), (0.018, 0.075, 0.025), PEDRA, ch=0.015, jit=0.05, cadeia=c, seed=24 + i, grupo='antebraco' + L))
    # ---------------- marreta (mão direita): cabo pelo punho e cabeça de ferro com cinta ----------------
    c = ('tronco', 'ombroR', 'cotoR')
    add(caixa('cabo', (0.70, 0.34, 0.10), (0.036, 0.46, 0.036), TERRA, ch=0.025, jit=0.04, cadeia=c, seed=30, grupo='antebracoR'))
    add(caixa('marreta', (0.70, -0.06, 0.10), (0.27, 0.19, 0.19), CINZA, ch=0.10, jit=0.05, cadeia=c, seed=31, grupo='antebracoR'))
    add(caixa('cinta', (0.70, -0.06, 0.10), (0.285, 0.05, 0.205), TERRA, ch=0.03, jit=0.03, cadeia=c, seed=32, grupo='antebracoR'))
    # ---------------- tronco: coluna, caixa torácica aberta e clavículas ----------------
    t = ('tronco',)
    add(caixa('cavidade', (0, 1.90, 0.0), (0.24, 0.40, 0.14), TERRA, ch=0.10, jit=0.03, cadeia=t, seed=40, grupo='tronco'))
    add(caixa('coluna', (0, 1.78, -0.12), (0.045, 0.40, 0.050), PEDRA, ch=0.03, jit=0.04, cadeia=t, seed=41, grupo='tronco'))
    add(caixa('esterno', (0, 1.96, 0.22), (0.045, 0.30, 0.040), PEDRA, ch=0.03, jit=0.04, cadeia=t, seed=42, grupo='tronco'))
    for k, y in enumerate((1.66, 1.82, 1.98, 2.14)):
        w = (0.27, 0.31, 0.32, 0.27)[k]
        for s in (-1, 1):
            add(caixa('costela%d_%d' % (k, s), (s * w * 0.62, y, 0.14), (w * 0.42, 0.024, 0.036), PEDRA, rot=(0, s * -28, 0), ch=0.02, jit=0.05, cadeia=t, seed=43, grupo='tronco'))
            add(caixa('lado%d_%d' % (k, s), (s * w * 0.99, y, -0.01), (0.036, 0.024, 0.15), PEDRA, ch=0.02, jit=0.05, cadeia=t, seed=44, grupo='tronco'))
            add(caixa('tras%d_%d' % (k, s), (s * w * 0.62, y, -0.17), (w * 0.38, 0.024, 0.034), PEDRA, rot=(0, s * 24, 0), ch=0.02, jit=0.05, cadeia=t, seed=45, grupo='tronco'))
    for s in (-1, 1):
        add(caixa('clavicula%d' % s, (s * 0.30, 2.22, 0.02), (0.30, 0.04, 0.05), PEDRA, rot=(0, 0, s * -8), ch=0.03, jit=0.04, cadeia=t, seed=46, grupo='tronco'))
    # correntes cruzadas no peito (bandoleira): argolas de ferro em diagonal
    for s in (-1, 1):
        for i in range(6):
            k = i / 5.0
            x = s * (-0.30 + 0.60 * k) * -1
            y = 2.20 - 0.58 * k
            add(caixa('elo%d_%d' % (s, i), (x, y, 0.27), (0.045, 0.030, 0.026), CINZA, rot=(0, 0, s * 38 + (60 if i % 2 else 0)), ch=0.02, jit=0.04, cadeia=t, seed=47 + i, grupo='tronco'))
    # ---------------- cabeça: caveira, mandíbula, órbitas em brasa e coroa de ferro ----------------
    h = ('tronco', 'cabeca')
    add(caixa('cranio', (0, 2.40, 0.0), (0.20, 0.20, 0.21), PEDRA, ch=0.10, jit=0.04, cadeia=h, seed=50, grupo='cabeca'))
    add(caixa('face', (0, 2.30, 0.14), (0.15, 0.11, 0.09), PEDRA, ch=0.06, jit=0.04, cadeia=h, seed=51, grupo='cabeca'))
    add(caixa('mandibula', (0, 2.15, 0.08), (0.12, 0.05, 0.12), PEDRA, ch=0.04, jit=0.05, cadeia=h, seed=52, grupo='cabeca'))
    add(caixa('dentes', (0, 2.205, 0.20), (0.11, 0.024, 0.02), TERRA, ch=0.01, jit=0.03, cadeia=h, seed=53, grupo='cabeca'))
    for s in (-1, 1):
        add(caixa('orbita%d' % s, (s * 0.085, 2.38, 0.21), (0.065, 0.058, 0.03), TERRA, ch=0.02, jit=0.03, cadeia=h, seed=54, grupo='cabeca'))
        add(esfera('olho%d' % s, (s * 0.085, 2.38, 0.225), 0.046, OLHO, cadeia=h, grupo='cabeca'))
    add(caixa('aro', (0, 2.60, 0.0), (0.22, 0.04, 0.23), CINZA, ch=0.03, jit=0.03, cadeia=h, seed=55, grupo='cabeca'))
    for i, (x, z, hgt) in enumerate(((0.0, 0.21, 0.14), (-0.15, 0.15, 0.11), (0.15, 0.15, 0.11), (-0.21, 0.0, 0.12), (0.21, 0.0, 0.12), (0.0, -0.21, 0.11))):
        add(caixa('ponta%d' % i, (x, 2.68 + hgt * 0.45, z), (0.030, hgt, 0.030), CINZA, ch=0.015, jit=0.04, cadeia=h, seed=56 + i, grupo='cabeca'))
    add(caixa('pescoco', (0, 2.16, -0.02), (0.045, 0.07, 0.045), PEDRA, ch=0.03, jit=0.04, cadeia=t, seed=62, grupo='tronco'))
    add(caixa('gola', (0, 2.24, 0.0), (0.17, 0.040, 0.15), CINZA, ch=0.03, jit=0.03, cadeia=t, seed=63, grupo='tronco'))
    return P
