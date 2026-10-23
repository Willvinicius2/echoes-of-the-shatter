"""Arco v2, etapa 4 (Blender -b): material PBR (BC 2048 + normal + MR), corda como malha separada
(SM_ArcherDark_BowString, cilindro de 6 lados, material rosa proprio) ligando as duas pontas, exporta o GLB.
Uso: blender -b -P arco_v2_export.py -- <saida.glb>"""
import bpy, sys, os, math, bmesh, numpy as np
from mathutils import Vector
out = sys.argv[sys.argv.index("--") + 1]
W2 = r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\arco\work2"
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
# --- pontas: vertices mais altos/baixos, lado +X (corda)
P = np.array([v.co[:] for v in bow.data.vertices])
def tip(sign):
    sel = P[(P[:, 2] * sign) > 0.46]
    k = sel[np.argmax(sel[:, 0] + 0.5 * sign * sel[:, 2] * 0)]
    return k
tt, tb = tip(1), tip(-1)
print("PONTAS", tt, tb, "x max haste", P[:, 0].max())
# a corda sai do entalhe, um pouco para dentro da ponta
a = Vector((tt[0] - 0.006, 0, tt[2] - 0.045)); b = Vector((tb[0] - 0.006, 0, tb[2] + 0.045))
bm = bmesh.new(); R = 0.0024; SEG = 4; ring = []
for i in range(SEG + 1):
    c = a.lerp(b, i / SEG); r = []
    for j in range(6):
        t = 2 * math.pi * j / 6; r.append(bm.verts.new(c + Vector((math.cos(t) * R, math.sin(t) * R, 0))))
    ring.append(r)
for i in range(SEG):
    for j in range(6):
        bm.faces.new((ring[i][j], ring[i][(j + 1) % 6], ring[i + 1][(j + 1) % 6], ring[i + 1][j]))
bm.faces.new(ring[0][::-1]); bm.faces.new(ring[-1])
bmesh.ops.triangulate(bm, faces=bm.faces[:])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
me = bpy.data.meshes.new("SM_ArcherDark_BowString"); bm.to_mesh(me); bm.free()
so = bpy.data.objects.new("SM_ArcherDark_BowString", me); bpy.context.scene.collection.objects.link(so)
sm = bpy.data.materials.new("M_ArcherDark_BowString"); sm.use_nodes = True
b2 = sm.node_tree.nodes["Principled BSDF"]
b2.inputs['Base Color'].default_value = (0.62, 0.07, 0.26, 1); b2.inputs['Roughness'].default_value = 0.45
b2.inputs['Emission Color'].default_value = (1.0, 0.1, 0.4, 1); b2.inputs['Emission Strength'].default_value = 0.35
so.data.materials.append(sm)
print("TRIS arco", sum(len(p.vertices) - 2 for p in bow.data.polygons), "corda", len(me.polygons))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
    export_image_format='AUTO', export_materials='EXPORT', export_cameras=False, export_lights=False, export_normals=True, export_texcoords=True)
print("OK", out, os.path.getsize(out))
