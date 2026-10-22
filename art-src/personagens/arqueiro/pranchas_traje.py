"""Pranchas do traje (peitoral/calca/luvas/botas): conjunto, antes/depois da cor, comparacao com a folha.
Rodar apos previas.py conjunto: python pranchas_traje.py. Saida: previas/traje_*.png"""
import os
from PIL import Image, ImageDraw
AQUI = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(AQUI, "previas"); S = os.path.join(P, "_png")
REF = os.path.join(AQUI, "..", "..", "..", "docs", "arte", "referencias-geracao", "aprovadas", "03_arqueiro.png")
V = ["frente", "tres_quartos", "costas"]


def ld(n, h=768):
    return Image.open(os.path.join(S, n + ".png")).convert("RGB").resize((h, h), Image.LANCZOS)


def tira(imgs, titulos, nome, h=768):
    img = Image.new("RGB", (h * len(imgs), h)); d = ImageDraw.Draw(img)
    for i, (im, t) in enumerate(zip(imgs, titulos)):
        img.paste(im, (i * h, 0)); d.text((i * h + 8, 6), t, fill=(255, 255, 255))
    img.save(os.path.join(P, nome))


tira([ld("conjunto_" + v) for v in V], ["frente", "3/4", "costas"], "traje_conjunto.png")
h = 768
img = Image.new("RGB", (h * 3, h * 2)); d = ImageDraw.Draw(img)
for i, v in enumerate(V):
    img.paste(ld("traje_antes_" + v), (i * h, 0)); d.text((i * h + 8, 6), "antes: " + v, fill=(255, 255, 255))
    img.paste(ld("conjunto_" + v), (i * h, h)); d.text((i * h + 8, h + 6), "depois: " + v, fill=(255, 255, 255))
img.save(os.path.join(P, "traje_antes_depois.png"))
ref = Image.open(REF).convert("RGB")
# recorte da folha: heroi grande (esquerda) e as 4 vistas do turnaround
cr = ref.crop((0, 0, 420, 800)).resize((int(420 * 1024 / 800), 1024), Image.LANCZOS)
cr2 = ref.crop((420, 20, 1040, 400)).resize((int(620 * 1024 / 380 * 0.62), int(1024 * 0.62)), Image.LANCZOS)
a, b = ld("conjunto_frente", 1024), ld("conjunto_tres_quartos", 1024)
img = Image.new("RGB", (cr.width + 2 * 1024, 1024), (30, 30, 34))
img.paste(cr, (0, 0)); img.paste(a, (cr.width, 0)); img.paste(b, (cr.width + 1024, 0))
img.paste(cr2, (0, 1024 - cr2.height)) if False else None
ImageDraw.Draw(img).text((8, 6), "folha 03 | modelo frente | modelo 3/4", fill=(255, 255, 255))
img.save(os.path.join(P, "traje_vs_folha.png"))
print("ok")
