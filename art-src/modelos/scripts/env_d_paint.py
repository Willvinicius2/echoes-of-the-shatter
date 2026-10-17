"""Etapa d (Python do venv com numpy, scipy, cv2, pymeshlab): pintura projetada da folha no albedo 512 e mascara 256.

A imagem de entrada (recorte da folha aprovada) e a vista de -Y no quadro `src` da malha. Alinha o alfa limpo (sem os
fios das fatias vizinhas) a silhueta da malha: caixa e depois afim por ECC. Cada texel recebe a cor da vista da frente
(peso cos^1,5, z-buffer) e, nas faces de tras, a imagem espelhada (peso menor); o que nenhuma vista alcanca (laterais,
topo, fundo) recebe a MEDIANA das cores pintadas mais proximas no espaco 3D. Soma AO (malha alta decimada), luz do
alto-esquerda e sombra violeta, sem preto puro. Mascara (docs/04 3.5): R emissao (so fogo), G rim, B tinta (so pano).
Grava OUT/T_Cripta_<Peca>_BC.png, OUT/T_Cripta_<Peca>_M.png e work/align.png.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2, pymeshlab
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from env_common import *

c = load_cfg()
TS, MS_ = c["tex"], c["mask_tex"]
nm = load_json(wpath(c, "norm.json"))
A = np.array(nm["A"]); t = np.array(nm["t"]); Ai = np.linalg.inv(A)
geo = np.load(wpath(c, "geo.npz"))
valid = geo["valid"]; POSF = geo["pos"].astype(np.float64); NRMF = geo["nrm"].astype(np.float64)
POS = (POSF - t) @ Ai.T                                        # quadro src
NRM = NRMF @ A                                                  # n_src ~ A^T n_final
NRM /= np.maximum(np.linalg.norm(NRM, axis=-1, keepdims=True), 1e-9)
ms = pymeshlab.MeshSet(); ms.load_new_mesh(wpath(c, "game_src.ply"))
V = ms.current_mesh().vertex_matrix().astype(np.float64); F = ms.current_mesh().face_matrix()
lo, hi = V.min(0), V.max(0)

# imagem de entrada: alfa limpo (abertura tira fios finos), figura = maior componente apos a abertura
im = cv2.imread(c["entrada"], cv2.IMREAD_UNCHANGED)
rgb = cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32) / 255
al = (im[..., 3] > 128).astype(np.uint8)
al = cv2.morphologyEx(al, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
nlab, lab, stats, _ = cv2.connectedComponentsWithStats(al)
if nlab > 1:
    keep = [i for i in range(1, nlab) if stats[i, cv2.CC_STAT_AREA] > 0.04 * stats[1:, cv2.CC_STAT_AREA].max()]
    al = np.isin(lab, keep).astype(np.uint8)
ys, xs = np.where(al > 0)
fx0, fx1, fy0, fy1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
H_, W_ = al.shape

# mapa caixa -> imagem; refino afim por ECC das silhuetas
def to_img(P):
    u = fx0 + (P[..., 0] - lo[0]) / (hi[0] - lo[0]) * (fx1 - fx0)
    v = fy0 + (hi[2] - P[..., 2]) / (hi[2] - lo[2]) * (fy1 - fy0)
    return u, v
sil = np.zeros((H_, W_), np.uint8)
uu, vv = to_img(V)
for f in F:
    cv2.fillConvexPoly(sil, np.round(np.stack([uu[f], vv[f]], 1) * 16).astype(np.int32), 255, cv2.LINE_8, 4)
W = np.eye(2, 3, dtype=np.float32)
try:
    tmpl = cv2.GaussianBlur(sil.astype(np.float32) / 255, (0, 0), 2.0)
    inp = cv2.GaussianBlur(al.astype(np.float32), (0, 0), 2.0)
    cc, W = cv2.findTransformECC(tmpl, inp, W, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    d = np.abs(W - np.eye(2, 3)); ok = d[:, :2].max() < 0.25 and d[:, 2].max() < 0.12 * max(W_, H_)
    if not ok: W = np.eye(2, 3, dtype=np.float32)
    print("ECC", round(float(cc), 3), "aceito" if ok else "rejeitado", np.round(W, 3).tolist())
except cv2.error as e:
    print("ECC falhou", str(e)[:60])
def to_img2(P):
    u, v = to_img(P)
    return W[0, 0] * u + W[0, 1] * v + W[0, 2], W[1, 0] * u + W[1, 1] * v + W[1, 2]
dbg = (rgb * 255).astype(np.uint8)[..., ::-1].copy()
sil2 = np.zeros((H_, W_), np.uint8); u2, v2 = to_img2(V)
for f in F:
    cv2.fillConvexPoly(sil2, np.round(np.stack([u2[f], v2[f]], 1) * 16).astype(np.int32), 255, cv2.LINE_8, 4)
cnt, _ = cv2.findContours(sil2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(dbg, cnt, -1, (0, 255, 255), 1)
cv2.imwrite(wpath(c, "align.png"), dbg)
print("silhueta malha/alfa", round(float((sil2 > 0).sum() / max(al.sum(), 1)), 2))

# mapas de caracteristicas na imagem (fogo, ouro, pano)
hsv = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
hh, ss, vvv = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
fire = ((hh > 8) & (hh < 58) & (ss > .5) & (vvv > .88)).astype(np.float32) if c.get("emission") else np.zeros_like(ss)
if c.get("emission") == "fire" and c["id"] == "braseiro":
    rows = np.arange(H_)[:, None] < fy0 + 0.55 * (fy1 - fy0)
    fire *= rows
gold = ((hh > 33) & (hh < 56) & (ss > .45) & (vvv > .45)).astype(np.float32)
cloth = (((hh < 14) | (hh > 340)) & (ss > .45) & (vvv > .2)).astype(np.float32) if c.get("tint") else np.zeros_like(ss)
feat = np.stack([cv2.GaussianBlur(fire, (0, 0), 1.2), cv2.GaussianBlur(gold, (0, 0), 1.0), cv2.GaussianBlur(cloth, (0, 0), 1.2)], -1)
good = cv2.erode(al, np.ones((5, 5), np.uint8)).astype(np.float32)           # amostras longe da borda/fundo da folha

# z-buffer (grade de 512 sobre a caixa x,z; profundidade = +-y)
VG = 512
def zbuffer(sign):
    gx = (V[:, 0] - lo[0]) / (hi[0] - lo[0]) * (VG - 1); gz = (hi[2] - V[:, 2]) / (hi[2] - lo[2]) * (VG - 1); d = sign * V[:, 1]
    z = np.full((VG, VG), np.inf)
    for a, b, cc_ in F:
        pu, pv, pd = gx[[a, b, cc_]], gz[[a, b, cc_]], d[[a, b, cc_]]
        x0, x1 = int(max(np.floor(pu.min()), 0)), int(min(np.ceil(pu.max()), VG - 1)); y0, y1 = int(max(np.floor(pv.min()), 0)), int(min(np.ceil(pv.max()), VG - 1))
        den = (pv[1] - pv[2]) * (pu[0] - pu[2]) + (pu[2] - pu[1]) * (pv[0] - pv[2])
        if x1 < x0 or y1 < y0 or abs(den) < 1e-12: continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        w0 = ((pv[1] - pv[2]) * (X - pu[2]) + (pu[2] - pu[1]) * (Y - pv[2])) / den
        w1 = ((pv[2] - pv[0]) * (X - pu[2]) + (pu[0] - pu[2]) * (Y - pv[2])) / den
        w2 = 1 - w0 - w1
        ins = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        dd = w0 * pd[0] + w1 * pd[1] + w2 * pd[2]
        sub = z[y0:y1 + 1, x0:x1 + 1]; upd = ins & (dd < sub); sub[upd] = dd[upd]
    return ndi.minimum_filter(z, 3) if False else ndi.maximum_filter(np.where(np.isinf(z), 1e9, z), 3)

ext = float((hi - lo).max()); tol = 0.03 * ext
acc = np.zeros(valid.shape + (6,)); wsum = np.zeros(valid.shape)
ix = np.clip(np.round((POS[..., 0] - lo[0]) / (hi[0] - lo[0]) * (VG - 1)).astype(int), 0, VG - 1)
iz = np.clip(np.round((hi[2] - POS[..., 2]) / (hi[2] - lo[2]) * (VG - 1)).astype(int), 0, VG - 1)
src_img = np.concatenate([rgb, feat], -1).astype(np.float32)
def img_uv(Pq, mode):
    """Coordenadas da imagem de cada ponto src para a vista virtual. F/B: frente e costas (espelho). S+/S-: lados, a imagem
    da frente girada 90 graus (a profundidade vira largura: mantem as faixas de altura e o grao). T: topo, a faixa alta
    da imagem (nos 3/4 da folha e onde o topo aparece)."""
    x, y, z = Pq[..., 0], Pq[..., 1], Pq[..., 2]
    xr = (x - lo[0]) / (hi[0] - lo[0]); yr = (y - lo[1]) / max(hi[1] - lo[1], 1e-9); zr = (hi[2] - z) / (hi[2] - lo[2])
    if mode == "F": a_, b_ = xr, zr
    elif mode == "B": a_, b_ = 1 - xr, zr
    elif mode == "S+": a_, b_ = yr, zr
    elif mode == "S-": a_, b_ = 1 - yr, zr
    else:
        tb = c.get("top_band", (0.02, 0.18)); a_, b_ = xr, tb[0] + (tb[1] - tb[0]) * (1 - yr)
    u, v = fx0 + a_ * (fx1 - fx0), fy0 + b_ * (fy1 - fy0)
    return (W[0, 0] * u + W[0, 1] * v + W[0, 2]).astype(np.float32), (W[1, 0] * u + W[1, 1] * v + W[1, 2]).astype(np.float32)

for mode, sign, wmul in (("F", 1, 1.0), ("B", -1, 0.55), ("S+", 0, 0.5), ("S-", 0, 0.5), ("T", 0, 0.6)):
    if sign:
        zb = zbuffer(sign)
        vis = (sign * POS[..., 1]) <= zb[iz, ix] + tol
        cosv = np.clip(-sign * NRM[..., 1], 0, 1)
    else:
        vis = np.ones(valid.shape, bool)
        cosv = np.clip({"S+": NRM[..., 0], "S-": -NRM[..., 0], "T": NRM[..., 2]}[mode], 0, 1)
    mu_, mv_ = img_uv(POS, mode)
    smp = np.concatenate([cv2.remap(src_img[..., :3], mu_, mv_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE),
                          cv2.remap(src_img[..., 3:], mu_, mv_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)], -1)
    gd = cv2.remap(good, mu_, mv_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    w = vis * valid * (cosv ** 1.5) * np.clip(gd * 1.5 - .25, 0, 1) * wmul
    acc += smp * w[..., None]; wsum += w
paint = wsum > 0.12
col6 = np.where(paint[..., None], acc / np.maximum(wsum, 1e-9)[..., None], 0)
print("pintado por projecao", round(float(paint[valid].mean()) * 100, 1), "% dos texels")

# preenchimento: mediana das cores pintadas mais proximas no espaco 3D (final)
fill = valid & ~paint
if fill.any():
    tree = cKDTree(POSF[paint]); pc = col6[paint]
    _, nn = tree.query(POSF[fill], k=min(8, len(pc)))
    med = np.median(pc[nn], axis=1)
    col6[fill] = med
    if c.get("emission"): col6[fill, 3] = 0                      # o fogo nao vaza para o vazio
col = col6[..., :3]; mk = col6[..., 3:]

# AO (malha alta decimada), luz e sombra violeta
d = np.load(wpath(c, "ao256.npz")); ao2, v2_ = d["ao"], d["valid"]
idx = ndi.distance_transform_edt(~v2_, return_distances=False, return_indices=True)
ao2 = ao2[idx[0], idx[1]]
ao = cv2.resize(ao2.astype(np.float32), (TS, TS), interpolation=cv2.INTER_LINEAR)
L = np.array([-0.45, -0.35, 0.82]); L /= np.linalg.norm(L)
lam = np.clip((NRMF * L).sum(-1), 0, 1)
shade = 0.90 + 0.18 * lam
s = np.clip(1 - ao, 0, 1)[..., None]
out = col * shade[..., None] * (1 - 0.5 * s) * (1 - s * (1 - np.array([0.62, 0.56, 0.80])) * 0.8) + s * 0.025 * np.array([.5, .4, .8])
out = np.clip(out, 0, 1)
blur = cv2.GaussianBlur(out.astype(np.float32), (0, 0), 1.2); out = np.clip(out + 0.35 * (out - blur), 0, 1)    # nitidez
if c.get("emission"):                       # o fogo continua claro, nao recebe AO
    fm = np.clip(mk[..., 0], 0, 1)[..., None]; out = out * (1 - fm) + np.clip(col * 1.05, 0, 1) * fm

def gutter(img, val, n=10):
    idx = ndi.distance_transform_edt(~val, return_distances=False, return_indices=True)
    return img[idx[0], idx[1]]
out = gutter(out, valid)
mask = np.zeros((TS, TS, 4), np.float32)
mask[..., 0] = np.clip(mk[..., 0] * 1.4, 0, 1) if c.get("emission") else 0
mask[..., 1] = np.clip(0.30 + 0.55 * mk[..., 1], 0, 1)
mask[..., 2] = np.clip(mk[..., 2] * 1.3, 0, 1) if c.get("tint") else 0
mask[..., 3] = 1.0
for ch in range(3): mask[..., ch] = gutter(mask[..., ch:ch + 1], valid)[..., 0]
mask = cv2.resize(mask, (MS_, MS_), interpolation=cv2.INTER_AREA)
tex = c["asset"][3:]
cv2.imwrite(f"{OUT_ROOT}/T_{tex}_BC.png", cv2.cvtColor((out * 255 + .5).astype(np.uint8), cv2.COLOR_RGB2BGR))
cv2.imwrite(f"{OUT_ROOT}/T_{tex}_M.png", cv2.cvtColor((mask[..., :3] * 255 + .5).astype(np.uint8), cv2.COLOR_RGB2BGR))
save_json(wpath(c, "paint_report.json"), dict(painted_pct=float(paint[valid].mean()) * 100, ao_mean=float(ao[valid].mean()),
          emission_texels=int((mask[..., 0] > .3).sum()), tint_texels=int((mask[..., 2] > .3).sum())))
print("ED", tex)
