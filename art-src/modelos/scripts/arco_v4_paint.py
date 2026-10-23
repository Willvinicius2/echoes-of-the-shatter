"""Arco v4, etapa 3 (venv, CPU): reprojeta a imagem de entrada (afiada, 2048) pela posicao 3D de cada texel (mesma projecao
frente/costas da silhueta), reforca couro escuro, metal e acentos rosa, soma cavidade (do normal map) e gera
T_ArcherDark_Bow_BC.png (2048), T_ArcherDark_Bow_N.png (normal) e T_ArcherDark_Bow_MR.png (glTF: G=rugosidade, B=metal, 1024).
Uso: python arco_v4_paint.py"""
import os, json, numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
ARCO = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\arco"; W2 = os.path.join(ARCO, "work4")
T = 2048
g = np.load(os.path.join(W2, "low_uv.npz")); P, N, tri, lv, UV = g["P"], g["N"], g["tri"], g["lv"], g["UV"]
par = json.load(open(os.path.join(W2, "geo_report.json")))["par"]; sx, sz, tx, tz = par
# --- rasteriza UV -> posicao/normal por texel
pos = np.zeros((T, T, 3)); nor = np.zeros((T, T, 3)); cov = np.zeros((T, T), bool)
for t in tri:
    uv = UV[t] * T; uv[:, 1] = T - uv[:, 1]                      # v de baixo para cima -> linhas
    x0, x1 = int(max(np.floor(uv[:, 0].min()), 0)), int(min(np.ceil(uv[:, 0].max()), T - 1))
    y0, y1 = int(max(np.floor(uv[:, 1].min()), 0)), int(min(np.ceil(uv[:, 1].max()), T - 1))
    den = (uv[1, 1] - uv[2, 1]) * (uv[0, 0] - uv[2, 0]) + (uv[2, 0] - uv[1, 0]) * (uv[0, 1] - uv[2, 1])
    if abs(den) < 1e-9: continue
    X, Y = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
    w0 = ((uv[1, 1] - uv[2, 1]) * (X - uv[2, 0]) + (uv[2, 0] - uv[1, 0]) * (Y - uv[2, 1])) / den
    w1 = ((uv[2, 1] - uv[0, 1]) * (X - uv[2, 0]) + (uv[0, 0] - uv[2, 0]) * (Y - uv[2, 1])) / den
    w2 = 1 - w0 - w1; ins = (w0 >= -.02) & (w1 >= -.02) & (w2 >= -.02)
    p3 = P[lv[t]]; n3 = N[t]
    pp = w0[..., None] * p3[0] + w1[..., None] * p3[1] + w2[..., None] * p3[2]
    nn = w0[..., None] * n3[0] + w1[..., None] * n3[1] + w2[..., None] * n3[2]
    sl = (slice(y0, y1 + 1), slice(x0, x1 + 1))
    pos[sl][ins] = pp[ins]; nor[sl][ins] = nn[ins]; cov[sl] |= ins
