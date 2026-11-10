"""Partes de cada direção do Cão de Cinza (coordenadas na grade de 64 px da base aprovada)."""
import numpy as np
from PIL import Image, ImageDraw
import rig
from rig import PAD, Q, carregar, opaco, vazio

# caixas (x0, y0, x1, y1) inclusivas na grade de 64 px
CFG = {
    'E': dict(
        y_corte=40, sobre=3,
        pernas=[dict(nome='T', x0=12, x1=30, quadril=38), dict(nome='F', x0=31, x1=53, quadril=38)],
        caudas=[dict(nome='cA', caixas=[(0, 0, 20, 15), (0, 16, 13, 25)], raiz=(15, 22)),
                dict(nome='cB', caixas=[(0, 29, 13, 40)], raiz=(14, 34))],
        frente=(1, 0)),
    'NE': dict(
        y_corte=40, sobre=3,
        pernas=[dict(nome='T', x0=13, x1=28, quadril=38), dict(nome='F', x0=33, x1=52, quadril=38)],
        caudas=[dict(nome='cA', caixas=[(0, 0, 20, 15), (0, 16, 12, 25)], raiz=(14, 22)),
                dict(nome='cB', caixas=[(0, 29, 13, 41)], raiz=(14, 34))],
        frente=(1, -1)),
    'S': dict(
        y_corte=40, sobre=3,
        pernas=[dict(nome='A', x0=9, x1=23, quadril=38), dict(nome='B', x0=24, x1=38, quadril=38),
                dict(nome='C', x0=39, x1=52, quadril=38)],
        caudas=[dict(nome='cA', caixas=[(41, 0, 63, 19)], raiz=(50, 18)),
                dict(nome='cB', caixas=[(51, 23, 63, 37)], raiz=(52, 30))],
        frente=(0, 1)),
    'SE': dict(
        y_corte=40, sobre=3,
        pernas=[dict(nome='A', x0=14, x1=24, quadril=38), dict(nome='B', x0=25, x1=37, quadril=38),
                dict(nome='C', x0=38, x1=53, quadril=38)],
        caudas=[dict(nome='cA', caixas=[(0, 0, 24, 17)], raiz=(18, 16)),
                dict(nome='cB', caixas=[(0, 24, 13, 37)], raiz=(14, 30))],
        frente=(1, 1)),
    'N': dict(
        y_corte=40, sobre=3,
        pernas=[dict(nome='A', x0=11, x1=23, quadril=40), dict(nome='B', x0=24, x1=37, quadril=40),
                dict(nome='C', x0=38, x1=52, quadril=40)],
        caudas=[dict(nome='cA', caixas=[(0, 8, 20, 30)], raiz=(20, 26)),
                dict(nome='cB', caixas=[(0, 35, 22, 44)], raiz=(21, 40))],
        frente=(0, -1)),
}


def mascara_caixas(caixas):
    m = np.zeros((Q, Q), bool)
    for (x0, y0, x1, y1) in caixas:
        m[y0 + PAD:y1 + PAD + 1, x0 + PAD:x1 + PAD + 1] = True
    return m


def partes(nome):
    """Divide a base em camadas: pernas (com sobreposição), caudas e o corpo restante."""
    cfg = CFG[nome]
    a = carregar(nome)
    op = opaco(a)
    resto = op.copy()
    camadas = {}
    yc = cfg['y_corte'] + PAD
    for t in cfg['caudas']:
        m = mascara_caixas(t['caixas']) & op & resto
        resto &= ~m
        c = vazio()
        c[m] = a[m]
        camadas[t['nome']] = c
    for p in cfg['pernas']:
        x0, x1 = p['x0'] + PAD, p['x1'] + PAD
        m = np.zeros_like(op)
        m[yc:, x0:x1 + 1] = (op & resto)[yc:, x0:x1 + 1]
        mo = m.copy()
        mo[yc - cfg['sobre']:yc, x0:x1 + 1] = (op & resto)[yc - cfg['sobre']:yc, x0:x1 + 1]
        resto &= ~m
        c = vazio()
        c[mo] = a[mo]
        camadas[p['nome']] = c
    corpo = vazio()
    corpo[resto] = a[resto]
    camadas['corpo'] = corpo
    return a, camadas


def depurar(nome, Z=8, saida=None):
    """Desenha as partes em cores sobre a base, para conferir os recortes."""
    a, cam = partes(nome)
    cores = {'corpo': (70, 70, 80), 'T': (255, 80, 80), 'F': (80, 255, 80), 'A': (255, 80, 80), 'B': (80, 255, 80),
             'C': (80, 160, 255), 'cA': (255, 0, 255), 'cB': (255, 255, 0)}
    s = Image.new('RGBA', (64 * Z, 64 * Z), (30, 30, 34, 255))
    arr = np.zeros((64, 64, 4), np.uint8)
    for k, c in cam.items():
        m = opaco(c)[PAD:PAD + 64, PAD:PAD + 64]
        base = np.array(cores[k] + (255,), np.uint8)
        orig = a[PAD:PAD + 64, PAD:PAD + 64]
        mix = (0.55 * orig[..., :3] + 0.45 * base[:3]).astype(np.uint8)
        arr[m, :3] = mix[m]
        arr[m, 3] = 255
    im = Image.fromarray(arr, 'RGBA').resize((64 * Z, 64 * Z), Image.NEAREST)
    s.alpha_composite(im)
    d = ImageDraw.Draw(s)
    for g in range(0, 64, 8):
        d.line([(g * Z, 0), (g * Z, 64 * Z)], fill=(255, 255, 255, 60))
        d.line([(0, g * Z), (64 * Z, g * Z)], fill=(255, 255, 255, 60))
        d.text((g * Z + 2, 2), str(g), fill=(255, 255, 0, 255))
        d.text((2, g * Z + 2), str(g), fill=(255, 255, 0, 255))
    if saida:
        s.save(saida)
    return s


if __name__ == '__main__':
    import sys
    pasta = sys.argv[1]            # onde gravar as imagens de conferência (fora do Git)
    for n in (sys.argv[2:] or list(CFG)):
        depurar(n, saida=f'{pasta}/dep_{n}.png')
        print('ok', n)
