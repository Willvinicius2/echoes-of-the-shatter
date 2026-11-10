#!/usr/bin/env python3
"""Ícones definitivos das habilidades, reforços e Ecos do Arqueiro, desenhados por código (sem serviço pago).

Cada ícone nasce como uma pintura de 128 px (mesma moldura de pedra dos aprovados, miolo desenhado em `glifos.py`) em
art-src/ui/icones_pintados/icone_<id>.png e desce para a grade do jogo pelo `tools/arte/pixelizar_icones.py`
(48 px, 22 cores, moldura de ferro com cantoneiras de bronze), igual aos ícones pintados à mão.

Uso: python3 tools/arte/icones_por_codigo/gerar.py [--saida pasta] [--folha arquivo.png] [--jogo] [--receitas modulo] [id ...]
  sem ids: todos os ícones de GLIFOS (as receitas aprovadas). --saida muda a pasta das pinturas 128 px (padrão
  art-src/ui/icones_pintados). --folha grava uma folha de conferência (128 px e 48 px lado a lado; não entra no Git).
  --jogo grava também o ícone 48 px em godot/art2d/ui/ (o que o jogo carrega).
  --receitas usa outro módulo de receitas (um arquivo com um dicionário GLIFOS) em vez do `glifos`: serve para a prévia
  de ícones refeitos, que só entram em `glifos.py` depois de aprovados.
"""
import importlib
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pintura as P                       # noqa: E402
import glifos                             # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
PINTADOS = RAIZ / "art-src" / "ui" / "icones_pintados"
MOLDURA_REF = PINTADOS / "icone_tiro.png"   # a moldura de pedra e ferro de referência (a pintura aprovada)
MOLDURA = 13
SUAVE = 3


def mascara_miolo(lado=128):
    m = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(m).rounded_rectangle([MOLDURA, MOLDURA, lado - 1 - MOLDURA, lado - 1 - MOLDURA], radius=6, fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(SUAVE / 2)), np.float32) / 255.0


def compor(miolo):
    """Miolo desenhado (128 x 128 x 3, 0..1) dentro da moldura da pintura de referência."""
    ref = np.asarray(Image.open(MOLDURA_REF).convert("RGBA"), np.float32) / 255.0
    m = mascara_miolo(P.N)[..., None]
    rgb = ref[..., :3] * (1 - m) + miolo * m
    out = np.concatenate([rgb, ref[..., 3:4]], axis=-1)
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")


def desenhar_icone(id, receitas=None):
    return compor((receitas or glifos.GLIFOS)[id]())


def main():
    args = sys.argv[1:]
    saida = PINTADOS
    folha = None
    jogo = False
    receitas = glifos.GLIFOS
    ids = []
    i = 0
    while i < len(args):
        if args[i] == "--saida":
            saida = Path(args[i + 1]); i += 2
        elif args[i] == "--folha":
            folha = Path(args[i + 1]); i += 2
        elif args[i] == "--jogo":
            jogo = True; i += 1
        elif args[i] == "--receitas":
            receitas = importlib.import_module(args[i + 1]).GLIFOS; i += 2
        else:
            ids.append(args[i]); i += 1
    ids = ids or list(receitas)
    saida.mkdir(parents=True, exist_ok=True)
    import pixelizar_icones as PX
    pares = []
    for id in ids:
        im = desenhar_icone(id, receitas)
        caminho = saida / f"icone_{id}.png"
        im.save(caminho, optimize=True)
        px = PX.pixelizar(caminho)
        if jogo:
            px.save(PX.DESTINO / f"icone_{id}.png", optimize=True)
        pares.append((id, im, px))
        print("ok", id)
    if folha:
        esc = 2
        cel_w, cel_h = 128 * esc + 48 * 3 + 12, 128 * esc + 14
        cols = 2 if len(pares) > 1 else 1
        rows = -(-len(pares) // cols)
        f = Image.new("RGB", (cols * cel_w, rows * cel_h), (30, 30, 36))
        d = ImageDraw.Draw(f)
        for k, (id, im, px) in enumerate(pares):
            x, y = (k % cols) * cel_w + 4, (k // cols) * cel_h + 2
            f.paste(im.resize((128 * esc, 128 * esc), Image.LANCZOS), (x, y), im.resize((128 * esc, 128 * esc), Image.LANCZOS))
            p3 = px.resize((48 * 3, 48 * 3), Image.NEAREST)
            f.paste(p3, (x + 128 * esc + 6, y), p3)
            d.text((x, y + 128 * esc + 1), id, fill=(220, 220, 220))
        f.save(folha)
        print("folha", folha, f.size)


if __name__ == "__main__":
    main()
