#!/usr/bin/env python3
"""Dá aos props em HD suave o tratamento do piso e do arqueiro: grade de pixels grossa (passo em px de mundo),
paleta reduzida por prop, contorno escuro de 1 px de grade e fundo com alfa binário.

Lê os originais de art-src/props-hd-originais/ (nunca os de godot/, para não degradar a cada rodada) e grava em
godot/art2d/props/. Também atualiza data2d/props_manifest.csv (tamanho e pivô) e a escala em data2d/props_2d.csv:
a imagem sai ampliada por m = round(passo/escala) com vizinho mais próximo, e a escala vira passo/m, de modo que
1 pixel da arte = `passo` px de mundo e o tamanho na tela continua igual ao de antes.

Uso: python3 tools/sprites2d/pixelar_props.py [passo=2] [cores=14]
"""
import csv, os, sys
from PIL import Image

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
ORIG = os.path.join(R, "art-src", "props-hd-originais")
DEST = os.path.join(R, "godot", "art2d", "props")
MAN = os.path.join(R, "godot", "data2d", "props_manifest.csv")
DEF = os.path.join(R, "godot", "data2d", "props_2d.csv")
PASSO = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
CORES = int(sys.argv[2]) if len(sys.argv) > 2 else 14
PULAR = {"altar_candles"}  # tem velas animadas por código (halo); mantém a arte
M = 1  # margem em pixels de grade para o contorno


def pixelar(im, escala):
    w, h = im.size
    lw = max(4, round(w * escala / PASSO))
    lh = max(4, round(h * escala / PASSO))
    # média com alfa pré-multiplicado, para a borda não puxar a cor do fundo
    a = im.getchannel("A")
    rgb = Image.composite(im.convert("RGB"), Image.new("RGB", im.size, (0, 0, 0)), a)
    pm = Image.merge("RGBA", (*rgb.split(), a)).resize((lw, lh), Image.BOX)
    pa = pm.getchannel("A")
    mask = pa.point(lambda v: 255 if v >= 110 else 0)
    r, g, b, _ = pm.split()
    # desfaz o pré-multiplicado
    px_r, px_g, px_b, px_a = r.load(), g.load(), b.load(), pa.load()
    cor = Image.new("RGB", (lw, lh))
    cp = cor.load()
    for y in range(lh):
        for x in range(lw):
            k = max(px_a[x, y], 1) / 255.0
            cp[x, y] = (min(255, int(px_r[x, y] / k)), min(255, int(px_g[x, y] / k)), min(255, int(px_b[x, y] / k)))
    q = cor.quantize(colors=CORES, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    out = Image.new("RGBA", (lw + 2 * M, lh + 2 * M), (0, 0, 0, 0))
    mk = Image.new("L", out.size, 0)
    mk.paste(mask, (M, M))
    out.paste(q, (M, M), mask)
    # contorno: pixel vazio com vizinho (4 direções) cheio; cor = o escuro do prop, mais escuro ainda
    pix = out.load()
    mp = mk.load()
    lum = lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    todas = [pix[x, y][:3] for y in range(out.height) for x in range(out.width) if mp[x, y]]
    esc = min(todas, key=lum) if todas else (20, 14, 24)
    cont = (int(esc[0] * 0.45), int(esc[1] * 0.45), int(esc[2] * 0.5), 255)
    for y in range(out.height):
        for x in range(out.width):
            if mp[x, y]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < out.width and 0 <= ny < out.height and mp[nx, ny]:
                    pix[x, y] = cont
                    break
    return out, (lw, lh)


def main():
    defs = list(csv.DictReader(open(DEF, encoding="utf-8")))
    man = list(csv.DictReader(open(MAN, encoding="utf-8")))
    d_por_id = {d["id"]: d for d in defs}
    for m in man:
        pid = m["id"]
        if pid in PULAR or pid not in d_por_id:
            continue
        escala = float(d_por_id[pid]["escala"])
        im = Image.open(os.path.join(ORIG, pid + ".png")).convert("RGBA")
        ow, oh = int(m["largura"]), int(m["altura"])
        px, py = int(m["pivo_x"]), int(m["pivo_y"])
        out, (lw, lh) = pixelar(im, escala)
        k = max(1, round(PASSO / escala))
        # pivô em pixels da grade: a base do prop fica na altura original; margem do contorno entra
        pxl = (px * escala / PASSO) + M
        pyl = (py * escala / PASSO) + M
        big = out.resize((out.width * k, out.height * k), Image.NEAREST)
        big.save(os.path.join(DEST, pid + ".png"))
        m["largura"], m["altura"] = str(big.width), str(big.height)
        # pivô = linha de baixo opaca (contorno incluído): o teste de ancoragem exige o pivô na base opaca do sprite
        bb = big.getchannel("A").point(lambda v: 255 if v > 127 else 0).getbbox()
        m["pivo_x"], m["pivo_y"] = str(round(pxl * k)), str(bb[3])
        d_por_id[pid]["escala"] = f"{PASSO / k:.4f}".rstrip("0").rstrip(".")
        print(pid, f"{ow}x{oh}@{escala} -> {lw}x{lh} grade, k={k}, escala {d_por_id[pid]['escala']}")
    for path, rows in ((MAN, man), (DEF, defs)):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
