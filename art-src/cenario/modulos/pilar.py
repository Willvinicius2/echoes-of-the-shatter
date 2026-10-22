"""Pilar da Cripta com estátua em nicho, versão detalhada (referência: referencias-cripta/pilar.png).
Pedra em blocos com arestas quebradas, nicho em arco ogival, colunetas com capitel de quadrifólio, cornija,
entulho no topo e na base, estátua encapuzada com espada. Metros, pivô no centro da base, frente = +Y do Blender.
python3 pilar.py <pasta_saida> [pasta_previas]     (módulo bpy do pip, ou: blender -b --factory-startup -P pilar.py -- ...)
Materiais com os mesmos nomes do modulos_cripta.py: M_Pedra / M_PedraEscura recebem a pedra triplanar no Godot."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None
ONLY = os.environ.get("PILAR_VISTA")
rnd = random.Random(11)
objs = []


def mat(name, color, metal=0.0, rough=0.85):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    return m


def reset():
    global M_PEDRA, M_ESCURA, M_ESTATUA, M_MUSGO, M_FERRO
    bpy.ops.wm.read_factory_settings(use_empty=True); objs.clear()
    M_PEDRA = mat("M_Pedra", (0.42, 0.42, 0.46))
    M_ESCURA = mat("M_PedraEscura", (0.16, 0.16, 0.19))
    M_ESTATUA = mat("M_Estatua", (0.22, 0.21, 0.20), rough=0.9)
    M_MUSGO = mat("M_Musgo", (0.08, 0.12, 0.05), rough=1.0)
    M_FERRO = mat("M_Ferro", (0.075, 0.07, 0.08), metal=0.7, rough=0.5)


def from_bm(bm, m, name="p"):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    me.materials.append(m); objs.append(o)
    return o


def bevel_bm(bm, off, seg=2):
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=off, segments=seg, affect='EDGES', profile=0.55)


def rock(loc, size, m=None, rot=(0, 0, 0), jit=0.0, bev=0.03, cuts=0, seg=2):
    """Bloco de pedra: cubo subdividido, vértices deslocados (quina lascada) e chanfro em 2 segmentos."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if cuts:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    sx, sy, sz = size
    for v in bm.verts:
        v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
        if jit:
            v.co += Vector((rnd.uniform(-1, 1) * jit * sx, rnd.uniform(-1, 1) * jit * sy, rnd.uniform(-1, 1) * jit * sz))
    if bev:
        bevel_bm(bm, min(bev, 0.3 * min(size)), seg)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X'), verts=bm.verts)
    return from_bm(bm, m or M_PEDRA, "rock")


