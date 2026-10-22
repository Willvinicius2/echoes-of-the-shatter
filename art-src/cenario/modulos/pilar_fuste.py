"""Fuste do pilar da Cripta (z 1.1 a 6.4): núcleo em fiadas, 8 colunetas com capitel de quadrifólio,
painéis de blocos rachados (3 faces; a frente +Y é do agente do nicho), cornija em degraus,
coroamento quebrado, entulho e musgo. Pivô no centro, z=0 no chão, frente +Y. Usa só pilar_lib (L)."""
import math, bpy, bmesh
from mathutils import Vector, Matrix

PI = math.pi
FACES = {"frente": 0.0, "esq": PI / 2, "costas": PI, "dir": -PI / 2}   # ângulo Z de cada face
HALF = 0.95            # meia largura do núcleo
Z0, Z1 = 1.10, 4.75    # fuste: base e cornija


def W(u, w, v, a):
    """Coordenada local da face (u lateral, w para fora, v altura) -> mundo."""
    return Vector((u * math.cos(a) - w * math.sin(a), u * math.sin(a) + w * math.cos(a), v))


def join_from(L, start, nome):
    """Junta os objetos criados a partir de L.objs[start:] num só e devolve."""
    grp = L.objs[start:]
    if len(grp) < 2:
        if grp: grp[0].name = nome
        return grp[0] if grp else None
    bpy.ops.object.select_all(action='DESELECT')
    for o in grp: o.select_set(True)
    bpy.context.view_layer.objects.active = grp[0]
    bpy.ops.object.join()
    o = bpy.context.object; o.name = nome
    del L.objs[start:]; L.objs.append(o)
    return o


def blk(L, u, w, v, sx, sy, sz, a, m=None, ez=0.0, **kw):
    if kw.get("chip"): kw["bev"] = 0.0   # a lasca já dá a quina viva; bevel só infla triângulos
    return L.rock(W(u, w, v, a), (sx, sy, sz), m, rot=(0, 0, a + ez), **kw)


def ribbon(L, pts, widths, w0, w1, a):
    """Cutter de fissura: faixa em zigue-zague (u,v) extrudada em w, já girada para a face."""
    n = len(pts); left = []; right = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        nr = Vector((-d.y, d.x))
        left.append(p + nr * widths[i]); right.append(p - nr * widths[i])
    poly = left + right[::-1]
    bm = bmesh.new()
    A = [bm.verts.new((q.x, w0, q.y)) for q in poly]
    B = [bm.verts.new((q.x, w1, q.y)) for q in poly]
    bm.faces.new(A[::-1]); bm.faces.new(B)
    k = len(poly)
    for i in range(k):
        bm.faces.new((A[i], A[(i + 1) % k], B[(i + 1) % k], B[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(a, 4, 'Z'), verts=bm.verts)
    return L.from_bm(bm, L.MAT["escura"], "crack")


def crack(L, u, v, ang, nseg, w0, w1, a, wid=0.014):
    pts = [Vector((u, v))]; wd = [wid]
    d = ang
    for i in range(nseg):
        d = ang + (0.75 if i % 2 else -0.75) * L.rnd.uniform(0.5, 1.2)
        ln = L.rnd.uniform(0.07, 0.15)
        pts.append(pts[-1] + Vector((math.cos(d), math.sin(d))) * ln)
        wd.append(max(0.004, wid * (1 - (i + 1) / (nseg + 1))))
    return ribbon(L, pts, wd, w0, w1, a), pts


def quadrifolio(L, u0, v0, wf, a, r=0.075, dep=0.085):
    """Cutter da cruz trilobada (quadrifólio): contorno = união de 4 lóbulos (cúspides entre eles), em 3 anéis:
    boca larga (bisel/chanfro), borda e fundo a `dep` m de profundidade. Malha única fechada, voltada para fora (w)."""
    c = r * 0.9
    n = 72
    def rad(t):
        best = 0.0
        for k in range(4):
            ph = k * PI / 2
            d = t - ph
            disc = r * r - (c * math.sin(d)) ** 2
            if disc > 0:
                best = max(best, c * math.cos(d) + math.sqrt(disc))
        return best
    base = [rad(2 * PI * i / n) for i in range(n)]
    bm = bmesh.new()
    rings = []
    for (w, sc) in ((0.035, 1.28), (-0.03, 1.0), (-dep, 0.88)):
        rings.append([bm.verts.new((u0 + base[i] * sc * math.cos(2 * PI * i / n), w, v0 + base[i] * sc * math.sin(2 * PI * i / n))) for i in range(n)])
    for j in range(2):
        for i in range(n):
            bm.faces.new((rings[j][i], rings[j][(i + 1) % n], rings[j + 1][(i + 1) % n], rings[j + 1][i]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[2])
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, wf, 0)), verts=bm.verts)
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(a, 4, 'Z'), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return L.from_bm(bm, L.MAT["escura"], "quadri")


