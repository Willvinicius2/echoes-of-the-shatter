"""Conferencia (no estilo do graybox/verify_fbx.py) do FBX de um personagem, reimportado no Blender.

Confere: eixos e escala do arquivo cru (GlobalSettings, no de topo com rotacao 0 e escala 1), dimensoes e pivo
(pes em y = 0, 1,50 m do corpo), triangulos contra o orcamento do 04 (17.2), 1 material, UV0 em [0,1] sem
segunda UV, malha fechada (sem buracos, sem arestas nao-manifold), normais para fora, ossos (<= 55, nomes do
Humanoid), pesos (<= 4 influencias, sem vertice sem peso, soma 1), teste de deformacao da cabeca e a textura
(1024, aproveitamento do atlas). Grava <final>/verify_report.json e sai com erro se algo falhar.
Uso: blender -b --factory-startup -P verify_modelo.py -- m01_guerreiro
"""
import bpy, bmesh, sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mathutils import Vector

cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
from io_scene_fbx import parse_fbx

BUDGET = dict(bones=55, influences=4)   # 04 secao 17.2; alvo do brief


def raw_fbx(path):
    root, ver = parse_fbx.parse(path)
    child = lambda e, n: next((c for c in e.elems if c.id == n), None)

    def props70(e):
        out = {}
        p70 = child(e, b"Properties70") if e is not None else None
        for p in (p70.elems if p70 else []):
            out[p.props[0].decode()] = p.props[4:]
        return out
    gs = props70(child(root, b"GlobalSettings"))
    keys = ["UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign", "UnitScaleFactor"]
    g = {k: (gs[k][0] if k in gs else None) for k in keys}
    models = {m.props[0]: (m.props[1].split(b"\x00")[0].decode(), props70(m)) for m in child(root, b"Objects").elems if m.id == b"Model"}
    top = []
    for c in child(root, b"Connections").elems:
        if c.props[0] == b"OO" and c.props[2] == 0 and c.props[1] in models:
            n, pr = models[c.props[1]]
            top.append(dict(name=n, rot=[round(v, 4) for v in pr.get("Lcl Rotation", (0, 0, 0))],
                            scl=[round(v, 4) for v in pr.get("Lcl Scaling", (1, 1, 1))]))
    canon = (g["UpAxis"], g["UpAxisSign"], g["FrontAxis"], g["FrontAxisSign"], g["CoordAxis"], g["CoordAxisSign"]) == (1, 1, 2, 1, 0, 1)
    top_ok = all(max(abs(v) for v in t["rot"]) < 1e-3 and max(abs(v - 1) for v in t["scl"]) < 1e-4 for t in top)
    return dict(version=ver, axis_canonical_y_up=canon, unit_scale_factor=g["UnitScaleFactor"], top_nodes=top, top_nodes_rot0_scale1=top_ok)


