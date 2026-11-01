# 31. Plano da virada para hordas (31/10/2026)

O Will jogou o build com as 3 classes e pediu: mapa bem maior, hordas de inimigos, habilidades atacando sozinhas (só ult e itens ativos manuais), dano, vida e spawn proporcionais, a ponte corrigida (o personagem passava por baixo das pedras), objetos que parecem flutuar (tumbas, pedras, árvores) presos ao chão, as duas portas do fim da sala revistas e os itens polidos. Inimigos e movimentação ficam como estão. Decisões técnicas e de design pelo Jev (`jev-latest`, `POST /v1/systemone`, duas rodadas); confiança abaixo de 0,5 é provisória e o número fica no CSV para ajustar depois do teste.

## 1. Decisões do Jev
| Pergunta | Decisão | Probabilidades | Conf. |
|---|---|---|---|
| Formato da fase | Mapa aberto único por fase, com zonas temáticas dentro dele (gramado, riacho, cripta em ruínas), ondas contadas que crescem e o Guardião na última onda; um portal único aparece depois do chefe | A 89%, sobrevivência por tempo 3%, zonas separadas 8% | 0,83 |
| Tamanho | Cerca de 3 × 3 telas de 1920 × 1080 (≈ 90 × 51 tiles de 64 px), com borda | 3×3 71%, 5×5 16%, infinito 13% | 0,56 |
| Habilidades | Ataque básico e todas as habilidades disparam sozinhas ao sair da recarga; só a ult e os itens ativos são manuais | 100% | 1,0 |
| Mira automática | Inimigo mais próximo (ou o maior grupo, quando o CSV da habilidade pedir) | 78% | 0,67 |
| Botões manuais | Ult (1 tecla) e 1 item ativo/consumível (1 tecla), além de mover e esquivar | 65% (2 itens 22%, só ult 13%) | 0,48 (provisória) |
| Upgrades na corrida | Gemas de XP enchem a barra de nível (1 de 3 cartas por nível) e elites soltam baú com carta rara | 67% (só baú 28%) | 0,50 |
| Inimigos vivos no pico | Até ~40 na primeira versão (teto no CSV) | 94% | 0,91 |
| Duração da fase | ~8 min na primeira versão | 49% (12 min 34%) | 0,24 (provisória) |
| Balanceamento | Curva em CSV por onda: vida, dano e orçamento de spawn crescem com a onda, calibrados contra o DPS esperado do jogador e conferidos pelo bot de corridas | 65% (fórmula no core 33%) | 0,48 (provisória) |
| Onde mora o spawn | ShatterCore, determinístico; o cliente só instancia | 80% | 0,60 |
| Portas | Uma saída só (o portal depois do chefe); as duas portas do topo saem | manter uma 68%, remover 32% | 0,52 |
| Primeiro pacote | Mapa grande com câmera seguindo o jogador | 75% | 0,62 |
| Modelo | Gameplay e core: Opus 5.5 (96%). Ancoragem visual: Fable 5.1 (60%, liberado pelo Will hoje) | | 0,92 / 0,20 |

## 2. Diagnóstico do que o Will viu
- **Ponte**: as pedras de travessia, as lajes soltas, o musgo e os tufos da beira do caminho estavam com `z_index = 1`, acima dos atores (z 0). Por isso o personagem passava "por baixo" delas. Corrigido neste PR (`terreno_2d.gd`): ficam no z do chão; a ordem entre elas continua pela árvore de nós. O desenho da ponte em si (lajes chapadas sobre a água) vai para o pacote H5.
- **Objetos flutuando**: os props têm só uma elipse preta de 42% sob o pé, sem contato (oclusão, grama na base, sombra projetada coerente com a luz). Pacote H5.
- **Habilidade que não ataca nem clicando**: `habilidades_2d.usar()` devolve falso quando o slot está vazio, sem recarga ou sem mana, e a HUD mostra o ícone mesmo assim. Hipótese (não reproduzida aqui, sem Godot na nuvem): slot sem nível aprendido ou clique na HUD sem ligação ao slot. O H2 confirma o motivo com um teste e o problema some com o autocast.
- **Duas portas**: são as células `D` do topo das salas (`data2d/rooms/*.txt`). Saem com o mapa novo (H1).

