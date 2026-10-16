"""Monta pranchas-mosaico com todas as texturas do Spell Brigade, por categoria."""
import json, os, re, sys
from PIL import Image, ImageDraw

ROOT = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)

ENEMY = r"fleshcrab|tripod|toad|stinkbug|squid|spitter|snipjaw|sneakybug|hydra|crabling|babyworm|teethy|static|spawner|shieldcrab|pregnantcrab|mole|hoarder|flying|explodingtick|eventmob|mobevent|crablodon|buffer|armou?r|ghost|mushroom|order|hunt|exploding|grunt|egg|manta|worm|crab|tick|boss"
MAGE = r"mage|smithy|wizardking|reginald|ludwig|hatty|campanel|portraits|rewards_wizards|rewards_skins|emotes|staff|player|running"
ICON = r"ui_atlas_spells|rewards_spells|rewards_elements|rewards_artifacts|rewards_missions|stat_icons|artifacts|objectives_icons|missions_icons|improvements|enchantments|badges|title_icons|challenges|curse_level|^artifact|^heart|pickup|^cards"
VFX = r"^ps_|^tx_|meteor|lightning|^fire|^ice|^acid|^dark|fallingstar|sawblade|summon|dice|clap|^book|^bell|rifle|shotgun|smg|laser|^plant|trail|smoke|blast|spark|slash|snow|frostflake|circle|telegraph|^arrow_|^spel|bolt|^hit|splash|convergen|bounce|^cone|cracking|^push|snap|^line|^thin|^medium|^large|^dot|^leaf|^spots|^cross|respawn|geyser|teleporter|^ldr|^save"
WORLD = r"world|background|sacrifice|bricks|statue|window|halloween|candle|campfire|crater|deathbush|herding|floor|rock|volcano|coral|foilage|lobby_|baked|reflectionprobe|cubemap|skybox"
UI = r"^ui_|start_menu|splash_screen|logo|healthbar|button|progresscircle|pingcircle|dropdown|checkmark|check|^arrow-|remove|uifoldout|uielement"
TECH = r"noise|gradient|bayer|areatex|searchtex|white1px|defaultparticle|defaultmaterial|defaultdot|console\.|emojione|font|sans|titillium|roboto|amiri|irishgrover|liberation|debug|cleaner|^fs0"


def cat(rel):
    n = os.path.basename(rel).lower()[:-4]
    if n.endswith("_n"):
        return "normais"
    if n.endswith("_em"):
        return "emissao"
    if re.search(TECH, n):
        return "tecnicos"
    if re.search(r"^logo", n):
        return "logos"
    for name, rx in (("icones", ICON), ("magos", MAGE), ("inimigos", ENEMY), ("vfx", VFX), ("cenarios", WORLD), ("ui", UI)):
        if re.search(rx, n):
            return name
    return "outros"


files = []
for dp, _, fs in os.walk(ROOT):
    for f in fs:
        if f.lower().endswith((".png", ".jpg", ".tga")):
            files.append(os.path.join(dp, f))
groups = {}
excluded = []
for p in sorted(files):
    low = p.lower()
    groups.setdefault(cat(os.path.relpath(p, ROOT)), []).append(p)

CELL, COLS, LABEL = 256, 8, 14
manifest = {"excluidos_mapas_tecnicos_n_em": len(excluded), "categorias": {}}
for g, ps in sorted(groups.items()):
    sheets = []
    per = COLS * COLS
    for s in range(0, len(ps), per):
        chunk = ps[s:s + per]
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new("RGB", (CELL * COLS, (CELL + LABEL) * rows), (40, 38, 44))
        d = ImageDraw.Draw(sheet)
        for i, p in enumerate(chunk):
            try:
                im = Image.open(p)
                im.draft("RGB", (CELL, CELL))
                im = im.convert("RGBA")
            except Exception as e:
                print("falha", p, e)
                continue
            im.thumbnail((CELL - 4, CELL - 4))
            x, y = (i % COLS) * CELL, (i // COLS) * (CELL + LABEL)
            bg = Image.new("RGB", im.size, (70, 66, 76))
            bg.paste(im, mask=im.split()[3])
            sheet.paste(bg, (x + 2 + (CELL - 4 - im.width) // 2, y + LABEL + 2 + (CELL - 4 - im.height) // 2))
            d.text((x + 3, y + 1), os.path.basename(p)[:-4][:38], fill=(230, 220, 120))
        name = f"{g}_{s // per + 1:02d}.png"
        sheet.save(os.path.join(OUT, name), optimize=True)
        sheets.append(name)
    manifest["categorias"][g] = {"arquivos": len(ps), "pranchas": sheets}
    print(g, len(ps), sheets, flush=True)
json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("excluidos (_n/_em):", len(excluded))
