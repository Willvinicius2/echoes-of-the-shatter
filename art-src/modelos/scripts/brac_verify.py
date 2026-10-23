"""Verificacao das bracadeiras (SK_ArcherDark_Bracers.glb) montadas no corpo: orcamento, UV, esqueleto, pesos, afastamento da pele em repouso e
teste de pose (braco levantado, cotovelo dobrado, mao fechando) com metrica de esticamento de aresta e de penetracao no corpo.
Uso: blender -b --factory-startup -P brac_verify.py -- arq_dark_bracadeiras"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
cfg = load_cfg()
glb = f"{cfg['final_dir']}/{cfg['asset']}.glb"
body_glb = "D:/openclaude/_trabalho-claude/wt/arqueiro-dark-3d/godot/art/models/personagens/arqueiro_dark/ArcherDark_Body.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=body_glb)
bo = list(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=glb)
bro = [o for o in bpy.data.objects if o not in bo]
bmesh_o = next(o for o in bo if o.type == 'MESH' and "Body" in o.name)
brm = next(o for o in bro if o.type == 'MESH' and 'Bracers' in o.name)
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
barm = next(o for o in bro if o.type == 'ARMATURE'); bdarm = next(o for o in bo if o.type == 'ARMATURE')
R = {}
me = brm.data
R["tris"] = sum(len(p.vertices) - 2 for p in me.polygons)
R["materials"] = len(me.materials)
uvs = np.array([l.uv[:] for l in me.uv_layers[0].data])
R["uv_range"] = [round(float(uvs.min()), 3), round(float(uvs.max()), 3)]
R["uv_layers"] = len(me.uv_layers)
R["bones_bracers"] = len(barm.data.bones); R["bones_body"] = len(bdarm.data.bones)
R["same_bones"] = sorted(b.name for b in barm.data.bones) == sorted(b.name for b in bdarm.data.bones)
cnt, sums = [], []
for v in me.vertices:
    ws = [g.weight for g in v.groups if g.weight > 1e-6]
    cnt.append(len(ws)); sums.append(sum(ws))
R["skin"] = dict(max_influences=max(cnt), unweighted=cnt.count(0), wsum_min=round(min(sums), 4), wsum_max=round(max(sums), 4))
ima = [i for i in bpy.data.images if i.size[0] > 0]
R["textures"] = {i.name: list(i.size) for i in ima if "T_ArcherDark_Bracers" in i.name or "Bracers" in i.name}


def evaluated(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg); m = e.to_mesh()
    P = np.array([(ob.matrix_world @ v.co)[:] for v in m.vertices])
    tris = [tuple(p.vertices) for p in m.polygons if len(p.vertices) == 3]
    e.to_mesh_clear()
    return P


def body_bvh():
    dg = bpy.context.evaluated_depsgraph_get()
    e = bmesh_o.evaluated_get(dg); m = e.to_mesh()
    bm = bmesh.new(); bm.from_mesh(m); bm.transform(bmesh_o.matrix_world)
    t = BVHTree.FromBMesh(bm); bm.free(); e.to_mesh_clear()
    return t


E = np.empty(len(me.edges) * 2, np.int64); me.edges.foreach_get('vertices', E); E = E.reshape(-1, 2)
rest = evaluated(brm)
bv = body_bvh()


def clearance(P):
    out = []
    for p in P:
        loc, n, fi, d = bv.find_nearest(Vector(p))
        out.append(d if (loc is not None and n.dot(Vector(p) - loc) >= 0) else -d)
    return np.array(out)


c0 = clearance(rest)
low = np.where(c0 < 0.003)[0]
print("BVER low", [(i, rest[i].round(3).tolist(), round(float(c0[i]*1000),1)) for i in low[:12]], len(low))
print("BVER uvbad", [(i, uvs[i].round(4).tolist()) for i in np.where((uvs < 0).any(1) | (uvs > 1).any(1))[0][:6]])
R["rest_clearance_mm"] = dict(min=round(float(c0.min() * 1000), 2), p5=round(float(np.percentile(c0, 5) * 1000), 2),
                               median=round(float(np.median(c0) * 1000), 2), inside=int((c0 < 0).sum()))


def rot_world(arm, bname, axis, deg):
    pb = arm.pose.bones[bname]
    head = arm.matrix_world @ pb.head
    Rm = Matrix.Rotation(math.radians(deg), 4, axis)
    T = Matrix.Translation(head)
    pb.matrix = arm.matrix_world.inverted() @ (T @ Rm @ T.inverted()) @ arm.matrix_world @ pb.matrix
    bpy.context.view_layer.update()


def clear_pose():
    for a in (barm, bdarm):
        for pb in a.pose.bones:
            pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


POSES = {
    "braco_levantado": [("UpperArm", 'Y', -100)],
    "cotovelo_dobrado": [("LowerArm", 'X', -100)],
    "mao_fechando": [("Hand", 'X', -60), ("LowerArm", 'X', -40)],
    "tiro_com_arco": [("UpperArm", 'Y', -80), ("LowerArm", 'X', -30), ("Hand", 'X', -35)],
}
R["pose"] = {}
for name, steps in POSES.items():
    clear_pose()
    for a in (barm, bdarm):
        for side, sgn in (("Left", 1), ("Right", 1)):
            for part, ax, deg in steps:
                d = deg * (1 if side == "Left" else (-1 if ax == 'Y' else 1))
                rot_world(a, side + part, ax, d)
    P = evaluated(brm)
    r = np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1) / np.maximum(np.linalg.norm(rest[E[:, 0]] - rest[E[:, 1]], axis=1), 1e-6)
    bv = body_bvh()
    c = clearance(P)
    R["pose"][name] = dict(edge_stretch_max=round(float(r.max()), 3), edge_stretch_p99=round(float(np.percentile(r, 99)), 3),
                           edges_over_1_5=int((r > 1.5).sum()), mean_move_m=round(float(np.linalg.norm(P - rest, axis=1).mean()), 3),
                           verts_inside_body=int((c < 0).sum()), clearance_min_mm=round(float(c.min() * 1000), 2),
                           clearance_p5_mm=round(float(np.percentile(c, 5) * 1000), 2))
    print("BVER", name, R["pose"][name])
clear_pose()
ok = dict(tris_le_2000=R["tris"] <= 2000, one_material=R["materials"] == 1, uv_in_01=R["uv_range"][0] >= 0 and R["uv_range"][1] <= 1,
          one_uv=R["uv_layers"] == 1, bones_30=R["bones_bracers"] == 30, same_bones=R["same_bones"], influences_le_4=R["skin"]["max_influences"] <= 4,
          all_weighted=R["skin"]["unweighted"] == 0, rest_no_penetration=R["rest_clearance_mm"]["inside"] == 0,
          rest_offset_ge_3mm=R["rest_clearance_mm"]["min"] >= 3.0,
          poses_move=all(v["mean_move_m"] > 0.02 for v in R["pose"].values()))
R["checks"] = {k: bool(v) for k, v in ok.items()}; R["all_ok"] = all(ok.values())
save_json(f"{cfg['final_dir']}/verify_report.json", R)
print("BVER", R["tris"], R["rest_clearance_mm"], R["skin"], R["checks"])
print("BVER", "OK" if R["all_ok"] else "FALHOU")
