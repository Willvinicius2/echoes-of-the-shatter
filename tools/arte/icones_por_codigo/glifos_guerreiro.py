"""Ícones do Guerreiro desenhados por código: as 8 habilidades elementais e os 4 Ecos do golpe básico.

Mesma receita dos ícones do Arqueiro (`glifos.py`), com a espada no lugar da flecha: cada função devolve o miolo
128 x 128 x 3 (0..1). Uso: python3 tools/arte/icones_por_codigo/gerar.py --receitas glifos_guerreiro --jogo
"""
import numpy as np

import pintura as P
from pintura import X, Y
import glifos as G
from glifos import FOGO, GELO, VENENO, RAIO, FERRO, MADEIRA, OURO, PEDRA, tela, faiscas

ACO_RAIO = [(10, 14, 44), (44, 62, 160), (118, 158, 244), (226, 238, 255), (255, 255, 255)]
ACO_GELO = [(8, 22, 48), (46, 104, 168), (136, 206, 248), (232, 248, 255), (255, 255, 255)]
ACO_PESTE = [(8, 26, 8), (34, 92, 22), (92, 172, 44), (178, 236, 90), (240, 255, 190)]
ACO_BRASA = [(16, 6, 6), (84, 30, 16), (176, 84, 30), (240, 160, 70), (255, 232, 170)]


def espada(t, p0, p1, larg=11.0, rampa=None, brilho_cor=None, guarda=OURO, cabo=MADEIRA):
    """Espada reta de p0 (pomo) a p1 (ponta): cabo, guarda em cruz e lâmina de dois gumes com fio de luz. Devolve a máscara."""
    rampa = rampa or FERRO
    a = np.array(p0, float)
    b = np.array(p1, float)
    u = (b - a) / np.linalg.norm(b - a)
    n = np.array([-u[1], u[0]])
    comp = float(np.linalg.norm(b - a))
    g = a + u * comp * 0.24                      # centro da guarda
    base = g + u * 3
    ombro = b - u * larg * 1.5
    lamina = P.poligono([tuple(base + n * larg / 2), tuple(ombro + n * larg / 2), tuple(b), tuple(ombro - n * larg / 2), tuple(base - n * larg / 2)])
    if brilho_cor is not None:
        t.brilho(lamina, brilho_cor, 5, 0.6)
    lado = ((X - a[0]) * n[0] + (Y - a[1]) * n[1]) / (larg / 2)
    v = np.where(lado < 0, 0.80 - 0.18 * (lado + 1), 0.46 - 0.22 * lado)
    v = np.clip(v + P.degrau(1 - np.abs(lado), 0.80, 1.0) * 0.22, 0, 1)
    t.pintar(lamina, P.rampa(v, rampa), 1.0)
    t.somar(P.borda_luz(lamina).clip(0, 1) * lamina, (1, 1, 1), 0.45)
    cabo_m = P.traco([tuple(a + u * 4), tuple(g)], larg * 0.42)
    t.volume(cabo_m, cabo, 1.4, 1.0)
    guarda_m = P.traco([tuple(g + n * larg * 1.25), tuple(g - n * larg * 1.25)], larg * 0.5)
    t.volume(guarda_m, guarda, 1.4, 1.0, brilho_borda=0.4)
    pomo = P.circulo(a[0] + u[0] * 2, a[1] + u[1] * 2, larg * 0.36)
    t.volume(pomo, guarda, 1.2, 1.0)
    return P.seguir(lamina, cabo_m, guarda_m, pomo)


def arco_corte(t, cx, cy, r, a0, a1, larg, rampa, cor, semente=1):
    """Rastro de corte: meia-lua que afina nas pontas, com miolo claro."""
    angs = np.radians(np.linspace(a0, a1, 14))
    pts = [(cx + np.cos(a) * r, cy + np.sin(a) * r) for a in angs]
    meio = len(pts) // 2
    m = P.seguir(P.tubo(pts[:meio + 1], 1.5, larg), P.tubo(pts[meio:], larg, 1.5))
    t.brilho(m, cor, 5, 0.7)
    t.pintar(m, P.rampa(0.45 + 0.4 * P.ruido(semente, 10, 3), rampa), 0.95)
    t.pintar(np.clip(P.gauss(m, 1.2) * 1.8 - 0.9, 0, 1), P.rampa(0.95, rampa), 0.9)
    return m


