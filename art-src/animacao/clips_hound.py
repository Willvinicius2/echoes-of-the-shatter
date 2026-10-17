"""Cao de Cinza (quadrupede, Rig_Quadruped_Simple): Idle, Walk, Run, Bite, Hit, Flee, Death. Sem IA: so keyframes de rotacao.

Convencao da anim_lib (espaco do personagem): X esquerda, Y cima, Z frente; rotacao nos eixos de repouso do esqueleto.
Pernas (UpperLeg): rx > 0 balanca para tras, rx < 0 para a frente; LowerLeg rx > 0 dobra. Pelvis/Spine/Chest/Neck/Head: rx > 0 inclina para a frente.
Tempos da mordida (skills.csv, skill.enemy.ash_bite): windup 0,3 s = 9 quadros, impacto 0,1 s = 3 quadros, recovery 0,4 s = 12 quadros
(30 fps): o bote chega ao pico no quadro 9 e a mordida acerta ate o 12; recuperacao 12-24. Sem root motion (root nunca anima).
Escala so na morte (allow_scale)."""
import math
from anim_lib import merge, lerp_pose

FILL = 1.55
CAM = (0.7, -0.72, 0.25)
BITE_WINDUP, BITE_IMPACT, BITE_END = 9, 12, 24


def pel(y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0, s=None):
    d = {"rot": (rx, ry, rz), "loc": (0.0, y, z)}
    if s is not None:
        d["scale"] = s
    return {"Pelvis": d}


def torso(sp=0.0, ch=0.0, nk=0.0, hd=0.0, ry=0.0, rz=0.0):
    return {"Spine": (sp, ry * 0.4, rz * 0.4), "Chest": (ch, ry * 0.6, rz * 0.5), "Neck": (nk, 0, 0), "Head": (hd, 0, 0)}


def tail(a=0.0, b=0.0, c=0.0, ry=0.0):
    return {"Tail1": (a, ry, 0), "Tail2": (b, ry * 1.2, 0), "Tail3": (c, ry * 1.4, 0)}


def leg(side, kind, sw, bend):
    """sw: balanco do UpperLeg (graus, + = para tras); bend: dobra do LowerLeg."""
    return {f"{side}{kind}UpperLeg": (sw, 0, 0), f"{side}{kind}LowerLeg": (bend, 0, 0), f"{side}{kind}Paw": (-bend * 0.4, 0, 0)}


def stride(t, phases, A, lift, direction=1):
    """Pose das 4 pernas no instante t (0..1) do ciclo. phases = (LF, RF, LH, RH). direction -1 inverte o ciclo (fuga de costas)."""
    out = {}
    legs = ((("Left", "Front"), phases[0]), (("Right", "Front"), phases[1]), (("Left", "Hind"), phases[2]), (("Right", "Hind"), phases[3]))
    for (side, kind), ph in legs:
        a = 2 * math.pi * (direction * t + ph)
        sw = -A * math.sin(a)                 # frente = negativo
        up = max(0.0, -math.cos(a))           # perna no ar (indo para a frente)
        out.update(leg(side, kind, sw, lift * up * (1.0 if kind == "Front" else 1.2)))
    return out


def idle_pose(t):
    ph = 2 * math.pi * t
    s, c = math.sin(ph), math.cos(ph)
    sl = math.sin(ph - 0.8)
    return merge(pel(0.006 * s, 0, rx=0.6 * c), torso(0.5 * c, 1.0 * s, -1.0 * s, 1.0 * sl, ry=2.0 * math.sin(ph * 0.5)),
                 tail(2 * sl, 3 * sl, 4 * sl, ry=7 * math.sin(ph * 0.5)))


def idle():
    keys = {f: idle_pose(f / 60) for f in range(0, 60, 5)}
    keys[60] = "loop"
    return keys


def walk_pose(t):
    ph = (0.0, 0.5, 0.75, 0.25)       # diagonais: LF com RH, RF com LH
    a = 2 * math.pi * t
    return merge(pel(0.012 * abs(math.sin(a * 2)) - 0.006, 0, rx=1.5 * math.sin(a * 2), rz=1.5 * math.sin(a)),
                 torso(1.2 * math.sin(a * 2), 1.0 * math.cos(a * 2), -1.5, 3 + 1.5 * math.sin(a * 2), ry=2.5 * math.sin(a), rz=-1.5 * math.sin(a)),
                 tail(4, 3 * math.sin(a), 5 * math.sin(a - 0.7), ry=14 * math.sin(a - 0.4)),
                 stride(t, ph, 22, 38))


