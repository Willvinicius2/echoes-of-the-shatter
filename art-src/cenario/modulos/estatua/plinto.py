"""PARTE plinto: pilar de pedra em 3 volumes escalonados (laje de base, fuste com cintas, capitel em degraus),
losango e filetes de ouro, cantos lascados por boolean EXACT, rachaduras e runas em baixo relevo (sulcos reais),
entulho de rochas angulares no canto frontal e um fragmento de capuz quebrado sobre o tampo."""
import bpy, bmesh, math
from mathutils import Vector, Matrix

# ---------- utilitários locais
_L = None   # lib (para os materiais M)

def _mk(bm, nome, mat="pedra"):
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    me.materials.append(_L.M[mat])
    o = bpy.data.objects.new(nome, me); bpy.context.collection.objects.link(o); return o

def _rotm(rot):
    return Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X')

def _caixa(c, d, rot=(0, 0, 0), nome="cx", mat="pedra"):
    """Caixa centrada em c, dimensões d, rotação euler."""
    bm = bmesh.new()
    m = Matrix.Translation(Vector(c)) @ _rotm(rot) @ Matrix.Diagonal((d[0], d[1], d[2], 1.0))
    bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    return _mk(bm, nome, mat)

def _bool(o, cortadores, op='DIFFERENCE'):
    """Boolean EXACT de o com uma lista de objetos (juntados antes); apaga os cortadores."""
    if not cortadores: return
    alvo = cortadores[0]
    if len(cortadores) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        for c in cortadores: c.select_set(True)
        bpy.context.view_layer.objects.active = alvo; bpy.ops.object.join()
    md = o.modifiers.new("b", 'BOOLEAN'); md.operation = op; md.solver = 'EXACT'; md.object = alvo; md.use_self = True; md.material_mode = 'TRANSFER'   # faces novas herdam o material do cortador (corte = fratura)
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier="b")
    bpy.data.objects.remove(alvo)

def _limpa(o, d=0.0004):
    """Solda vértices quase iguais (resíduo de boolean)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=d)
    bmesh.ops.dissolve_degenerate(bm, dist=d, edges=bm.edges)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.3), verts=bm.verts, edges=bm.edges, delimit={'MATERIAL'})
    bm.to_mesh(o.data); bm.free()

def _degen(o):
    """Dissolve só as faces de área quase nula deixadas pelo boolean (sem soldar sulcos)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.dissolve_degenerate(bm, dist=2e-5, edges=bm.edges)
    bm.to_mesh(o.data); bm.free()

def _dbg(o, t):
    bm = bmesh.new(); bm.from_mesh(o.data)
    print("dbg", t, len(bm.faces), "nm", sum(1 for e in bm.edges if not e.is_manifold), "deg", sum(1 for f in bm.faces if f.calc_area() < 1e-8)); bm.free()

def _uniao(objs):
    base = objs[0]
    for c in objs[1:]: _bool(base, [c], 'UNION')
    return base

def _lascas(R, o, pontos, tam, mat="corte"):
    """Cantos lascados: caixas giradas cortam os pontos dados (cantos/arestas)."""
    cs = []
    for p in pontos:
        s = tam * R.uniform(0.7, 1.3)
        cs.append(_caixa(Vector(p) + Vector((R.uniform(-.02, .02), R.uniform(-.02, .02), R.uniform(-.02, .02))),
                         (s, s * R.uniform(.7, 1.2), s * R.uniform(.7, 1.2)),
                         (R.uniform(0, 6.28), R.uniform(0, 6.28), R.uniform(0, 6.28)), "ch", mat))
    _bool(o, cs)

