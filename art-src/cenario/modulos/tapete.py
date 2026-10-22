"""Tapete da Cripta (módulo 2,4 x 6,0 m, deitado no piso). Partes: padrao (albedo+normal pintados), pano (grade com dobras e bordas viradas), franjas.
bpy: python tapete.py -- <saida.glb> [pasta_previas]    PARTES=padrao,pano,franjas  VISTAS=...  AMOSTRAS=16
Pivô no centro do tapete, +Z para cima, comprimento no eixo Y, metros."""
import sys, os, math, json, struct, random
import numpy as np
from PIL import Image, ImageDraw

LW, LL = 2.4, 6.0                      # largura x comprimento (m)
TW, TH = 1024, 2560                    # textura (px): 1 px = 2,34 mm
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

def gen_padrao():
    """Albedo RGBA (alfa = silhueta rasgada e furos) + normal. Retorna (albedo, normal, alfa) e grava PNGs."""
    W, H = TW, TH; rr = np.random.default_rng(11)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dedge = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy))
    n_l, n_m, n_s = noise(H, W, 6, 1), noise(H, W, 40, 2), noise(H, W, 220, 3)
    # ---- silhueta: borda rasgada com mordidas e furos de desgaste
    bite = np.zeros_like(dedge)
    for _ in range(14):
        side = rr.integers(0, 4); depth = rr.uniform(14, 48); width = rr.uniform(20, 90)
        t = rr.uniform(0.08, 0.92)
        cx, cy = (t * W, 0) if side == 0 else (t * W, H) if side == 1 else (0, t * H) if side == 2 else (W, t * H)
        bite = np.maximum(bite, depth * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * width ** 2))))
    inset = 4 + 8 * np.abs(n_m) + 7 * np.abs(n_s) * 1.4 + bite
    holes = np.zeros_like(dedge); wear = np.zeros_like(dedge)
    for _ in range(11):               # manchas gastas (centros em cantos e miolo)
        cx, cy = rr.uniform(0.08, 0.92) * W, rr.uniform(0.05, 0.95) * H; rad = rr.uniform(60, 190)
        wear = np.maximum(wear, np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rad ** 2))) * rr.uniform(0.6, 1.1))
    wear = np.clip(wear + 0.35 * n_m * 0.5, 0, 1.3) * (0.7 + 0.5 * n_l)
    hole = np.zeros(dedge.shape, bool)
    n_h = noise(H, W, 90, 21)
    for _ in range(9):               # aglomerados de furos, mais perto das bordas e de dois cantos
        side = rr.random()
        cx = rr.uniform(0.1, 0.9) * W; cy = rr.uniform(0.04, 0.96) * H
        if side < 0.5: cx = rr.choice((0.1, 0.9)) * W + rr.uniform(-60, 60)
        rad = rr.uniform(45, 120)
        f = np.exp(-(((xx - cx) ** 2 + ((yy - cy) * 1.3) ** 2) / (2 * rad ** 2))) + 0.6 * n_h + 0.10 * n_s
        hole |= f > 1.02
    for _ in range(18):               # furtinhos e cortes
        cx, cy = rr.uniform(0.05, 0.95) * W, rr.uniform(0.04, 0.96) * H; rad = rr.uniform(9, 26)
        hole |= ((xx - cx) ** 2 + ((yy - cy) * rr.uniform(0.5, 2.2)) ** 2) < rad ** 2 * (0.5 + 1.0 * np.abs(n_s))
    for _ in range(2):                # cortes finos rasgados (como na referência)
        cx, cy = rr.uniform(0.3, 0.7) * W, rr.uniform(0.1, 0.9) * H
        hole |= (np.abs(xx - cx - 0.0 * (yy - cy)) < 5 * (1 - np.abs(yy - cy) / 110)) & (np.abs(yy - cy) < 110)
    alive = (dedge > inset) & ~hole
    alpha = smooth(0, 1.6, (dedge - inset)) * (~hole)
    hole_d = gauss(hole.astype(np.float32), 3.0)
    edge_d = np.clip(1 - (dedge - inset) / 10, 0, 1)
    frays = np.clip(np.maximum(hole_d * 1.8, edge_d) , 0, 1) * alive
    # ---- base vermelha, trama e pelo
    A = np.zeros((H, W, 3), np.float32)
    base = np.array((0.52, 0.07, 0.085), np.float32)
    A[:] = base
    A *= (0.78 + 0.22 * n_l[..., None] + 0.16 * n_m[..., None] + 0.08 * n_s[..., None])
    weave = gauss((np.sin(xx * math.pi * 2 / 4.0) * np.sin(yy * math.pi * 2 / 4.0)) * 0.5 + 0.5, 0.6)
    A *= (0.93 + 0.12 * weave[..., None])
    # damasco: losangos sutis no campo
    u = (xx / 128.0); v = (yy / 160.0)
    lat = np.abs(((u + v) % 1) - 0.5) < 0.012; lat |= np.abs((((u - v) % 1)) - 0.5) < 0.012
    field = smooth(212, 220, dedge)
    A[lat] *= 1.0 + 0.0
    A *= (1 + 0.12 * (lat.astype(np.float32) * field)[..., None])
    gold_mask = np.zeros((H, W), np.float32)
    # ---- bordas (distância à borda em px)
    def band(a, b): return smooth(a - 1, a + 1, dedge) * (1 - smooth(b - 1, b + 1, dedge))
    gold_mask = np.maximum(gold_mask, band(30, 54)); gold_mask = np.maximum(gold_mask, band(96, 104))
    gold_mask = np.maximum(gold_mask, band(170, 178)); gold_mask = np.maximum(gold_mask, band(196, 212))
    A *= (1 - 0.25 * band(54, 96)[..., None])          # faixa vermelha entre ouros, mais escura
    A *= (1 - 0.35 * band(0, 30)[..., None])           # ourela (orla) escura
    # faixa de guarda: losangos dourados ao longo do perímetro
    sx = np.where((xx < dedge + 0.5) | (xx > W - 1 - dedge - 0.5), yy, xx)
    pat = 52.0; ub = ((sx % pat) / pat) - 0.5; tb = (dedge - 104) / 66.0 - 0.5
    dia = (np.abs(ub) * 1.0 + np.abs(tb) * 1.0 < 0.38) & (dedge > 104) & (dedge < 170)
    dia2 = (np.abs(ub) + np.abs(tb) < 0.15) & (dedge > 104) & (dedge < 170)
    gold_mask = np.maximum(gold_mask, dia.astype(np.float32) * 0.9); A *= (1 - 0.35 * (dia2 & ~dia)[..., None])
    A[dia2] = base * 0.8
    # ---- ornamentos centrais
    def stamp(img_mask, cx, cy, mk):
        h, w = mk.shape; x0, y0 = int(cx - w / 2), int(cy - h / 2)
        img_mask[y0:y0 + h, x0:x0 + w] = np.maximum(img_mask[y0:y0 + h, x0:x0 + w], mk)
    orn = np.zeros((H, W), np.float32)
    stamp(orn, W / 2, H / 2, motif(560, 1080, 1))
    for dy in (-780, 780): stamp(orn, W / 2, H / 2 + dy, motif(420, 520, 2 + (dy > 0)))
    gold_mask = np.maximum(gold_mask, orn)
    # ---- ouro: fios de cetim, relevo, desgaste
    stitch = 0.88 + 0.12 * np.sin(yy * math.pi / 3.0 + xx * 0.35) + 0.12 * n_s
    gcol = np.array((0.78, 0.60, 0.26), np.float32) * (0.72 + 0.30 * n_m[..., None]) * stitch[..., None]
    gcol *= (0.85 + 0.3 * smooth(0.2, 0.8, gauss(gold_mask, 1.2))[..., None])
    gm = gold_mask * (1 - np.clip((wear - 0.55) * 2.0, 0, 1)) * (n_s * 0.2 + 0.85 > 0.55)
    # contorno escuro (sombra do bordado)
    sh = np.clip(gauss(gold_mask, 2.2) - gold_mask, 0, 1)
    A *= (1 - 0.45 * sh[..., None])
    A = A * (1 - gm[..., None]) + gcol * gm[..., None]
    # ---- desgaste: pelo gasto mostra trama de fundo marrom; sujeira; manchas
    wear_c = np.clip((wear - 0.4) * 1.5, 0, 1) * (0.6 + 0.5 * np.abs(n_s))
    under = np.array((0.20, 0.13, 0.10), np.float32) * (0.7 + 0.4 * weave[..., None])
    A = A * (1 - 0.8 * wear_c[..., None]) + under * (0.8 * wear_c[..., None])
    dirt = smooth(-0.1, 0.7, n_l * 0.7 + n_m * 0.5)
    A *= (1 - 0.35 * dirt[..., None] * np.array((0.6, 0.8, 0.9)))
    stain = smooth(0.35, 0.65, noise(H, W, 12, 9) * 0.5 + 0.5) * smooth(0.5, 1.0, np.abs(n_m) + 0.3)
    A = A * (1 - 0.35 * stain[..., None]) + np.array((0.07, 0.03, 0.03)) * 0.35 * stain[..., None]
    A *= (1 - 0.55 * np.clip((16 - (dedge - inset)) / 16, 0, 1)[..., None])    # borda escurecida
    A[hole & False] = 0
    A *= (1 - 0.6 * (np.clip(hole_d * 1.6, 0, 1))[..., None] * alive[..., None])  # aro escuro dos furos
    A = np.clip(A, 0, 1)
    # ---- altura -> normal
    ht = weave * 0.12 + n_s * 0.30 + 0.20 * n_m
    ht += 0.9 * gauss(gold_mask, 0.8) + 0.3 * stitch * gold_mask       # bordado em relevo
    ht -= 0.8 * wear_c + 1.2 * frays
    ht -= 0.5 * lat.astype(np.float32) * field
    gx = np.gradient(ht, axis=1); gy = np.gradient(ht, axis=0)
    k = 5.0
    N = np.dstack([-gx * k, gy * k, np.ones_like(ht)]); N /= np.linalg.norm(N, axis=2, keepdims=True)
    N = (N * 0.5 + 0.5)
    rgba = np.dstack([A, alpha])
    out_a = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA")
    out_n = Image.fromarray((N * 255).astype(np.uint8), "RGB")
    out_a = out_a.transpose(Image.FLIP_TOP_BOTTOM); out_n = out_n.transpose(Image.FLIP_TOP_BOTTOM)
    out_a.save(f"{TEX}/tapete_albedo.png"); out_n.save(f"{TEX}/tapete_normal.png")
    np.save(f"{TEX}/alive.npy", np.flipud(alpha > 0.5))
    print("padrao ok")

