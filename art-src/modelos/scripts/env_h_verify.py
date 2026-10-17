"""Verificacao (Blender): reimporta cada FBX SM_Cripta_* e confere eixos/escala (1 unidade = 1 m), caixa e pivo do kit,
triangulos (13..300 simples; ate ~1.200 detalhado), 1 material, UV em 0..1, texturas existentes e tamanho 512/256.
Grava OUT/verify_cenario.json e imprime uma linha por peca (VERIFY ok|FALHA)."""
import bpy, sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_common import *

res = {}
bad = 0
for pid in ORDER:
    c = cfg_for(pid); a = c["asset"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fbx = f"{OUT_ROOT}/{a}.fbx"
    if not os.path.exists(fbx):
        res[pid] = dict(erro="sem fbx"); bad += 1; print("VERIFY FALHA", pid, "sem fbx"); continue
    bpy.ops.import_scene.fbx(filepath=fbx)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    o = obs[0]; me = o.data
    v = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', v); v = (v.reshape(-1, 3) * np.array(o.scale)) if False else v.reshape(-1, 3)
    M = np.array(o.matrix_world); v = v @ M[:3, :3].T + M[:3, 3]
    lo, hi = v.min(0), v.max(0); dims = hi - lo
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    uv = np.empty(len(me.loops) * 2); me.uv_layers[0].data.foreach_get('uv', uv)
    tgt = np.array(c["dims"], float) if "proc" not in c else np.array(c["proc"]["dims"], float)
    chk = []
    for i in range(3):
        if c["dims"][i] if "proc" not in c else True:
            if abs(dims[i] - tgt[i]) > 0.02 * max(tgt[i], 0.2): chk.append(f"dim{'XYZ'[i]} {dims[i]:.3f} != {tgt[i]}")
    if c["pivot"] == "floor_top" and abs(hi[2]) > 0.01: chk.append(f"topo z={hi[2]:.3f}")
    if c["pivot"] != "floor_top" and abs(lo[2]) > 0.01: chk.append(f"base z={lo[2]:.3f}")
    if c["pivot"] == "wall_outer" and abs(lo[1]) > 0.01: chk.append(f"face de fora y={lo[1]:.3f}")
    if c["pivot"] != "wall_outer" and abs((lo[0] + hi[0]) / 2) > 0.02: chk.append("centro x")
    lim = 300 if c["kind"] == "simple" else 1250
    if not (13 <= tris <= lim): chk.append(f"tris {tris}")
    if len(me.materials) != 1: chk.append(f"materiais {len(me.materials)}")
    if uv.min() < -0.001 or uv.max() > 1.001: chk.append("uv fora de 0..1")
    tex = c["asset"][3:]
    for f_, sz in ((f"T_{tex}_BC.png", 512), (f"T_{tex}_M.png", 256)):
        p = f"{OUT_ROOT}/{f_}"
        if not os.path.exists(p): chk.append("falta " + f_)
        else:
            im = bpy.data.images.load(p)
            if tuple(im.size) != (sz, sz): chk.append(f"{f_} {tuple(im.size)}")
    ok = not chk; bad += (not ok)
    res[pid] = dict(asset=a, tris=tris, dims_blender=np.round(dims, 3).tolist(), lo=np.round(lo, 3).tolist(), hi=np.round(hi, 3).tolist(), problemas=chk)
    print("VERIFY", "ok" if ok else "FALHA", pid, tris, "tris", np.round(dims, 2).tolist(), chk)
save_json(f"{OUT_ROOT}/verify_cenario.json", res)
print("VERIFY resumo:", len(ORDER) - bad, "ok de", len(ORDER))
