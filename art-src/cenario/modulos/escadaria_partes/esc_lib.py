"""Contrato de medidas e utilitários da escadaria da Cripta (compartilhado por todas as partes).
Metros, +Z para cima no Blender, frente (pé da escada) = +Y (vira -Z no Godot). Pivô: x=0, y=0 no meio da corrida, z=0 no piso do pé.
Degrau i (0 = o de baixo, no pé) ocupa y em [YF-(i+1)*T, YF-i*T] e tem o topo em (i+1)*R. No alto há um patamar.
configurar(n, largura) recalcula tudo; as partes leem os valores no momento da chamada (L.N, L.W, ...)."""
import bpy, bmesh, math, random
from mathutils import Vector

N = 11         # número de degraus
W = 4.0        # largura livre entre as paredes laterais
R = 0.18       # altura do espelho
T = 0.32       # profundidade do piso
WT = 0.34      # espessura da parede lateral
H0 = 0.30      # altura da parede acima da linha dos focinhos
COPE = 0.075   # espessura do capeamento
LAND = 0.95    # profundidade do patamar
BAIXO = -0.12  # cota onde a pedra afunda no terreno
RAIL_H = 0.52  # altura do corrimão acima do capeamento
POST = 0.46    # lado do pilar de ponta
YF = YT = 0.0
objs = []      # objetos criados; a main separa por material e junta


def configurar(n=11, largura=4.0, altura=0.18, piso=0.32):
    global N, W, R, T, YF, YT
    N, W, R, T = int(n), float(largura), float(altura), float(piso)
    YF = N * T / 2.0
    YT = YF - N * T          # cota y onde a rampa encontra o patamar
    del objs[:]


def linha(y):
    """Altura da linha dos focinhos (pitch line) em y; sobe para trás (-Y), constante no patamar."""
    return R + R * (YF - max(y, YT)) / T


def rng(seed): return random.Random(seed)


def mat(M, nome): return M[nome]


def _ruido(r, n=4):
    ph = [(r.uniform(0, 6.28), r.uniform(1.5, 7.0), r.uniform(1.5, 7.0), r.uniform(1.5, 7.0)) for _ in range(n)]
    def f(x, y, z):
        return sum(math.sin(a * x + b * y + c * z + p) for p, a, b, c in ph) / n
    return f


def novo(nome, bm, m=None):
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(nome, me); bpy.context.collection.objects.link(o)
    if m is not None: o.data.materials.append(m)
    for p in me.polygons: p.use_smooth = False
    objs.append(o); return o


def bisel(bm, largura=0.012, ang=32, seg=1):
    ed = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(ang)]
    if ed:
        try: bmesh.ops.bevel(bm, geom=ed, offset=largura, segments=seg, affect='EDGES', profile=0.5)
        except Exception: pass


def lasca(bm, r, cantos=2, tam=0.06):
    """Lascas reais: corta cantos do bloco com planos (convexo continua convexo) e tampa o buraco."""
    xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]; zs = [v.co.z for v in bm.verts]
    c = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
    h = Vector(((max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2, (max(zs) - min(zs)) / 2))
    for _ in range(cantos):
        s = Vector((r.choice((-1, 1)), r.choice((-1, 1)), r.choice((-1, 1))))
        corner = c + Vector((s.x * h.x, s.y * h.y, s.z * h.z))
        n = Vector((s.x * r.uniform(.6, 1.4), s.y * r.uniform(.6, 1.4), s.z * r.uniform(.6, 1.4))).normalized()
        d = tam * r.uniform(0.6, 1.5)
        pco = corner - n * d
        geo = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geo, plane_co=pco, plane_no=n, clear_outer=True)
        cut = [g for g in res['geom_cut'] if isinstance(g, bmesh.types.BMEdge)]
        if cut:
            try: bmesh.ops.holes_fill(bm, edges=cut, sides=0)
            except Exception: pass


