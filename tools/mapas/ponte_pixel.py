#!/usr/bin/env python3
"""Pintura por código da Ponte do Sino (área 3 do Ato I): a paleta da área e a borda do tabuleiro de pedra sobre o abismo.

Direção do Jev (10/11/2026): cada área tem uma cor própria (Cripta verde-escuro, Pedreira ocre, Ponte AZUL-ACINZENTADO), com o
quente só no bronze dos sinos e nos lampiões. O abismo e a névoa são só visuais.

`pintar_bordas(deck)` recebe a grade booleana do tabuleiro (True = chão andável) e devolve uma imagem do mapa inteiro, transparente
fora das bordas, com:
  - a face sul (o que a câmera 3/4 vê da lateral da ponte): cornija, fiadas de blocos que escurecem para baixo e somem no abismo em
    pontilhado, arcos escuros entre os pilares e um pilar a cada 6 tiles descendo mais fundo;
  - o parapeito norte (murada baixa atrás de quem anda), com trechos quebrados;
  - meio-fio a oeste, a leste e ao sul.
Mesma linguagem dos outros cenários por código: grade de 1 px de mundo, alfa binário, paleta curta, luz de cima à esquerda.
"""
import numpy as np

TILE = 64
# pedra azul-acinzentada (do mais escuro ao mais claro)
S0, S1, S2, S3, S4 = (26, 30, 44), (52, 60, 82), (84, 96, 122), (120, 134, 160), (160, 174, 196)
S2B = (76, 86, 112)             # segundo tom médio: blocos vizinhos não ficam iguais
A0, A1, A2 = (10, 13, 24), (16, 21, 36), (24, 31, 50)   # abismo
K0 = (0, 0, 0)
# bronze de sino e pátina (os mesmos tons da Tecelã)
B0, B1, B2, B3, B4 = (64, 42, 40), (98, 62, 44), (136, 90, 52), (176, 124, 66), (214, 164, 92)
P0, P1, P2 = (38, 76, 86), (52, 110, 112), (78, 150, 140)
W0, W1, W2, W3 = (40, 30, 30), (70, 54, 46), (104, 82, 62), (140, 114, 84)   # madeira e corda
T1, T2 = (160, 214, 232), (226, 246, 250)                                   # teia
ABISMO = A1

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) / 16.0 + 1.0 / 32.0


def h2(x, y, s=0):
    """Hash inteiro determinístico -> [0, 1)."""
    h = (int(x) * 73856093) ^ (int(y) * 19349663) ^ (int(s) * 83492791)
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0


def por(img, x0, y0, x1, y1, cor):
    """Retângulo [x0, x1) x [y0, y1), recortado na imagem."""
    H, W = img.shape[:2]
    x0, y0, x1, y1 = max(int(x0), 0), max(int(y0), 0), min(int(x1), W), min(int(y1), H)
    if x1 > x0 and y1 > y0:
        img[y0:y1, x0:x1, :3] = cor
        img[y0:y1, x0:x1, 3] = 255


def alvenaria(img, x0, y0, x1, y1, seed=0, fiada=16, tons=(S2, S2B, S1), junta=S0, luz=S3, passo=(26, 44)):
    """Parede de blocos de pedra vista de frente: fiadas com juntas, cada bloco com aresta de luz em cima e à esquerda."""
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    por(img, x0, y0, x1, y1, junta)
    r = 0
    y = y0
    while y < y1:
        ya = min(y + fiada, y1)
        x = x0 - int(h2(r, seed, 1) * passo[0])
        k = 0
        while x < x1:
            w = int(passo[0] + h2(k, r, seed + 2) * (passo[1] - passo[0]))
            xa, xb = max(x + 1, x0), min(x + w, x1)
            if xb > xa and ya - 1 > y + 1:
                v = h2(k, r, seed + 3)
                cor = tons[0] if v < 0.55 else (tons[1] if v < 0.85 else tons[2])
                por(img, xa, y + 1, xb, ya, cor)
                if cor != tons[2]:
                    por(img, xa, y + 1, xb, y + 2, luz)
                    por(img, xa, y + 2, xa + 1, ya - 1, luz)
                if h2(k, r, seed + 4) < 0.22 and xb - xa > 12:      # lasca ou trinca
                    cx = xa + 3 + int(h2(k, r, seed + 5) * (xb - xa - 8))
                    por(img, cx, y + 4, cx + 1, ya - 2, junta)
                    por(img, cx + 1, y + 6, cx + 2, ya - 4, junta)
            x += w
            k += 1
        y = ya
        r += 1


