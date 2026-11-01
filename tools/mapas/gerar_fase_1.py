#!/usr/bin/env python3
"""Gera godot/data2d/rooms/fase_1.txt: a fase aberta da Cripta (pacote H1 de docs/design/31_plano_hordas.md).

Mapa de 180 x 100 tiles (cerca de 7 x 7 telas de 1600 x 900) sem forma de retângulo: a área andável é
cercada por mata fechada (`m`) com borda irregular, e bosques internos abrem clareiras e passagens
estreitas. Zonas: cemitério e bosque a oeste, riacho com afluente no meio, ruínas da cripta e ossário
a leste, arena do Guardião no nordeste (G: onde ele espera; X: portal único, aberto depois dele).
As lajes das ruínas e da arena saem como manchas `@lajes` de contorno orgânico, não como tiles.
Mesma saída a cada execução (semente fixa). Uso: python3 tools/mapas/gerar_fase_1.py
"""
import math
import random
from pathlib import Path

W, H = 180, 100
SAIDA = Path(__file__).resolve().parents[2] / "godot/data2d/rooms/fase_1.txt"
rng = random.Random(1101)

P = (14, 86)
E_INICIO = [(27, 80), (31, 88), (24, 73), (35, 83)]   # primeira onda, adormecida, a uns 10 tiles do início
ARENA = (150.0, 24.0, 11.0)   # centro x, y e raio (células)

RIACHOS = [
    (1.8, [(84, -1), (80, 10), (86, 22), (81, 34), (87, 46), (82, 58), (88, 70), (83, 82), (86, 101)]),
    (1.3, [(128, 101), (122, 92), (112, 86), (100, 80), (88, 73)]),   # afluente do sudeste
]
CAMINHOS = [
    (1.7, [(14, 86), (22, 82), (32, 78), (44, 74), (56, 68), (68, 62), (78, 58), (90, 54), (102, 50),
           (114, 46), (126, 40), (136, 33), (143, 28)]),
    (1.5, [(24, 18), (36, 16), (50, 19), (64, 17), (76, 19), (90, 22), (104, 20), (118, 23), (130, 22),
           (139, 23)]),
    (1.4, [(24, 18), (21, 30), (26, 42), (22, 56), (28, 68), (32, 78)]),
    (1.4, [(56, 68), (62, 80), (74, 88), (86, 90), (98, 92), (112, 94)]),
    (1.4, [(114, 46), (120, 58), (132, 66), (146, 70), (160, 72)]),
    (1.3, [(90, 22), (96, 34), (102, 50)]),
]


def _pontos(linha, passo=0.25):
    out = []
    for (x0, y0), (x1, y1) in zip(linha, linha[1:]):
        n = max(1, int(math.dist((x0, y0), (x1, y1)) / passo))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    out.append(linha[-1])
    return out


PTS_RIACHOS = [(l, _pontos(p)) for l, p in RIACHOS]
PTS_CAMINHOS = [(l, _pontos(p)) for l, p in CAMINHOS]


def dist_linha(pts, x, y):
    return min(math.dist(p, (x, y)) for p in pts)


def perto_riacho(x, y, folga):
    return any(dist_linha(p, x, y) < l / 2 + folga for l, p in PTS_RIACHOS)


def perto_caminho(x, y, folga):
    return any(dist_linha(p, x, y) < l / 2 + folga for l, p in PTS_CAMINHOS)


def na_arena(x, y, folga=0.0):
    return math.dist((x, y), ARENA[:2]) < ARENA[2] + folga


def ruido(x, y, s):
    """Ruído suave e determinístico (soma de senos) entre -1 e 1."""
    return (math.sin(x * 0.21 + s) * math.cos(y * 0.17 + s * 1.7) * 0.5
            + math.sin(x * 0.07 + y * 0.05 + s * 2.3) * 0.35
            + math.sin(x * 0.43 - y * 0.37 + s * 0.9) * 0.15)


# Área andável: tudo dentro de uma borda que ondula entre 2 e 18 tiles da beira do mapa.
grade = [["m" for _ in range(W)] for _ in range(H)]
for y in range(H):
    for x in range(W):
        beira = min(x, y, W - 1 - x, H - 1 - y)
        if beira > 8 + 7 * ruido(x, y, 1.3) + 3 * ruido(y, x, 4.1):
            grade[y][x] = "."

