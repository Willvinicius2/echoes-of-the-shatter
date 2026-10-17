"""Prancha das 5 combinacoes do heroi modular (frente e 3/4): python -I m_prancha.py <pasta final> <saida.jpg> <Heroi>"""
import sys, cv2, numpy as np
fin, out, hero = sys.argv[1], sys.argv[2], sys.argv[3]
cs = ["completo", "sem_elmo", "sem_luvas", "sem_botas", "so_corpo"]
cell = 440
sheet = np.full((2 * cell + 24, 5 * cell, 3), 107, np.uint8)
for i, c in enumerate(cs):
    cv2.putText(sheet, c, (i * cell + 10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (240, 240, 240), 1, cv2.LINE_AA)
    for j, v in enumerate(("frente", "3-4")):
        im = cv2.imread(f"{fin}/previews/{hero}_modular_{c}_{v}.png")
        im = cv2.resize(im[60:1000, 150:874], (cell, int(cell * 940 / 724)))[:cell] if False else cv2.resize(im, (cell, cell), interpolation=cv2.INTER_AREA)
        sheet[24 + j * cell:24 + (j + 1) * cell, i * cell:(i + 1) * cell] = im
cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("ok", out)
