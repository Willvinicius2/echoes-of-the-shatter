"""Exporta Arqueiro_Capuz.glb (capuz). Rodar: blender -b -P build_capuz.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c

c.peca_personagem("SK_Archer_Head_Starter.fbx", "SK_Archer_Capuz", "M_Arqueiro_Capuz", "Arqueiro_Capuz.glb")
