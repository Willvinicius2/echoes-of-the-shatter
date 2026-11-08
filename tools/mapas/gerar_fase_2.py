#!/usr/bin/env python3
"""Gera godot/data2d/rooms/fase_2.txt: a Pedreira dos Ecos (área 2 do Ato I), e os PNG dos fossos e das pontes.

Direção do Jev e das revisões de arte (thread "Terminar o mapa da área 1 do arqueiro", 08/11/2026; texto completo em
docs/arte/35_pedreira_dos_ecos.md):
  - um elite no portão (não um chefe), fossos como perigo e uma ponte de tábuas como marco, uma rampa estreita com
    espaço para recuar e o primeiro encontro de 2 a 3 inimigos, matilhas maiores só nos trechos 2 e 3, nenhum trecho da
    estrada sem encontro nem marco por mais de ~6 s (24 tiles), um descanso com braseiro antes do portão e a paleta-base da
    área 1 (seca e poeirenta; o ciano só como acento);
  - nada de inimigo sem arte: só os que já têm folha de sprite (skeleton_soldier, hollow_sentinel, crypt_bat, wandering_ghost,
    ghost_archer e chain_wraith, mais o ossuary_captain como elite do portão); ash_hound e stone_herald ficam pendentes (PixelLab);
  - a ponte é uma reta de ~15 tiles e a estrada faz uma curva logo depois; a bifurcação do bolsão leva ao baú, com dois
    lampiões e luz na boca da trilha; o fundo dos fossos leva montes de entulho agrupados e lascas de bloco cortado (não
    pedrinhas redondas) espalham o chão;
  - o portão do fim NÃO repete o arco da área 1: `pedreira_portao` é um portal de pedra maciça (dois bastiões de blocos com guindaste
    e corrente, verga com caveira só como detalhe e grade de ferro levantada), a rocha fecha a clareira dos dois lados dele e o
    elite espera na frente, dentro de um poço de luz laranja (G); o portal (X) fica atrás, só se chega a ele pelo vão do portão;
  - o pórtico (guindaste) nunca esconde o arqueiro: fica na beira, fora da estrada (a Ancoragem ainda o apaga quando o
    arqueiro passa atrás dele); a estrada de pedra tem borda irregular de terra, como a da área 1, e não retângulos `s`; a rocha (`m`)
    tem a orla de terra do shader `orla_terra_2d.gd`, e o chão dela é o tile do piso em marrom-escuro (não o preto da mata).

Espinha da fase (x para a direita, y para baixo, em tiles; a câmera mostra ~10 x 5,6 tiles, então as peças altas ficam
a sul/direita da estrada e as baixas a norte):
  trecho 1  "A Rampa": do início (SO) por uma rampa estreita de ~5 tiles de largura, com o primeiro encontro (2-3);
  trecho 2  "O Campo de Fossos": a pedreira funda, com seis fossos, a bifurcação do bolsão e a ponte de tábuas sobre o maior deles;
  trecho 3  "Os Andaimes": o terraço dos guindastes, andaimes, blocos e carrinhos, com as matilhas mais densas;
  descanso  clareira de laje com braseiros; avenida de lampiões até o portão de pedra maciça: G (o elite) e X (o portal).
O mapa é fixo (sem sorteio fora das sementes) e sai igual a cada execução. Uso: python3 -I tools/mapas/gerar_fase_2.py
[--visao arquivo.png]: grava o mapa, os PNG de godot/art2d/fosso/ e (opcional) uma visão geral anotada. Ao fim ele escreve os pontos de
captura (`captura ...`) que a ferramenta godot/scripts2d/tools/captura_marcos_2d.gd aceita.
"""
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from marcos_fase1 import Curva   # noqa: E402  (Catmull-Rom como o jogo; amostra a curva por distância percorrida)
import fosso_pixel               # noqa: E402

RAIZ = AQUI.parents[1]
SAIDA = RAIZ / "godot/data2d/rooms/fase_2.txt"
PASTA_FOSSOS = RAIZ / "godot/art2d/fosso"
RES_FOSSOS = "res://art2d/fosso/"
TILE = 64
W, H = 160, 72
rng = random.Random(2202)

P = (13, 61)                      # início do arqueiro (célula)
LARG_ESTRADA = 2.0
LARG_TRILHA = 1.2
RAIO_GUARDA = 260                 # px: o encontro acorda a esta distância (a tela mostra 320 px de cada lado)
BRILHO_ESTRADA = 1.16             # as lajes da estrada levam 16% mais luz que o piso ocre em volta (separa estrada e chão)
# A reta da ponte tem ~15 tiles (5 de chegada, 7 de ponte e 3 de saída, de x = 67 a 82) e a estrada faz uma curva logo depois
# (revisão do Jev: nada de uma reta de 30 tiles); a bifurcação do bolsão sai da estrada em (57,4; 41,3).
ESTRADA = [(5.5, 61), (21, 61), (31, 58), (40, 52.5), (47, 46.5), (54, 42.2), (60, 41.0), (64, 40.3), (67, 40), (72, 40), (78, 40),
           (82, 40), (86.5, 39.0), (90.5, 37.0), (94, 34.0), (98.5, 31.4), (104, 29.6), (110, 28.5), (118, 25), (127, 22.5), (135, 22),
           (141, 21.5), (144, 19.5), (146, 17), (146, 13)]
TRILHA_BOLSAO = [(57.4, 41.3), (56.6, 36), (58, 31), (60, 27.5)]
BOLSAO = (60.0, 26.0, 3.4)        # centro e raio da clareira do baú
GATE = (146, 11.0)                # base do portão de pedra (os pés dos bastiões; a abertura fica no meio)
ELITE = (146, 13)                 # G: onde o elite espera (a 2 tiles na frente do portão, onde a estrada termina)
PORTAL = (146, 6)                 # X: o portal, atrás do portão
DESCANSO = (139.5, 21.6)          # clareira de laje com braseiros

# Fossos: lista de retângulos (coluna, linha, largura, altura) em células. O 0 é o da ponte: 7 x 5, a ponte (`=`) só na
# linha 40 (1 tile de largura: a estrada afunila na boca do fosso), a estrada (y = 40) passa pelo meio e sobram 2 linhas
# de fosso de cada lado dela.
FOSSOS = [
    [(72, 38, 7, 5)],
    [(63, 44, 6, 4)],
    [(63, 35, 6, 3)],
    [(85, 43, 5, 4), (88, 46, 3, 2)],
    [(84, 34, 4, 3)],
    [(97, 37, 5, 3)],
]
PONTE_FOSSO = 0
PONTE_LINHAS = (40,)
_c0, _l0, _w, _h = FOSSOS[PONTE_FOSSO][0]
PONTE_XA, PONTE_XB = _c0 - 0.5, _c0 + _w - 0.5   # bordas da ponte (unidades do mapa)

