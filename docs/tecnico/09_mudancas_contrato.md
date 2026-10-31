# 09 — Mudanças de contrato do ShatterCore (Backend Engineer)

Os headers de `ShatterCore/include/shatter/` são a parte executável do contrato (`docs/tecnico/04_arquitetura.md`, abertura). Este registro lista cada mudança feita neles depois da entrega do Tech Lead, com o motivo e o impacto. Regra: só adições ou mudanças compatíveis. Nenhuma assinatura existente mudou de forma incompatível.

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

- **Recuo no idle.** O encontro em que o personagem recua mantém o XP e o loot dos inimigos já mortos. Só o loot de área (o prêmio por concluir o encontro) fica de fora. Motivo: o plano diz "O loot já obtido nunca é perdido" (`docs/design/00_plano_existente.md`, seção 7) e a seção 12 do 04 diz "o loot obtido fica". Antes, o encontro do recuo era descartado inteiro.
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

## 4. Pendências do docs/tecnico/06_dados.md (seção 9) e do docs/design/13_design_pendencias.md

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

Decisão do dono em 16/10/2026: heróis modulares (corpo base mais peças de armadura) e **novo espaço de equipamento `legs`** com atributos. O detalhe visual está em `docs/tecnico/04_arquitetura.md`, seção 17.4. **É uma proposta: Backend e Dados implementam depois, nas suas worktrees; nada foi alterado em código ou CSV.** Muda o formato do save, então a versão sobe (compatível para trás por migração).

| # | Onde | Mudança | Dono |
|---|---|---|---|
| C-10a | `item.h` | `ItemSlot::Legs` entre `Hands` e `Feet` (ordem `MainHand, OffHand, Head, Body, Hands, Legs, Feet, Amulet, Ring, Ring2, Belt`); `kItemSlotCount` de 10 para 11; `ParseItemSlot` e `ToString` com `"legs"`. Se `shatter_c.h` ou os testes usarem o índice numérico, acrescentar `Legs` no fim para não renumerar | Backend |
| C-10b | `character.h`, equipar e desequipar | `equipment` passa a ter 11 posições; `legs` aceita só item de `slot = legs`, com as regras de `head/body/hands/feet`; o AA usa as 9 primeiras posições | Backend |
| C-10c | `save.h` | `kCurrentSaveVersion` de 1 para 2. `migrate_1_to_2`: para cada personagem, `equipment.legs = null` e recálculo do `sha256`. Serializar e parsear `legs`. Save v1 abre e é regravado em v2; save v2 em jogo v1 é recusado (RNF-10). Fixtures: manter `save_v1.json` como entrada e criar `save_v2.json`. A migração de poções (P10) é independente; se coincidirem, entram na mesma v2 | Backend |
| C-10d | `item_bases.csv`, `uniques.csv`, parser de conteúdo | Coluna nova **opcional** `visualSetId` (ID `vset.*`) em `item_bases.csv`, e a mesma em `uniques.csv` (prevalece sobre a da base). `ItemBaseData::visualSetId` (texto; vazio = fallback `vset.starter`), fora do `resultHash` e do simulador. O cabeçalho exato do CSV muda: o parser aceita a coluna nova. Getter no `RulesService` e na API C para o C# ler (04, 9.6). Alternativa: `item_visuals.csv` separado (`baseId,visualSetId`) | Backend (parser e API), Dados (CSV) |
| C-10e | `schemas/_enums.json`, `affixes.csv`, `item_bases.csv`, `tools/dados/validate_data.py` | `@slots` ganha `legs`; `allowedSlots` aceita `legs`; `item_bases.slot` aceita `legs` (sem dano de arma, `attackTime` nem `weaponTags`); prefixo `vset.` na lista de prefixos de ID; save com 11 posições; RF-30 e D1 do `docs/tecnico/06_dados.md` atualizados. Afixos com `allowedSlots` vazio passam a valer em `legs`: revisão do Game Designer | Dados |

Impactos: o conteúdo atual, que usa os 10 slots, continua válido (`legs` vazio). Enquanto não houver base de item e afixo para `legs`, o espaço fica vazio na UI e sem afixo possível. O ajuste de RF-30 no `docs/requisitos-qa/02_requisitos.md` (posições do protótipo) fica com o dono desse documento e está fora desta proposta. Teste novo sugerido no core: migração v1 para v2 e rejeição de item de outro slot em `legs`.


---

## 7. Etapa 2: regras novas do protótipo e API C 1.1 (Backend Engineer, 16/10/2026, branch `etapa2/backend`)

Origem: itens 1 a 11 de "Para o Tech Lead" em `docs/design/13_design_pendencias.md`, achados A-01, A-05, A-06 e M-03 de `docs/tecnico/11_revisao_codigo.md` (master) e a decisão do dono sobre a calça (`legs`, C-10 da seção 6). Números só nos CSV; o core lê as tabelas e colunas com os nomes exatos de `13`, "Para o Data Engineer", e do `docs/tecnico/06_dados.md` seção 5a (branch `etapa2/dados`).

### 7.1 Mudanças nos headers

| # | Header | Mudança | Impacto |
|---|---|---|---|
| C-11 | `content.h` | `PotionData`, `EliteModifierData`, `BossPhaseData`, `BossPatternData`, `EnemyAiData` e os getters `FindPotion/FindEliteModifier/FindBossPhase(bossId, phase)/FindBossPattern(id, phase)/FindEnemyAi` (+ listas em ordem do CSV). Colunas novas: `SkillData` (`coneAngle`, `knockback`, `projectileSpeed`, `idle.calibration`), `EnemyData` (`stunImmune`, `shieldArcDegrees`, `turnRateDegPerSec[Phase2]`, `guardBreakStaggerSeconds`, `guardBreakImmunitySeconds`, `modifierId`, `eliteLootTableId`), `UniqueData` (`idleParitySampleSize`, `idleCalibration`, `visualSetId`), `LootEntry` (`fixedChance`, `guaranteeFirstKill`, `pityKills`), `ItemBaseData::visualSetId`. `IdleCalibration` (`none`, `manual_estimate`, `bot_parity`) | Adição. As tabelas novas e as colunas novas são **opcionais** no leitor (ausente = padrão), para o core abrir tanto o conteúdo antigo quanto o de `etapa2/dados`; coluna desconhecida continua erro |
| C-12 | `constants.h` | 17 campos novos de `rules.csv` (esquiva, Guarda Quebrada, elite, `potion_lockout`) + `dodge_cancel_recovery_fraction` (0,5) e `out_of_combat_seconds` (3,0), que o `IRulesCore` pede; `retreatLifeFraction` padrão 0,25 | As 19 chaves são opcionais (padrão = valor do design); o CSV sempre vence. As 2 últimas ainda não estão em `rules.csv` (pedido ao Data Engineer) |
| C-13 | `effects.h` | `EffectData::interruptsAction`; `EffectContainer::RefreshAll` (timer único) e `Remove` (consumir acúmulos) | Adição |
| C-14 | `combat.h` + `combat.cpp` (novos) | `Vitals`, `PotionBelt`, `DodgeState`, `ActionStatus`, `EliteProfile`, `BossFight`, `ComputeActionTiming`, `RollBossLoot`, `DetCos/DetSin` | Novo |
| C-15 | `progress.h` (novo), `character.h` | `PotionSlotState`, `BossProgressEntry`; `CharacterState::potions` (int) **sai**: `potionSlots` e `bossProgress` | Mudança de dado (save v2) |
| C-16 | `expedition.h` | `ExpeditionRequest::potionHealFraction` **sai** (a cura vem de `potions.csv`); `AiRule::refId` em `use_potion` = ID da poção (vazio = a 1ª de cura); `ExpeditionProgress`: `potionSlots`, `dodgeCharges/Recharge`, `wardAmount/Remaining` (no lugar de `potionsLeft`); `EncounterReceipt::dodgesUsed`; `ExpeditionResult/Forecast::calibration`; `BuildIdleCalibration` | `resultHash` mudou (golden regravado) |
| C-17 | `loot.h` | `LootContext::bossProgress`; entradas fixas fora do sorteio ponderado | Adição |
| C-18 | `item.h`, `content.h` | `ItemSlot::Legs` no **fim** do enum (índice 10, `kItemSlotCount` 11, `"legs"`); `visualSetId` (`vset.*`) em `ItemBaseData` e `UniqueData`, fora do `resultHash` e do simulador | Índices da API C e do save antigos não deslocam |
| C-19 | `save.h`, `save_migrations.cpp` | `kCurrentSaveVersion` 2: `potion_slots` `{potion_id, charges, recharge_remaining}`, `boss_progress` `{enemy_id, kills, kills_since_unique}`, `equipment.legs`; migração 1→2 registrada; `NormalizeSavePotions(db, save)`; `DeriveExpeditionSeed` | Save v1 abre e vira v2; v2 em jogo v1 é recusado (`TooNew`) |
| C-20 | `shatter_c.h` | API C 1.1 (seção 7.4) | `SHATTER_C_API_VERSION` continua 1; `SHATTER_C_API_MINOR` 1 |

### 7.2 Regras implementadas e interpretações (item de `13` entre parênteses)

1. **Poções (2).** `PotionBelt` (um slot por linha de `potions.csv`): cargas, recarga **em série** (um relógio só), trava global (`globalLockout` da poção, ou `potion_lockout`), +1 carga ao matar elite na poção `refillOnEliteKill` com **menos cargas absolutas** (empate: a 1ª do CSV, a Vida), encher tudo (`RefillPotions`). Cura = `fractionOfMaxLife × vida máx. × PotionEffect`; barreira idem, por `duration`, **não acumula** (renova). A barreira de poção é separada das demais no simulador (expira sozinha).
2. **Esquiva (1, TL 3).** `DodgeState`: 3 cargas, 1,5 s em série, 0,35 s, i-frames em `[0, dodge_iframes)`, custo de carga + `dodge_cost_resource`; `dodge_perfect_resource` se o golpe chegou nos i-frames. No idle a IA esquiva com probabilidade `ai_base_dodge + idleDodgeTelegraphedBonus` **só se houver carga** (gasta uma; o sorteio continua consumindo 1 número do fluxo de combate).
3. **Stun e Guarda Quebrada (3, TL 4).** `ActionStatus` por entidade: `interruptsAction` vira stun real (`stunSeconds` = duração do efeito, interrompe o telegraph); imunes ao stun: `stunImmune`, chefe, elite fixo e elite sorteado. `effect.guard_break` (id reconhecido pelo core) usa **timer único** (`RefreshAll`); no N-ésimo acúmulo (N = `maxStacks` do efeito, 3), alvo imune ao stun e sem imunidade ativa fica em **stagger** (`guardBreakStaggerSeconds` ou `guard_break_stagger_seconds`), os acúmulos são consumidos, o bônus de `guard_break_stagger_damage_taken` entra em `DamageTaken` só durante o stagger (não soma com os acúmulos), `remove_barrier` manda zerar a barreira e a imunidade a nova quebra dura `guardBreakImmunitySeconds` ou `guard_break_immunity_boss/_other` (a partir do início do stagger). Comuns acumulam o bônus de dano e não têm stagger. **No idle, stun e Guarda Quebrada continuam ignorados** (conservador, 13 item 8.1).
4. **Escudo frontal (4.2, TL 5).** `shieldArcDegrees` é o arco **total** (120 = ±60°) em torno da frente do chefe; o ponto de origem é a posição do atacante (área: centro do alvo). Dentro do arco: 0 de dano, sem Ímpeto, sem empurrão (`shield_blocked`). Cai pela Guarda Quebrada por `shieldSeconds` da fase ou `boss_shield_down_seconds`. Giro: `turnRate` da fase (ou `turnRateDegPerSec[Phase2]`), 0 da preparação ao fim do impacto. Ângulos por série de Taylor determinística (`DetCos/DetSin`), sem `sin/cos` da libm.
5. **Fases do chefe (4.4, TL 6).** `BossFight`: `lifeThreshold` da fase N é a fração de vida em que a fase N **começa** (fase 1 = 1,0). O dano que passaria do limiar é cortado nele; o rugido (`transitionSeconds` da fase de entrada) começa quando o chefe termina o golpe em curso (sem interromper), é invulnerável, e invoca `summonCount × summonEnemyId` na **metade** do rugido (evento `SummonMarker` no início com o tempo até surgirem, `SummonSpawn` na metade; a metade é a constante `kSummonAtFractionOfTransition` em `combat.cpp`, a única proporção de design no código: **mover para o CSV se o Game Designer quiser**). Sem reinvocação; as invocadas são do chamador (sem XP e sem loot; morrem com o chefe). `Reset` = morte do jogador. `transitionSeconds` da fase 1 é a espera antes da 1ª ação (se 0, um atraso sorteado).
6. **Padrões por seed (4.3, TL 6).** Fluxo `Pcg32::ForStream(seed, Events, 0)`; atraso entre ações em `[decisionDelayMin, decisionDelayMax]` da fase; peso = `weight` × `playerNearWeightMult` (jogador na frente e a menos do alcance da skill) ou 0 (`ignoreIfBehind` com o jogador atrás); `maxRepeat` (vezes seguidas) e `cooldown` (do início do padrão); sem candidato, a 2ª passada ignora recarga e repetição. Telegraph e recuperação vêm do padrão (a chave é **`id` + `phase`**); impacto, alcance, cone e empurrão da skill.
7. **Elite (5, TL 7).** Elite sorteado: `elite_life/damage/xp_mult` × os do modificador; elite fixo (`modifierId`): só os do modificador. Modificador sorteado no fluxo de eventos por `weightPrototype` (**1 número**, sempre). Barreira = fração × vida máx.; Veloz: o telegraph (windup) não encurta, `attackSpeedMult` vale só em impacto e recuperação, `recoveryMult` na recuperação. Volátil (peso 0) funciona no idle: explosão após o fusível, esquivável com carga. XP do elite = XP × `xpMult`; +1 carga de poção ao matar. Loot: `eliteLootTableId` (coluna **opcional** nova em `enemies.csv`; sem ela, a tabela do inimigo).
8. **Calibração (8, TL 8).** `supported` exige amostra > 0 **e** selo ≠ `none` (em `skills.csv` e `uniques.csv`). Coluna `idleCalibration` ausente/vazia: amostra > 0 vale `bot_parity` (comportamento antigo). `BuildIdleCalibration` = o mais fraco entre a barra e os Únicos equipados; vai em `ExpeditionResult::calibration` (entra no `resultHash`), `ExpeditionForecast::calibration` e no JSON do resultado (`"calibration"`).
9. **Único do Guardião (9, TL 9).** Entrada **fixa** (`fixedChance`, `guaranteeFirstKill`, `pityKills`), fora do sorteio (o peso não dilui as outras; peso pode ficar vazio). Só no modo Manual, consome 1 número do fluxo Loot por entrada fixa. Cai se: 1ª vitória, ou `killsSinceUnique + 1 >= pityKills` (as 4 anteriores sem drop, a **5ª depois do drop** é garantida: sequência de azar de no máximo 4), ou o sorteio de `fixedChance`. `kills` sobe sempre; `killsSinceUnique` zera ao cair. O idle nunca entrega (dupla checagem) e não mexe no contador. **Ordem (RF-55):** `shatter_save_roll_boss_loot` já avança o contador no save; grave o save **antes** de entregar o item com `shatter_save_add_loot`.
10. **Recuo (10, TL 10).** `retreat_life_fraction` 0,25; recua se vida < 25% **e** sem carga de poção de cura (a primeira `heal` do CSV). Como as poções recarregam por tempo, "sem poção" é "sem carga agora".
11. **Fuga do Cão (TL 11).** O core guarda `fleeLifeFraction/fleeSeconds/fleeOncePerLife` em `enemy_ai.csv` (validado, exposto no `lookup_json`). **O simulador não soma tempo de fuga**: o design diz que o tempo entra como `idleApproachTime` da habilidade que finaliza, que é dado de calibração (`skills.csv`), não regra nova; nada foi acrescentado no código.
12. **Validações novas (Finalize).** potions (fração > 0, barreira com duração, recarga > 0, tecla única), modificadores (explosão com dano), fases (chefe real, 1..N sem buracos, limiar decrescente, invocado existente), padrões (chefe, skill, fase existente, chave `id + phase` única, prefixo `pattern.`), `enemy_ai` (inimigo, faixas), `modifierId`/`eliteLootTableId` existentes, entradas fixas exigem `manualOnly`, `visualSetId` com prefixo `vset.`, `dodge_iframes <= dodge_duration`.

