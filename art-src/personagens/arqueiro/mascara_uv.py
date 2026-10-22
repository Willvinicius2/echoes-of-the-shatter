"""Gera mascara_osso_uv.json: triangulos UV das regioes que devem virar osso claro (placas do cano das botas; as luvas continuam em couro).
Rodar uma vez (ou ao mudar o corte): blender -b -P mascara_uv.py. Usa os FBX da fonte (UV iguais as dos GLBs)."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import _comum as c

REGRAS = {  # fbx: funcao(centro da face em coords do FBX/Blender, Z-up) -> bool
    "SK_Archer_Feet_Starter.fbx": lambda p: p.z > 0.125,        # cano da bota
}
saida = {}
for fbx, regra in REGRAS.items():
    c.limpar(); c.importar(f"{c.FINAL}/{fbx}")
    m = next(o for o in bpy.data.objects if o.type == "MESH")
    uv = m.data.uv_layers.active.data
    tris = []
    for p in m.data.polygons:
        ctr = m.matrix_world @ p.center
        if regra(ctr):
            co = [tuple(uv[i].uv) for i in p.loop_indices]
            for k in range(1, len(co) - 1):
                tris.append([co[0], co[k], co[k + 1]])
    saida[fbx] = tris
    print(fbx, len(tris), "tris UV")
json.dump(saida, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mascara_osso_uv.json"), "w"))
