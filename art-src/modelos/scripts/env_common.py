"""Kit de cenario da Cripta (tipo `prop`, estatico, sem esqueleto): especificacao de cada peca e utilitarios.

Convencoes: metros; Blender Z para cima; frente da peca = -Y (vira +Z na Unity pelo preset do graybox).
A malha alta da IA nasce normalizada num cubo de ~1,9 m (a IA nao sabe a escala): a etapa de geometria leva a malha
da pose da fonte (`src`: Z para cima, a imagem de entrada vista de -Y) ate a pose final com M = rotacao * escala
NAO uniforme minima (so onde a proporcao da IA diverge do kit) * translacao do pivo. A pintura roda no quadro `src`
(onde a imagem de entrada se alinha) e a AO no quadro final. Cada etapa e um processo novo: `env_run.py <id|all>`.
"""
import os, sys, json, math

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
SRC_ROOT = "D:/openclaude/_trabalho-claude/modelos3d/cenario"
OUT_ROOT = "D:/openclaude/_trabalho-claude/modelos3d/cenario_final"
WORK_ROOT = OUT_ROOT + "/work"
BLENDER = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
VENV_PY = os.environ.get("MDL_VENV_PY", r"D:\openclaude\_ferramentas\TripoSG\.venv\Scripts\python.exe")
TMPDIR = r"D:\openclaude\_trabalho-claude\tmp"
GRAYBOX_SCRIPTS = os.path.normpath(HERE + "/../../graybox/scripts").replace("\\", "/")

# dims = (largura X, profundidade Y, altura Z) finais em metros; None = fator uniforme dos eixos dados.
# pivot: floor_top (centro em XY, topo em z=0) | base_center | wall_outer (centro em X, face de fora -Y em y=0, base em z=0)
# kind: simple (kit na grade, 13..300 tris) | detail (props, ate ~1200)
P = lambda **k: k
PIECES = {
    # c01 pisos: 2 x 2 x 0,2, topo em z = 0
    "piso_liso": P(folha="c01_pisos", rot="floor", dims=(2, 2, .2), pivot="floor_top", tris=220, kind="simple", ao_dist=.08, collider="floor"),
    "piso_quebrado": P(folha="c01_pisos", rot="floor", dims=(2, 2, .2), pivot="floor_top", tris=290, kind="simple", ao_dist=.08, collider="floor"),
    "piso_runa": P(folha="c01_pisos", rot="floor", dims=(2, 2, .2), pivot="floor_top", tris=220, kind="simple", ao_dist=.08, collider="floor"),
    # c02 paredes 2 x 0,6 x 3; canto 1 x 1 x 3
    "parede_reta": P(folha="c02_paredes", dims=(2, .6, 3), pivot="wall_outer", tris=250, kind="simple", ao_dist=.15, collider="box"),
    "parede_canto_a": P(folha="c02_paredes", dims=(1, 1, 3), pivot="base_center", auto_yaw=True, tris=290, kind="simple", ao_dist=.15, collider="box"),
    "parede_ruina": P(folha="c02_paredes", dims=(2, .9, 2.4), pivot="wall_outer", tris=800, kind="detail", ao_dist=.2, collider="box"),
    # c03
    "arco_ruina": P(folha="c03_pilar_arco", dims=(3.2, .6, 3), pivot="base_center", tris=300, kind="simple", ao_dist=.2,
                    collider=[[-1.3, 0, 1.5, .6, .6, 3], [1.3, 0, 1.5, .6, .6, 3]]),
    "pilar_inteiro": P(folha="c03_pilar_arco", dims=(1.2, 1.2, 4), pivot="base_center", tris=300, kind="simple", ao_dist=.15, collider="box"),
    "pilar_quebrado": P(folha="c03_pilar_arco", dims=(1.6, 1.6, 2.8), pivot="base_center", tris=800, kind="detail", ao_dist=.2, collider="box"),
    # c04
    "escada": P(folha="c04_escada_portal", dims=(2, 2, 1), pivot="base_center", tris=300, kind="simple", ao_dist=.15, collider="ramp"),
    "portal_aberto": P(folha="c04_escada_portal", dims=(2.4, .6, 3.6), pivot="base_center", tris=1000, kind="detail", ao_dist=.15,
                       collider=[[-1.0, 0, 1.8, .4, .6, 3.6], [1.0, 0, 1.8, .4, .6, 3.6]]),
    "portal_porta": P(folha="c04_escada_portal", dims=(2.4, .6, 3.6), pivot="base_center", tris=1000, kind="detail", ao_dist=.15, collider="box"),
    # c05 decoracao
    "braseiro": P(folha="c05_decoracao", dims=(1.3, 1.3, 1.5), pivot="base_center", tris=1000, kind="detail", ao_dist=.1, emission="fire", collider="box"),
    "estandarte": P(folha="c05_decoracao", dims=(None, None, 2.8), pivot="base_center", tris=700, kind="detail", ao_dist=.1, tint="cloth", collider="none"),
    "ossos": P(folha="c05_decoracao", dims=(1.2, None, None), pivot="base_center", tris=900, kind="detail", ao_dist=.08, collider="none"),
    "sarcofago_aberto": P(folha="c05_decoracao", dims=(2, 1.3, 1), pivot="base_center", tris=1100, kind="detail", ao_dist=.1, collider="box"),
    "sarcofago_fechado": P(folha="c05_decoracao", dims=(2, 1, 1), pivot="base_center", tris=800, kind="detail", ao_dist=.1, collider="box"),
    "velas": P(folha="c05_decoracao", dims=(None, None, .6), pivot="base_center", tris=700, kind="detail", ao_dist=.06, emission="fire", collider="none"),
    # c06 entulho e abismo
    "abismo_bordo": P(folha="c06_entulho_abismo", dims=(2, None, None), pivot="base_center", tris=300, kind="simple", ao_dist=.1, collider="box"),
    "bloco_a": P(folha="c06_entulho_abismo", dims=(None, None, .9), pivot="base_center", tris=450, kind="detail", ao_dist=.12, collider="box"),
    "bloco_c": P(folha="c06_entulho_abismo", dims=(None, None, .8), pivot="base_center", tris=450, kind="detail", ao_dist=.12, collider="box"),
    "ruina_grande": P(folha="c06_entulho_abismo", dims=(2.2, None, None), pivot="base_center", tris=1200, kind="detail", ao_dist=.15, collider="box"),
    # refeitos proceduralmente (geometria da IA recusada): superelipsoide com ruido, pintura pela imagem da propria peca
    "bloco_b": P(folha="c06_entulho_abismo", proc=dict(dims=(1.1, 1.0, .65), p=3.0, noise=.10, k=5, seed=11), pivot="base_center", tris=300, kind="detail", ao_dist=.12, collider="box"),
    "bloco_d": P(folha="c06_entulho_abismo", proc=dict(dims=(.8, .9, 1.4), p=3.0, noise=.10, k=5, seed=7), pivot="base_center", tris=300, kind="detail", ao_dist=.12, collider="box"),
    "pedra_e": P(folha="c06_entulho_abismo", proc=dict(dims=(.8, .55, .4), p=2.2, noise=.14, k=4, seed=3), pivot="base_center", tris=190, kind="simple", ao_dist=.08, collider="none"),
    "pedra_f": P(folha="c06_entulho_abismo", proc=dict(dims=(1.0, .6, .25), p=2.2, noise=.14, k=4, seed=5), pivot="base_center", tris=190, kind="simple", ao_dist=.08, collider="none"),
}
ORDER = list(PIECES)