def bool_self(o, cutters):
    for c in cutters:
        md = o.modifiers.new("b", 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = c
        md.solver = 'EXACT'; md.use_self = True
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=md.name)


def coluneta(L, u0, a, lado):
    wc = 0.99
    # base em 3 degraus + toro (anel) + filete
    blk(L, u0, wc, 1.16, 0.44, 0.38, 0.12, a, bev=0.012, chip=0.02, cuts_pre=1, seg=1)
    blk(L, u0, wc, 1.265, 0.37, 0.31, 0.09, a, bev=0.01, seg=1)
    blk(L, u0, wc, 1.335, 0.32, 0.27, 0.05, a, bev=0.008, seg=1)
    blk(L, u0, wc, 1.375, 0.285, 0.235, 0.03, a, bev=0.006, seg=1)   # anel fino
    # fuste em tambores com junta; filetes (anéis) nas emendas e entre-eixos
    zs = [1.39, 2.30, 3.20, 3.92]
    for i in range(3):
        h = zs[i + 1] - zs[i] - 0.02
        blk(L, u0, wc, (zs[i] + zs[i + 1]) / 2, 0.24, 0.20, h, a, bev=0.010, chip=0.016, rough=0.005,
            cuts_pre=2, seg=1, jit=0.003)
    for z in (2.30, 3.20):
        blk(L, u0, wc, z, 0.305, 0.255, 0.05, a, bev=0.008, seg=1)
        blk(L, u0, wc, z + 0.05, 0.27, 0.225, 0.03, a, bev=0.006, seg=1)
    # colarinho do capitel em degraus
    blk(L, u0, wc, 3.95, 0.30, 0.25, 0.05, a, bev=0.008, seg=1)
    blk(L, u0, wc, 3.995, 0.34, 0.285, 0.04, a, bev=0.008, seg=1)
    # sino do capitel, mais largo em cima, + quadrifólio vazado com bisel
    blk(L, u0, wc, 4.10, 0.29, 0.245, 0.17, a, bev=0.008, seg=1)
    cap = blk(L, u0, wc, 4.33, 0.40, 0.32, 0.32, a, bev=0.012, seg=1)
    q = quadrifolio(L, 0, 0, 0.0, a)
    q.location = W(u0, wc + 0.16, 4.33, a)
    bool_self(cap, [q]); bpy.data.objects.remove(q, do_unlink=True); L.objs.remove(q)
    # paredes e fundo do vazado em pedra escura (fundo escuro legível)
    cap.data.materials.append(L.MAT["escura"]); ie = len(cap.data.materials) - 1
    ca_, sa_ = math.cos(a), math.sin(a)
    for p in cap.data.polygons:
        c = p.center
        uu = c.x * ca_ + c.y * sa_ - u0; ww = -c.x * sa_ + c.y * ca_
        if abs(uu) < 0.17 and abs(c.z - 4.33) < 0.17 and ww < wc + 0.16 - 0.012:
            p.material_index = ie
    # ábaco em 2 lajes (a de baixo recuada)
    blk(L, u0, wc, 4.535, 0.46, 0.36, 0.09, a, bev=0.01, chip=0.02, cuts_pre=2, seg=1)
    blk(L, u0, wc, 4.65, 0.50, 0.39, 0.13, a, bev=0.012, chip=0.03, rough=0.005, cuts_pre=2, seg=1)