# --- Ecos do golpe básico ---------------------------------------------------------------------------------------

def eco_w_trovao():
    cor = (0.5, 0.7, 1.0)
    t = tela(cor, 54, 0.45)
    p0, p1 = (24, 104), (102, 26)
    t.brilho(P.tubo([p0, p1], 18, 18), cor, 7, 0.45)
    espada(t, p0, p1, 12, ACO_RAIO, cor)
    for k, off in enumerate((-14, 14)):
        pts = G.relampago_simples((p0[0] + 26 + off * 0.7, p0[1] - 26 + off * 0.7), (p1[0] - 8 + off * 0.7, p1[1] + 8 + off * 0.7), 60 + k, desvio=10, niveis=3)
        G.pintar_raio(t, P.traco(pts, 3.2), cor, raio_brilho=3.2, forca=0.95)
    G.pintar_raio(t, G.relampago(p1, (118, 8), 5, desvio=4, niveis=2, ramos=1, largura=3.2), cor, raio_brilho=3.4)
    faiscas(t, 61, (64, 64), 46, 12, cor)
    return t.reduzir()


def eco_w_peste():
    cor = (0.35, 1.0, 0.2)
    t = tela(cor, 54, 0.42)
    p0, p1 = (24, 104), (102, 26)
    nuv = P.ruido(15, (18, 18), 4)
    f = P.deformar(P.gauss(P.tubo([p0, p1], 26, 26), 4), (nuv - 0.5) * 16, (P.ruido(16, (18, 18), 4) - 0.5) * 16)
    t.pintar(np.clip(f * 1.3 - 0.25, 0, 1), P.rampa(0.35 + 0.5 * nuv, VENENO), 0.5)
    espada(t, p0, p1, 12, ACO_PESTE, cor, guarda=[(20, 30, 10), (60, 80, 24), (120, 140, 50), (190, 200, 100)])
    for (x, y, r) in [(92, 50, 4.4), (76, 68, 3.4), (104, 66, 3.0), (58, 90, 3.4)]:
        gg = G.gota(x, y + 2, r)
        t.brilho(gg, cor, 3, 0.8)
        t.pintar(gg, P.rampa(0.75, VENENO), 1.0)
        t.pintar(P.circulo(x - r * 0.3, y + 1, r * 0.3), (1, 1, 0.9), 0.8)
    faiscas(t, 62, (64, 64), 46, 8, cor)
    return t.reduzir()


def eco_w_gelo():
    cor = (0.5, 0.85, 1.0)
    t = tela(cor, 54, 0.45)
    p0, p1 = (24, 104), (102, 26)
    espada(t, p0, p1, 12, ACO_GELO, cor, guarda=[(14, 40, 80), (60, 120, 180), (150, 210, 245), (240, 250, 255)])
    for (x0, y0, x1, y1, w) in [(72, 52, 62, 30, 8), (56, 72, 36, 66, 8), (86, 66, 106, 76, 8), (70, 84, 78, 104, 7)]:
        G.cristal(t, (x0, y0), (x1, y1), w)
    fl = G.floco(96, 98, 11, 1.5, 1)
    t.brilho(fl, cor, 3, 0.7)
    t.pintar(fl, (0.95, 1, 1), 0.95)
    faiscas(t, 63, (64, 64), 46, 14, cor)
    return t.reduzir()


def eco_w_cinzas():
    cor = (1.0, 0.5, 0.1)
    t = tela(cor, 54, 0.45)
    p0, p1 = (24, 104), (102, 26)
    G.pintar_fogo(t, P.tubo([(50, 78), (98, 30)], 12, 15), 18, ganho=0.8, subida=20, vento=6, passos=4, periodo=(14, 22), fluxo=(-0.8, 0.8))
    espada(t, p0, p1, 12, ACO_BRASA, cor, guarda=FERRO)
    G.pintar_fogo(t, P.poligono([(102, 26), (88, 36), (94, 48)]), 19, ganho=0.9, subida=10, vento=4, passos=3)
    rng = np.random.default_rng(41)
    for _ in range(16):
        x, y = rng.uniform(20, 108), rng.uniform(44, 112)
        t.pintar(P.circulo(x, y, rng.uniform(0.9, 1.8)), P.rampa(rng.uniform(0.4, 0.9), PEDRA), 0.9)
    faiscas(t, 64, (64, 64), 46, 14, cor)
    return t.reduzir()


