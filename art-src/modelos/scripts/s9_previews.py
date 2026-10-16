"""Etapa 9 (Blender, Eevee): previas 1024 px com luz neutra e fundo cinza: frente, 3/4, costas e pose de teste.

Abre final/<asset>.blend (malha com material e esqueleto). Se o Eevee nao subir no modo -b, cai para Cycles na CPU.
Grava final/previews/<asset>_{frente,3-4,costas,pose}.png e work/captura_base.png (camera do jogo, 2048, transparente).
"""
import bpy, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mathutils import Vector

cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
bpy.ops.wm.open_mainfile(filepath=fpath(cfg, cfg["asset"] + ".blend"))
arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
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
vs = [o for o in bpy.data.objects if o.type == 'MESH']
bb = [o.matrix_world @ Vector(c) for o in vs for c in o.bound_box]
bmin = Vector([min(p[i] for p in bb) for i in range(3)]); bmax = Vector([max(p[i] for p in bb) for i in range(3)])
target = (bmin + bmax) / 2
SZ = max(bmax - bmin)

def shot(name, az_deg, dist=None):
    dist = dist or 2.25 * SZ
    a = math.radians(az_deg)
    co.location = target + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0.15 * SZ))
    d = target - co.location
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = fpath(cfg, f"previews/{cfg['asset']}_{name}.png")
    bpy.ops.render.render(write_still=True)

shot("frente", 0)
shot("3-4", -40)
shot("costas", 180)
if arm is not None:
    test_pose(arm, cfg["kind"])
    shot("pose", -40)
# captura da camera do jogo (pitch 55, yaw 45, FOV vertical 14,2) em 2048 transparente; s10 reduz a 512, 88 e 65 px de altura
sc.render.resolution_x = sc.render.resolution_y = 2048
sc.render.film_transparent = True
cam.lens = 18 / math.tan(math.radians(7.1))
if arm is not None:
    clear_pose(arm)
el, az, dist = math.radians(55), math.radians(-45), SZ / (2 * math.tan(math.radians(7.1))) * 1.25
co.location = target + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = wpath(cfg, "captura_base.png")
bpy.ops.render.render(write_still=True)
print("S9 ok", sc.render.engine)
