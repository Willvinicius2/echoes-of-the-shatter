"""Monta o estandarte da Cripta a partir das partes e exporta .glb.
bpy: python build_estandarte.py -- <saida.glb> [pasta_previas]
Cada parte é um módulo com build(L) que cria objetos já com material (via lib.add)."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, lib as L
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "SM_Cripta_Estandarte.glb"
PREV = argv[1] if len(argv) > 1 else None
ONLY = os.environ.get("PARTES", "base_corrente,ferragem,pano").split(",")  # para iterar numa parte só

bpy.ops.wm.read_factory_settings(use_empty=True)
for nome in ONLY:
    importlib.import_module(nome).build(L)
    print("parte", nome, "ok;", len(L.objs), "objetos")

bpy.ops.object.select_all(action='DESELECT')
for o in L.objs: o.select_set(True)
bpy.context.view_layer.objects.active = L.objs[0]
bpy.ops.object.join()
o = bpy.context.object; o.name = "SM_Cripta_Estandarte"
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
# peso: dissolve de faces coplanares (não muda o visual) e triangulação final
n0 = len(o.data.polygons)
mod = o.modifiers.new("plano", 'DECIMATE'); mod.decimate_type = 'DISSOLVE'; mod.angle_limit = math.radians(float(os.environ.get("DISSOLVE_GRAUS", "6")))
mod.delimit = {'MATERIAL', 'UV'}
bpy.ops.object.modifier_apply(modifier="plano")
print("dissolve", n0, "->", len(o.data.polygons))
bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format='GLB', export_yup=True, export_image_format='JPEG', export_jpeg_quality=88)
print("faces", len(o.data.polygons), "dim", tuple(round(d, 2) for d in o.dimensions), "->", OUT)

if PREV:
    os.makedirs(PREV, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get("AMOSTRAS", "32")); sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = True
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.055, 0.08, 1); sc.world = w
    def sun(rot, e, color=(1, 1, 1)):
        s = bpy.data.objects.new("s", bpy.data.lights.new("s", 'SUN')); s.data.energy = e; s.data.color = color; s.rotation_euler = rot
        bpy.context.collection.objects.link(s)
    sun((math.radians(55), 0, math.radians(35)), 3.0, (1.0, 0.85, 0.7))      # luz quente principal (tocha)
    sun((math.radians(70), 0, math.radians(-140)), 1.2, (0.55, 0.65, 1.0))   # recorte frio
    views = {"frente": ((0, 7.5, 1.7), (0, 0, 1.7), 700, 900), "tres_quartos": ((-4.5, 5.5, 3.0), (-0.1, 0, 1.6), 700, 900),
             "pano_close": ((0.3, 2.2, 2.2), (0, 0, 2.0), 800, 800), "topo_close": ((-0.1, 2.0, 3.1), (-0.1, 0, 3.0), 800, 800), "base_close": ((-0.9, 2.2, 0.5), (-0.64, 0, 0.35), 800, 800)}
    only_v = os.environ.get("VISTAS")
    for nome, (loc, tgt, rx, ry) in views.items():
        if only_v and nome not in only_v.split(","): continue
        cam = bpy.data.cameras.new("c"); co = bpy.data.objects.new("c", cam); bpy.context.collection.objects.link(co)
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        sc.camera = co; sc.render.resolution_x = rx; sc.render.resolution_y = ry
        sc.render.filepath = os.path.join(PREV, f"{nome}.png"); bpy.ops.render.render(write_still=True)
