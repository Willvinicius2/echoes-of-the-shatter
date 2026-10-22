"""Arco da Cripta: moldura de passagem (vão 6,0 x 4,8 m), 9,0 x 1,2 x 5,4 m.
Arco abatido (segmento de círculo) de aduelas de pedra clara com fecho, lábios em relevo, pilastras com capitel nas ombreiras,
tímpano e ombreiras de cantaria irregular (pedra escura), rodapé e cornija do módulo parede, brasão raso no fecho.
Pivô no centro da base; frente = +Y. Colisão só nas ombreiras e acima de 4,8 m."""
import bpy, bmesh, math
from mathutils import Vector

GLB = "SM_Cripta_Arco"
HEROI_X, HEROI_Y = -1.7, 2.4
VISTAS = {
    "frente": ((0, 15.5, 2.9), (0, 0, 2.7), 800, 900),
    "tres_quartos": ((-8.5, 8.5, 5.2), (0, 0, 2.6), 900, 900),
    "close": ((-1.6, 3.4, 4.7), (0, 0.5, 4.6), 900, 800),
    "borda": ((7.5, 2.5, 4.0), (4.5, 0.2, 3.9), 800, 700),
    "close_ombreira": ((-6.8, 3.2, 2.0), (-3.7, 0.5, 1.7), 900, 800),
}

HALF = 0.5            # face da cantaria (y); rodapé/cornija chegam a 0.6
GAP = 0.014           # junta
SPAN = 3.0            # meio vão
ZS = 3.3              # linha de imposta
ZC = 4.8              # chave (intradorso)
SAG = ZC - ZS
R_IN = (SPAN ** 2 + SAG ** 2) / (2 * SAG)
ZCEN = ZC - R_IN
DEPTH = 0.5
R_OUT = R_IN + DEPTH
X_HOOD = None         # calculado: onde o extradorso cruza 4,7


