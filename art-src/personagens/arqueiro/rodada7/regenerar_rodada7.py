#!/usr/bin/env python3
"""Regenera os GLBs polidos do Arqueiro (rodada 7: Capuz, Botas, Luvas, Peitoral) a partir do repositorio.

Onde fica:  art-src/personagens/arqueiro/rodada7/regenerar_rodada7.py
Escreve em: godot/art/models/personagens/arqueiro/  (Arqueiro_Capuz/Botas/Luvas/Peitoral.glb + T_Arqueiro_{Botas,Luvas,Peitoral}_BC.png)

Idempotencia: na primeira execucao copia os GLBs/PNGs atuais da pasta de saida (estado pre-polida) para
_fonte_original/ aqui ao lado (com .gitignore) e dali em diante SEMPRE le dessa copia. Pode rodar quantas vezes quiser.
Para recomecar do zero, apague _fonte_original/ (e restaure os GLBs originais do Git antes).

Como rodar (qualquer um):
  1) Python com o modulo bpy (pip install bpy) + numpy + Pillow:
         python regenerar_rodada7.py
  2) Blender (o Pillow nao existe no Python do Blender, entao o Python do sistema com numpy+Pillow e usado nas texturas):
         blender -b --factory-startup -P regenerar_rodada7.py
         blender -b --factory-startup -P regenerar_rodada7.py -- --python "C:/caminho/python.exe"
  3) Python do sistema (numpy+Pillow), achando o Blender sozinho (ou --blender "C:/.../blender.exe" / variavel BLENDER):
         python regenerar_rodada7.py
Opcoes: --so capuz,botas,luvas,peitoral  (so essas pecas)   --blender CAMINHO   --python CAMINHO
"""
import glob
import json
import os
import shutil
import struct
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", "..", "..", ".."))   # rodada7 -> arqueiro -> personagens -> art-src -> repo
SAIDA = os.path.join(RAIZ, "godot", "art", "models", "personagens", "arqueiro")
FONTE = os.path.join(AQUI, "_fonte_original")
TRAB = os.path.join(AQUI, "_trabalho")
PECAS = ["Capuz", "Botas", "Luvas", "Peitoral"]

# (peca, tipo, script relativo, env extra).  "bpy" = precisa do Blender/bpy; "py" = so numpy + Pillow.
PASSOS = [
    ("capuz", "bpy", "capuz/extract.py", {}),
    ("capuz", "py", "capuz/tex2.py", {}),
    ("capuz", "bpy", "capuz/build2.py", {}),
    ("botas", "py", "botas/src/textura_botas.py", {}),
    ("botas", "bpy", "botas/build_botas_v3.py", {}),
    ("luvas", "py", "luvas/luvas_tex.py", {}),
    ("luvas", "bpy", "luvas/build_luvas_glb.py", {}),
    ("peitoral", "bpy", "peitoral/gerar_peitoral2.py", {}),
    ("peitoral", "py", "peitoral/peitoral_textura2.py", {}),
]


def args_usuario():
    a = sys.argv[1:]
    if "--" in a:                      # blender -P script -- args
        a = a[a.index("--") + 1:]
    opc = {"so": None, "blender": None, "python": None}
    i = 0
    while i < len(a):
        if a[i] in ("--so", "--blender", "--python") and i + 1 < len(a):
            opc[a[i][2:]] = a[i + 1]
            i += 2
        else:
            i += 1
    return opc


def eh_blender():
    try:
        import bpy
        return os.path.basename(bpy.app.binary_path or "").lower().startswith("blender")
    except Exception:
        return False


def tem_modulo_bpy():
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def achar_blender(opc):
    for c in (opc["blender"], os.environ.get("BLENDER"), shutil.which("blender")):
        if c and os.path.exists(c):
            return c
    pads = []
    for base in (os.environ.get("ProgramFiles", "C:/Program Files"), "C:/Program Files", "D:/Program Files"):
        pads += glob.glob(os.path.join(base, "Blender Foundation", "Blender *", "blender.exe"))
    pads += glob.glob("/Applications/Blender.app/Contents/MacOS/Blender")
    return sorted(pads)[-1] if pads else None


def achar_python(opc):
    for c in (opc["python"], os.environ.get("PYTHON_SISTEMA")):
        if c and os.path.exists(c):
            return [c]
    for nome in ("python", "python3"):
        p = shutil.which(nome)
        if p:
            return [p]
    if shutil.which("py"):
        return ["py", "-3"]
    return None


