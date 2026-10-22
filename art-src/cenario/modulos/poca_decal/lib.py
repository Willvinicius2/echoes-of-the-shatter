"""Contrato da poça-decal da Cripta (compartilhado pelas partes). A poça NÃO é malha elevada: é uma região do próprio piso,
pintada em texturas de Decal do Godot (albedo RGBA, ORM, normal), mais um quad animado de gotas.
Medidas em metros; textura com PPM pixels por metro; x da imagem = +X, y da imagem = +Z do mundo (linha 0 no topo = -Z).
Todas as partes usam os mesmos arrays HxW float32 e a mesma L."""
import numpy as np, os, math
from types import SimpleNamespace

PPM = 480                                   # pixels por metro (texel density uniforme nas 3 variantes)
VARIANTES = {                               # nome: (largura m, altura m, semente, descrição)
    "A": (1.2, 0.95, 11, "pequena: um recorte só, quase redonda"),
    "B": (2.3, 1.05, 23, "média alongada, com rabo que escorre em uma junta"),
    "C": (3.5, 2.6, 37, "grande, bordas recortadas em degraus de laje"),
}
SAIDA_TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "godot", "art", "textures")

def contexto(nome):
    w, h, seed, desc = VARIANTES[nome]
    W, H = int(round(w * PPM)), int(round(h * PPM))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    X = (xx + 0.5) / PPM - w / 2             # metros, centro da decal = 0
    Z = (yy + 0.5) / PPM - h / 2
    return SimpleNamespace(nome=nome, w=w, h=h, W=W, H=H, seed=seed, rng=np.random.default_rng(seed), X=X, Z=Z, PPM=PPM)

def fbm(L, escala, oitavas=4, semente=0, persist=0.5):
    """Ruído fractal suave 0..1 em coordenadas de metros (valor interpolado, sem dependências além do numpy)."""
    rng = np.random.default_rng(L.seed * 131 + semente); out = np.zeros((L.H, L.W), np.float32); amp, tot = 1.0, 0.0
    for o in range(oitavas):
        gx, gy = max(2, int(L.w * escala * 2 ** o) + 2), max(2, int(L.h * escala * 2 ** o) + 2)
        g = rng.random((gy, gx)).astype(np.float32)
        u = (L.X + L.w / 2) / L.w * (gx - 1); v = (L.Z + L.h / 2) / L.h * (gy - 1)
        i0, j0 = np.clip(u.astype(int), 0, gx - 2), np.clip(v.astype(int), 0, gy - 2); fu, fv = u - i0, v - j0
        fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
        val = (g[j0, i0] * (1 - fu) + g[j0, i0 + 1] * fu) * (1 - fv) + (g[j0 + 1, i0] * (1 - fu) + g[j0 + 1, i0 + 1] * fu) * fv
        out += amp * val; tot += amp; amp *= persist
    return out / tot

def suave(a, sigma_m):
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, sigma_m * PPM)

def dist_m(mask):
    """Distância (m) de cada pixel fora da máscara até a máscara (0 dentro) e dentro até o fora (negativa dentro = use signed)."""
    from scipy.ndimage import distance_transform_edt
    m = mask > 0.5
    return (distance_transform_edt(~m) - distance_transform_edt(m)) / PPM   # >0 fora, <0 dentro

def salvar(path, arr):
    from PIL import Image
    a = np.clip(arr, 0, 1); a = (a * 255 + 0.5).astype(np.uint8); Image.fromarray(a).save(path)
