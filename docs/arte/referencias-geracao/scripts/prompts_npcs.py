"""Rodada 18 (18/10/2026): folhas de modelagem dos 4 NPCs do Refugio (Ilsa, Tico, Vendedor, Encantador), 2 variacoes cada.

Gera prompts_npcs.json (uso com gerar.py).
Saida das imagens: D:/openclaude/_trabalho-claude/echoes-arte/geradas_rodada_18/npcs
Uso: prompts_npcs.py [pasta aprovadas] [pasta pranchas do Spell Brigade] [saida.json]

Fonte do que cada NPC e (docs/00 secao 3 e docs/16 secao 11); nada alem disso foi inventado:
- Ilsa, a Cartografa: mapa, Marcos de Retorno, expedicoes; pratica e ironica.
- Tico, o Mensageiro: crianca que corre entre os Marcos; alivio comico; entrega relatorio e loot.
- Vendedor: funcao, sem nome proprio nem lore (compra itens, vende frascos).
- Encantador: funcao, sem nome proprio nem lore (melhorias de equipamento).
Todo o resto (roupa, props, cores) e escolha visual provisoria que comunica a funcao; o dono escreve a historia.
Cor dominante de cada um: Ilsa turquesa, Tico amarelo-sol, Vendedor marrom terroso, Encantador ametista;
longe do vermelho/verde/azul dos herois, do marfim/roxo escuro dos inimigos e do laranja do Unico (docs/03 2.3 e 2.4).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
A = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "aprovadas")
P = sys.argv[2] if len(sys.argv) > 2 else r"D:\openclaude\_trabalho-claude\echoes-arte\pranchas"
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "..", "prompts_npcs.json")


def ap(n):
    return os.path.abspath(os.path.join(A, "modelagem", n + ".png")).replace("\\", "/")


def sb(n):
    return os.path.join(P, n + ".png").replace("\\", "/")


BASE = (
    "MODEL SHEET for 3D modeling (character turnaround) of a NON-PLAYABLE TOWN NPC for the action-RPG \"Echoes of the Shatter\". "
    "Attached image 1 is the owner-approved modeling sheet of OUR game's Mage and attached image 2 the Warrior: use them ONLY for the layout format, the chibi proportions "
    "(about 3 heads tall, big head, small hands and feet), the sculpted finish and the hand-painted brushwork. Do NOT copy the Mage or the Warrior: this is a different, new character. "
    "Attached images 3 and 4 are texture contact sheets of the style reference game: finish quality only. "
    "The NPC must look like a finished in-game 3D model of a polished stylized game: sculpted, rounded, chunky bevelled volumes with smooth silhouettes, "
    "hand-painted textures with visible brush strokes and soft baked light and violet-tinted shadows. It must NOT look like blocky primitives, cubes, a graybox or a mobile toy. "
    "{who} "
    "It is a civilian town resident, NOT a hero: no armor, no helmet, no weapon, no class emblem, no heroic cape. "
    "LAYOUT: three full-body views of the same character side by side in three equal-width columns, left to right: FRONT view, RIGHT SIDE profile view, BACK view. "
    "Orthographic look, camera at mid-body height, no perspective distortion; all three views at the same scale, aligned on the same ground line, "
    "whole body inside each column with a clear margin, feet visible. "
    "Neutral A-pose for rigging: standing straight, arms angled about 40 degrees away from the body, palms down, legs slightly apart, friendly neutral face. {hands}"
    "Plain flat uniform light grey background (#C8C8C8), no floor, no cast shadow, no scenery, no text, no labels, no grid, no frame, no UI. "
    "Even neutral lighting so the colors read as albedo, with only soft painted shading. "
    "Readability: the silhouette must be unmistakable at a tiny size from far away, and the DOMINANT color mass of the outfit must be {color}. "
    "{var}"
)

MAOS_VAZIAS = "Hands empty and open. "

NPCS = [
    ("n01_ilsa", (
        "THIS NPC: Ilsa, the Cartographer: a practical, ironic adult woman who maps what changed in the world. Visual: a tall-for-the-cast, slim silhouette with a wide-brimmed round hat "
        "(brim wider than the shoulders), a knee-length turquoise travel coat with a high collar and cream scarf, a leather bandolier with ink pots and a brass compass on the chest, "
        "and a rolled map tube strapped diagonally on her back that sticks out above one shoulder (visible from front and back). Half-lidded, slightly wry expression. "
        "Dark brown trousers and boots."),
     MAOS_VAZIAS, "turquoise teal (#2F9C98) with cream and brown accents",
     ("Variation hint: the coat is long and straight with a flat brimmed hat.",
      "Variation hint: shorter swinging coat, a cocked hat brim and a tiny rolled map tucked in the belt as well.")),
    ("n02_tico", (
        "THIS NPC: Tico, the Messenger: a CHILD who runs between the Marker stone waypoints, comic relief, high energy. Visual: clearly the SHORTEST of the cast "
        "(about 80 percent of the Mage's height, about 2.5 heads tall, very big head, short limbs), a bright sunny-yellow short jacket or tunic with rolled-up sleeves, "
        "a big leather messenger satchel with a flap and a scroll sticking out, mismatched oversized boots, a short scarf tail, messy hair, a wide cheerful open grin. "
        "Light and springy build."),
     MAOS_VAZIAS, "bright sunny yellow (#FFC93C) with brown leather accents",
     ("Variation hint: a flat cap with a small visor, the satchel hangs on the left hip.",
      "Variation hint: bare head with a spiky hair tuft and a pair of small goggles pushed up on the forehead, the satchel on the back.")),
    ("n03_vendedor", (
        "THIS NPC: the Vendedor (Vendor), a shopkeeper who buys items and sells refill flasks; only a function, no name and no backstory. Visual: the WIDEST and roundest silhouette of the cast "
        "(stocky, barrel-shaped body, short legs), a long cream apron over an earthy brown tunic with rolled sleeves, a huge backpack stacked with sacks, crates and hanging glass flasks, "
        "and a small brass balance scale (two pans) hanging from the front of the belt or fixed on top of the backpack, a coin pouch on the belt. "
        "No hat or a soft round cap; a cheerful businesslike expression."),
     "Hands empty and open (the scale and the flasks are attached to the body or the backpack). ",
     "warm earthy brown (#8A5A34) with a cream apron",
     ("Variation hint: round soft cap, the balance scale hangs at the belt.",
      "Variation hint: bare head with a thick headband, the balance scale stands on top of the backpack.")),
    ("n04_encantador", (
        "THIS NPC: the Encantador (Enchanter), a craftsperson who upgrades equipment with magic; only a function, no name and no backstory. Visual: a TALL, narrow vertical silhouette "
        "(longest robe of the cast, almost reaching the ground), an amethyst-violet robe with long wide open sleeves, glowing cyan (#4FE0D0) runes embroidered along the hem and sleeves, "
        "both open hands softly glowing cyan with small floating rune glyphs above the palms, a thin floating rune ring behind the head like a halo, hair in a tall top knot (NO pointed mage hood or hat, "
        "it must not look like the Mage), a thick sash belt with small tool pouches. Calm, concentrated expression."),
     "Hands open and empty, softly glowing (the glow is small and soft, painted on the model). ",
     "amethyst violet (#8E5BD0) with cyan glowing runes",
     ("Variation hint: the rune ring floats behind the back of the head, sleeves are wide bells.",
      "Variation hint: no ring; the glyphs orbit near the hands, the robe has a high stiff collar and a hanging rune scroll sash.")),
]

data = []
for iid, who, hands, color, variacoes in NPCS:
    for v, var in zip("ab", variacoes):
        data.append({
            "id": f"{iid}_{v}",
            "titulo": f"Folha de modelagem NPC: {iid.split('_', 1)[1].replace('_', ' ')} (variacao {v})",
            "tamanho": "1536x1024",
            "prompt": BASE.format(who=who, hands=hands, color=color, var=var),
            "referencias": [ap("m03_mago"), ap("m01_guerreiro"), sb("magos_01"), sb("normais_01")],
        })

json.dump(data, open(OUT, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print(len(data), "pedidos em", OUT)
