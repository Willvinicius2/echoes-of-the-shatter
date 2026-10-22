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


def quadrifolio(L, u0, v0, wf, a, r=0.05, dep=0.075):
    """Cutter do quadrifólio: 4 lóbulos redondos + losango central, voltado para fora (w)."""
    bm = bmesh.new(); off = r * 0.95
    for du, dv in ((off, 0), (-off, 0), (0, off), (0, -off)):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r, radius2=r, depth=dep * 2,
                              matrix=Matrix.Translation((u0 + du, 0, v0 + dv)) @ Matrix.Rotation(PI / 2, 4, 'X'))
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((u0, 0, v0)) @ Matrix.Diagonal((r * 1.5, dep * 2, r * 1.5, 1)))
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
    # base em degraus
    blk(L, u0, wc, 1.16, 0.42, 0.36, 0.12, a, bev=0.012, chip=0.02, cuts_pre=1, seg=1)
    blk(L, u0, wc, 1.27, 0.35, 0.29, 0.10, a, bev=0.01, chip=0.015, cuts_pre=1, seg=1)
    blk(L, u0, wc, 1.345, 0.30, 0.25, 0.05, a, bev=0.01, seg=1)   # filete da base
    # fuste em tambores com junta, filete no meio
    zs = [1.37, 2.30, 3.20, 3.94]
    for i in range(3):
        h = zs[i + 1] - zs[i] - 0.014
        blk(L, u0, wc, (zs[i] + zs[i + 1]) / 2, 0.25, 0.21, h, a, bev=0.012, chip=0.018, rough=0.006,
            cuts_pre=2, seg=1, jit=0.004)
    blk(L, u0, wc, 2.30, 0.30, 0.25, 0.06, a, bev=0.01, seg=1)
    blk(L, u0, wc, 3.97, 0.30, 0.25, 0.07, a, bev=0.01, seg=1)      # colarinho
    # corpo do capitel + quadrifólio
    cap = blk(L, u0, wc, 4.27, 0.38, 0.30, 0.40, a, bev=0.012, chip=0.025, cuts_pre=3, seg=1)
    q = quadrifolio(L, 0, 0, 0.0, a)   # criado na origem, move para a posição certa
    q.location = W(u0, wc + 0.15 - 0.06, 4.29, a) - Vector((0, 0, 0))
    bool_self(cap, [q]); bpy.data.objects.remove(q, do_unlink=True); L.objs.remove(q)
    # ábaco
    blk(L, u0, wc, 4.62, 0.44, 0.33, 0.26, a, bev=0.014, chip=0.03, rough=0.006, cuts_pre=3, seg=1)


def fiadas(L, total0, total1, rng, lo=0.30, hi=0.46):
    """Alturas de fiadas aleatórias que somam exatamente total1-total0."""
    hs = []; z = total0
    while z < total1 - 0.3:
        h = rng.uniform(lo, hi); hs.append(h); z += h
    k = (total1 - total0) / sum(hs)
    return [h * k for h in hs]


def painel(L, a):
    """Mortar escuro + blocos irregulares com juntas fundas + fissuras na face a."""
    rng = L.rnd
    g = 0.035
    start = len(L.objs)
    # camada de argamassa escura (juntas fundas)
    L.rock(W(0, 0.945, (Z0 + Z1) / 2 + 0.02, a), (1.92, 0.04, Z1 - Z0 - 0.02), L.MAT["escura"], rot=(0, 0, a), bev=0.0)
    mort = L.objs[-1]
    start_b = len(L.objs)
    zc = Z0 + 0.06
    spans = [(-0.97, -0.87), (-0.55, 0.55), (0.87, 0.97)]
    for h in fiadas(L, Z0 + 0.06, Z1 - 0.02, rng, 0.28, 0.46):
        zmid = zc + h / 2
        for (u_a, u_b) in spans:
            wsp = u_b - u_a
            n = max(1, round(wsp / rng.uniform(0.36, 0.55))) if wsp > 0.3 else 1
            cuts = sorted(rng.uniform(0.3, 0.7) for _ in range(n - 1)) if n > 1 else []
            edges = [u_a] + [u_a + c * wsp for c in cuts] + [u_b]
            # equaliza para não sair bloco minúsculo
            edges = [u_a + (u_b - u_a) * i / n + (rng.uniform(-0.08, 0.08) if 0 < i < n else 0) for i in range(n + 1)]
            for i in range(n):
                bw = edges[i + 1] - edges[i] - g
                if bw < 0.04: continue
                partes = [(h, 0.0)]
                if h > 0.34 and bw > 0.3 and rng.random() < 0.3:
                    f = rng.uniform(0.42, 0.58); partes = [(h * f, -h * (1 - f) / 2), (h * (1 - f), h * f / 2)]
                for ph, dz in partes:
                    bh = ph - g + rng.uniform(-0.015, 0.015)
                    proud = rng.uniform(0.04, 0.07)
                    th = 0.12
                    blk(L, (edges[i] + edges[i + 1]) / 2, 0.945 + proud - th / 2 + 0.02, zmid + dz, bw, th, bh, a,
                        chip=min(0.04, bw * 0.3, bh * 0.3), rough=0.009, cuts_pre=1 if (bw < 0.25 or bh < 0.2) else 2, seg=1, jit=0.012)
        zc += h
    blocos = join_from(L, start_b, "painel_blocos")
    # fissuras: sulcos reais
    cut = []
    for i in range(3):
        u = rng.uniform(-0.45, 0.45); v = rng.uniform(2.4, 4.4)
        c, pts = crack(L, u, v, rng.uniform(-2.2, -1.0), rng.randint(6, 9), 0.99, 1.1, a, 0.02)
        cut.append(c)
        if rng.random() < 0.8:   # ramificação
            k = rng.randint(2, 4); p = pts[k]
            c2, _ = crack(L, p.x, p.y, rng.uniform(-0.6, 0.6) + (PI if rng.random() < 0.5 else 0), 4, 0.99, 1.1, a, 0.014)
            cut.append(c2)
    # cutters separados do mundo: cada um num boolean (evita auto-interseção)
    for c in cut: L.objs.remove(c)
    bpy.ops.object.select_all(action='DESELECT')
    for c in cut: c.select_set(True)
    bpy.context.view_layer.objects.active = cut[0]; bpy.ops.object.join()
    cj = bpy.context.object
    bool_self(blocos, [cj]); bpy.data.objects.remove(cj, do_unlink=True)
    return blocos


