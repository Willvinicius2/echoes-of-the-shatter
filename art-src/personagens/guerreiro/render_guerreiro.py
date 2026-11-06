"""Guerreiro 3D por partes (primitivas com bevel) e render para pixel art.

Uso: python3 render_guerreiro.py <pasta_saida> [anim ...] [--prev]
  Roda com o módulo `bpy` (pip install bpy). Sem janela, Cycles em CPU.
Saída: <pasta>/<anim>/<dir>_<quadro>.png, quadro de 3x o tamanho final (276 px), fundo transparente.
Direções renderizadas: S, SE, E, NE, N (SW, W, NW são espelho no jogo).
O personagem olha para -Y; a câmera olha de -Y para +Y, elevação 35 graus, ortográfica.
Quem pixela e monta as folhas: tools/sprites2d/montar_guerreiro_3d.py
Partes (cada uma um grupo de malhas num pivô): quadril, tronco+tabardo, elmo+pluma, ombreiras, braços, luvas,
pernas, botas, martelo e escudo. Cores: aço cinza-azulado, dourado, vermelho, couro escuro (folha oficial 02).
"""
import bpy, math, sys, os
from mathutils import Vector

ESCALA_PX = 39.0            # pixels finais por unidade de mundo
Q = 92                      # quadro final
SS = 3                      # supersample
PIVO = (46, 76)
ELEV = 35.0
DIRS = {"south": 0, "south-east": 45, "east": 90, "north-east": 135, "north": 180}
# guinada (graus) do personagem: 0 = olha para a câmera; positivo gira para a direita da tela (E)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lin(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


MATS = {}


def mat(nome, hexa, rough=0.7, metal=0.0, emis=None):
    if nome in MATS:
        return MATS[nome]
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(rgb(hexa)), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    MATS[nome] = m
    return m


ACO = lambda: mat("aco", "#5b6270", 0.65, 0.2)
ACO_ESC = lambda: mat("aco_esc", "#3b404d", 0.7, 0.2)
OURO = lambda: mat("ouro", "#e2a928", 0.45, 0.5)
VERM = lambda: mat("verm", "#b0262e", 0.9)
VERM_ESC = lambda: mat("verm_esc", "#6e161d", 0.9)
COURO = lambda: mat("couro", "#4a2c22", 0.9)
PRETO = lambda: mat("preto", "#17141c", 1.0)
PEDRA = lambda: mat("pedra", "#7c7f88", 0.9)
PELE = lambda: mat("pele", "#17141c", 1.0)


