#!/usr/bin/env python3
"""Troca a célula do braseiro (índice 15) do atlas da cripta pelo braseiro gerado no PixelLab
(godot/art2d/pixellab/braseiro_pedra_48x64.png). Fica em escala 1:1 (1 px da arte = 1 px de mundo, como o arqueiro),
centrado na célula de 64 com a base do pedestal a 4 px do fundo. O clima_2d.gd tira a chama pintada da tigela e
põe o fogo animado (clima.csv: tigela_borda 0.31 cai na borda da tigela desta arte)."""
import os
from PIL import Image
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
atlas_p = os.path.join(R, "godot", "art2d", "tiles", "cripta_tiles.png")
b = Image.open(os.path.join(R, "godot", "art2d", "pixellab", "braseiro_pedra_48x64.png")).convert("RGBA")
A = Image.open(atlas_p).convert("RGBA")
IDX, T = 15, 64
x0, y0 = (IDX % 8) * T, (IDX // 8) * T
# a chama pintada acima da borda (linhas 0..15) sai: o fogo animado a refaz; a arte cresce 25% (vizinho mais próximo)
b = b.crop((0, 16, 48, 64))
b = b.resize((60, 60), Image.NEAREST)
A.paste(Image.new("RGBA", (T, T), (0, 0, 0, 0)), (x0, y0))
bb = b.getbbox()
A.alpha_composite(b.crop(bb), (x0 + (T - (bb[2] - bb[0])) // 2, y0 + 63 - (bb[3] - bb[1])))
A.save(atlas_p)
print("braseiro aplicado na célula", IDX)
