#!/usr/bin/env python3
"""Monta as folhas finais do Mago (128 px, 5 direções) a partir das folhas brutas geradas por IA.

Uso: python3 tools/sprites/montar_mago.py [pasta_bruto] [pasta_saida]
Entrada: docs/arte/sprites2d/mago/bruto/mago_<anim>.png (fundo transparente, quadros desalinhados).
Saída: godot/art2d/sprites/mago/mago_<anim>.png, quadros de 128 com pés em (64,104). Ver docs/arte/25.

Todas as folhas brutas estão no desenho aprovado (04_mago.png: manto azul-marinho, cabelo castanho,
cajado dourado em anel com cristal azul). idle, dodge e death foram refeitas com
docs/arte/sprites2d/mago/prompts_mago_refazer.json, porque a primeira geração trouxe outro personagem.
  dodge: o brilho azul translúcido do gerador é removido (juntava quadros e apagava o contorno); o
         motor ganha um rastro curto desenhado aqui.
  death: só a última linha da folha bruta é a queda; ela serve às 5 direções.
Requer numpy, pillow e scipy.
"""
import math
import os
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

W = 128
PX, PY = 64, 104
ANIMS = {"idle": 6, "run": 8, "attack": 6, "dodge": 6, "hit": 3, "death": 8}
# folha bruta de onde sai cada animação (None = a própria)
ORIGEM = {}
# altura (px no quadro final) do quadro de referência de cada folha bruta, cajado incluído
ALTURA = {"run": 93.0, "attack": 92.0, "hit": 95.0, "idle": 95.0, "dodge": 92.0, "death": 95.0}
REF_COLS = {"run": [0, 1, 2, 3], "attack": [0, 1], "hit": [2], "idle": [0, 1, 2], "dodge": [0, 5], "death": [0]}
MIN_BLOB = 9000          # px de alfa: menores são projéteis soltos ou restos
FASE = [0.0, 1.3, 2.6, 3.9, 5.2]  # fase da respiração por direção (as linhas não respiram em uníssono)


def quadros(nome, bruto_dir):
    """Lê a folha bruta e devolve [linha][coluna] de recortes RGBA, achados por componente conexo."""
    img = Image.open(os.path.join(bruto_dir, f"mago_{nome}.png")).convert("RGBA")
    a = np.asarray(img)
    al = a[..., 3] > 40
    if nome == "dodge":
        a = sem_brilho(a)
        al = a[..., 3] > 40
    lab, n = ndimage.label(al if nome == "dodge" else ndimage.binary_dilation(al, iterations=2))
    tam = ndimage.sum(al, lab, range(1, n + 1))
    objs = ndimage.find_objects(lab)
    blobs = [(objs[i], i + 1) for i in range(n) if tam[i] >= MIN_BLOB]
    # agrupa em linhas pela base (pés): 5 linhas
    blobs.sort(key=lambda b: b[0][0].stop)
    bases = np.array([b[0][0].stop for b in blobs], float)
    cortes = np.sort(np.argsort(np.diff(bases))[-4:]) + 1
    linhas = np.split(np.arange(len(blobs)), cortes)
    grade = []
    for idx in linhas:
        linha = sorted((blobs[i] for i in idx), key=lambda b: b[0][1].start)
        fr = []
        for (sy, sx), k in linha:
            sub = a[sy, sx].copy()
            sub[..., 3] = np.where(lab[sy, sx] == k, sub[..., 3], 0)
            fr.append(Image.fromarray(sub, "RGBA"))
        grade.append(fr)
    assert len(grade) == 5, nome
    return grade


def sem_brilho(a):
    """Tira o brilho azul translúcido; mantém corpo opaco e o cristal (azul opaco perto do corpo)."""
    a = a.copy()
    r, g, b, al = [a[..., i].astype(int) for i in range(4)]
    azul = (b > r + 60) & (b > g + 20)
    corpo = (al >= 200) & ~azul
    perto = ndimage.binary_dilation(corpo, iterations=6)
    manter = ndimage.binary_dilation(corpo, iterations=1) & (al >= 120) | (azul & (al >= 230) & perto)
    a[..., 3] = np.where(manter, a[..., 3], 0)
    return a


