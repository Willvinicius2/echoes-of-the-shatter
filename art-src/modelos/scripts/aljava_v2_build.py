"""Aljava do arqueiro dark v2 (Blender -b): corpo TripoSG recortado + flechas, alca e emblema em geometria propria.
uso: blender -b -P aljava_v2_build.py -- <glb_atual> <tex_dir> <out_glb> <out_blend>"""
import bpy, bmesh, sys, math, random
from mathutils import Vector, Matrix
glb_in, tex, out_glb, out_blend = sys.argv[sys.argv.index("--") + 1:][:4]
random.seed(11)
THETA = math.radians(9.9)
ORG = Vector((0, 0, -0.1))
M = Matrix.Translation(ORG) @ Matrix.Rotation(THETA, 4, 'Y')   # local(eixo) -> mundo
Mi = M.inverted()
S_TOP = 0.178          # topo da cinta (s no eixo)
R_TUBE = 0.042

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_in)
body = [o for o in bpy.data.objects if o.type == 'MESH'][0]


# ---------- materiais ----------
def mat(name, img=None, nrm=None, rough=0.7, metal=0.0, color=(0.05, 0.04, 0.04, 1), alpha_clip=False, double=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bs = nt.nodes["Principled BSDF"]
    bs.inputs["Roughness"].default_value = rough; bs.inputs["Metallic"].default_value = metal
    bs.inputs["Base Color"].default_value = color
    if img:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(img)
        t.image.colorspace_settings.name = 'sRGB'
        nt.links.new(t.outputs["Color"], bs.inputs["Base Color"])
        if alpha_clip: nt.links.new(t.outputs["Alpha"], bs.inputs["Alpha"])
    if nrm:
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(nrm); tn.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 1.0
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    if alpha_clip:
        try: m.blend_method = 'CLIP'
        except Exception: pass
        try: m.surface_render_method = 'DITHERED'
        except Exception: pass
        m["gltf_alpha_mode"] = "MASK"
    m.use_backface_culling = not double
    return m


m_body = mat("M_ArcherDark_Quiver_Body", tex + "/T_ArcherDark_Quiver_Body_BC.png", tex + "/T_ArcherDark_Quiver_Body_N.png", rough=0.72)
m_in = mat("M_ArcherDark_Quiver_Inside", color=(0.025, 0.02, 0.02, 1), rough=0.95)
m_arr = mat("M_ArcherDark_Arrows", tex + "/T_ArcherDark_Arrows_BC.png", rough=0.6, alpha_clip=True, double=True)
m_strap = mat("M_ArcherDark_Strap", tex + "/T_ArcherDark_Strap_BC.png", rough=0.7)
m_emb = mat("M_ArcherDark_Emblem", tex + "/T_ArcherDark_Emblem_BC.png", rough=0.4, metal=0.5)

# ---------- corpo: recorte ----------
bm = bmesh.new(); bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)   # costuras de UV do glTF dividem vertices
for v in bm.verts: v.co = Mi @ v.co            # corpo no referencial do eixo
# zona do emblema borrado (frente, -y): achata o relevo na superficie do tubo e guarda a mascara de UV para repintar
import json
def in_zone(c): return c.y < 0.01 and 0.012 < c.z < 0.122 and abs(c.x) < 0.047
uvl = bm.loops.layers.uv.active; mask_polys = []
for f in bm.faces:
    if in_zone(f.calc_center_median()):
        mask_polys.append([[l[uvl].uv.x, l[uvl].uv.y] for l in f.loops])
json.dump(mask_polys, open(tex + "/emblem_mask.json", "w"))
for v in bm.verts:
    if v.co.y < 0.012 and 0.012 < v.co.z < 0.122 and abs(v.co.x) < 0.047:
        w = min(1.0, (0.047 - abs(v.co.x)) / 0.012, (v.co.z - 0.012) / 0.012, (0.122 - v.co.z) / 0.008)
        r = math.hypot(v.co.x, v.co.y)
        if r > 0.0415 and r > 1e-6:
            k = 0.0415 / r; k = 1 + (k - 1) * w
            v.co.x *= k; v.co.y *= k
