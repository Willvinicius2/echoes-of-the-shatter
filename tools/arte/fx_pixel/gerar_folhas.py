#!/usr/bin/env python3
"""Gera as folhas de VFX em pixel art das skills a partir do patch-gg/pixelfx (MIT).

Uso: python3 tools/arte/fx_pixel/gerar_folhas.py <pasta-do-clone-pixelfx> [saida]
  git clone --depth 1 https://github.com/patch-gg/pixelfx <pasta>   (precisa de Node 18+)
Para cada efeito de EFEITOS: renderiza com `node tools/render.mjs --sheet --fps 12 --no-actor --bg none`, corta todos os quadros
pela caixa de conteúdo, tira 1 de cada `passo` quadros, e reempacota numa folha com grade. Escreve:
  <saida>/<id>.png e <saida>/catalogo.json (quadros, tamanho, colunas, fps, âncoras em px do quadro cortado).
O catálogo é lido por godot/scripts2d/fx_pixel_2d.gd (copie o JSON para a const CATALOGO ou deixe o loader ler o arquivo).
"""
import glob, json, math, subprocess, sys
from PIL import Image

# id do jogo -> (categoria/efeito do pixelfx, passo de quadros, máximo de quadros)
EFEITOS = {
    "thunderclap": ("lightning/thunderclap", 1, 99), "storm_cloud": ("lightning/storm-cloud", 1, 99),
    "lightning_strike": ("lightning/lightning-strike", 1, 14), "ball_lightning": ("lightning/ball-lightning", 1, 99),
    "spore_burst": ("nature/spore-burst", 1, 99), "poison_cloud": ("nature/poison-cloud", 1, 99), "acid_splash": ("nature/acid-splash", 1, 99),
    "ice_lance": ("ice/ice-lance", 1, 99), "ice_spikes": ("ice/ice-spikes", 1, 99), "blizzard_vortex": ("ice/blizzard-vortex", 1, 99),
    "fire_breath": ("fire/fire-breath", 1, 99), "fire_ring": ("fire/fire-ring", 1, 99), "barrel_explosion": ("explosions/barrel-explosion", 1, 16),
}

def main():
    raiz = sys.argv[1]
    saida = sys.argv[2] if len(sys.argv) > 2 else "godot/art2d/fx/pixel"
    tmp = "/tmp/pixelfx_render"
    cat = {}
    for gid, (fx, passo, maxq) in EFEITOS.items():
        subprocess.run(["node", "tools/render.mjs", fx, "--sheet", "--fps", "12", "--no-actor", "--bg", "none", "--out", tmp],
                       cwd=raiz, check=True, capture_output=True)
        nome = fx.split("/")[1]
        j = json.load(open(glob.glob(f"{tmp}/*/{nome}/{nome}.json")[0]))
        im = Image.open(glob.glob(f"{tmp}/*/{nome}/{nome}.png")[0]).convert("RGBA")
        fr = j["frames"][::passo][:maxq]
        caixas, quadros = None, []
        for f in fr:
            r = f["frame"]
            q = im.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
            quadros.append(q)
            bb = q.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
            if bb:
                caixas = bb if caixas is None else (min(caixas[0], bb[0]), min(caixas[1], bb[1]), max(caixas[2], bb[2]), max(caixas[3], bb[3]))
        quadros = [q.crop(caixas) for q in quadros]
        w, h = quadros[0].size
        cols = max(1, min(len(quadros), int(math.ceil(math.sqrt(len(quadros) * h / w)))))
        linhas = math.ceil(len(quadros) / cols)
        folha = Image.new("RGBA", (cols * w, linhas * h), (0, 0, 0, 0))
        for i, q in enumerate(quadros):
            folha.paste(q, ((i % cols) * w, (i // cols) * h))
        folha.save(f"{saida}/{gid}.png", optimize=True)
        cat[gid] = {"n": len(quadros), "w": w, "h": h, "cols": cols, "fps": round(12.0 / passo, 1)}
        print(gid, cat[gid])
    json.dump(cat, open(f"{saida}/catalogo.json", "w"), indent=1)

if __name__ == "__main__":
    main()
