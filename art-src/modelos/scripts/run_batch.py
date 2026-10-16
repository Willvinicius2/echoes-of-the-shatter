"""Roda varios personagens em sequencia (um processo do Blender por vez): python run_batch.py id1 id2 ... [--from sN]"""
import subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
extra = []
if "--from" in args:
    i = args.index("--from"); extra = args[i:i + 2]; args = args[:i] + args[i + 2:]
for c in args:
    r = subprocess.run([sys.executable, os.path.join(HERE, "run_pipeline.py"), c] + extra)
    print(f"#### {c}: codigo {r.returncode}", flush=True)
