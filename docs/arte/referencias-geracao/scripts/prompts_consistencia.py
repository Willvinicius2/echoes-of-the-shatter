"""Segunda passada de consistencia: inimigos, chefes e herois canonicos em todas as cenas.

Uso: prompts_consistencia.py <prompts_base.json> <pranchas> <canon_dir> <saida.json>
canon_dir contem 02_guerreiro, 03_arqueiro, 04_mago, 05_inimigos_ato1, 06_chefes_ato1, 07_cripta_tileset,
08_pedreira_ponte e (para o HUD) 11_icones.
"""
import json, os, sys

base, P, C, out = sys.argv[1:5]
items = {i["id"]: i for i in json.load(open(base, encoding="utf-8"))}


def sheet(n):
    return os.path.join(P, n + ".png").replace("\\", "/")


def canon(n):
    return os.path.join(C, n + ".png").replace("\\", "/")


ROLE = {
    "02_guerreiro": "the canonical Warrior sheet (golden visor helmet with red plume, red tabard, stone-inlay kite shield, stone block hammer)",
    "03_arqueiro": "the canonical Archer sheet (green hood with bone beak mask, feathered green cloak, bone recurve bow)",
    "04_mago": "the canonical Mage sheet (ink-blue pointed hood with visible face, wooden staff with a floating blue crystal in a gold ring, no lantern)",
    "05_inimigos_ato1": "the canonical Act I enemy sheet (8 enemies, each with normal, elite gold-halo and purple corrupted variants)",
    "06_chefes_ato1": "the canonical Act I boss sheet (Guardiao da Cripta top-left, Tecela de Cascalho top-right, Carrasco do Voto bottom-left, Vigia do Sino bottom-right)",
    "07_cripta_tileset": "the canonical Broken Crypt environment and kit",
    "08_pedreira_ponte": "the canonical Quarry of Echoes and Bell Bridge environments and kits",
    "11_icones": "the canonical skill and item icon sheet",
}


def identity(canons, cast):
    lines = [f"attached image {k + 1} is {ROLE[c]}" for k, c in enumerate(canons)]
    return (
        "\n\nCONSISTENCY (mandatory): " + "; ".join(lines) + ". "
        "Every hero, enemy, boss, environment piece or icon that appears must be copied from those canonical sheets of OUR game exactly: "
        "same silhouette, proportions, colors, outfit and weapon. Do not invent new heroes, enemies or bosses. In this image: " + cast + "."
    )


PLAN = {
    "09_vfx_habilidades": (
        ["02_guerreiro", "03_arqueiro", "04_mago", "05_inimigos_ato1"],
        ["vfx_01", "vfx_05", "vfx_06", "vfx_09", "tecnicos_01"],
        "row 1 caster is the Warrior, row 2 the Archer, row 3 the Mage; the targets hit by the skills are Act I enemies from the enemy sheet "
        "(Sentinela Oca, Lanceiro Repetido, Cao-de-Cinza, Corvo Imitador, Arauto de Pedra); bottom row telegraphs are cast by enemies from the enemy sheet",
    ),
    "11_icones": (
        ["02_guerreiro", "03_arqueiro", "04_mago"],
        ["icones_01", "ui_02", "ui_03", "vfx_09"],
        "skill icons that show a figure must show that skill's hero (Warrior icons show the Warrior, Archer icons the Archer, Mage icons the Mage); "
        "item icons (helm, chest, shield, hammer, bow, staff) are the items those heroes wear and carry; no empty frames",
    ),
    "12_mapa_mundi": (
        ["02_guerreiro", "05_inimigos_ato1", "06_chefes_ato1", "07_cripta_tileset", "08_pedreira_ponte"],
        ["ui_01", "ui_02", "ui_03", "cenarios_01"],
        "the Cripta Partida, Pedreira dos Ecos and Ponte do Sino nodes look like their canonical environments; the selected-area card shows "
        "the Ponte do Sino with portraits of enemies from the enemy sheet and the Vigia do Sino boss from the boss sheet; any hero shown is the Warrior exactly as on his sheet",
    ),
    "10_hud_mockup": (
        ["02_guerreiro", "05_inimigos_ato1", "06_chefes_ato1", "11_icones"],
        ["ui_01", "ui_02", "ui_03", "cenarios_01"],
        "the player is the Warrior fighting the Guardiao da Cripta exactly as on the boss sheet, plus Sentinela Oca and Lanceiro Repetido enemies "
        "from the enemy sheet; the 6 skill slots show Warrior skill icons from the icon sheet (Corte de Ferro, Investida, Escudada, Fenda de Pedra, "
        "Postura Firme, Clamor de Aco); the hero portrait is the Warrior",
    ),
}

ids = sys.argv[5:] or list(PLAN)
result = []
for iid in ids:
    canons, sheets_, cast = PLAN[iid]
    it = dict(items[iid])
    it["prompt"] = it["prompt"] + identity(canons, cast)
    it["referencias"] = [canon(c) for c in canons] + [sheet(s) for s in sheets_]
    for r in it["referencias"]:
        assert os.path.exists(r), r
    result.append(it)
json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("ok", [(i["id"], len(i["referencias"])) for i in result])
