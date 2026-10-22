"""Arqueiro (Rig_Humanoid_Chibi 1,82 m, pose A): 9 clipes a 30 fps, sem root motion, sem IA, sem download.
Mao ESQUERDA segura o arco (socket_weapon_l); mao DIREITA puxa a corda.
Estilo da anim_lib: pose por rotacao em graus nos eixos de repouso (X esquerda, Y cima, Z frente). Para pes sem deslizar
e para a mira (maos na linha da flecha) usa uma cinematica direta (FK) + IK de 2 ossos feitos aqui com mathutils; o resultado
final continua sendo rotacoes por osso (euler em graus) entregues a A.make_action.

Quadros: o ultimo quadro de um loop e copia do quadro 0 (a anim_lib grava assim; o glTF mantem a chave extra, que o Godot
precisa para o loop linear). Velocidades de referencia (para casar com a velocidade de movimento no jogo, escalar a animacao):
Walk 0,60 m/s (passada 0,60 m), Run 2,17 m/s (passada 1,30 m)."""
import math, os, sys
from mathutils import Matrix, Euler, Vector
from anim_lib import ease

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "personagens", "arqueiro"))
import proporcao

FILL = 1.3
CAM = (0.62, -0.78, 0.22)
FPS = 30
UP = Vector((0, 1, 0))
AIM = Vector((0, 0.03, 1)).normalized()
QN = {}                                   # rotacao de repouso acumulada por osso (proporcao.rotacoes_acumuladas)
I3 = Matrix.Identity(3)
ANKX, ANKY, ANKZ = 0.16, 0.09, -0.09       # tornozelo no repouso (calibrate le do esqueleto)


def conv(bone, parent, m):
    """Converte a rotacao D (escrita para o repouso antigo, A-pose) para o repouso chibi, mantendo a mesma pose no mundo."""
    qp, qb = QN.get(parent, I3), QN.get(bone, I3)
    return qp @ m @ qb.inverted()


def calibrate(arm):
    global QN, ANKX, ANKY, ANKZ
    QN = proporcao.rotacoes_acumuladas(arm)
    h = arm.data.bones["LeftFoot"].head_local
    ANKX, ANKY, ANKZ = h.x, h.y, h.z
    ANK["Left"] = Vector((ANKX, ANKY, ANKZ))
    ANK["Right"] = Vector((-ANKX, ANKY, ANKZ))


def deg(a):
    return math.radians(a)


def mat(rx=0.0, ry=0.0, rz=0.0):
    return Euler((deg(rx), deg(ry), deg(rz)), 'XYZ').to_matrix()


def lerp(a, b, t):
    return a + (b - a) * t


def sstep(t):
    return ease(t)


