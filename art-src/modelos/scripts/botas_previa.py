"""Previas das botas (Blender -b, EEVEE): botas sozinhas e montadas no corpo (corpo cinza), frente, 3/4, costas, lado, close do pe, wireframe.
Uso: blender -b --factory-startup -P botas_previa.py -- arq_dark_botas <pasta_saida> [textura.png] [normal.png]"""
import bpy, sys, os, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
cfg = load_cfg()
args = sys.argv[sys.argv.index("--") + 1:]
out = args[1]; tex = args[2] if len(args) > 2 else None; nrm = args[3] if len(args) > 3 else None
os.makedirs(out, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(cfg["body_rig_blend"]), "game_uv.blend"))
body = bpy.data.objects["game"]; body.name = "body"
for o in list(bpy.data.objects):
    if o.type == 'ARMATURE':
        for c in o.children:
            pass
with bpy.data.libraries.load(wpath(cfg, "game_uv.blend")) as (src, dst):
    dst.objects = ["game"]
boots = dst.objects[0]
boots.name = "boots"
bpy.context.scene.collection.objects.link(boots)
boots.parent = None
for m in list(boots.modifiers):
    boots.modifiers.remove(m)
# material
mat = bpy.data.materials.new("mb"); mat.use_nodes = True
b = mat.node_tree.nodes["Principled BSDF"]
b.inputs["Roughness"].default_value = 0.55
if tex:
    t = mat.node_tree.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(tex)
    mat.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if nrm:
        n = mat.node_tree.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(nrm); n.image.colorspace_settings.name = "Non-Color"
        nm = mat.node_tree.nodes.new("ShaderNodeNormalMap")
        mat.node_tree.links.new(n.outputs["Color"], nm.inputs["Color"]); mat.node_tree.links.new(nm.outputs["Normal"], b.inputs["Normal"])
else:
    b.inputs["Base Color"].default_value = (0.35, 0.22, 0.16, 1)
mat.use_backface_culling = False
boots.data.materials.clear(); boots.data.materials.append(mat)
gm = bpy.data.materials.new("gm"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.62, 0.7, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
body.data.materials.clear(); body.data.materials.append(gm)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = 700; sc.render.resolution_y = 900
sc.render.film_transparent = False
sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.45, 0.46, 0.5, 1); bg.inputs[1].default_value = 0.9
for nme, loc, en in (("k", (2, -3, 4), 900), ("f", (-3, -2, 1.5), 350), ("r", (-1, 3, 2.5), 400)):
    ld = bpy.data.lights.new(nme, 'AREA'); ld.energy = en; ld.size = 3
    lo = bpy.data.objects.new(nme, ld); lo.location = loc; sc.collection.objects.link(lo)
    lo.rotation_euler = (Vector((0, 0, 0.5)) - lo.location).to_track_quat('-Z', 'Y').to_euler()
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.clip_end = 50


def shot(name, az, center, scale, show_body, wire=False, res=None):
    body.hide_render = not show_body
    sc.render.resolution_x, sc.render.resolution_y = res or (700, 900)
    cam.data.ortho_scale = scale
    a = math.radians(az); c = Vector(center)
    cam.location = c + Vector((math.sin(a) * 6, -math.cos(a) * 6, 0.2))
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for m in [x for x in boots.modifiers if x.type == 'WIREFRAME']:
        boots.modifiers.remove(m)
    if wire:
        md = boots.modifiers.new("w", 'WIREFRAME'); md.thickness = 0.0009; md.use_replace = True
    sc.render.filepath = os.path.join(out, name + ".png")
    bpy.ops.render.render(write_still=True)


for nm, az in (("frente", 0), ("3q", 35), ("costas", 180), ("lado", 90)):
    shot("b_" + nm, az, (0.0, 0.03, 0.27), 0.86, False)
for nm, az in (("frente", 0), ("3q", 35), ("costas", 180)):
    shot("m_" + nm, az, (0.0, 0.0, 0.62), 1.45, True)
shot("c_pe", 30, (0.19, -0.02, 0.12), 0.34, False)
shot("c_cano", 15, (0.17, 0.0, 0.38), 0.34, False)
shot("w_frente", 0, (0.0, 0.03, 0.27), 0.86, False, wire=True)
shot("w_3q", 40, (0.0, 0.03, 0.27), 0.86, False, wire=True)
shot("m_perto", 30, (0.0, 0.0, 0.3), 0.8, True)
print("BPREV ok", sum(len(p.vertices) - 2 for p in boots.data.polygons))
