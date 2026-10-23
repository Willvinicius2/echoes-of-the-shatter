"""Previas da aljava v3 (Blender -b, EEVEE/Workbench CPU-safe): frente, 3/4, costas, closes e wireframe.
uso: blender -b -P aljava_v3_prev.py -- <glb> <out_dir>"""
import bpy, sys, os, math, json
from mathutils import Vector
glb, outdir = sys.argv[sys.argv.index("--") + 1:][:2]
os.makedirs(outdir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
roots = [o.name for o in bpy.data.objects if o.parent is None]
print("ROOTS", roots, {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes})
sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = sc.render.resolution_y = 1000
sc.eevee.taa_render_samples = 24
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (.63, .63, .63, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc.world = w; sc.view_settings.view_transform = 'Standard'
def sun(rot, en):
    d = bpy.data.lights.new("s", 'SUN'); d.energy = en; o = bpy.data.objects.new("s", d); sc.collection.objects.link(o); o.rotation_euler = rot
sun((math.radians(50), 0, math.radians(-35)), 3.0); sun((math.radians(60), 0, math.radians(150)), 1.6)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'
def shot(az, name, c, size, wire=False, el=0.1):
    d = 1.0; a = math.radians(az)
    cam.location = c + Vector((math.sin(a) * d, -math.cos(a) * d, el * d)); cam.data.ortho_scale = size
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for o in meshes:
        for m in [x for x in o.modifiers if x.type == 'WIREFRAME']: o.modifiers.remove(m)
        if wire:
            mod = o.modifiers.new("w", 'WIREFRAME'); mod.thickness = 0.0006; mod.use_replace = True
    sc.render.filepath = os.path.join(outdir, f"q_{name}.png"); bpy.ops.render.render(write_still=True)
C = Vector((0.0, 0, 0.0))
shot(0, "frente", C, 0.72); shot(-38, "3-4", C, 0.72); shot(180, "costas", C, 0.72)
shot(25, "close1", Vector((0.02, 0, 0.19)), 0.20)
shot(-15, "close2", Vector((-0.03, 0, 0.04)), 0.20)
shot(0, "close3", Vector((0.0, 0, 0.1)), 0.14, el=0.5)
shot(30, "wire", C, 0.72, wire=True)
if os.environ.get("EXTRA"):
    shot(-90, "esq", Vector((0, 0, 0.04)), 0.5); shot(90, "dir", Vector((0, 0, 0.04)), 0.5); shot(-60, "esq2", Vector((-0.03, 0, 0.06)), 0.25)
