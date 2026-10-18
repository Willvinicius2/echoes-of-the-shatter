"""Escala do elenco (Blender, Eevee): renderiza cada personagem (final/<asset>.blend, malha unica) com a MESMA camera, sem reenquadrar,
para comparar tamanhos: frente (lente 70 mm a 3,9 m, alvo z = 0,85) e camera do jogo (pitch 55, yaw 45, FOV 14,2, distancia do heroi de 1,5 m).
Uso: blender -b --factory-startup -P m_prancha_npc.py -- <pasta de saida> rotulo=caminho.blend [rotulo=caminho.blend ...]
Grava <saida>/cast_<rotulo>_{frente,jogo}.png (frente 1024; jogo 2048 transparente)."""
import bpy, math, sys, os
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out = args[0]; os.makedirs(out, exist_ok=True)
for a in args[1:]:
    label, blend = a.split("=", 1)
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
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
    sc.render.resolution_x = sc.render.resolution_y = 1024
    target = Vector((0, 0, 0.85)); co.location = target + Vector((0, -3.9, 0.25))
    co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{out}/cast_{label}_frente.png"; bpy.ops.render.render(write_still=True)
    sc.render.resolution_x = sc.render.resolution_y = 2048
    sc.render.film_transparent = True
    cam.lens = 18 / math.tan(math.radians(7.1))
    target = Vector((0, 0, 0.75)); el, az = math.radians(55), math.radians(-45)
    d = 1.5 / (2 * math.tan(math.radians(7.1))) * 1.25
    co.location = target + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * d
    co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{out}/cast_{label}_jogo.png"; bpy.ops.render.render(write_still=True)
print("MCAST ok")
