#!/usr/bin/env python3
"""Aglomerados de cenário nos vazios da fase aberta (decisão do Jev, 1/11/2026: +30% de props, em
grupos com sentido: cemitério pequeno, círculo de pedras, tronco caído, moitas, ruína, ossuário, arvoredo).

Lê godot/data2d/rooms/fase_1.txt, acha células livres longe da mata, das trilhas, do riacho, dos marcadores
e dos props que já existem, sorteia centros com semente fixa e acrescenta os props no fim da lista `@props`.
Rodar de novo é idempotente: as linhas geradas ficam copiadas em tools/mapas/fase_1.gerados.txt e são
removidas da fase antes de gerar outra vez.

    python3 tools/mapas/aglomerados_fase1.py [--alvo 0.30] [--semente 7]
"""
import argparse, math, random, re, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ARQ = RAIZ / "godot/data2d/rooms/fase_1.txt"
CSV = RAIZ / "godot/data2d/props_2d.csv"
GERADOS = RAIZ / "tools/mapas/fase_1.gerados.txt"  # cópia das linhas geradas, para a próxima rodada substituí-las

MODELOS = {  # nome: (peso, [(id, dx, dy), ...]) em células
    "moitas": (3, [("bush_dry_tangled", 0, 0), ("bush_dry_wide", 1.3, 0.4), ("bush_thorny", -1.1, 0.6),
                   ("grass_dry_tall", 0.5, 1.1), ("ferns_withered", -0.4, -0.8), ("flowers_dead", 1.6, 1.2)]),
    "pedras": (2, [("rock_large", 0, 0), ("rock_cluster", 1.4, 0.5), ("rock_rubble", -1.1, 0.7),
                   ("rock_crystal", 0.6, 1.2), ("grass_dry_tall", -0.9, -0.5), ("thistles_dry", 1.5, 1.3)]),
    "tronco": (2, [("log_fallen", 0, 0), ("leaves_pile", 0.9, 0.7), ("skull_single", -1.0, 0.5),
                   ("bush_dry_round", 1.5, -0.4), ("grass_dry_patch", -0.3, 1.0), ("branches_fallen", -1.4, -0.3)]),
    "cemiterio": (1.5, [("grave_round", 0, 0), ("grave_slab", 1.3, 0.3), ("grave_broken", -1.2, 0.6),
                        ("tomb_flowers", 0.4, 1.1), ("skull_single", 1.6, 1.2), ("grass_dry_patch", -0.6, 1.3),
                        ("flowers_dead", 1.0, -0.6)]),
    "ruina": (1, [("pillar_fallen", 0, 0), ("pillar_broken", 1.4, -0.6), ("rock_rubble", -1.0, 0.6),
                  ("vines_dry_rock", 0.8, 1.1), ("leaves_scattered", -0.4, 1.2), ("skull_pile", 1.7, 0.8)]),
    "ossuario": (1, [("skull_pile", 0, 0), ("bones_scattered", 1.0, 0.5), ("skeleton_hand", -0.9, 0.6),
                     ("skull_pair", 0.4, 1.1), ("ribcage_arch", -1.2, -0.6), ("grass_dry_patch", 1.3, 1.2)]),
    "arvoredo": (2, [("tree_dry_small", 0, 0), ("sapling_dead", 1.2, 0.5), ("shrub_dry_tall", -1.0, 0.7),
                     ("leaves_pile", 0.4, 1.2), ("roots_clump", -0.3, -0.9)]),
}


