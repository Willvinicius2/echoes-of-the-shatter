"""Texturas procedurais (CPU) da aljava v3: penas com barbas (atlas flechas 1024), alca (cor + normal com costura diagonal),
emblema/metal 512, interior da boca, e normal do corpo (bake) com a zona do emblema aplainada.
uso: python aljava_v3_tex.py <out_dir> <v2_dir> <bake_normal.png>"""
import sys, os, json, numpy as np
from PIL import Image, ImageFilter, ImageDraw
out, v2, bake = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
rng = np.random.default_rng(23)


def noise(h, w, k):
    a = rng.random((h // k + 2, w // k + 2)).astype(np.float32)
    return np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255


def save(a, name):
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(out, name))


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def feather(seed, base, pink_from, pink_amt, tipc, bars):
    r = np.random.default_rng(seed)
    H, W = 1024, 512
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = 1 - yy / (H - 1)
    u = (xx / (W - 1) - 0.5) * 2
    au = np.abs(u)
    w = 0.92 * np.sin(np.pi * np.clip(t, 0, 1) ** 0.72) ** 0.8 + 0.10 * (1 - t)
    p = t * bars - au * 11.0 + (u > 0) * 0.37
    fr = p - np.floor(p)
    jitter = r.random(int(bars * 2 + 80)).astype(np.float32)
    jj = jitter[np.clip(np.floor(p).astype(int) + 40, 0, len(jitter) - 1)]
    edge = w - (0.16 + 0.12 * jj) * fr * (au > 0.25)
    inside = (au < edge) & (t > 0.0) & (t < 0.995)
    slit = (fr < 0.10) & (au > 0.42 * w) & (au < w)
    alpha = (inside & ~slit).astype(np.float32)
    rq = (au < 0.045) & (t < 0.985)
    alpha[rq] = 1.0
    line = 0.5 + 0.5 * np.cos(2 * np.pi * p)
    col = np.zeros((H, W, 3), np.float32) + np.array(base, np.float32)
    col += (line[..., None] - 0.5) * 16 + (noise(H, W, 5)[..., None] - 0.5) * 16
    col += np.array([14, 6, 10], np.float32) * (au[..., None] ** 2)
    rach = au < 0.035
    col[rach] = np.array([92, 70, 70], np.float32) + (noise(H, W, 3)[..., None][rach] - 0.5) * 20
    pk = sstep(pink_from, pink_from + 0.30, t) * pink_amt
    pkc = np.array(tipc, np.float32) * (0.78 + 0.22 * line[..., None]) + (noise(H, W, 4)[..., None] - 0.5) * 22
    col = col * (1 - pk[..., None]) + pkc * pk[..., None]
    pm = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
    a = Image.fromarray(np.clip(alpha * 255, 0, 255).astype(np.uint8))
    return pm.resize((256, 512), Image.LANCZOS), a.resize((256, 512), Image.LANCZOS)


variants = [dict(seed=1, base=(22, 18, 26), pink_from=0.50, pink_amt=0.92, tipc=(214, 86, 120), bars=70),
            dict(seed=2, base=(15, 12, 20), pink_from=0.62, pink_amt=0.85, tipc=(196, 70, 108), bars=64),
            dict(seed=3, base=(30, 24, 32), pink_from=0.42, pink_amt=1.0, tipc=(224, 104, 136), bars=76),
            dict(seed=4, base=(222, 196, 200), pink_from=0.35, pink_amt=0.65, tipc=(214, 96, 128), bars=58)]
atl = Image.new("RGBA", (1024, 1024), (20, 16, 20, 255))
for i, vp in enumerate(variants):
    c, a = feather(**vp); c = c.convert("RGBA"); c.putalpha(a); atl.paste(c, (i * 256, 0))
A = np.asarray(atl, np.float32).copy()
sh = np.zeros((512, 256, 3), np.float32) + np.array([54, 38, 30]) + noise(512, 256, 4)[..., None] * 22
gx = np.linspace(-1, 1, 256)[None, :]; sh *= (1 - 0.35 * gx ** 2)[..., None]
for y0 in (60, 90, 420, 450): sh[y0:y0 + 10] = [200, 80, 112]
A[512:, 0:256, :3] = sh; A[512:, 0:256, 3] = 255
g = np.linspace(-1, 1, 256)[None, :] * np.ones((512, 1))
hd = np.zeros((512, 256, 3), np.float32) + np.array([156, 54, 88]) + (1 - np.abs(g) ** 1.5)[..., None] * np.array([70, 40, 50])
hd += (np.abs(g) < 0.05)[..., None] * 60 + noise(512, 256, 8)[..., None] * 12
A[512:, 256:512, :3] = hd; A[512:, 256:512, 3] = 255
save(A, "T_ArcherDark_Arrows_BC.png")

# alca 512: couro (esq) + metal (dir), cor + normal
S = 512
leather = np.array([66, 44, 34], np.float32) + noise(S, S, 3)[..., None] * 18 + noise(S, S, 24)[..., None] * 14
h = noise(S, S, 3) * 0.5 + noise(S, S, 12) * 0.5
tc = Image.new("L", (S, S), 0); dr = ImageDraw.Draw(tc); gr = Image.new("L", (S, S), 0); dg = ImageDraw.Draw(gr)
for x0 in (34, 222):
    for y0 in range(-16, S + 16, 20):
        dr.line([(x0 - 4, y0 + 12), (x0 + 4, y0 - 2)], fill=255, width=4)
    dg.line([(x0 + (10 if x0 < 100 else -10), 0), (x0 + (10 if x0 < 100 else -10), S)], fill=255, width=2)
tcm = np.asarray(tc.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255
grm = np.asarray(gr.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255
t = np.zeros((S, S, 3), np.float32)
t[:, :256] = leather[:, :256]
thread = np.array([176, 140, 104], np.float32)
t[:, :256] = t[:, :256] * (1 - tcm[:, :256, None]) + thread * tcm[:, :256, None]
t[:, :256] *= (1 - 0.45 * grm[:, :256, None])
t[:, :6] *= 0.5; t[:, 250:256] *= 0.5
metal = np.array([138, 104, 70], np.float32) + noise(S, S, 4)[..., None] * 26 + (noise(S, S, 40)[..., None] - 0.5) * 40
t[:, 256:] = metal[:, 256:]
save(t, "T_ArcherDark_Strap_BC.png")
hh = h * 0.35 + tcm * 1.0 - grm * 0.6
hh[:, 256:] = noise(S, S, 2)[:, 256:] * 0.2
gy, gx2 = np.gradient(hh * 9.0)
nrm = np.dstack([-gx2, gy, np.ones_like(hh)]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
save((nrm * 0.5 + 0.5) * 255, "T_ArcherDark_Strap_N.png")

# emblema/metal 512
E = np.zeros((512, 512, 3), np.float32)


def metal_blk(base, var):
    return np.array(base, np.float32) + (noise(256, 256, 3)[..., None] - 0.5) * var + (noise(256, 256, 40)[..., None] - 0.5) * var * 1.5


E[:256, :256] = metal_blk((70, 52, 46), 28)
E[:256, 256:] = metal_blk((168, 132, 98), 30)
yy = np.linspace(0, 1, 128)[:, None, None]
E[256:384, :] = np.array([226, 92, 128], np.float32) * (1.1 - 0.5 * yy) + noise(128, 512, 6)[..., None] * 24
E[384:, :256] = metal_blk((92, 68, 52), 26)[:128]
E[384:, 256:] = metal_blk((92, 72, 58), 22)[:128]
# regiao alca (couro/metal) fica no atlas da alca; aqui UV_LEATHER/UV_MET_S nao sao usados
save(E, "T_ArcherDark_Emblem_BC.png")

# interior da boca
ins = np.zeros((64, 8, 3), np.float32)
for i in range(64):
    k = i / 63                                   # i=0 -> v=1 do topo da imagem (borda)
    ins[i, :] = np.array([46, 36, 34], np.float32) * (1 - sstep(0.0, 0.55, k)) + np.array([6, 5, 6], np.float32) * sstep(0.0, 0.55, k)
save(ins, "T_ArcherDark_Inside_BC.png")

# normal do corpo
bn = Image.open(bake).convert("RGB"); sz = bn.size[0]
arr = np.asarray(bn, np.float32)
n = arr / 255 * 2 - 1
mag = np.hypot(n[..., 0], n[..., 1]); k = np.minimum(1, 0.55 / np.maximum(mag, 1e-6)) * 0.85   # limita ruido e suaviza
n[..., 0] *= k; n[..., 1] *= k
n[..., 2] = np.sqrt(np.clip(1 - n[..., 0] ** 2 - n[..., 1] ** 2, 0, 1))
arr = (n * 0.5 + 0.5) * 255
mk = Image.new("L", (sz, sz), 0); d = ImageDraw.Draw(mk)
for poly in json.load(open(os.path.join(v2, "emblem_mask.json"))):
    d.polygon([(p[0] * sz, (1 - p[1]) * sz) for p in poly], fill=255)
mk = mk.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(5))
m = (np.asarray(mk, np.float32) / 255)[..., None]
arr = arr * (1 - m) + np.array([128, 128, 255], np.float32) * m
im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9))
im.save(os.path.join(out, "T_ArcherDark_Quiver_Body_N.png"))
Image.open(os.path.join(v2, "T_ArcherDark_Quiver_Body_BC.png")).save(os.path.join(out, "T_ArcherDark_Quiver_Body_BC.png"))
# remendo do corpo: tile com a cor media/ruido do couro do corpo
bc = np.asarray(Image.open(os.path.join(v2, "T_ArcherDark_Quiver_Body_BC.png")).convert("RGB"), np.float32).reshape(-1, 3)
bc = bc[bc.sum(1) > 30]
mu = np.median(bc, 0); sd = bc.std(0) * 0.5
tile = mu + (noise(256, 256, 2)[..., None] - 0.5) * sd * 2.2 + (noise(256, 256, 24)[..., None] - 0.5) * sd * 2.0
save(tile, "T_ArcherDark_Patch_BC.png")
print("TEX OK", mu, sd)