## 3. Pacotes (cada um numa thread nova)
Os pacotes H1, H2, H3 e H5 andam em paralelo; cada um é dono só dos arquivos listados. H4 e H6 começam quando as dependências estiverem no `master`. Todos: branch temporária, PR, CI `cliente2d` (e `core` quando mexer no ShatterCore) verde, merge no `master`, apagar a branch. Nenhum número de balanceamento no código; textos só por chave de localização.

| # | Pacote | Escopo | Arquivos (dono) | Depende de | Modelo |
|---|---|---|---|---|---|
| H1 | Mapa grande e câmera | Fase aberta de ~90 × 51 tiles com zonas (gramado, riacho, ruínas), borda, câmera seguindo o jogador com limites (fim do zoom que cabe a sala inteira), pontos de spawn nas bordas da tela, portal único depois do chefe, remoção das portas `D`. Desempenho com 40 inimigos e o terreno grande (60 fps no PC do Will) | `run_2d.gd` (câmera, carga da fase, estado), `room_2d.gd` (menos `colocar_props`), `data2d/rooms/fase_*.txt`, `run.csv`, `run_settings.csv` | — | Opus 5.5 |
| H2 | Autocast das habilidades | Ataque básico e as 4 habilidades da árvore disparam sozinhos ao sair da recarga, mirando no inimigo mais próximo (alvo por coluna `mira` no CSV: `proximo`, `grupo`, `si`); ult manual numa tecla; corrigir o "não ataca"; opção de acessibilidade para mirar no mouse | `player_2d.gd`, `habilidades_2d.gd`, `efeitos_*_2d.gd`, `warrior_2d.gd`, `mago_2d.gd`, `habilidades_*.csv`, `alvos_2d.gd` | — | Opus 5.5 |
| H3 | Spawner de hordas no core | Ondas contadas por fase com orçamento de spawn, teto de vivos, mistura de tipos por onda, elites marcados e chefe na última onda, tudo determinístico (seed); API C nova (`shatter_rogue_wave_*`, docs/09 nova seção) e ponte no GDExtension; o cliente só pede "quem nasce agora" | `ShatterCore/` (módulo `rogue`), `nucleo_2d.gd` e a ponte GDExtension, `data2d/ondas.csv` (novo), `docs/tecnico/09_mudancas_contrato.md` | — | Opus 5.5 (contrato novo da API C) |
| H4 | XP, nível e balanceamento | Gemas de XP e barra de nível, 1 de 3 cartas por nível, baú de elite com carta rara; curva CSV por onda (vida, dano, orçamento) calibrada contra o DPS esperado; o bot de corridas passa a medir mortes por onda, tempo de fase e DPS | `upgrades_2d.gd`, `upgrade_ui_2d.gd`, `drops.csv`, `upgrades.csv`, `curva_horda.csv` (novo), `enemies.csv` (só números), `tools/corridas_2d.gd` | H1, H2, H3 | Opus 5.5 |
| H5 | Ancoragem visual e ponte nova | Props presos ao chão: sombra de contato com oclusão, grama/terra na base, sombra projetada coerente com a luz, árvores com raiz; ponte de madeira ou de lajes com margem e reflexo na água, com os atores passando por cima e y-sort onde houver parapeito; revisão dos tufos e lajes soltas. Passa pela thread revisora antes do Will | `terreno_2d.gd`, `colocar_props` de `room_2d.gd` (só essa função), `props_2d.csv`, `props_manifest.csv`, arte em `docs/arte/sprites2d/` | — | Fable 5.1 |
| H6 | HUD de horda e polimento dos itens | HUD nova: só ult e item ativo (com recarga), barra de XP e nível, contador de onda e de inimigos; polimento dos itens (ícones, raridade com brilho, coleta com ímã e som, cartas mais legíveis) | `hud_2d.gd`, `hud_arte_2d.gd`, `hud_layout.csv`, `icones.csv`, `loc_2d.csv` | H2 (ult/item) e H4 (XP) | Opus 5.5 |

