"""Monta previas/peitoral_vs_folha.png: folha aprovada (frente/costas) ao lado do conjunto renderizado. Rodar: python peitoral_vs_folha.py"""
import os
from PIL import Image, ImageDraw
A = os.path.dirname(os.path.abspath(__file__))
ref = Image.open(os.path.join(A, "ref", "arq_ref_angulos.png")).convert("RGB")
def crop(im, box, h=700):
    c = im.crop(box); return c.resize((int(c.width * h / c.height), h), Image.LANCZOS)
paineis = [("FOLHA frente", crop(ref, (10, 10, 350, 620))), ("MODELO frente", crop(Image.open(os.path.join(A, "previas", "peitoral_conj_frente.png")).convert("RGB"), (250, 20, 780, 900))),
           ("FOLHA costas", crop(ref, (760, 10, 1110, 620))), ("MODELO costas", crop(Image.open(os.path.join(A, "previas", "peitoral_conj_costas.png")).convert("RGB"), (250, 40, 780, 900))),
           ("FOLHA 3/4", crop(ref, (1150, 10, 1500, 620))), ("MODELO 3/4 costas", crop(Image.open(os.path.join(A, "previas", "peitoral_conj_3q_costas.png")).convert("RGB"), (250, 40, 880, 900)))]
W = sum(p.width for _, p in paineis) + 10 * (len(paineis) + 1)
out = Image.new("RGB", (W, 740), (40, 40, 44)); d = ImageDraw.Draw(out); x = 10
for t, p in paineis:
    out.paste(p, (x, 30)); d.text((x + 6, 8), t, fill=(255, 255, 255)); x += p.width + 10
out.save(os.path.join(A, "previas", "peitoral_vs_folha.png")); print(out.size)
