"""Coluna gótica da "coluna com corrente" da Cripta (geometria).
Referência: coluna_corrente_ref/ref_coluna_corrente.png. Soco em degraus de blocos, fuste quadrado com nicho
ogival profundo na frente (arquivolta em relevo + colunetas), capitel em lajes com lasca faltando, pináculo
piramidal quebrado, olhais de ferro na face interna, entulho e musgo discreto. Metros, base em z=0, frente = +Y.

Cada bloco de pedra é um casco convexo irregular (cantos deslocados, faces com facetas, quinas lascadas) com chanfro
nas arestas vivas; shade flat. O resultado sai agrupado por material (M['pedra'], 'escura', 'musgo', 'ferro').

build_coluna(x, lado, seed, M) -> list[bpy.types.Object]
ancoras(x, lado) -> pontos absolutos dos olhais (onde a corrente prende)."""
import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix

ALTURA = 3.5
ANCORAS = None  # definido abaixo (depende de lado)


def _ancoras_rel(lado):
    return [(-lado * 0.34, 0.0, 2.35), (-lado * 0.34, 0.0, 1.35)]


def ancoras(x, lado):
    return [(x + a[0], a[1], a[2]) for a in _ancoras_rel(lado)]


ANCORAS = [(-0.34, 0, 2.35), (-0.34, 0, 1.35)]  # exemplo para lado=+1; use _ancoras_rel(lado) / ancoras()


class _Ctx:
    def __init__(self, seed, M, lado):
        self.r = random.Random(seed * 7919 + 13)
        self.M = M
        self.lado = lado
        self.dano = 1.0 if lado > 0 else 0.55
        self.parts = {'pedra': [], 'escura': [], 'musgo': [], 'ferro': []}
        self.tmp = []

    def add(self, bm, key, name="p"):
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(o)
        self.parts[key].append(o)
        return o


# ------------------------------------------------------------------ geometria base
def _hull_bm(pts, bev=0.0, seg=1, ang=0.35):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    dead = [v for v in bm.verts if not v.link_faces]
    if dead:
        bmesh.ops.delete(bm, geom=dead, context='VERTS')
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.5), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if bev > 0:
        es = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > ang]
        try:
            bmesh.ops.bevel(bm, geom=es, offset=bev, segments=seg, affect='EDGES', profile=0.5)
        except Exception:
            pass
    return bm


def _xf(bm, M4):
    bmesh.ops.transform(bm, matrix=M4, verts=bm.verts)


def box_pts(r, size, jit=0.008, cut=None, bulge=(), bamt=0.012):
    """Pontos de um bloco centrado na origem. cut = {(sx,sy,sz): (fx,fy,fz)} corta um canto (fração das arestas).
    bulge = eixos ('+y','+z'...) que ganham um ponto empurrado para fora (faces facetadas)."""
    sx, sy, sz = size
    pts = []
    cut = cut or {}
    for ix in (-1, 1):
        for iy in (-1, 1):
            for iz in (-1, 1):
                c = Vector((ix * sx / 2, iy * sy / 2, iz * sz / 2))
                if (ix, iy, iz) in cut:
                    fx, fy, fz = cut[(ix, iy, iz)]
                    pts.append(c - Vector((ix * fx * sx, 0, 0)))
                    pts.append(c - Vector((0, iy * fy * sy, 0)))
                    pts.append(c - Vector((0, 0, iz * fz * sz)))
                else:
                    pts.append(c)
    pts = [p + Vector((r.uniform(-jit, jit), r.uniform(-jit, jit), r.uniform(-jit, jit))) for p in pts]
    for b in bulge:
        ax = {'x': 0, 'y': 1, 'z': 2}[b[1]]
        sg = 1 if b[0] == '+' else -1
        t1, t2 = [i for i in range(3) if i != ax]
        for _ in range(5):
            u, w = r.uniform(-.85, .85), r.uniform(-.85, .85)
            v = Vector((0, 0, 0))
            v[t1] = u * size[t1] / 2
            v[t2] = w * size[t2] / 2
            fall = 1.0 - max(abs(u), abs(w)) * 0.7
            v[ax] = sg * (size[ax] / 2 + bamt * r.uniform(0.15, 1.0) * fall)
            pts.append(v)
    return pts


def place(bm, loc, rot=(0, 0, 0)):
    M4 = (Matrix.Translation(loc) @ Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y')
          @ Matrix.Rotation(rot[0], 4, 'X'))
    _xf(bm, M4)


