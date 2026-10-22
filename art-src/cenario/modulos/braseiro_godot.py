"""Módulo 3D do braseiro da Cripta para o Godot, montado por partes (referência: referencias-cripta/objeto.png).
  blender -b --factory-startup -P braseiro_godot.py -- <saida.glb> [pasta_previas]
Cada parte fica em braseiro/<parte>.py (pernas, bacia, gaiola, correntes, brasas) e é construída e renderizada
separada antes da montagem. Metros, pivô no centro da base, +Z para cima no Blender (o glTF vira Y-up).
A cor de desgaste (arestas vivas, fuligem, ferrugem) vai em vertex color (COLOR_0), multiplicada pelo material."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from braseiro import _lib, pernas, bacia, gaiola, correntes, brasas

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "SM_Cripta_Braseiro.glb"
PREV = argv[1] if len(argv) > 1 else None
SAMPLES = int(os.environ.get("SAMPLES", "24"))
objs = _lib.objs

PARTS = [("pernas", pernas), ("bacia", bacia), ("gaiola", gaiola), ("correntes", correntes), ("brasas", brasas)]
ranges = {}
for name, mod in PARTS:
    a = len(objs); mod.build(); ranges[name] = objs[a:]

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
    for m in body.data.materials:           # prévia: cor do vértice multiplica o material, como no Godot
        if m.name in ("M_Braseiro_Brasa", "M_Braseiro_Cinza"): continue
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        a = nt.nodes.new("ShaderNodeVertexColor"); a.layer_name = "Col"
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
        mx.inputs[6].default_value = b.inputs["Base Color"].default_value
        nt.links.new(a.outputs["Color"], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    sc = setup_render(800)
    shot(sc, "braseiro_tres_quartos", (2.6, -2.6, 2.2), (0, 0, 0.8))
    shot(sc, "braseiro_frente", (0, -3.6, 1.0), (0, 0, 0.8))
    shot(sc, "braseiro_close_borda", (0.6, -1.5, 1.7), (0.1, 0, 1.3), 60)
    shot(sc, "braseiro_cima", (0.01, -0.8, 3.0), (0, 0, 1.2))
