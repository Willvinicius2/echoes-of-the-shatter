"""Gera Guerreiro, Arqueiro e Mago (graybox, 150 cm) sobre o Rig_Humanoid_Chibi compartilhado.

Skinning rigido por peca: cada primitiva pesa 1,0 num unico osso. Silhuetas das folhas 02 a 04
(docs/arte/referencias-geracao/aprovadas): Guerreiro = elmo dourado + pluma + martelo de bloco + escudo largo;
Arqueiro = capuz com mascara de bico de osso + manto de penas + arco de osso; Mago = capuz pontudo com rosto
visivel + cajado com cristal num anel dourado (nunca lanterna).
"""
import bpy, sys, os, json, math
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gb_lib import *
from gb_rig import *

GOLD = '#D9A441'
HAND_R = Vector((0.41, 0.05, 0.38))


def base_body(b, c, bulk=1.0, hand=0.12):
    for side, sx in (("Left", -1), ("Right", 1)):
        b.add('box', (0.14, 0.17, 0.10), (sx * 0.11, 0.0, 0.05), c['boots'], bone=f"{side}Foot")
        b.add('box', (0.14, 0.10, 0.08), (sx * 0.11, 0.13, 0.04), c['boots'], bone=f"{side}Toes")
        b.limb((sx * 0.11, 0, 0.08), (sx * 0.11, 0, 0.26), 0.06, c['legs'], bone=f"{side}LowerLeg")
        b.limb((sx * 0.11, 0, 0.26), (sx * 0.11, 0, 0.46), 0.075, c['legs'], bone=f"{side}UpperLeg")
        b.limb((sx * 0.20, 0, 0.86), (sx * 0.31, 0, 0.66), 0.058 * bulk, c['arm'], bone=f"{side}UpperArm")
        b.limb((sx * 0.31, 0, 0.66), (sx * 0.37, 0.03, 0.47), 0.052 * bulk, c['arm'], bone=f"{side}LowerArm")
        b.add('sph', (hand, hand, hand * 1.1), (sx * 0.40, 0.045, 0.405), c['hand'], bone=f"{side}Hand", seg=6)
    b.add('box', (0.34, 0.22, 0.14), (0, 0, 0.50), c['pelvis'], bone="Hips")
    b.add('box', (0.36, 0.23, 0.12), (0, 0, 0.62), c['torso'], bone="Spine")
    b.add('box', (0.44 * bulk, 0.26, 0.24), (0, 0, 0.82), c['torso'], bone="Chest")
    b.add('cyl', (0.12, 0.12, 0.08), (0, 0, 0.96), c.get('neck', c['skin']), bone="Neck", seg=6)


def cuffs(b, color, r=0.064):
    for side, sx in (("Left", -1), ("Right", 1)):
        b.limb((sx * 0.355, 0.025, 0.525), (sx * 0.366, 0.031, 0.49), r, color, bone=f"{side}LowerArm", seg=8)


