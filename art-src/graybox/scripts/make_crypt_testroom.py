"""Cena de teste da Cripta Partida: sala de 16 x 16 m montada com o kit, o Guerreiro e 3 inimigos comuns.

Depende de crypt_kit_graybox.blend, heroes_graybox.blend e enemies_graybox.blend (rodar os outros scripts antes).
As pecas sao instancias que compartilham a malha do kit (como prefabs). O relatorio traz a montagem em
coordenadas do Unity para o Frontend refazer a sala com os prefabs.
Sala: x, y em [-8, 8] no Blender; porta (arco) no meio da parede oeste (x = -8), escada do lado de fora.
"""
import bpy, sys, os, json, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gb_lib import *

KIT = ["SM_Cripta_Floor_2x2_A", "SM_Cripta_Floor_2x2_B", "SM_Cripta_Wall_2m_A", "SM_Cripta_WallCorner_A",
       "SM_Cripta_Pillar_A", "SM_Cripta_Arch_A", "SM_Cripta_Stairs_A", "SM_Cripta_Sarcophagus_A",
       "SM_Cripta_Brazier_A", "SM_Cripta_BonePile_A"]
ENEMIES = ["SM_Enemy_HollowSentinel", "SM_Enemy_AshHound", "SM_Enemy_GhostArcher"]

reset()
with bpy.data.libraries.load(f"{ROOT}/crypt_kit_graybox.blend", link=False) as (src, dst):
    dst.meshes = list(KIT)
meshes = {m.name: m for m in dst.meshes}
root = new_coll("TestRoom_Cripta")
colls = {k: new_coll(k, root) for k in ("Floor", "Walls", "Props", "Characters")}
layout = []


def place(asset, coll, x, y, rot_deg=0.0, label=None):
    ob = bpy.data.objects.new(label or asset, meshes[asset])
    colls[coll].objects.link(ob)
    ob.location = (x, y, 0.0)
    ob.rotation_euler = (0, 0, math.radians(rot_deg))
    layout.append(dict(asset=asset, name=ob.name, group=coll, blender_pos=[x, y, 0.0], blender_rot_z=rot_deg))
    return ob


# piso 8 x 8 ladrilhos; os 4 do meio formam o anel dourado de Marco
odd = [-7, -5, -3, -1, 1, 3, 5, 7]
ring_rot = {(1, 1): 0, (-1, 1): 90, (-1, -1): 180, (1, -1): 270}
for x in odd:
    for y in odd:
        if (x, y) in ring_rot:
            place("SM_Cripta_Floor_2x2_B", "Floor", x, y, ring_rot[(x, y)])
        else:
            place("SM_Cripta_Floor_2x2_A", "Floor", x, y)
for y in (-1, 1):                                       # patamar do lado de fora da porta
    place("SM_Cripta_Floor_2x2_A", "Floor", -9, y)
place("SM_Cripta_Stairs_A", "Props", -11, 0, 90)          # sobe para -X, para longe da sala

# paredes: 8 modulos de 2 m por lado, torres nos cantos, arco de 4 m no lugar de 2 modulos na parede oeste
for cx, cy in ((-8, -8), (8, -8), (8, 8), (-8, 8)):
    place("SM_Cripta_WallCorner_A", "Walls", cx, cy)
for c in odd:
    place("SM_Cripta_Wall_2m_A", "Walls", c, -8)            # sul
    place("SM_Cripta_Wall_2m_A", "Walls", c, 8)             # norte
    place("SM_Cripta_Wall_2m_A", "Walls", 8, c, 90)         # leste
    if c not in (-1, 1):
        place("SM_Cripta_Wall_2m_A", "Walls", -8, c, 90)    # oeste
place("SM_Cripta_Arch_A", "Walls", -8, 0, 90)

for x, y in ((-4, -4), (4, -4), (4, 4), (-4, 4)):
    place("SM_Cripta_Pillar_A", "Props", x, y)
for y in (-2.8, 2.8):
    place("SM_Cripta_Brazier_A", "Props", -7.0, y)
for x, y, r in ((-2.0, -6.6, 0), (2.0, -6.6, 0), (-6.6, 5.5, 90)):
    place("SM_Cripta_Sarcophagus_A", "Props", x, y, r)
for x, y, r in ((-3.2, 4.8, 20), (4.6, 1.8, 130), (1.8, -4.8, 250), (-5.4, -5.4, 75)):
    place("SM_Cripta_BonePile_A", "Props", x, y, r)

