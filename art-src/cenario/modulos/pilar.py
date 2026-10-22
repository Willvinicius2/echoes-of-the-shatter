"""Pilar da Cripta com estátua em nicho (referência: referencias-cripta/pilar.png).
Montagem das partes: pilar_base.py (soco, entulho, musgo), pilar_fuste.py (núcleo, colunetas, cornija, coroamento) e
pilar_nicho.py (nicho ogival, moldura, estátua). Blocos lascados vêm de pilar_lib.py. Metros, pivô no centro da base, frente = +Y.
  python3 pilar.py <pasta_saida> [pasta_previas]      (módulo bpy do pip, ou: blender -b --factory-startup -P pilar.py -- ...)
  PILAR_VISTA=frente,tres_quartos,costas,nicho,topo escolhe as prévias; PILAR_SEM_GLB=1 não exporta.
Materiais com os nomes dos outros módulos da Cripta: M_Pedra / M_PedraEscura recebem a pedra triplanar no Godot."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pilar_lib as L
import pilar_base, pilar_fuste, pilar_nicho, pilar_bake

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None
ONLY = os.environ.get("PILAR_VISTA")


TEX = os.environ.get("PILAR_TEX", "/tmp/pilar_tex")   # onde ficam os PNGs do bake (o glb leva as imagens embutidas)


def montar(bake=None):
    L.reset()
    pilar_base.build(L)
    pilar_fuste.build(L)
    nucleo = [o for o in L.objs if o.name.startswith("fuste_nucleo")]
    assert nucleo, "pilar_fuste deve criar o objeto fuste_nucleo"
    L.boolean(nucleo[0], [pilar_nicho.cutter(L)])
    pilar_nicho.build(L)
    o = L.juntar("SM_Cripta_Pilar")
    L.pintar_vertices(o)
    if bake is None: bake = not os.environ.get("PILAR_SEM_BAKE")
    if bake: pilar_bake.bake(o, TEX, res=int(os.environ.get("PILAR_RES", "4096")))
    return o


if __name__ == "__main__":
    o = montar()
    print("tris", sum(len(p.vertices) - 2 for p in o.data.polygons), "dim", tuple(round(v, 2) for v in o.dimensions))
    if OUT and not os.environ.get("PILAR_SEM_GLB"):
        os.makedirs(OUT, exist_ok=True)
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SM_Cripta_Pilar.glb"), use_selection=True, export_format='GLB', export_yup=True, export_image_format='JPEG', export_jpeg_quality=90)
    if PREV:
        os.makedirs(PREV, exist_ok=True)
        for v in (ONLY.split(",") if ONLY else ("frente", "tres_quartos")):
            L.render(o, PREV, "pilar", v)
