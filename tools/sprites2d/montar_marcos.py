#!/usr/bin/env python3
"""Monta por código os marcos da estrada da Cripta, na mesma linguagem dos props pixelados:
grade de 1 px de mundo, alfa binário, contorno preto de 1 px, paleta curta, luz de cima-esquerda.

Saídas (em godot/art2d/props/):
  arco_portal.png  verga de pedra do portal do chefe, para ir sobre dois pillar_tall com centros a 256 px
                   (pivô = centro da borda de baixo = linha do chão dos pilares)
  arco_ruina.png   pedaço quebrado da verga, apoiado só no pilar da esquerda (mesmo pivô/altura)
  bau_bolsao.png   baú de recompensa do bolsão, 34x30, pivô na base

Uso: python3 -I tools/sprites2d/montar_marcos.py [--previas DIR]
Só precisa de PIL e numpy. Lê os PNG dos props existentes (pillar_tall, skull_single...) para medir e emprestar
as caveiras; nada de IA generativa.
"""
import os
import random
import sys

import numpy as np
from PIL import Image

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
PROPS = os.path.join(R, "godot", "art2d", "props")

# ---------------------------------------------------------------- paleta (tons dos pilares existentes)
K0 = (0, 0, 0)          # contorno
K1 = (21, 16, 25)       # linha interna / sombra funda
S1 = (52, 36, 51)       # pedra: sombra mais funda (roxo quente)
S2 = (53, 51, 63)       # pedra: escuro frio (rachaduras, ferro escuro)
S3 = (62, 61, 72)       # pedra: sombra fria
S4 = (72, 59, 62)       # pedra: escuro quente
S5 = (87, 71, 67)       # pedra: base da face frontal
S6 = (119, 101, 100)    # pedra: face frontal clara
S7 = (136, 111, 104)    # pedra: face de cima em sombra / sujeira
S8 = (159, 133, 119)    # pedra: face de cima
S9 = (184, 154, 127)    # pedra: aresta iluminada
G1 = (114, 76, 52)      # ouro escuro
G2 = (157, 107, 68)     # ouro sombra
G3 = (194, 160, 115)    # ouro base
G4 = (228, 199, 144)    # ouro claro
B1 = (233, 182, 127)    # osso claro
B2 = (253, 240, 219)    # osso brilho
I1 = (75, 69, 76)       # ferro claro
PALETA_PEDRA = [K0, K1, S1, S2, S3, S4, S5, S6, S7, S8, S9, G1, G2, G3, G4, B1, B2, I1]


