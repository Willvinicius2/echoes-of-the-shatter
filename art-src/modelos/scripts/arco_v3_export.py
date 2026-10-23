"""Arco v3, etapa 4 (Blender -b): junta haste + laminas (blades.npz) em SM_ArcherDark_Bow (material PBR: BC 2048 + normal + MR),
corda rosa-vinho como malha separada (SM_ArcherDark_BowString, 6 lados, reta entre as ancoras das laminas), recentra a origem na
empunhadura, gira o plano do arco para YZ (corda em +Y Blender = -Z glTF, como o build_arco.py) e exporta o GLB com um no raiz.
Uso: blender -b -P arco_v3_export.py -- <saida.glb>"""
import bpy, sys, os, math, bmesh, numpy as np
from mathutils import Vector
out = sys.argv[sys.argv.index("--") + 1]
W2 = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\arco\work3"
bpy.ops.wm.open_mainfile(filepath=os.path.join(W2, "low_uv.blend"))
bow = bpy.data.objects["low"]; bow.name = "SM_ArcherDark_Bow"; bow.data.name = "SM_ArcherDark_Bow"
bpy.context.view_layer.objects.active = bow; bow.select_set(True)
bpy.ops.object.shade_smooth()
bow.data.set_sharp_from_angle(angle=math.radians(50))
bow.data.materials.clear()
def img(name, cs):
    i = bpy.data.images.load(os.path.join(W2, name)); i.colorspace_settings.name = cs; i.pack(); return i
m = bpy.data.materials.new("M_ArcherDark_Bow"); m.use_nodes = True; nt = m.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(bsdf.outputs[0], nt.nodes["Material Output"].inputs[0])
bc = nt.nodes.new('ShaderNodeTexImage'); bc.image = img("T_ArcherDark_Bow_BC.png", 'sRGB'); nt.links.new(bc.outputs[0], bsdf.inputs['Base Color'])
mr = nt.nodes.new('ShaderNodeTexImage'); mr.image = img("T_ArcherDark_Bow_MR.png", 'Non-Color')
sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(mr.outputs[0], sep.inputs[0])
nt.links.new(sep.outputs[1], bsdf.inputs['Roughness']); nt.links.new(sep.outputs[2], bsdf.inputs['Metallic'])
nm = nt.nodes.new('ShaderNodeTexImage'); nm.image = img("T_ArcherDark_Bow_N.png", 'Non-Color')
nmap = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(nm.outputs[0], nmap.inputs['Color']); nt.links.new(nmap.outputs[0], bsdf.inputs['Normal'])
bow.data.materials.append(m)

import json
inf = json.load(open(os.path.join(W2, "blade_info.json"))); bl = np.load(os.path.join(W2, "blades.npz"))
uvname = bow.data.uv_layers.active.name
bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None
bpy.ops.object.select_all(action='DESELECT')
bow.select_set(True); bpy.context.view_layer.objects.active = bow
blades = []
for sg in ("1", "-1"):
    V = bl["V" + sg]; Fq = bl["F" + sg]; UVb = bl["UV" + sg]
    me = bpy.data.meshes.new("blade" + sg); me.from_pydata([tuple(v) for v in V], [], [tuple(int(i) for i in f) for f in Fq]); me.update()
    uvl = me.uv_layers.new(name=uvname)
    for li, lp in enumerate(me.loops): uvl.data[li].uv = tuple(UVb[lp.vertex_index])
    ob = bpy.data.objects.new("blade" + sg, me); bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(30))
    blades.append(ob)
