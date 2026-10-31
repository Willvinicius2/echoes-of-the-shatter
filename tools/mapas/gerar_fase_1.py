#!/usr/bin/env python3
"""Gera godot/data2d/rooms/fase_1.txt: a fase aberta da Cripta (pacote H1 de docs/design/31_plano_hordas.md).

Mapa único de 120 x 65 tiles (cerca de 5 x 5 telas de 1600 x 900), sem portas: gramado do cemitério a oeste,
riacho no meio com duas travessias, ruínas da cripta a leste e a arena do Guardião no nordeste
(G: onde o Guardião espera; X: portal único, aberto depois dele).
Mesma saída a cada execução (semente fixa). Uso: python3 tools/mapas/gerar_fase_1.py
"""
import math
import random
from pathlib import Path

W, H = 120, 65                 # 5 x a sala antiga (24 x 13) em cada lado, 25 x a área
DW, DH = 90, 51                # espaço de desenho: as coordenadas abaixo são escritas nele e escaladas para W x H
SX, SY = W / DW, H / DH
AREA = SX * SY


def S(p):
    return (round(p[0] * SX, 2), round(p[1] * SY, 2))


def SL(pts):
    return [S(p) for p in pts]
SAIDA = Path(__file__).resolve().parents[2] / "godot/data2d/rooms/fase_1.txt"
rng = random.Random(1031)

grade = [["." for _ in range(W)] for _ in range(H)]

# Borda: muro duplo no topo (face do muro visível), simples nos outros lados.
for x in range(W):
    grade[0][x] = grade[1][x] = grade[H - 1][x] = "#"
for y in range(H):
    grade[y][0] = grade[y][W - 1] = "#"

# Linhas em células (o jogo suaviza com Catmull-Rom).
RIACHO = (1.6, [(41, 1.5), (38.5, 9), (42.5, 17), (39, 25), (43.5, 33), (40.5, 41), (42, 49.5)])
CAMINHOS = [
    (1.6, [(9, 44), (14, 41.5), (21, 38.5), (28, 35), (35, 32.5), (41.5, 30), (48, 27.5), (55, 25),
           (62, 22), (67, 18.5), (71, 14.5)]),
    (1.4, [(12, 6), (16, 9.5), (22, 11.5), (30, 11), (37, 10.5), (44, 11), (50, 13.5), (56, 16.5),
           (61, 21)]),
    (1.3, [(16, 9.5), (17.5, 18), (19, 27), (21, 38.5)]),
    (1.3, [(55, 25), (60, 31), (66, 36.5), (74, 39), (82, 40)]),
]
ARENA = (72.0, 11.5, 8.5)   # centro x, y e raio (células)
P = (9, 44)
E_INICIO = [(19, 37), (22, 44), (16, 33), (24, 41)]   # primeira onda, adormecida, longe do início
RIACHO = (RIACHO[0], SL(RIACHO[1]))
CAMINHOS = [(l, SL(pts)) for l, pts in CAMINHOS]
ARENA = S(ARENA[:2]) + (ARENA[2] + 1.5,)
P = tuple(int(v) for v in S(P))
E_INICIO = [tuple(int(v) for v in S(e)) for e in E_INICIO]


def _pontos(linha, passo=0.25):
    out = []
    for (x0, y0), (x1, y1) in zip(linha, linha[1:]):
        n = max(1, int(math.dist((x0, y0), (x1, y1)) / passo))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    out.append(linha[-1])
    return out


PTS_RIACHO = _pontos(RIACHO[1])
PTS_CAMINHOS = [_pontos(c[1]) for c in CAMINHOS]


def dist_linha(pts, x, y):
    return min(math.dist(p, (x, y)) for p in pts)


def perto_riacho(x, y, folga):
    return dist_linha(PTS_RIACHO, x, y) < RIACHO[0] / 2 + folga


def perto_caminho(x, y, folga):
    return any(dist_linha(pts, x, y) < c[0] / 2 + folga for pts, c in zip(PTS_CAMINHOS, CAMINHOS))


def na_arena(x, y, folga=0.0):
    return math.dist((x, y), ARENA[:2]) < ARENA[2] + folga


# Ruínas da cripta: manchas de laje de pedra (s) a leste, irregulares.
manchas = [(ARENA[0], ARENA[1], ARENA[2] + 1.5)]
for _ in range(round(16 * AREA)):
    manchas.append(S((rng.uniform(55, 86), rng.uniform(4, 47))) + (rng.uniform(2.5, 5.5) * SX,))
for y in range(2, H - 1):
    for x in range(1, W - 1):
        for cx, cy, r in manchas:
            ruido = 0.6 * math.sin(x * 1.7 + cy) * math.cos(y * 1.3 + cx)
            if math.dist((x, y), (cx, cy)) < r + ruido:
                grade[y][x] = "s"
                break

