"""Ferramenta (Blender): importa um GLB e grava vistas ortograficas em Workbench + a caixa. Uso: blender -b -P tool_glb_preview.py -- <glb> <saida_sem_extensao>"""
import bpy, sys, math, numpy as np
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
glb, out = argv[0], argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
ob = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in ob:
    o.data.transform(o.matrix_world); o.matrix_world.identity()
v = np.concatenate([np.array([c.co[:] for c in o.data.vertices]) for o in ob])
lo, hi = v.min(0), v.max(0); ctr = (lo + hi) / 2
print("BBOX", lo.round(3), hi.round(3), "faces", sum(len(o.data.polygons) for o in ob))
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x = sc.render.resolution_y = 500
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'SINGLE'
cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.ortho_scale = float((hi - lo).max()) * 1.15
co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
for name, d, rot in (("front", (0, -1, 0), (math.pi / 2, 0, 0)), ("right", (-1, 0, 0), (math.pi / 2, 0, -math.pi / 2)), ("top", (0, 0, 1), (0, 0, 0))):
    co.location = Vector(ctr) + Vector(d) * 10; co.rotation_euler = rot
    sc.render.filepath = f"{out}_{name}.png"; bpy.ops.render.render(write_still=True)
