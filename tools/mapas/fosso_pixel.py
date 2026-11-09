#!/usr/bin/env python3
"""Fosso (corte de pedreira) e ponte de tábuas pintados em pixel art, por código (sem IA generativa).

Usado por `gerar_fase_2.py` (Pedreira dos Ecos): o mapa marca as células do fosso com `f` e as da ponte com `=`; este
módulo pinta um PNG por fosso e por ponte, na grade de 1 px de mundo do jogo (alfa binário, contorno preto de 1 px,
luz de cima-esquerda, borda tracejada em vez de sombra suave), e o cliente só cola os PNG como decalques de chão.

Direção do Jev (thread da área 2) e revisão v2: fosso com beiral de lajes de ~6 a 9 px em 3 tons, espessura da laje
sob a borda norte, parede norte em DOIS tons (faixa de cima quente e iluminada, faixa de baixo fria), tiras escuras
das paredes leste e oeste, chão azul-acinzentado escuro com uma luz fraca subindo do fundo (3 degraus de dither) e
entulho em pedras irregulares de 2 tons que somem no escuro. Ponte com tábuas legíveis, corrimão, desgaste nas pontas
e sombra projetada de 1 tom no fosso (o único alfa parcial permitido).

    pintar_fosso(celulas, semente) -> (Image RGBA, (ox, oy))   # (ox, oy): canto do PNG em px de mundo (origem = célula 0,0)
    pintar_ponte(celulas, semente) -> (Image RGBA, (ox, oy))

`celulas` é um conjunto de (coluna, linha) de um fosso inteiro (células `f` e `=` juntas, conexas) ou de uma ponte
(só as células `=`). Uso de teste: python3 -I tools/mapas/fosso_pixel.py --previa DIR
"""
import math
import os
import sys

import numpy as np
from PIL import Image

TILE = 64
PAD = 16          # margem do PNG em volta do fosso (borda clara e franja tracejada)
RAIO_IN = 20
RAIO_OUT = 14
PAREDE = 30       # altura (px) da parede norte do corte visível dentro do fosso (sem contar a espessura da laje)
ESP_LAJE = 3      # espessura (px) da laje do beiral vista por baixo da borda norte

# Paleta (os tons de pedra são os dos props da área 1: montar_marcos.py)
K0 = (0, 0, 0)
K1 = (21, 16, 25)
S2 = (53, 51, 63)
S3 = (62, 61, 72)
S4 = (72, 59, 62)
S5 = (87, 71, 67)
S6 = (119, 101, 100)
S7 = (136, 111, 104)
S8 = (159, 133, 119)
S9 = (184, 154, 127)
F1 = (50, 41, 54)      # histórico (chão v1); hoje o chão usa B0..B3
F2 = (27, 21, 33)
C0 = (34, 35, 47)      # base fria da parede, onde ela some no escuro
B0 = (16, 18, 27)      # chão do fosso: azul-acinzentado escuro, longe da luz
B1 = (23, 28, 39)
B2 = (30, 38, 53)
B3 = (38, 48, 66)      # chão do fosso: ponto mais claro da luz fraca do fundo
R2 = (98, 96, 114)     # entulho: tom claro (cima-esquerda)
R1 = (56, 55, 72)      # entulho: tom escuro (baixo-direita)
R0 = (28, 28, 40)      # entulho: contorno (escuro, não preto)
# madeira da ponte
W0 = (44, 31, 28)      # fresta / sombra funda
W1 = (86, 63, 50)
W2 = (120, 91, 66)
W3 = (156, 124, 88)
W4 = (186, 154, 108)
I1 = (75, 69, 76)      # ferro dos pregos

SOMBRA_ALFA = 110      # alfa fixo da sombra projetada da ponte (único alfa parcial de todo o módulo)
SOMBRA_DESL = 9        # deslocamento da sombra (px) para baixo e para a direita: luz de cima-esquerda, fosso fundo

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) / 16.0 + 1.0 / 32.0


def _bayer(h, w, x0=0, y0=0):
    ys = (np.arange(h) + y0) % 4
    xs = (np.arange(w) + x0) % 4
    return BAYER[ys[:, None], xs[None, :]]


_DISCOS = {}


def _discos(raio):
    if raio not in _DISCOS:
        offs = []
        for dy in range(-raio, raio + 1):
            for dx in range(-raio, raio + 1):
                d = math.hypot(dx, dy)
                if 0 < d <= raio:
                    offs.append((d, dx, dy))
        offs.sort()
        _DISCOS[raio] = offs
    return _DISCOS[raio]


def _distancia_ate(alvo, raio):
    """Distância de cada pixel ao pixel `alvo` mais próximo (limitada a `raio`; `raio + 1` se não houver)."""
    h, w = alvo.shape
    res = np.full((h, w), raio + 1.0, dtype=np.float32)
    res[alvo] = 0.0
    pad = np.pad(alvo, raio, constant_values=False)
    feito = alvo.copy()
    for d, dx, dy in _discos(raio):
        desl = pad[raio + dy:raio + dy + h, raio + dx:raio + dx + w]
        novo = desl & ~feito
        if novo.any():
            res[novo] = d
            feito |= novo
            if feito.all():
                break
    return res


def _perfil(n, rng, amp, p):
    """Perfil 1D de degraus raros (cada degrau de 1 a 3 px), preso em [-amp, amp]: borda reta que dá um passo de vez em quando."""
    v = 0
    out = np.zeros(n, dtype=np.int32)
    for i in range(n):
        if rng.random() < p:
            v = int(np.clip(v + rng.choice([-3, -2, -1, 1, 2, 3]), -amp, amp))
        out[i] = v
    return out