def _sulco(pts, origem, u, v, n, larg=0.011, prof=0.024):
    larg *= 1.45; prof *= 1.25   # sulcos finos porém legíveis a 8 m
    """Tiras finas de corte seguindo o plano (origem, eixos u,v, normal n): cortadores de um sulco poligonal."""
    cs = []
    for a, b in zip(pts, pts[1:]):
        pa = origem + u * a[0] + v * a[1]; pb = origem + u * b[0] + v * b[1]
        d = pb - pa; Lg = d.length
        if Lg < 1e-4: continue
        x = d.normalized(); y = n.cross(x).normalized()
        m = Matrix(((x.x, y.x, n.x, 0), (x.y, y.y, n.y, 0), (x.z, y.z, n.z, 0), (0, 0, 0, 1)))
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((pa + pb) / 2 - n * (prof * 0.5 - 0.004)) @ m @ Matrix.Diagonal((Lg + larg, larg, prof, 1)))
        cs.append(_mk(bm, "sl", "pedra"))
    return cs

def _hull(bm, vs):
    bmesh.ops.convex_hull(bm, input=vs)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')

def _rocha(R, c, raio, achat=0.65, n=13, rot=0.0):
    """Poliedro angular natural: casco convexo de pontos irregulares, achatado em cima."""
    bm = bmesh.new(); vs = []
    for i in range(n):
        th = R.uniform(0, 2 * math.pi); ph = math.acos(R.uniform(-1, 1)); r = raio * R.uniform(0.7, 1.15)
        vs.append(bm.verts.new((r * math.sin(ph) * math.cos(th) * R.uniform(.85, 1.25), r * math.sin(ph) * math.sin(th) * R.uniform(.8, 1.1), r * math.cos(ph) * achat)))
    _hull(bm, vs)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rot, 3, 'Z'))
    for v in bm.verts: v.co += Vector(c)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _mk(bm, "rocha")

def _lasca_grande(R, c, dim, rot):
    """Lasca plana caída do pilar: casca convexa achatada com faces de fratura."""
    bm = bmesh.new(); vs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (0, 1):
                vs.append(bm.verts.new((sx * dim[0] / 2 * R.uniform(.55, 1), sy * dim[1] / 2 * R.uniform(.6, 1), sz * dim[2] * R.uniform(.5, 1))))
    for _ in range(3):
        vs.append(bm.verts.new((R.uniform(-.5, .5) * dim[0], R.uniform(-.5, .5) * dim[1], dim[2] * R.uniform(.6, 1.1))))
    _hull(bm, vs)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rot[2], 3, 'Z') @ Matrix.Rotation(rot[0], 3, 'X'))
    for v in bm.verts: v.co += Vector(c)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _mk(bm, "lasca")

def _ponta_capuz(L, base):
    """Fragmento de capuz: casco cônico facetado (8 lados) curvado para trás, fratura inclinada em facetas."""
    n = 12; H = 0.36; ext_r = lambda t: 0.17 * (1 - t) ** 0.85 + 0.012
    def anel(r, t, z, ay=1.05):
        return [Vector((r * math.cos(2 * math.pi * i / n + .2) * 0.92, -0.10 * t ** 1.8 + r * math.sin(2 * math.pi * i / n + .2) * ay, z)) for i in range(n)]
    ext = _mk(L.loft([anel(ext_r(k / 6), k / 6, H * k / 6) for k in range(7)], True, True), "capuz_ext", "pedra")
    ints = _mk(L.loft([anel(max(0.004, ext_r(k / 6) - 0.05), k / 6, 0.05 + (H - 0.05) * k / 6 + 0.02) for k in range(7)], True, True), "capuz_int", "pedra")
    _bool(ext, [ints])
    _bool(ext, [_caixa((0.05, -0.02, 0.33), (0.5, 0.5, 0.2), (0.45, 0.35, 0.3), "f1"),
                _caixa((-0.12, 0.04, 0.29), (0.2, 0.3, 0.14), (-0.3, 0.5, 0.9), "f2")])
    for v in ext.data.vertices: v.co = v.co * 0.92 + Vector(base)
    return ext

