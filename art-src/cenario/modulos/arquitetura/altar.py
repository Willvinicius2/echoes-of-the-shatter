"""Altar/plataforma escalonada 2,6 x 2,6 x 0,8 m: soco, moldura, segundo degrau, pedestal central, runa na frente, nichos de vela nos cantos."""
import bpy, math
from _pedra import poly_loft, profile_loft, curve_levels, rect, cut, crack, diamond
GLB = 'SM_Cripta_Altar'
VISTAS = {
    "frente": ((0, 6.2, 1.3), (0, 0, 0.35), 900, 700),
    "tres_quartos": ((-3.6, 4.4, 3.0), (0, 0, 0.3), 900, 800),
    "close_runa": ((-0.9, 2.5, 0.75), (0, 1.3, 0.2), 900, 700),
    "close_canto": ((1.6, 2.5, 1.5), (0.9, 0.9, 0.35), 900, 700),
}
HEROI_X, HEROI_Y = 2.3, 2.4

def build(L):
    sd, sc = L.stone('escura'), L.stone('clara')
    # --- soco (degrau 1): corpo escuro levemente afunilado + moldura clara com laje superior
    b1 = poly_loft(L, "soco", rect(2.60, 2.60, 0.10), 0.0, 0.22, 0.985, 0.985, m=sd, bev=0.016)
    profile_loft(L, "pe", [(0.0, 2.64, 2.64, 0.11), (0.05, 2.64, 2.64, 0.11)], m=sc, bev=0.01)
    profile_loft(L, "ovolo1", curve_levels(0.22, 0.28, (2.52, 2.52), (2.60, 2.60), 4, "ovolo", 0.09), m=sc, bev=0.006)
    lj = poly_loft(L, "laje1", rect(2.58, 2.58, 0.10), 0.28, 0.34, m=sc, bev=0.012)
    # --- nichos de vela nos 4 cantos da laje (reentrância real)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cut(lj, (sx * 1.02, sy * 1.02, 0.34), (0.30, 0.30, 0.10))
            poly_loft(L, "vela_base", rect(0.17, 0.17, 0.05), 0.295, 0.325, 0.85, 0.85, m=sd, c=(0, 0), offs=(0, 0), bev=0.006).location = (sx * 1.02, sy * 1.02, 0.31)
    # --- degrau 2
    b2 = poly_loft(L, "degrau2", rect(1.92, 1.92, 0.08), 0.34, 0.52, 0.985, 0.985, m=sd, bev=0.014)
    profile_loft(L, "escocia2", curve_levels(0.52, 0.56, (1.84, 1.84), (1.90, 1.90), 3, "cove", 0.07), m=sd, bev=0.005)
    lj2 = poly_loft(L, "laje2", rect(2.00, 2.00, 0.08), 0.56, 0.64, m=sc, bev=0.012)
    # filetes de junta nas faces do degrau 2 (painéis rebaixados)
    for ang in (0, 90, 180, 270):
        a = math.radians(ang); s, c = math.sin(a), math.cos(a)
        horiz = ang % 180 == 0
        cut(b2, (s * 0.955, c * 0.955, 0.44), (0.9, 0.06, 0.09) if horiz else (0.06, 0.9, 0.09))
    # --- pedestal central
    poly_loft(L, "ped_plinto", rect(1.12, 1.12, 0.08), 0.64, 0.665, m=sc, bev=0.008)
    p1 = poly_loft(L, "ped_base", rect(0.98, 0.98, 0.07), 0.665, 0.71, 0.93, 0.93, m=sd, bev=0.01)
    profile_loft(L, "ped_escocia", curve_levels(0.71, 0.74, (0.88, 0.88), (0.84, 0.84), 3, "cove", 0.05), m=sd, bev=0.004)
    p2 = poly_loft(L, "ped_topo", rect(0.92, 0.92, 0.06), 0.74, 0.80, 1.0, 1.0, m=sc, bev=0.01)
    cut(p2, (0, 0, 0.80), (0.60, 0.60, 0.02))       # leito raso onde assenta a estátua
    # --- runa na face da frente (+Y) do soco: painel rebaixado, losango central e traços laterais
    fy = 1.30 * 0.992
    cut(b1, (0, 1.30, 0.11), (1.50, 0.10, 0.15))
    yb = 1.30 - 0.05 + 0.005
    diamond(L, "runa_c", (0, yb, 0.11), 0, 1, 0.10, 0.03, sc, 0.004)
    for k, u in enumerate((-0.62, -0.42, 0.42, 0.62)):
        cut(b1, (u, 1.30 - 0.05, 0.11), (0.03, 0.05, 0.11 if k in (0, 3) else 0.07))
    for u in (-0.30, 0.30):
        cut(b1, (u, 1.30 - 0.05, 0.11), (0.12, 0.05, 0.02), rot=(0, math.radians(35), 0))
    # juntas de cantaria nas 4 faces do soco e do degrau 2 (fora do painel da runa)
    for ang in (0, 90, 180, 270):
        a = math.radians(ang); s_, c_ = math.sin(a), math.cos(a)
        for t in (-0.87, -0.48, 0.48, 0.87):
            if ang == 0 and abs(t) < 0.6 and False: continue
            cut(b1, (s_ * 1.30 + c_ * t, c_ * 1.30 - s_ * t, 0.11 + (0.0 if abs(t) > 0.5 else 0)), (0.016, 0.03, 0.23) if ang % 180 == 0 else (0.03, 0.016, 0.23))
        for t in (-0.55, 0.0, 0.55):
            cut(b2, (s_ * 0.96 + c_ * t * 0.0 + (c_ * t), c_ * 0.96 - s_ * t, 0.43), (0.014, 0.03, 0.17) if ang % 180 == 0 else (0.03, 0.014, 0.17))
    # lascas e rachadura
    L.chip_corners(b1, 9, 0.22, 11); L.chip_corners(lj, 7, 0.2, 12)
    L.chip_corners(b2, 4, 0.12, 13); L.chip_corners(lj2, 6, 0.16, 14); L.chip_corners(p2, 1, 0.06, 15)
    crack(b2, (-0.55, 0.50), (-0.4, 0.37), w=0.012, depth=0.03, seed=4, n=3)
    L.col_box((0, 0, 0.4), (2.6, 2.6, 0.8))