def bloco(nome, x0, x1, y0, y1, z0, z1, m, seed, sub=(1, 1, 1), jit=0.006, lascas=2, tam=0.06,
          bis=0.012, tira=(), desgaste=0.0, gira=0.0):
    """Bloco de pedra irregular: caixa subdividida, vértices com ruído, lascas nos cantos e bisel.
    tira: faces a remover por normal ('-z','-y','+y','-x','+x') porque ficam escondidas.
    desgaste: afundamento do topo no meio (piso gasto pelo uso)."""
    r = rng(seed); f = _ruido(r)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = (x0 + x1) / 2 + v.co.x * (x1 - x0)
        v.co.y = (y0 + y1) / 2 + v.co.y * (y1 - y0)
        v.co.z = (z0 + z1) / 2 + v.co.z * (z1 - z0)
    for eixo, cuts in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), sub):
        if cuts > 0:
            ed = [e for e in bm.edges if abs((e.verts[0].co - e.verts[1].co).normalized().dot(Vector(eixo))) > 0.99]
            bmesh.ops.subdivide_edges(bm, edges=ed, cuts=cuts, use_grid_fill=True)
    lasca(bm, r, lascas, tam)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for v in bm.verts:
        p = v.co
        d = f(p.x * 3.1, p.y * 3.1, p.z * 3.1) * jit
        v.co += Vector((d * .8, f(p.y * 4, p.z * 4, p.x * 4) * jit, f(p.z * 5, p.x * 5, p.y * 5) * jit))
        if desgaste and p.z > z1 - 0.03:
            u = (p.x - cx) / max((x1 - x0) / 2, 1e-3); w = (p.y - cy) / max((y1 - y0) / 2, 1e-3)
            v.co.z -= desgaste * math.exp(-(u * u * 1.4 + w * w * 0.9)) * (0.7 + 0.3 * f(p.x * 6, p.y * 6, 0))
    if gira:
        c = Vector((cx, cy, 0)); cs, sn = math.cos(gira), math.sin(gira)
        for v in bm.verts:
            q = v.co - c; v.co.x = c.x + q.x * cs - q.y * sn; v.co.y = c.y + q.x * sn + q.y * cs
    if bis: bisel(bm, bis)
    nm = {'-z': (0, 0, -1), '+z': (0, 0, 1), '-y': (0, -1, 0), '+y': (0, 1, 0), '-x': (-1, 0, 0), '+x': (1, 0, 0)}
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    rem = []
    for fc in bm.faces:
        for k in tira:
            if fc.normal.dot(Vector(nm[k])) > 0.9: rem.append(fc); break
    if rem: bmesh.ops.delete(bm, geom=rem, context='FACES')
    return novo(nome, bm, m)


def prisma(nome, x0, x1, perfil, m, seed, jit=0.005, lascas=1, tam=0.05, bis=0.012, sub=0):
    """Prisma extrudado em X a partir de um perfil (y,z) convexo (paredes inclinadas, capeamento)."""
    r = rng(seed); f = _ruido(r)
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in perfil]
    b = [bm.verts.new((x1, y, z)) for y, z in perfil]
    n = len(perfil)
    bm.faces.new(a[::-1]); bm.faces.new(b)
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    if sub:
        ed = [e for e in bm.edges if abs(e.verts[0].co.x - e.verts[1].co.x) < 1e-6]
        bmesh.ops.subdivide_edges(bm, edges=ed, cuts=sub, use_grid_fill=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    lasca(bm, r, lascas, tam)
    for v in bm.verts:
        p = v.co
        v.co += Vector((f(p.y * 4, p.z * 4, p.x * 4), f(p.z * 3, p.x * 3, p.y * 3), f(p.x * 5, p.y * 5, p.z * 5))) * jit
    if bis: bisel(bm, bis)
    return novo(nome, bm, m)


def tubo(nome, pts, raios, m, lados=8, jit=0.0, seed=0, giro=0.0, quadrado=False, tampas=True):
    """Barra varrida por uma polilinha. raios: número ou lista. giro: voltas totais (barra torcida)."""
    r = rng(seed)
    if not isinstance(raios, (list, tuple)): raios = [raios] * len(pts)
    bm = bmesh.new(); aneis = []
    ref = Vector((0, 0, 1))
    for i, p in enumerate(pts):
        p = Vector(p)
        t = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        if abs(t.dot(ref)) > 0.95: ref = Vector((1, 0, 0))
        u = t.cross(ref).normalized(); w = t.cross(u).normalized()
        ang0 = giro * 2 * math.pi * i / max(len(pts) - 1, 1)
        an = []
        for k in range(lados):
            a = ang0 + 2 * math.pi * k / lados + (math.pi / lados if quadrado else 0)
            rad = raios[i] * (1 + r.uniform(-jit, jit))
            if quadrado: rad *= 1.25
            an.append(bm.verts.new(p + (u * math.cos(a) + w * math.sin(a)) * rad))
        aneis.append(an)
    for i in range(len(aneis) - 1):
        for k in range(lados):
            bm.faces.new((aneis[i][k], aneis[i][(k + 1) % lados], aneis[i + 1][(k + 1) % lados], aneis[i + 1][k]))
    if tampas:
        bm.faces.new(aneis[0][::-1]); bm.faces.new(aneis[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    o = novo(nome, bm, m)
    if lados > 4:
        for p_ in o.data.polygons: p_.use_smooth = True
    return o


def calota(nome, c, rx, ry, rz, m, seed, sub=2):
    """Massa baixa (musgo): esfera achatada com ruído, afundada no piso."""
    r = rng(seed); f = _ruido(r)
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    for v in bm.verts:
        p = v.co.copy(); k = 1 + 0.28 * f(p.x * 3, p.y * 3, p.z * 3)
        v.co = Vector((c[0] + p.x * rx * k, c[1] + p.y * ry * k, c[2] + max(p.z, -0.25) * rz * k))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return novo(nome, bm, m)
