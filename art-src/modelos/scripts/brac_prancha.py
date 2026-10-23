"""Prancha unica das bracadeiras do arqueiro dark: entrada, frente, 3/4, costas, close, wireframe, tris/verificacao, montado no corpo e captura do Godot.
Uso: python brac_prancha.py <pasta work> <pasta final> <captura_godot.png> <entrada.png> <saida.png>"""
import sys, json
from PIL import Image, ImageDraw, ImageFont
work, final, godot, entrada, out = sys.argv[1:6]
T = 640
rep = json.load(open(f"{final}/verify_report.json"))


def fit(im, size=T, bg=(176, 180, 190)):
    im = im.convert("RGB"); im.thumbnail((size, size), Image.LANCZOS)
    c = Image.new("RGB", (size, size), bg); c.paste(im, ((size - im.width) // 2, (size - im.height) // 2)); return c


def crop_center(p, box=None, size=T):
    im = Image.open(p).convert("RGB")
    if box: im = im.crop(box)
    return fit(im, size)


try:
    F = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 22); FB = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
except Exception:
    F = FB = ImageFont.load_default()
tiles = [
    ("entrada (arq3d_bracadeiras)", fit(Image.open(entrada), T, (200, 200, 200))),
    ("frente", crop_center(f"{work}/s_front.png")),
    ("3/4", crop_center(f"{work}/s_q34.png")),
    ("costas", crop_center(f"{work}/s_back.png")),
    ("close (luva e cintas)", crop_center(f"{work}/s_close.png")),
    ("wireframe", crop_center(f"{work}/s_wire_close.png")),
    ("montado no corpo", crop_center(f"{work}/s_body34.png", (180, 0, 720, 900))),
    ("captura do Godot (mirando)", crop_center(godot, (0, 0, 1024, 1024))),
]
W = 3 * T; H = 3 * T + 70
img = Image.new("RGB", (W, H), (24, 22, 28)); d = ImageDraw.Draw(img)
d.text((20, 18), "Arqueiro Dark - bracadeiras e luvas (SK_ArcherDark_Bracers)", font=FB, fill=(235, 225, 210))
for i, (cap, t) in enumerate(tiles):
    x, y = (i % 3) * T, 70 + (i // 3) * T
    img.paste(t, (x, y)); d.rectangle([x, y, x + T - 1, y + T - 1], outline=(60, 56, 66))
    d.rectangle([x, y, x + len(cap) * 12 + 16, y + 30], fill=(24, 22, 28)); d.text((x + 8, y + 2), cap, font=F, fill=(235, 225, 210))
x, y = 2 * T, 70 + 2 * T
img.paste(Image.new("RGB", (T, T), (34, 31, 38)), (x, y)); d.rectangle([x, y, x + T - 1, y + T - 1], outline=(60, 56, 66))
pz = rep["pose"]
lines = [("Triangulos e verificacao", FB),
         (f"total (par): {rep['tris']} tris  (teto 2000)", F), (f"por braco: {rep['tris'] // 2}", F),
         ("1 material, UV0 em [0,1], 2048 BC/N/MR", F), (f"esqueleto: {rep['bones_bracers']} ossos, ate {rep['skin']['max_influences']} influencias", F),
         (f"folga da pele em repouso: min {rep['rest_clearance_mm']['min']} mm, mediana {rep['rest_clearance_mm']['median']} mm", F),
         ("", F), ("esticamento de aresta (max) / folga min", FB)]
for k, v in pz.items():
    lines.append((f"{k}: x{v['edge_stretch_max']}  / {v['clearance_min_mm']} mm", F))
lines += [("", F), ("volume por script (medido no corpo); metais,", F), ("cintas e fivelas em geometria a parte", F)]
yy = y + 20
for txt, f in lines:
    d.text((x + 20, yy), txt, font=f, fill=(235, 225, 210)); yy += 32
img.save(out)
print("prancha", out, img.size)
