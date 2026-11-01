"""Fatia as folhas geradas (fundo magenta) em folhas de quadros iguais, com fundo transparente.
Uso: python montar.py <pasta_entrada> <pasta_saida>   (entrada: <id>.png do gerar.py; saída: godot/art2d/fx/gelo)
Divide a imagem em N células iguais (N em prompts_gelo.json), tira o magenta, recorta ao maior conteúdo comum e
guarda uma linha de N quadros do mesmo tamanho. Ícones: key + recorte 128 px (use prep_lote.py do HUD)."""
import json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ui_gpt_image"))
from key import key

def main(ent, sai):
    os.makedirs(sai, exist_ok=True)
    itens = json.load(open(os.path.join(os.path.dirname(__file__), "prompts_gelo.json"), encoding="utf-8"))
    for it in itens:
        p = os.path.join(ent, it["id"] + ".png")
        if not os.path.exists(p):
            print("falta", p); continue
        im = key(p); n = it["quadros"]; w = im.width // n
        cel = [im.crop((i * w, 0, (i + 1) * w, im.height)) for i in range(n)]
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
