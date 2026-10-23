"""Renders da prancha do corpo-base (Blender -b, Eevee, 1 por vez): close do rosto, wireframe frente e 3/4 (arestas por modificador
Wireframe sobre o corpo cinza), triangulos. Uso: blender -b --factory-startup -P prancha_corpo.py -- <id>
Grava work/prancha/{rosto,rosto3q,wire_frente,wire_34}.png; a montagem (entrada + folha v2 + renders) e feita por prancha_montar.py."""
import bpy, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mathutils import Vector
cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
bpy.ops.wm.open_mainfile(filepath=fpath(cfg, cfg["asset"] + ".blend"))
sc = bpy.context.scene
out = wpath(cfg, "prancha"); os.makedirs(out, exist_ok=True)
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
ob = next(o for o in bpy.data.objects if o.type == 'MESH')
def shot(name, target, az_deg, dist, lens=70, elev=0.0):
    cam.lens = lens; a = math.radians(az_deg)
    co.location = Vector(target) + Vector((math.sin(a) * dist, -math.cos(a) * dist, elev))
    co.rotation_euler = (Vector(target) - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{out}/{name}.png"; bpy.ops.render.render(write_still=True)
head = (0, 0.0, 1.66)
shot("rosto", head, 0, 1.0, lens=85)
shot("rosto3q", head, -35, 1.0, lens=85)
# wireframe: material cinza claro + modificador Wireframe (arestas dos triangulos) sobre um clone solido cinza
mat = bpy.data.materials.new("g"); mat.use_nodes = True; mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.78, 0.78, 0.8, 1)
ob.data.materials.clear(); ob.data.materials.append(mat)
mw = bpy.data.materials.new("wire"); mw.use_nodes = True; mw.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.05, 0.08, 1)
ob.data.materials.append(mw)
m = ob.modifiers.new("wf", 'WIREFRAME'); m.thickness = 0.0016; m.use_replace = False; m.material_offset = 1
for az, nm in ((0, "wire_frente"), (-40, "wire_34")):
    shot(nm, (0, 0, 0.9), az, 4.0)
print("PRANCHA ok", len(ob.data.polygons))
