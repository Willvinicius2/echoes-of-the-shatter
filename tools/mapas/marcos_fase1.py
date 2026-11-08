#!/usr/bin/env python3
"""Camada de marcos da fase 1 (direção do Jev, 06/11/2026, thread "Terminar o mapa da área 1 do arqueiro").

Roda DEPOIS do gerador (`gerar_fase_1.py` chama `aplicar` no fim, em memória) e deixa o mapa com uma espinha clara:
uma estrada de pedra larga do início do arqueiro até o portão da arena, com 2 curvas e 1 bifurcação curta para um
bolsão com recompensa; as outras estradas que cortavam a principal saem (sobra só a trilha do norte, estreita). Em
volta da estrada a mata alta recua (nada denso atrás dela) e entram os marcos, cada um com luz própria:
  1. início: dois pilares com glifo e braseiros;
  2. meio: ponte sobre o riacho e, logo depois, a alameda de pilares quebrados (ruína);
  3. bifurcação: árvore seca grande com velas na base;
  4. antes da arena: clareira de descanso com braseiros (o respiro) e a avenida final até o portão de caveiras e brasas.
Também grava as diretivas que o cliente lê: `@luz` (halos dos marcos), `@bolsao` (baú de recompensa) e `@guarda`
(encontros adormecidos por trecho, que acordam por proximidade; o fluxo do core continua sendo a horda).

Uso: python3 tools/mapas/marcos_fase1.py [arquivo]   (lê e grava no lugar; o arquivo precisa ser a saída pura do
gerador). Mesma saída a cada execução (semente fixa).
"""
import math
import random
import sys
from pathlib import Path

W, H = 180, 100
RAIZ = Path(__file__).resolve().parents[2]
ARQ = RAIZ / "godot/data2d/rooms/fase_1.txt"
rng = random.Random(4242)

# --------------------------------------------------------------------------------------------------------------------
# Geometria (em tiles; x para a direita, y para baixo)
# --------------------------------------------------------------------------------------------------------------------
P = (14, 86)                       # início do arqueiro
ARENA = (150.0, 24.0, 11.0)        # centro e raio da laje escura (como no gerador)
LARG_ESTRADA = 2.0                 # estrada principal (antes 1,7)
LARG_TRILHA = 1.1                  # bifurcação do bolsão e trilha do norte
ESTRADA = [(8.5, 86), (26, 87), (38, 85), (48, 80), (54, 72), (58, 64), (66, 59), (76, 57), (84, 56), (94, 54.5),
           (102, 51.5), (110, 49), (118, 49.5), (126, 47.5), (133, 46), (138.5, 43), (140.5, 38), (140.5, 32),
           (141, 28.5)]
RAIO_GUARDA = 260                  # px: o encontro acorda quando o jogador chega a esta distância (a tela mostra 320 px para cada lado)
S_INICIO_PILARES = 7.8             # os pilares do início ficam a ~2,3 tiles do arqueiro (a estrada começa 5,5 tiles antes dele, na borda da primeira tela)
BIFURCACAO_S = 104.0               # distância (tiles) ao longo da estrada em que a trilha do bolsão sai
BOLSAO = (100.0, 37.0, 3.2)        # centro e raio (tiles) da clareira do bolsão
TRILHA_BOLSAO_FIM = (100.4, 40.6)  # onde a trilha encosta na clareira

# Estradas do gerador que saem (cruzavam a principal e criavam bifurcações demais) e a que fica, só mais estreita.
REMOVER_ESTRADAS = [(24, 18, 21, 30), (56, 68, 62, 80), (114, 46, 120, 58), (90, 22, 96, 34)]   # primeiros 2 pontos de cada
TRILHA_NORTE_FIM = (118, 23)       # a trilha do norte para antes da arena (um só portão)
ARCO_RUINA_DX = 0.8125             # a verga quebrada (arco_ruina, 172 px, pivô no centro) tem o pilar 52 px à esquerda do pivô: deslocamento em tiles
E_ESTRADA = [(15, 2.6), (30, -2.6), (45, 2.6), (60, -2.6), (75, 2.6), (110, 2.6), (118, -2.8), (123, 2.8), (139, -2.6), (144, 2.6)]   # pontos E (s, lateral), longe dos marcos; o primeiro a ~9 tiles do início (alcance da flecha)