# --- habilidades elementais -------------------------------------------------------------------------------------

def w_thunder_strike():
    """Golpe do Trovão: a espada cravada de ponta para baixo com um raio descendo do céu sobre ela e o chão rachado."""
    cor = (0.5, 0.68, 1.0)
    t = tela(cor, 56, 0.5, 64, 70)
    chao = P.elipse(64, 104, 44, 9)
    t.brilho(chao, cor, 6, 0.6)
    t.pintar(chao, P.rampa(0.3 + 0.4 * P.ruido(71, 8, 3), RAIO), 0.85)
    for k in range(6):
        a = np.radians(k * 60 + 15)
        r = G.relampago((64, 104), (64 + np.cos(a) * 48, 104 + np.sin(a) * 9), 72 + k, desvio=4, niveis=2, ramos=0, largura=2.0)
        G.pintar_raio(t, r, cor, raio_brilho=2.4, forca=0.7)
    espada(t, (64, 40), (64, 104), 13, ACO_RAIO, cor)
    G.pintar_raio(t, G.relampago((48, 8), (64, 40), 79, desvio=10, niveis=3, ramos=2, largura=4.4), cor, raio_brilho=4.0)
    faiscas(t, 70, (64, 70), 50, 14, cor)
    return t.reduzir()


def w_storm_blades():
    """Lâminas da Tempestade: três lâminas girando em órbita, ligadas por um anel de raio."""
    cor = (0.5, 0.7, 1.0)
    t = tela(cor, 56, 0.45)
    anel = P.anel(64, 64, 36, 2.6)
    f = P.deformar(anel, (P.ruido(81, 9, 2) - 0.5) * 9, (P.ruido(82, 9, 2) - 0.5) * 9)
    G.pintar_raio(t, f, cor, raio_brilho=3.0, forca=0.8)
    for k in range(3):
        a = np.radians(k * 120 - 90)
        c = np.array([64 + np.cos(a) * 36, 64 + np.sin(a) * 36])
        tg = np.array([-np.sin(a), np.cos(a)])
        espada(t, tuple(c - tg * 30), tuple(c + tg * 30), 13, ACO_RAIO, cor)
    t.brilho(P.circulo(64, 64, 6), (0.7, 0.85, 1.0), 9, 0.9)
    G.esfera(t, 64, 64, 7, [(24, 36, 150), (90, 130, 250), (210, 228, 255), (255, 255, 255)])
    faiscas(t, 80, (64, 64), 52, 12, cor)
    return t.reduzir()


def w_flame_wave():
    """Onda Flamejante: meia-lua de fogo avançando do corte, com a lâmina atrás."""
    cor = (1.0, 0.5, 0.1)
    t = tela(cor, 56, 0.45, 70, 60)
    espada(t, (12, 116), (52, 76), 11, FERRO, cor)
    angs = np.radians(np.linspace(-95, 25, 16))
    pts = [(26 + np.cos(a) * 70, 102 + np.sin(a) * 70) for a in angs]
    meio = len(pts) // 2
    m = P.seguir(P.tubo(pts[:meio + 1], 2, 15), P.tubo(pts[meio:], 15, 2))
    G.pintar_fogo(t, m, 91, ganho=0.72, subida=14, vento=5, passos=4, periodo=(12, 22), fluxo=(-0.7, 0.7))
    arco_corte(t, 26, 102, 70, -92, 22, 9, FOGO, cor, 92)
    arco_corte(t, 26, 102, 46, -80, 10, 6, FOGO, cor, 93)
    faiscas(t, 90, (72, 56), 46, 16, cor)
    return t.reduzir()


