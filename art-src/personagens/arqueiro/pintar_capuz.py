"""Pinta as texturas proprias do capuz do Arqueiro (numpy + PIL, python do sistema).
Saida: art-src/personagens/arqueiro/texturas_capuz/*.png
  T_Capuz_BC/N (1024), T_Mascara_BC/N (512x1024), T_CapuzDetalhe_BC (512), T_Ouro_BC/N (256x1024), T_Olho_BC/E (256x128)
Rodar: python pintar_capuz.py   (depois build_capuz.py no Blender embute os PNG no .glb)
Convencao UV: v=1 e o topo da imagem. Capuz: u=0.5 e a frente (u = angulo/2pi + 0.5), u=0/1 as costas.
Mascara: u=0.25 e o vale do V central, cristas gemeas em u~0.15/0.35, u=0 e 0.5 as bordas, u .5..1 o verso; v=1 testa, v=0 ponta do bico.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "texturas_capuz")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(11)


def ruido(w, h, escala, seed):
    r = np.random.default_rng(seed)
    gw, gh = max(2, int(w / escala)), max(2, int(h / escala))
    g = r.random((gh, gw))
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im, dtype=np.float32) / 255.0


def salvar(arr, nome):
    a = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(a, "RGB").save(os.path.join(OUT, nome))
    print("ok", nome, a.shape)


def normal_de_altura(h, forca):
    """Normal map OpenGL (+Y) a partir de um mapa de altura (numpy HxW)."""
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * forca
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * forca  # y da imagem cresce para baixo
    nx, ny, nz = -gx, gy, np.ones_like(h)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([(nx / n * 0.5 + 0.5) * 255, (ny / n * 0.5 + 0.5) * 255, (nz / n * 0.5 + 0.5) * 255], -1)


def desfocar(arr, r):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def fold_f(psi, z):
    """mesma formula de build_capuz.fold_f (sombra das dobras pintada onde a geometria dobra)."""
    ph = psi * 3.0 + 1.1 * z + np.where(psi > 0, 0.55, -0.55) + 0.7 * np.sin(psi * 2.0 + z * 2.0)
    return 2.0 * np.abs(np.sin(ph)) ** 1.15 - 1.0 + 0.30 * np.sin(psi * 7.0 + z * 3.3 + 0.7) + 0.15 * np.sin(psi * 11.0 + 1.3)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ---------------- capuz 1024x1024 ----------------
def capuz():
    W = H = 1024
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1.0 - yy / H
    u = xx / W
    n1, n2, n3, n4 = ruido(W, H, 220, 1), ruido(W, H, 60, 2), ruido(W, H, 12, 3), ruido(W, H, 3, 4)
    base = np.array([58, 82, 48], np.float32)
    claro = np.array([88, 118, 66], np.float32)
    escuro = np.array([30, 44, 30], np.float32)
    ocre = np.array([104, 96, 52], np.float32)
    t = (n1 * 0.5 + n2 * 0.5)[..., None]
    img = base + (claro - base) * np.clip((t - 0.5) * 1.4, 0, 1) + (escuro - base) * np.clip((0.5 - t) * 1.4, 0, 1)
    mo = np.clip((ruido(W, H, 90, 5) - 0.60) * 5, 0, 1) * (0.35 + 0.65 * np.clip(1 - u * 1.2, 0, 1))
    img = img * (1 - mo[..., None] * 0.5) + ocre * (mo[..., None] * 0.5)
    trama = 3.0 * np.sin(xx * 1.9) * np.sin(yy * 1.9) + (n4 - 0.5) * 5
    img += trama[..., None]
    # dobras: sombra nos vales e luz nas cristas, mesmas fases da geometria
    psi = (u - 0.5) * 2 * np.pi
    z = np.clip((v - 0.02) / 0.96 * 2 - 1, -0.6, 1.0)
    env = smooth(0.55, 1.35, np.abs(psi))
    f = fold_f(psi, z)
    amp = env * (0.25 + 0.75 * smooth(0.85, -0.45, z))
    sh = 1 + 0.70 * f * amp
    vinco = np.exp(-((f + 1) / 0.16) ** 2) * amp
    sh = sh * (1 - 0.28 * vinco)
    img *= sh[..., None]
    img *= (0.80 + 0.28 * np.clip(v, 0, 1))[..., None]
    # bainha de osso-ouro fosca, borda irregular
    corte = 0.255 + 0.012 * (n2 - 0.5) * 2 + 0.008 * np.sin(u * 6.28 * 6 + 0.8)
    ouro = np.array([176, 146, 82], np.float32)
    ouro_e = np.array([100, 76, 36], np.float32)
    m = np.clip((corte - v) * 120, 0, 1)
    bainha = ouro + (ouro_e - ouro) * (n3[..., None] * 0.9) * 0.8
    costura = (np.abs(v - (corte - 0.012)) < 0.003) & ((xx % 14) < 8)
    bainha[costura] = [92, 66, 28]
    img = img * (1 - m[..., None]) + bainha * m[..., None]
    img *= (1 - np.clip(1 - np.abs(v - corte - 0.02) * 40, 0, 1)[..., None] * (m[..., None] < 0.5) * 0.30)
    topo = np.clip((v - 0.90) / 0.06, 0, 1)[..., None]
    img = img * (1 - topo) + np.array([62, 86, 52], np.float32) * topo
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, "RGBA")
    creme = (222, 204, 146, 255)
    for y in range(int(H * 0.32), int(H * 0.86), 22):   # costura central nas costas
        for ux in (2.4, W - 2.4):
            dr.ellipse([ux - 3, y, ux + 3, y + 6], fill=creme)
    for _ in range(40):   # arranhoes
        x0, y0 = rng.uniform(0, W), rng.uniform(H * 0.2, H * 0.74)
        l = rng.uniform(20, 60); a = rng.uniform(-0.6, 0.6)
        dr.line([(x0, y0), (x0 + np.sin(a) * l, y0 + np.cos(a) * l)], fill=(120, 140, 92, 80), width=2)
    im = im.filter(ImageFilter.GaussianBlur(0.8))
    salvar(np.asarray(im, np.float32), "T_Capuz_BC.png")
    alt = (n4 - 0.5) * 0.03 + (n3 - 0.5) * 0.10 + 0.6 * sh - 0.8 * vinco + 0.10 * np.sin(xx * 1.9) * np.sin(yy * 1.9)
    salvar(normal_de_altura(desfocar(np.clip(alt * 0.5 + 0.5, 0, 1), 1.0) * 2 - 1, 2.2), "T_Capuz_N.png")


# ---------------- mascara 512x1024 ----------------
def mascara():
    W, H = 512, 1024
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W, 1 - yy / H
    n1, n2, n3 = ruido(W, H, 120, 11), ruido(W, H, 32, 12), ruido(W, H, 5, 13)
    marfim = np.array([238, 220, 178], np.float32)
    osso_e = np.array([176, 146, 98], np.float32)
    img = marfim + (osso_e - marfim) * (n1 * 0.7 + n2 * 0.3)[..., None] * 0.85
    img += ((n3 - 0.5) * 20)[..., None]
    frente = u < 0.5
    d = np.abs(u - 0.25) * 4           # 0 vale central .. 1 borda
    crest = np.exp(-((np.abs(u - 0.25) - 0.10) / 0.05) ** 2)   # cristas gemeas claras
    img *= (1.0 + 0.10 * crest - 0.30 * np.clip(d - 0.5, 0, 1) ** 1.2)[..., None]
    vale = np.exp(-((u - 0.25) / 0.022) ** 2) * np.clip(v * 3, 0, 1)   # vale do V
    img *= (1 - 0.30 * vale)[..., None]
    img = np.where(frente[..., None], img, img * 0.45)
    amar = np.array([158, 116, 56], np.float32)
    k = np.clip((0.30 - v) * 2.4, 0, 1) * 0.6 + np.clip(d - 0.78, 0, 1) * 1.2
    img = img * (1 - k[..., None] * 0.5) + amar * (k[..., None] * 0.5)
    sulco = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sulco)

    def uv(uu, vv):
        return (uu * W, (1 - vv) * H)

    def linha(pts, larg):
        sd.line([uv(*p) for p in pts], fill=255, width=larg)
    for sg in (0, 1):
        f = (lambda a: a) if sg == 0 else (lambda a: 0.5 - a)
        linha([(f(0.25), 0.84), (f(0.17), 0.76), (f(0.08), 0.70)], 5)       # V da testa
        linha([(f(0.25), 0.60), (f(0.17), 0.63), (f(0.07), 0.60)], 4)       # linha da sobrancelha
        linha([(f(0.10), 0.60), (f(0.11), 0.44), (f(0.08), 0.34)], 4)       # placa da maca
        linha([(f(0.205), 0.52), (f(0.20), 0.30), (f(0.215), 0.12)], 4)     # perto do vale no bico
        linha([(f(0.14), 0.93), (f(0.09), 0.86), (f(0.05), 0.80)], 4)
    org = Image.new("L", (W, H), 0)
    od = ImageDraw.Draw(org)
    for cx in (0.075, 0.425):     # orbitas: sombra sob a sobrancelha
        od.ellipse([(cx - 0.07) * W, (1 - 0.66) * H, (cx + 0.07) * W, (1 - 0.48) * H], fill=255)
    for ini in [(0.18, 0.95), (0.33, 0.93), (0.27, 0.78), (0.40, 0.70), (0.12, 0.84), (0.22, 0.45), (0.30, 0.36), (0.15, 0.55)]:
        x, y = ini[0] * W, (1 - ini[1]) * H
        for _ in range(int(rng.integers(16, 40))):
            nx = x + rng.normal(0, 5.5); ny = y + rng.uniform(5, 15)
            sd.line([(x, y), (nx, ny)], fill=255, width=int(rng.integers(2, 6)))
            x, y = nx, ny
            if rng.random() < 0.10:
                sd.line([(x, y), (x + rng.normal(0, 24), y + rng.uniform(6, 20))], fill=255, width=2)
    s_arr = np.asarray(sulco, np.float32) / 255.0
    o_arr = np.asarray(org, np.float32) / 255.0
    s_mol = desfocar(s_arr, 2.0)
    img = img * (1 - 0.65 * s_mol[..., None]) + np.array([66, 44, 26], np.float32) * (0.65 * s_mol[..., None])
    suj = desfocar(s_arr, 8) * 0.55
    img *= (1 - suj[..., None] * 0.5)
    o_mol = desfocar(o_arr, 9)
    img = img * (1 - 0.60 * o_mol[..., None]) + np.array([60, 42, 30], np.float32) * (0.60 * o_mol[..., None])
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, "RGBA")
    for _ in range(60):
        yv = rng.uniform(0, H * 0.7)
        dr.rectangle([0, yv, rng.uniform(5, 16), yv + rng.uniform(5, 15)], fill=(110, 80, 46, 150))
    for _ in range(160):
        x0, y0 = rng.uniform(0, W * 0.5), rng.uniform(0, H)
        dr.ellipse([x0, y0, x0 + 3, y0 + 3], fill=(120, 94, 58, 110))
    im = im.filter(ImageFilter.GaussianBlur(0.7))
    salvar(np.asarray(im, np.float32), "T_Mascara_BC.png")
    alt = 0.5 + (n2 - 0.5) * 0.20 + (n3 - 0.5) * 0.10
    alt -= desfocar(s_arr, 1.8) * 1.0
    alt -= o_mol * 0.35
    salvar(normal_de_altura(alt, 4.5), "T_Mascara_N.png")


# ---------------- detalhes 512 (lenco | cabelo | pele) ----------------
def detalhe():
    W = H = 512
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.zeros((H, W, 3), np.float32)
    n2, n3 = ruido(W, H, 24, 21), ruido(W, H, 5, 22)
    Q = 256
    # TL: lenco verde-escuro; rolos horizontais e fio do tecido
    vq = 1 - yy[:Q, :Q] / Q
    verde = np.array([84, 112, 66], np.float32)
    rolo = np.abs(np.sin(vq * 3 * np.pi))
    fiapo = np.sin(xx[:Q, :Q] * 0.45 + n2[:Q, :Q] * 5) * 0.5 + 0.5
    lenco = verde * (0.45 + 0.70 * rolo[..., None] ** 0.8) * (0.9 + 0.12 * fiapo[..., None]) + ((n3[:Q, :Q] - 0.5) * 12)[..., None]
    img[:Q, :Q] = lenco
    # TR: cabelo castanho, mechas com brilho (tambem a sobrancelha)
    fio = 0.80 + 0.04 * np.sin(xx[:Q, Q:] * 0.30 + n2[:Q, Q:] * 3) + 0.08 * ruido(Q, Q, 20, 23)
    cab = np.array([112, 74, 44], np.float32) * fio[..., None]
    gv = 1 - yy[:Q, Q:] / Q
    cab *= (0.7 + 0.5 * gv)[..., None]
    img[:Q, Q:] = cab
    # BL: pele quente com sombra suave
    pele = np.array([176, 118, 82], np.float32) * (0.85 + 0.25 * n2[Q:, :Q][..., None]) + ((n3[Q:, :Q] - 0.5) * 8)[..., None]
    img[Q:, :Q] = pele
    # BR: pele mais escura (palpebras)
    img[Q:, Q:] = np.array([96, 60, 42], np.float32) * (0.9 + 0.2 * n2[Q:, Q:][..., None])
    salvar(img, "T_CapuzDetalhe_BC.png")


# ---------------- osso das placas 256x1024 (u atravessa a placa, v ao longo) ----------------
def ouro():
    W, H = 256, 1024
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W, yy / H
    n1, n2, n3 = ruido(W, H, 80, 31), ruido(W, H, 18, 32), ruido(W, H, 4, 33)
    base = np.array([242, 226, 182], np.float32)
    esc = np.array([168, 130, 72], np.float32)
    img = base + (esc - base) * (n1 * 0.6 + n2 * 0.4)[..., None] * 0.45 + ((n3 - 0.5) * 8)[..., None]
    bis = np.clip(1 - np.abs(u - 0.5) * 2, 0, 1)      # chanfro: topo claro, lados escuros
    lado = (u < 0.26) | (u > 0.74)
    img *= np.where(lado, 0.74, 1.0)[..., None]
    img *= (0.86 + 0.20 * bis ** 0.5)[..., None]
    cont = np.exp(-((np.minimum(u, 1 - u) - 0.06) / 0.018) ** 2)   # contorno escuro da placa
    img = img * (1 - 0.55 * cont[..., None]) + np.array([70, 48, 24], np.float32) * (0.55 * cont[..., None])
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, "RGBA")
    alt = Image.new("L", (W, H), 0)
    ad = ImageDraw.Draw(alt)
    for _ in range(9):   # rachaduras
        x, y = rng.uniform(20, W - 20), rng.uniform(0, H)
        for _ in range(int(rng.integers(8, 18))):
            nx, ny = x + rng.normal(0, 5), y + rng.uniform(4, 12)
            dr.line([(x, y), (nx, ny)], fill=(60, 40, 18, 210), width=2)
            ad.line([(x, y), (nx, ny)], fill=255, width=3)
            x, y = nx, ny
    for _ in range(22):   # lascas
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        dr.rectangle([x0, y0, x0 + rng.uniform(3, 12), y0 + rng.uniform(3, 10)], fill=(118, 84, 40, 140))
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    salvar(np.asarray(im, np.float32), "T_Ouro_BC.png")
    h = 0.5 + (n2 - 0.5) * 0.2 - desfocar(np.asarray(alt, np.float32) / 255.0, 1.5) * 0.9 + (bis ** 0.5 - 0.5) * 0.1
    salvar(normal_de_altura(h, 4.0), "T_Ouro_N.png")


# ---------------- olho 256x128 (amendoa: esclera, iris verde grande, pupila, brilho) + emissao so da iris ----------------
def olho():
    W, H = 256, 128
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H / 2 + 2
    img = np.zeros((H, W, 3), np.float32)
    img[:] = [214, 204, 172]            # esclera quente
    top = np.clip(1 - (yy / H) / 0.50, 0, 1)
    img *= (1 - 0.60 * top[..., None])      # sombra da palpebra
    img *= (1 - 0.35 * (np.abs(xx - cx) / cx) ** 3)[..., None]   # cantos mais escuros
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    R = 54
    ang = np.arctan2(yy - cy, xx - cx)
    fib = 0.5 + 0.5 * np.sin(ang * 34 + ruido(W, H, 12, 41) * 6)
    g = np.clip(r / R, 0, 1)
    iris = np.stack([30 + 130 * (1 - g) ** 2.2 * fib * 0.8, 120 + 125 * (1 - g) ** 1.2, 36 + 40 * (1 - g)], -1)
    iris *= (0.75 + 0.25 * fib)[..., None]
    borda = np.clip((g - 0.78) / 0.22, 0, 1)
    iris *= (1 - 0.65 * borda[..., None])             # anel do limbo escuro
    m_iris = np.clip((R - r) / 1.5, 0, 1)[..., None]
    img = img * (1 - m_iris) + iris * m_iris
    pup = np.clip((19 - r) / 1.5, 0, 1)[..., None]
    img = img * (1 - pup) + np.array([4, 10, 6], np.float32) * pup
    emis = iris * m_iris * (1 - pup)
    br = np.clip((9 - np.sqrt((xx - (cx - 17)) ** 2 + (yy - (cy - 16)) ** 2)) / 1.5, 0, 1)[..., None]
    br2 = np.clip((4 - np.sqrt((xx - (cx + 18)) ** 2 + (yy - (cy + 15)) ** 2)) / 1.2, 0, 1)[..., None]
    img = img * (1 - br) + np.array([248, 255, 240], np.float32) * br
    img = img * (1 - br2 * 0.8) + np.array([230, 255, 225], np.float32) * br2 * 0.8
    emis = emis * (1 - br) * (1 - br2)
    salvar(img, "T_Olho_BC.png")
    salvar(emis, "T_Olho_E.png")


if __name__ == "__main__":
    capuz(); mascara(); detalhe(); ouro(); olho()
