"""Monta prancha_aljava_v4.png. uso: python aljava_v4_prancha.py <prev_dir> <entrada.png> <godot_lado.png> <out.png> <body> <arrows> <strap> <emblem> <pendant>"""
import sys
from PIL import Image, ImageDraw
prev, entrada, gd, out = sys.argv[1:5]; tb, ta, ts, te, tp = [int(x) for x in sys.argv[5:10]]
PW, PH = 480, 640; BG = (208, 208, 208)
def fit(im, box=None):
    im = im.convert("RGB")
    if box: im = im.crop(box)
    im.thumbnail((PW, PH), Image.LANCZOS); c = Image.new("RGB", (PW, PH), BG); c.paste(im, ((PW - im.width) // 2, (PH - im.height) // 2)); return c
ent = Image.open(entrada).convert("RGBA"); bg = Image.new("RGBA", ent.size, BG + (255,)); bg.alpha_composite(ent)
full = (100, 0, 900, 1000)
def sq(n, box=None): return fit(Image.open(prev + "/q_" + n + ".png"), box)
g = Image.open(gd)
panels = [("entrada (referencia)", fit(bg, (500, 0, 1036, 1024))), ("frente", sq("frente", full)), ("3/4 (lado da alca)", sq("3-4", full)),
          ("costas", sq("costas", full)), ("Godot (captura, vista de lado)", fit(g.crop((700, 130, 940, 370)).resize((480, 480), Image.LANCZOS))),
          ("close: flechas", sq("close1")), ("close: cinta, alca e emblema", sq("close2")), ("close: boca concava", sq("close3")), ("wireframe", sq("wire", full))]
info = Image.new("RGB", (PW, PH), (40, 40, 40)); d = ImageDraw.Draw(info)
tot = tb + ta + ts + te + tp
lines = ["tris (medidos, GLB)", "", f"Body (torno+cintas) {tb}", f"Arrows (9)          {ta}", f"Strap + fivelas     {ts}", f"Emblem              {te}", f"Pendant             {tp}", "", f"TOTAL               {tot}  (<= 4500)", "",
         "corpo: torno fechado, UV unica,", "cor+normal assados em 2048", "(sem emenda de casca)", "alca larga 3,5 cm, argolas e placas", "penas: 3 cartoes curvos (MASK)"]
for i, l in enumerate(lines): d.text((24, 36 + i * 24), l, fill=(235, 235, 235))
panels.append(("tris", info))
sheet = Image.new("RGB", (PW * 5, (PH + 24) * 2), (30, 30, 30)); d = ImageDraw.Draw(sheet)
for i, (name, im) in enumerate(panels):
    x, y = (i % 5) * PW, (i // 5) * (PH + 24); sheet.paste(im, (x, y + 24)); d.text((x + 8, y + 6), name, fill=(235, 235, 235))
sheet.save(out); print(sheet.size)
