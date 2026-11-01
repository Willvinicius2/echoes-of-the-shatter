"""Folhas provisórias dos efeitos da árvore de Raio (Arqueiro), desenhadas em código (PIL + numpy).
Servem para o jogo funcionar já; a arte pintada final vem do gpt-image (prompts_raio.json) e substitui os PNGs.
Uso: python3 gerar_procedural.py <pasta_saida>   (ex.: godot/art2d/fx/raio)
Folhas = quadros em linha, fundo transparente, luz do alto à esquerda, contorno escuro fino."""
import math, os, random, sys
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
NUCLEO = (245, 252, 255, 255)
BRILHO = (120, 200, 255)
AZUL = (60, 120, 230)
CONTORNO = (20, 28, 70, 255)

def camada(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))

def glow(img, raio, cor_mult=1.0):
    g = img.filter(ImageFilter.GaussianBlur(raio))
    return Image.alpha_composite(g, img) if cor_mult else img

def raio_pts(p0, p1, rnd, seg=8, desvio=10.0):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / d, dx / d
    pts = [p0]
    for i in range(1, seg):
        t = i / seg
        o = rnd.uniform(-desvio, desvio) * math.sin(math.pi * t) ** 0.5
        pts.append((x0 + dx * t + nx * o, y0 + dy * t + ny * o))
    pts.append(p1)
    return pts

def desenha_raio(img, pts, larg=3.0, ramos=None, rnd=None):
    # contorno escuro, brilho azul, núcleo branco: três passadas
    for l, cor in ((larg + 4, CONTORNO), (larg + 2, AZUL + (255,)), (larg * 0.6, NUCLEO)):
        ImageDraw.Draw(img).line(pts, fill=cor, width=max(1, int(round(l))), joint="curve")
    if ramos and rnd:
        for _ in range(ramos):
            i = rnd.randrange(1, len(pts) - 1)
            a = pts[i]
            ang = rnd.uniform(-1.0, 1.0)
            fim = (a[0] + 14 * math.cos(ang) + 6, a[1] + 14 * math.sin(ang))
            ImageDraw.Draw(img).line([a, fim], fill=NUCLEO, width=1)

def final(quadros, caminho):
    w, h = quadros[0].size
    folha = camada(w * len(quadros), h)
    for i, q in enumerate(quadros):
        folha.paste(q, (i * w, 0))
    folha.save(os.path.join(OUT, caminho))
    print(caminho, folha.size, len(quadros), "quadros")

def com_brilho(img, r=4):
    return Image.alpha_composite(img.filter(ImageFilter.GaussianBlur(r)), img)

# 1. projétil: cabeça virada para a direita, rastro faísca à esquerda (6 quadros, 64x32)
def proj():
    qs = []
    for k in range(6):
        rnd = random.Random(100 + k)
        im = camada(64, 32)
        d = ImageDraw.Draw(im)
        d.line([(8, 16), (50, 16)], fill=(120, 80, 50, 255), width=2)         # haste
        d.polygon([(50, 12), (60, 16), (50, 20)], fill=NUCLEO, outline=CONTORNO)  # ponta
        d.polygon([(8, 16), (3, 11), (3, 21)], fill=(200, 230, 255, 255))      # pena
        for _ in range(2):
            desenha_raio(im, raio_pts((6, 16), (48, 16 + rnd.uniform(-5, 5)), rnd, 6, 5), 1.5)
        qs.append(com_brilho(im, 3))
    return qs

# 2. impacto: estrela de raios que cresce e some (8 quadros, 96x96)
def impacto():
    qs = []
    for k in range(8):
        rnd = random.Random(200 + k)
        im = camada(96, 96)
        t = k / 7.0
        r = 10 + 34 * t
        for j in range(7):
            a = j / 7 * math.tau + rnd.uniform(-0.2, 0.2)
            desenha_raio(im, raio_pts((48, 48), (48 + r * math.cos(a), 48 + r * math.sin(a)), rnd, 5, 5), 2.0)
        d = ImageDraw.Draw(im)
        rr = 14 * (1 - t) + 2
        d.ellipse([48 - rr, 48 - rr, 48 + rr, 48 + rr], fill=NUCLEO)
        im = com_brilho(im, 5)
        a = im.getchannel("A").point(lambda v: int(v * (1.0 - 0.8 * max(0, t - 0.5) * 2 * 0.5)))
        im.putalpha(a)
        qs.append(im)
    return qs

