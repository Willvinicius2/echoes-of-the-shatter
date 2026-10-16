"""Kit modular da Cripta Partida (graybox): grade de 1 m, modulo de 2 m, paredes de 3 m (docs/03 secao 3.7).

Blocos de pedra com chanfro de 3 cm, cores planas com saturacao baixa no cenario e listras de ouro de "Marco"
(folha 07). Pecas simetricas nas duas faces sempre que possivel, para que a rotacao de encaixe nao importe.
Pivos (docs/04 secao 17.1, "canto/centro de base da grade"):
- Piso: centro do ladrilho, face de cima em z = 0 (o chao jogavel fica em y = 0 no Unity).
- Parede e arco: centro da base, sobre a linha da grade; comprimento em X, espessura centrada na linha.
- Canto: torre na intersecao das linhas da grade; as paredes de 2 m terminam dentro dela.
- Pilar, escada, sarcofago, braseiro, ossos: centro da base, no chao (z = 0).
"""
import bpy, sys, os, json, math
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gb_lib import *

GOLD = '#D9A441'
GROUT, TILE_A, TILE_B = '#3A3342', '#6A6474', '#5E5868'
WALL, WALL_D, WALL_L, STONE_L = '#4E4858', '#3A3342', '#5E5868', '#6A6474'
BONE, BONE_D = '#D8CCB0', '#B8AC90'
WALL_H = 3.0


def floor_a(b=None, name="SM_Cripta_Floor_2x2_A"):
    b = b or Builder(name)
    b.add('bbox', (2.0, 2.0, 0.16), (0, 0, -0.10), GROUT, bev=0.02)
    for ix, x in enumerate((-0.5, 0.5)):
        for iy, y in enumerate((-0.5, 0.5)):
            b.add('bbox', (0.94, 0.94, 0.10), (x, y, -0.05), TILE_A if (ix + iy) % 2 == 0 else TILE_B, bev=0.03)
    return b


def floor_b():
    """Variante de "Marco": quarto de anel dourado centrado no canto (-1, -1). Quatro pecas giradas formam o circulo."""
    b = floor_a(Builder("SM_Cripta_Floor_2x2_B"))
    b.arc((-1, -1, 0.0), 1.35, 2, 88, 5, 0.16, 0.02, GOLD, plane='XY', bev=0.006)
    b.arc((-1, -1, 0.0), 0.65, 4, 86, 3, 0.12, 0.02, GOLD, plane='XY', bev=0.006)
    return b


def wall_body(b, length, cx=0.0, axis='X'):
    """Parede reta simetrica: rodape, corpo com blocos salientes nas duas faces, cornija e friso de ouro."""
    def put(dim, loc, color, shape='bbox', bev=0.03):
        if axis == 'X':
            b.add(shape, dim, (cx + loc[0], loc[1], loc[2]), color, bev=bev)
        else:
            b.add(shape, (dim[1], dim[0], dim[2]), (loc[1], cx + loc[0], loc[2]), color, bev=bev)
    put((length, 0.60, 0.30), (0, 0, 0.15), WALL_D)
    put((length, 0.50, 2.40), (0, 0, 1.50), WALL)
    put((length, 0.62, 0.30), (0, 0, 2.85), WALL_L)
    for side in (-1, 1):
        put((length, 0.02, 0.06), (0, side * 0.315, 2.66), GOLD, shape='box')
        n = max(1, int(round(length / 2.0)))
        for k in range(n):
            x0 = -length / 2 + (k + 0.5) * length / n
            put((0.80, 0.06, 0.46), (x0 - 0.35 * side, side * 0.26, 0.75), WALL_L)
            put((0.70, 0.06, 0.40), (x0 + 0.40 * side, side * 0.26, 1.62), WALL_L)


def wall():
    b = Builder("SM_Cripta_Wall_2m_A")
    wall_body(b, 2.0)
    return b


def corner():
    b = Builder("SM_Cripta_WallCorner_A")
    b.add('bbox', (1.00, 1.00, 0.36), (0, 0, 0.18), WALL_D)
    b.add('bbox', (0.86, 0.86, 3.00), (0, 0, 1.68), WALL)
    b.add('box', (0.88, 0.88, 0.06), (0, 0, 2.66), GOLD)
    b.add('bbox', (1.00, 1.00, 0.28), (0, 0, 3.22), WALL_L)
    b.add('bbox', (0.70, 0.70, 0.22), (0, 0, 3.47), STONE_L)
    return b


