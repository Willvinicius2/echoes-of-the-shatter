"""Pós-processa a arte pintada do Raio: remove o magenta, recorta em quadros iguais e salva.
Uso: python pos_processa.py <pasta_gerada> <raiz_do_repo>
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ui_gpt_image"))
from key import key
from PIL import Image, ImageDraw

FOLHAS = {  # id: (quadros, w, h)
    "flecha_eletrica_proj": (6, 64, 32),
    "raio_impacto": (8, 96, 96),
    "raio_arco": (4, 128, 32),
    "choque_overlay": (6, 64, 64),
    "tornado_tempestade": (8, 128, 160),
    "raio_coluna": (6, 64, 192),
    "arauto_trovao_aura": (6, 96, 96),
}
ICONES = {
    "icone_flecha_eletrica": "icone_shock_arrow",
    "icone_raio_encadeado": "icone_chain_lightning",
    "icone_tornado_tempestade": "icone_storm_tornado",
    "icone_arauto_trovao": "icone_herald_thunder",
}

def recorta(im, n, w, h):
    """Divide a folha em n colunas iguais. Usa uma caixa de proporcao w:h comum a todos os
    quadros (centrada no centro de cada coluna), para o loop nao tremer, e reduz ao tamanho final."""
    import numpy as np
    W, H = im.size
    cw = W / n
    al = np.asarray(im.split()[3]) > 12
    ys = np.where(al.any(axis=1))[0]
    cy = (ys.min() + ys.max()) / 2
    hy = (ys.max() - ys.min()) / 2
    hx = 0
    for i in range(n):
        xs = np.where(al[:, round(i * cw):round((i + 1) * cw)].any(axis=0))[0]
        if len(xs):
            hx = max(hx, (xs.max() - xs.min()) / 2, abs(xs.max() + xs.min()) / 2 - cw / 2 + (xs.max() - xs.min()) / 2)
    hx = max(hx, 1)
    r = w / h
    bh = max(2 * hy, 2 * hx / r) * 1.06
    bw = bh * r
    out = Image.new("RGBA", (w * n, h), (0, 0, 0, 0))
    for i in range(n):
        x0, x1 = round(i * cw), round((i + 1) * cw)
        cell = im.crop((x0, 0, x1, H))
        cx = (x1 - x0) / 2
        canvas = Image.new("RGBA", (round(bw), round(bh)), (0, 0, 0, 0))
        canvas.alpha_composite(cell, (round(bw / 2 - cx), round(bh / 2 - cy))) if bw/2-cx >= 0 and bh/2-cy >= 0 else canvas.paste(cell, (round(bw / 2 - cx), round(bh / 2 - cy)))
        out.alpha_composite(canvas.resize((w, h), Image.LANCZOS), (i * w, 0))
    return out

def main(src, raiz):
    fx = os.path.join(raiz, "godot", "art2d", "fx", "raio")
    ui = os.path.join(raiz, "godot", "art2d", "ui")
    for nome, (n, w, h) in FOLHAS.items():
        im = key(os.path.join(src, nome + ".png"))
        # o bbox por quadro recentra; para folhas de loop isso pode tremer, entao usa bbox global da folha
        recorta(im, n, w, h).save(os.path.join(fx, nome + ".png"))
        print(nome, "ok")
    for nome, dest in ICONES.items():
        im = Image.open(os.path.join(src, nome + ".png")).convert("RGBA")
        W, H = im.size
        m = int(W * 0.012)
        im = im.crop((m, m, W - m, H - m)).resize((128, 128), Image.LANCZOS)
        mask = Image.new("L", (512, 512), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 511, 511), radius=44, fill=255)
        im.putalpha(mask.resize((128, 128), Image.LANCZOS))
        im.save(os.path.join(ui, dest + ".png"))
        print(dest, "ok")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
