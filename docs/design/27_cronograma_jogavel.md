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

## 7. M7 — decisões do Jev sobre preços e habilidades (30/10/2026)
Consulta ao `jev-latest` (`POST /v1/systemone`) sobre a loja de meta-progressão: baratear ~30% os preços propostos (80% contra 17% de manter), manter as três habilidades bloqueadas no início (multishot, pierce, evasão; 100%), primeira compra em até 2 corridas (76%) e bônus de stat pequenos o bastante para não quebrar as cartas (61%). Preços finais em `godot/data2d/meta.csv`: melhorias 28/42/35, habilidades 56/56/42 fragmentos.

## 8. M8 — hub com craft básico e balanceamento (30/10/2026)
Consulta ao `jev-latest` sobre o hub: menu com Forja/Melhorias/Partir, sem cenário andável (89%); craft de amuletos e consumíveis juntos (99%); 1 slot de amuleto (100%); primeira receita com 3 a 4 materiais (44% contra 39% para 1 a 2); bônus de amuleto menor que a melhoria de loja de +10% de dano (78%).
- **Hub**: o título virou o hub. Mostra fragmentos, materiais e o amuleto equipado; botões Jogar, Forja, Melhorias, Sair. A Forja cria receitas de `godot/data2d/receitas.csv` (custo em até 2 materiais mais fragmentos).
- **Amuletos**: criados uma vez, 1 slot equipado, bônus permanente de stat (+5% dano, +5% velocidade, +10 vida, −8% recarga da esquiva, −6% recarga do tiro). **Consumíveis**: estoque de até 3, uma unidade de cada é gasta ao partir e vale só naquela corrida.
- **Orçamento de materiais por corrida completa** (drops de `drops.csv`, salas de `run.csv`): osso ~7, essência ~4, ferro ~2, pedra ~1, núcleo 1 (só com o chefe morto), cerca de 15 no total e ~140 fragmentos numa vitória. Por isso a pedra aparece pouco nas receitas (1 a 2) e o ferro só nas mais caras. Primeira receita (Amuleto de Osso): 4 materiais, sai em uma corrida; o amuleto mais caro (Estilhaço) pede o núcleo do chefe e leva ao menos 2 vitórias com as outras compras.
- Os números ficam no CSV; o teste `_testar_forja` confere a rodada de materiais e o custo da 1ª receita.

## 9. M9 — exploração por rotas (30/10/2026)
Consulta ao `jev-latest` (`POST /v1/systemone`): formato de bifurcação após a sala, sem mapa andável (68% contra 30% de escolher região no hub e 2% de mapa ramificado); só a Região 1 com rotas dentro dela (81%); tipos de sala empatados entre combate/tesouro (42%) e combate/elite/descanso (40%), então entraram elite e descanso; número de bifurcações sem consenso (32/33/35%), ficaram 2.
- **Fluxo**: a corrida segue 4 etapas. Ao atravessar a porta para as etapas 2 e 3, abre a tela "Escolha o caminho" com o combate padrão (`run.csv`) e uma alternativa de `godot/data2d/rota.csv`. Etapa 1 e chefe não têm bifurcação.
- **Elite** (etapa 2): 7 inimigos, +15 fragmentos e 1 carta a mais. **Descanso** (etapa 3): sem inimigos, cura 50% da vida máxima, sem cartas. Números em `run_settings.csv`.
- **Fora deste marco**: segunda região jogável, mapa em camadas, tesouro. A ligação com os vereditos do roteiro (doc 21) vem depois.


