"""Torso v2 do arqueiro dark por codigo (Blender): manto LONGO em 2 camadas de cartoes de pena curvos (ombro a panturrilha, abrindo em A,
pontas assimetricas), base do manto, colete com recorte projetado, cinto, gola de cachecol (tubo dobrado, 2 voltas + drapeado),
tabardo, pendente e metais (fivelas, broche, estrela, losangos) como geometria a parte com bisel. Ossos Cape_L/R/B (manto_add_cape_bones.py).
Grava work/game_uv.blend (objeto "game", UV no atlas de manto_atlas.py, pesos do corpo + Cape, max 4 influencias).
Uso: blender -b --factory-startup -P manto_build.py -- arq_dark_manto"""
import bpy, bmesh, sys, os, math, random
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from manto_atlas import *
from manto_add_cape_bones import add_cape_bones

cfg = load_cfg()
random.seed(23)
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(cfg["body_rig_blend"]), "game_uv.blend"))
body = bpy.data.objects["game"]
body.name = "body_ref"; body.data.name = "body_ref"
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
add_cape_bones(arm)
bm_b = bmesh.new(); bm_b.from_mesh(body.data)
bvh = BVHTree.FromBMesh(bm_b)
bvgroups = {g.index: g.name for g in body.vertex_groups}
bw = [{bvgroups[g.group]: g.weight for g in v.groups} for v in body.data.vertices]

bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
part_l = bm.verts.layers.int.new("part")
flat_l = bm.faces.layers.int.new("flat")
PART = [0]


def V(p):
    v = bm.verts.new(p)
    v[part_l] = PART[0]
    return v


def face(vs, uvs, ref="radial", flat=False):
    try:
        f = bm.faces.new(vs)
    except ValueError:
        return None
    for l, u in zip(f.loops, uvs):
        l[uvl].uv = u
    f.normal_update()
    c = f.calc_center_median()
    if ref is not None:
        r = Vector((0, 0, c.z)) if isinstance(ref, str) else ref
        if f.normal.dot(c - r) < 0:
            f.normal_flip()
    f[flat_l] = 1 if flat else 0
    return f


def rb(theta, z, default=0.12):
    d = Vector((math.sin(theta), -math.cos(theta), 0))
    loc, nrm, fi, dist = bvh.ray_cast(Vector((0, 0, z)) - d * 0.8, d, 0.8)
    r = (0.8 - dist) if loc is not None else default
    cap = 0.21 if z < 1.2 else (0.21 - 0.05 * min(1.0, (z - 1.2) / 0.25))
    return min(r, cap)


def surf_front(x, z, off):
    loc, nrm, fi, d = bvh.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 3.0)
    if loc is None:
        return Vector((x, -0.15, z))
    return loc + nrm * off


def interp(z, ks, vals):
    return float(np.interp(z, ks[::-1], vals[::-1]))


# perfil do manto (elipse por altura): ombro -> panturrilha, abrindo em A
ZK = [1.55, 1.50, 1.40, 1.30, 1.10, 0.90, 0.70, 0.50, 0.38]
AX = [.16, .28, .44, .50, .54, .59, .64, .70, .74]
AY = [.12, .18, .22, .24, .25, .28, .31, .34, .36]
PH0 = math.radians(40)
SPAN = 2 * math.pi - 2 * PH0


def ell(phi, z, lift=0.0):
    a = interp(z, ZK, AX) + lift
    b = interp(z, ZK, AY) + lift
    return Vector((a * math.sin(phi), -b * math.cos(phi), z))


def mean_r(z):
    a, b = interp(z, ZK, AX), interp(z, ZK, AY)
    return math.sqrt((a * a + b * b) / 2)


# ---------------- base do manto (casca por baixo das penas)
PART[0] = 1
zs = [1.52, 1.46, 1.38, 1.28, 1.10, 0.90, 0.70, 0.54]
NSH = 20
vs = [[V(ell(PH0 + SPAN * i / NSH, z, -0.008)) for z in zs] for i in range(NSH + 1)]
for i in range(NSH):
    for j in range(len(zs) - 1):
        q = [vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]]
        face(q, [uv(R["shell"], a / NSH, b / (len(zs) - 1)) for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))])

