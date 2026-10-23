"""Aljava do arqueiro dark v4 (Blender -b, CPU): corpo limpo (aljava_v4_body.py) + cinta da boca com relevo e interior concavo,
cinta inferior, flechas com penas curvas e pontas metalicas, alca larga em curva 3D com argolas/placas, emblema em camadas e
pingente com penas brancas. Tudo geometria por script.
uso: blender -b -P aljava_v4_build.py -- <body_v4.blend> <tex_dir> <out_glb> <out_blend>"""
import bpy, bmesh, sys, math, random
from mathutils import Vector, Matrix
body_blend, tex, out_glb, out_blend = sys.argv[sys.argv.index("--") + 1:][:4]
random.seed(41)
THETA = math.radians(9.9); ORG = Vector((0, 0, -0.1))
M = Matrix.Translation(ORG) @ Matrix.Rotation(THETA, 4, 'Y'); Mi = M.inverted()
R_TUBE = 0.0415
SEGS = 24
N_SEG = 20

bpy.ops.wm.open_mainfile(filepath=body_blend)
body = bpy.data.objects["SM_ArcherDark_Quiver_Body"]
body.data.transform(Mi)          # referencial do eixo
LV = [v.co.copy() for v in body.data.vertices]
LZ = []                           # z de cada anel do torno (anel 0 = ponta)
for i in range(1, 1 + 40):
    idx = 1 + (i - 1) * N_SEG
    if idx >= len(LV) - 1: break
    LZ.append(LV[idx].z)


def lathe_r(z, ang):
    """raio do corpo em (z, angulo) no referencial do eixo"""
    k = int(round(((ang - math.pi / 2) % (2 * math.pi)) / (2 * math.pi / N_SEG))) % N_SEG
    zs = LZ; j = 0
    while j < len(zs) - 2 and zs[j + 1] < z: j += 1
    t = max(0.0, min(1.0, (z - zs[j]) / (zs[j + 1] - zs[j])))
    r0 = math.hypot(*LV[1 + j * N_SEG + k].xy); r1 = math.hypot(*LV[1 + (j + 1) * N_SEG + k].xy)
    return r0 + (r1 - r0) * t


def mat(name, img=None, nrm=None, rough=0.7, metal=0.0, color=(0.05, 0.04, 0.04, 1), alpha=False, nstr=1.0, emit=None, cull=False):
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
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = nstr
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    if emit:
        bs.inputs["Emission Color"].default_value = emit; bs.inputs["Emission Strength"].default_value = 0.6
    m.use_backface_culling = cull
    if alpha:
        try: m.blend_method = 'CLIP'
        except Exception: pass
        try: m.surface_render_method = 'DITHERED'
        except Exception: pass
        m["gltf_alpha_mode"] = "MASK"
    return m


m_body = mat("M_ArcherDark_Quiver_Body", tex + "/T_ArcherDark_Quiver_Body_BC.png", tex + "/T_ArcherDark_Quiver_Body_N.png", rough=0.72, nstr=1.6, cull=True)
m_in = mat("M_ArcherDark_Quiver_Inside", tex + "/T_ArcherDark_Inside_BC.png", rough=0.95, cull=True)
m_metal = mat("M_ArcherDark_Metal", tex + "/T_ArcherDark_Emblem_BC.png", tex + "/T_ArcherDark_Emblem_N.png", rough=0.42, metal=0.65, nstr=1.4)
m_arr = mat("M_ArcherDark_Arrows", tex + "/T_ArcherDark_Arrows_BC.png", rough=0.6, alpha=True)
m_tip = mat("M_ArcherDark_ArrowTip", rough=0.2, metal=0.85, color=(0.93, 0.20, 0.42, 1), emit=(1.0, 0.18, 0.42, 1))
m_strap = mat("M_ArcherDark_Strap", tex + "/T_ArcherDark_Strap_BC.png", tex + "/T_ArcherDark_Strap_N.png", rough=0.7, nstr=1.3)
m_emb = mat("M_ArcherDark_Emblem", tex + "/T_ArcherDark_Emblem_BC.png", tex + "/T_ArcherDark_Emblem_N.png", rough=0.4, metal=0.65, nstr=1.4)

