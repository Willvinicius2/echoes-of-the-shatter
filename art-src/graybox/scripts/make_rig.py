"""Exporta Rig_Humanoid_Chibi.fbx (so o esqueleto, para autoria de animacao e Avatar) e a previa dos ossos."""
import bpy, sys, os, json, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gb_lib import *
from gb_rig import *

reset()
coll = new_coll(RIG_NAME)
arm = make_armature(coll)
export_fbx_rigged(arm, [], f"{FBX}/{RIG_NAME}.fbx")

bones = arm.data.bones
report = dict(version=version_info(), rig=RIG_NAME, bones=len(bones),
              deform_bones=sum(1 for b in bones if b.use_deform),
              hierarchy={b.name: (b.parent.name if b.parent else None) for b in bones},
              head_blender={b.name: [round(c, 3) + 0.0 for c in b.head_local] for b in bones},
              head_unity={b.name: [round(c, 3) + 0.0 for c in to_unity(b.head_local)] for b in bones},
              humanoid=humanoid_check([b.name for b in bones]),
              pose="A (bracos ~60 graus abaixo da horizontal); usar Enforce T-Pose se configurar Humanoid")

# previa: ossos como octaedros (centro dourado, esquerda azul, direita vermelha, sockets ciano)
viz = Builder("Preview_Bones")
for b in bones:
    h, t = b.head_local, b.tail_local
    L = (t - h).length
    if b.name.startswith("socket") or b.name == "root":
        viz.add('box', (0.04, 0.04, 0.04), h, '#3FE0D0')
        continue
    col = '#3A7AD0' if b.name.startswith("Left") else '#D04A3A' if b.name.startswith("Right") else '#E0C060'
    w = max(0.035, min(0.09, L * 0.28))
    viz.add('sph', (w, w, L), (h + t) / 2, col, rot=aim(h, t), seg=4)
    viz.add('sph', (0.035, 0.035, 0.035), h, '#E8E0D0', seg=4)
vo = viz.build()
vo.rotation_euler = (0, 0, math.pi)       # de frente para a camera
fl = Builder("Preview_Floor")
fl.add('box', (6, 6, 0.04), (0, 0, -0.02), '#6A5A55')
fl.build()
setup_render(1200, 900)
game_camera((0, 0, 0.72), 14, ortho_scale=2.6)
render(f"{PREV}/rig_humanoid_chibi.png")
bpy.data.objects.remove(bpy.context.scene.camera)
game_camera((0, 0, 0.75), 14, ortho_scale=2.2, yaw=0, pitch=-5)
render(f"{PREV}/rig_humanoid_chibi_front.png")

json.dump(report, open(f"{PREV}/_rig_report.json", "w"), indent=1)
print("REPORT", json.dumps(report["humanoid"]))
