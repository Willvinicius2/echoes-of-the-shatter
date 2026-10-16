"""Inimigos do Ato I + chefe Guardiao da Cripta (graybox, sem esqueleto).

Descritos em espaco do personagem (frente +Y, pivo nos pes); build(turn=True) deixa a frente em -Y no Blender
(+Z no Unity). Inclui o teste de silhueta do docs/03 secao 3.5 (preto sobre #6A5A55, 64 px de altura).
"""
import bpy, sys, os, json, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gb_lib import *

GOLD = '#D9A441'
EYE = '#FFC040'


def sentinel():
    b = Builder("SM_Enemy_HollowSentinel")
    steel, dark, red = '#8E8A96', '#4A4650', '#8A2A2A'
    for sx in (-1, 1):
        b.add('box', (0.20, 0.30, 0.12), (sx * 0.13, 0.04, 0.06), '#3A3640')
        b.limb((sx * 0.13, 0, 0.12), (sx * 0.13, 0, 0.50), 0.075, dark)
        b.add('sph', (0.20, 0.18, 0.16), (sx * 0.24, 0, 1.02), steel, seg=6)
        b.limb((sx * 0.24, 0, 1.02), (sx * 0.34, 0.05, 0.66), 0.06, steel)
        b.add('sph', (0.12, 0.12, 0.12), (sx * 0.36, 0.08, 0.60), dark, seg=6)
    b.add('box', (0.40, 0.26, 0.16), (0, 0, 0.58), red)
    b.add('box', (0.44, 0.28, 0.40), (0, 0, 0.86), steel)
    b.add('box', (0.28, 0.30, 0.20), (0, 0, 0.84), dark)  # oco no peito
    b.add('cyl', (0.12, 0.12, 0.08), (0, 0, 1.08), dark, seg=6)
    b.add('sph', (0.46, 0.44, 0.48), (0, 0, 1.34), steel)
    b.add('box', (0.30, 0.06, 0.10), (0, 0.21, 1.34), '#1A1A20')
    b.add('box', (0.06, 0.04, 0.04), (-0.07, 0.235, 1.34), EYE, emit=True, matname="GB_Eye")
    b.add('box', (0.06, 0.04, 0.04), (0.07, 0.235, 1.34), EYE, emit=True, matname="GB_Eye")
    b.add('box', (0.07, 0.34, 0.12), (0, -0.02, 1.58), red)
    # escudo (esq) e espada (dir)
    b.add('box', (0.07, 0.40, 0.56), (-0.46, 0.14, 0.78), red)
    b.add('box', (0.09, 0.34, 0.50), (-0.48, 0.14, 0.78), steel)
    h = Vector((0.36, 0.08, 0.60)); d = Vector((0, 0.7, 0.7)).normalized(); R = aim((0, 0, 0), d)
    b.add('box', (0.20, 0.05, 0.04), h + d * 0.08, GOLD, rot=R)
    b.add('box', (0.08, 0.025, 0.50), h + d * 0.36, '#C8CCD4', rot=R)
    return b


def hound():
    b = Builder("SM_Enemy_AshHound")
    fur, dark, mane = '#8A8580', '#55504C', '#C0392B'
    for sx in (-1, 1):
        for y in (-0.38, 0.32):
            b.limb((sx * 0.14, y, 0.0), (sx * 0.14, y, 0.46), 0.06, dark, taper=1.3, seg=6)
    b.add('box', (0.40, 0.95, 0.38), (0, 0, 0.55), fur)
    b.add('box', (0.40, 0.40, 0.46), (0, 0.38, 0.62), fur)       # peito
    b.add('box', (0.30, 0.36, 0.28), (0, 0.66, 0.70), fur)       # cabeca
    b.add('box', (0.16, 0.26, 0.12), (0, 0.90, 0.62), dark)      # focinho
    b.add('box', (0.08, 0.05, 0.05), (0.0, 1.04, 0.66), '#1A1A20')
    for sx in (-1, 1):
        b.add('cyl', (0.12, 0.08, 0.20), (sx * 0.11, 0.58, 0.88), dark, taper=0.1, seg=4)   # orelhas, topo 0.98?
        b.add('box', (0.05, 0.04, 0.05), (sx * 0.10, 0.80, 0.72), EYE, emit=True, matname="GB_Eye")
    for i, (y, z) in enumerate(((0.30, 0.86), (0.10, 0.80), (-0.10, 0.76))):
        b.add('cyl', (0.14, 0.14, 0.20), (0, y, z + 0.05), mane, taper=0.1, seg=4)         # juba em espinhos
    b.limb((0, -0.46, 0.60), (0, -0.78, 0.78), 0.05, mane, taper=0.5, seg=6)               # cauda
    return b


