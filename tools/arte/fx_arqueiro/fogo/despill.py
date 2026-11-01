"""Tira o resíduo roxo/magenta das bordas de fumaça: onde min(r,b) passa de g, o azul cai para tom quente. Uso: python despill.py <pasta>"""
import sys, glob, numpy as np
from PIL import Image
for f in glob.glob(sys.argv[1] + "/*.png"):
    if "icone_" in f: continue
    a = np.asarray(Image.open(f).convert("RGBA")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    ex = np.clip(np.minimum(r, b) - g, 0, None)
    a[..., 2] = np.clip(b - ex * 1.0, 0, 255)
    a[..., 0] = np.clip(r - ex * 0.2, 0, 255)
    Image.fromarray(a.astype(np.uint8), "RGBA").save(f)
