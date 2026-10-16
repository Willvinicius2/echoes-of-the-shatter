"""Biblioteca de animacao por keyframes (sem IA, sem download) para o Rig_Humanoid_Chibi.

Uso (dentro do Blender, -b): importar o FBX do modelo/esqueleto, depois

    arm = load_rig(path_fbx)
    make_action(arm, "AN_Exemplo", keys={0: {...}, 12: {...}, 24: "loop"}, loop=True)

Cada pose e um dicionario {osso: rotacao}, rotacao em GRAUS (rx, ry, rz) no "espaco do personagem":
    X = esquerda do personagem, Y = cima, Z = frente (os eixos do FBX/Unity importado).
A rotacao e aplicada nos eixos de repouso do esqueleto (nao nos eixos locais do osso), entao e intuitiva:

    Spine/Chest/Neck/Head : rx > 0 inclina para a frente, rx < 0 para tras
                            ry > 0 gira para a esquerda do personagem
                            rz > 0 inclina para a direita do personagem
    UpperArm/UpperLeg     : (osso aponta para baixo) rx > 0 balanca para tras, rx < 0 para a frente
    Left*  UpperArm       : rz > 0 abre o braco para o lado;  Right*: rz < 0 abre (use LR() para espelhar)
    LowerArm              : rx < 0 dobra o cotovelo (mao sobe e vai a frente)
    LowerLeg              : rx > 0 dobra o joelho

Entrada completa de um osso: tupla (rx, ry, rz) ou dict {'rot': (..), 'loc': (x, y, z), 'scale': s}.
`scale` so vale na morte (allow_scale=True em make_action) e e multiplicador relativo a 1; fora disso e ignorado
e nenhuma curva de escala e exportada.
`loc` e deslocamento em metros no espaco do personagem (multiplicado por loc_scale; use so em Hips, e so em
esqueletos cujo repouso seja o do proprio modelo, porque o FBX grava a posicao absoluta).

Chaves: {quadro: pose}. Ossos nao citados numa chave mantem o ultimo valor citado (parte de 0). Chaves
especiais por quadro: '_i' interpolacao ('BEZIER' padrao, 'LINEAR', 'SINE', 'QUAD', 'CUBIC', 'EXPO', 'CONSTANT'),
'_e' easing ('EASE_IN', 'EASE_OUT', 'EASE_IN_OUT'); valem para o trecho que SEGUE essa chave.
Uma chave pode ser a string "loop" (copia do quadro 0). Sem root motion: nenhum clip move o osso root.
"""
import bpy, math, os, sys, json
from mathutils import Matrix, Euler, Quaternion, Vector

FPS = 30
SPECIAL = ("_i", "_e")


# ---------------------------------------------------------------- utilitarios de pose
def LR(name, rx=0.0, ry=0.0, rz=0.0):
    """Par simetrico Left/Right de um osso (ry e rz espelhados)."""
    return {"Left" + name: (rx, ry, rz), "Right" + name: (rx, -ry, -rz)}


def merge(*poses):
    out = {}
    for p in poses:
        out.update(p)
    return out


def mirror(pose):
    """Espelha uma pose (troca Left/Right, inverte ry/rz e loc x)."""
    def swap(n):
        if n.startswith("Left"):
            return "Right" + n[4:]
        if n.startswith("Right"):
            return "Left" + n[5:]
        if n.endswith("_l"):
            return n[:-2] + "_r"
        if n.endswith("_r"):
            return n[:-2] + "_l"
        return n
    out = {}
    for n, v in pose.items():
        if n in SPECIAL:
            out[n] = v
            continue
        d = _norm(v)
        r = d["rot"]
        nd = dict(d)
        nd["rot"] = (r[0], -r[1], -r[2])
        if "loc" in d:
            l = d["loc"]
            nd["loc"] = (-l[0], l[1], l[2])
        out[swap(n)] = nd
    return out