def herald():
    b = Builder("SM_Enemy_StoneHerald")
    stone, dark, moss = '#A89F90', '#6E675C', '#5B7A3A'
    for sx in (-1, 1):
        b.add('box', (0.50, 0.55, 0.70), (sx * 0.30, 0, 0.35), stone)
        b.add('box', (0.56, 0.40, 0.14), (sx * 0.30, 0.10, 0.07), dark)
        b.limb((sx * 0.85, 0, 1.40), (sx * 1.00, 0.20, 0.72), 0.22, stone, seg=6)
        b.add('box', (0.46, 0.46, 0.46), (sx * 1.00, 0.25, 0.46), dark, rot=(0, 0, 15 * sx))
        b.add('box', (0.50, 0.50, 0.36), (sx * 0.85, 0, 1.45), dark, rot=(10, 0, 20 * sx))   # ombreira
    b.add('box', (0.96, 0.60, 0.30), (0, 0, 0.85), dark)
    b.add('box', (1.30, 0.80, 0.55), (0, 0, 1.275), stone)
    b.add('box', (0.50, 0.04, 0.30), (0, 0.42, 1.30), moss)
    b.add('box', (0.56, 0.50, 0.40), (0, 0.04, 1.75), stone)
    b.add('sph', (0.20, 0.10, 0.20), (0, 0.27, 1.75), '#FF9A2E', emit=True, matname="GB_EyeOrange", seg=6)
    b.add('box', (0.20, 0.20, 0.12), (0.18, -0.05, 1.90), dark, rot=(0, 0, 25))              # pedra do topo, topo 1.95
    return b


def ghost_archer():
    b = Builder("SM_Enemy_GhostArcher")
    cy, dk = '#4FC8D8', '#1E5F6B'
    b.add('cyl', (0.80, 0.70, 0.95), (0, 0, 0.625), cy, taper=0.30, seg=8, matname="GB_Ghost")
    for i, x in enumerate((-0.28, -0.10, 0.10, 0.28)):
        b.add('box', (0.14, 0.04, 0.26), (x, 0.0 + 0.1 * (i % 2), 0.15), dk, rot=(0, 0, 10 * (i - 1.5)))
    b.add('box', (0.34, 0.24, 0.30), (0, 0, 0.98), cy, matname="GB_Ghost")
    b.add('sph', (0.44, 0.42, 0.42), (0, -0.02, 1.26), cy, matname="GB_Ghost")
    b.add('cyl', (0.30, 0.30, 0.20), (0, -0.05, 1.40), cy, taper=0.12, seg=6, matname="GB_Ghost")
    b.add('box', (0.28, 0.05, 0.12), (0, 0.19, 1.24), '#0E2A30')
    b.add('box', (0.05, 0.04, 0.04), (-0.06, 0.215, 1.24), '#FFFFFF', emit=True, matname="GB_EyeWhite")
    b.add('box', (0.05, 0.04, 0.04), (0.06, 0.215, 1.24), '#FFFFFF', emit=True, matname="GB_EyeWhite")
    # arco esticado a frente
    pts = [(-0.18, 0.46, 0.55), (-0.18, 0.54, 0.80), (-0.18, 0.48, 1.00), (-0.18, 0.54, 1.20), (-0.18, 0.46, 1.45)]
    for a, c in zip(pts[:-1], pts[1:]):
        b.limb(a, c, 0.025, dk, seg=6)
    b.add('box', (0.012, 0.012, 0.90), (-0.18, 0.30, 1.00), '#E8F8FF')
    b.limb((-0.17, 0.0, 1.02), (-0.18, 0.44, 1.00), 0.05, cy, seg=6, matname="GB_Ghost")  # braco que segura
    b.limb((0.17, 0.0, 1.02), (-0.15, 0.28, 1.00), 0.05, cy, seg=6, matname="GB_Ghost")
    return b


