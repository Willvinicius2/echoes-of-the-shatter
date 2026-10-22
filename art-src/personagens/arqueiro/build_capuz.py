"""Exporta Arqueiro_Capuz.glb: capuz verde-musgo com dobras, moldura dourada angulosa em V, mascara de
cranio de corvo com bico longo, olhos de iris verde, lenco em 3 rolos e cabelo. Geometria procedural,
tudo skinado ao osso Head (peso 1.0), mesmo Rig_Humanoid_Chibi (27 ossos).
Rodar: python pintar_capuz.py  (texturas)  e depois  blender -b -P build_capuz.py
Eixos Blender (Z-up): rosto olha para -Y, cabeca em (0, 0.06, 1.30).
"""
import os, sys, math
import bpy, bmesh
from mathutils import Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c

TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "texturas_capuz")
C = Vector((0.0, 0.06, 1.30))  # centro da cabeca


# ---------- materiais ----------
def mat(nome, cor=None, tex=None, normal=None, rough=0.85, emis_tex=None, emis=1.0, dupla=False):
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = 0.0

    def img(nome_png, cs):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEX, nome_png), check_existing=True)
        t.image.colorspace_settings.name = cs
        t.image.pack()
        return t
    if tex:
        t = img(tex, "sRGB")
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        if emis_tex:
            nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = emis
    else:
        b.inputs["Base Color"].default_value = cor
    if normal:
        n = img(normal, "Non-Color")
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    m.use_backface_culling = not dupla
    return m


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ---------- capuz ----------
# abertura em V (losango achatado) em coordenadas unitarias (x, z) da esfera
POLY = [(0.0, 0.78), (-0.60, 0.36), (-0.80, -0.12), (-0.68, -0.64), (0.68, -0.64), (0.80, -0.12), (0.60, 0.36)]


def dentro(x, z):
    ok = False
    for (x1, z1), (x2, z2) in zip(POLY, POLY[1:] + POLY[:1]):
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            ok = not ok
    return ok


def raio_poly(phi):
    """distancia da origem ao contorno do POLY na direcao phi."""
    dx, dz = math.cos(phi), math.sin(phi)
    melhor = 9.0
    for (x1, z1), (x2, z2) in zip(POLY, POLY[1:] + POLY[:1]):
        ex, ez = x2 - x1, z2 - z1
        den = dx * ez - dz * ex
        if abs(den) < 1e-9:
            continue
        t = (x1 * ez - z1 * ex) / den
        s = (x1 * dz - z1 * dx) / den
        if t > 0 and -1e-6 <= s <= 1 + 1e-6:
            melhor = min(melhor, t)
    return melhor


D_PONTA = Vector((0, 0.6, 0.8)).normalized()


def dobra(p, folds=True):
    """deformacao do capuz em coordenadas unitarias: ponta curva, aba da testa, dobras de pano, bainha."""
    p = p.copy()
    k = max(0.0, p.dot(D_PONTA)) ** 2.6
    p += D_PONTA * 0.72 * k
    p.y += 0.30 * k      # a ponta cai para tras
    p.z -= 0.10 * k
    if p.y < 0 and p.z > 0.12:  # aba da testa projetada
        p.y -= 0.34 * min(1.0, (p.z - 0.12) / 0.55) * min(1.0, -p.y / 0.5)
    if p.z < -0.30:  # bainha alargada
        f = 1 + 0.34 * (-0.30 - p.z)
        p.x *= f; p.y *= f
    if folds:
        psi = math.atan2(p.x, -p.y)
        env = smoothstep(0.9, 1.5, abs(psi))
        amp = 0.22 * env * (0.30 + 0.70 * (1 - p.z) / 2)
        sn = math.sin(psi * 4 + 0.9 + (0.5 if psi > 0 else -0.5))
        ondas = (1 - 2 * abs(sn) ** 0.7) * 0.8 + 0.30 * math.sin(psi * 9 + 2.0)
        if p.z < -0.3:
            p.z -= 0.07 * env * max(0.0, math.sin(psi * 8 + 1.0))
        p *= 1 + amp * ondas
        # vinco do topo para a ponta (crista nas costas)
        vinco = math.exp(-(p.x / 0.16) ** 2) * smoothstep(0.1, 0.75, p.dot(D_PONTA))
        p *= 1 + 0.07 * vinco
        n = noise.noise(p * 2.1 + Vector((3, 1, 7)))
        p *= 1 + 0.03 * n
        p.x *= 1.0 + 0.025 * (1 if p.x > 0 else -1) * n
    return p


