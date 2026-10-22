"""Módulo 3D da Cripta: duas colunas de pedra gótica ligadas por correntes em catenária.
Referência: referencias-cripta/objetos.png (canto superior direito).
blender -b --factory-startup -P coluna_corrente.py -- <pasta_saida> [pasta_previas]
Medidas em metros; pivô no centro entre as colunas, na base; frente voltada para +Y do Blender (-Z do Godot).
O .glb sai com materiais de cor sólida (M_Pedra e M_PedraEscura recebem a textura triplanar no Godot);
a prévia usa materiais procedurais (ruído, musgo, ferrugem) só para avaliar a forma."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None
random.seed(11)

V = 3.2            # distância entre os eixos das colunas
H_COL = 2.7        # altura até a base da pirâmide
objs = []

def mat(name, color, metal=0.0, rough=0.85):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    return m

bpy.ops.wm.read_factory_settings(use_empty=True)
M_PEDRA = mat("M_Pedra", (0.30, 0.28, 0.26))
M_ESCURA = mat("M_PedraEscura", (0.12, 0.115, 0.13))
M_MUSGO = mat("M_Musgo", (0.12, 0.16, 0.05), rough=1.0)
M_FERRO = mat("M_Ferro", (0.16, 0.075, 0.045), metal=0.6, rough=0.55)   # corrente enferrujada
M_FERRO_ESC = mat("M_FerroEscuro", (0.06, 0.05, 0.05), metal=0.7, rough=0.5)  # argolas de prender

def add(o, m):
    o.data.materials.append(m); objs.append(o); return o

def bevel(o, off, seg=2):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=off, segments=seg, affect='EDGES')
    bm.to_mesh(o.data); bm.free()

def box(loc, size, m, rot=(0, 0, 0), bev=0.025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size; bpy.ops.object.transform_apply(scale=True)
    if bev: bevel(o, bev)
    return add(o, m)

def rough_stone(o, amp=0.012, seed=0):
    """Desloca vértices com ruído para quebrar as arestas retas (precisa de malha subdividida)."""
    rnd = random.Random(seed)
    for v in o.data.vertices:
        v.co += Vector((rnd.uniform(-amp, amp), rnd.uniform(-amp, amp), rnd.uniform(-amp, amp)))

def block(loc, size, m, rot=(0, 0, 0), bev=0.03, seed=0, amp=0.006):
    """Bloco de pedra: cubo subdividido, chanfrado e com vértices tremidos."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size; bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True)
    bm.to_mesh(o.data); bm.free()
    bevel(o, bev)
    rough_stone(o, min(amp, min(size) * 0.04), seed)
    return add(o, m)

def pyramid(loc, w, h, m, rot_z=0.0):
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=w * 0.7071, radius2=0.0, depth=h, location=loc,
                                    rotation=(0, 0, math.pi / 4 + rot_z))
    return add(bpy.context.object, m)

