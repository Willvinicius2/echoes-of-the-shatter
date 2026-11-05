#!/usr/bin/env python3
"""Cena de teste: arqueiro (folha run) andando sobre o piso novo, braseiro ao lado. Escala de mundo 2,5. Saída: PNG."""
import sys, os
from PIL import Image
R = os.path.join(os.path.dirname(__file__), "..", "..")
G = os.path.join(R, "godot", "art2d")
out = sys.argv[1]
atlas = Image.open(os.path.join(G, "tiles", "cripta_tiles.png")).convert("RGBA")
W, H = 960, 400
cena = Image.new("RGBA", (W, H))
for y in range(0, H, 64):
    for x in range(0, W, 64):
        cena.alpha_composite(atlas.crop((((x // 64 + y // 64) % 4) * 64, 0, ((x // 64 + y // 64) % 4) * 64 + 64, 64)), (x, y))
Q = 92
sh = Image.open(os.path.join(G, "sprites", "arqueiro", "arqueiro_run.png")).convert("RGBA")
for i, d in enumerate([0, 1, 2, 3, 4]):
    f = sh.crop((((i) % 6) * Q, d * Q, ((i) % 6) * Q + Q, d * Q + Q))
    f = f.resize((int(Q * 2.5), int(Q * 2.5)), Image.NEAREST)
    cena.alpha_composite(f, (60 + i * 140 - 115, 120))
b = Image.open(os.path.join(G, "pixellab", "braseiro_pedra_48x64.png")).convert("RGBA")
b = b.resize((int(48 * 2.5), int(64 * 2.5)), Image.NEAREST)
cena.alpha_composite(b, (780, 140))
cena.save(out)