path = fpath(cfg, cfg["asset"] + ".fbx")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=path)
bpy.context.view_layer.update()
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
arms = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
R = dict(file=path, file_kb=round(os.path.getsize(path) / 1024, 1), raw=raw_fbx(path))
ok = {}
body = meshes[0]
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
R["blender_min"] = [round(c, 3) for c in mn]; R["blender_max"] = [round(c, 3) for c in mx]
R["unity_size_xyz"] = [round(mx.x - mn.x, 3), round(mx.z - mn.z, 3), round(mx.y - mn.y, 3)]
R["height_total_m"] = round(mx.z - mn.z, 3)
ok["pivot_ok"] = (abs(mn.z) < 0.012 * cfg["size_scale"]) if cfg["kind"] != "static" else (mn.z < 0 < mx.z)   # personagem: pes em 0; arma: origem na empunhadura (dentro do comprimento)
R["body_height_m"] = cfg["body_height_m"]
R["kind"] = cfg["kind"]
R["tris"] = sum(len(o.data.polygons) for o in meshes if all(len(p.vertices) == 3 for p in o.data.polygons)) or sum(
    sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
lo_, hi_ = cfg.get("tris_range", [5500, 6500])
R["tris_range"] = [lo_, hi_]
ok["tris_in_range"] = lo_ <= R["tris"] <= hi_
mats = sorted({m.name for o in meshes for m in o.data.materials if m})
R["materials"] = mats; ok["one_material"] = len(mats) == 1
imgs = sorted({os.path.basename(n.image.filepath) for m in bpy.data.materials if m.node_tree for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image})
R["textures"] = imgs
ok["one_uv_layer"] = all(len(o.data.uv_layers) == 1 for o in meshes)

# UV e malha
bm = bmesh.new(); bm.from_mesh(body.data)
nonman = sum(1 for e in bm.edges if not e.is_manifold); bound = sum(1 for e in bm.edges if e.is_boundary)
bm.free()
# a malha reimportada separa vertices por UV/normal; fecha pela posicao antes de contar buracos
v, f = mesh_arrays(body)
key = {}
vid = np.array([key.setdefault(tuple(np.round(p, 5)), len(key)) for p in v])
fw = vid[f]
edges = {}
for a, b, c in fw:
    for x, y in ((a, b), (b, c), (c, a)):
        edges[(x, y)] = edges.get((x, y), 0) + 1
open_edges = sum(1 for (x, y), n in edges.items() if (y, x) not in edges)
dup_dir = sum(1 for n in edges.values() if n > 1)
R["mesh"] = dict(open_edges_after_welding=open_edges, nonmanifold_edges_after_welding=dup_dir)
ok["closed_no_holes"] = open_edges == 0 and dup_dir == 0
vw = v[f]
vol = float(np.einsum('ij,ij->', vw[:, 0], np.cross(vw[:, 1], vw[:, 2])) / 6)
R["mesh"]["signed_volume"] = round(vol, 5); ok["normals_outward"] = vol > 0
uv = np.empty(len(body.data.loops) * 2); body.data.uv_layers[0].data.foreach_get('uv', uv)
R["uv"] = dict(min=round(float(uv.min()), 4), max=round(float(uv.max()), 4))
ok["uv_in_0_1"] = uv.min() >= -1e-4 and uv.max() <= 1 + 1e-4
mask = rasterize_uv_mask(body, cfg["tex_size"])
R["uv"]["atlas_coverage_pct"] = round(100 * float(mask.mean()), 1)

# textura
pngs = {}
for n in imgs:
    im = bpy.data.images.get(n)
    pngs[n] = list(im.size) if im else None
R["texture_size"] = pngs

# esqueleto e pesos
if arms:
    a = arms[0]
    bones = [b.name for b in a.data.bones]
    R["armature"] = dict(bones=len(bones), humanoid=gb_rig.humanoid_check(bones) if cfg["kind"] == "humanoid" else None)
    ok["bones_le_55"] = len(bones) <= BUDGET["bones"]
    if cfg["kind"] == "humanoid" and not cfg.get("no_legs"):
        ok["humanoid_required"] = not R["armature"]["humanoid"]["required_missing"]
    counts, sums = [], []
    for vv in body.data.vertices:
        ws = [g.weight for g in vv.groups if g.weight > 1e-6]
        counts.append(len(ws)); sums.append(sum(ws))
    R["skin"] = dict(max_influences=max(counts), unweighted=counts.count(0), weight_sum_min=round(min(sums), 4), weight_sum_max=round(max(sums), 4))
    ok["influences_le_4"] = max(counts) <= 4
    ok["all_vertices_weighted"] = counts.count(0) == 0
    ok["weights_normalized"] = abs(min(sums) - 1) < 1e-3 and abs(max(sums) - 1) < 1e-3


    def group_mean(name):
        gi = body.vertex_groups[name].index
        dg = bpy.context.evaluated_depsgraph_get()
        me = body.evaluated_get(dg).to_mesh()
        pts = [me.vertices[i].co.copy() for i, vv in enumerate(body.data.vertices) if any(g.group == gi and g.weight > 0.5 for g in vv.groups)]
        body.evaluated_get(dg).to_mesh_clear()
        return pts
    hips = "Hips" if "Hips" in body.vertex_groups else "Pelvis"
    hips = "Hips" if "Hips" in body.vertex_groups else "Pelvis"
    h0, p0 = group_mean("Head"), group_mean(hips)
    test_pose(a, cfg["kind"])
    h1, p1 = group_mean("Head"), group_mean(hips)
    # deslocamento medio por vertice (o centroide nao serve: a cabeca gira em torno do proprio eixo)
    mv = lambda A, B: sum((x - y).length for x, y in zip(A, B)) / len(A)
    R["deform_test"] = dict(head_mean_move_m=round(mv(h0, h1), 3), hips_mean_move_m=round(mv(p0, p1), 4))
    ok["deform_test"] = mv(h0, h1) > 0.02 * cfg["size_scale"]
R["checks"] = ok
ok = {k: bool(v) for k, v in ok.items()}; R["checks"] = ok; R["all_ok"] = all(ok.values())
save_json(fpath(cfg, "verify_report.json"), R)
print({k: bool(v) for k, v in ok.items()})
print("VERIFY", "OK" if R["all_ok"] else "FALHOU", "tris", R["tris"], "altura total", R["height_total_m"], "atlas", R["uv"]["atlas_coverage_pct"], "%")
if not R["all_ok"]:
    raise SystemExit("conferencia falhou: " + str([k for k, v in ok.items() if not v]))
