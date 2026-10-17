"""Modular (Blender): corta o heroi vestido (SK_Warrior, malha fechada, pintada, com pesos) em 5 pecas: Head, Chest, Hands, Legs, Feet.

Cada vertice recebe a peca pelo osso dominante e por planos de corte (cintura, bota); a face fica com a maioria dos
vertices e um filtro de maioria alisa a fronteira. As pecas guardam UV, atlas e pesos do original (textura por conjunto:
T_<Heroi>_<Conjunto>_BC/M) e o esqueleto compartilhado. Cada borda cortada recebe uma tampa (cap) fechando o oco, com UV em
um ponto da borda vizinha (cor vizinha). Grava work/modular_work.blend (pecas + esqueleto) e as texturas do conjunto.
"""
import bpy, bmesh, numpy as np, sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_blender import *
from mathutils import Vector
from mathutils.kdtree import KDTree

cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
bpy.ops.wm.open_mainfile(filepath=cfg["src_blend"])
src = bpy.data.objects[cfg["src_mesh"]]
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
me = src.data
gname = {vg.index: vg.name for vg in src.vertex_groups}
CUT = cfg["cuts"]
PIECES = ["Head", "Chest", "Hands", "Legs", "Feet"]
BONE_GROUP = {"Head": "Head", "Neck": "Head", "LeftLowerArm": "Hands", "RightLowerArm": "Hands", "LeftHand": "Hands", "RightHand": "Hands",
              "LeftUpperArm": "Chest", "RightUpperArm": "Chest", "LeftShoulder": "Chest", "RightShoulder": "Chest",
              "Foot": "Feet", "Toes": "Feet"}
TORSO_LEGS = {"Chest", "Spine", "Hips", "LeftUpperLeg", "RightUpperLeg", "LeftLowerLeg", "RightLowerLeg"}


def vlabel(v):
    g = max(v.groups, key=lambda g: g.weight)
    n = gname[g.group]
    z = v.co.z
    if n.endswith("Foot") or n.endswith("Toes"):
        return "Feet"
    if n in BONE_GROUP:
        return BONE_GROUP[n]
    if n in TORSO_LEGS:
        if z < CUT["boot_z"] and "Leg" in n:
            return "Feet"
        return "Chest" if z >= CUT["waist_z"] else "Legs"
    return "Chest"


vl = [PIECES.index(vlabel(v)) for v in me.vertices]
fl = np.array([np.bincount([vl[i] for i in p.vertices], minlength=5).argmax() for p in me.polygons])
adj = {}
for e in me.edges:
    pass
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
nbr = [[g.index for e in f.edges for g in e.link_faces if g.index != f.index] for f in bm.faces]
for _ in range(2):   # filtro de maioria
    new = fl.copy()
    for i in range(len(fl)):
        c = np.bincount([fl[j] for j in nbr[i]] + [fl[i]], minlength=5)
        if c.argmax() != fl[i] and c.max() >= 3:
            new[i] = c.argmax()
    fl = new
bm.free()
counts_before = {p: int((fl == i).sum()) for i, p in enumerate(PIECES)}

