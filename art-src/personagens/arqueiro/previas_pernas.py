"""Previas de calca/botas (EEVEE 1024, um render por vez). Rodar: blender -b --factory-startup -P previas_pernas.py -- [vistas|close|wire|pose]
Saida: previas/pernas_*.png"""
import os, sys, types
import bpy
from mathutils import Vector
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
_c = types.ModuleType("_comum")
_c.SAIDA = os.environ.get("ARQ_SAIDA", os.path.join(AQUI, "..", "..", "..", "godot", "art", "models", "personagens", "arqueiro"))
sys.modules["_comum"] = _c
import previas as P
P.OUT = os.path.join(AQUI, "previas")
alvo = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["vistas"]
BAIXO = ["Corpo", "Calca", "Botas"]
ctr = Vector((0, 0.0, 0.36)); esc = 0.80
if "vistas" in alvo:
    sc = P.nova_cena(); P.montar(BAIXO)
    for n, az, el in (("frente", 0, 4), ("3q", 35, 14), ("lado", 90, 4), ("costas", 180, 4)):
        P.render(sc, "pernas_" + n, ctr, esc, az, el)
if "close" in alvo:
    sc = P.nova_cena(); P.montar(BAIXO)
    P.render(sc, "pernas_bota_close", Vector((0.1, -0.02, 0.15)), 0.42, 30, 12)
if "wire" in alvo:
    sc = P.nova_cena(); P.montar(["Calca", "Botas"])
    P.render(sc, "pernas_wire", ctr, esc, 35, 12, wire=True)
if "conj" in alvo:
    sc = P.nova_cena(); objs = P.montar(["Corpo", "Capuz", "Peitoral", "Calca", "Luvas", "Botas"])
    lo, hi = P.limites(objs)
    P.render(sc, "pernas_conjunto", (lo + hi) / 2, (hi.z - lo.z) * 1.1, 30, 8)
if "solo" in alvo:
    sc = P.nova_cena(); P.montar(["Calca", "Botas"])
    P.render(sc, "pernas_solo_3q", ctr, esc, 35, 12)
    P.render(sc, "pernas_solo_frente", ctr, esc, 0, 0)
if "dbg" in alvo:
    sc = P.nova_cena(); P.montar(["Calca"])
    P.render(sc, "dbg_a", Vector((0.15, 0.07, 0.3)), 0.4, 90, 0)
    sc = P.nova_cena(); P.montar(["Corpo", "Calca"])
    P.render(sc, "dbg_b", Vector((0.15, 0.07, 0.3)), 0.4, 90, 0)
if "pose" in alvo:
    import math
    sc = P.nova_cena(); P.montar(["Corpo", "Calca", "Botas"])
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    def poser(rot):
        for a in arms:
            for n, (x, y, z) in rot.items():
                pb = a.pose.bones.get(n)
                if pb:
                    pb.rotation_mode = "XYZ"; pb.rotation_euler = (math.radians(x), math.radians(y), math.radians(z))
        bpy.context.view_layer.update()
    agach = {}
    for s in ("Left", "Right"):
        agach[s + "UpperLeg"] = (-70, 0, 0); agach[s + "LowerLeg"] = (95, 0, 0); agach[s + "Foot"] = (-25, 0, 0)
    poser(agach)
    P.render(sc, "pernas_pose_agachado_lado", Vector((0, 0.0, 0.3)), 0.9, 90, 4)
    P.render(sc, "pernas_pose_agachado_3q", Vector((0, 0.0, 0.3)), 0.9, 35, 10)
    passo = {"LeftUpperLeg": (-45, 0, 0), "LeftLowerLeg": (20, 0, 0), "RightUpperLeg": (30, 0, 0), "RightLowerLeg": (50, 0, 0), "RightFoot": (-15, 0, 0), "LeftFoot": (10, 0, 0)}
    poser({n: (0, 0, 0) for n in agach}); poser(passo)
    P.render(sc, "pernas_pose_passo_lado", Vector((0, 0.0, 0.35)), 0.9, 90, 4)
