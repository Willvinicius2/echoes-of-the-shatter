"""Ícones do Mago, desenhados por código com as mesmas peças dos ícones do Arqueiro (`glifos.py`).

Só os que faltavam: o golpe básico, as três magias de veneno e os quatro Ecos (godot/data2d/afinidades_mago.csv).
As outras magias da árvore já têm ícone pintado em art-src/ui/icones_pintados (não regravar) e os Arautos usam os
ícones que o Arqueiro já tem. O Mago não tem flecha: os desenhos são orbes, cristais, raios, nuvens e chamas.

Uso: python3 tools/arte/icones_por_codigo/gerar.py --receitas glifos_mago --jogo [--folha arquivo.png]
"""
import numpy as np

import pintura as P
import glifos as G
from glifos import FOGO, VENENO, RAIO, PEDRA, ROXO, FERRO, tela

AMARELO = [(30, 30, 6), (110, 110, 14), (186, 184, 36), (236, 226, 88), (255, 250, 168)]
OSSO_C = [(40, 30, 22), (120, 100, 78), (196, 176, 140), (240, 228, 196)]
FERRO_C = [(20, 20, 26), (70, 70, 84), (140, 138, 150), (214, 208, 204)]
C_FOGO = (1.0, 0.5, 0.1)
C_GELO = (0.5, 0.85, 1.0)
C_RAIO = (0.5, 0.65, 1.0)
C_VENENO = (0.35, 1.0, 0.2)
C_ARCANO = (0.65, 0.4, 1.0)
R_FOGO = [(60, 10, 4), (200, 60, 12), (255, 170, 50), (255, 246, 200)]
R_GELO = [(20, 60, 120), (80, 160, 220), (200, 236, 255), (255, 255, 255)]
R_RAIO = [(24, 36, 150), (90, 130, 250), (210, 228, 255), (255, 255, 255)]
R_VENENO = [(10, 50, 8), (50, 140, 24), (150, 226, 60), (236, 255, 180)]
R_ARCANO = [(30, 12, 80), (104, 50, 190), (176, 124, 246), (240, 222, 255)]


def _cometa(t, cx, cy, r, cauda, rampa, semente, paleta=FOGO):
    """Esfera com cauda de fogo: `cauda` é o vetor da cauda (para onde o fogo fica para trás)."""
    del paleta
    ox, oy = (P.ruido(semente, (10, 16), 3) - 0.5) * 9, (P.ruido(semente + 1, (10, 16), 3) - 0.5) * 9
    camadas = [(1.0, 2.5, 0.16, 1.0), (0.78, 1.9, 0.42, 1.0), (0.56, 1.3, 0.72, 1.0), (0.34, 0.75, 0.94, 0.9)]
    for comp, larg, tom, alfa in camadas:   # do vermelho largo e comprido ao amarelo curto, junto da cabeça
        fim = (cx + cauda[0] * comp, cy + cauda[1] * comp)
        lingua = np.clip(P.deformar(P.tubo([(cx, cy), fim], r * larg, 1.5), ox * comp, oy * comp), 0, 1)
        if tom < 0.2:
            t.brilho(lingua, C_FOGO, 6, 0.5)
        t.pintar(lingua, P.rampa(tom, FOGO), alfa)
    G.esfera(t, cx, cy, r, rampa)


def basic():
    t = tela(C_ARCANO, 52, 0.5, 70, 58)
    for k, (x, y, r) in enumerate([(26, 102, 3.0), (38, 90, 4.4), (50, 78, 5.8)]):   # rastro
        m = P.circulo(x, y, r)
        t.brilho(m, C_ARCANO, 4, 0.7)
        t.pintar(m, P.rampa(0.45 + 0.15 * k, ROXO), 0.9)
    t.brilho(P.circulo(76, 52, 24), C_ARCANO, 10, 0.8)
    G.esfera(t, 76, 52, 24, R_ARCANO)
    t.somar(P.anel(76, 52, 31, 1.6), C_ARCANO, 0.6)
    G.faiscas(t, 301, (76, 52), 46, 12, C_ARCANO)
    return t.reduzir()


def _nuvem(t, cx, cy, largura, semente, paleta, alfa=0.95):
    rng = np.random.default_rng(semente)
    partes = [P.elipse(cx, cy + 4, largura * 0.5, 13)]
    for k in range(6):
        x = cx + (k - 2.5) * largura / 6 + rng.uniform(-3, 3)
        partes.append(P.circulo(x, cy - rng.uniform(0, 9), rng.uniform(12, 19) * (1.0 - abs(k - 2.5) * 0.1)))
    cum = np.clip(P.seguir(*partes), 0, 1)
    luz = P.luz_da_forma(np.clip(P.gauss(cum, 2), 0, 1), 4.0)
    t.sombra(cum, 5, 0.5)
    t.pintar(cum, P.rampa(np.clip(0.2 + luz * 0.6 + (P.ruido(semente, (16, 12), 4) - 0.5) * 0.3, 0, 1), paleta), alfa)
    t.somar(P.borda_luz(cum).clip(0, 1) * cum, (0.85, 1.0, 0.6), 0.5)
    return cum


