"""PANO do estandarte da Cripta: tecido rasgado denso (64x150) com dobras, espessura, tiras e franjas,
textura pintada (veludo vermelho, faixas douradas, flor-de-lis bordada) + normal map, argolas e ilhós no braço.
Tudo procedural (numpy+PIL+bmesh). Medidas vêm de lib.py."""
import bpy, bmesh, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from mathutils import Vector

TW, TH = 1024, 2048
NX, NY = 84, 200
HOLES = []   # (u, s, ru, rs) em coordenadas de pano (u 0..1, s 0..1 de cima p/ baixo)


# ---------------------------------------------------------------- utilidades de imagem
def _ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def fbm(h, w, seed, base=4, octs=5, aniso=(1, 1)):
    """Ruído fractal 0..1 (soma de oitavas bicúbicas)."""
    r = np.random.RandomState(seed); out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octs):
        gh = max(2, int(base * aniso[0] * 2 ** o)); gw = max(2, int(base * aniso[1] * 2 ** o))
        g = r.rand(gh, gw).astype(np.float32)
        im = Image.fromarray(g, mode="F").resize((w, h), Image.BICUBIC)
        out += np.asarray(im) * amp; tot += amp; amp *= 0.5
    out /= tot
    return (out - out.min()) / (out.max() - out.min() + 1e-6)

def blur(a, r):
    im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0

def lerp3(a, b, t): return a[None, None, :] * (1 - t[..., None]) + b[None, None, :] * t[..., None]


# ---------------------------------------------------------------- bordado (máscara dourada)
def emblema_mascara(W, LEN, cx_s):
    """Flor-de-lis + filigranas desenhadas em metros e rasterizadas na textura. Retorna máscara float TH x TW."""
    ppx, ppy = TW / W, TH / LEN       # px por metro (horizontal / vertical)
    S = 3
    mask = np.zeros((TH, TW), np.float32)
    def bez(p0, p1, p2, p3, n=28):
        t = np.linspace(0, 1, n)[:, None]
        p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
        return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)
    def mirror(pts): return np.concatenate([pts, pts[::-1] * np.array([-1, 1])])
    # região do emblema: 0.50 x 0.78 m
    rw, rh = 0.66, 1.0
    K = 1.2
    cw, ch = int(rw * ppx * S), int(rh * ppy * S)
    im = Image.new("L", (cw, ch), 0); d = ImageDraw.Draw(im)
    def P(pts): return [(cw / 2 + x * K * ppx * S, ch / 2 - y * K * ppy * S) for x, y in pts]
    def poly(pts): d.polygon(P(pts), fill=255)
    def line(pts, w_mm=2.4):
        d.line(P(pts), fill=255, width=max(2, int(w_mm / 1000 * K * ppx * S)), joint="curve")
    def dot(x, y, r):
        X, Y = P([(x, y)])[0]; d.ellipse((X - r * K * ppx * S, Y - r * K * ppy * S, X + r * K * ppx * S, Y + r * K * ppy * S), fill=255)
    # pétala central
    right = np.concatenate([bez((0, -0.03), (0.07, 0.02), (0.075, 0.15), (0.0, 0.30))])
    poly(np.concatenate([right, (right[::-1] * np.array([-1, 1]))]))
    # pétalas laterais (voluta)
    for sg in (1, -1):
        outer = bez((0.03, 0.05), (0.07, 0.24), (0.27, 0.22), (0.255, -0.03))
        inner = bez((0.255, -0.03), (0.235, 0.11), (0.11, 0.13), (0.045, 0.0))
        poly(np.concatenate([outer, inner]) * np.array([sg, 1]))
        dot(sg * 0.245, -0.035, 0.008)
    # faixa central
    poly([(-0.095, -0.02), (0.095, -0.02), (0.105, -0.045), (0.095, -0.07), (-0.095, -0.07), (-0.105, -0.045)])
    # cauda inferior: folha central + duas laterais
    cauda = bez((0.0, -0.07), (0.04, -0.11), (0.035, -0.17), (0, -0.26))
    poly(np.concatenate([cauda, cauda[::-1] * np.array([-1, 1])]))
    for sg in (1, -1):
        l = bez((0.03, -0.075), (0.12, -0.08), (0.17, -0.15), (0.12, -0.215))
        l2 = bez((0.12, -0.215), (0.11, -0.14), (0.07, -0.115), (0.025, -0.1))
        poly(np.concatenate([l, l2]) * np.array([sg, 1]))
    # filigrana: espirais laterais acima e abaixo, linhas e losangos
    for sg in (1, -1):
        for (y0, k) in ((0.04, 1.0), (-0.03, 0.8)):
            ang = np.linspace(0, 3.6 * math.pi, 60)
            rr = 0.035 * k * np.exp(-0.22 * ang)
            sp = np.stack([sg * (0.27 + rr * np.cos(ang) * 0.0 + (0.0)), np.zeros_like(ang)], 1)
        # espiral à direita da pétala
        ang = np.linspace(0, 3.2 * math.pi, 50); rr = 0.04 * np.exp(-0.2 * ang)
        line(np.stack([sg * (0.10 + 0.035 + rr * np.cos(ang)), 0.215 + rr * np.sin(ang) * 0.9], 1), 2.0)
        ang = np.linspace(0, 3.0 * math.pi, 50); rr = 0.035 * np.exp(-0.2 * ang)
        line(np.stack([sg * (0.165 + rr * np.cos(ang)), -0.275 + rr * np.sin(ang)], 1), 2.0)
        line(bez((0.07, 0.15), (0.11, 0.2), (0.13, 0.27), (0.09, 0.32)) * np.array([sg, 1]), 2.0)
        line(bez((0.03, -0.26), (0.08, -0.30), (0.12, -0.33), (0.10, -0.37)) * np.array([sg, 1]), 2.0)
        dot(sg * 0.09, 0.325, 0.005); dot(sg * 0.10, -0.375, 0.005)
        dot(sg * 0.15, 0.03, 0.004); dot(sg * 0.2, 0.02, 0.004)
    # eixo vertical com losangos
    line([(0, 0.30), (0, 0.38)], 2.2); line([(0, -0.26), (0, -0.37)], 2.2)
    for y in (0.34, 0.385, -0.31, -0.37):
        poly([(0, y + 0.018), (0.012, y), (0, y - 0.018), (-0.012, y)])
    poly([(0, 0.40), (0.008, 0.388), (-0.008, 0.388)])
    # nervuras vazadas (linhas escuras no centro das pétalas ficam depois, via máscara negativa)
    em = np.asarray(im.resize((int(rw * ppx), int(rh * ppy)), Image.LANCZOS), np.float32) / 255.0
    x0 = TW // 2 - em.shape[1] // 2; y0 = int(cx_s * TH) - em.shape[0] // 2
    mask[y0:y0 + em.shape[0], x0:x0 + em.shape[1]] = em
    return mask