# Suaviza a borda das lajes: tira pedra solta no gramado e fecha buracos dentro das ruínas.
for _ in range(2):
    nova = [l[:] for l in grade]
    for y in range(2, H - 1):
        for x in range(1, W - 1):
            viz = sum(grade[y + dy][x + dx] == "s" for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)
            if grade[y][x] == "s" and viz < 3:
                nova[y][x] = "."
            elif grade[y][x] == "." and viz >= 6:
                nova[y][x] = "s"
    grade = nova

# Arena do Guardião: piso escuro, anel de runas e braseiros nos quatro cantos.
ax, ay, ar = ARENA
for y in range(2, H - 1):
    for x in range(1, W - 1):
        d = math.dist((x, y), (ax, ay))
        if d < ar - 0.5:
            grade[y][x] = "q" if d < ar - 2.2 else "s"
        if ar - 2.2 <= d < ar - 1.3:
            grade[y][x] = "r"
for dx, dy in [(-6, -5), (6, -5), (-6, 5), (6, 5)]:
    grade[int(ay + dy)][int(ax + dx)] = "B"

# Muros em ruína: trechos curtos de muro nas ruínas, longe de caminho e arena.
MUROS = [((58, 6), (62, 6)), ((58, 6), (58, 9)), ((80, 24), (85, 24)), ((85, 24), (85, 28)),
         ((63, 42), (68, 42)), ((76, 31), (76, 34)), ((50, 40), (53, 40))]
for (x0, y0), (x1, y1) in MUROS:
    (x0, y0), (x1, y1) = [tuple(int(v) for v in S(q)) for q in ((x0, y0), (x1, y1))]
    for k in range(max(abs(x1 - x0), abs(y1 - y0)) + 1):
        x = x0 + (k if x1 > x0 else 0)
        y = y0 + (k if y1 > y0 else 0)
        if not perto_caminho(x, y, 1.5) and not na_arena(x, y, 1.5):
            grade[y][x] = "#"

# Braseiros das ruínas (fora da arena), na beira do caminho.
for x, y in [tuple(int(v) for v in S(q)) for q in [(57, 20), (64, 25), (69, 35), (79, 37), (52, 30), (30, 20), (15, 30), (60, 45)]]:
    if grade[y][x] in ".s":
        grade[y][x] = "B"

grade[P[1]][P[0]] = "P"
for x, y in E_INICIO:
    grade[y][x] = "E"
grade[int(ay) - 2][int(ax)] = "G"   # o Guardião espera aqui (o jogador vai até ele)
grade[int(ay) + 3][int(ax)] = "X"   # portal do fim da fase, aberto depois do Guardião


# Props por zona. Cada prop guarda um raio para não encostar em outro.
props = []


def livre_para_prop(x, y, raio, sem_caminho=1.0):
    cx, cy = int(x), int(y)
    if not (2 <= cx < W - 2 and 3 <= cy < H - 2):
        return False
    for yy in range(cy - 1, cy + 2):
        for xx in range(cx - 1, cx + 2):
            if grade[yy][xx] in "#BPEXGO":
                return False
    if perto_riacho(x, y, 0.9) or perto_caminho(x, y, sem_caminho) or na_arena(x, y, 1.0):
        return False
    if math.dist((x, y), P) < 4 or any(math.dist((x, y), e) < 2 for e in E_INICIO):
        return False
    return all(math.dist((x, y), (px, py)) >= raio + pr for _, px, py, pr, _ in props)


def espalhar(ids, n, caixa, raio, tentativas=400, sem_caminho=1.0, filtro=None, moldura=False):
    x0, y0, x1, y1 = caixa
    if not moldura:
        x0, y0 = S((x0, y0))
        x1, y1 = S((x1, y1))
        if n > 1:
            n = round(n * AREA)
    feitos = 0
    for _ in range(tentativas):
        if feitos >= n:
            break
        x, y = round(rng.uniform(x0, x1), 1), round(rng.uniform(y0, y1), 1)
        if filtro is not None and not filtro(x, y):
            continue
        if livre_para_prop(x, y, raio, sem_caminho):
            props.append((rng.choice(ids), x, y, raio, rng.random() < 0.4))
            feitos += 1


TUMULOS = ["grave_slab", "grave_round", "grave_broken", "grave_dirt_cross", "tomb_angel", "tomb_flowers"]
ARVORES = ["tree_dry_large", "tree_dry_leaning", "tree_dry_orange", "tree_dry_pile", "tree_dry_small",
           "tree_dry_thin", "tree_dead_large", "tree_dead_medium", "tree_hollow", "tree_skull"]
