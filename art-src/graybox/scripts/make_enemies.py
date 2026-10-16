"""Inimigos do Ato I + chefe Guardiao da Cripta (graybox, sem esqueleto). Frente = +Y, pivo nos pes."""
import bpy, sys, os, json
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
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
    b.limb(hand - hd * 0.9, hand + hd * 1.6, 0.11, '#7A5230', seg=6)
    b.add('box', (1.50, 0.90, 0.90), hand + hd * 1.7 + Vector((0, 0, 0.0)), stone, rot=aim((0, 0, 0), hd))
    b.add('box', (1.55, 0.30, 0.60), hand + hd * 1.7, GOLD, rot=aim((0, 0, 0), hd))
    # braco esquerdo + escudo
    b.limb((-1.45, 0, 3.15), (-1.85, 0.55, 2.30), 0.34, steel, seg=6)
    b.add('sph', (0.55, 0.55, 0.55), (-1.85, 0.60, 2.20), dark, seg=6)
    b.add('box', (0.35, 1.90, 2.80), (-2.10, 0.90, 2.00), red)
    b.add('box', (0.40, 1.60, 2.50), (-2.15, 0.90, 2.00), steel)
    b.add('sph', (0.55, 0.55, 0.55), (-2.35, 0.90, 2.15), GOLD, seg=6)
    return b


def make(builder_fn, fname, coll=None):
    b = builder_fn()
    ob = b.build(coll)
    return ob


report = {}
reset()
items = [(sentinel, "SM_Enemy_HollowSentinel"), (hound, "SM_Enemy_AshHound"),
         (herald, "SM_Enemy_StoneHerald"), (ghost_archer, "SM_Enemy_GhostArcher"),
         (guardian, "SM_Boss_CryptGuardian")]
objs = {}
for fn, name in items:
    coll = new_coll(name)
    ob = make(fn, name, coll)
    ob.name = name
    mn, mx = bbox([ob])
    report[name] = dict(h=round(mx.z - mn.z, 3), z0=round(mn.z, 3), w=round(mx.x - mn.x, 3), d=round(mx.y - mn.y, 3),
                        tris=tris(ob), mats=len(ob.data.materials))
    export_fbx([ob], f"{FBX}/{name}.fbx")
    objs[name] = ob
save_blend(f"{ROOT}/enemies_graybox.blend")

# previa: inimigos comuns em fila com heroi de referencia; chefe a parte
fl = Builder("Preview_Floor")
fl.add('box', (30, 30, 0.05), (0, 0, -0.025), '#6A5A55')
fl.build()
setup_render(1600, 800)
bpy.ops.object.light_add(type='SUN', location=(3, 3, 6))
with bpy.data.libraries.load(f"{ROOT}/heroes_graybox.blend", link=False) as (src, dst):
    dst.collections = ["SK_Warrior"]
wc = dst.collections[0]
bpy.context.scene.collection.children.link(wc)
for o in wc.objects:
    if o.type == 'ARMATURE':
        o.location = (0, 0, 0)
S = 0.7071
row = [("ref", -1.8)] + [(n, x) for (n, x) in (("SM_Enemy_HollowSentinel", 0.0), ("SM_Enemy_AshHound", 1.8),
                                               ("SM_Enemy_StoneHerald", 3.6), ("SM_Enemy_GhostArcher", 5.6))]
for n, x in row:
    o = wc.objects[0] if n == "ref" else objs[n]
    if n == "ref":
        o = [q for q in wc.objects if q.type == 'ARMATURE'][0]
    o.location = (x * S, -x * S, 0)
objs["SM_Boss_CryptGuardian"].location = (50, 50, 0)
cam = game_camera((2.0 * S, -2.0 * S, 0.8), 30, ortho_scale=9.0)
render(f"{PREV}/enemies_lineup.png")
# chefe com heroi ao lado
objs["SM_Boss_CryptGuardian"].location = (0, 0, 0)
for n in list(objs):
    if n != "SM_Boss_CryptGuardian":
        objs[n].location = (50, 50, 0)
arm = [q for q in wc.objects if q.type == 'ARMATURE'][0]
arm.location = (4.0 * S, -4.0 * S, 0)
cam.data.ortho_scale = 11.0
cam.location = Vector((0.5, 0, 2.2)) + (cam.location - Vector((2.0 * S, -2.0 * S, 0.8)))
render(f"{PREV}/boss_guardian.png")
json.dump(report, open(f"{PREV}/_enemies_report.json", "w"), indent=1)
print("REPORT", json.dumps(report))
