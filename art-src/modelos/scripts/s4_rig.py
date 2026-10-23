"""Etapa 4 (Blender): ajusta o Rig_Humanoid_Chibi a malha por marcos e calcula os pesos automaticos.

Os marcos (cfg["markers"], em metros, espaco do Blender, lado ESQUERDO do personagem = +X, frente -Y) fixam as
juntas; os ossos mantem os nomes e a hierarquia do esqueleto compartilhado (gb_rig). Pesos: automaticos por calor
do Blender, limitados a 4 influencias por vertice e normalizados; vertice sem peso recebe o osso mais proximo.
Grava work/game_rig.blend, work/rig_report.json e prévias de conferencia dos ossos (work/rig_overlay_*.png).
"""
import bpy, bmesh, math, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mathutils import Vector

cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
bpy.ops.wm.open_mainfile(filepath=wpath(cfg, "game.blend"))
ob = bpy.data.objects["game"]
if cfg["kind"] == "static":          # arma: malha estatica, sem esqueleto
    bpy.ops.wm.save_as_mainfile(filepath=wpath(cfg, "game_rig.blend"), compress=True)
    print("S4 static: sem esqueleto")
    raise SystemExit(0)
# modo por peca: o esqueleto e ajustado uma vez ao corpo base; as pecas apontam para o mesmo json de marcos
markers = load_json(cfg["markers_from"])["markers"] if cfg.get("markers_from") else cfg["markers"]
M = {k: Vector(v) for k, v in markers.items()}


def mir(v):
    return Vector((-v.x, v.y, v.z))


def bone_defs_quad():
    """Quadrupede simples (~22 ossos, sem Humanoid): root, Pelvis, Spine, Chest, Neck, Head, Tail1-3, 4 pernas de 3 ossos."""
    B = []
    add = lambda n, p, h, t, d=True: B.append((n, p, tuple(h), tuple(t), d))
    add("root", None, (0, 0, 0), (0, 0, 0.1), False)
    add("Pelvis", "root", M["pelvis"], M["spine"])
    add("Spine", "Pelvis", M["spine"], M["chest"])
    add("Chest", "Spine", M["chest"], M["neck"])
    add("Neck", "Chest", M["neck"], M["head"])
    add("Head", "Neck", M["head"], M["head_tip"])
    add("Tail1", "Pelvis", M["tail0"], M["tail1"])
    add("Tail2", "Tail1", M["tail1"], M["tail2"])
    add("Tail3", "Tail2", M["tail2"], M["tail_tip"])
    for side, f in (("Left", lambda v: v), ("Right", mir)):
        add(f"{side}FrontUpperLeg", "Chest", f(M["f_shoulder"]), f(M["f_elbow"]))
        add(f"{side}FrontLowerLeg", f"{side}FrontUpperLeg", f(M["f_elbow"]), f(M["f_paw"]))
        add(f"{side}FrontPaw", f"{side}FrontLowerLeg", f(M["f_paw"]), f(M["f_toe"]))
        add(f"{side}HindUpperLeg", "Pelvis", f(M["h_hip"]), f(M["h_knee"]))
        add(f"{side}HindLowerLeg", f"{side}HindUpperLeg", f(M["h_knee"]), f(M["h_paw"]))
        add(f"{side}HindPaw", f"{side}HindLowerLeg", f(M["h_paw"]), f(M["h_toe"]))
    add("socket_fx_ground", "root", (0, 0, 0), (0, -0.10, 0), False)
    return B