def gerar_texturas(L, hol):
    W, LEN = L.W, L.LEN
    r = np.random.RandomState(7)
    yy, xx = np.mgrid[0:TH, 0:TW].astype(np.float32)
    u = xx / TW; s = yy / TH
    # --- altura (tecido) e cor
    n_low = fbm(TH, TW, 1, 3, 5); n_mid = fbm(TH, TW, 2, 12, 4); n_fine = blur(r.rand(TH, TW).astype(np.float32), 1.2); n_fine = np.clip((n_fine - n_fine.mean()) * 3 + 0.5, 0, 1)
    weave = (0.5 + 0.5 * np.sin(xx * 2 * math.pi / 8)) * (0.5 + 0.5 * np.sin(yy * 2 * math.pi / 8 + 1.7))
    streak = fbm(TH, TW, 3, 3, 4, aniso=(1.0, 14.0)) * 0.7 + fbm(TH, TW, 31, 3, 3, aniso=(6.0, 1.0)) * 0.3  # fios
    # veludo vermelho-sangue
    deep = np.array([0.30, 0.02, 0.035]); mid = np.array([0.62, 0.05, 0.07]); hi = np.array([0.80, 0.13, 0.12])
    t = np.clip(0.30 + 0.9 * (n_low - 0.5) + 0.35 * (streak - 0.5), 0, 1)
    col = lerp3(deep, mid, np.clip(t * 1.6, 0, 1))
    col = col + (hi - mid)[None, None, :] * (np.clip(t - 0.62, 0, 1) * 2.2)[..., None]
    col *= (0.93 + 0.07 * weave + 0.08 * (n_fine - 0.5))[..., None]
    # desgaste: fios desbotados (rosado/marrom) e manchas escuras
    wear = fbm(TH, TW, 5, 5, 5); wmask = _ss(0.60, 0.78, wear * (0.7 + 0.5 * s) )
    col = col * (1 - 0.65 * wmask[..., None]) + np.array([0.40, 0.17, 0.13])[None, None, :] * (0.65 * wmask[..., None]) * (0.7 + 0.5 * n_fine[..., None])
    dark = _ss(0.55, 0.8, fbm(TH, TW, 6, 4, 5))
    col *= (1 - 0.55 * dark[..., None])
    # mofo esverdeado e queimado (mais embaixo e nas bordas)
    edge = np.minimum.reduce([u, 1 - u]) * 1.0
    mold = _ss(0.62, 0.74, fbm(TH, TW, 8, 6, 5)) * np.clip(0.25 + 1.3 * s + 2.5 * (0.15 - edge).clip(0), 0, 1)
    col = col * (1 - 0.6 * mold[..., None]) + np.array([0.15, 0.19, 0.08])[None, None, :] * (0.6 * mold[..., None]) * (0.7 + 0.6 * n_mid[..., None])
    burn = _ss(0.72, 0.82, fbm(TH, TW, 9, 5, 5)) * (0.1 + 0.6 * s)
    col = col * (1 - 0.6 * burn[..., None]) + np.array([0.03, 0.02, 0.015])[None, None, :] * (0.6 * burn[..., None])
    # escurece ao redor dos buracos (queimado/chamuscado)
    for (hu, hs, hru, hrs) in hol:
        dd = np.sqrt(((u - hu) / (hru * 1.0 / W)) ** 2 + ((s - hs) / (hrs / LEN)) ** 2) if False else np.sqrt(((u - hu) * W / hru) ** 2 + ((s - hs) * LEN / hrs) ** 2)
        k = _ss(2.6, 1.0, dd) * 0.85
        col = col * (1 - k[..., None]) + np.array([0.025, 0.012, 0.01])[None, None, :] * k[..., None]
    # --- alturas
    H = np.zeros((TH, TW), np.float32)
    H += 0.22 * weave + 0.10 * n_fine + 0.15 * streak
    # --- faixas douradas laterais (linha grossa + linha fina + fio)
    gold_mask = np.zeros((TH, TW), np.float32)
    def band(a, b): return _ss(a - 0.0025, a + 0.0025, u) * (1 - _ss(b - 0.0025, b + 0.0025, u))
    for sg in (0, 1):
        uu = u if sg == 0 else 1 - u
        for (a, b) in ((0.050, 0.072), (0.082, 0.090), (0.097, 0.100)):
            gold_mask = np.maximum(gold_mask, _ss(a - 0.0025, a + 0.0025, uu) * (1 - _ss(b - 0.0025, b + 0.0025, uu)))
    # entre as faixas: vermelho mais escuro (fita)
    ribbon = np.zeros((TH, TW), np.float32)
    for sg in (0, 1):
        uu = u if sg == 0 else 1 - u
        ribbon = np.maximum(ribbon, _ss(0.045, 0.05, uu) * (1 - _ss(0.10, 0.105, uu)))
    col = col * (1 - 0.35 * ribbon[..., None])
    # bainha do topo: faixa mais escura e costura
    hem = (1 - _ss(0.046, 0.050, s))
    col = col * (1 - 0.35 * hem[..., None])
    seam_y = 0.047
    stitch = (np.abs(s - seam_y) < 0.0011) & ((xx % 14) < 9)
    stitch2 = (np.abs(s - 0.0085) < 0.0009) & ((xx % 22) < 15)
    gold_mask = np.maximum(gold_mask, stitch.astype(np.float32) * 0.8)
    gold_mask = np.maximum(gold_mask, stitch2.astype(np.float32) * 0.5)
    # emblema
    emb = emblema_mascara(W, LEN, 0.38)
    gold_mask = np.maximum(gold_mask, emb)
    # fio quebrado/desgaste do ouro
    gw = fbm(TH, TW, 12, 8, 5)
    gold_alpha = gold_mask * (1 - _ss(0.66, 0.85, gw) * 0.6) * (1 - 0.55 * burn) * (1 - 0.7 * mold * 0.6)
    gold_alpha = np.clip(gold_alpha, 0, 1)
    # alturas do bordado
    Hg = blur(gold_mask, 1.6) * 1.0
    H += 1.1 * Hg
    # relevo de bainha/costura
    H += 0.25 * hem
    # dobras finas no relevo (rugas)
    H += 0.8 * (fbm(TH, TW, 20, 6, 4, aniso=(2.0, 1.0)) - 0.5) * 0.4
    # cor do ouro: gradiente com brilho por relevo e fios
    gdark = np.array([0.38, 0.22, 0.05]); gmid = np.array([0.78, 0.55, 0.16]); glight = np.array([1.0, 0.86, 0.45])
    gx = np.gradient(blur(gold_mask, 1.2), axis=1); gy = -np.gradient(blur(gold_mask, 1.2), axis=0)
    light = np.clip(0.5 + 9.0 * (-0.7 * gx + 0.7 * gy), 0, 1)
    th = np.clip(0.55 * streak + 0.35 * n_fine + 0.35 * light, 0, 1)
    gcol = lerp3(gdark, gmid, np.clip(th * 1.6, 0, 1))
    gcol = gcol + (glight - gmid)[None, None, :] * (np.clip(th - 0.62, 0, 1) * 2.4)[..., None]
    gcol *= (0.9 + 0.12 * weave)[..., None]
    # tarnish verde-escuro nas bordas do ouro
    gcol = gcol * (1 - 0.35 * mold[..., None])
    col = col * (1 - gold_alpha[..., None]) + gcol * gold_alpha[..., None]
    # sombra suave ao redor do bordado (profundidade)
    sh = blur(gold_mask, 4) * (1 - gold_mask)
    col *= (1 - 0.35 * sh[..., None])
    # bordas escurecidas / barra inferior suja
    vign = np.clip(1 - 2.2 * (0.09 - edge).clip(0), 0.45, 1) * np.clip(1 - 0.22 * _ss(0.55, 1.0, s), 0, 1)
    col *= vign[..., None]
    # umidade/escurecimento perto da barra
    col *= (1 - 0.10 * _ss(0.8, 1.0, s) * (0.6 + 0.4 * n_mid))[..., None]
    col = np.clip(col, 0, 1)
    # sRGB (cores acima estão em "visual"): guarda direto
    alb = (col ** 1.0 * 255).astype(np.uint8)
    p_alb = os.path.join(L.TEX_DIR, "estandarte_pano_albedo.png"); Image.fromarray(alb, "RGB").save(p_alb)
    # --- normal map (OpenGL, +Y = acima) a partir da altura
    Hb = H * 1.0
    dx = np.gradient(Hb, axis=1); dyr = np.gradient(Hb, axis=0)
    k = 3.2
    nx, ny, nz = -dx * k, dyr * k, np.ones_like(dx)
    ln = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2); nx, ny, nz = nx / ln, ny / ln, nz / ln
    nrm = np.stack([(nx * 0.5 + 0.5), (ny * 0.5 + 0.5), (nz * 0.5 + 0.5)], -1)
    p_n = os.path.join(L.TEX_DIR, "estandarte_pano_normal.png"); Image.fromarray((nrm * 255).astype(np.uint8), "RGB").save(p_n)
    return p_alb, p_n


