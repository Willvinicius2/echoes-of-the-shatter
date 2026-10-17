#!/usr/bin/env python3
"""Monta as pranchas de quadros-chave da vitrine de VFX (-vfxshow).

Entrada: a pasta de saida da vitrine (frames/<habilidade>_<enquadramento>/NNNNN.jpg + marks.txt).
Saida, na mesma pasta: prancha_<habilidade>_<enquadramento>.jpg por habilidade e enquadramento e prancha_geral_<enquadramento>.jpg
com um quadro de cada habilidade.

Uso: python montar_pranchas.py PASTA
Precisa do Pillow.
"""
import os
import sys
from collections import defaultdict

from PIL import Image, ImageDraw, ImageFont

FPS = 30
COLS = 3


def ler_marcas(pasta):
    marcas = defaultdict(dict)
    orcamento = {}
    caminho = os.path.join(pasta, "marks.txt")
    if not os.path.exists(caminho):
        return marcas, orcamento
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            partes = linha.rstrip("\n").split("\t")
            if len(partes) != 3:
                continue
            rotulo, nome, valor = partes
            if nome == "orcamento":
                orcamento[rotulo] = valor
            else:
                marcas[rotulo].setdefault(nome, int(valor))
    return marcas, orcamento


def quadros_chave(marcas, total):
    """Escolhe ate 6 quadros: preparacao, saida, voo, impacto e dois depois do impacto."""
    primeiro = lambda *nomes: next((marcas[n] for n in nomes if n in marcas), None)
    inicio = primeiro("carga_inicio", "defesa_ergue", "preparacao")
    saida = primeiro("saida", "bloqueio")
    impacto = primeiro("explosao", "acerto", "defesa_perfeita", "estilhaca")
    escolhidos = []

    def add(rotulo, quadro):
        if quadro is None:
            return
        quadro = max(0, min(total - 1, int(quadro)))
        if all(abs(quadro - q) > 1 for _, q in escolhidos):
            escolhidos.append((rotulo, quadro))

    add("preparacao", marcas.get("preparacao", inicio))
    if "carga_maxima" in marcas:
        add("carga maxima", marcas["carga_maxima"])
    add("saida", saida)
    if saida is not None and impacto is not None and impacto - saida > 4:
        add("em voo", (saida + impacto) // 2)
    add("impacto", impacto)
    if impacto is not None:
        add("+0,25 s", impacto + 8)
        add("+0,6 s", impacto + 18)
    elif saida is not None:
        add("+0,25 s", saida + 8)
        add("+0,6 s", saida + 18)
    if len(escolhidos) < 3:  # sem marcas: espalha
        for k in range(6):
            add(f"{k * total // 6 / FPS:.1f} s", k * total // 6)
    return sorted(escolhidos, key=lambda x: x[1])[:6]


def fonte(tamanho):
    for nome in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default()


def recorte_56m(img):
    """Na camera do jogo a 56 m o personagem fica no centro; o recorte 1:1 mostra a leitura em pixels reais."""
    w, h = img.size
    return img.crop((w // 2 - 320, h // 2 - 260, w // 2 + 640, h // 2 + 280))


def prancha(pasta, rotulo, marcas, orcamento):
    quadros_pasta = os.path.join(pasta, "frames", rotulo)
    arquivos = sorted(f for f in os.listdir(quadros_pasta) if f.endswith(".jpg"))
    total = len(arquivos)
    chaves = quadros_chave(marcas.get(rotulo, {}), total)
    e56 = rotulo.endswith("_56m")
    tile_w, tile_h = (720, 405) if e56 else (640, 360)
    linhas = (len(chaves) + COLS - 1) // COLS
    margem, topo = 8, 56
    folha = Image.new("RGB", (COLS * tile_w + (COLS + 1) * margem, topo + linhas * (tile_h + 30) + margem), (15, 11, 20))
    d = ImageDraw.Draw(folha)
    d.text((margem, 10), rotulo.replace("_", " "), fill=(252, 213, 138), font=fonte(26))
    extra = orcamento.get(rotulo, "")
    if extra:
        d.text((margem + 520, 16), "orcamento: " + extra, fill=(190, 180, 200), font=fonte(16))
    for i, (nome, quadro) in enumerate(chaves):
        img = Image.open(os.path.join(quadros_pasta, arquivos[quadro])).convert("RGB")
        if e56:
            img = recorte_56m(img)
        img = img.resize((tile_w, tile_h), Image.LANCZOS)
        x = margem + (i % COLS) * (tile_w + margem)
        y = topo + (i // COLS) * (tile_h + 30)
        folha.paste(img, (x, y + 24))
        d.text((x + 4, y + 2), f"{nome}  (quadro {quadro}, {quadro / FPS:.2f} s)", fill=(232, 224, 212), font=fonte(16))
    saida = os.path.join(pasta, f"prancha_{rotulo}.jpg")
    folha.save(saida, quality=92)
    return saida, chaves, total


def geral(pasta, enquadramento, itens):
    if not itens:
        return None
    cols = 3
    tile_w, tile_h = 640, 360
    linhas = (len(itens) + cols - 1) // cols
    margem = 8
    folha = Image.new("RGB", (cols * tile_w + (cols + 1) * margem, 50 + linhas * (tile_h + 28) + margem), (15, 11, 20))
    d = ImageDraw.Draw(folha)
    d.text((margem, 10), f"VFX das habilidades - enquadramento {enquadramento}", fill=(252, 213, 138), font=fonte(26))
    for i, (rotulo, caminho_quadro) in enumerate(itens):
        img = Image.open(caminho_quadro).convert("RGB")
        if enquadramento == "56m":
            img = recorte_56m(img)
        img = img.resize((tile_w, tile_h), Image.LANCZOS)
        x = margem + (i % cols) * (tile_w + margem)
        y = 50 + (i // cols) * (tile_h + 28)
        d.text((x + 4, y + 2), rotulo.replace("_", " ").rsplit(" ", 1)[0], fill=(232, 224, 212), font=fonte(16))
        folha.paste(img, (x, y + 24))
    saida = os.path.join(pasta, f"prancha_geral_{enquadramento}.jpg")
    folha.save(saida, quality=92)
    return saida


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    pasta = sys.argv[1]
    marcas, orcamento = ler_marcas(pasta)
    quadros = os.path.join(pasta, "frames")
    grupos = defaultdict(list)
    for rotulo in sorted(os.listdir(quadros)):
        saida, chaves, total = prancha(pasta, rotulo, marcas, orcamento)
        print(f"{saida}: {len(chaves)} quadros-chave de {total}")
        enquadramento = rotulo.rsplit("_", 1)[1]
        escolha = next((q for n, q in chaves if n in ("impacto", "em voo")), chaves[len(chaves) // 2][1])
        arquivos = sorted(f for f in os.listdir(os.path.join(quadros, rotulo)) if f.endswith(".jpg"))
        grupos[enquadramento].append((rotulo, os.path.join(quadros, rotulo, arquivos[min(escolha, len(arquivos) - 1)])))
    for enquadramento, itens in grupos.items():
        print(geral(pasta, enquadramento, itens))
    return 0


if __name__ == "__main__":
    sys.exit(main())