def esc(p, f=1.0):
    return Vector((p.x * 0.185 * f, p.y * 0.20 * f, p.z * 0.157 * f)) + C


def hood():
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=15, radius=1.0)
    bm.faces.ensure_lookup_table()
    morrer, marca = [], set()
    for f in bm.faces:
        p = f.calc_center_median()
        if p.y < -0.15 and dentro(p.x, p.z):
            morrer.append(f); marca.update(f.verts)
        elif p.z < -0.58:
            morrer.append(f)
    bmesh.ops.delete(bm, geom=morrer, context="FACES")
    borda = [v for v in marca if v.is_valid and v.link_faces]
    ang = {}
    for v in borda:
        phi = math.atan2(v.co.z, v.co.x)
        r = raio_poly(phi)
        x, z = r * math.cos(phi), r * math.sin(phi)
        v.co.x, v.co.z = x, z
        v.co.y = -math.sqrt(max(0.02, 1 - x * x - z * z))
        ang[v] = (phi + math.pi / 3) % (2 * math.pi)
    # UV (u = angulo, 0.5 frente; v = altura) com os valores ANTES da deformacao
    for f in bm.faces:
        us = []
        for l in f.loops:
            co = l.vert.co
            us.append(math.atan2(co.x, -co.y) / (2 * math.pi) + 0.5)
        if max(us) - min(us) > 0.5:
            us = [u + 1 if u < 0.25 else u for u in us]
        for l, u in zip(f.loops, us):
            l[uv].uv = (u, (max(-1.0, min(1.0, l.vert.co.z)) + 1) / 2 * 0.96 + 0.02)
    for v in bm.verts:
        v.co = esc(dobra(v.co))
    # moldura dourada em V: faixa grossa assentada na borda da abertura
    ordem = [v for v, a in sorted(ang.items(), key=lambda kv: kv[1])]
    Q = C + Vector((0, -0.10, 0.0))
    I, O, I2 = [], [], []
    L = len(ordem)
    for i, v in enumerate(ordem):
        P = v.co.copy()
        n = (P - C).normalized()
        d = P - Q
        tg = (d - n * d.dot(n)).normalized()
        w = 0.026
        vi = bm.verts.new(P - tg * 0.003 + n * 0.010)
        vo = bm.verts.new(P + tg * w + n * 0.003)
        v2 = bm.verts.new(P - n * 0.012 - tg * 0.003)
        I.append(vi); O.append(vo); I2.append(v2)
    for i in range(L - 1):
        t0, t1 = i / (L - 1), (i + 1) / (L - 1)
        for quad, uvs in (
            ([I[i], I[i + 1], O[i + 1], O[i]], [(0.18, t0), (0.18, t1), (0.92, t1), (0.92, t0)]),
            ([I2[i], I2[i + 1], I[i + 1], I[i]], [(0.02, t0), (0.02, t1), (0.18, t1), (0.18, t0)]),
        ):
            f = bm.faces.new(quad)
            f.material_index = 1
            # normal para fora
            f.normal_update()
            cen = f.calc_center_median()
            if f.normal.dot(cen - C) < 0:
                f.normal_flip()
            # UV por vertice (corrige a ordem dos loops apos o flip)
            mp = {vv: u for vv, u in zip(quad, uvs)}
            for l in f.loops:
                l[uv].uv = mp[l.vert]
    # casca interna escura (baixa resolucao) para o interior do capuz nao ficar vazado
    bm2 = bmesh.new()
    bmesh.ops.create_uvsphere(bm2, u_segments=16, v_segments=9, radius=1.0)
    mor2 = [f for f in bm2.faces if (f.calc_center_median().y < -0.15 and dentro(f.calc_center_median().x, f.calc_center_median().z)) or f.calc_center_median().z < -0.38]
    bmesh.ops.delete(bm2, geom=mor2, context="FACES")
    mp_v = {}
    for v in bm2.verts:
        mp_v[v] = bm.verts.new(esc(dobra(v.co, folds=False), 0.90))
    for f in bm2.faces:
        nf = bm.faces.new([mp_v[v] for v in f.verts])
        nf.material_index = 2
        nf.normal_flip()  # normais para dentro (para o rosto)
        for l in nf.loops:
            l[uv].uv = (0.5, 0.5)
    bm2.free()
    # normais da casca externa para fora (a esfera ja sai assim); recalcula so as faces do capuz
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f.material_index == 0])
    me = bpy.data.meshes.new("SK_Archer_Capuz")
    bm.to_mesh(me); bm.free()
    return me


