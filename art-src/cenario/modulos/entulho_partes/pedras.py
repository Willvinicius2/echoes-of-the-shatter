"""Parte 2: pedras soltas e lascas ao redor da pilha (poucas faces, facetadas)."""
import math
from comum import bloco, rnd

def construir(M, alt, n=12):
    out = []
    for _ in range(n):
        a = rnd.uniform(0, 6.283); r = rnd.uniform(0.85, 1.15)
        s = rnd.uniform(0.07, 0.19)
        tam = (s * rnd.uniform(1.0, 1.8), s * rnd.uniform(0.8, 1.4), s * rnd.uniform(0.6, 1.0))
        o = bloco((math.cos(a) * r * 1.1, math.sin(a) * r * 0.85, tam[2] / 2), tam, (rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), rnd.uniform(0, 6.28)),
                  M["pedra"] if rnd.random() > 0.4 else M["escura"], lascas=4, relevo=False, bev=0.06)
        alt.assentar(o); out.append(o)
    return out
