"""Etapa e (Blender): material unico, FBX SM_Cripta_<Peca> com o preset do graybox, .blend, json com colisor sugerido e previas.

1 material (M_Cripta_<Peca>: albedo pintado, sem normal map; a mascara T_..._M.png entra no material do jogo, nao no do Blender).
Colisor sugerido (docs/04 17.1: BoxCollider, nunca a malha visual) fica em OUT/SM_Cripta_<Peca>.json, em coordenadas da
Unity ((x,y,z)_Unity = (-x, z, -y)_Blender com o preset canonico). Previas Workbench (frente e 3/4 da camera do jogo).
"""
import bpy, sys, os, math, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_common import *
from mathutils import Vector

c = load_cfg()
gb = import_graybox()
bpy.ops.wm.open_mainfile(filepath=wpath(c, "game_final.blend"))
ob = bpy.data.objects["game"]
ob.name = ob.data.name = c["asset"]
tex = c["asset"][3:]
mat = bpy.data.materials.new("M_" + tex); mat.use_nodes = True
nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]
img = bpy.data.images.load(f"{OUT_ROOT}/T_{tex}_BC.png"); img.colorspace_settings.name = 'sRGB'
n = nt.nodes.new('ShaderNodeTexImage'); n.image = img
nt.links.new(n.outputs['Color'], bsdf.inputs['Base Color']); bsdf.inputs['Roughness'].default_value = 1.0
ob.data.materials.clear(); ob.data.materials.append(mat)
me = ob.data
v = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', v); v = v.reshape(-1, 3)
lo, hi = v.min(0), v.max(0)
tris = sum(len(p.vertices) - 2 for p in me.polygons)


def u3(p): return [round(float(-p[0]), 3), round(float(p[2]), 3), round(float(-p[1]), 3)]   # Blender -> Unity


def box(cen, size):   # centro/tamanho no Blender -> Unity
    return dict(type="BoxCollider", center=u3(cen), size=[round(float(size[0]), 3), round(float(size[2]), 3), round(float(size[1]), 3)])


col = c.get("collider", "none")
if col == "box": colliders = [box((lo + hi) / 2, hi - lo)]
elif col == "floor": colliders = [box(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, -0.1), (hi[0] - lo[0], hi[1] - lo[1], 0.2))]
elif col == "ramp":
    colliders = [dict(type="MeshCollider(convex) sugerido", note="rampa: cunha de 2 m de base e 1 m de altura sobe para +Y do Blender (frente +Z da Unity vira topo)",
                      bounds=box((lo + hi) / 2, hi - lo))]
elif isinstance(col, list): colliders = [box(b[:3], b[3:]) for b in col]
else: colliders = []
info = dict(asset=c["asset"], mesh=c["asset"], tris=tris, kind=c["kind"], size_m_unity=[round(float(hi[0] - lo[0]), 3), round(float(hi[2] - lo[2]), 3), round(float(hi[1] - lo[1]), 3)],
            bounds_blender=dict(min=np.round(lo, 3).tolist(), max=np.round(hi, 3).tolist()), pivot=c["pivot"],
            textures=dict(albedo=f"T_{tex}_BC.png ({c['tex']}x{c['tex']}, sRGB)", mask=f"T_{tex}_M.png ({c['mask_tex']}x{c['mask_tex']}, linear; R emissao, G rim, B tinta)"),
            colliders=colliders, shadow_casting="Off (cenario)", collider_note="sugestao: nunca usar a malha visual como colisor")
save_json(f"{OUT_ROOT}/{c['asset']}.json", info)
for o in bpy.context.scene.objects: o.select_set(False)
os.makedirs(OUT_ROOT + "/blend", exist_ok=True); os.makedirs(OUT_ROOT + "/prev", exist_ok=True)
gb.export_fbx([ob], f"{OUT_ROOT}/{c['asset']}.fbx")
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT_ROOT}/blend/{c['asset']}.blend", compress=True)

# previas
gb.setup_render(640, 640, outline=False)
sh = bpy.context.scene.display.shading
sh.background_color = (0.30, 0.30, 0.33); bpy.context.scene.world.color = (0.30, 0.30, 0.33)
cen = (lo + hi) / 2; ext = float(np.linalg.norm(hi - lo))
cam = gb.game_camera(cen, 12.0, ortho_scale=ext * 1.15, yaw=-135.0, pitch=-45.0)     # 3/4 de frente (camera em -X-Y); a do jogo fica em +X+Y
gb.render(f"{OUT_ROOT}/prev/{c['asset']}_3-4.png")
# frente (-Y)
bpy.data.objects.remove(cam)
cam = gb.game_camera(cen, 12.0, ortho_scale=max(hi[0] - lo[0], hi[2] - lo[2]) * 1.2, yaw=0.0, pitch=-8.0)
cam.location = Vector(cen) + Vector((0, -12, 0))
cam.rotation_euler = (Vector(cen) - cam.location).to_track_quat('-Z', 'Y').to_euler()
gb.render(f"{OUT_ROOT}/prev/{c['asset']}_frente.png")
print("EE", c["asset"], tris, "tris", info["size_m_unity"])
