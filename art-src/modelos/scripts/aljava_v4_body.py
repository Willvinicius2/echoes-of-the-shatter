"""Aljava v4, passo 1 (Blender -b, Cycles CPU): corpo limpo e fechado (torno com 20 lados) no perfil do corpo TripoSG,
UV cilindrica sem emenda de casca, e bake em 2048 do normal (high.ply) e da cor (malha de jogo v1 pintada).
uso: blender -b -P aljava_v4_body.py -- <body_v3.blend> <game_v1.blend> <high.ply> <out_dir> [tex=2048]"""
import bpy, bmesh, sys, math, os
import numpy as np
from mathutils import Vector, Matrix
a = sys.argv[sys.argv.index("--") + 1:]
body3, game, high_ply, out = a[:4]; TEX = int(a[4]) if len(a) > 4 else 2048
THETA = math.radians(9.9); ORG = Vector((0, 0, -0.1))
M = Matrix.Translation(ORG) @ Matrix.Rotation(THETA, 4, 'Y'); Mi = M.inverted()
N_SEG = 20; Z_TOP = 0.090
# ---- perfil r(z, angulo) do corpo v3 (percentil baixo: ignora saliencias de alca) ----
bpy.ops.wm.open_mainfile(filepath=body3)
b3 = bpy.data.objects["SM_ArcherDark_Quiver_Body"]
P = np.array([(Mi @ v.co)[:] for v in b3.data.vertices])
zmin = float(P[:, 2].min()); print("ZMIN", zmin, "ZMAX", float(P[:, 2].max()))
rr = np.hypot(P[:, 0], P[:, 1]); th = np.arctan2(P[:, 1], P[:, 0])
zs = list(np.linspace(zmin + 0.004, Z_TOP, 21))
zs = [zmin] + zs
prof = np.zeros((len(zs), N_SEG))
ang0 = math.pi / 2
for i, z in enumerate(zs):
    for k in range(N_SEG):
        t = ang0 + 2 * math.pi * k / N_SEG
        d = np.abs(((th - t + math.pi) % (2 * math.pi)) - math.pi)
        m = (np.abs(P[:, 2] - z) < 0.016) & (d < math.pi / N_SEG * 1.3)
        prof[i, k] = np.percentile(rr[m], 35) if m.sum() >= 3 else np.nan
for i in range(len(zs)):       # preenche vazios e suaviza
    row = prof[i]
    if np.isnan(row).all(): prof[i] = prof[i - 1] if i else 0.0
    else:
        idx = np.arange(N_SEG); ok = ~np.isnan(row)
        prof[i] = np.interp(idx, idx[ok], row[ok], period=N_SEG)
for _ in range(2):
    pad = np.vstack([prof[:1], prof, prof[-1:]]); prof = (pad[:-2] + 2 * pad[1:-1] + pad[2:]) / 4
    prof = (np.roll(prof, 1, 1) + 2 * prof + np.roll(prof, -1, 1)) / 4
prof[0] *= 0.0            # ponta fecha em ponto
prof[-1] = np.minimum(prof[-1], 0.0415)
print("PROF r(z=top)", prof[-1].round(4)[:6], "mid", prof[len(zs) // 2].round(4)[:4])
# ---- malha ----
bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
zr = zs[-1] - zs[0]; rings = []
for i, z in enumerate(zs):
    if i == 0:
        rings.append([bm.verts.new((0, 0, z))]); continue
    rings.append([bm.verts.new((prof[i, k] * math.cos(ang0 + 2 * math.pi * k / N_SEG), prof[i, k] * math.sin(ang0 + 2 * math.pi * k / N_SEG), z)) for k in range(N_SEG)])
ctop = bm.verts.new((0, 0, zs[-1]))
def uv_of(i, k): return ((k / N_SEG), 0.02 + 0.96 * (zs[i] - zs[0]) / zr)
def setuv(f, items):
    for lp, (i, k) in zip(f.loops, items): lp[uvl].uv = uv_of(i, k)
for k in range(N_SEG):
    k2 = (k + 1) % N_SEG
    f = bm.faces.new((rings[0][0], rings[1][k2], rings[1][k])); setuv(f, [(0, k), (1, k + 1), (1, k)])
for i in range(1, len(zs) - 1):
    for k in range(N_SEG):
        k2 = (k + 1) % N_SEG
        f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
        setuv(f, [(i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)])
for k in range(N_SEG):
    k2 = (k + 1) % N_SEG
    f = bm.faces.new((rings[-1][k2], rings[-1][k], ctop)); 
    for lp in f.loops: lp[uvl].uv = (0.5, 0.99)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces: f.smooth = True
VERT = [tuple(v.co) for v in bm.verts]; FACE = [[v.index for v in f.verts] for f in bm.faces]; UVS = [[tuple(lp[uvl].uv) for lp in f.loops] for f in bm.faces]
bm.free()
# ---- cena de bake ----
bpy.ops.wm.open_mainfile(filepath=game)
g = [o for o in bpy.data.objects if o.type == 'MESH'][0]
g.data.transform(g.matrix_world); g.matrix_world.identity(); g.parent = None
me = bpy.data.meshes.new("SM_ArcherDark_Quiver_Body"); me.from_pydata(VERT, [], FACE); me.update()
uvd = me.uv_layers.new(name="UVMap")
for p, uu in zip(me.polygons, UVS):
    for li, u in zip(p.loop_indices, uu): uvd.data[li].uv = u
for p in me.polygons: p.use_smooth = True
low = bpy.data.objects.new("SM_ArcherDark_Quiver_Body", me)
bpy.context.scene.collection.objects.link(low); low.data.transform(M)
bpy.ops.wm.ply_import(filepath=high_ply); high = bpy.context.selected_objects[0]; high.name = "high"
for o in (high,):
    bpy.context.view_layer.objects.active = o; o.select_set(True); bpy.ops.object.shade_smooth()
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = False; sc.cycles.samples = 2
mat = bpy.data.materials.new("bk"); mat.use_nodes = True; low.data.materials.append(mat)
def bake(kind, name, src, **kw):
    img = bpy.data.images.new(name, TEX, TEX)
    if kind == 'NORMAL': img.colorspace_settings.name = 'Non-Color'
    n = mat.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img; mat.node_tree.nodes.active = n
    bpy.ops.object.select_all(action='DESELECT'); src.select_set(True); low.select_set(True); bpy.context.view_layer.objects.active = low
    bpy.ops.object.bake(type=kind, margin=16, margin_type='EXTEND', use_selected_to_active=True, cage_extrusion=kw.get("ext", 0.010),
                        max_ray_distance=kw.get("dist", 0.02), normal_space='TANGENT', pass_filter={'COLOR'} if kind == 'DIFFUSE' else set())
    img.filepath_raw = os.path.join(out, name + ".png"); img.file_format = 'PNG'; img.save(); mat.node_tree.nodes.remove(n); print("BAKED", name)
bake('NORMAL', "bake_normal_v4", high, ext=0.008, dist=0.014)
bake('DIFFUSE', "bake_color_v4", g, ext=0.012, dist=0.025)
low.data.materials.clear()
for o in list(bpy.data.objects):
    if o is not low: bpy.data.objects.remove(o)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "body_v4.blend"))
print("BODYDONE", len(low.data.polygons))
