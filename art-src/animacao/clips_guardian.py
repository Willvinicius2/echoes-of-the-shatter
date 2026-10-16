"""Guardiao da Cripta: Rugido (2,0 s), Investida do Escudo (preparacao 0,9 s, corrida em loop, recuperacao 1,0 s).
Autorado no esqueleto do proprio modelo (loc do Hips em metros reais do Guardiao, que tem ~5,5 m).
Escudo no braco ESQUERDO; se o modelo trouxer o escudo no direito, ponha SHIELD_LEFT = False (espelha tudo)."""
import math
from anim_lib import LR, merge

SHIELD_LEFT = True
FILL = 1.35
CAM = (0.62, -0.78, 0.22)


def hips(y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0):
    return {"Hips": {"rot": (rx, ry, rz), "loc": (0.0, y, z)}}


def legs(ul, ll, ur, lr, spread=0.0):
    """Pernas: coxa/joelho esquerda (ul, ll) e direita (ur, lr); pes sempre planos (compensa a cadeia)."""
    return {"LeftUpperLeg": (ul, 0, spread), "LeftLowerLeg": (ll, 0, 0), "LeftFoot": (-(ul + ll), 0, 0),
            "RightUpperLeg": (ur, 0, -spread), "RightLowerLeg": (lr, 0, 0), "RightFoot": (-(ur + lr), 0, 0)}


def torso(sp, ch, nk, hd, ry=0.0, rz=0.0):
    return {"Spine": (sp, ry * 0.5, rz * 0.5), "Chest": (ch, ry * 0.5, rz * 0.5), "Neck": (nk, 0, 0), "Head": (hd, 0, 0)}


def arms(lu, ll, ru, rl, ls=None, rs=None):
    """lu/ru = (rx, ry, rz) dos bracos superiores; ll/rl = rx dos antebracos."""
    p = {"LeftUpperArm": lu, "LeftLowerArm": (ll, 0, 0), "RightUpperArm": ru, "RightLowerArm": (rl, 0, 0)}
    return p


# ------------------------------------------------------------------ rugido
def roar():
    rest = merge(hips(), torso(0, 0, 0, 0), arms((0, 0, 0), 0, (0, 0, 0), 0), legs(0, 0, 0, 0))
    coil = merge(hips(-0.14, -0.05), torso(14, 16, 6, 16),
                 arms((22, 0, 6), -40, (22, 0, -6), -40), legs(-14, 26, -14, 26, 6))
    open_ = merge(hips(-0.02, -0.12), torso(-14, -36, -14, -44),
                  arms((10, 0, 47), -34, (10, 0, -47), -34), legs(-4, 8, -4, 8, 7))
    keys = {0: rest, 8: coil, 24: dict(open_, _i='SINE')}
    for i, f in enumerate(range(26, 44, 2)):          # tremor do rugido
        a = 1 if i % 2 == 0 else -1
        keys[f] = merge(open_, torso(-14, -36 + 4 * a, -14, -44 + 6 * a, ry=8 * a, rz=4 * -a),
                        arms((10 + 8 * a, 0, 47 + 5 * a), -34, (10 - 8 * a, 0, -47 - 5 * a), -34))
    keys[42]["_e"] = 'EASE_IN'
    keys[42]["_i"] = 'CUBIC'
    slam = merge(hips(-0.26, 0.18), torso(24, 26, 10, 26),
                 arms((-34, 0, 22), -55, (-34, 0, -22), -55), legs(-24, 44, -24, 44, 9))
    keys[48] = slam
    keys[54] = merge(slam, hips(-0.22, 0.14), torso(22, 24, 8, 22))
    keys[60] = rest
    return keys


# ------------------------------------------------------------------ investida
CROUCH_ARMS = arms((-78, 0, 14), -72, (34, 0, -18), -30)


def crouch(extra=0.0):
    return merge(hips(-0.26 - 0.03 * extra, 0.05), torso(14 + extra, 28 + 3 * extra, -12, -12),
                 CROUCH_ARMS, legs(-46, 56, 20, 36, 5))


