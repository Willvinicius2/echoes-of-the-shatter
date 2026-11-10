"""Os 35 ícones: cada função devolve o miolo 128 x 128 x 3 (0..1) de um ícone; o `gerar.py` põe a moldura e pixeliza."""
import numpy as np

import pintura as P
from pintura import X, Y, W, S, N

# --- paletas (de escuro a claro, RGB 0..255) -------------------------------------------------------------------
FOGO = [(22, 4, 4), (104, 16, 8), (210, 60, 12), (255, 140, 26), (255, 212, 92), (255, 246, 196)]
BRASA = [(14, 6, 6), (52, 14, 10), (104, 30, 14), (176, 58, 18), (226, 104, 30)]
GELO = [(6, 16, 36), (22, 58, 116), (60, 134, 204), (136, 204, 244), (212, 242, 255), (255, 255, 255)]
VENENO = [(6, 24, 6), (24, 80, 14), (66, 156, 26), (138, 220, 50), (210, 252, 118), (244, 255, 200)]
RAIO = [(10, 12, 40), (38, 54, 168), (96, 138, 250), (186, 218, 255), (255, 255, 255)]
FERRO = [(8, 8, 12), (36, 36, 46), (80, 80, 94), (136, 134, 146), (204, 198, 194), (248, 242, 234)]
MADEIRA = [(24, 12, 8), (68, 38, 20), (116, 72, 36), (168, 118, 62), (214, 166, 98)]
OURO = [(40, 26, 8), (108, 74, 22), (184, 136, 46), (236, 198, 98), (255, 238, 170), (255, 252, 225)]
PEDRA = [(10, 10, 14), (38, 36, 44), (74, 70, 78), (118, 112, 116), (168, 160, 156)]
OSSO = [(40, 30, 22), (120, 100, 78), (196, 176, 140), (240, 228, 196)]
VIDRO_VERDE = [(6, 30, 20), (20, 90, 60), (50, 170, 110), (120, 232, 170), (220, 255, 230)]
ROXO = [(12, 6, 28), (52, 22, 108), (112, 54, 196), (170, 118, 244), (232, 208, 255)]
ESCAMA = [(8, 4, 6), (36, 14, 14), (82, 32, 22), (144, 66, 34), (208, 114, 54)]


def tela(cor, raio=48, forca=0.5, cx=64, cy=64):
    t = P.Tela()
    t.halo(cx, cy, raio, cor, forca)
    return t


# --- peças comuns ----------------------------------------------------------------------------------------------

def chama(forma, semente, subida=9.0, vento=5.0, passos=3, periodo=(14, 30), fluxo=(0.0, -1.0)):
    """Fogo a partir de uma forma: a máscara é puxada na direção `fluxo` (padrão: para cima) por ruído esticado e vira língua de
    chama. Devolve (intensidade 0..1, alfa 0..1)."""
    n1 = P.ruido(semente, periodo, 3)
    n2 = P.ruido(semente + 7, periodo, 3)
    f = forma
    fx, fy = fluxo
    for k in range(passos):
        dx = (n1 - 0.5) * 2 * vento - fx * subida / passos
        dy = (n2 - 0.5) * vento - fy * subida / passos
        f = P.deformar(P.gauss(f, 1.4), dx, dy)
    f = np.clip(f * 1.15, 0, 1)
    return f, P.degrau(f, 0.10, 0.45)


def pintar_fogo(t, forma, semente, paleta=FOGO, forca=1.0, ganho=1.0, **kw):
    """`ganho` < 1 deixa o fogo mais vermelho e laranja (só o miolo chega ao amarelo)."""
    f, a = chama(forma, semente, **kw)
    v = P.degrau(f, 0.05, 0.95) * ganho
    t.pintar(a, P.rampa(v, paleta), forca)
    return f


def esfera(t, cx, cy, r, rampa, alfa=1.0, brilho=0.9):
    d2 = (X - cx) ** 2 + (Y - cy) ** 2
    m = np.clip((r * r - d2) / (r * 2.2) + 0.5, 0, 1)
    z = np.sqrt(np.clip(1 - d2 / (r * r), 0, 1))
    nx, ny = (X - cx) / r, (Y - cy) / r
    l = P.LUZ
    d = np.clip(nx * l[0] + ny * l[1] + z * l[2], 0, 1)
    v = np.clip(d * 0.95 + 0.05 * z, 0, 1)
    t.pintar(m, P.rampa(v, rampa), alfa)
    # reflexo
    hx, hy = cx + l[0] * r * 0.52, cy + l[1] * r * 0.52
    h = np.exp(-(((X - hx) ** 2 + (Y - hy) ** 2) / (r * 0.22) ** 2))
    t.somar(h * m, (1, 1, 1), brilho * 0.55)
    return m


def relampago(p0, p1, semente, desvio=9.0, niveis=4, ramos=2, largura=2.4):
    rng = np.random.default_rng(semente)
    pts = [np.array(p0, float), np.array(p1, float)]
    for n in range(niveis):
        novos = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            m = (a + b) / 2
            d = b - a
            nrm = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-6)
            m = m + nrm * rng.uniform(-1, 1) * desvio / (1.6 ** n)
            novos += [m, b]
        pts = novos
    pts = [tuple(p) for p in pts]
    corpo = P.traco(pts, largura)
    ram = np.zeros_like(corpo)
    for _ in range(ramos):
        i = rng.integers(len(pts) // 4, 3 * len(pts) // 4)
        a = np.array(pts[i])
        ang = np.arctan2(p1[1] - p0[1], p1[0] - p0[0]) + rng.choice([-1, 1]) * rng.uniform(0.5, 0.9)
        L = rng.uniform(14, 24)
        e = a + L * np.array([np.cos(ang), np.sin(ang)])
        sub = relampago_simples(a, e, int(rng.integers(1 << 30)))
        ram = np.maximum(ram, P.traco(sub, largura * 0.6))
    return np.maximum(corpo, ram)


def relampago_simples(p0, p1, semente, desvio=5.0, niveis=3):
    rng = np.random.default_rng(semente)
    pts = [np.array(p0, float), np.array(p1, float)]
    for n in range(niveis):
        novos = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            m = (a + b) / 2
            d = b - a
            nrm = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-6)
            m = m + nrm * rng.uniform(-1, 1) * desvio / (1.5 ** n)
            novos += [m, b]
        pts = novos
    return [tuple(p) for p in pts]


def pintar_raio(t, mascara, cor_brilho, nucleo=(1, 1, 1), raio_brilho=3.5, forca=0.9):
    t.brilho(mascara, cor_brilho, raio_brilho * 2.2, forca * 0.7)
    t.brilho(mascara, cor_brilho, raio_brilho, forca)
    t.pintar(P.gauss(mascara, 0.5), np.array(cor_brilho) * 0.55 + 0.45 * np.array(nucleo), 1.0)
    t.pintar(np.clip(P.gauss(mascara, 0.4) * 1.6 - 0.35, 0, 1), nucleo, 0.95)


def faiscas(t, semente, centro, raio, n, cor, tam=(0.8, 1.8), forca=0.9):
    rng = np.random.default_rng(semente)
    for _ in range(n):
        a = rng.uniform(0, 2 * np.pi)
        r = raio * np.sqrt(rng.uniform(0.15, 1.0))
        x, y = centro[0] + np.cos(a) * r, centro[1] + np.sin(a) * r
        s = rng.uniform(*tam)
        m = P.circulo(x, y, s)
        t.brilho(m, cor, 2.2, 0.8 * forca)
        t.pintar(m, (1, 1, 0.9), forca)


def espinho(base, ponta, largura):
    """Espinho triangular (cristal, lança, chifre): devolve (máscara, lado -1..1 na largura, ao longo 0..1 da base à ponta)."""
    b = np.array(base, float)
    p = np.array(ponta, float)
    a = p - b
    L = np.linalg.norm(a)
    a /= L
    n = np.array([-a[1], a[0]])
    m = P.poligono([tuple(b + n * largura / 2), tuple(p), tuple(b - n * largura / 2)])
    rel_x, rel_y = X - b[0], Y - b[1]
    ao = (rel_x * a[0] + rel_y * a[1]) / L
    la = (rel_x * n[0] + rel_y * n[1]) / np.maximum(largura / 2 * (1 - np.clip(ao, 0, 0.98)), 0.5)
    return m, np.clip(la, -1, 1), np.clip(ao, 0, 1)


def cristal(t, base, ponta, largura, rampa=None, alfa=1.0, brilho_cor=None):
    """Espinho de gelo facetado: face da luz clara, face da sombra escura, fio branco no meio e na borda."""
    rampa = rampa or GELO
    m, la, ao = espinho(base, ponta, largura)
    v = np.where(la < 0, 0.62 + 0.30 * (-la) * 0.5, 0.40 - 0.18 * la) + 0.20 * (ao ** 0.8)
    v = np.clip(v + (1 - np.abs(la)) * 0.10, 0, 1)
    crista = P.degrau(1 - np.abs(la), 0.82, 1.0) * 0.30
    v = np.clip(v + crista, 0, 1)
    if brilho_cor is not None:
        t.brilho(m, brilho_cor, 3.0, 0.55)
    t.pintar(m, P.rampa(v, rampa), alfa)
    t.somar(P.borda_luz(m).clip(0, 1) * m, (0.9, 0.97, 1.0), 0.55)
    return m


def floco(cx, cy, r, grosso=1.9, ramos=2):
    """Máscara de um floco de neve de 6 braços com `ramos` pares de galhos."""
    ms = []
    for k in range(6):
        a = np.radians(k * 60 - 90)
        u = np.array([np.cos(a), np.sin(a)])
        v = np.array([-u[1], u[0]])
        c = np.array([cx, cy])
        ms.append(P.traco([tuple(c), tuple(c + u * r)], grosso))
        for j in range(ramos):
            f = 0.45 + 0.28 * j
            o = c + u * r * f
            L = r * (0.34 - 0.08 * j)
            for sg in (-1, 1):
                ms.append(P.traco([tuple(o), tuple(o + u * L * 0.7 + v * sg * L)], grosso * 0.8))
        ms.append(P.circulo(*(c + u * r), grosso * 0.9))
    return P.seguir(*ms)


def torcer(a, cx, cy, forca=1.0, raio=44.0):
    """Redemoinho: gira a amostragem em volta de (cx, cy) mais perto do centro."""
    dx, dy = X - cx, Y - cy
    r = np.sqrt(dx * dx + dy * dy)
    ang = forca * np.exp(-(r / raio) ** 2)
    c, s = np.cos(ang), np.sin(ang)
    rx = dx * c - dy * s
    ry = dx * s + dy * c
    return P.deformar(a, rx - dx, ry - dy)


def livro(t, cx=64, cy=84, cor_luz=(1, 0.6, 0.2), capa=None):
    """Livro aberto visto de cima, com as páginas acesas pela luz do símbolo; devolve a máscara das páginas."""
    capa = capa or [(14, 8, 6), (50, 28, 18), (92, 56, 30), (140, 96, 52)]
    capa_m = P.seguir(P.poligono([(cx - 46, cy - 6), (cx, cy - 16), (cx + 46, cy - 6), (cx + 46, cy + 26), (cx, cy + 36), (cx - 46, cy + 26)]))
    t.sombra(capa_m, 3, 0.55)
    t.volume(capa_m, capa, 1.6, 1.0, brilho_borda=0.25)
    pg_e = P.poligono([(cx - 42, cy - 5), (cx - 2, cy - 14), (cx - 2, cy + 28), (cx - 42, cy + 20)])
    pg_d = P.poligono([(cx + 2, cy - 14), (cx + 42, cy - 5), (cx + 42, cy + 20), (cx + 2, cy + 28)])
    pag = np.maximum(pg_e, pg_d)
    papel = [(60, 44, 30), (150, 126, 94), (214, 192, 152), (246, 232, 198)]
    brilho_pg = np.clip(1.0 - np.hypot(X - cx, (Y - cy + 28) * 0.9) / 62.0, 0, 1)
    t.pintar(pg_e, P.rampa(0.35 + 0.3 * (1 - (X - (cx - 42)) / 40.0).clip(0, 1) * 0.3 + brilho_pg * 0.45, papel))
    t.pintar(pg_d, P.rampa(0.30 + 0.25 * ((X - cx) / 42.0).clip(0, 1) * -0.2 + brilho_pg * 0.45, papel))
    # linhas de texto
    for k in range(4):
        y0 = cy - 1 + k * 5.2
        t.pintar(P.traco([(cx - 38, y0 + 0.5 - k * 0.6 + 4), (cx - 8, y0 - 3.5 + 4 - 0.4)], 1.2), (0.36, 0.26, 0.18), 0.55)
        t.pintar(P.traco([(cx + 8, y0 - 3.5 + 4 - 0.4), (cx + 38, y0 + 0.5 - k * 0.6 + 4)], 1.2), (0.36, 0.26, 0.18), 0.55)
    lombada = P.traco([(cx, cy - 15), (cx, cy + 29)], 3.0)
    t.volume(lombada, capa, 1.0, 1.0)
    t.somar(P.gauss(pag, 6.0) * np.clip(1 - np.hypot(X - cx, Y - (cy - 14)) / 40, 0, 1), cor_luz, 0.6)
    return pag


