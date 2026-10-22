"""Ferragem do estandarte: poste, braço, espigões, cintas, rebites, volutas e anéis.
Ferro forjado escuro e enferrujado: facetas de martelo (jitter controlado sobre malha subdividida),
bevel real nas arestas vivas, perfis em camadas e textura pintada em Python (albedo + normal), material M_Ferro."""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Quaternion, Matrix
from PIL import Image, ImageDraw, ImageFilter

# ------------------------------------------------------------------ textura procedural
def _fnoise(n, beta, rg):
    """Ruído de potência 1/f^beta, ladrilhável (FFT)."""
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    r = np.sqrt(fx ** 2 + fy ** 2); r[0, 0] = 1
    sp = np.fft.fft2(rg.standard_normal((n, n))) / (r ** beta)
    sp[0, 0] = 0
    o = np.real(np.fft.ifft2(sp))
    return (o - o.min()) / (o.max() - o.min())

def _smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

def gerar_texturas(L, n=512):
    """Cria ferro_albedo.png e ferro_normal.png em L.TEX_DIR."""
    rg = np.random.default_rng(7)
    base = _fnoise(n, 1.6, rg); fino = _fnoise(n, 0.9, rg); gr = _fnoise(n, 2.2, rg)
    # altura: martelado (discos achatados) + grão + riscos
    hm = Image.new("F", (n, n), 0.0)
    h_img = Image.new("L", (n, n), 128); d = ImageDraw.Draw(h_img)
    cr = np.random.default_rng(11)
    for _ in range(520):
        x, y = cr.integers(0, n, 2); rx = cr.integers(7, 26); ry = int(rx * cr.uniform(0.5, 1.2))
        v = int(cr.integers(105, 150))
        for dx in (-n, 0, n):
            for dy in (-n, 0, n):
                d.ellipse((x - rx + dx, y - ry + dy, x + rx + dx, y + ry + dy), fill=v)
    h_img = h_img.filter(ImageFilter.GaussianBlur(2.2))
    hamm = np.asarray(h_img, dtype=np.float32) / 255.0
    sc_img = Image.new("L", (n, n), 0); d = ImageDraw.Draw(sc_img)
    sr = np.random.default_rng(5)
    for _ in range(170):
        x, y = sr.integers(0, n, 2); a = sr.uniform(0, math.pi); l = sr.uniform(18, 120)
        d.line((x, y, x + math.cos(a) * l, y + math.sin(a) * l), fill=int(sr.integers(120, 255)), width=int(sr.integers(1, 3)))
    scr = np.asarray(sc_img, dtype=np.float32) / 255.0
    height = 0.55 * hamm + 0.25 * fino + 0.2 * base - 0.35 * scr

    # ferrugem: manchas + pontilhado
    rust_m = _smooth(base * 0.65 + fino * 0.35 + (gr - 0.5) * 0.2, 0.52, 0.66)
    rust_fine = _smooth(fino, 0.60, 0.75) * 0.6
    rust = np.clip(rust_m + rust_fine * 0.5, 0, 1)
    ferro = np.stack([0.085 + 0.05 * gr, 0.08 + 0.045 * gr, 0.09 + 0.05 * gr], -1)          # ferro escuro azulado
    ferro *= (0.75 + 0.5 * hamm)[..., None]                                                   # martelado marca o tom
    r1 = np.array([0.50, 0.22, 0.07]); r2 = np.array([0.27, 0.11, 0.05])                       # laranja e marrom
    ferrugem = r2[None, None] * (1 - fino[..., None]) + r1[None, None] * fino[..., None]
    ferrugem *= (0.6 + 0.6 * hamm)[..., None]
    img = ferro * (1 - rust[..., None]) + ferrugem * rust[..., None]
    # bordas gastas / riscos mais claros (aço exposto)
    gasto = scr * (0.6 + 0.4 * (1 - rust))
    img = img + (np.array([0.42, 0.40, 0.38]) - img) * (gasto[..., None] * 0.55)
    # sombras de sujeira
    img *= (0.8 + 0.3 * base)[..., None]
    a = (np.clip(img, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
    pa = os.path.join(L.TEX_DIR, "ferro_albedo.png"); Image.fromarray(a, "RGB").save(pa)

    # normal map a partir da altura
    gy, gx = np.gradient(np.pad(height, 1, mode="wrap"))
    gx = gx[1:-1, 1:-1]; gy = gy[1:-1, 1:-1]
    k = 14.0
    nv = np.stack([-gx * k, gy * k, np.ones_like(gx)], -1)
    nv /= np.linalg.norm(nv, axis=-1, keepdims=True)
    nm = ((nv * 0.5 + 0.5) * 255).astype(np.uint8)
    pn = os.path.join(L.TEX_DIR, "ferro_normal.png"); Image.fromarray(nm, "RGB").save(pn)
    return pa, pn

# ------------------------------------------------------------------ utilidades de malha
def _jitter(bm, amp, rg):
    for v in bm.verts:
        v.co += Vector((rg.uniform(-amp, amp), rg.uniform(-amp, amp), rg.uniform(-amp, amp)))

def _subdiv(bm, cuts):
    if cuts > 0:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)

def _flat(o):
    for p in o.data.polygons: p.use_smooth = False

def _obj(L, name, bm, loc, rot, m, bev, seg=2, ang=28):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.location = loc
    if isinstance(rot, Quaternion): o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = rot
    else: o.rotation_euler = rot
    bpy.context.view_layer.objects.active = o
    if bev: L.bevel_obj(o, bev, seg, ang)
    _flat(o)
    return L.add(o, m)

def aponta(d):
    """Quaternion que leva +Z do objeto para a direção d."""
    return Vector(d).normalized().to_track_quat('Z', 'Y')

def fbox(L, m, loc, size, rot=(0, 0, 0), cuts=2, amp=0.0035, bev=0.008, seed=1, taper=None):
    """Caixa forjada: subdividida, vértices deslocados (facetas de martelo), chanfro real nas arestas."""
    rg = np.random.default_rng(seed); import random; r = random.Random(seed)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]; v.co.y *= size[1]; v.co.z *= size[2]
        if taper:   # afunila em x e y conforme z (taper = fator no topo)
            t = (v.co.z / size[2]) + 0.5; f = 1 + (taper - 1) * t; v.co.x *= f; v.co.y *= f
    _subdiv(bm, cuts)
    for v in bm.verts: v.co += Vector((r.uniform(-amp, amp), r.uniform(-amp, amp), r.uniform(-amp, amp)))
    return _obj(L, "fb", bm, loc, rot, m, bev)

