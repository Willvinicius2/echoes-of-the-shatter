# 27. Cronograma até o jogo jogável (corrida roguelike com o arqueiro)

Data: 30/10/2026. Planejadora: thread "Levar o jogo até jogável com o Jev". O Will delegou ao Jev (modelo de decisão da TypeSafe, `jev-latest`) as decisões visuais e técnicas até o jogo ficar jogável. Este documento registra o que o Jev decidiu, o cronograma e os pacotes. Quem muda uma decisão é o Jev (ou o Will), nunca uma thread de pacote.

## 1. Ponto de partida
Cliente 2D em Godot (`godot/scripts2d/`, GDScript): corrida de 4 salas (3 de inimigos e o Guardião da Cripta), arqueiro com mira no mouse, flecha, esquiva, HUD, 8 inimigos, props, sprites em 5 direções, teste headless e CI. Faltam: escolha de upgrades, balanceamento e game feel, chefe com fases, áudio, menu/telas, build jogável. Direção visual: `docs/arte/26_direcao_visual_2d.md`.

## 2. Decisões do Jev (rodadas 1 e 2)
Confiança entre parênteses; abaixo de 0,5 está marcada como provisória.

| Pergunta | Decisão | Conf. |
|---|---|---|
| Escopo de "jogável" | 4 salas atuais + escolha de upgrade ao limpar sala + chefe. Sem meta-progressão nem save | 0,88 |
| Habilidades | Arqueiro com só tiro básico e esquiva; o resto vem de upgrades passivos | 0,98 |
| Escolha na corrida | Cartas de upgrade ao limpar a sala. Árvore de habilidades e meta-progressão ficam para depois | 0,42 (provisória) |
| Onde ficam as regras | Conteúdo novo em GDScript agora, dados em CSV; migrar ao ShatterCore depois | 0,91 |
| Ordem dos marcos | combate/feel → upgrades → salas → chefe → áudio/UI → save/meta | 0,92 |
| Cartas por escolha | 3 | 0,68 |
| Pool inicial | 6 a 8 upgrades simples (dano, cadência, velocidade, vida, multishot, perfuração) | 0,98 |
| Paralelismo | 4 ou mais pacotes, desde que cada um tenha dono de arquivo | 0,53 |
| Visual × técnico | Andam em paralelo; o visual só troca arte e não mexe em script de regra | 0,98 |
| Migração ao core | Logo depois do jogável, antes de meta-progressão e save | 0,77 |
| Marco seguinte ao jogável | Meta-progressão com save | 0,28 (provisória, decidir de novo ao fechar M5) |

## 3. Pacotes e dono de arquivos
Cada pacote é uma thread nova, com contexto curto, branch temporária, PR, CI verde e merge no `master`. Sempre CSV para números (`godot/data2d/`) e chaves em `loc_2d.csv` para texto. Teste `test_2d.gd` deve continuar verde.

| Pacote | Entrega | Dono de arquivos | Depende de |
|---|---|---|---|
| P1 Combate e feel | Hit stop, tremor de câmera, número de dano, telégrafo de ataque inimigo, ajuste de esquiva e tiro, balanceamento de `player.csv` e `enemies.csv` | `enemy_2d.gd`, `actor_2d.gd`, `arrow_2d.gd`, `player_2d.gd` (movimento/tiro), CSV de inimigos | nada |
| P2 Upgrades | `data2d/upgrades.csv` (6 a 8), tela de 3 cartas ao limpar a sala, aplicação dos modificadores, lista de upgrades no HUD, teste de cada upgrade | `upgrades_2d.gd`, `upgrade_ui_2d.gd`, `upgrades.csv`; só pontos de ligação em `player_2d.gd` e `run_2d.gd` | nada (combina com P1 pelo contrato `stats modificáveis`) |
| P3 Fluxo da corrida | Tela inicial, pausa, game over e vitória, transição entre salas, contagem de corrida | `run_2d.gd`, `hud_2d.gd`, telas novas | P2 |
| P4 Chefe Guardião | Fases e padrões do Guardião em CSV, barra de vida do chefe, entrada e morte do chefe | `enemy_2d.gd` (ramo do chefe) ou `boss_2d.gd`, `boss_patterns_2d.csv` | P1 |
| P5 Áudio e UI final | Efeitos e música CC0, HUD com Theme de pedra escura, ícones das cartas | `audio_2d.gd`, `data2d/audio.csv`, tema de UI | P2, P3 |
| P6 QA e build | Roteiro de playtest, 10 corridas automáticas sem travar, export Windows jogável, relatório ao Will | `scripts2d/tools/`, `.github/workflows/cliente2d.yml` | P1 a P5 |
| V Visual | Chão de gramado com caminho, riacho, passe de arte | Thread "Direção visual com o Jev", só arte e `props_*`/salas | paralelo, sem tocar nas regras |

