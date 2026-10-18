"""Roda o env_bevel_kit.py peca por peca (um processo do Blender por vez, TEMP em D:, espera 3 GB de memoria virtual livre (limite do dono: 2,5 GB)).
Uso: python env_bevel_run.py <Peca> [<Peca> ...] | all       (ex.: python env_bevel_run.py ParedeReta)
Entrada: kit de origem (D:/openclaude/_trabalho-claude/modelos3d/cenario_final), que nunca e alterado.
Saida:   art-src/modelos/cenario_chanfro/SM_Cripta_<Peca>.fbx; o EnvironmentKit.Import() prefere essa peca a de origem.
Largura por familia (spec_cenario.md): 4 cm em bloco de parede, pilar e prop de pedra; 6 cm no coroamento (parede reta, canto e ruina)."""
import os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_common import BLENDER, TMPDIR, wait_free_virtual

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "D:/openclaude/_trabalho-claude/modelos3d/cenario_final"
OUT = os.path.normpath(os.path.join(HERE, "..", "cenario_chanfro"))
WIDTH = {
    "ParedeReta": 0.06, "ParedeCantoA": 0.06, "ParedeRuina": 0.05, "ArcoRuina": 0.04, "RuinaGrande": 0.05, "AbismoBordo": 0.04,
    "PilarInteiro": 0.04, "PilarQuebrado": 0.05, "BlocoA": 0.04, "BlocoB": 0.04, "BlocoC": 0.04, "BlocoD": 0.04,
    "SarcofagoAberto": 0.04, "SarcofagoFechado": 0.04, "Escada": 0.04, "PortalAberto": 0.04, "PortalPorta": 0.04,
    "PedraE": 0.04, "PedraF": 0.04, "Ossos": 0.02,
}
# Ruinas e pedras soltas: todas as faces suaves (media ponderada por area e angulo), para nao parecerem facetadas.
SMOOTH_ALL = {"ParedeRuina", "ArcoRuina", "RuinaGrande", "PilarQuebrado", "PedraE", "PedraF", "Ossos"}

def run(name):
    src = f"{SRC}/SM_Cripta_{name}.fbx"
    dst = f"{OUT}/SM_Cripta_{name}.fbx"
    os.makedirs(OUT, exist_ok=True)
    env = dict(os.environ, TEMP=TMPDIR, TMP=TMPDIR)
    wait_free_virtual(3.0)
    t = time.time()
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P", os.path.join(HERE, "env_bevel_kit.py"), "--",
                        src, dst, "--width", str(WIDTH[name]), "--segments", "3", "--angle", "35"] + (["--smooth-all"] if name in SMOOTH_ALL else []), env=env, capture_output=True, text=True)
    out = (r.stdout + r.stderr).splitlines()
    print(f"[{name}] {round(time.time() - t)} s cod {r.returncode} | " + " | ".join(l for l in out if "bevel" in l or "gravado" in l or "rror" in l or "Traceback" in l), flush=True)
    return r.returncode == 0

if __name__ == "__main__":
    names = list(WIDTH) if sys.argv[1:] == ["all"] else sys.argv[1:]
    ok = all([run(n) for n in names])
    sys.exit(0 if ok else 1)
