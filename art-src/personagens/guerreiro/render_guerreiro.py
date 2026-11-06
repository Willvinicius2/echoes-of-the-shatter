"""Guerreiro 3D por partes (v2) e render para pixel art.

Uso: python3 render_guerreiro.py <pasta_saida> [anim ...]
  Roda com o módulo `bpy` (pip install bpy). Sem janela, Cycles em CPU.
Saída: <pasta>/<anim>/<dir>_<quadro>.png, quadro de 3x o tamanho final (276 px), fundo transparente.
Direções: S, SE, E, NE, N (SW, W, NW são espelho no jogo).
O personagem olha para -Y; câmera ortográfica olhando de -Y, elevação 35 graus.
Quem pixela e monta as folhas: tools/sprites2d/montar_guerreiro_3d.py

v2 (revisão da Direção visual): cabeça menor, tronco alto, pernas grossas, mãos com luva, martelo de DUAS mãos
(IK analítico nos dois braços), escudo nas costas, aço escurecido com ocre fosco e crista vermelha escura curta,
materiais com desgaste nas quinas (pointiness) e mancha de ruído, paleta dessaturada como a do arqueiro.
"""
import bpy, math, sys, os
from mathutils import Vector, Quaternion

ESCALA_PX = 35.0
Q = 92
SS = 3
PIVO = (46, 76)
ELEV = 35.0
DIRS = {"south": 0, "south-east": 45, "east": 90, "north-east": 135, "north": 180, "north-west": 225, "west": 270, "south-west": 315}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


MATS = {}


