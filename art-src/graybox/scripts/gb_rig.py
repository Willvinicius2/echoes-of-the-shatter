"""Rig_Humanoid_Chibi: esqueleto compartilhado pelos tres herois (heroi de 1,50 m, cabeca de 0,50 m).

Nomes iguais aos de HumanBodyBones do Unity (o mapeamento automatico do Humanoid reconhece todos), entao o
mesmo FBX serve como Generic (docs/04 secao 3.3) ou Humanoid, sem renomear. Coordenadas em espaco do
personagem (frente +Y, esquerda -X); make_armature gira 180 graus em Z (frente -Y no Blender, +Z no Unity).
"""
import bpy, math
from mathutils import Vector, Matrix
from gb_lib import TURN, export_fbx

RIG_NAME = "Rig_Humanoid_Chibi"

# Ossos que o Humanoid do Unity exige e os opcionais que este rig fornece.
HUMANOID_REQUIRED = ["Hips", "Spine", "Head",
                     "LeftUpperLeg", "RightUpperLeg", "LeftLowerLeg", "RightLowerLeg", "LeftFoot", "RightFoot",
                     "LeftUpperArm", "RightUpperArm", "LeftLowerArm", "RightLowerArm", "LeftHand", "RightHand"]
HUMANOID_OPTIONAL = ["Chest", "Neck", "LeftShoulder", "RightShoulder", "LeftToes", "RightToes"]
SOCKETS = ["socket_weapon_r", "socket_weapon_l", "socket_cast", "socket_head", "socket_fx_ground"]


def bone_defs():
    """(nome, pai, cabeca, cauda, deforma). Pose A (bracos a ~60 graus para baixo)."""
    B = []

    def add(n, p, h, t, d=True):
        B.append((n, p, tuple(h), tuple(t), d))
    add("root", None, (0, 0, 0), (0, 0, 0.15), False)
    add("Hips", "root", (0, 0, 0.46), (0, 0, 0.56))
    add("Spine", "Hips", (0, 0, 0.56), (0, 0, 0.70))
    add("Chest", "Spine", (0, 0, 0.70), (0, 0, 0.92))
    add("Neck", "Chest", (0, 0, 0.92), (0, 0, 1.00))
    add("Head", "Neck", (0, 0, 1.00), (0, 0, 1.50))
    for side, sx in (("Left", -1), ("Right", 1)):
        add(f"{side}Shoulder", "Chest", (sx * 0.04, 0, 0.86), (sx * 0.20, 0, 0.86))
        add(f"{side}UpperArm", f"{side}Shoulder", (sx * 0.20, 0, 0.86), (sx * 0.31, 0, 0.66))
        add(f"{side}LowerArm", f"{side}UpperArm", (sx * 0.31, 0, 0.66), (sx * 0.37, 0.03, 0.47))
        add(f"{side}Hand", f"{side}LowerArm", (sx * 0.37, 0.03, 0.47), (sx * 0.41, 0.05, 0.38))
        add(f"{side}UpperLeg", "Hips", (sx * 0.11, 0, 0.46), (sx * 0.11, 0, 0.26))
        add(f"{side}LowerLeg", f"{side}UpperLeg", (sx * 0.11, 0, 0.26), (sx * 0.11, 0, 0.08))
        add(f"{side}Foot", f"{side}LowerLeg", (sx * 0.11, 0, 0.08), (sx * 0.11, 0.10, 0.03))
        add(f"{side}Toes", f"{side}Foot", (sx * 0.11, 0.10, 0.03), (sx * 0.11, 0.17, 0.02))
    add("socket_weapon_r", "RightHand", (0.41, 0.05, 0.38), (0.41, 0.10, 0.38), False)
    add("socket_weapon_l", "LeftHand", (-0.41, 0.05, 0.38), (-0.41, 0.10, 0.38), False)
    add("socket_cast", "RightHand", (0.43, 0.20, 0.45), (0.43, 0.25, 0.45), False)
    add("socket_head", "Head", (0, 0, 1.50), (0, 0, 1.55), False)
    add("socket_fx_ground", "root", (0, 0, 0), (0, 0.10, 0), False)
    return B


def make_armature(coll, name=RIG_NAME, turn=True):
    arm = bpy.data.armatures.new(name)
    arm.display_type = 'OCTAHEDRAL'
    ob = bpy.data.objects.new(name, arm)
    coll.objects.link(ob)
    ob.show_in_front = True
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for n, p, h, t, d in bone_defs():
        b = arm.edit_bones.new(n)
        h, t = Vector(h), Vector(t)
        if turn:
            h, t = TURN @ h, TURN @ t
        b.head, b.tail = h, t
        b.roll = 0.0
        b.use_deform = d
        if p:
            b.parent = eb[p]
            b.use_connect = False
        eb[n] = b
    bpy.ops.object.mode_set(mode='OBJECT')
    ob.select_set(False)
    return ob


def bind(arm, mesh_obs):
    """Parenta as malhas ao esqueleto com modificador Armature (pesos ja vem dos grupos de vertices)."""
    for ob in mesh_obs:
        ob.parent = arm
        m = ob.modifiers.new("Armature", 'ARMATURE')
        m.object = arm
    return mesh_obs


def humanoid_check(bone_names):
    names = set(bone_names)
    return dict(required_missing=[n for n in HUMANOID_REQUIRED if n not in names],
                optional_present=[n for n in HUMANOID_OPTIONAL if n in names],
                sockets_present=[n for n in SOCKETS if n in names])


def export_fbx_rigged(arm, mesh_obs, path):
    """Exporta esqueleto + malhas com o no do esqueleto sem rotacao no FBX.

    O exportador do Blender so aplica o Apply Transform (bake_space_transform) em malhas; no armature a conversao
    de eixos vira Lcl Rotation (-90, 0, 0). Durante a exportacao o objeto do esqueleto fica girado +90 graus em X
    com os ossos contra-girados (posicoes no mundo iguais); depois tudo volta ao estado original.
    """
    R = Matrix.Rotation(math.radians(90), 4, 'X')

    def counter_rotate(m):
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='EDIT')
        for eb in arm.data.edit_bones:
            eb.transform(m)
        bpy.ops.object.mode_set(mode='OBJECT')
    saved = arm.matrix_world.copy()
    counter_rotate(R.inverted())
    arm.matrix_world = R @ saved
    for ob in mesh_obs:
        ob.matrix_parent_inverse = R.inverted()
    bpy.context.view_layer.update()
    export_fbx([arm] + list(mesh_obs), path)
    counter_rotate(R)
    arm.matrix_world = saved
    for ob in mesh_obs:
        ob.matrix_parent_inverse = Matrix.Identity(4)
    bpy.context.view_layer.update()
