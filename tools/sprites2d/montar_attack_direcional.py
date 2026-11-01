"""Monta arqueiro_attack.png (6 quadros x 5 linhas, 128 px, pé em 64x104) a partir de 5 faixas brutas (att_s/se/e/ne/n.png, fundo magenta).
Uso: python montar_attack_direcional.py <pasta_brutos> <saida.png> [altura_mediana_alvo]
Escala única na folha toda; o x é centrado nas pernas (não no arco), o y encosta a base do sprite em 104."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
from scipy import ndimage
from montar_folhas import key, despill, F, FOOT
N = 6
def limpa_celula(cell, mx, cw):
    """Guarda o corpo (maior componente, com a flecha fina unida por dilatação) e pedaços grandes cujo centro cai na coluna do quadro;
    descarta pontas de flecha dos quadros vizinhos que entram pela margem."""
    a = np.array(cell); al = a[..., 3] > 0
    lab, k = ndimage.label(ndimage.binary_dilation(al, iterations=6))
    if k == 0:
        return cell
    sizes = ndimage.sum(al, lab, range(1, k + 1)); main = int(np.argmax(sizes)) + 1
    cm = ndimage.center_of_mass(al, lab, range(1, k + 1))
    keep = np.zeros_like(al)
    for i in range(1, k + 1):
        if i == main or (sizes[i - 1] > 60 and mx <= cm[i - 1][1] <= mx + cw):
            keep |= (lab == i) & al
    a[~keep, 3] = 0
    return Image.fromarray(despill(a), "RGBA")
def corpo_h(cell, b):
    """altura do corpo sem a ponta do arco/flecha: do pé até a primeira linha larga (cabelo)."""
    a = (np.array(cell)[..., 3] > 0)[b[1]:b[3]]
    cnt = a.sum(axis=1); top = int(np.argmax(cnt >= 0.55 * cnt.max()))
    return len(cnt) - top
def celulas(raw):
    img = key(Image.open(raw)); W, H = img.size; cw = W / N; mx = cw * 0.04
    out = []
    for c in range(N):
        cell = limpa_celula(img.crop((round(c * cw - mx), 0, round((c + 1) * cw + mx), H)), mx, cw)
        out.append((cell, cell.getbbox()))
    return out
def cx_pernas(cell, b):
    a = np.array(cell)[..., 3] > 0
    y0 = b[3] - max(4, int((b[3] - b[1]) * 0.22))
    xs = np.where(a[y0:b[3]].any(axis=0))[0]
    return (xs.min() + xs.max()) / 2
if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    alvo = float(sys.argv[3]) if len(sys.argv) > 3 else 96
    rows = [celulas(os.path.join(src, f"att_{k}.png")) for k in ("s", "se", "e", "ne", "n")]
    hs = sorted(corpo_h(c, b) for r in rows for c, b in r)
    s = alvo / hs[len(hs) // 2]
    sheet = Image.new("RGBA", (N * F, 5 * F), (0, 0, 0, 0))
    for r, row in enumerate(rows):
        sr = min(s, FOOT[1] / max(b[3] - b[1] for _, b in row))  # linha com arco/flecha alto (N): escala uniforme na linha para caber no quadro
        for c, (cell, b) in enumerate(row):
            cx = cx_pernas(cell, b)
            spr = cell.crop(b)
            spr = spr.resize((max(1, round(spr.width * sr)), max(1, round(spr.height * sr))), Image.LANCZOS)
            x = c * F + FOOT[0] - round((cx - b[0]) * sr)
            y = r * F + FOOT[1] - spr.height
            ox, oy = x - c * F, y - r * F
            if ox < 0 or oy < 0 or ox + spr.width > F:
                print("AVISO: sprite passa do quadro", r, c, (ox, oy, spr.width, spr.height))
            tile = Image.new("RGBA", (F, F), (0, 0, 0, 0)); tile.paste(spr, (ox, oy))
            sheet.alpha_composite(tile, (c * F, r * F))
    sheet.save(dst); print("ok", dst, "escala", round(s, 3))
