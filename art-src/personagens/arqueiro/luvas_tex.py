"""Pinta T_Arqueiro_Luvas_BC.png (512x512) por script (numpy + PIL). Rodar: python luvas_tex.py
Atlas (v=0 embaixo, como no Blender; a linha 0 do PNG e o topo):
  COURO  (0.00,0.50)-(0.50,1.00)  couro escuro das luvas: rugas, costuras, desgaste assimetrico
  OSSO   (0.50,0.50)-(1.00,1.00)  osso marfim: veios, rachaduras, bordas amareladas
  PELE   (0.00,0.25)-(0.25,0.50)  pontas dos dedos expostas
  CINTA  (0.25,0.25)-(0.50,0.50)  couro mais claro das cintas, costura em tracejado
  METAL  (0.50,0.25)-(0.75,0.50)  fivelas de latao fosco
  PANO   (0.75,0.25)-(1.00,0.50)  faixa de pano verde-oliva sob a braçadeira
  PALMA  (0.00,0.00)-(0.50,0.25)  couro da palma (mais escuro, acolchoado)
"""
import os
import numpy as np
from PIL import Image

N = 512
ZONAS = {
    "couro": (0.0, 0.5, 0.5, 1.0), "osso": (0.5, 0.5, 1.0, 1.0), "pele": (0.0, 0.25, 0.25, 0.5),
    "cinta": (0.25, 0.25, 0.5, 0.5), "metal": (0.5, 0.25, 0.75, 0.5), "pano": (0.75, 0.25, 1.0, 0.5),
    "palma": (0.0, 0.0, 0.5, 0.25),
}
rng = np.random.default_rng(11)


def ruido(h, w, escala, oit=4):
    """Ruido de valor suave 0..1 (fbm)."""
    out = np.zeros((h, w)); amp = 1.0; tot = 0
    for o in range(oit):
        gh, gw = max(2, int(h / escala * 2 ** o) + 2), max(2, int(w / escala * 2 ** o) + 2)
        g = rng.random((gh, gw))
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += np.asarray(im, dtype=float) / 255 * amp; tot += amp; amp *= 0.5
    return out / tot


def zona_px(z):
    u0, v0, u1, v1 = ZONAS[z]
    return int(u0 * N), int((1 - v1) * N), int(u1 * N), int((1 - v0) * N)  # x0,y0,x1,y1 (linha 0 = topo)


def cor(rgb):
    return np.array(rgb, dtype=float)


def mistura(base, rgb, m):
    return base * (1 - m[..., None]) + cor(rgb) * m[..., None]


