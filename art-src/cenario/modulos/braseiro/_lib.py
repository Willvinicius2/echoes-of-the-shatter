"""Biblioteca do braseiro v3: contrato de medidas, texturas pintadas em Python (albedo, normal, emissão), materiais,
formas forjadas (subdivisão + jitter + bevel real por ângulo), lascas por boolean e UV por projeção em caixa."""
import bpy, bmesh, math, os, random
import numpy as np
from mathutils import Vector, Quaternion
from PIL import Image, ImageDraw, ImageFilter

TEX_DIR = os.environ.get("BRASEIRO_TEX", "/tmp/braseiro_tex")
os.makedirs(TEX_DIR, exist_ok=True)
objs = []
partes = {}          # nome da parte -> objetos
UVSCALE = 1.4        # repetições de textura por metro

# ---------------------------------------------------------------- ruído e texturas
def fnoise(n, beta, rg):
    f = np.fft.fftfreq(n); fx, fy = np.meshgrid(f, f)
    r = np.sqrt(fx ** 2 + fy ** 2); r[0, 0] = 1
    sp = np.fft.fft2(rg.standard_normal((n, n))) / (r ** beta); sp[0, 0] = 0
    o = np.real(np.fft.ifft2(sp)); return (o - o.min()) / (o.max() - o.min())

def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def _save(arr, name, srgb=True):
    a = np.clip(arr, 0, 1)
    if srgb: a = a ** (1 / 2.2)
    p = os.path.join(TEX_DIR, name); Image.fromarray((a * 255).astype(np.uint8), "RGB").save(p); return p

def _normal(height, name, k=14.0):
    gy, gx = np.gradient(np.pad(height, 1, mode="wrap")); gx = gx[1:-1, 1:-1]; gy = gy[1:-1, 1:-1]
    nv = np.stack([-gx * k, gy * k, np.ones_like(gx)], -1); nv /= np.linalg.norm(nv, axis=-1, keepdims=True)
    return _save(nv * 0.5 + 0.5, name, srgb=False)

def _discos(n, seed, qtd, rmin, rmax, lo, hi, blur):
    img = Image.new("L", (n, n), 128); d = ImageDraw.Draw(img); r = np.random.default_rng(seed)
    for _ in range(qtd):
        x, y = r.integers(0, n, 2); rx = r.integers(rmin, rmax); ry = int(rx * r.uniform(0.5, 1.2)); v = int(r.integers(lo, hi))
        for dx in (-n, 0, n):
            for dy in (-n, 0, n): d.ellipse((x - rx + dx, y - ry + dy, x + rx + dx, y + ry + dy), fill=v)
    return np.asarray(img.filter(ImageFilter.GaussianBlur(blur)), dtype=np.float32) / 255.0

def _riscos(n, seed, qtd, lmin, lmax):
    img = Image.new("L", (n, n), 0); d = ImageDraw.Draw(img); r = np.random.default_rng(seed)
    for _ in range(qtd):
        x, y = r.integers(0, n, 2); a = r.uniform(0, math.pi); l = r.uniform(lmin, lmax)
        d.line((x, y, x + math.cos(a) * l, y + math.sin(a) * l), fill=int(r.integers(120, 255)), width=int(r.integers(1, 3)))
    return np.asarray(img, dtype=np.float32) / 255.0