def guardian():
    b = Builder("SM_Boss_CryptGuardian")
    steel, dark, red, stone = '#8E8A96', '#4A4650', '#B02A22', '#A89F90'
    for sx in (-1, 1):
        b.add('box', (0.95, 1.20, 0.35), (sx * 0.55, 0.12, 0.175), '#3A3640')
        b.add('box', (0.85, 0.85, 1.20), (sx * 0.55, 0, 0.95), dark)
        b.add('box', (0.95, 0.95, 0.50), (sx * 0.55, 0.05, 1.70), steel)             # coxa/joelheira
        b.add('sph', (1.20, 1.10, 0.90), (sx * 1.45, 0, 3.15), steel, seg=8)         # ombreira
    b.add('box', (1.90, 1.10, 0.55), (0, 0, 2.00), red)                              # saia/pelve
    b.add('box', (2.30, 1.30, 1.40), (0, 0, 2.95), steel)
    b.add('box', (1.40, 0.10, 1.00), (0, 0.70, 2.85), red)                           # tabardo
    b.add('box', (1.70, 1.35, 0.18), (0, 0, 2.38), GOLD)                             # cinto
    b.add('cyl', (0.70, 0.70, 0.30), (0, 0, 3.75), dark, seg=8)
    b.add('sph', (1.60, 1.50, 1.50), (0, 0, 4.25), steel, seg=10)                    # elmo
    b.add('box', (1.05, 0.18, 0.28), (0, 0.72, 4.25), '#1A1A20')
    b.add('box', (0.22, 0.12, 0.14), (-0.22, 0.80, 4.25), EYE, emit=True, matname="GB_Eye")
    b.add('box', (0.22, 0.12, 0.14), (0.22, 0.80, 4.25), EYE, emit=True, matname="GB_Eye")
    b.add('box', (0.28, 1.10, 0.35), (0, -0.10, 4.85), red)                          # pluma, topo 5.02
    # braco direito + martelo (stone) no chao a frente
    b.limb((1.45, 0, 3.15), (1.75, 0.70, 2.10), 0.34, steel, seg=6)
    b.add('sph', (0.55, 0.55, 0.55), (1.75, 0.75, 2.00), dark, seg=6)
    hd = Vector((0, 0.45, -0.89)).normalized()
    hand = Vector((1.75, 0.75, 2.00))
    b.limb(hand - hd * 0.9, hand + hd * 1.5, 0.11, '#7A5230', seg=6)
    # cabeca do martelo apoiada no chao (antes furava o piso em 12 cm)
    b.add('box', (1.50, 0.90, 0.90), hand + hd * 1.56, stone, rot=aim((0, 0, 0), hd))
    b.add('box', (1.55, 0.30, 0.60), hand + hd * 1.56, GOLD, rot=aim((0, 0, 0), hd))
    # braco esquerdo + escudo
    b.limb((-1.45, 0, 3.15), (-1.85, 0.55, 2.30), 0.34, steel, seg=6)
    b.add('sph', (0.55, 0.55, 0.55), (-1.85, 0.60, 2.20), dark, seg=6)
    b.add('box', (0.35, 1.90, 2.80), (-2.10, 0.90, 2.00), red)
    b.add('box', (0.40, 1.60, 2.50), (-2.15, 0.90, 2.00), steel)
    b.add('sph', (0.55, 0.55, 0.55), (-2.35, 0.90, 2.15), GOLD, seg=6)
    return b


report = dict(version=version_info(), enemies={})
reset()
items = [(sentinel, "SM_Enemy_HollowSentinel"), (hound, "SM_Enemy_AshHound"),
         (herald, "SM_Enemy_StoneHerald"), (ghost_archer, "SM_Enemy_GhostArcher"),
         (guardian, "SM_Boss_CryptGuardian")]