def couro(w, h, base, claro, rugas=1.0, desgaste=0.5, tracejado=True):
    a = ruido(h, w, 40) * 0.6 + ruido(h, w, 10) * 0.4
    img = np.zeros((h, w, 3)) + cor(base)
    img = mistura(img, claro, np.clip((a - 0.45) * 2.2, 0, 1) * 0.55)
    # rugas: ruido anisotropico + sulcos escuros
    ry = ruido(h, w, 3, 3)
    ry = np.asarray(Image.fromarray((ry * 255).astype(np.uint8)).resize((w // 6 + 2, h)).resize((w, h), Image.BICUBIC), dtype=float) / 255
    sulco = np.clip(1 - np.abs(ry - 0.5) * 9, 0, 1) ** 2
    img = mistura(img, tuple(v * 0.45 for v in base), sulco * 0.55 * rugas)
    # desgaste assimetrico: mais gasto no canto superior esquerdo (nos dos dedos), polimento claro nas quinas
    gx = np.linspace(1, 0.25, w)[None, :] * np.linspace(1, 0.4, h)[:, None]
    d = np.clip(ruido(h, w, 14) * 1.6 - 0.75, 0, 1) * gx * desgaste
    img = mistura(img, tuple(min(255, v * 1.9) for v in claro), d * 0.8)
    # arranhoes finos
    for _ in range(int(14 * desgaste * w / 128)):
        x, y = rng.integers(0, w), rng.integers(0, h)
        dx, dy = rng.normal(0, 1, 2); n = max(1.0, np.hypot(dx, dy)); dx, dy = dx / n, dy / n
        for t in range(int(rng.integers(6, 22))):
            xi, yi = int(x + dx * t), int(y + dy * t)
            if 0 <= xi < w and 0 <= yi < h:
                img[yi, xi] = img[yi, xi] * 0.6 + cor(claro) * 0.5 * 0.4 + 12
    # bordas escurecidas (sujeira de dobra)
    yy, xx = np.mgrid[0:h, 0:w]
    borda = np.minimum.reduce([xx, w - 1 - xx, yy, h - 1 - yy]) / (0.18 * min(w, h))
    img *= (0.55 + 0.45 * np.clip(borda, 0, 1))[..., None]
    if tracejado:  # costura: tracejado a 7% da borda
        m = int(0.07 * min(w, h))
        for i in range(m + 3, w - m - 3, 7):
            for k in range(4):
                for yy2 in (m, h - 1 - m):
                    img[yy2, min(w - 1, i + k)] = cor((172, 138, 96)) * 0.85
                    img[min(h - 1, yy2 + 1), min(w - 1, i + k)] = cor((60, 40, 28))
        for j in range(m + 3, h - m - 3, 7):
            for k in range(4):
                for xx2 in (m, w - 1 - m):
                    img[min(h - 1, j + k), xx2] = cor((172, 138, 96)) * 0.85
                    img[min(h - 1, j + k), min(w - 1, xx2 + 1)] = cor((60, 40, 28))
    return img


def osso(w, h):
    ivory = cor((226, 210, 174))
    a = ruido(h, w, 30) * 0.6 + ruido(h, w, 8) * 0.4
    img = np.zeros((h, w, 3)) + ivory
    img = mistura(img, (170, 142, 98), np.clip((a - 0.4) * 2.0, 0, 1) * 0.85)       # manchas ocre
    veio = np.clip(1 - np.abs(ruido(h, w, 6, 3) - 0.5) * 14, 0, 1) ** 2             # veios de osso
    img = mistura(img, (150, 124, 84), veio * 0.6)
    yy, xx = np.mgrid[0:h, 0:w]
    borda = np.minimum.reduce([xx, w - 1 - xx, yy, h - 1 - yy]) / (0.16 * min(w, h))
    b = np.clip(1 - borda, 0, 1) ** 1.5
    img = mistura(img, (205, 160, 84), b * 0.85)                                      # borda amarelada/suja
    img = mistura(img, (110, 76, 44), np.clip(1 - borda * 3.2, 0, 1) * 0.6)         # linha de sujeira na quina
    # rachaduras: caminhadas aleatorias ramificadas
    def rach(x, y, ang, n, esp):
        for t in range(n):
            ang += rng.normal(0, 0.12)
            x += np.cos(ang) * 1.6; y += np.sin(ang) * 1.6
            xi, yi = int(x), int(y)
            if not (1 <= xi < w - 1 and 1 <= yi < h - 1):
                return
            img[yi, xi] = cor((74, 52, 34))
            if esp:
                img[yi, xi + 1] = img[yi, xi + 1] * 0.5 + cor((74, 52, 34)) * 0.5
            if rng.random() < 0.03 and n - t > 14:
                rach(x, y, ang + rng.choice([-1, 1]) * 0.55, (n - t) // 2, False)
    for _ in range(9):
        rach(rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0, 6.28), int(rng.integers(25, 70)), True)
    # sulco gravado a 11% da borda + rebites nos cantos
    sul = np.abs(np.minimum.reduce([xx, w - 1 - xx, yy, h - 1 - yy]) - 0.11 * min(w, h)) < 2.4
    img = mistura(img, (92, 66, 38), sul * 0.8)
    for cx in (0.2, 0.8):
        for cy in (0.2, 0.8):
            r2 = (xx - cx * w) ** 2 + (yy - cy * h) ** 2
            img = mistura(img, (88, 64, 40), (r2 < 44) * 0.95)
            img = mistura(img, (250, 242, 222), ((xx - cx * w + 2) ** 2 + (yy - cy * h + 2) ** 2 < 8) * 0.9)
    # lascas claras nas quinas
    lasca = np.clip(ruido(h, w, 5) * 1.7 - 0.95, 0, 1) * np.clip(1 - borda, 0, 1)
    img = mistura(img, (250, 244, 224), lasca * 0.8)
    return img


def pele(w, h):
    a = ruido(h, w, 12)
    img = np.zeros((h, w, 3)) + cor((158, 112, 84))
    img = mistura(img, (118, 78, 58), a * 0.6)
    img = mistura(img, (184, 136, 104), np.clip(ruido(h, w, 5) - 0.5, 0, 1) * 1.0)
    return img


def metal(w, h):
    a = ruido(h, w, 10)
    img = np.zeros((h, w, 3)) + cor((150, 118, 62))
    img = mistura(img, (92, 70, 38), a * 0.8)
    img = mistura(img, (200, 170, 100), np.clip(ruido(h, w, 4) - 0.6, 0, 1) * 2)
    return img


def pano(w, h):
    a = ruido(h, w, 14)
    img = np.zeros((h, w, 3)) + cor((70, 82, 46))
    img = mistura(img, (46, 56, 32), a * 0.7)
    yy, xx = np.mgrid[0:h, 0:w]
    tr = (np.sin(xx * 1.6) * np.sin(yy * 1.6)) * 0.5 + 0.5          # trama
    img *= (0.86 + 0.14 * tr)[..., None]
    img = mistura(img, (112, 104, 56), np.clip(ruido(h, w, 6) - 0.55, 0, 1) * 1.8)
    return img


def main(saida):
    tex = np.zeros((N, N, 3)) + cor((60, 40, 28))
    def poe(z, im):
        x0, y0, x1, y1 = zona_px(z)
        tex[y0:y1, x0:x1] = im
    def tam(z):
        x0, y0, x1, y1 = zona_px(z); return x1 - x0, y1 - y0
    w, h = tam("couro"); poe("couro", couro(w, h, (56, 38, 28), (110, 78, 52), 1.0, 0.6))
    w, h = tam("palma"); poe("palma", couro(w, h, (40, 28, 22), (84, 60, 42), 0.7, 0.35))
    w, h = tam("cinta"); poe("cinta", couro(w, h, (98, 66, 40), (156, 112, 70), 0.6, 0.5))
    w, h = tam("osso"); poe("osso", osso(w, h))
    w, h = tam("pele"); poe("pele", pele(w, h))
    w, h = tam("metal"); poe("metal", metal(w, h))
    w, h = tam("pano"); poe("pano", pano(w, h))
    # zona livre (v<0.25, u>0.5): couro escuro liso, evita lixo no atlas
    tex[zona_px("palma")[3]:, :] = tex[zona_px("palma")[3]:, :]
    tex[N * 3 // 4:, N // 2:] = cor((44, 30, 22))
    Image.fromarray(np.clip(tex, 0, 255).astype(np.uint8)).save(saida)
    print("TEXTURA", saida)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    main(os.path.join(here, "..", "..", "..", "godot", "art", "models", "personagens", "arqueiro", "T_Arqueiro_Luvas_BC.png"))