def sphere(loc, r, scale, m, seg=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(6, seg // 2), radius=r, location=loc)
    o = bpy.context.object; o.scale = scale; bpy.ops.object.transform_apply(scale=True)
    return add(o, m)

def moss(x, y, z, sx, sy, sz=0.07):
    o = sphere((x, y, z), 0.5, (sx * 0.6, sy * 0.6, sz * 0.7), M_MUSGO, 8)
    rough_stone(o, 0.015, int(x * 100 + y * 10))

# ---------------------------------------------------------------- coluna
def coluna(x, lado, desgaste):
    """Soco, base em degraus, fuste com nicho gótico na frente, capitel e pirâmide. `lado` = -1 esquerda, +1 direita."""
    s = int(x * 10) + 3
    block((x, 0, 0.14), (0.95, 0.95, 0.28), M_PEDRA, seed=s, amp=0.01)            # soco
    block((x, 0, 0.42), (0.78, 0.78, 0.30), M_ESCURA, seed=s + 1)                  # degrau escuro
    block((x, 0, 0.66), (0.70, 0.70, 0.20), M_PEDRA, seed=s + 2)                   # bloco de transição
    # fuste em três fiadas de pedra com juntas visíveis
    for i, (z0, h) in enumerate(((0.76, 0.72), (1.48, 0.62), (2.10, 0.60))):
        block((x, 0, z0 + h / 2), (0.56 - 0.01 * i, 0.56 - 0.01 * i, h - 0.02), M_PEDRA, seed=s + 10 + i, amp=0.005)
    # nicho gótico na frente (+Y): fundo escuro, mísulas laterais e arco apontado
    fy = 0.275
    box((x, fy, 1.55), (0.26, 0.05, 0.95), M_ESCURA, bev=0.008)
    for sx in (-1, 1):
        box((x + sx * 0.16, fy + 0.012, 1.55), (0.045, 0.06, 0.95), M_PEDRA, bev=0.008)
    for sx in (-1, 1):                                                              # arco em duas águas
        box((x + sx * 0.075, fy + 0.012, 2.10), (0.22, 0.06, 0.05), M_PEDRA, rot=(0, sx * 0.62, 0), bev=0.006)
    box((x, fy + 0.012, 1.065), (0.34, 0.07, 0.05), M_PEDRA, bev=0.008)            # peitoril
    # capitel: duas lajes escalonadas, a de cima mais larga
    block((x, 0, 2.78), (0.74, 0.74, 0.14), M_ESCURA, seed=s + 20)
    block((x, 0, 2.93), (0.84, 0.84, 0.18), M_PEDRA, seed=s + 21, amp=0.008)
    block((x, 0, 3.07), (0.62, 0.62, 0.10), M_ESCURA, seed=s + 22)
    pyramid((x, 0, 3.12 + 0.2), 0.50, 0.40, M_PEDRA, rot_z=0.0)                     # pináculo
    # cantos quebrados e lascas caídas ao pé
    for _ in range(4 + desgaste):
        a = random.uniform(0, 6.28); r = random.uniform(0.62, 0.9); sz = random.uniform(0.07, 0.17)
        block((x + math.cos(a) * r, math.sin(a) * r, sz * 0.5), (sz * 1.4, sz * 1.1, sz), M_ESCURA if random.random() > 0.4 else M_PEDRA,
              rot=(0, 0, a), bev=0.012, seed=int(a * 100), amp=0.008)
    # musgo: soco, degrau e topo do capitel
    moss(x + lado * 0.1, 0.42, 0.30, 0.5, 0.3); moss(x - lado * 0.2, 0.40, 0.58, 0.35, 0.25)
    moss(x, -0.1, 3.03, 0.6, 0.5, 0.05); moss(x + lado * 0.3, 0.1, 0.50, 0.3, 0.5)
    moss(x - lado * 0.28, 0.0, 1.48, 0.05, 0.25, 0.5)
    # mais musgo nas bordas e saliências (a referência é bem coberta)
    rnd = random.Random(s)
    for z, r in ((0.29, 0.5), (0.57, 0.38), (0.77, 0.30), (1.48, 0.29), (2.10, 0.29), (2.86, 0.40), (3.02, 0.35)):
        for _ in range(3):
            a = rnd.uniform(0, 6.28)
            moss(x + math.cos(a) * r, math.sin(a) * r, z, rnd.uniform(0.3, 0.7), rnd.uniform(0.3, 0.7), rnd.uniform(0.08, 0.16))
    for z in (1.1, 1.9, 2.5):                                                       # mantos verticais na frente do fuste
        moss(x + rnd.uniform(-0.15, 0.15), 0.29, z, rnd.uniform(0.15, 0.3), 0.08, rnd.uniform(0.5, 0.9))
    # argolas de prender: duas por coluna, voltadas para o lado de dentro
    for z in (2.35, 1.35):
        ax = x - lado * 0.30
        bpy.ops.mesh.primitive_torus_add(major_radius=0.075, minor_radius=0.022, location=(ax, 0, z), rotation=(0, math.pi / 2, 0),
                                         major_segments=14, minor_segments=6)
        add(bpy.context.object, M_FERRO_ESC)
        block((x - lado * 0.265, 0, z), (0.06, 0.10, 0.10), M_FERRO_ESC, bev=0.01, amp=0.002)   # olhal chumbado

# ---------------------------------------------------------------- corrente
def elo(loc, tang, giro, esc=1.0):
    """Um elo: toro achatado em forma de estádio (alongado), orientado ao longo da tangente."""
    L = 0.125 * esc; W = 0.075 * esc; r = 0.030 * esc
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=r / W, major_segments=16, minor_segments=8)
    o = bpy.context.object
    o.scale = Vector((L / W, 1.0, 1.0)) * W
    bpy.ops.object.transform_apply(scale=True)
    # o toro nasce deitado em XY, eixo longo em X; gira em torno do eixo longo (giro) e alinha X com a tangente
    rot = tang.to_track_quat('X', 'Z')
    from mathutils import Matrix
    mw = Matrix.Translation(loc) @ rot.to_matrix().to_4x4() @ Matrix.Rotation(giro, 4, 'X')
    o.matrix_world = mw
    return add(o, M_FERRO)

def corrente(p0, p1, queda, n_elos=None, y=0.0):
    """Catenária aproximada por parábola entre p0 e p1 (x, z) com flecha `queda`; elos alternados em 0° e 90°."""
    comp = ((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2) ** 0.5 + 0.9 * queda
    n = n_elos or int(comp / 0.135)
    pts = []
    for i in range(n + 1):
        t = i / n
        px = p0[0] + (p1[0] - p0[0]) * t
        pz = p0[1] + (p1[1] - p0[1]) * t - queda * 4 * t * (1 - t)
        pts.append(Vector((px, y, pz)))
    for i in range(n):
        a, b = pts[i], pts[i + 1]
        mid = (a + b) / 2; tang = (b - a).normalized()
        elo(mid, tang, (math.pi / 2) if i % 2 else 0.0, esc=1.0 + random.uniform(-0.03, 0.03))

def montar():
    esq, dir_ = -V / 2, V / 2
    coluna(esq, -1, 2); coluna(dir_, 1, 3)
    # duas correntes: a de cima mais esticada, a de baixo mais frouxa, como na referência
    off = 0.30
    corrente((esq + off, 2.35), (dir_ - off, 2.35), 0.55, y=0.10)
    corrente((esq + off, 1.35), (dir_ - off, 1.35), 0.38, y=-0.06)
    # chão: musgo e poeira no vão entre as colunas

# ---------------------------------------------------------------- exportação e prévia
def exportar():
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.shade_auto_smooth(angle=0.6)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SM_Cripta_ColunaCorrente.glb"), use_selection=True,
                              export_format='GLB', export_yup=True)
    print("exportado SM_Cripta_ColunaCorrente", len(o.data.polygons), "faces", tuple(round(d, 2) for d in o.dimensions))
    return o

def procedural():
    """Troca as cores sólidas por materiais procedurais só para a prévia (o glb já foi exportado)."""
    def base(name, c1, c2, scale, bump, rough, metal=0.0):
        m = bpy.data.materials[name]; nt = m.node_tree; nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        tc = nt.nodes.new("ShaderNodeTexCoord"); no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = scale
        no.inputs["Detail"].default_value = 10; no2 = nt.nodes.new("ShaderNodeTexVoronoi"); no2.inputs["Scale"].default_value = scale * 0.6
        cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*c1, 1); cr.color_ramp.elements[1].color = (*c2, 1)
        mix = nt.nodes.new("ShaderNodeMath"); mix.operation = 'MULTIPLY_ADD'; mix.inputs[1].default_value = 0.35; mix.inputs[2].default_value = 0.0
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = bump
        nt.links.new(tc.outputs["Object"], no.inputs["Vector"]); nt.links.new(tc.outputs["Object"], no2.inputs["Vector"])
        no2.feature = "DISTANCE_TO_EDGE"; nt.links.new(no2.outputs["Distance"], mix.inputs[0]); nt.links.new(no.outputs["Fac"], cr.inputs["Fac"])
        nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(no2.outputs["Distance"], bm.inputs["Height"]); nt.links.new(bm.outputs["Normal"], b.inputs["Normal"])
        b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
        nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    base("M_Pedra", (0.12, 0.11, 0.10), (0.45, 0.42, 0.38), 9, 0.6, 0.9)
    base("M_PedraEscura", (0.08, 0.075, 0.09), (0.22, 0.21, 0.23), 14, 0.4, 0.9)
    base("M_Musgo", (0.03, 0.06, 0.012), (0.13, 0.19, 0.045), 30, 0.8, 1.0)
    base("M_Ferro", (0.08, 0.035, 0.02), (0.30, 0.13, 0.06), 40, 0.5, 0.55, 0.5)
    base("M_FerroEscuro", (0.03, 0.03, 0.03), (0.10, 0.09, 0.09), 40, 0.3, 0.5, 0.7)