def cfg_for(pid):
    c = dict(PIECES[pid]); c["id"] = pid
    c["asset"] = "SM_Cripta_" + "".join(w.capitalize() for w in pid.split("_"))
    c["glb"] = f"{SRC_ROOT}/{c['folha']}/{pid}/{pid}.glb"
    c["entrada"] = f"{SRC_ROOT}/{c['folha']}/{pid}/{pid}_entrada_rgba.png"
    c["work"] = f"{WORK_ROOT}/{pid}"
    c["tex"] = 512; c["mask_tex"] = 256
    os.makedirs(c["work"], exist_ok=True)
    return c


def load_cfg(argv=None):
    argv = sys.argv if argv is None else argv
    return cfg_for(argv[argv.index("--") + 1] if "--" in argv else argv[1])


def wpath(c, name): return f"{c['work']}/{name}"


def save_json(path, data):
    def conv(o):
        if hasattr(o, "item"): return o.item()
        if hasattr(o, "tolist"): return o.tolist()
        raise TypeError(type(o))
    json.dump(data, open(path, "w", encoding="utf-8"), indent=1, default=conv)


def load_json(path, default=None):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def import_graybox():
    os.environ.setdefault("GB_ROOT", os.environ.get("TEMP", TMPDIR).replace("\\", "/") + "/gb_root")
    if GRAYBOX_SCRIPTS not in sys.path: sys.path.insert(0, GRAYBOX_SCRIPTS)
    import gb_lib
    return gb_lib


def wait_free_virtual(gb, timeout_s=7200):
    """Espera ter gb GB de memoria virtual (commit) livre (Windows), como o pipeline de personagens."""
    import ctypes, time
    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong) for n in ("totPhys", "availPhys", "totPage", "availPage", "totVirt", "availVirt", "ext")]
    t0 = time.time()
    while True:
        m = MS(); m.dwLength = ctypes.sizeof(MS)
        try: ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        except Exception: return None
        free = m.availPage / 2**30
        if free >= gb or time.time() - t0 > timeout_s: return free
        print(f"aguardando memoria virtual livre {free:.1f} GB < {gb} GB", flush=True); time.sleep(20)
