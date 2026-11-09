#!/usr/bin/env python3
"""Visão geral anotada da fase 1 (para revisão de layout): lê `godot/data2d/rooms/fase_1.txt` e desenha a mata, a água, as
lajes, a estrada principal com o tempo de caminhada, a trilha do bolsão, os marcos numerados, os encontros (`@guarda`) e
a vegetação (um ponto por árvore ou arbusto), sem precisar abrir o Godot.

Uso: python3 tools/mapas/visao_geral_fase1.py [saida.png] [escala=8] [mapa.txt]
Requer Pillow. A velocidade do arqueiro (260 px/s) e o tile (64 px) vêm de `godot/data2d/` (player.csv e run_settings.csv).
"""
import csv
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
MAPA = RAIZ / "godot/data2d/rooms/fase_1.txt"
FONTES = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]


def fonte(tam):
    for f in FONTES:
        try:
            return ImageFont.truetype(f, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def valor(arq, chave, padrao):
    try:
        for r in csv.DictReader(open(arq, encoding="utf-8")):
            if r.get("chave") == chave:
                return float(r["valor"])
    except (OSError, KeyError, ValueError):
        pass
    return padrao


def spline(pts, passo=0.25):
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        k = max(int(math.dist(p1, p2) / passo), 2)
        for j in range(k):
            t = j / k
            out.append(tuple(0.5 * ((2 * p1[c]) + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t ** 3) for c in (0, 1)))
    out.append(tuple(pts[-1]))
    return out


def ler(arq):
    linhas = Path(arq).read_text(encoding="utf-8").split("\n")
    grade, i = [], 0
    while i < len(linhas) and not linhas[i].startswith("@"):
        if linhas[i].strip():
            grade.append(linhas[i])
        i += 1
    m = {"grade": grade, "caminhos": [], "riachos": [], "lajes": [], "luzes": [], "guardas": [], "bolsoes": [], "props": []}
    em_props = False
    for l in linhas[i:]:
        l = l.strip()
        if not l:
            continue
        if l == "@props":
            em_props = True
            continue
        q = l.split()
        if em_props:
            m["props"].append((q[0], float(q[1]), float(q[2])))
        elif q[0] in ("@caminho", "@riacho"):
            m["caminhos" if q[0] == "@caminho" else "riachos"].append((float(q[1]), [tuple(map(float, p.split(","))) for p in q[2:]]))
        elif q[0] == "@lajes":
            xy = q[3].split(",")
            m["lajes"].append((q[1], float(q[2]), float(xy[0]), float(xy[1])))
        elif q[0] == "@luz":
            xy = q[1].split(",")
            m["luzes"].append((float(xy[0]), float(xy[1]), float(q[2])))
        elif q[0] == "@guarda":
            xy = q[1].split(",")
            m["guardas"].append((float(xy[0]), float(xy[1]), q[4]))
        elif q[0] == "@bolsao":
            xy = q[1].split(",")
            m["bolsoes"].append((float(xy[0]), float(xy[1])))
    return m


def main():
    saida = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("visao_geral_fase1.png")
    S = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    m = ler(sys.argv[3] if len(sys.argv) > 3 else MAPA)
    tile = valor(RAIZ / "godot/data2d/run_settings.csv", "tile", 64.0)
    vel = 260.0
    try:
        for r in csv.DictReader(open(RAIZ / "godot/data2d/player.csv", encoding="utf-8")):
            if r.get("chave") in ("speed", "move_speed"):
                vel = float(r["valor"])
    except (OSError, KeyError, ValueError):
        pass
    grade = m["grade"]
    H, W = len(grade), len(grade[0])
    topo, base = 56, 92
    img = Image.new("RGB", (W * S, H * S + topo + base), (22, 24, 20))
    d = ImageDraw.Draw(img, "RGBA")
    ox, oy = 0, topo

    def P(x, y):
        return (ox + x * S, oy + y * S)

    d.rectangle([*P(0, 0), *P(W, H)], fill=(70, 76, 48))
    for y in range(H):
        for x in range(W):
            c = grade[y][x]
            if c == "m":
                d.rectangle([*P(x, y), *P(x + 1, y + 1)], fill=(26, 40, 28))
            elif c == "#":
                d.rectangle([*P(x, y), *P(x + 1, y + 1)], fill=(80, 80, 84))
    for tom, r, cx, cy in m["lajes"]:
        cor = (150, 150, 160, 110) if tom == "claro" else (60, 60, 80, 190)
        d.ellipse([*P(cx - r, cy - r), *P(cx + r, cy + r)], fill=cor)
    for larg, pts in m["riachos"]:
        d.line([P(*p) for p in spline(pts)], fill=(70, 120, 190, 255), width=max(3, int(larg * S)), joint="curve")
    for k, (larg, pts) in enumerate(m["caminhos"]):
        linha = [P(*p) for p in spline(pts)]
        d.line(linha, fill=(40, 34, 26, 255), width=max(3, int(larg * S)) + 4, joint="curve")
        d.line(linha, fill=(204, 192, 164, 255) if k == 0 else (190, 176, 146, 255), width=max(3, int(larg * S)), joint="curve")
    # vegetação: um ponto por árvore (verde fundo) e por arbusto/mato (verde claro)
    for pid, x, y in m["props"]:
        if pid.startswith(("tree_", "sapling_")):
            r = max(2, S // 3)
            d.ellipse([P(x, y)[0] - r, P(x, y)[1] - r, P(x, y)[0] + r, P(x, y)[1] + r], fill=(18, 92, 34, 230))
        elif pid.startswith(("bush_", "shrub_")):
            r = max(1, S // 5)
            d.ellipse([P(x, y)[0] - r, P(x, y)[1] - r, P(x, y)[0] + r, P(x, y)[1] + r], fill=(122, 168, 70, 200))
        elif pid.startswith(("pillar", "arco_", "altar", "tomb", "grave", "sarcoph")):
            r = max(2, S // 4)
            d.rectangle([P(x, y)[0] - r, P(x, y)[1] - r, P(x, y)[0] + r, P(x, y)[1] + r], fill=(236, 150, 40, 255))
        elif pid.startswith(("skull", "bones")):
            r = max(1, S // 6)
            d.ellipse([P(x, y)[0] - r, P(x, y)[1] - r, P(x, y)[0] + r, P(x, y)[1] + r], fill=(240, 232, 160, 255))
    for x, y, r in m["luzes"]:
        d.ellipse([*P(x - r, y - r), *P(x + r, y + r)], outline=(255, 190, 90, 90), width=1)
    # braseiros, início, chefe, portal
    marcas = {"B": ((255, 140, 0), "braseiro"), "P": ((0, 255, 0), "início"), "G": ((255, 0, 0), "Guardião"), "X": ((255, 0, 255), "portal")}
    for y in range(H):
        for x in range(W):
            c = grade[y][x]
            if c in marcas:
                cx, cy = P(x + .5, y + .5)
                r = S * (0.9 if c != "B" else 0.55)
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=marcas[c][0] + (255,), fill=marcas[c][0] + (150,), width=2)
    # estrada principal: distância percorrida, com o tempo de caminhada
    estrada = spline(m["caminhos"][0][1], 0.25)
    acum = [0.0]
    for a, b in zip(estrada, estrada[1:]):
        acum.append(acum[-1] + math.dist(a, b))
    comp = acum[-1]
    seg_por_tile = tile / vel
    for tempo in range(5, int(comp * seg_por_tile) + 1, 5):
        alvo = tempo / seg_por_tile
        k = min(range(len(acum)), key=lambda j: abs(acum[j] - alvo))
        x, y = P(*estrada[k])
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(20, 20, 20, 255), outline=(255, 255, 255, 255))
        d.text((x - 6, y + 5), "%ds" % tempo, fill=(255, 255, 255, 255), font=fonte(11), stroke_width=2, stroke_fill=(0, 0, 0, 255))

    def perto_estrada(x, y):
        return min(range(len(estrada)), key=lambda j: (estrada[j][0] - x) ** 2 + (estrada[j][1] - y) ** 2)

    # marcos numerados
    marcos = []
    inicio = next(((x, y) for y in range(H) for x in range(W) if grade[y][x] == "P"), None)
    if inicio:
        marcos.append((inicio[0] + 4.5, inicio[1], "Início: pilares com glifo e braseiros"))
    ponte = None
    for _, pts in m["riachos"][:1]:
        rio = spline(pts, 0.5)
        melhor = min(((math.dist(a, b), a) for a in estrada[::4] for b in rio[::2]), key=lambda t: t[0])
        ponte = melhor[1]
    if ponte:
        marcos.append((ponte[0], ponte[1] - 1.8, "Ponte sobre o riacho (meio do mapa)"))
    ruina = [(x, y) for pid, x, y in m["props"] if pid == "arco_ruina"]
    if ruina:
        marcos.append((ruina[0][0], ruina[0][1] + 1.5, "Ruína: pilares e verga quebrada"))
    if len(m["caminhos"]) > 1:   # a trilha do bolsão sai da estrada; a árvore seca fica do outro lado
        fx, fy = m["caminhos"][1][1][0]
        marcos.append((fx + 1.0, fy + 4.2, "Bifurcação: árvore seca com velas"))
    for bx, by in m["bolsoes"]:
        marcos.append((bx, by - 2.6, "Bolsão: altar, guardas e baú"))
    resp = [(cx, cy) for tom, r, cx, cy in m["lajes"] if tom == "claro" and abs(r - 4.6) < 0.01]
    if resp:
        marcos.append((resp[-1][0], resp[-1][1] + 3.4, "Respiro: clareira com braseiros"))
    portao = [(x, y) for pid, x, y in m["props"] if pid == "arco_portal"]
    if portao:
        marcos.append((portao[0][0] + 4.2, portao[0][1] + 1.0, "Portão: verga, caveiras e brasas"))
    for k, (x, y, txt) in enumerate(marcos, 1):
        cx, cy = P(x, y)
        d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=(15, 15, 25, 235), outline=(255, 214, 120, 255), width=2)
        d.text((cx, cy), str(k), fill=(255, 235, 170, 255), font=fonte(14), anchor="mm")
    # encontros adormecidos
    for x, y, spec in m["guardas"]:
        cx, cy = P(x, y)
        d.polygon([(cx, cy - 6), (cx + 6, cy), (cx, cy + 6), (cx - 6, cy)], fill=(220, 50, 50, 255), outline=(255, 255, 255, 255))
        n = sum(int(p.split(":")[1]) for p in spec.split("|"))
        d.text((cx + 8, cy - 7), str(n), fill=(255, 190, 190, 255), font=fonte(12), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    # régua de tiles
    for x in range(0, W + 1, 10):
        d.line([P(x, 0), P(x, H)], fill=(255, 255, 255, 28))
        d.text((P(x, 0)[0] + 2, oy + 2), str(x), fill=(255, 255, 255, 170), font=fonte(10))
    for y in range(0, H + 1, 10):
        d.line([P(0, y), P(W, y)], fill=(255, 255, 255, 28))
        d.text((2, P(0, y)[1] + 2), str(y), fill=(255, 255, 255, 170), font=fonte(10))
    # cabeçalho e legenda
    d.text((12, 8), "Fase 1: visão geral do mapa (%d x %d tiles)" % (W, H), fill=(255, 235, 190, 255), font=fonte(22))
    d.text((12, 34), "Estrada principal: %.0f tiles, ~%.0f s de caminhada (%.0f px/s)   |   ponto vermelho = encontro adormecido (nº de inimigos)   |   tracejado dourado = alcance da luz de cada marco" % (
        comp, comp * seg_por_tile, vel), fill=(210, 210, 200, 255), font=fonte(12))
    y0 = H * S + topo + 8
    col = 0
    for k, (x, y, txt) in enumerate(marcos, 1):
        cx = 12 + (k - 1) % 4 * (W * S // 4)
        cy = y0 + (k - 1) // 4 * 26
        d.ellipse([cx, cy, cx + 20, cy + 20], fill=(15, 15, 25, 235), outline=(255, 214, 120, 255), width=2)
        d.text((cx + 10, cy + 10), str(k), fill=(255, 235, 170, 255), font=fonte(12), anchor="mm")
        d.text((cx + 28, cy + 3), txt, fill=(235, 235, 225, 255), font=fonte(13))
    img.save(saida)
    print(saida, img.size, "estrada %.0f tiles" % comp)


if __name__ == "__main__":
    main()
