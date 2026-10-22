"""Pilastra de parede 1,4 x 0,84 x 5,4 m (engrossada 40%): soco de 3 degraus em fiadas de blocos como o pilar v6, cornija de base,
fuste estriado em tambores, capitel em degraus com sino ovolo, quadrifólio e volutas, friso com losangos, dentículos e cornija.
Pivô no centro da base; parede atrás (-Y), frente +Y."""
import bpy, math, random
from _pedra import garantir_material, seguro, poly_loft, profile_loft, curve_levels, rect, cut, crack, fiada
GLB = 'SM_Cripta_Pilastra'
VISTAS = {
    "frente": ((0, 9.5, 2.7), (0, 0, 2.7), 700, 1000),
    "tres_quartos": ((-4.6, 5.6, 3.6), (0, 0, 2.5), 800, 1000),
    "close_base": ((-1.9, 2.5, 1.0), (0, 0, 0.7), 800, 800),
    "close_topo": ((-2.2, 3.6, 4.4), (0, 0, 4.9), 800, 800),
}
HEROI_X, HEROI_Y = 1.9, 1.7
W, D = 1.4, 0.84

def flute_section(w, d, nfl, ch=0.06, fw=0.13, fd=0.05):
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
    o = bpy.context.object; L.bevel_obj(o, 0.008, 1); return L.add(o, m)