# ---------------------------------------------------------------- geometria
def surf(L, u, s):
    """Posição 3D do ponto do pano (u 0..1 esq→dir, s 0..1 topo→barra). Dobras reais de tecido pendurado."""
    u = np.asarray(u, np.float64); s = np.asarray(s, np.float64)
    W, TOP, LEN = L.W, L.TOP, L.LEN
    grow = s ** 0.8
    fade = _ss(0.0, 0.10, s)                           # presa e plana na barra superior
    a1 = (0.014 + 0.11 * grow) * fade
    a2 = (0.006 + 0.040 * grow) * fade
    a3 = (0.0015 + 0.006 * grow) * fade
    y = (a1 * np.sin(2 * math.pi * 2.35 * u + 0.6 + 0.9 * s)
         + a2 * np.sin(2 * math.pi * 5.3 * u + 2.1 - 1.6 * s)
         + a3 * np.sin(2 * math.pi * 11.7 * u + 0.3 + 2.4 * s))
    # gathering nas argolas (ilhós) no topo: costa onde está o anel, sobra entre
    ring_ph = (u - 0.10) / 0.16
    y += -0.020 * np.exp(-s / 0.07) * (1 - np.cos(2 * math.pi * ring_ph)) / 2
    # arqueamento geral e torção leve
    y += 0.07 * s ** 2 * np.sin(0.9 + 1.2 * u) + 0.20 * s ** 2.2 * (u - 0.5)
    # estreitamento e leve deriva lateral
    x = L.CX + (u - 0.5) * W * (1 - 0.07 * s ** 1.6) + 0.02 * s ** 2 * np.sin(2.0 + 3 * s)
    x += 0.006 * grow * np.cos(2 * math.pi * 2.35 * u + 0.6 + 0.9 * s)    # tecido se junta nas dobras
    z = TOP - s * LEN
    # as dobras encurtam o pano; borda superior com leve ondulação entre as argolas
    z += 0.35 * np.abs(y) * s
    return x, y, z


