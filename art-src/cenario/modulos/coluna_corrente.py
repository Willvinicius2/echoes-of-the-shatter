"""Módulo 3D da Cripta: duas colunas de pedra gótica ligadas por duas correntes de ferro forjado.
Referência: referencias-cripta/objetos.png (canto superior direito). Método por partes, cada uma num arquivo:
  cc_coluna.py    geometria das colunas (alvenaria facetada, nicho ogival, lascas, entulho, olhais)
  cc_corrente.py  elos forjados encadeados em catenária, com grilhões
  cc_materiais.py materiais procedurais, bake de cor e normal numa textura só, renders de revisão
python3 coluna_corrente.py <pasta_glb> [pasta_previas] [--sem-bake] [--tam 2048]
Metros; pivô no centro entre as colunas, na base; frente = +Y do Blender (-Z do Godot)."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import cc_coluna, cc_corrente, cc_materiais

args = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = args[0] if args else "."
PREV = args[1] if len(args) > 1 else None
SEM_BAKE = "--sem-bake" in sys.argv
TAM = int(sys.argv[sys.argv.index("--tam") + 1]) if "--tam" in sys.argv else 2048
V = 3.2   # distância entre os eixos das colunas


def montar():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    M = cc_materiais.criar_materiais()
    objs = cc_coluna.build_coluna(-V / 2, -1, 3, M) + cc_coluna.build_coluna(V / 2, 1, 5, M)
    ae = cc_coluna.ancoras(-V / 2, -1); ad = cc_coluna.ancoras(V / 2, 1)
    flechas = (0.55, 0.40)
    for i in range(2):
        objs += cc_corrente.build_corrente(Vector(ae[i]), Vector(ad[i]), flechas[i], 20 + i, M, escala=1.3)
    return M, objs


def juntar(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object; o.name = "SM_Cripta_ColunaCorrente"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def exportar(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SM_Cripta_ColunaCorrente.glb"), use_selection=True,
                              export_format='GLB', export_yup=True)
    print("exportado", len(o.data.polygons), "faces", tuple(round(d, 2) for d in o.dimensions))


if __name__ == "__main__":
    M, objs = montar()
    o = juntar(objs)
    print("triângulos:", sum(len(p.vertices) - 2 for p in o.data.polygons))
    if PREV:
        os.makedirs(PREV, exist_ok=True)
    if not SEM_BAKE:
        cc_materiais.bake(o, tamanho=TAM, samples=12, pasta=PREV or OUT)
    exportar(o)
    if PREV:
        mat = "auto"
        for v in ("tres_quartos", "frente", "close"):
            cc_materiais.render_preview(o, os.path.join(PREV, f"coluna_corrente_{v}.png"), v, (900, 900), 48, mat)
