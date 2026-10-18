"""Prancha comparando dois conjuntos (python -I m_prancha_cmp_sheet.py <previews> <saida.jpg> <rotuloA> <rotuloB>).
Linha de cada conjunto: frente, costas, 3/4 e camera do jogo (ampliada x3 em um recorte) mais o tamanho real a 56 m (88 px de altura em 1080p)."""
import sys, cv2, numpy as np
pv, out, A, B = sys.argv[1:5]
cell = 512
def tile(label, v):
    im = cv2.imread(f"{pv}/cmp_{label}_{v}.png", cv2.IMREAD_UNCHANGED)
    return cv2.resize(im[:, :, :3], (cell, cell), interpolation=cv2.INTER_AREA)
def game(label):
    im = cv2.imread(f"{pv}/cmp_{label}_jogo.png", cv2.IMREAD_UNCHANGED).astype(np.float32)
    a = im[:, :, 3:4] / 255.0
    rgb = im[:, :, :3] * a + np.array([107, 107, 107], np.float32) * (1 - a)
    ys, xs = np.where(im[:, :, 3] > 8)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    h = y1 - y0 + 1
    c = rgb[y0:y1 + 1, x0:x1 + 1]
    big = np.full((cell, cell, 3), 107, np.uint8)
    s = 0.86 * cell / max(c.shape[:2]); b = cv2.resize(c, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    oy, ox = (cell - b.shape[0]) // 2, (cell - b.shape[1]) // 2
    big[oy:oy + b.shape[0], ox:ox + b.shape[1]] = np.clip(b, 0, 255).astype(np.uint8)
    # tamanho real: 88 px de altura em 1080p
    s2 = 88.0 / h; r = cv2.resize(c, None, fx=s2, fy=s2, interpolation=cv2.INTER_AREA)
    big[cell - r.shape[0] - 8:cell - 8, cell - r.shape[1] - 8:cell - 8] = np.clip(r, 0, 255).astype(np.uint8)
    cv2.rectangle(big, (cell - r.shape[1] - 10, cell - r.shape[0] - 10), (cell - 6, cell - 6), (255, 255, 255), 1)
    return big
cols = [("frente", None), ("costas", None), ("3/4", None), ("camera do jogo 56 m (inset = 88 px)", None)]
sheet = np.full((2 * cell + 48, 4 * cell, 3), 107, np.uint8)
for j, (t, _) in enumerate(cols):
    cv2.putText(sheet, t, (j * cell + 10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (240, 240, 240), 1, cv2.LINE_AA)
for i, L in enumerate((A, B)):
    y = 24 + i * (cell + 24)
    cv2.putText(sheet, L, (10, y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (30, 30, 30), 2, cv2.LINE_AA)
    for j, v in enumerate(("frente", "costas", "3-4")):
        sheet[y:y + cell, j * cell:(j + 1) * cell] = tile(L, v)
    sheet[y:y + cell, 3 * cell:] = game(L)
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("ok", out)
