"""Botas do arqueiro dark por codigo (Blender): volume do cano e do pe (aneis por altura em cima da pele do corpo, offset 4-6 mm), bico em ponta,
colarinho dobrado, sola e salto de madeira; tiras, fivelas e ornamentos de ponta de flecha em metal como geometria a parte, posicionados
pelas coordenadas da imagem de entrada (arq3d_botas) e com UV projetada da mesma imagem. Bota +X modelada e espelhada para -X.
Grava work/game_uv.blend (objeto "game", pesos transferidos do corpo, max 4 influencias, mesmo esqueleto de 30 ossos).
Uso: blender -b --factory-startup -P botas_build.py -- arq_dark_botas"""
import bpy, bmesh, sys, os, math, json
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from botas_atlas import *
from manto_add_cape_bones import add_cape_bones

cfg = load_cfg()
P_ = cfg.get("params", {})
OFF = P_.get("off", 0.005)
NA = 20
USC = 0.9      # fracao da meia-largura da silhueta usada na projecao (borda externa tem tiras/pendentes soltos)
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(cfg["body_rig_blend"]), "game_uv.blend"))
body = bpy.data.objects["game"]
body.name = "body_ref"; body.data.name = "body_ref"
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
add_cape_bones(arm)
bm_b = bmesh.new(); bm_b.from_mesh(body.data)
bvh = BVHTree.FromBMesh(bm_b)
bvgroups = {g.index: g.name for g in body.vertex_groups}
bw = [{bvgroups[g.group]: g.weight for g in v.groups} for v in body.data.vertices]
V = np.array([v.co[:] for v in body.data.vertices])
LV = V[(V[:, 0] > 0.04) & (V[:, 2] < 0.7)]


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ---------- centro de cada altura (bbox dos vertices da perna +X, suavizado)
zs_f = np.arange(0.0, 0.62, 0.01)
cen = []
for z in zs_f:
    w = 0.014
    while True:
        s = LV[abs(LV[:, 2] - z) < w]
        if len(s) >= 6:
            break
        w += 0.006
    cen.append(((s[:, 0].min() + s[:, 0].max()) / 2, (s[:, 1].min() + s[:, 1].max()) / 2))
cen = np.array(cen)
k = np.ones(3) / 3
cx_s = np.convolve(np.pad(cen[:, 0], 1, mode='edge'), k, 'valid'); cy_s = np.convolve(np.pad(cen[:, 1], 1, mode='edge'), k, 'valid')
center = lambda z: Vector((float(np.interp(z, zs_f, cx_s)), float(np.interp(z, zs_f, cy_s)), z))

Z_TOP = P_.get("z_top", 0.50)
ZR = [0.0, 0.014, 0.0165, 0.032, 0.05, 0.068, 0.088, 0.112, 0.145, 0.19, 0.25, 0.31, 0.37, 0.43, 0.47, Z_TOP]
NR = len(ZR)
TH = [2 * math.pi * j / NA for j in range(NA)]
DIRS = [Vector((math.sin(t), -math.cos(t), 0)) for t in TH]


def hit_r(c, d, z):
    o = Vector((c.x, c.y, z))
    loc, nrm, fi, dist = bvh.ray_cast(o, d, 0.35)
    return dist if loc is not None else None


# raio do corpo por angulo e altura; sem hit (ponta do pe): interpola entre hits vizinhos ou, acima do pe, inclina para dentro
zf = np.arange(0.0, 0.62, 0.004)
HT = np.full((NA, len(zf)), np.nan)
for j, d in enumerate(DIRS):
    for k_, z in enumerate(zf):
        h = hit_r(center(float(z)), d, float(max(z, 0.003)))
        if h is not None:
            HT[j, k_] = h
SLOPE = P_.get("toe_slope", 1.5)
RAISE = P_.get("toe_raise", 0.014)