class Tela:
    """Raster RGBA com alfa binário."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.a = np.zeros((h, w, 4), dtype=np.uint8)

    def dentro(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def put(self, x, y, c):
        if self.dentro(x, y):
            self.a[y, x] = (c[0], c[1], c[2], 255)

    def apagar(self, x, y):
        if self.dentro(x, y):
            self.a[y, x] = 0

    def opaco(self, x, y):
        return self.dentro(x, y) and self.a[y, x, 3] > 0

    def cor(self, x, y):
        return tuple(int(v) for v in self.a[y, x, :3])

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, c)

    def hline(self, x0, x1, y, c):
        for x in range(x0, x1 + 1):
            self.put(x, y, c)

    def vline(self, x, y0, y1, c):
        for y in range(y0, y1 + 1):
            self.put(x, y, c)

    def colar(self, outra, ox, oy):
        """Cola outra Tela/array RGBA (só pixels opacos) em (ox, oy)."""
        arr = outra.a if isinstance(outra, Tela) else outra
        h, w = arr.shape[:2]
        for y in range(h):
            for x in range(w):
                if arr[y, x, 3] > 0:
                    self.put(ox + x, oy + y, tuple(int(v) for v in arr[y, x, :3]))

    def contorno(self, cor=K0, mascara=None):
        """Pixel transparente com vizinho opaco (4 direções) vira contorno. `mascara(x, y)` limita a área."""
        a = self.a
        op = a[..., 3] > 0
        viz = np.zeros_like(op)
        viz[1:, :] |= op[:-1, :]
        viz[:-1, :] |= op[1:, :]
        viz[:, 1:] |= op[:, :-1]
        viz[:, :-1] |= op[:, 1:]
        borda = viz & ~op
        ys, xs = np.where(borda)
        for x, y in zip(xs, ys):
            if mascara is None or mascara(int(x), int(y)):
                a[y, x] = (cor[0], cor[1], cor[2], 255)

    def encaixar_paleta(self, paleta):
        pal = np.array(paleta, dtype=np.int32)
        op = self.a[..., 3] > 0
        rgb = self.a[..., :3].astype(np.int32)
        d = ((rgb[..., None, :] - pal[None, None, :, :]) ** 2).sum(-1)
        idx = d.argmin(-1)
        novo = pal[idx].astype(np.uint8)
        self.a[..., :3] = np.where(op[..., None], novo, 0)

    def imagem(self):
        return Image.fromarray(self.a, "RGBA")

    def bbox(self):
        ys, xs = np.where(self.a[..., 3] > 0)
        return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def pintar_grupo(t, x, y, cor, rng, n, mascara):
    """Mancha irregular: passeio aleatório de n pixels a partir de (x, y), só onde `mascara` deixa."""
    cx, cy = x, y
    for _ in range(n):
        if mascara(cx, cy):
            t.put(cx, cy, cor)
        cx += rng.choice((-1, 0, 1, 1, 0))
        cy += rng.choice((-1, 0, 0, 1))


def rachadura(t, x, y, comp, rng, cor, cor_luz=None, mascara=None, dy_pref=1):
    """Linha quebrada de 1 px descendo (dy_pref=1) com desvios laterais; opcional pixel de luz à direita."""
    cx, cy = x, y
    for i in range(comp):
        if mascara is None or mascara(cx, cy):
            t.put(cx, cy, cor)
            if cor_luz is not None and rng.random() < 0.45 and (mascara is None or mascara(cx + 1, cy)):
                t.put(cx + 1, cy, cor_luz)
        passo = rng.random()
        if passo < 0.3:
            cx -= 1
        elif passo < 0.6:
            cx += 1
        if rng.random() < 0.8:
            cy += dy_pref


# ---------------------------------------------------------------- verga
TOPO = 10      # face de cima visível
FRENTE = 28    # face frontal


def desenhar_viga(t, x0, x1, ty0, rng, cx_chave=None, aneis=(), glifos=True):
    """Viga de pedra maciça em 3/4 entre x0..x1 (inclusive), face de cima a partir de ty0.
    Retorna (fy0, fy1) = linhas da face frontal."""
    fy0 = ty0 + TOPO
    fy1 = fy0 + FRENTE - 1
    face_cima = lambda x, y: x0 <= x <= x1 and ty0 <= y < fy0
    face_frente = lambda x, y: x0 <= x <= x1 and fy0 <= y <= fy1

    # faces chapadas, com a fronteira das zonas de sombra irregular (nada de listras retas)
    t.rect(x0, ty0, x1, ty0, S7)
    t.rect(x0, ty0 + 1, x1, fy0 - 2, S8)
    t.rect(x0, fy0 - 1, x1, fy0 - 1, S9)
    t.rect(x0, fy0, x1, fy0, S6)
    t.rect(x0, fy0 + 1, x1, fy1, S5)
    lim = fy1 - 5
    for x in range(x0, x1 + 1):
        if rng.random() < 0.25:
            lim = max(fy1 - 8, min(fy1 - 3, lim + rng.choice((-1, 1))))
        t.vline(x, lim, fy1 - 2, S4)
        t.vline(x, fy1 - 1, fy1, S3)
        if rng.random() < 0.3:
            t.put(x, fy1 - 2 + (1 if rng.random() < 0.5 else 0), S3)
    # grão da pedra: pontos soltos, claros perto do alto e escuros perto da base
    for _ in range((x1 - x0) * 2 // 3):
        x = rng.randint(x0, x1)
        y = rng.randint(fy0 + 1, fy1 - 3)
        if t.cor(x, y) == S5:
            t.put(x, y, S6 if rng.random() < 0.55 - 0.4 * (y - fy0) / FRENTE else S4)
        elif t.cor(x, y) == S4 and rng.random() < 0.4:
            t.put(x, y, S5)
    for _ in range((x1 - x0) // 4):
        x = rng.randint(x0, x1)
        y = rng.randint(ty0 + 1, fy0 - 2)
        if t.cor(x, y) == S8:
            t.put(x, y, S9 if rng.random() < 0.4 else S7)

    # blocos grandes: juntas verticais irregulares (escura + luz à direita), continuam na face de cima
    juntas = []
    x = x0 + rng.randint(34, 50)
    while x < x1 - 30:
        if cx_chave is None or abs(x - cx_chave) > 24:
            juntas.append(x)
        x += rng.randint(44, 72)
    for jx in juntas:
        desvio = 0
        for y in range(ty0, fy1 + 1):
            if y in (fy0 + 9, fy0 + 19) and rng.random() < 0.6:
                desvio += rng.choice((-1, 1))
            xx = jx + desvio
            if y < fy0:
                t.put(xx, y, S7 if y > ty0 else S7)
                if y == fy0 - 1:
                    t.put(xx, y, S7)
            else:
                t.put(xx, y, S2 if y < fy1 - 1 else K1)
                if fy0 < y < fy1 - 5:
                    t.put(xx + 1, y, S6)
    # variação de tom por bloco (um bloco mais claro, outro mais sujo)
    limites = [x0] + juntas + [x1 + 1]
    for i in range(len(limites) - 1):
        bx0, bx1 = limites[i], limites[i + 1] - 1
        if cx_chave is not None and bx0 <= cx_chave <= bx1:
            continue
        so_base = lambda px, py: bx0 + 1 <= px <= bx1 - 1 and fy0 + 1 <= py <= fy1 - 3 and t.cor(px, py) == S5
        # manchas de desgaste claras (alto) e de umidade escuras (baixo), em formas irregulares
        for _ in range(rng.randint(1, 3)):
            pintar_grupo(t, rng.randint(bx0 + 2, max(bx0 + 2, bx1 - 2)), fy0 + rng.randint(1, 6), S6, rng,
                         rng.randint(8, 26), so_base)
        for _ in range(rng.randint(1, 2)):
            pintar_grupo(t, rng.randint(bx0 + 2, max(bx0 + 2, bx1 - 2)), fy1 - rng.randint(7, 12), S4, rng,
                         rng.randint(8, 22), so_base)
        # um lascado maior numa aresta do bloco, às vezes
        if rng.random() < 0.5 and bx1 - bx0 > 20:
            lx = rng.randint(bx0 + 4, bx1 - 6)
            for dy in range(3):
                for dx in range(3 - dy):
                    if so_base(lx + dx, fy0 + 1 + dy):
                        t.put(lx + dx, fy0 + 1 + dy, S4)
                if so_base(lx + 3 - dy, fy0 + 1 + dy):
                    t.put(lx + 3 - dy, fy0 + 1 + dy, S6)

    # faixa dourada baixa (cornija) com falhas
    by = fy1 - 7
    for x in range(x0 + 3, x1 - 2):
        if any(abs(x - a) < 4 for a in aneis):
            continue
        falha = rng.random() < 0.03
        if falha:
            continue
        t.put(x, by, G4)
        t.put(x, by + 1, G3)
        t.put(x, by + 2, G2)
    # ranhuras na faixa (pedra entre placas de ouro)
    for x in range(x0 + 14, x1 - 8, rng.randint(17, 26)):
        if any(abs(x - a) < 6 for a in aneis):
            continue
        t.put(x, by, G2)
        t.put(x, by + 1, G1)
        t.put(x, by + 2, G1)

    # anéis dourados verticais (como as pontas da coluna caída)
    for ax in aneis:
        for y in range(ty0, fy1 + 1):
            if y < fy0:
                t.put(ax - 1, y, G4)
                t.put(ax, y, G4)
                t.put(ax + 1, y, G3)
                t.put(ax + 2, y, G3)
                t.put(ax - 2, y, G3)
            else:
                esc = y >= fy1 - 3
                t.put(ax - 2, y, G3 if not esc else G2)
                t.put(ax - 1, y, G4 if not esc else G3)
                t.put(ax, y, G3 if not esc else G2)
                t.put(ax + 1, y, G2 if not esc else G1)
                t.put(ax + 2, y, G1)
        # pregos/encaixes do anel
        for y in (fy0 + 5, fy0 + 14, fy0 + 23):
            t.put(ax, y, G1)
            t.put(ax - 1, y, G2)

    # glifos pequenos gravados na face frontal
    if glifos:
        formas = [
            ["X.X", ".X.", "X.X"],
            [".X.", "XXX", ".X.", ".X."],
            ["XXX", "X..", "XXX"],
            [".X.", "X.X", ".X.", "X.X"],
            ["X.X", "XXX", "..X"],
        ]
        gx = x0 + rng.randint(10, 18)
        while gx < x1 - 10:
            ok = all(abs(gx - a) > 9 for a in aneis) and (cx_chave is None or abs(gx - cx_chave) > 22)
            ok = ok and all(abs(gx - j) > 6 for j in juntas)
            if ok:
                f = rng.choice(formas)
                gy = fy0 + 5 + rng.randint(0, 6)
                for dy, linha in enumerate(f):
                    for dx, ch in enumerate(linha):
                        if ch == "X":
                            c = G4 if (dx == 0 or dy == 0) and rng.random() < 0.5 else G3
                            if dy == len(f) - 1:
                                c = G2
                            t.put(gx + dx, gy + dy, c)
            gx += rng.randint(16, 28)

    # pedra-chave central
    if cx_chave is not None:
        desenhar_chave(t, cx_chave, ty0, fy0, fy1, rng)

    # rachaduras
    for _ in range(rng.randint(4, 6)):
        x = rng.randint(x0 + 4, x1 - 4)
        if cx_chave is not None and abs(x - cx_chave) < 18:
            continue
        if any(abs(x - a) < 5 for a in aneis):
            continue
        if rng.random() < 0.5:
            rachadura(t, x, fy0 + rng.randint(0, 2), rng.randint(7, 15), rng, S2, S6,
                      mascara=lambda px, py: face_frente(px, py) and t.cor(px, py) in (S5, S6, S4))
        else:
            rachadura(t, x, fy1 - 8 - rng.randint(0, 6), rng.randint(5, 10), rng, S2, None,
                      mascara=lambda px, py: face_frente(px, py) and t.cor(px, py) in (S5, S6, S4), dy_pref=-1)
    for _ in range(rng.randint(2, 3)):
        x = rng.randint(x0 + 6, x1 - 6)
        if cx_chave is not None and abs(x - cx_chave) < 18:
            continue
        rachadura(t, x, ty0 + 1, rng.randint(4, 8), rng, S5, None,
                  mascara=lambda px, py: face_cima(px, py) and t.cor(px, py) in (S8, S7, S9))

    # sujeira: face de cima com manchas escuras; face frontal com escorrimento perto da base
    for _ in range(rng.randint(5, 8)):
        x = rng.randint(x0 + 3, x1 - 3)
        pintar_grupo(t, x, ty0 + rng.randint(1, 6), S7, rng, rng.randint(6, 16),
                     lambda px, py: face_cima(px, py) and t.cor(px, py) == S8)
    for _ in range(rng.randint(3, 5)):
        x = rng.randint(x0 + 3, x1 - 3)
        pintar_grupo(t, x, ty0 + rng.randint(2, 7), S9, rng, rng.randint(3, 7),
                     lambda px, py: face_cima(px, py) and t.cor(px, py) == S8)
    for _ in range(rng.randint(4, 7)):
        x = rng.randint(x0 + 2, x1 - 2)
        if any(abs(x - a) < 4 for a in aneis):
            continue
        for dy in range(rng.randint(2, 5)):
            y = fy1 - 6 - dy
            if t.cor(x, y) in (S5, S6):
                t.put(x, y, S4)

    return fy0, fy1


def desenhar_chave(t, cx, ty0, fy0, fy1, rng):
    """Pedra-chave: bloco trapezoidal mais claro que sobressai da viga, com glifo dourado grande."""
    meia_cima, meia_baixo = 15, 11
    yk0, yk1 = fy0 - 2, fy1 + 3
    tk0 = ty0 - 1
    for y in range(tk0, yk1 + 1):
        frac = max(0.0, min(1.0, (y - fy0) / float(fy1 - fy0)))
        meia = int(round(meia_cima + (meia_baixo - meia_cima) * frac))
        for x in range(cx - meia, cx + meia + 1):
            if y < yk0:              # face de cima da chave
                t.put(x, y, S9 if y == yk0 - 1 else S8)
            elif y == yk0:
                t.put(x, y, S7)
            elif y >= yk1 - 2:
                t.put(x, y, S3 if y == yk1 else S4)
            else:
                t.put(x, y, S6)
        # juntas laterais: escura à esquerda (parede em sombra), e luz na aresta direita do bloco
        if y >= yk0:
            t.put(cx - meia - 1, y, S2 if y < yk1 - 1 else K1)
            t.put(cx - meia, y, S5)
            t.put(cx + meia + 1, y, S2 if y < yk1 - 1 else K1)
            t.put(cx + meia, y, S4)
        else:
            t.put(cx - meia - 1, y, S7)
            t.put(cx + meia + 1, y, S7)
    # cinzelado: a chave tem bisel (aresta de cima clara, aresta de baixo escura) e grão
    for x in range(cx - meia_cima + 1, cx + meia_cima):
        if t.cor(x, yk0 + 1) == S6:
            t.put(x, yk0 + 1, S8)
    for _ in range(14):
        x, y = cx + rng.randint(-meia_baixo + 1, meia_baixo - 1), rng.randint(yk0 + 3, yk1 - 3)
        if t.cor(x, y) == S6:
            t.put(x, y, S5 if rng.random() < 0.6 else S8)
    # glifo: losango duplo com cruz, 17x17, gravado (sombra escura embaixo/direita de cada traço)
    gy = (yk0 + yk1) // 2 + 1
    raio = 8
    for d in range(-raio, raio + 1):
        for s in (-1, 1):
            x = cx + d
            y = gy + s * (raio - abs(d))
            c = G4 if (s == -1 and d <= 0) else (G2 if s == 1 and d > 0 else G3)
            t.put(x, y, c)
            if s == 1 and t.cor(x, y + 1) in (S6, S5, S8):
                t.put(x, y + 1, S4)
    r2 = 4
    for d in range(-r2, r2 + 1):
        for s in (-1, 1):
            t.put(cx + d, gy + s * (r2 - abs(d)), G3 if s == -1 else G2)
    for d in range(-2, 3):
        t.put(cx + d, gy, G4 if d <= 0 else G3)
        t.put(cx, gy + d, G4 if d < 0 else G3)
    t.put(cx, gy, G4)
    for d in (-6, 6):
        t.put(cx + d, gy, G3)
        t.put(cx, gy + d, G3 if d < 0 else G2)
    # lascas pequenas na chave
    rachadura(t, cx + 12, yk0 + 2, 6, rng, S4, S8,
              mascara=lambda px, py: t.cor(px, py) in (S6, S8))
    rachadura(t, cx - 11, yk1 - 9, 5, rng, S4, None,
              mascara=lambda px, py: t.cor(px, py) == S6, dy_pref=-1)
    for dy in range(3):   # canto inferior esquerdo lascado
        for dx in range(3 - dy):
            t.apagar(cx - meia_baixo - 1 + dx, yk1 - dy)
        t.put(cx - meia_baixo - 1 + 3 - dy, yk1 - dy, S6)


def lascar_ponta(t, x_ponta, lado, ty0, fy0, fy1, rng, tam_cima=4, tam_baixo=6):
    """Quebra as quinas de uma ponta da viga (lado=-1 esquerda, +1 direita) e pinta a face fresca."""
    for y in range(ty0, fy0):               # quina de cima: triângulo
        prof = tam_cima - (y - ty0) + rng.choice((0, 0, 1))
        for i in range(prof):
            t.apagar(x_ponta + lado * i, y)
        if prof > 0:
            t.put(x_ponta + lado * prof, y, S9 if y > ty0 else S7)
    for y in range(fy1 - tam_baixo, fy1 + 1):  # quina de baixo: entalhe irregular
        prof = (y - (fy1 - tam_baixo)) + rng.choice((-1, 0, 0, 1))
        for i in range(max(0, prof)):
            t.apagar(x_ponta + lado * i, y)
        if prof > 0:
            t.put(x_ponta + lado * prof, y, S6)
    # mordidas na aresta frontal da ponta
    for _ in range(rng.randint(1, 2)):
        y = rng.randint(fy0 + 3, fy1 - 10)
        prof = rng.randint(1, 2)
        for dy in range(rng.randint(2, 3)):
            for i in range(prof):
                t.apagar(x_ponta + lado * i, y + dy)
            t.put(x_ponta + lado * prof, y + dy, S6)


def mordidas_baixo(t, x0, x1, fy1, rng, n, evitar=()):
    """Pequenas falhas na aresta de baixo e na aresta de trás da face de cima."""
    for _ in range(n):
        x = rng.randint(x0 + 6, x1 - 8)
        if any(abs(x - e) < 10 for e in evitar):
            continue
        larg = rng.randint(3, 6)
        alt = rng.randint(1, 2)
        for dx in range(larg):
            prof = alt if 0 < dx < larg - 1 else 1
            for dy in range(prof):
                t.apagar(x + dx, fy1 - dy)
            t.put(x + dx, fy1 - prof, S4)


def mordidas_cima(t, x0, x1, ty0, rng, n, evitar=()):
    for _ in range(n):
        x = rng.randint(x0 + 6, x1 - 8)
        if any(abs(x - e) < 12 for e in evitar):
            continue
        larg = rng.randint(3, 7)
        for dx in range(larg):
            prof = 2 if 0 < dx < larg - 1 and rng.random() < 0.6 else 1
            for dy in range(prof):
                t.apagar(x + dx, ty0 + dy)
            t.put(x + dx, ty0 + prof, S7)


# ---------------------------------------------------------------- caveiras emprestadas
def recortar_caveira(caminho):
    """Maior componente conexo opaco do sprite (a caveira, sem os ossinhos soltos)."""
    im = np.array(Image.open(caminho).convert("RGBA"))
    op = im[..., 3] > 0
    h, w = op.shape
    rot = np.zeros((h, w), dtype=np.int32)
    comp = 0
    melhor = (0, None)
    for y in range(h):
        for x in range(w):
            if op[y, x] and rot[y, x] == 0:
                comp += 1
                pilha = [(x, y)]
                rot[y, x] = comp
                n = 0
                while pilha:
                    px, py = pilha.pop()
                    n += 1
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                        nx, ny = px + dx, py + dy
                        if 0 <= nx < w and 0 <= ny < h and op[ny, nx] and rot[ny, nx] == 0:
                            rot[ny, nx] = comp
                            pilha.append((nx, ny))
                if n > melhor[0]:
                    melhor = (n, comp)
    m = rot == melhor[1]
    ys, xs = np.where(m)
    rec = im[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy()
    rec[~m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]] = 0
    return rec


def recortar_regiao(caminho, x0, y0, x1, y1, paleta):
    """Recorta uma região (inclusive) de um sprite, fica com o maior componente, encaixa na paleta e recontorna."""
    im = np.array(Image.open(caminho).convert("RGBA"))[y0:y1 + 1, x0:x1 + 1].copy()
    # tira o contorno antigo (vai ser refeito) para o componente ser só o miolo
    lum = 0.3 * im[..., 0].astype(int) + 0.59 * im[..., 1].astype(int) + 0.11 * im[..., 2].astype(int)
    im[(lum < 20) & (im[..., 3] > 0)] = 0
    tmp = Image.fromarray(im, "RGBA")
    op = im[..., 3] > 0
    h, w = op.shape
    rot = np.zeros((h, w), dtype=np.int32)
    comp, melhor = 0, (0, 0)
    for y in range(h):
        for x in range(w):
            if op[y, x] and rot[y, x] == 0:
                comp += 1
                pilha = [(x, y)]
                rot[y, x] = comp
                n = 0
                while pilha:
                    px, py = pilha.pop()
                    n += 1
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = px + dx, py + dy
                        if 0 <= nx < w and 0 <= ny < h and op[ny, nx] and rot[ny, nx] == 0:
                            rot[ny, nx] = comp
                            pilha.append((nx, ny))
                if n > melhor[0]:
                    melhor = (n, comp)
    im[rot != melhor[1]] = 0
    t = Tela(w + 2, h + 2)
    t.colar(im, 1, 1)
    t.encaixar_paleta(paleta)
    t.contorno()
    b = t.bbox()
    return t.a[b[1]:b[3] + 1, b[0]:b[2] + 1].copy()


def reduzir(arr, fator, paleta):
    """Reduz um sprite pixelado (BOX com alfa pré-multiplicado), alfa binário, encaixa na paleta e recontorna."""
    im = Image.fromarray(arr, "RGBA")
    w, h = im.size
    lw, lh = max(2, round(w * fator)), max(2, round(h * fator))
    a = im.getchannel("A")
    rgb = Image.composite(im.convert("RGB"), Image.new("RGB", im.size, (0, 0, 0)), a)
    pm = Image.merge("RGBA", (*rgb.split(), a)).resize((lw, lh), Image.BOX)
    p = np.array(pm).astype(np.float32)
    al = p[..., 3:4]
    rgbd = np.where(al > 0, p[..., :3] / np.maximum(al, 1) * 255, 0)
    # traços escuros internos (órbitas, nariz, dentes) não podem virar média: guardam-se por cobertura
    src = arr.astype(np.float32)
    lum = 0.3 * src[..., 0] + 0.59 * src[..., 1] + 0.11 * src[..., 2]
    escuro = ((lum < 60) & (src[..., 3] > 0)).astype(np.float32) * 255
    op = src[..., 3] > 0
    borda = np.zeros(op.shape, dtype=bool)   # pixels escuros que encostam no vazio = contorno antigo, não contam
    borda[1:, :] |= ~op[:-1, :]
    borda[:-1, :] |= ~op[1:, :]
    borda[:, 1:] |= ~op[:, :-1]
    borda[:, :-1] |= ~op[:, 1:]
    escuro_int = np.where(borda > 0, 0, escuro)
    cob = np.array(Image.fromarray(escuro_int.astype(np.uint8), "L").resize((lw, lh), Image.BOX)).astype(np.float32)
    claro = ((lum > 200) & (src[..., 3] > 0)).astype(np.float32) * 255
    cob_claro = np.array(Image.fromarray(claro.astype(np.uint8), "L").resize((lw, lh), Image.BOX)).astype(np.float32)
    out = Tela(lw + 2, lh + 2)
    mask = al[..., 0] >= 110
    for y in range(lh):
        for x in range(lw):
            if mask[y, x]:
                c = tuple(int(min(255, v)) for v in rgbd[y, x])
                if c[0] + c[1] + c[2] < 60:   # o contorno antigo vira transparente; o novo é refeito depois
                    continue
                if cob[y, x] >= 95:
                    c = K1
                elif cob_claro[y, x] >= 120:
                    c = B2
                out.put(x + 1, y + 1, c)
    out.encaixar_paleta(paleta)
    out.contorno()
    b = out.bbox()
    return out.a[b[1]:b[3] + 1, b[0]:b[2] + 1].copy()


def pedestal(t, cx, base_y, larg, rng):
    """Bloquinho de pedra em 3/4 com o pé em base_y (linha da face frontal de baixo). Retorna y do topo da face."""
    meia = larg // 2
    topo_cima = base_y - 7
    t.rect(cx - meia, topo_cima, cx + meia, topo_cima, S7)
    t.rect(cx - meia, topo_cima + 1, cx + meia, topo_cima + 2, S8)
    t.rect(cx - meia, topo_cima + 3, cx + meia, topo_cima + 3, S6)
    t.rect(cx - meia, topo_cima + 4, cx + meia, base_y - 1, S5)
    t.rect(cx - meia, base_y, cx + meia, base_y, S4)
    t.put(cx - meia + rng.randint(1, 2), topo_cima + 5, S2)
    t.put(cx + meia - rng.randint(1, 2), base_y - 2, S4)
    t.put(cx + meia, topo_cima + 1, S9)
    # contorno próprio (está sobre a viga, então o passo global não o contorna)
    for x in range(cx - meia - 1, cx + meia + 2):
        t.put(x, topo_cima - 1, K0)
        t.put(x, base_y + 1, K0)
    for y in range(topo_cima - 1, base_y + 2):
        t.put(cx - meia - 1, y, K0)
        t.put(cx + meia + 1, y, K0)
    return topo_cima


def colar_com_contorno(t, arr, ox, oy):
    """Cola um sprite já contornado; ele traz o próprio contorno preto."""
    t.colar(arr, ox, oy)


# ---------------------------------------------------------------- correntes
CORRENTE_ELO = [
    ".KKK.",
    "KIhhK",
    "KI.hK",
    "KI.hK",
    "KhhhK",
    ".KKK.",
]
CORRENTE_BARRA = [
    ".KhK.",
    ".KhK.",
]
CORRENTE_GANCHO = [
    ".KhK.",
    ".KhKK",
    ".KhhIK",
    "..KKhK",
    "..KIhK",
    "...KK.",
]
MAPA_FERRO = {"K": K0, "I": I1, "h": S2}


def desenhar_padrao(t, padrao, ox, oy, mapa):
    for dy, linha in enumerate(padrao):
        for dx, ch in enumerate(linha):
            if ch != ".":
                t.put(ox + dx, oy + dy, mapa[ch])


def corrente(t, x, y, elos, com_gancho=True):
    """Corrente pendurada a partir de (x, y) (canto esquerdo do primeiro elo). Retorna y final."""
    for i in range(elos):
        desenhar_padrao(t, CORRENTE_ELO, x, y, MAPA_FERRO)
        y += len(CORRENTE_ELO) - 1
        if i < elos - 1:
            desenhar_padrao(t, CORRENTE_BARRA, x, y, MAPA_FERRO)
            y += len(CORRENTE_BARRA)
    if com_gancho:
        desenhar_padrao(t, CORRENTE_GANCHO, x, y, MAPA_FERRO)
        y += len(CORRENTE_GANCHO)
    return y


# ---------------------------------------------------------------- montagem dos arcos
PILAR_ALT = 149          # altura do pillar_tall (topo em y=0 do sprite dele)
APOIO = 14               # linhas do topo do pilar cobertas pela viga (face de cima do capitel: linhas 0..13)


def montar_portal(caveira_g, caveira_p, caveira_p2, seed=7):
    rng = random.Random(seed)
    W = 332
    H = 206
    chao = H                        # pivô: centro da borda de baixo
    topo_pilar = chao - PILAR_ALT   # linha 0 do pillar_tall
    fy1 = topo_pilar + APOIO - 1    # última linha da face frontal da viga
    ty0 = fy1 - FRENTE - TOPO + 1
    cx = W // 2
    centros = (cx - 128, cx + 128)  # centros dos pilares
    t = Tela(W, H)
    aneis = (centros[0] + 18, centros[1] - 18)
    fy0, fy1b = desenhar_viga(t, 1, W - 2, ty0, rng, cx_chave=cx, aneis=aneis)
    assert fy1b == fy1
    lascar_ponta(t, 1, -1, ty0, fy0, fy1, rng, tam_cima=4, tam_baixo=7)
    lascar_ponta(t, W - 2, +1, ty0, fy0, fy1, rng, tam_cima=6, tam_baixo=5)
    mordidas_baixo(t, 1, W - 2, fy1, rng, 3, evitar=(cx,) + aneis)
    mordidas_cima(t, 1, W - 2, ty0, rng, 3, evitar=(cx, cx - 62, cx + 62) + aneis)

    # pedestais e caveiras sobre a face de cima
    base = fy0 - 2
    yp = pedestal(t, cx, base, 16, rng)
    yg = yp - caveira_g.shape[0] + 2
    colar_com_contorno(t, caveira_g, cx - caveira_g.shape[1] // 2, yg)
    for dx, cav in ((-62, caveira_p), (62, caveira_p2)):
        yp = pedestal(t, cx + dx, base, 12, rng)
        colar_com_contorno(t, cav, cx + dx - cav.shape[1] // 2, yp - cav.shape[0] + 2)

    t.contorno()
    # correntes por baixo da viga (depois do contorno geral: já trazem o próprio)
    corrente(t, cx - 48, fy1 + 1, 2)
    corrente(t, cx + 44, fy1 + 1, 3)
    t.encaixar_paleta(PALETA_PEDRA)
    b = t.bbox()
    rec = t.a[max(0, b[1] - 1):, :]
    return rec, centros, topo_pilar - max(0, b[1] - 1)


def montar_ruina(caveira_p, seed=11):
    rng = random.Random(seed)
    W = 172
    H = 206
    chao = H
    topo_pilar = chao - PILAR_ALT
    fy1 = topo_pilar + APOIO - 1
    ty0 = fy1 - FRENTE - TOPO + 1
    centro_pilar = 34
    t = Tela(W, H)
    x_quebra = 138
    fy0, _ = desenhar_viga(t, 0, W - 1, ty0, rng, cx_chave=None, aneis=(centro_pilar + 18,), glifos=True)
    lascar_ponta(t, 0, -1, ty0, fy0, fy1, rng, tam_cima=3, tam_baixo=5)
    mordidas_baixo(t, 0, x_quebra - 10, fy1, rng, 2, evitar=(centro_pilar + 18,))
    mordidas_cima(t, 0, x_quebra - 10, ty0, rng, 2, evitar=(centro_pilar + 18, 90))

    # quebra irregular à direita: perfil em passeio aleatório com dentes
    # perfil em degraus (facetas de 2 a 5 linhas), cada degrau recuando ou avançando bastante
    perfil = {}
    y = ty0
    bx = x_quebra - 8
    while y <= fy1:
        alt = rng.randint(2, 5)
        bx += rng.choice((-7, -4, -2, 3, 5, 8))
        bx = max(x_quebra - 12, min(x_quebra + 18, bx))
        for dy in range(alt):
            if y + dy <= fy1:
                perfil[y + dy] = bx + (dy if rng.random() < 0.5 else 0)
        y += alt
    # dois dentes curtos e grossos que sobram na face frontal (a pedra rompeu em lascas)
    px_corpo = max(perfil.values())
    for y0, alt in ((fy0 + 3, 5), (fy0 + 17, 4)):
        avanco = rng.randint(4, 6)
        for dy in range(alt):
            afina = 0 if 0 < dy < alt - 1 else 2
            perfil[y0 + dy] = min(W - 1, perfil[y0 + dy] + avanco - afina)
    # a face de cima rompe antes da frontal (um naco a menos no alto)
    for y in range(ty0, fy0 + 1):
        perfil[y] = min(perfil[y], x_quebra - 14 + 2 * (y - ty0) + rng.randint(0, 1))
    for y, px in perfil.items():
        for x in range(px, W):
            t.apagar(x, y)
    # face fresca da quebra: 2-3 px claros com risco escuro a cada degrau
    for y, px in perfil.items():
        larg = rng.randint(2, 3)
        for i in range(1, larg + 1):
            if t.opaco(px - i, y):
                if y < fy0:
                    c = S9 if i == 1 else S8
                else:
                    c = S8 if i == 1 else S6
                t.put(px - i, y, c)
        if t.opaco(px - larg - 1, y) and rng.random() < 0.6:
            t.put(px - larg - 1, y, S2 if y >= fy0 else S7)
        if y - 1 in perfil and perfil[y - 1] > px:          # degrau recuando: topo da faceta em luz
            for x in range(px, perfil[y - 1]):
                if t.opaco(x, y - 1):
                    t.put(x, y - 1, S9 if y - 1 >= fy0 else S9)
        if y - 1 in perfil and perfil[y - 1] < px:          # degrau avançando: sombra por baixo
            for x in range(perfil[y - 1], px):
                if t.opaco(x, y):
                    t.put(x, y, S3)
    # rachaduras partindo da quebra para dentro
    for y in (fy0 + 8, fy0 + 21):
        rachadura(t, perfil[y] - 4, y, rng.randint(10, 16), rng, S2, S6,
                  mascara=lambda px, py: t.opaco(px, py) and t.cor(px, py) in (S5, S6, S4), dy_pref=0)
    rachadura(t, perfil[ty0 + 3] - 3, ty0 + 3, 9, rng, S5, None,
              mascara=lambda px, py: t.opaco(px, py) and t.cor(px, py) in (S8, S7), dy_pref=0)

    # fragmentos: um naco grande a meio caminho de cair, um menor mais abaixo, pedrinhas
    def naco(cx, cy, w, h, inclina=0):
        """Pedra facetada: topo em luz, lado esquerdo claro, lado direito e base em sombra, risco interno."""
        for y in range(h):
            x0 = cx - w // 2 + (y * inclina) // max(1, h)
            corte = 1 if y in (0, h - 1) else 0
            for x in range(x0 + corte, x0 + w - corte):
                if y == 0:
                    c = S9
                elif x == x0 + corte and y < h - 1:
                    c = S8
                elif y >= h - 2 or x == x0 + w - 1 - corte:
                    c = S3 if y == h - 1 else S4
                else:
                    c = S6
                t.put(x, cy + y, c)
        if w >= 5 and h >= 4:
            for i in range(min(w, h) - 2):   # faceta diagonal escura
                t.put(cx - w // 2 + 1 + i + (h // 2 * inclina) // max(1, h), cy + 1 + i, S4 if i else S5)
            t.put(cx + w // 2 - 2, cy + 1, S9)

    px_base = min(px_corpo + 2, W - 24)
    naco(px_base + 10, fy0 + 9, 12, 10, inclina=3)
    naco(px_base + 16, fy1 + 5, 8, 7, inclina=-2)
    naco(px_base + 5, fy1 + 13, 5, 4)
    naco(px_base + 12, fy1 + 19, 4, 3)
    naco(px_base + 3, fy0 + 25, 3, 3)
    # pedra solta em cima da face, perto da quebra
    naco(perfil[ty0 + 2] - 10, ty0 - 2, 8, 6, inclina=1)

    # uma caveira pequena no pedestal, sobre o pilar
    base = fy0 - 2
    yp = pedestal(t, centro_pilar + 2, base, 12, rng)
    colar_com_contorno(t, caveira_p, centro_pilar + 2 - caveira_p.shape[1] // 2, yp - caveira_p.shape[0] + 2)

    t.contorno()
    corrente(t, centro_pilar + 50, fy1 + 1, 2)
    # corrente arrebentada perto da quebra: só um elo e meio
    corrente(t, x_quebra - 22, fy1 + 1, 1, com_gancho=False)
    t.encaixar_paleta(PALETA_PEDRA)
    b = t.bbox()
    rec = t.a[max(0, b[1] - 1):, :]
    return rec, centro_pilar, topo_pilar - max(0, b[1] - 1)


# ---------------------------------------------------------------- baú
BAU_MAPA = {
    "K": (0, 0, 0),
    "k": (26, 18, 16),
    "s": (36, 24, 18),
    "w": (58, 40, 32),
    "W": (85, 57, 42),
    "V": (110, 77, 54),
    "v": (138, 102, 71),
    "u": (122, 82, 56),
    "i": (47, 45, 56),
    "I": (75, 69, 76),
    "j": (106, 100, 114),
    "g": (157, 107, 68),
    "G": (194, 160, 115),
    "H": (228, 199, 144),
    "*": (255, 242, 196),
    "f": (21, 16, 14),
}


def _conteudo(esq, mad_e, cinta, mad_m, trava, mad_m2, mad_d, dir_):
    return esq + mad_e + cinta + mad_m + trava + mad_m2 + cinta + mad_d + dir_


def desenhar_bau():
    linhas = []
    linhas.append("..........KKKKKKKKKKKKKK..........")
    linhas.append(".......KKKvvvvvvvvvvvvvvKKK.......")
    linhas.append(".....KK*vVVVVVVVVVVVVVVVVvvKK.....")
    linhas.append("....KvvVVuVVWVVVuVVVVVWVVuVvvK....")
    linhas.append("...KvVVuVVVWVVVVuVVVVVVWVVuVVvK...")
    linhas.append("..KvvvvvvvvWvvvvvvvvvvvWvvvvvvvK..")
    # face frontal da tampa (x 2..31 = 30 colunas)
    linhas.append(".K" + _conteudo("HGG", "WWW", "iIi", "WWW", "WWWWWW", "WWW", "WWW", "GGH") + "K.")
    linhas.append(".K" + _conteudo("GGg", "WWW", "iji", "WWW", "WWWWWW", "WWW", "WWW", "gGG") + "K.")
    linhas.append(".K" + _conteudo("ggg", "WWW", "iIi", "WWW", "WWWWWW", "WWW", "WWW", "ggg") + "K.")
    linhas.append(".K" + _conteudo("WWW", "WWW", "iIi", "WWW", "KHHHHK", "WWW", "WWW", "WWW") + "K.")
    linhas.append(".K" + _conteudo("WWW", "WWW", "iIi", "WWW", "K*GGgK", "WWW", "WWW", "WWW") + "K.")
    linhas.append(".K" + _conteudo("III", "III", "iIi", "III", "KHGGgK", "III", "III", "III") + "K.")
    linhas.append(".K" + _conteudo("sss", "sss", "isi", "sss", "KGkggK", "sss", "sss", "sss") + "K.")
    # corpo
    linhas.append(".K" + _conteudo("www", "www", "iIi", "www", "KGgggK", "www", "www", "www") + "K.")
    linhas.append(".K" + _conteudo("www", "www", "iji", "www", "KgggkK", "www", "www", "www") + "K.")
    linhas.append(".K" + _conteudo("www", "www", "iIi", "www", "wKKKKw", "www", "www", "www") + "K.")
    linhas.append(".K" + _conteudo("kkk", "kkk", "iIi", "kkk", "kkkkkk", "kkk", "kkk", "kkk") + "K.")
    linhas.append(".K" + _conteudo("www", "wWw", "iIi", "wwWw", "wwww", "wwWw", "www", "www") + "K.")
    linhas.append(".K" + _conteudo("www", "www", "iIi", "www", "wwwwww", "www", "www", "www") + "K.")
    linhas.append(".K" + _conteudo("www", "www", "iji", "www", "wwwwww", "wWw", "www", "www") + "K.")
    linhas.append(".K" + _conteudo("kkk", "kkk", "iIi", "kkk", "kkkkkk", "kkk", "kkk", "kkk") + "K.")
    linhas.append(".K" + _conteudo("www", "www", "iIi", "wWww", "wwww", "wwww", "www", "www") + "K.")
    linhas.append(".K" + _conteudo("www", "www", "iIi", "www", "wwwwww", "www", "wWw", "www") + "K.")
    linhas.append(".K" + _conteudo("www", "Www", "iIi", "www", "wwwwww", "www", "www", "www") + "K.")
    linhas.append(".K" + _conteudo("HGG", "www", "iIi", "www", "wwwwww", "www", "www", "GGH") + "K.")
    linhas.append(".K" + _conteudo("GGg", "www", "iji", "www", "wwwwww", "www", "www", "gGG") + "K.")
    linhas.append(".K" + _conteudo("ggg", "www", "iIi", "www", "wwwwww", "www", "www", "ggg") + "K.")
    linhas.append(".K" + "i" * 30 + "K.")
    linhas.append("...KffK" + "." * 20 + "KffK...")
    linhas.append("...KKKK" + "." * 20 + "KKKK...")
    for i, l in enumerate(linhas):
        assert len(l) == 34, (i, len(l), l)
    assert len(linhas) == 30, len(linhas)
    t = Tela(34, 30)
    desenhar_padrao(t, linhas, 0, 0, BAU_MAPA)
    t.contorno()
    return t.a


# ---------------------------------------------------------------- prévias
def previas(destino, portal, ruina, bau, centros_portal, centro_ruina):
    os.makedirs(destino, exist_ok=True)
    fundo = (58, 62, 40, 255)

    def isolado(arr, nome, k=3):
        im = Image.fromarray(arr, "RGBA")
        base = Image.new("RGBA", (im.width + 16, im.height + 16), fundo)
        base.alpha_composite(im, (8, 8))
        base.resize((base.width * k, base.height * k), Image.NEAREST).save(os.path.join(destino, nome))

    isolado(portal, "a_arco_portal_3x.png")
    isolado(ruina, "a_arco_ruina_3x.png")
    isolado(bau, "a_bau_bolsao_3x.png", k=6)

    grama = Image.open(os.path.join(R, "godot", "art2d", "tiles", "cripta_grama.png")).convert("RGBA")
    tiles = Image.open(os.path.join(R, "godot", "art2d", "tiles", "cripta_tiles.png")).convert("RGBA")
    arq = Image.open(os.path.join(R, "godot", "art2d", "sprites", "arqueiro", "arqueiro_idle.png")).convert("RGBA")
    arq = arq.crop((0, 0, 92, 92))
    pilar = Image.open(os.path.join(PROPS, "pillar_tall.png")).convert("RGBA")
    rachado = Image.open(os.path.join(PROPS, "pillar_cracked.png")).convert("RGBA")
    rng = random.Random(3)

    def cena(largura, altura, chao, estrada_x, arco, arco_x, pilares, extras, arco_dy=0):
        base = Image.new("RGBA", (largura, altura), fundo)
        for ty in range(0, altura, 64):
            for tx in range(0, largura, 64):
                i = rng.randint(0, 3)
                base.alpha_composite(grama.crop((i * 64, 0, i * 64 + 64, 64)), (tx, ty))
        for ty in range(0, altura, 64):
            for tx in range(estrada_x, estrada_x + 128, 64):
                i = rng.randint(0, 3)
                base.alpha_composite(tiles.crop((i * 64, 0, i * 64 + 64, 64)), (tx, ty))
        for im, cx in pilares:
            base.alpha_composite(im, (cx - im.width // 2, chao - im.height))
        base.alpha_composite(Image.fromarray(arco, "RGBA"), (arco_x, chao - arco.shape[0] + arco_dy))
        for im, (x, y) in extras:
            base.alpha_composite(im, (x, y))
        return base.resize((base.width * 2, base.height * 2), Image.NEAREST)

    # portal: pilares com centros a 256 px, estrada de 128 px entre eles, arqueiro no meio
    W, H = 420, 300
    chao = 250
    cx = W // 2
    cena(W, H, chao, cx - 64, portal, cx - portal.shape[1] // 2,
         [(pilar, cx - 128), (pilar, cx + 128)],
         [(arq, (cx - 46, chao + 8 - 76))]).save(os.path.join(destino, "b_cena_portal_2x.png"))
    # mesma cena com o arqueiro adiante do portal (para ver a leitura da verga por trás)
    cena(W, H, chao, cx - 64, portal, cx - portal.shape[1] // 2,
         [(pilar, cx - 128), (pilar, cx + 128)],
         [(arq, (cx - 46 - 40, chao - 40 - 76)), (Image.fromarray(bau, "RGBA"), (cx + 30, chao + 10 - 30))]
         ).save(os.path.join(destino, "b_cena_portal_arqueiro_atras_2x.png"))
    # ruína: pilar rachado (131 px: 18 px mais baixo que o pillar_tall) do lado esquerdo da estrada;
    # para a verga apoiar nele, o sprite da ruína desce 18 px (o pivô dela segue a regra do pillar_tall)
    W2, H2 = 360, 300
    cx2 = 120
    cena(W2, H2, chao, cx2 + 40, ruina, cx2 - centro_ruina,
         [(rachado, cx2)],
         [(arq, (cx2 + 60, chao - 76 + 4))],
         arco_dy=PILAR_ALT - rachado.height).save(os.path.join(destino, "b_cena_ruina_2x.png"))
    cena(W2, H2, chao, cx2 + 40, ruina, cx2 - centro_ruina,
         [(pilar, cx2)],
         [(arq, (cx2 + 60, chao - 76 + 4))]).save(os.path.join(destino, "b_cena_ruina_pilar_tall_2x.png"))


def main():
    destino_previas = None
    if "--previas" in sys.argv:
        destino_previas = sys.argv[sys.argv.index("--previas") + 1]
    cav = recortar_caveira(os.path.join(PROPS, "skull_single.png"))
    # caveiras pequenas: a da direita do skull_pair (desenhada nesse tamanho, sem reduzir) e o espelho dela
    cav_p = recortar_regiao(os.path.join(PROPS, "skull_pair.png"), 28, 2, 46, 23, PALETA_PEDRA)
    cav_p2 = cav_p[:, ::-1].copy()
    cav_g = cav.copy()
    g = Tela(cav_g.shape[1], cav_g.shape[0])
    g.a[:] = cav_g
    g.encaixar_paleta(PALETA_PEDRA)
    cav_g = g.a

    portal, centros, _ = montar_portal(cav_g, cav_p, cav_p2)
    ruina, centro_ruina, _ = montar_ruina(cav_p)
    bau = desenhar_bau()
    for nome, arr in (("arco_portal", portal), ("arco_ruina", ruina), ("bau_bolsao", bau)):
        im = Image.fromarray(arr, "RGBA")
        im.save(os.path.join(PROPS, nome + ".png"))
        cores = len([c for c in im.getcolors(100000) if c[1][3] > 0])
        print(f"{nome}.png {im.width}x{im.height}  pivô ({im.width // 2},{im.height})  cores {cores}")
    print("centros dos pilares no arco_portal:", centros, "| centro do pilar no arco_ruina:", centro_ruina)
    if destino_previas:
        previas(destino_previas, portal, ruina, bau, centros, centro_ruina)


if __name__ == "__main__":
    main()