def warrior(coll):
    armor, armor_l, red, plume = '#4E5360', '#6E7480', '#C02A22', '#E0301E'
    c = dict(boots=armor, legs=armor, arm=armor, hand=armor_l, pelvis=red, torso=armor, skin='#E0B090', neck='#2A2A32')
    b = Builder("SK_Warrior_Body")
    base_body(b, c, bulk=1.1, hand=0.13)
    for sx, s in ((-1, "Left"), (1, "Right")):
        b.add('box', (0.12, 0.06, 0.09), (sx * 0.11, 0.07, 0.27), GOLD, bone=f"{s}LowerLeg")       # joelheira
        b.add('cyl', (0.15, 0.15, 0.03), (sx * 0.11, 0, 0.11), GOLD, bone=f"{s}LowerLeg", seg=8)  # aro da bota
        b.add('sph', (0.23, 0.21, 0.17), (sx * 0.23, 0, 0.90), armor_l, bone=f"{s}Shoulder", seg=8)  # ombreira
        b.add('cyl', (0.24, 0.22, 0.03), (sx * 0.23, 0, 0.855), GOLD, bone=f"{s}Shoulder", seg=8)
    cuffs(b, GOLD)
    b.add('box', (0.30, 0.04, 0.36), (0, 0.13, 0.35), red, bone="Hips")                       # tabardo frente
    b.add('box', (0.30, 0.04, 0.42), (0, -0.13, 0.33), red, bone="Hips")                      # tabardo costas
    b.add('box', (0.42, 0.27, 0.05), (0, 0, 0.58), GOLD, bone="Spine")                        # cinto
    b.add('cyl', (0.09, 0.09, 0.03), (0, 0.145, 0.58), GOLD, rot=(90, 0, 0), bone="Spine", seg=8)
    b.add('box', (0.30, 0.04, 0.22), (0, 0.145, 0.80), red, bone="Chest")                     # tabardo peito
    b.add('cyl', (0.08, 0.08, 0.02), (0, 0.17, 0.80), GOLD, rot=(90, 0, 0), bone="Chest", seg=8)
    b.add('box', (0.46, 0.28, 0.04), (0, 0, 0.93), GOLD, bone="Chest")                        # gorjal
    b.add('sph', (0.46, 0.44, 0.44), (0, 0, 1.22), GOLD, bone="Head")                         # elmo dourado
    b.add('box', (0.30, 0.05, 0.05), (0, 0.205, 1.22), '#161117', bone="Head")                # viseira em T
    b.add('box', (0.05, 0.05, 0.17), (0, 0.208, 1.15), '#161117', bone="Head")
    b.add('box', (0.06, 0.40, 0.05), (0, 0, 1.43), '#A87A2E', bone="Head")                    # crista do elmo
    b.add('box', (0.07, 0.22, 0.09), (0, -0.02, 1.455), plume, bone="Head")                   # pluma (topo 1,50)
    b.add('box', (0.07, 0.24, 0.07), (0, -0.21, 1.37), plume, rot=(35, 0, 0), bone="Head")
    # martelo de bloco de pedra (mao direita, cabeca para cima)
    hammer = Builder("SK_Warrior_Hammer")
    d = Vector((0.10, 0.12, 1.0)).normalized()
    R = aim((0, 0, 0), d)
    hammer.limb(HAND_R - d * 0.20, HAND_R + d * 0.50, 0.026, '#8A2A2A', bone="RightHand", seg=6)
    hammer.add('bbox', (0.06, 0.06, 0.06), HAND_R - d * 0.22, GOLD, rot=R, bone="RightHand", bev=0.01)
    hammer.add('bbox', (0.30, 0.22, 0.24), HAND_R + d * 0.58, '#8E8A96', rot=R, bone="RightHand", bev=0.03)
    hammer.add('box', (0.10, 0.235, 0.255), HAND_R + d * 0.58, GOLD, rot=R, bone="RightHand")
    # escudo largo com pedra e aro dourado (mao esquerda, virado 30 graus para fora)
    shield = Builder("SK_Warrior_Shield")
    shield.xf = Matrix.Translation((-0.42, 0.17, 0.56)) @ Matrix.Rotation(math.radians(30), 4, 'Z')
    shield.add('bbox', (0.50, 0.05, 0.50), (0, 0, 0.06), GOLD, bone="LeftHand", bev=0.02)
    shield.add('bbox', (0.354, 0.05, 0.354), (0, 0, -0.12), GOLD, rot=(0, 45, 0), bone="LeftHand", bev=0.02)
    shield.add('box', (0.42, 0.06, 0.42), (0, 0.006, 0.07), '#8E8A96', bone="LeftHand")
    shield.add('box', (0.29, 0.06, 0.29), (0, 0.006, -0.11), '#8E8A96', rot=(0, 45, 0), bone="LeftHand")
    shield.add('sph', (0.14, 0.08, 0.14), (0, 0.045, 0.04), GOLD, bone="LeftHand", seg=8)
    shield.xf = None
    return [b, hammer, shield]


