"""Máscaras da poça-decal: water (água parada), wet (umidade do piso), signed (distância assinada em m)."""
import numpy as np, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from scipy.ndimage import maximum_filter, gaussian_filter, distance_transform_edt, mean as ndmean


def _rot(L, ang_deg, cx=0.0, cz=0.0):
    a = np.deg2rad(ang_deg); c, s = np.cos(a), np.sin(a)
    x, z = L.X - cx, L.Z - cz
    return x * c + z * s, -x * s + z * c


def _cells(coord, rng, lo, hi, extent):
    """Índice de laje por coordenada, com larguras de laje irregulares; devolve (id, distância à junta mais próxima)."""
    edges = [-extent]
    while edges[-1] < extent:
        edges.append(edges[-1] + rng.uniform(lo, hi))
    edges = np.array(edges, np.float32)
    idx = np.clip(np.searchsorted(edges, coord) - 1, 0, len(edges) - 2)
    dj = np.minimum(coord - edges[idx], edges[idx + 1] - coord)
    return idx, dj


def _slabs(L, ang, lo=0.4, hi=0.75, semente=0, cx=0.0, cz=0.0):
    rng = np.random.default_rng(L.seed * 977 + semente)
    u, v = _rot(L, ang, cx, cz)
    ext = max(L.w, L.h) * 0.9
    iu, du = _cells(u, rng, lo, hi, ext)
    iv, dv = _cells(v, rng, lo, hi, ext)
    sid = iu * 1000 + iv
    return sid, du, dv, u, v


def _joints(L):
    """Duas malhas de juntas (~0° e ~90° com rotação leve em duas regiões); devolve sid, dist à junta e eixo da junta."""
    lo, hi = (0.2, 0.38) if L.nome == "C" else (0.4, 0.7)
    sid, du, dv, _, _ = _slabs(L, 3.0, lo=lo, hi=hi, semente=1)
    return sid, du, dv


def _shape_noise(L, amp, esc=2.2, semente=0):
    n = (lib.fbm(L, esc, 4, semente=semente, persist=0.55) - 0.5) * 2
    n2 = (lib.fbm(L, esc * 5, 3, semente=semente + 5) - 0.5) * 2
    return amp * n + amp * 0.12 * n2


def _field(L):
    """Campo de forma (m, negativo = água) por variante, mais mapa de 'escorre' (0..1) e flag stepped."""
    X, Z = L.X, L.Z
    flow = np.zeros_like(X)
    if L.nome == "A":
        # blob irregular (raio ~0.36 m) com lóbulos largos; a borda é depois quantizada por laje (ver build)
        th = np.arctan2(Z / 0.85, X)
        r = np.hypot(X, Z / 0.85)
        R = 0.355 + 0.045 * np.sin(th * 2 + 2.3) + 0.03 * np.sin(th * 3 + 0.4) + 0.02 * np.sin(th * 5 + 1.7)
        f = (r - R) + _shape_noise(L, 0.07, 1.8, 7)
        flow = np.exp(-(((X - 0.40) / 0.22) ** 2 + ((Z - 0.10) / 0.12) ** 2))
        return f, flow.astype(np.float32), True
    if L.nome == "B":
        r = np.hypot(X / 1.0, Z / 0.42)
        thb = np.arctan2(Z, X)
        body = (r - 0.72 + 0.05 * np.sin(thb * 3 + 0.7) + 0.035 * np.sin(thb * 5 + 2)) * 0.42 + _shape_noise(L, 0.09, 1.9, 1)
        # rabo: capsula afunilada seguindo uma junta horizontal em z = 0.05, para a direita
        zj = 0.06 + 0.02 * np.sin(X * 4 + 1)
        t = np.clip((X - 0.45) / 0.65, 0, 1)
        halfw = (0.07 * (1 - t) ** 0.9 + 0.012) * (0.55 + 0.9 * lib.fbm(L, 7, 3, semente=3))
        tail = np.abs(Z - zj) - halfw
        tail = np.maximum(tail, X - 1.12 + (lib.fbm(L, 5, 2, semente=4) - 0.5) * 0.1)
        tail = np.where(X < 0.3, 9, tail)
        tail = tail - 0.0  # união suave abaixo
        # poças pequenas isoladas ao longo do rabo (junta com depressões)
        k = 0.05; hh = np.clip(0.5 + 0.5 * (tail - body) / k, 0, 1); f = tail * (1 - hh) + body * hh - k * hh * (1 - hh)
        flow = np.clip((X - 0.2) / 0.6, 0, 1) * np.exp(-((Z - 0.06) / 0.28) ** 2)
        return f, flow, False
    # C: poça grande orgânica: contorno curvo com lóbulos e baías (domínio deformado), ilhotas secas irregulares
    wx = (lib.fbm(L, 1.1, 3, semente=61) - 0.5) * 0.55
    wz = (lib.fbm(L, 1.1, 3, semente=62) - 0.5) * 0.55
    Xw, Zw = X + wx, Z + wz
    th = np.arctan2(Zw / 0.74, Xw)
    r = np.hypot(Xw / 1.0, Zw / 0.74)
    R = 1.0 + 0.20 * np.sin(th * 2 + 0.4) + 0.14 * np.sin(th * 3 + 2.0) + 0.07 * np.sin(th * 4 + 4.1) + 0.04 * np.sin(th * 7 + 1.0)
    f = (r - R) * 0.55 + _shape_noise(L, 0.16, 1.3, 2)
    # ilhotas secas pequenas e irregulares (elipses deformadas, rotacionadas)
    for (cx, cz, rx, rz, ang, sd) in ((-0.30, 0.10, 0.10, 0.06, 25, 71), (0.34, -0.17, 0.07, 0.11, -35, 72), (0.06, 0.30, 0.06, 0.04, 70, 73)):
        c, sn = np.cos(np.deg2rad(ang)), np.sin(np.deg2rad(ang))
        dx, dz = X - cx, Z - cz
        u, v = dx * c + dz * sn, -dx * sn + dz * c
        u = u + (lib.fbm(L, 14, 2, semente=sd) - 0.5) * 0.05
        v = v + (lib.fbm(L, 14, 2, semente=sd + 9) - 0.5) * 0.05
        q = np.hypot(u / rx, v / rz) + (lib.fbm(L, 25, 3, semente=sd + 3) - 0.5) * 0.5
        f = np.maximum(f, (1 - q) * 0.8 - 0.02)
    flow = np.clip((lib.fbm(L, 1.2, 2, semente=9) - 0.45) * 4, 0, 1) * np.clip(1 - np.maximum(f, 0) / 0.3, 0, 1)
    return f, flow.astype(np.float32), True