# ---------------------------------------------------------------- cinematica do esqueleto
class Pose:
    """Pose por rotacoes D[osso] (matriz no espaco do personagem). world_rot(osso) = prod(D ancestrais) @ D @ R_repouso."""

    def __init__(self, arm):
        bones = arm.data.bones
        self.head = {b.name: Vector(b.head_local) for b in bones}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in bones}
        self.D = {}
        self.arm_obj = arm
        self.hips_loc = Vector((0, 0, 0))
        self.raw = {}      # eulers diretos (para ossos setados sem passar por matriz, ex.: giro de 360 do rolamento)

    # --- escrita
    def rot(self, bone, rx=0.0, ry=0.0, rz=0.0):
        self.D[bone] = mat(rx, ry, rz)
        self.raw[bone] = (rx, ry, rz)
        if QN.get(bone, I3) != I3 or QN.get(self.parent[bone], I3) != I3:
            self.D[bone] = conv(bone, self.parent[bone], self.D[bone])
            e = self.D[bone].to_euler('XYZ')
            self.raw[bone] = (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))

    def many(self, **kw):
        for k, v in kw.items():
            self.rot(k, *v)

    def hips(self, x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0):
        self.hips_loc = Vector((x, y, z))
        self.rot("Hips", rx, ry, rz)

    # --- leitura
    def acc(self, bone):
        m = Matrix.Identity(3)
        chain = []
        b = bone
        while b:
            chain.append(b)
            b = self.parent[b]
        for n in reversed(chain):
            m = m @ self.D.get(n, Matrix.Identity(3))
        return m

    def pos(self, bone):
        par = self.parent[bone]
        if par is None:
            return self.head[bone].copy()
        if par == "root":
            return self.head[bone] + self.hips_loc
        return self.pos(par) + self.acc(par) @ (self.head[bone] - self.head[par])

    # --- IK de 2 ossos (a -> m -> e = cabeca do osso final), target em espaco do personagem
    def ik2(self, a, m, e, target, pole, reach=0.995):
        par = self.parent[a]
        Dp = self.acc(par) if par else Matrix.Identity(3)
        p0 = self.pos(a)
        l1 = (self.head[m] - self.head[a]).length
        l2 = (self.head[e] - self.head[m]).length
        v = Vector(target) - p0
        d = min(max(v.length, 0.05), (l1 + l2) * reach)
        n = v.normalized()
        ca = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        h = math.sqrt(max(l1 * l1 - ca * ca, 0.0))
        pp = Vector(pole) - n * Vector(pole).dot(n)
        pp = pp.normalized() if pp.length > 1e-6 else Vector((0, 0, 1))
        mid = p0 + n * ca + pp * h
        end = p0 + n * d
        w1 = (mid - p0).normalized()
        w2 = (end - mid).normalized()
        r1 = (self.head[m] - self.head[a]).normalized()
        self.D[a] = r1.rotation_difference(Dp.inverted() @ w1).to_matrix()
        r2 = (self.head[e] - self.head[m]).normalized()
        dacc = Dp @ self.D[a]
        self.D[m] = r2.rotation_difference(dacc.inverted() @ w2).to_matrix()
        return end

    def leg(self, side, ankle, pitch=0.0):
        """Perna side ('Left'/'Right') com o tornozelo em `ankle` (mundo); pe plano (+ pitch graus: positivo = ponta para baixo)."""
        self.ik2(side + "UpperLeg", side + "LowerLeg", side + "Foot", ankle, (0, 0.05, 1))
        self.D[side + "Foot"] = self.acc(side + "LowerLeg").inverted() @ mat(pitch, 0, 0)

    def hand_level(self, side, k=1.0, tilt=(0, 0, 0)):
        """Mao com a orientacao de repouso do mundo (arco sempre na vertical); k = fracao da compensacao (0..1)."""
        full = self.acc(side + "LowerArm").inverted() @ mat(*tilt) @ QN.get(side + "Hand", I3).inverted()
        q = Matrix.Identity(3).to_quaternion().slerp(full.to_quaternion(), k)
        self.D[side + "Hand"] = q.to_matrix()

    def arm(self, side, hand, pole):
        self.ik2(side + "UpperArm", side + "LowerArm", side + "Hand", hand, pole)

    # --- saida: dict de pose para a anim_lib
    def out(self):
        res = {}
        for n, m in self.D.items():
            if n in self.raw:
                r = self.raw[n]
            else:
                e = m.to_euler('XYZ')
                r = (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))
            res[n] = r
        res["Hips"] = {"rot": res.get("Hips", (0, 0, 0)), "loc": tuple(self.hips_loc)}
        return res


# ---------------------------------------------------------------- bases
ANK = {"Left": Vector((0.16, 0.09, -0.09)), "Right": Vector((-0.16, 0.09, -0.09))}
SIDE = {"Left": 1, "Right": -1}


def stand(P, y=0.0, width=0.16, lz=0.0, rz=0.0, lpitch=0.0, rpitch=0.0):
    """Pes plantados no chao (tornozelo a 0,09 m), quadril abaixado y."""
    P.leg("Left", Vector((width, ANKY, ANKZ + lz)), lpitch)
    P.leg("Right", Vector((-width, ANKY, ANKZ + rz)), rpitch)