def block(C, key, loc, size, rot=(0, 0, 0), jit=0.008, bev=0.009, cut=None, bulge=('+y',), bamt=0.012, seg=1):
    r = C.r
    bm = _hull_bm(box_pts(r, size, jit, cut, bulge, bamt), min(bev, 0.22 * min(size)), seg)
    place(bm, loc, rot)
    return C.add(bm, key, "blk")


def prism_xz(poly, y0, y1):
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in poly]
    b = [bm.verts.new((x, y1, z)) for x, z in poly]
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    n = len(poly)
    for i in range(n):
        bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def ogive(w, h_side, n=8):
    """Polígono (x,z) ogival: base em z=0, lados até h_side e duas curvas de raio 2w até a ponta."""
    rr = 2 * w
    a_tip = math.acos((rr - w) / rr)
    right = [((w - rr) + rr * math.cos(a_tip * i / n), h_side + rr * math.sin(a_tip * i / n)) for i in range(1, n + 1)]
    left = [(-x, z) for x, z in reversed(right[:-1])]
    return [(-w, 0), (w, 0), (w, h_side)] + right + left + [(-w, h_side)]


def boolean(o, cutter, op='DIFFERENCE'):
    md = o.modifiers.new("b", 'BOOLEAN')
    md.operation = op
    md.object = cutter
    md.solver = 'EXACT'
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=md.name)


def cutter_obj(C, bm):
    me = bpy.data.meshes.new("cut")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("cut", me)
    bpy.context.collection.objects.link(o)
    C.tmp.append(o)
    return o


def bbox_world(o):
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (min(c.x for c in cs), max(c.x for c in cs), min(c.y for c in cs), max(c.y for c in cs),
            min(c.z for c in cs), max(c.z for c in cs))


def overlap(a, b):
    return a[0] < b[1] and a[1] > b[0] and a[2] < b[3] and a[3] > b[2] and a[4] < b[5] and a[5] > b[4]


# ------------------------------------------------------------------ alvenaria
def split_len(r, L, wmin, wmax):
    out, x = [], 0.0
    while L - x > wmax:
        w = r.uniform(wmin, wmax)
        out.append(w)
        x += w
    rest = L - x
    if out and rest < wmin:
        out[-1] += rest
    else:
        out.append(rest)
    return out


def ring_course(C, half, z0, h, t, wmin, wmax, parity, miss=0.0, chip=0.35, jit=0.007, bev=0.009, bulge_top=False,
                skip_front=False):
    """Fiada de blocos em anel. Devolve lista de (obj, (nx, ny)) com a normal externa de cada bloco."""
    r = C.r
    out = []
    for side in range(4):
        rot = side * math.pi / 2
        ox, oy = -math.sin(rot), math.cos(rot)
        full = (side % 2 == 0) == bool(parity)
        L0, L1 = (-half, half) if full else (-half + t, half - t)
        pos = L0
        for w in split_len(r, L1 - L0, wmin, wmax):
            u = pos + w / 2
            pos += w
            if miss and r.random() < miss:
                continue
            hh = h * r.uniform(0.96, 1.0) - 0.012
            ww = w - 0.014
            tt = t * r.uniform(0.9, 1.0)
            dy = r.uniform(-0.012, 0.010)
            cut = None
            if r.random() < chip:
                cut = {(r.choice((-1, 1)), 1, r.choice((-1, 1))): (r.uniform(.12, .32), r.uniform(.25, .6), r.uniform(.15, .4))}
            bl = ('+y', '+z') if bulge_top else ('+y',)
            o = block(C, 'escura' if r.random() < 0.07 else 'pedra', (0, 0, 0), (ww, tt, hh), jit=jit, bev=bev, cut=cut, bulge=bl, bamt=0.016)
            lx, ly = u, half - tt / 2 + dy
            M4 = Matrix.Rotation(rot, 4, 'Z') @ Matrix.Translation((lx, ly, z0 + h / 2))
            o.data.transform(M4 @ Matrix.Identity(4))
            o.data.update()
            out.append((o, (round(ox), round(oy))))
    return out