objs = {}
for fn, name in items:
    coll = new_coll(name)
    ob = fn().build(coll, turn=True)
    ob.name = name
    mn, mx = bbox([ob])
    report["enemies"][name] = dict(file=f"fbx/{name}.fbx", height=round(mx.z - mn.z, 3), foot_z=round(mn.z, 3) + 0.0,
                                   unity=unity_bounds(mn, mx), tris=tris(ob),
                                   materials=[m.name for m in ob.data.materials])
    export_fbx([ob], f"{FBX}/{name}.fbx")
    objs[name] = ob
save_blend(f"{ROOT}/enemies_graybox.blend")

# previas: inimigos virados para a camera, com o Guerreiro de referencia; chefe a parte
fl = Builder("Preview_Floor")
fl.add('box', (40, 40, 0.05), (0, 0, -0.025), '#6A5A55')
floor = fl.build()
setup_render(1600, 900)


def append_hero(key):
    with bpy.data.libraries.load(f"{ROOT}/heroes_graybox.blend", link=False) as (src, dst):
        dst.collections = [f"SK_{key}"]
    c = dst.collections[0]
    bpy.context.scene.collection.children.link(c)
    return [o for o in c.objects if o.type == 'ARMATURE'][0]


right = Vector((-0.7071, 0.7071, 0))           # direita da tela com a camera do jogo
ref = append_hero("Warrior")
row = [(ref, -1.9), (objs["SM_Enemy_HollowSentinel"], 0.0), (objs["SM_Enemy_AshHound"], 1.9),
       (objs["SM_Enemy_StoneHerald"], 4.0), (objs["SM_Enemy_GhostArcher"], 6.1)]
for o, x in row:
    o.location = right * x
    o.rotation_euler = (0, 0, math.pi)
objs["SM_Boss_CryptGuardian"].location = (60, 60, 0)
center = right * 2.1
cam = game_camera((center.x, center.y, 0.8), 30, ortho_scale=10.0)
render(f"{PREV}/enemies_lineup.png")
# chefe com o heroi ao lado
for o, x in row[1:]:
    o.location = (60, 60, 0)
g = objs["SM_Boss_CryptGuardian"]
g.location = (0, 0, 0)
g.rotation_euler = (0, 0, math.pi)
ref.location = right * -3.6
bpy.data.objects.remove(cam)
cam = game_camera((-0.8, 0.8, 1.5), 30, ortho_scale=13.0)
render(f"{PREV}/boss_guardian.png")
bpy.data.objects.remove(cam)

# teste de silhueta (docs/03 secao 3.5): preto sobre #6A5A55, camera do jogo, ~64 px de altura por heroi
g.location = (60, 60, 0)
heroes = [ref, append_hero("Archer"), append_hero("Mage")]
line = heroes + [objs[n] for n in ("SM_Enemy_HollowSentinel", "SM_Enemy_AshHound",
                                   "SM_Enemy_StoneHerald", "SM_Enemy_GhostArcher")]
xs = [-6.2, -4.9, -3.6, -1.9, 0.0, 2.1, 4.3]
for o, x in zip(line, xs):
    o.location = right * x
    o.rotation_euler = (0, 0, math.pi)
sc = bpy.context.scene
sh = sc.display.shading
sh.light, sh.color_type, sh.show_shadows, sh.show_object_outline = 'FLAT', 'OBJECT', False, False
for o in bpy.data.objects:
    o.color = (0.0, 0.0, 0.0, 1.0)
floor.color = (0.144, 0.102, 0.091, 1.0)           # #6A5A55 (cor do objeto em linear)
sh.background_color = (0.144, 0.102, 0.091)         # o mesmo #6A5A55 em linear
sc.view_settings.exposure = 0.0                     # sem ganho: o fundo tem de sair exatamente #6A5A55
sc.render.resolution_x, sc.render.resolution_y = 880, 200
cam = game_camera((right * -0.9).to_tuple()[:2] + (0.6,), 30, ortho_scale=15.0)
render(f"{PREV}/silhouette_test_64px.png")
json.dump(report, open(f"{PREV}/_enemies_report.json", "w"), indent=1)
print("REPORT", json.dumps({k: (v["height"], v["foot_z"], v["tris"]) for k, v in report["enemies"].items()}))
