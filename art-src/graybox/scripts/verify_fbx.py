"""Confere os FBX de fbx/ reimportando-os no Blender e lendo o arquivo cru.

Para cada FBX: dimensoes (Blender e Unity), pivo, triangulos por malha, materiais, UV e cor de vertice,
skinning (influencias por vertice), ossos e nomes do Humanoid, e o que o Unity vai ler do arquivo
(GlobalSettings: eixos e UnitScaleFactor; Lcl Rotation/Scaling dos nos de topo). Compara com os relatorios de
geracao (previews/_*_report.json) e com os orcamentos do docs/04 secao 17.2. Grava previews/_fbx_verify_report.json.
"""
import bpy, sys, os, json, glob, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gb_lib import *
from gb_rig import humanoid_check, RIG_NAME
from io_scene_fbx import parse_fbx

BUDGET = {  # docs/04 secao 17.2: (tris min, tris max, materiais max, ossos max)
    "hero": (7000, 10000, 2, 55), "enemy": (3500, 5000, 1, 35), "boss": (15000, 25000, 2, 100),
    "floor": (200, 600, 1, 0), "structure": (800, 2500, 1, 0), "prop": (100, 800, 1, 0), "rig": (0, 0, 0, 55)}
TOL = 0.002


def load(name):
    p = f"{PREV}/{name}"
    return json.load(open(p)) if os.path.exists(p) else {}


SRC_HEROES = load("_heroes_report.json").get("heroes", {})
SRC_ENEMIES = load("_enemies_report.json").get("enemies", {})
SRC_KIT = load("_crypt_kit_report.json").get("pieces", {})
SRC_RIG = load("_rig_report.json")


def raw_fbx(path):
    root, ver = parse_fbx.parse(path)

    def child(e, name):
        for c in e.elems:
            if c.id == name:
                return c

    def props70(e):
        out = {}
        p70 = child(e, b"Properties70") if e is not None else None
        for p in (p70.elems if p70 else []):
            out[p.props[0].decode()] = p.props[4:]
        return out
    gs = props70(child(root, b"GlobalSettings"))
    keys = ["UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign",
            "UnitScaleFactor", "OriginalUnitScaleFactor"]
    glob_s = {k: (gs[k][0] if k in gs else None) for k in keys}
    models = {}
    for m in child(root, b"Objects").elems:
        if m.id == b"Model":
            models[m.props[0]] = (m.props[1].split(b"\x00")[0].decode(), m.props[2].decode(), props70(m))
    top = []
    for c in child(root, b"Connections").elems:
        if c.props[0] == b"OO" and c.props[2] == 0 and c.props[1] in models:
            name, kind, pr = models[c.props[1]]
            top.append(dict(name=name, type=kind,
                            lcl_translation=[round(v, 4) for v in pr.get("Lcl Translation", (0, 0, 0))],
                            lcl_rotation=[round(v, 4) for v in pr.get("Lcl Rotation", (0, 0, 0))],
                            lcl_scaling=[round(v, 4) for v in pr.get("Lcl Scaling", (1, 1, 1))]))
    canonical = (glob_s["UpAxis"], glob_s["UpAxisSign"], glob_s["FrontAxis"], glob_s["FrontAxisSign"],
                 glob_s["CoordAxis"], glob_s["CoordAxisSign"]) == (1, 1, 2, 1, 0, 1)
    top_ok = all(max(abs(v) for v in t["lcl_rotation"]) < 1e-3 and max(abs(v - 1) for v in t["lcl_scaling"]) < 1e-4
                 for t in top)
    return dict(fbx_version=ver, global_settings=glob_s, axis_system_canonical_y_up=canonical,
                top_nodes=top, top_nodes_rotation_0_scale_1=top_ok)


