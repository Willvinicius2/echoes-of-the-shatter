"""Estátua encapuzada da Cripta, remodelada com mais detalhe e quebras (referência de estilo: modulos_cripta.py).
Gera SM_Cripta_Estatua.glb em metros, pivô no centro da base, frente voltada para +Y do Blender (-Z do Godot).
  python estatua.py <pasta_saida> [pasta_previas]          (módulo bpy: pip install bpy; ou: blender -b --factory-startup -P estatua.py -- ...)
Materiais: M_Estatua (pedra, textura triplanar no Godot), M_Musgo, M_PedraEscura (vazio do capuz), M_Ouro (filete rúnico)."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None
random.seed(11)
S = 1.25            # escala da figura (igual à estátua antiga: ~3 m com plinto)
PLINTO_H = 0.62
N = 72              # setores por anel

def mat(name, color, metal=0.0, rough=0.85):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    # a cor de vértice multiplica a cor-base (igual ao Godot) para a prévia refletir o resultado
    nt = m.node_tree; ca = nt.nodes.new("ShaderNodeVertexColor"); ca.layer_name = "Color"
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
    mx.inputs[6].default_value = (*color, 1); nt.links.new(ca.outputs["Color"], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    return m

bpy.ops.wm.read_factory_settings(use_empty=True)
M_ESTATUA = mat("M_Estatua", (0.36, 0.34, 0.42), rough=0.9)
M_MUSGO = mat("M_Musgo", (0.20, 0.34, 0.10), rough=1.0)
M_ESCURA = mat("M_PedraEscura", (0.05, 0.05, 0.06))
M_OURO = mat("M_Ouro", (0.72, 0.52, 0.16), metal=0.9, rough=0.4)
MATS = [M_ESTATUA, M_MUSGO, M_ESCURA, M_OURO]
IDX = {"pedra": 0, "musgo": 1, "escura": 2, "ouro": 3}

def lerp(a, b, t): return a + (b - a) * t
def prof(tab, z):
    """Interpola linearmente uma tabela [(z, valor), ...]."""
    if z <= tab[0][0]: return tab[0][1]
    for (z0, v0), (z1, v1) in zip(tab, tab[1:]):
        if z <= z1: return lerp(v0, v1, (z - z0) / (z1 - z0))
    return tab[-1][1]

def new_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    for m in MATS: me.materials.append(m)
    return o

def loft(rings, cap_bottom=True, cap_top=True):
    """rings: lista de anéis (cada um uma lista de Vector de mesmo tamanho), de baixo para cima."""
    bm = bmesh.new(); n = len(rings[0])
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    for a, b in zip(vs, vs[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    if cap_bottom: bm.faces.new(vs[0][::-1])
    if cap_top: bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm

def subdiv(bm, cuts=1):
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])

def fbm(p, f, oct=3):
    v, a = 0.0, 1.0
    for _ in range(oct):
        v += noise.noise(p * f) * a; f *= 2.1; a *= 0.5
    return v

def displace(bm, fn):
    """fn(co, normal) -> deslocamento ao longo da normal."""
    bm.normal_update()
    for v in bm.verts: v.co += v.normal * fn(v.co.copy(), v.normal.copy())

def dist_seg(p, a, b):
    ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length

# ---------- rachaduras (em coordenadas da figura, 0..1.92) ----------
def crack_poly(start, steps, seed):
    r = random.Random(seed); pts = [Vector(start)]
    for _ in range(steps):
        d = Vector((r.uniform(-0.05, 0.05), r.uniform(-0.03, 0.03), -r.uniform(0.05, 0.11)))
        pts.append(pts[-1] + d)
    return pts
CRACKS = [crack_poly((0.18, 0.2, 1.40), 9, 1), crack_poly((-0.25, 0.22, 1.05), 8, 2),
          crack_poly((0.05, 0.36, 0.70), 7, 3), crack_poly((-0.12, -0.30, 1.25), 8, 4)]
def crack_depth(co, w=0.016, d=0.028):
    m = min(dist_seg(co, a, b) for c in CRACKS for a, b in zip(c, c[1:]))
    return -d * max(0.0, 1.0 - m / w) ** 0.8

def stone(co, n, amp=0.005):
    """Aspereza de pedra esculpida + rachaduras."""
    return fbm(co, 9, 2) * amp + fbm(co + Vector((9, 3, 1)), 45, 2) * amp * 0.6 + crack_depth(co)

# ---------- manto (túnica) ----------
A_T = [(0, 0.54), (0.10, 0.51), (0.45, 0.41), (0.68, 0.355), (0.80, 0.33), (1.0, 0.34), (1.12, 0.345), (1.3, 0.345), (1.43, 0.30), (1.53, 0.17)]   # semilargura (x)
B_T = [(0, 0.47), (0.10, 0.44), (0.45, 0.35), (0.68, 0.295), (0.80, 0.27), (1.0, 0.26), (1.12, 0.25), (1.3, 0.225), (1.43, 0.20), (1.53, 0.16)]   # semiprofundidade (y)

def _tri(x):
    """Onda triangular 0..1 (1 em x=0, 0 em x=pi): gera planos retos entre vincos agudos."""
    return abs(((x / math.tau) % 1.0) * 2 - 1)

def _serra(x, q=0.72):
    """Dente de serra assimétrico 0..1: rampa longa e queda íngreme, como pano sobreposto."""
    u = (x / math.tau) % 1.0
    return u / q if u < q else (1 - u) / (1 - q)

def _liso(a, b, x):
    k = max(0.0, min(1.0, (x - a) / (b - a))); return k * k * (3 - 2 * k)

def _dobra(t, z, amp_k=1.0):
    """Fator radial do pano de pedra no ângulo t e altura z: três camadas de vincos em cascata, cinta de barra e rolo do bordo."""
    cima = _liso(0.15, 1.45, z)                                   # 0 embaixo, 1 no peito
    amp = (0.34 * (1 - cima) ** 1.1 + 0.05) * amp_k
    cinta = _liso(0.18, 0.32, z)                                  # a barra do manto (cenefa) não tem dobras
    aperto = 1 - 0.55 * math.exp(-((z - 0.80) / 0.07) ** 2)       # as dobras se juntam no cinto
    pa = 6 * t + 1.4 * z + 0.55 * math.sin(2.3 * z + 2 * t)
    pb = 11 * t - 1.9 * z + 0.6 + 0.35 * math.sin(3.7 * z + t)
    pc = 17 * t + 2.6 * z + 2.0 * math.sin(1.7 * z)
    w = _serra(pa) * 0.66 + _serra(pb, 0.3) * (0.34 + 0.14 * (1 - cima)) + _tri(pc) * 0.14 * (1 - cima)
    peito = math.exp(-((z - 1.22) / 0.16) ** 2) * math.exp(-((t - math.pi / 2) / 0.45) ** 2)   # peito calmo para o medalhão
    r = 1 - amp * cinta * aperto * w * (1 - 0.85 * peito)
    r *= 1 + 0.055 * math.exp(-((z - 0.085) / 0.05) ** 2)         # rolo grosso do bordo
    return r

def _lasca(t):
    """Elevação da barra por pedaços lascados (degraus e cortes inclinados)."""
    n = 19; u = (t % math.tau) / math.tau * n; i = int(u); fr = u - i
    h = abs(math.sin(i * 12.9898 + 4.1) * 43758.5453) % 1.0
    base = (0.0, 0.02, 0.05, 0.085, 0.12)[int(h * 5)]
    h2 = abs(math.sin(i * 78.233 + 1.3) * 12345.6789) % 1.0
    return base + (h2 - 0.5) * 0.07 * fr

def manto():
    zs = [0, 0.012, 0.03, 0.05, 0.075, 0.10, 0.13, 0.17, 0.21] + [0.21 + (i + 1) * 0.0175 for i in range(int((1.55 - 0.21) / 0.0175) + 1)]
    zs = [z for z in zs if z <= 1.55] + [1.55]
    M = 192; rings = []
    for z in zs:
        a, b = prof(A_T, z), prof(B_T, z); ring = []
        for i in range(M):
            t = i / M * math.tau
            c, s = math.cos(t), math.sin(t)
            r = _dobra(t, z)
            if z == 0: r *= 0.90                                  # chanfro na base
            zz = z + _lasca(t) * max(0.0, 1 - z / 0.10)           # barra recortada, de espessura visível
            ring.append(Vector((a * c * r, b * s * r - (0.03 if z > 1.2 else 0), zz)))
        rings.append(ring)
    bm = loft(rings, True, True)
    # pedra: aspereza leve e fendas; os vincos continuam nítidos
    displace(bm, lambda co, n: fbm(co, 14, 2) * 0.0035 + fbm(co + Vector((9, 3, 1)), 60, 1) * 0.0018 + crack_depth(co, 0.012, 0.03))
    # separa as normais nos vincos: o sombreamento liso não borra as arestas
    bm.edges.ensure_lookup_table()
    cortar = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > 0.42]
    bmesh.ops.split_edges(bm, edges=cortar)
    return new_obj("manto", bm)

# ---------- capuz ----------
# Capuz de pedra esculpida: casca facetada (poucos anéis, planos legíveis), boca em arco cavada por booleana
# (borda grossa), rosto sugerido por planos no fundo, drapeado atrás em dobras largas e ponta fraturada em planos.
def _afiar(o, graus=38):
    """Marca como aresta viva toda aresta cujo ângulo entre faces passa do limite (sombreamento por ângulo)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    lim = math.radians(graus)
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim)
    bm.to_mesh(o.data); bm.free()