# ---------- mascara ----------
SS = [0.0, 0.07, 0.14, 0.22, 0.30, 0.40, 0.52, 0.64, 0.76, 0.87, 0.95, 1.0]
# secao transversal (xn, nn): aresta, asa, CRISTA, asa, aresta, verso x3
SECAO = [(1.0, 0.0), (0.62, 0.42), (0.0, 1.45), (-0.62, 0.42), (-1.0, 0.0), (-0.55, -0.55), (0.0, -0.75), (0.55, -0.55)]


def lerp_tab(tab, x):
    for (a, va), (b, vb) in zip(tab, tab[1:]):
        if x <= b:
            return va + (vb - va) * (x - a) / (b - a)
    return tab[-1][1]


def perfil(s):
    pts_w = [(0, 0.044), (0.07, 0.068), (0.14, 0.078), (0.24, 0.070), (0.34, 0.048), (0.46, 0.030), (0.60, 0.022), (0.80, 0.013), (1.0, 0.002)]
    pts_d = [(0, 0.012), (0.15, 0.018), (0.35, 0.024), (0.60, 0.020), (0.85, 0.012), (1.0, 0.004)]
    w, dd = lerp_tab(pts_w, s), lerp_tab(pts_d, s)
    y = -0.086 - 0.108 * s ** 1.7
    z = 1.388 - 0.205 * s - 0.01 * math.sin(s * math.pi)
    return w, dd, y, z


def ponto(s, k, folga=0.0):
    w, dd, y, z = perfil(s)
    xn, nn = SECAO[k]
    if k in (1, 3) and 0.10 < s < 0.34:   # orbitas fundas
        nn *= 0.30
    x = (w + folga) * xn
    s2 = min(1.0, s + 0.01)
    _, _, y2, z2 = perfil(s2)
    t = Vector((0, y2 - y, z2 - z)).normalized()
    fw = Vector((0, -t.z, t.y))
    if fw.y > 0:
        fw = -fw
    wrap = 0.028 * (x / 0.07) ** 2 * (1 - smoothstep(0.25, 0.55, s))
    return Vector((x, y, z)) + fw * ((dd + folga) * nn) + Vector((0, wrap, 0))


def tubo(bm, uv, pts, r, lados, mi):
    aneis = []
    for i, p in enumerate(pts):
        a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
        t = (b - a).normalized()
        ref = Vector((0, 1, 0)) if abs(t.y) < 0.9 else Vector((1, 0, 0))
        e1 = t.cross(ref).normalized(); e2 = t.cross(e1)
        aneis.append([bm.verts.new(p + (e1 * math.cos(2 * math.pi * k / lados) + e2 * math.sin(2 * math.pi * k / lados)) * r) for k in range(lados)])
    n = len(aneis) - 1
    for i in range(n):
        for k in range(lados):
            q = [aneis[i][k], aneis[i][(k + 1) % lados], aneis[i + 1][(k + 1) % lados], aneis[i + 1][k]]
            f = bm.faces.new(q); f.material_index = mi
            uvs = [(0.3 + 0.4 * (k % 2), i / n), (0.3 + 0.4 * (k % 2), i / n), (0.3 + 0.4 * (k % 2), (i + 1) / n), (0.3 + 0.4 * (k % 2), (i + 1) / n)]
            for l, q_v in zip(f.loops, q):
                l[uv].uv = (0.5, i / n if q_v in aneis[i] else (i + 1) / n)


