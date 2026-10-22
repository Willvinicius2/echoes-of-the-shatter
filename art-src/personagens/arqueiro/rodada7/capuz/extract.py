# extrai as texturas originais do GLB do repo para ./orig
import bpy,os
import os as _os
_AQUI = _os.path.dirname(_os.path.abspath(__file__))
_R7 = _os.path.dirname(_AQUI)
_RAIZ = _os.path.abspath(_os.path.join(_R7, "..", "..", "..", ".."))
FONTE = _os.environ.get("ARQ_FONTE_ORIG", _os.path.join(_R7, "_fonte_original"))   # GLBs/texturas pre-polida (somente leitura)
SAIDA = _os.environ.get("ARQ_SAIDA", _os.path.join(_RAIZ, "godot", "art", "models", "personagens", "arqueiro"))
TRAB = _os.environ.get("ARQ_TRAB", _os.path.join(_R7, "_trabalho", "capuz"))   # intermediarios (fora do git)
_os.makedirs(TRAB, exist_ok=True)
SRC=os.path.join(FONTE,"Arqueiro_Capuz.glb")
os.makedirs(os.path.join(TRAB,"orig"),exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
for i in bpy.data.images:
    if i.name in("T_Capuz_BC","T_CapuzDetalhe_BC"):
        i.filepath_raw=os.path.join(TRAB,"orig",i.name+".png"); i.file_format="PNG"; i.save()
