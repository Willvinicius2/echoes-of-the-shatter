#!/usr/bin/env python3
"""Monta as folhas do arqueiro a partir dos quadros gerados no PixelLab (art-src/pixellab/arqueiro).

Quadro 92x92, pivô (46,76). Linhas = S, SE, E, NE, N; colunas = quadros.
idle, hit, dodge são derivados dos quadros gerados; walk, attack e death vêm do PixelLab.
"""
import glob, os, sys
from PIL import Image

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
SRC = os.path.join(RAIZ, "art-src", "pixellab", "arqueiro")
OUT = os.path.join(RAIZ, "godot", "art2d", "sprites", "arqueiro")
DIRS = ["south", "south-east", "east", "north-east", "north"]
Q = 92
PAD = (Q - 64) // 2
DX = {"south": 0, "south-east": 1, "east": 1, "north-east": 1, "north": 0}


def centro(im):
    if im.size == (Q, Q):
        return im
    c = Image.new("RGBA", (Q, Q), (0, 0, 0, 0))
    c.alpha_composite(im, ((Q - im.width) // 2, (Q - im.height) // 2))
    return c


def anim(nome, d):
    fs = sorted(glob.glob(os.path.join(SRC, "animations", nome, d, "*.png")))
    return [centro(Image.open(f).convert("RGBA")) for f in fs]


def rot(d):
    return centro(Image.open(os.path.join(SRC, "rotations", d + ".png")).convert("RGBA"))


def deslocar(im, dx, dy):
    o = Image.new("RGBA", im.size, (0, 0, 0, 0))
    o.alpha_composite(im, (dx, dy))
    return o


def flash(im, k):
    px = im.copy()
    a = px.getchannel("A")
    br = Image.new("RGBA", im.size, (255, 255, 255, 255))
    return Image.composite(Image.blend(im, br, k), im, a)


def salvar(nome, linhas):
    n = len(linhas[0])
    S = Image.new("RGBA", (Q * n, Q * 5), (0, 0, 0, 0))
    for r, row in enumerate(linhas):
        for c, im in enumerate(row):
            S.alpha_composite(im, (c * Q, r * Q))
    os.makedirs(OUT, exist_ok=True)
    S.save(os.path.join(OUT, f"arqueiro_{nome}.png"))
    print(nome, n, "quadros")


def main():
    salvar("run", [anim("walking", d) for d in DIRS])
    salvar("attack", [anim("attack", d) for d in DIRS])
    salvar("idle", [[deslocar(rot(d), 0, o) for o in (0, 0, 0, 1, 1, 0)] for d in DIRS])
    salvar("hit", [[flash(deslocar(rot(d), -DX[d] * s, 0), k) for s, k in ((1, 0.8), (2, 0.4), (1, 0.0))] for d in DIRS])
    dod = []
    for d in DIRS:
        w = anim("walking", d)
        dod.append([deslocar(w[i % len(w)], 0, 2 if i in (1, 2, 3, 4) else 0) for i in range(6)])
    salvar("dodge", dod)
    if glob.glob(os.path.join(SRC, "animations", "falling_backward", "south", "*.png")):
        salvar("death", [anim("falling_backward", d) for d in DIRS])


if __name__ == "__main__":
    main()
