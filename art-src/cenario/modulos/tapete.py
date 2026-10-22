"""Tapete da Cripta paramétrico (largura x comprimento, deitado no piso). Moldura em tiles (borda + canto), campo em tile, medalhões bordados repetidos (decals), furos/rasgos por geometria fina.
bpy: TAPETE_W=3.6 TAPETE_L=6 python tapete.py -- <saida.glb> [pasta_previas]    PARTES=padrao,...  VISTAS=...  AMOSTRAS=16
Pivô no centro do tapete, +Z para cima, comprimento no eixo Y, metros."""
import sys, os, math, json, struct, random
import numpy as np
from PIL import Image, ImageDraw

PX = 0.0025                            # m por texel
FR, FRP, PER = 214 * PX, 214, 52 * PX    # moldura (m e px) e período do padrão de losangos
PALE = np.array((0.60, 0.20, 0.20), np.float32)
TEX = os.environ.get("TAPETE_TEX", "/tmp/tapete_tex")
os.makedirs(TEX, exist_ok=True)

# ------------------------------------------------------------------ utilitários de textura
def noise(h, w, cells, seed):
    r = np.random.default_rng(seed)
    f = np.fft.fft2(r.standard_normal((h, w)))
    ky, kx = np.meshgrid(np.fft.fftfreq(h) * h, np.fft.fftfreq(w) * w, indexing="ij")
    f *= np.exp(-((kx ** 2 + ky ** 2) / (2 * cells ** 2)))
    n = np.real(np.fft.ifft2(f)); return n / np.abs(n).max()

def gauss(a, s):
    h, w = a.shape
    ky, kx = np.meshgrid(np.fft.fftfreq(h), np.fft.fftfreq(w), indexing="ij")
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (np.pi * s) ** 2 * (kx ** 2 + ky ** 2))))