def _bool(alvo, cortador, op='DIFFERENCE'):
    """Booleana exata (corta o alvo com o cortador) e descarta o cortador."""
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = alvo; alvo.select_set(True)
    m = alvo.modifiers.new("bool", 'BOOLEAN'); m.object = cortador; m.operation = op; m.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier="bool")
    bpy.data.objects.remove(cortador, do_unlink=True)

def _chanfro(o, larg=0.006, graus=32):
    """Bisel fino nas arestas vivas: a luz pega o fio e a forma fica nítida a distância."""
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
    m = o.modifiers.new("bis", 'BEVEL'); m.offset_type = 'OFFSET'; m.width = larg; m.segments = 2
    m.limit_method = 'ANGLE'; m.angle_limit = math.radians(graus)
    bpy.ops.object.modifier_apply(modifier="bis")

def _arco(cx, cz, hw, hh, y, m=12, topo=0.28):
    """Contorno em arco ogival (xz) no plano y: lista de Vector, de baixo para cima pela direita."""
    pts = []
    for k in range(m):
        a = k / m * math.tau - math.pi / 2
        s = math.sin(a)
        x = hw * math.cos(a) * (1 - 0.30 * max(0.0, s) ** 2)
        z = cz + hh * s + (topo * hh * max(0.0, s) ** 6)       # pico do arco no alto
        pts.append(Vector((x + cx, y, z)))
    return pts

def _capuz_casca():
    """Casca do capuz: 24 setores, vincos verticais alternados atrás e nas laterais; planos grandes na frente."""
    chaves = [0.0, 0.06, 0.17, 0.30, 0.45, 0.60, 0.74, 0.86, 1.0]
    rings = []
    for t01 in chaves:
        z = 1.40 + t01 * 0.62
        R = prof([(0, 0.20), (0.17, 0.27), (0.45, 0.255), (0.74, 0.17), (1.0, 0.0)], t01)
        cy = -0.02 - 0.19 * t01 ** 2.2                    # a ponta tomba para trás
        rx, ry = R * 0.97, R * 1.10; ring = []
        for i in range(24):
            t = i / 24 * math.tau
            c, s = math.cos(t), math.sin(t)
            atras = max(0.0, -s)                              # 1 atrás, 0 na frente
            vinco = (1 if i % 2 else -1) * 0.040 * (0.25 + atras) * (1 - t01 * 0.4)
            ring.append(Vector((rx * c * (1 + vinco), cy + ry * s * (1 + vinco), z)))
        rings.append(ring)
    return loft(rings, True, True), (rings, chaves)

def capuz():
    bm, (rings, chaves) = _capuz_casca()
    casca = new_obj("capuz", bm)
    # boca em arco: cortador afunilado (largo na frente, estreito no fundo); a parede vira a borda grossa
    cz = 1.67
    fora = _arco(0, cz, 0.112, 0.175, 0.50); fundo = _arco(0, cz + 0.005, 0.070, 0.135, -0.02)
    cb = loft([fundo, fora], True, True)
    cut = new_obj("cort", cb)
    for p in cut.data.polygons: p.material_index = IDX["escura"]
    _bool(casca, cut)
    # tampa do fundo e planos do rosto (testa, nariz, queixo) bem leves, só planos
    rosto = bmesh.new()
    def prisma(cx, cz_, w, h, d, y0, incl):
        v = bmesh.ops.create_cube(rosto, size=1.0)["verts"]
        for q in v:
            q.co = Vector((cx + q.co.x * w, y0 + q.co.y * d + (q.co.z + 0.5) * incl, cz_ + q.co.z * h))
    prisma(0, cz + 0.095, 0.150, 0.030, 0.050, 0.040, 0.020)            # testa/arco da sobrancelha
    prisma(0, cz + 0.000, 0.026, 0.100, 0.060, 0.020, 0.030)            # nariz (cunha)
    prisma(0, cz - 0.100, 0.075, 0.028, 0.046, 0.030, 0.018)            # queixo
    f = new_obj("rosto", rosto)
    for p in f.data.polygons: p.material_index = IDX["pedra"]
    partes = [casca, f]
    # borda em rolo de tecido ao redor da boca (facetada, 6 lados)
    borda = [Vector((p.x * 1.06, 0.0, cz + (p.z - cz) * 1.045)) for p in _arco(0, cz, 0.112, 0.175, 0.0)]
    for p in borda:
        yc = lambda z: -0.02 - 0.19 * ((z - 1.40) / 0.62) ** 2.2
        t01 = (p.z - 1.40) / 0.62
        R = prof([(0, 0.20), (0.17, 0.27), (0.45, 0.255), (0.74, 0.17), (1.0, 0.0)], t01)
        p.y = yc(p.z) + R * 1.10 * math.sqrt(max(0.0, 1 - (p.x / (R * 0.97)) ** 2)) - 0.012
    laco = borda + [borda[0], borda[1]]
    raios = [0.030 + 0.006 * math.sin(k * 1.7) for k in range(len(laco))]
    rolo = new_obj("rolo", tubo(laco, raios, 6, True))
    partes.append(rolo)
    # costura em crista descendo da ponta até a nuca (prisma de 4 lados, aresta viva)
    cr = []
    for k in range(9):
        t01 = 0.9 - k * 0.1; R = prof([(0, 0.20), (0.17, 0.27), (0.45, 0.255), (0.74, 0.17), (1.0, 0.0)], t01)
        cr.append(Vector((0, -0.02 - 0.19 * t01 ** 2.2 - R * 1.10 + 0.004, 1.40 + t01 * 0.62)))
    partes.append(new_obj("crista", tubo(cr, [0.016 + 0.006 * k / 8 for k in range(9)], 4, True)))
    # drapeado atrás: lâmina grossa com dobras largas descendo pelos ombros
    partes.append(_drapeado())
    # ponta fraturada: planos de corte angulosos (interseção de semiespaços) + lasca remanescente
    o = _juntar(partes, "capuz")
    _fratura(o)
    o = _juntar([o] + _ponta_quebrada() + lascas_capuz(), "capuz")
    _afiar(o, 26)
    return o

def _juntar(objs, nome):
    bpy.ops.object.select_all(action='DESELECT')
    for x in objs: x.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join()
    o = bpy.context.object; o.name = nome; return o

