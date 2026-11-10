"""Folhas de contato das folhas finais (conferência; não entram no Git)."""
import sys
import numpy as np
from PIL import Image, ImageDraw

DIRS = ['S', 'SE', 'E', 'NE', 'N']


def contato(arquivos, saida, lado=92, Z=2, fundo=(58, 56, 62, 255), recorte=(8, 6, 86, 84), pivo_y=74, rot=True):
    """Uma folha de contato com as animações lado a lado (colunas) e as 5 direções em linhas."""
    folhas = [np.array(Image.open(f).convert('RGBA')) for f in arquivos]
    x0, y0, x1, y1 = recorte
    w, h = (x1 - x0) * Z, (y1 - y0) * Z
    cols = sum(f.shape[1] // lado for f in folhas)
    img = Image.new('RGBA', (cols * w + 4 * (len(folhas) - 1), 5 * h), fundo)
    d = ImageDraw.Draw(img)
    cx = 0
    for f in folhas:
        n = f.shape[1] // lado
        for r in range(5):
            for c in range(n):
                q = f[r * lado:(r + 1) * lado, c * lado:(c + 1) * lado]
                im = Image.fromarray(q[y0:y1, x0:x1], 'RGBA').resize((w, h), Image.NEAREST)
                img.alpha_composite(im, (cx + c * w, r * h))
                d.line([(cx + c * w, r * h + (pivo_y - y0 + 1) * Z), (cx + (c + 1) * w, r * h + (pivo_y - y0 + 1) * Z)], fill=(255, 255, 255, 36))
                if rot and r == 0:
                    d.text((cx + c * w + 2, 2), str(c), fill=(255, 255, 0, 255))
            if rot and cx == 0:
                d.text((2, r * h + 12), DIRS[r], fill=(0, 255, 255, 255))
        cx += n * w + 4
    img.save(saida)
    return img.size


if __name__ == '__main__':
    # uso: python3 contato.py <pasta_das_folhas> <pasta_de_saida>   (conferência; as imagens não entram no Git)
    pasta, saida = sys.argv[1], sys.argv[2]
    b = pasta + '/ash_hound_'
    print(contato([b + 'run.png'], saida + '/prev_run.png'))
    print(contato([b + 'attack.png'], saida + '/prev_attack.png'))
    print(contato([b + 'idle.png', b + 'hit.png'], saida + '/prev_idle_hit.png'))
    print(contato([b + 'death.png'], saida + '/prev_death.png'))
