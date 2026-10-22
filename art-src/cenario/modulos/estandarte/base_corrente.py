"""Parte base_corrente do estandarte: plinto de pedra lascada com musgo + duas correntes de elos ferrugentos.
Metros, +Z para cima. Plinto centrado em x=PX (fuste do poste sobe de z=0.30, fica livre)."""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix


# ------------------------------------------------------------------ textura da ferrugem (256x256, periodica)
def _ruido(n, rnd, corte):
    """Ruido periodico passa-baixa via FFT (tile sem emenda)."""
    f = rnd.standard_normal((n, n))
    F = np.fft.fft2(f)
    fx = np.fft.fftfreq(n)[:, None]; fy = np.fft.fftfreq(n)[None, :]
    F *= np.exp(-((fx ** 2 + fy ** 2) / (corte ** 2)))
    r = np.real(np.fft.ifft2(F)); r -= r.min(); r /= (r.max() + 1e-9)
    return r


def _textura_ferrugem(path):
    from PIL import Image
    rnd = np.random.default_rng(7)
    n = 256
    grande = _ruido(n, rnd, 0.03)     # manchas largas
    medio = _ruido(n, rnd, 0.09)
    fino = _ruido(n, rnd, 0.35)       # grao
    mancha = np.clip(grande * 0.6 + medio * 0.4, 0, 1)
    # cores: marrom escuro -> laranja ferrugem -> ocre claro
    escuro = np.array([0.30, 0.14, 0.07]); laranja = np.array([0.74, 0.34, 0.11]); ocre = np.array([0.90, 0.54, 0.22])
    t = np.clip((mancha - 0.38) / 0.22, 0, 1)[..., None]
    img = escuro * (1 - t) + laranja * t
    img *= (0.7 + 0.6 * medio[..., None])
    pontos = np.clip((fino - 0.72) / 0.2, 0, 1)[..., None] * (medio[..., None] > 0.45)
    img = img * (1 - pontos * 0.8) + ocre * pontos * 0.8            # pustulas de ferrugem viva
    # desgaste: veios de metal escuro polido (cinza azulado) em faixas ao longo de u
    veio = _ruido(n, rnd, 0.5)
    faixa = np.clip((veio - 0.78) / 0.12, 0, 1)[..., None]
    metal = np.array([0.50, 0.46, 0.43])
    img = img * (1 - faixa * 0.7) + metal * faixa * 0.7
    # riscos escuros finos (sujeira nas juntas)
    suj = np.clip((0.3 - medio) / 0.3, 0, 1)[..., None]
    img *= (1 - suj * 0.35)
    img *= (0.85 + fino[..., None] * 0.3)
    img = img * 1.7
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(path)


# ------------------------------------------------------------------ helpers de malha
def _novo(L, nome, bm, m):
    return L.new_obj(nome, bm, m)


