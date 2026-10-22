"""Pilar de canto da Cripta: 1,2 x 1,2 x 5,4 m, junção em L de duas paredes (faces +Y e +X voltadas para a sala).
Aparelho de quinas alternadas ('dentes'): fiadas ímpares têm o bloco longo na face +Y, as pares na face +X.
Rodapé escalonado e cornija em mísulas; faces de sala recuadas INSET (a parede reta usa o mesmo recuo).
Pivô no centro da base."""
import bpy, bmesh, math
from mathutils import Vector
GLB = 'SM_Cripta_Canto'
HEROI_X, HEROI_Y = -1.5, 1.9
VISTAS = {"frente": ((0, 9, 2.7), (0, 0, 2.7), 700, 900),
          "tres_quartos": ((6.5, 6.5, 4.2), (0, 0, 2.5), 800, 900),
          "close": ((2.6, 2.6, 1.9), (0, 0, 1.3), 800, 800),
          "close_alto": ((2.8, 2.8, 5.0), (0, 0, 4.3), 800, 800)}
INSET = 0.05   # recuo do fuste nas faces da sala (+X, +Y) sobre o rodapé

def _bm_check(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    ok = all(e.is_manifold for e in bm.edges); bm.free(); return ok

def _talhe(o, R, amp):
    """Pedra talhada à mão: subdivide as faces e desloca os vértices (almofada + irregularidade)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
    dx, dy, dz = o.dimensions
    for v in bm.verts:
        n = v.normal
        q = (v.co - c)
        pill = 1 - min(1, (abs(q.x) / (dx / 2 + 1e-6)) ** 6 + 0) * 0  # sem efeito nas bordas
        v.co += n * R.uniform(-amp, amp) + Vector((R.uniform(-amp, amp), R.uniform(-amp, amp), R.uniform(-amp, amp))) * 0.4
    bm.to_mesh(o.data); bm.free()

def _vol(o):
    bm = bmesh.new(); bm.from_mesh(o.data); v = bm.calc_volume(); bm.free(); return v

def _chip(L, o, pos, size, seed):
    """Quina quebrada: cortador girado a 45 deg (faceta oblíqua e iluminada) + dente menor; pos = ponto da quina (x, y, z da aresta)."""
    r = L.rng(seed); d = Vector((1, 1, 0)).normalized()
    for i, (sz, dep, dz) in enumerate(((size, 0.15, 0.0), (size * 0.55, 0.11, r.uniform(0.1, 0.18) * r.choice((-1, 1))))):
        c = Vector(pos) + d * (sz / 2 - dep) + Vector((r.uniform(-.03, .03), r.uniform(-.03, .03), dz))
        bpy.ops.mesh.primitive_cube_add(size=1, location=c, rotation=(r.uniform(-.45, .45), r.uniform(-.45, .45), math.radians(45) + r.uniform(-.2, .2)))
        cut = bpy.context.object; cut.scale = (sz, sz, sz); bpy.ops.object.transform_apply(scale=True)
        mod = o.modifiers.new("chip", 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = cut; mod.solver = 'EXACT'
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier="chip")
        bpy.data.objects.remove(cut, do_unlink=True)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(o.data); bm.free()

def build(L):
    R = L.rng(11)
    esc = L.stone('escura'); cla = esc   # mesmo tom azul-violeta do nicho/arco (a pedra clara lia marrom sob o sol quente)
    H = L.WALL_H; P = L.PLINTH; CZ = L.CORNICE_Z; h = L.WALL_T / 2   # 0.6
    S = h - INSET   # face da sala do fuste
    GAP = 0.014
    quoins = []

    def blk(x0, x1, y0, y1, z0, z1, m, jit=0.012, bev=0.024, seed_out=True):
        # deslocamentos aleatórios nas faces expostas (+X,+Y), pequenas variações de altura
        dx = R.uniform(0, jit) if x1 >= S - 0.001 else 0
        dy = R.uniform(0, jit) if y1 >= S - 0.001 else 0
        z0 += R.uniform(-0.004, 0.004); z1 += R.uniform(-0.004, 0.004)
        x1 += dx; y1 += dy
        o = L.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), m, bev=0)
        _talhe(o, R, 0.006 if jit > 0.006 else 0.0015)
        L.bevel_obj(o, bev, 2, 35)
        return o

    # ---------- rodapé escalonado (3 degraus: 1,2 / 1,16 / fuste recuado)
    plint = blk(-h, h, -h, h, 0, 0.20, cla, jit=0, bev=0.03)
    blk(-h, h - 0.025, -h, h - 0.025, 0.20, 0.34, esc, jit=0.004, bev=0.025)
    blk(-h, h - 0.04, -h, h - 0.04, 0.34, P - 0.05, cla, jit=0.004, bev=0.02)
    blk(-h, S + 0.015, -h, S + 0.015, P - 0.05, P, esc, jit=0, bev=0.012)  # filete de arremate
    # lajes de rodapé partidas: junta vertical no degrau baixo (fenda estreita)

    # ---------- fuste: fiadas com quinas alternadas
    z = P
    alturas = []
    k = 0
    while z < CZ - 0.2:
        ht = R.choice((0.34, 0.40, 0.46, 0.52, 0.38, 0.58))
        if z + ht > CZ - 0.05 or CZ - (z + ht) < 0.22: ht = CZ - z
        alturas.append((z, z + ht)); z += ht
    for k, (z0, z1) in enumerate(alturas):
        zz0, zz1 = z0 + GAP / 2, z1 - GAP / 2
        cut = R.uniform(-0.12, 0.10)
        m_q = esc
        if k % 2 == 0:
            # bloco longo ao longo de X na face +Y (quina), restante em duas peças atrás
            yc = S - R.uniform(0.50, 0.58)
            q = blk(-h, S, yc + GAP, S, zz0, zz1, m_q, jit=0.018); quoins.append((q, k))
            xj = R.uniform(-0.1, 0.25)
            blk(-h, xj - GAP / 2, -h, yc, zz0, zz1, esc)
            blk(xj + GAP / 2, S, -h, yc, zz0, zz1, esc)
        else:
            xc = S - R.uniform(0.50, 0.58)
            q = blk(xc + GAP, S, -h, S, zz0, zz1, m_q, jit=0.018); quoins.append((q, k))
            yj = R.uniform(-0.1, 0.25)
            blk(-h, xc, -h, yj - GAP / 2, zz0, zz1, esc)
            blk(-h, xc, yj + GAP / 2, S, zz0, zz1, esc)
        # o dente: sobra de bloco que invade a outra face na quina, fechando o L
    # como os longos fecham a quina em um dos lados, completa o outro lado com bloco curto avançando até a face
    # (cada fiada já cobre o retângulo completo: A = [-h,S]x[yc,S]  + atrás;  B = [xc,S]x[-h,S] + atrás)
    # núcleo oculto para fechar qualquer fresta visual
    L.box(((-h + S - 0.03) / 2, (-h + S - 0.03) / 2, (P + CZ) / 2), (S - 0.03 + h, S - 0.03 + h, CZ - P), esc, bev=0)

    # ---------- fiada fina de remate e friso antes da cornija
    blk(-h, S + 0.02, -h, S + 0.02, CZ - 0.14, CZ, cla, jit=0.004, bev=0.02)
    # ---------- cornija em mísulas escalonadas (saindo do recuo até a face cheia 1,2)
    cz0 = CZ
    blk(-h, S + 0.04, -h, S + 0.04, cz0, cz0 + 0.09, esc, jit=0.003, bev=0.015)
    blk(-h, h - 0.01, -h, h - 0.01, cz0 + 0.09, cz0 + 0.17, cla, jit=0.003, bev=0.015)
    blk(-h, h - 0.015, -h, h - 0.015, cz0 + 0.17, cz0 + 0.30, esc, jit=0.003, bev=0.02)
    for i in range(7):   # dentículos nas duas faces da sala
        t = -h + 0.1 + i * 0.165
        L.box((t, h - 0.025, cz0 + 0.235), (0.10, 0.05, 0.10 + R.uniform(0, 0.02)), cla, bev=0.01)
        L.box((h - 0.025, t, cz0 + 0.235), (0.05, 0.10, 0.10 + R.uniform(0, 0.02)), cla, bev=0.01)
    corn = blk(-h, h, -h, h, cz0 + 0.30, cz0 + 0.46, cla, jit=0.0, bev=0.025)
    blk(-h, h - 0.02, -h, h - 0.02, cz0 + 0.46, cz0 + 0.56, esc, jit=0.003, bev=0.02)
    blk(-h, h, -h, h, cz0 + 0.56, H, esc, jit=0.0, bev=0.03)
    L.box((0, 0, H - 0.01), (1.2, 1.2, 0.02), esc, bev=0)

    # ---------- rachaduras: sulcos reais (boolean fino e raso) nas pedras da face da sala
    blocks = [o for o in L.objs if o.dimensions.z > 0.2 and o.dimensions.z < 0.7]
    def groove(axis, u0, z0, n, seed):
        r = L.rng(seed); u, zz = u0, z0
        for i in range(n):
            nu = u + r.uniform(-0.05, 0.05); nz = zz + r.uniform(0.06, 0.13)
            ang = math.atan2(nu - u, nz - zz); ln = math.hypot(nu - u, nz - zz) + 0.012
            mu, mz = (u + nu) / 2, (zz + nz) / 2
            w = 0.010 if i % 3 else 0.007
            if axis == 'y': loc, sz, rot = (mu, S, mz), (w, 0.04, ln), (0, ang, 0)
            else: loc, sz, rot = (S, mu, mz), (0.04, w, ln), (-ang, 0, 0)
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
            cut = bpy.context.object; cut.scale = sz; bpy.ops.object.transform_apply(scale=True)
            for o in blocks:
                bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
                if all(min(v[k] for v in bb) - 0.05 < loc[k] < max(v[k] for v in bb) + 0.05 for k in range(3)) and max(v.y if axis == 'y' else v.x for v in bb) > S - 0.03:
                    md = o.modifiers.new("g", 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cut; md.solver = 'EXACT'
                    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier="g")
            bpy.data.objects.remove(cut, do_unlink=True)
            u, zz = nu, nz
    groove('y', -0.15, 1.2, 9, 3); groove('x', 0.2, 2.6, 8, 5); groove('y', 0.3, 3.3, 6, 9)
    groove('x', -0.25, 0.7, 5, 12); groove('y', 0.1, 4.0, 4, 14)

    # ---------- lascas na quina externa (+X,+Y): vertical, topo e base das pedras escolhidas
    for q, k in quoins:
        if k in (0, 1, 2, 3, 4, 5, 6, 8, 9, 10):
            z0, z1 = alturas[k]
            for attempt in range(4):
                bak = q.data.copy(); v0 = _vol(q)
                pos = (S, S, (z1 + 0.02) if k % 2 else (z0 - 0.02))
                _chip(L, q, pos, 0.34 + 0.05 * (k % 3), 40 + k + attempt * 7)
                L.bevel_obj(q, 0.01, 1, 40)
                if _bm_check(q) and 0.6 * v0 < _vol(q) < 0.99 * v0: break
                q.data = bak
    # cornija e rodapé: lascas nas quinas
    for obj, pos, sz, sd in ((corn, (h, h, cz0 + 0.46), 0.3, 77), (corn, (-h + 0.02, h, cz0 + 0.30), 0.22, 78), (plint, (h, h, 0.2), 0.3, 79)):
        bak = obj.data.copy(); v0 = _vol(obj)
        _chip(L, obj, pos, sz, sd); L.bevel_obj(obj, 0.008, 1, 40)
        if not (_bm_check(obj) and 0.6 * v0 < _vol(obj) < 0.995 * v0): obj.data = bak
    L.col_box((0, 0, H / 2), (1.2, 1.2, H))
