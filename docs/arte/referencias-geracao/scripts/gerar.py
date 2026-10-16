import json, os, re, shutil, subprocess, sys, glob
from concurrent.futures import ThreadPoolExecutor

CODEX = os.path.expandvars(r"%LOCALAPPDATA%\OpenAI\Codex\bin\9614f1d9b40d9c4f\codex.exe")
PROMPTS = sys.argv[1]
OUT = sys.argv[2]
ONLY = set(sys.argv[3:])
GEN = os.path.expanduser(r"~\.codex\generated_images")
os.makedirs(OUT, exist_ok=True)
work = os.path.join(OUT, "_work")
os.makedirs(work, exist_ok=True)

def run(item):
    iid = item["id"]
    w, h = item["tamanho"].split("x")
    orient = "landscape" if int(w) > int(h) else ("portrait" if int(h) > int(w) else "square")
    msg = (
        f"Call your image generation tool exactly once to create one image ({item['tamanho']}, {orient}). "
        "Use the attached images only as style/quality references. Image prompt:\n\n"
        + item["prompt"]
        + "\n\nDo not run shell commands and do not write files. After the image is generated reply only: DONE"
    )
    args = [CODEX, "exec", "--skip-git-repo-check", "-s", "read-only",
            "-c", "model_reasoning_effort=low", "-C", work]
    for r in item["referencias"]:
        args += ["-i", r]
    args += ["--", msg]
    log = os.path.join(work, iid + ".log")
    with open(log, "w", encoding="utf-8") as f:
        p = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT, timeout=900)
    text = open(log, encoding="utf-8", errors="replace").read()
    m = re.search(r"session id:\s*([0-9a-f-]+)", text)
    if not m:
        return iid, "sem session id", p.returncode
    pngs = sorted(glob.glob(os.path.join(GEN, m.group(1), "*.png")), key=os.path.getmtime)
    if not pngs:
        return iid, "nenhuma imagem gerada", p.returncode
    for k, src in enumerate(pngs):
        dst = os.path.join(OUT, f"{iid}.png" if k == len(pngs) - 1 else f"{iid}_alt{k}.png")
        shutil.move(src, dst)  # o disco C está cheio: nada fica na pasta do Codex
    try:
        os.rmdir(os.path.join(GEN, m.group(1)))
    except OSError:
        pass
    return iid, f"ok ({len(pngs)} png)", p.returncode

items = json.load(open(PROMPTS, encoding="utf-8"))
if ONLY:
    items = [i for i in items if i["id"] in ONLY]
with ThreadPoolExecutor(4) as ex:
    for iid, status, rc in ex.map(run, items):
        print(iid, status, "rc=", rc, flush=True)
