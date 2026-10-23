"""Torso do arqueiro dark por codigo (Blender): manto de penas (cartoes), base do manto, colete, gola, tabardo, correias, cinto,
fivelas e broches. A malha do TripoSG saiu como casca fundida, entao o volume e refeito aqui; a imagem de entrada guia as medidas
e a pintura (manto_tex.py). Grava work/game_uv.blend (objeto "game", UV no atlas, pesos copiados do corpo base, max 4 influencias).
Uso: blender -b --factory-startup -P manto_build.py -- arq_dark_manto"""
import bpy, bmesh, sys, os, math, random
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from manto_atlas import *

cfg = load_cfg()
random.seed(11)
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(cfg["body_rig_blend"]), "game_uv.blend"))
body = bpy.data.objects["game"]
body.name = "body_ref"; body.data.name = "body_ref"
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
dg = bpy.context.evaluated_depsgraph_get()
bm_b = bmesh.new(); bm_b.from_mesh(body.data)
bvh = BVHTree.FromBMesh(bm_b)
bvgroups = {g.index: g.name for g in body.vertex_groups}
bw = [{bvgroups[g.group]: g.weight for g in v.groups} for v in body.data.vertices]

bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
PARTS = {}


def vert(p, uvc):
    v = bm.verts.new(p); v[idx_layer] = 0
    return v, uvc


idx_layer = bm.verts.layers.int.new("part")


def face(vs, uvs, part=0):
    try:
        f = bm.faces.new(vs)
    except ValueError:
        return None
    for l, u in zip(f.loops, uvs):
        l[uvl].uv = u
    return f


def rb(theta, z, default=0.12):
    """raio externo do corpo (ray cast de fora para o eixo, limitado ao tronco: braco em A nao entra)."""
    d = Vector((math.sin(theta), -math.cos(theta), 0))
    loc, nrm, fi, dist = bvh.ray_cast(Vector((0, 0, z)) - d * 0.8, d, 0.8)
    r = (0.8 - dist) if loc is not None else default
    cap = 0.21 if z < 1.2 else (0.21 - 0.05 * min(1.0, (z - 1.2) / 0.25))
    return min(r, cap)


