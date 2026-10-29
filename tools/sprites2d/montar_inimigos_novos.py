"""Monta as folhas de 128 px (5 direções) dos inimigos novos a partir das folhas 6x4 já sem fundo.

Uso: python montar_inimigos_novos.py <pasta_sprites_novos> <pasta_saida_sprites>
Fonte: linha 0 = andar S, 1 = andar N, 2 = andar E, 3 = ataque E (4 quadros) + morte E (2 quadros).
Limitações: SE e NE reaproveitam a vista E; ataque, hit e morte usam a vista E em todas as direções.
"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

IDS = {"g01_fantasma_errante": "wandering_ghost", "g02_espectro_correntes": "chain_wraith",
       "g03_esqueleto_soldado": "skeleton_soldier", "g04_morcego_cripta": "crypt_bat"}
F, FOOT_SRC, FOOT = 128, (128, 217), (64, 104)
ROW_DIR = [0, 0, 2, 2, 1]  # S, SE, E, NE, N -> linha da fonte (SE/NE usam E)

def limpa(a):
    """Tira o halo rosado/roxo das bordas e o excesso de R/B perto do vazio."""
    al = a[..., 3] > 0
    ring = ndimage.binary_dilation(~al, iterations=2) & al
    r, g, b = [a[..., i].astype(int) for i in range(3)]
    ex = np.clip(np.minimum(r, b) - g, 0, None)
    ruim = ring & (ex > 25)
    for i, ch in ((0, r), (2, b)):
        a[..., i] = np.where(ring, np.clip(ch - ex, 0, 255), ch).astype(np.uint8)
    a[ruim & (ex > 70), 3] = 0
    return a

def sem_fiapos(im, minimo=60):
    a = np.array(im)
    lab, n = ndimage.label(a[..., 3] > 0, structure=np.ones((3, 3)))
    if n:
        areas = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        for i, ar in enumerate(areas, 1):
            if ar < minimo:
                a[lab == i, 3] = 0
    return Image.fromarray(a, "RGBA")

def brilho_ciano(im, cor=(70, 235, 255)):
    """Borda ciano forte atrás do sprite, para ele se destacar no piso escuro."""
    al = np.array(im)[..., 3] > 0
    anel = ndimage.binary_dilation(al, iterations=2) & ~al
    g = ndimage.gaussian_filter(anel.astype(float), 1.5)
    g = np.clip(g * 1.4, 0, 1)
    glow = np.zeros(al.shape + (4,), np.uint8)
    glow[..., :3] = cor
    glow[..., 3] = (g * 120).astype(np.uint8)
    out = Image.fromarray(glow, "RGBA")
    out.alpha_composite(im)
    return out

def largura(im):
    bb = im.getbbox()
    return bb[2] - bb[0] if bb else 1

def escala_largura(im, alvo):
    """Escala o quadro em torno do pivô dos pés para a largura alvo (limitada a 0,8 a 1,25)."""
    k = min(1.25, max(0.8, alvo / largura(im)))
    if abs(k - 1) < 0.02:
        return im
    w = int(round(F * k))
    r = im.resize((w, w), Image.LANCZOS)
    out = Image.new("RGBA", (F, F), (0, 0, 0, 0))
    out.alpha_composite(r, (FOOT[0] - int(round(FOOT[0] * k)), FOOT[1] - int(round(FOOT[1] * k))))
    return out

def quadro(sheet, col, lin):
    c = sheet.crop((col * 256, lin * 256, col * 256 + 256, lin * 256 + 256))
    c = c.resize((128, 128), Image.LANCZOS)
    a = limpa(np.array(c))
    dx, dy = FOOT[0] - FOOT_SRC[0] // 2, FOOT[1] - FOOT_SRC[1] // 2
    out = Image.new("RGBA", (F, F), (0, 0, 0, 0))
    out.alpha_composite(Image.fromarray(a, "RGBA"), (dx, dy))
    return sem_fiapos(out)

def flash(im, dx):
    a = np.array(im).astype(int)
    m = a[..., 3] > 0
    a[m, :3] = np.clip(a[m, :3] + 90, 0, 255)
    o = Image.fromarray(a.astype(np.uint8), "RGBA")
    out = Image.new("RGBA", (F, F), (0, 0, 0, 0))
    out.alpha_composite(o, (dx, 0))
    return out

def folha(linhas):  # linhas: 5 listas de quadros
    n = len(linhas[0])
    s = Image.new("RGBA", (n * F, 5 * F), (0, 0, 0, 0))
    for y, l in enumerate(linhas):
        for x, q in enumerate(l):
            s.alpha_composite(q, (x * F, y * F))
    return s

def main(entrada, saida):
    for bruto, nome in IDS.items():
        sh = Image.open(os.path.join(entrada, bruto + ".png")).convert("RGBA")
        andar = {r: [quadro(sh, c, r) for c in range(6)] for r in range(3)}
        if nome == "crypt_bat":  # estabiliza a envergadura das asas entre os quadros
            for r, fr in andar.items():
                alvo = sorted(largura(q) for q in fr)[3]
                andar[r] = [escala_largura(q, alvo) for q in fr]
        ata = [quadro(sh, c, 3) for c in range(4)]
        mor = [quadro(sh, c, 3) for c in (4, 5)]
        if nome == "wandering_ghost":
            andar = {r: [brilho_ciano(q) for q in fr] for r, fr in andar.items()}
            ata = [brilho_ciano(sem_fiapos(q, 400)) for q in ata]
            mor = [brilho_ciano(q) for q in mor]
        if nome == "crypt_bat":
            ata = [sem_fiapos(q, 400) for q in ata]
        d = os.path.join(saida, nome)
        os.makedirs(d, exist_ok=True)
        idle = [andar[r] for r in ROW_DIR]
        run = [[andar[r][round(i * 6 / 8) % 6] for i in range(8)] for r in ROW_DIR]
        attack = [[ata[i] for i in (0, 1, 1, 2, 3, 3)] for _ in ROW_DIR]
        hit = [[flash(andar[r][0], 0), flash(andar[r][0], -4), flash(andar[r][0], -2)] for r in ROW_DIR]
        death = [[ata[3], mor[0], mor[0], mor[0], mor[1], mor[1], mor[1], mor[1]] for _ in ROW_DIR]
        for anim, l in (("idle", idle), ("run", run), ("attack", attack), ("hit", hit), ("death", death)):
            folha(l).save(os.path.join(d, f"{nome}_{anim}.png"))

if __name__ == "__main__":
    main(*sys.argv[1:3])