def tex_metal(nome, seed, ferrugem=(0.60, 0.74), fuligem=0.0, tom=(0.05, 0.048, 0.055), n=512):
    """Ferro forjado: martelado, riscos de aço exposto, manchas de ferrugem e fuligem opcional."""
    rg = np.random.default_rng(seed)
    base = fnoise(n, 1.6, rg); fino = fnoise(n, 0.9, rg); gr = fnoise(n, 2.2, rg)
    hamm = _discos(n, seed + 1, 520, 7, 26, 105, 150, 2.2); scr = _riscos(n, seed + 2, 90, 14, 80)
    height = 0.55 * hamm + 0.25 * fino + 0.2 * base - 0.35 * scr
    rust = np.clip(smooth(base * 0.65 + fino * 0.35 + (gr - 0.5) * 0.2, *ferrugem) + smooth(fino, 0.6, 0.75) * 0.3, 0, 1)
    ferro = np.stack([tom[0] + 0.05 * gr, tom[1] + 0.045 * gr, tom[2] + 0.05 * gr], -1) * (0.75 + 0.5 * hamm)[..., None]
    r1 = np.array([0.40, 0.17, 0.05]); r2 = np.array([0.20, 0.085, 0.04])
    ferrugem_c = (r2 * (1 - fino[..., None]) + r1 * fino[..., None]) * (0.6 + 0.6 * hamm)[..., None]
    img = ferro * (1 - rust[..., None]) + ferrugem_c * rust[..., None]
    img = img + (np.array([0.42, 0.40, 0.38]) - img) * (scr * (0.6 + 0.4 * (1 - rust)))[..., None] * 0.55
    img *= (0.8 + 0.3 * base)[..., None]
    if fuligem:
        f = smooth(fnoise(n, 1.4, rg), 0.35, 0.7) * fuligem; img = img * (1 - f[..., None] * 0.85)
    return _save(img, nome + "_albedo.png"), _normal(height, nome + "_normal.png")

def tex_pedra(nome, seed, n=512):
    """Pedra escura lascada: manchas, veios, rachaduras claras e musgo seco."""
    rg = np.random.default_rng(seed)
    base = fnoise(n, 1.7, rg); fino = fnoise(n, 0.8, rg); gr = fnoise(n, 2.4, rg)
    lasca = _discos(n, seed + 1, 380, 10, 44, 90, 165, 3.0); rach = _riscos(n, seed + 2, 40, 40, 200)
    height = 0.5 * lasca + 0.3 * fino + 0.25 * base - 0.45 * rach
    tom = np.stack([0.085 + 0.05 * gr, 0.085 + 0.046 * gr, 0.10 + 0.05 * gr], -1) * (0.7 + 0.5 * lasca)[..., None]
    tom = tom * (1 - rach[..., None] * 0.55) + (smooth(base, 0.6, 0.8) * 0.12)[..., None] * np.array([0.3, 0.5, 0.2])
    tom *= (0.8 + 0.3 * base)[..., None]
    return _save(tom, nome + "_albedo.png"), _normal(height, nome + "_normal.png", 12.0)

def tex_brasa(nome, seed, n=512):
    """Carvão com veios incandescentes: crosta escura rachada e luz alaranjada a amarela nas fendas."""
    rg = np.random.default_rng(seed)
    base = fnoise(n, 1.5, rg); fino = fnoise(n, 1.0, rg); gr = fnoise(n, 2.0, rg)
    rach = np.abs(base - 0.5) * 2                                  # linhas onde o ruído cruza 0,5
    brilho = np.clip(1 - smooth(rach, 0.0, 0.16), 0, 1) * (0.5 + 0.7 * fino)   # fendas
    brilho = np.clip(brilho + smooth(gr, 0.78, 0.9) * 0.5, 0, 1)
    crosta = np.stack([0.06 + 0.05 * fino, 0.05 + 0.03 * fino, 0.045 + 0.02 * fino], -1)
    quente = np.stack([np.ones_like(brilho), 0.28 + 0.5 * brilho, 0.04 + 0.2 * brilho ** 2], -1)
    albedo = crosta * (1 - brilho[..., None]) + quente * brilho[..., None] * 0.6
    emis = quente * (brilho ** 1.3)[..., None]
    height = 0.6 * base + 0.3 * fino - 0.4 * brilho
    return _save(albedo, nome + "_albedo.png"), _normal(height, nome + "_normal.png", 10.0), _save(emis, nome + "_emis.png")

def tex_cinza(nome, seed, n=512):
    rg = np.random.default_rng(seed); base = fnoise(n, 1.4, rg); fino = fnoise(n, 0.7, rg)
    v = 0.03 + 0.06 * base + 0.03 * smooth(fino, 0.7, 0.9)
    return _save(np.stack([v, v * 0.96, v * 0.93], -1), nome + "_albedo.png"), _normal(0.5 * base + 0.5 * fino, nome + "_normal.png", 6.0)

