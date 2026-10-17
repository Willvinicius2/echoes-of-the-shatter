"""Etapa a (Blender): GLB da IA -> work/raw.ply na pose da fonte (transformacoes aplicadas, sem normais).
Pecas refeitas por proc (superelipsoide) nao precisam do GLB: so registram o aviso."""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_common import *
c = load_cfg()
if "proc" in c:
    print("EA proc: geometria da IA recusada, nada a importar")
    raise SystemExit(0)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=c["glb"])
ob = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
ob.data.transform(ob.matrix_world); ob.matrix_world.identity()
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
bpy.ops.wm.ply_export(filepath=wpath(c, "raw.ply"), export_selected_objects=True, export_normals=False,
                      export_uv=False, export_colors='NONE', ascii_format=False)
print("EA", len(ob.data.polygons))
