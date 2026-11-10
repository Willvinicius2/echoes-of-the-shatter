"""Monta as folhas do Carcereiro do Ossuário (176 px, 5 direções por folha: S, SE, E, NE, N em linhas) a partir de animacao.py.
Cada quadro vem de um modelo 3D de pedra feito por código (carcereiro.py) desenhado por render.py em pixel art, sem serviço pago.
Confere: alfa binário, paleta curta, quadros vazios e folga de borda.

Uso: python3 tools/sprites2d/carcereiro_do_ossuario/montar_folhas.py [pasta_saida] [anim,anim]   (padrão: godot/art2d/sprites/ossuary_warden)
Use `python3` simples (não `-I`: o script importa os módulos vizinhos). A saída é determinística (sementes fixas)."""
import os
import sys
from multiprocessing import Pool
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animacao as A
import render as R

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
SAIDA = os.path.join(RAIZ, 'godot', 'art2d', 'sprites', 'ossuary_warden')
MARGEM = 2          # folga mínima entre o desenho e a borda do quadro, em px
MAX_CORES = 24      # paleta do conjunto (pedra 5, musgo 4, terra 4, olho 4, pupila, linha, contorno e o fundo)


def _quadro(args):
    nome, f, d = args
    fn, n, fps, loop = A.ANIMS[nome]
    return A.quadro(fn(f, n), A.YAW[d])


def montar(saida, anims=None):
    os.makedirs(saida, exist_ok=True)
    Q = R.QUADRO
    problemas = []
    relatorio = {}
    with Pool(max(1, min(os.cpu_count() or 1, 8))) as pool:
        for nome, (fn, n, fps, loop) in A.ANIMS.items():
            if anims and nome not in anims:
                continue
            jobs = [(nome, f, d) for d in A.ORDEM for f in range(n)]
            imgs = pool.map(_quadro, jobs)
            folha = np.zeros((Q * len(A.ORDEM), Q * n, 4), np.uint8)
            xmin, ymin, xmax, ymax = Q, Q, 0, 0
            for (nm, f, d), im in zip(jobs, imgs):
                r = A.ORDEM.index(d)
                folha[r * Q:(r + 1) * Q, f * Q:(f + 1) * Q] = im
                ys, xs = np.where(im[..., 3] > 0)
                if len(ys) == 0:
                    problemas.append('%s %s quadro %d vazio' % (nome, d, f))
                    continue
                xmin, ymin, xmax, ymax = min(xmin, xs.min()), min(ymin, ys.min()), max(xmax, xs.max()), max(ymax, ys.max())
                if xs.min() < MARGEM or ys.min() < MARGEM or xs.max() > Q - 1 - MARGEM or ys.max() > Q - 1 - MARGEM:
                    problemas.append('%s %s quadro %d chega à borda (%d,%d)-(%d,%d)' % (nome, d, f, xs.min(), ys.min(), xs.max(), ys.max()))
            Image.fromarray(folha, 'RGBA').save(os.path.join(saida, 'ossuary_warden_%s.png' % nome))
            alfas = set(np.unique(folha[..., 3]).tolist())
            if not alfas <= {0, 255}:
                problemas.append('%s tem alfa que não é binário: %s' % (nome, sorted(alfas)))
            cores = len(np.unique(folha[folha[..., 3] > 0][:, :3], axis=0))
            if cores > MAX_CORES:
                problemas.append('%s usa %d cores (máximo %d)' % (nome, cores, MAX_CORES))
            relatorio[nome] = dict(quadros=n, fps=fps, loop=loop, caixa=(int(xmin), int(ymin), int(xmax), int(ymax)), cores=cores)
    return relatorio, problemas


if __name__ == '__main__':
    saida = sys.argv[1] if len(sys.argv) > 1 else SAIDA
    anims = sys.argv[2].split(',') if len(sys.argv) > 2 else None
    rel, problemas = montar(saida, anims)
    for k, v in rel.items():
        print(k, v)
    if problemas:
        print('PROBLEMAS:')
        for p in problemas:
            print(' ', p)
        sys.exit(1)
    print('ok:', saida)
