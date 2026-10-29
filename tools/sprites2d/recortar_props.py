"""Recorta as folhas de props (6x4) em PNGs soltos e tira o fundo magenta das folhas de inimigos.

Uso: python recortar_props.py <pasta_brutos> <saida_props> <saida_inimigos>
"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage

NOMES = {
    "p01_pilares_pedras_arvores": [
        "pillar_runes", "pillar_tall", "pillar_thick", "pillar_cracked", "pillar_broken", "pillar_fallen",
        "rock_large", "rock_cluster", "rock_mossy", "rock_crystal", "rock_slabs", "rock_rubble",
        "tree_dead_large", "tree_dead_medium", "tree_dead_webs", "tree_dead_leaning", "tree_stump", "tree_hollow",
        "bush_thorny", "roots_clump", "shrub_withered", "tree_teal_leaves", "tree_skull", "sapling_dead"],
    "p02_tumbas_caveiras": [
        "grave_round", "grave_slab", "sarcophagus_closed", "sarcophagus_open", "grave_broken", "tomb_angel",
        "grave_dirt_cross", "mausoleum_door", "coffin_lid_leaning", "altar_candles", "grave_fence", "tomb_flowers",
        "skull_single", "skull_pair", "skull_pile", "skull_spike", "bones_ribcage", "bones_scattered",
        "skeleton_curled", "skeleton_hand", "ribcage_arch", "skull_mound_candles", "skull_teal_eyes", "bones_chains"],
}

def chave(img):
    a = np.asarray(img.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # magenta puro (#FF00FF) e seus tons de borda; roxo do desenho tem azul/vermelho menores
    fundo = (r > 170) & (b > 170) & (g < 120) & (abs(r - b) < 70)
    fundo = ndimage.binary_dilation(fundo, iterations=1) & (r > 110) & (b > 110) & (g < r - 50) & (g < b - 50) & (abs(r - b) < 90)
    out = np.dstack([a, np.where(fundo, 0, 255)]).astype(np.uint8)
    # erode 1px o contorno para sumir com o halo rosado
    alfa = ndimage.binary_erosion(out[..., 3] > 0, iterations=1)
    out[..., 3] = np.where(alfa, 255, 0)
    # linhas escuras da grade nas bordas da folha
    out[:, ::256][:, :, 3] = 0
    return Image.fromarray(out, "RGBA")

def main(brutos, saida_props, saida_ini):
    os.makedirs(saida_props, exist_ok=True)
    os.makedirs(saida_ini, exist_ok=True)
    for f in sorted(os.listdir(brutos)):
        if not f.endswith(".png"):
            continue
        id_ = f[:-4]
        im = chave(Image.open(os.path.join(brutos, f)))
        if id_ in NOMES:
            for i, nome in enumerate(NOMES[id_]):
                c, l = i % 6, i // 6
                cel = im.crop((c * 256 + 3, l * 256 + 3, c * 256 + 253, l * 256 + 253))
                bb = cel.getbbox()
                if bb:
                    cel.crop(bb).save(os.path.join(saida_props, f"{nome}.png"))
        else:
            im.save(os.path.join(saida_ini, f"{id_}.png"))

if __name__ == "__main__":
    main(*sys.argv[1:4])
