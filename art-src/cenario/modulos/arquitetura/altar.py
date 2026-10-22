"""Altar/plataforma escalonada (soco 2,6; pé irregular 2,9) x 0,8 m: soco, moldura, segundo degrau, pedestal central, runa na frente, nichos de vela nos cantos."""
import bpy, math
from _pedra import poly_loft, profile_loft, curve_levels, rect, cut, crack, diamond
GLB = 'SM_Cripta_Altar'
import random
def irr(w, d, seed, jit=0.02, cmin=0.06, cmax=0.2):
    """Contorno irregular (cantos chanfrados de tamanhos diferentes, meios de lado deslocados), anti-horário."""
    r = random.Random(seed); x, y = w / 2, d / 2; pts = []
    cs = [r.uniform(cmin, cmax) for _ in range(4)]
    # (canto, direção de entrada, saída)
    corners = [((-x, -y), (1, 0), (0, 1)), ((x, -y), (0, 1), (-1, 0)), ((x, y), (-1, 0), (0, -1)), ((-x, y), (0, -1), (1, 0))]
    # lado inferior começa depois do canto 3
    seq = []
    for i, (c, dout, din) in enumerate(corners):
        prev = corners[i - 1]
        # canto i: chega por prev dir, sai por dout
        pass
    for i in range(4):
        c, dout, _ = corners[i]; ch = cs[i]
        nxt = corners[(i + 1) % 4][0]; nch = cs[(i + 1) % 4]
        a = (c[0] + dout[0] * ch, c[1] + dout[1] * ch)
        b = (nxt[0] - dout[0] * nch, nxt[1] - dout[1] * nch)
        pts.append(a)
        nx, ny = dout[1], -dout[0]  # normal para fora
        for t in (0.33, 0.66):
            j = r.uniform(-jit, jit)
            pts.append((a[0] + (b[0] - a[0]) * t + nx * j, a[1] + (b[1] - a[1]) * t + ny * j))
        pts.append(b)
    return pts

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
    b1 = poly_loft(L, "soco", irr(2.60, 2.60, 1, 0.025, 0.08, 0.22), 0.10, 0.30, 0.985, 0.985, m=sd, bev=0.016)
    foot = poly_loft(L, "pe", irr(2.92, 2.92, 7, 0.05, 0.12, 0.34), 0.0, 0.06, 0.97, 0.97, m=sc, bev=0.012)
    foot2 = poly_loft(L, "pe2", irr(2.72, 2.72, 8, 0.03, 0.1, 0.26), 0.06, 0.10, 0.98, 0.98, m=sd, bev=0.01)
    profile_loft(L, "ovolo1", curve_levels(0.30, 0.35, (2.52, 2.52), (2.60, 2.60), 4, "ovolo", 0.09), m=sc, bev=0.006)
    lj = poly_loft(L, "laje1", irr(2.58, 2.58, 2, 0.022, 0.07, 0.2), 0.35, 0.40, m=sc, bev=0.012)
    # --- nichos de vela nos 4 cantos da laje (reentrância real)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cut(lj, (sx * 1.02, sy * 1.02, 0.40), (0.30, 0.30, 0.10))
            poly_loft(L, "vela_base", rect(0.17, 0.17, 0.05), 0.355, 0.385, 0.85, 0.85, m=sd, c=(0, 0), offs=(0, 0), bev=0.006).location = (sx * 1.02, sy * 1.02, 0.37)
    # --- degrau 2
    b2 = poly_loft(L, "degrau2", irr(1.92, 1.92, 3, 0.02, 0.06, 0.16), 0.40, 0.52, 0.985, 0.985, m=sd, bev=0.014)
    profile_loft(L, "escocia2", curve_levels(0.52, 0.56, (1.84, 1.84), (1.90, 1.90), 3, "cove", 0.07), m=sd, bev=0.005)
    lj2 = poly_loft(L, "laje2", irr(2.00, 2.00, 4, 0.02, 0.06, 0.16), 0.56, 0.64, m=sc, bev=0.012)
    # filetes de junta nas faces do degrau 2 (painéis rebaixados)
    for ang in (0, 90, 180, 270):
        a = math.radians(ang); s, c = math.sin(a), math.cos(a)
        horiz = ang % 180 == 0
        cut(b2, (s * 0.955, c * 0.955, 0.46), (0.9, 0.06, 0.09) if horiz else (0.06, 0.9, 0.09))
    # --- pedestal central
    poly_loft(L, "ped_plinto", rect(1.12, 1.12, 0.08), 0.64, 0.665, m=sc, bev=0.008)
    p1 = poly_loft(L, "ped_base", rect(0.98, 0.98, 0.07), 0.665, 0.71, 0.93, 0.93, m=sd, bev=0.01)
    profile_loft(L, "ped_escocia", curve_levels(0.71, 0.74, (0.88, 0.88), (0.84, 0.84), 3, "cove", 0.05), m=sd, bev=0.004)
    p2 = poly_loft(L, "ped_topo", rect(0.92, 0.92, 0.06), 0.74, 0.80, 1.0, 1.0, m=sc, bev=0.01)
    cut(p2, (0, 0, 0.80), (0.60, 0.60, 0.02))       # leito raso onde assenta a estátua
    # --- gravura na face da frente (+Y) do soco: painel fundo, brasão de losangos e runas entalhadas
    cut(b1, (0, 1.30, 0.20), (1.56, 0.16, 0.17))
    yb = 1.30 - 0.08 + 0.004
    diamond(L, "runa_c", (0, yb, 0.20), 0, 1, 0.135, 0.05, sc, 0.004)
    diamond(L, "runa_c2", (0, yb + 0.04, 0.20), 0, 1, 0.07, 0.03, sd, 0.003)
    for k, u in enumerate((-0.68, -0.50, -0.33, 0.33, 0.50, 0.68)):
        h = (0.12, 0.08, 0.10)[k % 3] if k < 3 else (0.10, 0.08, 0.12)[k - 3]
        cut(b1, (u, yb, 0.20), (0.035, 0.09, h))
    for u in (-0.43, 0.43):
        cut(b1, (u, yb, 0.20), (0.15, 0.09, 0.025), rot=(0, math.radians(40), 0))
        cut(b1, (u, yb, 0.20), (0.15, 0.09, 0.025), rot=(0, math.radians(-40), 0))
    # runas nos painéis do degrau 2 (frente) e laterais do soco
    cut(b2, (0, 0.96 - 0.0, 0.46), (0.3, 0.14, 0.10), rot=(0, 0, 0))
    for sgn in (-1, 1):
        cut(b1, (sgn * 1.30, 0.0, 0.20), (0.14, 0.9, 0.14))
        for u in (-0.25, 0.0, 0.25):
            cut(b1, (sgn * 1.26, u, 0.20), (0.1, 0.04, 0.09), rot=(0, math.radians(20 * (1 if u >= 0 else -1)), 0))
    # juntas de cantaria nas 4 faces do soco e do degrau 2 (fora do painel da runa)
    for ang in (0, 90, 180, 270):
        a = math.radians(ang); s_, c_ = math.sin(a), math.cos(a)
        for t in (-0.87, -0.48, 0.48, 0.87):
            if ang == 0 and abs(t) < 0.6 and False: continue
            cut(b1, (s_ * 1.30 + c_ * t, c_ * 1.30 - s_ * t, 0.20 + (0.0 if abs(t) > 0.5 else 0)), (0.016, 0.03, 0.23) if ang % 180 == 0 else (0.03, 0.016, 0.23))
        for t in (-0.55, 0.0, 0.55):
            cut(b2, (s_ * 0.96 + c_ * t * 0.0 + (c_ * t), c_ * 0.96 - s_ * t, 0.43), (0.014, 0.03, 0.17) if ang % 180 == 0 else (0.03, 0.014, 0.17))
    # cantos quebrados de verdade: pedaços grandes faltando
    cut(lj, (1.18, 1.20, 0.40), (0.7, 0.5, 0.3), rot=(0.5, 0.3, 0.6))
    cut(b1, (1.25, 1.25, 0.28), (0.6, 0.45, 0.34), rot=(0.4, 0.5, 0.7))
    cut(foot, (1.46, 1.40, 0.05), (0.60, 0.40, 0.14), rot=(0.3, 0.4, 0.5))
    cut(lj, (-1.22, -1.22, 0.40), (0.6, 0.45, 0.26), rot=(0.2, 0.5, 0.9))
    cut(lj2, (-1.0, 1.0, 0.62), (0.40, 0.30, 0.16), rot=(0.4, 0.2, 0.4))
    # lascas e rachadura
    L.chip_corners(b1, 12, 0.3, 11); L.chip_corners(lj, 9, 0.24, 12); L.chip_corners(foot, 10, 0.3, 21); L.chip_corners(foot2, 6, 0.2, 22)
    L.chip_corners(b2, 5, 0.16, 13); L.chip_corners(lj2, 8, 0.22, 14); L.chip_corners(p2, 1, 0.06, 15)
    crack(b2, (-0.55, 0.50), (-0.4, 0.37), w=0.012, depth=0.03, seed=4, n=3)
    # garante um único material por objeto (boolean pode perder o slot)
    clara = ("laje", "pe", "ovolo", "ped_topo", "ped_plinto", "runa_c")
    for o in L.objs:
        want = sc if (o.name.split(".")[0] in clara) else sd
        if o.name.startswith("runa_c2"): want = sd
        o.data.materials.clear(); o.data.materials.append(want)
    L.col_box((0, 0, 0.4), (2.9, 2.9, 0.8))
