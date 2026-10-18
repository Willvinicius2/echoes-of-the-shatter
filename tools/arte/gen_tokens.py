#!/usr/bin/env python3
"""Gera o arquivo de variáveis USS a partir de docs/arte/03_design_tokens.json.

Regra (docs/arte/03_design_system.md, seção 2.14): "--" + caminho do token em kebab-case
(pontos e sublinhados viram hífens); cor em #RRGGBB ou rgba(); comprimento em px no espaço
de referência 1920x1080; tempo em ms. Os grupos de arte 3D (art3d, juice) não viram variável.

O destino vem do próprio JSON (uss.tokens_file). Ninguém edita o arquivo gerado à mão:
mude o JSON e rode de novo.

Uso (da raiz do repositório):
    python3 tools/arte/gen_tokens.py            # escreve o arquivo
    python3 tools/arte/gen_tokens.py --check    # falha se o arquivo estiver desatualizado

Sem dependências externas.
"""

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOKENS = ROOT / "docs" / "arte" / "03_design_tokens.json"
PROJECT = ROOT / "EchoesOfTheShatter"

# Classe que também recebe as variáveis: o seletor :root do UI Toolkit casa com a raiz do painel,
# e a folha de estilo presa a um UXML nem sempre chega lá. A raiz de cada tela usa esta classe.
THEME_CLASS = ".echoes-theme"

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def kebab(*parts):
    return "-".join(p.replace("_", "-").replace(".", "-") for p in parts if p)


def rgba(hex_color, alpha):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r}, {g}, {b}, {alpha:g})"


def color_vars(node, path, out):
    if isinstance(node, str):
        if HEX.match(node):
            out.append((kebab("color", *path), node.upper()))
        return
    if isinstance(node, dict):
        if "hex" in node and isinstance(node["hex"], str) and HEX.match(node["hex"]):
            if "alpha" in node:
                out.append((kebab("color", *path), rgba(node["hex"], float(node["alpha"]))))
            else:
                out.append((kebab("color", *path), node["hex"].upper()))
            return
        for key, value in node.items():
            if key in ("note", "red_band_rule", "measured_haze", "telegraph_variant", "density"):
                continue
            color_vars(value, path + [key], out)


def build(tokens):
    out = []

    color_vars(tokens.get("color", {}), [], out)

    for style, spec in tokens.get("font", {}).get("styles", {}).items():
        if "size_px" in spec:
            out.append((kebab("font", style, "size"), f"{spec['size_px']}px"))
        if "line_height_px" in spec:
            out.append((kebab("font", style, "line-height"), f"{spec['line_height_px']}px"))

    for key, value in tokens.get("space", {}).items():
        out.append((kebab("space", key), f"{value}px"))

    for key, value in tokens.get("size", {}).items():
        out.append((kebab("size", key), f"{value}px"))

    for key, spec in tokens.get("nine_slice", {}).items():
        if "margin_px" in spec:
            out.append((kebab("slice", key), f"{spec['margin_px']}px"))

    for key, value in tokens.get("motion", {}).items():
        # Tempo: o sufixo _ms sai do nome (motion.ui_fade_ms -> --motion-ui-fade, seção 2.14).
        # Distância: o nome fica inteiro (motion.ui_slide_px -> --motion-ui-slide-px) para não colidir.
        if key.endswith("_ms"):
            out.append((kebab("motion", key[: -len("_ms")]), f"{value}ms"))
        elif key.endswith("_px"):
            out.append((kebab("motion", key), f"{value}px"))

    viewport = tokens.get("viewport", {})
    if "safe_margin" in viewport:
        out.append((kebab("viewport", "safe_margin"), f"{viewport['safe_margin']}px"))

    elevation = tokens.get("elevation", {})
    shadow = elevation.get("text_shadow")
    if isinstance(shadow, dict) and HEX.match(shadow.get("color", "")):
        out.append((kebab("elevation", "text-shadow-color"), rgba(shadow["color"], float(shadow.get("alpha", 1)))))
        out.append((kebab("elevation", "text-shadow-offset-y"), f"{shadow.get('offset_y', 0)}px"))
    if "world_label_outline_px" in elevation:
        out.append((kebab("elevation", "world-label-outline"), f"{elevation['world_label_outline_px']}px"))

    seen = set()
    unique = []
    for name, value in out:
        if name in seen:
            raise SystemExit(f"variável duplicada: --{name}")
        seen.add(name)
        unique.append((name, value))
    return unique


def render(tokens, variables):
    meta = tokens.get("meta", {})
    lines = [
        "/* ARQUIVO GERADO por tools/arte/gen_tokens.py a partir de docs/arte/03_design_tokens.json. */",
        "/* Não edite à mão: mude o JSON e rode o script de novo. */",
        f"/* Tokens {meta.get('name', '')} v{meta.get('version', '')} ({meta.get('date', '')}). */",
        "",
        f":root, {THEME_CLASS} {{",
    ]
    for name, value in variables:
        lines.append(f"    --{name}: {value};")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="falha se o arquivo gerado estiver desatualizado")
    args = parser.parse_args()

    tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
    target_rel = tokens.get("uss", {}).get("tokens_file", "Assets/UI/Styles/Tokens.uss")
    target = PROJECT / target_rel
    text = render(tokens, build(tokens))

    if args.check:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current != text:
            print(f"desatualizado: {target.relative_to(ROOT)} (rode python3 tools/arte/gen_tokens.py)")
            return 1
        print(f"ok: {target.relative_to(ROOT)}")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"escrito: {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
