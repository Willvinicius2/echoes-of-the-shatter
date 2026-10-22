"""Proporcao CHIBI do Arqueiro (cabeca grande, tronco e pernas curtos, ombros caidos, bracos relaxados).

Rodar DENTRO do Blender, logo apos importar o FBX do rig (e, no capuz, depois de criar as malhas skinadas), IGUAL para
o corpo e para todos os modulos:

    import proporcao
    proporcao.aplicar(arm)                  # arm = o objeto Armature (todas as malhas skinadas nele vao junto)
    proporcao.aplicar(arm, malhas=[...])    # ou so as malhas dadas
    proporcao.aplicar(arm, params=dict(...))  # sobrescreve parametros (nao usar nos build_<peca>: tem que ser identico)

O que faz (equivalente a escalar ossos em pose mode + "Apply Pose as Rest Pose", sem a escala herdada pelos filhos):
cada osso ganha escala de comprimento e de largura (so nele; os filhos nao herdam a escala, so a posicao e a rotacao)
e uma rotacao de repouso em torno da cabeca do osso (herdada pelos filhos). Os vertices sao deformados por skinning
linear (os mesmos pesos do FBX), os ossos sao regravados no modo de edicao e o repouso novo passa a ser o chibi
relaxado. Por fim o personagem inteiro sobe/desce para a sola do pe ficar em y=0 (Z=0 no Blender).

Eixos dos parametros (espaco do personagem, o mesmo da anim_lib): X esquerda do personagem, Y cima, Z frente.
Rotacoes em graus (rx, ry, rz) em torno desses eixos, na cabeca do osso; chaves 'Left'/'Right' sao espelhadas
(ry e rz invertidos no lado direito). rz>0 no braco esquerdo ABRE o braco; rz<0 fecha.
Os numeros abaixo sao de design do script de arte (nao sao regra do jogo).
"""
import math
import bpy
from mathutils import Matrix, Vector, Euler

PARAMS = {
    # escala do COMPRIMENTO do osso (ao longo dele). Osso sem entrada = 1.0
    "comprimento": {"Head": 1.40, "Neck": 1.00, "Spine": 0.88, "Chest": 0.88,
                    "UpperLeg": 0.80, "LowerLeg": 0.80, "UpperArm": 0.95, "LowerArm": 0.95,
                    "Hand": 1.18, "Foot": 1.15, "Toes": 1.15},
    # escala da LARGURA (perpendicular ao osso). Osso sem entrada = 1.0
    "largura": {"Head": 1.40, "Hand": 1.18, "Foot": 1.15, "Toes": 1.15},
    # rotacao de repouso (graus) em torno da cabeca do osso, herdada pelos filhos
    "rotacao": {
        "LeftShoulder": (0, 0, -10),     # ombros caidos
        "LeftUpperArm": (0, 0, -3),
        "LeftLowerArm": (-14, 0, 0),     # cotovelo levemente flexionado (mao vai a frente)
        "LeftUpperLeg": (-9, 0, 0),      # joelho levemente flexionado: coxa a frente...
        "LeftLowerLeg": (12, 0, 0),      # ...e canela atras
    },
    "pe_plano": True,                    # compensa a rotacao das pernas: pe sempre plano no repouso
    "sola_y": 0.0,                       # altura (no repouso antigo) do ponto da sola usado para pousar no chao
}

LADOS = ("Left", "Right")
RX90 = Matrix.Rotation(math.radians(90), 4, "X")   # char (Y cima) -> mundo Blender (Z cima)


def _base(nome):
    for l in LADOS:
        if nome.startswith(l):
            return nome[len(l):]
    return nome


def _rot(params, nome):
    r = params["rotacao"].get(nome)
    if r is None and nome.startswith("Right"):
        l = params["rotacao"].get("Left" + nome[5:])
        if l is not None:
            r = (l[0], -l[1], -l[2])
    if r is None:
        return Matrix.Identity(3)
    return Euler(tuple(math.radians(a) for a in r), "XYZ").to_matrix()


def rotacoes_acumuladas(arm, params=None):
    """{osso: matriz 3x3} com a rotacao de repouso ACUMULADA (espaco do personagem) que aplicar() deu a cada osso.
    A animacao usa isso para converter poses escritas no repouso antigo: D' = Q_pai @ D @ Q_osso^-1."""
    p = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PARAMS.items()}
    if params:
        for k, v in params.items():
            p[k].update(v) if isinstance(v, dict) else p.__setitem__(k, v)
    pai = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
    Q = {}
    def calc(n):
        if n in Q:
            return Q[n]
        if pai[n] is None:
            Q[n] = _rot(p, n)
        elif p["pe_plano"] and _base(n) == "Foot":
            Q[n] = Matrix.Identity(3)
        else:
            Q[n] = calc(pai[n]) @ _rot(p, n)
        return Q[n]
    for n in pai:
        calc(n)
    return Q


