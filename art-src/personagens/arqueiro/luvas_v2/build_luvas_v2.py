"""Reconstroi Arqueiro_Luvas.glb sobre o rig do GLB atual (FBX-fonte ausente). Rodar:
regenerar_rodada7.py
Usa luvas_geo.py (adaptado) e luvas_tex.py desta pasta."""
import os, sys, math
sys.dont_write_bytecode = True
import bpy
import os as _os
_AQUI = _os.path.dirname(_os.path.abspath(__file__))
_RAIZ = _os.path.abspath(_os.path.join(_AQUI, "..", "..", "..", ".."))
_GODOT = _os.path.join(_RAIZ, "godot", "art", "models", "personagens", "arqueiro")
FONTE = _os.environ.get("ARQ_RIG_DIR", _GODOT)   # GLB atual so fornece o rig
SAIDA = _os.environ.get("ARQ_SAIDA", _GODOT)
TRAB = _os.environ.get("ARQ_TRAB", _os.path.join(_AQUI, "_trabalho"))   # intermediarios (fora do git)
_os.makedirs(TRAB, exist_ok=True)
AQUI = _AQUI
REPO = os.path.join(FONTE, "Arqueiro_Luvas.glb")
sys.path.insert(0, os.path.join(_RAIZ, "art-src", "personagens", "arqueiro"))   # _comum.py, proporcao.py
sys.path.insert(0, AQUI)
import luvas_geo as G
import _comum as c
TEX = os.path.join(TRAB, "T_Arqueiro_Luvas_BC.png")

def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def pesos(ob, lado, W, ax, modo):
    nome = "Left" if lado > 0 else "Right"
    gl = ob.vertex_groups.new(name=nome + "LowerArm")
    gh = ob.vertex_groups.new(name=nome + "Hand")
    for v in ob.data.vertices:
        w = 0.0 if modo == "L" else 1.0 if modo == "H" else smoothstep(-0.025, 0.02, (v.co - W).dot(ax))
        if w < 1.0: gl.add([v.index], 1.0 - w, "REPLACE")
        if w > 0.0: gh.add([v.index], w, "REPLACE")

def arredondar(ob, k):
    """Anti-massinha: bevel nas pecas duras (osso, fivelas), subdivisao nas macias (dedos, couro)."""
    bpy.context.view_layer.objects.active = ob
    if k == "hard_H":
        return
    if k.startswith("hard"):
        m = ob.modifiers.new("bv", "BEVEL"); m.width = 0.0022; m.segments = 1; m.limit_method = "ANGLE"; m.angle_limit = math.radians(45)
        nome = "bv"
    else:
        m = ob.modifiers.new("ss", "SUBSURF"); m.levels = SUB; m.render_levels = SUB
        m.boundary_smooth = "PRESERVE_CORNERS"
        nome = "ss"
    bpy.ops.object.modifier_apply(modifier=nome)
    if k.startswith("hard"):
        d = ob.modifiers.new("pl", "DECIMATE"); d.decimate_type = "DISSOLVE"; d.angle_limit = math.radians(DIS)
        bpy.ops.object.modifier_apply(modifier="pl")
    if not k.startswith("hard") and DEC < 1.0:
        d = ob.modifiers.new("dc", "DECIMATE"); d.ratio = DEC; d.use_collapse_triangulate = False
        bpy.ops.object.modifier_apply(modifier="dc")


DIS = float(os.environ.get("ARQ_DIS", "10"))
DEC = float(os.environ.get("ARQ_DEC", "0.35"))
SUB = int(os.environ.get("ARQ_SUB", "1"))


def sombrear(ob, graus):
    for p in ob.data.polygons: p.use_smooth = True
    ob.data.set_sharp_from_angle(angle=math.radians(graus))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=REPO)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
tris0 = 0
for o in [o for o in bpy.data.objects if o.type == "MESH"]:
    tris0 += sum(len(p.vertices) - 2 for p in o.data.polygons)
    bpy.data.objects.remove(o)
print("TRIS_ANTES", tris0)
H = lambda n: arm.matrix_world @ arm.data.bones[n].head_local
objs = []
for lado, nome in ((1, "Left"), (-1, "Right")):
    W, E = H(nome + "Hand"), H(nome + "LowerArm")
    S, ax, out, side, L = G.construir(W, E, lado)
    (G.mao_esquerda if lado > 0 else G.mao_direita)(S, W, ax)
    modos = {"soft_L": "L", "soft_C": "C", "soft_H": "H", "hard_L": "L", "hard_H": "H"}
    for k, parte in S.items():
        if not parte.v: continue
        ob = parte.objeto(); ob.name = f"{k}_{nome}"
        pesos(ob, lado, W, ax, modos[k])
        t0 = sum(len(p.vertices) - 2 for p in ob.data.polygons); arredondar(ob, k); print("PARTE", ob.name, t0, "->", sum(len(p.vertices) - 2 for p in ob.data.polygons))
        sombrear(ob, 50 if k.startswith("hard") else 75)
        objs.append(ob)
bpy.ops.object.select_all(action="DESELECT")
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.join()
m = bpy.context.view_layer.objects.active
m.name = "SK_Archer_Luvas"
m.parent = arm
md = m.modifiers.new("Armature", "ARMATURE"); md.object = arm
c.material_simples(m, "M_Arqueiro_Luvas", TEX)
print("TRIS", sum(len(p.vertices) - 2 for p in m.data.polygons))
c.SAIDA = SAIDA
SAIDA_NOME = os.environ.get("ARQ_NOME", "Arqueiro_Luvas.glb")
c.exportar(SAIDA_NOME, [arm, m])
c.externalizar_textura(os.path.join(SAIDA, SAIDA_NOME), "T_Arqueiro_Luvas_BC.png")
import shutil
if os.path.abspath(TEX) != os.path.abspath(os.path.join(SAIDA, "T_Arqueiro_Luvas_BC.png")): shutil.copyfile(TEX, os.path.join(SAIDA, "T_Arqueiro_Luvas_BC.png"))
