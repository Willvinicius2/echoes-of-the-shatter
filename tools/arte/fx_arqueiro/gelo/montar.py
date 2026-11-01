"""Fatia as folhas geradas (fundo magenta) em folhas de quadros iguais, com fundo transparente.
Uso: python montar.py <pasta_entrada> <pasta_saida>   (entrada: <id>.png do gerar.py; saída: godot/art2d/fx/gelo)
Divide a imagem em N células iguais (N em prompts_gelo.json), tira o magenta, recorta ao maior conteúdo comum e
guarda uma linha de N quadros do mesmo tamanho. Ícones: key + recorte 128 px (use prep_lote.py do HUD)."""
import json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ui_gpt_image"))
from key import key

def key_verde(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    gv = g - np.maximum(r, b)
    alpha = np.clip(1 - (gv - 40) / 90, 0, 1)
    sp = np.clip(g - np.maximum(r, b), 0, None) * (alpha < 1)
    a[..., 1] -= sp * 0.8
    a[..., 1] = np.minimum(a[..., 1], np.maximum(r, b))  # tira o tom turquesa/verde: fica azul-gelo
    rgb = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB").convert("HSV")
    h = np.array(rgb).astype(float)
    m = (h[..., 0] > 85) & (h[..., 0] < 149)  # verde-ciano -> azul-gelo (210 graus = 149)
    h[..., 0][m] = 149 - (149 - h[..., 0][m]) * 0.12
    a = np.array(Image.fromarray(h.astype(np.uint8), "HSV").convert("RGB")).astype(float)
    return Image.fromarray(np.dstack([a, alpha * 255]).astype(np.uint8), "RGBA")

def cortes(im, n):
    """Acha os n+1 limites de quadro nos maiores vazios da projecao horizontal (o modelo nem sempre respeita a grade)."""
    w = im.width
    col = (np.array(im)[..., 3] > 20).sum(axis=0)
    lim = [0]
    for i in range(1, n):
        c = i * w // n; r = w // (n * 3)
        seg = col[c - r:c + r]
        # centro do vazio mais largo (ou do minimo) perto da grade
        z = np.where(seg == seg.min())[0]
        lim.append(c - r + int(z[len(z) // 2]))
    lim.append(w)
    return lim

def limpa_bordas(c):
    """O modelo as vezes deixa lascas do quadro vizinho na borda da celula: apaga os pedacos pequenos que tocam
    a borda esquerda/direita (menos de 20% da area do maior pedaco)."""
    from scipy import ndimage
    a = np.array(c)
    lab, k = ndimage.label(a[..., 3] > 20, structure=np.ones((3, 3)))
    if k < 2: return c
    areas = ndimage.sum(np.ones_like(lab), lab, range(1, k + 1))
    maior = areas.max()
    bordas = set(np.unique(lab[:, 0])) | set(np.unique(lab[:, -1]))
    for i in range(1, k + 1):
        if i in bordas and areas[i - 1] < 0.2 * maior:
            a[lab == i] = 0
    return Image.fromarray(a, "RGBA")

def main(ent, sai):
    os.makedirs(sai, exist_ok=True)
    itens = json.load(open(os.path.join(os.path.dirname(__file__), "prompts_gelo.json"), encoding="utf-8"))
    for it in itens:
        p = os.path.join(ent, it["id"] + ".png")
        if not os.path.exists(p):
            print("falta", p); continue
        im = key_verde(p) if it.get('fundo') == 'verde' else key(p); n = it["quadros"]; w = im.width // n
        lim = cortes(im, n) if it.get('fundo') == 'verde' else [i * w for i in range(n + 1)]
        cel = [limpa_bordas(im.crop((lim[i], 0, lim[i + 1], im.height))) for i in range(n)]
        cel = [c.crop((0, 0, c.width, c.height)) for c in cel]
        # caixa comum: união dos conteúdos, centrada na célula
        box = None
        for c in cel:
            b = c.split()[3].point(lambda v: 255 if v > 20 else 0).getbbox()
            if b: box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
        if box is None: print("vazio", it["id"]); continue
        cw, ch = box[2] - box[0], box[3] - box[1]
        side = max(cw, ch)
        out = Image.new("RGBA", (side * n, side))
        for i, c in enumerate(cel):
            out.paste(c.crop(box), (i * side + (side - cw) // 2, (side - ch) // 2))
        out.save(os.path.join(sai, it["id"] + ".png"))
        print(it["id"], out.size, n, "quadros")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
