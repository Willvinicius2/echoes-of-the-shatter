"""Previas das luvas (EEVEE 1024, um render por vez). Rodar: blender -b -P luvas_previas.py -- [peca|conjunto|mao|wire|pose]
Saida: previas/luvas_*.png. O arco entra deslocado (0,-0,085,0) em relacao a socket_weapon_l (ver luvas_geo.py)."""
import os, sys, math
import bpy
from mathutils import Vector
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import previas as P
P.OUT = os.path.join(AQUI, "previas")
OFF = Vector((0, -0.085, 0))
_wire_on = P.wire_on
def _fino(sc):
    _wire_on(sc)
    for ob in sc.objects:
        for m in ob.modifiers:
            if m.name == "wf":
                m.thickness = 0.0005
P.wire_on = _fino
alvo = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["peca"]


def esconder_maos():
    for o in bpy.data.objects:
        if o.name.startswith("Body_Hands"):
            o.hide_render = True; o.hide_viewport = True


def arco_off(objs_novos=None):
    for o in bpy.data.objects:
        if o.name.startswith("SM_Archer_Bow") or (o.parent is None and o.type == "EMPTY" and "Arco" in o.name):
            pass
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    for o in bpy.data.objects:
        if o.parent is None and o.type != "ARMATURE" and o.location.length > 0.2 and o.type in ("EMPTY", "MESH"):
            o.location = o.location + OFF


if "peca" in alvo:
    sc = P.nova_cena(); objs = P.montar(["Luvas"])
    lo, hi = P.limites(objs); ctr = (lo + hi) / 2
    P.render(sc, "luvas_frente", ctr, (hi.x - lo.x) * 1.1, 0, 5)
    P.render(sc, "luvas_tres_quartos", ctr, (hi.x - lo.x) * 1.1, 35, 20)
    P.render(sc, "luvas_lado", ctr, 0.45, 90, 5)
if "isoladas" in alvo:
    sc = P.nova_cena(); objs = P.montar(["Luvas", "Arco"]); arco_off()
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    cl = P.osso_mundo(arm, "LeftHand") + Vector((0, -0.06, 0.02)); cr = P.osso_mundo(arm, "RightHand") + Vector((0, -0.03, 0.03))
    P.render(sc, "luvas_esq_3q", cl, 0.36, 35, 16)
    P.render(sc, "luvas_esq_costas", cl, 0.36, 215, 12)
    P.render(sc, "luvas_dir_3q", cr, 0.36, -35, 16)
    P.render(sc, "luvas_dir_dentro", cr, 0.36, 60, 12)
    P.render(sc, "luvas_wire_esq", cl, 0.36, 35, 16, wire=True)
    P.render(sc, "luvas_wire_dir", cr, 0.36, -35, 16, wire=True)
if "wire" in alvo:
    sc = P.nova_cena(); objs = P.montar(["Luvas"])
    lo, hi = P.limites(objs); ctr = (lo + hi) / 2
    P.render(sc, "luvas_wire", ctr, (hi.x - lo.x) * 1.1, 35, 20, wire=True)
if "conjunto" in alvo:
    sc = P.nova_cena(); objs = P.montar(["Corpo", "Capuz", "Peitoral", "Calca", "Botas", "Luvas", "Arco"])
    arco_off(); esconder_maos()
    lo, hi = P.limites(objs); ctr = (lo + hi) / 2
    P.render(sc, "luvas_conjunto_frente", ctr, (hi.z - lo.z) * 1.1, 0, 5)
    P.render(sc, "luvas_conjunto_3q", ctr, (hi.z - lo.z) * 1.1, 40, 12)
if "mao" in alvo:
    sc = P.nova_cena(); objs = P.montar(["Corpo", "Peitoral", "Luvas", "Arco"])
    arco_off(); esconder_maos()
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    ctr = P.osso_mundo(arm, "socket_weapon_l") + Vector((0, -0.04, 0.02))
    P.render(sc, "luvas_mao_esq_3q", ctr, 0.42, 40, 14)
    P.render(sc, "luvas_mao_esq_frente", ctr, 0.42, 0, 6)
    P.render(sc, "luvas_mao_esq_lado", ctr, 0.42, 90, 6)
if "maod" in alvo:
    sc = P.nova_cena(); objs = P.montar(["Corpo", "Peitoral", "Luvas"]); esconder_maos()
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    ctr = P.osso_mundo(arm, "RightHand") + Vector((0, -0.02, 0.02))
    P.render(sc, "luvas_mao_dir_3q", ctr, 0.42, -40, 14)
    P.render(sc, "luvas_mao_dir_lado", ctr, 0.42, -90, 6)

if "pose" in alvo:
    sc = P.nova_cena(); objs = P.montar(["Corpo", "Peitoral", "Luvas"]); esconder_maos()
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    for a_ in [o for o in bpy.data.objects if o.type == "ARMATURE"]:
        for n, r in (("LeftLowerArm", (-60, 0, 0)), ("LeftHand", (-25, 0, 0)), ("RightLowerArm", (-75, 0, 0)), ("RightHand", (20, 0, 25))):
            pb = a_.pose.bones[n]; pb.rotation_mode = "XYZ"; pb.rotation_euler = tuple(math.radians(a) for a in r)
    bpy.context.view_layer.update()
    lo, hi = P.limites(objs); ctr = P.osso_mundo(arm, "RightHand") * 0.5 + P.osso_mundo(arm, "LeftHand") * 0.5
    P.render(sc, "luvas_pose_teste", P.osso_mundo(arm, "RightLowerArm") * 0.5 + P.osso_mundo(arm, "LeftLowerArm") * 0.5 + Vector((0, -0.1, 0)), 0.9, 55, 10)
