"""Arqueiro Espectral (sem pernas, flutua): Idle, Glide, Shoot (sem arco), Hit, Death. Esqueleto sem ossos de perna.
Hips em loc (metros): o osso root nunca anima (sem root motion). Arco na mao ESQUERDA, corda puxada pela DIREITA."""
import math
from anim_lib import LR, merge, lerp_pose

FILL = 1.5
CAM = (0.62, -0.78, 0.22)
SHOOT_RELEASE = 20


def hp(y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0, s=None):
    d = {"rot": (rx, ry, rz), "loc": (0.0, y, z)}
    if s is not None:
        d["scale"] = s
    return {"Hips": d}


def torso(sp, ch, nk, hd, ry=0.0, rz=0.0):
    return {"Spine": (sp, ry * 0.4, rz * 0.5), "Chest": (ch, ry * 0.6, rz * 0.5), "Neck": (nk, 0, 0), "Head": (hd, ry * 0.0, rz * 0.0 + 0)}


def idle_pose(t):
    ph = 2 * math.pi * t
    s, c = math.sin(ph), math.cos(ph)
    sl = math.sin(ph - 0.9)
    return merge(hp(0.04 * s, 0, rx=2 * c, rz=2 * s), torso(3 + 1.5 * sl, 2, 2 - 2 * sl, 3 + 2 * sl, ry=3 * c),
                 {"LeftShoulder": (0, 0, 2 + sl), "RightShoulder": (0, 0, -2 - sl),
                  "LeftUpperArm": (-6 + 5 * sl, 0, 12 + 5 * sl), "RightUpperArm": (-6 + 5 * sl, 0, -12 - 5 * sl),
                  "LeftLowerArm": (-14 - 6 * sl, 0, 0), "RightLowerArm": (-14 - 6 * sl, 0, 0),
                  "LeftHand": (8 * sl, 0, 0), "RightHand": (8 * sl, 0, 0)})


def idle():
    keys = {f: idle_pose(f / 60) for f in range(0, 60, 5)}
    keys[60] = "loop"
    return keys


def glide_pose(t):
    ph = 2 * math.pi * t
    s, c = math.sin(ph), math.cos(ph)
    sl = math.sin(ph - 1.0)
    return merge(hp(0.015 * math.sin(2 * ph), 0.0, rx=14, rz=4 * s), torso(8, 8, -8, -10, ry=-4 * s, rz=3 * c),
                 {"LeftUpperArm": (22 + 6 * sl, 0, 20), "RightUpperArm": (22 + 6 * sl, 0, -20),
                  "LeftLowerArm": (-10, 0, 0), "RightLowerArm": (-10, 0, 0),
                  "LeftHand": (14, 0, 0), "RightHand": (14, 0, 0)})


def glide():
    keys = {f: glide_pose(f / 36) for f in range(0, 36, 3)}
    keys[36] = "loop"
    return keys


def shoot():
    idle0 = idle_pose(0)
    # preparacao 0-19: braco do arco (esq) estica a frente, braco da corda (dir) puxa ao rosto
    ready = merge(hp(0.0, -0.02, rx=-2, ry=14), torso(2, 6, 0, 6, ry=24),
                  {"LeftShoulder": (0, 0, 2), "LeftUpperArm": (-82, 14, 22), "LeftLowerArm": (-6, 0, 0), "LeftHand": (0, 0, 0),
                   "RightShoulder": (0, 0, -2), "RightUpperArm": (-62, -30, -48), "RightLowerArm": (-118, 0, 0), "RightHand": (0, 0, 0)})
    aim = merge(ready, hp(0.0, -0.05, rx=-3, ry=16), torso(1, 5, -2, 4, ry=28),
                {"RightUpperArm": (-66, -34, -52), "RightLowerArm": (-124, 0, 0)})
    anti = merge(hp(0.02, 0.0, rx=0), torso(-4, -6, 0, -4, ry=8),
                 {"LeftUpperArm": (-40, 6, 22), "LeftLowerArm": (-30, 0, 0), "RightUpperArm": (-30, -10, -26), "RightLowerArm": (-60, 0, 0)})
    snap = merge(hp(-0.01, 0.06, rx=4, ry=12), torso(4, 4, 2, 2, ry=22),
                 {"LeftUpperArm": (-86, 14, 20), "LeftLowerArm": (-4, 0, 0),
                  "RightUpperArm": (-30, -50, -70), "RightLowerArm": (-30, 0, 0), "RightHand": (20, 0, 0)})
    settle = merge(hp(0.0, 0.0, rx=2, ry=8), torso(5, 4, 4, 6, ry=12),
                   {"LeftUpperArm": (-50, 6, 20), "LeftLowerArm": (-14, 0, 0), "RightUpperArm": (-16, -20, -34), "RightLowerArm": (-34, 0, 0),
                    "RightHand": (6, 0, 0)})
    return {0: idle0, 5: dict(anti, _i='SINE'), 12: ready, 19: dict(aim, _i='CONSTANT'), SHOOT_RELEASE: dict(snap, _i='SINE'),
            24: settle, 34: merge(idle0, hp(0.0)), 44: idle0}