def flecha(t, p0, p1, haste=3.0, ponta=(14, 7.0), pena=(8.5, 6.0), r_haste=None, r_ponta=None, r_pena=None, brilho_cor=None, n_penas=3):
    """Flecha de p0 (cauda) a p1 (ponta): penas, haste e ponta com relevo. Devolve a máscara do conjunto."""
    r_haste = r_haste or MADEIRA
    r_ponta = r_ponta or FERRO
    r_pena = r_pena or OSSO
    p0 = np.array(p0, float)
    p1 = np.array(p1, float)
    L = np.linalg.norm(p1 - p0)
    u = (p1 - p0) / L
    v = np.array([-u[1], u[0]])
    hl, hw = ponta
    corpo = P.traco([tuple(p0 + u * 2), tuple(p1 - u * hl * 0.6)], haste)
    cab = P.poligono([tuple(p1), tuple(p1 - u * hl + v * hw), tuple(p1 - u * hl * 0.74), tuple(p1 - u * hl - v * hw)])
    penas = np.zeros((W, W), np.float32)
    for k in range(n_penas):
        b = p0 + u * (1.5 + k * 4.6)
        for sg in (-1, 1):
            penas = np.maximum(penas, P.poligono([tuple(b), tuple(b + u * 7.0), tuple(b + u * 10.5 + v * sg * pena[1]), tuple(b + u * 3.5 + v * sg * pena[1])]))
    tudo = P.seguir(corpo, cab, penas)
    if brilho_cor is not None:
        t.brilho(tudo, brilho_cor, 6.0, 0.65)
    t.sombra(P.deslocar(tudo, 1.5, 2.5), 2.5, 0.45)
    t.volume(penas, r_pena, 1.1, 1.0, brilho_borda=0.25)
    t.volume(corpo, r_haste, 1.1, 1.0, brilho_borda=0.3)
    t.volume(cab, r_ponta, 1.5, 1.0, brilho_borda=0.45)
    return tudo


def gota(cx, cy, r, h=None):
    """Gota (ponta para cima)."""
    h = h or r * 1.9
    return P.seguir(P.circulo(cx, cy, r), P.poligono([(cx, cy - h), (cx + r * 0.92, cy - r * 0.3), (cx - r * 0.92, cy - r * 0.3)]))


def disco_mascara(cx, cy, r):
    return P.circulo(cx, cy, r)


def coord_curva(pts, n=96):
    """Para cada pixel: posição ao longo da curva (0..1), lado (-1..1 do eixo) e distância ao eixo, no espaço 128."""
    c = np.array(P.spline(pts, n), float)
    seg = np.diff(c, axis=0)
    comp = np.linalg.norm(seg, axis=1)
    acum = np.concatenate([[0], np.cumsum(comp)])
    total = acum[-1]
    melhor = np.full((W, W), 1e9, np.float32)
    idx = np.zeros((W, W), np.int32)
    for i, (cx, cy) in enumerate(c):
        d = (X - cx) ** 2 + (Y - cy) ** 2
        m = d < melhor
        melhor = np.where(m, d, melhor)
        idx = np.where(m, i, idx)
    dist = np.sqrt(melhor)
    ia = np.minimum(idx, len(seg) - 1)
    tang = seg[ia] / comp[ia][..., None]
    rel_x = X - c[idx, 0]
    rel_y = Y - c[idx, 1]
    lado = rel_x * tang[..., 1] * -1 + rel_y * tang[..., 0]
    return (acum[idx] / total).astype(np.float32), np.sign(lado).astype(np.float32), dist.astype(np.float32)


def nuvem_tempestade(t, cx, cy, largura, semente, cor_luz=(0.5, 0.65, 1.0)):
    """Cúmulo escuro com a borda de cima clara e a barriga acesa pelos raios."""
    rng = np.random.default_rng(semente)
    partes = [P.elipse(cx, cy + 4, largura * 0.5, 12)]
    for k in range(7):
        x = cx + (k - 3) * largura / 7 + rng.uniform(-3, 3)
        r = rng.uniform(11, 17) * (1.0 - abs(k - 3) * 0.1)
        partes.append(P.circulo(x, cy - rng.uniform(0, 7), r))
    cum = np.clip(P.seguir(*partes), 0, 1)
    nuv = P.ruido(semente, (18, 12), 4)
    luz = P.luz_da_forma(np.clip(P.gauss(cum, 2), 0, 1), 4.0)
    t.sombra(cum, 5, 0.55)
    t.pintar(cum, P.rampa(np.clip(0.10 + luz * 0.5 + (nuv - 0.5) * 0.35, 0, 1), RAIO))
    t.somar(P.borda_luz(cum).clip(0, 1) * cum, (0.75, 0.85, 1.0), 0.65)
    t.brilho(P.elipse(cx, cy + 10, largura * 0.36, 6), cor_luz, 7, 0.6)
    return cum


def girar_pts(pts, cx, cy, graus, k=1.0):
    """Gira e escala uma lista de pontos locais (x para a frente, y para baixo) em volta da origem (cx, cy)."""
    a = np.radians(graus)
    c, s = np.cos(a), np.sin(a)
    return [(cx + (x * c - y * s) * k, cy + (x * s + y * c) * k) for x, y in pts]


def tubo_perfil(pts, perfil, n=160):
    """Curva (spline) com largura dada por nós (posição 0..1, largura): serpentes, caudas."""
    c = P.spline(pts, n)
    pos = np.linspace(0, 1, len(c))
    nos = np.array(perfil, float)
    larg = np.interp(pos, nos[:, 0], nos[:, 1])
    def f(d, k):
        for (x, y), w in zip(c, larg):
            r = w * k / 2
            d.ellipse([x * k - r, y * k - r, x * k + r, y * k + r], fill=255)
    return P.desenhar(f)


def polar(cx, cy):
    dx, dy = X - cx, Y - cy
    return np.hypot(dx, dy), np.degrees(np.arctan2(dy, dx))


def petala(cx, cy, ang, r0, r1, larg, curva, n=14):
    """Língua de chama que sai do anel: do raio r0 ao r1 em volta de (cx, cy), larga na base, ponta curvada para o lado."""
    esq, dir_ = [], []
    for i in range(n + 1):
        s = i / n
        r = r0 + (r1 - r0) * s
        w = larg * (1 - s) ** 0.85 * (1 + 0.18 * np.sin(s * 5.0))
        a = np.radians(ang + curva * s * s)
        u = np.array([np.cos(a), np.sin(a)])
        v = np.array([-u[1], u[0]])
        c = np.array([cx, cy]) + u * r
        esq.append(tuple(c + v * w / 2))
        dir_.append(tuple(c - v * w / 2))
    return P.poligono(esq + dir_[::-1])


def lingua(base, ang, comp, larg, curva=0.0, n=16):
    """Língua de chama reta (ou levemente curvada para o lado) que parte de `base` na direção `ang`; devolve (máscara, posição 0..1
    ao longo da língua em cada pixel)."""
    a = np.radians(ang)
    u = np.array([np.cos(a), np.sin(a)])
    v = np.array([-u[1], u[0]])
    b = np.array(base, float)
    esq, dir_ = [], []
    for i in range(n + 1):
        q = i / n
        w = larg * (1 - q) ** 0.8 * (1 + 0.15 * np.sin(q * 5.0))
        c = b + u * comp * q + v * curva * q * q
        esq.append(tuple(c + v * w / 2))
        dir_.append(tuple(c - v * w / 2))
    m = P.poligono(esq + dir_[::-1])
    pos = np.clip(((X - b[0]) * u[0] + (Y - b[1]) * u[1]) / comp, 0, 1)
    return m, pos


def girar_em(pts, ox, oy, graus):
    """Gira pontos em volta de (ox, oy)."""
    a = np.radians(graus)
    c, s = np.cos(a), np.sin(a)
    return [(ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c) for x, y in pts]


def trompa(pts, w0, w1, expoente=2.2, n=110):
    """Tubo que alarga devagar e abre no fim (trompa, sino): largura w0 na boquilha e w1 na boca, com s ** expoente."""
    c = P.spline(pts, n)
    def f(d, k):
        m = len(c)
        for i, (x, y) in enumerate(c):
            r = (w0 + (w1 - w0) * (i / max(1, m - 1)) ** expoente) * k / 2
            d.ellipse([x * k - r, y * k - r, x * k + r, y * k + r], fill=255)
    return P.desenhar(f)


CHAMA_LARANJA = [(150, 30, 6), (240, 96, 14), (255, 150, 30), (255, 206, 90)]
CHAMA_GELO = [(14, 80, 150), (40, 160, 240), (100, 210, 255), (190, 240, 255)]
CHAMA_VENENO = [(14, 100, 14), (50, 180, 30), (110, 230, 50), (190, 255, 120)]
CHAMA_RAIO = [(60, 24, 160), (120, 70, 240), (170, 120, 255), (216, 190, 255)]


def chama_pequena(t, base, ang, comp, larg, paleta, brilho_cor):
    """Chama de silhueta limpa (gota alongada com a ponta torta) de uma cor só, com núcleo um tom mais claro (nunca branco)."""
    m, pos = lingua(base, ang, comp, larg, curva=3.0)
    t.brilho(m, brilho_cor, 3.0, 0.3)
    t.pintar(m, P.rampa(np.clip(0.78 - pos * 0.7, 0, 1), paleta), 1.0)
    n, pn = lingua(base, ang, comp * 0.6, larg * 0.42, curva=1.5)
    t.pintar(n, P.rampa(np.clip(1.0 - pn * 0.5, 0, 1), paleta), 0.95)


# --- protótipos ------------------------------------------------------------------------------------------------


def toxic_mines():
    t = tela((0.3, 1.0, 0.15), 50, 0.42, 64, 70)
    # nuvem de veneno que sobe
    nuv = P.ruido(8, (18, 26), 4)
    base = np.clip(P.circulo(64, 56, 26) * 0.9 + P.circulo(46, 64, 14) * 0.6 + P.circulo(84, 62, 15) * 0.6, 0, 1)
    f = P.deformar(P.gauss(base, 4), (nuv - 0.5) * 18, (P.ruido(9, (18, 26), 4) - 0.5) * 18 + 8)
    t.somar(np.clip(f * 1.4, 0, 1), (0.28, 0.9, 0.12), 0.65)
    t.pintar(np.clip(f * 1.5 - 0.35, 0, 1), P.rampa(0.55 + 0.45 * nuv, VENENO), 0.45)
    # minas
    for cx, cy, r, sem in [(64, 78, 22, 1), (34, 92, 13, 2), (96, 94, 13, 3)]:
        pontas = np.zeros((W, W), np.float32)
        for k in range(8):
            a = k * np.pi / 4 + 0.2
            c, s = np.cos(a), np.sin(a)
            pontas = np.maximum(pontas, P.poligono([(cx + c * (r - 2) - s * 4, cy + s * (r - 2) + c * 4), (cx + c * (r + 8), cy + s * (r + 8)),
                                                    (cx + c * (r - 2) + s * 4, cy + s * (r - 2) - c * 4)]))
        t.sombra(P.circulo(cx + 3, cy + 5, r + 6), 3, 0.5)
        t.volume(pontas, FERRO, 1.2, 1.0, brilho_borda=0.3)
        esfera(t, cx, cy, r, FERRO)
        anel_m = P.anel(cx, cy, r * 0.55, max(2.0, r * 0.14))
        nucleo = P.circulo(cx, cy, r * 0.38)
        t.brilho(nucleo, (0.35, 1.0, 0.2), r * 0.35, 0.9)
        t.pintar(anel_m, P.rampa(0.8, VENENO), 0.9)
        t.pintar(nucleo, P.rampa(0.55 + 0.45 * P.degrau(np.hypot(X - cx, Y - cy), r * 0.38, 0.0), VENENO), 1.0)
    faiscas(t, 7, (64, 50), 36, 12, (0.4, 1.0, 0.2))
    return t.reduzir()


