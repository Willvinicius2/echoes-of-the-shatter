"""Etapa 5 (Blender): UV (tex_size) da malha de jogo, ilhas por regiao do corpo e direcao da normal.

Regiao = osso dominante de cada vertice (cabeca, torso com ombros, braco, mao, perna, pe; esquerda e direita).
Dentro da regiao as faces se agrupam pelo eixo mais proximo da normal (+-X, +-Y, +-Z), com filtro de maioria e
fusao dos grupos pequenos. As fronteiras viram costuras, cada ilha e aberta com o desdobramento do Blender
(angular, com queda para conforme), a escala e normalizada pela area 3D, rosto e maos ganham texel e o
empacotamento concavo preenche o 1024. Grava work/game_uv.blend, work/uv_report.json e work/uv_layout.png.
"""
import bpy, bmesh, math, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mathutils import Vector

cfg = load_cfg()
bpy.ops.wm.open_mainfile(filepath=wpath(cfg, "game_rig.blend"))
ob = bpy.data.objects["game"]
me = ob.data
TS = cfg["tex_size"]

REGION = {"Head": "head", "Neck": "head", "Hips": "torso", "Spine": "torso", "Chest": "torso",
          "LeftShoulder": "torso", "RightShoulder": "torso",
          "LeftUpperArm": "armL", "LeftLowerArm": "armL", "LeftHand": "handL",
          "RightUpperArm": "armR", "RightLowerArm": "armR", "RightHand": "handR",
          "LeftUpperLeg": "legL", "LeftLowerLeg": "legL", "LeftFoot": "footL", "LeftToes": "footL",
          "RightUpperLeg": "legR", "RightLowerLeg": "legR", "RightFoot": "footR", "RightToes": "footR"}
def quad_region(n):
    if n in ("Head", "Neck"):
        return "head"
    if n.startswith("Tail"):
        return "tail"
    if "Leg" in n or "Paw" in n:
        return n.replace("UpperLeg", "").replace("LowerLeg", "").replace("Paw", "")    # LeftFront, RightHind...
    return "torso"


if cfg["kind"] == "static":
    REGION = None
    regions = ["all"]
    vreg = np.zeros(len(me.vertices), int)
else:
    if cfg["kind"] == "quadruped":
        REGION = {vg.name: quad_region(vg.name) for vg in ob.vertex_groups}
    regions = sorted(set(REGION.values()))
    vreg = []
    for v in me.vertices:
        g = max(v.groups, key=lambda g: g.weight)
        vreg.append(regions.index(REGION[ob.vertex_groups[g.group].name]))
    vreg = np.array(vreg)

bm = bmesh.new(); bm.from_mesh(me)
bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
nf = len(bm.faces)
AX = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
fn = np.array([f.normal[:] for f in bm.faces]); fa = np.array([f.calc_area() for f in bm.faces])
freg = np.array([np.bincount(vreg[[v.index for v in f.verts]]).argmax() for f in bm.faces])
fax = (fn @ AX.T).argmax(1)
adj = [[g.index for e in f.edges for g in e.link_faces if g.index != f.index] for f in bm.faces]

# filtro de maioria: so troca de eixo dentro da mesma regiao
for _ in range(cfg.get("uv_majority_iter", 6)):
    new = fax.copy()
    for i in range(nf):
        score = {fax[i]: 1.5 * fa[i]}
        for j in adj[i]:
            if freg[j] == freg[i]:
                score[fax[j]] = score.get(fax[j], 0) + fa[j]
        new[i] = max(score, key=score.get)
    fax = new
label = freg * 6 + fax


def components(label):
    comp = -np.ones(nf, int); n = 0
    for s in range(nf):
        if comp[s] >= 0:
            continue
        st = [s]; comp[s] = n
        while st:
            x = st.pop()
            for j in adj[x]:
                if comp[j] < 0 and label[j] == label[s]:
                    comp[j] = n; st.append(j)
        n += 1
    return comp, n


comp, n = components(label)
# funde componentes pequenos no vizinho (mesma regiao se houver) de maior fronteira
min_faces = cfg.get("uv_min_island_faces", 14)
for _ in range(8):
    size = np.bincount(comp, minlength=n)
    small = [c for c in range(n) if size[c] < min_faces]
    if not small:
        break
    changed = False
    for c in small:
        members = np.where(comp == c)[0]
        border = {}
        for i in members:
            for j in adj[i]:
                if comp[j] != c:
                    border[comp[j]] = border.get(comp[j], 0) + 1
        if not border:
            continue
        same = {k: w for k, w in border.items() if freg[np.where(comp == k)[0][0]] == freg[members[0]]}
        tgt = max(same or border, key=(same or border).get)
        comp[members] = tgt; changed = True
    comp_new, n = components(comp * 1000 + 0)   # recompacta (componentes continuam conexos)
    comp = comp_new
    # rotulo = componente atual
    label = comp.copy()
    if not changed:
        break
comp, n = components(label)

# costuras nas fronteiras entre ilhas; desdobra; ilhas com triangulos invertidos sao divididas e desdobradas de novo
face_normal_y = fn[:, 1]
bm.free()
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
bpy.context.view_layer.objects.active = ob
if not me.uv_layers:
    me.uv_layers.new(name="UVMap")
polys = [p.loop_indices[:] for p in me.polygons]