def anel(L, H, t, z0, z1, a_n, rng, m=None, quebra=False):
    """Barras de cornija formando um anel quadrado de meia largura H, espessura t."""
    for a in (0.0, PI, PI / 2, -PI / 2):
        n = a_n
        L_ = 2 * H
        for i in range(n):
            lw = L_ / n
            u = -H + lw * (i + 0.5)
            sx = lw + (0.02 if i < n - 1 else 0)
            blk(L, u, H - t / 2, (z0 + z1) / 2, sx - 0.012, t, z1 - z0, a, m, bev=0.012, chip=0.012, rough=0.0,
                cuts_pre=1, seg=1, jit=0.0)


def musgo(L, x, y, z, s, rot=0.0):
    """Tufo: 2 gomos achatados e arredondados juntos."""
    r = L.rnd
    for k in range(2):
        d = s * 0.45
        L.rock(Vector((x + r.uniform(-d, d), y + r.uniform(-d, d), z + r.uniform(0, s * 0.12))),
               (s * r.uniform(0.7, 1.1), s * r.uniform(0.7, 1.1), s * r.uniform(0.35, 0.6)), L.MAT["musgo"],
               rot=(0, 0, rot + r.uniform(0, 6)), jit=0.2, bev=0.04, cuts=0, seg=1)


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
    for nome in ("esq", "costas", "dir"):
        painel(L, FACES[nome])

    # (2) 8 colunetas
    for nome, a in FACES.items():
        for lado in (-0.70, 0.70):
            coluneta(L, lado, a, lado)

    # (4) cornija em degraus
    anel(L, 1.18, 0.34, 4.75, 4.88, 3, rng)
    anel(L, 1.24, 0.36, 4.88, 5.00, 3, rng)
    anel(L, 1.30, 0.40, 5.00, 5.10, 4, rng)

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
        blk(L, u, H - t / 2, 5.1 + h / 2, sx, t, h, a, bev=0.0, chip=0.07, rough=0.012, cuts_pre=3, seg=1,
            jit=0.02, ez=rng.uniform(-0.08, 0.08))
    # entulho em camadas
    def pedra(x, y, zc, s):
        sx, sy, sz = (s * rng.uniform(0.8, 1.25), s * rng.uniform(0.8, 1.25), s * rng.uniform(0.6, 1.0))
        L.rock(Vector((x, y, zc)), (sx, sy, sz), None, rot=(rng.uniform(-.5, .5), rng.uniform(-.5, .5), rng.uniform(0, 6.28)),
               bev=0.0, chip=0.05, rough=0.008, cuts_pre=3, seg=1, jit=0.015)
    for _ in range(8):
        pedra(rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0), rng.uniform(5.60, 5.78), rng.uniform(0.42, 0.6))
    for v in vazios:
        pedra(v.x * 0.8, v.y * 0.8, 5.6, 0.5)
    for _ in range(5):
        pedra(rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8), rng.uniform(5.95, 6.1), rng.uniform(0.38, 0.55))
    for _ in range(3):
        pedra(rng.uniform(-0.45, 0.45), rng.uniform(-0.45, 0.45), rng.uniform(6.2, 6.28), rng.uniform(0.32, 0.45))
    # blocos caídos na cornija (frente e costas)
    pedra(0.7, 1.22, 5.2, 0.3); pedra(-0.6, -1.25, 5.2, 0.28)

    # (6) musgo em tufos
    cantos = [(HALF + 0.03, HALF + 0.03), (-HALF - 0.03, HALF + 0.03), (HALF + 0.03, -HALF - 0.03), (-HALF - 0.03, -HALF - 0.03)]
    for cx, cy in cantos:
        for _ in range(4):
            musgo(L, cx + rng.uniform(-0.03, 0.03), cy + rng.uniform(-0.03, 0.03), rng.uniform(1.4, 4.4), rng.uniform(0.12, 0.2))
    for a in FACES.values():
        for u0 in (-0.70, 0.70):
            p = W(u0, 0.99, 1.37, a); musgo(L, p.x, p.y, p.z, 0.16)
            p = W(u0 + rng.uniform(-.1, .1), 1.0, 1.25, a); musgo(L, p.x, p.y, p.z, 0.12)
        for z in (4.9, 5.02):
            p = W(rng.uniform(-1.0, 1.0), 1.1, z + 0.02, a); musgo(L, p.x, p.y, p.z, 0.2)
        p = W(rng.uniform(-0.9, 0.9), 1.15, 5.1, a); musgo(L, p.x, p.y, p.z, 0.22)
    for _ in range(8):
        musgo(L, rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0), rng.uniform(5.6, 6.1), rng.uniform(0.14, 0.24))
