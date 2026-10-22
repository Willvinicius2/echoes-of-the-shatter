"""Folha de revisão do módulo: reimporta o .glb (o que o jogo vai carregar) e renderiza
frente, 3/4, lado, topo, close e wireframe, e monta a folha ao lado da referência.
python3 cc_revisao.py <arquivo.glb> <pasta_saida> <referencia.png> [amostras]"""
import sys, os, math
import bpy
from mathutils import Vector

GLB, OUT, REF = sys.argv[1], sys.argv[2], sys.argv[3]
SAMP = int(sys.argv[4]) if len(sys.argv) > 4 else 32
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
sc = bpy.context.scene
meshes = [o for o in sc.objects if o.type == 'MESH']
lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
ctr = (lo + hi) / 2; ext = hi - lo
print("extensão", tuple(round(e, 2) for e in ext), "tris", sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons))
# Godot/glTF: frente do módulo = -Y do glTF -> após import no Blender fica +Y (mesma convenção do script)

w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.045, 0.055, 0.085, 1); sc.world = w
sun = bpy.data.objects.new("sol", bpy.data.lights.new("sol", 'SUN')); sun.data.energy = 3.2; sun.data.color = (1.0, 0.82, 0.62)
sun.rotation_euler = (-1.0, 0.3, 0.55); sc.collection.objects.link(sun)
fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", 'AREA')); fill.data.energy = 260; fill.data.size = 5; fill.data.color = (0.55, 0.65, 1.0)
fill.location = (-5, 5, 3.5); fill.rotation_euler = (-1.0, 0, 0.0); fill.rotation_euler = (Vector((0, 0, 1.4)) - fill.location).to_track_quat('-Z', 'Y').to_euler(); sc.collection.objects.link(fill)
f2 = bpy.data.objects.new("f2", bpy.data.lights.new("f2", 'AREA')); f2.data.energy = 220; f2.data.size = 5; f2.data.color = (1.0, 0.8, 0.6)
f2.location = (6, 2, 3.5); f2.rotation_euler = (Vector((0, 0, 1.4)) - f2.location).to_track_quat('-Z', 'Y').to_euler(); sc.collection.objects.link(f2)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMP; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 760
alvo = Vector((0, 0, 1.55))
vistas = {  # nome: (posição, lente)
    "frente": (Vector((0, 9.0, 1.9)), 50), "tres_quartos": (Vector((5.4, 6.0, 4.1)), 50),
    "lado": (Vector((9.0, 0, 1.9)), 50), "topo": (Vector((0.01, 4.5, 10.5)), 50),
    "close": (Vector((-2.4, 3.3, 2.9)), 80),
}
arquivos = {}
for nome, (pos, lente) in vistas.items():
    cam.location = pos; cam.data.lens = lente
    a = Vector((-1.6, 0, 2.6)) if nome == "close" else alvo
    cam.rotation_euler = (a - pos).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = arquivos[nome] = os.path.join(OUT, f"rev_{nome}.png")
    bpy.ops.render.render(write_still=True)
# wireframe: material de sobreposição com o nó Wireframe (Cycles, sem GL)
wm = bpy.data.materials.new("wire"); wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear()
wf = nt.nodes.new("ShaderNodeWireframe"); wf.inputs["Size"].default_value = 0.012
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.75, 0.88, 1.0, 1); em.inputs["Strength"].default_value = 3.0
bg = nt.nodes.new("ShaderNodeBsdfDiffuse"); bg.inputs["Color"].default_value = (0.02, 0.025, 0.04, 1)
mx = nt.nodes.new("ShaderNodeMixShader"); out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(wf.outputs["Fac"], mx.inputs[0]); nt.links.new(bg.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
nt.links.new(mx.outputs[0], out.inputs[0])
bpy.context.view_layer.material_override = wm
sun.data.energy = 0.0; fill.data.energy = 0.0; f2.data.energy = 0.0
cam.location = vistas["tres_quartos"][0] * 1.35; cam.rotation_euler = (alvo - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = arquivos["wire"] = os.path.join(OUT, "rev_wireframe.png")
bpy.ops.render.render(write_still=True)

# folha: 3 colunas x 3 linhas com a referência
from PIL import Image, ImageDraw
ordem = ["frente", "tres_quartos", "lado", "topo", "close", "wire"]
S = 520
folha = Image.new("RGB", (S * 3, S * 3 + 0), (20, 22, 30))
ref = Image.open(REF).convert("RGB"); ref.thumbnail((S, S))
folha.paste(ref, (0, 0))
d = ImageDraw.Draw(folha); d.text((8, 8), "REFERENCIA", fill=(255, 255, 255))
slots = [(1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2)]
for nome, (cx, cy) in zip(ordem, slots):
    im = Image.open(arquivos[nome]).convert("RGB").resize((S, S))
    folha.paste(im, (cx * S, cy * S)); ImageDraw.Draw(folha).text((cx * S + 8, cy * S + 8), nome.upper(), fill=(255, 255, 255))
folha.crop((0, 0, S * 3, S * 3)).save(os.path.join(OUT, "folha_revisao.png"))
print("folha pronta")
