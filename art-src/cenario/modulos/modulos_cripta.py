"""Módulos 3D da Cripta para o Godot (referências: referencias-cripta/pilar.png e objetos.png).
Gera um .glb por módulo, em metros, pivô no centro da base, frente do módulo voltada para +Y do Blender (-Z do Godot).
blender -b --factory-startup -P modulos_cripta.py -- <pasta_saida> [pasta_previas]
Materiais: M_Pedra / M_PedraEscura recebem a textura triplanar de pedra no Godot (construtor da cena); o resto é cor sólida."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None
random.seed(7)

def mat(name, color, metal=0.0, rough=0.85, emit=None, strength=3.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    return m

def make_mats():
    global M_ESTATUA, M_PEDRA, M_ESCURA, M_MUSGO, M_TECIDO, M_OURO, M_CERA, M_CHAMA, M_FERRO
    M_PEDRA = mat("M_Pedra", (0.42, 0.42, 0.46))
    M_ESCURA = mat("M_PedraEscura", (0.16, 0.16, 0.19))
    M_MUSGO = mat("M_Musgo", (0.08, 0.12, 0.05), rough=1.0)
    M_TECIDO = mat("M_Tecido", (0.40, 0.035, 0.05), rough=0.95)
    M_OURO = mat("M_Ouro", (0.72, 0.52, 0.16), metal=0.9, rough=0.4)
    M_CERA = mat("M_Cera", (0.88, 0.82, 0.66), rough=0.7)
    M_CHAMA = mat("M_Chama", (1.0, 0.6, 0.15), rough=0.5, emit=(1.0, 0.55, 0.12), strength=6.0)
    M_ESTATUA = mat("M_Estatua", (0.22, 0.21, 0.20), rough=0.9)
    M_FERRO = mat("M_Ferro", (0.075, 0.07, 0.08), metal=0.7, rough=0.5)

objs = []

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True); objs.clear(); make_mats()

def add(o, m):
    m = m or M_PEDRA
    o.data.materials.append(m); objs.append(o); return o

def bevel(o, off=0.02):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=off, segments=1, affect='EDGES')
    bm.to_mesh(o.data); bm.free()

def box(loc, size, m=None, rot=(0, 0, 0), bev=0.03):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size; bpy.ops.object.transform_apply(scale=True)
    if bev: bevel(o, bev)
    return add(o, m)

def cyl(loc, r, h, m=None, sides=16, r2=None, rot=(0, 0, 0)):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=r, depth=h, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    return add(bpy.context.object, m)

def sphere(loc, r, scale=(1, 1, 1), m=None, seg=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(6, seg // 2), radius=r, location=loc)
    o = bpy.context.object; o.scale = scale; bpy.ops.object.transform_apply(scale=True)
    return add(o, m)

def estatua(x, y, z, esc=1.0):
    """Figura encapuzada: manto largo em camadas, ombros, braços cruzados à frente, capuz pontudo com rosto na sombra."""
    e = esc
    cyl((x, y, z + 0.30 * e), 0.50 * e, 0.60 * e, M_ESTATUA, 14, r2=0.42 * e)     # barra do manto
    cyl((x, y, z + 0.85 * e), 0.42 * e, 0.60 * e, M_ESTATUA, 14, r2=0.33 * e)     # tronco
    cyl((x, y, z + 1.30 * e), 0.33 * e, 0.35 * e, M_ESTATUA, 12, r2=0.30 * e)     # peito
    sphere((x, y, z + 1.45 * e), 0.30 * e, (1.2, 0.75, 0.45), M_ESTATUA, 14)      # ombros
    for sx in (-1, 1):                                                            # braços caindo e dobrando para a frente
        cyl((x + sx * 0.30 * e, y + 0.04 * e, z + 1.15 * e), 0.075 * e, 0.55 * e, M_ESTATUA, 8, rot=(0.25, sx * 0.12, 0))
        cyl((x + sx * 0.14 * e, y + 0.30 * e, z + 0.95 * e), 0.07 * e, 0.34 * e, M_ESTATUA, 8, rot=(1.25, 0, sx * 0.6))
    sphere((x, y + 0.34 * e, z + 0.92 * e), 0.085 * e, (1.4, 0.8, 0.8), M_ESTATUA, 8)  # mãos juntas
    cyl((x, y, z + 1.52 * e), 0.17 * e, 0.12 * e, M_ESTATUA, 10)                     # gola do capuz
    sphere((x, y - 0.02 * e, z + 1.70 * e), 0.22 * e, (1, 1.05, 1.1), M_ESTATUA, 14)  # capuz
    cyl((x, y - 0.10 * e, z + 1.92 * e), 0.15 * e, 0.28 * e, M_ESTATUA, 10, r2=0.0)    # ponta do capuz
    sphere((x, y + 0.12 * e, z + 1.68 * e), 0.13 * e, (0.9, 0.55, 1.1), M_ESCURA, 10)  # rosto na sombra
    box((x, y, z + 0.06 * e), (0.9 * e, 0.9 * e, 0.12 * e), M_ESTATUA, bev=0.015)

def musgo(x, y, z, sx, sy):
    sphere((x, y, z), 0.5, (sx, sy, 0.12), M_MUSGO, 8)

def exportar(nome):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.object
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, nome + ".glb"), use_selection=True, export_format='GLB', export_yup=True)
    print("exportado", nome, len(o.data.polygons), "faces")
    if PREV:
        cam = bpy.data.cameras.new("c"); co = bpy.data.objects.new("c", cam); bpy.context.collection.objects.link(co)
        d = max(o.dimensions) * 2.2; co.location = (d * 0.7, -d * 0.9, d * 0.55 + o.dimensions.z * 0.25)
        co.rotation_euler = (Vector((0, 0, o.dimensions.z * 0.45)) - co.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.scene.camera = co
        sun = bpy.data.objects.new("s", bpy.data.lights.new("s", 'SUN')); sun.data.energy = 3; sun.rotation_euler = (0.9, 0.2, 0.6)
        bpy.context.collection.objects.link(sun)
        w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.06, 0.09, 1)
        bpy.context.scene.world = w
        sc = bpy.context.scene; sc.render.resolution_x = 700; sc.render.resolution_y = 700
        sc.render.filepath = os.path.join(PREV, nome + ".png"); bpy.ops.render.render(write_still=True)

# ---------------------------------------------------------------- Pilar com estátua em nicho
def pilar():
    reset()
    box((0, 0, 0.2), (3.0, 3.0, 0.4), M_PEDRA)                 # soco largo
    box((0, 0, 0.62), (2.6, 2.6, 0.44), M_PEDRA)               # degrau
    box((0, 0, 1.0), (2.3, 2.3, 0.32), M_ESCURA, bev=0.02)     # moldura escura
    box((0, 0, 3.55), (1.9, 1.9, 4.8), M_PEDRA)                # fuste
    # nicho na frente (+Y): fundo escuro, moldura e arco
    box((0, 0.93, 2.45), (1.1, 0.1, 2.3), M_ESCURA, bev=0.01)
    box((-0.58, 0.95, 2.3), (0.14, 0.12, 2.1), M_PEDRA, bev=0.01); box((0.58, 0.95, 2.3), (0.14, 0.12, 2.1), M_PEDRA, bev=0.01)
    box((0, 0.95, 3.4), (1.3, 0.12, 0.16), M_PEDRA, bev=0.01)
    sphere((0, 0.94, 3.25), 0.5, (1, 0.12, 0.55), M_ESCURA, 12)  # arco
    estatua(0, 0.72, 1.15, 1.08)
    # vigas de faixa horizontais e capitel
    box((0, 0, 4.9), (2.1, 2.1, 0.18), M_ESCURA, bev=0.02)
    box((0, 0, 5.5), (2.35, 2.35, 0.45), M_PEDRA)
    box((0, 0, 5.9), (2.0, 2.0, 0.3), M_ESCURA, bev=0.02)
    # lascas e musgo no soco
    for _ in range(5):
        a = random.uniform(0, 6.28)
        box((math.cos(a) * 1.3, math.sin(a) * 1.3, 0.12 + random.random() * 0.1), (0.2 + random.random() * 0.25, 0.2 + random.random() * 0.2, 0.18), M_ESCURA, rot=(0, 0, a), bev=0.02)
    musgo(-0.9, 1.45, 0.44, 1.0, 0.7); musgo(0.8, 1.4, 0.82, 0.6, 0.5); musgo(0.95, 0.4, 3.0, 0.2, 1.0)
    exportar("SM_Cripta_Pilar")

def estandarte():
    reset()
    cyl((0, 0, 0.1), 0.2, 0.2, M_PEDRA, 10)
    cyl((0, 0, 1.6), 0.05, 3.0, M_FERRO, 8)                                  # mastro
    box((0, 0, 3.05), (0.9, 0.07, 0.07), M_FERRO, bev=0)                      # travessa
    sphere((-0.47, 0, 3.05), 0.07, m=M_OURO, seg=8); sphere((0.47, 0, 3.05), 0.07, m=M_OURO, seg=8)
    # pano ondulado: faixa com pontas rasgadas
    bm = bmesh.new()
    cols, rows = 5, 14
    verts = []
    for j in range(rows + 1):
        t = j / rows
        for i in range(cols + 1):
            u = i / cols - 0.5
            drop = 2.35 - (0.12 if abs(u) < 0.2 else 0) * (1 if True else 0)
            x = u * 0.8; z = 3.0 - t * 2.25 - (0.18 * abs(u) if t > 0.85 else 0)
            y = math.sin(t * 5 + u * 3) * 0.04
            verts.append(bm.verts.new((x, y, z)))
    for j in range(rows):
        for i in range(cols):
            bm.faces.new((verts[j * (cols + 1) + i], verts[j * (cols + 1) + i + 1], verts[(j + 1) * (cols + 1) + i + 1], verts[(j + 1) * (cols + 1) + i]))
    me = bpy.data.meshes.new("pano"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("pano", me); bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    mod = o.modifiers.new("s", 'SOLIDIFY'); mod.thickness = 0.02
    bpy.ops.object.modifier_apply(modifier="s")
    add(o, M_TECIDO)
    box((0, 0.04, 2.1), (0.1, 0.02, 1.2), M_OURO, bev=0)                       # faixa dourada central
    sphere((0, 0.05, 1.9), 0.16, (1, 0.15, 1), M_OURO, 8)                      # brasão
    exportar("SM_Cripta_Estandarte")

def velas():
    reset()
    box((0, 0, 0.03), (0.9, 0.9, 0.06), M_ESCURA, bev=0.01)                     # lajota de apoio
    pos = [(-0.2, -0.1, 0.30), (0.15, 0.05, 0.22), (0.05, -0.25, 0.14), (-0.3, 0.2, 0.18), (0.28, -0.2, 0.34), (-0.05, 0.28, 0.10), (0.3, 0.25, 0.16)]
    for x, y, h in pos:
        cyl((x, y, 0.06 + h / 2), 0.035, h, M_CERA, 8)
        sphere((x, y, 0.06 + h + 0.025), 0.022, (1, 1, 1.9), M_CHAMA, 6)
        sphere((x, y, 0.07), 0.05, (1, 1, 0.4), M_CERA, 6)                      # poça de cera
    exportar("SM_Cripta_Velas")

def corrente_dupla():
    """Duas colunas de ferro e pedra a 6 m uma da outra com corrente em catenária."""
    reset()
    V = 6.0
    for sx in (-1, 1):
        x = sx * V / 2
        box((x, 0, 0.12), (0.7, 0.7, 0.24), M_PEDRA); box((x, 0, 0.5), (0.5, 0.5, 0.52), M_ESCURA)
        box((x, 0, 1.15), (0.34, 0.34, 1.3), M_PEDRA); box((x, 0, 1.9), (0.5, 0.5, 0.2), M_ESCURA)
        sphere((x, 0, 2.1), 0.17, m=M_FERRO, seg=10)
        cyl((x - sx * 0.0, 0, 1.55), 0.035, 0.0001, M_FERRO, 6)  # (pino) mantido para pivô
        # argola
        bpy.ops.mesh.primitive_torus_add(major_radius=0.08, minor_radius=0.02, location=(x - sx * 0.2, 0, 1.6), rotation=(0, math.pi / 2, 0)); add(bpy.context.object, M_FERRO)
    n = 26
    for i in range(n):
        t = i / (n - 1); x = (t - 0.5) * (V - 0.4)
        z = 1.6 - 0.55 * (1 - (2 * t - 1) ** 2)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.055, minor_radius=0.014, location=(x, 0, z), rotation=((math.pi / 2) if i % 2 else 0, 0, 0))
        add(bpy.context.object, M_FERRO)
    exportar("SM_Cripta_ColunaCorrente")

def entulho():
    reset()
    for _ in range(9):
        a = random.uniform(0, 6.28); r = random.uniform(0.0, 0.7)
        s = random.uniform(0.18, 0.5)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=s, location=(math.cos(a) * r, math.sin(a) * r, s * 0.45))
        o = bpy.context.object; o.scale = (random.uniform(0.8, 1.4), random.uniform(0.8, 1.4), random.uniform(0.5, 0.9))
        o.rotation_euler = (random.random(), random.random(), random.random()); bpy.ops.object.transform_apply(scale=True, rotation=True)
        add(o, M_PEDRA if random.random() > 0.35 else M_ESCURA)
    musgo(0.2, -0.2, 0.05, 1.2, 0.9)
    exportar("SM_Cripta_Entulho")

def estatua_avulsa():
    reset()
    box((0, 0, 0.2), (1.1, 1.1, 0.4), M_PEDRA); box((0, 0, 0.5), (0.85, 0.85, 0.2), M_ESCURA)
    estatua(0, 0, 0.6, 1.25)
    exportar("SM_Cripta_Estatua")

for fn in (pilar, estandarte, velas, entulho, estatua_avulsa):  # coluna com corrente: coluna_corrente.py
    fn()