def grid(P, nu, nv, rect, closed=False, flip=False):
    """P(i, j) -> Vector, i em 0..nu, j em 0..nv; UV = retangulo inteiro."""
    vs = [[bm.verts.new(P(i, j)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            q = [vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]]
            uvs = [uv(rect, a / nu, b / nv) for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
            if flip:
                q.reverse(); uvs.reverse()
            face(q, uvs)
    return vs


def interp(z, ks, vals):
    return float(np.interp(z, ks[::-1], vals[::-1]))


# ---------- base do manto
ZK = [1.52, 1.46, 1.38, 1.28, 1.10, 0.90, 0.70, 0.50]
AX = [.15, .28, .44, .50, .54, .58, .62, .66]
AY = [.12, .18, .22, .24, .25, .27, .29, .31]
PH0 = math.radians(40)


def ell(phi, z, lift=0.0, yc=0.0):
    a = interp(z, ZK, AX) + lift; b = interp(z, ZK, AY) + lift
    return Vector((a * math.sin(phi), -b * math.cos(phi) + yc, z))


span = 2 * math.pi - 2 * PH0
zs = [1.52, 1.46, 1.38, 1.28, 1.10, 0.90, 0.70, 0.52]
grid(lambda i, j: ell(PH0 + span * i / 22, zs[j]), 22, len(zs) - 1, R["shell"])

# ---------- penas (cartoes): linhas de cima para baixo, cada linha mais externa que a anterior
ROWS = [(1.50, .28, 20), (1.38, .32, 22), (1.26, .36, 24), (1.14, .38, 26), (1.02, .40, 28), (0.90, .40, 30), (0.80, .38, 32)]
nfe = 0
for k, (zt, L, n) in enumerate(ROWS):
    lift0 = 0.012 + 0.010 * k
    for j in range(n):
        phi = PH0 + span * (j + 0.5 + 0.5 * (k % 2)) / (n + 0.5) + random.uniform(-0.02, 0.02)
        phi = min(max(phi, PH0), 2 * math.pi - PH0)
        Ln = L * random.uniform(0.82, 1.18)
        w = (span * interp(zt, ZK, AX) / n) * 1.0
        w = max(w, 0.06)
        yaw = random.uniform(-0.12, 0.12) + (0.10 * math.sin(phi) * (k / 6.0))     # abre um pouco para fora
        cell = random.randrange(FEATHER_COLS * FEATHER_ROWS)
        ts = [0.0, 0.34, 0.68, 1.0]
        rings = []
        for t in ts:
            z = zt - Ln * t
            ph = phi + yaw * t
            lift = lift0 + 0.035 * t + 0.02 * (1 - (2 * t - 1) ** 2) * 0.5
            c = ell(ph, z, lift)
            tang = Vector((math.cos(ph) * interp(z, ZK, AX), math.sin(ph) * interp(z, ZK, AY), 0))
            tang.normalize()
            nrm = Vector((math.sin(ph), -math.cos(ph), 0))
            wt = w * (1.0 - t ** 2.3) ** 0.85 * min(1.0, 0.45 + t * 4)
            rings.append((c, tang, nrm, wt, t))
        vs = []
        for c, tang, nrm, wt, t in rings:
            if t >= 1.0:
                vs.append([bm.verts.new(c + nrm * 0.004)])
            else:
                vs.append([bm.verts.new(c - tang * wt / 2 - nrm * 0.008), bm.verts.new(c + nrm * 0.005), bm.verts.new(c + tang * wt / 2 - nrm * 0.008)])
        for r in range(2):
            for q in range(2):
                a, b, c2, d = vs[r][q], vs[r][q + 1], vs[r + 1][q + 1], vs[r + 1][q]
                face([a, d, c2, b], [feather_uv(cell, q / 2, ts[r]), feather_uv(cell, q / 2, ts[r + 1]),
                                      feather_uv(cell, (q + 1) / 2, ts[r + 1]), feather_uv(cell, (q + 1) / 2, ts[r])])
        for q in range(2):
            face([vs[2][q], vs[3][0], vs[2][q + 1]], [feather_uv(cell, q / 2, ts[2]), feather_uv(cell, 0.5, 1.0), feather_uv(cell, (q + 1) / 2, ts[2])])
        nfe += 1

# ---------- colete (ajustado ao corpo)
ZV = [0.98, 1.06, 1.14, 1.22, 1.30, 1.38, 1.46]
NV = 24
grid(lambda i, j: (lambda th: Vector((math.sin(th), -math.cos(th), 0)) * (rb(th, ZV[j]) + 0.014) + Vector((0, 0, ZV[j])))(2 * math.pi * i / NV),
     NV, len(ZV) - 1, R["cloth"])

# ---------- gola (cachecol): cilindro que alarga ate os ombros, com ponta pendurada na frente (+X)
NS = 24
th0 = math.radians(25)


def scarf(i, j):
    th = 2 * math.pi * i / NS
    s = j / 4.0
    drop = 0.15 * math.exp(-(((th - th0 + math.pi) % (2 * math.pi) - math.pi) / 0.55) ** 2)
    ztop = 1.50 + 0.03 * math.cos(th)
    zbot = 1.43 - drop
    z = ztop + (zbot - ztop) * s
    rn = rb(th, z, 0.14)
    r = rn + 0.06 + 0.06 * (s ** 1.2) + 0.018 * math.sin(s * math.pi) + 0.012 * math.sin(th * 5 + s * 2.0) * s
    return Vector((math.sin(th) * r, -math.cos(th) * r * 1.0, z))


grid(scarf, NS, 4, R["scarf"], flip=True)

# ---------- tabardo: dois paineis na frente, ponta em V
for sx in (-1, 1):
    cx = sx * 0.095
    def tab(i, j, cx=cx, sx=sx):
        t = j / 4.0
        z = 1.00 - 0.46 * t
        wdt = 0.19 * (1.0 - 0.0 * t)
        x = cx + (i / 2.0 - 0.5) * wdt + sx * 0.03 * t
        y = -(0.155 + 0.11 * t)
        return Vector((x, y, z - (0.07 * (1 - abs(i - 1)) if j == 4 else 0)))
    grid(tab, 2, 4, R["panel"], flip=(sx > 0))

# ---------- correias em X, cinto e metal
def surf_front(x, z, off):
    loc, nrm, fi, d = bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 3.0)
    if loc is None:
        return Vector((x, -0.15, z))
    return loc + nrm * off


def strap(p0, p1, nseg, width, th, rect, base=0.0):
    pts = []
    for s in range(nseg + 1):
        t = s / nseg
        x = p0[0] + (p1[0] - p0[0]) * t; z = p0[1] + (p1[1] - p0[1]) * t
        pts.append(surf_front(x, z, base))
    prev = None
    for s, pt in enumerate(pts):
        a = pts[min(s + 1, nseg)] - pts[max(s - 1, 0)]
        side = a.cross(Vector((0, -1, 0))).normalized() * width / 2
        out = Vector((0, -1, 0)) * th
        ring = [bm.verts.new(pt - side), bm.verts.new(pt + side), bm.verts.new(pt + side + out), bm.verts.new(pt - side + out)]
        if prev:
            for q in range(4):
                u0, u1 = s - 1, s
                face([prev[q], ring[q], ring[(q + 1) % 4], prev[(q + 1) % 4]],
                     [uv(rect, (u0 / nseg) * 0.5, 0.1), uv(rect, (u1 / nseg) * 0.5, 0.1), uv(rect, (u1 / nseg) * 0.5, 0.9), uv(rect, (u0 / nseg) * 0.5, 0.9)])
        prev = ring
    return pts


strap((-0.15, 1.44), (0.17, 1.04), 10, 0.030, 0.007, R["leather"], 0.022)
strap((0.15, 1.44), (-0.17, 1.04), 10, 0.030, 0.007, R["leather"], 0.026)
# cinto em anel
NB = 28
for row, (zc, hgt) in enumerate(((1.03, 0.075), (1.085, 0.03))):
    vs = []
    for i in range(NB + 1):
        th = 2 * math.pi * i / NB
        r = rb(th, zc) + 0.030 + 0.006 * row
        d = Vector((math.sin(th), -math.cos(th), 0))
        vs.append((bm.verts.new(d * r + Vector((0, 0, zc - hgt / 2))), bm.verts.new(d * r + Vector((0, 0, zc + hgt / 2)))))
    for i in range(NB):
        face([vs[i][0], vs[i + 1][0], vs[i + 1][1], vs[i][1]], [uv(R["leather"], i / NB, 0.15), uv(R["leather"], (i + 1) / NB, 0.15),
                                                               uv(R["leather"], (i + 1) / NB, 0.85), uv(R["leather"], i / NB, 0.85)][::-1] if False else
             [uv(R["leather"], (i % 14) / 14 * .5 + .5, 0.15), uv(R["leather"], ((i % 14) + 1) / 14 * .5 + .5, 0.15),
              uv(R["leather"], ((i % 14) + 1) / 14 * .5 + .5, 0.85), uv(R["leather"], (i % 14) / 14 * .5 + .5, 0.85)])


def box(c, sx, sy, sz, rect, rot=0.0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r["verts"]
    ca, sa = math.cos(rot), math.sin(rot)
    for v in vs:
        x, y, z = v.co.x * sx, v.co.y * sy, v.co.z * sz
        v.co = Vector((x * ca - z * sa, y, x * sa + z * ca)) + c
    for f in {f for v in vs for f in v.link_faces}:
        for l in f.loops:
            l[uvl].uv = uv(rect, 0.5 + 0.2 * (l.vert.co.x - c.x) / max(sx, 1e-3) * 0, 0.5)
            l[uvl].uv = uv(rect, random.random() * 0.8 + 0.1, random.random() * 0.8 + 0.1)


def buckle(c, size, rot=0.0):
    w, h = size
    t = 0.007; bar = 0.007
    box(c + Vector((-w / 2 + bar / 2, -t / 2, 0)), bar, t, h, R["metal"], rot)
    box(c + Vector((w / 2 - bar / 2, -t / 2, 0)), bar, t, h, R["metal"], rot)
    box(c + Vector((0, -t / 2, h / 2 - bar / 2)), w, t, bar, R["metal"], rot)
    box(c + Vector((0, -t / 2, -h / 2 + bar / 2)), w, t, bar, R["metal"], rot)
    box(c + Vector((0, -t / 2 - 0.002, 0)), 0.006, t, h * 0.9, R["metal"], rot)


def diamond(c, hw, hh, d, rect, uvc=(0.5, 0.5)):
    top = bm.verts.new(c + Vector((0, 0, hh))); bot = bm.verts.new(c + Vector((0, 0, -hh)))
    l = bm.verts.new(c + Vector((-hw, 0, 0))); r = bm.verts.new(c + Vector((hw, 0, 0)))
    f = bm.verts.new(c + Vector((0, -d, 0))); b = bm.verts.new(c + Vector((0, d * 0.3, 0)))
    ui = lambda a, b2: uv(rect, a, b2)
    for tri in ((top, l, f), (top, f, r), (bot, f, l), (bot, r, f), (top, b, l), (top, r, b), (bot, l, b), (bot, b, r)):
        face(list(tri), [ui(.5, .1), ui(.1, .5), ui(.5, .5)] if False else [ui(.5, .3), ui(.3, .5), ui(.5, .5)])


# fivelas nas correias e no cinto
p1 = surf_front(-0.07, 1.30, 0.045); buckle(p1, (0.05, 0.04), 0.0)
p2 = surf_front(0.06, 1.24, 0.045); buckle(p2, (0.05, 0.04), 0.0)
buckle(surf_front(0.0, 1.03, 0.050), (0.07, 0.055))
# broche no ombro (cruz em losangos) e pendente do cinto
b0 = surf_front(-0.26, 1.40, 0.05) if False else Vector((-0.27, -0.205, 1.40))
diamond(b0, 0.015, 0.07, 0.016, R["emblem"])
diamond(b0 + Vector((0, 0, 0.02)), 0.045, 0.014, 0.014, R["emblem"])
tb = surf_front(0.115, 1.02, 0.03)
box(tb + Vector((0, 0, -0.07)), 0.008, 0.006, 0.12, R["leather"])
diamond(tb + Vector((0, -0.002, -0.17)), 0.022, 0.05, 0.014, R["metal"])
diamond(tb + Vector((0, -0.002, -0.27)), 0.015, 0.04, 0.012, R["metal"])

# normais para fora e liso
for f in bm.faces:
    c = f.calc_center_median()
    out = Vector((c.x, c.y + 0.0, 0)).normalized()
    if f.normal.dot(out) < 0 and not (abs(c.x) < 0.3 and c.y < -0.1 and c.z < 1.1):
        f.normal_flip()
bm.normal_update()

bmesh.ops.triangulate(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("game")
bm.to_mesh(me); bm.free()
for p in me.polygons:
    p.use_smooth = True
ob = bpy.data.objects.new("game", me)
bpy.context.scene.collection.objects.link(ob)

# ---------- pesos: vizinho mais proximo do corpo, com regras de manto
DEF = {"LeftLowerArm": "LeftUpperArm", "LeftHand": "LeftUpperArm", "RightLowerArm": "RightUpperArm", "RightHand": "RightUpperArm",
       "LeftLowerLeg": "LeftUpperLeg", "LeftFoot": "LeftUpperLeg", "LeftToes": "LeftUpperLeg", "RightLowerLeg": "RightUpperLeg",
       "RightFoot": "RightUpperLeg", "RightToes": "RightUpperLeg", "Head": "Neck"}
deform = {b.name for b in arm.data.bones if b.use_deform}
for n in deform:
    ob.vertex_groups.new(name=n)
nv = len(me.vertices)
names = sorted(deform)
bi = {n: i for i, n in enumerate(names)}
Wm = np.zeros((nv, len(names)))
from mathutils import interpolate as mi
for v in me.vertices:
    co = v.co
    loc, nrm, fi, d = bvh.find_nearest(co)
    poly = body.data.polygons[fi]
    pv = [body.data.vertices[i].co for i in poly.vertices]
    wts = mi.poly_3d_calc(pv, loc)
    W = {}
    for i, w in zip(poly.vertices, wts):
        for g, ww in bw[i].items():
            W[g] = W.get(g, 0) + ww * w
    W2 = {}
    for g, w in W.items():
        g2 = DEF.get(g, g)
        W2[g2] = W2.get(g2, 0) + w
    for side in ("Left", "Right"):                       # o manto so segue metade do braco
        k = side + "UpperArm"
        if k in W2:
            mv = W2[k] * 0.5; W2[k] -= mv; W2["Chest"] = W2.get("Chest", 0) + mv
    if co.z < 1.0:                                       # abaixo da cintura: quadril + coxa do lado (nunca o joelho)
        k = (1.0 - max(co.z, 0.45)) / 0.55
        sd = "Left" if co.x < 0 else "Right"
        W2 = {"Hips": 1 - 0.5 * k, sd + "UpperLeg": 0.5 * k}
    for g, w in W2.items():
        if g in bi:
            Wm[v.index, bi[g]] += w
# componentes: pecas pequenas (penas, correias, fivelas) seguem o peso da raiz (rigidas); superficies grandes suavizam
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
zz = np.array([v.co.z for v in me.vertices])
nbr = [[] for _ in range(nv)]
for e in me.edges:
    nbr[e.vertices[0]].append(e.vertices[1]); nbr[e.vertices[1]].append(e.vertices[0])
big = []
for c in np.unique(comp):
    ids = np.where(comp == c)[0]
    if len(ids) <= 60:
        top = ids[np.argmax(zz[ids])]
        Wm[ids] = Wm[top]
    else:
        big.extend(ids.tolist())
big = np.array(big)
for _ in range(6):
    Wn = Wm.copy()
    for i in big:
        if nbr[i]:
            Wn[i] = 0.5 * Wm[i] + 0.5 * Wm[nbr[i]].mean(0)
    Wm = Wn
for i in range(nv):
    idxs = np.argsort(-Wm[i])[:4]
    t2 = Wm[i, idxs].sum() or 1
    for j in idxs:
        if Wm[i, j] / t2 > 1e-3:
            ob.vertex_groups[names[j]].add([i], float(Wm[i, j] / t2), 'REPLACE')
ob.parent = arm
mod = ob.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
bpy.data.objects.remove(body)
bpy.ops.wm.save_as_mainfile(filepath=wpath(cfg, "game_uv.blend"))
print("MBUILD feathers", nfe, "tris", sum(len(p.vertices) - 2 for p in me.polygons), "verts", nv)
