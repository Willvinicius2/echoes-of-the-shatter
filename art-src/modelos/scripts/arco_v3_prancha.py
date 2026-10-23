"""Arco v3: renders (Eevee, CPU/Blender -b) do GLB em frente, 3/4, costas, close da ponta e wireframe.
Uso: blender -b -P arco_v3_prancha.py -- <glb> <pasta_saida>"""
import bpy, sys, os, math
from mathutils import Vector
glb, outdir = sys.argv[sys.argv.index("--") + 1:][:2]
os.makedirs(outdir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 600, 1000
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new("w"); w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (.60, .60, .62, 1); bg.inputs[1].default_value = 1.1; sc.world = w
def sun(rot, en, col=(1, 1, 1)):
    d = bpy.data.lights.new("s", 'SUN'); d.energy = en; d.color = col
    o = bpy.data.objects.new("s", d); sc.collection.objects.link(o); o.rotation_euler = rot
sun((math.radians(50), 0, math.radians(-35)), 3.2, (1, .95, .88)); sun((math.radians(60), 0, math.radians(150)), 1.6, (.8, .85, 1))
sun((math.radians(100), 0, math.radians(90)), 1.2, (1, .8, .9))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'
def shot(name, az, center, scale, wire=False, elev=0.0, res=None):
    cam.data.ortho_scale = scale
    if res: sc.render.resolution_x, sc.render.resolution_y = res
    a = math.radians(az); d = 3.0
    cam.location = Vector(center) + Vector((math.sin(a) * d * math.cos(elev), -math.cos(a) * d * math.cos(elev), d * math.sin(elev)))
    cam.rotation_euler = (Vector(center) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for o in meshes:
        for m in [x for x in o.modifiers if x.type == 'WIREFRAME']: o.modifiers.remove(m)
        if wire:
            mod = o.modifiers.new("w", 'WIREFRAME'); mod.thickness = 0.0016; mod.use_replace = True
    sc.render.filepath = os.path.join(outdir, name + ".png"); bpy.ops.render.render(write_still=True)
GY = 0.10
shot("frente", 90, (0, GY, 0), 1.3)
shot("tq", 55, (0, GY, 0), 1.3, elev=0.18)
shot("costas", 270, (0, GY, 0), 1.3)
shot("close", 60, (0, 0.14, 0.50), 0.36, elev=0.2)
shot("wire", 90, (0, GY, 0), 1.3, wire=True)
shot("close2", 90, (0, 0.14, 0.50), 0.36)
shot("base", 90, (0, 0.10, 0.40), 0.14, res=(700,700))
shot("basew", 90, (0, 0.10, 0.40), 0.14, wire=True, res=(700,700))