def aplicar(arm, malhas=None, params=None):
    p = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PARAMS.items()}
    if params:
        for k, v in params.items():
            p[k].update(v) if isinstance(v, dict) else p.__setitem__(k, v)
    if malhas is None:
        malhas = [o for o in bpy.data.objects if o.type == "MESH"]
    M = arm.matrix_world.copy()
    A = RX90.inverted() @ M                 # local do armature -> espaco do personagem (Y cima)
    Ainv = A.inverted()
    bones = list(arm.data.bones)
    h0, t0, par = {}, {}, {}
    for b in bones:
        h0[b.name] = A @ b.head_local
        t0[b.name] = A @ b.tail_local
        par[b.name] = b.parent.name if b.parent else None
    ordem = []
    def visita(n):
        if n in ordem:
            return
        if par[n]:
            visita(par[n])
        ordem.append(n)
    for n in h0:
        visita(n)
    S, H, Q = {}, {}, {}
    for n in ordem:
        d = t0[n] - h0[n]
        L = d.length
        d = d / L if L > 1e-9 else Vector((0, 1, 0))
        sl = p["comprimento"].get(_base(n), 1.0)
        sg = p["largura"].get(_base(n), 1.0)
        dd = Matrix(((d.x * d.x, d.x * d.y, d.x * d.z), (d.y * d.x, d.y * d.y, d.y * d.z), (d.z * d.x, d.z * d.y, d.z * d.z)))
        S[n] = Matrix.Identity(3) * sg + dd * (sl - sg)
        pn = par[n]
        R = _rot(p, n)
        if pn is None:
            H[n], Q[n] = h0[n].copy(), R
        else:
            H[n] = H[pn] + Q[pn] @ (S[pn] @ (h0[n] - h0[pn]))
            if p["pe_plano"] and _base(n) == "Foot":
                Q[n] = Matrix.Identity(3)      # pe plano: cancela a rotacao acumulada das pernas
            else:
                Q[n] = Q[pn] @ R
    # pousa no chao: ponto da sola do pe esquerdo
    pf = Vector((h0["LeftFoot"].x, p["sola_y"], h0["LeftFoot"].z))
    sola = H["LeftFoot"] + Q["LeftFoot"] @ (S["LeftFoot"] @ (pf - h0["LeftFoot"]))
    lift = Vector((0, -sola.y, 0))
    for n in ordem:
        if n not in ("root", "socket_fx_ground") and par[n] is not None:
            H[n] = H[n] + lift

    # malhas (skinning linear com os pesos do FBX)
    for ob in malhas:
        Wm = ob.matrix_world.copy()
        Cm = RX90.inverted() @ Wm           # local da malha -> personagem (a malha esta em mundo Z-up)
        Cinv = Cm.inverted()
        nomes = {vg.index: vg.name for vg in ob.vertex_groups}
        novos = []
        for v in ob.data.vertices:
            pc = Cm @ v.co
            acc, tot = Vector((0, 0, 0)), 0.0
            for g in v.groups:
                n = nomes.get(g.group)
                if n in H and g.weight > 0:
                    acc += g.weight * (H[n] + Q[n] @ (S[n] @ (pc - h0[n])))
                    tot += g.weight
            novos.append(Cinv @ (acc / tot) if tot > 1e-9 else v.co.copy())
        for v, nv in zip(ob.data.vertices, novos):
            v.co = nv
        ob.data.update()

    # ossos (modo de edicao)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for e in eb:
        e.use_connect = False
    antigas = {n: (A @ eb[n].matrix @ Matrix.Identity(4)) for n in ordem}   # matrix em espaco de personagem (4x4)
    for n in ordem:
        e = eb[n]
        L = (S[n] @ (t0[n] - h0[n])).length
        R3 = (Q[n] @ antigas[n].to_3x3()).normalized()
        m = Matrix.Translation(H[n]) @ R3.to_4x4()
        e.matrix = Ainv @ m
        e.length = max(L, 1e-4)
    bpy.ops.object.mode_set(mode="OBJECT")
    alt = max((RX90.inverted() @ (ob.matrix_world @ v.co)).y for ob in malhas for v in ob.data.vertices) if malhas else 0.0
    print("PROPORCAO aplicada: altura da malha %.3f m, sola em y=0 (lift %.3f)" % (alt, lift.y))
    return alt