def _quebra(R, o, n=1):
    """Fratura de uma rocha: plano de corte inclinado (face clara de material corte) arrancando um canto."""
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]; ctr = sum(bb, Vector()) / 8
    ext = max((max(p[i] for p in bb) - min(p[i] for p in bb)) for i in range(3))
    cs = []
    for _ in range(n):
        d = Vector((R.uniform(-1, 1), R.uniform(-1, 1), R.uniform(0.2, 1.0))).normalized()
        q = d.to_track_quat('Z', 'Y')
        c = ctr + d * ext * R.uniform(0.28, 0.4)
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c + d * ext) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((ext * 3, ext * 3, ext * 2, 1)))
        cs.append(_mk(bm, "qb", "corte"))
    _bool(o, cs)

def _portoes(L):
    """Portões de geometria: manifold, volume positivo, faces degeneradas, auto-interseção."""
    from mathutils.bvhtree import BVHTree
    for o in L.objs:
        if not o.name.startswith("plinto"): continue
        bm = bmesh.new(); bm.from_mesh(o.data)
        nm = sum(1 for e in bm.edges if not e.is_manifold); deg = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
        vol = bm.calc_volume(signed=True)
        bm.faces.ensure_lookup_table(); bvh = BVHTree.FromBMesh(bm); ov = sum(1 for a, b in bvh.overlap(bvh) if a < b and not (set(v.index for v in bm.faces[a].verts) & set(v.index for v in bm.faces[b].verts)))
        print("gate", o.name, "nao-manifold", nm, "degeneradas", deg, "volume", round(vol, 4), "interseccoes", ov)
        bm.free()

