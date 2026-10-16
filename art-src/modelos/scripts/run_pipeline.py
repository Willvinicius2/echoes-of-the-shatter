"""Roda o pipeline de acabamento de um personagem ou peca, cada etapa num processo novo.

Uso: python run_pipeline.py m01_guerreiro [--from s5] [--only s7] [--skip s9]
Blender 5.1 em -b; pymeshlab e a pintura rodam no Python do venv do TripoSG (numpy, scipy, cv2, pymeshlab).
TEMP e TMP ficam em D: (o C: esta cheio). Os parametros ficam em chars/<id>.json.
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
VENV_PY = os.environ.get("MDL_VENV_PY", r"D:\openclaude\_ferramentas\TripoSG\.venv\Scripts\python.exe")
TMPDIR = os.environ.get("MDL_TMP", r"D:\openclaude\_trabalho-claude\tmp")

STAGES = [  # (id, script, interprete)
    ("s1", "s1_prepare.py", "blender"),      # limpa e normaliza a malha alta
    ("s2", "s2_decimate.py", "venv"),        # malha de jogo (pymeshlab)
    ("s3", "s3_game_prep.py", "blender"),    # normais, sombreamento
    ("s4", "s4_rig.py", "blender"),          # esqueleto por marcos + pesos
    ("s5", "s5_uv.py", "blender"),           # UV 1024 por regiao
    ("s6", "s6_bake.py", "blender"),         # AO e cavidade da malha alta
    ("s7a", "s7a_export_geo.py", "blender"), # geometria por texel
    ("s7", "s7_paint.py", "venv"),           # pintura pela folha
    ("s8", "s8_export.py", "blender"),       # material, pose de teste, .blend e .fbx
    ("s9", "s9_previews.py", "blender"),     # previas Eevee
    ("v", "verify_modelo.py", "blender"),    # conferencia do FBX
]


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    char = args[0]
    start = args[args.index("--from") + 1] if "--from" in args else None
    only = args[args.index("--only") + 1] if "--only" in args else None
    skip = {args[i + 1] for i, a in enumerate(args) if a == "--skip"}
    env = dict(os.environ, TEMP=TMPDIR, TMP=TMPDIR)
    os.makedirs(TMPDIR, exist_ok=True)
    started = start is None
    for sid, script, how in STAGES:
        if sid == start:
            started = True
        if not started or (only and sid != only) or sid in skip:
            continue
        path = os.path.join(HERE, script)
        cmd = ([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P", path, "--", char] if how == "blender"
               else [VENV_PY, "-I", path, char])
        t = time.time()
        print(f"== {sid} {script}", flush=True)
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        lines = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith(("S", "VERIFY", "{", "jogo", "Traceback", "Error", "  File"))
                 or "rror" in l]
        print("\n".join(lines[-12:]))
        print(f"   {round(time.time() - t)} s, codigo {r.returncode}", flush=True)
        if r.returncode:
            raise SystemExit(f"etapa {sid} falhou")


if __name__ == "__main__":
    main()
