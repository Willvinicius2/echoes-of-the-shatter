# 29 — Arte da interface pintada com gpt-image (31/10/2026)

Substitui os ícones procedurais do doc 28 (o gerador `tools/arte/gen_icones_habilidade.py` fica só como reserva) e acrescenta as peças da HUD do PR 110. Tudo gerado pelo Codex CLI (gpt-image) no PC do Will, no disco D.

## Estilo (decisão herdada do Jev no doc 28, mantida)
Ícone pintado à mão com glifo central, halo da cor da habilidade e moldura de pedra escura e ferro com fio dourado e quatro rebites. A moldura é a mesma nos 10 ícones (o ícone Tiro serve de referência para os outros). O fundo muda de tom só o suficiente para o halo ler. Cores por habilidade: as da tabela do doc 28.

## Arquivos
- Ícones: `godot/art2d/ui/icone_<id>.png`, 128 px, cantos arredondados com alfa. Mesmos ids do doc 28.
- Peças da HUD (PNG com alfa, fundo magenta removido por `key.py`):
  - `hud_globo_moldura.png` 256x256, anel de ferro e pedra com vidro vazio (o líquido de vida e mana é desenhado pelo código por baixo).
  - `hud_faixa_pedra.png` 1280x147, base da barra de ação, ornamento dourado no centro do topo.
  - `hud_slot_moldura.png` 96x96, moldura vazia para sobrepor ao ícone (seleção, recarga).
  - `hud_barra_chefe_moldura.png` 1024x199, moldura com caveira de chifres; o canal interno é vazio para o preenchimento vermelho.
- Prévias: `docs/arte/sprites2d/arte_ui_icones_previa.png` (128, 64 e 48 px) e `arte_ui_hud_maquete.png` (maquete sobre a sala 1; os globos da maquete têm líquido improvisado, só o anel é arte final).

## Como reproduzir
`tools/arte/ui_gpt_image/`: `prompts_icones.json` e `prompts_hud.json` (rodar com `docs/arte/referencias-geracao/scripts/gerar.py`, ajustando os caminhos de referência), `prep.py` (recorte, 128 px e cantos dos ícones), `key.py` e `exporta.py` (remoção do magenta e tamanhos da HUD). Python do venv em `D:\openclaude\_trabalho-claude\venv` (Pillow e numpy).

## Pendências
- Ligar as peças da HUD em `hud_arte_2d.gd` (hoje a HUD desenha as molduras por código); decisão da thread da HUD.
- Passar pela revisora e pela Direção visual com o Jev antes do Will ver.
- Efeitos animados (recarga, golpe na barra do chefe): avaliar a skill pixelfx (`ui/health-bar-hit`, `ui/heart-lost`); nada exportado ainda.
