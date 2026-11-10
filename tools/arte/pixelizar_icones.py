#!/usr/bin/env python3
"""Ícones do jogo em pixel art, gerados dos ícones pintados de art-src/ui/icones_pintados/.

Cada pintura (128 px, com moldura) perde a moldura, tem o fundo texturizado trocado por um chapado escuro,
desce para a grade do jogo (48 px) com paleta curta e sem pontilhado, e ganha a moldura de ferro com
cantoneiras de bronze desenhada pixel a pixel. O jogo mostra o PNG sem suavizar (vizinho mais próximo).

Uso: python3 tools/arte/pixelizar_icones.py [id ...]      (sem ids: todos)
     python3 tools/arte/pixelizar_icones.py --folha saida.png   (folha de conferência, não entra no Git)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

RAIZ = Path(__file__).resolve().parents[2]
ORIGEM = RAIZ / "art-src" / "ui" / "icones_pintados"
DESTINO = RAIZ / "godot" / "art2d" / "ui"
LADO = 48          # px do ícone pronto
BORDA = 3          # px da moldura
CORES = 22         # cores do miolo
RECORTE = 14 / 128  # fração da pintura ocupada pela moldura pintada
FUNDO = (17, 15, 22)
ESCURO, FERRO, FERRO_LUZ = (9, 8, 12), (58, 54, 64), (112, 104, 112)
BRONZE, BRONZE_LUZ, BRONZE_SOMBRA = (168, 132, 72), (222, 186, 110), (104, 78, 44)


def moldura(img):
    d, n = ImageDraw.Draw(img), LADO
    d.rectangle([0, 0, n - 1, n - 1], outline=ESCURO)
    d.rectangle([1, 1, n - 2, n - 2], outline=FERRO)
    d.line([1, 1, n - 2, 1], fill=FERRO_LUZ)
    d.line([1, 1, 1, n - 2], fill=FERRO_LUZ)
    d.rectangle([2, 2, n - 3, n - 3], outline=ESCURO)
    for cx, cy, sx, sy in [(1, 1, 1, 1), (n - 2, 1, -1, 1), (1, n - 2, 1, -1), (n - 2, n - 2, -1, -1)]:
        for k in range(5):
            d.point((cx + sx * k, cy), fill=BRONZE)
            d.point((cx, cy + sy * k), fill=BRONZE)
        d.point((cx + sx, cy + sy), fill=BRONZE_LUZ)
        d.point((cx + sx * 4, cy), fill=BRONZE_SOMBRA)
        d.point((cx, cy + sy * 4), fill=BRONZE_SOMBRA)
    for p in [(0, 0), (n - 1, 0), (0, n - 1), (n - 1, n - 1)]:
        img.putpixel(p, (0, 0, 0, 0))
    return img


def pixelizar(caminho):
    im = Image.open(caminho).convert("RGB")
    w = im.size[0]
    c = round(RECORTE * w)
    im = im.crop((c, c, w - c, w - c))
    m = LADO - 2 * BORDA
    a = np.asarray(im.resize((m * 2, m * 2), Image.LANCZOS), float)
    v = a.max(axis=2)
    sat = (v - a.min(axis=2)) / np.maximum(v, 1)
    # o que é escuro e sem cor é fundo: vira chapado; o motivo (claro ou saturado) fica
    peso = np.maximum(np.clip((v - 52) / 46, 0, 1), np.clip((sat * v - 40) / 50, 0, 1))
    fundo = np.array(FUNDO, float)
    s = Image.fromarray((fundo + (a - fundo) * peso[..., None]).clip(0, 255).astype("uint8"))
    s = ImageEnhance.Color(ImageEnhance.Contrast(s).enhance(1.12)).enhance(1.25)
    s = s.resize((m, m), Image.BOX).filter(ImageFilter.UnsharpMask(radius=1, percent=110, threshold=0))
    q = s.quantize(CORES, method=Image.MEDIANCUT, dither=Image.NONE, kmeans=4).convert("RGB")
    out = Image.new("RGBA", (LADO, LADO), FUNDO + (255,))
    out.paste(q, (BORDA, BORDA))
    return moldura(out)


def main():
    args = sys.argv[1:]
    if args[:1] == ["--folha"]:
        arqs = sorted(ORIGEM.glob("icone_*.png"))
        col, cel = 13, LADO * 2 + 4
        folha = Image.new("RGB", (col * cel, -(-len(arqs) // col) * cel), (30, 30, 36))
        for i, f in enumerate(arqs):
            folha.paste(pixelizar(f).convert("RGB").resize((LADO * 2, LADO * 2), Image.NEAREST), (i % col * cel + 2, i // col * cel + 2))
        folha.save(args[1])
        return
    arqs = [ORIGEM / f"icone_{i}.png" for i in args] or sorted(ORIGEM.glob("icone_*.png"))
    for f in arqs:
        pixelizar(f).save(DESTINO / f.name, optimize=True)
    print(f"{len(arqs)} ícones em {DESTINO}")


if __name__ == "__main__":
    main()
