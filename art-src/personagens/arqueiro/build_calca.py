"""Exporta Arqueiro_Calca.glb (calca). Rodar: blender -b -P build_calca.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c

c.peca_personagem("SK_Archer_Legs_Starter.fbx", "SK_Archer_Calca", "M_Arqueiro_Calca", "Arqueiro_Calca.glb")
