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


def arco_marrom(im):
    """O modelo pintou o arco de vermelho vivo em algumas direções: volta para o marrom do arco."""
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a and r > 170 and g < 110 and b < 90:
                px[x, y] = (int(r * 0.62), int(g * 1.25 + 30), int(b * 1.1 + 18), a)
    return im


def _claro(p):
    r, g, b, a = p
    return a > 0 and min(r, g, b) > 120 and max(r, g, b) - min(r, g, b) < 45


def sem_flecha(im):
    """A flecha sai como projétil no motor: apaga as manchas claras e finas (haste e ponta) do quadro."""
    px = im.load()
    w, h = im.size
    vis = set()
    for y in range(h):
        for x in range(w):
            if (x, y) in vis or not _claro(px[x, y]):
                continue
            comp, pil = [], [(x, y)]
            vis.add((x, y))
            while pil:
                cx, cy = pil.pop()
                comp.append((cx, cy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        n = (cx + dx, cy + dy)
                        if n not in vis and 0 <= n[0] < w and 0 <= n[1] < h and _claro(px[n[0], n[1]]):
                            vis.add(n)
                            pil.append(n)
            xs = [c[0] for c in comp]
            ys = [c[1] for c in comp]
            lw, lh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            if (lh <= 3 and lw >= 3) or (lw <= 2 and lh >= 6 and False):
                for cx, cy in comp:
                    px[cx, cy] = (0, 0, 0, 0)
    return im


def capa_verde(im):
    """Capa quase preta (S, ataque) -> rampa verde da capa: só pixels escuros e neutros fora do contorno."""
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a and abs(x - Q // 2) >= 12 and max(r, g, b) < 70 and abs(r - b) < 25:
                l = max(r, g, b)
                px[x, y] = (int(l * 0.9) + 8, int(l * 1.25) + 22, int(l * 1.15) + 20, a)
    return im


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
    salvar("attack", [[(capa_verde if d == "south" else (lambda i: i))(sem_flecha(arco_marrom(f))) for f in anim("attack2", d)] for d in DIRS])
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
