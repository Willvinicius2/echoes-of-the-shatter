"""Monta as folhas finais do arqueiro a partir das imagens brutas geradas por IA.

Uso: python montar_folhas.py <pasta_brutos> <pasta_saida>
Entrada: arq_<anim>.png (grade COLS x 5 linhas, fundo magenta).
Saída: arqueiro_<anim>.png com (quadros x 128) x (5 x 128), fundo transparente,
pé em (64,104), mesma escala em toda a folha. Ver docs/arte/25 (formato).
"""
import os, sys
from PIL import Image
import numpy as np
from scipy import ndimage

COLS = {"idle": 6, "run": 8, "attack": 6, "dodge": 6, "hit": 3, "death": 8}
ROWS, F, FOOT = 5, 128, (64, 104)
# attack: a flecha sai no quadro 4 (0-based); a pose de puxar vira o quadro 3 repetido
ORDEM = {"attack": [0, 1, 2, 2, 3, 4]}

def key(img):
    a = np.array(img.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mag = (r > 170) & (b > 170) & (g < 110)
    mag |= (r - g > 90) & (b - g > 90)  # bordas rosadas
    out = np.dstack([a, np.where(mag, 0, 255)]).astype(np.uint8)
    # tira o halo magenta dos pixels de borda
    edge = (~mag) & (r - g > 40) & (b - g > 40)
    out[edge, 0] = np.minimum(out[edge, 0], out[edge, 2] // 2 + 40)
    out[edge, 2] = np.minimum(out[edge, 2], out[edge, 0])
    return Image.fromarray(out, "RGBA")

def despill(a):
    """Tira o halo magenta/azul-roxo das bordas: erode 1 px e remove o excesso de R/B sobre G perto do vazio."""
    al = a[..., 3] > 0
    er = ndimage.binary_erosion(al, iterations=1)
    ring = ndimage.binary_dilation(~al, iterations=3) & er
    a[~er, 3] = 0
    r, g, b = [a[..., i].astype(int) for i in range(3)]
    m = np.clip(np.minimum(r, b) - g, 0, None)
    for i, ch in ((0, r), (2, b)):
        a[..., i] = np.where(ring, np.clip(ch - m, 0, 255), ch).astype(np.uint8)
    return a

def limpa(cell, cx, cy):
    """Guarda o sprite do centro (blob mais perto de cx,cy) e o que cruza a faixa vertical dele."""
    a = np.array(cell)
    al = a[..., 3] > 0
    lab, k = ndimage.label(ndimage.binary_dilation(al, iterations=4))
    if k == 0:
        return cell
    sizes = ndimage.sum(al, lab, range(1, k + 1))
    cm = ndimage.center_of_mass(al, lab, range(1, k + 1))
    cand = [i for i in range(k) if sizes[i] > 0.25 * sizes.max()]
    main = min(cand, key=lambda i: (cm[i][0] - cy) ** 2 + (cm[i][1] - cx) ** 2) + 1
    ys = np.where((lab == main).any(axis=1))[0]
    top, bot = ys.min(), ys.max()
    keep = np.zeros_like(al)
    for i in range(1, k + 1):
        yy = np.where((lab == i).any(axis=1))[0]
        if i == main or (yy.min() >= top - 4 and yy.max() <= bot + 4 and sizes[i - 1] > 40):
            keep |= (lab == i) & al
    a[~keep, 3] = 0
    return Image.fromarray(despill(a), "RGBA")

def montar(raw, n):
    img = key(Image.open(raw))
    W, H = img.size
    cw, ch = W / n, H / ROWS
    mx, my = cw * 0.04, ch * 0.3  # margem para pegar cabelo/pés que passam da grade
    cells = []
    for r in range(ROWS):
        for c in range(n):
            box = (round(c * cw - mx), round(r * ch - my), round((c + 1) * cw + mx), round((r + 1) * ch + my))
            cell = img.crop(box)  # fora da imagem fica transparente
            cell = limpa(cell, cell.width / 2, cell.height / 2)
            cells.append((r, c, cell, cell.getbbox()))
    boxes = [b for *_, b in cells if b]
    maxh = max(b[3] - b[1] for b in boxes)
    maxw = max(b[2] - b[0] for b in boxes)
    s = min(100 / maxh, 120 / maxw)
    sheet = Image.new("RGBA", (n * F, ROWS * F), (0, 0, 0, 0))
    for r, c, cell, b in cells:
        if not b:
            continue
        spr = cell.crop(b)
        spr = spr.resize((max(1, round(spr.width * s)), max(1, round(spr.height * s))), Image.LANCZOS)
        x = c * F + FOOT[0] - spr.width // 2
        y = r * F + FOOT[1] - spr.height
        sheet.alpha_composite(spr, (max(x, c * F), max(y, r * F)))
    return sheet

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for anim, n in COLS.items():
        raw = os.path.join(src, f"arq_{anim}.png")
        if os.path.exists(raw):
            sh = montar(raw, n)
            if anim in ORDEM:
                out = Image.new("RGBA", sh.size, (0, 0, 0, 0))
                for dst_c, src_c in enumerate(ORDEM[anim]):
                    out.paste(sh.crop((src_c * F, 0, (src_c + 1) * F, ROWS * F)), (dst_c * F, 0))
                sh = out
            sh.save(os.path.join(dst, f"arqueiro_{anim}.png"))
            print("ok", anim)