def _drapeado():
    """Capa do capuz caindo atrás nos ombros: poucas dobras largas (planos facetados), barra recortada em degraus."""
    cols = 13; linhas = [0.0, 0.18, 0.42, 0.68, 1.0]
    capa_a = lambda z: prof([(1.02, 0.43), (1.3, 0.40), (1.5, 0.28), (1.7, 0.25)], z) + 0.035
    capa_b = lambda z: prof([(1.02, 0.34), (1.3, 0.27), (1.5, 0.20), (1.7, 0.27)], z) + 0.035
    bm = bmesh.new(); grid = []
    for h in linhas:
        z = 1.62 - h * 0.34
        k = min(1.0, h * 2.6); k = k * k * (3 - 2 * k)          # sai do capuz e assenta sobre a capa
        fila = []
        for j in range(cols):
            u = j / (cols - 1)
            t = math.pi * (1.10 + 0.80 * u)                       # arco atrás, até os ombros
            dobra = 1 - abs((u * 3.0) % 1.0 * 2 - 1)                        # pregas em zigue-zague (planos nítidos)
            ext = 0.025 + 0.10 * dobra * (0.15 + h)
            a = lerp(0.200, capa_a(z) + ext, k); b = lerp(0.230, capa_b(z) + ext, k)
            zz = z - (0.07 * ((j // 2) % 2) + 0.05 * math.sin(u * 5.0 + 1.0)) * h * h     # barra recortada
            fila.append(bm.verts.new(Vector((a * math.cos(t), b * math.sin(t) - 0.03, zz))))
        grid.append(fila)
    for r0, r1 in zip(grid, grid[1:]):
        for j in range(cols - 1):
            bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.045)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj("drapeado", bm)

def _lasca_pl(loc, r, seed, esc=(1.0, 0.7, 0.5)):
    """Lasca de pedra: casco convexo de pontos aleatórios (poucas faces planas, arestas vivas)."""
    rn = random.Random(seed); bm = bmesh.new()
    for _ in range(9):
        v = Vector((rn.uniform(-1, 1), rn.uniform(-1, 1), rn.uniform(-1, 1)))
        bm.verts.new(Vector((v.x * esc[0], v.y * esc[1], v.z * esc[2])) * r)
    h = bmesh.ops.convex_hull(bm, input=bm.verts[:])
    soltos = [v for v in bm.verts if not v.link_faces]                 # pontos que ficaram dentro do casco
    bmesh.ops.delete(bm, geom=soltos, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = new_obj("lasca", bm); o.location = loc
    o.rotation_euler = (rn.random() * 3, rn.random() * 3, rn.random() * 6)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o

def _fratura(o):
    """Corta a ponta por vários planos inclinados (fratura facetada) e deixa uma lasca pontuda no corte."""
    planos = [(Vector((0.0, -0.10, 1.87)), Vector((0.22, -0.90, 1)).normalized()),
              (Vector((0.0, -0.16, 1.955)), Vector((-0.85, -0.20, 1)).normalized()),
              (Vector((0.02, -0.10, 1.935)), Vector((0.70, 0.55, 1)).normalized())]
    bm = bmesh.new(); bm.from_mesh(o.data)
    for pc, pn in planos:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=pc, plane_no=pn, clear_outer=True)
        arestas = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        novo = bmesh.ops.holes_fill(bm, edges=arestas, sides=64)
        for f in novo["faces"]: f.material_index = IDX["pedra"]
    bm.to_mesh(o.data); bm.free()

def _ponta_quebrada():
    """Dentes de pedra que sobraram no corte: duas lascas pontudas fincadas e inclinadas."""
    dentes = []
    for k, (loc, esc, seed) in enumerate((((0.04, -0.12, 1.90), (0.06, 0.05, 0.085), 21), ((-0.05, -0.16, 1.885), (0.045, 0.045, 0.065), 22))):
        d = _lasca_pl(loc, 1.0, seed, esc)
        dentes.append(d)
    return dentes

def lascas_capuz():
    """Estilhaços soltos no entorno do capuz (ombros e nuca)."""
    return [_lasca_pl(Vector(l), r, sd, e) for l, r, sd, e in (
        ((0.27, 0.02, 1.57), 0.050, 31, (1.3, 0.9, 0.5)), ((-0.30, -0.08, 1.53), 0.040, 32, (1.2, 0.8, 0.55)),
        ((0.16, -0.30, 1.50), 0.035, 33, (1.0, 1.0, 0.5)), ((-0.12, 0.24, 1.545), 0.030, 34, (1.1, 0.8, 0.5)),
        ((0.33, -0.12, 1.50), 0.028, 35, (1.2, 0.8, 0.5)))]

def gola():
    """Gola de pedra: colar facetado nos ombros, com dobras de tecido em degraus."""
    rings = []
    for h, e in ((0.0, 1.0), (0.035, 1.06), (0.07, 1.02), (0.11, 0.86)):
        ring = []
        for i in range(24):
            t = i / 24 * math.tau
            v = 1 + 0.07 * (1 if i % 2 else -1) * (1 - h * 5)
            ring.append(Vector((0.262 * math.cos(t) * e * v, 0.222 * math.sin(t) * e * v - 0.01, 1.43 + h)))
        rings.append(ring)
    o = new_obj("gola", loft(rings, True, True))
    _afiar(o, 30)
    return o


# ---------- braços ----------
def bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return p0 * u ** 3 + p1 * 3 * u * u * t + p2 * 3 * u * t * t + p3 * t ** 3

def tubo(path, radii, sides=18, cap_end=True):
    """Tubo ao longo de um caminho (lista de Vector) com raios."""
    rings = []; up = Vector((0, 0, 1))
    for i, (p, r) in enumerate(zip(path, radii)):
        tg = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        side = tg.cross(up if abs(tg.z) < 0.9 else Vector((1, 0, 0))).normalized(); fw = side.cross(tg).normalized()
        rings.append([p + (side * math.cos(k / sides * math.tau) + fw * math.sin(k / sides * math.tau)) * r
                      for k in range(sides)])
    bm = loft(rings, True, cap_end)
    return bm

# --- helpers locais dos braços/mãos (arestas vivas, sem subdivisão suave) ---
M_FRAT = None
def mat_fratura():
    """Material da pedra recém-quebrada (mais clara que a pedra antiga); criado sob demanda."""
    global M_FRAT
    if M_FRAT is None: M_FRAT = mat("M_Fratura", (0.80, 0.78, 0.72), rough=0.95)
    return M_FRAT

def _onda(x):
    """Onda triangular 0..1 (1 em x=0, 0 em x=pi): elevada a uma potência vira sulco estreito de prega."""
    return abs(((x / math.pi) % 2.0) - 1.0)

def _base_caminho(pts, i):
    """Base (lado, frente, tangente) do tubo no ponto i, estável para qualquer direção."""
    tg = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
    ref = Vector((0, 0, 1)) if abs(tg.z) < 0.9 else Vector((1, 0, 0))
    side = tg.cross(ref).normalized(); fw = side.cross(tg).normalized()
    return side, fw, tg

def _manga(pts, ents, lados=30, dobras=5, fase=0.0):
    """Anéis de uma manga larga de pedra. ents: lista (índice no caminho, raio, profundidade das pregas); índices
    repetidos criam degraus de aresta viva (bainha). Pregas = sulcos fundos e estreitos que giram ao longo do braço."""
    rings = []
    for (i, r, d) in ents:
        side, fw, tg = _base_caminho(pts, i); ring = []
        for k in range(lados):
            t = k / lados * math.tau
            g = (1 - _onda(dobras * t + fase + i * 0.11)) ** 3            # 1 no fundo do sulco
            g2 = (1 - _onda(2 * dobras * t + 1.7 - i * 0.07)) ** 4        # sulcos menores entre os grandes
            rr = r * (1 - d * g - d * 0.35 * g2)
            ring.append(pts[i] + (side * math.cos(t) + fw * math.sin(t)) * rr)
        rings.append(ring)
    return rings

def _unir(dst, src, M=None):
    """Copia a malha src (bmesh) para dst (com matriz opcional), mantendo o índice de material."""
    mp = {}
    for v in src.verts: mp[v] = dst.verts.new(M @ v.co if M is not None else v.co)
    for f in src.faces:
        nf = dst.faces.new([mp[v] for v in f.verts]); nf.material_index = f.material_index
    src.free()

def _quebrar(bm, centro, normal, dentes=0.03, seed=5):
    """Corta por um plano (remove o lado +normal) e fecha com facetas angulares de pedra clara (material 4)."""
    r = random.Random(seed); normal = normal.normalized()
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=centro, plane_no=normal, clear_outer=True)
    vs = [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMVert)]
    if len(vs) < 3: return
    c = sum((v.co for v in vs), Vector()) / len(vs)
    ref = (vs[0].co - c).normalized(); perp = normal.cross(ref)
    vs.sort(key=lambda v: math.atan2((v.co - c).dot(perp), (v.co - c).dot(ref)))
    k = 0                                    # dentes: grupos de 2 a 3 vértices sobem ou descem juntos (lascas pontiagudas)
    while k < len(vs):
        n = r.choice((2, 3)); h = r.uniform(-dentes, dentes * 0.6)
        for v in vs[k:k + n]: v.co += normal * (h * r.uniform(0.7, 1.0))
        k += n
    topo = bm.verts.new(c + normal * (-dentes * 0.4) + perp * r.uniform(-0.01, 0.01))
    novos = []
    for a, b in zip(vs, vs[1:] + vs[:1]):
        try: novos.append(bm.faces.new((a, b, topo)))
        except ValueError: pass
    for f in novos: f.material_index = 4
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:                       # beirada lascada: faixa de faces coladas à fratura também fica clara
        if f.material_index == 0 and all((v.co - c).dot(normal) > -0.025 for v in f.verts): f.material_index = 4

