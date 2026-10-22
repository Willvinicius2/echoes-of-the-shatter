"""Módulo 3D: poça d'água da Cripta (objeto separado, espalhado sobre o piso aprovado).
python poca.py <pasta_glb> [pasta_previas]       VARIANTES=A,B,C  AMOSTRAS=24  RAPIDO=1
Metros, +Z para cima, pivô no centro da poça, apoiada em z=0 (piso). Três variações de forma (A redonda com lóbulo,
B alongada com rabo, C rim de dois lóbulos). Cada variante é um .glb com 3 malhas:
  - Agua: lâmina rasa de contorno irregular e nítido, borda com menisco; UV2 = (profundidade, opacidade) para o shader.
  - Anel: faixa de pedra molhada escurecendo o piso em volta (alfa degradê, falhando com ruído).
  - Limo: calotas de musgo junto à borda (M_Limo). Variantes: A pequena, B média alongada, C grande com ilha de pedra.
  - (PEDRAS=1 gera também as pedrinhas, hoje um objeto separado)
  - Pedrinhas: seixos facetados e blocos da ilha (C) (material M_PedraEscura, o Godot troca pela pedra triplanar).
Materiais por nome (o Godot troca): M_Agua -> cripta_agua.gdshader; M_AnelMolhado -> M_Cripta_AnelMolhado.tres."""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None
VARS = os.environ.get("VARIANTES", "A,B,C").split(",")

# ---- contrato de medidas por variante: (semente, raio base, escala x, escala y, lóbulos[(ângulo, força, largura)])
VAR = {
    "A": dict(seed=11, R=0.27, sx=1.0, sy=0.85, lobes=[(0.6, 0.3, 0.5)], ring=0.14, n_peb=4, tongues=2, musgo=1, ilha=0),    # pequena
    "B": dict(seed=23, R=0.34, sx=1.7, sy=0.55, lobes=[(3.2, 0.45, 0.35), (0.2, 0.18, 0.5)], ring=0.24, n_peb=7, tongues=4, musgo=2, ilha=0),  # média alongada
    "C": dict(seed=37, R=0.62, sx=1.12, sy=0.9, lobes=[(1.1, 0.4, 0.45), (4.3, 0.35, 0.5)], ring=0.32, n_peb=8, tongues=5, musgo=3, ilha=1),   # grande com ilha de pedra
}
Z_BORDA, Z_MENISCO, Z_AGUA = 0.003, 0.0145, 0.013     # perfil da lâmina (m)
Z_ANEL = 0.0015

def seno_periodico(seed, n, amp_ini, decai):
    r = random.Random(seed); return [(k, amp_ini * decai ** k * r.uniform(0.5, 1.0), r.uniform(0, 6.283)) for k in range(2, n)]

def contorno(v):
    """Devolve f(θ) -> (x, y) da borda: raio com harmônicos baixos (forma) + altos (serrilhado nítido) + lóbulos gaussianos."""
    H = seno_periodico(v["seed"], 8, 0.16, 0.82)
    S = seno_periodico(v["seed"] + 7, 22, 0.05, 0.93)
    S = [(k + 7, a, p) for k, a, p in S]
    def f(t):
        r = 1.0 + sum(a * math.sin(k * t + p) for k, a, p in H) + sum(a * math.sin(k * t + p) for k, a, p in S)
        for ang, forca, larg in v["lobes"]:
            d = math.atan2(math.sin(t - ang), math.cos(t - ang)); r += forca * math.exp(-(d / larg) ** 2)
        r *= v["R"]
        return Vector((math.cos(t) * r * v["sx"], math.sin(t) * r * v["sy"]))
    return f

def ruido_t(seed, t, k=5):
    r = random.Random(seed); return sum(r.uniform(0.4, 1) * math.sin((i + 2) * t + r.uniform(0, 6.28)) for i in range(k)) / k

# ---------------------------------------------------------------- materiais
def mat(nome, cor, rough, alpha=None, vcol=False, metal=0.0, ior=1.33):
    m = bpy.data.materials.new(nome); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*cor, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    b.inputs["IOR"].default_value = ior
    if alpha is not None or vcol:
        a = m.node_tree.nodes.new("ShaderNodeVertexColor"); a.layer_name = "Col"
        if vcol and alpha is not None:
            mul = m.node_tree.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = alpha
            m.node_tree.links.new(a.outputs["Alpha"], mul.inputs[0]); m.node_tree.links.new(mul.outputs[0], b.inputs["Alpha"])
        m.surface_render_method = 'BLENDED'
    return m