## 4. Critério de pronto da virada
- Uma fase de ~8 min no mapa grande, com ondas crescentes até ~40 inimigos vivos, chefe na última onda e o portal no fim; nenhuma porta `D`.
- O jogador só move, esquiva, usa a ult e o item ativo; todo o resto dispara sozinho.
- O bot de corridas (10 corridas, 3 classes) termina sem erro, e a taxa de morte por onda fica dentro da faixa do `curva_horda.csv`.
- Nenhum prop parece flutuar e ninguém passa por baixo da ponte, conferido em capturas no build.

## 5. Ideias da referência de hordas (análise do PokeBonk, 31/10)
Uma sessão no PC do Will analisou um jogo de hordas como referência de estrutura (notas em `D:\openclaude\research\pokebonk\notas\`). Só a estrutura serve de inspiração: nenhum código, nome ou número exato entra no jogo. O Jev avaliou cada ideia (agora, depois do primeiro teste, ou não):

| Ideia | Decisão | Probabilidades (agora / depois / não) | Conf. | Pacote |
|---|---|---|---|---|
| Spawn em anel ao redor do jogador, fora da tela | **Agora** | 50 / 37 / 13 | 0,25 (provisória) | H3 (regra) e H1 (raio da tela, bordas do mapa) |
| Fase com prazo: no fim do tempo vem um enxame final; antes disso o jogador acorda o Guardião e abre o portal | **Agora**, como variante do "Guardião na última onda" | 51 / 38 / 11 | 0,26 (provisória) | H3 (gatilho e enxame), H1 (Guardião e portal no mapa) |
| Vida do chefe adaptativa: DPS medido do jogador × um tempo-alvo de luta (no CSV) | **Agora** | 57 / 38 / 5 | 0,35 (provisória) | H4 (o cliente mede, o core recebe o DPS como entrada e calcula, mantendo o determinismo) |
| Level up com 3 cartas, ao menos 1 de habilidade de ataque, reroll/pular/banir limitados | **Agora** | 62 / 35 / 3 | 0,43 (provisória) | H4 (regra no core), H6 (botões) |
| Diretor por orçamento (créditos por segundo, cada inimigo custa pela força) no lugar das ondas | Depois | 8 / 60 / 32 | 0,40 | backlog do H3; as ondas contadas já usam orçamento por onda |
| Baralho de espécies (um tipo novo por minuto) | Depois | 18 / 67 / 15 | 0,50 | backlog do H3 |
| Teto de vivos que "condensa" inimigos novos em um mais forte | Depois | 41 / 49 / 10 | 0,24 | backlog do H3; o H3 deixa o teto como número no CSV |
| Escala separada por atributo (vida rápido, dano devagar, velocidade com teto) | Depois | 41 / 53 / 6 | 0,30 | backlog do H4; o `curva_horda.csv` já nasce com uma coluna por atributo para isso caber sem migração |
| Eventos com horário fixo (alfa gigante, enxame em anel, manada em linha, onda de elites, totens) | Depois | 31 / 64 / 5 | 0,46 | backlog do H3 |
| 3 habilidades de ataque + 3 passivas, nível máximo, fusão | Depois | 14 / 69 / 17 | 0,53 | backlog; hoje a árvore tem 4 slots (doc 29) |
| Arena procedural com um bioma por zona | Depois | 30 / 55 / 15 | 0,33 | backlog do H1; a primeira fase é feita à mão |
| Moeda comum com custo crescente e moeda rara só de chefes | Depois | 25 / 65 / 10 | 0,48 | backlog do meta (`meta.csv`) |