def construir_cortes(L, rs):
    """Retorna função keep(u_c, s_c) para faces: tiras rasgadas, fendas, buracos e bordas comidas."""
    # tiras da barra
    bounds = [0.0]
    while bounds[-1] < 1.0: bounds.append(bounds[-1] + rs.uniform(0.035, 0.11))
    bounds[-1] = 1.0
    strips = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        base = rs.uniform(0.80, 0.985)
        if rs.rand() < 0.2: base = rs.uniform(0.66, 0.78)             # rasgão fundo
        centro = abs((a + b) / 2 - 0.5)
        base -= 0.05 * (1 - centro * 2) * rs.rand()                    # meio costuma ser mais curto
        strips.append((a, b, base, rs.uniform(-0.06, 0.06)))
    slits = [(bounds[i], rs.uniform(0.04, 0.22)) for i in range(1, len(bounds) - 1) if rs.rand() < 0.45]
    # buracos (u, s, raio_m_x, raio_m_y)
    holes = [(0.28, 0.58, 0.035, 0.05), (0.72, 0.66, 0.045, 0.035), (0.78, 0.27, 0.022, 0.03), (0.2, 0.80, 0.03, 0.045),
             (0.80, 0.84, 0.03, 0.025), (0.45, 0.74, 0.018, 0.022), (0.88, 0.48, 0.02, 0.03), (0.12, 0.40, 0.016, 0.02)]
    HOLES.clear(); HOLES.extend(holes)
    seeds = rs.rand(2048)
    def keep(u, s, i):
        # barra: tira corresponde a u
        for (a, b, base, sl) in strips:
            if a <= u < b:
                ln = base + sl * (u - a) / (b - a) - 0.5 * sl
                if s > ln: return False
                break
        for (bu, ds) in slits:
            if abs(u - bu) < 0.55 / NX and s > 1.0 - ds - 0.02 and s > 0.55 + 0.0: 
                if s > strips_len_at(bu) - ds: return False
        # buracos (borda irregular)
        for (hu, hs, rx, ry) in holes:
            dx = (u - hu) * L.W / rx; dy = (s - hs) * L.LEN / ry
            dd = math.hypot(dx, dy) * (1 + 0.28 * math.sin(3 * math.atan2(dy, dx) + hu * 20) + 0.15 * math.sin(7 * math.atan2(dy, dx) + hs * 30))
            if dd < 1.0: return False
        # bordas laterais comidas e roídas no fim da barra
        edge = min(u, 1 - u)
        if edge < 1.2 / NX and s > 0.35 and seeds[i % 2048] < 0.20 * (s - 0.2): return False
        # leve mordida na barra
        for (a, b, base, sl) in strips:
            if a <= u < b:
                ln = base + sl * (u - a) / (b - a) - 0.5 * sl
                if s > ln - 0.018 and seeds[(i * 7) % 2048] < 0.28: return False
                break
        return True
    def strips_len_at(bu):
        for (a, b, base, sl) in strips:
            if a <= bu < b: return base
        return 0.95
    return keep, strips


