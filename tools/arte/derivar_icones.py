#!/usr/bin/env python3
"""Ícones provisórios derivados de ícones pintados já aprovados (art-src/ui/icones_pintados/icone_<id>.png).

Habilidades, reforços e Ecos do arqueiro que ainda não têm ícone próprio usam um ícone aprovado de mesmo tema
(os do mago e do guerreiro não aparecem na partida do arqueiro), copiado ou com o miolo trocado de matiz; a
moldura de pedra e ferro fica intacta. Quando o ícone definitivo for pintado (doc 29), basta gravar por cima
do mesmo arquivo e tirar a linha da tabela abaixo.

Em 10/11/2026 os outros 29 ganharam ícone definitivo, desenhado por código (`tools/arte/icones_por_codigo`, doc 29);
sobram aqui os 6 que a revisão mandou refazer. Quando eles forem aprovados, esta ferramenta pode ser apagada.

Uso: python3 tools/arte/derivar_icones.py [pasta_saida]   (padrão: art-src/ui/icones_pintados; depois rode tools/arte/pixelizar_icones.py)
"""
import colorsys, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

UI = Path(__file__).resolve().parents[2] / "art-src" / "ui" / "icones_pintados"
MOLDURA = 13     # px da moldura que não muda de cor (ícones de 128 px)
SUAVE = 3        # px de transição entre a moldura e o miolo

# destino: (origem, matiz em graus ou None para cópia, modo)
# modo "girar" leva a cor dominante ao matiz; "rodar" soma os graus ao matiz de tudo; "tingir" pinta tudo com o matiz
TABELA = {
    # habilidades do arqueiro
    "fire_serpent":   ("skill.mage.fire_wall", None, ""),
    "flame_breath":   ("skill.mage.flame_breath", None, ""),
    "ring_of_fire":   ("skill.mage.inferno_nova", None, ""),
    # cartas de reforço
    "wide_reach":     ("skill.mage.frost_nova", 42, "girar"),
    "herald_might":   ("w_battle_cry", None, ""),
    "focus":          ("esquiva", 42, "girar"),
}


def mascara(lado):
    m = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(m).rounded_rectangle([MOLDURA, MOLDURA, lado - 1 - MOLDURA, lado - 1 - MOLDURA], radius=6, fill=255)
    return m.filter(ImageFilter.GaussianBlur(SUAVE / 2))


def dominante(px, m, lado):
    """Matiz dominante do miolo (média circular pesada por saturação e brilho)."""
    import math
    x = y = 0.0
    for j in range(lado):
        for i in range(lado):
            if m.getpixel((i, j)) < 128:
                continue
            r, g, b, a = px[i, j]
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            w = s * s * v
            x += math.cos(h * math.tau) * w
            y += math.sin(h * math.tau) * w
    return (math.atan2(y, x) / math.tau) % 1.0


def derivar(origem, matiz, modo):
    img = Image.open(UI / f"icone_{origem}.png").convert("RGBA")
    if matiz is None:
        return img
    lado = img.size[0]
    m = mascara(lado)
    px = img.load()
    alvo = matiz / 360.0
    giro = (alvo - dominante(px, m, lado)) if modo == "girar" else alvo
    out = img.copy()
    po = out.load()
    for j in range(lado):
        for i in range(lado):
            k = m.getpixel((i, j)) / 255.0
            if k <= 0.0:
                continue
            r, g, b, a = px[i, j]
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if modo != "tingir":
                h2, s2, v2 = (h + giro) % 1.0, s, v
            else:   # tingir: a luz do elemento cresce com o brilho; o escuro do fundo quase não muda
                h2 = alvo
                s2 = min(1.0, 0.25 + 0.75 * max(0.0, 1.0 - abs(v - 0.62) * 1.6)) if v > 0.2 else s * 0.6
                v2 = min(1.0, v * 1.08)
            r2, g2, b2 = colorsys.hsv_to_rgb(h2, s2, v2)
            po[i, j] = (round(r * (1 - k) + r2 * 255 * k), round(g * (1 - k) + g2 * 255 * k), round(b * (1 - k) + b2 * 255 * k), a)
    return out


def main():
    saida = Path(sys.argv[1]) if len(sys.argv) > 1 else UI
    saida.mkdir(parents=True, exist_ok=True)
    for destino, (origem, matiz, modo) in TABELA.items():
        derivar(origem, matiz, modo).save(saida / f"icone_{destino}.png", optimize=True)
    print(f"{len(TABELA)} ícones em {saida}")


if __name__ == "__main__":
    main()