def plague_cloud():
    """Nuvem amarelo-esverdeada com caveira no miolo: lê como peste mesmo ao lado do cogumelo e da poça."""
    t = tela((0.8, 0.9, 0.2), 56, 0.45, 64, 60)
    _nuvem(t, 62, 80, 92, 491, AMARELO[:4], 0.85)
    _nuvem(t, 66, 50, 100, 492, AMARELO)
    cr = P.seguir(P.circulo(64, 52, 20), P.elipse(64, 70, 13, 9))
    t.sombra(cr, 3, 0.5)
    t.pintar(cr, P.rampa(0.88, OSSO_C), 1.0)
    for ox in (-8, 8):
        t.pintar(P.circulo(64 + ox, 52, 5.6), (0.08, 0.06, 0.02), 1.0)
    t.pintar(P.poligono([(64, 58), (60, 65), (68, 65)]), (0.08, 0.06, 0.02), 1.0)
    for ox in (-6, -2, 2, 6):
        t.pintar(P.tubo([(64 + ox, 66), (64 + ox, 74)], 1.4, 1.4), (0.08, 0.06, 0.02), 1.0)
    G.faiscas(t, 493, (64, 60), 50, 8, (0.8, 0.9, 0.2))
    return t.reduzir()


def spore_mark():
    t = tela(C_VENENO, 54, 0.42, 64, 60)
    cabo = P.tubo([(64, 108), (62, 62)], 15, 10)
    t.volume(cabo, [(30, 40, 20), (110, 130, 80), (200, 214, 150), (244, 250, 214)], 2.4, 1.0)
    chapeu = np.clip(P.elipse(64, 58, 44, 30) - P.elipse(64, 80, 54, 20), 0, 1)
    t.sombra(chapeu, 4, 0.5)
    t.volume(chapeu, [(40, 10, 40), (104, 30, 96), (170, 70, 150), (232, 150, 214)], 3.4, 1.1, brilho_borda=0.3)
    for (x, y, r) in [(46, 48, 6), (70, 40, 7.5), (88, 54, 5), (60, 58, 3.5)]:
        m = P.circulo(x, y, r) * chapeu
        t.brilho(m, C_VENENO, 3, 0.7)
        t.pintar(m, P.rampa(0.85, VENENO), 1.0)
    G.faiscas(t, 501, (64, 34), 48, 16, C_VENENO, tam=(1.2, 2.4))
    return t.reduzir()


def acid_pool():
    """Tonel de ferro virado derramando ácido numa poça sobre pedra escura: a silhueta de objeto separa do cogumelo e da nuvem."""
    t = tela(C_VENENO, 50, 0.3, 64, 78)
    chao = P.elipse(64, 100, 56, 18)
    t.pintar(chao, P.rampa(0.2 + 0.25 * P.ruido(511, 9, 3), PEDRA), 1.0)
    poca = P.elipse(70, 100, 44, 13)
    t.brilho(poca, C_VENENO, 6, 0.6)
    t.pintar(poca, P.rampa(0.5 + 0.4 * P.ruido(514, (26, 10), 4), VENENO), 1.0)
    jato = P.tubo([(46, 62), (50, 80), (58, 98)], 9, 6)
    t.pintar(jato, P.rampa(0.8, VENENO), 1.0)
    tonel = P.poligono([(10, 56), (22, 28), (60, 20), (76, 46), (62, 74), (24, 82)])
    t.sombra(tonel, 4, 0.5)
    t.volume(tonel, [(14, 12, 10), (60, 36, 22), (116, 74, 40), (190, 130, 70)], 3.0, 1.0)
    for (a, b) in [((20, 32), (14, 74)), ((38, 24), (36, 80)), ((62, 22), (66, 70))]:
        t.volume(P.tubo([a, b], 4.2, 4.2), FERRO_C, 1.4, 1.0)
    boca = P.elipse(14, 66, 8, 13, 10)
    t.pintar(boca, (0.04, 0.12, 0.03), 1.0)
    t.pintar(P.anel(14, 66, 9, 1.8), P.rampa(0.8, FERRO_C), 1.0)
    for (x, y, r) in [(84, 94, 5), (100, 98, 4)]:
        G.esfera(t, x, y, r, R_VENENO, alfa=0.95)
    G.faiscas(t, 515, (64, 64), 50, 6, C_VENENO)
    return t.reduzir()


