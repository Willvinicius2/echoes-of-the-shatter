"""Adiciona os 3 ossos de manto (Cape_L, Cape_R, Cape_B, filhos de Chest, deformam, peso zero) a um rig. Idempotente; mesma posicao sempre.
Todos os modulos do arqueiro dark precisam do mesmo esqueleto: aplicar a corpo, botas, bracadeiras etc.

Uso (Blender 5.1, -b):
  blender -b --factory-startup -P manto_add_cape_bones.py -- <entrada> <saida>
  <entrada>/<saida> = .blend (esqueleto Rig_Humanoid_Chibi; recomendado, depois reexportar o FBX com o s8/gb_rig) ou .glb (testado: posicoes iguais ao torso).
  .fbx -> .fbx NAO e confiavel (o importador do FBX gira o esqueleto): para o FBX do corpo aplique ao .blend final e reexporte.
Posicoes no espaco do corpo (z para cima, frente -Y, metros, esqueleto na escala 1 do corpo de 1,80 m).
Como modulo: add_cape_bones(arm) com o armature em modo objeto."""
import bpy, sys, os
from mathutils import Vector

CAPE_BONES = {   # nome: (cabeca, cauda) no espaco do esqueleto
    "Cape_L": ((0.16, 0.10, 1.42), (0.40, 0.17, 0.62)),
    "Cape_R": ((-0.16, 0.10, 1.42), (-0.40, 0.17, 0.62)),
    "Cape_B": ((0.0, 0.14, 1.42), (0.0, 0.30, 0.55)),
}


def add_cape_bones(arm):
    if all(n in arm.data.bones for n in CAPE_BONES):
        return False
    view = bpy.context.view_layer
    for o in bpy.data.objects:
        o.select_set(False)
    view.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    inv = arm.matrix_world.inverted()          # posicoes sao do mundo (z para cima); o FBX importado pode vir girado/escalado
    parent = eb["Chest"]
    for n, (h, t) in CAPE_BONES.items():
        if n in eb:
            continue
        b = eb.new(n)
        b.head, b.tail, b.roll = inv @ Vector(h), inv @ Vector(t), 0.0
        b.parent = parent
        b.use_connect = False
        b.use_deform = True
    bpy.ops.object.mode_set(mode='OBJECT')
    return True


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    src, dst = argv[0], argv[1]
    ext = os.path.splitext(src)[1].lower()
    if ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=src)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if ext == ".glb":
            bpy.ops.import_scene.gltf(filepath=src)
        else:
            bpy.ops.import_scene.fbx(filepath=src, automatic_bone_orientation=False, use_anim=False)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    changed = add_cape_bones(arm)
    out_ext = os.path.splitext(dst)[1].lower()
    if out_ext == ".blend":
        bpy.ops.wm.save_as_mainfile(filepath=dst)
    elif out_ext == ".glb":
        bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_yup=True, export_apply=False, export_image_format='AUTO',
                                  export_materials='EXPORT', export_normals=True, export_texcoords=True, export_skins=True)
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from mdl_common import import_graybox
        gb_lib, gb_rig = import_graybox()
        meshes = [o for o in bpy.data.objects if o.type == 'MESH']
        gb_rig.export_fbx_rigged(arm, meshes, dst)
    print("CAPEBONES", "adicionados" if changed else "ja existiam", [(b.name, b.parent.name if b.parent else None) for b in arm.data.bones if b.name.startswith("Cape")])


if __name__ == "__main__":
    main()