def lerp_pose(a, b, t):
    """Mistura linear de duas poses (rotacoes em graus)."""
    out = {}
    for n in set(a) | set(b):
        if n in SPECIAL:
            continue
        da, db = _norm(a.get(n, (0, 0, 0))), _norm(b.get(n, (0, 0, 0)))
        d = {"rot": tuple(x + (y - x) * t for x, y in zip(da["rot"], db["rot"]))}
        if "loc" in da or "loc" in db:
            la, lb = da.get("loc", (0, 0, 0)), db.get("loc", (0, 0, 0))
            d["loc"] = tuple(x + (y - x) * t for x, y in zip(la, lb))
        if "scale" in da or "scale" in db:
            sa, sb = da.get("scale", 1.0), db.get("scale", 1.0)
            d["scale"] = sa + (sb - sa) * t
        out[n] = d
    return out


def _norm(v):
    if isinstance(v, dict):
        d = dict(v)
        d["rot"] = tuple(d.get("rot", (0, 0, 0)))
        return d
    return {"rot": tuple(v)}


def ease(t):
    """Suavizacao (smoothstep) para montar pocos em funcoes."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- cena / rig
def load_rig(fbx_path):
    """Limpa a cena, importa o FBX e devolve o objeto do esqueleto (ossos em Y-up, objeto girado +90 X)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx_path)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.render.fps_base = 1.0
    return arm


def hips_scale(arm, ref=0.46):
    """Fator de tamanho do esqueleto (altura do Hips / altura do Hips do Rig_Humanoid_Chibi)."""
    return arm.data.bones["Hips"].head_local.y / ref


def _basis(bone, d):
    R = bone.matrix_local.to_3x3()
    rx, ry, rz = (math.radians(a) for a in d["rot"])
    D = Euler((rx, ry, rz), 'XYZ').to_matrix()
    q = (R.inverted() @ D @ R).to_quaternion()
    loc = None
    if "loc" in d:
        loc = R.inverted() @ Vector(d["loc"])
    return q, loc


def _channelbags(action):
    """fcurves da acao (API de slots do Blender 4.4+/5.x, com fallback para a antiga)."""
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


def make_action(arm, name, keys, loop=False, loc_scale=1.0, mirror_all=False, default_i='BEZIER', allow_scale=False):
    """Cria a acao `name` no esqueleto. Devolve (acao, ultimo_quadro).
    Escala: so e gravada com allow_scale=True (use apenas na morte). O valor e um MULTIPLICADOR sobre a escala de
    repouso do osso (1.0 = sem mudar; 0.12 = 12% do tamanho do modelo), nunca um valor absoluto do armature."""
    keys = dict(keys)
    frames = sorted(keys)
    first = frames[0]
    for f in list(frames):
        if isinstance(keys[f], str) and keys[f] == "loop":
            keys[f] = {n: v for n, v in keys[first].items() if n not in SPECIAL}
    if mirror_all:
        keys = {f: mirror(p) for f, p in keys.items()}
    if arm.animation_data is None:
        arm.animation_data_create()
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    pb = arm.pose.bones
    for b in pb:
        b.rotation_mode = 'QUATERNION'
        b.rotation_quaternion = Quaternion((1, 0, 0, 0))
        b.location = (0, 0, 0)
        b.scale = (1, 1, 1)
    touched = set()
    for f in frames:
        touched |= {n for n in keys[f] if n not in SPECIAL}
    missing = touched - set(pb.keys())
    if missing:
        raise KeyError(f"ossos inexistentes no esqueleto: {sorted(missing)}")
    state = {n: {"rot": (0, 0, 0)} for n in touched}
    lastq = {n: Quaternion((1, 0, 0, 0)) for n in touched}
    interp = {}
    for f in frames:
        p = keys[f]
        for n, v in p.items():
            if n in SPECIAL:
                continue
            d = _norm(v)
            old = state[n]
            for k in ("loc", "scale"):      # mantem o ultimo valor citado
                if k not in d and k in old:
                    d[k] = old[k]
            state[n] = d
        interp[f] = (p.get("_i", default_i), p.get("_e", None))
        for n in touched:
            d = state[n]
            bone = arm.data.bones[n]
            q, loc = _basis(bone, d)
            if q.dot(lastq[n]) < 0:
                q.negate()
            lastq[n] = q
            b = pb[n]
            b.rotation_quaternion = q
            b.keyframe_insert("rotation_quaternion", frame=f, group=n)
            if loc is not None:
                b.location = loc * loc_scale
                b.keyframe_insert("location", frame=f, group=n)
            if allow_scale and "scale" in d:
                s = d["scale"]
                b.scale = (s, s, s)
                b.keyframe_insert("scale", frame=f, group=n)
    for fc in _channelbags(act):
        for kp in fc.keyframe_points:
            i, e = interp.get(int(round(kp.co.x)), (default_i, None))
            kp.interpolation = i
            if e:
                kp.easing = e
        fc.update()
    last = frames[-1]
    act["frame_first"], act["frame_last"] = first, last
    return act, last