# ---------------------------------------------------------------- partes
def tri_fan(bm, aneis, cor):
    """aneis: lista de listas de vértices (mesmo S); o primeiro pode ser 1 vértice (centro)."""
    S = len(aneis[-1]); lay = bm.loops.layers.color["Col"]
    for a, b in zip(aneis[:-1], aneis[1:]):
        for i in range(S):
            j = (i + 1) % S
            if len(a) == 1: fs = [(a[0], b[i], b[j])]
            else: fs = [(a[i], b[i], b[j]), (a[i], b[j], a[j])]
            for f in fs:
                face = bm.faces.new(f)
                for lp in face.loops: lp[lay] = cor[lp.vert.index]

def parte_agua(v, M, f, S=160, N=26):
    bm = bmesh.new(); bm.loops.layers.color.new("Col"); cor = {}
    rnd = random.Random(v["seed"] + 100); fase = [rnd.uniform(0, 6.28) for _ in range(4)]
    def vert(x, y, z, depth, alpha):
        vv = bm.verts.new((x, y, z)); bm.verts.index_update(); cor[vv.index] = (depth, 0.0, 0.0, alpha); return vv
    rr = random.Random(v["seed"] + 150); gotas = [(rr.uniform(-0.45, 0.45) * v["R"] * v["sx"], rr.uniform(-0.4, 0.4) * v["R"] * v["sy"], rr.uniform(0.04, 0.12)) for _ in range(1 + (v["seed"] % 3))]
    def onda(x, y):
        z = 0.0009 * math.sin(x * 33 + fase[0] + 1.7 * math.sin(y * 17)) + 0.0007 * math.sin(y * 41 + fase[1] + x * 11)      # ondulação rasa e cruzada
        for gx, gy, r0 in gotas:                                                                                        # anéis de gota que se abrem
            d = math.hypot(x - gx, y - gy)
            for q in range(3): z += 0.0022 * math.exp(-((d - r0 * (1 + q * 0.55)) / 0.012) ** 2) * math.cos((d - r0) * 150) * (0.8 ** q)
        return z
    c = vert(0, 0, Z_AGUA, 1.0, 1.0); aneis = [[c]]
    for i in range(1, N + 1):
        t = i / N; anel = []
        for s in range(S):
            th = 6.2832 * s / S; p = f(th)
            if t >= 0.999: z, d, al = Z_BORDA, 0.0, 0.0                         # pé do menisco: some no piso
            else:
                z = Z_AGUA + onda(p.x * t, p.y * t) * min(1, (0.92 - t) * 12 + 0.0) if t < 0.92 else Z_MENISCO + (Z_BORDA - Z_MENISCO) * ((t - 0.92) / 0.08) ** 2
                prof = (1 - t) ** 0.7 + 0.12 * math.sin(th * 5 + fase[2]) * math.sin(t * 6 + fase[3])
                d, al = max(0.0, min(1.0, prof)), 1.0 if t < 0.97 else 0.85
            anel.append(vert(p.x * t, p.y * t, z, d, al))
        aneis.append(anel)
    bm.verts.ensure_lookup_table(); tri_fan(bm, aneis, {k: val for k, val in cor.items()})
    # UV planar em metros/1.8 (o shader usa posição de mundo; a UV serve de reserva)
    uv = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for lp in face.loops: lp[uv].uv = (lp.vert.co.x / 1.8 + 0.5, lp.vert.co.y / 1.8 + 0.5)
    u2 = bm.loops.layers.uv.new("Dados"); cl = bm.loops.layers.color["Col"]
    for face in bm.faces:
        for lp in face.loops: lp[u2].uv = (lp[cl][0], lp[cl][3])       # UV2 no Godot: x = profundidade, y = opacidade
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("Agua"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new("Agua", me); bpy.context.collection.objects.link(o); me.materials.append(M["agua"]); return o

def parte_anel(v, M, f, S=180, N=12):
    bm = bmesh.new(); bm.loops.layers.color.new("Col"); cor = {}
    sem = v["seed"] + 200
    def vert(x, y, z, a):
        vv = bm.verts.new((x, y, z)); bm.verts.index_update(); cor[vv.index] = (0.02, 0.025, 0.035, a); return vv
    aneis = []
    for j in range(N + 1):
        u = j / N; anel = []
        for s in range(S):
            th = 6.2832 * s / S; p = f(th)
            alcance = v["ring"] * (0.45 + 0.55 * (ruido_t(sem, th, 6) * 0.5 + 0.5) ** 1.4 + 0.3 * ruido_t(sem + 3, th * 3.1, 4) + 0.12 * ruido_t(sem + 9, th * 9, 5))
            for k in range(v["tongues"]):
                ang = random.Random(sem + 50 + k).uniform(0, 6.2832); d = math.atan2(math.sin(th - ang), math.cos(th - ang))
                alcance += v["ring"] * 1.9 * math.exp(-(d / 0.11) ** 2)      # escorrido que segue a junta das lajes
            alcance = max(0.05, alcance)
            n = p.normalized() if p.length > 1e-6 else Vector((1, 0)); lado = Vector((n.x / v["sx"], n.y / v["sy"])).normalized()
            q = p * 0.97 + lado * (alcance * u)
            fur = 0.5 + 0.5 * math.sin(th * 23 + u * 7 + sem) * math.sin(th * 11 - u * 4) * (0.6 + 0.4 * math.sin(th * 47 + u * 15))     # falhas na mancha: pedra seca aparecendo
            a = (0.55 * (1 - u) ** 0.8 + 0.4 * (1 - u) ** 2.6) * (0.55 + 0.45 * fur)
            if j == N: a = 0.0
            anel.append(vert(q.x, q.y, Z_ANEL, a))
        aneis.append(anel)
    bm.verts.ensure_lookup_table()
    lay = bm.loops.layers.color["Col"]
    for a, b in zip(aneis[:-1], aneis[1:]):
        for i in range(S):
            j = (i + 1) % S
            for fv in ((a[i], b[i], b[j]), (a[i], b[j], a[j])):
                face = bm.faces.new(fv)
                for lp in face.loops: lp[lay] = cor[lp.vert.index]
    uv = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for lp in face.loops: lp[uv].uv = (lp.vert.co.x / 2.6 + 0.5, lp.vert.co.y / 2.6 + 0.5)
    u2 = bm.loops.layers.uv.new("Dados"); cl = bm.loops.layers.color["Col"]
    for face in bm.faces:
        for lp in face.loops: lp[u2].uv = (lp[cl][3], 0.0)             # UV2 no Godot: x = opacidade da mancha
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("Anel"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new("Anel", me); bpy.context.collection.objects.link(o); me.materials.append(M["anel"]); return o

def seixo(r, rnd, M, n=1):
    """Pedra pequena com arestas: poliedro (icosfera subdiv 1) esticado, vértices deslocados, base reta, sombreado chapado."""
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=n, radius=1)
    sx, sy, sz = rnd.uniform(0.8, 1.4), rnd.uniform(0.7, 1.15), rnd.uniform(0.35, 0.6)
    for vv in bm.verts:
        k = 1 + rnd.uniform(-0.28, 0.2); vv.co = Vector((vv.co.x * sx * k, vv.co.y * sy * k, max(vv.co.z * sz * k, -0.2 * sz))) * r
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("seixo"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    me.materials.append(M["pedra"]); return me

def parte_pedrinhas(v, M, f):
    rnd = random.Random(v["seed"] + 300); objs = []
    for i in range(v["n_peb"]):
        th = rnd.uniform(0, 6.2832); p = f(th)
        zona = rnd.random()
        if zona < 0.55: t = rnd.uniform(0.93, 1.1)          # na borda
        elif zona < 0.8: t = rnd.uniform(0.55, 0.9)         # dentro da água
        else: t = rnd.uniform(1.12, 1.45)                   # espalhadas fora
        r = rnd.choice((0.016, 0.022, 0.03, 0.04)) * rnd.uniform(0.85, 1.2)
        me = seixo(r, rnd, M); o = bpy.data.objects.new(f"seixo{i}", me); bpy.context.collection.objects.link(o)
        o.location = (p.x * t, p.y * t, 0.0 if t < 0.9 else 0.001); o.rotation_euler = (rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), rnd.uniform(0, 6.28))
        objs.append(o)
    # lascas planas grandes: uma ou duas lajotas quebradas encostadas na borda
    for i in range(1 + (v["seed"] % 2)):
        th = rnd.uniform(0, 6.2832); p = f(th) * 1.08
        me = seixo(0.07, rnd, M)
        for vv in me.vertices: vv.co.z *= 0.55
        o = bpy.data.objects.new(f"lasca{i}", me); bpy.context.collection.objects.link(o); o.location = (p.x, p.y, 0.002); o.rotation_euler = (0, 0, rnd.uniform(0, 6.28)); objs.append(o)
    if v["ilha"]:     # ilha de pedra no meio: laje quebrada com blocos menores empilhados
        c = f(2.0) * 0.0 + Vector((0.12, -0.05))
        for k, (dx, dy, rr, hh) in enumerate(((0, 0, 0.15, 0.6), (0.13, 0.05, 0.085, 0.8), (-0.1, 0.09, 0.07, 0.9), (0.04, -0.12, 0.075, 0.7), (-0.02, 0.02, 0.07, 1.6))):
            me = seixo(rr, rnd, M, 2)
            for vv in me.vertices: vv.co.z *= hh * (1.0 if k < 4 else 0.7)
            o = bpy.data.objects.new(f"ilha{k}", me); bpy.context.collection.objects.link(o); o.location = (c.x + dx, c.y + dy, 0.0 + (0.035 if k == 4 else 0)); o.rotation_euler = (0, 0, rnd.uniform(0, 6.28)); objs.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join(); o = bpy.context.object; o.name = "Pedrinhas"
    return o

def parte_limo(v, M, f):
    """Limo/musgo em calotas com volume (domos de 1–3 cm) concentradas na borda, em dois tons (M_Limo escuro, M_LimoClaro amarelado)."""
    rnd = random.Random(v["seed"] + 400); bm = bmesh.new(); tons = []
    import mathutils
    for k in range(v["musgo"]):
        th = rnd.uniform(0, 6.2832); p = f(th)
        for j in range(rnd.randint(12, 20)):       # tufo = muitas calotas apertadas ao longo da borda
            t = rnd.uniform(0.97, 1.06); a2 = th + rnd.uniform(-0.28, 0.28); q = f(a2) * t
            r2 = rnd.choice((0.008, 0.011, 0.016, 0.024, 0.036)) * (0.8 + v["R"]); alt = rnd.uniform(0.25, 0.6) * r2 * 1.2; alongar = rnd.choice((1, 1, 2.2)); tg = Vector((-math.sin(a2), math.cos(a2)))
            g = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1, matrix=mathutils.Matrix.Translation((q.x, q.y, 0.0)))
            for vv in g["verts"]:
                dx, dy, dz = vv.co.x - q.x, vv.co.y - q.y, vv.co.z
                ex = (dx * tg.x + dy * tg.y) * alongar; ey = -dx * tg.y + dy * tg.x; vv.co = Vector((q.x + (ex * tg.x - ey * tg.y) * r2 * rnd.uniform(0.85, 1.2), q.y + (ex * tg.y + ey * tg.x) * r2 * rnd.uniform(0.85, 1.2), max(dz, 0.0) * alt))
            tons.append((g["verts"], rnd.random() < 0.4))
    me = bpy.data.meshes.new("Limo"); bm.to_mesh(me); bm.free()
    me.materials.append(M["limo"]); me.materials.append(M["limo2"])
    # tom por calota: faces ligadas por vértices contíguos de 42 vértices (icosfera subdiv 2)
    for i, pl in enumerate(me.polygons):
        pl.use_smooth = True; pl.material_index = 1 if tons[min(pl.vertices[0] // 42, len(tons) - 1)][1] else 0
    o = bpy.data.objects.new("Limo", me); bpy.context.collection.objects.link(o); return o

# ---------------------------------------------------------------- montagem / exportação / prévias
def materiais():
    return dict(agua=mat("M_Agua", (0.012, 0.02, 0.04), 0.0, alpha=0.88, vcol=True),
                anel=mat("M_AnelMolhado", (0.02, 0.025, 0.035), 0.12, alpha=1.0, vcol=True),
                pedra=mat("M_PedraEscura", (0.034, 0.036, 0.048), 0.5), limo=mat("M_Limo", (0.006, 0.012, 0.006), 0.92), limo2=mat("M_LimoClaro", (0.014, 0.024, 0.01), 0.88))

def construir(nome):
    v = VAR[nome]; M = materiais(); f = contorno(v)
    partes = [parte_anel(v, M, f), parte_agua(v, M, f), parte_limo(v, M, f)]
    if os.environ.get("PEDRAS"): partes.append(parte_pedrinhas(v, M, f))      # as pedras serão um objeto separado
    return v, partes

def exportar(nome, partes):
    bpy.ops.object.select_all(action='DESELECT')
    for o in partes: o.select_set(True)
    kw = dict(filepath=os.path.join(OUT, f"SM_Cripta_Poca_{nome}.glb"), use_selection=True, export_format='GLB', export_yup=True,
              export_image_format='JPEG', export_jpeg_quality=88)
    try: bpy.ops.export_scene.gltf(export_vertex_color='NONE', **kw)
    except TypeError: bpy.ops.export_scene.gltf(**kw)

def cena_previa(partes, piso_tex):
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get("AMOSTRAS", 24)); sc.cycles.use_denoising = True
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("w"); w.use_nodes = True; nt = w.node_tree; sc.world = w
    bg = nt.nodes["Background"]; tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); rp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], rp.inputs[0]); nt.links.new(rp.outputs[0], bg.inputs[0])
    cr = rp.color_ramp; cr.elements[0].position = 0.45; cr.elements[0].color = (0.02, 0.025, 0.05, 1); cr.elements[1].position = 0.78; cr.elements[1].color = (0.55, 0.7, 1.0, 1)
    e = cr.elements.new(0.58); e.color = (0.5, 0.62, 0.9, 1); bg.inputs[1].default_value = 0.85      # horizonte claro e frio (arcos/janelas da Cripta), topo escuro
    for k, (x, y, z) in enumerate(((2.4, -0.6, 1.1), (-1.0, 2.6, 1.3), (2.8, 1.6, 1.0))):      # tochas: esferas laranja que só aparecem no reflexo
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(x, y, z)); t = bpy.context.object; t.name = f"tocha_vis{k}"
        mm = bpy.data.materials.new(f"tv{k}"); mm.use_nodes = True; nn = mm.node_tree; nn.nodes.clear(); em = nn.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (1.0, 0.5, 0.15, 1); em.inputs[1].default_value = 220
        oo = nn.nodes.new("ShaderNodeOutputMaterial"); nn.links.new(em.outputs[0], oo.inputs[0]); t.data.materials.append(mm); t.visible_camera = False; t.visible_shadow = False
    # piso de referência: lajotas escuras com textura do jogo
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=2.2)
    uv = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for lp in face.loops: lp[uv].uv = ((lp.vert.co.x + 2.2) / 4.4 * 2.2, (lp.vert.co.y + 2.2) / 4.4 * 2.2)
    me = bpy.data.meshes.new("piso"); bm.to_mesh(me); bm.free(); g = bpy.data.objects.new("piso", me); bpy.context.collection.objects.link(g)
    m = bpy.data.materials.new("piso"); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.55
    if os.path.exists(piso_tex):
        t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(piso_tex)
        mix = m.node_tree.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 1; mix.inputs[7].default_value = (0.62, 0.62, 0.68, 1)
        m.node_tree.links.new(t.outputs["Color"], mix.inputs[6]); m.node_tree.links.new(mix.outputs[2], b.inputs["Base Color"])
    else: b.inputs["Base Color"].default_value = (0.08, 0.08, 0.1, 1)
    g.data.materials.append(m)
    for o in partes:                       # água da prévia: ondulação leve (bump) e especular máximo
        for slot in o.material_slots:
            if slot.material.name.startswith("M_Agua"):
                nt3 = slot.material.node_tree; bs = nt3.nodes["Principled BSDF"]; bs.inputs["Specular IOR Level"].default_value = 1.0
                co = nt3.nodes.new("ShaderNodeTexCoord"); nz = nt3.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 14; nz.inputs["Detail"].default_value = 3
                bp = nt3.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.06; bp.inputs["Distance"].default_value = 0.02
                nt3.links.new(co.outputs["Object"], nz.inputs[0]); nt3.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt3.links.new(bp.outputs[0], bs.inputs["Normal"])
    for o in partes:                       # pedras da prévia: textura das lajes, projeção por caixa (o Godot troca por M_PedraEscura)
        for slot in o.material_slots:
            if slot.material.name.startswith("M_PedraEscura") and os.path.exists(piso_tex):
                nt2 = slot.material.node_tree; bsdf = nt2.nodes["Principled BSDF"]
                tx = nt2.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(piso_tex); tx.projection = 'BOX'; tx.projection_blend = 0.2
                co = nt2.nodes.new("ShaderNodeTexCoord"); mp = nt2.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (7, 7, 7)
                nt2.links.new(co.outputs["Object"], mp.inputs[0]); nt2.links.new(mp.outputs[0], tx.inputs[0])
                mx2 = nt2.nodes.new("ShaderNodeMix"); mx2.data_type = 'RGBA'; mx2.blend_type = 'MULTIPLY'; mx2.inputs[0].default_value = 1; mx2.inputs[7].default_value = (0.5, 0.52, 0.62, 1)
                nt2.links.new(tx.outputs["Color"], mx2.inputs[6]); nt2.links.new(mx2.outputs[2], bsdf.inputs["Base Color"])
    # luzes: tocha quente de um lado (reflexo na água), azul frio de preenchimento
    def luz(nome, tipo, e, loc, cor, size=1.0):
        d = bpy.data.lights.new(nome, tipo); d.energy = e; d.color = cor
        if tipo == 'AREA': d.size = size
        o = bpy.data.objects.new(nome, d); o.location = loc; bpy.context.collection.objects.link(o)
        o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
    luz("tocha", 'AREA', 70, (1.7, -0.9, 1.5), (1.0, 0.55, 0.25), 0.5)
    for l in (luz("frio", 'AREA', 120, (-1.8, 1.4, 2.2), (0.45, 0.6, 1.0), 1.4), luz("topo", 'AREA', 60, (0.2, -0.3, 3.0), (0.8, 0.85, 1.0), 1.5)):
        l.visible_glossy = False         # preenchimento não vira lençol branco refletido na água
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam); sc.camera = cam
    return sc, cam

