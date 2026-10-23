"""Recorta o atlas gerado (fundo azul chapado) em alpha: 8 mechas largas (celulas 512x512, 2 linhas x 4 colunas)
e 8 fios finos (linha inferior, celulas 256x512). Grava T_ArcherDark_Hair_BC.png (2048x1536 RGBA) e hair_atlas.json (UV de cada peca)."""
import numpy as np, json
from PIL import Image
D = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\cabeca"
im = np.asarray(Image.open(D + r"\cab_atlas.png").convert("RGB"), np.float32)
H, W, _ = im.shape
blue = im[..., 2] - np.maximum(im[..., 0], im[..., 1])
a = np.clip(1 - (blue - 60) / 90, 0, 1)
a = np.clip((a - 0.15) / 0.85, 0, 1)
# remove contaminacao azul na cor: onde a<1 puxa a cor para o interior (dilatacao de cores opacas)
rgb = im.copy(); solid = a > 0.9
for _ in range(4):
    acc = np.zeros_like(rgb); cnt = np.zeros(a.shape, np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            m = np.roll(np.roll(solid, dy, 0), dx, 1); acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * m[..., None]; cnt += m
    new = (~solid) & (cnt > 0); rgb[new] = acc[new] / cnt[new][:, None]; solid = solid | new
# so tons de cabelo: limita o azul residual
rgb[..., 2] = np.minimum(rgb[..., 2], np.maximum(rgb[..., 0], rgb[..., 1]) * 0.95)
rgba = np.dstack([rgb, a * 255])
AT = Image.new("RGBA", (2048, 1536), (0, 0, 0, 0)); meta = dict(locks=[], strands=[])
cw, ch = W // 4, H // 2
def segs(mask_cols, gap=10):
    idx = np.where(mask_cols)[0]; out = []; s = idx[0]; p = idx[0]
    for i in idx[1:]:
        if i - p > gap: out.append((s, p)); s = i
        p = i
    out.append((s, p)); return out
for r in range(2):
    for c in range(4):
        cell = rgba[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
        cols = (cell[..., 3] > 100).sum(0) > 1
        sg = segs(cols)
        lock = max(sg, key=lambda s: (s[1] - s[0]))
        cand = [s for s in sg if s is not lock and (cell[:, s[0]:s[1] + 1, 3] > 100).sum() > 1500]
        strand = cand[-1] if cand else None
        for kind, sgm in (("lock", lock), ("strand", strand)):
            if sgm is None: continue
            sub = cell[:, max(0, sgm[0] - 6):sgm[1] + 7]
            rows = np.where((sub[..., 3] > 100).sum(1) > 0)[0]
            sub = sub[rows[0]:rows[-1] + 1]
            sub = sub.copy()
            if kind == "lock":     # raiz com alpha em degrade: some sob a camada de cima (sem borda reta)
                hh = sub.shape[0]; ramp = np.clip(np.arange(hh) / (hh * 0.22), 0, 1) ** 1.5
                sub[..., 3] *= ramp[:, None]
                sub[..., :3] = sub[..., :3] * 1.0 + 0
            pil = Image.fromarray(sub.astype(np.uint8), "RGBA")
            if kind == "lock":
                cwid, chei, ox, oy = 512, 512, c * 512, r * 512
            else:
                cwid, chei, ox, oy = 256, 512, len(meta['strands']) * 256, 1024
            k = min((cwid - 4) / pil.size[0], (chei - 4) / pil.size[1])
            pil = pil.resize((max(2, int(pil.size[0] * k)), int(pil.size[1] * k)), Image.LANCZOS)
            px = ox + (cwid - pil.size[0]) // 2; py = oy + 2
            AT.alpha_composite(pil, (px, py))
            meta["locks" if kind == "lock" else "strands"].append([px / 2048, py / 1536, (px + pil.size[0]) / 2048, (py + pil.size[1]) / 1536])
AT.save(D + r"\T_ArcherDark_Hair_BC.png"); json.dump(meta, open(D + r"\hair_atlas.json", "w"))
bg = Image.new("RGBA", AT.size, (100, 100, 110, 255)); bg.alpha_composite(AT); bg.convert("RGB").resize((1024, 768)).save(D + r"\hair_prev.png")
print(len(meta["locks"]), len(meta["strands"]))