def body_r(j, z):
    k_ = int(round(z / 0.004)); k_ = min(max(k_, 0), len(zf) - 1)
    if not np.isnan(HT[j, k_]):
        return float(HT[j, k_])
    below = [m for m in range(k_ - 1, -1, -1) if not np.isnan(HT[j, m])]
    above = [m for m in range(k_ + 1, len(zf)) if not np.isnan(HT[j, m])]
    kb = below[0] if below else None
    ka = above[0] if above else None
    if kb is not None and ka is not None and (ka - kb) * 0.004 < 0.05:
        t = (k_ - kb) / (ka - kb)
        return float(HT[j, kb] * (1 - t) + HT[j, ka] * t)
    if kb is not None:                       # acima do topo do pe naquela direcao: cupula
        zz = z - (zf[kb] + RAISE)
        return float(HT[j, kb]) if zz <= 0 else float(max(0.012, HT[j, kb] - zz * SLOPE))
    return float(HT[j, ka]) if ka is not None else 0.05


R_ = np.zeros((NR, NA))
for i, z in enumerate(ZR):
    for j in range(NA):
        if z < 0.17:      # envelope: o peito do pe sobe depois do ponto onde o raio horizontal acerta
            R_[i, j] = max(body_r(j, max(z + dz, 0.004)) - 0.55 * dz * (1.0 if dz > 0 else 0.0) for dz in (0.0, 0.012, 0.024, 0.036))
        else:
            R_[i, j] = body_r(j, max(z, 0.004))
for _ in range(2):    # suaviza angularmente (ruido da malha decimada)
    R_ = 0.25 * np.roll(R_, 1, 1) + 0.5 * R_ + 0.25 * np.roll(R_, -1, 1)

# ---------- aneis finais (offset, flare no cano, sola, bico em ponta)
PT = [[None] * NA for _ in range(NR)]
for i, z in enumerate(ZR):
    c = center(z)
    for j in range(NA):
        off = OFF + 0.0035 * math.sin(40 * z + 2.3 * j) * smoothstep(0.1, 0.2, z)
        off += 0.0144 * smoothstep(0.38, Z_TOP, z) ** 1.4          # boca do cano mais larga
        if i < 2:
            off += 0.0075                                          # sola salienta (degrau no anel 2)
        r = R_[i, j] + off
        PT[i][j] = Vector((c.x + DIRS[j].x * r, c.y + DIRS[j].y * r, z))
EXT = P_.get("toe_ext", 0.05); PINCH = P_.get("toe_pinch", 0.28)
for i, z in enumerate(ZR):     # bico: alonga para frente e afina em planta (so abaixo de ~11 cm)
    c = center(z)
    f = 1.0 - smoothstep(0.03, 0.125, z)
    if i <= 2:
        f = 1.0
    for j in range(NA):
        p = PT[i][j]
        fwd = -(p.y - c.y)
        if fwd <= 0:
            continue
        s = min(1.0, fwd / 0.14)
        p.y -= EXT * s ** 2.2 * f
        p.x = c.x + (p.x - c.x) * (1 - PINCH * s ** 2.2 * f)
# empurra para fora todo vertice que ficou a menos de 4,5 mm da pele do corpo (iterativo)
MINC = P_.get("min_clear", 0.0055)
for _ in range(14):
    moved = 0
    for i in range(1, NR):
        for j in range(NA):
            p = PT[i][j]
            loc, nrm, fi, d = bvh.find_nearest(p)
            sg = (p - loc).dot(nrm)
            if sg < MINC:
                p += nrm * (MINC - sg + 0.001); moved += 1
    for i in range(1, NR - 1):        # centro e meios das faces (o corpo pode furar a casca entre vertices)
        for j in range(NA):
            j2 = (j + 1) % NA
            qv = [(i, j), (i, j2), (i + 1, j2), (i + 1, j)]
            pts = [sum((PT[a][b] for a, b in qv), Vector()) / 4] + [(PT[qv[k_][0]][qv[k_][1]] + PT[qv[(k_ + 1) % 4][0]][qv[(k_ + 1) % 4][1]]) / 2 for k_ in range(4)]
            for p in pts:
                loc, nrm, fi, d = bvh.find_nearest(p)
                sg = (p - loc).dot(nrm)
                if sg < MINC - 0.001:
                    for a, b in qv:
                        PT[a][b] += nrm * (MINC - sg + 0.001); moved += 1
    for i in range(NR):
        for j in range(NA):
            PT[i][j].z = max(PT[i][j].z, ZR[i])
    if not moved:
        break
