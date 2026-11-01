"""Gera prompts_arqueiro_attack.json: uma faixa de 6 quadros por direção (redesenho da folha attack, docs/arte/33 seção 2.1).
Uso: python gerar_prompts_attack.py <saida.json>"""
import json, sys
BASE = ("Create a game-ready 2D SPRITE STRIP for the top-down action-RPG 'Echoes of the Shatter' (Godot; high top-down 3/4 view, ~55 degrees pitch). "
 "Hand-painted stylized 2D, chunky readable shapes, dark outline 2-3px, light from top-left, SAME paint style, palette and outline as the attached idle sheet. "
 "CHARACTER: copy EXACTLY the attached reference turnaround and idle sheet: young archer, messy golden-brown hair, green tunic with brown leather straps and shoulder pad, olive trousers, brown boots and bracers, leather quiver of green-fletched arrows on the back, ornate wooden recurve bow held in the LEFT hand. "
 "Flat solid pure magenta (#FF00FF) background, NO ground shadow, NO scenery, NO text, NO grid lines, no glow halo. "
 "ONE horizontal row of exactly 6 equal cells, same sprite scale in every cell, feet on the same baseline, character centered, nothing crossing cell borders, never cut the hair. "
 "Frames left to right: 1 reach to quiver and take the arrow, 2 nock the arrow, 3 draw the string (arrow nocked), 4 full draw at anchor (arrow nocked, pointing exactly at the target direction), "
 "5 RELEASE: string snapped forward and still vibrating, the arrow is GONE (no arrow anywhere, no flying arrow, no motion streak), bow hand still aimed, "
 "6 bow arm coming back down, relaxed recover. "
 "The BOW and the arrow must always point toward the aim direction given below, in all 6 frames from the nock on. ")
DIRS = [
 ("s",  "AIM DIRECTION = straight DOWN the screen, toward the camera (character faces the viewer, South). Bow seen from the front, almost a flattened circle in front of the chest; bow arm extended toward the camera; the arrow tip points down the screen (foreshortened)."),
 ("se", "AIM DIRECTION = DOWN-RIGHT (South-East, 3/4 front view). The bow is tilted toward the lower right and the arrow runs diagonally down-right."),
 ("e",  "AIM DIRECTION = RIGHT (East, pure side profile). Vertical bow, horizontal arrow pointing right."),
 ("ne", "AIM DIRECTION = UP-RIGHT (North-East, 3/4 back view). The bow is tilted toward the upper right and the arrow runs diagonally up-right; head slightly raised."),
 ("n",  "AIM DIRECTION = straight UP the screen, away from the camera (character seen from behind, North). The bow is seen from behind, above the shoulders: only the top limb and the tips of the bow show; the arrow points up the screen (foreshortened)."),
]
REFS = ["docs/arte/sprites2d/arqueiro/refs/turnaround_arqueiro.png", "godot/art2d/sprites/arqueiro/arqueiro_idle.png"]
out = [{"id": f"att_{k}", "tamanho": "1536x1024", "referencias": REFS, "prompt": BASE + d} for k, d in DIRS]
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