def hit():
    idle0 = idle_pose(0.0)
    back = merge(hp(0.03, -0.14, rx=-8, rz=5), torso(-8, -12, -8, -14, rz=-6),
                 {"LeftUpperArm": (14, 0, 62), "RightUpperArm": (10, 0, -58), "LeftLowerArm": (-30, 0, 0), "RightLowerArm": (-26, 0, 0),
                  "LeftHand": (-20, 0, 0), "RightHand": (-20, 0, 0)})
    return {0: idle0, 3: dict(back, _i='EXPO', _e='EASE_OUT'), 8: merge(back, hp(0.0, -0.08, rx=-4), torso(-4, -6, -4, -8)), 12: idle0}


def death():
    idle0 = idle_pose(0.0)
    jolt = merge(hp(0.04, -0.12, rx=-8, rz=6), torso(-8, -14, -10, -24),
                 {"LeftUpperArm": (14, 0, 66), "RightUpperArm": (10, 0, -62), "LeftLowerArm": (-30, 0, 0), "RightLowerArm": (-26, 0, 0)})
    sink1 = merge(hp(-0.25, -0.1, rx=-6, rz=10, s=0.85), torso(10, 14, 20, 36, rz=8),
                  {"LeftUpperArm": (-14, 0, 40), "RightUpperArm": (-12, 0, -34), "LeftLowerArm": (-34, 0, 0), "RightLowerArm": (-40, 0, 0)})
    end = merge(hp(-0.74, -0.04, rx=18, rz=14, s=0.12), torso(24, 26, 24, 30, rz=10),
                {"LeftUpperArm": (-30, 0, 18), "RightUpperArm": (-26, 0, -14), "LeftLowerArm": (-30, 0, 0), "RightLowerArm": (-34, 0, 0)})
    return {0: idle0, 4: dict(jolt, _i='EXPO', _e='EASE_OUT'), 12: dict(sink1, _i='CUBIC', _e='EASE_IN'), 20: dict(sink1, _i='SINE'), 28: dict(lerp_pose(sink1, end, 0.5), _i='SINE'), 36: dict(end, _i='QUAD')}


def build(A, arm):
    mk = lambda n, k, loop=False: A.make_action(arm, n, k, loop=loop)
    out = []
    a, l = mk("AN_GhostArcher_Idle", idle(), True)
    out.append(dict(action=a, last=l, loop=True, preview=[0, 15, 30, 45], note="Flutuar 2,0 s, sobe/desce 8 cm (+-4 cm no Hips)"))
    a, l = mk("AN_GhostArcher_Glide", glide(), True)
    out.append(dict(action=a, last=l, loop=True, preview=[0, 9, 18, 27], note="Deslizar em loop 1,2 s"))
    a, l = mk("AN_GhostArcher_Shoot", shoot())
    out.append(dict(action=a, last=l, loop=False, preview=[0, 5, 12, 19, 20, 24, 44],
                    events={"draw_start": 5, "aim_end": 19, "release": SHOOT_RELEASE}, note="Mira 0,6 s (0-19), disparo no quadro 20, recuperacao 0,8 s (20-44)"))
    a, l = mk("AN_GhostArcher_Hit", hit())
    out.append(dict(action=a, last=l, loop=False, preview=[0, 3, 8, 12], note="Hit 0,4 s"))
    a, l = A.make_action(arm, "AN_GhostArcher_Death", death(), allow_scale=True)
    out.append(dict(action=a, last=l, loop=False, preview=[0, 4, 12, 20, 36], note="Morte 1,2 s: afunda e encolhe"))
    return out
