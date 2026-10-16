"""Etapa 3 (Blender): malha de jogo (game_raw.ply) -> normais para fora, sombreamento suave e arestas vivas.

Grava work/game.blend e work/prep_report.json. As UV vem depois do esqueleto (s5), porque as ilhas seguem as
regioes do corpo (a regiao vem do osso dominante de cada vertice).
"""
import bpy, bmesh, math, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *

cfg = load_cfg()
clean_scene()
ob = load_ply_obj(wpath(cfg, "game_raw.ply"), "game")
me = ob.data
bm = bmesh.new(); bm.from_mesh(me)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
vol = bm.calc_volume(signed=True)
if vol < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    vol = -vol
bm.to_mesh(me); bm.free()
for p in me.polygons:
    p.use_smooth = True
bm = bmesh.new(); bm.from_mesh(me)
sharp = 0
for e in bm.edges:
    if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(cfg.get("sharp_angle_deg", 75)):
        e.smooth = False; sharp += 1
nonman = sum(1 for e in bm.edges if not e.is_manifold)
boundary = sum(1 for e in bm.edges if e.is_boundary)
bm.to_mesh(me); bm.free()
rep = dict(tris=len(me.polygons), verts=len(me.vertices), signed_volume=vol, sharp_edges=sharp,
           boundary_edges=boundary, nonmanifold_edges=nonman,
           surface_area_m2=round(sum(p.area for p in me.polygons), 3))
save_json(wpath(cfg, "prep_report.json"), rep)
bpy.ops.wm.save_as_mainfile(filepath=wpath(cfg, "game.blend"), compress=True)
print("S3", rep)
