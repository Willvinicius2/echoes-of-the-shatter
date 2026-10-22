"""Gotas da poça: altura (m) da superfície da água = ondulação fina anisotrópica + 1-3 gotas com 2-3 anéis discretos.
O shader animado correspondente está em godot/art/shaders/cripta_gotas.gdshader (material M_Cripta_Gotas.tres)."""
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
import lib


def _ondulacao(L):
    """Ruído de valor esticado numa direção (anisotrópico), rotacionado por poça; ~0.15 mm."""
    rng = np.random.default_rng(L.seed * 977 + 5)
    ang = rng.uniform(0, np.pi)
    c, s = np.cos(ang), np.sin(ang)
    u = (L.X * c + L.Z * s); v = (-L.X * s + L.Z * c)
    out = np.zeros((L.H, L.W), np.float32)
    amp = 1.0
    for esc_u, esc_v in ((14, 3.5), (30, 8), (62, 17)):    # ciclos por metro ao longo / através
        n = 48
        g = rng.standard_normal((n, n)).astype(np.float32)
        gu = (u * esc_u + 200) % (n - 3) + 1; gv = (v * esc_v + 200) % (n - 3) + 1
        val = map_coordinates(g, [gv.ravel(), gu.ravel()], order=3, mode="wrap").reshape(L.H, L.W)
        out += amp * val; amp *= 0.55
    out /= np.abs(out).max() + 1e-6
    return out * 0.00018


def _gotas(L, m):
    rng = np.random.default_rng(L.seed * 313 + 9)
    interior = m["signed"] < -0.12
    ys, xs = np.nonzero(interior)
    h = np.zeros((L.H, L.W), np.float32)
    if len(xs) == 0:
        return h
    n = int(rng.integers(1, 4)) if L.nome != "A" else int(rng.integers(1, 3))
    for _ in range(n):
        k = int(rng.integers(len(xs)))
        cx, cz = L.X[ys[k], xs[k]], L.Z[ys[k], xs[k]]
        r0 = rng.uniform(0.035, 0.085)                 # raio do primeiro anel
        gap = rng.uniform(0.016, 0.026)
        nr = int(rng.integers(2, 4))
        # leve achatamento elíptico para não ser círculo perfeito
        ex = rng.uniform(0.9, 1.1); ang = rng.uniform(0, np.pi)
        dx, dz = L.X - cx, L.Z - cz
        a = dx * np.cos(ang) + dz * np.sin(ang); b = (-dx * np.sin(ang) + dz * np.cos(ang)) * ex
        r = np.sqrt(a * a + b * b)
        t_ = np.arctan2(b, a); r = r * (1 + 0.06 * np.sin(2 * t_ + rng.uniform(0, 6)) + 0.02 * np.sin(3 * t_ + rng.uniform(0, 6)))
        for j in range(nr):
            rj = r0 - j * gap
            if rj <= 0.008:
                continue
            w = 0.005 + 0.001 * j
            fase = (r - rj) / w
            h += (0.00022 * (0.6 ** j)) * (fase * np.exp(-fase * fase / 1.2)).astype(np.float32)
    return h


def build(L, m):
    w = np.clip(m["water"], 0, 1)
    h = (_ondulacao(L) + _gotas(L, m)) * w
    # sem degrau na borda: some nos últimos centímetros
    borda = np.clip(-m["signed"] / 0.04, 0, 1)
    return dict(altura=(h * borda * w).astype(np.float32))


def _stub(L):
    ang = np.arctan2(L.Z, L.X)
    rad = 0.36 * (1 + 0.15 * np.sin(3 * ang + 1) + 0.08 * np.sin(5 * ang)) * np.array([L.w, L.h]).min() / 0.95 / 0.8
    sd = np.sqrt((L.X / 1.2) ** 2 + (L.Z / 0.9) ** 2) * 0.9 - rad * 0.9
    sd = sd.astype(np.float32)
    return dict(water=np.clip(0.5 - sd * lib.PPM, 0, 1).astype(np.float32), wet=None, signed=sd)


if __name__ == "__main__":
    import sys
    from PIL import Image
    try:
        import mascara
        real = True
    except Exception:
        real = False
    for V in "ABC":
        L = lib.contexto(V)
        m = mascara.build(L) if real else _stub(L)
        h = build(L, m)["altura"]
        gy, gx = np.gradient(h, 1 / lib.PPM)
        luz = np.array([-0.5, -0.6, 0.62])
        nz = 1 / np.sqrt(1 + (gx * 25) ** 2 + (gy * 25) ** 2)
        sh = np.clip((-gx * 25 * nz * luz[0] - gy * 25 * nz * luz[1] + nz * luz[2]), 0, 1)
        img = 0.08 + 0.85 * sh * m["water"]
        Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(f"/tmp/poca_gotas_{V}.png")
        print(V, "real" if real else "stub", float(np.abs(h).max()) * 1000, "mm")
