#!/usr/bin/env python3
"""Monta as folhas finais do Mago (128 px, 5 direções) a partir das folhas brutas geradas por IA.

Uso: python3 tools/sprites/montar_mago.py [pasta_bruto] [pasta_saida]
Entrada: docs/arte/sprites2d/mago/bruto/mago_<anim>.png (fundo transparente, quadros desalinhados).
Saída: godot/art2d/sprites/mago/mago_<anim>.png, quadros de 128 com pés em (64,104). Ver docs/arte/25.

Só o desenho fiel à folha aprovada (04_mago.png: manto azul-marinho, cabelo castanho, cajado dourado em
anel com cristal azul) entra. As folhas brutas run, attack e hit saíram nesse desenho; idle, dodge e death
saíram com outro personagem (manto roxo, olhos ciano) e ficam de fora. Enquanto não chegam refeitas
(prompts em docs/arte/sprites2d/mago/prompts_mago_refazer.json), elas são montadas por código:
  idle  = pose calma do hit (quadro 2) com respiração;
  dodge = quadros do run, inclinados e baixos, com rastro arcano;
  death = recuo do hit, depois tomba e deita no chão.
Quando as folhas novas chegarem com o nome mago_<anim>.png e o desenho certo, troque a origem em ORIGEM.
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
ORIGEM = {"idle": "hit", "dodge": "run", "death": "hit"}
# altura (px no quadro final) do quadro de referência de cada folha bruta, cajado incluído
ALTURA = {"run": 90.0, "attack": 90.0, "hit": 95.0}
REF_COLS = {"run": [0, 1, 2, 3], "attack": [0, 1], "hit": [2]}
MIN_BLOB = 9000          # px de alfa: menores são projéteis soltos ou restos
FASE = [0.0, 1.3, 2.6, 3.9, 5.2]  # fase da respiração por direção (as linhas não respiram em uníssono)


def quadros(nome, bruto_dir):
    """Lê a folha bruta e devolve [linha][coluna] de recortes RGBA, achados por componente conexo."""
    img = Image.open(os.path.join(bruto_dir, f"mago_{nome}.png")).convert("RGBA")
    a = np.asarray(img)
    al = a[..., 3] > 40
    lab, n = ndimage.label(ndimage.binary_dilation(al, iterations=2))
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
    sil.putalpha(al.point(lambda v: v * 0.45))
    sil = sil.filter(ImageFilter.GaussianBlur(2))
    base = Image.new("RGBA", q.size, (0, 0, 0, 0))
    for k, f in ((2, 0.5), (1, 1.0)):
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
                fr = linha[2]
                fase = FASE[d]
                quadro = encaixa(fr, ancora(fr), s, dy=-0.8 * math.sin(t * math.tau + fase),
                                 sy=1.0 + 0.02 * math.sin(t * math.tau + fase))
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
                quadro = encaixa(fr, ancora(fr), s, dx=[-3, -4, -1][q])
                if q == 0:
                    quadro = clarao(quadro, (255, 255, 255), 110)
            elif anim == "dodge":
                # agacha, dispara para a frente e volta; usa passos do run
                fr = linha[[0, 2, 3, 4, 6, 7][q]]
                lean = [4, 10, 14, 14, 9, 3][q]
                sq = [0.96, 0.88, 0.82, 0.82, 0.9, 0.97][q]
                ix = 1 if d in (1, 2, 3) else 0       # vira para a direita nas laterais
                quadro = encaixa(fr, (ancora(fr)[0], anc_linha[1]), s, sy=sq, sx=1.0 + (1 - sq) * 0.5,
                                 rot=-lean * ix, dx=-7 * ix)
                if 1 <= q <= 4:
                    tras = [0, -9, -12, -12, -7, 0][q]
                    if d == 0:
                        quadro = rastro_v(quadro, -tras)
                    elif d == 4:
                        quadro = rastro_v(quadro, tras)
                    else:
                        quadro = rastro(quadro, tras)
            elif anim == "death":
                # 0-1 recuo (hit 0,1), 2-6 tomba para trás, 7 deitado e apagado
                if q < 2:
                    fr = linha[q]
                    quadro = encaixa(fr, ancora(fr), s, dx=-2 * q)
                else:
                    fr = linha[1]
                    k = min(1.0, (q - 2) / 4.0)
                    ease = 1 - (1 - k) ** 2
                    lado = -1 if d in (1, 2, 3) else 1
                    quadro = tomba(fr, s * (1 - 0.08 * ease), lado * 86 * ease, ease)
                    if q >= 6:
                        arr = np.asarray(quadro).copy().astype(float)
                        esc = 0.82 if q == 6 else 0.7
                        arr[..., :3] *= esc
                        quadro = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")
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
