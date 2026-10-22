"""Parede reta da Cripta: SM_Cripta_Parede, 3,0 (X) x 1,2 (Y) x 5,4 (Z) m.
Rodapé escalonado de 0,45 m, cantaria de blocos grandes irregulares em fiadas desencontradas, pilastra rasa,
friso com losangos, cornija de 0,7 m com dentículos e mísulas, bloco caído/rachado. Frente (+Y) com mais detalhe que o verso."""
import bpy, bmesh, math, random
from mathutils import Vector

GLB = "SM_Cripta_Parede"
HEROI_X, HEROI_Y = 1.9, 1.9
VISTAS = {
    "frente": ((0.2, 9.5, 2.8), (0, 0, 2.7), 700, 900),
    "tres_quartos": ((-5.2, 6.0, 4.6), (0, 0, 2.5), 800, 900),
    "close": ((-1.6, 2.6, 1.0), (-0.5, 0.4, 0.8), 800, 800),
    "cornija": ((1.4, 3.2, 3.2), (0, 0.4, 4.9), 800, 800),
}
HALF = 1.5
FACE = 0.44          # plano médio da face frontal da cantaria
BACK = -0.46         # plano da face traseira


def _manifold_ok(o, v0):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bad = sum(1 for e in bm.edges if not e.is_manifold)
    vol = abs(bm.calc_volume()); bm.free()
    return bad == 0 and vol > 0.72 * v0


def chip(L, o, n, size, seed):
    """Lascas com checagem de manifold; se a boolean estragar o bloco, volta à malha original."""
    bm = bmesh.new(); bm.from_mesh(o.data); v0 = abs(bm.calc_volume()); bm.free()
    for k in range(4):
        backup = o.data.copy()
        L.chip_corners(o, n, size, seed + k * 97, 0.5)
        if _manifold_ok(o, v0):
            bpy.data.meshes.remove(backup); return True
        bad = o.data; o.data = backup; bpy.data.meshes.remove(bad)
    return False