dele = []
for f in bm.faces:
    c = f.calc_center_median()
    if c.z > S_TOP or c.x < -0.05 or (c.x < -0.043 and c.z < 0.135) or (c.x > 0.044 and c.z < 0.125):
        dele.append(f)
bmesh.ops.delete(bm, geom=dele, context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.faces.ensure_lookup_table()
seen = set(); islands = []
for f in bm.faces:
    if f in seen: continue
    st = [f]; seen.add(f); isl = []
    while st:
        x = st.pop(); isl.append(x)
        for e in x.edges:
            for g in e.link_faces:
                if g not in seen: seen.add(g); st.append(g)
    islands.append(isl)
islands.sort(key=len, reverse=True)
bmesh.ops.delete(bm, geom=[f for isl in islands[1:] for f in isl], context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
for v in bm.verts:     # serrilhado deixado pelo corte da alca (lado esquerdo): alisa no raio do tubo
    if v.co.x < -0.03 and 0.0 < v.co.z < 0.135:
        r = math.hypot(v.co.x, v.co.y)
        if r > 0.0415:
            k = 0.0415 / r; v.co.x *= k; v.co.y *= k
bset = set(e for e in bm.edges if e.is_boundary); loops = []
while bset:
    e0 = bset.pop(); comp = [e0]; st = [e0]
    while st:
        x = st.pop()
        for v in x.verts:
            for e in v.link_edges:
                if e in bset: bset.remove(e); comp.append(e); st.append(e)
    loops.append(comp)
top_edges = []
for comp in loops:
    zs = [v.co.z for e in comp for v in e.verts]
    if sum(zs) / len(zs) > 0.15 and len(comp) > len(top_edges): top_edges = comp
    else:
        for ff in bmesh.ops.holes_fill(bm, edges=comp, sides=len(comp) + 2)['faces']: ff.material_index = 1
for v in {v for e in top_edges for v in e.verts}: v.co.z = S_TOP
res = bmesh.ops.holes_fill(bm, edges=top_edges, sides=len(top_edges) + 2)
cap = res["faces"]
bmesh.ops.inset_region(bm, faces=cap, thickness=0.008, depth=0.0)
ext = bmesh.ops.extrude_face_region(bm, geom=list(cap))
ev = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
bmesh.ops.translate(bm, verts=ev, vec=(0, 0, -0.05))
for g in ext["geom"]:
    if isinstance(g, bmesh.types.BMFace): g.material_index = 1
for f in cap: f.material_index = 1
# faces do interior: o miolo da tampa ficou em `cap` (inset reaproveita a face), extrusao = fundo
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.normal_update()
bm.to_mesh(body.data); bm.free()
body.data.materials.clear(); body.data.materials.append(m_body); body.data.materials.append(m_in)
for p in body.data.polygons: p.use_smooth = True
body.name = body.data.name = "SM_ArcherDark_Quiver_Body"


# ---------- helper de malha ----------
def mk(name, verts, faces, uvs, material, smooth=False):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces]); me.update()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices: uv.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(material)
    for p in me.polygons: p.use_smooth = smooth
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o


class B:
    def __init__(s): s.v = []; s.f = []; s.uv = []
    def vert(s, p, uv): s.v.append(tuple(p)); s.uv.append(uv); return len(s.v) - 1
    def tri(s, a, b, c): s.f.append((a, b, c))
    def quad(s, a, b, c, d): s.f.append((a, b, c, d))
    def build(s, name, material, smooth=False): return mk(name, s.v, s.f, s.uv, material, smooth)


def box(b, c, ax, ay, az, hx, hy, hz, uv):
    pts = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                pts[(sx, sy, sz)] = b.vert(c + ax * hx * sx + ay * hy * sy + az * hz * sz, uv)
    flip = (ax.cross(ay)).dot(az) > 0
    for q in (((-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1)), ((1, -1, -1), (1, -1, 1), (1, 1, 1), (1, 1, -1)),
              ((-1, -1, -1), (-1, -1, 1), (1, -1, 1), (1, -1, -1)), ((-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1)),
              ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1)), ((-1, -1, 1), (-1, 1, 1), (1, 1, 1), (1, -1, 1))):
        qq = [pts[k] for k in q]
        b.quad(*(qq[::-1] if flip else qq))