def spline(pts, passo=0.25):
    """Catmull-Rom como o `terreno_2d.gd`, em tiles."""
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


class Curva:
    """Amostra uma curva uniformemente: distância percorrida, posição, direção e normal (para a direita de quem anda)."""

    def __init__(self, pts, passo=0.25):
        self.pts = spline(pts, passo)
        self.s = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.s.append(self.s[-1] + math.dist(a, b))
        self.comprimento = self.s[-1]

    def em(self, s, lateral=0.0):
        s = max(0.0, min(self.comprimento, s))
        lo, hi = 0, len(self.s) - 1
        while hi - lo > 1:
            m = (lo + hi) // 2
            if self.s[m] <= s:
                lo = m
            else:
                hi = m
        a, b = self.pts[lo], self.pts[min(lo + 1, len(self.pts) - 1)]
        d = math.dist(a, b) or 1.0
        t = (s - self.s[lo]) / d
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        dx, dy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
        return (round(x - dy * lateral, 2), round(y + dx * lateral, 2))   # lateral > 0: à direita de quem anda

    def distancia(self, x, y, janela=None):
        """Menor distância de (x, y) à curva, em tiles."""
        melhor = 1e9
        for px, py in self.pts:
            d = (px - x) ** 2 + (py - y) ** 2
            if d < melhor:
                melhor = d
        return math.sqrt(melhor)

    def s_mais_perto(self, x, y):
        melhor, bs = 1e18, 0.0
        for (px, py), s in zip(self.pts, self.s):
            d = (px - x) ** 2 + (py - y) ** 2
            if d < melhor:
                melhor, bs = d, s
        return bs


def dist_segmento(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy or 1.0)))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def ruido(x, y, s):
    """Mesmo ruído do gerador (soma de senos), para refazer as bordas das manchas de mata."""
    return (math.sin(x * 0.21 + s) * math.cos(y * 0.17 + s * 1.7) * 0.5
            + math.sin(x * 0.07 + y * 0.05 + s * 2.3) * 0.35
            + math.sin(x * 0.43 - y * 0.37 + s * 0.9) * 0.15)


# --------------------------------------------------------------------------------------------------------------------
# Leitura e escrita do arquivo da sala
# --------------------------------------------------------------------------------------------------------------------
class Sala:
    def __init__(self, linhas):
        i = 0
        self.grade = []
        while not linhas[i].startswith("@"):
            if linhas[i].strip():
                self.grade.append(list(linhas[i]))
            i += 1
        self.diretivas = []
        while linhas[i] != "@props":
            self.diretivas.append(linhas[i])
            i += 1
        self.props = []   # [id, x, y, flip]
        for l in linhas[i + 1:]:
            if l.strip():
                q = l.split()
                self.props.append([q[0], float(q[1]), float(q[2]), len(q) > 3 and q[3] == "flip"])

    def texto(self):
        out = ["".join(l) for l in self.grade] + self.diretivas + ["@props"]
        for pid, x, y, flip in sorted(self.props, key=lambda p: (p[2], p[1])):
            out.append("%s %g %g%s" % (pid, x, y, " flip" if flip else ""))
        return "\n".join(out) + "\n"

    def caminhos(self):
        r = []
        for l in self.diretivas:
            if l.startswith("@caminho "):
                q = l.split()
                r.append((float(q[1]), [tuple(map(float, p.split(","))) for p in q[2:]]))
        return r


# --------------------------------------------------------------------------------------------------------------------
# Famílias de props (por id)
# --------------------------------------------------------------------------------------------------------------------
def eh_arvore(i):
    return i.startswith(("tree_", "sapling_"))


def eh_folhagem(i):
    return i.startswith(("bush_", "shrub_"))


def eh_raso(i):
    return i.startswith(("leaves_", "bones_", "skeleton_", "skull_single", "skull_pair", "skull_teal", "branches_",
                         "flowers_", "grass_", "roots_", "ferns_", "reeds_", "thistles_"))


