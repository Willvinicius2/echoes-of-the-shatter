"""Prancha do elenco na mesma escala (python -I m_prancha_npc_sheet.py <pasta dos cast_*.png> <saida.jpg> rotulo [rotulo ...]).
Linha 1: frente; linha 2: camera do jogo a 56 m (mesma escala entre personagens) com a altura real (88 px = 1,5 m em 1080p) ao lado."""
import sys, cv2, numpy as np
pv, out, labels = sys.argv[1], sys.argv[2], sys.argv[3:]
cell = 400
sheet = np.full((2 * cell + 60, len(labels) * cell, 3), 107, np.uint8)
for i, L in enumerate(labels):
    f = cv2.resize(cv2.imread(f"{pv}/cast_{L}_frente.png")[:, :, :3], (cell, cell), interpolation=cv2.INTER_AREA)
    sheet[30:30 + cell, i * cell:(i + 1) * cell] = f
    cv2.putText(sheet, L, (i * cell + 10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    g = cv2.imread(f"{pv}/cast_{L}_jogo.png", cv2.IMREAD_UNCHANGED).astype(np.float32)
    a = g[:, :, 3:4] / 255.0
    rgb = (g[:, :, :3] * a + np.array([107, 107, 107], np.float32) * (1 - a))
    crop = rgb[300:1750, 300:1750]                       # mesmo recorte para todos (escala preservada)
    tile = cv2.resize(crop, (cell, cell), interpolation=cv2.INTER_AREA)
    sheet[60 + cell:60 + 2 * cell, i * cell:(i + 1) * cell] = np.clip(tile, 0, 255).astype(np.uint8)
    # tamanho real em 1080p a 56 m: 1080 px cobrem 2*56*tan(7,1 graus) = 13,95 m (77,4 px/m); o render tem 2048 px para 1,875 m (1092 px/m)
    small = cv2.resize(crop, None, fx=0.0709, fy=0.0709, interpolation=cv2.INTER_AREA)
    y0 = 60 + 2 * cell - small.shape[0] - 6; x0 = (i + 1) * cell - small.shape[1] - 6
    sheet[y0:y0 + small.shape[0], x0:x0 + small.shape[1]] = np.clip(small, 0, 255).astype(np.uint8)
    cv2.rectangle(sheet, (x0 - 1, y0 - 1), (x0 + small.shape[1], y0 + small.shape[0]), (255, 255, 255), 1)
cv2.putText(sheet, "camera do jogo 56 m (mesma escala); quadro pequeno = tamanho real em 1080p", (10, 50 + cell), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1, cv2.LINE_AA)
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("ok", out)
