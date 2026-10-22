"""Exporta Arqueiro_Botas.glb (botas grandes modeladas por script: cano alto, placas de osso, solado grosso).
Rodar: blender -b -P build_botas.py   (antes: python pernas_textura.py)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c
import pernas_geo as G

G.peca_pernas("SK_Archer_Feet_Starter.fbx", "SK_Archer_Botas", "M_Arqueiro_Botas", "Arqueiro_Botas.glb",
              G.construir_botas, c.SAIDA + "/T_Arqueiro_Botas_BC.png")
