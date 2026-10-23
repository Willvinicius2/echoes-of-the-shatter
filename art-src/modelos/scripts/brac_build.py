"""Bracadeiras + luvas de dedos abertos do arqueiro dark por codigo (Blender). Nao usa TripoSG: o volume e um laco de aneis cuja
secao e MEDIDA no corpo (raios por direcao + 4,5 mm), entao nunca atravessa a pele; a luva (palma, 4 dedos, polegar) e a cuff sao
volumes proprios; cintas em helice, fivelas e pontas de flecha de metal (conformadas por raycast na luva) sao geometria a parte.
Grava work/game_uv.blend (objeto "game", UV no atlas de brac_atlas.py, pesos do corpo, max 4 influencias).
Uso: blender -b --factory-startup -P brac_build.py -- arq_dark_bracadeiras"""
import bpy, bmesh, sys, os, math, random
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from brac_atlas import *
from manto_add_cape_bones import add_cape_bones

cfg = load_cfg()
random.seed(5)
HAND_OFF = 0.0085
HCUT = 0.150
OFF = cfg.get("offset_pele_m", 0.0045)
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(cfg["body_rig_blend"]), "game_uv.blend"))
body = bpy.data.objects["game"]
body.name = "body_ref"; body.data.name = "body_ref"
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
add_cape_bones(arm)
bm_b = bmesh.new(); bm_b.from_mesh(body.data)
bvh_b = BVHTree.FromBMesh(bm_b)
gname = {g.index: g.name for g in body.vertex_groups}
bw = [{gname[g.group]: g.weight for g in v.groups} for v in body.data.vertices]
BP = np.array([v.co[:] for v in body.data.vertices])

bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
part_l = bm.verts.layers.int.new("part")     # 0 couro/luva/cintas (pesos por vertice), 1.. metais (rigidos, pesos do centro)
flat_l = bm.faces.layers.int.new("flat")
PART = [0]
NS = 12                                        # lados do anel do antebraco/palma


def V(p):
    v = bm.verts.new(p); v[part_l] = PART[0]; return v


def face(vs, uvs, ref=None, flat=False):
    try:
        f = bm.faces.new(vs)
    except ValueError:
        return None
    for l, u in zip(f.loops, uvs):
        l[uvl].uv = u
    f.normal_update()
    if ref is not None and f.normal.dot(f.calc_center_median() - ref) < 0:
        f.normal_flip()
    f[flat_l] = 1 if flat else 0
    return f


def smooth_ring(r):
    n = len(r)
    return [0.25 * r[k - 1] + 0.5 * r[k] + 0.25 * r[(k + 1) % n] for k in range(n)]


def pre_name(sx):
    return "Left" if sx > 0 else "Right"


class Side:
    pass


