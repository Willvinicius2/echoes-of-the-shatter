"""Atlas 2048 das bracadeiras/luvas do arqueiro dark. Retangulos (x0, y0, x1, y1) em px, origem no canto superior esquerdo."""
N = 2048
R = dict(
    leather=(0, 0, 1024, 1536),        # couro do antebraco e da luva: u = angulo em volta do eixo (0 = lado de dentro, 0.5 = dorso), v = cuff -> pontas dos dedos
    strap=(1024, 0, 2048, 256),        # cintas: u ao longo, v atravessado (borda cobre nos dois lados)
    metal=(1024, 256, 1536, 768),      # ponta de flecha 512x512 (u,v = forma normalizada ARROW) + canto liso p/ fivelas
    rose=(1536, 256, 2048, 512),       # vazado rosado dentro das pontas de flecha
    dark=(1536, 512, 2048, 768),       # couro liso escuro (forro, aba interna)
)


def uv(rect, u, v, pad=3):
    x0, y0, x1, y1 = rect
    x = x0 + pad + u * (x1 - x0 - 2 * pad)
    y = y0 + pad + v * (y1 - y0 - 2 * pad)
    return (x / N, 1.0 - y / N)

# ponta de flecha: silhueta tracada na imagem de entrada (recorte x 395..600, y 105..395 de arq3d_bracadeiras.png, pixels do recorte).
# A malha (brac_build.py) e a textura (brac_tex.py) usam as MESMAS coordenadas normalizadas (x, y em -1..1 dentro da caixa ARROW_BOX).
ARROW_CROP_ORIGIN = (395, 105)
ARROW_PX = [(86, 8), (102, 52), (124, 75), (150, 108), (197, 120), (165, 142), (145, 190), (129, 282), (107, 220), (75, 187), (10, 150),
            (47, 152), (65, 115), (70, 80)]
_xs = [p[0] for p in ARROW_PX]; _ys = [p[1] for p in ARROW_PX]
ARROW_BOX = (min(_xs), min(_ys), max(_xs), max(_ys))
_cx, _cy = (ARROW_BOX[0] + ARROW_BOX[2]) / 2, (ARROW_BOX[1] + ARROW_BOX[3]) / 2
_hw, _hh = (ARROW_BOX[2] - ARROW_BOX[0]) / 2, (ARROW_BOX[3] - ARROW_BOX[1]) / 2
ARROW = [((x - _cx) / _hw, (y - _cy) / _hh) for x, y in ARROW_PX]
