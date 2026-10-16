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
if not cfg.get("keep_normals"):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
vol = bm.calc_volume(signed=True)
if vol < 0 and not cfg.get("keep_normals"):
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    vol = -vol
bm.to_mesh(me); bm.free()
culled = 0
if cfg.get("cull_inner"):
    # peca modular: o miolo oco (face de dentro do casco) nunca aparece, porque o corpo preenche a cavidade. Uma face fica
    # se algum raio de fora para a sua normal escapa sem bater na peca nem no corpo (oclusor).
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    bm = bmesh.new(); bm.from_mesh(me)
    pv = [v.co.copy() for v in bm.verts]; pf = [[v.index for v in f.verts] for f in bm.faces]
    occ_v, occ_f = [], []
    if cfg.get("occluder_ply"):
        bpy.ops.wm.ply_import(filepath=cfg["occluder_ply"])
        oc = bpy.context.selected_objects[0]
        occ_v = [v.co.copy() for v in oc.data.vertices]; occ_f = [list(p.vertices) for p in oc.data.polygons]
        bpy.data.objects.remove(oc)
    allv = pv + occ_v
    allf = pf + [[i + len(pv) for i in f] for f in occ_f]
    bvh = BVHTree.FromPolygons([tuple(v) for v in allv], allf)
    NDIR = 48
    k = (np.arange(NDIR) + 0.5) / NDIR
    zz = 1 - 2 * k; rr = np.sqrt(1 - zz ** 2); ph = np.arange(NDIR) * 2.399963
    dirs = [Vector((rr[i] * math.cos(ph[i]), rr[i] * math.sin(ph[i]), zz[i])) for i in range(NDIR)]
    dead, flip = [], []
    K = cfg["size_scale"]
    for f in bm.faces:
        c, n = f.calc_center_median(), f.normal
        esc = {1: 0, -1: 0}
        for sg in (1, -1):
            o = c + n * (sg * 0.002 * K)
            for d in dirs:
                if sg * d.dot(n) > 0.2 and bvh.ray_cast(o, d, 100.0)[0] is None:
                    esc[sg] += 1
        if esc[1] == 0 and esc[-1] == 0:
            dead.append(f)
        elif esc[-1] > esc[1]:
            flip.append(f)        # o lado de fora e o oposto a normal gravada: vira a face (normal para fora)
    bmesh.ops.reverse_faces(bm, faces=flip)
    culled = len(dead)
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
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
rep = dict(culled_inner_faces=culled, flipped_faces=len(flip) if cfg.get('cull_inner') else 0, tris=len(me.polygons), verts=len(me.vertices), signed_volume=vol, sharp_edges=sharp,
           boundary_edges=boundary, nonmanifold_edges=nonman,
           surface_area_m2=round(sum(p.area for p in me.polygons), 3))
save_json(wpath(cfg, "prep_report.json"), rep)
bpy.ops.wm.save_as_mainfile(filepath=wpath(cfg, "game.blend"), compress=True)
print("S3", rep)