def _caixa_media(m, r):
    """Média móvel quadrada (raio r) de uma máscara booleana, por somas acumuladas."""
    f = m.astype(np.float32)
    k = 2 * r + 1
    p = np.pad(f, r, mode="edge")
    c = np.cumsum(np.cumsum(p, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = m.shape
    soma = c[k:k + h, k:k + w] - c[0:h, k:k + w] - c[k:k + h, 0:w] + c[0:h, 0:w]
    return soma / float(k * k)


def _mascara(celulas, rng):
    xs = [c[0] for c in celulas]
    ys = [c[1] for c in celulas]
    cx0, cx1, cy0, cy1 = min(xs), max(xs), min(ys), max(ys)
    cw, ch = cx1 - cx0 + 1, cy1 - cy0 + 1
    cel = np.zeros((ch, cw), dtype=bool)
    for (x, y) in celulas:
        cel[y - cy0, x - cx0] = True
    w, h = cw * TILE + 2 * PAD, ch * TILE + 2 * PAD
    yy, xx = np.mgrid[0:h, 0:w]
    dx = _perfil(h, rng, 5, 0.045)[yy]
    dy = _perfil(w, rng, 4, 0.045)[xx]
    sx = np.floor((xx - PAD + dx) / TILE).astype(np.int32)
    sy = np.floor((yy - PAD + dy) / TILE).astype(np.int32)
    ok = (sx >= 0) & (sx < cw) & (sy >= 0) & (sy < ch)
    m = np.zeros((h, w), dtype=bool)
    m[ok] = cel[sy[ok], sx[ok]]
    # cantos arredondados (raio ~5 px): média móvel e limiar
    m = _caixa_media(m, 5) > 0.5
    # lascas: pequenos retângulos arrancados ou acrescentados na borda
    borda = m ^ (np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1) & m)
    ys_b, xs_b = np.nonzero(borda)
    if len(ys_b):
        n = max(6, len(ys_b) // 90)
        for _ in range(n):
            i = rng.randrange(len(ys_b))
            x, y = int(xs_b[i]), int(ys_b[i])
            lw, lh = rng.randint(3, 9), rng.randint(2, 5)
            x0, y0 = x - lw // 2, y - lh // 2
            sub = (slice(max(y0, 0), min(y0 + lh, h)), slice(max(x0, 0), min(x0 + lw, w)))
            m[sub] = not m[y, x]
    return m, (cx0 * TILE - PAD, cy0 * TILE - PAD)


def _ruido_suave(h, w, passo, rng):
    """Ruído de valor em [0, 1]: grade grosseira de `passo` px interpolada (bilinear), sem aleatório global."""
    gh, gw = h // passo + 3, w // passo + 3
    g = np.array([[rng.random() for _ in range(gw)] for _ in range(gh)], dtype=np.float32)
    ys = np.arange(h) / float(passo)
    xs = np.arange(w) / float(passo)
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    fy = (ys - y0)[:, None]
    fx = (xs - x0)[None, :]
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _lajes(h, w, vao, rng):
    """Pedra do beiral em lajes irregulares (Voronoi de sementes com jitter): devolve (índice da laje, folga até a junta)."""
    gh, gw = h // vao + 3, w // vao + 3
    sx = np.zeros((gh, gw), dtype=np.float32)
    sy = np.zeros((gh, gw), dtype=np.float32)
    for gy in range(gh):
        for gx in range(gw):
            sx[gy, gx] = (gx - 1 + 0.5 + (rng.random() - 0.5) * 0.8) * vao
            sy[gy, gx] = (gy - 1 + 0.5 + (rng.random() - 0.5) * 0.8) * vao
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    gy0 = (yy // vao).astype(int) + 1
    gx0 = (xx // vao).astype(int) + 1
    melhor = np.full((h, w), 1e9, dtype=np.float32)
    segundo = np.full((h, w), 1e9, dtype=np.float32)
    idx = np.zeros((h, w), dtype=np.int32)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            gy = np.clip(gy0 + oy, 0, gh - 1)
            gx = np.clip(gx0 + ox, 0, gw - 1)
            d = np.hypot(xx - sx[gy, gx], yy - sy[gy, gx])
            novo = d < melhor
            segundo = np.where(novo, melhor, np.minimum(segundo, d))
            idx = np.where(novo, gy * gw + gx, idx)
            melhor = np.where(novo, d, melhor)
    return idx, segundo - melhor


def _contagem(m, eixo, inverso=False):
    """Para cada pixel de `m`, quantos pixels seguidos de `m` há até ele a partir da borda (eixo 0: de cima; eixo 1: da
    esquerda; `inverso`: de baixo / da direita). 0 fora de `m`."""
    a = m if eixo == 0 else m.T
    if inverso:
        a = a[::-1]
    k = np.zeros(a.shape, dtype=np.int32)
    for y in range(a.shape[0]):
        k[y] = np.where(a[y], (k[y - 1] + 1) if y else 1, 0)
    if inverso:
        k = k[::-1]
    return k if eixo == 0 else k.T


def _poligono(rng, raio):
    """Pedra irregular: polígono de 6 a 9 vértices em volta de um centro, raio variável, achatado e girado ao acaso.
    Devolve (máscara booleana, x0, y0) com x0/y0 relativos ao centro."""
    n = rng.randint(6, 9)
    ax, ay = 1.0 + 0.5 * rng.random(), 0.65 + 0.3 * rng.random()     # mais larga do que alta (pedra deitada)
    giro = rng.random() * math.pi
    pts = []
    for i in range(n):
        ang = (i + 0.5 * (rng.random() - 0.5)) * 2.0 * math.pi / n
        r = raio * (0.6 + 0.4 * rng.random())
        px, py = math.cos(ang) * r * ax, math.sin(ang) * r * ay
        pts.append((px * math.cos(giro) - py * math.sin(giro), px * math.sin(giro) + py * math.cos(giro)))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = int(math.floor(min(xs))) - 1, int(math.ceil(max(xs))) + 1
    y0, y1 = int(math.floor(min(ys))) - 1, int(math.ceil(max(ys))) + 1
    yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1].astype(np.float32) + 0.5
    dentro = np.zeros(yy.shape, dtype=bool)
    for i in range(n):
        (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
        if ya == yb:
            continue
        cruza = ((ya > yy) != (yb > yy)) & (xx < (xb - xa) * (yy - ya) / (yb - ya) + xa)
        dentro ^= cruza
    return dentro, x0, y0


def pintar_fosso(celulas, semente=1):
    import random
    rng = random.Random(semente)
    m, origem = _mascara(celulas, rng)
    h, w = m.shape
    npr = np.random.default_rng(semente)
    d_in = _distancia_ate(~m, RAIO_IN)
    d_out = _distancia_ate(m, RAIO_OUT)
    cor = np.zeros((h, w, 3), dtype=np.uint8)
    alfa = np.zeros((h, w), dtype=bool)
    bay = _bayer(h, w)
    ruido = npr.random((h, w)).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # --- beiral claro: lajes de calcário de ~13 px em 3 tons bem distintos, largura de 6 a 9 px, juntas visíveis,
    # quinas lascadas e contorno preto de 1 px junto do vazio
    larg = 7.0 + 3.0 * _ruido_suave(h, w, 40, rng)
    lab = (~m) & (d_out <= larg)
    idx, folga = _lajes(h, w, 13, rng)
    tons = [S9, S8, S7, S8, S9, S7, S8, S9]
    tom_idx = np.array([(int(i) * 2654435761 >> 7) % len(tons) for i in range(int(idx.max()) + 1)], dtype=np.int32)[idx]
    tom_laje = np.array(tons, dtype=np.uint8)[tom_idx]
    um_abaixo = np.array([S8 if t == S9 else (S7 if t == S8 else S6) for t in tons], dtype=np.uint8)[tom_idx]
    cor[lab] = tom_laje[lab]
    alfa |= lab
    t = d_out
    junta = lab & (folga < 1.0) & (t > 1.5)
    cor[junta] = S5                                                # junta entre lajes, bem marcada
    lasca = lab & ~junta & (folga < 2.4) & (ruido < 0.28) & (t > 1.5)
    cor[lasca] = um_abaixo[lasca]                                  # quina lascada: um tom abaixo junto da junta
    sel = lab & (t > 1.5) & (t <= 2.5) & (ruido < 0.35)
    cor[sel] = um_abaixo[sel]                                      # aresta interna um pouco roída
    cor[lab & (t <= 1.5)] = K0                                     # contorno preto de 1 px junto do vazio
    # luz: a aresta externa do beiral ganha um fio claro nas faces voltadas para cima-esquerda e escuro nas outras
    gy, gx = np.gradient(d_out.astype(np.float32))
    ilum = -(gx * -0.6 + gy * -0.8)                                # > 0: a normal externa aponta para a luz
    externa = lab & (t > larg - 1.0)
    cor[externa & (ilum < -0.1)] = S9
    cor[externa & (ilum > 0.3)] = S6
    corpo = lab & (t > 2.5) & (t <= larg - 1.0) & ~junta
    cor[corpo & (ruido < 0.04)] = S6                               # sujeira e furinhos
    cor[corpo & (ruido > 0.975)] = S9
    # franja tracejada: a pedra se desfaz no chão por pontos (Bayer), sem borda dura
    fr = (~m) & (d_out > larg) & (d_out <= larg + 4.0)
    pfr = np.clip((larg + 4.0 - d_out) / 4.0, 0.0, 1.0) * 0.85
    f = fr & (bay < pfr)
    cor[f] = S7
    alfa |= f

    # --- interior
    k = _contagem(m, 0)                   # linhas de fosso acima de cada pixel (1 = logo abaixo do beiral norte)
    kw = _contagem(m, 1)                  # colunas de fosso à esquerda
    ke = _contagem(m, 1, inverso=True)    # colunas de fosso à direita
    cor[m] = B0
    alfa |= m
    # espessura da laje do beiral norte, vista por baixo: 3 faces em tons frios de sombra
    laje_face = m & (k >= 1) & (k <= ESP_LAJE)
    cor[laje_face & (k == 1)] = S3
    cor[laje_face & (k == 2)] = S2
    cor[laje_face & (k == 3)] = C0
    # parede norte em dois tons: faixa de cima quente e iluminada (S5), de baixo fria e escura (S3); o limite anda em
    # degraus e a passagem é tracejada em 3 linhas
    parede = m & (k > ESP_LAJE) & (k <= ESP_LAJE + PAREDE)
    kk = k - ESP_LAJE
    lim = (PAREDE // 2) + _perfil(w, rng, 2, 0.06)
    dif = kk - lim[None, :]
    quente = parede & (bay < np.clip(0.5 - dif / 3.0, 0.0, 1.0))
    frio = parede & ~quente
    cor[quente] = S5
    cor[frio] = S3
    q3 = quente[..., None]
    alto = np.where(q3, np.array(S6, dtype=np.uint8), np.array(S4, dtype=np.uint8))      # realce por faixa
    baixo = np.where(q3, np.array(S4, dtype=np.uint8), np.array(S2, dtype=np.uint8))     # sombra por faixa
    fundo = np.where(q3, np.array(S3, dtype=np.uint8), np.array(C0, dtype=np.uint8))     # rachadura por faixa
    # fiadas de 5 a 9 px com topo claro, base escura, juntas verticais desencontradas e marcas de cunha
    fiadas = []
    y0 = 0
    while y0 < PAREDE:
        alt = rng.randint(5, 9)
        fiadas.append((y0, min(y0 + alt, PAREDE)))
        y0 += alt
    xs = np.arange(w)
    for (ya, yb) in fiadas:
        faixa = parede & (kk > ya) & (kk <= yb)
        sel = faixa & (kk == ya + 1) & (ruido > 0.3)
        cor[sel] = alto[sel]
        sel = faixa & (kk == yb) & (ruido < 0.85)
        cor[sel] = baixo[sel]
        passo = rng.randint(16, 34)
        desl = rng.randint(0, passo)
        junta_v = ((xs + desl) % passo == 0)
        sel = faixa & junta_v[None, :] & (ruido < 0.9)
        cor[sel] = baixo[sel]
        if rng.random() < 0.55:                                    # marcas de cunha: 3 tracinhos de 2 px
            p2, d2 = rng.randint(24, 48), rng.randint(0, 20)
            marca = (((xs + d2) % p2) % 3 == 0) & (((xs + d2) % p2) <= 6)
            sel = parede & (kk > ya + 1) & (kk <= ya + 3) & marca[None, :]
            cor[sel] = fundo[sel]
    # rachaduras: passeios verticais de 6 a 14 px, com um fio de realce à direita
    for _ in range(max(2, w // 70)):
        x = rng.randint(2, w - 3)
        y_ini = rng.randint(2, PAREDE - 8)
        for j in range(rng.randint(6, 14)):
            yk = y_ini + j
            if yk > PAREDE:
                break
            x = int(np.clip(x + rng.choice([-1, 0, 0, 0, 1]), 1, w - 2))
            sel = parede[:, x] & (kk[:, x] == yk)
            cor[sel, x] = fundo[sel, x]
            if rng.random() < 0.3:
                sel2 = parede[:, x + 1] & (kk[:, x + 1] == yk)
                cor[sel2, x + 1] = alto[sel2, x + 1]
    cor[parede & (kk == 1) & (bay < 0.5)] = C0                     # sombra da laje, logo abaixo da espessura
    # base da parede escurece por pontos até o tom frio de fundo, e este se desfaz em pontos sobre o chão
    for j in range(6):
        sel = parede & (kk == PAREDE - 5 + j) & (bay < (j + 1) / 7.0)
        cor[sel] = C0
    for j, pa in enumerate([0.75, 0.55, 0.38, 0.22, 0.1]):
        cor[m & (k == ESP_LAJE + PAREDE + 1 + j) & (bay < pa)] = C0

    # --- chão: azul-acinzentado muito escuro com uma luz fraca subindo do fundo (centro-baixo, um pouco diferente por
    # fosso), em 3 degraus de dither estreitos, sumindo em direção às paredes
    chao = m & ~parede & ~laje_face
    ys_c, xs_c = np.nonzero(chao)
    L = np.zeros((h, w), dtype=np.float32)
    if len(ys_c):
        x0c, x1c, y0c, y1c = xs_c.min(), xs_c.max(), ys_c.min(), ys_c.max()
        wc, hc = float(x1c - x0c + 1), float(y1c - y0c + 1)
        cx = (x0c + x1c) / 2.0 + (rng.random() - 0.5) * 0.3 * wc
        cy = y1c - 0.28 * hc + (rng.random() - 0.5) * 0.2 * hc
        rx = 0.55 * wc * (0.9 + 0.3 * rng.random())
        ry = 0.75 * hc * (0.9 + 0.2 * rng.random())
        dell = np.hypot((xx - cx) / rx, (yy - cy) / ry)
        L = np.clip(1.15 - 1.15 * dell, 0.0, 1.0)
        L *= np.clip((d_in - 2.0) / 9.0, 0.0, 1.0)
        L *= np.clip((k - ESP_LAJE - PAREDE - 3) / 12.0, 0.0, 1.0)
        L = np.clip(L * (0.8 + 0.4 * _ruido_suave(h, w, 24, rng)), 0.0, 1.0)
    nivel = np.clip(np.floor(L * 3.0 + 0.5 + (bay - 0.5) * 0.7), 0, 3).astype(np.int32)
    tons_chao = np.array([B0, B1, B2, B3], dtype=np.uint8)
    cor_chao = tons_chao[nivel]
    cor[chao] = cor_chao[chao]
    # tiras escuras das paredes leste e oeste (3 a 5 px), por dentro: a oeste mais funda (de costas para a luz)
    lw = 3 + (_perfil(h, rng, 1, 0.05) + 1)
    le = 3 + (_perfil(h, rng, 1, 0.05) + 1)
    faixa_w = chao & (kw <= lw[:, None])
    faixa_e = chao & (ke <= le[:, None])
    cor[faixa_w] = C0
    cor[faixa_e] = S2
    cor[faixa_w & (kw == 1)] = K1
    cor[faixa_e & (ke == 1)] = K1
    sel = chao & (kw == lw[:, None] + 1) & (bay < 0.5)
    cor[sel] = C0
    sel = chao & (ke == le[:, None] + 1) & (bay < 0.5)
    cor[sel] = S2
    livre = chao & ~faixa_w & ~faixa_e & (d_in > 5) & (k > ESP_LAJE + PAREDE + 4)

    # --- entulho (revisão v3): poucos MONTES de pedras (3 a 4 nos fossos grandes, 1 a 2 nos pequenos), cada um com
    # uma pedra grande no meio e 4 a 7 menores encostadas em volta, sombra de 1 tom (um degrau do chão abaixo)
    # embaixo-direita do conjunto; o resto do chão fica liso. Pedras em 2 tons (claro em cima-esquerda, escuro
    # embaixo-direita) com contorno escuro (não preto); quanto mais longe da luz do fundo, mais o tom claro é comido
    # pelo chão, até a pedra sumir no escuro
    def pedra(cx_p, cy_p, raio, uniao):
        forma, fx0, fy0 = _poligono(rng, raio)
        fh, fw = forma.shape
        ya_, xa_ = cy_p + fy0, cx_p + fx0
        if ya_ < 1 or xa_ < 1 or ya_ + fh + 1 >= h or xa_ + fw + 1 >= w:
            return False
        if not livre[ya_:ya_ + fh, xa_:xa_ + fw][forma].all():
            return False
        Lc = float(L[cy_p, cx_p])
        p2 = min(1.0, Lc * 1.7)              # quanto do tom claro sobrevive
        p1 = min(1.0, Lc * 2.4 + 0.05)       # tom escuro
        p0 = min(1.0, Lc * 2.8 + 0.12)       # contorno
        borda_p = forma & ~(np.roll(forma, 1, 0) & np.roll(forma, -1, 0) & np.roll(forma, 1, 1) & np.roll(forma, -1, 1))
        corte = (rng.random() - 0.3) * raio * 0.5
        fyy, fxx = np.mgrid[0:fh, 0:fw].astype(np.float32)
        claro = forma & ~borda_p & ((fxx + fx0) * 0.8 + (fyy + fy0) < corte)
        escuro = forma & ~borda_p & ~claro
        sub = (slice(ya_, ya_ + fh), slice(xa_, xa_ + fw))
        b = bay[sub]
        cor_sub = cor[sub]
        cor_sub[claro & (b < p2)] = R2
        cor_sub[escuro & (b < p1)] = R1
        cor_sub[borda_p & (b < p0)] = R0
        uniao[sub] |= forma
        return True

    def monte(cx_m, cy_m):
        """Pedra grande no centro, menores encostadas em volta (sobrepondo um pouco a grande), sombra do conjunto."""
        uniao = np.zeros((h, w), dtype=bool)
        r0 = rng.randint(11, 14)
        if not pedra(cx_m, cy_m, r0, uniao):
            return None
        n = rng.randint(5, 7)
        ang = rng.random() * 2.0 * math.pi
        for _ in range(n):
            ang += 2.0 * math.pi / n * (0.7 + 0.6 * rng.random())
            r = rng.randint(4, 7)
            dist = r0 * 0.9 + r * 0.5
            px = cx_m + int(round(math.cos(ang) * dist * 1.3))
            py = cy_m + int(round(math.sin(ang) * dist * 0.75))
            pedra(px, py, r, uniao)
        # sombra do conjunto: 1 tom só (B0, o chão mais escuro), colada embaixo e à direita do monte (3 px), só no
        # chão livre, por dither conforme a luz (longe da luz o chão já é B0 e a sombra some junto)
        somb = np.zeros_like(uniao)
        for dy in range(0, 4):
            for dx in range(0, 4):
                if dx + dy and dx + dy <= 5:
                    somb[dy:, dx:] |= uniao[:h - dy, :w - dx]
        somb &= ~uniao & livre
        Lc = float(L[cy_m, cx_m])
        sel = somb & (bay < min(1.0, Lc * 2.8 + 0.12) * 0.9)
        cor[sel] = B0
        return (cx_m, cy_m, r0, uniao)

    area = int(livre.sum())
    ys_l, xs_l = np.nonzero(livre)
    montes = []
    if len(ys_l):
        n_montes = max(1, min(4, 1 + area // 50000))
        # candidatos perto da luz do fundo (onde o monte aparece), afastados uns dos outros e da borda do chão livre
        for limiar in (0.4, 0.25, -1.0):
            cand = np.nonzero((L[ys_l, xs_l] > limiar) & (d_in[ys_l, xs_l] > 20))[0]
            tentativas = 0
            while len(montes) < n_montes and tentativas < 200 and len(cand):
                tentativas += 1
                i = int(cand[rng.randrange(len(cand))])
                mx, my = int(xs_l[i]), int(ys_l[i])
                if any(math.hypot(mx - mt[0], my - mt[1]) < 56 for mt in montes):
                    continue
                mt = monte(mx, my)
                if mt is not None:
                    montes.append(mt)
            if len(montes) >= n_montes:
                break
    # lascas miúdas: no máximo 5 por fosso, sempre encostadas em algum monte (1 a 2 px), somem longe da luz
    n_lascas = 0
    for (mx, my, r0, uniao) in montes:
        for _ in range(rng.randint(0, 2)):
            if n_lascas >= 5:
                break
            ang = rng.random() * 2.0 * math.pi
            dist = r0 + rng.randint(4, 9)
            x = mx + int(round(math.cos(ang) * dist * 1.3))
            y = my + int(round(math.sin(ang) * dist * 0.8))
            if not (0 <= y < h and 0 <= x + 1 < w) or not livre[y, x] or uniao[y, x]:
                continue
            if bay[y, x] < min(1.0, L[y, x] * 2.2 + 0.15):
                cor[y, x] = R1
                if livre[y, x + 1] and not uniao[y, x + 1] and rng.random() < 0.6:
                    cor[y, x + 1] = R0
                n_lascas += 1
    # contorno interno: o 1º pixel de dentro, onde não há parede nem laje, fecha o vazio em preto (K1)
    interno = m & (d_in <= 1.5) & ~parede & ~laje_face
    cor[interno] = K1
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[..., :3] = cor
    img[..., 3] = np.where(alfa, 255, 0)
    return Image.fromarray(img, "RGBA"), origem


# ---------------------------------------------------------------- ponte de tábuas
EXT = 10          # px que o tabuleiro avança sobre a margem de cada lado (assenta na terra)
ALT_POSTE = 15    # altura do poste do corrimão (px)
FUNDO_VIGA = 6    # espessura visível do tabuleiro (faixa escura abaixo da borda sul)
ZONA_DESGASTE = 14  # px de cada ponta do tabuleiro com desgaste

_MAIS_ESCURO = {W4: W2, W3: W1, W2: W1, W1: W0}   # mancha de uso: cada tom de madeira desce um ou dois degraus


def _tabuas(tela, u0, u1, v0, v1, rng, horiz):
    """Tabuleiro: tábuas de 9 a 12 px perpendiculares ao sentido da ponte, frestas escuras de 1 px, veio, nós e pregos.
    (u0..u1 ao longo da ponte, v0..v1 através; `horiz`: a ponte corre na horizontal da imagem)."""
    u = u0
    tons = [W2, W2, W3, W1, W2]
    while u <= u1:
        larg = rng.randint(9, 12)
        fim = min(u + larg - 1, u1)
        tom = tons[rng.randrange(len(tons))]
        luz = W4 if tom in (W3, W2) else W3
        for uu in range(u, fim + 1):
            for vv in range(v0, v1 + 1):
                x, y = (uu, vv) if horiz else (vv, uu)
                tela.put(x, y, tom)
        # fresta entre tábuas (no fim da tábua) e bordas claras/escuras da tábua
        for vv in range(v0, v1 + 1):
            x, y = (fim, vv) if horiz else (vv, fim)
            tela.put(x, y, W0)
        for uu in range(u, fim):
            for vv, c in ((v0, luz), (v1, W1)):
                x, y = (uu, vv) if horiz else (vv, uu)
                tela.put(x, y, c)
        # veio da madeira: tracinhos de 5 a 14 px na direção do comprimento da tábua, um tom abaixo
        for _ in range(rng.randint(1, 3)):
            uv = rng.randint(u + 1, max(u + 1, fim - 1))
            v_ini = rng.randint(v0 + 2, v1 - 8)
            for vv in range(v_ini, min(v_ini + rng.randint(5, 14), v1 - 1)):
                x, y = (uv, vv) if horiz else (vv, uv)
                tela.put(x, y, W1 if tom != W1 else W0)
        if rng.random() < 0.35:   # nó
            uv, vv = rng.randint(u + 2, max(u + 2, fim - 2)), rng.randint(v0 + 6, v1 - 6)
            x, y = (uv, vv) if horiz else (vv, uv)
            tela.put(x, y, W0)
            tela.put(x + 1, y, W1)
        # pregos nas duas pontas
        for vv in (v0 + 3, v1 - 3):
            x, y = (u + 2, vv) if horiz else (vv, u + 2)
            tela.put(x, y, I1)
        u = fim + 1


def _desgaste_h(tela, x0, x1, y_n, y_s, rng):
    """Desgaste da ponte horizontal: nas duas pontas do tabuleiro (ZONA_DESGASTE px), quinas lascadas, ponta esfiapada,
    pregos faltando, mancha escura de uso (dither) e pontinhos de poeira; no meio, 1 ou 2 tábuas rachadas."""
    for x_ini, sinal in ((x0, 1), (x1, -1)):
        # quinas: escadinha de 2 a 4 px arrancada em cada canto
        for y_c, dy in ((y_n, 1), (y_s, -1)):
            prof = rng.randint(2, 4)
            for i in range(prof):
                for j in range(prof - i):
                    tela.apaga(x_ini + sinal * i, y_c + dy * j)
        # ponta esfiapada: na coluna da ponta, pixels arrancados, escurecidos ou uma farpa
        for y in range(y_n + 4, y_s - 3):
            r = rng.random()
            if r < 0.16:
                tela.apaga(x_ini, y)
            elif r < 0.30:
                tela.put(x_ini, y, W0)
            elif r < 0.36:
                tela.put(x_ini + sinal, y, W0)
        # mancha de uso: cada tom de madeira desce por dither, mais forte na ponta
        for i in range(ZONA_DESGASTE):
            p = 0.5 * (1.0 - i / float(ZONA_DESGASTE)) ** 1.5
            x = x_ini + sinal * i
            for y in range(y_n, y_s + 1):
                c = tela.get(x, y)
                if c is None:
                    continue
                if c == I1:
                    if rng.random() < 0.5:                        # prego faltando: só o furo
                        tela.put(x, y, W0)
                elif c in _MAIS_ESCURO and BAYER[y % 4, x % 4] < p:
                    tela.put(x, y, _MAIS_ESCURO[c])
        # poeira: pontinhos claros soltos sobre as tábuas
        for _ in range(rng.randint(5, 8)):
            x = x_ini + sinal * rng.randint(1, ZONA_DESGASTE - 1)
            y = rng.randint(y_n + 4, y_s - 4)
            if tela.get(x, y) in (W1, W2, W3):
                tela.put(x, y, S8)
    # tábuas rachadas no meio: passeio vertical de 8 a 16 px em W0, com um fio claro ao lado aqui e ali
    for _ in range(rng.randint(1, 2)):
        x = rng.randint(x0 + ZONA_DESGASTE + 6, x1 - ZONA_DESGASTE - 6)
        y = rng.randint(y_n + 4, y_s - 20)
        for _j in range(rng.randint(8, 16)):
            if tela.get(x, y) in (W1, W2, W3, W4):
                tela.put(x, y, W0)
                if rng.random() < 0.25 and tela.get(x + 1, y) in (W1, W2):
                    tela.put(x + 1, y, W3)
            x += rng.choice([-1, 0, 0, 0, 1])
            y += 1


def _sombra(tela, x_a, x_b, y_a, y_b):
    """Sombra projetada de 1 tom (preto, alfa fixo SOMBRA_ALFA) no retângulo dado, só onde a tela está vazia."""
    for y in range(max(y_a, 0), min(y_b, tela.h - 1) + 1):
        for x in range(max(x_a, 0), min(x_b, tela.w - 1) + 1):
            if tela.a[y, x, 3] == 0:
                tela.a[y, x] = (0, 0, 0, SOMBRA_ALFA)


def _poste(tela, x, y_base, alt, larg=5):
    """Poste de madeira em pé: base em (x, y_base), sobe `alt` px; luz à esquerda, sombra à direita, topo claro."""
    for yy in range(y_base - alt, y_base + 1):
        for xx in range(x - larg // 2, x + larg // 2 + 1):
            tela.put(xx, yy, W2)
        tela.put(x - larg // 2, yy, W3)
        tela.put(x + larg // 2, yy, W1)
    for xx in range(x - larg // 2, x + larg // 2 + 1):
        tela.put(xx, y_base - alt, W4)


def _viga_h(tela, x0, x1, y, esp=3):
    """Viga horizontal do corrimão: topo claro, meio, base escura."""
    for xx in range(x0, x1 + 1):
        tela.put(xx, y, W3)
        for k in range(1, esp - 1):
            tela.put(xx, y + k, W2)
        tela.put(xx, y + esp - 1, W1)


def _viga_v(tela, x, y0, y1, esp=3):
    for yy in range(y0, y1 + 1):
        tela.put(x, yy, W3)
        for k in range(1, esp - 1):
            tela.put(x + k, yy, W2)
        tela.put(x + esp - 1, yy, W1)


def pintar_ponte(celulas, semente=1):
    """Ponte de tábuas sobre um fosso. `celulas`: as células `=` (um retângulo). A ponte corre no sentido mais longo.
    O PNG leva a sombra projetada no fosso (alfa parcial fixo), deslocada para baixo-direita; o resto é alfa binário."""
    import random
    rng = random.Random(semente)
    xs = [c[0] for c in celulas]
    ys = [c[1] for c in celulas]
    cx0, cx1, cy0, cy1 = min(xs), max(xs), min(ys), max(ys)
    cw, ch = cx1 - cx0 + 1, cy1 - cy0 + 1
    horiz = cw >= ch
    X0, Y0 = cx0 * TILE, cy0 * TILE
    if horiz:
        comp = cw * TILE + 2 * EXT
        larg = ch * TILE
        W, H = comp + 4, larg + ALT_POSTE + FUNDO_VIGA + 14 + SOMBRA_DESL + 1
        tela = _Tela(W, H)
        ox, oy = X0 - EXT - 2, Y0 - ALT_POSTE - 3
        d0 = 2                                   # x do começo do tabuleiro na imagem
        y_n = ALT_POSTE + 3                      # y da borda norte do tabuleiro
        y_s = y_n + larg - 1                     # y da borda sul
        # postes e viga do corrimão norte (atrás do tabuleiro)
        passo = 26
        n_postes = max(2, round(comp / passo) + 1)
        px = [d0 + 3 + round(i * (comp - 7) / (n_postes - 1)) for i in range(n_postes)]
        for x in px:
            _poste(tela, x, y_n + 3, ALT_POSTE)
        _viga_h(tela, d0 + 1, d0 + comp - 2, y_n + 3 - ALT_POSTE + 3, 3)
        _viga_h(tela, d0 + 1, d0 + comp - 2, y_n + 3 - ALT_POSTE // 2, 2)
        # lateral (espessura) do tabuleiro, abaixo da borda sul, e pés de apoio
        for x in range(d0, d0 + comp):
            for k in range(1, FUNDO_VIGA + 1):
                tela.put(x, y_s + k, W1 if k < FUNDO_VIGA else W0)
        pes = px[1:-1:2] or px[1:2]
        for x in pes:
            for k in range(FUNDO_VIGA + 1, FUNDO_VIGA + 9):
                for dx in (-1, 0, 1):
                    tela.put(x + dx, y_s + k, W0 if k == FUNDO_VIGA + 8 else W1)
        # tabuleiro
        _tabuas(tela, d0, d0 + comp - 1, y_n, y_s, rng, True)
        # vigas laterais do tabuleiro (longarinas) por cima das tábuas
        for x in range(d0, d0 + comp):
            for k in range(0, 3):
                tela.put(x, y_n + k, W2 if k else W3)
                tela.put(x, y_s - k, W1 if k else W0)
        _desgaste_h(tela, d0, d0 + comp - 1, y_n, y_s, rng)
        # corrimão sul, na frente
        for x in px:
            _poste(tela, x, y_s - 1, ALT_POSTE)
        _viga_h(tela, d0 + 1, d0 + comp - 2, y_s - 1 - ALT_POSTE + 3, 3)
        _viga_h(tela, d0 + 1, d0 + comp - 2, y_s - 1 - ALT_POSTE // 2, 2)
        tela.contorno()
        # sombra projetada no fosso: tabuleiro (com a espessura) e pés, deslocados para baixo-direita, só no vão do fosso
        xa, xb = d0 + EXT + 6, d0 + comp - 1 - EXT - 6
        _sombra(tela, xa, xb, y_n + SOMBRA_DESL, y_s + FUNDO_VIGA + SOMBRA_DESL)
        for x in pes:
            _sombra(tela, max(xa, x - 1 + SOMBRA_DESL), min(xb, x + 1 + SOMBRA_DESL),
                    y_s + FUNDO_VIGA + 1 + SOMBRA_DESL, y_s + FUNDO_VIGA + 8 + SOMBRA_DESL)
    else:
        comp = ch * TILE + 2 * EXT
        larg = cw * TILE
        W, H = larg + 2 * 4 + 6 + SOMBRA_DESL + 1, comp + ALT_POSTE + FUNDO_VIGA + 10
        tela = _Tela(W, H)
        ox, oy = X0 - 7, Y0 - EXT - ALT_POSTE - 3
        d0 = ALT_POSTE + 3                      # y do começo do tabuleiro (norte)
        x_w = 7
        x_e = x_w + larg - 1
        passo = 26
        n_postes = max(2, round(comp / passo) + 1)
        py = [d0 + 4 + round(i * (comp - 8) / (n_postes - 1)) for i in range(n_postes)]
        # lateral (espessura) sob a borda sul do tabuleiro
        for x in range(x_w, x_e + 1):
            for k in range(1, FUNDO_VIGA + 1):
                tela.put(x, d0 + comp - 1 + k, W1 if k < FUNDO_VIGA else W0)
        _tabuas(tela, d0, d0 + comp - 1, x_w, x_e, rng, False)
        for y in range(d0, d0 + comp):
            for k in range(0, 3):
                tela.put(x_w + k, y, W2 if k else W3)
                tela.put(x_e - k, y, W1 if k else W0)
        for xl in (x_w + 2, x_e - 2):
            for y in py:
                _poste(tela, xl, y, ALT_POSTE)
            _viga_v(tela, xl - 1, py[0] - ALT_POSTE + 1, py[-1] - ALT_POSTE + 4, 3)
        tela.contorno()
        ya, yb = d0 + EXT + 6, d0 + comp - 1 - EXT - 6
        _sombra(tela, x_w + SOMBRA_DESL, x_e + SOMBRA_DESL, ya, yb)
    return tela.imagem(), (ox, oy)


class _Tela:
    """Raster RGBA de alfa binário (o mesmo contrato da Tela de montar_marcos.py, sem depender dele). A única exceção
    ao alfa binário é `_sombra`, que escreve direto em `a`."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.a = np.zeros((h, w, 4), dtype=np.uint8)

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = (c[0], c[1], c[2], 255)

    def get(self, x, y):
        """Cor (r, g, b) do pixel, ou None se vazio ou fora da tela."""
        if 0 <= x < self.w and 0 <= y < self.h and self.a[y, x, 3] > 0:
            return (int(self.a[y, x, 0]), int(self.a[y, x, 1]), int(self.a[y, x, 2]))
        return None

    def apaga(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = (0, 0, 0, 0)

    def contorno(self, cor=K0):
        op = self.a[..., 3] > 0
        viz = np.zeros_like(op)
        viz[1:, :] |= op[:-1, :]
        viz[:-1, :] |= op[1:, :]
        viz[:, 1:] |= op[:, :-1]
        viz[:, :-1] |= op[:, 1:]
        borda = viz & ~op
        self.a[borda] = (cor[0], cor[1], cor[2], 255)

    def imagem(self):
        return Image.fromarray(self.a, "RGBA")


def main():
    args = sys.argv[1:]
    if "--previa" in args:
        pasta = args[args.index("--previa") + 1]
        os.makedirs(pasta, exist_ok=True)
        formas = {
            "fosso_a": {(x, y) for x in range(0, 6) for y in range(0, 3)},
            "fosso_b": {(x, y) for x in range(0, 4) for y in range(0, 2)} | {(x, y) for x in range(2, 4) for y in range(2, 5)},
        }
        for nome, cel in formas.items():
            im, org = pintar_fosso(cel, semente=3)
            im.save(os.path.join(pasta, nome + ".png"))
            print(nome, im.size, org)
        # ponte horizontal sobre o fosso_a (linha 1, colunas 0..5 + margens) e ponte vertical sobre o fosso_b
        im, org = pintar_ponte({(x, 1) for x in range(0, 6)}, semente=5)
        im.save(os.path.join(pasta, "ponte_h.png"))
        print("ponte_h", im.size, org)
        im, org = pintar_ponte({(3, y) for y in range(2, 5)}, semente=6)
        im.save(os.path.join(pasta, "ponte_v.png"))
        print("ponte_v", im.size, org)


if __name__ == "__main__":
    main()
