#!/usr/bin/env python3
"""Hook Stop do Claude Code: não deixa a sessão terminar com commit que ainda não foi para o GitHub.

Lê o JSON do hook na entrada padrão (usa "cwd" e "stop_hook_active"). Se a branch atual tem
commits que não estão em nenhuma branch do GitHub, devolve {"decision": "block"} com o comando
de push. Na segunda tentativa seguida (stop_hook_active) só avisa, para não prender a sessão
quando o push falha. Alterações sem commit não bloqueiam: podem estar esperando o ok do dono.
Só biblioteca padrão.
"""
import json
import subprocess
import sys


def git(cwd: str, *args: str) -> tuple:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout.strip()


def main() -> None:
    try:
        entrada = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        entrada = {}
    cwd = entrada.get("cwd") or "."
    ok, branch = git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    if ok != 0 or branch in ("", "HEAD"):
        return  # fora de um repositório ou HEAD destacado
    tem_upstream, upstream = git(cwd, "rev-parse", "--abbrev-ref", "@{u}")
    if tem_upstream == 0:
        _, n = git(cwd, "rev-list", "--count", "@{u}..HEAD")
        comando = "git push"
    else:
        _, n = git(cwd, "rev-list", "--count", "HEAD", "--not", "--remotes")
        comando = f"git push -u origin {branch}"
    faltam = int(n or 0)
    if faltam == 0:
        return
    texto = (f"A branch {branch} tem {faltam} commit(s) que ainda não estão no GitHub. "
             f"Regra do CLAUDE.md (seção Git e GitHub): rode `{comando}` agora e confira o resultado.")
    if entrada.get("stop_hook_active"):
        print(json.dumps({"systemMessage": texto + " O push anterior não resolveu; confira a rede ou o acesso."}))
    else:
        print(json.dumps({"decision": "block", "reason": texto}))


if __name__ == "__main__":
    main()
