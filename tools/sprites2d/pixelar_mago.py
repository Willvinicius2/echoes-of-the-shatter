#!/usr/bin/env python3
"""Mago em pixel art, sem serviço pago: as folhas HD pintadas (128 px, art-src/sprites-hd-originais/mago/) passam pelo
mesmo redutor dos inimigos (`pixelar_inimigos.processa_folha`: redução por caixa, paleta curta por folha, alfa binário e
contorno de 1 px) e são encaixadas no quadro de 92 px do Arqueiro, com os pés no pivô (46, 76). O fator deixa o corpo do
Mago na altura do corpo do Arqueiro (o cajado passa da cabeça). O manifesto e `sprites_escala.csv` são ajustados aqui.

Os originais HD são sempre a fonte: rodar de novo regrava os mesmos bytes.
Uso: python3 tools/sprites2d/pixelar_mago.py [pasta_saida]   (padrão: godot/art2d/sprites/mago)
"""
import csv, os, sys
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.argv, _args = [sys.argv[0], "24"], sys.argv[1:]   # 24 cores por folha (o módulo lê a contagem de sys.argv)
import pixelar_inimigos as redutor  # noqa: E402

R = os.path.join(AQUI, "..", "..")
ORIG = os.path.join(R, "art-src", "sprites-hd-originais", "mago")
SAIDA = _args[0] if _args else os.path.join(R, "godot", "art2d", "sprites", "mago")
MAN = os.path.join(R, "godot", "data2d", "sprites_manifest.csv")
ESC = os.path.join(R, "godot", "data2d", "sprites_escala.csv")
LADO_HD, PIVO_HD = 128, (64, 104)
FATOR = 0.66
QUADRO, PIVO = 92, (46, 76)
ANIMS = {"idle": 6, "run": 8, "attack": 6, "dodge": 6, "hit": 3, "death": 8}
LINHAS = 5


def montar(anim, cols):
    novo = round(LADO_HD * FATOR)
    folha = redutor.processa_folha(os.path.join(ORIG, f"mago_{anim}.png"), LADO_HD, cols, LINHAS, novo)
    dx, dy = PIVO[0] - round(PIVO_HD[0] * FATOR), PIVO[1] - round(PIVO_HD[1] * FATOR)
    out = Image.new("RGBA", (cols * QUADRO, LINHAS * QUADRO), (0, 0, 0, 0))
    for r in range(LINHAS):
        for c in range(cols):
            q = folha.crop((c * novo, r * novo, (c + 1) * novo, (r + 1) * novo))
            bb = q.getchannel("A").getbbox()
            assert bb, f"quadro vazio: {anim} linha {r} coluna {c}"
            assert bb[0] + dx >= 1 and bb[1] + dy >= 1 and bb[2] + dx <= QUADRO - 1 and bb[3] + dy <= QUADRO - 1, \
                f"desenho encosta na borda: {anim} linha {r} coluna {c} {bb}"
            out.paste(q, (c * QUADRO + dx, r * QUADRO + dy))
    return out


def main():
    os.makedirs(SAIDA, exist_ok=True)
    for anim, cols in ANIMS.items():
        montar(anim, cols).save(os.path.join(SAIDA, f"mago_{anim}.png"))
        print("mago", anim, cols)
    if _args:
        return   # saída de revisão: não mexe nos dados do jogo
    rows = list(csv.DictReader(open(MAN, encoding="utf-8")))
    for r in rows:
        if r["id"] == "mago":
            r["quadro"], r["pivo_x"], r["pivo_y"] = str(QUADRO), str(PIVO[0]), str(PIVO[1])
    esc = list(csv.DictReader(open(ESC, encoding="utf-8")))
    if not any(r["id"] == "mago" for r in esc):
        esc.insert(1, {"id": "mago", "escala": "2.5", "nota": "mago em pixel art (pixelar_mago.py): 1 px da arte = 1 px da grade como o arqueiro"})
    for path, rs in ((MAN, rows), (ESC, esc)):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rs[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rs)


if __name__ == "__main__":
    main()