# ---------------- penas: cartoes curvos com alpha (atlas de penas com barbas), 4 aneis x 3 vertices
LAYERS = [  # (z do topo, comprimento, n, lift0)  A: longa, por baixo; B: ombro, por cima
    (1.30, .46, 17, .004), (1.06, .48, 20, .008), (0.84, .44, 22, .012), (0.66, .34, 24, .016),
    (1.52, .34, 15, .034), (1.38, .36, 17, .040), (1.24, .38, 19, .046), (1.10, .38, 21, .052), (0.96, .38, 23, .058)]
TS = [0.0, 0.33, 0.66, 1.0]
nfe = 0
NCELL = FEATHER_COLS * FEATHER_ROWS
for k, (zt, L, n, lift0) in enumerate(LAYERS):
    for j in range(n):
        if k < 4 and random.random() < 0.10:               # falhas na camada longa: quebra o bloco da cauda
            continue
        phi = PH0 + SPAN * (j + 0.5 + (0.5 if k % 2 else 0.0)) / (n + 0.5) + random.uniform(-0.035, 0.035)
        phi = min(max(phi, PH0 + 0.02), 2 * math.pi - PH0 - 0.02)
        side = -math.sin(phi)                             # lado esquerdo (x<0) mais comprido; assimetria
        Ln = L * random.uniform(0.66, 1.34) * (1 + 0.20 * side)
        ztk = zt + random.uniform(-0.04, 0.04)
        cell = random.randrange(NCELL)
        asp = FEATHER_ASPECT[cell]
        w = max(Ln * asp * random.uniform(1.25, 1.55), SPAN * mean_r(zt) / n * 1.2)
        yaw = random.uniform(-0.16, 0.16) + 0.12 * math.sin(phi) * (zt < 1.2)
        flipu = random.random() < 0.5
        rings = []
        for t in TS:
            z = ztk - Ln * t
            ph = phi + yaw * t
            lift = lift0 + 0.02 * t + 0.07 * t ** 1.7
            c = ell(ph, z, lift)
            a_, b_ = interp(z, ZK, AX), interp(z, ZK, AY)
            tang = Vector((math.cos(ph) * a_, math.sin(ph) * b_, 0)).normalized()
            nrm = Vector((math.sin(ph), -math.cos(ph), 0))
            rings.append((c, tang, nrm))
        PART[0] = 1
        rv = []
        for (c, tang, nrm), t in zip(rings, TS):
            cv = 0.14 * w * (1 - 0.3 * t)                   # curvatura da secao
            rv.append([V(c - tang * w / 2 - nrm * cv), V(c + nrm * 0.004), V(c + tang * w / 2 - nrm * cv)])
        for r in range(3):
            for q in range(2):
                a, b2, c2, d = rv[r][q], rv[r][q + 1], rv[r + 1][q + 1], rv[r + 1][q]
                u0, u1 = (q / 2, (q + 1) / 2) if not flipu else (1 - q / 2, 1 - (q + 1) / 2)
                face([a, d, c2, b2], [feather_uv(cell, u0, TS[r]), feather_uv(cell, u0, TS[r + 1]),
                                      feather_uv(cell, u1, TS[r + 1]), feather_uv(cell, u1, TS[r])])
        nfe += 1
PART[0] = 0


# ---------------- projecao da imagem de entrada no colete (x, z do corpo -> UV do recorte)
def proj_uv(x, z, rect="vest"):
    px = x / PX_M + PX_X0
    py = PX_Z0 + (1.46 - z) / PX_MZ
    x0, y0, x1, y1 = SRC["vest"]
    u = (px - x0) / (x1 - x0)
    v = (py - y0) / (y1 - y0)
    return u, v


