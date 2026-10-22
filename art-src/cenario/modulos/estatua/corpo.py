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
A_PROF = [(0.90, 0.50), (1.20, 0.48), (1.45, 0.465), (1.58, 0.44), (1.68, 0.425), (1.82, 0.31), (2.00, 0.29), (2.20, 0.34), (2.35, 0.40), (2.45, 0.40), (2.52, 0.33), (2.58, 0.215)]
B_PROF = [(0.90, 0.38), (1.20, 0.325), (1.55, 0.262), (1.68, 0.205), (1.85, 0.188), (2.00, 0.205), (2.15, 0.235), (2.30, 0.250), (2.45, 0.235), (2.52, 0.215), (2.58, 0.19)]
FAMILIAS = [(7, 0.105, 1.80, 2.45), (15, 0.058, 1.40, 2.20), (29, 0.024, 1.00, 1.85)]  # (nº de dobras, amplitude no pé, zs mín, zs máx)
NOTCH_C, NOTCH_HW, NOTCH_H = math.radians(136), math.radians(24), 0.62
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
    return math.cos(th) * (a + d + hem), math.sin(th) * (b + d + hem)

def superficie(L, th, z, off=0.0, esc=1.0):
    x, y = corpo_xy(L, th, z, False)
    if esc != 1.0:
        x0 = math.cos(th) * L.prof(A_PROF, z); y0 = math.sin(th) * L.prof(B_PROF, z)
        x = x0 + (x - x0) * esc; y = y0 + (y - y0) * esc
    n = Vector((x, y, 0)); n = n.normalized() if n.length > 1e-6 else Vector((0, 1, 0))
    return Vector((x, y, z)) + n * off

# ---------- capa dos ombros
CA_PROF = [(2.05, 0.505), (2.18, 0.50), (2.32, 0.495), (2.45, 0.485), (2.51, 0.455), (2.555, 0.36), (2.58, 0.23)]
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
            ring.append(Vector((math.cos(th) * (a + d), math.sin(th) * (b + d), z)))
        rings.append(ring)
    return L.loft(rings, cap_bottom=True, cap_top=True)

# ---------- mangas
def manga(L, lado, quebrada):
    s_ = -1.0 if lado < 0 else 1.0
    # braço pende ao lado e o antebraço vem para a frente; a boca do punho esquerdo fica atrás do pulso
    # (parte maos: punho em (-0.06, 0.30, Z_HANDS) apontando f=(0.47, 0.88) subindo 12°)
    f = Vector((0.47 * s_, 0.88, math.tan(math.radians(12)))).normalized()
    fim = Vector((0.13 * s_, 0.17, 1.81))
    P = [Vector((0.40 * s_, -0.03, 2.30)), Vector((0.41 * s_, 0.0, 2.03)), Vector((0.33 * s_, 0.08, 1.84)),
         fim - f * 0.11, fim]
    path = catmull(P, 8)
    m = 20
    R = [(0, 0.115), (0.3, 0.15), (0.55, 0.162), (0.80, 0.17), (0.86, 0.148), (0.885, 0.178), (1.0, 0.178)]
    def rad(s, a):
        r = L.prof(R, s)
        x = 6 * a / TAU + 0.8 * s + (0.3 if lado > 0 else 0)
        env = smooth(0.0, 0.25, s) * (1 - smooth(0.80, 0.86, s))
        return r * (1 - 0.28 * env * crease(x))
    full, fr = sweep_rings(path, Vector((0, 0, 1)), m, rad)
    # manga larga pende: a metade de baixo do tecido cai mais (sino caído sob o antebraço)
    for i, ring in enumerate(full):
        sg = 1.5 * smooth(0.30, 0.90, i / (len(full) - 1))
        for q in ring:
            dz = q.z - path[i].z
            if dz < 0: q.z += dz * sg
    if not quebrada:
        # punho: anel externo termina em face plana, boca de raio 0.09 e parede interna recuada (casca contínua)
        T = fr[-1][0]; U = fr[-1][1]; W = fr[-1][2]; p = path[-1]
        boca = [p + U * (0.09 * math.cos(j / m * TAU)) + W * (0.09 * math.sin(j / m * TAU)) for j in range(m)]
        fundo = [q - T * 0.11 for q in boca]
        return L.loft(full + [boca, fundo], cap_bottom=True, cap_top=True), None
    # manga direita: corta em s=0.72 com fratura facetada (3 planos, degraus), pedra exposta
    k = int(len(path) * 0.74); sub = full[:k + 1]; T, U, W = fr[k]; ring = sub[-1]; c = path[k]
    planos = [(0.0, 0.09, 0.6), (0.05, -0.07, 2.5), (0.02, 0.06, 4.4)]
    out = []
    for j, q in enumerate(ring):
        a = j / m * TAU
        d = min(p0 + p1 * math.cos(a - p2) for (p0, p1, p2) in planos) + 0.025 * (hsh(j, 9) - 0.5)
        d = round(d / 0.012) * 0.012
        out.append(q + T * (0.07 + d) + (c - q) * (0.04 + 0.05 * hsh(j, 4)))
    bm = L.loft(sub + [out], cap_bottom=True, cap_top=False)
    vs = [bm.verts.new(v) for v in out]
    ctr = bm.verts.new(sum(out, Vector()) / m + T * -0.03)
    for j in range(m):
        bm.faces.new((ctr, vs[(j + 1) % m], vs[j]))
    # as faces do anel 'out' foram criadas pelo loft com vértices próprios: soldar
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm, None

