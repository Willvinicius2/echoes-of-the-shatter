"""Regera todo o graybox em ordem, cada etapa num processo novo (cada script comeca com a cena vazia).

Uso:
  python build_all.py                      # Python com o modulo bpy instalado (pip install bpy)
  blender -b -P build_all.py               # Blender instalado (Windows: blender.exe)
  python build_all.py --blender CAMINHO    # chama o Blender indicado para cada etapa
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = ["make_rig.py", "make_heroes.py", "make_enemies.py", "make_crypt_kit.py", "make_crypt_testroom.py",
         "verify_fbx.py"]


def runner():
    if "--blender" in sys.argv:
        return [sys.argv[sys.argv.index("--blender") + 1], "-b", "--factory-startup", "--python-exit-code", "1", "-P"]
    try:
        import bpy
        exe = bpy.app.binary_path
        if exe and os.path.basename(exe).lower().startswith("blender"):
            return [exe, "-b", "--factory-startup", "--python-exit-code", "1", "-P"]
    except ImportError:
        pass
    return [sys.executable]


if __name__ == "__main__":
    base = runner()
    for step in STEPS:
        print(f"== {step}", flush=True)
        r = subprocess.run(base + [os.path.join(HERE, step)], cwd=HERE)
        if r.returncode != 0:
            sys.exit(f"falhou: {step} (codigo {r.returncode})")
    print("== graybox regerado; relatorio de conferencia em previews/_fbx_verify_report.json")