def ancora(fr):
    al = np.asarray(fr)[..., 3] > 40
    # x pelo centro de massa da metade de baixo (pernas e manto), y pela base
    h = al.shape[0]
    low = al[h // 2:]
    x = np.average(np.arange(al.shape[1]), weights=low.sum(0)) if low.any() else fr.width / 2
    return float(x), float(fr.getbbox()[3])


def escala(grade, nome):
    alts = [grade[0][c].getbbox()[3] - grade[0][c].getbbox()[1] for c in REF_COLS[nome]]
    return ALTURA[nome] / float(np.median(alts))


def encaixa(fr, anc, s, dx=0.0, dy=0.0, sy=1.0, rot=0.0, sx=1.0):
    nw, nh = max(1, round(fr.width * s * sx)), max(1, round(fr.height * s * sy))
    pe = fr.resize((nw, nh), Image.LANCZOS)
    tela = Image.new("RGBA", (W * 3, W * 3), (0, 0, 0, 0))
    ox = round(W + PX - anc[0] * s * sx + dx)
    oy = round(W + PY - anc[1] * s * sy + dy)
    tela.paste(pe, (ox, oy), pe)
    if rot:
        tela = tela.rotate(rot, resample=Image.BICUBIC, center=(W + PX + dx, W + PY + dy))
    return tela.crop((W, W, W * 2, W * 2))


def clarao(q, cor, forca):
    t = Image.new("RGBA", q.size, (0, 0, 0, 0))
    t.paste(Image.new("RGBA", q.size, cor + (forca,)), mask=q.split()[3])
    out = q.copy()
    out.alpha_composite(t)
    return out


def rastro(q, dx, cor=(90, 140, 255)):
    """Rastro arcano: silhueta azul translúcida deslocada para trás e borrada."""
    al = q.split()[3]
    sil = Image.new("RGBA", q.size, cor + (0,))
    sil.putalpha(al.point(lambda v: v * 0.28))
    sil = sil.filter(ImageFilter.GaussianBlur(1))
    base = Image.new("RGBA", q.size, (0, 0, 0, 0))
    for k, f in ((1, 1.0),):
        camada = Image.new("RGBA", q.size, (0, 0, 0, 0))
        camada.paste(sil, (round(dx * k), 0))
        arr = np.asarray(camada).copy()
        arr[..., 3] = (arr[..., 3] * f).astype(np.uint8)
        base.alpha_composite(Image.fromarray(arr, "RGBA"))
    base.alpha_composite(q)
    return base


def montar(anim, bruto, cache):
    n = ANIMS[anim]
    org = ORIGEM.get(anim, anim)
    if org not in cache:
        cache[org] = quadros(org, bruto)
    grade = cache[org]
    s = escala(grade, org)
    folha = Image.new("RGBA", (W * n, W * 5), (0, 0, 0, 0))
    for d in range(5):
        linha = grade[d]
        ancs = [ancora(f) for f in linha]
        anc_linha = (float(np.median([x for x, _ in ancs])), float(np.median([y for _, y in ancs])))
        for q in range(n):
            t = q / n
            if anim == "idle":
                fr = linha[q]
                quadro = encaixa(fr, (anc_linha[0], ancora(fr)[1]), s)
            elif anim == "run":
                fr = linha[q]
                quadro = encaixa(fr, (ancora(fr)[0], anc_linha[1]), s, dy=-2.0 * abs(math.sin(t * math.tau * 2)))
            elif anim == "attack":
                fr = linha[[0, 1, 2, 2, 3, 4][q]]
                quadro = encaixa(fr, (anc_linha[0], ancora(fr)[1]), s, dy=[0, 0, -1, -2, 0, 0][q])
                if q == 3:
                    quadro = clarao(quadro, (170, 190, 255), 18)
                quadro = borda_suave(quadro)
            elif anim == "hit":
                fr = linha[q]
                quadro = encaixa(fr, ancora(fr), s, dx=[-3, -4, 0][q])
                if q == 0:
                    quadro = clarao(quadro, (255, 255, 255), 110)
            elif anim == "dodge":
                fr = linha[q]
                lateral = d in (1, 2, 3)
                quadro = encaixa(fr, (ancora(fr)[0], anc_linha[1]), s, dx=-6 if lateral and 2 <= q <= 4 else 0)
                quadro = borda_suave(quadro, 6)
                if 2 <= q <= 4:
                    tras = [0, 0, -7, -8, -6, 0][q]
                    if d == 0:
                        quadro = rastro_v(quadro, -tras)
                    elif d == 4:
                        quadro = rastro_v(quadro, tras)
                    else:
                        quadro = rastro(quadro, tras)
            elif anim == "death":
                linha = grade[4]  # a queda desenhada (de frente) serve às 5 direções
                fr = linha[q]
                quadro = encaixa(fr, (ancora(linha[0])[0], ancora(fr)[1]), s)
                quadro = borda_suave(quadro, 4)
            folha.alpha_composite(quadro, (q * W, d * W))
    return folha


def tomba(fr, s, rot, ease):
    """Gira o corpo inteiro (sem cortar) e assenta no chão: centro em x=64, base em y=104+2."""
    pe = fr.resize((max(1, round(fr.width * s)), max(1, round(fr.height * s))), Image.LANCZOS)
    pe = pe.rotate(rot, resample=Image.BICUBIC, expand=True)
    bb = pe.getbbox()
    pe = pe.crop(bb)
    q = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    x0 = round(PX - pe.width / 2 + (0 if ease >= 1 else 0))
    y0 = round(PY + 2 * ease - pe.height)
    q.paste(pe, (x0, y0), pe)
    return q


def borda_suave(q, m=10):
    """Some suave nas bordas laterais do quadro (energia do ataque que passaria da célula)."""
    arr = np.asarray(q).copy().astype(float)
    ramp = np.ones(W)
    ramp[:m] = np.linspace(0, 1, m)
    ramp[-m:] = np.linspace(1, 0, m)
    arr[..., 3] *= ramp[None, :]
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def rastro_v(q, dy, cor=(90, 140, 255)):
    al = q.split()[3]
    sil = Image.new("RGBA", q.size, cor + (0,))
    sil.putalpha(al.point(lambda v: v * 0.4))
    sil = sil.filter(ImageFilter.GaussianBlur(2))
    base = Image.new("RGBA", q.size, (0, 0, 0, 0))
    base.paste(sil, (0, round(dy)))
    base.alpha_composite(q)
    return base


def main():
    raiz = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    bruto = sys.argv[1] if len(sys.argv) > 1 else os.path.join(raiz, "docs", "arte", "sprites2d", "mago", "bruto")
    saida = sys.argv[2] if len(sys.argv) > 2 else os.path.join(raiz, "godot", "art2d", "sprites", "mago")
    os.makedirs(saida, exist_ok=True)
    cache = {}
    for anim in ANIMS:
        montar(anim, bruto, cache).save(os.path.join(saida, f"mago_{anim}.png"), optimize=True)
    print("folhas em", os.path.abspath(saida))


if __name__ == "__main__":
    main()