# ---------- bota de pedra (lado aberto)
def bota(L):
    cx, y0, y1 = -0.30, 0.20, 0.54
    rings = []
    ys = [y0, y0 + 0.03, y0 + 0.10, y0 + 0.18, y0 + 0.25, y1 - 0.04, y1]
    alt = [0.15, 0.15, 0.13, 0.10, 0.075, 0.05, 0.02]
    larg = [0.07, 0.085, 0.092, 0.09, 0.085, 0.07, 0.04]
    for y, h, w in zip(ys, alt, larg):
        ring = []
        for j in range(8):
            a = j / 8 * TAU + TAU / 16
            px, pz = math.cos(a), math.sin(a)
            ring.append(Vector((cx + px * w * (1.0 if pz > 0 else 1.08), y, L.ZP - 0.01 + max(0.0, (pz * 0.5 + 0.5)) * (h + 0.01) if pz > -0.2 else L.ZP - 0.01)))
        rings.append(ring)
    return L.loft(rings, cap_bottom=True, cap_top=True)

# ---------- cinto, nó e pontas
def cinto(L, nth, bm_ouro=None):
    bm = bmesh.new(); cs = []; ns = []
    for i in range(nth):
        th = i / nth * TAU; p = superficie(L, th, L.Z_WAIST, 0.036, 0.4)
        q = Vector((p.x, p.y, 0)); ns.append(q.normalized()); cs.append(Vector((p.x, p.y, L.Z_WAIST)) + q.normalized() * 0.0)
    closed_tube(bm, cs, ns, 12, lambda i, j, a: 0.034 * (1 + 0.32 * math.cos(3 * a + i * 0.55)))
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

# ---------- montagem
def build(L):
    nth = 160
    # corpo (manto): grade com anéis mais densos perto do chão
    rings = []
    K = 42
    for k in range(K + 1):
        u = k / K; z = L.ZP - 0.02 + (L.Z_NECK - L.ZP + 0.02) * (u ** 1.15)
        ring = []
        for i in range(nth):
            th = i / nth * TAU; x, y = corpo_xy(L, th, max(z, L.ZP), True); ring.append(Vector((x, y, z)))
        rings.append(ring)
    L.new_obj("corpo_manto", L.loft(rings, True, True))
    o = L.new_obj("corpo_capa", capa(L, nth)); L.bevel_obj(o, 0.006, 1, 40)
    for lado, q in ((-1, False), (1, True)):
        bm, _ = manga(L, lado, q); o = L.new_obj("manga_%s" % ("esq" if lado < 0 else "dir"), bm); L.bevel_obj(o, 0.006, 1, 40)
    o = L.new_obj("bota", bota(L)); L.bevel_obj(o, 0.008, 2, 35)
    L.new_obj("cinto", cinto(L, 96))
    th0 = math.pi / 2 - 0.10
    L.new_obj("cinto_no", no(L, th0))
    L.new_obj("cinto_ponta1", ponta(L, th0, -0.10, 0.62, 0.028))
    L.new_obj("cinto_ponta2", ponta(L, th0 + 0.02, 0.18, 0.46, 0.026))
    o = L.new_obj("colar", gola(L)); L.bevel_obj(o, 0.004, 1, 40)
    for k, bm in enumerate(medalhao(L)):
        o = L.new_obj(f"medalhao_{k}", bm, "ouro"); L.bevel_obj(o, 0.005, 1, 40)
    for s in (-1, 1): L.new_obj("corrente_%d" % s, corrente(L, s), "ouro")
    placas_barra(L)
    tot = sum(len(o.data.polygons) for o in L.objs); print("corpo faces:", tot)