def pillar():
    b = Builder("SM_Cripta_Pillar_A")
    b.add('bbox', (0.80, 0.80, 0.35), (0, 0, 0.175), WALL_D)
    b.add('bbox', (0.66, 0.66, 0.15), (0, 0, 0.42), WALL)
    b.add('bbox', (0.54, 0.54, 2.30), (0, 0, 1.60), WALL_L)
    for z in (1.10, 2.30):
        b.add('box', (0.57, 0.57, 0.07), (0, 0, z), GOLD)
    b.add('bbox', (0.80, 0.80, 0.30), (0, 0, 2.90), WALL)
    b.add('bbox', (0.66, 0.66, 0.18), (0, 0, 3.14), STONE_L)
    return b


def arch():
    """Arco/porta de 4 m (dois modulos): vao de 2 m x 2,8 m, aduelas salientes, fecho dourado e estandartes."""
    b = Builder("SM_Cripta_Arch_A")
    n, R, spring = 8, 1.0, 1.8
    top = 3.1
    arc_pts = [(R * math.cos(math.radians(180 - k * 90 / n)), spring + R * math.sin(math.radians(180 - k * 90 / n)))
               for k in range(n + 1)]
    for sx in (-1, 1):
        # parede em pecas convexas: ombreira + uma faixa vertical por segmento do arco (ate o topo)
        jamb = [(-2.0, 0.0), (-1.0, 0.0), (-1.0, top), (-2.0, top)]
        strips = [[p0, p1, (p1[0], top), (p0[0], top)] for p0, p1 in zip(arc_pts[:-1], arc_pts[1:])]
        for poly in [jamb] + strips:
            pts = [(sx * -x, z) for x, z in poly] if sx > 0 else poly
            b.prism(pts if sx < 0 else list(reversed(pts)), -0.30, 0.30, WALL)
    b.arc((0, 0, spring), 1.15, 0, 180, 7, 0.30, 0.70, STONE_L, plane='XZ', bev=0.03, overlap=0.97)
    b.add('bbox', (0.30, 0.74, 0.38), (0, 0, spring + 1.16), GOLD, bev=0.03)             # fecho do arco
    for sx in (-1, 1):
        b.add('bbox', (0.30, 0.70, 1.80), (sx * 1.15, 0, 0.90), STONE_L)                 # ombreiras
        b.add('bbox', (1.00, 0.70, 0.30), (sx * 1.50, 0, 0.15), WALL_D)                  # rodape
        for sy in (-1, 1):
            b.add('box', (0.50, 0.03, 1.10), (sx * 1.58, sy * 0.33, 2.05), '#8A2A2A')     # estandarte
            b.add('box', (0.16, 0.035, 0.16), (sx * 1.58, sy * 0.335, 2.15), GOLD, rot=(0, 45, 0))
    b.add('bbox', (4.00, 0.72, 0.30), (0, 0, 3.25), WALL_L)                              # cornija (topo 3,40)
    for sy in (-1, 1):
        b.add('box', (4.00, 0.02, 0.06), (0, sy * 0.355, 3.02), GOLD)
    return b


