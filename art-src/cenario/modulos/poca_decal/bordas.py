"""Bordas da poça: lama fina, cascalho miúdo e fiapos de musgo, pintados em numpy/PIL (supersample 3x)."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

SS = 3

def _stub_mask(L):
    from scipy.ndimage import gaussian_filter
    r = np.hypot(L.X / (L.w * 0.36), L.Z / (L.h * 0.36))
    ang = np.arctan2(L.Z, L.X)
    r = r * (1 + 0.12 * np.sin(3 * ang + 1) + 0.07 * np.sin(7 * ang))
    water = np.clip((1 - r) * L.PPM * 0.3, 0, 1).astype(np.float32)
    signed = lib.dist_m(water > 0.5).astype(np.float32)
    n = lib.fbm(L, 6, 3, 5)
    wet = np.clip(np.exp(-np.maximum(signed, 0) / (0.03 + 0.08 * n)), 0, 1).astype(np.float32)
    wet = np.maximum(wet, water)
    return dict(wet=wet, water=water, signed=signed)

def _smooth(t): return t * t * (3 - 2 * t)

def _pick(rng, prob, n):
    p = prob.ravel().astype(np.float64); s = p.sum()
    if s <= 0 or n <= 0: return np.zeros((0, 2))
    idx = rng.choice(p.size, size=n, p=p / s)
    ys, xs = np.divmod(idx, prob.shape[1])
    return np.stack([xs + rng.random(n), ys + rng.random(n)], 1)

def build(L, m):
    rng = np.random.default_rng(L.seed * 977 + 5)
    H, W = L.H, L.W
    sg = m["signed"].astype(np.float32); wet = m["wet"].astype(np.float32); water = m["water"]
    out_d = np.maximum(sg, 0)
    ppm = L.PPM
    n1 = lib.fbm(L, 9, 4, 1); n2 = lib.fbm(L, 4, 3, 2); n3 = lib.fbm(L, 25, 3, 3)

    # ---- campos de direção
    sgs = lib.suave(sg, 0.012); gy, gx = np.gradient(sgs)
    gn = np.hypot(gx, gy) + 1e-6; gx, gy = gx / gn, gy / gn          # aponta para fora da água
    wts = lib.suave(wet, 0.012); wy, wx = np.gradient(wts)
    wn = np.hypot(wx, wy) + 1e-6; wx, wy = wx / wn, wy / wn          # aponta para onde há mais umidade (frestas)

    # ---- lama fina: manchas irregulares e curtas, nunca um anel
    patchy = _smooth(np.clip((n1 * 0.6 + n2 * 0.4 - 0.42) * 4.5, 0, 1))
    reach = 0.004 + 0.022 * n2 + 0.02 * wet
    mud_a = np.clip(1 - out_d / reach, 0, 1) ** 1.3 * patchy * (1 - water)
    mud_a = mud_a * (0.55 + 0.45 * n3) * 0.85
    mud_a = np.clip(mud_a + (n3 - 0.5) * 0.04 * (mud_a > 0.02), 0, 0.5)
    t = (n1 - 0.5) * 2
    mud_rgb = np.stack([0.15 + 0.02 * t, 0.145 + 0.015 * t, 0.15 + 0.005 * t], -1)

    # ---- densidades
    band = np.exp(-np.maximum(sg + 0.003, 0) / 0.025) * (sg > -0.004)
    fil = np.clip(wet - 0.25, 0, 1) * (sg > 0.0)
    dens_g = (band * (0.15 + 1.4 * _smooth(np.clip(n2 * 1.6 - 0.35, 0, 1))) + 0.12 * fil * n3) * (water < 0.5)
    dens_g = dens_g * (0.35 + 2.0 * n1 ** 2)

    # ---- canvas supersampleados (substituição direta; composição correta depois)
    def canv(mode, bg): return Image.new(mode, (W * SS, H * SS), bg)
    shad = canv("RGBA", (0, 0, 0, 0)); gra = canv("RGBA", (0, 0, 0, 0)); mos = canv("RGBA", (0, 0, 0, 0))
    hgt = canv("L", 128)
    ds, dg, dm, dh = (ImageDraw.Draw(c) for c in (shad, gra, mos, hgt))

    # ---- cascalho
    peri = max(0.5, float((np.abs(sg) < 0.004).sum()) / (0.008 * ppm) / ppm)   # perímetro da água + filetes (m)
    ng = int(min(30000, 2000 * peri))        # densidade por metro de borda (calibrada na poça A)
    pts = _pick(rng, dens_g, ng)
    base = np.array([0.21, 0.24, 0.30])
    def grain(x, y, d, big=False):
        r = d / 2 * SS / 1000 * ppm                # d em mm -> raio em px supersample
        r = max(r, 0.7)
        asp = rng.uniform(0.65, 1.0); rot = rng.uniform(0, math.pi)
        k = 0.6 + rng.random() * 0.75
        tone = np.array([rng.uniform(-0.015, 0.015), rng.uniform(-0.01, 0.015), rng.uniform(0.0, 0.03)])
        if rng.random() < 0.12: tone += np.array([0.03, 0.02, -0.01])   # raros grãos mais quentes
        col = np.clip(base * k + tone, 0, 1)
        cx, cy = x * SS, y * SS
        def poly(rr, ox=0, oy=0, wob=0.18):
            n = 9 if r < 6 else 16
            a = np.linspace(0, 2 * math.pi, n, endpoint=False)
            rad = rr * (1 + wob * (rng.random(n) - 0.5))
            px = rad * np.cos(a) * 1.0; py = rad * np.sin(a) * asp
            c, s = math.cos(rot), math.sin(rot)
            return [(cx + ox + c * u - s * v, cy + oy + s * u + c * v) for u, v in zip(px, py)]
        return r, col, poly, cx, cy
    grains = []
    for i in range(len(pts)):
        u = rng.random()
        d = 1.2 + 4.8 * u ** 1.6                    # 1.2..6 mm
        if rng.random() < 0.012: d = rng.uniform(10, 20)   # poucos de 1-2 cm
        grains.append((pts[i, 0], pts[i, 1], d))
    for x, y, d in grains:                          # sombras
        r, col, poly, cx, cy = grain(x, y, d)
        o = max(0.9, r * 0.55)
        ds.polygon(poly(r * 1.05, o * 0.7, o), fill=(5, 7, 12, int(150 if d > 6 else 105)))
        dh.polygon(poly(r * 1.05, o * 0.7, o), fill=112)
    for x, y, d in grains:                          # corpos
        r, col, poly, cx, cy = grain(x, y, d)
        c8 = tuple(int(v * 255) for v in col)
        dg.polygon(poly(r), fill=c8 + (255,))
        dh.polygon(poly(r), fill=int(150 + 40 * min(1, r / 8)))
        if r > 1.6:
            hi = tuple(int(min(255, v * 255 * 1.22 + 6)) for v in col)
            dg.polygon(poly(r * 0.62, -r * 0.2, -r * 0.28), fill=hi + (255,))
            lo = tuple(int(v * 255 * 0.7) for v in col)
            dg.polygon(poly(r * 0.38, r * 0.4, r * 0.45, 0.4), fill=lo + (150,))
            dh.polygon(poly(r * 0.6, -r * 0.1, -r * 0.1), fill=int(185 + 30 * min(1, r / 8)))

    # ---- musgo: fitas curvas em grupos
    mdens = band * (0.1 + _smooth(np.clip(n2 * 2.0 - 0.7, 0, 1))) + 0.3 * fil * _smooth(np.clip(n1 * 2 - 0.9, 0, 1))
    mdens = mdens * (water < 0.5)
    ncl = max(6, int(peri * 6.0))             # grupos de musgo por metro de borda
    centers = _pick(rng, mdens, ncl)
    greens = [np.array(c) for c in ([0.07, 0.14, 0.07], [0.11, 0.20, 0.08], [0.18, 0.26, 0.08], [0.13, 0.23, 0.10], [0.08, 0.18, 0.10], [0.21, 0.27, 0.09])]
    def ribbon(x0, y0, ang, length, wmax, base_c, leaf):
        # centro-linha em px supersample
        nseg = 14; step = length / nseg
        pts_ = [(x0, y0)]; a = ang; curv = rng.normal(0, 0.12)
        for i in range(nseg):
            a += curv + rng.normal(0, 0.05)
            pts_.append((pts_[-1][0] + step * math.cos(a), pts_[-1][1] + step * math.sin(a)))
        P = np.array(pts_)
        T = np.gradient(P, axis=0); T /= (np.hypot(T[:, 0], T[:, 1])[:, None] + 1e-9)
        N = np.stack([-T[:, 1], T[:, 0]], 1)
        s = np.linspace(0, 1, nseg + 1)
        prof = (np.sin(np.pi * np.clip(s * 0.97 + 0.015, 0, 1)) ** 0.7) if leaf else (1 - s ** 2.2) * np.minimum(1, s * 8 + 0.35)
        wd = wmax * np.maximum(prof, 0.06)
        Lf = P + N * wd[:, None] / 2; Rg = P - N * wd[:, None] / 2
        tone = 0.82 + 0.35 * rng.random()
        for i in range(nseg):
            f = i / nseg
            al = 255 if f < 0.6 else int(255 - (f - 0.6) / 0.4 * 150)
            shade = tone * (0.9 + 0.2 * math.sin(f * 5 + rng.random()))
            c = np.clip(base_c * shade, 0, 1)
            quad = [tuple(Lf[i]), tuple(Lf[i + 1]), tuple(Rg[i + 1]), tuple(Rg[i])]
            sh = [(px + 0.7 * SS, py + 1.0 * SS) for px, py in quad]
            ds.polygon(sh, fill=(4, 8, 6, 120 if al > 200 else 60))
            dm.polygon(quad, fill=tuple(int(v * 255) for v in c) + (al,))
            # lado de baixo mais escuro, nervura clara no centro
            q2 = [tuple((Lf[i] + P[i]) / 2 * 0 + P[i] * 0.7 + Rg[i] * 0.3), tuple(P[i + 1] * 0.7 + Rg[i + 1] * 0.3), tuple(Rg[i + 1]), tuple(Rg[i])]
            dm.polygon(q2, fill=tuple(int(v * 255 * 0.72) for v in c) + (al,))
            if wd[i] > 2.2 * SS * 0.5:
                mid = [tuple(P[i] + N[i] * wd[i] * 0.08), tuple(P[i + 1] + N[i + 1] * wd[i + 1] * 0.08),
                       tuple(P[i + 1] - N[i + 1] * wd[i + 1] * 0.08), tuple(P[i] - N[i] * wd[i] * 0.08)]
                hl = np.clip(c * 1.5 + 0.03, 0, 1)
                dm.polygon(mid, fill=tuple(int(v * 255) for v in hl) + (int(al * 0.85),))
            dh.polygon(quad, fill=152)
    for cx, cy in centers:
        cl_base = greens[rng.integers(len(greens))]
        spread = rng.uniform(0.012, 0.04) * ppm
        k = int(rng.integers(5, 20))
        # direção local: ao longo da borda, parcialmente puxada para as frestas úmidas
        xi, yi = int(min(W - 1, cx)), int(min(H - 1, cy))
        tx, ty = -gy[yi, xi], gx[yi, xi]
        if rng.random() < 0.5: tx, ty = -tx, -ty
        pull = rng.uniform(0.0, 0.7)
        dx_, dy_ = tx * (1 - pull) + wx[yi, xi] * pull, ty * (1 - pull) + wy[yi, xi] * pull
        base_ang = math.atan2(dy_, dx_)
        for _ in range(k):
            px = cx + rng.normal(0, spread); py = cy + rng.normal(0, spread)
            ang = base_ang + rng.normal(0, 0.45)
            leaf = rng.random() < 0.3
            length = (0.01 + 0.05 * rng.random() ** 0.8) * ppm * SS
            wmax = (rng.uniform(4, 12) if leaf else rng.uniform(2.5, 7)) / 1000 * ppm * SS
            bc = np.clip(cl_base * rng.uniform(0.8, 1.25) + rng.normal(0, 0.015, 3), 0, 1)
            if sg[int(np.clip(py,0,H-1)), int(np.clip(px,0,W-1))] < -0.003: continue
            ribbon(px * SS, py * SS, ang, length, max(wmax, 1.2), bc, leaf)

    def down(img):
        a = np.asarray(img, np.float32) / 255
        if a.ndim == 2: return a.reshape(H, SS, W, SS).mean((1, 3))
        al = a[..., 3]; pm = a[..., :3] * al[..., None]
        al_d = al.reshape(H, SS, W, SS).mean((1, 3))
        pm_d = pm.reshape(H, SS, W, SS, 3).mean((1, 3))
        return pm_d, al_d      # premultiplicado
    ps, as_ = down(shad); pg, ag = down(gra); pmo, amo = down(mos)
    # composição sobre transparente: lama -> sombras -> cascalho -> musgo
    pre = mud_rgb * mud_a[..., None]; a = mud_a.copy()
    for pc, ac in ((ps, as_), (pg, ag), (pmo, amo)):
        pre = pc + pre * (1 - ac[..., None]); a = ac + a * (1 - ac)
    rgb = np.where(a[..., None] > 1e-4, pre / np.maximum(a[..., None], 1e-4), 0)
    rgba = np.concatenate([np.clip(rgb, 0, 1), a[..., None]], -1).astype(np.float32)
    altura = down(hgt).astype(np.float32)
    altura = np.clip(altura + (n3 - 0.5) * 0.02 * (mud_a > 0.03), 0, 1)
    return dict(rgba=rgba, altura=altura)

if __name__ == "__main__":
    V = sys.argv[1] if len(sys.argv) > 1 else "A"
    L = lib.contexto(V)
    try:
        import mascara; m = mascara.build(L); print("mascara real")
    except Exception as e:
        print("stub:", e); m = _stub_mask(L)
    r = build(L, m)
    rgba = r["rgba"]
    fl = np.array([0.27, 0.31, 0.40], np.float32)
    bg = np.ones((L.H, L.W, 3), np.float32) * fl * (0.9 + 0.2 * lib.fbm(L, 3, 3, 9))[..., None]
    wetm = m["wet"][..., None]; bg = bg * (1 - 0.25 * wetm)
    bg = bg * (1 - m["water"][..., None]) + np.array([0.08, 0.13, 0.2]) * m["water"][..., None]
    out = bg * (1 - rgba[..., 3:]) + rgba[..., :3] * rgba[..., 3:]
    lib.salvar(f"/tmp/poca_bordas_{V}.png", out)
    from PIL import Image
    im = Image.open(f"/tmp/poca_bordas_{V}.png")
    ys, xs = np.nonzero((np.abs(m["signed"]) < 0.02) & (rgba[..., 3] > 0.3))
    cy, cx = (int(ys.mean()), int(xs.mean())) if len(ys) else (L.H // 2, L.W // 2)
    from scipy.ndimage import uniform_filter
    dd = uniform_filter(rgba[..., 3], 150); cy, cx = np.unravel_index(np.argmax(dd), dd.shape)
    x0 = int(np.clip(cx - 200, 0, L.W - 400)); y0 = int(np.clip(cy - 150, 0, L.H - 300))
    im.crop((x0, y0, x0 + 400, y0 + 300)).resize((1200, 900), Image.LANCZOS).save(f"/tmp/poca_bordas_{V}_zoom.png")
    Image.fromarray((np.clip(r["altura"], 0, 1) * 255).astype(np.uint8)).save(f"/tmp/poca_bordas_{V}_h.png")