def hang_arms(P, lsw=0.0, rsw=0.0, lelb=-26, relb=-18):
    """Bracos soltos; esquerdo com o arco. Esq/dir rx = balanco (negativo = frente)."""
    P.many(LeftUpperArm=(lsw, 0, -22), LeftLowerArm=(lelb, 0, 0), LeftHand=(-8, 0, 0),
           RightUpperArm=(rsw, 0, 22), RightLowerArm=(relb, 0, 0), RightHand=(0, 0, 0))


# ---------------------------------------------------------------- Idle (60 quadros = 2,0 s)
def idle_pose(A_, arm, t):
    P = Pose(arm)
    br = math.sin(2 * math.pi * t)
    sh = math.sin(2 * math.pi * t + 1.0)
    P.hips(y=-0.035 + 0.008 * br, rz=1.2 * math.sin(2 * math.pi * t * 1 + 0.5), ry=1.5 * math.sin(2 * math.pi * t))
    stand(P, width=0.15)
    P.many(Spine=(3 + 1.0 * br, 0, 0), Chest=(2 + 2.0 * br, -1.0 * sh, 0), Neck=(-2 - 0.8 * br, 1.5 * sh, 0),
           Head=(-1, 2.5 * sh, 0.8 * sh), LeftShoulder=(0, 0, 1.2 * br), RightShoulder=(0, 0, -1.2 * br))
    hang_arms(P, lsw=6 + 1.5 * br, rsw=4 - 2 * br, lelb=-30 - 2 * br, relb=-14)
    P.hand_level("Left", 1.0)
    return P.out()


# ---------------------------------------------------------------- locomocao
def foot_cycle(p, duty, A, stride, lift):
    """p em [0,1) -> (z do tornozelo relativo ao repouso, elevacao, pitch). Apoio: recua a velocidade constante (sem deslizar)."""
    if p < duty:
        s = p / duty
        pitch = 28 * max(0.0, (s - 0.78) / 0.22) ** 1.5
        return A - stride * p, 0.0, pitch
    s = (p - duty) / (1 - duty)
    m = -stride * (1 - duty)                       # tangente: velocidade do apoio nas duas pontas
    h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
    z = h00 * -A + h10 * m + h01 * A + h11 * m
    y = lift * math.sin(math.pi * s) ** 1.2
    pitch = 28 * max(0.0, 1 - s / 0.45) - 14 * max(0.0, (s - 0.55) / 0.45)
    return z, y, pitch


def walk_pose(arm, t):
    P = Pose(arm)
    stride, duty, lift = 0.60, 0.60, 0.06
    A = stride * duty / 2
    ph = 2 * math.pi * t
    h = -0.060 + 0.016 * math.cos(4 * math.pi * (t - 0.3))
    P.hips(x=0.012 * math.sin(ph), y=h, rz=-2.5 * math.sin(ph), ry=-5 * math.cos(ph), rx=2)
    for side, off in (("Left", 0.0), ("Right", 0.5)):
        z, y, pitch = foot_cycle((t + off) % 1.0, duty, A, stride, lift)
        P.leg(side, ANK[side] + Vector((0, y, z)), pitch)
    c = math.cos(ph)
    P.many(Spine=(4, 3 * c, 1.5 * math.sin(ph)), Chest=(3, 4 * c, 0), Neck=(-4, -2 * c, 0), Head=(-2, -3 * c, 0),
           LeftShoulder=(0, 0, 0), RightShoulder=(0, 0, 0))
    hang_arms(P, lelb=-30 - 6 * c, relb=-20 + 10 * c)
    # braco esquerdo (arco) balanca menos; ambos opostos ao da perna do mesmo lado
    P.rot("LeftUpperArm", 8 * c + 4, 0, -20)
    P.rot("RightUpperArm", -20 * c, 0, 20)
    P.hand_level("Left", 1.0)
    return P.out()


