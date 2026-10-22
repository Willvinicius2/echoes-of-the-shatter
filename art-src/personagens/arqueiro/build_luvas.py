"""Exporta Arqueiro_Luvas.glb (luvas). Rodar: blender -b -P build_luvas.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c

c.peca_personagem("SK_Archer_Hands_Starter.fbx", "SK_Archer_Luvas", "M_Arqueiro_Luvas", "Arqueiro_Luvas.glb", textura=c.TEX_TRAJE)
