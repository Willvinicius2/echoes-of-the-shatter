"""Monta o corpo-base com a cabeca nova + cabelo em cartoes (Blender -b).
Entrada: head_v2.blend (head_build.py), texturas T_ArcherDark_Head_*.png e T_ArcherDark_Hair_BC.png (head_paint.py, hair_tex.py).
Saida: SK_ArcherDark_Body.blend/.fbx (corpo + SM_ArcherDark_Hair, mesmo esqueleto), GLB, relatorio.
Uso: blender -b --factory-startup -P head_assemble.py -- arq_dark_corpo"""
import bpy, bmesh, math, sys, os, shutil, json
import numpy as np
REPO = r"D:\openclaude\_trabalho-claude\wt\arqueiro-dark-3d"
sys.path.insert(0, REPO + r"\art-src\modelos\scripts")
from mdl_common import *
from mdl_blender import *
from mathutils import Vector

cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
HD = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\cabeca"
bpy.ops.wm.open_mainfile(filepath=HD + r"\head_v2.blend")
ob = bpy.data.objects["game"]
ob.name = cfg.get("mesh_name", "SK_ArcherDark_Body"); ob.data.name = ob.name
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')

# ---------------------------------------------------------------- cabelo
rng = np.random.default_rng(7)
C = np.array([0.0, 0.0, 1.655]); R = np.array([0.079, 0.098, 0.126])
cards = []   # (pts[n+1], width, tipw, col)


def surf(p, off):
    """projeta p na superficie do cabelo (elipsoide inflada no alto, saia afilada abaixo)"""
    q = (p - C) / R
    if q[2] > -0.36:
        q = q / np.linalg.norm(q)
        return C + R * q + (R * q) / np.linalg.norm(R * q) * off
    z = p[2]
    tp = 1.0 - 0.30 * min(1.0, (1.60 - z) / 0.10) if z < 1.60 else 1.0
    a = (0.079 * 0.93 * tp + off * 0.8); b = (0.098 * 0.93 * tp + off * 0.8)
    xy = np.array([p[0] / a, (p[1] - C[1]) / b]); nrm = np.linalg.norm(xy) + 1e-9
    xy = xy / nrm
    return np.array([xy[0] * a, C[1] + xy[1] * b, z])


def normal_at(p):
    q = (p - C) / (R * R); return q / (np.linalg.norm(q) + 1e-9)


def make_card(az_deg, el_deg, length, width, off0, off1, lat=0.0, fwd=0.0, grav=0.0, nseg=4, flare=0.0):
    a = math.radians(az_deg); e = math.radians(el_deg)
    d = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
    p = surf(C + R * d, off0)
    pts = [p.copy()]
    ds = length / nseg
    for k in range(nseg):
        n = normal_at(p)
        down = np.array([0, 0, -1.0]) - n * np.dot(np.array([0, 0, -1.0]), n)
        if np.linalg.norm(down) < 0.2:
            down = np.array([math.sin(a), -math.cos(a), 0.0])
        down /= np.linalg.norm(down) + 1e-9
        latv = np.cross(n, [0, 0, 1.0]); latv /= np.linalg.norm(latv) + 1e-9
        dirv = down + latv * lat + np.array([0, -1.0, 0]) * fwd + np.array([0, 0, -1.0]) * grav
        dirv -= n * np.dot(dirv, n) * (0.6 if p[2] > 1.62 else 0.0)
        dirv /= np.linalg.norm(dirv) + 1e-9
        t = (k + 1) / nseg
        off = off0 + (off1 - off0) * t ** 1.4
        p = surf(p + dirv * ds, off + flare * t * t)
        pts.append(p.copy())
    cards.append((np.array(pts), width))


S2 = lambda x: 1 if x >= 0 else -1
JIT = lambda: rng.uniform(-0.3, 0.3)
# 1) coroa e topo: cobre o couro cabeludo, varre para tras e para os lados
make_card(0, 84, 0.12, 0.08, 0.004, 0.03, grav=0.3)
for el, na in ((72, 6), (60, 10), (48, 14)):
    for i in range(na):
        az = (i + rng.uniform(-0.3, 0.3)) * 360 / na - 180
        front = abs(az) < 60
        if front and el < 55: continue
        sd = S2(math.sin(math.radians(az)))
        make_card(az, el, rng.uniform(0.12, 0.17), rng.uniform(0.07, 0.085), 0.004, 0.032,
                  lat=(0.9 * sd if front else 0.2) + JIT() * 0.5, fwd=(-0.25 if front else 0.0), grav=0.25, flare=rng.uniform(0.004, 0.014))
