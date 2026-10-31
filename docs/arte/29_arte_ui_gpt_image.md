# 29 — Arte da interface pintada com gpt-image (31/10/2026)

Substitui os ícones procedurais do doc 28 (o gerador `tools/arte/gen_icones_habilidade.py` fica só como reserva) e acrescenta as peças da HUD do PR 110. Tudo gerado pelo Codex CLI (gpt-image) no PC do Will, no disco D.

## Estilo (decisão herdada do Jev no doc 28, mantida)
Ícone pintado à mão com glifo central, halo da cor da habilidade e moldura de pedra escura e ferro com fio dourado e quatro rebites. A moldura é a mesma nos 10 ícones (o ícone Tiro serve de referência para os outros). O fundo muda de tom só o suficiente para o halo ler. Cores por habilidade: as da tabela do doc 28.

## Arquivos
- Ícones: `godot/art2d/ui/icone_<id>.png`, 128 px, cantos arredondados com alfa. Mesmos ids do doc 28.
- Peças da HUD (PNG com alfa, fundo magenta removido por `key.py`), versão 2 com os ajustes do Jev, em 2x do tamanho de tela de 1280x720:
  - `hud_globo_moldura.png` 270x270 (tela: 135 px de diâmetro externo, encostado no canto de baixo; escalar a 0,5). Aro de ferro fino, 4 rebites, sem espinhos, reflexo de vidro. O vidro é vazio: o líquido é desenhado por baixo, **recortado pelo círculo de raio 0,859 do raio externo** (r interno = 58 px na tela).
  - `hud_faixa_pedra.png` 1120x150 (tela: 560x75 centrada embaixo, x 360 a 920, y 645 a 720), entre os globos. Bordas finas de ferro e dourado fosco, pedra com veios, reta, sem ornamento subindo ao campo. **9-slice**: margens esquerda e direita 48 px, topo e base 20 px (no arquivo 2x); o miolo repete-se na horizontal.
  - `hud_slot_moldura.png` 96x96 (tela: 56 a 64 px, 6 slots de 60 px com 8 px de intervalo, 388 px de largura total, centrados na faixa), sobreposta ao ícone.
  - `hud_barra_chefe_moldura.png` 1240x146 (tela: 620 px de largura, ~73 px de altura com a caveira de ~36 px acima do centro, y 6 a 79; o campo começa em y 120). **Sem 9-slice**: a caveira central se deformaria, usar em tamanho fixo. Canal interno vazio: o código põe por baixo um fundo escuro e a barra roxa, e o nome serifado vai abaixo da moldura.
- Ícones: luzes dos glifos reduzidas em ~14% (curva só nos realces), a pedido do Jev.
- Maquetes 1280x720 (aproximação sobre capturas antigas, que ainda trazem a HUD velha desenhada; só a arte nova é final): `docs/arte/sprites2d/arte_ui_maquete_sala1.png` e `arte_ui_maquete_chefe.png`. Prévia dos ícones: `arte_ui_icones_previa.png`.

## Como reproduzir
`tools/arte/ui_gpt_image/`: `prompts_icones.json` e `prompts_hud_v2.json` (gerado por `mk_v2.py`) (rodar com `docs/arte/referencias-geracao/scripts/gerar.py`, ajustando os caminhos de referência), `prep.py` (recorte, 128 px e cantos dos ícones), `key.py`, `exporta.py` e `exporta_v2.py` (remoção do magenta, tamanhos da HUD e suavização das luzes dos ícones; rode o `exporta_v2.py` uma vez só sobre os ícones, senão a luz é cortada duas vezes) e `maquete.py`. Python do venv em `D:\openclaude\_trabalho-claude\venv` (Pillow e numpy).

## Pendências
- Ligar as peças em `hud_arte_2d.gd` e `hud_2d.gd`: esse código está no PR 110, ainda não mesclado e já divergente do master. Fazer depois do merge do 110, com as medidas acima, sem deixar a thread da HUD e esta editarem os mesmos arquivos.
- Passar pela revisora e pela Direção visual com o Jev antes do Will ver.
- Efeitos animados (recarga, golpe na barra do chefe): avaliar a skill pixelfx (`ui/health-bar-hit`, `ui/heart-lost`); nada exportado ainda.