for i in range(NR):     # suaviza o resultado entre vizinhos do mesmo anel (sem entrar na pele)
    pass
TOP = [Vector(PT[NR - 1][j]) for j in range(NA)]

# ---------- estrutura da malha (+X); depois espelhada
VERTS, FACES = [], []     # FACES: (idx, uvs, ref, flat, inward)


def V_(p):
    VERTS.append(Vector(p))
    return len(VERTS) - 1


def F_(idx, uvs, ref, flat=False, inward=False):
    FACES.append((idx, uvs, Vector(ref), flat, inward))


front = [PT[i][0] for i in range(NR)]
arc = [0.0] * NR
for i in range(NR - 2, -1, -1):
    arc[i] = arc[i + 1] + (front[i] - front[i + 1]).length
arc_tot = arc[0] + 0.02
PYI = [min(PY1, PY0 + 14 + (arc[i] / arc_tot) * (PY1 - PY0 - 14)) for i in range(NR)]   # py da imagem por anel (anel 0 = ponta)
PYI[0] = PY1


def ring_x_extent(i):
    xs = [PT[i][j].x for j in range(NA)]
    return (min(xs) + max(xs)) / 2, (max(xs) - min(xs)) / 2


def uv_ring(i, j, edge=False):
    py = PYI[i]
    mid, half = ring_x_extent(i)
    u = (PT[i][j].x - mid) / max(half, 1e-4)
    c_, hw = sil(py)
    return proj_uv(c_ + u * hw * USC, py)


plain_uv = lambda a, b: uv(R["plain"], 0.02 + 0.96 * min(max(a, 0.0), 1.0), 0.02 + 0.96 * min(max(b, 0.0), 1.0), pad=2)
wood_uv = lambda a, b: uv(R["wood"], 0.02 + 0.96 * min(max(a, 0.0), 1.0), 0.02 + 0.96 * min(max(b, 0.0), 1.0), pad=2)

ids = [[V_(PT[i][j]) for j in range(NA)] for i in range(NR)]
for i in range(NR - 1):
    for j in range(NA):
        j2 = (j + 1) % NA
        q = [ids[i][j], ids[i][j2], ids[i + 1][j2], ids[i + 1][j]]
        ref = center(ZR[i])
        ang = TH[j] + math.pi / NA
        nfront = math.cos(ang)        # +1 de frente (theta=0)
        if i <= 1:
            uvs = [wood_uv((j + dj) / NA, 0.5 * di) for dj, di in ((0, 0), (1, 0), (1, 1), (0, 1))]
        elif nfront > 0.1:
            # frente: projecao da imagem. A face que cruza theta=0 usa o lado oposto (u negativo) para o ponto j=0 quando preciso
            def u_of(ii, jj, left):
                py = PYI[ii]; mid, half = ring_x_extent(ii)
                x = PT[ii][jj].x
                u = (x - mid) / max(half, 1e-4)
                c_, hw = sil(py)
                return proj_uv(c_ + u * hw * USC, py)
            uvs = [u_of(i, j, 0), u_of(i, j2, 0), u_of(i + 1, j2, 0), u_of(i + 1, j, 0)]
        else:
            uvs = [plain_uv((j + dj) / NA, ZR[i + di] / 0.52) for dj, di in ((0, 0), (1, 0), (1, 1), (0, 1))]
        F_(q, uvs, ref, flat=(i <= 2))


# colarinho dobrado: rolo externo, borda, parede interna
def lipv(j, dz, dr):
    p = Vector(TOP[j]); d = DIRS[j]
    return V_(Vector((p.x + d.x * dr, p.y + d.y * dr, Z_TOP + dz)))