# 2) anel medio: volume lateral
for i in range(20):
    az = -180 + (i + rng.uniform(-0.25, 0.25)) * 18
    if abs(az) < 40: continue
    make_card(az, rng.uniform(16, 28), rng.uniform(0.16, 0.22), rng.uniform(0.065, 0.08), 0.012, 0.045, lat=JIT(), grav=0.2, flare=rng.uniform(0.012, 0.028))
# 3) nuca em camadas, pontas abertas
for el, na, ln in ((6, 14, 0.25), (-10, 12, 0.22), (-24, 8, 0.17)):
    for i in range(na):
        az = (180 + (i + rng.uniform(-0.2, 0.2)) * 360 / na + 180) % 360 - 180
        if abs(az) < 62: continue
        make_card(az, el, ln + rng.uniform(-0.04, 0.03), rng.uniform(0.07, 0.085), 0.018, 0.05, lat=JIT(), grav=0.3, flare=rng.uniform(0.014, 0.03))
# 4) franja repartida: cai dos dois lados da risca, deixa o centro aberto
for i in range(14):
    side = -1 if i % 2 == 0 else 1
    make_card(side * rng.uniform(4, 40), rng.uniform(38, 46), rng.uniform(0.10, 0.135), rng.uniform(0.04, 0.055), 0.006, 0.026,
              lat=1.5 * side + JIT() * 0.4, fwd=-0.05, grav=0.45, flare=rng.uniform(0.006, 0.016))
# 5) mechas laterais na frente da orelha
for i in range(10):
    side = -1 if i % 2 == 0 else 1
    make_card(side * rng.uniform(56, 80), rng.uniform(16, 30), rng.uniform(0.13, 0.18), rng.uniform(0.04, 0.052), 0.008, 0.034, fwd=0.3, grav=0.12, flare=rng.uniform(0.008, 0.02))
# 6) fios soltos nas pontas
for i in range(12):
    az = rng.uniform(-180, 180)
    if abs(az) < 50: continue
    make_card(az, rng.uniform(5, 32), rng.uniform(0.12, 0.18), rng.uniform(0.032, 0.042), 0.03, 0.06, lat=JIT(), grav=0.2, flare=0.02)

bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); dl = bm.verts.layers.deform.new()
NSEG = 4
for k, (pts, width) in enumerate(cards):
    col = k % 8; flip = rng.random() < 0.5
    rows = []
    for i, p in enumerate(pts):
        n = normal_at(p)
        tdir = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]); tdir /= np.linalg.norm(tdir) + 1e-9
        w = np.cross(tdir, n); w /= np.linalg.norm(w) + 1e-9
        hw = width / 2 * (1 - 0.15 * i / (len(pts) - 1))
        vl = bm.verts.new(Vector(p - w * hw)); vr = bm.verts.new(Vector(p + w * hw))
        vl[dl][0] = 1.0; vr[dl][0] = 1.0
        rows.append((vl, vr))
    for i in range(len(pts) - 1):
        a0, a1 = rows[i]; b0, b1 = rows[i + 1]
        f = bm.faces.new((a0, a1, b1, b0))
        nf = np.array(f.normal); nn = normal_at(pts[i])
        if np.dot(nf, nn) < 0:
            f.normal_flip()
        u0, u1 = col / 8 + 0.004, (col + 1) / 8 - 0.004
        if flip: u0, u1 = u1, u0
        v0, v1 = 1 - i / (len(pts) - 1), 1 - (i + 1) / (len(pts) - 1)
        for l in f.loops:
            vv = l.vert
            isL = (vv is a0 or vv is b0); isTop = (vv is a0 or vv is a1)
            l[uvl].uv = (u0 if isL else u1, v0 if isTop else v1)
        f.smooth = True
bm.normal_update()
hm = bpy.data.meshes.new("SM_ArcherDark_Hair"); bm.to_mesh(hm); bm.free()
hob = bpy.data.objects.new("SM_ArcherDark_Hair", hm); bpy.context.scene.collection.objects.link(hob)
hob.vertex_groups.new(name="Head")
# vertex group "Head" deve ter o mesmo indice do osso; cria por nome e atribui peso 1
hm_verts = [v.index for v in hm.vertices]
hob.vertex_groups["Head"].add(hm_verts, 1.0, 'REPLACE')
hob.parent = arm; hob.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
md = hob.modifiers.new("Armature", 'ARMATURE'); md.object = arm
n_hair = len(hm.polygons) * 2
print("HAIR cards", len(cards), "tris", n_hair)

