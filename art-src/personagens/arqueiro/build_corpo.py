"""Arqueiro: corpo base + 9 animacoes -> Arqueiro_Corpo.glb. Roda no Blender em lote (sem IA, sem download).
Uso (TEMP/TMP no disco D):
  blender -b --factory-startup -P build_corpo.py -- glb              # exporta o GLB e o arqueiro_eventos.json
  blender -b --factory-startup -P build_corpo.py -- previas [clipe..] # quadros de previa em previas/anim/<clipe>/ (um render por vez)
  blender -b --factory-startup -P build_corpo.py -- verificar         # reimporta o GLB: acoes, ossos, deslizamento dos pes
"""
import bpy, sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "art-src", "animacao"))
import anim_lib as A
import clips_arqueiro as C
sys.path.insert(0, HERE)
import proporcao

FBX = os.environ.get("ARQ_CORPO_FBX") or r"D:\openclaude\_trabalho-claude\modelos3d\modular_arqueiro\final\SK_Archer_Body.fbx"
TEX = os.environ.get("ARQ_CORPO_TEX") or os.path.join(HERE, "tex_corpo", "T_Archer_Body_BC.png")  # repintada por pintar_corpo.py
BOW = r"D:\openclaude\_trabalho-claude\modelos3d\m09_armas\arco\final\SM_Weapon_Bow.fbx"
BOW_TEX = r"D:\openclaude\_trabalho-claude\modelos3d\m09_armas\arco\final\T_Weapon_Bow_BC.png"
GLB = os.path.join(REPO, "godot", "art", "models", "personagens", "arqueiro", "Arqueiro_Corpo.glb")
EVENTOS = os.path.join(REPO, "art-src", "animacao", "arqueiro_eventos.json")
PREV = os.path.join(HERE, "previas", "anim")
BOW_OFF = (0.0, 0.0, 0.0)
AIM_CAM = (1.0, -0.25, 0.12)
AIM_CLIPS = {"AN_Arqueiro_AimIdle": (1.0, -0.25, 0.12), "AN_Arqueiro_Draw": (-1.0, -0.3, 0.12), "AN_Arqueiro_Release": (-1.0, -0.3, 0.12)}


def textura(nome_mat, png):
    mat = bpy.data.materials.get(nome_mat) or bpy.data.materials.new(nome_mat)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(png, check_existing=True)
    img.image.colorspace_settings.name = "sRGB"
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.85
    return mat


def preparar():
    arm = A.load_rig(FBX)
    proporcao.aplicar(arm)   # chibi (identico em todos os modulos)
    mat = textura("M_Archer_Body", TEX)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.data.materials.clear()
            o.data.materials.append(mat)
    clips = C.build(A, arm)
    return arm, clips


