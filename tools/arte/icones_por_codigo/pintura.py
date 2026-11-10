"""Pincel por código dos ícones: máscaras com supersampling, volume com luz, brilho, ruído, deformação e rampas de cor.

Tudo em float32 no espaço de 128 x 128 do ícone (o tamanho da pintura em art-src/ui/icones_pintados), desenhado em 4x e
reduzido no fim. Só numpy e Pillow, sem GPU e sem aleatório fora de `np.random.default_rng(semente)`: a saída é igual
a cada execução.
"""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

N = 128           # lado da pintura final
S = 4             # supersampling
W = N * S         # lado do quadro de trabalho
FUNDO = (0.062, 0.056, 0.072)

_y, _x = np.mgrid[0:W, 0:W].astype(np.float32)
X = (_x + 0.5) / S      # coordenadas no espaço 128
Y = (_y + 0.5) / S


# --- máscaras ---------------------------------------------------------------------------------------------------

def desenhar(fn):
    """fn(d, k) recebe o ImageDraw e a escala k (coordenadas do ícone x k = pixels de trabalho); devolve a máscara 0..1."""
    im = Image.new("L", (W, W), 0)
    fn(ImageDraw.Draw(im), S)
    return np.asarray(im, np.float32) / 255.0


def poligono(pts):
    return desenhar(lambda d, k: d.polygon([(x * k, y * k) for x, y in pts], fill=255))


def circulo(cx, cy, r):
    return desenhar(lambda d, k: d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], fill=255))


def elipse(cx, cy, rx, ry, graus=0.0, passos=72):
    a = np.radians(graus)
    t = np.linspace(0, 2 * np.pi, passos, endpoint=False)
    px = cx + rx * np.cos(t) * np.cos(a) - ry * np.sin(t) * np.sin(a)
    py = cy + rx * np.cos(t) * np.sin(a) + ry * np.sin(t) * np.cos(a)
    return poligono(list(zip(px, py)))


def anel(cx, cy, r, espessura):
    def f(d, k):
        h = espessura / 2
        d.ellipse([(cx - r - h) * k, (cy - r - h) * k, (cx + r + h) * k, (cy + r + h) * k], fill=255)
        d.ellipse([(cx - r + h) * k, (cy - r + h) * k, (cx + r - h) * k, (cy + r - h) * k], fill=0)
    return desenhar(f)


def spline(pts, n=48):
    """Catmull-Rom por pontos (lista de (x, y)); devolve n amostras."""
    p = np.array([pts[0]] + list(pts) + [pts[-1]], float)
    m = len(pts) - 1
    out = []
    for i in range(m):
        p0, p1, p2, p3 = p[i], p[i + 1], p[i + 2], p[i + 3]
        for t in np.linspace(0, 1, max(2, n // m), endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2])
    return [tuple(v) for v in out]


def traco(pts, w):
    """Linha grossa com pontas e juntas redondas (w no espaço 128)."""
    def f(d, k):
        d.line([(x * k, y * k) for x, y in pts], fill=255, width=max(1, int(round(w * k))), joint="curve")
        r = w * k / 2
        for x, y in (pts[0], pts[-1]):
            d.ellipse([x * k - r, y * k - r, x * k + r, y * k + r], fill=255)
    return desenhar(f)


def tubo(pts, w0, w1, n=64, suave=True):
    """Curva (spline) com largura que muda de w0 a w1 (da primeira à última ponta): serpentes, caudas, jatos."""
    c = spline(pts, n) if suave else pts
    def f(d, k):
        m = len(c)
        for i, (x, y) in enumerate(c):
            r = (w0 + (w1 - w0) * i / max(1, m - 1)) * k / 2
            d.ellipse([x * k - r, y * k - r, x * k + r, y * k + r], fill=255)
    return desenhar(f)


def seguir(*mascaras):
    out = mascaras[0]
    for m in mascaras[1:]:
        out = np.maximum(out, m)
    return out


def menos(a, b):
    return np.clip(a - b, 0, 1)


def encosta(a, b):
    return a * b


# --- filtros ----------------------------------------------------------------------------------------------------

@lru_cache(maxsize=64)
def _nucleo(sigma):
    s = sigma * S
    fy = np.fft.fftfreq(W)[:, None]
    fx = np.fft.rfftfreq(W)[None, :]
    return np.exp(-2 * np.pi ** 2 * s ** 2 * (fx ** 2 + fy ** 2)).astype(np.float32)


def gauss(a, sigma):
    """Desfoque gaussiano (sigma no espaço 128), por FFT; vale para (W, W) e (W, W, 3)."""
    if sigma <= 0:
        return a
    h = _nucleo(float(sigma))
    if a.ndim == 2:
        return np.fft.irfft2(np.fft.rfft2(a) * h, s=a.shape).astype(np.float32)
    return np.stack([gauss(a[..., i], sigma) for i in range(a.shape[2])], axis=-1)


def deslocar(a, dx, dy):
    """Desloca a imagem por (dx, dy) no espaço 128 (amostra bilinear; borda repete)."""
    return deformar(a, np.full((W, W), dx, np.float32), np.full((W, W), dy, np.float32))


def deformar(a, dx, dy):
    """Amostra `a` em (x + dx, y + dy), com dx e dy em unidades do espaço 128 (campos W x W): chamas, fumaça, ondas."""
    xs = np.clip(_x + dx * S, 0, W - 1.001)
    ys = np.clip(_y + dy * S, 0, W - 1.001)
    x0 = xs.astype(np.int32)
    y0 = ys.astype(np.int32)
    fx = xs - x0
    fy = ys - y0
    if a.ndim == 3:
        fx = fx[..., None]
        fy = fy[..., None]
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy) + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)


