"""Previas EEVEE 1024 do Peitoral (um render por vez, via previas.py). Rodar: blender -b -P peitoral_previas.py -- [solo] [conj] [ombros]
Saida: previas/peitoral_*.png"""
import os, sys
import bpy
from mathutils import Vector
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import previas as P

P.OUT = os.path.join(AQUI, "previas")
PECAS = ["Capuz", "Peitoral", "Calca", "Luvas", "Botas", "Arco", "Aljava"]


def run(modo):
    if modo == "solo":
        sc = P.nova_cena(); objs = P.montar(["Peitoral"])
        lo, hi = P.limites(objs); ct = (lo + hi) / 2; es = max(hi.z - lo.z, hi.x - lo.x, hi.y - lo.y) * 1.15
        for n, az, el in (("frente", 0, 5), ("lado", 90, 5), ("3q", 35, 15), ("costas", 180, 5)):
            P.render(sc, "peitoral_solo_" + n, ct, es, az, el)
        P.render(sc, "peitoral_wire", ct, es, 150, 15, wire=True)
    elif modo == "conj":
        sc = P.nova_cena(); objs = P.montar(PECAS)
        lo, hi = P.limites(objs); ct = (lo + hi) / 2; es = max(hi.z - lo.z, hi.x - lo.x, hi.y - lo.y) * 1.1
        for n, az, el in (("frente", 0, 6), ("3q", 35, 15), ("costas", 180, 6), ("lado", 90, 6), ("3q_costas", 145, 15)):
            P.render(sc, "peitoral_conj_" + n, ct, es, az, el)
    elif modo == "ombros":
        sc = P.nova_cena(); objs = P.montar(["Capuz", "Peitoral", "Calca", "Luvas", "Botas"])
        P.render(sc, "peitoral_ombros", Vector((0, 0.07, 0.85)), 0.8, 35, 18)
        P.render(sc, "peitoral_ombros_costas", Vector((0, 0.15, 0.7)), 1.0, 160, 14)
    elif modo == "pesos":
        pass


for m in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["solo", "conj", "ombros"]):
    run(m)
