"""Chanfro e normais suaves para as pecas SM_Cripta_* (rodada 17, cenario "redondinho").

PRONTO, NAO EXECUTADO NO KIT INTEIRO. Teste primeiro em UMA peca e envie a previa ao dono.
Uso (Blender 5.1, sem interface), uma peca por vez:
  blender -b --python art-src/modelos/scripts/env_bevel_kit.py -- <entrada.fbx|.blend> <saida.fbx> [--width 0.04] [--segments 3] [--angle 35]
Nao altera o arquivo de entrada. Por padrao so grava a saida se --out for dado; sem saida, apenas relata.
Efeito: Bevel (largura em metros, limite por angulo) -> normais ponderadas por area/face -> sombreamento suave por angulo.
Nao mexe em UV nem em material; a pintura/AO deve ser reassada depois (env_c_uv_ao.py / env_d_paint.py).
"""
import sys, math, os
import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not argv:
    sys.exit("uso: -- entrada saida.fbx [--width m] [--segments n] [--angle graus]")

def opt(name, default):
    return type(default)(argv[argv.index(name) + 1]) if name in argv else default

src = argv[0]
dst = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else None
width, segs, angle = opt("--width", 0.04), opt("--segments", 3), opt("--angle", 35.0)
smooth_all = "--smooth-all" in argv  # ruinas: todas as faces suaves, normais por area x angulo (sem facetas)

bpy.ops.wm.read_factory_settings(use_empty=True)
if src.lower().endswith(".fbx"):
    bpy.ops.import_scene.fbx(filepath=src)
else:
    bpy.ops.wm.open_mainfile(filepath=src)

for ob in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    # raio nunca maior que ~1/6 da menor dimensao (evita deformar pecas finas)
    w = min(width, min(ob.dimensions) / 6.0)
    m = ob.modifiers.new("Chanfro", "BEVEL")
    m.width, m.segments, m.limit_method = w, segs, "ANGLE"
    m.angle_limit = math.radians(angle)
    m.profile = 0.6
    m.harden_normals = True
    bpy.ops.object.modifier_apply(modifier=m.name)
    wn = ob.modifiers.new("Normais", "WEIGHTED_NORMAL")
    if smooth_all:
        wn.mode = "FACE_AREA_WITH_ANGLE"
        wn.weight = 50
        wn.keep_sharp = False
        bpy.ops.object.shade_smooth(keep_sharp_edges=False)
    else:
        wn.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier=wn.name)
    if not smooth_all:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(60))
    print(f"{ob.name}: bevel {w:.3f} m, tris {sum(len(p.vertices) - 2 for p in ob.data.polygons)}")
    ob.select_set(False)

if dst:
    bpy.ops.export_scene.fbx(filepath=dst, use_selection=False, apply_scale_options="FBX_SCALE_UNITS")
    print("gravado", dst)