def eco_m_trovao():
    t = tela(C_RAIO, 54, 0.5, 64, 64)
    cruz = np.maximum(P.tubo([(64, 14), (64, 114)], 9, 9), P.tubo([(14, 64), (114, 64)], 9, 9))
    cruz = np.maximum(cruz, np.maximum(P.tubo([(38, 38), (90, 90)], 6, 6), P.tubo([(90, 38), (38, 90)], 6, 6)))
    pontas = cruz * np.clip(1.25 - np.hypot(P.X - 64, P.Y - 64) / 44.0, 0, 1)
    t.brilho(pontas, C_RAIO, 7, 1.0)
    t.pintar(np.clip(P.gauss(pontas, 1.2) * 1.8, 0, 1), P.rampa(0.8, RAIO), 1.0)
    for k in range(4):
        a = np.radians(k * 90 + 45)
        r = G.relampago((64 + np.cos(a) * 20, 64 + np.sin(a) * 20), (64 + np.cos(a) * 54, 64 + np.sin(a) * 54), 521 + k, desvio=7, ramos=1, largura=2.6)
        G.pintar_raio(t, r, C_RAIO, raio_brilho=3.0)
    t.brilho(P.circulo(64, 64, 13), (0.8, 0.9, 1.0), 10, 1.0)
    G.esfera(t, 64, 64, 13, R_RAIO)
    G.faiscas(t, 525, (64, 64), 50, 12, C_RAIO)
    return t.reduzir()


def eco_m_peste():
    """Frasco de vidro com veneno e fumaça roxa saindo do gargalo: não se confunde com o orbe do golpe básico."""
    t = tela(C_VENENO, 50, 0.4, 64, 74)
    for k, (x, y, r) in enumerate([(64, 30, 16), (50, 20, 13), (80, 16, 12), (66, 6, 10)]):   # fumaça roxa
        f = P.circulo(x, y, r)
        t.pintar(f, P.rampa(0.35 + 0.15 * k, ROXO), 0.9)
        t.somar(P.borda_luz(f).clip(0, 1) * f, (0.7, 0.5, 1.0), 0.4)
    vidro = P.seguir(P.circulo(64, 84, 32), P.tubo([(64, 62), (64, 40)], 15, 11))
    t.sombra(vidro, 4, 0.5)
    t.pintar(vidro, (0.08, 0.2, 0.18), 0.95)
    liquido = vidro * (P.Y > 78)
    t.volume(liquido, VENENO, 2.6, 1.0, brilho_borda=0.3)
    t.somar(P.borda_luz(vidro).clip(0, 1) * vidro, (0.8, 1.0, 0.9), 0.7)
    t.pintar(P.elipse(50, 74, 3.5, 9, 10), (0.9, 1.0, 0.95), 0.7)
    rolha = P.poligono([(54, 40), (74, 40), (72, 31), (56, 31)])
    t.volume(rolha, [(30, 16, 8), (90, 54, 26), (150, 100, 50), (200, 150, 86)], 1.4, 1.0)
    for (x, y, r) in [(54, 92, 3.0), (72, 98, 2.4), (62, 86, 2.0)]:
        t.pintar(P.anel(x, y, r, 1.0), P.rampa(0.95, VENENO), 0.9)
    G.faiscas(t, 531, (64, 40), 44, 6, C_ARCANO)
    return t.reduzir()


def eco_m_gelo():
    t = tela(C_GELO, 54, 0.45, 64, 64)
    for (ang, comp, larg) in [(-72, 80, 15), (-45, 92, 17), (-18, 80, 15)]:
        a = np.radians(ang)
        G.cristal(t, (22, 106), (22 + np.cos(a) * comp, 106 + np.sin(a) * comp), larg, brilho_cor=C_GELO)
    t.brilho(P.circulo(22, 106, 8), C_GELO, 6, 0.9)
    G.esfera(t, 22, 106, 8, R_GELO)
    fl = G.floco(98, 98, 12, 1.6, 1)
    t.brilho(fl, C_GELO, 3, 0.7)
    t.pintar(fl, (0.95, 1, 1), 0.95)
    G.faiscas(t, 541, (64, 64), 48, 12, C_GELO)
    return t.reduzir()


def eco_m_cinzas():
    t = tela(C_FOGO, 54, 0.45, 70, 58)
    _cometa(t, 84, 44, 15, (-58, 58), R_FOGO, 551)
    rng = np.random.default_rng(552)
    for _ in range(16):
        x, y = rng.uniform(16, 80), rng.uniform(60, 114)
        t.pintar(P.circulo(x, y, rng.uniform(1.0, 2.0)), P.rampa(rng.uniform(0.4, 0.9), PEDRA), 0.9)
    G.faiscas(t, 553, (60, 70), 44, 12, C_FOGO)
    return t.reduzir()


GLIFOS = {
    "skill.mage.basic": basic,
    "skill.mage.plague_cloud": plague_cloud,
    "skill.mage.spore_mark": spore_mark,
    "skill.mage.acid_pool": acid_pool,
    "eco_m_trovao": eco_m_trovao,
    "eco_m_peste": eco_m_peste,
    "eco_m_gelo": eco_m_gelo,
    "eco_m_cinzas": eco_m_cinzas,
}