MATO = ["bush_dry_round", "bush_dry_tangled", "bush_dry_wide", "grass_dry_patch", "grass_dry_tall",
        "ferns_withered", "flowers_dead", "thistles_dry", "shrub_dry_tall", "leaves_pile"]
PEDRAS = ["rock_large", "rock_cluster", "rock_mossy", "rock_slabs"]
RUINAS = ["pillar_broken", "pillar_cracked", "pillar_fallen", "pillar_runes", "pillar_tall", "pillar_thick",
          "rock_rubble", "bones_scattered", "skull_pile", "bones_ribcage"]
OSSARIO = ["sarcophagus_closed", "sarcophagus_open", "coffin_lid_leaning", "skull_mound_candles",
           "skull_pile", "bones_chains", "skeleton_curled", "skull_spike", "ribcage_arch"]

# Moldura de árvores e pedras junto ao muro (o mapa não acaba num corte seco).
for x in range(3, W - 3, 3):
    for y in (2.6, H - 2.4):
        espalhar(ARVORES + PEDRAS, 1, (x - 1, y - 0.4, x + 1, y + 0.4), 1.2, tentativas=6, moldura=True)
for y in range(5, H - 4, 3):
    for x in (1.6, W - 2.4):
        espalhar(ARVORES + PEDRAS, 1, (x - 0.4, y - 1, x + 0.4, y + 1), 1.2, tentativas=6, moldura=True)

# Zona 1: cemitério no gramado (oeste). Fileiras de túmulos e um mausoléu.
for fy in (14, 18, 22):
    for fx in range(4, 15, 2):
        espalhar(TUMULOS, 1, (fx - 0.3, fy - 0.3, fx + 0.3, fy + 0.3), 0.8, tentativas=4)
for fy in (27, 30):
    for fx in range(24, 33, 2):
        espalhar(TUMULOS, 1, (fx - 0.3, fy - 0.3, fx + 0.3, fy + 0.3), 0.8, tentativas=4)
espalhar(["mausoleum_door"], 1, (5, 9, 9, 11), 2.0)
espalhar(["grave_fence"], 3, (3, 12, 16, 24), 1.4)
espalhar(ARVORES, 12, (3, 4, 34, 47), 2.0)
espalhar(MATO, 30, (3, 4, 36, 47), 0.8)
espalhar(PEDRAS, 6, (3, 4, 34, 47), 1.4)

# Zona 2: margens do riacho. Juncos, pedras e troncos caídos.
beira = lambda x, y: perto_riacho(x, y, 1.6) and not perto_riacho(x, y, 0.9)
espalhar(["reeds_dry"], 26, (33, 3, 50, 48), 0.6, tentativas=2000, filtro=beira)
espalhar(PEDRAS + ["log_fallen", "roots_clump"], 10, (33, 3, 50, 48), 1.3, tentativas=2000,
         filtro=lambda x, y: perto_riacho(x, y, 2.6) and not perto_riacho(x, y, 0.9))
espalhar(ARVORES, 6, (33, 3, 50, 48), 2.0, filtro=lambda x, y: perto_riacho(x, y, 4.5))

# Zona 3: ruínas da cripta (leste) e ossário (sudeste).
espalhar(RUINAS, 26, (51, 3, 87, 47), 1.3)
espalhar(OSSARIO, 18, (56, 28, 87, 47), 1.3)
espalhar(["altar_candles", "skull_mound_candles"], 6, (52, 3, 87, 47), 1.6)
espalhar(ARVORES[5:], 8, (51, 3, 87, 47), 2.0)
espalhar(MATO[:6], 14, (51, 3, 87, 47), 0.8)

# Arena: pilares de runas em volta do anel (fora dele), sem fechar a entrada do caminho.
for k in range(8):
    a = k * math.tau / 8 + math.pi / 8
    x, y = ax + math.cos(a) * (ar + 1.4), ay + math.sin(a) * (ar + 1.0)
    if 2 < x < W - 2 and 3 < y < H - 2 and not perto_caminho(x, y, 1.2):
        props.append(("pillar_runes" if k % 2 else "pillar_tall", round(x, 1), round(y, 1), 1.0, False))

linhas = ["".join(l) for l in grade]
linhas.append("@piso grama")
for larg, pts in CAMINHOS:
    linhas.append("@caminho %s %s" % (larg, " ".join("%g,%g" % p for p in pts)))
linhas.append("@riacho %s %s" % (RIACHO[0], " ".join("%g,%g" % p for p in RIACHO[1])))
linhas.append("@props")
for pid, x, y, _, flip in sorted(props, key=lambda p: (p[2], p[1])):
    linhas.append("%s %g %g%s" % (pid, x, y, " flip" if flip else ""))
SAIDA.write_text("\n".join(linhas) + "\n")
print("%s: %d x %d, %d props" % (SAIDA.name, W, H, len(props)))
