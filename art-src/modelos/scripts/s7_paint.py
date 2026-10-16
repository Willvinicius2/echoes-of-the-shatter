"""Etapa 7 (Python do venv com numpy, scipy, cv2): pintura do albedo (tex_size) da malha de jogo a partir da folha.

1. Rasteriza a malha de jogo em vistas ortograficas (frente, costas, direita, esquerda) com z-buffer. A folha
   tem frente, lado e costas (cortes automaticos pelas colunas vazias, ou cfg.sheet_cuts); o lado e usado como
   direita ou esquerda conforme a silhueta da malha (a outra e o espelho). Arma: uma imagem so (single_view),
   costas = espelho.
2. Alinha cada painel a silhueta da malha: afim por ECC e depois fluxo optico denso sobre mapas de distancia
   assinada das duas silhuetas.
3. Cada texel (posicao e normal da malha) recebe a cor das vistas onde esta visivel, ponderada por
   cos(normal, camera)^p, sem amostrar perto de descontinuidades de profundidade nem do fundo da folha. Faces
   quase horizontais (topo e fundo) entram pelas vistas laterais com o cosseno baixo.
4. O que sobra sem cor e preenchido pela MEDIANA das cores pintadas mais proximas no espaco 3D (cor do material
   vizinho, sem listras).
5. Luz embutida (AO e cavidade da malha alta, luz quente do alto-esquerda, sombra violeta, sem preto puro),
   pincelada direcional (listras alongadas seguindo o eixo vertical do modelo projetado na UV), nitidez, teto de
   saturacao sat_max exceto nos tons-assinatura (sat_keep_hues), gutter dilatado.
Grava T_<Nome>_BC.png e T_<Nome>_M.png (tex_size/2; contrato do docs/04 3.5: R emissao, G rim, B tinta, A reservado),
work/paint_report.json e work/paint_dbg_*.png.
Uso: python -I s7_paint.py m01_guerreiro
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from mdl_common import *

cfg = load_cfg()
TS = cfg["tex_size"]
VG = 1024                      # grade das vistas ortograficas
geo = np.load(wpath(cfg, "game_geo.npz"))
V, F = geo["verts"].astype(np.float64), geo["faces"]
valid, POS, NRM = geo["valid"], geo["pos"].astype(np.float64), geo["nrm"].astype(np.float64)
bmin, bmax = V.min(0), V.max(0)
ctr = (bmin + bmax) / 2
EXT = 1.12 * float((bmax - bmin).max())
PX = EXT / VG
KS = EXT / 2.0                 # escala dos limiares em metros (afinados para 2 m)

VIEW = {
    "front": dict(dir=(0, 1, 0), proj=lambda p: ((p[..., 0] - ctr[0]) / PX + VG / 2, VG / 2 - (p[..., 2] - ctr[2]) / PX, p[..., 1])),
    "back": dict(dir=(0, -1, 0), proj=lambda p: (VG / 2 - (p[..., 0] - ctr[0]) / PX, VG / 2 - (p[..., 2] - ctr[2]) / PX, -p[..., 1])),
    "right": dict(dir=(1, 0, 0), proj=lambda p: (VG / 2 - (p[..., 1] - ctr[1]) / PX, VG / 2 - (p[..., 2] - ctr[2]) / PX, p[..., 0])),
    "left": dict(dir=(-1, 0, 0), proj=lambda p: (VG / 2 + (p[..., 1] - ctr[1]) / PX, VG / 2 - (p[..., 2] - ctr[2]) / PX, -p[..., 0])),
}


def zbuffer(view):
    u, v, d = VIEW[view]["proj"](V)
    z = np.full((VG, VG), np.inf)
    for a, b, c in F:
        pu, pv, pd = u[[a, b, c]], v[[a, b, c]], d[[a, b, c]]
        x0, x1 = int(max(np.floor(pu.min()), 0)), int(min(np.ceil(pu.max()), VG - 1))
        y0, y1 = int(max(np.floor(pv.min()), 0)), int(min(np.ceil(pv.max()), VG - 1))
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


def figure_mask(img, alpha=None):
    if alpha is not None:
        fig = (alpha > 128).astype(np.uint8)
    else:
        bg = np.median(np.concatenate([img[:6].reshape(-1, 3), img[-6:].reshape(-1, 3)]), 0)
        diff = np.abs(img.astype(np.float32) - bg).max(-1)
        bgm = (diff <= cfg.get("sheet_bg_tol", 24)).astype(np.uint8)
        n, lab = cv2.connectedComponents(bgm)
        border = [b for b in np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])) if b > 0]
        fig = (~np.isin(lab, border)).astype(np.uint8)
    fig = cv2.morphologyEx(fig, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(fig)
    if n > 1:
        fig = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    return fig


def find_cuts(img):
    bg = np.median(np.concatenate([img[:6].reshape(-1, 3), img[-6:].reshape(-1, 3)]), 0)
    fig = (np.abs(img.astype(np.float32) - bg).max(-1) > cfg.get("sheet_bg_tol", 24))
    fig = cv2.morphologyEx(fig.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    occ = fig.sum(0) > 2
    runs, s = [], None
    for x, o in enumerate(occ):
        if not o and s is None:
            s = x
        if o and s is not None:
            runs.append((s, x)); s = None
    inner = [(a, b) for a, b in runs if a > 0 and b < len(occ) and b - a >= 4]
    inner = sorted(sorted(inner, key=lambda r: r[0] - r[1])[:2])
    return [(a + b) // 2 for a, b in inner]


def sdf(mask, clip=40):
    m = mask.astype(np.uint8)
    s = np.clip(cv2.distanceTransform(m, cv2.DIST_L2, 3) - cv2.distanceTransform(1 - m, cv2.DIST_L2, 3), -clip, clip)
    return cv2.GaussianBlur(s, (0, 0), 3)


def align(M, img, Sp):
    """Alinha img (painel) a silhueta M da malha. Devolve cor e mascara na grade da vista e o IoU."""
    ys_, xs_ = np.where(M); ysp, xsp = np.where(Sp)
    cM = np.array([xs_.mean(), ys_.mean()]); cS = np.array([xsp.mean(), ysp.mean()])
    s = np.sqrt(Sp.sum() / M.sum())
    A0 = np.array([[1 / s, 0, cM[0] - cS[0] / s], [0, 1 / s, cM[1] - cS[1] / s]], np.float32)
    C0 = cv2.warpAffine(img, A0, (VG, VG), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    S0 = cv2.warpAffine(Sp.astype(np.float32), A0, (VG, VG), flags=cv2.INTER_LINEAR)
    iou = lambda S: float(((S > .5) & (M > 0)).sum() / max(((S > .5) | (M > 0)).sum(), 1))
    iou0 = iou(S0)
    Mb = cv2.GaussianBlur(M.astype(np.float32), (0, 0), 6); Sb = cv2.GaussianBlur(S0, (0, 0), 6)
    W = np.eye(2, 3, dtype=np.float32)
    try:
        _, W = cv2.findTransformECC(Mb, Sb, W, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 7)
    except cv2.error as e:
        print("ECC falhou", e)
    C1 = cv2.warpAffine(C0, W, (VG, VG), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    S1 = cv2.warpAffine(S0, W, (VG, VG), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
    to8 = lambda a: np.clip((a + 40) * 255 / 80, 0, 255).astype(np.uint8)
    flow = cv2.calcOpticalFlowFarneback(to8(sdf(M > 0)), to8(sdf(S1 > .5)), None, 0.5, 5, 41, 5, 7, 1.5, 0)
    flow = cv2.GaussianBlur(flow, (0, 0), cfg.get("flow_smooth", 10))
    mag = np.linalg.norm(flow, axis=-1, keepdims=True)
    flow *= np.minimum(1, cfg.get("flow_max_px", 28) / np.maximum(mag, 1e-6))
    gx, gy = np.meshgrid(np.arange(VG, dtype=np.float32), np.arange(VG, dtype=np.float32))
    C2 = cv2.remap(C1, gx + flow[..., 0], gy + flow[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    S2 = cv2.remap(S1, gx + flow[..., 0], gy + flow[..., 1], cv2.INTER_LINEAR)
    return C2, S2, iou0, iou(S2), float(1 / s)


# --- entradas: folha de 3 vistas ou imagem unica (arma)
report = {}
if cfg.get("single_view"):
    raw = cv2.imread(cfg["single_view"], cv2.IMREAD_UNCHANGED)
    alpha = raw[..., 3] if raw.shape[2] == 4 else None
    rgb = cv2.cvtColor(raw[..., :3], cv2.COLOR_BGR2RGB)
    panel = {"front": (rgb, figure_mask(rgb, alpha)), "back": (rgb[:, ::-1].copy(), figure_mask(rgb, alpha)[:, ::-1].copy())}
    if alpha is not None:
        panel["back"] = (rgb[:, ::-1].copy(), figure_mask(rgb[:, ::-1], alpha[:, ::-1].copy()))
    views = ["front", "back"]
    side_choice = {}
else:
    sheet = cv2.cvtColor(cv2.imread(cfg["sheet"], cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    cut = cfg.get("sheet_cuts") or find_cuts(sheet)
    report["cortes_da_folha"] = cut
    cuts = [0] + list(cut) + [sheet.shape[1]]
    pf, ps, pb = sheet[:, cuts[0]:cuts[1]], sheet[:, cuts[1]:cuts[2]], sheet[:, cuts[2]:cuts[3]]
    panel = {"front": (pf, figure_mask(pf)), "back": (pb, figure_mask(pb))}
    views = ["front", "back", "right", "left"]

Z, SAMPLE, SMASK = {}, {}, {}
for view in views:
    Z[view] = zbuffer(view)
Mk = {v: np.isfinite(Z[v]).astype(np.uint8) for v in views}
if not cfg.get("single_view"):
    # o painel lateral serve de vista direita se o personagem olha para a direita (silhueta da malha decide)
    cand = {}
    for name, flip in (("as_is", False), ("flipped", True)):
        im = ps[:, ::-1].copy() if flip else ps
        cand[name] = align(Mk["right"], im, figure_mask(im))
    pick = "as_is" if cand["as_is"][3] >= cand["flipped"][3] else "flipped"
    report["lado_da_folha"] = dict(escolha=("olha para a direita" if pick == "as_is" else "olha para a esquerda"),
                                   iou={k: round(v[3], 3) for k, v in cand.items()})
    side_right = ps if pick == "as_is" else ps[:, ::-1].copy()
    panel["right"] = (side_right, figure_mask(side_right))
    panel["left"] = (side_right[:, ::-1].copy(), figure_mask(side_right[:, ::-1].copy()))
for view in views:
    img, Sp = panel[view]
    C2, S2, iou0, iou1, sc_ = align(Mk[view], img, Sp)
    SMASK[view] = cv2.erode((S2 > 0.5).astype(np.uint8), np.ones((5, 5), np.uint8))
    SAMPLE[view] = C2.astype(np.float32) / 255.0
    report[view] = dict(iou_inicial=round(iou0, 3), iou_final=round(iou1, 3))
    dbg = C2.copy()
    dbg[cv2.morphologyEx(Mk[view], cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0] = (0, 255, 0)
    cv2.imwrite(wpath(cfg, f"paint_dbg_{view}.png"), cv2.cvtColor(dbg, cv2.COLOR_RGB2BGR))

# --- projecao nos texels
ty, tx = np.where(valid)
P, N = POS[ty, tx], NRM[ty, tx]
acc = np.zeros((len(P), 3)); wsum = np.zeros(len(P))
pw = cfg.get("proj_power", 3.0)
for view in views:
    d = np.array(VIEW[view]["dir"], float)
    c = np.maximum(0, -(N @ d))
    u, v, dep = VIEW[view]["proj"](P)
    zf = np.where(np.isfinite(Z[view]), Z[view], 9.0 * KS)
    zmin = ndi.minimum_filter(zf, size=3)
    gr = np.maximum(np.abs(ndi.sobel(zf, 0)), np.abs(ndi.sobel(zf, 1)))
    disc = cv2.dilate((gr > cfg.get("disc_thr", 0.4) * KS).astype(np.uint8), np.ones((5, 5), np.uint8))
    ui, vi = np.clip(np.round(u - 0.5).astype(int), 0, VG - 1), np.clip(np.round(v - 0.5).astype(int), 0, VG - 1)
    vis = (dep <= zmin[vi, ui] + cfg.get("depth_bias", 0.012) * KS) & (disc[vi, ui] == 0) & (SMASK[view][vi, ui] > 0)
    w = np.where(vis, c ** pw, 0.0)
    col = np.stack([ndi.map_coordinates(SAMPLE[view][..., k], [v - 0.5, u - 0.5], order=1, mode='nearest') for k in range(3)], 1)
    acc += col * w[:, None]; wsum += w
have = wsum > cfg.get("min_weight", 0.001)
color = np.zeros((len(P), 3))
color[have] = acc[have] / wsum[have, None]
# sobras: mediana das cores pintadas mais proximas no espaco 3D (cor do material vizinho, sem listras)
tree = cKDTree(P[have])
dist, idx = tree.query(P[~have], k=cfg.get("fill_k", 24))
color[~have] = np.median(color[have][idx], axis=1)
report["texels"] = dict(total=int(len(P)), pintados_por_projecao=int(have.sum()), preenchidos=int((~have).sum()),
                        pct_preenchidos=round(100 * float((~have).sum() / len(P)), 2))
img = np.zeros((TS, TS, 3)); img[ty, tx] = color

# --- luz embutida
def load_gray(name):
    a = cv2.imread(wpath(cfg, name), cv2.IMREAD_COLOR)
    return cv2.cvtColor(a, cv2.COLOR_BGR2RGB)[..., 0].astype(np.float32) / 255.0
ao, cav = load_gray("bake_ao.png"), load_gray("bake_cavity.png")
A = np.clip((ao - 0.15) / 0.85, 0, 1)
hx = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255.0
SH, LT = hx(cfg.get("shadow_color", "#2C2A4A")), hx(cfg.get("light_color", "#FFB86B"))
Lw = np.array(cfg.get("light_dir", [0.55, -0.45, 0.70])); Lw /= np.linalg.norm(Lw)     # esquerda(+X), frente(-Y), cima
nl = np.full((TS, TS), 0.5, np.float32); nl[ty, tx] = (N @ Lw).astype(np.float32)
lit = np.clip(nl * 0.5 + 0.5, 0, 1)
k_ao, k_sh, k_li = cfg.get("k_ao", 0.55), cfg.get("k_shadow_tint", 0.35), cfg.get("k_light", 0.22)
out = img * (1 - k_ao * (1 - A)[..., None])
out = out + (SH[None, None] - out) * (k_sh * (1 - A))[..., None] * 0.5
cvx = np.clip((cav - 0.5) * 2, -1, 1)
out = out * (1 + 0.45 * np.minimum(cvx, 0))[..., None]
out = out + LT[None, None] * (0.10 * np.maximum(cvx, 0))[..., None]
tint = (1 - k_li) + k_li * (lit[..., None] * LT[None, None] * 1.25 + (1 - lit[..., None]) * (SH[None, None] * 2.2))
out = out * np.clip(tint, 0, 1.4)

# --- pincelada direcional: o eixo vertical do modelo projetado na UV dita a direcao das listras
vm = valid.astype(np.float32)
def smooth_masked(a, s):
    return cv2.GaussianBlur(a * vm, (0, 0), s) / np.maximum(cv2.GaussianBlur(vm, (0, 0), s), 1e-4)
zmap = np.zeros((TS, TS), np.float32); zmap[ty, tx] = P[:, 2]
xmap = np.zeros((TS, TS), np.float32); xmap[ty, tx] = P[:, 0]
zs, xs_ = smooth_masked(zmap, 2.0), smooth_masked(xmap, 2.0)
gz = np.stack([cv2.Sobel(zs, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(zs, cv2.CV_32F, 0, 1, ksize=3)], -1)
gx_ = np.stack([cv2.Sobel(xs_, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(xs_, cv2.CV_32F, 0, 1, ksize=3)], -1)
use_x = np.linalg.norm(gz, axis=-1) < 1e-4 * KS
g = np.where(use_x[..., None], gx_, gz)
theta = np.arctan2(g[..., 1], g[..., 0])
NA = 8
q = np.round(((theta % np.pi) / np.pi) * NA).astype(int) % NA
rng = np.random.default_rng(7)
base = rng.standard_normal((TS, TS)).astype(np.float32)
Lk = max(7, int(round(TS * cfg.get("stroke_len_frac", 0.014))))
streaks = np.zeros((NA, TS, TS), np.float32)
for i in range(NA):
    ang = i * np.pi / NA
    ker = np.zeros((Lk, Lk), np.float32)
    c0 = Lk // 2
    cv2.line(ker, (int(round(c0 - np.cos(ang) * c0)), int(round(c0 - np.sin(ang) * c0))),
             (int(round(c0 + np.cos(ang) * c0)), int(round(c0 + np.sin(ang) * c0))), 1.0, 1)
    ker /= max(ker.sum(), 1)
    st = cv2.filter2D(cv2.GaussianBlur(base, (0, 0), 0.7), -1, ker, borderType=cv2.BORDER_REFLECT)
    streaks[i] = st / (st.std() + 1e-6)
stroke = np.take_along_axis(streaks, q[None], 0)[0]
dab = cv2.GaussianBlur(rng.standard_normal((TS, TS)).astype(np.float32), (0, 0), TS / 128.0)
dab /= dab.std() + 1e-6
amp_s, amp_d = cfg.get("brush_amp", 0.04), cfg.get("dab_amp", 0.03)
out = out * (1 + amp_s * stroke + amp_d * dab)[..., None]
blur = cv2.GaussianBlur(out.astype(np.float32), (0, 0), 1.2)
out = out + cfg.get("sharpen", 0.5) * (out - blur)
out = np.maximum(out, np.array([15, 11, 20], np.float32) / 255.0)       # nada abaixo de #0F0B14 (03 secao 3.4)
out = np.clip(out, 0, 1).astype(np.float32)

# --- teto de saturacao (03 3.4: personagens <= 70%) exceto nos tons-assinatura da folha
hsv = cv2.cvtColor(out, cv2.COLOR_RGB2HSV)
def hue_mask(h, ranges):
    m = np.zeros(h.shape, bool)
    for lo, hi in ranges:
        m |= ((h >= lo) & (h <= hi)) if lo <= hi else ((h >= lo) | (h <= hi))
    return m
keep = hue_mask(hsv[..., 0], cfg.get("sat_keep_hues", cfg.get("tint_hues", []) + cfg.get("emissive_hues", []))) & (hsv[..., 1] > 0.3)
keep = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 1.5)
smax = cfg.get("sat_max", 0.70)
sat_new = np.minimum(hsv[..., 1], smax)
hsv[..., 1] = hsv[..., 1] * keep + sat_new * (1 - keep)
out = np.clip(cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB), 0, 1)
out = np.maximum(out, np.array([15, 11, 20], np.float32) / 255.0)

_, (iy, ix) = ndi.distance_transform_edt(~valid, return_indices=True)
full = np.where(valid[..., None], out, out[iy, ix])
asset = cfg["asset"]
albedo = (np.clip(full, 0, 1) * 255 + 0.5).astype(np.uint8)
cv2.imwrite(fpath(cfg, f"T_{asset[3:]}_BC.png"), cv2.cvtColor(albedo, cv2.COLOR_RGB2BGR))

# --- mascara (tex_size/2), contrato do docs/04 secao 3.5: R = emissao (so o que brilha), G = rim (1 em armadura e
# pele, menor em tecido escuro), B = tinta/raridade (tecido, capa; 0 em metal e pele). O AO vai so no albedo.
hsv = cv2.cvtColor(albedo.astype(np.float32) / 255.0, cv2.COLOR_RGB2HSV)
def hmask(ranges):
    return hue_mask(hsv[..., 0], ranges) if ranges else np.zeros(hsv.shape[:2], bool)
zf_ = np.zeros((TS, TS), np.float32); zf_[ty, tx] = (P[:, 2] - V[:, 2].min()) / (V[:, 2].max() - V[:, 2].min())
emi = hmask(cfg.get("emissive_hues")) & (hsv[..., 1] > 0.45) & (hsv[..., 2] > cfg.get("emissive_v", 0.75)) & (zf_ >= cfg.get("emissive_zmin_frac", 0.0)) & valid
tintm = hmask(cfg.get("tint_hues")) & (hsv[..., 1] > 0.35) & (hsv[..., 2] > 0.12)
cloth = tintm | (hmask(cfg.get("cloth_hues")) & (hsv[..., 1] > 0.2))
rim = np.where(cloth & (hsv[..., 2] < 0.35), 0.5, 1.0)
rim = np.where(emi, 0.0, rim)
H2 = TS // 2
chan = lambda a_: cv2.resize(cv2.GaussianBlur(a_.astype(np.float32), (0, 0), 1.0), (H2, H2), interpolation=cv2.INTER_AREA)
mask = np.stack([chan(emi), chan(rim), chan(tintm), np.ones((H2, H2), np.float32)], -1)
cv2.imwrite(fpath(cfg, f"T_{asset[3:]}_M.png"), cv2.cvtColor((np.clip(mask, 0, 1) * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGBA2BGRA))
sat = hsv[..., 1][valid]
report["albedo"] = dict(min_rgb=int(albedo[valid].min()), mean_rgb=[round(float(x), 1) for x in albedo[valid].mean(0)],
                        saturacao_media=round(float(sat.mean()), 3), saturacao_p95=round(float(np.percentile(sat, 95)), 3),
                        pct_texels_sat_acima_70=round(100 * float((sat > 0.7).mean()), 1))
report["mascara"] = dict(R_emissao_media=round(float(mask[..., 0].mean()), 4), G_rim_media=round(float(mask[..., 1].mean()), 3),
                         B_tinta_media=round(float(mask[..., 2].mean()), 3))
save_json(wpath(cfg, "paint_report.json"), report)
print("S7", json.dumps(report))
