"""Pilastra de parede 1,0 x 0,6 x 5,4 m: base escalonada com escócia, fuste estriado em tambores, capitel ovolo com volutas e friso com rosetas e dentículos.
Pivô no centro da base; parede atrás (-Y), frente +Y."""
import bpy, math, random
from _pedra import poly_loft, profile_loft, curve_levels, rect, cut, crack
GLB = 'SM_Cripta_Pilastra'
VISTAS = {
    "frente": ((0, 8.5, 2.7), (0, 0, 2.7), 700, 1000),
    "tres_quartos": ((-4.2, 5.2, 3.6), (0, 0, 2.5), 800, 1000),
    "close_base": ((-1.4, 1.9, 0.9), (0, 0, 0.8), 800, 800),
    "close_topo": ((-1.7, 3.2, 4.4), (0, 0, 4.9), 800, 800),
}
HEROI_X, HEROI_Y = 1.6, 1.4
W, D = 1.0, 0.6

def flute_section(w, d, nfl, ch=0.05, fw=0.1, fd=0.042):
    """Seção do fuste: estrias trapezoidais na frente (+Y), lados lisos chanfrados; anti-horário."""
    x, y = w / 2, d / 2
    pts = [(-x + ch, -y), (x - ch, -y), (x, -y + ch), (x, y - ch), (x - ch, y)]
    step = (w - 2 * ch) / nfl
    for i in range(nfl):
        xr = x - ch - i * step; xc = xr - step / 2
        pts += [(xr - (step - fw) / 2, y), (xc + fw * 0.32, y - fd), (xc - fw * 0.32, y - fd), (xr - (step + fw) / 2, y)]
    pts += [(-x + ch, y), (-x, y - ch), (-x, -y + ch)]
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) > 1e-5: out.append(p)
    return out

def cyl_y(L, loc, r, depth, m, sides=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=r, depth=depth, location=loc, rotation=(math.radians(90), 0, 0))
    o = bpy.context.object; L.bevel_obj(o, 0.006, 1); return L.add(o, m)

def build(L):
    sd, sc = L.stone('escura'), L.stone('clara')
    r = random.Random(5)
    # ---- base escalonada: plinto, degrau, toro claro, escócia
    b1 = poly_loft(L, "base1", rect(W, D, 0.045), 0, 0.26, m=sd, bev=0.02)
    b2 = poly_loft(L, "base2", rect(0.92, 0.52, 0.04), 0.26, 0.42, m=sd, bev=0.014)
    profile_loft(L, "toro", [(0.42, 0.88, 0.48, 0.04), (0.45, 0.9, 0.5, 0.04), (0.50, 0.9, 0.5, 0.045), (0.53, 0.86, 0.46, 0.045), (0.55, 0.82, 0.42, 0.04)], m=sc, bev=0.007)
    profile_loft(L, "escocia", curve_levels(0.55, 0.70, (0.82, 0.42), (0.76, 0.395), 5, "cove", 0.05), m=sd, bev=0.005)
    L.chip_corners(b1, 6, 0.17, 14); L.chip_corners(b2, 2, 0.08, 13)
    # lascas soltas sobre o plinto
    for sx, sy, s in ((-0.4, 0.2, 0.06), (0.36, 0.22, 0.05)):
        p = poly_loft(L, "caco", rect(s, s * 0.8, 0.012), 0.26, 0.26 + s * 0.8, 0.7, 0.6, m=sd, bev=0.006, offs=(0, 0)); p.location = (sx, sy, 0.26 + s * 0.35); p.rotation_euler = (0.2, 0.1, r.uniform(0, 3))
    # ---- fuste: 4 tambores estriados, juntas claras, leve entasis
    zs = [0.70, 1.80, 2.92, 3.98]; ze = [1.80, 2.92, 3.98, 4.40]
    sh = []
    for i, (a, b) in enumerate(zip(zs, ze)):
        k = 1.0 - 0.022 * i
        t = poly_loft(L, f"fuste{i}", flute_section(0.74 * k, 0.40, 5, 0.05 * k), a, b - 0.014, 0.985, 0.985, m=sd, bev=0.005, seg=1)
        sh.append(t)
        if i < 3:
            poly_loft(L, f"junta{i}", rect(0.80 * k, 0.45, 0.055), b - 0.022, b + 0.016, m=sc, bev=0.006)
    L.chip_corners(sh[0], 6, 0.15, 21); L.chip_corners(sh[1], 4, 0.09, 22); L.chip_corners(sh[2], 3, 0.08, 24); L.chip_corners(sh[3], 3, 0.07, 23)
    crack(sh[1], (0.13, 1.95), (-0.06, 2.8), w=0.02, depth=0.05, seed=3, n=8)
    crack(sh[0], (-0.22, 0.85), (-0.1, 1.7), w=0.018, depth=0.05, seed=5, n=7)
    crack(sh[2], (0.2, 3.1), (0.08, 3.9), w=0.018, depth=0.05, seed=8, n=7)
    crack(sh[0], (0.0, 0.8), (0.12, 1.05), w=0.014, depth=0.04, seed=9, n=3)
    # ---- colar e capitel
    profile_loft(L, "colar", [(4.40, 0.80, 0.43, 0.05), (4.47, 0.82, 0.45, 0.05), (4.52, 0.80, 0.43, 0.05)], m=sc, bev=0.006)
    cap = profile_loft(L, "equino", curve_levels(4.52, 4.80, (0.76, 0.405), (0.96, 0.52), 6, "ovolo", 0.05), m=sd, bev=0.004)
    profile_loft(L, "filete_cap", [(4.80, 0.94, 0.52, 0.04), (4.86, 0.96, 0.54, 0.04)], m=sc, bev=0.007)
    for sx in (-1, 1):   # volutas laterais: rolos com olho
        for y in (-0.0,):
            bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.08, depth=0.36, location=(sx * 0.40, 0, 4.66), rotation=(math.radians(90), 0, 0))
            v = bpy.context.object; L.bevel_obj(v, 0.008, 2); L.add(v, sd)
            cyl_y(L, (sx * 0.40, 0.2, 4.66), 0.05, 0.03, sc)
    # ---- friso: arquitrave, friso com rosetas, dentículos, cornija dupla
    poly_loft(L, "arquitrave", rect(0.95, 0.55, 0.03), 4.86, 5.02, m=sd, bev=0.012)
    fr = poly_loft(L, "friso", rect(0.93, 0.53, 0.03), 5.02, 5.24, m=sd, bev=0.008)
    for x in (-0.28, 0.0, 0.28):
        cut(fr, (fr.location.x + x, 0.265, 5.13), (0.11, 0.1, 0.11), rot=(0, math.radians(45), 0))   # losango rebaixado
        cyl_y(L, (x, 0.27, 5.13), 0.04, 0.035, sc, 12)                                               # botão claro no centro
    for i in range(12):
        x = -0.44 + i * 0.08
        poly_loft(L, "dent", rect(0.045, 0.06), 5.24, 5.31, m=sd, bev=0.004, seg=1).location = (x, 0.275, 5.275)
    poly_loft(L, "cornija0", rect(0.97, 0.58, 0.03), 5.24, 5.31, m=sd, bev=0.006, seg=1, offs=(0, 0.0)).location.z += 0.0
    cor = profile_loft(L, "cornija", [(5.31, 0.96, 0.57, 0.04), (5.33, 1.0, 0.6, 0.04), (5.40, 1.0, 0.6, 0.04)], m=sc, bev=0.012)
    L.chip_corners(cor, 3, 0.09, 31)
    L.col_box((0, 0, 2.7), (W, D, 5.4))
