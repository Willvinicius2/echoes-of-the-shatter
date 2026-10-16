# 09 — Mudanças de contrato do ShatterCore (Backend Engineer)

Os headers de `ShatterCore/include/shatter/` são a parte executável do contrato (`docs/04_arquitetura.md`, abertura). Este registro lista cada mudança feita neles depois da entrega do Tech Lead, com o motivo e o impacto. Regra: só adições ou mudanças compatíveis. Nenhuma assinatura existente mudou de forma incompatível.

Data: 16/10/2026. Branch: `claude/confident-archimedes-ftd7kj`.

## 1. Mudanças nos headers

| # | Header | Mudança | Motivo | Impacto |
|---|---|---|---|---|
| C-1 | `save.h` | `SaveContentVersionSupported(const SaveData&, const ContentDB&)` (feita pelo agente anterior; revisada e mantida) | RNF-10: save com `content_version` maior que o do jogo é recusado sem ser alterado. `ParseJson` e `ReadSaveFile` não recebem o `ContentDB`, então a regra precisava de um ponto no core para o C# não comparar versões por conta própria | Adição. Usada por `shatter_save_read` quando o chamador passa o banco |
| C-2 | `save.h` | `AreaRunOutcome`, `AreaRunReward`, `RecordAreaRun(...)` | RF-35 e RF-50 eram [SC] e não tinham função no core: cargas por limpar a área e por vencer o chefe, domínio e o teto de 12 ficariam no C# | Adição. Decisão das cargas na seção 2 |
| C-3 | `save.h` | `ExpeditionStartParams`, `StartExpedition(...)` | O fluxo da seção 6.3 do 04 (snapshot congelado, `Running`, desconto de cargas) não tinha função. Sem ela, o C# descontaria cargas e montaria o snapshot | Adição. Chama `CanStartExpedition` com as cargas do save e "outra em andamento" entre todos os personagens (RF-37) |
| C-4 | `save.h` | `ItemToJson/FromJson`, `CharacterToJson/FromJson`, `ExpeditionRequestToJson/FromJson`, `ToString`/`Parse*` dos enums de expedição | Já existiam dentro de `save.cpp`. Ficaram públicas para a API C usar o mesmo formato do save no snapshot e no pedido de expedição, sem duplicar o formato | Adição. Formato do save inalterado |
| C-5 | `expedition.h` | `kTipRaisePotion`, `kTipMorePotions`, `kTipLowLife`, `kTipAllGood`; `tipKeys` passa a ter exatamente uma chave | As chaves antigas (`tip.expedition.*`) não existiam em `Content/Data/Loc/` (RF-61 [SC] falharia). As novas são as que o Narrative já escreveu em `Loc/expedition.csv`. RF-44 pede "uma dica acionável" | Muda o conteúdo de `ExpeditionResult::tipKeys`. Não entra no `resultHash` |
| C-6 | `expedition.h` | `ApplyWindowStop(ExpeditionProgress&, const OfflineWindow&)`; o header passa a incluir `clock.h` | RF-48 pede o motivo "relógio voltou" no relatório. `StopReason::ClockRollback` existia mas nada o produzia | Adição. O motivo entra no `resultHash` |
| C-7 | `character.h` | `BuildEnemyStatBlock(const EnemyData&, int level, StatBlock&)` | A conta "base + perLevel × (nível − 1)" do inimigo estava só dentro do simulador. O combate em tempo real precisa do mesmo builder (API C `shatter_statblock_for_enemy`) | Adição. O simulador passou a usá-la (mesmo resultado) |
| C-8 | `rng.h` | `Pcg32::Increment()` e `Pcg32::FromRaw(state, inc)` | A seção 9.2 do 04 prevê o RNG como struct de 2 `uint64_t` do chamador. Sem acesso ao incremento não havia como atravessar a fronteira | Adição, inline. Sequências inalteradas |
| C-9 | `effects.h` | Membro privado `internalCooldowns_` de `unordered_map` para `vector<pair<ContentId,double>>` | `EffectContainer::Tick` iterava o `unordered_map` (proibido no CLAUDE.md em código que afeta resultado) | Só o membro privado. API igual |
| C-10 | `shatter_c.h` (novo) | API C v1 (`SHATTER_C_API_VERSION 1`) | Item 2 da tarefa e seção 9 do 04 | Novo. Resumo na seção 3 |

