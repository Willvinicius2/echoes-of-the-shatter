"""Módulo 3D: piso da Cripta (módulo 8x8 m periódico, topo das lajotas em z=0).
python3 piso.py <pasta_saida> [pasta_previas]    (módulo bpy)  ou  blender -b --factory-startup -P piso.py -- <saida> [previas]
Monta as partes de piso_partes/: lajotas (lajotas e juntas), desgaste (rachaduras, lascas, cascalho), pocas (água e musgo).
Exporta SM_Cripta_Piso.glb (cores sólidas por material M_Piso_*), pivô no centro do módulo, Y para cima no glTF."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from piso_partes import comum, lajotas, desgaste, pocas

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None

comum.limpar_cena()
objs = []
for parte in (lajotas, desgaste, pocas):
    objs += parte.construir()
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
    # nós procedurais só na prévia: variação de tom e relevo fino nas lajotas (o .glb leva cor sólida)
    for m in bpy.data.materials:
        if m.name.startswith("M_Piso_Laje"):
            nt = m.node_tree; b = nt.nodes["Principled BSDF"]; base = b.inputs["Base Color"].default_value
            tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 14; n.inputs["Detail"].default_value = 10
            mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
            mix.inputs[6].default_value = (base[0] * 0.7, base[1] * 0.7, base[2] * 0.75, 1); mix.inputs[7].default_value = (base[0] * 1.35, base[1] * 1.35, base[2] * 1.4, 1)
            nt.links.new(tc.outputs["Object"], n.inputs["Vector"]); nt.links.new(n.outputs["Fac"], mix.inputs[0]); nt.links.new(mix.outputs[2], b.inputs["Base Color"])
            bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5
            nt.links.new(n.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    comum.previa(os.path.join(PREV, "piso_jogo.png"), olhar=(0, 0, 0), cam=(5.5, -7.5, 8.5), luz_quente=False)
    comum.previa(os.path.join(PREV, "piso_rasante.png"), olhar=(0, 0, 0), cam=(3.0, -3.5, 1.2), lente=40, luz_quente=False)
