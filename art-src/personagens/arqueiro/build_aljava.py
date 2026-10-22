"""Exporta Arqueiro_Aljava.glb (estatico, sem armature). Rodar: blender -b -P build_aljava.py

Orientacao (glTF Y-up, escala 1 m, 0,53 m de altura): origem no meio da alca/corpo da aljava
(a origem original do FBX); comprimento ao longo de Y (boca em +Y), largura 0,15 m em X e 0,17 m em Z.
No Godot, parentar a um BoneAttachment3D em Chest (costas), inclinada ~20 graus, ou fixa nas costas.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c

c.arma_estatica(c.ALJAVA + "/SM_Weapon_Quiver.fbx", c.ALJAVA + "/T_Weapon_Quiver_BC.png",
                "SM_Archer_Quiver", "M_Arqueiro_Aljava", "Arqueiro_Aljava.glb")
