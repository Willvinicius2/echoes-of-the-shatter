"""Módulo 3D: estandarte da Cripta (referência: referencias-cripta/objetos.png, pano vermelho com faixa e brasão dourados).
blender -b --factory-startup -P estandarte.py -- <saida.glb> [pasta_previas]
Metros, pivô no centro da base, frente voltada para +Y do Blender. Poste de ferro com braço de espigões, pano rasgado e corrente.
Materiais: M_Tecido, M_Ouro, M_Ferro, M_PedraEscura (a base recebe a pedra triplanar no Godot)."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "SM_Cripta_Estandarte.glb"
PREV = argv[1] if len(argv) > 1 else None
random.seed(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
objs = []

def mat(name, color, metal=0.0, rough=0.85):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    return m

M_FERRO = mat("M_Ferro", (0.10, 0.08, 0.075), 0.7, 0.5)
M_FERRUGEM = mat("M_Ferrugem", (0.20, 0.10, 0.06), 0.5, 0.65)
M_ESCURA = mat("M_PedraEscura", (0.16, 0.16, 0.19))
M_TECIDO = mat("M_Tecido", (0.34, 0.025, 0.04), rough=0.95)
M_TECIDO2 = mat("M_TecidoEscuro", (0.20, 0.015, 0.03), rough=1.0)
M_OURO = mat("M_Ouro", (0.72, 0.52, 0.16), 0.9, 0.4)

def add(o, m):
    o.data.materials.append(m); objs.append(o); return o

def bevel(o, off):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=off, segments=1, affect='EDGES')
    bm.to_mesh(o.data); bm.free()

def box(loc, size, m, rot=(0, 0, 0), bev=0.01):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size; bpy.ops.object.transform_apply(scale=True)
    if bev: bevel(o, bev)
    return add(o, m)

def cyl(loc, r, h, m, sides=10, r2=None, rot=(0, 0, 0)):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=r, depth=h, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    return add(bpy.context.object, m)

def spike(loc, r, h, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=r, radius2=0, depth=h, location=loc, rotation=rot)
    return add(bpy.context.object, m)

def torus(loc, R, r, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=12, minor_segments=5, location=loc, rotation=rot)
    return add(bpy.context.object, m)

# ---------------------------------------------------------------- base de pedra e poste de ferro
PX = -0.64   # o poste fica ao lado do pano, como na referência (pano pendurado no braço)
box((PX, 0, 0.09), (0.55, 0.55, 0.18), M_ESCURA, bev=0.025)
box((PX, 0, 0.24), (0.38, 0.38, 0.12), M_ESCURA, bev=0.02)
POST_Z = 3.15
box((PX, 0, 1.7), (0.10, 0.10, 3.0), M_FERRO, bev=0.012)                    # fuste quadrado
for z in (0.45, 1.5, 2.5):
    box((PX, 0, z), (0.17, 0.17, 0.07), M_FERRUGEM, bev=0.012)               # cintas
box((PX, 0, 3.12), (0.16, 0.16, 0.10), M_FERRUGEM, bev=0.012)
spike((PX, 0, 3.17), 0.095, 0.38, M_FERRO, rot=(0, 0, math.pi / 4))          # ponta do poste
for s in (-1, 1):
    spike((PX + s * 0.09, 0, 3.12), 0.04, 0.18, M_FERRO, rot=(0, s * math.radians(55), math.pi / 4))
    spike((PX, s * 0.09, 3.12), 0.04, 0.18, M_FERRO, rot=(-s * math.radians(55), 0, math.pi / 4))

# ---------------------------------------------------------------- braço horizontal com espigões nas pontas
ARM_Z = 2.88
AX0, AX1 = PX - 0.06, 0.74          # braço do poste até depois da borda direita do pano
box(((AX0 + AX1) / 2, 0, ARM_Z), (AX1 - AX0, 0.075, 0.075), M_FERRO, bev=0.01)
box((AX1 + 0.02, 0, ARM_Z), (0.10, 0.10, 0.10), M_FERRUGEM, bev=0.01)
spike((AX1 + 0.07, 0, ARM_Z), 0.075, 0.32, M_FERRO, rot=(0, -math.pi / 2, math.pi / 4))
spike((PX - 0.11, 0, ARM_Z), 0.07, 0.24, M_FERRO, rot=(0, math.pi / 2, math.pi / 4))
for k in (-1, 1):                                                          # espinhos ao longo do braço
    for x in (0.52, 0.30):
        spike((x, k * 0.04, ARM_Z + 0.02), 0.028, 0.12, M_FERRO, rot=(-k * math.pi / 2, 0, 0))
# escora diagonal poste -> braço
dx, dz = 0.17, 0.17
L = math.hypot(dx, dz); ang = math.atan2(dz, dx)
box((PX + dx / 2, 0, ARM_Z - dz / 2), (L, 0.045, 0.045), M_FERRO, rot=(0, ang, 0), bev=0.006)
box((PX + 0.02, 0.0, ARM_Z), (0.20, 0.14, 0.20), M_FERRUGEM, bev=0.012)    # junta

# ---------------------------------------------------------------- pano rasgado
W = 0.84; TOP = ARM_Z - 0.06; LEN = 2.25
COLS, ROWS = 8, 30
def cloth_edge(u, t):
    """Comprimento extra da barra: franjas rasgadas, mais longas no centro."""
    return 0

bm = bmesh.new()
rows_v = []
# faixa de ponta: o pano termina em tiras de comprimentos diferentes
tear = [random.uniform(0.0, 0.34) for _ in range(COLS + 1)]
tear[COLS // 2] += 0.18; tear[COLS // 2 + 1] += 0.1
tear[1] += 0.25
for j in range(ROWS + 1):
    t = j / ROWS
    row = []
    for i in range(COLS + 1):
        u = i / COLS - 0.5
        length = LEN - 0.20 * abs(u) * 1.6 + tear[i] * 0.9 - 0.15
        z = TOP - t * length
        x = u * W * (1 - 0.10 * t) + 0.015 * math.sin(t * 9 + i)
        y = 0.045 * math.sin(t * 6.0 + u * 5.0) * (0.3 + t) + 0.02 * math.sin(t * 17 + i * 1.7) * t
        row.append(bm.verts.new((x, y, z)))
    rows_v.append(row)
for j in range(ROWS):
    for i in range(COLS):
        bm.faces.new((rows_v[j][i], rows_v[j][i + 1], rows_v[j + 1][i + 1], rows_v[j + 1][i]))
me = bpy.data.meshes.new("pano"); bm.to_mesh(me); bm.free()
pano = bpy.data.objects.new("pano", me); bpy.context.collection.objects.link(pano)
bpy.context.view_layer.objects.active = pano; pano.select_set(True)
mod = pano.modifiers.new("s", 'SOLIDIFY'); mod.thickness = 0.018
bpy.ops.object.modifier_apply(modifier="s")
add(pano, M_TECIDO)

def Y_AT(u, t):
    """Superfície do pano na frente (para colar ornamentos)."""
    return 0.045 * math.sin(t * 6.0 + u * 5.0) * (0.3 + t) + 0.02 * math.sin(t * 17 + int((u + 0.5) * COLS) * 1.7) * t + 0.012

def strip(u0, u1, t0, t1, m, th=0.006, n=14):
    """Faixa plana acompanhando a ondulação do pano."""
    b = bmesh.new(); vs = []
    for k in range(n + 1):
        t = t0 + (t1 - t0) * k / n
        len_ = LEN - 0.20 * abs((u0 + u1) / 2) * 1.6 - 0.15
        z = TOP - t * len_
        pair = []
        for u in (u0, u1):
            x = u * W * (1 - 0.10 * t)
            pair.append(b.verts.new((x, Y_AT(u, t) + th, z)))
        vs.append(pair)
    for k in range(n):
        b.faces.new((vs[k][0], vs[k][1], vs[k + 1][1], vs[k + 1][0]))
    mm = bpy.data.meshes.new("faixa"); b.to_mesh(mm); b.free()
    o = bpy.data.objects.new("faixa", mm); bpy.context.collection.objects.link(o)
    return add(o, m)

# faixas verticais douradas nas bordas e linhas finas internas
strip(-0.47, -0.42, 0.02, 0.88, M_OURO)
strip(0.42, 0.47, 0.02, 0.88, M_OURO)
strip(-0.395, -0.380, 0.02, 0.88, M_OURO)
strip(0.380, 0.395, 0.02, 0.88, M_OURO)
# barra de ouro no alto, onde o pano prende ao braço
strip(-0.50, 0.50, 0.0, 0.035, M_OURO, th=0.012, n=2)
# trilho de tecido mais escuro no alto (dobra costurada)
strip(-0.50, 0.50, 0.035, 0.085, M_TECIDO2, th=0.009, n=2)

# brasão: flor de lis estilizada em ouro (losango central, pétalas, haste)
Z_C = TOP - 0.40 * (LEN - 0.15)
def ornament(u, t, w, h, m, rot=0.0):
    """Losango achatado sobre o pano (w, h em metros, rot em radianos no plano do pano)."""
    z = TOP - t * (LEN - 0.15)
    y = Y_AT(u, t) + 0.010
    b = bmesh.new()
    c, sn = math.cos(rot), math.sin(rot)
    pts = [(0, h), (w, 0), (0, -h), (-w, 0)]
    vs = [b.verts.new((u * W + px * c - pz * sn, y, z + px * sn + pz * c)) for px, pz in pts]
    b.faces.new(vs)
    mm = bpy.data.meshes.new("orn"); b.to_mesh(mm); b.free()
    o = bpy.data.objects.new("orn", mm); bpy.context.collection.objects.link(o)
    return add(o, m)

ornament(0, 0.40, 0.10, 0.20, M_OURO)                          # losango central
ornament(0, 0.33, 0.05, 0.09, M_OURO)                          # topo
ornament(0, 0.50, 0.05, 0.09, M_OURO)                          # baixo
for s in (-1, 1):
    ornament(s * 0.11, 0.395, 0.055, 0.12, M_OURO, rot=s * 0.5)  # pétalas laterais
    ornament(s * 0.20, 0.44, 0.04, 0.085, M_OURO, rot=s * 0.9)
    ornament(s * 0.065, 0.48, 0.035, 0.07, M_OURO, rot=s * 0.4)
ornament(0, 0.60, 0.018, 0.17, M_OURO)                         # haste
ornament(0, 0.72, 0.045, 0.05, M_OURO)                         # ponta inferior
# detalhe: rasgões escuros (remendos) e manchas
for (u, t, w, h) in ((-0.28, 0.62, 0.05, 0.10), (0.30, 0.70, 0.04, 0.12), (-0.12, 0.80, 0.03, 0.09)):
    ornament(u, t, w, h, M_TECIDO2)

# argolas que seguram o pano no braço
for u in (-0.40, -0.20, 0.0, 0.20, 0.40):
    torus((u * W, 0.0, ARM_Z - 0.01), 0.045, 0.011, M_FERRUGEM, rot=(math.pi / 2, 0, 0))
    box((u * W, 0.02, ARM_Z - 0.065), (0.03, 0.012, 0.09), M_FERRUGEM, bev=0)

# ---------------------------------------------------------------- corrente pendente do braço (lado direito)
def corrente(x0, z0, n, y=0.04):
    for i in range(n):
        z = z0 - i * 0.075
        rot = (math.pi / 2, 0, 0) if i % 2 == 0 else (math.pi / 2, 0, math.pi / 2)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.034, minor_radius=0.009, major_segments=8, minor_segments=4, location=(x0, y, z), rotation=rot)
        add(bpy.context.object, M_FERRUGEM)
corrente(AX1 - 0.05, ARM_Z - 0.05, 11)
corrente(PX + 0.10, ARM_Z - 0.20, 4)

# ---------------------------------------------------------------- juntar e exportar
bpy.ops.object.select_all(action='DESELECT')
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.join()
o = bpy.context.object; o.name = "SM_Cripta_Estandarte"
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format='GLB', export_yup=True)
print("faces", len(o.data.polygons), "dim", tuple(round(d, 2) for d in o.dimensions), "->", OUT)

if PREV:
    os.makedirs(PREV, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.device = 'CPU'
    sc.render.resolution_x = 700; sc.render.resolution_y = 900
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.07, 0.10, 1)
    sc.world = w
    sun = bpy.data.objects.new("s", bpy.data.lights.new("s", 'SUN')); sun.data.energy = 3.5; sun.rotation_euler = (0.9, 0.2, 0.6)
    bpy.context.collection.objects.link(sun)
    for nome, loc in (("frente", (0, -6.5, 1.8)), ("tres_quartos", (4.0, -5.0, 3.0))):
        cam = bpy.data.cameras.new("c"); co = bpy.data.objects.new("c", cam); bpy.context.collection.objects.link(co)
        # a frente do módulo é +Y; a câmera olha de +Y
        co.location = (loc[0], -loc[1], loc[2]); co.rotation_euler = (Vector((0, 0, 1.6)) - co.location).to_track_quat('-Z', 'Y').to_euler()
        sc.camera = co; sc.render.filepath = os.path.join(PREV, f"estandarte_{nome}.png"); bpy.ops.render.render(write_still=True)
