"""Roda o acabamento do kit de cenario: python env_run.py <peca|all> [--from a|b|c|d|e] [--only x]
Um processo por vez (Blender ou Python do venv), TEMP/TMP em D:, espera 4 GB de memoria virtual livre antes de cada etapa."""
import os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_common import *

STAGES = [("a", "env_a_import.py", "blender"), ("b", "env_b_geometry.py", "venv"), ("c", "env_c_uv_ao.py", "blender"),
          ("d", "env_d_paint.py", "venv"), ("e", "env_e_export.py", "blender")]


def run_piece(pid, start=None, only=None):
    env = dict(os.environ, TEMP=TMPDIR, TMP=TMPDIR)
    os.makedirs(TMPDIR, exist_ok=True)
    started = start is None
    for sid, script, how in STAGES:
        if sid == start: started = True
        if not started or (only and sid != only): continue
        path = os.path.join(HERE, script)
        cmd = ([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P", path, "--", pid] if how == "blender" else [VENV_PY, "-I", path, pid])
        wait_free_virtual(4.0)
        t = time.time()
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        out = (r.stdout + r.stderr).splitlines()
        keep = [l for l in out if l.startswith(("EA", "EB", "EC", "ED", "EE", "ECC", "componentes", "jogo", "silhueta", "pintado", "Traceback", "Error", "  File")) or "rror" in l]
        print(f"[{pid}:{sid}] {round(time.time() - t)} s cod {r.returncode} | " + " | ".join(keep[-5:]), flush=True)
        if r.returncode:
            print("\n".join(out[-15:])); return False
    return True


if __name__ == "__main__":
    a = sys.argv[1:]
    ids = ORDER if a[0] == "all" else a[0].split(",")
    start = a[a.index("--from") + 1] if "--from" in a else None
    only = a[a.index("--only") + 1] if "--only" in a else None
    bad = [p for p in ids if not run_piece(p, start, only)]
    print("falhas:", bad)
