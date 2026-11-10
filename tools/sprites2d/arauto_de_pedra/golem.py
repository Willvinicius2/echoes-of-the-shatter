"""Geometria do Arauto de Pedra (golem de blocos de pedra marfim com musgo e um olho laranja), em metros.

Origem no centro dos pés, +y para cima, +z para a frente do golem. Segue o desenho aprovado (folha m06): ombreiras enormes,
peitoral em duas placas sobre um núcleo de terra, cabeça afundada com um olho só e crista de lajes, braços e punhos grossos,
quadris em V, coxas e canelas de pedra com juntas de terra e pés largos com dedos de pedra.
"""
import numpy as np
from render import caixa, esfera, PEDRA, TERRA, OLHO

JUNTAS = {
    'tronco': (0.0, 1.40, 0.0),
    'cabeca': (0.0, 2.22, 0.12),
    'ombroL': (-0.98, 2.14, 0.0), 'ombroR': (0.98, 2.14, 0.0),
    'ombroPL': (-0.98, 2.14, 0.0), 'ombroPR': (0.98, 2.14, 0.0),
    'cotoL': (-1.04, 1.46, 0.0), 'cotoR': (1.04, 1.46, 0.0),
    'quadL': (-0.46, 1.32, 0.0), 'quadR': (0.46, 1.32, 0.0),
    'joeL': (-0.46, 0.92, 0.02), 'joeR': (0.46, 0.92, 0.02),
    'peL': (-0.46, 0.30, 0.05), 'peR': (0.46, 0.30, 0.05),
}


