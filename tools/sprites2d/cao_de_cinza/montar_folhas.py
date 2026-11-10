"""Monta as folhas do Cão de Cinza (92 px, 5 direções por linha: S, SE, E, NE, N) a partir de animacao.py.
Alinha os pés de todas as direções à mesma linha (PE_LINHA) e confere: alfa binário e paleta curta.

Uso: python3 tools/sprites2d/cao_de_cinza/montar_folhas.py [pasta_saida]   (padrão: godot/art2d/sprites/ash_hound)"""
import os
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import animacao as anim

PE_LINHA = 74
ANIMS = {'idle': anim.parado, 'run': anim.correr, 'attack': anim.morder, 'hit': anim.ferido, 'death': anim.morrer}


def deslocamentos():
    """Quanto cada direção desce/sobe para os pés do primeiro quadro de idle ficarem em PE_LINHA."""
    d = {}
    for n in anim.DIRS:
        f = anim.parado(n)[0]
        ys = np.where(f[..., 3] > 0)[0]
        d[n] = PE_LINHA - int(ys.max())
    return d


def folha(nome_anim, desl):
    fn = ANIMS[nome_anim]
    lin = []
    for n in anim.DIRS:
        q = [anim.deslocar(f, 0, desl[n]) for f in fn(n)]
        lin.append(np.concatenate(q, axis=1))
    return np.concatenate(lin, axis=0)


RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
SAIDA = os.path.join(RAIZ, 'godot', 'art2d', 'sprites', 'ash_hound')


def main(saida):
    os.makedirs(saida, exist_ok=True)
    desl = deslocamentos()
    print('deslocamentos', desl)
    cores = set()
    for nm in ANIMS:
        a = folha(nm, desl)
        assert a.shape[0] == 5 * anim.Q and a.shape[1] % anim.Q == 0
        al = a[..., 3]
        assert set(np.unique(al)) <= {0, 255}, 'alfa nao binario'
        m = al > 0
        cores |= {tuple(int(v) for v in p[:3]) for p in a[m]}
        Image.fromarray(a, 'RGBA').save(os.path.join(saida, f'ash_hound_{nm}.png'), optimize=True)
        print(nm, a.shape[1] // anim.Q, 'quadros', a.shape)
    print('cores no conjunto:', len(cores))
    return cores


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else SAIDA)
