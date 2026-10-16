"""Prompts do complemento: terrenos, areas do Ato I que faltam, mapas e inimigos do endgame.

Uso: prompts_complemento.py <prompts_base.json> <pranchas> <saida.json> <pasta_canon>... -- <ids...>
As pastas canon sao procuradas em ordem (aprovadas primeiro, depois as geradas nesta rodada).
"""
import json, os, sys

args = sys.argv[1:]
sep = args.index("--")
base, P, out = args[0], args[1], args[2]
canon_dirs = args[3:sep]
ids = args[sep + 1:]
STYLE = json.load(open(base, encoding="utf-8"))[0]["prompt"].split("CONTENT: ")[0] + "CONTENT: "

ROLE = {
    "02_guerreiro": "the canonical Warrior sheet (golden visor helmet with red plume, red tabard, stone-inlay kite shield, stone block hammer)",
    "03_arqueiro": "the canonical Archer sheet (green hood with bone beak mask, feathered green cloak, bone recurve bow)",
    "04_mago": "the canonical Mage sheet (ink-blue pointed hood with visible face, wooden staff with a floating blue crystal in a gold ring, no lantern)",
    "05_inimigos_ato1": "the canonical Act I enemy sheet",
    "06_chefes_ato1": "the canonical Act I boss sheet (Guardiao da Cripta top-left, Tecela de Cascalho top-right, Carrasco do Voto bottom-left, Vigia do Sino bottom-right)",
    "07_cripta_tileset": "the canonical Broken Crypt environment and kit (reference for environment rendering and kit layout)",
    "08_pedreira_ponte": "the canonical Quarry and Bell Bridge environments",
    "21_terrenos_ato1": "the canonical Act I terrain material sheet (one row per area)",
    "22_terrenos_endgame": "the canonical endgame terrain and hazard sheet",
    "23_inimigos_endgame": "the canonical endgame enemy sheet (3 enemies per endgame map)",
}

SCENE = ("Environment sheet in the same layout as the canonical crypt kit: left, a finished top-down 3/4 playable area with the named hero for scale "
         "and a few enemies; right, the modular kit laid out (floor tiles, walls, props, destructibles, light sources, interactables). ")

