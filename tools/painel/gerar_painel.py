#!/usr/bin/env python3
"""Gera docs/progresso/painel.html a partir de estado.json, git log e miniaturas.

Uso (Python do venv, que tem Pillow):
    D:/openclaude/_trabalho-claude/venv/Scripts/python.exe tools/painel/gerar_painel.py
"""
import html
import json
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PROG = RAIZ / "docs" / "progresso"
THUMBS = PROG / "thumbs"
APROV = RAIZ / "docs" / "arte" / "referencias-geracao" / "aprovadas"
PREVIAS = RAIZ / "art-src" / "graybox" / "previews"
VOTACAO = RAIZ / "tools" / "votacao"
ROTEIRO_URL = "https://claude.ai/artifact/5G5WBocgrp8NAeLKiF9FP8"
LARGURA, QUALIDADE = 480, 80
# Cores da votação (tools/votacao/votacao.css) a partir dos tokens do painel.
CSS_VOTACAO = (".votacao{--v-fundo:var(--media);--v-borda:var(--clara);--v-texto:var(--perg);--v-mut:var(--clara);"
               "--v-nome:var(--ouro-claro);--v-destaque:var(--ouro);--v-campo:var(--noite);--v-botao:var(--ouro);--v-botao-txt:var(--noite)}"
               ".v-tit{font-family:var(--f-txt)}.topo a{color:var(--ouro-claro)}")

e = html.escape


def miniatura(origem: Path, nome: str) -> str:
    destino = THUMBS / (nome + ".jpg")
    if not destino.exists() or destino.stat().st_mtime < origem.stat().st_mtime:
        from PIL import Image
        with Image.open(origem) as im:
            im = im.convert("RGB")
            h = round(im.height * LARGURA / im.width)
            im.resize((LARGURA, h), Image.LANCZOS).save(destino, "JPEG", quality=QUALIDADE, optimize=True)
    return "thumbs/" + destino.name


def titulos_aprovadas() -> dict:
    """Título de cada imagem, tirado da tabela do README da pasta."""
    out = {}
    for linha in (APROV.parent / "README.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(\d\d_[\w]+\.png)\s*\|\s*(.+?)\s*\|\s*$", linha)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def git_log() -> list:
    try:
        r = subprocess.run(["git", "log", "--date=short", "--format=%h|%ad|%s"], cwd=RAIZ,
                           capture_output=True, text=True, encoding="utf-8", timeout=30)
        return [l.split("|", 2) for l in r.stdout.splitlines() if l.count("|") >= 2]
    except Exception:
        return []


