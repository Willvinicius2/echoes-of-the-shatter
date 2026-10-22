"""PARTE corpo: manto, capa de ombros, mangas, cinto, medalhão e adornos da estátua encapuzada.
Silhueta de coluna (ombros largos, torso reto), manto em dobras verticais longas e assimétricas (vincos de aresta viva),
lado esquerdo da estátua (x<0) aberto mostrando uma bota de pedra. Manga esquerda termina em punho grosso (mão entra
em (-0.06, 0.30, Z_HANDS)); a direita está quebrada em fratura facetada. Tudo em cascas fechadas."""
import bmesh, math
from mathutils import Vector

TAU = math.tau

# ---------- utilitários locais
def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)

def hsh(i, seed=0):
    v = math.sin((i + 1) * 12.9898 + seed * 78.233) * 43758.5453
    return v - math.floor(v)

def crease(x):
    """1 no vinco (vale agudo), 0 na crista arredondada."""
    return 1.0 - tri(x)

def tri(x):
    """Onda triangular: 0 no vale agudo, 1 na crista (planos retos, aresta viva)."""
    f = x - math.floor(x); return (1.0 - abs(2.0 * f - 1.0)) ** 0.9

def catmull(pts, per=8):
    out = []; P = [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(Vector(pts[-1])); return out

def closed_tube(bm, centers, normals, m, rad):
    """Toro fechado: rad(i, j, ang) -> raio; normals = eixo radial (horizontal) de cada ponto; eixo vertical = Z."""
    n = len(centers); V = []
    for i, (c, nr) in enumerate(zip(centers, normals)):
        ring = []
        for j in range(m):
            a = j / m * TAU; r = rad(i, j, a)
            ring.append(bm.verts.new(c + nr * (r * math.cos(a)) + Vector((0, 0, r * math.sin(a)))))
        V.append(ring)
    for i in range(n):
        for j in range(m):
            bm.faces.new((V[i][j], V[(i + 1) % n][j], V[(i + 1) % n][(j + 1) % m], V[i][(j + 1) % m]))

def sweep_rings(path, ref, m, rad):
    """Anéis perpendiculares ao caminho (transporte de quadro). rad(s, ang) -> raio. Devolve (anéis, quadros)."""
    N = len(path); rings = []; frames = []
    T0 = (path[1] - path[0]).normalized(); U = T0.cross(ref).normalized()
    for i, p in enumerate(path):
        T = ((path[min(i + 1, N - 1)] - path[max(i - 1, 0)])).normalized()
        U = (U - T * U.dot(T)).normalized(); W = T.cross(U)
        s = i / (N - 1); ring = []
        for j in range(m):
            a = j / m * TAU; r = rad(s, a)
            ring.append(p + U * (r * math.cos(a)) + W * (r * math.sin(a)))
        rings.append(ring); frames.append((T, U, W))
    return rings, frames

# ---------- superfície do manto (corpo)
A_PROF = [(0.90, 0.36), (1.20, 0.365), (1.45, 0.37), (1.58, 0.37), (1.68, 0.37), (1.82, 0.285), (2.00, 0.28), (2.20, 0.33), (2.35, 0.41), (2.45, 0.43), (2.52, 0.35), (2.58, 0.215)]
SQ_PROF = [(0.90, 2.2), (1.60, 2.2), (2.10, 2.6), (2.30, 3.6), (2.46, 3.8), (2.54, 2.8), (2.58, 2.2)]  # expoente da superelipse: ombros quadrados
B_PROF = [(0.90, 0.31), (1.20, 0.285), (1.55, 0.250), (1.68, 0.205), (1.85, 0.188), (2.00, 0.205), (2.15, 0.235), (2.30, 0.250), (2.45, 0.235), (2.52, 0.215), (2.58, 0.19)]
FAMILIAS = [(6, 0.080, 1.85, 2.45), (13, 0.042, 1.45, 2.25), (27, 0.016, 1.00, 1.85)]  # (nº de dobras, amplitude no pé, zs mín, zs máx)
NOTCH_C, NOTCH_HW, NOTCH_H = math.radians(128), math.radians(27), 0.78
NOTCH_LO, NOTCH_HI = NOTCH_C - NOTCH_HW, NOTCH_C + NOTCH_HW

def pregas(L, th, z, escala=1.0, seed=0, zmin_amp=2.5):
    """Deslocamento radial (m) das dobras: 3 frequências, cada dobra com altura de início própria, fase com deriva suave."""
    g = th + 0.14 * (math.sin(th - 0.9) + math.sin(0.9))
    grow = L.prof([(L.ZP, 1.0), (1.40, 0.78), (1.55, 0.38), (1.72, 0.20), (2.2, 0.09), (2.6, 0.02)], z)
    assim = 0.85 + 0.30 * math.cos(th - 0.55)
    d = 0.0
    for fi, (N, amp, zs0, zs1) in enumerate(FAMILIAS):
        x = N * g / TAU + 0.30 * math.sin(1.6 * z + 0.7 * fi + th) * (1 + 0.5 * fi)
        i = int(math.floor(x)) % N
        zs = zs0 + (zs1 - zs0) * hsh(i, fi + seed)
        env = smooth(0.0, 0.40, zs - z)
        d += amp * grow * assim * env * (1.0 - crease(x))
    return d * escala

def sq_cs(L, th, z):
    """cos/sen de superelipse: ombros quadrados, resto elíptico."""
    e = 2.0 / L.prof(SQ_PROF, z); c, s_ = math.cos(th), math.sin(th)
    return math.copysign(abs(c) ** e, c), math.copysign(abs(s_) ** e, s_)

def corpo_xy(L, th, z, com_notch=True):
    a = L.prof(A_PROF, z); b = L.prof(B_PROF, z)
    c = 0.0
    if com_notch and z < L.ZP + NOTCH_H:
        # abertura em A: a borda do manto externo sobe em diagonal (resolvida pelo ângulo, sem degraus)
        hw = NOTCH_HW * (L.ZP + NOTCH_H - z) / NOTCH_H
        c = smooth(0.0, 0.20, hw - abs(th - NOTCH_C))
    d = pregas(L, th, z, 1.0 - 0.7 * c)
    # camada interna do lado aberto: mais estreita
    a = a * (1 - 0.17 * c); b = b * (1 - 0.15 * c)
    # barra grossa (bainha) e lascas na borda de baixo
    hem = smooth(L.ZP + 0.075, L.ZP + 0.02, z) * 0.03 * (1 - c)
    for k in range(9):
        ck = (hsh(k, 5) + 0.02) * TAU; w = 0.05 + 0.05 * hsh(k, 6); hh = 0.05 + 0.10 * hsh(k, 7)
        dd = abs(((th - ck + math.pi) % TAU) - math.pi) / w
        if dd < 1: hem -= 0.05 * (1 - dd) * smooth(L.ZP + hh, L.ZP, z) * (1 - c)
    ct, st = sq_cs(L, th, z)
    return ct * (a + d + hem), st * (b + d + hem)

def superficie(L, th, z, off=0.0, esc=1.0):
    x, y = corpo_xy(L, th, z, False)
    if esc != 1.0:
        ct, st = sq_cs(L, th, z); x0 = ct * L.prof(A_PROF, z); y0 = st * L.prof(B_PROF, z)
        x = x0 + (x - x0) * esc; y = y0 + (y - y0) * esc
    n = Vector((x, y, 0)); n = n.normalized() if n.length > 1e-6 else Vector((0, 1, 0))
    return Vector((x, y, z)) + n * off

# ---------- capa dos ombros
CA_PROF = [(2.05, 0.46), (2.18, 0.475), (2.32, 0.49), (2.45, 0.49), (2.50, 0.47), (2.545, 0.36), (2.58, 0.23)]
CB_PROF = [(2.05, 0.325), (2.18, 0.315), (2.32, 0.305), (2.45, 0.292), (2.51, 0.275), (2.555, 0.245), (2.58, 0.205)]

def rim_z(th):
    fr = math.exp(-((math.atan2(math.sin(th - math.pi / 2), math.cos(th - math.pi / 2)) / math.radians(26)) ** 2))
    return 2.12 + 0.20 * fr - 0.10 * smooth(0.0, 1.0, -math.sin(th))

def capa(L, nth):
    rings = []
    perfil = [((u / 13.0) ** 1.5, 0.0, 0.0) for u in range(14)] + [(1.0, -0.09, 0.0), (0.93, -0.09, 0.0)]
    for (u, dr, dz) in perfil:
        ring = []
        for i in range(nth):
            th = i / nth * TAU; zr = rim_z(th)
            z = L.Z_NECK + (zr - L.Z_NECK) * u + dz
            zz = max(2.05, min(2.58, z))
            a = L.prof(CA_PROF, zz) + dr; b = L.prof(CB_PROF, zz) + dr
            d = pregas(L, th, z + 0.45, 0.55, 3) * smooth(2.58, 2.40, z) if dr == 0.0 else 0.0
            # bordo grosso e ondulado: franja de pano abaixo do ombro
            if u > 0.88 and dr == 0.0: d += 0.012 * math.sin(th * 11 + 1.0)
            if dr == 0.0:   # dobras verticais da capa, mais fundas rumo à borda
                g = th + 0.18 * math.sin(th * 2 + 0.6)
                d += (0.034 * (1.0 - crease(8 * g / TAU + 0.3)) + 0.016 * (1.0 - crease(17 * g / TAU))) * (u ** 1.6)
            ct, st = sq_cs(L, th, zz)
            ring.append(Vector((ct * (a + d), st * (b + d), z)))
        rings.append(ring)
    return L.loft(rings, cap_bottom=True, cap_top=True)

# ---------- mangas
def manga(L, lado, quebrada):
    """Antebraços cruzados à frente: o esquerdo (x<0) termina no punho; o direito passa por cima e quebra perto do punho."""
    s_ = -1.0 if lado < 0 else 1.0
    if not quebrada:
        fim = Vector((-0.13, 0.17, 1.81)); f = Vector((0.47 * s_, 0.88, math.tan(math.radians(12)))).normalized()
        P = [Vector((0.38 * s_, -0.03, 2.30)), Vector((0.405 * s_, 0.0, 2.04)), Vector((0.36 * s_, 0.06, 1.88)), fim - f * 0.11, fim]
    else:
        fim = Vector((-0.05, 0.23, 1.76))
        P = [Vector((0.38, -0.03, 2.30)), Vector((0.405, 0.0, 2.04)), Vector((0.33, 0.10, 1.86)), Vector((0.16, 0.19, 1.79)), fim]
    path = catmull(P, 8)
    m = 20
    R = [(0, 0.105), (0.3, 0.128), (0.55, 0.138), (0.78, 0.148), (0.86, 0.14), (0.885, 0.165), (1.0, 0.165)]
    def rad(s, a):
        r = L.prof(R, s)
        x = 6 * a / TAU + 0.8 * s + (0.3 if lado > 0 else 0)
        env = smooth(0.0, 0.25, s) * (1 - smooth(0.80, 0.86, s))
        return r * (1 - 0.24 * env * crease(x))
    full, fr = sweep_rings(path, Vector((0, 0, 1)), m, rad)
    # a metade de baixo do tecido da manga cai um pouco (volume legível sob o antebraço)
    for i, ring in enumerate(full):
        sg = 0.55 * smooth(0.30, 0.90, i / (len(full) - 1))
        for q in ring:
            dz = q.z - path[i].z
            if dz < 0: q.z += dz * sg
    if not quebrada:
        # punho: anel externo termina em face plana, boca de raio 0.10 e parede interna recuada (casca contínua)
        T = fr[-1][0]; U = fr[-1][1]; W = fr[-1][2]; p = path[-1]
        boca = [p + U * (0.10 * math.cos(j / m * TAU)) + W * (0.10 * math.sin(j / m * TAU)) for j in range(m)]
        fundo = [q - T * 0.11 for q in boca]
        return L.loft(full + [boca, fundo], cap_bottom=True, cap_top=True), None
    # manga direita: corta com fratura facetada (3 planos, degraus); a face do corte usa o material claro
    k = int(len(path) * 0.80); sub = full[:k + 1]; T, U, W = fr[k]; ring = sub[-1]; c = path[k]
    planos = [(0.0, 0.09, 0.6), (0.05, -0.07, 2.5), (0.02, 0.06, 4.4)]
    out = []
    for j, q in enumerate(ring):
        a = j / m * TAU
        d = min(p0 + p1 * math.cos(a - p2) for (p0, p1, p2) in planos) + 0.025 * (hsh(j, 9) - 0.5)
        d = round(d / 0.012) * 0.012
        out.append(q + T * (0.06 + d) + (c - q) * (0.04 + 0.05 * hsh(j, 4)))
    bm = L.loft(sub + [out], cap_bottom=True, cap_top=False)
    vs = [bm.verts.new(v) for v in out]
    ctr = bm.verts.new(sum(out, Vector()) / m + T * -0.03)
    for j in range(m):
        bm.faces.new((ctr, vs[(j + 1) % m], vs[j])).material_index = 1
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, None

# ---------- lascas em plano: corta um canto da casca fechada e tampa o corte (face de "corte")
def lasca(bm, p, n):
    n = Vector(n).normalized()
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=Vector(p), plane_no=n, clear_outer=True)
    bnd = [e for e in bm.edges if e.is_boundary]
    if bnd:
        r = bmesh.ops.holes_fill(bm, edges=bnd, sides=400)
        for f in r['faces']: f.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm

