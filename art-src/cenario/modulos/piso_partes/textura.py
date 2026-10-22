"""Textura de cor do piso (albedo 2048², periódica em 8 m) gerada em numpy a partir do layout das lajotas.
Dá contraste: tom por lajota, manchas pintadas, desgaste claro perto das arestas, escurecimento e sujeira nas juntas.
Mapeada por projeção planar (u=x/8, v=y/8) nas lajotas; o .glb leva a imagem embutida."""
import numpy as np, bpy
from . import comum

def _ruido(res, celulas, seed):
    r = np.random.default_rng(seed); f = np.fft.fft2(r.standard_normal((res, res)))
    k = np.fft.fftfreq(res) * res; kx, ky = np.meshgrid(k, k)
    n = np.real(np.fft.ifft2(f * np.exp(-((kx ** 2 + ky ** 2) / (2 * celulas ** 2)))))
    return n / np.abs(n).max()

def gerar(N=2048):
    px = comum.TILE / N
    ys, xs = (np.mgrid[0:N, 0:N] + 0.5) * px            # linha 0 = y 0
    idx = np.full((N, N), -1, int); dist = np.zeros((N, N))
    lajes = comum.layout()
    dist[:] = 0.0
    for i, l in enumerate(lajes):
        a, b = int(l["x0"] / px), int(l["x1"] / px); c, d = int(l["y0"] / px), int(l["y1"] / px)
        idx[c:d, a:b] = i
        yy, xx = ys[c:d, a:b], xs[c:d, a:b]
        dist[c:d, a:b] = np.minimum(np.minimum(xx - l["x0"], l["x1"] - xx), np.minimum(yy - l["y0"], l["y1"] - yy))
    r = np.random.default_rng(comum.SEED)
    tom = r.uniform(-0.16, 0.16, len(lajes) + 1); matiz = r.uniform(-0.05, 0.05, len(lajes) + 1)
    base = np.array([0.21, 0.27, 0.38])                 # azul-ardósia (sRGB linear-ish, o glTF espera sRGB no baseColorTexture)
    img = np.empty((N, N, 3))
    t = tom[idx]; m = matiz[idx]
    for c in range(3): img[..., c] = base[c] * (1 + t + m * (c - 1))
    img *= (1 + 0.20 * _ruido(N, 10, 3) + 0.10 * _ruido(N, 45, 4) + 0.05 * _ruido(N, 160, 5))[..., None]
    # desgaste claro nas arestas (pedra viva) e escurecimento ao entrar na junta
    gasto = np.clip(1 - dist / 0.09, 0, 1) * np.clip(0.5 + 0.7 * _ruido(N, 60, 6), 0, 1)
    img *= (1 + 0.45 * gasto)[..., None]
    manchas = np.clip(_ruido(N, 14, 7) * 1.4 - 0.2, 0, 1)   # sujeira/umidade em manchas
    img *= (1 - 0.35 * manchas)[..., None]
    junta = idx < 0
    img[junta] = np.array([0.045, 0.05, 0.06]) * (1 + 0.5 * _ruido(N, 90, 8))[junta][:, None]
    return np.clip(img, 0, 1)

def aplicar(objs, N=2048):
    """Cria M_Piso_Laje com a imagem, troca nas lajotas (M_Piso_Laje_*) e põe UV planar."""
    img = gerar(N)
    im = bpy.data.images.new("T_Cripta_Piso_Cor", N, N, alpha=False)
    rgba = np.concatenate([img, np.ones((N, N, 1))], axis=2)
    srgb = np.where(rgba <= 0.0031308, rgba * 12.92, 1.055 * np.power(rgba, 1 / 2.4) - 0.055); srgb[..., 3] = 1
    im.pixels = srgb.astype(np.float32).ravel(); im.pack()
    m = comum.material("M_Piso_Laje", (0.2, 0.25, 0.35), rough=0.72)
    nt = m.node_tree; tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = im; tx.interpolation = 'Linear'
    nt.links.new(tx.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    for o in objs:
        if not any(s.material and s.material.name.startswith("M_Piso_Laje") for s in o.material_slots): continue
        me = o.data; uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                v = me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv = ((v.x + o.location.x) / comum.TILE, (v.y + o.location.y) / comum.TILE)
        me.materials.clear(); me.materials.append(m)
    return m