# ---------------------------------------------------------------- materiais
def mat(name, color=(1, 1, 1), metal=0.0, rough=0.85, image=None, normal=None, emis=None, emis_strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    if image:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(image); t.image.pack()
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if normal:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(normal); t.image.pack(); t.image.colorspace_settings.name = 'Non-Color'
        n = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(t.outputs["Color"], n.inputs["Color"]); nt.links.new(n.outputs["Normal"], b.inputs["Normal"])
    if emis:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(emis); t.image.pack()
        nt.links.new(t.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = emis_strength
    return m

bpy.ops.wm.read_factory_settings(use_empty=True)
FERRO = mat("M_Braseiro_Ferro", (1, 1, 1), 0.55, 0.7, *tex_metal("ferro", 7, fuligem=0.15))
ENVELH = mat("M_Braseiro_FerroEnvelhecido", (1, 1, 1), 0.5, 0.78, *tex_metal("envelhecido", 23, ferrugem=(0.50, 0.66), tom=(0.075, 0.058, 0.048)))
FUL = mat("M_Braseiro_Fuligem", (1, 1, 1), 0.3, 0.9, *tex_metal("fuligem", 41, ferrugem=(0.7, 0.85), fuligem=0.95, tom=(0.05, 0.045, 0.045)))
PEDRA = mat("M_Braseiro_Pedra", (1, 1, 1), 0.0, 0.92, *tex_pedra("pedra", 5))
_a, _n, _e = tex_brasa("brasa", 3)
BRASA = mat("M_Braseiro_Brasa", (1, 1, 1), 0.0, 0.7, _a, _n, _e, 3.0)
CINZA = mat("M_Braseiro_Cinza", (1, 1, 1), 0.0, 1.0, *tex_cinza("cinza", 9))

# ---------------------------------------------------------------- malha
def rng(seed): return random.Random(seed)

def add(o, m, parte=None):
    if m is not None: o.data.materials.append(m)
    objs.append(o)
    if parte: partes.setdefault(parte, []).append(o)
    return o

PARTE = [None]  # parte atual (setada pelo orquestrador)

def new(name, bm, loc=(0, 0, 0), rot=(0, 0, 0), m=None, bev=0.008, seg=2, ang=28, flat=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.location = loc
    if isinstance(rot, Quaternion): o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = rot
    else: o.rotation_euler = rot
    bpy.context.view_layer.objects.active = o
    if bev:
        mod = o.modifiers.new("bev", 'BEVEL'); mod.width = bev; mod.segments = seg; mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(ang)
        bpy.ops.object.modifier_apply(modifier="bev")
    for p in o.data.polygons: p.use_smooth = not flat
    return add(o, m, PARTE[0])

def aponta(d): return Vector(d).normalized().to_track_quat('Z', 'Y')

def jitter(bm, amp, r):
    for v in bm.verts: v.co += Vector((r.uniform(-amp, amp), r.uniform(-amp, amp), r.uniform(-amp, amp)))

def subdiv(bm, cuts):
    if cuts: bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)

def fbox(m, loc, size, rot=(0, 0, 0), cuts=2, amp=0.0035, bev=0.008, seed=1, taper=None):
    r = rng(seed); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]; v.co.y *= size[1]; v.co.z *= size[2]
        if taper:
            t = (v.co.z / size[2]) + 0.5; f = 1 + (taper - 1) * t; v.co.x *= f; v.co.y *= f
    subdiv(bm, cuts); jitter(bm, amp, r)
    return new("fb", bm, loc, rot, m, bev)

def fcyl(m, loc, r1, h, rot=(0, 0, 0), sides=8, r2=None, cuts=2, amp=0.003, bev=0.005, seed=1, caps=True):
    r = rng(seed); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=sides, radius1=r1, radius2=(r1 if r2 is None else r2), depth=h)
    if cuts:
        ed = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > h * 0.5]
        bmesh.ops.subdivide_edges(bm, edges=ed, cuts=cuts, use_grid_fill=False)
    jitter(bm, amp, r)
    return new("fc", bm, loc, rot, m, bev)

