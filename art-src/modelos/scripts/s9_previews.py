"""Etapa 9 (Blender, Eevee): previas 1024 px com luz neutra e fundo cinza: frente, 3/4, costas e pose de teste.

Abre final/<asset>.blend (malha com material e esqueleto). Se o Eevee nao subir no modo -b, cai para Cycles na CPU.
Grava final/previews/<asset>_{frente,3-4,costas,pose}.png.
"""
import bpy, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mathutils import Vector

cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
bpy.ops.wm.open_mainfile(filepath=fpath(cfg, cfg["asset"] + ".blend"))
arm = bpy.data.objects[gb_rig.RIG_NAME]
sc = bpy.context.scene
os.makedirs(fpath(cfg, "previews"), exist_ok=True)
sc.render.resolution_x = sc.render.resolution_y = 1024
try:
    sc.render.engine = 'BLENDER_EEVEE'
except TypeError:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new("w"); w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.42, 0.42, 0.42, 1); bg.inputs[1].default_value = 0.9
sc.world = w
# luz neutra: sol de tres quartos + preenchimento suave
def light(name, kind, energy, rot, loc=(0, 0, 3)):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy
    lo = bpy.data.objects.new(name, ld); lo.rotation_euler = rot; lo.location = loc
    sc.collection.objects.link(lo)
    return lo
light("key", 'SUN', 2.6, (math.radians(50), 0, math.radians(-35)))
light("fill", 'SUN', 0.9, (math.radians(65), 0, math.radians(140)))
cam = bpy.data.cameras.new("cam"); cam.lens = 70
co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
target = Vector((0, 0, 0.82))

def shot(name, az_deg, dist=3.7):
    a = math.radians(az_deg)
    co.location = target + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0.25))
    d = target - co.location
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = fpath(cfg, f"previews/{cfg['asset']}_{name}.png")
    bpy.ops.render.render(write_still=True)

shot("frente", 0)
shot("3-4", -40)
shot("costas", 180)
apply_test_pose(arm)
shot("pose", -40)
print("S9 ok", sc.render.engine)