# Bosques internos: manchas de mata fechada que fazem clareiras e passagens estreitas.
BOSQUES = [(44, 34, 7), (58, 44, 5), (40, 58, 4.5), (64, 30, 4), (110, 66, 6), (100, 38, 4.5), (122, 80, 4),
           (162, 50, 6), (138, 52, 4), (70, 92, 3.5), (12, 44, 5), (168, 88, 5), (54, 6, 4), (116, 10, 5)]
for cx, cy, r in BOSQUES:
    for y in range(H):
        for x in range(W):
            if math.dist((x, y), (cx, cy)) < r + 2.2 * ruido(x, y, cx * 0.1):
                grade[y][x] = "m"

# Caminhos, riachos, arena e início sempre abertos (com folga para andar ao lado).
for y in range(H):
    for x in range(W):
        if grade[y][x] != "m":
            continue
        if perto_caminho(x, y, 2.0) or perto_riacho(x, y, 1.8) or na_arena(x, y, 4.0) or math.dist((x, y), P) < 6:
            grade[y][x] = "."

# A beira do mapa é sempre mata (nem riacho nem caminho saem por ela).
for y in range(H):
    for x in range(W):
        if min(x, y, W - 1 - x, H - 1 - y) < 3:
            grade[y][x] = "m"

# Muros em ruína nas ruínas, longe de caminho e arena.
MUROS = [((118, 30), (123, 30)), ((118, 30), (118, 34)), ((150, 44), (156, 44)), ((156, 44), (156, 49)),
         ((128, 86), (134, 86)), ((142, 58), (142, 62)), ((104, 72), (108, 72)), ((166, 30), (166, 35))]
for (x0, y0), (x1, y1) in MUROS:
    for k in range(max(abs(x1 - x0), abs(y1 - y0)) + 1):
        x = x0 + (k if x1 > x0 else 0)
        y = y0 + (k if y1 > y0 else 0)
        if grade[y][x] == "." and not perto_caminho(x, y, 1.5) and not na_arena(x, y, 2.0):
            grade[y][x] = "#"

# Arena: braseiros nos cantos, anel de runas no gramado em volta da laje escura.
ax, ay, ar = ARENA
for y in range(H):
    for x in range(W):
        d = math.dist((x, y), (ax, ay))
        if ar + 0.6 <= d < ar + 1.5 and grade[y][x] == "." and not perto_caminho(x, y, 0.6):
            grade[y][x] = "r"
for dx, dy in [(-7, -6), (7, -6), (-7, 6), (7, 6)]:
    grade[int(ay + dy)][int(ax + dx)] = "B"

# Braseiros pelo mapa, na beira dos caminhos.
for x, y in [(36, 75), (60, 64), (100, 48), (122, 41), (106, 22), (66, 16), (128, 64), (150, 68), (90, 88),
             (24, 40), (140, 82)]:
    if grade[y][x] == ".":
        grade[y][x] = "B"

grade[P[1]][P[0]] = "P"
for x, y in E_INICIO:
    grade[y][x] = "E"
grade[int(ay) - 3][int(ax)] = "G"
grade[int(ay) + 4][int(ax)] = "X"

# Lajes das ruínas: manchas de contorno orgânico (o jogo desenha o polígono com textura de pedra).
LAJES = [("escuro", ax, ay, ar), ("claro", ax, ay, ar + 3.2)]
for _ in range(40):
    cx, cy = rng.uniform(100, 172), rng.uniform(8, 92)
    if math.dist((cx, cy), (ax, ay)) < ar + 4 or perto_riacho(cx, cy, 4):
        continue
    if grade[int(cy)][int(cx)] == "m":
        continue
    LAJES.append(("claro", round(cx, 1), round(cy, 1), round(rng.uniform(2.5, 6.0), 1)))


def em_laje(x, y):
    return any(math.dist((x, y), (cx, cy)) < r for _, cx, cy, r in LAJES)


# Props. Cada prop guarda um raio para não encostar em outro.
props = []


