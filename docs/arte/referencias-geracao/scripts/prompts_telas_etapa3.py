"""Gera prompts_telas_etapa3.json: mockups das telas principais da Etapa 3 (docs/design/16_etapa3_fluxo.md).

Telas: S-01 tela inicial, S-05 inventario e equipamento, S-06 tooltip comparando, S-08 expedicao, S-09 relatorio.
Uso: prompts_telas_etapa3.py [pasta aprovadas] [pasta pranchas do Spell Brigade] [saida.json]
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
A = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "aprovadas")
P = sys.argv[2] if len(sys.argv) > 2 else r"D:\openclaude\_trabalho-claude\echoes-arte\pranchas"
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "..", "prompts_telas_etapa3.json")


def ap(n):
    return os.path.abspath(os.path.join(A, n + ".png")).replace("\\", "/")


def sb(n):
    return os.path.join(P, n + ".png").replace("\\", "/")


REFS = [ap("10_hud_mockup"), ap("11_icones"), ap("02_guerreiro"), sb("ui_01"), sb("ui_02"), sb("ui_03")]

BASE = (
    "Create a finished, polished UI screen mockup (full-screen game UI design, 3:2 layout) for the action-RPG \"Echoes of the Shatter\". "
    "CONSISTENCY (mandatory): attached image 1 is our approved HUD mockup and attached image 2 is our approved icon sheet: use exactly the same UI language, "
    "dark violet-grey organic stone frames (#2A222F body, #161117 gaps, #0F0B14 outlines) with thorny corners, a thin gold filigree line (#D9A441, highlight #FCD58A), "
    "bevelled stone buttons, lava-orange/crimson fills for life, amber for resource, and the same icon painting style (dark #161117 icon background, gold-framed squares with a small gem at the bottom). "
    "Attached image 3 is the canonical Warrior sheet (golden visor helmet with red plume, red tabard, stone-inlay kite shield, stone block hammer): any hero shown is that Warrior exactly. "
    "Attached images 4 to 6 are UI sheets of another game, only a style reference for finish and brushwork; do not copy any of their elements. "
    "Hand-painted, chunky bevelled shapes, warm gold accents only where it matters, never pure black, strong readable hierarchy, clear contrast between panels and content. "
    "NO readable text, no letters, no real numbers, no watermark: wherever text or numbers would be, draw abstract glyph-like marks, short rune-like dashes and tiny pictograms. "
    "Rarity is shown by frame shape and color: common plain bevelled corner, magic blue (#6FA8FF) simple corner filigree, rare gold (#FFD24A) double corners, unique orange (#FF8A2E) thorny corners with glow. "
    "SCREEN: "
)

ITEMS = [
    ("t01_tela_inicial", "S-01 Tela inicial",
     "MAIN MENU. Full-screen painted background of the Marco Refuge at night: a small walled camp of dark stone ruins with warm lanterns and a campfire, a glowing golden memory-shard "
     "crystal in the middle-right, shattered floating towers and a giant cracked bell silhouette in a deep violet-blue sky. "
     "Top center: a large carved-stone game logo plate made of bold rune-like shapes (no readable letters) with a cracked gold shard motif. "
     "Center column, below the logo: exactly FIVE separate wide bevelled stone buttons stacked vertically with clear gaps between them, each a single plain horizontal button with gold filigree and a tiny glyph icon at the left and rune-dash label marks: "
     "1 Continue (slightly larger, bright gold focus ring and warm glow, with a small round gold badge carrying a scroll icon overlapping its top-right corner meaning expedition ready), 2 New game, 3 Options (gear icon), 4 Credits (star icon), 5 Quit (door icon). Do not draw any portrait inside the buttons. "
     "SEPARATE from the buttons, at the left of the screen: a stand-alone save card in its own stone frame (not touching the buttons) with the Warrior bust portrait in a stone medallion and three short glyph lines (name, class and level, area). "
     "Bottom-left a tiny logs-folder icon link, bottom-right a small version glyph string. Cinematic, calm, adventurous with a melancholic edge."),
    ("t02_inventario", "S-05 Inventario e equipamento",
     "INVENTORY AND EQUIPMENT (paper doll). Dark dimmed backdrop. Center-left: the Warrior as a full-body modular 3D character, standing in a neutral idle pose on a small round carved stone pedestal "
     "with a soft golden spotlight behind him, wearing the starting set (golden visor helmet with red plume, chest armor with red tabard, gauntlets, armored pants, boots, stone hammer in the main hand, stone-inlay kite shield in the off hand, "
     "a thin curved arrow icon below him hinting that he can be rotated by dragging). "
     "Around the hero, exactly 10 equipment slots in stone square frames with a small gem at the bottom. "
     "SIX ACTIVE slots with gold trim and a painted item icon in the style of the icon sheet: left column top to bottom: helmet (head), chest armor (body), gauntlets (hands), armored pants (legs), boots (feet); right column top: hammer (main hand). "
     "FOUR LOCKED slots, clearly dimmed and desaturated, dark stone, no gold trim, no item, a small grey padlock icon in the center and a faint ghost silhouette behind it: right column below the hammer, top to bottom: kite shield silhouette (off hand), amulet, ring, second ring. The hero still carries his shield on the arm visually, but its slot is locked. Active and locked slots must differ at a glance. "
     "Right side: a large stone panel with the backpack grid of 8 columns by 5 rows of square item slots (40 slots), about 12 filled with varied painted item icons (weapons, armor pieces, potions, materials) with rarity corner marks (common, magic blue, rare gold, one unique orange thorny), "
     "one item highlighted by a bright gold hover frame with a small green up-arrow in its corner and another with a small red down-arrow; a slot-count glyph strip under the grid. "
     "Below the grid: a compact stats block with 8 rows of small icon + glyph-dash value (life, armor, damage per second, crit, attack speed, move speed, fire resistance, regeneration), "
     "and a resources row with gold coin, shard and charge icons. Tabs at the top of the right panel (backpack, shared chest) as small stone tabs with icons. Close button as a small stone X at the top-right corner of the panel."),
    ("t03_tooltip_comparacao", "S-06 Tooltip comparando com o equipado",
     "ITEM TOOLTIP COMPARISON, clean. Background: only a heavily dimmed and blurred dark stone inventory screen, NO HUD, NO life or resource orbs, NO skill bar, NO tab bar. "
     "Center: exactly two tall tooltip cards side by side with a small gap, equal height and same layout, centered on screen. "
     "LEFT card: the currently equipped item, a common helmet, plain bevelled stone frame, a small 'equipped' tab with a check glyph at its top edge, white-grey name made of glyph marks, a painted helmet icon in a stone square frame, a type line, one base property line, two short affix lines in grey, level line, no price. "
     "RIGHT card: the new item, a rare helmet, double gold corner frame, gold-colored two-line name of glyph marks, larger painted helmet icon with a soft glow, rarity/type line, base property line, four affix lines in soft blue glyph strokes with small value marks, level line, small price line with a gold coin. "
     "INSIDE both cards, in a stats section under the affixes, matching stat rows (armor, life, damage, speed, resistance), each row: a tiny stat icon, a glyph value mark, and on the right card a clear bright green up-triangle for better, a red down-triangle for worse, one grey dash for equal, so both columns can be compared row by row at a glance. "
     "A single key-hint footer strip centered under the two cards with three keycap icons (mouse right button, Shift, Alt) and glyph labels. "
     "Hierarchy: item name, icon and the green and red arrows read first."),
    ("t04_expedicao", "S-08 Expedicao: rota, regras de IA e tempo",
     "EXPEDITION SETUP. A large stone panel centered on a dimmed Refuge workshop background. Top-left corner: portrait medallion of Ilsa, the Refuge quartermaster, an ordinary workshop woman in a brown leather apron with rolled sleeves, hair tied back, a small lit lantern hanging from her belt; NOT hooded, no green cloak, no bow. "
     "Header strip: Marco charges as a row of 12 small crystal pips (8 lit gold, 4 dark) and a stamina gauge. "
     "Left column: ONE single area card only, a painted thumbnail of the Broken Crypt (dark crypt arena with braziers and a cracked stone floor), gold filigree selection frame, small level-range glyph and boss-skull mark; no second thumbnail anywhere. "
     "Under it a row of 3 objective toggle buttons with icons (experience star, gold coin, materials pile), one selected with gold ring. "
     "Center column: the AI rules list, 6 stacked horizontal stone rows, each with an order handle, a condition chip (icon like heart with percent mark), an arrow glyph, an action chip (potion icon or a Warrior skill icon from the icon sheet), up/down arrow buttons and a delete X; "
     "rows 1 to 4 filled, row 5 empty with a gold dashed outline and plus icon, row 6 empty dim. "
     "Bottom of the center: a wide duration slider from 1 to 12 hours with tick marks, gold knob at about 8, track in three zones (green, amber, red-orange), clock icon at the left. "
     "Right column: a forecast card inside the panel (no big picture on it), titled by a glyph line, containing four clearly separated forecast rows, each with an icon at the left and a horizontal RANGE BAR with a pale filled band between a low and a high end marker: experience (star), gold (coin), rare items (4 small gem icons, 'up to 4'), retreat risk (skull with warning icon). "
     "The round gold-rimmed 'Estimate' stamp seal (hourglass and wavy-line emblem, no letters) sits INSIDE the forecast card, fully contained within the card edges with a clear margin of stone on all four sides, placed in the card's header row beside the title glyph line, never overlapping or crossing the card border. "
     "Bottom-right: a big primary stone button with gold glow (start expedition), a smaller plain Cancel button to its left, and a small padlock icon next to them."),
    ("t05_relatorio", "S-09 Relatorio da expedicao com selo Estimativa",
     "EXPEDITION REPORT. A large stone panel centered over a dimmed Refuge background. At the left, Tico (a small cheerful messenger courier character in a brown satchel and cap, running pose) "
     "stands in a stone medallion with a scroll in hand. Header: a stone title plate of glyph marks and, next to it, a round gold-rimmed 'Estimate' stamp seal (hourglass and wavy-line emblem, no letters), clearly visible. "
     "Top row: 6 summary tiles in stone frames, each with a painted icon and glyph value marks: effective time (hourglass with a segmented bar mostly full), encounters won (crossed swords), potions used (red and blue flasks), "
     "stop reason (a calm flag icon, neutral color), experience (star) and gold (coin pile). Under them a thin per-hour receipt strip made of 8 small bars of different heights. "
     "Middle: the loot grid: rare items first as three large slots with double gold corners and glowing icons, then magic items with blue simple corners in a second row, then one wide long slot with a stack icon for aggregated common items and a materials/gold line. "
     "A tip card with a lightbulb icon and glyph lines at the lower left with a small 'adjust rule' button; an invitation card with a portal icon and glyph lines at the lower middle with a 'play this route now' button. "
     "Bottom-right: two buttons, a large primary gold-glowing 'collect all' stone button and a secondary 'collect and new expedition' button with a loop-arrow icon. Tone: calm and rewarding, no red for small quantities."),
]

result = []
for iid, titulo, desc in ITEMS:
    for r in REFS:
        assert os.path.exists(r), r
    result.append({"id": iid, "titulo": titulo, "tamanho": "1536x1024", "prompt": BASE + desc, "referencias": REFS})

json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("ok", len(result), "->", os.path.abspath(OUT))