# ------------------------------------------------------------------ Blender
def blender_part():
    import bpy, bmesh
    from mathutils import Vector
    objs = []
    def mat(name, color, rough=1.0, image=None, normal=None):
        m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = 0
        try: b.inputs["Specular IOR Level"].default_value = 0.25
        except KeyError: pass
        if image:
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(image); t.image.pack()
            nt.links.new(t.outputs["Color"], b.inputs["Base Color"]); nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
        if normal:
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(normal); t.image.pack(); t.image.colorspace_settings.name = "Non-Color"
            n = nt.nodes.new("ShaderNodeNormalMap"); n.inputs["Strength"].default_value = 0.9
            nt.links.new(t.outputs["Color"], n.inputs["Color"]); nt.links.new(n.outputs["Normal"], b.inputs["Normal"])
        return m
    def new(name, bm, m):
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); o.data.materials.append(m); objs.append(o); return o

    ONLY = os.environ.get("PARTES", "padrao,pano,franjas").split(",")
    if "padrao" in ONLY: gen_padrao()
    alive = np.load(f"{TEX}/alive.npy")        # [v (de baixo p/ cima), u]
    mt = mat("M_TapeteTecido", (0.4, 0.05, 0.06), 1.0, f"{TEX}/tapete_albedo.png", f"{TEX}/tapete_normal.png")

    def height(x, y):
        """Dobras e bordas viradas: x,y em metros a partir do centro."""
        z = 0.004 * (1 + 0.5 * math.sin(x * 9 + y * 4)) * 0.5
        u, v = x / LW + 0.5, y / LL + 0.5
        z += 0.016 * math.sin(y * 3.1 + 0.8 * math.sin(x * 2.3)) * math.exp(-((x - 0.5) ** 2) / 0.8)        # ondas longitudinais
        z += 0.010 * math.sin(x * 13 + y * 5.5) * math.sin(y * 2.9 + 1)                                       # pregas curtas
        # prega alta cruzando o tapete (dobra esmagada)
        for (yc, ang, h0) in ((-1.4, 0.35, 0.075), (1.9, -0.25, 0.055), (0.2, 0.1, 0.03)):
            dd = (y - yc) - math.tan(ang) * x
            z += h0 * math.exp(-(dd / 0.14) ** 2) * (0.6 + 0.4 * math.sin(x * 4))
        # bordas viradas para cima, mais em alguns trechos
        d = min(LW / 2 - abs(x), LL / 2 - abs(y))
        rng_ = 0.5 + 0.5 * math.sin(x * 5.3 + y * 3.7) * math.sin(x * 1.7 - y * 2.3)
        z += (0.035 * rng_ + 0.01) * math.exp(-max(d, 0) / 0.05)
        # cantos mais virados
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            cd = math.hypot(x - sx * LW / 2, y - sy * LL / 2)
            if sx * sy > 0 or True: z += 0.11 * math.exp(-(cd / 0.22) ** 2) * (1 if (sx, sy) in ((1, 1), (-1, -1)) else 0.3)
        return max(z + 0.014, 0.004)

    if "pano" in ONLY:
        NX, NY = 60, 150; cell = LW / NX
        bm = bmesh.new(); uv = bm.loops.layers.uv.new()
        vs = [[bm.verts.new((((i / NX) - 0.5) * LW, ((j / NY) - 0.5) * LL, height(((i / NX) - 0.5) * LW, ((j / NY) - 0.5) * LL))) for i in range(NX + 1)] for j in range(NY + 1)]
        for j in range(NY):
            for i in range(NX):
                u0, u1 = i / NX, (i + 1) / NX; v0, v1 = j / NY, (j + 1) / NY
                a = alive[int(v0 * (TH - 1)):int(v1 * (TH - 1)) + 1, int(u0 * (TW - 1)):int(u1 * (TW - 1)) + 1]
                if not a.any(): continue
                f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
                for l, (u, v) in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))): l[uv].uv = (u, v)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        new("Tapete_Pano", bm, mt)
        o = objs[-1]
        for p in o.data.polygons: p.use_smooth = True

    if "franjas" in ONLY:
        r = random.Random(7)
        mf = mat("M_TapeteFranja", (0.50, 0.33, 0.15), 1.0)
        bm = bmesh.new()
        for sgn in (-1, 1):
            n = 150
            for k in range(n):
                if r.random() < 0.14: continue                    # falhas
                x0 = ((k + 0.5) / n - 0.5) * (LW * 0.975) + r.uniform(-0.004, 0.004)
                ln = r.uniform(0.075, 0.115) * (0.45 if r.random() < 0.15 else 1)
                ang = r.uniform(-0.28, 0.28); ph = r.uniform(0, 6.3); wd = 0.0055
                y0 = sgn * (LL / 2 - 0.03); rows = []
                for s_ in range(8):
                    t = s_ / 7; yy = y0 + sgn * (ln + 0.03) * t * math.cos(ang); xx = x0 + (ln + 0.03) * t * math.sin(ang) + 0.006 * math.sin(t * 7 + ph)
                    zz = max(0.0035, height(xx, max(min(abs(yy), LL / 2 - 0.001), 0) * sgn) * (1 - t) ** 1.5 + 0.0035 + 0.004 * math.sin(t * 9 + ph) ** 2)
                    ww = wd * (1 - 0.25 * t)
                    rows.append((bm.verts.new((xx - ww, yy, zz)), bm.verts.new((xx + ww, yy, zz + 0.002))))
                for s_ in range(7):
                    q = (rows[s_][0], rows[s_][1], rows[s_ + 1][1], rows[s_ + 1][0])
                    bm.faces.new(q if sgn > 0 else q[::-1])
        new("Tapete_Franjas", bm, mf)
    return bpy, objs

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    OUT = argv[0] if argv else "SM_Cripta_Tapete.glb"; PREV = argv[1] if len(argv) > 1 else None
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy, objs = blender_part()
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    for o in objs:
        pass
    bpy.ops.object.join(); o = bpy.context.object; o.name = "SM_Cripta_Tapete"
    print("faces", len(o.data.polygons), "dim", tuple(round(x, 2) for x in o.dimensions))
    bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format="GLB", export_yup=True, export_image_format="AUTO")
    # alfa em modo MASK (recorte), face dupla
    with open(OUT, "rb") as f: data = f.read()
    jl = struct.unpack("<I", data[12:16])[0]; js = json.loads(data[20:20 + jl]); rest = data[20 + jl:]
    for m in js["materials"]:
        if m["name"] == "M_TapeteTecido": m["alphaMode"] = "MASK"; m["alphaCutoff"] = 0.5; m["doubleSided"] = True
        if m["name"] == "M_TapeteFranja": m["doubleSided"] = True
    jb = json.dumps(js, separators=(",", ":")).encode(); jb += b" " * ((4 - len(jb) % 4) % 4)
    with open(OUT, "wb") as f:
        f.write(data[:8] + struct.pack("<I", 12 + 8 + len(jb) + len(rest)) + struct.pack("<I", len(jb)) + b"JSON" + jb + rest)
    if PREV: render(bpy, o, PREV)

