"""PARTE mãos: punho de pedra fechado (estátua, esquerda) e a mão direita quebrada caída no plinto.
Cada mão é UMA casca sólida: blocos chanfrados (palma, laje de quatro dedos com sulcos, nós, polegar, pulso)
unidos por boolean UNION EXACT, depois bevel leve nas arestas vivas. Sem peças soltas, exceto a lasca no chão."""
import bpy, bmesh, math
from mathutils import Vector, Matrix

ESC = 2.25  # mão grande (estilo chibi) para ler a 8 m
_MAT = []   # [pedra, corte]: todo bloco temporário carrega os dois espaços de material, para o boolean preservar o índice

def _bloco(c, s, bev=0.004, rot=(0, 0, 0), nome="b"):
    """Cubo com centro c, tamanho s=(x,y,z), girado (euler), com chanfro; devolve objeto temporário."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * s[0], v.co.y * s[1], v.co.z * s[2]))
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X'), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bev, segments=1, affect='EDGES')
    return _tmp(nome, bm)

def _prisma(c, r, comp, n=8, eixo='X', jit=None, bev=0.003, nome="p"):
    """Prisma de n lados ao longo do eixo (X), centro c; jit = função (i) -> deslocamento da ponta +X (fratura facetada)."""
    bm = bmesh.new(); a = [[], []]
    for k, x in enumerate((-comp / 2, comp / 2)):
        for i in range(n):
            t = i / n * math.tau + math.pi / n
            d = jit(i) if (jit and k == 1) else 0.0
            a[k].append(bm.verts.new(Vector((x + d, r * math.cos(t), r * math.sin(t)))))
    for i in range(n): bm.faces.new((a[0][i], a[0][(i + 1) % n], a[1][(i + 1) % n], a[1][i]))
    bm.faces.new(a[0][::-1]); bm.faces.new(a[1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c), verts=bm.verts)
    if bev: bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bev, segments=1, affect='EDGES')
    return _tmp(nome, bm)

def _tmp(nome, bm):
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(nome, me); bpy.context.collection.objects.link(o)
    for m in _MAT: o.data.materials.append(m)
    return o

def _uniao(objs, nome):
    """Une todos os blocos no primeiro, via boolean EXACT; devolve o objeto resultante (temporário)."""
    base = objs[0]
    for o in objs[1:]:
        m = base.modifiers.new("u", 'BOOLEAN'); m.operation = 'UNION'; m.solver = 'EXACT'; m.object = o
        bpy.context.view_layer.objects.active = base; bpy.ops.object.modifier_apply(modifier="u")
        bpy.data.objects.remove(o, do_unlink=True)
    base.name = nome; return base

def _pulso(r, ini, comp, quebrado=False, n=8):
    """Pulso grosso (prisma de n lados ao longo de X, de x=ini a ini+comp). Se quebrado, a ponta traseira (-X) termina em fratura
    de planos facetados em leque (triângulos da face de corte recebem o material 'corte', índice 1)."""
    bm = bmesh.new(); an = []
    for k, x in enumerate((ini, ini + comp)):
        an.append([bm.verts.new(Vector((x, r * math.cos(i / n * math.tau + math.pi / n), r * math.sin(i / n * math.tau + math.pi / n)))) for i in range(n)])
    for i in range(n): bm.faces.new((an[0][i], an[0][(i + 1) % n], an[1][(i + 1) % n], an[1][i]))
    bm.faces.new(an[1])
    if quebrado:
        planos = [(0.0, 0.034, 0.5), (0.020, -0.030, 2.6), (0.006, 0.026, 4.4)]
        for i, v in enumerate(an[0]):
            a = i / n * math.tau
            v.co.x += min(p0 + p1 * math.cos(a - p2) for (p0, p1, p2) in planos) * 1.0 - 0.018 * (i % 2)
        c = bm.verts.new(sum((v.co for v in an[0]), Vector()) / n + Vector((-0.014, 0, 0)))
        for i in range(n):
            f = bm.faces.new((c, an[0][(i + 1) % n], an[0][i])); f.material_index = 1
    else:
        bm.faces.new(an[0][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if not any(f.material_index == 1 for f in e.link_faces)], offset=0.003, segments=1, affect='EDGES')
    return _tmp("pulso", bm)

def _punho(nome, quebrado=False):
    """Punho fechado no espaço local: antebraço/pulso vem de -X, nós dos dedos para +X, costas da mão para +Z.
    Poucos blocos grandes (palma, laje de dedos com 3 sulcos, polegar, base do polegar, pulso). Medidas antes de ESC."""
    p = []
    p.append(_bloco((0.0, 0, 0.002), (0.105, 0.104, 0.094), 0.010, nome="palma"))
    # laje dos quatro dedos curvados: quatro blocos separados por 3 sulcos largos, alturas levemente escalonadas
    w = 0.0215; gap = 0.0065; y = -0.0525
    for i in range(4):
        cy = y + w / 2; y += w + gap
        alt = (0.066, 0.070, 0.067, 0.058)[i]
        p.append(_bloco((0.070, cy, 0.0 + (alt - 0.066) / 2), (0.050, w, alt), 0.004, nome="dedo%d" % i))
    # polegar: bloco grande cruzando a frente dos dedos, mais a base muscular no flanco
    p.append(_bloco((0.090, 0.030, -0.020), (0.034, 0.068, 0.034), 0.007, rot=(0, 0, math.radians(-8)), nome="polegar"))
    p.append(_bloco((0.030, 0.052, -0.014), (0.072, 0.030, 0.062), 0.007, rot=(0, 0, math.radians(8)), nome="tenar"))
    # pulso grosso: entra na boca da manga (esquerda) ou termina em fratura (mão caída)
    p.append(_pulso(0.043, -0.100 if quebrado else -0.150, 0.080 if quebrado else 0.140, quebrado))
    return _uniao(p, nome)

def _marcar_corte(o):
    """O boolean perde o índice de material: marca as facetas de fratura (viradas para trás, na ponta do pulso) com 'corte'."""
    for q in o.data.polygons:
        q.material_index = 1 if (q.center.x < -0.100 + 0.050 and q.normal.x < -0.35) else 0

def _sulcar(o, pts, z, larg=0.0048, prof=0.016):
    """Rachadura fina: sulco real (boolean DIFFERENCE) com tiras finas ao longo da polilinha (x, y) em plano horizontal z."""
    cs = []
    for a, b in zip(pts, pts[1:]):
        pa = Vector((a[0], a[1], z)); pb = Vector((b[0], b[1], z)); d = pb - pa; ang = math.atan2(d.y, d.x)
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((pa + pb) / 2) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Diagonal((d.length + larg, larg, prof * 2, 1)))
        cs.append(_tmp("sulco", bm))
    for c in cs:
        m = o.modifiers.new("d", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.solver = 'EXACT'; m.object = c
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier="d")
        bpy.data.objects.remove(c, do_unlink=True)

def _lasca(L, nome, c, s, yaw, rnd, alto=0.6):
    """Lasca clara de pedra recém-quebrada: casca convexa afunilada de faces planas, assentada no chão (base em z=c.z)."""
    bm = bmesh.new(); n = 6; r0 = []
    for i in range(n):
        t = i / n * math.tau + rnd.uniform(-0.25, 0.25); rr = s * rnd.uniform(0.65, 1.2)
        r0.append((rr * math.cos(t) * 1.25, rr * math.sin(t)))
    bot = [bm.verts.new(Vector((x, y, 0))) for x, y in r0]
    top = [bm.verts.new(Vector((x * 0.45, y * 0.45, s * alto * rnd.uniform(0.8, 1.2) + 0.25 * x * rnd.uniform(0.2, 1)))) for x, y in r0]
    for i in range(n): bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
    bm.faces.new(bot[::-1]); bm.faces.new(top); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ Matrix.Rotation(yaw, 4, 'Z'), verts=bm.verts)
    o = L.new_obj(nome, bm, "corte"); L.bevel_obj(o, 0.005, 1, 25); return o

def _posicionar(o, pos, yaw, pitch=0.0, roll=0.0, esc=ESC):
    """Aplica escala, rotação e posição ao objeto temporário (no mesh)."""
    M = Matrix.Translation(pos) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(pitch, 4, 'Y') @ Matrix.Rotation(roll, 4, 'X') @ Matrix.Scale(esc, 4)
    o.data.transform(M)

def _finalizar(L, o):
    # os blocos já carregam [pedra, corte] na mesma ordem de L.M; só registra
    L.objs.append(o)

def build(L):
    rnd = L.rng(7)
    _MAT[:] = [L.M["pedra"], L.M["corte"]]
    # ---- mão esquerda da estátua: punho fechado cruzado à frente; pulso entra na boca da manga em (-0.13, 0.17, 1.81), direção (0.47, 0.88) subindo 12°
    e = _punho("punho_esq")
    _posicionar(e, Vector((-0.06, 0.30, L.Z_HANDS)), math.radians(62), pitch=math.radians(-12))
    _finalizar(L, e)

    # ---- mão direita quebrada, caída no tampo do plinto: pulso em fratura clara e rachaduras finas
    d = _punho("mao_caida", quebrado=True)
    _sulcar(d, [(-0.17, 0.020), (-0.13, 0.010), (-0.11, -0.012), (-0.07, -0.016)], 0.040)          # racha o pulso a partir da fratura
    _sulcar(d, [(-0.04, -0.045), (-0.02, -0.020), (-0.035, 0.006), (-0.012, 0.030)], 0.050)       # racha o dorso da mão
    _sulcar(d, [(0.020, 0.040), (0.040, 0.020), (0.036, -0.004)], 0.050)
    _marcar_corte(d)
    _posicionar(d, Vector((0.20, 0.57, 0)), math.radians(203), roll=math.radians(4))
    zmin = min(v.co.z for v in d.data.vertices)
    d.data.transform(Matrix.Translation((0, 0, L.ZP - 0.004 - zmin)))
    _finalizar(L, d)
    # lascas claras junto à fratura e ao lado
    _lasca(L, "lasca1", Vector((0.55, 0.66, L.ZP - 0.003)), 0.050, 0.4, rnd)
    _lasca(L, "lasca2", Vector((0.40, 0.70, L.ZP - 0.003)), 0.032, 1.1, rnd, 0.8)
    _lasca(L, "lasca3", Vector((0.62, 0.50, L.ZP - 0.003)), 0.030, 2.0, rnd)
    _lasca(L, "lasca4", Vector((0.30, 0.74, L.ZP - 0.003)), 0.024, 0.2, rnd, 0.9)
