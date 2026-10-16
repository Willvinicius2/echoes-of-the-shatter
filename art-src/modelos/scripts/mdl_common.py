"""Utilitarios comuns do pipeline de acabamento de personagens (art-src/modelos/scripts).

Cada etapa roda num processo novo: Blender (-b -P etapa.py -- config.json) ou Python com pymeshlab.
Os parametros por personagem ficam em chars/<id>.json; os intermediarios em work_dir; as saidas em final_dir.
Convencoes do projeto: metros, personagem de frente para -Y no Blender (+Z na Unity), pes em z = 0.
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
GRAYBOX_SCRIPTS = os.path.normpath(HERE + "/../../graybox/scripts").replace("\\", "/")


def load_cfg(argv=None):
    argv = sys.argv if argv is None else argv
    path = argv[argv.index("--") + 1] if "--" in argv else argv[1]
    if not os.path.isabs(path) and not os.path.exists(path):
        path = f"{HERE}/chars/{path}.json"
    cfg = json.load(open(path, encoding="utf-8"))
    cfg["_cfg_path"] = path
    cfg.update(json.loads(os.environ.get("MDL_OVERRIDE", "{}")))   # ajuste pontual sem editar o json
    cfg.setdefault("kind", "humanoid")          # humanoid | quadruped | static (arma)
    cfg.setdefault("tex_size", 1024)
    cfg.setdefault("size_scale", cfg["body_height_m"] / 1.5)   # distancias em metros foram afinadas para o heroi de 1,50 m
    for k in ("work_dir", "final_dir"):
        os.makedirs(cfg[k], exist_ok=True)
    return cfg


def wpath(cfg, name):
    return f"{cfg['work_dir']}/{name}"


def fpath(cfg, name):
    return f"{cfg['final_dir']}/{name}"


def load_json(path, default=None):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def save_json(path, data):
    def conv(o):   # tipos do numpy
        if hasattr(o, "item"):
            return o.item()
        if hasattr(o, "tolist"):
            return o.tolist()
        raise TypeError(type(o))
    json.dump(data, open(path, "w", encoding="utf-8"), indent=1, default=conv)


def import_graybox():
    """Importa gb_lib/gb_rig (preset de exportacao FBX e esqueleto) sem criar pastas no repositorio."""
    os.environ.setdefault("GB_ROOT", os.environ.get("TEMP", "D:/openclaude/_trabalho-claude/tmp").replace("\\", "/") + "/gb_root")
    if GRAYBOX_SCRIPTS not in sys.path:
        sys.path.insert(0, GRAYBOX_SCRIPTS)
    import gb_lib, gb_rig
    return gb_lib, gb_rig


def wait_free_virtual(gb, timeout_s=3600):
    """Espera a memoria virtual livre (commit disponivel = FreeVirtualMemory do WMI) passar de gb GB (Windows)."""
    import ctypes, time
    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong) for n in ("totPhys", "availPhys", "totPage", "availPage", "totVirt", "availVirt", "ext")]
    t0 = time.time()
    while True:
        m = MS(); m.dwLength = ctypes.sizeof(MS)
        try:
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        except Exception:
            return
        free = (m.availPage & 0xFFFFFFFFFFFFFFFF) / 2**30
        if free >= gb or time.time() - t0 > timeout_s:
            return free
        print(f"aguardando memoria virtual livre {free:.1f} GB < {gb} GB", flush=True)
        time.sleep(20)
