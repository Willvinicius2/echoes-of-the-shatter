"""Monta as folhas finais do arqueiro a partir das imagens brutas geradas por IA.

Uso: python montar_folhas.py <pasta_brutos> <pasta_saida>
Entrada: arq_<anim>.png (grade COLS x 5 linhas, fundo magenta).
Saída: arqueiro_<anim>.png com (quadros x 128) x (5 x 128), fundo transparente,
pé em (64,104), mesma escala em toda a folha. Ver docs/arte/25 (formato).
"""
import os, sys
from PIL import Image
import numpy as np

COLS = {"idle": 6, "run": 8, "attack": 6, "dodge": 6, "hit": 3, "death": 8}
ROWS, F, FOOT = 5, 128, (64, 104)

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

def montar(raw, n):
    img = key(Image.open(raw))
    W, H = img.size
    cw, ch = W / n, H / ROWS
    cells = []
    for r in range(ROWS):
        for c in range(n):
            cell = img.crop((round(c * cw), round(r * ch), round((c + 1) * cw), round((r + 1) * ch)))
            cells.append((r, c, cell, cell.getbbox()))
    boxes = [b for *_, b in cells if b]
    # escala única: o maior sprite cabe em 100 px de altura (pé em 104, topo em 4)
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
        y = r * F + FOOT[1] - spr.height  # base do sprite no pé
        sheet.alpha_composite(spr, (max(x, c * F), max(y, r * F)))
    return sheet

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for anim, n in COLS.items():
        raw = os.path.join(src, f"arq_{anim}.png")
        if os.path.exists(raw):
            montar(raw, n).save(os.path.join(dst, f"arqueiro_{anim}.png"))
            print("ok", anim)
