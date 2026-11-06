#!/usr/bin/env python3
"""Pixela os renders 3D do guerreiro (art-src/personagens/guerreiro/render_guerreiro.py) e monta as folhas.

Uso: python3 tools/sprites2d/montar_guerreiro_3d.py <pasta_render> [pasta_saida]
Quadros de 3x (276 px) -> 92 px (média por caixa), alfa binário, paleta única de PALETA cores calculada sobre todos
os quadros (mesma paleta em todas as animações), contorno escuro de 1 px (por fora e entre partes escuras não).
Folhas: quadro 92, pivô (46,76), linhas S, SE, E, NE, N. idle/hit/dodge/run/attack/death como o arqueiro
(hit derivado do idle: recuo + clarão).
"""
import glob, os, sys
import numpy as np
from PIL import Image

Q = 92
SS = 3
PALETA = 26
DIRS = ["south", "south-east", "east", "north-east", "north"]
N = {"idle": 6, "run": 6, "attack": 6, "dodge": 6, "death": 6}
CONTORNO = (22, 14, 26)
RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")


def carregar(src, anim, d, i):
    return Image.open(os.path.join(src, anim, f"{d}_{i}.png")).convert("RGBA")


def reduzir(im):
    a = np.asarray(im).astype(float)
    al = a[..., 3:4] / 255.0
    pre = a[..., :3] * al
    h = Q
    pre = pre.reshape(h, SS, h, SS, 3).sum((1, 3))
    al2 = al.reshape(h, SS, h, SS, 1).sum((1, 3))
    cor = pre / np.maximum(al2, 1e-6)
    cobertura = al2[..., 0] / (SS * SS)
    return cor, cobertura


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, "godot", "art2d", "sprites", "guerreiro")
    quadros = {}
    pix = []
    for anim in N:
        for d in DIRS:
            for i in range(N[anim]):
                cor, cob = reduzir(carregar(src, anim, d, i))
                quadros[(anim, d, i)] = (cor, cob)
                m = cob > 0.5
                pix.append(cor[m])
    todos = np.concatenate(pix).astype(np.uint8)
    # paleta por median cut do PIL sobre uma imagem com todos os pixels opacos
    lado = int(np.ceil(np.sqrt(len(todos))))
    buf = np.zeros((lado * lado, 3), np.uint8)
    buf[: len(todos)] = todos
    pal_im = Image.fromarray(buf.reshape(lado, lado, 3)).quantize(PALETA, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(pal_im.getpalette()[: PALETA * 3], np.uint8).reshape(-1, 3)

    def pixelar(cor, cob):
        m = cob > 0.5
        d2 = ((cor[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(-1)
        idx = d2.argmin(-1)
        rgb = pal[idx]
        res = np.zeros((Q, Q, 4), np.uint8)
        res[..., :3] = rgb
        res[..., 3] = np.where(m, 255, 0)
        # contorno externo de 1 px
        viz = np.zeros_like(m)
        viz[1:, :] |= m[:-1, :]
        viz[:-1, :] |= m[1:, :]
        viz[:, 1:] |= m[:, :-1]
        viz[:, :-1] |= m[:, 1:]
        borda = viz & ~m
        res[borda] = (*CONTORNO, 255)
        return Image.fromarray(res, "RGBA")

    feitos = {k: pixelar(*v) for k, v in quadros.items()}

    def salvar(nome, linhas):
        n = len(linhas[0])
        S = Image.new("RGBA", (Q * n, Q * 5), (0, 0, 0, 0))
        for r, row in enumerate(linhas):
            for c, im in enumerate(row):
                S.alpha_composite(im, (c * Q, r * Q))
        os.makedirs(out, exist_ok=True)
        S.save(os.path.join(out, f"guerreiro_{nome}.png"))
        print(nome, n, "quadros")

    def deslocar(im, dx, dy):
        o = Image.new("RGBA", im.size, (0, 0, 0, 0))
        o.alpha_composite(im, (dx, dy))
        return o

    def flash(im, k):
        a = im.getchannel("A")
        br = Image.new("RGBA", im.size, (255, 255, 255, 255))
        return Image.composite(Image.blend(im, br, k), im, a)

    for anim in N:
        salvar({"idle": "idle", "run": "run", "attack": "attack", "dodge": "dodge", "death": "death"}[anim],
               [[feitos[(anim, d, i)] for i in range(N[anim])] for d in DIRS])
    DX = {"south": 0, "south-east": 1, "east": 1, "north-east": 1, "north": 0}
    salvar("hit", [[flash(deslocar(feitos[("idle", d, 0)], -DX[d] * s, 0), k) for s, k in ((1, 0.8), (2, 0.4), (1, 0.0))] for d in DIRS])


if __name__ == "__main__":
    main()