def smooth(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def motif(w, h, seed, rings=True):
    """Ornamento floral bilateral (máscara 0..1) w x h: haste central, folhas de acanto, volutas, losango e anel. Desenha um quadrante e espelha."""
    S = 3; r = random.Random(seed)
    qw, qh = w * S // 2, h * S // 2
    im = Image.new("L", (qw, qh), 0); d = ImageDraw.Draw(im)
    ox, oy = 0, qh                    # origem no canto inferior esquerdo do quadrante: x p/ direita, y p/ cima
    def P(x, y): return (ox + x, oy - y)
    def disk(x, y, rad): d.ellipse([P(x - rad, y + rad), P(x + rad, y - rad)], fill=255)
    def leaf(x, y, ang, ln, wd):
        pts = []
        for i in range(0, 21):
            t = i / 20; a = ln * t; b = wd * math.sin(math.pi * t ** 0.8) * (1 - 0.3 * t)
            pts.append((a, b))
        pts = pts + [(a, -b) for a, b in reversed(pts)]
        ca, sa = math.cos(ang), math.sin(ang)
        d.polygon([P(x + a * ca - b * sa, y + a * sa + b * ca) for a, b in pts], fill=255)
    def scroll(cx, cy, R, turns, width, sign, phi0=math.pi):
        n = int(turns * 90)
        for i in range(n + 1):
            t = i / n; rad = R * (1 - t * 0.88); phi = phi0 + sign * turns * 2 * math.pi * t
            disk(cx + rad * math.cos(phi), cy + rad * math.sin(phi), max(1.4 * S * 0.5, width * (1 - t * 0.65)))
    L = h * S / 2; Wq = w * S / 2
    # haste central
    for i in range(int(L * 0.96)):
        disk(0, i, 2.2 * S * (1 - 0.4 * i / L) + 1.2)
    d.polygon([P(0, 0), P(0.11 * Wq, 0), P(0, 0.20 * L)], fill=255)           # losango central
    d.polygon([P(0, 0.2 * L), P(0.06 * Wq, 0.26 * L), P(0, 0.34 * L)], fill=255)
    # folhas alternadas ao longo da haste, menores para a ponta
    for i in range(1, 6):
        t = i / 6.4; y = 0.2 * L + t * L * 0.72
        ln = (1 - 0.5 * t) * Wq * 0.50; wd = ln * 0.17
        leaf(0, y, math.radians(52 + 4 * (i % 2)), ln, wd)
        leaf(0, y + 0.02 * L, math.radians(14), ln * 0.6, wd * 0.6)
    # volutas laterais em S
    for (yy, R, sg, tn) in ((0.30, 0.20, 1, 1.25), (0.52, 0.17, -1, 1.2), (0.72, 0.13, 1, 1.1)):
        scroll(R * Wq + 3 * S, L * yy, R * Wq, tn, 2.6 * S, sg)
    # folhas no eixo horizontal
    for i in range(1, 4):
        x = i * Wq * 0.17; ln = Wq * 0.20 * (1 - 0.18 * i)
        leaf(x, 4 * S, math.radians(85), ln, ln * 0.20)
    disk(0, L * 0.96, 4.5 * S); leaf(0, L * 0.88, math.radians(90), L * 0.1, 5 * S)
    if rings:                         # anel em elipse com pérolas
        for i in range(260):
            a = i / 260 * math.pi / 2
            disk(w * S / 2 * 0.97 * math.cos(a), L * 0.97 * math.sin(a), 2.0 * S)
        for i in range(24):
            a = (i + 0.5) / 24 * math.pi / 2
            disk(w * S / 2 * 0.90 * math.cos(a), L * 0.90 * math.sin(a), 2.6 * S)
    q = np.asarray(im, np.float32) / 255
    top = np.concatenate([q[:, ::-1], q], 1)   # espelha p/ esquerda
    full = np.concatenate([top, top[::-1]], 0)                # espelha p/ baixo
    return np.asarray(Image.fromarray((full * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS), np.float32) / 255

def rosette(w, h, seed, petals=7, scrolls=True):
    """Medalhão em losango com rosácea central, pétalas em anéis, arabescos e pérolas (bilateral, 4 quadrantes)."""
    S = 3; r = random.Random(seed); qw, qh = w * S // 2, h * S // 2
    im = Image.new("L", (qw, qh), 0); d = ImageDraw.Draw(im)
    def P(x, y): return (x, qh - y)
    def disk(x, y, rad): d.ellipse([P(x - rad, y + rad), P(x + rad, y - rad)], fill=255)
    def leaf(x, y, ang, ln, wd, tip=0.8):
        pts = [(ln * i / 20, wd * math.sin(math.pi * (i / 20) ** tip) * (1 - 0.25 * i / 20)) for i in range(21)]
        pts = pts + [(a, -b) for a, b in reversed(pts)]
        ca, sa = math.cos(ang), math.sin(ang)
        d.polygon([P(x + a * ca - b * sa, y + a * sa + b * ca) for a, b in pts], fill=255)
    def line(p0, p1, wd):
        n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))) + 1
        for i in range(n + 1):
            t = i / n; disk(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, wd)
    def spiral(cx, cy, R, turns, wd, sign, phi0):
        n = int(turns * 90)
        for i in range(n + 1):
            t = i / n; rad = R * (1 - t * 0.88); phi = phi0 + sign * turns * 2 * math.pi * t
            disk(cx + rad * math.cos(phi), cy + rad * math.sin(phi), max(1.2 * S, wd * (1 - t * 0.6)))
    A, B = qw, qh                        # semi-eixos do losango
    for k, wd in ((1.0, 3.4), (0.93, 1.6), (0.60, 1.8)):       # losangos concêntricos
        line((A * k, 0), (0, B * k), wd * S)
    R = min(A, B) * 0.40
    for i in range(9):                                   # anel externo de pétalos longos, alternados
        ang = (math.pi / 2) * (i + 0.5) / 8 if 0 < i < 8 else (math.pi / 2) * (i / 8)
        leaf(R * 0.46 * math.cos(ang), R * 0.46 * math.sin(ang), ang, R * 0.52, R * 0.52 * 0.24)
    for i in range(0, 9):                                # anel interno
        ang = (math.pi / 2) * i / 8
        leaf(R * 0.14 * math.cos(ang), R * 0.14 * math.sin(ang), ang, R * 0.34, R * 0.34 * 0.34, tip=0.65)
    d.ellipse([P(-R * 0.12, R * 0.12), P(R * 0.12, -R * 0.12)], fill=0)      # miolo vazado
    disk(0, 0, R * 0.07); d.ellipse([P(-R * 0.11, R * 0.11), P(R * 0.11, -R * 0.11)], outline=255, width=2 * S)
    for i in range(24):                                  # pérolas em anel
        a_ = (math.pi / 2) * (i + 0.5) / 24; disk(R * 1.02 * math.cos(a_), R * 1.02 * math.sin(a_), 2.2 * S)
    # hastes nos eixos com folhas
    for i in range(int(R * 0.9), int(B * 0.92)):
        disk(0, i, 2.4 * S * (1 - 0.35 * i / B) + 1)
    for i in range(int(R * 0.9), int(A * 0.92)):
        disk(i, 0, 2.4 * S * (1 - 0.35 * i / A) + 1)
    for t in (0.50, 0.62, 0.74, 0.85):
        y = t * B; ln = (1.15 - 0.45 * t) * A * 0.15
        leaf(0, y, math.radians(46), ln, ln * 0.26); leaf(0, y, math.radians(134), ln, ln * 0.26)
    for t in (0.55, 0.72, 0.87):
        x = t * A; ln = (1.15 - 0.45 * t) * A * 0.13
        leaf(x, 0, math.radians(44), ln, ln * 0.26)
    leaf(0, B * 0.82, math.pi / 2, B * 0.1, 9 * S); leaf(A * 0.82, 0, 0, A * 0.1, 8 * S)
    ca, sa = A / math.hypot(A, B), B / math.hypot(A, B)       # folhas na diagonal do losango
    for t in (0.35, 0.5, 0.65):
        x, y = A * 0.62 * (1 - t) + 0, B * 0.62 * t
        leaf(x, y, math.atan2(B, A) * 0 + math.pi / 4, A * 0.07, A * 0.02)
    if scrolls:                          # arabescos nas diagonais dentro do losango
        for i, (fx, fy, sg) in enumerate(((0.66, 0.15, 1), (0.14, 0.62, -1), (0.40, 0.32, -1))):
            cx, cy = A * fx, B * fy
            spiral(cx, cy, R * (0.34 - 0.04 * i), 1.3, 3.6 * S, sg, math.atan2(cy, cx) + math.pi)
            spiral(cx, cy, R * (0.26 - 0.04 * i), 1.1, 3.0 * S, -sg, math.atan2(cy, cx))
    for i in range(10):                  # pérolas ao longo do losango interno
        t = (i + 0.5) / 10; disk(A * 0.80 * (1 - t), B * 0.80 * t, 1.8 * S)
    q = np.asarray(im, np.float32) / 255
    top = np.concatenate([q[:, ::-1], q], 1); full = np.concatenate([top, top[::-1]], 0)
    return np.asarray(Image.fromarray((full * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS), np.float32) / 255

# ------------------------------------------------------------------ texturas em tiles
def hexgold(): return np.array((0.78, 0.60, 0.26), np.float32)

def grad(h, periodic=True):
    if periodic:
        gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5; gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    else:
        gx = np.gradient(h, axis=1); gy = np.gradient(h, axis=0)
    return gx, gy

def to_normal(ht, k=7.0, periodic=True):
    gx, gy = grad(ht, periodic)                       # eixo 0 = v para cima
    N = np.dstack([-gx * k, -gy * k, np.ones_like(ht)]); N /= np.linalg.norm(N, axis=2, keepdims=True)
    return N * 0.5 + 0.5

def save_img(arr, name, quality=None):
    """arr em espaço v-para-cima (linha 0 = v 0): vira PNG/JPG com a linha 0 embaixo."""
    a = np.clip(arr, 0, 1)
    im = Image.fromarray((a * 255).astype(np.uint8)).transpose(Image.FLIP_TOP_BOTTOM)
    p = f"{TEX}/{name}"
    im.save(p, quality=quality) if quality else im.save(p); return p

def fabric(h, w, seed):
    """Tecido 'pálido' (o vermelho fundo vem da cor de vértice): albedo, altura de fibra/trama. Periódico."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    n_l, n_m, n_s = noise(h, w, 4, seed), noise(h, w, max(6, w // 14), seed + 1), noise(h, w, w // 2.2, seed + 2)
    A = np.broadcast_to(PALE, (h, w, 3)).copy()
    A *= (0.80 + 0.14 * n_l[..., None] + 0.14 * n_m[..., None] + 0.08 * n_s[..., None])
    weave = gauss((np.sin(xx * math.pi * 2 / 4.0) * np.sin(yy * math.pi * 2 / 4.0)) * 0.5 + 0.5, 0.6)
    A *= (0.93 + 0.12 * weave[..., None])
    fib = n_m * 0.15 + gauss(np.random.default_rng(seed).standard_normal((h, w)).astype(np.float32), 0.8) * 1.3
    ht = weave * 0.14 + n_s * 0.30 + 0.20 * n_m + 0.55 * fib
    return A, ht, (n_s, n_m)

def frame_layers(dedge, s, h, w, seed):
    """Moldura (faixas douradas, losangos): devolve ouro, sombra, faixa vermelha escura, losango interno, para qualquer dedge/s."""
    def band(a, b): return smooth(a - 1, a + 1, dedge) * (1 - smooth(b - 1, b + 1, dedge))
    gold = np.maximum.reduce([band(30, 54), band(96, 104), band(170, 178), band(196, 212)])
    pat = 52.0; ub = ((s % pat) / pat) - 0.5; tb = (dedge - 104) / 66.0 - 0.5
    inb = (dedge > 104) & (dedge < 170)
    dia = (np.abs(ub) + np.abs(tb) < 0.38) & inb; dia2 = (np.abs(ub) + np.abs(tb) < 0.15) & inb
    gold = np.maximum(gold, dia.astype(np.float32) * 0.9)
    return gold, band(54, 96), band(0, 30), dia, dia2

def paint_frame(h, w, seed, kind):
    """kind 'borda' (tira h=416 ao longo, w=214 de fora p/ dentro) ou 'canto' (214x214, canto externo em 0,0)."""
    A, ht, (n_s, n_m) = fabric(h, w, seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if kind == "borda": dedge = xx; s = yy + FRP
    else: dedge = np.minimum(xx, yy); s = np.where(xx <= yy, yy, xx)
    gold, red, sel, dia, dia2 = frame_layers(dedge, s, h, w, seed)
    A *= (1 - 0.25 * red[..., None]); A *= (1 - 0.35 * sel[..., None])
    A *= (1 - 0.35 * (dia2 & ~dia)[..., None]); A[dia2] = (PALE * 0.8)
    stitch = 0.88 + 0.12 * np.sin(yy * math.pi / 3.0 + xx * 0.35) + 0.12 * n_s
    gcol = hexgold() * (0.72 + 0.30 * n_m[..., None]) * stitch[..., None]
    gm = gold * (n_s * 0.2 + 0.85 > 0.55)
    A *= (1 - 0.45 * np.clip(gauss(gold, 2.2) - gold, 0, 1)[..., None])
    A = A * (1 - gm[..., None]) + gcol * gm[..., None]
    ht = ht + 0.9 * gauss(gold, 0.8) + 0.3 * stitch * gold
    return A, ht

def paint_field(h, w, seed):
    A, ht, (n_s, n_m) = fabric(h, w, seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / 128.0; v = yy / 128.0
    lat = (np.abs(((u + v) % 1) - 0.5) < 0.012) | (np.abs(((u - v) % 1) - 0.5) < 0.012)
    A *= (1 + 0.12 * lat[..., None]); ht = ht - 0.5 * lat
    return A, ht

def paint_motifs():
    """Atlas RGBA (v-para-cima) com rosácea grande, medalhão pequeno e roseta de canto; devolve (rgba, normal, rects{nome:(u0,v0,u1,v1)})."""
    AW, AH = 1080, 1860
    ms = {"rosa": (rosette(1060, 1340, 1), 0, 0), "peq": (motif(560, 440, 2, rings=True), 0, 1360), "canto": (rosette(150, 150, 7, petals=4, scrolls=False), 580, 1360)}
    mask = np.zeros((AH, AW), np.float32); rects = {}
    for k, (m, x0, y0) in ms.items():
        h, w = m.shape; mask[y0:y0 + h, x0:x0 + w] = m; rects[k] = (x0 / AW, y0 / AH, (x0 + w) / AW, (y0 + h) / AH)
    yy, xx = np.mgrid[0:AH, 0:AW].astype(np.float32)
    n_m = noise(AH, AW, 70, 51); n_s = noise(AH, AW, AW / 2.2, 52)
    stitch = 0.88 + 0.12 * np.sin(yy * math.pi / 3.0 + xx * 0.35) + 0.12 * n_s
    gcol = hexgold() * (0.72 + 0.30 * n_m[..., None]) * stitch[..., None]
    sh = np.clip(gauss(mask, 2.4) * 1.6 - mask, 0, 1)
    rgb = gcol * mask[..., None] + np.array((0.06, 0.02, 0.02)) * (1 - mask[..., None])
    alpha = np.clip(mask * 1.2 + sh * 0.9, 0, 1)
    rgba = np.dstack([rgb, alpha])
    ht = 0.9 * gauss(mask, 0.8) + 0.3 * stitch * mask + 0.25 * n_s
    return rgba, to_normal(ht, 7.0, False), rects

def gen_texturas():
    os.makedirs(TEX, exist_ok=True)
    A, ht = paint_field(512, 512, 100); save_img(A, "campo.jpg", 90); save_img(to_normal(ht), "campo_n.jpg", 92)
    A, ht = paint_frame(416, 214, 200, "borda"); save_img(A, "borda.jpg", 90); save_img(to_normal(ht), "borda_n.jpg", 92)
    A, ht = paint_frame(214, 214, 300, "canto"); save_img(A, "canto.jpg", 90); save_img(to_normal(ht, 7.0, False), "canto_n.jpg", 92)
    rgba, nrm, rects = paint_motifs(); save_img(rgba, "motivos.png"); save_img(nrm, "motivos_n.jpg", 92)
    json.dump(rects, open(f"{TEX}/rects.json", "w")); print("texturas ok")

# ------------------------------------------------------------------ forma do tapete (parametrizada)
def quantize(LWr, LLr):
    qs = lambda L: max(2, round((L - 2 * FR) / PER)) * PER + 2 * FR
    return qs(LWr), qs(LLr)

def layout(LW, LL):
    """Posições dos motivos (centro x, centro y, largura, altura, tipo) no campo."""
    FW, FL = LW - 2 * FR, LL - 2 * FR
    w = min(2.2, FW * 0.80); rh = w * 1340 / 1060; sw = w * 0.5; sh = sw * 440 / 560
    ncol = max(1, int(FW // (w + 0.5))); nrow = max(1, int(FL // (rh + sh + 0.35)))
    out = []
    for c in range(ncol):
        cx = -FW / 2 + (c + 0.5) * FW / ncol
        for r in range(nrow):
            cy = -FL / 2 + (r + 0.5) * FL / nrow
            out.append((cx, cy, w, rh, "rosa"))
        for r in range(nrow + 1):
            cy = -FL / 2 + r * FL / nrow; cy = min(max(cy, -FL / 2 + sh / 2 + 0.22), FL / 2 - sh / 2 - 0.22)
            out.append((cx, cy, sw, sh, "peq"))
    for sx in (-1, 1):
        for sy in (-1, 1): out.append((sx * (FW / 2 - 0.28), sy * (FL / 2 - 0.28), 0.34, 0.34, "canto"))
    return out

def make_mask(LW, LL, boxes, seed=11, CM=0.01):
    """Silhueta rasgada + furos num mapa de 1 cm (linha = y de baixo p/ cima). Retorna alive (bool) e rim (0..1, escurecimento perto do rasgo)."""
    rr = np.random.default_rng(seed)
    nx, ny = int(round(LW / CM)), int(round(LL / CM))
    yy, xx = np.mgrid[0:ny, 0:nx].astype(np.float32); X = (xx + 0.5) * CM - LW / 2; Y = (yy + 0.5) * CM - LL / 2
    dedge = np.minimum(LW / 2 - np.abs(X), LL / 2 - np.abs(Y))
    ar = (LW * LL / 21.6) ** 0.7; per = 2 * (LW + LL) / 19.2
    nz = lambda feat, sd: noise(ny, nx, max(2.0, nx * CM / feat), sd)
    n_m, n_s, n_h = nz(0.06, 2), nz(0.03, 3), nz(0.30, 21) * 0.6 + nz(0.10, 22) * 0.4
    bite = np.zeros_like(dedge)
    for _ in range(int(26 * per)):
        side = rr.integers(0, 4); depth = rr.uniform(0.03, 0.22); width = rr.uniform(0.05, 0.35); t = rr.uniform(0.04, 0.96)
        cx, cy = ((t - .5) * LW, -LL / 2) if side == 0 else ((t - .5) * LW, LL / 2) if side == 1 else (-LW / 2, (t - .5) * LL) if side == 2 else (LW / 2, (t - .5) * LL)
        bite = np.maximum(bite, depth * np.exp(-(((X - cx) ** 2 + (Y - cy) ** 2) / (2 * width ** 2))))
    inset = 0.01 + 0.02 * np.abs(n_m) + 0.015 * np.abs(n_s) + bite
    def free(cx, cy, pad=0.0):
        return not any(abs(cx - bx) < bw / 2 + pad and abs(cy - by) < bh / 2 + pad for bx, by, bw, bh in boxes)
    def pick():
        for _ in range(60):
            cx, cy = rr.uniform(-LW / 2 * 0.92, LW / 2 * 0.92), rr.uniform(-LL / 2 * 0.95, LL / 2 * 0.95)
            if rr.random() < 0.5: cx = rr.choice((-1, 1)) * (LW / 2 - rr.uniform(0.15, 0.6))
            if free(cx, cy, 0.1): return cx, cy
        return None
    hole = np.zeros(dedge.shape, bool)
    for _ in range(int(14 * ar)):
        p = pick()
        if p is None: continue
        rad = rr.uniform(0.16, 0.45)
        hole |= (np.exp(-(((X - p[0]) ** 2 + ((Y - p[1]) * 1.3) ** 2) / (2 * rad ** 2))) + 0.55 * n_h + 0.12 * n_s) > 0.97
    for _ in range(int(5 * ar)):
        p = pick()
        if p is None: continue
        rad = rr.uniform(0.17, 0.30)
        hole |= (np.exp(-(((X - p[0]) ** 2 + ((Y - p[1]) * rr.uniform(0.7, 1.6)) ** 2) / (2 * rad ** 2))) + 0.6 * n_h + 0.12 * n_s) > 0.75
    for _ in range(int(18 * ar)):
        p = pick()
        if p is None: continue
        rad = rr.uniform(0.02, 0.06)
        hole |= ((X - p[0]) ** 2 + ((Y - p[1]) * rr.uniform(0.5, 2.2)) ** 2) < rad ** 2 * (0.5 + 1.0 * np.abs(n_s))
    for _ in range(int(5 * ar)):
        p = pick()
        if p is None: continue
        L = rr.uniform(0.2, 0.4)
        hole |= (np.abs(X - p[0]) < 0.016 * (1 - np.abs(Y - p[1]) / L)) & (np.abs(Y - p[1]) < L)
    alive = (dedge > inset) & ~hole
    g = gauss(alive.astype(np.float32), 2.0)
    rim = np.clip((0.7 - g) / 0.55, 0, 1) * alive
    return alive, rim, CM

# ------------------------------------------------------------------ Blender
def blender_part(LWr, LLr, seed):
    import bpy, bmesh
    LW, LL = quantize(LWr, LLr); objs = []
    rects = json.load(open(f"{TEX}/rects.json"))
    def mat(name, color, rough=1.0, image=None, normal=None, vcol=False):
        m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = 0
        try: b.inputs["Specular IOR Level"].default_value = 0.25
        except KeyError: pass
        if image:
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(image); t.image.pack(); src = t.outputs["Color"]
            if vcol:
                vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
                mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1.0
                nt.links.new(src, mx.inputs[6]); nt.links.new(vc.outputs["Color"], mx.inputs[7]); src = mx.outputs[2]
            nt.links.new(src, b.inputs["Base Color"])
            if image.endswith(".png"): nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
        if normal:
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(normal); t.image.pack(); t.image.colorspace_settings.name = "Non-Color"
            n = nt.nodes.new("ShaderNodeNormalMap"); n.inputs["Strength"].default_value = 0.9
            nt.links.new(t.outputs["Color"], n.inputs["Color"]); nt.links.new(n.outputs["Normal"], b.inputs["Normal"])
        return m
    mats = {"campo": mat("M_TapeteCampo", (0.4, 0.05, 0.06), 1, f"{TEX}/campo.jpg", f"{TEX}/campo_n.jpg", True),
            "borda": mat("M_TapeteBorda", (0.4, 0.05, 0.06), 1, f"{TEX}/borda.jpg", f"{TEX}/borda_n.jpg", True),
            "canto": mat("M_TapeteCanto", (0.4, 0.05, 0.06), 1, f"{TEX}/canto.jpg", f"{TEX}/canto_n.jpg", True),
            "motivo": mat("M_TapeteMotivo", (0.7, 0.5, 0.2), 1, f"{TEX}/motivos.png", f"{TEX}/motivos_n.jpg", False),
            "franja": mat("M_TapeteFranja", (0.50, 0.33, 0.15), 1.0)}
    def new(name, bm):
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); objs.append(o); return o

    rg = random.Random(seed)
    area = LW * LL; nf = max(2, int(area / 8))
    folds = [(rg.uniform(-LL * 0.45, LL * 0.45), rg.uniform(-0.45, 0.45), rg.uniform(0.05, 0.12), rg.uniform(-LW * 0.2, LW * 0.2)) for _ in range(nf)]
    ph = [rg.uniform(0, 6.3) for _ in range(4)]
    def height(x, y):
        z = 0.002 * (1 + 0.5 * math.sin(x * 9 + y * 4 + ph[0]))
        z += 0.016 * math.sin(y * 3.1 + 0.8 * math.sin(x * 2.3) + ph[1]) * math.exp(-((x - 0.5) ** 2) / 0.8 * 0.2 / max(0.2, LW / 3.6))
        z += 0.010 * math.sin(x * 13 + y * 5.5 + ph[2]) * math.sin(y * 2.9 + 1)
        z += 0.02 * math.sin(x * 0.9 + y * 0.55 + ph[3])
        for yc, ang, h0, xc in folds:
            dd = (y - yc) - math.tan(ang) * (x - xc)
            z += h0 * math.exp(-(dd / 0.17) ** 2) * (0.6 + 0.4 * math.sin(x * 4)) * math.exp(-((x - xc) / (LW * 0.45)) ** 2)
        d = min(LW / 2 - abs(x), LL / 2 - abs(y))
        z += (0.035 * (0.5 + 0.5 * math.sin(x * 5.3 + y * 3.7) * math.sin(x * 1.7 - y * 2.3)) + 0.01) * math.exp(-max(d, 0) / 0.05)
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            cd = math.hypot(x - sx * LW / 2, y - sy * LL / 2)
            z += 0.11 * math.exp(-(cd / 0.22) ** 2) * (1 if sx * sy > 0 else 0.3)
        return max(z + 0.014, 0.004)

    boxes = [(cx, cy, bw, bh) for cx, cy, bw, bh, t in layout(LW, LL)]
    alive, rim, CM = make_mask(LW, LL, boxes, seed)
    ny, nx = alive.shape
    def samp(arr, x, y):
        i = min(max(int((x + LW / 2) / CM), 0), nx - 1); j = min(max(int((y + LL / 2) / CM), 0), ny - 1); return arr[j, i]
    # tinta de vértice: vermelho fundo nas bordas, desbotado/pálido no centro e em manchas; rim escuro nos rasgos
    DEEP = np.array((0.52, 0.07, 0.085)); ratio = np.clip(DEEP / PALE, 0, 1)
    nT = noise(ny, nx, max(3.0, nx * CM / 0.9), 61); nP = noise(ny, nx, max(3.0, nx * CM / 0.35), 62); nD = noise(ny, nx, max(3.0, nx * CM / 0.12), 63)
    def tint(x, y):
        cen = math.exp(-((x / (LW * 0.42)) ** 2 + (y / (LL * 0.32)) ** 2))
        fade = min(1, max(0, cen * (0.55 + 0.4 * samp(nT, x, y)) + 0.8 * max(0, samp(nP, x, y) - 0.45) * 0.8))
        c = ratio * (1 - fade) + fade
        dirt = 1 - 0.35 * max(0, samp(nT, x, y) * 0.7 + samp(nD, x, y) * 0.5) - 0.08 * abs(samp(nD, x, y))
        rm = 1 - 0.65 * samp(rim, x, y)
        return tuple(float(max(0, min(1, v * dirt * rm))) for v in c)

    def breaks(a, b, step): n = max(1, round((b - a) / step)); return [a + (b - a) * i / n for i in range(n + 1)]
    xs = breaks(-LW / 2, -LW / 2 + FR, FR / 5)[:-1] + breaks(-LW / 2 + FR, LW / 2 - FR, 0.15)[:-1] + breaks(LW / 2 - FR, LW / 2, FR / 5)
    ys = breaks(-LL / 2, -LL / 2 + FR, FR / 5)[:-1] + breaks(-LL / 2 + FR, LL / 2 - FR, 0.15)[:-1] + breaks(LL / 2 - FR, LL / 2, FR / 5)
    xin = lambda x: -LW / 2 + FR - 1e-6 <= x <= LW / 2 - FR + 1e-6
    yin = lambda y: -LL / 2 + FR - 1e-6 <= y <= LL / 2 - FR + 1e-6
    def region(cx, cy):
        fx, fy = not xin(cx), not yin(cy)
        return "canto" if fx and fy else "borda" if fx or fy else "campo"
    def uv(reg, x, y):
        if reg == "campo": return ((x + LW / 2) / 1.28, (y + LL / 2) / 1.28)
        if reg == "canto":
            return (min(max((LW / 2 - abs(x)), 0), FR) / FR, min(max((LL / 2 - abs(y)), 0), FR) / FR)
        if not xin(x * 0.999999 if False else x) and xin(x) is False and abs(x) > LW / 2 - FR - 1e-6 and yin(y):            # tira lateral
            return ((LW / 2 - abs(x)) / FR, (y - (-LL / 2 + FR)) / 1.04)
        return ((LL / 2 - abs(y)) / FR, (x - (-LW / 2 + FR)) / 1.04)                                                      # tira de topo/base
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new(); col = bm.loops.layers.float_color.new("Col")
    matidx = {"campo": 0, "borda": 1, "canto": 2}
    verts = {}
    gs = gauss(alive.astype(np.float32), 2.2); ggy, ggx = np.gradient(gs, CM)
    def project(x, y):
        """Empurra vértices da beira do rasgo para a curva de nível 0,5 do mapa borrado: tira o serrilhado em degraus."""
        x0_, y0_ = x, y
        for _ in range(3):
            g = samp(gs, x, y)
            if g < 0.08 or g > 0.92: break
            dx, dy = samp(ggx, x, y), samp(ggy, x, y); m2 = dx * dx + dy * dy
            if m2 < 1e-6: break
            x -= dx / m2 * (g - 0.5); y -= dy / m2 * (g - 0.5)
        if math.hypot(x - x0_, y - y0_) > 0.025: return x0_, y0_        # passo longo = gradiente ruim: mantém
        return x, y
    def V(x, y):
        k = (round(x, 5), round(y, 5))
        if k not in verts:
            px_, py_ = project(x, y) if (abs(abs(x) - LW / 2) > 1e-6 and abs(abs(y) - LL / 2) > 1e-6 or True) else (x, y)
            verts[k] = bm.verts.new((px_, py_, height(px_, py_)))
        return verts[k]
    def quad(x0, y0, x1, y1, reg):
        vv = [V(x0, y0), V(x1, y0), V(x1, y1), V(x0, y1)]
        try: f = bm.faces.new(vv)
        except ValueError: return
        f.material_index = matidx[reg]
        for l, (x, y) in zip(f.loops, ((x0, y0), (x1, y0), (x1, y1), (x0, y1))):
            # UV de região avaliado dentro da célula (evita cair no limite entre regiões)
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            ex = x + (mx - x) * 1e-4; ey = y + (my - y) * 1e-4
            l[uvl].uv = uv(reg, ex, ey); l[col] = (*tint(x, y), 1)
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
            reg = region((x0 + x1) / 2, (y0 + y1) / 2)
            ia, ib = int((x0 + LW / 2) / CM), int(math.ceil((x1 + LW / 2) / CM)); ja, jb = int((y0 + LL / 2) / CM), int(math.ceil((y1 + LL / 2) / CM))
            al = alive[ja:jb, ia:ib]; rm = rim[ja:jb, ia:ib]
            if not al.any(): continue
            if al.all() and rm.max() < 0.02: quad(x0, y0, x1, y1, reg); continue
            n = 6
            for b in range(n):
                for a in range(n):
                    sx0, sx1 = x0 + (x1 - x0) * a / n, x0 + (x1 - x0) * (a + 1) / n; sy0, sy1 = y0 + (y1 - y0) * b / n, y0 + (y1 - y0) * (b + 1) / n
                    if samp(alive, (sx0 + sx1) / 2, (sy0 + sy1) / 2) or alive[int((sy0 + LL / 2) / CM):int(math.ceil((sy1 + LL / 2) / CM)), int((sx0 + LW / 2) / CM):int(math.ceil((sx1 + LW / 2) / CM))].mean() > 0.4:
                        quad(sx0, sy0, sx1, sy1, reg)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    pano = new("Tapete_Pano", bm)
    for k in ("campo", "borda", "canto"): pano.data.materials.append(mats[k])
    for p in pano.data.polygons: p.use_smooth = True
    # motivos bordados (quads sobre o pano)
    bm = bmesh.new(); uvm = bm.loops.layers.uv.new(); colm = bm.loops.layers.float_color.new("Col"); NS = 22
    for cx, cy, w, h, t in layout(LW, LL):
        u0, v0, u1, v1 = rects[t]; grid = []
        for j in range(NS + 1):
            row = []
            for i in range(NS + 1):
                x = cx + (i / NS - 0.5) * w; y = cy + (j / NS - 0.5) * h; row.append(bm.verts.new((x, y, height(x, y) + 0.0035)))
            grid.append(row)
        for j in range(NS):
            for i in range(NS):
                f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
                for l, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    l[uvm].uv = (u0 + (u1 - u0) * a / NS, v0 + (v1 - v0) * b / NS); l[colm] = (1, 1, 1, 1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mo = new("Tapete_Motivos", bm); mo.data.materials.append(mats["motivo"])
    for p in mo.data.polygons: p.use_smooth = True
    # franjas: tufos de fios finos
    r = random.Random(7); bm = bmesh.new()
    for sgn in (-1, 1):
        ntuf = int(70 * LW / 3.6)
        for k in range(ntuf):
            if r.random() < 0.16: continue
            xt = ((k + r.uniform(0.2, 0.8)) / ntuf - 0.5) * (LW * 0.975)
            tl = r.uniform(0.06, 0.18) * (0.35 if r.random() < 0.15 else 1); tang = r.uniform(-0.5, 0.5); tcurl = r.uniform(-0.05, 0.05)
            for th in range(r.randint(5, 9)):
                if r.random() < 0.12: continue
                x0 = xt + r.uniform(-0.012, 0.012); ln = tl * r.uniform(0.6, 1.1); ang = tang + r.uniform(-0.2, 0.2)
                p0 = r.uniform(0, 6.3); wd = 0.0016; y0 = sgn * (LL / 2 - 0.03); rows = []; tangle = r.random() < 0.2
                for s_ in range(8):
                    t = s_ / 7; yy = y0 + sgn * (ln + 0.03) * t * math.cos(ang * (0.5 + t))
                    xx = x0 + (ln + 0.03) * t * math.sin(ang) + (tcurl + (0.03 if tangle else 0.008)) * math.sin(t * (11 if tangle else 6) + p0) * t
                    zz = max(0.003, height(xx, max(min(abs(yy), LL / 2 - 0.001), 0) * sgn) * (1 - t) ** 1.5 + 0.003 + 0.003 * math.sin(t * 9 + p0) ** 2)
                    ww = wd * (1 - 0.3 * t); rows.append((bm.verts.new((xx - ww, yy, zz)), bm.verts.new((xx + ww, yy, zz + 0.0015))))
                for s_ in range(7):
                    q = (rows[s_][0], rows[s_][1], rows[s_ + 1][1], rows[s_ + 1][0]); bm.faces.new(q if sgn > 0 else q[::-1])
    fr = new("Tapete_Franjas", bm); fr.data.materials.append(mats["franja"])
    return bpy, objs, LW, LL

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    OUT = argv[0] if argv else "SM_Cripta_Tapete.glb"; PREV = argv[1] if len(argv) > 1 else None
    LWr, LLr = float(os.environ.get("TAPETE_W", "3.6")), float(os.environ.get("TAPETE_L", "6.0")); seed = int(os.environ.get("TAPETE_SEED", "11"))
    if "padrao" in os.environ.get("PARTES", "padrao,pano,franjas").split(","): gen_texturas()
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy, objs, LW, LL = blender_part(LWr, LLr, seed)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join(); o = bpy.context.object; o.name = "SM_Cripta_Tapete"
    print("faces", len(o.data.polygons), "dim", tuple(round(x, 2) for x in o.dimensions), "tapete", LW, LL)
    bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format="GLB", export_yup=True, export_image_format="AUTO", export_vertex_color="ACTIVE")
    with open(OUT, "rb") as f: data = f.read()
    jl = struct.unpack("<I", data[12:16])[0]; js = json.loads(data[20:20 + jl]); rest = data[20 + jl:]
    for m in js["materials"]:
        m["doubleSided"] = True
        if m["name"] == "M_TapeteMotivo": m["alphaMode"] = "MASK"; m["alphaCutoff"] = 0.4
    print("COLOR_0" in json.dumps(js), "vertex color no glb")
    jb = json.dumps(js, separators=(",", ":")).encode(); jb += b" " * ((4 - len(jb) % 4) % 4)
    with open(OUT, "wb") as f:
        f.write(data[:8] + struct.pack("<I", 12 + 8 + len(jb) + len(rest)) + struct.pack("<I", len(jb)) + b"JSON" + jb + rest)
    if PREV: render(bpy, o, PREV, LW, LL)

def render(bpy, o, PREV, LW, LL):
    from mathutils import Vector
    os.makedirs(PREV, exist_ok=True); sc = bpy.context.scene; K = max(LL, LW * 1.4) / 6.0
    bpy.ops.mesh.primitive_plane_add(size=max(14, LL * 2.4), location=(0, 0, -0.03)); fl = bpy.context.object
    fm = bpy.data.materials.new("piso"); fm.use_nodes = True; fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.11, 0.10, 0.095, 1); fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    fl.data.materials.append(fm)
    sc.render.engine = "CYCLES"; sc.cycles.samples = int(os.environ.get("AMOSTRAS", "24")); sc.cycles.device = "CPU"; sc.cycles.use_denoising = True
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.055, 0.08, 1); sc.world = w
    def sun(rot, e, c):
        s = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN")); s.data.energy = e; s.data.color = c; s.rotation_euler = rot; bpy.context.collection.objects.link(s)
    sun((math.radians(50), 0, math.radians(35)), 3.2, (1.0, 0.85, 0.7)); sun((math.radians(65), 0, math.radians(-140)), 1.0, (0.55, 0.65, 1.0))
    cx, cy = LW / 2 - 0.3, -LL / 2 + 0.25
    views = {"cima": ((0, 0, 11 * K), (0, 0, 0), 560, 1000), "tres_quartos": ((3.5 * K, -7.5 * K, 5.5 * K), (0, 0, 0), 900, 650), "jogo_3q": ((0, -10 * K, 8.5 * K), (0, 0, 0), 900, 650),
             "close_medalhao": ((0.9, -1.4, 1.6), (0, 0, 0), 800, 800), "close_borda": ((cx + 0.3, cy - 0.9, 0.7), (cx, cy, 0), 800, 800), "close_franja": ((0.2, -LL / 2 - 0.5, 0.45), (0, -LL / 2 + 0.4, 0), 800, 800),
             "rasante": ((-5.5 * K, -2.5 * K, 0.9), (0, 0, 0), 900, 500), "wire": ((0, -4.5 * K, 7.5 * K), (0, 0, 0), 900, 650)}
    only_v = os.environ.get("VISTAS")
    for nome, (loc, tgt, rx, ry) in views.items():
        if only_v and nome not in only_v.split(","): continue
        if nome == "wire":
            w_ = o.copy(); w_.data = o.data.copy(); bpy.context.collection.objects.link(w_)
            md = w_.modifiers.new("w", "WIREFRAME"); md.thickness = 0.004; md.use_replace = True
            wm = bpy.data.materials.new("wm"); wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear()
            em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.85, 0.9, 1, 1); em.inputs["Strength"].default_value = 2.0
            ou = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], ou.inputs[0])
            w_.data.materials.clear(); w_.data.materials.append(wm); o.hide_render = True; fl.hide_render = True
        cam = bpy.data.cameras.new("c"); co = bpy.data.objects.new("c", cam); bpy.context.collection.objects.link(co)
        if nome == "cima": cam.type = "ORTHO"; cam.ortho_scale = max(LL, LW * 1.7) * 1.08
        if nome.startswith("close"): cam.lens = 35
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.camera = co; sc.render.resolution_x = rx; sc.render.resolution_y = ry
        sc.render.filepath = os.path.join(PREV, f"{nome}.png"); bpy.ops.render.render(write_still=True)
        if nome == "wire": bpy.data.objects.remove(w_, do_unlink=True); o.hide_render = False; fl.hide_render = False

if __name__ == "__main__": main()
