"""Prancha de entrega do pilar: frente, 3/4, lado, cima, close da textura e wireframe (PNGs + prancha única).
python3 pilar_prancha.py <pasta_saida>"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pilar_lib as L
import pilar
from mathutils import Vector

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)
o = pilar.montar()
L.stone_preview()
sc = bpy.context.scene


def cena(luz=True):
    for ob in list(bpy.data.objects):
        if ob.type in ('CAMERA', 'LIGHT'): bpy.data.objects.remove(ob, do_unlink=True)
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam)
    sun = bpy.data.objects.new("s", bpy.data.lights.new("s", 'SUN')); sun.data.energy = 4.0; sun.data.color = (1.0, 0.88, 0.72); sun.rotation_euler = (0.9, 0.25, 0.7)
    fill = bpy.data.objects.new("f", bpy.data.lights.new("f", 'SUN')); fill.data.energy = 1.2; fill.data.color = (0.8, 0.85, 1.0); fill.rotation_euler = (1.2, 0, -2.2)
    for x in (sun, fill): bpy.context.collection.objects.link(x)
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.12, 0.13, 0.17, 1); sc.world = w
    return cam


def tirar(nome, alvo, direcao, dist, lente=60, wire=False, ortho=False, samples=40):
    cam = cena()
    cam.data.lens = lente
    if ortho:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = dist
        cam.location = alvo + Vector(direcao).normalized() * 20
    else:
        cam.location = alvo + Vector(direcao).normalized() * dist
    cam.rotation_euler = (alvo - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sc.render.resolution_x = 720; sc.render.resolution_y = 720
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 16 if wire else samples; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = not wire
    if wire:
        # wireframe por material: nó Wireframe (em pixels) emissivo, fundo escuro; vale sem GPU
        m = bpy.data.materials.new("wf"); m.use_nodes = True; N = m.node_tree.nodes; Lk = m.node_tree.links
        N.clear(); wf = N.new("ShaderNodeWireframe"); wf.use_pixel_size = True; wf.inputs["Size"].default_value = 1.0
        em = N.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 3.0
        bg = N.new("ShaderNodeBsdfDiffuse"); bg.inputs["Color"].default_value = (0.02, 0.02, 0.03, 1)
        mx = N.new("ShaderNodeMixShader"); out = N.new("ShaderNodeOutputMaterial")
        Lk.new(wf.outputs["Fac"], mx.inputs["Fac"]); Lk.new(bg.outputs[0], mx.inputs[1]); Lk.new(em.outputs[0], mx.inputs[2]); Lk.new(mx.outputs[0], out.inputs["Surface"])
        bpy.context.view_layer.material_override = m
    else:
        bpy.context.view_layer.material_override = None
    sc.render.filepath = os.path.join(OUT, f"pilar_{nome}.png")
    bpy.ops.render.render(write_still=True)


c = Vector((0, 0, 3.3)); d = 12.0
tirar("a_frente", c, (0, 1, 0.2), d)
tirar("b_tres_quartos", c, (0.8, 1, 0.55), d)
tirar("c_lado", c, (1, 0, 0.2), d)
tirar("d_cima", Vector((0, 0, 4.5)), (0.3, 0.6, 1.8), 12)
tirar("e_close_textura", Vector((-0.9, -0.4, 3.2)), (-1, -0.6, 0.15), 3.2, lente=85)
tirar("f_wireframe", c, (0.8, 1, 0.55), d, wire=True)
from PIL import Image
nomes = ["a_frente", "b_tres_quartos", "c_lado", "d_cima", "e_close_textura", "f_wireframe"]
ims = [Image.open(os.path.join(OUT, f"pilar_{n}.png")).convert("RGB").resize((480, 480)) for n in nomes]
sheet = Image.new("RGB", (480 * 3, 480 * 2))
for i, im in enumerate(ims): sheet.paste(im, ((i % 3) * 480, (i // 3) * 480))
sheet.save(os.path.join(OUT, "pilar_prancha.png"))
print("ok", OUT)