def apontar(cam, loc, alvo=(0, 0, 0.0)):
    cam.location = loc; cam.rotation_euler = (Vector(alvo) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()

def render(sc, cam, loc, alvo, path, res=(720, 500), lente=45):
    sc.render.resolution_x, sc.render.resolution_y = res; cam.data.lens = lente; apontar(cam, loc, alvo)
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)

def wire_override(on):
    if on:
        wm = bpy.data.materials.new("wire"); wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear()
        wf = nt.nodes.new("ShaderNodeWireframe"); wf.inputs[0].default_value = 0.004; em = nt.nodes.new("ShaderNodeEmission"); ot = nt.nodes.new("ShaderNodeOutputMaterial")
        bg = nt.nodes.new("ShaderNodeBsdfDiffuse"); bg.inputs[0].default_value = (0.02, 0.02, 0.02, 1); mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(wf.outputs[0], mx.inputs[0]); nt.links.new(bg.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], ot.inputs[0])
        bpy.context.view_layer.material_override = wm
    else: bpy.context.view_layer.material_override = None

ANG = {"frente": ((0, -1.7, 0.55), 40), "tq": ((1.5, -1.5, 0.95), 40), "lado": ((1.9, 0.2, 0.5), 40), "topo": ((0.001, -0.2, 2.6), 36),
       "close": ((0.55, -0.7, 0.2), 38), "wire": ((0.0, -1.0, 2.5), 40)}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    piso = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "godot", "art", "textures", "T_Cripta_Piso.png")
    for nome in VARS:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        v, partes = construir(nome); exportar(nome, partes)
        tris = sum(len(o.data.polygons) for o in partes); print("exportado poça", nome, tris, "polígonos")
        if not PREV: continue
        os.makedirs(PREV, exist_ok=True)
        sc, cam = cena_previa(partes, os.path.normpath(piso))
        for a, (loc, lente) in ANG.items():
            if os.environ.get("RAPIDO") and a not in ("tq", "close"): continue
            if a == "wire": wire_override(True)
            render(sc, cam, loc, (0, 0, 0), os.path.join(PREV, f"poca_{nome}_{a}.png"), lente=lente)
            if a == "wire": wire_override(False)
