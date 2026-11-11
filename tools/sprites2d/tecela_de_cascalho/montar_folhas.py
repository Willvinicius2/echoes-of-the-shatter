"""Monta as folhas das aranhas da Ponte do Sino (5 direções por folha: S, SE, E, NE, N em linhas) a partir de animacao.py:
a Tecelã de Cascalho (`bell_weaver`, quadro de 256 px) e o Filhote de Cascalho (`gravel_spiderling`, quadro de 96 px).
Cada quadro vem de um modelo 3D feito por código (aranha.py) desenhado por render.py em pixel art, sem serviço pago.
Confere: alfa binário, paleta curta, quadros vazios e folga de borda.

Uso: python3 tools/sprites2d/tecela_de_cascalho/montar_folhas.py [tecela|filhote|todas] [anim,anim] [pasta_saida]
Use `python3` simples (não `-I`: o script importa os módulos vizinhos). A saída é determinística (sementes fixas)."""
import os
import sys
from multiprocessing import Pool
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animacao as A

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
IDS = {'tecela': 'bell_weaver', 'filhote': 'gravel_spiderling'}
MARGEM = 2          # folga mínima entre o desenho e a borda do quadro, em px
MAX_CORES = 24


def _quadro(args):
    variante, nome, f, d = args
    ar = A.aranha(variante)
    fn, n, fps, loop = ar.anims[nome]
    return ar.quadro(fn(f, n), A.YAW[d])


def montar(variante, anims=None, saida=None):
    ident = IDS[variante]
    saida = saida or os.path.join(RAIZ, 'godot', 'art2d', 'sprites', ident)
    os.makedirs(saida, exist_ok=True)
    ar = A.aranha(variante)
    Q = ar.cfg['quadro']
    problemas, relatorio = [], {}
    with Pool(max(1, min(os.cpu_count() or 1, 8))) as pool:
        for nome, (fn, n, fps, loop) in ar.anims.items():
            if anims and nome not in anims:
                continue
            jobs = [(variante, nome, f, d) for d in A.ORDEM for f in range(n)]
            imgs = pool.map(_quadro, jobs)
            folha = np.zeros((Q * len(A.ORDEM), Q * n, 4), np.uint8)
            xmin, ymin, xmax, ymax = Q, Q, 0, 0
            for (_, nm, f, d), im in zip(jobs, imgs):
                r = A.ORDEM.index(d)
                folha[r * Q:(r + 1) * Q, f * Q:(f + 1) * Q] = im
                ys, xs = np.where(im[..., 3] > 0)
                if len(ys) == 0:
                    problemas.append('%s %s %s quadro %d vazio' % (ident, nome, d, f))
                    continue
                xmin, ymin, xmax, ymax = min(xmin, xs.min()), min(ymin, ys.min()), max(xmax, xs.max()), max(ymax, ys.max())
                if xs.min() < MARGEM or ys.min() < MARGEM or xs.max() > Q - 1 - MARGEM or ys.max() > Q - 1 - MARGEM:
                    problemas.append('%s %s %s quadro %d chega à borda (%d,%d)-(%d,%d)' % (ident, nome, d, f, xs.min(), ys.min(), xs.max(), ys.max()))
            Image.fromarray(folha, 'RGBA').save(os.path.join(saida, '%s_%s.png' % (ident, nome)))
            alfas = set(np.unique(folha[..., 3]).tolist())
            if not alfas <= {0, 255}:
                problemas.append('%s %s tem alfa que não é binário: %s' % (ident, nome, sorted(alfas)))
            cores = len(np.unique(folha[folha[..., 3] > 0][:, :3], axis=0))
            if cores > MAX_CORES:
                problemas.append('%s %s usa %d cores (máximo %d)' % (ident, nome, cores, MAX_CORES))
            relatorio[nome] = dict(quadros=n, fps=fps, loop=loop, caixa=(int(xmin), int(ymin), int(xmax), int(ymax)), cores=cores)
    return relatorio, problemas


if __name__ == '__main__':
    quais = sys.argv[1] if len(sys.argv) > 1 else 'todas'
    anims = sys.argv[2].split(',') if len(sys.argv) > 2 and sys.argv[2] != 'todas' else None
    saida = sys.argv[3] if len(sys.argv) > 3 else None
    ruim = []
    for v in (IDS if quais == 'todas' else [quais]):
        rel, problemas = montar(v, anims, saida)
        for k, val in rel.items():
            print(IDS[v], k, val)
        ruim += problemas
    if ruim:
        print('PROBLEMAS:')
        for p in ruim:
            print(' ', p)
        sys.exit(1)
    print('ok')