L1 = [lipv(j, 0.010, 0.012) for j in range(NA)]
L2 = [lipv(j, 0.010, -0.004) for j in range(NA)]
L3 = [lipv(j, -0.030, -0.014) for j in range(NA)]
cz = center(Z_TOP)
for j in range(NA):
    j2 = (j + 1) % NA
    for (a, b, inward, rect) in ((ids[NR - 1], L1, False, "plain"), (L1, L2, False, "plain"), (L2, L3, True, "lining")):
        q = [a[j], a[j2], b[j2], b[j]]
        uvs = [uv(R[rect], 0.05 + 0.9 * (((j + dj) / NA) % 1.0), 0.2 + 0.6 * di, pad=2) for dj, di in ((0, 0), (1, 0), (1, 1), (0, 1))]
        F_(q, uvs, cz + Vector((0, 0, -0.02)) if not inward else cz + Vector((0, 0, 0.5)), flat=False, inward=False)

# salto de madeira: bloco chanfrado sob o calcanhar
ys0 = [PT[1][j].y for j in range(NA)]
yb = max(ys0)
xs_h = [PT[1][j].x for j in range(NA) if PT[1][j].y > yb - 0.05]
hx0, hx1 = min(xs_h) - 0.003, max(xs_h) + 0.003
hy0, hy1 = yb - 0.075, yb + 0.004
HZ, HC = 0.032, 0.006


def rect_loop(z, ins):
    return [V_(Vector(p)) for p in ((hx0 + ins, hy0 + ins, z), (hx1 - ins, hy0 + ins, z), (hx1 - ins, hy1 - ins, z), (hx0 + ins, hy1 - ins, z))]


hb0, hb1, hb2 = rect_loop(0.0, 0), rect_loop(HZ - HC, 0), rect_loop(HZ, HC)
hc = Vector(((hx0 + hx1) / 2, (hy0 + hy1) / 2, 0.016))
for a, b in ((hb0, hb1), (hb1, hb2)):
    for k_ in range(4):
        k2 = (k_ + 1) % 4
        F_([a[k_], a[k2], b[k2], b[k_]], [wood_uv(0.1 + 0.2 * m, 0.1 + 0.1 * n) for m, n in ((0, 0), (1, 0), (1, 1), (0, 1))], hc, flat=True)


# ---------- superficie interpolada para posicionar detalhes
def ring_at(i_f):
    i0 = int(min(max(math.floor(i_f), 0), NR - 2)); t = min(max(i_f - i0, 0.0), 1.0)
    return [PT[i0][j].lerp(PT[i0 + 1][j], t) for j in range(NA)], center(ZR[i0] * (1 - t) + ZR[i0 + 1] * t)


def pt_ring(pts, th):
    f = (th % (2 * math.pi)) / (2 * math.pi) * NA
    j0 = int(f) % NA; t = f - int(f)
    return pts[j0].lerp(pts[(j0 + 1) % NA], t)


def py_to_i(py):
    return float(np.interp(py, PYI[::-1], list(range(NR))[::-1]))


def surf(px, py, off=0.0):
    """ponto e normal da superficie da bota para (px,py) da imagem (frente); u normalizado pela silhueta."""
    i_f = py_to_i(py)
    pts, c = ring_at(i_f)
    c_, hw = sil(py)
    u = max(-0.99, min(0.99, (px - c_) / (hw * USC)))
    i0 = int(min(max(math.floor(i_f), 0), NR - 2))
    mid, half = ring_x_extent(i0)
    ths = np.linspace(-math.pi / 2 * 1.02, math.pi / 2 * 1.02, 61)
    xs = np.array([pt_ring(pts, t).x for t in ths])
    th = float(np.interp(mid + u * half, xs, ths))
    p = pt_ring(pts, th)
    e = 0.02
    pa, pb = pt_ring(pts, th - e), pt_ring(pts, th + e)
    ptsu, _ = ring_at(i_f + 0.15); ptsd, _ = ring_at(i_f - 0.15)
    pu, pd = pt_ring(ptsu, th), pt_ring(ptsd, th)
    n = (pb - pa).cross(pu - pd)
    if n.length < 1e-9:
        n = Vector((math.sin(th), -math.cos(th), 0))
    n.normalize()
    if n.dot(Vector((math.sin(th), -math.cos(th), 0))) < 0:
        n = -n
    return p + n * off, n, th