def exportar_glb():
    arm, clips = preparar()
    arm.animation_data.action = None
    ad = arm.animation_data
    for c in clips:                      # uma faixa NLA por acao: o nome da faixa vira o nome da animacao no glTF
        act = c["action"]
        tr = ad.nla_tracks.new()
        tr.name = act.name
        st = tr.strips.new(act.name, int(act["frame_first"]), act)
        st.name = act.name
    os.makedirs(os.path.dirname(GLB), exist_ok=True)
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = max(c["last"] for c in clips)
    bpy.ops.export_scene.gltf(filepath=GLB, export_format='GLB', export_yup=True, export_apply=False,
                              export_image_format='AUTO', export_materials='EXPORT', export_skins=True,
                              export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
                              export_frame_step=1, export_optimize_animation_size=False, export_anim_single_armature=True,
                              export_cameras=False, export_lights=False, export_extras=False, export_def_bones=False)
    eventos = {}
    for c in clips:
        eventos[c["action"].name] = dict(frames=c["last"], segundos=round(c["last"] / A.FPS, 3), loop=c["loop"],
                                         eventos=c.get("events", {}), nota=c.get("note", ""))
    with open(EVENTOS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(eventos, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("GLB", GLB, os.path.getsize(GLB))


def previas(nomes):
    arm, clips = preparar()
    # arco so na previa, no socket da mao esquerda
    arm_objs = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=BOW)
    bow = [o for o in bpy.data.objects if o not in arm_objs]
    m = textura("M_Bow", BOW_TEX)
    for o in bow:
        if o.type == 'MESH':
            o.data.materials.clear()
            o.data.materials.append(m)
    root = [o for o in bow if o.parent is None][0]
    mw = root.matrix_world.copy()
    rot, sc_ = mw.to_3x3().normalized(), mw.to_scale()
    bone = arm.data.bones["socket_weapon_l"]
    rest_world = arm.matrix_world @ bone.matrix_local
    # arco na vertical (como importado), com o centro dele no socket da mao esquerda
    from mathutils import Matrix, Vector
    want = Matrix.Translation(rest_world.translation + Vector(BOW_OFF)) @ rot.to_4x4() @ Matrix.Diagonal((*sc_, 1.0))
    root.parent = arm
    root.parent_type = 'BONE'
    root.parent_bone = "socket_weapon_l"
    root.matrix_basis = Matrix.Identity(4)
    root.matrix_parent_inverse = rest_world.inverted() @ want
    A.setup_preview()
    A.add_stage(1.9, fill=1.08, cam_dir=C.CAM, center_y=0.9)
    for c in clips:
        if nomes and c["action"].name not in nomes and c["action"].name.replace("AN_Arqueiro_", "") not in nomes:
            continue
        cam_dir = AIM_CLIPS.get(c["action"].name, C.CAM)
        from mathutils import Vector
        cam = bpy.context.scene.camera
        tgt = Vector((0, 0, 0.9))
        cam.location = tgt + Vector(cam_dir).normalized() * 1.9 * 6
        cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        A.render_frames(arm, c["action"], c["preview"], os.path.join(PREV, c["action"].name), c["action"].name)
    print("DONE previas")


def verificar():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB)
    acts = sorted(a.name for a in bpy.data.actions)
    print("ACOES", len(acts), acts)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    print("OSSOS", len(arm.data.bones), sorted(b.name for b in arm.data.bones))
    print("MALHAS", [(o.name, len(o.data.vertices), [s.material.name for s in o.material_slots]) for o in bpy.data.objects if o.type == 'MESH'])
    mx = max(max(v.z for v in (o.matrix_world @ __import__("mathutils").Vector(c) for c in o.bound_box)) for o in bpy.data.objects if o.type == 'MESH')
    print("ALTURA_MAX", round(mx, 3))
    sc = bpy.context.scene
    for clip, cyc, stance in (("AN_Arqueiro_Walk", 30, 18), ("AN_Arqueiro_Run", 18, 6.84)):
        act = next((a for a in bpy.data.actions if a.name == clip or a.name.startswith(clip)), None)
        arm.animation_data_create()
        arm.animation_data.action = act
        try:
            arm.animation_data.action_slot = act.slots[0]
        except Exception:
            pass
        pf = arm.pose.bones.get("LeftFoot")
        ys, zs = [], []
        for f in range(0, cyc):
            sc.frame_set(0)
            p = arm.matrix_world @ pf.matrix @ __import__("mathutils").Vector((0, 0, 0))
            ys.append(p.y)
            zs.append(p.z)
        print(clip, "pe esq. (Y-up reimportado) quadro: y,z")
        # no glTF reimportado o Z do Blender e o 'cima'; o avanco e o eixo Y do Blender
        ps = []
        for f in range(0, cyc):
            fr = f * sc.render.fps / 30.0       # o importador usa o fps da cena (24): amostra por tempo
            sc.frame_set(int(fr), subframe=fr - int(fr))
            ps.append(arm.matrix_world @ pf.matrix @ __import__("mathutils").Vector((0, 0, 0)))
        print("  y(m):", [round(q.y, 3) for q in ps])
        print("  alt(m):", [round(q.z, 3) for q in ps])
        n_st = int(round(stance))
        d = [ps[i + 1].y - ps[i].y for i in range(n_st - 1)]
        up = [ps[i].z for i in range(n_st)]
        print("  apoio: passo(m/quadro) medio %.4f min %.4f max %.4f | altura min %.4f max %.4f" % (sum(d) / len(d), min(d), max(d), min(up), max(up)))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    modo = argv[0]
    if modo == "glb":
        exportar_glb()
    elif modo == "previas":
        previas(argv[1:])
    elif modo == "verificar":
        verificar()