def spline(pts, passo=0.5):
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, len(pts) - 1)]
        n = max(int(math.dist(p1, p2) / passo), 2)
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    out.append(pts[-1])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alvo", type=float, default=0.30)
    ap.add_argument("--semente", type=int, default=7)
    a = ap.parse_args()
    rng = random.Random(a.semente)
    ids_ok = {l.split(",")[0] for l in CSV.read_text().splitlines()[1:] if l.strip()}
    solidos = {l.split(",")[0] for l in CSV.read_text().splitlines()[1:] if l.strip() and float(l.split(",")[2]) > 0}
    for m in MODELOS.values():
        for pid, _, _ in m[1]:
            assert pid in ids_ok, pid

    linhas = ARQ.read_text(encoding="utf-8").split("\n")
    grade = []
    i = 0
    while i < len(linhas) and not linhas[i].startswith("@"):
        if linhas[i].strip():
            grade.append(linhas[i])
        i += 1
    H, W = len(grade), len(grade[0])
    cab = []
    while i < len(linhas) and linhas[i] != "@props":
        cab.append(linhas[i]); i += 1
    props = [l for l in linhas[i + 1:] if l.strip()]
    if GERADOS.exists():
        antigos = set(GERADOS.read_text(encoding="utf-8").split("\n"))
        props = [l for l in props if l not in antigos]
    base = len(props)

    # obstáculos em células: trilhas, riachos, marcadores, mata, props existentes
    bloqueio = []  # (x, y, raio)
    for l in cab:
        if l.startswith("@caminho") or l.startswith("@riacho"):
            partes = l.split()
            larg = float(partes[1])
            pts = [tuple(float(v) for v in p.split(",")) for p in partes[2:]]
            r = larg * 0.5 + (2.6 if l.startswith("@riacho") else 1.6)
            for p in spline(pts):
                bloqueio.append((p[0], p[1], r))
    for y in range(H):
        for x in range(W):
            if grade[y][x] in "PEXGDBO":
                bloqueio.append((x + 0.5, y + 0.5, 4.0))
    RASOS = ("leaves_", "bones_", "skeleton_", "skull_single", "skull_pair", "skull_teal", "branches_", "flowers_",
             "grass_", "roots_", "ferns_", "reeds_", "thistles_")
    existentes = []   # todos os props: distância mínima de cada peça nova
    marcantes = []    # só os que chamam atenção (árvore, pedra, tumba, arbusto): definem o que é "vazio"
    for l in props:
        p = l.split()
        xy = (float(p[1]) + 0.5, float(p[2]) + 0.5)
        existentes.append(xy)
        if not p[0].startswith(RASOS):
            marcantes.append(xy)

    def livre(x, y, raio_props=2.0, lista=None):
        lista = existentes if lista is None else lista
        if not (1 <= x < W - 1 and 1 <= y < H - 1):
            return False
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if grade[int(y) + dy][int(x) + dx] != ".":
                    return False
        for bx, by, r in bloqueio:
            if (bx - x) ** 2 + (by - y) ** 2 < r * r:
                return False
        for ex, ey in lista:
            if (ex - x) ** 2 + (ey - y) ** 2 < raio_props * raio_props:
                return False
        return True

    nomes = list(MODELOS)
    pesos = [MODELOS[n][0] for n in nomes]
    novos = []
    alvo = int(base * a.alvo)
    tentativas = 0
    while len(novos) < alvo and tentativas < 200000:
        tentativas += 1
        cx = rng.uniform(2, W - 2); cy = rng.uniform(2, H - 2)
        if not livre(cx, cy, 3.5, marcantes) or not livre(cx, cy, 1.2):  # centro só em vazio de verdade
            continue
        modelo = MODELOS[rng.choices(nomes, pesos)[0]][1]
        ang = rng.uniform(0, math.tau)
        esp = rng.uniform(0.9, 1.25)
        grupo = []
        for pid, dx, dy in modelo:
            rx = (dx * math.cos(ang) - dy * math.sin(ang)) * esp + rng.uniform(-0.2, 0.2)
            ry = (dx * math.sin(ang) + dy * math.cos(ang)) * esp * 0.8 + rng.uniform(-0.15, 0.15)
            x, y = cx + rx, cy + ry
            if not livre(x, y, 1.0 if pid in solidos else 0.6):
                continue
            grupo.append((pid, x, y, rng.random() < 0.5))
        for pid, x, y, _ in grupo:
            if not pid.startswith(RASOS):
                marcantes.append((x, y))
        if len(grupo) < 3:
            continue
        for pid, x, y, flip in grupo:
            existentes.append((x, y))
            novos.append(f"{pid} {x - 0.5:.1f} {y - 0.5:.1f}" + (" flip" if flip else ""))
    novos.sort(key=lambda l: float(l.split()[2]))
    saida = linhas[:i + 1] + props + novos + [""]
    ARQ.write_text("\n".join(saida), encoding="utf-8")
    GERADOS.write_text("\n".join(novos) + "\n", encoding="utf-8")
    print(f"props antes {base}, gerados {len(novos)} (alvo {alvo}), total {base + len(novos)}, tentativas {tentativas}")


if __name__ == "__main__":
    main()
