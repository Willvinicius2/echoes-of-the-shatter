"""Estátua encapuzada da Cripta, remodelada com mais detalhe e quebras (referência de estilo: modulos_cripta.py).
Gera SM_Cripta_Estatua.glb em metros, pivô no centro da base, frente voltada para +Y do Blender (-Z do Godot).
  python estatua.py <pasta_saida> [pasta_previas]          (módulo bpy: pip install bpy; ou: blender -b --factory-startup -P estatua.py -- ...)
Materiais: M_Estatua (pedra, textura triplanar no Godot), M_Musgo, M_PedraEscura (vazio do capuz), M_Ouro (filete rúnico)."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None
random.seed(11)
S = 1.25            # escala da figura (igual à estátua antiga: ~3 m com plinto)
PLINTO_H = 0.62
N = 72              # setores por anel

def mat(name, color, metal=0.0, rough=0.85):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    return m

bpy.ops.wm.read_factory_settings(use_empty=True)
M_ESTATUA = mat("M_Estatua", (0.22, 0.21, 0.20), rough=0.9)
M_MUSGO = mat("M_Musgo", (0.08, 0.12, 0.05), rough=1.0)
M_ESCURA = mat("M_PedraEscura", (0.05, 0.05, 0.06))
M_OURO = mat("M_Ouro", (0.72, 0.52, 0.16), metal=0.9, rough=0.4)
MATS = [M_ESTATUA, M_MUSGO, M_ESCURA, M_OURO]
IDX = {"pedra": 0, "musgo": 1, "escura": 2, "ouro": 3}

def lerp(a, b, t): return a + (b - a) * t
def prof(tab, z):
    """Interpola linearmente uma tabela [(z, valor), ...]."""
    if z <= tab[0][0]: return tab[0][1]
    for (z0, v0), (z1, v1) in zip(tab, tab[1:]):
        if z <= z1: return lerp(v0, v1, (z - z0) / (z1 - z0))
    return tab[-1][1]

def new_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    for m in MATS: me.materials.append(m)
    return o

def loft(rings, cap_bottom=True, cap_top=True):
    """rings: lista de anéis (cada um uma lista de Vector de mesmo tamanho), de baixo para cima."""
    bm = bmesh.new(); n = len(rings[0])
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    for a, b in zip(vs, vs[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    if cap_bottom: bm.faces.new(vs[0][::-1])
    if cap_top: bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm

def subdiv(bm, cuts=1):
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])

def fbm(p, f, oct=3):
    v, a = 0.0, 1.0
    for _ in range(oct):
        v += noise.noise(p * f) * a; f *= 2.1; a *= 0.5
    return v

def displace(bm, fn):
    """fn(co, normal) -> deslocamento ao longo da normal."""
    bm.normal_update()
    for v in bm.verts: v.co += v.normal * fn(v.co.copy(), v.normal.copy())

def dist_seg(p, a, b):
    ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length

# ---------- rachaduras (em coordenadas da figura, 0..1.92) ----------
def crack_poly(start, steps, seed):
    r = random.Random(seed); pts = [Vector(start)]
    for _ in range(steps):
        d = Vector((r.uniform(-0.05, 0.05), r.uniform(-0.03, 0.03), -r.uniform(0.05, 0.11)))
        pts.append(pts[-1] + d)
    return pts
CRACKS = [crack_poly((0.18, 0.2, 1.40), 9, 1), crack_poly((-0.25, 0.22, 1.05), 8, 2),
          crack_poly((0.05, 0.36, 0.70), 7, 3), crack_poly((-0.12, -0.30, 1.25), 8, 4)]
def crack_depth(co, w=0.016, d=0.028):
    m = min(dist_seg(co, a, b) for c in CRACKS for a, b in zip(c, c[1:]))
    return -d * max(0.0, 1.0 - m / w) ** 0.8

def stone(co, n, amp=0.005):
    """Aspereza de pedra esculpida + rachaduras."""
    return fbm(co, 9, 2) * amp + fbm(co + Vector((9, 3, 1)), 45, 2) * amp * 0.6 + crack_depth(co)

# ---------- manto (túnica) ----------
A_T = [(0, 0.54), (0.12, 0.49), (0.5, 0.40), (0.95, 0.34), (1.3, 0.34), (1.43, 0.30), (1.53, 0.17)]   # semilargura (x)
B_T = [(0, 0.47), (0.12, 0.42), (0.5, 0.34), (0.95, 0.27), (1.3, 0.22), (1.43, 0.20), (1.53, 0.16)]   # semiprofundidade (y)
def manto():
    rings = []; zs = [i / 70 * 1.55 for i in range(71)]
    for z in zs:
        a, b = prof(A_T, z), prof(B_T, z); ring = []
        fold = 0.075 * (1 - z / 1.8) + 0.012
        for i in range(N):
            t = i / N * math.tau
            c, s = math.cos(t), math.sin(t)
            r = 1 - fold * 1.3 * abs(math.sin(4.5 * t + z * 1.6 + 0.7 * math.sin(z * 4))) + fold * 0.5 * math.sin(11 * t - z * 3) + 0.03 * math.sin(3 * t + 1)
            # barra do manto ondulada e levantada atrás
            zz = z + (0.05 * math.sin(5 * t + 0.4) if z < 0.12 else 0)
            ring.append(Vector((a * c * r, b * s * r - (0.03 if z > 1.2 else 0), zz)))
        rings.append(ring)
    bm = loft(rings, True, True)
    subdiv(bm, 1)
    displace(bm, lambda co, n: stone(co, n))
    return new_obj("manto", bm)

# ---------- capuz ----------
def capuz():
    rings = []; zs = [1.40 + i / 50 * 0.62 for i in range(51)]
    for z in zs:
        t01 = (z - 1.40) / 0.62
        R = prof([(0, 0.19), (0.18, 0.25), (0.45, 0.235), (0.8, 0.12), (1.0, 0.0)], t01)
        cy = -0.02 - 0.20 * t01 ** 2.2              # a ponta tomba para trás
        rx, ry = R * 0.95, R * 1.12; ring = []
        for i in range(N):
            t = i / N * math.tau
            c, s = math.cos(t), math.sin(t)
            r = 1 + 0.035 * math.sin(6 * t + z * 5) * (1 - t01 * 0.5)
            ring.append(Vector((rx * c * r, cy + ry * s * r, z + 0.0)))
        rings.append(ring)
    bm = loft(rings, True, True)
    subdiv(bm, 1)
    # abertura do rosto: afunda a frente do capuz
    def fn(co, n):
        k = 0.0
        if co.y > -0.02 and 1.50 < co.z < 1.86:
            fx = max(0.0, 1 - (co.x / 0.115) ** 2)
            fz = max(0.0, 1 - ((co.z - 1.66) / 0.17) ** 2)
            k = -0.15 * fx * fz
        return k + stone(co, n, 0.008)
    displace(bm, fn)
    for f in bm.faces:                                   # vazio escuro dentro do capuz
        c = f.calc_center_median()
        if c.y > -0.02 and abs(c.x) < 0.095 and 1.53 < c.z < 1.83 and (c.x / 0.095) ** 2 + ((c.z - 1.67) / 0.14) ** 2 < 1:
            f.material_index = IDX["escura"]
    # a ponta do capuz quebrou: corte inclinado
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector((0, -0.10, 1.93)), plane_no=Vector((0, -0.45, 1)).normalized(), clear_outer=True)
    edges = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    filled = bmesh.ops.holes_fill(bm, edges=edges, sides=64)
    for f in filled["faces"]: f.material_index = IDX["pedra"]
    for v in bm.verts:                                   # fratura irregular no corte
        if abs((v.co - Vector((0, -0.10, 1.93))).dot(Vector((0, -0.45, 1)).normalized())) < 0.02:
            v.co.z += fbm(v.co, 30) * 0.015
    return new_obj("capuz", bm)

# ---------- braços ----------
def bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return p0 * u ** 3 + p1 * 3 * u * u * t + p2 * 3 * u * t * t + p3 * t ** 3

def tubo(path, radii, sides=18, cap_end=True):
    """Tubo ao longo de um caminho (lista de Vector) com raios."""
    rings = []; up = Vector((0, 0, 1))
    for i, (p, r) in enumerate(zip(path, radii)):
        tg = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        side = tg.cross(up if abs(tg.z) < 0.9 else Vector((1, 0, 0))).normalized(); fw = side.cross(tg).normalized()
        rings.append([p + (side * math.cos(k / sides * math.tau) + fw * math.sin(k / sides * math.tau)) * r
                      for k in range(sides)])
    bm = loft(rings, True, cap_end)
    return bm

def braco(sx, quebrado):
    p0 = Vector((sx * 0.30, -0.01, 1.42)); p1 = Vector((sx * 0.40, 0.03, 1.15)); p2 = Vector((sx * 0.36, 0.18, 0.95)); p3 = Vector((sx * 0.07, 0.33, 1.00))
    n = 40; pts = [bezier(p0, p1, p2, p3, i / (n - 1)) for i in range(n)]
    rad = []
    for i in range(n):
        t = i / (n - 1)
        rad.append(prof([(0, 0.10), (0.35, 0.11), (0.55, 0.09), (0.85, 0.095), (1, 0.115)], t) * (1 + 0.1 * math.sin(t * 25)))   # manga abre no punho
    end = int(n * (0.80 if quebrado else 1.0))
    bm = tubo(pts[:end], rad[:end], 16, cap_end=True)
    subdiv(bm, 1)
    def fn(co, n):
        return stone(co, n, 0.008) + (fbm(co, 60, 2) * 0.012 if quebrado and (co - pts[end - 1]).length < 0.06 else 0)
    displace(bm, fn)
    return new_obj("braco", bm), pts

def mao(pts):
    """Punho fechado: bloco arredondado com dedos sugeridos por sulcos."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.075)
    for v in bm.verts: v.co *= Vector((1.25, 0.9, 0.85))
    subdiv(bm, 1)
    displace(bm, lambda co, n: 0.008 * math.sin(co.x * 160) * (1 if co.y > 0 else 0) + fbm(co, 40) * 0.006)
    o = new_obj("mao", bm); return o

