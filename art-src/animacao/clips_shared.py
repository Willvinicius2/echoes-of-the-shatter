"""Clipes compartilhados (rotacao pura: servem em qualquer proporcao do Rig_Humanoid_Chibi)."""
import math
from anim_lib import LR, merge, ease


def stun_pose(t):
    """Tonto: cabeca girando em circulo, tronco bambo, bracos soltos. t em [0,1) = um ciclo de 0,8 s."""
    ph = 2 * math.pi * t
    s, c = math.sin(ph), math.cos(ph)
    s2 = math.sin(ph + 1.2)
    sl = math.sin(ph - 1.0)     # atraso dos bracos em relacao a cabeca
    cl = math.cos(ph - 1.0)
    p = {
        "Hips": (4 + 2 * c, 6 * s, -5 * s),
        "Spine": (8 + 3 * c, -4 * s, 5 * s),
        "Chest": (6, -5 * s, 6 * math.sin(ph + 0.6)),
        "Neck": (6 + 7 * c, 16 * s, 8 * s2),
        "Head": (12 + 10 * c, 22 * s, 18 * math.sin(ph + 1.6)),
    }
    # bracos soltos, balancando com atraso; cotovelos frouxos
    p["LeftShoulder"] = (0, 0, 4 + 3 * sl)
    p["RightShoulder"] = (0, 0, -4 - 3 * sl)
    p["LeftUpperArm"] = (-12 + 18 * sl, 8 * cl, 16 + 12 * cl)
    p["RightUpperArm"] = (-12 - 18 * sl, -8 * cl, -16 - 12 * cl)
    p["LeftLowerArm"] = (-18 - 14 * sl, 0, 4)
    p["RightLowerArm"] = (-18 + 14 * sl, 0, -4)
    p["LeftHand"] = (10 * cl, 0, 0)
    p["RightHand"] = (-10 * cl, 0, 0)
    # joelhos moles, peso passando de um pe ao outro
    p["LeftUpperLeg"] = (-8 + 5 * s, 0, 3)
    p["RightUpperLeg"] = (-8 - 5 * s, 0, -3)
    p["LeftLowerLeg"] = (16 - 6 * s, 0, 0)
    p["RightLowerLeg"] = (16 + 6 * s, 0, 0)
    p["LeftFoot"] = (-8, 0, 0)
    p["RightFoot"] = (-8, 0, 0)
    return p


def build(A, arm):
    make_action = A.make_action
    n = 24
    keys = {}
    for f in range(0, n, 2):
        keys[f] = stun_pose(f / n)
    keys[n] = "loop"
    act, last = make_action(arm, "AN_Shared_Stun", keys, loop=True)
    return [dict(action=act, last=last, loop=True, preview=[0, 6, 12, 18], note="Stun 0,8 s, loop")]
