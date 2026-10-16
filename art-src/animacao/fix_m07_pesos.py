"""Corrige os pesos do Arqueiro Espectral (m07): ilhas soltas (farrapos da capa e pedacos flutuantes) nao podem
herdar peso de osso distante (maos/bracos). Cada ilha que nao e o corpo principal passa a seguir so Hips/Spine/Chest
(mistura linear pela altura do vertice). Regrava final/SK_Enemy_GhostArcher.blend e .fbx (mesmo export do pipeline).
Uso: blender -b --factory-startup -P fix_m07_pesos.py   (depois: verify_modelo.py m07_arqueiro_espectral)"""
import bpy, bmesh, sys, os
sys.path.insert(0, "D:/openclaude/EchoesOfTheShatter/art-src/modelos/scripts")
from mdl_common import *
from mdl_blender import *
sys.argv = [sys.argv[0], "--", "m07_arqueiro_espectral"]
cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
blend = fpath(cfg, cfg["asset"] + ".blend")
bpy.ops.wm.open_mainfile(filepath=blend)
ob = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
me = ob.data
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
seen, isl = set(), []
for v in bm.verts:
    if v.index in seen:
        continue
    st, comp = [v], []
    seen.add(v.index)
    while st:
        x = st.pop(); comp.append(x.index)
        for e in x.link_edges:
            o = e.other_vert(x)
            if o.index not in seen:
                seen.add(o.index); st.append(o)
    isl.append(comp)
isl.sort(key=len, reverse=True)
body = isl[0]
centers = [("Hips", 0.875), ("Spine", 1.035), ("Chest", 1.21)]   # altura (m) do centro de cada osso do tronco
groups = {n: ob.vertex_groups[n] for n, _ in centers}
fixed = 0
for comp in isl[1:]:
    for i in comp:
        for g in list(me.vertices[i].groups):
            ob.vertex_groups[g.group].remove([i])
        z = me.vertices[i].co.z
        if z <= centers[0][1]:
            w = {"Hips": 1.0}
        elif z >= centers[-1][1]:
            w = {"Chest": 1.0}
        else:
            for (na, za), (nb, zb) in zip(centers, centers[1:]):
                if za <= z <= zb:
                    t = (z - za) / (zb - za)
                    w = {na: 1 - t, nb: t}
                    break
        for n, wt in w.items():
            if wt > 1e-4:
                groups[n].add([i], wt, 'REPLACE')
        fixed += 1
print("FIX islands", len(isl) - 1, "verts", fixed)
for o in bpy.context.scene.objects:
    o.select_set(False)
fbx = fpath(cfg, cfg["asset"] + ".fbx")
gb_rig.export_fbx_rigged(arm, [ob], fbx)
bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
print("S8 fix ok", fbx)