# ---------- flechas ----------
ba = B()
disk = [(0, 0), (0.0235, 0.004), (-0.0235, -0.004), (0.004, 0.0235), (-0.004, -0.0235),
        (0.0165, 0.0165), (-0.0165, -0.0165), (0.0165, -0.0165), (-0.0165, 0.0165)]
heights = [0.19, 0.225, 0.175, 0.205, 0.185, 0.235, 0.17, 0.215, 0.195]
for k, (px, py) in enumerate(disk):
    rr = math.hypot(px, py); tilt = 0.05 + rr * 4.0
    ang = math.atan2(py, px) if rr > 1e-6 else 1.0
    d = Vector((math.cos(ang) * math.sin(tilt), math.sin(ang) * math.sin(tilt), 0)); d.z = math.sqrt(max(0, 1 - d.x ** 2 - d.y ** 2))
    base = Vector((px, py, 0.13)); L = heights[k]
    ax = d.normalized(); ref = Vector((0, 1, 0)) if abs(ax.y) < 0.9 else Vector((1, 0, 0))
    e1 = ax.cross(ref).normalized(); e2 = ax.cross(e1).normalized()
    roll = random.random() * 2 * math.pi
    e1, e2 = e1 * math.cos(roll) + e2 * math.sin(roll), -e1 * math.sin(roll) + e2 * math.cos(roll)
    top = base + ax * (L + (S_TOP - 0.13))
    r = 0.0032; ring0 = []; ring1 = []
    for j in range(6):
        a = j / 6 * 2 * math.pi; off = e1 * math.cos(a) * r + e2 * math.sin(a) * r
        ring0.append(ba.vert(base + off, (0.52 + 0.02 * j, 0.02))); ring1.append(ba.vert(top + off, (0.52 + 0.02 * j, 0.98)))
    for j in range(6):
        ba.quad(ring0[j], ring0[(j + 1) % 6], ring1[(j + 1) % 6], ring1[j])
    hw = 0.0105; hb = top; ht = top + ax * 0.034; hl = top - ax * 0.004
    side = [ba.vert(hb + e1 * hw, (0.82, 0.5)), ba.vert(hb + e2 * hw * 0.55, (0.9, 0.5)),
            ba.vert(hb - e1 * hw, (0.82, 0.5)), ba.vert(hb - e2 * hw * 0.55, (0.9, 0.5))]
    tt = ba.vert(ht, (0.88, 0.05)); tl = ba.vert(hl, (0.88, 0.95))
    for j in range(4):
        ba.tri(side[j], side[(j + 1) % 4], tt); ba.tri(side[(j + 1) % 4], side[j], tl)
    for j in range(3):
        a = j / 3 * 2 * math.pi + 0.5
        rad = e1 * math.cos(a) + e2 * math.sin(a)
        s_hi = top - ax * 0.010; s_lo = top - ax * 0.074; s_mid = top - ax * 0.040
        w = 0.0235
        p0 = s_hi + rad * r * 0.8; p1 = s_hi + rad * w * 0.8
        q0 = s_mid + rad * r * 0.8; q1 = s_mid + rad * w * 1.02 + rad * 0.0
        z0 = s_lo + rad * r * 0.8; z1 = s_lo + rad * w * 0.95 + rad * 0.003
        va = [ba.vert(p0, (0.25, 0.995)), ba.vert(p1, (0.5, 0.995)), ba.vert(q0, (0.25, 0.5)),
              ba.vert(q1, (0.5, 0.5)), ba.vert(z0, (0.25, 0.005)), ba.vert(z1, (0.5, 0.005))]
        ba.quad(va[0], va[1], va[3], va[2]); ba.quad(va[2], va[3], va[5], va[4])
arrows = ba.build("SM_ArcherDark_Quiver_Arrows", m_arr, smooth=False)

# ---------- alca ----------
bs = B()
NS = 30; W_ST = 0.026; TH = 0.0058


