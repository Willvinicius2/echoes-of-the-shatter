"""Sentinela Oca (Rig_Humanoid_Chibi, Humanoid): golpe com antecipacao clara (rev6).
O KayKit Melee_1H_Attack_Chop so ergue o braco 25 cm para o lado; aqui o tronco torce para tras, o peso vai para o pe de tras e o braco sobe
atras da cabeca antes do golpe de cima. Tempos iguais aos do core (skills.csv, skill.enemy.sentinel_strike): preparacao 0,7 s (quadros 0-21),
impacto 0,1 s (21-24), recuperacao 0,5 s (24-39); a velocidade do clipe fica em 1 (o Animator so segue as fases do core).
Convencao da anim_lib (espaco do personagem): X esquerda, Y cima, Z frente; Spine/Chest/Neck/Head rx>0 inclina para a frente, ry>0 gira para a
esquerda do personagem; UpperArm rx<0 balanca para a frente/cima, rz<0 abre o braco direito; LowerArm rx<0 dobra o cotovelo.
O braco do golpe e o DIREITO (como o clipe do KayKit, que usa RightHand)."""
import math
from anim_lib import merge, lerp_pose

FILL = 1.5
CAM = (0.9, -0.5, 0.2)
WINDUP_END, IMPACT_END, TOTAL = 21, 24, 39


def hips(y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0):
    return {"Hips": {"rot": (rx, ry, rz), "loc": (0.0, y, z)}}


def torso(sp, ch, nk, hd, ry=0.0, rz=0.0):
    return {"Spine": (sp, ry * 0.45, rz * 0.5), "Chest": (ch, ry * 0.55, rz * 0.5), "Neck": (nk, -ry * 0.35, 0), "Head": (hd, -ry * 0.45, 0)}


def legs(ul, ll, ur, lr, spread=0.0):
    """Coxa/joelho esquerda (ul, ll) e direita (ur, lr); pes planos (compensa a cadeia)."""
    return {"LeftUpperLeg": (ul, 0, spread), "LeftLowerLeg": (ll, 0, 0), "LeftFoot": (-(ul + ll), 0, 0),
            "RightUpperLeg": (ur, 0, -spread), "RightLowerLeg": (lr, 0, 0), "RightFoot": (-(ur + lr), 0, 0)}


def arms(lu, ll, ru, rl):
    return {"LeftUpperArm": lu, "LeftLowerArm": (ll, 0, 0), "RightUpperArm": ru, "RightLowerArm": (rl, 0, 0)}


REST = merge(hips(), torso(0, 0, 0, 0), arms((0, 0, 8), -10, (0, 0, -8), -10), legs(0, 0, 0, 0))


def coil(k):
    """Pose de antecipacao, k em [0,1]: 0 = repouso, 1 = tronco torcido para tras, peso no pe de tras, braco direito atras da cabeca."""
    full = merge(hips(-0.05, -0.05, rx=-3, ry=-14), torso(-9, -12, 4, 8, ry=-34, rz=-8),
                 arms((-34, 6, 28), -34, (-148, -10, -22), -62), legs(-12, 14, 14, 30, 4))
    return lerp_pose(REST, full, k)


def strike():
    return merge(hips(-0.09, 0.09, rx=5, ry=16), torso(22, 26, 8, 12, ry=26, rz=4),
                 arms((24, 0, 10), -22, (-58, 4, -10), -22), legs(-26, 28, 18, 24, 5))


def settle():
    return merge(hips(-0.05, 0.05, rx=3, ry=8), torso(12, 14, 4, 6, ry=10),
                 arms((10, 0, 9), -14, (-26, 0, -9), -16), legs(-12, 14, 6, 12, 3))


def build(A, arm):
    keys = {0: REST}
    # preparacao: sobe rapido ate 70% da torcao (quadro 9) e depois cresce devagar ate o quadro 21 (tensao antes do golpe)
    keys[4] = dict(coil(0.4), _i='SINE', _e='EASE_OUT')
    keys[9] = dict(coil(0.72), _i='SINE')
    keys[15] = dict(coil(0.9), _i='SINE')
    keys[WINDUP_END] = dict(coil(1.0), _i='EXPO', _e='EASE_IN')
    keys[IMPACT_END] = dict(strike(), _i='SINE', _e='EASE_OUT')
    keys[28] = dict(lerp_pose(strike(), settle(), 0.55), _i='SINE')
    keys[TOTAL] = dict(REST, _i='SINE', _e='EASE_IN_OUT')
    act, last = A.make_action(arm, "AN_Sentinel_Strike", keys, loop=False)
    return [dict(action=act, last=last, loop=False, preview=[0, 6, 12, 18, 21, 22, 24, 28, 39],
                 events={"windup_end": WINDUP_END, "impact": WINDUP_END + 1, "recovery_end": TOTAL}, note="golpe da Sentinela 1,3 s")]