ITEMS = {
    # etapa 1: bases
    "21_terrenos_ato1": ("1024x1536", "Terrenos do Ato I",
        "Terrain material sheet for all 8 Act I areas: 8 rows, one per area, each with 4 square seamless tileable top-down ground swatches "
        "(base ground, variation, path/edge transition, special or hazard ground). Rows in order: Estrada das Lanternas (packed dirt road, grass tufts, warm lantern light); "
        "Cripta Partida (cracked grey flagstones with gold inlay); Pedreira dos Ecos (pale quarry stone, sand, glowing hazard cracks); Ponte do Sino (bridge cobbles, chasm edge); "
        "Armazem de Cinzas (wooden planks under ash, ember spots); Patio dos Marcos (ceremonial paving with carved runes); Tuneis do Voto (rough tunnel rock, mine rails, sigil glow); "
        "Mirante Partido (cliff rock, cloud edge, floating fragments). Hand-painted, chunky, readable from the top-down game camera.",
        ["07_cripta_tileset", "08_pedreira_ponte"], ["cenarios_01", "cenarios_02", "normais_01", "tecnicos_01"], "terrain swatches only, no characters"),
    "22_terrenos_endgame": ("1536x1024", "Terrenos do endgame e perigos",
        "Terrain and hazard sheet for the 3 endgame maps: 4 rows of 4 square seamless tileable top-down swatches. Row 1 Ossario do Marco (deep crypt: bone-paved floor, ossuary tiles, crumbling grave soil, cursed purple seep). "
        "Row 2 Trilha de Cinza (dead forest: ash soil, burnt roots, ember-dotted leaves, smouldering ground). Row 3 Salao do Martelo (abandoned workshop: iron floor plates, metal grates, soot stone, molten channel). "
        "Row 4 hazard ground decals shared by all maps: enemy telegraph circle, cone, line, persistent fire pool, poison/acid pool, fog patch.",
        ["07_cripta_tileset"], ["cenarios_01", "cenarios_02", "normais_01", "vfx_07", "vfx_08", "tecnicos_02"], "terrain swatches only, no characters"),
    "23_inimigos_endgame": ("1536x1024", "Inimigos do endgame",
        "Enemy lineup sheet for the endgame, same layout and rendering as the canonical Act I enemy sheet: each enemy shown in normal, elite (gold halo) and purple corrupted variants, "
        "plus a hit-flash frame and a golden-shard death burst. 9 NEW enemies, 3 per map, that must look clearly different from the Act I enemies: "
        "Ossario do Marco: Eco de Soldado (translucent soldier echo with a broken spear), Porta-Escudo (huge tower-shield echo elite), Rastejante de Ossos (bone crawler). "
        "Trilha de Cinza: Lobo-de-Brasa (fast ash wolf with ember mane), Cervo Queimado (burnt stag that charges), Gralha Atiradora (crow that spits ember shots). "
        "Salao do Martelo: Constructo Bigorna (anvil-bodied armored construct), Martelador (armored hammer automaton), Fornalha Ambulante (walking furnace that explodes).",
        ["05_inimigos_ato1"], ["inimigos_01", "inimigos_02", "inimigos_03", "emissao_01", "emissao_02"], "enemies only, no heroes"),
    # etapa 2: areas e chefe
    "13_estrada_lanternas": ("1536x1024", "Estrada das Lanternas",
        SCENE + "Area: Estrada das Lanternas (levels 1-2, tutorial). A ruined countryside road at dusk lined with hanging bell-lanterns, low stone walls, broken carts, small milestone shrines, open readable paths.",
        ["02_guerreiro", "05_inimigos_ato1", "07_cripta_tileset", "21_terrenos_ato1"], ["cenarios_01", "vfx_01"],
        "the hero is the Warrior; enemies are Sentinela Oca and Cao-de-Cinza from the Act I enemy sheet; ground uses the Estrada row of the terrain sheet"),
    "14_armazem_cinzas": ("1536x1024", "Armazem de Cinzas",
        SCENE + "Area: Armazem de Cinzas (levels 7-9, optional loot area). Abandoned storehouse full of ash heaps, stacked crates, locked treasure chests with glowing seals, collapsed roof beams with light shafts, hoists and chains.",
        ["03_arqueiro", "05_inimigos_ato1", "07_cripta_tileset", "21_terrenos_ato1"], ["cenarios_02", "emissao_03"],
        "the hero is the Archer; gold-halo elite enemies from the Act I enemy sheet guard the chests; ground uses the Armazem row of the terrain sheet"),
    "15_patio_marcos": ("1536x1024", "Patio dos Marcos",
        SCENE + "Area: Patio dos Marcos (levels 9-11). Ceremonial courtyard with tall carved waystones (Marcos de Retorno) in a ring, oath pillars wrapped in chains, the Trial of the Marker dais, and the boss arena of the Carrasco do Voto.",
        ["04_mago", "06_chefes_ato1", "05_inimigos_ato1", "21_terrenos_ato1"], ["cenarios_01", "vfx_06"],
        "the hero is the Mage facing the Carrasco do Voto exactly as on the boss sheet; ground uses the Patio row of the terrain sheet"),
    "16_tuneis_voto": ("1536x1024", "Tuneis do Voto",
        SCENE + "Area: Tuneis do Voto (levels 11-13, the longest dungeon). Narrow carved tunnels, chained doors, alcoves holding rare glowing sigils, mine rails, side chambers; add a small abstract top-down layout inset showing the branching dungeon.",
        ["02_guerreiro", "05_inimigos_ato1", "07_cripta_tileset", "21_terrenos_ato1"], ["cenarios_02", "normais_01"],
        "the hero is the Warrior; enemies are Lanceiro Repetido, Arqueiro Fantasma and Prensa Viva from the Act I enemy sheet; ground uses the Tuneis row of the terrain sheet"),
    "17_mirante_partido": ("1536x1024", "Mirante Partido",
        SCENE + "Area: Mirante Partido (levels 13-15, final area of Act I). A shattered clifftop belvedere above the clouds, floating broken Archive fragments, the giant cracked bell tower, and the final boss arena of the Vigia do Sino.",
        ["03_arqueiro", "06_chefes_ato1", "08_pedreira_ponte", "21_terrenos_ato1"], ["cenarios_01", "vfx_05"],
        "the hero is the Archer facing the Vigia do Sino exactly as on the boss sheet; ground uses the Mirante row of the terrain sheet"),
    "18_ossario_marco": ("1536x1024", "Ossario do Marco (endgame)",
        SCENE + "Endgame map: Ossario do Marco, a deep crypt below the Broken Crypt: bone walls, ossuary niches, darker colder lighting, a Route Stone pedestal (Pedra de Rota) at the entrance and glowing tracks of the endgame boss on the floor.",
        ["02_guerreiro", "23_inimigos_endgame", "22_terrenos_endgame", "07_cripta_tileset"], ["cenarios_02", "emissao_01"],
        "the hero is the Warrior; enemies are Eco de Soldado, Porta-Escudo and Rastejante de Ossos from the endgame enemy sheet; ground uses row 1 of the endgame terrain sheet"),
    "19_trilha_cinza": ("1536x1024", "Trilha de Cinza (endgame)",
        SCENE + "Endgame map: Trilha de Cinza, a dead ash forest: grey burned trees, ember fog, fallen logs, hunting trails, a Route Stone pedestal and glowing tracks of the endgame boss.",
        ["03_arqueiro", "23_inimigos_endgame", "22_terrenos_endgame"], ["cenarios_01", "vfx_03", "vfx_09"],
        "the hero is the Archer; enemies are Lobo-de-Brasa, Cervo Queimado and Gralha Atiradora from the endgame enemy sheet; ground uses row 2 of the endgame terrain sheet"),
    "20_salao_martelo": ("1536x1024", "Salao do Martelo (endgame)",
        SCENE + "Endgame map: Salao do Martelo, an abandoned giant forge-workshop: anvils, giant hammers on chains, conveyor chains, molten channels, a Route Stone pedestal and glowing tracks of the endgame boss.",
        ["04_mago", "23_inimigos_endgame", "22_terrenos_endgame"], ["cenarios_02", "vfx_04", "emissao_02"],
        "the hero is the Mage; enemies are Constructo Bigorna, Martelador and Fornalha Ambulante from the endgame enemy sheet; ground uses row 3 of the endgame terrain sheet"),
    "24_predador_marcos": ("1536x1024", "Predador dos Marcos (chefe do endgame)",
        "Boss sheet of the endgame boss Predador dos Marcos: a beast made of hunting memories that roams between the three endgame maps, wolf-and-stag hybrid of fog and bone plates with small marker stones embedded, one glowing golden weak point. "
        "Show: big front and side views, phase poses (stalking/hunting the player, vanishing into fog, telegraphed charge with a long ground line telegraph), its 3 glowing tracks that open the arena, and a panel of the arena fight with the hero for scale and a segmented boss health bar.",
        ["02_guerreiro", "23_inimigos_endgame", "22_terrenos_endgame"], ["inimigos_01", "inimigos_02", "vfx_06", "emissao_03"],
        "the hero for scale is the Warrior; the boss must be a new design, clearly different from the Act I bosses and the endgame enemies"),
}


def find(name):
    for d in canon_dirs:
        p = os.path.join(d, name + ".png")
        if os.path.exists(p):
            return p.replace("\\", "/")
    raise SystemExit("canon nao encontrado: " + name)


result = []
for iid in ids:
    size, title, content, canons, sheets, cast = ITEMS[iid]
    refs = [find(c) for c in canons] + [os.path.join(P, s + ".png").replace("\\", "/") for s in sheets]
    for r in refs:
        assert os.path.exists(r), r
    lines = [f"attached image {k + 1} is {ROLE[c]}" for k, c in enumerate(canons)]
    prompt = (STYLE + content + "\n\nCONSISTENCY (mandatory): " + "; ".join(lines) + ". Every hero, enemy, boss, terrain or environment piece that comes from "
              "those canonical sheets must be copied exactly (same silhouette, proportions, colors, outfit, weapon, materials). In this image: " + cast + ".")
    result.append({"id": iid, "titulo": title, "tamanho": size, "prompt": prompt, "referencias": refs})
json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("ok", [(i["id"], len(i["referencias"])) for i in result])