def pilula(estado: str, legenda: dict) -> str:
    return f'<span class="pil {e(estado)}"><i></i>{e(legenda.get(estado, estado))}</span>'


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Lilita+One&family=Source+Sans+3:wght@400;600&display=swap');
:root{--noite:%(pedra_noite)s;--escura:%(pedra_escura)s;--media:%(pedra_media)s;--clara:%(pedra_clara)s;--ouro:%(dourado)s;--ouro-claro:%(dourado_claro)s;--carm:%(carmesim)s;--lava:%(perigo)s;--perg:%(pergaminho)s;--verde:#6FB36A;--azul:#6A9BD9;
--f-tit:'Cinzel',Georgia,serif;--f-txt:'Source Sans 3',system-ui,sans-serif;--f-num:'Lilita One','Cinzel',sans-serif}
*{box-sizing:border-box}
:root{color-scheme:dark}
body{margin:0;background:var(--noite);color:var(--perg);font:16px/1.5 var(--f-txt);
padding:24px max(16px,env(safe-area-inset-right,0px)) 48px max(16px,env(safe-area-inset-left,0px))}
main{max-width:1080px;margin:0 auto}
h1,h2,h3{font-family:var(--f-tit);color:var(--ouro-claro);margin:0;line-height:1.2}
h1{font-size:clamp(1.6rem,5vw,2.4rem)}
h2{font-size:1.3rem;margin:36px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--media)}
h3{font-size:1.05rem;color:var(--perg)}
p{margin:4px 0}.mut{color:var(--clara)}.peq{font-size:.85rem}
.topo{border:2px solid var(--ouro);border-radius:6px 18px 6px 18px;background:var(--escura);padding:18px 20px}
.topo .sub{color:var(--perg);margin-top:6px}
.faixa{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-top:14px}
.faixa a{display:block;text-decoration:none;color:var(--perg);background:var(--media);border-left:5px solid var(--clara);border-radius:4px;padding:8px 10px;font-size:.9rem}
.faixa a.concluido{border-color:var(--verde)}.faixa a.nuvem{border-color:var(--azul)}.faixa a.andamento{border-color:var(--ouro)}
.faixa a.aguardando_dono{border-color:var(--lava)}.faixa a.bloqueado{border-color:var(--carm)}
.faixa b{display:block;font-family:var(--f-tit);font-size:.85rem}
.dest{margin:12px 0 0;padding:10px 14px;border:2px solid var(--verde);border-radius:4px;background:var(--media)}.dest b{display:block;color:var(--ouro-claro);overflow-wrap:anywhere}.dest span{display:block;font-size:.85rem;margin-top:4px}
.etapas{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:14px}
.etapa{background:var(--media);border-radius:4px;padding:8px 10px;font-size:.85rem}.etapa b{display:block;font-family:var(--f-tit);color:var(--ouro-claro)}.etapa.concluido{border-top:4px solid var(--verde)}.etapa.andamento{border-top:4px solid var(--ouro)}.etapa.pendente{border-top:4px dashed var(--clara)}
.pend{grid-column:1/-1}.perg{font-weight:600;font-size:1.05rem;color:var(--ouro-claro);border-left:4px solid var(--lava);padding-left:10px;margin:8px 0}
.pend summary{cursor:pointer;color:var(--ouro);font-size:.9rem}.pend details p{margin:6px 0}
.opcs{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px;margin:10px 0}.opc{background:var(--media);border:1px solid var(--clara);border-radius:4px;padding:8px 10px;font-size:.9rem}.opc b{display:block;color:var(--ouro-claro);margin-bottom:2px}
.cont{display:flex;flex-wrap:wrap;gap:16px;margin-top:14px}
.cont div{font-family:var(--f-num);font-size:1.7rem;color:var(--ouro-claro)}.cont span{display:block;font:.8rem var(--f-txt);color:var(--clara)}
.pil{display:inline-flex;align-items:center;gap:6px;font-size:.78rem;font-weight:600;padding:2px 10px 2px 8px;border-radius:99px;background:var(--media);border:1px solid var(--clara);white-space:nowrap}
.pil i{width:10px;height:10px;background:var(--clara);display:inline-block}
.pil.concluido i{background:var(--verde);border-radius:50%%}
.pil.nuvem i{background:var(--azul);border-radius:50%% 50%% 50%% 0}
.pil.andamento i{background:var(--ouro);clip-path:polygon(0 0,100%% 50%%,0 100%%)}
.pil.aguardando_dono{border-color:var(--lava);color:var(--lava)}.pil.aguardando_dono i{background:var(--lava);transform:rotate(45deg)}
.pil.pendente i{background:transparent;border:2px solid var(--clara);border-radius:50%%}
.pil.bloqueado{border-color:var(--carm)}.pil.bloqueado i{background:var(--carm)}
.grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.card{background:var(--escura);border:1px solid var(--media);border-radius:4px 14px 4px 14px;padding:14px 16px}
.card.alerta{border-color:var(--lava)}
.card header{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:6px}
.card ul{margin:8px 0 0;padding-left:18px}.card li{margin:2px 0}
.arq{display:block;color:var(--clara);font-size:.78rem;overflow-wrap:anywhere}
.prox{margin-top:10px;padding-top:8px;border-top:1px dashed var(--media);font-size:.9rem}.prox b{color:var(--ouro)}
.marcos{list-style:none;padding:0;margin:0;display:grid;gap:6px}
.marcos li{display:flex;gap:10px;align-items:center;background:var(--escura);border:1px solid var(--media);border-radius:4px;padding:8px 12px}
.marcos li i{flex:none;width:14px;height:14px;border:2px solid var(--clara);border-radius:50%%}
.marcos li.ok i{background:var(--verde);border-color:var(--verde)}
.linha{list-style:none;margin:0;padding:0 0 0 14px;border-left:2px solid var(--media)}
.linha li{position:relative;padding:4px 0 8px 14px}.linha li:before{content:"";position:absolute;left:-21px;top:12px;width:10px;height:10px;background:var(--ouro);transform:rotate(45deg)}
.linha code{color:var(--ouro);font-size:.8rem}.linha .dt{color:var(--clara);font-size:.8rem;margin-left:6px}
.abas{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.abas button{font:600 .9rem var(--f-txt);color:var(--perg);background:var(--media);border:1px solid var(--clara);border-radius:99px;padding:6px 14px;cursor:pointer}
.abas button[aria-pressed=true]{background:var(--ouro);color:var(--noite);border-color:var(--ouro)}
.gal{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.gal figure{margin:0;background:var(--escura);border:1px solid var(--media);border-radius:4px;overflow:hidden}
.gal img{display:block;width:100%%;height:auto;aspect-ratio:3/2;object-fit:cover;background:var(--media)}
.gal figcaption{padding:8px 10px;font-size:.85rem}.gal figcaption b{display:block;color:var(--ouro-claro)}
.gal figure.ag{border-color:var(--ouro)}
.tab{overflow-x:auto}
table{border-collapse:collapse;width:100%%}td,th{text-align:left;padding:6px 10px;border-bottom:1px solid var(--media);vertical-align:top}th{color:var(--ouro)}
[hidden]{display:none!important}
@media (max-width:420px){.grade{grid-template-columns:1fr}.gal{grid-template-columns:1fr 1fr}}
"""

JS = """
(function(){var b=document.querySelectorAll('.abas button'),f=document.querySelectorAll('.gal figure');
b.forEach(function(x){x.addEventListener('click',function(){var k=x.dataset.f;
b.forEach(function(y){y.setAttribute('aria-pressed',y===x)});
f.forEach(function(g){g.hidden=!(k==='todas'||g.dataset.k===k)})})})})();
"""


def main() -> None:
    THUMBS.mkdir(parents=True, exist_ok=True)
    estado = json.loads((PROG / "estado.json").read_text(encoding="utf-8"))
    tokens = json.loads((RAIZ / "docs" / "arte" / "03_design_tokens.json").read_text(encoding="utf-8"))["color"]["base"]
    leg = estado["meta"]["legenda_estados"]
    setores = estado["setores"]
    commits = git_log()

    # Galeria
    titulos = titulos_aprovadas()
    aprov = []
    for nome in sorted(titulos):
        origem = APROV / nome
        if origem.exists():
            desc = titulos[nome]
            tit, _, resto = desc.partition(":")
            aprov.append((miniatura(origem, origem.stem), tit.strip() if resto else desc, resto.strip(), nome))
    GRUPOS = [("referencias", "Referências"), ("modelagem", "Modelagem"), ("modulares", "Heróis modulares"),
              ("aguardando", "Aguardando aprovação"), ("nojogo", "No jogo"), ("cenario", "Cenário da Cripta"), ("modelos3d", "Modelos 3D"), ("graybox", "Graybox")]
    itens = [("referencias", "aprovada", miniatura(APROV / n, Path(n).stem), (t.partition(":")[0].strip() if ":" in t else t),
              t.partition(":")[2].strip()) for n, t in sorted(titulos.items()) if (APROV / n).exists()]
    for it in estado.get("galeria", []):
        origem = RAIZ / it["arquivo"]
        if origem.exists():
            itens.append((it["grupo"], it["estado"], miniatura(origem, it["grupo"] + "_" + origem.stem), it["titulo"], it.get("detalhe", "")))
    aprov = itens

    cont = {}
    for s in setores:
        cont[s["estado"]] = cont.get(s["estado"], 0) + 1
    feitos = sum(1 for m in estado["marcos"] if m["feito"])

    o = []
    o.append("<title>Painel Echoes of the Shatter</title>")
    o.append('<meta name="claude:viewport-fit-sides" content="cover">')
    o.append("<style>" + CSS % tokens + (VOTACAO / "votacao.css").read_text(encoding="utf-8") + CSS_VOTACAO + "</style>")
    o.append("<main>")
    # Topo + faixa
    o.append('<section class="topo"><h1>Echoes of the Shatter</h1>')
    o.append(f'<p class="sub">{e(estado["meta"]["marco_atual"])}. Atualizado em {e(estado["meta"]["atualizado_em"][8:10])}/{e(estado["meta"]["atualizado_em"][5:7])}/{e(estado["meta"]["atualizado_em"][:4])}.</p>')
    o.append(f'<p class="sub"><a href="#aguardando">Votar nas perguntas</a> · '
             f'<a href="{ROTEIRO_URL}" target="_blank" rel="noopener">Roteiro completo: documentos e artes ↗</a></p>')
    if estado["meta"].get("destaque"):
        o.append(f'<p class="dest"><b>{e(estado["meta"]["destaque"])}</b><span>{e(estado["meta"].get("destaque_detalhe", ""))}</span></p>')
    o.append('<div class="faixa">')
    for s in setores:
        o.append(f'<a class="{e(s["estado"])}" href="#s-{e(s["id"])}"><b>{e(s["nome"])}</b>{e(leg[s["estado"]])}</a>')
    o.append("</div>")
    o.append('<div class="cont">')
    o.append(f'<div>{len(estado["pendencias_dono"])}<span>aguardando você</span></div>')
    o.append(f'<div>{cont.get("nuvem", 0)}<span>sessões na nuvem</span></div>')
    o.append(f'<div>{cont.get("concluido", 0)}/{len(setores)}<span>setores concluídos</span></div>')
    o.append(f'<div>{feitos}/{len(estado["marcos"])}<span>marcos</span></div>')
    o.append("</div>")
    o.append('<div class="etapas">')
    for et in estado.get("etapas", []):
        o.append(f'<div class="etapa {e(et["estado"])}"><b>Etapa {et["n"]}</b>{e(et["titulo"])}<br>{pilula(et["estado"], leg)}</div>')
    o.append("</div></section>")

    # Aguardando
    o.append('<h2 id="aguardando">Aguardando você</h2>')
    # votos e comentários: tools/votacao, banco deste artifact (coleção "votos")
    o.append("<p class='nota'>Clique numa opção para votar e deixe um comentário em cada pergunta. "
             "Os votos de todos aparecem aqui.</p>")
    o.append("<div class='grade'>")
    for p in estado["pendencias_dono"]:
        h = f'<article class="card alerta pend"><h3>{e(p["titulo"])}</h3>'
        if p.get("pergunta"):
            h += f'<p class="perg">{e(p["pergunta"])}</p>'
        else:
            h += f'<p>{e(p["detalhe"])}</p>'
        if p.get("contexto"):
            h += '<details open><summary>Contexto</summary>' + "".join(f"<p>{e(c)}</p>" for c in p["contexto"]) + "</details>"
        if p.get("id") and p.get("opcoes"):
            h += f'<div class="votacao" data-q="{e(p["id"])}"></div>'
        elif p.get("opcoes"):
            h += '<div class="opcs">' + "".join(f'<div class="opc"><b>{e(op["nome"])}</b>{e(op["efeito"])}</div>' for op in p["opcoes"]) + "</div>"
        o.append(h + f'<span class="arq">{e(p["origem"])}</span></article>')
    o.append("</div>")
    votaveis = [{"id": p["id"], "opcoes": p["opcoes"]} for p in estado["pendencias_dono"] if p.get("id") and p.get("opcoes")]

    # Marcos
    o.append("<h2>Marcos</h2><ul class='marcos'>")
    for m in estado["marcos"]:
        o.append(f'<li class="{"ok" if m["feito"] else ""}"><i></i><span>{e(m["titulo"])}</span><span class="mut peq">{"feito" if m["feito"] else "falta"}</span></li>')
    o.append("</ul>")

    # Setores
    o.append("<h2>Setores</h2><div class='grade'>")
    for s in setores:
        o.append(f'<article class="card" id="s-{e(s["id"])}"><header><div><h3>{e(s["nome"])}</h3><span class="mut peq">{e(s["agente"])}</span></div>{pilula(s["estado"], leg)}</header>')
        o.append(f'<p>{e(s["resumo"])}</p><ul>')
        for en in s["entregas"]:
            o.append(f'<li>{e(en["titulo"])}<span class="arq">{e(en["arquivo"])}</span></li>')
        o.append(f'</ul><p class="prox"><b>Próximo passo:</b> {e(s["proximo"])}</p></article>')
    o.append("</div>")

    # Linha do tempo
    o.append(f"<h2>Linha do tempo</h2><ul class='linha'>")
    for h, d, msg in commits:
        o.append(f'<li><code>{e(h)}</code><span class="dt">{e(d[8:10])}/{e(d[5:7])}/{e(d[:4])}</span><br>{e(msg)}</li>')
    o.append("</ul>")

    # Decisões
    o.append("<h2>Decisões tomadas</h2><div class='grade'>")
    for d in estado["decisoes"]:
        o.append(f'<article class="card"><h3>{e(d["titulo"])}</h3><p>{e(d["detalhe"])}</p><span class="arq">{e(d["data"][8:10])}/{e(d["data"][5:7])}/{e(d["data"][:4])}</span></article>')
    o.append("</div>")

    # Galeria
    o.append("<h2>Galeria de arte</h2>")
    o.append(f'<div class="abas"><button data-f="todas" aria-pressed="true">Todas ({len(itens)})</button>')
    for gid, gn in GRUPOS:
        n = sum(1 for i in itens if i[0] == gid)
        if n:
            o.append(f'<button data-f="{gid}" aria-pressed="false">{e(gn)} ({n})</button>')
    o.append('</div><div class="gal">')
    for gid, est, img, tit, det in itens:
        prov = est in ("provisoria", "producao", "aguardando")
        pil = pilula("aguardando_dono", {"aguardando_dono": "Aguardando aprovação"}) if est == "aguardando" else pilula("andamento", {"andamento": "Em produção" if est == "producao" else "Provisório"}) if prov else pilula("concluido", {"concluido": "Aprovada"})
        o.append(f'<figure class="{"ag" if prov else ""}" data-k="{gid}"><img src="{e(img)}" alt="{e(tit)}" loading="lazy"><figcaption><b>{e(tit)}</b>{e(det)}<br>{pil}</figcaption></figure>')
    o.append("</div>")

    # Nuvem
    if estado["nuvem"]:
      o.append("<h2>Sessões na nuvem</h2><div class='grade'>")
    for n in estado["nuvem"]:
      if True:
        o.append(f'<article class="card"><header><h3>{n["n"]}. {e(n["titulo"])}</h3>{pilula("nuvem", leg)}</header>'
                 f'<p class="mut peq">{e(n["setor"])} - iniciada em {e(n["data"][8:10])}/{e(n["data"][5:7])}/{e(n["data"][:4])}</p>'
                 + (f'<p>{e(n["detalhe"])}</p>' if n.get("detalhe") else "") + f'<p class="prox"><b>Resultado:</b> {e(n["saida"])}</p></article>')
    if estado["nuvem"]:
        o.append("</div>")

    # Infra
    o.append("<h2>Infraestrutura</h2><div class='tab'><table><tr><th>Item</th><th>Detalhe</th></tr>")
    for i in estado["infraestrutura"]:
        o.append(f'<tr><td>{e(i["item"])}</td><td>{e(i["detalhe"])}</td></tr>')
    o.append("</table></div></main>")
    o.append("<script>" + JS + "</script>")
    if votaveis:
        dados = json.dumps(votaveis, ensure_ascii=False).replace("</", "<\\/")
        o.append(f'<script type="application/json" id="votacao-dados">{dados}</script>')
        o.append("<script>" + (VOTACAO / "votacao.js").read_text(encoding="utf-8") + "</script>")

    (PROG / "painel.html").write_text("\n".join(o), encoding="utf-8")
    print(f"painel.html: {len(setores)} setores, {len(commits)} commits, {len(itens)} imagens na galeria")


if __name__ == "__main__":
    main()