nor /= np.maximum(np.linalg.norm(nor, axis=-1, keepdims=True), 1e-9)
print("cobertura %", round(100 * cov.mean(), 1))
# --- imagem de entrada afiada (2x) com preenchimento para fora da silhueta
src = np.array(Image.open(os.path.join(ARCO, "arco_entrada_rgba.png"))).astype(np.float32)
rgb, al = src[..., :3] / 255, src[..., 3] > 128
inner = ndi.binary_erosion(al, iterations=2)
_, idx = ndi.distance_transform_edt(~inner, return_indices=True)
rgb = rgb[idx[0], idx[1]]
S = 2; big = cv2.resize(rgb, None, fx=S, fy=S, interpolation=cv2.INTER_LANCZOS4)
bl = cv2.GaussianBlur(big, (0, 0), 1.6); big = np.clip(big + 1.1 * (big - bl), 0, 1)
bl = cv2.GaussianBlur(big, (0, 0), 6); big = np.clip(big + 0.35 * (big - bl), 0, 1)   # contraste local
Hh, Ww = big.shape[:2]
uu = (tx + pos[..., 0] * sx) * S; vv = (tz - pos[..., 2] * sz) * S
col = np.stack([cv2.remap(big[..., c], uu.astype(np.float32), vv.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) for c in range(3)], -1)
# --- grade: couro escuro, metal brilhante, rosa vivo
hsv = cv2.cvtColor(col.astype(np.float32), cv2.COLOR_RGB2HSV)       # H 0-360
h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
pink = ((h > 318) | (h < 20)) & (s > 0.28) & (v > 0.32)
pinkm = cv2.GaussianBlur(pink.astype(np.float32), (0, 0), 1.0)
luma = col @ np.array([.299, .587, .114], np.float32)
metal = np.clip((luma - 0.30) / 0.14, 0, 1) * (1 - pinkm) * (s < 0.55)
metal = cv2.GaussianBlur(metal.astype(np.float32), (0, 0), 1.2)
leather = (1 - metal) * (1 - pinkm)
v2 = v.copy()
v2 = np.where(leather > .5, np.clip((v ** 1.35) * 0.88, 0, 1), v2)                      # couro mais escuro e contrastado
v2 = v2 * (1 - metal) + metal * np.clip(0.12 + (v ** 0.72) * 1.18, 0, 1)                # metal claro
v2 = v2 * (1 - pinkm) + pinkm * np.clip(v * 1.25 + 0.08, 0, 1)
s2 = s * (1 - metal) * (1 - pinkm) * 1.1 + metal * np.clip(s * 0.85, 0, 1) + pinkm * np.clip(s * 1.45, 0, 1)
h2 = h.copy(); h2 = np.where(pinkm > .3, np.where(h > 180, np.minimum(h, 345) , h), h2)
col2 = cv2.cvtColor(np.stack([h2, np.clip(s2, 0, 1), np.clip(v2, 0, 1)], -1).astype(np.float32), cv2.COLOR_HSV2RGB)
# --- cavidade a partir do normal map
nm = np.array(Image.open(os.path.join(W2, "bake_normal.png")).convert("RGB")).astype(np.float32) / 255 * 2 - 1
nx, ny = cv2.GaussianBlur(nm[..., 0], (0, 0), 1.0), cv2.GaussianBlur(nm[..., 1], (0, 0), 1.0)
div = cv2.Sobel(nx, cv2.CV_32F, 1, 0, ksize=3) + cv2.Sobel(ny, cv2.CV_32F, 0, 1, ksize=3)
cav = np.clip(cv2.GaussianBlur(div, (0, 0), 1.0) * 1.6, -1, 1)
col2 = col2 * (1 - 0.30 * np.clip(-cav, 0, 1))[..., None]                 # cavidade escurece
col2 = col2 + (0.10 * np.clip(cav, 0, 1) * metal)[..., None]              # quina polida do metal
# luz de cima suave pelo eixo Z da normal (arte pintada a mao)
col2 = col2 * (0.86 + 0.14 * np.clip(nor[..., 2] * .5 + .5, 0, 1))[..., None]
col2 = np.clip(col2, 0, 1)
# --- preenche fora das ilhas (padding)
_, ii = ndi.distance_transform_edt(~cov, return_indices=True)
col2 = col2[ii[0], ii[1]]; 

# --- v3: faixa das duas laminas (v>0.87): u = comprimento (0..0.5 ponta de cima, 0.5..1 de baixo), v = em volta da secao (losango)
V0, V1 = 0.88, 0.995
rows = np.arange(T)[:, None]; cols = np.arange(T)[None, :]
vv_ = 1 - (rows + .5) / T; uu_ = (cols + .5) / T
SM = (vv_ > 0.865) & np.ones((1, T), bool)
tl = np.clip(((uu_ % 0.5) - 0.015) / 0.485, 0, 1) * np.ones((T, 1)); psi = np.clip((vv_ - V0) / (V1 - V0), 0, 1) * 2 * np.pi * np.ones((1, T))
ref = metal > 0.6
hm = col2[ref]                                                       # cores reais do metal da haste (bronze/osso)
base = hm.mean(0) if ref.any() else np.array([.62, .50, .40]); sd = hm.std(0) if ref.any() else np.array([.05, .05, .05])
print("metal base (haste)", base.round(3), "sd", sd.round(3))
cs = np.abs(np.cos(psi))
edge = np.clip((cs - 0.8) / 0.2, 0, 1)                                                      # perto das arestas vivas (so escurece/desgasta)
ridge = np.clip(1 - np.abs(np.abs(np.sin(psi)) - 1) / 0.14, 0, 1)                            # nervura central
rng = np.random.RandomState(3)
def noise(sig, sy=None):
    n_ = cv2.GaussianBlur(rng.rand(T, T).astype(np.float32), (0, 0), sigmaX=sig, sigmaY=sy or sig); return (n_ - n_.mean()) / (n_.std() + 1e-6)
