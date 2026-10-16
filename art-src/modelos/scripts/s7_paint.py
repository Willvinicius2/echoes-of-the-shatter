"""Etapa 7 (Python do venv com numpy, scipy, cv2, PIL): pintura do albedo 1024 da malha de jogo a partir da folha.

1. Rasteriza a malha de jogo em 4 vistas ortograficas (frente, costas, direita, esquerda; a esquerda e a direita
   espelhada) com z-buffer.
2. Alinha cada painel da folha a silhueta da malha: afim por ECC e depois fluxo optico denso sobre mapas de
   distancia assinada das duas silhuetas (a malha da IA nao e identica a folha, principalmente nas vistas
   laterais e na pluma).
3. Cada texel (posicao e normal da malha) recebe a cor de cada vista onde esta visivel, ponderada por
   cos(normal, camera)^p, sem amostrar perto de descontinuidades de profundidade nem do fundo da folha.
4. Buracos (sola, topo da cabeca, axilas, fundo da pluma) sao preenchidos pelo texel valido mais proximo no
   espaco 3D.
5. Luz embutida: AO e cavidade assadas da malha alta, luz quente do alto-esquerda e sombra violeta (03 secao 3.4),
   sem preto puro; pequena variacao de pincelada e nitidez; gutter dilatado.
Grava T_<asset>_BC.png (1024), T_<asset>_M.png (512; R rim, G emissivo, B AO, A reservado), work/paint_report.json
e work/paint_dbg_*.png.
Uso: python -I s7_paint.py m01_guerreiro
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from mdl_common import *

cfg = load_cfg()
G = 1024
EXT = 2.0
PX = EXT / G
CZ = 0.85
CY = 0.10
geo = np.load(wpath(cfg, "game_geo.npz"))
V, F = geo["verts"].astype(np.float64), geo["faces"]
valid, POS, NRM = geo["valid"], geo["pos"].astype(np.float64), geo["nrm"].astype(np.float64)

# direcao em que a camera olha e projecao (u, v, profundidade) de cada vista
VIEW = {
    "front": dict(dir=(0, 1, 0), proj=lambda p: (p[..., 0] / PX + G / 2, G / 2 - (p[..., 2] - CZ) / PX, p[..., 1])),
    "back": dict(dir=(0, -1, 0), proj=lambda p: (G / 2 - p[..., 0] / PX, G / 2 - (p[..., 2] - CZ) / PX, -p[..., 1])),
    "right": dict(dir=(1, 0, 0), proj=lambda p: (G / 2 - (p[..., 1] - CY) / PX, G / 2 - (p[..., 2] - CZ) / PX, p[..., 0])),
    "left": dict(dir=(-1, 0, 0), proj=lambda p: (G / 2 + (p[..., 1] - CY) / PX, G / 2 - (p[..., 2] - CZ) / PX, -p[..., 0])),
}


def zbuffer(view):
    u, v, d = VIEW[view]["proj"](V)
    z = np.full((G, G), np.inf)
    for a, b, c in F:
        pu, pv, pd = u[[a, b, c]], v[[a, b, c]], d[[a, b, c]]
        x0, x1 = int(max(np.floor(pu.min()), 0)), int(min(np.ceil(pu.max()), G - 1))
        y0, y1 = int(max(np.floor(pv.min()), 0)), int(min(np.ceil(pv.max()), G - 1))
        if x1 < x0 or y1 < y0:
            continue
        den = (pv[1] - pv[2]) * (pu[0] - pu[2]) + (pu[2] - pu[1]) * (pv[0] - pv[2])
        if abs(den) < 1e-12:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((pv[1] - pv[2]) * (xs - pu[2]) + (pu[2] - pu[1]) * (ys - pv[2])) / den
        w1 = ((pv[2] - pv[0]) * (xs - pu[2]) + (pu[0] - pu[2]) * (ys - pv[2])) / den
        w2 = 1 - w0 - w1
        ins = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        dd = w0 * pd[0] + w1 * pd[1] + w2 * pd[2]
        sub = z[y0:y1 + 1, x0:x1 + 1]
        upd = ins & (dd < sub)
        sub[upd] = dd[upd]
    return z


# --- folha
sheet = cv2.cvtColor(cv2.imread(cfg["sheet"], cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
cuts = [0] + cfg["sheet_cuts"] + [sheet.shape[1]]
panels = {"front": sheet[:, cuts[0]:cuts[1]], "right": sheet[:, cuts[1]:cuts[2]], "back": sheet[:, cuts[2]:cuts[3]]}
panels["left"] = panels["right"][:, ::-1].copy()


def figure_mask(img):
    bg = np.median(np.concatenate([img[:6].reshape(-1, 3), img[-6:].reshape(-1, 3)]), 0)
    diff = np.abs(img.astype(np.float32) - bg).max(-1)
    bgm = (diff <= cfg.get("sheet_bg_tol", 24)).astype(np.uint8)
    n, lab = cv2.connectedComponents(bgm)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    border = [b for b in border if b > 0]
    back = np.isin(lab, border)
    fig = (~back).astype(np.uint8)
    fig = cv2.morphologyEx(fig, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(fig)
    if n > 1:
        fig = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    return fig, bg


def sdf(mask, clip=40):
    m = mask.astype(np.uint8)
    inside = cv2.distanceTransform(m, cv2.DIST_L2, 3)
    outside = cv2.distanceTransform(1 - m, cv2.DIST_L2, 3)
    s = np.clip(inside - outside, -clip, clip)
    return cv2.GaussianBlur(s, (0, 0), 3)


report = {}
Z, SAMPLE, SMASK = {}, {}, {}
for view in VIEW:
    z = zbuffer(view)
    Z[view] = z
    M = np.isfinite(z).astype(np.uint8)
    img = panels[view]
    Sp, bg = figure_mask(img)
    ys_, xs_ = np.where(M); ysp, xsp = np.where(Sp)
    cM = np.array([xs_.mean(), ys_.mean()]); cS = np.array([xsp.mean(), ysp.mean()])
    s = np.sqrt(Sp.sum() / M.sum())
    A0 = np.array([[1 / s, 0, cM[0] - cS[0] / s], [0, 1 / s, cM[1] - cS[1] / s]], np.float32)   # painel -> grade
    C0 = cv2.warpAffine(img, A0, (G, G), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    S0 = cv2.warpAffine(Sp.astype(np.float32), A0, (G, G), flags=cv2.INTER_LINEAR)
    iou0 = float(((S0 > .5) & (M > 0)).sum() / max(((S0 > .5) | (M > 0)).sum(), 1))
    # afim fino por ECC (grade da malha -> grade da folha)
    Mb = cv2.GaussianBlur(M.astype(np.float32), (0, 0), 6); Sb = cv2.GaussianBlur(S0, (0, 0), 6)
    W = np.eye(2, 3, dtype=np.float32)
    try:
        _, W = cv2.findTransformECC(Mb, Sb, W, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 7)
    except cv2.error as e:
        print("ECC falhou", view, e)
    C1 = cv2.warpAffine(C0, W, (G, G), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    S1 = cv2.warpAffine(S0, W, (G, G), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
    # fluxo optico denso entre os mapas de distancia (borda da folha -> borda da malha)
    sm = sdf(M > 0); ss = sdf(S1 > .5)
    to8 = lambda a: np.clip((a + 40) * 255 / 80, 0, 255).astype(np.uint8)
    flow = cv2.calcOpticalFlowFarneback(to8(sm), to8(ss), None, 0.5, 5, 41, 5, 7, 1.5, 0)
    flow = cv2.GaussianBlur(flow, (0, 0), cfg.get("flow_smooth", 10))
    mag = np.linalg.norm(flow, axis=-1, keepdims=True)
    flow *= np.minimum(1, cfg.get("flow_max_px", 28) / np.maximum(mag, 1e-6))
    gx, gy = np.meshgrid(np.arange(G, dtype=np.float32), np.arange(G, dtype=np.float32))
    mapx, mapy = gx + flow[..., 0], gy + flow[..., 1]
    C2 = cv2.remap(C1, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    S2 = cv2.remap(S1, mapx, mapy, cv2.INTER_LINEAR)
    # erosao da mascara da folha: tira o halo de antialias com o fundo cinza
    Sm = cv2.erode((S2 > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8))
    iou1 = float(((S2 > .5) & (M > 0)).sum() / max(((S2 > .5) | (M > 0)).sum(), 1))
    report[view] = dict(iou_inicial=round(iou0, 3), iou_final=round(iou1, 3), escala_painel_para_grade=round(float(1 / s), 3))
    SAMPLE[view] = C2.astype(np.float32) / 255.0
    SMASK[view] = Sm
    dbg = C2.copy()
    edge = cv2.morphologyEx(M, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    dbg[edge] = (0, 255, 0)
    cv2.imwrite(wpath(cfg, f"paint_dbg_{view}.png"), cv2.cvtColor(dbg, cv2.COLOR_RGB2BGR))

# --- projecao nos texels
ty, tx = np.where(valid)
P, N = POS[ty, tx], NRM[ty, tx]
acc = np.zeros((len(P), 3)); wsum = np.zeros(len(P))
pw = cfg.get("proj_power", 3.0)
for view, vd in VIEW.items():
    d = np.array(vd["dir"], float)
    c = np.maximum(0, -(N @ d))
    u, v, dep = vd["proj"](P)
    z = Z[view]
    zmin = ndi.minimum_filter(np.where(np.isfinite(z), z, 9.0), size=3)
    # descontinuidade de profundidade
    zf = np.where(np.isfinite(z), z, 9.0)
    gr = np.maximum(np.abs(ndi.sobel(zf, 0)), np.abs(ndi.sobel(zf, 1)))
    disc = cv2.dilate((gr > cfg.get("disc_thr", 0.12)).astype(np.uint8), np.ones((5, 5), np.uint8))
    ui, vi = np.clip(np.round(u - 0.5).astype(int), 0, G - 1), np.clip(np.round(v - 0.5).astype(int), 0, G - 1)
    vis = (dep <= zmin[vi, ui] + cfg.get("depth_bias", 0.012)) & (disc[vi, ui] == 0) & (SMASK[view][vi, ui] > 0)
    w = np.where(vis, c ** pw, 0.0)
    col = np.stack([ndi.map_coordinates(SAMPLE[view][..., k], [v - 0.5, u - 0.5], order=1, mode='nearest') for k in range(3)], 1)
    acc += col * w[:, None]; wsum += w
have = wsum > cfg.get("min_weight", 0.02)
color = np.zeros((len(P), 3))
color[have] = acc[have] / wsum[have, None]
# buracos: texel valido mais proximo no espaco 3D (media dos mais proximos)
tree = cKDTree(P[have])
dist, idx = tree.query(P[~have], k=6)
wk = 1.0 / (dist + 1e-3)
color[~have] = (color[have][idx] * wk[..., None]).sum(1) / wk.sum(1, keepdims=True)
report["texels"] = dict(total=int(len(P)), pintados_por_projecao=int(have.sum()), preenchidos=int((~have).sum()),
                        pct_preenchidos=round(100 * float((~have).sum() / len(P)), 2))
img = np.zeros((G, G, 3)); img[ty, tx] = color

# --- luz embutida: AO, cavidade, luz quente do alto-esquerda, sombra violeta
def load_gray(name):
    a = cv2.imread(wpath(cfg, name), cv2.IMREAD_COLOR)
    return cv2.cvtColor(a, cv2.COLOR_BGR2RGB)[..., 0].astype(np.float32) / 255.0
ao, cav = load_gray("bake_ao.png"), load_gray("bake_cavity.png")
A = np.clip((ao - 0.15) / 0.85, 0, 1)
shadow_hex = cfg.get("shadow_color", "#2C2A4A"); light_hex = cfg.get("light_color", "#FFB86B")
hx = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255.0
SH, LT = hx(shadow_hex), hx(light_hex)
Lw = np.array(cfg.get("light_dir", [0.55, -0.45, 0.70])); Lw /= np.linalg.norm(Lw)     # esquerda(+X), frente(-Y), cima
nl = np.full((G, G), 0.5, np.float32)
nl[ty, tx] = (N @ Lw).astype(np.float32)
lit = np.clip(nl * 0.5 + 0.5, 0, 1)                           # lambert com wrap
k_ao, k_sh, k_li = cfg.get("k_ao", 0.55), cfg.get("k_shadow_tint", 0.35), cfg.get("k_light", 0.22)
out = img * (1 - k_ao * (1 - A)[..., None])                    # AO escurece
out = out + (SH[None, None] * 1.0 - out) * (k_sh * (1 - A))[..., None] * 0.5     # sombra muda de matiz para violeta
cvx = np.clip((cav - 0.5) * 2, -1, 1)
out = out * (1 + 0.45 * np.minimum(cvx, 0))[..., None]         # fendas escurecem
out = out + LT[None, None] * (0.10 * np.maximum(cvx, 0))[..., None]   # arestas convexas pegam luz quente
tint = (1 - k_li) + k_li * (lit[..., None] * LT[None, None] * 1.25 + (1 - lit[..., None]) * (SH[None, None] * 2.2))
out = out * np.clip(tint, 0, 1.4)
# pincelada: variacao de valor em duas escalas e nitidez
rng = np.random.default_rng(7)
nz = sum(cv2.GaussianBlur(rng.standard_normal((G, G)).astype(np.float32), (0, 0), s) * a for s, a in ((1.5, 1.0), (4.0, 2.2)))
nz = nz / (nz.std() + 1e-6)
out = out * (1 + cfg.get("brush_amp", 0.035) * nz)[..., None]
blur = cv2.GaussianBlur(out.astype(np.float32), (0, 0), 1.2)
out = out + cfg.get("sharpen", 0.5) * (out - blur)
floor = np.array([15, 11, 20], np.float32) / 255.0             # nada abaixo de #0F0B14 (03 secao 3.4)
out = np.maximum(out, floor)
if cfg.get("sat_max"):
    hsv = cv2.cvtColor(np.clip(out, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
    hsv[..., 1] = np.minimum(hsv[..., 1], cfg["sat_max"])
    out = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
out = np.clip(out, 0, 1)
# gutter: estende o texel valido mais proximo
_, (iy, ix) = ndi.distance_transform_edt(~valid, return_indices=True)
full = out[iy, ix]
full = np.where(valid[..., None], out, full)
asset = cfg["asset"]
albedo = (np.clip(full, 0, 1) * 255 + 0.5).astype(np.uint8)
cv2.imwrite(fpath(cfg, f"T_{asset[3:]}_BC.png"), cv2.cvtColor(albedo, cv2.COLOR_RGB2BGR))
# mascara 512: R rim (mais forte nas partes expostas), G emissivo (nenhum neste personagem), B AO, A reservado
m512 = lambda a: cv2.resize(a, (512, 512), interpolation=cv2.INTER_AREA)
mask = np.stack([m512(0.35 + 0.65 * A), np.zeros((512, 512), np.float32), m512(ao), np.ones((512, 512), np.float32)], -1)
cv2.imwrite(fpath(cfg, f"T_{asset[3:]}_M.png"), cv2.cvtColor((np.clip(mask, 0, 1) * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGBA2BGRA))
sat = cv2.cvtColor(np.clip(out, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)[..., 1][valid]
report["albedo"] = dict(min_rgb=int(albedo[valid].min()), mean_rgb=[round(float(x), 1) for x in albedo[valid].mean(0)],
                        saturacao_media=round(float(sat.mean()), 3), saturacao_p95=round(float(np.percentile(sat, 95)), 3))
save_json(wpath(cfg, "paint_report.json"), report)
print("S7", json.dumps(report))