def _bainha(rc):
    """Perfil da bainha grossa do punho: degrau para fora, topo arredondado, volta para dentro e boca escura."""
    return [(rc * 0.99, 1), (rc * 1.15, 1), (rc * 1.19, 1), (rc * 1.19, 1), (rc * 1.15, 1), (rc * 1.07, 1), (rc * 0.70, 1)]

def _boca_escura(bm, cx, tg, raio):
    """Interior da boca da manga em pedra escura."""
    for f in bm.faces:
        c = f.calc_center_median(); d = c - cx; ax = d.dot(tg)
        if ax < -0.002 and (d - tg * ax).length < raio and ax > -0.07: f.material_index = IDX["escura"]

def braco(sx, quebrado):
    """Manga larga de pedra com pregas fundas e punho de bainha grossa. O braço quebrado termina numa fratura facetada."""
    p0 = Vector((sx * 0.30, -0.01, 1.42)); p1 = Vector((sx * 0.43, 0.06, 1.16)); p2 = Vector((sx * 0.40, 0.34, 1.00)); p3 = Vector((sx * 0.07, 0.43, 1.00))
    n = 46; pts = [bezier(p0, p1, p2, p3, i / (n - 1)) for i in range(n)]
    ic = n - 5; ents = []
    for i in range(ic):
        t = i / (n - 1)
        r = prof([(0, 0.105), (0.30, 0.115), (0.55, 0.108), (0.89, 0.135)], t)
        d = prof([(0, 0.05), (0.30, 0.18), (0.6, 0.24), (0.89, 0.26)], t)
        ents.append((i, r, d))
    rc = 0.125
    pr = _bainha(rc)
    ents += [(ic, pr[0][0], 0.0), (ic, pr[1][0], 0.0), (ic + 1, pr[2][0], 0.0), (ic + 3, pr[3][0], 0.0), (n - 2, pr[4][0], 0.0), (n - 1, pr[5][0], 0.0), (n - 1, pr[6][0], 0.0)]
    rings = _manga(pts, ents, 30, 5, 0.3 * sx)
    tg = _base_caminho(pts, n - 1)[2]; cx = pts[n - 1]
    rings.append([cx - tg * 0.055 + (q - cx) * 0.8 for q in rings[-1]])   # fundo da boca, recuado
    bm = loft(rings, True, True)
    _boca_escura(bm, cx, tg, rc * 0.74)
    if quebrado:
        i = int(n * 0.52); lado, fw, t0 = _base_caminho(pts, i)
        _quebrar(bm, pts[i], t0 + lado * 0.6 + fw * 0.3, 0.035, 7)   # corte diagonal no antebraço; o resto é descartado
    o = new_obj("braco", bm); o.data.materials.append(mat_fratura())
    return o, pts

def _seg(bm, a, b, wa, wb, ta, tb):
    """Caixa afilada entre dois pontos (meia-largura wa/wb, meia-espessura ta/tb) com arestas biseladas."""
    dr = (b - a).normalized(); ref = Vector((0, 0, 1)) if abs(dr.z) < 0.9 else Vector((1, 0, 0))
    lado = dr.cross(ref).normalized(); cima = lado.cross(dr).normalized()
    a = a - dr * 0.0035; b = b + dr * 0.0035
    vs = []
    for (p, w, t) in ((a, wa, ta), (b, wb, tb)):
        for sw, st in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            vs.append(bm.verts.new(p + lado * (w * sw) + cima * (t * st)))
    novos = [bm.faces.new([vs[k] for k in f]) for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))]
    bmesh.ops.recalc_face_normals(bm, faces=novos)
    bmesh.ops.bevel(bm, geom=list({e for f in novos for e in f.edges}), offset=0.0022, segments=1, affect='EDGES')

def dedos(bm, sx, curl, esc=1.0):
    """Quatro dedos de três falanges e o polegar de duas, em caixas afiladas biseladas.
    Sistema local da mão: pulso na origem, +Y = dedos, os dedos fecham para -Z (palma), o polegar fica em +X*sx."""
    larg = (0.0128, 0.0135, 0.0125, 0.0108); comp = (1.0, 1.12, 1.0, 0.78)
    for j, x in enumerate((0.036, 0.012, -0.012, -0.036)):
        p = Vector((x * sx, 0.090 * esc, 0.0)); w0 = larg[j] * esc; ang = 0.0
        abre = 0.045 * (j - 1.5) * sx                     # leve leque entre os dedos
        for f, (L, c) in enumerate(((0.040, 0.85), (0.030, 1.15), (0.023, 0.95))):
            ang += curl * c
            q = p + Vector((abre * math.cos(ang), math.cos(ang), -math.sin(ang))).normalized() * (L * comp[j] * esc)
            _seg(bm, p, q, w0, w0 * 0.88, 0.0115 * esc * (1 - 0.12 * f), 0.0100 * esc * (1 - 0.12 * f))
            p = q; w0 *= 0.88
    p = Vector((0.046 * sx, 0.020 * esc, -0.006 * esc)); d = Vector((0.55 * sx, 0.80, -0.18)).normalized(); w0 = 0.0175 * esc
    for f, L in enumerate((0.036, 0.030)):
        d = Vector((d.x - 0.35 * sx * f * curl, d.y, d.z - 0.45 * f * curl)).normalized()
        q = p + d * (L * esc)
        _seg(bm, p, q, w0, w0 * 0.86, 0.0135 * esc, 0.0120 * esc)
        p = q; w0 *= 0.86

def _mao_bm(sx, curl=0.55, esc=1.3):
    """Mão completa em bmesh: pulso, palma afilada, cunha do polegar, nós dos dedos, dedos e polegar."""
    bm = bmesh.new()
    _seg(bm, Vector((0, -0.060 * esc, 0)), Vector((0, 0, 0)), 0.034 * esc, 0.040 * esc, 0.0165 * esc, 0.018 * esc)
    _seg(bm, Vector((0, -0.004, 0)), Vector((0, 0.092 * esc, 0)), 0.040 * esc, 0.050 * esc, 0.018 * esc, 0.0155 * esc)
    _seg(bm, Vector((0.030 * sx, 0.008 * esc, -0.006)), Vector((0.046 * sx, 0.052 * esc, -0.010)), 0.016 * esc, 0.014 * esc, 0.0115 * esc, 0.0100 * esc)
    for x in (0.036, 0.012, -0.012, -0.036):
        _seg(bm, Vector((x * sx, 0.074 * esc, 0.006 * esc)), Vector((x * sx, 0.092 * esc, 0.006 * esc)), 0.0105 * esc, 0.0110 * esc, 0.0075 * esc, 0.0070 * esc)
    dedos(bm, sx, curl, esc)
    return bm

def mao(sx=1, curl=0.55, esc=1.3, nome="mao"):
    """Mão de pedra com dedos de verdade (falanges e polegar); ver _mao_bm para o sistema de coordenadas."""
    return new_obj(nome, _mao_bm(sx, curl, esc))

def _base_mao(tg, palma_cima=True):
    """Matriz que leva o sistema local da mão ao mundo: +Y local = tg, palma para cima (ou para baixo)."""
    from mathutils import Matrix
    ey = tg.normalized(); ez = Vector((0, 0, -1 if palma_cima else 1))
    ez = (ez - ey * ez.dot(ey)).normalized(); ex = ey.cross(ez).normalized()
    return Matrix((ex, ey, ez)).transposed()

def mao_quebrada():
    """Mão caída com um toco de manga: bainha no punho, dedos curvos e fratura facetada do lado do cotovelo.
    Sistema local igual ao da mão (pulso em y=0), toco em y negativo."""
    bm = bmesh.new()
    pts = [Vector((0, -0.27 + 0.27 * i / 19, 0)) for i in range(20)]
    ents = [(i, 0.135, 0.26) for i in range(15)]
    pr = _bainha(0.125)
    ents += [(15, pr[0][0], 0.0), (15, pr[1][0], 0.0), (16, pr[2][0], 0.0), (17, pr[3][0], 0.0), (18, pr[4][0], 0.0), (19, pr[5][0], 0.0), (19, pr[6][0], 0.0)]
    rings = _manga(pts, ents, 30, 5, 0.9)
    cx = pts[-1]; tg = Vector((0, 1, 0))
    rings.append([cx - tg * 0.055 + (q - cx) * 0.8 for q in rings[-1]])
    m = loft(rings, True, True); _boca_escura(m, cx, tg, 0.093)
    _quebrar(m, pts[0] + Vector((0, 0.04, 0)), Vector((0.35, -1, 0.5)), 0.03, 3)   # fratura voltada para o cotovelo
    _unir(bm, m)
    from mathutils import Matrix
    _unir(bm, _mao_bm(-1, 0.75, 1.9), Matrix.Translation((0, 0, 0.075)))   # a mão escorregou da manga e repousa mais baixo
    return bm