# limita a 4 influencias por vertice (o corte do pescoco interpola pesos de varios ossos)
for v in ob.data.vertices:
    gs = sorted([(g.group, g.weight) for g in v.groups], key=lambda t: -t[1])
    if len(gs) > 4:
        for gi, _ in gs[4:]:
            ob.vertex_groups[gi].remove([v.index])
        gs = gs[:4]
        tot = sum(w for _, w in gs)
        for gi, w in gs:
            ob.vertex_groups[gi].add([v.index], w / tot, 'REPLACE')

# ---------------------------------------------------------------- materiais
FD = cfg["final_dir"]


def mk_mat(name, bc, nrm=None, alpha=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    img = bpy.data.images.load(bc); img.colorspace_settings.name = 'sRGB'
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.55 if alpha else 1.0
    if alpha:
        nt.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
        m.surface_render_method = 'DITHERED'      # alpha-hash
        m.use_backface_culling = False
    if nrm:
        ni = bpy.data.images.load(nrm); ni.colorspace_settings.name = 'Non-Color'
        nt2 = nt.nodes.new('ShaderNodeTexImage'); nt2.image = ni
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = cfg.get("normal_strength", 1.0)
        nt.links.new(nt2.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


tex = "ArcherDark"
for n in ("T_ArcherDark_Head_BC.png", "T_ArcherDark_Head_N.png", "T_ArcherDark_Hair_BC.png"):
    shutil.copyfile(HD + "\\" + n, FD + "\\" + n)
body_mat = mk_mat("M_ArcherDark_Body", FD + r"\T_ArcherDark_Body_BC.png", FD + r"\T_ArcherDark_Body_N.png")
head_mat = mk_mat("M_ArcherDark_Head", FD + r"\T_ArcherDark_Head_BC.png", FD + r"\T_ArcherDark_Head_N.png")
hair_mat = mk_mat("M_ArcherDark_Hair", FD + r"\T_ArcherDark_Hair_BC.png", None, alpha=True)
ob.data.materials.clear(); ob.data.materials.append(body_mat); ob.data.materials.append(head_mat)
hob.data.materials.append(hair_mat)
mb = ob.data
zmin = np.array([min(mb.vertices[v].co.z for v in p.vertices) for p in mb.polygons])
for p, zm in zip(mb.polygons, zmin):
    p.material_index = 1 if zm >= 1.4699 else 0

# ---------------------------------------------------------------- teste de pose (corpo + cabelo)
rest = evaluated_coords(ob)
test_pose(arm, cfg["kind"])
pos = evaluated_coords(ob)
me = ob.data
e = np.empty(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get('vertices', e); e = e.reshape(-1, 2)
r = np.linalg.norm(pos[e[:, 0]] - pos[e[:, 1]], axis=1) / np.maximum(np.linalg.norm(rest[e[:, 0]] - rest[e[:, 1]], axis=1), 1e-6)
pose = dict(edge_stretch_max=round(float(r.max()), 3), edge_stretch_p99=round(float(np.percentile(r, 99)), 3),
            edges_over_1_5=int((r > 1.5).sum()), edges_over_2=int((r > 2).sum()), edges=int(len(r)), note="1 = sem esticar; aresta acima de 2 = possivel rasgo")
save_json(wpath(cfg, "pose_report.json"), pose)
clear_pose(arm)

# ---------------------------------------------------------------- export
for o in bpy.context.scene.objects: o.select_set(False)
fbx = fpath(cfg, cfg["asset"] + ".fbx")
gb_rig.export_fbx_rigged(arm, [ob, hob], fbx)
bpy.ops.wm.save_as_mainfile(filepath=fpath(cfg, cfg["asset"] + ".blend"), compress=True)
glb = fpath(cfg, "ArcherDark_Body.glb")
for o in bpy.context.scene.objects: o.select_set(False)
arm.select_set(True); ob.select_set(True); hob.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=False, export_animations=False,
                          export_skins=True, export_image_format='AUTO')
rep = dict(fbx=fbx, glb=glb, pose=pose, tris_body=len(me.polygons), tris_hair=n_hair, tris_total=len(me.polygons) + n_hair)
save_json(wpath(cfg, "export_report.json"), rep)
print("ASSEMBLE", rep)
