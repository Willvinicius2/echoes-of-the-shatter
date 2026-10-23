"""Renders do modulo (Eevee) montado no corpo. blender -b -P brac_render.py -- <bracers.glb> <saida_prefixo> <vistas> [pose_json]
vistas: lista 'nome:az:el:cx:cz:escala:res' separadas por ';' (ortografica). pose_json: {"Bone": [rx,ry,rz graus]} aplicado a todos os esqueletos."""
import bpy, sys, math, json, os
from mathutils import Vector, Euler
args = sys.argv[sys.argv.index("--") + 1:]
glb, outp, views = args[0], args[1], args[2]
pose = json.loads(args[3]) if len(args) > 3 else {}
body_glb = "D:/openclaude/_trabalho-claude/wt/arqueiro-dark-3d/godot/art/models/personagens/arqueiro_dark/ArcherDark_Body.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=body_glb)
body_objs = list(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=glb)
brac_objs = [o for o in bpy.data.objects if o not in body_objs]
for o in body_objs:
    if o.type == 'MESH' and "Hair" in o.name:
        pass
if os.environ.get('BHIDE'):
    for o in body_objs:
        if o.type == 'MESH':
            o.hide_render = True
for arm in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
    for bn, e in pose.items():
        pb = arm.pose.bones.get(bn)
        if pb:
            pb.rotation_mode = 'XYZ'; pb.rotation_euler = Euler([math.radians(a) for a in e], 'XYZ')
bpy.context.view_layer.update()
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (.48, .50, .55, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc.world = w; sc.view_settings.view_transform = 'Standard'
def sun(rot, en, col=(1, 1, 1)):
    d = bpy.data.lights.new("s", 'SUN'); d.energy = en; d.color = col
    o = bpy.data.objects.new("s", d); sc.collection.objects.link(o); o.rotation_euler = rot
sun((math.radians(55), 0, math.radians(-30)), 3.2, (1, .95, .88)); sun((math.radians(60), 0, math.radians(150)), 1.6, (.7, .8, 1))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.type = 'ORTHO'
for spec in views.split(";"):
    n, az, el, cx, cz, scl, res = spec.split(":")
    sc.render.resolution_x = sc.render.resolution_y = int(res)
    cam.data.ortho_scale = float(scl)
    a = math.radians(float(az)); e = math.radians(float(el)); c = Vector((float(cx), 0, float(cz)))
    cam.location = c + Vector((math.sin(a) * math.cos(e) * 6, -math.cos(a) * math.cos(e) * 6, math.sin(e) * 6))
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for o in brac_objs:
        if o.type == 'MESH':
            for m in [x for x in o.modifiers if x.type == 'WIREFRAME']:
                o.modifiers.remove(m)
            if n.startswith("wire"):
                md = o.modifiers.new("w", 'WIREFRAME'); md.thickness = 0.0007; md.use_replace = True
    sc.render.filepath = f"{outp}_{n}.png"
    bpy.ops.render.render(write_still=True)
print("BEXP render ok")