def deform_test(arm, body):
    """Gira o osso Head 30 graus: as pecas da cabeca tem de se mover e as do quadril nao (prova o bind pose)."""
    def group_mean(name):
        gi = body.vertex_groups[name].index
        dg = bpy.context.evaluated_depsgraph_get()
        me = body.evaluated_get(dg).to_mesh()
        pts = [body.matrix_world @ me.vertices[v.index].co for v in body.data.vertices
               if any(g.group == gi for g in v.groups)]
        body.evaluated_get(dg).to_mesh_clear()
        return sum(pts, Vector()) / len(pts)
    h0, p0 = group_mean("Head"), group_mean("Hips")
    pb = arm.pose.bones["Head"]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = (math.radians(30), 0, 0)
    bpy.context.view_layer.update()
    h1, p1 = group_mean("Head"), group_mean("Hips")
    pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    moved, still = (h1 - h0).length, (p1 - p0).length
    return dict(head_moved_m=round(moved, 3), hips_moved_m=round(still, 4), ok=moved > 0.02 and still < 1e-4)


def category(stem):
    if stem.startswith("Rig_"):
        return "rig"
    if stem.startswith("SK_"):
        return "hero"
    if stem.startswith("SM_Enemy_"):
        return "enemy"
    if stem.startswith("SM_Boss_"):
        return "boss"
    return SRC_KIT.get(stem, {}).get("category", "prop")


