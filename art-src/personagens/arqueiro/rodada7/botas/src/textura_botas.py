import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import pernas_textura as T
from pernas_textura import *

CO = (205, 170, 110)


def upper2(w, h):
    a = leather(h, w, (0.37, 0.215, 0.11), rugas=1.3, ay=1.6)
    uu, tt = coords(h, w)
    topo = np.exp(-((uu - 0.5) / 0.22) ** 2)
    # dobras vincadas do peito do pe (nitidas): escuro + realce de cima
    for t0, f in ((0.40, 0.9), (0.47, 0.8), (0.55, 0.6)):
        v = vinco(h, w, t0, 0.010, f, 0.8, t0 * 9) * topo
        a *= (1 - 0.75 * v)[..., None]
        a += np.array([0.30, 0.2, 0.11], np.float32) * (vinco(h, w, t0 + 0.022, 0.012, 0.5, 0.8, t0 * 9) * topo)[..., None]
    # biqueira reforcada (t>0.80), mais escura, com borda gasta clara
    bq = ss(tt, 0.79, 0.80)
    a = a * (1 - 0.30 * bq)[..., None]
    a += np.array([0.20, 0.13, 0.07], np.float32) * (np.exp(-((tt - 0.805) / 0.012) ** 2))[..., None]
    gast = ss(tt, 0.88, 1.0) * ss(fbm(h, w, 2.0), -0.2, 1.3) * np.exp(-((uu - 0.5) / 0.3) ** 2)
    a += np.array([0.28, 0.19, 0.10], np.float32) * gast[..., None]
    # contraforte do calcanhar (t<0.20): couro mais escuro e liso nas laterais
    ct = (1 - ss(tt, 0.19, 0.20)) * (1 - np.exp(-((uu - 0.5) / 0.30) ** 2))
    a = a * (1 - 0.28 * ct)[..., None]
    # sujeira / lama perto da vira (bordas u=0 e u=1)
    low = np.minimum(uu, 1 - uu)
    a *= (1 - 0.55 * (1 - ss(low, 0.0, 0.20)))[..., None]
    # desgaste: couro esbranquicado nas arestas do topo do pe
    des = ss(fbm(h, w, 2.4), 0.8, 2.0) * topo * 0.5
    a += np.array([0.20, 0.15, 0.09], np.float32) * des[..., None]
    im = to_img(a)
    d = ImageDraw.Draw(im)
    for xx in (0.085, 0.915):                              # costura rente a vira, dupla
        for dx in (-4, 4):
            tracejado(im, (xx * w + dx, 0), (xx * w + dx, h), CO, 8, 6, 2)
    for dy in (-5, 5):                                      # costura da biqueira
        yy = (1 - 0.80) * h + dy
        tracejado(im, (0, yy), (w, yy), CO, 8, 6, 2)
    yy = (1 - 0.20) * h                                      # costura do contraforte
    tracejado(im, (0, yy), (w, yy), CO, 7, 5, 2)
    tracejado(im, (0, h * 0.03), (w, h * 0.03), CO, 7, 5, 2)
    # furinhos de ornamento na biqueira
    for k in range(18):
        x = (0.18 + 0.64 * k / 17) * w
        y = (1 - 0.88 - 0.05 * math.sin(math.pi * k / 17)) * h
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(40, 22, 11))
    rs = rng()
    for _ in range(9):
        rachadura(im, (rs.uniform(0.2 * w, 0.8 * w), rs.uniform(0, h)), 8, 5, (30, 17, 8), rs)
    return arranhoes(from_img(im), 220, rs, (0.82, 0.62, 0.42), 36, 0.5)


T.upper = upper2
_cano = T.cano


def cano2(w, h):
    a = _cano(w, h)
    # dobras de acordeao mais nitidas no tornozelo
    uu, tt = coords(h, w)
    for t0 in (0.14, 0.30):
        v = vinco(h, w, t0, 0.008, 0.9, 1.2, t0 * 70)
        a *= (1 - 0.6 * v)[..., None]
    return a


T.cano = cano2
if __name__ == "__main__":
    T.SAIDA = os.environ["ARQ_TRAB"]
    T.salvar(T.montar_botas(), "T_Arqueiro_Botas_BC.png")
