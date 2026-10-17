"""Gera as animacoes de um grupo. Uso:
blender -b --factory-startup -P run_group.py -- <grupo> <fbx_esqueleto> <fbx_previa|-> <pasta_saida>
grupos: shared | guardian | ghost | hound.  Sem IA: so Python do Blender posando os ossos."""
import bpy, sys, os, json, importlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import anim_lib as A

argv = sys.argv[sys.argv.index("--") + 1:]
group, rig_fbx, prev_fbx, out = argv[0], argv[1], argv[2], argv[3]
os.makedirs(out, exist_ok=True)
mod = importlib.import_module({"shared": "clips_shared", "guardian": "clips_guardian", "ghost": "clips_ghost", "hound": "clips_hound"}[group])

# 1) exportacao: esqueleto do proprio rig
arm = A.load_rig(rig_fbx)
clips = mod.build(A, arm)
report = []
for c in clips:
    act = c["action"]
    path = os.path.join(out, act.name + ".fbx")
    A.export_action(arm, act, path)
    report.append(dict(name=act.name, file=os.path.basename(path), frames=c["last"], seconds=round(c["last"] / A.FPS, 3),
                       loop=c["loop"], events=c.get("events", {}), note=c.get("note", "")))
    print("EXPORT", path)

# 2) previas: sobre o modelo (se houver); caso contrario, no proprio rig
if prev_fbx != "-":
    arm = A.load_rig(prev_fbx)
    clips = mod.build(A, arm)
A.setup_preview()
import mathutils
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
hmax = max((max(v.z for v in (o.matrix_world @ mathutils.Vector(c) for c in o.bound_box)) for o in meshes), default=2.0)
A.add_stage(hmax, fill=float(getattr(mod, "FILL", 1.3)), cam_dir=getattr(mod, "CAM", (0.62, -0.78, 0.22)))
pdir = os.path.join(out, "previas")
for c in clips:
    c["files"] = A.render_frames(arm, c["action"], c["preview"], os.path.join(pdir, c["action"].name), c["action"].name)
    for r in report:
        if r["name"] == c["action"].name:
            r["preview"] = [os.path.basename(p) for p in c["files"]]
json.dump(report, open(os.path.join(out, f"_clips_{group}.json"), "w"), indent=1, ensure_ascii=False)
print("DONE", group)