def path(t):
    s = -0.05 + (0.105 + 0.05) * t
    x = -(R_TUBE + 0.002 + 0.07 * math.sin(math.pi * t) ** 0.65)
    return Vector((x, 0, s))


pts = [path(i / NS) for i in range(NS + 1)]
frames = []
for i, p in enumerate(pts):
    tg = (pts[min(i + 1, NS)] - pts[max(i - 1, 0)]).normalized()
    ny = Vector((0, 1, 0)); nn = ny.cross(tg).normalized()
    if nn.x > 0: nn = -nn
    frames.append((tg, ny, nn))
cols = []
hw, ht = W_ST / 2, TH / 2
for i, p in enumerate(pts):
    tg, ny, nn = frames[i]; v = i / NS * 3.0
    wd, td = nn, ny
    c_out = [bs.vert(p - td * ht + wd * hw, (0.46, v)), bs.vert(p - td * ht - wd * hw, (0.04, v))]
    c_s1 = [bs.vert(p - td * ht + wd * hw, (0.005, v)), bs.vert(p + td * ht + wd * hw, (0.015, v))]
    c_in = [bs.vert(p + td * ht + wd * hw, (0.46, v)), bs.vert(p + td * ht - wd * hw, (0.04, v))]
    c_s2 = [bs.vert(p + td * ht - wd * hw, (0.005, v)), bs.vert(p - td * ht - wd * hw, (0.015, v))]
    cols.append((c_out, c_s1, c_in, c_s2))
for i in range(NS):
    a, b = cols[i], cols[i + 1]
    bs.quad(a[0][0], b[0][0], b[0][1], a[0][1])
    bs.quad(a[1][0], b[1][0], b[1][1], a[1][1])
    bs.quad(a[2][1], b[2][1], b[2][0], a[2][0])
    bs.quad(a[3][0], b[3][0], b[3][1], a[3][1])
MU = (0.78, 0.5)


def frame_at(t):
    i = max(0, min(NS, int(round(t * NS)))); return pts[i], frames[i]


for t in (0.34, 0.70):
    p, (tg, ny, nn) = frame_at(t)
    c = p - ny * (TH / 2 + 0.0025)
    fw = W_ST + 0.012; fl = 0.024; bar = 0.0035; hh = 0.0035
    box(bs, c + tg * (fl / 2 - bar / 2), tg, nn, ny, bar / 2, fw / 2, hh, MU)
    box(bs, c - tg * (fl / 2 - bar / 2), tg, nn, ny, bar / 2, fw / 2, hh, MU)
    box(bs, c + nn * (fw / 2 - bar / 2), tg, nn, ny, fl / 2, bar / 2, hh, MU)
    box(bs, c - nn * (fw / 2 - bar / 2), tg, nn, ny, fl / 2, bar / 2, hh, MU)
    box(bs, c - ny * 0.0012 + tg * 0.003, tg, nn, ny, 0.0022, (fw - 0.004) / 2, hh * 0.8, MU)
    pk, (tk, yk, nk) = frame_at(t + 0.09)
    box(bs, pk - yk * (TH / 2 + 0.0012), tk, nk, yk, 0.005, W_ST / 2 + 0.002, 0.0017, (0.2, 0.5))
for t in (0.0, 1.0):
    p, (tg, ny, nn) = frame_at(t)
    c = p + Vector((0.004, 0, 0))
    box(bs, c, Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), 0.0045, 0.02, 0.017, MU)
    for dy in (-0.01, 0.01):
        cc = c + Vector((-0.0035, dy, 0))
        ring = [bs.vert(cc + Vector((0, 0.003 * math.cos(q * math.pi / 2), 0.003 * math.sin(q * math.pi / 2))), MU) for q in range(4)]
        tipv = bs.vert(cc + Vector((-0.002, 0, 0)), MU)
        for q in range(4): bs.tri(ring[q], ring[(q + 1) % 4], tipv)
strap = bs.build("SM_ArcherDark_Quiver_Strap", m_strap, smooth=True)