bpy.ops.object.select_all(action='DESELECT')
for ob in blades + [bow]: ob.select_set(True)
bpy.context.view_layer.objects.active = bow
bpy.ops.object.join()
bow = bpy.context.view_layer.objects.active; bow.name = "SM_ArcherDark_Bow"; bow.data.name = "SM_ArcherDark_Bow"
for p_ in bow.data.polygons: p_.material_index = 0
while len(bow.data.materials) > 1: bow.data.materials.pop(index=len(bow.data.materials) - 1)
# --- corda: reta entre as ancoras, rosa-vinho fosco
a = Vector(inf["1"]["anchor"]); b = Vector(inf["-1"]["anchor"])
R = 0.0017; d = (b - a).normalized(); u = d.cross(Vector((0, 1, 0))).normalized(); w = d.cross(u).normalized()
bm = bmesh.new(); ring = []
for c in (a, b):
    ring.append([bm.verts.new(c + (u * math.cos(2 * math.pi * j / 6) + w * math.sin(2 * math.pi * j / 6)) * R) for j in range(6)])
for j in range(6): bm.faces.new((ring[0][j], ring[0][(j + 1) % 6], ring[1][(j + 1) % 6], ring[1][j]))
bm.faces.new(ring[0][::-1]); bm.faces.new(ring[1])
bmesh.ops.triangulate(bm, faces=bm.faces[:]); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("SM_ArcherDark_BowString"); bm.to_mesh(me); bm.free()
so = bpy.data.objects.new("SM_ArcherDark_BowString", me); bpy.context.scene.collection.objects.link(so)
sm = bpy.data.materials.new("M_ArcherDark_BowString"); sm.use_nodes = True
b2 = sm.node_tree.nodes["Principled BSDF"]
b2.inputs['Base Color'].default_value = (0.30, 0.025, 0.11, 1); b2.inputs['Roughness'].default_value = 0.78
b2.inputs['Emission Color'].default_value = (0.75, 0.05, 0.26, 1); b2.inputs['Emission Strength'].default_value = 0.10
so.data.materials.append(sm)
# --- folga corda x haste (so vertices da haste: indices antes das laminas) e dimensoes
Pw = np.array([v.co[:] for v in bow.data.vertices]); nh = len(Pw)
ab = np.array(b - a); L2 = ab @ ab
Hv = Pw[np.array([v.co[2] for v in bow.data.vertices]) != 0] if False else Pw
tpar = np.clip(((Hv - np.array(a)) @ ab) / L2, 0, 1); dist = np.linalg.norm(Hv - (np.array(a) + tpar[:, None] * ab), axis=1)
ish = np.ones(len(Hv), bool)
print("FOLGA corda-malha (min dist ao eixo, descontando as ancoras) mm", round(1000 * np.sort(dist[(tpar > 0.06) & (tpar < 0.94)])[0], 2), "min global", round(1000 * dist.min(), 2))
# --- recentra na empunhadura, gira 90 graus em Z (+X -> +Y)
grip = Pw[np.abs(Pw[:, 2]) < 0.02]; gx = (grip[:, 0].min() + grip[:, 0].max()) / 2
print("EMPUNHADURA x", round(gx, 4), "y", round((grip[:, 1].min() + grip[:, 1].max()) / 2, 4))
from mathutils import Matrix
Mx = Matrix.Rotation(math.radians(90), 4, 'Z') @ Matrix.Translation((-gx, 0, 0))
for ob in (bow, so):
    ob.data.transform(Mx); ob.data.update()
root = bpy.data.objects.new("SM_ArcherDark_Bow_Root", None); bpy.context.scene.collection.objects.link(root)
for ob in (bow, so): ob.parent = root
Pf = np.array([v.co[:] for v in bow.data.vertices]); print("BBOX arco", Pf.min(0).round(3), Pf.max(0).round(3), "altura", round(Pf[:, 2].max() - Pf[:, 2].min(), 3))
print("TRIS arco", sum(len(p.vertices) - 2 for p in bow.data.polygons), "corda", len(so.data.polygons))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
    export_image_format='AUTO', export_materials='EXPORT', export_cameras=False, export_lights=False, export_normals=True, export_texcoords=True)
print("OK", out, os.path.getsize(out))
