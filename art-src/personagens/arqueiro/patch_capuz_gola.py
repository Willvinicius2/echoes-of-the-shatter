"""Acrescenta a gola (SK_Archer_Gola) ao Arqueiro_Capuz.glb existente: tubo de pano que fecha o vao entre a barra do capuz e o
peitoral (de costas o capuz flutuava sem ligar ao pescoco). Reimporta o GLB, cria a malha skinada e reexporta.
Rodar: python patch_capuz_gola.py   (modulo bpy; ou blender -b -P). Idempotente: remove uma gola anterior.
"""
import os, math
import bpy, bmesh
import numpy as np

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
GLB = os.path.join(RAIZ, "godot", "art", "models", "personagens", "arqueiro", "Arqueiro_Capuz.glb")
CX, CY = 0.0, 0.11            # eixo do pescoco (Blender; costas = +Y)
Z0, Z1 = 0.93, 1.13           # base (dentro da gola do peitoral) e topo (dentro do capuz)
RX0, RY0, RX1, RY1 = 0.21, 0.20, 0.145, 0.14
LADOS, ANEIS = 20, 6

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
capuz = bpy.data.objects["SK_Archer_Capuz"]
for o in [o for o in bpy.data.objects if o.name.startswith("SK_Archer_Gola")]:
    bpy.data.objects.remove(o)

# UV: um ponto de verde medio do capuz (a gola e lisa; evita UV pintada fora do atlas)
mat = capuz.data.materials[0]
img = next(n.image for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and "BC" in n.image.name)
px = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
uvl = capuz.data.uv_layers.active.data
melhor, uvp = 9, (0.5, 0.5)
alvo = np.array([0.12, 0.26, 0.10])  # verde de sombra: a gola fica no fundo do capuz
for p in capuz.data.polygons:
    if p.material_index != 0:
        continue
    uv = np.mean([uvl[i].uv[:] for i in p.loop_indices], axis=0) % 1.0
    c = px[int(uv[1] * (img.size[1] - 1)), int(uv[0] * (img.size[0] - 1)), :3]
    d = np.abs(c - alvo).sum()
    if d < melhor:
        melhor, uvp = d, tuple(uv)

me = bpy.data.meshes.new("SK_Archer_Gola")
bm = bmesh.new()
aneis = []
for j in range(ANEIS):
    t = j / (ANEIS - 1)
    z = Z0 + (Z1 - Z0) * t
    # barra inferior levemente aberta (dobra de pano), depois estreita
    k = 1 + 0.10 * math.exp(-t * 7)
    e = t * t * (3 - 2 * t)  # estreita suave: pano caido, sem tubo reto
    rx = (RX0 + (RX1 - RX0) * e) * k
    ry = (RY0 + (RY1 - RY0) * e) * k
    aneis.append([bm.verts.new((CX + rx * (1 + 0.06 * math.sin(3 * a_) * (1 - t)) * math.cos(a_), CY + ry * (1 + 0.06 * math.sin(3 * a_) * (1 - t)) * math.sin(a_), z)) for i in range(LADOS) for a_ in [2 * math.pi * i / LADOS]])
for j in range(ANEIS - 1):
    for i in range(LADOS):
        a, b = aneis[j][i], aneis[j][(i + 1) % LADOS]
        c, d = aneis[j + 1][(i + 1) % LADOS], aneis[j + 1][i]
        bm.faces.new((a, b, c, d))
bm.normal_update()
uv = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    for l in f.loops:
        l[uv].uv = uvp
bm.to_mesh(me); bm.free()
# normais para fora e liso
for p in me.polygons:
    p.use_smooth = True
gola = bpy.data.objects.new("SK_Archer_Gola", me)
bpy.context.scene.collection.objects.link(gola)
gola.parent = capuz.parent
gola.matrix_parent_inverse = capuz.matrix_parent_inverse
gola.matrix_world = capuz.matrix_world.copy()
me.materials.append(mat)
# normais: apontam para fora se o primeiro poligono aponta para longe do eixo
bpy.context.view_layer.objects.active = gola
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode="OBJECT")
# duplo-face: a gola e vista por dentro pelo vazio do capuz? nao: so por fora; mantem 1 face.
for g in ("Chest", "Neck", "Head"):
    gola.vertex_groups.new(name=g)
vg = gola.vertex_groups
for v in me.vertices:
    t = (v.co.z - Z0) / (Z1 - Z0)
    if t < 0.25:
        vg["Chest"].add([v.index], 1.0 - t / 0.25 * 0.5, "REPLACE"); vg["Neck"].add([v.index], t / 0.25 * 0.5, "REPLACE")
    elif t < 0.65:
        vg["Neck"].add([v.index], 1.0, "REPLACE")
    else:
        vg["Neck"].add([v.index], 1.0 - (t - 0.65) / 0.35, "REPLACE"); vg["Head"].add([v.index], (t - 0.65) / 0.35, "REPLACE")
mod = gola.modifiers.new("Armature", "ARMATURE"); mod.object = arm

bpy.ops.object.select_all(action="DESELECT")
for o in [arm] + [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SK_Archer")]:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", use_selection=True, export_animations=False, export_skins=True,
                          export_yup=True, export_apply=False, export_materials="EXPORT", export_image_format="AUTO", export_leaf_bone=False)
print("GOLA OK uv", uvp, "dist", melhor)
