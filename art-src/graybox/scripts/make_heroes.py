"""Gera Guerreiro, Arqueiro e Mago (graybox, 150 cm) com Rig_Humanoid_Chibi compartilhado."""
import bpy, sys, os, json
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
from gb_lib import *


# ---------------- Esqueleto compartilhado ----------------
def bone_defs():
    B = []  # (nome, pai, head, tail, deform)

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


def make_armature(name, coll):
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    coll.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for n, p, h, t, d in bone_defs():
        b = arm.edit_bones.new(n)
        b.head, b.tail = Vector(h), Vector(t)
        b.use_deform = d
        if p:
            b.parent = eb[p]
        eb[n] = b
    bpy.ops.object.mode_set(mode='OBJECT')
    ob.select_set(False)
    return ob


def finish(coll, builders):
    arm = make_armature("Rig_Humanoid_Chibi", coll)
    objs = []
    for bd in builders:
        ob = bd.build(coll)
        ob.parent = arm
        m = ob.modifiers.new("Armature", 'ARMATURE')
        m.object = arm
        objs.append(ob)
    return arm, objs


# ---------------- corpo base ----------------
def base_body(b, c, bulk=1.0):
    for side, sx in (("Left", -1), ("Right", 1)):
        b.add('box', (0.14, 0.26, 0.10), (sx * 0.11, 0.04, 0.05), c['boots'], bone=f"{side}Foot")
        b.limb((sx * 0.11, 0, 0.08), (sx * 0.11, 0, 0.26), 0.06, c['legs'], bone=f"{side}LowerLeg")
        b.limb((sx * 0.11, 0, 0.26), (sx * 0.11, 0, 0.46), 0.075, c['legs'], bone=f"{side}UpperLeg")
        b.limb((sx * 0.20, 0, 0.86), (sx * 0.31, 0, 0.66), 0.058 * bulk, c['arm'], bone=f"{side}UpperArm")
        b.limb((sx * 0.31, 0, 0.66), (sx * 0.37, 0.03, 0.47), 0.052 * bulk, c['arm'], bone=f"{side}LowerArm")
        b.add('sph', (0.11, 0.11, 0.11), (sx * 0.41, 0.05, 0.38), c['hand'], bone=f"{side}Hand", seg=6)
    b.add('box', (0.34, 0.22, 0.14), (0, 0, 0.50), c['pelvis'], bone="Hips")
    b.add('box', (0.36, 0.23, 0.12), (0, 0, 0.62), c['torso'], bone="Spine")
    b.add('box', (0.44 * bulk, 0.26, 0.24), (0, 0, 0.82), c['torso'], bone="Chest")
    b.add('cyl', (0.12, 0.12, 0.08), (0, 0, 0.96), c['skin'], bone="Neck", seg=6)


def warrior(coll):
    c = dict(boots='#4A3A2E', legs='#5A5F6A', arm='#9AA0AA', hand='#7A5230', pelvis='#C02A22',
             torso='#9AA0AA', skin='#E0B090')
    b = Builder("SK_Warrior_Body")
    base_body(b, c, bulk=1.1)
    b.add('box', (0.46, 0.04, 0.22), (0, 0.145, 0.78), '#C02A22', bone="Chest")           # tabardo
    b.add('box', (0.40, 0.25, 0.04), (0, 0, 0.58), '#D9A441', bone="Spine")               # cinto
    for sx, s in ((-1, "Left"), (1, "Right")):
        b.add('sph', (0.18, 0.16, 0.14), (sx * 0.22, 0, 0.88), '#9AA0AA', bone=f"{s}Shoulder", seg=6)
    b.add('sph', (0.46, 0.44, 0.44), (0, 0, 1.22), '#9AA0AA', bone="Head")                # elmo
    b.add('box', (0.32, 0.05, 0.07), (0, 0.205, 1.22), '#2A2A32', bone="Head")            # viseira
    b.add('box', (0.07, 0.30, 0.10), (0, -0.02, 1.45), '#C02A22', bone="Head")            # pluma (topo 1.50)
    sword = Builder("SM_Warrior_Sword")
    h = Vector((0.41, 0.05, 0.38))
    d = Vector((0, 0.6, 0.8)).normalized()
    R = aim((0, 0, 0), d)
    sword.add('cyl', (0.04, 0.04, 0.12), h + d * 0.04, '#7A5230', rot=R, bone="RightHand", seg=6)
    sword.add('box', (0.22, 0.05, 0.04), h + d * 0.10, '#D9A441', rot=R, bone="RightHand")
    sword.add('box', (0.09, 0.025, 0.52), h + d * 0.38, '#D8DCE4', rot=R, bone="RightHand")
    shield = Builder("SM_Warrior_Shield")
    shield.add('box', (0.07, 0.46, 0.62), (-0.50, 0.10, 0.55), '#C02A22', bone="LeftHand")
    shield.add('box', (0.09, 0.40, 0.56), (-0.52, 0.10, 0.55), '#9AA0AA', bone="LeftHand")
    shield.add('sph', (0.14, 0.14, 0.14), (-0.55, 0.10, 0.55), '#D9A441', bone="LeftHand", seg=6)
    return finish(coll, [b, sword, shield])


