"""Etapa 1 (Blender): limpar e normalizar a malha alta gerada por IA.

Remove pedacos soltos pequenos, escala para a altura do corpo (do chao ate a coroa do elmo, sem a pluma),
pes em z = 0, centro em x = 0 e y no centro dos pes, frente -Y. Grava work/high.ply e work/norm.json.
"""
import bpy, bmesh, math, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *

cfg = load_cfg()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=cfg["src_glb"])
ob = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
bpy.context.view_layer.objects.active = ob
ob.data.transform(ob.matrix_world)
ob.matrix_world.identity()
me = ob.data

# rotacao da fonte (frente -Y, alto +Z) e recortes por caixa (fracoes da caixa da fonte): corda do arco, fragmento solto
v0 = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', v0); v0 = v0.reshape(-1, 3)
if cfg.get("src_euler_deg"):
    from mathutils import Euler
    R = np.array(Euler([math.radians(a) for a in cfg["src_euler_deg"]], 'XYZ').to_matrix())
    v0 = v0 @ R.T
    me.vertices.foreach_set('co', v0.ravel()); me.update()
if cfg.get("delete_boxes_frac"):
    lo, hi = v0.min(0), v0.max(0)
    bm = bmesh.new(); bm.from_mesh(me)
    dead = []
    for f in bm.faces:
        c = (f.calc_center_median()[:] - lo) / (hi - lo)
        if any(all(b[2 * i] <= c[i] <= b[2 * i + 1] for i in range(3)) for b in cfg["delete_boxes_frac"]):
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(me); bm.free()

if cfg.get("mask_from_image"):
    # arco: a corda saiu como membrana. A imagem de entrada traz a membrana em cinza claro sem cor: o que nao cai no
    # arco (imagem sem o cinza, dilatada) sai da malha. Mapeia a caixa da malha na caixa do alfa da imagem (vista de frente).
    mi = cfg["mask_from_image"]
    img = bpy.data.images.load(cfg["single_view"])
    W_, H_ = img.size
    px_ = np.empty(W_ * H_ * 4, np.float32); img.pixels.foreach_get(px_)
    px_ = px_.reshape(H_, W_, 4)[::-1]                      # linha 0 em cima
    al = px_[..., 3] > 0.5
    gray = ((px_[..., :3].max(-1) - px_[..., :3].min(-1)) < 0.07) & (px_[..., :3].min(-1) > 0.58)
    bow = al & ~gray
    for _ in range(mi.get("dilate_px", 5)):
        bow = bow | np.roll(bow, 1, 0) | np.roll(bow, -1, 0) | np.roll(bow, 1, 1) | np.roll(bow, -1, 1)
    ys_, xs_ = np.where(al)
    x0, x1, y0, y1 = xs_.min(), xs_.max(), ys_.min(), ys_.max()
    lo, hi = v0.min(0), v0.max(0)
    bm = bmesh.new(); bm.from_mesh(me)
    dead = []
    for f in bm.faces:
        c = f.calc_center_median()
        u = x0 + (c.x - lo[0]) / (hi[0] - lo[0]) * (x1 - x0)
        w = y0 + (1 - (c.z - lo[2]) / (hi[2] - lo[2])) * (y1 - y0)
        ui, wi = int(np.clip(u, 0, W_ - 1)), int(np.clip(w, 0, H_ - 1))
        if not bow[wi, ui]:
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(me); bm.free()

# componentes conexos; descarta os pequenos
bm = bmesh.new(); bm.from_mesh(me)
seen, comps = set(), []
for f in bm.faces:
    if f.index in seen:
        continue
    st, fs = [f], []
    seen.add(f.index)
    while st:
        x = st.pop(); fs.append(x)
        for e in x.edges:
            for g in e.link_faces:
                if g.index not in seen:
                    seen.add(g.index); st.append(g)
    comps.append(fs)
thr = max(cfg.get("min_component_faces", 0), cfg.get("min_component_ratio", 0.005) * max(len(c) for c in comps))
kept = [c for c in comps if len(c) >= thr]
drop = [f for c in comps if len(c) < thr for f in c]
removed_faces = len(drop)
bmesh.ops.delete(bm, geom=drop, context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.to_mesh(me); bm.free()

v = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', v); v = v.reshape(-1, 3)
if cfg["kind"] == "static":
    # arma: comprimento (eixo Z) = body_height_m; origem na empunhadura (pivot_frac da altura, do pe do cabo); centro em x e y
    zmin = v[:, 2].min(); L = v[:, 2].max() - zmin
    s = cfg["body_height_m"] / L
    v = (v - [0, 0, zmin]) * s
    cx = (v[:, 0].min() + v[:, 0].max()) / 2; cy = (v[:, 1].min() + v[:, 1].max()) / 2
    v[:, 0] -= cx; v[:, 1] -= cy
    v[:, 2] -= cfg.get("pivot_frac", 0.25) * cfg["body_height_m"]
    zmin = 0.0
elif cfg.get("norm_from"):
    # modo por peca: mesma escala e deslocamento do corpo base (as pecas precisam ficar encaixadas no corpo)
    nrm = load_json(cfg["norm_from"])
    s = nrm["scale"]; cx, cy, zmin = nrm["offset_src"]
    v = (v - [0, 0, zmin]) * s
else:
    zmin = v[:, 2].min()
    top = v[:, 2].max() if cfg.get("height_ref") == "bbox" else cfg["crown_z_src"]
    s = cfg["body_height_m"] / (top - zmin)
    v = (v - [0, 0, zmin]) * s
    feet = v[v[:, 2] < 0.08 * cfg["size_scale"]]
    cx = (v[:, 0].min() + v[:, 0].max()) / 2
    cy = (feet[:, 1].min() + feet[:, 1].max()) / 2
if cfg["kind"] != "static":
    v[:, 0] -= cx; v[:, 1] -= cy      # cx, cy ja em metros (apos a escala)
me.vertices.foreach_set('co', v.ravel()); me.update()
for p in me.polygons:
    p.use_smooth = True

bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
bpy.ops.wm.ply_export(filepath=wpath(cfg, "high.ply"), export_selected_objects=True, export_normals=False,
                      export_uv=False, export_colors='NONE', ascii_format=False)
info = dict(scale=s, offset_src=[cx, cy, zmin], components_total=len(comps), components_kept=len(kept),
            faces_removed=removed_faces, faces_high=len(me.polygons), bbox_min=v.min(0).tolist(), bbox_max=v.max(0).tolist(),
            height_total=float(v[:, 2].max()), crown_z=cfg["body_height_m"])
save_json(wpath(cfg, "norm.json"), info)
print("S1", info)
