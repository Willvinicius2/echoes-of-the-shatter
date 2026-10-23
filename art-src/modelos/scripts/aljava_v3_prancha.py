"""Monta prancha_aljava_v3.png. uso: python aljava_v3_prancha.py <prev_dir> <entrada.png> <out.png> <body> <arrows> <strap> <emblem> <pendant>"""
import sys
from PIL import Image, ImageDraw
prev, entrada, out = sys.argv[1:4]; tb, ta, ts, te, tp = [int(x) for x in sys.argv[4:9]]
PW, PH = 600, 780; BG = (208, 208, 208)
def fit(im, box=None):
    im = im.convert("RGB")
    if box: im = im.crop(box)
    im.thumbnail((PW, PH)); c = Image.new("RGB", (PW, PH), BG); c.paste(im, ((PW - im.width) // 2, (PH - im.height) // 2)); return c
ent = Image.open(entrada).convert("RGBA"); bg = Image.new("RGBA", ent.size, BG + (255,)); bg.alpha_composite(ent)
full = (100, 0, 900, 1000)
def sq(n, box=None): return fit(Image.open(prev + "/q_" + n + ".png"), box)
panels = [("entrada (referencia)", fit(bg, (500, 0, 1036, 1024))), ("frente", sq("frente", full)), ("3/4 (lado da alca)", sq("3-4", full)),
          ("costas", sq("costas", full)), ("close: flechas", sq("close1")), ("close: boca, alca e emblema", sq("close2")),
          ("wireframe", sq("wire", full))]
info = Image.new("RGB", (PW, PH), (40, 40, 40)); d = ImageDraw.Draw(info)
tot = tb + ta + ts + te + tp
lines = ["tris (medidos, GLB)", "", f"Body (TripoSG+boca)  {tb}", f"Arrows (9)           {ta}", f"Strap + fivelas      {ts}", f"Emblem               {te}", f"Pendant              {tp}", "", f"TOTAL                {tot}  (<= 4500)", "", "penas: 3 cartoes curvos por flecha", "alca: curva 3D com bevel e costura",
         "normal do corpo: bake do high.ply", "texturas: corpo 2048+N, penas 1024,", "alca 512+N, metal 512"]
for i, l in enumerate(lines): d.text((30, 40 + i * 26), l, fill=(235, 235, 235))
panels.append(("tris", info))
sheet = Image.new("RGB", (PW * 4, (PH + 26) * 2), (30, 30, 30)); d = ImageDraw.Draw(sheet)
for i, (name, im) in enumerate(panels):
    x, y = (i % 4) * PW, (i // 4) * (PH + 26); sheet.paste(im, (x, y + 26)); d.text((x + 8, y + 7), name, fill=(235, 235, 235))
sheet.save(out); print(sheet.size)
