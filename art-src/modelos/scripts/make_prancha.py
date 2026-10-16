"""Prancha JPG das previas 3/4 de tudo que tem final/previews: python -I make_prancha.py [saida.jpg]"""
import sys, os, glob, json
import numpy as np, cv2

ROOT = "D:/openclaude/_trabalho-claude/modelos3d"
out = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/_prancha_final.jpg"
files = sorted(glob.glob(f"{ROOT}/*/final/previews/*_3-4.png") + glob.glob(f"{ROOT}/m09_armas/*/final/previews/*_3-4.png"))
cell = 420
cols = 4
rows = (len(files) + cols - 1) // cols
sheet = np.full((rows * cell, cols * cell, 3), 107, np.uint8)
for i, f in enumerate(files):
    im = cv2.imread(f)
    # recorta a margem cinza uniforme para o personagem ocupar a celula
    bg = im[2, 2].astype(int)
    m = (np.abs(im.astype(int) - bg).max(-1) > 12)
    ys, xs = np.where(m)
    if len(ys):
        pad = 12
        im = im[max(ys.min() - pad, 0):ys.max() + pad, max(xs.min() - pad, 0):xs.max() + pad]
    h, w = im.shape[:2]
    s = (cell - 30) / max(h, w)
    im = cv2.resize(im, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
    y0 = (i // cols) * cell + 24 + (cell - 30 - im.shape[0]) // 2
    x0 = (i % cols) * cell + (cell - im.shape[1]) // 2
    sheet[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = im
    name = os.path.basename(f).replace("_3-4.png", "")
    cv2.putText(sheet, name, ((i % cols) * cell + 8, (i // cols) * cell + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1, cv2.LINE_AA)
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("prancha", out, len(files), "itens")
