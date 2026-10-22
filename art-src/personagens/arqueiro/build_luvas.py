"""Exporta Arqueiro_Luvas.glb: luvas modeladas do zero (couro, braçadeiras de osso, dedos, garras), skinadas ao rig.
Rodar: blender -b -P build_luvas.py   (TEMP/TMP no disco D). Textura propria: python luvas_tex.py -> T_Arqueiro_Luvas_BC.png
Geometria em luvas_geo.py. O FBX da mao so fornece o Rig_Humanoid_Chibi (27 ossos) e o repouso chibi (proporcao.aplicar).
"""
import os, sys, math
import bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _comum as c
import luvas_geo as G

TEX = c.SAIDA + "/T_Arqueiro_Luvas_BC.png"


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def pesos(ob, lado, W, ax, modo):
    nome = "Left" if lado > 0 else "Right"
    gl = ob.vertex_groups.new(name=nome + "LowerArm")
    gh = ob.vertex_groups.new(name=nome + "Hand")
    for v in ob.data.vertices:
        if modo == "L":
            w = 0.0
        elif modo == "H":
            w = 1.0
        else:  # mistura pelo eixo do antebraco: s<-0,02 LowerArm, s>+0,02 Hand
            w = smoothstep(-0.025, 0.02, (v.co - W).dot(ax))
        if w < 1.0:
            gl.add([v.index], 1.0 - w, "REPLACE")
        if w > 0.0:
            gh.add([v.index], w, "REPLACE")


def sombrear(ob, graus):
    """Suave ate 'graus' entre faces vizinhas (couro 76: dedos redondos; osso 40: planos chanfrados nitidos)."""
    for p in ob.data.polygons:
        p.use_smooth = True
    try:
        ob.data.set_sharp_from_angle(angle=math.radians(graus))
    except Exception as e:
        print("AVISO set_sharp_from_angle", e)


def bevel(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    md = ob.modifiers.new("bev", "BEVEL")
    md.width = 0.0022
    md.segments = 1
    md.limit_method = "ANGLE"
    md.angle_limit = math.radians(40)
    bpy.ops.object.modifier_apply(modifier="bev")


def main():
    c.limpar()
    c.importar(f"{c.FINAL}/SK_Archer_Hands_Starter.fbx")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    velha = [o for o in bpy.data.objects if o.type == "MESH"]
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    arm.animation_data_clear()
    c.aplicar_rotacao([arm] + velha)
    c.proporcao.aplicar(arm, velha)          # repouso chibi identico em todos os modulos
    for o in velha:
        bpy.data.objects.remove(o)
    H = lambda n: arm.matrix_world @ arm.data.bones[n].head_local
    objs = []
    for lado, nome in ((1, "Left"), (-1, "Right")):
        W, E = H(nome + "Hand"), H(nome + "LowerArm")
        S, ax, out, side, L = G.construir(W, E, lado)
        if lado > 0:
            G.mao_esquerda(S, W, ax)
        else:
            G.mao_direita(S, W, ax)
        modos = {"soft_L": "L", "soft_C": "C", "soft_H": "H", "hard_L": "L", "hard_H": "H"}
        for k, parte in S.items():
            if not parte.v:
                continue
            ob = parte.objeto()
            ob.name = f"{k}_{nome}"
            if False and parte.bevel:
                bevel(ob)
            pesos(ob, lado, W, ax, modos[k])
            sombrear(ob, 40 if k.startswith("hard") or k == "soft_L" else 76)
            print("TRIS_PARTE", ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons))
            objs.append(ob)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    m = bpy.context.view_layer.objects.active
    m.name = "SK_Archer_Luvas"
    me = m.data
    m.parent = arm
    md = m.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    c.material_simples(m, "M_Arqueiro_Luvas", TEX)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print("TRIS", tris)
    c.exportar("Arqueiro_Luvas.glb", [arm, m])
    c.externalizar_textura(os.path.join(c.SAIDA, "Arqueiro_Luvas.glb"), os.path.basename(TEX))
    xs = [v.co.x for v in me.vertices]
    print("BBOX x", min(xs), max(xs))


main()
