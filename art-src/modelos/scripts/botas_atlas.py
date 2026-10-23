"""Atlas 2048 das botas do arqueiro dark. Retangulos (x0, y0, x1, y1) em px, origem no canto superior esquerdo.
FRONT = recorte da bota direita da imagem (arq3d_botas.png, personagem esquerda +X) projetado de frente; a bota -X e espelhada (mesma UV).
Sem dependencias (usado dentro do Blender e no python do venv)."""
import json, os
N = 2048
R = dict(
    front=(0, 0, 640, 2040),
    plain=(640, 0, 1152, 512),       # couro escuro liso (costas e laterais)
    strap=(640, 512, 1152, 768),     # couro marrom das tiras
    metal=(640, 768, 1152, 1024),
    wood=(640, 1024, 1152, 1280),    # sola e salto de madeira
    lining=(640, 1280, 1152, 1408),
)
SRCB = (800, 20, 1100, 992)          # caixa do recorte na imagem de entrada (x0, y0, x1, y1)
_S = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "botas_sil.json")))["rows"]
PY0, PY1 = 26, 984                   # topo do cano e ponta do bico (py na imagem)


def sil(py):
    """(centro, meia-largura) do corpo da bota na imagem na linha py, suavizado."""
    py = int(min(max(py, 30), 980))
    xs = [r for r in _S[max(30, py - 12):min(980, py + 13)] if r]
    if not xs:
        return 940.0, 100.0
    xl = sum(r[0] for r in xs) / len(xs); xr = sum(r[1] for r in xs) / len(xs)
    return (xl + xr) / 2, (xr - xl) / 2


def uv(rect, u, v, pad=6):
    x0, y0, x1, y1 = rect
    x = x0 + pad + u * (x1 - x0 - 2 * pad)
    y = y0 + pad + v * (y1 - y0 - 2 * pad)
    return (x / N, 1.0 - y / N)


def proj_uv(px, py):
    x0, y0, x1, y1 = SRCB
    return uv(R["front"], min(max((px - x0) / (x1 - x0), 0.002), 0.998), min(max((py - y0) / (y1 - y0), 0.002), 0.998), pad=0)
