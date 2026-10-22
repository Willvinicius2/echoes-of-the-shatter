"""Monta as pranchas de previas/ a partir de previas/_png (PIL). Uso: python pranchas.py"""
import os
from PIL import Image, ImageDraw
AQUI = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(AQUI, "previas"); S = os.path.join(P, "_png")
REF = os.path.join(AQUI, "..", "..", "..", "docs", "arte", "referencias-geracao", "aprovadas", "03_arqueiro.png")
VISTAS = ["frente", "lado", "tres_quartos", "costas", "rosto", "wire"]
TIT = {"frente": "frente", "lado": "lado", "tres_quartos": "3/4", "costas": "costas", "rosto": "close rosto/capuz", "wire": "wireframe"}


def grade(nome, prefixos, vistas, cel=512, cols=3, titulo=None):
    itens = []
    for pf in prefixos:
        for v in vistas:
            f = os.path.join(S, f"{pf}_{v}.png")
            if os.path.exists(f):
                itens.append((f"{pf} - {TIT[v]}", f))
    linhas = (len(itens) + cols - 1) // cols
    img = Image.new("RGB", (cols * cel, linhas * cel), (30, 30, 34))
    d = ImageDraw.Draw(img)
    for i, (t, f) in enumerate(itens):
        im = Image.open(f).convert("RGB").resize((cel, cel), Image.LANCZOS)
        x, y = (i % cols) * cel, (i // cols) * cel
        img.paste(im, (x, y)); d.text((x + 8, y + 6), t, fill=(255, 255, 255))
    img.save(os.path.join(P, nome))


pecas = ["capuz", "peitoral", "calca", "luvas", "botas", "arco", "aljava"]
grade("conjunto_montado.png", ["conjunto"], VISTAS)
for p in pecas:
    grade(f"modulo_{p}.png", [p], VISTAS)
# lado a lado com a folha aprovada
ref = Image.open(REF).convert("RGB")
a = Image.open(os.path.join(S, "conjunto_tres_quartos.png")).convert("RGB")
b = Image.open(os.path.join(S, "conjunto_frente.png")).convert("RGB")
h = 1024
ref = ref.resize((int(ref.width * h / ref.height), h), Image.LANCZOS)
img = Image.new("RGB", (ref.width + 2 * h, h)); img.paste(ref, (0, 0)); img.paste(b, (ref.width, 0)); img.paste(a, (ref.width + h, 0))
ImageDraw.Draw(img).text((8, 6), "folha aprovada 03_arqueiro | modelo frente | modelo 3/4", fill=(255, 255, 255))
img.save(os.path.join(P, "comparacao_folha_aprovada.png"))
# proporcao chibi: folha aprovada + frente, 3/4 e lado do modelo
ref2 = Image.open(REF).convert("RGB"); ref2 = ref2.resize((int(ref2.width * h / ref2.height), h), Image.LANCZOS)
tres = [Image.open(os.path.join(S, f"conjunto_{v}.png")).convert("RGB").resize((h, h), Image.LANCZOS) for v in ("frente", "tres_quartos", "lado")]
img = Image.new("RGB", (ref2.width + 3 * h, h)); img.paste(ref2, (0, 0))
for i, t in enumerate(tres):
    img.paste(t, (ref2.width + i * h, 0))
ImageDraw.Draw(img).text((8, 6), "folha aprovada 03_arqueiro | modelo frente | 3/4 | lado", fill=(255, 255, 255))
img.save(os.path.join(P, "proporcao_vs_folha.png"))
# prancha mestra
mestra = ["conjunto_frente", "conjunto_tres_quartos", "conjunto_costas", "conjunto_rosto"] + [f"{p}_{'rosto' if p=='capuz' else 'frente'}" for p in pecas]
cel, cols = 512, 4
linhas = (len(mestra) + cols - 1) // cols
img = Image.new("RGB", (cols * cel, linhas * cel), (30, 30, 34)); d = ImageDraw.Draw(img)
for i, n in enumerate(mestra):
    im = Image.open(os.path.join(S, n + ".png")).convert("RGB").resize((cel, cel), Image.LANCZOS)
    img.paste(im, ((i % cols) * cel, (i // cols) * cel)); d.text(((i % cols) * cel + 8, (i // cols) * cel + 6), n, fill=(255, 255, 255))
img.save(os.path.join(P, "prancha_arqueiro_modular.png"))
print("ok")