def band(zrows, nseg, off, rect_alt, uv_proj_ok=True):
    vs = [[V(Vector((math.sin(th), -math.cos(th), 0)) * (rb(th, z) + off) + Vector((0, 0, z))) for z in zrows]
          for th in [2 * math.pi * i / nseg for i in range(nseg + 1)]]
    for i in range(nseg):
        for j in range(len(zrows) - 1):
            q = [vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]]
            cen = sum((v.co for v in q), Vector()) / 4
            uvp = [proj_uv(v.co.x, v.co.z) for v in q]
            if cen.y < -0.02 and all(-0.02 <= u <= 1.02 for u, _ in uvp) and all(-0.02 <= v <= 1.02 for _, v in uvp):
                uvs = [uv(R["vest"], min(max(u, 0.005), 0.995), min(max(v, 0.005), 0.995), pad=2) for u, v in uvp]
            else:
                uvs = [uv(rect_alt, 0.04 + 0.08 * (a % 2), 0.3 + 0.4 * (b % 2), pad=2) for a, b in ((0, 0), (1, 0), (1, 1), (0, 1))]
            face(q, uvs)


ZV = [1.04, 1.14, 1.24, 1.34, 1.44]
band(ZV, 24, 0.014, R["plain"])
band([1.12, 1.20], 28, 0.032, R["belt"])


# ---------------- gola de cachecol: tubo dobrado (2 voltas) + drapeado
def tube(pathfn, nseg, radfn, sides, rect, urep=3):
    rings = []
    for i in range(nseg):
        c = pathfn(i / nseg)
        rn, rv_ = radfn(i / nseg)
        out = Vector((c.x, c.y, 0)).normalized()
        rings.append([V(c + out * math.cos(2 * math.pi * s / sides) * rn + Vector((0, 0, 1)) * math.sin(2 * math.pi * s / sides) * rv_)
                      for s in range(sides)] + [c])
    for i in range(nseg):
        a, b2 = rings[i], rings[(i + 1) % nseg]
        for s in range(sides):
            s2 = (s + 1) % sides
            face([a[s], b2[s], b2[s2], a[s2]],
                 [uv(rect, (i / nseg * urep) % 1.0, s / sides), uv(rect, ((i + 1) / nseg * urep) % 1.0, s / sides),
                  uv(rect, ((i + 1) / nseg * urep) % 1.0, (s + 1) / sides), uv(rect, (i / nseg * urep) % 1.0, (s + 1) / sides)], ref=a[sides])


def loop_path(ax, ay, z0, dz, ph0):
    def f(u):
        th = 2 * math.pi * u
        front = max(0.0, math.cos(th - ph0)) ** 1.2
        return Vector((ax * math.sin(th), -ay * math.cos(th), z0 - dz * front + 0.012 * math.sin(3 * th)))
    return f


tube(loop_path(0.135, 0.126, 1.55, 0.035, 0.0), 22, lambda u: (0.056 + 0.014 * math.sin(6.28 * 3 * u), 0.044 + 0.008 * math.sin(6.28 * 2 * u)), 7, R["scarf"], 2)
tube(loop_path(0.19, 0.162, 1.488, 0.06, 0.35), 22, lambda u: (0.068 + 0.016 * math.sin(6.28 * 2 * u + 1), 0.050 + 0.01 * math.sin(6.28 * 3 * u)), 7, R["scarf"], 2)


def drape(i, j):
    pass


ND, MD = 6, 5
dvs = []
for i in range(ND + 1):
    u = i / ND
    row = []
    for j in range(MD + 1):
        v = j / MD
        xl = -0.15 + 0.185 * v
        xr = 0.135 - 0.095 * v
        x = xl + (xr - xl) * u
        z = 1.50 - 0.20 * v - 0.025 * math.sin(u * math.pi) * (1 - v)
        off = 0.052 + 0.016 * math.sin(u * 7 + v * 4) * (0.5 + v) + 0.02 * math.sin(u * math.pi) * (1 - v)
        if j == MD:
            z -= 0.022 * (i % 2)
            x += 0.008 * ((i + 1) % 2)
        if i in (0, ND):
            z += 0.006 * (j % 2)
        row.append(V(surf_front(x, z, off)))
    dvs.append(row)
for i in range(ND):
    for j in range(MD):
        q = [dvs[i][j], dvs[i + 1][j], dvs[i + 1][j + 1], dvs[i][j + 1]]
        face(q, [uv(R["scarf"], 0.02 + 0.96 * a / ND, 0.05 + 0.9 * b / MD) for a, b in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))],
             ref=Vector((0, 0.5, 1.4)))

