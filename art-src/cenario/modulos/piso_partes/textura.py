"""Texturas do piso (2048², periódicas em 8 m), geradas em numpy a partir do layout das lajotas:
  T_Cripta_Piso_Cor    albedo azul-ardósia: tom/matiz/manchas/veios por lajota, lascas e riscos pintados,
                       umidade escura, juntas com terra escura, sujeira irregular e musgo.
  T_Cripta_Piso_Normal normal (OpenGL, +Y) derivada de um mapa de altura: chanfro irregular nas arestas, grão de pedra,
                       riscos, lascas e juntas fundas.
Projeção planar (u=x/8, v=y/8). O .glb leva as duas imagens embutidas (baseColorTexture + normalTexture)."""
import numpy as np, bpy
from . import comum

_cache = {}

def _ruido(res, celulas, seed):
    """Ruído periódico (filtro gaussiano no espectro), normalizado em [-1, 1]. celulas ~ frequência."""
    k_ = (res, celulas, seed)
    if k_ in _cache: return _cache[k_]
    r = np.random.default_rng(seed); f = np.fft.fft2(r.standard_normal((res, res)))
    k = np.fft.fftfreq(res) * res; kx, ky = np.meshgrid(k, k)
    n = np.real(np.fft.ifft2(f * np.exp(-((kx ** 2 + ky ** 2) / (2 * celulas ** 2)))))
    _cache[k_] = n / np.abs(n).max()
    return _cache[k_]

def _borra(a, raio):
    """Desfoque gaussiano periódico via FFT (raio em px)."""
    N = a.shape[0]; k = np.fft.fftfreq(N); kx, ky = np.meshgrid(k, k)
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (np.pi * raio) ** 2 * (kx ** 2 + ky ** 2))))

def _linhas(N, segs, esp=1.0):
    """Rasteriza segmentos (x0,y0,x1,y1 em px) em máscara 0..1 com largura esp (px)."""
    m = np.zeros((N, N))
    for (a, b, c, d) in segs:
        n = int(max(abs(c - a), abs(d - b)) * 1.5) + 2
        t = np.linspace(0, 1, n)
        xs = np.clip((a + (c - a) * t).astype(int), 0, N - 1); ys = np.clip((b + (d - b) * t).astype(int), 0, N - 1)
        m[ys, xs] = 1
    return _borra(m, esp) * (4 * esp) if esp > 0.4 else m