def windup():
    rest = roar_rest()
    rise = merge(hips(0.05, -0.04), torso(-4, -8, 4, 6), arms((16, 0, 6), -10, (16, 0, -6), -10), legs(0, 0, 0, 0))
    keys = {0: rest, 5: rise, 18: crouch(0)}
    keys[18]["_i"] = 'EXPO'
    keys[18]["_e"] = 'EASE_OUT'
    keys[21] = crouch(1.0)
    keys[24] = crouch(0.2)
    keys[27] = crouch(1.0)
    return keys


def roar_rest():
    return merge(hips(), torso(0, 0, 0, 0), arms((0, 0, 0), 0, (0, 0, 0), 0), legs(0, 0, 0, 0))


def run_pose(t):
    ph = 2 * math.pi * t
    s, c = math.sin(ph), math.cos(ph)

    def leg(sg):          # sg = +1 perna esquerda, -1 direita
        sn = sg * s
        ul = -40 * math.cos(ph if sg > 0 else ph + math.pi) * 1.0
        # coxa vai e volta; joelho dobra na passada para a frente
        cs = math.cos(ph if sg > 0 else ph + math.pi)
        sn2 = math.sin(ph if sg > 0 else ph + math.pi)
        ll = 34 - 30 * sn2
        return ul, ll
    ul, ll = leg(1)
    ur, lr = leg(-1)
    p = merge(hips(-0.22 - 0.07 * math.cos(2 * ph), 0.08, ry=5 * s),
              torso(12, 24, -10, -14, ry=-8 * s, rz=3 * c),
              {"LeftUpperArm": (-78 + 4 * s, 0, 14), "LeftLowerArm": (-72, 0, 0),        # escudo a frente
               "RightUpperArm": (22 + 38 * s, 0, -14), "RightLowerArm": (-62, 0, 0)},   # martelo balancando
              legs(ul, ll, ur, lr, 4))
    return p


def run_keys():
    n = 18
    keys = {f: run_pose(f / n) for f in range(0, n, 2)}
    keys[n] = "loop"
    return keys


def recover():
    run = run_pose(0.12)
    skid = merge(hips(-0.30, -0.08, rx=-6), torso(-4, 4, -2, -10), arms((-52, 0, 20), -50, (-10, 0, -40), -20),
                 legs(-52, 18, 30, 24, 8))
    stumble = merge(hips(-0.20, 0.16), torso(28, 34, 12, 8), arms((-30, 0, 18), -40, (10, 0, -16), -20),
                    legs(-34, 28, 10, 20, 7))
    pant1 = merge(hips(-0.20, 0.10), torso(24, 34, 12, 14), arms((-12, 0, 14), -20, (12, 0, -14), -16), legs(-20, 24, 6, 14, 6))
    pant2 = merge(hips(-0.17, 0.08), torso(20, 28, 8, 10), arms((-8, 0, 12), -14, (10, 0, -12), -12), legs(-18, 22, 6, 12, 6))
    return {0: run, 6: dict(skid, _i='SINE'), 12: stumble, 16: pant1, 20: pant2, 24: pant1, 30: roar_rest()}


def build(A, arm):
    mk = lambda n, k, loop=False: A.make_action(arm, n, k, loop=loop, mirror_all=not SHIELD_LEFT)
    out = []
    a, l = mk("AN_Guardian_Roar", roar())
    out.append(dict(action=a, last=l, loop=False, preview=[0, 8, 24, 36, 48, 56], events={"summon_marks": 30, "slam": 48},
                    note="Rugido 2,0 s; apice com bracos abertos em 24-42; Sentinelas em 1,0 s (quadro 30)"))
    a, l = mk("AN_Guardian_ShieldCharge_Windup", windup())
    out.append(dict(action=a, last=l, loop=False, preview=[0, 5, 12, 18, 21, 27], note="Preparacao 0,9 s (27 quadros)"))
    a, l = mk("AN_Guardian_ShieldCharge_Run", run_keys(), True)
    out.append(dict(action=a, last=l, loop=True, preview=[0, 4, 8, 12, 16], note="Corrida em loop, ciclo 0,6 s"))
    a, l = mk("AN_Guardian_ShieldCharge_Recover", recover())
    out.append(dict(action=a, last=l, loop=False, preview=[0, 6, 12, 16, 22, 30], note="Recuperacao 1,0 s (30 quadros)"))
    return out
