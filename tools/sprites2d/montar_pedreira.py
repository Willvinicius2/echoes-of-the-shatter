#!/usr/bin/env python3
"""Monta por código os props da Pedreira dos Ecos (área 2 do Ato I), na mesma linguagem dos props pixelados da
Cripta: grade de 1 px de mundo, alfa binário, contorno preto de 1 px, paleta curta por material, luz de cima-esquerda,
sem anti-serrilhado nem gradientes.

Saídas (em godot/art2d/props/):
  pedreira_blocos.png          pilha de blocos de calcário cortados, com marcas de cunha
  pedreira_andaime.png         andaime de madeira quebrado, com plataforma meio caída e corda
  pedreira_carrinho.png        carrinho de pedra tombado para o lado da roda quebrada, blocos derramados
  pedreira_portico.png         pórtico de guindaste (marco do trecho): pés em A, viga, roldana, corrente e bloco pendurado
  pedreira_poste_lanterna.png  poste com braço, correntinha e lanterna de ferro acesa
  pedreira_portao.png          portão final da fase (fundo da luta contra o elite): dois bastiões maciços de blocos de
                               calcário com vão livre de 2 tiles, verga grossa com pedra-chave, grade de ferro levantada
                               por correntes e guindaste de madeira com roldana e contrapeso no topo do bastião direito
  pedreira_lasca_0/1/2.png     lascas angulares de bloco cortado soltas no chão (1, 2 e 3 fragmentos), no lugar das
                               pedras redondas da área 1

Pivô de todos = centro da borda de baixo. Uso: python3 -I tools/sprites2d/montar_pedreira.py [--previas DIR]
Só PIL e numpy; reaproveita `Tela`, `rachadura`, `pintar_grupo` e os padrões de corrente de montar_marcos.py
(arquivo irmão, carregado por caminho porque o script roda com -I).
"""
import importlib.util
import math
import os
import random
import sys

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(AQUI, "..", "..")
PROPS = os.path.join(R, "godot", "art2d", "props")

_spec = importlib.util.spec_from_file_location("montar_marcos", os.path.join(AQUI, "montar_marcos.py"))
marcos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(marcos)
Tela = marcos.Tela
rachadura = marcos.rachadura
pintar_grupo = marcos.pintar_grupo
desenhar_padrao = marcos.desenhar_padrao

# ---------------------------------------------------------------- paleta da Pedreira
# Mesma lógica da área 1 (contorno K0, linha interna K1), só o matiz muda: calcário bege-acinzentado, madeira
# cinza-amarronzada, ferro azul-acinzentado, corda cor de palha. Cada material: 3 tons de base + aresta de luz +
# sombra funda.
K0 = marcos.K0
K1 = marcos.K1
# calcário cortado
# (rodada 2, Jev: calcário 16% mais escuro que a v1, mesma matiz; vale para toda a família: pilha, bloco do
# pórtico, pedras do carrinho e entulho)
C0 = (55, 44, 39)       # sombra funda (junta, embaixo)
C1 = (94, 77, 64)       # escuro (parte baixa da face frontal, lateral direita chapada)
C2 = (133, 116, 91)     # médio (face frontal)
C3 = (170, 155, 126)    # claro (face de cima)
C4 = (198, 188, 161)    # aresta de luz
# madeira gasta
M0 = (40, 30, 26)       # sombra funda / fenda
M1 = (76, 58, 46)       # escuro
M2 = (114, 92, 68)      # médio
M3 = (152, 128, 96)     # claro
M4 = (194, 170, 132)    # aresta de luz / madeira fresca da quebra
# ferro azul-acinzentado escuro
F0 = (26, 28, 38)       # sombra funda
F1 = (48, 52, 66)       # escuro
F2 = (76, 82, 98)       # médio
F3 = (118, 126, 142)    # aresta de luz
# corda de palha
R1 = (128, 100, 54)     # escuro
R2 = (184, 152, 88)     # médio
R3 = (226, 202, 136)    # claro
# chama (miolo G4/B2 da área 1 + laranja)
G4 = marcos.G4
B2 = marcos.B2
L1 = (196, 78, 28)      # laranja escuro
L2 = (238, 142, 48)     # laranja
PALETA = [K0, K1, C0, C1, C2, C3, C4, M0, M1, M2, M3, M4, F0, F1, F2, F3, R1, R2, R3, G4, B2, L1, L2]
MAPA_FERRO = {"K": K0, "I": F2, "h": F1}