def com_corte(L, nome, bm, bev=None):
    """Cria o objeto de pedra com o 2º slot de material = pedra clara do corte."""
    o = L.new_obj(nome, bm); o.data.materials.append(L.M['corte'])
    if bev: L.bevel_obj(o, *bev)
    return o

# ---------- bota de pedra (lado aberto): biqueira arredondada, sola e cano, três cascas unidas por boolean
def _rr(w, h, n=10, e=4.0):
    """Seção retangular arredondada (superelipse) de meia-largura w e meia-altura h; lista de (x, z)."""
    out = []
    for j in range(n):
        a = j / n * TAU; c, s_ = math.cos(a), math.sin(a)
        out.append((w * math.copysign(abs(c) ** (2 / e), c), h * math.copysign(abs(s_) ** (2 / e), s_)))
    return out

def _obj_tmp(bm, name):
    import bpy
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); return o

def _uniao(a, b):
    import bpy
    m = a.modifiers.new("u", 'BOOLEAN'); m.operation = 'UNION'; m.solver = 'EXACT'; m.object = b
    bpy.context.view_layer.objects.active = a; bpy.ops.object.modifier_apply(modifier="u")
    bpy.data.objects.remove(b)

def bota(L, cx, y0, comp, yaw, nome):
    c, s_ = math.cos(yaw), math.sin(yaw)
    def pos(x, y, z):  # gira em torno do calcanhar
        dx, dy = x - cx, y - y0
        return Vector((cx + dx * c - dy * s_, y0 + dx * s_ + dy * c, z))
    zb = L.ZP - 0.012
    # peito do pé: cresce do calcanhar, sobe no peito e cai arredondado na biqueira
    ts = [0.0, 0.06, 0.28, 0.52, 0.72, 0.86, 0.95, 1.0]
    ws = [0.095, 0.108, 0.106, 0.114, 0.120, 0.106, 0.075, 0.036]
    hs = [0.170, 0.185, 0.165, 0.130, 0.108, 0.095, 0.072, 0.040]
    rings = []
    for t, w, h in zip(ts, ws, hs):
        rings.append([pos(cx + x, y0 + t * comp, zb + h + z) for (x, z) in _rr(w, h)])
    pe = _obj_tmp(L.loft(rings, True, True), nome + "_pe")
    # sola: placa fina e um pouco mais larga, ponta redonda
    sr = []
    for t, w in zip([0.0, 0.05, 0.5, 0.88, 0.97, 1.0], [0.085, 0.118, 0.126, 0.124, 0.09, 0.04]):
        sr.append([pos(cx + x, y0 + t * comp + 0.012, zb + 0.026 + z) for (x, z) in _rr(w, 0.026, 10, 3.0)])
    so = _obj_tmp(L.loft(sr, True, True), nome + "_sola")
    # cano: cilindro levemente afunilado com punho (borda) em cima, sobe sob o manto
    cr = []
    for z, r in [(zb, 0.112), (zb + 0.20, 0.104), (zb + 0.36, 0.102), (zb + 0.375, 0.126), (zb + 0.43, 0.124), (zb + 0.44, 0.102)]:
        cr.append([pos(cx + r * math.cos(k / 12 * TAU), y0 + 0.095 + r * 0.95 * math.sin(k / 12 * TAU), z) for k in range(12)])
    ca = _obj_tmp(L.loft(cr, True, True), nome + "_cano")
    _uniao(pe, so); _uniao(pe, ca)
    me = pe.data; me.materials.clear(); import bpy; bpy.data.objects.remove(pe); return me

