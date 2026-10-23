"""Arqueiro_Capuz.glb v4: capuz, mascara de bico de osso, lenco e gola.
Objetivo: tirar o aspecto de massinha da v3 (lobulos rigidos, placas de osso em bloco, olhos de desenho animado) com malha
arredondada por subdivisao, borda de pano enrolada com friso dourado, mascara lisa de osso com olhos amendoados em fenda
(folha aprovada 03_arqueiro.png), rosto coberto por lenco escuro e gola de pano caindo sobre os ombros.
Rig: o armature de 27 ossos (Rig_Humanoid_Chibi) vem do GLB atual (ARQ_BASE_GLB), ja no espaco chibi; as malhas sao
modeladas direto nesse espaco (Blender Z cima, rosto olha para -Y) e skinadas ao osso Head (gola: Neck).
Rodar: python pintar_capuz_v4.py  (texturas em texturas_capuz_v4/)  e depois  python build_capuz_v4.py  (bpy) ou blender -b -P.
Saida: ARQ_SAIDA (padrao godot/art/models/personagens/arqueiro/Arqueiro_Capuz.glb).
"""
import os, sys, math
import bpy, bmesh
from mathutils import Vector, noise

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import _comum as c

TEX = os.path.join(AQUI, "texturas_capuz_v4")
BASE_GLB = os.environ.get("ARQ_BASE_GLB", os.path.join(c.SAIDA, "Arqueiro_Capuz.glb"))
HC = Vector((0.0, 0.07, 1.275))   # centro do capuz


def sstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lerp_tab(tab, x):
    if x <= tab[0][0]:
        return tab[0][1]
    for (x0, y0), (x1, y1) in zip(tab, tab[1:]):
        if x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + (y1 - y0) * t
    return tab[-1][1]


# ---------- materiais ----------
def mat(nome, tex=None, cor=(0.5, 0.5, 0.5, 1), rough=0.85, metal=0.0, emis=None, emis_forca=2.0, dupla=False):
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if tex:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEX, tex), check_existing=True)
        t.image.colorspace_settings.name = "sRGB"
        t.image.pack()
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = cor
    if emis:
        b.inputs["Emission Color"].default_value = emis
        b.inputs["Emission Strength"].default_value = emis_forca
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    m.use_backface_culling = not dupla
    return m


# ---------- utilidades de malha ----------
def para_objeto(bm, nome, mats, arm, osso, subsurf=0, suave=True):
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(nome, me)
    bpy.context.scene.collection.objects.link(ob)
    if subsurf:
        md = ob.modifiers.new("ss", "SUBSURF")
        md.levels = subsurf
        md.render_levels = subsurf
        md.uv_smooth = "PRESERVE_BOUNDARIES"
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier="ss")
    for p in ob.data.polygons:
        p.use_smooth = suave
    vg = ob.vertex_groups.new(name=osso)
    vg.add([v.index for v in ob.data.vertices], 1.0, "REPLACE")
    ob.parent = arm
    md = ob.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    return ob


def casca_esfera(u, v):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    bm.faces.ensure_lookup_table()
    return bm


def uv_cilindro(bm, uvl, fn):
    """UV por angulo (u, 0.5 = frente, -Y) e altura; corrige a emenda nas costas."""
    for f in bm.faces:
        us = []
        for l in f.loops:
            co = fn(l.vert)
            us.append(math.atan2(co.x, -co.y) / (2 * math.pi) + 0.5)
        if max(us) - min(us) > 0.5:
            us = [u + 1 if u < 0.25 else u for u in us]
        for l, u in zip(f.loops, us):
            co = fn(l.vert)
            l[uvl].uv = (u, max(0.0, min(1.0, (co.z + 1.0) / 2.0)) * 0.96 + 0.02)


def borda_enrolada(bm, bordas, delta, mi):
    """extrude as arestas de borda e puxa os vertices novos por delta(v) (lábio de pano); faces novas em mi."""
    uvl = bm.loops.layers.uv.active
    uv_v = {}
    if uvl:
        for e in bordas:
            for v in e.verts:
                uv_v[v] = v.link_loops[0][uvl].uv.copy()
    r = bmesh.ops.extrude_edge_only(bm, edges=bordas)
    novos = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
    if uvl:
        for g in r["geom"]:
            if isinstance(g, bmesh.types.BMFace):
                for l in g.loops:
                    v = l.vert
                    if v in uv_v:
                        l[uvl].uv = uv_v[v]
                    else:
                        for e in v.link_edges:
                            o = e.other_vert(v)
                            if o in uv_v and o in g.verts:
                                l[uvl].uv = uv_v[o]
                                break
    for v in novos:
        v.co += delta(v)
    for g in r["geom"]:
        if isinstance(g, bmesh.types.BMFace):
            g.material_index = mi
    return novos