# ---------- emblema (placa de 4 pontas com bisel, gema rosa) ----------
be = B()
VC = 0.066


def star_pts():
    tipL = (0.034, 0.055); r_in = 0.0135; o = []
    for k in range(4):
        a = k * math.pi / 2; L = tipL[k % 2]
        o.append((L * math.cos(a), L * math.sin(a), 0))
        b = a + math.pi / 4
        o.append((r_in * math.cos(b), r_in * math.sin(b), 1))
    return o


outl = star_pts()
rhos = [0.34, 0.67, 1.0]


def wrap(u, v, h):
    ph = u / R_TUBE; r = R_TUBE + 0.002 + h
    return Vector((r * math.sin(ph), -r * math.cos(ph), VC + v))


def uvp(u, v, rho=1.0): return ((0.05, 0.28, 0.55, 0.92)[int(round(rho * 3)) if rho < 1 else 3] if False else 0.1 + 0.85 * rho, 0.8)


ctr = be.vert(wrap(0, 0, 0.0105), uvp(0, 0, 0.0))
rings = []
for rho in rhos:
    ring = []
    for (x, y, inner) in outl:
        u, v = x * rho, y * rho
        h = (0.0022 + 0.0078 * (1 - rho)) if not inner else (0.0022 + 0.0035 * (1 - rho))
        ring.append(be.vert(wrap(u, v, h), uvp(u, v, rho)))
    rings.append(ring)
n8 = len(outl)
for j in range(n8): be.tri(ctr, rings[0][(j + 1) % n8], rings[0][j])
for r in range(2):
    for j in range(n8):
        be.quad(rings[r][j], rings[r][(j + 1) % n8], rings[r + 1][(j + 1) % n8], rings[r + 1][j])
wall = [be.vert(wrap(x, y, -0.002), (0.12, 0.8)) for (x, y, inner) in outl]
for j in range(n8):
    be.quad(rings[2][j], wall[j], wall[(j + 1) % n8], rings[2][(j + 1) % n8])
g0 = be.vert(wrap(0, 0, 0.0185), (0.5, 0.15))
gr = [be.vert(wrap(0.006 * math.cos(q * math.pi / 2), 0.012 * math.sin(q * math.pi / 2), 0.0125), (0.5, 0.15)) for q in range(4)]
for q in range(4): be.tri(gr[q], gr[(q + 1) % 4], g0)
emblem = be.build("SM_ArcherDark_Quiver_Emblem", m_emb, smooth=False)

# ---------- normais para fora (referencial do eixo) ----------
for o, mode in ((emblem, "axis"), (strap, "none"), (arrows, "none")):
    if mode != "axis": continue
    bm2 = bmesh.new(); bm2.from_mesh(o.data); bm2.normal_update()
    for f in bm2.faces:
        c = f.calc_center_median(); out = Vector((c.x, c.y, 0))
        if f.normal.dot(out) < 0: f.normal_flip()
    bm2.normal_update(); bm2.to_mesh(o.data); bm2.free()
bm2 = bmesh.new(); bm2.from_mesh(strap.data); bm2.faces.ensure_lookup_table(); bm2.normal_update()
for f in list(bm2.faces)[:4 * NS]:
    c = f.calc_center_median(); pn = min(pts, key=lambda q: (q - c).length)
    if f.normal.dot(c - pn) < 0: f.normal_flip()
bm2.normal_update(); bm2.to_mesh(strap.data); bm2.free()

# ---------- mundo e hierarquia ----------
root = bpy.data.objects.new("SM_ArcherDark_Quiver", None); bpy.context.scene.collection.objects.link(root)
objs = [body, arrows, strap, emblem]
for o in objs:
    if o.name not in bpy.context.scene.collection.objects: bpy.context.scene.collection.objects.link(o)
    o.data.transform(M)
    o.parent = root
    o.data.update()
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
bpy.ops.object.select_all(action='DESELECT')
for o in objs + [root]: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                          export_image_format='AUTO', export_materials='EXPORT', export_cameras=False, export_lights=False,
                          export_normals=True, export_texcoords=True)
tr = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs}
print("TRIS", tr, sum(tr.values()))
