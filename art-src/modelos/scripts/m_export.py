"""Modular (Blender): exporta as 5 pecas (um FBX cada) e o corpo base em 6 regioes, com o preset do projeto, e a lista de regioes escondidas."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdl_common import *
from mdl_modular import *

cfg = load_cfg()
gb_lib, gb_rig = import_graybox()
arm, pieces, regs = assemble(cfg)
out = {}
for s, o in pieces.items():
    for ob in bpy.context.scene.objects:
        ob.select_set(False)
    path = fpath(cfg, f"{o.name}.fbx")
    gb_rig.export_fbx_rigged(arm, [o], path)
    out[o.name] = dict(tris=len(o.data.polygons), fbx=path)
path = fpath(cfg, f"SK_{cfg['hero']}_Body.fbx")
gb_rig.export_fbx_rigged(arm, [regs[r] for r in REGIONS], path)
out[f"SK_{cfg['hero']}_Body"] = dict(tris={r: len(regs[r].data.polygons) for r in REGIONS}, fbx=path)
save_json(fpath(cfg, "hides_regions.json"), dict(cfg["hides"]))
bpy.ops.wm.save_as_mainfile(filepath=fpath(cfg, f"SK_{cfg['hero']}_Modular.blend"), compress=True)
save_json(wpath(cfg, "export_modular.json"), out)
print("MEXP", out)