def livre_para_prop(x, y, raio, sem_caminho=1.0, na_mata=False):
    cx, cy = int(x), int(y)
    if not (1 <= cx < W - 1 and 1 <= cy < H - 1):
        return False
    if not na_mata:
        for yy in range(cy - 1, cy + 2):
            for xx in range(cx - 1, cx + 2):
                if grade[yy][xx] in "#BPEXGOr":
                    return False
        if perto_riacho(x, y, 0.9) or perto_caminho(x, y, sem_caminho) or na_arena(x, y, 2.5):
            return False
        if math.dist((x, y), P) < 4 or any(math.dist((x, y), e) < 2 for e in E_INICIO):
            return False
    return all(math.dist((x, y), (px, py)) >= raio + pr for _, px, py, pr, _ in props)


def espalhar(ids, n, caixa, raio, tentativas=None, sem_caminho=1.0, filtro=None):
    x0, y0, x1, y1 = caixa
    feitos = 0
    for _ in range(tentativas or n * 30):
        if feitos >= n:
            break
        x, y = round(rng.uniform(x0, x1), 1), round(rng.uniform(y0, y1), 1)
        if not (1 <= x < W - 1 and 1 <= y < H - 1) or grade[int(y)][int(x)] == "m":
            continue
        if filtro is not None and not filtro(x, y):
            continue
        if livre_para_prop(x, y, raio, sem_caminho):
            props.append((rng.choice(ids), x, y, raio, rng.random() < 0.4))
            feitos += 1


TUMULOS = ["grave_slab", "grave_round", "grave_broken", "grave_dirt_cross", "tomb_angel", "tomb_flowers"]
ARVORES = ["tree_dry_large", "tree_dry_leaning", "tree_dry_orange", "tree_dry_pile", "tree_dry_small",
           "tree_dry_thin", "tree_dead_large", "tree_dead_medium", "tree_hollow", "tree_skull", "tree_dead_webs",
           "tree_teal_leaves"]
MATA = ["tree_dry_large", "tree_dead_large", "tree_dry_pile", "tree_dead_medium", "tree_hollow", "tree_dead_webs",
        "tree_dry_orange", "tree_teal_leaves"]
MATO = ["bush_dry_round", "bush_dry_tangled", "bush_dry_wide", "grass_dry_patch", "grass_dry_tall",
        "ferns_withered", "flowers_dead", "thistles_dry", "shrub_dry_tall", "leaves_pile", "bush_thorny",
        "branches_fallen", "leaves_scattered"]
PEDRAS = ["rock_large", "rock_cluster", "rock_mossy", "rock_slabs"]
RUINAS = ["pillar_broken", "pillar_cracked", "pillar_fallen", "pillar_runes", "pillar_tall", "pillar_thick",
          "rock_rubble", "bones_scattered", "skull_pile", "bones_ribcage"]
OSSARIO = ["sarcophagus_closed", "sarcophagus_open", "coffin_lid_leaning", "skull_mound_candles",
           "skull_pile", "bones_chains", "skeleton_curled", "skull_spike", "ribcage_arch"]


def vizinho_mata(x, y):
    return any(0 <= y + dy < H and 0 <= x + dx < W and grade[y + dy][x + dx] == "m"
               for dy in (-1, 0, 1) for dx in (-1, 0, 1))


def dist_aberto(x, y, raio=4):
    """Distância (em células) até a célula andável mais perto, até `raio`."""
    melhor = raio + 1
    for dy in range(-raio, raio + 1):
        for dx in range(-raio, raio + 1):
            xx, yy = x + dx, y + dy
            if 0 <= xx < W and 0 <= yy < H and grade[yy][xx] != "m":
                melhor = min(melhor, math.hypot(dx, dy))
    return melhor


# Orla da mata: árvores grossas na beira e dentro dela, para a borda ler como floresta, não como corte.
celulas_orla = [(x, y) for y in range(H) for x in range(W) if grade[y][x] == "m" and dist_aberto(x, y) <= 3.2]
rng.shuffle(celulas_orla)
for x, y in celulas_orla:
    px, py = round(x + rng.uniform(0.1, 0.9), 1), round(y + rng.uniform(0.1, 0.9), 1)
    if livre_para_prop(px, py, 1.15, na_mata=True):
        props.append((rng.choice(MATA), px, py, 1.15, rng.random() < 0.5))
