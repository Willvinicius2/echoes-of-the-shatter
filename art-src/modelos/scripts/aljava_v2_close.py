# close-ups (derivado de previas_glb.py)
import bpy, sys, os, math, json
from mathutils import Vector
glb, outdir, tag = sys.argv[sys.argv.index("--") + 1:][:3]
os.makedirs(outdir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs = list(bpy.data.objects)
roots = [o.name for o in objs if o.parent is None]
meshes = [o for o in objs if o.type == 'MESH']
tris = sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons)
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
info = dict(roots=roots, tris=tris, bbox_min=[round(x, 3) for x in mn], bbox_max=[round(x, 3) for x in mx], images=[i.name for i in bpy.data.images])
print("INFO", json.dumps(info)); json.dump(info, open(os.path.join(outdir, f"{tag}_info.json"), "w"))
sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = sc.render.resolution_y = 1024
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (.63, .63, .63, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc.world = w
sc.view_settings.view_transform = 'Standard'
size = 0.30; c = Vector((0.02, 0, 0.12))
for pos, e in (((0, 0, 0), 3.0),):
    pass
def sun(rot, en):
    d = bpy.data.lights.new("s", 'SUN'); d.energy = en; o = bpy.data.objects.new("s", d); sc.collection.objects.link(o); o.rotation_euler = rot
sun((math.radians(50), 0, math.radians(-35)), 3.0); sun((math.radians(60), 0, math.radians(150)), 1.5)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = size * 1.12
def shot(az, name, wire=False):
    # glTF importado esta em Y-up convertido para Z-up do Blender: frente do glTF (+Z gltf) = -Y blender
    d = size * 3; a = math.radians(az)
    cam.location = c + Vector((math.sin(a) * d, -math.cos(a) * d, 0.12 * size * (1 if az not in (0, 180) else 0)))
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for o in meshes:
        for m in [x for x in o.modifiers if x.type == 'WIREFRAME']: o.modifiers.remove(m)
        if wire:
            mod = o.modifiers.new("w", 'WIREFRAME'); mod.thickness = size * 0.004; mod.use_replace = True
    sc.render.filepath = os.path.join(outdir, f"{tag}_{name}.png"); bpy.ops.render.render(write_still=True)
shot(20, "close1"); c = Vector((0.01, 0, -0.02)); size = 0.22; cam.data.ortho_scale = size * 1.12; shot(0, "close2")
