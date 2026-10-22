"""Capuz do Arqueiro, passada 2 (festao do barrado, volume da mascara de pano, silhueta redonda).
Entrada: GLB original do repo. Saida: godot/art/models/personagens/arqueiro/Arqueiro_Capuz.glb.  Rodar via regenerar_rodada7.py (extract.py -> tex2.py -> build2.py)."""
import bpy, bmesh, numpy as np, math, os
from mathutils import Vector, kdtree
import os as _os
_AQUI = _os.path.dirname(_os.path.abspath(__file__))
_R7 = _os.path.dirname(_AQUI)
_RAIZ = _os.path.abspath(_os.path.join(_R7, "..", "..", "..", ".."))
FONTE = _os.environ.get("ARQ_FONTE_ORIG", _os.path.join(_R7, "_fonte_original"))   # GLBs/texturas pre-polida (somente leitura)
SAIDA = _os.environ.get("ARQ_SAIDA", _os.path.join(_RAIZ, "godot", "art", "models", "personagens", "arqueiro"))
TRAB = _os.environ.get("ARQ_TRAB", _os.path.join(_R7, "_trabalho", "capuz"))   # intermediarios (fora do git)
_os.makedirs(TRAB, exist_ok=True)
SRC = os.path.join(FONTE, "Arqueiro_Capuz.glb")
OUT = os.environ.get("OUT", os.path.join(SAIDA, "Arqueiro_Capuz.glb"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
CX, CY = 0.0, 0.11
ZSUB = float(os.environ.get("ZSUB", 1.12))     # abaixo disto o capuz ganha um loop extra (barrado)
KF = int(os.environ.get("KF", 5))              # festoes ao redor
AH = float(os.environ.get("AH", 0.065))        # profundidade do festao
AR = float(os.environ.get("AR", 0.030))        # amplitude radial das pregas no barrado
TAU = int(os.environ.get("TAU", 6))            # passes de suavizacao (Taubin)


def sstep(a, b, t):
    t = np.clip((t - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
cap = bpy.data.objects["SK_Archer_Capuz"]
ros = bpy.data.objects["SK_Archer_Rosto"]
for o in [o for o in bpy.data.objects if o.name.startswith("SK_Archer_Gola") or o.name.startswith("Icosphere")]:
    bpy.data.objects.remove(o)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


ANTES = {o.name: tris(o) for o in bpy.data.objects if o.type == "MESH"}


def clear_custom_normals(ob):
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.select_set(False)


def head_only(ob):
    ob.vertex_groups.clear() if False else None
    for g in list(ob.vertex_groups):
        if g.name != "Head":
            ob.vertex_groups.remove(g)
    vg = ob.vertex_groups["Head"]
    vg.add([v.index for v in ob.data.vertices], 1.0, "REPLACE")


# ============================================================ CAPUZ
me = cap.data
bm = bmesh.new(); bm.from_mesh(me)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
# moldura de osso (mat 1) fica imovel: kd-tree dos seus vertices
frame_v = [v.co.copy() for f in bm.faces if f.material_index == 1 for v in f.verts]
kd = kdtree.KDTree(len(frame_v))
for i, p in enumerate(frame_v):
    kd.insert(p, i)
kd.balance()
# loop extra no barrado: subdivide as faces do capuz abaixo de ZSUB
sel = [f for f in bm.faces if f.material_index == 0 and f.calc_center_median().z < ZSUB]
edges = list({e for f in sel for e in f.edges})
bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
# 0) alisa a altura do barrado ao longo da borda (o original tem degraus duros) e espalha o ajuste para cima
def build_nb():
    nbr = {}
    for e in bm.edges:
        a_, b_ = e.verts
        if any(f.material_index == 0 for f in e.link_faces):
            nbr.setdefault(a_.index, set()).add(b_.index); nbr.setdefault(b_.index, set()).add(a_.index)
    return nbr
nb0 = build_nb()
bnd = {}
for e in bm.edges:
    if e.is_boundary and any(f.material_index == 0 for f in e.link_faces):
        a_, b_ = e.verts
        if a_.co.z < 1.16 and b_.co.z < 1.16:
            bnd.setdefault(a_.index, []).append(b_.index); bnd.setdefault(b_.index, []).append(a_.index)
bnd = {i: n for i, n in bnd.items() if len(n) == 2 and kd.find(bm.verts[i].co)[2] > 0.03}
zs0 = {i: bm.verts[i].co.z for i in bnd}; zz = dict(zs0)
for it in range(int(os.environ.get("BP", 14))):
    zz = {i: 0.5 * zz[i] + 0.25 * (zz.get(a_, zs0.get(a_, bm.verts[a_].co.z)) + zz.get(b_, zs0.get(b_, bm.verts[b_].co.z))) for i, (a_, b_) in bnd.items()}
delta = {i: zz[i] - zs0[i] for i in bnd}
dist = {i: 0 for i in bnd}; front = list(bnd); dd = dict(delta)
for k in range(1, 5):
    nxt = []
    for i in front:
        for j in nb0.get(i, ()):
            if j not in dist:
                dist[j] = k; dd[j] = dd[i]; nxt.append(j)
    front = nxt
for i, k in dist.items():
    if k > 0:
        bm.verts[i].co.z += dd[i] * 0.5 * (1 + math.cos(math.pi * k / 5))
    elif k == 0:
        bm.verts[i].co.z += dd[i]
hv = sorted({v.index for f in bm.faces if f.material_index == 0 for v in f.verts})
hidx = np.array(hv)
co = np.array([bm.verts[i].co[:] for i in hv], dtype=float)
x, y, z = co[:, 0], co[:, 1] - CY, co[:, 2]
th = np.arctan2(y, x); r = np.hypot(x, y)
back = sstep(-0.4, 0.35, np.sin(th))
hz = sstep(1.42, 1.10, z)
s = back * hz
# 1) raio suavizado em theta/z (some os lobulos duros do original)
rs = r.copy()
for i in np.where(s > 0.01)[0]:
    dth = np.abs(np.angle(np.exp(1j * (th - th[i]))))
    dz = np.abs(z - z[i])
    w = np.exp(-(dth / 0.40) ** 2 - (dz / 0.07) ** 2) * (back > 0.01)
    rs[i] = (w * r).sum() / w.sum()
rn = r + (rs - r) * s
# 2) pregas: KF festoes; vale na costura (theta=90 graus)
f_ = -np.cos(KF * (th - math.pi / 2))            # -1 na costura (vale), +1 crista
wlow = sstep(1.42, 1.02, z)                      # pregas crescem para o barrado
rn = rn + AR * f_ * s * (0.25 + 0.75 * wlow)
# 3) barrado em festao macio: crista desce, vale sobe; so abaixo de 1.22
backh = sstep(-0.50, 0.20, np.sin(th))
lowm = sstep(1.24, 1.02, z) * backh
fz = 0.5 + 0.5 * f_ + 0.05 * np.cos(2 * KF * (th - math.pi / 2) + 0.6)
zn = z - AH * (fz - 0.35) * lowm
# alarga um pouco o barrado (caimento de pano)
rn = rn * (1 + 0.05 * sstep(1.2, 1.0, z) * back)
new = co.copy()
new[:, 0] = CX + rn * np.cos(th); new[:, 1] = CY + rn * np.sin(th); new[:, 2] = zn
for k, i in enumerate(hv):
    bm.verts[i].co = new[k]
# 4) suavizacao Taubin para arredondar a silhueta (pinos: moldura de osso e ponta de baixo da abertura)
nb = {i: set() for i in hv}
for e in bm.edges:
    a, b = e.verts
    if a.index in nb and b.index in nb and any(f.material_index == 0 for f in e.link_faces):
        nb[a.index].add(b.index); nb[b.index].add(a.index)
pinw = {}
for i in hv:
    p = bm.verts[i].co
    d = kd.find(p)[2]
    pinw[i] = float(sstep(0.012, 0.10, d))     # 0 junto da moldura, 1 longe
TOPW = lambda p: float(sstep(1.56, 1.40, p.z))  # a ponta do capuz mantem o flop original
for it in range(TAU):
    for lam in (0.5, -0.53):
        pos = {i: bm.verts[i].co.copy() for i in hv}
        for i in hv:
            w = pinw[i]
            if w <= 0 or not nb[i]:
                continue
            avg = sum((pos[j] for j in nb[i]), Vector()) / len(nb[i])
            bm.verts[i].co = pos[i] + (avg - pos[i]) * lam * w
bm.normal_update()
bm.to_mesh(me); bm.free()
clear_custom_normals(cap)
head_only(cap)

# ============================================================ GOLA
mat = cap.data.materials[0]
Z0, Z1 = 0.93, 1.13
RX0, RY0, RX1, RY1 = 0.21, 0.20, 0.145, 0.14
LADOS, ANEIS = 16, 4
gb = bmesh.new(); aneis = []
for j in range(ANEIS):
    t = j / (ANEIS - 1); zz = Z0 + (Z1 - Z0) * t
    e = t * t * (3 - 2 * t); k = 1 + 0.10 * math.exp(-t * 7)
    rx = (RX0 + (RX1 - RX0) * e) * k; ry = (RY0 + (RY1 - RY0) * e) * k
    ring = []
    for i in range(LADOS):
        a = 2 * math.pi * i / LADOS
        f = 1 + 0.07 * math.cos(4 * a + 0.5) * (1 - t * 0.5) + 0.03 * math.cos(3 * a) * (1 - t)
        zh = zz + 0.018 * math.cos(4 * a + 0.5) * (1 - t) ** 2
        ring.append(gb.verts.new((CX + rx * f * math.cos(a), CY + ry * f * math.sin(a), zh)))
    aneis.append(ring)
for j in range(ANEIS - 1):
    for i in range(LADOS):
        gb.faces.new((aneis[j][i], aneis[j][(i + 1) % LADOS], aneis[j + 1][(i + 1) % LADOS], aneis[j + 1][i]))
uvl = gb.loops.layers.uv.new("UVMap")
pos2ij = {}
for j in range(ANEIS):
    for i, v in enumerate(aneis[j]):
        pos2ij[v] = (i, j)
for f in gb.faces:
    ids = [pos2ij[l.vert] for l in f.loops]
    for l, (i, j) in zip(f.loops, ids):
        ii = i if not (i == 0 and any(q == LADOS - 1 for q, _ in ids)) else LADOS
        m = 1 - abs(2 * ii / LADOS - 1)
        l[uvl].uv = (0.10 + 0.80 * m, 0.60 - 0.40 * (j / (ANEIS - 1)))
bmesh.ops.recalc_face_normals(gb, faces=list(gb.faces))
tg = bpy.data.meshes.new("SK_Archer_Gola"); gb.to_mesh(tg); gb.free()
for p in tg.polygons:
    p.use_smooth = True
gola = bpy.data.objects.new("SK_Archer_Gola", tg); bpy.context.scene.collection.objects.link(gola)
gola.parent = cap.parent; gola.matrix_parent_inverse = cap.matrix_parent_inverse; gola.matrix_world = cap.matrix_world.copy()
tg.materials.append(mat)
for g in ("Chest", "Neck", "Head"):
    gola.vertex_groups.new(name=g)
vg = gola.vertex_groups
for v in tg.vertices:
    t = (v.co.z - Z0) / (Z1 - Z0)
    if t < 0.25:
        vg["Chest"].add([v.index], 1 - t / 0.25 * 0.5, "REPLACE"); vg["Neck"].add([v.index], t / 0.25 * 0.5, "REPLACE")
    elif t < 0.65:
        vg["Neck"].add([v.index], 1.0, "REPLACE")
    else:
        vg["Neck"].add([v.index], 1 - (t - 0.65) / 0.35, "REPLACE"); vg["Head"].add([v.index], (t - 0.65) / 0.35, "REPLACE")
md = gola.modifiers.new("Armature", "ARMATURE"); md.object = arm

# ============================================================ ROSTO: mascara de pano (lenco) redonda e drapejada
me = ros.data
bm = bmesh.new(); bm.from_mesh(me)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
# componente do lenco: a maior com mat 0, faces 168 (z 1.017..1.235)
seen = set(); comps = []
for f in bm.faces:
    if f.index in seen:
        continue
    st = [f]; seen.add(f.index); cl = []
    while st:
        g = st.pop(); cl.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h.index not in seen:
                    seen.add(h.index); st.append(h)
    comps.append(cl)
len_ = next(c_ for c_ in comps if len(c_) == 168)
vs = sorted({v.index for g in len_ for v in g.verts})
NCo, NRo = 13, 8
assert len(vs) == NCo * NRo
net = np.array([bm.verts[i].co[:] for i in vs], dtype=float).reshape(NRo, NCo, 3)   # linha 0 = topo, colunas esquerda->direita
mi = len_[0].material_index
bmesh.ops.delete(bm, geom=len_, context="FACES_ONLY")
for v in [v for v in bm.verts if not v.link_faces]:
    bm.verts.remove(v)
# suaviza a rede de controle (tira o ruido) mantendo o contorno
for _ in range(2):
    n2 = net.copy()
    n2[1:-1] = 0.25 * net[:-2] + 0.5 * net[1:-1] + 0.25 * net[2:]
    n3 = n2.copy()
    n3[:, 1:-1] = 0.25 * n2[:, :-2] + 0.5 * n2[:, 1:-1] + 0.25 * n2[:, 2:]
    net = n3


def cr(p, t):
    """Catmull-Rom uniforme (p: n x 3), t em [0, n-1] -> n_t x 3"""
    n = len(p); out = []
    for tt in np.atleast_1d(t):
        i = min(int(tt), n - 2); u = tt - i
        p0, p1, p2, p3 = p[max(i - 1, 0)], p[i], p[i + 1], p[min(i + 2, n - 1)]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    return np.array(out)


NC, NR = int(os.environ.get("NC", 19)), int(os.environ.get("NR", 8))
tc = np.linspace(0, NCo - 1, NC); tr = np.linspace(0, NRo - 1, NR)
rows = np.array([cr(net[:, c], tr) for c in range(NCo)])        # (NCo, NR, 3)
grid = np.zeros((NR, NC, 3))
for j in range(NR):
    grid[j] = cr(rows[:, j], tc)
# drapejado: pregas verticais que convergem para o queixo + barriga suave
cxs = np.linspace(-1, 1, NC)
for j in range(NR):
    tj = j / (NR - 1)
    for i in range(NC):
        edge = math.sin(math.pi * (i / (NC - 1))) ** 0.7
        fold = math.sin(cxs[i] * 3.2 * math.pi * 0.5 + 0.4) * 0.5 + 0.5 * math.sin(cxs[i] * 5.5 + 1.0)
        d = 0.0075 * fold * edge * (0.3 + 0.7 * tj) + 0.010 * edge * math.sin(math.pi * tj) * (1 - 0.5 * abs(cxs[i]))
        # sai pela direcao radial a partir do eixo do rosto
        px, py = grid[j, i, 0], grid[j, i, 1] - 0.06
        n = math.hypot(px, py) or 1
        grid[j, i, 0] += d * px / n; grid[j, i, 1] += d * py / n
        # barra inferior: pontinha de pano leve (festao raso) no ultimo anel
        if j == NR - 1:
            grid[j, i, 2] -= 0.006 * math.cos(cxs[i] * math.pi * 3)
bv = [[bm.verts.new(grid[j, i]) for i in range(NC)] for j in range(NR)]
uvl = bm.loops.layers.uv.active
for j in range(NR - 1):
    for i in range(NC - 1):
        q = [bv[j][i], bv[j][i + 1], bv[j + 1][i + 1], bv[j + 1][i]]
        for tri in ((0, 1, 2), (0, 2, 3)):
            f = bm.faces.new([q[k] for k in tri]); f.material_index = mi; f.smooth = True
            for l in f.loops:
                jj, ii = next((jj, ii) for jj in (j, j + 1) for ii in (i, i + 1) if bv[jj][ii] is l.vert)
                l[uvl].uv = (0.02 + 0.48 * ii / (NC - 1), 1.0 - 0.48 * jj / (NR - 1))
bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f.material_index == mi and all(v in sum(bv, []) for v in f.verts)])
bm.to_mesh(me); bm.free()
clear_custom_normals(ros)
head_only(ros)

# ============================================================ texturas
for nm, fn in (("T_Capuz_BC", "T_Capuz_BC_new.png"), ("T_CapuzDetalhe_BC", "T_CapuzDetalhe_BC_new.png")):
    img = bpy.data.images[nm]; im = bpy.data.images.load(os.path.join(TRAB, fn))
    assert tuple(im.size) == tuple(img.size)
    img.pixels.foreach_set(np.array(im.pixels[:], dtype=np.float32)); img.pack(); img.update()
# interior menos preto: o verde da sombra do pano, para as dobras nao virarem bolsos escuros
for m in bpy.data.materials:
    if m.name == "M_Arqueiro_CapuzInterior" and m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                n.inputs["Base Color"].default_value = (0.060, 0.135, 0.050, 1)
bpy.ops.object.select_all(action="DESELECT")
for o in [arm] + [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SK_Archer")]:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_animations=False, export_skins=True,
                          export_yup=True, export_apply=False, export_materials="EXPORT", export_image_format="AUTO", export_leaf_bone=False)
DEPOIS = {o.name: tris(o) for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SK_Archer")}
print("TRIS antes", ANTES, sum(ANTES.values()))
print("TRIS depois", DEPOIS, sum(DEPOIS.values()))
