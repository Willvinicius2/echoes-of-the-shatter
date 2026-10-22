"""Pedestal baixo 0,6 x 0,6 x 1,4 m: base escalonada, fuste chanfrado com painéis e runa, topo moldurado, esfera de pedra clara."""
import bpy, math
from _pedra import garantir_material, poly_loft, profile_loft, curve_levels, rect, cut, crack, diamond
GLB = 'SM_Cripta_Pedestal'
VISTAS = {
    "frente": ((0, 5.0, 0.8), (0, 0, 0.7), 700, 900),
    "tres_quartos": ((-2.6, 3.0, 1.9), (0, 0, 0.7), 800, 900),
    "close_topo": ((-0.9, 1.3, 1.5), (0, 0, 1.1), 800, 800),
    "close_base": ((-1.0, 1.2, 0.5), (0, 0, 0.3), 800, 800),
}
HEROI_X, HEROI_Y = 1.2, 1.1

def build(L):
    sd, sc = L.stone('escura'), L.stone('clara')
    p1 = poly_loft(L, "p1", rect(0.60, 0.60, 0.04), 0, 0.15, m=sd, bev=0.02)
    p2 = poly_loft(L, "p2", rect(0.54, 0.54, 0.035), 0.15, 0.25, m=sd, bev=0.015)
    profile_loft(L, "toro", [(0.25, 0.50, 0.50, 0.04), (0.27, 0.52, 0.52, 0.04), (0.30, 0.52, 0.52, 0.04), (0.33, 0.48, 0.48, 0.04)], m=sd, bev=0.006)
    profile_loft(L, "escocia", curve_levels(0.33, 0.42, (0.48, 0.48), (0.42, 0.42), 4, "cove", 0.07), m=sd, bev=0.004)
    # fuste chanfrado, dois tambores
    f1 = poly_loft(L, "fuste1", rect(0.42, 0.42, 0.08), 0.42, 0.70, 0.97, 0.97, m=sd, bev=0.011)
    poly_loft(L, "junta", rect(0.45, 0.45, 0.085), 0.69, 0.725, m=sc, bev=0.005)
    f2 = poly_loft(L, "fuste2", rect(0.41, 0.41, 0.078), 0.72, 0.93, 0.98, 0.98, m=sd, bev=0.011)
    # painéis rebaixados com runa em losango nas 4 faces
    for ang in (0, 90, 180, 270):
        a = math.radians(ang); s, c = math.sin(a), math.cos(a)
        horiz = ang % 180 == 0
        for o, z, h in ((f1, 0.56, 0.2), (f2, 0.825, 0.12)):
            cx = o.location.x + s * 0.205; cy = o.location.y - c * 0.205
            cut(o, (cx, cy, z), (0.2, 0.05, h) if horiz else (0.05, 0.2, h))
        diamond(L, 'runa', (s * 0.205, -c * 0.205, 0.56), s, -c, 0.06, 0.016, sc)
    # colar + topo: ovolo + cornija clara + plinto
    profile_loft(L, "colar", [(0.93, 0.43, 0.43, 0.08), (0.97, 0.45, 0.45, 0.08), (1.00, 0.43, 0.43, 0.08)], m=sc, bev=0.005)
    profile_loft(L, "ovolo", curve_levels(1.00, 1.08, (0.41, 0.41), (0.54, 0.54), 5, "ovolo", 0.05), m=sd, bev=0.004)
    top = profile_loft(L, "cornija", [(1.08, 0.58, 0.58, 0.035), (1.16, 0.60, 0.60, 0.035)], m=sd, bev=0.015)
    poly_loft(L, "plinto_topo", rect(0.46, 0.46, 0.035), 1.16, 1.19, m=sd, bev=0.006)
    # pescoço + esfera de pedra clara com cinta
    profile_loft(L, "colo", [(1.19, 0.2, 0.2, 0.05), (1.22, 0.16, 0.16, 0.04), (1.27, 0.16, 0.16, 0.04)], m=sc, bev=0.005)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.135, segments=40, ring_count=24, location=(0, 0, 1.265))
    sp = bpy.context.object
    for p in sp.data.polygons: p.use_smooth = True
    L.add(sp, sc)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.1355, minor_radius=0.006, major_segments=40, minor_segments=8, location=(0, 0, 1.265)); L.add(bpy.context.object, sd)
    L.chip_corners(p1, 6, 0.12, 41); L.chip_corners(p2, 2, 0.06, 42)
    L.chip_corners(f2, 3, 0.06, 43); L.chip_corners(top, 3, 0.1, 44)
    crack(f1, (0.09, 0.45), (-0.03, 0.67), w=0.012, depth=0.03, seed=2, n=5)
    crack(p1, (-0.18, 0.02), (-0.12, 0.13), w=0.012, depth=0.03, seed=7, n=3)
    # lasca e rachadura reais na esfera
    cut(sp, (-0.075, 0.08, 1.335), (0.075, 0.075, 0.075), rot=(0.6, 0.5, 0.7))
    cut(sp, (0.03, 0.125, 1.30), (0.012, 0.03, 0.2), rot=(0, 0.25, 0.35))
    cut(sp, (0.05, 0.115, 1.36), (0.012, 0.03, 0.09), rot=(0, 0.0, -0.5))
    L.chip_corners(f1, 3, 0.07, 51); L.chip_corners(p2, 2, 0.07, 52)
    garantir_material(L, sd)
    L.col_box((0, 0, 0.7), (0.6, 0.6, 1.4))
