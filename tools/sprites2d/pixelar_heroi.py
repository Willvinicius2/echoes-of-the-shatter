#!/usr/bin/env python3
"""Passa as folhas pintadas (HD, 128 px) de um herói para a densidade de pixel do arqueiro, com o mesmo método dos
inimigos (`pixelar_inimigos.py`): paleta curta por folha, alfa binário e contorno de 1 px. O desenho é reduzido por
`FATOR` (0,58: o herói fica com cerca de 1,25x a altura do arqueiro, e não do tamanho de um esqueleto) e encaixado no
quadro do arqueiro (92 px, pivô (46, 76)); `sprites_escala.csv` ganha a escala 2.5 (1 px da arte = 1 px da grade).

Os originais HD ficam em art-src/sprites-hd-originais/<id>/ (copiados na primeira rodada) e são sempre a fonte:
rodar de novo regrava os mesmos bytes. Uso: python3 tools/sprites2d/pixelar_heroi.py guerreiro [cores=24]
"""
import csv, os, shutil, sys

heroi = sys.argv[1]
sys.argv = [sys.argv[0]] + sys.argv[2:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixelar_inimigos as P  # noqa: E402
from PIL import Image  # noqa: E402
import numpy as np  # noqa: E402

PIVO_Y_HD = 104
FATOR = 0.58
QUADRO, PIVO = 92, (46, 76)
ARO = (126, 190, 238)   # aro azul-aço: o herói é o único com contorno frio e não se perde entre esqueletos e capas vermelhas


def aro(folha):
    """Contorno de 1 px azul-aço por fora da silhueta, mais um halo de 1 px a 35% (cada quadro separado)."""
    a = np.asarray(folha, dtype=np.uint8).copy()
    op = a[..., 3] > 40
    viz = np.zeros_like(op)
    viz[1:, :] |= op[:-1, :]
    viz[:-1, :] |= op[1:, :]
    viz[:, 1:] |= op[:, :-1]
    viz[:, :-1] |= op[:, 1:]
    borda = viz & ~op
    halo = np.zeros_like(op)
    halo[1:, :] |= borda[:-1, :]
    halo[:-1, :] |= borda[1:, :]
    halo[:, 1:] |= borda[:, :-1]
    halo[:, :-1] |= borda[:, 1:]
    halo &= ~op & ~borda
    a[halo] = (*ARO, 90)
    a[borda] = (*ARO, 255)
    return Image.fromarray(a, "RGBA")


def main():
    orig = os.path.join(P.ORIG, heroi)
    if not os.path.isdir(orig):
        shutil.copytree(os.path.join(P.SPR, heroi), orig, ignore=shutil.ignore_patterns("*.import"))
    rows = list(csv.DictReader(open(P.MAN, encoding="utf-8")))
    for r in rows:
        if r["id"] != heroi:
            continue
        nome = os.path.basename(r["arquivo"])
        src = os.path.join(orig, nome)
        cols, lins = int(r["quadros"]), int(r["direcoes"])
        lado = Image.open(src).height // lins
        novo = round(lado * FATOR)
        peq = P.processa_folha(src, lado, cols, lins, novo)
        dx, dy = PIVO[0] - novo // 2, PIVO[1] - round(PIVO_Y_HD * novo / lado)
        folha = Image.new("RGBA", (cols * QUADRO, lins * QUADRO), (0, 0, 0, 0))
        for li in range(lins):
            for co in range(cols):
                q = peq.crop((co * novo, li * novo, (co + 1) * novo, (li + 1) * novo))
                folha.paste(q, (co * QUADRO + dx, li * QUADRO + dy))
        folha = aro(folha)
        folha.save(os.path.join(P.SPR, heroi, nome))
        r["quadro"] = str(QUADRO)
        r["pivo_x"] = str(PIVO[0])
        r["pivo_y"] = str(PIVO[1])
        print(heroi, nome, lado, "->", novo, "em", QUADRO)
    esc = list(csv.DictReader(open(P.ESC, encoding="utf-8")))
    if heroi not in {e["id"] for e in esc}:
        esc.append({"id": heroi, "escala": "2.5", "nota": "heroi em pixel art (pixelar_heroi.py): 1 px da arte = 1 px da grade"})
    for path, rs in ((P.MAN, rows), (P.ESC, esc)):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rs[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rs)


if __name__ == "__main__":
    main()