def run_pose(arm, t):
    P = Pose(arm)
    stride, duty, lift = 1.30, 0.38, 0.17
    A = stride * duty / 2
    ph = 2 * math.pi * t
    h = -0.115 - 0.035 * math.cos(4 * math.pi * (t - 0.19))
    P.hips(y=h, x=0.015 * math.sin(ph), ry=-10 * math.cos(ph), rz=-3 * math.sin(ph), rx=4)
    for side, off in (("Left", 0.0), ("Right", 0.5)):
        z, y, pitch = foot_cycle((t + off) % 1.0, duty, A, stride, lift)
        P.leg(side, ANK[side] + Vector((0, y, z)), pitch)
    c = math.cos(ph)
    P.many(Spine=(10, 6 * c, 2 * math.sin(ph)), Chest=(9, 8 * c, 0), Neck=(-6, -4 * c, 0), Head=(-9, -5 * c, 0),
           LeftShoulder=(0, 0, 0), RightShoulder=(0, 0, 0))
    P.many(LeftUpperArm=(-30 + 14 * c, 0, -14), LeftLowerArm=(-62, 0, 0), LeftHand=(-6, 0, 0),
           RightUpperArm=(-8 - 52 * c, 0, 16), RightLowerArm=(-70 + 14 * c, 0, 0), RightHand=(0, 0, 0))
    P.hand_level("Left", 1.0)
    return P.out()


# ---------------------------------------------------------------- mira
def aim_pose(arm, draw, t=0.0, tw=0.0, kick=0.0):
    """Mira. draw 0 = corda levemente puxada, 1 = totalmente puxada (>1 = a mao voa para tras na soltura). t = fase do sway (0..1).
    tw = torcao extra do tronco; kick = coice do arco (sobe a mao esquerda)."""
    P = Pose(arm)
    br = math.sin(2 * math.pi * t)
    twist = -18 - 4 * min(draw, 1.2) + tw
    P.hips(y=-0.05, ry=twist, rx=2)
    P.leg("Left", Vector((0.20, ANKY, ANKZ + 0.14)), 0)
    P.leg("Right", Vector((-0.18, ANKY, ANKZ - 0.20)), 0)
    P.many(Spine=(3 + 0.8 * br, twist * 0.5, 0), Chest=(1 + 1.2 * br, twist * 0.8, 0),
           Neck=(-2, -twist * 0.55, 0), Head=(-2, -twist * 1.0 - 8, -2),
           LeftShoulder=(0, 0, 3), RightShoulder=(0, 0, -2))
    # mao do arco: braco quase reto na linha de mira, na altura do ombro
    sh = P.pos("LeftUpperArm")
    reach = 0.95 * ((P.head["LeftLowerArm"] - P.head["LeftUpperArm"]).length + (P.head["LeftHand"] - P.head["LeftLowerArm"]).length)
    lhand = sh + AIM * reach + Vector((-0.01, 0.075 + kick * 0.05, 0))
    P.arm("Left", lhand, (0.5, -1, 0.1))
    P.hand_level("Left", 1.0, (-8 * kick, 0, 0))
    # mao da corda: do ponto frouxo ate a ancora no queixo
    anchor = P.pos("Head") + P.acc("Head") @ Vector((-0.05, 0.05, 0.12))
    loose = lhand - AIM * 0.13 + Vector((-0.035, -0.03, 0))
    rhand = loose + (anchor - loose) * draw
    P.arm("Right", rhand, (-0.35, 0.25, -1))
    P.D["RightHand"] = mat(0, 0, 0)
    return P.out()


def aim_idle_pose(arm, t):
    return aim_pose(arm, 0.0, t)


def draw_pose(arm, k):
    d = sstep(k)
    return aim_pose(arm, d + 0.04 * math.sin(math.pi * k) * k, 0.0, tw=-3 * d)