def bone_defs():
    """(nome, pai, cabeca, cauda, deforma) em espaco do Blender; esquerda = +X."""
    B = []
    add = lambda n, p, h, t, d=True: B.append((n, p, tuple(h), tuple(t), d))
    add("root", None, (0, 0, 0), (0, 0, 0.15), False)
    add("Hips", "root", M["hips"], M["spine"])
    add("Spine", "Hips", M["spine"], M["chest"])
    add("Chest", "Spine", M["chest"], M["neck"])
    add("Neck", "Chest", M["neck"], M["head"])
    add("Head", "Neck", M["head"], M["head_top"])
    for side, f in (("Left", lambda v: v), ("Right", mir)):
        add(f"{side}Shoulder", "Chest", f(M["shoulder"]), f(M["upperarm"]))
        add(f"{side}UpperArm", f"{side}Shoulder", f(M["upperarm"]), f(M["lowerarm"]))
        add(f"{side}LowerArm", f"{side}UpperArm", f(M["lowerarm"]), f(M["hand"]))
        add(f"{side}Hand", f"{side}LowerArm", f(M["hand"]), f(M["hand_tip"]))
        add(f"{side}UpperLeg", "Hips", f(M["upperleg"]), f(M["lowerleg"]))
        add(f"{side}LowerLeg", f"{side}UpperLeg", f(M["lowerleg"]), f(M["foot"]))
        add(f"{side}Foot", f"{side}LowerLeg", f(M["foot"]), f(M["toes"]))
        add(f"{side}Toes", f"{side}Foot", f(M["toes"]), f(M["toe_tip"]))
    hr, hl = mir(M["hand"]), M["hand"]
    add("socket_weapon_r", "RightHand", hr, hr + Vector((0, -0.05, 0)), False)
    add("socket_weapon_l", "LeftHand", hl, hl + Vector((0, -0.05, 0)), False)
    add("socket_cast", "RightHand", hr + Vector((0, -0.15, 0.07)), hr + Vector((0, -0.20, 0.07)), False)
    add("socket_head", "Head", M["head_top"], M["head_top"] + Vector((0, 0, 0.05)), False)
    add("socket_fx_ground", "root", (0, 0, 0), (0, -0.10, 0), False)
    return B


if cfg["kind"] == "quadruped":
    gb_rig.bone_defs = bone_defs_quad
else:
    _full = bone_defs
    def _no_legs():
        d = _full()
        if not cfg.get("no_legs"):
            return d
        drop = {"UpperLeg", "LowerLeg", "Foot", "Toes"}
        return [b for b in d if not any(b[0].endswith(x) for x in drop)]
    gb_rig.bone_defs = _no_legs
coll = bpy.context.scene.collection
arm = gb_rig.make_armature(coll, turn=False)
rig_name = "Rig_Quadruped_Simple" if cfg["kind"] == "quadruped" else gb_rig.RIG_NAME
arm.name = rig_name
arm.data.name = rig_name

# pesos
if cfg.get("modular_role") == "piece":
    # peca modular: "shrinkwrap" leve (vertice dentro do corpo ou rente a ele sai para fora) e pesos copiados da superficie
    # mais proxima do corpo base (mesmo esqueleto, mesma deformacao: a peca acompanha o corpo sem rasgar nem atravessar)
    from mathutils.bvhtree import BVHTree
    from mathutils import interpolate
    ref = cfg["body_rig_blend"]
    with bpy.data.libraries.load(ref) as (src, dst):
        dst.objects = ["game"]
    body = dst.objects[0]
    bpy.context.scene.collection.objects.link(body)
    bg = [vg.name for vg in body.vertex_groups]
    bw = np.zeros((len(body.data.vertices), len(bg)))
    for v in body.data.vertices:
        for g in v.groups:
            bw[v.index, g.group] = g.weight
    bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    K = cfg["size_scale"]
    off = cfg.get("shrink_offset", 0.004) * K
    near = cfg.get("shrink_range", 0.03) * K
    moved = 0
    me = ob.data
    for v in me.vertices:
        loc, nrm, fi, d = bvh.find_nearest(v.co)
        if loc is None:
            continue
        if (v.co - loc).dot(nrm) < off and d < near:
            v.co = loc + nrm * off; moved += 1
    me.update()
    ob.vertex_groups.clear()
    for n in bg:
        ob.vertex_groups.new(name=n)
    W = np.zeros((len(me.vertices), len(bg)))
    for v in me.vertices:
        loc, nrm, fi, d = bvh.find_nearest(v.co)
        poly = body.data.polygons[fi]
        vs = [body.data.vertices[i] for i in poly.vertices]
        wts = interpolate.poly_3d_calc([x.co for x in vs], loc)
        for x, w in zip(vs, wts):
            W[v.index] += bw[x.index] * w
    for i in range(len(me.vertices)):
        idx = np.argsort(-W[i])[:4]
        t = W[i, idx].sum()
        for j in idx:
            if W[i, j] > 1e-4:
                ob.vertex_groups[j].add([i], float(W[i, j] / t), 'REPLACE')
    bpy.data.objects.remove(body)
    ob.parent = arm
    m_ = ob.modifiers.new("Armature", 'ARMATURE'); m_.object = arm
    shrink_moved = moved
