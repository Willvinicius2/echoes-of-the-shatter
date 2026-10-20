"""Modulo 3D: braseiro de ferro com espigoes (referencia: referencias-cripta/objeto.png).
blender -b --factory-startup -P braseiro.py -- <saida.fbx> [preview.png]
Escala em metros, pivo no centro da base, +Z para cima no Blender (FBX exporta Y-up para a Unity). Altura do corpo ~1,45 m; a chama fica por conta do FirePool."""
import bpy, bmesh, math, sys
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "braseiro.fbx"
PREVIEW = argv[1] if len(argv) > 1 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
objs = []

def mat(name, color, metal=0.7, rough=0.45, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = 2.5
    return m

IRON = mat("M_Braseiro_Ferro", (0.075, 0.07, 0.08))
TRIM = mat("M_Braseiro_Cinta", (0.16, 0.12, 0.09), 0.6, 0.4)   # cintas e rebites: ferro mais quente
EMBER = mat("M_Braseiro_Brasa", (0.9, 0.25, 0.05), 0.0, 0.8, emit=(1.0, 0.35, 0.05))

def add(obj, material):
    obj.data.materials.append(material); objs.append(obj); return obj

def box(loc, size, rot=(0, 0, 0), material=IRON, bevel=0.012):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=1, affect='EDGES')
        bm.to_mesh(o.data); bm.free()
    return add(o, material)

def cone(loc, r, h, sides=4, rot=(0, 0, 0), material=IRON, r2=0.0):
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=r, radius2=r2, depth=h, location=(loc[0], loc[1], loc[2] + h / 2), rotation=rot)
    return add(bpy.context.object, material)

def cyl(loc, r, h, sides=16, material=IRON):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=r, depth=h, location=loc)
    return add(bpy.context.object, material)

# ---- pernas: 4 colunas quadradas com base escalonada e capitel
LEG = 0.42
for sx in (-1, 1):
    for sy in (-1, 1):
        x, y = sx * LEG, sy * LEG
        box((x, y, 0.07), (0.40, 0.40, 0.14), material=IRON)               # sapata
        box((x, y, 0.24), (0.30, 0.30, 0.20), material=TRIM)              # cinta baixa
        box((x, y, 0.62), (0.22, 0.22, 0.56), material=IRON)              # fuste
        box((x, y, 0.95), (0.30, 0.30, 0.10), material=TRIM)              # capitel
        cone((x, y, 1.00), 0.10, 0.20, rot=(0, 0, math.pi / 4), material=IRON)  # ponta de canto
# ---- travessas em X e diamante central
for ang in (math.pi / 4, -math.pi / 4):
    box((0, 0, 0.38), (1.30, 0.07, 0.07), rot=(0, 0, ang), material=IRON)
box((0, 0, 0.38), (0.20, 0.20, 0.20), rot=(math.pi / 4, 0, math.pi / 4), material=TRIM)
cone((0, 0, 0.16), 0.11, 0.22, rot=(math.pi, 0, math.pi / 4), material=IRON)

# ---- bacia (hemisferio) com cintas
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=10, radius=0.68, location=(0, 0, 1.12))
bowl = bpy.context.object
bm = bmesh.new(); bm.from_mesh(bowl.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 0.02], context='VERTS')
bm.to_mesh(bowl.data); bm.free()
bowl.scale = (1, 1, 0.55); bpy.ops.object.transform_apply(scale=True)
for p in bowl.data.polygons: p.use_smooth = False
add(bowl, IRON)
for a in range(4):
    box((0, 0, 0.97), (0.05, 1.3, 0.05), rot=(0, 0, a * math.pi / 4), material=TRIM)   # cintas meridianas (escondidas sob a bacia)

# ---- aro superior: dois aneis e ripas verticais (gaiola)
Z0, Z1 = 1.12, 1.40
for z in (Z0 + 0.04, Z1 - 0.04):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.68, minor_radius=0.04, major_segments=24, minor_segments=6, location=(0, 0, z))
    add(bpy.context.object, TRIM)
N = 14
for i in range(N):
    a = i * 2 * math.pi / N
    x, y = 0.68 * math.cos(a), 0.68 * math.sin(a)
    box((x, y, (Z0 + Z1) / 2), (0.05, 0.05, Z1 - Z0), rot=(0, 0, a), material=IRON)
    if i % 2 == 0:
        box((x, y, (Z0 + Z1) / 2 + 0.02), (0.07, 0.07, 0.07), rot=(math.pi / 4, 0, a), material=TRIM)  # rebite em losango
# ---- espigoes no aro: 8 medios + 4 altos nos cantos
for i in range(8):
    a = (i + 0.5) * 2 * math.pi / 8
    cone((0.70 * math.cos(a), 0.70 * math.sin(a), Z1 - 0.02), 0.075, 0.20 + 0.04 * ((i * 7) % 3), sides=4, rot=(0, 0, a))
for sx in (-1, 1):
    for sy in (-1, 1):
        a = math.atan2(sy, sx)
        x, y = 0.74 * math.cos(a), 0.74 * math.sin(a)
        box((x, y, 1.20), (0.14, 0.14, 0.40), rot=(0, 0, a), material=IRON)
        cone((x, y, 1.40), 0.11, 0.30, sides=4, rot=(0, 0, a), material=IRON)
        for sgn in (-1, 1):  # espinhos laterais
            cone((x + sgn * 0.11 * -math.sin(a), y + sgn * 0.11 * math.cos(a), 1.26), 0.05, 0.16, sides=4, rot=(sgn * math.pi / 2 * 0.9, 0, a))

# ---- brasas dentro
import random
random.seed(5)
for i in range(7):
    r = 0.32 * math.sqrt(random.random()); a = random.random() * 2 * math.pi
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.13 + random.random() * 0.06, location=(r * math.cos(a), r * math.sin(a), 1.20 + random.random() * 0.08))
    o = bpy.context.object; o.scale = (1, 1, 0.7); add(o, EMBER)

# ---- juntar, triangular, exportar
for o in bpy.data.objects: o.select_set(o in objs)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.join()
body = bpy.context.object; body.name = "SM_Cripta_Braseiro_Novo"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.shade_flat()
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', add_leaf_bones=False)
print("tris", sum(len(p.vertices) - 2 for p in body.data.polygons), "->", OUT)

if PREVIEW:
    bpy.ops.object.light_add(type='SUN', location=(3, -3, 5)); bpy.context.object.data.energy = 3.5
    bpy.context.object.rotation_euler = (math.radians(50), 0, math.radians(35))
    bpy.ops.object.camera_add(location=(2.6, -2.6, 2.2)); cam = bpy.context.object
    d = Vector((0, 0, 0.8)) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam
    bpy.context.scene.world = bpy.data.worlds.new("w"); bpy.context.scene.world.color = (0.05, 0.05, 0.07)
    bpy.context.scene.render.resolution_x = 900; bpy.context.scene.render.resolution_y = 900
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