def walk():
    keys = {f: walk_pose(f / 32) for f in range(0, 32, 2)}
    keys[32] = "loop"
    return keys


def run_pose(t, direction=1):
    ph = (0.0, 0.12, 0.5, 0.62)     # galope: pares de pernas quase juntos
    a = 2 * math.pi * t
    flex = math.sin(a)
    return merge(pel(0.03 * math.sin(a + 1.2), 0, rx=5.0 * direction + 4 * flex, rz=1.0 * math.sin(a * 2)),
                 torso(-5 * flex, -3 * flex, -4 + 2 * flex, 6 - 3 * flex, ry=1.5 * math.sin(a)),
                 tail(-8, -5 * math.sin(a), -9 * math.sin(a - 0.6), ry=8 * math.sin(a)),
                 stride(t, ph, 36 if direction > 0 else 29, 55, direction))


def run():
    keys = {f: run_pose(f / 20) for f in range(0, 20)}
    keys[20] = "loop"
    return keys


def flee():
    """Fuga: corrida para tras (o cao recua de frente para a ameaca): ciclo da corrida invertido, peito alto, cabeca erguida."""
    keys = {}
    for f in range(0, 24):
        p = run_pose(f / 24, direction=-1)
        keys[f] = merge(p, torso(-6, -8, -10, -6), pel(0, 0, rx=-8))
    keys[24] = "loop"
    return keys


def bite():
    idle0 = idle_pose(0)
    coil = merge(pel(-0.03, -0.07, rx=-4), torso(-3, -4, -10, -12), tail(6, 6, 6),
                 {"LeftFrontUpperLeg": (14, 0, 0), "RightFrontUpperLeg": (14, 0, 0), "LeftFrontLowerLeg": (18, 0, 0), "RightFrontLowerLeg": (18, 0, 0),
                  "LeftHindUpperLeg": (-12, 0, 0), "RightHindUpperLeg": (-12, 0, 0), "LeftHindLowerLeg": (22, 0, 0), "RightHindLowerLeg": (22, 0, 0)})
    snap = merge(pel(-0.02, 0.14, rx=12), torso(8, 12, 26, 36), tail(-8, -6, -6),
                 {"LeftFrontUpperLeg": (-34, 0, 0), "RightFrontUpperLeg": (-30, 0, 0), "LeftFrontLowerLeg": (6, 0, 0), "RightFrontLowerLeg": (6, 0, 0),
                  "LeftHindUpperLeg": (24, 0, 0), "RightHindUpperLeg": (24, 0, 0), "LeftHindLowerLeg": (-8, 0, 0), "RightHindLowerLeg": (-8, 0, 0)})
    rec = merge(pel(0.0, 0.05, rx=3), torso(2, 3, 6, 10), tail(2, 2, 2),
                {"LeftFrontUpperLeg": (-10, 0, 0), "RightFrontUpperLeg": (-8, 0, 0), "LeftHindUpperLeg": (6, 0, 0), "RightHindUpperLeg": (6, 0, 0)})
    return {0: idle0, 5: dict(coil, _i='SINE', _e='EASE_OUT'), BITE_WINDUP: dict(coil, _i='EXPO', _e='EASE_IN'),
            BITE_IMPACT: dict(snap, _i='SINE'), 16: dict(rec, _i='SINE', _e='EASE_OUT'), BITE_END: merge(idle0, pel(0, 0))}


def hit():
    idle0 = idle_pose(0)
    back = merge(pel(0.02, -0.09, rx=-6, rz=4), torso(-6, -9, -6, -14, rz=-5), tail(10, 8, 8, ry=12),
                 {"LeftFrontUpperLeg": (10, 0, 0), "RightFrontUpperLeg": (8, 0, 0), "LeftFrontLowerLeg": (10, 0, 0), "RightFrontLowerLeg": (10, 0, 0),
                  "LeftHindUpperLeg": (-6, 0, 0), "RightHindUpperLeg": (-6, 0, 0)})
    return {0: idle0, 3: dict(back, _i='EXPO', _e='EASE_OUT'), 8: merge(back, pel(0.0, -0.05, rx=-3), torso(-3, -5, -3, -8)), 12: idle0}


