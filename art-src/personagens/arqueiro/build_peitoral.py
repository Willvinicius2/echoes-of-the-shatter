"""Exporta Arqueiro_Peitoral.glb (peitoral e capa de penas). Rodar: blender -b -P build_peitoral.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c

c.peca_personagem("SK_Archer_Chest_Starter.fbx", "SK_Archer_Peitoral", "M_Arqueiro_Peitoral", "Arqueiro_Peitoral.glb")
