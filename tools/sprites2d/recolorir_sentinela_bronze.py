"""Sentinela Oca em bronze escurecido para a Ponte do Sino (pedido dos revisores): recolore as folhas do hollow_sentinel
(comum e elite) trocando o dourado da armadura por bronze velho com pátina azul-esverdeada nas juntas, e escurecendo o vermelho
do penacho e do estandarte. Uma troca de cor por cor de paleta (sem pixel novo, sem custo): a saída é determinística.

Uso: python3 tools/sprites2d/recolorir_sentinela_bronze.py [pasta_saida]
Escreve godot/art2d/sprites/hollow_sentinel/hollow_sentinel_bronze[_elite]_<anim>.png (ver data2d/sprites_manifest.csv e arte_fase_2d.csv)."""
import colorsys
import os
import sys
import numpy as np
from PIL import Image

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
PASTA = os.path.join(RAIZ, 'godot', 'art2d', 'sprites', 'hollow_sentinel')
ANIMS = ['idle', 'run', 'attack', 'hit', 'death']


def trocar(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h360 = h * 360.0
    if s < 0.08:   # preto, cinza e osso: só um pouco mais frios
        r, g, b = r * 0.94, g * 0.97, min(1.0, b * 1.06)
    elif h360 < 14 or h360 > 340:   # vermelho do penacho e do estandarte: vinho escuro
        r, g, b = colorsys.hsv_to_rgb(h, s * 0.75, v * 0.62)
    else:   # dourado: bronze velho, mais escuro e menos saturado; os tons mais escuros ganham pátina azul-esverdeada
        nh = (22.0 + (h360 - 24.0) * 0.4) / 360.0
        ns = min(1.0, s * 1.05)
        nv = v * 0.7
        r, g, b = colorsys.hsv_to_rgb(nh, ns, nv)
        if v < 0.42:
            k = (0.42 - v) / 0.42 * 0.4
            r, g, b = r * (1 - k) + 0.16 * k, g * (1 - k) + 0.30 * k, b * (1 - k) + 0.30 * k
    return tuple(int(round(max(0.0, min(1.0, c)) * 255)) for c in (r, g, b))


def main():
    saida = sys.argv[1] if len(sys.argv) > 1 else PASTA
    os.makedirs(saida, exist_ok=True)
    for pref in ('hollow_sentinel', 'hollow_sentinel_elite'):
        for anim in ANIMS:
            im = np.array(Image.open(os.path.join(PASTA, '%s_%s.png' % (pref, anim))).convert('RGBA'))
            cores = {tuple(c) for c in np.unique(im[im[..., 3] > 0][:, :3], axis=0).tolist()}
            mapa = {c: trocar(c) for c in cores}
            out = im.copy()
            for y, x in zip(*np.where(im[..., 3] > 0)):
                out[y, x, :3] = mapa[tuple(int(c) for c in im[y, x, :3])]
            nome = pref.replace('hollow_sentinel', 'hollow_sentinel_bronze') + '_%s.png' % anim
            Image.fromarray(out, 'RGBA').save(os.path.join(saida, nome))
            print(nome)


if __name__ == '__main__':
    main()