# Afloramentos de pedra dentro do salão (massas fechadas, `m`): quebram a vista e formam terraços
AFLORAMENTOS = [(70.0, 29.5, 2.6), (83.0, 27.0, 2.2), (97.5, 28.0, 2.4), (62.0, 50.5, 2.2), (86.0, 53.0, 2.6), (101.0, 47.5, 2.0),
                (122.0, 15.0, 2.2), (130.0, 31.5, 2.4), (116.5, 31.5, 1.8), (137.5, 13.5, 1.8)]
SALAS = [(77.0, 40.0, 27.0, 15.5), (127.0, 24.0, 16.5, 9.5), (13.0, 61.0, 8.0, 7.0), (146.0, 10.0, 8.5, 7.5),
         (DESCANSO[0], DESCANSO[1], 6.5, 6.0), (BOLSAO[0], BOLSAO[1], BOLSAO[2], BOLSAO[2])]   # elipses (cx, cy, rx, ry)
PERFIL_HW = [(0, 4.0), (21, 4.0), (27, 2.3), (46, 2.3), (51, 5.5), (56, 8.5), (100, 8.5), (106, 3.6), (113, 3.4), (118, 5.5),
             (141, 5.5), (144, 4.2), (150, 4.2)]   # meia-largura do corredor por coluna do ponto mais perto da estrada

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)   # a célula (c, l) tem o centro em (c, l) nas unidades do mapa


def ruido(x, y, s):
    """Ruído suave e determinístico (soma de senos), entre -1 e 1; a mesma receita do gerador da área 1."""
    return (np.sin(x * 0.21 + s) * np.cos(y * 0.17 + s * 1.7) * 0.5
            + np.sin(x * 0.07 + y * 0.05 + s * 2.3) * 0.35
            + np.sin(x * 0.43 - y * 0.37 + s * 0.9) * 0.15)


def celula(u):
    return int(math.floor(u + 0.5))


# --------------------------------------------------------------------------------------------------------------------
# Estrada e área andável
# --------------------------------------------------------------------------------------------------------------------
estrada = Curva(ESTRADA)
trilha = Curva(TRILHA_BOLSAO)
pts_e = np.array(estrada.pts, dtype=np.float32)
s_e = np.array(estrada.s, dtype=np.float32)
pts_t = np.array(trilha.pts, dtype=np.float32)


def dist_curva(pts, x, y):
    return float(np.sqrt(((pts[:, 0] - x) ** 2 + (pts[:, 1] - y) ** 2).min()))


def mapa_dist(pts):
    d2 = np.full((H, W), 1e9, np.float32)
    idx = np.zeros((H, W), np.int32)
    for i in range(len(pts)):
        d = (xx - pts[i, 0]) ** 2 + (yy - pts[i, 1]) ** 2
        m = d < d2
        d2[m] = d[m]
        idx[m] = i
    return np.sqrt(d2), idx


d_estrada, i_estrada = mapa_dist(pts_e)
d_trilha, _ = mapa_dist(pts_t)
x_perto = pts_e[i_estrada, 0]
hw = np.interp(x_perto, [p[0] for p in PERFIL_HW], [p[1] for p in PERFIL_HW])
n1 = ruido(xx, yy, 1.3) * 1.5 + ruido(yy, xx, 4.1) * 0.9
aberto = d_estrada < hw + n1
for cx, cy, rx, ry in SALAS:
    aberto |= ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 < 1.0 + 0.11 * n1
aberto |= d_trilha < 1.5 + 0.3 * n1
aberto |= d_estrada < 2.3          # a estrada e 1,3 tile de cada lado dela ficam sempre abertos
aberto |= np.hypot(xx - P[0], yy - P[1]) < 5.0
for k in range(2):                 # alisa degraus de 1 célula (maioria 3 x 3)
    pad = np.pad(aberto, 1, constant_values=False).astype(np.int32)
    soma = sum(pad[1 + dy:1 + dy + H, 1 + dx:1 + dx + W] for dy in (-1, 0, 1) for dx in (-1, 0, 1))
    aberto = (soma >= 5) | (d_estrada < 2.3)
beira = np.minimum.reduce([xx, yy, W - 1 - xx, H - 1 - yy])
aberto &= beira >= 3

# afloramentos: massas de pedra fechadas dentro do salão, longe da estrada (bordas onduladas)
n2 = ruido(xx, yy, 7.7) * 1.0
for cx, cy, r in AFLORAMENTOS:
    massa = (np.hypot(xx - cx, yy - cy) < r + 0.6 * n2) & (d_estrada > r + 3.2) & (d_trilha > r + 2.0)
    aberto &= ~massa
aberto |= d_estrada < 2.3

grade = [["m"] * W for _ in range(H)]
for y in range(H):
    for x in range(W):
        if aberto[y, x]:
            grade[y][x] = "."


def vizinhos8(x, y):
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if (dx or dy) and 0 <= x + dx < W and 0 <= y + dy < H:
                yield x + dx, y + dy


# --------------------------------------------------------------------------------------------------------------------
# Fossos e a ponte
# --------------------------------------------------------------------------------------------------------------------
fossos = []        # [{celulas, ponte, rects}]
for k, rects in enumerate(FOSSOS):
    cel = set()
    for c0, l0, w, h in rects:
        cel |= {(c0 + i, l0 + j) for i in range(w) for j in range(h)}
    ponte = {c for c in cel if k == PONTE_FOSSO and c[1] in PONTE_LINHAS}
    fossos.append({"celulas": cel, "ponte": ponte, "rects": rects})
    for x, y in cel:
        if not aberto[y, x]:
            print("AVISO: fosso %d invade a mata em (%d, %d)" % (k, x, y))
for f in fossos:
    for x, y in f["celulas"]:
        grade[y][x] = "=" if (x, y) in f["ponte"] else "f"
# margem de 1 célula de chão em volta de cada fosso (o jogador anda em volta; a borda do PNG leva 16 px de beiral)
for k, f in enumerate(fossos):
    for x, y in f["celulas"]:
        for vx, vy in vizinhos8(x, y):
            if (vx, vy) not in f["celulas"] and grade[vy][vx] in "mf=":
                if grade[vy][vx] == "m":
                    grade[vy][vx] = "."   # abre a margem (a mata nunca encosta num fosso)
RECTS_FOSSO = []   # (x0, y0, x1, y1) em unidades do mapa (bordas das células)
for f in fossos:
    for c0, l0, w, h in f["rects"]:
        RECTS_FOSSO.append((c0 - 0.5, l0 - 0.5, c0 + w - 0.5, l0 + h - 0.5))