# ---------- construção
def build(L):
    global _L
    _L = L
    R = L.rng(7)
    SX, SY = 1.22, 1.14   # alarga o pilar (tampo ~1.30 x 1.13) para o manto esguio caber com folga
    ZP = L.ZP
    fx = Vector((1, 0, 0)); fz = Vector((0, 0, 1)); ny = Vector((0, 1, 0))
    # 1) laje de base: 1.30, topo em z=0.20, torta e afundada no chão
    laje = _caixa((0, 0, 0.06), (L.PLINTO_W, 1.24, 0.28), (0, 0, 0), "laje")   # montada reta; gira no fim
    # 2) fuste 0.95 (z 0.20..0.75) com cintas em relevo; 3) capitel em degraus (1.10 e 1.02)
    fuste = _caixa((0, 0, 0.475), (0.95, 0.93, 0.58), (0, 0, 0.012), "fuste")
    cintas = [_caixa((0, 0, 0.255), (1.03, 1.01, 0.12), (0, 0, 0.012), "c1"),
              _caixa((0, 0, 0.318), (0.99, 0.97, 0.05), (0, 0, 0.012), "c1b"),
              _caixa((0, 0, 0.69), (1.01, 0.99, 0.09), (0, 0, 0.012), "c2")]
    cap0 = _caixa((0, 0, 0.765), (0.99, 0.97, 0.04), (0, 0, 0.012), "cap0")      # gola
    cap1 = _caixa((0, 0, 0.795), (1.10, 1.08, 0.06), (0, 0, 0.012), "cap1")      # moldura larga
    capf = _caixa((0, 0, 0.84), (1.04, 1.02, 0.04), (0, 0, 0.012), "capf")       # filete
    cap2 = _caixa((0, 0, 0.88), (1.00, 0.96, 0.05), (0, 0, 0.012), "cap2")       # tampo
    partes = [fuste] + cintas + [cap0, cap1, capf, cap2]
    for p in partes: L.bevel_obj(p, 0.014, 4, 30)      # chanfro real em cada volume antes da união
    pilar = _uniao(partes)
    _bool(pilar, [_caixa((0, 0, ZP + 0.5), (3, 3, 1.0), (0, 0, 0), "topo", "pedra")])   # topo plano exatamente em ZP
    # lascas nos cantos (a área central do tampo fica intacta)
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            if R.random() < 0.85: pts.append((sx * 0.52, sy * 0.49, ZP))
            if R.random() < 0.6: pts.append((sx * 0.56, sy * 0.54, 0.75))
            pts.append((sx * 0.51, sy * 0.49, 0.20))
    _lascas(R, pilar, pts, 0.16)
    _lascas(R, pilar, [(0.35, 0.51, 0.90), (-0.52, -0.15, 0.80), (0.0, -0.51, 0.82), (0.52, 0.2, 0.30), (-0.2, 0.52, 0.30)], 0.07)
    _limpa(pilar, 0.00015)
    L.bevel_obj(laje, 0.016, 4, 30)
    _lascas(R, laje, [(0.65, 0.62, 0.20), (-0.65, 0.62, 0.20), (0.62, -0.62, 0.2), (-0.64, -0.6, 0.2), (0.0, 0.62, 0.20), (0.65, 0.1, 0.2), (-0.65, -0.1, 0.0)], 0.15)
    # juntas (3 lajes na frente, 2 nos lados) e rachaduras que atravessam a laje, em cima e na face
    W2, D2 = L.PLINTO_W / 2, 0.62; cl = []
    for x in (-0.22, 0.28):
        cl += _sulco([(x, -0.08), (x, 0.21)], Vector((0, D2, 0)), fx, fz, ny, 0.016, 0.03)
        cl += _sulco([(x, D2 + 0.01), (x + 0.01, 0.44)], Vector((0, 0, 0.20)), fx, ny, fz, 0.016, 0.03)
    for sx in (-1, 1):
        cl += _sulco([(0.08 * sx, -0.08), (0.08 * sx, 0.21)], Vector((sx * W2, 0, 0)), Vector((0, 1, 0)), fz, Vector((sx, 0, 0)), 0.016, 0.03)
        cl += _sulco([(W2 + 0.01, 0.08 * sx), (0.46, 0.08 * sx + 0.01)], Vector((0, 0, 0.20)) * 1 + Vector((0, 0, 0)), Vector((sx, 0, 0)), ny, fz, 0.016, 0.03)
    cl += _sulco([(0.05, 0.20), (0.09, 0.13), (0.06, 0.08), (0.13, 0.02), (0.11, -0.05)], Vector((0, D2, 0)), fx, fz, ny, 0.011, 0.022)
    cl += _sulco([(-0.48, 0.20), (-0.44, 0.12), (-0.50, 0.05)], Vector((0, D2, 0)), fx, fz, ny, 0.011, 0.022)
    cl += _sulco([(0.10, D2), (0.13, 0.56), (0.08, 0.51), (0.12, 0.47)], Vector((0, 0, 0.20)), fx, ny, fz, 0.011, 0.022)
    cl += _sulco([(-0.3, 0.20), (-0.36, 0.1), (-0.29, 0.02)], Vector((0.65, 0, 0)), Vector((0, 1, 0)), fz, fx, 0.011, 0.022)
    _bool(laje, cl)
    laje.data.transform(Matrix.Diagonal((SX, SY, 1.0, 1.0)))
    mrot = Matrix.Translation((0.015, -0.01, 0.0)) @ _rotm((0.012, -0.018, 0.045))   # torta e afundada
    laje.data.transform(mrot)

    # 4) sulcos reais: rachaduras, juntas (2 lajes por face), runas e encaixe do losango
    cs = []
    cs += _sulco([(0.18, 0.48), (0.2, 0.40), (0.27, 0.36), (0.25, 0.30), (0.32, 0.22), (0.30, 0.15)], Vector((0, 0.47, 0.2)), fx, fz, ny, 0.010, 0.02)
    cs += _sulco([(-0.40, 0.55), (-0.36, 0.50), (-0.41, 0.44), (-0.33, 0.36), (-0.37, 0.28), (-0.30, 0.20), (-0.33, 0.12)], Vector((0, 0.47, 0.2)), fx, fz, ny, 0.012, 0.022)
    cs += _sulco([(0.05, 0.50), (0.12, 0.44), (0.10, 0.40), (0.0, 0.33)], Vector((0.475, 0, 0.2)), Vector((0, 1, 0)), fz, Vector((1, 0, 0)), 0.010, 0.02) if False else []
    cs += _sulco([(-0.1, 0.5), (-0.15, 0.42), (-0.08, 0.36), (-0.14, 0.28), (-0.07, 0.2)], Vector((-0.478, 0, 0.2)), Vector((0, 1, 0)), fz, Vector((-1, 0, 0)), 0.011, 0.02)
    cs += _sulco([(0.3, 0.55), (0.25, 0.47), (0.33, 0.40), (0.2, 0.33), (0.26, 0.25)], Vector((0, -0.468, 0.2)), fx, fz, Vector((0, -1, 0)), 0.011, 0.02)
    cs += _sulco([(0.3, 0.52), (0.35, 0.47), (0.3, 0.42)], Vector((0, 0.5, 0.0)), fx, fz, ny, 0.010, 0.02) if False else []
    cs += _sulco([(-0.30, 0.55), (-0.33, 0.47), (-0.29, 0.42), (-0.36, 0.36)], Vector((0, 0.47, 0.2)), fx, fz, ny, 0.010, 0.02)
    cs += _sulco([(0.05, 0.0), (0.05, 0.55)], Vector((-0.478, 0, 0.2)), Vector((0, 1, 0)), fz, Vector((-1, 0, 0)), 0.016, 0.03)
    cs += _sulco([(-0.1, 0.0), (-0.1, 0.55)], Vector((0.478, 0, 0.2)), Vector((0, 1, 0)), fz, Vector((1, 0, 0)), 0.016, 0.03)
    cs += _sulco([(0.1, 0.0), (0.1, 0.55)], Vector((0, -0.468, 0.2)), fx, fz, Vector((0, -1, 0)), 0.016, 0.03)
    cs += _sulco([(-0.5, 0.0), (-0.42, 0.045), (-0.36, 0.02)], Vector((-0.2, 0.548, 0.75)), fx, fz, ny, 0.009, 0.02)
    glifos = [[[(0, 0), (0, 0.12)], [(0, 0.12), (0.06, 0.06)], [(0.06, 0.06), (0, 0)]],
              [[(0, 0), (0.07, 0.07)], [(0.07, 0.07), (0, 0.13)], [(0.07, 0), (0.07, 0.13)]],
              [[(0, 0), (0, 0.13)], [(0, 0.065), (0.07, 0.065)], [(0.07, 0), (0.07, 0.13)]],
              [[(0, 0.06), (0.04, 0.13)], [(0.04, 0.13), (0.08, 0.06)], [(0.04, 0), (0.04, 0.13)]]]
    for (px, uy, nx) in ((-0.478, Vector((0, 1, 0)), Vector((-1, 0, 0))), (0.478, Vector((0, 1, 0)), Vector((1, 0, 0)))):
        for i, gl in enumerate(glifos):
            for seg in gl:
                cs += _sulco([(a[0] + 0.14 * (i - 1.5) - 0.06, a[1] + 0.42) for a in seg], Vector((px, 0, 0)), uy, fz, nx, 0.011, 0.018)
    for i, gl in enumerate(glifos[:3]):
        for seg in gl:
            cs += _sulco([(a[0] + 0.15 * (i - 1.0) - 0.04, a[1] + 0.42) for a in seg], Vector((0, -0.468, 0)), fx, fz, Vector((0, -1, 0)), 0.011, 0.018)
    # rachaduras longas que cruzam cintas e fuste (atravessam vários blocos)
    cs += _sulco([(0.50, 0.58), (0.46, 0.50), (0.52, 0.43), (0.47, 0.36), (0.55, 0.28)], Vector((0, 0.47, 0.2)), fx, fz, ny, 0.010, 0.02)
    cs += _sulco([(-0.20, 0.60), (-0.26, 0.53), (-0.20, 0.47), (-0.28, 0.41), (-0.22, 0.30), (-0.27, 0.18)], Vector((0, 0.47, 0.2)), fx, fz, ny, 0.010, 0.02)
    cs += _sulco([(-0.05, 0.62), (-0.12, 0.58), (-0.2, 0.60)], Vector((0, 0.47, 0.2)), fx, fz, ny, 0.010, 0.02)
    cs += _sulco([(0.0, 0.0), (0.1, 0.05), (0.04, 0.10), (0.14, 0.16), (0.08, 0.22), (0.18, 0.28)], Vector((0, 0, 0.45)), Vector((0, 1, 0)), fz, Vector((1, 0, 0)), 0.010, 0.02) if False else []
    _bool(pilar, cs)
    pilar.data.transform(Matrix.Diagonal((SX, SY, 1.0, 1.0)))
    FY = 0.465 * SY; FX = 0.465 * SX   # faces do fuste (frente em y=FY)

    # 5) ouro: filetes com espessura e desgaste nas cintas e no capitel; losango entalhado em moldura
    ouro = []
    for z, y, ls in ((0.255, 0.516, [(-0.47, -0.30), (-0.25, -0.08), (-0.03, 0.16), (0.22, 0.47)]), (0.69, 0.508, [(-0.47, -0.36), (-0.30, -0.1), (-0.05, 0.12), (0.2, 0.47)])):
        for a, b in ls:
            ouro.append(_caixa(((a + b) / 2, y, z), (b - a, 0.048, 0.036), (0, 0, 0.012), "fil", "ouro"))
    for a, b in ((-0.4, -0.12), (0.12, 0.4)):
        ouro.append(_caixa(((a + b) / 2, 0.488, 0.318), (b - a, 0.036, 0.026), (0, 0, 0.012), "fil2", "ouro"))
    for a, b in ((-0.45, -0.2), (0.0, 0.3)):
        ouro.append(_caixa(((a + b) / 2, 0.51, 0.84), (b - a, 0.04, 0.026), (0, 0, 0.012), "fil3", "ouro"))
    o_ouro = _uniao(ouro)
    _lascas(R, o_ouro, [(-0.30, 0.52, 0.255), (-0.08, 0.52, 0.255), (0.22, 0.52, 0.69), (-0.36, 0.51, 0.69), (0.16, 0.52, 0.255)], 0.03, "ouro")  # desgaste nas pontas
    _limpa(o_ouro); L.bevel_obj(o_ouro, 0.006, 2, 35)
    o_ouro.data.transform(Matrix.Diagonal((SX, SY, 1.0, 1.0)))
    # losango: recesso na face do fuste, moldura espessa vazada, cruz fina e núcleo em relevo
    r45 = (0, math.radians(45), 0); DY = FY
    _bool(pilar, [_caixa((0, DY, 0.47), (0.44, 0.07, 0.44), r45, "enc", "pedra")])
    moldura = _caixa((0, DY - 0.002, 0.47), (0.38, 0.05, 0.38), r45, "lo", "ouro")
    _bool(moldura, [_caixa((0, DY, 0.47), (0.25, 0.3, 0.25), r45, "lo_i", "ouro")])
    nucleo = _caixa((0, DY + 0.004, 0.47), (0.14, 0.055, 0.14), r45, "lo2", "ouro")
    bras = [_caixa((0, DY - 0.004, 0.47), (0.014, 0.04, 0.42), (0, 0, 0), "lo3", "ouro"), _caixa((0, DY - 0.004, 0.47), (0.42, 0.04, 0.014), (0, 0, 0), "lo4", "ouro")]
    losango = _uniao([moldura, nucleo] + bras)
    _limpa(losango); L.bevel_obj(losango, 0.005, 2, 35)
    o_ouro = _uniao([o_ouro, losango])

    # 6) entulho: rochas angulares no canto frontal direito + duas lascas grandes caídas
    cfg = [((0.74, 0.86), 0.14, 0.95, 20, 0.4, 1.0), ((0.92, 0.72), 0.09, 0.6, 11, 1.2, 1.0), ((0.58, 1.04), 0.07, 1.2, 10, 2.0, 1.0),
           ((1.00, 0.97), 0.055, 0.8, 9, 0.1, 1.0), ((0.82, 1.14), 0.10, 0.5, 16, 2.6, 1.0), ((0.50, 0.70), 0.05, 0.9, 9, 0.8, 0.2)]
    rocs = []
    for (x, y), r, ach, n, rt, _ in cfg:
        o = _rocha(R, (x * 1.22, y * 1.14, 0.0), r * 1.1, ach, n, rt)
        zmin = min(v.co.z for v in o.data.vertices)
        base_z = 0.20 if y < 0.72 and x < 0.55 else 0.0
        if base_z: o.data.transform(Matrix.Translation((-0.1, -0.05, 0)))     # a menor repousa sobre a laje
        for v in o.data.vertices: v.co.z += base_z - 0.012 - zmin
        _quebra(R, o, 1)
        rocs.append(o)
    for c, d, rt in (((-0.78, 0.86, 0.0), (0.38, 0.22, 0.10), (0.1, 0, 0.5)), ((0.12, 1.0, 0.0), (0.26, 0.16, 0.08), (0.0, 0, 2.2))):
        o = _lasca_grande(R, (c[0] * 1.22, c[1] * 1.14, 0.0), d, rt); zmin = min(v.co.z for v in o.data.vertices)
        for v in o.data.vertices: v.co.z += -0.012 - zmin
        _quebra(R, o, 1)
        rocs.append(o)
    # bloco caído sobre o degrau de base (lasca de laje inclinada, apoiada na borda)
    bloco = _caixa((-0.55, 0.68, 0.30), (0.34, 0.22, 0.13), (0.10, -0.16, 0.45), "bloco")
    L.bevel_obj(bloco, 0.012, 3, 30); _lascas(R, bloco, [(-0.72, 0.62, 0.35), (-0.40, 0.78, 0.25), (-0.70, 0.78, 0.36), (-0.43, 0.61, 0.24)], 0.09)
    rocs.append(bloco)
    for o in rocs[:-1]: L.bevel_obj(o, 0.006 if max(o.dimensions) > 0.2 else 0.004, 2, 25)

    # 7) fragmento de capuz sobre o tampo
    ponta = _ponta_capuz(L, (-0.49, 0.47, ZP - 0.004))
    L.bevel_obj(ponta, 0.006, 3, 30)

    # entrega: objetos finais com material
    lista = [("plinto_pilar", pilar, "pedra"), ("plinto_laje", laje, "pedra"), ("plinto_ouro", o_ouro, "ouro"), ("plinto_capuz", ponta, "pedra")] + \
            [("plinto_entulho%d" % i, r, "pedra") for i, r in enumerate(rocs)]
    tot = 0; chave = {m.name: k for k, m in L.M.items()}
    for nome, o, mat in lista:
        me = o.data
        nomes = [chave.get(m.name, mat) if m else mat for m in me.materials]      # ordem de slots do objeto
        idx = [p.material_index for p in me.polygons]
        ordem = [mat, "corte"] if mat != "corte" else [mat]
        me.materials.clear()                                                        # limpa slots vazios/duplicados do boolean
        bpy.data.objects.remove(o); ob = L.new_obj(nome, me, mat)
        if mat != "corte": me.materials.append(L.M["corte"])
        for p, k in zip(me.polygons, idx):
            kk = nomes[k] if k < len(nomes) else mat
            p.material_index = ordem.index(kk) if kk in ordem else 0
        tot += len(me.polygons)
    _portoes(L)
    print("plinto:", tot, "faces")
