"""Conferencia do heroi modular: monta as combinacoes (completo, sem elmo, sem luvas, sem botas, so corpo) e mede buracos nas juntas.

Buraco = raio ortografico cujo primeiro acerto e uma face de tras (a camera enxerga o interior da malha por uma fresta).
Mede em 8 direcoes (frente, costas, lados, 4 diagonais com 35 graus de elevacao), na pose de repouso e na pose de teste.
Tambem confere: cada peca fechada (tampas), triangulos por peca contra o teto do 04 17.4, soma do pior caso e distancia
maxima entre vertices de borda compartilhados entre pecas na pose (0 = nao abre). Grava final/verify_modular_report.json.
Uso: blender -b --factory-startup -P verify_modular.py -- mod_warrior_cut
"""
import bpy, bmesh, math, sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mdl_modular import *
from mathutils import Vector
from mathutils.bvhtree import BVHTree

cfg = load_cfg()
arm, pieces, regs = assemble(cfg)
hides = cfg["hides"]
CEIL = {"Head": 1400, "Chest": 2200, "Hands": 750, "Legs": 1200, "Feet": 750}   # docs/04 17.4
report = dict(pecas={}, combos={})

for s, o in pieces.items():
    bm = bmesh.new(); bm.from_mesh(o.data)
    open_edges = sum(1 for e in bm.edges if e.is_boundary or not e.is_manifold)
    bm.free()
    report["pecas"][o.name] = dict(tris=len(o.data.polygons), teto_17_4=CEIL[s], acima_do_teto=len(o.data.polygons) > CEIL[s], arestas_abertas=open_edges)
report["corpo_regioes_tris"] = {r: len(o.data.polygons) for r, o in regs.items()}


def world_mesh(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    V, F, off = [], [], 0
    for o in objs:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        mw = o.matrix_world
        v = [tuple(mw @ x.co) for x in me.vertices]
        f = [tuple(i + off for i in p.vertices) for p in me.polygons]
        V += v; F += f; off += len(v)
        ev.to_mesh_clear()
    return V, F


def hole_scan(objs):
    V, F = world_mesh(objs)
    bvh = BVHTree.FromPolygons(V, F)
    A = np.array(V)
    lo, hi = A.min(0), A.max(0); c = (lo + hi) / 2
    R = 0.5 * float(np.linalg.norm(hi - lo)) * 1.05
    N = 120
    res = {}
    dirs = {"frente": (0, 1, 0), "costas": (0, -1, 0), "esq": (-1, 0, 0), "dir": (1, 0, 0)}
    for k in (45, 135, 225, 315):
        a = math.radians(k); e = math.radians(35)
        dirs[f"diag{k}"] = (math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), -math.sin(e))
    for name, d in dirs.items():
        d = Vector(d).normalized()
        up = Vector((0, 0, 1)); r = d.cross(up)
        r = r.normalized() if r.length > 1e-6 else Vector((1, 0, 0))
        u = r.cross(d).normalized()
        hits = back = 0
        for iu in range(N):
            for iv in range(N):
                p = Vector(c) + r * ((iu / (N - 1) - 0.5) * 2 * R) + u * ((iv / (N - 1) - 0.5) * 2 * R) - d * (2 * R)
                h = bvh.ray_cast(p, d)
                if h[0] is None:
                    continue
                hits += 1
                if h[1].dot(d) > 0.05:
                    back += 1
        res[name] = round(100 * back / max(hits, 1), 3)
    return res


# referencia: o proprio heroi vestido intacto (SK_<Heroi>.blend). Aberturas naturais (capuz aberto, manga) aparecem como face de
# tras tambem nele; o que conta como buraco de junta e o excesso sobre essa referencia, vista a vista.
import bpy as _b
with _b.data.libraries.load(cfg["src_blend"]) as (_s, _d):
    _d.objects = [cfg["src_mesh"]]
orig = _d.objects[0]
_b.context.scene.collection.objects.link(orig)
orig.parent = None
for _m in list(orig.modifiers):
    orig.modifiers.remove(_m)
baseline = hole_scan([orig])
_b.data.objects.remove(orig)
report["referencia_heroi_intacto_pct_por_vista"] = baseline

for pose in ("repouso", "teste"):
    if pose == "teste":
        apply_test_pose(arm)
    for cn, worn in COMBOS.items():
        vis = set_combo(pieces, regs, worn, hides)
        objs = [o for s, o in pieces.items() if s in worn] + [regs[r] for r in vis]
        res = hole_scan(objs)
        tri = sum(len(o.data.polygons) for o in objs)
        exc = {k: round(res[k] - baseline[k], 3) for k in res}
        report["combos"].setdefault(cn, {})[pose] = dict(regioes_do_corpo_visiveis=vis, triangulos=tri, face_de_tras_pct_por_vista=res,
                                                         excesso_sobre_intacto_por_vista=exc, pior_vista_pct=max(res.values()),
                                                         pior_excesso_pct=max(exc.values()))

# vertices de borda compartilhados entre pecas: distancia na pose (repouso: mesma posicao exata)
from mathutils.kdtree import KDTree
clear_pose(arm)
rest_pos = {s_: world_mesh([o])[0] for s_, o in pieces.items()}
apply_test_pose(arm)
posed = {s_: world_mesh([o])[0] for s_, o in pieces.items()}
slots = list(pieces)
mx = 0.0; shared = 0
for i in range(len(slots)):
    for j in range(i + 1, len(slots)):
        kd = KDTree(len(rest_pos[slots[j]]))
        for k, p in enumerate(rest_pos[slots[j]]):
            kd.insert(p, k)
        kd.balance()
        for k, p in enumerate(rest_pos[slots[i]]):
            _, kk, d = kd.find(p)
            if d < 1e-5:
                shared += 1
                mx = max(mx, (Vector(posed[slots[i]][k]) - Vector(posed[slots[j]][kk])).length)
report["juntas"] = dict(vertices_compartilhados=shared, distancia_maxima_na_pose_m=round(mx, 6))
worst = max(v[p]["pior_excesso_pct"] for k, v in report["combos"].items() if k != "so_corpo" for p in v)
total_worst = sum(p["tris"] for p in report["pecas"].values())
report["resumo"] = dict(pior_excesso_de_face_de_tras_sobre_intacto_pct=round(worst, 3), soma_triangulos_pecas=total_worst,
                        pecas_acima_do_teto=[n for n, p in report["pecas"].items() if p["acima_do_teto"]],
                        pecas_com_arestas_abertas=[n for n, p in report["pecas"].items() if p["arestas_abertas"]],
                        sem_buracos=worst < 1.0 and mx < 1e-4)
save_json(fpath(cfg, "verify_modular_report.json"), report)
print("VMOD", json.dumps(report["resumo"]), report["juntas"])
for cn, v in report["combos"].items():
    print(" ", cn, {p: v[p]["pior_excesso_pct"] for p in v})