def release_pose(arm, f):
    # draw: 1 -> 1.4 (mao voa para tras) -> 0.55 -> 0 ; recuo do tronco e coice do arco
    curve = {0: 1.0, 1: 1.0, 2: 1.45, 3: 1.35, 5: 0.7, 8: 0.1, 9: 0.0}
    xs = sorted(curve)
    for a, b in zip(xs, xs[1:]):
        if a <= f <= b:
            u = (f - a) / (b - a)
            dr = lerp(curve[a], curve[b], sstep(u))
            break
    kick_c = {0: 0, 1: 0, 2: 1, 3: 0.9, 5: 0.35, 9: 0}
    ks = sorted(kick_c)
    for a, b in zip(ks, ks[1:]):
        if a <= f <= b:
            kick = lerp(kick_c[a], kick_c[b], sstep((f - a) / (b - a)))
            break
    rec = {0: 0, 2: 1, 5: 0.5, 9: 0}
    rs = sorted(rec)
    for a, b in zip(rs, rs[1:]):
        if a <= f <= b:
            r = lerp(rec[a], rec[b], sstep((f - a) / (b - a)))
            break
    return aim_pose(arm, dr, 0.0, tw=-3 + 4 * r, kick=kick)


# ---------------------------------------------------------------- dodge (rolamento a frente, 14 quadros = 0,47 s)
def dodge_pose(arm, f):
    n = 14
    P = Pose(arm)
    crouch = {0: 0.0, 2: 1.0, 4: 1.0, 10: 1.0, 12: 0.5, 14: 0.0}
    ks = sorted(crouch)
    for a, b in zip(ks, ks[1:]):
        if a <= f <= b:
            c = lerp(crouch[a], crouch[b], sstep((f - a) / (b - a)))
            break
    roll = 360.0 * sstep(max(0.0, min(1.0, (f - 3) / 8.0)))       # quadros 3..11
    ytab = {0: 0.0, 2: -0.24, 4: -0.17, 6: -0.06, 8: -0.04, 10: -0.14, 12: -0.22, 14: -0.035}
    ky = sorted(ytab)
    y = next(lerp(ytab[x0], ytab[x1], sstep((f - x0) / (x1 - x0))) for x0, x1 in zip(ky, ky[1:]) if x0 <= f <= x1)
    P.D["Hips"] = mat(roll, 0, 0)
    P.raw["Hips"] = (roll, 0, 0)
    P.hips_loc = Vector((0, y, 0.0 + 0.0))
    P.hips_loc = Vector((0, y, 0))
    P.D["Hips"] = mat(roll, 0, 0)
    P.raw["Hips"] = (roll, 0, 0)
    t_in = sstep(min(1.0, max(0.0, (f - 1) / 3.0))) * (1 - sstep(min(1.0, max(0.0, (f - 10.5) / 2.5))))
    t_in = max(t_in, 0.35 * c)
    P.many(Spine=(lerp(6, 58, t_in), 0, 0), Chest=(lerp(4, 36, t_in), 0, 0), Neck=(lerp(-2, 18, t_in), 0, 0),
           Head=(lerp(-2, 20, t_in), 0, 0),
           LeftUpperLeg=(lerp(-8, -118, t_in), 0, 4), LeftLowerLeg=(lerp(16, 138, t_in), 0, 0), LeftFoot=(lerp(-8, 30, t_in), 0, 0),
           RightUpperLeg=(lerp(-8, -118, t_in), 0, -4), RightLowerLeg=(lerp(16, 138, t_in), 0, 0), RightFoot=(lerp(-8, 30, t_in), 0, 0),
           LeftUpperArm=(lerp(-10, -62, t_in), 0, lerp(-22, -12, t_in)), LeftLowerArm=(lerp(-30, -70, t_in), 0, 0),
           RightUpperArm=(lerp(-10, -62, t_in), 0, lerp(22, 12, t_in)), RightLowerArm=(lerp(-20, -70, t_in), 0, 0))
    out = {}
    for nme, r in P.raw.items():
        out[nme] = r
    out["Hips"] = {"rot": (roll, 0, 0), "loc": tuple(P.hips_loc)}
    return out


