"""Ferramenta (venv): sobrepoe a malha de jogo do corpo e a malha alta encaixada de uma peca (frente e lado) com grade de 0,1 m.
Uso: python -I tool_fit_overlay.py <personagem_da_peca> <corpo_game_raw.ply> -> work/fit_overlay.png"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh, cv2
from mdl_common import *
cfg = load_cfg()
body = trimesh.load(sys.argv[2], process=False)
pc = trimesh.load(wpath(cfg, "high.ply"), process=False)
S = 1000; sc = 560.0   # px por metro
def draw(view):
    img = np.full((S, S, 3), 40, np.uint8)
    def proj(P):
        if view == "front":
            return (500 + P[:, 0] * sc), (950 - P[:, 2] * sc)
        return (500 - P[:, 1] * sc), (950 - P[:, 2] * sc)
    for k in range(-8, 9):
        x = int(500 + k * 0.1 * sc); cv2.line(img, (x, 0), (x, S), (90, 70, 70) if k else (60, 60, 200), 1)
    for k in range(0, 17):
        y = int(950 - k * 0.1 * sc); cv2.line(img, (0, y), (S, y), (70, 70, 90) if k % 5 else (60, 160, 255), 1)
        cv2.putText(img, f"{k/10:.1f}", (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    for k in range(-5, 6):
        x = int(500 + k * 0.1 * sc); cv2.putText(img, f"{k/10:.1f}", (x + 2, 990), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
    # corpo: triangulos preenchidos cinza
    u, v = proj(body.vertices)
    for f in body.faces:
        cv2.fillConvexPoly(img, np.stack([u[f], v[f]], 1).astype(np.int32), (120, 120, 120))
    pts = pc.vertices
    pts = pts[np.random.default_rng(0).choice(len(pts), min(len(pts), 400000), replace=False)]
    u, v = proj(pts)
    ok = (u >= 0) & (u < S) & (v >= 0) & (v < S)
    img[v[ok].astype(int), u[ok].astype(int)] = (60, 80, 255)
    return img
cv2.imwrite(wpath(cfg, "fit_overlay.png"), np.concatenate([draw("front"), draw("side")], 1))
print("ok")