def rblock(L, m, x0, x1, y0, y1, z0, z1, seed, jit=0.006, bulge=0.012, bev=0.018, nchip=0, csize=0.1, front=True, cuts=3):
    """Bloco de pedra irregular: caixa subdividida, face deslocada com barriga e ruído, bisel real e lascas."""
    r = random.Random(seed); jit *= 0.7; csize *= 1.7; cuts = cuts + 1; nchip = nchip + (1 if front and nchip else 0)
    p1, p2, k1, k2 = r.uniform(0, 6.3), r.uniform(0, 6.3), r.uniform(2.5, 5), r.uniform(2.5, 6)
    amp = 0.016 if front else 0.008
    w, d, h = x1 - x0, y1 - y0, z1 - z0
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co.x *= w; v.co.y *= d; v.co.z *= h
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    fy = 1 if front else -1
    for v in bm.verts:
        edge_x = abs(abs(v.co.x) - w / 2) < 1e-4
        nx, nz = v.co.x / (w / 2), v.co.z / (h / 2)
        on_face = (v.co.y * fy) > d / 2 - 1e-4
        if on_face:
            v.co.y += fy * (bulge * (1 - nx * nx) * (1 - nz * nz) + amp * math.sin(k1 * v.co.x + p1) * math.sin(k2 * v.co.z + p2) + r.uniform(-jit, jit))
        if not edge_x: v.co.x += r.uniform(-jit, jit) * 0.6
        v.co.z += r.uniform(-jit, jit) * 0.6
        if not on_face: v.co.y += r.uniform(-jit, jit) * 0.4
    me = bpy.data.meshes.new("blk"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("blk", me); bpy.context.collection.objects.link(o)
    o.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    for p in me.polygons: p.use_smooth = False
    bpy.context.view_layer.objects.active = o
    L.bevel_obj(o, bev * 1.3, 2, 28)
    if nchip: chip(L, o, nchip, csize, seed * 7 + 3)
    for p in o.data.polygons: p.use_smooth = False
    return L.add(o, m)


def partition(r, total, lo, hi):
    out = []; rest = total
    while rest > hi:
        w = r.uniform(lo, hi)
        if rest - w < lo: w = rest - lo
        out.append(w); rest -= w
    out.append(rest)
    return out


def crack(L, m_host, pts, width, depth, seed):
    """Rachadura: cadeia de fatias finas giradas subtraídas do bloco (boolean)."""
    cuts = []
    for (a, b) in zip(pts[:-1], pts[1:]):
        a = Vector(a); b = Vector(b); mid = (a + b) / 2; ln = (b - a).length
        bpy.ops.mesh.primitive_cube_add(size=1, location=mid)
        c = bpy.context.object
        c.scale = (width * random.Random(seed + len(cuts)).uniform(0.7, 1.3), depth * 2, ln * 1.05)
        c.rotation_euler = (0, -math.atan2((b - a).x, (b - a).z), 0)
        bpy.ops.object.transform_apply(scale=True)
        cuts.append(c)
    bpy.ops.object.select_all(action='DESELECT')
    for c in cuts: c.select_set(True)
    bpy.context.view_layer.objects.active = cuts[0]; bpy.ops.object.join()
    cutter = bpy.context.object
    bm = bmesh.new(); bm.from_mesh(m_host.data); v0 = abs(bm.calc_volume()); bm.free()
    backup = m_host.data.copy()
    mod = m_host.modifiers.new("crk", 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = cutter; mod.solver = 'EXACT'
    bpy.context.view_layer.objects.active = m_host
    bpy.ops.object.modifier_apply(modifier="crk")
    if not _manifold_ok(m_host, v0):
        bad = m_host.data; m_host.data = backup; bpy.data.meshes.remove(bad)
    else:
        bpy.data.meshes.remove(backup)
    bpy.data.objects.remove(cutter, do_unlink=True)


def build(L):
    r = random.Random(2026)
    E, C, F = L.stone("escura"), L.stone("clara"), L.stone("ferro")
    def pick(p=0.16): return C if r.random() < p else E

    # ---------------------------------------------------------------- miolo (preenche as juntas, escuro)
    core = L.box((0, -0.02, 2.57), (2.98, 0.80, 4.2), E, bev=0.0)

    # ---------------------------------------------------------------- rodapé escalonado (0 .. 0.45)
    # degrau baixo: salta até y=0.6 ; degrau alto recuado até y=0.54
    for side in (1, -1):
        front = side == 1
        for tier, (z0, z1, yo) in enumerate(((0.0, 0.24, 0.60), (0.24, 0.45, 0.54))):
            xs = partition(r, 3.0, 0.8, 1.5); x = -HALF
            if tier: xs = xs[::-1]
            for i, w in enumerate(xs):
                xa = x; xb = x + w; x += w
                ga = 0.012 if i else 0.0; gb = 0.012 if i < len(xs) - 1 else 0.0
                yy = (-0.02, yo) if front else (-yo, 0.02)
                yy = (yy[0] if front else yy[0] - r.uniform(0, 0.02), yy[1] + (r.uniform(-0.02, 0.01) if front else 0))
                rblock(L, pick(0.1), xa + ga, xb - gb, yy[0], yy[1], z0 + 0.006, z1 - 0.006, r.randint(1, 10 ** 6),
                       jit=0.007, bulge=0.014, bev=0.02, nchip=2 if front else 1, csize=0.1 if tier == 0 else 0.08, front=front)

    # ---------------------------------------------------------------- cantaria: fiadas desencontradas (0.45 .. 4.7)
    z_lo, z_hi = 0.45, 4.70
    hs = [0.78, 0.62, 0.82, 0.66, 0.74, 0.63]
    sc = (z_hi - z_lo) / sum(hs); hs = [h * sc for h in hs]
    fiadas = []
    z = z_lo
    for ci, h in enumerate(hs):
        zb, zt = z, z + h; z = zt
        row_front = []
        for side in (1, -1):
            front = side == 1
            xs = partition(r, 3.0, 0.75 if front else 0.95, 1.55)
            # desencontra: deslocamento da junta por fiada
            x = -HALF
            for i, w in enumerate(xs):
                xa = x; xb = x + w; x += w
                ga = 0.014 if i else 0.0; gb = 0.014 if i < len(xs) - 1 else 0.0
                zj0 = zb + 0.008 + r.uniform(0, 0.012); zj1 = zt - 0.008 - r.uniform(0, 0.012)
                if front:
                    fy = FACE + r.uniform(-0.035, 0.05)
                    o = rblock(L, pick(), xa + ga, xb - gb, 0.0, fy, zj0, zj1, r.randint(1, 10 ** 6),
                               jit=0.008, bulge=0.016, bev=0.022, nchip=r.choice((1, 2, 2, 3)), csize=r.uniform(0.09, 0.15), front=True)
                    row_front.append((o, xa + ga, xb - gb, zj0, zj1, fy))
                else:
                    fy = BACK - r.uniform(0, 0.03)
                    rblock(L, pick(0.1), xa + ga, xb - gb, fy, 0.0, zj0, zj1, r.randint(1, 10 ** 6),
                           jit=0.005, bulge=0.008, bev=0.016, nchip=r.choice((0, 1)), csize=0.09, front=False, cuts=2)
        fiadas.append(row_front)

    # rachaduras e bloco partido na frente
    done = 0
    for ci in (0, 1, 3, 4, 5):
        blocks = fiadas[ci]
        o, xa, xb, z0, z1, fy = blocks[len(blocks) // 2]
        xm = (xa + xb) / 2 + r.uniform(-0.15, 0.15)
        pts = []; zz = z1 + 0.02; xx = xm
        for k in range(6):
            pts.append((xx, fy, zz)); zz -= (z1 - z0 + 0.04) / 5; xx += r.uniform(-0.12, 0.12)
        crack(L, o, pts, 0.026, 0.04, 40 + ci)
        done += 1

    # bloco partido: o canto de cima caiu (corte passante, boolean) e os pedaços estão no rodapé
    blocks = fiadas[2]
    o, xa, xb, z0, z1, fy = max(blocks, key=lambda t: t[2] - t[1])
    bm = bmesh.new(); bm.from_mesh(o.data); v0 = abs(bm.calc_volume()); bm.free()
    backup = o.data.copy()
    bpy.ops.mesh.primitive_cube_add(size=1, location=(xb - 0.06, 0.2, z1 - 0.02), rotation=(0.0, math.radians(32), 0))
    cut = bpy.context.object; cut.scale = (0.62, 1.6, 0.42); bpy.ops.object.transform_apply(scale=True)
    mod = o.modifiers.new("brk", 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = cut; mod.solver = 'EXACT'
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier="brk")
    bpy.data.objects.remove(cut, do_unlink=True)
    if not _manifold_ok(o, v0):
        bad = o.data; o.data = backup; bpy.data.meshes.remove(bad)
    else: bpy.data.meshes.remove(backup)
    cx = xb - 0.35
    # pedaços caídos sobre o degrau do rodapé (z=0.45)
    for k, (dx, w, h, yv, rz, tx) in enumerate(((0.0, 0.46, 0.20, 0.40, 0.35, 0.10), (0.42, 0.20, 0.12, 0.43, -0.7, -0.15),
                                                  (-0.36, 0.16, 0.11, 0.44, 0.3, 0.2), (0.22, 0.12, 0.08, 0.47, 1.0, 0.1),
                                                  (-0.18, 0.10, 0.07, 0.48, 0.6, -0.1))):
        fr = rblock(L, E if k % 2 else C, -w / 2, w / 2, -0.12, 0.12, 0.0, h, 910 + k, jit=0.012, bulge=0.012, bev=0.02, nchip=2, csize=0.07, front=True, cuts=2)
        fr.location = (cx + dx, yv, 0.45 + h * 0.45)
        fr.rotation_euler = (tx, r.uniform(-0.15, 0.15), rz)

    # ---------------------------------------------------------------- friso (faixa com losangos em relevo) a z=3.28
    zf0, zf1 = 3.22, 3.40
    x = -HALF; xs = partition(r, 3.0, 0.9, 1.3)
    for i, w in enumerate(xs):
        xa = x; xb = x + w; x += w
        ga = 0.012 if i else 0.0; gb = 0.012 if i < len(xs) - 1 else 0.0
        rblock(L, E, xa + ga, xb - gb, 0.30, 0.545, zf0, zf1, 300 + i, jit=0.004, bulge=0.006, bev=0.014, nchip=1, csize=0.06, front=True, cuts=2)
    nd = 6
    for i in range(nd):
        dx = -1.25 + i * 0.5 + r.uniform(-0.02, 0.02)
        if i == 4: continue    # um losango perdido
        L.box((dx, 0.555, 3.31), (0.10, 0.03, 0.10), C, rot=(0, math.radians(45), 0), bev=0.006)
    # (losangos: caixas giradas 45 graus em torno de Y, achatadas em Y)
    # ---------------------------------------------------------------- pilastra rasa (esq., x=-0.78)
    px = -0.78; pw = 0.52
    rblock(L, C, px - 0.39, px + 0.39, 0.10, 0.575, 0.45, 0.75, 440, jit=0.006, bulge=0.012, bev=0.024, nchip=3, csize=0.1, front=True)
    zc = 0.75
    segs = [0.62, 0.52, 0.80, 0.55, 0.66, 0.48]
    scale = (4.05 - zc) / sum(segs)
    for i, h in enumerate(segs):
        h *= scale
        rblock(L, C if i % 5 != 2 else E, px - pw / 2 + r.uniform(-0.01, 0.01), px + pw / 2 + r.uniform(-0.01, 0.01), 0.10, 0.535 + r.uniform(-0.01, 0.015),
               zc + 0.008, zc + h - 0.008, 400 + i, jit=0.006, bulge=0.014, bev=0.02, nchip=2, csize=0.08, front=True, cuts=2)
        zc += h
    # capitel em três camadas
    for k, (z0, z1, hw, yy) in enumerate(((4.05, 4.22, 0.30, 0.555), (4.22, 4.45, 0.36, 0.575), (4.45, 4.70, 0.42, 0.595))):
        rblock(L, C, px - hw, px + hw, 0.10, yy, z0 + 0.006, z1 - 0.006, 450 + k, jit=0.006, bulge=0.01, bev=0.02, nchip=2, csize=0.09, front=True, cuts=2)

    # ---------------------------------------------------------------- cornija 4.70 .. 5.40
    def cornice_layer(z0, z1, yf, yb, lo, hi, seed, nchip=2, csize=0.09):
        for side in (1, -1):
            front = side == 1
            xs = partition(random.Random(seed + side), 3.0, lo, hi); x = -HALF
            for i, w in enumerate(xs):
                xa = x; xb = x + w; x += w
                ga = 0.012 if i else 0.0; gb = 0.012 if i < len(xs) - 1 else 0.0
                if front: rblock(L, E, xa + ga, xb - gb, 0.0, yf, z0 + 0.005, z1 - 0.005, seed * 3 + i, jit=0.006, bulge=0.01, bev=0.02, nchip=nchip, csize=csize, front=True, cuts=2)
                else: rblock(L, E, xa + ga, xb - gb, yb, 0.0, z0 + 0.005, z1 - 0.005, seed * 5 + i, jit=0.005, bulge=0.006, bev=0.018, nchip=1, csize=0.07, front=False, cuts=2)
    cornice_layer(4.70, 4.82, 0.56, -0.56, 1.0, 1.6, 500)       # filete
    cornice_layer(4.82, 5.10, 0.50, -0.50, 0.9, 1.5, 520)       # friso liso
    cornice_layer(5.10, 5.24, 0.57, -0.57, 1.1, 1.7, 540)       # gola
    cornice_layer(5.24, 5.40, 0.60, -0.60, 1.0, 1.7, 560, nchip=3, csize=0.11)  # coroa
    # dentículos sob a coroa (frente)
    for i in range(14):
        dx = -1.40 + i * 0.215 + r.uniform(-0.012, 0.012)
        if i == 9: continue
        L.box((dx, 0.49, 4.96), (0.11, 0.11, 0.13), E, bev=0.012)
    # mísulas (frente): três degraus que avançam
    for i, mx in enumerate((-1.18, -0.30, 0.55, 1.28)):
        mx += r.uniform(-0.04, 0.04)
        L.box((mx, 0.43, 4.93), (0.34, 0.24, 0.12), C, bev=0.014)
        L.box((mx, 0.45, 4.99), (0.26, 0.22, 0.10), C, bev=0.014)
        L.box((mx, 0.46, 5.05), (0.18, 0.20, 0.10), C, bev=0.014)

    # ---------------------------------------------------------------- colisão
    L.col_box((0, 0, 2.7), (3.0, 1.2, 5.4))