def prism(poly, y0, y1, m=None):
    """Extrusão em Y de um polígono 2D (x, z)."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in poly]
    b = [bm.verts.new((x, y1, z)) for x, z in poly]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    n = len(poly)
    for i in range(n):
        bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return from_bm(bm, m or M_ESCURA, "prism")


def boolean(o, cutters, op='DIFFERENCE'):
    for c in cutters:
        md = o.modifiers.new("b", 'BOOLEAN'); md.operation = op; md.object = c; md.solver = 'EXACT'
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=md.name)
        bpy.data.objects.remove(c, do_unlink=True)
        if c in objs: objs.remove(c)


def ogive(w, h_side, rise, n=8):
    """Polígono (x, z) de um arco ogival de largura 2w: lados até h_side e duas curvas de raio 2w até a ponta."""
    r = 2 * w
    a_tip = math.acos((r - w) / r)
    right = [((w - r) + r * math.cos(a_tip * i / n), h_side + r * math.sin(a_tip * i / n)) for i in range(1, n + 1)]
    left = [(-x, z) for x, z in reversed(right[:-1])]
    return [(-w, 0), (w, 0), (w, h_side)] + right + left + [(-w, h_side)]


# ------------------------------------------------------------------ peças
def moss(x, y, z, sx, sy, sz=0.06):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.5)
    for v in bm.verts:
        v.co.x *= sx * (1 + rnd.uniform(-.15, .15)); v.co.y *= sy * (1 + rnd.uniform(-.15, .15)); v.co.z *= sz
    bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y, z)), verts=bm.verts)
    return from_bm(bm, M_MUSGO, "musgo")


def course_ring(half, z0, h, nx, t, m=None, jit=0.012, miss=0.0):
    """Fiada de blocos em anel (lado = 2*half), nx blocos por lado, espessura t."""
    L = 2 * half
    step = L / nx
    for side in range(4):
        rot = side * math.pi / 2
        c, s = math.cos(rot), math.sin(rot)
        for i in range(nx):
            if miss and rnd.random() < miss: continue
            u = -half + step * (i + 0.5)
            ww = step * rnd.uniform(0.9, 1.0) - 0.03
            hh = h * rnd.uniform(0.95, 1.0) - 0.02
            # bloco na face +Y rodado
            px, py = u, half - t / 2
            o = rock((px * c - py * s, px * s + py * c, z0 + h / 2), (ww, t, hh), m, (0, 0, rot), jit=jit, bev=0.035)


def colonnette(x, y_face, z0, z1):
    """Coluneta quadrada de face (sobre a face +Y): base em 2 degraus, fuste com filete, capitel com quadrifólio."""
    w = 0.26
    yc = y_face + 0.07
    rock((x, yc, z0 + 0.09), (w + 0.12, 0.2, 0.18), M_PEDRA, jit=0.01, bev=0.025)
    rock((x, yc, z0 + 0.23), (w + 0.05, 0.17, 0.12), M_PEDRA, jit=0.01, bev=0.02)
    hs = z1 - z0 - 0.29 - 0.42
    # fuste em duas peças com junta, e filete central
    h1 = hs * 0.55
    rock((x, yc, z0 + 0.29 + h1 / 2), (w, 0.15, h1 - 0.02), M_PEDRA, jit=0.008, bev=0.022)
    rock((x, yc, z0 + 0.29 + h1 + (hs - h1) / 2), (w, 0.15, hs - h1 - 0.02), M_PEDRA, jit=0.008, bev=0.022)
    rock((x, yc + 0.075, z0 + 0.29 + hs / 2), (0.05, 0.02, hs - 0.1), M_ESCURA, bev=0.005, cuts=0)  # filete
    rock((x, yc, z1 - 0.40), (w + 0.04, 0.17, 0.08), M_PEDRA, bev=0.015)       # colarinho
    cap = rock((x, yc, z1 - 0.21), (w + 0.12, 0.22, 0.30), M_PEDRA, jit=0.006, bev=0.02, cuts=2, seg=1)
    # quadrifólio (4 folhas + centro) cortado na face frontal do capitel
    cut = []
    qy = yc + 0.11
    for dx, dz in ((0.055, 0), (-0.055, 0), (0, 0.055), (0, -0.055)):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.05, radius2=0.05, depth=0.12,
                              matrix=Matrix.Translation((x + dx, qy, z1 - 0.21 + dz)) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
        cut.append(from_bm(bm, M_ESCURA, "q"))
    boolean(cap, cut)
    rock((x, yc, z1 - 0.04), (w + 0.2, 0.26, 0.09), M_PEDRA, jit=0.01, bev=0.02)  # ábaco


def face(niche):
    """Uma face do fuste (orientada para +Y). Fuste: 1.9 x 1.9, de z=1.0 a z=4.75."""
    F = 0.95
    z0, z1 = 1.05, 4.75
    for sx in (-1, 1):
        colonnette(sx * 0.70, F, z0, z1)
    # painel central: blocos grandes encaixados entre as colunetas (parte do fuste em relevo leve)
    if niche:
        return
    # painel de blocos rachado (costas e laterais)
    rows = [(1.20, 1.72), (1.72, 2.52), (2.52, 3.45), (3.45, 4.15), (4.15, 4.70)]
    for (a, b) in rows:
        x = -0.48
        while x < 0.46:
            wcell = rnd.choice([0.30, 0.38, 0.46]); wcell = min(wcell, 0.48 - x)
            if wcell < 0.12: break
            rock((x + wcell / 2, F + 0.018, (a + b) / 2), (wcell - 0.025, 0.05, (b - a) - 0.025), M_PEDRA, jit=0.02, bev=0.02)
            x += wcell
    # rachadura em Y: sulco escuro diagonal
    for i in range(6):
        t = i / 5
        rock((-0.3 + t * 0.7 + rnd.uniform(-.03, .03), F + 0.044, 3.9 - t * 1.7), (0.04, 0.03, 0.30), M_ESCURA, rot=(0, rnd.uniform(-.7, -.2), 0), bev=0, cuts=0)


# ------------------------------------------------------------------ estátua
def ring(c, rx, ry, n=16, z=0.0, fold=0.0, ph=0.0):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + fold * math.sin(a * 4 + ph) * math.cos(z * 9 + ph)
        pts.append(Vector((c[0] + rx * k * math.cos(a), c[1] + ry * k * math.sin(a), z)))
    return pts


def loft(rings, m, cap_top=True, cap_bot=True):
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(vs[0])
    for j in range(len(vs) - 1):
        for i in range(n):
            bm.faces.new((vs[j][i], vs[j][(i + 1) % n], vs[j + 1][(i + 1) % n], vs[j + 1][i]))
    if cap_bot: bm.faces.new(vs[0][::-1])
    if cap_top: bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.3, use_axis_x=True, use_axis_y=True, use_axis_z=True) if False else None
    o = from_bm(bm, m, "loft"); o["liso"] = 1
    md = o.modifiers.new("ss", 'SUBSURF'); md.levels = 1; md.render_levels = 1
    return o


def tube(p0, p1, r0, r1, m, n=10, fold=0.0):
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0); L = d.length
    q = d.to_track_quat('Z', 'Y')
    rings = []
    for k in range(5):
        t = k / 4
        r = r0 + (r1 - r0) * t
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            pts.append(p0 + d * t + q @ Vector((r * math.cos(a) * (1 + fold * math.sin(a * 3 + t * 6)), r * math.sin(a), 0)))
        rings.append(pts)
    return loft(rings, m)


def estatua(x, y, z, e=1.0):
    """Figura encapuzada: manto com dobras, mãos sobre o punho da espada, capuz com rosto na sombra."""
    # manto: seções (altura, rx, ry, deslocamento y)
    secs = [(0.00, 0.40, 0.30, 0.00), (0.10, 0.38, 0.29, 0.00), (0.45, 0.30, 0.23, 0.00), (0.90, 0.24, 0.19, 0.00),
            (1.25, 0.22, 0.17, 0.00), (1.45, 0.30, 0.17, 0.00), (1.56, 0.20, 0.13, 0.00), (1.62, 0.12, 0.10, 0.00)]
    rings = [ring((x, y + s[3] * e), s[1] * e, s[2] * e, 20, z + s[0] * e, fold=0.11 if s[0] < 1.2 else 0.03, ph=0.5) for s in secs]
    loft(rings, M_ESTATUA)
    # capuz: calota com bico, aba escura na frente
    hood = [ring((x, y - 0.01 * e), r * e, r2 * e, 16, z + zz * e) for zz, r, r2 in
            [(1.56, 0.17, 0.15), (1.66, 0.21, 0.19), (1.80, 0.22, 0.20), (1.94, 0.19, 0.17), (2.06, 0.13, 0.12), (2.14, 0.07, 0.07), (2.18, 0.01, 0.01)]]
    loft(hood, M_ESTATUA)
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.14 * e)
    for v in bm.verts: v.co.x *= 0.95; v.co.y *= 0.8; v.co.z *= 1.25
    bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y + 0.12 * e, z + 1.82 * e)), verts=bm.verts)
    from_bm(bm, M_ESCURA, "rosto")
    # aba do capuz (moldura do rosto)
    for sx in (-1, 1):
        tube((x + sx * 0.17 * e, y + 0.07 * e, z + 1.68 * e), (x + sx * 0.12 * e, y + 0.11 * e, z + 2.02 * e), 0.05 * e, 0.045 * e, M_ESTATUA, 8)
    # braços: ombro -> cotovelo (para fora) -> mãos no punho
    hx, hy, hz = x, y + 0.27 * e, z + 1.05 * e
    for sx in (-1, 1):
        sh = (x + sx * 0.28 * e, y, z + 1.42 * e)
        el = (x + sx * 0.34 * e, y + 0.07 * e, z + 1.10 * e)
        ha = (x + sx * 0.04 * e, hy, hz + (0.04 if sx > 0 else -0.04) * e)
        tube(sh, el, 0.095 * e, 0.095 * e, M_ESTATUA, 10, fold=0.1)
        tube(el, ha, 0.10 * e, 0.07 * e, M_ESTATUA, 10, fold=0.1)   # manga se estreitando
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.06 * e)
        bmesh.ops.transform(bm, matrix=Matrix.Translation(ha), verts=bm.verts)
        from_bm(bm, M_ESTATUA, "mao")
    # espada com ponta para baixo, apoiada no chão: punho e cruzeta nas mãos
    sy = hy
    tube((x, sy, hz + 0.28 * e), (x, sy, hz - 0.02 * e), 0.025 * e, 0.025 * e, M_FERRO, 8)           # empunhadura
    rock((x, sy, hz + 0.31 * e), (0.07 * e, 0.07 * e, 0.07 * e), M_FERRO, bev=0.012, cuts=0)           # pomo
    rock((x, sy, hz - 0.04 * e), (0.40 * e, 0.06 * e, 0.045 * e), M_FERRO, bev=0.012, cuts=0)          # guarda
    for sx in (-1, 1):
        rock((x + sx * 0.21 * e, sy, hz - 0.03 * e), (0.05 * e, 0.05 * e, 0.09 * e), M_FERRO, bev=0.01, cuts=0)  # pontas da guarda
    rock((x, sy, z + (hz - z) / 2 - 0.05 * e), (0.07 * e, 0.025 * e, (hz - z) - 0.09 * e), M_FERRO, bev=0.008, cuts=0)  # lâmina
    # pedestal da estátua
    rock((x, y, z - 0.07), (1.0, 0.8, 0.14), M_PEDRA, jit=0.01, bev=0.03)


# ------------------------------------------------------------------ montagem
def pilar():
    reset()
    # soco: três fiadas de blocos (cada uma recuada) com miolo
    rock((0, 0, 0.17), (2.9, 2.9, 0.34), M_ESCURA, bev=0.02, cuts=0)
    course_ring(1.60, 0.0, 0.36, 6, 0.50)
    course_ring(1.32, 0.36, 0.34, 5, 0.46)
    course_ring(1.12, 0.70, 0.34, 5, 0.40)
    rock((0, 0, 0.9), (2.1, 2.1, 0.4), M_ESCURA, bev=0.02, cuts=0)
    # cornija de base do fuste
    rock((0, 0, 1.03), (2.15, 2.15, 0.1), M_PEDRA, jit=0.01, bev=0.03)
    rock((0, 0, 1.12), (2.02, 2.02, 0.1), M_PEDRA, jit=0.01, bev=0.03)

    # fuste: núcleo com nicho cortado na frente
    core = rock((0, 0, 2.95), (1.9, 1.9, 3.75), M_PEDRA, bev=0.025, cuts=0)
    nw, nz0 = 0.56, 1.25
    cutp = ogive(nw, 1.75, 0, 9)
    cutter = prism([(x, z + nz0) for x, z in cutp], 0.55, 1.2, M_ESCURA)
    boolean(core, [cutter])
    # moldura do arco: anel ogival saliente
    outer = prism([(x * 1.0, z + nz0 - 0.0) for x, z in ogive(nw + 0.13, 1.75, 0, 9)], 0.93, 1.03, M_PEDRA)
    inner = prism([(x, z + nz0) for x, z in ogive(nw, 1.75, 0, 9)], 0.80, 1.20, M_ESCURA)
    boolean(outer, [inner])
    # tímpano em relevo no fundo do nicho (arco menor, mais escuro)
    prism([(x, z + nz0 + 0.02) for x, z in ogive(nw - 0.12, 1.65, 0, 7)], 0.545, 0.585, M_ESCURA)

    # faces: 0 = frente (com nicho), 1..3 = outras, giradas em torno de Z
    for i in range(4):
        n0 = len(objs)
        face(niche=(i == 0))
        ang = i * math.pi / 2
        if i:
            for o in objs[n0:]:
                o.matrix_world = Matrix.Rotation(ang, 4, 'Z') @ o.matrix_world
                bpy.context.view_layer.objects.active = o
    # (as faces 1..3 são aplicadas ao mundo ao juntar)

    estatua(0, 0.78, 1.15, 1.12)

    # cornija e coroamento
    for (w, z, h) in ((2.12, 4.82, 0.12), (2.28, 4.95, 0.14)):
        course_ring(w / 2, z - h / 2, h, 4, 0.30, M_PEDRA, jit=0.01)
    rock((0, 0, 5.08), (2.0, 2.0, 0.14), M_ESCURA, bev=0.02, cuts=0)
    course_ring(1.30, 5.15, 0.50, 4, 0.55, M_PEDRA, jit=0.05, miss=0.2)
    rock((0, 0, 5.40), (2.1, 2.1, 0.5), M_ESCURA, bev=0.02, cuts=0)
    # entulho no topo: blocos tombados e lascas
    for _ in range(30):
        r = rnd.uniform(0.0, 1.0) ** 0.8
        a = rnd.uniform(0, 6.283)
        px, py = math.cos(a) * r * 0.95, math.sin(a) * r * 0.95
        s = rnd.uniform(0.25, 0.60)
        rock((px, py, 5.62 + rnd.uniform(0, 0.75) * (1 - r * 0.7)), (s, s * rnd.uniform(0.7, 1.1), s * rnd.uniform(0.5, 0.9)),
             M_PEDRA if rnd.random() < 0.7 else M_ESCURA, rot=(rnd.uniform(-.4, .4), rnd.uniform(-.4, .4), rnd.uniform(0, 3)),
             jit=0.09, bev=0.045, cuts=1)

    # lascas e entulho no soco e no chão
    for _ in range(14):
        a = rnd.uniform(0, 6.283); r = rnd.uniform(1.4, 1.7)
        s = rnd.uniform(0.16, 0.42)
        rock((math.cos(a) * r, math.sin(a) * r, s * 0.35), (s, s * rnd.uniform(.7, 1.2), s * 0.7), M_PEDRA if rnd.random() < .6 else M_ESCURA,
             rot=(rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), a), jit=0.09, bev=0.04, cuts=1)
    for _ in range(7):
        a = rnd.uniform(0, 6.283); r = rnd.uniform(0.9, 1.15)
        s = rnd.uniform(0.12, 0.26)
        rock((math.cos(a) * r, math.sin(a) * r, 0.88 + s * 0.3), (s, s, s * 0.7), M_PEDRA, rot=(0, 0, a), jit=0.1, bev=0.03, cuts=1)

    # musgo nas juntas
    for (x, y, z, sx, sy) in ((-1.3, 1.45, 0.37, .9, .6), (1.0, 1.55, 0.71, .6, .45), (0.0, 1.05, 1.0, .8, .3),
                              (-1.05, 0.3, 1.0, .4, .7), (1.0, -0.4, 0.37, .5, .9), (-0.5, -1.55, 0.37, .8, .5),
                              (0.6, -1.0, 1.15, .6, .15)):
        moss(x, y, z, sx, sy)
    # musgo vertical nas faces
    for (x, y, z) in ((-0.95, 0.5, 3.2), (0.8, -0.955, 2.5), (0.955, 0.1, 2.0)):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.5)
        for v in bm.verts: v.co.x *= 0.05; v.co.y *= 0.35; v.co.z *= 0.5
        bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y, z)), verts=bm.verts)
        from_bm(bm, M_MUSGO, "musgo")


# ------------------------------------------------------------------ exportação e prévias
def juntar():
    for o in objs:
        if o.modifiers:
            bpy.context.view_layer.objects.active = o
            for md in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=md.name)
        o.data.update()
        for p in o.data.polygons: p.use_smooth = bool(o.get("liso"))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = "SM_Cripta_Pilar"
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    # normais suaves só onde o ângulo é pequeno
    bpy.ops.object.shade_smooth(keep_sharp_edges=False) if False else None
    md = o.modifiers.new("w", 'WEIGHTED_NORMAL') if False else None
    o.data.set_sharp_from_angle(angle=math.radians(35)) if hasattr(o.data, "set_sharp_from_angle") else None
    return o


def render(o, nome, view, res=720, samples=40):
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        if ob.type in ('CAMERA', 'LIGHT'): bpy.data.objects.remove(ob, do_unlink=True)
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam)
    h = o.dimensions.z
    target = Vector((0, 0, h * 0.5))
    views = {"frente": (0, 1, 0.25), "tres_quartos": (0.8, 1, 0.55), "costas": (0.5, -1, 0.3), "topo": (0.4, 0.6, 1.6),
             "nicho": (0.0, 1, 0.05), "baixo": (0.6, 1, 0.1)}
    dx, dy, dz = views[view]
    d = h * 2.4
    cam.location = target + Vector((dx, dy, dz)).normalized() * d
    if view == "nicho":
        target = Vector((0, 0.7, 2.1)); cam.location = target + Vector((0.25, 1.0, 0.15)).normalized() * 3.2
        cam.data.lens = 85
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    if view != "nicho": cam.data.lens = 60
    sun = bpy.data.objects.new("s", bpy.data.lights.new("s", 'SUN')); sun.data.energy = 4.0; sun.rotation_euler = (0.9, 0.25, 0.7)
    bpy.context.collection.objects.link(sun)
    fill = bpy.data.objects.new("f", bpy.data.lights.new("f", 'SUN')); fill.data.energy = 0.8; fill.rotation_euler = (1.2, 0, -2.2)
    bpy.context.collection.objects.link(fill)
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.12, 0.13, 0.17, 1); sc.world = w
    sc.render.engine = 'CYCLES'; sc.cycles.samples = samples; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = True
    sc.render.resolution_x = res; sc.render.resolution_y = res
    sc.render.filepath = os.path.join(PREV, f"{nome}_{view}.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    pilar()
    o = juntar()
    print("faces", len(o.data.polygons), "tris~", sum(len(p.vertices) - 2 for p in o.data.polygons), "dim", tuple(round(v, 2) for v in o.dimensions))
    if OUT and not os.environ.get("PILAR_SEM_GLB"):
        os.makedirs(OUT, exist_ok=True)
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SM_Cripta_Pilar.glb"), use_selection=True, export_format='GLB', export_yup=True)
    if PREV:
        os.makedirs(PREV, exist_ok=True)
        for v in (ONLY.split(",") if ONLY else ("frente", "tres_quartos")):
            render(o, "pilar", v)