# ---------- fragmentos e entulho ----------
def pedaco(nome, loc, raio, esc=(1, 1, 1), rot=(0, 0, 0), mat=0):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=raio)
    for v in bm.verts: v.co *= Vector(esc)
    displace(bm, lambda co, n: fbm(co, 9, 3) * raio * 0.55 + fbm(co, 30, 2) * raio * 0.12)
    # facetar: achata verts em planos aleatórios
    for v in bm.verts: v.co.z = max(v.co.z, -raio * 0.55)
    o = new_obj(nome, bm); o.location = loc; o.rotation_euler = rot
    for p in o.data.polygons: p.material_index = mat
    return o

def plinto():
    objs = []
    def bloco(nome, size, z, bev=0.035, seed=0):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev, segments=2, affect='EDGES')
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
        def fn(co, n):
            d = stone(co + Vector((0, 0, z * 3)), n, 0.016)
            # cantos lascados
            for sx, sy in ((1, 1), (-1, -1)):
                c = Vector((sx * size[0] / 2, sy * size[1] / 2, size[2] / 2))
                dd = (co - c).length
                if dd < 0.22: d -= 0.05 * (1 - dd / 0.22) * (0.6 + fbm(co, 20))
            return d
        displace(bm, fn)
        o = new_obj(nome, bm); o.location = (0, 0, z + size[2] / 2); return o
    objs.append(bloco("base_baixa", (1.30, 1.30, 0.28), 0.0))
    objs.append(bloco("base_alta", (1.02, 1.02, 0.26), 0.28))
    objs.append(bloco("tampo", (1.16, 1.16, 0.08), 0.54, 0.02))
    # filete de ouro rúnico na face frontal da base alta
    bm = bmesh.new()
    for sx in (-1, 1):
        bmesh.ops.create_cube(bm, size=1.0)
    bm.free()
    bm = bmesh.new()
    def faixa(cx, cz, w, h):
        v = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        for q in v: q.co = Vector((cx + q.co.x * w, 0.515 + q.co.y * 0.012, cz + q.co.z * h))
    faixa(0, 0.41, 0.74, 0.018); faixa(-0.37, 0.41, 0.018, 0.14); faixa(0.37, 0.41, 0.018, 0.14)
    for sh in (-0.14, 0.0, 0.14):   # losango central
        pass
    o = new_obj("filete", bm)
    for p in o.data.polygons: p.material_index = IDX["ouro"]
    objs.append(o)
    return objs

