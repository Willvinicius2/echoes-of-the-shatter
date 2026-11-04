"""Teste v7: piso de laje (32x32, ladrilha) e brasseiro de pedra (32x48) em pixel art feito pixel a pixel,
com a mesma paleta quente/escura do arqueiro e cena de comparação com o arqueiro v7.
Uso: python gerar_cenario_pixel_teste.py <pasta_saida> <folha_arqueiro_idle.png>"""
import os, random, sys
from PIL import Image

def H(s): s = s.lstrip("#"); return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))
PEDRA = [H("1d1a22"), H("2e2a36"), H("423d4c"), H("5a5466"), H("77708a")]
LIMO = [H("1f2a1c"), H("34502a"), H("55793a")]
FOGO = [H("7a1f12"), H("c8421a"), H("f58a22"), H("ffd24a"), H("fff3b0")]

def piso(n=32, semente=11):
    """Lajes irregulares (Voronoi com borda toroidal, ladrilha sem emenda): junta escura, chanfro claro em cima e à esquerda."""
    r = random.Random(semente)
    sem = [(r.uniform(0, n), r.uniform(0, n)) for _ in range(7)]
    tom = [r.choice([1, 2, 2, 2, 3]) for _ in sem]
    def cel(x, y):
        best, bi, sec = 1e9, 0, 1e9
        for i, (sx, sy) in enumerate(sem):
            dx = min(abs(x - sx), n - abs(x - sx)); dy = min(abs(y - sy), n - abs(y - sy))
            d = dx * dx + dy * dy * 1.3
            if d < best: sec, best, bi = best, d, i
            elif d < sec: sec = d
        return bi, sec ** .5 - best ** .5
    im = Image.new("RGBA", (n, n)); px = im.load()
    ids = [[cel(x, y) for x in range(n)] for y in range(n)]
    for y in range(n):
        for x in range(n):
            i, gap = ids[y][x]
            if gap < 1.6: c = PEDRA[0]
            else:
                up = ids[(y - 1) % n][x][0]; lf = ids[y][(x - 1) % n][0]
                dn = ids[(y + 1) % n][x][0]; rt = ids[y][(x + 1) % n][0]
                c = PEDRA[tom[i]]
                if gap < 3.2 and (up != i or lf != i or ids[(y - 2) % n][x][0] != i and gap < 2.4): c = PEDRA[min(tom[i] + 1, 4)]
                elif gap < 3.2 and (dn != i or rt != i): c = PEDRA[max(tom[i] - 1, 1)]
            px[x, y] = c + (255,)
    for (x, y) in [(5, 4), (6, 5), (6, 6), (7, 7), (7, 8), (8, 9)]:
        px[x, y] = PEDRA[0] + (255,)
    for (x, y) in [(24, 20), (25, 20), (24, 21), (26, 21), (25, 22)]:
        px[x, y] = LIMO[1 + (x + y) % 2] + (255,)
    return im

def brasseiro():
    W, Hh = 32, 48
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); px = im.load()
    def rect(x0, y0, x1, y1, cor):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                px[x, y] = cor + (255,)
    # sombra
    for y in range(41, 46):
        for x in range(6, 26):
            if ((x - 16) / 10) ** 2 + ((y - 43.5) / 2.5) ** 2 <= 1: px[x, y] = (0, 0, 0, 90)
    # base
    rect(9, 38, 22, 42, PEDRA[2]); rect(9, 38, 22, 38, PEDRA[3]); rect(9, 42, 22, 42, PEDRA[0]); rect(9, 38, 9, 42, PEDRA[3]); rect(22, 39, 22, 42, PEDRA[1])
    # coluna
    rect(12, 22, 19, 37, PEDRA[2]); rect(12, 22, 13, 37, PEDRA[3]); rect(18, 22, 19, 37, PEDRA[1]); rect(19, 22, 19, 37, PEDRA[0]); rect(12, 22, 12, 37, PEDRA[4])
    for y in (27, 32): rect(12, y, 19, y, PEDRA[0])
    # runa brilhante
    for y in range(28, 31): px[15, y] = FOGO[3] + (255,); px[16, y] = FOGO[2] + (255,)
    # bacia
    rect(8, 17, 23, 21, PEDRA[2]); rect(8, 17, 23, 17, PEDRA[4]); rect(8, 21, 23, 21, PEDRA[0]); rect(8, 17, 8, 21, PEDRA[3]); rect(22, 18, 23, 21, PEDRA[1])
    rect(10, 16, 21, 16, PEDRA[0])
    # brasas na borda e chama
    rect(11, 15, 20, 15, FOGO[1])
    chama = [(14, 5, 17, 5, 1), (13, 6, 18, 6, 2), (12, 7, 19, 7, 2), (12, 8, 19, 9, 2), (11, 10, 20, 12, 2), (11, 13, 20, 14, 1)]
    for x0, y0, x1, y1, c in chama: rect(x0, y0, x1, y1, FOGO[c])
    rect(13, 8, 18, 14, FOGO[3]); rect(14, 10, 17, 14, FOGO[4]); rect(15, 3, 16, 4, FOGO[2]); rect(15, 2, 15, 2, FOGO[1])
    # contorno externo escuro da chama
    novos = []
    for y in range(16):
        for x in range(W):
            if px[x, y][3] == 0:
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    xx, yy = x+dx, y+dy
                    if 0 <= xx < W and 0 <= yy < 16 and px[xx, yy][3] == 255:
                        novos.append((x, y)); break
    for x, y in novos: px[x, y] = FOGO[0] + (255,)
    return im

def cena(saida, folha, esc=6):
    F = 72
    arq = Image.open(folha).crop((0, 0, F, F))   # S, quadro 0
    arq2 = Image.open(folha).crop((0, 3 * F, F, 4 * F))  # NE
    pis = piso(); br = brasseiro()
    W, Hh = 192, 108   # 1/ (360/108 ~ 3.3) escala: recorte de 16:9 do mundo
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 255))
    for y in range(0, Hh, 32):
        for x in range(0, W, 32): im.paste(pis, (x, y))
    # brilho do braseiro no chão: 3 faixas com dither de Bayer 2x2 (pixel art, sem gradiente liso)
    cx, cy = 156, 72
    bayer = [[0, 2], [3, 1]]
    px = im.load()
    for y in range(Hh):
        for x in range(W):
            d = (((x - cx) / 40.0) ** 2 + ((y - cy) / 20.0) ** 2) ** 0.5
            if d < 1.0:
                nivel = (1.0 - d) * 4.0 - bayer[y % 2][x % 2] * 0.25
                if nivel > 0.3:
                    a = 0.10 if nivel < 1.2 else 0.20 if nivel < 2.4 else 0.32
                    r, g, b, _ = px[x, y]
                    px[x, y] = (int(r + (FOGO[2][0] - r) * a), int(g + (FOGO[2][1] - g) * a), int(b + (FOGO[2][2] - b) * a), 255)
    im.alpha_composite(br, (140, 30)); im.alpha_composite(arq, (40, 24)); im.alpha_composite(arq2, (92, 40))
    im.resize((W * esc, Hh * esc), Image.NEAREST).save(os.path.join(saida, "cena_teste_v7.png"))

if __name__ == "__main__":
    s = sys.argv[1]; os.makedirs(s, exist_ok=True)
    piso().save(os.path.join(s, "piso_laje_32.png")); brasseiro().save(os.path.join(s, "brasseiro_32x48.png"))
    cena(s, sys.argv[2])
