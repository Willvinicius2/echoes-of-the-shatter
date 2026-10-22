"""PARTE mãos: punho de pedra fechado (estátua, esquerda) e a mão direita quebrada caída no plinto.
Cada mão é UMA casca sólida: blocos chanfrados (palma, laje de quatro dedos com sulcos, nós, polegar, pulso)
unidos por boolean UNION EXACT, depois bevel leve nas arestas vivas. Sem peças soltas, exceto a lasca no chão."""
import bpy, bmesh, math
from mathutils import Vector, Matrix

ESC = 1.6  # a mão é um pouco grande (estilo chibi) para ler a 8 m

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
    o = bpy.data.objects.new(nome, me); bpy.context.collection.objects.link(o); return o

def _uniao(objs, nome):
    """Une todos os blocos no primeiro, via boolean EXACT; devolve o objeto resultante (temporário)."""
    base = objs[0]
    for o in objs[1:]:
        m = base.modifiers.new("u", 'BOOLEAN'); m.operation = 'UNION'; m.solver = 'EXACT'; m.object = o
        bpy.context.view_layer.objects.active = base; bpy.ops.object.modifier_apply(modifier="u")
        bpy.data.objects.remove(o, do_unlink=True)
    base.name = nome; return base

def _punho(nome, pulso_ate=-0.16, manga=False, quebra=None, cristal=False):
    """Punho fechado no espaço local: antebraço vem de -X, nós dos dedos para +X, costas da mão para +Z.
    Medidas em metros antes de ESC. Devolve objeto temporário (casca única)."""
    p = []
    p.append(_bloco((0.0, 0, 0), (0.105, 0.098, 0.088), 0.010, nome="palma"))            # palma e costas da mão
    p.append(_bloco((-0.012, 0, 0.034), (0.085, 0.092, 0.03), 0.008, nome="dorso"))        # dorso mais alto
    # laje dos quatro dedos curvados: quatro blocos com sulcos (largura 0.092 / 4)
    larg = [0.021, 0.024, 0.023, 0.019]; y = -0.049
    for i, w in enumerate(larg):
        cy = y + w / 2; y += w + 0.0035
        alt = 0.060 - 0.003 * abs(i - 1.2)
        p.append(_bloco((0.067, cy - 0.0015, -0.002), (0.042, w, alt), 0.0045, nome=f"dedo{i}"))
        p.append(_bloco((0.052, cy - 0.0015, 0.036 - 0.002 * abs(i - 1.2)), (0.026, w + 0.002, 0.020), 0.005, nome=f"no{i}"))   # nó do dedo
    # polegar: barra cruzando a frente dos dedos, apontando para o lado do mindinho
    p.append(_bloco((0.085, 0.020, -0.016), (0.030, 0.062, 0.026), 0.006, rot=(0, 0, math.radians(-8)), nome="polegar"))
    p.append(_bloco((0.083, 0.054, -0.016), (0.026, 0.024, 0.024), 0.006, nome="pol_ponta"))
    # base do polegar (músculo) no flanco
    p.append(_bloco((0.030, 0.046, -0.014), (0.070, 0.024, 0.052), 0.006, rot=(0, 0, math.radians(8)), nome="tenar"))
    # pulso (entra na boca da manga)
    p.append(_prisma((-0.100, 0, -0.002), 0.050, 0.100, 8, bev=0.004, nome="pulso"))
    if manga:  # toco curto de manga (punho do manto) com borda quebrada, só na mão caída
        j = quebra
        p.append(_prisma((-0.170, 0, -0.002), 0.080, 0.075, 10, jit=lambda i: 0.0, bev=0.0, nome="manga0"))
    if cristal:
        # estilhaço de cristal preso entre os dedos e o polegar (base embutida na mão)
        bm = bmesh.new(); n = 6; base = [bm.verts.new(Vector((0.020 * math.cos(i / n * math.tau), 0.020 * math.sin(i / n * math.tau), 0))) for i in range(n)]
        top = bm.verts.new(Vector((0.004, 0.002, 0.075)))
        mid = [bm.verts.new(Vector((0.017 * math.cos(i / n * math.tau + 0.3), 0.017 * math.sin(i / n * math.tau + 0.3), 0.03))) for i in range(n)]
        for i in range(n):
            bm.faces.new((base[i], base[(i + 1) % n], mid[(i + 1) % n], mid[i])); bm.faces.new((mid[i], mid[(i + 1) % n], top))
        bm.faces.new(base[::-1]); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.transform(bm, matrix=Matrix.Translation((0.060, 0.012, 0.030)) @ Matrix.Rotation(math.radians(-18), 4, 'Y'), verts=bm.verts)
        p.append(_tmp("cristal", bm))
    return _uniao(p, nome)