# ---------- fragmentos e entulho ----------
# Pedra facetada: sólidos convexos (casca convexa de pontos), bisel curto e uma face = um plano (vértices separados por face,
# sombreamento chapado). Nada de bolhas: arestas vivas e fraturas em planos, como nos blocos da folha c05.
def _pl_hull(pts):
    bm = bmesh.new(); vs = [bm.verts.new(p) for p in pts]
    r = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    morto = list({g for g in r["geom_interior"] + r["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if morto: bmesh.ops.delete(bm, geom=morto, context='VERTS')
    return bm

def _pl_acabar(bm, bev, limite=0.14):
    """Funde faces quase coplanares, chanfra as arestas, triangula e separa cada face (facetas nítidas, sem faces internas)."""
    bmesh.ops.dissolve_limit(bm, angle_limit=limite, verts=bm.verts[:], edges=bm.edges[:])
    if bev > 0: bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev, segments=1, affect='EDGES', clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.split_edges(bm, edges=bm.edges[:])
    return bm

def _pl_obj(nome, bm, mat=0, loc=(0, 0, 0)):
    for f in bm.faces: f.material_index = mat
    o = new_obj(nome, bm); o.location = loc; return o

def _pl_cubo(tam):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * tam[0], v.co.y * tam[1], v.co.z * tam[2]))
    return bm

def _pl_cortar(bm, co, no, remove_fora=True):
    """Corta o sólido convexo por um plano e fecha o buraco (fratura plana)."""
    g = bm.verts[:] + bm.edges[:] + bm.faces[:]
    r = bmesh.ops.bisect_plane(bm, geom=g, plane_co=co, plane_no=no, clear_outer=remove_fora, clear_inner=not remove_fora)
    cut = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if cut: bmesh.ops.holes_fill(bm, edges=cut, sides=32)

def _pl_mover(bm, c, euler):
    from mathutils import Matrix, Euler
    M = Matrix.Translation(c) @ Euler(euler).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])

def _pl_bloco(c, tam, rng, chips=(), bev=0.02, jit=0.007, euler=(0, 0, 0), fenda=None):
    """Bloco de pedra: cubo com cantos fraturados em planos (chips = [(sx, sy)] nos cantos de cima), vértices levemente tortos.
    fenda=(normal) parte o bloco em duas metades afastadas (rachadura que atravessa o bloco). Devolve lista de bmesh."""
    planos = [(Vector((sx * rng.uniform(0.3, 1.0), sy * rng.uniform(0.3, 1.0), rng.uniform(0.5, 1.3))).normalized(),
               min(rng.uniform(0.04, 0.10), 0.35 * min(tam))) for sx, sy in chips]
    jits = [Vector((rng.uniform(-jit, jit), rng.uniform(-jit, jit), rng.uniform(-jit, jit))) for _ in range(64)]
    def um(lado):
        bm = _pl_cubo(tam)
        if fenda is not None:
            _pl_cortar(bm, Vector((0, 0, 0)), Vector(fenda).normalized(), remove_fora=(lado < 0))
        for (sx, sy), (n, d) in zip(chips, planos):
            _pl_cortar(bm, Vector((sx * tam[0] / 2, sy * tam[1] / 2, tam[2] / 2)) - n * d, n)
        for k, v in enumerate(bm.verts): v.co += jits[k % 64]
        _pl_acabar(bm, bev, 0.035)
        if fenda is not None:
            n = Vector(fenda).normalized()
            for v in bm.verts: v.co += n * (0.007 * -lado)
        _pl_mover(bm, c, euler)
        return bm
    return [um(1), um(-1)] if fenda is not None else [um(1)]

def _pl_rocha(raio, esc, rng, rot, achatar=0.5):
    """Pedra angulosa: casca convexa de 10-14 pontos irregulares, base achatada, bisel curto."""
    pts = []; zmin = -raio * esc[2] * achatar
    for _ in range(rng.randint(10, 14)):
        d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)))
        if d.length < 1e-3: continue
        d.normalize(); p = Vector((d.x * esc[0], d.y * esc[1], d.z * esc[2])) * raio * rng.uniform(0.62, 1.0)
        p.z = max(p.z, zmin); pts.append(p)
    bm = _pl_hull(pts); _pl_mover(bm, Vector(), rot)
    zb = min(v.co.z for v in bm.verts)
    for v in bm.verts: v.co.z += -zb - 0.012          # encosta no chão, afundando um pouco
    return _pl_acabar(bm, raio * 0.05, 0.2)

def pedaco(nome, loc, raio, esc=(1, 1, 1), rot=(0, 0, 0), mat=0):
    """Pedra caída angulosa; loc é o ponto de contato com a superfície."""
    import zlib
    rng = random.Random(zlib.crc32(nome.encode()) + int(raio * 1000))
    return _pl_obj(nome, _pl_rocha(raio, esc, rng, rot), mat, loc)

def _pl_fila(rng, a, b, alvo):
    """Divide [a, b] em segmentos de larguras irregulares: lista de (centro, largura)."""
    L = b - a; n = max(1, round(L / alvo)); w = [rng.uniform(0.8, 1.25) for _ in range(n)]; s = sum(w)
    out = []; x = a
    for k in range(n):
        seg = L * w[k] / s; out.append((x + seg / 2, seg)); x += seg
    return out

def _pl_tira(x0, z0, x1, z1, y, larg, esp):
    """Tira reta no plano XZ (face frontal), de (x0,z0) a (x1,z1), centrada em y: filete de ouro, rachadura ou traço de runa."""
    from mathutils import Matrix
    L = math.hypot(x1 - x0, z1 - z0) + larg * 0.6
    bm = _pl_cubo((L, esp, larg))
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(-math.atan2(z1 - z0, x1 - x0), 4, 'Y'), verts=bm.verts[:])
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(((x0 + x1) / 2, y, (z0 + z1) / 2))), verts=bm.verts[:])
    return _pl_acabar(bm, min(larg, esp) * 0.2, 0.05)

_RUNAS = [[(0, 0, 0, 1), (0, 0.5, 0.45, 0.2), (0, 0.5, -0.45, 0.2)],
          [(-0.4, 0, 0.4, 0), (0, 0, 0, 1), (-0.4, 1, 0, 0.5)],
          [(-0.4, 0, 0.4, 1), (0.4, 0, -0.4, 1)],
          [(-0.4, 0.5, 0.4, 0.5), (0, 0, 0, 1), (-0.4, 1, 0.4, 1)],
          [(-0.35, 0, 0, 0.55), (0.35, 0, 0, 0.55), (0, 0.55, 0, 1)]]