def build_side(sx):
    S = Side()
    pre = "Left" if sx > 0 else "Right"
    B = arm.data.bones
    elbow = Vector(B[pre + "LowerArm"].head_local); wrist = Vector(B[pre + "LowerArm"].tail_local)
    S.a = a = (wrist - elbow).normalized(); S.L = L = (wrist - elbow).length; S.o = elbow
    e1 = Vector((sx, 0, 0)); e1 = (e1 - a * e1.dot(a)).normalized()
    e2 = Vector((0, -1, 0)); e2 = (e2 - a * e2.dot(a) - e1 * e2.dot(e1)).normalized()
    S.e1, S.e2 = e1, e2
    wsel = np.array([bw[i].get(pre + "LowerArm", 0) + bw[i].get(pre + "Hand", 0) for i in range(len(BP))])
    rel = BP - np.array(elbow[:])
    along = rel @ np.array(a[:])
    perp = rel - np.outer(along, np.array(a[:]))
    ang = [math.pi + 2 * math.pi * k / NS for k in range(NS)]
    dirs = [e1 * math.cos(t) + e2 * math.sin(t) for t in ang]

    P1, P2 = perp @ np.array(e1[:]), perp @ np.array(e2[:])
    perp_n = np.linalg.norm(perp, axis=1)
    cand = (BP[:, 0] * sx > 0.22) & (perp_n < 0.10)
    DS = np.arange(-0.02, L + 0.30, 0.01)
    raw = []
    for d in DS:
        m = cand & (np.abs(along - d) < 0.022)
        raw.append(((P1[m].min() + P1[m].max()) / 2, (P2[m].min() + P2[m].max()) / 2) if m.sum() >= 3 else None)
    for i_ in range(len(raw)):
        if raw[i_] is None:
            raw[i_] = next((raw[k_] for k_ in range(i_ - 1, -1, -1) if raw[k_] is not None), (0.0, 0.0))
    raw = np.array(raw)
    for _ in range(3):
        sm = raw.copy()
        sm[1:-1] = 0.25 * raw[:-2] + 0.5 * raw[1:-1] + 0.25 * raw[2:]
        raw = sm

    def center(d):
        c1 = float(np.interp(d, DS, raw[:, 0])); c2 = float(np.interp(d, DS, raw[:, 1]))
        return elbow + a * d + e1 * c1 + e2 * c2

    def measure(d, cap=None):
        c = center(d)
        rs = []
        for dr in dirs:
            loc, nrm, fi, dist = bvh_b.ray_cast(c, dr, 0.14)
            rs.append(dist if loc is not None else None)
        ok = [r for r in rs if r is not None]
        med = float(np.median(ok)) if ok else 0.04
        rs = [min(r if r is not None else med, med * 1.3) for r in rs]
        rs = smooth_ring(smooth_ring(rs))
        return c, rs
    S.measure = measure
    S.center = center
    S.dirs = dirs
    return S


def ring_pts(S, c, rs, extra=0.0, lift=None):
    return [c + S.dirs[k] * (rs[k] + OFF + extra + (lift[k] if lift else 0)) for k in range(NS)]


def loft(rings, vcoords, cents, rect=R["leather"], close_ends=False):
    """rings: lista de listas de V (mesmo n); vcoords: v (0..1) por anel. u = k/n."""
    n = len(rings[0])
    vs = []
    for i in range(len(rings) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            q = [rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]]
            us = [k / n, (k + 1) / n, (k + 1) / n, k / n]
            vv = [vcoords[i], vcoords[i], vcoords[i + 1], vcoords[i + 1]]
            face(q, [uv(rect, u, v) for u, v in zip(us, vv)], ref=(cents[i] + cents[i + 1]) * 0.5)


