"""Remove fragmentos de sprites vizinhos que vazaram para a borda das celulas das folhas 2D.

Em cada celula, apaga componentes de alfa que tocam a faixa de 12 px do topo ou da base da celula, estao soltos
do corpo principal e sao pequenos (< LIMITE do maior componente).
Uso: python tools/sprites2d/limpar_bordas.py [--aplicar] [pasta]
"""
import glob
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

LIMITE = 0.10
ALFA = 16
MARGEM = 12


def limpar(caminho, aplicar):
    im = np.array(Image.open(caminho).convert("RGBA"))
    cs = 256 if "crypt_guardian" in caminho else 128
    h, w = im.shape[:2]
    mudou = 0
    for r in range(h // cs):
        for c in range(w // cs):
            cel = im[r * cs:(r + 1) * cs, c * cs:(c + 1) * cs]
            a = cel[..., 3] > ALFA
            lab, k = ndi.label(a, structure=np.ones((3, 3)))
            if k < 2:
                continue
            tam = ndi.sum(a, lab, range(1, k + 1))
            maior = tam.max()
            for i in range(1, k + 1):
                m = lab == i
                ys, xs = np.nonzero(m)
                toca = ys.min() < MARGEM or ys.max() >= cs - MARGEM
                if toca and tam[i - 1] < LIMITE * maior:
                    cel[m] = 0
                    mudou += int(tam[i - 1])
    if mudou and aplicar:
        Image.fromarray(im).save(caminho)
    return mudou


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--aplicar"]
    aplicar = "--aplicar" in sys.argv
    base = args[0] if args else "godot/art2d/sprites"
    for f in sorted(glob.glob(base + "/*/*.png")):
        if "_death" in f or "ghost_archer" in f:
            continue  # restos de morte e a flecha espectral sao parte da animacao
        n = limpar(f, aplicar)
        if n:
            print(f, n, "px")