def plinto():
    """Plinto de 3 degraus de blocos individuais com juntas, cantos fraturados, rachaduras, filete e losango de ouro e runas."""
    from mathutils import Matrix
    rng = random.Random(23); objs = []; JUNTA = 0.016
    def blocos(nome, lado, i, xy, tam2, hx, hy, z0, z1, afunda, incl, chip, fendas, baixos):
        fundo = z0 - afunda - rng.uniform(0, afunda * 0.5)
        topo = z1 + rng.uniform(-0.012, 0.012)
        if baixos and (lado, i) in baixos: topo = z0 + baixos[(lado, i)]
        tam = (tam2[0], tam2[1], topo - fundo)
        chips = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                externo = abs(xy[0] + sx * tam[0] / 2) > hx - 0.03 and abs(xy[1] + sy * tam[1] / 2) > hy - 0.03
                if rng.random() < (0.7 if externo else chip * 0.7): chips.append((sx, sy))
        eul = (rng.uniform(-incl, incl), rng.uniform(-incl, incl), rng.uniform(-0.02, 0.02) if afunda > 0.02 else rng.uniform(-0.006, 0.006))
        fenda = None
        if (lado, i) in fendas: fenda = (1.0, 0.25, 0.0) if lado in "ft" else (0.25, 1.0, 0.0)
        for k, bm in enumerate(_pl_bloco(Vector((xy[0], xy[1], (topo + fundo) / 2)), tam, rng, chips, euler=eul, fenda=fenda)):
            objs.append(_pl_obj(f"{nome}_{lado}{i}_{k}", bm))
        if fenda is None and lado in "fd" and rng.random() < 0.6 and tam[2] > 0.15:     # rachadura em zigue-zague atravessando o bloco
            x = rng.uniform(-0.3, 0.3) * tam[0 if lado == "f" else 1]; z = topo - 0.01; pts = [(x, z)]
            for _ in range(rng.randint(6, 9)): x += rng.uniform(-0.018, 0.018); z -= rng.uniform(0.03, 0.05); pts.append((x, max(z, fundo + 0.02)))
            for (xa, za), (xb, zb) in zip(pts, pts[1:]):
                if lado == "f": bm = _pl_tira(xy[0] + xa, za, xy[0] + xb, zb, xy[1] + tam[1] / 2 + 0.002, 0.009, 0.005)
                else:
                    bm = _pl_tira(xa, za, xb, zb, 0, 0.009, 0.005)
                    bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.pi / 2, 4, 'Z'), verts=bm.verts[:])
                    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector((xy[0] + tam[0] / 2 + 0.002, xy[1], 0))), verts=bm.verts[:])
                objs.append(_pl_obj(f"{nome}_rach", bm, IDX["escura"]))
    def anel(nome, hx, hy, esp, z0, z1, afunda, incl, chip, alvo, fendas=(), baixos=None):
        objs.append(_pl_obj(nome + "_nucleo", _pl_cubo((2 * (hx - esp * 0.55), 2 * (hy - esp * 0.55), z1 - z0 - 0.012)), IDX["escura"],
                            (0, 0, (z0 + z1) / 2 - 0.006)))
        for lado, sg in (("f", 1), ("t", -1)):
            for i, (xc, w) in enumerate(_pl_fila(rng, -hx, hx, alvo)):
                blocos(nome, lado, i, (xc, sg * (hy - esp / 2)), (w - JUNTA, esp - 0.004), hx, hy, z0, z1, afunda, incl, chip, fendas, baixos)
        for lado, sg in (("d", 1), ("e", -1)):
            for i, (yc, w) in enumerate(_pl_fila(rng, -hy + esp + JUNTA, hy - esp - JUNTA, alvo)):
                blocos(nome, lado, i, (sg * (hx - esp / 2), yc), (esp - 0.004, w - JUNTA), hx, hy, z0, z1, afunda, incl, chip, fendas, baixos)
    # degrau 1: afundado e irregular no chão (um bloco caiu atrás, outro está partido); degrau 2: bloco partido na frente
    anel("deg1", 0.93, 0.83, 0.30, 0.0, 0.22, 0.07, 0.035, 0.38, 0.95, fendas={("d", 1)}, baixos={("t", 0): 0.10})
    anel("deg2", 0.82, 0.74, 0.26, 0.22, 0.42, 0.005, 0.008, 0.30, 0.85, fendas={("f", 1)})
    anel("deg3", 0.71, 0.64, 0.24, 0.42, 0.54, 0.005, 0.004, 0.18, 0.70)
    # tampo em lajes (3 x 2), levemente salientes, com cantos lascados
    objs.append(_pl_obj("tampo_nucleo", _pl_cubo((1.40, 1.26, 0.10)), IDX["escura"], (0, 0, 0.545)))
    for j, (yc, d) in enumerate(_pl_fila(rng, -0.69, 0.69, 1.4)):
        for i, (xc, w) in enumerate(_pl_fila(rng, -0.76, 0.76, 0.78)):
            tam = (w - JUNTA, d - JUNTA, 0.085); ch = []
            for sx in (-1, 1):
                for sy in (-1, 1):
                    externo = abs(xc + sx * tam[0] / 2) > 0.74 and abs(yc + sy * tam[1] / 2) > 0.66
                    if rng.random() < (0.8 if externo else 0.15): ch.append((sx, sy))
            for k, bm in enumerate(_pl_bloco(Vector((xc, yc, 0.577 + rng.uniform(-0.003, 0.003))), tam, rng, ch, bev=0.01, euler=(0, 0, rng.uniform(-0.006, 0.006)))):
                objs.append(_pl_obj(f"tampo_{j}{i}_{k}", bm))
    # ouro: filete e losango na frente do degrau 2, filete no tampo; runas gravadas no degrau 3
    ouro = []; Y = 0.74 + 0.007; Z = 0.32
    for sg in (-1, 1):
        ouro.append(_pl_tira(sg * 0.24, Z, sg * 0.62, Z, Y, 0.026, 0.014))
        ouro.append(_pl_tira(sg * 0.62, Z - 0.07, sg * 0.62, Z + 0.07, Y, 0.026, 0.014))
    ring = [(-0.21, 0), (0, 0.088), (0.21, 0), (0, -0.088)]
    for (xa, za), (xb, zb) in zip(ring, ring[1:] + ring[:1]): ouro.append(_pl_tira(xa, Z + za, xb, Z + zb, Y, 0.02, 0.014))
    pts = [Vector((px, py, Z + pz)) for px, pz in ((-0.09, 0), (0, 0.04), (0.09, 0), (0, -0.04)) for py in (0.74 + 0.002, 0.74 + 0.012)]
    ouro.append(_pl_acabar(_pl_hull(pts), 0.003, 0.05))
    ouro.append(_pl_tira(-0.55, 0.585, 0.55, 0.585, 0.69 + 0.006, 0.012, 0.012))
    for k, bm in enumerate(ouro): objs.append(_pl_obj(f"ouro{k}", bm, IDX["ouro"]))
    for g in range(5):
        gx = (g - 2) * 0.17
        for k, (xa, za, xb, zb) in enumerate(_RUNAS[g]):
            bm = _pl_tira(gx + xa * 0.05, 0.445 + za * 0.07, gx + xb * 0.05, 0.445 + zb * 0.07, 0.64 + 0.003, 0.011, 0.007)
            objs.append(_pl_obj(f"runa{g}{k}", bm, IDX["escura"]))
    return objs

def _pl_entulho():
    """Entulho angular em volta do plinto: pedras grandes, monte no canto frontal direito, cascalho e lascas nos degraus."""
    rng = random.Random(41); out = []
    def el(a, off): return Vector((math.cos(a) * (0.93 + off), math.sin(a) * (0.83 + off), 0))
    for i in range(5):
        s = rng.uniform(0.14, 0.26); p = el(rng.uniform(0, math.tau), rng.uniform(0.04, 0.26) + s * 0.9)
        out.append(pedaco(f"e{i}", p, s, (rng.uniform(1.0, 1.5), rng.uniform(0.9, 1.3), rng.uniform(0.6, 0.9)), (rng.uniform(-.2, .2), rng.uniform(-.2, .2), rng.uniform(0, 6.28))))
    base = Vector((1.0, 0.92, 0))                              # onde o bloco da base quebrou: monte de pedras
    for i, (dx, dy, s, dz) in enumerate(((0, 0, 0.20, 0), (0.22, -0.06, 0.14, 0), (0.04, 0.12, 0.12, 0.14))):
        out.append(pedaco(f"m{i}", base + Vector((dx, dy, dz)), s, (1.3, 1.0, 0.8), (0.15 * i, 0.1, i * 1.7)))
    for i in range(5):
        s = rng.uniform(0.05, 0.09); p = el(rng.uniform(0, math.tau), rng.uniform(0.02, 0.4))
        out.append(pedaco(f"c{i}", p, s, (1.3, 1.0, 0.7), (rng.uniform(-.3, .3), rng.uniform(-.3, .3), rng.uniform(0, 6.28))))
    for i in range(4):                                           # lascas caídas sobre os degraus (laje fina e pontuda)
        hx, hy, z = ((0.875, 0.785, 0.22), (0.765, 0.69, 0.42))[i % 2]
        if rng.random() < 0.5: p = Vector((rng.choice((-1, 1)) * hx, rng.uniform(-hy, hy), z))
        else: p = Vector((rng.uniform(-hx, hx), rng.choice((-1, 1)) * hy, z))
        out.append(pedaco(f"l{i}", p + Vector((0, 0, -0.005)), rng.uniform(0.03, 0.05), (1.7, 1.0, 0.35), (0, 0, rng.uniform(0, 6.28))))
    return out


def tubo_fechado(pts, raio, sides=10):
    bm = tubo(pts, [raio] * len(pts), sides, cap_end=True); return bm

def _afiar_bm(bm, ang=0.42):
    """Separa as normais nas arestas vivas (sombreamento liso só dentro de cada plano)."""
    bm.edges.ensure_lookup_table()
    bmesh.ops.split_edges(bm, edges=[e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > ang])