else:
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    shrink_moved = 0
deform = {b.name for b in arm.data.bones if b.use_deform}
for vg in list(ob.vertex_groups):
    if vg.name not in deform:
        ob.vertex_groups.remove(vg)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
if cfg.get("weight_smooth"):      # suaviza o calor automatico no grafo de arestas (axila/ombro/virilha esticavam em pose extrema)
    _me = ob.data; _n = len(_me.vertices); _names = [vg.name for vg in ob.vertex_groups]
    _W = np.zeros((_n, len(_names)))
    for _v in _me.vertices:
        for _g in _v.groups:
            _W[_v.index, _g.group] = _g.weight
    _e = np.empty(len(_me.edges) * 2, dtype=np.int64); _me.edges.foreach_get('vertices', _e); _e = _e.reshape(-1, 2)
    _f = cfg.get("weight_smooth_factor", 0.5)
    for _ in range(cfg["weight_smooth"]):
        _acc = np.zeros_like(_W); _cnt = np.zeros(_n)
        np.add.at(_acc, _e[:, 0], _W[_e[:, 1]]); np.add.at(_acc, _e[:, 1], _W[_e[:, 0]])
        np.add.at(_cnt, _e[:, 0], 1); np.add.at(_cnt, _e[:, 1], 1)
        _W = (1 - _f) * _W + _f * _acc / np.maximum(_cnt, 1)[:, None]
    for _v in range(_n):
        for _j in np.where(_W[_v] > 1e-4)[0]:
            ob.vertex_groups[_j].add([_v], float(_W[_v, _j]), 'REPLACE')
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)

# vertices sem peso: osso deformante mais proximo (distancia ate o segmento)
me = ob.data
segs = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones if b.use_deform}
def dist_seg(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length
unw = 0
for v in me.vertices:
    if not any(g.weight > 1e-6 for g in v.groups):
        unw += 1
        n = min(segs, key=lambda k: dist_seg(v.co, *segs[k]))
        (ob.vertex_groups.get(n) or ob.vertex_groups.new(name=n)).add([v.index], 1.0, 'REPLACE')
for n in deform:
    if n not in ob.vertex_groups:
        ob.vertex_groups.new(name=n)

# relatorio de pesos
maxinf, counts = 0, []
for v in me.vertices:
    c = sum(1 for g in v.groups if g.weight > 1e-6)
    counts.append(c); maxinf = max(maxinf, c)
dom = {}
for v in me.vertices:
    g = max(v.groups, key=lambda g: g.weight)
    n = ob.vertex_groups[g.group].name
    dom[n] = dom.get(n, 0) + 1
rep = dict(shrinkwrap_vertices_moved=shrink_moved, bones=len(arm.data.bones), deform_bones=len(deform), max_influences=maxinf, unweighted_fixed=unw,
           dominant_bone_vertices=dom, humanoid=(gb_rig.humanoid_check([b.name for b in arm.data.bones]) if cfg["kind"] == "humanoid" else None))
save_json(wpath(cfg, "rig_report.json"), rep)
bpy.ops.wm.save_as_mainfile(filepath=wpath(cfg, "game_rig.blend"), compress=True)
print("S4", rep)
