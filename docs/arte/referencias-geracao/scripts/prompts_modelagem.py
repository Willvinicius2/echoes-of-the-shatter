"""Folhas de modelagem (giro frente/lado/costas) para gerar os modelos 3D por IA de imagem para 3D.

Uso: prompts_modelagem.py <pasta das pranchas do Spell Brigade> <pasta aprovadas> <saida.json>
A imagem 1 de cada pedido e a folha canonica aprovada do personagem; as demais sao pranchas de textura do jogo de referencia.
"""
import json, os, sys

P, A, OUT = sys.argv[1:4]


def path(d, n):
    return os.path.join(d, n + ".png").replace("\\", "/")


HEROI = [path(P, n) for n in ("magos_01", "magos_02", "magos_03", "normais_01", "emissao_01")]
INIMIGO = [path(P, n) for n in ("inimigos_01", "inimigos_02", "inimigos_03", "normais_01", "emissao_01")]

BASE = (
    "MODEL SHEET for 3D modeling (character turnaround) for the action-RPG \"Echoes of the Shatter\". "
    "Attached image 1 is the canonical, owner-approved design sheet of OUR game: copy {who} from it exactly "
    "(same silhouette, proportions, colors, materials, outfit). The other attached images are texture contact sheets of the style reference game: "
    "use them only for the finish quality. The character must look like a finished in-game 3D model of a polished stylized game: "
    "sculpted, rounded, chunky bevelled volumes with smooth silhouettes and hand-painted textures with visible brush strokes and soft baked light, "
    "chibi proportions as in the design sheet. It must NOT look like blocky primitives, cubes or a graybox. "
    "LAYOUT: three full-body views of the same character side by side in three equal-width columns, left to right: FRONT view, RIGHT SIDE profile view, BACK view. "
    "Orthographic look, camera at mid-body height, no perspective distortion; all three views at the same scale, aligned on the same ground line, "
    "whole body inside each column with a clear margin, feet visible. {pose} "
    "Plain flat uniform light grey background (#C8C8C8), no floor, no cast shadow, no scenery, no text, no labels, no grid, no frame, no UI, no VFX. "
    "Even neutral lighting so the colors read as albedo, with only soft painted shading. "
    "Do not reproduce any existing character from the reference game one-to-one."
)

POSE_HUMANOIDE = (
    "Neutral A-pose for rigging: standing straight, arms angled about 40 degrees away from the body, palms down, legs slightly apart, neutral face. "
    "Hands empty and open: do NOT hold weapons or shields (they are modeled separately)."
)
POSE_FLUTUANTE = (
    "Neutral A-pose for rigging: floating upright a little above the ground line, arms angled about 40 degrees away from the body, palms down, neutral face. "
    "Hands empty and open: do NOT hold the bow (it is modeled separately)."
)
POSE_QUADRUPEDE = "Neutral standing pose for rigging: four legs straight under the body, head forward, mouth closed, tail relaxed."

ITENS = [
    ("m01_guerreiro", "02_guerreiro", HEROI, POSE_HUMANOIDE,
     "the Warrior (golden visor helmet with red plume, red tabard over grey plate armor, brown boots and gloves)"),
    ("m02_arqueiro", "03_arqueiro", HEROI, POSE_HUMANOIDE,
     "the Archer (green hood with bone beak mask, feathered green cloak, leather outfit)"),
    ("m03_mago", "04_mago", HEROI, POSE_HUMANOIDE,
     "the Mage (ink-blue pointed hood with visible face, blue robe with gold trims; never a lantern)"),
    ("m04_sentinela_oca", "05_inimigos_ato1", INIMIGO, POSE_HUMANOIDE,
     "the Sentinela Oca, the hollow armored knight in the top-left panel of the enemy sheet, normal variant only "
     "(leftmost figure: empty dark visor with two golden eyes, worn ivory plate armor, red cloth; no gold halo, no purple corruption)"),
    ("m05_cao_de_cinza", "05_inimigos_ato1", INIMIGO, POSE_QUADRUPEDE,
     "the Cao-de-Cinza, the armored hound in the third panel of the top row of the enemy sheet, normal variant only "
     "(leftmost figure: pale grey hide, red and stone back plates, horned head; no gold, no purple)"),
    ("m06_arauto_de_pedra", "05_inimigos_ato1", INIMIGO, POSE_HUMANOIDE.replace("neutral face", "single glowing orange eye"),
     "the Arauto de Pedra, the stone golem construct in the first panel of the bottom row of the enemy sheet, normal variant only "
     "(leftmost figure: chunky ivory stone blocks with moss, one glowing orange eye in the chest-head; no gold halo, no purple)"),
    ("m07_arqueiro_espectral", "05_inimigos_ato1", INIMIGO, POSE_FLUTUANTE,
     "the Arqueiro Espectral, the teal hooded ghost archer in the third panel of the bottom row of the enemy sheet, normal variant only "
     "(leftmost figure: translucent teal tattered robe, glowing cyan eyes under the hood, wispy lower body)"),
    ("m08_guardiao_cripta", "06_chefes_ato1", INIMIGO, POSE_HUMANOIDE.replace("weapons or shields", "the stone hammer or the shield"),
     "the boss Guardiao da Cripta in the top-left panel of the boss sheet (giant armored knight: cracked ivory stone plate armor with gold trims, "
     "golden visor with glowing yellow eye slit, big red plume and tattered red cape); it is about three times the height of a hero"),
]

data = []
for iid, canon, refs, pose, who in ITENS:
    data.append({
        "id": iid,
        "titulo": "Folha de modelagem: " + iid.split("_", 1)[1].replace("_", " "),
        "tamanho": "1536x1024",
        "prompt": BASE.format(who=who, pose=pose),
        "referencias": [path(A, canon)] + refs,
    })

data.append({
    "id": "m09_armas",
    "titulo": "Folha de modelagem: armas e escudos",
    "tamanho": "1536x1024",
    "prompt": (
        "PROP MODEL SHEET for 3D modeling for the action-RPG \"Echoes of the Shatter\". Attached images 1 to 4 are the canonical, owner-approved design sheets of OUR game "
        "(1 Warrior, 2 Archer, 3 Mage, 4 Act I bosses). Copy these weapons exactly from them and lay them out separately, each one isolated and fully visible, "
        "in a clean grid, each shown from the front and from the side: the Warrior's stone block hammer and stone-inlay kite shield; the Archer's bone recurve bow and quiver; "
        "the Mage's wooden staff with a floating blue crystal in a gold ring (never a lantern); the boss Guardiao da Cripta's giant cracked stone hammer and tall red shield with a gold sun emblem. "
        "Finished stylized game props: sculpted chunky bevelled forms with hand-painted textures and visible brush strokes, not blocky primitives. "
        "Orthographic look, plain flat uniform light grey background (#C8C8C8), no cast shadow, no text, no labels, no grid lines, no frame, even neutral lighting."
    ),
    "referencias": [path(A, n) for n in ("02_guerreiro", "03_arqueiro", "04_mago", "06_chefes_ato1")] + [path(P, "magos_01"), path(P, "inimigos_01")],
})

json.dump(data, open(OUT, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print(len(data), "pedidos em", OUT)