def render(o, nome="coluna_corrente", amostras=24, res=(960, 720), vistas=None):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = amostras; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.04, 0.05, 0.08, 1); sc.world = w
    sun = bpy.data.objects.new("sol", bpy.data.lights.new("sol", 'SUN')); sun.data.energy = 3.0
    sun.rotation_euler = (0.9, 0.15, 0.7); bpy.context.collection.objects.link(sun)
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", 'AREA')); fill.data.energy = 200; fill.data.size = 4
    fill.location = (-4, -3, 3); fill.rotation_euler = (1.1, 0, -0.9); bpy.context.collection.objects.link(fill)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.collection.objects.link(cam); sc.camera = cam
    alvo = Vector((0, 0, 1.4))
    vistas = vistas or {"3q": (4.6, 5.2, 3.4), "frente": (0, 7.5, 1.8), "detalhe": (-0.4, 2.6, 1.7), "costas": (-3.5, -5.0, 2.6)}
    for k, p in vistas.items():
        cam.location = p
        cam.rotation_euler = (alvo - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = 70 if k == "detalhe" else 50
        sc.render.filepath = os.path.join(PREV, f"{nome}_{k}.png"); bpy.ops.render.render(write_still=True)

montar()
o = exportar()
if PREV:
    os.makedirs(PREV, exist_ok=True)
    procedural()
    render(o)
