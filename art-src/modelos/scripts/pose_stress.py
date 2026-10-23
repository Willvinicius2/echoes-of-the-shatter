"""Teste de pose extremo com metrica de esticamento de aresta (Blender -b): braco levantado (lateral 90 e 150 graus),
joelho dobrado (90) e torcao do tronco (Spine+Chest 25 + Neck 20 em Z). Uso: blender -b --factory-startup -P pose_stress.py -- <id>
O sinal de cada rotacao e escolhido pelo efeito (mao sobe, pe vai para tras). Grava work/pose_stress.json."""
import bpy, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
bpy.ops.wm.open_mainfile(filepath=fpath(cfg, cfg["asset"] + ".blend"))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
ob = next(o for o in bpy.data.objects if o.type == 'MESH')
rest = evaluated_coords(ob)
me = ob.data
e = np.empty(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get('vertices', e); e = e.reshape(-1, 2)
rl = np.maximum(np.linalg.norm(rest[e[:, 0]] - rest[e[:, 1]], axis=1), 1e-6)
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
def bone_tail_z(n): return (arm.matrix_world @ arm.pose.bones[n].tail)[2], (arm.matrix_world @ arm.pose.bones[n].tail)[1]
def metrics(name):
    pos = evaluated_coords(ob)
    r = np.linalg.norm(pos[e[:, 0]] - pos[e[:, 1]], axis=1) / rl
    return dict(pose=name, max=round(float(r.max()), 3), p99=round(float(np.percentile(r, 99)), 3), over_1_5=int((r > 1.5).sum()),
                over_2=int((r > 2).sum()), min=round(float(r.min()), 3))
out = []
def run(name, fn):
    clear_pose(arm); fn(); bpy.context.view_layer.update(); out.append(metrics(name)); clear_pose(arm)
def arm_up(deg):
    z0 = bone_tail_z("LeftHand")[0]
    for sgn in (1, -1):
        clear_pose(arm); rot_bone_world(arm, "LeftUpperArm", Y, sgn * deg); bpy.context.view_layer.update()
        if bone_tail_z("LeftHand")[0] > z0 + 0.1: return sgn
    return 1
def knee():
    y0 = bone_tail_z("RightFoot")[1]
    for sgn in (1, -1):
        clear_pose(arm); rot_bone_world(arm, "RightLowerLeg", X, sgn * 90); bpy.context.view_layer.update()
        if bone_tail_z("RightFoot")[1] > y0 + 0.1: return sgn
    return 1
s90 = arm_up(90); s150 = arm_up(150); sk = knee(); clear_pose(arm)
run("braco_lateral_90", lambda: rot_bone_world(arm, "LeftUpperArm", Y, s90 * 90))
run("braco_levantado_150", lambda: rot_bone_world(arm, "LeftUpperArm", Y, s150 * 150))
run("braco_levantado_150_cotovelo", lambda: (rot_bone_world(arm, "LeftUpperArm", Y, s150 * 150), rot_bone_world(arm, "LeftLowerArm", X, -60)))
run("joelho_90", lambda: (rot_bone_world(arm, "RightUpperLeg", X, -sk * 45), rot_bone_world(arm, "RightLowerLeg", X, sk * 90)))
run("torcao_tronco_55", lambda: (rot_bone_world(arm, "Spine", Z, 25), rot_bone_world(arm, "Chest", Z, 25), rot_bone_world(arm, "Neck", Z, 20)))
res = dict(poses=out, worst_max=max(o["max"] for o in out), worst_over_2=max(o["over_2"] for o in out), edges=int(len(rl)), sinais=dict(braco90=s90, braco150=s150, joelho=sk))
save_json(wpath(cfg, "pose_stress.json"), res); print("POSE", res)
