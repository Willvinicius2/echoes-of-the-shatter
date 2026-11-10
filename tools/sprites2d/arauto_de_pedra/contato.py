"""Folhas de contato do Arauto de Pedra para revisão (fora do Git): uma faixa por direção, quadros lado a lado, recortada ao desenho.

Uso: python3 tools/sprites2d/arauto_de_pedra/contato.py <anim> <direcoes|todas> <escala> <arquivo_png>
  anim: idle, run, attack, hit ou death; direcoes: S,SE,E,NE,N separadas por vírgula (ou `todas`); escala: inteiro (2 serve)."""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animacao as A
import render as R


def faixa(nome, direcoes, esc=2, fundo=(44, 46, 52, 255)):
    fn, n, fps, loop = A.ANIMS[nome]
    Q = R.QUADRO
    quadros = [[A.quadro(fn(f, n), A.YAW[d]) for f in range(n)] for d in direcoes]
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
    nome = sys.argv[1]
    dirs = A.ORDEM if sys.argv[2] == 'todas' else sys.argv[2].split(',')
    faixa(nome, dirs, int(sys.argv[3])).save(sys.argv[4])
    print(sys.argv[4])
