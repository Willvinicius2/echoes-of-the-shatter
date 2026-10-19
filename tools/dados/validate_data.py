#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_data.py — validador de dados do Echoes of the Shatter (Data Engineer).

Só biblioteca padrão do Python 3 (>= 3.8). Valida:
  * as tabelas CSV de conteúdo (Content/Data/*.csv) contra Content/Data/schemas/*.schema.json;
  * arquivos de save JSON contra schemas/save*.schema.json (+ SHA-256 do envelope).

Uso rápido (da raiz do repositório):
  python3 tools/dados/validate_data.py                         # valida EchoesOfTheShatter/Content/Data
  python3 tools/dados/validate_data.py --data ShatterCore/tests/data
  python3 tools/dados/validate_data.py --data X --expect-fail  # sucesso só se X tiver erro
  python3 tools/dados/validate_data.py --save slot_1.json --content EchoesOfTheShatter/Content/Data
  python3 tools/dados/validate_data.py --self-test             # Content/Data + todos os fixtures (CI)

Código de saída: 0 = ok; 1 = erro de dados; 2 = erro de uso/arquivo de esquema.
Esquema e convenções: docs/tecnico/06_dados.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DATA = os.path.join(ROOT, "EchoesOfTheShatter", "Content", "Data")
DEFAULT_SCHEMAS = os.path.join(DEFAULT_DATA, "schemas")
TEST_DATA = os.path.join(ROOT, "ShatterCore", "tests", "data")

SAVE_FORMAT_TAG = "echoes-of-the-shatter-save"
ID_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")
INT_RE = re.compile(r"^-?[0-9]+$")
NUM_RE = re.compile(r"^-?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?$")
DECIMAL_COMMA_HINT = re.compile(r"^-?[0-9]+$")
STACK_PREFIXES = ("currency.", "material.", "page.", "sigil.common.")
INT64_MIN, INT64_MAX = -(2 ** 63), 2 ** 63 - 1
UINT64_MAX = 2 ** 64 - 1


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------
class Report:
    def __init__(self, label: str):
        self.label = label
        self.errors: List[Tuple[str, int, str, str]] = []    # (arquivo, linha, código, mensagem)
        self.warnings: List[Tuple[str, int, str, str]] = []
        self.infos: List[str] = []

    def err(self, f: str, line: int, code: str, msg: str) -> None:
        self.errors.append((f, line, code, msg))

    def warn(self, f: str, line: int, code: str, msg: str) -> None:
        self.warnings.append((f, line, code, msg))

    def info(self, msg: str) -> None:
        self.infos.append(msg)

    @staticmethod
    def _loc(f: str, line: int) -> str:
        return f"{f}:{line}" if line > 0 else f

    def print(self, out=sys.stdout, quiet: bool = False) -> None:
        print(f"== {self.label}", file=out)
        if not quiet:
            for m in self.infos:
                print(f"   info   {m}", file=out)
        for f, l, c, m in self.warnings:
            print(f"   AVISO  {self._loc(f, l)} [{c}] {m}", file=out)
        for f, l, c, m in self.errors:
            print(f"   ERRO   {self._loc(f, l)} [{c}] {m}", file=out)
        status = "OK" if not self.errors else "FALHOU"
        print(f"   -> {status}: {len(self.errors)} erro(s), {len(self.warnings)} aviso(s)", file=out)

    @property
    def ok(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------------------
# Esquemas de tabela (formato próprio shatter-table-schema/1)
# ---------------------------------------------------------------------------
class SchemaError(Exception):
    pass


def load_table_schemas(schema_dir: str) -> Tuple[Dict[str, dict], Dict[str, List[str]]]:
    if not os.path.isdir(schema_dir):
        raise SchemaError(f"pasta de esquemas não encontrada: {schema_dir}")
    enums_path = os.path.join(schema_dir, "_enums.json")
    if not os.path.isfile(enums_path):
        raise SchemaError(f"faltando {enums_path}")
    with open(enums_path, encoding="utf-8") as fh:
        enums = json.load(fh)["enums"]
    schemas: Dict[str, dict] = {}
    for name in sorted(os.listdir(schema_dir)):
        if not name.endswith(".schema.json") or name.startswith("save"):
            continue
        with open(os.path.join(schema_dir, name), encoding="utf-8") as fh:
            s = json.load(fh)
        if s.get("format") != "shatter-table-schema/1":
            raise SchemaError(f"{name}: format inesperado")
        schemas[s["table"]] = s
    if not schemas:
        raise SchemaError("nenhum esquema de tabela encontrado")
    return schemas, enums


def enum_values(spec_values: Any, enums: Dict[str, List[str]]) -> List[str]:
    if isinstance(spec_values, str) and spec_values.startswith("@"):
        return enums[spec_values[1:]]
    return list(spec_values)


# ---------------------------------------------------------------------------
# Leitura de CSV (regras próprias: sem aspas, vírgula só como separador)
# ---------------------------------------------------------------------------
def read_csv_raw(path: str, fname: str, rep: Report) -> Optional[Tuple[List[str], List[Tuple[int, List[str]]]]]:
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        rep.err(fname, 1, "E_BOM", "arquivo começa com BOM UTF-8; salve como UTF-8 sem BOM")
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        rep.err(fname, 0, "E_ENCODING", f"não é UTF-8 válido (byte {e.start})")
        return None
    lines = text.split("\n")
    rows: List[Tuple[int, List[str]]] = []
    header: Optional[List[str]] = None
    for i, line in enumerate(lines, start=1):
        if line.endswith("\r"):
            line = line[:-1]
        if line.strip() == "":
            if i < len(lines):  # linha vazia no meio (a última após \n final é normal)
                rep.warn(fname, i, "W_BLANK", "linha vazia ignorada")
            continue
        if '"' in line:
            rep.err(fname, i, "E_QUOTE", "aspas não são permitidas nas tabelas do ContentDB (sem texto livre; textos vão em Loc/)")
            continue
        cells = line.split(",")
        if header is None:
            header = cells
            continue
        rows.append((i, cells))
    if header is None:
        rep.err(fname, 0, "E_EMPTY", "arquivo vazio (precisa ao menos da linha de cabeçalho)")
        return None
    return header, rows


# ---------------------------------------------------------------------------
# Conversão de células
# ---------------------------------------------------------------------------
class CellError(Exception):
    def __init__(self, code: str, msg: str):
        super().__init__(msg)
        self.code = code
        self.msg = msg


def parse_number(text: str, integer: bool) -> Any:
    if integer:
        if not INT_RE.match(text):
            if NUM_RE.match(text):
                raise CellError("E_TYPE", f"'{text}' deveria ser inteiro")
            raise CellError("E_TYPE", f"'{text}' não é inteiro")
        v = int(text)
        if v < INT64_MIN or v > INT64_MAX:
            raise CellError("E_RANGE", f"'{text}' fora de int64")
        return v
    if not NUM_RE.match(text):
        raise CellError("E_TYPE", f"'{text}' não é número (use ponto decimal, sem separador de milhar)")
    v = float(text)
    if math.isinf(v) or math.isnan(v):
        raise CellError("E_TYPE", f"'{text}' não é finito")
    return v


def parse_bool(text: str) -> bool:
    if text == "true":
        return True
    if text == "false":
        return False
    raise CellError("E_TYPE", f"'{text}' não é booleano (use true/false)")


def check_id(text: str, prefix: Optional[str] = None) -> str:
    if not ID_RE.match(text):
        raise CellError("E_ID", f"ID '{text}' inválido (minúsculas, [a-z0-9_], segmentos separados por ponto, >= 2 segmentos)")
    if prefix and not text.startswith(prefix):
        raise CellError("E_ID", f"ID '{text}' deveria começar com '{prefix}'")
    return text


def check_range(name: str, v: float, spec: dict) -> None:
    if "min" in spec and v < spec["min"]:
        raise CellError("E_RANGE", f"{v} < mínimo {spec['min']}")
    if "max" in spec and v > spec["max"]:
        raise CellError("E_RANGE", f"{v} > máximo {spec['max']}")
    if "minExclusive" in spec and not v > spec["minExclusive"]:
        raise CellError("E_RANGE", f"{v} deve ser > {spec['minExclusive']}")
    if "multipleOf" in spec:
        q = v / spec["multipleOf"]
        if abs(q - round(q)) > 1e-9:
            raise CellError("E_RANGE", f"{v} deve ser múltiplo de {spec['multipleOf']}")


def parse_tags(text: str, enums) -> List[str]:
    if text == "":
        return []
    out = []
    for t in text.split("|"):
        if t not in enums["tags"]:
            raise CellError("E_TAG", f"tag desconhecida '{t}' (válidas: {', '.join(enums['tags'])})")
        if t in out:
            raise CellError("E_TAG", f"tag repetida '{t}'")
        out.append(t)
    return out


def parse_mod(item: str, enums) -> dict:
    parts = item.split(":")
    if len(parts) not in (3, 4):
        raise CellError("E_MOD", f"modificador '{item}' deve ser stat:kind:valor[:tag+tag]")
    stat, kind, value = parts[0], parts[1], parts[2]
    if stat not in enums["stats"]:
        raise CellError("E_ENUM", f"stat desconhecido '{stat}' em '{item}'")
    if kind not in enums["modKinds"]:
        raise CellError("E_ENUM", f"tipo de modificador '{kind}' inválido em '{item}' (flat|increased|more)")
    v = parse_number(value, False)
    tags: List[str] = []
    if len(parts) == 4:
        tags = parse_tags(parts[3].replace("+", "|"), enums) if parts[3] else []
    return {"stat": stat, "kind": kind, "value": v, "requiredTags": tags}


def parse_cell(spec: dict, text: str, enums) -> Any:
    t = spec["type"]
    if t == "number":
        v = parse_number(text, False)
        check_range(spec["name"], v, spec)
        return v
    if t == "int":
        v = parse_number(text, True)
        check_range(spec["name"], v, spec)
        return v
    if t == "bool":
        return parse_bool(text)
    if t == "string":
        if "pattern" in spec and not re.match(spec["pattern"], text):
            raise CellError("E_FORMAT", f"'{text}' não segue {spec['pattern']}")
        return text
    if t == "id":
        return check_id(text, spec.get("prefix"))
    if t == "ref":
        return check_id(text)
    if t == "enum":
        vals = enum_values(spec["values"], enums)
        if text not in vals:
            raise CellError("E_ENUM", f"'{text}' não é valor válido (válidos: {', '.join(vals)})")
        return text
    if t == "tags":
        return parse_tags(text, enums)
    if t == "list":
        items = text.split("|") if text != "" else []
        out = []
        for it in items:
            if it == "":
                raise CellError("E_LIST", "item vazio na lista (dois '|' seguidos ou '|' nas pontas)")
            it_type = spec["itemType"]
            if it_type in ("id", "ref"):
                check_id(it, spec.get("prefix"))
            elif it_type == "enum":
                vals = enum_values(spec["values"], enums)
                if it not in vals:
                    raise CellError("E_ENUM", f"'{it}' não é valor válido (válidos: {', '.join(vals)})")
            if it in out and not spec.get("allowRepeat"):
                raise CellError("E_LIST", f"item repetido '{it}'")
            out.append(it)
        if "minItems" in spec and len(out) < spec["minItems"]:
            raise CellError("E_LIST", f"{len(out)} item(ns); mínimo {spec['minItems']}")
        if "maxItems" in spec and len(out) > spec["maxItems"]:
            raise CellError("E_LIST", f"{len(out)} item(ns); máximo {spec['maxItems']}")
        return out
    if t == "mods":
        return [parse_mod(it, enums) for it in text.split("|")] if text else []
    if t == "growths":
        out = []
        seen = set()
        for it in text.split("|") if text else []:
            p = it.split(":")
            if len(p) != 3:
                raise CellError("E_FORMAT", f"'{it}' deve ser stat:base:porNível")
            if p[0] not in enums["stats"]:
                raise CellError("E_ENUM", f"stat desconhecido '{p[0]}'")
            if p[0] in seen:
                raise CellError("E_LIST", f"stat repetido '{p[0]}'")
            seen.add(p[0])
            out.append({"stat": p[0], "base": parse_number(p[1], False), "perLevel": parse_number(p[2], False)})
        return out
    if t == "groups":
        out = []
        for it in text.split("|") if text else []:
            p = it.split(":")
            if len(p) != 4:
                raise CellError("E_FORMAT", f"grupo '{it}' deve ser enemyId:countMin:countMax:eliteChance")
            g = {"enemyId": check_id(p[0], "enemy."), "countMin": parse_number(p[1], True),
                 "countMax": parse_number(p[2], True), "eliteChance": parse_number(p[3], False)}
            if g["countMin"] < 1:
                raise CellError("E_RANGE", f"countMin {g['countMin']} < 1 em '{it}'")
            if g["countMin"] > g["countMax"]:
                raise CellError("E_MINMAX", f"countMin {g['countMin']} > countMax {g['countMax']} em '{it}'")
            if not 0.0 <= g["eliteChance"] <= 1.0:
                raise CellError("E_RANGE", f"eliteChance {g['eliteChance']} fora de [0,1] em '{it}'")
            out.append(g)
        return out
    raise SchemaError(f"tipo de coluna desconhecido: {t}")


# ---------------------------------------------------------------------------
# Tabelas
# ---------------------------------------------------------------------------
def load_key_value(path: str, fname: str, schema: dict, enums, rep: Report) -> Dict[str, Any]:
    raw = read_csv_raw(path, fname, rep)
    if raw is None:
        return {}
    header, rows = raw
    if header != ["key", "value"]:
        rep.err(fname, 1, "E_HEADER", f"cabeçalho deve ser exatamente 'key,value' (veio '{','.join(header)}')")
        return {}
    specs = {k["name"]: k for k in schema["keys"]}
    out: Dict[str, Any] = {}
    lines: Dict[str, int] = {}
    for line, cells in rows:
        if len(cells) != 2:
            hint = " — vírgula decimal? use ponto" if len(cells) == 3 and DECIMAL_COMMA_HINT.match(cells[2]) else ""
            rep.err(fname, line, "E_COLUMNS", f"esperava 2 colunas, veio {len(cells)}{hint}")
            continue
        k, v = cells
        if k != k.strip() or v != v.strip():
            rep.err(fname, line, "E_SPACE", "espaço nas pontas da célula")
            continue
        if k not in specs:
            rep.err(fname, line, "E_KEY", f"chave desconhecida '{k}'")
            continue
        if k in out:
            rep.err(fname, line, "E_DUP", f"chave '{k}' repetida (primeira na linha {lines[k]})")
            continue
        try:
            s = dict(specs[k])
            out[k] = parse_cell(s, v, enums)
            lines[k] = line
        except CellError as e:
            rep.err(fname, line, e.code, f"{k}: {e.msg}")
    for k in specs:
        if k not in out and not any(x[0] == fname and k in x[3] for x in rep.errors):
            rep.err(fname, 0, "E_KEY_MISSING", f"chave obrigatória ausente: '{k}'")
    out["__lines__"] = lines
    return out


def load_rows(path: str, fname: str, schema: dict, enums, rep: Report) -> List[dict]:
    raw = read_csv_raw(path, fname, rep)
    if raw is None:
        return []
    header, rows = raw
    cols = schema["columns"]
    expected = [c["name"] for c in cols]
    if header != expected:
        missing = [c for c in expected if c not in header]
        extra = [c for c in header if c not in expected]
        detail = []
        if missing:
            detail.append("faltando: " + ", ".join(missing))
        if extra:
            detail.append("sobrando: " + ", ".join(extra))
        if not missing and not extra:
            detail.append("ordem diferente")
        rep.err(fname, 1, "E_HEADER", "cabeçalho diferente do esquema (" + "; ".join(detail) + ")")
        return []
    out = []
    for line, cells in rows:
        if len(cells) != len(cols):
            hint = ""
            if len(cells) > len(cols):
                hint = " — vírgula decimal? números usam ponto (1.5), listas usam '|'"
            rep.err(fname, line, "E_COLUMNS", f"esperava {len(cols)} colunas, veio {len(cells)}{hint}")
            continue
        row: Dict[str, Any] = {"__line__": line}
        bad = False
        for spec, text in zip(cols, cells):
            name = spec["name"]
            if text != text.strip():
                rep.err(fname, line, "E_SPACE", f"{name}: espaço nas pontas da célula")
                bad = True
                continue
            if text == "":
                if spec.get("required"):
                    rep.err(fname, line, "E_REQUIRED", f"{name}: obrigatório")
                    bad = True
                    continue
                d = spec.get("default")
                if d is None:
                    d = [] if spec["type"] in ("list", "tags", "mods", "growths", "groups") else ""
                row[name] = d
                continue
            try:
                row[name] = parse_cell(spec, text, enums)
            except CellError as e:
                rep.err(fname, line, e.code, f"{name}: {e.msg}")
                bad = True
        if not bad:
            out.append(row)
    return out


class Content:
    def __init__(self):
        self.tables: Dict[str, List[dict]] = {}
        self.rules: Dict[str, Any] = {}
        self.meta: Dict[str, Any] = {}
        self.by_id: Dict[str, Dict[str, dict]] = {}
        self.data_dir: str = ""

    def ids(self, table: str) -> Dict[str, dict]:
        return self.by_id.get(table, {})


def validate_content(data_dir: str, schema_dir: str, rep: Report, check_loc: bool = True) -> Content:
    schemas, enums = load_table_schemas(schema_dir)
    c = Content()
    c.data_dir = data_dir
    if not os.path.isdir(data_dir):
        rep.err(data_dir, 0, "E_DIR", "pasta de dados não existe")
        return c
    present = {f for f in os.listdir(data_dir) if f.endswith(".csv")}
    for f in sorted(present - set(schemas)):
        rep.err(f, 0, "E_UNKNOWN_TABLE", "CSV sem esquema (o ContentDB não conhece esta tabela)")
    for table in sorted(schemas):
        if table not in present and not schemas[table].get("optional"):
            rep.err(table, 0, "E_MISSING_TABLE", "tabela obrigatória ausente (crie ao menos com o cabeçalho)")
    # 1) leitura e tipos
    for table, schema in sorted(schemas.items()):
        if table not in present:
            continue
        path = os.path.join(data_dir, table)
        if schema["kind"] == "key_value":
            kv = load_key_value(path, table, schema, enums, rep)
            if table == "rules.csv":
                c.rules = kv
            else:
                c.meta = kv
        else:
            c.tables[table] = load_rows(path, table, schema, enums, rep)
    # 2) chaves primárias
    all_ids: Dict[str, str] = {}
    for table, rows in c.tables.items():
        pk = schemas[table]["primaryKey"]
        if not pk:
            continue
        seen: Dict[Tuple, int] = {}
        idx: Dict[str, dict] = {}
        for r in rows:
            key = tuple(r[k] for k in pk)
            if key in seen:
                rep.err(table, r["__line__"], "E_DUP_ID", f"chave {'/'.join(map(str, key))} repetida (primeira na linha {seen[key]})")
                continue
            seen[key] = r["__line__"]
            if pk == ["id"]:
                idx[r["id"]] = r
                if r["id"] in all_ids and all_ids[r["id"]] != table:
                    rep.err(table, r["__line__"], "E_DUP_ID", f"ID '{r['id']}' já usado em {all_ids[r['id']]}")
                all_ids[r["id"]] = table
        c.by_id[table] = idx
    # 3) referências
    for table, rows in c.tables.items():
        for spec in schemas[table]["columns"]:
            ref = spec.get("ref")
            if not ref:
                continue
            target = c.ids(ref)
            for r in rows:
                vals = r[spec["name"]] if isinstance(r[spec["name"]], list) else [r[spec["name"]]]
                for v in vals:
                    if v and v not in target:
                        rep.err(table, r["__line__"], "E_FK", f"{spec['name']}: '{v}' não existe em {ref}")
    # 4) regras por tabela
    if c.rules:
        check_rules(c, rep)
    if c.meta:
        cv = c.meta.get("content_version")
        if isinstance(cv, int):
            rep.info(f"content_version = {cv}")
    run_checks(c, schemas, rep)
    # 5) localização
    if check_loc:
        check_localization(c, schemas, data_dir, rep)
    counts = ", ".join(f"{t}={len(r)}" for t, r in sorted(c.tables.items()))
    rep.info(f"linhas: {counts}")
    return c


def check_rules(c: Content, rep: Report) -> None:
    r = c.rules
    ln = r.get("__lines__", {})
    def g(k):
        return r.get(k)
    if g("min_expedition_hours") is not None and g("max_expedition_hours") is not None:
        if g("min_expedition_hours") > g("max_expedition_hours"):
            rep.err("rules.csv", ln.get("min_expedition_hours", 0), "E_MINMAX", "min_expedition_hours > max_expedition_hours")
    if g("max_expedition_hours") is not None and g("max_offline_hours") is not None:
        if g("max_expedition_hours") > g("max_offline_hours"):
            rep.warn("rules.csv", ln.get("max_expedition_hours", 0), "W_RULES", "max_expedition_hours > max_offline_hours: horas além do teto offline nunca são simuladas")
    v = [g("vigor_h1_4"), g("vigor_h5_8"), g("vigor_h9_12")]
    if None not in v and not (v[0] >= v[1] >= v[2]):
        rep.warn("rules.csv", ln.get("vigor_h5_8", 0), "W_RULES", "Vigor deveria ser não crescente por faixa (plano: 100/70/40%)")
    if g("sim_step") is not None and g("sim_step_fast") is not None and g("sim_step_fast") < g("sim_step"):
        rep.err("rules.csv", ln.get("sim_step_fast", 0), "E_RULES", "sim_step_fast < sim_step")
    if g("vigor_band_hours") is not None and g("max_expedition_hours") is not None:
        if g("vigor_band_hours") * 3 < g("max_expedition_hours"):
            rep.err("rules.csv", ln.get("vigor_band_hours", 0), "E_RULES", "3 faixas de Vigor não cobrem max_expedition_hours")
    if g("charges_per_hour") is not None and g("charges_max") is not None and g("max_expedition_hours") is not None:
        if g("charges_per_hour") * g("max_expedition_hours") > g("charges_max"):
            rep.warn("rules.csv", ln.get("charges_max", 0), "W_RULES", "charges_max não paga uma expedição de duração máxima")
    # Inventário e equipamento (docs/16 4.1 e 4.4)
    prices = [g("sell_price_normal"), g("sell_price_magic"), g("sell_price_rare"), g("sell_price_unique")]
    if None not in prices and not (prices[0] <= prices[1] <= prices[2] <= prices[3]):
        rep.warn("rules.csv", ln.get("sell_price_magic", 0), "W_RULES", "preço de venda deveria crescer com a raridade (Comum <= Mágico <= Raro <= Único)")
    if g("equip_slot_main_hand") is False:
        rep.err("rules.csv", ln.get("equip_slot_main_hand", 0), "E_RULES", "equip_slot_main_hand = false: o herói não poderia equipar arma")
    slots = ["main_hand", "off_hand", "head", "body", "hands", "feet", "amulet", "ring", "ring2", "belt", "legs"]
    enabled = {s: g("equip_slot_" + s) for s in slots}
    for base in c.tables.get("item_bases.csv", []):
        s = base["slot"]
        ok = enabled.get(s) is not False and (s != "ring" and s != "ring2" or enabled.get("ring") is not False or enabled.get("ring2") is not False)
        if not ok:
            rep.err("item_bases.csv", base["__line__"], "E_SLOT_LOCKED",
                    f"{base['id']}: a posição '{s}' está bloqueada em rules.csv (equip_slot_{s} = false); a peça nunca poderia ser equipada")
    # Economia do protótipo (docs/16 11.8)
    if g("polish_step_fraction") is not None and g("polish_max_steps") is not None:
        if g("polish_step_fraction") * g("polish_max_steps") > 1:
            rep.warn("rules.csv", ln.get("polish_max_steps", 0), "W_RULES", "polish_step_fraction x polish_max_steps > 1: os últimos passos de Lapidar passam do máximo da faixa e não rendem nada")
    shards = [g("dismantle_shards_normal"), g("dismantle_shards_magic"), g("dismantle_shards_rare")]
    if None not in shards and not (shards[0] <= shards[1] <= shards[2]):
        rep.warn("rules.csv", ln.get("dismantle_shards_magic", 0), "W_RULES", "Lascas de Desmontar deveriam crescer com a raridade (Comum <= Mágico <= Raro)")
    if g("reforge_mult_cap") is not None and g("reforge_step_mult") is not None:
        if g("reforge_step_mult") == 0 and g("reforge_mult_cap") > 1:
            rep.warn("rules.csv", ln.get("reforge_step_mult", 0), "W_RULES", "reforge_step_mult = 0: reforge_mult_cap nunca é atingido")


def run_checks(c: Content, schemas: Dict[str, dict], rep: Report) -> None:
    for table, schema in schemas.items():
        rows = c.tables.get(table, [])
        for chk in schema.get("checks", []):
            kind = chk["check"]
            if kind == "lte":
                for r in rows:
                    if r[chk["a"]] > r[chk["b"]]:
                        rep.err(table, r["__line__"], "E_MINMAX", f"{chk['a']} ({r[chk['a']]}) > {chk['b']} ({r[chk['b']]})")
            elif kind == "sum_positive":
                for r in rows:
                    if sum(r[k] for k in chk["cols"]) <= 0:
                        rep.err(table, r["__line__"], "E_WEIGHT", f"soma de {', '.join(chk['cols'])} deve ser > 0")
            else:
                CHECKS[kind](c, table, rows, rep)


def chk_skill(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    cd_min = c.rules.get("cooldown_min", 0.1)
    for r in rows:
        ln = r["__line__"]
        if 0 < r["cooldown"] < cd_min:
            rep.err(table, ln, "E_RANGE", f"cooldown {r['cooldown']} > 0 e < cooldown_min ({cd_min})")
        if r["idleSupported"] and r["idleParitySampleSize"] <= 0:
            rep.err(table, ln, "E_IDLE", "idleSupported=true exige idleParitySampleSize > 0 (perfil calibrado pelo teste de paridade)")
        check_idle_calibration(table, ln, r, rep)
        if r["classId"]:
            seg = r["classId"].split(".", 1)[1]
            if not r["id"].startswith(f"skill.{seg}."):
                rep.err(table, ln, "E_ID", f"habilidade de {r['classId']} deve ter ID 'skill.{seg}.<nome>'")
        elif not r["id"].startswith("skill.enemy.") and not r["id"].startswith("skill.common.") and not r["id"].startswith("skill.devoured."):
            rep.err(table, ln, "E_ID", "habilidade sem classId deve ter ID 'skill.enemy.*' , 'skill.common.*' ou 'skill.devoured.*'")
        coefs = [r["coefficientRank1"], r["coefficientRank2"], r["coefficientRank3"]]
        if not coefs[0] <= coefs[1] <= coefs[2]:
            rep.warn(table, ln, "W_COEF", "coeficientes por rank deveriam ser não decrescentes")
        dmg = sum(r[f"baseDamage{t}"] for t in ("Physical", "Fire", "Cold", "Lightning"))
        if r["scalesWithWeapon"] and dmg > 0:
            rep.warn(table, ln, "W_DAMAGE", "scalesWithWeapon=true: baseDamage* é ignorado (vem da arma)")
        if r["windup"] + r["impact"] + r["recovery"] <= 0 and r["shape"] not in ("self",):
            rep.warn(table, ln, "W_TIMING", "windup+impact+recovery = 0")
        if r["idleFractionOfGroupHit"] == 0 and r["idleAvgTargetsHit"] <= 0 and r["idleSupported"]:
            rep.err(table, ln, "E_IDLE", "perfil idle sem alvos (idleAvgTargetsHit e idleFractionOfGroupHit = 0)")
        # docs/18 8.2 e 8.3: semântica de forma no tempo real
        if r["pierce"] > 0 and r["shape"] != "projectile":
            rep.err(table, ln, "E_PIERCE", "pierce > 0 só vale para shape=projectile")
        if r["explosionRadius"] > 0 and r["shape"] != "projectile":
            rep.err(table, ln, "E_EXPLOSION", "explosionRadius > 0 só vale para shape=projectile")
        if r["shape"] == "projectile" and r["projectiles"] > 1 and r["coneAngle"] <= 0:
            rep.err(table, ln, "E_FAN", "projectile com projectiles > 1 exige coneAngle > 0 (leque)")
        if r["shape"] == "area" and r["radius"] <= 0:
            rep.err(table, ln, "E_AREA", "shape=area exige radius > 0")
        if r["shape"] == "dash" and "projectile" in r["tags"] and "dash_shot_range" not in c.rules:
            rep.err(table, ln, "E_DASH_SHOT", "dash com tag projectile exige dash_shot_range em rules.csv")


def check_idle_calibration(table: str, ln: int, r: dict, rep: Report) -> None:
    """docs/13 item 8: manual_estimate (ou bot_parity) exige amostra > 0; idleSupported exige calibracao."""
    cal = r["idleCalibration"]
    sample = r["idleParitySampleSize"]
    if cal in ("manual_estimate", "bot_parity") and sample <= 0:
        rep.err(table, ln, "E_IDLE", f"idleCalibration={cal} exige idleParitySampleSize > 0")
    if r["idleSupported"] and cal == "none":
        rep.err(table, ln, "E_IDLE", "idleSupported=true exige idleCalibration manual_estimate ou bot_parity")


def chk_unique(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    for r in rows:
        ln = r["__line__"]
        if r["idleSupported"] and r["idleParitySampleSize"] <= 0:
            rep.err(table, ln, "E_IDLE", "idleSupported=true exige idleParitySampleSize > 0 (docs/13 item 8)")
        check_idle_calibration(table, ln, r, rep)


def chk_potion(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    slots: Dict[int, int] = {}
    pot_rule = c.rules.get("potion_lockout")
    for r in rows:
        ln = r["__line__"]
        if r["kind"] == "barrier" and r["duration"] <= 0:
            rep.err(table, ln, "E_POTION", "kind=barrier exige duration > 0")
        if r["kind"] == "heal" and r["duration"] > 0:
            rep.err(table, ln, "E_POTION", "kind=heal nao usa duration")
        if r["hotkeySlot"] in slots:
            rep.err(table, ln, "E_POTION", f"hotkeySlot {r['hotkeySlot']} repetido (primeiro na linha {slots[r['hotkeySlot']]})")
        slots[r["hotkeySlot"]] = ln
        if pot_rule is not None and r["globalLockout"] != pot_rule:
            rep.warn(table, ln, "W_POTION", f"globalLockout {r['globalLockout']} difere de rules.csv potion_lockout ({pot_rule})")


def chk_basic_kit(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    skills = c.ids("skills.csv")
    effects = c.ids("effects.csv")
    classes = c.ids("classes.csv")
    for r in rows:
        ln = r["__line__"]
        cid = r["classId"]
        for sid in list(r["lightChain"]) + [r["heavySkill"]]:
            s = skills.get(sid)
            if s is not None and s["classId"] != cid:
                rep.err(table, ln, "E_KIT", f"{sid} não pertence a {cid} (classId da habilidade = '{s['classId']}')")
        first = skills.get(r["lightChain"][0]) if r["lightChain"] else None
        cls = classes.get(cid)
        if first is not None and cls is not None and cls["startingSkill"] != r["lightChain"][0]:
            rep.warn(table, ln, "W_KIT", f"lightChain[0] ({r['lightChain'][0]}) difere de startingSkill ({cls['startingSkill']}) em classes.csv")
        ge = effects.get(r["guardEffect"])
        if ge is not None and "guard" not in ge["tags"]:
            rep.err(table, ln, "E_KIT", f"guardEffect {r['guardEffect']} deve ter a tag 'guard' (o dano recebido só cai se o golpe vem de dentro do arco)")
        if r["guardPerfectWindow"] > 0 and r["guardPerfectCooldown"] < r["guardPerfectWindow"]:
            rep.warn(table, ln, "W_KIT", "guardPerfectCooldown menor que guardPerfectWindow: a janela perfeita reabriria dentro de si mesma")
        # docs/19 N0: refAttackTime e o attackTime da arma inicial da classe (so faz sentido se o golpe escala com a arma)
        ref = r["refAttackTime"]
        first_skill = skills.get(r["lightChain"][0]) if r["lightChain"] else None
        if ref > 0 and first_skill is not None and first_skill["scalesWithWeapon"]:
            style = "melee" if "melee" in first_skill["tags"] else "projectile"
            starters = [b for b in c.tables.get("item_bases.csv", [])
                        if b["slot"] == "main_hand" and b["itemLevel"] <= 1 and style in b["weaponTags"]]
            if starters and not any(abs(b["attackTime"] - ref) < 1e-9 for b in starters):
                times = ", ".join(sorted({str(b["attackTime"]) for b in starters}))
                rep.warn(table, ln, "W_KIT", f"refAttackTime {ref} difere do attackTime da arma inicial da classe ({times}): o kit inicial não ficaria com fator 1,0")


def chk_craft_cost(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    """docs/16 11.8: custos de Encantar. Tabela opcional; presente, precisa cobrir todas as operações."""
    if table not in c.tables:
        return
    allowed = {"refine": ("normal",), "reforge": ("magic", "rare"), "add": ("magic", "rare"), "polish": ("normal", "magic", "rare", "any")}
    max_steps = c.rules.get("polish_max_steps")
    seen: Dict[Tuple[str, str, int], int] = {}
    for r in rows:
        ln = r["__line__"]
        key = (r["op"], r["rarity"], r["step"])
        if key in seen:
            rep.err(table, ln, "E_CRAFT", f"par (op, rarity, step) {key} repetido (primeiro na linha {seen[key]})")
        seen[key] = ln
        if r["rarity"] not in allowed[r["op"]]:
            rep.err(table, ln, "E_CRAFT", f"op={r['op']} só aceita rarity {', '.join(allowed[r['op']])} (veio {r['rarity']})")
        if r["op"] != "polish" and r["step"] != 0:
            rep.err(table, ln, "E_CRAFT", f"op={r['op']} usa step 0 (só polish usa passos)")
        if r["op"] == "polish" and r["step"] < 1:
            rep.err(table, ln, "E_CRAFT", "op=polish exige step >= 1")
        if r["op"] == "polish" and isinstance(max_steps, int) and r["step"] > max_steps:
            rep.err(table, ln, "E_CRAFT", f"step {r['step']} > polish_max_steps ({max_steps})")
    for op in allowed:
        if not any(r["op"] == op for r in rows):
            rep.err(table, 0, "E_CRAFT", f"a operação '{op}' não tem nenhuma linha em craft_costs.csv")
    if isinstance(max_steps, int):
        for s in range(1, max_steps + 1):
            if not any(r["op"] == "polish" and r["step"] == s for r in rows):
                rep.err(table, 0, "E_CRAFT", f"polish sem linha para o passo {s} (1..polish_max_steps = {max_steps})")
    dn = c.rules.get("dismantle_shards_normal")
    for r in rows:
        if r["op"] == "refine" and isinstance(dn, int) and dn >= r["shardCost"]:
            rep.warn(table, r["__line__"], "W_CRAFT", "Desmontar Comum devolve >= Lascas que Refinar custa: ciclo infinito de Lascas")


def chk_vendor_stock(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    """docs/16 11.8: estoque fixo do Vendedor. refId não é validado contra tabela (não há tabela de consumíveis)."""
    seen: Dict[str, int] = {}
    cap = c.rules.get("refill_flask_carry_cap")
    for r in rows:
        ln = r["__line__"]
        if r["refId"] in seen:
            rep.err(table, ln, "E_VENDOR", f"refId '{r['refId']}' repetido (primeiro na linha {seen[r['refId']]})")
        seen[r["refId"]] = ln
        if r["refId"] == "consumable.refill_flask" and isinstance(cap, int) and r["carryCap"] != cap:
            rep.err(table, ln, "E_VENDOR", f"carryCap {r['carryCap']} difere de refill_flask_carry_cap em rules.csv ({cap})")


def chk_modifier(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    if rows and sum(r["weightPrototype"] for r in rows) <= 0:
        rep.err(table, rows[0]["__line__"], "E_WEIGHT", "a soma de weightPrototype deve ser > 0 (ao menos um modificador sorteavel)")
    for r in rows:
        ln = r["__line__"]
        if r["deathExplosionRadius"] > 0 and (r["deathExplosionDamage"] <= 0 or r["deathExplosionFuse"] <= 0):
            rep.err(table, ln, "E_MODIFIER", "explosao (deathExplosionRadius > 0) exige dano e fuse > 0")
        if r["deathExplosionRadius"] == 0 and (r["deathExplosionDamage"] > 0 or r["deathExplosionFuse"] > 0):
            rep.err(table, ln, "E_MODIFIER", "deathExplosionDamage/Fuse sem deathExplosionRadius")


def chk_boss_phase(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    enemies = c.ids("enemies.csv")
    by_boss: Dict[str, List[dict]] = {}
    for r in rows:
        ln = r["__line__"]
        by_boss.setdefault(r["bossId"], []).append(r)
        if r["bossId"] in enemies and not enemies[r["bossId"]]["isBoss"]:
            rep.err(table, ln, "E_BOSS", f"bossId '{r['bossId']}' nao e isBoss=true em enemies.csv")
        if r["phase"] > 1 and r["transitionSeconds"] <= 0:
            rep.err(table, ln, "E_BOSS", "fase > 1 exige transitionSeconds > 0 (rugido de transicao)")
        if r["summonEnemyId"] and r["summonCount"] <= 0:
            rep.err(table, ln, "E_BOSS", "summonEnemyId sem summonCount > 0")
        if r["summonCount"] > 0 and not (0 < r["summonAtFraction"] < 1):
            rep.err(table, ln, "E_BOSS", "summonCount > 0 exige summonAtFraction em (0, 1)")
        if r["summonCount"] <= 0 and r["summonAtFraction"] > 0:
            rep.err(table, ln, "E_BOSS", "summonAtFraction sem summonCount > 0")
        if r["decisionDelayMin"] > r["decisionDelayMax"]:
            rep.err(table, ln, "E_MINMAX", "decisionDelayMin > decisionDelayMax")
    for boss, ps in by_boss.items():
        ps = sorted(ps, key=lambda r: r["phase"])
        if [r["phase"] for r in ps] != list(range(1, len(ps) + 1)):
            rep.err(table, ps[0]["__line__"], "E_BOSS", f"fases de '{boss}' devem ser 1..N sem buracos")
        if ps[0]["lifeThreshold"] != 1.0:
            rep.err(table, ps[0]["__line__"], "E_BOSS", "a fase 1 comeca com lifeThreshold 1.0")
        for a, b in zip(ps, ps[1:]):
            if not b["lifeThreshold"] < a["lifeThreshold"]:
                rep.err(table, b["__line__"], "E_BOSS", "lifeThreshold deve cair a cada fase")


def chk_boss_pattern(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    phases = {(p["bossId"], p["phase"]) for p in c.tables.get("boss_phases.csv", [])}
    attacks = {(a["enemyId"], a["skillId"]) for a in c.tables.get("enemy_attacks.csv", [])}
    for r in rows:
        ln = r["__line__"]
        if (r["bossId"], r["phase"]) not in phases:
            rep.err(table, ln, "E_FK", f"bossId/phase '{r['bossId']}/{r['phase']}' nao existe em boss_phases.csv")
        if (r["bossId"], r["skillId"]) not in attacks:
            rep.err(table, ln, "E_FK", f"skillId '{r['skillId']}' nao esta em enemy_attacks.csv para '{r['bossId']}'")
        if 0 < r["cooldown"] < c.rules.get("cooldown_min", 0.1):
            rep.err(table, ln, "E_RANGE", "cooldown > 0 e < cooldown_min")


def chk_enemy_ai(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    enemies = c.ids("enemies.csv")
    for r in rows:
        ln = r["__line__"]
        e = enemies.get(r["enemyId"])
        if e is not None:
            if e["isBoss"]:
                rep.err(table, ln, "E_ENEMY_AI", "chefe nao usa enemy_ai.csv (fases em boss_phases.csv)")
            if r["aggroRange"] and r["aggroRange"] != e["aggroRange"]:
                rep.err(table, ln, "E_ENEMY_AI", f"aggroRange {r['aggroRange']} difere de enemies.csv ({e['aggroRange']})")
        if r["circleMin"] > r["circleMax"]:
            rep.err(table, ln, "E_MINMAX", "circleMin > circleMax")
        if r["preferredMin"] > r["preferredMax"]:
            rep.err(table, ln, "E_MINMAX", "preferredMin > preferredMax")
        if r["tokenIntervalMin"] > r["tokenIntervalMax"]:
            rep.err(table, ln, "E_MINMAX", "tokenIntervalMin > tokenIntervalMax")
        if r["circleMax"] > 0 and r["attackTokens"] < 1:
            rep.err(table, ln, "E_ENEMY_AI", "cerco (circleMax > 0) exige attackTokens >= 1")


def boss_tables(c: Content) -> set:
    return {e["lootTableId"] for e in c.tables.get("enemies.csv", []) if e["isBoss"] and e["lootTableId"]}


def stain_loot_table(c: Content) -> str:
    """Tabela da Mancha (Story/story_rules.csv, chave stain_loot_table); "" se não existir."""
    path = os.path.join(c.data_dir, "Story", "story_rules.csv")
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            key, _, val = line.strip().partition(",")
            if key == "stain_loot_table":
                return val
    return ""


def chk_effect(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    for r in rows:
        ln = r["__line__"]
        dot = sum(r[f"damagePerTick{t}"] for t in ("Physical", "Fire", "Cold", "Lightning"))
        if dot > 0 and r["tickInterval"] <= 0:
            rep.err(table, ln, "E_EFFECT", "damagePerTick* > 0 exige tickInterval > 0")
        if r["tickInterval"] > 0 and r["duration"] <= 0:
            rep.err(table, ln, "E_EFFECT", "tickInterval > 0 exige duration > 0")
        if r["stackRule"] != "stack_n" and r["maxStacks"] != 1:
            rep.warn(table, ln, "W_EFFECT", "maxStacks só é usado com stack_n")
        if r["trigger"] == "none" and r["triggerChance"] != 1:
            rep.warn(table, ln, "W_EFFECT", "triggerChance ignorado com trigger=none")
        if r["trigger"] != "none" and 0 < r["internalCooldown"] < c.rules.get("trigger_icd_min", 0.25):
            rep.warn(table, ln, "W_EFFECT", "internalCooldown abaixo de trigger_icd_min; o core usa o mínimo")


def chk_enemy(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    attacks = c.tables.get("enemy_attacks.csv", [])
    with_attacks = {a["enemyId"] for a in attacks}
    for r in rows:
        ln = r["__line__"]
        stats = {g["stat"] for g in r["stats"]}
        if "life" not in stats:
            rep.err(table, ln, "E_ENEMY", "stats precisa incluir 'life'")
        for g in r["stats"]:
            if g["stat"] == "life" and g["base"] <= 0:
                rep.err(table, ln, "E_ENEMY", "vida base deve ser > 0")
        if r["id"] not in with_attacks:
            rep.err(table, ln, "E_ENEMY", "inimigo sem nenhuma linha em enemy_attacks.csv")
        if r["isBoss"] and r["isElite"]:
            rep.warn(table, ln, "W_ENEMY", "isBoss e isElite ao mesmo tempo")
        if r["modifierId"] and not r["isElite"]:
            rep.err(table, ln, "E_ENEMY", "modifierId so vale para elite fixa (isElite=true)")
        if r["eliteLootTableId"] and not r["isElite"]:
            rep.err(table, ln, "E_ENEMY", "eliteLootTableId so vale para elite fixa (isElite=true)")


def chk_item_base(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    for r in rows:
        ln = r["__line__"]
        dmg = sum(r[f"weaponDamage{t}"] for t in ("Physical", "Fire", "Cold", "Lightning"))
        if r["slot"] == "main_hand":
            if r["attackTime"] <= 0:
                rep.err(table, ln, "E_WEAPON", "arma (main_hand) precisa de attackTime > 0")
            if dmg <= 0:
                rep.err(table, ln, "E_WEAPON", "arma (main_hand) precisa de weaponDamage* > 0")
            wt = set(r["weaponTags"])
            if len(wt & {"melee", "projectile"}) != 1 or wt - {"melee", "projectile"}:
                rep.err(table, ln, "E_WEAPON", "weaponTags deve ser exatamente 'melee' ou 'projectile'")
        else:
            if dmg > 0 or r["attackTime"] > 0 or r["weaponTags"]:
                rep.err(table, ln, "E_WEAPON", "só main_hand pode ter weaponDamage/attackTime/weaponTags")


def chk_loot(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    entries = c.tables.get("loot_entries.csv", [])
    by_table: Dict[str, List[dict]] = {}
    for e in entries:
        by_table.setdefault(e["tableId"], []).append(e)
    for r in rows:
        if r["id"] not in by_table:
            rep.err(table, r["__line__"], "E_LOOT", "tabela sem nenhuma entrada em loot_entries.csv")
    # ciclos e profundidade (máx. 8, loot.h)
    graph = {t: [e["refId"] for e in es if e["kind"] == "table"] for t, es in by_table.items()}
    lines = {r["id"]: r["__line__"] for r in rows}

    def depth(node: str, stack: List[str]) -> int:
        if node in stack:
            raise ValueError(" -> ".join(stack + [node]))
        best = 1
        for nxt in graph.get(node, []):
            best = max(best, 1 + depth(nxt, stack + [node]))
        return best

    for t in graph:
        try:
            d = depth(t, [])
            if d > 8:
                rep.err(table, lines.get(t, 0), "E_LOOT", f"subtabelas com profundidade {d} > 8")
        except ValueError as e:
            rep.err(table, lines.get(t, 0), "E_LOOT", f"ciclo de subtabelas: {e}")


REF_BY_KIND = {
    "item_base": ("item_bases.csv", "item_base."),
    "unique": ("uniques.csv", "unique."),
    "table": ("loot_tables.csv", "loot."),
    "spec_book": (None, "book.spec."),
    "map_stone": (None, "map_stone."),
    "echo_fragment": (None, "material.echo_fragment"),
}
MANUAL_ONLY_KINDS = {"unique", "spec_book", "map_stone", "echo_fragment"}


def chk_loot_entry(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    for r in rows:
        ln, kind, ref = r["__line__"], r["kind"], r["refId"]
        if kind == "nothing":
            if ref:
                rep.err(table, ln, "E_LOOT", "kind=nothing não usa refId")
            continue
        if not ref:
            rep.err(table, ln, "E_REQUIRED", f"refId obrigatório para kind={kind}")
            continue
        if kind == "stack":
            if not ref.startswith(STACK_PREFIXES):
                rep.err(table, ln, "E_LOOT", f"stack deve referenciar {', '.join(p + '*' for p in STACK_PREFIXES)}")
            if ref == "material.echo_fragment":
                rep.err(table, ln, "E_LOOT", "Fragmento de Eco usa kind=echo_fragment, não stack")
        else:
            tbl, prefix = REF_BY_KIND[kind]
            if kind == "echo_fragment":
                if ref != prefix:
                    rep.err(table, ln, "E_LOOT", "echo_fragment deve ter refId 'material.echo_fragment'")
            elif not ref.startswith(prefix):
                rep.err(table, ln, "E_LOOT", f"kind={kind} exige refId '{prefix}*'")
            if tbl and ref not in c.ids(tbl):
                rep.err(table, ln, "E_FK", f"refId: '{ref}' não existe em {tbl}")
        fixed = r["fixedChance"] > 0 or r["guaranteeFirstKill"] or r["pityKills"] > 0
        if r["weight"] <= 0 and not fixed:
            rep.err(table, ln, "E_WEIGHT", "peso vazio/0 so e valido em entrada fixa (fixedChance > 0, guaranteeFirstKill ou pityKills > 0)")
        if fixed and r["tableId"] not in boss_tables(c):
            rep.err(table, ln, "E_FIXED_TABLE", f"entrada fixa so vale na tabela de topo de um chefe; '{r['tableId']}' nao e")
        if fixed and any(o["kind"] == "table" and o["refId"] == r["tableId"] for o in rows):
            rep.err(table, ln, "E_FIXED_TABLE", f"entrada fixa em subtabela ('{r['tableId']}' e alvo de kind=table) nunca cai")
        if kind == "unique" and r["tableId"] not in boss_tables(c) and r["tableId"] != stain_loot_table(c):
            rep.err(table, ln, "E_UNIQUE_TABLE", f"Unico so pode estar em tabela de chefe (lootTableId de enemies.csv com isBoss=true) ou na tabela da Mancha (stain_loot_table); '{r['tableId']}' nao e")
        if kind in MANUAL_ONLY_KINDS and not r["manualOnly"]:
            rep.err(table, ln, "E_IDLE_TOP", f"kind={kind} é item de topo: manualOnly deve ser true (regra 4 do idle)")
        if kind != "stack" and (r["minAmount"] != 1 or r["maxAmount"] != 1):
            rep.warn(table, ln, "W_LOOT", "minAmount/maxAmount só valem para stack")


def chk_encounter(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    enemies = c.ids("enemies.csv")
    for r in rows:
        ln = r["__line__"]
        if not r["groups"]:
            rep.err(table, ln, "E_REQUIRED", "groups vazio")
        has_boss = False
        for g in r["groups"]:
            if g["enemyId"] not in enemies:
                rep.err(table, ln, "E_FK", f"groups: '{g['enemyId']}' não existe em enemies.csv")
            elif enemies[g["enemyId"]]["isBoss"]:
                has_boss = True
        if r["isBoss"] and not has_boss and all(g["enemyId"] in enemies for g in r["groups"]):
            rep.err(table, ln, "E_BOSS", "encontro isBoss=true sem inimigo isBoss=true")
        if has_boss and not r["isBoss"]:
            rep.err(table, ln, "E_BOSS", "encontro com chefe deve ter isBoss=true")


def chk_map(c: Content, table: str, rows: List[dict], rep: Report) -> None:
    encs = c.ids("encounters.csv")
    for r in rows:
        ln = r["__line__"]
        for e in r["encounters"]:
            if e in encs and encs[e]["isBoss"]:
                rep.err(table, ln, "E_BOSS", f"'{e}' é de chefe: use bossEncounter, não encounters")
        b = r["bossEncounter"]
        if b and b in encs and not encs[b]["isBoss"]:
            rep.err(table, ln, "E_BOSS", f"bossEncounter '{b}' não tem isBoss=true")
        if r["tier"] == 0 and r["id"].startswith("map.endgame."):
            rep.warn(table, ln, "W_MAP", "mapa endgame com tier 0")


def chk_class(c: Content) -> None:
    pass


CHECKS = {
    "skill_rules": chk_skill,
    "effect_rules": chk_effect,
    "enemy_rules": chk_enemy,
    "item_base_rules": chk_item_base,
    "loot_rules": chk_loot,
    "loot_entry_rules": chk_loot_entry,
    "encounter_rules": chk_encounter,
    "map_rules": chk_map,
    "unique_rules": chk_unique,
    "potion_rules": chk_potion,
    "basic_kit_rules": chk_basic_kit,
    "craft_cost_rules": chk_craft_cost,
    "vendor_stock_rules": chk_vendor_stock,
    "modifier_rules": chk_modifier,
    "boss_phase_rules": chk_boss_phase,
    "boss_pattern_rules": chk_boss_pattern,
    "enemy_ai_rules": chk_enemy_ai,
}


def check_classes_extra(c: Content, rep: Report) -> None:
    stats = c.tables.get("class_stats.csv", [])
    skills = c.ids("skills.csv")
    for r in c.tables.get("classes.csv", []):
        have = {s["stat"] for s in stats if s["classId"] == r["id"]}
        for need in ("life", "resource"):
            if need not in have:
                rep.err("classes.csv", r["__line__"], "E_CLASS", f"class_stats.csv não define '{need}' para {r['id']}")
        sk = skills.get(r["startingSkill"])
        if sk is not None and sk["classId"] not in ("", r["id"]):
            rep.err("classes.csv", r["__line__"], "E_CLASS", f"startingSkill pertence a {sk['classId']}")
        if sk is not None and sk["unlockLevel"] != 1:
            rep.err("classes.csv", r["__line__"], "E_CLASS", "startingSkill deve ter unlockLevel = 1")
    for s in stats:
        if s["stat"] == "life" and s["base"] <= 0:
            rep.err("class_stats.csv", s["__line__"], "E_CLASS", "vida base deve ser > 0")


# ---------------------------------------------------------------------------
# Localização (Content/Data/Loc/*.csv: key,pt_BR,en,es,context,gender)
# ---------------------------------------------------------------------------
def read_loc_dir(loc_dir: str, rep: Report) -> Dict[str, Dict[str, str]]:
    import csv
    keys: Dict[str, Dict[str, str]] = {}
    for f in sorted(os.listdir(loc_dir)):
        if not f.endswith(".csv"):
            continue
        rel = "Loc/" + f
        with open(os.path.join(loc_dir, f), encoding="utf-8-sig", newline="") as fh:
            rd = csv.reader(fh)
            try:
                header = next(rd)
            except StopIteration:
                rep.err(rel, 0, "E_EMPTY", "arquivo vazio")
                continue
            for need in ("key", "pt_BR", "en"):
                if need not in header:
                    rep.err(rel, 1, "E_HEADER", f"coluna '{need}' ausente (esperado key,pt_BR,en,es,context,gender)")
            if "key" not in header:
                continue
            ki = header.index("key")
            for row in rd:
                if not row or all(x == "" for x in row):
                    continue
                d = dict(zip(header, row))
                k = row[ki]
                if k in keys:
                    rep.err(rel, rd.line_num, "E_DUP_ID", f"chave de localização '{k}' repetida")
                keys[k] = d
                for lang in ("pt_BR", "en"):
                    if lang in header and d.get(lang, "") == "":
                        rep.err(rel, rd.line_num, "E_LOC", f"'{k}' sem texto em {lang}")
    return keys


def expand_loc(template: str, row: dict) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(row.get(m.group(1), "")), template)


def check_localization(c: Content, schemas: Dict[str, dict], data_dir: str, rep: Report) -> None:
    check_classes_extra(c, rep)  # (aproveita o passo final para regras entre tabelas de classe)
    loc_dir = os.path.join(data_dir, "Loc")
    if not os.path.isdir(loc_dir):
        rep.info("pasta Loc/ não existe: checagem de chaves de localização pulada")
        return
    keys = read_loc_dir(loc_dir, rep)
    rep.info(f"localização: {len(keys)} chave(s) em Loc/")
    for table, schema in schemas.items():
        for spec in schema.get("locKeys", []):
            tmpl = spec if isinstance(spec, str) else spec["key"]
            cond = None if isinstance(spec, str) else spec.get("when")
            for r in c.tables.get(table, []):
                if cond:
                    if "=" in cond:
                        col, val = cond.split("=", 1)
                        if r.get(col) != val:
                            continue
                    elif not r.get(cond):
                        continue
                k = expand_loc(tmpl, r)
                if k and k not in keys:
                    rep.err(table, r["__line__"], "E_LOC_MISSING", f"chave de localização '{k}' não existe em Loc/*.csv")


# ---------------------------------------------------------------------------
# Lock de conteúdo publicado (IDs nunca renomeados/removidos; content_version sobe)
# ---------------------------------------------------------------------------
LOCK_NAME = "content_lock.json"


def tables_digest(data_dir: str) -> Dict[str, str]:
    out = {}
    for f in sorted(os.listdir(data_dir)):
        if f.endswith(".csv") and f != "meta.csv":
            with open(os.path.join(data_dir, f), "rb") as fh:
                out[f] = hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()
    return out


def check_lock(c: Content, data_dir: str, rep: Report) -> None:
    path = os.path.join(data_dir, LOCK_NAME)
    if not os.path.isfile(path):
        rep.info(f"{LOCK_NAME} ausente: nenhum conteúdo publicado ainda (crie com --update-lock na 1ª release)")
        return
    with open(path, encoding="utf-8") as fh:
        lock = json.load(fh)
    current_ids = {i for t in c.by_id.values() for i in t}
    for pid in lock.get("ids", []):
        if pid not in current_ids:
            rep.err(LOCK_NAME, 0, "E_ID_REMOVED", f"ID publicado '{pid}' sumiu (IDs nunca são renomeados nem removidos; marque como obsoleto no conteúdo)")
    cv = c.meta.get("content_version")
    if isinstance(cv, int):
        if cv < lock.get("content_version", 0):
            rep.err("meta.csv", 0, "E_VERSION", f"content_version {cv} menor que o publicado ({lock['content_version']})")
        elif cv == lock.get("content_version") and tables_digest(data_dir) != lock.get("tables_sha256"):
            rep.err("meta.csv", 0, "E_VERSION", "dados mudaram desde a última publicação e content_version não subiu")


def update_lock(c: Content, data_dir: str) -> str:
    ids = sorted({i for t in c.by_id.values() for i in t})
    path = os.path.join(data_dir, LOCK_NAME)
    old_ids: List[str] = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            old_ids = json.load(fh).get("ids", [])
    lock = {"content_version": c.meta.get("content_version"), "tables_sha256": tables_digest(data_dir),
            "ids": sorted(set(ids) | set(old_ids))}
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(lock, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


# ---------------------------------------------------------------------------
# JSON canônico (espelho de shatter::json::Serialize(pretty=false)) e SHA-256
# ---------------------------------------------------------------------------
class JsonDouble(float):
    """Número que veio de literal não-inteiro (o core guarda como double)."""


def _parse_int(s: str):
    v = int(s)
    if INT64_MIN <= v <= INT64_MAX:
        return v
    return JsonDouble(float(s))


def _bad_const(s: str):
    raise ValueError(f"constante JSON inválida: {s}")


def json_load_text(text: str):
    return json.loads(text, parse_int=_parse_int, parse_float=lambda s: JsonDouble(float(s)),
                      parse_constant=_bad_const)


def _canon_str(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif o < 0x20:
            out.append("\\u%04x" % o)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def canonical(v) -> str:
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, JsonDouble) or isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            raise ValueError("NaN/Inf não é permitido no save")
        return "%.17g" % v
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return _canon_str(v)
    if isinstance(v, list):
        return "[" + ",".join(canonical(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(_canon_str(k) + ":" + canonical(x) for k, x in v.items()) + "}"
    raise TypeError(type(v))


def data_sha256(data) -> str:
    return hashlib.sha256(canonical(data).encode("utf-8")).hexdigest()


def write_save_file(path: str, save_version: int, data: dict) -> None:
    env = {"format": SAVE_FORMAT_TAG, "save_version": save_version, "sha256": data_sha256(data), "data": data}
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(env, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Subconjunto de JSON Schema 2020-12 (o suficiente para save*.schema.json)
# ---------------------------------------------------------------------------
def _jtype(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, JsonDouble):
        return "integer" if float(v).is_integer() else "number"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "integer" if v.is_integer() else "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    return "object"


def jsonschema_validate(inst, sch: dict, root: dict, path: str, errs: List[str]) -> None:
    if "$ref" in sch:
        ref = sch["$ref"]
        if not ref.startswith("#/$defs/"):
            raise SchemaError(f"$ref não suportado: {ref}")
        jsonschema_validate(inst, root["$defs"][ref[len("#/$defs/"):]], root, path, errs)
        return
    if "oneOf" in sch:
        ok = 0
        sub_errs: List[str] = []
        for s in sch["oneOf"]:
            e: List[str] = []
            jsonschema_validate(inst, s, root, path, e)
            if not e:
                ok += 1
            sub_errs.extend(e)
        if ok != 1:
            errs.append(f"{path}: deve casar com exatamente 1 alternativa ({'; '.join(sub_errs[:3])})")
        return
    if "type" in sch:
        types = sch["type"] if isinstance(sch["type"], list) else [sch["type"]]
        t = _jtype(inst)
        if t not in types and not (t == "integer" and "number" in types):
            errs.append(f"{path}: tipo {t}, esperado {'|'.join(types)}")
            return
    if "const" in sch and inst != sch["const"]:
        errs.append(f"{path}: deve ser {sch['const']!r}")
    if "enum" in sch and inst not in sch["enum"]:
        errs.append(f"{path}: {inst!r} não está em {sch['enum']}")
    if isinstance(inst, str):
        if "pattern" in sch and not re.search(sch["pattern"], inst):
            errs.append(f"{path}: {inst!r} não segue {sch['pattern']}")
        if "minLength" in sch and len(inst) < sch["minLength"]:
            errs.append(f"{path}: string curta demais")
        if "maxLength" in sch and len(inst) > sch["maxLength"]:
            errs.append(f"{path}: string longa demais (máx. {sch['maxLength']})")
    if isinstance(inst, (int, float)) and not isinstance(inst, bool):
        if "minimum" in sch and inst < sch["minimum"]:
            errs.append(f"{path}: {inst} < {sch['minimum']}")
        if "maximum" in sch and inst > sch["maximum"]:
            errs.append(f"{path}: {inst} > {sch['maximum']}")
        if "exclusiveMinimum" in sch and not inst > sch["exclusiveMinimum"]:
            errs.append(f"{path}: {inst} deve ser > {sch['exclusiveMinimum']}")
    if isinstance(inst, list):
        if "minItems" in sch and len(inst) < sch["minItems"]:
            errs.append(f"{path}: mínimo {sch['minItems']} itens")
        if "maxItems" in sch and len(inst) > sch["maxItems"]:
            errs.append(f"{path}: máximo {sch['maxItems']} itens")
        if "items" in sch:
            for i, x in enumerate(inst):
                jsonschema_validate(x, sch["items"], root, f"{path}[{i}]", errs)
    if isinstance(inst, dict):
        for k in sch.get("required", []):
            if k not in inst:
                errs.append(f"{path}: campo obrigatório '{k}' ausente")
        props = sch.get("properties", {})
        for k, v in inst.items():
            if k in props:
                jsonschema_validate(v, props[k], root, f"{path}.{k}", errs)
            elif sch.get("additionalProperties") is False:
                errs.append(f"{path}: campo desconhecido '{k}'")


def load_save_schemas(schema_dir: str) -> Dict[int, dict]:
    out = {}
    for f in sorted(os.listdir(schema_dir)):
        if f.startswith("save") and f.endswith(".schema.json"):
            with open(os.path.join(schema_dir, f), encoding="utf-8") as fh:
                s = json.load(fh)
            out[int(s["x-save-version"])] = s
    if not out:
        raise SchemaError("nenhum save*.schema.json encontrado")
    return out


# ---------------------------------------------------------------------------
# Migrações de referência (espelho do que o core implementa em src/save_migrations.cpp)
# ---------------------------------------------------------------------------
def _potion_slot_defaults() -> List[dict]:
    """Um slot por linha de potions.csv, na ordem do arquivo: (potion_id, máximo de cargas)."""
    import csv
    path = os.path.join(DEFAULT_DATA, "potions.csv")
    with open(path, encoding="utf-8", newline="") as fh:
        return [{"potion_id": r["id"], "max": int(r["maxCharges"])} for r in csv.DictReader(fh)]


def migrate_1_to_2(data: dict) -> dict:
    """Migração v1 -> v2 (save_v2.schema.json; docs/06 seção 6a).
    - characters[].potions (int) -> potion_slots: um slot por linha de potions.csv, com
      charges = o antigo 'potions' no 1º slot (Vida) e o máximo de cargas nos demais; recharge_remaining = 0.
    - characters[].boss_progress = [] (contador do Único por chefe).
    - characters[].equipment.legs = null (11 posições, C-10c).
    - expeditions[].request.potion_heal_fraction sai (a cura vem de potions.csv).
    Nada mais é apagado."""
    slot_defaults = _potion_slot_defaults()

    def conv_char(ch: dict) -> dict:
        out = {}
        old_potions = ch.get("potions", 0)
        for k, v in ch.items():
            if k == "potions":
                slots = []
                for i, d in enumerate(slot_defaults):
                    charges = old_potions if i == 0 else d["max"]
                    slots.append({"potion_id": d["potion_id"], "charges": charges, "recharge_remaining": 0})
                out["potion_slots"] = slots
            elif k == "equipment":
                eq = {}
                for slot, it in v.items():
                    eq[slot] = it
                    if slot == "hands":
                        eq["legs"] = None
                if "legs" not in eq:
                    eq["legs"] = None
                out[k] = eq
            else:
                out[k] = v
        out.setdefault("boss_progress", [])
        return out

    new = {}
    for k, v in data.items():
        if k == "characters":
            new[k] = [conv_char(ch) for ch in v]
        elif k == "expeditions":
            exps = []
            for e in v:
                e2 = dict(e)
                req = dict(e2["request"])
                req.pop("potion_heal_fraction", None)
                snap = dict(req["snapshot"])
                snap["character"] = conv_char(snap["character"])
                req["snapshot"] = snap
                e2["request"] = req
                exps.append(e2)
            new[k] = exps
        elif k == "save_version":
            new[k] = 2
        else:
            new[k] = v
    return new


MIGRATIONS = {1: migrate_1_to_2}


def migrate(data: dict, frm: int, to: int) -> dict:
    for v in range(frm, to):
        if v not in MIGRATIONS:
            raise ValueError(f"falta migração {v}->{v + 1}")
        data = MIGRATIONS[v](data)
    return data


# ---------------------------------------------------------------------------
# Validação de save
# ---------------------------------------------------------------------------
SLOTS = ["main_hand", "off_hand", "head", "body", "hands", "legs", "feet", "amulet", "ring", "ring2", "belt"]


def _items_of_character(ch: dict):
    for slot, it in (ch.get("equipment") or {}).items():
        if it is not None:
            yield f"equipment.{slot}", it


def validate_save(path: str, schema_dir: str, rep: Report, content: Optional[Content] = None) -> Optional[dict]:
    fname = os.path.relpath(path, ROOT) if path.startswith(ROOT) else path
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        rep.err(fname, 0, "E_READ", str(e))
        return None
    try:
        env = json_load_text(text)
    except ValueError as e:
        rep.err(fname, 0, "E_JSON", f"JSON inválido: {e}")
        return None
    if not isinstance(env, dict):
        rep.err(fname, 0, "E_ENVELOPE", "raiz deve ser objeto")
        return None
    if list(env.keys()) != ["format", "save_version", "sha256", "data"]:
        rep.err(fname, 0, "E_ENVELOPE", f"envelope deve ter exatamente format, save_version, sha256, data (nessa ordem); veio {list(env.keys())}")
    if env.get("format") != SAVE_FORMAT_TAG:
        rep.err(fname, 0, "E_FORMAT_TAG", f"format deve ser '{SAVE_FORMAT_TAG}'")
        return None
    schemas = load_save_schemas(schema_dir)
    ver = env.get("save_version")
    if not isinstance(ver, int) or isinstance(ver, bool) or ver < 1:
        rep.err(fname, 0, "E_VERSION", "save_version deve ser inteiro >= 1")
        return None
    if ver not in schemas:
        rep.err(fname, 0, "E_TOO_NEW", f"save_version {ver} desconhecido (esquemas: {sorted(schemas)}) — o jogo recusa sem alterar o arquivo")
        return None
    data = env.get("data")
    sha = env.get("sha256")
    if not isinstance(sha, str) or not re.match(r"^[0-9a-f]{64}$", sha):
        rep.err(fname, 0, "E_CHECKSUM", "sha256 deve ser hex minúsculo de 64 caracteres")
    else:
        try:
            calc = data_sha256(data)
            if calc != sha:
                rep.err(fname, 0, "E_CHECKSUM", f"SHA-256 não confere (arquivo {sha[:12]}…, calculado {calc[:12]}…)")
        except ValueError as e:
            rep.err(fname, 0, "E_JSON", str(e))
    errs: List[str] = []
    jsonschema_validate(env, schemas[ver], schemas[ver], "$", errs)
    for e in errs:
        rep.err(fname, 0, "E_SCHEMA", e)
    if errs or not isinstance(data, dict):
        return data if isinstance(data, dict) else None
    save_semantics(fname, data, ver, rep, content)
    rep.info(f"{fname}: save_version {ver}, {len(data['characters'])} personagem(ns), {len(data['stash'])} item(ns) no baú")
    return data


def save_semantics(fname: str, d: dict, ver: int, rep: Report, content: Optional[Content]) -> None:
    uids: Dict[int, str] = {}

    def reg_item(where: str, it: dict):
        u = int(it["uid"])
        if u == 0:
            rep.err(fname, 0, "E_SAVE", f"{where}: uid 0 é reservado")
        if u in uids:
            rep.err(fname, 0, "E_SAVE", f"{where}: uid {u} repetido (também em {uids[u]})")
        uids[u] = where
        check_item(where, it)

    def check_item(where: str, it: dict):
        if it["rarity"] == "unique" and not it["unique_id"]:
            rep.err(fname, 0, "E_SAVE", f"{where}: raridade unique sem unique_id")
        if it["rarity"] != "unique" and it["unique_id"]:
            rep.err(fname, 0, "E_SAVE", f"{where}: unique_id em item não-único")
        pmax = content.rules.get("polish_max_steps") if content is not None else None
        for a in it["affixes"]:
            if isinstance(pmax, int) and a.get("polish", 0) > pmax:
                rep.err(fname, 0, "E_SAVE", f"{where}: polish {a['polish']} > polish_max_steps {pmax}")
        limit = {"normal": 0, "magic": 2, "rare": 4, "unique": 0}[it["rarity"]]
        if len(it["affixes"]) > limit:
            rep.err(fname, 0, "E_SAVE", f"{where}: {len(it['affixes'])} afixos > máximo {limit} para {it['rarity']}")
        if content is not None:
            if it["base_id"] not in content.ids("item_bases.csv"):
                rep.err(fname, 0, "E_FK", f"{where}: base_id '{it['base_id']}' não existe no conteúdo")
            if it["unique_id"] and it["unique_id"] not in content.ids("uniques.csv"):
                rep.err(fname, 0, "E_FK", f"{where}: unique_id '{it['unique_id']}' não existe")
            for a in it["affixes"]:
                af = content.ids("affixes.csv").get(a["affix_id"])
                if af is None:
                    rep.err(fname, 0, "E_FK", f"{where}: affix_id '{a['affix_id']}' não existe")
                elif not af["minValue"] <= a["value"] <= af["maxValue"]:
                    rep.warn(fname, 0, "W_SAVE", f"{where}: valor {a['value']} fora da faixa atual de {a['affix_id']} (conteúdo mudou?)")

    def check_char(where: str, ch: dict, live: bool):
        if content is not None:
            if ch["class_id"] not in content.ids("classes.csv"):
                rep.err(fname, 0, "E_FK", f"{where}: class_id '{ch['class_id']}' não existe")
            sk = content.ids("skills.csv")
            for s in ch["skills"]:
                if s["skill_id"] not in sk:
                    rep.err(fname, 0, "E_FK", f"{where}: skill '{s['skill_id']}' não existe")
            for s in ch["skill_bar"]:
                if s and s not in sk:
                    rep.err(fname, 0, "E_FK", f"{where}: skill_bar '{s}' não existe")
            for m in ch["conquered_maps"]:
                if m not in content.ids("maps.csv"):
                    rep.err(fname, 0, "E_FK", f"{where}: conquered_maps '{m}' não existe")
            ml = content.rules.get("max_level")
            if isinstance(ml, int) and ch["level"] > ml:
                rep.err(fname, 0, "E_SAVE", f"{where}: level {ch['level']} > max_level {ml}")
        learned = {s["skill_id"] for s in ch["skills"]}
        for s in ch["skill_bar"]:
            if s and s not in learned:
                rep.err(fname, 0, "E_SAVE", f"{where}: skill_bar tem '{s}' que não está em skills")
        for slot, it in (ch.get("equipment") or {}).items():
            if it is None:
                continue
            if live:
                reg_item(f"{where}.equipment.{slot}", it)
            else:
                check_item(f"{where}.equipment.{slot}", it)

    for i, ch in enumerate(d["characters"]):
        check_char(f"characters[{i}]", ch, True)
    for i, it in enumerate(d["stash"]):
        reg_item(f"stash[{i}]", it)
    nxt = int(d["next_item_uid"])
    if uids and nxt <= max(uids):
        rep.err(fname, 0, "E_SAVE", f"next_item_uid {nxt} <= maior uid em uso ({max(uids)})")
    for i, ch in enumerate(d["characters"]):
        for j, it in enumerate(ch.get("backpack") or []):
            check_item(f"characters[{i}].backpack[{j}]", it)
    bb = d.get("vendor_buyback") or []
    bslots = content.rules.get("vendor_buyback_slots") if content is not None else None
    if isinstance(bslots, int) and len(bb) > bslots:
        rep.err(fname, 0, "E_SAVE", f"vendor_buyback tem {len(bb)} itens > vendor_buyback_slots {bslots}")
    for j, e in enumerate(bb):
        check_item(f"vendor_buyback[{j}].item", e["item"])
        if e["paid"] < 0:
            rep.err(fname, 0, "E_SAVE", f"vendor_buyback[{j}]: paid negativo")
    cur_ids = [c["id"] for c in d["currencies"]]
    if len(cur_ids) != len(set(cur_ids)):
        rep.err(fname, 0, "E_SAVE", "currencies com id repetido")
    if content is not None:
        cv = content.meta.get("content_version")
        if isinstance(cv, int) and d["content_version"] > cv:
            rep.err(fname, 0, "E_TOO_NEW", f"content_version do save ({d['content_version']}) > do jogo ({cv})")
        mc = content.rules.get("charges_max")
        if isinstance(mc, int) and d["marker_charges"] > mc:
            rep.err(fname, 0, "E_SAVE", f"marker_charges {d['marker_charges']} > charges_max {mc}")
    if len(d["expeditions"]) > d["expedition_slots"]:
        rep.err(fname, 0, "E_SAVE", "mais expedições que expedition_slots")
    running = [e for e in d["expeditions"] if e["status"] == "running"]
    if len(running) > 1:
        rep.err(fname, 0, "E_SAVE", "mais de 1 expedição running (regra 7: um por vez)")
    for i, e in enumerate(d["expeditions"]):
        w = f"expeditions[{i}]"
        if e["status"] == "none":
            continue
        if not 0 <= e["character_index"] < len(d["characters"]):
            rep.err(fname, 0, "E_SAVE", f"{w}: character_index {e['character_index']} fora do vetor characters")
        req = e["request"]
        if req["effective_seconds"] > req["duration_hours"] * 3600:
            rep.err(fname, 0, "E_SAVE", f"{w}: effective_seconds > duration_hours × 3600")
        if e["status"] == "collected" and e["collected_result_hash"] == "0":
            rep.err(fname, 0, "E_SAVE", f"{w}: collected sem collected_result_hash")
        if e["status"] == "running" and e["collected_result_hash"] != "0":
            rep.err(fname, 0, "E_SAVE", f"{w}: running com collected_result_hash != 0")
        if req["content_version"] != req["snapshot"]["content_version"]:
            rep.warn(fname, 0, "W_SAVE", f"{w}: content_version do pedido difere do snapshot")
        if content is not None:
            if req["map_id"] not in content.ids("maps.csv"):
                rep.err(fname, 0, "E_FK", f"{w}: map_id '{req['map_id']}' não existe")
            mr = content.rules.get("max_ai_rules")
            if isinstance(mr, int) and len(req["rules"]) > mr:
                rep.err(fname, 0, "E_SAVE", f"{w}: {len(req['rules'])} regras de IA > max_ai_rules {mr}")
        for j, r in enumerate(req["rules"]):
            if r["action"] == "use_skill" and not r["ref_id"]:
                rep.err(fname, 0, "E_SAVE", f"{w}.rules[{j}]: use_skill sem ref_id")
            if r["condition"] == "effect_missing" and not r["ref_id"]:
                rep.err(fname, 0, "E_SAVE", f"{w}.rules[{j}]: effect_missing sem ref_id")
        check_char(f"{w}.request.snapshot.character", req["snapshot"]["character"], False)


# ---------------------------------------------------------------------------
# Auto-teste (CI): Content/Data + fixtures válidos + inválidos + saves
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Mutações negativas do conteúdo real (docs/13): cada cópia com um defeito DEVE falhar com o código esperado
# ---------------------------------------------------------------------------
def _set_skill_field(text: str, skill_id: str, column: str, value: str) -> str:
    """Troca uma célula de uma linha de skills.csv pelo nome da coluna (a mutação não depende do resto da linha)."""
    lines = text.split("\n")
    header = lines[0].split(",")
    col = header.index(column)
    for n, line in enumerate(lines):
        if line.startswith(skill_id + ","):
            cells = line.split(",")
            cells[col] = value
            lines[n] = ",".join(cells)
    return "\n".join(lines)


MUTATIONS = [
    ("unico_fora_de_tabela_de_chefe", "loot_entries.csv",
     lambda t: t + "loot.crypt.common,unique,unique.empty_throne_maul,5,1,1,1,999,true,,,\n", "E_UNIQUE_TABLE"),
    ("unico_sem_peso_e_sem_chance", "loot_entries.csv",
     lambda t: t.replace("unique.empty_throne_maul,,1,1,1,999,true,0.2,true,5", "unique.empty_throne_maul,,1,1,1,999,true,,,"), "E_WEIGHT"),
    ("idle_manual_sem_amostra", "uniques.csv",
     lambda t: t.replace(",20,manual_estimate", ",0,manual_estimate"), "E_IDLE"),
    ("pocao_barreira_sem_duracao", "potions.csv",
     lambda t: t.replace("barrier,0.3,6,", "barrier,0.3,,"), "E_POTION"),
    ("modificadores_sem_peso", "elite_modifiers.csv",
     lambda t: t.replace("modifier.elite.shield,50", "modifier.elite.shield,0").replace("modifier.elite.swift,50", "modifier.elite.swift,0"), "E_WEIGHT"),
    ("padrao_do_chefe_com_skill_inexistente", "boss_patterns.csv",
     lambda t: t.replace("skill.enemy.guardian_shield_charge", "skill.enemy.guardian_nope"), "E_FK"),
    ("fase_do_chefe_com_limiar_nao_decrescente", "boss_phases.csv",
     lambda t: t.replace("enemy.crypt_guardian,2,0.5", "enemy.crypt_guardian,2,1.0"), "E_BOSS"),
    ("ia_aggro_diferente_do_inimigo", "enemy_ai.csv",
     lambda t: t.replace("enemy.ash_hound,1100", "enemy.ash_hound,900"), "E_ENEMY_AI"),
    ("visual_set_sem_prefixo_vset", "item_bases.csv",
     lambda t: t.replace("vset.starter", "starter"), "E_ID"),
    ("calca_com_dano_de_arma", "item_bases.csv",
     lambda t: t.replace("armor:flat:4,,,,,,,f", "armor:flat:4,9,,,,,,f"), "E_WEAPON"),
    ("invocacao_sem_summonAtFraction", "boss_phases.csv",
     lambda t: t.replace(",0.6,1.1,0.5", ",0.6,1.1,"), "E_BOSS"),
    ("patrulha_acima_da_perseguicao", "enemies.csv",
     lambda t: "\n".join(l[:-3] + "1.5" if l.startswith("enemy.hollow_sentinel,") else l for l in t.split("\n")), "E_RANGE"),
    ("margem_de_tela_removida", "rules.csv",
     lambda t: t.replace("require_on_screen_margin,100\n", ""), "E_KEY_MISSING"),
    ("regra_obrigatoria_removida", "rules.csv",
     lambda t: t.replace("potion_lockout,1.0\n", ""), "E_KEY_MISSING"),
    ("capacidade_da_mochila_removida", "rules.csv",
     lambda t: t.replace("inventory_capacity,40\n", ""), "E_KEY_MISSING"),
    ("arma_bloqueada", "rules.csv",
     lambda t: t.replace("equip_slot_main_hand,true", "equip_slot_main_hand,false"), "E_RULES"),
    ("chave_do_combo_removida", "rules.csv",
     lambda t: t.replace("combo_window,0.5" + chr(10), ""), "E_KEY_MISSING"),
    ("janela_do_combo_fora_da_faixa", "rules.csv",
     lambda t: t.replace("attack_buffer,0.22", "attack_buffer,9"), "E_RANGE"),
    ("kit_com_golpe_de_outra_classe", "basic_kits.csv",
     lambda t: t.replace("class.archer,skill.archer.quick_shot|skill.archer.quick_shot|skill.archer.fan_shot", "class.archer,skill.archer.quick_shot|skill.mage.arcane_dart|skill.archer.fan_shot"), "E_KIT"),
    ("kit_com_defesa_sem_tag_guard", "basic_kits.csv",
     lambda t: t.replace("effect.guarding.archer", "effect.charging.archer"), "E_KIT"),
    ("kit_com_corrente_de_4_golpes", "basic_kits.csv",
     lambda t: t.replace("skill.mage.arcane_dart|skill.mage.arcane_dart|skill.mage.arcane_orb", "skill.mage.arcane_dart|skill.mage.arcane_dart|skill.mage.arcane_orb|skill.mage.arcane_dart"), "E_LIST"),
    ("kit_com_arco_acima_de_360", "basic_kits.csv",
     lambda t: t.replace(",360,0,0.4,", ",400,0,0.4,"), "E_RANGE"),
    ("kit_com_refAttackTime_negativo", "basic_kits.csv",
     lambda t: t.replace("effect.stun|effect.guard_break,25,0,0.9", "effect.stun|effect.guard_break,25,0,-0.9"), "E_RANGE"),
    ("bau_com_prefixo_errado", "chests.csv",
     lambda t: t.replace("chest.crypt.01,", "box.crypt.01,"), "E_ID"),
    ("bau_com_mapa_inexistente", "chests.csv",
     lambda t: t.replace("chest.crypt.02,map.act1.crypt", "chest.crypt.02,map.act1.nope"), "E_FK"),
    ("bau_com_tabela_de_loot_inexistente", "chests.csv",
     lambda t: t.replace("loot.crypt.elite", "loot.crypt.nope", 1), "E_FK"),
    ("bau_com_id_repetido", "chests.csv",
     lambda t: t.replace("chest.crypt.03,", "chest.crypt.02,"), "E_DUP_ID"),
    ("perfuracao_em_golpe_que_nao_e_projetil", "skills.csv",
     lambda t: _set_skill_field(t, "skill.archer.arrow_rain", "pierce", "5"), "E_PIERCE"),
    ("explosao_em_golpe_que_nao_e_projetil", "skills.csv",
     lambda t: _set_skill_field(t, "skill.mage.frost_nova", "explosionRadius", "100"), "E_EXPLOSION"),
    ("leque_sem_angulo", "skills.csv",
     lambda t: t.replace("1100,,3,,,false,,,,,,,,1,28,", "1100,,3,,,false,,,,,,,,1,,"), "E_FAN"),
    ("craft_costs_sem_a_operacao_polish", "craft_costs.csv",
     lambda t: chr(10).join(l for l in t.split(chr(10)) if not l.startswith("craft.polish.")), "E_CRAFT"),
    ("craft_costs_com_op_invalido", "craft_costs.csv",
     lambda t: t.replace("craft.refine.normal,refine,", "craft.refine.normal,upgrade,"), "E_ENUM"),
    ("craft_costs_reforge_em_raridade_any", "craft_costs.csv",
     lambda t: t.replace("craft.reforge.rare,reforge,rare,", "craft.reforge.rare,reforge,any,"), "E_CRAFT"),
    ("craft_costs_com_par_repetido", "craft_costs.csv",
     lambda t: t + "craft.polish.9,polish,any,3,1,0" + chr(10), "E_CRAFT"),
    ("vendor_stock_com_carryCap_diferente_da_regra", "vendor_stock.csv",
     lambda t: t.replace("stack,50,3", "stack,50,5"), "E_VENDOR"),
    ("afixo_com_craftInscription_invalido", "affixes.csv",
     lambda t: t.replace("affix.sturdy,prefix,life,flat,,10,25,1,10,head|body|hands|legs|feet|off_hand,life,true", "affix.sturdy,prefix,life,flat,,10,25,1,10,head|body|hands|legs|feet|off_hand,life,sim"), "E_TYPE"),
    ("reforge_mult_cap_abaixo_de_1", "rules.csv",
     lambda t: t.replace("reforge_mult_cap,3.0", "reforge_mult_cap,0.5"), "E_RANGE"),
    ("base_em_posicao_bloqueada", "rules.csv",
     lambda t: t.replace("equip_slot_head,true", "equip_slot_head,false"), "E_SLOT_LOCKED"),
]


def mutation_self_test(schema_dir: str, quiet: bool) -> int:
    import shutil
    import tempfile
    print("== mutações negativas do conteúdo real (cada uma deve falhar com o código esperado)")
    failures = 0
    for name, fname, mutate, code in MUTATIONS:
        tmp = tempfile.mkdtemp(prefix="mut_")
        try:
            dst = os.path.join(tmp, "Data")
            shutil.copytree(DEFAULT_DATA, dst)
            path = os.path.join(dst, fname)
            with open(path, encoding="utf-8", newline="") as fh:
                before = fh.read()
            after = mutate(before)
            if after == before:
                print(f"   !! mutação '{name}' não alterou {fname}")
                failures += 1
                continue
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(after)
            rep = Report(f"mutação {name}")
            validate_content(dst, schema_dir, rep)
            hit = [e for e in rep.errors if e[2] == code]
            if hit:
                if not quiet:
                    print(f"   ok: {name} falhou como esperado [{code}]")
            else:
                print(f"   !! {name}: esperado [{code}], veio {sorted({e[2] for e in rep.errors})}")
                failures += 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return failures


def self_test(schema_dir: str, quiet: bool) -> int:
    failures = 0
    print("### validate_data.py --self-test")
    # 1. conteúdo real
    rep = Report(f"Content/Data ({os.path.relpath(DEFAULT_DATA, ROOT)})")
    content = validate_content(DEFAULT_DATA, schema_dir, rep)
    check_lock(content, DEFAULT_DATA, rep)
    rep.print(quiet=quiet)
    failures += 0 if rep.ok else 1
    # 2. fixtures válidos
    rep = Report(f"fixtures válidos ({os.path.relpath(TEST_DATA, ROOT)})")
    tcontent = validate_content(TEST_DATA, schema_dir, rep)
    rep.print(quiet=quiet)
    failures += 0 if rep.ok else 1
    # 3. fixtures inválidos: cada um DEVE falhar com o código/linha esperados
    inv = os.path.join(TEST_DATA, "invalid")
    for case in sorted(os.listdir(inv)) if os.path.isdir(inv) else []:
        d = os.path.join(inv, case)
        if not os.path.isdir(d):
            continue
        rep = Report(f"fixture inválido invalid/{case} (deve falhar)")
        validate_content(d, schema_dir, rep)
        exp_path = os.path.join(d, "expected_error.json")
        exp = json.load(open(exp_path, encoding="utf-8")) if os.path.isfile(exp_path) else None
        rep.print(quiet=True)
        if rep.ok:
            print("   !! esperado falhar, mas passou")
            failures += 1
        elif exp:
            hit = [e for e in rep.errors if e[0] == exp["table"] and e[1] == exp["line"] and e[2] == exp["code"]]
            if not hit:
                print(f"   !! erro esperado não encontrado: {exp}")
                failures += 1
            else:
                print(f"   ok: falhou como esperado ({exp['table']}:{exp['line']} [{exp['code']}])")
    # 4. saves
    saves = os.path.join(TEST_DATA, "saves")
    if os.path.isdir(saves):
        for f in sorted(os.listdir(saves)):
            if not f.endswith(".json"):
                continue
            rep = Report(f"save saves/{f}")
            validate_save(os.path.join(saves, f), schema_dir, rep, tcontent)
            rep.print(quiet=quiet)
            failures += 0 if rep.ok else 1
        for sub in ("future", "invalid"):
            sd = os.path.join(saves, sub)
            for f in sorted(os.listdir(sd)) if os.path.isdir(sd) else []:
                if not f.endswith(".json"):
                    continue
                rep = Report(f"save saves/{sub}/{f}" + (" (deve falhar)" if sub == "invalid" else ""))
                validate_save(os.path.join(sd, f), schema_dir, rep, tcontent)
                rep.print(quiet=quiet)
                if sub == "invalid":
                    if rep.ok:
                        print("   !! esperado falhar, mas passou")
                        failures += 1
                    else:
                        print("   ok: falhou como esperado")
                else:
                    failures += 0 if rep.ok else 1
        # 5. migração de referência v1 -> v2: o resultado bate com o objeto "data" esperado
        #    (v2 ainda não está ativa no core; por isso o esperado é só dado, sem esquema de v2)
        v1 = os.path.join(saves, "save_v1.json")
        v2 = os.path.join(saves, "migration", "v1_to_v2_expected.json")
        if os.path.isfile(v1) and os.path.isfile(v2):
            d1 = json_load_text(open(v1, encoding="utf-8").read())["data"]
            d2 = json_load_text(open(v2, encoding="utf-8").read())
            same = canonical(migrate(d1, 1, 2)) == canonical(d2)
            print(f"== migração de referência v1->v2: {'OK (igual a migration/v1_to_v2_expected.json)' if same else 'FALHOU (difere)'}")
            failures += 0 if same else 1
    failures += mutation_self_test(schema_dir, quiet)
    print(f"### resultado: {'OK' if failures == 0 else f'{failures} falha(s)'}")
    return 0 if failures == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Valida CSV de conteúdo e saves do Echoes of the Shatter (docs/tecnico/06_dados.md).")
    ap.add_argument("--data", action="append", help="pasta com os CSV (padrão: EchoesOfTheShatter/Content/Data). Pode repetir.")
    ap.add_argument("--schemas", default=DEFAULT_SCHEMAS, help="pasta dos esquemas")
    ap.add_argument("--expect-fail", action="store_true", help="inverte o resultado: sucesso se houver erro (testes negativos)")
    ap.add_argument("--save", action="append", help="arquivo de save JSON a validar. Pode repetir.")
    ap.add_argument("--content", help="pasta de CSV para checar IDs do save (padrão: a primeira --data, se houver)")
    ap.add_argument("--update-lock", action="store_true", help="grava content_lock.json (usar só ao publicar uma release)")
    ap.add_argument("--self-test", action="store_true", help="valida Content/Data, todos os fixtures e saves de tests/data")
    ap.add_argument("--quiet", action="store_true", help="omite linhas 'info'")
    a = ap.parse_args(argv)
    try:
        if a.self_test:
            return self_test(a.schemas, a.quiet)
        overall_ok = True
        data_dirs = a.data or ([] if a.save else [DEFAULT_DATA])
        contents: Dict[str, Content] = {}
        for d in data_dirs:
            d = os.path.abspath(d)
            rep = Report(f"dados: {os.path.relpath(d, ROOT) if d.startswith(ROOT) else d}")
            c = validate_content(d, a.schemas, rep)
            check_lock(c, d, rep)
            contents[d] = c
            rep.print(quiet=a.quiet)
            overall_ok &= rep.ok
            if a.update_lock and rep.ok:
                print(f"   lock gravado: {update_lock(c, d)}")
        content = None
        if a.save:
            cdir = os.path.abspath(a.content) if a.content else (os.path.abspath(data_dirs[0]) if data_dirs else None)
            if cdir:
                if cdir not in contents:
                    crep = Report("conteúdo para o save")
                    contents[cdir] = validate_content(cdir, a.schemas, crep)
                    if not crep.ok:
                        crep.print(quiet=a.quiet)
                content = contents[cdir]
            for s in a.save:
                rep = Report(f"save: {s}")
                validate_save(os.path.abspath(s), a.schemas, rep, content)
                rep.print(quiet=a.quiet)
                overall_ok &= rep.ok
        if a.expect_fail:
            print("(--expect-fail) " + ("falhou como esperado" if not overall_ok else "ERRO: esperado falhar, mas passou"))
            return 0 if not overall_ok else 1
        return 0 if overall_ok else 1
    except SchemaError as e:
        print(f"erro de esquema: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
