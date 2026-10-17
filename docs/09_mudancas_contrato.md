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


---

## 7. Etapa 2: regras novas do protótipo e API C 1.1 (Backend Engineer, 16/10/2026, branch `etapa2/backend`)

Origem: itens 1 a 11 de "Para o Tech Lead" em `13_design_pendencias.md`, achados A-01, A-05, A-06 e M-03 de `11_revisao_codigo.md` (master) e a decisão do dono sobre a calça (`legs`, C-10 da seção 6). Números só nos CSV; o core lê as tabelas e colunas com os nomes exatos de `13`, "Para o Data Engineer", e do `06_dados.md` seção 5a (branch `etapa2/dados`).

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

Origem: `13_design_pendencias.md`, "Balanceamento e dados — rodada 2". Core, CSV, esquemas, validador e `06_dados.md` no mesmo branch.

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

Dados: `rules.csv` (+2 chaves, 62), `skills.csv` (`wallStaggerSeconds`; `idleDamageTakenMult` 0,85 nas 4 habilidades do Guerreiro), `enemies.csv` (`patrolSpeedMult`), `enemy_ai.csv` (`requireOnScreen`), `boss_phases.csv` (`summonAtFraction`), os 5 esquemas, `validate_data.py` (`E_BOSS` para `summonAtFraction`; 3 mutações novas no `--self-test`) e `06_dados.md`. Fixtures de `tests/data` alinhadas; golden regravado.

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

Conteúdo (CSV): as **62 chaves** de `rules.csv` agora são obrigatórias quando o conteúdo vem de CSV (chave faltando = erro de validação `E_REQUIRED`); `constants.h` guarda só 0 neutro, nenhum número de balanceamento escondido. `potions.csv`, `elite_modifiers.csv`, `boss_phases.csv`, `boss_patterns.csv` e `enemy_ai.csv` são obrigatórias (arquivo ausente em `LoadDirectory` = E_IO; carregar regras sem uma delas = `E_REQUIRED` no `Finalize`). Entrada de loot fixa só vale na tabela de topo de um chefe (fora disso `E_RULE`); `tools/validate_data.py` aceita peso vazio em entrada fixa por `fixedChance`, `guaranteeFirstKill` ou `pityKills`, e rejeita entrada fixa fora da tabela de topo (`E_FIXED_TABLE`).

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

Origem: `docs/18_combate_combo.md` (seção 8 e as decisões do orquestrador em 8.1). `SHATTER_C_API_MINOR` vai para **5** (só adições; o C# deve exigir `shatter_api_minor() >= 5`). **A máquina de combate básica fica no C#** (`HeroCombatLogic`, passo fixo de 60 Hz): índice do combo, buffer, janelas, limiar de segurar, carga com multiplicador linear, cancelamentos e a geometria do arco da defesa. O core guarda e valida os NÚMEROS (`basic_kits.csv` e 7 chaves de `rules.csv`) e continua resolvendo dano, efeitos, defesa e recurso. O item 4 do docs/18 seção 8 (máquina no core) não vale.

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
| `shatter_combat_rules` + `shatter_db_combat_rules(db, out)` | 7 doubles: `combo_window`, `combo_window_after_dodge`, `attack_buffer`, `heavy_hold_threshold`, `light_windup_credit_max`, `guard_lower_time`, `dash_shot_range` |
| `shatter_basic_kit` + `shatter_basic_kit_get(db, class_id, len, out)` | Kit da classe (720 bytes). 9 doubles (`heavy_charge_time`, `heavy_max_mult`, `guard_arc`, `guard_max_hold`, `guard_cooldown`, `guard_perfect_window`, `guard_perfect_cooldown`, `guard_perfect_resource`, `guard_drain_per_damage`), `int32 light_chain_count` (1 a 3), `int32 guard_perfect_effect_count` (0 a 4), `char light_chain[3][64]`, `heavy_skill[64]`, `charge_effect[64]`, `guard_effect[64]`, `guard_perfect_effects[4][64]` (UTF-8, NUL). NOT_FOUND: classe inexistente ou sem linha |
| `shatter_vitals_tick_ex(db, vitals, stats, class_id, len, dt, in_combat, moving)` | Como `shatter_vitals_tick`, com o herói andando ou parado |
| `shatter_vitals_gain_on_hit` / `shatter_vitals_gain_on_block` `(db, vitals, stats, class_id, len)` | Recurso por golpe e por bloqueio da classe, limitado ao máximo; class_id vazio/nulo = nada; classe desconhecida = INVALID_ARGUMENT |
| `shatter_layout_info_ext5` / `shatter_layout_check_ext5` (`SHATTER_LAYOUT_EXT5_COUNT` = 26) | `[offset de from_guard_arc, sizeof(shatter_combat_rules), 7 offsets, sizeof(shatter_basic_kit), 9 offsets dos doubles, light_chain_count, guard_perfect_effect_count, light_chain, heavy_skill, charge_effect, guard_effect, guard_perfect_effects]`. Chamar o check na inicialização |

### 12.4 Para o Frontend / Integração

C# (`Interop`): `CombatRules` ganhou `ComboWindowSeconds`, `ComboWindowAfterDodgeSeconds`, `AttackBufferSeconds`, `HeavyHoldThresholdSeconds`, `LightWindupCreditMax`, `GuardLowerTimeSeconds`, `DashShotRangeUu`; `HitRequest.FromGuardArc`; `SkillTags.Guard`; `SkillInfo.Pierce`, `SkillInfo.Behavior` (`SkillBehavior`); `BasicKitInfo` (`IRulesCore.FindBasicKit(classId)`); `IRulesCore.TickVitals(..., moving)`, `GainResourceOnHit`, `GainResourceOnBlock` (membros com implementação padrão; o stub não os precisa). Não foi possível compilar na Unity neste worktree.

### 12.5 Testes e pendências

Testes novos em `test_combat_basic.cpp` (18) e `test_c_api.cpp` (3, `c_api_15_*`), `validate_data.py` com 8 mutações novas. Pendências: (1) defesa perfeita, limite de tempo, dreno de recurso e empurrão por tipo de alvo (docs/18 §8 itens 5 e 11) ficam no C# com os valores do kit; (2) o stub em C# ignora `moving`, kit, `pierce` e comportamento (só o núcleo nativo preenche); (3) Arqueiro e Mago sem expedição por decisão do dono (Q18-2).
