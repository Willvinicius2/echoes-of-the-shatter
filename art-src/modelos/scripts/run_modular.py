"""Roda o modo modular (corte do heroi vestido): python run_modular.py mod_warrior_cut  (um Blender por vez).
Pre-requisitos: heroi vestido pronto (final/SK_<Heroi>.blend) e corpo base com game_uv.blend (chars/mod_guerreiro_body)."""
import subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
env = dict(os.environ, TEMP=r"D:\openclaude\_trabalho-claude\tmp", TMP=r"D:\openclaude\_trabalho-claude\tmp")
for s in ("m_cut.py", "m_body.py", "m_export.py", "m_previews.py", "verify_modular.py"):
    print("==", s, flush=True)
    r = subprocess.run([B, "-b", "--factory-startup", "--python-exit-code", "1", "-P", os.path.join(HERE, s), "--", sys.argv[1]], env=env,
                       capture_output=True, text=True)
    print("\n".join(l for l in r.stdout.splitlines() if l.startswith(("MCUT", "MBODY", "MEXP", "MPREV", "VMOD", "  ")))[:1500])
    if r.returncode:
        raise SystemExit(f"{s} falhou")