def ext_poly(poly, base, top, apex, flat=True, inset=0.30):
    pts = [surf(px, py, base) for px, py in poly]
    cpx = sum(p[0] for p in poly) / len(poly); cpy = sum(p[1] for p in poly) / len(poly)
    cs = surf(cpx, cpy, apex)
    n = len(poly)
    vb = [V_(p[0]) for p in pts]
    vt = [V_(surf(cpx + (px - cpx) * (1 - inset), cpy + (py - cpy) * (1 - inset), top)[0]) for px, py in poly]
    vc = V_(cs[0])
    ref = surf(cpx, cpy, -0.02)[0]
    for k_ in range(n):
        k2 = (k_ + 1) % n
        (x1, y1), (x2, y2) = poly[k_], poly[k2]
        ix1, iy1 = cpx + (x1 - cpx) * (1 - inset), cpy + (y1 - cpy) * (1 - inset)
        ix2, iy2 = cpx + (x2 - cpx) * (1 - inset), cpy + (y2 - cpy) * (1 - inset)
        F_([vb[k_], vb[k2], vt[k2], vt[k_]], [proj_uv(x1, y1), proj_uv(x2, y2), proj_uv(ix2, iy2), proj_uv(ix1, iy1)], ref, flat=flat)
        F_([vt[k_], vt[k2], vc], [proj_uv(ix1, iy1), proj_uv(ix2, iy2), proj_uv(cpx, cpy)], ref, flat=flat)


