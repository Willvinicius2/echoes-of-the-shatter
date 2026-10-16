"""Prancha JPG das previas (Python comum com Pillow). Uso: python make_sheet.py <pasta blender> [clip ...]
Sem clips: todas as pastas de previas/ em uma prancha unica (_prancha.jpg); com clips: um quadro por clip (_rev.jpg)."""
import sys, os, glob
from PIL import Image, ImageDraw
root = sys.argv[1]
names = sys.argv[2:] or sorted(os.listdir(os.path.join(root, "previas")))
rows = []
for n in names:
    fs = sorted(glob.glob(os.path.join(root, "previas", n, "*.png")))
    if fs:
        rows.append((n, fs))
cw = 340 if not sys.argv[2:] else 512
maxc = max(len(f) for _, f in rows)
lab = 22
sheet = Image.new("RGB", (cw * maxc, (cw + lab) * len(rows)), (24, 20, 30))
d = ImageDraw.Draw(sheet)
for r, (n, fs) in enumerate(rows):
    d.text((6, r * (cw + lab) + 4), n, fill=(240, 230, 200))
    for c, f in enumerate(fs):
        im = Image.open(f).convert("RGB").resize((cw, cw), Image.LANCZOS)
        sheet.paste(im, (c * cw, r * (cw + lab) + lab))
        d.text((c * cw + 6, r * (cw + lab) + lab + 4), os.path.basename(f)[-8:-4], fill=(200, 200, 200))
out = os.path.join(root, "_prancha.jpg" if not sys.argv[2:] else "_rev.jpg")
sheet.save(out, quality=88)
print(out, sheet.size)