## 10. M10 — migração ao ShatterCore (30/10/2026)
Consulta ao `jev-latest` (`POST /v1/systemone`): escopo economia mais fluxo da corrida (79%, contra 17% só economia, 3% adiar e 1% tudo); ponte por GDExtension em C++ (88%, contra 11% JSON e 1% C#); paridade de regras com os mesmos CSV (100%). Combate e movimento em tempo real ficam no GDScript.
- **Pacote 1 (feito)**: módulo `rogue` do core (`shatter/rogue.h`, API C `shatter_rogue_*`, minor 8; contrato na seção 16 de `docs/tecnico/09_mudancas_contrato.md`). Lê `godot/data2d`, guarda o save no mesmo JSON do `meta_2d.gd`, sorteia cartas com `RngStream::Rogue`. Paridade é de regras, não da sequência aleatória do Godot.
- **Pacote 2 (próximo, thread nova)**: GDExtension (godot-cpp) que embrulha `shatter_rogue_*`; `meta_2d.gd`, `upgrades_2d.gd` e as regras de `run_2d.gd` passam a chamar o core; ajustar o CI `cliente2d.yml` para compilar a extensão. Só depois a HUD (PR 110) e a lapidação (PR 112) são rebaseadas.

## 11. Roadmap por setores até o Acesso Antecipado (31/10/2026)
O Will pediu para dividir o que falta em setores independentes, cada um em uma thread, com o Jev decidindo prioridades e correções. Consulta ao `jev-latest` (`POST /v1/systemone`): prioridade 1 em conteúdo (38%, contra 24% combate e 18% QA; confiança 0,26, provisória); Região 2 fora do lançamento (95%); Steam começa agora em paralelo (90%); QA desde o início (53% contra 47%, provisória); áudio final depois da arte e do conteúdo (77%); número de setores novos em paralelo: 3 (77%). Escolha da coordenação: 4 setores novos, porque Steam (90% "agora") tem arquivos próprios e não disputa nada com os outros; áudio fica adiado.

### Setores que já têm dono (não recriar)
| Setor | Thread | Observação |
|---|---|---|
| Arte 2D e ícones | "Gerar ícones e HUD no ChatGPT" | roda no PC do Will |
| Revisão visual | "Direção visual com o Jev" | só arte, `props_*`, salas |
| Migração ao ShatterCore (pacote 2) | "Migrar jogo ao ShatterCore" | espera os PRs 110 (HUD) e 112 (combate lapidado), que esperam o sim do Will |

### Setores novos
| Setor | Entrega | Dono de arquivos (exclusivo) | Não toca |
|---|---|---|---|
| A Conteúdo | Mais inimigos, 1 ou 2 variações de chefe/elite, salas, cartas, amuletos e receitas; texto da Região 1 conforme o doc 21 | `data2d/enemies.csv`, `upgrades.csv`, `receitas.csv`, `drops.csv`, `rota.csv`, `rooms/`, `loc_2d.csv` (chaves de conteúdo) | scripts de regra (só pede ponto de ligação ao dono) |
| B Combate e balanceamento | Ajuste fino de `player.csv`, `feel.csv`, `run_settings.csv`, curva de dificuldade por etapa, simulação de corridas para achar picos | `player.csv`, `feel.csv`, `run_settings.csv`, `enemy_2d.gd`, `player_2d.gd`, `arrow_2d.gd`, `boss_patterns_2d.csv`; começa depois do merge do PR 112 | CSV de conteúdo do setor A |
| C QA e build | Corridas automáticas a cada PR (headless, 10 corridas sem travar), relatório de métricas (tempo, mortes por sala), roteiro de playtest, export Windows/Linux no CI | `scripts2d/tools/`, `.github/workflows/cliente2d.yml`, `tools/` de export, `docs/requisitos-qa/` | scripts de jogo |
| D Steam e opções | Menu de opções (volume, vídeo, remapear teclas), tutorial da primeira corrida, conquistas e nuvem de saves via GodotSteam (atrás de interface, sem travar sem Steam), texto e checklist da página da loja | `menus_2d.gd` (seção de opções), `opcoes_2d.gd`, `steam_2d.gd`, `docs/steam/` | HUD de corrida (PR 110) |
| E Áudio final (adiado) | Música e efeitos próprios | `audio_2d.gd`, `data2d/audio.csv` | começa depois da arte e do conteúdo |

### Ordem e regras
1. Agora, em paralelo: A, C e D. B começa quando o PR 112 for mesclado. E espera.
2. Fora do escopo do lançamento: Região 2, MMO, co-op.
3. Cada setor: uma thread, branch temporária, PR, CI verde, merge no `master`, passagem de bastão curta. Números em CSV, texto em `loc_2d.csv`, `test_2d.gd` verde.
4. A cada entrega a thread do setor avisa a coordenação, que consulta o Jev. Se o Jev tiver confiança abaixo de 0,5, a decisão é provisória e volta ao Jev ao fechar o setor. Arte nova passa pela revisora antes do Will.