def lightning_rod():
    t = tela((0.3, 0.5, 1.0), 52, 0.5, 64, 60)
    nuvem_tempestade(t, 64, 26, 100, 4)
    topo = (64, 42)
    rel = relampago((72, 28), topo, 17, desvio=6, niveis=3, ramos=2)
    pintar_raio(t, rel, (0.5, 0.65, 1.0))
    for k, (a, b) in enumerate([((64, 54), (44, 80)), ((64, 64), (86, 88)), ((64, 78), (46, 102))]):
        arc = relampago_simples(a, b, 40 + k, desvio=5)
        pintar_raio(t, P.traco(arc, 1.9), (0.4, 0.6, 1.0), raio_brilho=2.5, forca=0.75)
    haste = P.poligono([(61.5, 44), (66.5, 44), (68.5, 110), (59.5, 110)])
    t.sombra(haste, 3, 0.5)
    t.volume(haste, FERRO, 1.6, 1.0, brilho_borda=0.3)
    ponta = P.poligono([(64, 34), (67, 46), (61, 46)])
    t.volume(ponta, FERRO, 1.0, 1.0)
    for y in (58, 78, 98):
        t.volume(P.poligono([(57, y), (71, y), (72, y + 5), (56, y + 5)]), OURO, 1.2, 1.0)
    base = P.seguir(P.elipse(64, 112, 26, 8), P.elipse(50, 108, 10, 6), P.elipse(80, 108, 11, 6))
    t.volume(base, PEDRA, 2.0, 1.0, ruido_arr=P.ruido(6, 8, 3), ruido_k=0.25)
    faiscas(t, 5, (64, 62), 36, 10, (0.5, 0.7, 1.0))
    t.brilho(P.circulo(64, 38, 2.6), (0.5, 0.7, 1.0), 6, 1.0)
    return t.reduzir()


def toxic_tornado():
    t = tela((0.3, 1.0, 0.15), 52, 0.40, 64, 62)
    ys = np.arange(14, 111)
    eixo = lambda y: 64 + 7 * np.sin((y - 14) / 15.0)
    raio = lambda y: 3 + 37 * ((110 - y) / 96.0) ** 1.25
    esq = [(eixo(y) - raio(y), y) for y in ys]
    dire = [(eixo(y) + raio(y), y) for y in ys[::-1]]
    funil = P.poligono(esq + dire)
    funil = np.clip(P.deformar(funil, (P.ruido(3, (14, 20), 4) - 0.5) * 9, 0), 0, 1)
    xc = 64 + 7 * np.sin((Y - 14) / 15.0)
    r = np.maximum(3 + 37 * (np.clip(110 - Y, 0, 96) / 96.0) ** 1.25, 1.0)
    u = np.clip((X - xc) / r, -1, 1)
    n = P.ruido(5, (12, 12), 4)
    faixas = 0.5 + 0.5 * np.sin(Y * 0.34 + u * 1.9 + n * 1.5)
    v = np.clip(0.16 + 0.40 * faixas + 0.22 * (1 - u * u) + 0.16 * (-u) + (n - 0.5) * 0.25, 0, 1)
    t.sombra(funil, 4, 0.4)
    t.brilho(funil, (0.3, 0.95, 0.15), 7, 0.5)
    t.pintar(funil, P.rampa(v, VENENO))
    t.somar(P.borda_luz(funil).clip(0, 1) * funil, (0.8, 1.0, 0.5), 0.55)
    # topo: nuvem de miasma por cima, mais larga e clara
    topo = P.seguir(P.elipse(62, 18, 44, 9), P.circulo(34, 22, 9), P.circulo(92, 22, 10), P.circulo(64, 12, 12))
    topo = np.clip(P.deformar(topo, (P.ruido(8, 14, 3) - 0.5) * 6, (P.ruido(9, 14, 3) - 0.5) * 3), 0, 1)
    t.pintar(topo, P.rampa(np.clip(0.30 + 0.5 * P.luz_da_forma(topo, 3.0) + (n - 0.5) * 0.3, 0, 1), VENENO))
    t.somar(P.borda_luz(topo).clip(0, 1) * topo, (0.85, 1.0, 0.55), 0.6)
    # lascas e bolhas girando
    rng = np.random.default_rng(12)
    for k in range(11):
        y = rng.uniform(26, 98)
        a = rng.uniform(0, 2 * np.pi)
        x = 64 + 7 * np.sin((y - 14) / 15.0) + np.cos(a) * (raio(y) + rng.uniform(2, 8))
        m = P.circulo(x, y, rng.uniform(1.3, 2.6))
        t.brilho(m, (0.5, 1.0, 0.25), 2.5, 0.7)
        t.pintar(m, (0.85, 1.0, 0.6))
    poca = P.elipse(66, 114, 22, 5)
    t.brilho(poca, (0.3, 1.0, 0.15), 4, 0.8)
    t.pintar(poca, P.rampa(0.6 + 0.3 * P.ruido(2, 8, 2), VENENO), 0.9)
    return t.reduzir()


def ice_comet():
    t = tela((0.4, 0.75, 1.0), 52, 0.45, 60, 66)
    # cauda: faixas de gelo e neve que fluem para cima e à direita
    cauda = P.tubo([(40, 90), (62, 62), (84, 38), (112, 14)], 34, 3)
    f, a = chama(cauda, 5, subida=14, vento=5, passos=3, periodo=(30, 14), fluxo=(1.0, -0.8))
    t.pintar(a, P.rampa(P.degrau(f, 0.05, 0.9) * 0.8, GELO), 0.9)
    t.brilho(cauda, (0.45, 0.8, 1.0), 8, 0.55)
    for k in range(7):
        off = (k - 3) * 4.2
        linha = P.traco([(44 + off * 0.5, 88 - off * 0.8), (96 + off * 0.3, 26 - off * 0.5)], 1.3)
        t.pintar(linha * np.clip(P.ruido(30 + k, 18, 2) * 1.6, 0, 1), (0.86, 0.97, 1.0), 0.7)
    # cabeça: rocha de gelo facetada
    cab = P.poligono([(26, 78), (36, 66), (54, 62), (68, 74), (66, 92), (50, 104), (32, 100), (22, 90)])
    t.sombra(cab, 3, 0.4)
    v = P.luz_da_forma(cab, 3.0)
    facetas = P.ruido(8, 20, 2)
    t.pintar(cab, P.rampa(np.clip(v * 0.8 + (np.floor(facetas * 4) / 4) * 0.35, 0, 1), GELO))
    for a2, b2 in [((36, 66), (50, 104)), ((54, 62), (32, 100)), ((22, 90), (68, 74))]:
        t.pintar(P.traco([a2, b2], 0.9) * cab, (0.9, 0.98, 1.0), 0.45)
    t.somar(P.borda_luz(cab).clip(0, 1) * cab, (0.9, 0.98, 1.0), 0.7)
    t.brilho(cab, (0.55, 0.85, 1.0), 7, 0.5)
    for (x0, y0, x1, y1, w) in [(84, 82, 98, 92, 7), (30, 40, 40, 30, 6), (96, 60, 108, 62, 5)]:
        cristal(t, (x0, y0), (x1, y1), w)
    faiscas(t, 2, (62, 62), 44, 12, (0.6, 0.9, 1.0))
    return t.reduzir()


def frost_nova():
    cor = (0.45, 0.8, 1.0)
    t = tela(cor, 54, 0.5, 64, 64)
    t.brilho(P.anel(64, 64, 40, 6), cor, 5, 0.8)
    for k in range(12):
        a = np.radians(k * 30)
        u = np.array([np.cos(a), np.sin(a)])
        longo = 46 if k % 2 == 0 else 32
        cristal(t, tuple(np.array([64, 64]) + u * 12), tuple(np.array([64, 64]) + u * longo), 11 if k % 2 == 0 else 8, brilho_cor=cor)
    anel_m = P.anel(64, 64, 20, 4.0)
    t.volume(anel_m, GELO, 1.2, 1.0, brilho_borda=0.35)
    nucleo = P.circulo(64, 64, 10)
    t.brilho(nucleo, (0.8, 0.95, 1.0), 9, 1.0)
    esfera(t, 64, 64, 10, [(20, 60, 120), (80, 160, 220), (200, 236, 255), (255, 255, 255)])
    t.pintar(floco(64, 64, 8, 1.3, 1), (1, 1, 1), 0.85)
    faiscas(t, 4, (64, 64), 50, 16, (0.7, 0.95, 1.0))
    return t.reduzir()


def thunder_burst():
    cor = (0.5, 0.65, 1.0)
    t = tela(cor, 56, 0.5, 64, 64)
    for k in range(8):
        a = np.radians(k * 45 - 90)
        fim = (64 + np.cos(a) * 50, 64 + np.sin(a) * 50)
        r = relampago((64 + np.cos(a) * 8, 64 + np.sin(a) * 8), fim, 100 + k, desvio=9, ramos=1, largura=2.8 if k % 2 == 0 else 2.2)
        pintar_raio(t, r, cor, raio_brilho=3.0, forca=0.85)
    t.brilho(P.circulo(64, 64, 12), (0.7, 0.85, 1.0), 12, 1.0)
    esfera(t, 64, 64, 12, [(24, 36, 150), (90, 130, 250), (210, 228, 255), (255, 255, 255)])
    t.somar(P.anel(64, 64, 22, 2.0), cor, 0.7)
    t.brilho(P.anel(64, 64, 22, 2.0), cor, 4, 0.7)
    faiscas(t, 8, (64, 64), 52, 14, cor)
    return t.reduzir()


def sky_storm():
    cor = (0.5, 0.65, 1.0)
    t = tela(cor, 56, 0.40, 64, 60)
    chao = P.elipse(64, 118, 60, 12)
    t.pintar(chao, P.rampa(0.18 + 0.2 * P.ruido(4, 10, 3), PEDRA), 0.9)
    nuvem_tempestade(t, 64, 30, 108, 6)
    for k, (x0, x1) in enumerate([(36, 30), (66, 70), (94, 100)]):
        r = relampago((x0, 40), (x1, 110), 200 + k, desvio=9, ramos=1, largura=3.6)
        pintar_raio(t, r, cor, raio_brilho=3.5, forca=0.9)
        imp = P.elipse(x1, 112, 15, 5)
        t.brilho(imp, (0.7, 0.8, 1.0), 6, 1.0)
        t.pintar(imp, (0.9, 0.95, 1.0), 0.8)
    faiscas(t, 9, (64, 80), 44, 10, cor)
    return t.reduzir()


def storm_orbs():
    cor = (0.45, 0.62, 1.0)
    t = tela(cor, 56, 0.42, 64, 66)
    t.brilho(P.anel(64, 68, 36, 2.4), cor, 4, 0.55)
    pts = [(64, 32), (34, 88), (94, 88)]
    for i in range(3):
        a, b = pts[i], pts[(i + 1) % 3]
        arc = P.traco(relampago_simples(a, b, 60 + i, desvio=9), 2.8)
        pintar_raio(t, arc, cor, raio_brilho=3.2, forca=0.9)
    for (x, y) in pts:
        t.brilho(P.circulo(x, y, 14), cor, 10, 0.95)
        esfera(t, x, y, 14, [(14, 20, 100), (60, 96, 230), (160, 196, 255), (255, 255, 255)])
        for j in range(5):
            r2 = relampago_simples((x, y), (x + np.cos(j * 1.26 + x) * 19, y + np.sin(j * 1.26 + x) * 19), 80 + j + x, desvio=3)
            t.pintar(P.traco(r2, 1.0), (0.85, 0.92, 1.0), 0.75)
    faiscas(t, 3, (64, 68), 46, 10, cor)
    return t.reduzir()