def _sup(t, z):
    """Ponto (x, y) da superfície do manto no ângulo t e altura z (sem ruído de pedra)."""
    r = _dobra(t, z)
    return prof(A_T, z) * math.cos(t) * r, prof(B_T, z) * math.sin(t) * r - (0.03 if z > 1.2 else 0)

def _capa_r(t, zc):
    """Semieixos da capa (já com a dobra, sem y deslocado) no ângulo t e altura nominal zc: devolve (x, y, r)."""
    h = max(0.0, min(1.0, (zc - 1.0) / 0.5))
    a = prof(A_T, zc) + 0.05 + 0.05 * (1 - h) ** 2; b = prof(B_T, zc) + 0.05 + 0.04 * (1 - h) ** 2
    calmo = 1 - 0.8 * math.exp(-((t - math.pi / 2) / 0.42) ** 2)                      # frente calma para o medalhão
    f = 0.075 * (1 - h) ** 0.8 * (0.65 * _tri(4 * t + 0.9 + 2 * h) + 0.35 * _tri(9 * t - 1.5 * h)) * calmo + 0.012
    return a * math.cos(t), b * math.sin(t) - 0.03 * _liso(1.1, 1.25, zc), 1 - f

def _capa():
    """Capa curta sobre os ombros: bordo grosso em dentes recortados, dobras largas e vincos agudos."""
    M = 144; rings = []
    lips = [(0.0, 0.93), (0.006, 1.03), (0.045, 1.05), (0.075, 1.02)]          # espessura do bordo
    zs_main = [1.095 + j * 0.0275 for j in range(16)]                          # até ~1.51
    for k in range(len(lips) + len(zs_main)):
        ring = []
        for i in range(M):
            t = i / M * math.tau
            lift = 0.10 * _tri(7 * t + 0.35) ** 0.7 + 0.025 * _tri(19 * t)       # dentes pendentes recortados
            if k < len(lips):
                du, rs = lips[k]; z = 1.0 - lift + du; zc = 1.0 + du
            else:
                z = zs_main[k - len(lips)]; zc = z; rs = 1.0
            x, y, r = _capa_r(t, zc); r *= rs
            ring.append(Vector((x * r, y * r, z)))
        rings.append(ring)
    bm = loft(rings, True, True)
    displace(bm, lambda co, n: fbm(co, 14, 2) * 0.003 + fbm(co + Vector((4, 1, 7)), 60, 1) * 0.0015)
    _afiar_bm(bm)
    return new_obj("capa", bm)

def _faixas_ouro(fig):
    """Filete de ouro gasto sobre o rolo da barra do manto: placas curtas, algumas faltando."""
    for j in range(26):
        h = abs(math.sin(j * 12.9898 + 0.7) * 43758.5453) % 1.0
        if h < 0.28: continue                                                  # placa perdida
        t0 = j / 26 * math.tau + 0.02; t1 = (j + 0.86) / 26 * math.tau
        rings = []
        for s in range(5):
            t = lerp(t0, t1, s / 4)
            x, y = _sup(t, 0.14); r = math.hypot(x, y); ux, uy = x / r, y / r
            def p(d, z): return Vector((x + ux * d, y + uy * d, z))
            rings.append([p(0.020, 0.108), p(0.020, 0.172), p(-0.006, 0.172), p(-0.006, 0.108)])
        bm = loft(rings, True, True)
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.0035, segments=1, affect='EDGES')
        o = new_obj("barra_ouro", bm)
        for pl in o.data.polygons: pl.material_index = IDX["ouro"]
        fig.append(o)

def adornos(fig):
    fig.append(_capa())
    # cinto: corda trançada em torno da cintura, com nó à frente e duas pontas desfiadas
    pts = []
    for i in range(0, 71):
        t = math.pi / 2 + 0.16 + (math.tau - 0.32) * i / 70
        x, y = _sup(t, 0.80 + 0.012 * math.sin(t * 3)); r = math.hypot(x, y)
        pts.append(Vector((x * (1 + 0.026 / r), y * (1 + 0.026 / r), 0.80 + 0.012 * math.sin(t * 3))))
    bm = tubo(pts, [0.028 * (1 + 0.16 * math.sin(i * 1.7)) for i in range(len(pts))], 8, True)
    displace(bm, lambda co, n: fbm(co, 70, 2) * 0.003); _afiar_bm(bm, 0.5); fig.append(new_obj("cinto", bm))
    yk = _sup(math.pi / 2, 0.80)[1]
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.05)
    for v in bm.verts: v.co = Vector((v.co.x * 1.35, v.co.y * 0.85 + yk + 0.035, v.co.z * 1.0 + 0.80))
    displace(bm, lambda co, n: 0.008 * math.sin(co.x * 120 + co.z * 40)); _afiar_bm(bm, 0.5); fig.append(new_obj("no", bm))
    for sx, dz, sw in ((-1, 0.50, 1.0), (1, 0.38, -0.8)):
        path = []
        for i in range(25):
            u = i / 24; z = 0.79 - dz * u; x = sx * (0.035 + 0.06 * math.sin(u * 2.6) * sw + 0.02 * u)
            t = math.pi / 2 - x / prof(A_T, z); path.append(Vector((x, _sup(t, z)[1] + 0.034 + 0.01 * u, z)))
        bm = tubo(path, [0.024 * (1 + 0.16 * math.sin(i * 1.7)) * (1 - 0.15 * i / 24) for i in range(25)], 8, True)
        displace(bm, lambda co, n: fbm(co, 70, 2) * 0.003); _afiar_bm(bm, 0.5); fig.append(new_obj("corda", bm))
        # ponta desfiada: cone aberto em leque
        bm2 = bmesh.new(); bmesh.ops.create_cone(bm2, cap_ends=True, segments=7, radius1=0.036, radius2=0.016, depth=0.075)
        for v in bm2.verts: v.co += path[-1] + Vector((0, 0.004, -0.032))
        displace(bm2, lambda co, n: fbm(co, 90, 1) * 0.007); _afiar_bm(bm2, 0.5); fig.append(new_obj("pingente", bm2))
    # medalhão de ouro (hexágono com aro e núcleo em relevo) e estilhaço de pedra, com corrente até a gola
    zm = 1.3; cx, cy, cr = _capa_r(math.pi / 2, zm); ym = cy * cr - 0.012          # medalhão apoiado na frente da capa
    def hexa(rad, prof_z, y0):
        b = bmesh.new(); bmesh.ops.create_cone(b, cap_ends=True, segments=6, radius1=rad, radius2=rad, depth=prof_z)
        for v in b.verts: v.co = Vector((v.co.x, -v.co.z * 1 + y0, v.co.y + zm))
        bmesh.ops.bevel(b, geom=b.edges[:], offset=0.004, segments=1, affect='EDGES'); return b
    for rad, d, y0 in ((0.11, 0.032, ym + 0.006), (0.07, 0.032, ym + 0.028)):
        o = new_obj("medalhao", hexa(rad, d, y0))
        for pl in o.data.polygons: pl.material_index = IDX["ouro"]
        fig.append(o)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=0.04, radius2=0.0, depth=0.11)
    for v in bm.verts: v.co = Vector((v.co.x * 0.9, v.co.z * -1 + ym + 0.075, v.co.y + zm))
    _afiar_bm(bm, 0.5); fig.append(new_obj("estilhaco", bm))
    for sx in (-1, 1):
        a0 = Vector((sx * 0.07, ym + 0.012, zm + 0.07)); ta = math.pi / 2 - sx * 0.62; xa, ya, ra = _capa_r(ta, 1.5); a1 = Vector((xa * ra, ya * ra + 0.02, 1.5))
        path = [bezier(a0, lerp(a0, a1, 0.3) + Vector((0, 0.01, -0.07)), lerp(a0, a1, 0.7) + Vector((0, 0.015, -0.03)), a1, i / 14) for i in range(15)]
        o = new_obj("corrente", tubo(path, [0.009 * (1 + 0.35 * math.sin(i * 2.4)) for i in range(15)], 6, True))
        for pl in o.data.polygons: pl.material_index = IDX["ouro"]
        fig.append(o)
    _faixas_ouro(fig)