def fiadas(L, total0, total1, rng, lo=0.30, hi=0.46):
    """Alturas de fiadas aleatórias que somam exatamente total1-total0."""
    hs = []; z = total0
    while z < total1 - 0.3:
        h = rng.uniform(lo, hi); hs.append(h); z += h
    k = (total1 - total0) / sum(hs)
    return [h * k for h in hs]


def painel(L, a, face_seed):
    """Alvenaria: fiadas horizontais retas de alturas diferentes, blocos retos de larguras variadas (aparelho
    com juntas desencontradas), peças grandes ocasionais, juntas fundas na argamassa escura, cantos lascados e
    fissuras. Cada face usa uma semente própria (assimétrica)."""
    import random
    rng = random.Random(face_seed)
    g = 0.045
    # argamassa escura recuada
    L.rock(W(0, 0.935, (Z0 + Z1) / 2 + 0.02, a), (1.92, 0.04, Z1 - Z0 - 0.02), L.MAT["escura"], rot=(0, 0, a), bev=0.0)
    start_b = len(L.objs)
    z = Z0 + 0.05
    top = Z1 - 0.01
    hs = []; zz = z
    while zz < top - 0.25:
        h = rng.choice([0.24, 0.30, 0.36, 0.44, 0.52, 0.28, 0.40]); hs.append(h); zz += h
    k = (top - z) / sum(hs); hs = [h * k for h in hs]
    for ci, h in enumerate(hs):
        # larguras da fiada; começa deslocada para desencontrar as juntas
        x = -0.97; widths = []
        x += -rng.uniform(0.0, 0.35)
        while x < 0.97:
            w = rng.choice([0.42, 0.55, 0.70, 0.90, 1.05, 0.48, 0.64])
            widths.append((x, x + w)); x += w
        for (xa, xb) in widths:
            xa = max(xa, -0.97); xb = min(xb, 0.97)
            bw = xb - xa - g
            if bw < 0.2: continue
            bh = h - g + rng.uniform(-0.012, 0.012)
            proud = rng.uniform(0.035, 0.085)
            th = 0.12
            ch = min(0.03, bw * 0.08, bh * 0.1)
            blk(L, (xa + xb) / 2, 0.935 + proud + 0.02 - th / 2 + 0.02, z + h / 2 + rng.uniform(-0.004, 0.004), bw, th, bh, a,
                chip=ch, rough=0.006, cuts_pre=1 if (bw < 0.5 or bh < 0.34) else 2, seg=1, jit=0.0, ez=rng.uniform(-0.006, 0.006))
        z += h
    blocos = join_from(L, start_b, "painel_blocos")
    # fissuras: sulcos reais (poucas, uma delas longa)
    cut = []
    for i in range(2):
        u = rng.uniform(-0.6, 0.6); v = rng.uniform(2.2, 4.3)
        c, pts = crack(L, u, v, rng.uniform(-2.2, -1.0), rng.randint(6, 9), 0.985, 1.2, a, 0.02)
        cut.append(c)
        if rng.random() < 0.8:
            kk = rng.randint(2, 4); p = pts[kk]
            c2, _ = crack(L, p.x, p.y, rng.uniform(-0.6, 0.6) + (PI if rng.random() < 0.5 else 0), 4, 0.985, 1.2, a, 0.014)
            cut.append(c2)
    for c in cut: L.objs.remove(c)
    bpy.ops.object.select_all(action='DESELECT')
    for c in cut: c.select_set(True)
    bpy.context.view_layer.objects.active = cut[0]; bpy.ops.object.join()
    cj = bpy.context.object
    bool_self(blocos, [cj]); bpy.data.objects.remove(cj, do_unlink=True)
    return blocos


