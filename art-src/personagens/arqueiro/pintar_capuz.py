"""Pinta as texturas proprias do capuz do Arqueiro (numpy + PIL, python do sistema).
Saida: art-src/personagens/arqueiro/texturas_capuz/*.png
  T_Capuz_BC/N (512), T_Mascara_BC/N (256x512), T_CapuzDetalhe_BC (512), T_Ouro_BC (128x512), T_Olho_BC (128x64)
Rodar: python pintar_capuz.py   (depois build_capuz.py no Blender embute os PNG no .glb)
Convencao UV: v=1 e o topo da imagem. Capuz: u=0.5 e a frente (u = angulo/2pi + 0.5), u=0/1 as costas.
Mascara: u=0.25 e a crista central, u=0 e 0.5 as bordas, u .5..1 o verso; v=1 testa, v=0 ponta do bico.
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
    """Normal map OpenGL (+Y) a partir de um mapa de altura 0..1 (numpy HxW)."""
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * forca
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * forca  # y da imagem cresce para baixo
    nx, ny, nz = -gx, gy, np.ones_like(h)  # +Y = para cima na tela
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([(nx / n * 0.5 + 0.5) * 255, (ny / n * 0.5 + 0.5) * 255, (nz / n * 0.5 + 0.5) * 255], -1)


def desfocar(arr, r):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


# ---------------- capuz 512x512 ----------------
def capuz():
    W = H = 512
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1.0 - yy / H
    u = xx / W
    n1, n2, n3 = ruido(W, H, 110, 1), ruido(W, H, 30, 2), ruido(W, H, 6, 3)
    base = np.array([54, 76, 46], np.float32)
    claro = np.array([74, 100, 58], np.float32)
    escuro = np.array([32, 46, 32], np.float32)
    ocre = np.array([92, 86, 48], np.float32)
    t = (n1 * 0.55 + n2 * 0.45)[..., None]
    img = base + (claro - base) * np.clip((t - 0.5) * 2.6, 0, 1) + (escuro - base) * np.clip((0.5 - t) * 2.6, 0, 1)
    # manchas de ocre (camuflagem do traje), concentradas num lado
    mo = np.clip((ruido(W, H, 50, 5) - 0.62) * 5, 0, 1) * (0.4 + 0.6 * np.clip(1 - u * 1.2, 0, 1))
    img = img * (1 - mo[..., None] * 0.55) + ocre * (mo[..., None] * 0.55)
    # trama do tecido (linhas) e fibra
    trama = (n3 - 0.5) * 12 + (ruido(W, H, 2, 9) - 0.5) * 6
    img += trama[..., None]
    # sombra nos vales das dobras: mesmas fases do deslocamento da geometria (build_capuz.dobra)
    psi = (u - 0.5) * 2 * np.pi
    env = np.clip((np.abs(psi) - 0.9) / 0.6, 0, 1)
    vale = 0.5 + 0.5 * np.sin(psi * 4 + 0.9 + np.sign(psi) * 0.5)
    img *= (1 - 0.30 * env * (1 - vale) * np.clip(1.15 - v, 0.2, 1))[..., None]
    img *= (0.78 + 0.30 * np.clip(v, 0, 1))[..., None]
    # bainha dourada fosca com borda irregular e desgaste assimetrico
    corte = 0.27 + 0.03 * (n2 - 0.5) * 2 + 0.015 * np.sin(u * 6.28 * 3 + 0.8)
    ouro = np.array([170, 138, 72], np.float32)
    ouro_e = np.array([98, 74, 34], np.float32)
    m = np.clip((corte - v) * 70, 0, 1)
    falha = (n2 * 0.7 + n3 * 0.3) > (0.60 + 0.20 * np.clip((u - 0.3) * 2, 0, 1))
    m = m * (~falha)
    bainha = ouro + (ouro_e - ouro) * (n3[..., None] * 0.9) * 0.9
    costura = (np.abs(v - (corte - 0.03)) < 0.0045) & ((xx % 10) < 6)
    bainha[costura] = [92, 66, 28]
    img = img * (1 - m[..., None]) + bainha * m[..., None]
    sh = np.clip(1 - np.abs(v - corte - 0.04) * 26, 0, 1)[..., None] * (m[..., None] < 0.5) * 0.28
    img *= (1 - sh)
    # polo do topo liso (esconde a convergencia do UV)
    topo = np.clip((v - 0.88) / 0.07, 0, 1)[..., None]
    img = img * (1 - topo) + np.array([60, 82, 50], np.float32) * topo
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, "RGBA")
    # costura central em V de pontos creme: costas (u=0/1) e V sobre a testa (u=0.5)
    creme = (214, 196, 134, 255)
    for y in range(int(H * 0.32), int(H * 0.86), 12):
        for ux in (1.2, W - 1.2):
            dr.ellipse([ux - 1.6, y, ux + 1.6, y + 3.2], fill=creme)
    for sgn in (-1, 1):  # V das costuras: dois ramos abertos para cima a partir do vinco central
        for k in range(1, 9):
            f = k / 8
            x = (W if sgn > 0 else 0) - sgn * f * W * 0.07
            y = H * (0.30 - 0.0 + 0.0) + (1 - f) * 0 - f * 0 + (H * 0.16) * (1 - f) * 0 + H * (0.34 - 0.14 * f) * 0 + (H * 0.32 - f * H * 0.13)
            dr.ellipse([x - 1.6, y - 1.6, x + 1.6, y + 1.6], fill=creme)
    # remendos, arranhoes e manchas pintadas
    for _ in range(26):
        x0, y0 = rng.uniform(0, W), rng.uniform(H * 0.2, H * 0.74)
        if x0 > W * 0.6 and rng.random() < 0.6:
            continue
        l = rng.uniform(10, 30); a = rng.uniform(-0.6, 0.6)
        dr.line([(x0, y0), (x0 + np.sin(a) * l, y0 + np.cos(a) * l)], fill=(112, 130, 84, 90), width=1)
    for _ in range(70):
        x0, y0 = rng.uniform(0, W), rng.uniform(H * 0.14, H * 0.8)
        l = rng.uniform(12, 36)
        dr.ellipse([x0, y0, x0 + l * 0.4, y0 + l], fill=(26, 40, 26, 42))
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    salvar(np.asarray(im, np.float32), "T_Capuz_BC.png")
    # normal: trama + costura
    alt = (n3 - 0.5) * 0.9 + n2 * 0.5
    salvar(normal_de_altura(alt, 1.2), "T_Capuz_N.png")


# ---------------- mascara 256x512 ----------------
def mascara():
    W, H = 256, 512
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W, 1 - yy / H
    n1, n2, n3 = ruido(W, H, 60, 11), ruido(W, H, 16, 12), ruido(W, H, 3, 13)
    marfim = np.array([232, 214, 172], np.float32)
    osso_e = np.array([170, 142, 96], np.float32)
    img = marfim + (osso_e - marfim) * (n1 * 0.7 + n2 * 0.3)[..., None] * 0.85
    img += ((n3 - 0.5) * 22)[..., None]
    frente = u < 0.5
    d = np.abs(u - 0.25) * 4           # 0 crista .. 1 borda
    img *= (1.10 - 0.34 * np.clip(d, 0, 1) ** 1.4)[..., None]
    img = np.where(frente[..., None], img, img * 0.5)
    amar = np.array([154, 112, 52], np.float32)
    k = np.clip((0.33 - v) * 2.4, 0, 1) * 0.6 + np.clip(d - 0.72, 0, 1) * 1.1
    img = img * (1 - k[..., None] * 0.55) + amar * (k[..., None] * 0.55)
    # sulcos (suturas entre placas) e rachaduras: desenhados num mapa de profundidade
    sulco = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sulco)

    def uv(uu, vv):
        return (uu * W, (1 - vv) * H)

    def linha(pts, larg):
        sd.line([uv(*p) for p in pts], fill=255, width=larg)
    for sg in (0, 1):
        f = (lambda a: a) if sg == 0 else (lambda a: 0.5 - a)
        linha([(f(0.25), 0.80), (f(0.16), 0.72), (f(0.06), 0.66)], 3)       # V da testa
        linha([(f(0.25), 0.58), (f(0.17), 0.60), (f(0.08), 0.57)], 2)       # linha da sobrancelha
        linha([(f(0.11), 0.60), (f(0.12), 0.44), (f(0.09), 0.34)], 2)       # placa da macã
        linha([(f(0.205), 0.52), (f(0.20), 0.30), (f(0.215), 0.12)], 2)     # perto da crista no bico
    # orbitas fundas: manchas escuras
    org = Image.new("L", (W, H), 0)
    od = ImageDraw.Draw(org)
    for cx in (0.115, 0.385):
        od.ellipse([(cx - 0.07) * W, (1 - 0.64) * H, (cx + 0.07) * W, (1 - 0.50) * H], fill=255)
    # rachaduras profundas (caminhada aleatoria), mais no lado direito
    for ini in [(0.18, 0.95), (0.33, 0.93), (0.27, 0.78), (0.40, 0.70), (0.12, 0.84), (0.22, 0.45)]:
        x, y = ini[0] * W, (1 - ini[1]) * H
        for _ in range(int(rng.integers(12, 30))):
            nx = x + rng.normal(0, 3.2); ny = y + rng.uniform(3, 9)
            sd.line([(x, y), (nx, ny)], fill=255, width=int(rng.integers(1, 4)))
            x, y = nx, ny
            if rng.random() < 0.10:
                sd.line([(x, y), (x + rng.normal(0, 14), y + rng.uniform(4, 12))], fill=255, width=1)
    s_arr = np.asarray(sulco, np.float32) / 255.0
    o_arr = np.asarray(org, np.float32) / 255.0
    s_mol = desfocar(s_arr, 1.4)
    img = img * (1 - 0.62 * s_mol[..., None]) + np.array([70, 48, 28], np.float32) * (0.62 * s_mol[..., None])
    # sujeira acumulada em volta dos sulcos
    suj = desfocar(s_arr, 5) * 0.55
    img *= (1 - suj[..., None] * 0.45)
    # orbitas
    o_mol = desfocar(o_arr, 5)
    img = img * (1 - 0.7 * o_mol[..., None]) + np.array([48, 34, 24], np.float32) * (0.7 * o_mol[..., None])
    # lascas escuras na borda esquerda e pontinhos de poro
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, "RGBA")
    for _ in range(40):
        yv = rng.uniform(0, H * 0.7)
        dr.rectangle([0, yv, rng.uniform(3, 9), yv + rng.uniform(3, 9)], fill=(110, 80, 46, 150))
    for _ in range(90):
        x0, y0 = rng.uniform(0, W * 0.5), rng.uniform(0, H)
        dr.ellipse([x0, y0, x0 + 2, y0 + 2], fill=(120, 94, 58, 120))
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    salvar(np.asarray(im, np.float32), "T_Mascara_BC.png")
    # normal: placas levemente abauladas, sulcos e orbitas fundos
    alt = 0.5 + (n2 - 0.5) * 0.25 + (n3 - 0.5) * 0.12
    alt -= desfocar(s_arr, 1.2) * 0.9
    alt -= o_mol * 0.5
    salvar(normal_de_altura(alt, 3.2), "T_Mascara_N.png")


# ---------------- detalhes 512 (lenco | cabelo | pele) ----------------
def detalhe():
    W = H = 512
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.zeros((H, W, 3), np.float32)
    n2, n3 = ruido(W, H, 24, 21), ruido(W, H, 5, 22)
    Q = 256
    # TL: lenco verde-escuro; 3 rolos horizontais (v' do quadrante) e fio do tecido
    vq = 1 - yy[:Q, :Q] / Q       # 1 topo do lenco
    verde = np.array([58, 78, 48], np.float32)
    rolo = np.abs(np.sin(vq * 3 * np.pi))     # 1 no meio do rolo, 0 no vinco
    fiapo = np.sin(xx[:Q, :Q] * 0.45 + n2[:Q, :Q] * 5) * 0.5 + 0.5
    lenco = verde * (0.50 + 0.62 * rolo[..., None] ** 0.8) * (0.9 + 0.12 * fiapo[..., None]) + ((n3[:Q, :Q] - 0.5) * 12)[..., None]
    img[:Q, :Q] = lenco
    # TR: cabelo castanho, listras suaves e brilho
    fio = 0.55 + 0.25 * np.sin(xx[:Q, Q:] * 0.22 + n2[:Q, Q:] * 3) + 0.2 * ruido(Q, Q, 20, 23)
    cab = np.array([104, 70, 42], np.float32) * fio[..., None]
    gv = 1 - yy[:Q, Q:] / Q
    cab *= (0.7 + 0.5 * gv)[..., None]
    img[:Q, Q:] = cab
    # BL: pele quente com sombra suave
    pele = np.array([168, 112, 78], np.float32) * (0.85 + 0.25 * n2[Q:, :Q][..., None]) + ((n3[Q:, :Q] - 0.5) * 8)[..., None]
    img[Q:, :Q] = pele
    # BR: pele mais escura (palpebras)
    img[Q:, Q:] = np.array([104, 66, 46], np.float32) * (0.9 + 0.2 * n2[Q:, Q:][..., None])
    salvar(img, "T_CapuzDetalhe_BC.png")


# ---------------- moldura dourada 128x512 (u atravessa a faixa, v ao longo) ----------------
def ouro():
    W, H = 128, 512
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W, yy / H
    n1, n2, n3 = ruido(W, H, 40, 31), ruido(W, H, 9, 32), ruido(W, H, 3, 33)
    base = np.array([206, 174, 104], np.float32)
    esc = np.array([104, 76, 32], np.float32)
    img = base + (esc - base) * (n1 * 0.6 + n2 * 0.4)[..., None] * 0.9 + ((n3 - 0.5) * 14)[..., None]
    # bisel: bordas laterais claras/escuras
    bis = np.clip(1 - np.abs(u - 0.5) * 2, 0, 1)
    img *= (0.72 + 0.4 * bis ** 0.6)[..., None]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, "RGBA")
    # ranhuras transversais e rachaduras
    for y in np.arange(14, H, 34):
        yy0 = y + rng.uniform(-6, 6)
        dr.line([(W * 0.1, yy0), (W * 0.9, yy0 + rng.uniform(-3, 3))], fill=(62, 42, 18, 200), width=2)
    for _ in range(14):
        x, y = rng.uniform(10, W - 10), rng.uniform(0, H)
        for _ in range(8):
            nx, ny = x + rng.normal(0, 3), y + rng.uniform(2, 7)
            dr.line([(x, y), (nx, ny)], fill=(56, 38, 18, 190), width=1)
            x, y = nx, ny
    # desgaste: lascas claras assimetricas
    for _ in range(40):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        dr.rectangle([x0, y0, x0 + rng.uniform(2, 7), y0 + rng.uniform(2, 6)], fill=(214, 186, 112, 150))
    salvar(np.asarray(im.filter(ImageFilter.GaussianBlur(0.4)), np.float32), "T_Ouro_BC.png")


# ---------------- olho 128x64 (amendoa: esclera, iris verde, pupila, palpebra) ----------------
def olho():
    W, H = 128, 64
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H / 2
    img = np.zeros((H, W, 3), np.float32)
    img[:] = [196, 186, 150]            # esclera quente
    # sombra da palpebra no topo
    top = np.clip(1 - (yy / H) / 0.42, 0, 1)
    img *= (1 - 0.55 * top[..., None])
    r = np.sqrt(((xx - cx) / 1.0) ** 2 + ((yy - cy * 1.04) / 1.0) ** 2)
    iris = r < 24
    g = np.clip(1 - r / 24, 0, 1)
    ir = np.stack([40 + 40 * (1 - g), 160 + 70 * (1 - g) * 0.4 + 40 * g, 50 + 30 * g], -1)
    img = np.where(iris[..., None], ir, img)
    img = np.where(((r > 19) & (r < 24))[..., None], img * 0.55, img)   # anel do limbo
    pup = r < 9
    img = np.where(pup[..., None], np.array([6, 14, 8], np.float32), img)
    # brilho
    br = ((xx - (cx - 8)) ** 2 + (yy - (cy - 8)) ** 2) < 12
    img = np.where(br[..., None], np.array([240, 255, 230], np.float32), img)
    salvar(img, "T_Olho_BC.png")


if __name__ == "__main__":
    capuz(); mascara(); detalhe(); ouro(); olho()
