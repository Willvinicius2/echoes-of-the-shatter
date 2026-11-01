"""Corta as folhas brutas do gpt-image em folhas de quadros em linha, com alfa.
Uso: python fatiar.py <pasta_bruta> <pasta_saida (godot/art2d/fx/fogo)>
Entrada: fogo_<nome>.png (fundo magenta, N quadros em uma linha). Saída: <nome>.png de (N*tam) x tam.
Quadros e tamanhos vêm de FOLHAS em godot/scripts2d/fogo_util_2d.gd (copiados aqui). Ícones: icone_*.png -> 128 px."""
import sys, os
import numpy as np
from PIL import Image
FOLHAS = {"flecha_proj": (6, 96), "flecha_impacto": (8, 128), "queimadura": (6, 96), "meteoro_queda": (6, 128),
          "meteoro_impacto": (8, 256), "brasas_chao": (6, 256), "muralha_chama": (8, 128), "arauto_aura": (6, 128), "arauto_explosao": (8, 256)}

def key(im):
    a = np.asarray(im.convert("RGB")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mag = np.minimum(r, b) - g
    alpha = np.clip(1 - (mag - 40) / 90, 0, 1)
    spill = np.clip(mag, 0, None) * (alpha < 1)
    a[..., 0] -= spill * 0.6; a[..., 2] -= spill * 0.6
    return Image.fromarray(np.dstack([np.clip(a, 0, 255), alpha * 255]).astype(np.uint8), "RGBA")

def cortes(alpha, n):
    """n-1 cortes: perto de cada fronteira nominal (largura/n), no vale de menor massa de alfa (+-30% da celula)."""
    mass = (alpha > 20).sum(axis=0).astype(float)
    k = np.ones(9) / 9; mass = np.convolve(mass, k, mode="same")
    cw = len(mass) / n; out = []
    for i in range(1, n):
        c = int(cw * i); lo, hi = int(c - cw * 0.3), int(c + cw * 0.3)
        out.append(lo + int(np.argmin(mass[lo:hi])))
    return out

def fatia(src, dst, n, tam):
    im = key(Image.open(src))
    al = np.asarray(im.split()[3])
    bb = im.split()[3].point(lambda v: 255 if v > 20 else 0).getbbox()
    im = im.crop((0, bb[1], im.width, bb[3])); al = al[bb[1]:bb[3], :]
    cs = cortes(al, n)
    if len(cs) != n - 1: raise SystemExit(f"{src}: so achei {len(cs)+1} quadros, esperado {n}")
    lim = [0] + cs + [im.width]
    cells = []
    for i in range(n):
        c = im.crop((lim[i], 0, lim[i + 1], im.height))
        bx = c.split()[3].point(lambda v: 255 if v > 20 else 0).getbbox()
        cells.append(c.crop((bx[0], 0, bx[2], c.height)) if bx else c)
    esc = (tam * 0.96) / max(max(c.width for c in cells), im.height)
    folha = Image.new("RGBA", (n * tam, tam), (0, 0, 0, 0))
    for i, c in enumerate(cells):
        c = c.resize((max(1, round(c.width * esc)), max(1, round(c.height * esc))), Image.LANCZOS)
        folha.alpha_composite(c, (i * tam + (tam - c.width) // 2, (tam - c.height) // 2))
    folha.save(dst)

if __name__ == "__main__":
    ent, sai = sys.argv[1], sys.argv[2]
    os.makedirs(sai, exist_ok=True)
    for nome, (n, tam) in FOLHAS.items():
        p = os.path.join(ent, f"fogo_{nome}.png")
        if os.path.exists(p):
            fatia(p, os.path.join(sai, nome + ".png"), n, tam); print("ok", nome)
    for f in os.listdir(ent):
        if f.startswith("icone_") and f.endswith(".png") and "_alt" not in f:
            Image.open(os.path.join(ent, f)).convert("RGBA").resize((128, 128), Image.LANCZOS).save(os.path.join(sai, f)); print("ok", f)