def build(L):
    import random
    global X_HOOD
    cl = L.stone("clara"); es = L.stone("escura"); fe = L.stone("ferro")
    blocks = []
    X_HOOD = math.sqrt(max(R_OUT ** 2 - (4.7 - ZCEN) ** 2, 0))

    # ------------------------------------------------------------ utilidades
    def mesh_obj(name, bm, center, m):
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
        o.location = center
        for p in me.polygons: p.use_smooth = False
        o['m'] = m.name
        return L.add(o, m)

    def manifold_ok(o):
        bm = bmesh.new(); bm.from_mesh(o.data)
        ok = all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True) > 1e-5
        bm.free(); return ok

    def safe_chip(o, n, size, seed):
        bpy.context.view_layer.objects.active = o
        backup = o.data.copy()
        try:
            L.chip_corners(o, n, size, seed)
            if manifold_ok(o):
                bpy.data.meshes.remove(backup); return True
        except Exception:
            pass
        old = o.data; o.data = backup; bpy.data.meshes.remove(old); return False

    def prism(poly, y0, y1, m, seed, rough=0.015, bev=0.032, chips=0, csize=0.14, cuts=1, wob=0.01, track=True):
        """Prisma de pedra: polígono em (x,z) extrudado de y0 a y1, cantos tortos, faces cinzeladas, bisel e lascas."""
        r = random.Random(seed)
        pts = [(max(-4.5, min(4.5, x + r.uniform(-wob, wob))), z + r.uniform(-wob, wob)) for x, z in poly]
        xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
        cx = (min(xs) + max(xs)) / 2; cz = (min(zs) + max(zs)) / 2; cy = (y0 + y1) / 2
        bm = bmesh.new()
        vf = [bm.verts.new((x - cx, y1 - cy, z - cz)) for x, z in pts]
        vb = [bm.verts.new((x - cx, y0 - cy, z - cz)) for x, z in pts]
        n = len(pts)
        faces = [bm.faces.new(vf), bm.faces.new(vb[::-1])]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((vf[i], vf[j], vb[j], vb[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
        if cuts:
            bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
        ph = [r.uniform(0, 6.28) for _ in range(4)]; fq = [r.uniform(3, 6) for _ in range(2)]
        for v in bm.verts:
            if abs(v.co.y - (y1 - cy)) < 1e-5 or abs(v.co.y - (y0 - cy)) < 1e-5:
                nz = 0.6 * math.sin(v.co.x * fq[0] + ph[0]) * math.cos(v.co.z * fq[1] + ph[1]) + 0.2 * math.sin(v.co.x * 11 + v.co.z * 13 + ph[2])
                v.co.y += rough * nz + r.uniform(-rough, rough) * 0.12
        o = mesh_obj("bloco", bm, (cx, cy, cz), m)
        bpy.context.view_layer.objects.active = o
        if bev: L.bevel_obj(o, bev * r.uniform(0.8, 1.25), 2, 30)
        if not chips and r.random() < 0.4: chips = 1
        if chips:
            safe_chip(o, chips * 2, csize * 1.15, seed + 77)
        if track: blocks.append(o)
        return o

    def xprism(profile, x0, x1, m, seed, bev=0.015, chips=0, csize=0.12):
        """Perfil em (y,z) extrudado ao longo de X (rodapé e cornija)."""
        r = random.Random(seed)
        ys = [p[0] for p in profile]; zs = [p[1] for p in profile]
        cy = (min(ys) + max(ys)) / 2; cz = (min(zs) + max(zs)) / 2; cx = (x0 + x1) / 2
        bm = bmesh.new()
        va = [bm.verts.new((x0 - cx + r.uniform(-.01, .01), y - cy, z - cz)) for y, z in profile]
        vb = [bm.verts.new((x1 - cx + r.uniform(-.01, .01), y - cy, z - cz)) for y, z in profile]
        n = len(profile)
        bm.faces.new(va[::-1]); bm.faces.new(vb)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((va[i], va[j], vb[j], vb[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
        o = mesh_obj("perfil", bm, (cx, cy, cz), m)
        bpy.context.view_layer.objects.active = o
        L.bevel_obj(o, bev, 2, 30)
        safe_chip(o, max(chips, 1) * 2, csize * 1.15, seed + 5)
        blocks.append(o)
        return o

    def arc_pts(rad, ta, tb, side, n):
        """Pontos do arco de círculo de raio rad entre ângulos ta e tb (graus a partir da vertical)."""
        out = []
        for i in range(n + 1):
            t = math.radians(ta + (tb - ta) * i / n)
            out.append((side * rad * math.sin(t), ZCEN + rad * math.cos(t)))
        return out

    def ze(x):      # extradorso
        a = abs(x)
        return ZCEN + math.sqrt(R_OUT ** 2 - a * a) if a < R_OUT * math.sin(math.acos((ZS - ZCEN) / R_OUT)) else ZS

    X_SPR = R_OUT * math.sin(math.acos((ZS - ZCEN) / R_OUT))   # x do extradorso na imposta

    # ------------------------------------------------------------ núcleo escuro (argamassa/atrás das juntas)
    core_pts = [(-4.5, 0.45), (-SPAN, 0.45), (-SPAN, ZS)] + arc_pts(R_IN + 0.06, -math.degrees(math.asin(SPAN / R_IN)), math.degrees(math.asin(SPAN / R_IN)), 1, 24)[0:0]
    arc = []
    tmax = math.asin(SPAN / R_IN)
    for i in range(25):
        t = -tmax + 2 * tmax * i / 24
        arc.append(((R_IN + 0.05) * math.sin(t) * 1.0, ZCEN + (R_IN + 0.05) * math.cos(t)))
    arc[0] = (-SPAN - 0.03, ZS); arc[-1] = (SPAN + 0.03, ZS)
    core = [(-4.47, 0.46), (-SPAN - 0.03, 0.46)] + arc + [(SPAN + 0.03, 0.46), (4.47, 0.46), (4.47, 5.28), (-4.47, 5.28)]
    # polígono não-convexo: construído à parte, sem subdivisão
    co = prism(core, -0.47, 0.47, es, 3, rough=0, bev=0, cuts=0, wob=0, track=False)

    # ------------------------------------------------------------ cantaria (ombreiras e tímpano)
    def masonry(xa, xb, courses, low, up, joints, seed, m, wmin=0.7, wmax=1.5, front=HALF, pil=None, chips=0.35):
        r = random.Random(seed)
        for ci, (z0, z1) in enumerate(courses):
            xs = [xa]
            x = xa
            while x < xb - 1e-6:
                nxt = x + r.uniform(wmin, wmax)
                # junta obrigatória mais próxima
                for j in joints:
                    if x + 0.15 < j < nxt + 0.1: nxt = j; break
                if xb - nxt < wmin * 0.55: nxt = xb
                x = min(nxt, xb); xs.append(x)
            for pi in range(len(xs) - 1):
                p0, p1 = xs[pi], xs[pi + 1]
                a = p0 + (GAP if pi > 0 else 0); b = p1 - (GAP if pi < len(xs) - 2 else 0)
                lo, hi = z0 + GAP, z1 - GAP
                n = 10
                samp = []
                for k in range(n + 1):
                    x = a + (b - a) * k / n
                    bot = max(lo, low(x) + GAP); top = min(hi, up((a + b) / 2))
                    if top - bot > 0.07: samp.append((x, bot, top))
                if len(samp) < 2 or max(s[2] - s[1] for s in samp) < 0.16: continue
                poly = [(s[0], s[1]) for s in samp] + [(s[0], s[2]) for s in samp[::-1]]
                # remove pontos colineares do topo (só mantém extremos se plano)
                yf = front
                if pil and (xs[pi + 1] <= pil[0] + 1e-6): yf = pil[1]
                sd = int(seed * 100 + ci * 13 + pi * 7)
                prism(poly, -yf, yf, m, sd, chips=1 if r.random() < chips else 0, csize=r.uniform(0.1, 0.2))

    # ombreiras (esq/dir independentes: assimetria)
    def ombreiras(side, seed):
        r = random.Random(seed)
        hs = []
        total = ZS - 0.45
        n = 6
        raw = [r.uniform(0.38, 0.58) for _ in range(n)]
        k = total / sum(raw); z = 0.45; courses = []
        for h in raw:
            courses.append((z, z + h * k)); z += h * k
        courses[-1] = (courses[-1][0], ZS)
        xa, xb = SPAN, 4.5
        # espelhamos criando em coordenadas positivas e invertendo X dentro da prism via trocar sinais
        masonry_side(side, xa, xb, courses, seed)
        return courses

    def masonry_side(side, xa, xb, courses, seed):
        r = random.Random(seed)
        for ci, (z0, z1) in enumerate(courses):
            # quoins alternados na ombreira: tijolos longos e curtos
            cuts = [xa]
            long_first = (ci % 2 == 0)
            first = r.uniform(0.85, 1.05) if long_first else r.uniform(0.45, 0.6)
            x = xa + first
            while xb - x > 0.35:
                cuts.append(x); x += r.uniform(0.5, 0.95)
            cuts.append(xb)
            if len(cuts) > 2 and cuts[-1] - cuts[-2] < 0.3: cuts.pop(-2)
            for pi in range(len(cuts) - 1):
                p0, p1 = cuts[pi], cuts[pi + 1]
                a = p0 + (GAP if pi > 0 else 0.0); b = p1 - (GAP if pi < len(cuts) - 2 else 0.0)
                lo, hi = z0 + GAP, z1 - GAP
                if ci == 0: lo = z0 - 0.02
                yf = 0.56 if (p1 <= xa + 0.62 and p0 <= xa + 0.01 and pi == 0 and False) else HALF
                poly = [(side * a, lo), (side * b, lo), (side * b, hi), (side * a, hi)]
                if side < 0: poly = poly[::-1]
                prism(poly, -yf, yf, es, int(seed * 31 + ci * 17 + pi * 5), chips=1 if r.random() < 0.85 else 0, csize=r.uniform(0.1, 0.2))

    ombreiras(-1, 11); ombreiras(1, 23)

    # tímpano: acima do extradorso
    low = lambda x: ze(x)
    up = lambda xm: 5.3 if abs(xm) < X_HOOD else 4.7
    t_courses = [(ZS, 3.78), (3.78, 4.25), (4.25, 4.7), (4.7, 5.3)]
    for side, sd in ((-1, 41), (1, 43)):
        # trabalhamos em coordenadas positivas e espelhamos por inversão de x no polígono
        r = random.Random(sd)
        for ci, (z0, z1) in enumerate(t_courses):
            xs = [0.0]
            joints = [X_HOOD, X_SPR, SPAN]
            x = 0.0
            while x < 4.5 - 1e-6:
                nxt = x + r.uniform(0.7, 1.5)
                for j in joints:
                    if x + 0.12 < j < nxt + 0.1: nxt = j; break
                if 4.5 - nxt < 0.4: nxt = 4.5
                x = min(nxt, 4.5); xs.append(x)
            for pi in range(len(xs) - 1):
                p0, p1 = xs[pi], xs[pi + 1]
                a = p0 + (GAP if pi > 0 else 0.02); b = p1 - (GAP if pi < len(xs) - 2 else 0.0)
                lo, hi = z0 + GAP, z1 - GAP
                n = 10; samp = []
                topv = 5.3 if (a + b) / 2 < X_HOOD else 4.7
                for k in range(n + 1):
                    x = a + (b - a) * k / n
                    bot = max(lo, ze(x) + GAP + 0.004); top = min(hi, topv)
                    if top - bot > 0.07: samp.append((x, bot, top))
                if len(samp) < 2 or max(s[2] - s[1] for s in samp) < 0.15: continue
                poly = [(side * s[0], s[1]) for s in samp] + [(side * s[0], s[2]) for s in samp[::-1]]
                if side < 0: poly = poly[::-1]
                prism(poly, -HALF, HALF, es, int(sd * 97 + ci * 11 + pi * 3), chips=1 if r.random() < 0.8 else 0, csize=r.uniform(0.1, 0.18))

    # ------------------------------------------------------------ arco: aduelas, lábios, fecho
    tin = math.degrees(math.asin(SPAN / R_IN))
    tspr_out = math.degrees(math.acos((ZS - ZCEN) / R_OUT))
    for side, sd in ((-1, 5), (1, 6)):
        r = random.Random(sd)
        edges = [45.0, 36.4, 28.4, 19.6, 10.0]
        edges = [edges[0]] + [e + r.uniform(-0.9, 0.9) for e in edges[1:-1]] + [edges[-1]]
        # arrancamento (horizontal na imposta)
        a_in = arc_pts(R_IN, tin, edges[0], side, 6)
        a_out = arc_pts(R_OUT, edges[0], tspr_out, side, 6)
        poly = a_in + a_out + [(side * SPAN, ZS)][0:0]
        poly = [(side * SPAN, ZS)] + a_in[1:] + a_out + []
        if side < 0: poly = poly[::-1]
        prism(poly, -HALF, HALF, cl, sd * 7, chips=1, csize=0.16, wob=0.006)
        # aduelas
        for i in range(4):
            ta, tb = edges[i], edges[i + 1]
            ro = R_OUT + r.uniform(-0.025, 0.025); ri = R_IN + r.uniform(-0.012, 0.012)
            ta2 = ta - 0.25; tb2 = tb + 0.25
            poly = arc_pts(ri, ta2, tb2, side, 4) + arc_pts(ro, tb2, ta2, side, 4)
            if side < 0: poly = poly[::-1]
            yf = HALF + r.uniform(-0.02, 0.02)
            prism(poly, -yf, yf + r.uniform(-0.01, 0.015), cl, sd * 100 + i, chips=1, csize=0.15, wob=0.005)
        # lábios em relevo (frente e trás), juntas desencontradas
        le = [50.5, 41.0, 32.0, 23.0, 15.0, 11.4]
        le = [le[0]] + [e + r.uniform(-1.0, 1.0) for e in le[1:-1]] + [le[-1]]
        for i in range(len(le) - 1):
            ta, tb = le[i] - 0.3, le[i + 1] + 0.3
            ro = R_OUT + 0.012; ri = R_OUT - 0.27 + r.uniform(-0.02, 0.02)
            poly = arc_pts(ri, ta, tb, side, 4) + arc_pts(ro, tb, ta, side, 4)
            if side < 0: poly = poly[::-1]
            for face in (1, -1):
                y0, y1 = (HALF - 0.05, 0.592) if face > 0 else (-0.592, -HALF + 0.05)
                prism(poly, y0, y1, cl, sd * 300 + i * 2 + (face > 0), rough=0.006, bev=0.02, chips=0, wob=0.004)

    # fecho (chave): cunha alta que sobe até a cornija
    r = random.Random(9)
    tk = 10.0
    key = arc_pts(R_IN - 0.06, -tk, tk, 1, 3) + arc_pts(R_OUT + 0.1, tk, -tk, 1, 3)
    prism(key, -HALF, HALF, cl, 901, chips=1, csize=0.12, wob=0.004)
    # placa frontal do fecho, brasão raso
    plate = arc_pts(R_IN + 0.04, -8.8, 8.8, 1, 3) + arc_pts(R_OUT + 0.02, 8.8, -8.8, 1, 3)
    for face in (1, -1):
        y0, y1 = (HALF - 0.04, 0.593) if face > 0 else (-0.593, -HALF + 0.04)
        prism(plate, y0, y1, cl, 910 + face, rough=0.004, bev=0.02, wob=0.003)
        yy = 0.6 if face > 0 else -0.6
        cx, cz = 0.0, 5.07
        def rune(loc, size, rot=0.0):
            L.box((loc[0], yy + face * (size[1] * 0.5 - 0.012), loc[1]), size, es, rot=(0, rot, 0), bev=0.004, seg=1)
        # losango + haste + pontos (relevo de 2 cm)
        rune((cx, cz), (0.30, 0.03, 0.30), math.radians(45))
        rune((cx, cz), (0.12, 0.04, 0.12), math.radians(45))
        rune((cx, cz - 0.30), (0.04, 0.03, 0.16))
        rune((cx, cz + 0.28), (0.04, 0.03, 0.12))
        rune((cx - 0.27, cz), (0.12, 0.03, 0.04)); rune((cx + 0.27, cz), (0.12, 0.03, 0.04))

    # mísulas: pilastra + capitel em degraus sob a imposta
    for side in (-1, 1):
        for face in (1, -1):
            for k, (zb, zt, xe, ye) in enumerate(((3.12, 3.3, 3.9, 0.592), (2.94, 3.12, 3.62, 0.585), (2.80, 2.94, 3.38, 0.57))):
                poly = [(side * SPAN, zb), (side * xe, zb), (side * xe, zt), (side * SPAN, zt)]
                if side < 0: poly = poly[::-1]
                y0, y1 = (HALF - 0.05, ye) if face > 0 else (-ye, -HALF + 0.05)
                prism(poly, y0, y1, cl, 1200 + k * 10 + (side + 2) * 3 + face, rough=0.005, bev=0.02, chips=1 if k == 0 else 0, csize=0.1, wob=0.004)
            # fuste da pilastra (clara), três peças
            zz = 0.45; r2 = random.Random(1300 + side * 3 + face)
            heights = [0.8, 0.95, 0.6]
            ks = (2.80 - 0.45 - 0.02) / sum(heights)
            for k, h in enumerate(heights):
                z1 = zz + h * ks
                xe = 3.62 + r2.uniform(-0.03, 0.03)
                poly = [(side * SPAN, zz + GAP), (side * xe, zz + GAP), (side * xe, z1 - GAP), (side * SPAN, z1 - GAP)]
                if side < 0: poly = poly[::-1]
                y0, y1 = (HALF - 0.05, 0.585) if face > 0 else (-0.585, -HALF + 0.05)
                prism(poly, y0, y1, cl, 1400 + k * 10 + (side + 2) * 3 + face, rough=0.005, bev=0.02, chips=1 if k == 1 else 0, csize=0.1)
                zz = z1

    # ------------------------------------------------------------ rodapé e cornija (perfis em camadas)
    plinth = [(0.6, 0.0), (0.6, 0.31), (0.55, 0.38), (0.55, 0.45), (-0.55, 0.45), (-0.55, 0.38), (-0.6, 0.31), (-0.6, 0.0)]
    for side, sd in ((-1, 71), (1, 72)):
        r = random.Random(sd)
        cuts = [SPAN, SPAN + 0.85, 4.5]
        for i in range(2):
            a, b = cuts[i], cuts[i + 1]
            a += GAP if i else 0; b -= GAP if i == 0 else 0
            x0, x1 = sorted((side * a, side * b))
            xprism(plinth, x0, x1, es, sd * 10 + i, bev=0.02, chips=1, csize=0.15)
    corn = [(0.5, 4.7), (0.56, 4.7), (0.56, 4.82), (0.50, 4.82), (0.50, 5.10), (0.57, 5.10), (0.57, 5.24), (0.60, 5.24), (0.60, 5.4)]
    corn_full = corn + [(-y, z) for y, z in corn[::-1]]
    for side, sd in ((-1, 81), (1, 82)):
        r = random.Random(sd)
        cuts = [X_HOOD, X_HOOD + r.uniform(0.7, 1.0), 4.5]
        for i in range(2):
            a, b = cuts[i], cuts[i + 1]
            a += GAP if i else 0.0; b -= GAP if i == 0 else 0
            x0, x1 = sorted((side * a, side * b))
            xprism(corn_full, x0, x1, es, sd * 10 + i, bev=0.02, chips=1, csize=0.15)
    # lábio superior sobre o arco (z 5.3..5.4)
    # dentículos sob a coroa (frente e verso), iguais aos da parede
    rd = random.Random(1800)
    for side in (-1, 1):
        n = int((4.5 - X_HOOD - 0.1) / 0.215)
        for i in range(n):
            dx = side * (X_HOOD + 0.15 + i * 0.215 + rd.uniform(-0.012, 0.012))
            if abs(dx) > 4.42: continue
            for face in (1, -1):
                o = L.box((dx, face * 0.49, 4.96), (0.11, 0.11, 0.13), es, bev=0.014)
                if rd.random() < 0.3: safe_chip(o, 1, 0.05, 1900 + i)
    lip = [(0.60, 5.24), (-0.60, 5.24), (-0.60, 5.4), (0.60, 5.4)]
    for side, sd in ((-1, 91), (1, 92)):
        r = random.Random(sd)
        cuts = [0.8, 0.8 + (X_HOOD - 0.8) * r.uniform(0.45, 0.6), X_HOOD]
        for i in range(2):
            a, b = cuts[i], cuts[i + 1]
            a += GAP; b -= GAP if i == 0 else 0.0
            x0, x1 = sorted((side * a, side * b))
            xprism(lip, x0, x1, cl, sd * 10 + i, bev=0.012, chips=0)

    # ------------------------------------------------------------ rachaduras (entalhes finos com boolean)
    def crack(o, p, seed, face):
        r = random.Random(seed)
        x, z = p
        for k in range(r.randint(3, 4)):
            ang = math.radians(r.uniform(-75, -105) + r.uniform(-30, 30))
            ln = r.uniform(0.12, 0.24)
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, face * (HALF + 0.0), z), rotation=(0, ang, 0))
            c = bpy.context.object; c.scale = (0.022, 0.08, ln); bpy.ops.object.transform_apply(scale=True)
            bk = o.data.copy()
            mod = o.modifiers.new("cr", 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = c; mod.solver = 'EXACT'
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier="cr")
            bpy.data.objects.remove(c, do_unlink=True)
            if manifold_ok(o): bpy.data.meshes.remove(bk)
            else:
                old = o.data; o.data = bk; bpy.data.meshes.remove(old)
            x += math.sin(ang) * -ln * 0.9 if False else math.sin(ang) * ln * 0.9
            z += math.cos(ang) * ln * 0.9

    r = random.Random(1500)
    cand = [o for o in blocks if o.dimensions.x > 0.5 and o.dimensions.z > 0.35 and o.data.materials and o.data.materials[0] == es and o.location.z < 4.9]
    r.shuffle(cand)
    for i, o in enumerate(cand[:8]):
        o_x = o.location.x + r.uniform(-o.dimensions.x * 0.25, o.dimensions.x * 0.25)
        o_z = o.location.z + o.dimensions.z * 0.35
        crack(o, (o_x, o_z), 1600 + i, 1 if i % 2 == 0 else -1)

    # grapas de ferro (cintas entre blocos) nas ombreiras
    r = random.Random(1700)
    for side in (-1, 1):
        for z in (1.3, 2.35):
            x = side * (SPAN + r.uniform(0.35, 1.15))
            for face in (1, -1):
                L.box((x, face * (HALF + 0.004), z + r.uniform(-0.03, 0.03)), (0.22, 0.02, 0.045), fe, bev=0.006, seg=1)
                for dx in (-0.08, 0.08):
                    L.box((x + dx, face * (HALF + 0.013), z), (0.03, 0.02, 0.03), fe, bev=0.005, seg=1)

    for o in L.objs:
        b = bmesh.new(); b.from_mesh(o.data)
        bmesh.ops.recalc_face_normals(b, faces=b.faces[:]); b.to_mesh(o.data); b.free()
    # um único material por objeto (boolean pode perder o slot)
    for o in L.objs:
        mt = bpy.data.materials.get(o.get('m', '')) if 'm' in o.keys() else (o.data.materials[0] if len(o.data.materials) else es)
        if mt is None: mt = es
        o.data.materials.clear(); o.data.materials.append(mt)
        for p in o.data.polygons: p.material_index = 0
    # garante o contrato de profundidade (|y| <= 0.6)
    for o in L.objs:
        me = o.data; ch = False
        for v in me.vertices:
            wy = v.co.y + o.location.y
            if abs(wy) > 0.6:
                v.co.y = (0.6 if wy > 0 else -0.6) - o.location.y; ch = True
        if ch: me.update()

    # ------------------------------------------------------------ colisão: só ombreiras e acima de 4,8 m
    L.col_box((-3.75, 0, 2.7), (1.5, 1.2, 5.4), "ColOmbreira")
    L.col_box((3.75, 0, 2.7), (1.5, 1.2, 5.4), "ColOmbreira")
    L.col_box((0, 0, 5.1), (6.0, 1.2, 0.6), "ColTimpano")
