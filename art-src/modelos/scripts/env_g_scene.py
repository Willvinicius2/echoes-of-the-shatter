"""Cena de teste do kit da Cripta (Blender, Eevee): 3 x 3 pisos de 2 m, paredes, canto, pilares, arco, escada e props
montados na grade, importados dos FBX finais (testa o artefato real) e renderizados com a camera do jogo
(pitch 55, yaw 45, FOV vertical 14,2). Grava OUT/cena_teste_jogo.png (56 m), OUT/cena_teste_perto.png e OUT/cena_teste_cripta.blend.
Blender: x,y do chao; a camera do jogo fica em +X+Y olhando para -X-Y (docs/04 3.2), entao as paredes do fundo ficam em
x = -3 e y = -3 com a face de frente (-Y da peca) virada para a sala; props giram para a camera.
"""
import bpy, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_common import *
from mathutils import Vector
gb = import_graybox()

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
cache = {}


def put(pid, x, y, rz=0.0, z=0.0, name=None):
    asset = cfg_for(pid)["asset"]
    if pid not in cache:
        bpy.ops.import_scene.fbx(filepath=f"{OUT_ROOT}/{asset}.fbx")
        o = [o for o in bpy.context.selected_objects if o.type == 'MESH'][0]
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)     # o importador do FBX traz giro/escala do eixo
        cache[pid] = o
        o.location = (0, 0, -50)
        src = o
        o = src
    else:
        src = cache[pid]
        o = src.copy(); sc.collection.objects.link(o)       # instancia a malha e o material
    o.location = (x, y, z); o.rotation_euler = (0, 0, math.radians(rz))
    o.name = name or asset
    return o


FACE = 135.0     # giro em Z que vira a frente (-Y) da peca para a camera (+X+Y)
# 3 x 3 pisos de 2 m, centros em -2, 0, 2
for i, x in enumerate((-2, 0, 2)):
    for j, y in enumerate((-2, 0, 2)):
        pid = "piso_runa" if (i, j) == (1, 1) else "piso_quebrado" if (i, j) == (2, 0) else "piso_liso"
        put(pid, x, y)
# paredes do fundo: sul (y = -3, de frente para +Y, gira 180) e oeste (x = -3, gira 90)
put("parede_reta", -2, -3, 180); put("parede_reta", 0, -3, 180); put("parede_ruina", 2, -3, 180)
put("parede_reta", -3, -2, 90); put("arco_ruina", -3, 0.0, 90, name="arco"); put("parede_reta", -3, 2.8, 90)
put("parede_canto_a", -3.3, -3.3, 0)
# pilares, escada, portais
put("pilar_inteiro", 3.2, -3.2); put("pilar_inteiro", -3.2, 3.2); put("pilar_quebrado", 3.8, 3.6)
put("escada", 4.0, 0.0, -90)
put("portal_porta", 0, -3.6, 180, z=-50)      # fora de cena (so valida o import)
# props
put("braseiro", -2.3, -2.3, 0); put("braseiro", 2.6, 2.4, 0)
put("sarcofago_fechado", -1.2, 0.2, FACE - 30); put("sarcofago_aberto", 1.6, -1.2, FACE + 10)
put("velas", 0.2, -0.6, FACE); put("velas", -2.2, 1.9, FACE + 40)
put("ossos", -0.6, 1.5, FACE + 20); put("estandarte", -2.7, -0.9, 90)
put("abismo_bordo", 0, 3.6, 0); put("abismo_bordo", 2.0, 3.6, 0)
put("ruina_grande", -4.8, 2.6, FACE); put("bloco_a", 3.3, -4.2, 20); put("bloco_b", -1.4, -4.4, 0)
put("bloco_c", 1.0, -4.8, 60); put("bloco_d", -4.6, -1.8, 10)
put("pedra_e", -0.6, -1.1, 30); put("pedra_f", 1.2, 1.1, 80); put("pedra_e", 3.6, 1.8, 140)
for o in list(cache.values()):
    if o.location.z < -40: bpy.data.objects.remove(o)       # cabecas originais fora de cena
for o in [o for o in sc.objects if o.type == 'MESH' and o.location.z < -40]:
    bpy.data.objects.remove(o)

try:
    sc.render.engine = 'BLENDER_EEVEE'
except TypeError:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.09, 0.075, 0.12, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sc.world = w
def light(name, kind, energy, rot, color=(1, 1, 1), loc=(0, 0, 8)):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    lo = bpy.data.objects.new(name, ld); lo.rotation_euler = rot; lo.location = loc; sc.collection.objects.link(lo); return lo
light("sol", 'SUN', 3.2, (math.radians(55), 0, math.radians(35)), (1.0, 0.88, 0.72))
light("ceu", 'SUN', 1.0, (math.radians(70), 0, math.radians(200)), (0.55, 0.5, 0.9))
for x, y in ((-2.3, -2.3), (2.6, 2.4)):
    light("fogo", 'POINT', 900, (0, 0, 0), (1.0, 0.55, 0.2), loc=(x, y, 1.3))
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT_ROOT}/cena_teste_cripta.blend", compress=True)

tgt = (0, 0, 0.6)
for name, dist, w_, h_ in (("jogo", 56.0, 1920, 1080), ("perto", 30.0, 1920, 1080)):
    sc.render.resolution_x, sc.render.resolution_y = w_, h_
    for o in [o for o in sc.objects if o.type == 'CAMERA']: bpy.data.objects.remove(o)
    gb.game_camera(tgt, dist, fov_v=14.2, yaw=45.0, pitch=-55.0)
    sc.render.filepath = f"{OUT_ROOT}/cena_teste_{name}.png"
    bpy.ops.render.render(write_still=True)
print("EG ok", sc.render.engine, len([o for o in sc.objects if o.type == 'MESH']), "malhas")