def chip_edges(C, blocks, prob, smin=0.04, smax=0.10, top=True):
    r = C.r
    for (o, nrm) in blocks:
        if r.random() > prob:
            continue
        bb = bbox_world(o)
        nx, ny = nrm
        if nx:
            ox_ = bb[1] if nx > 0 else bb[0]
            ty = r.choice((bb[2], bb[3]))
            c = Vector((ox_, ty, bb[5] if (top and r.random() < .7) else bb[4]))
        else:
            oy_ = bb[3] if ny > 0 else bb[2]
            tx = r.choice((bb[0], bb[1]))
            c = Vector((tx, oy_, bb[5] if (top and r.random() < .7) else bb[4]))
        sz = r.uniform(smin, smax)
        cm = cutter_obj(C, _hull_bm(box_pts(r, (sz * r.uniform(.8, 1.4), sz * r.uniform(.8, 1.4), sz * r.uniform(.6, 1.1)), sz * 0.15), 0.0))
        cm.location = c - Vector((nx, ny, 0)) * sz * 0.1
        cm.rotation_euler = (r.uniform(0, 1.5), r.uniform(0, 1.5), r.uniform(0, 3))
        bpy.context.view_layer.update()
        try:
            boolean(o, cm)
        except Exception:
            pass


def _crack(C, blocks, nrm, zig, face_pos, dmax=None):
    """Sulco em zigue-zague: zig = [(u, z)], u = coordenada ao longo da face (y p/ faces X; x p/ faces Y)."""
    r = C.r
    nx, ny = nrm
    for (o, bn) in blocks:
        if bn != nrm:
            continue
        bb = bbox_world(o)
        for i in range(len(zig) - 1):
            (u0, z0c), (u1, z1c) = zig[i], zig[i + 1]
            lo, hi = min(u0, u1) - 0.02, max(u0, u1) + 0.02
            if nx:
                bbx = (min(nx * 0.2, nx * 0.7), max(nx * 0.2, nx * 0.7), lo, hi, min(z0c, z1c) - .02, max(z0c, z1c) + .02)
            else:
                bbx = (lo, hi, min(ny * 0.2, ny * 0.7), max(ny * 0.2, ny * 0.7), min(z0c, z1c) - .02, max(z0c, z1c) + .02)
            if not overlap(bb, bbx):
                continue
            d = Vector((u1 - u0, z1c - z0c))
            L = d.length
            wdt = 0.018 if i % 2 == 0 else 0.012
            bm = _hull_bm(box_pts(r, (0.10, wdt, L + 0.014), 0.0), 0.0)  # eixo longo = Z local
            ang = math.atan2(-d.x if nx else d.x, d.y)
            _xf(bm, Matrix.Rotation(ang, 4, 'X'))
            # bm: profundidade ao longo de X local; longo em Y/Z -> para faces Y gira 90 graus
            if nx:
                _xf(bm, Matrix.Translation((nx * face_pos, (u0 + u1) / 2, (z0c + z1c) / 2)))
            else:
                _xf(bm, Matrix.Rotation(math.pi / 2, 4, 'Z'))
                _xf(bm, Matrix.Translation(((u0 + u1) / 2, ny * face_pos, (z0c + z1c) / 2)))
            boolean(o, cutter_obj(C, bm))


def scars(C, blocks, dens=55, skip=None):
    """Cicatrizes de cinzel/fissuras rasas nas faces externas dos blocos (aspecto de pedra talhada à mão)."""
    r = C.r
    for (o, nrm) in blocks:
        if skip and skip(o, nrm):
            continue
        nx, ny = nrm
        bb = bbox_world(o)
        if nx:
            ext = bb[1] if nx > 0 else bb[0]
            wu, wz = bb[3] - bb[2], bb[5] - bb[4]
            u0 = bb[2]
        else:
            ext = bb[3] if ny > 0 else bb[2]
            wu, wz = bb[1] - bb[0], bb[5] - bb[4]
            u0 = bb[0]
        n = int(wu * wz * dens + r.random())
        for _ in range(n):
            u = u0 + wu * r.uniform(0.12, 0.88)
            z = bb[4] + wz * r.uniform(0.12, 0.88)
            L = r.uniform(0.04, 0.09)
            pp = []
            for _k in range(9):
                v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1)))
                v.normalize()
                v *= r.uniform(0.7, 1.1)
                pp.append(Vector((v.x * 0.02, v.y * L * r.uniform(.5, 1), v.z * L * 0.6)))
            bm = _hull_bm(pp, 0.0)
            _xf(bm, Matrix.Rotation(r.uniform(0, math.pi), 4, 'X'))
            if nx:
                _xf(bm, Matrix.Translation((ext + nx * 0.006, u, z)))
            else:
                _xf(bm, Matrix.Rotation(math.pi / 2, 4, 'Z'))
                _xf(bm, Matrix.Translation((u, ext + ny * 0.006, z)))
            try:
                boolean(o, cutter_obj(C, bm))
            except Exception:
                pass