def montar_comandos(opc):
    """Devolve (cmd_bpy(script), cmd_py(script)) conforme o ambiente em que o driver roda."""
    if eh_blender():                                    # blender -b -P regenerar_rodada7.py
        import bpy
        py = achar_python(opc)
        if not py:
            sys.exit("Python do sistema (com numpy e Pillow) nao encontrado: use -- --python CAMINHO")
        return (lambda s: [bpy.app.binary_path, "-b", "--factory-startup", "-P", s]), (lambda s: py + [s])
    if tem_modulo_bpy():                                # python com o modulo bpy
        return (lambda s: [sys.executable, s]), (lambda s: [sys.executable, s])
    bl = achar_blender(opc)                             # python do sistema + blender externo
    if not bl:
        sys.exit("Nem o modulo bpy nem o Blender foram encontrados: use --blender CAMINHO ou a variavel BLENDER")
    return (lambda s: [bl, "-b", "--factory-startup", "-P", s]), (lambda s: [sys.executable, s])


def preparar_fonte():
    """Primeira execucao: congela o estado atual do repo em _fonte_original/ (fora do git)."""
    marca = os.path.join(FONTE, ".pronto")
    if not os.path.exists(marca):
        faltam = [p for p in PECAS if not os.path.exists(os.path.join(SAIDA, f"Arqueiro_{p}.glb"))]
        if faltam:
            sys.exit(f"GLBs de origem nao encontrados em {SAIDA}: {faltam}")
        os.makedirs(FONTE, exist_ok=True)
        n = 0
        for f in sorted(os.listdir(SAIDA)):
            if f.lower().endswith((".glb", ".png")):
                shutil.copyfile(os.path.join(SAIDA, f), os.path.join(FONTE, f))
                n += 1
        with open(os.path.join(AQUI, ".gitignore"), "w", newline="\n") as g:
            g.write("_fonte_original/\n_trabalho/\n__pycache__/\n*.pyc\n")
        with open(marca, "w") as m:
            m.write("copia do estado original (pre-polida) do repositorio\n")
        print(f"[fonte] {n} arquivos copiados para {FONTE}")
    else:
        print(f"[fonte] usando a copia existente em {FONTE}")
    if not os.path.exists(os.path.join(AQUI, ".gitignore")):
        with open(os.path.join(AQUI, ".gitignore"), "w", newline="\n") as g:
            g.write("_fonte_original/\n_trabalho/\n__pycache__/\n*.pyc\n")


def rodar(cmd, env, nome):
    r = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=AQUI)
    saida = r.stdout.decode("utf-8", "replace")
    if r.returncode != 0 or "Traceback" in saida:
        print(saida)
        sys.exit(f"FALHOU: {nome} (codigo {r.returncode})")
    for ln in saida.splitlines():
        if any(k in ln for k in ("TRIS", "EXPORTADO", "TEXTURA", "DECIMADO")):
            print("   ", ln.strip())


def resumo_glb(caminho):
    b = open(caminho, "rb").read()
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + n])
    acc = j["accessors"]
    malhas = {}
    for m in j.get("meshes", []):
        t = 0
        for p in m["primitives"]:
            t += (acc[p["indices"]]["count"] // 3) if "indices" in p else acc[p["attributes"]["POSITION"]]["count"] // 3
        malhas[m["name"]] = t
    ossos = [x["name"] for x in j["nodes"] if x["name"] not in malhas and "mesh" not in x]
    return malhas, ossos, [i.get("uri", "<embutida>") for i in j.get("images", [])]


def main():
    opc = args_usuario()
    so = {s.strip().lower() for s in opc["so"].split(",")} if opc["so"] else None
    print(f"[raiz] {RAIZ}\n[saida] {SAIDA}")
    preparar_fonte()
    os.makedirs(TRAB, exist_ok=True)
    cmd_bpy, cmd_py = montar_comandos(opc)
    for peca, tipo, rel, extra in PASSOS:
        if so and peca not in so:
            continue
        env = dict(os.environ)
        env.update({"ARQ_FONTE_ORIG": FONTE, "ARQ_SAIDA": SAIDA, "ARQ_TRAB": os.path.join(TRAB, peca),
                    "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"})
        env.pop("OUT", None)
        env.update(extra)
        os.makedirs(env["ARQ_TRAB"], exist_ok=True)
        script = os.path.join(AQUI, *rel.split("/"))
        print(f"[{peca}] {rel}")
        rodar((cmd_bpy if tipo == "bpy" else cmd_py)(script), env, rel)
    print("\n[resultado]")
    for p in PECAS:
        if so and p.lower() not in so:
            continue
        g = os.path.join(SAIDA, f"Arqueiro_{p}.glb")
        if os.path.exists(g):
            malhas, ossos, imgs = resumo_glb(g)
            print(f"  Arqueiro_{p}.glb: malhas={malhas} ossos={len(ossos)} texturas={imgs}")
    print("Pronto. Abra o projeto no Godot para reimportar.")


if __name__ == "__main__":
    main()
