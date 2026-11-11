"""Folhas de contato das aranhas da Ponte do Sino para revisão (fora do Git): uma faixa por direção, quadros lado a lado.

Uso: python3 tools/sprites2d/tecela_de_cascalho/contato.py <tecela|filhote> <anim> <direcoes|todas> <escala> <arquivo_png>"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animacao as A


def faixa(variante, nome, direcoes, esc=2, fundo=(58, 64, 78, 255)):
    ar = A.aranha(variante)
    fn, n, fps, loop = ar.anims[nome]
    Q = ar.cfg['quadro']
    quadros = [[ar.quadro(fn(f, n), A.YAW[d]) for f in range(n)] for d in direcoes]
    todos = np.concatenate([np.stack(r) for r in quadros])
    ys, xs = np.where(todos[..., 3].max(0) > 0)
    x0, y0, x1, y1 = max(xs.min() - 4, 0), max(ys.min() - 4, 0), min(xs.max() + 5, Q), min(ys.max() + 5, Q)
    w, h = (x1 - x0) * esc, (y1 - y0) * esc
    sheet = Image.new('RGBA', (w * n, h * len(direcoes)), fundo)
    for r, row in enumerate(quadros):
        for f, im in enumerate(row):
            fr = Image.fromarray(im, 'RGBA').crop((x0, y0, x1, y1)).resize((w, h), Image.NEAREST)
            sheet.alpha_composite(fr, (f * w, r * h))
    d = ImageDraw.Draw(sheet)
    for f in range(n):
        d.text((f * w + 3, 3), str(f), fill=(255, 255, 0, 255))
    return sheet


if __name__ == '__main__':
    variante, nome = sys.argv[1], sys.argv[2]
    dirs = A.ORDEM if sys.argv[3] == 'todas' else sys.argv[3].split(',')
    faixa(variante, nome, dirs, int(sys.argv[4])).save(sys.argv[5])
    print(sys.argv[5])