def montar():
    fig = []
    fig.append(manto()); fig.append(capuz())
    br_l, pts_l = braco(-1, False); fig.append(br_l)
    br_r, pts_r = braco(1, True); fig.append(br_r)
    tg_l = (pts_l[-1] - pts_l[-2]).normalized(); m = mao(-1, 0.5, 1.9, "mao")        # mão esquerda aberta, palma para cima, segurando
    m.rotation_euler = _base_mao(tg_l, True).to_euler(); m.location = pts_l[-1] - tg_l * 0.045; fig.append(m)
    # ombros/dobra do manto sobre os braços: gola
    fig.append(gola())
    adornos(fig)
    # une a figura e leva ao mundo
    bpy.ops.object.select_all(action='DESELECT')
    for o in fig: o.select_set(True)
    bpy.context.view_layer.objects.active = fig[0]; bpy.ops.object.join()
    f = bpy.context.object
    f.scale = (S, S, S); f.location = (0, 0, PLINTO_H); bpy.ops.object.transform_apply(location=True, scale=True)
    f.name = "figura"
    # planta do manto encostada no tampo (afunda um pouco para não flutuar)
    f.location.z = -0.01; bpy.ops.object.transform_apply(location=True)
    parts = [f] + plinto()
    # fragmentos: mão quebrada e ponta do capuz sobre o tampo; entulho angular e lascas em volta do plinto
    pts = pts_r
    mao_q = new_obj("mao_quebrada", mao_quebrada()); mao_q.data.materials.append(mat_fratura())   # mão caída no tampo, palma para cima
    mao_q.location = (0.20, 0.50, PLINTO_H + 0.12); mao_q.rotation_euler = (0.0, math.pi, -1.35); mao_q.scale = (S, S, S); parts.append(mao_q)
    parts.append(pedaco("ponta", (-0.42, 0.50, PLINTO_H), 0.14, (0.8, 1.9, 0.8), (0.1, 0.0, 0.6)))
    parts += _pl_entulho()
    return parts

def musgo(o):
    """Musgo em manchas orgânicas: divide as faces de cima e as da base do plinto/entulho em triângulos pequenos e escolhe por ruído
    de baixa frequência; as manchas levantam um pouco (almofada) e ganham tufos facetados. Na figura segue o ruído antigo."""
    mw = o.matrix_world; bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    def ruido(c): return fbm(c + Vector((0.37, 0.71, 0.13)), 5.0, 3)
    alvo = [f for f in bm.faces if f.material_index == 0 and (mw @ f.calc_center_median()).z < PLINTO_H + 0.04 and f.normal.z > 0.85 and f.calc_area() > 0.0016]
    for f in alvo:
        if not f.is_valid: continue
        if ruido(mw @ f.calc_center_median()) < -0.12: continue                  # longe das manchas: não divide
        cuts = min(6, max(1, int(max(e.calc_length() for e in f.edges) / 0.03)))
        bmesh.ops.subdivide_edges(bm, edges=list(f.edges), cuts=cuts, use_grid_fill=True)
    bm.faces.ensure_lookup_table(); bm.normal_update(); tufos = []
    for f in bm.faces:
        if f.material_index != 0: continue
        c = mw @ f.calc_center_median(); up = f.normal.z; v = ruido(c)
        if c.z < PLINTO_H + 0.04:
            borda = (0.0 if c.z > 0.30 else 0.22 * (0.30 - c.z) / 0.30)            # mais musgo perto do chão
            ok = up > 0.85 and v > 0.02 - borda
            if ok and f.calc_area() < 0.003:
                f.material_index = IDX["musgo"]
                if up > 0.85 and v > 0.34 and len(tufos) < 16: tufos.append(c.copy())
        elif f.calc_area() < 0.004:                                                # figura: ruído original
            thr = 0.10 - 0.5 * max(0.0, 0.9 - c.z) + (0.0 if c.z < 0.9 else 0.06)
            if up > 0.55 and v > thr + 0.28: f.material_index = IDX["musgo"]
    rng = random.Random(5)
    for c in tufos:                                                                # tufos: cúpulas achatadas e facetadas
        if rng.random() < 0.4: continue
        r = rng.uniform(0.04, 0.07); pts = []
        for _ in range(9):
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), abs(rng.gauss(0, 0.8)))).normalized()
            pts.append(Vector((d.x * r * 1.3, d.y * r, d.z * r * 0.32)))
        pts += [Vector((p.x, p.y, -0.006)) for p in pts[:6]]
        t = _pl_acabar(_pl_hull(pts), 0.003, 0.2)
        for v in t.verts: v.co += c
        m2 = bpy.data.meshes.new("t"); t.to_mesh(m2); t.free(); n0 = len(bm.faces); bm.from_mesh(m2); bpy.data.meshes.remove(m2)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n0:]: f.material_index = IDX["musgo"]
    bm.to_mesh(o.data); bm.free()


def pintar(o):
    """Cor de vértice (COLOR_0): cavidades escuras, arestas gastas, sujeira embaixo e variação de pedra. Multiplica a cor-base no Godot."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    cav = {}
    for v in bm.verts:
        viz = [e.other_vert(v).co for e in v.link_edges]
        if viz:
            m = sum(viz, Vector()) / len(viz); cav[v.index] = (m - v.co).dot(v.normal)   # >0 côncavo
        else: cav[v.index] = 0.0
    layer = bm.loops.layers.float_color.new("Color")
    for f in bm.faces:
        for l in f.loops:
            v = l.vert; c = o.matrix_world @ v.co
            k = max(-1.0, min(1.0, cav[v.index] * 90))
            val = 0.82 + 0.45 * (-k if k < 0 else 0) - 0.50 * (k if k > 0 else 0)          # arestas claras, cavidades escuras
            val *= 0.85 + 0.25 * (fbm(c + Vector((3.1, 1.7, 0.4)), 3.2, 3) + 0.5)          # manchas largas
            val *= 0.75 + 0.25 * min(1.0, c.z / 1.2)                                       # sujeira perto do chão
            tom = 0.04 * fbm(c * 2.0, 2, 2)
            l[layer] = (max(0.05, min(1.4, val)) * (1 - tom), max(0.05, min(1.4, val)), max(0.05, min(1.4, val)) * (1 + tom), 1)
    bm.to_mesh(o.data); bm.free()

def exportar(parts):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
    o = bpy.context.object; o.name = "SM_Cripta_Estatua"
    musgo(o)
    pintar(o)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(34))   # facetas nítidas: só suaviza onde o ângulo é pequeno
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SM_Cripta_Estatua.glb"), use_selection=True, export_format='GLB', export_yup=True, export_vertex_color='ACTIVE')
    print("exportado SM_Cripta_Estatua", len(o.data.polygons), "faces, altura", round(o.dimensions.z, 2), "m")
    return o

def render(o, ang, nome, samples=24, res=(640, 800), alvo=None, d=6.5):
    sc = bpy.context.scene
    for ob in [x for x in sc.objects if x.type in ('CAMERA', 'LIGHT')]: bpy.data.objects.remove(ob)
    sc.render.engine = 'CYCLES'; sc.cycles.samples = samples; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.03, 0.045, 1); sc.world = w
    alvo = alvo or Vector((0, 0, 1.55));
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); cam.data.lens = 60
    cam.location = alvo + Vector((math.sin(ang) * d, -math.cos(ang) * d, 0.6))
    cam.rotation_euler = (alvo - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    rot = lambda v: Vector((v.x * math.cos(ang - math.pi) - v.y * math.sin(ang - math.pi), v.x * math.sin(ang - math.pi) + v.y * math.cos(ang - math.pi), v.z))
    # luzes definidas para a câmera em +Y e giradas junto com ela
    for loc, e, col in (((-3, 4, 5), 380, (1, 0.9, 0.8)), ((4, 3, 2), 170, (0.6, 0.7, 1.0)), ((0, -3, 3), 250, (0.7, 0.8, 1.0)), ((0.2, 1.0, 1.0), 120, (1.0, 0.55, 0.2))):
        L = bpy.data.objects.new("l", bpy.data.lights.new("l", 'POINT')); L.data.energy = e; L.data.color = col; L.location = rot(Vector(loc)); sc.collection.objects.link(L)
    sc.render.filepath = os.path.join(PREV, nome + ".png"); bpy.ops.render.render(write_still=True)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    o = exportar(montar())
    if PREV:
        os.makedirs(PREV, exist_ok=True)
        render(o, 3.45, "estatua_frente")
        render(o, 0.35, "estatua_tras")
        sc = bpy.context.scene; mw = o.modifiers.new("wf", 'WIREFRAME'); mw.thickness = 0.004   # vista de malha
        render(o, 3.45, "estatua_wireframe", samples=8)
        o.modifiers.remove(mw)
        render(o, 3.14, "estatua_close_capuz", res=(640, 640), alvo=Vector((0, 0, 2.55)), d=2.8)