# ---------- capuz ----------
# O capuz e um loft: aneis perpendiculares a uma espinha que sobe reta pela cabeca e curva para tras ate a ponta
# (silhueta de touca pontuda da folha). A abertura frontal e recortada depois, com friso dourado enrolado.
NT, NS = 30, 32
Q = (Vector((0, 0.07, 1.17)), Vector((0, 0.07, 1.34)), Vector((0.05, 0.24, 1.50)), Vector((0.20, 0.40, 1.38)))
RAIO = [(0.0, 0.330), (0.10, 0.310), (0.20, 0.300), (0.30, 0.295), (0.40, 0.280), (0.50, 0.250), (0.60, 0.205),
        (0.70, 0.150), (0.80, 0.100), (0.90, 0.052), (1.0, 0.004)]
HEM_Z, HEM_T = 0.985, 0.30
Z_ARCO, HW, Z_TOPO = 1.21, 0.178, 1.405


def bezier(p0, p1, p2, p3, t):
    a = (1 - t)
    return p0 * a ** 3 + p1 * 3 * a * a * t + p2 * 3 * a * t * t + p3 * t ** 3


def espinha(t):
    if t <= HEM_T:
        return Vector((0, 0.07, HEM_Z + (Q[0].z - HEM_Z) * t / HEM_T)), Vector((0, 0, 1))
    u = (t - HEM_T) / (1 - HEM_T)
    p = bezier(*Q, u)
    d = (bezier(*Q, min(1.0, u + 0.01)) - bezier(*Q, max(0.0, u - 0.01))).normalized()
    return p, d


def hw_z(z):
    if z <= Z_ARCO:
        return HW
    u = min(1.0, (z - Z_ARCO) / (Z_TOPO - Z_ARCO))
    return HW * (1 - u ** 1.7) ** 0.75   # ogiva: laterais retas e topo em ponta suave