def plague_spread():
    cor = (0.35, 1.0, 0.2)
    t = tela(cor, 54, 0.42, 64, 64)
    centro = (64, 66)
    sat = [(26, 32), (104, 36), (22, 98), (106, 96)]
    for i, (x, y) in enumerate(sat):
        veia = P.tubo([centro, ((centro[0] + x) / 2 + (8 if i % 2 else -8), (centro[1] + y) / 2 + 6), (x, y)], 9, 4)
        t.brilho(veia, cor, 4, 0.6)
        t.volume(veia, VENENO, 1.6, 1.0, ruido_arr=P.ruido(40 + i, 10, 3), ruido_k=0.2)
    for (x, y) in sat:
        pont = np.zeros((W, W), np.float32)
        for k in range(8):
            a = k * np.pi / 4 + 0.4
            c, s2 = np.cos(a), np.sin(a)
            pont = np.maximum(pont, P.poligono([(x + c * 6 - s2 * 2, y + s2 * 6 + c * 2), (x + c * 12, y + s2 * 12), (x + c * 6 + s2 * 2, y + s2 * 6 - c * 2)]))
        t.volume(pont, VENENO, 1.0, 1.0)
        t.brilho(P.circulo(x, y, 8), cor, 5, 0.8)
        esfera(t, x, y, 8, VENENO)
    pont = np.zeros((W, W), np.float32)
    for k in range(12):
        a = k * np.pi / 6
        c, s2 = np.cos(a), np.sin(a)
        pont = np.maximum(pont, P.poligono([(centro[0] + c * 18 - s2 * 4, centro[1] + s2 * 18 + c * 4), (centro[0] + c * 30, centro[1] + s2 * 30), (centro[0] + c * 18 + s2 * 4, centro[1] + s2 * 18 - c * 4)]))
    t.brilho(pont, cor, 5, 0.7)
    t.volume(pont, VENENO, 1.4, 1.0)
    t.brilho(P.circulo(*centro, 20), cor, 10, 0.9)
    esfera(t, centro[0], centro[1], 20, VENENO)
    # caveira pequena no centro
    cr = P.seguir(P.elipse(centro[0], centro[1] - 2, 9, 8), P.poligono([(centro[0] - 5, centro[1] + 3), (centro[0] + 5, centro[1] + 3), (centro[0] + 4, centro[1] + 10), (centro[0] - 4, centro[1] + 10)]))
    t.pintar(cr, P.rampa(0.55 + 0.35 * P.luz_da_forma(cr, 1.6), OSSO), 0.95)
    t.pintar(P.seguir(P.circulo(centro[0] - 3.6, centro[1] - 2, 2.4), P.circulo(centro[0] + 3.6, centro[1] - 2, 2.4)), (0.06, 0.2, 0.04))
    faiscas(t, 5, (64, 64), 50, 12, cor)
    return t.reduzir()


def acid_geyser():
    cor = (0.5, 1.0, 0.15)
    t = tela(cor, 54, 0.40, 64, 60)
    # jato: coluna que alarga embaixo e se abre em copa no alto
    col = P.tubo([(64, 112), (62, 84), (66, 56), (64, 30)], 24, 12)
    topo = P.seguir(P.elipse(64, 26, 20, 10), P.circulo(48, 30, 7), P.circulo(80, 30, 7))
    jato = np.maximum(col, topo)
    wob = P.ruido(9, (10, 28), 3)
    jato = np.clip(P.deformar(jato, (wob - 0.5) * 8, 0), 0, 1)
    v = P.luz_da_forma(jato, 3.0) * 0.6 + P.ruido(10, (8, 20), 3) * 0.4
    t.brilho(jato, cor, 8, 0.7)
    t.pintar(jato, P.rampa(np.clip(v, 0, 1), VENENO))
    t.somar(P.borda_luz(jato).clip(0, 1) * jato, (0.8, 1.0, 0.5), 0.6)
    # bolhas dentro e gotas ao redor
    rng = np.random.default_rng(5)
    for k in range(12):
        x = 64 + rng.uniform(-9, 9)
        y = rng.uniform(34, 100)
        b = P.anel(x, y, rng.uniform(1.4, 2.6), 0.9)
        t.pintar(b * jato, (0.9, 1.0, 0.7), 0.7)
    for k in range(12):
        a = rng.uniform(-2.7, -0.4)
        r = rng.uniform(18, 34)
        x, y = 64 + np.cos(a) * r, 34 + np.sin(a) * r * 0.8 + 6
        m = P.circulo(x, y, rng.uniform(1.4, 2.8))
        t.brilho(m, cor, 2.5, 0.7)
        t.pintar(m, P.rampa(0.8, VENENO), 1.0)
    # chão rachado e poça
    solo = P.seguir(P.elipse(64, 112, 44, 10), P.elipse(32, 108, 14, 6), P.elipse(96, 108, 14, 6))
    t.volume(solo, PEDRA, 2.0, 1.0, ruido_arr=P.ruido(6, 8, 3), ruido_k=0.25)
    poca = P.elipse(64, 110, 26, 5.5)
    t.brilho(poca, cor, 5, 0.9)
    t.pintar(poca, P.rampa(0.65 + 0.3 * P.ruido(3, 8, 2), VENENO), 0.95)
    return t.reduzir()


def icicle_lance():
    cor = (0.5, 0.82, 1.0)
    t = tela(cor, 54, 0.45, 64, 64)
    a = np.array([22.0, 106.0])
    b = np.array([108.0, 20.0])
    u = (b - a) / np.linalg.norm(b - a)
    nrm = np.array([-u[1], u[0]])
    # rastro de frio
    rastro = P.tubo([tuple(a), tuple(a + u * 40)], 4, 16)
    f, al = chama(rastro, 3, subida=8, vento=4, passos=3, periodo=(24, 12), fluxo=(-1.0, 0.8))
    t.pintar(al, P.rampa(P.degrau(f, 0.05, 0.9) * 0.7, GELO), 0.75)
    # haste de cristal
    haste = P.traco([tuple(a + u * 8), tuple(b - u * 34)], 5.5)
    t.volume(haste, GELO, 1.2, 1.0, brilho_borda=0.4)
    t.pintar(P.traco([tuple(a + u * 8 - nrm * 0.8), tuple(b - u * 34 - nrm * 0.8)], 1.1) * haste, (0.95, 1.0, 1.0), 0.8)
    # ponta da lança
    cristal(t, tuple(b - u * 40), tuple(b + u * 10), 17, brilho_cor=cor)
    for off in (-8, 8):
        cristal(t, tuple(b - u * 34 + nrm * off), tuple(b - u * 20 + nrm * off * 2.0), 6)
    # estilhaços
    for (x0, y0, x1, y1, w) in [(40, 46, 30, 30, 6), (82, 90, 98, 98, 6), (52, 98, 40, 110, 5)]:
        cristal(t, (x0, y0), (x1, y1), w)
    t.brilho(P.circulo(*(b + u * 4), 4), (0.9, 1.0, 1.0), 8, 1.0)
    faiscas(t, 6, (64, 64), 48, 14, cor)
    return t.reduzir()


def ice_spikes():
    cor = (0.5, 0.82, 1.0)
    t = tela(cor, 54, 0.45, 64, 74)
    chao = P.elipse(64, 108, 52, 9)
    t.brilho(chao, cor, 6, 0.6)
    t.pintar(chao, P.rampa(0.35 + 0.4 * P.ruido(4, 8, 3), GELO), 0.9)
    espinhos = [(22, 108, 28, 58, 12), (104, 108, 100, 60, 12), (40, 106, 36, 38, 17), (88, 106, 92, 40, 17), (64, 108, 64, 14, 24), (52, 108, 52, 52, 12), (76, 108, 78, 50, 12)]
    for (bx, by, px, py, w) in sorted(espinhos, key=lambda e: e[3] - e[1] * 0.0, reverse=False)[::-1]:
        cristal(t, (bx, by), (px, py), w, brilho_cor=cor)
    nevoa = P.elipse(64, 108, 54, 7)
    t.somar(P.gauss(nevoa, 4) * (0.5 + 0.5 * P.ruido(2, 14, 2)), (0.8, 0.92, 1.0), 0.5)
    faiscas(t, 5, (64, 60), 46, 14, cor)
    return t.reduzir()


def blizzard():
    cor = (0.6, 0.85, 1.0)
    t = tela(cor, 56, 0.40, 64, 64)
    n = P.ruido(5, (26, 26), 5)
    base = P.degrau(n, 0.38, 0.75) * np.clip(1.2 - np.hypot(X - 64, Y - 64) / 52.0, 0, 1)
    sw = torcer(base, 64, 64, 2.4, 44.0)
    sw = torcer(sw, 64, 64, 1.6, 30.0)
    t.brilho(sw, cor, 6, 0.5)
    t.pintar(np.clip(sw * 1.6, 0, 1), P.rampa(0.25 + 0.7 * torcer(n, 64, 64, 2.4, 44.0), GELO), 0.95)
    # riscos de vento em espiral
    rng = np.random.default_rng(8)
    for k in range(6):
        a0 = k * np.pi / 3
        pts = [(64 + np.cos(a0 + j * 0.5) * (8 + j * 6), 64 + np.sin(a0 + j * 0.5) * (8 + j * 6)) for j in range(9)]
        t.pintar(P.traco(pts, 1.8) * np.clip(P.ruido(70 + k, 14, 2) * 1.8, 0, 1), (0.92, 0.98, 1.0), 0.8)
    # flocos
    for k in range(9):
        a = rng.uniform(0, 2 * np.pi)
        r = rng.uniform(16, 46)
        x, y = 64 + np.cos(a) * r, 64 + np.sin(a) * r
        fl = floco(x, y, rng.uniform(4.5, 7.5), 1.2, 1)
        t.brilho(fl, cor, 2.5, 0.5)
        t.pintar(fl, (0.96, 1.0, 1.0), 0.95)
    t.brilho(P.circulo(64, 64, 8), (0.9, 1.0, 1.0), 8, 0.9)
    t.pintar(floco(64, 64, 11, 1.8, 2), (1, 1, 1), 1.0)
    return t.reduzir()


def fuse_bomb():
    t = tela((1.0, 0.5, 0.1), 54, 0.42, 60, 76)
    # bomba pequena ao fundo (a cadeia)
    t.sombra(P.circulo(98, 90, 14), 3, 0.5)
    esfera(t, 98, 88, 13, FERRO, 0.95)
    t.pintar(P.traco([(98, 76), (96, 70), (100, 64)], 1.6), (0.7, 0.5, 0.3))
    t.brilho(P.circulo(100, 63, 2.6), (1, 0.6, 0.15), 5, 0.9)
    t.pintar(P.circulo(100, 63, 1.8), (1, 0.95, 0.6))
    # bomba principal
    t.sombra(P.circulo(56, 80, 28), 4, 0.6)
    esfera(t, 54, 78, 28, [(6, 6, 10), (30, 30, 38), (70, 70, 84), (134, 132, 146), (210, 204, 200)])
    cinta = P.anel(54, 78, 20, 2.0)
    t.pintar(cinta * P.circulo(54, 78, 28), (0.5, 0.36, 0.2), 0.5)
    for k in range(6):
        a = k * np.pi / 3 + 0.4
        t.pintar(P.circulo(54 + np.cos(a) * 20, 78 + np.sin(a) * 20, 1.6), (0.7, 0.55, 0.3), 0.8)
    # tampa e rastilho
    tampa = P.poligono([(46, 54), (62, 54), (64, 46), (44, 46)])
    t.volume(tampa, OURO, 1.0, 1.0, brilho_borda=0.3)
    rastilho = P.tubo([(54, 46), (54, 36), (66, 28), (74, 14)], 3.2, 2.2)
    t.volume(rastilho, MADEIRA, 1.0, 1.0)
    for k in range(10):
        a = k * 0.62
        t.pintar(P.traco([(74 + np.cos(a) * 3, 14 + np.sin(a) * 3), (74 + np.cos(a) * 10, 14 + np.sin(a) * 10)], 1.2), (1.0, 0.8, 0.3), 0.9)
    t.brilho(P.circulo(74, 14, 5), (1.0, 0.6, 0.15), 8, 1.0)
    t.pintar(P.circulo(74, 14, 3.6), (1.0, 0.96, 0.7))
    # faísca ligando as bombas
    t.pintar(P.traco(relampago_simples((80, 66), (96, 70), 5, desvio=3), 1.3), (1.0, 0.8, 0.3), 0.9)
    faiscas(t, 14, (70, 40), 24, 8, (1.0, 0.55, 0.1))
    return t.reduzir()