def dist_fosso(x, y):
    d = 1e9
    for x0, y0, x1, y1 in RECTS_FOSSO:
        dx = max(x0 - x, 0.0, x - x1)
        dy = max(y0 - y, 0.0, y - y1)
        d = min(d, math.hypot(dx, dy))
    return d


# --------------------------------------------------------------------------------------------------------------------
# Marcadores: P, braseiros (B), E (pontos de inimigo do fluxo por etapas), G, X
# --------------------------------------------------------------------------------------------------------------------
def marcar(x, y, c):
    xi, yi = celula(x), celula(y)
    if grade[yi][xi] not in ".":
        raise SystemExit("marcador %r em célula %r (%g, %g)" % (c, grade[yi][xi], x, y))
    grade[yi][xi] = c
    return xi, yi


# --------------------------------------------------------------------------------------------------------------------
# Props
# --------------------------------------------------------------------------------------------------------------------
LASCAS = ["pedreira_lasca_0", "pedreira_lasca_1", "pedreira_lasca_2"]   # fragmentos de bloco cortado: no lugar das pedras redondas
RAIO = {"rock_large": 0.8, "rock_cluster": 0.65, "rock_slabs": 0.7, "rock_mossy": 0.75, "rock_rubble": 0.55,
        "pedreira_lasca_0": 0.3, "pedreira_lasca_1": 0.45, "pedreira_lasca_2": 0.55, "pedreira_portao": 4.2,
        "tree_dead_large": 0.8, "tree_dead_medium": 0.6, "tree_dry_pile": 0.9, "tree_dead_webs": 0.7, "tree_dry_leaning": 0.8,
        "tree_hollow": 0.7, "tree_dry_small": 0.55, "pedreira_blocos": 0.85, "pedreira_andaime": 0.8, "pedreira_carrinho": 0.85,
        "pedreira_portico": 1.3, "pedreira_poste_lanterna": 0.35, "pillar_broken": 0.6, "pillar_cracked": 0.55, "pillar_tall": 0.5,
        "pillar_fallen": 0.9, "arco_portal": 0.4, "skull_mound_candles": 0.4, "log_fallen": 0.7, "skull_pile": 0.4,
        "skull_spike": 0.3, "bones_scattered": 0.45, "bones_ribcage": 0.5, "vines_dry_rock": 0.7, "altar_candles": 0.7,
        "tomb_flowers": 0.7, "grave_broken": 0.5, "coffin_lid_leaning": 0.6, "sapling_dead": 0.4}
BAIXOS = {"rock_rubble", "grass_dry_patch", "grass_dry_tall", "thistles_dry", "leaves_scattered", "leaves_pile", "branches_fallen",
          "bones_scattered", "skull_single", "skull_pair", "flowers_dead", "reeds_dry", "ferns_withered", "roots_clump", "skeleton_hand",
          "skeleton_curled", "bones_chains", "leaves_bone"} | set(LASCAS)   # sem corpo sólido: podem ficar na beira da estrada
props = []            # [id, x, y, flip, raio]
_hash = {}