def angulos(ps_b, R=None):
    """psi (-pi..pi, 0 = frente) de cada vertice de um anel: os vertices a +-JF celulas da frente caem exatamente em +-ps_b
    (contorno da abertura); a primeira celula de fora e estreita (friso dourado); o resto se distribui ate as costas."""
    out = []
    for j in range(NS):
        d = j - NS // 2
        a = abs(d)
        if a <= JF:
            psi = (d / JF) * ps_b
        else:
            n = a - JF
            if n == 1:
                psi = ps_b + FRISO
            else:
                psi = ps_b + FRISO + (math.pi - ps_b - FRISO) * (n - 1) / (NS // 2 - JF - 1)
            psi = math.copysign(psi, d)
        out.append(psi)
    return out


JF, FRISO = 3, 0.060


def hood(m_pano, m_ouro, arm):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    X = Vector((1, 0, 0))
    an, psis, zfs = [], [], []
    # 1) altura do centro frontal de cada anel e anel k1 onde a ogiva se fecha
    cen_k = []
    for k in range(NT + 1):
        cen, T = espinha(k / NT)
        Nn = T.cross(X).normalized()
        R = lerp_tab(RAIO, k / NT)
        cen_k.append((cen, T, Nn, R))
        zfs.append(cen.z - Nn.z * R * 0.985)
    k1 = next(k for k in range(NT + 1) if zfs[k] >= Z_TOPO - 0.004)
    unif = (JF / (NS / 2)) * math.pi
    for k in range(NT + 1):
        t = k / NT
        cen, T, Nn, R = cen_k[k]
        zf = zfs[k]
        if k <= k1:
            ps = math.asin(min(0.999, max(0.0, hw_z(zf)) / R))
            ps = max(ps, 0.045)
        else:
            w = min(1.0, (zf - Z_TOPO) / 0.30)
            ps = 0.045 * (1 - w) + unif * w
        psi_l = angulos(ps)
        psis.append(psi_l)
        linha = []
        for j in range(NS):
            psi = psi_l[j]
            sx, sn = math.sin(psi), -math.cos(psi)         # frente = -Nn (sn=-1 em psi=0)
            env = sstep(0.45, 1.3, abs(psi))
            cr = abs(math.sin(psi * 3.0 + 4.0 * t + 0.5 * math.sin(psi * 2.0))) ** 0.55 - 0.55
            cr2 = abs(math.sin(psi * 4.7 - 3.0 * t + 1.0)) ** 0.7 - 0.55
            amp = 0.30 * env * (0.30 + 0.70 * sstep(0.75, 0.15, t)) * (1 - sstep(0.80, 1.0, t))
            nz = noise.noise(Vector((psi * 1.3, t * 3.0, 5.0)))
            r = R * (1 + amp * (cr * 0.75 + cr2 * 0.35) + 0.02 * nz)
            pos = cen + X * (sx * r) + Nn * (sn * r * 0.985)
            if abs(psi) < 1.0 and 1.28 < pos.z < 1.52:   # aba da testa projetada sobre os olhos
                pos.y -= 0.06 * sstep(1.28, 1.40, pos.z) * (1 - sstep(1.45, 1.52, pos.z)) * (1 - abs(psi))
            if t < 0.2 and sn > 0:                         # costas do capuz pendem para tras
                pos.y += 0.04 * (0.2 - t) / 0.2 * sn
            if t < 0.08:                                   # barra ondulada, mais baixa nos lados
                pos.z -= 0.075 * (1 - t / 0.08) * (0.5 + 0.5 * math.sin(psi * 7 + 1.0)) * (0.4 + 0.6 * env)
            linha.append(bm.verts.new(pos))
        an.append(linha)
    marca = set()
    jA, jB = NS // 2 - JF, NS // 2 + JF
    for k in range(NT):
        for j in range(NS):
            j2 = (j + 1) % NS
            dentro = (jA <= j < jB) and k < k1
            if dentro:
                marca.update([an[k][j], an[k][j2], an[k + 1][j], an[k + 1][j2]])
                continue
            f = bm.faces.new([an[k][j], an[k][j2], an[k + 1][j2], an[k + 1][j]])
            ouro = (k < k1) and (j == jA - 1 or j == jB)
            f.material_index = 1 if ouro else 0
            for l, (jj, kk) in zip(f.loops, [(j, k), (j2, k), (j2, k + 1), (j, k + 1)]):
                uu = psis[kk][jj] / (2 * math.pi) + 0.5
                if j2 == 0 and jj == 0:
                    uu = 1.0
                l[uvl].uv = (uu, 0.02 + 0.96 * (kk / NT))
    bm.faces.ensure_lookup_table()
    borda_ab = [v for v in marca if v.is_valid and v.link_faces]
    ouro_v = set(borda_ab)
    bordas = [e for e in bm.edges if e.is_boundary]
    ab_edges = [e for e in bordas if e.verts[0] in ouro_v and e.verts[1] in ouro_v]
    ou_edges = [e for e in bordas if e not in ab_edges]

    def delta_ab(v):  # labio para dentro e um pouco para tras
        d = (v.co - Vector((0, 0.09, 1.25))).normalized()
        return -d * 0.024 + Vector((0, 0.008, 0))

    def delta_barra(v):
        d = (v.co - Vector((0, 0.07, v.co.z))).normalized()
        return -d * 0.016 + Vector((0, 0, -0.012))
    borda_enrolada(bm, ab_edges, delta_ab, 1)
    borda_enrolada(bm, ou_edges, delta_barra, 0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    f0 = max(bm.faces, key=lambda f: (f.calc_center_median() - HC).length)
    if f0.normal.dot(f0.calc_center_median() - HC) < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    return para_objeto(bm, "SK_Archer_Capuz", [m_pano, m_ouro], arm, "Head", subsurf=0)


# ---------- mascara ----------
LARG = [(0.0, 0.010), (0.08, 0.020), (0.20, 0.038), (0.40, 0.058), (0.55, 0.080), (0.66, 0.118), (0.78, 0.146),
        (0.90, 0.126), (0.96, 0.088), (1.0, 0.040)]
Z0, Z1 = 1.15, 1.385
OLHO_C, OLHO_RX, OLHO_RZ, OLHO_ROT = (0.062, 1.322), 0.054, 0.027, 22.0


def mascara_pt(u, v):
    """superficie da mascara: u in [-1, 1] (esq-dir), v in [0, 1] (ponta do bico -> testa)."""
    w = lerp_tab(LARG, v) * 1.12
    x = u * w
    z = Z0 + (Z1 - Z0) * v
    if v < 0.60:
        yb = -0.205 - 0.105 * (1 - v / 0.60) ** 1.1
    else:
        yb = -0.205 + 0.010 * sstep(0.60, 1.0, v)
    yb += 0.006
    yb -= 0.024 * math.exp(-((v - 0.80) / 0.09) ** 2) * (1 - abs(u) ** 3)
    yb -= 0.012 * math.exp(-((v - 0.62) / 0.10) ** 2) * (abs(u) ** 1.2) * (1 - abs(u)) * 2.5   # maca do rosto           # sobrancelha
    yb += 0.060 * sstep(0.88, 1.0, v) ** 2                                           # testa recua
    yb += x * x * 3.6                                                                # curva em volta da cabeca
    quilha = 0.045 * sstep(0.62, 0.45, v) * (1 - abs(u)) ** 1.4 + 0.008 * sstep(0.7, 0.6, v) * (1 - abs(u)) ** 2
    yb -= quilha
    z -= 0.012 * (1 - v / 0.6) ** 2 * (v < 0.6)                                      # ponta do bico cai
    return Vector((x, yb, z))


def mascara(m_osso, arm):
    NU, NV = 10, 14
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    grade = {}
    for j in range(NV + 1):
        for i in range(NU + 1):
            u = -1 + 2 * i / NU
            v = (j / NV)
            grade[i, j] = bm.verts.new(mascara_pt(u, v))
    for j in range(NV):
        for i in range(NU):
            f = bm.faces.new([grade[i, j], grade[i + 1, j], grade[i + 1, j + 1], grade[i, j + 1]])
            for l in f.loops:
                co = l.vert.co
                l[uvl].uv = (0.5 + co.x / 0.30, (co.z - Z0) / (Z1 - Z0))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    # inverte se a normal aponta para dentro
    if bm.faces[0].normal.y > 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    me = bpy.data.meshes.new("mask_tmp")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("mask_tmp", me)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    md = ob.modifiers.new("sol", "SOLIDIFY")
    md.thickness = 0.022
    md.offset = -1.0
    md.use_rim = True
    bpy.ops.object.modifier_apply(modifier="sol")
    # furos dos olhos (cortadores elipticos inclinados)
    for s in (-1, 1):
        bmc = bmesh.new()
        bmesh.ops.create_cone(bmc, cap_ends=True, segments=14, radius1=1.0, radius2=1.0, depth=0.20)
        cm = bpy.data.meshes.new("cut%d" % s)
        bmc.to_mesh(cm)
        bmc.free()
        co = bpy.data.objects.new("cut%d" % s, cm)
        bpy.context.scene.collection.objects.link(co)
        co.rotation_euler = (math.radians(90), math.radians(-s * OLHO_ROT), 0)
        co.scale = (OLHO_RX, OLHO_RZ, 1.0)
        co.location = (s * OLHO_C[0], -0.19, OLHO_C[1])
        bpy.context.view_layer.update()
        bpy.context.view_layer.objects.active = ob
        bo = ob.modifiers.new("bool", "BOOLEAN")
        bo.object = co
        bo.operation = "DIFFERENCE"
        bo.solver = "EXACT"
        bpy.ops.object.modifier_apply(modifier="bool")
        bpy.data.objects.remove(co)
    bpy.context.view_layer.objects.active = ob
    bv = ob.modifiers.new("bev", "BEVEL")
    bv.width = 0.0035
    bv.segments = 1
    bv.limit_method = "ANGLE"
    bv.angle_limit = math.radians(35)
    bpy.ops.object.modifier_apply(modifier="bev")
    me = ob.data
    me.materials.append(m_osso)
    for p in me.polygons:
        p.use_smooth = True
    ob.name = "SK_Archer_Mascara"
    me.name = "SK_Archer_Mascara"
    vg = ob.vertex_groups.new(name="Head")
    vg.add([v.index for v in me.vertices], 1.0, "REPLACE")
    ob.parent = arm
    md = ob.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    return ob


# ---------- rosto: vazio escuro atras da mascara, olhos em fenda, lenco ----------
def elipsoide(bm, centro, rx, ry, rz, seg=(14, 9)):
    r = bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=1.0)
    for v in r["verts"]:
        v.co = Vector((v.co.x * rx + centro[0], v.co.y * ry + centro[1], v.co.z * rz + centro[2]))
    return r["verts"]


def rosto(m_vazio, m_olho, m_lenco, arm, m_nucleo=None):
    # 0 = vazio escuro, 1 = olhos, 2 = lenco
    bm = bmesh.new()
    elipsoide(bm, (0, -0.005, 1.285), 0.150, 0.135, 0.175, seg=(14, 8))
    for f in bm.faces:
        f.material_index = 0
    fa = len(bm.faces)
    for s in (-1, 1):
        for esc_, dy, mi_ in ((0.58, -0.172, 1), (0.28, -0.178, 3)):
            n0 = len(bm.faces)
            vs = elipsoide(bm, (0, 0, 0), 1, 1, 1, seg=(12, 6))
            for v in vs:   # fenda amendoada, ponta externa para cima
                x, y, z = v.co.x * (OLHO_RX * esc_), v.co.y * 0.010, v.co.z * (OLHO_RZ * esc_ * 0.95)
                a = math.radians(s * OLHO_ROT)
                xr = x * math.cos(a) + z * math.sin(a)
                zr = -x * math.sin(a) + z * math.cos(a)
                v.co = Vector((s * OLHO_C[0] + xr, dy + y, OLHO_C[1] + zr))
            bm.faces.ensure_lookup_table()
            for f in bm.faces[n0:]:
                f.material_index = mi_
    bm.faces.ensure_lookup_table()
    # lenco: faixa de pano em tigela sob o bico, subindo nas bochechas e fechando no pescoco
    bl = casca_esfera(24, 12)
    uvl = bl.loops.layers.uv.verify()
    uv_cilindro(bl, uvl, lambda v: v.co)
    mor = []
    for f in bl.faces:
        p = f.calc_center_median()
        topo = 0.0 + 1.1 * min(1.0, abs(p.x) / 0.85) ** 1.2
        if p.z > topo or p.z < -1.0 or p.y > 0.55:
            mor.append(f)
    bmesh.ops.delete(bl, geom=mor, context="FACES")
    for v in bl.verts:
        v.co = Vector((v.co.x * 0.168, v.co.y * 0.150, v.co.z * 0.135)) + Vector((0, 0.035, 1.185))
    for v in bl.verts:   # dobras em diagonal no pano do lenco
        n = noise.noise(Vector((v.co.x * 14, v.co.z * 10 + v.co.x * 6, 2.0)))
        d = (v.co - Vector((0, 0.0, 1.185))).normalized()
        v.co += d * 0.008 * n
    for _ in range(12):   # alisa a escada da borda de cima
        nv = {}
        for v in bl.verts:
            viz = [e.other_vert(v).co for e in v.link_edges if e.is_boundary]
            if len(viz) == 2:
                nv[v] = v.co * 0.5 + (viz[0] + viz[1]) * 0.25
        for v, co in nv.items():
            v.co = co
    bordas = [e for e in bl.edges if e.is_boundary]
    topo_e = [e for e in bordas if (e.verts[0].co.z + e.verts[1].co.z) / 2 > 1.08]
    baixo_e = [e for e in bordas if e not in topo_e]
    borda_enrolada(bl, topo_e, lambda v: Vector((-v.co.x * 0.02, -0.014, 0.010)), 0)
    borda_enrolada(bl, baixo_e, lambda v: Vector((0, 0.0, -0.012)), 0)
    # copia o lenco para o bmesh principal
    mapa = {}
    uvp = bm.loops.layers.uv.verify()
    for v in bl.verts:
        mapa[v] = bm.verts.new(v.co)
    for f in bl.faces:
        nf = bm.faces.new([mapa[v] for v in f.verts])
        nf.material_index = 2
        for l_old, l_new in zip(f.loops, nf.loops):
            l_new[uvp].uv = l_old[uvl].uv
    bl.free()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    ob = para_objeto(bm, "SK_Archer_Rosto", [m_vazio, m_olho, m_lenco, m_nucleo], arm, "Head", subsurf=0)
    # subdivisao so no lenco: aplica no objeto inteiro seria pesado nos olhos; faz por modificador de material nao existe,
    # entao o lenco recebe suavizacao pelas normais suaves e pela malha ja densa
    return ob


# ---------- gola ----------
def gola(m_pano, m_ouro, arm):
    NU, NV = 27, 5
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    perfil = [(1.005, 0.120), (0.990, 0.165), (0.950, 0.215), (0.915, 0.252), (0.885, 0.275), (0.865, 0.285)]
    anel = []
    for j, (z, r) in enumerate(perfil):
        linha = []
        for i in range(NU):
            a = 2 * math.pi * i / NU
            lobo = math.cos(a * 9)
            ond = 1 + 0.12 * lobo * (j / NV) ** 1.2
            rr = r * ond
            x, y = rr * math.sin(a) * 1.0, -rr * math.cos(a) * 0.86 + 0.075
            zz = z - 0.06 * (j / NV) * (max(0.0, lobo) ** 1.5)
            if y < 0.0 and j > 0:   # a frente cai mais (peito) e as costas sobem
                zz -= 0.01 * j
            linha.append(bm.verts.new((x, y, zz)))
        anel.append(linha)
    for j in range(NV):
        for i in range(NU):
            i2 = (i + 1) % NU
            f = bm.faces.new([anel[j][i], anel[j][i2], anel[j + 1][i2], anel[j + 1][i]])
            f.material_index = 0
            for l in f.loops:
                ang = math.atan2(l.vert.co.x, -(l.vert.co.y - 0.075)) / (2 * math.pi) + 0.5
                l[uvl].uv = (ang, 1 - (perfil[0][0] - l.vert.co.z) / 0.2)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bordas = [e for e in bm.edges if e.is_boundary]
    ap = [e for e in bordas if (e.verts[0].co.z + e.verts[1].co.z) / 2 > 1.0]
    bx = [e for e in bordas if e not in ap]
    borda_enrolada(bm, ap, lambda v: Vector((0, 0, -0.004)), 0)
    borda_enrolada(bm, bx, lambda v: Vector((0, 0, -0.012)), 0)
    return para_objeto(bm, "SK_Archer_Gola", [m_pano, m_ouro], arm, "Neck", subsurf=0)


# ---------- montagem ----------
def main():
    c.limpar()
    bpy.ops.import_scene.gltf(filepath=BASE_GLB)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    for o in [o for o in bpy.data.objects if o.type == "MESH"]:
        bpy.data.objects.remove(o)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):   # sobras do GLB antigo (nomes ficariam com .001)
        for d in list(coll):
            coll.remove(d)
    m_pano = mat("M_Arqueiro_Capuz", tex="T_Capuz_BC.png", rough=0.92, dupla=True)
    m_ouro = mat("M_Arqueiro_CapuzOuro", tex="T_Ouro_BC.png", rough=0.45, metal=0.55, dupla=True)
    m_osso = mat("M_Arqueiro_Mascara", tex="T_Mascara_BC.png", rough=0.55, dupla=True)
    m_vazio = mat("M_Arqueiro_RostoVazio", cor=(0.018, 0.034, 0.016, 1), rough=1.0, dupla=True)
    m_olho = mat("M_Arqueiro_OlhoVerde", cor=(0.10, 0.55, 0.06, 1), rough=0.3, emis=(0.12, 0.85, 0.05, 1), emis_forca=1.0, dupla=True)
    m_nucleo = mat("M_Arqueiro_OlhoNucleo", cor=(0.8, 1.0, 0.6, 1), rough=0.3, emis=(0.75, 1.0, 0.55, 1), emis_forca=1.6, dupla=True)
    m_lenco = mat("M_Arqueiro_Lenco", tex="T_Lenco_BC.png", rough=0.95, dupla=True)
    hd = hood(m_pano, m_ouro, arm)
    mk = mascara(m_osso, arm)
    ro = rosto(m_vazio, m_olho, m_lenco, arm, m_nucleo)
    gl = gola(m_lenco, m_ouro, arm)
    tot = 0
    for o in (hd, mk, ro, gl):
        t = sum(len(p.vertices) - 2 for p in o.data.polygons)
        print("TRIS", o.name, t)
        tot += t
    print("TRIS_TOTAL", tot)
    vs = [v.co for o in (hd, mk, ro, gl) for v in o.data.vertices]
    print("BOUNDS", [round(min(v[i] for v in vs), 3) for i in range(3)], [round(max(v[i] for v in vs), 3) for i in range(3)])
    c.exportar("Arqueiro_Capuz.glb", [arm, hd, mk, ro, gl])


main()
