"""Etapa c (Blender): malha de jogo no quadro final, normais, UV 512 e oclusao de ambiente da malha alta decimada.

Aplica M (work/norm.json) a work/game_src.ply e work/high_src.ply, arestas vivas por angulo, desdobramento por
angulo (smart project) e empacotamento sem rotacao. A AO usa a malha alta decimada (high_src) ja no quadro final:
cada texel acha o ponto mais proximo da malha alta e dispara um hemisferio de raios (cosseno) ate `ao_dist`.
Calcula em 256 (a AO e suave) e deixa a ampliacao para a pintura. Grava work/game_final.blend, work/geo.npz
(posicao e normal por texel em 512, no quadro final) e work/ao256.npz. Cada fragmento de AO em 1 processo so.
"""
import bpy, bmesh, math, numpy as np, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_common import *
from mdl_blender import *
from mathutils import Vector
from mathutils.bvhtree import BVHTree

c = load_cfg()
nm = load_json(wpath(c, "norm.json"))
A = np.array(nm["A"]); t = np.array(nm["t"])
bpy.ops.wm.read_factory_settings(use_empty=True)
low = load_ply_obj(wpath(c, "game_src.ply"), "game")
high = load_ply_obj(wpath(c, "high_src.ply"), "high")
for ob in (low, high):
    v, _ = mesh_arrays(ob)
    ob.data.vertices.foreach_set('co', ((v @ A.T) + t).ravel()); ob.data.update()
bpy.context.view_layer.objects.active = low
bm = bmesh.new(); bm.from_mesh(low.data)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bmesh.ops.triangulate(bm, faces=bm.faces)
bm.edges.ensure_lookup_table()
for e in bm.edges:
    e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(c.get("sharp_deg", 38)))
for f in bm.faces: f.smooth = True
bm.to_mesh(low.data); bm.free()

# UV: ilhas por direcao da normal no quadro src (frente -Y = a propria imagem da folha, costas, lados, topo) com
# projecao planar em metros (densidade uniforme); componentes minusculos viram parte do vizinho; fundo (normal final
# para baixo) fica com 20 % da densidade porque a camera nunca o ve.
Ai = np.linalg.inv(A)
sc_ax = np.linalg.norm(A, axis=0)                      # comprimento final de cada eixo src
bm = bmesh.new(); bm.from_mesh(low.data); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
AX = np.array([[0, -1, 0], [0, 1, 0], [1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1]], float)
bias = np.array([1.0, 1.0, .85, .85, .85, .85])
fgrp = np.zeros(len(bm.faces), int); farea = np.zeros(len(bm.faces))
for f in bm.faces:
    ns = A.T @ np.array(f.normal[:]); ns /= max(np.linalg.norm(ns), 1e-9)
    fgrp[f.index] = int(np.argmax((AX @ ns) * bias)); farea[f.index] = f.calc_area()
for _ in range(3):
    seen = -np.ones(len(bm.faces), int); comps = []
    for f0 in bm.faces:
        if seen[f0.index] >= 0: continue
        st = [f0]; seen[f0.index] = len(comps); cur = [f0.index]
        while st:
            x = st.pop()
            for e in x.edges:
                for g in e.link_faces:
                    if seen[g.index] < 0 and fgrp[g.index] == fgrp[f0.index]:
                        seen[g.index] = len(comps); st.append(g); cur.append(g.index)
        comps.append(cur)
    tot = farea.sum(); changed = False
    for cur in comps:
        if farea[cur].sum() < 0.05 * tot and len(comps) > 1:
            votes = {}
            for fi in cur:
                for e in bm.faces[fi].edges:
                    for g in e.link_faces:
                        if g.index not in cur: votes[fgrp[g.index]] = votes.get(fgrp[g.index], 0) + e.calc_length()
            if votes:
                fgrp[cur] = max(votes, key=votes.get); changed = True
    if not changed: break
uvl = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    nf = np.array(f.normal[:])
    g = fgrp[f.index]; hid = (nf[2] < -0.8)
    for l in f.loops:
        q = Ai @ (np.array(l.vert.co[:]) - t)
        if g == 0: uv = (q[0] * sc_ax[0], q[2] * sc_ax[2])
        elif g == 1: uv = (-q[0] * sc_ax[0], q[2] * sc_ax[2])
        elif g in (2, 3): uv = (q[1] * sc_ax[1] * (1 if g == 2 else -1), q[2] * sc_ax[2])
        else: uv = (q[0] * sc_ax[0], q[1] * sc_ax[1] * (1 if g == 4 else -1))
        k = 0.2 if hid else 1.0
        l[uvl].uv = (uv[0] * k, uv[1] * k)
bm.to_mesh(low.data); bm.free()
bpy.ops.object.select_all(action='DESELECT'); low.select_set(True); bpy.context.view_layer.objects.active = low
bpy.context.scene.tool_settings.use_uv_select_sync = True
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.pack_islands(rotate=False, margin=0.01)
bpy.ops.object.mode_set(mode='OBJECT')
low.data.name = low.name = "game"
uvrep = dict(islands_by_group=np.bincount(fgrp, minlength=6).tolist())

# geometria por texel (512) e AO (256)
TS = c["tex"]
g = texel_geometry(low, TS)
np.savez_compressed(wpath(c, "geo.npz"), valid=g["valid"], pos=g["pos"].astype(np.float32), nrm=g["nrm"].astype(np.float32))
g2 = texel_geometry(low, 256)
hv, hf = mesh_arrays(high)
bvh = BVHTree.FromPolygons([tuple(x) for x in hv], [tuple(f) for f in hf])
ys, xs = np.where(g2["valid"])
NR = c.get("ao_rays", 20)
dist = c["ao_dist"]
k = (np.arange(NR) + 0.5) / NR
ct, st = np.sqrt(1 - k), np.sqrt(k)
ph = np.arange(NR) * 2.399963
hemi = np.stack([st * np.cos(ph), st * np.sin(ph), ct], 1)
rng = np.random.default_rng(5)
ao = np.ones((256, 256), np.float32)
t0 = time.time()
for y, x in zip(ys, xs):
    p, n = Vector(g2["pos"][y, x]), Vector(g2["nrm"][y, x])
    h = bvh.find_nearest(p, 0.2)
    if h[0] is None:
        continue
    o, hn = h[0], h[1]
    if hn.dot(n) < 0: hn = -hn
    o = o + hn * 0.004
    tt = hn.cross(Vector((0, 0, 1)) if abs(hn.z) < 0.9 else Vector((1, 0, 0))).normalized(); bb = hn.cross(tt)
    a = rng.uniform(0, 2 * math.pi); ca, sa = math.cos(a), math.sin(a)
    tt, bb = tt * ca + bb * sa, bb * ca - tt * sa
    hit = 0
    for d in hemi:
        if bvh.ray_cast(o, tt * d[0] + bb * d[1] + hn * d[2], dist)[0] is not None: hit += 1
    ao[y, x] = 1.0 - hit / NR
np.savez_compressed(wpath(c, "ao256.npz"), ao=ao, valid=g2["valid"])
bpy.data.objects.remove(high)
bpy.ops.wm.save_as_mainfile(filepath=wpath(c, "game_final.blend"), compress=True)
print("EC", uvrep, len(low.data.polygons), "tris; texels", int(g["valid"].sum()), "ao", round(float(ao[g2["valid"]].mean()), 3), round(time.time() - t0), "s")