# ---------------- tabardo (dois paineis em V na frente, sob o cinto)
for sx in (-1, 1):
    cx = sx * 0.098
    zt, zb = 1.10, 0.52

    def tab(i, j, cx=cx, sx=sx):
        t = j / 5.0
        z = zt - (zt - zb) * t
        x = cx + (i / 2.0 - 0.5) * 0.19 + sx * 0.035 * t
        y = -(0.165 + 0.135 * t)
        return V(Vector((x, y, z - (0.075 * (1 - abs(i - 1)) if j == 5 else 0))))
    gv = [[tab(i, j) for j in range(6)] for i in range(3)]
    for i in range(2):
        for j in range(5):
            q = [gv[i][j], gv[i + 1][j], gv[i + 1][j + 1], gv[i][j + 1]]
            us = [(i + a) / 2 for a in (0, 1, 1, 0)]
            if sx > 0:
                us = [1 - u for u in us]
            vv = [(j + b) / 5 for b in (0, 0, 1, 1)]
            face(q, [uv(R["tabard"], u, v) for u, v in zip(us, vv)], ref=Vector((cx, 0.6, 0.8)))


# ---------------- metais por geometria (bisel): placa extrudada com chanfro
def frame_from(O, Z, up=Vector((0, 0, 1)), rot=0.0):
    Z = Z.normalized()
    X = up.cross(Z).normalized()
    Y = Z.cross(X).normalized()
    if rot:
        c, s = math.cos(rot), math.sin(rot)
        X, Y = X * c + Y * s, Y * c - X * s
    return O, X, Y, Z


def extruded(poly, depth, inset, fr, back=0.0, rect="metal"):
    O, X, Y, Z = fr
    c = Vector((sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)))
    W = lambda p, z: O + X * p[0] + Y * p[1] + Z * z
    base = [V(W(p, back)) for p in poly]
    top = [V(W((c.x + (p[0] - c.x) * (1 - inset), c.y + (p[1] - c.y) * (1 - inset)), depth)) for p in poly]
    ctr = V(W((c.x, c.y), depth * 1.15))
    n = len(poly)
    ref = O - Z * 0.02 + (X * c.x + Y * c.y)
    for i in range(n):
        i2 = (i + 1) % n
        mu = uv(R[rect], random.uniform(0.1, 0.9), random.uniform(0.1, 0.9))
        face([base[i], base[i2], top[i2], top[i]], [mu] * 4, ref=ref, flat=True)
        face([top[i], top[i2], ctr], [mu] * 3, ref=ref, flat=True)


def rect_poly(w, h, cx=0.0, cy=0.0):
    return [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]


def buckle(O, Z, w, h, rot=0.0, rivets=True):
    fr = frame_from(O, Z, rot=rot)
    bar = max(0.0065, w * 0.14)
    d = 0.007
    for poly in (rect_poly(w, bar, 0, h / 2 - bar / 2), rect_poly(w, bar, 0, -h / 2 + bar / 2),
                 rect_poly(bar, h - 2 * bar, -w / 2 + bar / 2, 0), rect_poly(bar, h - 2 * bar, w / 2 - bar / 2, 0)):
        extruded(poly, d, 0.35, fr)
    extruded(rect_poly(bar * 0.8, h * 0.8, 0.0, 0.0), 0.0045, 0.3, fr, back=0.002)
    if rivets:
        for dx in (-w * 0.9, w * 0.9):
            pent = [(dx + 0.0055 * math.cos(2 * math.pi * k / 5), 0.0055 * math.sin(2 * math.pi * k / 5)) for k in range(5)]
            extruded(pent, 0.004, 0.4, fr)


def front_y(x, z):
    if z >= 1.10:
        return surf_front(x, z, 0.04).y
    t = (1.10 - z) / 0.58
    return -(0.165 + 0.135 * t) - 0.01


def at(px, py):
    x, z = img_to_xz(px, py)
    return x, z