def mascara():
    bm = bmesh.new()
    N = len(SECAO)
    uv = bm.loops.layers.uv.verify()
    aneis = [[bm.verts.new(ponto(s, k)) for k in range(N)] for s in SS]
    for i in range(len(SS) - 1):
        for k in range(N):
            q = [aneis[i][k], aneis[i][(k + 1) % N], aneis[i + 1][(k + 1) % N], aneis[i + 1][k]]
            uvs = [(k / N, 1 - SS[i]), ((k + 1) / N, 1 - SS[i]), ((k + 1) / N, 1 - SS[i + 1]), (k / N, 1 - SS[i + 1])]
            f = bm.faces.new(q); f.material_index = 0
            for l, u in zip(f.loops, uvs):
                l[uv].uv = u
    f = bm.faces.new(aneis[0][::-1]); f.material_index = 0
    for l in f.loops: l[uv].uv = (0.25, 1.0)
    f = bm.faces.new(aneis[-1]); f.material_index = 0
    for l in f.loops: l[uv].uv = (0.25, 0.0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    # moldura dourada grossa: ponta -> borda esq. -> arco da testa -> borda dir. -> ponta
    esq = [ponto(s, 4, 0.004) for s in SS[::-1]]
    dir_ = [ponto(s, 0, 0.004) for s in SS]
    arco = [ponto(0.0, 3, 0.004), ponto(0.0, 2, 0.004), ponto(0.0, 1, 0.004)]
    tubo(bm, uv, esq + arco + dir_, 0.0058, 3, 1)
    me = bpy.data.meshes.new("SK_Archer_Mascara")
    bm.to_mesh(me); bm.free()
    return me


# ---------- rosto (pele, olhos, palpebras, lenco, cabelo) ----------
def uvq(l, uv, u, v, quad=0):
    ox, oy = [(0, 0.5), (0.5, 0.5), (0, 0), (0.5, 0)][quad]
    l[uv].uv = (ox + u * 0.5 * 0.96 + 0.02, oy + v * 0.5 * 0.96 + 0.02)


def rosto():
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    # pele (ovoide atras da mascara) - slot 0
    g = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=1.0)
    for v in g["verts"]:
        v.co = Vector((v.co.x * 0.088, v.co.y * 0.084, v.co.z * 0.085)) + Vector((0, 0.0, 1.292))
    for f in bm.faces:
        f.material_index = 0
        for l in f.loops: uvq(l, uv, 0.5, 0.5, 2)
    # olhos amendoados (leque) + palpebra superior
    for sx in (-1, 1):
        a, b = 0.0270, 0.0130
        ce = Vector((0.057 * sx, -0.082, 1.310))
        tilt = math.radians(9) * sx  # canto externo mais alto
        def P(t):
            x = a * math.cos(t)
            z = b * math.sin(t) * (1 - 0.30 * abs(math.cos(t)))
            xr = x * math.cos(tilt) - z * math.sin(tilt)
            zr = x * math.sin(tilt) + z * math.cos(tilt)
            return Vector((xr, 0.0, zr)) + ce, (0.5 + 0.5 * x / a, 0.5 + 0.5 * z / b)
        cent = bm.verts.new(ce + Vector((0, -0.005, 0)))
        ring = []
        for j in range(12):
            pos, uvp = P(2 * math.pi * j / 12)
            ring.append((bm.verts.new(pos), uvp))
        cuv = (0.5, 0.5)
        for j in range(12):
            v0, u0 = ring[j]; v1, u1 = ring[(j + 1) % 12]
            q = [cent, v1, v0]
            f = bm.faces.new(q); f.material_index = 1
            f.normal_update()
            if f.normal.y > 0:
                f.normal_flip()
            mp = {cent: cuv, v0: u0, v1: u1}
            for l in f.loops: l[uv].uv = mp[l.vert]
        # palpebra superior: faixa escura acima do contorno (t em 0..pi)
        top = []
        for j in range(7):
            t = math.pi * j / 6
            pos, _ = P(t)
            top.append((bm.verts.new(pos + Vector((0, -0.002, 0.0))), bm.verts.new(pos + Vector((0, -0.006, 0.0075 * math.sin(t) + 0.002)))))
        for j in range(6):
            q = [top[j][0], top[j + 1][0], top[j + 1][1], top[j][1]]
            f = bm.faces.new(q); f.material_index = 2
            f.normal_update()
            if f.normal.y > 0:
                f.normal_flip()
            for l in f.loops: uvq(l, uv, 0.5, 0.5, 3)
    # lenco: 3 rolos de pano em volta da boca e do nariz (slot 2)
    cols, rows = 10, 9
    gv = []
    for j in range(rows + 1):
        t = j / rows
        fila = []
        for i in range(cols + 1):
            span = 115 - 32 * t
            a = math.radians(-span + 2 * span * i / cols)
            fr = math.cos(a) ** 2
            ztopo = 1.282 + 0.028 * fr - 0.020 * (1 - fr)
            zbase = 1.215 - 0.050 * fr + 0.012 * math.sin(i * 2.3)
            z = ztopo + (zbase - ztopo) * t
            r = 0.090 + 0.012 * t + 0.011 * abs(math.sin(3 * math.pi * t)) + 0.003 * math.sin(i * 1.7 + j)
            fila.append(bm.verts.new(Vector((math.sin(a) * r * 1.02, -math.cos(a) * r * 0.96, z))))
        gv.append(fila)
    for j in range(rows):
        for i in range(cols):
            q = [gv[j][i], gv[j][i + 1], gv[j + 1][i + 1], gv[j + 1][i]]
            f = bm.faces.new(q); f.material_index = 2
            for l, (u, v) in zip(f.loops, [(i / cols, 1 - j / rows), ((i + 1) / cols, 1 - j / rows), ((i + 1) / cols, 1 - (j + 1) / rows), (i / cols, 1 - (j + 1) / rows)]):
                uvq(l, uv, u, v, 0)
    # mechas de cabelo: fitas curvas e pequenas nas laterais da testa (slot 2)
    mechas = [(-1, 0.088, 1.386, 0.060, 0.012), (-1, 0.100, 1.364, 0.055, 0.018),
              (1, 0.090, 1.388, 0.050, -0.010), (1, 0.102, 1.360, 0.062, -0.016)]
    for sx, x0, z0, comp, curva in mechas:
        vs = []
        for k in range(4):
            t = k / 3
            p = Vector((sx * (x0 + 0.010 * t + curva * math.sin(t * 3.0)), -0.084 + 0.020 * t, z0 - comp * t))
            w = 0.0130 * [0.40, 1.0, 0.70, 0.12][k]
            vs.append((bm.verts.new(p + Vector((-w, 0, 0))), bm.verts.new(p + Vector((w, 0, 0)))))
        for k in range(3):
            f = bm.faces.new([vs[k][0], vs[k][1], vs[k + 1][1], vs[k + 1][0]])
            f.material_index = 2
            for l, (u, v) in zip(f.loops, [(0.2, k / 3), (0.8, k / 3), (0.8, (k + 1) / 3), (0.2, (k + 1) / 3)]):
                uvq(l, uv, u, v, 1)
    me = bpy.data.meshes.new("SK_Archer_Rosto")
    bm.to_mesh(me); bm.free()
    return me


