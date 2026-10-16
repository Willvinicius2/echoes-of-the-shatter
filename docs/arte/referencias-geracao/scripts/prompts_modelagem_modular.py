"""Folhas do personagem modular: corpo base sem equipamento e as 5 pecas da armadura inicial de cada heroi.

Decisao do dono (16/10/2026): o corpo e o equipamento sao modelos 3D separados, para que trocar de item mude a aparencia.
Espacos de armadura: cabeca (head), corpo/peitoral (body), maos (hands), pernas/calca (legs) e pes (feet).
A aparencia aprovada de cada heroi (aprovadas/modelagem/m01..m03) e a armadura inicial.

Uso: prompts_modelagem_modular.py <pasta das pranchas do Spell Brigade> <pasta aprovadas> <saida.json>
"""
import json, os, sys

P, A, OUT = sys.argv[1:4]


def path(*parts):
    return os.path.join(*parts).replace("\\", "/") + ".png"


ESTILO = [path(P, n) for n in ("magos_01", "magos_02", "magos_03", "normais_01")]

COMUM = (
    "Plain flat uniform light grey background (#C8C8C8), no floor, no cast shadow, no scenery, no text, no labels, no numbers, no grid lines, no frame, no UI, no VFX. "
    "Even neutral lighting so the colors read as albedo, only soft painted shading. "
    "Finished stylized 3D game model look: sculpted, rounded, chunky bevelled volumes with smooth silhouettes and hand-painted textures with visible brush strokes; "
    "never blocky primitives, cubes or a graybox. Do not reproduce any existing character from the style reference one-to-one."
)

CORPO = (
    "BASE BODY MODEL SHEET for a modular 3D character of the action-RPG \"Echoes of the Shatter\" (all equipment is modeled separately and worn on top). "
    "Attached image 1 is the owner-approved modeling sheet of OUR {hero} wearing the starting equipment; attached image 2 is the canonical design sheet. "
    "Draw the SAME character WITHOUT any equipment: no helmet or hood, no chest armor, robe or cloak, no gloves, no armored pants, no boots, no weapons. "
    "Keep exactly the same chibi proportions, height, head size, body build, A-pose and ground line as image 1, so the equipment pieces fit on top. "
    "The body wears only a plain close-fitting neutral undergarment: a dark grey sleeveless linen undershirt and short dark grey linen undershorts; bare arms, bare hands, bare feet. "
    "{rosto} "
    "LAYOUT exactly like image 1: three full-body views side by side in three equal-width columns, left to right FRONT view, RIGHT SIDE profile view, BACK view; "
    "orthographic look, same scale, aligned on the same ground line, whole body inside each column with a clear margin. "
    "Neutral A-pose: standing straight, arms angled about 40 degrees away from the body, palms down, legs slightly apart. "
)

PECAS = (
    "EQUIPMENT MODEL SHEET (modular armor) for the action-RPG \"Echoes of the Shatter\". "
    "Attached image 1 is the owner-approved modeling sheet of OUR {hero}; attached image 2 is the canonical design sheet. "
    "Split that exact outfit into its five equipment pieces and draw each piece SEPARATELY, isolated, as a hollow piece of equipment with no body inside "
    "(as if worn by an invisible body, keeping the worn shape, size and proportions of image 1). Copy colors, materials and details exactly from image 1. "
    "The five pieces: 1 HEAD: {head}; 2 BODY: {body}; 3 HANDS: {hands}; 4 LEGS: {legs}; 5 FEET: {feet}. "
    "LAYOUT: a clean grid of five columns in this order left to right: HEAD, BODY, HANDS, LEGS, FEET. "
    "Top row: FRONT view of each piece. Bottom row: BACK view of each piece, in the same column. All pieces at the same scale as worn on the character, "
    "each piece fully visible with a clear margin, pieces never touching each other. "
)

HEROIS = [
    ("01", "guerreiro", "m01_guerreiro", "02_guerreiro", "Warrior",
     "Show the head and face normally hidden under the helmet (new design for owner approval): a friendly but determined young adult with a sturdy jaw, "
     "short messy auburn-red hair echoing the red plume, thick eyebrows, warm skin tone, big readable chibi eyes.",
     dict(head="the golden visor helmet with the big red plume",
          body="the grey plate cuirass with gold-trimmed pauldrons and the red tabard hanging front and back",
          hands="the pair of brown leather gauntlets with grey metal cuffs",
          legs="the grey plate thigh guards and knee guards over brown trousers, from the hips down to the ankles",
          feet="the pair of brown leather boots with metal toe caps")),
    ("02", "arqueiro", "m02_arqueiro", "03_arqueiro", "Archer",
     "Show the face normally hidden under the hood and the bone beak mask (new design for owner approval): a sharp-eyed young adult with bright green eyes, "
     "light freckles, dark brown hair tied in a short ponytail, lean build.",
     dict(head="the green hood together with the bone beak mask",
          body="the feathered green cloak over the leather jerkin with belt and pouches",
          hands="the pair of leather bracers with fingerless gloves",
          legs="the dark brown leather trousers, from the hips down to the ankles",
          feet="the pair of tall brown leather boots with straps")),
    ("03", "mago", "m03_mago", "04_mago", "Mage",
     "Keep the face and hair already visible in image 1 identical (same lavender hair, same big eyes, same face).",
     dict(head="the ink-blue pointed hood with gold trims (empty, no face inside)",
          body="the blue robe with gold trims, long wide sleeves and the long robe skirt",
          hands="a pair of simple blue cloth hand wraps with gold cuffs matching the robe (new design for owner approval, the approved art shows bare hands)",
          legs="simple dark blue cloth trousers worn under the robe, from the hips down to the ankles",
          feet="the pair of brown boots with gold trims")),
]

data = []
for n, nome, mod, canon, hero, rosto, pecas in HEROIS:
    refs = [path(A, "modelagem", mod), path(A, canon)] + ESTILO
    data.append({"id": f"mod_b{n}_{nome}_corpo", "titulo": f"Corpo base: {nome}", "tamanho": "1536x1024",
                 "prompt": CORPO.format(hero=hero, rosto=rosto) + COMUM, "referencias": refs})
    data.append({"id": f"mod_a{n}_{nome}_inicial", "titulo": f"Armadura inicial em pecas: {nome}", "tamanho": "1536x1024",
                 "prompt": PECAS.format(hero=hero, **pecas) + COMUM, "referencias": refs})

json.dump(data, open(OUT, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print(len(data), "pedidos em", OUT)