# ---------- cinto, nó e pontas
def cinto(L, nth, bm_ouro=None):
    bm = bmesh.new(); cs = []; ns = []
    for i in range(nth):
        th = i / nth * TAU; p = superficie(L, th, L.Z_WAIST, 0.036, 0.4)
        q = Vector((p.x, p.y, 0)); ns.append(q.normalized()); cs.append(Vector((p.x, p.y, L.Z_WAIST)) + q.normalized() * 0.0)
    closed_tube(bm, cs, ns, 8, lambda i, j, a: 0.034 * (1 + 0.32 * math.cos(3 * a + i * 0.55)))
    return bm

def ponta(L, th0, deriva, comp, rad0):
    path = []
    for k in range(14):
        t = k / 13; z = L.Z_WAIST - 0.03 - comp * t
        path.append(superficie(L, th0 + deriva * t, z, 0.026 + 0.004 * math.sin(t * 6)))
    rings, fr = sweep_rings(path, Vector((0, 0, 1)), 8, lambda s, a: rad0 * (1 + 0.25 * math.cos(3 * a + s * 14)) * (1.0 + 0.7 * smooth(0.85, 1.0, s)))
    return L.loft(rings, True, True)

def no(L, th0):
    p = superficie(L, th0, L.Z_WAIST - 0.01, 0.040)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for v in bm.verts:
        j = 0.8 + 0.4 * hsh(int(v.co.x * 97 + v.co.y * 53 + v.co.z * 31) % 997, 2)
        v.co = Vector((v.co.x * 0.07 * j, v.co.y * 0.045 * j, v.co.z * 0.055 * j)) + p
    return bm