def strap(pl, width_px, segs=6, base=0.0035, top=0.0085):
    pl = np.array(pl, float)
    d = np.diff(pl, axis=0); L = np.hypot(d[:, 0], d[:, 1]); cum = np.concatenate([[0], np.cumsum(L)])
    ss = np.linspace(0, cum[-1], segs + 1)
    cp = np.stack([np.interp(ss, cum, pl[:, 0]), np.interp(ss, cum, pl[:, 1])], 1)
    tang = np.gradient(cp, axis=0); tang /= np.maximum(np.hypot(tang[:, 0], tang[:, 1]), 1e-6)[:, None]
    nor = np.stack([-tang[:, 1], tang[:, 0]], 1)
    rows = []
    for k_ in range(segs + 1):
        a = cp[k_] + nor[k_] * width_px / 2; b = cp[k_]; c = cp[k_] - nor[k_] * width_px / 2
        rows.append(([V_(surf(*a, base)[0]), V_(surf(*b, top)[0]), V_(surf(*c, base)[0])], (a, b, c)))
    ref = surf(*cp[segs // 2], -0.02)[0]
    for k_ in range(segs):
        for q in range(2):
            (ia, pa), (ib, pb) = rows[k_], rows[k_ + 1]
            F_([ia[q], ib[q], ib[q + 1], ia[q + 1]], [proj_uv(*pa[q]), proj_uv(*pb[q]), proj_uv(*pb[q + 1]), proj_uv(*pa[q + 1])], ref, flat=False)


# ---------- layout (coordenadas da imagem arq3d_botas.png, bota da direita da imagem)
STRAPS = [
    ([(822, 252), (880, 258), (940, 262), (1000, 258), (1045, 246)], 34),
    ([(835, 285), (895, 330), (955, 395), (1000, 445)], 28),
    ([(1010, 312), (950, 370), (890, 420), (850, 445)], 28),
    ([(840, 505), (900, 535), (960, 580), (985, 600)], 28),
    ([(990, 505), (930, 545), (880, 585), (850, 610)], 28),
    ([(850, 605), (910, 590), (975, 588)], 30),
    ([(845, 705), (915, 668), (980, 682)], 36),
]
for pl, w in STRAPS:
    strap(pl, w)
METALS = [
    ([(981, 85), (1002, 150), (1047, 198), (988, 214), (952, 356), (916, 216), (852, 192), (930, 155)], 0.0045, 0.010, 0.020),
    ([(945, 352), (982, 374), (958, 394), (948, 436), (932, 394), (910, 374)], 0.0045, 0.0085, 0.014),
    ([(940, 442), (962, 472), (938, 508), (918, 472)], 0.0045, 0.0085, 0.013),
    ([(935, 540), (962, 572), (935, 606), (910, 572)], 0.0045, 0.0085, 0.014),
    ([(980, 652), (995, 705), (980, 765), (962, 705)], 0.0045, 0.0085, 0.013),
    ([(842, 695), (858, 722), (842, 750), (826, 722)], 0.0045, 0.0085, 0.012),
    ([(875, 300), (895, 325), (875, 352), (855, 325)], 0.0045, 0.0085, 0.012),
    ([(980, 846), (1026, 884), (1050, 914), (1006, 936), (930, 916), (950, 880)], 0.0045, 0.0095, 0.016),
]
for poly, b_, t_, a_ in METALS:
    ext_poly(poly, b_, t_, a_)


def frame(cx, cy, w, h, bar=5):
    """fivela: moldura retangular com bisel."""
    out = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]
    inn = [(cx - w / 2 + bar, cy - h / 2 + bar), (cx + w / 2 - bar, cy - h / 2 + bar), (cx + w / 2 - bar, cy + h / 2 - bar), (cx - w / 2 + bar, cy + h / 2 - bar)]
    ref = surf(cx, cy, -0.02)[0]
    vo = [V_(surf(*p, 0.004)[0]) for p in out]; vot = [V_(surf(*p, 0.0105)[0]) for p in out]
    vi = [V_(surf(*p, 0.004)[0]) for p in inn]; vit = [V_(surf(*p, 0.0105)[0]) for p in inn]
    for k_ in range(4):
        k2 = (k_ + 1) % 4
        F_([vo[k_], vo[k2], vot[k2], vot[k_]], [proj_uv(*out[k_]), proj_uv(*out[k2]), proj_uv(*out[k2]), proj_uv(*out[k_])], ref, flat=True)
        F_([vot[k_], vot[k2], vit[k2], vit[k_]], [proj_uv(*out[k_]), proj_uv(*out[k2]), proj_uv(*inn[k2]), proj_uv(*inn[k_])], ref, flat=True)


frame(822, 262, 26, 44)


def hang(th, py0, py1, wd, tipL):
    """tira pendurada na lateral externa + ponta de flecha."""
    pts0, _ = ring_at(py_to_i(py0)); pts1, _ = ring_at(py_to_i(py1))
    p0 = pt_ring(pts0, th); p1 = pt_ring(pts1, th)
    d = Vector((math.sin(th), -math.cos(th), 0))
    o0 = p0 + d * 0.012; o1 = p1 + d * 0.016
    tang = Vector((math.cos(th), math.sin(th), 0))
    ids_ = [V_(o0 - tang * wd), V_(o0 + tang * wd), V_(o1 + tang * wd), V_(o1 - tang * wd)]
    ref = o0 - d * 0.05
    u0 = proj_uv(1026, py0); u1 = proj_uv(1026, py1)
    F_(ids_, [u0, u0, u1, u1], ref)
    tip = o1 + Vector((0, 0, -tipL)) + d * 0.002
    mid = o1 + Vector((0, 0, -tipL * 0.35)) + d * 0.006
    a = V_(o1 - tang * wd * 1.9); b = V_(o1 + tang * wd * 1.9); m1 = V_(mid); t_ = V_(tip)
    u2 = proj_uv(1025, 480)
    F_([a, m1, b], [u2] * 3, ref, flat=True); F_([a, t_, m1], [u2] * 3, ref, flat=True); F_([m1, t_, b], [u2] * 3, ref, flat=True)


hang(math.radians(78), 225, 455, 0.007, 0.05)

# ---------- emite a malha: +X e espelho -X
bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
flat_l = bm.faces.layers.int.new("flat")
for mir in (False, True):
    bv = [bm.verts.new(Vector((-p.x, p.y, p.z)) if mir else p) for p in VERTS]
    for idx, uvs, ref, flat, inward in FACES:
        vs = [bv[i] for i in idx]
        if len(set(id(v) for v in vs)) < len(vs):
            continue
        try:
            f = bm.faces.new(vs)
        except ValueError:
            continue
        for l, u in zip(f.loops, uvs):
            l[uvl].uv = u
        f.normal_update()
        c = f.calc_center_median()
        r = Vector((-ref.x, ref.y, ref.z)) if mir else ref
        if f.normal.dot(c - r) < 0:
            f.normal_flip()
        f[flat_l] = 1 if flat else 0
bmesh.ops.triangulate(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("game")
bm.to_mesh(me)
fl = np.zeros(len(me.polygons), np.int32)
me.attributes["flat"].data.foreach_get("value", fl)
bm.free()
for p, f in zip(me.polygons, fl):
    p.use_smooth = not f
ob = bpy.data.objects.new("game", me)
bpy.context.scene.collection.objects.link(ob)

# ---------- pesos: transferencia do corpo (pernas/pes), 4 influencias
from mathutils import interpolate as mi
deform = {b.name for b in arm.data.bones if b.use_deform}
for n in deform:
    ob.vertex_groups.new(name=n)
names = sorted(deform); bi = {n: i for i, n in enumerate(names)}
nv = len(me.vertices)
Wm = np.zeros((nv, len(names)))
for v in me.vertices:
    loc, nrm, fi, d = bvh.find_nearest(v.co)
    poly = body.data.polygons[fi]
    pv = [body.data.vertices[i].co for i in poly.vertices]
    wts = mi.poly_3d_calc(pv, loc)
    for i, w in zip(poly.vertices, wts):
        for g, ww in bw[i].items():
            if g in bi:
                Wm[v.index, bi[g]] += ww * w
for i in range(nv):
    idxs = [j for j in np.argsort(-Wm[i])[:4] if Wm[i, j] > 1e-5]
    if not idxs:
        idxs = [bi["Hips"]]; Wm[i, bi["Hips"]] = 1
    t2 = Wm[i, idxs].sum() or 1
    for j in idxs:
        ob.vertex_groups[names[j]].add([i], float(Wm[i, j] / t2), 'REPLACE')
ob.parent = arm
mod = ob.modifiers.new("Armature", 'ARMATURE'); mod.object = arm

# ---------- folga em relacao a pele do corpo (distancia assinada ao corpo; negativa = bota por dentro da pele)
clear = []
for v in me.vertices:
    loc, nrm, fi, d = bvh.find_nearest(v.co)
    clear.append((v.co - loc).dot(nrm))
clear = np.array(clear)
print("CLEARANCE min", round(float(clear.min()), 4), "p1", round(float(np.percentile(clear, 1)), 4), "med", round(float(np.median(clear)), 4),
      "verts<0.002", int((clear < 0.002).sum()), "de", nv)
for ii in np.argsort(clear)[:8]:
    print("WORST", int(ii), round(float(clear[ii]),4), tuple(round(c,3) for c in me.vertices[int(ii)].co))
save_json(wpath(cfg, "clearance.json"), dict(clear_min=float(clear.min()), clear_p1=float(np.percentile(clear, 1)), verts_lt_2mm=int((clear < 0.002).sum()), verts=nv))
bpy.data.objects.remove(body)
me.attributes.remove(me.attributes["flat"])
bpy.ops.wm.save_as_mainfile(filepath=wpath(cfg, "game_uv.blend"))
print("BBUILD tris", sum(len(p.vertices) - 2 for p in me.polygons), "verts", nv)
