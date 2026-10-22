"""Módulo 3D: entulho da Cripta (referência: referencias-cripta/objetos.png, pilha de blocos cortados com musgo).
python entulho.py <pasta_saida> [pasta_previas]    (módulo bpy) ou  blender -b --factory-startup -P entulho.py -- <saida> [previas]
Escala em metros, pivô no centro da base, +Z para cima no Blender. Montado por partes (entulho_partes/):
blocos (pilha grande), pedras (soltas e lascas), musgo (tufos), texturas (albedo + normal cozidos no .glb)."""
import bpy, bmesh, math, sys, os
from mathutils import Vector
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "entulho_partes"))
import comum, blocos, pedras, musgo, texturas

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None
LIMITE_FACES = 5500

bpy.ops.wm.read_factory_settings(use_empty=True)
M = comum.criar_materiais(); alt = comum.Altura()
grandes = blocos.construir(M, alt)
soltas = pedras.construir(M, alt)
tufos = musgo.construir(M, grandes)

bpy.ops.object.select_all(action='DESELECT')
todos = grandes + soltas + tufos
for o in todos: o.select_set(True)
bpy.context.view_layer.objects.active = todos[0]
bpy.ops.object.join(); o = bpy.context.object
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
n = len(o.data.polygons)
if n > LIMITE_FACES:   # decimação planar mantém as facetas retas e tira o excesso dos relevos
    md = o.modifiers.new("d", 'DECIMATE'); md.decimate_type = 'DISSOLVE'; md.angle_limit = math.radians(6)
    bpy.ops.object.modifier_apply(modifier="d")
zs = [v.co.z for v in o.data.vertices]
for v in o.data.vertices: v.co.z -= min(zs)
cx = sum(v.co.x for v in o.data.vertices) / len(o.data.vertices); cy = sum(v.co.y for v in o.data.vertices) / len(o.data.vertices)
for v in o.data.vertices: v.co.x -= cx; v.co.y -= cy
o.name = "SM_Cripta_Entulho"
# triangula para contar certo e evitar ngons no glb
bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(o.data); bm.free()
for p in o.data.polygons: p.use_smooth = False
tris = len(o.data.polygons)

if PREV: os.makedirs(PREV, exist_ok=True)
texturas.cozer(o, M, PREV)
os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SM_Cripta_Entulho.glb"), use_selection=True, export_format='GLB', export_yup=True)
print("exportado SM_Cripta_Entulho", tris, "tris", tuple(round(d, 2) for d in o.dimensions))

if PREV:
    sc = bpy.context.scene; sc.cycles.samples = 24
    sc.render.resolution_x = 640; sc.render.resolution_y = 480
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.07, 1); sc.world = w
    sun = bpy.data.objects.new("s", bpy.data.lights.new("s", 'SUN')); sun.data.energy = 2.2; sun.rotation_euler = (0.9, 0.2, 0.6); bpy.context.collection.objects.link(sun)
    fill = bpy.data.objects.new("f", bpy.data.lights.new("f", 'AREA')); fill.data.energy = 40; fill.data.size = 3; fill.location = (-2, -2, 2); fill.rotation_euler = (1.0, 0, -0.8); bpy.context.collection.objects.link(fill)
    chao = bpy.data.objects.new("g", bpy.data.meshes.new("g")); bpy.context.collection.objects.link(chao)
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4); bm.to_mesh(chao.data); bm.free()
    chao.data.materials.append(comum.mat("g", (0.07, 0.07, 0.08)))
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam); sc.camera = cam
    for nome, (x, y, z) in {"a": (3.4, -3.6, 2.6), "b": (-3.8, 2.0, 1.6)}.items():
        cam.location = (x, y, z); cam.rotation_euler = (Vector((0, 0, 0.35)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(PREV, f"entulho_{nome}.png"); bpy.ops.render.render(write_still=True)