# ---------------------------------------------------------------- hit (9 quadros = 0,3 s)
def hit_pose(arm, f):
    key = {0: 0.0, 2: 1.0, 4: 0.8, 9: 0.0}
    ks = sorted(key)
    for a, b in zip(ks, ks[1:]):
        if a <= f <= b:
            k = lerp(key[a], key[b], sstep((f - a) / (b - a)))
            break
    P = Pose(arm)
    P.hips(y=-0.035 - 0.03 * k, z=-0.05 * k, rx=-6 * k, ry=-6 * k, rz=3 * k)
    P.leg("Left", Vector((0.16, ANKY, ANKZ + 0.05 * k)), 0)
    P.leg("Right", Vector((-0.16, ANKY, ANKZ - 0.06 * k)), 0)
    P.many(Spine=(3 - 14 * k, 8 * k, 0), Chest=(2 - 16 * k, 10 * k, 4 * k), Neck=(-2 - 8 * k, -6 * k, 0), Head=(-1 - 16 * k, -10 * k, 6 * k),
           LeftShoulder=(0, 0, 3 * k), RightShoulder=(0, 0, 3 * k))
    P.many(LeftUpperArm=(lerp(6, 28, k), 0, lerp(-22, -2, k)), LeftLowerArm=(lerp(-30, -34, k), 0, 0), LeftHand=(-8, 0, 0),
           RightUpperArm=(lerp(4, 36, k), 0, lerp(22, 34, k)), RightLowerArm=(lerp(-14, -40, k), 0, 0))
    P.hand_level("Left", 1.0)
    return P.out()


# ---------------------------------------------------------------- death (36 quadros = 1,2 s)
def _interp(table, f):
    ks = sorted(table)
    if f <= ks[0]:
        return dict(table[ks[0]])
    if f >= ks[-1]:
        return dict(table[ks[-1]])
    for a, b in zip(ks, ks[1:]):
        if a <= f <= b:
            u = sstep((f - a) / (b - a))
            return {n: tuple(lerp(x, y, u) for x, y in zip(table[a][n], table[b][n])) for n in table[a]}


def _w(hy, hz, hrx, sp, ch, nk, hd, ul, ll, ur, lr, lua, lla, rua, rla, spread=4):
    """Pose bruta de morte (hips loc/rot + coluna + pernas + bracos), tudo em eulers."""
    return {"hips_loc": (0, hy, hz), "Hips": (hrx, 0, 0), "Spine": (sp, 0, 0), "Chest": (ch, 0, 0), "Neck": (nk, 0, 0), "Head": (hd, 0, 0),
            "LeftUpperLeg": (ul, 0, spread), "LeftLowerLeg": (ll, 0, 0), "LeftFoot": (-(ul + ll) * 0.6, 0, 0),
            "RightUpperLeg": (ur, 0, -spread), "RightLowerLeg": (lr, 0, 0), "RightFoot": (-(ur + lr) * 0.6, 0, 0),
            "LeftUpperArm": lua, "LeftLowerArm": (lla, 0, 0), "RightUpperArm": rua, "RightLowerArm": (rla, 0, 0)}


DEATH_KEYS = {
    0: _w(-0.035, 0, 0, 3, 2, -2, -1, 0, 0, 0, 0, (6, 0, -22), -30, (4, 0, 22), -14),
    4: _w(-0.08, -0.05, -6, -10, -14, -8, -16, 6, 14, -8, 12, (28, 0, -4), -34, (34, 0, 30), -40),                       # impacto
    12: _w(-0.26, -0.10, -4, 6, 4, 6, 8, -72, 128, -58, 118, (10, 0, -14), -20, (10, 0, 14), -20, spread=6),              # cai de joelhos
    20: _w(-0.30, -0.22, -26, -12, -14, -6, -10, -84, 134, -84, 134, (30, 0, -26), -10, (30, 0, 26), -10, spread=8),       # tomba para tras
    28: _w(-0.43, -0.30, -86, -4, -6, -4, -6, -42, 70, -56, 84, (16, 0, -38), -14, (20, 0, 30), -10, spread=10),          # bate no chao
    36: _w(-0.44, -0.32, -90, -2, -2, 0, -4, -6, 8, -12, 16, (6, 0, -50), -8, (12, 0, 42), -10, spread=11),                # fica no chao
}


