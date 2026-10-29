#!/usr/bin/env python3
"""Recorta as folhas brutas da IA (fundo magenta) no formato de docs/arte/25_formato_folhas_sprites_2d.md.

Uso: python tools/arte2d/recortar_sprites.py [saida_sprites] [saida_tiles]
Entrada: docs/arte/sprites2d/brutos/. Saída padrão: godot/art2d/sprites/<id>/<id>_<anim>.png e
godot/art2d/tiles/cripta_tiles.png. Também escreve o trecho de manifesto em
docs/arte/sprites2d/manifest_trecho.csv e um relatório de emenda dos tiles.
"""
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BRUTOS = os.path.join(RAIZ, "docs", "arte", "sprites2d", "brutos")
DIRS = ["S", "SE", "E", "NE", "N"]
FACE = {"S": (0, 1), "SE": (.7, .7), "E": (1, 0), "NE": (.7, -.7), "N": (0, -1)}

# id -> (arquivo base, quadro, pé x, pé y, altura do personagem parado, bob do idle)
PERSONAGENS = {
    "hollow_sentinel": ("s01_sentinela_espada", 128, 64, 104, 96, 1.5),
    "hollow_spearman": ("s02_sentinela_lanca", 128, 64, 104, 96, 1.5),
    "ghost_archer": ("s03_arqueiro_espectral", 128, 64, 104, 96, 3.0),
    "crypt_guardian": ("s04_guardiao_chefe", 256, 128, 208, 192, 1.0),
}
# animação -> (quadros, fps, loop)
ANIMS = {"idle": (6, 8, 1), "run": (8, 12, 1), "attack": (6, 14, 0), "hit": (3, 12, 0), "death": (8, 10, 0)}
EVENTO_ATAQUE = 3


