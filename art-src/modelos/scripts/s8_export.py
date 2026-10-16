"""Etapa 8 (Blender): material, teste de pose, .blend final e FBX com o preset do projeto.

1 material (M_<Heroi>: albedo pintado, sem normal map), malha nomeada cfg["mesh_name"], Armature modifier,
teste de pose (bracos para baixo, cabeca virada, passo) com metricas de esticamento de aresta, e exportacao
SK_<...>.fbx pelo gb_rig.export_fbx_rigged (preset docs/04 secao 17.1). Grava final/<asset>.blend,
final/<asset>.fbx e work/export_report.json.
"""
import bpy, numpy as np, sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *

cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
bpy.ops.wm.open_mainfile(filepath=wpath(cfg, "game_uv.blend"))
ob = bpy.data.objects["game"]
ob.name = cfg.get("mesh_name", cfg["asset"] + "_Body"); ob.data.name = ob.name
tex = cfg["asset"][3:]

# material unico
mat = bpy.data.materials.new("M_" + tex)
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
img = bpy.data.images.load(fpath(cfg, f"T_{tex}_BC.png"))
img.colorspace_settings.name = 'sRGB'
node = nt.nodes.new('ShaderNodeTexImage'); node.image = img
nt.links.new(node.outputs['Color'], bsdf.inputs['Base Color'])
bsdf.inputs['Roughness'].default_value = 1.0
ob.data.materials.clear(); ob.data.materials.append(mat)

# teste de pose (so com esqueleto)
pose = None
arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if arm is not None:
    rest = evaluated_coords(ob)
    test_pose(arm, cfg["kind"])
    pos = evaluated_coords(ob)
    me = ob.data
    e = np.empty(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get('vertices', e); e = e.reshape(-1, 2)
    r = np.linalg.norm(pos[e[:, 0]] - pos[e[:, 1]], axis=1) / np.maximum(np.linalg.norm(rest[e[:, 0]] - rest[e[:, 1]], axis=1), 1e-6)
    pose = dict(edge_stretch_max=round(float(r.max()), 3), edge_stretch_p99=round(float(np.percentile(r, 99)), 3),
                edges_over_1_5=int((r > 1.5).sum()), edges_over_2=int((r > 2).sum()), edges=int(len(r)),
                note="1 = sem esticar; aresta acima de 2 = possivel rasgo")
    save_json(wpath(cfg, "pose_report.json"), pose)
    clear_pose(arm)
me = ob.data

# FBX
for o in bpy.context.scene.objects:
    o.select_set(False)
fbx = fpath(cfg, cfg["asset"] + ".fbx")
(gb_rig.export_fbx_rigged(arm, [ob], fbx) if arm is not None else gb_lib.export_fbx([ob], fbx))
bpy.ops.wm.save_as_mainfile(filepath=fpath(cfg, cfg["asset"] + ".blend"), compress=True)
save_json(wpath(cfg, "export_report.json"), dict(fbx=fbx, pose=pose, tris=len(me.polygons)))
print("S8", pose, len(me.polygons))