Mudanças de comportamento sem mudança de assinatura:

- **Recuo no idle.** O encontro em que o personagem recua mantém o XP e o loot dos inimigos já mortos. Só o loot de área (o prêmio por concluir o encontro) fica de fora. Motivo: o plano diz "O loot já obtido nunca é perdido" (`00_plano_existente.md`, seção 7) e a seção 12 do 04 diz "o loot obtido fica". Antes, o encontro do recuo era descartado inteiro.
- **Encontro sem inimigo.** `Finalize` recusa `countMin < 1` (CSV ou programático) e o simulador encerra com `ContentMismatch` se receber um encontro que não gera inimigo. Antes, o encontro durava 0 s e a simulação não terminava.
- **Golden.** Nenhum caso de `tests/data/golden/expeditions.txt` recua, então nenhum `resultHash` de referência mudou. O arquivo continua o mesmo.

## 2. Decisões tomadas nesta entrega

1. **Cargas por corrida (RF-35, RF-50).** Por corrida conta o maior entre limpar a área (+`charges_clear_area`) e vencer o chefe (+`charges_boss`), não a soma. A primeira conquista soma +`charges_new_area` uma vez. Assim a conquista da Cripta dá exatamente +5 (2 + 3), como pede o RF-50. Somar tudo daria +6. O teto `charges_max` nunca tira cargas que já estavam no save.
2. **Domínio.** Conquista = chegar ao fim **e** vencer o chefe na mesma corrida. Num mapa sem `bossEncounter`, basta chegar ao fim. A conquista grava `conquered_maps` e sobe `highest_tier_cleared` se o tier do mapa for maior.
3. **Dica única.** Recuo com poções sobrando (morreu antes de beber) → `report.tip.low_life`. Recuo sem poções, ou "quis curar e não tinha poção" → `report.tip.more_potions`. Nada a corrigir → `report.tip.all_good`. `report.tip.raise_potion` tem `{pct}` e fica sem uso até o core saber sugerir o limiar.
4. **Relógio voltando.** A janela offline já encerrava no último ponto conhecido. Agora o resultado também sai com `ClockRollback`. Não é preciso gravar nada no save: abrir de novo com o relógio certo só entrega o tempo real, até a duração escolhida, sem recompensa extra (RNF-09).
5. **Previsão e flags.** `ForecastExpedition` não mudou. A API C limita `samples` a 1–100 000.

## 3. API C (`shatter_c.h`), resumo

- **Versão e layout.** `shatter_api_version`, `shatter_core_version`, `shatter_layout_info`/`shatter_layout_check`: 82 valores (sizeof e offsetof das 15 structs blittable, em ordem fixa). Também há `static_assert` de tamanho e offset no `.cpp`.
- **Status.** `SHATTER_OK`, `INVALID_ARGUMENT`, `BUFFER_TOO_SMALL`, `PARSE_ERROR`, `CONTENT_INVALID`, `IO_ERROR`, `VERSION_MISMATCH`, `NOT_FOUND`, `INTERNAL`. O detalhe vai em `shatter_error` do chamador (`code`, `line`, `message[256]` UTF-8, cortado em fronteira de caractere). Não há erro global nem `thread_local`.
- **Handles.** `shatter_db` (imutável depois de finalizado, leitura concorrente), `shatter_save`, `shatter_statblock` e `shatter_effects` (main thread). `*_destroy(NULL)` não faz nada.
- **Buffers.** Padrão de duas chamadas. Com `BUFFER_TOO_SMALL`, nada muda: o RNG e o contador de uid do loot só avançam se a saída couber. Os eventos de efeito ficam no handle até o próximo tick.
- **Caminho quente.** `shatter_resolve_hit(attacker, defender, input, rules, rng, out)` não aloca. As regras vêm de `shatter_db_rules`, então o C# não guarda número de balanceamento.
- **Caminho frio (JSON no formato do save).** Pedido de expedição (`shatter_save_expedition_request` já aplica a janela do relógio), `shatter_expedition_simulate` (thread de fundo), `simulate_range`/`finalize` (fatias com o progresso inteiro em JSON; mesmo `resultHash`), `forecast`, `shatter_save_collect_expedition`, `shatter_db_lookup_json` (nome, tempos e tooltip).
- **Save.** `shatter_save_read` (backup + `content_version` futuro), `write` (tmp → 3 backups → rename), `to_json`/`from_json`, `summary`, `touch_last_seen`, `apply_daily_rest`, `record_area_run`, `start_expedition`, `add_loot`.
- **Build.** O alvo `shattercore_dll` (nome de saída `shattercore`) é controlado por `SHATTER_BUILD_SHARED` (ligado por padrão). Usa CRT estático no MSVC e visibilidade oculta. No Linux, um version script deixa exportadas só as funções `shatter_*` (o teste `shattercore_dll_exports` confere as 64). Sem DLL, a mesma API vira biblioteca estática para os testes.