def construir(variante=0):
    P = []
    add = P.append
    # ---------------- pélvis e quadril (raiz) ----------------
    add(caixa('pelvis', (0, 1.36, 0.0), (0.62, 0.26, 0.40), TERRA, ch=0.40, jit=0.05, seed=1, grupo='pelvis'))
    add(caixa('quadril_frente', (0, 1.42, 0.40), (0.40, 0.24, 0.10), PEDRA, rot=(-6, 0, 0), ch=0.26, jit=0.05, musgo=0.4, seed=2, grupo='pelvis'))
    add(caixa('quadril_v', (0, 1.18, 0.43), (0.22, 0.22, 0.09), PEDRA, rot=(-6, 0, 45), ch=0.16, jit=0.04, seed=3, grupo='pelvis'))
    add(caixa('quadril_costas', (0, 1.40, -0.40), (0.42, 0.26, 0.10), PEDRA, rot=(6, 0, 0), ch=0.26, jit=0.05, musgo=0.4, seed=4, grupo='pelvis'))
    for s, L in ((-1, 'L'), (1, 'R')):
        # ---------------- perna ----------------
        q = ('quad' + L,)
        j = ('quad' + L, 'joe' + L)
        p = ('quad' + L, 'joe' + L, 'pe' + L)
        add(caixa('coxa' + L, (s * 0.46, 1.10, 0.0), (0.34, 0.34, 0.34), PEDRA, rot=(0, s * 6, s * -4), ch=0.42, jit=0.06, musgo=0.45, cadeia=q, seed=5, grupo='coxa' + L))
        add(caixa('joelho' + L, (s * 0.46, 0.84, 0.02), (0.23, 0.20, 0.23), TERRA, rot=(0, s * 20, 0), ch=0.30, jit=0.08, cadeia=q, seed=50, grupo='coxa' + L))
        add(caixa('canela' + L, (s * 0.46, 0.60, 0.02), (0.30, 0.28, 0.30), PEDRA, rot=(0, s * 4, 0), ch=0.40, jit=0.06, musgo=0.35, cadeia=j, seed=6, grupo='canela' + L))
        add(caixa('joelheira' + L, (s * 0.46, 0.78, 0.28), (0.20, 0.17, 0.10), PEDRA, rot=(-12, 0, 0), ch=0.18, jit=0.05, musgo=0.6, cadeia=j, seed=7, grupo='canela' + L))
        add(caixa('tornozelo' + L, (s * 0.46, 0.33, 0.04), (0.18, 0.15, 0.18), TERRA, rot=(0, s * -15, 0), ch=0.24, jit=0.08, cadeia=j, seed=51, grupo='canela' + L))
        add(caixa('pe' + L, (s * 0.46, 0.13, 0.10), (0.28, 0.13, 0.38), PEDRA, rot=(0, s * 9, 0), ch=0.30, jit=0.06, musgo=0.4, cadeia=p, seed=8, grupo='pe' + L))
        for i, dx in enumerate((-0.17, 0.0, 0.17)):
            add(caixa('dedo%s%d' % (L, i), (s * 0.46 + dx * 1.15 + s * 0.05, 0.11, 0.50), (0.085, 0.105, 0.13), PEDRA, rot=(0, s * 9, 0), ch=0.06, jit=0.05, cadeia=p, seed=9 + i, grupo='pe' + L))
        # ---------------- braço ----------------
        a = ('tronco', 'ombro' + L)
        c = ('tronco', 'ombro' + L, 'coto' + L)
        add(caixa('ombreira' + L, (s * 0.92, 2.44, 0.0), (0.40, 0.30, 0.42), PEDRA, rot=(0, 0, s * -10), ch=0.46, jit=0.07, musgo=0.8, cadeia=('tronco', 'ombroP' + L), seed=10, grupo='ombreira' + L))
        add(caixa('ombro' + L, (s * 0.99, 2.12, 0.0), (0.27, 0.24, 0.27), TERRA, rot=(0, s * 25, 0), ch=0.36, jit=0.08, cadeia=a, seed=52, grupo='braco' + L))
        add(caixa('braco' + L, (s * 1.04, 1.84, 0.0), (0.25, 0.34, 0.26), PEDRA, rot=(0, 0, s * -4), ch=0.34, jit=0.06, musgo=0.3, cadeia=a, seed=11, grupo='braco' + L))
        add(caixa('cotovelo' + L, (s * 1.05, 1.47, 0.0), (0.21, 0.19, 0.21), TERRA, rot=(0, s * -20, 0), ch=0.28, jit=0.08, cadeia=a, seed=53, grupo='braco' + L))
        add(caixa('antebraco' + L, (s * 1.08, 1.04, 0.04), (0.31, 0.42, 0.29), PEDRA, rot=(-4, 0, s * -3), ch=0.40, jit=0.06, musgo=0.4, cadeia=c, seed=12, grupo='antebraco' + L))
        add(caixa('punho' + L, (s * 1.08, 0.56, 0.08), (0.26, 0.19, 0.26), PEDRA, rot=(0, 0, 0), ch=0.26, jit=0.06, cadeia=c, seed=13, grupo='antebraco' + L))
        for i, dx in enumerate((-0.15, -0.05, 0.05, 0.15)):
            add(caixa('nó%s%d' % (L, i), (s * 1.08 + dx, 0.40, 0.31), (0.052, 0.10, 0.085), PEDRA, ch=0.05, jit=0.05, cadeia=c, seed=14 + i, grupo='antebraco' + L))
    # ---------------- tronco ----------------
    t = ('tronco',)
    add(caixa('barriga', (0, 1.66, 0.0), (0.46, 0.32, 0.38), TERRA, ch=0.34, jit=0.05, cadeia=t, seed=20, grupo='tronco'))
    add(caixa('nucleo', (0, 2.00, 0.0), (0.68, 0.46, 0.46), TERRA, ch=0.40, jit=0.05, cadeia=t, seed=21, grupo='tronco'))
    for s, L in ((-1, 'L'), (1, 'R')):
        add(caixa('peito' + L, (s * 0.37, 1.96, 0.30), (0.40, 0.42, 0.30), PEDRA, rot=(-6, s * -14, 0), ch=0.40, jit=0.06, musgo=0.45, cadeia=t, seed=22, grupo='tronco'))
        add(caixa('costas' + L, (s * 0.38, 1.98, -0.32), (0.42, 0.46, 0.28), PEDRA, rot=(6, s * 14, 0), ch=0.40, jit=0.06, musgo=0.5, cadeia=t, seed=23, grupo='tronco'))
    # ---------------- cabeça ----------------
    h = ('tronco', 'cabeca')
    add(caixa('cabeca', (0, 2.30, 0.12), (0.36, 0.34, 0.36), TERRA, ch=0.36, jit=0.06, cadeia=h, seed=54, grupo='cabeca'))
    add(esfera('olho', (0, 2.27, 0.43), 0.19, OLHO, cadeia=h, grupo='cabeca'))
    add(caixa('crista0', (0, 2.78, 0.02), (0.13, 0.27, 0.19), PEDRA, rot=(-8, 0, 0), ch=0.14, jit=0.05, musgo=0.35, cadeia=h, seed=30, grupo='cabeca'))
    for s in (-1, 1):
        add(caixa('crista%d' % (s + 2), (s * 0.24, 2.70, 0.04), (0.12, 0.23, 0.18), PEDRA, rot=(-6, 0, s * -16), ch=0.12, jit=0.05, cadeia=h, seed=31, grupo='cabeca'))
        add(caixa('crista%d' % (s + 6), (s * 0.43, 2.53, 0.06), (0.11, 0.18, 0.16), PEDRA, rot=(-4, 0, s * -34), ch=0.10, jit=0.05, cadeia=h, seed=32, grupo='cabeca'))
    return P
