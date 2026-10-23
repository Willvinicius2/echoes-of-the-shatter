"""Monta prancha_aljava_v2.png. uso: python aljava_v2_prancha.py <prev_dir> <entrada.png> <out.png> <tris_body> <arrows> <strap> <emblem>"""
import sys
from PIL import Image, ImageDraw
prev, entrada, out = sys.argv[1:4]; tb, ta, ts, te = [int(x) for x in sys.argv[4:8]]
PW, PH = 600, 780; BG = (208, 208, 208)
def fit(im, box=None):
    im = im.convert("RGB")
    if box: im = im.crop(box)
    im.thumbnail((PW, PH)); c = Image.new("RGB", (PW, PH), BG); c.paste(im, ((PW - im.width) // 2, (PH - im.height) // 2)); return c
ent = Image.open(entrada).convert("RGBA"); bg = Image.new("RGBA", ent.size, BG + (255,)); bg.alpha_composite(ent)
full = (230, 30, 810, 1000)
panels = [("entrada (referencia)", fit(bg)), ("frente", fit(Image.open(prev + "/q_frente.png"), full)), ("3/4", fit(Image.open(prev + "/q_3-4.png"), full)),
          ("costas", fit(Image.open(prev + "/q_costas.png"), full)), ("close: flechas", fit(Image.open(prev + "/q_close1.png"))),
          ("close: emblema e alca", fit(Image.open(prev + "/q_close2.png"))), ("wireframe", fit(Image.open(prev + "/q_wire.png"), full))]
info = Image.new("RGB", (PW, PH), (40, 40, 40)); d = ImageDraw.Draw(info)
lines = ["tris (medidos, GLB)", "", f"Body (TripoSG)   {tb}", f"Arrows (9)       {ta}", f"Strap + fivelas  {ts}", f"Emblem           {te}", "", f"TOTAL            {tb + ta + ts + te}", "", "texturas: corpo 2048 + normal,", "flechas 512 (alpha cutout),", "alca 512, emblema 512"]
for i, l in enumerate(lines): d.text((30, 40 + i * 28), l, fill=(235, 235, 235))
panels.append(("tris", info))
sheet = Image.new("RGB", (PW * 4, (PH + 26) * 2), (30, 30, 30)); d = ImageDraw.Draw(sheet)
for i, (name, im) in enumerate(panels):
    x, y = (i % 4) * PW, (i // 4) * (PH + 26); sheet.paste(im, (x, y + 26)); d.text((x + 8, y + 7), name, fill=(235, 235, 235))
sheet.save(out); print(sheet.size)