def escurecer(img, x0, y0, x1, y1, mapa):
    """Troca cores por outras (dict cor -> cor) num retângulo: sombra sem inventar tom novo."""
    H, W = img.shape[:2]
    x0, y0, x1, y1 = max(int(x0), 0), max(int(y0), 0), min(int(x1), W), min(int(y1), H)
    if x1 <= x0 or y1 <= y0:
        return
    reg = img[y0:y1, x0:x1]
    for de, para in mapa.items():
        m = (reg[..., 0] == de[0]) & (reg[..., 1] == de[1]) & (reg[..., 2] == de[2]) & (reg[..., 3] > 0)
        reg[m, :3] = para


SOMBRA = {S4: S3, S3: S2, S2: S1, S2B: S1, S1: S0}


def sumir(img, x0, y0, x1, y1, cor=None):
    """Pontilhado (Bayer) que apaga a pintura de cima para baixo: o que desce some no abismo. Com `cor`, em vez de apagar, pinta."""
    H, W = img.shape[:2]
    x0, y0, x1, y1 = max(int(x0), 0), max(int(y0), 0), min(int(x1), W), min(int(y1), H)
    if x1 <= x0 or y1 <= y0:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1]
    t = (ys - y0 + 0.5) / float(y1 - y0)
    m = t > BAYER[ys % 4, xs % 4]
    reg = img[y0:y1, x0:x1]
    if cor is None:
        reg[m, 3] = 0
        reg[m, :3] = 0
    else:
        m &= reg[..., 3] > 0
        reg[m, :3] = cor


