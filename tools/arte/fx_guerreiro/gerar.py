#!/usr/bin/env python3
"""Folhas de efeitos em pixel art das habilidades do Guerreiro, desenhadas por código (sem serviço pago e sem arte de
terceiros). Cada efeito é uma função que devolve os quadros (RGBA, alfa binário, paleta curta em degraus, sem
suavização); a folha sai com os quadros lado a lado e o catálogo (quadros, tamanho, fps, âncora) vai para
godot/art2d/fx/guerreiro/catalogo.json, lido por godot/scripts2d/fx_guerreiro_2d.gd.

Os cortes, o giro e a onda de choque saem em tons de marfim para o jogo tingir pelo elemento (modulate); o resto
tem cor própria. Todos apontam para a direita (o jogo gira pela mira). A saída é sempre a mesma (sementes fixas).

Uso: python3 tools/arte/fx_guerreiro/gerar.py [pasta_saida] [--contato arquivo.png]
"""
import json, math, os, sys
import numpy as np
from PIL import Image

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
SAIDA = os.path.join(RAIZ, "godot", "art2d", "fx", "guerreiro")

MARFIM = [(255, 252, 240), (238, 222, 184), (190, 164, 120), (120, 98, 72)]
FOGO = [(255, 244, 190), (255, 196, 64), (240, 120, 30), (176, 52, 20), (92, 24, 16)]
GELO = [(246, 253, 255), (190, 234, 247), (127, 211, 242), (58, 143, 192), (29, 74, 112)]
RAIO = [(255, 255, 255), (190, 224, 255), (95, 168, 255), (44, 92, 190)]
VENENO = [(214, 250, 150), (140, 220, 60), (76, 160, 36), (40, 96, 28), (22, 52, 22)]
PEDRA = [(214, 188, 140), (170, 138, 92), (118, 90, 60), (70, 50, 34), (34, 24, 18)]
SANGUE = [(255, 214, 120), (250, 120, 50), (214, 48, 36), (130, 22, 26), (60, 12, 18)]


class Tela:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = np.zeros((h, w, 4), dtype=np.uint8)
        self.y, self.x = np.mgrid[0:h, 0:w]
        self.x = self.x + 0.5
        self.y = self.y + 0.5

    def pintar(self, mascara, cor):
        self.px[mascara] = (*cor, 255)

    def apagar(self, mascara):
        self.px[mascara] = (0, 0, 0, 0)

    def ponto(self, x, y, cor):
        x, y = int(math.floor(x)), int(math.floor(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y, x] = (*cor, 255)

    def contorno(self, cor):
        a = self.px[:, :, 3] > 0
        viz = np.zeros_like(a)
        viz[1:, :] |= a[:-1, :]
        viz[:-1, :] |= a[1:, :]
        viz[:, 1:] |= a[:, :-1]
        viz[:, :-1] |= a[:, 1:]
        self.px[viz & ~a] = (*cor, 255)

    def imagem(self):
        return Image.fromarray(self.px, "RGBA")


def suave(u):
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3 - 2 * u)


def crescente(t, cx, cy, raio, esp, a0, a1, u0, u1, pal, achat=1.0):
    """Meia-lua de corte: do ângulo a0 a a1 (rad), mostrando o trecho u0..u1 do arco; fina nas pontas, a borda de
    fora é a mais clara. `achat` achata em Y (giro visto de cima em 3/4)."""
    dx, dy = t.x - cx, (t.y - cy) / achat
    r = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)
    u = (ang - a0) / (a1 - a0)
    if a1 - a0 > math.pi * 1.5:   # volta inteira: o ângulo dá a volta
        u = np.mod(ang - a0, 2 * math.pi) / (a1 - a0)
    dentro = (u >= u0) & (u <= u1)
    v = (u - u0) / max(u1 - u0, 1e-6)
    larg = esp * np.sin(np.clip(v, 0, 1) * math.pi) ** 0.7 * (0.35 + 0.65 * v)   # cabeça (v=1) mais grossa
    fora = raio
    d = fora - r
    faixa = dentro & (d >= 0) & (d <= larg)
    t.pintar(faixa, pal[2])
    t.pintar(faixa & (d <= larg * 0.62), pal[1])
    t.pintar(faixa & (d <= np.maximum(larg * 0.28, 1.0)), pal[0])


