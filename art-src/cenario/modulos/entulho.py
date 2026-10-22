"""Módulo 3D: entulho da Cripta (referência: referencias-cripta/objetos.png, monte de lajes quebradas com musgo).
python entulho.py <pasta_saida> [pasta_previas]    (módulo bpy) ou  blender -b --factory-startup -P entulho.py -- <saida> [previas]
Metros, +Z para cima, pivô no centro da base. Montado por partes em entulho_partes/:
forma (fragmentos naturais) -> monte (composição) -> assentar (física de corpo rígido) -> musgo -> terra -> texturas (pintadas, embutidas no .glb)."""
import bpy, bmesh, math, sys, os, zlib
from mathutils import Vector
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "entulho_partes"))
import comum, monte, musgo, terra, texturas, assentamento

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None
TEX = os.path.join(PREV or OUT, "tex") if (PREV or OUT) else "tex"

bpy.ops.wm.read_factory_settings(use_empty=True)
M = comum.criar_materiais()
pedras = monte.construir(M)
cs = [sum((o.matrix_world @ v.co for v in o.data.vertices), Vector()) / len(o.data.vertices) for o in pedras]
chao = terra.construir(M, (sum(c.x for c in cs) / len(cs), sum(c.y for c in cs) / len(cs)))
assentamento.assentar(pedras, chao)
tufos = musgo.construir(M, pedras)

import random
for o in pedras:   # tom por pedra: de bege quente a cinza frio, brilho variado
    k = random.Random(zlib.crc32(o.name.encode())); b = k.uniform(1.15, 1.65); w = k.uniform(0.0, 1.0)
    texturas.preparar(o, (b * (1.0 + 0.06 * w), b * (0.96 + 0.04 * w), b * (0.88 + 0.1 * (1 - w))))
for o in tufos: texturas.preparar(o, (1, 1, 1))
texturas.preparar(chao, (1, 1, 1))
bpy.ops.object.select_all(action='DESELECT')
todos = pedras + tufos + [chao]
for o in todos: o.select_set(True)
bpy.context.view_layer.objects.active = todos[0]
bpy.ops.object.join(); o = bpy.context.object
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
o.name = "SM_Cripta_Entulho"
bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(o.data); bm.free()
for p in o.data.polygons: p.use_smooth = False
tris = len(o.data.polygons)

novos = texturas.aplicar(M, TEX)
texturas.trocar_materiais(o, M, novos)
texturas.oclusao_vertice(o)
os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SM_Cripta_Entulho.glb"), use_selection=True, export_format='GLB', export_yup=True, export_image_format='JPEG', export_jpeg_quality=85)
print("exportado SM_Cripta_Entulho", tris, "tris", tuple(round(d, 2) for d in o.dimensions))

if PREV:
    os.makedirs(PREV, exist_ok=True)
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = False
    RAP = bool(os.environ.get('ENTULHO_RAPIDO'))
    sc.render.resolution_x, sc.render.resolution_y = (400, 280) if RAP else (800, 560)
    if RAP: sc.cycles.samples = 8
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.07, 1); sc.world = w
    sun = bpy.data.objects.new("s", bpy.data.lights.new("s", 'SUN')); sun.data.energy = 2.6; sun.rotation_euler = (0.9, 0.2, 0.6); bpy.context.collection.objects.link(sun)
    fill = bpy.data.objects.new("f", bpy.data.lights.new("f", 'AREA')); fill.data.energy = 60; fill.data.size = 3; fill.location = (-2, -2, 2); fill.rotation_euler = (1.0, 0, -0.8); bpy.context.collection.objects.link(fill)
    g = bpy.data.objects.new("g", bpy.data.meshes.new("g")); bpy.context.collection.objects.link(g)
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4); bm.to_mesh(g.data); bm.free(); g.data.materials.append(comum.mat("g", (0.09, 0.09, 0.1)))
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam); sc.camera = cam
    angulos = (("a", (2.8, -3.0, 0.95), 0.4), ("frente", (0.0, -3.6, 0.55), 0.45), ("lado", (3.6, 0.0, 0.55), 0.45), ("b", (-2.8, 1.8, 0.7), 0.4), ("cima", (0.01, -0.6, 4.2), 0.0), ("close", (1.3, -1.4, 0.5), 0.35))
    for nome, (x, y, z), alvo in (angulos[:1] if RAP else angulos):
        cam.location = (x, y, z); cam.rotation_euler = (Vector((0, 0, alvo)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(PREV, f"entulho_{nome}.png"); bpy.ops.render.render(write_still=True)
    if RAP: sys.exit(0)
    # wireframe: material de substituição com nó Wireframe
    wm = bpy.data.materials.new("wire"); wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear()
    wf = nt.nodes.new("ShaderNodeWireframe"); wf.inputs[0].default_value = 0.01; em = nt.nodes.new("ShaderNodeEmission"); ot = nt.nodes.new("ShaderNodeOutputMaterial")
    bg = nt.nodes.new("ShaderNodeBsdfDiffuse"); bg.inputs[0].default_value = (0.02, 0.02, 0.02, 1); mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(wf.outputs[0], mx.inputs[0]); nt.links.new(bg.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], ot.inputs[0])
    bpy.context.view_layer.material_override = wm
    cam.location = (2.6, -2.9, 2.0); cam.rotation_euler = (Vector((0, 0, 0.25)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(PREV, "entulho_wire.png"); bpy.ops.render.render(write_still=True)