def anel(L, H, z0, z1, rng, m=None, nmin=2, chip=0.012):
    """Anel de cornija: barras de comprimento variado (juntas desencontradas), frente/costas inteiras e
    laterais entre elas; espessura t chega ao núcleo."""
    t = H - 0.90
    for a in (0.0, PI, PI / 2, -PI / 2):
        span = H if a in (0.0, PI) else H - t
        pos = -span; cuts = [-span]
        while pos < span - 0.35:
            pos += rng.uniform(0.55, 1.0); cuts.append(min(pos, span))
        if cuts[-1] < span: cuts.append(span)
        if cuts[-1] - cuts[-2] < 0.3 and len(cuts) > 2: cuts.pop(-2)
        for i in range(len(cuts) - 1):
            lw = cuts[i + 1] - cuts[i]
            blk(L, (cuts[i] + cuts[i + 1]) / 2, H - t / 2, (z0 + z1) / 2, lw - 0.02, t, z1 - z0, a, m, bev=0.008,
                chip=chip, rough=0.0, cuts_pre=1, seg=1, jit=0.0)


def calota(L, x, y, z, s, rot=0.0):
    """Calota de musgo: meia esfera facetada achatada, meio enterrada."""
    r = L.rnd
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.5)
    for v in bm.verts:
        n = 1 + r.uniform(-0.16, 0.16)
        v.co = Vector((v.co.x * n, v.co.y * n, v.co.z * r.uniform(0.8, 1.15)))
    sx, sy, sz = s * r.uniform(1.1, 1.7), s * r.uniform(1.1, 1.7), s * r.uniform(0.28, 0.5)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector((x, y, z))) @ Matrix.Rotation(rot, 4, 'Z') @ Matrix.Diagonal((sx, sy, sz, 1)), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return L.from_bm(bm, L.MAT["musgo"], "musgo")


def musgo(L, x, y, z, s, rot=0.0):
    """Tufo irregular: calotas sobrepostas de tamanhos diferentes."""
    r = L.rnd
    for k in range(r.choice([2, 3, 3, 4])):
        d = s * 0.55
        calota(L, x + r.uniform(-d, d), y + r.uniform(-d, d), z + r.uniform(0, s * 0.12),
               s * (1.0 if k == 0 else r.uniform(0.45, 0.8)), rot + r.uniform(0, 6))