def archer(coll):
    dark, mantle, hood, bone_c = '#3A2E28', '#3E5A2E', '#5FD04A', '#E8DCC0'
    c = dict(boots='#6A4A2E', legs=dark, arm=dark, hand='#5A3A24', pelvis=mantle, torso=dark, skin='#E0B090')
    b = Builder("SK_Archer_Body")
    base_body(b, c, bulk=0.95)
    for sx, s in ((-1, "Left"), (1, "Right")):
        b.add('box', (0.11, 0.06, 0.10), (sx * 0.11, 0.07, 0.27), '#D8CCB0', bone=f"{s}LowerLeg")  # joelheira de osso
    cuffs(b, '#6A4A2E', r=0.058)
    b.add('cyl', (0.40, 0.30, 0.26), (0, 0, 0.40), mantle, taper=0.8, bone="Hips")             # tunica
    b.add('box', (0.40, 0.26, 0.05), (0, 0, 0.58), '#6A4A2E', bone="Spine")                    # cinto
    b.add('box', (0.10, 0.06, 0.10), (-0.13, 0.14, 0.54), '#5A3A24', bone="Spine")             # bolsa
    b.add('cyl', (0.62, 0.50, 0.30), (0, -0.01, 0.80), mantle, taper=0.45, bone="Chest")       # manto de penas
    b.add('cyl', (0.66, 0.54, 0.08), (0, -0.01, 0.66), '#A08A5A', taper=0.92, bone="Chest")   # franja das penas
    b.add('box', (0.32, 0.30, 0.07), (0, 0.03, 1.03), '#2E4424', bone="Neck")                 # lenco
    b.add('sph', (0.36, 0.34, 0.36), (0, 0.04, 1.19), '#E0B090', bone="Head")                 # rosto
    b.add('sph', (0.50, 0.46, 0.46), (0, -0.03, 1.22), hood, bone="Head")                     # capuz
    b.add('cyl', (0.32, 0.32, 0.22), (0, -0.08, 1.39), hood, bone="Head", taper=0.12, seg=6)  # ponta (topo 1,50)
    b.add('sph', (0.30, 0.12, 0.26), (0, 0.17, 1.21), bone_c, bone="Head")                    # mascara de osso
    b.limb((0, 0.21, 1.17), (0, 0.33, 1.07), 0.05, bone_c, bone="Head", taper=0.15, seg=4)   # bico
    for sx in (-1, 1):
        b.add('box', (0.05, 0.03, 0.025), (sx * 0.06, 0.225, 1.235), '#9AFF6A', bone="Head", emit=True)
    bow = Builder("SK_Archer_Bow")
    pts = [(-0.44, 0.06, 0.02), (-0.44, 0.19, 0.20), (-0.44, 0.13, 0.40), (-0.44, 0.19, 0.60), (-0.44, 0.06, 0.78)]
    for a, bb in zip(pts[:-1], pts[1:]):
        bow.limb(a, bb, 0.024, '#D8CCB0', bone="LeftHand", seg=6)
    bow.add('box', (0.05, 0.05, 0.11), (-0.44, 0.13, 0.40), '#6A4A2E', bone="LeftHand")       # empunhadura
    bow.add('box', (0.012, 0.012, 0.76), (-0.44, 0.06, 0.40), '#E8E0D0', bone="LeftHand")     # corda
    quiver = Builder("SK_Archer_Quiver")
    quiver.add('cyl', (0.13, 0.13, 0.46), (0.10, -0.19, 0.88), '#6A4A2E', rot=(0, 15, 0), bone="Chest", seg=6)
    for i in (-1, 0, 1):
        quiver.add('box', (0.035, 0.035, 0.10), (0.165 + i * 0.035, -0.19, 1.15), hood, bone="Chest")
    return [b, bow, quiver]


def mage(coll):
    navy, navy_l, cream = '#2E3A8C', '#3E4FA8', '#C8B890'
    c = dict(boots='#5A3A24', legs='#3A2E28', arm=navy, hand='#2A2A32', pelvis=navy, torso=navy, skin='#E0B090')
    b = Builder("SK_Mage_Body")
    base_body(b, c, bulk=1.0)
    cuffs(b, cream, r=0.062)
    b.add('cyl', (0.52, 0.46, 0.50), (0, 0, 0.37), navy, bone="Hips", taper=0.62)             # saia do manto
    b.add('cyl', (0.535, 0.475, 0.04), (0, 0, 0.14), GOLD, bone="Hips", taper=0.97)           # barra dourada
    b.add('box', (0.10, 0.03, 0.48), (0, 0.196, 0.37), cream, rot=(9.9, 0, 0), bone="Hips")   # frente do manto
    b.add('box', (0.40, 0.25, 0.05), (0, 0, 0.60), '#6A4A2E', bone="Spine")                   # cinto
    b.add('bbox', (0.14, 0.06, 0.17), (-0.20, 0.10, 0.52), '#7A5230', bone="Hips", bev=0.015)  # livro na bolsa
    b.add('box', (0.04, 0.02, 0.04), (-0.20, 0.135, 0.53), GOLD, bone="Hips")
    b.add('box', (0.06, 0.03, 0.22), (0, 0.135, 0.80), GOLD, bone="Chest")                    # faixa do peito
    b.add('box', (0.48, 0.30, 0.08), (0, 0, 0.91), navy_l, bone="Chest")                      # cachecol
    b.add('sph', (0.34, 0.30, 0.34), (0, 0.09, 1.17), '#E0B090', bone="Head")                 # rosto visivel
    for sx in (-1, 1):
        b.add('box', (0.04, 0.02, 0.045), (sx * 0.065, 0.236, 1.185), '#1A1A2A', bone="Head")  # olhos
    b.add('box', (0.24, 0.06, 0.06), (0, 0.185, 1.285), '#6A4428', bone="Head")               # franja do cabelo
    b.add('sph', (0.52, 0.50, 0.50), (0, -0.06, 1.21), navy, bone="Head")                     # capuz
    b.add('ring', (0.38, 0.38, 0.08), (0, 0.12, 1.18), navy_l, rot=(90, 0, 0), bone="Head", seg=10, tube=0.12)  # borda do capuz
    b.add('cyl', (0.34, 0.34, 0.18), (0, -0.06, 1.41), navy, bone="Head", taper=0.12, seg=6)  # ponta (topo 1,50)
    staff = Builder("SK_Mage_Staff")
    sp = [(0.43, 0.08, 0.02), (0.445, 0.08, 0.45), (0.425, 0.085, 0.90), (0.44, 0.08, 1.38)]
    for a, bb in zip(sp[:-1], sp[1:]):
        staff.limb(a, bb, 0.024, '#7A5230', bone="RightHand", seg=6)
    top = Vector((0.44, 0.08, 1.55))
    staff.add('bbox', (0.07, 0.07, 0.07), (0.44, 0.08, 1.39), GOLD, bone="RightHand", bev=0.01)
    staff.add('ring', (0.30, 0.30, 0.30), top, GOLD, rot=(90, 0, 0), bone="RightHand", seg=12, tube=0.10)
    for a in (-50, 50):
        u = Vector((math.sin(math.radians(a)), 0, math.cos(math.radians(a))))
        staff.limb(top + u * 0.14, top + u * 0.21, 0.022, GOLD, bone="RightHand", taper=0.1, seg=4)
    staff.add('sph', (0.12, 0.12, 0.24), top, '#4A9CF0', bone="RightHand", seg=4, emit=True)   # cristal azul
    return [b, staff]