# 3. arco de raio: segmento horizontal de ponta a ponta, esticado no jogo (4 quadros, 128x32)
def arco():
    qs = []
    for k in range(4):
        rnd = random.Random(300 + k)
        im = camada(128, 32)
        desenha_raio(im, raio_pts((2, 16), (126, 16), rnd, 12, 9), 3.0, ramos=4, rnd=rnd)
        qs.append(com_brilho(im, 3))
    return qs

# 4. overlay de choque no inimigo: faíscas em volta (6 quadros, 64x64)
def choque():
    qs = []
    for k in range(6):
        rnd = random.Random(400 + k)
        im = camada(64, 64)
        for _ in range(3):
            a = rnd.uniform(0, math.tau)
            p0 = (32 + 10 * math.cos(a), 36 + 10 * math.sin(a))
            p1 = (32 + 28 * math.cos(a + rnd.uniform(-.5, .5)), 36 + 28 * math.sin(a + rnd.uniform(-.5, .5)))
            desenha_raio(im, raio_pts(p0, p1, rnd, 4, 4), 1.5)
        qs.append(com_brilho(im, 2))
    return qs

# 5. tornado de tempestade: funil de nuvem azul-cinza com raios, gira (8 quadros, 128x160)
def tornado():
    qs = []
    for k in range(8):
        rnd = random.Random(500 + k)
        im = camada(128, 160)
        d = ImageDraw.Draw(im)
        for i in range(14):
            y = 8 + i * 10.5
            t = i / 13.0
            larg = 14 + 44 * (1 - t) ** 1.2
            cx = 64 + 6 * math.sin(t * 6 + k * math.tau / 8)
            fase = k * math.tau / 8 + i * 0.7
            for lado in (-1, 1):
                x = cx + lado * larg * math.cos(fase) * 0.5
                esp = 5 + 3 * (1 - t)
                tom = 70 + int(60 * (1 - t)) + (15 if lado > 0 else 0)
                d.ellipse([x - larg * 0.55, y - esp, x + larg * 0.55, y + esp], fill=(tom, tom + 25, tom + 70, 215), outline=CONTORNO)
        im = im.filter(ImageFilter.GaussianBlur(0.8))
        for _ in range(2):
            x0 = 64 + rnd.uniform(-30, 30)
            desenha_raio(im, raio_pts((x0, 14), (64 + rnd.uniform(-8, 8), 150), rnd, 9, 10), 2.0)
        qs.append(com_brilho(im, 4))
    return qs

# 6. raio do céu (Arauto do Trovão e queda do tornado): coluna vertical (6 quadros, 64x192)
def coluna():
    qs = []
    for k in range(6):
        rnd = random.Random(600 + k)
        im = camada(64, 192)
        desenha_raio(im, raio_pts((32 + rnd.uniform(-6, 6), 0), (32, 186), rnd, 14, 12), 4.0 - k * 0.4, ramos=4, rnd=rnd)
        im = com_brilho(im, 5)
        im.putalpha(im.getchannel("A").point(lambda v: int(v * (1.0 - k / 8.0))))
        qs.append(im)
    return qs

# 7. aura do Arauto no arqueiro: anel de faíscas (6 quadros, 96x96)
def aura():
    qs = []
    for k in range(6):
        rnd = random.Random(700 + k)
        im = camada(96, 96)
        for j in range(6):
            a = j / 6 * math.tau + k * 0.3
            p0 = (48 + 30 * math.cos(a), 52 + 22 * math.sin(a))
            p1 = (48 + 40 * math.cos(a + 0.35), 52 + 30 * math.sin(a + 0.35))
            desenha_raio(im, raio_pts(p0, p1, rnd, 3, 3), 1.5)
        im = com_brilho(im, 2)
        im.putalpha(im.getchannel("A").point(lambda v: int(v * 0.8)))
        qs.append(im)
    return qs

for nome, f in (("flecha_eletrica_proj", proj), ("raio_impacto", impacto), ("raio_arco", arco),
                ("choque_overlay", choque), ("tornado_tempestade", tornado), ("raio_coluna", coluna),
                ("arauto_trovao_aura", aura)):
    final(f(), nome + ".png")
