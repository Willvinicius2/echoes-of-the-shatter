"""Módulo 3D do braseiro da Cripta para o Godot, montado por partes (referência: referencias-cripta/objeto.png).
  blender -b --factory-startup -P braseiro_godot.py -- <saida.glb> [pasta_previas]
Cada parte fica em braseiro/<parte>.py (pernas, bacia, gaiola, correntes, brasas) e é construída e renderizada
separada antes da montagem. Metros, pivô no centro da base, +Z para cima no Blender (o glTF vira Y-up).
A cor de desgaste (arestas vivas, fuligem, ferrugem) vai em vertex color (COLOR_0), multiplicada pelo material."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
from braseiro import _lib

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "SM_Cripta_Braseiro.glb"
PREV = argv[1] if len(argv) > 1 else None
SAMPLES = int(os.environ.get("SAMPLES", "24"))
objs = _lib.objs

ONLY = os.environ.get("PARTES", "pernas,bacia,gaiola,correntes,brasas").split(",")
PARTS = [(n, importlib.import_module("braseiro." + n)) for n in ONLY]
ranges = {}
for name, mod in PARTS:
    a = len(objs); _lib.PARTE[0] = name; mod.build(); ranges[name] = objs[a:]; print("parte", name, "ok;", len(objs) - a, "objetos")
_lib.uv_todos()
print("SEM MAT", [(o.name, o.parent) for o in objs if not o.data.materials][:5])

def setup_render(res=800):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.cycles.device = 'CPU'
    sc.view_settings.view_transform = 'Standard'; sc.render.resolution_x = sc.render.resolution_y = res
    sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.03, 0.03, 0.045)
    for loc, en, col in (((3, -3, 5), 3.0, (1, 0.95, 0.9)), ((-3, 2, 2), 1.5, (0.5, 0.6, 1.0))):
        bpy.ops.object.light_add(type='SUN', location=loc); Ln = bpy.context.object
        Ln.data.energy = en; Ln.data.color = col; Ln.rotation_euler = (Vector((0, 0, 0.8)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.object.light_add(type='POINT', location=(0, 0, 1.3)); bpy.context.object.data.energy = 120; bpy.context.object.data.color = (1, 0.5, 0.15)
    return sc

def shot(sc, name, loc, tgt, lens=45):
    bpy.ops.object.camera_add(location=loc); cam = bpy.context.object
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = lens
    sc.camera = cam; sc.render.filepath = os.path.join(PREV, name + ".png")
    bpy.ops.render.render(write_still=True)

# ---- previa de cada parte isolada
if PREV:
    os.makedirs(PREV, exist_ok=True)
    sc = setup_render(500)
    for name, _ in PARTS:
        for o in objs: o.hide_render = o not in ranges[name]
        shot(sc, f"parte_{name}", (2.6, -2.6, 2.2), (0, 0, 0.8))
    for o in objs: o.hide_render = False

# ---- juntar, soldar, vertex color de desgaste
for o in bpy.data.objects: o.select_set(o in objs)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.join()
body = bpy.context.object; body.name = "SM_Cripta_Braseiro"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bm = bmesh.new(); bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
bm.to_mesh(body.data); bm.free()
bpy.ops.object.shade_flat()
_lib.bake_vertex_colors(body)
tris = sum(len(p.vertices) - 2 for p in body.data.polygons)

bpy.ops.object.select_all(action='DESELECT'); body.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format='GLB', export_yup=True, export_vertex_color='ACTIVE')
print("tris", tris, "->", OUT)

if PREV:
    for m in body.data.materials:           # prévia: cor do vértice multiplica o albedo, como no Godot
        if m.name.startswith("M_Braseiro_Brasa") or m.name == "M_Braseiro_Cinza": continue
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        src = b.inputs["Base Color"].links[0].from_socket
        a = nt.nodes.new("ShaderNodeVertexColor"); a.layer_name = "Col"
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
        nt.links.new(src, mx.inputs[6]); nt.links.new(a.outputs["Color"], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    # chama só para a prévia (no Godot é cartão com shader + partículas): 3 cartões cruzados, emissivos com alfa
    if os.environ.get("CHAMA", "1") == "1":
        fp = _lib.tex_chama("chama_preview", 4)
        fm = bpy.data.materials.new("chama_prev"); fm.use_nodes = True; nt = fm.node_tree
        for nd in list(nt.nodes): nt.nodes.remove(nd)
        img = nt.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(fp)
        em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 2.6
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader"); out = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(img.outputs["Color"], em.inputs["Color"]); nt.links.new(img.outputs["Alpha"], mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
        for k, (w, h, yaw, dx) in enumerate(((1.2, 0.85, 0.0, 0.0), (1.2, 0.85, 1.05, 0.03), (0.9, 0.65, 2.1, -0.03))):
            bpy.ops.mesh.primitive_plane_add(size=1, location=(dx, 0, 1.36 + h / 2 - 0.1), rotation=(math.pi / 2, 0, yaw))
            c = bpy.context.object; c.scale = (w, h, 1); c.data.materials.append(fm)
            c.visible_shadow = False
    sc = setup_render(800)
    shot(sc, "braseiro_tres_quartos", (2.6, -2.6, 2.2), (0, 0, 0.8))
    shot(sc, "braseiro_frente", (0, -3.6, 1.0), (0, 0, 0.8))
    shot(sc, "braseiro_close_borda", (0.6, -1.5, 1.7), (0.1, 0, 1.3), 60)
    shot(sc, "braseiro_lado", (3.6, 0, 1.0), (0, 0, 0.9))
    shot(sc, "braseiro_cima", (0.01, -0.8, 3.0), (0, 0, 1.2))
    shot(sc, "braseiro_brasas_close", (0.0, -1.1, 2.15), (0, 0, 1.25), 50)
    shot(sc, "braseiro_pernas_close", (1.1, -1.3, 0.55), (0.35, -0.35, 0.45), 55)
    wf = body.modifiers.new("wf", 'WIREFRAME'); wf.thickness = 0.004
    shot(sc, "braseiro_wireframe", (2.6, -2.6, 2.2), (0, 0, 0.8))