def chave_magenta(img):
    """RGBA com o magenta removido (alpha suave, sem halo)."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    d = np.minimum(r, b) - g
    alpha = 1.0 - np.clip((d - 50.0) / 90.0, 0, 1)
    alpha[(r < 150) | (b < 150)] = 1.0
    solido = alpha > 0.5
    borda = solido & ~ndi.binary_erosion(solido, iterations=3)
    alpha = np.where(solido, 1.0, 0.0)  # contorno escuro do sprite cobre a serrilha
    # tira o rosa que sobrou na borda
    spill = np.clip(np.minimum(r, b) - g, 0, None) * 0.9
    r2 = np.where(borda, r - spill, r)
    b2 = np.where(borda, b - spill, b)
    alpha = np.where(borda & (d > 70), 0.0, alpha)
    out = np.stack([r2, g, b2, alpha * 255], -1).clip(0, 255).astype(np.uint8)
    return out


def extrair_quadros(path, nlin=4, ncol=6, cel=256):
    """Lista de listas (linha, coluna) de recortes RGBA (np.uint8) com o conteúdo de cada célula."""
    rgba = chave_magenta(Image.open(path))
    mask = rgba[..., 3] > 127
    aberto = ndi.binary_opening(mask, structure=np.ones((3, 3)))  # tira as linhas finas de grade
    lab, n = ndi.label(aberto)
    alturas, larg = mask.shape
    ch, cw = alturas / nlin, larg / ncol
    comps = ndi.find_objects(lab)
    donos = {}
    for i, sl in enumerate(comps, start=1):
        area = (lab[sl] == i).sum()
        if area < 60:
            continue
        cy, cx = ndi.center_of_mass(lab == i) if area < 5000 else ndi.center_of_mass((lab[sl] == i))
        if area >= 5000:
            cy += sl[0].start
            cx += sl[1].start
        donos.setdefault((min(nlin - 1, int(cy // ch)), min(ncol - 1, int(cx // cw))), []).append(i)
    quadros = [[None] * ncol for _ in range(nlin)]
    for (r, c), ids in donos.items():
        m = np.isin(lab, ids)
        m = ndi.binary_dilation(m, iterations=2) & mask
        ys, xs = np.where(m)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        rec = rgba[y0:y1, x0:x1].copy()
        rec[~m[y0:y1, x0:x1], 3] = 0
        quadros[r][c] = rec
    return quadros


def pe(rec):
    """x do pé = mediana dos pixels do fundo do sprite; y = base."""
    ys, xs = np.where(rec[..., 3] > 127)
    h = ys.max() + 1
    fundo = xs[ys >= h - max(3, int(h * 0.12))]
    return float(np.median(fundo)), h


def redim(rec, s):
    h, w = rec.shape[:2]
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    p = rec.astype(np.float32)
    p[..., :3] *= p[..., 3:4] / 255.0
    im = Image.fromarray(p.astype(np.uint8), "RGBA").resize((nw, nh), Image.LANCZOS)
    q = np.asarray(im).astype(np.float32)
    a = q[..., 3:4]
    q[..., :3] = np.where(a > 0, q[..., :3] * 255.0 / np.maximum(a, 1), 0)
    return q.clip(0, 255).astype(np.uint8)


def colocar(rec, s, F, px, py, dx=0, dy=0, flash=0.0):
    """Quadro FxF com o pé em (px+dx, py+dy). Encolhe só o quadro que não cabe."""
    fx, fh = pe(rec)
    if rec.shape[1] * s > F - 2 or fh * s > py - 2:
        s = min(s, (F - 2) / rec.shape[1], (py - 2) / fh)
    r = redim(rec, s)
    fx, fh = fx * s, fh * s
    x = int(round(px + dx - fx))
    y = int(round(py + dy - fh))
    x = max(0, min(F - r.shape[1], x)) if r.shape[1] <= F else 0
    y = max(0, min(F - r.shape[0], y))
    quadro = np.zeros((F, F, 4), np.uint8)
    h, w = min(r.shape[0], F), min(r.shape[1], F)
    quadro[y:y + h, x:x + w] = r[:h, :w]
    if flash:
        a = quadro[..., 3:4] > 0
        quadro[..., :3] = np.where(a, quadro[..., :3] * (1 - flash) + 255 * flash, 0).astype(np.uint8)
    return quadro


def montar(pid, cfg, saida):
    base, F, px, py, altura, bob = cfg
    prin = extrair_quadros(os.path.join(BRUTOS, base + ".png"))
    diag_path = os.path.join(BRUTOS, base + "_diag.png")
    diag = extrair_quadros(diag_path) if os.path.exists(diag_path) else None
    walk = {"S": prin[0], "N": prin[1], "E": prin[2]}
    ataque = {"E": [prin[3][i] for i in (0, 0, 1, 2, 3, 3)]}
    if diag:
        walk.update({"SE": diag[0], "NE": diag[1]})
        ataque.update({"SE": diag[2], "NE": diag[3]})
    for d in DIRS:  # o que faltar cai no vizinho mais próximo
        walk.setdefault(d, walk["E"])
    ataque.setdefault("SE", ataque["E"])
    ataque.setdefault("NE", ataque["E"])
    ataque["S"], ataque["N"] = ataque["SE"], ataque["NE"]
    morte = [prin[3][4], prin[3][5]]
    alts = [pe(q)[1] for q in walk["S"] if q is not None]
    s = altura / float(np.median(alts))
    folhas = {a: np.zeros((5 * F, n * F, 4), np.uint8) for a, (n, _, _) in ANIMS.items()}
    for li, d in enumerate(DIRS):
        w = [q for q in walk[d] if q is not None]
        at = [q for q in ataque[d] if q is not None] or w
        if len(at) < 6:
            at = (at * 6)[:6]
        fx, fy = FACE[d]
        for i in range(6):  # idle: respiração
            dy = bob * math.sin(2 * math.pi * i / 6)
            folhas["idle"][li * F:(li + 1) * F, i * F:(i + 1) * F] = colocar(w[0], s, F, px, py, dy=dy)
        for i in range(8):
            k = round(i * (len(w) - 1) / 7)
            folhas["run"][li * F:(li + 1) * F, i * F:(i + 1) * F] = colocar(w[k], s, F, px, py)
        for i in range(6):
            folhas["attack"][li * F:(li + 1) * F, i * F:(i + 1) * F] = colocar(at[i], s, F, px, py)
        for i, (rec_off, fl) in enumerate(((2, 0.6), (5, 0.25), (2, 0.0))):
            folhas["hit"][li * F:(li + 1) * F, i * F:(i + 1) * F] = colocar(
                w[0], s, F, px, py, dx=-fx * rec_off, dy=-fy * rec_off, flash=fl)
        for i in range(8):
            rec = morte[0] if i < 3 else morte[1]
            folhas["death"][li * F:(li + 1) * F, i * F:(i + 1) * F] = colocar(rec, s, F, px, py)
    os.makedirs(os.path.join(saida, pid), exist_ok=True)
    linhas = []
    for a, (n, fps, loop) in ANIMS.items():
        Image.fromarray(folhas[a], "RGBA").save(os.path.join(saida, pid, f"{pid}_{a}.png"), optimize=True)
        ev = EVENTO_ATAQUE if a == "attack" else ""
        linhas.append(f"{pid},{a},{pid}/{pid}_{a}.png,{F},{n},{fps},{loop},5,{px},{py},{ev}")
    return linhas


# ---- tiles ---------------------------------------------------------------
def sem_emenda(t):
    """Torna o tile contínuo ao repetir: mistura com ele mesmo deslocado meio tile."""
    n = t.shape[0]
    u = np.sin(np.linspace(0, np.pi, n)) ** 2
    m = np.outer(u, u)[..., None]
    rolado = np.roll(t.astype(np.float32), (n // 2, n // 2), (0, 1))
    return (t * m + rolado * (1 - m)).astype(np.uint8)


def erro_emenda(t):
    """Diferença média entre a borda esquerda e a direita (e topo/base); 0 = perfeito."""
    t = t.astype(np.float32)[..., :3]
    return float((np.abs(t[:, 0] - t[:, -1]).mean() + np.abs(t[0] - t[-1]).mean()) / 2)


def montar_tiles(saida_tiles):
    img = Image.open(os.path.join(BRUTOS, "t01_cripta_tiles.png")).convert("RGB")
    W = img.size[0]
    c = W / 8.0
    rgba = chave_magenta(img)

    def celula(r, k, margem=3, fundo_opaco=False):
        if fundo_opaco:
            margem = 14 if r < 3 else 7  # tira a grade magenta e o contorno entre os tiles
        box = (round(k * c) + margem, round(r * c) + margem, round((k + 1) * c) - margem, round((r + 1) * c) - margem)
        if fundo_opaco:
            return np.asarray(img.crop(box).resize((64, 64), Image.LANCZOS).convert("RGBA"))
        rec = rgba[box[1]:box[3], box[0]:box[2]]
        q = fit_cell(rec)
        return redim(q, 64.0 / q.shape[0])[:64, :64] if q.shape[0] != 64 else q

    def fit_cell(rec):
        ys, xs = np.where(rec[..., 3] > 127)
        if len(ys) == 0:
            return rec
        rec = rec[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        lado = max(rec.shape[:2])
        q = np.zeros((lado, lado, 4), np.uint8)
        y0 = lado - rec.shape[0]  # prop apoiado na base
        x0 = (lado - rec.shape[1]) // 2
        q[y0:y0 + rec.shape[0], x0:x0 + rec.shape[1]] = rec
        return q

    piso = lambda r, k: sem_emenda(celula(r, k, fundo_opaco=True))
    props = lambda r, k: celula(r, k)
    atlas = [None] * 64
    for i in range(4):
        atlas[i] = piso(0, i)                  # pisos lisos
    atlas[4] = piso(1, 0)                      # rachadura dourada
    atlas[5] = celula(2, 3, fundo_opaco=True)  # centro do círculo de runas (tapete)
    cinza = piso(0, 4).astype(np.float32)
    cinza[..., :3] = cinza[..., :3] * np.array([0.8, 0.65, 0.62])  # piso com cinza/sangue
    atlas[6] = cinza.astype(np.uint8)
    atlas[7] = props(5, 7)                     # porta fechada (selo)
    atlas[8] = props(4, 0)                     # parede, face frontal
    topo = piso(0, 5).astype(np.float32)
    topo[..., :3] *= 0.45
    atlas[9] = topo.astype(np.uint8)           # parede, topo (pedra escura)
    atlas[10] = props(4, 2)
    atlas[11] = props(4, 3)
    atlas[12] = props(5, 0)                    # pilar
    atlas[13] = props(5, 6)                    # portal aberto
    br = props(7, 0).astype(np.float32)
    br[..., :3] *= 0.6
    atlas[14] = br.astype(np.uint8)            # braseiro apagado (aceso escurecido; rever)
    atlas[15] = props(7, 0)                    # braseiro aceso
    extra = [(5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (4, 1), (4, 4), (4, 5), (4, 6), (4, 7),
             (6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6), (6, 7),
             (7, 1), (7, 2), (7, 3), (7, 4), (7, 5), (7, 6), (7, 7),
             (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7),
             (2, 0), (2, 1), (2, 2), (2, 4), (2, 5), (2, 6), (2, 7),
             (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 7)]
    for j, (r, k) in enumerate(extra):
        opaco = r in (1, 2, 3)
        atlas[16 + j] = piso(r, k) if r == 1 else celula(r, k, fundo_opaco=opaco)
    out = np.zeros((512, 512, 4), np.uint8)
    rel = []
    for i, t in enumerate(atlas):
        if t is None:
            continue
        out[(i // 8) * 64:(i // 8) * 64 + 64, (i % 8) * 64:(i % 8) * 64 + 64] = t
        if i < 5:
            rel.append(f"tile {i}: erro de emenda {erro_emenda(t):.1f}")
    os.makedirs(os.path.dirname(saida_tiles), exist_ok=True)
    Image.fromarray(out, "RGBA").save(saida_tiles, optimize=True)
    return rel


def main():
    saida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "godot", "art2d", "sprites")
    saida_t = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, "godot", "art2d", "tiles", "cripta_tiles.png")
    linhas = ["id,anim,arquivo,quadro,quadros,fps,loop,direcoes,pivo_x,pivo_y,evento_quadro"]
    for pid, cfg in PERSONAGENS.items():
        linhas += montar(pid, cfg, saida)
        print("ok", pid)
    with open(os.path.join(RAIZ, "docs", "arte", "sprites2d", "manifest_trecho.csv"), "w") as f:
        f.write("\n".join(linhas) + "\n")
    for l in montar_tiles(saida_t):
        print(l)


if __name__ == "__main__":
    main()
