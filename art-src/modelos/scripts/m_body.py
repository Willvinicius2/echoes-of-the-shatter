"""Modular (Blender): reposiciona o corpo base (SK_<Heroi>_Body) sobre o esqueleto do heroi vestido e o parte em 6 regioes.

Para cada osso deformante, mapeia o osso do corpo base para o osso do heroi vestido (translacao, rotacao e escala pelo
comprimento do osso) e deforma a malha pelos proprios pesos (LBS): o corpo e ajustado ao SK_<Heroi>, e nao o contrario, e
usa o mesmo Rig_Humanoid_Chibi. Regioes pelas mesmas regras das pecas (osso dominante e planos de cintura e bota):
Head (cabeca e pescoco), Torso, Arms (ate o cotovelo), Hands (antebraco e mao), Legs (cintura ao cano da bota), Feet.
Grava work/modular_body.blend (6 regioes + esqueleto do heroi).
"""
import bpy, bmesh, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mathutils import Vector, Matrix

cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
bpy.ops.wm.open_mainfile(filepath=cfg["body_mesh_src"])      # game_uv.blend: malha do corpo com UV, pesos e esqueleto do corpo
body = bpy.data.objects["game"]
arm_b = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm_b.name = "Rig_body_src"
with bpy.data.libraries.load(wpath(cfg, "modular_work.blend")) as (src, dst):
    dst.objects = [gb_rig.RIG_NAME]
arm_w = dst.objects[0]
bpy.context.scene.collection.objects.link(arm_w)
arm_w.name = gb_rig.RIG_NAME
CUT = cfg["cuts"]
gname = {vg.index: vg.name for vg in body.vertex_groups}
bones_b = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm_b.data.bones if b.use_deform}
bones_w = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm_w.data.bones if b.use_deform}
M = {}
for n, (hb, tb) in bones_b.items():
    hw, tw = bones_w[n]
    a, b = (tb - hb), (tw - hw)
    s = min(max(b.length / max(a.length, 1e-6), 0.6), 1.6)
    q = a.rotation_difference(b)
    M[n] = (hb, hw, s, q.to_matrix())
me = body.data
co = [v.co.copy() for v in me.vertices]
newco = []
for v in me.vertices:
    p = Vector((0, 0, 0)); wsum = 0.0
    for g in v.groups:
        n = gname[g.group]
        if n not in M:
            continue
        hb, hw, s, R = M[n]
        p += (hw + R @ ((co[v.index] - hb) * s)) * g.weight; wsum += g.weight
    newco.append(p / wsum if wsum > 0 else co[v.index])
for v, c in zip(me.vertices, newco):
    v.co = c
me.update()
# re-parent ao esqueleto do heroi
body.parent = arm_w
for m in list(body.modifiers):
    body.modifiers.remove(m)
mod = body.modifiers.new("Armature", 'ARMATURE'); mod.object = arm_w
bpy.data.objects.remove(arm_b)
body.matrix_parent_inverse = Matrix.Identity(4)
# regioes
TORSO_LEGS = {"Chest", "Spine", "Hips", "LeftUpperLeg", "RightUpperLeg", "LeftLowerLeg", "RightLowerLeg"}
def vregion(v):
    g = max(v.groups, key=lambda g: g.weight); n = gname[g.group]; z = v.co.z
    if n in ("Head", "Neck"):
        return "Head"
    if n.endswith("LowerArm") or n.endswith("Hand"):
        return "Hands"
    if n.endswith("UpperArm"):
        return "Arms"
    if n.endswith("Foot") or n.endswith("Toes"):
        return "Feet"
    if n in TORSO_LEGS and "Leg" in n and z < CUT["boot_z"]:
        return "Feet"
    if n in TORSO_LEGS or n.endswith("Shoulder"):
        return "Torso" if z >= CUT["waist_z"] else "Legs"
    return "Torso"
R6 = ["Head", "Torso", "Arms", "Hands", "Legs", "Feet"]
vl = [R6.index(vregion(v)) for v in me.vertices]
fl = np.array([np.bincount([vl[i] for i in p.vertices], minlength=6).argmax() for p in me.polygons])
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
nbr = [[g.index for e in f.edges for g in e.link_faces if g.index != f.index] for f in bm.faces]
bm.free()
for _ in range(2):
    new = fl.copy()
    for i in range(len(fl)):
        c = np.bincount([fl[j] for j in nbr[i]] + [fl[i]], minlength=6)
        if c.argmax() != fl[i] and c.max() >= 3:
            new[i] = c.argmax()
    fl = new
mat = bpy.data.materials.new(f"M_{cfg['hero']}_Body"); mat.use_nodes = True
img = bpy.data.images.load(f"{cfg['body_tex_dir']}/T_{cfg['hero']}_Body_BC.png")
tn = mat.node_tree.nodes.new('ShaderNodeTexImage'); tn.image = img
mat.node_tree.links.new(tn.outputs['Color'], mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 1.0
rep = {}
for i, rn in enumerate(R6):
    o2 = body.copy(); o2.data = body.data.copy(); o2.name = f"Body_{rn}"; o2.data.name = f"Body_{rn}"
    bpy.context.scene.collection.objects.link(o2)
    bm = bmesh.new(); bm.from_mesh(o2.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if fl[f.index] != i], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(o2.data); bm.free()
    o2.data.materials.clear(); o2.data.materials.append(mat)
    rep[rn] = len(o2.data.polygons)
bpy.data.objects.remove(body)
bb = [o for o in bpy.data.objects if o.name.startswith("Body_")]
allv = np.concatenate([[ (o.matrix_world @ v.co)[:] for v in o.data.vertices] for o in bb])
rep["bbox_min"] = allv.min(0).round(3).tolist(); rep["bbox_max"] = allv.max(0).round(3).tolist()
bpy.ops.wm.save_as_mainfile(filepath=wpath(cfg, "modular_body.blend"), compress=True)
save_json(wpath(cfg, "body_report.json"), rep)
print("MBODY", rep)
