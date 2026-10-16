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
