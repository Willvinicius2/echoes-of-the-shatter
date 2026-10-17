"""Rodada de 17/10/2026: Guerreiro Raro (m10), kit de UI (ui_kit_01) e icones de itens (icones_itens_01).

Gera prompts_rodada17.json (uso com gerar.py).
Saida das imagens: D:/openclaude/_trabalho-claude/echoes-arte/geradas_rodada_17
Uso: prompts_rodada17.py [pasta aprovadas] [pasta pranchas do Spell Brigade] [saida.json]
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
A = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "aprovadas")
P = sys.argv[2] if len(sys.argv) > 2 else r"D:\openclaude\_trabalho-claude\echoes-arte\pranchas"
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "..", "prompts_rodada17.json")


def ap(*n):
    return os.path.abspath(os.path.join(A, *n[:-1], n[-1] + ".png")).replace("\\", "/")


def sb(n):
    return os.path.join(P, n + ".png").replace("\\", "/")


COMUM_MODELO = (
    "Plain flat uniform light grey background (#C8C8C8), no floor, no cast shadow, no scenery, no text, no labels, no numbers, no grid lines, no frame, no UI, no VFX. "
    "Even neutral lighting so the colors read as albedo, only soft painted shading. "
    "Finished stylized 3D game model look: sculpted, rounded, chunky bevelled volumes with smooth silhouettes and hand-painted textures with visible brush strokes; "
    "never blocky primitives, cubes or a graybox. Do not reproduce any existing character from the style reference one-to-one."
)

M10 = (
    "CHARACTER MODEL SHEET of the Warrior of the action-RPG \"Echoes of the Shatter\" wearing the RARE armor set (second modular set, for owner approval). "
    "CONSISTENCY (mandatory): attached image 1 is the approved modeling sheet of the Warrior with the starting set; attached image 2 is his approved bare base body with the approved face; "
    "attached image 3 is the canonical design sheet. Draw the SAME character: the same body, the same chibi proportions (about 3 heads tall), the same height, head size, build, A-pose and ground line, "
    "and the same face as image 2 (visible only through the helmet opening: keep the same dark visor opening as image 1). "
    "Only the equipment changes. Attached images 4 to 6 are style references of stylized 3D mage heroes of another game: only finish and brushwork, copy nothing from them. "
    "THE RARE SET must read as clearly different in SILHOUETTE from image 1 at a glance, but still be the same hero (red, steel and gold): "
    "1 HELMET: a different helmet, golden visor with a taller swept-back gold fin and a wide TRANSVERSE crest of red plume running from ear to ear across the top "
    "(a fan crest seen from the front as a wide red arc, instead of the single front-to-back plume of image 1), small gold wing-shaped cheek plates; the red plume is still the class mark. "
    "2 SHOULDERS: much LARGER layered pauldrons, two or three overlapping steel plates each with a gold rim and a raised gold rivet, rising above the shoulder line, so the upper body is visibly wider than image 1. "
    "3 BODY: heavier steel breastplate with more metal coverage (steel gorget, ribbed plates on the chest and belly), gold edge lines and a central gold sunburst emblem. "
    "4 TABARD AND CAPE: the red tabard (front and back) now has rich GOLD EMBROIDERY (#FFD24A thread: border scrolls, a sunburst and small shard motifs) and a short red cape with a gold-embroidered hem behind the shoulders; "
    "this cloth is where the rarity gold shows. The Warrior red stays the dominant cloth color. "
    "5 GAUNTLETS: heavier steel gauntlets with gold rims and spiked knuckle guards, longer cuffs. "
    "6 LEGS AND BOOTS: bigger steel thigh and knee guards with gold trim, steel greaves over the boots, brown leather boots with gold buckles and metal toe caps. "
    "More metal overall than image 1, gold (#FFD24A) only on details (trims, rivets, embroidery, emblem), nothing glowing. The hands are EMPTY: no weapon, no shield, no props. "
    "LAYOUT exactly like image 1: three full-body views side by side in three equal-width columns, left to right FRONT view, RIGHT SIDE profile view, BACK view; orthographic look, same scale, aligned on the same ground line, "
    "whole body inside each column with a clear margin. Neutral A-pose: standing straight, arms angled about 40 degrees away from the body, legs slightly apart. "
)

UI_KIT = (
    "UI KIT SHEET (elements for 9-slice cutting) for the dark-fantasy action-RPG \"Echoes of the Shatter\". "
    "CONSISTENCY (mandatory): attached images 1 to 3 are our approved UI screens and HUD: copy exactly their UI language, dark violet-grey organic stone (#2A222F body, #161117 recessed gaps, #0F0B14 outlines, rim light #6A606E), "
    "thorny corners with small crystals, a thin gold filigree line (#D9A441, highlight #FCD58A), bevelled hand-painted stone, warm top-left light. "
    "Attached image 4 is the approved icon sheet (slot frames with a small gem at the bottom center). Attached images 5 and 6 are UI sheets of another game, style/finish reference only, copy none of their elements. "
    "Draw one clean sheet on a flat uniform mid grey background (#808080) with NO scenery. Each element is ISOLATED, fully visible, orthographic front view, not touching others, with wide grey space around it; "
    "the CENTER of every panel, slot, button and tab is a flat, plain, empty stone fill (no ornament, no pattern, no icon) so it can stretch; "
    "all ornament lives only in the four corners (thorns, crystals, gold filigree) while the straight edges are plain and uniform (same thickness along the whole edge). "
    "NO text, no letters, no numbers, no glyph marks, no characters, no icons inside, no watermark. "
    "LAYOUT, three rows. "
    "ROW 1 (large panels): left, 1 ORNATE PANEL FRAME (square, thick stone border, thorns, crystals and gold filigree in the corners, double gold inner line); right, 1 PLAIN PANEL FRAME (square, thin bevelled stone border, chamfered corners, no gold, no thorns). "
    "ROW 2 (item slots, equal squares): EXACTLY FIVE slots in a row, left to right, with a clear gap between them. Slot 1 is the plain EMPTY SLOT (bevelled dark stone square, dark recessed #120E16 void, NO colored rim, NO corner ornament, and NO gem at all, the most neutral and humble one). Slots 2 to 5 are the four RARITY BORDER slots, each with a dark void and a small gem at the bottom center in the rarity color: "
    "NORMAL (plain bevelled grey stone corner, white-grey rim #C9C4CC), MAGIC (blue #6FA8FF rim, a simple small filigree curl on each corner), RARE (gold #FFD24A rim, DOUBLE corners: two stacked bevelled corner brackets), "
    "UNIQUE (orange #FF8A2E rim, sharp THORNY spiked corners with a thin gold line and a soft orange glow). The four rarities must differ by corner SHAPE as well as color. "
    "ROW 3 (controls, wide rectangles of the same size): NORMAL button (stone plate, light on the top edge, shadow at the bottom, thin gold line), HOVER button (same plate, brighter, gold #FCD58A rim and a warm glow), "
    "DISABLED button (same plate, desaturated dark grey, no gold, flat); then 1 TAB (a stone tab shape with bevelled top corners and an open bottom, selected look with a gold top line) "
    "and 1 TITLE BAR (a wide thin stone strip with small thorny end caps and a gold line, empty center). "
)

ICONES = (
    "ITEM ICON SHEET for the action-RPG \"Echoes of the Shatter\", a grid of exactly 12 icons in 4 columns by 3 rows, equal square cells with even gaps, on a flat dark violet-grey background (#2A222F). "
    "Each icon is one hand-painted square illustration with its own very dark violet-black background (#161117) filling the whole square, the single object centered and occupying at most 60% of the square, "
    "warm light from the upper left, violet shadows, no pure black, readable when reduced to 48 px, NO frame, NO border, NO gem, NO text, NO numbers, no hand or character. "
    "CONSISTENCY (mandatory): attached image 1 is our approved icon sheet (the bottom two rows hold the item icons): copy the same painting style, saturation, gold trims, steel grey and red cloth of the Warrior set, the chunky bevelled hand-painted look. "
    "Attached image 2 is the Warrior design sheet and attached image 3 the Warrior starting armor pieces: the armor icons are exactly those pieces. Attached images 4 and 5 show the weapon design (stone block hammer) and the Crypt Guardian. "
    "The 12 icons, row by row, left to right: "
    "ROW 1: (1) a short iron SWORD, straight steel blade with a small gold cross guard and a red grip, pointing diagonally up-right; "
    "(2) a STONE MAUL, a big hammer with a grey stone block head with a small gold star inlay on a wooden shaft with red wrap; "
    "(3) the golden visor HELMET with a red plume, three-quarter front; "
    "(4) a plain brown LEATHER VEST, simple stitched brown leather jerkin with a belt and a couple of rivets, no plates, dull and worn. "
    "ROW 2: (5) a pair of brown leather GLOVES, simple, with small stitched cuffs; "
    "(6) a pair of WORN BOOTS, scuffed brown leather boots, patched, plain; "
    "(7) a pair of WORN TROUSERS, patched dark brown cloth trousers with a rope belt, plain, shown flat; "
    "(8) the UNIQUE item of the Crypt Guardian, the Maul of the Empty Throne: a big dark carved-stone hammer whose head is shaped like a small empty throne with a crown, thorny edges with gold lines and a single glowing ORANGE (#FF8A2E) ember rune on the head, a few orange sparks, a thin orange glow around it. This is the only icon with an orange glow. "
    "ROW 3: (9) a round glass POTION of Life: red liquid (#E0301E tones), cork, brown leather strap, warm highlight; "
    "(10) a POTION of Ward (Resguardo): a tall slim glass flask with luminous blue-white liquid and a small gold shield-shaped charm on its neck, cork stopper; "
    "(11) GOLD: a small pile of gold coins with a few coins standing on edge, warm gold highlights; "
    "(12) SHARDS (Lascas): three or four pale-blue memory crystal shards in a small cluster, angular, with a cool light core. "
    "Common items are drab and humble, only the unique glows. The two potions use distinct colors and silhouettes (round red flask vs tall slim blue flask) so they never get confused. "
)

REFS_M10 = [ap("modelagem", "m01_guerreiro"), ap("modelagem", "mod_b01_guerreiro_corpo"), ap("02_guerreiro"),
            sb("magos_01"), sb("magos_02"), sb("magos_03")]
REFS_UI = [ap("telas", "t02_inventario"), ap("telas", "t04_expedicao"), ap("10_hud_mockup"), ap("11_icones"), sb("ui_01"), sb("ui_02")]
REFS_ICO = [ap("11_icones"), ap("02_guerreiro"), ap("modelagem", "mod_a01_guerreiro_inicial"), ap("modelagem", "m09_armas"), ap("06_chefes_ato1")]

ITENS = [
    ("m10_guerreiro_raro", "Guerreiro: conjunto Raro", "1536x1024", M10 + COMUM_MODELO, REFS_M10),
    ("ui_kit_01", "Kit de UI para 9-slice", "1536x1024", UI_KIT, REFS_UI),
    ("icones_itens_01", "Icones de itens (12)", "1536x1024", ICONES, REFS_ICO),
]

result = []
for iid, titulo, tam, prompt, refs in ITENS:
    for r in refs:
        assert os.path.exists(r), r
    result.append({"id": iid, "titulo": titulo, "tamanho": tam, "prompt": prompt, "referencias": refs})

json.dump(result, open(OUT, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
print("ok", len(result), "->", os.path.abspath(OUT))
