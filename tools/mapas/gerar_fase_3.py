#!/usr/bin/env python3
"""Gera godot/data2d/rooms/fase_3.txt: a Ponte do Sino (área 3 do Ato I), e os PNG da borda do tabuleiro (godot/art2d/ponte/).

Direção da thread "Direção visual com o Jev" (10/11/2026; texto em docs/arte/37_ponte_do_sino.md):
  - ponte de pedra sobre o abismo, com névoa, ao entardecer frio; a cor da área é o azul-acinzentado e o quente fica só no bronze
    dos sinos e nos lampiões;
  - os trechos estreitos têm pelo menos 8 tiles de largura jogável (para esquivar de lado diante dos arqueiros) e as praças de
    sino têm 16 x 12 ou mais; o abismo dos dois lados é só visual (não há queda que mata);
  - 6 encontros; o elenco é o Filhote de Cascalho (exclusivo da área), arqueiros fantasmas, morcegos e espectros, com a Sentinela
    Oca como peso; nada de Arauto de Pedra (seria a Pedreira de novo); a chefe é a Tecelã de Cascalho, sob o Sino Maior.

O tabuleiro é uma união de retângulos (vãos e praças), alinhado à grade, para a borda pintada (tools/mapas/ponte_pixel.py) casar
com as células. Fora dele tudo é abismo: `f` (bloqueia o passo, flecha e magia passam por cima) e `m` só na moldura do mapa.
Espinha (x para a direita, y para baixo, em tiles):
  cabeceira (início) -> vão 1 -> Praça dos Vigias (sino no pórtico) -> vão 2 (os atiradores) -> Praça do Sino Caído (ninho, com o
  balcão do baú ao sul) -> vão 3 -> descanso (braseiros) -> vão 4 -> a Praça do Sino Maior: G (a Tecelã) e X (o portal).
O mapa é fixo e sai igual a cada execução. Uso: python3 -I tools/mapas/gerar_fase_3.py [--visao arquivo.png]. Ao fim ele escreve os
pontos de captura (`captura ...`) que godot/scripts2d/tools/captura_marcos_2d.gd aceita.
"""
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from marcos_fase1 import Curva   # noqa: E402
import ponte_pixel               # noqa: E402

RAIZ = AQUI.parents[1]
SAIDA = RAIZ / "godot/data2d/rooms/fase_3.txt"
PASTA_ARTE = RAIZ / "godot/art2d/ponte"
RES_ARTE = "res://art2d/ponte/"
TILE = 64
W, H = 180, 50
rng = random.Random(3303)
RAIO_GUARDA = 260
LARG_ESTRADA = 2.4
BRILHO_ESTRADA = 1.12

# Tabuleiro: (nome, x0, y0, x1, y1), células [x0, x1) x [y0, y1)
PARTES = [
    ("cabeceira", 6, 19, 22, 33),
    ("vao1", 22, 22, 44, 30),
    ("praca_vigias", 44, 15, 62, 30),
    ("vao2", 62, 16, 86, 24),
    ("praca_caido", 86, 14, 106, 28),
    ("balcao", 92, 28, 100, 34),
    ("vao3", 106, 19, 132, 28),
    ("descanso", 132, 16, 146, 28),
    ("vao4", 146, 19, 153, 27),
    ("arena", 153, 12, 174, 36),
]
P = (12, 26)
ESTRADA = [(7, 26), (22, 26), (40, 26), (47, 24.5), (56, 21), (62, 20), (84, 20), (90, 20.6), (102, 22.4), (108, 23.5), (130, 23.5),
           (136, 22.6), (144, 23), (152, 23), (158, 23.4), (163, 23.6)]
ELITE = (163, 23)                 # G: a Tecelã espera sob o Sino Maior
PORTAL = (163, 32)                # X: o portal, do outro lado da arena
SINO_MAIOR = (163.0, 14.4)        # pé do arco do Sino Maior (na beira norte da arena)
BOLSAO = (96.0, 31.2)

