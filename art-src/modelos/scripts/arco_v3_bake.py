"""Arco v3, etapa 2 (Blender -b, CPU): UV (smart project, 2048), bake de normal map (high2 -> low) e AO (Cycles CPU),
e grava low_uv.npz (posicao, normal, uv por canto) para a pintura. Uso: blender -b -P arco_v3_bake.py -- [tex]"""
import bpy, sys, os, math, numpy as np
a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEX = int(a[0]) if a else 2048
W2 = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\arco\work3"
bpy.ops.wm.read_factory_settings(use_empty=True)
def load(p, name):
    bpy.ops.wm.ply_import(filepath=p); o = bpy.context.selected_objects[0]; o.name = name; return o
low = load(os.path.join(W2, "low3.ply"), "low"); high = load(os.path.join(W2, "high3.ply"), "high")
for o in (low, high):
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.shade_smooth()
bpy.context.view_layer.objects.active = low
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.6)
bpy.ops.uv.pack_islands(margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
UVS = 0.86   # v3: a faixa v>0.87 do atlas fica para as duas laminas
for u in low.data.uv_layers.active.data: u.uv = (u.uv[0] * UVS, u.uv[1] * UVS)
low.data.set_sharp_from_angle(angle=math.radians(50)) if hasattr(low.data, "set_sharp_from_angle") else None
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.use_denoising = False
mat = bpy.data.materials.new("m"); mat.use_nodes = True; low.data.materials.append(mat)
def bake(kind, name, samples, **kw):
    img = bpy.data.images.new(name, TEX, TEX, alpha=False, float_buffer=False)
    if kind == 'NORMAL': img.colorspace_settings.name = 'Non-Color'
    n = mat.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img; mat.node_tree.nodes.active = n
    sc.cycles.samples = samples
    bpy.ops.object.select_all(action='DESELECT')
    if kw.get("sel"): high.select_set(True)
    low.select_set(True); bpy.context.view_layer.objects.active = low
    bpy.ops.object.bake(type=kind, margin=12, margin_type='EXTEND', use_selected_to_active=bool(kw.get("sel")),
                        cage_extrusion=0.012, max_ray_distance=0.04, normal_space='TANGENT')
    img.filepath_raw = os.path.join(W2, name + ".png"); img.file_format = 'PNG'; img.save()
    mat.node_tree.nodes.remove(n); print("BAKED", name)
bake('NORMAL', "bake_normal", 4, sel=True)
bake('AO', "bake_ao", 32)
bpy.ops.object.select_all(action="DESELECT"); high.select_set(True); bpy.ops.object.delete()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(W2, "low_uv.blend"))
# geometria por canto para a pintura
me = low.data; me.calc_loop_triangles()
uv = me.uv_layers.active.data
P = np.array([v.co[:] for v in me.vertices]); Nn = np.array([l.normal[:] for l in me.loops])
tri = np.array([t.loops[:] for t in me.loop_triangles]); lv = np.array([l.vertex_index for l in me.loops])
UV = np.array([u.uv[:] for u in uv])
np.savez(os.path.join(W2, "low_uv.npz"), P=P, N=Nn, tri=tri, lv=lv, UV=UV)
print("TRIS", len(tri), "islands n/a")