def death_pose(arm, f):
    pose = _interp(DEATH_KEYS, f)
    out = {}
    for n, v in pose.items():
        if n == "hips_loc":
            continue
        v = tuple(v)
        b = arm.data.bones[n]
        pn = b.parent.name if b.parent else None
        if QN.get(n, I3) != I3 or QN.get(pn, I3) != I3:
            e = conv(n, pn, mat(*v)).to_euler('XYZ')
            v = (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))
        out[n] = v
    out["Hips"] = {"rot": pose["Hips"], "loc": tuple(pose["hips_loc"])}
    return out


# ---------------------------------------------------------------- montagem dos clipes
def _frames(fn, n, step=1):
    keys = {f: fn(f) for f in range(0, n, step)}
    return keys


def build(A, arm):
    calibrate(arm)
    mk = A.make_action
    out = []

    def add(name, keys, loop, preview, events, note):
        act, last = mk(arm, name, keys, loop=loop)
        out.append(dict(action=act, last=last, loop=loop, preview=preview, events=events, note=note))

    def loopkeys(fn, n, step=1):
        k = {f: fn(f / n) for f in range(0, n, step)}
        k[n] = "loop"
        return k

    add("AN_Arqueiro_Idle", loopkeys(lambda t: idle_pose(None, arm, t), 60, 2), True, [0, 15, 30, 45],
        {}, "Respiracao leve, arco relaxado na mao esquerda; 2,0 s")
    add("AN_Arqueiro_Walk", loopkeys(lambda t: walk_pose(arm, t), 30), True, [0, 7, 15, 22],
        {"passo_esq": 0, "passo_dir": 15}, "Caminhada 1,0 s, passada 0,60 m (0,60 m/s)")
    add("AN_Arqueiro_Run", loopkeys(lambda t: run_pose(arm, t), 18), True, [0, 5, 9, 14],
        {"passo_esq": 0, "passo_dir": 9}, "Corrida 0,6 s, passada 1,30 m (2,17 m/s)")
    k = {f: dodge_pose(arm, f) for f in range(0, 15)}
    add("AN_Arqueiro_Dodge", k, False, [0, 3, 6, 9, 12],
        {"iframes_inicio": 2, "iframes_fim": 12, "impulso": 3, "aterrissagem": 12}, "Rolamento a frente 14 quadros (0,47 s)")
    add("AN_Arqueiro_AimIdle", loopkeys(lambda t: aim_idle_pose(arm, t), 60, 2), True, [0, 15, 30, 45],
        {}, "Mira parada, arco estendido a esquerda, corda levemente puxada; 2,0 s")
    add("AN_Arqueiro_Draw", {f: draw_pose(arm, f / 15.0) for f in range(0, 16)}, False, [0, 5, 10, 15],
        {"corda_cheia": 15}, "Puxar a corda 0,5 s: da AimIdle (quadro 0) a corda cheia (quadro 15)")
    add("AN_Arqueiro_Release", {f: release_pose(arm, f) for f in range(0, 10)}, False, [0, 2, 5, 9],
        {"solta": 2, "volta_aim_idle": 9}, "Soltura: corda cheia (0) -> solta no 2 -> AimIdle (9); 9 quadros = 0,3 s")
    add("AN_Arqueiro_Hit", {f: hit_pose(arm, f) for f in range(0, 10)}, False, [0, 2, 4, 9],
        {"impacto": 2}, "Reacao a dano 0,3 s (9 quadros)")
    add("AN_Arqueiro_Death", {f: death_pose(arm, f) for f in range(0, 37, 2)}, False, [0, 8, 16, 24, 36],
        {"impacto": 4, "joelhos_no_chao": 12, "corpo_no_chao": 28}, "Morte 1,2 s: cai de joelhos e de costas, fica no chao")
    return out