def build(L):
    rng = L.rnd
    # (1) núcleo em fiadas (fuste_nucleo)
    s0 = len(L.objs)
    z = Z0; hs = fiadas(L, Z0, Z1, rng)
    for h in hs:
        L.rock(Vector((0, 0, z + h / 2)), (1.90, 1.90, h - 0.012), L.MAT["pedra"], bev=0.0, chip=0.03, cuts_pre=2, seg=1)
        z += h
    join_from(L, s0, "fuste_nucleo")

    # (3) painéis nas 3 faces sem nicho
    for nome, sd in (("esq", 101), ("costas", 202), ("dir", 303)):
        painel(L, FACES[nome], sd)

    # (2) 8 colunetas
    for nome, a in FACES.items():
        for lado in (-0.70, 0.70):
            coluneta(L, lado, a, lado)

    # (4) cornija em degraus
    for (H_, z0_, z1_) in ((1.12, 4.75, 4.82), (1.19, 4.82, 4.92), (1.14, 4.92, 4.98), (1.25, 4.98, 5.04), (1.31, 5.04, 5.10)):
        anel(L, H_, z0_, z1_, rng)

    # (5) coroamento: preenchimento + anel de blocos grandes (alguns faltando)
    L.rock(Vector((0, 0, 5.30)), (1.90, 1.90, 0.40), L.MAT["escura"], bev=0.0)
    H, t = 1.30, 0.50
    slots = []
    for a in (0.0, PI, PI / 2, -PI / 2):
        n = 3 if a in (0.0, PI) else 2
        span = 2 * H if n == 3 else 2 * (H - t)
        for i in range(n):
            slots.append((a, n, i, span))
    estado = {2: "falta", 5: "quebrado", 7: "falta", 3: "quebrado", 9: "quebrado"}
    vazios = []
    for k, (a, n, i, span) in enumerate(slots):
        lw = span / n
        u = -span / 2 + lw * (i + 0.5)
        st = estado.get(k, "ok")
        if st == "falta":
            vazios.append(W(u, H - t / 2, 5.5, a)); continue
        h = rng.uniform(0.50, 0.58)
        sx = lw - 0.03
        if st == "quebrado":
            h *= 0.55; sx *= 0.75; u += rng.uniform(-0.1, 0.1)
        blk(L, u, H - t / 2, 5.1 + h / 2, sx, t, h, a, bev=0.0, chip=0.05, rough=0.008, cuts_pre=3, seg=1,
            jit=0.01, ez=rng.uniform(-0.04, 0.04))
    # coroamento desabado: lajes quebradas de borda irregular, em camadas, algumas inclinadas
    def laje(x, y, zc, w, tilt, mat=None):
        # laje retangular de borda reta com cantos lascados, assentada quase plana
        L.rock(Vector((x, y, zc)), (w * rng.uniform(0.95, 1.15), w * rng.uniform(0.7, 0.95), 0.2 + 0.1 * w), mat,
               rot=(rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt), rng.choice([0, 1.5708]) + rng.uniform(-0.09, 0.09)),
               bev=0.01, chip=0.06, rough=0.008, cuts_pre=3, seg=1, jit=0.008)
    L.rock(Vector((0, 0, 5.62)), (1.9, 1.9, 0.12), L.MAT["escura"], bev=0.0, chip=0.05, rough=0.01, cuts_pre=3, seg=1, jit=0.03)  # terra entre as lajes
    for (x, y) in ((-0.55, -0.55), (0.55, -0.55), (-0.55, 0.55), (0.55, 0.55), (0.0, 0.0), (0.0, -0.85)):
        laje(x + rng.uniform(-.12, .12), y + rng.uniform(-.12, .12), 5.72, rng.uniform(0.85, 1.05), 0.03)
    for v in vazios:
        laje(v.x * 0.85, v.y * 0.85, 5.68, 0.8, 0.05)
    for (x, y) in ((-0.3, 0.2), (0.4, -0.1), (-0.1, -0.5), (0.3, 0.55)):
        laje(x + rng.uniform(-.1, .1), y + rng.uniform(-.1, .1), 5.92, rng.uniform(0.6, 0.8), 0.06)
    for (x, y) in ((0.1, 0.1), (-0.3, -0.25)):
        laje(x, y, 6.10, rng.uniform(0.45, 0.6), 0.1)
    for _ in range(6):  # cascalho miúdo nas fendas
        L.boulder(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(5.7, 5.95))), (0.16, 0.14, 0.1), None,
                  rot=(0, 0, rng.uniform(0, 6)), pts=10, bev=0.006)
    # blocos caídos na cornija (frente e costas)
    laje(0.7, 1.22, 5.2, 0.35, 0.15); laje(-0.6, -1.25, 5.2, 0.32, 0.15)

    # (6) musgo em tufos de calotas: cantos, base das colunetas, topo da cornija, frestas e topo
    cantos = [(HALF + 0.03, HALF + 0.03), (-HALF - 0.03, HALF + 0.03), (HALF + 0.03, -HALF - 0.03), (-HALF - 0.03, -HALF - 0.03)]
    for cx, cy in cantos:
        for _ in range(3):
            musgo(L, cx + rng.uniform(-0.03, 0.03), cy + rng.uniform(-0.03, 0.03), rng.uniform(1.4, 4.4), rng.uniform(0.10, 0.18))
    for a in FACES.values():
        for u0 in (-0.70, 0.70):
            p = W(u0 + rng.uniform(-.12, .12), 1.05, 1.42, a); musgo(L, p.x, p.y, p.z, 0.15)
            p = W(u0 + rng.uniform(-.1, .1), 1.18, 1.22, a); musgo(L, p.x, p.y, p.z, 0.12)
        for z, w_ in ((4.82, 1.0), (5.10, 1.05)):   # topo dos degraus da cornija
            for _ in range(2):
                p = W(rng.uniform(-1.0, 1.0), w_ + rng.uniform(0.0, 0.2), z, a); musgo(L, p.x, p.y, p.z, rng.uniform(0.18, 0.3))
        for _ in range(3):   # frestas entre fiadas nas faces sem nicho
            if a == 0.0: continue
            p = W(rng.uniform(-0.9, 0.9), 1.03, rng.uniform(1.5, 3.9), a); musgo(L, p.x, p.y, p.z, rng.uniform(0.07, 0.12))
    for _ in range(9):
        musgo(L, rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0), rng.uniform(5.7, 6.1), rng.uniform(0.2, 0.34))
