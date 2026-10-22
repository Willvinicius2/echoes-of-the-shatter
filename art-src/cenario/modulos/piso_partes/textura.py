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

def _mapas(N):
    """Devolve dict com idx, dist (m, até a aresta da lajota), e as máscaras de composição."""
    px = comum.TILE / N
    ys, xs = (np.mgrid[0:N, 0:N] + 0.5) * px
    idx = np.full((N, N), -1, int); dist = np.zeros((N, N))
    lajes = comum.layout()
    for i, l in enumerate(lajes):
        a, b = int(round(l["x0"] / px)), int(round(l["x1"] / px)); c, d = int(round(l["y0"] / px)), int(round(l["y1"] / px))
        idx[c:d, a:b] = i
        yy, xx = ys[c:d, a:b], xs[c:d, a:b]
        dist[c:d, a:b] = np.minimum(np.minimum(xx - l["x0"], l["x1"] - xx), np.minimum(yy - l["y0"], l["y1"] - yy))
    # distância para dentro da junta (m): aproximada pela distância às lajotas vizinhas, via dilatação do campo
    d_junta = np.zeros((N, N))
    j = idx < 0
    # dentro da junta: distância ao pixel de lajota mais próximo (juntas têm ~11 px, basta checar até 8 px)
    dj = np.full((N, N), 9.0)
    for s in range(1, 9):
        viz = np.zeros((N, N), bool)
        for dx, dy in ((s, 0), (-s, 0), (0, s), (0, -s)):
            viz |= np.roll(np.roll(~j, dx, 1), dy, 0)
        dj = np.where(viz & (dj > 8), s, dj)
    d_junta = dj * px
    return idx, dist, d_junta, len(lajes), lajes