def pintar_bordas(deck, semente=3):
    """deck: matriz booleana (linhas x colunas). Devolve RGBA (linhas*64, colunas*64) só com as bordas do tabuleiro."""
    H, W = deck.shape
    img = np.zeros((H * TILE, W * TILE, 4), np.uint8)

    def d(x, y):
        return 0 <= x < W and 0 <= y < H and bool(deck[y, x])

    FACE = 86          # altura das fiadas visíveis da face sul
    # ---------------- face sul ----------------
    for y in range(H):
        x = 0
        while x < W:
            if d(x, y) and not d(x, y + 1):
                xa = x
                while x < W and d(x, y) and not d(x, y + 1):
                    x += 1
                px0, px1, py = xa * TILE, x * TILE, (y + 1) * TILE
                alvenaria(img, px0, py + 6, px1, py + FACE, seed=semente + y)
                # as fiadas escurecem para baixo
                escurecer(img, px0, py + 38, px1, py + FACE, SOMBRA)
                escurecer(img, px0, py + 64, px1, py + FACE, SOMBRA)
                # arcos entre pilares (um vão a cada 6 tiles): a parte de baixo da face é o escuro do arco
                vao = 6 * TILE
                for ax in range((px0 // vao) * vao, px1, vao):
                    cx = ax + vao // 2
                    rx, ry = vao // 2 - 34, 46
                    x_a, x_b = max(ax + 34, px0), min(ax + vao - 34, px1)
                    if x_b <= x_a:
                        continue
                    xs = np.arange(x_a, x_b)
                    topo = py + FACE - (ry * np.sqrt(np.clip(1.0 - ((xs + 0.5 - cx) / rx) ** 2, 0, 1))).astype(int)
                    for xx, tp in zip(xs, topo):
                        if tp < py + FACE:
                            img[tp:py + FACE, xx, :3] = A0
                            img[tp:py + FACE, xx, 3] = 255
                            img[max(tp - 2, py + 8):tp, xx, :3] = S0      # aduela (a borda do arco)
                    # pilar: desce mais fundo e some em pontilhado
                    p0, p1 = max(ax - 30, px0), min(ax + 30, px1)
                    if p1 - p0 >= 16:
                        alvenaria(img, p0, py + FACE, p1, py + FACE + 150, seed=semente + ax, tons=(S1, S1, S0), junta=A0, luz=S2)
                        escurecer(img, p0, py + FACE + 60, p1, py + FACE + 150, SOMBRA)
                        sumir(img, p0, py + FACE + 70, p1, py + FACE + 150)
                        por(img, p0, py + FACE, p0 + 1, py + FACE + 70, K0)
                        por(img, p1 - 1, py + FACE, p1, py + FACE + 70, K0)
                sumir(img, px0, py + FACE - 22, px1, py + FACE, cor=A0)
                # cornija e meio-fio sul (por cima da beira do chão)
                por(img, px0, py - 7, px1, py - 6, K0)
                por(img, px0, py - 6, px1, py - 1, S3)
                por(img, px0, py - 6, px1, py - 5, S4)
                por(img, px0, py - 1, px1, py + 4, S2)
                por(img, px0, py + 4, px1, py + 6, K0)
                for jx in range(px0 + int(h2(y, xa, 7) * 40), px1, 46):      # juntas da cornija
                    por(img, jx, py - 6, jx + 1, py + 4, S1)
                # contorno das pontas
                if not d(xa - 1, y) or d(xa - 1, y + 1):
                    por(img, px0, py - 7, px0 + 1, py + FACE, K0)
                if not d(x, y) or d(x, y + 1):
                    por(img, px1 - 1, py - 7, px1, py + FACE, K0)
            else:
                x += 1
    # ---------------- parapeito norte ----------------
    ALT = 20
    for y in range(H):
        for x in range(W):
            if not (d(x, y) and not d(x, y - 1)):
                continue
            px0, px1, py = x * TILE, (x + 1) * TILE, y * TILE
            quebrado = h2(x, y, semente + 11) < 0.16
            if quebrado:
                # trecho caído: só a base e dois cacos
                por(img, px0, py - 2, px1, py + 5, S1)
                por(img, px0, py - 3, px1, py - 2, K0)
                por(img, px0, py + 5, px1, py + 6, K0)
                for k in range(3):
                    cx = px0 + 6 + int(h2(x, k, semente + 12) * 44)
                    cy = py + 8 + int(h2(x, k, semente + 13) * 12)
                    por(img, cx - 1, cy - 1, cx + 9, cy + 6, K0)
                    por(img, cx, cy, cx + 8, cy + 5, S2)
                    por(img, cx, cy, cx + 8, cy + 1, S3)
                continue
            por(img, px0, py - ALT - 1, px1, py + 7, K0)
            por(img, px0, py - ALT, px1, py - ALT + 8, S3)          # topo da murada
            por(img, px0, py - ALT, px1, py - ALT + 1, S4)
            alvenaria(img, px0, py - ALT + 8, px1, py + 6, seed=semente + x * 3 + y, fiada=7, passo=(18, 30))
            if not d(x - 1, y) or d(x - 1, y - 1):
                por(img, px0, py - ALT - 1, px0 + 1, py + 7, K0)
            if not d(x + 1, y) or d(x + 1, y - 1):
                por(img, px1 - 1, py - ALT - 1, px1, py + 7, K0)
            if x % 4 == 0:                                            # pilarete
                por(img, px0 + 22, py - ALT - 9, px0 + 44, py + 8, K0)
                por(img, px0 + 23, py - ALT - 8, px0 + 43, py - ALT + 2, S4)
                por(img, px0 + 23, py - ALT + 2, px0 + 43, py + 7, S2)
                por(img, px0 + 23, py - ALT + 2, px0 + 25, py + 7, S3)
                por(img, px0 + 39, py - ALT + 2, px0 + 43, py + 7, S1)
    # ---------------- meio-fio oeste e leste ----------------
    for y in range(H):
        for x in range(W):
            if not d(x, y):
                continue
            py0, py1 = y * TILE, (y + 1) * TILE
            for lado, viz in ((-1, d(x - 1, y)), (1, d(x + 1, y))):
                if viz:
                    continue
                xa = x * TILE - 3 if lado < 0 else (x + 1) * TILE - 7
                ya = py0 - (ALT if not d(x, y - 1) else 0)
                por(img, xa - 1, ya, xa + 11, py1 + (5 if not d(x, y + 1) else 0), K0)
                por(img, xa, ya, xa + 10, py1 + (4 if not d(x, y + 1) else 0), S3)
                por(img, xa, ya, xa + 2, py1, S4)
                por(img, xa + 7, ya, xa + 10, py1 + (4 if not d(x, y + 1) else 0), S1)
                for jy in range(py0 + int(h2(x, y, 21) * 30), py1, 34):
                    por(img, xa, jy, xa + 10, jy + 1, S1)
    return img


def recortar_blocos(img, lado=1024):
    """Corta a imagem em blocos de `lado` px e devolve [(x, y, recorte)] só dos que têm pintura (cada um reduzido à sua caixa)."""
    out = []
    H, W = img.shape[:2]
    for by in range(0, H, lado):
        for bx in range(0, W, lado):
            reg = img[by:by + lado, bx:bx + lado]
            a = reg[..., 3] > 0
            if not a.any():
                continue
            ys, xs = np.where(a)
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            out.append((bx + int(x0), by + int(y0), reg[y0:y1, x0:x1].copy()))
    return out