def w_eruption():
    """Erupção: fenda no chão com três pilares de fogo subindo e pedras lançadas."""
    cor = (1.0, 0.48, 0.1)
    t = tela(cor, 56, 0.5, 64, 80)
    chao = P.elipse(64, 106, 50, 10)
    t.pintar(chao, P.rampa(0.25 + 0.4 * P.ruido(101, 8, 3), PEDRA), 0.95)
    fenda = P.traco([(22, 108), (44, 103), (64, 108), (86, 102), (106, 107)], 4.5)
    t.brilho(fenda, cor, 5, 0.9)
    t.pintar(fenda, P.rampa(0.85, FOGO), 1.0)
    for k, (x, h, w) in enumerate([(34, 44, 12), (94, 48, 12), (64, 80, 17)]):
        pilar = P.tubo([(x, 106), (x, 106 - h * 0.5), (x, 106 - h)], w, w * 0.35)
        G.pintar_fogo(t, pilar, 102 + k, ganho=0.7, subida=14, vento=4, passos=3, periodo=(12, 26))
    rng = np.random.default_rng(104)
    for _ in range(9):
        x, y, r = rng.uniform(18, 110), rng.uniform(28, 84), rng.uniform(2.2, 4.4)
        ped = P.elipse(x, y, r, r * 0.8, rng.uniform(0, 90), 7)
        t.volume(ped, PEDRA, 1.0, 1.0)
    faiscas(t, 100, (64, 60), 50, 14, cor)
    return t.reduzir()


def w_glacial_plant():
    """Cravar Gélido: a espada fincada no chão com uma coroa de cristais de gelo brotando em volta."""
    cor = (0.5, 0.84, 1.0)
    t = tela(cor, 56, 0.45, 64, 74)
    chao = P.elipse(64, 106, 52, 10)
    t.brilho(chao, cor, 6, 0.6)
    t.pintar(chao, P.rampa(0.35 + 0.4 * P.ruido(111, 8, 3), GELO), 0.9)
    for (bx, by, px, py, w) in [(26, 106, 12, 66, 13), (102, 106, 116, 66, 13), (40, 108, 30, 52, 14), (88, 108, 98, 52, 14)]:
        G.cristal(t, (bx, by), (px, py), w, brilho_cor=cor)
    espada(t, (64, 14), (64, 106), 14, ACO_GELO, cor, guarda=[(14, 40, 80), (60, 120, 180), (150, 210, 245), (240, 250, 255)])
    for (bx, by, px, py, w) in [(52, 110, 46, 82, 11), (76, 110, 82, 82, 11)]:
        G.cristal(t, (bx, by), (px, py), w)
    faiscas(t, 110, (64, 60), 48, 14, cor)
    return t.reduzir()


def w_frost_shield():
    """Escudo de Geada: escudo redondo coberto de gelo, com floco no centro e rastro de arremesso."""
    cor = (0.5, 0.84, 1.0)
    t = tela(cor, 56, 0.45)
    for k, r in enumerate((54, 46)):
        arco_corte(t, 64, 64, r, 150 + k * 20, 250 + k * 20, 7 - k * 2, GELO, cor, 121 + k)
        arco_corte(t, 64, 64, r, -30 + k * 20, 70 + k * 20, 7 - k * 2, GELO, cor, 123 + k)
    disco = P.circulo(64, 64, 34)
    t.brilho(disco, cor, 6, 0.6)
    G.esfera(t, 64, 64, 34, [(8, 24, 56), (36, 90, 156), (110, 184, 236), (216, 242, 255)], brilho=0.6)
    aro = P.anel(64, 64, 31, 5.5)
    t.volume(aro, [(20, 44, 84), (80, 140, 200), (180, 226, 250), (250, 254, 255)], 1.4, 1.0, brilho_borda=0.4)
    fl = G.floco(64, 64, 19, 2.6, 2)
    t.brilho(fl, cor, 3, 0.8)
    t.pintar(fl, (0.97, 1, 1), 1.0)
    for k in range(4):
        a = np.radians(k * 90 + 45)
        G.cristal(t, (64 + np.cos(a) * 30, 64 + np.sin(a) * 30), (64 + np.cos(a) * 52, 64 + np.sin(a) * 52), 9)
    faiscas(t, 120, (64, 64), 52, 12, cor)
    return t.reduzir()


