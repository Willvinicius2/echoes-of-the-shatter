"""Modular (Blender, Eevee): previas das 5 combinacoes (completo, sem elmo, sem luvas, sem botas, so corpo) em frente e 3/4, 1024 px."""
import bpy, math, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mdl_modular import *
from mathutils import Vector

cfg = load_cfg()
arm, pieces, regs = assemble(cfg)
hides = json.load(open(fpath(cfg, "hides_regions.json"))) if False else cfg["hides"]
sc = bpy.context.scene
os.makedirs(fpath(cfg, "previews"), exist_ok=True)
sc.render.resolution_x = sc.render.resolution_y = 1024
sc.render.engine = 'BLENDER_EEVEE'
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.42, 0.42, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
sc.world = w
def light(name, energy, rot):
    ld = bpy.data.lights.new(name, 'SUN'); ld.energy = energy
    lo = bpy.data.objects.new(name, ld); lo.rotation_euler = rot; sc.collection.objects.link(lo)
light("key", 2.6, (math.radians(50), 0, math.radians(-35))); light("fill", 0.9, (math.radians(65), 0, math.radians(140)))
cam = bpy.data.cameras.new("cam"); cam.lens = 70
co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
target = Vector((0, 0, 0.85)); dist = 3.9
def shot(name, az):
    a = math.radians(az)
    co.location = target + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0.25))
    co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = fpath(cfg, f"previews/{cfg['hero']}_modular_{name}.png")
    bpy.ops.render.render(write_still=True)
for cn, worn in COMBOS.items():
    set_combo(pieces, regs, worn, hides)
    shot(f"{cn}_frente", 0); shot(f"{cn}_3-4", -40)
print("MPREV ok")
