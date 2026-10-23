"""Arco v3: monta a prancha (entrada, frente, 3/4, costas, close, wireframe, tris). Uso: python arco_v3_compor.py <pasta_renders> <saida.png> <tris_haste> <tris_corda>"""
import sys, os
from PIL import Image, ImageDraw
r, out, th, tc = sys.argv[1:5]
ARCO = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark"
ent = Image.open(os.path.join(ARCO, "entradas", "arq3d_arco.png")).convert("RGB").crop((480, 0, 1056, 1024))
items = [("entrada", ent)] + [(n, Image.open(os.path.join(r, f + ".png")).convert("RGB")) for n, f in
         (("frente", "frente"), ("3/4", "tq"), ("costas", "costas"), ("close da ponta", "close"), (f"wireframe: haste+laminas {th} tris, corda {tc} tris", "wire"))]
h = 1000; tiles = [(n, i.resize((int(i.width * h / i.height), h), Image.LANCZOS)) for n, i in items]
W = sum(t.width for _, t in tiles) + 10 * (len(tiles) + 1)
S = Image.new("RGB", (W, h + 50), (38, 38, 40)); d = ImageDraw.Draw(S); x = 10
for n, t in tiles:
    S.paste(t, (x, 40)); d.text((x + 4, 14), n, fill=(235, 235, 235)); x += t.width + 10
S.save(out); print(S.size)
