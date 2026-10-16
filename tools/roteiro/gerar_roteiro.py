#!/usr/bin/env python3
"""Gera o HTML do roteiro (página para compartilhar) a partir dos docs atuais do repositório.

A página junta os documentos de docs/ e as artes aprovadas. É publicada como artifact
no claude.ai (https://claude.ai/artifact/5G5WBocgrp8NAeLKiF9FP8); para atualizar, gere
numa pasta do scratchpad e republique no mesmo URL, com img/*.jpg em `files`.

Uso (Python do venv, que tem Pillow):
    D:/openclaude/_trabalho-claude/venv/Scripts/python.exe tools/roteiro/gerar_roteiro.py [--saida PASTA]

Saída: PASTA/index.html e PASTA/img/*.jpg (padrão: docs/roteiro/, ignorada pelo git).
"""
import argparse
import html
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
APROV = RAIZ / "docs" / "arte" / "referencias-geracao" / "aprovadas"
PAINEL_URL = "https://claude.ai/artifact/7Kzo46Eyy8cQjF9HhuWMXg"
LARGURA, QUALIDADE = 1280, 82
# Mesmos nomes de grupo da galeria do painel (tools/painel/gerar_painel.py).
GRUPOS_ARTE = {"referencias": "Referências", "modelagem": "Modelagem", "modulares": "Heróis modulares",
               "cenario": "Cenário da Cripta", "modelos3d": "Modelos 3D"}

# (grupo, [(id, caminho relativo, rótulo curto no menu)])
DOCS = [
    ("Visão e plano", [
        ("plano-steam", "docs/00_plano_existente.md", "Plano Steam v2.0"),
        ("requisitos", "docs/02_requisitos.md", "Requisitos e critérios de aceite"),
        ("etapas", "docs/15_etapas.md", "Etapas do projeto"),
        ("plano-execucao", "docs/01_plano_execucao.md", "Plano de execução"),
        ("proximos-passos", "docs/07_proximos_passos.md", "Próximos passos"),
        ("regras", "CLAUDE.md", "Regras do projeto"),
    ]),
    ("Design e conteúdo", [
        ("pendencias-design", "docs/13_design_pendencias.md", "Decisões de design"),
        ("layout-cripta", "docs/14_layout_cripta.md", "Layout da Cripta Partida"),
        ("conteudo", "docs/05_conteudo.md", "Conteúdo do protótipo"),
    ]),
    ("Arte", [
        ("decisoes-visual", "docs/08_decisoes_visual_3d.md", "Motor, renderização e arte"),
        ("design-system", "docs/03_design_system.md", "Design system e interface"),
        ("regua-sb", "docs/arte/regua_spell_brigade.md", "Régua técnica dos modelos"),
        ("referencias", "docs/arte/referencias-geracao/README.md", "Referências aprovadas"),
    ]),
    ("Técnico", [
        ("arquitetura", "docs/04_arquitetura.md", "Arquitetura e contratos"),
        ("dados", "docs/06_dados.md", "Dados e save"),
        ("contrato", "docs/09_mudancas_contrato.md", "Mudanças de contrato"),
        ("qa", "docs/10_qa.md", "Plano de QA"),
        ("revisao-codigo", "docs/11_revisao_codigo.md", "Revisão de código"),
    ]),
    ("Pesquisa", [
        ("modelos-gratis", "docs/pesquisa/modelos_3d_gratis.md", "Modelos 3D grátis"),
        # stefan_3d_ai.md fica de fora: tem nome e perfis de uma pessoa real.
    ]),
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def titulos_aprovadas() -> dict:
    """Legenda de cada imagem, tirada da tabela do README da pasta."""
    out = {}
    for linha in (APROV.parent / "README.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(\d\d_[\w]+\.png)\s*\|\s*(.+?)\s*\|\s*$", linha)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def converter(origem: Path, destino: Path) -> None:
    if destino.exists() and destino.stat().st_mtime >= origem.stat().st_mtime:
        return
    from PIL import Image
    with Image.open(origem) as im:
        im = im.convert("RGB")
        if im.width > LARGURA:
            im = im.resize((LARGURA, round(im.height * LARGURA / im.width)), Image.LANCZOS)
        im.save(destino, "JPEG", quality=QUALIDADE, optimize=True, progressive=True)


def imagens(saida: Path, estado: dict) -> list:
    """Pranchas de referência (legenda no README) e a galeria aprovada do painel (docs/progresso/estado.json)."""
    pasta = saida / "img"
    pasta.mkdir(parents=True, exist_ok=True)
    lista = []
    for png, legenda in sorted(titulos_aprovadas().items()):
        if (APROV / png).exists():
            lista.append(("referencias", APROV / png, legenda, ""))
    for it in estado.get("galeria", []):
        origem = RAIZ / it["arquivo"]
        if it.get("estado") == "aprovada" and origem.exists():
            lista.append((it["grupo"], origem, it["titulo"], it.get("detalhe", "")))
    saida_lista = []
    for grupo, origem, legenda, detalhe in lista:
        destino = pasta / f"{grupo}_{origem.stem}.jpg"
        converter(origem, destino)
        saida_lista.append({"grupo": GRUPOS_ARTE.get(grupo, grupo), "src": "img/" + destino.name,
                            "legenda": legenda, "detalhe": detalhe})
    usados = {a["src"].removeprefix("img/") for a in saida_lista}
    for velho in pasta.glob("*.jpg"):
        if velho.name not in usados:
            velho.unlink()
    return saida_lista


def carregar_docs() -> tuple:
    grupos, textos = [], {}
    for grupo, itens in DOCS:
        entradas = []
        for ident, rel, rotulo in itens:
            caminho = RAIZ / rel
            if not caminho.exists():
                print(f"aviso: {rel} não existe, ignorado")
                continue
            texto = caminho.read_text(encoding="utf-8")
            m = re.search(r"^# (.+)$", texto, re.M)
            entradas.append({"id": ident, "arquivo": rel, "rotulo": rotulo,
                             "titulo": m.group(1).strip() if m else rotulo,
                             "modificado": git("log", "-1", "--format=%cs", "--", rel)})
            textos[ident] = texto
        grupos.append({"grupo": grupo, "docs": entradas})
    return grupos, textos


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", type=Path, default=RAIZ / "docs" / "roteiro")
    saida = ap.parse_args().saida.resolve()
    saida.mkdir(parents=True, exist_ok=True)

    grupos, textos = carregar_docs()
    estado = json.loads((RAIZ / "docs" / "progresso" / "estado.json").read_text(encoding="utf-8"))
    dados = {
        "grupos": grupos,
        "textos": textos,
        "perguntas": estado.get("pendencias_dono", []),
        "arte": imagens(saida, estado),
        "commit": git("log", "-1", "--format=%h|%cs|%s").split("|", 2),
        "gerado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "painel": PAINEL_URL,
    }
    payload = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    modelo = (Path(__file__).with_name("modelo.html")).read_text(encoding="utf-8")
    (saida / "index.html").write_text(modelo.replace("/*__DADOS__*/{}", payload), encoding="utf-8")
    total = sum(f.stat().st_size for f in saida.rglob("*") if f.is_file())
    print(f"ok: {saida / 'index.html'} ({len(textos)} docs, {len(dados['arte'])} imagens, {total / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
