"""Monta a prancha unica das botas: entrada, frente, 3/4, costas, lado, closes, wireframe, triangulos, montado no corpo e captura do Godot.
Uso: python -I botas_prancha.py <saida.png> <tris> <pasta_godot_capturas> (le as previas em modelos3d/arqueiro_dark/botas/work/prancha)."""
import sys
from PIL import Image, ImageDraw
B = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark"; P = B + r"\botas\work\prancha"
out, tris, gd = sys.argv[1], sys.argv[2], sys.argv[3]
ent = Image.open(B + r"\entradas\arq3d_botas.png").convert("RGB").crop((440, 0, 1110, 1024))
pr = lambda n: Image.open(P + rf"\{n}.png").convert("RGB")
gdi = lambda n, box: Image.open(gd + rf"\{n}.png").convert("RGB").crop(box)
H = 640
row1 = [("entrada (arq3d_botas)", ent), ("frente", pr("b_frente")), ("3/4", pr("b_3q")), ("costas", pr("b_costas")), ("lado", pr("b_lado"))]
row2 = [("close do cano", pr("c_cano")), ("close do pe", pr("c_pe")), (f"wireframe ({tris} tris, par)", pr("w_frente")), ("wireframe 3/4", pr("w_3q"))]
row3 = [("montado no corpo - frente", pr("m_frente")), ("montado - 3/4", pr("m_3q")), ("montado - costas", pr("m_costas")),
        ("Godot - frente (cena de teste)", gdi("godot_frente", (380, 480, 900, 900))), ("Godot - 3/4 perto", gdi("godot_3q_perto", (380, 480, 900, 900)))]
rows = [row1, row2, row3]
cells = [[(t, im.resize((int(im.width * H / im.height), H), Image.LANCZOS)) for t, im in r] for r in rows]
W = max(sum(i.width for _, i in r) for r in cells)
sheet = Image.new("RGB", (W, 3 * (H + 26) + 60), (40, 40, 44)); d = ImageDraw.Draw(sheet)
d.text((8, 6), f"SK_ArcherDark_Boots - par de botas, {tris} tris, 30 ossos, textura 2048 + normal; volume por script sobre a pele do corpo (+4,5 mm), metais/tiras/salto geometria a parte", fill=(255, 255, 255))
y = 30
for r in cells:
    x = 0
    for t, im in r:
        sheet.paste(im, (x, y + 22)); d.text((x + 8, y + 5), t, fill=(255, 255, 255)); x += im.width
    y += H + 26
sheet.save(out); print(sheet.size)
