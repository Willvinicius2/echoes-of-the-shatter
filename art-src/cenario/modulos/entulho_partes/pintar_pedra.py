"""Texturas pintadas de pedra e musgo para o entulho da cripta (numpy + PIL, sem bpy).
Tudo periodico (tile sem emenda): ruido por FFT passa-baixa, rachaduras como isolinhas de ruido deformado.
Uso: gerar(pasta, tam=1024, seed=5) grava pedra_albedo/pedra_normal/musgo_albedo/musgo_normal.png."""
import os
import numpy as np
from PIL import Image


def _ruido(n, rnd, corte, banda=None):
    """Ruido periodico passa-baixa via FFT (0..1). banda: corte menor, subtrai (passa-faixa)."""
    f = rnd.standard_normal((n, n))
    F = np.fft.fft2(f)
    fx = np.fft.fftfreq(n)[:, None]; fy = np.fft.fftfreq(n)[None, :]
    r2 = fx ** 2 + fy ** 2
    F = F * np.exp(-r2 / corte ** 2)
    if banda:
        F = F * (1 - np.exp(-r2 / banda ** 2))
    r = np.real(np.fft.ifft2(F))
    r -= r.min(); r /= (r.max() + 1e-9)
    return r


def _sm(x, a, b):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def _deforma(campo, dx, dy, amp):
    """Deforma um campo periodico por deslocamento (bilinear, com wrap)."""
    n = campo.shape[0]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx + (dx - 0.5) * amp) % n
    y = (yy + (dy - 0.5) * amp) % n
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    x1 = (x0 + 1) % n; y1 = (y0 + 1) % n
    return (campo[y0, x0] * (1 - fx) * (1 - fy) + campo[y0, x1] * fx * (1 - fy)
            + campo[y1, x0] * (1 - fx) * fy + campo[y1, x1] * fx * fy)


def _rachaduras(n, rnd, escala, largura, cobertura):
    """Rachaduras finas irregulares: isolinhas de ruido deformado, mascaradas para aparecerem em trechos."""
    base = _ruido(n, rnd, 0.0065 * escala, banda=0.0012)
    dx = _ruido(n, rnd, 0.02); dy = _ruido(n, rnd, 0.02)
    base = _deforma(base, dx, dy, n * 0.022)
    base = _deforma(base, _ruido(n, rnd, 0.12), _ruido(n, rnd, 0.12), n * 0.012)  # serrilhado fino
    d = np.abs(base - np.median(base)) / (base.std() + 1e-9)
    linha = np.exp(-(d / largura) ** 2)
    # estilhaca em trechos (rachadura nao percorre a textura toda) e ramifica com ruido fino
    trecho = _smooth_mask(_ruido(n, rnd, 0.018), cobertura)
    ramo = _ruido(n, rnd, 0.09)
    linha = linha * trecho * (0.45 + 0.9 * _sm(ramo, 0.3, 0.65))
    return np.clip(linha, 0, 1)


def _smooth_mask(r, cobertura):
    lim = np.quantile(r, 1 - cobertura)
    return _sm(r, lim - 0.06, lim + 0.06)


def _altura_pedra(n, rnd):
    """Campo de altura da pedra: grao + lascas + cinzel raso em terracos. Retorna (h, rach, lasca, terraco)."""
    grande = _ruido(n, rnd, 0.025)
    medio = _ruido(n, rnd, 0.07)
    grao = _ruido(n, rnd, 0.28)
    fino = _ruido(n, rnd, 0.6)
    # cinzel raso: facetas planas (terracos suaves de ruido deformado), nao celulas regulares
    t = _deforma(_ruido(n, rnd, 0.016), _ruido(n, rnd, 0.03), _ruido(n, rnd, 0.03), n * 0.05)
    q = t * 5
    terraco = (np.floor(q) + _sm(q - np.floor(q), 0.96, 1.0)) / 5
    # lascas: concavidades escuras de borda angulosa (limiar de ruido medio-alto)
    lm = _deforma(_ruido(n, rnd, 0.12), _ruido(n, rnd, 0.05), _ruido(n, rnd, 0.05), n * 0.03)
    lasca = _sm(lm, 0.70, 0.74) * _sm(_ruido(n, rnd, 0.04), 0.4, 0.55)
    rach = np.clip(_rachaduras(n, rnd, 1.0, 0.10, 0.6) + 0.8 * _rachaduras(n, rnd, 1.8, 0.08, 0.4), 0, 1)
    hb = (0.22 * terraco + 0.3 * grande + 0.2 * medio - 0.2 * lasca - 0.45 * rach)
    h = (0.4 * terraco + 0.22 * grande + 0.18 * medio + 0.10 * grao + 0.06 * fino
         - 0.20 * lasca - 0.45 * rach)
    return h, rach, lasca, terraco, (grande, medio, grao, fino), hb


