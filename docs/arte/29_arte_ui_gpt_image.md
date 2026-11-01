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

## Ícones das 18 habilidades do Arqueiro (31/10/2026)
`tools/arte/ui_gpt_image/prompts_icones_arqueiro.json`: 18 prompts no mesmo molde dos 10 aprovados (moldura de pedra e ferro igual ao ícone Tiro, 128 px depois do `prep.py`). Saída esperada: `godot/art2d/ui/icone_<id>.png` com `<id>` = id da skill em `data2d/habilidades_arqueiro.csv`. Depois de gerar, trocar a coluna `icone` do CSV para o próprio id e acrescentar linhas em `data2d/icones.csv` (o `icones_2d.gd` já prioriza o PNG).

## HUD v3: molduras leves e slots das ativas (31/10/2026)
Decisões do Jev (`jev-latest`, `POST /v1/systemone`, três consultas com capturas; confiança abaixo de 0,5 é provisória):
- Fundo da barra de slots: **slots soltos com friso fino de ferro** (47%, contra 40% slots soltos e 13% faixa justa; provisória). A faixa pintada continua disponível em `hud_layout.csv` (`faixa_modo` 0 = faixa justa em 9-slice, 1 = soltos, 2 = friso).
- Rodapé escuro reduzido a 90 px e 25% (85%); globos de raio 84 para 70 (96%).
- 4 slots grandes de 75 px para Q E F R (94%), ataque e esquiva em slots menores à esquerda (77%; 58 px depois da conferência final); encaixe vazio só com a letra, sem cadeado (92%).
- Recarga com varredura e segundos no centro (42%, provisória); ícone tingido de azul quando falta mana ou ímpeto (66%).
- Barra fina de estamina removida, porque o slot de esquiva já mostra a recarga (57%, provisória; `estamina_barra` = 1 a traz de volta).
- Globo da direita: mana real quando o jogador tem `mana` (runtime de habilidades), ímpeto no guerreiro, trancado nos outros casos.
Código em `hud_2d.gd` (`retangulos_slots`, `conteudo_slots`) e `hud_arte_2d.gd` (`slot`, `encaixe_vazio`, `nove_fatias`, `friso`). Capturas com `godot/scripts2d/tools/captura_hud_variantes_2d.gd`; antes e depois em `/mnt/project-files/hud/v3/`.

## HUD v4: formas recortadas (31/10/2026)
O Will reprovou a v3 por estar "tudo muito quadrado". A v4 troca as caixas por formas recortadas, desenhadas em código (`hud_arte_2d.gd`): slots das ativas em octógono chanfrado com garras de ferro nos chanfros, ataque e esquiva em medalhões redondos, plaquinha de tecla em escudinho, base de pedra em arco com pico central e gema (`faixa_modo` 3), placa da sala com topo ogival, buffs em losango e globos com crista e garras. Jev: a v4 deixou de parecer quadrada (81%) e é melhor que a v3 (95%); o ajuste pedido, ornamento nos globos (45%, provisória), já entrou. Capturas em `/mnt/project-files/hud/v4/`.

## HUD v5: lapidação (1/11/2026)
O Will viu a v4 e disse que melhorou, mas ainda estava quadrada. A v5 troca a barra do chefe por uma lâmina com pontas afiadas, chifres curvos e crista central com caveira (`Arte.barra_chefe`, chamada em `boss_2d.gd`), faz a placa da sala virar estandarte (topo ogival, laterais côncavas, ponta embaixo), põe chifres de ferro nos globos, move o texto de ajuda para o canto inferior esquerdo e tira os rótulos soltos "Vida" e "Mana". Os slots leem o runtime comum de habilidades para as três classes (o guerreiro também usa `habilidades` agora). Jev: menos quadrada que a v4 (77%); o que ainda pesava era a placa da sala (55%) e a moldura dos globos (53%), tratados nesta passada. Capturas em `/mnt/project-files/hud/v5/`.

## HUD v6: compacta e discreta (1/11/2026)
O Will reprovou a v5: curvada demais, esquisita e ocupando muita tela. A v6 remove a base de pedra em arco e a sombra do rodapé; sobram globos de 68 px nos cantos com aro fino de ferro, seis slots (todos de 46 px) em fileira curta centralizada (ataque, esquiva, Q E F R) com moldura fina e tecla pequena, placa da sala de 110 x 36 px, barra do chefe fina (10 px, 380 px de largura) com marcas de fase e só o nome e a fase em texto, e a ajuda pequena que some sozinha. Peças em `hud_arte_2d.gd` (`slot_mini`, `encaixe_mini`, `globo_mini`, `placa_mini`, `barra_chefe_fina`); medidas em `hud_layout.csv`. As peças da v3 a v5 (`base_arco`, `barra_chefe`, `placa_gotica` etc.) ficam no arquivo sem uso. Capturas em `/mnt/project-files/hud/v6/`.
Ajustes de legibilidade da v6 (revisor): globos de 68 px, todos os slots com 46 px e a mesma moldura, tecla em plaquinha escura no canto (12 px), encaixe vazio com cadeado pequeno, ajuda some em 5 s e fase do chefe com texto claro. Capturas `v6b_*` em `/mnt/project-files/hud/v6/`.