deck = np.zeros((H, W), bool)
for _, x0, y0, x1, y1 in PARTES:
    deck[y0:y1, x0:x1] = True
ret = {n: (x0, y0, x1, y1) for n, x0, y0, x1, y1 in PARTES}

grade = [["f"] * W for _ in range(H)]
for y in range(H):
    for x in range(W):
        if deck[y, x]:
            grade[y][x] = "."
        elif min(x, y, W - 1 - x, H - 1 - y) < 2:
            grade[y][x] = "m"


def celula(u):
    return int(math.floor(u + 0.5))


estrada = Curva(ESTRADA)


def em(s, lat=0.0):
    return estrada.em(s, lat)


def marcar(x, y, c):
    xi, yi = celula(x), celula(y)
    if grade[yi][xi] != ".":
        raise SystemExit("marcador %r em célula %r (%g, %g)" % (c, grade[yi][xi], x, y))
    grade[yi][xi] = c
    return xi, yi


# --------------------------------------------------------------------------------------------------------------------
# Props
# --------------------------------------------------------------------------------------------------------------------
RAIO = {"ponte_sino": 1.6, "ponte_sino_caido": 2.4, "ponte_sino_maior": 3.6, "ponte_casulo": 0.4, "ponte_entulho": 0.8,
        "pedreira_poste_lanterna": 0.35, "rock_rubble": 0.55, "rock_slabs": 0.7, "pillar_broken": 0.6, "pillar_cracked": 0.55,
        "pillar_fallen": 0.9, "skull_pile": 0.4, "bones_ribcage": 0.5}
BAIXOS = {"ponte_teia_0", "ponte_teia_1", "rock_rubble", "bones_scattered", "skull_single", "skull_pair", "bones_chains", "skeleton_curled"}
props = []            # [id, x, y, flip, raio]
luzes, guardas, bolsoes, lajes, decalques = [], [], [], [], []
capturas = {}
LUZ_LAMPIAO = (1.0, 0.58, 0.22, 0.28)


def dist_estrada(x, y):
    return estrada.distancia(x, y)


def livre(ident, x, y, raio):
    xi, yi = celula(x), celula(y)
    if not (2 <= xi < W - 2 and 2 <= yi < H - 2) or grade[yi][xi] != ".":
        return False
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if grade[yi + dy][xi + dx] in "BPEXG":
                return False
    if ident not in BAIXOS and dist_estrada(x, y) < 1.6 + raio:
        return False
    if math.hypot(x - P[0], y - P[1]) < 3.0:
        return False
    for it in props:
        if math.hypot(it[1] - x, it[2] - y) < (raio + it[4]) * 0.95:
            return False
    return True


def pôr(ident, x, y, flip=False, forcar=False):
    raio = RAIO.get(ident, 0.45)
    if not forcar and not livre(ident, x, y, raio):
        return False
    props.append([ident, round(x, 2), round(y, 2), flip, raio])
    return True


def lampiao(x, y, flip=False):
    pôr("pedreira_poste_lanterna", x, y, flip, forcar=True)
    luzes.append((x + (-0.55 if flip else 0.55), y - 1.0, 3.6, LUZ_LAMPIAO))


def braseiro(x, y):
    return marcar(x, y, "B")


def centro(nome):
    x0, y0, x1, y1 = ret[nome]
    return ((x0 + x1 - 1) / 2.0, (y0 + y1 - 1) / 2.0)


# ---- Cabeceira: o arqueiro nasce entre dois braseiros, com a ponte à frente ----
grade[P[1]][P[0]] = "P"
lajes.append(("claro", 4.6, P[0] + 1.5, P[1]))
braseiro(15, 23)
braseiro(15, 29)
pôr("pillar_broken", 9.0, 21.4, forcar=True)
pôr("pillar_cracked", 9.2, 31.2, True, forcar=True)
pôr("ponte_entulho", 18.5, 20.6, forcar=True)
lampiao(21.0, 22.4)
lampiao(21.0, 30.4, True)
capturas["1_inicio"] = (P[0], P[1], ":d")