SIDES = {}
TOTAL_V = 0.50                    # comprimento (m) do cuff aos dedos que corresponde a v=1
for sx in (1, -1):
    S = build_side(sx)
    SIDES[sx] = S
    L = S.L
    PART[0] = 0
    # ---- aneis da cuff + antebraco + palma: (distancia do cotovelo, extra radial)
    spec = [(0.058, 0.026, 'lip'), (0.058, 0.026, 'top'), (0.070, 0.029, ''), (0.086, 0.020, ''), (0.106, 0.008, ''),
            (0.135, 0.002, ''), (0.165, 0.0, ''), (0.195, 0.0, ''), (L, 0.001, ''), (L + 0.016, 0.004, '')]
    rings, vcs, meas = [], [], []
    for d, ex, tag in spec:
        c, rs = S.measure(d)
        if tag == 'lip':
            pts = ring_pts(S, c, rs, -0.0005)
        else:
            pts = ring_pts(S, c, rs, ex)
        rings.append([V(p) for p in pts]); vcs.append(max(0.0, (d - 0.058) / TOTAL_V)); meas.append((d, c, rs, ex))
    S.meas = meas
    if os.environ.get('BDBG'):
        for m_ in meas: print('BBUILD', sx, round(m_[0],3), [round(x_,3) for x_ in m_[1]], [round(x_,3) for x_ in m_[2]])
    S.nring = len(rings)
    cents = [m_[1] for m_ in meas]
    loft(rings, vcs, cents)
    # aba interna do cuff (lip -> topo): fecha a boca
    r0, r1 = rings[0], rings[1]
    for k in range(NS):
        k2 = (k + 1) % NS
        face([r0[k], r0[k2], r1[k2], r1[k]], [uv(R["dark"], k / NS, 0.2), uv(R["dark"], (k + 1) / NS, 0.2),
                                              uv(R["dark"], (k + 1) / NS, 0.8), uv(R["dark"], k / NS, 0.8)], ref=cents[0])

    # ---- mao: casca da propria mao do corpo dilatada (garante envolver a pele; dedos do corpo viram os dedos da luva)
    hw = np.array([bw[i_].get(pre_name(sx) + "Hand", 0.0) for i_ in range(len(BP))])
    selp = [pl for pl in body.data.polygons if all(hw[v_] > 0.08 and (BP[v_] - np.array(S.o[:])) @ np.array(S.a[:]) > L - 0.045 for v_ in pl.vertices)]
    used = sorted({v_ for pl in selp for v_ in pl.vertices})
    nrm_b = {v_.index: Vector(v_.normal) for v_ in body.data.vertices}
    adj = {v_: set() for v_ in used}
    for pl in selp:
        vl = list(pl.vertices)
        for q_ in range(len(vl)):
            adj[vl[q_]].add(vl[(q_ + 1) % len(vl)]); adj[vl[(q_ + 1) % len(vl)]].add(vl[q_])
    pos = {v_: Vector(BP[v_]) + nrm_b[v_] * HAND_OFF for v_ in used}
    for v_ in used:                                       # luva de dedos abertos: corta as pontas (achata no plano h = HCUT); a pele dos dedos aparece abaixo
        ex_ = (pos[v_] - S.o).dot(S.a) - (L + HCUT)
        if ex_ > 0:
            pos[v_] = pos[v_] - S.a * ex_
    for _ in range(4):                                    # suaviza as pontas dos dedos do corpo, que sao picos
        pos = {v_: pos[v_] * 0.5 + (sum((pos[w_] for w_ in adj[v_]), Vector()) / max(1, len(adj[v_]))) * 0.5 for v_ in used}
    vmap = {v_: V(pos[v_]) for v_ in used}

    def huv(v_):
        r = pos[v_] - S.center(L)
        ph = math.atan2(r.dot(S.e2), r.dot(S.e1))
        return ((ph - math.pi) % (2 * math.pi)) / (2 * math.pi), max(0.0, (r.dot(S.a) + L - 0.058) / TOTAL_V)
    for pl in selp:
        vl = list(pl.vertices)
        uu = [huv(v_) for v_ in vl]
        if max(u for u, _ in uu) - min(u for u, _ in uu) > 0.5:
            uu = [(u + 1.0 if u < 0.5 else u, v) for u, v in uu]
        uu = [(min(max(u, 0.0), 1.9) % 1.0 if False else (u if u <= 1.0 else u - 1.0 + 1.0), v) for u, v in uu]
        face([vmap[v_] for v_ in vl], [uv(R["leather"], min(u, 0.999), min(v, 0.999)) for u, v in uu], ref=None)
        # (u>1 repete a borda; o couro e uniforme ao redor, a emenda nao aparece)

# ---------------- garante o afastamento da pele: nenhum vertice de couro/luva fica dentro do corpo nem a menos de OFF
def push_out(bmx, off):
    n_fix = 0

    def vert_pass():
        n = 0
        for v in bmx.verts:
            if v[part_l] != 0:
                continue
            loc, nrm, fi, dist = bvh_b.find_nearest(v.co)
            if loc is None:
                continue
            if nrm.dot(v.co - loc) < 0 or dist < off - 1e-4:
                v.co = loc + nrm * off
                n += 1
        return n
    for _ in range(2):
        n_fix += vert_pass()
    for _ in range(3):                                   # centro e meio das arestas das faces tambem nao podem afundar (sem rasgos na superficie)
        for f in bmx.faces:
            if f.verts[0][part_l] != 0:
                continue
            for pt in [f.calc_center_median()] + [(f.verts[i].co + f.verts[(i + 1) % len(f.verts)].co) * 0.5 for i in range(len(f.verts))]:
                loc, nrm, fi, dist = bvh_b.find_nearest(pt)
                if loc is None:
                    continue
                dd = (off * 0.8) - (dist if nrm.dot(pt - loc) >= 0 else -dist)
                if dd > 0:
                    for v in f.verts:
                        v.co += nrm * dd * 0.6
                    n_fix += 1
    for _ in range(3):
        n_fix += vert_pass()                              # ultima palavra: todo vertice a >= off do corpo
    return n_fix


