"""Previa rapida de geometria (workbench): blender -b -P brac_geoprev.py -- <blend com objeto game> <saida_prefixo> [corpo 0/1]"""
import bpy, sys, math, os
from mathutils import Vector
blend, outp = sys.argv[sys.argv.index("--") + 1:][:2]
withbody = (sys.argv[sys.argv.index("--") + 3:] or ["1"])[0] == "1"
bpy.ops.wm.open_mainfile(filepath="D:/openclaude/_trabalho-claude/modelos3d/arqueiro_dark/corpo/work/game_uv.blend")
bpy.data.objects["game"].name = "body_ref"
bpy.data.objects["Rig_Humanoid_Chibi"].hide_render = True
if not withbody: bpy.data.objects["body_ref"].hide_render = True
with bpy.data.libraries.load(blend) as (src, dst):
    dst.objects = [n for n in src.objects if n == "game"]
for o in dst.objects:
    o.parent = None
    for m_ in list(o.modifiers): o.modifiers.remove(m_)
    bpy.context.scene.collection.objects.link(o)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x = 520; sc.render.resolution_y = 520
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'OBJECT'; sc.display.shading.show_cavity = True
bpy.data.objects["body_ref"].color = (0.9, 0.7, 0.6, 1); dst.objects[0].color = (0.35, 0.25, 0.2, 1)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.type = 'ORTHO'; CX, CZ, SC = [float(x) for x in os.environ.get('BCAM', '0.36,0.92,0.62').split(',')]
SX = float(os.environ.get('BSX', '1'))
cam.data.ortho_scale = SC
for n, (az, el, _) in {"f": (0, 0, 0), "s": (90, 0, 0.36), "b": (180, 0, 0.36), "i": (270, 0, 0.36), "t": (0, 80, 0.36)}.items():
    a = math.radians(az); c = Vector((CX * SX, 0, CZ))
    cam.location = c + Vector((math.sin(a) * 3 * math.cos(math.radians(el)), -math.cos(a) * 3 * math.cos(math.radians(el)), 3 * math.sin(math.radians(el))))
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{outp}_{n}.png"; bpy.ops.render.render(write_still=True)
