"""Gera prompts_sb.json: conteudo do roteiro Echoes of the Shatter, visual do Spell Brigade."""
import json, os, sys

P = sys.argv[1]  # pasta das pranchas
OUT = sys.argv[2]

STYLE = (
    "Create a finished, polished game illustration for the action-RPG \"Echoes of the Shatter\". "
    "VISUAL STYLE: match the visual style of the reference game shown in the attached reference sheets as closely as possible. "
    "The attached images are contact sheets of that game's assets: hand-painted UV texture atlases of its characters, creatures and environments, "
    "portrait atlases, spell icons, VFX sprites/textures, UI atlases, plus their normal maps (lilac), emission/glow maps (black with glowing areas), technical noise/gradient textures and logo marks (reference for finish only). Study them for rendering, palette, brushwork, materials, shape language and UI finish, "
    "then render our content as if it were made by the same art team. Do NOT output UV maps, texture atlases or a collage of the sheets; output one coherent finished image. "
    "Style traits to reproduce: stylized 3D game look, low-poly chunky bevelled forms whose volume is read through hand-painted textures with visible brush strokes and baked light/shadow plus soft rim light; "
    "chibi proportions about 3 to 3.5 heads tall, big readable head silhouettes, thin angular shoulders, distinct oversized props; "
    "friendly rounded heroes vs. angular segmented creatures with carapaces, spikes and golden eyes; warm/cool complementary colors (teal/cyan bodies, coral and sand armor plates, gold accents, deep maroon or navy shadows, never pure black), purple 'dark/corrupted' variants; "
    "magic as pure neon color with near-white cores and glow (fire orange-yellow, ice cyan-white, lightning electric blue, acid lime, dark purple), thin shapes like rings, diamonds and trails; "
    "each world has a saturated signature fog color, floors and props desaturated so characters and spells pop; top-down 3/4 perspective camera; "
    "UI made of dark organic stone: purple-grey bevelled stone buttons, black spiky organic frames around bars, lava-orange health fill, yellow highlights. "
    "CONTENT comes from our own game script below; all characters, creatures and places are ours: do not reproduce any specific existing character, creature, logo or game title from the reference one-to-one. "
    "No readable text, letters, numbers, watermark or logos; use abstract glyph-like marks where text would go.\n\nCONTENT: "
)


def sheets(*names):
    return [os.path.join(P, n + ".png").replace("\\", "/") for n in names]