def _cortar(o, loc, size, rot):
    """Subtrai um cubo girado (boolean exato) do objeto: lasca ou fenda."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    c = bpy.context.object; c.scale = size; bpy.ops.object.transform_apply(scale=True)
    mod = o.modifiers.new("cut", 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = c; mod.solver = 'EXACT'
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="cut")
    bpy.data.objects.remove(c, do_unlink=True)


def _facetas(o, loc, size, r, n):
    """Facetas de cinzel: cortes rasos e planos nas faces (pedra talhada a mao), rotacionados."""
    for _ in range(n):
        k = r.randint(0, 2); sg = r.choice((-1, 1))
        e = [0, 0, 0]; e[k] = sg
        t = [r.uniform(-0.35, 0.35) * size[i] if i != k else 0 for i in range(3)]
        prof = r.uniform(0.002, 0.006)
        p = [loc[i] + e[i] * (size[i] / 2 + 0.012 - prof) + t[i] for i in range(3)]
        sc = [r.uniform(0.07, 0.15) if i != k else 0.024 for i in range(3)]
        rot = [r.uniform(-0.12, 0.12) for _ in range(3)]
        _cortar(o, p, sc, rot)


def _lascas_aresta(o, loc, size, r, n):
    """Lascas alongadas ao longo das arestas: entalhes em V como pedra quebrada na quina."""
    for _ in range(n):
        k = r.randint(0, 2)
        p = [0, 0, 0]; rot = [0, 0, 0]
        for i in range(3):
            if i == k: p[i] = loc[i] + r.uniform(-0.35, 0.35) * size[i]
            else: p[i] = loc[i] + r.choice((-1, 1)) * size[i] / 2
        c = r.uniform(0.018, 0.035)
        sc = [c, c, c]; sc[k] = r.uniform(0.25, 0.55) * size[k]
        rot[k] = math.radians(45 + r.uniform(-8, 8))
        rot[(k + 1) % 3] = r.uniform(-0.1, 0.1)
        _cortar(o, p, sc, rot)


def _bloco(L, m, loc, size, r, rz=0.0, jit=0.014, bev=0.003, lascas=3, lasca=0.04, fendas=1, facetas=4):
    """Bloco de pedra: cubo com cantos deslocados, bevel, lascas de canto, facetas de cinzel e fendas reais."""
    for tentativa in range(6):
        o = _bloco_try(L, loc, size, r, jit, bev, lascas, lasca, fendas, facetas)
        bm = bmesh.new(); bm.from_mesh(o.data)
        ok = all(e.is_manifold for e in bm.edges) and bm.calc_volume() > 0.7 * size[0] * size[1] * size[2]
        bm.free()
        if ok: break
        bpy.data.objects.remove(o, do_unlink=True)
    o.rotation_euler.z = rz
    L.add(o, m)
    return o


def _bloco_try(L, loc, size, r, jit, bev, lascas, lasca, fendas, facetas):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.scale = size; bpy.ops.object.transform_apply(scale=True)
    for v in o.data.vertices:
        v.co += Vector((r.uniform(-jit, jit), r.uniform(-jit, jit), r.uniform(-jit * 0.7, jit * 0.7)))
    L.bevel_obj(o, bev, 1)
    L.chip_corners(o, lascas, lasca, r.randint(0, 99999))
    _lascas_aresta(o, loc, size, r, 4)
    _facetas(o, loc, size, r, facetas)
    for _ in range(fendas):
        dx, dy, dz = size
        ang = r.uniform(0, math.pi)
        p = (loc[0] + r.uniform(-dx * 0.3, dx * 0.3), loc[1] + r.uniform(-dy * 0.3, dy * 0.3), loc[2] + dz / 2 + 0.004)
        _cortar(o, p, (r.uniform(0.10, 0.2), 0.004, 0.016), (r.uniform(-0.15, 0.15), r.uniform(-0.15, 0.15), ang))
    return o


def _camada(L, m, r, cx, cy, s, z0, h, nlin, ncol, g, **kw):
    """Camada de blocos: linhas com divisoes desiguais, juntas de g, alturas levemente diferentes."""
    lins = sorted([0.0, 1.0] + [r.uniform(0.3, 0.7) for _ in range(nlin - 1)])
    for i in range(nlin):
        ya = cy - s / 2 + s * lins[i] + (g / 2 if i else 0); yb = cy - s / 2 + s * lins[i + 1] - (g / 2 if i < nlin - 1 else 0)
        cols = sorted([0.0, 1.0] + [min(0.75, max(0.25, 1 / ncol * (j + 1) + r.uniform(-0.12, 0.12))) for j in range(ncol - 1)])
        for j in range(ncol):
            xa = cx - s / 2 + s * cols[j] + (g / 2 if j else 0); xb = cx - s / 2 + s * cols[j + 1] - (g / 2 if j < ncol - 1 else 0)
            alt = h * r.uniform(0.9, 1.0)
            _bloco(L, m, ((xa + xb) / 2, (ya + yb) / 2, z0 + alt / 2), (xb - xa, yb - ya, alt), r, rz=r.uniform(-0.03, 0.03), **kw)


def _lasca_solta(L, m, loc, r, tam):
    """Pedrinha poligonal caida: casco convexo de pontos aleatorios, apoiada no chao."""
    bm = bmesh.new()
    pts = [Vector((r.uniform(-1, 1) * tam, r.uniform(-1, 1) * tam * r.uniform(0.6, 1.0), r.uniform(0, 1) * tam * 0.55)) for _ in range(9)]
    for p in pts: bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=list(bm.verts))
    bm.verts.ensure_lookup_table()
    zmin = min(v.co.z for v in bm.verts)
    rot = Matrix.Rotation(r.uniform(0, 6.28), 4, 'Z')
    bmesh.ops.transform(bm, matrix=Matrix.Translation((loc[0], loc[1], -zmin * 0.85)) @ rot, verts=bm.verts)
    return _novo(L, "lasca", bm, m)


def _musgo(L, m, c, raio, r, alt=0.016):
    """Tufo baixo de musgo: calota irregular de poucos poligonos + algumas laminas."""
    bm = bmesh.new()
    n = r.randint(7, 9)
    topo = bm.verts.new((c[0], c[1], c[2] + alt * r.uniform(1.0, 1.5)))
    anel_in = []; anel_out = []
    for i in range(n):
        a = i / n * 6.283 + r.uniform(-0.2, 0.2)
        ro = raio * r.uniform(0.6, 1.2); ri = ro * 0.55
        anel_out.append(bm.verts.new((c[0] + math.cos(a) * ro, c[1] + math.sin(a) * ro, c[2] + 0.002)))
        anel_in.append(bm.verts.new((c[0] + math.cos(a) * ri, c[1] + math.sin(a) * ri, c[2] + alt * r.uniform(0.6, 1.1))))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((anel_out[i], anel_out[j], anel_in[j], anel_in[i]))
        bm.faces.new((anel_in[i], anel_in[j], topo))
    # laminas (tetraedros finos) de musgo
    for _ in range(r.randint(2, 4)):
        a = r.uniform(0, 6.283); d = raio * r.uniform(0.1, 0.8)
        bx, by = c[0] + math.cos(a) * d, c[1] + math.sin(a) * d
        h = alt * r.uniform(1.1, 1.7); w = 0.006
        b0 = bm.verts.new((bx - w, by - w, c[2] + alt * 0.5)); b1 = bm.verts.new((bx + w, by - w * 0.5, c[2] + alt * 0.5))
        b2 = bm.verts.new((bx, by + w, c[2] + alt * 0.5)); pt = bm.verts.new((bx + r.uniform(-0.008, 0.008), by + r.uniform(-0.008, 0.008), c[2] + h))
        bm.faces.new((b0, b1, pt)); bm.faces.new((b1, b2, pt)); bm.faces.new((b2, b0, pt))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _novo(L, "musgo", bm, m)


# ------------------------------------------------------------------ tubos (elos e gancho)
def _tubo(bm, pts, w_axis, rn, rw, lados, fechado, u_mult=1.0, u_off=0.0):
    """Varre secao eliptica (rn no plano, rw fora do plano) ao longo da polilinha. UVs por laco (sem emenda visivel)."""
    uv = bm.loops.layers.uv.verify()
    N = len(pts)
    aneis = []
    for i, p in enumerate(pts):
        a = pts[(i + 1) % N] if (fechado or i < N - 1) else p
        b = pts[(i - 1) % N] if (fechado or i > 0) else p
        t = (a - b).normalized()
        n = w_axis.cross(t).normalized()
        anel = []
        for j in range(lados):
            ph = j / lados * 6.283185
            anel.append(bm.verts.new(p + n * (rn * math.cos(ph)) + w_axis * (rw * math.sin(ph))))
        aneis.append(anel)
    M = N if fechado else N - 1
    for i in range(M):
        i2 = (i + 1) % N
        for j in range(lados):
            j2 = (j + 1) % lados
            f = bm.faces.new((aneis[i][j], aneis[i2][j], aneis[i2][j2], aneis[i][j2]))
            f.smooth = False
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                lp[uv].uv = (u_off + ii / N * u_mult, jj / lados)
    if not fechado:  # tampas
        for anel, inv in ((aneis[0], True), (aneis[-1], False)):
            f = bm.faces.new(list(reversed(anel)) if inv else anel)
            for lp in f.loops: lp[uv].uv = (0.5, 0.5)


def _elo(bm, centro, t, w_axis, Lc, Rw, r, rnd):
    """Um elo oval grosso: pista (2 semicirculos + retas) no plano (t, n); secao ligeiramente achatada."""
    n = w_axis.cross(t).normalized()
    ch = Lc - Rw   # distancia do centro ao centro do semicirculo
    pts = []
    K = 10
    for k in range(K + 1):   # semicirculo de cima
        a = math.pi * k / K
        pts.append(centro + t * (ch + Rw * math.sin(a)) + n * (Rw * -math.cos(a)))
    for k in range(K + 1):   # semicirculo de baixo
        a = math.pi * k / K
        pts.append(centro - t * (ch + Rw * math.sin(a)) + n * (Rw * math.cos(a)))
    # remove duplicatas de juncao
    lim = []
    for p in pts:
        if not lim or (p - lim[-1]).length > 1e-5: lim.append(p)
    if (lim[0] - lim[-1]).length < 1e-5: lim.pop()
    _tubo(bm, lim, w_axis, r * 1.02, r * 0.94, 8, True, u_mult=1.5, u_off=rnd.random())


def _corrente(L, m, x0, z_topo, comp, bow, nome, rnd):
    """Corrente pendurada: gancho em S no braco + elos alternando 90 graus, leve curva (catenaria rasa)."""
    r = 0.0105; Lc = 0.027; Rw = 0.0135; passo = 0.034
    # curva de centro: x desloca suavemente, z cai
    def curva(s):
        u = s / comp
        return Vector((x0 + bow * (u ** 1.6), 0.0, z_topo - s * (1 - 0.5 * (bow / comp) ** 2)))
    # reamostra por comprimento de arco
    dens = [curva(i * comp / 400) for i in range(401)]
    centros = []; acc = 0.0; alvo = 0.0; ult = dens[0]
    centros.append(dens[0])
    for p in dens[1:]:
        acc += (p - ult).length; ult = p
        if acc >= passo * len(centros): centros.append(p)
    bm = bmesh.new()
    Y = Vector((0, 1, 0))
    for i, c in enumerate(centros):
        a = centros[min(i + 1, len(centros) - 1)]; b = centros[max(i - 1, 0)]
        t = (b - a).normalized()          # aponta para cima ao longo da corrente
        w = t.cross(Y).normalized() if i % 2 == 0 else Y
        _elo(bm, c, t, w, Lc, Rw, r, rnd)
    # gancho em S (plano XZ, eixo fora do plano = Y); termina enganchado no 1o elo
    hb = centros[0].z + Lc + 0.0   # topo do 1o elo (linha de centro)
    pts = []
    R1 = 0.042; R2 = 0.026
    cu = Vector((x0, 0, hb + 0.0 + 0.0))  # ajustado abaixo
    # arco de cima: centro em (x0, zc1); parte baixa do arco inferior toca o topo do elo
    zc2 = hb - 0.0105 - 0.012 + R2       # centro do arco inferior (fio passa por dentro do elo)
    zc1 = zc2 + R2 + 0.0 + R1 * 0.0 + 0.0
    zc1 = zc2 + R2                         # topo do arco inferior = fundo do arco superior
    cu = Vector((x0, 0, zc1 + R1 - R1))   # centro arco superior em zc1 ... fundo em zc1-R1? ver abaixo
    # arco superior: circulo de raio R1 cujo ponto de baixo e (x0, zc2+R2)
    cu = Vector((x0, 0, zc2 + R2 + R1))
    cl = Vector((x0, 0, zc2))
    for k in range(0, 19):   # sup: de 40 a 270 graus (CCW), termina embaixo indo para +x
        a = math.radians(40 + (270 - 40) * k / 18)
        pts.append(cu + Vector((math.cos(a) * R1, 0, math.sin(a) * R1)))
    for k in range(1, 22):   # inf: do topo (90) girando CW ate -160
        a = math.radians(90 - (90 + 160) * k / 21)
        pts.append(cl + Vector((math.cos(a) * R2, 0, math.sin(a) * R2)))
    _tubo(bm, pts, Y, r * 1.0, r * 1.0, 8, False, u_mult=3.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _novo(L, nome, bm, m)
    return o


# ------------------------------------------------------------------ build
def build(L):
    PX, ARM_Z, AX1 = L.PX, L.ARM_Z, L.AX1
    r = L.rng(2026)
    pedra = L.mat("M_PedraEscura", (0.16, 0.16, 0.19), rough=0.9)
    musgo = L.mat("M_Musgo", (0.24, 0.28, 0.07), rough=0.95)
    tex = os.path.join(L.TEX_DIR, "ferrugem_corrente.png")
    _textura_ferrugem(tex)
    ferro = L.mat("M_Ferrugem", (0.4, 0.2, 0.08), metal=0.05, rough=0.7, image=tex)

    cx, cy = PX, 0.0
    # ---------- plinto: 3 niveis escalonados, blocos separados por juntas, argamassa escura recuada por baixo
    s1, h1, s2, z2, s3, z3, g = 0.70, 0.12, 0.54, 0.12, 0.40, 0.22, 0.014
    L.box((cx, cy, 0.045), (s1 - 0.05, s1 - 0.05, 0.09), pedra, bev=0.0)
    _camada(L, pedra, r, cx, cy, s1, 0.0, h1, 2, 3, g, lascas=3, lasca=0.035, fendas=1, facetas=5, bev=0.006)
    L.box((cx, cy, z2 + 0.04), (s2 - 0.05, s2 - 0.05, 0.08), pedra, bev=0.0)
    _camada(L, pedra, r, cx, cy, s2, z2, 0.10, 2, 2, g, lascas=3, lasca=0.03, fendas=1, facetas=4, bev=0.005)
    _bloco(L, pedra, (cx, cy, z3 + 0.04), (s3, s3, 0.08), r, rz=0.05, jit=0.006, bev=0.010, lascas=4, lasca=0.035, fendas=2, facetas=6)

    # ---------- lascas soltas no chao
    nl = 0
    tent = 0
    while nl < 14 and tent < 200:
        tent += 1
        a = r.uniform(0, 6.283); d = r.uniform(0.40, 0.78)
        dx, dy = math.cos(a) * d, math.sin(a) * d
        if max(abs(dx), abs(dy)) < 0.39: continue
        tam = r.choice((0.022, 0.03, 0.04, 0.05))
        _lasca_solta(L, pedra, (cx + dx, cy + dy, 0), r, tam)
        nl += 1

    # ---------- musgo: tufos baixos nas bordas dos degraus e no chao junto das pedras
    def topo(s, z, n, m):
        for _ in range(n):
            lado = r.randint(0, 3); t = r.uniform(-0.45, 0.45) * s; e = s / 2 - r.uniform(0.01, 0.07)
            p = [(e, t), (-e, t), (t, e), (t, -e)][lado]
            _musgo(L, musgo, (cx + p[0], cy + p[1], z), r.uniform(0.03, 0.07), r)
    topo(s1, h1 * 0.96, 6, musgo)
    topo(s2, z2 + 0.095, 4, musgo)
    topo(s3, 0.30, 3, musgo)
    for _ in range(4):
        a = r.uniform(0, 6.283); d = r.uniform(0.38, 0.5)
        _musgo(L, musgo, (cx + math.cos(a) * d, cy + math.sin(a) * d, 0.0), r.uniform(0.03, 0.05), r, alt=0.012)

    # ---------- correntes
    _corrente(L, ferro, AX1 - 0.05, ARM_Z - 0.115, 0.80, 0.03, "corrente_longa", r)
    _corrente(L, ferro, PX + 0.10, ARM_Z - 0.115, 0.35, 0.02, "corrente_curta", r)