def rebite(m, loc, normal, r=0.016, seed=1):
    rr = rng(seed); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=r)
    for v in bm.verts:
        v.co.z *= 0.5; v.co += Vector((rr.uniform(-.002, .002), rr.uniform(-.002, .002), rr.uniform(-.001, .001)))
    return new("rv", bm, loc, aponta(normal), m, 0)

def espigao(m, base, direc, r, h, seed=1, sides=4):
    rr = rng(seed); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=sides, radius1=r, radius2=r * 0.04, depth=h)
    subdiv(bm, 1)
    for v in bm.verts: v.co += Vector((rr.uniform(-.004, .004), rr.uniform(-.004, .004), rr.uniform(-.004, .004)))
    d = Vector(direc).normalized()
    return new("sp", bm, Vector(base) + d * h / 2, aponta(d), m, 0.007)

def chip_corners(o, n, size, seed):
    """Lascas reais por boolean DIFFERENCE nos cantos e arestas (pedra quebrada)."""
    r = rng(seed); dx, dy, dz = o.dimensions; c = o.location; mats = list(o.data.materials)
    for _ in range(n):
        sx, sy, sz = r.choice((-1, 1)), r.choice((-1, 1)), r.choice((-1, 1))
        p = (c.x + sx * dx / 2 * r.uniform(.8, 1), c.y + sy * dy / 2 * r.uniform(.8, 1), c.z + sz * dz / 2 * r.uniform(.8, 1))
        s = size * r.uniform(0.6, 1.5)
        bpy.ops.mesh.primitive_cube_add(size=1, location=p, rotation=(r.uniform(0, 1.5), r.uniform(0, 1.5), r.uniform(0, 1.5)))
        cut = bpy.context.object; cut.scale = (s, s * r.uniform(.7, 1.3), s * r.uniform(.7, 1.3)); bpy.ops.object.transform_apply(scale=True)
        mod = o.modifiers.new("chip", 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = cut; mod.solver = 'EXACT'
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier="chip")
        bpy.data.objects.remove(cut, do_unlink=True)
    if not o.data.materials:
        for m in mats: o.data.materials.append(m)

def uv_caixa(o, escala=UVSCALE):
    me = o.data; mw = o.matrix_world
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers.active.data
    for p in me.polygons:
        n = mw.to_3x3() @ p.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            u, v = ((co.y, co.z), (co.x, co.z), (co.x, co.y))[ax]
            uvl[li].uv = (u * escala, v * escala)

def uv_todos():
    bpy.context.view_layer.update()
    for o in objs:
        for i, m in enumerate(o.data.materials):
            if m is None: o.data.materials[i] = PEDRA if 'fb' in o.name else FERRO   # slot vazio deixado pelo boolean
        uv_caixa(o)

def bake_vertex_colors(body):
    """Oclusão/cavidade em vertex color: arestas vivas claras, frestas e fuligem escuras (multiplica o albedo)."""
    me = body.data; bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    cav = {v.index: 1.0 - min(1.0, sum(f.normal.dot(v.normal) for f in v.link_faces) / max(1, len(v.link_faces))) for v in bm.verts}
    me.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER'); attr = me.color_attributes["Col"]; me.color_attributes.active_color = attr
    for poly in me.polygons:
        nome = me.materials[poly.material_index].name
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index; co = me.vertices[vi].co
            if nome in ("M_Braseiro_Brasa", "M_Braseiro_Cinza"): attr.data[li].color = (1, 1, 1, 1); continue
            edge = min(1.0, cav[vi] * 2.5); chao = max(0.0, 1.0 - co.z / 0.7) * 0.35
            k = max(0.35, min(1.0, 0.72 + 0.28 * edge - chao * (1 - edge)))
            attr.data[li].color = (k, k, k, 1)
    bm.free()