def _chanfro(fonte, it):
    """Distância (px) até a máscara fonte, por propagação chanfro 8-vizinhos (periódica), saturada em it."""
    d = np.where(fonte, 0.0, 1e3)
    for _ in range(it):
        for dx, dy, w in ((1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (-1, -1, 1.414), (1, -1, 1.414), (-1, 1, 1.414)):
            d = np.minimum(d, np.roll(np.roll(d, dx, 1), dy, 0) + w)
    return np.minimum(d, it)

def _bilin(a, N):
    """Reamostra um campo periódico MxM para NxN (bilinear)."""
    M = a.shape[0]
    if M == N: return a
    c = (np.arange(N) + 0.5) * M / N - 0.5
    i0 = np.floor(c).astype(int); f = c - i0; i1 = (i0 + 1) % M; i0 %= M
    t = a[i0] * (1 - f)[:, None] + a[i1] * f[:, None]
    return t[:, i0] * (1 - f)[None, :] + t[:, i1] * f[None, :]

def _mapas(objs, N, M=1024):
    """Lança raios -Z na MESMA malha das lajotas (Lajotas_* e Junta), grade MxM periódica de 8 m, e devolve em NxN:
    idx (ilha conectada de cada lajota; -1 = junta), dist (m, dentro da lajota até a junta), dj (m, dentro da junta até a lajota),
    nl (nº de ilhas), z (altura do topo)."""
    from mathutils.bvhtree import BVHTree
    verts = []; polys = []; info = []                # info[poly] = (é_junta, ilha global)
    ilha_base = 0
    for o in objs:
        if not (o.name.startswith("Lajotas_") or o.name == "Junta"): continue
        me = o.data; off = len(verts); eh_j = o.name == "Junta"
        verts += [tuple(v.co + o.location) for v in me.vertices]
        pai = list(range(len(me.vertices)))
        def raiz(x):
            while pai[x] != x: pai[x] = pai[pai[x]]; x = pai[x]
            return x
        for p in me.polygons:
            vs = list(p.vertices)
            for v in vs[1:]: pai[raiz(v)] = raiz(vs[0])
        mapa = {}
        for p in me.polygons:
            polys.append(tuple(off + v for v in p.vertices))
            if eh_j: info.append((True, -1)); continue
            rt = raiz(p.vertices[0]); mapa.setdefault(rt, ilha_base + len(mapa))
            info.append((False, mapa[rt]))
        ilha_base += len(mapa)
    bvh = BVHTree.FromPolygons(verts, polys)
    from mathutils import Vector
    dirz = Vector((0, 0, -1)); px = comum.TILE / M
    idx = np.full((M, M), -1, int); z = np.full((M, M), -0.2); jm = np.ones((M, M), bool)
    for j in range(M):
        y = (j + 0.5) * px
        for i in range(M):
            h = bvh.ray_cast(Vector(((i + 0.5) * px, y, 1.0)), dirz)
            if h[0] is None: continue
            eh_j, il = info[h[2]]
            z[j, i] = h[0].z
            if not eh_j:
                idx[j, i] = il; jm[j, i] = False
    # ilhas minúsculas (cacos) viram junta p/ não poluir; limpa buracos de 1 px
    din = _chanfro(jm, 22) * px; dj = _chanfro(~jm, 12) * px
    jf = _bilin(jm.astype(float), N)
    jf = _borra(jf, 1.0)
    junta = jf > 0.5
    # índice: vizinho mais próximo reamostrado, depois forçado à máscara suave
    ii = np.repeat(np.repeat(idx, N // M, 0), N // M, 1)
    ii = np.where(junta, -1, ii)
    ii = np.where((ii < 0) & ~junta, _vizinho(ii, junta), ii)
    din = _bilin(din, N); dj = _bilin(dj, N)
    din = np.where(junta, 0, din); dj = np.where(junta, dj, 0)
    return ii, din, dj, ilha_base, _bilin(z, N), junta

def _vizinho(ii, junta):
    out = ii.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        v = np.roll(np.roll(ii, dx, 1), dy, 0); out = np.where(out < 0, v, out)
    return np.where(out < 0, 0, out)

def _vor(N, nc, seed, warp=0.0):
    """Voronoi periódico (nc células por lado, nc divide N). Devolve F1, F2 (px), valor aleatório da célula mais próxima e seu id.
    warp (px) deforma as bordas das células. Dá grãos ANGULOSOS de borda dura (ao contrário do ruído gaussiano)."""
    r = np.random.default_rng(seed); G = N / nc
    jit = r.random((nc, nc, 2)) * 0.8 + 0.1; val = r.random((nc, nc))
    Y, X = np.mgrid[0:N, 0:N].astype(np.float32) + 0.5
    if warp:
        X = (X + warp * _ruido(N, 14, seed + 500)) % N; Y = (Y + warp * _ruido(N, 14, seed + 501)) % N
    cx = np.floor(X / G).astype(int) % nc; cy = np.floor(Y / G).astype(int) % nc
    f1 = np.full((N, N), 1e9, np.float32); f2 = f1.copy(); v1 = np.zeros((N, N), np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ix = (cx + dx) % nc; iy = (cy + dy) % nc
            px_ = (cx + dx + jit[iy, ix, 0]) * G; py_ = (cy + dy + jit[iy, ix, 1]) * G
            ddx = np.abs(X - px_); ddx = np.minimum(ddx, N - ddx); ddy = np.abs(Y - py_); ddy = np.minimum(ddy, N - ddy)
            d = np.sqrt(ddx * ddx + ddy * ddy)
            novo = d < f1
            f2 = np.where(novo, f1, np.minimum(f2, d)); v1 = np.where(novo, val[iy, ix], v1); f1 = np.where(novo, d, f1)
    return f1, f2, v1

def gerar(objs, N=2048):
    """Retorna (albedo linear HxWx3 em [0,1], altura HxW em metros ficticios), a partir da malha real das lajotas.
    Micro-relevo com feições DURAS (grãos Voronoi, poros de disco, riscos de 1 px, lascas de borda dura, patches definidos)."""
    px = comum.TILE / N
    idx, dist, dj, nl, zm, junta = _mapas(objs, N)
    r = np.random.default_rng(comum.SEED)
    laje = ~junta
    # ---- por lajota: tom e matiz (cinza-ardósia quente da Cripta)
    tom = r.uniform(-0.18, 0.18, nl + 1); matiz = r.uniform(-0.06, 0.06, nl + 1)
    tom[-1] = matiz[-1] = 0
    base = np.array([0.150, 0.140, 0.130])
    t = tom[idx]; m = matiz[idx]
    img = np.empty((N, N, 3))
    for c in range(3): img[..., c] = base[c] * (1 + t) * (1 + m * np.array([-0.9, 0.1, 0.9])[c])
    # ---- manchas definidas por lajota: patches de borda reconhecível (Voronoi grande deformado)
    f1, f2, v = _vor(N, 16, 103, warp=26)
    patch = (v > 0.62) & ((f2 - f1) > 0)
    img *= np.where(patch, 0.68 + 0.62 * ((v * 7.3) % 1.0), 1.0)[..., None]
    bp = np.clip(1 - (f2 - f1) / 2.0, 0, 1) * patch                      # contorno do patch levemente mais escuro
    img *= (1 - 0.18 * bp)[..., None]
    # ---- grão de pedra duro: células angulares de tom próprio, com fio escuro entre elas
    f1, f2, v = _vor(N, 256, 101)
    groove = np.clip(1 - (f2 - f1) / 1.3, 0, 1)
    img *= (1 + 0.40 * (v - 0.5))[..., None] * (1 - 0.10 * groove)[..., None]
    h = np.zeros((N, N))
    h += 0.0020 * v - 0.0016 * groove
    # ---- facetas médias: placas angulares com degrau (relevo de média frequência)
    f1, f2, v = _vor(N, 32, 102, warp=8)
    h += 0.0045 * (v - 0.5)
    gro2 = np.clip(1 - (f2 - f1) / 2.2, 0, 1) * (v > 0.5)
    h -= 0.0030 * gro2; img *= (1 - 0.12 * gro2)[..., None]
    # ondulação suave só do topo da lajota (muito baixa)
    h += 0.0015 * _ruido(N, 10, 63)
    # ---- poros: discos pequenos de borda dura, escuros
    f1, f2, v = _vor(N, 256, 104)
    rad = 1.0 + 2.0 * ((v * 13.7) % 1.0)
    poro = ((f1 < rad) & (v > 0.86) & laje).astype(float)
    h -= 0.0050 * poro; img *= (1 - 0.55 * poro)[..., None]
    # ---- chanfro nas arestas (largura irregular) + desgaste serrilhado de borda dura
    fa, fb, va = _vor(N, 128, 106)
    lar = 0.030 + 0.030 * va
    ch = np.clip(1 - dist / lar, 0, 1)
    h -= 0.018 * ch ** 1.4
    gasto = ((dist < 0.012 + 0.050 * va) & laje).astype(float)
    img *= (1 + 0.40 * gasto)[..., None]
    h += 0.0020 * gasto * (va - 0.5)
    # ---- lascas: recortes de borda dura nas bordas, pedra clara exposta
    fl, fl2, vl = _vor(N, 64, 105, warp=3)
    lasca = ((vl > 0.78) & (dist < 0.025 + 0.11 * ((vl * 9.1) % 1.0)) & laje).astype(float)
    h -= 0.012 * lasca; img *= (1 + 0.32 * lasca)[..., None]
    lasca_b = np.clip(lasca - np.roll(lasca, 1, 0) * np.roll(lasca, 1, 1), 0, 1)
    # ---- riscos retos de 1 px (mais claros e escuros) em direções aleatórias, por lajota
    ys_, xs_ = np.nonzero(idx >= 0); ordem = np.argsort(idx[ys_, xs_], kind="stable")
    ys_, xs_ = ys_[ordem], xs_[ordem]; cortes = np.searchsorted(idx[ys_, xs_], np.arange(nl + 1))
    ilhas = []
    for i in range(nl):
        a_, b_ = cortes[i], cortes[i + 1]
        ilhas.append(None if b_ - a_ < 400 else (xs_[a_:b_], ys_[a_:b_]))
    def pt(l):
        k = r.integers(0, len(l[0])); return float(l[0][k]), float(l[1][k])
    riscos = []; rachs = []
    for l in ilhas:
        if l is None: continue
        for _ in range(r.integers(3, 9)):
            cx, cy = pt(l); a = r.uniform(0, np.pi); L = r.uniform(30, 160)
            riscos.append((cx - np.cos(a) * L / 2, cy - np.sin(a) * L / 2, cx + np.cos(a) * L / 2, cy + np.sin(a) * L / 2))
        if r.random() < 0.30:
            x0, y0 = pt(l); a = r.uniform(0, np.pi)
            for k in range(r.integers(4, 9)):
                a += r.uniform(-0.7, 0.7); L = r.uniform(14, 38); x1, y1 = x0 + np.cos(a) * L, y0 + np.sin(a) * L
                rachs.append((x0, y0, x1, y1)); x0, y0 = x1, y1
                if r.random() < 0.3:
                    ab = a + r.choice([-1, 1]) * r.uniform(0.5, 1.1)
                    rachs.append((x0, y0, x0 + np.cos(ab) * L * 0.8, y0 + np.sin(ab) * L * 0.8))
    risco = _linhas(N, riscos, 0.0) * laje
    rach = np.clip(_linhas(N, rachs, 0.9) * 1.8, 0, 1) * laje
    risco_claro = (risco > 0) & (r.random((N, N)) < 0.35)
    h -= 0.0030 * risco + 0.012 * rach
    img *= np.where(risco_claro, 1.35, 1 - 0.40 * risco)[..., None] * (1 - 0.85 * rach)[..., None]
    # ---- umidade escura e fria (grandes, suaves) perto das juntas + sujeira que escorre + musgo
    umid = np.clip(_ruido(N, 8, 70) * 1.5 - 0.15, 0, 1) * np.clip(0.4 + 0.6 * np.clip(1 - dist / 0.5, 0, 1), 0, 1)
    img *= (1 - 0.30 * umid)[..., None]
    img[..., 0] *= 1 - 0.18 * umid; img[..., 2] *= 1 + 0.30 * umid
    sujo_lim = 0.016 + 0.07 * np.clip(0.5 + 0.7 * _ruido(N, 50, 71) + 0.5 * _ruido(N, 130, 72), 0, 1)
    sujo = np.clip(1 - dist / sujo_lim, 0, 1) ** 0.8
    img *= (1 - 0.75 * sujo)[..., None]
    img[..., 0] *= 1 + 0.25 * sujo; img[..., 1] *= 1 + 0.18 * sujo
    musgo_t = np.clip(_ruido(N, 11, 73) * 2.6 - 0.25, 0, 1) * np.clip(_ruido(N, 90, 74) * 0.5 + 0.8, 0, 1)
    musgo = musgo_t * np.clip(1 - dist / (0.06 + 0.07 * np.clip(_ruido(N, 60, 75), 0, 1)), 0, 1)
    musgo += 0.25 * np.clip(_ruido(N, 6, 76) * 2 - 0.9, 0, 1) * np.clip(umid * 2, 0, 1) * laje
    musgo = np.clip(musgo, 0, 1)
    cor_musgo = np.array([0.045, 0.085, 0.045]) * (1 + 0.4 * _ruido(N, 250, 77))[..., None]
    img = img * (1 - 0.7 * musgo)[..., None] + cor_musgo * (0.7 * musgo)[..., None]
    img = np.clip(img, 0, 0.30)                                         # nunca quase branco
    # ---- juntas: terra escura com cascalho
    terra = np.array([0.020, 0.022, 0.030])
    jc = terra[None, None, :] * (1 + 0.9 * _ruido(N, 160, 80) + 0.6 * _ruido(N, 25, 81))[..., None]
    jc = np.clip(jc, 0.005, 1)
    seixo = np.clip(_ruido(N, 350, 82) * 3 - 1.8, 0, 1)
    jc = jc * (1 + 2.0 * seixo)[..., None]
    jc[..., 0] *= 1.0 + 0.5 * np.clip(_ruido(N, 20, 83), 0, 1)
    jc = jc * (1 - 0.7 * musgo)[..., None] + cor_musgo * (0.8 * musgo)[..., None]
    jc *= (0.55 + 0.45 * np.clip(dj / (comum.JUNTA * 0.5), 0, 1))[..., None]
    img = np.where(junta[..., None], jc, img)
    h = np.where(junta, -0.035 + 0.004 * _ruido(N, 140, 84) + 0.004 * seixo, h)
    return np.clip(img, 0, 1), h

def _normal(h, N, forca=1.0):
    """Mapa de normal (tangente, OpenGL +Y) a partir da altura em metros; periódico via roll. Pixel = TILE/N metros."""
    px = comum.TILE / N
    h = _borra(h, 0.6)
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px) * forca
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * px) * forca
    n = np.stack([-dx, -dy, np.ones_like(h)], axis=-1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5

def aplicar(objs, N=2048):
    """Cria M_Piso_Laje com cor + normal embutidos, troca nas lajotas (M_Piso_Laje_*) e põe UV planar."""
    img, h = gerar(objs, N)
    im = bpy.data.images.new("T_Cripta_Piso_Cor", N, N, alpha=False)
    rgba = np.concatenate([img, np.ones((N, N, 1))], axis=2)
    srgb = np.where(rgba <= 0.0031308, rgba * 12.92, 1.055 * np.power(rgba, 1 / 2.4) - 0.055); srgb[..., 3] = 1
    im.pixels = srgb.astype(np.float32).ravel(); im.pack()
    nm = bpy.data.images.new("T_Cripta_Piso_Normal", N, N, alpha=False)
    nm.colorspace_settings.name = 'Non-Color'
    nrgba = np.concatenate([_normal(h, N), np.ones((N, N, 1))], axis=2)
    nm.pixels = nrgba.astype(np.float32).ravel(); nm.pack()
    m = comum.material("M_Piso_Laje", (0.2, 0.25, 0.35), rough=0.72)
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = im; tx.interpolation = 'Linear'
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = nm; tn.interpolation = 'Linear'
    nmn = nt.nodes.new("ShaderNodeNormalMap"); nmn.inputs["Strength"].default_value = 1.2
    nt.links.new(tn.outputs["Color"], nmn.inputs["Color"]); nt.links.new(nmn.outputs["Normal"], bsdf.inputs["Normal"])
    for o in objs:
        if not any(s.material and s.material.name.startswith("M_Piso_Laje") for s in o.material_slots): continue
        me = o.data; uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                v = me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv = ((v.x + o.location.x) / comum.TILE, (v.y + o.location.y) / comum.TILE)
        me.materials.clear(); me.materials.append(m)
    return m
