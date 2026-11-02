"""Gera as folhas de pixel art do arqueiro (quadro 64x64, ~42 px de altura, paleta fixa).

Método: modelo 3D procedural (elipsoides e cápsulas) amostrado em pontos de superfície, projetado em
ortográfica (câmera 3/4 de cima), sombreado em 3 tons por papel de cor (rampa da paleta), contorno de 1 px.
Todas as animações saem de poses (alvos de mãos e pés com IK de dois ossos), então as 5 direções
(S, SE, E, NE, N) ficam coerentes. SW, W e NW o jogo espelha.

Uso: python gerar_arqueiro_pixel.py <pasta_saida> [--previa]
Saída: arqueiro_<anim>.png (quadros x 64, 5 x 64) e, com --previa, previa_*.png ampliadas.
"""
import math
import os
import sys
import numpy as np
from PIL import Image

F = 64                  # lado do quadro
PIVO = (32, 52)         # pé
ELEV = math.radians(32)  # elevação da câmera
LUZ = np.array([-0.5, 0.6, 0.62])
LUZ = LUZ / np.linalg.norm(LUZ)
DIRS = [0, 45, 90, 135, 180]   # S, SE, E, NE, N (graus de giro do modelo)

# ---------------- paleta (rampas escuro -> claro) ----------------
def H(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

RAMPAS = {
    "cabelo": [H("8a4a1a"), H("c47a2a"), H("e8a43e"), H("fbd877")],
    "pele": [H("b8704a"), H("e0a074"), H("f6cfa4"), H("fff0d4")],
    "sobr": [H("4a2a14")] * 3,
    "tunica": [H("2f3e1c"), H("4a6128"), H("6f8c36"), H("a2c24f")],
    "capuz": [H("1a2a20"), H("2a4230"), H("40613a"), H("668850")],
    "couro": [H("33200f"), H("57361c"), H("80542a"), H("a9783c")],
    "bota": [H("2b1a0e"), H("4a2e19"), H("6b4426")],
    "calca": [H("2a2a1f"), H("403e2c"), H("5c5840")],
    "arco": [H("6a3f1c"), H("a06a30"), H("d09a52"), H("f1cd88")],
    "corda": [H("e6dcc0"), H("e6dcc0"), H("fffbe8")],
    "pena1": [H("a8861a"), H("efc92e"), H("fff08a")],
    "pena2": [H("2e5a2a"), H("4f8a3c"), H("7fb552")],
    "ferro": [H("4a4f5c"), H("7a8294"), H("c5ccdb")],
    "olho": [H("1a1210")] * 3,
    "boca": [H("a65a3c")] * 3,
    "brilho": [H("fff6dc")] * 3,
    "cinto": [H("26170f"), H("3b2216"), H("5e3a21")],
}
NOMES = list(RAMPAS.keys())
CONTORNO = H("1c120d")


# ---------------- primitivas (amostragem de superfície) ----------------
class Pts:
    def __init__(self):
        self.p, self.n, self.r, self.g = [], [], [], []

    def add(self, p, n, papel, parte):
        self.p.append(p)
        self.n.append(n)
        self.r.append(np.full(len(p), NOMES.index(papel)))
        self.g.append(np.full(len(p), parte))

    def cat(self):
        return (np.concatenate(self.p), np.concatenate(self.n), np.concatenate(self.r), np.concatenate(self.g))


def elipsoide(c, rad, papel, parte, passo=0.28, rot=None):
    a, b, cz = rad
    nu = max(8, int(math.pi * max(rad) / passo))
    nv = max(12, int(2 * math.pi * max(rad) / passo))
    u = np.linspace(0, math.pi, nu)[:, None]
    v = np.linspace(0, 2 * math.pi, nv, endpoint=False)[None, :]
    x = a * np.sin(u) * np.cos(v)
    y = b * np.sin(u) * np.sin(v)
    z = cz * np.cos(u) + 0 * v
    p = np.stack([x, y, z + 0 * x], -1).reshape(-1, 3)
    n = np.stack([x / a ** 2, y / b ** 2, z / cz ** 2 + 0 * x], -1).reshape(-1, 3)
    n = n / np.linalg.norm(n, axis=1, keepdims=True)
    if rot is not None:
        p = p @ rot.T
        n = n @ rot.T
    return (p + np.array(c, float), n, papel, parte)


def capsula(a, b, ra, rb, papel, parte, passo=0.28):
    a, b = np.array(a, float), np.array(b, float)
    ax = b - a
    L = np.linalg.norm(ax)
    if L < 1e-6:
        return elipsoide(a, (ra, ra, ra), papel, parte)
    ax /= L
    t0 = np.cross(ax, [0, 0, 1.0])
    if np.linalg.norm(t0) < 1e-3:
        t0 = np.cross(ax, [1.0, 0, 0])
    t0 /= np.linalg.norm(t0)
    t1 = np.cross(ax, t0)
    rmax = max(ra, rb)
    nt = max(2, int((L + 2 * rmax) / passo))
    nth = max(10, int(2 * math.pi * rmax / passo))
    pts, nor = [], []
    # tubo (cone)
    s = np.linspace(0, 1, nt)[:, None]
    th = np.linspace(0, 2 * math.pi, nth, endpoint=False)[None, :]
    r = ra + (rb - ra) * s
    d = np.cos(th)[..., None] * t0 + np.sin(th)[..., None] * t1
    d = np.broadcast_to(d, (nt, nth, 3))
    pos = a + s[..., None] * (b - a) + r[..., None] * d
    pts.append(pos.reshape(-1, 3))
    nor.append(d.reshape(-1, 3))
    # tampas esféricas
    for c, rr, sg in ((a, ra, -1), (b, rb, 1)):
        nu = max(6, int(math.pi * rr / passo / 2))
        u = np.linspace(0, math.pi / 2, nu)[:, None]
        v = np.linspace(0, 2 * math.pi, max(8, int(2 * math.pi * rr / passo)), endpoint=False)[None, :]
        dd = (np.sin(u) * np.cos(v))[..., None] * t0 + (np.sin(u) * np.sin(v))[..., None] * t1 + (sg * np.cos(u))[..., None] * ax
        pts.append((c + rr * dd).reshape(-1, 3))
        nor.append(dd.reshape(-1, 3))
    return (np.concatenate(pts), np.concatenate(nor), papel, parte)


def anel(c, ra, rb, tubo, papel, parte, passo=0.3):
    n1 = int(2 * math.pi * max(ra, rb) / passo)
    n2 = max(8, int(2 * math.pi * tubo / passo))
    ph = np.linspace(0, 2 * math.pi, n1, endpoint=False)[:, None]
    th = np.linspace(0, 2 * math.pi, n2, endpoint=False)[None, :]
    cx, cy = ra * np.cos(ph), rb * np.sin(ph)
    nx = np.cos(ph) * np.cos(th)
    ny = np.sin(ph) * np.cos(th)
    nz = np.sin(th) + 0 * ph
    x = cx + tubo * nx
    y = cy + tubo * ny
    z = tubo * nz
    p = np.stack([x, y, z], -1).reshape(-1, 3) + np.array(c, float)
    n = np.stack([nx + 0 * th, ny + 0 * th, nz], -1).reshape(-1, 3)
    return (p, n, papel, parte)


def add(grupo, prim):
    grupo.add(prim[0], prim[1], prim[2], prim[3])


# ---------------- partes ----------------
PARTE = {"corpo": 1, "cabeca": 2, "braco": 3, "perna": 4, "arco": 5, "corda": 6, "flecha": 7, "cabelo": 8}


def modelo_torso():
    g = Pts()
    P = PARTE["corpo"]
    add(g, elipsoide((0, 0, 19.8), (4.7, 3.7, 6.4), "tunica", P))
    add(g, elipsoide((0, 0, 15.2), (5.2, 4.2, 3.9), "tunica", P))       # saia da túnica
    for sx in (-1, 1):                                                   # ombros na silhueta
        add(g, elipsoide((sx * 5.0, 0.0, 23.6), (2.8, 2.9, 2.5), "tunica", P))
    add(g, anel((0, 0, 14.6), 4.8, 3.9, 0.95, "cinto", P))              # cinto
    add(g, elipsoide((3.9, 2.6, 14.2), (1.5, 1.2, 1.5), "couro", P))    # bolsinha
    add(g, elipsoide((-5.7, 0.2, 24.6), (3.1, 3.1, 2.3), "couro", P))   # ombreira
    add(g, anel((-5.7, 0.2, 24.7), 2.8, 2.8, 0.55, "couro", P))
    for t in np.linspace(0, 1, 18):                                      # tira cruzada no peito
        x = -3.6 + 7.0 * t
        z = 25.3 - 10.4 * t
        k = 1 - (x / 4.7) ** 2 - ((z - 19.8) / 6.4) ** 2
        if k > 0:
            y = 3.7 * math.sqrt(k) + 0.25
            add(g, elipsoide((x, y, z), (1.0, 0.8, 1.0), "couro", PARTE["corpo"], 0.2))
    # tira da aljava atravessando as costas (no sentido contrário), para ler de costas
    for t in np.linspace(0, 1, 18):
        x = 3.6 - 7.0 * t
        z = 25.3 - 10.4 * t
        k = 1 - (x / 4.7) ** 2 - ((z - 19.8) / 6.4) ** 2
        if k > 0:
            y = -3.7 * math.sqrt(k) - 0.25
            add(g, elipsoide((x, y, z), (1.0, 0.8, 1.0), "couro", PARTE["corpo"], 0.2))
    # capuz caído nos ombros (gola grossa)
    add(g, anel((0, -0.5, 24.6), 4.5, 3.6, 1.0, "tunica", P))
    # aljava nas costas, inclinada, mais fina e de lado
    add(g, capsula((2.8, -4.9, 12.0), (-2.8, -5.3, 28.6), 2.35, 2.35, "couro", P))
    add(g, anel((-2.6, -5.5, 28.6), 1.5, 1.5, 0.4, "ferro", P))
    for dx, dy, papel in ((-0.8, 0.0, "pena1"), (0.6, -0.6, "pena2"), (-2.0, -0.9, "pena1")):
        add(g, capsula((-2.6 + dx * 0.4, -5.5 + dy * 0.4, 28.8), (-3.6 + dx, -5.9 + dy, 34.6), 0.6, 0.85, papel, P))
    return g.cat()


def modelo_cabeca():
    """Devolve (cabeça sem cabelo, cabelo)."""
    g = Pts()
    P = PARTE["cabeca"]
    H_ = PARTE["cabelo"]
    add(g, elipsoide((0, 0.5, 32.0), (7.2, 6.6, 6.9), "pele", P))
    for sx in (-2.7, 2.7):
        add(g, elipsoide((sx, 6.5, 31.4), (1.15, 0.8, 1.6), "olho", P, 0.15))     # olho 2 px
        add(g, elipsoide((sx + 0.35, 7.1, 32.0), (0.45, 0.35, 0.5), "brilho", P, 0.12))  # brilho de 1 px
        add(g, capsula((sx - 1.5 * np.sign(sx) * -1, 6.2, 34.0), (sx + 1.5 * np.sign(sx) * -1, 6.2, 34.3), 0.5, 0.5, "sobr", P, 0.15))
    add(g, elipsoide((0, 6.8, 28.4), (0.9, 0.5, 0.3), "boca", P, 0.12))           # boca
    add(g, elipsoide((0, 7.0, 30.0), (0.7, 0.6, 0.8), "pele", P, 0.15))           # nariz
    # capuz caído nas costas: só atrás e nas laterais, nunca cobre o topo nem a testa
    add(g, elipsoide((0, -5.6, 28.6), (5.8, 3.2, 4.8), "capuz", P))
    add(g, elipsoide((-6.2, -2.4, 29.0), (1.5, 3.2, 3.4), "capuz", P))
    add(g, elipsoide((6.2, -2.4, 29.0), (1.5, 3.2, 3.4), "capuz", P))
    hair = Pts()
    # calota de cabelo + mechas espetadas no topo e na frente (realce amarelo-claro vem da rampa)
    add(hair, elipsoide((0.4, -0.6, 34.2), (7.2, 6.6, 4.6), "cabelo", H_))
    add(hair, elipsoide((-0.8, 4.2, 35.6), (5.6, 2.4, 2.2), "cabelo", H_))
    # mechas assimétricas: esquerda curta, direita mais longa, tufo caído na testa
    for c, r in (((-4.8, 4.2, 35.8), (1.4, 1.5, 2.0)), ((-2.0, 5.2, 36.6), (1.4, 1.4, 2.2)),
                 ((3.4, 5.4, 36.4), (1.5, 1.5, 2.4)), ((5.4, 3.8, 35.6), (1.5, 1.6, 2.2)),
                 ((-3.6, 1.0, 38.2), (1.6, 1.7, 2.2)), ((0.0, -0.2, 39.0), (1.8, 1.8, 2.6)),
                 ((3.8, 0.4, 39.6), (1.7, 1.7, 3.0)), ((6.6, 0.6, 36.4), (1.6, 1.8, 2.8)),
                 ((-6.6, 0.8, 35.8), (1.5, 1.7, 2.4)), ((0, -5.2, 34.4), (3.4, 2.4, 3.2)),
                 ((-6.0, 2.4, 32.0), (1.2, 1.5, 2.2)), ((6.2, 2.4, 31.4), (1.2, 1.6, 3.0)),
                 ((1.6, 6.3, 34.0), (1.2, 1.1, 2.4))):
        add(hair, elipsoide(c, r, "cabelo", H_))
    return g.cat(), hair.cat()


# ---------------- álgebra ----------------
def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def ik2(S, T, l1, l2, pole):
    S, T = np.array(S, float), np.array(T, float)
    d = T - S
    dist = np.linalg.norm(d)
    dist = min(max(dist, 1e-3), l1 + l2 - 0.02)
    dirv = d / max(np.linalg.norm(d), 1e-6)
    T = S + dirv * dist
    a = (l1 ** 2 - l2 ** 2 + dist ** 2) / (2 * dist)
    h = math.sqrt(max(l1 ** 2 - a ** 2, 0.0))
    pole = np.array(pole, float)
    perp = pole - dirv * np.dot(pole, dirv)
    if np.linalg.norm(perp) < 1e-4:
        perp = np.array([1.0, 0, 0]) - dirv * dirv[0]
    perp /= np.linalg.norm(perp)
    return S + dirv * a + perp * h, T


# ---------------- pose ----------------
def pose_base():
    return dict(
        root_dz=0.0, root_dy=0.0, root_pitch=0.0, root_pivo=(0, 0, 12.0),
        torso_yaw=0.0, torso_pitch=0.0, torso_dz=-1.8,
        head_yaw=0.0, head_pitch=0.0, head_roll=0.0, head_dz=0.0, head_dy=0.0,
        handL=(7.6, 1.8, 12.8), handR=(-7.4, 0.8, 12.8),
        footL=(2.4, 0.4, 2.6), footR=(-2.4, 0.4, 2.6),
        poleL=(1.0, -0.5, -0.4), poleR=(-1.0, -0.5, -0.4),
        kneeL=(0.25, 1.0, 0.0), kneeR=(-0.25, 1.0, 0.0),
        bow_tilt=0.0, bow_on=True, pull=0.0, arrow=False, hip_yaw=0.0,
    )


SH_L = np.array([5.1, 0.0, 23.4])
SH_R = np.array([-5.1, 0.0, 23.4])
HIP_L = np.array([2.3, 0.0, 12.8])
HIP_R = np.array([-2.3, 0.0, 12.8])

_cache = {}


def estaticos():
    if "t" not in _cache:
        _cache["t"] = modelo_torso()
        _cache["h"], _cache["hr"] = modelo_cabeca()
    return _cache["t"], _cache["h"], _cache["hr"]


def prim_dyn(lista, prim):
    lista.append(prim)


def montar(pose):
    """Devolve (pos, normais, papel, parte) do modelo posado, antes da câmera."""
    T, Hd, Hr = estaticos()
    out = []
    # torso: yaw e pitch em torno do quadril
    pv_t = np.array([0, 0, 13.0])
    Rt = rot_z(pose["torso_yaw"]) @ rot_x(pose["torso_pitch"])
    off_t = np.array([0, 0, pose["torso_dz"]])

    def tf_t(p):
        return (p - pv_t) @ Rt.T + pv_t + off_t

    def tf_t_n(n):
        return n @ Rt.T

    out.append((tf_t(T[0]), tf_t_n(T[1]), T[2], T[3]))
    # cabeça: gira em torno do pescoço, depois acompanha o torso
    pv_h = np.array([0, 0.3, 27.0])
    Rh = rot_z(pose["head_yaw"]) @ rot_x(pose["head_pitch"]) @ rot_y(pose["head_roll"])
    hp = (Hd[0] - pv_h) @ Rh.T + pv_h + np.array([0, pose["head_dy"], pose["head_dz"]])
    hn = Hd[1] @ Rh.T
    out.append((tf_t(hp), tf_t_n(hn), Hd[2], Hd[3]))
    sw = np.array([pose.get("hair_dx", 0.0), 0.0, pose.get("hair_dz", 0.0)])
    hrp = (Hr[0] - pv_h) @ Rh.T + pv_h + np.array([0, pose["head_dy"], pose["head_dz"]]) + sw
    out.append((tf_t(hrp), tf_t_n(Hr[1] @ Rh.T), Hr[2], Hr[3]))

    sL, sR = tf_t(SH_L), tf_t(SH_R)
    Ry = rot_z(pose["hip_yaw"])
    hL, hR = (HIP_L - [0, 0, 0]) @ Ry.T, (HIP_R) @ Ry.T
    hL = hL + np.array([0, 0, 0])
    hR = hR + np.array([0, 0, 0])

    dyn = []
    # braços
    for lado, S, T_, pole in (("L", sL, np.array(pose["handL"], float), pose["poleL"]),
                              ("R", sR, np.array(pose["handR"], float), pose["poleR"])):
        E, Tm = ik2(S, T_, 5.6, 5.6, pole)
        dyn.append(capsula(S, E, 2.0, 1.75, "tunica", PARTE["braco"]))
        # antebraço: manga verde e braçadeira de couro na metade de baixo
        M = E + (Tm - E) * 0.5
        dyn.append(capsula(E, M, 1.8, 1.8, "tunica", PARTE["braco"]))
        dyn.append(capsula(M, Tm, 1.9, 1.9, "couro", PARTE["braco"]))
        dyn.append(elipsoide(Tm, (1.75, 1.75, 1.75), "pele", PARTE["braco"]))
        if lado == "L":
            HL = Tm
        else:
            HR = Tm
    # pernas
    for lado, hip, foot, pole in (("L", hL, np.array(pose["footL"], float), pose["kneeL"]),
                                  ("R", hR, np.array(pose["footR"], float), pose["kneeR"])):
        K, A = ik2(hip, foot + np.array([0, 0, 1.6]), 5.0, 4.8, pole)
        dyn.append(capsula(hip, K, 2.5, 2.35, "calca", PARTE["perna"]))
        dyn.append(capsula(K, A, 2.6, 2.7, "bota", PARTE["perna"]))
        dyn.append(anel(K + np.array([0, 0, -0.9]), 2.3, 2.3, 0.45, "couro", PARTE["perna"]))
        ante = foot + np.array([0, 3.0, -0.6])
        dyn.append(capsula(A + np.array([0, 0.2, -1.2]), ante + np.array([0, 0.8, 0]), 3.0, 2.3, "bota", PARTE["perna"]))
    # arco: acompanha a mão esquerda, plano vertical, pontas voltadas para o arqueiro
    if pose["bow_on"]:
        Rb = rot_z(pose.get("bow_yaw", 1.05)) @ rot_x(pose["bow_tilt"])
        grip = np.array(HL) + np.array([3.2, 0.6, -1.6])
        tips = []
        prev = None
        for t in np.linspace(-1, 1, 14):
            z = 13.0 * t
            y = 2.0 - 5.6 * t * t
            p = grip + Rb @ np.array([0, y, z])
            tips.append(p)
            if prev is not None:
                papel = "arco" if abs(t) > 0.2 else "couro"
                rr = 1.5 if abs(t) > 0.2 else 1.9
                dyn.append(capsula(prev, p, rr, rr, papel, PARTE["arco"], 0.22))
            prev = p
        # corda
        nock = tips[0] * 0.5 + tips[-1] * 0.5
        if pose["pull"] > 0:
            nock = nock * (1 - pose["pull"]) + (np.array(HR) + np.array([0, -0.2, 0.0])) * pose["pull"]
        dyn.append(capsula(tips[0], nock, 0.45, 0.45, "corda", PARTE["corda"], 0.2))
        dyn.append(capsula(nock, tips[-1], 0.45, 0.45, "corda", PARTE["corda"], 0.2))
        if pose["arrow"]:
            cab = np.array(HL) + np.array([0.2, 4.2, 0.0])
            dyn.append(capsula(nock + np.array([0, -1.0, 0]), cab, 0.65, 0.65, "pena1", PARTE["flecha"], 0.2))
            dyn.append(capsula(cab, cab + np.array([0, 1.4, 0]), 0.7, 0.2, "ferro", PARTE["flecha"], 0.2))
    for d in dyn:
        out.append(d)
    pos = np.concatenate([o[0] for o in out])
    nor = np.concatenate([o[1] for o in out])
    pap = np.concatenate([np.full(len(o[0]), NOMES.index(o[2])) if isinstance(o[2], str) else o[2] for o in out])
    par = np.concatenate([np.full(len(o[0]), o[3]) if np.isscalar(o[3]) else o[3] for o in out])
    # pernas e pés seguem o quadril; nada mais a fazer
    # raiz
    Rr = rot_y(pose.get("root_roll", 0.0)) @ rot_x(pose["root_pitch"])
    pv = np.array(pose["root_pivo"], float)
    pos = (pos - pv) @ Rr.T + pv + np.array([pose.get("root_dx", 0.0), pose["root_dy"], pose["root_dz"]])
    nor = nor @ Rr.T
    return pos, nor, pap, par


# ---------------- render ----------------
def renderizar(pose, graus):
    pos, nor, pap, par = montar(pose)
    R = rot_z(-math.radians(graus))
    pos = pos @ R.T
    nor = nor @ R.T
    sx = pos[:, 0]
    sy = -pos[:, 2] * math.cos(ELEV) + pos[:, 1] * math.sin(ELEV)
    dep = pos[:, 1] * math.cos(ELEV) + pos[:, 2] * math.sin(ELEV)
    # normal em espaço de câmera para a luz (luz fixa na tela)
    nc = np.stack([nor[:, 0], nor[:, 1] * math.cos(ELEV) + nor[:, 2] * math.sin(ELEV),
                   -nor[:, 1] * math.sin(ELEV) + nor[:, 2] * math.cos(ELEV)], 1)
    # câmera: x direita, y para a câmera, z para cima (aprox.)
    lum = nor @ LUZ
    ix = np.floor(sx + PIVO[0] + 0.5).astype(int)
    iy = np.floor(sy + PIVO[1] + 0.5).astype(int)
    ok = (ix >= 1) & (ix < F - 1) & (iy >= 1) & (iy < F - 1)
    ix, iy, dep, lum, pap, par = ix[ok], iy[ok], dep[ok], lum[ok], pap[ok], par[ok]
    idx = iy * F + ix
    ordem = np.argsort(dep)  # do mais longe ao mais perto: o último vence
    zb = np.full(F * F, -1e9)
    papel = np.full(F * F, -1)
    luz = np.zeros(F * F)
    parte = np.zeros(F * F, int)
    zb[idx[ordem]] = dep[ordem]
    papel[idx[ordem]] = pap[ordem]
    luz[idx[ordem]] = lum[ordem]
    parte[idx[ordem]] = par[ordem]
    img = np.zeros((F, F, 4), np.uint8)
    cobre = papel >= 0
    for i in np.where(cobre)[0]:
        rampa = RAMPAS[NOMES[papel[i]]]
        n = len(rampa)
        l = luz[i]
        if n == 1:
            k = 0
        else:
            lim = [0.30, 0.62, 0.90][: n - 1] if n == 4 else [0.34, 0.74][: n - 1]
            k = sum(1 for t in lim if l >= t)
        c = rampa[min(k, n - 1)]
        img[i // F, i % F] = (*c, 255)
    # contorno interno: vizinho (acima ou à esquerda) bem mais perto e de outra parte escurece o pixel
    zb2 = zb.reshape(F, F)
    pr2 = parte.reshape(F, F)
    pp2 = papel.reshape(F, F)
    for y in range(1, F - 1):
        for x in range(1, F - 1):
            if pp2[y, x] < 0:
                continue
            for dy, dx in ((-1, 0), (0, -1), (1, 0), (0, 1)):
                yy, xx = y + dy, x + dx
                if pp2[yy, xx] >= 0 and pr2[yy, xx] != pr2[y, x] and zb2[yy, xx] - zb2[y, x] > 2.2:
                    rampa = RAMPAS[NOMES[pp2[y, x]]]
                    img[y, x] = (*rampa[0], 255)
                    break
    # contorno externo seletivo: cor escura do próprio material vizinho (nunca preto chapado)
    alfa = img[..., 3] > 0
    for y in range(F):
        for x in range(F):
            if alfa[y, x]:
                continue
            viz = [(y + dy, x + dx) for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
                   if 0 <= y + dy < F and 0 <= x + dx < F and alfa[y + dy, x + dx]]
            if not viz:
                continue
            # vizinho mais escuro dá o tom: baixo/esquerda pesam mais (sombra), topo mais claro
            yy, xx = min(viz, key=lambda q: int(sum(int(v) for v in img[q[0], q[1], :3])))
            c = np.array(img[yy, xx, :3], float)
            c = c * 0.38 + np.array([14, 8, 12]) * 0.62 * 0.5
            img[y, x] = (*[int(v) for v in c], 255)
    return Image.fromarray(img, "RGBA")


# ---------------- animações ----------------
def L(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def anim_idle(i, n=6):
    s_ = math.sin(2 * math.pi * i / n)
    p = pose_base()
    resp = [0.0, 0.0, 0.6, 1.0, 0.6, 0.0][i]
    p["head_dz"] = resp * 0.5
    p["torso_dz"] = -1.8 + resp * 0.35
    p["handL"] = (7.6, 1.8, 12.8 + resp * 0.4)
    p["handR"] = (-7.4, 0.8, 12.8 + resp * 0.4)
    p["head_pitch"] = -0.03 * s_
    p["hair_dx"] = [0.0, 0.3, 0.6, 0.3, 0.0, -0.3][i]
    p["hair_dz"] = [0.0, -0.2, -0.4, -0.2, 0.0, 0.0][i]
    return p


def anim_run(i, n=8):
    ph = 2 * math.pi * i / n
    p = pose_base()
    sw = math.sin(ph)
    p["root_dz"] = abs(math.cos(ph)) * 1.3 - 0.6
    p["torso_pitch"] = -0.16  # inclina para a frente
    p["torso_yaw"] = 0.10 * sw
    p["head_pitch"] = 0.10
    p["head_yaw"] = -0.10 * sw
    for lado, sg in (("L", 1), ("R", -1)):
        f = math.sin(ph + (0 if lado == "L" else math.pi))
        lift = max(0.0, math.cos(ph + (0 if lado == "L" else math.pi))) * 3.4
        p["foot" + lado] = (2.4 * sg, 0.4 + 4.6 * f, 2.6 + lift)
    p["handL"] = (7.0, 2.0 - 2.2 * sw, 13.8 + 0.8 * abs(sw))
    p["handR"] = (-7.0, 1.0 + 4.4 * sw, 13.4 + 0.6 * abs(sw))
    p["poleL"] = (1.0, -0.8, -0.4)
    p["poleR"] = (-1.0, -0.8, -0.4)
    return p


def anim_attack(i, n=6):
    p = pose_base()
    # estância lateral: ombro do arco para a frente
    yaw = [0.5, 0.9, 1.05, 1.1, 0.95, 0.7][i]
    p["torso_yaw"] = yaw
    p["head_yaw"] = -yaw * 0.9
    p["head_pitch"] = 0.02
    p["footL"] = (1.8, 3.8, 2.6)
    p["footR"] = (-1.8, -3.4, 2.6)
    p["torso_pitch"] = -0.04
    hand_bow = [(5.0, 6.5, 22.0), (5.2, 9.0, 24.2), (5.2, 10.0, 25.0), (5.2, 10.2, 25.2), (5.2, 10.2, 25.2), (5.0, 9.0, 24.0)][i]
    draw = [(-0.5, 5.5, 22.0), (-1.5, 4.0, 24.5), (-3.2, 2.2, 26.0), (-4.4, 1.0, 26.8), (-1.2, 3.8, 25.0), (-1.0, 5.0, 23.2)][i]
    p["handL"] = hand_bow
    p["handR"] = draw
    p["poleL"] = (0.8, -0.2, -1.0)
    p["poleR"] = (-0.6, -1.0, 0.1)
    p["pull"] = [0.0, 0.35, 0.8, 1.0, 0.0, 0.0][i]
    p["arrow"] = i in (0, 1, 2, 3)
    p["bow_tilt"] = 0.0
    p["bow_yaw"] = 0.6
    p["root_dy"] = -0.6 if i == 4 else 0.0
    return p


def anim_dodge(i, n=6):
    p = pose_base()
    ang = [-0.5, -1.7, -3.3, -4.9, -6.0, -6.28][i]
    dz = [-1.5, 6.0, 9.5, 7.5, 2.0, 0.0][i]
    p["root_pitch"] = ang
    p["root_dz"] = dz
    p["root_pivo"] = (0, 0, 14.0)
    if i in (1, 2, 3, 4):
        # corpo encolhido (bola)
        p["footL"] = (2.0, 3.5, 9.0)
        p["footR"] = (-2.0, 3.5, 9.0)
        p["handL"] = (4.5, 5.5, 16.0)
        p["handR"] = (-4.5, 5.5, 16.0)
        p["head_pitch"] = 0.5
        p["torso_pitch"] = -0.5
    elif i == 0:
        p["torso_pitch"] = -0.4
        p["footL"] = (2.4, 1.0, 2.6)
        p["footR"] = (-2.4, 1.0, 2.6)
    return p


def anim_hit(i, n=3):
    p = pose_base()
    k = [1.0, 0.8, 0.3][i]
    p["torso_pitch"] = 0.30 * k
    p["head_pitch"] = 0.30 * k
    p["head_dy"] = -0.8 * k
    p["root_dy"] = -1.2 * k
    p["handL"] = (8.0, -0.5, 16.5 * k + 12.8 * (1 - k))
    p["handR"] = (-8.0, -0.8, 16.0 * k + 12.8 * (1 - k))
    p["footL"] = (2.8, 1.8, 2.6)
    p["footR"] = (-2.8, -1.2, 2.6)
    return p


def anim_death(i, n=8):
    p = pose_base()
    ang = [0.25, 0.55, 0.95, 1.30, 1.50, 1.57, 1.57, 1.57][i]
    p["root_pitch"] = 0.25 * min(i, 3) / 3
    p["root_roll"] = ang
    p["root_dx"] = -19.0 * math.sin(ang)
    p["root_pivo"] = (0, 0, 2.0)
    p["root_dz"] = [0, 0.5, 1.5, 2.5, 3.2, 3.6, 3.6, 3.6][i]
    p["torso_pitch"] = [0.1, 0.1, 0.0, 0.0, 0, 0, 0, 0][i]
    p["handL"] = (8.5 + 1.0 * min(i, 4) / 4, -1.5, 14.0 + (4.0 if i < 4 else 0))
    p["handR"] = (-8.5, -2.0, 13.0 + (3.0 if i < 4 else 0))
    p["footL"] = (3.0, 0.5, 2.6)
    p["footR"] = (-3.0, 0.2, 2.6)
    p["head_pitch"] = 0.2
    return p


ANIMS = {"idle": (anim_idle, 6), "run": (anim_run, 8), "attack": (anim_attack, 6),
         "dodge": (anim_dodge, 6), "hit": (anim_hit, 3), "death": (anim_death, 8)}


def folha(nome):
    fn, n = ANIMS[nome]
    sheet = Image.new("RGBA", (n * F, 5 * F), (0, 0, 0, 0))
    for r, g in enumerate(DIRS):
        for q in range(n):
            sheet.paste(renderizar(fn(q, n), g), (q * F, r * F))
    return sheet


def ancoras(esc):
    """Boca do arco (ponta da flecha no quadro de soltar) por linha, em px do mundo a partir dos pés."""
    p = anim_attack(4)
    tip = np.array(p["handL"], float) + np.array([0.2, 5.6, 0.0]) + np.array([0, p["root_dy"], 0])
    linhas = []
    for r, g in enumerate(DIRS):
        q = rot_z(-math.radians(g)) @ tip
        sx = q[0]
        sy = -q[2] * math.cos(ELEV) + q[1] * math.sin(ELEV)
        linhas.append((r, round(sx * esc), round(sy * esc)))
    return linhas


def main():
    saida = sys.argv[1]
    previa = "--previa" in sys.argv
    if "--ancoras" in sys.argv:
        for r, x, y in ancoras(1.0):
            print(f"arqueiro,attack,{r},{x},{y}")
        return
    only = [a for a in sys.argv[2:] if not a.startswith("--")]
    os.makedirs(saida, exist_ok=True)
    for nome in ANIMS:
        if only and nome not in only:
            continue
        s = folha(nome)
        s.save(os.path.join(saida, f"arqueiro_{nome}.png"))
        if previa:
            bg = Image.new("RGBA", s.size, (70, 78, 70, 255))
            bg.alpha_composite(s)
            bg = bg.resize((s.width * 3, s.height * 3), Image.NEAREST)
            bg.save(os.path.join(saida, f"previa_{nome}.png"))
        print(nome, s.size)


if __name__ == "__main__":
    main()
