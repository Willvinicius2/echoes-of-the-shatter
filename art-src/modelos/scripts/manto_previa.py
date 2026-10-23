"""Previas do torso do arqueiro dark (Blender, Eevee): torso sozinho (frente, 3/4, costas, close, wire) e conjunto corpo + torso.
Uso: blender -b --factory-startup -P manto_previa.py -- <torso.glb> <corpo.glb> <pasta_saida>"""
import bpy, sys, os, math
from mathutils import Vector
torso, corpo, out = sys.argv[sys.argv.index("--") + 1:][:3]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = 800; sc.render.resolution_y = 1000
w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (.58, .58, .60, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc.world = w; sc.view_settings.view_transform = 'Standard'


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    return [o for o in new if o.type == 'MESH']


mt = load(torso)
mb = load(corpo)


def sun(rot, en):
    d = bpy.data.lights.new("s", 'SUN'); d.energy = en
    o = bpy.data.objects.new("s", d); sc.collection.objects.link(o); o.rotation_euler = rot


sun((math.radians(50), 0, math.radians(-35)), 3.0)
sun((math.radians(60), 0, math.radians(150)), 1.6)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'


def shot(name, az, center, scale, show, wire=False):
    for o in mt:
        o.hide_render = "t" not in show
    for o in mb:
        o.hide_render = "b" not in show
    cam.data.ortho_scale = scale
    a = math.radians(az); c = Vector(center)
    cam.location = c + Vector((math.sin(a) * 6, -math.cos(a) * 6, 0.15))
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for o in mt:
        for m in [x for x in o.modifiers if x.type == 'WIREFRAME']:
            o.modifiers.remove(m)
        if wire:
            md = o.modifiers.new("w", 'WIREFRAME'); md.thickness = 0.0012; md.use_replace = True
    sc.render.filepath = os.path.join(out, f"{name}.png")
    bpy.ops.render.render(write_still=True)


shot("t_frente", 0, (0, 0, 1.05), 1.55, "t")
shot("t_34", 35, (0, 0, 1.05), 1.55, "t")
shot("t_costas", 180, (0, 0, 1.05), 1.55, "t")
shot("t_close", 20, (0, 0, 1.42), 0.62, "t")
shot("t_wire", 25, (0, 0, 1.05), 1.55, "t", wire=True)
sc.render.resolution_x = 700; sc.render.resolution_y = 1100
shot("c_frente", 0, (0, 0, 0.9), 2.0, "tb")
shot("c_34", 35, (0, 0, 0.9), 2.0, "tb")
shot("c_costas", 180, (0, 0, 0.9), 2.0, "tb")
print("MPREV ok", sum(len(p.vertices) - 2 for o in mt for p in o.data.polygons))