def death():
    idle0 = idle_pose(0)
    jolt = merge(pel(0.03, -0.1, rx=-8, rz=6), torso(-6, -12, -14, -22, rz=-6), tail(14, 12, 12),
                 {"LeftFrontUpperLeg": (14, 0, 0), "RightFrontUpperLeg": (12, 0, 0), "LeftFrontLowerLeg": (14, 0, 0), "RightFrontLowerLeg": (14, 0, 0)})
    fall = merge(pel(-0.18, -0.06, rx=4, rz=38, s=0.9), torso(8, 12, 14, 20, rz=12), tail(-10, -12, -14),
                 {"LeftFrontUpperLeg": (-30, 0, 24), "RightFrontUpperLeg": (-10, 0, -20), "LeftFrontLowerLeg": (54, 0, 0), "RightFrontLowerLeg": (50, 0, 0),
                  "LeftHindUpperLeg": (-26, 0, 30), "RightHindUpperLeg": (-14, 0, -18), "LeftHindLowerLeg": (58, 0, 0), "RightHindLowerLeg": (52, 0, 0)})
    end = merge(pel(-0.30, -0.04, rx=6, rz=62, s=0.12), torso(14, 18, 20, 26, rz=18), tail(-18, -20, -22),
                {"LeftFrontUpperLeg": (-40, 0, 30), "RightFrontUpperLeg": (-20, 0, -24), "LeftFrontLowerLeg": (70, 0, 0), "RightFrontLowerLeg": (66, 0, 0),
                 "LeftHindUpperLeg": (-36, 0, 34), "RightHindUpperLeg": (-24, 0, -22), "LeftHindLowerLeg": (74, 0, 0), "RightHindLowerLeg": (68, 0, 0)})
    return {0: idle0, 4: dict(jolt, _i='EXPO', _e='EASE_OUT'), 14: dict(fall, _i='CUBIC', _e='EASE_IN'), 24: dict(lerp_pose(fall, end, 0.5), _i='SINE'),
            36: dict(end, _i='QUAD')}


def build(A, arm):
    mk = lambda n, k, loop=False: A.make_action(arm, n, k, loop=loop)
    out = []
    a, l = mk("AN_AshHound_Idle", idle(), True)
    out.append(dict(action=a, last=l, loop=True, preview=[0, 15, 30, 45], note="Respirar e balancar o rabo, 2,0 s"))
    a, l = mk("AN_AshHound_Walk", walk(), True)
    out.append(dict(action=a, last=l, loop=True, preview=[0, 8, 16, 24], note="Andar em loop 1,07 s, diagonais, sem root motion"))
    a, l = mk("AN_AshHound_Run", run(), True)
    out.append(dict(action=a, last=l, loop=True, preview=[0, 5, 10, 15], note="Correr em loop 0,67 s (galope)"))
    a, l = mk("AN_AshHound_Bite", bite())
    out.append(dict(action=a, last=l, loop=False, preview=[0, 5, BITE_WINDUP, BITE_IMPACT, 16, 24],
                    events={"windup_end": BITE_WINDUP, "impact": BITE_IMPACT, "recovery_end": BITE_END},
                    note="skill.enemy.ash_bite: preparacao 0,3 s (0-9), bote/impacto 0,1 s (9-12), recuperacao 0,4 s (12-24)"))
    a, l = mk("AN_AshHound_Hit", hit())
    out.append(dict(action=a, last=l, loop=False, preview=[0, 3, 8, 12], note="Hit 0,4 s"))
    a, l = mk("AN_AshHound_Flee", flee(), True)
    out.append(dict(action=a, last=l, loop=True, preview=[0, 6, 12, 18], note="Fuga: corrida para tras, loop 0,8 s, sem root motion"))
    a, l = A.make_action(arm, "AN_AshHound_Death", death(), allow_scale=True)
    out.append(dict(action=a, last=l, loop=False, preview=[0, 4, 14, 24, 36], note="Morte 1,2 s: tomba de lado e encolhe (escala so aqui)"))
    return out