# ---------- montagem ----------
def objeto(me, nome, arm, mats):
    ob = bpy.data.objects.new(nome, me)
    bpy.context.scene.collection.objects.link(ob)
    for m in mats:
        me.materials.append(m)
    vg = ob.vertex_groups.new(name="Head")
    vg.add([v.index for v in me.vertices], 1.0, "REPLACE")
    ob.parent = arm
    md = ob.modifiers.new("Armature", "ARMATURE"); md.object = arm
    return ob


def main():
    c.limpar()
    c.importar(f"{c.FINAL}/SK_Archer_Head_Starter.fbx")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    antigas = [o for o in bpy.data.objects if o.type == "MESH"]
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    arm.animation_data_clear()
    c.aplicar_rotacao([arm] + antigas)
    for o in antigas:
        bpy.data.objects.remove(o)
    m_capuz = mat("M_Arqueiro_Capuz", tex="T_Capuz_BC.png", normal="T_Capuz_N.png", rough=0.93, dupla=True)
    m_ouro = mat("M_Arqueiro_CapuzOuro", tex="T_Ouro_BC.png", rough=0.55, dupla=True)
    m_int = mat("M_Arqueiro_CapuzInterior", cor=(0.022, 0.040, 0.022, 1), rough=0.95, dupla=True)
    m_masc = mat("M_Arqueiro_Mascara", tex="T_Mascara_BC.png", normal="T_Mascara_N.png", rough=0.6)
    m_det = mat("M_Arqueiro_CapuzDetalhe", tex="T_CapuzDetalhe_BC.png", rough=0.9, dupla=True)
    m_olho = mat("M_Arqueiro_OlhoVerde", tex="T_Olho_BC.png", rough=0.25, emis_tex=True, emis=0.9)
    ob = objeto(hood(), "SK_Archer_Capuz", arm, [m_capuz, m_ouro, m_int])
    for p in ob.data.polygons:
        p.use_smooth = (p.material_index != 1)
    mk = objeto(mascara(), "SK_Archer_Mascara", arm, [m_masc, m_ouro])
    for p in mk.data.polygons:
        p.use_smooth = (p.material_index == 0)
    ro = objeto(rosto(), "SK_Archer_Rosto", arm, [m_det, m_olho, m_det])
    for p in ro.data.polygons:
        p.use_smooth = True
    tris = 0
    for o in (ob, mk, ro):
        t = sum(len(p.vertices) - 2 for p in o.data.polygons)
        print("TRIS", o.name, t); tris += t
    print("TRIS_TOTAL", tris)
    vs = [v.co for o in (ob, mk, ro) for v in o.data.vertices]
    print("BOUNDS", [round(min(v[i] for v in vs), 3) for i in range(3)], [round(max(v[i] for v in vs), 3) for i in range(3)])
    c.proporcao.aplicar(arm, [ob, mk, ro])   # mesma deformacao chibi do corpo: a cabeca maior leva o capuz junto
    c.exportar("Arqueiro_Capuz.glb", [arm, ob, mk, ro])


main()