# ---------------------------------------------------------------- primitivas
def linha(t, x0, y0, x1, y1, cor, esp=1):
    """Bresenham; `esp` engrossa para baixo (traço mais horizontal) ou para a direita (mais vertical)."""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    x, y = x0, y0
    while True:
        for k in range(esp):
            if dx >= -dy:
                t.put(x, y + k, cor)
            else:
                t.put(x + k, y, cor)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def poligono(t, pts, cor):
    """Preenche um polígono (lista de (x, y)) por scanline."""
    ys = [p[1] for p in pts]
    for y in range(min(ys), max(ys) + 1):
        xs = []
        n = len(pts)
        for i in range(n):
            (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
            if ya == yb:
                continue
            if min(ya, yb) <= y < max(ya, yb):
                xs.append(xa + (y - ya) * (xb - xa) / float(yb - ya))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            for x in range(int(round(xs[i])), int(round(xs[i + 1])) + 1):
                t.put(x, y, cor)


def elipse(t, cx, cy, rx, ry, cor):
    for y in range(cy - ry, cy + ry + 1):
        for x in range(cx - rx, cx + rx + 1):
            if ((x - cx) / float(rx)) ** 2 + ((y - cy) / float(ry)) ** 2 <= 1.0:
                t.put(x, y, cor)


def colar_contornado(dest, elem, ox=0, oy=0):
    """Contorna o elemento (na própria tela) e cola no destino: é a separação preta entre peças sobrepostas."""
    elem.contorno()
    dest.colar(elem, ox, oy)


def nova(w, h):
    return Tela(w, h)


def cisalhar(t, x_fixo, inclinacao):
    """Desce cada coluna à direita de x_fixo em round((x - x_fixo) * inclinacao) px: inclina o desenho sem
    reamostrar (pixels continuam inteiros)."""
    out = nova(t.w, t.h + int(abs(inclinacao) * t.w) + 2)
    for x in range(t.w):
        d = int(round((x - x_fixo) * inclinacao))
        for y in range(t.h):
            if t.a[y, x, 3] > 0:
                out.put(x, y + d, t.cor(x, y))
    return out


def morder(t, pixels, cor_fresca, rng, n, larg=(2, 4), prof=(1, 2)):
    """Mordidas numa aresta: `pixels` é a lista de (x, y, dx, dy) da aresta e da direção para dentro."""
    if not pixels:
        return
    for _ in range(n):
        x, y, dx, dy = rng.choice(pixels)
        w = rng.randint(*larg)
        p = rng.randint(*prof)
        for i in range(w):
            pp = p if 0 < i < w - 1 else 1
            for k in range(pp):
                if dy:
                    t.apagar(x + i, y + k * dy)
                else:
                    t.apagar(x + k * dx, y + i)
            if dy:
                t.put(x + i, y + pp * dy, cor_fresca)
            else:
                t.put(x + pp * dx, y + i, cor_fresca)


# ---------------------------------------------------------------- calcário
def bloco_calcario(t, x, y, w, h, d, s, rng, cunhas=False, rachado=True, lascas=1, mordidas=1, cima=C3,
                   cunhas_lado=False, faixa=None):
    """Bloco de calcário cortado em 3/4 oblíquo: face de cima (w x d) a partir de (x, y), face frontal (w x h)
    embaixo, lateral direita de `s` px que sobe 1 px por coluna. Mesma leitura das lajes da Cripta (rock_slabs):
    face de cima clara e mosqueada, face frontal escura com uma faixa média logo abaixo da quina, base funda,
    lateral em sombra; textura só trocando entre os tons do material; quinas duras (pedra cortada), uma lasca ou
    outra. `cunhas` = fileira de marcas de cunha na quina de cima; `cunhas_lado` = a mesma fileira na aresta
    esquerda (bloco caído de lado); `faixa` = (início, teto) em px da faixa média abaixo da quina (padrão: h/3 até
    h/2). Devolve a caixa ocupada."""
    fy0 = y + d
    fy1 = fy0 + h - 1
    t.rect(x, y, x + w - 1, fy0 - 1, cima)
    t.rect(x, fy0, x + w - 1, fy1, C1)
    # faixa média irregular logo abaixo da quina (a luz ainda pega o alto da face frontal)
    f_ini, f_teto = faixa if faixa else (max(2, h // 3), h // 2)
    lim = fy0 + f_ini
    for px in range(x, x + w):
        if rng.random() < 0.35:
            lim = max(fy0 + 2, min(fy0 + f_teto, lim + rng.choice((-1, 1))))
        t.vline(px, fy0, lim, C2)
        t.put(px, fy1, C0)
        if h >= 10 and rng.random() < 0.5:
            t.put(px, fy1 - 1, C0)
    for i in range(s):                       # lateral direita: um tom só de sombra, chapado (Jev, rodada 2)
        cx = x + w + i
        t.vline(cx, y - i - 1, fy0 - i - 2, C3 if i < 2 else C2)
        t.vline(cx, fy0 - i - 1, fy1 - i - 1, C1)
        t.put(cx, fy1 - i - 1, C0)
    t.hline(x, x + w - 1, y, C4)             # arestas de luz
    t.vline(x, y, fy0 - 1, C4)
    t.hline(x + 1, x + w - 1, fy0, C3)
    if s:
        t.hline(x + w, x + w + s - 1, fy0 - s, C3)
    # grão e mosqueado da face de cima (manchas médias, pontos de luz)
    so_cima = lambda px, py: x + 1 <= px <= x + w - 2 and y + 1 <= py <= fy0 - 1
    for _ in range(max(2, w // 6)):
        pintar_grupo(t, rng.randint(x + 2, x + w - 3), rng.randint(y + 1, fy0 - 1), C2, rng, rng.randint(4, 12),
                     lambda px, py: so_cima(px, py) and t.cor(px, py) == cima)
    for _ in range(max(2, w * d // 16)):
        px, py = rng.randint(x + 1, x + w - 2), rng.randint(y + 1, fy0 - 1)
        c = t.cor(px, py)
        if c == cima and rng.random() < 0.5:
            t.put(px, py, C4)
        elif c == C2 and rng.random() < 0.3:
            t.put(px, py, C1)
    # grão da face frontal
    so_frente = lambda px, py: x + 1 <= px <= x + w - 2 and fy0 + 1 <= py <= fy1 - 1
    for _ in range(max(2, w * h // 30)):
        px, py = rng.randint(x + 1, x + w - 2), rng.randint(fy0 + 1, fy1 - 1)
        c = t.cor(px, py)
        if c == C1:
            t.put(px, py, C2 if rng.random() < 0.45 else C0)
        elif c == C2 and rng.random() < 0.5:
            t.put(px, py, C3 if rng.random() < 0.4 else C1)
    for _ in range(max(1, w // 14)):
        pintar_grupo(t, rng.randint(x + 2, x + w - 3), fy1 - rng.randint(1, 3), C0, rng, rng.randint(3, 8),
                     lambda px, py: so_frente(px, py) and t.cor(px, py) == C1)
    for _ in range(max(1, w // 12)):
        pintar_grupo(t, rng.randint(x + 2, x + w - 3), rng.randint(fy0 + 2, fy1 - 2), C2, rng, rng.randint(3, 8),
                     lambda px, py: so_frente(px, py) and t.cor(px, py) == C1)
        pintar_grupo(t, rng.randint(x + 2, x + w - 3), fy0 + rng.randint(1, 3), C1, rng, rng.randint(2, 6),
                     lambda px, py: so_frente(px, py) and t.cor(px, py) == C2)
    # talhes (marcas de ferramenta): cada bloco sorteia o próprio repertório: traços horizontais de 1 a 4 px,
    # risquinhos diagonais, covinhas de 2x2; quantidade e posição também variam (Jev: "variando os talhes")
    estilo = rng.choice(("h", "hd", "hp", "dp"))
    for _ in range(rng.randint(max(1, w // 12), max(2, w // 6))):
        px, py = rng.randint(x + 2, x + w - 6), rng.randint(fy0 + 1, fy1 - 3)
        c = t.cor(px, py)
        esc = C0 if c == C1 else C1
        luz = C2 if c == C1 else C3
        forma = rng.choice(estilo)
        if forma == "h":
            comp = rng.randint(1, 4)
            t.hline(px, px + comp, py, esc)
            if rng.random() < 0.6:
                t.hline(px + 1, px + comp, py - 1, luz)
        elif forma == "d":
            comp = rng.randint(2, 3)
            for i in range(comp):
                t.put(px + i, py + (i if rng.random() < 0.5 else -i), esc)
            t.put(px + comp, py, luz)
        else:
            t.rect(px, py, px + 1, py + 1, esc)
            t.put(px + 1, py + 1, C0)
            t.put(px + 2, py, luz)
    # marcas de cunha: fileira de entalhes retangulares na quina (cima) ou na aresta esquerda (bloco de lado)
    if cunhas and w >= 20:
        px = x + 3 + rng.randint(0, 2)
        while px + 2 <= x + w - 3:
            lw = rng.choice((1, 1, 2))
            alt = rng.choice((2, 2, 3))
            if rng.random() < 0.85:          # uma marca ou outra falha (a cunha não pegou)
                t.rect(px, fy0, px + lw, fy0 + alt, C0)
                t.hline(px, px + lw, fy0 - 1, C1)
                t.vline(px + lw + 1, fy0, fy0 + alt - 1, C4)
                t.put(px + lw + 1, fy0 + alt, C3)
                t.put(px - 1, fy0 + 1, C0)
            px += lw + rng.randint(4, 6)
    if cunhas_lado and h >= 16:
        py = fy0 + 3 + rng.randint(0, 1)
        while py + 2 <= fy1 - 3:
            t.rect(x + 1, py, x + 3, py + 1, C0)
            t.hline(x + 1, x + 3, py + 2, C2)
            t.put(x, py, C3)
            py += 6
    # rachaduras
    if rachado and h >= 8:
        for _ in range(rng.randint(1, 2)):
            rachadura(t, rng.randint(x + 3, x + w - 4), fy0 + rng.randint(1, 2), rng.randint(3, h - 3), rng, C0, C2,
                      mascara=lambda px, py: so_frente(px, py) and t.cor(px, py) in (C1, C2))
    if rachado and d >= 6 and w >= 16:
        rachadura(t, rng.randint(x + 4, x + w - 5), y + 1, rng.randint(3, d - 2), rng, C2, None,
                  mascara=lambda px, py: so_cima(px, py) and t.cor(px, py) in (cima, C4))
    # lascas pequenas nas quinas (pedra cortada: poucas e duras)
    for _ in range(lascas):
        lado = rng.choice(("ce", "cd", "be"))
        tam = 2
        for dy in range(tam):
            for dx in range(tam - dy):
                if lado == "ce":
                    t.apagar(x + dx, y + dy)
                elif lado == "cd":
                    t.apagar(x + w - 1 + s - dx, y - s + dy)
                else:
                    t.apagar(x + dx, fy1 - dy)
            if lado == "ce":
                t.put(x + tam - dy, y + dy, C2)
            elif lado == "cd":
                t.put(x + w - 1 + s - (tam - dy), y - s + dy, C2)
            else:
                t.put(x + tam - dy, fy1 - dy, C1)
    if mordidas:
        morder(t, [(px, y, 0, 1) for px in range(x + 3, x + w - 5)], C2, rng, mordidas, larg=(2, 3), prof=(1, 1))
    return x, y - s, x + w - 1 + s, fy1


def bloco_inclinado(t, cx, cy, w, h, d, ang_graus, rng):
    """Bloco cortado deitado de través: a face frontal é um retângulo w x h girado `ang_graus` (positivo = ponta
    direita para cima) em torno de (cx, cy); a face de cima é essa aresta de cima extrudada `d` px para cima na tela
    e a lateral direita a aresta direita extrudada. Mesmos tons do bloco reto: cima clara, frente média/escura,
    lateral em um tom chapado, base funda."""
    a = math.radians(ang_graus)
    ca, sa = math.cos(a), math.sin(a)

    def rot(px, py):
        return (int(round(cx + px * ca + py * sa)), int(round(cy - px * sa + py * ca)))

    p0, p1, p2, p3 = rot(-w / 2, -h / 2), rot(w / 2, -h / 2), rot(w / 2, h / 2), rot(-w / 2, h / 2)
    cima = [p0, p1, (p1[0], p1[1] - d), (p0[0], p0[1] - d)]
    lado = [p1, p2, (p2[0] + 3, p2[1] - 3), (p1[0] + 3, p1[1] - 3)]
    poligono(t, lado, C1)
    poligono(t, cima, C3)
    poligono(t, [p0, p1, p2, p3], C2)
    # zona escura embaixo da face frontal (paralela à aresta de baixo), com fronteira irregular
    for k in range(1, h * 2 // 5 + 2):
        f0 = rot(-w / 2, h / 2 - k)
        f1 = rot(w / 2, h / 2 - k)
        if k <= 1:
            linha(t, f0[0], f0[1], f1[0], f1[1], C0)
        else:
            linha(t, f0[0] + rng.randint(0, 3), f0[1] + rng.randint(0, 1), f1[0] - rng.randint(0, 3), f1[1], C1)
    linha(t, cima[3][0], cima[3][1], cima[2][0], cima[2][1], C4)      # arestas de luz
    linha(t, p0[0], p0[1] - d, p3[0], p3[1], C4)
    linha(t, p0[0], p0[1], p1[0], p1[1], C3)
    linha(t, p1[0], p1[1], p2[0], p2[1], C1)
    # grão e talhes dentro da face frontal
    xs = [p[0] for p in (p0, p1, p2, p3)]
    ys = [p[1] for p in (p0, p1, p2, p3)]
    for _ in range(w * h // 20):
        px, py = rng.randint(min(xs), max(xs)), rng.randint(min(ys), max(ys))
        if not t.opaco(px, py):
            continue
        c = t.cor(px, py)
        if c == C2 and rng.random() < 0.5:
            t.put(px, py, C3 if rng.random() < 0.4 else C1)
        elif c == C1 and rng.random() < 0.4:
            t.put(px, py, C2 if rng.random() < 0.6 else C0)
        elif c == C3 and rng.random() < 0.4:
            t.put(px, py, C4 if rng.random() < 0.5 else C2)
    for _ in range(rng.randint(2, 4)):
        f = rng.uniform(-0.35, 0.35)
        g = rng.uniform(-0.3, 0.1)
        q0 = rot(w * f, h * g)
        q1 = rot(w * f + rng.randint(1, 3), h * g)
        linha(t, q0[0], q0[1], q1[0], q1[1], C0)
        t.put(q1[0] + 1, q1[1] - 1, C3)
    # lasca na quina de baixo à esquerda
    for dy in range(2):
        for dx in range(2 - dy):
            t.apagar(p3[0] + dx, p3[1] - dy)
    return min(xs), min(ys) - d, max(xs) + 3, max(ys)


def pedra_bruta(t, pts_topo, altura, rng):
    """Pedra bruta facetada: polígono de topo (claro, mosqueado) extrudado `altura` px para baixo; as faces de
    baixo ficam escuras (C1) com a quina em C2 e a base em C0, como as lajes da Cripta."""
    base = [(x, y + altura) for x, y in pts_topo]
    n = len(pts_topo)
    for i in range(n):
        (xa, ya), (xb, yb) = pts_topo[i], pts_topo[(i + 1) % n]
        poligono(t, [(xa, ya), (xb, yb), (xb, yb + altura), (xa, ya + altura)], C1)
    poligono(t, pts_topo, C3)
    xs = [p[0] for p in pts_topo]
    ys = [p[1] for p in pts_topo]
    for i in range(n):
        (xa, ya), (xb, yb) = pts_topo[i], pts_topo[(i + 1) % n]
        if yb > ya or (yb == ya and xb < xa):     # arestas viradas para baixo/esquerda: quina média
            linha(t, xa, ya, xb, yb, C2)
            linha(t, xa, ya + 1, xb, yb + 1, C2)
        else:                                       # arestas viradas para cima: luz
            linha(t, xa, ya, xb, yb, C4)
    for x, y in base:
        t.put(x, y, C0)
    ybase = max(ys) + altura
    for x in range(min(xs), max(xs) + 1):
        for y in range(ybase, ybase - altura, -1):
            if t.opaco(x, y) and t.cor(x, y) == C1:
                t.put(x, y, C0)
                break
    # faceta diagonal e mosqueado do topo
    pintar_grupo(t, (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2, C2, rng, rng.randint(4, 9),
                 lambda px, py: t.opaco(px, py) and t.cor(px, py) == C3)
    for _ in range(max(4, (max(xs) - min(xs)))):
        px, py = rng.randint(min(xs), max(xs)), rng.randint(min(ys), max(ys) + altura)
        c = t.cor(px, py) if t.opaco(px, py) else None
        if c == C3 and rng.random() < 0.5:
            t.put(px, py, C4 if rng.random() < 0.5 else C2)
        elif c == C1:
            t.put(px, py, C2 if rng.random() < 0.4 else C0)


def entulho(t, x0, x1, y_base, rng, n, tons=(C1, C2, C3)):
    """Pedrinhas e pó na base: grupos pequenos (3 a 9 px), nada de pixel solto."""
    for _ in range(n):
        cx = rng.randint(x0, x1)
        cy = y_base - rng.randint(0, 1)
        w = rng.randint(2, 4)
        h = rng.randint(1, 2)
        for dy in range(h):
            for dx in range(w - dy):
                t.put(cx + dx + dy // 2, cy - dy, tons[1] if dy else tons[0])
        t.put(cx + (w - 1) // 2, cy - h, tons[2])


# ---------------------------------------------------------------- madeira
def tons_poste(larg):
    """Colunas de um poste cilíndrico visto de frente: luz à esquerda, sombra à direita."""
    if larg <= 5:
        return [M3, M2, M2, M1, M0][:larg]
    k = larg - 5
    return [M4, M3] + [M2] * k + [M2, M1, M0]


def poste(t, x, y0, y1, larg, rng, quebrado_topo=False, quebrado_base=False, nos=True):
    """Poste vertical de madeira gasta: faixas de luz/sombra, veios em tracinhos, nós e uma fenda seca."""
    cols = tons_poste(larg)
    for i, c in enumerate(cols):
        t.vline(x + i, y0, y1, c)
    for _ in range((y1 - y0) // 3):
        vx = rng.randint(x + 1, x + larg - 2)
        vy = rng.randint(y0 + 1, y1 - 4)
        comp = rng.randint(2, 6)
        atual = t.cor(vx, vy)
        if atual == M2:
            cor = M1 if rng.random() < 0.6 else M3
        elif atual == M3:
            cor = M4 if rng.random() < 0.4 else M2
        elif atual == M1:
            cor = M0 if rng.random() < 0.4 else M2
        else:
            continue
        t.vline(vx, vy, min(y1, vy + comp), cor)
    if nos:
        for _ in range(max(1, (y1 - y0) // 36)):
            ny = rng.randint(y0 + 6, y1 - 6)
            nx = x + rng.randint(1, max(1, larg - 3))
            t.rect(nx, ny - 1, nx + 1, ny + 1, M1)
            t.put(nx + 1, ny, M0)
            t.put(nx, ny - 2, M3)
    if y1 - y0 > 24:
        rachadura(t, x + larg // 2, y0 + rng.randint(3, 8), rng.randint(6, 14), rng, M0, None,
                  mascara=lambda px, py: x + 1 <= px <= x + larg - 2 and py <= y1 - 2)
    if quebrado_topo:
        quebrar_topo(t, x, y0, larg, rng)
    else:
        t.hline(x, x + larg - 2, y0, M4)
        t.hline(x + 1, x + larg - 2, y0 + 1, M3)
    if quebrado_base:
        quebrar_base(t, x, y1, larg, rng)


def quebrar_topo(t, x, y0, larg, rng):
    """Topo partido: perfil em lascas, madeira fresca clara (M4) e fibras escuras."""
    alturas = [rng.randint(1, 6) for _ in range(larg)]
    alturas[rng.randrange(1, larg - 1)] = 0
    for i, a in enumerate(alturas):
        for dy in range(a):
            t.apagar(x + i, y0 + dy)
        t.put(x + i, y0 + a, M4)
        t.put(x + i, y0 + a + 1, M3 if rng.random() < 0.5 else M4)
        if rng.random() < 0.6:
            t.vline(x + i, y0 + a + 2 + rng.randint(0, 1), y0 + a + 3 + rng.randint(0, 2), M0)


def quebrar_base(t, x, y1, larg, rng):
    for i in range(larg):
        a = rng.randint(0, 2)
        for dy in range(a):
            t.apagar(x + i, y1 - dy)
        t.put(x + i, y1 - a, M1)


def travessa(t, x0, x1, y, alt, rng, pontas=True):
    """Tronco/travessa horizontal: topo claro, corpo médio, embaixo escuro e sombra funda, veios horizontais."""
    cols = tons_poste(alt)
    for i, c in enumerate(cols):
        t.hline(x0, x1, y + i, c)
    for _ in range((x1 - x0) // 4):
        vx = rng.randint(x0 + 1, x1 - 6)
        vy = rng.randint(y + 1, y + alt - 2)
        comp = rng.randint(2, 7)
        atual = t.cor(vx, vy)
        if atual == M2:
            cor = M1 if rng.random() < 0.6 else M3
        elif atual == M3:
            cor = M4 if rng.random() < 0.4 else M2
        elif atual == M1:
            cor = M0 if rng.random() < 0.4 else M2
        else:
            continue
        t.hline(vx, vx + comp, vy, cor)
    for _ in range(max(1, (x1 - x0) // 40)):
        nx = rng.randint(x0 + 6, x1 - 6)
        ny = y + rng.randint(1, max(1, alt - 3))
        t.rect(nx - 1, ny, nx + 1, ny + 1, M1)
        t.put(nx, ny + 1, M0)
        t.put(nx - 2, ny, M3)
    if x1 - x0 > 30:
        rachadura(t, x0 + rng.randint(6, 14), y + alt // 2, rng.randint(8, 18), rng, M0, None,
                  mascara=lambda px, py: x0 + 1 <= px <= x1 - 1 and y + 1 <= py <= y + alt - 2, dy_pref=0)
    if pontas:
        for px, s in ((x0, 1), (x1, -1)):
            for dy in range(alt):
                if rng.random() < 0.4:
                    t.apagar(px, y + dy)
                    t.put(px + s, y + dy, M4 if dy < alt // 2 else M3)


def barra_inclinada(t, x0, y0, x1, y1, esp, rng, veios=True):
    """Barra de madeira de (x0,y0) a (x1,y1), com `esp` px de espessura vertical; luz em cima, sombra embaixo."""
    poligono(t, [(x0, y0), (x1, y1), (x1, y1 + esp - 1), (x0, y0 + esp - 1)], M2)
    linha(t, x0, y0, x1, y1, M4)
    if esp >= 5:
        linha(t, x0, y0 + 1, x1, y1 + 1, M3)
    linha(t, x0, y0 + esp - 1, x1, y1 + esp - 1, M0)
    linha(t, x0, y0 + esp - 2, x1, y1 + esp - 2, M1)
    if veios:
        comp = abs(x1 - x0)
        for _ in range(comp // 5):
            f0 = rng.random()
            f1 = min(1.0, f0 + rng.uniform(0.06, 0.16))
            k = rng.randint(2 if esp >= 5 else 1, max(2, esp - 3))
            ax, ay = int(x0 + (x1 - x0) * f0), int(y0 + (y1 - y0) * f0) + k
            bx, by = int(x0 + (x1 - x0) * f1), int(y0 + (y1 - y0) * f1) + k
            linha(t, ax, ay, bx, by, M1 if rng.random() < 0.6 else M3)


def plataforma(t, x0, y0, x1, y1, larg, n_tabuas, rng):
    """Plataforma de tábuas lado a lado: faixa inclinada de (x0,y0) a (x1,y1), `larg` px para baixo, dividida em
    `n_tabuas` com juntas escuras; cada tábua tem o próprio topo claro."""
    passo = larg / float(n_tabuas)
    for i in range(n_tabuas):
        ya = y0 + int(round(i * passo))
        yb = y0 + int(round((i + 1) * passo)) - 1
        e = yb - ya + 1
        poligono(t, [(x0, ya), (x1, y1 + (ya - y0)), (x1, y1 + (yb - y0)), (x0, yb)], M2 if i % 2 else M3)
        linha(t, x0, ya, x1, y1 + (ya - y0), M4)
        linha(t, x0, yb, x1, y1 + (yb - y0), M0)
        if e >= 4:
            linha(t, x0, yb - 1, x1, y1 + (yb - 1 - y0), M1)
        for _ in range(abs(x1 - x0) // 8):
            f0 = rng.random()
            f1 = min(1.0, f0 + rng.uniform(0.05, 0.14))
            k = rng.randint(1, max(1, e - 3))
            ax, ay = int(x0 + (x1 - x0) * f0), ya + int((y1 - y0) * f0) + k
            bx, by = int(x0 + (x1 - x0) * f1), ya + int((y1 - y0) * f1) + k
            linha(t, ax, ay, bx, by, M1 if rng.random() < 0.6 else M4)


# ---------------------------------------------------------------- corda e ferro
def corda(t, x0, y0, x1, y1, rng, esp=2):
    """Corda: linha de 2 px com torção (alterna claro/médio/escuro a cada 2 px ao longo)."""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    x, y = x0, y0
    i = 0
    while True:
        cor = (R2, R3, R2, R1)[(i // 2) % 4]
        for k in range(esp):
            if dx >= -dy:
                t.put(x, y + k, cor if k == 0 else R1)
            else:
                t.put(x + k, y, cor if k == 0 else R1)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
        i += 1


def amarracao(t, x, y, larg, voltas, rng, ponta=True):
    """Amarração de corda num poste: voltas horizontais, a de cima mais clara, ponta solta."""
    for v in range(voltas):
        yy = y + v * 2
        t.hline(x, x + larg - 1, yy, R3 if v == 0 else R2)
        t.hline(x, x + larg - 1, yy + 1, R1)
        t.put(x + larg - 1, yy, R1)
        t.put(x + rng.randint(1, larg - 2), yy, R1 if v == 0 else R3)
    if ponta:
        t.put(x + larg, y + voltas * 2 - 1, R2)
        t.put(x + larg + 1, y + voltas * 2, R2)
        t.put(x + larg + 1, y + voltas * 2 + 1, R1)


def corrente(t, x, y, elos, com_gancho=True):
    """Corrente da Cripta (padrões de montar_marcos) no ferro azul-acinzentado da Pedreira. Devolve o y final."""
    for i in range(elos):
        desenhar_padrao(t, marcos.CORRENTE_ELO, x, y, MAPA_FERRO)
        y += len(marcos.CORRENTE_ELO) - 1
        if i < elos - 1:
            desenhar_padrao(t, marcos.CORRENTE_BARRA, x, y, MAPA_FERRO)
            y += len(marcos.CORRENTE_BARRA)
    if com_gancho:
        desenhar_padrao(t, marcos.CORRENTE_GANCHO, x, y, MAPA_FERRO)
        y += len(marcos.CORRENTE_GANCHO)
    return y


def roldana(t, cx, cy, r):
    """Roldana de ferro: disco com aro, cubo e luz em cima à esquerda."""
    elipse(t, cx, cy, r, r, F1)
    elipse(t, cx, cy, r - 2, r - 2, F2)
    elipse(t, cx, cy, r - 2, r - 2, F2)
    for d in range(-r + 2, 1):
        t.put(cx + d, cy - int((r * r - d * d) ** 0.5) + 1, F3)
    for d in range(1, r - 1):
        t.put(cx + d, cy + int(((r - 2) ** 2 - d * d) ** 0.5), F1)
    elipse(t, cx, cy, 1, 1, F0)
    t.put(cx - 1, cy - 1, F3)


def lanterna(t, x, y, w, h):
    """Lanterna de ferro com vidro e chama acesa. (x, y) = canto superior esquerdo do corpo. Sem glow: o motor faz."""
    cx = x + w // 2
    # argola e tampa
    t.rect(cx - 1, y - 3, cx, y - 1, F2)
    t.put(cx, y - 2, F1)
    t.rect(x + 2, y, x + w - 3, y, F3)
    t.rect(x + 1, y + 1, x + w - 2, y + 2, F1)
    t.hline(x + 2, x + w - 3, y + 1, F2)
    t.rect(x, y + 3, x + w - 1, y + 3, F1)
    t.hline(x + 1, x + w - 3, y + 3, F2)
    # corpo: colunas de ferro nas bordas e no meio, vidro iluminado
    t.rect(x, y + 4, x + w - 1, y + h - 4, F1)
    t.vline(x, y + 4, y + h - 4, F2)
    t.vline(x + w - 1, y + 4, y + h - 4, F0)
    gx0, gx1 = x + 2, x + w - 3
    gy0, gy1 = y + 4, y + h - 4
    t.rect(gx0, gy0, gx1, gy1, L1)
    t.rect(gx0 + 1, gy0 + 1, gx1 - 1, gy1 - 1, L2)
    fy = (gy0 + gy1) // 2
    # chama: gota com miolo claro
    t.rect(cx - 1, fy - 2, cx + 1, fy + 2, G4)
    t.put(cx, fy - 3, G4)
    t.put(cx, fy - 4, L2)
    t.rect(cx, fy - 1, cx, fy + 1, B2)
    t.put(cx - 1, fy, B2)
    t.put(cx - 1, fy + 2, L2)
    t.put(cx + 1, fy + 2, L1)
    t.hline(gx0 + 1, gx1 - 1, gy1, L1)
    # barras verticais do vidro
    t.vline(x + w // 2 + 2, gy0, gy1, F1)
    t.vline(x + w // 2 - 3, gy0, gy1, F1)
    # base
    t.rect(x, y + h - 3, x + w - 1, y + h - 1, F1)
    t.hline(x + 1, x + w - 2, y + h - 3, F2)
    t.hline(x + 1, x + w - 2, y + h - 1, F0)
    t.put(x + 1, y + h - 2, F2)


# ---------------------------------------------------------------- props
def montar_blocos(seed=21):
    rng = random.Random(seed)
    W, H = 106, 84
    t = nova(W, H)
    chao = H - 2
    # bloco de trás à direita, no chão
    e = nova(W, H)
    bloco_calcario(e, 56, chao - 38, 34, 16, 13, 5, rng)
    colar_contornado(t, e)
    # bloco principal, no chão à esquerda, com marcas de cunha na quina
    e = nova(W, H)
    bloco_calcario(e, 2, chao - 34, 50, 18, 14, 6, rng, cunhas=True)
    colar_contornado(t, e)
    # bloco em cima do principal, assentado na face de cima dele, mais à direita (encosta no de trás)
    e = nova(W, H)
    bloco_calcario(e, 26, chao - 50, 30, 12, 10, 5, rng, lascas=1)
    colar_contornado(t, e)
    # bloco inclinado jogado por cima: a quina esquerda na face de cima do bloco, a direita erguida sobre uma lasca
    # (quebra o topo reto da pilha; Jev, rodada 2)
    e = nova(W, H)
    pedra_bruta(e, [(49, chao - 46), (56, chao - 47), (58, chao - 43), (52, chao - 42)], 3, rng)
    colar_contornado(t, e)
    e = nova(W, H)
    bloco_inclinado(e, 40, chao - 50, 28, 10, 6, 18, rng)
    colar_contornado(t, e)
    # bloco caído de lado, na frente à direita: alto e estreito, com a fileira de cunhas na aresta esquerda
    e = nova(W, H)
    bloco_calcario(e, 76, chao - 30, 18, 24, 5, 4, rng, cunhas_lado=True, lascas=1, mordidas=0)
    colar_contornado(t, e)
    # lascas grandes no chão ao redor da base (tamanhos variados)
    for pts, alt in (
        ([(58, chao - 7), (68, chao - 9), (73, chao - 5), (64, chao - 2)], 3),
        ([(96, chao - 6), (103, chao - 8), (105, chao - 3), (99, chao - 1)], 3),
        ([(0, chao - 5), (6, chao - 7), (9, chao - 3), (4, chao - 1)], 2),
        ([(44, chao - 2), (50, chao - 4), (53, chao - 1)], 2),
        ([(90, chao - 2), (95, chao - 3), (96, chao)], 1),
    ):
        e = nova(W, H)
        pedra_bruta(e, pts, alt, rng)
        colar_contornado(t, e)
    e = nova(W, H)
    entulho(e, 0, 104, chao, rng, 16)
    colar_contornado(t, e)
    t.encaixar_paleta(PALETA)
    return recortar(t)


def montar_andaime(seed=33):
    rng = random.Random(seed)
    W, H = 106, 136
    t = nova(W, H)
    chao = H - 2
    LP = 8
    xs = (6, 48, 90)
    # postes: o da esquerda está partido na altura da travessa de cima
    for i, x in enumerate(xs):
        e = nova(W, H)
        if i == 0:
            poste(e, x, 40, chao, LP, rng, quebrado_topo=True)
        elif i == 1:
            poste(e, x, 4, chao, LP, rng)
        else:
            poste(e, x, 10, chao, LP, rng)
        colar_contornado(t, e)
    # travessas horizontais amarradas na frente dos postes
    e = nova(W, H)
    travessa(e, 1, 101, 50, 6, rng)
    colar_contornado(t, e)
    e = nova(W, H)
    travessa(e, 42, 103, 22, 6, rng)
    colar_contornado(t, e)
    # escora diagonal do pé esquerdo até o poste do meio
    e = nova(W, H)
    barra_inclinada(e, 9, 104, 52, 58, 5, rng)
    colar_contornado(t, e)
    # plataforma de tábuas: presa à direita na travessa de baixo, caída à esquerda
    e = nova(W, H)
    plataforma(e, 14, 78, 96, 46, 14, 3, rng)
    colar_contornado(t, e)
    # topo do poste partido caído no chão, com a ponta lascada
    e = nova(W, H)
    barra_inclinada(e, 12, chao - 11, 44, chao - 5, 5, rng)
    for dy in range(5):
        a = rng.randint(0, 3)
        for dx in range(a):
            e.apagar(12 + dx, chao - 11 + dy)
        e.put(12 + a, chao - 11 + dy, M4)
    colar_contornado(t, e)
    # amarrações nas juntas
    e = nova(W, H)
    amarracao(e, 47, 20, LP + 2, 3, rng)
    amarracao(e, 89, 20, LP + 2, 3, rng)
    amarracao(e, 47, 48, LP + 2, 3, rng)
    amarracao(e, 5, 48, LP + 2, 3, rng)
    amarracao(e, 89, 48, LP + 2, 3, rng)
    colar_contornado(t, e)
    # corda pendurada da travessa de cima, balançando e com a ponta esgarçada
    e = nova(W, H)
    corda(e, 70, 27, 67, 56, rng)
    corda(e, 67, 56, 72, 86, rng)
    e.put(72, 88, R1)
    e.put(74, 88, R2)
    e.put(73, 89, R1)
    colar_contornado(t, e)
    e = nova(W, H)
    entulho(e, 2, 102, chao, rng, 6)
    colar_contornado(t, e)
    t.encaixar_paleta(PALETA)
    return recortar(t)


def roda(t, cx, cy, r, rng):
    """Roda de madeira com aro de ferro, vista de lado."""
    elipse(t, cx, cy, r, r, F1)
    elipse(t, cx, cy, r - 2, r - 2, M2)
    for d in range(-r + 1, 1):
        t.put(cx + d, cy - int((r * r - d * d) ** 0.5) + 1, F3)
    for d in range(0, r - 1):
        t.put(cx + d, cy + int((r * r - d * d) ** 0.5) - 1, F0)
    for y in range(cy - r + 3, cy + r - 2):
        for x in range(cx - r + 3, cx + r - 2):
            if 3 < math.hypot(x - cx, y - cy) < r - 3 and t.cor(x, y) == M2:
                t.apagar(x, y)
    for ang in range(0, 360, 45):
        ex = cx + int(round(math.cos(math.radians(ang)) * (r - 2)))
        ey = cy + int(round(math.sin(math.radians(ang)) * (r - 2)))
        linha(t, cx, cy, ex, ey, M1 if 45 <= ang <= 180 else M3)
        linha(t, cx, cy + 1, ex, ey + 1, M1)
    elipse(t, cx, cy, 3, 3, M1)
    t.put(cx - 1, cy - 1, M3)
    t.rect(cx, cy, cx + 1, cy + 1, F1)
    t.put(cx, cy, F2)


def roda_quebrada(t, cx, cy, r, rng):
    """Roda com um quarto arrancado (de 3 h a 6 h), raios partidos à mostra."""
    roda(t, cx, cy, r, rng)
    for y in range(cy + 1, cy + r + 1):
        for x in range(cx + 1, cx + r + 1):
            if math.hypot(x - cx, y - cy) > 3.5:
                t.apagar(x, y)
    # pontas de raio e de aro partidas
    linha(t, cx + 3, cy + 1, cx + 6, cy + 3, M4)
    t.put(cx + 7, cy + 4, M3)
    linha(t, cx + 1, cy + 4, cx + 2, cy + 7, M4)
    t.put(cx + r - 1, cy + 1, F2)
    t.put(cx + 1, cy + r - 1, F2)


def montar_carrinho(seed=45):
    rng = random.Random(seed)
    W, H = 102, 70
    t = nova(W, H)
    chao = H - 2
    # --- caçamba desenhada de pé numa tela própria, depois inclinada para a direita (lado da roda quebrada)
    c = nova(86, 56)
    bx0, bx1 = 14, 70          # caixa da caçamba
    topo, fundo = 14, 42       # topo da parede de trás, base da parede da frente
    prof = 10                  # quanto se vê do interior (face de cima)
    c.rect(bx0 + 2, topo + 2, bx1 - 2, topo + prof + 1, M1)       # chão da caçamba em sombra
    c.rect(bx0 + 2, topo + 2, bx1 - 2, topo + 3, M0)
    c.rect(bx0, topo, bx1, topo + 1, M3)                          # borda de cima da parede de trás
    c.hline(bx0, bx1, topo, M4)
    c.rect(bx0, topo, bx0 + 1, topo + prof + 2, M3)               # laterais vistas por dentro
    c.rect(bx1 - 1, topo, bx1, topo + prof + 2, M1)
    fy0 = topo + prof + 2                                         # parede da frente: tábuas horizontais
    c.rect(bx0, fy0, bx1, fundo, M2)
    c.hline(bx0, bx1, fy0, M4)
    c.hline(bx0, bx1, fy0 + 1, M3)
    for yy in range(fy0 + 7, fundo - 2, 7):
        c.hline(bx0, bx1, yy, M0)
        c.hline(bx0, bx1, yy + 1, M3)
    c.hline(bx0, bx1, fundo, M0)
    c.hline(bx0, bx1, fundo - 1, M1)
    for _ in range(28):
        px, py = rng.randint(bx0 + 1, bx1 - 1), rng.randint(fy0 + 2, fundo - 2)
        if c.cor(px, py) == M2:
            c.hline(px, px + rng.randint(1, 4), py, M1 if rng.random() < 0.6 else M3)
    # nó e racha na tábua
    c.rect(40, fy0 + 3, 41, fy0 + 4, M1)
    c.put(41, fy0 + 4, M0)
    rachadura(c, 56, fy0 + 9, 6, rng, M0, None, mascara=lambda px, py: c.cor(px, py) in (M2, M1, M3), dy_pref=0)
    # cantoneiras de ferro nas quinas da frente
    for xx in (bx0, bx1 - 2):
        c.rect(xx, fy0, xx + 2, fundo, F1)
        c.vline(xx, fy0, fundo, F2)
        c.put(xx + 1, fy0 + 3, F3)
        c.put(xx + 1, fundo - 5, F3)
    # pedras na caçamba: três, à mostra acima da borda
    pedra_bruta(c, [(22, 7), (36, 5), (44, 9), (38, 15), (24, 14)], 7, rng)
    pedra_bruta(c, [(44, 9), (58, 6), (66, 12), (56, 17)], 6, rng)
    c.contorno()
    # eixo e roda boa (lado esquerdo), atrás da caçamba
    e = nova(W, H)
    e.rect(14, chao - 25, 30, chao - 23, F1)
    e.hline(14, 30, chao - 25, F2)
    roda(e, 14, chao - 18, 13, rng)
    colar_contornado(t, e)
    # caçamba inclinada: a quina esquerda sobre o eixo, a direita no chão
    ci = cisalhar(c, bx0, 0.26)
    dy_dir = int(round((bx1 - bx0) * 0.26))
    oy = chao - (fundo + dy_dir) - 1
    t.colar(ci, 6, oy)
    # roda quebrada, de pé, encostada no lado direito da caçamba
    e = nova(W, H)
    roda_quebrada(e, 86, chao - 11, 11, rng)
    colar_contornado(t, e)
    # varais (dois cabos) caídos no chão na frente, saindo de baixo da caçamba para a esquerda
    e = nova(W, H)
    barra_inclinada(e, 2, chao - 7, 34, chao - 13, 3, rng, veios=False)
    barra_inclinada(e, 6, chao - 1, 36, chao - 7, 3, rng, veios=False)
    colar_contornado(t, e)
    # bloco derramado pela boca, na frente à direita
    e = nova(W, H)
    pedra_bruta(e, [(58, chao - 11), (70, chao - 13), (76, chao - 7), (68, chao - 3), (58, chao - 5)], 5, rng)
    colar_contornado(t, e)
    e = nova(W, H)
    entulho(e, 38, 98, chao, rng, 7)
    colar_contornado(t, e)
    t.encaixar_paleta(PALETA)
    return recortar(t)


def pe_em_a(t, cx, y_topo, y_chao, abertura, larg, rng):
    """Pé em A: dois postes inclinados que se encontram no topo, travessa a 2/3 da altura, amarrações."""
    e = nova(t.w, t.h)
    for lado in (-1, 1):
        x_base = cx + lado * abertura // 2
        xt0, xb0 = cx - larg // 2, x_base - larg // 2
        poligono(e, [(xt0, y_topo), (xt0 + larg - 1, y_topo), (xb0 + larg - 1, y_chao), (xb0, y_chao)], M2)
        cols = tons_poste(larg)
        for i, c in enumerate(cols):
            if c != M2:
                linha(e, xt0 + i, y_topo, xb0 + i, y_chao, c)
        for _ in range((y_chao - y_topo) // 3):
            f = rng.random()
            px = int(xt0 + (xb0 - xt0) * f) + rng.randint(1, larg - 2)
            py = int(y_topo + (y_chao - y_topo) * f)
            comp = rng.randint(2, 6)
            atual = e.cor(px, py) if e.opaco(px, py) else None
            if atual == M2:
                e.vline(px, py, py + comp, M1 if rng.random() < 0.6 else M3)
            elif atual == M3 and rng.random() < 0.5:
                e.vline(px, py, py + comp, M4)
        # nó
        f = rng.uniform(0.3, 0.7)
        nx, ny = int(xt0 + (xb0 - xt0) * f) + 2, int(y_topo + (y_chao - y_topo) * f)
        e.rect(nx, ny, nx + 1, ny + 1, M1)
        e.put(nx + 1, ny + 1, M0)
        quebrar_base(e, xb0, y_chao, larg, rng)
    colar_contornado(t, e)
    ym = y_topo + (y_chao - y_topo) * 2 // 3
    e = nova(t.w, t.h)
    meia = abertura // 2 * (ym - y_topo) // (y_chao - y_topo)
    travessa(e, cx - meia - 3, cx + meia + 3, ym, 6, rng)
    colar_contornado(t, e)
    e = nova(t.w, t.h)
    amarracao(e, cx - meia - 4, ym - 2, larg, 4, rng)
    amarracao(e, cx + meia - larg + 4, ym - 2, larg, 4, rng, ponta=False)
    colar_contornado(t, e)


def montar_portico(seed=57):
    rng = random.Random(seed)
    W, H = 156, 176
    t = nova(W, H)
    chao = H - 2
    y_topo = 16
    LP = 9
    pe_em_a(t, 26, y_topo + 2, chao, 40, LP, rng)
    pe_em_a(t, W - 28, y_topo + 2, chao, 40, LP, rng)
    # viga de cima: tronco grosso apoiado nos dois pés, com cintas de ferro
    e = nova(W, H)
    travessa(e, 1, W - 2, y_topo - 10, 13, rng)
    for x in (12, W - 18):
        e.rect(x, y_topo - 10, x + 3, y_topo + 2, F1)
        e.vline(x, y_topo - 10, y_topo + 2, F2)
        e.put(x + 1, y_topo - 9, F3)
        e.put(x + 1, y_topo - 4, F3)
    colar_contornado(t, e)
    e = nova(W, H)
    amarracao(e, 21, y_topo + 3, LP + 2, 4, rng)
    amarracao(e, W - 32, y_topo + 3, LP + 2, 4, rng, ponta=False)
    colar_contornado(t, e)
    # roldana pendurada no meio da viga por uma alça de ferro
    cx = W // 2
    e = nova(W, H)
    e.rect(cx - 1, y_topo + 3, cx, y_topo + 9, F1)
    e.vline(cx - 1, y_topo + 3, y_topo + 9, F2)
    roldana(e, cx, y_topo + 16, 7)
    colar_contornado(t, e)
    # corrente da roldana até o gancho
    e = nova(W, H)
    y_fim = corrente(e, cx - 3, y_topo + 23, 4, com_gancho=True)
    colar_contornado(t, e)
    # bloco meio lavrado pendurado por cordas: duas cordas do gancho às quinas, duas voltas por baixo
    bw, bh, bd = 36, 20, 9
    bx, by = cx - bw // 2, y_fim + 9
    e = nova(W, H)
    corda(e, cx, y_fim - 3, bx + 3, by + 1, rng)
    corda(e, cx + 1, y_fim - 3, bx + bw + 1, by - 2, rng)
    colar_contornado(t, e)
    e = nova(W, H)
    bloco_calcario(e, bx, by, bw, bh, bd, 4, rng, cunhas=True, lascas=1, mordidas=1)
    for x in (bx + 6, bx + bw - 9):
        e.vline(x, by, by + bd + bh - 1, R2)
        e.vline(x + 1, by, by + bd + bh - 1, R1)
        e.put(x, by + 2, R3)
        e.put(x, by + bd + 3, R3)
    colar_contornado(t, e)
    # corda sobrando, pendurada da travessa do pé direito e enrolada na ponta
    e = nova(W, H)
    ym = y_topo + 2 + (chao - y_topo - 2) * 2 // 3
    corda(e, W - 20, ym + 6, W - 22, ym + 26, rng)
    amarracao(e, W - 25, ym + 26, 7, 3, rng, ponta=False)
    colar_contornado(t, e)
    e = nova(W, H)
    entulho(e, 4, W - 6, chao, rng, 8)
    colar_contornado(t, e)
    t.encaixar_paleta(PALETA)
    return recortar(t)


def montar_poste_lanterna(seed=69):
    rng = random.Random(seed)
    W, H = 46, 116
    t = nova(W, H)
    chao = H - 2
    px = 4
    LP = 7
    e = nova(W, H)
    poste(e, px, 10, chao, LP, rng)
    colar_contornado(t, e)
    # braço horizontal no topo, escora diagonal e amarração
    e = nova(W, H)
    travessa(e, px, px + 30, 10, 5, rng)
    colar_contornado(t, e)
    e = nova(W, H)
    barra_inclinada(e, px + LP, 28, px + 24, 15, 3, rng, veios=False)
    colar_contornado(t, e)
    e = nova(W, H)
    amarracao(e, px - 1, 12, LP + 2, 3, rng)
    colar_contornado(t, e)
    # gancho de ferro na ponta do braço e correntinha
    e = nova(W, H)
    e.rect(px + 26, 15, px + 27, 17, F1)
    e.put(px + 26, 15, F2)
    y = corrente(e, px + 24, 18, 1, com_gancho=False)
    colar_contornado(t, e)
    e = nova(W, H)
    lanterna(e, px + 19, y + 3, 14, 20)
    colar_contornado(t, e)
    e = nova(W, H)
    entulho(e, 1, 18, chao, rng, 4)
    colar_contornado(t, e)
    t.encaixar_paleta(PALETA)
    return recortar(t)


# ---------------------------------------------------------------- portão (alvenaria, grade e guindaste)
def fiada_blocos(t, x0, x1, fy0, h, d, rng, evitar=(), cunhas_p=0.3, larg=(30, 52)):
    """Uma fiada de blocos de calcário encostados de x0 a x1 (inclusive): face frontal de fy0 a fy0+h-1, face de cima
    `d` px acima (nas fiadas de baixo ela fica escondida pela fiada seguinte). Juntas verticais de 1 px em C0, fugindo
    das juntas da fiada de baixo (`evitar`) para desencontrar. Devolve as juntas desta fiada."""
    juntas = []
    x = x0
    while x <= x1:
        w = rng.randint(*larg)
        for _ in range(3):                      # junta cai perto de uma da fiada de baixo: alarga ou encurta o bloco
            if any(abs(x + w - j) < 8 for j in evitar):
                w += rng.choice((-9, 9))
        w = max(18, w)
        if x1 - (x + w) < 18:                   # o último bloco pega o resto
            w = x1 - x + 1
        ini = rng.randint(h // 3, h * 3 // 5)     # altura da faixa clara varia por bloco (sem listra contínua)
        bloco_calcario(t, x, fy0 - d, w, h, d, 0, rng, cunhas=rng.random() < cunhas_p, lascas=0, mordidas=0,
                       faixa=(ini, min(h - 4, ini + h // 4)))
        if d >= 16 and rng.random() < 0.6:      # junta cruzada na face de cima (bloco mais curto na profundidade)
            jy = fy0 - d + rng.randint(9, d - 9)
            t.hline(x + 1, x + w - 2, jy, C0)
            t.hline(x + 1, x + w - 2, jy + 1, C4)
        x += w
        if x <= x1:
            t.vline(x, fy0 - d, fy0 + h - 1, C0)
            t.vline(x + 1, fy0 + 1, fy0 + h // 3, C3)    # fio de luz no bloco à direita da junta
            juntas.append(x)
            x += 1
    return juntas


def lateral_parede(t, x, y_topo, y_base, s, juntas_h=()):
    """Lateral direita de uma parede de blocos (face em sombra, chapada), subindo 1 px por coluna como nos blocos
    soltos; `juntas_h` = linhas (y) das juntas horizontais, marcadas em C0 na lateral."""
    for i in range(s):
        cx = x + i
        t.vline(cx, y_topo - i - 1, y_base - i - 1, C1)
        t.put(cx, y_topo - i - 1, C3 if i < 2 else C2)
        t.put(cx, y_base - i - 1, C0)
        for jy in juntas_h:
            t.put(cx, jy - i - 1, C0)


def bastiao(t, chao, alt, d_topo, s, rng, corpo, plinto, alt_plinto, lado):
    """Bastião maciço de blocos de calcário: `corpo` = (x0, x1) da face frontal acima do plinto, `plinto` = (x0, x1)
    das fiadas de baixo (sai `lado`: -1 para a esquerda, +1 para a direita), lateral direita de `s` px. Fiadas de baixo
    para cima com juntas desencontradas; a fiada de cima traz a face de cima (d_topo). Devolve (y da face de cima,
    y do topo da face frontal, y do topo do plinto)."""
    e = nova(t.w, t.h)
    alturas = []
    resto = alt
    while resto > 0:
        a = rng.randint(19, 25)
        if resto - a < 12:
            a = resto
        alturas.append(a)
        resto -= a
    fy1 = chao
    juntas = []
    juntas_h = []
    y_plinto = None
    for i, a in enumerate(alturas):
        fy0 = fy1 - a + 1
        ultima = i == len(alturas) - 1
        no_plinto = chao - fy1 < alt_plinto
        x0, x1 = plinto if no_plinto else corpo
        if no_plinto and chao - fy0 + 1 >= alt_plinto:          # topo do plinto: a fiada acima já é do corpo
            y_plinto = fy0
        d = d_topo if ultima else 2
        juntas = fiada_blocos(e, x0, x1, fy0, a, d, rng, evitar=juntas, cunhas_p=0.18 if not ultima else 0.7)
        if not ultima:
            juntas_h.append(fy0 - 1)
        else:
            for px in range(x0, x1 + 1):         # quina da face de cima com a frontal: aresta de luz contínua
                if e.cor(px, fy0) == C3:
                    e.put(px, fy0, C4)
        fy1 = fy0 - 1
    y_topo = fy1 + 1 - d_topo
    # degrau do plinto: face de cima fina na parte que sobra para fora do corpo
    if y_plinto is not None and plinto != corpo:
        if lado < 0:
            px0, px1 = plinto[0], corpo[0] - 1
        else:
            px0, px1 = corpo[1] + 1, plinto[1]
        e.rect(px0, y_plinto - 4, px1, y_plinto - 1, C3)
        e.hline(px0, px1, y_plinto - 4, C4)
        if lado < 0:
            e.vline(px0, y_plinto - 4, y_plinto - 1, C4)
        for px in range(px0, px1 + 1):
            if rng.random() < 0.3:
                e.put(px, y_plinto - rng.randint(1, 3), C2)
    # lateral direita: do corpo (toda a altura) e do plinto (quando ele sai para a direita)
    if lado > 0 and plinto != corpo:
        lateral_parede(e, plinto[1] + 1, y_plinto, chao, s, [j for j in juntas_h if j > y_plinto])
        lateral_parede(e, corpo[1] + 1, y_topo, y_plinto - 1, s, [j for j in juntas_h if j < y_plinto])
        # quina do degrau na lateral
        for i in range(s):
            e.put(corpo[1] + 1 + i, y_plinto - 1 - i - 1, C3)
    else:
        lateral_parede(e, corpo[1] + 1, y_topo, chao, s, juntas_h)
    # mordidas na silhueta: topo da face de cima e aresta externa
    xa, xb = (plinto[0], corpo[1]) if lado < 0 else (corpo[0], plinto[1])
    morder(e, [(px, y_topo, 0, 1) for px in range(corpo[0] + 4, corpo[1] - 4)], C2, rng, 4, larg=(2, 4), prof=(1, 2))
    x_ext = corpo[0] if lado < 0 else corpo[1] + s
    dx_in = 1 if lado < 0 else -1
    morder(e, [(x_ext, py, dx_in, 0) for py in range(y_topo + 6, y_plinto - 6)], C2, rng, 3, larg=(2, 4), prof=(1, 2))
    colar_contornado(t, e)
    return y_topo, fy1 + 1, y_plinto


def grade_ferro(t, x0, x1, y_topo, y_fim, passo, travessas):
    """Grade de ferro (portcullis) levantada: barras verticais de 3 px com ponta para baixo, travessas horizontais com
    rebites nos cruzamentos. Vazada entre as barras (alfa binário)."""
    xs = list(range(x0, x1 - 2, passo))
    for x in xs:
        t.vline(x, y_topo, y_fim - 3, F3)
        t.vline(x + 1, y_topo, y_fim - 3, F2)
        t.vline(x + 2, y_topo, y_fim - 3, F1)
        t.put(x, y_fim - 2, F2)
        t.put(x + 1, y_fim - 2, F1)
        t.put(x + 2, y_fim - 2, F0)
        t.put(x + 1, y_fim - 1, F1)
        t.put(x + 1, y_fim, F0)
    for ty in travessas:
        t.hline(x0 - 2, xs[-1] + 4, ty, F3)
        t.hline(x0 - 2, xs[-1] + 4, ty + 1, F2)
        t.hline(x0 - 2, xs[-1] + 4, ty + 2, F2)
        t.hline(x0 - 2, xs[-1] + 4, ty + 3, F1)
        for x in xs:
            t.put(x + 1, ty + 1, F3)
            t.put(x + 1, ty + 2, F0)
        t.put(x0 - 2, ty + 3, F0)
        t.put(xs[-1] + 4, ty, F2)
    return xs


CAVEIRA = [
    "..bbbb..",
    ".bBBBbs.",
    "bBBBBBbs",
    "bBBBBBbs",
    "bKKBKKbs",
    ".bKbbKs.",
    "..bsbs..",
    "..sKsK..",
]
MAPA_CAVEIRA = {"K": K0, "B": B2, "b": C4, "s": C3}


def caveira_pequena(t, x, y):
    desenhar_padrao(t, CAVEIRA, x, y, MAPA_CAVEIRA)


def pedra_chave(t, cx, y_cima, y_frente0, y_frente1, rng):
    """Pedra-chave da verga: bloco trapezoidal (mais largo em cima) saltado para a frente, com face de cima própria e
    uma caveirinha entalhada no meio."""
    meia_c, meia_b = 13, 9
    t.rect(cx - meia_c, y_cima, cx + meia_c, y_frente0 - 1, C3)
    t.hline(cx - meia_c, cx + meia_c, y_cima, C4)
    t.vline(cx - meia_c, y_cima, y_frente0 - 1, C4)
    poligono(t, [(cx - meia_c, y_frente0), (cx + meia_c, y_frente0), (cx + meia_b, y_frente1), (cx - meia_b, y_frente1)], C2)
    for y in range(y_frente0, y_frente1 + 1):
        f = (y - y_frente0) / float(y_frente1 - y_frente0)
        meia = int(round(meia_c + (meia_b - meia_c) * f))
        if f > 0.62:
            t.hline(cx - meia, cx + meia, y, C1)
        t.put(cx - meia, y, C4 if f < 0.7 else C3)
        t.put(cx + meia, y, C0)
        if y == y_frente1:
            t.hline(cx - meia, cx + meia, y, C0)
    t.hline(cx - meia_c + 1, cx + meia_c - 1, y_frente0, C3)
    for _ in range(14):
        px, py = rng.randint(cx - meia_b + 1, cx + meia_b - 1), rng.randint(y_frente0 + 1, y_frente1 - 2)
        c = t.cor(px, py)
        if c == C2 and rng.random() < 0.5:
            t.put(px, py, C3 if rng.random() < 0.4 else C1)
        elif c == C1:
            t.put(px, py, C2 if rng.random() < 0.5 else C0)
    caveira_pequena(t, cx - 4, y_frente0 + 5)


def montar_portao(seed=81):
    """Portão da Pedreira (fundo da luta contra o elite): dois bastiões maciços de calcário com um vão livre de 2 tiles
    no meio, verga grossa com pedra-chave, grade de ferro levantada pendurada em correntes e guindaste de madeira no
    topo do bastião direito, com roldana e contrapeso de pedra."""
    rng = random.Random(seed)
    W, H = 416, 256
    t = nova(W, H)
    chao = H - 2
    ALT, D_TOPO, S = 176, 36, 6
    # bastiões: 143 px cada (corpo 129 + lateral 6 + degrau do plinto 8), vão de 128 px (x 144..271)
    ye_topo, ye_frente, ye_plinto = bastiao(t, chao, ALT, D_TOPO, S, rng, corpo=(9, 137), plinto=(1, 137),
                                            alt_plinto=66, lado=-1)
    yd_topo, yd_frente, yd_plinto = bastiao(t, chao, ALT, D_TOPO, S, rng, corpo=(272, 400), plinto=(272, 408),
                                            alt_plinto=66, lado=+1)
    # blocos soltos em cima do bastião esquerdo
    e = nova(W, H)
    bloco_calcario(e, 30, ye_topo + 6, 30, 12, 9, 4, rng, cunhas=True, lascas=1, mordidas=1)
    colar_contornado(t, e)
    e = nova(W, H)
    bloco_calcario(e, 66, ye_topo + 14, 22, 10, 7, 3, rng, lascas=1, mordidas=0)
    colar_contornado(t, e)
    e = nova(W, H)
    pedra_bruta(e, [(96, ye_topo + 22), (106, ye_topo + 20), (112, ye_topo + 25), (104, ye_topo + 29)], 3, rng)
    colar_contornado(t, e)
    # grade de ferro levantada (atrás da verga, que esconde o topo dela)
    y_verga_baixo = chao - 124                   # borda de baixo da verga: 124 px acima do chão
    y_pontas = chao - 64                         # pontas da grade: 64 px acima do chão
    e = nova(W, H)
    grade_ferro(e, 151, 265, y_verga_baixo - 8, y_pontas, 16, (y_verga_baixo + 9, y_verga_baixo + 30, y_verga_baixo + 50))
    colar_contornado(t, e)
    # verga: bloco grosso de calcário com marcas de cunha, apoiado nas duas faces frontais
    vh, vd = 28, 10
    vy = y_verga_baixo - vh - vd + 1
    cx = 208
    # correntes de içar: da barra acima da verga até a travessa de cima da grade, passando por trás da verga (entram
    # por ranhuras); desenhadas antes da verga para ela cobrir o meio
    y_barra = vy - 12
    e = nova(W, H)
    e.rect(176, y_barra, 240, y_barra + 2, F2)
    e.hline(176, 240, y_barra, F3)
    e.hline(177, 239, y_barra + 2, F1)
    for x in (176, 236):
        y = y_barra + 3
        while y + 6 <= y_verga_baixo + 10:
            y = corrente(e, x, y, 1, com_gancho=False)
            desenhar_padrao(e, marcos.CORRENTE_BARRA, x, y, MAPA_FERRO)
            y += 2
    colar_contornado(t, e)
    e = nova(W, H)
    bloco_calcario(e, 130, vy, 152, vh, vd, 4, rng, cunhas=True, lascas=0, mordidas=2)
    for x in (176, 236):                         # ranhuras na face de cima da verga por onde as correntes descem
        t.rect(x - 1, vy + 2, x + 5, vy + 4, C0)
        t.hline(x, x + 4, vy + 5, C4)
    colar_contornado(t, e)
    e = nova(W, H)
    pedra_chave(e, cx, vy, vy + vd + 6, y_verga_baixo + 4, rng)
    colar_contornado(t, e)
    # caveirinhas em cima da verga, perto das pontas (detalhe pequeno)
    e = nova(W, H)
    caveira_pequena(e, 146, vy - 7)
    caveira_pequena(e, 268, vy - 6)
    colar_contornado(t, e)
    # guindaste no topo do bastião direito: poste, viga em balanço sobre o vão, escora, amarrações
    y_viga = chao - 251
    LP = 10
    e = nova(W, H)
    poste(e, 311, y_viga + 9, yd_topo + 18, LP, rng)
    colar_contornado(t, e)
    e = nova(W, H)
    travessa(e, 196, 358, y_viga, 10, rng)
    for x in (204, 346):                         # cintas de ferro nas pontas da viga
        e.rect(x, y_viga, x + 2, y_viga + 9, F1)
        e.vline(x, y_viga, y_viga + 9, F2)
        e.put(x + 1, y_viga + 1, F3)
        e.put(x + 1, y_viga + 6, F3)
    colar_contornado(t, e)
    e = nova(W, H)
    barra_inclinada(e, 236, y_viga + 10, 311, yd_topo + 2, 7, rng)
    colar_contornado(t, e)
    e = nova(W, H)
    amarracao(e, 310, y_viga + 11, LP + 2, 4, rng)
    amarracao(e, 310, yd_topo + 3, LP + 2, 3, rng, ponta=False)
    colar_contornado(t, e)
    # pé do poste: calço de pedra na face de cima
    e = nova(W, H)
    bloco_calcario(e, 305, yd_topo + 15, 23, 6, 5, 3, rng, rachado=False, lascas=0, mordidas=0)
    colar_contornado(t, e)
    # roldana pendurada na ponta da viga e corrente até a barra de içar
    e = nova(W, H)
    e.rect(cx - 1, y_viga + 10, cx, y_viga + 15, F1)
    e.vline(cx - 1, y_viga + 10, y_viga + 15, F2)
    roldana(e, cx, y_viga + 22, 7)
    colar_contornado(t, e)
    e = nova(W, H)
    y = y_viga + 29
    while y + 6 <= y_barra:
        y = corrente(e, cx - 2, y, 1, com_gancho=False)
        if y + 8 <= y_barra:
            desenhar_padrao(e, marcos.CORRENTE_BARRA, cx - 2, y, MAPA_FERRO)
            y += 2
    colar_contornado(t, e)
    # contrapeso: bloco de pedra pendurado por corrente na ponta direita da viga
    e = nova(W, H)
    y = corrente(e, 345, y_viga + 10, 3, com_gancho=True)
    colar_contornado(t, e)
    e = nova(W, H)
    bloco_calcario(e, 335, y + 2, 24, 13, 8, 3, rng, cunhas=False, lascas=1, mordidas=0)
    e.vline(347, y + 2, y + 2 + 8 + 12, R2)
    e.vline(348, y + 2, y + 2 + 8 + 12, R1)
    colar_contornado(t, e)
    # lascas e entulho no pé dos bastiões (fora do vão)
    for pts, alt in (
        ([(4, chao - 6), (14, chao - 8), (19, chao - 4), (10, chao - 1)], 3),
        ([(120, chao - 5), (128, chao - 7), (133, chao - 3), (126, chao - 1)], 2),
        ([(286, chao - 6), (296, chao - 9), (302, chao - 4), (292, chao - 1)], 3),
        ([(392, chao - 4), (401, chao - 6), (406, chao - 2), (398, chao)], 2),
    ):
        e = nova(W, H)
        pedra_bruta(e, pts, alt, rng)
        colar_contornado(t, e)
    e = nova(W, H)
    entulho(e, 2, 134, chao, rng, 10)
    entulho(e, 282, 412, chao, rng, 10)
    colar_contornado(t, e)
    t.encaixar_paleta(PALETA)
    return recortar(t)


# ---------------------------------------------------------------- lascas de bloco
def lasca_cortada(t, x, y, w, h, alt, rng):
    """Fragmento angular de bloco cortado: topo de 4 ou 5 vértices com arestas retas, face de cima clara, lateral
    escura, base funda (pedra_bruta), e uma faceta diagonal quebrada no topo."""
    pts = [(x, y + rng.randint(2, 4)), (x + w // 2 - rng.randint(0, 2), y), (x + w - 1, y + rng.randint(1, 3)),
           (x + w - rng.randint(2, 4), y + h - 1), (x + rng.randint(1, 3), y + h - 2)]
    if rng.random() < 0.4:
        pts.pop(rng.choice((1, 4)))
    pedra_bruta(t, pts, alt, rng)
    # faceta: um lado do topo vira C2 com aresta C4 (quebra em outro plano)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    fx = (min(xs) + max(xs)) // 2 + rng.randint(1, 3)
    for py in range(min(ys), max(ys) + 1):
        for px in range(fx, max(xs) + 1):
            if t.opaco(px, py) and t.cor(px, py) in (C3, C4):
                t.put(px, py, C2)
        if t.opaco(fx, py) and t.cor(fx, py) == C2:
            t.put(fx, py, C4)


def sombra_chao(t, cor=C0):
    """Sombra própria de 1 tom colada embaixo-direita do que já está desenhado (1 px), fora do contorno."""
    op = t.a[..., 3] > 0
    somb = np.zeros_like(op)
    somb[1:, :] |= op[:-1, :]
    somb[1:, 1:] |= op[:-1, :-1]
    somb[:, 1:] |= op[:, :-1]
    ys, xs = np.where(somb & ~op)
    for x, y in zip(xs, ys):
        t.put(int(x), int(y), cor)


def montar_lascas(variante, seed=93):
    rng = random.Random(seed + variante * 7)
    if variante == 0:
        W, H = 26, 18
        pecas = [(2, 2, 21, 9, 4)]
    elif variante == 1:
        W, H = 38, 22
        pecas = [(2, 6, 17, 9, 4), (16, 2, 19, 10, 3)]
    else:
        W, H = 48, 26
        pecas = [(14, 2, 21, 11, 5), (1, 10, 14, 7, 3), (34, 12, 12, 6, 2)]
    t = nova(W, H)
    for x, y, w, h, alt in pecas:
        e = nova(W, H)
        lasca_cortada(e, x, y, w, h, alt, rng)
        colar_contornado(t, e)
    sombra_chao(t)
    t.encaixar_paleta(PALETA)
    return recortar(t)


# ---------------------------------------------------------------- saída
def recortar(t):
    """Caixa justa; o pivô fica no centro da borda de baixo."""
    b = t.bbox()
    return t.a[b[1]:b[3] + 1, b[0]:b[2] + 1].copy()


def main():
    destino_previas = None
    if "--previas" in sys.argv:
        destino_previas = sys.argv[sys.argv.index("--previas") + 1]
    props = [
        ("pedreira_blocos", montar_blocos()),
        ("pedreira_andaime", montar_andaime()),
        ("pedreira_carrinho", montar_carrinho()),
        ("pedreira_portico", montar_portico()),
        ("pedreira_poste_lanterna", montar_poste_lanterna()),
        ("pedreira_portao", montar_portao()),
        ("pedreira_lasca_0", montar_lascas(0)),
        ("pedreira_lasca_1", montar_lascas(1)),
        ("pedreira_lasca_2", montar_lascas(2)),
    ]
    os.makedirs(PROPS, exist_ok=True)
    for nome, arr in props:
        im = Image.fromarray(arr, "RGBA")
        assert set(np.unique(arr[..., 3]).tolist()) <= {0, 255}
        im.save(os.path.join(PROPS, nome + ".png"))
        print(f"{nome} {im.width}x{im.height} {im.width // 2},{im.height}")
    if destino_previas:
        os.makedirs(destino_previas, exist_ok=True)
        for nome, arr in props:
            im = Image.fromarray(arr, "RGBA")
            for fundo, tag in (((66, 82, 40, 255), "grama"), ((112, 92, 62, 255), "poeira")):
                base = Image.new("RGBA", (im.width + 12, im.height + 12), fundo)
                base.alpha_composite(im, (6, 6))
                base.resize((base.width * 3, base.height * 3), Image.NEAREST).save(
                    os.path.join(destino_previas, f"{nome}_{tag}_3x.png"))


if __name__ == "__main__":
    main()