FZ = Vector((0, -1, 0))
for (px, py, w, h, rot) in ((482, 277, .048, .042, -0.6), (460, 310, .048, .042, 0.5), (490, 400, .072, .056, 0.0),
                           (550, 430, .042, .052, 0.0), (555, 392, .04, .05, 0.0)):
    x, z = at(px, py)
    buckle(Vector((x, surf_front(x, z, 0.0).y - 0.004 if z > 1.1 else front_y(x, z), z)), FZ, w, h, rot, rivets=(w > .06))

def mirror(right):
    """meio contorno (x >= 0) de cima para baixo, com as pontas no eixo -> contorno fechado."""
    return right + [(-x, y) for x, y in reversed(right[1:-1])]


def rivet(fr_, x, y, r=0.0055, d=0.004):
    pent = [(x + r * math.cos(2 * math.pi * k / 5), y + r * math.sin(2 * math.pi * k / 5)) for k in range(5)]
    extruded(pent, d, 0.4, fr_)


# broche do ombro: cruz com pontas de seta, encaixado na borda da camada de penas do ombro (sobre a superficie, levemente afundado)
sxp, sz = 5.40, 1.44
O = ell(sxp, sz, 0.047)
radial = Vector((math.sin(sxp), -math.cos(sxp), 0.12))
Zv = (radial * 0.40 + Vector((0, -1, 0)) * 0.85).normalized()
fr = frame_from(O - Zv * 0.004, Zv)
S = 1.45
cross = [(x * S, y * S) for x, y in mirror([(0, .088), (.013, .050), (.030, .044), (.052, .022), (.030, .014), (.016, .008), (.013, -.020),
                                           (.026, -.040), (.012, -.054), (0, -.092)])]
extruded(cross, 0.013, 0.5, fr)
extruded([(0, .056 * S), (.022 * S, .018 * S), (0, -.016 * S), (-.022 * S, .018 * S)], 0.019, 0.5, fr, back=0.008)
for (x, y) in ((0, .066 * S), (.040 * S, .028 * S), (-.040 * S, .028 * S), (0, -.070 * S)):
    rivet(fr, x, y, 0.0065, 0.017)

# estrela bordada na gola: estrela de 8 pontas + estrela de 4 pontas por cima + rebite
xs, zs_ = at(540, 240)
O = surf_front(xs, zs_, 0.078)
fr = frame_from(O, FZ)
star = []
for k in range(8):
    r_ = 0.036 if k % 2 == 0 else 0.012
    a_ = math.pi / 2 + k * math.pi / 4
    star.append((r_ * math.cos(a_), r_ * math.sin(a_)))
extruded(star, 0.006, 0.45, fr)
star4 = []
for k in range(8):
    r_ = 0.022 if k % 2 == 0 else 0.008
    a_ = k * math.pi / 4
    star4.append((r_ * math.cos(a_), r_ * math.sin(a_)))
extruded(star4, 0.012, 0.45, fr, back=0.005)
rivet(fr, 0, 0, 0.004, 0.015)

# tira de couro e dois pendentes com ponta de seta (como na entrada)
xp = img_to_xz(555, 0)[0]
zt_, zb_ = 1.115, 0.64
ys = front_y(xp, 0.9) - 0.006
extruded(rect_poly(0.016, zt_ - zb_, 0, (zt_ + zb_) / 2), 0.004, 0.2, (Vector((xp, ys, 0)), Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, -1, 0))), rect="leather")
arrow = mirror([(0, .078), (.012, .040), (.028, .022), (.012, .016), (.010, -.030), (.024, -.052), (0, -.082)])
for z, sc_ in ((0.93, 1.0), (0.70, 0.85)):
    Oz = Vector((xp, front_y(xp, z) - 0.008, z))
    fr = frame_from(Oz, FZ)
    extruded([(x * sc_, y * sc_) for x, y in arrow], 0.011, 0.45, fr)
    extruded([(0, .030 * sc_), (.007, 0.0), (0, -.030 * sc_), (-.007, 0.0)], 0.017, 0.2, fr, back=0.008)
    rivet(fr, 0, .056 * sc_, 0.0045, 0.014)
# fivela-anel do pendente no cinto
frp = frame_from(Vector((xp, front_y(xp, 1.115) - 0.008, 1.115)), FZ)
for dx in (-0.012, 0.012):
    extruded(rect_poly(0.006, 0.03, dx, 0), 0.006, 0.3, frp)