UV_PLATE = (0.25, 0.75); UV_STAR = (0.75, 0.75); UV_GEM = (0.5, 0.375); UV_COLLAR = (0.25, 0.125); UV_DARK = (0.75, 0.125)
UV_LEATHER = (0.25, 0.5); UV_MET_S = (0.75, 0.5)


class B:
    def __init__(s): s.v = []; s.f = []; s.uv = []; s.fm = []; s.fuv = []
    def vert(s, p, uv=(0.5, 0.5)): s.v.append(tuple(p)); s.uv.append(tuple(uv)); return len(s.v) - 1
    def tri(s, a, b, c, m=0, uv=None): s.f.append((a, b, c)); s.fm.append(m); s.fuv.append(uv)
    def quad(s, a, b, c, d, m=0, uv=None): s.f.append((a, b, c, d)); s.fm.append(m); s.fuv.append(uv)
    def face(s, vs, m=0, uv=None): s.f.append(tuple(vs)); s.fm.append(m); s.fuv.append(uv)


def bevbox(b, c, ax, ay, az, hx, hy, hz, bev, uv, m=0):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
    for v in bm.verts: v.co = Vector((v.co.x * hx, v.co.y * hy, v.co.z * hz))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bev, segments=1, affect='EDGES')
    bm.verts.ensure_lookup_table(); idx = {}
    for v in bm.verts: idx[v.index] = b.vert(c + ax * v.co.x + ay * v.co.y + az * v.co.z, uv)
    flip = (ax.cross(ay)).dot(az) < 0
    for f in bm.faces:
        vs = [idx[v.index] for v in f.verts]
        b.face(vs[::-1] if flip else vs, m, uv)
    bm.free()