def montar():
    fig = []
    fig.append(manto()); fig.append(capuz())
    br_l, pts_l = braco(-1, False); fig.append(br_l)
    br_r, pts_r = braco(1, True); fig.append(br_r)
    m = mao(pts_l); m.location = pts_l[-1] + Vector((0.02, 0.05, -0.01)); m.rotation_euler = (0.2, 0, 0.45); fig.append(m)
    # ombros/dobra do manto sobre os braços: gola
    bm = loft([[Vector((0.255 * math.cos(i / N * math.tau), 0.215 * math.sin(i / N * math.tau) - 0.01, 1.44 + h)) * 1
                for i in range(N)] for h in (0.0, 0.05, 0.10)], True, True)
    subdiv(bm, 1); displace(bm, lambda co, n: stone(co, n, 0.01)); fig.append(new_obj("gola", bm))
    # une a figura e leva ao mundo
    bpy.ops.object.select_all(action='DESELECT')
    for o in fig: o.select_set(True)
    bpy.context.view_layer.objects.active = fig[0]; bpy.ops.object.join()
    f = bpy.context.object
    f.scale = (S, S, S); f.location = (0, 0, PLINTO_H); bpy.ops.object.transform_apply(location=True, scale=True)
    f.name = "figura"
    # planta do manto encostada no tampo (afunda um pouco para não flutuar)
    f.location.z = -0.01; bpy.ops.object.transform_apply(location=True)
    parts = [f] + plinto()
    # fragmentos: ponta do capuz, mão quebrada, lascas
    pts = pts_r
    mao_q = mao(pts); mao_q.location = (0.62, 0.55, PLINTO_H + 0.075); mao_q.rotation_euler = (1.2, 0.3, 0.9); mao_q.scale = (S, S, S)
    parts.append(mao_q)
    ponta = pedaco("ponta", (-0.30, 0.52, PLINTO_H + 0.10), 0.14, (0.8, 1.9, 0.8), (0.1, 0.0, 0.6)); parts.append(ponta)
    parts += [pedaco("l1", (0.55, 0.2, PLINTO_H + 0.03), 0.07, (1.4, 1, 0.7), (0, 0, 1)),
              pedaco("l2", (-0.44, -0.3, PLINTO_H + 0.03), 0.06, (1.2, 1, 0.6), (0, 0, 2))]
    # entulho no chão
    for i in range(7):
        a = random.uniform(0, math.tau); r = random.uniform(0.78, 1.05)
        s = random.uniform(0.07, 0.17)
        parts.append(pedaco(f"e{i}", (math.cos(a) * r, math.sin(a) * r, s * 0.25), s, (random.uniform(0.9, 1.5), random.uniform(0.9, 1.4), random.uniform(0.5, 0.8)),
                            (random.random(), random.random(), random.random() * 6), mat=0))
    return parts

