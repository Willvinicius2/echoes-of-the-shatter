"""Funcoes comuns dos build_<peca>.py do Arqueiro modular (rodar no Blender -b).

Fonte (somente leitura): variavel de ambiente ARQ_FONTE (padrao abaixo).
Saida: godot/art/models/personagens/arqueiro/ (ARQ_SAIDA para trocar).
Uso: blender -b -P build_capuz.py
"""
import os
import bpy

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
FONTE = os.environ.get("ARQ_FONTE", "D:/openclaude/_trabalho-claude/modelos3d")
FINAL = FONTE + "/modular_arqueiro/final"
ARCO = FONTE + "/m09_armas/arco/final"
ALJAVA = FONTE + "/m09_armas/aljava/final"
SAIDA = os.environ.get("ARQ_SAIDA", os.path.join(RAIZ, "godot", "art", "models", "personagens", "arqueiro"))


def limpar():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def importar(fbx):
    bpy.ops.import_scene.fbx(filepath=fbx)


def material_simples(malha, nome, textura_bc):
    """Um unico material M_Arqueiro_<Peca>: Principled com so a textura BC (albedo), sem normal map."""
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(textura_bc, check_existing=True)
    tex.image.colorspace_settings.name = "sRGB"
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.9
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    malha.data.materials.clear()
    malha.data.materials.append(mat)


def aplicar_rotacao(objs):
    """Zera a rotacao de 90 graus em X que o importador FBX deixa na armature."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def exportar(nome_glb, objs):
    os.makedirs(SAIDA, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    caminho = os.path.join(SAIDA, nome_glb)
    bpy.ops.export_scene.gltf(
        filepath=caminho, export_format="GLB", use_selection=True,
        export_animations=False, export_skins=True, export_yup=True,
        export_apply=False, export_materials="EXPORT", export_image_format="AUTO",
        export_leaf_bone=False,
    )
    print("EXPORTADO", caminho)


def peca_personagem(fbx_nome, nome_malha_final, material, glb):
    """Capuz/peitoral/calca/luvas/botas: armature Rig_Humanoid_Chibi + malha skinada, sem animacao."""
    limpar()
    importar(f"{FINAL}/{fbx_nome}")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    malhas = [o for o in bpy.data.objects if o.type == "MESH"]
    assert len(malhas) == 1, malhas
    m = malhas[0]
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    arm.animation_data_clear()
    aplicar_rotacao([arm, m])
    m.name = nome_malha_final
    material_simples(m, material, f"{FINAL}/T_Archer_Starter_BC.png")
    exportar(glb, [arm, m])


def arma_estatica(fbx, tex, nome, material, glb, origem=None):
    """Arma sem armature. origem=(x,y,z) em Blender (Z-up) para mover a origem; padrao: a do FBX."""
    limpar()
    importar(fbx)
    m = next(o for o in bpy.data.objects if o.type == "MESH")
    aplicar_rotacao([m])
    if origem is not None:
        bpy.context.scene.cursor.location = origem
        bpy.ops.object.select_all(action="DESELECT")
        m.select_set(True)
        bpy.context.view_layer.objects.active = m
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    m.name = nome
    material_simples(m, material, tex)
    exportar(glb, [m])