# ---- lampiões dos vãos: na murada norte, um a cada ~9 tiles; o do lado sul fica deslocado ----
for nome in ("vao1", "vao2", "vao3"):
    x0, y0, x1, y1 = ret[nome]
    for k, x in enumerate(range(x0 + 5, x1 - 3, 9)):
        lampiao(x + 0.2, y0 + 0.35, k % 2 == 1)
    for x in range(x0 + 9, x1 - 3, 13):
        pôr("ponte_entulho" if (x // 13) % 2 else "rock_slabs", x + 0.3, y1 - 0.9, x % 2 == 0, forcar=True)

# ---- Praça dos Vigias: o sino no pórtico, dois braseiros e as primeiras teias ----
cx, cy = centro("praca_vigias")
x0, y0, x1, y1 = ret["praca_vigias"]
pôr("ponte_sino", cx, y0 + 3.4, forcar=True)
lajes.append(("claro", 5.4, cx, cy + 0.6))
lajes.append(("escuro", 2.2, cx, y0 + 3.6))
luzes.append((cx, y0 + 2.4, 4.2, (1.0, 0.62, 0.26, 0.24)))
braseiro(cx - 5, y0 + 5)
braseiro(cx + 5, y0 + 5)
pôr("ponte_teia_1", cx - 6.4, y0 + 1.6, forcar=True)
pôr("ponte_teia_0", cx + 6.2, y1 - 2.2, True, forcar=True)
pôr("ponte_casulo", x1 - 1.6, y0 + 1.4, forcar=True)
pôr("pillar_cracked", x0 + 1.4, y0 + 1.6, forcar=True)
pôr("pillar_broken", x0 + 1.4, y1 - 1.2, True, forcar=True)
capturas["2_praca_dos_vigias"] = (cx - 2.5, cy + 2.2, ":g:cy-150")

# ---- Praça do Sino Caído: o ninho (sino rachado no chão, casulos e teias) e o balcão do baú ----
cx, cy = centro("praca_caido")
x0, y0, x1, y1 = ret["praca_caido"]
pôr("ponte_sino_caido", cx + 0.4, cy - 1.2, forcar=True)
lajes.append(("escuro", 3.6, cx, cy - 0.5))
for dx, dy, fl in [(-7.6, -5.0, False), (-5.0, -5.6, True), (6.4, -5.4, False), (8.2, -2.0, True), (-8.2, 3.8, False), (7.4, 4.6, True)]:
    pôr("ponte_casulo", cx + dx, cy + dy, fl, forcar=True)
for dx, dy, v in [(-4.6, -1.0, 0), (4.8, 1.8, 0), (-1.0, 4.4, 1), (2.6, -4.6, 1), (-7.0, 1.2, 1), (7.6, -4.0, 1)]:
    pôr("ponte_teia_%d" % v, cx + dx, cy + dy, dx > 0, forcar=True)
pôr("bones_ribcage", cx - 3.2, y0 + 3.6, forcar=True)
pôr("skull_pile", cx + 4.4, y0 + 2.4, forcar=True)
luzes.append((cx + 0.4, cy - 2.4, 5.0, (0.55, 0.8, 1.0, 0.2)))       # o ninho tem a luz fria da teia, não fogo
capturas["4_praca_do_sino_caido"] = (cx - 3.0, cy + 2.6, ":g:cy-140")
bx, by = BOLSAO
bolsoes.append((bx, by, "bau"))
pôr("ponte_casulo", bx - 2.8, by - 1.4, forcar=True)
pôr("ponte_casulo", bx + 2.8, by - 1.0, True, forcar=True)
pôr("ponte_teia_1", bx - 0.4, by - 2.0, forcar=True)
luzes.append((bx, by - 0.4, 3.6, (1.0, 0.6, 0.24, 0.3)))
guardas.append((bx, by - 2.2, RAIO_GUARDA, 1.1, "gravel_spiderling:4"))
capturas["bolsao"] = (bx, by - 3.6, ":g:cy90")

# ---- Descanso: braseiros e laje clara antes da arena ----
cx, cy = centro("descanso")
x0, y0, x1, y1 = ret["descanso"]
lajes.append(("claro", 4.4, cx, cy))
braseiro(cx - 3, y0 + 2)
braseiro(cx + 3, y0 + 2)
braseiro(cx - 3, y1 - 3)
braseiro(cx + 3, y1 - 3)
pôr("pillar_fallen", cx - 0.2, y0 + 1.2, forcar=True)
pôr("ponte_entulho", x0 + 1.6, y1 - 1.0, forcar=True)
capturas["5_descanso"] = (cx - 2.0, cy + 1.0, "")

# ---- Praça do Sino Maior: a arena da Tecelã ----
cx, cy = centro("arena")
x0, y0, x1, y1 = ret["arena"]
pôr("ponte_sino_maior", SINO_MAIOR[0], SINO_MAIOR[1], forcar=True)
lajes.append(("claro", 8.6, cx, cy - 0.5))
lajes.append(("escuro", 4.3, cx, cy - 0.5))
luzes.append((ELITE[0], ELITE[1] + 0.2, 3.2, (1.0, 0.5, 0.18, 0.26)))   # poço de luz quente nos pés da chefe (o bronze acende)
for dx, dy in [(-7.5, -6.0), (7.5, -6.0), (-7.5, 7.0), (7.5, 7.0)]:
    braseiro(cx + dx, cy + dy)
for dx, dy, fl in [(-9.2, -9.6, False), (9.0, -9.4, True), (-9.4, 0.4, False), (9.2, 1.0, True), (-9.0, 10.4, False), (9.0, 10.2, True),
                   (-4.6, -9.8, True), (4.8, -9.8, False)]:
    pôr("ponte_casulo", cx + dx, cy + dy, fl, forcar=True)
for dx, dy, v in [(-5.6, -3.4, 0), (5.8, -2.6, 0), (-6.2, 4.4, 0), (5.4, 5.6, 0), (0.4, 8.6, 1), (-2.6, -7.0, 1), (3.0, -6.6, 1), (-8.6, -4.0, 1), (8.4, 4.0, 1)]:
    pôr("ponte_teia_%d" % v, cx + dx, cy + dy, dx > 0, forcar=True)
G_CEL = marcar(*ELITE, "G")
X_CEL = marcar(*PORTAL, "X")
capturas["6_sino_maior_com_a_tecela"] = (ELITE[0] - 3.4, ELITE[1] + 6.0, ":e:cx140:cy-260")
capturas["6a_arena"] = (ELITE[0] - 2.0, ELITE[1] + 4.0, ":e:cx0:cy-190")

# ---- Encontros: 6 na espinha (o primeiro com 3), mais o do balcão do baú ----
ENCONTROS = [
    ("vao1", 0.0, 0.85, "gravel_spiderling:3"),
    ("praca_vigias", 3.0, 0.95, "gravel_spiderling:3|ghost_archer:1"),
    ("vao2", 0.0, 1.0, "ghost_archer:2|wandering_ghost:1"),
    ("praca_caido", 2.5, 1.05, "gravel_spiderling:5|hollow_sentinel:1"),
    ("vao3", 0.0, 1.1, "ghost_archer:2|crypt_bat:3"),
    ("vao4", 0.0, 1.2, "hollow_sentinel:2|gravel_spiderling:3"),
]
for nome, dy, forca, spec in ENCONTROS:
    cx, cy = centro(nome)
    guardas.append((cx, cy + dy, RAIO_GUARDA, forca, spec))
cx, cy = centro("vao2")
capturas["3_vao_dos_atiradores"] = (cx - 6.0, cy + 0.5, ":g")
cx, cy = centro("vao1")
capturas["1a_primeiro_vao"] = (cx - 5.0, cy + 0.6, ":g")

# ---- Pontos E (fluxo por etapas) ----
for nome in ("vao1", "praca_vigias", "vao2", "praca_caido", "vao3", "descanso", "arena"):
    x0, y0, x1, y1 = ret[nome]
    for ex, ey in ((x0 + 2, y0 + 1), (x1 - 3, y1 - 2)):
        if grade[ey][ex] == "." and all(math.hypot(it[1] - ex, it[2] - ey) > 1.6 for it in props):
            grade[ey][ex] = "E"

# ---- Chão: entulho, ossos e teias soltas (pouco: a ponte é varrida pelo vento) ----
CHAO = ["ponte_entulho", "bones_scattered", "skull_single", "ponte_teia_1", "ponte_teia_0", "bones_chains"]
feitos = 0
for _ in range(4000):
    if feitos >= 70:
        break
    x, y = round(rng.uniform(7, W - 7), 1), round(rng.uniform(13, H - 13), 1)
    ident = rng.choice(CHAO)
    if dist_estrada(x, y) < 1.9:
        continue
    if pôr(ident, x, y, rng.random() < 0.5):
        feitos += 1
feitos = 0
for _ in range(3000):                    # cacos de parapeito junto das beiras
    if feitos >= 26:
        break
    x, y = round(rng.uniform(7, W - 7), 1), round(rng.uniform(13, H - 13), 1)
    xi, yi = celula(x), celula(y)
    if grade[yi][xi] == "." and (grade[yi - 1][xi] == "f" or grade[yi + 1][xi] == "f") and pôr(rng.choice(["ponte_entulho", "rock_slabs", "pillar_broken"]), x, y, rng.random() < 0.5):
        feitos += 1

# --------------------------------------------------------------------------------------------------------------------
# Borda pintada (PNG por código) e diretivas
# --------------------------------------------------------------------------------------------------------------------
PASTA_ARTE.mkdir(parents=True, exist_ok=True)
for velho in PASTA_ARTE.glob("borda_*.png"):
    velho.unlink()
borda = ponte_pixel.pintar_bordas(deck)
for k, (bx_, by_, rec) in enumerate(ponte_pixel.recortar_blocos(borda)):
    nome = "borda_%02d.png" % k
    Image.fromarray(rec, "RGBA").save(PASTA_ARTE / nome)
    decalques.append((nome, bx_, by_, False))

linhas = ["".join(l) for l in grade]
linhas.append("@piso ponte")
linhas.append("@caminho %g %s" % (LARG_ESTRADA, " ".join("%g,%g" % p for p in ESTRADA)))
for tom, r, x, y in lajes:
    linhas.append("@lajes %s %g %g,%g" % (tom, r, round(x, 2), round(y, 2)))
for arq, x, y, topo in decalques:
    linhas.append("@decalque %s%s %d %d%s" % (RES_ARTE, arq, x, y, " topo" if topo else ""))
for x, y, r, (cr, cg, cb, ca) in luzes:
    linhas.append("@luz %g,%g %g %g,%g,%g,%g" % (round(x, 2), round(y, 2), r, cr, cg, cb, ca))
for x, y, rec in bolsoes:
    linhas.append("@bolsao %g,%g %s" % (round(x, 2), round(y, 2), rec))
linhas.append("@brilho_estrada %g" % BRILHO_ESTRADA)
for x, y, raio, forca, spec in guardas:
    linhas.append("@guarda %g,%g %g %g %s" % (round(x, 2), round(y, 2), raio, forca, spec))
linhas.append("@props")
for ident, x, y, flip, _ in sorted(props, key=lambda p: (p[2], p[1])):
    linhas.append("%s %g %g%s" % (ident, x, y, " flip" if flip else ""))
SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")

# --------------------------------------------------------------------------------------------------------------------
# Checagens: conexão, larguras mínimas, props dentro do tabuleiro
# --------------------------------------------------------------------------------------------------------------------
def alcancaveis(origem):
    vis = {origem}
    fila = [origem]
    while fila:
        x, y = fila.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in vis and 0 <= n[0] < W and 0 <= n[1] < H and grade[n[1]][n[0]] not in "mf":
                vis.add(n)
                fila.append(n)
    return vis


alc = alcancaveis(P)
problemas = []
for nome, (cx_, cy_) in {"G": G_CEL, "X": X_CEL, "bolsão": (celula(BOLSAO[0]), celula(BOLSAO[1]))}.items():
    if (cx_, cy_) not in alc:
        problemas.append("%s fora do alcance do início" % nome)
for x, y, _, _, spec in guardas:
    if (celula(x), celula(y)) not in alc:
        problemas.append("encontro %s em célula inalcançável" % spec)
for ident, x, y, flip, r in props:
    if grade[celula(y)][celula(x)] in "fm":
        problemas.append("prop %s fora do tabuleiro (%g, %g)" % (ident, x, y))
for nome, x0, y0, x1, y1 in PARTES:
    if nome.startswith("vao") and min(x1 - x0, y1 - y0) < 8 and nome != "vao4":
        problemas.append("%s tem menos de 8 tiles de largura" % nome)
    if nome.startswith("vao") and (y1 - y0) < 8:
        problemas.append("%s tem menos de 8 tiles de largura jogável" % nome)
    if nome.startswith("praca") and (x1 - x0 < 16 or y1 - y0 < 12):
        problemas.append("%s menor que 16 x 12" % nome)
n_pri = sum(int(t.split(":")[1]) for t in ENCONTROS[0][3].split("|"))
if not 2 <= n_pri <= 3:
    problemas.append("o primeiro encontro deve ter 2 ou 3 inimigos")
print("mapa: %d x %d, %d células de tabuleiro, %d props, %d luzes, %d encontros, %d lajes, %d PNG de borda" % (
    W, H, int(deck.sum()), len(props), len(luzes), len(guardas), len(lajes), len(decalques)))
for k, v in capturas.items():
    print("captura %s:%.1f:%.1f%s" % (k, v[0], v[1], v[2]))
if problemas:
    print("PROBLEMAS:")
    for p in problemas:
        print("  -", p)
    sys.exit(1)

if "--visao" in sys.argv:
    destino = Path(sys.argv[sys.argv.index("--visao") + 1])
    E = 8
    im = Image.new("RGB", (W * E, H * E), (16, 21, 36))
    d = ImageDraw.Draw(im)
    for y in range(H):
        for x in range(W):
            c = grade[y][x]
            if c not in "fm":
                d.rectangle([x * E, y * E, x * E + E - 1, y * E + E - 1], fill=(120, 134, 160))
            if c in "BPEXG":
                d.rectangle([x * E + 1, y * E + 1, x * E + E - 2, y * E + E - 2], fill={"B": (255, 140, 40), "P": (60, 200, 90), "E": (200, 60, 60), "X": (90, 160, 255), "G": (255, 60, 200)}[c])
    d.line([((px + 0.5) * E, (py + 0.5) * E) for px, py in estrada.pts], fill=(200, 210, 226), width=int(LARG_ESTRADA * E * 0.5))
    for ident, x, y, _, _ in props:
        cor = {"ponte_sino": (214, 164, 92), "ponte_sino_caido": (214, 164, 92), "ponte_sino_maior": (255, 200, 90), "ponte_casulo": (226, 246, 250),
               "pedreira_poste_lanterna": (255, 220, 90)}.get(ident)
        if cor:
            d.rectangle([(x + 0.5) * E - 2, (y + 0.5) * E - 2, (x + 0.5) * E + 2, (y + 0.5) * E + 2], fill=cor)
    for x, y, raio, forca, spec in guardas:
        d.ellipse([(x + 0.5) * E - 5, (y + 0.5) * E - 5, (x + 0.5) * E + 5, (y + 0.5) * E + 5], outline=(255, 30, 30), width=2)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino)
    print("visão geral:", destino)