## 4. Marcos
Prazos em dias de trabalho dos agentes (uma thread por pacote). Datas absolutas só depois que o Will confirmar o ritmo.

| Marco | Conteúdo | Estimativa | Critério de saída |
|---|---|---|---|
| M1 | P1 e P2 em paralelo (V segue na thread própria) | 3 a 4 dias | Limpar sala mostra 3 cartas, a escolha muda o jogo, teste verde, o tiro tem peso |
| M2 | P3 | 2 dias | Do menu ao game over e à vitória sem ajuda manual |
| M3 | P4 | 2 a 3 dias | Chefe com 2 ou 3 fases, derrotável e justo |
| M4 | P5 | 2 dias | Jogo com som e UI final |
| M5 | P6 | 2 dias | Build Windows para o Will jogar uma corrida completa; passa pela revisora antes |
| M6 | Migração ao ShatterCore e decisão do próximo marco | Jev decide ao fechar o M5 | |

Total até o jogável (M5): cerca de 11 a 13 dias de trabalho, menos se P1 e P2 correrem juntos como previsto.

## 5. Regras de trabalho
- O Jev decide o técnico e o visual. Dúvida de pacote vai para a planejadora, que consulta o Jev (`POST /v1/systemone`, `jev-latest`; credencial injetada pelo proxy).
- Arte final passa pela revisora ("Agente escolhedor de ferramentas") e só depois o coordenador mostra ao Will.
- Contexto pequeno: o índice `contexto-do-jogo/00_INDICE.md`, este documento e `COMO_RODAR_2D.md`. Ao fechar o pacote, passagem de bastão curta.

## 6. Decisão de direção (30/10/2026): roguelike com hub, craft e exploração
O Will perguntou se o jogo seguiria como roguelike ou viraria um MMO 2D de exploração, craft e habilidades. O Jev decidiu e o Will aprovou: **roguelike 2D com hub, craft e exploração, single-player. Sem MMO.**

- Respostas do Jev: direção roguelike com hub e craft 98% (roguelike puro 2%, MMO 0%); "MMO é viável e de baixo risco para esta equipe?" 4%; "hub e craft aproveitam o master?" 90%; próximo marco hub com craft 63% contra migração ao core 35% (confiança 0,51, provisória).
- Motivo: um MMO exige servidor autoritativo, contas, banco, anti-cheat, moderação e hospedagem mensal, mais reescrever o cliente para rede e ter jogadores para o mundo não ficar vazio. A equipe é o dono com agentes de IA. O hub com craft reaproveita todo o cliente 2D, as cartas e o chefe.
- Ordem a partir do M5 (substitui o "decidir de novo" do M6 na linha de meta-progressão):
  1. M5: build jogável para o Will testar uma corrida completa.
  2. M7 Meta-progressão com save: moeda/materiais que sobrevivem à morte, save em disco, habilidades desbloqueáveis.
  3. M8 Hub com craft básico: tela do hub entre corridas, receitas em CSV, materiais dropados nas salas.
  4. M9 Exploração: regiões ou rotas escolhíveis na corrida, ligadas ao roteiro da Região 1.
  5. M10 Migração ao ShatterCore antes de o craft crescer demais.
- Fora do escopo: servidor, contas e MMO. Co-op pequeno só como extensão futura, depois do Acesso Antecipado.
- Cada marco novo vira pacote em thread própria, com dono de arquivos, CSV para números e chaves em `loc_2d.csv`.
