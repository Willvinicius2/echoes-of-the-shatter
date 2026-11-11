#!/usr/bin/env python3
"""Monta por código o piso e os props da Ponte do Sino (área 3 do Ato I), na linguagem dos cenários pixelados do jogo: grade de
1 px de mundo, alfa binário, contorno preto de 1 px, paleta curta por material, luz de cima à esquerda, sem gradiente.

Saídas:
  godot/art2d/tiles/cripta_ponte.png     atlas do piso (256 x 128): 4 variantes de calçada de pedra azul-acinzentada na linha 0 e
                                         4 de laje mais clara na linha 1; as juntas ficam na mesma grade nas 8, então casam entre si
  godot/art2d/props/ponte_sino.png        sino de bronze com pátina pendurado num pórtico de pedra (marco das praças)
  godot/art2d/props/ponte_sino_caido.png  sino rachado tombado no chão, com teia
  godot/art2d/props/ponte_sino_maior.png  o Sino Maior da arena do chefe: dois pilares, arco, o sino grande e as teias da Tecelã
  godot/art2d/props/ponte_casulo.png      casulo de teia pendurado num toco de pilar
  godot/art2d/props/ponte_teia_0/1.png    teias no chão (sem colisor)
  godot/art2d/props/ponte_entulho.png     pedaço de parapeito caído

Pivô de todos = centro da borda de baixo. Uso: python3 -I tools/sprites2d/montar_ponte.py [--previas DIR]
Só PIL e numpy; a paleta e a alvenaria vêm de tools/mapas/ponte_pixel.py (carregado por caminho porque o script roda com -I).
"""
import importlib.util
import math
import os
import sys

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(AQUI, "..", "..")
PROPS = os.path.join(R, "godot", "art2d", "props")
TILES = os.path.join(R, "godot", "art2d", "tiles")

_spec = importlib.util.spec_from_file_location("ponte_pixel", os.path.join(R, "tools", "mapas", "ponte_pixel.py"))
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)
por, h2, alvenaria = pp.por, pp.h2, pp.alvenaria
S0, S1, S2, S2B, S3, S4, K0 = pp.S0, pp.S1, pp.S2, pp.S2B, pp.S3, pp.S4, pp.K0
B0, B1, B2, B3, B4, P0, P1, P2 = pp.B0, pp.B1, pp.B2, pp.B3, pp.B4, pp.P0, pp.P1, pp.P2
W0, W1, W2, W3, T1, T2, A0 = pp.W0, pp.W1, pp.W2, pp.W3, pp.T1, pp.T2, pp.A0


def nova(w, h):
    return np.zeros((h, w, 4), np.uint8)


def ruido(x, y, esc, s=0):
    """Ruído de valor suave em [0, 1) (interpolação bilinear de h2)."""
    fx, fy = x / esc, y / esc
    ix, iy = math.floor(fx), math.floor(fy)
    tx, ty = fx - ix, fy - iy
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a, b = h2(ix, iy, s), h2(ix + 1, iy, s)
    c, d = h2(ix, iy + 1, s), h2(ix + 1, iy + 1, s)
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty


def contornar(img, cor=K0):
    """Contorno externo de 1 px (4 vizinhos) em volta de tudo o que está pintado."""
    m = img[..., 3] > 0
    viz = np.zeros_like(m)
    viz[1:, :] |= m[:-1, :]
    viz[:-1, :] |= m[1:, :]
    viz[:, 1:] |= m[:, :-1]
    viz[:, :-1] |= m[:, 1:]
    b = viz & ~m
    img[b, :3] = cor
    img[b, 3] = 255
    return img


def recortar(img, margem=0):
    ys, xs = np.where(img[..., 3] > 0)
    x0, x1 = xs.min(), xs.max() + 1
    y0, y1 = ys.min(), ys.max() + 1
    # o pivô é o centro da borda de baixo: mantém o desenho centrado em x
    cx = img.shape[1] // 2
    meia = max(cx - x0, x1 - cx)
    return img[y0:y1, cx - meia:cx + meia].copy()


def linha(img, x0, y0, x1, y1, cor, esp=1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n + 1):
        t = i / max(n, 1)
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        por(img, round(x), round(y), round(x) + esp, round(y) + esp, cor)