def fcyl(L, m, loc, r1, h, rot=(0, 0, 0), sides=8, r2=None, cuts=3, amp=0.0025, bev=0.005, seed=1, caps=True):
    """Cilindro/cone forjado (eixo local Z), subdividido ao longo do comprimento e martelado."""
    import random; r = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=sides, radius1=r1, radius2=(r1 if r2 is None else r2), depth=h)
    if cuts:
        ed = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > h * 0.5]
        bmesh.ops.subdivide_edges(bm, edges=ed, cuts=cuts, use_grid_fill=False)
    for v in bm.verts:
        s = amp * (0.35 if abs(abs(v.co.z) - h / 2) < 1e-5 and False else 1)
        v.co += Vector((r.uniform(-amp, amp), r.uniform(-amp, amp), r.uniform(-amp, amp)))
    return _obj(L, "fc", bm, loc, rot, m, bev)

def frebite(L, m, loc, normal, r=0.014, seed=1):
    """Rebite: cúpula achatada e levemente torta, apontando para 'normal'."""
    import random; rr = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=7, v_segments=4, radius=r)
    for v in bm.verts:
        if v.co.z < -r * 0.2: v.co.z = -r * 0.2          # corta a metade de baixo (assenta na superfície)
        v.co.z *= 0.7
        v.co += Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(-1, 1))) * r * 0.1
    return _obj(L, "rv", bm, loc, aponta(normal), m, 0)

def rebites_linha(L, m, p0, p1, normal, n, r=0.013, seed=1):
    for i in range(n):
        t = (i + 0.5) / n
        frebite(L, m, Vector(p0).lerp(Vector(p1), t), normal, r, seed + i)

