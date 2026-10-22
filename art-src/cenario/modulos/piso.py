"""Módulo 3D: piso da Cripta (módulo 8x8 m periódico, topo das lajotas em z=0).
python3 piso.py <pasta_saida> [pasta_previas]    (módulo bpy)  ou  blender -b --factory-startup -P piso.py -- <saida> [previas]
Monta as partes de piso_partes/: lajotas (lajotas e juntas), desgaste (rachaduras, lascas, cascalho), pocas (água e musgo).
Exporta SM_Cripta_Piso.glb (cores sólidas por material M_Piso_*), pivô no centro do módulo, Y para cima no glTF."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from piso_partes import comum, lajotas, desgaste, pocas, textura

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None

comum.limpar_cena()
objs = []
for parte in (lajotas, desgaste, pocas):
    objs += parte.construir()
textura.aplicar(objs)
bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.select_set(True); o.location.x -= comum.TILE / 2; o.location.y -= comum.TILE / 2   # pivô no centro
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
tris = sum(len(o.data.polygons) for o in objs)
os.makedirs(OUT, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SM_Cripta_Piso.glb"), use_selection=True, export_format='GLB', export_yup=True)
print("exportado SM_Cripta_Piso", len(objs), "objetos", tris, "polígonos")
if PREV:
    comum.previa(os.path.join(PREV, "piso_jogo.png"), olhar=(0, 0, 0), cam=(5.5, -7.5, 8.5), luz_quente=False)
    comum.previa(os.path.join(PREV, "piso_rasante.png"), olhar=(0, 0, 0), cam=(3.0, -3.5, 1.2), lente=40, luz_quente=False)