def eh_solido(i):
    return not (eh_arvore(i) or eh_folhagem(i) or eh_raso(i)) or i == "tree_stump"


MATO = ["bush_dry_round", "bush_dry_tangled", "bush_dry_wide", "grass_dry_patch", "grass_dry_tall", "ferns_withered",
        "flowers_dead", "thistles_dry", "shrub_dry_tall", "leaves_pile", "bush_thorny", "branches_fallen",
        "leaves_scattered"]
BAIXO = ["grass_dry_patch", "flowers_dead", "leaves_scattered", "thistles_dry", "leaves_pile", "grass_dry_tall"]
MATA = ["tree_dry_large", "tree_dead_large", "tree_dry_pile", "tree_dead_medium", "tree_hollow", "tree_dead_webs",
        "tree_dry_orange", "tree_teal_leaves"]


def aplicar(linhas):
    sala = Sala(linhas)
    grade, props = sala.grade, sala.props
    estrada = Curva(ESTRADA)
    notas = {}

    def aberto(x, y):
        return 0 <= int(y) < H and 0 <= int(x) < W and grade[int(y)][int(x)] != "m"

    # ---- 1. Estradas: sai o que cruzava a principal, entra a nova espinha, a trilha do bolsão e a trilha do norte ----
    velhas = sala.caminhos()
    novas_dir = []
    removidas = []
    for l in sala.diretivas:
        if l.startswith("@caminho "):
            q = l.split()
            pts = [tuple(map(float, p.split(","))) for p in q[2:]]
            larg = float(q[1])
            if larg == 1.7:                                   # a estrada principal antiga
                removidas.append(pts)
                continue
            if any(pts[0] == (a, b) and pts[1] == (c, d) for a, b, c, d in REMOVER_ESTRADAS):
                removidas.append(pts)
                continue
            if larg == 1.5:                                   # trilha do norte: mais estreita e termina antes da arena
                fim = [p for p in pts if p[0] <= TRILHA_NORTE_FIM[0]] + [TRILHA_NORTE_FIM]
                pts = fim
                l = "@caminho %g %s" % (LARG_TRILHA, " ".join("%g,%g" % p for p in pts))
        novas_dir.append(l)
    # a nova estrada principal vai primeiro (o jogo usa a primeira @caminho como a trilha dos vídeos e das capturas)
    s_bif = BIFURCACAO_S
    bx, by = estrada.em(s_bif)
    trilha = [(bx, by), (101.6, 46.5), (100.9, 43.6), TRILHA_BOLSAO_FIM]
    cabecas = ["@caminho %g %s" % (LARG_ESTRADA, " ".join("%g,%g" % p for p in ESTRADA)),
               "@caminho %g %s" % (LARG_TRILHA, " ".join("%g,%g" % p for p in trilha))]
    ini = next(i for i, l in enumerate(novas_dir) if l.startswith("@piso"))
    novas_dir[ini + 1:ini + 1] = cabecas
    sala.diretivas = novas_dir
    trilha_c = Curva(trilha)
    notas["comprimento_estrada_tiles"] = round(estrada.comprimento, 1)

    # ---- 2. Grade: mata recua em volta da estrada e da trilha; clareira do bolsão cercada de mata ----
    bosque_cx, bosque_cy, bosque_r = BOLSAO[0], BOLSAO[1], BOLSAO[2]
    for y in range(H):
        for x in range(W):
            if min(x, y, W - 1 - x, H - 1 - y) < 3:
                continue
            c = grade[y][x]
            if c == "m" and (estrada.distancia(x + .5, y + .5) < LARG_ESTRADA / 2 + 2.4
                             or trilha_c.distancia(x + .5, y + .5) < LARG_TRILHA / 2 + 1.6):
                grade[y][x] = "."
    # anel de mata em volta do bolsão (a clareira fica no meio da floresta); a trilha entra por baixo
    novas_mata = []
    for y in range(H):
        for x in range(W):
            d = math.dist((x + .5, y + .5), (bosque_cx, bosque_cy))
            if bosque_r + 0.9 < d < bosque_r + 3.4 + 1.2 * ruido(x, y, 3.3) and grade[y][x] != "#":
                if trilha_c.distancia(x + .5, y + .5) < LARG_TRILHA / 2 + 1.3 or estrada.distancia(x + .5, y + .5) < 4.0:
                    continue
                if grade[y][x] != "m":
                    grade[y][x] = "m"
                    novas_mata.append((x, y))
            elif d <= bosque_r + 0.9 and grade[y][x] == "m":
                grade[y][x] = "."
    # início e arena nunca fecham
    for y in range(H):
        for x in range(W):
            if math.dist((x, y), P) < 6 and grade[y][x] == "m":
                grade[y][x] = "."

    # braseiros do gerador que cairiam em cima da estrada ou da boca da trilha saem (os dos marcos entram depois)
    for y in range(H):
        for x in range(W):
            if grade[y][x] == "B" and (estrada.distancia(x + .5, y + .5) < LARG_ESTRADA / 2 + 1.4
                                       or trilha_c.distancia(x + .5, y + .5) < LARG_TRILHA / 2 + 1.4):
                grade[y][x] = "."

    # ---- 3. Props: limpa a faixa da estrada, do bolsão e das zonas dos marcos ----
    marcos_zonas = []   # (x, y, raio): zonas onde só entra o que o marco põe

    def limpar(x, y, r, so_solidos=False):
        mantidos = []
        for p in props:
            if math.dist((p[1], p[2]), (x, y)) < r and not (so_solidos and eh_raso(p[0])):
                continue
            mantidos.append(p)
        props[:] = mantidos

    antes = len(props)
    mantidos = []
    for p in props:
        d = estrada.distancia(p[1], p[2])
        dt = trilha_c.distancia(p[1], p[2])
        i = p[0]
        if d < LARG_ESTRADA / 2 + 0.45 or dt < LARG_TRILHA / 2 + 0.4:
            continue                                      # em cima da pista: nada
        if eh_arvore(i) and (d < 3.4 or dt < 2.2):
            continue                                      # tronco alto não encosta na estrada
        if eh_solido(i) and (d < LARG_ESTRADA / 2 + 1.2 or dt < LARG_TRILHA / 2 + 1.0):
            continue                                      # obstáculo sólido deixa a pista livre dos dois lados
        if eh_arvore(i) and d < 5.2 and rng.random() < 0.5:
            continue                                      # copas um pouco mais abertas perto da estrada
        if math.dist((p[1], p[2]), (BOLSAO[0], BOLSAO[1])) < BOLSAO[2] + 0.6:
            continue
        mantidos.append(p)
    props[:] = mantidos
    notas["props_removidos_da_faixa"] = antes - len(props)

    # faixas das estradas que saíram: o gerador deixava essas faixas vazias; devolve mato baixo em volta
    def ocupado(x, y, r):
        return any(math.dist((p[1], p[2]), (x, y)) < r + (0.9 if eh_arvore(p[0]) else 0.5) for p in props)

    def sobre_pista(x, y):
        return estrada.distancia(x, y) < LARG_ESTRADA / 2 + 0.6 or trilha_c.distancia(x, y) < LARG_TRILHA / 2 + 0.5

    def mancha_agua(x, y):
        for l in sala.diretivas:
            if l.startswith("@riacho "):
                q = l.split()
                larg = float(q[1])
                pts = [tuple(map(float, p.split(","))) for p in q[2:]]
                if min(dist_segmento((x, y), a, b) for a, b in zip(pts, pts[1:])) < larg / 2 + 1.2:
                    return True
        return False

    em_laje = []
    for l in sala.diretivas:
        if l.startswith("@lajes "):
            q = l.split()
            xy = q[3].split(",")
            em_laje.append((float(xy[0]), float(xy[1]), float(q[2])))

    def na_laje(x, y):
        return any(math.dist((x, y), (cx, cy)) < r for cx, cy, r in em_laje)

    preenchidos = 0
    for pts in removidas:
        curva = Curva(pts, 0.5)
        s = 0.0
        while s < curva.comprimento:
            cx, cy = curva.em(s)
            s += 0.9
            for _ in range(2):
                x = cx + rng.uniform(-2.0, 2.0)
                y = cy + rng.uniform(-2.0, 2.0)
                if not (3 < x < W - 3 and 3 < y < H - 3) or not aberto(x, y) or sobre_pista(x, y) or mancha_agua(x, y):
                    continue
                if na_laje(x, y) or ocupado(x, y, 0.55):
                    continue
                if rng.random() < 0.18:
                    ident = rng.choice(MATO[:8] + ["rock_rubble"]) if rng.random() < 0.5 else rng.choice(BAIXO)
                else:
                    ident = rng.choice(BAIXO + MATO[:6])
                props.append([ident, round(x, 1), round(y, 1), rng.random() < 0.45])
                preenchidos += 1
    # moitas e uma árvore a cada tanto nas faixas, para não ficar um corredor só de capim
    notas["props_nas_faixas_antigas"] = preenchidos

    # orla de árvores nas células novas de mata (anel do bolsão)
    def vizinho_aberto(x, y, r=3.2):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                xx, yy = x + dx, y + dy
                if 0 <= xx < W and 0 <= yy < H and grade[yy][xx] != "m" and math.hypot(dx, dy) <= r:
                    return True
        return False

    rng.shuffle(novas_mata)
    for x, y in novas_mata:
        if not vizinho_aberto(x, y):
            continue
        px, py = round(x + rng.uniform(0.1, 0.9), 1), round(y + rng.uniform(0.1, 0.9), 1)
        if not ocupado(px, py, 1.15):
            props.append([rng.choice(MATA), px, py, rng.random() < 0.5])
    # ---- 4. Marcos ----
    # A câmera mostra só ~10 x 5,6 tiles e o personagem fica no centro: o que está ao norte da estrada (acima) só
    # aparece se a base estiver a menos de 2,8 tiles, e o que é alto some pela borda de cima. Por isso as peças altas
    # ficam à DIREITA de quem anda (lateral > 0: ao sul nos trechos leste-oeste, a leste nos trechos norte-sul), onde a
    # copa e o topo entram na tela de longe, e o lado esquerdo leva só peças baixas, velas e braseiros.
    luzes = []     # (x, y, raio_tiles, (r, g, b, a))
    guardas = []   # (x, y, raio_despertar_px, forca, spec)
    bolsoes = []   # (x, y, id_recompensa)
    capturas = {}  # nome -> (x, y) em tiles: onde o jogador fica para a captura de cada marco

    def pb(ident, x, y, flip=False):
        props.append([ident, round(x, 2), round(y, 2), flip])

    def braseiro(x, y):
        xi, yi = int(x), int(y)
        if grade[yi][xi] in ".p":
            grade[yi][xi] = "B"
            return xi, yi   # o centro do braseiro no mapa é o índice da célula (o jogo soma 0,5)
        raise SystemExit("braseiro em célula %r (%g, %g)" % (grade[yi][xi], x, y))

    def sem_pilares_antigos(x, y, r):
        props[:] = [p for p in props if not (p[0].startswith("pillar") and math.dist((p[1], p[2]), (x, y)) < r)]

    # 4.1 Início: dois pilares com glifo e dois braseiros logo à frente do arqueiro
    s0 = S_INICIO_PILARES
    for lado, flip in [(-2.4, True), (2.4, False)]:
        x, y = estrada.em(s0, lado)
        limpar(x, y, 1.8)
        pb("pillar_runes", x, y, flip)
    for lado in (-2.2, 2.2):
        x, y = estrada.em(s0 + 2.0, lado)
        limpar(x, y, 1.4)
        bxi, byi = braseiro(x, y)
        luzes.append((bxi, byi, 4.6, (1.0, 0.6, 0.24, 0.36)))
    marcos_zonas.append((estrada.em(s0)[0], estrada.em(s0)[1], 6.0))
    notas["inicio"] = estrada.em(s0)
    capturas["1_inicio"] = P

    # 4.2 Meio: ruína logo depois da ponte (a ponte do riacho é desenhada pelo jogo): fileira de pilares à direita da
    # estrada, o primeiro alto com a verga quebrada (arco_ruina) avançando para a frente, mais uma fileira de fundo,
    # um pilar caído, entulho e cotocos baixos à esquerda.
    s_ponte = estrada.s_mais_perto(84, 56)
    notas["ponte_s"] = round(s_ponte, 1)
    r0 = s_ponte + 5.6
    fileira = [(0.0, "pillar_tall"), (4.2, "pillar_cracked"), (8.0, "pillar_broken")]
    for ds, ident in fileira:
        x, y = estrada.em(r0 + ds, 2.9)
        limpar(x, y, 1.7)
        pb(ident, x, y, ident != "pillar_tall" and rng.random() < 0.5)
        if ident == "pillar_tall":
            notas["arco_ruina_pilar"] = (round(x, 2), round(y, 2))
            pb("arco_ruina", x + ARCO_RUINA_DX, y)
    for ds, ident in [(2.0, "pillar_broken"), (6.4, "pillar_cracked")]:
        x, y = estrada.em(r0 + ds, 5.7 + rng.uniform(-0.2, 0.2))
        limpar(x, y, 1.7)
        pb(ident, x, y, rng.random() < 0.5)
    x, y = estrada.em(r0 + 3.2, -2.5)
    limpar(x, y, 1.4)
    pb("pillar_broken", x, y)
    x, y = estrada.em(r0 + 7.0, -2.4)
    limpar(x, y, 1.6)
    pb("pillar_fallen", x, y)
    x, y = estrada.em(r0 + 5.8, 1.9)
    pb("rock_rubble", x, y)
    pb("vines_dry_rock", *estrada.em(r0 + 9.8, 3.4))
    for lado, ds in [(-1.9, 1.2), (1.9, 9.8)]:
        x, y = estrada.em(r0 + ds, lado)
        pb("skull_mound_candles", x, y)
        luzes.append((x, y, 3.2, (1.0, 0.72, 0.3, 0.32)))
    gx2, gy2 = estrada.em(r0 + 6.0, 2.9)   # sentinela e esqueletos dormem entre os pilares; morcegos na frente da ruína
    guardas.append((gx2, gy2 - 1.3, RAIO_GUARDA, 1.0, "hollow_sentinel:1|skeleton_soldier:2"))
    gx2, gy2 = estrada.em(r0 + 10.0, 2.4)
    guardas.append((gx2, gy2, RAIO_GUARDA, 1.0, "crypt_bat:2"))
    marcos_zonas.append((*estrada.em(r0 + 5.0), 8.0))
    capturas["2_ruina"] = estrada.em(r0 + 1.0)
    capturas["2a_ruina_perto"] = estrada.em(r0 + 1.6, 1.8)   # na beira sul da estrada: a base dos pilares e a verga entram na tela

    # 4.3 Bifurcação: árvore seca grande do outro lado da estrada (à direita, de onde ela aparece de longe) com velas
    # na base, e dois montes de velas em cada lado da boca da trilha do bolsão
    fx, fy = estrada.em(s_bif)
    ax, ay = estrada.em(s_bif + 1.4, 3.6)
    limpar(ax, ay, 3.0)
    pb("tree_skull", ax, ay)
    for dx, dy in [(-1.7, 1.2), (1.6, 1.4)]:
        limpar(ax + dx, ay + dy, 0.8)
        pb("skull_mound_candles", ax + dx, ay + dy)
    luzes.append((ax, ay + 1.0, 4.0, (1.0, 0.7, 0.3, 0.4)))
    for dx in (-1.5, 1.5):
        limpar(fx + dx, fy - 1.8, 0.9)
        pb("skull_mound_candles", fx + dx, fy - 1.8)
    notas["bifurcacao"] = (round(fx, 2), round(fy, 2))
    capturas["3_bifurcacao"] = estrada.em(s_bif - 1.0, 1.2)   # um pouco ao sul da estrada: a base da árvore seca entra na tela

    # 4.4 Bolsão: altar com velas e o baú; guardas adormecidos em volta
    bcx, bcy, br = BOLSAO
    limpar(bcx, bcy, br + 0.4)
    pb("altar_candles", bcx, bcy - 1.4)
    for dx, dy in [(-2.3, -0.5), (2.3, -0.5), (-1.7, 1.6), (1.8, 1.7)]:
        pb("skull_mound_candles", bcx + dx, bcy + dy)
    for dx, dy, ident in [(-2.6, 0.9, "skull_pile"), (2.5, 0.7, "bones_scattered")]:
        pb(ident, bcx + dx, bcy + dy)
    luzes.append((bcx, bcy - 0.4, 4.6, (1.0, 0.72, 0.3, 0.46)))
    bolsoes.append((bcx, bcy + 0.4, "bau"))
    guardas.append((bcx - 0.8, bcy - 0.2, RAIO_GUARDA, 1.15, "skeleton_soldier:2|hollow_sentinel:1"))
    capturas["4_bolsao"] = (bcx, bcy + 2.0)

    # 4.5 Respiro: clareira de laje clara com braseiros antes da avenida final
    s_fim = estrada.comprimento
    s_resp = s_fim - 27.0
    rx, ry = estrada.em(s_resp)
    sala.diretivas.append("@lajes claro 4.6 %g,%g" % (rx, ry))
    limpar(rx, ry, 5.2)
    for lado, ds in [(-2.7, -1.0), (2.7, 1.0)]:
        x, y = estrada.em(s_resp + ds, lado)
        limpar(x, y, 1.5)
        bxi, byi = braseiro(x, y)
        luzes.append((bxi, byi, 4.8, (1.0, 0.6, 0.24, 0.4)))
    pb("log_fallen", *estrada.em(s_resp - 2.4, 2.6))
    pb("log_fallen", *estrada.em(s_resp + 2.8, -2.4), True)
    pb("skull_mound_candles", *estrada.em(s_resp + 0.2, 4.4))
    marcos_zonas.append((rx, ry, 6.5))
    notas["respiro"] = (round(rx, 2), round(ry, 2))
    capturas["5_respiro"] = estrada.em(s_resp - 2.0)

    # 4.6 Avenida final e portão: dois pilares altos a 256 px um do outro (centros), verga de pedra por cima
    # (arco_portal), caveiras e brasas. Na avenida, pilares quebrados e túmulos nos dois lados.
    s_port = s_fim - 6.5
    gx, gy = estrada.em(s_port)
    gy = round(gy, 2)
    notas["portao"] = (round(gx, 2), gy)
    sem_pilares_antigos(gx, gy, 7.0)
    for dx in (-2.0, 2.0):
        limpar(gx + dx, gy, 1.9)
        pb("pillar_tall", gx + dx, gy)
    pb("arco_portal", gx, gy)
    for dx in (-3.5, 3.5):
        limpar(gx + dx, gy + 1.6, 1.4)
        bxi, byi = braseiro(gx + dx, gy + 1.6)
        luzes.append((bxi, byi, 5.2, (1.0, 0.55, 0.2, 0.46)))
    for dx, dy in [(-2.9, 0.9), (2.9, 0.9), (-4.5, -0.1), (4.5, -0.2)]:
        pb("skull_pile", gx + dx, gy + dy)
    for dx, dy in [(-2.6, 1.8), (2.6, 1.9), (-3.4, 3.0), (3.4, 3.0)]:
        pb("skull_spike", gx + dx, gy + dy)
    luzes.append((gx, gy + 0.2, 7.0, (1.0, 0.6, 0.25, 0.3)))   # a luz do portão avisa de longe, acima da borda da tela
    s = s_port - 5.0
    k = 0
    while s > s_resp + 5.5:
        for lado in (-3.6, 3.6):
            x, y = estrada.em(s, lado + rng.uniform(-0.3, 0.3))
            if not aberto(x, y):
                continue
            limpar(x, y, 1.3)
            pb(["pillar_cracked", "pillar_broken", "tomb_flowers", "sarcophagus_closed", "grave_broken"][(k + (lado > 0)) % 5],
               x, y, rng.random() < 0.5)
        s -= 3.7
        k += 1
    marcos_zonas.append((gx, gy, 9.0))
    capturas["6_portao"] = (gx, gy - 0.5)   # sob a verga: a tela inteira do portão (a viga só entra na tela aqui)
    capturas["6a_portao_aproximacao"] = (gx, gy + 2.6)
    capturas["7_arena"] = (gx + 0.4, gy - 4.5)

    # 4.7 Velas ao pé da estrada no primeiro terço (uma a cada ~16 tiles), do lado direito de quem anda
    for s_v in (20.0, 36.0, 52.0, 68.0):
        x, y = estrada.em(s_v, 2.6)
        if not aberto(x, y) or mancha_agua(x, y):
            continue
        limpar(x, y, 1.0)
        pb("skull_mound_candles", x, y)
        pb("bones_scattered", x + 0.9, y + 0.5, rng.random() < 0.5)

    # 4.8 Encontros na própria estrada, à vista (a tela mostra 5 tiles para cada lado e o raio de acordar é menor que
    # isso), um a cada ~24 tiles (6 s de caminhada) até o respiro, para a estrada nunca ficar vazia por mais de ~6 s:
    # trecho 1 (calmo, esqueletos e morcegos), a ruína e a bifurcação (acima) e o trecho 3 (denso, antes do respiro).
    # O respiro e a avenida final ficam sem encontros: é o descanso antes do chefe.
    guardas.append((*estrada.em(28.0, 0.8), RAIO_GUARDA, 0.85, "skeleton_soldier:2"))
    guardas.append((*estrada.em(52.0, 0.8), RAIO_GUARDA, 0.9, "crypt_bat:3"))
    guardas.append((*estrada.em(76.0, -0.8), RAIO_GUARDA, 0.95, "skeleton_soldier:2|hollow_sentinel:1"))
    guardas.append((*estrada.em(s_resp - 15.0, -0.8), RAIO_GUARDA, 1.2, "skeleton_soldier:2|ghost_archer:1"))
    guardas.append((*estrada.em(s_resp - 7.0, 0.8), RAIO_GUARDA, 1.3, "skeleton_soldier:2|hollow_sentinel:1"))
    capturas["3a_trecho3"] = estrada.em(s_resp - 11.0)   # entre os dois encontros do trecho 3

    # 4.9 Pontos de inimigo `E` (só o fluxo por etapas usa; o modo horda nasce pelo spawner do core): ao longo da
    # estrada, do início ao portão, em células livres
    for y in range(H):
        for x in range(W):
            if grade[y][x] == "E":
                grade[y][x] = "."
    for s_e, lado in E_ESTRADA:
        x, y = estrada.em(s_e, lado)
        xi, yi = int(x), int(y)
        if grade[yi][xi] == "." and not mancha_agua(x, y):
            grade[yi][xi] = "E"
    notas["capturas"] = {k: (round(v[0], 1), round(v[1], 1)) for k, v in capturas.items()}

    # ---- 5. Diretivas novas ----
    for x, y, r, (cr, cg, cb, ca) in luzes:
        sala.diretivas.append("@luz %g,%g %g %g,%g,%g,%g" % (round(x, 2), round(y, 2), r, cr, cg, cb, ca))
    for x, y, rec in bolsoes:
        sala.diretivas.append("@bolsao %g,%g %s" % (round(x, 2), round(y, 2), rec))
    for x, y, raio, forca, spec in guardas:
        sala.diretivas.append("@guarda %g,%g %g %g %s" % (round(x, 2), round(y, 2), raio, forca, spec))
    notas["marcos_zonas"] = marcos_zonas
    return sala.texto(), notas


def main():
    arq = Path(sys.argv[1]) if len(sys.argv) > 1 else ARQ
    linhas = arq.read_text(encoding="utf-8").split("\n")
    if any(l.startswith("@bolsao ") for l in linhas):
        raise SystemExit("%s já tem os marcos aplicados: para refazer, rode python3 tools/mapas/gerar_fase_1.py" % arq)
    texto, notas = aplicar(linhas)
    arq.write_text(texto, encoding="utf-8")
    for k, v in notas.items():
        print("%s: %s" % (k, v))


if __name__ == "__main__":
    main()