def espigao(L, m, base, direc, r, h, seed=1, sides=4):
    """Espigão: base em bulbo facetado + haste cônica de 4 faces levemente torta."""
    d = Vector(direc).normalized(); q = aponta(d)
    fcyl(L, m, base + d * (h * 0.04), r * 1.25, h * 0.10, q, sides=sides * 2, r2=r * 1.0, cuts=0, amp=0.0015, bev=0.003, seed=seed)
    fcyl(L, m, base + d * (h * 0.12 + h * 0.44), r * 0.95, h * 0.88, q, sides=sides, r2=r * 0.02, cuts=2, amp=0.0022, bev=0.0025, seed=seed + 1)

def barra(L, m, pts, r, seed=1, tape=(0.55, 1.0), res=1):
    """Barra dobrada: curva 3D POLY com bevel_depth, convertida em malha. pts = lista de Vector."""
    cu = bpy.data.curves.new("bar", 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = r; cu.bevel_resolution = res; cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    import random; rr = random.Random(seed)
    n = len(pts)
    for i, (p, pt) in enumerate(zip(pts, sp.points)):
        pt.co = (p.x + rr.uniform(-0.0012, 0.0012), p.y + rr.uniform(-0.0012, 0.0012), p.z + rr.uniform(-0.0012, 0.0012), 1)
        t = i / (n - 1)
        pt.radius = tape[1] - (tape[1] - tape[0]) * (abs(t - 0.5) * 2) ** 2 * 0.0 + 0  # base
        # afina nas pontas do arame, volume no meio
        pt.radius = tape[0] + (tape[1] - tape[0]) * (1 - abs(t - 0.5) * 2) ** 0.6
    o = bpy.data.objects.new("bar", cu); bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    for ob in bpy.context.selected_objects: ob.select_set(False)
    o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    _flat(o)
    return L.add(o, m)

def espiral(c, a0, a1, th0, th1, n, plano="xz", dy=0.0, rot0=0.0, flip=1.0):
    """Pontos de espiral de Arquimedes no plano xz (ou yz): raio a0->a1, ângulo th0->th1."""
    out = []
    for i in range(n):
        t = i / (n - 1); a = a0 + (a1 - a0) * t; th = th0 + (th1 - th0) * t
        u = a * math.cos(th) * flip; v = a * math.sin(th)
        out.append(Vector((c[0] + u, c[1] + dy, c[2] + v)) if plano == "xz" else Vector((c[0] + dy, c[1] + u, c[2] + v)))
    return out

def cat(*listas):
    out = []
    for l in listas: out += l
    return out

def curva_suave(pts, sub=6):
    """Catmull-Rom sobre pontos de controle (Vectors)."""
    out = []; P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(sub):
            t = s / sub
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1]); return out

# ------------------------------------------------------------------ UV por projeção em caixa (coordenadas de mundo)
def uv_caixa(o, escala=1.6):
    me = o.data; mw = o.matrix_world
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers.active.data
    for p in me.polygons:
        n = mw.to_3x3() @ p.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            if ax == 0: u, v = co.y, co.z
            elif ax == 1: u, v = co.x, co.z
            else: u, v = co.x, co.y
            uvl[li].uv = (u * escala, v * escala)