print("BBUILD push_out", push_out(bm, OFF * 0.95))

bvh_g = BVHTree.FromBMesh(bm)                      # superficie de couro + luva (sem cintas/metais): para conformar os acessorios


def snap(S, d, phi, h):
    c = S.center(d)
    dr = S.e1 * math.cos(phi) + S.e2 * math.sin(phi)
    loc, nrm, fi, dist = bvh_g.ray_cast(c + dr * 0.25, -dr, 0.4)
    if loc is None:
        return c + dr * 0.04
    return loc + nrm * h


def strap(S, d0, d1, ph0, turns, w, nseg, h=0.0042):
    secs = []
    for i in range(nseg + 1):
        t = i / nseg
        d = d0 + (d1 - d0) * t
        ph = ph0 + turns * 2 * math.pi * t
        secs.append([V(snap(S, d - w / 2, ph, 0.0016)), V(snap(S, d, ph, h)), V(snap(S, d + w / 2, ph, 0.0016))])
    PART[0] = 4
    ln = abs(turns) * 2 * math.pi * 0.04 + abs(d1 - d0)
    for i in range(nseg):
        ua, ub = min(i / nseg * ln / 0.26, 0.99), min((i + 1) / nseg * ln / 0.26, 0.999)
        for q in range(2):
            quad = [secs[i][q], secs[i + 1][q], secs[i + 1][q + 1], secs[i][q + 1]]
            vv = (q * 0.5, (q + 1) * 0.5)
            face(quad, [uv(R["strap"], ua, vv[0]), uv(R["strap"], ub, vv[0]), uv(R["strap"], ub, vv[1]), uv(R["strap"], ua, vv[1])],
                 ref=S.center(d0 + (d1 - d0) * 0.5))
    PART[0] = 0
    return (d1, ph0 + turns * 2 * math.pi)


def plate(S, d0, ph0, hx, hy, shape, rot=0.0, h=(0.0025, 0.0075, 0.0105), rect="metal", inlay=None):
    """ponta de flecha conformada: contorno (h0) -> anel interno (h1) -> centro (h2). hx, hy em metros (meia largura/comprimento)."""
    r0 = 0.036
    pts = [(x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)) for x, y in shape]
    n = len(pts)
    cp = (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)
    PART[0] = 1

    def P(x, y, hh):
        return V(snap(S, d0 + y * hy, ph0 + x * hx / r0, hh))
    outer = [P(x, y, h[0]) for x, y in pts]
    inner = [P(cp[0] + (x - cp[0]) * 0.55, cp[1] + (y - cp[1]) * 0.55, h[1]) for x, y in pts]
    ctr = P(cp[0], cp[1], h[2])
    refc = S.center(d0)
    for i in range(n):
        j = (i + 1) % n
        u = lambda x, y: uv(R[rect], 0.5 + 0.5 * x, 0.5 + 0.5 * y)
        ip = lambda x, y: (cp[0] + (x - cp[0]) * 0.55, cp[1] + (y - cp[1]) * 0.55)
        face([outer[i], outer[j], inner[j], inner[i]], [u(*pts[i]), u(*pts[j]), u(*ip(*pts[j])), u(*ip(*pts[i]))], ref=refc, flat=True)
        face([inner[i], inner[j], ctr], [u(*ip(*pts[i])), u(*ip(*pts[j])), u(*cp)], ref=refc, flat=True)
    if inlay:
        ip2 = [P(cp[0] + x * 0.6, cp[1] + y * 0.6, h[2] + 0.0012) for x, y in inlay]
        c2 = P(cp[0], cp[1], h[2] + 0.0030)
        for i in range(len(ip2)):
            j = (i + 1) % len(ip2)
            face([ip2[i], ip2[j], c2], [uv(R["rose"], 0.3, 0.3), uv(R["rose"], 0.7, 0.3), uv(R["rose"], 0.5, 0.7)], ref=refc, flat=True)
    PART[0] = 0


