"""Verifica os GLBs do arqueiro lendo o JSON do glTF (python puro). Uso: python verificar_glb.py"""
import json, struct, glob, os, sys
args = [a for a in sys.argv[1:] if not a.startswith("--")]
pasta = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "godot", "art", "models", "personagens", "arqueiro")
for p in sorted(glob.glob(os.path.join(pasta, "Arqueiro_*.glb"))):
    b = open(p, "rb").read()
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + n])
    tris = 0; uv = False; lo = [9e9]*3; hi = [-9e9]*3
    for m in j["meshes"]:
        for pr in m["primitives"]:
            tris += j["accessors"][pr["indices"]]["count"] // 3
            uv |= "TEXCOORD_0" in pr["attributes"]
            a = j["accessors"][pr["attributes"]["POSITION"]]
            lo = [min(x, y) for x, y in zip(lo, a["min"])]; hi = [max(x, y) for x, y in zip(hi, a["max"])]
    skins = j.get("skins", [])
    bones = len(skins[0]["joints"]) if skins else 0
    nomes = [j["nodes"][i]["name"] for i in skins[0]["joints"]] if skins else []
    raiz_rot = [nd.get("rotation") for nd in j["nodes"] if nd.get("name") == "Rig_Humanoid_Chibi"]
    print(f"{os.path.basename(p)}: tris={tris} ossos={bones} materiais={[m['name'] for m in j['materials']]} uv={uv} "
          f"anim={len(j.get('animations', []))} imagens={len(j.get('images', []))} yMin={lo[1]:.3f} yMax={hi[1]:.3f} "
          f"x=[{lo[0]:.2f},{hi[0]:.2f}] z=[{lo[2]:.2f},{hi[2]:.2f}] rotArmature={raiz_rot}")
    if nomes and "--ossos" in sys.argv: print("   ", nomes)