def corte():
    qs = []
    w, h, cx, cy, R = 44, 60, 5, 30, 36
    a0, a1 = math.radians(-62), math.radians(62)
    trechos = [(0.0, 0.42), (0.0, 0.8), (0.12, 1.0), (0.45, 1.0), (0.78, 1.0)]
    esp = [9, 12, 12, 9, 5]
    for i, (u0, u1) in enumerate(trechos):
        t = Tela(w, h)
        crescente(t, cx, cy, R, esp[i], a0, a1, u0, u1, MARFIM)
        if i >= 2:   # faíscas que escapam da ponta
            rs = np.random.RandomState(40 + i)
            for _ in range(4):
                a = a1 + rs.uniform(-0.25, 0.1)
                r = R + rs.uniform(-3, 4)
                t.ponto(cx + math.cos(a) * r, cy + math.sin(a) * r, MARFIM[0 if rs.rand() < 0.5 else 1])
        qs.append(t.imagem())
    return qs, {"fps": 24, "ax": cx, "ay": cy, "ref": R}


def corte_pesado():
    qs = []
    w, h, cx, cy, R = 62, 96, 6, 48, 52
    a0, a1 = math.radians(-78), math.radians(78)
    trechos = [(0.0, 0.3), (0.0, 0.7), (0.05, 1.0), (0.3, 1.0), (0.6, 1.0), (0.85, 1.0)]
    esp = [12, 17, 18, 14, 10, 6]
    for i, (u0, u1) in enumerate(trechos):
        t = Tela(w, h)
        crescente(t, cx, cy, R, esp[i], a0, a1, u0, u1, MARFIM)
        crescente(t, cx, cy, R - esp[i] - 3, max(2, esp[i] // 3), a0, a1, min(u0 + 0.15, 0.95), max(u1 - 0.1, 0.2), MARFIM[1:] + [MARFIM[3]])
        rs = np.random.RandomState(60 + i)
        for _ in range(6):
            a = a0 + (a1 - a0) * rs.uniform(u0, u1)
            r = R + rs.uniform(1, 6)
            t.ponto(cx + math.cos(a) * r, cy + math.sin(a) * r, MARFIM[0])
        qs.append(t.imagem())
    return qs, {"fps": 20, "ax": cx, "ay": cy, "ref": R}


def giro():
    qs = []
    w, h, cx, cy, R = 96, 60, 48, 30, 45
    n = 8
    for i in range(n):
        t = Tela(w, h)
        base = 2 * math.pi * i / n * 1.25
        comp = 0.36 if i < n - 2 else 0.2
        esp = 11 if i < n - 2 else 6
        for k in range(2):
            a0 = base + k * math.pi - math.pi
            crescente(t, cx, cy, R, esp, a0, a0 + 2 * math.pi, 0.0, comp, MARFIM, achat=0.56)
        rs = np.random.RandomState(80 + i)
        for _ in range(5):
            a = rs.uniform(0, 2 * math.pi)
            t.ponto(cx + math.cos(a) * (R + 1), cy + math.sin(a) * (R + 1) * 0.56, MARFIM[1])
        qs.append(t.imagem())
    return qs, {"fps": 22, "ax": cx, "ay": cy, "ref": R}


def onda():
    qs = []
    w, h, cx, cy = 100, 60, 50, 32
    n = 7
    for i in range(n):
        t = Tela(w, h)
        k = (i + 1) / n
        rx = 8 + 38 * suave(k) ** 0.8
        esp = max(2.0, 9 * (1 - k) + 2.0)
        dx, dy = (t.x - cx) / rx, (t.y - cy) / (rx * 0.56)
        r = np.hypot(dx, dy)
        e = esp / rx
        anel = (r <= 1.0) & (r >= 1.0 - e)
        ang = np.arctan2(dy, dx)
        dente = (np.sin(ang * 9 + i * 1.3) > -0.55) | (k < 0.5)   # quebra o anel no fim
        t.pintar(anel & dente, MARFIM[2])
        t.pintar(anel & dente & (r >= 1.0 - e * 0.6), MARFIM[1])
        t.pintar(anel & dente & (r >= 1.0 - e * 0.25) & (t.y < cy + 2), MARFIM[0])
        rs = np.random.RandomState(100 + i)
        for _ in range(10):   # poeira e lascas que sobem da borda
            a = rs.uniform(0, 2 * math.pi)
            alt = rs.uniform(1, 7) * math.sin(k * math.pi)
            t.ponto(cx + math.cos(a) * rx * 1.04, cy + math.sin(a) * rx * 0.58 - alt, MARFIM[int(rs.randint(0, 3))])
        qs.append(t.imagem())
    return qs, {"fps": 18, "ax": cx, "ay": cy, "ref": 46}


def fenda():
    qs = []
    w, h, cy = 132, 40, 26
    n = 8
    rs0 = np.random.RandomState(7)
    dentes = [(8 + i * 11 + rs0.uniform(-2, 2), rs0.uniform(7, 15), rs0.uniform(3.5, 6), rs0.uniform(-2, 2)) for i in range(11)]
    desvio = lambda x: 2.2 * np.sin(x * 0.21) + 1.4 * np.sin(x * 0.53 + 1.0)
    for i in range(n):
        t = Tela(w, h)
        alcance = w * min(1.0, (i + 1) / 4.0)
        larg = np.where(t.x < alcance, 2.6 * np.sin(np.clip(t.x / max(alcance, 1), 0, 1) * math.pi) ** 0.5 + 0.6, 0.0)
        if i >= 6:
            larg = larg * (0.6 if i == 6 else 0.3)
        d = np.abs(t.y - (cy + desvio(t.x)))
        t.pintar((d <= larg + 1.2) & (t.x < alcance), PEDRA[3])
        t.pintar((d <= larg) & (t.x < alcance), PEDRA[4])
        if 1 <= i <= 4:
            t.pintar((d <= larg * 0.35) & (t.x < alcance) & (t.x > alcance - 40), FOGO[2])
        for (x0, alt, meia, incl) in dentes:   # lascas de pedra que saltam da fenda
            nasce = x0 / w * 4.0
            idade = (i + 1) - nasce
            if idade <= 0:
                continue
            f = min(1.0, idade / 1.5) if i < 5 else max(0.0, 1.0 - (i - 4) / 3.5)
            a = alt * f
            if a < 1.5:
                continue
            base_y = cy + float(desvio(np.array(x0)))
            v = (base_y - t.y) / a
            meia_l = meia * (1 - np.clip(v, 0, 1))
            xc = x0 + incl * np.clip(v, 0, 1) * 2
            m = (v >= 0) & (v <= 1) & (np.abs(t.x - xc) <= meia_l)
            t.pintar(m, PEDRA[2])
            t.pintar(m & (t.x < xc - meia_l * 0.15), PEDRA[1])
            t.pintar(m & (t.x < xc - meia_l * 0.6), PEDRA[0])
        rs = np.random.RandomState(120 + i)
        for _ in range(8 if i < 6 else 14):   # cascalho
            x = rs.uniform(4, max(alcance, 8))
            t.ponto(x, cy + float(desvio(np.array(x))) + rs.uniform(-9, 6), PEDRA[int(rs.randint(1, 4))])
        t.contorno(PEDRA[4])
        qs.append(t.imagem())
    return qs, {"fps": 16, "ax": 0, "ay": cy, "ref": w}


def escudada():
    qs = []
    w, h, cx, cy = 40, 52, 8, 26
    n = 5
    azul = [(255, 255, 255), (190, 224, 255), (95, 168, 255), (44, 92, 190)]
    for i in range(n):
        t = Tela(w, h)
        k = (i + 1) / n
        R = 10 + 20 * k
        crescente(t, cx - 6, cy, R, 6 * (1 - k) + 2, math.radians(-58), math.radians(58), 0.0, 1.0, azul)
        if i < 3:   # estrela do impacto
            for a in np.linspace(-1.0, 1.0, 5):
                comp = (8 + 6 * (a == 0)) * (1 - k * 0.5)
                for s in np.arange(2, comp, 0.5):
                    t.ponto(cx + math.cos(a) * s, cy + math.sin(a) * s, azul[0] if s < comp * 0.6 else azul[1])
        qs.append(t.imagem())
    return qs, {"fps": 20, "ax": cx, "ay": cy, "ref": 30}


def poeira():
    qs = []
    w, h = 24, 16
    cores = [(196, 176, 140), (150, 130, 100), (104, 88, 70)]
    for i in range(5):
        t = Tela(w, h)
        k = i / 4.0
        rs = np.random.RandomState(140)
        for j in range(5):
            bx, by = rs.uniform(6, 18), rs.uniform(8, 12)
            r = rs.uniform(2.5, 4.5) * (0.6 + 0.6 * k) * (1.0 if i < 3 else 1.0 - (i - 2) * 0.3)
            ox = (bx - 12) * k * 0.6
            m = np.hypot(t.x - bx - ox, (t.y - by + k * 5)) <= r
            t.pintar(m, cores[1])
            t.pintar(m & (t.y < by - k * 5), cores[0])
        t.contorno(cores[2])
        if i == 4:
            t.apagar((np.sin(t.x * 2.1) * np.sin(t.y * 2.7) > 0.1))
        qs.append(t.imagem())
    return qs, {"fps": 14, "ax": 12, "ay": 13, "ref": 24}


def chama(t, cx, base, alt, meia, fase, pal, ondas=3.0):
    """Língua de chama: larga embaixo, afina e balança em cima; 4 degraus da paleta do miolo para a borda."""
    v = (base - t.y) / max(alt, 1e-6)
    bal = np.sin(v * ondas + fase) * meia * 0.45 * v
    l = meia * (1 - np.clip(v, 0, 1) ** 1.3) * (0.75 + 0.25 * np.sin(v * 7 + fase * 1.7))
    d = np.abs(t.x - cx - bal)
    m = (v >= 0) & (v <= 1) & (d <= l)
    t.pintar(m, pal[3])
    t.pintar(m & (d <= l * 0.72) & (v <= 0.86), pal[2])
    t.pintar(m & (d <= l * 0.45) & (v <= 0.66), pal[1])
    t.pintar(m & (d <= l * 0.2) & (v <= 0.4), pal[0])


def furia():
    qs = []
    w, h = 40, 46
    n = 6
    for i in range(n):
        t = Tela(w, h)
        f = 2 * math.pi * i / n
        for j, (x, alt, meia) in enumerate([(8, 26, 5), (20, 38, 7), (32, 24, 5), (14, 16, 4), (27, 18, 4)]):
            chama(t, x, h - 1, alt * (0.85 + 0.15 * math.sin(f + j * 1.9)), meia, f + j * 2.1, SANGUE)
        rs = np.random.RandomState(160)
        for j in range(6):
            x = rs.uniform(4, 36)
            y = (rs.uniform(0, h) - i * h / n) % h
            t.ponto(x, y, SANGUE[int(rs.randint(0, 2))])
        qs.append(t.imagem())
    return qs, {"fps": 12, "ax": 20, "ay": 44, "ref": 40, "loop": True}


def lamina():
    qs = []
    w, h, cy = 30, 14, 7
    for i in range(4):
        t = Tela(w, h)
        ponta = 26
        larg = np.where(t.x < ponta - 4, 2.0, np.clip((ponta - t.x) / 2.0, 0, 2.0))
        m = (t.x >= 8) & (t.x <= ponta) & (np.abs(t.y - cy) <= larg)
        t.pintar(m, RAIO[1])
        t.pintar(m & (t.y < cy), RAIO[0])
        t.pintar((t.x >= 6) & (t.x < 8) & (np.abs(t.y - cy) <= 4), (214, 170, 80))
        t.pintar((t.x >= 2) & (t.x < 6) & (np.abs(t.y - cy) <= 1), (110, 72, 44))
        t.contorno(RAIO[3])
        rs = np.random.RandomState(180 + i)
        for _ in range(5):   # faíscas
            x = rs.uniform(8, 28)
            t.ponto(x, cy + rs.choice([-5, -4, 4, 5]), RAIO[int(rs.randint(0, 3))])
            t.ponto(x + rs.choice([-1, 1]), cy + rs.choice([-3, 3]), RAIO[2])
        qs.append(t.imagem())
    return qs, {"fps": 14, "ax": 15, "ay": cy, "ref": 30, "loop": True}


def onda_fogo():
    qs = []
    w, h, cx, cy, R = 40, 64, -14, 32, 46
    n = 6
    for i in range(n):
        t = Tela(w, h)
        f = 2 * math.pi * i / n
        dx, dy = t.x - cx, t.y - cy
        r = np.hypot(dx, dy)
        ang = np.arctan2(dy, dx)
        u = (ang + math.radians(40)) / math.radians(80)
        dentro = (u >= 0) & (u <= 1)
        cauda = (9 + 5 * np.sin(ang * 9 + f) + 3 * np.sin(ang * 17 - f * 2)) * np.sin(np.clip(u, 0, 1) * math.pi) ** 0.6
        d = R - r
        m = dentro & (d >= 0) & (d <= cauda)
        t.pintar(m, FOGO[3])
        t.pintar(m & (d <= cauda * 0.7), FOGO[2])
        t.pintar(m & (d <= cauda * 0.42), FOGO[1])
        t.pintar(m & (d <= np.maximum(cauda * 0.16, 1.2)), FOGO[0])
        rs = np.random.RandomState(200 + i)
        for _ in range(7):   # brasas que ficam para trás
            a = math.radians(rs.uniform(-36, 36))
            rr = R - rs.uniform(12, 22)
            t.ponto(cx + math.cos(a) * rr, cy + math.sin(a) * rr, FOGO[int(rs.randint(1, 4))])
        qs.append(t.imagem())
    return qs, {"fps": 14, "ax": 22, "ay": cy, "ref": 58, "loop": True}


def pilar_fogo():
    qs = []
    w, h = 44, 84
    alts = [6, 30, 62, 74, 70, 58, 36, 14]
    for i, alt in enumerate(alts):
        t = Tela(w, h)
        f = i * 1.3
        base = h - 6
        m = np.hypot((t.x - 22) / 17.0, (t.y - base) / 5.0) <= 1.0   # boca de brasa no chão
        t.pintar(m, FOGO[4])
        t.pintar(np.hypot((t.x - 22) / 13.0, (t.y - base) / 3.4) <= 1.0, FOGO[3])
        t.pintar(np.hypot((t.x - 22) / 8.0, (t.y - base) / 2.0) <= 1.0, FOGO[1 if i < 6 else 2])
        if i < 7:
            larg = 12 if 1 <= i <= 5 else 8
            chama(t, 22, base, alt, larg, f, FOGO, ondas=5.0)
            chama(t, 13, base, alt * 0.55, larg * 0.5, f + 2.0, FOGO, ondas=4.0)
            chama(t, 31, base, alt * 0.62, larg * 0.5, f + 4.0, FOGO, ondas=4.0)
        rs = np.random.RandomState(220 + i)
        for _ in range(8):
            t.ponto(22 + rs.uniform(-16, 16), base - rs.uniform(4, alt + 8), FOGO[int(rs.randint(0, 3))])
        qs.append(t.imagem())
    return qs, {"fps": 14, "ax": 22, "ay": h - 6, "ref": 34}


def anel_gelo():
    qs = []
    w, h, cx, cy, rx = 112, 76, 56, 50, 46
    ry = rx * 0.5
    n = 9
    rs0 = np.random.RandomState(11)
    esp = []
    for k in range(12):
        a = 2 * math.pi * k / 12 + rs0.uniform(-0.12, 0.12)
        esp.append((cx + math.cos(a) * rx, cy + math.sin(a) * ry, rs0.uniform(17, 26), rs0.uniform(4.5, 6.5), math.cos(a) * 3.5, k))
    esp.sort(key=lambda e: e[1])
    cresc = [0.25, 0.7, 1.0, 1.0, 1.0, 1.0, 0.9, 0.55, 0.2]
    for i in range(n):
        t = Tela(w, h)
        dx, dy = (t.x - cx) / (rx + 5), (t.y - cy) / (ry + 4)
        geada = (np.hypot(dx, dy) <= 1.0) & (np.hypot(dx, dy) >= 0.72) & (((t.x.astype(int) + t.y.astype(int)) % 2) == 0)
        if 1 <= i <= 7:
            t.pintar(geada, GELO[3])
        for (x0, y0, alt, meia, incl, k) in esp:
            f = cresc[i] * (1.0 if i < 6 else (1.0 if k % 3 else 0.5))
            a = alt * f
            if a < 2:
                continue
            v = (y0 - t.y) / a
            vc = np.clip(v, 0, 1)
            l = meia * (1 - vc)
            xc = x0 + incl * vc
            m = (v >= 0) & (v <= 1) & (np.abs(t.x - xc) <= l)
            t.pintar(m, GELO[2])
            t.pintar(m & (t.x < xc), GELO[1])
            t.pintar(m & (t.x < xc - l * 0.45), GELO[0])
            t.pintar(m & (t.x > xc + l * 0.5), GELO[3])
        t.contorno(GELO[4])
        rs = np.random.RandomState(240 + i)
        if i >= 6:   # estilhaços
            for _ in range(22):
                a = rs.uniform(0, 2 * math.pi)
                rr = rx + rs.uniform(-6, 10) * (i - 5) * 0.5
                t.ponto(cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.5 - rs.uniform(0, 16), GELO[int(rs.randint(0, 3))])
        qs.append(t.imagem())
    return qs, {"fps": 12, "ax": cx, "ay": cy, "ref": rx}


def escudo():
    qs = []
    w = h = 22
    c = 11
    for i in range(4):
        t = Tela(w, h)
        r = np.hypot(t.x - c, t.y - c)
        ang = np.arctan2(t.y - c, t.x - c) + i * math.pi / 2
        t.pintar(r <= 9, (196, 152, 62))
        t.pintar(r <= 7, (96, 104, 120))
        t.pintar((r <= 7) & (np.cos(ang) > 0.3), (140, 150, 168))
        t.pintar((r <= 9) & (r > 7) & (np.cos(ang - 0.6) > 0.55), (244, 214, 130))
        t.pintar(r <= 2.4, (226, 190, 96))
        t.pintar((r <= 6) & (r > 3) & (np.abs(np.sin(ang * 2)) < 0.22), (196, 152, 62))
        t.contorno((40, 30, 24))
        rs = np.random.RandomState(260 + i)
        for _ in range(3):   # geada na borda
            a = rs.uniform(0, 2 * math.pi)
            t.ponto(c + math.cos(a) * 9.5, c + math.sin(a) * 9.5, GELO[0])
        qs.append(t.imagem())
    return qs, {"fps": 16, "ax": c, "ay": c, "ref": 20, "loop": True}


def poca():
    qs = []
    w, h, cx, cy = 48, 28, 24, 14
    bolhas = [(14, 12, 0), (30, 17, 2), (24, 9, 1), (36, 12, 3), (19, 18, 2)]
    for i in range(4):
        t = Tela(w, h)
        ang = np.arctan2((t.y - cy) / 0.55, t.x - cx)
        borda = 20 + 1.6 * np.sin(ang * 5 + 0.7) + 1.1 * np.sin(ang * 9 + i * 0.8)
        r = np.hypot(t.x - cx, (t.y - cy) / 0.55)
        t.pintar(r <= borda, VENENO[3])
        t.pintar(r <= borda - 2.5, VENENO[2])
        t.pintar((r <= borda - 7) & (np.sin(t.x * 0.7 + i * 1.5) + np.sin(t.y * 1.3) > 0.6), VENENO[1])
        for (bx, by, fase) in bolhas:
            e = (i + fase) % 4
            if e == 0:
                t.ponto(bx, by, VENENO[1])
            elif e == 1:
                t.pintar(np.hypot(t.x - bx, t.y - by) <= 1.6, VENENO[1])
                t.ponto(bx - 1, by - 1, VENENO[0])
            elif e == 2:
                t.pintar(np.abs(np.hypot(t.x - bx, t.y - by) - 2.4) <= 0.6, VENENO[0])
        t.contorno(VENENO[4])
        qs.append(t.imagem())
    return qs, {"fps": 6, "ax": cx, "ay": cy, "ref": 40, "loop": True}


def estandarte():
    qs = []
    w, h = 30, 54
    pano = [(96, 150, 60), (58, 108, 44), (36, 72, 34), (22, 44, 26)]
    for i in range(4):
        t = Tela(w, h)
        f = 2 * math.pi * i / 4
        t.pintar((np.abs(t.x - 8) <= 1) & (t.y >= 4) & (t.y <= h - 2), (120, 84, 52))   # haste
        t.pintar((np.abs(t.x - 7.5) <= 0.5) & (t.y >= 4) & (t.y <= h - 2), (168, 124, 78))
        t.pintar((np.hypot(t.x - 8, t.y - 3.5) <= 2.2), (206, 196, 170))                 # ponta de osso
        t.pintar((np.abs(t.y - 7.5) <= 1) & (t.x >= 6) & (t.x <= 26), (120, 84, 52))     # travessa
        desl = np.round(1.6 * np.sin(t.y * 0.32 + f) * np.clip((t.y - 8) / 22.0, 0, 1))
        xx = t.x - desl
        barra = 31 + np.where((xx.astype(int) // 4) % 2 == 0, 0, -4) + np.round(1.2 * np.sin(f + xx * 0.5))
        m = (xx >= 10) & (xx <= 26) & (t.y >= 9) & (t.y <= barra)
        t.pintar(m, pano[1])
        t.pintar(m & (np.sin(xx * 0.9 + t.y * 0.25 + f) > 0.35), pano[0])
        t.pintar(m & (np.sin(xx * 0.9 + t.y * 0.25 + f) < -0.5), pano[2])
        cxk, cyk = 18 + desl, 18
        cr = np.hypot(xx - 18, t.y - cyk)
        t.pintar(m & (cr <= 3.6), (214, 240, 170))                                        # caveira
        t.pintar(m & (np.abs(xx - 18) <= 2) & (t.y > cyk + 2) & (t.y <= cyk + 5), (214, 240, 170))
        t.pintar(m & (np.abs(np.abs(xx - 18) - 1.5) <= 0.6) & (np.abs(t.y - cyk) <= 0.8), pano[3])
        t.contorno((18, 30, 20))
        rs = np.random.RandomState(280)
        for j in range(5):   # esporos que sobem
            x = rs.uniform(4, 28)
            y = (rs.uniform(0, h) - i * h / 4.0) % h
            t.ponto(x, y, VENENO[int(rs.randint(0, 2))])
        qs.append(t.imagem())
    return qs, {"fps": 6, "ax": 8, "ay": h - 2, "ref": 54, "loop": True}


EFEITOS = {"corte": corte, "corte_pesado": corte_pesado, "giro": giro, "onda": onda, "fenda": fenda,
           "escudada": escudada, "poeira": poeira, "furia": furia, "lamina": lamina, "onda_fogo": onda_fogo,
           "pilar_fogo": pilar_fogo, "anel_gelo": anel_gelo, "escudo": escudo, "poca": poca, "estandarte": estandarte}


def main():
    args = [a for a in sys.argv[1:]]
    contato = None
    if "--contato" in args:
        contato = args[args.index("--contato") + 1]
        del args[args.index("--contato"):args.index("--contato") + 2]
    saida = args[0] if args else SAIDA
    os.makedirs(saida, exist_ok=True)
    cat, folhas = {}, []
    for nome, fn in EFEITOS.items():
        qs, info = fn()
        w, h = qs[0].size
        folha = Image.new("RGBA", (w * len(qs), h), (0, 0, 0, 0))
        for i, q in enumerate(qs):
            folha.paste(q, (i * w, 0))
        assert set(np.unique(np.asarray(folha.getchannel("A")))) <= {0, 255}, nome
        folha.save(os.path.join(saida, nome + ".png"), optimize=True)
        cat[nome] = {"n": len(qs), "w": w, "h": h, **info}
        folhas.append((nome, folha))
        print(nome, cat[nome])
    with open(os.path.join(saida, "catalogo.json"), "w", encoding="utf-8") as f:
        json.dump(cat, f, indent=1, sort_keys=True)
        f.write("\n")
    if contato:
        esc = 3
        larg = max(f.width for _, f in folhas) * esc
        alt = sum(f.height * esc + 6 for _, f in folhas)
        im = Image.new("RGBA", (larg, alt), (52, 56, 52, 255))
        y = 0
        for _, f in folhas:
            g = f.resize((f.width * esc, f.height * esc), Image.NEAREST)
            im.alpha_composite(g, (0, y))
            y += g.height + 6
        im.save(contato)


if __name__ == "__main__":
    main()
