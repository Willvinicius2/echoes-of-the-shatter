"""Refino v2 da arte de Raio (pedido da revisora): raio_arco mais grosso com nós de brilho, choque_overlay só de faíscas
e arcos (sem silhueta) e ícone do tornado puxado para o azul. Uso: python3 refino_v2.py <raiz_do_repo>"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
R = sys.argv[1]
FX = os.path.join(R, "godot/art2d/fx/raio"); UI = os.path.join(R, "godot/art2d/ui")
NUC = (245, 252, 255, 255); AZ = (70, 130, 255, 255); CON = (15, 22, 80, 255)

def bolt(p0, p1, rnd, seg, desv):
    (x0, y0), (x1, y1) = p0, p1; dx, dy = x1 - x0, y1 - y0; d = math.hypot(dx, dy) or 1
    nx, ny = -dy / d, dx / d; pts = [p0]
    for i in range(1, seg):
        t = i / seg; o = rnd.uniform(-desv, desv) * math.sin(math.pi * t) ** .5
        pts.append((x0 + dx * t + nx * o, y0 + dy * t + ny * o))
    return pts + [p1]

def traco(im, pts, w):
    d = ImageDraw.Draw(im)
    for l, c in ((w + 5, CON), (w + 3, AZ), (max(1, w * .55), NUC)):
        d.line(pts, fill=c, width=int(round(l)), joint="curve")

def no(im, p, r):
    d = ImageDraw.Draw(im)
    d.ellipse([p[0] - r - 2, p[1] - r - 2, p[0] + r + 2, p[1] + r + 2], fill=AZ)
    d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=NUC)

def brilho(im, r):
    return Image.alpha_composite(im.filter(ImageFilter.GaussianBlur(r)), im)

def folha(qs, nome):
    w, h = qs[0].size; f = Image.new("RGBA", (w * len(qs), h), (0, 0, 0, 0))
    for i, q in enumerate(qs): f.paste(q, (i * w, 0))
    f.save(os.path.join(FX, nome))

# raio_arco 4x 128x32: traço grosso, nós nas pontas e nas ramificações
qs = []
for k in range(4):
    rnd = random.Random(900 + k); im = Image.new("RGBA", (128, 32), (0, 0, 0, 0))
    pts = bolt((8, 16), (120, 16), rnd, 10, 7); traco(im, pts, 4)
    for _ in range(3):
        i = rnd.randrange(2, len(pts) - 2); a = pts[i]; s = rnd.choice((-1, 1))
        b = (a[0] + rnd.uniform(8, 14), a[1] + s * rnd.uniform(7, 11)); traco(im, [a, b], 2); no(im, b, 2)
    no(im, (8, 16), 4); no(im, (120, 16), 4)
    qs.append(brilho(im, 3))
folha(qs, "raio_arco.png")

# choque_overlay 6x 64x64: arcos e faíscas em volta de qualquer corpo (sem silhueta)
qs = []
for k in range(6):
    rnd = random.Random(950 + k); im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    for j in range(4):
        a = (j / 4 + k * 0.07) * math.tau + rnd.uniform(-.3, .3)
        p0 = (32 + 20 * math.cos(a), 32 + 20 * math.sin(a)); a2 = a + rnd.uniform(.5, .9)
        p1 = (32 + 24 * math.cos(a2), 32 + 24 * math.sin(a2))
        traco(im, bolt(p0, p1, rnd, 4, 4), 2)
        if rnd.random() < .7: no(im, p1, 2)
    for _ in range(5):
        a = rnd.uniform(0, math.tau); r = rnd.uniform(14, 28); no(im, (32 + r * math.cos(a), 32 + r * math.sin(a)), 1)
    qs.append(brilho(im, 2))
folha(qs, "choque_overlay.png")

# ícone do tornado: roxo -> azul (gira o matiz só onde está roxo/violeta, mantém a moldura)
p = os.path.join(UI, "icone_storm_tornado.png")
im = Image.open(p).convert("RGBA"); hsv = np.array(im.convert("RGB").convert("HSV")).astype(int)
h, s = hsv[..., 0], hsv[..., 1]
roxo = (h > 170) & (h < 225) & (s > 40)      # 0-255: roxo/violeta/magenta
hsv[..., 0] = np.where(roxo, np.clip(h - 42, 0, 255), h)  # (2 passadas: -28 e -14)
hsv[..., 1] = np.where(roxo, np.clip(s + 25, 0, 255), s)
out = Image.fromarray(hsv.astype("uint8"), "HSV").convert("RGB").convert("RGBA"); out.putalpha(im.getchannel("A"))
out.save(p)
