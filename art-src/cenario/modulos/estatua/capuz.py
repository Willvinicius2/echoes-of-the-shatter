"""PARTE capuz: capuz encapuzado, rosto de máscara de pedra, drapeado nas costas e filete de ouro.
A casca do capuz é UM sólido: união EXACT de (casca externa + lâmina do drapeado + rolo da borda), menos a cavidade côncava,
mais a máscara do rosto encaixada no fundo (embutida na parede, sem faces coincidentes), menos três planos de fratura na ponta.
O material 'vazio' só pinta uma pequena região do teto/fundo da cavidade (faces da própria casca)."""
import bpy, bmesh, math
from mathutils import Vector

# perfil da casca externa: (z, rx, ry, cy). A ponta se inclina para trás e é quebrada depois.
PERFIL = [(2.48, 0.205, 0.195, 0.00), (2.58, 0.230, 0.215, 0.01), (2.70, 0.255, 0.235, 0.03), (2.82, 0.268, 0.250, 0.035),
          (2.94, 0.238, 0.240, 0.040), (3.04, 0.185, 0.205, 0.010), (3.14, 0.120, 0.150, -0.05), (3.26, 0.060, 0.090, -0.10), (3.40, 0.015, 0.030, -0.16)]
ZC, A_ROLO, B_ROLO = 2.76, 0.188, 0.232      # centro e semieixos do contorno da abertura (plano XZ)

def _lp(tab, z):
    if z <= tab[0][0]: return tab[0][1]
    for (z0, v0), (z1, v1) in zip(tab, tab[1:]):
        if z <= z1: return v0 + (v1 - v0) * (z - z0) / (z1 - z0)
    return tab[-1][1]

def _interp(z, i):
    return _lp([(p[0], p[i]) for p in PERFIL], z)

def _zig(t):
    """Onda triangular de vinco agudo, de -1 a 1."""
    return abs((t % 1.0) * 2 - 1) * 2 - 1

def _tmp(nome, bm):
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(nome, me); bpy.context.collection.objects.link(o); return o

def _bool(a, b, op, solver='EXACT'):
    print("  antes", len(a.data.polygons), "cutter", len(b.data.polygons), "nm cutter", _nonmanifold(b)); m = a.modifiers.new("b", 'BOOLEAN'); m.operation = op; m.solver = solver; m.object = b
    bpy.context.view_layer.objects.active = a; bpy.ops.object.modifier_apply(modifier="b")
    bpy.data.objects.remove(b, do_unlink=True)
    print("  bool", op, len(a.data.polygons), "nm", _nonmanifold(a))

def _nonmanifold(o):
    bm = bmesh.new(); bm.from_mesh(o.data); n = sum(1 for e in bm.edges if not e.is_manifold); bm.free(); return n

def _casca(L):
    """Casca externa do capuz: loft fechado com vincos laterais/traseiros (dobras agudas) e ponta torta."""
    N = 44; rings = []
    zs = [2.48 + k * 0.03 for k in range(31)]
    for z in zs:
        rx, ry, cy = _interp(z, 1), _interp(z, 2), _interp(z, 3)
        pts = []
        for i in range(N):
            t = i / N * math.tau; c, s = math.cos(t), math.sin(t)
            atras = max(0.0, (1 - s) / 2)                       # 0 na frente, 1 nas costas
            amp = 0.045 / rx * min(1.0, (3.15 - z) / 0.45 + 0.3) * atras ** 0.6
            f = 1 + amp * (0.6 * _zig(t / math.tau * 9 + 0.15 + 0.5 * math.sin(z * 5)) + 0.4 * _zig(t / math.tau * 3 + 0.4))
            pts.append(Vector((rx * f * c, cy + ry * f * s, z)))
        rings.append(pts)
    return L.loft(rings)