def _fratura(L, o_manga_x, r, rnd):
    pass

def _lasca(L, nome, c, s, yaw, rnd):
    """Lasca de pedra facetada: prisma baixo irregular, assentado no chão (base plana em z=c.z)."""
    bm = bmesh.new(); n = 7; r0 = []
    for i in range(n):
        t = i / n * math.tau + rnd.uniform(-0.2, 0.2); rr = s * rnd.uniform(0.7, 1.15)
        r0.append((rr * math.cos(t), rr * math.sin(t)))
    h = s * 0.7
    bot = [bm.verts.new(Vector((x, y, 0))) for x, y in r0]
    top = [bm.verts.new(Vector((x * 0.62 + rnd.uniform(-0.01, 0.01), y * 0.62 + rnd.uniform(-0.01, 0.01), h * rnd.uniform(0.8, 1.15)))) for x, y in r0]
    for i in range(n): bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
    bm.faces.new(bot[::-1]); bm.faces.new(top); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ Matrix.Rotation(yaw, 4, 'Z'), verts=bm.verts)
    o = L.new_obj(nome, bm); L.bevel_obj(o, 0.006, 1, 25); return o

def _posicionar(o, pos, yaw, pitch=0.0, roll=0.0, esc=ESC):
    """Aplica escala, rotação e posição ao objeto temporário (no mesh)."""
    M = Matrix.Translation(pos) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(pitch, 4, 'Y') @ Matrix.Rotation(roll, 4, 'X') @ Matrix.Scale(esc, 4)
    o.data.transform(M)

def build(L):
    rnd = L.rng(7)
    # ---- mão esquerda da estátua: punho fechado cruzado à frente, antebraço vindo de trás/esquerda
    e = _punho("punho_esq")
    _posicionar(e, Vector((-0.06, 0.30, L.Z_HANDS)), math.radians(62), pitch=math.radians(-12))
    e.data.materials.clear(); e.data.materials.append(L.M['pedra']); L.objs.append(e)

    # ---- mão direita quebrada, caída no tampo do plinto
    d = _punho("mao_caida", manga=True)
    # fratura facetada no fim do toco de manga: desloca vértices da face traseira (-X mais externo)
    xmin = min(v.co.x for v in d.data.vertices)
    for v in d.data.vertices:
        if v.co.x < xmin + 0.014:   # plano de quebra inclinado + facetas irregulares
            v.co.x += 0.030 + 0.55 * v.co.y + 0.35 * v.co.z + rnd.uniform(-0.012, 0.012)
    _posicionar(d, Vector((0.55, 0.45, 0)), math.radians(53), roll=math.radians(25))
    # assenta: base do menor z = topo do plinto (com 4 mm de encaixe)
    zmin = min(v.co.z for v in d.data.vertices)
    d.data.transform(Matrix.Translation((0, 0, L.ZP - 0.004 - zmin)))
    d.data.materials.clear(); d.data.materials.append(L.M['pedra']); L.objs.append(d)
    # lascas junto à fratura e ao lado
    _lasca(L, "lasca1", Vector((0.42, 0.28, L.ZP - 0.003)), 0.045, 0.4, rnd)
    _lasca(L, "lasca2", Vector((0.66, 0.60, L.ZP - 0.003)), 0.03, 1.1, rnd)