def malha_pano(L, keep):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    vs = []; idx = []
    for j in range(NY + 1):
        row = []
        s = j / NY
        for i in range(NX + 1):
            u = i / NX
            x, y, z = surf(L, u, s)
            v_ = bm.verts.new((float(x), float(y), float(z))); v_.index = len(idx); idx.append((i, j)); row.append(v_)
        vs.append(row)
    for j in range(NY):
        for i in range(NX):
            uc = (i + 0.5) / NX; sc = (j + 0.5) / NY
            if not keep(uc, sc, j * NX + i): continue
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            f.normal_flip()  # normais para +Y (frente)
            f.smooth = True
            for lp in f.loops:   # UV pela posição do vértice (o flip inverte a ordem dos loops)
                ii, jj = idx[lp.vert.index]
                lp[uvl].uv = (ii / NX, 1 - jj / NY)
    # remove vértices soltos
    for v in [v for v in bm.verts if not v.link_faces]: bm.verts.remove(v)
    # irregularidade fina nas bordas: desloca vértices de contorno (ondulação de fio solto)
    rs = np.random.RandomState(3)
    for v in bm.verts:
        if v.is_boundary:
            v.co += Vector((rs.normal(0, 0.0025), rs.normal(0, 0.004), rs.normal(0, 0.0025)))
    return bm


