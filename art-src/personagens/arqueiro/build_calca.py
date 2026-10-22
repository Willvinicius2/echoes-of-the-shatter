"""Exporta Arqueiro_Calca.glb (calca modelada por script: pernas com dobras, joelheiras, ataduras, barra de penas).
Rodar: blender -b -P build_calca.py   (antes: python pernas_textura.py)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c
import pernas_geo as G

G.peca_pernas("SK_Archer_Legs_Starter.fbx", "SK_Archer_Calca", "M_Arqueiro_Calca", "Arqueiro_Calca.glb",
              G.construir_calca, c.SAIDA + "/T_Arqueiro_Calca_BC.png")
