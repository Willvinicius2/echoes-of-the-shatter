"""Atlas 2048 do torso do arqueiro dark (manto, gola, colete, correias, metal). Retangulos (x0, y0, x1, y1) em pixels, origem no canto superior esquerdo.
Usado por manto_build.py (UV) e manto_tex.py (pintura), sem dependencias."""
N = 2048
FEATHER_CELL = (128, 512)     # 8 colunas x 4 linhas em x 0..1024, y 0..2048; raiz em cima, ponta rosada embaixo
FEATHER_COLS, FEATHER_ROWS = 8, 4
R = dict(
    leather=(1024, 0, 2048, 256),
    cloth=(1024, 256, 2048, 640),
    panel=(1024, 640, 1536, 1664),
    scarf=(1536, 640, 2048, 1152),
    metal=(1536, 1152, 2048, 1408),
    emblem=(1536, 1408, 1792, 1664),
    shell=(1024, 1664, 1536, 2048),
    lining=(1792, 1408, 2048, 1664),
)


def uv(rect, u, v, pad=6):
    """u, v em [0,1] dentro do retangulo (v = 0 no topo da imagem) -> UV do Blender (origem embaixo)."""
    x0, y0, x1, y1 = rect
    x = x0 + pad + u * (x1 - x0 - 2 * pad)
    y = y0 + pad + v * (y1 - y0 - 2 * pad)
    return (x / N, 1.0 - y / N)


def feather_uv(cell, u, t):
    c, r = cell % FEATHER_COLS, cell // FEATHER_COLS
    w, h = FEATHER_CELL
    return uv((c * w, r * h, (c + 1) * w, (r + 1) * h), u, t, pad=3)