for x, y in celulas_orla[: len(celulas_orla) // 3]:
    px, py = round(x + rng.uniform(0.1, 0.9), 1), round(y + rng.uniform(0.1, 0.9), 1)
    if livre_para_prop(px, py, 0.6, na_mata=True):
        props.append((rng.choice(MATO[:8]), px, py, 0.6, rng.random() < 0.5))
# Do lado de dentro da beira, moitas e capim (a mata não termina numa linha reta).
beira_dentro = [(x, y) for y in range(H) for x in range(W) if grade[y][x] == "." and vizinho_mata(x, y)]
rng.shuffle(beira_dentro)
for x, y in beira_dentro[: len(beira_dentro) // 3]:
    espalhar(MATO, 1, (x, y, x + 0.9, y + 0.9), 0.6, tentativas=3)

# Zona 1: cemitério e bosque (oeste).
for fy in range(24, 52, 4):
    for fx in range(32, 60, 3):
        if rng.random() < 0.8:
            espalhar(TUMULOS, 1, (fx - 0.3, fy - 0.3, fx + 0.3, fy + 0.3), 0.8, tentativas=4)
for fy in range(60, 70, 3):
    for fx in range(8, 20, 3):
        espalhar(TUMULOS, 1, (fx - 0.3, fy - 0.3, fx + 0.3, fy + 0.3), 0.8, tentativas=4)
espalhar(["mausoleum_door"], 3, (30, 22, 62, 52), 2.0)
espalhar(["grave_fence"], 6, (30, 22, 62, 52), 1.4)
espalhar(ARVORES, 40, (6, 6, 76, 94), 2.0)
espalhar(MATO, 110, (6, 6, 78, 94), 0.8)
espalhar(PEDRAS, 18, (6, 6, 76, 94), 1.4)

# Zona 2: margens dos riachos.
beira = lambda x, y: perto_riacho(x, y, 1.6) and not perto_riacho(x, y, 0.9)
espalhar(["reeds_dry"], 90, (70, 0, 130, 100), 0.6, tentativas=12000, filtro=beira)
espalhar(PEDRAS + ["log_fallen", "roots_clump"], 30, (70, 0, 130, 100), 1.3, tentativas=12000,
         filtro=lambda x, y: perto_riacho(x, y, 2.6) and not perto_riacho(x, y, 0.9))
espalhar(ARVORES, 20, (70, 0, 130, 100), 2.0, filtro=lambda x, y: perto_riacho(x, y, 5.0))

# Zona 3: ruínas (leste) e ossário (sudeste), sobre as lajes e em volta delas.
espalhar(RUINAS, 70, (98, 6, 174, 94), 1.3)
espalhar(OSSARIO, 45, (120, 55, 174, 94), 1.3)
espalhar(["altar_candles", "skull_mound_candles"], 14, (98, 6, 174, 94), 1.6)
espalhar(ARVORES[5:], 22, (98, 6, 174, 94), 2.0, filtro=lambda x, y: not em_laje(x, y))
espalhar(MATO[:6], 50, (98, 6, 174, 94), 0.8, filtro=lambda x, y: not em_laje(x, y))

# Arena: pilares de runas em volta do anel, sem fechar a entrada dos caminhos.
for k in range(10):
    a = k * math.tau / 10 + math.pi / 10
    x, y = ax + math.cos(a) * (ar + 2.6), ay + math.sin(a) * (ar + 2.2)
    if not perto_caminho(x, y, 1.2) and grade[int(y)][int(x)] not in "mB":
        props.append(("pillar_runes" if k % 2 else "pillar_tall", round(x, 1), round(y, 1), 1.0, False))

linhas = ["".join(l) for l in grade]
linhas.append("@piso grama")
for larg, pts in CAMINHOS:
    linhas.append("@caminho %s %s" % (larg, " ".join("%g,%g" % p for p in pts)))
for larg, pts in RIACHOS:
    linhas.append("@riacho %s %s" % (larg, " ".join("%g,%g" % p for p in pts)))
for tom, cx, cy, r in LAJES:
    linhas.append("@lajes %s %g %g,%g" % (tom, r, cx, cy))
linhas.append("@props")
for pid, x, y, _, flip in sorted(props, key=lambda p: (p[2], p[1])):
    linhas.append("%s %g %g%s" % (pid, x, y, " flip" if flip else ""))
SAIDA.write_text("\n".join(linhas) + "\n")
print("%s: %d x %d, %d props, %d lajes" % (SAIDA.name, W, H, len(props), len(LAJES)))
