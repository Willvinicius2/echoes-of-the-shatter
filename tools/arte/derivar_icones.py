#!/usr/bin/env python3
"""Ícones provisórios derivados de ícones pintados já aprovados (godot/art2d/ui/icone_<id>.png).

Habilidades, reforços e Ecos do arqueiro que ainda não têm ícone próprio usam um ícone aprovado de mesmo tema
(os do mago e do guerreiro não aparecem na partida do arqueiro), copiado ou com o miolo trocado de matiz; a
moldura de pedra e ferro fica intacta. Quando o ícone definitivo for pintado (doc 29), basta gravar por cima
do mesmo arquivo e tirar a linha da tabela abaixo.

Uso: python3 tools/arte/derivar_icones.py [pasta_saida]   (padrão: godot/art2d/ui)
"""
import colorsys, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

UI = Path(__file__).resolve().parents[2] / "godot" / "art2d" / "ui"
MOLDURA = 13     # px da moldura que não muda de cor (ícones de 128 px)
SUAVE = 3        # px de transição entre a moldura e o miolo

# destino: (origem, matiz em graus ou None para cópia, modo)
# modo "girar" leva a cor dominante ao matiz; "rodar" soma os graus ao matiz de tudo; "tingir" pinta tudo com o matiz
TABELA = {
    # habilidades do arqueiro
    "toxic_tornado":  ("storm_tornado", 100, "girar"),
    "ice_comet":      ("flecha_meteoro", 200, "girar"),
    "frost_nova":     ("skill.mage.frost_nova", None, ""),
    "fire_serpent":   ("skill.mage.fire_wall", None, ""),
    "lightning_rod":  ("skill.mage.thunderstorm", None, ""),
    "thunder_burst":  ("skill.mage.overload", None, ""),
    "sky_storm":      ("corrosive_rain", 222, "girar"),
    "storm_orbs":     ("skill.mage.chain_lightning", 215, "girar"),
    "plague_spread":  ("skill.mage.inferno_nova", 100, "girar"),
    "toxic_mines":    ("smoke_bomb", 100, "rodar"),
    "acid_geyser":    ("skill.mage.flame_breath", 95, "girar"),
    "icicle_lance":   ("skill.mage.frost_bolt", None, ""),
    "ice_spikes":     ("skill.mage.glacial_spike", None, ""),
    "blizzard":       ("skill.mage.blizzard", None, ""),
    "flame_breath":   ("skill.mage.flame_breath", None, ""),
    "ring_of_fire":   ("skill.mage.inferno_nova", None, ""),
    "fuse_bomb":      ("skill.mage.meteor", None, ""),
    # cartas de reforço
    "ember_tip":      ("skill.mage.embers", None, ""),
    "wide_reach":     ("skill.mage.frost_nova", 42, "girar"),
    "extra_shot":     ("multishot", 200, "girar"),
    "swift_shots":    ("power_shot", 168, "girar"),
    "lingering":      ("skill.mage.mana_surge", None, ""),
    "piercing_skills": ("pierce", 280, "girar"),
    "flame_lore":     ("skill.mage.fireball", None, ""),
    "frost_lore":     ("skill.mage.chill", None, ""),
    "storm_lore":     ("skill.mage.static_charge", 215, "girar"),
    "venom_lore":     ("w_bloodlust", 100, "girar"),
    "herald_might":   ("w_battle_cry", None, ""),
    "keen_eye":       ("steady_aim", 190, "girar"),
    "deadly_aim":     ("hunters_mark", 42, "girar"),
    "focus":          ("esquiva", 42, "girar"),
    # Ecos do ataque básico: a flecha do ícone Tiro com a luz do elemento
    "eco_trovao":     ("tiro", 215, "tingir"),
    "eco_peste":      ("tiro", 100, "tingir"),
    "eco_gelo":       ("tiro", 190, "tingir"),
    "eco_cinzas":     ("tiro", 24, "tingir"),
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
