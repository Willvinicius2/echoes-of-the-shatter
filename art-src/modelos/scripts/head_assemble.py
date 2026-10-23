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
    cards.append((np.array(pts), width)); cards_side.append(1 if pts[0][0] >= 0 else -1)


S2 = lambda x: 1 if x >= 0 else -1
JIT = lambda: rng.uniform(-0.3, 0.3)
ATL = json.load(open(HD + r"\hair_atlas.json"))
cards_side = []
meta = []   # tipo de textura por cartao: ("lock", i) ou ("strand", 0)
def lk(kind="lock"):
    if kind == "strand": meta.append(("strand", 0)); return
    meta.append(("lock", int(rng.integers(0, len(ATL["locks"])))))
def add(*a, kind="lock", **k):
    make_card(*a, **k)
    if kind == "smooth": meta.append(("smooth", int(rng.integers(0, len(ATL["smooth"])))))
    else: lk(kind)
# ---- v3: penteado repartido e liso. risca no centro (frente -> tras); mechas partem da risca para os lados e para tras
for side in (-1, 1):
    # franja: da risca na frente cai sobre a testa e varre para a tempora (acima do olho)
    for az, el, ln, wd, lt in ((4, 62, 0.09, 0.07, 2.2), (12, 55, 0.10, 0.07, 2.4), (22, 49, 0.105, 0.07, 2.6)):
        add(side * az, el, ln, wd, 0.005, 0.014, lat=lt * side, fwd=-0.1, grav=0.5, flare=0.0, kind="smooth")
    # topo: da risca, cai sobre os lados do cranio ate a altura da tempora
    for azb, el, ln in ((176, 74, 0.18), (150, 60, 0.18), (6, 78, 0.19), (40, 68, 0.19), (80, 66, 0.15), (118, 58, 0.17)):
        az = azb if azb < 100 or azb > 140 else azb
        azs = side * azb if azb < 140 else 180 - side * (180 - azb)
        front = azb <= 60
        add(azs, el, 0.12 if front else ln, 0.095, 0.004, 0.012, lat=side * (1.7 if front else 0.45), grav=0.45, flare=0.0, kind="smooth")
    # laterais curtas (cobrem a regiao da orelha ate a tempora, nao descem ao ombro)
    for azb, el, ln in ((66, 36, 0.10), (88, 34, 0.11), (110, 32, 0.12), (130, 28, 0.15)):
        add(side * azb, el, ln, 0.085, 0.01, 0.03, fwd=0.1, grav=0.1, flare=0.01)
for side in (-1, 1):
    for azb, el, ln in ((124, 44, 0.16), (140, 38, 0.18), (156, 36, 0.18), (130, 24, 0.20), (150, 24, 0.22)):
        add(side * azb, el, ln, 0.095, 0.01, 0.034, lat=JIT(), grav=0.2, flare=0.015)
# base rente (cobre o couro cabeludo) so atras
add(180, 70, 0.12, 0.10, 0.003, 0.014, grav=0.2)
for az0 in range(-165, 166, 33):
    if abs(az0) < 112: continue
    add(az0 + JIT() * 8, 52, 0.15, 0.10, 0.005, 0.02, grav=0.2, flare=0.004)
# camada media atras
for i in range(10):
    az = 180 - 119 - (i + JIT()) * (122 / 10)
    az = -az if i % 2 else az
    az = (az + 180) % 360 - 180
add_az = [(-170 + k * 24 + JIT() * 6) for k in range(15)]
for az in add_az:
    if abs(az) < 118 or abs(az) > 175 and False: continue
    add(az, 32, rng.uniform(0.18, 0.22), rng.uniform(0.09, 0.105), 0.01, 0.034, lat=JIT(), grav=0.2, flare=rng.uniform(0.01, 0.02))
# camada externa: nuca ate a base do pescoco
for az in [(-172 + k * 22 + JIT() * 5) for k in range(16)]:
    if abs(az) < 120: continue
    add(az, 14, rng.uniform(0.24, 0.29), rng.uniform(0.09, 0.105), 0.016, 0.05, lat=JIT(), grav=0.3, flare=rng.uniform(0.02, 0.035))
for i in range(5):
    az = (180 + (i - 2 + JIT()) * 38 + 180) % 360 - 180
    add(az, 0, rng.uniform(0.22, 0.26), rng.uniform(0.085, 0.10), 0.022, 0.058, lat=JIT(), grav=0.35, flare=0.03)
# mechas soltas
for az in (-150, -130, 130, 150, 172):
    add(az, 14, 0.15, 0.03, 0.028, 0.045, lat=0.2 * S2(az), grav=0.25, flare=0.01, kind="strand")

BULGE = 0.007
bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); dl = bm.verts.layers.deform.new()
for k, (pts, width) in enumerate(cards):
    kind, ci = meta[k]
    u0, v0_, u1, v1_ = ATL["locks"][ci] if kind == "lock" else (ATL["smooth"][ci] if kind == "smooth" else ATL["strands"][0])
    if kind in ("lock",) and rng.random() < 0.5: u0, u1 = u1, u0
    if kind == "smooth" and cards_side[k] < 0: u0, u1 = u1, u0
    npt = len(pts)
    rows = []
    for i, p in enumerate(pts):
        t = i / (npt - 1)
        n = normal_at(p)
        tdir = pts[min(i + 1, npt - 1)] - pts[max(i - 1, 0)]; tdir /= np.linalg.norm(tdir) + 1e-9
        w = np.cross(tdir, n); w /= np.linalg.norm(w) + 1e-9
        hw = width / 2 * (1 + 0.1 * t)
        off = 0.0
        row = []
        for j, sx in enumerate((-1, 0, 1)):
            e_ = 1.0
            if i == npt - 1: e_ = rng.uniform(0.4, 0.8) if sx != 0 else 1.0       # ponta afilada
            elif i > 0 and sx != 0: e_ = rng.uniform(0.82, 1.08)                     # borda irregular
            q = p + w * hw * sx * e_ 
            q = q + n * (BULGE * (1 - 0.4 * t) if sx == 0 else 0.0)
            v = bm.verts.new(Vector(q)); v[dl][0] = 1.0
            row.append(v)
        rows.append(row)
    for i in range(npt - 1):
        for j in range(2):
            a0, a1, b1, b0 = rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]
            f = bm.faces.new((a0, a1, b1, b0))
            nn = normal_at(pts[i])
            if np.dot(np.array(f.normal), nn) < 0: f.normal_flip()
            for l in f.loops:
                vv = l.vert
                col = rows[i].index(vv) if vv in rows[i] else rows[i + 1].index(vv)
                row_i = i if vv in rows[i] else i + 1
                l[uvl].uv = (u0 + (u1 - u0) * col / 2, (1 - v0_) - (v1_ - v0_) * row_i / (npt - 1))
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
