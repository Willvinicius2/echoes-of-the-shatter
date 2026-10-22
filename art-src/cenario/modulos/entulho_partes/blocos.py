"""Parte 1: blocos grandes cortados, empilhados por altura (sem bloco solto)."""
import math
from comum import bloco, rnd

H = math.radians
# (x, y, tamanho, rotação, escura?) do chão para o cume; o assentamento calcula o z
PILHA = [
    ((-0.55, -0.10), (0.80, 0.70, 0.42), (0, 0, H(12)), False),
    ((0.35, 0.20), (0.70, 0.66, 0.38), (0, 0, H(-20)), True),
    ((-0.10, 0.62), (0.58, 0.46, 0.34), (0, 0, H(35)), False),
    ((0.20, -0.58), (0.62, 0.42, 0.32), (0, 0, H(-8)), True),
    ((-0.12, 0.00), (0.60, 0.52, 0.40), (H(4), H(-5), H(28)), False),
    ((0.52, -0.15), (0.46, 0.42, 0.34), (H(-6), H(5), H(-40)), False),
    ((-0.40, 0.40), (0.42, 0.36, 0.30), (H(6), H(8), H(52)), True),
    ((0.10, 0.12), (0.38, 0.32, 0.28), (H(8), H(-6), H(15)), False),
]

def construir(M, alt):
    out = []
    for (x, y), tam, rot, escura in PILHA:
        o = bloco((x, y, tam[2] / 2), tam, rot, M["escura"] if escura else M["pedra"], lascas=3, relevo=True)
        alt.assentar(o); out.append(o)
    return out