def core_box(C, half, z0, z1):
    bm = _hull_bm(box_pts(C.r, (2 * half, 2 * half, z1 - z0), 0.0), 0.0)
    place(bm, (0, 0, (z0 + z1) / 2))
    return C.add(bm, 'escura', "core")


# ------------------------------------------------------------------ pequenos detalhes
def rock(C, key, loc, size, bev=0.004, n=None, rot=None, flat=1.0, bury=0.3):
    """Pedra irregular: poliedro convexo de 8 a 14 faces (pontos numa elipsoide com raio e cisalhamento aleatórios),
    inclinado e parcialmente enterrado."""
    r = C.r
    n = n or r.randint(8, 12)
    pts = []
    for _ in range(n):
        v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1)))
        while v.length < 0.2:
            v = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1)))
        v.normalize()
        v *= r.uniform(0.7, 1.15)
        pts.append(Vector((v.x * size[0] / 2, v.y * size[1] / 2, v.z * size[2] / 2 * flat)))
    sh = r.uniform(-0.35, 0.35)
    pts = [Vector((p.x + sh * p.z, p.y, p.z)) for p in pts]
    bm = _hull_bm(pts, min(bev, 0.12 * min(size)), 1, 0.5)
    rr = rot or (r.uniform(-0.6, 0.6), r.uniform(-0.6, 0.6), r.uniform(0, 6.28))
    place(bm, (0, 0, 0), rr)
    zs = [v.co.z for v in bm.verts]
    zmin, zmax = min(zs), max(zs)
    _xf(bm, Matrix.Translation((loc[0], loc[1], loc[2] - zmin - bury * (zmax - zmin))))
    return C.add(bm, key, "rubble")


def moss(C, loc, rad, normal=(0, 0, 1)):
    r = C.r
    n = r.randint(5, 7)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + r.uniform(-.3, .3)
        rr = rad * r.uniform(0.55, 1.1)
        pts.append(Vector((math.cos(a) * rr * r.uniform(.8, 1.3), math.sin(a) * rr, -0.004)))
        pts.append(Vector((math.cos(a) * rr * 0.8, math.sin(a) * rr * 0.8, r.uniform(0.012, 0.022))))
    pts.append(Vector((r.uniform(-.2, .2) * rad, r.uniform(-.2, .2) * rad, r.uniform(0.026, 0.04))))
    bm = _hull_bm(pts, 0.0)
    q = Vector(normal).to_track_quat('Z', 'Y')
    _xf(bm, Matrix.Translation(loc) @ q.to_matrix().to_4x4())
    return C.add(bm, 'musgo', "musgo")