def render(bpy, o, PREV):
    from mathutils import Vector
    os.makedirs(PREV, exist_ok=True); sc = bpy.context.scene
    # piso de pedra escura para dar contexto
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, -0.03)); fl = bpy.context.object
    fm = bpy.data.materials.new("piso"); fm.use_nodes = True; fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.11, 0.10, 0.095, 1); fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    fl.data.materials.append(fm)
    sc.render.engine = "CYCLES"; sc.cycles.samples = int(os.environ.get("AMOSTRAS", "24")); sc.cycles.device = "CPU"; sc.cycles.use_denoising = True
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.055, 0.08, 1); sc.world = w
    def sun(rot, e, c):
        s = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN")); s.data.energy = e; s.data.color = c; s.rotation_euler = rot; bpy.context.collection.objects.link(s)
    sun((math.radians(50), 0, math.radians(35)), 3.2, (1.0, 0.85, 0.7)); sun((math.radians(65), 0, math.radians(-140)), 1.0, (0.55, 0.65, 1.0))
    views = {"cima": ((0, 0, 11), (0, 0, 0), 560, 1000), "tres_quartos": ((3.5, -7.5, 5.5), (0, 0, 0), 900, 650), "jogo_3q": ((0, -9, 8), (0, 0, 0), 900, 650),
             "close_medalhao": ((0.9, -1.4, 1.6), (0, 0, 0), 800, 800), "close_borda": ((1.25, -2.7, 0.55), (1.0, -2.85, 0), 800, 800), "close_franja": ((0.2, -3.5, 0.45), (0, -3.1, 0), 800, 800), "rasante": ((-5.5, -2.5, 0.9), (0, 0, 0), 900, 500), "wire": ((0, -4.5, 7.5), (0, 0, 0), 900, 650)}
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
        if nome == "cima": cam.type = "ORTHO"; cam.ortho_scale = 6.6
        if nome.startswith("close"): cam.lens = 35
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.camera = co; sc.render.resolution_x = rx; sc.render.resolution_y = ry
        sc.render.filepath = os.path.join(PREV, f"{nome}.png"); bpy.ops.render.render(write_still=True)
        if nome == "wire": bpy.data.objects.remove(w_, do_unlink=True); o.hide_render = False; fl.hide_render = False

if __name__ == "__main__": main()