def franjas(L, strips, rs, m):
    """Fios desfiados pendurados nas pontas das tiras (fitas finas com curvatura)."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    for (a, b, base, sl) in strips:
        n = rs.randint(3, 8)
        for k in range(n):
            u = rs.uniform(a, b)
            ln = base + sl * (u - a) / (b - a) - 0.5 * sl - 0.005
            if ln > 0.99: ln = 0.99
            seg = rs.randint(5, 9); length = rs.uniform(0.04, 0.16); w = rs.uniform(0.0016, 0.0032)
            x0, y0, z0 = surf(L, u, ln)
            drift = rs.normal(0, 0.012); dy = rs.normal(0, 0.012); curl = rs.normal(0, 0.05)
            prev = None
            for q in range(seg + 1):
                t = q / seg
                px = x0 + drift * t + curl * t * t * 0.2
                py = y0 + dy * t + 0.01 * t * t * rs.normal()
                pz = z0 - length * t
                wv = w * (1 - 0.6 * t)
                a_ = bm.verts.new((px - wv, py, pz)); b_ = bm.verts.new((px + wv, py, pz))
                if prev:
                    f = bm.faces.new((prev[0], prev[1], b_, a_)); f.smooth = True
                    for lp, vv in zip(f.loops, (prev[0], prev[1], b_, a_)):
                        lp[uvl].uv = (min(max(u, 0), 1), 1 - min(0.995, ln + 0.002 * q))
                prev = (a_, b_)
    # dupla face
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    geom = bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)
    newf = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.reverse_faces(bm, faces=newf)
    return bm


def aneis(L, m_ferro, m_latao):
    """Argolas de ferro no braço (círculos no plano YZ em volta do eixo x) e ilhós de latão no pano."""
    R = L.ARM_Z - (L.TOP - 0.03)           # raio do anel: toca o pano na altura do ilhó
    R = 0.085
    for i in range(6):
        u = 0.10 + 0.16 * i
        x = float(L.CX + (u - 0.5) * L.W)
        bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=0.0085, major_segments=28, minor_segments=8,
                                         location=(x, 0, L.ARM_Z), rotation=(0, math.radians(90), 0))
        o = bpy.context.object; o.name = f"Argola_{i}"
        bpy.ops.object.shade_smooth()
        L.add(o, m_ferro)
        # ilhós de latão no pano (plano XZ, em torno do ponto onde o anel o atravessa)
        xs, ys, zs = surf(L, u, (L.TOP - (L.ARM_Z - R)) / L.LEN)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.019, minor_radius=0.0055, major_segments=20, minor_segments=8,
                                         location=(float(xs), float(ys), float(zs)), rotation=(math.radians(90), 0, 0))
        g = bpy.context.object; g.name = f"Ilhos_{i}"; bpy.ops.object.shade_smooth()
        L.add(g, m_latao)


def build(L):
    rs = np.random.RandomState(11)
    keep, strips = construir_cortes(L, rs)
    p_alb, p_n = gerar_texturas(L, [(h[0], h[1], h[2], h[3]) for h in HOLES])
    m = L.mat("Estandarte_Pano", (0.4, 0.04, 0.05), metal=0.0, rough=0.88, image=p_alb, normal=(None if os.environ.get("SEMNORMAL") else p_n))
    bm = malha_pano(L, keep)
    o = L.new_obj("Pano", bm, m)
    # espessura real do tecido
    bpy.context.view_layer.objects.active = o
    mod = o.modifiers.new("esp", 'SOLIDIFY'); mod.thickness = 0.007; mod.offset = 0; mod.use_rim = True
    bpy.ops.object.modifier_apply(modifier="esp")
    for p in o.data.polygons: p.use_smooth = True
    # franjas
    fb = franjas(L, strips, np.random.RandomState(5), m)
    fo = L.new_obj("Franjas", fb, m)
    m_f = L.mat("Estandarte_Argola", (0.10, 0.085, 0.08), metal=0.9, rough=0.55)
    m_l = L.mat("Estandarte_Ilhos", (0.62, 0.42, 0.14), metal=0.85, rough=0.4)
    aneis(L, m_f, m_l)