def check(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    reset()
    bpy.ops.import_scene.fbx(filepath=path)
    bpy.context.view_layer.update()
    meshes = sorted([o for o in bpy.context.scene.objects if o.type == 'MESH'], key=lambda o: o.name)
    arms = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
    cat = category(stem)
    lo, hi, mat_max, bone_max = BUDGET[cat]
    r = dict(category=cat, file_kb=round(os.path.getsize(path) / 1024, 1), raw=raw_fbx(path))
    if meshes:
        mn, mx = bbox(meshes)
        r["blender_min"] = [round(c, 3) + 0.0 for c in mn]
        r["blender_max"] = [round(c, 3) + 0.0 for c in mx]
        r["unity"] = unity_bounds(mn, mx)
        r["pivot"] = dict(min_height=round(mn.z, 3) + 0.0, center_xz_unity=[round(-(mn.x + mx.x) / 2, 3) + 0.0,
                                                                            round(-(mn.y + mx.y) / 2, 3) + 0.0])
        r["tris"] = {o.name: tris(o) for o in meshes}
        r["tris_total"] = sum(r["tris"].values())
        r["materials"] = sorted({m.name for o in meshes for m in o.data.materials if m})
        imgs = set()
        for m in bpy.data.materials:
            if m.node_tree:
                imgs |= {os.path.basename(n.image.filepath) for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image}
        r["textures"] = sorted(imgs)
        r["uv_and_vertex_color"] = all(len(o.data.uv_layers) > 0 and len(o.data.color_attributes) > 0 for o in meshes)
        r["budget"] = dict(tris_range=[lo, hi], pct_of_max=round(100 * r["tris_total"] / hi, 1),
                           under_max=r["tris_total"] <= hi, materials_ok=len(r["materials"]) <= mat_max)
    if arms:
        a = arms[0]
        bones = a.data.bones
        r["armature"] = dict(object=a.name, bones=len(bones), under_max=len(bones) <= bone_max,
                             humanoid=humanoid_check([b.name for b in bones]))
        if SRC_RIG:
            err = 0.0
            for b in bones:
                src = SRC_RIG["head_blender"].get(b.name)
                if src:
                    err = max(err, ((a.matrix_world @ b.head_local) - Vector(src)).length)
            r["armature"]["max_bone_head_error_m"] = round(err, 5)
        skin = {}
        for o in meshes:
            counts = [sum(1 for g in v.groups if g.weight > 1e-6) for v in o.data.vertices]
            skin[o.name] = dict(max_influences=max(counts), unweighted=counts.count(0), groups=len(o.vertex_groups),
                                bound_to_armature=any(m.type == 'ARMATURE' for m in o.modifiers) or o.parent is a)
        r["skinning"] = skin
        r["skinning_rigid_ok"] = all(s["max_influences"] == 1 and s["unweighted"] == 0 for s in skin.values()) if skin else None
        body = next((o for o in meshes if o.name.endswith("_Body")), None)
        if body and "Head" in a.pose.bones:
            r["deform_test"] = deform_test(a, body)
    # comparacao com os relatorios de geracao
    src = None
    if stem in SRC_KIT:
        src = dict(size=SRC_KIT[stem]["unity"]["size"], tris=SRC_KIT[stem]["tris"])
    elif stem in SRC_ENEMIES:
        src = dict(size=SRC_ENEMIES[stem]["unity"]["size"], tris=SRC_ENEMIES[stem]["tris"])
    elif stem.startswith("SK_") and stem[3:] in SRC_HEROES:
        h = SRC_HEROES[stem[3:]]
        src = dict(size=h["unity_all"]["size"], tris=h["tris_total"])
    if src and meshes:
        r["matches_source"] = (max(abs(a - b) for a, b in zip(src["size"], r["unity"]["size"])) <= TOL
                               and src["tris"] == r["tris_total"])
    return stem, r


report = dict(version=version_info(), preset=dict((k, (sorted(v) if isinstance(v, set) else v)) for k, v in FBX_PRESET.items()),
              mapping="Unity (x, y, z) = (-x_blender, z_blender, -y_blender)", files={})
for path in sorted(glob.glob(f"{FBX}/*.fbx")):
    stem, r = check(path)
    report["files"][stem] = r
files = report["files"].values()
report["summary"] = dict(
    files=len(report["files"]),
    all_axis_canonical=all(r["raw"]["axis_system_canonical_y_up"] for r in files),
    all_top_nodes_rotation_0_scale_1=all(r["raw"]["top_nodes_rotation_0_scale_1"] for r in files),
    all_unit_scale_factor_100=all(abs(r["raw"]["global_settings"]["UnitScaleFactor"] - 100.0) < 1e-6 for r in files),
    all_under_tris_max=all(r.get("budget", {}).get("under_max", True) for r in files),
    all_materials_ok=all(r.get("budget", {}).get("materials_ok", True) for r in files),
    all_match_source=all(r.get("matches_source", True) for r in files),
    all_rigid_skinning=all(r.get("skinning_rigid_ok") in (True, None) for r in files),
    all_deform_tests_ok=all(r["deform_test"]["ok"] for r in files if "deform_test" in r),
    humanoid_required_missing=sorted({n for r in files for n in r.get("armature", {}).get("humanoid", {}).get("required_missing", [])}),
    max_bone_head_error_m=max([r["armature"].get("max_bone_head_error_m", 0) for r in files if "armature" in r] or [0]))
json.dump(report, open(f"{PREV}/_fbx_verify_report.json", "w"), indent=1)

print(f"{'arquivo':34s} {'cat':9s} {'L x A x P (Unity, m)':24s} {'tris':>6s} {'%max':>6s} {'piv_y':>6s} ok")
for stem, r in report["files"].items():
    if "unity" in r:
        s = r["unity"]["size"]
        print(f"{stem:34s} {r['category']:9s} {s[0]:6.2f} x {s[1]:5.2f} x {s[2]:5.2f}     {r['tris_total']:6d} "
              f"{r['budget']['pct_of_max']:6.1f} {r['pivot']['min_height']:6.2f} {r.get('matches_source', '-')}")
    else:
        print(f"{stem:34s} {r['category']:9s} bones={r['armature']['bones']} humanoid_missing={r['armature']['humanoid']['required_missing']}")
print("SUMMARY", json.dumps(report["summary"]))
bad = [k for k, v in report["summary"].items() if v is False] + report["summary"]["humanoid_required_missing"]
if bad:
    raise SystemExit(f"conferencia falhou: {bad}")
