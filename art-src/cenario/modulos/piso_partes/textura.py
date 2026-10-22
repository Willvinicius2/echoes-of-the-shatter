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

def gerar(objs, N=2048):
    """Retorna (albedo linear HxWx3 em [0,1], altura HxW em metros ficticios), a partir da malha real das lajotas."""
    px = comum.TILE / N
    idx, dist, dj, nl, zm, junta = _mapas(objs, N)
    r = np.random.default_rng(comum.SEED)
    # ---- por lajota: tom, matiz, escolha de campo de manchas, inclinação suave
    tom = r.uniform(-0.10, 0.12, nl + 1); matiz = r.uniform(-0.10, 0.10, nl + 1)
    sat = r.uniform(0.75, 1.25, nl + 1); campo = r.integers(0, 4, nl + 1)
    tom[-1] = matiz[-1] = 0; sat[-1] = 1                    # índice -1 (junta) cai no último
    base = np.array([0.215, 0.205, 0.192])                   # cinza-ardósia quente dessaturado (linear)
    t = tom[idx]; m = matiz[idx]; s_ = sat[idx]
    img = np.empty((N, N, 3))
    for c in range(3):
        # matiz: desloca azul <-> verde-acinzentado/violeta por lajota
        img[..., c] = base[c] * (1 + t) * (1 + m * np.array([-0.9, 0.1, 0.9])[c]) * (1 + (s_ - 1) * (c - 1) * 0.3)
    # ---- manchas pintadas por lajota: 4 campos de ruído diferentes escolhidos por lajota (sem repetição visível)
    F = [_ruido(N, 5, 20 + i) * 0.75 + _ruido(N, 14, 30 + i) * 0.25 for i in range(4)]
    mancha = np.choose(campo[idx], F)
    img *= (1 + 0.16 * mancha)[..., None]
    img *= (1 + 0.10 * _ruido(N, 70, 5) + 0.06 * _ruido(N, 200, 6))[..., None]
    # tom levemente mais quente/escuro em manchas de matiz (frio <-> neutro)
    quente = np.clip(np.choose(campo[idx], [_ruido(N, 14, 40 + i) for i in range(4)]), 0, 1)
    img[..., 0] *= 1 + 0.10 * quente; img[..., 1] *= 1 + 0.04 * quente
    # ---- veios: bandas finas curvas, claras e escuras, ruído deformado
    tem = ((campo[idx] % 2) == 0)
    veio = np.zeros((N, N))
    for k, (cel, sd) in enumerate(((5, 50), (7, 54))):
        n = _ruido(N, cel, sd) + 0.12 * _ruido(N, 30, sd + 1)
        veio = np.maximum(veio, np.clip(1 - np.abs(n) / 0.015, 0, 1) ** 1.5 * (0.5 + 0.5 * k))
    veio *= tem * np.clip(_ruido(N, 4, 52) * 2.5 + 0.3, 0, 1)
    sinal = np.where(_ruido(N, 6, 53) > 0, 0.9, -0.6)
    img *= (1 + 0.22 * veio * sinal)[..., None]
    # grão de cor: pontos claros/escuros de pedra (cristais) e poeira
    gr = _ruido(N, 420, 55); img *= (1 + 0.07 * gr + 0.10 * np.clip(_ruido(N, 260, 56) * 2.2 - 1.2, 0, 1) - 0.10 * np.clip(-_ruido(N, 300, 57) * 2 - 0.6, 0, 1))[..., None]
    # ---- altura base (metros fictícios; escala aplicada no normal)
    h = np.zeros((N, N))
    # grão de pedra
    h += 0.00015 * _ruido(N, 420, 60) + 0.0009 * _ruido(N, 150, 61) + 0.0050 * _ruido(N, 60, 62)
    # poros e crateras pequenas (espalhados e mais densos perto das bordas)
    poro = np.clip(_ruido(N, 230, 90) * 3.0 - 2.1, 0, 1) + 0.9 * np.clip(_ruido(N, 150, 91) * 3.0 - 1.9, 0, 1) * np.clip(1 - dist / 0.25, 0, 1)
    poro = np.clip(poro, 0, 1) * (~junta)
    h -= 0.0035 * poro
    # ondulação de cada lajota (alturas suavemente diferentes, topo irregular)
    h += 0.0030 * _ruido(N, 12, 63) + 0.003 * (r.uniform(-1, 1, nl + 1)[idx]) * 0.4
    # ---- chanfro irregular nas arestas: largura varia ao longo da aresta
    lar = 0.030 + 0.030 * (0.5 + 0.5 * _ruido(N, 50, 64)) + 0.022 * np.clip(_ruido(N, 14, 65), 0, 1) + 0.012 * _ruido(N, 160, 92)
    ch = np.clip(1 - dist / lar, 0, 1)
    h -= 0.020 * ch ** 1.6
    # arestas gastas: borda clareada e rugosa
    gasto = np.clip(1 - dist / (0.05 + 0.05 * np.clip(_ruido(N, 22, 66), -0.2, 1)), 0, 1) * np.clip(0.5 + 0.8 * _ruido(N, 100, 67), 0, 1)
    h += 0.010 * gasto * _ruido(N, 200, 68)
    # ---- lascas: quinas e pedaços na borda (blobs onde dist pequeno), fundos e claros
    lasca = np.clip(_ruido(N, 26, 69) * 2.4 - 1.35, 0, 1) * np.clip(1 - dist / 0.14, 0, 1)
    lasca = np.clip(lasca * 2, 0, 1)
    h -= 0.014 * lasca
    # ---- riscos e rachaduras finas por lajota (pintados escuros + fundos no relevo)
    segs = []; segs_f = []
    ys_, xs_ = np.nonzero(idx >= 0); ordem = np.argsort(idx[ys_, xs_], kind="stable")
    ys_, xs_ = ys_[ordem], xs_[ordem]; cortes = np.searchsorted(idx[ys_, xs_], np.arange(nl + 1))
    lajes = []
    for i in range(nl):
        a_, b_ = cortes[i], cortes[i + 1]
        if b_ - a_ < 400: lajes.append(None); continue
        lajes.append(dict(x=xs_[a_:b_], y=ys_[a_:b_]))
    def pt(l):
        k = r.integers(0, len(l["x"])); return float(l["x"][k]), float(l["y"][k])
    for i, l in enumerate(lajes):
        if l is None: continue
        if r.random() < 0.45:
            for _ in range(r.integers(1, 3)):
                cx, cy = pt(l)
                a = r.uniform(0, np.pi); L = r.uniform(25, 120)
                x0, y0 = cx, cy
                for k in range(r.integers(2, 5)):                    # polilinha quebrada
                    a += r.uniform(-0.6, 0.6); x1, y1 = x0 + np.cos(a) * L / 3, y0 + np.sin(a) * L / 3
                    segs.append((x0, y0, x1, y1)); x0, y0 = x1, y1
        if r.random() < 0.22:                                         # rachadura funda
            cx, cy = pt(l)
            a = r.uniform(0, np.pi); x0, y0 = cx, cy
            for k in range(r.integers(4, 9)):
                a += r.uniform(-0.7, 0.7); L = r.uniform(14, 38); x1, y1 = x0 + np.cos(a) * L, y0 + np.sin(a) * L
                segs_f.append((x0, y0, x1, y1)); x0, y0 = x1, y1
                if r.random() < 0.3:                                  # ramo
                    ab = a + r.choice([-1, 1]) * r.uniform(0.5, 1.1)
                    segs_f.append((x0, y0, x0 + np.cos(ab) * L * 0.8, y0 + np.sin(ab) * L * 0.8))
    risco = np.clip(_linhas(N, segs, 0.8) * 1.5, 0, 1) * (idx >= 0)
    rach = np.clip(_linhas(N, segs_f, 1.1) * 1.6, 0, 1) * (idx >= 0)
    h -= 0.0025 * risco + 0.012 * rach
    # ---- umidade escura (manchas grandes, concentradas ao longo das juntas) e musgo
    umid = np.clip(_ruido(N, 8, 70) * 1.5 - 0.15, 0, 1) * np.clip(0.4 + 0.6 * np.clip(1 - dist / 0.5, 0, 1), 0, 1)
    img *= (1 - 0.18 * umid)[..., None]
    img[..., 0] *= 1 - 0.18 * umid; img[..., 2] *= 1 + 0.30 * umid                                      # umidade puxa para azul frio
    # sujeira irregular escorrendo da junta para a lajota
    sujo_lim = 0.016 + 0.07 * np.clip(0.5 + 0.7 * _ruido(N, 50, 71) + 0.5 * _ruido(N, 130, 72), 0, 1)
    sujo = np.clip(1 - dist / sujo_lim, 0, 1) ** 0.8
    img *= (1 - 0.6 * sujo)[..., None]
    img[..., 0] *= 1 + 0.25 * sujo; img[..., 1] *= 1 + 0.18 * sujo      # sujeira puxa para terra
    # musgo: verde-musgo escuro nas juntas e primeiros cm das lajotas, por trechos
    musgo_t = np.clip(_ruido(N, 11, 73) * 2.6 - 0.25, 0, 1) * np.clip(_ruido(N, 90, 74) * 0.5 + 0.8, 0, 1)
    musgo = musgo_t * np.clip(1 - dist / (0.06 + 0.07 * np.clip(_ruido(N, 60, 75), 0, 1)), 0, 1)
    musgo += 0.25 * np.clip(_ruido(N, 6, 76) * 2 - 0.9, 0, 1) * np.clip(umid * 2, 0, 1) * (idx >= 0)
    musgo = np.clip(musgo, 0, 1)
    cor_musgo = np.array([0.045, 0.085, 0.045]) * (1 + 0.4 * _ruido(N, 250, 77))[..., None]
    img = img * (1 - 0.7 * musgo)[..., None] + cor_musgo * (0.7 * musgo)[..., None]
    # ---- bordas: aresta viva clara (fio de luz de pedra gasta) e lascas expondo pedra mais clara
    img *= (1 + 0.3 * gasto)[..., None]
    img[..., 2] *= 1 + 0.1 * gasto
    img *= (1 + 0.25 * lasca)[..., None]
    # riscos e rachaduras escuros pintados
    img *= (1 - 0.55 * risco)[..., None] * (1 - 0.35 * poro)[..., None] * (1 - 0.85 * rach)[..., None]
    # ---- juntas: terra escura com cascalho, grão, manchas
    terra = np.array([0.020, 0.022, 0.030])
    jc = terra[None, None, :] * (1 + 0.9 * _ruido(N, 160, 80) + 0.6 * _ruido(N, 25, 81))[..., None]
    jc = np.clip(jc, 0.005, 1)
    seixo = np.clip(_ruido(N, 350, 82) * 3 - 1.8, 0, 1)
    jc = jc * (1 + 2.0 * seixo)[..., None]
    jc[..., 0] *= 1.0 + 0.5 * np.clip(_ruido(N, 20, 83), 0, 1)           # terra mais marrom em trechos
    jc = jc * (1 - 0.7 * musgo)[..., None] + cor_musgo * (0.8 * musgo)[..., None]
    # juntas mais claras e secas só nos trechos onde há seixo; sombra interna perto da lajota
    jc *= (0.55 + 0.45 * np.clip(dj / (comum.JUNTA * 0.5), 0, 1))[..., None]
    img = np.where(junta[..., None], jc, img)
    # altura nas juntas: funda e granulada
    h = np.where(junta, -0.035 + 0.006 * _ruido(N, 140, 84) + 0.004 * seixo, h)
    return np.clip(img, 0, 1), h

def _normal(h, N, forca=1.0):
    """Mapa de normal (tangente, OpenGL +Y) a partir da altura em metros; periódico via roll. Pixel = TILE/N metros."""
    px = comum.TILE / N
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
    nmn = nt.nodes.new("ShaderNodeNormalMap"); nmn.inputs["Strength"].default_value = 1.4
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
