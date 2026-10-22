"""Monta UMA prancha com os 4 ângulos, o close e o wireframe do piso. python3 piso_prancha.py <previas/piso> <saida.png>"""
import sys, os
from PIL import Image, ImageDraw
d, out = sys.argv[1], sys.argv[2]
itens = [("3/4 (jogo)", "piso_jogo"), ("Frente", "piso_frente"), ("Lado", "piso_lado"), ("Cima", "piso_cima"), ("Close", "piso_close"), ("Wireframe", "piso_wireframe")]
W, H = 800, 540
img = Image.new("RGB", (W * 3, H * 2), (12, 14, 20)); dr = ImageDraw.Draw(img)
for i, (t, n) in enumerate(itens):
    im = Image.open(os.path.join(d, n + ".png")).convert("RGB"); im.thumbnail((W, H))
    x, y = (i % 3) * W + (W - im.width) // 2, (i // 3) * H + (H - im.height) // 2
    img.paste(im, (x, y)); dr.text(((i % 3) * W + 10, (i // 3) * H + 8), t, fill=(240, 220, 160))
img.save(out)
