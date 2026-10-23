"""Texturas proprias de Calca e Botas do Arqueiro (1024, pintadas por script, numpy + PIL; semente fixa).
Saida: godot/art/models/personagens/arqueiro/T_Arqueiro_Calca_BC.png e T_Arqueiro_Botas_BC.png.
Rodar: python pernas_textura.py   (o layout de UV vem de pernas_atlas.py; a geometria de pernas_geo.py)
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pernas_atlas import *

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
SAIDA = os.environ.get("ARQ_SAIDA", os.path.join(RAIZ, "godot", "art", "models", "personagens", "arqueiro"))
SEED = [100]


def rng():
    SEED[0] += 1
    return np.random.default_rng(SEED[0])


def fbm(h, w, beta=2.0, ax=1.0, ay=1.0):
    """Ruido periodico (sem emenda em u e t) por filtragem de FFT; normalizado (desvio 1)."""
    b = rng().standard_normal((h, w))
    F = np.fft.fft2(b)
    fy = np.fft.fftfreq(h)[:, None] * ay
    fx = np.fft.fftfreq(w)[None, :] * ax
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    F = F * f ** (-beta / 2)
    F[0, 0] = 0
    n = np.real(np.fft.ifft2(F))
    return (n / (n.std() + 1e-9)).astype(np.float32)


def ss(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def rgb(h, *c):
    return np.broadcast_to(np.array(c, np.float32), (h[0], h[1], 3)).copy() if False else np.array(c, np.float32)


def coords(h, w):
    """u em [0,1) por coluna, t em [0,1] por linha (t=1 em cima do retangulo, como no uvmap)."""
    u = (np.arange(w, dtype=np.float32) + 0.5)[None, :] / w
    t = 1.0 - (np.arange(h, dtype=np.float32) + 0.5)[:, None] / h
    return np.broadcast_to(u, (h, w)), np.broadcast_to(t, (h, w))


def leather(h, w, base, seed_wr=1.0, rugas=1.0, poros=1.0, ax=1.0, ay=1.0):
    """Couro: tom grande, rugas em crista, poros, grao fino."""
    n1 = fbm(h, w, 2.2, ax, ay)
    n2 = fbm(h, w, 1.4, ax, ay)
    cr = 1 - np.abs(fbm(h, w, 1.6, ax * 1.3, ay)) / 1.6
    cr = np.clip(cr, 0, 1) ** 6 * rugas          # vinco fino
    pore = fbm(h, w, 0.2)
    pores = ss(pore, 1.6, 2.4) * poros            # pontinhos escuros
    grain = fbm(h, w, 0.5)
    base = np.array(base, np.float32)
    tone = 1 + 0.16 * n1 + 0.07 * n2 + 0.03 * grain
    col = base[None, None, :] * tone[..., None]
    col *= (1 - 0.55 * cr)[..., None]
    col *= (1 - 0.35 * pores)[..., None]
    # brilho do couro em cristas suaves
    hi = ss(n2, 0.9, 2.2) * 0.22
    col += np.array([0.95, 0.75, 0.5], np.float32) * hi[..., None] * base.mean() * 1.6
    return col


def cloth(h, w, base, fio=0.5):
    n1 = fbm(h, w, 2.0)
    n2 = fbm(h, w, 1.0)
    uu, tt = coords(h, w)
    trama = 0.5 + 0.5 * np.sin(uu * w * 1.9) * np.sin(tt * h * 1.9)
    base = np.array(base, np.float32)
    col = base[None, None, :] * (1 + 0.14 * n1 + 0.06 * n2 + 0.08 * fio * (trama - 0.5))[..., None]
    return col


def vinco(h, w, t0, larg, forca, amp_u=0.0, fase=0.0):
    """Faixa horizontal escura (dobra) em t0 com contorno levemente ondulado."""
    uu, tt = coords(h, w)
    desl = amp_u * np.sin(uu * math.tau * 3 + fase) * 0.02
    d = np.abs(tt - t0 - desl) / larg
    return np.exp(-d * d * 2.5) * forca


def to_img(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")


def from_img(im):
    return np.asarray(im, np.float32) / 255.0


def tracejado(im, p0, p1, cor, dash=7, gap=5, larg=2, sombra=True):
    """Costura: tracos curtos alinhados (com sombra de 1 px) de p0 a p1."""
    d = ImageDraw.Draw(im)
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    n = max(1, int(L // (dash + gap)))
    ux, uy = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L
    for k in range(n + 1):
        a = k * (dash + gap)
        b = min(a + dash, L)
        if a >= L:
            break
        pa = (p0[0] + ux * a, p0[1] + uy * a)
        pb = (p0[0] + ux * b, p0[1] + uy * b)
        if sombra:
            d.line([(pa[0] + 1, pa[1] + 2), (pb[0] + 1, pb[1] + 2)], fill=(20, 12, 6), width=larg)
        d.line([pa, pb], fill=cor, width=larg)


def rachadura(im, ini, n, passo, cor, rs, larg=1, deriva=0.0):
    d = ImageDraw.Draw(im)
    x, y = ini
    ang = rs.uniform(0, math.tau) if deriva == 0 else deriva
    for k in range(n):
        ang += rs.normal(0, 0.45)
        nx, ny = x + math.cos(ang) * passo, y + math.sin(ang) * passo
        d.line([(x, y), (nx, ny)], fill=cor, width=larg)
        if rs.random() < 0.12:
            rachadura(im, (nx, ny), n // 3, passo * 0.8, cor, rs, larg, ang + rs.choice([-1, 1]) * 0.7)
        x, y = nx, ny


def arranhoes(a, n, rs, claro=(0.8, 0.6, 0.4), comp=40, forca=0.5):
    h, w = a.shape[:2]
    im = to_img(a)
    ov = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(ov)
    for _ in range(n):
        x, y = rs.uniform(0, w), rs.uniform(0, h)
        ang = rs.normal(0.3, 0.5)
        L = rs.uniform(0.3, 1) * comp
        d.line([(x, y), (x + math.cos(ang) * L, y + math.sin(ang) * L)], fill=int(rs.uniform(80, 255)), width=1)
    m = np.asarray(ov, np.float32)[..., None] / 255 * forca
    return a * (1 - m) + np.array(claro, np.float32) * m


def borda_clara(a, px, cor, forca=0.8, escuro=0.0):
    """Realce de aresta: faixa clara de 'px' no contorno do retangulo e gradiente para dentro."""
    h, w = a.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.minimum(np.minimum(x, w - 1 - x), np.minimum(y, h - 1 - y))
    m = (1 - ss(d, 0, px))[..., None] * forca
    a = a * (1 - m) + np.array(cor, np.float32) * m
    if escuro:
        m2 = ((1 - ss(d, px, px * 4))[..., None]) * escuro
        a = a * (1 - m2)
    return a


def cinto_furos(im, y, xs, r=3):
    d = ImageDraw.Draw(im)
    for x in xs:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(14, 8, 5), outline=(150, 110, 70))


# ====================================================================== CALCA
def pant(w, h):
    a = cloth(h, w, (0.19, 0.14, 0.10), 0.7)
    uu, tt = coords(h, w)
    # rugas longas de tecido (coxa: diagonais; canela: verticais)
    d1 = fbm(h, w, 1.8, 2.5, 0.7)
    rug = np.clip(1 - np.abs(d1) / 1.5, 0, 1) ** 5
    a *= (1 - 0.5 * rug * ss(tt, 0.15, 0.9))[..., None]
    # dobras: creases em t = (z-0.2)/0.36 para z = .355 .375 .44 .48
    for z, f in ((0.355, 0.9), (0.44, 0.6), (0.48, 0.0), (0.375, -0.5)):
        t0 = (z - Z_HEM) / (Z_TOP - Z_HEM)
        v = vinco(h, w, t0, 0.014, 0.75 if f > 0 else 0.0, 1.0, z * 20)
        if f > 0:
            a *= (1 - v)[..., None]
        elif f < 0:    # bojo claro acima da dobra
            hl = vinco(h, w, t0 + 0.012, 0.03, 0.35, 1.0, z * 20)
            a += np.array([0.3, 0.22, 0.14], np.float32) * hl[..., None]
    # sujeira na barra e nas dobras, desgaste claro nos joelhos/coxas da frente
    suj = ss(0.22 - tt, 0, 0.22)
    a = a * (1 - 0.35 * suj)[..., None] + np.array([0.20, 0.14, 0.07], np.float32) * (0.35 * suj * (fbm(h, w, 1.5) > 0.2))[..., None]
    desg = ss(fbm(h, w, 2.4), 0.8, 2.0) * ss(np.cos((uu - 0.25) * math.tau), 0.2, 0.9) * ss(tt, 0.3, 0.7)
    a += np.array([0.12, 0.09, 0.06], np.float32) * desg[..., None]
    im = to_img(a)
    # costuras: lateral externa (u=.5), interna (u=0/1), remendo na coxa
    for u in (0.5, 0.0):
        x = u * w
        for dx in ([-4, 4] if u == 0.5 else [4, w - 4]):
            tracejado(im, (x + dx if u == 0.5 else dx, 4), (x + dx if u == 0.5 else dx, h - 4), (170, 140, 95), 6, 5)
    d = ImageDraw.Draw(im)
    # remendo de couro costurado na coxa (frente-fora)
    px0, py0, px1, py1 = int(w * 0.60), int(h * 0.16), int(w * 0.72), int(h * 0.34)
    pat = from_img(im)
    pl = leather(py1 - py0, px1 - px0, (0.33, 0.20, 0.11))
    pl = borda_clara(pl, 3, (0.75, 0.55, 0.32), 0.7, 0.2)
    pat[py0:py1, px0:px1] = pl
    im = to_img(pat)
    for (a0, a1) in (((px0 + 5, py0 + 5), (px1 - 5, py0 + 5)), ((px1 - 5, py0 + 5), (px1 - 5, py1 - 5)),
                     ((px1 - 5, py1 - 5), (px0 + 5, py1 - 5)), ((px0 + 5, py1 - 5), (px0 + 5, py0 + 5))):
        tracejado(im, a0, a1, (190, 160, 110), 5, 4)
    a = arranhoes(from_img(im), 60, rng(), (0.45, 0.35, 0.25), 34, 0.35)
    return a


def knee(w, h):
    a = leather(h, w, (0.34, 0.20, 0.11), rugas=1.3)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    a *= (0.8 + 0.35 * (1 - np.clip(r, 0, 1.2)))[..., None]     # cupula: centro claro
    a = a * (1 - 0.35 * ss(r, 0.5, 1.2))[..., None]
    a += np.array([0.5, 0.38, 0.22], np.float32) * (0.25 * np.exp(-((x - w * 0.42) ** 2 + (y - h * 0.38) ** 2) / (w * 8.5)))[..., None]
    a = borda_clara(a, 5, (0.80, 0.60, 0.35), 0.75, 0.25)
    im = to_img(a)
    m = 16
    for p0, p1 in (((m, m), (w - m, m)), ((w - m, m), (w - m, h - m)), ((w - m, h - m), (m, h - m)), ((m, h - m), (m, m))):
        tracejado(im, p0, p1, (205, 175, 120), 7, 5, 2)
    d = ImageDraw.Draw(im)
    for cx, cy in ((m, m), (w - m, m), (w - m, h - m), (m, h - m)):
        d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(130, 100, 55), outline=(30, 20, 10))
        d.ellipse([cx - 2, cy - 3, cx, cy - 1], fill=(240, 215, 150))
    rs = rng()
    for _ in range(3):
        rachadura(im, (rs.uniform(w * .2, w * .8), rs.uniform(h * .3, h * .7)), 8, 6, (40, 24, 12), rs)
    return arranhoes(from_img(im), 40, rs, (0.75, 0.55, 0.35), 30, 0.45)


def wrap(w, h):
    a = cloth(h, w, (0.17, 0.29, 0.105), 1.3)
    uu, tt = coords(h, w)
    fios = 0.5 + 0.5 * np.sin(uu * w * 0.9 + 6 * fbm(h, w, 2.0))
    a *= (0.88 + 0.22 * fios)[..., None]
    a += np.array([0.18, 0.22, 0.05], np.float32) * (ss(fbm(h, w, 2.5), 0.5, 2.0) * 0.5)[..., None]
    a *= (1 - 0.55 * ss(0.12 - np.minimum(tt, 1 - tt), 0, 0.12))[..., None]    # bordas sombreadas (camada sobre camada)
    # sujeira / manchas marrons
    a = a * (1 - 0.3 * ss(fbm(h, w, 2.8), 0.6, 2.0))[..., None] + np.array([0.15, 0.10, 0.05], np.float32) * (0.2 * ss(fbm(h, w, 2.8), 1.0, 2.4))[..., None]
    im = to_img(a)
    d = ImageDraw.Draw(im)
    rs = rng()
    for _ in range(90):   # fios soltos nas bordas
        x = rs.uniform(0, w)
        y0 = 0 if rs.random() < 0.5 else h
        d.line([(x, y0), (x + rs.normal(0, 4), y0 + (6 if y0 == 0 else -6) * rs.uniform(0.5, 1.5))], fill=(90, 120, 45), width=1)
    return from_img(im)


def strap(w, h, base=(0.20, 0.11, 0.06)):
    a = leather(h, w, base, rugas=0.8)
    a = borda_clara(a, 3, (0.7, 0.5, 0.3), 0.5, 0.25)
    im = to_img(a)
    tracejado(im, (0, 7), (w, 7), (200, 168, 110), 8, 5, 1)
    tracejado(im, (0, h - 8), (w, h - 8), (200, 168, 110), 8, 5, 1)
    cinto_furos(im, h // 2, range(40, w, 70), 3)
    return from_img(im)


def metal(w, h):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    g = 0.65 + 0.35 * np.cos((y / h - 0.35) * 3.0)
    a = np.array([0.78, 0.60, 0.26], np.float32)[None, None, :] * g[..., None]
    a *= (1 + 0.1 * fbm(h, w, 1.2))[..., None]
    a += (ss(fbm(h, w, 0.8), 1.8, 2.8) * 0.5)[..., None]
    return np.clip(a, 0, 1)


def folha(w, h, tipo):
    """Lamina de barra: topo (y=0) = fixacao no cinto, base = ponta. tipo 0 folha verde, 1 pena marfim, 2 folha escura/couro."""
    uu, tt = coords(h, w)
    s = 1 - tt                                   # 0 topo, 1 ponta
    cen = np.abs(uu - 0.5) * 2
    n = fbm(h, w, 2.0)
    if tipo == 0:
        base = np.array([0.12, 0.25, 0.08], np.float32)
        ponta = np.array([0.30, 0.40, 0.11], np.float32)
    elif tipo == 1:
        base = np.array([0.62, 0.54, 0.38], np.float32)
        ponta = np.array([0.82, 0.74, 0.56], np.float32)
    else:
        base = np.array([0.10, 0.15, 0.07], np.float32)
        ponta = np.array([0.24, 0.22, 0.10], np.float32)
    a = base * (1 - s[..., None]) + ponta * s[..., None]
    a *= (1 + 0.12 * n)[..., None]
    # nervura central e secundarias
    veia = np.exp(-(cen * w / 2.2) ** 2 / 2) * 0.35
    sec = np.maximum(0, np.sin((s * 14 + cen * 4.5) * math.pi)) ** 8 * ss(cen, 0.08, 0.5) * (1 - ss(cen, 0.6, 1.0)) * 0.22
    cor_v = np.array([0.55, 0.65, 0.30], np.float32) if tipo != 1 else np.array([0.55, 0.45, 0.30], np.float32)
    a = a * (1 - (veia + sec)[..., None] * 0.5) + cor_v * ((veia + sec) * 0.5)[..., None] * (0.6 if tipo == 1 else 1.0)
    if tipo == 1:   # barbas
        barb = np.sin((s * 40 + cen * 6 * np.sign(uu - 0.5)) * math.pi) * 0.5 + 0.5
        a *= (0.85 + 0.2 * barb)[..., None]
        a *= (1 - 0.5 * ss(np.abs(s - 0.72), 0.1, 0.0) * (cen < 2))[..., None] if False else 1
        band = ss(np.abs(s - 0.78), 0.05, 0.0)
        a = a * (1 - 0.35 * band)[..., None] + np.array([0.35, 0.22, 0.10], np.float32) * (0.35 * band)[..., None]
    a *= (1 - 0.5 * ss(cen, 0.75, 1.0))[..., None]       # borda escurece
    a *= (0.62 + 0.38 * ss(s, 0.0, 0.25))[..., None]      # sombra perto do cinto
    return np.clip(a, 0, 1)


def pelv(w, h):
    uu, tt = coords(h, w)
    a = leather(h, w, (0.20, 0.12, 0.07), rugas=0.8)
    a[: int(h * 0.45)] = cloth(int(h * 0.45), w, (0.18, 0.13, 0.09), 0.6)      # parte de baixo: tecido da calca (t baixo = linhas finais)
    a = borda_clara(a, 2, (0.5, 0.4, 0.3), 0.3)
    im = to_img(a)
    d = ImageDraw.Draw(im)
    tracejado(im, (0, int(h * 0.12)), (w, int(h * 0.12)), (190, 160, 110), 7, 5, 1)
    tracejado(im, (0, int(h * 0.50)), (w, int(h * 0.50)), (190, 160, 110), 7, 5, 1)
    for x in range(10, w, 32):
        d.ellipse([x - 3, h * 0.30 - 3, x + 3, h * 0.30 + 3], fill=(150, 112, 55), outline=(30, 20, 10))
    return from_img(im)


def montar_calca():
    A = np.zeros((TAM, TAM, 3), np.float32)
    A[...] = (0.17, 0.12, 0.08)

    def pos(nome, arr):
        x0, y0, x1, y1 = CALCA[nome]
        A[y0:y1, x0:x1] = arr
    r = lambda n: (CALCA[n][3] - CALCA[n][1], CALCA[n][2] - CALCA[n][0])
    pos("PANT", pant(CALCA["PANT"][2] - CALCA["PANT"][0], CALCA["PANT"][3] - CALCA["PANT"][1]))
    pos("PELV", pelv(CALCA["PELV"][2] - CALCA["PELV"][0], CALCA["PELV"][3] - CALCA["PELV"][1]))
    pos("KNEE", knee(CALCA["KNEE"][2] - CALCA["KNEE"][0], CALCA["KNEE"][3] - CALCA["KNEE"][1]))
    pos("WRAP", wrap(CALCA["WRAP"][2] - CALCA["WRAP"][0], CALCA["WRAP"][3] - CALCA["WRAP"][1]))
    pos("STRAP", strap(CALCA["STRAP"][2] - CALCA["STRAP"][0], CALCA["STRAP"][3] - CALCA["STRAP"][1]))
    pos("METAL", metal(CALCA["METAL"][2] - CALCA["METAL"][0], CALCA["METAL"][3] - CALCA["METAL"][1]))
    for i, n in enumerate(("F0", "F1", "F2")):
        pos(n, folha(CALCA[n][2] - CALCA[n][0], CALCA[n][3] - CALCA[n][1], i))
    # restos livres (y 470..608 a direita)
    return A


# ====================================================================== BOTAS
OSSO = (0.84, 0.74, 0.55)


def cano(w, h):
    a = leather(h, w, (0.34, 0.20, 0.10), rugas=1.4, ay=1.0)
    uu, tt = coords(h, w)
    # rugas de acordeao no tornozelo (embaixo) e dobras horizontais
    for t0, f in ((0.12, 0.8), (0.26, 0.6), (0.40, 0.4)):
        v = vinco(h, w, t0, 0.022, f, 1.5, t0 * 50)
        a *= (1 - 0.6 * v)[..., None]
        a += np.array([0.35, 0.24, 0.14], np.float32) * (vinco(h, w, t0 + 0.04, 0.03, 0.25, 1.5, t0 * 50))[..., None]
    # sujeira embaixo, couro claro gasto na frente (u=.25), escuro atras
    a *= (1 - 0.45 * ss(0.3 - tt, 0, 0.3))[..., None]
    gasto = ss(fbm(h, w, 2.2), 0.6, 2.0) * ss(np.cos((uu - 0.25) * math.tau), 0.1, 0.9)
    a += np.array([0.16, 0.11, 0.06], np.float32) * gasto[..., None]
    lama = ss(fbm(h, w, 2.8) + (0.25 - tt) * 4, 1.2, 2.2)
    a = a * (1 - 0.5 * lama)[..., None] + np.array([0.14, 0.09, 0.05], np.float32) * (0.5 * lama)[..., None]
    im = to_img(a)
    xb = int(w * 0.75)
    tracejado(im, (xb - 5, 6), (xb - 5, h - 6), (200, 165, 105), 7, 5, 2)    # costura traseira
    tracejado(im, (xb + 5, 6), (xb + 5, h - 6), (200, 165, 105), 7, 5, 2)
    tracejado(im, (0, int(h * 0.12)), (w, int(h * 0.12)), (200, 165, 105), 8, 6, 1)
    rs = rng()
    for _ in range(5):
        rachadura(im, (rs.uniform(0, w), rs.uniform(h * 0.2, h * 0.9)), 7, 5, (35, 20, 10), rs)
    return arranhoes(from_img(im), 120, rs, (0.78, 0.58, 0.38), 45, 0.4)


def upper(w, h):
    a = leather(h, w, (0.36, 0.21, 0.11), rugas=1.2, ay=1.7)
    uu, tt = coords(h, w)
    # u=0 externo, .25 topo, .5 interno, .75 sola. t=0 calcanhar, 1 bico
    topo = np.exp(-((uu - 0.25) / 0.20) ** 2)
    # dobras do peito do pe (ao dobrar o dedao): vincos em t .42..0.55
    for t0 in (0.45, 0.54, 0.62):
        v = vinco(h, w, t0, 0.018, 0.7, 0.3, t0 * 9) * topo
        a *= (1 - 0.6 * v)[..., None]
    # biqueira (t>.78): couro mais escuro e reforcado, costura em arco
    bq = ss(tt, 0.76, 0.80)
    a = a * (1 - 0.25 * bq)[..., None]
    # gasto claro na ponta
    gast = ss(tt, 0.85, 1.0) * ss(fbm(h, w, 2.0), 0.0, 1.5) * np.exp(-((uu - 0.25) / 0.25) ** 2)
    a += np.array([0.26, 0.18, 0.10], np.float32) * gast[..., None]
    # sujeira perto da sola
    low = ss(np.abs(uu - 0.75), 0.0, 0.16)
    a *= (1 - 0.5 * (1 - low))[..., None] * 1
    a = a * (1 - 0.0)
    im = to_img(a)
    for xx in (0.60, 0.90):
        tracejado(im, (xx * w, 0), (xx * w, h), (205, 170, 110), 8, 6, 2)
    tracejado(im, (0, 0.78 * h), (w, 0.78 * h), (205, 170, 110), 8, 6, 2)  # nota: t=.78 -> y=(1-.78)*h
    rs = rng()
    for _ in range(6):
        rachadura(im, (rs.uniform(0, w), rs.uniform(0, h)), 8, 5, (35, 20, 10), rs)
    return arranhoes(from_img(im), 140, rs, (0.8, 0.6, 0.4), 40, 0.45)


def sola(w, h):
    a = np.zeros((h, w, 3), np.float32)
    a[...] = (0.09, 0.06, 0.045)
    n = fbm(h, w, 1.6)
    a *= (1 + 0.25 * n)[..., None]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    im = to_img(a)
    d = ImageDraw.Draw(im)
    # banda de rodagem: blocos
    for yy in range(14, h - 14, 22):
        for xx in range(10, w - 10, 26):
            off = 13 if (yy // 22) % 2 else 0
            d.rectangle([xx + off, yy, xx + off + 18, yy + 14], fill=(30, 21, 15), outline=(52, 38, 27))
    d.rectangle([0, 0, w - 1, h - 1], outline=(70, 50, 34), width=4)
    return arranhoes(from_img(im), 30, rng(), (0.35, 0.26, 0.18), 30, 0.4)


def solaw(w, h):
    a = np.zeros((h, w, 3), np.float32)
    uu, tt = coords(h, w)
    n = fbm(h, w, 1.5)
    borra = np.array([0.08, 0.055, 0.04], np.float32)
    meio = np.array([0.16, 0.10, 0.065], np.float32)
    a[...] = meio * (1 + 0.2 * n)[..., None]
    a = np.where((tt < 0.3)[..., None], borra * (1 + 0.2 * n)[..., None], a)
    # vira de couro (welt) no topo
    welt = np.array([0.40, 0.25, 0.13], np.float32) * (1 + 0.15 * n)[..., None]
    a = np.where((tt > 0.72)[..., None], welt, a)
    im = to_img(a)
    tracejado(im, (0, h * (1 - 0.86)), (w, h * (1 - 0.86)), (215, 180, 120), 6, 4, 1)
    return from_img(im)


def placa(w, h, rs, tipo):
    uu, tt = coords(h, w)
    base = np.array(OSSO, np.float32)
    n = fbm(h, w, 2.4, 1.0, 0.7)
    a = base[None, None, :] * (1 + 0.09 * n)[..., None]
    # sulcos/fibras do osso ao longo de t e leve amarelado
    fib = np.sin((uu * (9 + tipo) + 0.8 * fbm(h, w, 2.5)) * math.pi) * 0.5 + 0.5
    a *= (0.9 + 0.12 * fib)[..., None]
    a += np.array([0.06, 0.03, -0.04], np.float32) * ss(n, 0.5, 2.0)[..., None]
    # sujeira marrom nas bordas e manchas
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.minimum(np.minimum(x, w - 1 - x), np.minimum(y, h - 1 - y))
    sujo = (1 - ss(d, 2, 22)) * ss(fbm(h, w, 2.2), -0.3, 1.5)
    a = a * (1 - 0.42 * sujo)[..., None] + np.array([0.33, 0.22, 0.12], np.float32) * (0.42 * sujo)[..., None]
    # gradiente: topo claro / base suja
    a *= (0.82 + 0.28 * tt)[..., None]
    a = borda_clara(a, 4, (0.99, 0.96, 0.86), 0.9, 0.22)
    # sombra de cavidade interna
    im = to_img(a)
    d_ = ImageDraw.Draw(im)
    for _ in range(3):
        rachadura(im, (rs.uniform(w * .15, w * .85), rs.uniform(h * 0.1, h * 0.9)), 14, 6, (86, 62, 42), rs)
    d_.rectangle([6, 6, w - 7, h - 7], outline=(150, 128, 98), width=1)
    cx = w // 2
    for yy in (h // 6, h - h // 6):   # rebites
        d_.ellipse([cx - 4, yy - 4, cx + 4, yy + 4], fill=(180, 138, 66), outline=(30, 22, 12))
        d_.ellipse([cx - 2, yy - 3, cx - 0, yy - 1], fill=(250, 230, 160))
    return from_img(im)


def cuff(w, h):
    a = leather(h, w, (0.40, 0.24, 0.12), rugas=1.0)
    uu, tt = coords(h, w)
    a *= (0.85 + 0.3 * ss(tt, 0.4, 1.0))[..., None]      # topo do bordo: claro (quina gasta)
    a = borda_clara(a, 3, (0.80, 0.60, 0.36), 0.6, 0.15)
    im = to_img(a)
    tracejado(im, (0, h * 0.62), (w, h * 0.62), (215, 180, 120), 8, 5, 1)
    rs = rng()
    return arranhoes(from_img(im), 40, rs, (0.82, 0.64, 0.42), 30, 0.4)


def montar_botas():
    A = np.zeros((TAM, TAM, 3), np.float32)
    A[...] = (0.20, 0.12, 0.07)

    def sz(n):
        x0, y0, x1, y1 = BOTAS[n]
        return x1 - x0, y1 - y0

    def pos(nome, arr):
        x0, y0, x1, y1 = BOTAS[nome]
        A[y0:y1, x0:x1] = arr
    pos("CANO", cano(*sz("CANO")))
    pos("UPPER", upper(*sz("UPPER")))
    pos("SOLE", sola(*sz("SOLE")))
    pos("SOLEW", solaw(*sz("SOLEW")))
    for i, n in enumerate(("PLATE_O", "PLATE_I", "PLATE_F")):
        pos(n, placa(*sz(n), rng(), i))
    pos("CUFF", cuff(*sz("CUFF")))
    pos("STRAP", strap(*sz("STRAP"), base=(0.16, 0.09, 0.05)))
    pos("METAL", metal(*sz("METAL")))
    return pintar_botas(A)


def pintar_botas(A):
    """Acabamento 'pintado a mao': tira o ruido fotografico do couro e do osso, cria bandas suaves de luz e saturacao."""
    out = A.copy()
    for nome, raio, bandas in (("CANO", 2.2, 5), ("UPPER", 2.2, 5), ("CUFF", 1.8, 4), ("PLATE_O", 1.6, 4),
                               ("PLATE_I", 1.6, 4), ("PLATE_F", 1.6, 4), ("SOLE", 1.0, 0), ("SOLEW", 1.0, 0), ("STRAP", 1.0, 0)):
        x0, y0, x1, y1 = BOTAS[nome]
        im = Image.fromarray((np.clip(A[y0:y1, x0:x1], 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")
        if raio > 1.5:
            im = im.filter(ImageFilter.MedianFilter(5))      # some riscos e rachaduras finas
        im = im.filter(ImageFilter.GaussianBlur(raio)).filter(ImageFilter.UnsharpMask(2, 60, 3))
        r = np.asarray(im, np.float32) / 255
        lum = (r * np.array([0.3, 0.55, 0.15], np.float32)).sum(-1, keepdims=True)
        if bandas:
            q = np.round(lum * bandas) / bandas
            q = lum * 0.45 + q * 0.55                       # bandas suaves de pintura
            r = r * (q / (lum + 1e-4))
        gray = r.mean(-1, keepdims=True)
        r = gray + (r - gray) * 1.12                        # mais saturado, quente
        r = 0.5 + (r - 0.5) * 1.08
        if nome.startswith('PLATE'):
            r = r * 1.10 + 0.02
        out[y0:y1, x0:x1] = np.clip(r, 0, 1)
    return out


def salvar(A, nome):
    os.makedirs(SAIDA, exist_ok=True)
    Image.fromarray((np.clip(A, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(SAIDA, nome), optimize=True)
    print("OK", nome)


if __name__ == "__main__":
    salvar(montar_calca(), "T_Arqueiro_Calca_BC.png")
    salvar(montar_botas(), "T_Arqueiro_Botas_BC.png")
