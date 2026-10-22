"""Exporta Arqueiro_Botas.glb (botas). Rodar: blender -b -P build_botas.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c

c.peca_personagem("SK_Archer_Feet_Starter.fbx", "SK_Archer_Botas", "M_Arqueiro_Botas", "Arqueiro_Botas.glb")