def _normal(h, forca):
    """Normal map tangente OpenGL (Y+ para cima) por diferencas finitas periodicas."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    nx = -dx * forca
    ny = dy * forca  # linhas da imagem crescem para baixo; OpenGL = Y para cima
    nz = np.ones_like(h)
    L = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    n = np.stack([nx / L, ny / L, nz / L], -1)
    return ((n * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)


def _salvar(img, path):
    Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


def _pedra(n, rnd):
    h, rach, lasca, terraco, (grande, medio, grao, fino), hb = _altura_pedra(n, rnd)
    hn = (h - h.min()) / (h.max() - h.min())
    # cores quentes cinza-marrom
    escuro = np.array([0.20, 0.175, 0.15])
    medio_c = np.array([0.36, 0.32, 0.27])
    claro = np.array([0.52, 0.47, 0.40])
    ferro = np.array([0.34, 0.25, 0.18])      # veios avermelhados
    tom = _sm(0.8 * grande + 0.2 * medio, 0.3, 0.7)[..., None]
    img = escuro * (1 - tom) + medio_c * tom
    # manchas largas variando o matiz (quente/frio)
    quente = (_ruido(n, rnd, 0.02) - 0.5)[..., None]
    img = img * (1 + quente * np.array([0.30, 0.05, -0.30]))
    # patamares do cinzel: cada faceta com leve variacao de valor
    img = img * (0.80 + 0.45 * terraco[..., None])
    # veios: faixas longas e finas, pouco claras ou ferrosas
    v = _deforma(_ruido(n, rnd, 0.010, banda=0.002), _ruido(n, rnd, 0.02), _ruido(n, rnd, 0.02), n * 0.06)
    veio = np.exp(-((np.abs(v - np.median(v)) / (v.std() + 1e-9)) / 0.10) ** 2) * _sm(_ruido(n, rnd, 0.03), 0.4, 0.6)
    mat = _sm(_ruido(n, rnd, 0.03), 0.45, 0.6)[..., None]
    img = img * (1 - veio[..., None] * 0.55) + (claro * mat + ferro * (1 - mat)) * veio[..., None] * 0.55
    # manchas de sujeira: escurece em poças irregulares + pingos finos
    suj = _sm(_deforma(_ruido(n, rnd, 0.03), _ruido(n, rnd, 0.05), _ruido(n, rnd, 0.05), n * 0.05), 0.55, 0.85)
    img = img * (1 - suj[..., None] * 0.42)
    # cavidade (ambient): fundo das lascas e das fendas mais escuro
    cav = 1 - np.clip(hn, 0, 1)
    img = img * (0.78 + 0.35 * hn[..., None])
    # grao fino mineral
    img = img * (0.90 + 0.20 * grao[..., None]) * (0.96 + 0.08 * fino[..., None])
    # pontos claros de lascas (quinas frescas) e poeira clara nas bordas de lasca
    borda = np.clip(_sm(np.abs(np.roll(lasca, 2, 0) - lasca) + np.abs(np.roll(lasca, 2, 1) - lasca), 0.1, 0.5), 0, 1)
    pts = _sm(fino * 0.6 + _ruido(n, rnd, 0.45) * 0.4, 0.80, 0.86) * _sm(medio, 0.35, 0.6)
    img = img + (claro * 1.05 - img) * np.clip(pts * 0.9 + borda * 0.5, 0, 1)[..., None] * 0.7
    # luz pintada a mao (cima-esquerda) assada do campo de altura: da volume aos cinzeis e lascas
    gx = np.roll(hb, -2, 1) - np.roll(hb, 2, 1); gy = np.roll(hb, -2, 0) - np.roll(hb, 2, 0)
    luz = np.clip(0.5 + (-gx - gy) * 6.0, 0, 1)
    img = img * (0.62 + 0.8 * luz[..., None])
    # rachaduras escuras finas por cima
    rk = np.clip(rach * 1.4, 0, 1)[..., None]
    img = img * (1 - rk * 0.88) + np.array([0.06, 0.05, 0.045]) * rk * 0.88
    # remapeia para 0.18-0.55 (percentis para evitar outliers de rachadura/pontos)
    lum = img.mean(-1)
    lo, hi = np.quantile(lum, 0.01), np.quantile(lum, 0.995)
    img = (img - lo) / (hi - lo)
    img = 0.18 + np.clip(img, 0, 1) * (0.55 - 0.18)
    return np.clip(img, 0.18, 0.55), h


def _musgo(n, rnd):
    grumo = _ruido(n, rnd, 0.05)
    grumo2 = _ruido(n, rnd, 0.13)
    macro = _ruido(n, rnd, 0.03)
    fio = _ruido(n, rnd, 0.5)
    # grumos arredondados: soma de ruidos com ridge suave (almofadas de musgo)
    alm = _sm(grumo, 0.25, 0.75)
    alm = alm * (0.7 + 0.3 * _sm(grumo2, 0.3, 0.7))
    h = 0.55 * alm + 0.25 * grumo2 + 0.12 * fio + 0.10 * macro
    base = np.array([0.055, 0.085, 0.035])
    verde = np.array([0.11, 0.16, 0.05])
    amar = np.array([0.20, 0.20, 0.06])
    t = _sm(alm, 0.2, 0.9)[..., None]
    img = base * (1 - t) + verde * t
    am = _sm(0.6 * macro + 0.4 * grumo2, 0.55, 0.85)[..., None] * _sm(alm, 0.5, 0.95)[..., None]
    img = img * (1 - am * 0.6) + amar * am * 0.6
    img = img * (0.82 + 0.34 * fio[..., None])
    img = img * (0.72 + 0.5 * _sm(h, 0.2, 0.9)[..., None])  # topo das almofadas mais claro, vales escuros
    # clampa 0.05-0.2
    lum = img.max(-1)
    lo, hi = np.quantile(lum, 0.01), np.quantile(lum, 0.995)
    img = (img - np.quantile(img, 0.01)) / (np.quantile(img, 0.995) - np.quantile(img, 0.01))
    img = np.clip(img, 0, 1)
    img = 0.05 + (img ** 0.65) * 0.15
    return np.clip(img, 0.05, 0.2), h


def gerar(pasta, tam=1024, seed=5):
    """Grava pedra_albedo/normal e musgo_albedo/normal em `pasta`. Retorna dict de caminhos."""
    os.makedirs(pasta, exist_ok=True)
    rnd = np.random.default_rng(seed)
    alb, h = _pedra(tam, rnd)
    saida = {}
    saida["pedra_albedo"] = os.path.join(pasta, "pedra_albedo.png"); _salvar(alb, saida["pedra_albedo"])
    saida["pedra_normal"] = os.path.join(pasta, "pedra_normal.png")
    Image.fromarray(_normal(h, 7.0 * tam / 256 * 0.35)).save(saida["pedra_normal"])
    malb, mh = _musgo(tam, rnd)
    saida["musgo_albedo"] = os.path.join(pasta, "musgo_albedo.png"); _salvar(malb, saida["musgo_albedo"])
    saida["musgo_normal"] = os.path.join(pasta, "musgo_normal.png")
    Image.fromarray(_normal(mh, 5.0 * tam / 256 * 0.5)).save(saida["musgo_normal"])
    return saida


if __name__ == "__main__":
    import sys
    out = gerar(os.path.join(os.getcwd(), "tex_prev"), tam=int(sys.argv[1]) if len(sys.argv) > 1 else 1024)
    for k, v in out.items():
        print(k, v)
    # previa 2x2 de tile para conferir emenda
    p = Image.open(out["pedra_albedo"]); w, h = p.size
    t = Image.new("RGB", (w * 2, h * 2))
    for i in range(2):
        for j in range(2):
            t.paste(p, (i * w, j * h))
    t.resize((1024, 1024)).save(os.path.join(os.getcwd(), "tex_prev", "_tile2x2.png"))
