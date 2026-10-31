#!/usr/bin/env python3
"""Monta as folhas finais do Guerreiro (128 px, 5 direções) a partir das folhas brutas geradas por IA.

Uso: python3 tools/sprites/montar_guerreiro.py [pasta_bruto] [pasta_saida]
Entrada: docs/arte/sprites2d/guerreiro/bruto/guerreiro_<anim>.png (grade N colunas x 5 linhas, fundo magenta,
xadrez falso ou transparente, quadros desalinhados). Saída: godot/art2d/sprites/guerreiro/guerreiro_<anim>.png.
Passos: remove o fundo, fatia a grade, escala cada folha para ~100 px de altura em pé, ancora os pés em (64,104)
com a mesma âncora por linha (sem tremida), e anima idle/run por código (respiração, balanço), pois os quadros
brutos saem quase iguais. A animação "hit" é montada do idle (recuo + clarão), porque o rosto bruto divergia.
Requer numpy, pillow e scipy.
"""
import math
import os
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

W = 128
PX, PY = 64, 104
ALTURA = 100.0
FASE_IDLE = [0.0, 1.3, 2.6, 3.9, 5.2]
ANIMS = {"idle": 6, "run": 8, "attack": 6, "dodge": 6, "hit": 3, "death": 8}


def sem_fundo(img):
    a = np.asarray(img.convert("RGBA")).astype(float)
    if a[..., 3].min() < 10:
        return Image.fromarray(a.astype(np.uint8), "RGBA")
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    canto = a[2:6, 2:6, :3].reshape(-1, 3).mean(0)
    if canto[0] > 200 and canto[2] > 200 and canto[1] < 80:        # magenta
        mag = np.minimum(r, b) - g
        alpha = np.clip(1 - (mag - 40) / 90, 0, 1)
        spill = np.clip(mag, 0, None) * (alpha < 1)
        a[..., 0] -= spill * 0.6
        a[..., 2] -= spill * 0.6
    else:                                                          # xadrez falso claro: preenche a partir da borda
        sat = a[..., :3].max(-1) - a[..., :3].min(-1)
        claro = (a[..., :3].min(-1) > 175) & (sat < 14)
        lab, _ = ndimage.label(claro)
        borda = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
        fundo = np.isin(lab, list(borda))
        fundo = (ndimage.binary_dilation(fundo, iterations=1) & claro) | fundo
        alpha = ndimage.gaussian_filter(np.where(fundo, 0.0, 1.0), 0.6)
        alpha = ndimage.minimum_filter(alpha, size=3)           # come a franja clara do xadrez
        alpha = np.clip((alpha - 0.3) / 0.7, 0, 1)
    out = np.dstack([np.clip(a[..., :3], 0, 255), alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def limpa_ilhas(frame):
    """Mantém o componente principal e os grandes (corte da espada); remove restos de células vizinhas."""
    al = np.asarray(frame)[..., 3] > 25
    grosso = ndimage.binary_dilation(al, iterations=3)
    lab, n = ndimage.label(grosso)
    if n <= 1:
        return frame
    tam = ndimage.sum(al, lab, range(1, n + 1))
    manter = [i + 1 for i, t in enumerate(tam) if t >= 0.3 * tam.max()]
    arr = np.asarray(frame).copy()
    arr[..., 3] = np.where(np.isin(lab, manter), arr[..., 3], 0)
    return Image.fromarray(arr, "RGBA")


def fatia(img, cols):
    cw, ch = img.width / cols, img.height / 5
    return [[limpa_ilhas(img.crop((round(q * cw), round(d * ch), round((q + 1) * cw), round((d + 1) * ch))))
             for q in range(cols)] for d in range(5)]


def bbox(fr):
    return fr.split()[3].point(lambda v: 255 if v > 25 else 0).getbbox()


def escala_da_folha(grade):
    alts = [bbox(grade[0][q])[3] - bbox(grade[0][q])[1] for q in range(min(2, len(grade[0])))]
    return ALTURA / float(np.median(alts))


def ancora_linha(linha):
    """Âncora (x do centro de massa, y dos pés) comum à linha, em px da folha bruta (medianas)."""
    xs, ys = [], []
    for fr in linha:
        al = np.asarray(fr)[..., 3] > 25
        xs.append(np.average(np.arange(al.shape[1]), weights=al.sum(0)) if al.any() else fr.width / 2)
        ys.append(bbox(fr)[3])
    return float(np.median(xs)), float(np.median(ys))


def encaixa(fr, ancora, s, dx=0.0, dy=0.0, sy=1.0, rot=0.0):
    nw, nh = max(1, round(fr.width * s)), max(1, round(fr.height * s * sy))
    pe = fr.resize((nw, nh), Image.LANCZOS)
    tela = Image.new("RGBA", (W * 3, W * 3), (0, 0, 0, 0))
    ox = round(W + PX - ancora[0] * s + dx)
    oy = round(W + PY - ancora[1] * s * sy + dy)
    tela.alpha_composite(pe, (ox, oy)) if ox >= 0 and oy >= 0 else tela.paste(pe, (ox, oy), pe)
    if rot:
        tela = tela.rotate(rot, resample=Image.BICUBIC, center=(W + PX + dx, W + PY + dy))
    return tela.crop((W, W, W * 2, W * 2))


DIRS_V2 = ["s", "se", "e", "ne", "n"]
GRADE_V2 = {"run": (4, 2), "idle": (3, 2)}
ALTURA_V2 = {"run": ALTURA * 0.97, "idle": ALTURA}


def separa_v2(img, n):
    """Folha v2 (um personagem por célula de uma grade invisível): pega os n maiores blocos e ordena por leitura."""
    al = np.asarray(img)[..., 3] > 25
    lab, k = ndimage.label(ndimage.binary_dilation(al, iterations=6))
    tam = ndimage.sum(al, lab, range(1, k + 1))
    maiores = sorted(np.argsort(tam)[::-1][:n] + 1)
    caixas = ndimage.find_objects(lab)
    blocos = []
    for i in maiores:
        sl = caixas[i - 1]
        arr = np.asarray(img).copy()[sl]
        arr[..., 3] = np.where(lab[sl] == i, arr[..., 3], 0)
        cy, cx = (sl[0].start + sl[0].stop) / 2, (sl[1].start + sl[1].stop) / 2
        blocos.append((cy, cx, Image.fromarray(arr, "RGBA")))
    linhas = img.height / 2
    blocos.sort(key=lambda b: (int(b[0] // linhas), b[1]))
    return [limpa_ilhas(b[2]) for b in blocos]


def tira_magenta(img):
    """Remove o reflexo magenta que o fundo deixa nas bordas do metal (só onde vermelho e azul passam do verde)."""
    a = np.asarray(img).astype(float)
    mag = np.minimum(a[..., 0], a[..., 2]) - a[..., 1]
    corte = np.clip(mag - 12, 0, None) * 0.9
    a[..., 0] -= corte
    a[..., 2] -= corte
    # roxo pintado pela IA no aço (azul e vermelho acima do verde): volta para cinza-aço
    roxo = (a[..., 2] > a[..., 1] + 10) & (a[..., 0] >= a[..., 1])
    for c in (0, 2):
        a[..., c] = np.where(roxo, a[..., 1] + (a[..., c] - a[..., 1]) * 0.35, a[..., c])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def montar_v2(anim, v2_dir):
    """Corrida e idle desenhados quadro a quadro (v2): uma folha bruta por direção, sem animação por código."""
    n = ANIMS[anim]
    folha = Image.new("RGBA", (W * n, W * 5), (0, 0, 0, 0))
    for d, nome in enumerate(DIRS_V2):
        img = tira_magenta(sem_fundo(Image.open(os.path.join(v2_dir, f"{anim}_{nome}.png"))))
        quadros = separa_v2(img, n)
        alts = sorted(bbox(f)[3] - bbox(f)[1] for f in quadros)
        s = ALTURA_V2[anim] / float(np.median(alts))
        # todos os quadros numa tela comum, com o pé mais baixo de cada um no chão
        hmax = max(f.height for f in quadros)
        wmax = max(f.width for f in quadros)
        telas = []
        for f in quadros:
            t = Image.new("RGBA", (wmax, hmax), (0, 0, 0, 0))
            t.alpha_composite(f, ((wmax - f.width) // 2, hmax - f.height))
            telas.append(t)
        if anim == "idle":  # quadro que destoa da silhueta (IA redesenhou) vira o anterior: respira sem trocar de desenho
            hs = [bbox(t)[3] - bbox(t)[1] for t in telas]
            med = float(np.median(hs))
            for q in range(1, n):
                if hs[q] < 0.95 * med:
                    telas[q] = telas[q - 1]
        anc = ancora_linha(telas)
        quadros_finais = [encaixa(telas[q], anc, s) for q in range(n)]
        pe = max(bbox(f)[3] for f in quadros_finais)  # pé exatamente no pivô
        for q, f in enumerate(quadros_finais):
            folha.alpha_composite(f, (q * W, d * W + PY - pe))
    return folha


def montar(anim, bruto_dir, cache, v2_dir=None):
    if v2_dir and anim in GRADE_V2 and os.path.exists(os.path.join(v2_dir, f"{anim}_s.png")):
        return montar_v2(anim, v2_dir)
    n = ANIMS[anim]
    origem = "idle" if anim == "hit" else anim
    if origem not in cache:
        img = sem_fundo(Image.open(os.path.join(bruto_dir, f"guerreiro_{origem}.png")))
        cache[origem] = fatia(img, ANIMS[origem])
    grade = cache[origem]
    s = escala_da_folha(grade)
    folha = Image.new("RGBA", (W * n, W * 5), (0, 0, 0, 0))
    for d in range(5):
        linha = grade[d]
        anc = ancora_linha(linha)
        for q in range(n):
            t = q / n
            dx = dy = rot = 0.0
            sy = 1.0
            fr = linha[min(q, len(linha) - 1)]
            if anim == "hit":
                fr = linha[0]
                dx, dy, rot = [-5, -8, -3][q], [1, 2, 0][q], [3, 5, 2][q]
            elif anim == "idle":
                fase = FASE_IDLE[d]  # fase própria por direção: as linhas não respiram em uníssono
                sy = 1.0 + 0.022 * math.sin(t * math.tau + fase)
                dy = -1.0 * math.sin(t * math.tau + fase)
            elif anim == "run":
                dy = -3.0 * abs(math.sin(t * math.tau * 2))
                rot = 2.5 * math.sin(t * math.tau)
            quadro = encaixa(fr, anc, s, dx, dy, sy, rot)
            if anim == "hit" and q == 0:
                tint = Image.new("RGBA", quadro.size, (0, 0, 0, 0))
                tint.paste(Image.new("RGBA", quadro.size, (255, 255, 255, 110)), mask=quadro.split()[3])
                quadro.alpha_composite(tint)
            if anim == "attack" and d == 4 and q in (3, 4):
                # fragmento solto do corte (luz branca à direita) que o gerador deixou nesses quadros
                arr = np.asarray(quadro).copy()
                if q == 3:
                    arr[:40, 96:, 3] = 0   # sobra à direita, acima do ombro
                    arr[:, 116:, 3] = 0
                else:
                    arr[:, :26, 3] = 0    # o corte do quadro 3 invade a célula seguinte pela esquerda
                quadro = Image.fromarray(arr, "RGBA")
            folha.alpha_composite(quadro, (q * W, d * W))
    return folha


def main():
    raiz = os.path.join(os.path.dirname(__file__), "..", "..")
    bruto = sys.argv[1] if len(sys.argv) > 1 else os.path.join(raiz, "docs", "arte", "sprites2d", "guerreiro", "bruto")
    saida = sys.argv[2] if len(sys.argv) > 2 else os.path.join(raiz, "godot", "art2d", "sprites", "guerreiro")
    os.makedirs(saida, exist_ok=True)
    v2 = os.path.join(raiz, "docs", "arte", "sprites2d", "guerreiro", "v2", "bruto")
    cache = {}
    for anim in ANIMS:
        montar(anim, bruto, cache, v2).save(os.path.join(saida, f"guerreiro_{anim}.png"))
    print("folhas em", os.path.abspath(saida))


if __name__ == "__main__":
    main()