def w_venom_cleave():
    """Talho Pestilento: corte largo em meia-lua verde pingando veneno, com a lâmina no fim do giro."""
    cor = (0.4, 1.0, 0.2)
    t = tela(cor, 56, 0.42)
    arco_corte(t, 64, 70, 44, 185, 345, 20, VENENO, cor, 131)
    arco_corte(t, 64, 70, 28, 200, 330, 8, VENENO, cor, 132)
    espada(t, (56, 108), (112, 60), 11, ACO_PESTE, cor, guarda=[(20, 30, 10), (60, 80, 24), (120, 140, 50), (190, 200, 100)])
    for (x, y, r) in [(26, 66, 4.6), (44, 44, 3.6), (70, 34, 4.2), (94, 40, 3.2), (36, 88, 3.2)]:
        gg = G.gota(x, y + 4, r)
        t.brilho(gg, cor, 3, 0.8)
        t.pintar(gg, P.rampa(0.78, VENENO), 1.0)
        t.pintar(P.circulo(x - r * 0.3, y + 3, r * 0.3), (1, 1, 0.9), 0.8)
    faiscas(t, 130, (64, 64), 48, 8, cor)
    return t.reduzir()


def w_plague_banner():
    """Estandarte da Peste: mastro fincado com bandeira rasgada verde e miasma subindo da base."""
    cor = (0.4, 1.0, 0.2)
    t = tela(cor, 56, 0.42, 64, 70)
    chao = P.elipse(60, 108, 46, 9)
    t.brilho(chao, cor, 7, 0.7)
    t.pintar(chao, P.rampa(0.3 + 0.45 * P.ruido(141, 8, 3), VENENO), 0.85)
    nuv = P.ruido(142, (16, 20), 4)
    miasma = P.deformar(P.gauss(P.elipse(60, 96, 44, 16), 4), (nuv - 0.5) * 18, (P.ruido(143, (16, 20), 4) - 0.5) * 18)
    t.pintar(np.clip(miasma * 1.3 - 0.3, 0, 1), P.rampa(0.3 + 0.5 * nuv, VENENO), 0.5)
    pano = P.poligono([(44, 22), (104, 28), (94, 44), (106, 58), (90, 66), (98, 82), (76, 74), (62, 88), (44, 76)])
    onda = (P.ruido(144, (22, 40), 2) - 0.5) * 8
    pano = P.deformar(pano, onda, onda * 0.5)
    t.brilho(pano, cor, 5, 0.5)
    t.volume(pano, [(8, 30, 10), (26, 84, 22), (60, 146, 36), (130, 210, 60)], 3.2, 1.2, ruido_arr=P.ruido(145, 10, 3), brilho_borda=0.3)
    cav = P.seguir(P.circulo(70, 46, 10), P.poligono([(63, 50), (77, 50), (74, 62), (66, 62)]))
    t.pintar(cav, P.rampa(0.92, VENENO), 0.95)
    for (x, y) in [(66, 45), (74, 45)]:
        t.pintar(P.circulo(x, y, 2.6), (0.03, 0.12, 0.03), 1.0)
    mastro = P.traco([(42, 12), (42, 110)], 5.5)
    t.volume(mastro, MADEIRA, 1.4, 1.0)
    ponta = P.poligono([(42, 2), (48, 14), (36, 14)])
    t.volume(ponta, FERRO, 1.2, 1.0)
    faiscas(t, 140, (64, 64), 48, 8, cor)
    return t.reduzir()


GLIFOS = {
    "eco_w_trovao": eco_w_trovao,
    "eco_w_peste": eco_w_peste,
    "eco_w_gelo": eco_w_gelo,
    "eco_w_cinzas": eco_w_cinzas,
    "w_thunder_strike": w_thunder_strike,
    "w_storm_blades": w_storm_blades,
    "w_flame_wave": w_flame_wave,
    "w_eruption": w_eruption,
    "w_glacial_plant": w_glacial_plant,
    "w_frost_shield": w_frost_shield,
    "w_venom_cleave": w_venom_cleave,
    "w_plague_banner": w_plague_banner,
}
