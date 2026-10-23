"""Previas das luvas v2 (Cycles CPU, baixa amostragem). Uso: python render_luvas.py [glb_luvas] [saida_dir] [tag]
Importa Corpo + Luvas (+ Arco no socket) e renderiza closes de cada mao. Um render por vez."""
import os, sys, math
import bpy
from mathutils import Vector
RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
GLBS = os.path.join(RAIZ, "godot", "art", "models", "personagens", "arqueiro")
luvas = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else os.path.join(GLBS, "Arqueiro_Luvas.glb")
out = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else os.path.join(os.path.dirname(os.path.abspath(__file__)), "previas")
tag = sys.argv[3] if len(sys.argv) > 3 else "v0"
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 640
sc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.33, 0.36, 1); sc.world = w
for loc, en in (((-3, -4, 5), 3.0), ((4, 3, 2), 1.2)):
    l = bpy.data.lights.new("s", "SUN"); l.energy = en
    o = bpy.data.objects.new("s", l); sc.collection.objects.link(o)
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
def imp(p):
    a = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=p)
    n = [o for o in bpy.data.objects if o not in a]
    for o in list(n):
        if o.name.startswith("Icosphere"): bpy.data.objects.remove(o); n.remove(o)
    return n
imp(os.path.join(GLBS, "Arqueiro_Corpo.glb")); L = imp(luvas)
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
arm = arms[0]
hp = lambda n: arm.matrix_world @ arm.pose.bones[n].head
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"
def shot(name, ctr, scale, az, el):
    d = Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)), -math.cos(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el))))
    cam.location = ctr + d * 3; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler(); cam.data.ortho_scale = scale
    sc.render.filepath = os.path.join(out, f"{tag}_{name}.png"); bpy.ops.render.render(write_still=True)
for lado, nome in (("esq", "LeftHand"), ("dir", "RightHand")):
    c = hp(nome); s = 1 if lado == "esq" else -1
    shot(f"{lado}_frente", c + Vector((0,0,0.0)), 0.42, 0, 10)
    shot(f"{lado}_3q", c, 0.42, 40 * s, 20)
    shot(f"{lado}_lado", c, 0.42, 90 * s, 5)
    shot(f"{lado}_costas", c, 0.42, 180, 10)