def build(L):
    f, flow, stepped = _field(L)
    sid, du, dv = _joints(L)
    dj = np.minimum(du, dv) + (lib.fbm(L, 20, 2, semente=33) - 0.5) * 0.006
    dj = np.maximum(dj, 0)
    rng = np.random.default_rng(L.seed * 31 + 5)

    if stepped:
        # recortes de laje só em alguns trechos: dentro das zonas "gate" a borda segue lajes (cantos arredondados), fora segue a curva suave
        sid2, _, _, _, _ = _slabs(L, -7.0, lo=0.16 if L.nome != "A" else 0.12, hi=0.55 if L.nome != "A" else 0.32, semente=5)
        ids, inv = np.unique(sid2, return_inverse=True)
        inv = inv.reshape(sid2.shape)
        fm = np.asarray(ndmean(f, labels=inv, index=np.arange(len(ids))), np.float32)
        off = rng.normal(0, 0.05 if L.nome != "A" else 0.035, len(ids)).astype(np.float32)
        fq = (fm + off)[inv]
        # cantos arredondados de 1-3 cm: suaviza o campo por laje antes do limiar
        fq = gaussian_filter(fq, (0.012 + 0.012 * 0.5) * L.PPM)
        zona = lib.fbm(L, 2.3, 3, semente=81)
        gate = lib.suave(np.clip((zona - (0.47 if L.nome != "A" else 0.44)) * 12, 0, 1), 0.02)
        g = (1 - gate) * f + gate * ((0.75 if L.nome != "A" else 0.8) * fq + (0.25 if L.nome != "A" else 0.2) * f)
        # algumas frestas deixam a água escorrer um pouco, só em poucos trechos
        fing = np.clip(1 - dj / (0.006 + 0.006 * lib.fbm(L, 16, 2, semente=41)), 0, 1)
        g = g - 0.05 * fing * np.clip((lib.fbm(L, 3.0, 3, semente=42) - 0.5) * 5, 0, 1) * (np.abs(f) < 0.12)
        g = g + (lib.fbm(L, 9, 3, semente=43) - 0.5) * 0.03 * (np.abs(g) < 0.1)
    else:
        g = f
        # junta recebe água primeiro (canal) e laje levemente abaixo: junta puxa a borda
        g = g - 0.010 * np.exp(-(dj / 0.012) ** 2) * (g < 0.1)
    # irregularidade fina da borda (sub-centímetro a poucos cm)
    g = g + (lib.fbm(L, 14, 3, semente=11) - 0.5) * (0.006 if stepped else 0.010)

    if L.nome == "A":
        # lingueta: fita fina que escorre por uma junta horizontal, para a direita
        rowz = np.argmin(dv[:, int(L.W * 0.5)] + np.abs(L.Z[:, 0] - 0.13) * 0.6)  # junta horizontal perto de z=0.05
        zj = L.Z[rowz, 0]
        t = np.clip((L.X - 0.20) / 0.38, 0, 1)
        hw = (0.034 * (1 - t) ** 1.6 + 0.004) * (0.7 + 0.6 * lib.fbm(L, 9, 2, semente=6))
        tg = np.maximum(np.abs(L.Z - zj) - hw, L.X - 0.575 + (lib.fbm(L, 6, 2, semente=8) - 0.5) * 0.04)
        tg = np.where(L.X < 0.0, 9, tg)
        g = np.minimum(g, tg)
    mask = g < 0
    if stepped:  # arredonda cantos e tira espinhos finos (1-2 cm)
        mask = gaussian_filter(mask.astype(np.float32), 0.011 * L.PPM) > 0.5
    # remove pontinhos minúsculos (< 6 cm²)
    from scipy.ndimage import label, binary_closing
    lab, n = label(mask)
    if n:
        sz = np.bincount(lab.ravel()); sz[0] = 0
        keep = sz > (0.012 * L.PPM) ** 2
        mask = keep[lab]
    signed = lib.dist_m(mask.astype(np.float32)).astype(np.float32)
    # refinamento subpixel pelo campo para borda antialiased
    water = np.clip(0.5 - signed * L.PPM, 0, 1).astype(np.float32)
    water = gaussian_filter(water, 0.55)
    water = np.clip((water - 0.5) * 1.35 + 0.5, 0, 1).astype(np.float32)

    # ----- umidade: halo largo e difuso (10-35 cm), segue juntas em trechos, ~0.9 junto da agua -----
    d = np.maximum(signed, 0)
    wn = lib.fbm(L, 1.6, 3, semente=13)
    wn = np.clip((wn - 0.25) * 1.9, 0, 1)
    wid = 0.10 + 0.25 * wn                                                # 10..35 cm, varia ao longo da borda
    wid = wid * (0.85 + 0.3 * lib.fbm(L, 5, 2, semente=14)) + 0.08 * flow  # mais largo onde escorre
    if L.nome == "B":
        gb = lib.fbm(L, 2.2, 3, semente=51)
        wid = wid * (0.7 + 0.6 * np.clip((gb - 0.3) * 2.0, 0, 1))
    wid = np.clip(wid, 0.10, 0.40)
    # juntas puxam a umidade para longe em alguns trechos (distancia efetiva menor perto da junta)
    jg = np.clip((lib.fbm(L, 3.0, 3, semente=21) - 0.38) * 4, 0, 1)
    jb = np.exp(-(dj / 0.025) ** 2)
    d_eff = d * (1 - 0.55 * jg * jb)
    t = np.clip(d_eff / wid, 0, 1)
    wet_a = 0.9 * (1 - (3 * t ** 2 - 2 * t ** 3)) ** 1.15                  # curva suave, sem degrau
    wet_a = wet_a * (0.88 + 0.24 * lib.fbm(L, 6, 3, semente=15))           # manchas suaves
    wet_a = gaussian_filter(wet_a, 0.012 * L.PPM)
    # a umidade some antes da borda da decal
    ed = np.minimum(np.minimum(L.X + L.w / 2, L.w / 2 - L.X), np.minimum(L.Z + L.h / 2, L.h / 2 - L.Z))
    q = np.clip(ed / 0.07, 0, 1)
    wet_a = wet_a * q * q * (3 - 2 * q)
    # filetes nas juntas: umidade entra nas frestas, com comprimento variável (até 30-60 cm)
    jw = 0.007 + 0.010 * lib.fbm(L, 14, 2, semente=16)                  # meia-largura 0.7..1.7 cm => 1.4..3.4 cm
    band = np.clip(1 - (dj / jw) ** 2, 0, 1) ** 0.8
    reach = 0.15 + 0.55 * lib.fbm(L, 2.5, 3, semente=17) ** 1.4 + 0.15 * flow
    # só em algumas juntas/trechos: máscara de trechos por ruído de baixa freq
    gate = np.clip((lib.fbm(L, 3.5, 3, semente=18) - 0.34) * 5, 0, 1)
    along = np.clip(1 - d / reach, 0, 1) ** 1.4
    # o rastro é contínuo a partir da água: só vale perto de água (dentro do alcance)
    wet_j = (0.5 if L.nome == 'C' else 1.0) * band * along * gate * (0.55 + 0.45 * lib.fbm(L, 30, 2, semente=19))
    # umidade espalha um pouco a partir do filete
    wet_j = np.maximum(wet_j, gaussian_filter(wet_j, 0.004 * L.PPM) * 0.7)
    wet = np.maximum(wet_a, wet_j)
    wet = np.clip(np.maximum(wet, water), 0, 1).astype(np.float32)
    return dict(wet=wet, water=water, signed=signed)


if __name__ == "__main__":
    from PIL import Image
    for V in ("A", "B", "C"):
        t0 = time.time()
        L = lib.contexto(V); m = build(L); dt = time.time() - t0
        wet, wa = m["wet"], m["water"]
        grey = np.stack([wet * 0.75] * 3, -1)
        blue = np.array([0.12, 0.35, 0.95])
        img = grey * (1 - wa[..., None]) + blue * wa[..., None]
        Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(f"/tmp/poca_mascara_{V}.png")
        print(V, L.W, L.H, f"{dt:.2f}s", "wet>=water:", bool((wet >= wa - 1e-6).all()), "agua m2: %.2f" % (wa.sum() / L.PPM ** 2))