def build(L):
    sd, sc = L.stone('escura'), L.stone('clara')
    r = random.Random(5)
    hx, hy = W / 2, D / 2
    # ---- soco: 3 degraus em fiadas (o 1.º em duas fiadas desencontradas), miolo escuro
    fiada(L, hx, hy, 0.0, 0.15, 0.30, 0.38, 0.62, 101, sd, sd, 0.018, 0.6, core=False)
    fiada(L, hx, hy, 0.15, 0.15, 0.30, 0.34, 0.58, 102, sd, sd, 0.018, 0.6)
    fiada(L, 0.63, 0.35, 0.30, 0.25, 0.24, 0.32, 0.52, 103, sd, sd, 0.016, 0.6)
    fiada(L, 0.55, 0.30, 0.55, 0.20, 0.20, 0.28, 0.46, 104, sd, sd, 0.014, 0.55)
    # lajes de tampo dos degraus
    for hx_, hy_, z in ((0.63, 0.35, 0.55), (0.55, 0.30, 0.75)):
        L.chip_corners(L.box((0, 0, z + 0.015), (2 * hx_ - 0.1, 2 * hy_ - 0.05, 0.03), sd, bev=0.01), 2, 0.06, int(z * 100))
    # cornija de base do fuste: dois anéis moldurados
    cb = profile_loft(L, "cornija_base", [(0.75, 1.0, 0.56, 0.05), (0.80, 1.06, 0.60, 0.05), (0.86, 1.06, 0.60, 0.05), (0.88, 1.0, 0.56, 0.05)], m=sc, bev=0.012, seg=2)
    L.chip_corners(cb, 3, 0.09, 12)
    profile_loft(L, "escocia", curve_levels(0.88, 1.0, (1.0, 0.56), (0.94, 0.5), 5, "cove", 0.06), m=sd, bev=0.006)
    # cacos soltos nos degraus
    for sx, sy, s in ((-0.55, 0.38, 0.09), (0.5, 0.40, 0.07), (-0.2, 0.40, 0.05)):
        p = poly_loft(L, "caco", rect(s, s * 0.8, 0.015), 0.30, 0.30 + s * 0.8, 0.7, 0.6, m=sd, bev=0.01)
        p.location = (sx, sy, 0.30 + s * 0.35); p.rotation_euler = (0.2, 0.1, r.uniform(0, 3))
    # ---- fuste: 3 tambores, 6 estrias na frente
    zs = [1.0, 2.15, 3.2]; ze = [2.15, 3.2, 4.15]
    sh = []
    for i, (a, b) in enumerate(zip(zs, ze)):
        k = 1.0 - 0.02 * i
        t = poly_loft(L, f"fuste{i}", flute_section(0.98 * k, 0.54, 6, 0.06 * k), a, b - 0.016, 0.985, 0.985, m=sd, bev=0.008, seg=2)
        sh.append(t)
        if i < 2:
            poly_loft(L, f"junta{i}", rect(1.05 * k, 0.60, 0.06), b - 0.024, b + 0.02, m=sc, bev=0.008)
    for t, n, s, sd_ in ((sh[0], 7, 0.17, 21), (sh[1], 5, 0.14, 22), (sh[2], 5, 0.14, 24)):
        seguro(t, lambda k, t=t, n=n, s=s, sd_=sd_: L.chip_corners(t, n, s, sd_ + 97 * k))
    for t, p0, p1, w, sd_, n in ((sh[1], (0.17, 2.3), (-0.08, 3.1), 0.025, 3, 8), (sh[0], (-0.3, 1.15), (-0.14, 2.05), 0.022, 5, 7), (sh[2], (0.28, 3.3), (0.1, 4.05), 0.022, 8, 7)):
        seguro(t, lambda k, t=t, p0=p0, p1=p1, w=w, sd_=sd_, n=n: crack(t, p0, p1, w=w, depth=0.06, seed=sd_ + k, n=n), 2)
    # ---- capitel: colarinho em degraus, sino ovolo, quadrifólio, volutas
    profile_loft(L, "colar", [(4.15, 1.05, 0.58, 0.06), (4.22, 1.09, 0.62, 0.06), (4.30, 1.09, 0.62, 0.06), (4.34, 1.04, 0.57, 0.06)], m=sc, bev=0.008)
    profile_loft(L, "colar2", [(4.34, 1.12, 0.66, 0.06), (4.44, 1.14, 0.68, 0.06)], m=sd, bev=0.01)
    cap = profile_loft(L, "sino", curve_levels(4.44, 4.88, (1.06, 0.60), (1.30, 0.78), 7, "ovolo", 0.07), m=sd, bev=0.006)
    for dx, dz in ((0.06, 0), (-0.06, 0), (0, 0.06), (0, -0.06)):   # quadrifólio vazado no sino
        cut(cap, (cap.location.x + dx, 0.36, 4.66 + dz), (0.1, 0.08, 0.1), rot=(0, math.radians(r.uniform(0, 90)), 0))
    L.chip_corners(cap, 3, 0.1, 61)
    filete = profile_loft(L, "filete_cap", [(4.88, 1.28, 0.78, 0.05), (4.96, 1.32, 0.82, 0.05)], m=sc, bev=0.01)
    L.chip_corners(filete, 2, 0.08, 62)
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.11, depth=0.58, location=(sx * 0.58, 0, 4.62), rotation=(math.radians(90), 0, 0))
        v = bpy.context.object; L.bevel_obj(v, 0.01, 2); L.add(v, sd)
        cyl_y(L, (sx * 0.58, 0.3, 4.62), 0.07, 0.04, sc)
    # ---- friso e cornija (topo em 5,4)
    poly_loft(L, "arquitrave", rect(1.32, 0.80, 0.04), 4.96, 5.08, m=sd, bev=0.014)
    fr = poly_loft(L, "friso", rect(1.28, 0.76, 0.04), 5.08, 5.26, m=sd, bev=0.01)
    for x in (-0.42, -0.14, 0.14, 0.42):
        cut(fr, (fr.location.x + x, 0.38, 5.17), (0.13, 0.1, 0.13), rot=(0, math.radians(45), 0))
        cyl_y(L, (x, 0.385, 5.17), 0.045, 0.04, sc, 12)
    L.chip_corners(fr, 3, 0.07, 71)
    for i in range(16):
        x = -0.63 + i * 0.084
        poly_loft(L, "dent", rect(0.05, 0.07), 5.26, 5.33, m=sd, bev=0.005, seg=1).location = (x, 0.39, 5.295)
    poly_loft(L, "cornija0", rect(1.34, 0.80, 0.04), 5.26, 5.33, m=sd, bev=0.008, seg=1)
    cor = profile_loft(L, "cornija", [(5.33, 1.34, 0.80, 0.05), (5.36, 1.4, 0.84, 0.05), (5.40, 1.4, 0.84, 0.05)], m=sc, bev=0.016)
    L.chip_corners(cor, 4, 0.12, 31)
    garantir_material(L, sd)
    L.col_box((0, 0, 2.7), (W, D, 5.4))
