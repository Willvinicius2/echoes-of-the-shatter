"""Aljava do arqueiro dark v3 (Blender -b, CPU): corpo (body.blend do aljava_v3_body.py) + boca concava com cinta de metal,
flechas com penas curvas, alca em curva 3D com fivelas, emblema em camadas e pingente. Tudo geometria por script.
uso: blender -b -P aljava_v3_build.py -- <body.blend> <tex_dir> <out_glb> <out_blend>"""
import bpy, bmesh, sys, math, random
from mathutils import Vector, Matrix
body_blend, tex, out_glb, out_blend = sys.argv[sys.argv.index("--") + 1:][:4]
random.seed(31)
THETA = math.radians(9.9); ORG = Vector((0, 0, -0.1))
M = Matrix.Translation(ORG) @ Matrix.Rotation(THETA, 4, 'Y'); Mi = M.inverted()
S_TOP = 0.178; R_TUBE = 0.0415
SEGS = 24

bpy.ops.wm.open_mainfile(filepath=body_blend)
body = bpy.data.objects["SM_ArcherDark_Quiver_Body"]
body.data.transform(Mi)          # referencial do eixo
for ca in list(body.data.color_attributes): body.data.color_attributes.remove(ca)   # cor de vertice da v1 estragaria o remendo


def mat(name, img=None, nrm=None, rough=0.7, metal=0.0, color=(0.05, 0.04, 0.04, 1), alpha=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bs = nt.nodes["Principled BSDF"]
    bs.inputs["Roughness"].default_value = rough; bs.inputs["Metallic"].default_value = metal
    bs.inputs["Base Color"].default_value = color
    if img:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(img); t.image.colorspace_settings.name = 'sRGB'
        nt.links.new(t.outputs["Color"], bs.inputs["Base Color"])
        if alpha: nt.links.new(t.outputs["Alpha"], bs.inputs["Alpha"])
    if nrm:
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(nrm); tn.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 1.0
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    m.use_backface_culling = not alpha
    if alpha:
        try: m.blend_method = 'CLIP'
        except Exception: pass
        try: m.surface_render_method = 'DITHERED'
        except Exception: pass
        m["gltf_alpha_mode"] = "MASK"
    return m


m_body = mat("M_ArcherDark_Quiver_Body", tex + "/T_ArcherDark_Quiver_Body_BC.png", tex + "/T_ArcherDark_Quiver_Body_N.png", rough=0.72)
m_in = mat("M_ArcherDark_Quiver_Inside", tex + "/T_ArcherDark_Inside_BC.png", rough=0.95)
m_metal = mat("M_ArcherDark_Metal", tex + "/T_ArcherDark_Emblem_BC.png", rough=0.38, metal=0.6)
m_arr = mat("M_ArcherDark_Arrows", tex + "/T_ArcherDark_Arrows_BC.png", rough=0.6, alpha=True)
m_strap = mat("M_ArcherDark_Strap", tex + "/T_ArcherDark_Strap_BC.png", tex + "/T_ArcherDark_Strap_N.png", rough=0.7)
m_patch = mat("M_ArcherDark_Quiver_Patch", tex + "/T_ArcherDark_Patch_BC.png", rough=0.8)
m_emb = mat("M_ArcherDark_Emblem", tex + "/T_ArcherDark_Emblem_BC.png", rough=0.38, metal=0.6)

# regioes do atlas de metal 512 (u, v)
UV_PLATE = (0.25, 0.75); UV_STAR = (0.75, 0.75); UV_GEM = (0.5, 0.375); UV_COLLAR = (0.25, 0.125); UV_DARK = (0.75, 0.125)
UV_LEATHER = (0.25, 0.5); UV_MET_S = (0.75, 0.5)      # alca: couro (esq) e metal (dir)


class B:
    def __init__(s): s.v = []; s.f = []; s.uv = []; s.fm = []
    def vert(s, p, uv): s.v.append(tuple(p)); s.uv.append(tuple(uv)); return len(s.v) - 1
    def tri(s, a, b, c, m=0): s.f.append((a, b, c)); s.fm.append(m)
    def quad(s, a, b, c, d, m=0): s.f.append((a, b, c, d)); s.fm.append(m)


def uvk(face_uv): return face_uv


def bevbox(b, c, ax, ay, az, hx, hy, hz, bev, uv, m=0):
    """caixa com chanfro (bevel de 1 segmento), eixos locais ax/ay/az."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
    for v in bm.verts: v.co = Vector((v.co.x * hx, v.co.y * hy, v.co.z * hz))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bev, segments=1, affect='EDGES')
    bm.verts.ensure_lookup_table(); idx = {}
    for v in bm.verts: idx[v.index] = b.vert(c + ax * v.co.x + ay * v.co.y + az * v.co.z, uv)
    flip = (ax.cross(ay)).dot(az) < 0
    for f in bm.faces:
        vs = [idx[v.index] for v in f.verts]
        b.f.append(tuple(vs[::-1] if flip else vs)); b.fm.append(m)
    bm.free()


def frame_rect(b, c, ax, ay, az, hx, hy, ht, bar, bev, uv, m=0):
    """moldura retangular com furo e chanfro (eixo az = espessura)."""
    loops = [(hx, hy, -ht), (hx, hy, ht - bev), (hx - bev, hy - bev, ht), (hx - bar + bev, hy - bar + bev, ht),
             (hx - bar, hy - bar, ht - bev), (hx - bar, hy - bar, -ht)]
    rings = []
    for (X, Y, Z) in loops:
        rings.append([b.vert(c + ax * sx * X + ay * sy * Y + az * Z, uv) for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    flip = (ax.cross(ay)).dot(az) < 0
    for i in range(len(rings) - 1):
        for j in range(4):
            q = (rings[i][j], rings[i][(j + 1) % 4], rings[i + 1][(j + 1) % 4], rings[i + 1][j])
            b.f.append(tuple(q[::-1] if not flip else q)); b.fm.append(m)
    for j in range(4):   # fundo
        q = (rings[0][j], rings[0][(j + 1) % 4], rings[5][(j + 1) % 4], rings[5][j])
        b.f.append(tuple(q if not flip else q[::-1])); b.fm.append(m)


def dome(b, c, nrm, rad, h, uv, n=6, m=0):
    """rebite: aro de n lados + calota."""
    ref = Vector((0, 0, 1)) if abs(nrm.z) < 0.9 else Vector((1, 0, 0))
    e1 = nrm.cross(ref).normalized(); e2 = nrm.cross(e1).normalized()
    ring = [b.vert(c + (e1 * math.cos(2 * math.pi * k / n) + e2 * math.sin(2 * math.pi * k / n)) * rad, uv) for k in range(n)]
    ring2 = [b.vert(c + nrm * h * 0.62 + (e1 * math.cos(2 * math.pi * k / n) + e2 * math.sin(2 * math.pi * k / n)) * rad * 0.62, uv) for k in range(n)]
    top = b.vert(c + nrm * h, uv)
    for k in range(n):
        k2 = (k + 1) % n
        b.quad(ring[k], ring[k2], ring2[k2], ring2[k], m)
        b.tri(ring2[k], ring2[k2], top, m)


def finish(name, b, mats, angle=35, existing=None):
    me = bpy.data.meshes.new(name); me.from_pydata(b.v, [], b.f); me.update()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        poly.material_index = b.fm[poly.index]; poly.use_smooth = True
        for li in poly.loop_indices: uv.data[li].uv = b.uv[me.loops[li].vertex_index]
    for m in mats: me.materials.append(m)
    bm = bmesh.new(); bm.from_mesh(me)
    bm.normal_update()
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(angle): e.smooth = False
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o


def orient_out(o, center_fn):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median(); d = c - center_fn(c)
        if f.normal.dot(d) < 0: f.normal_flip()
    bm.normal_update(); bm.to_mesh(o.data); bm.free()


# ============================ BOCA: cinta + interior concavo (no corpo) ============================
bd = B()
prof = [((0.0436, 0.1080), 0, UV_COLLAR), ((0.0470, 0.1130), 0, UV_COLLAR), ((0.0470, 0.1435), 0, UV_COLLAR), ((0.0470, 0.1815), 0, UV_COLLAR),
        ((0.0456, 0.1868), 0, UV_STAR), ((0.0394, 0.1868), 0, UV_STAR), ((0.0378, 0.1838), 1, None),
        ((0.0376, 0.150), 1, None), ((0.0358, 0.112), 1, None), ((0.0298, 0.100), 1, None), ((0.0160, 0.0965), 1, None), ((0.0, 0.0955), 1, None)]
rings = []
for i, ((r, z), mi, uvc) in enumerate(prof):
    if i < 5: uvs = [uvc] * SEGS
    else:
        vv = 1.0 - (i - 5) / 6.0 * 0.98; uvs = [(0.5, vv)] * SEGS
    if r == 0.0:
        rings.append([bd.vert((0, 0, z), (0.5, 0.02))])
    else:
        rings.append([bd.vert((r * math.cos(2 * math.pi * j / SEGS), r * math.sin(2 * math.pi * j / SEGS), z), uvs[j]) for j in range(SEGS)])
for i in range(len(prof) - 1):
    m = prof[i + 1][1]
    for j in range(SEGS):
        j2 = (j + 1) % SEGS
        if len(rings[i + 1]) == 1: bd.tri(rings[i][j], rings[i][j2], rings[i + 1][0], m)
        else: bd.quad(rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j], m)
# parte inferior do aro (fecha por baixo da cinta contra o corpo)
# rebites da cinta
for k in range(12):
    a = (k + 0.5) / 12 * 2 * math.pi
    dome(bd, Vector((0.0470 * math.cos(a), 0.0470 * math.sin(a), 0.1500)), Vector((math.cos(a), math.sin(a), 0)), 0.0020, 0.0016, UV_STAR, 6)
# funde na malha do corpo
bm = bmesh.new(); bm.from_mesh(body.data)
uvl = bm.loops.layers.uv.active
nv = [bm.verts.new(p) for p in bd.v]
for f, m in zip(bd.f, bd.fm):
    face = bm.faces.new([nv[i] for i in f]); face.material_index = 1 if m == 1 else 2; face.smooth = True
    for lp in face.loops: lp[uvl].uv = bd.uv[bd.v.index(tuple(lp.vert.co))] if False else lp[uvl].uv
bm.verts.ensure_lookup_table()
# UV por vertice novo
newmap = {nv[i]: bd.uv[i] for i in range(len(nv))}
for f in bm.faces:
    if f.material_index in (1, 2) and all(v in newmap for v in f.verts):
        for lp in f.loops: lp[uvl].uv = newmap[lp.vert]
# materiais: 0 corpo, 1 interior (preenchimentos antigos do corpo usam 1 tambem), 2 metal
for e in bm.edges:
    if len(e.link_faces) == 2 and all(f.material_index != 0 for f in e.link_faces) and e.calc_face_angle(0) > math.radians(38): e.smooth = False
bm.to_mesh(body.data); bm.free()
for i, m in enumerate((m_body, m_in, m_metal, m_patch)): body.data.materials[i] = m
body.name = body.data.name = "SM_ArcherDark_Quiver_Body"


# ============================ FLECHAS ============================
ba = B()
FW = (0.0, 0.25, 0.5, 0.75)   # u0 das variantes de pena no atlas
def fuv(var, x, q): return (FW[var] + 0.25 * (0.5 + x * 0.5), 0.5 + 0.5 * q)   # x -1..1 ; q 0 base .. 1 ponta


def feather_card(b, base, ax, rad, nrm, length, halfw, var, cup, bend, cols=3, rows=5):
    ring = []
    for r in range(rows + 1):
        q = r / rows
        row = []
        for c in range(cols):
            x = -1 + 2 * c / (cols - 1)
            p = base + ax * (length * q) + rad * (halfw * x) + nrm * (cup * x * x * (1 - 0.5 * q) + bend * q * q)
            row.append(b.vert(p, fuv(var, x, q)))
        ring.append(row)
    for r in range(rows):
        for c in range(cols - 1):
            b.quad(ring[r][c], ring[r][c + 1], ring[r + 1][c + 1], ring[r + 1][c])


disk = [(0, 0), (0.0235, 0.004), (-0.0235, -0.004), (0.004, 0.0235), (-0.004, -0.0235),
        (0.0165, 0.0165), (-0.0165, -0.0165), (0.0165, -0.0165), (-0.0165, 0.0165)]
heights = [0.205, 0.235, 0.185, 0.22, 0.195, 0.245, 0.18, 0.228, 0.20]
for k, (px, py) in enumerate(disk):
    rr = math.hypot(px, py); tilt = 0.035 + rr * 3.0
    ang = math.atan2(py, px) if rr > 1e-6 else 1.0
    d = Vector((math.cos(ang) * math.sin(tilt), math.sin(ang) * math.sin(tilt), 0)); d.z = math.sqrt(max(0, 1 - d.x ** 2 - d.y ** 2))
    base = Vector((px, py, 0.115)); L = heights[k]
    ax = d.normalized(); ref = Vector((0, 1, 0)) if abs(ax.y) < 0.9 else Vector((1, 0, 0))
    e1 = ax.cross(ref).normalized(); e2 = ax.cross(e1).normalized()
    roll = random.random() * 2 * math.pi
    e1, e2 = e1 * math.cos(roll) + e2 * math.sin(roll), -e1 * math.sin(roll) + e2 * math.cos(roll)
    top = base + ax * (L + (S_TOP - 0.115))
    # haste (hexagono)
    r = 0.0031; r0 = []; r1 = []
    for j in range(6):
        a = j / 6 * 2 * math.pi; off = e1 * math.cos(a) * r + e2 * math.sin(a) * r
        r0.append(ba.vert(base + off, (0.12 + 0.01 * j, 0.25))); r1.append(ba.vert(top + off, (0.12 + 0.01 * j, 0.25)))
    for j in range(6): ba.quad(r0[j], r0[(j + 1) % 6], r1[(j + 1) % 6], r1[j])
    # ponta rosa em losango com bisel
    U = lambda x, y: (0.5 + 0.25 * x, 0.5 - 0.5 * y)
    prof_h = [(top - ax * 0.003, 0.0042, 0.0042, (0.34, 0.40)), (top + ax * 0.004, 0.0108, 0.0046, (0.38, 0.40)),
              (top + ax * 0.0125, 0.0092, 0.0040, (0.36, 0.30)), (top + ax * 0.0215, 0.0040, 0.0020, (0.34, 0.15))]
    hr = []
    for (pc, wa, wb, uv) in prof_h:
        hr.append([ba.vert(pc + e1 * wa, uv), ba.vert(pc + e2 * wb, (uv[0] + 0.02, uv[1])), ba.vert(pc - e1 * wa, uv), ba.vert(pc - e2 * wb, (uv[0] + 0.02, uv[1]))])
    apex = ba.vert(top + ax * 0.036, (0.36, 0.04))
    for j in range(4):
        j2 = (j + 1) % 4
        for i in range(len(hr) - 1): ba.quad(hr[i][j], hr[i][j2], hr[i + 1][j2], hr[i + 1][j])
        ba.tri(hr[-1][j], hr[-1][j2], apex)
    # penas: 3 cartoes curvos em torno da haste
    var = (k % 3)
    lscale = 0.9 + 0.2 * random.random(); wscale = 0.85 + 0.3 * random.random()
    s_lo = top - ax * (0.083 * lscale); length = 0.072 * lscale
    for ci in range(3):
        a = ci / 3 * 2 * math.pi + roll * 0.0 + random.uniform(-0.2, 0.2) + 0.4 * k
        rad = e1 * math.cos(a) + e2 * math.sin(a); nrm = ax.cross(rad).normalized()
        feather_card(ba, s_lo + rad * 0.0, ax, rad, nrm, length, 0.0125 * wscale * (0.9 + 0.2 * random.random()), (var + ci) % 3,
                     cup=0.0045 * random.choice((-1, 1)), bend=0.0045 * random.choice((-1, 1)) + 0.002)
arrows = finish("SM_ArcherDark_Quiver_Arrows", ba, [m_arr], angle=50)


# ============================ ALCA (curva 3D com bevel) ============================
bs = B()
HW = 0.0125; HT = 0.0028; CH = 0.0012
key = [(-0.0445, 0.118), (-0.0545, 0.1205), (-0.0740, 0.1135), (-0.0925, 0.0900), (-0.1045, 0.0520), (-0.1085, 0.0100),
       (-0.1020, -0.0250), (-0.0820, -0.0480), (-0.0600, -0.0580), (-0.0455, -0.0555)]
YA, YB = -0.0125, 0.0030


def catmull(pts, n):
    out = []; P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        for s in range(n):
            t = s / n; p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t ** 3) for k in range(2)))
    out.append(pts[-1]); return out


cp = catmull(key, 4)
# reamostra por comprimento de arco
acc = [0.0]
for i in range(1, len(cp)): acc.append(acc[-1] + math.hypot(cp[i][0] - cp[i - 1][0], cp[i][1] - cp[i - 1][1]))
TOTAL = acc[-1]; NS = 28; pts = []
for i in range(NS + 1):
    s = TOTAL * i / NS; j = max(1, next((q for q in range(1, len(acc)) if acc[q] >= s), len(acc) - 1))
    t = (s - acc[j - 1]) / max(1e-9, acc[j] - acc[j - 1]); x = cp[j - 1][0] + (cp[j][0] - cp[j - 1][0]) * t; z = cp[j - 1][1] + (cp[j][1] - cp[j - 1][1]) * t
    tt = i / NS; y = YA + (YB - YA) * math.sin(math.pi * tt) ** 1.2
    pts.append(Vector((x, y, z)))
frames = []
for i, p in enumerate(pts):
    tg = (pts[min(i + 1, NS)] - pts[max(i - 1, 0)]).normalized()
    W = Vector((0, 1, 0)); W = (W - tg * W.dot(tg)).normalized()
    N = tg.cross(W).normalized()                          # espessura
    if N.x > 0 and i == 0: pass
    frames.append((tg, W, N))
# N deve apontar para fora do laco (afastando do tubo) -> no meio, N.x < 0
if frames[NS // 2][2].x > 0: frames = [(t, -w, -n) for (t, w, n) in frames]
LEN_TEX = 0.20
cols = []
for i, p in enumerate(pts):
    tg, W, N = frames[i]; v = acc[min(len(acc) - 1, 0)] if False else (TOTAL * i / NS) / LEN_TEX
    ring = [(-HW + CH, HT, 0.05), (HW - CH, HT, 0.45), (HW, 0.0, 0.49), (HW - CH, -HT, 0.45), (-HW + CH, -HT, 0.05), (-HW, 0.0, 0.01)]
    cols.append([bs.vert(p + W * a + N * b_, (u, v)) for (a, b_, u) in ring])
for i in range(NS):
    for j in range(6):
        j2 = (j + 1) % 6
        bs.quad(cols[i][j], cols[i][j2], cols[i + 1][j2], cols[i + 1][j])
for ringv, flip in ((cols[0], True), (cols[NS], False)):
    for j in range(1, 5):
        bs.tri(ringv[0], ringv[j + 1], ringv[j]) if not flip else bs.tri(ringv[0], ringv[j], ringv[j + 1])


def at(t):
    i = max(0, min(NS, int(round(t * NS)))); return pts[i], frames[i]


# placas de ancoragem (cinta superior e inferior) com rebites
for t, sgn in ((0.0, 1), (1.0, -1)):
    p, (tg, W, N) = at(t)
    tgd = tg if t == 0.0 else -tg
    c = p + tgd * 0.003 + N * (HT + 0.0017)
    bevbox(bs, c, tgd, W, N, 0.0125, HW + 0.0050, 0.0017, 0.0008, UV_MET_S)
    for sx in (-1, 1):
        for sy in (-1, 1):
            dome(bs, c + tgd * 0.0075 * sx + W * 0.0085 * sy + N * 0.0017, N, 0.0017, 0.0013, UV_MET_S, 6)
# fivelas
for t, tail in ((0.30, False), (0.66, True)):
    p, (tg, W, N) = at(t)
    c = p + N * (HT + 0.0018)
    frame_rect(bs, c, tg, W, N, 0.0095, HW + 0.0050, 0.0018, 0.0035, 0.0007, UV_MET_S)
    bevbox(bs, c + N * 0.0008, tg, W, N, 0.0013, HW + 0.0010, 0.0016, 0.0005, UV_MET_S)               # lingueta (barra central)
    pk, (tk, Wk, Nk) = at(t + 0.075)
    frame_rect(bs, pk + Nk * (HT + 0.0014), tk, Wk, Nk, 0.0038, HW + 0.0016, 0.0013, 0.0017, 0.0005, UV_LEATHER)   # passador de couro
    for sy in (-1, 1): dome(bs, pk + Nk * (HT + 0.0026) + Wk * (HW - 0.0004) * sy, Nk, 0.0014, 0.0011, UV_MET_S, 6)
    if tail:   # ponta de couro com extremidade afilada, saindo da fivela
        pt, (tt_, Wt, Nt) = at(t - 0.02)
        base_c = c - tg * 0.011 + N * 0.0021; Lt = 0.021
        shape = [(-0.0, -HW + 0.001), (Lt * 0.62, -HW + 0.001), (Lt, 0.0), (Lt * 0.62, HW - 0.001), (0.0, HW - 0.001)]
        for hz, (zo, m) in ((0.0, (0.0, 0)), ):
            top_v = [bs.vert(base_c - tg * 0.011 + tg * (x + 0.0) + W * y + N * 0.0017, (0.25 + 0.2 * (y / HW), 0.3 + 0.02 * x)) for (x, y) in shape]
            bot_v = [bs.vert(base_c - tg * 0.011 + tg * (x + 0.0) + W * y + N * -0.0017, (0.25 + 0.2 * (y / HW), 0.3 + 0.02 * x)) for (x, y) in shape]
            n5 = len(shape)
            bs.f.append(tuple(top_v)); bs.fm.append(0)
            bs.f.append(tuple(bot_v[::-1])); bs.fm.append(0)
            for j in range(n5):
                j2 = (j + 1) % n5; bs.quad(top_v[j2], top_v[j], bot_v[j], bot_v[j2])
# rebites no couro
for t in (0.12, 0.50, 0.86):
    p, (tg, W, N) = at(t)
    for sy in (-1, 1): dome(bs, p + N * HT + W * (HW - 0.0033) * sy, N, 0.0016, 0.0013, UV_MET_S, 6)
strap = finish("SM_ArcherDark_Quiver_Strap", bs, [m_strap], angle=40)
orient_out(strap, lambda c: Vector((-0.04, c.y * 0.0 - 0.0, 0.03)) if False else Vector((-0.07, c.y, 0.03)))


# ============================ EMBLEMA em camadas ============================
be = B()
VC = 0.066


def wrap(u, v, h, phi0=0.0):
    ph = u / R_TUBE + phi0; r = R_TUBE + h
    return Vector((r * math.sin(ph), -r * math.cos(ph), VC + v))


def star_outline(tl, r_in):
    o = []
    for k in range(4):
        a = k * math.pi / 2; L = tl[k % 2]
        o.append((L * math.cos(a), L * math.sin(a), 0))
        bb = a + math.pi / 4
        o.append((r_in * math.cos(bb), r_in * math.sin(bb), 1))
    return o


def layered(b, outl, rhos, hfun, uv, wall_h=None, center_h=None, m=0):
    """placa estrela: aneis concentricos (rho) com altura h(rho, inner), centro e parede."""
    ctr = b.vert(wrap(0, 0, center_h), uv)
    rg = []
    for rho in rhos:
        rg.append([b.vert(wrap(x * rho, y * rho, hfun(rho, inner)), uv) for (x, y, inner) in outl])
    n = len(outl)
    for j in range(n): b.tri(ctr, rg[0][(j + 1) % n], rg[0][j], m)
    for r in range(len(rhos) - 1):
        for j in range(n): b.quad(rg[r][j], rg[r][(j + 1) % n], rg[r + 1][(j + 1) % n], rg[r + 1][j], m)
    if wall_h is not None:
        wl = [b.vert(wrap(x * rhos[-1], y * rhos[-1], wall_h), uv) for (x, y, inner) in outl]
        for j in range(n): b.quad(rg[-1][j], wl[j], wl[(j + 1) % n], rg[-1][(j + 1) % n], m)
    return rg


PL_H = 0.0030
plate_o = star_outline((0.036, 0.056), 0.0185)
layered(be, plate_o, [0.35, 0.65, 0.88, 0.97, 1.0], lambda r, i: PL_H - 0.0005 * (r > 0.95) * 1 - 0.0007 * (r > 0.99) - 0.0001 * (1 - r) * 0, UV_PLATE, wall_h=-0.0015, center_h=PL_H)
# aro (moldura) da placa: segundo nivel mais claro, so uma borda interna
frame_o = star_outline((0.0305, 0.047), 0.0152)
layered(be, frame_o, [0.55, 0.88, 1.0], lambda r, i: PL_H + 0.0008 + (0.0005 if r < 0.7 else 0.0) - 0.0004 * (r > 0.95), UV_STAR, wall_h=PL_H - 0.0003, center_h=PL_H + 0.0018)
star_o = star_outline((0.0255, 0.0415), 0.0085)
layered(be, star_o, [0.28, 0.62, 1.0], lambda r, i: PL_H + 0.0020 + (0.0034 if not i else 0.0016) * (1 - r) ** 0.9 + 0.0006, UV_STAR, wall_h=PL_H + 0.0014, center_h=PL_H + 0.0100)
# gema rosa (bipiramide de 6 lados)
gz = PL_H + 0.0103; gn = 6
gring = [be.vert(wrap(0.0052 * math.cos(2 * math.pi * k / gn), 0.0090 * math.sin(2 * math.pi * k / gn), gz), UV_GEM) for k in range(gn)]
gring2 = [be.vert(wrap(0.0032 * math.cos(2 * math.pi * k / gn), 0.0054 * math.sin(2 * math.pi * k / gn), gz + 0.0026), (0.55, 0.4)) for k in range(gn)]
gtop = be.vert(wrap(0, 0, gz + 0.0044), (0.5, 0.45))
for k in range(gn):
    k2 = (k + 1) % gn
    be.quad(gring[k], gring[k2], gring2[k2], gring2[k]); be.tri(gring2[k], gring2[k2], gtop)
# rebites nas pontas
for k in range(4):
    a = k * math.pi / 2; L = (0.036, 0.056)[k % 2] * 0.84
    cpos = wrap(L * math.cos(a), L * math.sin(a), PL_H - 0.0004)
    nrm = Vector((cpos.x, cpos.y, 0)).normalized()
    dome(be, cpos, nrm, 0.0021, 0.0022, UV_STAR, 6)
# argola do pingente (torus, preso na ponta inferior da placa)
ring_c = wrap(0, -0.0600, 0.0012)
rn = Vector((ring_c.x, ring_c.y, 0)).normalized()
tdir = Vector((1, 0, 0))
def torus(b, c, a1, a2, R, r, n1, n2, uv):
    vs = []
    for i in range(n1):
        t = 2 * math.pi * i / n1; cc = c + (a1 * math.cos(t) + a2 * math.sin(t)) * R; rad = (a1 * math.cos(t) + a2 * math.sin(t))
        nrm = a1.cross(a2)
        vs.append([b.vert(cc + (rad * math.cos(2 * math.pi * j / n2) + nrm * math.sin(2 * math.pi * j / n2)) * r, uv) for j in range(n2)])
    for i in range(n1):
        i2 = (i + 1) % n1
        for j in range(n2):
            j2 = (j + 1) % n2; b.quad(vs[i][j], vs[i][j2], vs[i2][j2], vs[i2][j])
torus(be, ring_c + rn * 0.0016, tdir, Vector((0, 0, 1)), 0.0034, 0.0010, 8, 4, UV_DARK)
emblem = finish("SM_ArcherDark_Quiver_Emblem", be, [m_emb], angle=30)
orient_out(emblem, lambda c: Vector((0, 0, c.z)))


# ============================ PINGENTE ============================
bp = B()
pc = wrap(0, -0.0770, 0.0042)           # centro do losango (pendurado na argola)
pn = Vector((pc.x, pc.y, 0)).normalized(); pt_ = Vector((1, 0, 0)); pz = Vector((0, 0, 1))
# anel pequeno de ligacao
torus(bp, wrap(0, -0.0665, 0.0030), pt_, pz, 0.0022, 0.0007, 6, 4, UV_DARK)
HWd, HHd = 0.0058, 0.0125
def dp(x, y, h): return pc + pt_ * x + pz * y + pn * h
pa = [bp.vert(dp(0, HHd, 0), UV_STAR), bp.vert(dp(HWd, 0, 0), UV_STAR), bp.vert(dp(0, -HHd, 0), UV_STAR), bp.vert(dp(-HWd, 0, 0), UV_STAR)]
pb = [bp.vert(dp(0, HHd * 0.58, 0.0020), UV_PLATE), bp.vert(dp(HWd * 0.58, 0, 0.0020), UV_PLATE), bp.vert(dp(0, -HHd * 0.58, 0.0020), UV_PLATE), bp.vert(dp(-HWd * 0.58, 0, 0.0020), UV_PLATE)]
pc2 = [bp.vert(dp(0, HHd * 0.58, -0.0020), UV_PLATE), bp.vert(dp(HWd * 0.58, 0, -0.0020), UV_PLATE), bp.vert(dp(0, -HHd * 0.58, -0.0020), UV_PLATE), bp.vert(dp(-HWd * 0.58, 0, -0.0020), UV_PLATE)]
cf = bp.vert(dp(0, 0, 0.0032), UV_GEM); cb = bp.vert(dp(0, 0, -0.0032), UV_PLATE)
for j in range(4):
    j2 = (j + 1) % 4
    bp.quad(pa[j], pa[j2], pb[j2], pb[j]); bp.tri(pb[j], pb[j2], cf)
    bp.quad(pa[j2], pa[j], pc2[j], pc2[j2]); bp.tri(pc2[j2], pc2[j], cb)
# tirinhas de pena rosa
UVF = lambda x, q: (0.75 + 0.25 * (0.5 + x * 0.5), 0.5 + 0.5 * q)
sp = dp(0, -HHd + 0.001, 0.0)
for (xo, ln, sway) in ((-0.0035, 0.034, -0.002), (0.0, 0.044, 0.0015), (0.0035, 0.030, 0.0025)):
    rows = 4; ringp = []
    for r in range(rows + 1):
        q = r / rows; cen = sp + pt_ * (xo + sway * q * q) - pz * (ln * q) + pn * (0.0004 + 0.0018 * q * q)
        ringp.append([bp.vert(cen + pt_ * (0.0042 * x), UVF(x, q * 0.9 + 0.05)) for x in (-1, 0, 1)])
    for r in range(rows):
        for c in range(2): bp.quad(ringp[r][c], ringp[r][c + 1], ringp[r + 1][c + 1], ringp[r + 1][c])
# separa materiais: tirinhas usam material de penas
fm_n = len(bp.f)
pendant = finish("SM_ArcherDark_Quiver_Pendant", bp, [m_emb, m_arr], angle=30)
# faces das tirinhas (as ultimas 3*4*2 quads) = material 1
nq = 3 * 4 * 2
for p in pendant.data.polygons:
    if p.index >= fm_n - nq: p.material_index = 1
bm = bmesh.new(); bm.from_mesh(pendant.data)
for f in bm.faces:
    if f.material_index == 0:
        pass
bm.free()
orient_out_ok = True


# ============================ mundo e hierarquia ============================
body.data.materials  # ja configurado
root = bpy.data.objects.new("SM_ArcherDark_Quiver", None); bpy.context.scene.collection.objects.link(root)
objs = [body, arrows, strap, emblem, pendant]
for o in objs:
    if o.name not in bpy.context.scene.collection.objects: bpy.context.scene.collection.objects.link(o)
    o.data.transform(M); o.parent = root; o.data.update()
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
bpy.ops.object.select_all(action='DESELECT')
for o in objs + [root]: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                          export_image_format='AUTO', export_materials='EXPORT', export_cameras=False, export_lights=False,
                          export_normals=True, export_texcoords=True)
tr = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs}
print("TRIS", tr, sum(tr.values()))