arm_ob = arm
objs = {}
caps = {}
asset = lambda p: f"SK_{cfg['hero']}_{p}_{cfg['set_name']}"
mat = src.data.materials[0]
mat.name = f"M_{cfg['hero']}_{cfg['set_name']}"
for i, pn in enumerate(PIECES):
    o2 = src.copy(); o2.data = src.data.copy(); o2.name = asset(pn); o2.data.name = asset(pn)
    bpy.context.scene.collection.objects.link(o2)
    bm = bmesh.new(); bm.from_mesh(o2.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if fl[f.index] != i], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    uvl = bm.loops.layers.uv.active
    deform = bm.verts.layers.deform.active
    # tampa nas bordas cortadas
    bedges = [e for e in bm.edges if e.is_boundary]
    n_old_faces = len(bm.faces)
    old_faces = set(f.index for f in bm.faces)
    # componentes de arestas de borda (por vertices compartilhados) e um leque de triangulos por componente
    par = {}
    def find(x):
        while par.setdefault(x, x) != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for e in bedges:
        par[find(e.verts[0].index)] = find(e.verts[1].index)
    comps = {}
    for e in bedges:
        comps.setdefault(find(e.verts[0].index), []).append(e)
    newf = []
    for key, es in comps.items():
        vs = {v for e in es for v in e.verts}
        ctr = sum((v.co for v in vs), Vector()) / len(vs)
        cv = bm.verts.new(ctr)
        acc = {}
        for v in vs:
            for g, w in v[deform].items():
                acc[g] = acc.get(g, 0.0) + w / len(vs)
        for g, w in acc.items():
            cv[deform][g] = w
        for e in es:
            f0 = e.link_faces[0]
            order = [l.vert for l in f0.loops]
            va, vb = e.verts
            # direcao da aresta no laco da face vizinha: a tampa usa a direcao oposta (normal para fora)
            fwd = None
            for l in f0.loops:
                if l.edge == e:
                    fwd = (l.vert, l.link_loop_next.vert)
                    uvs = [l[uvl].uv.copy(), l.link_loop_next[uvl].uv.copy()]
            try:
                nf = bm.faces.new((fwd[1], fwd[0], cv))
            except ValueError:
                continue
            uvm = (uvs[0] + uvs[1]) / 2
            for l in nf.loops:
                l[uvl].uv = uvm
            newf.append(nf)
    # laços complexos (componente de borda nao simples): o leque deixa arestas abertas; triangulate_fill cobre o resto
    rest = [e for e in bm.edges if e.is_boundary]
    extra = 0
    if rest:
        try:
            tf = bmesh.ops.triangle_fill(bm, edges=rest, use_beauty=True)["geom"]
            nf2 = [g for g in tf if isinstance(g, bmesh.types.BMFace)]
            kd = KDTree(len(bedges))
            for k, e in enumerate(bedges):
                kd.insert((e.verts[0].co + e.verts[1].co) / 2, k)
            kd.balance()
            for f in nf2:
                _, k, _ = kd.find(f.calc_center_median())
                e = bedges[k]
                # UV da aresta de borda original mais proxima (da face vizinha que sobrou)
                uvm = None
                for ff in e.link_faces:
                    if len(ff.loops):
                        ls = [l for l in ff.loops if l.vert in e.verts]
                        if len(ls) == 2:
                            uvm = (ls[0][uvl].uv + ls[1][uvl].uv) / 2
                            break
                if uvm is not None:
                    for l in f.loops:
                        l[uvl].uv = uvm
            extra = len(nf2)
        except Exception as ex:
            print("triangle_fill falhou", pn, ex)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    left = sum(1 for e in bm.edges if e.is_boundary or not e.is_manifold)
    caps[pn] = dict(boundary_edges=len(bedges), cap_tris=len(newf), triangle_fill_extra=extra, arestas_abertas_restantes=left)
    bm.to_mesh(o2.data); bm.free()
    o2.data.materials.clear(); o2.data.materials.append(mat)
    for p in o2.data.polygons:
        p.use_smooth = True
    objs[pn] = o2
bpy.data.objects.remove(src)
# textura do conjunto
os.makedirs(cfg["final_dir"], exist_ok=True)
tex = f"{cfg['hero']}_{cfg['set_name']}"
for suf in ("BC", "M"):
    shutil.copy(f"{cfg['src_tex_dir']}/T_{cfg['hero']}_{suf}.png", f"{cfg['final_dir']}/T_{tex}_{suf}.png")
img = bpy.data.images.load(f"{cfg['final_dir']}/T_{tex}_BC.png")
for n in mat.node_tree.nodes:
    if n.type == 'TEX_IMAGE':
        n.image = img
bpy.ops.wm.save_as_mainfile(filepath=wpath(cfg, "modular_work.blend"), compress=True)
rep = dict(faces_por_peca={p: len(objs[p].data.polygons) for p in PIECES}, faces_antes_filtro=counts_before, caps=caps)
save_json(wpath(cfg, "cut_report.json"), rep)
print("MCUT", rep)