extruded(rect_poly(0.03, 0.006, 0, 0.015), 0.006, 0.3, frp)
extruded(rect_poly(0.03, 0.006, 0, -0.015), 0.006, 0.3, frp)

# losango com rebite no cinto (esquerda)
xl = -0.14
Ol = surf_front(xl, 1.16, 0.044)
frl = frame_from(Ol, (FZ + Vector((-0.45, 0, 0))).normalized())
extruded([(0, .034), (.024, 0), (0, -.034), (-.024, 0)], 0.007, 0.4, frl)
extruded([(0, .016), (.011, 0), (0, -.016), (-.011, 0)], 0.012, 0.3, frl, back=0.004)
rivet(frl, 0, 0, 0.0035, 0.013)

# ---------------- finalizacao da malha
bmesh.ops.triangulate(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("game")
bm.to_mesh(me)
flat_attr = me.attributes.get("flat")
fl = np.zeros(len(me.polygons), np.int32)
if flat_attr:
    flat_attr.data.foreach_get("value", fl)
bm.free()
for p, f in zip(me.polygons, fl):
    p.use_smooth = not f
ob = bpy.data.objects.new("game", me)
bpy.context.scene.collection.objects.link(ob)
part = np.zeros(len(me.vertices), np.int32)
me.attributes["part"].data.foreach_get("value", part)

# ---------------- pesos: transferencia do corpo + ossos Cape
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
CAPE_BODY = {"Chest", "Spine", "Hips", "Neck", "LeftShoulder", "RightShoulder", "LeftUpperArm", "RightUpperArm"}
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
    if part[v.index] == 1:                               # manto: tronco em cima, ossos Cape de baixo
        Wb = {g: (w * 0.5 if g.endswith('UpperArm') else w) for g, w in W2.items() if g in CAPE_BODY}
        if not Wb or sum(Wb.values()) < 1e-6:
            Wb = {"Chest": 1.0}
        tb = sum(Wb.values()) or 1.0; Wb = {g: w / tb for g, w in Wb.items()}
        kz = min(1.0, max(0.0, (1.25 - co.z) / 0.45))
        Wb = {g: w * (1 - kz) for g, w in Wb.items()}
        Wb["Hips"] = Wb.get("Hips", 0) + kz
        s = min(1.0, max(0.0, (1.42 - co.z) / 0.72)) ** 0.85
        wc = 0.93 * s
        sx = max(-1.0, min(1.0, co.x / 0.33))
        wB = (1 - abs(sx)) ** 1.4
        wL = (1 - wB) * (1.0 if sx > 0 else 0.0)
        wR = (1 - wB) * (1.0 if sx <= 0 else 0.0)
        Wf = {g: w * (1 - wc) for g, w in Wb.items()}
        Wf["Cape_L"] = wc * wL; Wf["Cape_R"] = wc * wR; Wf["Cape_B"] = wc * wB
        W2 = Wf
    elif co.z < 1.0:                                     # tabardo e pendente: quadril + coxa do lado (nunca o joelho)
        k = (1.0 - max(co.z, 0.45)) / 0.55
        sd = "Left" if co.x < 0 else "Right"
        W2 = {"Hips": 1 - 0.45 * k, sd + "UpperLeg": 0.45 * k}
    for g, w in W2.items():
        if g in bi:
            Wm[v.index, bi[g]] += w
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
    if part[ids[0]] == 1:
        continue
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
    idxs = [j for j in np.argsort(-Wm[i])[:4] if Wm[i, j] > 1e-5]
    t2 = Wm[i, idxs].sum() or 1
    for j in idxs:
        if True:
            ob.vertex_groups[names[j]].add([i], float(Wm[i, j] / t2), 'REPLACE')
ob.parent = arm
mod = ob.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
bpy.data.objects.remove(body)
me.attributes.remove(me.attributes["part"])
if me.attributes.get("flat"):
    me.attributes.remove(me.attributes["flat"])
bpy.ops.wm.save_as_mainfile(filepath=wpath(cfg, "game_uv.blend"))
print("MBUILD feathers", nfe, "tris", sum(len(p.vertices) - 2 for p in me.polygons), "verts", nv)