def ember_tip():
    t = tela((1.0, 0.4, 0.06), 54, 0.5, 66, 62)
    # ponta de flecha grande em brasa, com veios de lava
    cab = P.poligono([(100, 18), (68, 40), (38, 54), (62, 62), (52, 94), (76, 72), (84, 46)])
    cab = P.poligono([(104, 14), (74, 28), (40, 64), (60, 72), (50, 98), (80, 80), (92, 46)])
    haste = P.traco([(52, 86), (20, 114)], 5.0)
    t.sombra(cab, 3, 0.5)
    t.volume(haste, MADEIRA, 1.0, 1.0)
    r1 = P.ruido(2, 12, 4)
    luz = P.luz_da_forma(cab, 3.2)
    t.brilho(cab, (1.0, 0.45, 0.1), 7, 0.9)
    t.pintar(cab, P.rampa(np.clip(luz * 0.7 + (r1 - 0.5) * 0.5 + 0.1, 0, 1), BRASA))
    veio = P.degrau(1.0 - np.abs(P.ruido(14, 9, 3) - 0.5) * 2.0, 0.74, 0.96)
    ponta_q = np.clip(1.0 - np.hypot(X - 104, Y - 14) / 70.0, 0, 1)
    t.pintar(cab * np.clip(veio + ponta_q * 0.5, 0, 1), P.rampa(0.5 + 0.5 * np.clip(ponta_q * 1.4 + r1 * 0.3, 0, 1), FOGO))
    t.somar(P.borda_luz(cab).clip(0, 1) * cab, (1.0, 0.7, 0.3), 0.6)
    pintar_fogo(t, P.poligono([(100, 14), (88, 30), (96, 36)]), 3, subida=10, vento=4, passos=3)
    faiscas(t, 14, (64, 60), 46, 18, (1.0, 0.5, 0.1), tam=(0.9, 2.0))
    return t.reduzir()


def extra_shot():
    cor = (1.0, 0.82, 0.35)
    t = tela(cor, 52, 0.38, 62, 66)
    claro = [(150, 110, 60), (210, 170, 100), (250, 220, 150), (255, 250, 220)]
    for ang, comp, w in [(-26, 76, 5.2), (26, 76, 5.2), (0, 90, 6.2)]:
        a = np.radians(ang - 90)
        u = np.array([np.cos(a), np.sin(a)])
        p0 = np.array([58.0, 112.0])
        flecha(t, tuple(p0), tuple(p0 + u * comp), haste=w, ponta=(22, 11.5) if ang == 0 else (19, 10), pena=(10, 7.5), r_haste=claro, r_ponta=OURO, r_pena=[(160, 140, 110), (230, 214, 180), (252, 244, 224), (255, 255, 250)], brilho_cor=(1, 0.8, 0.3))
    t.sombra(P.circulo(100, 98, 17), 3, 0.5)
    t.brilho(P.circulo(100, 98, 16), cor, 6, 0.8)
    esfera(t, 100, 98, 16, OURO, brilho=0.4)
    mais = P.seguir(P.traco([(100, 89), (100, 107)], 5.2), P.traco([(91, 98), (109, 98)], 5.2))
    t.pintar(mais, (0.18, 0.1, 0.02), 0.95)
    t.pintar(P.deslocar(mais, 0, -0.8), (1, 0.97, 0.8), 0.9)
    faiscas(t, 3, (60, 50), 44, 8, cor)
    return t.reduzir()


def swift_shots():
    cor = (0.35, 0.95, 0.9)
    t = tela(cor, 54, 0.42, 64, 64)
    a = np.array([28.0, 100.0])
    b = np.array([110.0, 20.0])
    u = (b - a) / np.linalg.norm(b - a)
    v = np.array([-u[1], u[0]])
    rng = np.random.default_rng(6)
    for k, off in enumerate([-24, -16, -8, 8, 16, 24]):
        ini = a + v * off + u * rng.uniform(0, 12)
        for j in range(2):
            q0 = ini - u * j * 18
            m = P.tubo([tuple(q0), tuple(q0 - u * 17)], 3.6 - j * 0.8, 0.8)
            t.brilho(m, cor, 3, 0.55)
            t.pintar(m, (0.85, 1.0, 0.98), 0.9 - j * 0.25)
    cianos = [(6, 40, 40), (30, 120, 120), (90, 200, 190), (190, 250, 240)]
    flecha(t, tuple(a + u * 4), tuple(b), haste=4.0, ponta=(20, 10), r_haste=cianos, r_ponta=GELO, r_pena=[(20, 60, 60), (90, 170, 170), (190, 240, 232), (250, 255, 250)], brilho_cor=cor)
    for sg in (-1, 1):
        c = a + (b - a) * 0.46
        asa = P.poligono([tuple(c), tuple(c + u * 18 + v * sg * 17), tuple(c + u * 7 + v * sg * 3)])
        t.volume(asa, [(20, 60, 60), (90, 170, 170), (190, 240, 232), (250, 255, 250)], 1.2, 1.0, brilho_borda=0.35)
    faiscas(t, 2, (70, 56), 40, 8, cor)
    return t.reduzir()


def lingering():
    cor = (0.75, 0.5, 1.0)
    t = tela(cor, 54, 0.42, 64, 68)
    # zona acesa no chão
    t.brilho(P.anel(64, 108, 34, 4), cor, 5, 0.9)
    zona = P.elipse(64, 108, 42, 9)
    t.pintar(zona, P.rampa(0.25 + 0.3 * P.ruido(4, 12, 3), [(12, 6, 30), (60, 30, 120), (130, 84, 220), (200, 160, 255)]), 0.8)
    # ampulheta: vidro, areia e moldura
    vidro = P.seguir(P.poligono([(40, 24), (88, 24), (88, 34), (70, 58), (70, 70), (88, 94), (88, 104), (40, 104), (40, 94), (58, 70), (58, 58), (40, 34)]))
    t.sombra(vidro, 3, 0.5)
    t.pintar(vidro, P.rampa(0.18 + 0.5 * P.luz_da_forma(vidro, 2.5), [(10, 8, 28), (60, 40, 120), (130, 100, 220), (200, 180, 255)]), 0.85)
    areia_t = P.seguir(P.poligono([(50, 36), (78, 36), (68, 54), (60, 54)]))
    areia_b = P.seguir(P.poligono([(42, 102), (86, 102), (80, 92), (64, 80), (48, 92)]))
    for m in (areia_t, areia_b):
        t.brilho(m, (1.0, 0.7, 0.3), 5, 0.7)
        t.pintar(m, P.rampa(0.55 + 0.45 * P.luz_da_forma(m, 2.0), OURO), 0.95)
    fio = P.traco([(64, 56), (64, 82)], 1.7)
    t.brilho(fio, (1, 0.8, 0.4), 3, 0.9)
    t.pintar(fio, (1, 0.92, 0.6), 0.95)
    t.somar(P.borda_luz(vidro).clip(0, 1) * vidro, (0.9, 0.85, 1.0), 0.6)
    for y in (18, 105):
        placa = P.poligono([(34, y), (94, y), (94, y + 8), (34, y + 8)])
        t.volume(placa, MADEIRA if False else OURO, 1.2, 1.0, brilho_borda=0.35)
    for x in (38, 90):
        col = P.traco([(x, 26), (x, 104)], 3.2)
        t.volume(col, OURO, 1.0, 1.0, brilho_borda=0.3)
    faiscas(t, 5, (64, 64), 44, 12, cor)
    return t.reduzir()


def piercing_skills():
    cor = (0.8, 0.5, 1.0)
    t = tela(cor, 54, 0.42, 64, 64)
    a = np.array([20.0, 108.0])
    b = np.array([108.0, 20.0])
    u = (b - a) / np.linalg.norm(b - a)
    v = np.array([-u[1], u[0]])
    ang = np.degrees(np.arctan2(v[1], v[0]))
    aneis = []
    for f in (0.40, 0.68):
        c = a + (b - a) * f
        anel_m = np.clip(P.elipse(c[0], c[1], 27, 11, ang) - P.elipse(c[0], c[1], 21, 5.2, ang), 0, 1)
        aneis.append((c, anel_m))
        t.brilho(anel_m, cor, 5, 0.9)
        t.volume(anel_m, [(40, 14, 100), (100, 60, 200), (170, 120, 250), (240, 220, 255)], 1.6, 1.0, brilho_borda=0.5)
    flecha(t, tuple(a), tuple(b), haste=4.0, ponta=(20, 10), r_haste=[(150, 140, 160), (200, 190, 210), (240, 232, 246), (255, 255, 255)], r_ponta=[(120, 120, 140), (180, 180, 200), (235, 235, 245), (255, 255, 255)], r_pena=[(90, 30, 140), (170, 100, 230), (230, 180, 255), (255, 240, 255)], brilho_cor=cor)
    # a metade da frente de cada anel volta por cima da flecha: ela passa por dentro
    for c, anel_m in aneis:
        frente = anel_m * np.clip((((X - c[0]) * v[0] + (Y - c[1]) * v[1]) / 2.0 + 0.5), 0, 1)
        t.volume(frente, [(40, 14, 100), (100, 60, 200), (170, 120, 250), (240, 220, 255)], 1.6, 1.0, brilho_borda=0.5)
        est = np.zeros((W, W), np.float32)
        for k in range(10):
            g = k * np.pi / 5 + 0.3
            r1 = 11 if k % 2 == 0 else 6
            est = np.maximum(est, P.poligono([(c[0] + np.cos(g - 0.2) * 2.5, c[1] + np.sin(g - 0.2) * 2.5), (c[0] + np.cos(g) * r1, c[1] + np.sin(g) * r1), (c[0] + np.cos(g + 0.2) * 2.5, c[1] + np.sin(g + 0.2) * 2.5)]))
        t.brilho(est, cor, 3, 0.7)
        t.pintar(est, (1.0, 0.94, 1.0), 0.85)
    for (x0, y0, x1, y1, w) in [(44, 36, 34, 20, 5), (92, 90, 108, 98, 5), (56, 102, 48, 116, 4)]:
        cristal(t, (x0, y0), (x1, y1), w, rampa=[(20, 8, 50), (80, 40, 150), (160, 100, 240), (230, 200, 255), (255, 255, 255)])
    faiscas(t, 8, (64, 64), 46, 10, cor)
    return t.reduzir()


def flame_lore():
    t = tela((1.0, 0.45, 0.08), 52, 0.45, 64, 66)
    pag = livro(t, 64, 86, (1.0, 0.55, 0.15))
    forma = P.seguir(P.elipse(64, 53, 14.4, 26.4), P.circulo(64, 63, 16.8))   # chama 20% maior (pedido da revisão)
    pintar_fogo(t, forma, 5, ganho=0.72, subida=20, vento=7, passos=4, periodo=(12, 28))
    pintar_fogo(t, P.elipse(64, 60, 8.4, 15.6), 6, ganho=0.95, paleta=FOGO, subida=9, vento=3.5, passos=3)
    faiscas(t, 9, (64, 44), 30, 14, (1.0, 0.55, 0.1))
    return t.reduzir()


def frost_lore():
    cor = (0.5, 0.82, 1.0)
    t = tela(cor, 52, 0.45, 64, 66)
    livro(t, 64, 86, cor, capa=[(6, 12, 26), (24, 48, 86), (50, 96, 150), (96, 156, 206)])
    fl = floco(64, 44, 25, 2.6, 2)
    t.brilho(fl, cor, 6, 0.9)
    t.volume(fl, GELO, 1.0, 1.0, brilho_borda=0.4)
    t.brilho(P.circulo(64, 44, 6), (0.9, 1, 1), 6, 0.9)
    faiscas(t, 4, (64, 44), 30, 12, cor)
    return t.reduzir()


