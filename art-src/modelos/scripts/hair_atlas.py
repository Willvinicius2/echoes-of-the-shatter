"""Atlas de cabelo com alpha a partir de imagens geradas em fundo azul chapado (cab_atlas.png: mechas onduladas; cab_atlas2.png: mechas lisas).
Saida: T_ArcherDark_Hair_BC.png (2048x1536 RGBA) e hair_atlas.json. Celulas: locks (onduladas) 2x4 de 512x512 no topo; 1 fio fino; smooth (lisas) 4 celulas de 384x512 na linha 3.
Decontaminacao: erode 2 px, suaviza alpha, cor das bordas vem da dilatacao do interior."""
import numpy as np, json
from PIL import Image, ImageFilter
D = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\cabeca"


def proc(path):
    im = np.asarray(Image.open(path).convert("RGB"), np.float32)
    blue = im[..., 2] - np.maximum(im[..., 0], im[..., 1])
    a = np.clip(1 - (blue - 60) / 90, 0, 1); a = np.clip((a - 0.15) / 0.85, 0, 1)
    for _ in range(2):
        a = np.minimum.reduce([a, np.roll(a, 1, 0), np.roll(a, -1, 0), np.roll(a, 1, 1), np.roll(a, -1, 1)])
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
    rgb = im.copy(); solid = a > 0.97
    for _ in range(8):
        acc = np.zeros_like(rgb); cnt = np.zeros(a.shape, np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                m = np.roll(np.roll(solid, dy, 0), dx, 1); acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * m[..., None]; cnt += m
        new = (~solid) & (cnt > 0); rgb[new] = acc[new] / cnt[new][:, None]; solid = solid | new
    # decontamina: onde o alpha e parcial, usa a cor do interior (dilatada) e nunca deixa azul/rosa passar do loiro
    part = a < 0.97
    rgb[part] = rgb[part] * 0.0 + rgb[part]
    rgb[..., 2] = np.minimum(rgb[..., 2], np.maximum(rgb[..., 0], rgb[..., 1]) * 0.9)
    rgb[..., 0] = np.minimum(rgb[..., 0], 255)
    return np.dstack([rgb, a * 255])


def segs(mask_cols, gap=10):
    idx = np.where(mask_cols)[0]; out = []; s = idx[0]; p = idx[0]
    for i in idx[1:]:
        if i - p > gap: out.append((s, p)); s = i
        p = i
    out.append((s, p)); return out


def cells(rgba):
    H, W, _ = rgba.shape; cw, ch = W // 4, H // 2; res = []
    for r in range(2):
        for c in range(4):
            cell = rgba[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
            sg = segs((cell[..., 3] > 100).sum(0) > 1)
            lock = max(sg, key=lambda s: s[1] - s[0])
            cand = [s for s in sg if s is not lock and (cell[:, s[0]:s[1] + 1, 3] > 100).sum() > 1500]
            res.append((cell, lock, cand[-1] if cand else None))
    return res


def crop(cell, sg, ramp):
    sub = cell[:, max(0, sg[0] - 6):sg[1] + 7].copy()
    rows = np.where((sub[..., 3] > 100).sum(1) > 0)[0]; sub = sub[rows[0]:rows[-1] + 1]
    if ramp:
        hh = sub.shape[0]; sub[..., 3] *= (np.clip(np.arange(hh) / (hh * 0.22), 0, 1) ** 1.5)[:, None]
    return Image.fromarray(sub.astype(np.uint8), "RGBA")


AT = Image.new("RGBA", (2048, 1536), (0, 0, 0, 0)); meta = dict(locks=[], strands=[], smooth=[])


def place(pil, ox, oy, cwid, chei, key):
    k = min((cwid - 4) / pil.size[0], (chei - 4) / pil.size[1])
    pil = pil.resize((max(2, int(pil.size[0] * k)), int(pil.size[1] * k)), Image.LANCZOS)
    px = ox + (cwid - pil.size[0]) // 2; py = oy + 2
    AT.alpha_composite(pil, (px, py)); meta[key].append([px / 2048, py / 1536, (px + pil.size[0]) / 2048, (py + pil.size[1]) / 1536])


for i, (cell, lock, strand) in enumerate(cells(proc(D + r"\cab_atlas.png"))):
    place(crop(cell, lock, True), (i % 4) * 512, (i // 4) * 512, 512, 512, "locks")
    if strand is not None and not meta["strands"]:
        place(crop(cell, strand, False), 0, 1024, 256, 512, "strands")
for i, (cell, lock, strand) in enumerate(cells(proc(D + r"\cab_atlas2.png"))[:4]):
    place(crop(cell, lock, True), 512 + i * 384, 1024, 384, 512, "smooth")
AT.save(D + r"\T_ArcherDark_Hair_BC.png"); json.dump(meta, open(D + r"\hair_atlas.json", "w"))
bg = Image.new("RGBA", AT.size, (100, 100, 110, 255)); bg.alpha_composite(AT); bg.convert("RGB").resize((1024, 768)).save(D + r"\hair_prev.png")
print(len(meta["locks"]), len(meta["strands"]), len(meta["smooth"]))