def gerar(N=2048):
    """Retorna (albedo linear HxWx3 em [0,1], altura HxW em metros ficticios)."""
    px = comum.TILE / N
    idx, dist, dj, nl, lajes = _mapas(N)
    junta = idx < 0
    r = np.random.default_rng(comum.SEED)
    # ---- por lajota: tom, matiz, escolha de campo de manchas, inclinação suave
    tom = r.uniform(-0.38, 0.30, nl + 1); matiz = r.uniform(-0.12, 0.12, nl + 1)
    sat = r.uniform(0.75, 1.25, nl + 1); campo = r.integers(0, 4, nl + 1)
    tom[-1] = matiz[-1] = 0; sat[-1] = 1                    # índice -1 (junta) cai no último
    base = np.array([0.050, 0.072, 0.125])                   # azul-ardósia escuro (linear)
    t = tom[idx]; m = matiz[idx]; s_ = sat[idx]
    img = np.empty((N, N, 3))
    for c in range(3):
        # matiz: desloca azul <-> verde-acinzentado/violeta por lajota
        img[..., c] = base[c] * (1 + t) * (1 + m * np.array([-1.2, 0.6, 1.0])[c]) * (1 + (s_ - 1) * (c - 1) * 0.8)
    # ---- manchas pintadas por lajota: 4 campos de ruído diferentes escolhidos por lajota (sem repetição visível)
    F = [_ruido(N, 9, 20 + i) * 0.6 + _ruido(N, 28, 30 + i) * 0.4 for i in range(4)]
    mancha = np.choose(campo[idx], F)
    img *= (1 + 0.50 * mancha)[..., None]
    img *= (1 + 0.10 * _ruido(N, 70, 5) + 0.06 * _ruido(N, 200, 6))[..., None]
    # tom levemente mais quente/escuro em manchas de matiz (frio <-> neutro)
    quente = np.clip(np.choose(campo[idx], [_ruido(N, 14, 40 + i) for i in range(4)]), 0, 1)
    img[..., 0] *= 1 + 0.35 * quente; img[..., 1] *= 1 + 0.12 * quente
    # ---- veios: bandas finas curvas, claras e escuras, ruído deformado
    tem = ((campo[idx] % 2) == 0)
    veio = np.zeros((N, N))
    for k, (cel, sd) in enumerate(((5, 50), (7, 54))):
        n = _ruido(N, cel, sd) + 0.12 * _ruido(N, 30, sd + 1)
        veio = np.maximum(veio, np.clip(1 - np.abs(n) / 0.035, 0, 1) ** 1.5 * (0.5 + 0.5 * k))
    veio *= tem * np.clip(_ruido(N, 4, 52) * 2.5 + 0.3, 0, 1)
    sinal = np.where(_ruido(N, 6, 53) > 0, 0.9, -0.6)
    img *= (1 + 0.8 * veio * sinal)[..., None]
    # grão de cor: pontos claros/escuros de pedra (cristais) e poeira
    gr = _ruido(N, 420, 55); img *= (1 + 0.22 * gr + 0.18 * np.clip(_ruido(N, 260, 56) * 2.2 - 1.2, 0, 1) - 0.10 * np.clip(-_ruido(N, 300, 57) * 2 - 0.6, 0, 1))[..., None]
    # ---- altura base (metros fictícios; escala aplicada no normal)
    h = np.zeros((N, N))
    # grão de pedra
    h += 0.0007 * _ruido(N, 300, 60) + 0.0010 * _ruido(N, 110, 61) + 0.0016 * _ruido(N, 35, 62)
    # ondulação de cada lajota (alturas suavemente diferentes, topo irregular)
    h += 0.0030 * _ruido(N, 12, 63) + 0.003 * (r.uniform(-1, 1, nl + 1)[idx]) * 0.4
    # ---- chanfro irregular nas arestas: largura varia ao longo da aresta
    lar = 0.030 + 0.030 * (0.5 + 0.5 * _ruido(N, 50, 64)) + 0.022 * np.clip(_ruido(N, 14, 65), 0, 1)
    ch = np.clip(1 - dist / lar, 0, 1)
    h -= 0.020 * ch ** 1.6
    # arestas gastas: borda clareada e rugosa
    gasto = np.clip(1 - dist / (0.05 + 0.05 * np.clip(_ruido(N, 22, 66), -0.2, 1)), 0, 1) * np.clip(0.5 + 0.8 * _ruido(N, 100, 67), 0, 1)
    h += 0.004 * gasto * _ruido(N, 140, 68)
    # ---- lascas: quinas e pedaços na borda (blobs onde dist pequeno), fundos e claros
    lasca = np.clip(_ruido(N, 26, 69) * 2.4 - 1.35, 0, 1) * np.clip(1 - dist / 0.14, 0, 1)
    lasca = np.clip(lasca * 2, 0, 1)
    h -= 0.014 * lasca
    # ---- riscos e rachaduras finas por lajota (pintados escuros + fundos no relevo)
    segs = []; segs_f = []
    for i, l in enumerate(lajes):
        if r.random() < 0.45:
            for _ in range(r.integers(1, 3)):
                cx = r.uniform(l["x0"], l["x1"]) / px; cy = r.uniform(l["y0"], l["y1"]) / px
                a = r.uniform(0, np.pi); L = r.uniform(25, 120)
                x0, y0 = cx, cy
                for k in range(r.integers(2, 5)):                    # polilinha quebrada
                    a += r.uniform(-0.6, 0.6); x1, y1 = x0 + np.cos(a) * L / 3, y0 + np.sin(a) * L / 3
                    segs.append((x0, y0, x1, y1)); x0, y0 = x1, y1
        if r.random() < 0.22:                                         # rachadura funda
            cx = r.uniform(l["x0"], l["x1"]) / px; cy = r.uniform(l["y0"], l["y1"]) / px
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
    img *= (1 - 0.55 * umid)[..., None]
    img[..., 2] *= 1 + 0.10 * umid                                      # umidade puxa para azul frio
    # sujeira irregular escorrendo da junta para a lajota
    sujo_lim = 0.016 + 0.07 * np.clip(0.5 + 0.7 * _ruido(N, 50, 71) + 0.5 * _ruido(N, 130, 72), 0, 1)
    sujo = np.clip(1 - dist / sujo_lim, 0, 1) ** 0.8
    img *= (1 - 0.8 * sujo)[..., None]
    img[..., 0] *= 1 + 0.25 * sujo; img[..., 1] *= 1 + 0.18 * sujo      # sujeira puxa para terra
    # musgo: verde-musgo escuro nas juntas e primeiros cm das lajotas, por trechos
    musgo_t = np.clip(_ruido(N, 11, 73) * 2.6 - 0.25, 0, 1) * np.clip(_ruido(N, 90, 74) * 0.5 + 0.8, 0, 1)
    musgo = musgo_t * np.clip(1 - dist / (0.06 + 0.07 * np.clip(_ruido(N, 60, 75), 0, 1)), 0, 1)
    musgo += 0.25 * np.clip(_ruido(N, 6, 76) * 2 - 0.9, 0, 1) * np.clip(umid * 2, 0, 1) * (idx >= 0)
    musgo = np.clip(musgo, 0, 1)
    cor_musgo = np.array([0.045, 0.085, 0.045]) * (1 + 0.4 * _ruido(N, 250, 77))[..., None]
    img = img * (1 - 0.7 * musgo)[..., None] + cor_musgo * (0.7 * musgo)[..., None]
    # ---- bordas: aresta viva clara (fio de luz de pedra gasta) e lascas expondo pedra mais clara
    img *= (1 + 0.55 * gasto)[..., None]
    img[..., 2] *= 1 + 0.1 * gasto
    img *= (1 + 0.5 * lasca)[..., None]
    # riscos e rachaduras escuros pintados
    img *= (1 - 0.55 * risco)[..., None] * (1 - 0.85 * rach)[..., None]
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
    img, h = gerar(N)
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
    nmn = nt.nodes.new("ShaderNodeNormalMap"); nmn.inputs["Strength"].default_value = 1.0
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