def storm_lore():
    cor = (0.5, 0.65, 1.0)
    t = tela(cor, 52, 0.45, 64, 66)
    livro(t, 64, 86, cor, capa=[(8, 10, 30), (30, 40, 100), (60, 80, 170), (110, 140, 230)])
    t.brilho(P.elipse(64, 46, 22, 30), cor, 10, 0.5)
    r = relampago((76, 8), (54, 62), 321, desvio=9, ramos=2, largura=6.5)
    pintar_raio(t, r, cor, raio_brilho=5.0, forca=1.0)
    r2 = relampago_simples((38, 22), (50, 58), 5, desvio=4)
    pintar_raio(t, P.traco(r2, 2.8), cor, raio_brilho=3.0, forca=0.8)
    faiscas(t, 6, (64, 44), 30, 12, cor)
    return t.reduzir()


def venom_lore():
    cor = (0.35, 1.0, 0.2)
    t = tela(cor, 52, 0.45, 64, 66)
    livro(t, 64, 86, cor, capa=[(6, 18, 8), (24, 62, 24), (56, 118, 46), (110, 180, 80)])
    g = gota(64, 52, 16, 36)
    t.brilho(g, cor, 6, 0.9)
    t.sombra(g, 3, 0.4)
    t.pintar(g, P.rampa(np.clip(P.luz_da_forma(g, 3.5) * 0.9 + 0.1, 0, 1), VENENO))
    t.somar(P.borda_luz(g).clip(0, 1) * g, (0.8, 1, 0.5), 0.6)
    cr = P.seguir(P.elipse(64, 52, 8, 7), P.poligono([(59, 56), (69, 56), (68, 63), (60, 63)]))
    t.pintar(cr, P.rampa(0.55 + 0.35 * P.luz_da_forma(cr, 1.4), OSSO), 0.95)
    t.pintar(P.seguir(P.circulo(60.6, 51, 2.1), P.circulo(67.4, 51, 2.1)), (0.05, 0.18, 0.04))
    for (x, y, r) in [(34, 40, 4), (96, 36, 3.2), (90, 56, 2.4)]:
        gg = gota(x, y, r)
        t.brilho(gg, cor, 3, 0.7)
        t.pintar(gg, P.rampa(0.7, VENENO), 0.95)
    return t.reduzir()


def keen_eye():
    cor = (0.35, 0.9, 0.95)
    t = tela(cor, 54, 0.42, 64, 64)
    # retículo
    for pts in ([(64, 8), (64, 28)], [(64, 100), (64, 120)], [(8, 64), (28, 64)], [(100, 64), (120, 64)]):
        t.brilho(P.traco(pts, 1.6), cor, 3, 0.6)
        t.pintar(P.traco(pts, 1.8), (0.7, 0.95, 1.0), 0.85)
    t.pintar(P.anel(64, 64, 52, 1.2), cor, 0.35)
    olho = np.clip(P.circulo(64, 112, 80) * P.circulo(64, 16, 80), 0, 1)
    olho = np.clip(P.elipse(64, 64, 46, 24), 0, 1)
    t.sombra(olho, 4, 0.5)
    esc = P.rampa(np.clip(0.3 + 0.6 * P.luz_da_forma(olho, 3.0), 0, 1), [(40, 36, 36), (150, 140, 130), (226, 216, 200), (255, 250, 240)])
    t.pintar(olho, esc)
    t.somar(P.borda_luz(olho).clip(0, 1) * olho, cor, 0.7)
    t.pintar(np.clip(P.elipse(64, 64, 46, 24) - P.elipse(64, 64, 42, 20), 0, 1), (0.04, 0.05, 0.08), 0.85)
    # íris com raios
    r = np.hypot(X - 64, Y - 64)
    ang = np.arctan2(Y - 64, X - 64)
    raios = 0.5 + 0.5 * np.sin(ang * 22 + P.ruido(3, 10, 2) * 6)
    iris = P.circulo(64, 64, 21) * olho
    v = np.clip(0.25 + 0.5 * (1 - r / 21) + 0.18 * raios, 0, 1)
    t.brilho(iris, cor, 6, 0.6)
    t.pintar(iris, P.rampa(v, [(6, 40, 56), (20, 120, 140), (70, 200, 210), (210, 250, 245)]))
    t.pintar(P.anel(64, 64, 20, 1.8) * olho, (0.02, 0.1, 0.14), 0.9)
    pup = P.elipse(64, 64, 6.2, 11)
    t.pintar(pup, (0.02, 0.03, 0.05), 1.0)
    t.pintar(P.circulo(57, 57, 3.0), (1, 1, 1), 0.95)
    t.pintar(P.circulo(70, 71, 1.4), (0.8, 1, 1), 0.7)
    return t.reduzir()


def deadly_aim():
    cor = (1.0, 0.25, 0.2)
    t = tela(cor, 54, 0.45, 64, 64)
    # estouro crítico atrás
    pont = np.zeros((W, W), np.float32)
    for k in range(16):
        a = k * np.pi / 8
        c, s2 = np.cos(a), np.sin(a)
        r0, r1 = 26, 52 if k % 2 == 0 else 40
        pont = np.maximum(pont, P.poligono([(64 + c * r0 - s2 * 5, 64 + s2 * r0 + c * 5), (64 + c * r1, 64 + s2 * r1), (64 + c * r0 + s2 * 5, 64 + s2 * r0 - c * 5)]))
    t.brilho(pont, cor, 5, 0.7)
    t.volume(pont, [(40, 4, 6), (140, 18, 18), (230, 60, 40), (255, 150, 90), (255, 230, 190)], 1.2, 1.0, brilho_borda=0.3)
    # mira
    for ini, fim in [(0, 75), (90, 165), (180, 255), (270, 345)]:
        pts = [(64 + np.cos(np.radians(g)) * 30, 64 + np.sin(np.radians(g)) * 30) for g in range(ini + 8, fim - 8, 6)]
        t.volume(P.traco(pts, 4.0), OURO, 1.0, 1.0, brilho_borda=0.4)
    for g in (0, 90, 180, 270):
        c, s2 = np.cos(np.radians(g)), np.sin(np.radians(g))
        t.volume(P.traco([(64 + c * 22, 64 + s2 * 22), (64 + c * 42, 64 + s2 * 42)], 3.4), OURO, 1.0, 1.0, brilho_borda=0.4)
    t.brilho(P.circulo(64, 64, 5), cor, 8, 1.0)
    # flecha cravada no alvo
    flecha(t, (112, 14), (68, 60), haste=3.0, ponta=(13, 6.5), r_pena=[(60, 8, 10), (170, 30, 30), (240, 90, 70), (255, 200, 170)], brilho_cor=None)
    t.brilho(P.circulo(64, 64, 4), (1, 0.8, 0.6), 6, 1.0)
    t.pintar(P.circulo(64, 64, 2.6), (1, 0.95, 0.85))
    faiscas(t, 11, (64, 64), 46, 10, (1.0, 0.5, 0.2))
    return t.reduzir()


def eco_trovao():
    cor = (0.5, 0.7, 1.0)
    t = tela(cor, 54, 0.45, 64, 64)
    p0, p1 = (22, 106), (106, 22)
    # arcos elétricos em volta da haste, grossos para sobreviver aos 48 px
    t.brilho(P.tubo([p0, p1], 20, 20), cor, 7, 0.5)
    flecha(t, p0, p1, haste=4.6, ponta=(22, 11), pena=(9, 6.5), r_haste=[(10, 14, 50), (40, 56, 150), (110, 150, 240), (225, 238, 255)], r_ponta=[(10, 14, 40), (50, 80, 190), (150, 190, 255), (255, 255, 255)], r_pena=[(20, 30, 90), (70, 100, 200), (160, 190, 255), (245, 250, 255)], brilho_cor=cor)
    for k, off in enumerate((-13, 13)):
        pts = relampago_simples((p0[0] + 16 + off * 0.7, p0[1] - 16 + off * 0.7), (p1[0] - 16 + off * 0.7, p1[1] + 16 + off * 0.7), 40 + k, desvio=10, niveis=3)
        pintar_raio(t, P.traco(pts, 3.4), cor, raio_brilho=3.4, forca=0.95)
    r = relampago(p1, (118, 8), 3, desvio=4, niveis=2, ramos=1, largura=3.2)
    pintar_raio(t, r, cor, raio_brilho=3.4)
    ponta_luz = P.circulo(p1[0], p1[1], 4.0)
    t.brilho(ponta_luz, cor, 5, 1.0)
    faiscas(t, 21, (64, 64), 46, 12, cor)
    return t.reduzir()


def eco_peste():
    cor = (0.35, 1.0, 0.2)
    t = tela(cor, 54, 0.42, 64, 64)
    p0, p1 = (24, 104), (104, 24)
    # miasma em volta
    nuv = P.ruido(5, (18, 18), 4)
    corpo = P.tubo([p0, p1], 26, 26)
    f = P.deformar(P.gauss(corpo, 4), (nuv - 0.5) * 16, (P.ruido(6, (18, 18), 4) - 0.5) * 16)
    t.pintar(np.clip(f * 1.3 - 0.25, 0, 1), P.rampa(0.35 + 0.5 * nuv, VENENO), 0.55)
    flecha(t, p0, p1, haste=3.4, ponta=(16, 8), r_haste=[(8, 30, 8), (30, 90, 20), (80, 160, 40), (160, 230, 70)], r_ponta=[(8, 24, 8), (30, 80, 20), (90, 170, 40), (200, 250, 120)], r_pena=[(20, 50, 10), (60, 120, 30), (140, 200, 60), (230, 255, 150)], brilho_cor=cor)
    # gotas de veneno pingando da ponta
    for (x, y, r) in [(94, 46, 4.2), (80, 64, 3.2), (104, 62, 3.0), (60, 84, 3.4)]:
        gg = gota(x, y + 2, r)
        t.brilho(gg, cor, 3, 0.8)
        t.pintar(gg, P.rampa(0.75, VENENO), 1.0)
        t.pintar(P.circulo(x - r * 0.3, y + 1, r * 0.3), (1, 1, 0.9), 0.8)
    faiscas(t, 22, (64, 64), 46, 8, cor)
    return t.reduzir()


def eco_gelo():
    cor = (0.5, 0.85, 1.0)
    t = tela(cor, 54, 0.45, 64, 64)
    p0, p1 = (22, 106), (106, 22)
    flecha(t, p0, p1, haste=4.6, ponta=(22, 11), pena=(9, 6.5), r_haste=[(10, 30, 60), (50, 110, 170), (140, 210, 250), (235, 250, 255)], r_ponta=[(6, 20, 50), (40, 100, 170), (130, 210, 250), (255, 255, 255)], r_pena=[(30, 70, 120), (100, 170, 220), (200, 235, 255), (255, 255, 255)], brilho_cor=cor)
    for (x0, y0, x1, y1, w) in [(70, 54, 62, 34, 7), (50, 78, 32, 74, 7), (88, 70, 106, 78, 7), (38, 52, 22, 40, 6)]:
        cristal(t, (x0, y0), (x1, y1), w)
    fl = floco(92, 96, 11, 1.5, 1)
    t.brilho(fl, cor, 3, 0.7)
    t.pintar(fl, (0.95, 1, 1), 0.95)
    faiscas(t, 23, (64, 64), 46, 14, cor)
    return t.reduzir()


def eco_cinzas():
    cor = (1.0, 0.5, 0.1)
    t = tela(cor, 54, 0.45, 64, 64)
    p0, p1 = (22, 106), (106, 22)
    haste_m = P.tubo([(42, 86), (92, 36)], 9, 12)
    pintar_fogo(t, haste_m, 8, ganho=0.8, subida=20, vento=6, passos=4, periodo=(14, 22), fluxo=(-0.8, 0.8))
    flecha(t, p0, p1, haste=4.6, ponta=(22, 11), pena=(9, 6.5), r_haste=[(14, 8, 8), (60, 34, 24), (130, 76, 42), (210, 130, 74)], r_ponta=[(10, 6, 6), (60, 48, 46), (136, 116, 110), (225, 205, 196)], r_pena=[(30, 14, 10), (110, 50, 20), (200, 110, 40), (255, 200, 120)], brilho_cor=cor)
    pintar_fogo(t, P.poligono([(106, 22), (94, 34), (100, 44)]), 9, ganho=0.9, subida=10, vento=4, passos=3)
    rng = np.random.default_rng(31)
    for k in range(18):
        x, y = rng.uniform(20, 108), rng.uniform(40, 112)
        m = P.circulo(x, y, rng.uniform(0.9, 1.8))
        t.pintar(m, P.rampa(rng.uniform(0.4, 0.9), PEDRA), 0.9)
    faiscas(t, 24, (64, 64), 46, 14, cor)
    return t.reduzir()