def _chave(x, y):
    return int(x // 2), int(y // 2)


def _vizinhanca(x, y):
    cx, cy = _chave(x, y)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            yield from _hash.get((cx + dx, cy + dy), ())


def _guardar(item):
    props.append(item)
    _hash.setdefault(_chave(item[1], item[2]), []).append(item)


def limpar(x, y, r, so_ids=None):
    """Tira os props sem marco num raio (antes de pôr um marco no lugar)."""
    for item in list(_vizinhanca(x, y)) + list(_vizinhanca(x + 2, y + 2)) + list(_vizinhanca(x - 2, y - 2)):
        if item in props and math.hypot(item[1] - x, item[2] - y) < r and (so_ids is None or item[0] in so_ids):
            props.remove(item)
            _hash[_chave(item[1], item[2])].remove(item)


def livre(ident, x, y, raio, mata=False, estrada_folga=None):
    xi, yi = celula(x), celula(y)
    if not (1 <= xi < W - 1 and 1 <= yi < H - 1):
        return False
    if mata:
        if grade[yi][xi] != "m":
            return False
    else:
        if grade[yi][xi] != ".":
            return False
        for vx, vy in vizinhos8(xi, yi):
            if grade[vy][vx] in "BPEXG":
                return False
        if dist_fosso(x, y) < 0.95 + raio * 0.4:
            return False
        folga = estrada_folga if estrada_folga is not None else (1.2 if ident in BAIXOS else 1.0 + raio + 0.15)
        if dist_curva(pts_e, x, y) < folga:
            return False
        if dist_curva(pts_t, x, y) < min(folga, 1.0 + raio * 0.5):
            return False
        if math.hypot(x - P[0], y - P[1]) < 3.0:
            return False
    for item in _vizinhanca(x, y):
        if math.hypot(item[1] - x, item[2] - y) < (raio + item[4]) * 0.92:
            return False
    return True


def pôr(ident, x, y, flip=False, raio=None, forcar=False, **kw):
    raio = RAIO.get(ident, 0.45) if raio is None else raio
    if forcar:
        limpar(x, y, raio + 0.2)
    elif not livre(ident, x, y, raio, **kw):
        return False
    _guardar([ident, round(x, 2), round(y, 2), flip, raio])
    return True


def espalhar(ids, n, caixa, tentativas=None, filtro=None, **kw):
    x0, y0, x1, y1 = caixa
    feitos = 0
    for _ in range(tentativas or n * 40):
        if feitos >= n:
            break
        x, y = round(rng.uniform(x0, x1), 1), round(rng.uniform(y0, y1), 1)
        if filtro is not None and not filtro(x, y):
            continue
        if pôr(rng.choice(ids), x, y, rng.random() < 0.5, **kw):
            feitos += 1
    return feitos


def em(s, lat=0.0):
    return estrada.em(s, lat)


def dist_ao_aberto(raio=7):
    ab = np.array([[c != "m" for c in l] for l in grade])
    res = np.full((H, W), raio + 1.0, np.float32)
    res[ab] = 0.0
    pad = np.pad(ab, raio, constant_values=False)
    feito = ab.copy()
    for d, dx, dy in sorted((math.hypot(dx, dy), dx, dy) for dy in range(-raio, raio + 1) for dx in range(-raio, raio + 1)
                            if 0 < math.hypot(dx, dy) <= raio):
        novo = pad[raio + dy:raio + dy + H, raio + dx:raio + dx + W] & ~feito
        res[novo] = d
        feito |= novo
    return res


luzes = []      # (x, y, raio_tiles, (r, g, b, a))
guardas = []    # (x, y, raio_px, forca, spec)
bolsoes = []
decalques = []  # (arquivo, x_px, y_px, topo)
lajes = []      # (tom, raio, x, y)
capturas = {}
marcos_s = {}   # nome -> s (distância ao longo da estrada) dos marcos, para a checagem de ritmo
LUZ_LAMPIAO = (1.0, 0.55, 0.2, 0.26)   # laranja quente e fraca: o G alto puxava o chão para verde-limão (revisão do Jev e da arte)


def poste(s, lat, flip=False, luz=True):
    x, y = em(s, lat)
    pôr("pedreira_poste_lanterna", x, y, flip, forcar=True)
    if luz:
        luzes.append((x + (-0.55 if flip else 0.55), y - 1.0, 3.4, LUZ_LAMPIAO))
    return x, y


def braseiro(s, lat):
    """Braseiro (`B`): o motor já põe o halo dele; nada de `@luz` por cima, que empilhava dois halos e estourava as lajes."""
    x, y = em(s, lat)
    limpar(x, y, 1.4)
    return marcar(x, y, "B")


# ---- Início ----
S_P = estrada.s_mais_perto(*P)
grade[P[1]][P[0]] = "P"
lajes.append(("claro", 5.2, P[0] + 1.6, P[1]))          # pátio de laje cortada onde o arqueiro nasce
for lado in (-2.2, 2.2):             # dois braseiros logo à frente do arqueiro: a luz quente acolhe o começo (como na área 1)
    braseiro(S_P + 2.4, lado)
for lado, flip in ((-2.3, True), (2.3, False)):   # dois lampiões na boca da rampa
    poste(S_P + 10.0, lado, flip)
pôr("pedreira_carrinho", *em(S_P - 2.9, -2.4), False, forcar=True)
pôr("pedreira_blocos", *em(S_P - 2.6, 2.3), True, forcar=True)
pôr("pedreira_andaime", *em(S_P + 15.0, 4.0), forcar=True)
pôr("rock_slabs", *em(S_P + 1.0, -3.6), forcar=True)
marcos_s["inicio"] = S_P
capturas["1_inicio"] = (P[0], P[1], ":d")   # com a dica de controles dos primeiros segundos

# ---- Rampa (trecho 1) ----
S_RAMPA = estrada.s_mais_perto(38, 54)
for ds, lat, ident, flip in [(-6, 3.2, "pedreira_blocos", False), (2, -3.3, "rock_large", True), (8, 3.4, "pedreira_andaime", True),
                             (-2, 3.3, "pedreira_carrinho", False), (13, -3.0, "pedreira_blocos", True)]:
    x, y = em(S_RAMPA + ds, lat)
    pôr(ident, x, y, flip, forcar=True)
poste(S_RAMPA + 5.0, 2.3, True)
marcos_s["rampa"] = S_RAMPA

# ---- Bifurcação do bolsão (trecho 2): a trilha sai da estrada para o norte; o marco é a luz dos lampiões na boca dela e o
# guindaste do outro lado da estrada (alto, aparece por baixo da tela) ----
fx, fy = TRILHA_BOLSAO[0]
S_FORK = estrada.s_mais_perto(fx, fy)
lajes.append(("claro", 2.5, fx, fy - 1.9))                       # a boca da trilha é calçada: lê como bifurcação
limpar(fx, fy - 2.0, 2.6)
for dx, flip in ((-1.9, True), (1.9, False)):                     # dois lampiões na boca, acesos
    x_l, y_l = fx + dx, fy - 2.6
    pôr("pedreira_poste_lanterna", x_l, y_l, flip, forcar=True)
    luzes.append((x_l + (-0.55 if flip else 0.55), y_l - 1.0, 3.8, (1.0, 0.55, 0.2, 0.34)))
pôr("skull_mound_candles", fx + 0.3, fy - 4.4, forcar=True)       # velas no meio da trilha: chamam o olhar para dentro
x_g, y_g = em(S_FORK + 2.0, 3.9)
limpar(x_g, y_g, 1.6)
pôr("pedreira_portico", x_g, y_g, False, forcar=True)             # guindaste do marco, do lado sul da estrada
marcos_s["bifurcacao"] = S_FORK

# ---- Campo de fossos (trecho 2): ponte com lampiões ----
xa, xb = PONTE_XA, PONTE_XB      # bordas da ponte (unidades do mapa)
S_PONTE = estrada.s_mais_perto((xa + xb) / 2.0, 40.0)
poste_ponte = [(xa - 1.1, 42.2, False), (xb + 1.1, 37.8, True)]
for x, y, flip in poste_ponte:
    pôr("pedreira_poste_lanterna", x, y, flip, forcar=True)
    luzes.append((x + (-0.55 if flip else 0.55), y - 1.0, 3.6, LUZ_LAMPIAO))
marcos_s["ponte"] = S_PONTE
capturas["3_fosso"] = (xa - 0.6, 41.1)       # câmera na cabeceira oeste: a ponte à direita e o lampião do lado sul inteiro
capturas["3a_ponte"] = ((xa + xb) / 2.0, 40.0)
capturas["3b_curva_depois_da_ponte"] = (*em(S_PONTE + 12.0), ":g")

# ---- Trecho 3 (terraço dos andaimes): o pórtico fica na beira sul, fora da estrada ----
S_T3 = estrada.s_mais_perto(124, 23.2)
x_p3, y_p3 = em(S_T3, 3.8)
pôr("pedreira_portico", x_p3, y_p3, False, forcar=True)
marcos_s["portico"] = S_T3
capturas["4_andaimes"] = (*em(S_T3 - 1.0), ":g")

# ---- Descanso e avenida do portão ----
S_FIM = estrada.comprimento
S_DESC = estrada.s_mais_perto(*DESCANSO)
rx, ry = em(S_DESC)
lajes.append(("claro", 4.6, rx, ry))
limpar(rx, ry, 5.0)
for lado, ds in [(-2.8, -1.0), (2.8, 1.0)]:
    braseiro(S_DESC + ds, lado)
pôr("log_fallen", *em(S_DESC - 2.6, 2.7), False, forcar=True)
pôr("log_fallen", *em(S_DESC + 2.9, -2.6), True, forcar=True)
pôr("skull_mound_candles", *em(S_DESC + 0.3, 4.6), forcar=True)
marcos_s["descanso"] = S_DESC
capturas["5_descanso"] = None   # definido abaixo, com a câmera deslocada para o braseiro do lado sul

gx, gy = GATE
S_PORT = estrada.s_mais_perto(gx, gy + 2.0)
# Portão de pedra maciça (bastiões, verga, grade de ferro levantada e guindaste; não repete o arco da área 1): o sprite é
# um só, com os dois bastiões sólidos e a abertura de 2 tiles no meio, por onde se chega ao portal (X). Fica nos pés.
limpar(gx, gy, 4.0)
pôr("pedreira_portao", gx, gy, False, forcar=True)
for dx in (-3.0, 3.0):                                            # braseiros em frente aos bastiões: a luz quente acolhe o elite
    limpar(gx + dx, gy + 2.2, 1.4)
    marcar(gx + dx, gy + 2.2, "B")
for dx, dy in [(-4.0, 0.9), (4.1, 0.8)]:                          # caveiras só como detalhe, ao pé dos bastiões
    pôr("skull_pile", gx + dx, gy + dy, forcar=True)
luzes.append((ELITE[0], ELITE[1] - 0.3, 3.8, (1.0, 0.4, 0.14, 0.4)))   # luz própria do elite: ele espera dentro de um poço de luz quente
marcos_s["portao"] = S_PORT
# O portão fecha a clareira: a rocha liga os pés dos bastiões às paredes (as linhas gy-1 e gy; o pé deles toma a faixa de baixo
# da linha gy) e o único caminho para o portal (X) é o vão de 2 tiles no meio.
gxi, gyi = int(gx), int(gy)
for ly in (gyi - 1, gyi):
    x_ini = x_fim = gxi
    while x_ini > 0 and grade[ly][x_ini - 1] != "m":
        x_ini -= 1
    while x_fim < W - 1 and grade[ly][x_fim + 1] != "m":
        x_fim += 1
    for lx in range(x_ini, x_fim + 1):
        if (lx <= gxi - 3 or lx >= gxi + 3) and grade[ly][lx] == ".":
            grade[ly][lx] = "m"
lajes.append(("claro", 4.2, gx, gy + 3.4))     # a praça do elite, na frente do portão
lajes.append(("escuro", 3.0, gx, gy + 3.4))
lajes.append(("claro", 4.0, gx, gy - 5.0))     # e o pátio do portal, atrás dele (as duas pontas ficam longe da rocha que fecha a clareira)
lajes.append(("escuro", 2.8, gx, gy - 5.0))
# avenida: pares de lampiões e entulho de pedreira entre o descanso e o portão
s = S_DESC + 6.0
k = 0
while s < S_PORT - 3.5:
    x1, y1 = poste(s, -2.5, True)
    x2, y2 = poste(s, 2.5, False)
    for lado in (-4.4, 4.4):
        if rng.random() < 0.7:
            pôr(["pedreira_blocos", "pillar_broken", "rock_large", "pillar_cracked"][(k + (lado > 0)) % 4], *em(s + 1.8, lado + rng.uniform(-0.3, 0.3)),
                rng.random() < 0.5, forcar=True)
    s += 4.6
    k += 1
G_CEL = marcar(*ELITE, "G")
X_CEL = marcar(*PORTAL, "X")


def com_camera(jogador, alvo, extra=""):
    """Ponto de captura: o jogador fica em `jogador` e a câmera (só ela) vai até `alvo`; `extra` leva os sufixos (`:g`, `:e`)."""
    return (jogador[0], jogador[1], "%s:cx%d:cy%d" % (extra, round((alvo[0] - jogador[0]) * TILE), round((alvo[1] - jogador[1]) * TILE)))


# `:g` = os encontros ao alcance nascem adormecidos e dormem na foto; a rampa: o arqueiro 3,5 tiles antes do encontro e a câmera à frente dele
capturas["2_rampa"] = com_camera(em(S_RAMPA - 3.5), em(S_RAMPA - 1.0), ":g")
# a bifurcação: o arqueiro na beira norte da estrada e a câmera 1,8 tile ao norte dele, com os dois lampiões inteiros, as velas e a
# boca da trilha do bolsão (o poste tem 107 px: mais alto que isso o arqueiro sairia do quadro)
capturas["3c_bifurcacao"] = com_camera((fx - 1.0, fy - 0.2), (fx - 0.5, fy - 2.0), ":g")
capturas["6_portao_elite"] = com_camera((gx - 1.6, gy + 3.6), (gx, gy + 0.2), ":e")   # o elite parado na frente do portão, com a luz dele
capturas["6a_portao_perto"] = com_camera((gx, gy + 0.62), (gx, gy - 1.3))   # o portão inteiro, do guindaste aos pés dos bastiões
capturas["5_descanso"] = com_camera(em(S_DESC - 1.5), (rx, ry + 1.3))   # a clareira de laje com o braseiro do lado sul à vista

# pousos de laje nas duas pontas da ponte e plataformas de pedra cortada espalhadas pelo salão e pelo terraço (quebram o ocre)
lajes.append(("claro", 2.3, xa - 1.9, 40.0))
lajes.append(("claro", 2.3, xb + 1.9, 40.0))
n_plat = 0
for _ in range(400):
    if n_plat >= 11:
        break
    cx_, cy_ = rng.uniform(20, 148), rng.uniform(10, 62)
    r_ = rng.uniform(2.0, 3.6)
    xi, yi = celula(cx_), celula(cy_)
    if not (0 <= xi < W and 0 <= yi < H) or not aberto[yi, xi]:
        continue
    if dist_curva(pts_e, cx_, cy_) < r_ + 2.2 or dist_fosso(cx_, cy_) < r_ + 1.4 or dist_curva(pts_t, cx_, cy_) < r_ + 1.5:
        continue
    if any(math.hypot(cx_ - lx, cy_ - ly) < lr + r_ + 2.0 for _, lr, lx, ly in lajes):
        continue
    if math.hypot(cx_ - P[0], cy_ - P[1]) < 9 or not all(0 <= celula(cx_ + math.cos(a) * r_) < W and aberto[celula(cy_ + math.sin(a) * r_), celula(cx_ + math.cos(a) * r_)]
                                                     for a in np.linspace(0, math.tau, 12, endpoint=False)):
        continue
    lajes.append((rng.choice(["claro", "claro", "escuro"]), round(r_, 1), round(cx_, 1), round(cy_, 1)))
    n_plat += 1

# ---- Bolsão: o baú da pedreira (um depósito de ferramentas) ----
bcx, bcy, br = BOLSAO
limpar(bcx, bcy, br + 0.4)
pôr("pedreira_carrinho", bcx - 1.5, bcy - 1.0, False, forcar=True)
pôr("pedreira_blocos", bcx + 2.0, bcy - 0.8, True, forcar=True)
pôr("pedreira_andaime", bcx - 0.4, bcy - 2.4, False, forcar=True)
for dx, dy in [(-2.3, 0.9), (2.2, 1.1), (-1.0, 1.9)]:
    pôr("skull_mound_candles", bcx + dx, bcy + dy, forcar=True)
luzes.append((bcx, bcy - 0.4, 4.4, (1.0, 0.55, 0.2, 0.4)))
bolsoes.append((bcx, bcy + 0.4, "bau"))
guardas.append((bcx - 0.8, bcy - 0.2, RAIO_GUARDA, 1.1, "skeleton_soldier:2|hollow_sentinel:1"))
capturas["bolsao"] = (bcx, bcy + 2.0, ":g")

# ---- Encontros na estrada (por distância s), um a cada ~20 tiles; só os trechos 2 e 3 têm matilhas de 3+ ----
S_APROX = estrada.s_mais_perto(66.0, 40.0)    # a chegada da ponte, entre dois fossos: a arqueira fantasma atira por cima do vão
S_CURVA = estrada.s_mais_perto(91.0, 37.0)    # a curva logo depois da ponte
ENCONTROS = [
    (17.0, 0.8, 0.85, "skeleton_soldier:2|hollow_sentinel:1"),     # trecho 1: o primeiro encontro, 2-3 inimigos
    (36.0, -0.8, 0.9, "crypt_bat:2|skeleton_soldier:1"),
    (56.0, 0.8, 0.95, "skeleton_soldier:3|wandering_ghost:1"),      # trecho 2: matilhas
    (S_APROX, 0.9, 1.0, "skeleton_soldier:2|ghost_archer:1"),
    (S_CURVA, -0.8, 1.05, "crypt_bat:3|hollow_sentinel:1"),
    (110.0, 0.8, 1.1, "chain_wraith:1|skeleton_soldier:2"),         # trecho 3: os mais densos
    (127.0, 0.8, 1.15, "skeleton_soldier:3|hollow_sentinel:1"),
    (141.0, -0.8, 1.2, "ghost_archer:2|skeleton_soldier:2"),
]
for s_g, lat, forca, spec in ENCONTROS:
    gx_, gy_ = em(s_g, lat)
    guardas.append((gx_, gy_, RAIO_GUARDA, forca, spec))
    marcos_s["guarda@%d" % s_g] = s_g

# ---- Pontos E (fluxo por etapas): ao longo da estrada, em células livres ----
for s_e_, lat in [(14, 2.5), (30, -2.5), (46, 2.5), (62, -2.5), (76, 2.5), (100, -2.5), (116, 2.5), (131, -2.5)]:
    x, y = em(s_e_, lat)
    xi, yi = celula(x), celula(y)
    if grade[yi][xi] == "." and dist_fosso(x, y) > 1.5:
        grade[yi][xi] = "E"

# --------------------------------------------------------------------------------------------------------------------
# Orla de rocha, chão e equipamento da pedreira
# --------------------------------------------------------------------------------------------------------------------
d_ab = dist_ao_aberto()
ROCHA_ORLA = ["rock_large"] * 7 + ["rock_cluster"] * 3 + ["rock_slabs"] * 2 + ["rock_mossy"] + ["pedreira_blocos"]
ARV_SECAS = ["tree_dead_large", "tree_dead_medium", "tree_dry_pile", "tree_dead_webs", "tree_dry_leaning", "tree_hollow", "tree_dry_small"]
celulas_orla = [(x, y) for y in range(H) for x in range(W) if grade[y][x] == "m" and d_ab[y, x] <= 3.4]
rng.shuffle(celulas_orla)
for x, y in celulas_orla:
    for _ in range(2):
        px, py = round(x + rng.uniform(-0.45, 0.45), 1), round(y + rng.uniform(-0.45, 0.45), 1)
        ident = rng.choice(ARV_SECAS) if rng.random() < 0.14 else rng.choice(ROCHA_ORLA)
        if pôr(ident, px, py, rng.random() < 0.5, mata=True):
            break
# mais fundo na mata de rocha: pedras e árvores secas esparsas (a câmera vê 5 tiles para dentro da borda)
profundas = [(x, y) for y in range(H) for x in range(W) if grade[y][x] == "m" and 3.4 < d_ab[y, x] <= 6.5]
rng.shuffle(profundas)
for x, y in profundas[: len(profundas) // 3]:
    pôr(rng.choice(["rock_large", "rock_cluster", "rock_slabs"] + ARV_SECAS[:3]), round(x + rng.uniform(-0.4, 0.4), 1),
        round(y + rng.uniform(-0.4, 0.4), 1), rng.random() < 0.5, mata=True)
# pedregulhos na beira de dentro do salão (a borda da mata não é uma linha)
beira_dentro = [(x, y) for y in range(H) for x in range(W) if grade[y][x] == "." and any(grade[vy][vx] == "m" for vx, vy in vizinhos8(x, y))]
rng.shuffle(beira_dentro)
for x, y in beira_dentro[: len(beira_dentro) // 2]:
    pôr(rng.choice(LASCAS + LASCAS + ["grass_dry_patch", "thistles_dry"]), round(x + rng.uniform(-0.4, 0.4), 1),
        round(y + rng.uniform(-0.4, 0.4), 1), rng.random() < 0.5)

# entulho em volta de cada fosso: cascalho e lajes soltas na borda (esconde o corte reto do chão com o beiral do PNG)
for f in fossos:
    for c0, l0, w, h in f["rects"]:
        perim = 2 * (w + h)
        for k in range(perim * 2):
            a = rng.uniform(0, 4)
            if a < 1:
                x, y = c0 - 0.5 + rng.uniform(0, w), l0 - 0.5 - rng.uniform(0.5, 1.4)
            elif a < 2:
                x, y = c0 - 0.5 + rng.uniform(0, w), l0 + h - 0.5 + rng.uniform(0.5, 1.4)
            elif a < 3:
                x, y = c0 - 0.5 - rng.uniform(0.5, 1.4), l0 - 0.5 + rng.uniform(0, h)
            else:
                x, y = c0 + w - 0.5 + rng.uniform(0.5, 1.4), l0 - 0.5 + rng.uniform(0, h)
            pôr(rng.choice(LASCAS + LASCAS + ["branches_fallen", "thistles_dry"]), round(x, 1), round(y, 1),
                rng.random() < 0.5, raio=0.4)

# equipamento da pedreira perto da estrada, com metas por peça. As peças altas (andaime, pórtico) ficam ao sul/direita (a copa
# entra na tela de baixo) e a mais de 3,2 tiles do eixo; as baixas (blocos, carrinho) valem dos dois lados.
def perto_da_estrada(ids, n, s_ini, s_fim, lat_min, lat_max, sul=0.62, tentativas=None):
    feitos = 0
    for _ in range(tentativas or n * 120):
        if feitos >= n:
            break
        lado = 1 if rng.random() < sul else -1
        x, y = em(rng.uniform(s_ini, s_fim), lado * rng.uniform(lat_min, lat_max))
        if dist_fosso(x, y) < 1.9:
            continue
        if pôr(rng.choice(ids), x, y, rng.random() < 0.5):
            feitos += 1
    return feitos


extras = 0
for s_p in [float(v) for v in range(86, 124, 2)] + [30.0, 44.0, 24.0]:   # um pórtico extra entre a curva e o terraço (o primeiro que couber)
    if extras >= 1:
        break
    for lat_p in (4.4, 4.0, 4.8, 3.8, 5.2):
        x, y = em(s_p, lat_p)
        xi, yi = celula(x), celula(y)
        if grade[yi][xi] == "." and dist_fosso(x, y) > 2.6 and all(grade[yi + dy][xi + dx] != "m" for dx in (-1, 0, 1) for dy in (-1, 0, 1)) \
                and not any(math.hypot(it[1] - x, it[2] - y) < 22 for it in props if it[0] == "pedreira_portico"):
            pôr("pedreira_portico", x, y, forcar=True)
            marcos_s["portico@%d" % s_p] = s_p
            extras += 1
            break
if extras < 1:
    print("AVISO: nenhum pórtico extra coube")
perto_da_estrada(["pedreira_carrinho"], 10, 22.0, S_DESC - 4, 2.9, 6.0, sul=0.5)
perto_da_estrada(["pedreira_andaime"], 12, 22.0, S_DESC - 4, 3.4, 6.5, sul=0.85)
perto_da_estrada(["pedreira_blocos"], 24, 22.0, S_DESC - 4, 2.8, 6.5, sul=0.5)
# e na beira de dentro das paredes do terraço e do salão (a mais de 3,4 tiles da estrada)
for _ in range(900):
    x, y = rng.uniform(20, W - 10), rng.uniform(8, H - 8)
    xi, yi = celula(x), celula(y)
    if not (0 <= xi < W and 0 <= yi < H) or grade[yi][xi] != "." or not any(grade[vy][vx] == "m" for vx, vy in vizinhos8(xi, yi)):
        continue
    if dist_curva(pts_e, x, y) < 3.4 or dist_fosso(x, y) < 2.0:
        continue
    pôr(rng.choice(["pedreira_andaime", "pedreira_blocos", "pedreira_blocos", "pedreira_carrinho"]), x, y, rng.random() < 0.5)

# entulho baixo na faixa de 1,6 a 3,0 tiles de cada lado da estrada: é o que a câmera (±2,8 tiles) mostra do chão em volta
s_ent = 3.0
while s_ent < S_FIM - 4:
    for lado in (-1, 1):
        if rng.random() < 0.62:
            x, y = em(s_ent + rng.uniform(-1.0, 1.0), lado * rng.uniform(1.7, 2.9))
            pôr(rng.choice(LASCAS + LASCAS + ["rock_slabs", "grass_dry_patch", "thistles_dry", "branches_fallen", "bones_scattered",
                            "leaves_scattered", "skull_single"]), x, y, rng.random() < 0.5, estrada_folga=1.3)
    s_ent += 1.7

# lampiões ao longo da estrada (um a cada ~26 tiles), do lado sul
for s_l in range(30, int(S_DESC) - 6, 26):
    if abs(s_l - S_PONTE) > 8:
        poste(s_l, 2.6 if (s_l // 26) % 2 == 0 else -2.6, (s_l // 26) % 2 == 1)

# chão: pedras soltas, cardos, ossos; pouca vegetação (a pedreira é seca)
CHAO = LASCAS + LASCAS + ["grass_dry_patch", "thistles_dry", "leaves_scattered", "bones_scattered", "branches_fallen",
                         "grass_dry_tall", "skull_single", "rock_slabs"]
espalhar(CHAO, 520, (6, 4, 154, 72), estrada_folga=None)
espalhar(["rock_cluster", "rock_large", "rock_slabs"], 36, (6, 4, 154, 72), filtro=lambda x, y: dist_curva(pts_e, x, y) > 3.4 and dist_fosso(x, y) > 3.6)   # lajes grandes longe dos fossos: junto da borda, só lascas
espalhar(ARV_SECAS, 16, (6, 4, 154, 72), filtro=lambda x, y: dist_curva(pts_e, x, y) > 4.5 and dist_fosso(x, y) > 2.5)

# --------------------------------------------------------------------------------------------------------------------
# Fossos pintados (PNG por código) e diretivas
# --------------------------------------------------------------------------------------------------------------------
PASTA_FOSSOS.mkdir(parents=True, exist_ok=True)
for k, f in enumerate(fossos):
    img, (ox, oy) = fosso_pixel.pintar_fosso(f["celulas"], semente=11 + 7 * k)
    img.save(PASTA_FOSSOS / ("fosso_%d.png" % k))
    decalques.append(("fosso_%d.png" % k, ox, oy, False))
    if f["ponte"]:
        img, (ox, oy) = fosso_pixel.pintar_ponte(f["ponte"], semente=5)
        img.save(PASTA_FOSSOS / ("ponte_%d.png" % k))
        decalques.append(("ponte_%d.png" % k, ox, oy, True))

linhas = ["".join(l) for l in grade]
linhas.append("@piso pedreira")
linhas.append("@caminho %g %s" % (LARG_ESTRADA, " ".join("%g,%g" % p for p in ESTRADA)))
linhas.append("@caminho %g %s" % (LARG_TRILHA, " ".join("%g,%g" % p for p in TRILHA_BOLSAO)))
for tom, r, x, y in lajes:
    linhas.append("@lajes %s %g %g,%g" % (tom, r, round(x, 2), round(y, 2)))
for arq, x, y, topo in decalques:
    linhas.append("@decalque %s%s %d %d%s" % (RES_FOSSOS, arq, x, y, " topo" if topo else ""))
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
# Checagens: conexão, ritmo, retirada do primeiro encontro, matilhas por trecho, props fora dos fossos
# --------------------------------------------------------------------------------------------------------------------
def alcancaveis(origem):
    vis = {origem}
    fila = [origem]
    while fila:
        x, y = fila.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in vis and 0 <= n[0] < W and 0 <= n[1] < H and grade[n[1]][n[0]] not in "m#fO":
                vis.add(n)
                fila.append(n)
    return vis


alc = alcancaveis(P)
problemas = []
for nome, (cx, cy) in {"G": G_CEL, "X": X_CEL, "bolsão": (celula(bcx), celula(bcy))}.items():
    if (cx, cy) not in alc:
        problemas.append("%s fora do alcance do início" % nome)
for x, y, _, _, spec in guardas:
    if (celula(x), celula(y)) not in alc:
        problemas.append("encontro %s em célula inalcançável (%g, %g)" % (spec, x, y))
for ident, x, y, flip, r in props:
    if grade[celula(y)][celula(x)] in "f=":
        problemas.append("prop %s sobre fosso (%g, %g)" % (ident, x, y))
ritmo = sorted(v for k, v in marcos_s.items() if k not in ("inicio",))
marcos_ordem = sorted(marcos_s.items(), key=lambda kv: kv[1])
maior_vazio = (0.0, "")
anterior = ("inicio", marcos_s["inicio"])
for nome, v in marcos_ordem:
    if nome == "inicio":
        continue
    if nome in ("portao",):
        break   # do descanso ao portão (avenida) e o descanso em si são o respiro: não contam
    if nome == "descanso":
        vazio = v - anterior[1]
        maior_vazio = max(maior_vazio, (vazio, "%s -> %s" % (anterior[0], nome)))
        break
    vazio = v - anterior[1]
    maior_vazio = max(maior_vazio, (vazio, "%s -> %s" % (anterior[0], nome)))
    anterior = (nome, v)
print("estrada: %.1f tiles (inicio s=%.1f, rampa %.1f, ponte %.1f, pórtico %.1f, descanso %.1f, portão %.1f)" % (
    S_FIM, S_P, S_RAMPA, S_PONTE, S_T3, S_DESC, S_PORT))
print("maior intervalo sem encontro nem marco (antes do descanso): %.1f tiles (%s) = %.1f s a 4 tiles/s" % (
    maior_vazio[0], maior_vazio[1], maior_vazio[0] / 4.0))
if maior_vazio[0] > 24.0:
    problemas.append("trecho vazio de %.1f tiles (> 24, ~6 s)" % maior_vazio[0])
pri = [g for g in guardas if abs(g[0] - em(17.0, 0.8)[0]) < 0.01]
n_pri = sum(int(t.split(":")[1]) for t in pri[0][4].split("|")) if pri else 0
print("primeiro encontro: %d inimigos" % n_pri)
if not 2 <= n_pri <= 3:
    problemas.append("o primeiro encontro deve ter 2 ou 3 inimigos (tem %d)" % n_pri)
for s_g, lat, forca, spec in ENCONTROS:
    n = sum(int(t.split(":")[1]) for t in spec.split("|"))
    if s_g < S_RAMPA + 14 and n > 3:
        problemas.append("matilha de %d no trecho 1 (s=%g)" % (n, s_g))
espaco_atras = sum(1 for (x, y) in alc if math.hypot(x - em(17.0)[0], y - em(17.0)[1]) < 12 and x < em(17.0)[0])
print("espaço para recuar atrás do primeiro encontro: %d células andáveis em 12 tiles" % espaco_atras)
tema_n = {i: sum(1 for p in props if p[0] == i) for i in ("pedreira_blocos", "pedreira_andaime", "pedreira_carrinho", "pedreira_portico", "pedreira_poste_lanterna")}
print("props da pedreira:", tema_n)
print("mapa: %d x %d, %d props, %d fossos (%d células), %d luzes, %d encontros, %d lajes" % (
    W, H, len(props), len(fossos), sum(len(f["celulas"]) for f in fossos), len(luzes), len(guardas), len(lajes)))
for k, v in capturas.items():
    print("captura %s:%.1f:%.1f%s" % (k, v[0], v[1], v[2] if len(v) > 2 else ""))
if problemas:
    print("PROBLEMAS:")
    for p in problemas:
        print("  -", p)

# --------------------------------------------------------------------------------------------------------------------
# Visão geral anotada (opcional): --visao arquivo.png
# --------------------------------------------------------------------------------------------------------------------
if "--visao" in sys.argv:
    destino = Path(sys.argv[sys.argv.index("--visao") + 1])
    E = 8
    im = Image.new("RGB", (W * E, H * E), (60, 42, 30))
    d = ImageDraw.Draw(im)
    for y in range(H):
        for x in range(W):
            c = grade[y][x]
            cor = {"m": (58, 40, 30), "f": (22, 30, 56), "=": (150, 100, 52)}.get(c, (196, 158, 96))
            d.rectangle([x * E, y * E, x * E + E - 1, y * E + E - 1], fill=cor)
            if c in "BPEXG":
                d.rectangle([x * E + 1, y * E + 1, x * E + E - 2, y * E + E - 2], fill={"B": (255, 140, 40), "P": (60, 200, 90), "E": (200, 60, 60), "X": (90, 160, 255), "G": (255, 60, 200)}[c])
    pts = [((px + 0.5) * E, (py + 0.5) * E) for px, py in estrada.pts]
    d.line(pts, fill=(235, 235, 225), width=int(LARG_ESTRADA * E * 0.5))
    d.line([((px + 0.5) * E, (py + 0.5) * E) for px, py in trilha.pts], fill=(235, 235, 225), width=int(LARG_TRILHA * E * 0.5))
    for ident, x, y, _, _ in props:
        cor = {"pedreira_portico": (255, 255, 40), "pedreira_andaime": (120, 70, 20), "pedreira_blocos": (150, 150, 160),
               "pedreira_carrinho": (90, 60, 40), "pedreira_poste_lanterna": (255, 220, 90), "pedreira_portao": (255, 255, 255)}.get(ident)
        if cor:
            d.rectangle([(x + 0.5) * E - 2, (y + 0.5) * E - 2, (x + 0.5) * E + 2, (y + 0.5) * E + 2], fill=cor)
    for x, y, raio, forca, spec in guardas:
        d.ellipse([(x + 0.5) * E - 5, (y + 0.5) * E - 5, (x + 0.5) * E + 5, (y + 0.5) * E + 5], outline=(255, 30, 30), width=2)
        d.text(((x + 0.5) * E + 7, (y + 0.5) * E - 5), spec.replace("skeleton_soldier", "sk").replace("hollow_sentinel", "sen").replace("crypt_bat", "bat")
               .replace("ash_hound", "cão").replace("ghost_archer", "arq").replace("stone_herald", "arauto"), fill=(255, 230, 230))
    for x, y, rec in bolsoes:
        d.rectangle([(x + 0.5) * E - 4, (y + 0.5) * E - 4, (x + 0.5) * E + 4, (y + 0.5) * E + 4], outline=(255, 215, 0), width=2)
    for s in range(0, int(S_FIM), 20):
        x, y = estrada.em(s)
        d.text(((x + 0.5) * E - 6, (y + 0.5) * E + 8), "s%d" % s, fill=(255, 255, 255))
    for nome, v in marcos_s.items():
        if not nome.startswith("guarda"):
            x, y = estrada.em(v)
            d.text(((x + 0.5) * E - 10, (y + 0.5) * E - 22), nome, fill=(120, 255, 160))
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino)
    print("visão geral:", destino)
