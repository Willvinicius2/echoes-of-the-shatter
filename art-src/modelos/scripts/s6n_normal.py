"""Etapa 6n (Blender, CPU): normal map em espaco tangente (tex_size) da malha ALTA assada na UV da malha de jogo.

Cada texel acha o ponto mais externo da malha alta (raio de fora para dentro ao longo da normal; se errar, o mais
proximo); a normal da malha alta nesse ponto vai para o espaco tangente da malha de jogo (T = dP/du, B = dP/dv da UV,
ortogonalizados pela normal de canto; convencao OpenGL/Godot: Y+ = dP/dv). Texel cuja normal alta desvia mais que
normal_max_deg da baixa fica plano. Grava work/bake_normal.png (e normal_report no bake_report). So um processo do Blender.
"""
import bpy, numpy as np, sys, os, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mathutils import Vector
from mathutils.bvhtree import BVHTree

cfg = load_cfg()
SIZE = cfg["tex_size"]
t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=wpath(cfg, "game_uv.blend"))
low = bpy.data.objects["game"]
g = texel_geometry(low, SIZE)
me = low.data
uv = np.empty(len(me.loops) * 2); me.uv_layers[0].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
tl = np.array([t.loops[:] for t in me.loop_triangles], dtype=np.int64)
tv = np.array([t.vertices[:] for t in me.loop_triangles], dtype=np.int64)
co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
# tangente e bitangente por triangulo (v para cima)
p0, p1, p2 = co[tv[:, 0]], co[tv[:, 1]], co[tv[:, 2]]
u0, u1, u2 = uv[tl[:, 0]], uv[tl[:, 1]], uv[tl[:, 2]]
e1, e2, d1, d2 = p1 - p0, p2 - p0, u1 - u0, u2 - u0
det = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
det = np.where(np.abs(det) < 1e-12, 1e-12, det)
Tt = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / det[:, None]
Bt = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / det[:, None]

high = load_ply_obj(wpath(cfg, "high.ply"), "high")
hv, hf = mesh_arrays(high)
bvh = BVHTree.FromPolygons([tuple(v) for v in hv], [tuple(f) for f in hf])
K = cfg["size_scale"]
valid = g["valid"]
ys, xs = np.where(valid)
nrm_out = np.zeros((SIZE, SIZE, 3), np.float32); nrm_out[..., 2] = 1.0
maxdev = math.cos(math.radians(cfg.get("normal_max_deg", 70)))
flat = 0
for y, x in zip(ys, xs):
    p, n = Vector(g["pos"][y, x]), Vector(g["nrm"][y, x])
    h = bvh.ray_cast(p + n * 0.05 * K, -n, 0.12 * K)
    if h[0] is None:
        h = bvh.find_nearest(p, 0.08 * K)
    if h[0] is None:
        flat += 1; continue
    hn = h[1]
    if hn.dot(n) < 0:
        hn = -hn
    if hn.dot(n) < maxdev:
        flat += 1; continue
    k = g["tri"][y, x]
    T = Tt[k]; B = Bt[k]
    T = T - np.array(n) * np.dot(T, np.array(n)); T /= max(np.linalg.norm(T), 1e-9)
    B = np.cross(np.array(n), T) * (1.0 if np.dot(np.cross(np.array(n), T), B) >= 0 else -1.0)
    nrm_out[y, x] = (np.dot(hn, T), np.dot(hn, B), np.dot(hn, n))
nrm_out /= np.maximum(np.linalg.norm(nrm_out, axis=-1, keepdims=True), 1e-9)
def gblur(a, sig):
    r = max(1, int(3 * sig)); k = np.exp(-0.5 * (np.arange(-r, r + 1) / sig) ** 2); k /= k.sum()
    for ax in (0, 1):
        pad = [(0, 0)] * a.ndim; pad[ax] = (r, r)
        ap = np.pad(a, pad, mode="edge")
        a = sum(k[i] * np.take(ap, np.arange(i, i + a.shape[ax]), axis=ax) for i in range(len(k)))
    return a
sm = gblur(nrm_out, cfg.get("normal_blur", 0.8))
sm /= np.maximum(np.linalg.norm(sm, axis=-1, keepdims=True), 1e-9)
nrm_out, _ = dilate(sm, valid, 16)
img = np.clip(nrm_out * 0.5 + 0.5, 0, 1)
fs = np.concatenate([nrm_out[valid][:, :2]], 0)
save_png(img.astype(np.float32), wpath(cfg, "bake_normal.png"))
rep = load_json(wpath(cfg, "bake_report.json"), {})
rep["normal"] = dict(texels=int(valid.sum()), planos=int(flat), desvio_xy_medio=round(float(np.abs(fs).mean()), 4), seconds=round(time.time() - t0))
save_json(wpath(cfg, "bake_report.json"), rep)
print("S6n", rep["normal"])