# ------------------------------------------------------------------ construção
def build(L):
    PX, POST_TOP, ARM_Z, AX1 = L.PX, L.POST_TOP, L.ARM_Z, L.AX1
    inicio = len(L.objs)
    pa, pn = gerar_texturas(L)
    M = L.mat("M_Ferro", (0.12, 0.1, 0.1), metal=0.55, rough=0.72, image=pa, normal=pn)
    V = lambda *a: Vector(a[0]) if len(a) == 1 else Vector(a)
    S = 0.065   # meia largura do fuste (poste quadrado de 0.13)

    # ---------- poste: fuste em camadas
    z0 = 0.30
    fbox(L, M, (PX, 0, z0 + 0.03), (0.19, 0.19, 0.06), M and None or M, cuts=2, bev=0.012, seed=2) if False else None
    # sapata escalonada
    fbox(L, M, (PX, 0, z0 + 0.025), (0.20, 0.20, 0.05), cuts=3, bev=0.010, seed=2)
    fbox(L, M, (PX, 0, z0 + 0.07), (0.165, 0.165, 0.035), cuts=3, bev=0.008, seed=3)
    fbox(L, M, (PX, 0, z0 + 0.10), (0.14, 0.14, 0.03), cuts=2, bev=0.006, seed=4, taper=0.92)
    # fuste (chanfro largo = bevel maior) em 3 segmentos para ter emendas
    seg = [(z0 + 0.115, 1.15), (1.15, 2.05), (2.05, POST_TOP - 0.16)]
    for i, (za, zb) in enumerate(seg):
        fbox(L, M, (PX, 0, (za + zb) / 2), (0.13, 0.13, zb - za), cuts=5, amp=0.003, bev=0.014, seed=10 + i)
    # cintas / abraçadeiras com moldura em camadas e rebites
    def cinta(z, h=0.07, w=0.17, seed=1):
        fbox(L, M, (PX, 0, z), (w, w, h), cuts=3, bev=0.011, seed=seed)
        fbox(L, M, (PX, 0, z + h / 2 + 0.008), (w - 0.025, w - 0.025, 0.016), cuts=2, bev=0.005, seed=seed + 1)
        fbox(L, M, (PX, 0, z - h / 2 - 0.008), (w - 0.025, w - 0.025, 0.016), cuts=2, bev=0.005, seed=seed + 2)
        hw = w / 2
        for sx in (-1, 1):
            rebites_linha(L, M, (PX + sx * 0.04, hw, z), (PX + sx * 0.04, hw, z), (0, 1, 0), 1, 0.014, seed + 3)
        rebites_linha(L, M, (PX - 0.05, hw, z), (PX + 0.05, hw, z), (0, 1, 0), 3, 0.012, seed + 5)
        rebites_linha(L, M, (PX - 0.05, -hw, z), (PX + 0.05, -hw, z), (0, -1, 0), 3, 0.012, seed + 9)
        rebites_linha(L, M, (PX + hw, -0.05, z), (PX + hw, 0.05, z), (1, 0, 0), 2, 0.012, seed + 13)
        rebites_linha(L, M, (PX - hw, -0.05, z), (PX - hw, 0.05, z), (-1, 0, 0), 2, 0.012, seed + 17)
    cinta(0.62, 0.08, 0.175, 30); cinta(1.15, 0.06, 0.165, 40); cinta(1.65, 0.08, 0.175, 50)
    cinta(2.05, 0.06, 0.165, 60); cinta(2.50, 0.07, 0.17, 70)

    # ---------- junção do braço: bloco com molduras, atravessado pelo braço
    fbox(L, M, (PX, 0, ARM_Z), (0.19, 0.19, 0.20), cuts=4, bev=0.014, seed=80)
    fbox(L, M, (PX, 0, ARM_Z + 0.115), (0.17, 0.17, 0.03), cuts=2, bev=0.006, seed=81, taper=0.9)
    fbox(L, M, (PX, 0, ARM_Z - 0.115), (0.17, 0.17, 0.03), cuts=2, bev=0.006, seed=82)
    fbox(L, M, (PX, 0, ARM_Z + 0.145), (0.155, 0.155, 0.02), cuts=2, bev=0.005, seed=83)
    for sz in (-1, 1):
        for sx in (-1, 1):
            frebite(L, M, V(PX + sx * 0.06, 0.095, ARM_Z + sz * 0.07), (0, 1, 0), 0.015, 90 + sx + 2 * sz)
            frebite(L, M, V(PX + sx * 0.06, -0.095, ARM_Z + sz * 0.07), (0, -1, 0), 0.015, 95 + sx + 2 * sz)

    # ---------- ponta do poste: moldura, colar e pirâmide gótica com espigões laterais
    zt = POST_TOP - 0.16
    fbox(L, M, (PX, 0, POST_TOP - 0.09), (0.175, 0.175, 0.05), cuts=3, bev=0.010, seed=100)
    fbox(L, M, (PX, 0, POST_TOP - 0.045), (0.15, 0.15, 0.04), cuts=2, bev=0.008, seed=101, taper=1.1)
    fbox(L, M, (PX, 0, POST_TOP + 0.005), (0.185, 0.185, 0.05), cuts=3, bev=0.011, seed=102)   # capitel
    fbox(L, M, (PX, 0, POST_TOP + 0.045), (0.14, 0.14, 0.035), cuts=2, bev=0.007, seed=103)
    # pirâmide gótica: 4 faces, base quadrada, pontas facetadas
    fcyl(L, M, (PX, 0, POST_TOP + 0.20), 0.095, 0.28, sides=4, r2=0.006, cuts=6, amp=0.0035, bev=0.004, seed=104,
         rot=(0, 0, math.radians(45)))
    fcyl(L, M, (PX, 0, POST_TOP + 0.375), 0.02, 0.06, sides=4, r2=0.0, cuts=1, amp=0.001, bev=0.002, seed=105,
         rot=(0, 0, math.radians(45)))
    # 4 espigões laterais saindo do capitel (inclinados para fora e para cima)
    for k, (dx, dy) in enumerate(((1, 0), (-1, 0), (0, 1), (0, -1))):
        d = V(dx * 1.0, dy * 1.0, 0.55)
        espigao(L, M, V(PX + dx * 0.09, dy * 0.09, POST_TOP + 0.01), d, 0.018, 0.17, seed=110 + k * 3)
    # 4 mini-pináculos nos cantos do capitel
    for k, (dx, dy) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        espigao(L, M, V(PX + dx * 0.07, dy * 0.07, POST_TOP + 0.03), V(dx * 0.25, dy * 0.25, 1), 0.014, 0.11, seed=130 + k * 3)

    # ---------- braço horizontal (octogonal forjado) com molduras e anéis
    ax0 = PX - 0.06
    comp = AX1 - ax0
    ra = 0.036
    rot_x = Quaternion((0, 1, 0), math.radians(90))     # eixo local Z -> +X
    fcyl(L, M, (ax0 + comp / 2, 0, ARM_Z), ra, comp, rot_x, sides=8, cuts=16, amp=0.0022, bev=0.006, seed=150)
    # espigão esquerdo (atrás do poste) e braçadeiras com moldura
    espigao(L, M, V(ax0 - 0.01, 0, ARM_Z), (-1, 0, 0), 0.032, 0.13, seed=151)
    # colar do braço junto ao poste (do lado direito)
    def colar(x, seed, r=0.054, w=0.05):
        fcyl(L, M, (x, 0, ARM_Z), r, w, rot_x, sides=8, cuts=1, amp=0.0018, bev=0.006, seed=seed)
        fcyl(L, M, (x - w / 2 - 0.007, 0, ARM_Z), r * 1.1, 0.014, rot_x, sides=8, cuts=0, amp=0.001, bev=0.003, seed=seed + 1)
        fcyl(L, M, (x + w / 2 + 0.007, 0, ARM_Z), r * 1.1, 0.014, rot_x, sides=8, cuts=0, amp=0.001, bev=0.003, seed=seed + 2)
        for k in range(8):   # rebites ao redor
            a = k * math.pi / 4 + 0.2
            frebite(L, M, V(x, math.cos(a) * r * 0.98, ARM_Z + math.sin(a) * r * 0.98), V(0, math.cos(a), math.sin(a)), 0.009, seed + 3 + k)
    colar(PX + 0.14, 160)
    colar(-0.52, 170, 0.049, 0.035)      # colar logo antes do pano
    colar(0.52, 180, 0.049, 0.035)
    colar(AX1 - 0.17, 190, 0.058, 0.07)  # colar de onde saem os espigões

    # anéis onde o pano pendura (torus ao redor do braço, plano yz)
    for k, x in enumerate((-0.36, -0.12, 0.12, 0.36)):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.056, minor_radius=0.011, major_segments=14, minor_segments=6,
                                         location=(x, 0, ARM_Z), rotation=(0, math.radians(90), 0))
        o = bpy.context.object
        bm = bmesh.new(); bm.from_mesh(o.data)
        import random; rr = random.Random(200 + k)
        for v in bm.verts: v.co += V(rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(-1, 1)) * 0.0018
        bm.to_mesh(o.data); bm.free(); _flat(o)
        L.add(o, M)
        # nó/emenda do anel (pequeno bloco forjado no topo)
        fbox(L, M, (x, 0, ARM_Z + 0.06), (0.03, 0.026, 0.02), cuts=1, bev=0.004, seed=205 + k, amp=0.0015)

    # ponta direita: espigão central + 2 inclinados (cima/baixo), em torno da colar
    tip = V(AX1 + 0.0, 0, ARM_Z)
    espigao(L, M, tip, (1, 0, 0), 0.034, 0.22, seed=250)
    espigao(L, M, V(AX1 - 0.14, 0, ARM_Z + 0.04), (0.45, 0, 1), 0.026, 0.19, seed=253)
    espigao(L, M, V(AX1 - 0.14, 0, ARM_Z - 0.04), (0.45, 0, -1), 0.026, 0.19, seed=256)
    espigao(L, M, V(AX1 - 0.14, 0.04, ARM_Z), (0.4, 1, 0), 0.02, 0.14, seed=259)
    espigao(L, M, V(AX1 - 0.14, -0.04, ARM_Z), (0.4, -1, 0), 0.02, 0.14, seed=262)
    # espigões no meio do braço (em cima, entre anéis e nas pontas)
    for k, x in enumerate((-0.48, 0.48)):
        espigao(L, M, V(x, 0, ARM_Z + 0.045), (0, 0, 1), 0.016, 0.1, seed=270 + k * 3)

    # ---------- escora diagonal (barra chata com moldura e voluta) no plano xz, y=0
    xp = PX + S                      # face direita do poste
    xb = -0.475                      # onde encosta no braço (fora do pano)
    p_low = V(xp - 0.005, 0, 2.00); p_hi = V(xb, 0, ARM_Z - 0.035)
    dv = p_hi - p_low; ang = math.atan2(dv.z, dv.x); ln = dv.length
    qd = Quaternion((0, 1, 0), -ang)
    fbox(L, M, (p_low + dv / 2), (ln + 0.02, 0.046, 0.055), rot=Euler_from_q(qd) if False else (0, -ang, 0), cuts=9, amp=0.0025, bev=0.008, seed=300)
    fbox(L, M, (p_low + dv / 2 + V(0, 0, 0)), (ln * 0.8, 0.058, 0.02), rot=(0, -ang, 0), cuts=6, amp=0.002, bev=0.004, seed=301)
    # braçadeira inferior e superior da escora
    for q, sd in ((p_low, 305), (p_hi, 310)):
        fbox(L, M, q, (0.045, 0.06, 0.07), rot=(0, -ang, 0), cuts=2, bev=0.008, seed=sd)
        for sy in (-1, 1): frebite(L, M, q + V(0, sy * 0.03, 0), (0, sy, 0), 0.012, sd + 3 + sy)
    rebites_linha(L, M, p_low + dv * 0.3 + V(0, 0.017, 0.0), p_low + dv * 0.7 + V(0, 0.017, 0.0), (0, 1, 0), 3, 0.011, 320)
    # voluta no triângulo entre poste, braço e escora (spiral pequena + S)
    esp = espiral((-0.538, 0, 2.70), 0.075, 0.010, math.radians(-30), math.radians(520), 22)
    barra(L, M, curva_suave(esp, 1), 0.013, seed=330, tape=(0.55, 1.0))
    # S de ligação: do poste ao braço
    pts = [V(xp, 0, 2.60), V(-0.585, 0, 2.66), V(-0.535, 0, 2.74), V(-0.495, 0, 2.82), V(-0.50, 0, ARM_Z - 0.04)]
    barra(L, M, curva_suave(pts, 5), 0.014, seed=340, tape=(0.6, 1.0))

    # ---------- ornamentos góticos em cima do braço (arcos/volutas de barra dobrada)
    # arco ascendente do braço ao poste com voluta em cada ponta
    arc = [V(PX + S + 0.005, 0, 3.02), V(-0.55, 0, 3.07), V(-0.50, 0, 3.05), V(-0.455, 0, 3.0), V(-0.42, 0, 2.95), V(-0.40, 0, ARM_Z + 0.04)]
    barra(L, M, curva_suave(arc, 6), 0.015, seed=350, tape=(0.7, 1.0))
    esp2 = espiral((-0.44, 0, 3.05), 0.0001, 0.05, math.radians(-90), math.radians(520), 22, flip=-1.0)
    barra(L, M, curva_suave(esp2[::-1], 1), 0.012, seed=351, tape=(0.55, 1.0))
    # ponta de lança em cima do braço perto do espigão direito: gancho em C
    c1 = [V(0.60, 0, ARM_Z + 0.03), V(0.66, 0, ARM_Z + 0.13), V(0.58, 0, ARM_Z + 0.24), V(0.46, 0, ARM_Z + 0.22), V(0.43, 0, ARM_Z + 0.14), V(0.48, 0, ARM_Z + 0.10)]
    barra(L, M, curva_suave(c1, 5), 0.012, seed=360, tape=(0.5, 1.0))
    # gancho caindo na ponta direita (onde se pendura uma corrente/flâmula), em C para baixo
    c2 = [V(0.62, 0, ARM_Z - 0.03), V(0.68, 0, ARM_Z - 0.11), V(0.62, 0, ARM_Z - 0.20), V(0.54, 0, ARM_Z - 0.18), V(0.53, 0, ARM_Z - 0.11)]
    barra(L, M, curva_suave(c2, 5), 0.012, seed=365, tape=(0.5, 1.0))

    # ---------- placa frontal e traseira no poste (ornamento de canto) com cantos góticos
    for sy, sd in ((1, 400), (-1, 420)):
        fbox(L, M, (PX, sy * (S + 0.008), 2.16), (0.11, 0.016, 0.26), cuts=4, amp=0.0022, bev=0.006, seed=sd)
        # pontas góticas nos cantos da placa
        for cz in (2.16 + 0.13, 2.16 - 0.13):
            for cx in (-1, 1):
                espigao(L, M, V(PX + cx * 0.05, sy * (S + 0.016), cz), V(cx * 0.4, sy * 0.4, 1 if cz > 2.16 else -1), 0.011, 0.07, seed=sd + 5 + cx, sides=4)
        rebites_linha(L, M, (PX - 0.04, sy * (S + 0.016), 2.16), (PX + 0.04, sy * (S + 0.016), 2.16), (0, sy, 0), 3, 0.011, sd + 12)


    # nervuras da pirâmide gótica + cravos (crockets) ao longo delas
    apex = V(PX, 0, POST_TOP + 0.335)
    for k, (cx, cy) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        b0 = V(PX + cx * 0.066, cy * 0.066, POST_TOP + 0.065)
        dv2 = apex - b0
        fbox(L, M, b0 + dv2 * 0.5, (0.016, 0.016, dv2.length), rot=aponta(dv2), cuts=5, amp=0.0015, bev=0.004, seed=500 + k)
        for t, sc_ in ((0.3, 1.0), (0.55, 0.8), (0.78, 0.6)):
            p = b0 + dv2 * t
            espigao(L, M, p, V(cx * 1.0, cy * 1.0, 0.9), 0.008 * sc_ + 0.002, 0.05 * sc_ + 0.01, seed=510 + k * 5 + int(t * 10), sides=4)
    # molduras elevadas (painéis) nas faces frontal e traseira do fuste
    for sy in (1, -1):
        for j, (za, zb) in enumerate(((0.72, 1.08), (1.24, 1.58), (1.74, 2.0))):
            zc = (za + zb) / 2; hh = zb - za
            for sx in (-1, 1):
                fbox(L, M, (PX + sx * 0.04, sy * (S + 0.003), zc), (0.012, 0.012, hh), cuts=6, amp=0.0012, bev=0.003, seed=600 + j + sx)
            for zz in (za, zb):
                fbox(L, M, (PX, sy * (S + 0.003), zz), (0.092, 0.012, 0.012), cuts=3, amp=0.0012, bev=0.003, seed=610 + j)
            for sx in (-1, 1):
                for zz in (za, zb): frebite(L, M, V(PX + sx * 0.04, sy * (S + 0.009), zz), (0, sy, 0), 0.01, 620 + j)

    # ---------- finalização: UVs em caixa para todos os objetos desta parte
    for o in L.objs[inicio:]:
        if o.type == 'MESH': uv_caixa(o)


def Euler_from_q(q):
    return q.to_euler()
