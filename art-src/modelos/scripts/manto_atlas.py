"""Atlas 2048 do torso do arqueiro dark (manto, gola, colete, correias, metal). Retangulos (x0, y0, x1, y1) em pixels, origem no canto superior esquerdo.
Usado por manto_build.py (UV) e manto_tex.py (pintura), sem dependencias."""
N = 2048
FEATHER_CELL = (128, 512)     # 8 colunas x 4 linhas em x 0..1024, y 0..2048; raiz em cima, ponta rosada embaixo
FEATHER_COLS, FEATHER_ROWS = 8, 4
R = dict(
    vest=(1024, 0, 1536, 730),          # recorte da imagem de entrada: colete, correias, fivelas
    plain=(1536, 0, 1792, 128),         # tecido escuro liso (costas e laterais do colete)
    belt=(1536, 128, 2048, 318),        # recorte do cinto de couro
    scarf=(1536, 320, 2048, 830),       # recorte da gola (creme com dobras)
    tabard=(1024, 730, 1280, 1400),     # recorte do painel do tabardo (borda rosada, losango)
    shell=(1280, 730, 1536, 1000),      # base do manto
    metal=(1536, 830, 2048, 1090),
    lining=(1536, 1090, 1792, 1300),
    leather=(1792, 1090, 2048, 1300),   # tira de couro liso (pendente)
)
# recortes na imagem de entrada manto_entrada_rgba.png (x0, y0, x1, y1) e mapeamento imagem -> corpo (m)
SRC = dict(vest=(405, 215, 580, 465), belt=(405, 385, 580, 450), scarf=(420, 80, 560, 215), tabard=(300, 860, 400, 1120))
PX_X0, PX_M, PX_Z0, PX_MZ = 492.0, 0.0017, 215.0, 0.00164      # x = (px-492)*PX_M ; z = 1.46 - (py-215)*PX_MZ


def img_to_xz(px, py):
    return ((px - PX_X0) * PX_M, 1.46 - (py - PX_Z0) * PX_MZ)


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