ITEMS = [
    ("01_key_art", "Key art e folha de estilo", "1536x1024",
     "Key art. A small team of our three heroes (a stout Warrior with a big shield and hammer, a hooded Archer with a long bow, a scholar Mage with a lantern staff) "
     "standing on a ruined lantern-lined road, looking at the shattered floating towers of the Archive broken in the sky, a giant cracked bell silhouette, glowing golden memory shards drifting. "
     "Strip along the bottom with style swatches: color chips, a floor tile, a torch, an enemy telegraph circle on the ground, a loot light beam, a UI frame. Mood: adventurous with a melancholic edge.",
     sheets("magos_02", "inimigos_02", "cenarios_01", "vfx_01", "ui_02", "logos_01")),
    ("02_guerreiro", "Guerreiro - folha de personagem", "1536x1024",
     "Character sheet of the Warrior (Guerreiro, 'a wall that becomes a hammer'): broad armored fighter, kite shield with cracked stone inlay, heavy two-handed hammer, crimson tabard, iron and gold plate, a bold symbolic helmet shape as the head silhouette. "
     "Front, back and 3/4 turnaround, plus action poses: idle, walk, Corte de Ferro (iron slash), Investida (charging dash), Escudada (shield bash), Fenda de Pedra (ground fissure slam), Postura Firme (guard stance). Include a palette strip and 2 alternate skins (golden, prestige).",
     sheets("magos_01", "magos_02", "magos_03", "vfx_02")),
    ("03_arqueiro", "Arqueiro - folha de personagem", "1536x1024",
     "Character sheet of the Archer (Arqueiro, 'patient hunter who never misses'): lean figure, forest-green and leather outfit, hooded cowl with a bone mask as the head silhouette, long recurve bow, quiver with barbed arrows, feathered cloak, green Focus accent. "
     "Front, back and 3/4 turnaround, plus poses: idle, walk, Disparo Reto (straight shot), Flecha Fendida (arrow splitting in 3), Recuo Agil (backflip shot), Rede de Caca (net throw), Chuva de Farpas (arrow volley). Palette strip and 2 alternate skins.",
     sheets("magos_01", "magos_02", "magos_03", "vfx_03")),
    ("04_mago", "Mago - folha de personagem", "1536x1024",
     "Character sheet of the Mage (Mago, 'scholar who bends the Archive'): robed scholar whose head silhouette is a hood with a glass lantern glow inside, staff ending in a hanging lantern, ink-blue robe with gold library-seal embroidery, floating torn book pages, blue Mana accent. "
     "Front, back and 3/4 turnaround, plus poses: idle, walk, Faisca Guiada (homing spark), Lanca de Gelo (ice lance), Brasa Errante (ember ball), Barreira de Vidro (glass barrier), Raio do Arquivo / Pulso de Tempestade (chain lightning), Passagem Arcana (blink). Palette strip and 2 alternate skins.",
     sheets("magos_01", "magos_02", "magos_03", "vfx_04", "emissao_03")),
    ("05_inimigos_ato1", "Inimigos comuns do Ato I", "1536x1024",
     "Enemy lineup sheet for Act I, creatures are memories stuck in loops: Sentinela Oca (hollow empty armor soldier), Lanceiro Repetido (spear soldier), Cao-de-Cinza (ash hound), Corvo Imitador (masked crow), Arauto de Pedra (slow stone construct), "
     "Prensa Viva (living press machine), Arqueiro Fantasma (spectral archer), Lanca-Faiscas (spark thrower). Show each one with a normal, an elite (gold shield aura) and a purple dark/corrupted variant, plus a hit-flash frame and a death burst of golden shards.",
     sheets("inimigos_01", "inimigos_02", "inimigos_03", "vfx_05", "emissao_01")),
    ("06_chefes_ato1", "Chefes do Ato I", "1536x1024",
     "Boss sheet, 4 panels, each boss about 2.5x the height of a hero shown for scale, symmetric with multiple limbs and one glowing golden weak point: "
     "Guardiao da Cripta (giant knight still guarding an absent king, huge hammer, tower shield, hammer-swing cone telegraph on the floor), "
     "Tecela de Cascalho (stone spider that rebuilds bridge slabs with rubble webs), Carrasco do Voto (chained executioner marking a target with an oath glyph), "
     "Vigia do Sino (memory of the bell-keeper frozen at the moment of the Shatter, giant cracked bell). Each in its arena with a boss health bar frame.",
     sheets("inimigos_01", "inimigos_02", "inimigos_03", "vfx_06", "cenarios_02", "emissao_02")),
    ("07_cripta_tileset", "Cripta Partida - mapa e kit de cenario", "1536x1024",
     "Environment sheet for the first area, Cripta Partida (Broken Crypt). Left: a finished top-down 3/4 arena with a hero for scale: cracked chunky stone floor, broken sarcophagi, braziers, bone piles, pillars, stairway, a boss arena ring of carved runes, signature fog color in the corners, gold shard debris. "
     "Right: the modular kit laid out: floor tiles, wall pieces, pillars, props, destructibles, light sources.",
     sheets("cenarios_01", "cenarios_02", "vfx_07", "normais_01")),
    ("08_pedreira_ponte", "Pedreira dos Ecos e Ponte do Sino", "1536x1024",
     "Two Act I biomes, each as a finished top-down 3/4 scene plus a small kit of pieces. Top: Pedreira dos Ecos (Quarry of Echoes): terraced quarry, stacked stone blocks, wooden cranes, echoing crevasses, hazard cracks. "
     "Bottom: Ponte do Sino (Bell Bridge): narrow stone bridge over a chasm, bell tower, broken slabs, safe vs. unsafe floor clearly readable. Give each biome its own saturated fog color.",
     sheets("cenarios_01", "cenarios_02", "vfx_08")),
    ("09_vfx_habilidades", "Folha de VFX das habilidades", "1536x1024",
     "VFX sheet of our skills grouped in three rows by class, each effect shown in-world on a small floor patch with the hero casting it. "
     "Warrior: Corte de Ferro (short frontal arc slash), Investida (dash with impact ring), Escudada (shield bash shockwave), Fenda de Pedra (cone of stone fissures with dust). "
     "Archer: Disparo Reto, Flecha Fendida (splits in 3), Chuva de Farpas (volley area), Rede de Caca (net trap). "
     "Mage: Faisca Guiada (homing electric spark), Lanca de Gelo, Brasa Errante (ember ball), Barreira de Vidro, Pulso de Tempestade (chain lightning). "
     "Bottom row: enemy telegraphs for contrast (warm opaque ground circles and cones) and a loot beam.",
     sheets("vfx_01", "vfx_05", "vfx_06", "vfx_07", "vfx_08", "vfx_09", "tecnicos_01", "tecnicos_02")),
    ("10_hud_mockup", "Mockup de HUD em jogo", "1536x1024",
     "In-game screenshot mockup: the Warrior fighting the Guardiao da Cripta boss and some Act I enemies in the Broken Crypt, top-down 3/4 camera. "
     "HUD: bottom bar with life orb, class resource bar, 6 skill slots, a dodge slot with 3 charges, 2 potion slots; top-left hero portrait with thin bars; top-right minimap; top-center segmented boss health bar; floating damage glyphs; a loot light beam; a boss telegraph on the floor.",
     sheets("ui_01", "ui_02", "ui_03", "icones_01", "cenarios_01")),
    ("11_icones", "Icones de habilidades e itens", "1024x1024",
     "Icon sheet in a grid on a dark background. First rows, skill icons for: Corte de Ferro, Investida, Escudada, Fenda de Pedra, Postura Firme, Clamor de Aco, Disparo Reto, Flecha Fendida, Recuo Agil, Marca da Trilha, Chuva de Farpas, Rede de Caca, "
     "Faisca Guiada, Lanca de Gelo, Brasa Errante, Barreira de Vidro, Passagem Arcana, Pulso de Tempestade. Next rows, item icons: helm, chest armor, gloves, boots, belt, ring, amulet, sword, hammer, shield, bow, staff, potion, skill book, sigil, Marco de Retorno charge. "
     "Frames colored by element and rarity.",
     sheets("icones_01", "ui_02", "ui_03", "vfx_09")),
    ("12_mapa_mundi", "Mapa-mundi / selecao de area do Ato I", "1536x1024",
     "World-map and area-selection screen for Act I of the land of Aural: 8 locations linked by a road: Estrada das Lanternas, Cripta Partida, Pedreira dos Ecos, Ponte do Sino, Armazem de Cinzas, Patio dos Marcos, Tuneis do Voto, Mirante Partido. "
     "Each node is a small 3D diorama landmark; locked nodes greyed, conquered ones with a Marco de Retorno flag, boss nodes with a bell emblem; shattered floating Archive towers on the horizon. "
     "Right panel: selected-area card with an illustrated vignette, enemy portraits and reward slots, and a big stone Start button.",
     sheets("ui_01", "ui_02", "ui_03", "cenarios_01", "cenarios_02", "magos_02", "logos_01")),
]

data = [{"id": i, "titulo": t, "tamanho": s, "prompt": STYLE + c, "referencias": r} for i, t, s, c, r in ITEMS]
for d in data:
    for r in d["referencias"]:
        assert os.path.exists(r), r
used = {os.path.basename(r) for d in data for r in d["referencias"]}
allsheets = {f for f in os.listdir(P) if f.endswith(".png") and True}
print("pranchas nao usadas:", sorted(allsheets - used))
json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("ok", len(data))