def reset_pose(arm):
    for b in arm.pose.bones:
        b.rotation_mode = 'QUATERNION'
        b.rotation_quaternion = Quaternion((1, 0, 0, 0))
        b.location = (0, 0, 0)
        b.scale = (1, 1, 1)


# ---------------------------------------------------------------- exportacao
FBX_ANIM = dict(global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                bake_space_transform=True, axis_forward='-Z', axis_up='Y',
                object_types={'ARMATURE'}, add_leaf_bones=False, use_armature_deform_only=False,
                primary_bone_axis='Y', secondary_bone_axis='X', path_mode='RELATIVE',
                bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                bake_anim_force_startend_keying=True, bake_anim_step=1.0, bake_anim_simplify_factor=0.0)


def export_action(arm, act, path, first=None, last=None):
    """FBX so com o armature e a acao `act` (Y-up, escala 1, sem mesh)."""
    arm.animation_data.action = act
    sc = bpy.context.scene
    sc.name = act.name      # o FBX grava o take com o nome da cena (vira o nome do clip na Unity)
    sc.frame_start = int(act["frame_first"] if first is None else first)
    sc.frame_end = int(act["frame_last"] if last is None else last)
    for o in bpy.data.objects:
        o.select_set(False)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, **FBX_ANIM)


# ---------------------------------------------------------------- previa
def setup_preview(w=512, h=512):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.studio_light = 'outdoor.sl'
    sh.color_type = 'TEXTURE'
    sh.show_shadows = True
    sh.shadow_intensity = 0.4
    sh.show_cavity = False
    sh.show_object_outline = True
    sh.object_outline_color = (0.05, 0.04, 0.07)
    sh.background_type = 'VIEWPORT'
    sh.background_color = (0.12, 0.10, 0.15)
    sc.display.light_direction = (-0.3, 0.3, 0.9)
    if sc.world is None:
        sc.world = bpy.data.worlds.new("W")
    sc.world.color = (0.12, 0.10, 0.15)
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.exposure = 0.6
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'


def add_stage(height, cam_dir=(0.62, -0.78, 0.22), fill=1.25, center_y=None):
    """Chao + camera ortografica 3/4 frontal (o personagem olha para -Y no Blender)."""
    sc = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=height * 30, location=(0, 0, -0.005))
    fl = bpy.context.active_object
    fl.name = "Preview_Floor"
    mat = bpy.data.materials.new("PrevFloor")
    mat.diffuse_color = (0.22, 0.19, 0.24, 1)
    fl.data.materials.append(mat)
    cam = bpy.data.cameras.new("PrevCam")
    cam.type = 'ORTHO'
    cam.ortho_scale = height * fill
    co = bpy.data.objects.new("PrevCam", cam)
    sc.collection.objects.link(co)
    target = Vector((0, 0, (center_y if center_y is not None else height * 0.5)))
    d = Vector(cam_dir).normalized() * height * 6
    co.location = target + d
    direction = target - co.location
    co.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co


def render_frames(arm, act, frames, out_dir, prefix):
    os.makedirs(out_dir, exist_ok=True)
    arm.animation_data.action = act
    sc = bpy.context.scene
    paths = []
    for f in frames:
        sc.frame_set(int(f))
        p = os.path.join(out_dir, f"{prefix}_f{int(f):03d}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        paths.append(p)
    return paths
