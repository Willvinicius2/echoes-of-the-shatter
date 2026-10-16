"""Deriva os prompts da rodada de consistencia dos herois a partir de prompts_spell_brigade.json.

Uso: prompts_herois.py <prompts_base.json> <saida.json> <folha_guerreiro> <folha_arqueiro> <folha_mago>
"""
import json, sys

base, out, warrior, archer, mage = sys.argv[1:6]
items = {i["id"]: i for i in json.load(open(base, encoding="utf-8"))}

MAGE = (
    "Character sheet of the Mage (Mago, 'scholar who bends the Archive'): a young human scholar wearing a deep ink-blue pointed hood draped over the shoulders, "
    "the FACE IS CLEARLY VISIBLE under the hood (eyes, nose, mouth, some hair), not an empty, dark or glowing hood. "
    "Holds a tall carved wooden staff topped with a floating blue crystal held inside a gold Archive-glyph ring. NO lantern anywhere, nothing hanging from the staff. "
    "Ink-blue robe with gold library-seal embroidery, leather belt with a small book, torn book pages floating around, blue Mana accent. "
    "Front, back and 3/4 turnaround, plus poses: idle, walk, Faisca Guiada (homing spark from the staff), Lanca de Gelo (ice lance), Brasa Errante (ember ball), "
    "Barreira de Vidro (glass barrier), Pulso de Tempestade (chain lightning), Passagem Arcana (blink). Palette strip and 2 alternate skins (golden, prestige)."
)

IDENTITY = (
    "\n\nHERO IDENTITY (mandatory): the first attached images are the canonical character sheets of our three heroes. "
    "Every hero that appears must match those sheets exactly: same silhouette, proportions, colors, outfit, helmet/hood and weapon. "
    "Warrior = golden visor helmet with red plume, red tabard, stone-inlay kite shield, stone block hammer. "
    "Archer = green hood with bone beak mask, feathered green cloak, bone recurve bow. "
    "Mage = ink-blue pointed hood with visible face, wooden staff with a floating blue crystal in a gold ring, no lantern. "
    "Do not invent other heroes or generic adventurers."
)

HERO_SCENES = {
    "01_key_art": ["01_key_art", "all three heroes"],
    "06_chefes_ato1": ["06_chefes_ato1", "in each panel one of our heroes fights the boss: Warrior vs Guardiao da Cripta, Archer vs Tecela de Cascalho, Mage vs Carrasco do Voto, Warrior vs Vigia do Sino"],
    "07_cripta_tileset": ["07_cripta_tileset", "the hero for scale is our Warrior"],
    "08_pedreira_ponte": ["08_pedreira_ponte", "the hero in the quarry scene is our Archer, the hero on the bridge is our Mage"],
    "09_vfx_habilidades": ["09_vfx_habilidades", "row 1 caster is our Warrior, row 2 our Archer, row 3 our Mage"],
    "10_hud_mockup": ["10_hud_mockup", "the player character is our Warrior and the boss is the Guardiao da Cripta (giant knight with a huge hammer and tower shield)"],
}

result = []
m = dict(items["04_mago"])
m["prompt"] = (m["prompt"].split("CONTENT: ")[0] + "CONTENT: " + MAGE
               + " The first two attached images are the approved Warrior and Archer sheets: draw the Mage as the third member of the same set "
               "(same rendering, proportions, sheet layout and level of detail).")
m["referencias"] = [warrior, archer] + m["referencias"]
result.append(m)
for iid, (_, cast) in HERO_SCENES.items():
    it = dict(items[iid])
    it["prompt"] = it["prompt"] + IDENTITY + " In this image: " + cast + "."
    refs = [r for r in it["referencias"]]
    if iid == "09_vfx_habilidades":  # mantem 9 anexos: sai uma prancha de vfx que ja aparece em 07/08
        refs = [r for r in refs if not r.endswith(("vfx_07.png", "vfx_08.png"))]
    it["referencias"] = [warrior, archer, mage] + refs
    result.append(it)
json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("ok", [i["id"] for i in result], [len(i["referencias"]) for i in result])
