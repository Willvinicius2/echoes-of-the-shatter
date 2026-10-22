"""Previas da aljava (EEVEE 1024, um render por vez). Rodar: blender -b --factory-startup -P previas_aljava.py -- [peca|wire|corpo|medir]
Offset da aljava no Chest (Blender, metros, relativo a cabeca do osso): ALJ_OFF="dx,dy,dz" (costas = +Y). Saida: previas/aljava_*.png"""
import os, sys, math
import bpy
from mathutils import Vector
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import types
_c = types.ModuleType("_comum")
_c.SAIDA = os.environ.get("ARQ_SAIDA", os.path.join(AQUI, "..", "..", "..", "godot", "art", "models", "personagens", "arqueiro"))
sys.modules["_comum"] = _c
import previas as P
P.OUT = os.path.join(AQUI, "previas")
OFF = Vector([float(x) for x in os.environ.get("ALJ_OFF", "-0.08,0.47,-0.08").split(",")])
alvo = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["peca"]


def so_aljava():
    sc = P.nova_cena()
    objs = P.importar_glb("Aljava")
    return sc, objs


if "peca" in alvo or "wire" in alvo:
    sc, objs = so_aljava()
    ctr = Vector((0.0, 0.0, 0.08)); esc = 0.80
    if "peca" in alvo:
        P.render(sc, "aljava_frente", ctr, esc, 0, 4)
        P.render(sc, "aljava_lado", ctr, esc, 90, 4)
        P.render(sc, "aljava_costas", ctr, esc, 180, 4)
        P.render(sc, "aljava_tres_quartos", ctr, esc, 215, 20)
        P.render(sc, "aljava_bandoleira", Vector((0.1, 0.0, 0.0)), 1.1, 150, 10)
    if "wire" in alvo:
        P.render(sc, "aljava_wire", ctr, esc, 215, 20, wire=True)
if "corpo" in alvo or "medir" in alvo:
    sc = P.nova_cena()
    objs = P.montar(["Corpo", "Capuz", "Peitoral", "Calca", "Luvas", "Botas"])
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    ch = P.osso_mundo(arm, "Chest")
    if "medir" in alvo:
        lo, hi = P.limites([o for o in objs if o.type == "MESH"])
        print("MEDIR chest", tuple(round(v, 3) for v in ch), "lo", tuple(round(v, 3) for v in lo), "hi", tuple(round(v, 3) for v in hi))
        for o in objs:
            if o.type == "MESH":
                a, b = P.limites([o]); print("MEDIR", o.name, tuple(round(v, 3) for v in a), tuple(round(v, 3) for v in b))
    else:
        al = P.importar_glb("Aljava")
        raiz = [o for o in al if o.parent is None][0]
        raiz.location = ch + OFF
        objs += al
        lo, hi = P.limites(objs); ctr = (lo + hi) / 2
        esc = (hi.z - lo.z) * 1.1
        P.render(sc, "aljava_corpo_costas", ctr, esc, 180, 6)
        P.render(sc, "aljava_corpo_lado", ctr, esc, 90, 5)
        P.render(sc, "aljava_corpo_frente", ctr, esc, 0, 5)
        P.render(sc, "aljava_corpo_3q", ctr, esc, 215, 12)
