"""Prancha do kit final (Python do venv, cv2): previa 3/4 de frente de cada peca, nome, triangulos e tamanho (Unity x, y, z).
Grava modelos3d/_prancha_cenario_final.jpg. Uso: python -I env_f_prancha.py"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from env_common import *

cols, cw, ch = 6, 340, 360
rows = (len(ORDER) + cols - 1) // cols
sheet = np.full((rows * ch + 40, cols * cw, 3), 46, np.uint8)
cv2.putText(sheet, "Cenario da Cripta, kit final (SM_Cripta_*, prop estatico): previa 3/4 de frente e frente", (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 1, cv2.LINE_AA)
for i, pid in enumerate(ORDER):
    a = cfg_for(pid)["asset"]
    r, k = divmod(i, cols); x0, y0 = k * cw, 40 + r * ch
    p = f"{OUT_ROOT}/prev/{a}_3-4.png"
    if os.path.exists(p):
        im = cv2.imread(p); im = cv2.resize(im, (cw - 10, cw - 10), interpolation=cv2.INTER_AREA); sheet[y0 + 4:y0 + 4 + im.shape[0], x0 + 5:x0 + 5 + im.shape[1]] = im
    j = json.load(open(f"{OUT_ROOT}/{a}.json", encoding="utf-8")) if os.path.exists(f"{OUT_ROOT}/{a}.json") else {}
    cv2.putText(sheet, a, (x0 + 6, y0 + cw + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (235, 235, 235), 1, cv2.LINE_AA)
    s = j.get("size_m_unity")
    cv2.putText(sheet, f"{j.get('tris', '?')} tris  {s[0]:.2f}x{s[1]:.2f}x{s[2]:.2f} m" if s else "?", (x0 + 6, y0 + cw + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (170, 200, 230), 1, cv2.LINE_AA)
cv2.imwrite("D:/openclaude/_trabalho-claude/modelos3d/_prancha_cenario_final.jpg", sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
print("EF", sheet.shape)
