"""Pos-processo do GLB: o exportador do Blender 5.1 grava alphaMode BLEND nas penas; troca por MASK (alphaCutoff 0.5) e
confere um unico no raiz. uso: python aljava_v4_glbfix.py <in.glb> <out.glb>"""
import json, struct, sys
f = open(sys.argv[1], "rb").read()
n = struct.unpack("<I", f[12:16])[0]; j = json.loads(f[20:20 + n]); rest = f[20 + n:]
for m in j["materials"]:
    if m["name"] == "M_ArcherDark_Arrows": m["alphaMode"] = "MASK"; m["alphaCutoff"] = 0.5; m["doubleSided"] = True
raw = json.dumps(j, separators=(",", ":")).encode(); raw += b" " * ((4 - len(raw) % 4) % 4)
out = f[:12] + struct.pack("<I", len(raw)) + b"JSON" + raw + rest
out = out[:8] + struct.pack("<I", len(out)) + out[12:]
open(sys.argv[2], "wb").write(out)
roots = [nd["name"] for nd in j["nodes"] if "name" in nd and nd["name"] == "SM_ArcherDark_Quiver"]
print("fix ok, scenes roots", j["scenes"][0]["nodes"], roots)