# ---------- ouro
def prisma_hex(L, c, r_ext, r_int, h, rot=0.0):
    """Hexágono (anel se r_int>0), eixo +Y para fora, espessura h a partir de c."""
    bm = bmesh.new(); n = 6
    def pts(r, y): return [bm.verts.new(c + Vector((r * math.cos(rot + k / n * TAU), y, r * math.sin(rot + k / n * TAU)))) for k in range(n)]
    if r_int <= 0:
        a = pts(r_ext, 0); b = pts(r_ext, h)
        for k in range(n): bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
        bm.faces.new(a[::-1]); bm.faces.new(b)
    else:
        a = pts(r_ext, 0); b = pts(r_ext, h); ci = pts(r_int, h); di = pts(r_int, 0)
        for k in range(n):
            k1 = (k + 1) % n
            bm.faces.new((a[k], a[k1], b[k1], b[k])); bm.faces.new((b[k], b[k1], ci[k1], ci[k]))
            bm.faces.new((ci[k], ci[k1], di[k1], di[k])); bm.faces.new((di[k], di[k1], a[k1], a[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return bm

def medalhao(L):
    zc = 2.10; y = superficie(L, math.pi / 2, zc, 0.0).y - 0.02
    c = Vector((0, y, zc)); res = []
    res.append(prisma_hex(L, c, 0.118, 0.088, 0.058, math.pi / 6))              # aro
    res.append(prisma_hex(L, c + Vector((0, 0.008, 0)), 0.090, 0, 0.040, math.pi / 6))  # placa
    res.append(prisma_hex(L, c + Vector((0, 0.040, 0)), 0.052, 0, 0.032, 0.0))      # emblema central girado
    res.append(prisma_hex(L, c + Vector((0, 0.068, 0)), 0.024, 0, 0.014, math.pi / 6))
    return res

def corrente(L, lado):
    s_ = lado
    def ponto(t):
        x = s_ * (0.035 + 0.095 * t); z = 2.205 + (2.565 - 2.205) * t - 0.035 * math.sin(math.pi * t) * 0.0
        th = math.atan2(1, 1)
        # y na superfície do corpo ou da capa (o maior), por x
        yb = L.prof(B_PROF, z) * math.sqrt(max(0.0, 1 - (x / L.prof(A_PROF, z)) ** 2))
        ya = L.prof(CB_PROF, z) * math.sqrt(max(0.0, 1 - (x / L.prof(CA_PROF, z)) ** 2)) if z > 2.2 else 0.0
        return Vector((x, max(yb, ya) + 0.016 + 0.02 * math.sin(math.pi * t) * 0.0, z))
    pts = [ponto(k / 18) for k in range(19)]
    rings, fr = sweep_rings(pts, Vector((0, 1, 0)), 4, lambda s, a: 0.0095 if int(s * 36) % 2 == 0 else 0.0062)
    return L.loft(rings, True, True)

def placas_barra(L):
    saida = []; n = 26
    for k in range(n):
        if hsh(k, 11) < 0.22: continue                      # algumas placas faltando
        th0 = k / n * TAU + 0.02; th1 = th0 + TAU / n * 0.78
        if NOTCH_LO - 0.03 < th0 < NOTCH_HI + 0.03: continue  # no vão aberto não há barra externa
        z0 = L.ZP + 0.045 + 0.01 * hsh(k, 12); z1 = z0 + 0.052
        rings = []
        for s in range(4):
            th = th0 + (th1 - th0) * s / 3
            ring = []
            for zz, off in ((z0, 0.024), (z1, 0.024), (z1, -0.015), (z0, -0.015)):
                p = superficie(L, th, zz + 0.004, off); ring.append(p)
            rings.append(ring)
        bm = L.loft(rings, True, True); o = L.new_obj(f"filete_{k}", bm, "ouro"); saida.append(o)
    return saida

def gola(L):
    bm = bmesh.new(); n = 24; cs = []; ns = []
    for i in range(n):
        th = i / n * TAU; p = Vector((0.232 * math.cos(th), 0.205 * math.sin(th), L.Z_NECK + 0.005)); cs.append(p)
        ns.append(Vector((math.cos(th), math.sin(th), 0)))
    closed_tube(bm, cs, ns, 8, lambda i, j, a: 0.042 * (1 + 0.12 * math.cos(6 * a + i)))
    return bm

# ---------- rachaduras: sulcos finos reais (polilinhas em (graus, z)) afundando os vértices da casca
RACHADURAS = [
    [(80, 2.08), (77, 1.93), (81, 1.78), (78, 1.62), (84, 1.47), (82, 1.32), (88, 1.17), (85, 1.02)],
    [(28, 1.95), (32, 1.78), (27, 1.60), (34, 1.42), (31, 1.22), (35, 1.05)],
    [(214, 2.12), (211, 1.92), (217, 1.72), (213, 1.45), (219, 1.2)],
    [(150, 1.62), (153, 1.4), (148, 1.2)],
]
def groove(th, z, raio):
    """Profundidade (m) do sulco em (th, z): perfil em V, largura ~1,3 cm."""
    best = 1e9
    for pl in RACHADURAS:
        for (t0, z0), (t1, z1) in zip(pl, pl[1:]):
            ax, az = math.radians(t0) * raio, z0; bx, bz = math.radians(t1) * raio, z1
            dt = (th - 0 + math.pi) % TAU - math.pi
            px = ((th - math.radians(t0) + math.pi) % TAU - math.pi) * raio + ax
            vx, vz = bx - ax, bz - az; wx, wz = px - ax, z - az
            t = max(0.0, min(1.0, (wx * vx + wz * vz) / (vx * vx + vz * vz)))
            d = math.hypot(wx - vx * t, wz - vz * t)
            best = min(best, d)
    w = 0.019
    return 0.016 * max(0.0, 1.0 - best / w)

def build(L):
    nth = 120
    # corpo (manto): grade com anéis mais densos perto do chão
    rings = []
    K = 36
    for k in range(K + 1):
        u = k / K; z = L.ZP - 0.02 + (L.Z_NECK - L.ZP + 0.02) * (u ** 1.15)
        ring = []
        for i in range(nth):
            th = i / nth * TAU; x, y = corpo_xy(L, th, max(z, L.ZP), True)
            g = groove(th, z, 0.4)
            if g > 0:
                r = math.hypot(x, y); x *= (r - g) / r; y *= (r - g) / r
            ring.append(Vector((x, y, z)))
        rings.append(ring)
    bm = L.loft(rings, True, True)
    lasca(bm, (0.27, 0.19, 0.985), (0.5, 0.55, -0.66))      # lasca na barra, canto frontal direito
    lasca(bm, (-0.19, -0.27, 0.99), (-0.4, -0.6, -0.7))     # lasca na barra, atrás
    com_corte(L, "corpo_manto", bm)
    bm = capa(L, 96)
    com_corte(L, "corpo_capa", bm, (0.006, 1, 40))
    for lado, q in ((-1, False), (1, True)):
        bm, _ = manga(L, lado, q); com_corte(L, "manga_%s" % ("esq" if lado < 0 else "dir"), bm, (0.006, 1, 40))
    for cx, yaw, nm in ((-0.34, math.radians(14), "bota_e"), (-0.08, math.radians(-4), "bota_d")):
        me = bota(L, cx, 0.10, 0.60, yaw, nm); o = L.new_obj(nm, me); L.bevel_obj(o, 0.006, 2, 35)
    L.new_obj("cinto", cinto(L, 60))
    th0 = math.pi / 2 - 0.10
    L.new_obj("cinto_no", no(L, th0))
    L.new_obj("cinto_ponta1", ponta(L, th0, -0.10, 0.62, 0.028))
    L.new_obj("cinto_ponta2", ponta(L, th0 + 0.02, 0.18, 0.46, 0.026))
    o = L.new_obj("colar", gola(L)); L.bevel_obj(o, 0.004, 1, 40)
    for k, bm in enumerate(medalhao(L)):
        o = L.new_obj(f"medalhao_{k}", bm, "ouro"); L.bevel_obj(o, 0.005, 1, 40)
    for s in (-1, 1): L.new_obj("corrente_%d" % s, corrente(L, s), "ouro")
    placas_barra(L)
    for o in L.objs: print("  ", o.name, len(o.data.polygons))
    tot = sum(len(o.data.polygons) for o in L.objs); print("corpo faces:", tot)
