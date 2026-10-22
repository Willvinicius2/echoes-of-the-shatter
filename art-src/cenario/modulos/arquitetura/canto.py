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
    esc, cla = L.stone('escura'), L.stone('clara')
    H = L.WALL_H; P = L.PLINTH; CZ = L.CORNICE_Z; h = L.WALL_T / 2   # 0.6
    S = h - INSET   # face da sala do fuste
    GAP = 0.014
    quoins = []

    def blk(x0, x1, y0, y1, z0, z1, m, jit=0.012, bev=0.018, seed_out=True):
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
    blk(-h, h, -h, h, 0, 0.20, cla, jit=0, bev=0.03)
    blk(-h, h - 0.025, -h, h - 0.025, 0.20, 0.34, esc, jit=0.004, bev=0.025)
    blk(-h, h - 0.04, -h, h - 0.04, 0.34, P - 0.05, cla, jit=0.004, bev=0.02)
    blk(-h, S + 0.015, -h, S + 0.015, P - 0.05, P, esc, jit=0, bev=0.012)  # filete de arremate
    # lajes de rodapé partidas: junta vertical no degrau baixo (fenda estreita)
    L.box((0.15, h - 0.01, 0.10), (0.012, 0.03, 0.20), L.stone('ferro'), bev=0)
    L.box((h - 0.01, -0.2, 0.10), (0.03, 0.012, 0.20), L.stone('ferro'), bev=0)

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
        m_q = cla if R.random() < 0.7 else esc
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
    blk(-h, h, -h, h, cz0 + 0.30, cz0 + 0.46, cla, jit=0.0, bev=0.025)
    blk(-h, h - 0.02, -h, h - 0.02, cz0 + 0.46, cz0 + 0.56, esc, jit=0.003, bev=0.02)
    blk(-h, h, -h, h, cz0 + 0.56, H, esc, jit=0.0, bev=0.03)
    L.box((0, 0, H - 0.01), (1.2, 1.2, 0.02), esc, bev=0)

    # ---------- musgo/sujeira baixa: calotas escuras na base
    for i in range(6):
        t = R.uniform(-0.45, 0.45)
        L.box((t, h - 0.015, 0.45 + R.uniform(0, 0.05)), (R.uniform(0.1, 0.22), 0.03, R.uniform(0.03, 0.06)), L.stone('ferro'), bev=0.006)

    # ---------- rachaduras: sulcos finos em zigue-zague nas faces da sala
    ferro = L.stone('ferro')
    def crack(axis, x0, z0, n, seed):
        r = L.rng(seed); x, zz = x0, z0
        for i in range(n):
            nx = x + r.uniform(-0.06, 0.06); nz = zz + r.uniform(0.07, 0.15)
            ang = math.atan2(nx - x, nz - zz); ln = math.hypot(nx - x, nz - zz)
            if axis == 'y':
                L.box(((x + nx) / 2, S + 0.012, (zz + nz) / 2), (0.014, 0.012, ln), ferro, rot=(0, -ang, 0), bev=0)
            else:
                L.box((S + 0.012, (x + nx) / 2, (zz + nz) / 2), (0.012, 0.014, ln), ferro, rot=(-ang, 0, 0), bev=0)
            x, zz = nx, nz
    crack('y', -0.15, 1.2, 9, 3)
    crack('x', 0.2, 2.6, 8, 5)
    crack('y', 0.3, 3.3, 6, 9)

    # ---------- lascas na quina externa (+X,+Y): vertical, topo e base das pedras escolhidas
    for q, k in quoins:
        if k in (1, 2, 4, 6, 9):
            z0, z1 = alturas[k]
            for attempt in range(4):
                bak = q.data.copy(); v0 = _vol(q)
                pos = (S, S, (z1 + 0.02) if k % 2 else (z0 - 0.02))
                _chip(L, q, pos, 0.42 if k != 4 else 0.5, 40 + k + attempt * 7)
                if _bm_check(q) and 0.6 * v0 < _vol(q) < 0.99 * v0: break
                q.data = bak
    # cornija: lasca no canto superior frontal
    for o in list(L.objs):
        if abs(o.location.z - (cz0 + 0.38)) < 0.1 and o.dimensions.x > 1.1 and o.dimensions.y > 1.1:
            _chip(L, o, (h, h, cz0 + 0.46), 0.3, 77); break


    for o in L.objs:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        if max(v.x for v in bb) > 0.61 or max(v.y for v in bb) > 0.61: print("OVER", o.name, [round(c,3) for c in o.dimensions], [round(c,2) for c in (sum(v.z for v in bb)/8,)], [round(max(v.x for v in bb), 3), round(max(v.y for v in bb), 3)])
    L.col_box((0, 0, H / 2), (1.2, 1.2, H))