# ------------------------------------------------------------------ montagem
def _montar(C):
    r = C.r
    lado = C.lado
    dano = C.dano
    allblocks = []

    # --- soco: cores + 4 fiadas em degraus
    steps = [
        # half, z0, h, t, wmin, wmax, miss
        (0.56, 0.00, 0.34, 0.16, 0.28, 0.46, 0.05 * dano),
        (0.47, 0.34, 0.32, 0.14, 0.26, 0.42, 0.07 * dano),
        (0.39, 0.66, 0.17, 0.12, 0.26, 0.44, 0.06 * dano),
        (0.34, 0.83, 0.17, 0.10, 0.22, 0.40, 0.05 * dano),
    ]
    for (half, z0, h, t, wmin, wmax, miss) in steps:
        core_box(C, half - t + 0.025, z0, z0 + h + 0.01)
    for i, (half, z0, h, t, wmin, wmax, miss) in enumerate(steps):
        allblocks += ring_course(C, half, z0, h, t, wmin, wmax, i % 2, miss=miss, chip=0.4 * dano + 0.15,
                                 bev=0.011, bulge_top=True)
    chip_edges(C, allblocks, 0.6 * dano + 0.25, 0.06, 0.17)
    # laje de topo do soco (base do fuste): evita ver o vazio sob o fuste
    core_box(C, 0.25, 0.95, 1.01)

    # --- fuste: núcleo + fiadas
    zs = [1.0, 1.42 + r.uniform(-.03, .03), 1.80 + r.uniform(-.03, .03), 2.26 + r.uniform(-.03, .03), 2.70]
    core = core_box(C, 0.235, 1.0, 2.70)
    shaft = []
    for i in range(4):
        shaft += ring_course(C, 0.30, zs[i], zs[i + 1] - zs[i], 0.07, 0.17, 0.34, (i + int(r.random() * 2)) % 2,
                             miss=0.07 * dano, chip=0.45 * dano + 0.1, bev=0.007, jit=0.005)
    scars(C, allblocks, 22)
    chip_edges(C, shaft, 0.45 * dano + 0.15, 0.04, 0.11)
    # nicho ogival: corta blocos da frente e o núcleo
    scars(C, shaft, 26)
    NW, NZ0, NSIDE = 0.115, 1.25, 0.85
    ncut = cutter_obj(C, prism_xz([(x, z + NZ0) for x, z in ogive(NW, NSIDE, 9)], 0.10, 0.5))
    nb = (-NW, NW, 0.0, 0.5, NZ0, NZ0 + NSIDE + 0.25)
    boolean(core, ncut)
    for (o, nrm) in shaft:
        if nrm == (0, 1) and overlap(bbox_world(o), nb):
            boolean(o, ncut)
    # fenda estreita mais funda no fundo do nicho (profundidade)
    slit = cutter_obj(C, prism_xz([(x, z + 1.42) for x, z in ogive(0.045, 0.45, 7)], 0.0, 0.2))
    boolean(core, slit)
    # arquivolta em relevo (moldura ogival) com soleira
    ring = prism_xz([(x, z + 1.20) for x, z in ogive(0.165, 0.90, 9)], 0.288, 0.348)
    ring_o = C.add(ring, 'pedra', "arquivolta")
    inner = cutter_obj(C, prism_xz([(x, z + NZ0) for x, z in ogive(NW, NSIDE, 9)], 0.0, 0.6))
    boolean(ring_o, inner)
    _bevel_obj(ring_o, 0.006)
    # moldura interna: filete mais fino em volta da abertura (segunda ordem)
    # colunetas pequenas
    for sx in (-1, 1):
        cx = sx * 0.215
        block(C, 'pedra', (cx, 0.31, 1.235), (0.085, 0.075, 0.075), bev=0.006, jit=0.003, bulge=())
        cz0, cz1 = 1.27, 2.03
        pts = []
        for zz in (cz0, cz1):
            for k in range(8):
                a = 2 * math.pi * (k + 0.5) / 8
                rr = 0.03 * r.uniform(0.95, 1.05)
                pts.append(Vector((cx + math.cos(a) * rr, 0.315 + math.sin(a) * rr, zz)))
        bm = _hull_bm(pts, 0.003, 1, 0.5)
        C.add(bm, 'pedra', "coluneta")
        block(C, 'pedra', (cx, 0.31, 2.065), (0.095, 0.082, 0.075), bev=0.006, jit=0.003,
              cut={(sx, 1, 1): (0.3, 0.35, 0.4)} if sx == (1 if dano > .8 else -1) else None, bulge=())
    # tímpano em relevo: pequeno quadrifólio entalhado acima do arco (cortador)
    qb = None

    # --- rachaduras diagonais entalhadas (face externa, face interna, soco da frente)
    zig = [(0.16, 2.60), (0.10, 2.47), (0.18, 2.33), (0.06, 2.17), (0.0, 2.02), (-0.09, 1.86), (-0.04, 1.72),
           (-0.15, 1.55), (-0.10, 1.40), (-0.19, 1.25)]
    _crack(C, shaft, (lado, 0), zig, 0.30)
    zig2 = [(0.26, 2.62), (0.20, 2.44), (0.24, 2.25), (0.16, 2.08), (0.20, 1.92), (0.13, 1.74)]
    _crack(C, shaft, (-lado, 0), zig2, 0.30)
    zig3 = [(-0.30, 0.62), (-0.22, 0.52), (-0.27, 0.42), (-0.15, 0.30), (-0.18, 0.18), (-0.08, 0.06)]
    _crack(C, allblocks, (0, 1), zig3, 0.56, dmax=0.62)
    # rachaduras curtas no soco (frente)
    # olhais de ferro na face interna
    for (ax, ay, az) in _ancoras_rel(lado):
        s = -lado
        face_x = s * 0.30
        # placa chumbada
        bm = _hull_bm(box_pts(r, (0.03, 0.13, 0.17), 0.003, bulge=('+x',), bamt=0.006), 0.006, 1)
        if s < 0:
            _xf(bm, Matrix.Scale(-1, 4, (1, 0, 0)))
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        _xf(bm, Matrix.Translation((face_x + s * 0.012, 0, az)))
        C.add(bm, 'ferro', "placa")
        for dz in (-0.062, 0.062):
            for dy in (-0.045, 0.045):
                bm = _hull_bm([Vector((s * 0.0 + math.cos(a) * 0.011, dy + math.sin(a) * 0.011, dz)) for a in
                               [k * math.pi / 3 for k in range(6)]] +
                              [Vector((s * 0.0 + math.cos(a) * 0.011, dy + math.sin(a) * 0.011, dz)) + Vector((s * 0.016, 0, 0))
                               for a in [k * math.pi / 3 for k in range(6)]], 0.0)
                _xf(bm, Matrix.Translation((face_x + s * 0.025, 0, az)))
                C.add(bm, 'ferro', "rebite")
        # haste (munhão) saindo da placa
        pts = []
        for xx in (face_x + s * 0.02, ax - s * 0.0):
            for k in range(8):
                a = 2 * math.pi * k / 8
                pts.append(Vector((xx, math.cos(a) * 0.017, az + math.sin(a) * 0.017)))
        C.add(_hull_bm(pts, 0.0), 'ferro', "munhao")
        # argola (toro) com eixo em Y, passando pelo munhão
        _torus(C, (ax, ay, az), 0.050, 0.0125, (math.pi / 2, 0, 0), 'ferro', 20, 8)

    # --- capitel: 3 lajes
    cut_main = {(lado, 1, 1): (0.40, 0.34, 0.85)}
    s1 = block(C, 'pedra', (0, 0, 2.76), (0.74, 0.74, 0.12), bev=0.010, jit=0.006, bulge=('+x', '-x', '+y', '-y', '+z'))
    cut2 = dict(cut_main)
    s2 = block(C, 'pedra', (0, 0, 2.895), (0.86, 0.86, 0.15), bev=0.012, jit=0.008, cut=cut2,
               bulge=('+x', '-x', '+y', '-y', '+z'), bamt=0.015)
    # frustum da terceira laje
    pts = [Vector((sx * 0.20, sy * 0.20, 0.05)) for sx in (-1, 1) for sy in (-1, 1)] + \
          [Vector((sx * 0.215, sy * 0.215, -0.05)) for sx in (-1, 1) for sy in (-1, 1)] + \
          [Vector((r.uniform(-.1, .1), r.uniform(-.1, .1), 0.062))]
    pts = [p + Vector((r.uniform(-.006, .006), r.uniform(-.006, .006), 0)) for p in pts]
    pts[:] = [Vector((p.x * 1.65, p.y * 1.65, p.z)) for p in pts]
    bm = _hull_bm(pts, 0.009, 1)
    _xf(bm, Matrix.Translation((0, 0, 3.02)))
    s3 = C.add(bm, 'pedra', "laje3")
    if dano > 0.8:
        c = cutter_obj(C, _hull_bm(box_pts(r, (0.2, 0.2, 0.2), 0.02), 0.0))
        c.location = (0.34, -0.33, 3.09)
        c.rotation_euler = (0.5, 0.4, 0.7)
        bpy.context.view_layer.update()
        boolean(s3, c)
    # lascas nas bordas das lajes
    for slab, half, ztop, n in ((s1, 0.37, 2.82, int(3 + 2 * dano)), (s2, 0.43, 2.97, int(5 + 4 * dano))):
        for _ in range(n):
            side = r.randint(0, 3)
            u = r.uniform(-half, half)
            px, py = [(u, half), (half, u), (u, -half), (-half, u)][side]
            sz = r.uniform(0.05, 0.10 + 0.04 * dano)
            cm = cutter_obj(C, _hull_bm(box_pts(r, (sz, sz, sz * .8), sz * .2), 0.0))
            cm.location = (px, py, ztop + sz * 0.1)
            cm.rotation_euler = (r.uniform(0, 1.5), r.uniform(0, 1.5), r.uniform(0, 3))
            bpy.context.view_layer.update()
            boolean(slab, cm)
    # dentículos sob a primeira laje
    for side in range(4):
        rot = side * math.pi / 2
        for i in range(7):
            if r.random() < 0.08 * dano:
                continue
            u = -0.27 + i * 0.09
            o = block(C, 'pedra', (0, 0, 0), (0.06, 0.05, 0.065), jit=0.004, bev=0.005, bulge=('+y',), bamt=0.006)
            o.data.transform(Matrix.Rotation(rot, 4, 'Z') @ Matrix.Translation((u, 0.325, 2.725)))
    # lasca caída ao pé (o canto que faltou)
    f = list(cut_main.values())[0]
    size2 = (0.86 * f[0], 0.86 * f[1], 0.15 * f[2])
    tet = [Vector((0, 0, 0)), Vector((-lado * size2[0], 0, 0)), Vector((0, -size2[1], 0)), Vector((0, 0, -size2[2]))]
    nrm_ = (tet[1] - tet[0]).cross(tet[2] - tet[0]).normalized()
    ctr = sum(tet, Vector()) / 4
    tet += [p + (ctr - p) * 0.0 + Vector((0.0, 0.0, 0.0)) + (ctr - p).normalized() * 0.06 for p in tet[:4]]
    tet = [p * 1.0 for p in tet]
    bm = _hull_bm([p * 1.1 for p in tet], 0.008, 1)
    bf = max(bm.faces, key=lambda f: f.calc_area())  # assenta sobre a maior face
    q = bf.normal.rotation_difference(Vector((0, 0, -1)))
    _xf(bm, q.to_matrix().to_4x4())
    _xf(bm, Matrix.Rotation(r.uniform(0, 6.28), 4, 'Z'))
    zmin = min(v.co.z for v in bm.verts)
    _xf(bm, Matrix.Translation((lado * 0.80, 0.66, -zmin - 0.01)))
    C.add(bm, 'pedra', "lasca_capitel")

    # --- pináculo
    neck = block(C, 'pedra', (0, 0, 3.11), (0.40, 0.40, 0.10), bev=0.008, jit=0.005, bulge=('+x', '-x', '+y', '-y'))
    apex = Vector((r.uniform(-.012, .012), r.uniform(-.012, .012), 0.34))
    hb = 0.165
    pyr = [Vector((sx * hb, sy * hb, 0)) for sx in (-1, 1) for sy in (-1, 1)]
    pyr = [p + Vector((r.uniform(-.006, .006), r.uniform(-.006, .006), 0)) for p in pyr]
    pyr += [apex]
    for sx, sy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        pyr.append(Vector((sx * (hb * 0.55 + .004) + sy * r.uniform(-.02, .02), sy * (hb * 0.55 + .004) + sx * r.uniform(-.02, .02), 0.17)))
    bm = _hull_bm(pyr, 0.006, 1, 0.3)
    _xf(bm, Matrix.Translation((0, 0, 3.16)))
    pyr_o = C.add(bm, 'pedra', "piramide")
    ck = cutter_obj(C, _hull_bm(box_pts(r, (0.26, 0.2, 0.2), 0.02), 0.0))
    ck.location = (lado * 0.15, 0.16, 3.20)
    ck.rotation_euler = (0.55, 0.45, 0.6)
    bpy.context.view_layer.update()
    boolean(pyr_o, ck)
    if dano > 0.8:  # ponta quebrada
        ck2 = cutter_obj(C, _hull_bm(box_pts(r, (0.5, 0.5, 0.3), 0.0), 0.0))
        ck2.location = (0.0, 0.0, 3.16 + 0.34 + 0.02)
        ck2.rotation_euler = (0.55, -0.35, 0.0)
        bpy.context.view_layer.update()
        boolean(pyr_o, ck2)
    # --- entulho ao pé e nos degraus: poucas peças grandes, muitas pequenas e cascalho, em aglomerados
    clusters = [(r.uniform(0, 2 * math.pi), r.uniform(0.7, 0.95)) for _ in range(3 + int(2 * dano))]
    def pile_pos():
        if r.random() < 0.8:
            a0, d0 = r.choice(clusters)
            a = a0 + r.gauss(0, 0.35)
            d = d0 + abs(r.gauss(0, 0.16))
        else:
            a = r.uniform(0, 2 * math.pi)
            d = r.uniform(0.75, 1.25)
        return math.cos(a) * d, math.sin(a) * d
    for _ in range(int(3 + 3 * dano)):  # grandes
        px, py = pile_pos()
        sz = r.uniform(0.14, 0.24)
        rock(C, 'pedra' if r.random() < 0.75 else 'escura', (px, py, 0), (sz * r.uniform(1, 1.5), sz * r.uniform(.8, 1.2), sz * r.uniform(.55, .9)), bury=r.uniform(0.25, 0.4))
    for _ in range(int(15 + 10 * dano)):  # médias
        px, py = pile_pos()
        sz = r.uniform(0.06, 0.12)
        rock(C, 'pedra' if r.random() < 0.7 else 'escura', (px, py, 0), (sz * r.uniform(1, 1.6), sz * r.uniform(.7, 1.2), sz * r.uniform(.4, .9)), bury=r.uniform(0.15, 0.4))
    for _ in range(int(40 + 30 * dano)):  # cascalho
        px, py = pile_pos()
        sz = r.uniform(0.025, 0.055)
        rock(C, 'pedra' if r.random() < 0.6 else 'escura', (px, py, 0), (sz * r.uniform(1, 1.8), sz * r.uniform(.7, 1.3), sz * r.uniform(.5, 1)), bury=r.uniform(0.1, 0.4), bev=0.002)
    for _ in range(int(8 + 5 * dano)):  # lascas planas e angulosas vindas das quinas
        px, py = pile_pos()
        sz = r.uniform(0.07, 0.15)
        rock(C, 'pedra', (px, py, 0), (sz * r.uniform(1, 1.5), sz * r.uniform(.6, 1.1), sz), flat=0.22, bury=0.1, n=r.randint(7, 9), bev=0.003)
    for _ in range(7):  # sobre o degrau A
        side = r.randint(0, 3)
        u = r.uniform(-0.46, 0.46)
        v = r.uniform(0.485, 0.545)
        px, py = [(u, v), (v, -u), (-u, -v), (-v, u)][side]
        sz = r.uniform(0.025, 0.07)
        rock(C, 'pedra', (px, py, 0.34), (sz * 1.4, sz, sz * .7), bev=0.003, bury=0.2)
    # --- musgo discreto (topos e saliências)
    for _ in range(int(7 + 2 * dano)):
        side = r.randint(0, 3)
        u = r.uniform(-0.4, 0.4)
        v = r.uniform(0.49, 0.54)
        px, py = [(u, v), (v, -u), (-u, -v), (-v, u)][side]
        moss(C, (px, py, 0.345), r.uniform(0.035, 0.075))
    for _ in range(3):
        side = r.randint(0, 3)
        u = r.uniform(-0.33, 0.33)
        v = r.uniform(0.40, 0.44)
        px, py = [(u, v), (v, -u), (-u, -v), (-v, u)][side]
        moss(C, (px, py, 0.665), r.uniform(0.03, 0.055))
    for _ in range(3):  # topo da laje 3
        a = r.uniform(0, 2 * math.pi)
        d = r.uniform(0.27, 0.31)
        moss(C, (math.cos(a) * d, math.sin(a) * d, 3.06), r.uniform(0.03, 0.05))
    for _ in range(2):  # pé do fuste
        px = r.choice((-1, 1)) * r.uniform(0.18, 0.30)
        moss(C, (px, r.uniform(0.33, 0.37), 1.0), r.uniform(0.03, 0.05))
    moss(C, (0.0, 0.33, 2.375), 0.03)  # em cima da arquivolta
    moss(C, (lado * 0.2, 0.43, 2.97 + 0.0), 0.05)  # topo da laje 2 (ressalto externo)
    # fio de musgo vertical numa junta
    moss(C, (r.choice((-1, 1)) * 0.3, 0.2, 1.0 + 0.0), 0.0 + 0.04, normal=(1, 0, 0)) if False else None


