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
    "p03_vegetacao_seca": [
        "tree_dry_large", "tree_dry_orange", "tree_dry_thin", "tree_dry_pile", "tree_dry_leaning", "tree_dry_small",
        "bush_dry_round", "bush_dry_thorny", "shrub_dry_tall", "bush_dry_wide", "bush_dry_tangled", "bush_dry_red",
        "grass_dry_tall", "grass_dry_patch", "reeds_dry", "ferns_withered", "thistles_dry", "flowers_dead",
        "leaves_pile", "leaves_scattered", "log_fallen", "branches_fallen", "vines_dry_rock", "leaves_bone"],
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

def tira_fragmentos_de_borda(cel):
    """Apaga pedaços pequenos colados na borda do recorte (restos do vizinho)."""
    a = np.array(cel)
    lab, n = ndimage.label(a[..., 3] > 0, structure=np.ones((3, 3)))
    if n < 2:
        return cel
    areas = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    grande = max(areas)
    for i, ar in enumerate(areas, 1):
        m = lab == i
        if ar < 0.1 * grande and (m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any()):
            a[m, 3] = 0
    return Image.fromarray(a, "RGBA")

# folhas em que os props não respeitam a grade de 256 px
POR_COMPONENTE = {"p03_vegetacao_seca"}

def por_componente(im, juncao=8):
    """Separa os props por agrupamento de pixels (ordem: linha a linha, esquerda para a direita)."""
    a = np.array(im)
    sol = a[..., 3] > 0
    lab, n = ndimage.label(ndimage.binary_dilation(sol, iterations=juncao))
    lab = np.where(sol, lab, 0)
    objs = ndimage.find_objects(lab)
    itens = []
    for i, sl in enumerate(objs, 1):
        if sl is not None and (lab == i).sum() >= 1500:
            itens.append((sl[0].stop, sl[1].start, i))
    itens.sort()  # pela linha de base; depois cada linha de 6 vai da esquerda para a direita
    centros, n_linhas, por_linha = itens, 4, 6
    saida = []
    for r in range(n_linhas):
        linha = sorted(centros[r * por_linha:(r + 1) * por_linha], key=lambda t: t[1])
        for _, _, i in linha:
            b = np.zeros_like(a)
            m = lab == i
            b[m] = a[m]
            saida.append(Image.fromarray(b, "RGBA"))
    return saida

def main(brutos, saida_props, saida_ini):
    os.makedirs(saida_props, exist_ok=True)
    os.makedirs(saida_ini, exist_ok=True)
    for f in sorted(os.listdir(brutos)):
        if not f.endswith(".png"):
            continue
        id_ = f[:-4]
        im = chave(Image.open(os.path.join(brutos, f)))
        if id_ in NOMES and id_ in POR_COMPONENTE:
            for nome, cel in zip(NOMES[id_], por_componente(im)):
                cel.crop(cel.getbbox()).save(os.path.join(saida_props, f"{nome}.png"))
        elif id_ in NOMES:
            for i, nome in enumerate(NOMES[id_]):
                c, l = i % 6, i // 6
                cel = im.crop((c * 256 + 3, l * 256 + 3, c * 256 + 253, l * 256 + 253))
                cel = tira_fragmentos_de_borda(cel)
                bb = cel.getbbox()
                if bb:
                    cel.crop(bb).save(os.path.join(saida_props, f"{nome}.png"))
        else:
            im.save(os.path.join(saida_ini, f"{id_}.png"))

if __name__ == "__main__":
    main(*sys.argv[1:4])