## 4. Pendências do 06_dados.md (seção 9) e do 13_design_pendencias.md

| Pendência | Situação no core |
|---|---|
| P1 Poção sem dados | Mantido `ExpeditionRequest::potionHealFraction` (padrão 0,35 do header; `StartExpedition` usa o padrão). O design (13, item 2) pede `potions.csv` com Vida e Resguardo, `ref_id` em `use_potion` e `potion_slots` no save. Isso exige tabela nova (Data Engineer), mudança de header e save v2. **Pendente**: o 0,35 é um número de balanceamento no header até a tabela existir |
| P2 Único sem amostra de paridade | O core usa só `UniqueData::idleSupported`. A coluna `idleParitySampleSize`/`idleCalibration` em `uniques.csv` (13, item 8) está pendente com o Data Engineer |
| P3 IDs sem tabela | Mantida a decisão do agente anterior: só formato e prefixo para `family.`, `spec.`, `currency.`, `material.`, `page.`, `sigil.common.`, `book.spec.` e `map_stone.` (teste `content_p3_p8_decisions_documented`) |
| P4 Combate em tempo real sem dados | Esquiva, telegraph em segundos, fases e padrões do chefe, elites e IA de RF-20/21: sem tabela nem função no core. RF-15, RF-19, RF-23 e RF-24 ficam **sem cobertura** até existirem `rules.csv` (chaves de esquiva), `boss_phases.csv`, `boss_patterns.csv`, `elite_modifiers.csv` e `enemy_ai.csv` (13, itens 1, 3 a 6) |
| P5 Único só do Guardião | Não é garantido por dados. O idle nunca entrega Único (dupla checagem), mas uma tabela qualquer com `kind = unique` e `manualOnly = true` cairia no manual. A regra "1ª vitória garantida, 20% depois, garantido na 5ª" (13, item 9) precisa de colunas em `loot_entries.csv` e de `boss_progress` no save |
| P6 `Loc/` | `ContentDB::LoadDirectory` ignora subpastas, então `Content/Data/Loc/` não atrapalha. Os testes RF-45/RF-61 leem `Loc/*.csv` |
| P7 CI sem `--self-test` | Fora do escopo (ainda não há workflow de CI). O ctest roda o validador Python sobre um save do core (RF-51) |
| P8 Tags obrigatórias | No CSV, obrigatórias. Via `Add()`, `tags = 0` é aceito (mantido) |
| P9 Crescimento do inimigo | Mantido inline em `enemies.stats`. `BuildEnemyStatBlock` lê `EnemyData::stats` |
| P10 Migração v1→v2 | Não registrada: `kCurrentSaveVersion` continua 1 e a tabela de migrações está vazia. A máquina de migração é testada |
| P11 Valores provisórios | O core lê tudo de `rules.csv`. O 13 (item 10) recomenda `retreat_life_fraction` 0,25. O CSV não foi tocado nesta entrega; fica com o Data Engineer |

## 5. O que o Frontend ainda não encontra no core

O core não tem, e a API C portanto não expõe:

- Novo jogo e personagem (habilidade inicial, barra).
- XP do jogo manual com subida de nível e liberação de habilidades por `unlockLevel` (simplificação do protótipo, 02 seção 2.2).
- Inventário: equipar e desequipar com checagem de posição.
- Esquiva, poções em tempo real, fases do chefe e elites (P4).
- `tools/build_native.*`, que copia a DLL para `Assets/Plugins/x86_64/`.
- O lado C# (`Echoes.Interop`).

Essas funções são o próximo passo do Backend. A saída provisória seria o C# editar o JSON do save e reabri-lo por `shatter_save_from_json`, mas isso exige recalcular o SHA-256 e põe regra no C#, o que o 04 proíbe. Não é recomendada.

## 6. Proposta de mudança de contrato C-10: personagem modular e espaço `legs` (Tech Lead, 16/10/2026)

Decisão do dono em 16/10/2026: heróis modulares (corpo base mais peças de armadura) e **novo espaço de equipamento `legs`** com atributos. O detalhe visual está em `docs/04_arquitetura.md`, seção 17.4. **É uma proposta: Backend e Dados implementam depois, nas suas worktrees; nada foi alterado em código ou CSV.** Muda o formato do save, então a versão sobe (compatível para trás por migração).

| # | Onde | Mudança | Dono |
|---|---|---|---|
| C-10a | `item.h` | `ItemSlot::Legs` entre `Hands` e `Feet` (ordem `MainHand, OffHand, Head, Body, Hands, Legs, Feet, Amulet, Ring, Ring2, Belt`); `kItemSlotCount` de 10 para 11; `ParseItemSlot` e `ToString` com `"legs"`. Se `shatter_c.h` ou os testes usarem o índice numérico, acrescentar `Legs` no fim para não renumerar | Backend |
| C-10b | `character.h`, equipar e desequipar | `equipment` passa a ter 11 posições; `legs` aceita só item de `slot = legs`, com as regras de `head/body/hands/feet`; o AA usa as 9 primeiras posições | Backend |
| C-10c | `save.h` | `kCurrentSaveVersion` de 1 para 2. `migrate_1_to_2`: para cada personagem, `equipment.legs = null` e recálculo do `sha256`. Serializar e parsear `legs`. Save v1 abre e é regravado em v2; save v2 em jogo v1 é recusado (RNF-10). Fixtures: manter `save_v1.json` como entrada e criar `save_v2.json`. A migração de poções (P10) é independente; se coincidirem, entram na mesma v2 | Backend |
| C-10d | `item_bases.csv`, `uniques.csv`, parser de conteúdo | Coluna nova **opcional** `visualSetId` (ID `vset.*`) em `item_bases.csv`, e a mesma em `uniques.csv` (prevalece sobre a da base). `ItemBaseData::visualSetId` (texto; vazio = fallback `vset.starter`), fora do `resultHash` e do simulador. O cabeçalho exato do CSV muda: o parser aceita a coluna nova. Getter no `RulesService` e na API C para o C# ler (04, 9.6). Alternativa: `item_visuals.csv` separado (`baseId,visualSetId`) | Backend (parser e API), Dados (CSV) |
| C-10e | `schemas/_enums.json`, `affixes.csv`, `item_bases.csv`, `tools/validate_data.py` | `@slots` ganha `legs`; `allowedSlots` aceita `legs`; `item_bases.slot` aceita `legs` (sem dano de arma, `attackTime` nem `weaponTags`); prefixo `vset.` na lista de prefixos de ID; save com 11 posições; RF-30 e D1 do `06_dados.md` atualizados. Afixos com `allowedSlots` vazio passam a valer em `legs`: revisão do Game Designer | Dados |

Impactos: o conteúdo atual, que usa os 10 slots, continua válido (`legs` vazio). Enquanto não houver base de item e afixo para `legs`, o espaço fica vazio na UI e sem afixo possível. O ajuste de RF-30 no `02_requisitos.md` (posições do protótipo) fica com o dono desse documento e está fora desta proposta. Teste novo sugerido no core: migração v1 para v2 e rejeição de item de outro slot em `legs`.