def archer(coll):
    c = dict(boots='#5A3A24', legs='#5A4030', arm='#2F7A32', hand='#7A5230', pelvis='#7A5230',
             torso='#2F7A32', skin='#E0B090')
    b = Builder("SK_Archer_Body")
    base_body(b, c, bulk=0.95)
    b.add('box', (0.40, 0.25, 0.04), (0, 0, 0.58), '#7A5230', bone="Spine")
    b.add('box', (0.46, 0.27, 0.10), (0, 0, 0.88), '#5FD04A', bone="Chest")               # gola
    b.add('sph', (0.38, 0.36, 0.38), (0, 0.04, 1.19), '#E0B090', bone="Head")            # rosto
    b.add('sph', (0.50, 0.46, 0.46), (0, -0.04, 1.23), '#5FD04A', bone="Head")           # capuz
    b.add('cyl', (0.34, 0.34, 0.22), (0, -0.08, 1.39), '#5FD04A', bone="Head", taper=0.15, seg=6)
    b.add('box', (0.30, 0.04, 0.12), (0, 0.205, 1.20), '#2A2A32', bone="Head")           # sombra do rosto
    bow = Builder("SM_Archer_Bow")
    pts = [(-0.44, 0.06, 0.00), (-0.44, 0.18, 0.22), (-0.44, 0.12, 0.42), (-0.44, 0.18, 0.62), (-0.44, 0.06, 0.84)]
    for a, bb in zip(pts[:-1], pts[1:]):
        bow.limb(a, bb, 0.022, '#7A5230', bone="LeftHand", seg=6)
    bow.add('box', (0.012, 0.012, 0.84), (-0.44, 0.04, 0.42), '#E8E0D0', bone="LeftHand")
    quiver = Builder("SM_Archer_Quiver")
    quiver.add('cyl', (0.13, 0.13, 0.46), (0.10, -0.18, 0.88), '#7A5230', rot=(0, 15, 0), bone="Chest", seg=6)
    for i in (-1, 0, 1):
        quiver.add('box', (0.03, 0.03, 0.10), (0.17 + i * 0.03, -0.18, 1.14), '#E8E0D0', bone="Chest")
    return finish(coll, [b, bow, quiver])