def mat(nome, base, luz, rough=0.6, metal=0.0, ruido=0.25):
    """Material pintado: base com mancha de ruído e quinas (pointiness) clareadas para a cor `luz`."""
    if nome in MATS:
        return MATS[nome]
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.5
    ramp.color_ramp.elements[1].position = 0.62
    nt.links.new(geo.outputs["Pointiness"], ramp.inputs["Fac"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 6.0
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    mix1 = nt.nodes.new("ShaderNodeMix")
    mix1.data_type = "RGBA"
    mix1.inputs["A"].default_value = (*lin(rgb(base)), 1)
    dk = tuple(c * (1 - ruido) for c in lin(rgb(base)))
    mix1.inputs["B"].default_value = (*dk, 1)
    nt.links.new(noise.outputs["Fac"], mix1.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix")
    mix2.data_type = "RGBA"
    nt.links.new(ramp.outputs["Color"], mix2.inputs["Factor"])
    nt.links.new(mix1.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (*lin(rgb(luz)), 1)
    nt.links.new(mix2.outputs["Result"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    MATS[nome] = m
    return m


ACO = lambda: mat("aco", "#454d58", "#8b97a3", 0.5, 0.35)
ACO_ESC = lambda: mat("aco_esc", "#2c323c", "#5b6572", 0.55, 0.3)
OCRE = lambda: mat("ocre", "#8d7440", "#cdb06a", 0.55, 0.4)
VERM = lambda: mat("verm", "#6d2a2e", "#9a4545", 0.9, 0.0, 0.3)
VERM_ESC = lambda: mat("verm_esc", "#45191f", "#6d2a2e", 0.9, 0.0, 0.3)
COURO = lambda: mat("couro", "#3a2a26", "#6a5044", 0.9, 0.0, 0.3)
PRETO = lambda: mat("preto", "#0f0d13", "#1a1720", 1.0, 0.0, 0.0)
PEDRA = lambda: mat("pedra", "#5e636d", "#a1a7b0", 0.8, 0.1, 0.35)


def pivo(nome, pai=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(nome, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = pai
    o.location = loc
    return o


def malha(pai, tipo, loc, esc, m, rot=(0, 0, 0), bevel=0.0, seg=16, nome="p", bseg=3):
    if tipo == "cubo":
        bpy.ops.mesh.primitive_cube_add(size=1)
    elif tipo == "esfera":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(8, seg // 2), radius=0.5)
    elif tipo == "cilindro":
        bpy.ops.mesh.primitive_cylinder_add(vertices=seg, radius=0.5, depth=1)
    elif tipo == "cone":
        bpy.ops.mesh.primitive_cone_add(vertices=seg, radius1=0.5, radius2=0.0, depth=1)
    elif tipo == "toro":
        bpy.ops.mesh.primitive_torus_add(major_radius=0.5, minor_radius=0.07, major_segments=24, minor_segments=8)
    o = bpy.context.active_object
    o.name = nome
    o.parent = pai
    o.location = loc
    o.rotation_euler = tuple(math.radians(r) for r in rot)
    o.scale = esc
    if tipo != "cubo":
        bpy.ops.object.shade_smooth()
    if tipo == "cubo" or bevel:
        bpy.context.view_layer.objects.active = o
        b = o.modifiers.new("bv", "BEVEL")
        b.width = bevel or 0.06
        b.segments = bseg
        b.limit_method = "ANGLE"
    if tipo in ("cubo", "cilindro"):
        # subdivisão leve para a pointiness ter vértices
        s = o.modifiers.new("sub", "SUBSURF")
        s.levels = 1
        s.render_levels = 1
    o.data.materials.append(m)
    return o


HIP = 0.74
L_COXA, L_CANELA = 0.34, 0.36
L_BRACO, L_ANTEBRACO = 0.27, 0.27


def construir():
    P = {}
    P["raiz"] = pivo("raiz")
    P["quad"] = pivo("quad", P["raiz"], (0, 0, HIP))
    for lado, x in (("L", 0.15), ("R", -0.15)):
        q = pivo("coxa" + lado, P["quad"], (x, 0, -0.02))
        malha(q, "cilindro", (0, 0, -L_COXA / 2), (0.23, 0.23, L_COXA), ACO_ESC(), nome="coxa")
        malha(q, "cubo", (0, -0.1, -0.12), (0.2, 0.08, 0.2), ACO(), bevel=0.04, nome="coxote")
        j = pivo("joelho" + lado, q, (0, 0, -L_COXA))
        malha(j, "esfera", (0, -0.07, 0.02), (0.22, 0.2, 0.2), OCRE(), nome="joelheira")
        malha(j, "cilindro", (0, 0, -L_CANELA / 2), (0.21, 0.21, L_CANELA), ACO(), nome="canela")
        malha(j, "cubo", (0, -0.06, -L_CANELA / 2), (0.2, 0.08, 0.28), ACO_ESC(), bevel=0.03, nome="grevas")
        malha(j, "cubo", (0, -0.04, -L_CANELA - 0.02), (0.27, 0.4, 0.16), COURO(), bevel=0.05, nome="bota")
        malha(j, "cubo", (0, -0.2, -L_CANELA - 0.0), (0.24, 0.12, 0.13), ACO_ESC(), bevel=0.04, nome="biqueira")
        P["coxa" + lado], P["joelho" + lado] = q, j
    malha(P["quad"], "cubo", (0, 0, 0.02), (0.5, 0.3, 0.2), COURO(), bevel=0.05, nome="pelve")
    P["saia"] = pivo("saia", P["quad"], (0, -0.17, 0.0))
    malha(P["saia"], "cubo", (0, 0, -0.13), (0.26, 0.04, 0.34), VERM(), bevel=0.02, nome="saia")
    malha(P["saia"], "cubo", (0.2, 0.0, -0.1), (0.14, 0.05, 0.22), ACO(), bevel=0.03, nome="escarcela_a")
    malha(P["saia"], "cubo", (-0.2, 0.0, -0.1), (0.14, 0.05, 0.22), ACO(), bevel=0.03, nome="escarcela_b")
    # tronco alto
    P["tronco"] = pivo("tronco", P["quad"], (0, 0, 0.1))
    t = P["tronco"]
    malha(t, "cubo", (0, 0, 0.26), (0.54, 0.38, 0.54), ACO(), bevel=0.1, nome="peito")
    malha(t, "cubo", (0, -0.18, 0.18), (0.4, 0.06, 0.3), ACO_ESC(), bevel=0.04, nome="abdomen")
    malha(t, "cubo", (0, -0.21, 0.26), (0.26, 0.04, 0.46), VERM(), bevel=0.02, nome="tabardo")
    malha(t, "esfera", (0, -0.235, 0.34), (0.1, 0.05, 0.1), OCRE(), nome="emblema")
    malha(t, "cubo", (0, 0, 0.02), (0.54, 0.4, 0.08), OCRE(), bevel=0.03, nome="cinto")
    malha(t, "cubo", (0, 0.18, 0.28), (0.4, 0.06, 0.5), VERM_ESC(), bevel=0.02, nome="manto_costas")
    # cabeça menor
    P["cabeca"] = pivo("cabeca", t, (0, 0, 0.6))
    h = P["cabeca"]
    malha(h, "cilindro", (0, 0, 0.0), (0.22, 0.22, 0.1), ACO_ESC(), nome="gorjal")
    malha(h, "esfera", (0, 0, 0.17), (0.4, 0.38, 0.4), ACO(), nome="elmo")
    malha(h, "cubo", (0, -0.13, 0.13), (0.3, 0.14, 0.24), ACO(), bevel=0.05, nome="face")
    malha(h, "cubo", (0, -0.205, 0.17), (0.24, 0.02, 0.05), PRETO(), nome="viseira")
    malha(h, "cubo", (0, -0.205, 0.09), (0.04, 0.02, 0.12), PRETO(), nome="viseira_v")
    malha(h, "cubo", (0, -0.02, 0.36), (0.07, 0.34, 0.07), OCRE(), bevel=0.02, nome="crista_base")
    P["pluma"] = pivo("pluma", h, (0, 0.0, 0.37))
    for i in range(4):
        malha(P["pluma"], "esfera", (0, 0.03 + 0.07 * i, 0.02 - 0.012 * i * i * 0.5),
              (0.09 - 0.008 * i, 0.15, 0.09 - 0.008 * i), VERM() if i % 2 == 0 else VERM_ESC(), nome="pluma%d" % i)
    # ombreiras e braços
    for lado, x in (("L", 0.33), ("R", -0.33)):
        o = pivo("ombro" + lado, t, (x, 0, 0.46))
        sg = 1 if lado == "L" else -1
        malha(o, "esfera", (0.05 * sg, 0, 0.02), (0.3, 0.3, 0.26), ACO(), nome="ombreira")
        malha(o, "toro", (0.05 * sg, 0, -0.02), (0.31, 0.31, 0.31), OCRE(), rot=(90, 0, 0), nome="aro_ombreira")
        malha(o, "cilindro", (0, 0, -L_BRACO / 2), (0.15, 0.15, L_BRACO), ACO_ESC(), nome="braco")
        c = pivo("cotovelo" + lado, o, (0, 0, -L_BRACO))
        malha(c, "esfera", (0, 0, 0), (0.17, 0.17, 0.17), OCRE(), nome="cotoveleira")
        malha(c, "cilindro", (0, 0, -L_ANTEBRACO / 2), (0.16, 0.16, L_ANTEBRACO), ACO(), nome="antebraco")
        malha(c, "cilindro", (0, 0, -L_ANTEBRACO + 0.05), (0.19, 0.19, 0.07), OCRE(), nome="braceleira")
        if lado == "L":
            P["escudo"] = pivo("escudo", c, (0.04, -0.1, -0.12))
            es = P["escudo"]
            es.scale = (0.75, 0.75, 0.75)
            malha(es, "cilindro", (0, 0, 0), (0.62, 0.62, 0.09), PEDRA(), rot=(90, 0, 0), nome="escudo", seg=28)
            malha(es, "toro", (0, -0.03, 0), (0.64, 0.64, 0.64), OCRE(), rot=(90, 0, 0), nome="escudo_aro")
            malha(es, "cilindro", (0, -0.07, 0), (0.46, 0.46, 0.05), ACO_ESC(), rot=(90, 0, 0), nome="escudo_disco", seg=28)
            malha(es, "esfera", (0, -0.1, 0), (0.18, 0.1, 0.18), OCRE(), nome="escudo_boss")
        mao = pivo("mao" + lado, c, (0, 0, -L_ANTEBRACO))
        malha(mao, "cubo", (0, 0, -0.03), (0.16, 0.16, 0.14), COURO(), bevel=0.04, nome="luva")
        malha(mao, "cubo", (0, -0.07, -0.02), (0.14, 0.05, 0.1), ACO_ESC(), bevel=0.02, nome="dedos")
        P["ombro" + lado], P["cotovelo" + lado], P["mao" + lado] = o, c, mao
    # martelo de duas mãos, preso ao tronco (os braços seguem por IK)
    P["martelo"] = pivo("martelo", t, (-0.3, -0.3, 0.1))
    mt = P["martelo"]
    mt.scale = (0.78, 0.78, 0.78)
    malha(mt, "cilindro", (0, 0, 0.25), (0.075, 0.075, 1.05), COURO(), nome="cabo")
    for z in (0.02, 0.1, 0.38, 0.46):
        malha(mt, "cilindro", (0, 0, z), (0.095, 0.095, 0.05), COURO(), nome="pegada")
    malha(mt, "cubo", (0, 0, 0.82), (0.44, 0.3, 0.3), PEDRA(), bevel=0.07, nome="cabeca_martelo", bseg=4)
    malha(mt, "cubo", (0.235, 0, 0.82), (0.05, 0.32, 0.32), OCRE(), bevel=0.02, nome="faixa_a")
    malha(mt, "cubo", (-0.235, 0, 0.82), (0.05, 0.32, 0.32), OCRE(), bevel=0.02, nome="faixa_b")
    malha(mt, "cone", (0, 0.2, 0.82), (0.16, 0.16, 0.16), ACO_ESC(), rot=(-90, 0, 0), nome="espigao")
    malha(mt, "esfera", (0, 0, -0.29), (0.13, 0.13, 0.13), OCRE(), nome="pomo")
    return P


def deg(*a):
    return tuple(math.radians(x) for x in a)


def pose_base():
    return {
        "quad_z": 0.0, "raiz_z": 0.0, "raiz_rx": 0.0, "quad_rx": 0.0,
        "tronco": (0, 0, 0), "cabeca": (0, 0, 0), "pluma": (0, 0, 0),
        "coxaL": (0, 0, 0), "joelhoL": (0, 0, 0), "coxaR": (0, 0, 0), "joelhoR": (0, 0, 0),
        # martelo: posição no espaço do tronco (x, y, z) da mão de baixo e ângulo absoluto (0 = cabeça para cima, + = frente)
        "mt_pos": (-0.3, -0.12, 0.1), "mt_ang": -20.0, "mt_roll": 0.0,
    }


def lerp(a, b, t):
    return a + (b - a) * t


def pose_anim(anim, i, n):
    p = pose_base()
    ph = i / n
    s = math.sin(2 * math.pi * ph)
    c = math.cos(2 * math.pi * ph)
    if anim == "idle":
        p["quad_z"] = -0.01 + 0.02 * s
        p["tronco"] = (-2 + 1.5 * s, 0, 0)
        p["cabeca"] = (2 - 1.5 * s, 0, 0)
        p["coxaL"] = (-4, 0, 0)
        p["coxaR"] = (4, 0, 0)
        p["mt_pos"] = (0.0, -0.2, -0.02 + 0.015 * s)
        p["mt_ang"] = -32
        p["pluma"] = (5 * s, 0, 0)
    elif anim == "run":
        a = 46
        p["quad_z"] = 0.05 * abs(s) - 0.02
        p["tronco"] = (-12, 7 * s, 0)
        p["cabeca"] = (5, -5 * s, 0)
        p["coxaL"] = (-a * s, 0, 0)
        p["coxaR"] = (a * s, 0, 0)
        p["joelhoL"] = (max(0, 75 * c) + 8, 0, 0)
        p["joelhoR"] = (max(0, -75 * c) + 8, 0, 0)
        p["mt_pos"] = (0.04 * s, -0.32 + 0.04 * c, 0.16 + 0.05 * abs(s))
        p["mt_ang"] = -38 + 8 * s
        p["pluma"] = (-20 + 6 * s, 0, 0)
    elif anim == "dodge":
        # mergulho baixo para a frente: tronco bem inclinado, quadril baixo, martelo preso atrás
        t = i / (n - 1)
        e = math.sin(math.pi * t)
        p["raiz_rx"] = -lerp(0, 38, e)
        p["quad_z"] = -0.26 * e
        p["raiz_z"] = 0.0
        p["tronco"] = (-lerp(0, 20, e), 0, 0)
        p["cabeca"] = (12 * e, 0, 0)
        a = 70
        p["coxaL"] = (-a * e * 0.9, 0, 0)
        p["coxaR"] = (a * e * 0.5, 0, 0)
        p["joelhoL"] = (50 * e, 0, 0)
        p["joelhoR"] = (95 * e, 0, 0)
        p["mt_pos"] = (0.1, 0.05, 0.2 + 0.1 * e)
        p["mt_ang"] = -85 * e - 10
        p["pluma"] = (-40 * e, 0, 0)
    elif anim == "attack":
        F = [
            # (tronco rx, ry, rz), quad_z, mt_pos, mt_ang, coxaL, coxaR, joelhoL, joelhoR
            ((8, 0, -22), -0.04, (-0.2, 0.0, 0.52), -80, 8, -18, 14, 22),
            ((14, 0, -30), -0.07, (-0.2, 0.2, 0.62), -110, 12, -24, 20, 30),
            ((-6, 0, 8), -0.08, (-0.1, -0.2, 0.7), -10, -22, 20, 30, 10),
            ((-24, 0, 18), -0.16, (0.0, -0.58, 0.1), 125, -38, 28, 46, 16),
            ((-22, 0, 16), -0.16, (0.0, -0.6, 0.06), 135, -36, 26, 44, 16),
            ((-8, 0, 6), -0.07, (0.0, -0.4, 0.12), 80, -12, 8, 16, 8),
        ][i]
        p["tronco"] = F[0]
        p["quad_z"] = F[1]
        p["mt_pos"] = F[2]
        p["mt_ang"] = F[3]
        p["coxaL"], p["coxaR"], p["joelhoL"], p["joelhoR"] = ((F[4], 0, 0), (F[5], 0, 0), (F[6], 0, 0), (F[7], 0, 0))
        p["pluma"] = (-14, 0, 0)
    elif anim == "death":
        t = i / (n - 1)
        e = t * t * (3 - 2 * t)
        p["raiz_rx"] = lerp(0, 78, e)
        p["raiz_z"] = lerp(0, 0.12, e)
        p["quad_z"] = lerp(0, -0.1, e)
        p["tronco"] = (lerp(0, -16, e), 0, 0)
        p["cabeca"] = (lerp(0, -14, e), 0, 0)
        p["coxaL"] = (lerp(0, -22, e), 0, 0)
        p["coxaR"] = (lerp(0, 16, e), 0, 0)
        p["joelhoL"] = (lerp(0, 30, e), 0, 0)
        p["joelhoR"] = (lerp(0, 44, e), 0, 0)
        p["mt_pos"] = (lerp(0, 0.35, e), lerp(-0.3, -0.6, e), lerp(0.12, 0.0, e))
        p["mt_ang"] = lerp(-14, 80, e)
        p["mt_roll"] = lerp(0, 25, e)
        p["pluma"] = (lerp(0, 40, e), 0, 0)
    return p


def ik_braco(P, lado, alvo_w):
    """Dois ossos analíticos: ombro mira o alvo e o cotovelo dobra pela lei dos cossenos."""
    o, c = P["ombro" + lado], P["cotovelo" + lado]
    bpy.context.view_layer.update()
    sp = o.matrix_world.translation
    v = alvo_w - sp
    rot_t = P["tronco"].matrix_world.to_3x3().inverted()
    vl = rot_t @ v
    a, b = L_BRACO, L_ANTEBRACO
    d = min(vl.length, a + b - 1e-3)
    d = max(d, 0.06)
    cosg = (a * a + b * b - d * d) / (2 * a * b)
    gam = math.acos(max(-1, min(1, cosg)))
    cosa = (a * a + d * d - b * b) / (2 * a * d)
    alp = math.acos(max(-1, min(1, cosa)))
    q_aim = Vector((0, 0, -1)).rotation_difference(vl.normalized())
    melhor = None
    for sgn in (1, -1):
        q = q_aim @ Quaternion((1, 0, 0), sgn * alp)
        o.rotation_euler = q.to_euler("XYZ")
        c.rotation_euler = deg(0, 0, 0)
        c.rotation_euler = (-sgn * (math.pi - gam), 0, 0)
        bpy.context.view_layer.update()
        ez = c.matrix_world.translation.z
        if melhor is None or ez < melhor[0]:
            melhor = (ez, q, -sgn * (math.pi - gam))
    o.rotation_euler = melhor[1].to_euler("XYZ")
    c.rotation_euler = (melhor[2], 0, 0)


def aplicar(P, p, yaw):
    for nome in ("tronco", "cabeca", "pluma", "coxaL", "joelhoL", "coxaR", "joelhoR"):
        P[nome].rotation_euler = deg(*p[nome])
    P["quad"].location = (0, 0, HIP + p["quad_z"])
    P["raiz"].location = (0, 0, p["raiz_z"])
    P["raiz"].rotation_euler = deg(p["raiz_rx"], 0, yaw)
    # martelo no espaço do tronco; ângulo absoluto compensa o tronco e a inclinação da raiz
    mt = P["martelo"]
    mt.location = (p["mt_pos"][0] - 0.28, p["mt_pos"][1], p["mt_pos"][2])
    mt.rotation_euler = deg(p["mt_ang"] - p["tronco"][0] - p["raiz_rx"], 0, p["mt_roll"])
    bpy.context.view_layer.update()
    mw = mt.matrix_world
    ik_braco(P, "R", mw @ Vector((0, 0, 0.0)))
    # braço do escudo: ombro e cotovelo do pose (escudo voltado para a frente)
    P["ombroL"].rotation_euler = deg(*p.get("ombroL", (-38, 0, 18)))
    P["cotoveloL"].rotation_euler = deg(*p.get("cotoveloL", (-85, 0, 0)))
    P["escudo"].rotation_euler = deg(-(p.get("ombroL", (-38, 0, 18))[0] + p.get("cotoveloL", (-85, 0, 0))[0] + p["tronco"][0] + p["raiz_rx"]) * 0.9 + 6, 0, 0)


def cena():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.samples = 32
    s.cycles.device = "CPU"
    s.cycles.use_denoising = False
    s.render.film_transparent = True
    s.render.resolution_x = s.render.resolution_y = Q * SS
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    s.view_settings.view_transform = "Standard"
    s.render.filter_size = 0.8
    w = bpy.data.worlds.new("w")
    s.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.5, 0.55, 0.62, 1)
    bg.inputs["Strength"].default_value = 0.4
    l = bpy.data.lights.new("sol", "SUN")
    l.energy = 4.2
    l.angle = math.radians(20)
    lo = bpy.data.objects.new("sol", l)
    s.collection.objects.link(lo)
    lo.rotation_euler = deg(50, 0, -38)
    l2 = bpy.data.lights.new("rim", "SUN")
    l2.energy = 1.4
    l2.color = (0.55, 0.62, 0.9)
    l2o = bpy.data.objects.new("rim", l2)
    s.collection.objects.link(l2o)
    l2o.rotation_euler = deg(62, 0, 150)
    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    cam.ortho_scale = Q / ESCALA_PX
    co = bpy.data.objects.new("cam", cam)
    s.collection.objects.link(co)
    e = math.radians(ELEV)
    d = 20
    co.location = (0, -d * math.cos(e), d * math.sin(e))
    co.rotation_euler = (math.radians(90 - ELEV), 0, 0)
    cam.shift_x = (PIVO[0] - Q / 2) / Q * -1
    cam.shift_y = (PIVO[1] - Q / 2) / Q
    s.camera = co
    return s


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    saida = args[0]
    anims = args[1:] or ["idle", "run", "attack", "dodge", "death"]
    N = {"idle": 6, "run": 6, "attack": 6, "dodge": 6, "death": 6}
    s = cena()
    P = construir()
    for anim in anims:
        os.makedirs(os.path.join(saida, anim), exist_ok=True)
        for d, yaw in DIRS.items():
            for i in range(N[anim]):
                aplicar(P, pose_anim(anim, i, N[anim]), yaw)
                s.render.filepath = os.path.join(saida, anim, "%s_%d.png" % (d, i))
                bpy.ops.render.render(write_still=True)
        print("ok", anim, flush=True)


if __name__ == "__main__":
    main()
