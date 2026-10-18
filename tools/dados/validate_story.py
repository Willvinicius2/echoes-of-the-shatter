#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_story.py — valida as tabelas de história em Content/Data/Story/ (regiões, Ecos, missões, vereditos).

Só biblioteca padrão. O ShatterCore ainda não lê estas tabelas (ficam em subpasta, que o core ignora);
quando o core passar a carregá-las, elas sobem para a raiz com esquema em schemas/.
Uso: python3 tools/dados/validate_story.py [--data EchoesOfTheShatter/Content/Data]
Saída: 0 = ok, 1 = erro de dados.
"""
import argparse
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COLS = {
    "regions.csv": ["id", "order", "mapId", "generalId", "exorcizeVerdict", "devourVerdict"],
    "echoes.csv": ["id", "regionId", "kind", "revealsSkill", "minToReveal"],
    "quests.csv": ["id", "regionId", "giver", "objectiveType", "objectiveTarget", "objectiveCount", "requires", "reward"],
    "verdicts.csv": ["id", "regionId", "choice", "hungerDelta", "statBonusPct", "grantsRelic", "grantsSignature",
                     "regionState", "hubState", "lastWordsKey"],
}
PREFIX = {"regions.csv": "region.", "echoes.csv": "echo.", "quests.csv": "quest.", "verdicts.csv": "verdict."}
ENUMS = {
    ("echoes.csv", "kind"): {"weapon", "memory"},
    ("quests.csv", "objectiveType"): {"talk", "collect_echo", "reach_map_boss", "verdict"},
    ("verdicts.csv", "choice"): {"exorcise", "devour"},
    ("verdicts.csv", "regionState"): {"purified", "stain"},
}
HUNGER_MAX = 4


def rows(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        return rd.fieldnames or [], [dict(r, __line__=rd.line_num) for r in rd]


def ids(data, name):
    p = os.path.join(data, name)
    return {r["id"] for r in rows(p)[1]} if os.path.exists(p) else set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(ROOT, "EchoesOfTheShatter", "Content", "Data"))
    data = ap.parse_args().data
    sdir = os.path.join(data, "Story")
    errs = []

    def err(f, ln, msg):
        errs.append(f"{f}:{ln}: {msg}")

    loc = set()
    ld = os.path.join(data, "Loc")
    for f in sorted(os.listdir(ld)):
        if f.endswith(".csv"):
            loc |= {r["key"] for r in rows(os.path.join(ld, f))[1]}
    ext = {"maps": ids(data, "maps.csv"), "enemies": ids(data, "enemies.csv"), "skills": ids(data, "skills.csv")}
    t = {}
    for name, cols in COLS.items():
        p = os.path.join(sdir, name)
        if not os.path.exists(p):
            err(name, 0, "tabela ausente")
            continue
        head, rs = rows(p)
        if head != cols:
            err(name, 1, f"cabeçalho esperado {','.join(cols)}")
            continue
        seen = set()
        for r in rs:
            ln = r["__line__"]
            if not r["id"].startswith(PREFIX[name]):
                err(name, ln, f"id '{r['id']}' deve começar com {PREFIX[name]}")
            if r["id"] in seen:
                err(name, ln, f"id '{r['id']}' repetido")
            seen.add(r["id"])
            for (tn, col), allowed in ENUMS.items():
                if tn == name and r[col] not in allowed:
                    err(name, ln, f"{col}='{r[col]}' fora de {sorted(allowed)}")
            if f"{r['id']}.name" not in loc:
                err(name, ln, f"falta chave de localização '{r['id']}.name'")
        t[name] = rs
    if errs:
        return finish(errs)
    regions = {r["id"] for r in t["regions.csv"]}
    verdicts = {r["id"] for r in t["verdicts.csv"]}
    quests = {r["id"] for r in t["quests.csv"]}
    for r in t["regions.csv"]:
        ln = r["__line__"]
        if r["mapId"] not in ext["maps"]:
            err("regions.csv", ln, f"mapId '{r['mapId']}' não existe em maps.csv")
        if r["generalId"] not in ext["enemies"]:
            err("regions.csv", ln, f"generalId '{r['generalId']}' não existe em enemies.csv")
        for col in ("exorcizeVerdict", "devourVerdict"):
            if r[col] not in verdicts:
                err("regions.csv", ln, f"{col} '{r[col]}' não existe em verdicts.csv")
    for r in t["echoes.csv"]:
        ln = r["__line__"]
        if r["regionId"] not in regions:
            err("echoes.csv", ln, f"regionId '{r['regionId']}' desconhecido")
        if r["revealsSkill"] not in ext["skills"]:
            err("echoes.csv", ln, f"revealsSkill '{r['revealsSkill']}' não existe em skills.csv")
        if not r["minToReveal"].isdigit() or int(r["minToReveal"]) < 1:
            err("echoes.csv", ln, "minToReveal deve ser inteiro >= 1")
    n_echoes = {}
    for r in t["echoes.csv"]:
        n_echoes[r["regionId"]] = n_echoes.get(r["regionId"], 0) + 1
    for r in t["quests.csv"]:
        ln = r["__line__"]
        if r["regionId"] not in regions:
            err("quests.csv", ln, f"regionId '{r['regionId']}' desconhecido")
        if r["requires"] and r["requires"] not in quests:
            err("quests.csv", ln, f"requires '{r['requires']}' desconhecida")
        if not r["objectiveCount"].isdigit() or int(r["objectiveCount"]) < 1:
            err("quests.csv", ln, "objectiveCount deve ser inteiro >= 1")
        elif r["objectiveType"] == "collect_echo" and int(r["objectiveCount"]) > n_echoes.get(r["regionId"], 0):
            err("quests.csv", ln, "objectiveCount maior que os Ecos da região")
        if r["objectiveType"] == "reach_map_boss" and r["objectiveTarget"] not in ext["maps"]:
            err("quests.csv", ln, f"objectiveTarget '{r['objectiveTarget']}' não é mapa")
        if r["giver"] and f"{r['giver']}.name" not in loc:
            err("quests.csv", ln, f"giver '{r['giver']}' sem nome em Loc")
    for r in t["verdicts.csv"]:
        ln = r["__line__"]
        if r["regionId"] not in regions:
            err("verdicts.csv", ln, f"regionId '{r['regionId']}' desconhecido")
        try:
            h, b = int(r["hungerDelta"]), int(r["statBonusPct"])
            if not 0 <= h <= HUNGER_MAX or b < 0:
                err("verdicts.csv", ln, f"hungerDelta 0..{HUNGER_MAX} e statBonusPct >= 0")
            if r["choice"] == "exorcise" and (h or b or r["grantsSignature"]):
                err("verdicts.csv", ln, "Exorcizar não dá Fome, bônus nem golpe-assinatura")
            if r["choice"] == "devour" and (h < 1 or r["grantsRelic"]):
                err("verdicts.csv", ln, "Devorar exige Fome >= 1 e não dá relíquia")
        except ValueError:
            err("verdicts.csv", ln, "hungerDelta e statBonusPct devem ser inteiros")
        for col in ("grantsRelic", "grantsSignature", "hubState"):
            if r[col] and f"{r[col]}.name" not in loc:
                err("verdicts.csv", ln, f"{col} '{r[col]}' sem nome em Loc")
        if r["lastWordsKey"] and r["lastWordsKey"] not in loc:
            err("verdicts.csv", ln, f"lastWordsKey '{r['lastWordsKey']}' não existe em Loc")
    return finish(errs)


def finish(errs):
    for e in errs:
        print("ERRO", e)
    print("story: ok" if not errs else f"story: {len(errs)} erro(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