def frame_rect(b, c, ax, ay, az, hx, hy, ht, bar, bev, uv, m=0):
    loops = [(hx, hy, -ht), (hx, hy, ht - bev), (hx - bev, hy - bev, ht), (hx - bar + bev, hy - bar + bev, ht),
             (hx - bar, hy - bar, ht - bev), (hx - bar, hy - bar, -ht)]
    rings = []
    for (X, Y, Z) in loops:
        rings.append([b.vert(c + ax * sx * X + ay * sy * Y + az * Z, uv) for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    flip = (ax.cross(ay)).dot(az) < 0
    for i in range(len(rings) - 1):
        for j in range(4):
            q = (rings[i][j], rings[i][(j + 1) % 4], rings[i + 1][(j + 1) % 4], rings[i + 1][j])
            b.face(q[::-1] if not flip else q, m, uv)
    for j in range(4):
        q = (rings[0][j], rings[0][(j + 1) % 4], rings[5][(j + 1) % 4], rings[5][j])
        b.face(q if not flip else q[::-1], m, uv)


def dome(b, c, nrm, rad, h, uv, n=5, m=0):
    """rebite: piramide baixa de n lados com topo achatado em ponto (n tris)."""
    ref = Vector((0, 0, 1)) if abs(nrm.z) < 0.9 else Vector((1, 0, 0))
    e1 = nrm.cross(ref).normalized(); e2 = nrm.cross(e1).normalized()
    ring = [b.vert(c + (e1 * math.cos(2 * math.pi * k / n) + e2 * math.sin(2 * math.pi * k / n)) * rad, uv) for k in range(n)]
    top = b.vert(c + nrm * h, uv)
    for k in range(n): b.tri(ring[k], ring[(k + 1) % n], top, m, uv)


def finish(name, b, mats, angle=35):
    me = bpy.data.meshes.new(name); me.from_pydata(b.v, [], b.f); me.update()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        poly.material_index = b.fm[poly.index]; poly.use_smooth = True
        fu = b.fuv[poly.index]
        for li in poly.loop_indices: uv.data[li].uv = fu if fu is not None else b.uv[me.loops[li].vertex_index]
    for m in mats: me.materials.append(m)
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
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


# ============================ CORPO: torno + cinta da boca + cinta inferior (um mesh, 3 materiais) ============================
bd = B()
Z_LIP = 0.0800
col = [  # (r, z, uv do trecho ate o proximo anel)
    (0.0432, Z_LIP, UV_COLLAR), (0.0463, 0.0825, UV_COLLAR), (0.0468, 0.1060, UV_DARK), (0.0451, 0.1085, UV_DARK),
    (0.0451, 0.1125, UV_COLLAR), (0.0473, 0.1150, UV_COLLAR), (0.0475, 0.1700, UV_STAR), (0.0486, 0.1730, UV_STAR),
    (0.0488, 0.1812, UV_COLLAR), (0.0478, 0.1850, UV_STAR), (0.0420, 0.1858, UV_STAR), (0.0392, 0.1840, None)]
inner = [(0.0378, 0.1790), (0.0376, 0.1500), (0.0366, 0.1200), (0.0330, 0.1050), (0.0200, 0.0975), (0.0, 0.0955)]
rings = []
for (r, z, uvc) in col:
    rings.append([bd.vert((r * math.cos(2 * math.pi * j / SEGS), r * math.sin(2 * math.pi * j / SEGS), z)) for j in range(SEGS)])
for i in range(len(col) - 1):
    uvc = col[i][2]
    for j in range(SEGS):
        j2 = (j + 1) % SEGS
        if uvc is None: break
        bd.quad(rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j], 2, uvc)
prev = rings[-1]; nin = len(inner)
for n_, (r, z) in enumerate(inner):
    vv = 1.0 - 0.98 * n_ / (nin - 1)
    if r == 0.0:
        cen = bd.vert((0, 0, z), (0.5, 0.02))
        for j in range(SEGS): bd.tri(prev[j], prev[(j + 1) % SEGS], cen, 1)
    else:
        rg = [bd.vert((r * math.cos(2 * math.pi * j / SEGS), r * math.sin(2 * math.pi * j / SEGS), z), (0.5, vv)) for j in range(SEGS)]
        for j in range(SEGS):
            j2 = (j + 1) % SEGS; bd.quad(prev[j], prev[j2], rg[j2], rg[j], 1)
        prev = rg
# fecha o fundo da cinta (disco no labio): casco fechado
cl = bd.vert((0, 0, Z_LIP), UV_COLLAR)
for j in range(SEGS): bd.tri(rings[0][(j + 1) % SEGS], rings[0][j], cl, 2, UV_COLLAR)
# rebites da cinta (anel de 12 na faixa grande)
for k in range(12):
    a = (k + 0.5) / 12 * 2 * math.pi
    dome(bd, Vector((0.0475 * math.cos(a), 0.0475 * math.sin(a), 0.1425)), Vector((math.cos(a), math.sin(a), 0)), 0.0026, 0.0024, UV_STAR, 5, 2)
for k in range(12):
    a = k / 12 * 2 * math.pi
    dome(bd, Vector((0.0468 * math.cos(a), 0.0468 * math.sin(a), 0.0945)), Vector((math.cos(a), math.sin(a), 0)), 0.0022, 0.0020, UV_STAR, 5, 2)

# cinta inferior: anel fechado sobre o corpo (z da cinta pintada na textura)
ZB0, ZB1 = -0.2135, -0.1850
bprof = [(-0.0012, ZB0), (0.0014, ZB0 + 0.0012), (0.0030, ZB0 + 0.0040), (0.0034, ZB0 + 0.0070), (0.0034, ZB1 - 0.0070), (0.0030, ZB1 - 0.0040),
         (0.0014, ZB1 - 0.0012), (-0.0012, ZB1)]
bring = []
for (d, z) in bprof:
    row = []
    for j in range(N_SEG):
        a = math.pi / 2 + 2 * math.pi * j / N_SEG; rr = lathe_r(z, a) + d
        row.append(bd.vert((rr * math.cos(a), rr * math.sin(a), z)))
    bring.append(row)
for i in range(len(bprof) - 1):
    uvc = UV_COLLAR if i not in (2, 4) else UV_STAR
    for j in range(N_SEG):
        j2 = (j + 1) % N_SEG
        bd.quad(bring[i][j], bring[i][j2], bring[i + 1][j2], bring[i + 1][j], 2, uvc)
# fecha o anel por dentro (parede interna)
for j in range(N_SEG):
    j2 = (j + 1) % N_SEG
    bd.quad(bring[-1][j], bring[-1][j2], bring[0][j2], bring[0][j], 2, UV_DARK)
for k in range(10):
    a = (k + 0.5) / 10 * 2 * math.pi + math.pi / 2; zc = (ZB0 + ZB1) / 2; rr = lathe_r(zc, a) + 0.0034
    dome(bd, Vector((rr * math.cos(a), rr * math.sin(a), zc)), Vector((math.cos(a), math.sin(a), 0)), 0.0026, 0.0022, UV_STAR, 5, 2)

# junta ao corpo (torno) numa so malha
bm = bmesh.new(); bm.from_mesh(body.data)
uvl = bm.loops.layers.uv.active
nv = [bm.verts.new(p) for p in bd.v]
vmap = {}
for i, v in enumerate(nv): vmap[v] = bd.uv[i]
for f, m, fu in zip(bd.f, bd.fm, bd.fuv):
    face = bm.faces.new([nv[i2] for i2 in f]); face.material_index = m; face.smooth = True
    for lp in face.loops: lp[uvl].uv = fu if fu is not None else vmap[lp.vert]
bm.to_mesh(body.data); bm.free()
for i, m in enumerate((m_body, m_in, m_metal)):
    if i < len(body.data.materials): body.data.materials[i] = m
    else: body.data.materials.append(m)
for p in body.data.polygons: p.use_smooth = True
for ca in list(body.data.color_attributes): body.data.color_attributes.remove(ca)
body.name = body.data.name = "SM_ArcherDark_Quiver_Body"
S_TOP = 0.1858


# ============================ FLECHAS ============================
ba = B()
FW = (0.0, 0.25, 0.5, 0.75)
def fuv(var, x, q): return (FW[var] + 0.25 * (0.5 + x * 0.5), 0.5 + 0.5 * q)


def feather_card(b, base, ax, rad, nrm, length, halfw, var, cup, bend, cols=3, rows=5):
    ring = []
    for r in range(rows + 1):
        q = r / rows; row = []
        for c in range(cols):
            x = -1 + 2 * c / (cols - 1)
            p = base + ax * (length * q) + rad * (halfw * x) + nrm * (cup * x * x * (1 - 0.5 * q) + bend * q * q)
            row.append(b.vert(p, fuv(var, x, q)))
        ring.append(row)
    for r in range(rows):
        for c in range(cols - 1): b.quad(ring[r][c], ring[r][c + 1], ring[r + 1][c + 1], ring[r + 1][c])


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
    r = 0.0031; r0 = []; r1 = []
    for j in range(5):
        a = j / 5 * 2 * math.pi; off = e1 * math.cos(a) * r + e2 * math.sin(a) * r
        r0.append(ba.vert(base + off, (0.12 + 0.01 * j, 0.25))); r1.append(ba.vert(top + off, (0.12 + 0.01 * j, 0.25)))
    for j in range(5): ba.quad(r0[j], r0[(j + 1) % 5], r1[(j + 1) % 5], r1[j])
    # ponta: losango com facetas e mais bisel (material metalico rosa)
    prof_h = [(top - ax * 0.002, 0.0046, 0.0046), (top + ax * 0.0035, 0.0118, 0.0052), (top + ax * 0.0100, 0.0124, 0.0056),
              (top + ax * 0.0185, 0.0062, 0.0030)]
    hr = []
    for (pc, wa, wb) in prof_h:
        hr.append([ba.vert(pc + e1 * wa), ba.vert(pc + e2 * wb), ba.vert(pc - e1 * wa), ba.vert(pc - e2 * wb)])
    apex = ba.vert(top + ax * 0.0385)
    for j in range(4):
        j2 = (j + 1) % 4
        for i in range(len(hr) - 1): ba.quad(hr[i][j], hr[i][j2], hr[i + 1][j2], hr[i + 1][j], 1)
        ba.tri(hr[-1][j], hr[-1][j2], apex, 1)
    var = (k % 3)
    lscale = 0.9 + 0.2 * random.random(); wscale = 0.85 + 0.3 * random.random()
    s_lo = top - ax * (0.083 * lscale); length = 0.072 * lscale
    for ci in range(3):
        a = ci / 3 * 2 * math.pi + random.uniform(-0.2, 0.2) + 0.4 * k
        rad = e1 * math.cos(a) + e2 * math.sin(a); nrm = ax.cross(rad).normalized()
        feather_card(ba, s_lo, ax, rad, nrm, length, 0.0125 * wscale * (0.9 + 0.2 * random.random()), (var + ci) % 3,
                     cup=0.0045 * random.choice((-1, 1)), bend=0.0045 * random.choice((-1, 1)) + 0.002)
arrows = finish("SM_ArcherDark_Quiver_Arrows", ba, [m_arr, m_tip], angle=50)
for p in arrows.data.polygons:        # hastes opacas: remove cor de pena do atlas nas hastes (material 0 usa a regiao da haste)
    pass


# ============================ ALCA LARGA (curva 3D com bevel) ============================
bs = B()
HW = 0.0178; HT = 0.0032; CH = 0.0013
Z_TOPA = 0.1425; Z_LOWA = -0.0760
r_low = lathe_r(Z_LOWA, math.pi) + 0.0
X_TA = -(0.0475 + 0.0030)                  # ponto de saida da cinta superior (centro da argola)
X_LA = -(r_low + 0.0036)
key = [(X_TA, Z_TOPA), (-0.0700, Z_TOPA - 0.001), (-0.0975, 0.1180), (-0.1130, 0.0780), (-0.1175, 0.0300), (-0.1115, -0.0180),
       (-0.0960, -0.0520), (-0.0760, -0.0720), (X_LA, Z_LOWA)]
YA = -0.008


def catmull(pts, n):
    out = []; P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        for s in range(n):
            t = s / n; p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t ** 3) for k in range(2)))
    out.append(pts[-1]); return out