def mage(coll):
    c = dict(boots='#5A3A24', legs='#2E3A8C', arm='#2E3A8C', hand='#2A2A32', pelvis='#2E3A8C',
             torso='#2E3A8C', skin='#E0B090')
    b = Builder("SK_Mage_Body")
    base_body(b, c, bulk=1.0)
    b.add('cyl', (0.52, 0.46, 0.50), (0, 0, 0.37), '#2E3A8C', bone="Hips", taper=0.62)    # saia do manto
    b.add('box', (0.30, 0.03, 0.50), (0, 0.235, 0.35), '#D9A441', bone="Hips")           # faixa dourada
    b.add('box', (0.40, 0.25, 0.04), (0, 0, 0.58), '#7A5230', bone="Spine")              # cinto
    b.add('box', (0.50, 0.30, 0.08), (0, 0, 0.90), '#C8B890', bone="Chest")              # gola
    b.add('sph', (0.34, 0.30, 0.34), (0, 0.10, 1.18), '#E0B090', bone="Head")            # rosto
    b.add('sph', (0.52, 0.50, 0.48), (0, -0.02, 1.20), '#2E3A8C', bone="Head")           # capuz
    b.add('cyl', (0.34, 0.34, 0.18), (0, -0.04, 1.41), '#2E3A8C', bone="Head", taper=0.12, seg=6)
    b.add('box', (0.30, 0.04, 0.12), (0, 0.215, 1.20), '#1A1A2A', bone="Head")
    staff = Builder("SM_Mage_Staff")
    sx, sy = 0.43, 0.08
    staff.add('cyl', (0.05, 0.05, 1.55), (sx, sy, 0.775), '#7A5230', bone="RightHand", seg=6)
    staff.add('box', (0.12, 0.12, 0.05), (sx, sy, 1.57), '#D9A441', bone="RightHand")
    for dx, dy in ((0.07, 0), (-0.07, 0), (0, 0.07), (0, -0.07)):
        staff.add('box', (0.03, 0.03, 0.24), (sx + dx, sy + dy, 1.68), '#D9A441', bone="RightHand")
    staff.add('sph', (0.16, 0.16, 0.34), (sx, sy, 1.70), '#4A9CF0', bone="RightHand", seg=4, emit=True, matname="GB_Crystal")
    return finish(coll, [b, staff])


report = {}
reset()
x_off = {"Warrior": -2.0, "Archer": 0.0, "Mage": 2.0}
for fn, key in ((warrior, "Warrior"), (archer, "Archer"), (mage, "Mage")):
    coll = new_coll("SK_" + key)
    arm, objs = fn(coll)
    arm.name = "Rig_Humanoid_Chibi"
    body = objs[0]
    mn, mx = bbox([body])
    mn2, mx2 = bbox(objs)
    report[key] = dict(body_h=round(mx.z - mn.z, 3), body_foot_z=round(mn.z, 3), body_w=round(mx.x - mn.x, 3),
                       all_w=round(mx2.x - mn2.x, 3), all_h=round(mx2.z - mn2.z, 3),
                       tris={o.name: tris(o) for o in objs}, bones=len(arm.data.bones),
                       mats=len({m.name for o in objs for m in o.data.materials}))
    export_fbx([arm] + objs, f"{FBX}/SK_{key}.fbx")
    arm.location = (x_off[key] * 0.7071, -x_off[key] * 0.7071, 0)
    bpy.context.view_layer.update()

# previa
fl = Builder("Preview_Floor")
fl.add('box', (8, 4, 0.05), (0, 0, -0.025), '#6A5A55')
fo = fl.build()
setup_render(1600, 800)
cam = game_camera((0, 0, 0.6), 14, ortho_scale=6.0)
bpy.ops.object.light_add(type='SUN', location=(3, 3, 6))
render(f"{PREV}/heroes_lineup.png")
for r in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
    r.location = (r.location.x * 1.4142 * 0.7071 * 0 + (x_off[{'Rig_Humanoid_Chibi': 'Warrior', 'Rig_Humanoid_Chibi.001': 'Archer', 'Rig_Humanoid_Chibi.002': 'Mage'}[r.name]]), 0, 0)
bpy.data.objects.remove(cam)
game_camera((0, 0, 0.8), 14, ortho_scale=5.2, yaw=0, pitch=-12)
render(f"{PREV}/heroes_front.png")
fo.hide_render = True
fo.hide_viewport = True
save_blend(f"{ROOT}/heroes_graybox.blend")
json.dump(report, open(f"{PREV}/_heroes_report.json", "w"), indent=1)
print("REPORT", json.dumps(report))