def _lamina(L):
    """Drapeado caindo nas costas e ombros: lâmina grossa com pregas em vinco agudo e barra recortada."""
    N, R = 64, 10; ph0, ph1 = math.radians(-90 - 84), math.radians(-90 + 84)
    perfil_o = [(2.14, (0.43, 0.30)), (2.40, (0.44, 0.27)), (2.62, (0.335, 0.25)), (2.74, (0.20, 0.17)), (2.92, (0.15, 0.12))]
    esp = 0.075
    def rr(z, k): return _lp([(p[0], p[1][k]) for p in perfil_o], z)
    zb = []
    for j in range(N + 1):
        u = j / N * 7.0; ip = int(u); r = L.rng(ip + 11).random()
        zb.append(2.10 + 0.17 * r * r + 0.09 * (1 - (u - ip)) * (0.4 + r))
    top = 2.90
    bm = bmesh.new(); ext = []; inn = []
    for j in range(N + 1):
        ph = ph0 + (ph1 - ph0) * j / N; c, s = math.cos(ph), math.sin(ph); ce, ci = [], []
        for k in range(R + 1):
            z = zb[j] + (top - zb[j]) * k / R
            fo = (z - 2.14) / 0.8
            amp = (max(0.0, 0.07 * (1 - fo * 0.9)) + 0.010) / rr(z, 0)
            f = 1 + amp * (0.65 * _zig(ph / math.tau * 11 + 0.2) + 0.35 * _zig(ph / math.tau * 5.5 + 0.7 + z * 0.8))
            ro_x, ro_y = rr(z, 0) * f, rr(z, 1) * f
            ce.append(bm.verts.new(Vector((ro_x * c, ro_y * s, z))))
            ci.append(bm.verts.new(Vector(((ro_x - esp) * c, (ro_y - esp) * s, z))))
        ext.append(ce); inn.append(ci)
    for j in range(N):
        for k in range(R):
            bm.faces.new((ext[j][k], ext[j + 1][k], ext[j + 1][k + 1], ext[j][k + 1]))
            bm.faces.new((inn[j][k], inn[j][k + 1], inn[j + 1][k + 1], inn[j + 1][k]))
        bm.faces.new((ext[j][0], inn[j][0], inn[j + 1][0], ext[j + 1][0]))
        bm.faces.new((ext[j][R], ext[j + 1][R], inn[j + 1][R], inn[j][R]))
    for k in range(R):
        bm.faces.new((ext[0][k], ext[0][k + 1], inn[0][k + 1], inn[0][k]))
        bm.faces.new((ext[N][k], inn[N][k], inn[N][k + 1], ext[N][k + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return bm

def _y_frente(x, z):
    rx, ry, cy = _interp(z, 1), _interp(z, 2), _interp(z, 3)
    return cy + ry * math.sqrt(max(0.0, 1 - (x / rx) ** 2))

def _caminho(a=A_ROLO, b=B_ROLO, n=40):
    """Contorno da abertura sobre a superfície frontal do capuz (ponto, normal aproximada)."""
    pts = []
    for i in range(n):
        t = i / n * math.tau; st = math.sin(t)
        x = a * math.cos(t) * (1 - 0.30 * max(0.0, st) ** 1.5 + 0.10 * max(0.0, -st)); z = ZC + b * st * (1.06 if st > 0 else 0.95)
        pts.append((Vector((x, _y_frente(x, z) + 0.02 + 0.03 * max(0.0, st), z)), Vector((x / a * 0.6, 0.8, (z - ZC) / b * 0.6)).normalized()))
    return pts

def _raio_rolo(t):
    return 0.044 + 0.012 * abs(math.cos(t)) + 0.010 * max(0.0, -math.sin(t)) - 0.006 * max(0.0, math.sin(t)) + 0.009 * _zig(t / math.tau * 9 + 0.25)

def _tubo(centros, raios, fechado=True, seg=8, achatar=1.0):
    """Tubo varrido ao longo de uma curva (rolo de tecido ou filete). Seção levemente achatada."""
    bm = bmesh.new(); n = len(centros); an = []
    for i, c in enumerate(centros):
        t = (centros[(i + 1) % n] - centros[i - 1]).normalized() if fechado else (centros[min(i + 1, n - 1)] - centros[max(i - 1, 0)]).normalized()
        sd = t.cross(Vector((0, 1, 0)))
        if sd.length < 1e-4: sd = Vector((1, 0, 0))
        sd.normalize(); up2 = sd.cross(t).normalized()
        an.append([bm.verts.new(c + (sd * math.cos(k / seg * math.tau) + up2 * math.sin(k / seg * math.tau) * achatar) * raios[i]) for k in range(seg)])
    for i in range(n if fechado else n - 1):
        a, b = an[i], an[(i + 1) % n]
        for k in range(seg): bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    if not fechado:
        bm.faces.new(an[0][::-1]); bm.faces.new(an[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return bm

def _rolo():
    """Rolo grosso de tecido em volta do rosto: espessura variável (mais grosso nas laterais e embaixo)."""
    cam = _caminho(n=44); cs, rs = [], []
    for i, (p, nrm) in enumerate(cam):
        cs.append(p + nrm * 0.012); rs.append(_raio_rolo(i / len(cam) * math.tau))
    return _tubo(cs, rs, True, 8, 0.80)

def _cavidade(L):
    """Cavidade côncava contínua (elipsoide) que vara a frente do capuz."""
    cx, cy, cz, rx, ry, rz = 0.0, 0.185, ZC, 0.172, 0.235, 0.228
    rings = []
    for k in range(1, 13):
        a = -math.pi / 2 + k / 13 * math.pi; zz = cz + rz * math.sin(a); f = math.cos(a)
        rings.append([Vector((cx + rx * f * math.cos(i / 26 * math.tau), cy + ry * f * math.sin(i / 26 * math.tau), zz)) for i in range(26)])
    return L.loft(rings)

DY = 0.07   # avanço da máscara em y (rosto mais perto da abertura, para pegar luz)

def _mascara(L):
    """Máscara de pedra em planos vivos (tabela feita à mão): queixo, boca, nariz em cunha, maçãs, órbitas fundas, arcada e testa.
    As bordas laterais (x=0.17) ficam enterradas na parede da cavidade: o rosto nasce da casca, sem folga preta ao redor."""
    xs = [0.0, 0.035, 0.07, 0.105, 0.14, 0.17]
    linhas = [(2.55, [.09, .09, .08, .07, .05, .04]), (2.60, [.15, .145, .13, .11, .09, .07]), (2.64, [.14, .135, .125, .105, .09, .07]),
              (2.68, [.115, .115, .11, .10, .085, .07]), (2.72, [.13, .13, .125, .115, .10, .08]), (2.76, [.19, .16, .14, .15, .12, .09]),
              (2.80, [.21, .17, .12, .14, .115, .09]), (2.84, [.17, .12, .06, .09, .10, .085]), (2.88, [.16, .14, .13, .17, .14, .10]),
              (2.92, [.17, .17, .165, .165, .14, .10]), (2.97, [.15, .15, .145, .14, .12, .09]), (3.00, [.10, .10, .10, .09, .08, .07])]
    yb = -0.13; rings = []
    esc = [0.40, 0.46, 0.55, 0.62, 0.78, 0.92, 0.88, 0.92, 1.0, 0.95, 0.80, 0.55]   # contorno do rosto: queixo estreito, maçãs e arcada largas
    for (z, ys), e in zip(linhas, esc):
        ys = [y + DY for y in ys]; xe = [x * e for x in xs]
        fr = [Vector((-x, y, z)) for x, y in zip(xe[:0:-1], ys[:0:-1])] + [Vector((x, y, z)) for x, y in zip(xe, ys)]
        rings.append(fr + [Vector((xe[-1], yb, z)), Vector((-xe[-1], yb, z))])
    return L.loft(rings)

def _corta(o, ponto, normal):
    """Corte plano exato por bisect (remove o lado de cima do plano e tampa com uma face plana: fratura facetada)."""
    bm = bmesh.new(); bm.from_mesh(o.data); n = Vector(normal).normalized()
    r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=Vector(ponto), plane_no=n, clear_outer=True, clear_inner=False)
    bor = [e for e in bm.edges if e.is_boundary]
    if bor: bmesh.ops.contextual_create(bm, geom=bor)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free(); print("  corte", len(o.data.polygons), "nm", _nonmanifold(o))

CORTES = [((0.02, -0.08, 3.12), (0.85, -0.20, 1.0)), ((0.02, -0.08, 3.115), (-0.75, -0.15, 1.0)), ((0.02, -0.08, 3.13), (0.05, -0.80, 1.0)),
          ((0.0, -0.06, 3.12), (0.12, 0.30, 1.0))]

def _z_corte(p):
    """Altura do conjunto dos planos de fratura no ponto (x, y)."""
    zs = []
    for q, n in CORTES:
        n = Vector(n); zs.append(q[2] - (n.x * (p.x - q[0]) + n.y * (p.y - q[1])) / n.z)
    return min(zs)

PERFIL_OURO = [(-0.016, -0.012), (0.016, -0.012), (0.016, 0.001), (0.0105, 0.0085), (-0.0105, 0.0085), (-0.016, 0.001)]   # (lado, altura): trapézio chanfrado

def _perfil_tubo(centros, nrms, perfil, fechado, esc=1.0, fundo=0.0):
    """Varre um perfil (lado, altura) ao longo da curva; esc alarga o perfil e fundo o desce (para a canaleta)."""
    bm = bmesh.new(); n = len(centros); an = []
    for i, c in enumerate(centros):
        t = (centros[(i + 1) % n] - centros[i - 1]).normalized() if fechado else (centros[min(i + 1, n - 1)] - centros[max(i - 1, 0)]).normalized()
        nr = nrms[i]; sd = t.cross(nr).normalized(); up = sd.cross(t).normalized()
        an.append([bm.verts.new(c + sd * (a * esc) + up * (h * esc + (fundo if h < 0 else 0.0))) for a, h in perfil])
    m = len(perfil)
    for i in range(n if fechado else n - 1):
        a, b = an[i], an[(i + 1) % n]
        for k in range(m): bm.faces.new((a[k], a[(k + 1) % m], b[(k + 1) % m], b[k]))
    if not fechado: bm.faces.new(an[0][::-1]); bm.faces.new(an[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return bm

def _crista(n=64):
    cam = _caminho(a=A_ROLO, b=B_ROLO, n=n); cs, ns = [], []
    for i, (p, nrm) in enumerate(cam):
        r = _raio_rolo(i / n * math.tau); cs.append(p + nrm * (0.012 + r * 0.8)); ns.append(nrm)
    return cs, ns

def _canaleta():
    """Canaleta contínua na crista do rolo, onde a moldura de ouro assenta."""
    cs, ns = _crista(); return _perfil_tubo(cs, ns, [(a, h + (0.02 if h > 0 else 0)) for a, h in PERFIL_OURO], True, 1.12)

def _moldura_ouro():
    """Moldura de ouro com espessura e perfil chanfrado, embutida na canaleta; faltam trechos (falhas) onde a canaleta fica vazia."""
    cs, ns = _crista(); n = len(cs); out = []; seg = []
    faltas = set(range(5, 8)) | {23, 24} | set(range(37, 40)) | set(range(51, 53)) | {60}
    def fecha():
        if len(seg) >= 3:
            ci = [c for c, _ in seg]; ni = [q for _, q in seg]; out.append(_perfil_tubo(ci, ni, PERFIL_OURO, False))
        seg.clear()
    for i in range(n):
        if i in faltas or cs[i].z > _z_corte(cs[i]) - 0.02: fecha()
        else: seg.append((cs[i], ns[i]))
    fecha(); return out

def _superficie(o, ang, z):
    """Ponto na casca do capuz (raio de fora para o eixo na altura z, ângulo ang em graus; 90 = frente)."""
    d = Vector((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0)); ori = Vector((0, 0.0, z)) + d * 0.6
    ok, loc, nor, idx = o.ray_cast(ori, -d)
    return (loc, nor) if ok else (None, None)

def _rachadura(o, ang0, z0, passos, rad=0.0055):
    """Sulco fino (prisma triangular) que desce em zigue-zague pela casca a partir da fratura."""
    cs, ns = [], []; ang = ang0; z = z0
    for k, (da, dz) in enumerate(passos):
        ang += da; z -= dz; loc, nor = _superficie(o, ang, z)
        if loc is None: continue
        cs.append(loc + nor * 0.002); ns.append(nor)
    if len(cs) < 3: return None
    return _perfil_tubo(cs, ns, [(-rad, -rad * 0.2), (rad, -rad * 0.2), (0.0, rad * 1.1)], False, 1.0, 0.0)

def _marca_corte(o):
    """Faces coplanares aos planos de fratura recebem o material 'corte' (índice 2)."""
    for p in o.data.polygons:
        ctr = p.center
        for q, n in CORTES:
            n = Vector(n).normalized()
            if abs(n.dot(ctr - Vector(q))) < 1e-4 and abs(n.dot(p.normal)) > 0.98: p.material_index = 2; break

def build(L):
    base = _tmp("capuz_casca", _casca(L))
    _bool(base, _tmp("capuz_lamina", _lamina(L)), "UNION")
    _bool(base, _tmp("capuz_rolo", _rolo()), 'UNION')
    _bool(base, _tmp("capuz_cav", _cavidade(L)), "DIFFERENCE")
    _bool(base, _tmp("capuz_rosto", _mascara(L)), 'UNION')
    for p, n in CORTES: _corta(base, p, n)
    print("capuz: não-manifold", _nonmanifold(base), "faces", len(base.data.polygons), "zmax", round(max(v.co.z for v in base.data.vertices), 3))
    base.data.materials.clear()
    for k in ('pedra', 'vazio', 'corte'): base.data.materials.append(L.M[k])
    _marca_corte(base)
    _bool(base, _tmp("capuz_canaleta", _canaleta()), "DIFFERENCE")
    for ang, z, passos in [(80, 3.02, [(-5, .06), (4, .08), (-6, .07), (3, .09), (-4, .08)]), (150, 3.0, [(5, .07), (-4, .08), (6, .09), (-3, .07)]),
                           (-30, 3.0, [(-4, .08), (5, .06), (-5, .1), (3, .08), (-3, .07)]), (260, 2.98, [(3, .07), (-5, .08), (4, .09)]),
                           (35, 2.95, [(4, .06), (-3, .07), (5, .06)])]:
        r = _rachadura(base, ang, z, passos)
        if r: _bool(base, _tmp("capuz_rach", r), "DIFFERENCE", "EXACT")
    L.bevel_obj(base, 0.007, 1, 38)
    print("  pós-bevel nm", _nonmanifold(base), len(base.data.polygons))
    # sombra funda e contínua: só as faces do teto da cavidade acima da testa
    for p in base.data.polygons:
        c = p.center
        if p.material_index == 0 and 3.0 < c.z < 3.03 and -0.06 < c.y < 0.05 and abs(c.x) < 0.1: p.material_index = 1
    for p in base.data.polygons:
        if p.material_index > 2: p.material_index = 0
    base.data.materials.clear()
    for k in ('pedra', 'vazio', 'corte'): base.data.materials.append(L.M[k])
    L.objs.append(base)
    for i, bmo in enumerate(_moldura_ouro()): L.new_obj(f"capuz_ouro_{i}", bmo, "ouro")
    print("capuz:", L.stats(base))