# ---------------------------------------------------------------------------------------------------------------- piso
def montar_atlas():
    """Calçada em fiadas: 4 fiadas de 16 px por tile, juntas verticais numa grade de 32 px deslocada 16 px a cada fiada (as 8
    variantes têm as mesmas juntas e casam em qualquer ordem). O que muda de uma para outra: tons, lascas, trincas e poeira."""
    img = nova(256, 128)
    for linha_atlas, (base, claro, escuro, junta) in enumerate([(S2, S3, S2B, S1), (S3, S4, S2, S1)]):
        for v in range(4):
            ox, oy = v * 64, linha_atlas * 64
            por(img, ox, oy, ox + 64, oy + 64, junta)
            for f in range(4):
                desl = 16 if f % 2 else 0
                for k in range(-1, 2):
                    xa, xb = k * 32 + desl + 1, k * 32 + desl + 32
                    xa2, xb2 = max(xa, 0), min(xb, 64)
                    if xb2 <= xa2:
                        continue
                    # o tom do bloco depende da posição dele na parede inteira do tile (a metade que cruza a borda repete)
                    chave = (k * 32 + desl) % 64
                    t = h2(chave, f, 31 + v * 7 + linha_atlas * 3)
                    cor = base if t < 0.62 else (escuro if t < 0.95 else claro)
                    por(img, ox + xa2, oy + f * 16 + 1, ox + xb2, oy + f * 16 + 16, cor)
                    if cor != claro and xa >= 0:
                        por(img, ox + xa2, oy + f * 16 + 1, ox + xb2, oy + f * 16 + 2, claro if cor == base else base)
                    if h2(chave, f, 47 + v) < 0.3 and xb2 - xa2 > 20:     # trinca
                        cx = ox + xa2 + 5 + int(h2(chave, f, 53 + v) * (xb2 - xa2 - 12))
                        for j in range(4 + int(h2(chave, f, 59) * 8)):
                            por(img, cx + (j // 3) % 2, oy + f * 16 + 3 + j, cx + (j // 3) % 2 + 1, oy + f * 16 + 4 + j, junta)
            # poeira e desgaste: pixels soltos mais claros e mais escuros
            for i in range(46):
                x, y = int(h2(i, v, 61 + linha_atlas) * 62) + 1, int(h2(i, v, 67 + linha_atlas) * 62) + 1
                if tuple(img[oy + y, ox + x, :3]) == base:
                    por(img, ox + x, oy + y, ox + x + (2 if i % 3 == 0 else 1), oy + y + 1, escuro if i % 2 else claro)
    return img


# ---------------------------------------------------------------------------------------------------------------- sino
def _perfil_sino(t):
    """Meia-largura relativa (0 a 1) do sino na altura t (0 = topo da coroa, 1 = boca)."""
    if t < 0.10:
        return 0.30 + 0.9 * t
    if t < 0.30:
        return 0.39 + 1.25 * (t - 0.10)
    if t < 0.82:
        return 0.64 + 0.27 * (t - 0.30)
    return 0.78 + 1.22 * (t - 0.82)


def sino(img, cx, topo, larg, alt, seed=1, rachado=False, mordida=None):
    """Sino de bronze visto de frente (câmera 3/4): corpo em faixas de luz, pátina escorrendo de cima, friso, boca em elipse com o
    oco escuro e o badalo. `mordida` = (u0, u1) tira um pedaço da borda (sino quebrado)."""
    meia = larg / 2.0
    for j in range(alt):
        t = (j + 0.5) / alt
        hw = meia * _perfil_sino(t)
        y = topo + j
        for x in range(int(cx - hw), int(math.ceil(cx + hw))):
            u = (x + 0.5 - cx) / max(hw, 1.0)
            if mordida and t > 0.70 and mordida[0] < u < mordida[1] and t > 0.70 + 0.16 * abs(math.sin(u * 23.0)):
                continue
            n = ruido(x, y, 9.0, seed) - 0.5
            v = u + n * 0.22
            if v < -0.80:
                cor = B2
            elif v < -0.42:
                cor = B4
            elif v < 0.05:
                cor = B3
            elif v < 0.55:
                cor = B2
            elif v < 0.86:
                cor = B1
            else:
                cor = B0
            # pátina: escorre de cima e mancha a sombra
            pat = ruido(x, y * 0.35, 7.0, seed + 5) * 0.7 + ruido(x, y, 3.0, seed + 6) * 0.3
            if pat > 0.47 + 0.34 * t - (0.10 if 0.30 < t < 0.40 else 0.0):
                cor = P2 if cor in (B4, B3) else (P1 if cor == B2 else P0)
            if 0.60 < t < 0.64 or 0.26 < t < 0.285:        # frisos
                cor = B1 if cor not in (B0,) else B0
            por(img, x, y, x + 1, y + 1, cor)
    # boca: elipse com a borda clara e o oco
    rx, ry = meia * _perfil_sino(1.0), max(5, alt // 9)
    yb = topo + alt - 1
    for x in range(int(cx - rx), int(math.ceil(cx + rx))):
        u = (x + 0.5 - cx) / rx
        if mordida and mordida[0] < u < mordida[1]:
            continue
        dy = int(ry * math.sqrt(max(0.0, 1.0 - u * u)))
        por(img, x, yb, x + 1, yb + dy + 1, B1 if u > 0.2 else B2)
        if dy > 3:
            por(img, x, yb + 1, x + 1, yb + dy - 2, A0)
            por(img, x, yb + dy - 2, x + 1, yb + dy, B3 if u < 0.3 else B1)
    # badalo
    por(img, cx - 2, yb + 1, cx + 2, yb + ry + 4, B0)
    por(img, cx - 5, yb + ry + 2, cx + 5, yb + ry + 10, B2)
    por(img, cx - 5, yb + ry + 2, cx - 2, yb + ry + 6, B3)
    por(img, cx + 2, yb + ry + 6, cx + 5, yb + ry + 10, B1)
    if rachado:
        x, y = cx + int(meia * 0.22), topo + int(alt * 0.34)
        for j in range(int(alt * 0.6)):
            x += (1 if h2(j, seed, 71) < 0.35 else (-1 if h2(j, seed, 72) < 0.3 else 0))
            por(img, x, y + j, x + (2 if j % 5 == 0 else 1), y + j + 1, B0)


def teia(img, pts, seed=1, cor=T1, nos=T2):
    """Fios de teia entre pontos, com uma barriga leve; os nós brilham."""
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        n = int(max(abs(x1 - x0), abs(y1 - y0)))
        for k in range(n + 1):
            t = k / max(n, 1)
            bar = math.sin(t * math.pi) * (4 + 5 * h2(i, seed, 81))
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + bar
            if (k + i) % 9 != 8:
                por(img, round(x), round(y), round(x) + 1, round(y) + 1, cor)
        por(img, x0 - 1, y0 - 1, x0 + 1, y0 + 1, nos)


def pilar(img, x0, x1, y_topo, y_base, seed=1, capitel=True):
    """Pilar de blocos visto de frente: lateral clara à esquerda, sombra à direita, capitel e base mais largos."""
    alvenaria(img, x0, y_topo, x1, y_base, seed=seed, fiada=15, passo=(16, 30))
    por(img, x0, y_topo, x0 + 3, y_base, S3)
    por(img, x1 - 5, y_topo, x1, y_base, S1)
    for jy in range(y_topo + 15, y_base, 15):
        por(img, x0, jy, x0 + 3, jy + 1, S1)
        por(img, x1 - 5, jy, x1, jy + 1, S0)
    por(img, x0 - 4, y_base - 12, x1 + 4, y_base, S2)
    por(img, x0 - 4, y_base - 12, x1 + 4, y_base - 10, S4)
    por(img, x0 - 4, y_base - 3, x1 + 4, y_base, S1)
    if capitel:
        por(img, x0 - 5, y_topo - 10, x1 + 5, y_topo, S3)
        por(img, x0 - 5, y_topo - 10, x1 + 5, y_topo - 8, S4)
        por(img, x0 - 5, y_topo - 2, x1 + 5, y_topo, S1)


def montar_sino():
    w, h = 190, 230
    img = nova(w, h)
    cx, base = w // 2, h - 2
    pilar(img, cx - 78, cx - 52, base - 170, base, seed=3)
    pilar(img, cx + 52, cx + 78, base - 170, base, seed=5)
    # viga de madeira com cintas de bronze
    yv = base - 196
    por(img, cx - 90, yv, cx + 90, yv + 16, W2)
    por(img, cx - 90, yv, cx + 90, yv + 3, W3)
    por(img, cx - 90, yv + 12, cx + 90, yv + 16, W1)
    for x in range(cx - 84, cx + 84, 13):
        por(img, x, yv + 5 + int(h2(x, 1, 5) * 4), x + 6, yv + 6 + int(h2(x, 1, 5) * 4), W1)
    for x in (cx - 66, cx + 60, cx - 4):
        por(img, x, yv - 1, x + 8, yv + 17, B2)
        por(img, x, yv - 1, x + 2, yv + 17, B4)
        por(img, x + 6, yv - 1, x + 8, yv + 17, B0)
    # jugo e sino
    por(img, cx - 5, yv + 16, cx + 5, yv + 30, B1)
    por(img, cx - 5, yv + 16, cx - 2, yv + 30, B3)
    sino(img, cx, yv + 28, 88, 96, seed=11)
    teia(img, [(cx - 52, base - 150), (cx - 30, yv + 60)], seed=2)
    teia(img, [(cx + 52, base - 120), (cx + 34, yv + 96), (cx + 60, base - 60)], seed=3)
    return recortar(contornar(img))


def montar_sino_caido():
    """Sino rachado tombado de lado, com o dobro do tamanho do sino do pórtico (a revisão pediu bem maior e legível)."""
    k = 2
    w, h = 170 * k, 120 * k
    img = nova(w, h)
    tmp = nova(140 * k, 140 * k)
    sino(tmp, 70 * k, 12 * k, 96 * k, 100 * k, seed=23, rachado=True, mordida=(-0.2, 0.5))
    # tombado: gira 90 graus e achata um pouco (a boca fica para a direita)
    gir = np.rot90(tmp, 3)
    gir = np.array(Image.fromarray(gir, "RGBA").resize((126 * k, 92 * k), Image.NEAREST))
    y0 = h - 6 * k - 92 * k
    a = gir[..., 3] > 0
    img[y0:y0 + 92 * k, 20 * k:146 * k][a] = gir[a]
    # cacos e teia
    for (x, y, lw, lh) in [(8, h - 16, 18, 10), (148, h - 12, 14, 7), (132, h - 22, 10, 8), (60, h - 10, 16, 8), (250, h - 14, 22, 9), (300, h - 26, 12, 9)]:
        x = x * k if x < 160 else x
        por(img, x, y, x + lw, y + lh, B2)
        por(img, x, y, x + lw, y + 2, B4)
        por(img, x + lw - 3, y + 2, x + lw, y + lh, B0)
    teia(img, [(44, y0 + 20), (120, y0 + 36), (220, y0 + 12)], seed=4)
    teia(img, [(300, y0 + 60), (320, h - 28)], seed=5)
    return recortar(contornar(img))


def montar_sino_maior():
    w, h = 460, 400
    img = nova(w, h)
    cx, base = w // 2, h - 2
    # dois pilares largos e o arco
    for s, seed in ((-1, 7), (1, 9)):
        xa = cx + s * 170 - 34
        pilar(img, xa, xa + 68, base - 250, base, seed=seed)
        por(img, xa - 10, base - 20, xa + 78, base, S2)
        por(img, xa - 10, base - 20, xa + 78, base - 17, S4)
        por(img, xa - 10, base - 5, xa + 78, base, S1)
    # arco de aduelas
    R_out, R_in, yc = 214, 172, base - 250
    ACH = 0.6      # arco abatido
    for y in range(yc - int(R_out * ACH) - 1, yc + 1):
        for x in range(cx - R_out, cx + R_out):
            dx, dy = x + 0.5 - cx, (y + 0.5 - yc) / ACH
            r = math.hypot(dx, dy)
            if R_in <= r < R_out:
                ang = math.atan2(-dy, dx)
                k = int(ang / math.pi * 13)
                borda = abs(ang / math.pi * 13 - round(ang / math.pi * 13)) < 0.035
                cor = S1 if borda else (S3 if r > R_out - 5 else (S1 if r < R_in + 5 else (S2 if k % 3 else S2B)))
                if dx > 60 and not borda and r <= R_out - 5:
                    cor = S1 if cor in (S2, S2B) else cor
                por(img, x, y, x + 1, y + 1, cor)
    # pedra-chave
    por(img, cx - 18, yc - int(R_out * ACH) - 8, cx + 18, yc - int(R_in * ACH) + 6, S3)
    por(img, cx - 18, yc - int(R_out * ACH) - 8, cx + 18, yc - int(R_out * ACH) - 5, S4)
    por(img, cx + 12, yc - int(R_out * ACH) - 5, cx + 18, yc - int(R_in * ACH) + 6, S1)
    # viga e o Sino Maior
    yv = yc - 92
    por(img, cx - 150, yv, cx + 150, yv + 20, W2)
    por(img, cx - 150, yv, cx + 150, yv + 4, W3)
    por(img, cx - 150, yv + 15, cx + 150, yv + 20, W1)
    for x in (cx - 120, cx - 12, cx + 100):
        por(img, x, yv - 2, x + 12, yv + 22, B2)
        por(img, x, yv - 2, x + 3, yv + 22, B4)
        por(img, x + 9, yv - 2, x + 12, yv + 22, B0)
    por(img, cx - 8, yv + 20, cx + 8, yv + 40, B1)
    por(img, cx - 8, yv + 20, cx - 3, yv + 40, B3)
    sino(img, cx, yv + 38, 210, 216, seed=41, rachado=True, mordida=(0.25, 0.7))
    # teias da Tecelã: dos pilares ao sino e ao arco
    teia(img, [(cx - 136, base - 230), (cx - 70, yv + 120), (cx - 136, base - 90)], seed=11)
    teia(img, [(cx + 136, base - 240), (cx + 84, yv + 150), (cx + 136, base - 60)], seed=12)
    teia(img, [(cx - 150, yc - 60), (cx - 60, yv + 30)], seed=13)
    teia(img, [(cx + 150, yc - 80), (cx + 50, yv + 34)], seed=14)
    teia(img, [(cx - 136, base - 150), (cx - 88, yv + 200)], seed=15)
    return recortar(contornar(img))


def montar_casulo():
    w, h = 70, 120
    img = nova(w, h)
    cx, base = w // 2, h - 2
    # toco de pilar quebrado
    alvenaria(img, cx - 14, base - 86, cx + 14, base, seed=17, fiada=14, passo=(12, 22))
    por(img, cx - 14, base - 86, cx - 11, base, S3)
    por(img, cx + 10, base - 86, cx + 14, base, S1)
    por(img, cx - 14, base - 92, cx - 2, base - 86, S2)       # topo quebrado
    por(img, cx + 2, base - 89, cx + 10, base - 86, S2)
    por(img, cx - 18, base - 10, cx + 18, base, S2)
    por(img, cx - 18, base - 10, cx + 18, base - 8, S4)
    # casulo pendurado na frente
    for j in range(46):
        t = (j + 0.5) / 46
        hw = 13 * math.sin(math.pi * (0.12 + 0.8 * t)) ** 0.8
        y = base - 78 + j
        for x in range(int(cx + 4 - hw), int(cx + 4 + hw) + 1):
            u = (x + 0.5 - cx - 4) / max(hw, 1)
            cor = T2 if u < -0.2 else (T1 if u < 0.5 else (104, 160, 196))
            if (x + j * 2) % 7 == 0:
                cor = (104, 160, 196)
            por(img, x, y, x + 1, y + 1, cor)
    teia(img, [(cx - 12, base - 88), (cx + 4, base - 78)], seed=6)
    teia(img, [(cx + 12, base - 86), (cx + 6, base - 76)], seed=7)
    return recortar(contornar(img))


def montar_teia(variante):
    """Teia no chão: raios e anéis vistos de cima (achatados pela câmera), sem contorno preto (é um decalque fino)."""
    w, h = (150, 96) if variante == 0 else (110, 70)
    img = nova(w, h)
    cx, cy = w // 2, h // 2
    n_r = 9 if variante == 0 else 7
    ang0 = 0.3 * variante
    raios = []
    for k in range(n_r):
        a = ang0 + 2 * math.pi * k / n_r + (h2(k, variante, 91) - 0.5) * 0.3
        r = (0.80 + 0.2 * h2(k, variante, 92))
        raios.append((a, r))
        linha(img, cx, cy, cx + math.cos(a) * r * (w / 2 - 3), cy + math.sin(a) * r * (h / 2 - 3), T1)
    for anel in (0.3, 0.52, 0.76):
        for k in range(n_r):
            (a0, r0), (a1, r1) = raios[k], raios[(k + 1) % n_r]
            if h2(k, int(anel * 100), 93 + variante) < 0.18:
                continue      # fio rompido
            x0, y0 = cx + math.cos(a0) * r0 * anel * (w / 2 - 3), cy + math.sin(a0) * r0 * anel * (h / 2 - 3)
            x1, y1 = cx + math.cos(a1) * r1 * anel * (w / 2 - 3), cy + math.sin(a1) * r1 * anel * (h / 2 - 3)
            linha(img, x0, y0, x1, y1, T1)
            por(img, round(x0), round(y0), round(x0) + 2, round(y0) + 2, T2)
    por(img, cx - 1, cy - 1, cx + 2, cy + 2, T2)
    return recortar(img)


def montar_entulho():
    w, h = 110, 60
    img = nova(w, h)
    base = h - 2
    for k, (x, lw, lh) in enumerate([(6, 40, 26), (40, 34, 34), (70, 30, 20), (22, 22, 14), (62, 18, 12)]):
        y = base - lh - (0 if k < 3 else 0)
        if k >= 3:
            y = base - lh
        alvenaria(img, x, y + 8, x + lw, base, seed=30 + k, fiada=9, passo=(12, 22))
        por(img, x, y, x + lw, y + 8, S3)
        por(img, x, y, x + lw, y + 2, S4)
        por(img, x + lw - 4, y + 8, x + lw, base, S1)
        tmp = nova(w, h)
        tmp[y:base, x:x + lw] = img[y:base, x:x + lw]
        contornar(tmp)
        a = (tmp[..., 3] > 0) & (img[..., 3] == 0)
        img[a] = tmp[a]
    return recortar(contornar(img))


def main():
    saidas = {
        "ponte_sino": montar_sino(), "ponte_sino_caido": montar_sino_caido(), "ponte_sino_maior": montar_sino_maior(),
        "ponte_casulo": montar_casulo(), "ponte_teia_0": montar_teia(0), "ponte_teia_1": montar_teia(1), "ponte_entulho": montar_entulho(),
    }
    Image.fromarray(montar_atlas(), "RGBA").save(os.path.join(TILES, "cripta_ponte.png"))
    for nome, img in saidas.items():
        Image.fromarray(img, "RGBA").save(os.path.join(PROPS, nome + ".png"))
        print("%s,res://art2d/props/%s.png,%d,%d,%d,%d" % (nome, nome, img.shape[1], img.shape[0], img.shape[1] // 2, img.shape[0]))
    if "--previas" in sys.argv:
        destino = sys.argv[sys.argv.index("--previas") + 1]
        os.makedirs(destino, exist_ok=True)
        larg = sum(i.shape[1] + 12 for i in saidas.values()) + 12
        alt = max(i.shape[0] for i in saidas.values()) + 24 + 128 * 2
        folha = Image.new("RGBA", (max(larg, 512 + 24), alt), (70, 78, 98, 255))
        x = 12
        for img in saidas.values():
            folha.alpha_composite(Image.fromarray(img, "RGBA"), (x, alt - 12 - img.shape[0] - 256))
            x += img.shape[1] + 12
        at = Image.fromarray(montar_atlas(), "RGBA").resize((512, 256), Image.NEAREST)
        folha.alpha_composite(at, (12, alt - 256))
        folha.save(os.path.join(destino, "ponte_props.png"))
        print("prévia:", os.path.join(destino, "ponte_props.png"))


if __name__ == "__main__":
    main()