def stairs():
    """Escada de 2 x 2 m: 5 degraus de 0,20 x 0,40 m, sobe 1 m para +Y (o pe da escada fica em -Y)."""
    b = Builder("SM_Cripta_Stairs_A")
    for i in range(5):
        h = 0.2 * (i + 1)
        b.add('bbox', (1.60, 0.40, h), (0, -0.8 + 0.4 * i, h / 2), TILE_A if i % 2 == 0 else TILE_B, bev=0.03)
        b.add('box', (1.60, 0.03, 0.025), (0, -1.0 + 0.4 * i + 0.015, h + 0.0125), GOLD)     # quina de ouro
    prof = [(-1.0, 0.0), (1.0, 0.0), (1.0, 1.25), (0.6, 1.25), (-1.0, 0.25)]           # (y, z) da mureta
    for sx in (-1, 1):
        b.xf = Matrix.Translation((sx * 0.9, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, 'Z')
        b.prism(prof, -0.10, 0.10, WALL)
        b.xf = None
    return b


def sarcophagus():
    b = Builder("SM_Cripta_Sarcophagus_A")
    b.add('bbox', (1.00, 2.00, 0.15), (0, 0, 0.075), WALL_D, bev=0.03)
    b.add('bbox', (0.86, 1.86, 0.55), (0, 0, 0.425), WALL_L, bev=0.03)
    b.add('bbox', (0.98, 1.98, 0.16), (0, 0, 0.78), STONE_L, bev=0.03)
    b.add('bbox', (0.60, 1.70, 0.08), (0, 0, 0.90), '#7C7684', bev=0.03)
    b.add('box', (0.08, 1.10, 0.03), (0, -0.05, 0.955), GOLD)
    b.add('box', (0.50, 0.08, 0.03), (0, 0.28, 0.955), GOLD)
    for sy in (-1, 1):
        b.add('box', (0.22, 0.03, 0.22), (0, sy * 0.94, 0.45), GOLD, rot=(0, 45, 0))
    return b


def brazier():
    b = Builder("SM_Cripta_Brazier_A")
    b.add('bbox', (0.70, 0.70, 0.20), (0, 0, 0.10), WALL_D)
    b.add('bbox', (0.44, 0.44, 0.60), (0, 0, 0.50), WALL_L)
    b.add('bbox', (0.60, 0.60, 0.10), (0, 0, 0.85), WALL, bev=0.02)
    b.add('cyl', (0.50, 0.50, 0.22), (0, 0, 1.01), '#A87A2E', taper=1.5, seg=10)          # bacia de bronze
    b.add('ring', (0.80, 0.80, 0.08), (0, 0, 1.12), '#7A5A2A', seg=12, tube=0.09)
    b.add('cyl', (0.42, 0.42, 0.44), (0, 0, 1.32), '#FF7A1E', taper=0.05, seg=6, emit=True)   # chama
    b.add('cyl', (0.24, 0.24, 0.34), (0.03, 0.02, 1.29), '#FFD27A', taper=0.05, seg=5, emit=True)
    for a in (40, 200):
        u = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        b.add('cyl', (0.16, 0.16, 0.22), u * 0.15 + Vector((0, 0, 1.22)), '#FF7A1E', taper=0.05, seg=5, emit=True)
    return b


def bone_piece(b, a, c, r, color):
    a, c = Vector(a), Vector(c)
    b.limb(a, c, r, color, seg=6)
    for p in (a, c):
        b.add('sph', (r * 3.0, r * 3.0, r * 2.6), p, color, seg=4)


def bone_pile():
    b = Builder("SM_Cripta_BonePile_A")
    b.add('sph', (0.20, 0.23, 0.18), (0.05, -0.06, 0.10), BONE, seg=8)                     # cranio
    b.add('box', (0.13, 0.08, 0.05), (0.05, -0.15, 0.03), BONE_D)                          # mandibula
    for sx in (-1, 1):
        b.add('box', (0.045, 0.02, 0.045), (0.05 + sx * 0.045, -0.172, 0.11), '#2A222F')   # orbitas
    bone_piece(b, (-0.30, -0.10, 0.035), (0.08, 0.22, 0.035), 0.026, BONE)       # pontas encostam em z = 0
    bone_piece(b, (-0.25, 0.25, 0.032), (0.20, 0.10, 0.032), 0.024, BONE_D)
    bone_piece(b, (0.18, -0.30, 0.03), (0.32, 0.12, 0.03), 0.022, BONE)
    bone_piece(b, (-0.12, -0.32, 0.08), (-0.05, 0.10, 0.08), 0.022, BONE_D)
    bone_piece(b, (-0.34, 0.02, 0.027), (-0.20, -0.30, 0.027), 0.02, BONE)
    for loc, s in (((0.30, 0.28, 0.05), 0.10), ((-0.32, 0.30, 0.04), 0.08), ((0.33, -0.12, 0.04), 0.08)):
        b.add('bbox', (s, s * 0.9, s), loc, WALL, rot=(0, 0, 25), bev=0.012)               # pedrinhas
    return b


PIECES = [
    # (funcao, categoria do orcamento 04/17.2, pivo, encaixe)
    (floor_a, "floor", "centro do ladrilho, topo em z=0", "centro em coordenadas impares (2x2 m)"),
    (floor_b, "floor", "centro do ladrilho, topo em z=0", "4 pecas giradas 0/90/180/270 em volta de um ponto par formam o anel"),
    (wall, "structure", "centro da base sobre a linha da grade", "linha da grade, centro em coordenada impar"),
    (corner, "structure", "intersecao das linhas da grade, base", "coordenadas pares"),
    (pillar, "structure", "centro da base", "grade de 1 m (cantos de ladrilho)"),
    (arch, "structure", "centro da base sobre a linha da grade", "linha da grade, centro em coordenada par (ocupa 2 modulos)"),
    (stairs, "structure", "centro da base 2x2 m; sobe para +Y no Blender (-Z no Unity)", "centro em coordenadas impares"),
    (sarcophagus, "prop", "centro da base", "1x2 m"),
    (brazier, "prop", "centro da base", "1x1 m"),
    (bone_pile, "prop", "centro da base", "livre (decorativo, sem colisor)"),
]
BUDGET = {"floor": (200, 600), "structure": (800, 2500), "prop": (100, 800)}   # docs/04 secao 17.2

if __name__ == "__main__":
    report = dict(version=version_info(), grid_m=1.0, module_m=2.0, wall_height_m=WALL_H, pieces={})
    reset()
    kit = new_coll("Kit_Cripta")
    objs = []
    for fn, cat, pivot, snap in PIECES:
        ob = fn().build(kit)
        mn, mx = bbox([ob])
        lo, hi = BUDGET[cat]
        report["pieces"][ob.name] = dict(
            file=f"fbx/{ob.name}.fbx", category=cat, pivot=pivot, snap=snap,
            blender_min=[round(c, 3) + 0.0 for c in mn], blender_max=[round(c, 3) + 0.0 for c in mx],
            unity=unity_bounds(mn, mx), tris=tris(ob), budget_tris=[lo, hi], pct_of_budget_max=round(100 * tris(ob) / hi, 1),
            materials=[m.name for m in ob.data.materials])
        export_fbx([ob], f"{FBX}/{ob.name}.fbx")
        objs.append(ob)

    # previa do kit: pecas em duas fileiras, com o Guerreiro de referencia e rotulos no chao
    right, down = Vector((-0.7071, 0.7071, 0)), Vector((0.7071, 0.7071, 0))
    rows = [["SM_Cripta_Wall_2m_A", "SM_Cripta_WallCorner_A", "SM_Cripta_Pillar_A", "SM_Cripta_Arch_A", "SM_Cripta_Stairs_A"],
            ["SM_Cripta_Floor_2x2_A", "SM_Cripta_Floor_2x2_B", "SM_Cripta_Sarcophagus_A", "SM_Cripta_Brazier_A",
             "SM_Cripta_BonePile_A", "REF"]]
    gaps = [[0, 2.9, 2.3, 3.8, 3.9], [0, 2.9, 2.6, 2.1, 1.7, 1.7]]
    prev = new_coll("Preview")
    label_mat = bpy.data.materials.new("Preview_Label")
    label_mat.diffuse_color = (0.85, 0.80, 0.70, 1.0)
    with bpy.data.libraries.load(f"{ROOT}/heroes_graybox.blend", link=False) as (src, dst):
        dst.collections = ["SK_Warrior"]
    wc = dst.collections[0]
    prev.children.link(wc)
    hero = [o for o in wc.objects if o.type == 'ARMATURE'][0]
    hero.rotation_euler = (0, 0, math.pi)
    for r, (names, gp) in enumerate(zip(rows, gaps)):
        x = -6.3
        for name, g in zip(names, gp):
            x += g
            o = hero if name == "REF" else bpy.data.objects[name]
            o.location = right * x + down * (r * 4.2 - 2.6)
            if name == "REF":
                continue
            cu = bpy.data.curves.new(name + "_label", 'FONT')
            cu.body = name.replace("SM_Cripta_", "")
            cu.size, cu.align_x = 0.30, 'CENTER'
            lo = bpy.data.objects.new(name + "_label", cu)
            lo.data.materials.append(label_mat)
            prev.objects.link(lo)
            lo.location = o.location + down * (1.55 if r == 0 else 1.45) + Vector((0, 0, 0.02))
            lo.rotation_euler = (0, 0, math.radians(135))
    fl = Builder("Preview_Floor")
    fl.add('box', (40, 40, 0.05), (0, 0, -0.205), '#2A222F')
    fo = fl.build(prev)
    setup_render(1600, 900)
    bpy.context.scene.display.shading.show_shadows = False     # os rotulos projetariam sombra no chao
    game_camera((0.0, 0.0, 0.6), 40, ortho_scale=17.5)
    render(f"{PREV}/crypt_kit.png")
    prev.hide_render = True
    bpy.context.view_layer.layer_collection.children["Preview"].hide_viewport = True
    for c in list(prev.children):
        prev.children.unlink(c)
    save_blend(f"{ROOT}/crypt_kit_graybox.blend")
    json.dump(report, open(f"{PREV}/_crypt_kit_report.json", "w"), indent=1)
    print("REPORT", json.dumps({k: (v["unity"]["size"], v["tris"]) for k, v in report["pieces"].items()}))
