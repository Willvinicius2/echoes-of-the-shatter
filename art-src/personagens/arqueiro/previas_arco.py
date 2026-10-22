"""Previas do arco (EEVEE 1024, um render por vez). Rodar: blender -b --factory-startup -P previas_arco.py -- [peca|grip|mao|wire]
Saida: previas/arco_*.png"""
import os, sys
import bpy
from mathutils import Vector
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import types
_c = types.ModuleType("_comum")  # _comum.py e de outro agente; so precisamos da pasta de saida dos GLB
_c.SAIDA = os.environ.get("ARQ_SAIDA", os.path.join(AQUI, "..", "..", "..", "godot", "art", "models", "personagens", "arqueiro"))
sys.modules["_comum"] = _c
import previas as P
P.OUT = os.path.join(AQUI, "previas")
alvo = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["peca", "grip", "mao"]
if "peca" in alvo or "wire" in alvo:
    sc = P.nova_cena()
    objs = P.montar(["Arco"])
    lo, hi = P.limites(objs); ctr = (lo + hi) / 2
    esc = (hi.z - lo.z) * 1.12
    if "peca" in alvo:
        P.render(sc, "arco_frente", ctr, esc, 0, 3)
        P.render(sc, "arco_lado", ctr, esc, 90, 3)
        P.render(sc, "arco_tres_quartos", ctr, esc, 40, 15)
    P.render(sc, "arco_wire", ctr, esc, 40, 15, wire=True)
if "grip" in alvo:
    sc = P.nova_cena()
    P.montar(["Arco"])
    P.render(sc, "arco_grip", Vector((0, 0, 0)), 0.34, 35, 15)
if "mao" in alvo:
    sc = P.nova_cena()
    objs = P.montar(["Corpo", "Capuz", "Peitoral", "Calca", "Luvas", "Botas", "Aljava", "Arco"])
    lo, hi = P.limites(objs); ctr = (lo + hi) / 2
    P.render(sc, "arco_na_mao", ctr, (hi.z - lo.z) * 1.1, 60, 8)
    P.render(sc, "arco_na_mao_lado", ctr, (hi.z - lo.z) * 1.1, 90, 5)
    P.render(sc, "arco_na_mao_frente", ctr, (hi.z - lo.z) * 1.1, 0, 5)
if "pontas" in alvo:
    sc = P.nova_cena()
    P.montar(["Arco"])
    P.render(sc, "arco_ponta_cima", Vector((0, 0.05, 0.47)), 0.30, 60, 12)
    P.render(sc, "arco_ponta_baixo", Vector((0, 0.05, -0.47)), 0.30, -60, 12)
if "maoclose" in alvo:
    sc = P.nova_cena()
    objs = P.montar(["Corpo", "Luvas", "Arco"])
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    ctr = P.osso_mundo(arm, "socket_weapon_l")
    P.render(sc, "arco_mao_close_lado", ctr, 0.55, 90, 5)
    P.render(sc, "arco_mao_close_3q", ctr, 0.55, 40, 12)