def mark_seams():
    bm = bmesh.new(); bm.from_mesh(me)
    bm.edges.ensure_lookup_table()
    k = 0
    for e in bm.edges:
        s_ = bool(len(e.link_faces) == 2 and comp[e.link_faces[0].index] != comp[e.link_faces[1].index])
        e.seam = s_; k += s_
    bm.to_mesh(me); bm.free()
    return k


def unwrap():
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', fill_holes=True, correct_aspect=True, margin=0.0)
    bpy.ops.object.mode_set(mode='OBJECT')


def flipped_faces():
    uvt, _ = uv_triangles(ob)
    a2 = (uvt[:, 1, 0] - uvt[:, 0, 0]) * (uvt[:, 2, 1] - uvt[:, 0, 1]) - (uvt[:, 2, 0] - uvt[:, 0, 0]) * (uvt[:, 1, 1] - uvt[:, 0, 1])
    fl = np.zeros(nf, bool)
    for c in range(n):
        fs = np.where(comp == c)[0]
        maj = np.sign((a2[fs] * fa[fs]).sum()) or 1
        fl[fs] = np.sign(a2[fs]) != maj
    return fl


seams = mark_seams()
unwrap()
for it in range(cfg.get("uv_flip_iter", 4)):
    fl = flipped_faces()
    if not fl.any():
        break
    seen = np.zeros(nf, bool)
    for s0 in np.where(fl)[0]:
        if seen[s0]:
            continue
        st = [s0]; seen[s0] = True; grp = []
        while st:
            x = st.pop(); grp.append(x)
            for j in adj[x]:
                if fl[j] and not seen[j] and comp[j] == comp[s0]:
                    seen[j] = True; st.append(j)
        comp[grp] = n; n += 1
    seams = mark_seams()
    unwrap()
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.average_islands_scale(scale_uv=False, shear=False)
bpy.ops.object.mode_set(mode='OBJECT')

# escala por regiao: rosto (cabeca virada para a frente) e maos ganham texel
uv = np.empty(len(me.loops) * 2); me.uv_layers[0].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
reg = cfg.get("uv_region_scale", {"face": 1.5, "head": 1.15, "hand": 1.35})
nm = {r: i for i, r in enumerate(regions)}
scaled = {"face": 0, "head": 0, "hand": 0}
for c in range(n):
    fs = np.where(comp == c)[0]
    r = regions[freg[fs[0]]]
    k = 1.0
    if r == "head":
        w = fa[fs]
        front = (fn[fs, 1] * w).sum() / w.sum() < -0.3
        k = reg["face"] if front else reg["head"]; scaled["face" if front else "head"] += 1
    elif r.startswith("hand"):
        k = reg["hand"]; scaled["hand"] += 1
    if k != 1.0:
        li = np.array([l for f in fs for l in polys[f]])
        ctr = uv[li].mean(0)
        uv[li] = ctr + (uv[li] - ctr) * k
me.uv_layers[0].data.foreach_set('uv', uv.ravel())
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, rotate_method='ANY', scale=True, merge_overlap=False,
                        margin_method='SCALED', margin=cfg.get("uv_margin", 0.004), shape_method='CONCAVE')
bpy.ops.object.mode_set(mode='OBJECT')
me.uv_layers[0].name = "UVMap"
me.uv_layers[0].data.foreach_get('uv', uv.ravel())

# conferencia: aproveitamento, sobreposicao, triangulos invertidos, densidade
uvt, _ = uv_triangles(ob)
TS = cfg["tex_size"]
cnt = np.zeros((TS, TS), np.int32)
idx, _ = raster_tris(uvt * TS, TS, cnt)
cov = cnt > 0
area2 = 0.5 * ((uvt[:, 1, 0] - uvt[:, 0, 0]) * (uvt[:, 2, 1] - uvt[:, 0, 1]) - (uvt[:, 2, 0] - uvt[:, 0, 0]) * (uvt[:, 1, 1] - uvt[:, 0, 1]))
# orientacao por ilha: invertido = sinal oposto ao da maioria (ponderado) da ilha
area3d_cm2 = fa.sum() * 1e4
rep = dict(tris=nf, islands=n, seams=seams, uv_min=float(uv.min()), uv_max=float(uv.max()),
           atlas_coverage_pct=round(100 * float(cov.mean()), 1),
           overlap_pixels=int((cnt > 1).sum()), overlap_pct_of_used=round(float(100 * (cnt > 1).sum() / max(cov.sum(), 1)), 2),
           flipped_triangles=int(flipped_faces().sum()), scaled_islands=scaled, surface_area_m2=round(float(fa.sum()), 3),
           texel_per_cm_mean=round(math.sqrt(float(cov.sum()) / area3d_cm2), 2),
           degenerate_uv_triangles=int((np.abs(area2) < 1e-12).sum()))
rng = np.random.default_rng(3)
cols = rng.uniform(0.25, 1.0, (n + 1, 3))
img = np.where((idx >= 0)[..., None], cols[comp[np.maximum(idx, 0)]], 0.08)
save_png(img.astype(np.float32), wpath(cfg, "uv_layout.png"))
save_json(wpath(cfg, "uv_report.json"), rep)
bpy.ops.wm.save_as_mainfile(filepath=wpath(cfg, "game_uv.blend"), compress=True)
print("S5", rep)
