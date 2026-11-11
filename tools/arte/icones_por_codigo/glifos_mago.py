"""Ícones do Mago, desenhados por código com as mesmas peças dos ícones do Arqueiro (`glifos.py`).

Só os que faltavam: o golpe básico, as três magias de veneno e os quatro Ecos (godot/data2d/afinidades_mago.csv).
As outras magias da árvore já têm ícone pintado em art-src/ui/icones_pintados (não regravar) e os Arautos usam os
ícones que o Arqueiro já tem. O Mago não tem flecha: os desenhos são orbes, cristais, raios, nuvens e chamas.

Uso: python3 tools/arte/icones_por_codigo/gerar.py --receitas glifos_mago --jogo [--folha arquivo.png]
"""
import numpy as np

import pintura as P
import glifos as G
from glifos import FOGO, VENENO, RAIO, PEDRA, ROXO, tela

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
    t = tela(C_VENENO, 56, 0.42, 64, 62)
    _nuvem(t, 58, 76, 84, 491, VENENO[:5], 0.8)
    _nuvem(t, 70, 46, 92, 492, VENENO)
    for (x, y, r) in [(40, 100, 4.5), (64, 106, 3.6), (88, 98, 4.0)]:
        gg = G.gota(x, y, r)
        t.brilho(gg, C_VENENO, 3, 0.8)
        t.pintar(gg, P.rampa(0.8, VENENO), 1.0)
    for (x, y, r) in [(52, 44, 5), (84, 38, 6), (70, 56, 3.5)]:   # bolhas na nuvem
        t.pintar(P.anel(x, y, r, 1.4), P.rampa(0.95, VENENO), 0.85)
    G.faiscas(t, 493, (64, 60), 50, 8, C_VENENO)
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
    t = tela(C_VENENO, 56, 0.42, 64, 74)
    borda = P.elipse(64, 82, 56, 30)
    t.pintar(borda, P.rampa(0.2 + 0.25 * P.ruido(511, 9, 3), PEDRA), 1.0)
    poca = P.elipse(64, 82, 48, 23)
    poca = np.clip(P.deformar(poca, (P.ruido(512, 20, 3) - 0.5) * 10, (P.ruido(513, 20, 3) - 0.5) * 6), 0, 1)
    t.brilho(poca, C_VENENO, 6, 0.6)
    t.pintar(poca, P.rampa(0.35 + 0.5 * P.ruido(514, (26, 10), 4), VENENO), 1.0)
    t.somar(P.borda_luz(poca).clip(0, 1) * poca, (0.9, 1.0, 0.6), 0.6)
    for (x, y, r) in [(40, 80, 7), (70, 90, 5), (86, 74, 8), (58, 70, 4)]:
        G.esfera(t, x, y, r, R_VENENO, alfa=0.9)
    for (x, y, r) in [(48, 44, 5), (78, 34, 6.5), (64, 54, 3.5), (92, 50, 4)]:   # bolhas que sobem
        t.brilho(P.circulo(x, y, r), C_VENENO, 3, 0.6)
        G.esfera(t, x, y, r, R_VENENO, alfa=0.85)
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
    t = tela(C_VENENO, 54, 0.45, 64, 62)
    t.brilho(P.circulo(64, 60, 36), C_VENENO, 8, 0.5)
    G.esfera(t, 64, 60, 36, [(6, 40, 6), (40, 130, 20), (120, 214, 50), (220, 255, 150)], alfa=0.7)
    t.somar(P.anel(64, 60, 36, 3.0), (0.8, 1.0, 0.5), 0.8)
    t.pintar(P.elipse(48, 44, 9, 5, -40), (1, 1, 0.92), 0.85)
    for (x, y, r) in [(72, 70, 8), (54, 74, 5), (80, 50, 4)]:
        t.pintar(P.anel(x, y, r, 1.6), P.rampa(0.92, VENENO), 0.9)
    for (x, y, r) in [(34, 108, 4.5), (64, 112, 3.5), (96, 106, 4)]:
        gg = G.gota(x, y, r)
        t.pintar(gg, P.rampa(0.78, VENENO), 1.0)
    G.faiscas(t, 531, (64, 60), 52, 8, C_VENENO)
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