def ruido(semente, periodo=24.0, oitavas=4, persistencia=0.5):
    """Ruído de valor (fBm) em 0..1. `periodo` é o da primeira oitava no espaço 128; com (px, py) estica o ruído (chamas sobem
    com py maior que px)."""
    rng = np.random.default_rng(semente)
    px, py = (periodo, periodo) if np.isscalar(periodo) else periodo
    out = np.zeros((W, W), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(oitavas):
        nx = max(2, int(round(N / (px / 2 ** o))) + 1)
        ny = max(2, int(round(N / (py / 2 ** o))) + 1)
        g = rng.random((ny, nx)).astype(np.float32)
        out += amp * np.asarray(Image.fromarray(g, "F").resize((W, W), Image.BICUBIC), np.float32)
        tot += amp
        amp *= persistencia
    out /= tot
    lo, hi = np.percentile(out, 1), np.percentile(out, 99)
    return np.clip((out - lo) / max(hi - lo, 1e-6), 0, 1)


def rampa(v, paradas):
    """Leva v (0..1) a uma rampa de cores (lista de (r, g, b) em 0..255)."""
    p = np.array(paradas, np.float32) / 255.0
    k = len(p) - 1
    x = np.clip(v, 0, 1) * k
    i = np.minimum(x.astype(np.int32), k - 1)
    f = (x - i)[..., None]
    return p[i] * (1 - f) + p[i + 1] * f


def degrau(v, a, b):
    t = np.clip((v - a) / max(b - a, 1e-6), 0, 1)
    return t * t * (3 - 2 * t)


# --- volume e luz -----------------------------------------------------------------------------------------------

LUZ = np.array([-0.52, -0.62, 0.60], np.float32)
LUZ /= np.linalg.norm(LUZ)


def luz_da_forma(mascara, suavidade=2.6, relevo=1.0, luz=None):
    """Valor de luz 0..1 de uma forma tratada como relevo (altura = máscara suavizada): bordas viradas para a luz acendem."""
    l = LUZ if luz is None else np.asarray(luz, np.float32) / np.linalg.norm(luz)
    h = gauss(mascara, suavidade) * suavidade * 2.2 * relevo
    gy, gx = np.gradient(h, 1.0 / S)
    nx, ny = -gx, -gy
    n = np.sqrt(nx * nx + ny * ny + 1.0)
    d = (nx * l[0] + ny * l[1] + l[2]) / n
    return np.clip((d - 0.15) / 0.85, 0, 1)


def borda_luz(mascara, raio=1.2, luz=(-1.0, -1.0)):
    """Fio de luz nas bordas viradas para a luz (e de sombra nas opostas): devolve valor de -1 a 1."""
    d = gauss(mascara, raio) - gauss(mascara, raio * 2.2)
    gy, gx = np.gradient(gauss(mascara, raio), 1.0 / S)
    n = np.sqrt(gx * gx + gy * gy) + 1e-6
    l = np.array(luz, np.float32) / np.linalg.norm(luz)
    return -(gx * l[0] + gy * l[1]) / n * np.clip(np.abs(d) * 9.0, 0, 1) * (mascara > 0.02)


class Tela:
    """Quadro de trabalho 512 x 512: fundo escuro, camadas pintadas por máscara e brilhos somados."""

    def __init__(self, fundo=FUNDO):
        self.rgb = np.empty((W, W, 3), np.float32)
        self.rgb[:] = np.array(fundo, np.float32)

    def halo(self, cx, cy, raio, cor, forca=0.6):
        d2 = ((X - cx) ** 2 + (Y - cy) ** 2) / (raio * raio)
        self.rgb += np.exp(-d2)[..., None] * np.array(cor, np.float32) * forca

    def pintar(self, mascara, cor, alfa=1.0):
        m = (mascara * alfa)[..., None]
        cor = np.asarray(cor, np.float32)
        self.rgb = self.rgb * (1 - m) + cor * m

    def somar(self, mascara, cor, forca=1.0):
        self.rgb += mascara[..., None] * np.asarray(cor, np.float32) * forca

    def brilho(self, mascara, cor, raio, forca=1.0):
        self.somar(gauss(mascara, raio), cor, forca)

    def sombra(self, mascara, raio, forca=0.6):
        self.rgb *= (1 - gauss(mascara, raio) * forca)[..., None]

    def solido(self, mascara, rampa_cores, luz, alfa=1.0, tom=None):
        """Pinta a forma com uma rampa de cores indexada por `luz` (0..1)."""
        v = luz if tom is None else np.clip(luz + tom, 0, 1)
        self.pintar(mascara, rampa(v, rampa_cores), alfa)

    def volume(self, mascara, rampa_cores, suavidade=2.6, relevo=1.0, ruido_arr=None, ruido_k=0.18, brilho_borda=0.22, alfa=1.0):
        """Forma com relevo: luz de cima à esquerda, ruído de pincel opcional e fio de luz na borda."""
        v = luz_da_forma(mascara, suavidade, relevo)
        if ruido_arr is not None:
            v = np.clip(v + (ruido_arr - 0.5) * ruido_k * 2, 0, 1)
        if brilho_borda:
            v = np.clip(v + borda_luz(mascara) * brilho_borda, 0, 1)
        self.pintar(mascara, rampa(v, rampa_cores), alfa)

    def reduzir(self):
        a = np.clip(self.rgb, 0, 1)
        return a.reshape(N, S, N, S, 3).mean(axis=(1, 3))


def para_imagem(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")
