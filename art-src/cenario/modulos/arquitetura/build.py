"""Monta um módulo de arquitetura e exporta .glb + prévias.
Uso: blender-python build.py <modulo> [saida_dir]   (python -I build.py nicho /tmp/out)
Cada módulo (arquivo <modulo>.py) tem build(L) que cria objetos via L.add/L.box/L.new_obj e caixas via L.col_box."""
import bpy, sys, os, math, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
from mathutils import Vector
nome = sys.argv[1]; OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/arq_out"
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
mod = importlib.import_module(nome); mod.build(L)
GLB = getattr(mod, "GLB", f"SM_Cripta_{nome.capitalize()}")
bpy.ops.object.select_all(action='DESELECT')
for o in L.objs: o.select_set(True)
bpy.context.view_layer.objects.active = L.objs[0]; bpy.ops.object.join()
o = bpy.context.object; o.name = GLB
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
n0 = len(o.data.polygons)
m = o.modifiers.new("plano", 'DECIMATE'); m.decimate_type = 'DISSOLVE'; m.angle_limit = math.radians(6); m.delimit = {'MATERIAL', 'UV'}
bpy.ops.object.modifier_apply(modifier="plano")
print("faces", n0, "->", len(o.data.polygons), "dim", tuple(round(d, 2) for d in o.dimensions), "cols", len(L.cols))
# exporta visível + colisões
bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
for c in L.cols: c.select_set(True)
if os.environ.get("EXPORTAR", "1") == "1":
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, GLB + ".glb"), use_selection=True, export_format='GLB', export_yup=True, export_image_format='JPEG', export_jpeg_quality=88)
# prévias (colisões ocultas no render)
for c in L.cols: c.hide_render = True
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get("AMOSTRAS", "24")); sc.cycles.device = 'CPU'; sc.cycles.use_denoising = True
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.055, 0.09, 1); sc.world = w
def sun(rot, e, color):
    s = bpy.data.objects.new("s", bpy.data.lights.new("s", 'SUN')); s.data.energy = e; s.data.color = color; s.rotation_euler = rot; bpy.context.collection.objects.link(s)
sun((math.radians(55), 0, math.radians(35)), 3.0, (1.0, 0.8, 0.6)); sun((math.radians(70), 0, math.radians(-140)), 1.5, (0.55, 0.6, 1.0))
# o chão de apoio para ler a escala (herói de 1,8 m = cilindro cinza)
bpy.ops.mesh.primitive_cylinder_add(radius=0.28, depth=1.8, location=(getattr(mod, "HEROI_X", 1.2), getattr(mod, "HEROI_Y", 2.2), 0.9)); h = bpy.context.object
h.data.materials.append(L.mat("heroi", (0.6, 0.2, 0.2)))
d = max(o.dimensions) ; cz = o.dimensions.z / 2
views = getattr(mod, "VISTAS", {"frente": ((0, d * 1.9, cz), (0, 0, cz), 700, 900), "tres_quartos": ((-d * 1.1, d * 1.2, cz * 1.5), (0, 0, cz * 0.8), 800, 900), "close": ((-d * 0.45, d * 0.6, 2.5), (0, 0, 2.2), 800, 800)})
for nm, (loc, tgt, rx, ry) in views.items():
    cam = bpy.data.cameras.new("c"); co = bpy.data.objects.new("c", cam); bpy.context.collection.objects.link(co)
    co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co; sc.render.resolution_x = rx; sc.render.resolution_y = ry
    sc.render.filepath = os.path.join(OUT, f"{nome}_{nm}.png"); bpy.ops.render.render(write_still=True)