def wide_reach():
    """Leque de cinco flechas de ouro claro, bem separadas, abrindo em arco sobre um setor escuro, com um fio de arco além das pontas."""
    cor = (1.0, 0.85, 0.4)
    t = tela(cor, 54, 0.22, 64, 60)
    haste = [(205, 170, 108), (240, 216, 150), (255, 244, 200), (255, 252, 236)]
    ponta_c = [(150, 100, 30), (222, 172, 70), (255, 224, 124), (255, 250, 218)]
    pena = [(130, 100, 56), (200, 164, 100), (240, 214, 150), (255, 244, 206)]
    origem = np.array([64.0, 112.0])
    # setor escuro de fundo (a área que o leque cobre)
    r, ang = polar(origem[0], origem[1])
    setor = P.gauss(((r < 88) & (np.abs(ang + 90) < 50)).astype(np.float32), 1.2)
    t.pintar(setor, P.rampa(np.clip(r / 92.0, 0, 1) ** 1.3 * 0.55 + 0.05, [(10, 7, 4), (30, 20, 8), (62, 42, 14), (96, 68, 24)]), 0.75)
    pontas = []
    for ang_f, comp, w in [(-42, 66, 5.6), (-21, 82, 5.8), (0, 92, 6.6), (21, 82, 5.8), (42, 66, 5.6)]:
        a = np.radians(ang_f - 90)
        u = np.array([np.cos(a), np.sin(a)])
        p1 = origem + u * comp
        pontas.append(tuple(p1))
        flecha(t, tuple(origem + u * 11), tuple(p1), haste=w, ponta=(28, 15) if ang_f == 0 else (25, 13.5), pena=(9, 6.5),
               r_haste=haste, r_ponta=ponta_c, r_pena=pena, brilho_cor=None, n_penas=2)
    # fio de arco além das pontas, bem fino, só para dizer "área"
    arco = P.traco(P.spline([(x + (x - 64.0) * 0.06, y - 6.0) for x, y in pontas], 60), 1.6)
    t.brilho(arco, cor, 2.6, 0.5)
    t.pintar(arco, P.rampa(0.8, OURO), 0.8)
    # pino do leque
    t.sombra(P.circulo(64, 112, 10), 2, 0.5)
    esfera(t, 64, 112, 9.5, OURO, brilho=0.5)
    faiscas(t, 12, (64, 50), 42, 8, cor)
    return t.reduzir()

def focus():
    """Seta circular roxa com friso dourado em volta de um raio pequeno, de ouro."""
    cor = (0.62, 0.36, 1.0)
    t = tela(cor, 54, 0.4, 64, 64)
    cx, cy, R, esp = 64.0, 64.0, 37.0, 12.0
    r, ang = polar(cx, cy)
    # arco de 296 graus, em sentido horário, que termina numa ponta de seta no alto
    a0, a1 = -48.0, 248.0
    rel = (ang - a0) % 360.0
    arco = ((np.abs(r - R) < esp / 2) & (rel < (a1 - a0))).astype(np.float32)
    # ponta da seta
    th = np.radians(a1)
    fim = np.array([cx + R * np.cos(th), cy + R * np.sin(th)])
    tang = np.array([-np.sin(th), np.cos(th)])
    nrm = np.array([np.cos(th), np.sin(th)])
    ponta = P.poligono([tuple(fim + tang * 22), tuple(fim + nrm * 15 - tang * 2), tuple(fim - nrm * 15 - tang * 2)])
    tudo = np.maximum(arco, ponta)
    t.brilho(tudo, cor, 6, 0.55)
    t.sombra(P.deslocar(tudo, 1.5, 2.5), 2.5, 0.5)
    t.volume(tudo, OURO, 2.2, 1.0, brilho_borda=0.4)
    miolo = np.clip(P.gauss(tudo, 1.5) * 1.6 - 0.62, 0, 1)
    t.volume(miolo, ROXO, 2.0, 1.0, brilho_borda=0.25)
    # raio pequeno no centro
    raio = P.poligono([(71, 36), (51, 68), (62, 68), (55, 92), (79, 57), (67, 57)])
    t.brilho(raio, (1.0, 0.85, 0.3), 5, 0.9)
    t.sombra(P.deslocar(raio, 1.0, 2.0), 2.0, 0.5)
    t.volume(raio, OURO, 1.4, 1.0, brilho_borda=0.35)
    t.pintar(np.clip(P.gauss(raio, 1.1) * 1.8 - 0.8, 0, 1), (1, 0.98, 0.85), 0.9)
    faiscas(t, 14, (64, 64), 46, 8, cor)
    return t.reduzir()

def ring_of_fire():
    """Anel de chamas visto de cima: buraco escuro no meio, miolo claro no anel e línguas de fogo para fora."""
    cor = (1.0, 0.4, 0.08)
    t = tela(cor, 56, 0.28, 64, 64)
    cx, cy = 64.0, 64.0
    rng = np.random.default_rng(77)
    r, ang = polar(cx, cy)
    # chão escuro do buraco, com um fio de brasa na borda de dentro
    furo = P.circulo(cx, cy, 25)
    t.pintar(furo, P.rampa(np.clip((r - 6) / 28.0, 0, 1) ** 2.0 * 0.5, [(5, 4, 8), (26, 8, 8), (70, 16, 10)]), 1.0)
    # duas camadas de línguas: as de trás, longas e vermelhas, e as da frente, curtas e claras
    n1 = 18
    for k in range(n1):
        a = k * 360.0 / n1 + rng.uniform(-5, 5)
        m = petala(cx, cy, a, 27, 50 + rng.uniform(-5, 4), 15.0, 18)
        v = np.clip((r - 27) / 24.0, 0, 1)
        t.pintar(m, P.rampa(0.62 - v * 0.55, [(70, 8, 6), (170, 30, 8), (235, 90, 16), (255, 150, 30)]), 1.0)
    for k in range(n1):
        a = k * 360.0 / n1 + 10 + rng.uniform(-4, 4)
        m = petala(cx, cy, a, 27, 42 + rng.uniform(-4, 3), 12.5, 14)
        v = np.clip((r - 27) / 17.0, 0, 1)
        t.pintar(m, P.rampa(0.95 - v * 0.6, [(160, 30, 8), (240, 100, 20), (255, 170, 40), (255, 225, 120), (255, 245, 190)]), 1.0)
    # anel de brasa viva
    anel = ((np.abs(r - 29.5) < 3.4)).astype(np.float32)
    anel = P.gauss(anel, 0.5)
    t.brilho(anel, (1.0, 0.8, 0.3), 4, 0.7)
    t.pintar(anel, P.rampa(0.68 + 0.2 * np.clip(1 - np.abs(r - 29.5) / 3.4, 0, 1), FOGO), 1.0)
    # fio de luz na borda do buraco
    borda = np.exp(-((r - 25.0) / 1.2) ** 2)
    t.somar(borda, (1.0, 0.45, 0.12), 0.8)
    faiscas(t, 15, (64, 64), 50, 16, (1.0, 0.6, 0.15))
    return t.reduzir()

def flame_breath():
    """Cabeça de dragão de perfil com a boca aberta soprando um cone de chamas que se abre para a ponta."""
    cor = (1.0, 0.45, 0.1)
    t = tela(cor, 56, 0.3, 74, 52)
    cx, cy, graus, k = 24.0, 92.0, -28.0, 0.78
    def L(pts):
        return girar_pts(pts, cx, cy, graus, k)
    abertura = 32.0
    gancho = (-4.0, 8.0)
    # pescoço e chifre
    pescoco = P.tubo(L([(-14, 6), (-28, 26), (-44, 46), (-64, 66)]), 30 * k, 40 * k)
    chifre = P.poligono(L([(-6, -28), (-26, -42), (-52, -42), (-36, -32), (-20, -20)]))
    espinhos = [P.poligono(L([(-18 - 9 * i, -22 + 12 * i), (-30 - 9 * i, -32 + 12 * i), (-22 - 9 * i, -12 + 12 * i)])) for i in range(2)]
    crani = P.poligono(L([(-26, 8), (-30, -10), (-20, -26), (-2, -32), (22, -24), (44, -17), (60, -12), (66, -3), (60, 3), (42, 5), (22, 5), (0, 5)]))
    mandi = P.poligono(L(girar_em([(-14, 8), (-10, 20), (6, 26), (34, 24), (54, 16), (58, 9), (40, 11), (14, 10)], gancho[0], gancho[1], abertura)))
    corpo = P.seguir(pescoco, chifre, crani, mandi, *espinhos)
    t.sombra(P.deslocar(corpo, 1.5, 3.0), 3.0, 0.55)
    t.brilho(corpo, (1.0, 0.45, 0.1), 7, 0.22)
    # interior da boca: o vão entre as mandíbulas, aceso pelo fogo
    cant = L([gancho])[0]
    ponta_sup = L([(60, 4)])[0]
    ponta_inf = L(girar_em([(56, 9)], gancho[0], gancho[1], abertura))[0]
    boca = P.poligono([cant, ponta_sup, ponta_inf])
    # pele de escamas: luz do fogo (da frente) somada à luz de cima
    def pele(m, tom=0.0):
        v1 = P.luz_da_forma(m, 2.4, 1.0, luz=(0.85, -0.25, 0.5))
        v2 = P.luz_da_forma(m, 2.4, 1.0)
        v = np.clip(0.55 * v1 + 0.45 * v2 + tom + (P.ruido(5, 6, 3) - 0.5) * 0.18, 0, 1)
        t.pintar(m, P.rampa(v, ESCAMA), 1.0)
        bl = np.clip(P.borda_luz(m, 1.2, luz=(0.9, -0.4)), 0, 1)
        t.somar(bl * m, (1.0, 0.55, 0.2), 0.55)
    pele(np.maximum(pescoco, espinhos[0]))
    pele(espinhos[1], 0.05)
    pele(chifre, 0.12)
    pele(mandi, -0.06)
    t.pintar(boca, (0.2, 0.04, 0.03), 1.0)
    t.somar(P.gauss(boca, 3.0), (1.0, 0.4, 0.08), 0.8)
    pele(crani)
    # dentes
    for x in (16, 28, 40, 52):
        m = P.poligono(L([(x - 3.4, 4), (x + 3.4, 4), (x, 13)]))
        t.pintar(m, P.rampa(0.8, OSSO), 1.0)
    for x in (24, 36, 48):
        m = P.poligono(L(girar_em([(x - 3.2, 11), (x + 3.2, 11), (x, 3)], gancho[0], gancho[1], abertura)))
        t.pintar(m, P.rampa(0.8, OSSO), 1.0)
    # olho, sobrancelha e narina
    olho = P.elipse(*L([(15, -14)])[0], 6.2 * k, 3.8 * k, graus - 16)
    t.brilho(olho, (1.0, 0.8, 0.2), 4, 0.9)
    t.pintar(olho, P.rampa(0.75, [(120, 50, 10), (255, 170, 30), (255, 230, 90), (255, 250, 200)]), 1.0)
    t.pintar(P.elipse(*L([(15, -14)])[0], 1.3 * k, 3.4 * k, graus - 16), (0.05, 0.02, 0.02), 1.0)
    ponto_a, ponto_b = L([(3, -21)])[0], L([(28, -17)])[0]
    t.pintar(P.traco([ponto_a, ponto_b], 3.2 * k), (0.07, 0.03, 0.03), 0.9)
    t.pintar(P.elipse(*L([(54, -6)])[0], 2.6 * k, 1.7 * k, graus), (0.04, 0.02, 0.02), 1.0)
    # cone de fogo saindo da boca: línguas em leque, estreito na boca e largo na ponta
    m0 = (np.array(ponta_sup) + np.array(ponta_inf)) / 2
    eixo = -22.0
    cone_total = np.zeros((W, W), np.float32)
    camadas = []
    for j, dv in enumerate((-31, -21, -11, 0, 11, 21, 31)):
        comp = 62.0 - abs(dv) * 0.5 + (4 if j % 2 else -3)
        m, pos = lingua(m0 + np.array([0.0, (j - 3) * 1.2]), eixo + dv, comp, 15.0, curva=dv * 0.18)
        camadas.append((m, pos, abs(dv)))
        cone_total = np.maximum(cone_total, m)
    t.brilho(cone_total, cor, 7, 0.45)
    rampa_fogo = [(78, 8, 6), (170, 30, 8), (236, 92, 16), (255, 154, 34), (255, 214, 96)]
    for m, pos, dv in sorted(camadas, key=lambda c: -c[2]):
        t.pintar(m, P.rampa(np.clip(1.0 - pos * 0.85 - dv / 90.0 + 0.18, 0, 1), rampa_fogo), 1.0)
    for j, dv in enumerate((-20, -7, 7, 20)):
        m, pos = lingua(m0, eixo + dv, 40.0 - abs(dv) * 0.4, 9.0, curva=dv * 0.1)
        t.pintar(m, P.rampa(np.clip(1.0 - pos * 0.7 + 0.12, 0, 1), [(170, 36, 8), (250, 120, 24), (255, 190, 60), (255, 236, 150), (255, 250, 210)]), 1.0)
    faiscas(t, 13, tuple(m0 + np.array([np.cos(np.radians(eixo)), np.sin(np.radians(eixo))]) * 46), 30, 12, (1.0, 0.6, 0.15))
    return t.reduzir()

