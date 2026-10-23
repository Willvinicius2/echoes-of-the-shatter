"""Monta a prancha unica do corpo-base: entrada, folha v2, frente, 3/4, costas, close do rosto, wireframe, triangulos.
Uso: python prancha_montar.py <saida.png> [tris] (le as previas em modelos3d/arqueiro_dark/corpo)."""
import sys
from PIL import Image, ImageDraw
B = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark"; C = B + r"\corpo"
out = sys.argv[1]; tris = sys.argv[2] if len(sys.argv) > 2 else "?"
ent = Image.open(B + r"\entradas\arq3d_corpo.png").convert("RGB").crop((480, 0, 1056, 1024))
v2 = Image.open(r"D:\openclaude\_trabalho-claude\arqueiro-dark\v2\arq_v2_vistas.png").convert("RGB")
pv = lambda n: Image.open(C + rf"\final\previews\SK_ArcherDark_Body_{n}.png").convert("RGB").crop((230, 0, 794, 1024))
pr = lambda n: Image.open(C + rf"\work\prancha\{n}.png").convert("RGB")
cells = [("entrada (arq3d_corpo)", ent), ("frente", pv("frente")), ("3/4", pv("3-4")), ("costas", pv("costas")),
         ("close do rosto", pr("rosto").crop((100, 60, 924, 884))), ("close 3/4", pr("rosto3q").crop((100, 60, 924, 884))),
         (f"wireframe frente ({tris} tris)", pr("wire_frente").crop((300, 0, 724, 1024))), ("wireframe 3/4", pr("wire_34").crop((300, 0, 724, 1024)))]
H = 700; cw = []
for t, im in cells:
    im = im.resize((int(im.width * H / im.height), H), Image.LANCZOS); cw.append((t, im))
row1 = cw[:4]; row2 = cw[4:]
W = max(sum(i.width for _, i in row1), sum(i.width for _, i in row2))
v2s = v2.resize((W, int(v2.height * W / v2.width)), Image.LANCZOS)
sheet = Image.new("RGB", (W, v2s.height + 2 * (H + 28)), (40, 40, 44)); d = ImageDraw.Draw(sheet)
sheet.paste(v2s, (0, 0)); d.text((8, 6), "folha v2 (referencia aprovada)", fill=(255, 255, 255))
y = v2s.height
for row in (row1, row2):
    x = 0
    for t, im in row:
        sheet.paste(im, (x, y + 28)); d.text((x + 8, y + 8), t, fill=(255, 255, 255)); x += im.width
    y += H + 28
sheet.save(out); print(sheet.size)
