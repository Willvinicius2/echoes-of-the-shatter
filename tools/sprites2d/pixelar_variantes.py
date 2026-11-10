#!/usr/bin/env python3
"""Tamanhos por papel dos inimigos em pixel art (decisão do Jev, 10/11/2026), sempre na grade nativa (1 px da arte = 1 px da grade):
inimigos comuns 1,1x e elites 1,5x o tamanho que `pixelar_inimigos.py` dá (fator 0,72 do HD de 128 px). Em vez de esticar o
sprite, reprocessa o original HD em art-src/sprites-hd-originais/ com o fator maior.

- Comuns: as folhas de `<dono>/<dono>_<anim>.png` passam de 92 para 101 px.
- Elites: folhas novas `<dono>/<dono>_elite_<anim>.png` (138 px) e linhas `<id>_elite` no manifesto, usadas pelos elites de
  onda e do portão (o jogo troca a arte; ver Actor2D.usar_arte). Quem não tem folha elite (Cão de Cinza, feito por código)
  segue no caminho antigo.
Uso: python3 tools/sprites2d/pixelar_variantes.py [cores=20]   (repetível: parte sempre dos originais)"""
import csv, os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixelar_inimigos as P

DONOS = ["chain_wraith", "crypt_bat", "ghost_archer", "hollow_sentinel", "skeleton_soldier", "wandering_ghost"]
K_COMUM, K_ELITE = 1.1, 1.5
LADO_HD = 128
PIVO_Y = {"chain_wraith": 116, "cinder_archer": 104, "crypt_bat": 112, "fallen_echo": 117, "ghost_archer": 104, "hollow_sentinel": 104,
          "ossuary_captain": 119, "skeleton_soldier": 119, "wandering_ghost": 117}


def tamanho(k):
    return round(LADO_HD * P.FATOR[LADO_HD] * k)


def main():
    rows = list(csv.DictReader(open(P.MAN, encoding="utf-8")))
    campos = list(rows[0].keys())
    rows = [r for r in rows if not r["id"].endswith("_elite")]
    novos = []
    feitos = set()
    for r in rows:
        dono = os.path.basename(os.path.dirname(r["arquivo"]))
        if dono not in DONOS:
            continue
        nome = os.path.basename(r["arquivo"])
        src = os.path.join(P.ORIG, dono, nome)
        cols, lins = int(r["quadros"]), int(r["direcoes"])
        assert Image.open(src).height // lins == LADO_HD, src
        for k, sufixo in ((K_COMUM, ""), (K_ELITE, "_elite")):
            novo = tamanho(k)
            destino = nome if not sufixo else nome.replace(dono + "_", dono + "_elite_", 1)
            if (dono, destino) not in feitos:
                P.processa_folha(src, LADO_HD, cols, lins, novo, dono == "chain_wraith").save(os.path.join(P.SPR, dono, destino))
                feitos.add((dono, destino))
                print(dono, destino, LADO_HD, "->", novo)
            piv_y = str(round(PIVO_Y[r["id"]] * novo / LADO_HD))
            if not sufixo:
                r["quadro"], r["pivo_x"], r["pivo_y"] = str(novo), str(novo // 2), piv_y
            else:
                e = dict(r)
                e["id"] = r["id"] + "_elite"
                e["arquivo"] = r["arquivo"].replace(dono + "_" + r["anim"], dono + "_elite_" + r["anim"])
                e["quadro"], e["pivo_x"], e["pivo_y"] = str(novo), str(novo // 2), piv_y
                novos.append(e)
    rows += novos
    with open(P.MAN, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    esc = [r for r in csv.DictReader(open(P.ESC, encoding="utf-8")) if not r["id"].endswith("_elite")]
    campos_e = list(esc[0].keys())
    for i in sorted({r["id"] for r in novos}):
        esc.append({"id": i, "escala": "2.5", "nota": "elite em pixel art 1,5x (pixelar_variantes.py): 1 px da arte = 1 px da grade"})
    with open(P.ESC, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos_e, lineterminator="\n")
        w.writeheader()
        w.writerows(esc)


if __name__ == "__main__":
    P.CORES = int(sys.argv[1]) if len(sys.argv) > 1 else P.CORES
    main()
