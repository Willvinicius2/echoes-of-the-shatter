"""Teste de pose das botas com metrica de esticamento de aresta (Blender -b): joelho dobrado (90), passo (uma coxa a frente, outra atras),
ponta do pe para cima e para baixo, agachamento (joelhos 70 + coxas 50). Sinal de cada rotacao escolhido pelo efeito (pe vai para tras, pe sobe).
Uso: blender -b --factory-startup -P botas_pose.py -- arq_dark_botas. Grava work/pose_stress.json."""
import bpy, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
cfg = load_cfg()
bpy.ops.wm.open_mainfile(filepath=fpath(cfg, cfg["asset"] + ".blend"))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
ob = next(o for o in bpy.data.objects if o.type == 'MESH')
rest = evaluated_coords(ob)
me = ob.data
e = np.empty(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get('vertices', e); e = e.reshape(-1, 2)
rl = np.maximum(np.linalg.norm(rest[e[:, 0]] - rest[e[:, 1]], axis=1), 1e-6)
X = (1, 0, 0)
tail = lambda n: arm.matrix_world @ arm.pose.bones[n].tail


def metrics(name):
    pos = evaluated_coords(ob)
    r = np.linalg.norm(pos[e[:, 0]] - pos[e[:, 1]], axis=1) / rl
    return dict(pose=name, max=round(float(r.max()), 3), p99=round(float(np.percentile(r, 99)), 3), over_1_5=int((r > 1.5).sum()),
                over_2=int((r > 2).sum()), min=round(float(r.min()), 3))


out = []


def run(name, fn):
    clear_pose(arm); fn(); bpy.context.view_layer.update(); out.append(metrics(name)); clear_pose(arm)


def sign_for(bone, ref_bone, axis_fn):
    y0 = axis_fn(tail(ref_bone))
    for sgn in (1, -1):
        clear_pose(arm); rot_bone_world(arm, bone, X, sgn * 40); bpy.context.view_layer.update()
        if abs(axis_fn(tail(ref_bone)) - y0) > 0.05:
            return sgn, axis_fn(tail(ref_bone)) - y0
    return 1, 0


# +rot X do osso "gira para frente" (-Y) quando a cauda do pe vai a -Y
sk, d = sign_for("RightUpperLeg", "RightFoot", lambda v: v.y)
clear_pose(arm)
sf = sk if d < 0 else -sk          # sinal que leva o pe para a frente (-Y)
knee = -sf                          # joelho dobra o pe para tras
run("joelho_90", lambda: (rot_bone_world(arm, "RightUpperLeg", X, sf * 40), rot_bone_world(arm, "RightLowerLeg", X, knee * 90)))
run("passo", lambda: (rot_bone_world(arm, "LeftUpperLeg", X, sf * 30), rot_bone_world(arm, "RightUpperLeg", X, -sf * 25),
                      rot_bone_world(arm, "RightLowerLeg", X, knee * 20)))
run("ponta_pe_cima_35", lambda: (rot_bone_world(arm, "LeftFoot", X, 35), rot_bone_world(arm, "LeftToes", X, 15)))
run("ponta_pe_baixo_40", lambda: (rot_bone_world(arm, "LeftFoot", X, -40), rot_bone_world(arm, "LeftToes", X, -20)))
run("agachamento", lambda: [(rot_bone_world(arm, s + "UpperLeg", X, sf * 55), rot_bone_world(arm, s + "LowerLeg", X, knee * 80),
                             rot_bone_world(arm, s + "Foot", X, sf * 20)) for s in ("Left", "Right")])
res = dict(poses=out, worst_max=max(o["max"] for o in out), worst_over_2=max(o["over_2"] for o in out), edges=int(len(rl)),
           sinais=dict(perna_frente=sf, joelho=knee))
save_json(wpath(cfg, "pose_stress.json"), res); print("POSE", res)
