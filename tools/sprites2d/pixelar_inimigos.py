#!/usr/bin/env python3
"""Dá aos inimigos (folhas HD pintadas) a densidade de pixel do arqueiro do PixelLab: cada quadro é reduzido (fator
`F`), a paleta fica em `CORES` cores por folha, o alfa vira binário e entra contorno escuro de 1 px. O quadro e o
pivô do manifesto encolhem pelo mesmo fator e `sprites_escala.csv` ganha a escala 2.5 (o ator amplia o sprite por
1/zoom da câmera, então 1 px da arte = 1 px da grade, como o arqueiro).

Os originais HD ficam em art-src/sprites-hd-originais/ (copiados na primeira rodada) e são sempre a fonte:
rodar de novo não degrada nada. Uso: python3 tools/sprites2d/pixelar_inimigos.py [cores=20]
"""
import csv, os, shutil, sys
from PIL import Image

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
SPR = os.path.join(R, "godot", "art2d", "sprites")
ORIG = os.path.join(R, "art-src", "sprites-hd-originais")
MAN = os.path.join(R, "godot", "data2d", "sprites_manifest.csv")
ESC = os.path.join(R, "godot", "data2d", "sprites_escala.csv")
CORES = int(sys.argv[1]) if len(sys.argv) > 1 else 20
FATOR = {128: 0.72, 192: 0.7, 256: 0.7}
HEROIS = {"arqueiro", "guerreiro", "mago"}


def reduz_quadro(im, lado_novo):
    a = im.getchannel("A")
    rgb = Image.composite(im.convert("RGB"), Image.new("RGB", im.size, (0, 0, 0)), a)
    pm = Image.merge("RGBA", (*rgb.split(), a)).resize((lado_novo, lado_novo), Image.BOX)
    return pm


def contorno(q, mascara):
    w, h = q.size
    px, mp = q.load(), mascara.load()
    lum = lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    cores = [px[x, y][:3] for y in range(h) for x in range(w) if mp[x, y]]
    if not cores:
        return
    esc = min(cores, key=lum)
    c = (int(esc[0] * 0.4), int(esc[1] * 0.4), int(esc[2] * 0.45), 255)
    novos = []
    for y in range(h):
        for x in range(w):
            if mp[x, y]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and mp[nx, ny]:
                    novos.append((x, y))
                    break
    for p in novos:
        px[p] = c
        mp[p] = 255


def processa_folha(arq, lado, cols, lins, novo):
    sheet = Image.open(arq).convert("RGBA")
    out = Image.new("RGBA", (cols * novo, lins * novo), (0, 0, 0, 0))
    quadros = []
    for r in range(lins):
        for c in range(cols):
            q = sheet.crop((c * lado, r * lado, (c + 1) * lado, (r + 1) * lado))
            quadros.append((r, c, reduz_quadro(q, novo)))
    # paleta única da folha: junta os quadros opacos numa imagem e quantiza
    junto = Image.new("RGB", (novo, novo * len(quadros)), (0, 0, 0))
    for i, (_, _, q) in enumerate(quadros):
        junto.paste(q.convert("RGB"), (0, i * novo))
    pal = junto.quantize(colors=CORES, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    for r, c, q in quadros:
        mask = q.getchannel("A").point(lambda v: 255 if v >= 110 else 0)
        cor = q.convert("RGB").quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB")
        res = Image.new("RGBA", (novo, novo), (0, 0, 0, 0))
        res.paste(cor, (0, 0), mask)
        mk = mask.copy()
        # o contorno pode sair 1 px do desenho: mantém dentro do quadro (a margem do HD já sobra)
        contorno(res, mk)
        out.paste(res, (c * novo, r * novo))
    return out


def main():
    rows = list(csv.DictReader(open(MAN, encoding="utf-8")))
    campos = list(rows[0].keys())
    ids = sorted(i for i in {r["id"] for r in rows} - HEROIS if os.path.isdir(os.path.join(SPR, i)))  # sem pasta = placeholder do cliente
    esc_rows = list(csv.DictReader(open(ESC, encoding="utf-8")))
    com_escala = {r["id"] for r in esc_rows}
    # backup dos originais (uma vez)
    for i in ids:
        d_orig = os.path.join(ORIG, i)
        if not os.path.isdir(d_orig):
            shutil.copytree(os.path.join(SPR, i), d_orig, ignore=shutil.ignore_patterns("*.import"))
    feitos = set()
    com_arte = set()
    for r in rows:
        i = r["id"]
        dono = os.path.basename(os.path.dirname(r["arquivo"]))  # variantes (elites) usam a folha de outro inimigo
        if i in HEROIS or dono not in ids:
            continue
        nome = os.path.basename(r["arquivo"])
        src = os.path.join(ORIG, dono, nome)
        cols, lins = int(r["quadros"]), int(r["direcoes"])
        lado = Image.open(src).height // lins  # lado do quadro HD, lido do original (a rodada é repetível)
        novo = round(lado * FATOR[lado])
        if (dono, nome) not in feitos:
            processa_folha(src, lado, cols, lins, novo).save(os.path.join(SPR, dono, nome))
            feitos.add((dono, nome))
            print(dono, nome, lado, "->", novo)
        r["quadro"] = str(novo)
        r["pivo_x"] = str(novo // 2)
        r["pivo_y"] = str(round(PIVO_Y[i] * novo / lado))
        com_arte.add(i)
    ids = sorted(com_arte)
    for i in ids:
        if i not in com_escala:
            esc_rows.append({"id": i, "escala": "2.5", "nota": "inimigo em pixel art (pixelar_inimigos.py): 1 px da arte = 1 px da grade"})
    for path, rs in ((MAN, rows), (ESC, esc_rows)):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rs[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rs)


PIVO_Y = {}
if __name__ == "__main__":
    # pivô Y original por id (do manifesto HD, antes da primeira rodada); fixo aqui para a rodada ser repetível
    PIVO_Y.update({"ash_hound": 104, "chain_wraith": 116, "cinder_archer": 104, "crypt_bat": 112, "crypt_guardian": 208,
                   "fallen_echo": 117, "ghost_archer": 104, "hollow_sentinel": 104, "ossuary_captain": 119,
                   "ossuary_warden": 156, "skeleton_soldier": 119, "stone_herald": 156, "wandering_ghost": 117})
    main()