def buckle(S, d0, ph0, w, hgt):
    """aro da fivela (retangulo vazado) + lingueta, a partir do ponto (d0, ph0); w no sentido do eixo, hgt no sentido em volta."""
    r0 = 0.036
    PART[0] = 1
    def P(x, y, hh):
        return V(snap(S, d0 + y * w / 2, ph0 + x * hgt / 2 / r0, hh))
    o = [P(-1, -1, 0.0025), P(1, -1, 0.0025), P(1, 1, 0.0025), P(-1, 1, 0.0025)]
    i_ = [P(-0.62, -0.7, 0.0075), P(0.62, -0.7, 0.0075), P(0.62, 0.7, 0.0075), P(-0.62, 0.7, 0.0075)]
    refc = S.center(d0)
    mu = uv(R["metal"], 0.02, 0.02)
    for a in range(4):
        b = (a + 1) % 4
        face([o[a], o[b], i_[b], i_[a]], [mu] * 4, ref=refc, flat=True)
    bar = [P(-0.1, -0.9, 0.0095), P(0.1, -0.9, 0.0095), P(0.1, 0.9, 0.0095), P(-0.1, 0.9, 0.0095)]
    face(bar, [mu] * 4, ref=refc, flat=True)
    PART[0] = 0


for sx in (1, -1):
    S = SIDES[sx]
    L = S.L
    nl = 1 if sx > 0 else 1
    # cintas: abaixo da cuff, duas em diagonal cruzadas e uma no pulso
    strap(S, 0.092, 0.092, 0.0, 1.0, 0.020, 14)
    e1_ = strap(S, 0.140, 0.172, 4.0, 1.12, 0.021, 15)
    e2_ = strap(S, 0.185, 0.150, 1.0, -1.05, 0.019, 15)
    strap(S, L + 0.004, L + 0.004, 2.0, 1.0, 0.020, 14)
    # fivelas nas pontas das cintas
    buckle(S, 0.092, 1.9, 0.028, 0.022)
    buckle(S, e1_[0], e1_[1], 0.026, 0.020)
    buckle(S, 0.170, 5.3, 0.024, 0.020)
    # pontas de flecha: grande no antebraco (levemente para a frente), pequena abaixo, uma na mao, espinho perto do polegar
    plate(S, 0.128, 0.95, 0.042, 0.062, ARROW, h=(0.0025, 0.0085, 0.0118))
    plate(S, 0.198, 0.85, 0.0165, 0.0243, ARROW, h=(0.0025, 0.0070, 0.0095))
    plate(S, L + 0.052, 0.75, 0.031, 0.046, ARROW, h=(0.0030, 0.0085, 0.0115))
    plate(S, L + 0.040, 1.75, 0.0115, 0.017, ARROW, h=(0.0030, 0.0065, 0.0085))

# ---------------- ultima passada: nenhum vertice (nem de metal) a menos de 3,3 mm da pele
for v in bm.verts:
    loc, nrm, fi, dist = bvh_b.find_nearest(v.co)
    if loc is not None and (nrm.dot(v.co - loc) < 0 or dist < 0.0033):
        v.co = loc + nrm * 0.0035