report = dict(version=version_info(), heroes={})
reset()
for fn, key in ((warrior, "Warrior"), (archer, "Archer"), (mage, "Mage")):
    coll = new_coll("SK_" + key)
    arm = make_armature(coll)
    objs = bind(arm, [bd.build(coll, turn=True) for bd in fn(coll)])
    body = objs[0]
    mn, mx = bbox([body])
    mn2, mx2 = bbox(objs)
    report["heroes"][key] = dict(
        file=f"fbx/SK_{key}.fbx", body_height=round(mx.z - mn.z, 3), foot_z=round(mn.z, 3) + 0.0,
        unity_body=unity_bounds(mn, mx), unity_all=unity_bounds(mn2, mx2),
        width_over_height=round((mx2.x - mn2.x) / (mx.z - mn.z), 2),
        tris={o.name: tris(o) for o in objs}, tris_total=sum(tris(o) for o in objs),
        bones=len(arm.data.bones), materials=sorted({m.name for o in objs for m in o.data.materials}),
        vertex_groups={o.name: [g.name for g in o.vertex_groups] for o in objs})
    export_fbx_rigged(arm, objs, f"{FBX}/SK_{key}.fbx")
    arm.name = f"{RIG_NAME}_{key}"
    arm.data.name = f"{RIG_NAME}_{key}"

# previas: herois virados para a camera (rotacao so do objeto, nao exportada)
x_off = {"Warrior": -1.6, "Archer": 0.0, "Mage": 1.6}
right = Vector((-0.7071, 0.7071, 0))          # direita da tela com a camera do jogo
fl = Builder("Preview_Floor")
fl.add('box', (12, 12, 0.05), (0, 0, -0.025), '#6A5A55')
fo = fl.build()
setup_render(1600, 900)
for key, x in x_off.items():
    a = bpy.data.objects[f"{RIG_NAME}_{key}"]
    a.location = right * x
    a.rotation_euler = (0, 0, math.pi)
cam = game_camera((0, 0, 0.6), 14, ortho_scale=5.6)
render(f"{PREV}/heroes_lineup.png")
for key, x in x_off.items():
    bpy.data.objects[f"{RIG_NAME}_{key}"].location = (-x, 0, 0)
bpy.data.objects.remove(cam)
cam = game_camera((0, 0, 0.82), 14, ortho_scale=5.2, yaw=0, pitch=-8)
render(f"{PREV}/heroes_front.png")
bpy.data.objects.remove(cam)
for key, x in x_off.items():
    bpy.data.objects[f"{RIG_NAME}_{key}"].rotation_euler = (0, 0, 0)
cam = game_camera((0, 0, 0.82), 14, ortho_scale=5.2, yaw=0, pitch=-8)
render(f"{PREV}/heroes_back.png")
bpy.data.objects.remove(cam)
for key in x_off:
    a = bpy.data.objects[f"{RIG_NAME}_{key}"]
    a.location = (0, 0, 0)
    a.rotation_euler = (0, 0, 0)
fo.hide_render = True
fo.hide_viewport = True
save_blend(f"{ROOT}/heroes_graybox.blend")
json.dump(report, open(f"{PREV}/_heroes_report.json", "w"), indent=1)
print("REPORT", json.dumps({k: (v["body_height"], v["tris_total"]) for k, v in report["heroes"].items()}))