def pivo(nome, pai=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(nome, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = pai
    o.location = loc
    return o


def malha(pai, tipo, loc, esc, m, rot=(0, 0, 0), bevel=0.0, seg=16, nome="p"):
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
    bpy.ops.object.shade_smooth() if tipo not in ("cubo",) else None
    if tipo == "cubo" or bevel:
        bpy.context.view_layer.objects.active = o
        b = o.modifiers.new("bv", "BEVEL")
        b.width = bevel or 0.08
        b.segments = 3
        b.limit_method = "ANGLE"
    o.data.materials.append(m)
    return o


def construir():
    P = {}
    P["raiz"] = pivo("raiz")
    P["quad"] = pivo("quad", P["raiz"], (0, 0, 0.62))
    # pernas (quadril em z=0.62; coxa 0.28, canela 0.3)
    for lado, x in (("L", 0.14), ("R", -0.14)):
        q = pivo("coxa" + lado, P["quad"], (x, 0, -0.02))
        malha(q, "cilindro", (0, 0, -0.14), (0.2, 0.2, 0.30), ACO_ESC(), nome="coxa")
        j = pivo("joelho" + lado, q, (0, 0, -0.28))
        malha(j, "cilindro", (0, 0, -0.14), (0.18, 0.18, 0.26), ACO(), nome="canela")
        malha(j, "esfera", (0, -0.06, 0.0), (0.2, 0.2, 0.18), OURO(), nome="joelheira")
        malha(j, "cubo", (0, -0.03, -0.30), (0.24, 0.34, 0.16), COURO(), bevel=0.04, nome="bota")
        malha(j, "cubo", (0, -0.17, -0.31), (0.19, 0.1, 0.1), OURO(), bevel=0.03, nome="biqueira")
        P["coxa" + lado], P["joelho" + lado] = q, j
    malha(P["quad"], "cubo", (0, 0, 0.0), (0.46, 0.28, 0.16), COURO(), bevel=0.05, nome="pelve")
    # saiote vermelho
    P["saia"] = pivo("saia", P["quad"], (0, -0.14, -0.02))
    malha(P["saia"], "cubo", (0, 0, -0.1), (0.2, 0.04, 0.26), VERM(), bevel=0.02, nome="saia")
    malha(P["saia"], "cubo", (0, -0.02, -0.25), (0.12, 0.04, 0.06), VERM_ESC(), bevel=0.02, nome="saia_ponta")
    # tronco
    P["tronco"] = pivo("tronco", P["quad"], (0, 0, 0.08))
    t = P["tronco"]
    malha(t, "cubo", (0, 0, 0.22), (0.62, 0.4, 0.44), ACO(), bevel=0.1, nome="peito")
    malha(t, "cubo", (0, -0.2, 0.2), (0.28, 0.05, 0.36), VERM(), bevel=0.02, nome="tabardo")
    malha(t, "esfera", (0, -0.235, 0.24), (0.1, 0.05, 0.1), OURO(), nome="emblema")
    malha(t, "cubo", (0, 0, 0.02), (0.54, 0.4, 0.07), OURO(), bevel=0.025, nome="cinto")
    malha(t, "cubo", (0, 0.2, 0.2), (0.3, 0.05, 0.36), VERM_ESC(), bevel=0.02, nome="manto_costas")
    # cabeça e elmo
    P["cabeca"] = pivo("cabeca", t, (0, 0, 0.5))
    h = P["cabeca"]
    malha(h, "esfera", (0, 0, 0.26), (0.58, 0.54, 0.58), OURO(), nome="elmo")
    malha(h, "cubo", (0, -0.17, 0.2), (0.4, 0.2, 0.34), OURO(), bevel=0.07, nome="face_dourada")
    malha(h, "cubo", (0, -0.272, 0.24), (0.3, 0.02, 0.07), PRETO(), nome="viseira")
    malha(h, "cubo", (0, -0.272, 0.13), (0.06, 0.02, 0.16), PRETO(), nome="viseira_v")
    malha(h, "cubo", (0, -0.02, 0.58), (0.08, 0.44, 0.1), ACO_ESC(), bevel=0.03, nome="crista")
    malha(h, "cubo", (0.27, 0.0, 0.2), (0.06, 0.34, 0.3), ACO_ESC(), bevel=0.03, nome="proteção_a")
    malha(h, "cubo", (-0.27, 0.0, 0.2), (0.06, 0.34, 0.3), ACO_ESC(), bevel=0.03, nome="proteção_b")
    P["pluma"] = pivo("pluma", h, (0, 0.02, 0.58))
    for i in range(8):
        malha(P["pluma"], "esfera", (0, 0.04 + 0.085 * i, 0.07 - 0.012 * i * i * 0.5 + 0.02 * i if i < 3 else 0.07 - 0.03 * (i - 2) ** 1.4),
              (0.13 - 0.008 * i, 0.19, 0.12 - 0.008 * i), VERM() if i % 2 == 0 else VERM_ESC(), nome="pluma%d" % i)
    # ombreiras e braços
    for lado, x in (("L", 0.37), ("R", -0.37)):
        o = pivo("ombro" + lado, t, (x, 0, 0.4))
        malha(o, "esfera", (0.04 if lado == "L" else -0.04, 0, 0.02), (0.34, 0.34, 0.3), ACO(), nome="ombreira")
        malha(o, "toro", (0.04 if lado == "L" else -0.04, 0, -0.02), (0.34, 0.34, 0.34), OURO(), rot=(90, 0, 0), nome="aro_ombreira")
        malha(o, "cilindro", (0, 0, -0.14), (0.14, 0.14, 0.3), ACO_ESC(), nome="braco")
        c = pivo("cotovelo" + lado, o, (0, 0, -0.28))
        malha(c, "cilindro", (0, 0, -0.12), (0.13, 0.13, 0.25), ACO(), nome="antebraco")
        malha(c, "cilindro", (0, 0, -0.04), (0.17, 0.17, 0.05), OURO(), nome="braceleira")
        mao = pivo("mao" + lado, c, (0, 0, -0.27))
        malha(mao, "esfera", (0, 0, 0), (0.2, 0.2, 0.2), OURO(), nome="luva")
        P["ombro" + lado], P["cotovelo" + lado], P["mao" + lado] = o, c, mao
    # martelo (mão direita do personagem = x negativo)
    P["martelo"] = pivo("martelo", P["maoR"], (0, 0, 0))
    mt = P["martelo"]
    malha(mt, "cilindro", (0, 0, 0.2), (0.07, 0.07, 0.95), COURO(), nome="cabo")
    malha(mt, "cubo", (0, 0, 0.66), (0.5, 0.32, 0.32), PEDRA(), bevel=0.06, nome="cabeca_martelo")
    malha(mt, "cubo", (0.26, 0, 0.66), (0.05, 0.34, 0.34), OURO(), bevel=0.02, nome="faixa_a")
    malha(mt, "cubo", (-0.26, 0, 0.66), (0.05, 0.34, 0.34), OURO(), bevel=0.02, nome="faixa_b")
    malha(mt, "cubo", (0, 0, -0.27), (0.11, 0.11, 0.07), OURO(), bevel=0.02, nome="pomo")
    # escudo (mão esquerda = x positivo): placa larga voltada para a frente (-Y)
    P["escudo"] = pivo("escudo", P["maoL"], (0.02, -0.14, 0.12))
    s = P["escudo"]
    malha(s, "cubo", (0.0, 0.0, 0.0), (0.42, 0.09, 0.66), PEDRA(), bevel=0.05, nome="escudo")
    malha(s, "cubo", (0.0, -0.03, 0.0), (0.46, 0.06, 0.7), OURO(), bevel=0.02, nome="escudo_aro")
    malha(s, "cubo", (0.0, -0.05, 0.0), (0.34, 0.06, 0.58), PEDRA(), bevel=0.04, nome="escudo_face")
    malha(s, "esfera", (0.0, -0.1, 0.0), (0.16, 0.1, 0.16), OURO(), nome="escudo_boss")
    return P


# ------------------------------------------------------------------ poses
def deg(*a):
    return tuple(math.radians(x) for x in a)


def pose_base():
    # chaves: nome do pivô -> (rx, ry, rz) em graus; "quad_z" e "raiz_rz" extras
    return {
        "quad_z": 0.0, "quad_rx": 0, "quad_ry": 0, "quad_rz": 0,
        "tronco": (0, 0, 0), "cabeca": (0, 0, 0), "pluma": (0, 0, 0),
        "coxaL": (0, 0, 0), "joelhoL": (0, 0, 0), "coxaR": (0, 0, 0), "joelhoR": (0, 0, 0),
        "ombroL": (0, 0, 0), "cotoveloL": (0, 0, 0), "ombroR": (0, 0, 0), "cotoveloR": (0, 0, 0),
        "martelo": (0, 0, 0), "escudo": (0, 0, 0), "raiz_z": 0.0, "raiz_rx": 0,
    }


def lerp(a, b, t):
    return a + (b - a) * t


def pose_anim(anim, i, n):
    """Retorna a pose do quadro i de n. Ângulos: rx negativo = para a frente (-Y)."""
    p = pose_base()
    ph = i / n
    s = math.sin(2 * math.pi * ph)
    c = math.cos(2 * math.pi * ph)
    if anim == "idle":
        p["quad_z"] = -0.015 + 0.02 * s
        p["tronco"] = (-3 + 1.5 * s, 0, 0)
        p["cabeca"] = (2 - 1.5 * s, 0, 0)
        p["ombroR"] = (-8, 0, -6 + 2 * s)
        p["cotoveloR"] = (-45, 0, 0)
        p["ombroL"] = (-10, 0, 6 - 2 * s)
        p["cotoveloL"] = (-55, 0, 0)
        p["martelo"] = (-14, 0, 0)
        p["pluma"] = (4 * s, 0, 0)
    elif anim in ("run", "dodge"):
        k = 1.0 if anim == "run" else 1.35
        a = 48 * k
        p["quad_z"] = 0.045 * abs(s) * k - 0.03
        p["tronco"] = (-9 * k, 6 * s, 0)
        p["cabeca"] = (4 * k, -4 * s, 0)
        p["coxaL"] = (-a * s, 0, 0)
        p["coxaR"] = (a * s, 0, 0)
        p["joelhoL"] = (max(0, 70 * c * k) + 8, 0, 0)
        p["joelhoR"] = (max(0, -70 * c * k) + 8, 0, 0)
        p["ombroL"] = (-18 + 28 * s, 0, 8)
        p["cotoveloL"] = (-70, 0, 0)
        p["ombroR"] = (-30 - 22 * s, 0, -4)
        p["cotoveloR"] = (-65, 0, 0)
        p["martelo"] = (-32 + 8 * s, 0, 0)
        p["pluma"] = (-18 + 6 * s, 0, 0)
    elif anim == "attack":
        # 6 quadros: preparar, erguer, descer (impacto no 3), recuperar
        fases = [
            dict(ombroR=(-175, 0, -8), cotoveloR=(-70, 0, 0), tronco=(10, 0, -18), martelo=(-60, 0, 0), quad_z=-0.02, coxaL=(10, 0, 0), coxaR=(-18, 0, 0), joelhoL=(14, 0, 0), joelhoR=(20, 0, 0), ombroL=(-25, 0, 20), cotoveloL=(-60, 0, 0)),
            dict(ombroR=(-200, 0, -10), cotoveloR=(-40, 0, 0), tronco=(16, 0, -26), martelo=(-100, 0, 0), quad_z=-0.03, coxaL=(10, 0, 0), coxaR=(-22, 0, 0), joelhoL=(18, 0, 0), joelhoR=(26, 0, 0), ombroL=(-25, 0, 24), cotoveloL=(-60, 0, 0)),
            dict(ombroR=(-120, 0, -6), cotoveloR=(-20, 0, 0), tronco=(-12, 0, 10), martelo=(10, 0, 0), quad_z=-0.05, coxaL=(-26, 0, 0), coxaR=(20, 0, 0), joelhoL=(30, 0, 0), joelhoR=(10, 0, 0), ombroL=(-30, 0, 18), cotoveloL=(-60, 0, 0)),
            dict(ombroR=(-62, 0, -4), cotoveloR=(-6, 0, 0), tronco=(-26, 0, 16), martelo=(130, 0, 0), quad_z=-0.1, coxaL=(-36, 0, 0), coxaR=(26, 0, 0), joelhoL=(40, 0, 0), joelhoR=(14, 0, 0), ombroL=(-34, 0, 18), cotoveloL=(-60, 0, 0)),
            dict(ombroR=(-56, 0, -4), cotoveloR=(-8, 0, 0), tronco=(-22, 0, 14), martelo=(135, 0, 0), quad_z=-0.1, coxaL=(-34, 0, 0), coxaR=(24, 0, 0), joelhoL=(38, 0, 0), joelhoR=(14, 0, 0), ombroL=(-34, 0, 18), cotoveloL=(-60, 0, 0)),
            dict(ombroR=(-30, 0, -6), cotoveloR=(-40, 0, 0), tronco=(-6, 0, 4), martelo=(95, 0, 0), quad_z=-0.04, coxaL=(-12, 0, 0), coxaR=(8, 0, 0), joelhoL=(14, 0, 0), joelhoR=(6, 0, 0), ombroL=(-14, 0, 10), cotoveloL=(-55, 0, 0)),
        ]
        for k, v in fases[i].items():
            p[k] = v
        p["pluma"] = (-14, 0, 0)
    elif anim == "death":
        # cai para trás: i/(n-1) de 0 a 1
        t = i / (n - 1)
        e = t * t * (3 - 2 * t)
        p["raiz_rx"] = lerp(0, 82, e)
        p["raiz_z"] = lerp(0, 0.18, e)
        p["quad_z"] = lerp(0, -0.12, e)
        p["tronco"] = (lerp(0, -14, e), 0, 0)
        p["cabeca"] = (lerp(0, -14, e), 0, 0)
        p["ombroR"] = (lerp(-8, -60, e), 0, lerp(-6, -35, e))
        p["cotoveloR"] = (-30, 0, 0)
        p["ombroL"] = (lerp(-10, -50, e), 0, lerp(6, 40, e))
        p["cotoveloL"] = (-30, 0, 0)
        p["coxaL"] = (lerp(0, -24, e), 0, 0)
        p["coxaR"] = (lerp(0, 18, e), 0, 0)
        p["joelhoL"] = (lerp(0, 30, e), 0, 0)
        p["joelhoR"] = (lerp(0, 40, e), 0, 0)
        p["martelo"] = (lerp(-14, 70, e), 0, 0)
        p["pluma"] = (lerp(0, 40, e), 0, 0)
    return p


def aplicar(P, p, yaw):
    for nome, v in p.items():
        if nome in P and isinstance(v, tuple):
            P[nome].rotation_euler = deg(*v)
    P["quad"].location = (0, 0, 0.62 + p["quad_z"])
    P["raiz"].location = (0, 0, p["raiz_z"])
    P["raiz"].rotation_euler = deg(p["raiz_rx"], 0, yaw)
    # martelo: p["martelo"][0] é o ângulo ABSOLUTO (0 = cabeça para cima, + = para a frente)
    soma = p["raiz_rx"] + p["tronco"][0] + p["ombroR"][0] + p["cotoveloR"][0]
    P["martelo"].rotation_euler = deg(p["martelo"][0] - soma, 0, p["martelo"][2] if len(p["martelo"]) > 2 else 0)
    somaL = p["raiz_rx"] + p["tronco"][0] + p["ombroL"][0] + p["cotoveloL"][0]
    P["escudo"].rotation_euler = deg(p["escudo"][0] - somaL, 0, 0)


def cena():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.samples = 24
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
    bg.inputs["Color"].default_value = (0.55, 0.58, 0.7, 1)
    bg.inputs["Strength"].default_value = 0.55
    # luz principal do alto à esquerda (câmera) + contraluz frio
    l = bpy.data.lights.new("sol", "SUN")
    l.energy = 3.4
    l.angle = math.radians(25)
    lo = bpy.data.objects.new("sol", l)
    s.collection.objects.link(lo)
    lo.rotation_euler = deg(48, 0, -35)
    l2 = bpy.data.lights.new("rim", "SUN")
    l2.energy = 1.1
    l2.color = (0.55, 0.6, 1.0)
    l2o = bpy.data.objects.new("rim", l2)
    s.collection.objects.link(l2o)
    l2o.rotation_euler = deg(60, 0, 150)
    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    cam.ortho_scale = Q / ESCALA_PX
    co = bpy.data.objects.new("cam", cam)
    s.collection.objects.link(co)
    e = math.radians(ELEV)
    d = 20
    co.location = (0, -d * math.cos(e), d * math.sin(e))
    co.rotation_euler = (math.radians(90 - ELEV), 0, 0)
    # origem do mundo no pixel PIVO do quadro
    cam.shift_x = (Q / 2 - PIVO[0]) / Q * -1
    cam.shift_y = (PIVO[1] - Q / 2) / Q * -1 * -1
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