def musgo(o):
    """Musgo nas faces voltadas para cima e na base, por ruído."""
    me = o.data; mw = o.matrix_world
    for p in me.polygons:
        if p.material_index != 0 or p.area > 0.004: continue
        c = mw @ p.center
        up = (mw.to_3x3() @ p.normal).z
        v = fbm(c + Vector((0.37, 0.71, 0.13)), 6.3, 3)
        thr = 0.18 - 0.5 * max(0.0, 0.9 - c.z) + (0.0 if c.z < 0.9 else 0.12)
        if up > 0.45 and v > thr + 0.1: p.material_index = IDX["musgo"]
        elif c.z < 0.3 and v > 0.2: p.material_index = IDX["musgo"]

def exportar(parts):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
    o = bpy.context.object; o.name = "SM_Cripta_Estatua"
    for p in o.data.polygons: p.use_smooth = True
    musgo(o)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SM_Cripta_Estatua.glb"), use_selection=True, export_format='GLB', export_yup=True)
    print("exportado SM_Cripta_Estatua", len(o.data.polygons), "faces, altura", round(o.dimensions.z, 2), "m")
    return o

def render(o, ang, nome, samples=24, res=(640, 800), alvo=None, d=6.5):
    sc = bpy.context.scene
    for ob in [x for x in sc.objects if x.type in ('CAMERA', 'LIGHT')]: bpy.data.objects.remove(ob)
    sc.render.engine = 'CYCLES'; sc.cycles.samples = samples; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.03, 0.045, 1); sc.world = w
    alvo = alvo or Vector((0, 0, 1.55));
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); cam.data.lens = 60
    cam.location = alvo + Vector((math.sin(ang) * d, -math.cos(ang) * d, 0.6))
    cam.rotation_euler = (alvo - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    rot = lambda v: Vector((v.x * math.cos(ang - math.pi) - v.y * math.sin(ang - math.pi), v.x * math.sin(ang - math.pi) + v.y * math.cos(ang - math.pi), v.z))
    # luzes definidas para a câmera em +Y e giradas junto com ela
    for loc, e, col in (((-3, 4, 5), 700, (1, 0.9, 0.8)), ((4, 3, 2), 300, (0.6, 0.7, 1.0)), ((0, -3, 3), 250, (0.7, 0.8, 1.0)), ((0.2, 1.0, 1.0), 120, (1.0, 0.55, 0.2))):
        L = bpy.data.objects.new("l", bpy.data.lights.new("l", 'POINT')); L.data.energy = e; L.data.color = col; L.location = rot(Vector(loc)); sc.collection.objects.link(L)
    sc.render.filepath = os.path.join(PREV, nome + ".png"); bpy.ops.render.render(write_still=True)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    o = exportar(montar())
    if PREV:
        os.makedirs(PREV, exist_ok=True)
        render(o, 3.45, "estatua_frente")
        render(o, 0.35, "estatua_tras")
        render(o, 3.14, "estatua_close_capuz", res=(640, 640), alvo=Vector((0, 0, 2.55)), d=2.8)