# personagens (frente -Y no Blender; rotacao theta faz a frente apontar para (sin theta, -cos theta))
with bpy.data.libraries.load(f"{ROOT}/heroes_graybox.blend", link=False) as (src, dst):
    dst.collections = ["SK_Warrior"]
wc = dst.collections[0]
colls["Characters"].children.link(wc)
hero = [o for o in wc.objects if o.type == 'ARMATURE'][0]
with bpy.data.libraries.load(f"{ROOT}/enemies_graybox.blend", link=False) as (src, dst):
    dst.objects = list(ENEMIES)
for o in dst.objects:
    colls["Characters"].objects.link(o)
hero_pos = Vector((0.6, 0.3, 0))
chars = [(hero, "SK_Warrior", hero_pos)] + [(bpy.data.objects[n], n, Vector(p)) for n, p in
                                             zip(ENEMIES, ((-3.0, -1.6, 0), (-2.6, 1.9, 0), (-5.2, 0.4, 0)))]
for ob, asset, pos in chars:
    target = Vector((-6.0, 0.3, 0)) if ob is hero else hero_pos
    d = target - pos
    rot = math.degrees(math.atan2(d.x, -d.y))
    ob.location = pos
    ob.rotation_euler = (0, 0, math.radians(rot))
    layout.append(dict(asset=asset, name=ob.name, group="Characters", blender_pos=[round(pos.x, 3), round(pos.y, 3), 0.0],
                       blender_rot_z=round(rot, 2)))

for e in layout:
    p = e["blender_pos"]
    e["unity_pos"] = [round(c, 3) + 0.0 for c in to_unity(p)]
    e["unity_rot_y"] = round((-e["blender_rot_z"] + 180) % 360 - 180, 2) + 0.0

# previas
bpy.context.view_layer.update()
setup_render(1920, 1080)
mn, mx = bbox([o for o in root.all_objects if o.type == 'MESH' and o.data.name in KIT])
cam_over = game_camera((-1.2, 0.0, 0.0), 60, ortho_scale=27.0)
cam_over.name = "Cam_Overview"
render(f"{PREV}/crypt_testroom_overview.png")
# vista de cima na orientacao do Unity: +X do Unity para a direita, +Z do Unity para cima
cam_top = game_camera((-1.75, 0.0, 0.0), 60, ortho_scale=31.5, yaw=0, pitch=-89.9)
cam_top.name = "Cam_Top"
render(f"{PREV}/crypt_testroom_top.png")
# camera do jogo (docs/04 secao 3.2): pitch 55, yaw 45, FOV vertical 14,2 graus, 42 m, alvo = heroi + 0,52 m.
# Paredes norte e leste (entre a camera e a sala) escondidas, como o fade de oclusao do jogo (04 secao 3.7).
near = [o for o in colls["Walls"].objects if o.location.x > 7 or o.location.y > 7]
for o in near:
    o.hide_render = True
cam_game = game_camera(hero_pos + Vector((0, 0, 0.52)), 42.0, fov_v=14.2)
cam_game.name = "Cam_Game"
render(f"{PREV}/crypt_testroom_game.png")
from bpy_extras.object_utils import world_to_camera_view
sc = bpy.context.scene
body = [o for o in hero.children if o.name.startswith("SK_Warrior_Body")][0]
pts = [body.matrix_world @ v.co for v in body.data.vertices]          # so o corpo (sem martelo e escudo)
vs = [world_to_camera_view(sc, cam_game, p).y for p in pts]
hero_px = round((max(vs) - min(vs)) * sc.render.resolution_y)
for o in near:
    o.hide_render = False
bpy.context.scene.camera = cam_game

counts = {}
room_tris = 0
for e in layout:
    counts[e["asset"]] = counts.get(e["asset"], 0) + 1
for o in root.all_objects:
    if o.type == 'MESH':
        room_tris += tris(o)
report = dict(version=version_info(), file="crypt_testroom_graybox.blend", room_m=[16, 16],
              blender_bounds=dict(min=[round(c, 3) for c in mn], max=[round(c, 3) for c in mx]),
              unity_bounds=unity_bounds(mn, mx), instances=counts, scene_tris=room_tris,
              hidden_in_game_preview=sorted(o.name for o in near),
              game_camera=dict(pitch=55, yaw=45, fov_vertical=14.2, distance=42, target="heroi + (0, 0,52, 0)",
                               hero_height_px_1080p=hero_px),
              layout=layout)
save_blend(f"{ROOT}/crypt_testroom_graybox.blend")
json.dump(report, open(f"{PREV}/_crypt_testroom_report.json", "w"), indent=1)
print("REPORT", json.dumps(dict(instances=counts, scene_tris=room_tris, hero_px=hero_px)))
