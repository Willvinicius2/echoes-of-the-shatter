"""Gera prompts.json da árvore de veneno. Rodar com docs/arte/referencias-geracao/scripts/gerar.py (Codex + gpt-image)."""
import json, sys
REF = [r"D:\openclaude\_trabalho-claude\arte-ui\docs\arte\sprites2d\capturas_cripta\sala1.png"]
BASE = ("A horizontal sprite sheet of {n} animation frames in a single row, evenly spaced, each frame in its own square cell of identical size (the row is vertically centered in the canvas), "
        "on a flat solid magenta (#FF00FF) background, no grid lines, no text, no watermark. Hand-painted dark fantasy ARPG visual effect, "
        "top-down 3/4 view, painterly with a thin dark outline, light from the upper left, rich toxic green (#7ddc3c) with yellow-green highlights and dark teal shadows, "
        "soft bubbles and wisps, NOT pixel art, no clay look, no glow bleeding outside its cell, effect centered in each cell. Subject: {s}")
FOLHAS = {
 "fx_veneno_flecha": (6, "a LARGE, THICK arrow projectile flying to the right that fills most of its cell width: clearly readable wooden shaft, a big broad steel arrowhead dripping bright green venom, visible feathered fletching at the tail, thick toxic green glow and a short bubbling trail, looping animation with slight venom drip changes between frames", "1536x1024"),
 "fx_veneno_impacto": (8, "a poison impact burst: green splash that expands, droplets and small bubbles, then fades into thin mist", "1536x1024"),
 "fx_veneno_bola": (6, "a glowing sphere of toxic venom thrown upward: round blob of swirling green liquid with bubbles, wobbling, with small drips, looping; the sphere is large and fills about 80% of its cell, keeping a strong bright inner glow", "1536x1024"),
 "fx_veneno_poca": (8, "a top-down puddle of toxic acid on the ground, viewed from above at a slight angle: bubbling green pool with popping bubbles and thin rising vapor, ring-shaped irregular edge, looping seamlessly", "1536x1024"),
 "fx_veneno_nuvem": (8, "a toxic gas cloud burst on the ground: green cloud puffs outward from the center with skull-shaped wisps hinted in the smoke, expands and dissolves at the end", "1536x1024"),
 "fx_veneno_chuva": (8, "a large area of corrosive green rain: slanted acid droplets falling over a circular patch of the ground that is splashing and eaten by acid, looping seamlessly", "1536x1024"),
 "fx_veneno_status": (6, "an overlay for a poisoned enemy: dense clusters of many bright green bubbles and drops of different sizes rising upward around the body, with thick sickly green vapor wisps, high contrast and clearly visible, NOT a thin ring; the middle column stays mostly empty so the body shows through, looping", "1536x1024"),
 "fx_veneno_arauto_aura": (6, "a faint aura around a hero: thin swirling ring of green miasma with two tiny skull-like wisps orbiting, mostly transparent in the center, looping", "1536x1024"),
 "fx_veneno_arauto_gatilho": (8, "a plague burst: a green cloud expands outward in a ring with spores and little skulls of mist, spreading to the sides, then dissipates", "1536x1024"),
}
ICONES = {
 "icone_poison_arrow": "an arrow with a dripping green venom tip leaving a small green splash",
 "icone_venom_orb": "a round bubbling sphere of green venom with an upward arc trail and drips",
 "icone_corrosive_rain": "a dark cloud above with slanted green acid drops and a corroded puddle below",
 "icone_herald_plague": "a green skull of mist with spores spreading outward like a ring",
}
ICONE_BASE = ("A single square video-game ability icon for a dark fantasy top-down ARPG, hand-painted with crisp detail, matching the rich painterly style of the attached game screenshot. "
 "Composition: the tile fills the entire square canvas edge to edge. Outer frame is a beveled dark stone and iron border with a thin worn gold inner line and four small rivets, slightly rounded corners. "
 "Inside, a dark stone background with soft vignette and a green glow halo behind the central glyph. The glyph is large, centered, readable at 64px, strong light from top-left, shading, dark outline. "
 "No text, no letters, no watermark, no flat plastic look, no clay look. Glyph: {s}. Use EXACTLY the same stone-and-iron frame as the second attached icon.")
ICONE_REF = r"D:\openclaude\_trabalho-claude\arte-ui-work\icones\icone_tiro.png"
out = []
for k, (n, s, tam) in FOLHAS.items():
    out.append({"id": k, "tamanho": tam, "prompt": BASE.format(n=n, s=s), "referencias": REF})
for k, s in ICONES.items():
    out.append({"id": k, "tamanho": "1024x1024", "prompt": ICONE_BASE.format(s=s), "referencias": REF + [ICONE_REF]})
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "prompts.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