def _bevel_obj(o, w):
    md = o.modifiers.new("bv", 'BEVEL')
    md.width = w
    md.segments = 1
    md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(30)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=md.name)


def _torus(C, loc, R, rr, rot, key, nu=16, nv=8):
    bm = bmesh.new()
    vs = []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        row = []
        for j in range(nv):
            b = 2 * math.pi * j / nv
            rad = R + rr * math.cos(b)
            row.append(bm.verts.new((math.cos(a) * rad, math.sin(a) * rad, rr * math.sin(b))))
        vs.append(row)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((vs[i][j], vs[(i + 1) % nu][j], vs[(i + 1) % nu][(j + 1) % nv], vs[i][(j + 1) % nv]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    place(bm, loc, rot)
    return C.add(bm, key, "argola")


def build_coluna(x, lado, seed, M):
    C = _Ctx(seed, M, lado)
    _montar(C)
    for o in C.tmp:
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(me)
    out = []
    for key, objs in C.parts.items():
        objs = [o for o in objs if o.name in bpy.data.objects and len(o.data.polygons)]
        if not objs:
            continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            if o.data.materials:
                o.data.materials.clear()
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1:
            bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active
        o.name = f"CC_Coluna_{'E' if lado < 0 else 'D'}_{key}"
        me = o.data
        me.name = o.name
        me.materials.append(M[key])
        me.polygons.foreach_set("use_smooth", [False] * len(me.polygons))
        me.update()
        o.location = (x, 0, 0)
        out.append(o)
    return out