streak = noise(40, 1.2)                                                                      # riscos ao longo da lamina
patch = noise(10); fine = noise(2.0)
fuller = np.clip(1 - np.abs(np.abs(np.sin(psi)) - 0.55) / 0.07, 0, 1)                      # friso gravado suave
shade = 0.80 + 0.20 * tl ** 0.7                                                          # raiz um pouco mais escura (sujeira)
k = shade * (1 + 0.06 * patch + 0.05 * fine + 0.04 * streak - 0.12 * fuller * (tl > 0.12) - 0.10 * edge + 0.06 * ridge)
tint = 1 + 0.10 * patch[..., None] * np.array([1.0, 0.8, 0.6])[None, None, :]              # variacao de tom osso/bronze como a haste
grime = np.clip(noise(6) - 0.6, 0, 1) * np.clip((0.5 - tl) / 0.5, 0, 1) * 0.35               # manchas escuras de uso, sem furos
sc = base[None, None, :] * np.array([0.87, 0.82, 0.76])[None, None, :] * k[..., None] * tint * (1 - grime[..., None])
sc = np.clip(sc, 0, 1)
m_ = SM[..., None]
col2 = np.where(m_, sc, col2)
Image.fromarray((col2 * 255 + .5).astype(np.uint8)).save(os.path.join(W2, "T_ArcherDark_Bow_BC.png"))
rough = 0.82 * leather + 0.32 * metal + 0.5 * pinkm
rough = np.clip(rough + 0.12 * np.clip(-cav, 0, 1), 0, 1)
mr = np.zeros((T, T, 3), np.float32); mr[..., 0] = 1; mr[..., 1] = rough; mr[..., 2] = np.clip(metal * 0.85, 0, 1)
mr = mr[ii[0], ii[1]]
mr[SM] = np.stack([np.ones(SM.sum()), np.clip(0.38 + 0.05 * streak[SM] + 0.04 * patch[SM] + 0.10 * grime[SM] - 0.04 * ridge[SM], .2, .7), np.clip(0.70 - 0.25 * grime[SM], 0, 1)], -1)
Image.fromarray((mr * 255 + .5).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS).save(os.path.join(W2, "T_ArcherDark_Bow_MR.png"))
nimg = np.array(Image.open(os.path.join(W2, "bake_normal.png")).convert("RGB")).astype(np.float32)
hgt = 0.9 * ridge + 0.35 * np.abs(np.sin(psi)) ** 3 - 0.8 * fuller * (tl > 0.12) + 0.05 * streak + 0.10 * patch   # relevo sutil (nervuras, friso, desgaste)
hgt = cv2.GaussianBlur(hgt.astype(np.float32), (0, 0), 2.0)
gx_ = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3) / 8; gy_ = -cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3) / 8    # v para cima
nv = np.stack([-gx_ * 2.0, -gy_ * 2.0, np.ones_like(gx_)], -1); nv /= np.linalg.norm(nv, axis=-1, keepdims=True)
nimg[SM] = ((nv * 0.5 + 0.5) * 255)[SM]
Image.fromarray(np.clip(nimg + 0.5, 0, 255).astype(np.uint8)).save(os.path.join(W2, "T_ArcherDark_Bow_N.png"))
print("ok")
