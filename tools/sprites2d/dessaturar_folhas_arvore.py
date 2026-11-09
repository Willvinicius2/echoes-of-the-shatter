#!/usr/bin/env python3
"""Tira um tom da saturação do ciano da árvore `tree_teal_leaves` (godot/art2d/props/), que se repete 48 vezes no mapa
da área 1 e dominava a floresta. Pedido da revisão de arte: menos saturação, mesmo valor (o V do HSV não muda) e sem
acinzentar; a copa mantém 3 folhas com o ciano vivo como acento (uma no alto, uma à esquerda, uma à direita).

Só mexe nas cores da família ciano (matiz 172° a 202°, saturação > 0,25): o tronco roxo-acinzentado, as pedras e o
contorno ficam como estão. Fator de saturação padrão 0,75.

Uso: python3 -I tools/sprites2d/dessaturar_folhas_arvore.py [--fator 0.75] [--forcar] [--saida ARQUIVO]
O PNG de origem é conferido por hash: aplicar duas vezes tiraria dois tons, então com o arquivo já ajustado o script
recusa, a não ser com --forcar. Só precisa de PIL e numpy; nada de IA generativa.
"""
import colorsys
import hashlib
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
ARQUIVO = os.path.join(R, "godot", "art2d", "props", "tree_teal_leaves.png")
SHA_ORIGINAL = "7fbf1601e69872da1363d5b7328270d92c2910764358821feb8573637735e635"
FATOR_PADRAO = 0.75

# as três cores das folhas e das veias do tronco (corpo, sombra e luz); o resto do ciano é tom escuro do tronco
CIANOS_VIVOS = {(33, 229, 234), (25, 175, 188), (148, 217, 218)}
# folhas que ficam com o ciano vivo (acento): um ponto dentro de cada uma, em px do sprite (102x121)
ACENTOS = [(72, 4), (15, 55), (94, 73)]


def componentes(mascara):
    """Componentes 8-conexos da máscara: lista de listas de (y, x)."""
    h, w = mascara.shape
    visto = np.zeros((h, w), bool)
    saida = []
    for y in range(h):
        for x in range(w):
            if mascara[y, x] and not visto[y, x]:
                fila = deque([(y, x)])
                visto[y, x] = True
                pts = []
                while fila:
                    cy, cx = fila.popleft()
                    pts.append((cy, cx))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and mascara[ny, nx] and not visto[ny, nx]:
                                visto[ny, nx] = True
                                fila.append((ny, nx))
                saida.append(pts)
    return saida


def main():
    args = sys.argv[1:]
    fator = float(args[args.index("--fator") + 1]) if "--fator" in args else FATOR_PADRAO
    saida = args[args.index("--saida") + 1] if "--saida" in args else ARQUIVO
    sha = hashlib.sha256(open(ARQUIVO, "rb").read()).hexdigest()
    if sha != SHA_ORIGINAL and "--forcar" not in args:
        raise SystemExit("%s não é mais o arquivo original (já ajustado?): use --forcar para aplicar de novo" % ARQUIVO)
    a = np.asarray(Image.open(ARQUIVO).convert("RGBA")).copy()
    h, w = a.shape[:2]
    vivos = np.zeros((h, w), bool)
    for y in range(h):
        for x in range(w):
            if a[y, x, 3] and tuple(int(v) for v in a[y, x, :3]) in CIANOS_VIVOS:
                vivos[y, x] = True
    comps = componentes(vivos)
    manter = np.zeros((h, w), bool)
    for sx, sy in ACENTOS:   # a folha de acento é a componente cujo centro fica mais perto do ponto dado
        melhor = min(comps, key=lambda pts: (sum(p[1] for p in pts) / len(pts) - sx) ** 2 + (sum(p[0] for p in pts) / len(pts) - sy) ** 2)
        for y, x in melhor:
            manter[y, x] = True
    mudou = 0
    for y in range(h):
        for x in range(w):
            if not a[y, x, 3] or manter[y, x]:
                continue
            r, g, b = [int(v) / 255 for v in a[y, x, :3]]
            matiz, sat, val = colorsys.rgb_to_hsv(r, g, b)
            if 0.48 < matiz < 0.56 and sat > 0.25:
                nr, ng, nb = colorsys.hsv_to_rgb(matiz, sat * fator, val)
                novo = [round(nr * 255), round(ng * 255), round(nb * 255)]
                if novo != list(a[y, x, :3]):
                    mudou += 1
                a[y, x, :3] = novo
    Image.fromarray(a, "RGBA").save(saida)
    print("%s: %d pixels com o ciano ajustado (fator %.2f), %d de acento intocados" % (os.path.basename(saida), mudou, fator, int(manter.sum())))


if __name__ == "__main__":
    main()
