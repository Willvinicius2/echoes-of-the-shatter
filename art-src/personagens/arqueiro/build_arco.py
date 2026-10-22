"""Exporta Arqueiro_Arco.glb (estatico, sem armature). Rodar: blender -b -P build_arco.py

Orientacao (glTF Y-up, escala 1 m, 0,88 m de altura): origem na empunhadura (centro do arco);
as pontas das alcas ficam ao longo de +-Y, a curva do arco abre no eixo X e a espessura vai em Z.
No Godot, parentar a um BoneAttachment3D em socket_weapon_l (ajustar rotacao no encaixe).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c

c.arma_estatica(c.ARCO + "/SM_Weapon_Bow.fbx", c.ARCO + "/T_Weapon_Bow_BC.png",
                "SM_Archer_Bow", "M_Arqueiro_Arco", "Arqueiro_Arco.glb")