### 7.3 Correções de confiança da revisão (A-05, M-03, A-06)

- **A-05.** `shatter_save_collect_expedition` (resultado do chamador) foi **retirada**: devolve `INVALID_ARGUMENT`. Nova `shatter_save_collect_expedition_trusted`: recusa se a janela do relógio confiável ainda não acabou (`SHATTER_COLLECT_NOT_FINISHED`, nada muda), senão **recalcula** o resultado pelo pedido salvo (snapshot, seed, início) e pela janela, e coleta; `ALREADY` se já coletada; devolve o resultado em JSON; buffer pequeno não muda nada.
- **M-03.** `shatter_save_start_expedition` foi **retirada** (mesmo tratamento). Nova `shatter_save_start_expedition_trusted`: `start_utc` = `trusted_now.now`; a seed sai de `DeriveExpeditionSeed` (contador de uid, último ponto visto, personagem, nº de expedições, início, XP/tempo de jogo); `seed` e `start_utc` no JSON de parâmetros são recusados.
- **A-06.** O cabeçalho de `shatter_c.h` agora documenta a posse: quem cria destrói; `shatter_boss` guarda o `shatter_db` (destrua o boss antes do banco); `shatter_effects_*` e `shatter_actor_*` exigem passar sempre o MESMO `shatter_statblock` da entidade; eventos ficam no handle; strings copiadas; threads. Novas `shatter_resolve_hit_db` e `shatter_effective_cooldown_db` leem as constantes do **banco** (o C# não manda mais número de regra; as versões com `shatter_rules*` ficam só para teste).

### 7.4 API C 1.1 (aditiva; `shatter_api_version()` continua 1, `shatter_api_minor()` = 1)

Layout próprio: `shatter_layout_info_ext` / `shatter_layout_check_ext` (`SHATTER_LAYOUT_EXT_COUNT` 37). O layout da v1 (82 valores) não mudou.

| Grupo | Funções |
|---|---|
| Regras | `shatter_api_minor`, `shatter_db_rules_ext` (`dodge_*`, `guard_break_*`, `boss_shield_down_seconds`, `elite_*_mult`, `potion_lockout`, `out_of_combat_seconds`, `dodge_max_charges`), `shatter_resolve_hit_db`, `shatter_effective_cooldown_db` |
| Vida e recurso (A-01) | `shatter_vitals_create`, `_tick` (regeneração, decaimento fora de combate, fim da barreira de poção), `_gain_resource`, `_spend_resource` |
| Tempos (A-01) | `shatter_skill_timing` (3 fases com a velocidade, recarga efetiva, custo; `modifier_id` de elite opcional), `shatter_move_speed` (base > 0: inimigo; base <= 0: herói, o atributo já vem em uu/s de `class_stats.csv`), `shatter_can_act`, `shatter_can_move` (também consideram o `shatter_actor`), `shatter_pick_attack` |
| Poções | `shatter_potion_resolve`; handle `shatter_potions`: `_create`, `_from_save`, `_to_save`, `_destroy`, `_tick`, `_use`, `_refill`, `_on_elite_killed`, `_info_json` |
| Esquiva | `shatter_dodge_init/_tick/_start/_invulnerable/_perfect_reward` (estado POD do chamador) |
| Stun e Guarda Quebrada | handle `shatter_actor`: `_create` (inimigo ou herói; flag de elite sorteado), `_destroy`, `_apply_effect`, `_tick`, `_info_get` |
| Elite | `shatter_elite_roll`, `shatter_elite_profile`, `shatter_elite_apply` (escreve no bloco e devolve a barreira inicial) |
| Chefe | handle `shatter_boss`: `_create`, `_destroy`, `_reset`, `_start`, `_step`, `_apply_damage`, `_apply_effect`, `_events`, `_info_get`, `_shield_covers` |
| Único | `shatter_save_boss_progress_get`, `shatter_save_roll_boss_loot` |
| Expedição | `shatter_expedition_forecast_ex` (com `calibration`), `shatter_save_start_expedition_trusted`, `shatter_save_collect_expedition_trusted` |
| `lookup_json` | prefixos novos `potion.` e `modifier.elite.`; `enemy.*` traz escudo, giros, imunidades, `ai`, `phases` e `patterns`; `skill.*` traz cone, empurrão, velocidade de projétil e o selo; `effect.*` traz `interrupts_action`; `item_base.*` e `unique.*` trazem `visual_set_id`; `loot.*` traz as colunas fixas |

Retiradas (comportamento): `shatter_save_start_expedition` e `shatter_save_collect_expedition` (seção 7.3). JSON: o pedido de expedição perde `potion_heal_fraction`; o progresso troca `potions_left` por `potion_slots`, `dodge_charges/recharge`, `ward_amount/remaining`; o recibo ganha `dodges_used`; o resultado ganha `calibration`. `shatter_save_read` com banco normaliza os slots de poção (save migrado do v1).

### 7.5 Testes (CMake)

`shattercore_tests`: 146 (eram 107); `shattercore_c_api_tests`: 21 (eram 11); `save_rf51_python_validator` passa com o `save_v2.schema.json`. Novos: `test_potions_dodge.cpp`, `test_status_boss.cpp`, `test_elite_unique.cpp` e os `c_api_11_*`. Fixtures (`tests/data`, `rich`, `invalid/*`) no esquema novo; `rich` ganhou poções, modificadores, fases, padrões, IA, elite fixo com Escudo, calça e o Único como entrada fixa; `golden/expeditions.txt` regravado (o `resultHash` mudou de propósito: retreat 0,25, recarga de poção, esquiva com cargas, selo de calibração no hash); `saves/save_v2.json` publicado. **O Unity precisa regravar o golden do EditMode** (`Rules.GoldenExpedition`) e a DLL.

### 7.6 Pendências e pontos sensíveis

- **Dados.** (a) `rules.csv`: `dodge_cancel_recovery_fraction` e `out_of_combat_seconds` (hoje só padrão do core); (b) `enemies.csv`: coluna opcional `eliteLootTableId` (sem ela o elite sorteado usa a tabela do inimigo, não `loot.crypt.elite`); (c) `boss_phases.csv`: `transitionSeconds` da fase 1 = 1,5 reproduz "a 1ª ação 1,5 s depois de entrar"; hoje está vazio (usa o atraso sorteado); (d) o stagger de 2,0 s e a queda do escudo na batida da Investida na parede (4.3, hipótese) **não** existem no core (sem chave em `rules.csv`); (e) `save_v2.schema.json`: `data.save_version` era `const 1`, corrigido para 2 (e a migração de referência do validador atualiza o campo); `Loc/content.csv` ganhou `item_base.worn_trousers.name`.
- **Balanceamento.** Com o conteúdo real, o Guerreiro nível 4 sem equipamento recua em ~1 min no idle (3 cargas de Vida, bandos de Cães): o Game Designer deve olhar `idleDamageTakenMult`/perfis antes do playtest. O teste de ponta a ponta usa nível 20.
- **Unity/C#.** `shatter_move_speed` com base <= 0 para o herói; chamar `shatter_potions_to_save` e gravar o save quando mudar de cena; o `IRulesCore.CanAct/CanMove` vira `shatter_can_act/_move` com o `shatter_actor`; Guarda Quebrada e stun passam por `shatter_actor_apply_effect` / `shatter_boss_apply_effect` (não por `shatter_effects_apply`); `remove_barrier` e `interrupted` são ordens do core ao C#.
- **Revisão do orquestrador.** Tudo que toca confiança de save e de resultado (7.3) e a derivação da seed. Nenhum segredo, credencial ou dado pessoal foi tocado.


---

## 8. Rodada 2: balanceamento e dados (Backend + Dados, 16/10/2026, `etapa2/backend`)

Origem: `docs/design/13_design_pendencias.md`, "Balanceamento e dados — rodada 2". Core, CSV, esquemas, validador e `docs/tecnico/06_dados.md` no mesmo branch.

### 8.1 Mudanças

| # | Onde | Mudança |
|---|---|---|
| C-21 | `constants.h`, `rules.csv` | `unarmed_weapon_damage_physical` = 3 e `require_on_screen_margin` = 100 (opcionais no core, obrigatórias no validador) |
| C-22 | `combat.h` | `ComputeSkillBaseDamage(db, skill, weaponOrNull)`: golpe que escala com arma usa a arma; **sem arma, o desarmado (só físico)**; o simulador (antes: 0 de dano sem arma) e o golpe manual usam a mesma conta. API: `shatter_skill_base_damage`, `shatter_db_rules_ext2` |
| C-23 | `expedition.cpp` | **Fichas de ataque** (`enemy_ai.csv` `attackTokens`): no máximo N inimigos do MESMO tipo (`enemyId`) com o ciclo de ataque em curso; quem termina devolve a ficha, a livre vai para o mais antigo sem atacar (rodízio determinístico), sem ficha espera sem acumular atraso. Sem linha em `enemy_ai.csv` ou com 0: sem limite (a ordem de ataque continua a do encontro). **Não simulado:** o intervalo sorteado `tokenIntervalMin/Max` entre ataques de cada Cão (só o limite de simultâneos) |
| C-24 | `combat.cpp` | **Bug do Veloz corrigido:** `ComputeActionTiming` com `EliteProfile` não depende mais de o bloco já ter os mods `source = "elite"`: velocidade-base = a do bloco SEM eles; telegraph = `windup / base` (0,3 s do Cão Veloz fica 0,3 s; antes 0,375 s se o bloco não tinha os mods); impacto e recuperação = `/ (base × attackSpeedMult)`, recuperação ainda `× recoveryMult`. Ciclo do Cão Veloz = 0,3 + (0,1 + 0,4×0,8)/1,25 = 0,636 s |
| C-25 | `boss_phases.csv` `summonAtFraction` | sai a constante `kSummonAtFractionOfTransition`; obrigatória (0 < x < 1) se `summonCount` > 0; marcador e surgimento em `transição × fração` |
| C-26 | `skills.csv` `wallStaggerSeconds` | `BossFight::OnWallHit(stats, eventos)`: a investida em **impacto** com `wallStaggerSeconds` > 0 atordoa o chefe por esse tempo (+30% de dano recebido como no stagger), interrompe o padrão e derruba o escudo (`boss_shield_down_seconds`); não dá imunidade à Guarda Quebrada. API: `shatter_boss_wall_hit` |
| C-27 | `enemies.csv` `patrolSpeedMult`, `enemy_ai.csv` `requireOnScreen` | lidos, validados (`patrolSpeedMult` em (0,1]) e expostos no `lookup_json` (`patrol_speed_mult`, `ai.require_on_screen`); quem usa é o cliente (patrulha e R-VIS-1 com o frustum e a margem) |
| C-28 | `shatter_c.h` | aditivo: `shatter_rules_ext2` (+ `shatter_layout_info_ext2/_check_ext2`, `SHATTER_LAYOUT_EXT2_COUNT` 3; o layout ext anterior, 37, não mudou), `shatter_skill_base_damage`, `shatter_boss_wall_hit`; `lookup_json` com `wall_stagger_seconds`, `phases[].summon_at_fraction` |

Dados: `rules.csv` (+2 chaves, 62), `skills.csv` (`wallStaggerSeconds`; `idleDamageTakenMult` 0,85 nas 4 habilidades do Guerreiro), `enemies.csv` (`patrolSpeedMult`), `enemy_ai.csv` (`requireOnScreen`), `boss_phases.csv` (`summonAtFraction`), os 5 esquemas, `validate_data.py` (`E_BOSS` para `summonAtFraction`; 3 mutações novas no `--self-test`) e `docs/tecnico/06_dados.md`. Fixtures de `tests/data` alinhadas; golden regravado.

### 8.2 Medição (item 2): 20 sementes de 12 h, Guerreiro nível 4, conteúdo real, `ShatterCore/tests/test_balance_probe.cpp`

Rodar com `SHATTER_BALANCE_PROBE=1 shattercore_tests balance_probe`. Regras de IA: poção de Vida abaixo de 35%, Fenda de Pedra com 3+ inimigos, Escudada em elite, Corte de Ferro. Barra com as 4 habilidades. "Fervor por hora" = a taxa do idle: **XP bruto por hora simulada** (antes do Vigor e do teto de nível, que satura em nível 5) e abates por hora. Tempo em minutos.

| Cenário | Variante | Recuaram em 12 h | Recuo em até 1 h | Tempo até recuar min / mediana / máx | XP bruto/h | Abates/h |
|---|---|---|---|---|---|---|
| só espada | **antes** (m = 1, sem fichas) | 20/20 | 20/20 | 0,7 / 2,6 / 9,0 | 10 888 | 504 |
| só espada | fichas, m = 1 | 20/20 | 20/20 | 1,0 / 4,2 / 14,5 | 11 311 | 527 |
| só espada | fichas, m = 0,92 | 20/20 | 20/20 | 1,1 / 5,5 / 22,6 | 11 425 | 532 |
| só espada | **fichas, m = 0,85** | 20/20 | 20/20 | 1,8 / 7,4 / 42,4 | 11 546 | 545 |
| só espada | fichas, m = 0,80 | 20/20 | 17/20 | 5,6 / 31,0 / 123,2 | 11 709 | 552 |
| só espada | fichas, m = 0,75 | 20/20 | 6/20 | 17,7 / 83,5 / 620,6 | 11 804 | 554 |
| só espada | fichas, m = 0,70 | 9/20 | 1/20 | 52,5 / sem recuo / sem recuo | 11 823 | 553 |
| kit completo | **antes** (m = 1, sem fichas) | 20/20 | 20/20 | 1,6 / 6,0 / 15,4 | 11 590 | 540 |
| kit completo | fichas, m = 1 | 20/20 | 20/20 | 1,8 / 12,6 / 41,7 | 11 943 | 567 |
| kit completo | fichas, m = 0,92 | 20/20 | 14/20 | 4,3 / 35,6 / 347,5 | 11 965 | 567 |
| kit completo | **fichas, m = 0,85** | 18/20 | 3/20 | 17,4 / 197,0 / 719,8 | 12 058 | 565 |
| kit completo | fichas, m = 0,80 | 4/20 | 1/20 | 25,8 / sem recuo / sem recuo | 12 076 | 564 |
| kit completo | fichas, m = 0,75 | 0/20 | 0/20 | sem recuo | 12 089 | 564 |
| kit completo | fichas, m = 0,70 | 0/20 | 0/20 | sem recuo | 12 105 | 565 |

(Kit completo = espada, elmo, peitoral, luvas, calça e botas bases, nenhum afixo; "sem recuo" = 720 min.) Leitura: o ritmo de abates e o XP/h mal mudam entre as variantes (+/- 10%), então a meta de 30 a 40% do manual (RF-32) não se mexe. As fichas sozinhas dobram o tempo até recuar, mas não bastam. Critério do R2.1.5 (kit: recuo em 1 h <= 10% e mediana sem recuo; só espada: mediana >= 30 min): **m = 0,85 NÃO atende** (kit: 3/20 em 1 h e a mediana recua; só espada: mediana 7,4 min). **m = 0,80 atende** (kit: 1/20 em 1 h e 16/20 sem recuo em 12 h; só espada: mediana 31 min); m = 0,75 deixa o kit sem nenhum recuo em 12 h (margem grande demais para o pilar P3). O `skills.csv` ficou em **0,85** como pedido; trocar para 0,80 é uma célula nas 4 linhas. A estimativa de 0,92 do Designer (com fichas) também não atende; as contas à mão do docs/13 (6 min e 48 min) ficaram otimistas: o simulador tem o Cão sem esquiva, o Arauto e a Elite Escudada tiram 60 a 96% da vida, e a vida do herói de nível 4 é 156.

### 8.3 Câmera

`SO_RenderSettings.asset`: `yawDegrees: 45` (e `RenderSettingsAsset.yawDegrees = 45f`): yaw **+45°**. O core não usa o ângulo (R-VIS-1 é do cliente, com `require_on_screen_margin`).

### 8.4 Testes

`shattercore_tests` 155 (eram 146) e `shattercore_c_api_tests` 23 (eram 21): `test_round2.cpp` (desarmado, fichas, Veloz, colunas novas lidas e validadas, momento da invocação, stagger de parede) e `c_api_r2_*`. `validate_data.py` e `--self-test` OK.

## 9. Rodada 3: correções da revisão do core (docs/17, Backend, 17/10/2026, `etapa2/backend`)

API C: `SHATTER_C_API_MINOR` vai de 1 para **2** (só adições; o C# deve exigir `shatter_api_minor() >= 2` para usar o que está abaixo).

| Mudança | Detalhe |
|---|---|
| `shatter_vitals` ganhou `double potion_barrier` | A parte da barreira que veio da poção (tamanho 32 -> 40). Quem guarda `shatter_vitals` no cliente deve copiar o campo; zero = sem barreira de poção. |
| `shatter_save_start_expedition_clock` (nova) | Recebe o relógio cru (`shatter_clock_input`), resolve o "agora" por dentro com o `last_seen` do SAVE (como a coleta) e inicia. Preferida ao `_trusted`. |
| `SHATTER_START_CLOCK_ROLLBACK` (novo valor de `start_check`) | O início confiável recusa com o relógio voltando (RF-48): nada muda. Vale para `_clock` e `_trusted`. No `_trusted` o core também confere `now` contra o `last_seen` do save e a tolerância (o chamador não escolhe o início). Início aceito: `start_utc = max(now, last_seen)` e `last_seen` sobe. |
| `shatter_save_start_expedition_trusted` | Mesmo comportamento acima; JSON com `seed` ou `start_utc` continua INVALID_ARGUMENT. `shatter_save_collect_expedition_trusted` recusa expedição sem `character_index` válido. |
| `shatter_elite_apply` | Não recebe mais multiplicadores do chamador: monta o perfil pelo `modifier_id` + valores sorteados (`rolled`) e o banco; id desconhecido = NOT_FOUND. Reaplicar no mesmo bloco é idempotente (remove os modificadores de origem `elite` antes). |
| Layout 1.1 completo | `kLayoutExt` confere TODOS os campos das 15 structs de extensão (`SHATTER_LAYOUT_EXT_COUNT` = 114). Um espelho C# com campos trocados é recusado por `shatter_layout_check_ext`. |
| `shatter_boss` x `shatter_db` | Cada chefe vivo segura uma referência do banco: `shatter_db_destroy` com chefes vivos só marca o banco para destruição e libera quando o último chefe sai (sem uso de memória liberada). Contrato single-thread (sem `<atomic>` no core). |

Save v2 (leitura recusa com `BadData`, sem migração; saves honestos nunca caem aqui):
- `boss_progress`: `enemy_id` vazio, repetido, `kills` fora de 0..1.000.000 (`kMaxBossCounter`) ou `kills_since_unique` fora de 0..`kills`.
- `potion_slots`: `charges` fora de 0..1000, `recharge_remaining` fora de 0..1e9 s, `potion_id` repetido. Na carga, `recharge_remaining` é limitado a `rechargeSeconds` da poção.
- Expedição: `start_utc` fora de 0..253402300799; `character_index` fora da faixa ou inexistente quando o status não é `none`.

Conteúdo (CSV): as **62 chaves** de `rules.csv` agora são obrigatórias quando o conteúdo vem de CSV (chave faltando = erro de validação `E_REQUIRED`); `constants.h` guarda só 0 neutro, nenhum número de balanceamento escondido. `potions.csv`, `elite_modifiers.csv`, `boss_phases.csv`, `boss_patterns.csv` e `enemy_ai.csv` são obrigatórias (arquivo ausente em `LoadDirectory` = E_IO; carregar regras sem uma delas = `E_REQUIRED` no `Finalize`). Entrada de loot fixa só vale na tabela de topo de um chefe (fora disso `E_RULE`); `tools/dados/validate_data.py` aceita peso vazio em entrada fixa por `fixedChance`, `guaranteeFirstKill` ou `pityKills`, e rejeita entrada fixa fora da tabela de topo (`E_FIXED_TABLE`).

Regras: barreira da poção igual no manual e no idle (`ApplyPotionBarrier`/`TickPotionBarrier`, uma só implementação); poção cheia não é gasta ao ganhar carga de elite e a carga vai para a poção com `refillOnEliteKill` que não estava cheia; DoT do herói no idle respeita a barreira do elite; explosão do Volátil e DoT recebido no idle usam `idleDamageTakenMult`; `ComputeExpeditionWindow` usa `double` na janela (sem estouro com `start_utc` extremo).

## 10. API C 1.3: fuga do inimigo no core (Backend, 17/10/2026, `etapa2/backend`)

`SHATTER_C_API_MINOR` vai para **3** (só adições). A decisão de fuga (antes em C#, `EnemyCombatLogic.UpdateFlee`) passa a ser do core, no `shatter_actor`, lida de `enemy_ai.csv` (`fleeLifeFraction`, `fleeSeconds`, `fleeOncePerLife`). O C# não compara vida com fração nem conta o tempo de fuga: só chama o passo e move o inimigo para longe do alvo.

| Função / tipo | Contrato |
|---|---|
| `shatter_actor_flee_step(actor, dt, life, max_life, has_target, dead, shatter_flee_result* out)` | Uma vez por tick de IA. Ator criado com o `enemy_id` do inimigo. Vida < fração x vida máx. (estritamente), com alvo e fora do "uma vez por vida" gasto: `started = 1`, `fleeing = 1`, dura `fleeSeconds`. Em curso: `remaining` cai; acaba por tempo ou sem alvo (`ended = 1`, `fleeing = 0`). Iniciar e acabar nunca no mesmo passo. Morto (`dead != 0`) não foge. `dt < 0` ou valores não finitos: INVALID_ARGUMENT. |
| `shatter_actor_flee_reset(actor)` | Revive: zera a fuga e libera o "uma vez por vida". |
| `shatter_flee_result` | `double remaining; u8 fleeing, started, ended, can_flee; u8 reserved[4]` (16 bytes). `can_flee = 0`: inimigo sem linha em `enemy_ai.csv`, fração 0 ou ator do herói (enemy_id vazio): nunca foge. |
| `shatter_layout_info_ext3` / `shatter_layout_check_ext3` (`SHATTER_LAYOUT_EXT3_COUNT` = 6) | `[tamanho, offsets de remaining, fleeing, started, ended, can_flee]`. Chamar o check na inicialização, como os outros. |

Ao `started`, o cliente cancela o telegraph e o golpe em curso (o core não controla a animação). O C# deve exigir `shatter_api_minor() >= 3`. No core: `FleeProfile`/`FleeState`/`FleeStep` em `combat.h`.

Paridade: o simulador idle NÃO modela fuga de inimigo (eles lutam até morrer; só o herói recua, `retreatLifeFraction`), então não existe lógica idle de fuga para igualar. A regra única fica no core (`FleeState`) e os testes (`test_flee.cpp`, `c_api_13_*`) fixam o comportamento do `UpdateFlee` anterior (limite estrito, tempo, sem alvo, uma vez por vida, revive) lendo os números do CSV real.

## 11. API C 1.4: inventário, equipamento, venda e loot no chão (Backend, 17/10/2026, `etapa2/backend`)

`SHATTER_C_API_MINOR` vai para **4** (só adições; o C# deve exigir `shatter_api_minor() >= 4`). Regra de docs/16 seção 4 e docs/09 9.2 (itens 1 a 3) no core, em `inventory.h`/`inventory.cpp`; o cliente só mostra. Sem RNG nas operações de inventário (mesmo estado, mesmo resultado).

**Dados novos** (`rules.csv`, 18 chaves obrigatórias, todas [HIPÓTESE] de docs/16): `inventory_capacity` (40), `stash_capacity` (100), `sell_price_normal/magic/rare/unique` (4/12/35/100), `sell_level_factor` (0.1) e `equip_slot_<slot>` x 11 (liberadas: main_hand, head, body, hands, feet, legs; bloqueadas: off_hand, amulet, ring, ring2, belt). Esquema, validador (`E_SLOT_LOCKED`, `E_RULES` e três mutações no `--self-test`) e docs/06 atualizados. **Save**: `characters[].backpack` opcional (ver docs/06); sem migração.

**Resultados** (`*result`, a função devolve OK; INVALID_ARGUMENT só para ponteiro nulo ou personagem fora da faixa; recusa não muda nada): `SHATTER_INV_OK, NOT_FOUND, FULL, SLOT_MISMATCH, SLOT_LOCKED, SLOT_EMPTY, UNKNOWN_CONTENT`. Contêineres: `SHATTER_CONTAINER_BACKPACK = 0`, `SHATTER_CONTAINER_STASH = 1`. Itens são achados por `uid` (uint64).

| Função | Contrato |
|---|---|
| `shatter_inventory_info_get(db, save, ci, shatter_inventory_info*)` | `{backpack_capacity, backpack_used, stash_capacity, stash_used}` (int32 x 4) |
| `shatter_inventory_slot_enabled(db, slot, uint8* enabled)` | posição liberada em `equip_slot_*` (slot na ordem de `ItemSlot`, 0..10) |
| `shatter_inventory_list_json(save, ci, container, buf...)` | array JSON de `ItemInstance` da Mochila ou do Baú; o equipamento vem em `shatter_save_character_json` |
| `shatter_inventory_sort(db, save, ci)` | ordena a Mochila por posição, raridade (Único primeiro), itemLevel (maior primeiro), base e uid |
| `shatter_inventory_move(db, save, ci, uid, to, *result)` | Mochila <-> Baú; destino cheio = `FULL` |
| `shatter_inventory_equip(db, save, ci, uid, slot, shatter_statblock* stats, shatter_equip_result*)` | equipa o item da Mochila (`slot = -1`: posição padrão; anel: a primeira livre entre ring e ring2). Valida posição liberada e compatível. O antigo volta à Mochila (`displaced`, `displaced_uid`). Com `stats`, só os modificadores dos itens trocados saem/entram (o resto do bloco fica) |
| `shatter_inventory_unequip(db, save, ci, slot, stats, *out)` | para a Mochila; `FULL` ou `SLOT_EMPTY` sem mudar nada |
| `shatter_inventory_compare(db, save, ci, uid, slot, buf...)` | tooltip: `{"result","slot","equipped_uid","is_weapon","weapon_dps_before","weapon_dps_after","deltas":[{"stat","before","after"}]}`; só os atributos que mudam; DPS da arma = dano x velocidade de ataque, com implícito e afixos (docs/16 4.3). O item pode estar na Mochila, no Baú ou no chão. Nada é alterado |
| `shatter_inventory_sell_value(db, save, ci, uid, int64* value)` | valor em Ouro, sem vendedor: `preço da raridade x (1 + fator x (itemLevel − 1))`, arredondado |
| `shatter_inventory_sell(db, save, ci, container, uid, int64* gold, *result)` | vende da Mochila ou do Baú; o valor entra em `currency.gold` no mesmo save. Idempotente (repetir o uid dá `NOT_FOUND` e `gold = 0`). Equipado não vende |
| `shatter_inventory_discard(save, ci, container, uid, *result)` | destrói o item |
| `shatter_item_visual_set_id(db, base_id, len, unique_id, len, buf...)` | `uniques.visualSetId`, depois `item_bases.visualSetId`, depois `vset.starter` (texto UTF-8 sem NUL, duas chamadas); id desconhecido = `NOT_FOUND`. A Unity não lê mais o CSV |
| `shatter_save_drop_loot(db, save, table, ctx, rng, buf..., err)` | rola a tabela (como `shatter_loot_roll`, mesmo RNG de loot e contexto, uids do save) e põe os itens **no chão**; Ouro e Lascas entram direto no save. Devolve o mesmo JSON de `shatter_loot_roll`. Buffer pequeno: nada muda |
| `shatter_save_ground_add_loot(save, loot_json, len, err)` | põe no chão um loot já rolado (ex.: `shatter_save_roll_boss_loot`, com o Único do chefe) |
| `shatter_save_ground_list(save, buf...)` | `{"items":[ItemInstance...]}` na ordem de queda |
| `shatter_save_pickup(db, save, ci, uid, *dest)` | chão -> Mochila (`SHATTER_PICKUP_BACKPACK`); Mochila cheia e item Único -> Baú (`..._STASH`, nunca fica sem dono, docs/16 fluxo do chefe); senão `..._FULL` e o item FICA no chão; uid desconhecido = `..._NOT_FOUND` |
| `shatter_save_ground_discard(save, uid, *result)` / `shatter_save_ground_clear(save)` | destrói um item do chão / limpa o chão (ao sair da Cripta) |
| `shatter_layout_info_ext4` / `shatter_layout_check_ext4` (`SHATTER_LAYOUT_EXT4_COUNT` = 10) | `[tamanho de shatter_inventory_info, 4 offsets, tamanho de shatter_equip_result, 4 offsets]` |

`shatter_equip_result`: `{int32 result; int32 slot; uint64 displaced_uid; uint8 displaced; uint8 reserved[7]}` (24 bytes). Ordem do Refúgio para o chefe: grave o save (`shatter_save_write`) antes de `ground_add_loot` do Único (RF-55); o chão não é salvo, então o Único só pode ficar no chão se o contador já foi gravado.

Fora do escopo desta rodada (decisão do dono ou UI): requisito de nível do item, "Vender Comuns ao coletar" (a coleta atômica da expedição continua entregando ao Baú), confirmações e desfazer 5 s (UI), uso do Ouro (docs/16 Q3-3).

## 12. API C 1.5: combate básico com combo, ataque forte e defesa (Backend, 17/10/2026, `etapa3/combate-core`)

Origem: `docs/design/18_combate_combo.md` (seção 8 e as decisões do orquestrador em 8.1). `SHATTER_C_API_MINOR` vai para **5** (só adições; o C# deve exigir `shatter_api_minor() >= 5`). **A máquina de combate básica fica no C#** (`HeroCombatLogic`, passo fixo de 60 Hz): índice do combo, buffer, janelas, limiar de segurar, carga com multiplicador linear, cancelamentos e a geometria do arco da defesa. O core guarda e valida os NÚMEROS (`basic_kits.csv` e 7 chaves de `rules.csv`) e continua resolvendo dano, efeitos, defesa e recurso. O item 4 do docs/18 seção 8 (máquina no core) não vale.

### 12.1 Dados

| Onde | Mudança |
|---|---|
| `rules.csv` | 7 chaves obrigatórias: `combo_window`, `combo_window_after_dodge`, `attack_buffer`, `heavy_hold_threshold`, `light_windup_credit_max`, `guard_lower_time`, `dash_shot_range` (87 no total; faixas: tempos 0 a 5 s, crédito 0 a 1, alcance 0 a 10000 uu). `RulesConstants` ganha os 7 campos com 0 neutro |
| `basic_kits.csv` (nova, OPCIONAL) | Kit por classe (`ContentDB::FindBasicKit`, `BasicKits()`, `BasicKitData`). Validação: classe existe e sem linha repetida, `lightChain` de 1 a 3 (repete permitido), habilidades da própria classe, efeitos existentes, `guardEffect` com a tag `guard`, `heavyChargeTime` > 0, `heavyMaxMult` >= 1, `guardArc` 0 a 360, no máximo 4 efeitos da defesa perfeita, IDs de até 63 bytes. Arquivo ausente em `LoadDirectory` não é erro |
| `skills.csv` `pierce` | Coluna opcional, 0 a 99 (99 = atravessa todos), só `shape = projectile`. `SkillData::pierce`, `kPierceAll` |
| `effects.csv` tag `guard` | Nova tag (`Tag::Guard = 1 << 9`, `kTagCount` 10, `SHATTER_TAG_GUARD`). Efeito com a tag: os mods de `damage_taken` ganham a exigência da tag ao entrar no StatBlock |
| Conteúdo (docs/18 4.1 a 4.7) | 13 habilidades, 6 efeitos, 2 classes (Arqueiro e Mago), `class_stats`, `item_base.hunter_bow`, chaves de Loc em pt-BR |

### 12.2 Regras no core

| Item do docs/18 §8 | Implementação |
|---|---|
| 1, 2 | `basic_kits.csv` lida e validada com erros tipados (`E_FK`, `E_RANGE`, `E_RULE`, `E_DUP_ID`, `E_TYPE`, `E_HEADER`); as 7 chaves lidas e validadas; `pierce` lida e validada |
| 3 (a) a (e) | `ClassifySkill(SkillData) -> SkillBehavior`: `explodes` (projétil com `radius` > 0), `fan` (projétil com `projectiles` > 1 e `coneAngle` > 0), `selfCentered` (área com `range` 0), `groundTargeted` (área com `range` > 0), `dashBackShot` (dash com tag `projectile`; pula `range` e atira em `dash_shot_range`). Validação no `Finalize`: leque sem ângulo, área sem raio, dash com tiro sem `dash_shot_range`, `pierce` fora de projétil. Exposto no `lookup_json` da habilidade (`pierce`, `behavior`). A geometria em si continua no C# |
| 5 (defesa) | `HitInput::fromGuardArc` (C: `shatter_hit_input.from_guard_arc`, antes `reserved[0]`). Passo 8 de `ResolveHit`: `defender.GetTagged(DamageTaken, fromGuardArc ? guard : nenhuma)`. Os mods de efeito `guard` só valem se o chamador diz que o golpe veio de dentro do arco; os demais mods do alvo não dependem disso. O consumo de RNG não muda. **Não implementado no core** (ficam no C#, com os valores do kit): tempo máximo da defesa, espera, janela da defesa perfeita, dano zero da perfeita, efeitos no atacante, dreno de Mana por ponto evitado |
| 6 | `ResourceOnHit/OnBlock(cls)` e `GainResourceOnHit/OnBlock(vitals, stats, cls)` (combat.h); o simulador idle usa as mesmas funções. API: `shatter_vitals_gain_on_hit`, `shatter_vitals_gain_on_block` |
| 7 | `TickVitals(..., bool moving = false)`: o recurso regenera × `regenMultWhileMoving` com o herói andando (Foco 0,3); a vida não muda; sem classe, nada. API: `shatter_vitals_tick_ex` (o `shatter_vitals_tick` antigo = parado) |
| 8 | `IsIdleCompatible` olha o golpe 1 do kit e a barra (Q/E/R); golpes 2 e 3 do combo e o golpe forte do kit (`IsKitOnlySkill`) não exigem perfil idle, mesmo na barra. Arqueiro e Mago ficam bloqueados para expedição (`IdleIncompatible`, RF-43, esperado). `BuildIdleCalibration` ignora os mesmos golpes |
| 9 | `cast_speed` tem base neutra 1 (`StatBlock`); o Mago sem o atributo conjura nos tempos do CSV. Teste fixa |
| 10 | `ctest` e `validate_data.py` com 3 classes; nenhum teste de classe única precisou de ajuste de lógica (só as colunas novas dos fixtures) |

### 12.3 API C 1.5 (aditiva)

| Função / tipo | Contrato |
|---|---|
| `shatter_hit_input.from_guard_arc` | 1 = o golpe veio de dentro do arco da defesa do alvo. 0 (o que chamadores antigos já mandavam) = fora. Tamanho do struct inalterado (64) |
| `SHATTER_TAG_GUARD` (1 << 9) | Tag de efeito de defesa. `shatter_statblock_get(sb, DAMAGE_TAKEN, SHATTER_TAG_GUARD)` dá o dano recebido DENTRO do arco; com tags 0, fora |
| `shatter_resolve_hit_charged(db, atk, def, input, class_id, len, charge_fraction, rng, out, err)` | Golpe do ataque forte (adição de 17/10). O CORE calcula `1 + (heavy_max_mult - 1) * charge_fraction` com o kit da classe e aplica como `more` só neste golpe, depois dos modificadores do atacante e antes do crítico (`HitInput::hitMore`, `HeavyChargeMultiplier`). Fração fora de [0,1] ou NaN: INVALID_ARGUMENT com mensagem em `err`, sem efeito e sem avançar o rng; classe sem kit: NOT_FOUND. Função própria, e não campo em `shatter_hit_input`, porque só sobra 1 byte livre no struct de 64 bytes. C#: `HitRequest.IsHeavy`, `ChargeFraction`, `ClassId` (o C# não escala o coeficiente) |
| `shatter_combat_rules` + `shatter_db_combat_rules(db, out)` | 7 doubles: `combo_window`, `combo_window_after_dodge`, `attack_buffer`, `heavy_hold_threshold`, `light_windup_credit_max`, `guard_lower_time`, `dash_shot_range` |
| `shatter_basic_kit` + `shatter_basic_kit_get(db, class_id, len, out)` | Kit da classe (720 bytes). 9 doubles (`heavy_charge_time`, `heavy_max_mult`, `guard_arc`, `guard_max_hold`, `guard_cooldown`, `guard_perfect_window`, `guard_perfect_cooldown`, `guard_perfect_resource`, `guard_drain_per_damage`), `int32 light_chain_count` (1 a 3), `int32 guard_perfect_effect_count` (0 a 4), `char light_chain[3][64]`, `heavy_skill[64]`, `charge_effect[64]`, `guard_effect[64]`, `guard_perfect_effects[4][64]` (UTF-8, NUL). NOT_FOUND: classe inexistente ou sem linha |
| `shatter_vitals_tick_ex(db, vitals, stats, class_id, len, dt, in_combat, moving)` | Como `shatter_vitals_tick`, com o herói andando ou parado |
| `shatter_vitals_gain_on_hit` / `shatter_vitals_gain_on_block` `(db, vitals, stats, class_id, len)` | Recurso por golpe e por bloqueio da classe, limitado ao máximo; class_id vazio/nulo = nada; classe desconhecida = INVALID_ARGUMENT |
| `shatter_layout_info_ext5` / `shatter_layout_check_ext5` (`SHATTER_LAYOUT_EXT5_COUNT` = 26) | `[offset de from_guard_arc, sizeof(shatter_combat_rules), 7 offsets, sizeof(shatter_basic_kit), 9 offsets dos doubles, light_chain_count, guard_perfect_effect_count, light_chain, heavy_skill, charge_effect, guard_effect, guard_perfect_effects]`. Chamar o check na inicialização |

### 12.4 Para o Frontend / Integração

C# (`Interop`): `CombatRules` ganhou `ComboWindowSeconds`, `ComboWindowAfterDodgeSeconds`, `AttackBufferSeconds`, `HeavyHoldThresholdSeconds`, `LightWindupCreditMax`, `GuardLowerTimeSeconds`, `DashShotRangeUu`; `HitRequest.FromGuardArc`; `SkillTags.Guard`; `SkillInfo.Pierce`, `SkillInfo.Behavior` (`SkillBehavior`); `BasicKitInfo` (`IRulesCore.FindBasicKit(classId)`); `IRulesCore.TickVitals(..., moving)`, `GainResourceOnHit`, `GainResourceOnBlock` (membros com implementação padrão; o stub não os precisa). Não foi possível compilar na Unity neste worktree.

### 12.4b Adições de 17/10 (mesma branch)

- **Ataque forte no core**: `shatter_resolve_hit_charged` (tabela 12.3). O C# não escala mais o coeficiente: use `HitRequest.IsHeavy` + `ChargeFraction` + `ClassId`.
- **`knockback`**: já era lido e validado (`SkillData::knockback`) e já saía no `shatter_db_lookup_json` (`knockback`); o C# agora o expõe como `SkillInfo.KnockbackUu`. Layout inalterado (nenhuma struct nova).
- **`explosionRadius`** (coluna opcional nova, última de `skills.csv`): raio da explosão de projétil, separado de `radius` (largura de colisão). `SkillData::explosionRadius`; `SkillBehavior::explodes` = projétil com `explosionRadius` > 0; `lookup_json` `explosion_radius`; erro `E_RULE` (core) / `E_EXPLOSION` (validador) fora de projétil. Dados: `fireball` radius 35 / explosionRadius 220, `arcane_orb` radius 25 / explosionRadius 130 (as larguras 35 e 25 são [HIPÓTESE], o docs/18 só tinha o raio da explosão). C#: `SkillInfo.ExplosionRadiusUu`, `SkillInfo.RadiusUu` passa a ser só colisão em projétil.

### 12.5 Testes e pendências

Testes novos em `test_combat_basic.cpp` (18) e `test_c_api.cpp` (3, `c_api_15_*`), `validate_data.py` com 8 mutações novas. Pendências: (1) defesa perfeita, limite de tempo, dreno de recurso e empurrão por tipo de alvo (docs/18 §8 itens 5 e 11) ficam no C# com os valores do kit; (2) o stub em C# ignora `moving`, kit, `pierce` e comportamento (só o núcleo nativo preenche); (3) Arqueiro e Mago sem expedição por decisão do dono (Q18-2).

## 13. API C 1.6: economia do protótipo, Vendedor, Frasco de Recarga e Encantador (Backend, 18/10/2026, `etapa3/economia`)

Origem: `docs/design/16_etapa3_fluxo.md` seção 11, com as decisões Q3-5 A (2 afixos novos de arma) e Q3-6 A (Reforjar sem desfazer, com trava de 1 afixo e aviso). `SHATTER_C_API_MINOR` vai para **6** (só adições; o C# deve exigir `shatter_api_minor() >= 6` e chamar `shatter_layout_check_ext6`). Código novo: `craft.h/.cpp` (Encantador), `vendor.h/.cpp` (Vendedor e frasco); o resto é adição em `rng.h`, `item.h`, `constants.h`, `content.*`, `loot.*` e `save.*`.

### 13.1 Dados

| Onde | Mudança |
|---|---|
| `rules.csv` | 15 chaves obrigatórias (102 no total): `vendor_buyback_slots`, `vendor_buyback_price_factor`, `refill_flask_carry_cap`, `refill_flask_charges`, `craft_cost_level_factor`, `reforge_step_mult`, `reforge_mult_cap`, `reforge_lock_cost_mult`, `reforge_lock_max`, `add_affix_candidates`, `polish_step_fraction`, `polish_max_steps`, `dismantle_shards_normal/magic/rare`. `RulesConstants` ganha os campos (0 neutro) |
| `craft_costs.csv`, `vendor_stock.csv` | Tabelas NOVAS e OPCIONAIS (como `basic_kits.csv`: arquivo ausente não é erro; sem `craft_costs` o Encantador recusa com `UnknownContent`). Validação no `Finalize` (`E_RULE`, `E_RANGE`, `E_DUP_ID`, `E_ID_PREFIX`): passo 1.. só na Lapidar, Refinar só `normal`, linha de custo para cada operação e raridade e para cada passo de Lapidar até `polish_max_steps`, `carryCap` do frasco igual a `refill_flask_carry_cap` |
| `affixes.csv` | `craftInscription = true` nos afixos do protótipo; afixos novos de arma `affix.scorching` (dano de fogo aumentado) e `affix.of_ruin` (multiplicador de crítico), depois trocados em `Content/Data` por `affix.ruthless` e `affix.of_cadence` do docs/19 (a seção 14); o fixture de teste `tests/data/rich` mantém os dois. "Vida por acerto" não existe como atributo: criar exigiria mexer no combate e no idle |
| Loc | Vendedor e Encantador por chave provisória (`npc.*.name`, `ui.vendor.*`, `ui.enchant.*`, `consumable.refill_flask.*`), sem lore |

### 13.2 Save (v2, campos OPCIONAIS; sem novo `save_version` e sem migração)

Só são gravados se diferentes de zero/vazios, então saves antigos mantêm os mesmos bytes e hash (os saves `save_v1`/`save_v2` de teste continuam passando). `SaveData.craftSeed` (`craft_seed`, uint64 em texto), `SaveData.vendorBuyback` (`vendor_buyback`: até `vendor_buyback_slots` de `{item, paid}`, o mais recente primeiro), `ItemInstance.craftSteps` (`craft_steps`), `ItemInstance.craftReforges` (`craft_reforges`, preço do próximo Reforjar) e `RolledAffix.polish` (`polish`, 0 a `polish_max_steps`). Faixas validadas na leitura (save adulterado é recusado). Ouro (`currency.gold`), Lascas (`material.shards`) e Frasco de Recarga (`consumable.refill_flask`) são pilhas de `currencies`: formato inalterado. Como não houve mudança de formato incompatível, **não há migração**; um save sem `craft_seed` usa `EffectiveCraftSeed` (função estável do nome e da classe do primeiro personagem), e a primeira melhoria grava exatamente esse valor (fixar a semente não muda sorteio algum).

### 13.3 Regras no core

- `RngStream::Crafting = 4`. Semente por operação = função pura de (`craft_seed`, `uid`, `craft_steps` do item, operação) em `CraftRng`; nada consome `Loot`. Recarregar o save antes de confirmar não muda o sorteio. `craft_steps` sobe a cada Refinar, Reforjar e Adicionar; Lapidar não sorteia e não sobe.
- `PlanCraft` só lê o save e decide tudo (custo, resultado, item depois); `CommitCraft` só escreve (cobra e aplica juntos, confere o plano contra o save e o saldo de novo). Operação que não chega ao Commit deixa o save byte a byte igual.
- Custo = base x (1 + `craft_cost_level_factor` x (itemLevel - 1)), arredondado para cima (margem de 1e-9 contra ruído de ponto flutuante). Reforjar x `min(reforge_mult_cap, 1 + reforge_step_mult x reforges anteriores)`; travar 1 afixo multiplica só as Lascas por `reforge_lock_cost_mult`.
- Refinar (Comum vira Mágico, 1 a 2 afixos), Reforjar (mantém quantidade e inscrição, zera a lapidação dos novos, mantém valor e lapidação do travado; se o sorteio guloso empacar num conjunto pequeno, tenta de novo até 16 vezes e por fim mantém os mesmos afixos com valores novos), Adicionar afixo (oferta de até `add_affix_candidates` sem repetição, só `craftInscription`, respeitando slot, nível, grupo e 2+2; a aplicação recalcula a oferta, não confia no cliente), Lapidar (sobe `polish_step_fraction` da faixa; inteiros arredondam e andam pelo menos 1; recusa no máximo ou no passo `polish_max_steps`), Desmontar (Lascas por raridade; só Mochila e Baú).
- Vendedor: `VendorSell` paga `SellValue`, guarda o item na recompra e expulsa o mais antigo no 11º; `BuybackPrice` = ceil(pago x `vendor_buyback_price_factor`); recompra e venda são idempotentes por `uid`; `VendorBuy` respeita `carryCap` e Ouro.
- Frasco: `UseRefillFlask` age sobre o cinto vivo (`PotionBelt`) e sobre o save; recusa por contexto `Arena`/`Idle`, sem frasco, poções cheias (não gasta) e trava global (`LockedOut`); restaura `refill_flask_charges` da poção com menos cargas (empate: a primeira do CSV, a Vida); inicia a trava global da poção.
- `RollAffixes` ganhou irmãos (`EligibleAffixes`, `RollAffixValue`, `RollAffixesFixed`); o sorteio do loot não mudou (mesma sequência).

### 13.4 API C 1.6

| Função | Contrato |
|---|---|
| `shatter_currency_get(save, id, len, int64* amount)` | saldo de uma pilha (0 se não existe) |
| `shatter_craft_quote_json(db, save, ci, uid, op, arg, buf...)` | prévia sem custo: `{op,result,gold,shards,shards_gain,affix_count_min/max,polish_step,polish_from/to,shards_with_lock,shards_no_lock,reforges,expedition_running,have_gold,have_shards}`; `NO_GOLD`/`NO_SHARDS` trazem os custos. `arg`: Reforjar = afixo travado (-1), Lapidar = afixo, Adicionar = -1 |
| `shatter_craft_refine(db, save, ci, uid, shatter_craft_result*)` | Refinar |
| `shatter_craft_reforge(db, save, ci, uid, locked_affix_index, ...)` | Reforjar (-1 = sem trava) |
| `shatter_craft_add_affix_offer(db, save, ci, uid, buf...)` | `{result,gold,shards,candidates:[{affix_id,min,max}]}`; não altera; mesma saída se repetida |
| `shatter_craft_add_affix_apply(db, save, ci, uid, candidate_index, ...)` | confirma o candidato |
| `shatter_craft_polish(db, save, ci, uid, affix_index, ...)` | um passo de Lapidar |
| `shatter_craft_dismantle(db, save, ci, uid, ...)` | Desmontar |
| `shatter_vendor_sell(db, save, ci, container, uid, shatter_vendor_result*)` | vende ao Vendedor (vai para a recompra) |
| `shatter_vendor_buyback_json(db, save, buf...)` | `{capacity,count,would_evict,evict_rarity,items:[{item,paid,price}]}`, o mais recente primeiro |
| `shatter_vendor_buyback(db, save, ci, uid, ...)` | recompra POR UID (não por índice: o índice muda a cada venda e dois cliques comprariam itens diferentes) |
| `shatter_vendor_stock_json(db, save, buf...)` | `[{id,ref_id,price_gold,carry_cap,owned}]` |
| `shatter_vendor_buy(db, save, stock_id, len, qty, ...)` | compra (`qty` >= 1) |
| `shatter_flask_use(db, save, potions, context, shatter_flask_result*)` | Frasco de Recarga; `context` 0 = corrida, 1 = arena, 2 = idle. Recebe o cinto vivo `shatter_potions*` (sem `ci`: o cinto já é de um personagem) |
| `shatter_layout_info_ext6` / `shatter_layout_check_ext6` (`SHATTER_LAYOUT_EXT6_COUNT` = 16) | `[sizeof(shatter_craft_result), 5 offsets, sizeof(shatter_vendor_result), 4 offsets, sizeof(shatter_flask_result), 4 offsets]` |

Resultados: `SHATTER_CRAFT_*` (`OK, NOT_FOUND, UNIQUE, WRONG_RARITY, AFFIX_LIMIT, ALREADY_INSCRIBED, POLISH_MAX, NO_CANDIDATE, NO_GOLD, NO_SHARDS, EQUIPPED_DISMANTLE, UNKNOWN_CONTENT, BAD_INDEX`), `SHATTER_VENDOR_*` (`OK, NOT_FOUND, FULL, NO_GOLD, CARRY_CAP, BAD_QUANTITY, UNKNOWN_CONTENT`), `SHATTER_FLASK_*` (`OK, NO_FLASK, ARENA_LOCKED, IDLE_FORBIDDEN, POTIONS_FULL, LOCKED_OUT, UNKNOWN_CONTENT`). Recusa não muda nada.

### 13.5 Para o Frontend / Integração

C# em `Assets/Scripts/Interop`: `EconomyTypes.cs` (tipos), `Native/ShatterNative.Economy.cs` (P/Invoke) e `Native/SaveGame.Economy.cs`: `Currency(id)`, `QuoteCraft`, `CraftRefine`, `CraftReforge`, `CraftAddAffixOffer`, `CraftAddAffixApply`, `CraftPolish`, `CraftDismantle`, `VendorSell`, `VendorBuybackInfo`, `VendorRebuy`, `VendorStock`, `VendorBuy`, `UseRefillFlask`. `ItemInstanceInfo` ganhou `CraftSteps`, `CraftReforges` e `AffixInfo.Polish`. `ExpectedApiMinor` = 6 e o `CheckExt6` entram na inicialização. **Depois de melhorar um item equipado, refaça o bloco de atributos** (`StatsOfCharacter`); com expedição `Running` a UI mostra "Vale a partir da próxima expedição" (`expedition_running` na prévia). Gravar o save depois de cada melhoria (RF-54). Não foi possível abrir a Unity neste worktree; o C# do Interop foi compilado com o Roslyn da Unity contra netstandard 2.1.

### 13.6 Testes e pendências

`test_economy.cpp` (29 testes: dados e erros, RNG puro, cada operação e cada recusa, custo por nível e por Reforjar, atomicidade, 1000 ciclos salvar/carregar, recompra e frasco, save e a propriedade de **1 milhão de operações aleatórias** sem violar a lista "nunca pode acontecer" do docs/16 11.5) e `c_api_16_*` (3 testes na fronteira da DLL). Pendências: a falha injetada é por `PlanCraft` sem `CommitCraft` (não há ponto de falha dentro do Commit); a medição de ritmo H3-20 (A3-37) depende do `batch_sim`; `content_version` precisa de bump na próxima release (os dados mudam o loot de arma).

## 14. API C 1.7: core da Cripta (Backend, 18/10/2026, `etapa3/economia`)

Origem: auditoria do orquestrador (lacunas do jogo manual da Cripta) e `docs/19` (N0, Q19-1 A). `SHATTER_C_API_MINOR` vai para **7** (só adições; o C# deve exigir `shatter_api_minor() >= 7` e chamar `shatter_layout_check_ext7`). Código novo: `world.h/.cpp`; adições em `save.*`, `content.*`, `combat.*` e `expedition.cpp`.

### 14.1 O que entrou

| # | Lacuna | Como ficou |
|---|---|---|
| 1 | XP no jogo manual | `shatter_xp_award_kill`: `(xpBase + xpPerLevel x (nível - 1))` do `enemies.csv` x multiplicador de elite (elite sorteado: `elite_xp_mult` x modificador; elite fixo e chefe: o valor do próprio inimigo) x `fervor_xp_mult` (flag). Sobe de nível NO SAVE até o teto da área (`monsterLevel + xp_cap_levels_above_area`, até `max_level`; no teto o XP não entra), com a mesma regra da coleta de expedição (`AwardXp`). `shatter_character_progress` devolve nível, XP e XP para o próximo: o herói usa o nível do save, não um nível fixo da cena |
| 2 | Estado do mundo no save | `SaveData::world` (`world_state`: por mapa `{map_id, visits, opened[]}`). `shatter_world_object_get/set` por ID de objeto (`chest.crypt.01`, `secret.crypt.cracked_wall`, `shortcut.crypt.a`...), `shatter_world_state_json`. Limites 64 áreas e 512 objetos por área. **Migração:** o campo é opcional no save v2 (ausente = nada aberto), então não houve novo `save_version`: um save v2 sem o campo abre, grava os mesmos bytes e só passa a ter `world_state` depois do primeiro objeto aberto ou da primeira visita; testado (`world_state_survives_the_save_file_and_old_saves_load_with_nothing_opened`) |
| 3 | Baús | Tabela nova opcional `chests.csv` (`id,mapId,lootTable`). `shatter_chest_open`: tabela do baú (sem linha, ou de outro mapa: `areaLootTable` do mapa), rola como `shatter_save_drop_loot` (itens no chão, Ouro/Lascas no save), marca o baú aberto. Já aberto: nada rola, `SHATTER_CHEST_ALREADY_OPEN`. Buffer pequeno: nada muda (nem estado, nem rng) |
| 4 | Loot ao limpar um encontro | `shatter_encounter_clear_loot`: rola a `areaLootTable` do mapa (como `drop_loot`) |
| 5 | Encontros | `shatter_world_begin_visit` (incrementa as visitas e devolve a semente, função pura de craft_seed efetivo, mapa e contador: o chamador não a escolhe) e `shatter_encounter_roll_json`: n entre min e max por grupo e a elite (`chanceElite`) por espaço com o modificador, fluxo `Events`, determinístico pela semente da visita (a mesma formação depois de um checkpoint). Chefe e elite fixo nunca viram "elite sorteado". `shatter_map_info_json`: encontros na ordem do CSV, tabela da área e baús |
| 6 | Fervor | `shatter_fervor_get` para a HUD (multiplicadores e bônus: XP +200% com o CSV atual). XP usa a flag `fervor`; Ouro, materiais e chance de Raro já usavam o modo Manual do loot |
| N0 | Tempo da arma | `ComputeActionTiming` ganhou `weaponTimeFactor`; `WeaponTimeFactor` = `attackTime` da arma / `refAttackTime` da classe, só para habilidades `scalesWithWeapon` (preparação, impacto e recuperação; a recarga não muda). Coluna nova opcional `refAttackTime` em `basic_kits.csv` (0 ou ausente = sem escala). Espada inicial: fator 1; Martelo: 1,4/0,9 (a duração do golpe cresce 56%, a velocidade cai 36%). O simulador idle usa o mesmo fator para o herói. API: `shatter_skill_timing_weapon` (o `shatter_skill_timing` antigo não muda). Interpretação: "x refAttackTime / attackTime" do docs/19 é a VELOCIDADE; a duração é o inverso |
| 7 | Dados do docs/16 4.5 | `worn_trousers`, `stone_maul` e itens de baixo peso nas tabelas da Cripta, mais as linhas F1 do Guerreiro do docs/19 (bases, afixos, `off_hand` ligado, `vset.warrior_rare_01`); `affix.ruthless` e `affix.of_cadence` substituem `scorching` e `of_ruin` em `Content/Data` (o fixture `tests/data/rich` mantém os seus). **N5 (`skill_ranks.csv`) fica para a Etapa 4** |

### 14.2 API C 1.7

| Função | Contrato |
|---|---|
| `shatter_world_begin_visit(db, save, map, len, uint64* seed)` | mapa desconhecido = `NOT_FOUND` |
| `shatter_world_object_get/set(save, map, len, object, len[, opened])` | ID inválido ou limite = `INVALID_ARGUMENT` |
| `shatter_world_state_json(save, map, len, buf...)` | `{map_id,visits,opened:[...]}` |
| `shatter_map_info_json(db, map, len, buf...)` | `{map_id,monster_level,tier,area_loot_table,boss_encounter,encounters,chests:[{id,loot_table}]}` |
| `shatter_encounter_roll_json(db, enc, len, visit_seed, buf...)` | `{encounter_id,is_boss,groups:[{enemy_id,count,slots:[{elite,modifier_id}]}]}`; um grupo de n inimigos usa os n primeiros espaços do layout |
| `shatter_chest_open(db, save, map, len, chest, len, ctx, rng, buf..., int32* result, err)` | `result` = `SHATTER_CHEST_OPENED/ALREADY_OPEN/NO_TABLE`; saída = JSON do loot |
| `shatter_encounter_clear_loot(db, save, map, len, ctx, rng, buf..., err)` | mapa sem tabela = `NOT_FOUND` |
| `shatter_xp_award_kill(db, save, ci, map, len, enemy, len, monster_level, elite_rolled, modifier, len, fervor, shatter_xp_info*)` | inimigo ou modificador desconhecido = `NOT_FOUND` |
| `shatter_character_progress(db, save, ci, map, len, shatter_xp_info*)` | `map` vazio = teto `max_level` |
| `shatter_fervor_get(db, shatter_fervor_info*)` | multiplicadores e bônus |
| `shatter_skill_timing_weapon(db, skill, len, stats, class, len, weapon_base, len, shatter_action_timing*)` | `weapon_base` vazio = desarmado |
| `shatter_layout_info_ext7` / `shatter_layout_check_ext7` (`SHATTER_LAYOUT_EXT7_COUNT` = 15) | `[sizeof(shatter_xp_info), 7 offsets, sizeof(shatter_fervor_info), 6 offsets]` |

### 14.3 Para o Frontend / Integração

C# em `Assets/Scripts/Interop`: `CryptTypes.cs`, `Native/ShatterNative.Crypt.cs`, `Native/SaveGame.Crypt.cs`: `BeginAreaVisit`, `IsWorldObjectOpen`, `SetWorldObjectOpen`, `WorldState`, `MapInfoOf`, `RollEncounter`, `OpenChest`, `EncounterClearLoot`, `AwardKillXp`, `CharacterProgress`; em `NativeRulesCore`: `Fervor()` e `GetActionTimingWithWeapon`. O herói deve usar `CharacterProgress(...).Level` (hoje a cena fixa 5). Grave o save depois de abrir baú, abrir segredo ou atalho e depois de uma melhoria (o chão não é salvo).

### 14.4 Testes

`test_world.cpp` (13 testes: estado do mundo e limites, save antigo sem o campo, semente da visita, formação determinística e distribuição de elite em 20 mil sementes, tabela de baú e fallback, erros de `chests.csv`, XP de cada tipo, Fervor, teto de nível, N0 com o conteúdo real: Martelo mais lento que a Espada e DPS na faixa do docs/19) e `c_api_17_*` (5 testes na fronteira da DLL).

### 14.5 Movimento do herói (rampa)

Chaves `hero_move_accel_seconds` (0,10) e `hero_move_decel_seconds` (0,08) em `rules.csv` [HIPÓTESE], faixa 0 a 0,5 s, obrigatórias. API: `shatter_db_hero_move_rules` e `shatter_layout_check_ext8` (3 valores). C#: `CombatRules.HeroMoveAccelSeconds` e `HeroMoveDecelSeconds` (o C# aplica a rampa linear: velocidade += máxima x dt / tempo; 0 = instantâneo). Teste: `c_api_17_hero_move_rules_...`.

## 15. API C: história da Região 1 (Backend, 19/10/2026, `claude/regiao1-capi`)
Aditiva; `SHATTER_C_API_VERSION` continua 1. Regras em `ShatterCore/include/shatter/story.h`; tabelas em `Content/Data/Story/` (docs/design/21 e 22).
- Handle novo `shatter_story` (imutável): `shatter_story_load_directory(path, db_ou_NULL, &story, err)` e `shatter_story_destroy`. Pasta faltando: `SHATTER_IO_ERROR`; tabela inválida: `SHATTER_CONTENT_INVALID`.
- `shatter_story_record_echo` (`is_new`), `shatter_story_skill_revealed`, `shatter_story_apply_verdict` (`result` = `SHATTER_VERDICT_OK|UNKNOWN|GENERAL_NOT_DEFEATED|ALREADY_DECIDED`; só OK muda o save).
- Leitura em JSON: `shatter_story_state_json` (Fome, bônus total, Ecos e vereditos tomados) e `shatter_story_region_json` (as duas opções da tela de veredito).
- Save: campo opcional `story` no save v2 (só gravado se não vazio), sem migração. Vale para o save inteiro, não por herói.
- Veredito irreversível; Fome limitada a `hunger_max` de `story_rules.csv`. Sem struct nova (só JSON), então sem `layout_info`.

### 15.1 Mancha no combate manual e custo em Fome (19/10/2026, `claude/golpe-devorado-mancha`)
Aditiva; `SHATTER_C_API_VERSION` continua 1. Revisão Opus do contrato pendente antes do merge (ver PR).
- **Função nova** `shatter_encounter_roll_json_ex(db, id, len, visit_seed, elite_bonus_pct, out, cap, needed)`. `elite_bonus_pct` em 0..100 (fora disso `SHATTER_INVALID_ARGUMENT`) soma pontos à `chanceElite` de cada grupo, com teto de 100%. `shatter_encounter_roll_json` ficou como está e chama a nova com 0; com 0 o sorteio é idêntico (cada espaço continua consumindo 1 número do fluxo Events).
- Core: `RollEncounter(..., int eliteBonusPct = 0)` em `world.h`.
- `shatter_story_state_json` ganhou só chaves: `stain_loot_table_by_map` ({mapId: tabela}) e `devoured_hunger_cost`.
- `story_rules.csv`: `devoured_hunger_cost` (0..`hunger_max`; cada uso de habilidade devorada gasta isso de Fome na corrida) e `stain_loot_table` (tabela de `loot_tables.csv` extra das áreas com Mancha, conferida contra o conteúdo). Novos em `story.h`: `DevouredHungerCost()`, `StainLootTable()`, `StainLootTableForMap`.
- Dados: `loot.crypt.stain` (rolls 1, dropChance 0,25, só mágico e raro; Lascas, Ouro e o conjunto do Guardião e o escudo `item_base.guard_shield`).
- Sem struct nova, então sem `layout_info`. Testes: `world_encounter_elite_bonus_*`, `story_devoured_cost_and_stain_loot_table`, trecho novo em `c_api_17`.

### 15.2 Missões da história (19/10/2026, `claude/missoes-regiao1`)
Aditiva; `SHATTER_C_API_VERSION` continua 1. Revisão Opus feita em 19/10/2026: sem bloqueio. Corrigidos: `requires` em ciclo agora é erro no `StoryDB::Finalize` e no `validate_story.py`, e o `validate_story.py` roda no CI. Notas abertas fechadas no 15.3 (A6); restam: um evento só avança em uma passada (efeito depende da ordem do CSV); `reach_map_boss` poderia ser derivado do `bossProgress` no core.
- **Save**: `story.quests` (opcional, só gravado se houver): `[{quest_id, progress, done}]`, no máximo 256, sem id repetido. Saves sem missões mantêm os mesmos bytes e hash. `save_v2.schema.json` atualizado.
- **Função nova** `shatter_story_quest_event(story, save, type, type_len, target, target_len, *completed)`: `type` `talk` ou `reach_map_boss`; soma 1 às missões liberadas e não concluídas com esse objetivo e alvo; `*completed` = quantas concluiu agora. Tipo ou alvo sem missão: 0.
- `shatter_story_record_echo` e `shatter_story_apply_verdict` sincronizam as missões `collect_echo` e `verdict`. `shatter_story_state_json` ganhou só a chave `quests` (lista na ordem de `quests.csv` com `progress`, `status` locked|active|done e `reward`).
- Core: `GetQuestStatus`, `QuestProgress`, `ReportQuestEvent` em `story.h`. Sem struct nova, então sem `layout_info`.

### 15.3 Fechamento das notas abertas do core e dos dados (19/10/2026, `claude/a6-notas-core-dados`)
Sem mudança de assinatura nem de layout; `SHATTER_C_API_VERSION` continua 1. Mudanças de comportamento:
- **Missões acima do limite**: `StoryDB::Finalize` recusa `quests.csv` com mais de `kMaxSavedQuests` (256) missões. Assim `GetOrAddQuestRecord` nunca encontra o save cheio e o evento deixa de ser ignorado sem aviso.
- **Save com tipo errado**: o leitor de `story.quests` agora exige `progress` inteiro e `done` booleano; texto, nulo ou campo ausente dá `BadData` (antes lia 0/false em silêncio).
- **Percentuais**: `TotalStatBonusPct` e `TotalPotionEffectPct` são limitados a 100, o mesmo teto que a expedição já aplicava (`storyStatBonusPct`, `storyPotionEffectPct`). Antes `shatter_story_state_json` informava, por exemplo, 130 enquanto o efeito real era 100. `RollEncounter` já limitava `eliteBonusPct` a 0..100 (sem mudança).
- **Esquema**: `save_v2.schema.json` descreve `world_state` (campo opcional já gravado pelo core desde a Etapa 3): `[{map_id, visits, opened}]`, no máximo 64 áreas e 512 objetos por área.
- Testes novos: buffer pequeno e ponteiros nulos em `quest_event`/`state_json`, tipos errados no save, teto de 100 e limite de 256 missões.
- Ainda aberto: um evento só avança em uma passada (efeito depende da ordem do CSV); `reach_map_boss` poderia ser derivado do `bossProgress`.

### 15.4 Travas de recompensa de missão (19/10/2026, `claude/a7-nuvem`)
- **Mecanismo no core, desligado nos dados**: `story_rules.csv` aceita linhas repetíveis `gate_reward,<chave de recompensa>`. Recompensa travada só vale depois de uma missão com essa recompensa estar concluída. Sem linhas, nada muda (hoje nenhuma está ativa: Marco de Retorno e duelo seguem livres).
- Core: `StoryDB::GatedRewards/IsRewardGated`, `IsRewardUnlocked` (alguma missão com a chave está `Done`) e `IsRewardOpen` (não travada, ou liberada). `Finalize` e `validate_story.py` recusam `gate_reward` que nenhuma missão concede (a trava nunca abriria).
- API C: `shatter_story_state_json` ganhou `gated_rewards: [{reward, open}]` (campo novo, sem assinatura nova, vazio por padrão).
- **Para travar de verdade** falta decisão de design do Will (qual recompensa, `unlock.return_marker` e/ou `unlock.duel`) e a ligação no cliente: Marco de Retorno e entrada do duelo consultarem `gated_rewards`. Sem isso, adicionar a linha no CSV não muda o jogo.
- Testes: `story_gate_reward_locks_until_quest_done`.

### 15.5 Fome e loot da Mancha na expedição idle (19/10/2026, `claude/project-thread-ca6jzj`)
Aditiva; `SHATTER_C_API_VERSION` continua 1. Nenhuma função nova nem struct nova (só chaves de JSON), então sem `layout_info`. Nenhum número do balanceamento do Ato I (PR #29) mudou. Decisões tomadas sem o Will (ele dormia), registradas aqui e no docs/design/21.
- **Fome no idle**: o golpe devorado entra na barra da expedição pela mesma regra do manual (`DevouredKit.FillBar`): último espaço vazio entre o 3 e o 6, com posto 1; barra cheia, fica de fora. Cada uso gasta 1 dos usos da "corrida", que no idle é a expedição inteira (não há morte e renascimento; o recuo encerra). Usos = `(hunger_max - Fome) / devoured_hunger_cost`, arredondado para baixo: Fome 1, 2, 3 e 4 dão 3, 2, 1 e 0 usos; custo 0 = sem limite (-1). Com 0 usos o golpe nem entra e o resultado é idêntico ao de antes do veredito. Todo `skill.devoured.*` da barra gasta esses usos, inclusive um que já viesse na barra do snapshot (a trava do manual também é pelo id).
- **Quando a IA usa o golpe**: se alguma regra da IA cita o golpe, só as regras o usam (por exemplo `target_is_elite`). Se nenhuma cita, ele é usado assim que fica pronto, no lugar da próxima habilidade; regras de poção que vêm antes continuam valendo. O golpe nunca vira o ataque básico (posição 0).
- **Loot da Mancha no idle**: encontro limpo numa área com Mancha rola também a tabela `stain_loot_table` (`loot.crypt.stain`), depois da tabela de área, no mesmo fluxo Loot do encontro. Combate, XP e tempo não mudam; o teto de raros por expedição vale também para ela. Encontro em que o herói recua não rola (igual à tabela de área).
- **Pedido (`ExpeditionRequest`) e parâmetros de início**: campos opcionais `story_devoured_skills` (lista, até 8), `story_devoured_uses` (-1..1000) e `story_stain_loot_table` (texto). Só gravados quando não são padrão (a lista só com usos != 0), então pedidos antigos mantêm os mesmos bytes e o mesmo `resultHash`. Lista que não é lista, item que não é texto ou mais de 8 itens: `SHATTER_PARSE_ERROR` no início e `BadData` no save. Golpe ou tabela que não existe mais no conteúdo: a simulação para com `content_mismatch`; golpe sem perfil idle é ignorado.
- **Progresso e recibos (JSON da API)**: `devoured_uses_spent` no progresso (atravessa as partes da simulação) e `devoured_uses` no recibo do encontro, só quando > 0. O `resultHash` inclui `devoured_uses` só quando > 0.
- **`shatter_story_state_json`** ganhou `devoured_skills` (lista) e `idle_devoured_uses` (o número acima). O cliente copia os dois e a `stain_loot_table_by_map` do mapa nos parâmetros de início, como já fazia com `story_*_pct`.
- **Core**: `DevouredSkills`, `IdleDevouredUses` e `ApplyStoryToExpedition` (preenche todos os `story*` dos parâmetros de início para um mapa) em `story.h`; `WriteStoryIdleFields`/`ReadStoryIdleFields` em `save.h`; `EncounterReceipt::devouredUses` e `ExpeditionProgress::devouredUsesSpent` em `expedition.h`.
- **Dados**: `skill.devoured.guardian_slam` ganhou perfil idle (`idleSupported` true, mesmo perfil da Fenda de Pedra, outro cone de área: alvos 3, fração 0,6, aproximação 0,6, uptime 0,8, dano recebido 0,80, amostra 20, `manual_estimate`). `save_v2.schema.json` descreve os três campos novos do pedido.
- **Testes**: `test_story_idle.cpp` (usos por Fome 1 a 4 e custo 0; `ApplyStoryToExpedition` sem veredito, Exorcizar, Devorar, outro mapa e Fome cheia; loot da Mancha sem mudar combate; gasto de usos em partes de 1 e 4 encontros; regra citando o golpe; barra cheia; ida e volta do JSON e recusas) e `c_api_story_idle_fields_go_from_start_params_to_the_saved_request`, mais as chaves novas em `c_api_story_echoes_verdict_hunger_and_state_json`. A sonda `balance_story` ganhou a tabela "Devorar vigente com Fome e loot da Mancha".
- **Resultado da sonda** (12 h, Guerreiro nível 4, 30 sementes): o loot da Mancha sobe os itens de 48,7 para 60,6 por hora (kit completo) e os raros do herói só com espada de 3,37 para 3,83 por expedição (o teto de 4 segura o kit completo). A Fome quase não muda o idle: 1 a 3 golpes numa expedição de milhares de encontros. É o efeito fiel ao manual (usos por vida); se o design quiser a Fome mais visível no idle, a troca simples é contar os usos por encontro em vez de por expedição.

## 16. API C 1.8: roguelike 2D da Cripta no core (marco M10, pacote 1; 30/10/2026, `claude/project-thread-pyabz7`)
Aditiva: `SHATTER_C_API_VERSION` continua 1 e `SHATTER_C_API_MINOR` sobe de 7 para 8 (o cliente que quiser as funções `shatter_rogue_*` confere `shatter_api_minor() >= 8`). Sem struct nova (só escalares e JSON), então sem `layout_info`. O cliente Godot ainda não usa: a troca do GDScript pelas chamadas é o pacote seguinte.

### 16.1 O que entrou
- **Módulo novo** `include/shatter/rogue.h` + `src/rogue.cpp`: as regras de `godot/scripts2d/meta_2d.gd` (compra de melhorias, Forja de amuletos e consumíveis, equipar, preparar corrida, aplicar stats, drops, creditar ganhos, save), `upgrades_2d.gd` (níveis, disponíveis, sorteio, escolha, aplicação sobre a base) e `run_2d.gd` (etapas de `run.csv`, caminhos com `rota.csv`, fragmentos por sala limpa, elite e vitória, cartas por sala com a extra da elite e nenhuma no descanso nem na última sala, cura do descanso, morte, fim da corrida). Combate, movimento, física, spawns e o relógio da corrida ficam no Godot.
- **Dados**: o core lê `godot/data2d/{meta,receitas,drops,rota,run,run_settings,upgrades}.csv` sem mudar o formato das linhas (`csv.h` e `std::from_chars`). São a única fonte de números. `RogueData::Finalize` confere: habilidade de `meta.csv` aponta para um upgrade; etapa de `rota.csv` existe; sala de combate tem inimigos; chaves obrigatórias de `run_settings.csv` (`seed`, `upgrade_cards`, `elite_extra_cards`, `room_clear_fragments`, `elite_fragments`, `victory_fragments` inteiras e não negativas; `rest_heal` entre 0 e 1).
- **RNG**: `RngStream::Rogue = 5` em `rng.h`. Cada sorteio de cartas usa `Pcg32::ForStream(seed, Rogue, nº do sorteio)` e o mesmo Fisher-Yates de `sortear()`. **Não reproduz o `RandomNumberGenerator` do Godot**: a paridade é nas regras (quais cartas podem sair, quantas, sem repetir), não na sequência. Mesmo seed + dados + ações = mesmo estado e mesmo hash (SHA-256 do estado canônico).
- **Save do meta**: o mesmo JSON do `meta_2d.gd` (`{"versao":1,"fragmentos","materiais","niveis","amuletos","equipado","estoque"}`), então o `user://save_2d.json` que o GDScript já gravou continua valendo. Escrita em `caminho.tmp`, conferida relendo, e troca pelo principal (`IFileIO` do `save.h`; o save do ARPG não mudou). Leitura tolerante igual ao `carregar()`: arquivo ausente, JSON inválido ou `versao` != 1 zera o meta; ids desconhecidos descartados; níveis e estoque limitados ao máximo; negativos viram 0; `equipado` só se o amuleto foi criado; números aceitos como inteiro ou float (o JSON do Godot lê tudo como float).

### 16.2 API C (`shatter_c.h`, handle `shatter_rogue`, uma thread)
- Contexto: `shatter_rogue_load_directory(path, &rogue, err)` (pasta ou CSV faltando: `IO_ERROR`; tabela inválida: `CONTENT_INVALID`), `shatter_rogue_destroy`, `shatter_rogue_setting(key, *double)` (valores de cliente como `clear_delay`, `room_fade`, `seed`).
- Save: `shatter_rogue_save_path_set`, `shatter_rogue_meta_load(*result)` (`SHATTER_ROGUE_LOAD_OK|MISSING|BAD_JSON|BAD_VERSION`), `shatter_rogue_meta_save(err)`, `shatter_rogue_meta_save_json`, `shatter_rogue_meta_load_json`. Com caminho ligado, cada ação do meta que dá certo grava sozinha (como o `salvar()` do GDScript): comprar, criar, equipar, preparar corrida, creditar, iniciar corrida que creditou ganhos pendentes e terminar corrida com ganhos. Se só a gravação falhar, a função devolve `SHATTER_IO_ERROR` e a mudança fica na memória.
- Meta: `shatter_rogue_meta_buy` / `_can_buy`, `_craft` / `_can_craft`, `_equip` (troca ou desequipa), `_prepare_run`, `_credit({"fragmentos","materiais"})`, consultas `_fragments`, `_material`, `_level`, `_stock`, `_owns`, `shatter_rogue_skill_unlocked`, `shatter_rogue_meta_json` (tudo da tela de meta e da Forja, com `can_buy`/`can_craft` = código de resultado) e `shatter_rogue_drop_json`. `*result` = `SHATTER_ROGUE_META_OK|UNKNOWN|MAXED|NO_FRAGMENTS|NO_MATERIALS|ALREADY_OWNED|STOCK_FULL|NOT_OWNED`; só OK muda o estado.
- Stats: `shatter_rogue_stats_apply(base_json, include_run, ...)` recebe e devolve um objeto `stat -> número` (ordem da entrada). Aplica amuleto equipado, consumíveis ativos, melhorias de stat e, com `include_run`, os upgrades da corrida.
- Corrida: `shatter_rogue_run_start(seed, base_json)`, `_phase` (`SHATTER_ROGUE_PHASE_NONE|FIGHT|CLEARED|CHOICE|ROUTE|WON|DEAD`), `_paths_json(stage)`, `_enemy_killed(id, *room_cleared, *result)`, `_choose_card(id, hp, *hp_out)`, `_rest(hp, *hp_out)`, `_door` (`SHATTER_ROGUE_DOOR_NOT_READY|ENTERED|ROUTE|VICTORY`), `_choose_path(index)`, `_player_died`, `_finish`, e leituras `_run_json` (fase, sala, vivos, cartas oferecidas, níveis, opções de rota, ganhos), `_run_stats_json`, `_run_summary_json`. `*result` = `SHATTER_ROGUE_RUN_OK|WRONG_PHASE|NOT_OFFERED|UNKNOWN|NO_HP_STAT`.
- Estado: `shatter_rogue_state_json`, `shatter_rogue_state_restore` (inválido: `PARSE_ERROR` e nada muda) e `shatter_rogue_state_hash` (64 hex). Retomar o estado continua do mesmo ponto: simular em partes dá o mesmo hash que de uma vez.
- Strings do jogador nunca saem do core: só ids (`stage`, `kind`, ids de upgrade, receita e material). O resumo não traz o tempo da corrida: o relógio é do cliente.

### 16.3 Decisões (diferenças conscientes do GDScript)
- **Quem conta os vivos é o core**: o cliente avisa cada morte (`_enemy_killed`) e o core limpa a sala quando o total de `enemies` da sala chega a 0. As cartas são sorteadas no mesmo instante (o GDScript esperava o `clear_delay`; nada muda os níveis nesse intervalo, então é equivalente). O atraso visual continua no cliente.
- **Ordem dos consumíveis ativos**: a de `receitas.csv` (o GDScript usava a ordem do dicionário, que dependia do histórico). Com os dados de hoje não muda número nenhum (cada consumível mexe num stat diferente).
- **Stat ausente na base é ignorado** (o GDScript dava erro de chave). **Carta precisa estar entre as oferecidas** (o GDScript aceitava qualquer id). **Morrer depois da vitória** é ignorado (`WRONG_PHASE`).
- **Save**: material que não existe nos dados é descartado na leitura (o GDScript guardava qualquer chave); entradas com 0 não são gravadas. O formato e a versão continuam os do GDScript.
- **Cura do descanso**: uma vez por sala de descanso, chamada pelo cliente ao entrar (o GDScript curava sozinho ao carregar a sala). `hp_max` vem dos stats da corrida guardados no core.

### 16.4 Testes e build
- `tests/test_rogue.cpp` (16 testes, números reais dos CSV): tabelas e erros de tabela; `meta_dano` +10% por nível até o máximo 3 e `meta_vida` +15; Amuleto de Osso custa osso 3 + pedra 1 + 30 fragmentos, se equipa sozinho e dá +5%; estoque máximo 3 e preparar corrida; drops e +5 por sala; habilidades bloqueadas nunca oferecidas em 200 seeds até a compra; elite +15 e 4 cartas; descanso cura 50% sem cartas e limitado ao máximo; última sala sem cartas e vitória +25 com resumo; `vitality` sobe a vida atual; morte e abandono creditam; save ida e volta e arquivo atômico; save corrompido, versão errada e leitura tolerante; determinismo (mesma seed duas vezes, 150 + 250 passos com restauração = 400 de uma vez, seed diferente muda o hash); restauração inválida não muda nada.
- `tests/test_c_api_rogue.cpp` (5 testes, no executável da DLL): todos os argumentos nulos e UTF-8 inválido, `BUFFER_TOO_SMALL` sem efeito, meta e stats, corrida inteira pela API (rota, elite, descanso, chefe, vitória, resumo), gravação automática, save corrompido e gravação que falha, mesmo hash com a mesma seed e restauração. O CMake junta `tests/test_c_api*.cpp` nesse executável e passa `SHATTER_ROGUE_DATA_DIR` (godot/data2d) aos dois executáveis de teste.
- GCC e Clang com `-Werror`, e ASan/UBSan nos testes do rogue: sem avisos nem erros.

### 16.5 API C 1.9: modo "cartas externas" (31/10/2026)
Aditiva: `SHATTER_C_API_MINOR` sobe de 8 para 9 (o cliente confere `shatter_api_minor() >= 9`). Sem struct nova. Motivo: o cliente 2D tem duas classes. O Arqueiro usa as cartas de `upgrades.csv` sorteadas pelo core; o Guerreiro tem árvore de habilidades própria (pai, slots de ativas, recargas), que por enquanto fica no GDScript. O fluxo da corrida (etapas, rotas, drops, ganhos, descanso, vitória, derrota) é o do core para as duas.
- **API**: `shatter_rogue_run_external_cards_set(rogue, uint8_t on, int32_t* result)` e `shatter_rogue_run_external_cards_get(rogue, uint8_t* out)`. No C++: `RogueState::SetExternalCards(bool)` e `ExternalCards()`. `on` = 0 desliga, qualquer outro valor liga.
- **Semântica**: com o modo ligado, a morte que limpa a sala vai direto à fase `CLEARED` (porta aberta, como já acontece na última sala e no descanso). Não sorteia: o nº de sorteios do Pcg32 (`draws`) não muda e `offer` fica vazia. `shatter_rogue_run_choose_card` devolve `WRONG_PHASE` (nunca há fase `CHOICE`). Os stats da corrida ficam base + meta (nenhum upgrade escolhido; `upgrades_total` = 0 no resumo). Os fragmentos de sala limpa, elite e vitória, os drops, as rotas, o descanso e a morte são os mesmos: mesma seed e mesmas ações dão os mesmos ganhos com e sem o modo.
- **Quando vale**: o modo é configuração do `shatter_rogue`, não da corrida. Fica ligado até ser desligado: `run_start`, `run_finish` e o save do meta não o mexem. Só muda fora de corrida viva (fase `NONE`, `WON` ou `DEAD`); em `FIGHT`, `CLEARED`, `CHOICE` ou `ROUTE`, `*result` = `WRONG_PHASE` e nada muda. O cliente liga o modo ao escolher a classe, antes de `shatter_rogue_run_start`.
- **Estado e determinismo**: entra no `state_json` como `"external_cards": true` no nível de cima, só quando ligado. Desligado, o JSON é byte a byte o da 1.8 (os hashes antigos continuam valendo). `state_restore` lê a chave (ausente = desligado; valor que não é booleano, ou modo ligado com fase `choice` ou oferta não vazia: `PARSE_ERROR` e nada muda). Com o modo no estado, o hash difere do mesmo estado sem ele. Não vai para o save do meta (`save_2d.json`). `shatter_rogue_run_json` ganhou `"external_cards": bool`.
- **Testes**: `test_rogue.cpp` +3 (sala limpa e elite vão a `Cleared` sem oferta nem sorteio, carta dá `WrongPhase`, descanso e vitória iguais, stats = base + meta, troca recusada na corrida viva e liberada depois; mesma seed com e sem o modo dá os mesmos ganhos e o mesmo save do meta, hash diferente, sem chave nova no JSON desligado; 400 passos sem sorteio, 150 + 250 com restauração = 400 de uma vez, restauração inválida não muda nada). `test_c_api_rogue.cpp` +1 (argumentos nulos, set/get, `WRONG_PHASE` na corrida viva, `CLEARED` sem oferta, `choose_card` = `WRONG_PHASE`, `draws` 0, `run_stats_json` = `stats_apply` sem corrida, estado ida e volta com o mesmo hash). `test_c_api.cpp` confere o minor 9. GCC e Clang com `-Werror`: 4/4 no ctest.
- **Falta (fora do core)**: o nó da GDExtension (`godot/gdextension/src/shatter_rogue_node.*`) expor as duas funções, e o cliente do Guerreiro ligar o modo.
