"""Motor de animação por recorte para o Cão de Cinza (sem serviço pago).

A base são as cinco vistas aprovadas (art-src/pixellab/cao_de_cinza/base/jogo_<S|SE|E|NE|N>.png, 64 px).

Tudo é deslocamento de pixel inteiro (translação, cisalhamento por linha ou coluna, reamostragem de linhas por
vizinho mais próximo), então os pixels e a paleta da base aprovada não mudam: só se movem. Nada de rotação com
reamostragem, que quebraria o contorno de 1 px.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path(__file__).resolve().parents[3] / 'art-src' / 'pixellab' / 'cao_de_cinza' / 'base'
Q = 92
PAD = (Q - 64) // 2


def carregar(nome):
    a = np.array(Image.open(SRC / f'jogo_{nome}.png').convert('RGBA'))
    out = np.zeros((Q, Q, 4), np.uint8)
    out[PAD:PAD + 64, PAD:PAD + 64] = a
    return out


def vazio():
    return np.zeros((Q, Q, 4), np.uint8)


def opaco(a):
    return a[..., 3] > 0


def deslocar(a, dx, dy):
    """Translação inteira com borda transparente."""
    dx, dy = int(round(dx)), int(round(dy))
    out = vazio()
    h, w = a.shape[:2]
    xs0, xs1 = max(0, -dx), min(w, w - dx)
    ys0, ys1 = max(0, -dy), min(h, h - dy)
    if xs1 > xs0 and ys1 > ys0:
        out[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx] = a[ys0:ys1, xs0:xs1]
    return out


def cisalhar_linhas(a, desloc):
    """Cada linha r desloca desloc(r) px na horizontal (função devolve inteiro)."""
    out = vazio()
    for r in range(a.shape[0]):
        d = int(desloc(r))
        row = a[r]
        if not row[:, 3].any():
            continue
        if d == 0:
            out[r] = row
        elif d > 0:
            out[r, d:] = row[:-d]
        else:
            out[r, :d] = row[-d:]
    return out


def cisalhar_colunas(a, desloc):
    """Cada coluna c desloca desloc(c) px na vertical."""
    out = vazio()
    for c in range(a.shape[1]):
        d = int(desloc(c))
        col = a[:, c]
        if not col[:, 3].any():
            continue
        if d == 0:
            out[:, c] = col
        elif d > 0:
            out[d:, c] = col[:-d]
        else:
            out[:d, c] = col[-d:]
    return out


def colar(dst, src):
    """Cola os pixels opacos de src sobre dst (alfa binário)."""
    m = src[..., 3] > 0
    dst[m] = src[m]
    return dst


def deformar_perna(a, y_quadril, dx, dy):
    """Perna presa no quadril (linha y_quadril): o pé desloca dx na horizontal e dy na vertical.
    As linhas abaixo do quadril são reamostradas (vizinho mais próximo) para encurtar ou esticar a perna;
    o deslocamento horizontal cresce linearmente do quadril ao pé (cisalhamento)."""
    rows = np.where(a[..., 3].any(axis=1))[0]
    if len(rows) == 0:
        return a.copy()
    y_pe = rows.max()
    comp = y_pe - y_quadril
    if comp <= 1:
        return deslocar(a, dx, dy)
    novo = max(2, comp + int(round(dy)))
    out = vazio()
    out[:y_quadril] = a[:y_quadril]
    for j in range(0, novo + 1):
        s = min(comp, int(round(j * comp / novo)))
        row = a[y_quadril + s]
        if not row[:, 3].any():
            continue
        d = int(round(dx * j / novo))
        yy = y_quadril + j
        if yy >= Q:
            break
        if d == 0:
            out[yy] = row
        elif d > 0:
            out[yy, d:] = row[:-d]
        else:
            out[yy, :d] = row[-d:]
    return out


def ondular(a, y_raiz, y_ponta, amp, fase, volta=2.4):
    """Onda horizontal na cauda: peso 0 na raiz e 1 na ponta (linhas entre y_raiz e y_ponta)."""
    def desloc(r):
        if y_ponta == y_raiz:
            return 0
        w = (r - y_raiz) / (y_ponta - y_raiz)
        if w <= 0:
            return 0
        w = min(1.0, w)
        return round(amp * w * math.sin(fase + volta * w))
    return cisalhar_linhas(a, desloc)


def ondular_v(a, x_raiz, x_ponta, amp, fase, volta=2.4):
    """Onda vertical na cauda (colunas entre x_raiz e x_ponta)."""
    def desloc(c):
        if x_ponta == x_raiz:
            return 0
        w = (c - x_raiz) / (x_ponta - x_raiz)
        if w <= 0:
            return 0
        w = min(1.0, w)
        return round(amp * w * math.sin(fase + volta * w))
    return cisalhar_colunas(a, desloc)