# ---------------- finalizacao da malha
bmesh.ops.triangulate(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("game")
bm.to_mesh(me)
bm.free()
fl = np.zeros(len(me.polygons), np.int32)
if me.attributes.get("flat"):
    me.attributes["flat"].data.foreach_get("value", fl)
for pl, f_ in zip(me.polygons, fl):
    pl.use_smooth = not f_
ob = bpy.data.objects.new("game", me)
bpy.context.scene.collection.objects.link(ob)
part = np.zeros(len(me.vertices), np.int32)
me.attributes["part"].data.foreach_get("value", part)

# ---------------- pesos: transferencia do corpo (antebraco/mao); mao e dedos -> LeftHand/RightHand; max 4 influencias
from mathutils import interpolate as mi
deform = {b.name for b in arm.data.bones if b.use_deform}
for n in deform:
    ob.vertex_groups.new(name=n)
nv = len(me.vertices)
names = sorted(deform)
bi = {n: i for i, n in enumerate(names)}
Wm = np.zeros((nv, len(names)))


def body_w(co):
    loc, nrm, fi, d = bvh_b.find_nearest(co)
    poly = body.data.polygons[fi]
    pv = [body.data.vertices[i].co for i in poly.vertices]
    wts = mi.poly_3d_calc(pv, loc)
    W = {}
    for i, w in zip(poly.vertices, wts):
        for g, w2 in bw[i].items():
            W[g] = W.get(g, 0) + w2 * w
    return W


for v in me.vertices:
    W = body_w(v.co)
    keep = {g: w for g, w in W.items() if g in ("LeftLowerArm", "LeftHand", "LeftUpperArm", "RightLowerArm", "RightHand", "RightUpperArm")}
    if not keep or sum(keep.values()) < 1e-6:
        keep = {("Left" if v.co.x > 0 else "Right") + "LowerArm": 1.0}
    t_ = sum(keep.values())
    for g, w in keep.items():
        Wm[v.index, bi[g]] = w / t_
# metais: pecas rigidas, pesos do centro da peca
par = list(range(nv))


def fd(x):
    while par[x] != x:
        par[x] = par[par[x]]; x = par[x]
    return x


for e in me.edges:
    a_, b_ = fd(e.vertices[0]), fd(e.vertices[1])
    if a_ != b_:
        par[a_] = b_
comp = np.array([fd(i) for i in range(nv)])
for c in np.unique(comp):
    ids = np.where(comp == c)[0]
    if part[ids[0]] == 1:
        cen = sum((me.vertices[i].co for i in ids), Vector()) / len(ids)
        W = body_w(cen)
        keep = {g: w for g, w in W.items() if g in ("LeftLowerArm", "LeftHand", "RightLowerArm", "RightHand")}
        if not keep:
            keep = {("Left" if cen.x > 0 else "Right") + "LowerArm": 1.0}
        t_ = sum(keep.values())
        for i in ids:
            Wm[i] = 0
            for g, w in keep.items():
                Wm[i, bi[g]] = w / t_
nbr = [[] for _ in range(nv)]
for e in me.edges:
    nbr[e.vertices[0]].append(e.vertices[1]); nbr[e.vertices[1]].append(e.vertices[0])
soft = np.where(part != 1)[0]
for _ in range(3):                                     # suaviza so couro/cintas (metais ficam rigidos)
    Wn = Wm.copy()
    for i in soft:
        if nbr[i]:
            Wn[i] = 0.5 * Wm[i] + 0.5 * Wm[[j for j in nbr[i] if part[j] != 1] or [i]].mean(0)
    Wm = Wn
for i in range(nv):
    idxs = [j for j in np.argsort(-Wm[i])[:4] if Wm[i, j] > 1e-5]
    t2 = Wm[i, idxs].sum() or 1
    for j in idxs:
        ob.vertex_groups[names[j]].add([i], float(Wm[i, j] / t2), 'REPLACE')
ob.parent = arm
mod = ob.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
bpy.data.objects.remove(body)
me.attributes.remove(me.attributes["part"])
if me.attributes.get("flat"):
    me.attributes.remove(me.attributes["flat"])
bpy.ops.wm.save_as_mainfile(filepath=wpath(cfg, "game_uv.blend"))
print("BBUILD tris", sum(len(p.vertices) - 2 for p in me.polygons), "verts", nv)
