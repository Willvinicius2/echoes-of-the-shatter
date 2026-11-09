#!/usr/bin/env python3
"""Troca as 4 variantes do piso comum (células 0..3) e o piso escuro (célula 6) do atlas da cripta
pelas lajes geradas no PixelLab (art-src/pixellab/cenario, 32x32 ampliadas 2x para a célula de 64)."""
import os
from PIL import Image, ImageEnhance, ImageOps
R = os.path.join(os.path.dirname(__file__), "..", "..")
atlas_p = os.path.join(R, "godot", "art2d", "tiles", "cripta_tiles.png")
a = Image.open(os.path.join(R, "art-src", "pixellab", "cenario", "wang_0.png")).convert("RGBA")
b = Image.open(os.path.join(R, "art-src", "pixellab", "cenario", "wang_15.png")).convert("RGBA")
def tint(im):
    """Teal do PixelLab -> cinza-arroxeado frio do atlas das paredes (mapeia luminância)."""
    g = ImageOps.grayscale(im.convert("RGB"))
    lo, hi = g.getextrema()
    mapa = ImageOps.colorize(ImageOps.autocontrast(g), (26, 24, 36), (128, 122, 138), mid=(70, 66, 80))
    mapa.putalpha(im.getchannel("A"))
    return mapa
def lisa(b, a):
    """b sem o glifo: troca a laje inferior direita (onde ele fica) pela da laje a, que é lisa; as emendas continuam."""
    c = b.copy()
    c.paste(a.crop((17, 18, 31, 31)), (17, 18))
    return c
up = lambda im: tint(im).resize((64, 64), Image.NEAREST)
var = [up(a), up(b), ImageOps.mirror(up(lisa(b, a))), ImageOps.flip(up(a))]  # só 1 de 4 lajes leva glifo
escuro = ImageEnhance.Brightness(up(a)).enhance(0.55)
A = Image.open(atlas_p).convert("RGBA")
for i, t in enumerate(var):
    A.paste(t, (i * 64, 0))
A.paste(escuro, (6 * 64, 0))
A.save(atlas_p)