cp = catmull(key, 5)
acc = [0.0]
for i in range(1, len(cp)): acc.append(acc[-1] + math.hypot(cp[i][0] - cp[i - 1][0], cp[i][1] - cp[i - 1][1]))
TOTAL = acc[-1]; NS = 26; pts = []
for i in range(NS + 1):
    s = TOTAL * i / NS; j = max(1, next((q for q in range(1, len(acc)) if acc[q] >= s), len(acc) - 1))
    t = (s - acc[j - 1]) / max(1e-9, acc[j] - acc[j - 1]); x = cp[j - 1][0] + (cp[j][0] - cp[j - 1][0]) * t; z = cp[j - 1][1] + (cp[j][1] - cp[j - 1][1]) * t
    pts.append(Vector((x, YA, z)))
frames = []
for i, p in enumerate(pts):
    tg = (pts[min(i + 1, NS)] - pts[max(i - 1, 0)]).normalized()
    Wy = Vector((0, 1, 0)); Wy = (Wy - tg * Wy.dot(tg)).normalized()
    Nn = tg.cross(Wy).normalized()
    if i == NS // 2 and Nn.x > 0: SGN = -1
    frames.append([tg, Wy, Nn])
SGN = -1 if frames[NS // 2][2].x > 0 else 1
for i, (tg, Wy, Nn) in enumerate(frames):
    Wy = Wy * SGN; Nn = Nn * SGN                       # N aponta para fora do laco
    al = math.radians(48) * max(0.0, math.sin(math.pi * i / NS)) ** 1.2    # torcao suave: mostra a face larga de frente e de lado
    W = Wy * math.cos(al) + Nn * math.sin(al); N = Nn * math.cos(al) - Wy * math.sin(al)
    frames[i] = (tg, W, N)
LEN_TEX = 0.20
cols = []
for i, p in enumerate(pts):
    tg, W, N = frames[i]; v = (TOTAL * i / NS) / LEN_TEX
    ring = [(-HW + CH, HT, 0.05), (HW - CH, HT, 0.45), (HW, 0.0, 0.49), (HW - CH, -HT, 0.45), (-HW + CH, -HT, 0.05), (-HW, 0.0, 0.01)]
    cols.append([bs.vert(p + W * a + N * b_, (u, v)) for (a, b_, u) in ring])
for i in range(NS):
    for j in range(6):
        j2 = (j + 1) % 6; bs.quad(cols[i][j], cols[i][j2], cols[i + 1][j2], cols[i + 1][j])
for ringv, flip in ((cols[0], True), (cols[NS], False)):
    for j in range(1, 5):
        bs.tri(ringv[0], ringv[j + 1], ringv[j]) if not flip else bs.tri(ringv[0], ringv[j], ringv[j + 1])


def at(t):
    i = max(0, min(NS, int(round(t * NS)))); return pts[i], frames[i]


# ancoragens: placa na cinta + argola retangular (a fita passa por dentro) + rebites
def anchor(zc, x_surf, outward):
    """x_surf: raio da superficie; outward = -1 (esquerda). Placa curva achatada + argola vazada."""
    c = Vector((outward * (x_surf + 0.0022), YA, zc))
    ax_t = Vector((0, 1, 0)); ax_z = Vector((0, 0, 1)); ax_r = Vector((outward, 0, 0))
    bevbox(bs, c, ax_t, ax_z, ax_r, 0.0215, 0.0155, 0.0022, 0.0009, UV_MET_S, 0)
    for sx in (-1, 1):
        for sz in (-1, 1):
            dome(bs, c + ax_t * 0.0155 * sx + ax_z * 0.0095 * sz + ax_r * 0.0022, ax_r, 0.0026, 0.0020, UV_MET_S, 5)
    cf = c + ax_r * 0.0054
    frame_rect(bs, cf, ax_t, ax_z, ax_r, 0.0215, 0.0085, 0.0018, 0.0032, 0.0008, UV_MET_S, 0)


anchor(Z_TOPA, 0.0475, -1)
anchor(Z_LOWA, r_low, -1)
# fivela no meio da fita: moldura com furo, lingueta, passador de couro e ponta
for t, tail in ((0.50, True),):
    p, (tg, W, N) = at(t)
    c = p + N * (HT + 0.0018)
    frame_rect(bs, c, tg, W, N, 0.0105, HW + 0.0050, 0.0018, 0.0036, 0.0008, UV_MET_S)
    bevbox(bs, c + N * 0.0008, tg, W, N, 0.0013, HW + 0.0010, 0.0016, 0.0005, UV_MET_S)
    pk, (tk, Wk, Nk) = at(t + 0.08)
    frame_rect(bs, pk + Nk * (HT + 0.0014), tk, Wk, Nk, 0.0042, HW + 0.0016, 0.0013, 0.0017, 0.0005, UV_LEATHER)
    for sy in (-1, 1): dome(bs, pk + Nk * (HT + 0.0026) + Wk * (HW - 0.0004) * sy, Nk, 0.0016, 0.0013, UV_MET_S, 5)
    pt, (tt_, Wt, Nt) = at(t - 0.05)
    Lt = 0.020
    shape = [(0.0, -HW + 0.002), (Lt * 0.62, -HW + 0.002), (Lt, 0.0), (Lt * 0.62, HW - 0.002), (0.0, HW - 0.002)]
    base_c = c - tg * 0.020 + N * 0.0021
    top_v = [bs.vert(base_c + tg * x + W * y + N * 0.0017, (0.25 + 0.2 * (y / HW), 0.3 + 0.02 * x)) for (x, y) in shape]
    bot_v = [bs.vert(base_c + tg * x + W * y - N * 0.0017, (0.25 + 0.2 * (y / HW), 0.3 + 0.02 * x)) for (x, y) in shape]
    bs.face(top_v); bs.face(bot_v[::-1])
    for j in range(5): bs.quad(top_v[(j + 1) % 5], top_v[j], bot_v[j], bot_v[(j + 1) % 5])
for t in (0.22, 0.80):
    p, (tg, W, N) = at(t)
    for sy in (-1, 1): dome(bs, p + N * HT + W * (HW - 0.0050) * sy, N, 0.0020, 0.0015, UV_MET_S, 5)
strap = finish("SM_ArcherDark_Quiver_Strap", bs, [m_strap], angle=40)


# ============================ EMBLEMA em camadas ============================
be = B()
VC = 0.066


def wrap(u, v, h):
    ph = u / R_TUBE; r = R_TUBE + h
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
    ctr = b.vert(wrap(0, 0, center_h), uv)
    rg = []
    for rho in rhos:
        rg.append([b.vert(wrap(x * rho, y * rho, hfun(rho, inner)), uv) for (x, y, inner) in outl])
    n = len(outl)
    for j in range(n): b.tri(ctr, rg[0][(j + 1) % n], rg[0][j], m, uv)
    for r in range(len(rhos) - 1):
        for j in range(n): b.quad(rg[r][j], rg[r][(j + 1) % n], rg[r + 1][(j + 1) % n], rg[r + 1][j], m, uv)
    if wall_h is not None:
        wl = [b.vert(wrap(x * rhos[-1], y * rhos[-1], wall_h), uv) for (x, y, inner) in outl]
        for j in range(n): b.quad(rg[-1][j], wl[j], wl[(j + 1) % n], rg[-1][(j + 1) % n], m, uv)


PL_H = 0.0030
layered(be, star_outline((0.036, 0.056), 0.0185), [0.5, 0.92, 1.0], lambda r, i: PL_H - 0.0006 * (r > 0.95), UV_PLATE, wall_h=-0.0015, center_h=PL_H)
layered(be, star_outline((0.0305, 0.047), 0.0152), [0.7, 1.0], lambda r, i: PL_H + 0.0010 - 0.0004 * (r > 0.95), UV_STAR, wall_h=PL_H - 0.0003, center_h=PL_H + 0.0018)
layered(be, star_outline((0.0255, 0.0415), 0.0085), [0.4, 1.0], lambda r, i: PL_H + 0.0026 + (0.0030 if not i else 0.0014) * (1 - r) ** 0.9, UV_STAR, wall_h=PL_H + 0.0014, center_h=PL_H + 0.0100)
gz = PL_H + 0.0103; gn = 6
gring = [be.vert(wrap(0.0052 * math.cos(2 * math.pi * k / gn), 0.0090 * math.sin(2 * math.pi * k / gn), gz), UV_GEM) for k in range(gn)]
gring2 = [be.vert(wrap(0.0032 * math.cos(2 * math.pi * k / gn), 0.0054 * math.sin(2 * math.pi * k / gn), gz + 0.0026), UV_GEM) for k in range(gn)]
gtop = be.vert(wrap(0, 0, gz + 0.0044), UV_GEM)
for k in range(gn):
    k2 = (k + 1) % gn
    be.quad(gring[k], gring[k2], gring2[k2], gring2[k], 0, UV_GEM); be.tri(gring2[k], gring2[k2], gtop, 0, UV_GEM)
for k in range(4):
    a = k * math.pi / 2; L = (0.036, 0.056)[k % 2] * 0.84
    cpos = wrap(L * math.cos(a), L * math.sin(a), PL_H - 0.0004)
    dome(be, cpos, Vector((cpos.x, cpos.y, 0)).normalized(), 0.0022, 0.0022, UV_STAR, 5)
ring_c = wrap(0, -0.0600, 0.0012)
rn = Vector((ring_c.x, ring_c.y, 0)).normalized()


def torus(b, c, a1, a2, R, r, n1, n2, uv):
    vs = []
    for i in range(n1):
        t = 2 * math.pi * i / n1; cc = c + (a1 * math.cos(t) + a2 * math.sin(t)) * R; rad = (a1 * math.cos(t) + a2 * math.sin(t))
        nrm = a1.cross(a2)
        vs.append([b.vert(cc + (rad * math.cos(2 * math.pi * j / n2) + nrm * math.sin(2 * math.pi * j / n2)) * r, uv) for j in range(n2)])
    for i in range(n1):
        i2 = (i + 1) % n1
        for j in range(n2):
            j2 = (j + 1) % n2; b.quad(vs[i][j], vs[i][j2], vs[i2][j2], vs[i2][j], 0, uv)


torus(be, ring_c + rn * 0.0016, Vector((1, 0, 0)), Vector((0, 0, 1)), 0.0034, 0.0010, 8, 4, UV_DARK)
emblem = finish("SM_ArcherDark_Quiver_Emblem", be, [m_emb], angle=30)
orient_out(emblem, lambda c: Vector((0, 0, c.z)))


# ============================ PINGENTE com penas brancas ============================
bp = B()
pc = wrap(0, -0.0780, 0.0042)
pn = Vector((pc.x, pc.y, 0)).normalized(); pt_ = Vector((1, 0, 0)); pz = Vector((0, 0, 1))
torus(bp, wrap(0, -0.0665, 0.0030), pt_, pz, 0.0022, 0.0007, 6, 4, UV_DARK)
HWd, HHd = 0.0058, 0.0125
def dp(x, y, h): return pc + pt_ * x + pz * y + pn * h
pa = [bp.vert(dp(0, HHd, 0), UV_STAR), bp.vert(dp(HWd, 0, 0), UV_STAR), bp.vert(dp(0, -HHd, 0), UV_STAR), bp.vert(dp(-HWd, 0, 0), UV_STAR)]
pb = [bp.vert(dp(0, HHd * 0.58, 0.0020), UV_PLATE), bp.vert(dp(HWd * 0.58, 0, 0.0020), UV_PLATE), bp.vert(dp(0, -HHd * 0.58, 0.0020), UV_PLATE), bp.vert(dp(-HWd * 0.58, 0, 0.0020), UV_PLATE)]
pc2 = [bp.vert(dp(0, HHd * 0.58, -0.0020), UV_PLATE), bp.vert(dp(HWd * 0.58, 0, -0.0020), UV_PLATE), bp.vert(dp(0, -HHd * 0.58, -0.0020), UV_PLATE), bp.vert(dp(-HWd * 0.58, 0, -0.0020), UV_PLATE)]
cf = bp.vert(dp(0, 0, 0.0032), UV_GEM); cb = bp.vert(dp(0, 0, -0.0032), UV_PLATE)
for j in range(4):
    j2 = (j + 1) % 4
    bp.quad(pa[j], pa[j2], pb[j2], pb[j], 0, UV_STAR); bp.tri(pb[j], pb[j2], cf, 0, UV_GEM)
    bp.quad(pa[j2], pa[j], pc2[j], pc2[j2], 0, UV_STAR); bp.tri(pc2[j2], pc2[j], cb, 0, UV_PLATE)
n_metal = len(bp.f)
sp = dp(0, HHd * 0.2, -0.0002)      # penas brancas penduradas ao lado do losango (3 a 5 cartoes curvos)
fan = [(-0.0105, 0.060, 0.22, 0.003), (-0.0035, 0.078, 0.07, -0.002), (0.0045, 0.068, -0.10, 0.003), (0.0120, 0.050, -0.24, -0.002), (0.0020, 0.042, 0.02, 0.004)]
for (xo, ln, sw, bend) in fan:
    ax = (pz * -1 * math.cos(sw) + pt_ * math.sin(sw)).normalized(); rad = ax.cross(pn).normalized()
    feather_card(bp, dp(xo, -HHd * 0.55, 0.0016 + 0.0006 * abs(sw)), ax, rad, pn, ln, 0.0066, 3, cup=0.0016, bend=bend, cols=3, rows=4)
pendant = finish("SM_ArcherDark_Quiver_Pendant", bp, [m_emb, m_arr], angle=30)
for p in pendant.data.polygons:
    p.material_index = 0 if p.index < n_metal else 1


# ============================ mundo e hierarquia ============================
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