def fire_serpent():
    """Serpente de fogo em S, de escamas em brasa, com cabeça de crista, olho aceso e língua bífida, bem recortada no fundo escuro."""
    cor = (1.0, 0.4, 0.08)
    t = tela(cor, 54, 0.26, 64, 64)
    pts = [(24, 100), (40, 107), (62, 104), (80, 93), (88, 78), (80, 64), (62, 58), (48, 50), (46, 36), (58, 26), (74, 24)]
    corpo = tubo_perfil(pts, [(0.0, 3.0), (0.22, 11.0), (0.55, 17.0), (0.85, 14.0), (1.0, 13.0)])
    # cabeça: cunha apontada para a direita, no fim do corpo
    hx, hy = 78.0, 24.0
    def Hd(pp):
        return girar_pts(pp, hx, hy, -4.0, 1.0)
    cabeca = P.poligono(Hd([(-12, -10), (4, -13), (20, -9), (31, -3), (32, 3), (21, 9), (4, 12), (-12, 10)]))
    tudo = P.seguir(corpo, cabeca)
    # crista de chamas que corre para trás da cabeça, por trás dela
    for ang_c, comp_c, larg_c in ((-168, 20, 8.0), (-150, 22, 8.5), (-132, 18, 7.5)):
        m, pos = lingua(Hd([(-6, -7)])[0], ang_c, comp_c, larg_c, curva=-3)
        t.brilho(m, cor, 3, 0.45)
        t.pintar(m, P.rampa(np.clip(0.98 - pos * 0.7, 0, 1), [(150, 28, 8), (240, 100, 18), (255, 170, 44), (255, 228, 120)]), 1.0)
    t.sombra(P.deslocar(tudo, 1.5, 3.0), 3.0, 0.6)
    t.brilho(tudo, cor, 6, 0.32)
    # contorno escuro para recortar a silhueta
    contorno = np.clip(P.gauss(tudo, 1.6) * 3.0 - 0.45, 0, 1)
    t.pintar(contorno, (0.05, 0.01, 0.01), 1.0)
    # corpo em brasa: relevo e uma faixa de luz no dorso
    pos, lado, dist = coord_curva(pts, 160)
    v = P.luz_da_forma(corpo, 3.2, 1.2)
    perfil = np.array([(0.0, 3.0), (0.22, 11.0), (0.55, 17.0), (0.85, 14.0), (1.0, 13.0)])
    meia = np.interp(pos, perfil[:, 0], perfil[:, 1]) / 2.0
    centro = np.clip(1.0 - dist / np.maximum(meia, 1.0), 0, 1) ** 1.3          # dorso quente no eixo, bordas em crosta
    escamas = 0.5 + 0.5 * np.cos(pos * 2 * np.pi * 15.0)
    ruid = (P.ruido(9, 8, 3) - 0.5) * 0.16
    vv = np.clip(0.10 + 0.62 * centro + 0.24 * v - 0.26 * P.degrau(escamas, 0.7, 1.0) + ruid, 0, 1)
    t.pintar(corpo, P.rampa(vv, [(24, 4, 4), (84, 12, 8), (170, 36, 10), (240, 92, 16), (255, 170, 46), (255, 226, 126)]), 1.0)
    # barriga mais clara na parte de dentro das curvas
    barriga = corpo * np.clip(1.0 - dist / 8.0, 0, 1) * (lado > 0)
    t.somar(barriga * 0.0, (1, 0.8, 0.3), 0.0)
    # cabeça
    vc = np.clip(0.2 + P.luz_da_forma(cabeca, 2.2, 1.2) * 0.8 + (P.ruido(10, 6, 3) - 0.5) * 0.1, 0, 1)
    t.pintar(cabeca, P.rampa(vc, [(30, 5, 5), (110, 18, 8), (196, 50, 12), (250, 112, 22), (255, 190, 60)]), 1.0)
    bl = np.clip(P.borda_luz(tudo, 1.1, luz=(-1.0, -1.0)), 0, 1)
    t.somar(bl * tudo, (1.0, 0.8, 0.4), 0.45)
    # olho aceso com pupila de fenda
    ox, oy = Hd([(9, -4.0)])[0]
    olho = P.elipse(ox, oy, 4.6, 3.2, -20)
    t.brilho(olho, (1.0, 0.9, 0.3), 3.5, 0.9)
    t.pintar(olho, P.rampa(0.9, [(160, 90, 10), (255, 210, 60), (255, 244, 170), (255, 255, 235)]), 1.0)
    t.pintar(P.elipse(ox + 0.4, oy, 1.0, 2.6, -20), (0.04, 0.01, 0.01), 1.0)
    # boca e língua bífida
    boca = P.traco(Hd([(4, 5.5), (30, 3.2)]), 1.6)
    t.pintar(boca, (0.08, 0.01, 0.01), 0.9)
    tl = Hd([(30, 3.5), (40, 4.5), (47, 1.0)]), Hd([(40, 4.5), (47, 8.5)])
    for seg in tl:
        m = P.traco(seg, 2.0)
        t.brilho(m, (1.0, 0.3, 0.1), 2.2, 0.6)
        t.pintar(m, (1.0, 0.45, 0.14), 1.0)
    # brasas soltas
    faiscas(t, 21, (64, 64), 48, 16, (1.0, 0.55, 0.12))
    return t.reduzir()

def herald_might():
    """Trompa de guerra de bronze, com o tubo curvo à vista e a campânula larga (40% da altura do ícone), soprando quatro chamas
    pequenas de cores distintas (cinzas, gelo, peste e trovão)."""
    cor = (1.0, 0.75, 0.35)
    t = tela(cor, 54, 0.07, 68, 72)
    pts = [(18, 102), (32, 110), (52, 108), (68, 96), (77, 80), (82, 66)]   # da boquilha à boca
    corpo = trompa(pts, 7.0, 54.0, 2.7)
    # a ponta redonda do último círculo vira uma cúpula: corta o corpo no plano da boca
    corpo = corpo * (((X - 82.0) * 0.28 + (Y - 64.0) * -0.96) <= 6.0)
    contorno = np.clip(P.gauss(corpo, 1.6) * 3.0 - 0.45, 0, 1)
    t.sombra(P.deslocar(corpo, 1.5, 3.0), 3.0, 0.55)
    t.pintar(contorno, (0.05, 0.03, 0.02), 1.0)
    t.volume(corpo, OURO, 3.6, 1.3, brilho_borda=0.4)
    pos, lado, dist = coord_curva(pts, 120)
    # argolas de bronze escuro com fio de luz ao lado: marcam a curva do tubo
    for s0, gr in ((0.08, 0.026), (0.30, 0.022), (0.52, 0.022), (0.72, 0.024), (0.88, 0.020)):
        faixa = corpo * (np.abs(pos - s0) < gr)
        t.pintar(faixa, P.rampa(0.16 + 0.1 * np.clip(-lado, 0, 1), OURO), 0.95)
        fio = corpo * (np.abs(pos - (s0 + gr * 1.5)) < gr * 0.5)
        t.pintar(fio, P.rampa(0.92, OURO), 0.85)
    # boquilha: anel escuro na ponta fina
    bq = P.circulo(18, 102, 4.4)
    t.pintar(bq, (0.07, 0.04, 0.02), 1.0)
    t.pintar(P.anel(18, 102, 4.0, 1.4), P.rampa(0.9, OURO), 0.9)
    # boca: borda de bronze larga e interior escuro aceso por dentro
    cx, cy = 82.0, 64.0
    ang = np.degrees(np.arctan2(-0.96, 0.28)) + 90
    t.pintar(P.elipse(cx, cy, 29.5, 10.5, ang), P.rampa(0.3, OURO), 1.0)
    boca = P.elipse(cx, cy, 26.0, 8.6, ang)
    t.pintar(P.elipse(cx, cy, 28.0, 9.8, ang), P.rampa(0.85, OURO), 1.0)
    dentro = np.clip(1.0 - np.hypot((X - cx) / 26.0, (Y - cy) / 10.0), 0, 1)
    t.pintar(boca, P.rampa(0.06 + 0.7 * dentro, [(16, 6, 3), (60, 22, 6), (150, 70, 20), (236, 150, 50)]), 1.0)
    # quatro chamas menores em fila saindo da boca, uma cor para cada Arauto
    u = np.array([0.28, -0.96])
    v = np.array([0.96, 0.28])
    base_ang = np.degrees(np.arctan2(u[1], u[0]))
    chamas = [(-17.0, -14, CHAMA_LARANJA, (1.0, 0.5, 0.1)), (-6.0, -5, CHAMA_GELO, (0.5, 0.85, 1.0)),
              (6.0, 5, CHAMA_VENENO, (0.35, 1.0, 0.2)), (17.0, 14, CHAMA_RAIO, (0.5, 0.45, 1.0))]
    for d, dang, paleta, bril in chamas:
        b = np.array([cx, cy]) + v * d - u * 1.0
        chama_pequena(t, tuple(b), base_ang + dang, 28.0, 10.0, paleta, bril)
    faiscas(t, 64, (80, 34), 22, 5, cor)
    return t.reduzir()


GLIFOS = {
    "toxic_tornado": toxic_tornado,
    "ice_comet": ice_comet,
    "frost_nova": frost_nova,
    "fire_serpent": fire_serpent,
    "lightning_rod": lightning_rod,
    "thunder_burst": thunder_burst,
    "sky_storm": sky_storm,
    "storm_orbs": storm_orbs,
    "plague_spread": plague_spread,
    "toxic_mines": toxic_mines,
    "acid_geyser": acid_geyser,
    "icicle_lance": icicle_lance,
    "ice_spikes": ice_spikes,
    "blizzard": blizzard,
    "flame_breath": flame_breath,
    "ring_of_fire": ring_of_fire,
    "fuse_bomb": fuse_bomb,
    "ember_tip": ember_tip,
    "wide_reach": wide_reach,
    "extra_shot": extra_shot,
    "swift_shots": swift_shots,
    "lingering": lingering,
    "piercing_skills": piercing_skills,
    "flame_lore": flame_lore,
    "frost_lore": frost_lore,
    "storm_lore": storm_lore,
    "venom_lore": venom_lore,
    "herald_might": herald_might,
    "keen_eye": keen_eye,
    "deadly_aim": deadly_aim,
    "focus": focus,
    "eco_trovao": eco_trovao,
    "eco_peste": eco_peste,
    "eco_gelo": eco_gelo,
    "eco_cinzas": eco_cinzas,
}
