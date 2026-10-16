"""Etapa 1 (Blender): limpar e normalizar a malha alta gerada por IA.

Remove pedacos soltos pequenos, escala para a altura do corpo (do chao ate a coroa do elmo, sem a pluma),
pes em z = 0, centro em x = 0 e y no centro dos pes, frente -Y. Grava work/high.ply e work/norm.json.
"""
import bpy, bmesh, numpy as np, sys, os
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
kept = [c for c in comps if len(c) >= cfg["min_component_faces"]]
drop = [f for c in comps if len(c) < cfg["min_component_faces"] for f in c]
removed_faces = len(drop)
bmesh.ops.delete(bm, geom=drop, context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.to_mesh(me); bm.free()

v = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', v); v = v.reshape(-1, 3)
if cfg.get("norm_from"):
    # modo por peca: mesma escala e deslocamento do corpo base (as pecas precisam ficar encaixadas no corpo)
    nrm = load_json(cfg["norm_from"])
    s = nrm["scale"]; cx, cy, zmin = nrm["offset_src"]
    v = (v - [0, 0, zmin]) * s
else:
    zmin = v[:, 2].min()
    s = cfg["body_height_m"] / (cfg["crown_z_src"] - zmin)
    v = (v - [0, 0, zmin]) * s
    feet = v[v[:, 2] < 0.08]
    cx = (v[:, 0].min() + v[:, 0].max()) / 2
    cy = (feet[:, 1].min() + feet[:, 1].max()) / 2
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
