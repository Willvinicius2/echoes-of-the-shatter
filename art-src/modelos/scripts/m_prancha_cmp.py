"""Comparacao de conjuntos modulares (Blender, Eevee): renderiza o heroi COMPLETO (corpo + 5 pecas) de cada conjunto em frente, costas, 3/4 e camera do jogo.

Uso: blender -b --factory-startup -P m_prancha_cmp.py -- <cfg do corte do conjunto novo> <rotulo=blend,...>
  ex.: -- mod_warrior_rare_cut Starter=D:/.../SK_Warrior_Modular.blend Rare=D:/.../SK_Warrior_Modular.blend
Grava <final_dir>/previews/cmp_<rotulo>_{frente,costas,3-4,jogo}.png (1024; o jogo em 2048 transparente, camera do s9: pitch 55, yaw 45, FOV 14,2).
Cada blend traz Body_<Regiao> e SK_<Heroi>_<Slot>_<Conjunto>; esconde as regioes do corpo que as pecas cobrem (cfg["hides"]).
"""
import bpy, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_modular import SLOTS, REGIONS
from mathutils import Vector

cfg = load_cfg(sys.argv[:sys.argv.index("--") + 2])
pairs = [a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 2:]]
out = fpath(cfg, "previews"); os.makedirs(out, exist_ok=True)
hidden = set(r for s in SLOTS for r in cfg["hides"][s])


def render_set(label, blend):
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        if o.name.startswith("Body_"):
            o.hide_render = o.hide_viewport = o.name[5:] in hidden
        else:
            o.hide_render = o.hide_viewport = False
    sc.render.engine = 'BLENDER_EEVEE'
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.42, 0.42, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    sc.world = w
    for name, e, rot in (("key", 2.6, (math.radians(50), 0, math.radians(-35))), ("fill", 0.9, (math.radians(65), 0, math.radians(140)))):
        ld = bpy.data.lights.new(name, 'SUN'); ld.energy = e
        lo = bpy.data.objects.new(name, ld); lo.rotation_euler = rot; sc.collection.objects.link(lo)
    cam = bpy.data.cameras.new("cam"); cam.lens = 70
    co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
    target = Vector((0, 0, 0.85)); dist = 3.9
    sc.render.resolution_x = sc.render.resolution_y = 1024
    for name, az in (("frente", 0), ("costas", 180), ("3-4", -40)):
        a = math.radians(az)
        co.location = target + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0.25))
        co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f"{out}/cmp_{label}_{name}.png"
        bpy.ops.render.render(write_still=True)
    # camera do jogo, mesma geometria do s9 (altura 1,5 m + pluma: SZ = 1,5)
    sc.render.resolution_x = sc.render.resolution_y = 2048
    sc.render.film_transparent = True
    cam.lens = 18 / math.tan(math.radians(7.1))
    SZ = 1.5; target = Vector((0, 0, 0.75))
    el, az = math.radians(55), math.radians(-45)
    d = SZ / (2 * math.tan(math.radians(7.1))) * 1.25
    co.location = target + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * d
    co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{out}/cmp_{label}_jogo.png"
    bpy.ops.render.render(write_still=True)


for label, blend in pairs:
    render_set(label, blend)
print("MCMP ok")
