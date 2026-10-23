"""Atlas de mechas com alpha (2048x1024: 8 colunas de 256x1024, raiz em cima), pintado por script: cada coluna e uma mecha
(tufo de fios finos ondulados, raiz escura, pontas claras, pontas rasgadas). Cores amostradas do close gerado (cab_cabelo.png)."""
import numpy as np, math
from PIL import Image, ImageDraw, ImageFilter
D = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\cabeca"
ref = np.asarray(Image.open(D + r"\cab_cabelo.png").convert("RGB"), np.float32)
# amostra o cabelo do close (regiao do topo da cabeca de perfil): pega quantis de luminancia
reg = ref[150:300, 60:450].reshape(-1, 3)
lum = reg @ np.array([0.3, 0.59, 0.11])
q = lambda a, b: reg[(lum >= np.percentile(lum, a)) & (lum <= np.percentile(lum, b))].mean(0)
DARK, MID, LIGHT = q(3, 20), q(40, 60), q(88, 99)
DARK, MID, LIGHT = np.array([118,84,46],np.float32), np.array([192,152,94],np.float32), np.array([234,203,142],np.float32)
print("cores", DARK, MID, LIGHT)
CW, CH, NC = 256, 1024, 8
SS = 2
rng = np.random.default_rng(11)
atlas = Image.new("RGBA", (CW * NC, CH), (0, 0, 0, 0))


def lerp(a, b, t): return a * (1 - t) + b * t


for c in range(NC):
    W, Hh = CW * SS, CH * SS
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    nstr = int(rng.integers(9, 13))
    sway = rng.uniform(-0.18, 0.18)        # deriva geral da mecha (fracao da largura)
    curl = rng.uniform(0.012, 0.035)
    strands = []
    for s in range(nstr):
        x0 = rng.uniform(0.18, 0.82)
        L = rng.uniform(0.72, 1.0) if s > 2 else rng.uniform(0.55, 0.8)
        ph = rng.uniform(0, 6.28); fr = rng.uniform(0.7, 1.5)
        wd = rng.uniform(22, 40) * SS
        tone = rng.uniform(0, 1)
        strands.append((x0, L, ph, fr, wd, tone))
    # envelope: as mechas afinam para a ponta
    for (x0, L, ph, fr, wd, tone) in sorted(strands, key=lambda s: s[5]):
        pts = []
        n = 60
        for k in range(n + 1):
            v = k / n * L
            # converge para o centro e deriva
            xc = 0.5 + (x0 - 0.5) * (1 - 0.55 * v ** 1.3) + sway * v ** 1.5 + curl * math.sin(ph + fr * v * 6.28)
            pts.append((xc * W, v * Hh))
        # contorno escuro (profundidade) + nucleo claro com gradiente raiz->ponta em segmentos
        for k in range(n):
            t = k / n
            col_core = lerp(lerp(DARK, MID, min(1, t * 1.6)), LIGHT, max(0, (t - 0.35) / 0.65) * (0.5 + 0.5 * tone))
            col_core = col_core * (0.82 + 0.3 * tone)
            w = wd * (1 - 0.9 * (t / (L + 1e-6)) ** 1.8 * (1 if L < 1 else 1)) * (0.65 + 0.35 * (1 - k / n))
            w = max(1.2, w)
            edge = tuple(int(x) for x in np.clip(col_core * 0.55, 0, 255)) + (255,)
            dr.line([pts[k], pts[k + 1]], fill=edge, width=int(w + 5), joint="curve")
        for k in range(n):
            t = k / n
            col_core = lerp(lerp(DARK, MID, min(1, t * 1.6)), LIGHT, max(0, (t - 0.35) / 0.65) * (0.5 + 0.5 * tone))
            col_core = col_core * (0.88 + 0.28 * tone)
            w = wd * (1 - 0.9 * (t / (L + 1e-6)) ** 1.8) * (0.65 + 0.35 * (1 - k / n))
            w = max(1.0, w)
            fill = tuple(int(x) for x in np.clip(col_core, 0, 255)) + (255,)
            dr.line([pts[k], pts[k + 1]], fill=fill, width=int(max(1, w)), joint="curve")
            # fios finos dentro da fita: sulco escuro + brilho
            if w > 8:
                dk = tuple(int(x) for x in np.clip(col_core * 0.62, 0, 255)) + (255,)
                hl = tuple(int(x) for x in np.clip(col_core * 1.15 + 12, 0, 255)) + (255,)
                for off, cc in ((-0.28, dk), (0.05, hl), (0.30, dk)):
                    dr.line([(pts[k][0] + w * off, pts[k][1]), (pts[k + 1][0] + w * off, pts[k + 1][1])], fill=cc, width=max(1, int(w * 0.09 + 1)))
    # raiz: faixa de 6% mais escura e opaca (se esconde sob a camada de cima)
    arr = np.asarray(im, np.float32)
    ys = np.linspace(0, 1, Hh)[:, None, None]
    arr[..., :3] *= (0.78 + 0.22 * np.clip(ys / 0.18, 0, 1))
    im2 = Image.fromarray(arr.astype(np.uint8), "RGBA").resize((CW, CH), Image.LANCZOS)
    # alpha com preenchimento do topo (raiz solida) para nao ficar buraco onde a mecha encosta no couro cabeludo
    a = np.asarray(im2, np.float32)
    top = int(CH * 0.05)
    atlas.paste(im2, (c * CW, 0))
at = np.asarray(atlas, np.float32)
# dilata a cor para fora do alpha (evita borda escura no mip)
rgb = at[..., :3].copy(); al = at[..., 3] > 8
for _ in range(6):
    acc = np.zeros_like(rgb); cnt = np.zeros(al.shape, np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            m = np.roll(np.roll(al, dy, 0), dx, 1); acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * m[..., None]; cnt += m
    new = (~al) & (cnt > 0); rgb[new] = acc[new] / cnt[new][:, None]; al = al | new
at[..., 3] *= np.clip(np.linspace(0, 1, CH)[:, None] / 0.07, 0, 1)
out = np.dstack([rgb, at[..., 3]]).astype(np.uint8)
Image.fromarray(out, "RGBA").save(D + r"\T_ArcherDark_Hair_BC.png")
print("ok")
