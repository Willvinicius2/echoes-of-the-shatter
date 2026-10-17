# 17. Revisão do core — Etapa 2 (ShatterCore)

Data: 17/10/2026. Base: `master` @ `b39caf3` (o `ShatterCore/` é idêntico ao de `5d02199` e ao de `b4107cb`, o `master` na hora de abrir o PR). Escopo: `git diff e1df5c4..master -- ShatterCore`, 99 arquivos, +7.230/−277 linhas (código de produção +3.901/−127, testes +3.329/−150). Outra sessão está mexendo no ShatterCore ao mesmo tempo: esta revisão **não altera código de produção**; só acrescenta testes em arquivos novos (`ShatterCore/tests/test_revisao_*.cpp`).

## 0. Escopo, método e limites

- **Lido:** `combat.h/.cpp`, `content.h/.cpp`, `constants.h`, `effects.h/.cpp`, `expedition.h/.cpp`, `loot.h/.cpp`, `progress.h`, `save.h/.cpp`, `save_migrations.cpp`, `shatter_c.h`, `src/c_api/shatter_c.cpp` e os testes novos (`test_potions_dodge`, `test_status_boss`, `test_elite_unique`, `test_round2`, `test_balance_probe`, `c_api_11_*`, `c_api_r2_*`). Referências: `CLAUDE.md`, `docs/04_arquitetura.md` §9, `docs/09_mudancas_contrato.md` §6 a §8, `docs/11_revisao_codigo.md`, `docs/13_design_pendencias.md`.
- **Executado:** o CI do core em Linux (seção 1) e os 16 testes de reprodução da seção 6, em Release e em Debug com ASan/UBSan. Cada achado diz se foi **confirmado por teste** ou visto **só pela leitura**.
- **Não executado:** build no Windows (MSVC, `tools\build_core.cmd`), testes do Unity (EditMode/PlayMode) e o build com `-ffast-math` (proibido; não foi testado). Nada aqui foi medido em outra CPU.

### Contagem

| Prioridade | Achados |
|---|---|
| Crítico | 1 |
| Alto | 2 |
| Médio | 8 |
| Baixo | 9 |

### Resumo

1. **O CI do core está vermelho no `master` desde o merge da Etapa 2** (C1): um aviso que o MSVC não dá (`-Wmissing-field-initializers`) para o build nos 4 jobs. Nenhum teste do core rodou no GitHub Actions desde `d9b8eb3`. A correção é uma linha.
2. Corrigido o C1, **os 2 jobs `sanitize` continuam vermelhos** por um vazamento no próprio `test_c_api.cpp` (A1).
3. **O início "confiável" de expedição aceita relógio atrasado** (A2): com o relógio do PC 7 dias para trás, a expedição de 4 h fica pronta 1 minuto depois. É a parte de M-03 do docs/11 que ficou aberta.
4. O save v2 aceita `boss_progress` e expedições com valores fora de faixa (M1, M2): nenhum derruba o core em Release, mas há comportamento indefinido (UB) que o UBSan acusa, garantia do Único quebrada e expedição presa para sempre.
5. As 21 chaves novas de `rules.csv` e as 5 tabelas novas continuam **opcionais**, com os números de balanceamento escritos em `constants.h` (M3, M4). Viola o `CLAUDE.md`.
6. Determinismo: **sem achado**. Nenhum `unordered_map` iterado, nenhum RNG da STL, nenhum `pow/exp/log/sin` no golpe nem no simulador, `std::stable_sort` com desempate pelo índice, `double` normalizado antes do hash (−0 → 0), NaN recusado no JSON, `DetCos/DetSin` só com ângulos em [0, π].

---

## 1. Resultados do CI local (item 1)

Máquina: contêiner Linux x86-64, 4 núcleos, 15 GB; Ubuntu 24.04, GCC 13.3.0, Clang 18.1.3, CMake 3.28.3, Python 3.13.16. Mesmos comandos de `.github/workflows/core.yml` (configurar, `cmake --build -j 4`, `ctest -j 4` com `ASAN_OPTIONS=detect_leaks=1:abort_on_error=1` e `UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1`), sem ccache, uma configuração por vez. Tempos de parede em segundos.

### 1.1 Como está no `master` (`SHATTER_WERROR=ON`)

| Configuração | Configurar | Compilar | Testes |
|---|---|---|---|
| GCC Release | 0,9 s, ok | **falha** em 9,8 s (`content.cpp:381`) | não rodam |
| GCC Debug + ASan/UBSan | 0,5 s, ok | **falha** em 9,1 s | não rodam |
| Clang Release | 1,7 s, ok | **falha** em 2,8 s (`content.cpp:316, 317, 320, 321, 340, 343, 351, 356, 357`) | não rodam |
| Clang Debug + ASan/UBSan | 0,7 s, ok | **falha** em 3,9 s | não rodam |
| `python3 tools/validate_data.py` | — | — | **OK** em 0,1 s (0 erros, 0 avisos; 18 tabelas, 249 chaves de Loc) |
| `python3 tools/validate_data.py --self-test` | — | — | **OK** em 0,2 s (todas as mutações falham como esperado) |

O GitHub Actions confirma: os runs #7 (`d9b8eb3`, merge de `etapa2/backend`), #9, #10 e #11 do workflow `core` falharam nos 4 jobs `core-linux` com o mesmo erro; o último verde foi o #6 (`3ad87b9`). O job `data` passa.

### 1.2 Com o aviso do C1 rebaixado (`-DCMAKE_CXX_FLAGS=-Wno-error=missing-field-initializers`, resto igual)

Para saber o que vem depois do C1, sem mexer no código. Inclui os 16 testes novos da seção 6 (desligados por padrão; não mudam o resultado).

| Configuração | Compilar | `shattercore_tests` | `shattercore_c_api_tests` | `save_rf51_python_validator` | `shattercore_dll_exports` | ctest |
|---|---|---|---|---|---|---|
| GCC Release | ok, 35,7 s | 171/171 ok, 6,5 s | 23/23 ok, 1,6 s | ok | ok | **4/4 ok** em 6,5 s |
| GCC Debug + ASan/UBSan | ok, 36,5 s | 171/171 ok, 228,6 s | **aborta** em 99,8 s (LeakSanitizer, A1) | ok | ok | **3/4**, 228,6 s |
| Clang Release | ok, 32,4 s | 171/171 ok, 7,6 s | 23/23 ok, 1,7 s | ok | ok | **4/4 ok** em 7,6 s |
| Clang Debug + ASan/UBSan | ok, 21,7 s | 171/171 ok, 194,0 s | **aborta** em 84,4 s (LeakSanitizer, A1) | ok | ok | **3/4**, 194,0 s |
| GCC Release + ASan/UBSan (fora da matriz do CI) | **falha** em 101,8 s (B9) | — | — | — | — | — |
| Clang Release + ASan/UBSan (fora da matriz do CI) | ok, 62,3 s | 171/171 ok, 43,8 s | **aborta** em 11,4 s (A1) | ok | ok | **3/4**, 43,8 s |

Observações:
- Os testes do core: **171 de 171** (155 do `master` + 16 novos) e **23 de 23** da API C em Release, nos dois compiladores. Sem os testes novos (só o `master`, passada anterior): 155 de 155 e 23 de 23 em Release, e no GCC Debug + ASan o mesmo aborto do A1.
- Tempos de `ctest -j 4` (os testes correm em paralelo). Sob ASan o `shattercore_tests` leva de 3 a 4 min; os mais lentos são antigos: `expedition_rf40_forecast_band_contains_real_results` (83,8 s no GCC Debug + ASan), `expedition_rf34_many_twelve_hour_*` (28,0 s) e `expedition_rf34_no_top_tier_*` (22,9 s). Cabe no `timeout-minutes: 20` do workflow, mas é o primeiro lugar a olhar se o job passar disso.
- Nos jobs com sanitizer, `shattercore_c_api_tests` aborta pelo LeakSanitizer: é o A1 (vazamento no teste, não no core).
- Clang com sanitizer: o pacote `libclang-rt-18-dev` não vinha instalado no contêiner (link falhava por falta de `libclang_rt.asan*.a`); instalei e rodei de novo. É coisa do ambiente, não do código: no GitHub o job `core-linux (clang, sanitize)` passou no run #6, antes da Etapa 2 (a etapa de testes levou ~2 min lá).
- GCC **Release** com sanitizer (fora da matriz do CI) não compila: `-Wmaybe-uninitialized` dentro de `<regex>`/`std::function` da libstdc++ em `tests/test_save_schema.cpp` e `tests/test_text_and_code.cpp` (o aviso aponta para o interior da libstdc++, não para código do projeto; parece falso positivo do GCC 13 com `-O2` + ASan). Ver B9.

---

## 2. Crítico

### C1. O CI do core não compila no Linux desde o merge da Etapa 2

- **Onde:** `ShatterCore/src/content.cpp:307-312` (`struct TableDef`: `optionalColumns` sem inicializador padrão) e `:314-381` (as 9 tabelas sem coluna opcional, como `{"rules.csv", {"key", "value"}}`, omitem o 3º campo).
- **Cenário que falha:** `-Wextra` liga `-Wmissing-field-initializers` no GCC 13 e no Clang 18; com `SHATTER_WERROR=ON` (o CI) o build para em `content.cpp` nos 4 jobs. O MSVC (`/W4`) não tem esse aviso, por isso `tools\build_core.cmd Release --werror` passa no Windows e o problema passou despercebido. Desde então nenhuma regra da Etapa 2 (poções, esquiva, stun, chefe, elite, Único, fichas) foi testada no CI, e os achados A1 e B9 ficaram escondidos atrás deste.
- **Correção:** em `content.cpp:310`, `std::vector<const char*> optionalColumns{};`. Conferido com um arquivo mínimo: GCC 13.3 e Clang 18.1 com `-Wall -Wextra -Wpedantic -Werror` compilam com `{}` e falham sem ele. Para o processo: o merge entrou direto no `master`; vale abrir PR (o workflow já roda em `pull_request`) e olhar o resultado antes de juntar.

---

## 3. Alto

### A1. `test_c_api.cpp` vaza um handle e derruba os jobs `sanitize`

- **Onde:** `ShatterCore/tests/test_c_api.cpp:1042` (cria `again`) e `:1059` (`shatter_potions_from_save(db.db, save.save, 9, &again.p)`). A API zera `*out` antes de validar o índice (`src/c_api/shatter_c.cpp:2401`), então o cinto criado em 1042 perde o dono.
- **Cenário que falha:** com o C1 corrigido, `shattercore_c_api_tests` aborta nos jobs gcc/clang `sanitize` com `ERROR: LeakSanitizer: detected memory leaks … Direct leak of 32 byte(s) … shatter_potions_from_save shatter_c.cpp:2405 … test_c_api.cpp:1042` (128 bytes em 2 alocações). Reproduzido aqui (seção 1.2).
- **Correção:** no teste, usar uma variável nova na chamada que deve falhar (`shatter_potions* tmp = nullptr;`). A API está certa: zerar `*out` antes de falhar é o contrato (docs/11, seção 5). Como é arquivo de teste existente, fica para quem mexe no core.

### A2. `shatter_save_start_expedition_trusted` aceita o "agora" do chamador e ignora o relógio voltando

- **Onde:** `src/c_api/shatter_c.cpp:2873-2875` (`p.startUtc = now->now;`, sem olhar `now->rollback_detected` nem `save.lastSeenUtc`). A coleta, ao contrário, resolve o relógio por dentro com o `last_seen` do save (`:2898-2906`).
- **Cenário que falha (confirmado):** sem hora da Steam, o jogador atrasa o relógio do PC em 7 dias. `shatter_clock_resolve_now` devolve `rollback_detected = 1`, mas o início aceita e grava `start_utc` 7 dias no passado. O jogador corrige o relógio; 60 s depois a coleta confiável acha a expedição de 4 h terminada e entrega tudo (teste `revisao_A2_*`: devolve `BUFFER_TOO_SMALL` com `needed = 22544`, ou seja, resultado pronto, em vez de `NOT_FINISHED`). Contorna o RF-48. O C# do `master` atual passa exatamente a saída de `shatter_clock_resolve_now` (`EchoesOfTheShatter/Assets/Scripts/Core/ExpeditionService.cs:205-206`), então o cenário vale no jogo. Além disso, `shatter_trusted_now` é uma struct preenchida pelo chamador e o `now` entra em `DeriveExpeditionSeed` (`:2875`): o C# ainda escolhe a seed indiretamente (a segunda metade de M-03 do docs/11).
- **Correção:** receber `const shatter_clock_input*` (como a coleta) e resolver por dentro com `save.lastSeenUtc`; com relógio voltando (`now < last_seen − tolerância`), recusar o início com um `StartCheck` novo ou usar `max(now, last_seen)`; gravar `last_seen_utc` no mesmo passo. Subir `SHATTER_C_API_MINOR` e registrar no docs/09.

---

## 4. Médio

### M1. `boss_progress` do save entra sem validação: duplicado, negativo ou no limite do `int`

- **Onde:** `src/save.cpp:253-259` (lê `kills` e `kills_since_unique` com `AsInt` e `static_cast<int>`, sem faixa e sem deduplicar). A API lê a **última** entrada do chefe (`src/c_api/shatter_c.cpp:2790-2795` e `:2818-2820`) e grava na **primeira** (`FindOrAddBossProgress`, `include/shatter/progress.h:27-35`, usada em `shatter_c.cpp:2828`). `src/loot.cpp:124`, `:131` e `:133` somam em `int`.
- **Cenários que falham (confirmados):**
  1. `[{guardian,0,0},{guardian,10,3}]`: cada vitória lê 10/3 e grava 11/4 na primeira entrada; o valor lido nunca muda, `kills` fica em 10 para sempre e a garantia de 5 vitórias nunca dispara (`revisao_M1_boss_progress_duplicado_congela_o_contador`: `10 != 16`). Com `[{guardian,5,..},{guardian,0,..}]` o contrário: `kills == 0` sempre, e a "primeira vitória" garante o Único em **toda** vitória.
  2. `kills_since_unique = -1000`: a garantia só viria na vitória 1005 (`revisao_M1_pity_negativo_*`: `0 != 1`).
  3. `kills = 2147483647`: `++kills` e `killsSinceUnique + 1` estouram `int` com sinal (UB). O UBSan acusa `loot.cpp:124:78: runtime error: signed integer overflow: 2147483647 + 1` nos dois compiladores; no Clang, com `halt_on_error=1`, o processo aborta (`revisao_M1_kills_int_max_estoura_no_roll_UB`).
- **Por que médio, não alto:** o core nunca grava duplicata nem valor fora de faixa (sempre `FindOrAdd` e `++`); só um save editado, corrompido ou escrito por outra ferramenta chega aqui. O checksum SHA-256 sem segredo não impede edição.
- **Correção:** em `CharacterFromJson`, recusar com `BadData` (ou fundir duplicatas pelo maior `kills`) e cortar para `0 <= killsSinceUnique <= kills <= teto`; uma função só de busca para ler e gravar; somar com saturação em `RollTable`.

### M2. Expedição guardada no save entra sem validação

- **Onde:** `src/save.cpp:376-384` (`character_index` e `request.start_utc` sem faixa); `include/shatter/clock.h:66` (`ref - startUtc` em `int64`); `src/save.cpp:631-634` e `src/c_api/shatter_c.cpp:2920-2921`.
- **Cenários que falham (confirmados):**
  1. `start_utc = INT64_MIN + 1`: `ref - startUtc` estoura (UB; UBSan: `clock.h:66:52: signed integer overflow`). Em Release o tempo decorrido fica negativo e a coleta responde `NOT_FINISHED` para sempre: a expedição fica presa e bloqueia novos inícios (`revisao_M2_start_utc_extremo_*_UB`).
  2. `character_index = 5` com um personagem só: `CollectExpedition` devolve `false` e a API responde `COLLECT_ALREADY`, mas a expedição continua `Running` (`running_expedition` = 0) e bloqueia novos inícios (`revisao_M2_coleta_diz_already_*`: `0 != -1`).
- **Correção:** validar na leitura (`character_index` em `[0, n)`, `start_utc` entre 0 e `last_seen + margem`); fazer a subtração em `double` em `ComputeExpeditionWindow`; separar os motivos do `false` de `CollectExpedition` (índice inválido vira erro, não `ALREADY`).

### M3. As 21 chaves novas de `rules.csv` são opcionais e o número de balanceamento está no código

- **Onde:** `src/content.cpp:118-144` (`optional = true`) e `include/shatter/constants.h:42-68`: esquiva 3 / 1,5 / 0,35 / 0,2 / 400 / 0 / 0,1 / 10; Guarda Quebrada 1,5 / 0,30 / 8 / 4 / 5; elite 2,0 / 1,2 / 3,0; `dodge_cancel_recovery_fraction` 0,5; `out_of_combat_seconds` 3,0; `potion_lockout` 1,0; `unarmed_weapon_damage_physical` 3,0; `require_on_screen_margin` 100.
- **Cenário que falha (confirmado):** um merge ou edição tira a linha `elite_life_mult` do `rules.csv`. O `Finalize` aceita e o elite usa o 2,0 do código, sem aviso; o validador Python acusa, mas a DLL carregada no jogo não (`revisao_M3_*`). Viola "nenhum número de balanceamento no código" (`CLAUDE.md`). O `rules.csv` real e todas as fixtures já têm as 62 chaves: a fase de transição acabou.
- **Correção:** tornar as 21 obrigatórias (`E_KEY_MISSING`, como as 41 antigas) e deixar os padrões de `constants.h` neutros (0), como os demais.

### M4. As 5 tabelas novas continuam opcionais

- **Onde:** `src/content.cpp:359-380` (`optionalTable = true` em `potions.csv`, `elite_modifiers.csv`, `boss_phases.csv`, `boss_patterns.csv`, `enemy_ai.csv`) e `:1121`.
- **Cenário que falha (confirmado):** a cópia dos dados para `StreamingAssets` perde o `potions.csv`. O conteúdo real finaliza sem erro com `Potions()` vazio: o herói fica sem poção no manual e no idle (o recuo passa a depender só da vida), e ninguém é avisado (`revisao_M4_*`). Sem `enemy_ai.csv` as fichas de ataque somem do simulador do mesmo jeito.
- **Correção:** tornar obrigatórias (o conteúdo real e as fixtures já têm as 5). Se for preciso abrir conteúdo antigo, exigir por `content_version`.

### M5. A barreira da Poção de Resguardo tem regra duplicada e diferente no manual e no idle

- **Onde:** manual: `src/c_api/shatter_c.cpp:320-335` (`ApplyPotionToVitals`: `vitals.barrier = po.barrierAmount`, substitui a barreira inteira; a regra de teto da cura também mora na camada da API) e `src/combat.cpp:96-102` (`TickVitals` zera a barreira inteira quando o tempo da poção acaba). Idle: `src/expedition.cpp:300-308` e `:486-493` (só a parte da poção entra e sai; a de outras fontes fica).
- **Cenário (só pela leitura):** barreira de outra fonte (o simulador já soma `e->barrier` de efeitos em `expedition.cpp:342` e `:418`) mais o Resguardo. No manual a barreira de fora some ao beber e de novo quando a poção expira; no idle ela fica. A paridade manual × idle quebra. Hoje é latente: nenhum efeito do conteúdo real dá barreira.
- **Correção:** um campo próprio para a barreira de poção em `Vitals` e uma função do core (`ApplyPotionBarrier`/`TickPotionBarrier`) usada pela API C e pelo `EncounterSim`; mover o teto da cura para o core; teste de paridade.

### M6. O layout 1.1 confere poucos campos

- **Onde:** `src/c_api/shatter_c.cpp:256-278` (`kLayoutExt`): de `shatter_rules_ext` (19 campos) só o tamanho e 3 offsets; `shatter_boss_info` 2 offsets; `shatter_potion_outcome` 1; `shatter_vec2` e `shatter_boss_context` só o tamanho. Repete o M-08 do docs/11 (o `ext2` está completo).
- **Cenário que falha (confirmado):** o espelho C# de `shatter_rules_ext` troca `dodge_duration` e `dodge_iframes`; tamanho e offsets conferidos batem e `shatter_layout_check_ext` devolve `OK` (`revisao_M6_*`: `0 != 6`). Os i-frames passam a durar a esquiva inteira.
- **Correção:** listar todos os offsets com X-macro e subir `SHATTER_LAYOUT_EXT_COUNT` (ou criar um `ext3`).

### M7. Testes fixam valores de balanceamento do CSV real

- **Onde:** `tests/test_elite_unique.cpp:429-465` (`content_real_prototype_tables_load_and_validate`: contagem de linhas 2/3/2/5/3, `retreat_life_fraction` 0,25, `dodge_recharge` 1,5, `potion_lockout` 1,0, `shieldArcDegrees` 120, `unlockLevel` 4, `fixedChance` 0,2, pity 5, vida 700 + 50×2); `tests/test_round2.cpp:77-78, 86, 88, 98` (o `Replace` exige o texto `unarmed_weapon_damage_physical,3`), `:156-159`, `:170`, `:177`, `:180`, `:185`, `:189-194`, `:203-208`; `tests/test_c_api.cpp:1533` e `:1540` (telegraph 0,3).
- **Cenário que falha (confirmado numa cópia):** mudar 7 células válidas, só de balanceamento (`potion_lockout` 1,2, `unarmed_weapon_damage_physical` 4, `dodge_recharge` 1,6, `retreat_life_fraction` 0,3, `attackSpeedMult` do Veloz 1,3, `attackTokens` 3, `summonAtFraction` 0,4) deixa 5 testes vermelhos: `content_real_prototype_tables_load_and_validate`, `r2_unarmed_*`, `r2_attack_tokens_in_real_content_*`, `r2_swift_elite_*` e `r2_new_columns_are_read_from_the_real_content`. O Game Designer não consegue ajustar o CSV sem mexer em C++.
- **Correção:** comparar com o valor lido do banco (`real->Rules().x`, `swift->attackSpeedMult`) ou usar a fixture `rich` para números exatos; no conteúdo real, testar só invariantes (carrega, coluna lida, faixa, coerência), como o `a988666` já fez com `idleDamageTakenMult`.

### M8. Cobertura fraca nas regras novas

- **Volátil no idle:** nenhum teste de `TickExplosions`, do laço que espera as explosões pendentes nem da esquiva da explosão (`expedition.cpp:564-588`); só os números do perfil são testados (`test_elite_unique.cpp:110-113`).
- **Fichas de ataque:** `test_round2.cpp:110-152` compara só o dano médio com 0, 1 e 2 fichas. Falta afirmar "no máximo N com o ciclo em curso", a devolução da ficha quando o portador morre e o rodízio por `lastAct` (o código em `expedition.cpp:647-683` está certo pela leitura).
- **Poções:** `AddChargeOnEliteKill` só é testada com máximos 3 e 2, onde o B1 não aparece; nenhum teste de paridade da barreira manual × idle (M5).
- **Chefe:** nenhum teste de dano durante o stagger que cruza o limiar de fase (conferido à parte: funciona).
- **Save v2 malformado:** nenhum teste de faixa para `boss_progress`, `potion_slots` e expedições (M1, M2, B6).
- **API C:** nenhum teste de início confiável com relógio voltando (A2) nem de coleta com `character_index` inválido (M2).
- **Correção:** um teste por lacuna; os de M1, M2, A2 e B6 já estão na seção 6 (desligados até a correção).

---

## 5. Baixo

### B1. A carga ganha ao matar elite se perde quando a poção com menos cargas já está cheia

- **Onde:** `src/combat.cpp:230-245` (`AddChargeOnEliteKill` escolhe a poção de menos cargas absolutas, mesmo cheia, e devolve `false`). O header promete "`*added = 0` se todas estavam cheias" (`shatter_c.h:762`).
- **Cenário (confirmado):** Vida 2/3 e Resguardo 1/1 (máximo 1): o Resguardo é escolhido, está cheio, e a Vida não ganha a carga (`revisao_B1_*`). Com o conteúdo real (3 e 2) não acontece.
- **Correção:** ignorar as cheias na escolha. Confirmar a intenção com o Game Designer.

### B2. No idle, o DoT do herói ignora a barreira do elite

- **Onde:** `src/expedition.cpp:620-633`: o `HitInput` do tick não recebe `defenderBarrier` e o resultado não grava `e.barrier`; o golpe direto respeita (`:448-451`; docs/04 §11, passo 9).
- **Cenário (confirmado):** Corte de Ferro só com veneno contra a Sentinela Escudada: o elite morre no mesmo tempo com e sem a barreira de 40% (`revisao_B2_*`: 92,5 s nos dois).
- **Correção:** `in.defenderBarrier = e.barrier;` e `e.barrier = r.defenderBarrierAfter;`.

### B3. A explosão do Volátil e o DoT recebido não usam `idleDamageTakenMult`

- **Onde:** `src/expedition.cpp:577-586` (coeficiente 1,0) e `:605-613`; o golpe inimigo usa `coef × prof.damageTakenMult` (`:545`).
- **Cenário (só pela leitura):** a alavanca de calibração do idle (R2.1.5) não vale para essas fontes. Latente: o Volátil tem peso 0 e nenhum inimigo real aplica DoT.
- **Correção:** aplicar o mesmo multiplicador ou documentar a exceção no docs/13.

### B4. Entrada fixa fora da tabela de topo do chefe é aceita e nunca cai

- **Onde:** `src/loot.cpp:114` (fixas só em `depth == 1`) e `:144` (fixas fora do sorteio em qualquer profundidade); `src/content.cpp:1494-1495` não recusa fixa em subtabela nem em tabela que não é de chefe. O `validate_data.py:804` só pega `kind = unique` (`E_UNIQUE_TABLE`).
- **Cenário (confirmado):** livro de especialização com chance fixa 1 e garantia numa subtabela sorteada pelo chefe: o `Finalize` aceita e o livro cai 0 vezes em 50 vitórias (`revisao_B4_*`).
- **Correção:** no `Finalize`, recusar entrada fixa em tabela que não seja `lootTableId` de inimigo `isBoss` ou que seja alvo de `kind = table`.

### B5. Validador e core discordam no peso de entrada fixa

- **Onde:** `tools/validate_data.py:802` exige `fixedChance > 0` quando o peso está vazio; `src/content.cpp:1494` aceita peso vazio se houver qualquer campo fixo (garantia ou pity com chance 0).
- **Cenário (só pela leitura):** a linha `...,true,0,true,5` passa no core e falha no validador.
- **Correção:** escolher uma regra e alinhar os dois.

### B6. `recharge_remaining` do save sem teto: a poção nunca recarrega

- **Onde:** `src/combat.cpp:196` (`MakePotionBelt` aceita qualquer valor > 0) e `src/save.cpp:250`; o mesmo vale para o progresso que volta pela API (`shatter_c.cpp:1036-1042`).
- **Cenário (confirmado):** `recharge_remaining = 1e12` com 0 cargas: depois de `rechargeSeconds + 1` s continua com 0 (`revisao_B6_*`).
- **Correção:** `std::min(q.rechargeRemaining, p.rechargeSeconds)` em `MakePotionBelt`.

### B7. `shatter_elite_apply` não é idempotente e aceita multiplicadores do chamador

- **Onde:** `src/combat.cpp:476` (`ApplyEliteToStats` só acrescenta) e `src/c_api/shatter_c.cpp:2640-2648`; `EliteFromC` (`:381-396`) copia `life_mult`, `damage_mult` etc. da struct do chamador.
- **Cenário (confirmado):** aplicar duas vezes no mesmo bloco (reinício no checkpoint com bloco reaproveitado, docs/13 R2.4) leva a vida de 96 para 192 e depois 384 (`revisao_B7_*`). E o C# pode mandar multiplicadores que não vieram do banco, contra o espírito do A-06 do docs/11.
- **Correção:** `stats.RemoveModifiersFrom("elite")` antes de acrescentar; receber `modifier_id` + `rolled` e montar o perfil pelo banco.

### B8. `shatter_boss` depende do `shatter_db` sem dono

- **Onde:** `src/c_api/shatter_c.cpp:41-46` e `include/shatter/combat.h:316-319` (`db_`, `boss_`, `phases_`, `patterns_` são ponteiros para dentro do banco); o vínculo existe só no comentário do header.
- **Cenário (confirmado):** destruir o banco antes do chefe: ASan acusa `heap-use-after-free` em `BossFight::PickAndStart`; em Release, falha de segmentação (`revisao_B8_*_UB`). Uso errado documentado, mas sem proteção, e o `SafeHandle` do C# ainda não conta uso entre handles.
- **Correção:** contagem de referências no `shatter_db` (o `destroy` só libera quando o último chefe sair) ou teste `Interop.*` no C# para a ordem de descarte.

### B9. Versão da API e build de Release com sanitizer

- `SHATTER_C_API_VERSION` continua 1 (`shatter_c.h:29`) embora o header prometa subir a cada mudança incompatível de JSON (`:22`): a 1.1 mudou o JSON do pedido, do progresso e do resultado, o save foi para v2 e duas funções da v1 passaram a recusar sempre. Um wrapper 1.0 passa no `VersionMatchesSource` e quebra só em execução. Correção: subir para 2, ou o C# exigir `shatter_api_minor() >= 1`.
- GCC Release + `SHATTER_SANITIZE=ON` não compila por `-Wmaybe-uninitialized` dentro de `<regex>` (`tests/test_save_schema.cpp:51`, `tests/test_text_and_code.cpp:104`). Fora da matriz do CI; só importa se alguém usar essa combinação. Correção: `-Wno-maybe-uninitialized` nos testes quando `SHATTER_SANITIZE` e não Debug, ou trocar o `std::regex` por comparação simples.

---

## 6. Testes novos (reproduzem os achados)

Três arquivos novos em `ShatterCore/tests/`, sem tocar em código de produção nem no `CMakeLists.txt`. Cada teste afirma o comportamento **correto**; como falha no `master`, fica **desligado** por padrão (sai cedo e passa), no mesmo padrão do `SHATTER_BALANCE_PROBE`. O nome traz o ID do achado. Quando o achado for corrigido, apague a guarda do teste.

```
SHATTER_REVISAO_BUGS=1 ./build/shattercore_tests revisao_           # 13 testes; hoje: 13 falham
SHATTER_REVISAO_UB=1   ./build/shattercore_tests <nome do teste _UB> # um por vez; UB: o sanitizer acusa ou aborta (B8 derruba até o Release)
```

| Teste | Achado | Hoje (Release) |
|---|---|---|
| `revisao_A2_inicio_confiavel_aceita_relogio_atrasado_e_coleta_na_hora` | A2 | `2 != 0`, `needed 22544 != 0` |
| `revisao_M1_boss_progress_duplicado_congela_o_contador` | M1 | `10 != 16` |
| `revisao_M1_save_aceita_boss_progress_negativo_ou_int_max` | M1 | leitura aceita −1000 e `INT_MAX` |
| `revisao_M1_pity_negativo_vindo_do_save_atrasa_o_unico` | M1 | `0 != 1` |
| `revisao_M1_kills_int_max_estoura_no_roll_UB` | M1 | contador negativo; UBSan acusa `loot.cpp:124` (Clang aborta) |
| `revisao_M2_start_utc_extremo_no_save_estoura_a_janela_UB` | M2 | `NOT_FINISHED`; UBSan acusa `clock.h:66` (Clang aborta) |
| `revisao_M2_coleta_diz_already_com_expedicao_ainda_running` | M2 | `0 != -1` |
| `revisao_M3_rules_sem_chave_de_balanceamento_usa_numero_do_codigo` | M3 | `Finalize` aceita; usa 2,0 |
| `revisao_M4_conteudo_real_sem_potions_csv_finaliza_sem_pocoes` | M4 | `Finalize` aceita |
| `revisao_M6_layout_ext_aceita_campos_trocados` | M6 | `0 != 6` |
| `revisao_B1_carga_de_elite_perdida_com_pocao_minima_cheia` | B1 | `false`; `2 != 3` |
| `revisao_B2_dot_do_idle_ignora_a_barreira_do_elite` | B2 | 92,5 s com e sem barreira |
| `revisao_B4_entrada_fixa_em_subtabela_nunca_cai` | B4 | 0 livros em 50 vitórias |
| `revisao_B6_recarga_de_pocao_gigante_no_save_trava_a_carga` | B6 | `0 != 1` |
| `revisao_B7_elite_apply_duas_vezes_multiplica_de_novo` | B7 | `384 vs 192` |
| `revisao_B8_boss_depois_do_db_destruido_usa_memoria_liberada_UB` | B8 | falha de segmentação; ASan: `heap-use-after-free` |

Ligação dos testes da API C: o CMake põe `tests/*.cpp` em `shattercore_tests`, que liga só a biblioteca estática. `test_revisao_api_c.cpp` compila a própria API C na unidade (`#define SHATTER_C_STATIC` e `#include "../src/c_api/shatter_c.cpp"`); **só um arquivo** de `shattercore_tests` pode fazer isso, senão as funções `shatter_*` ficam duplicadas no link. Conferido com GCC e Clang, Release e Debug + ASan/UBSan, com `SHATTER_WERROR=ON`. Não conferido no MSVC.

Sem teste: C1 (o próprio build reproduz), A1 (o `test_c_api.cpp` existente reproduz sob ASan), M5, M7 (reproduzido numa cópia com o CSV mudado; ver o achado), M8, B3, B5 e B9.

---

## 7. Situação dos achados do core no docs/11

| docs/11 | Situação em `b39caf3` |
|---|---|
| A-05 (coleta confia no resultado do C#) | **Resolvido**: `shatter_save_collect_expedition` recusa; `_trusted` recalcula pelo pedido salvo e pela janela do relógio. |
| M-03 (`start_utc` e `seed` do chamador) | **Parcial**: o JSON recusa `seed`/`start_utc`, mas o `now` ainda vem do chamador e ignora o rollback (A2). |
| A-06 (posse e regras na fronteira) | **Parcial**: `shatter_resolve_hit_db` e `shatter_effective_cooldown_db` leem do banco; posse documentada no header, sem proteção (B8); elite com multiplicadores do chamador (B7). |
| M-11 (`potion_heal_fraction` 0,35 no código) | **Resolvido**: o campo saiu do pedido (`save_migrations.cpp:60`); a cura vem de `potions.csv`. |
| M-08 (layout incompleto) | **Aberto** e repetido na 1.1 (M6). |
| M-04 (`add_loot` aceita uid duplicado) | **Aberto** (`shatter_c.cpp:1903-1908`). |
| M-02 (previsão com teto de 100.000 amostras) | **Aberto** (`shatter_c.cpp:2074`). |
| B-12 (NaN na fronteira C) | **Parcial**: as funções novas da 1.1 recusam `dt` e valores não finitos; `shatter_effects_tick` e `shatter_resolve_hit` continuam sem checar (`shatter_c.cpp:1590-1599`, `:1515-1521`). |
| B-22 (`finalize` repetido) | **Aberto** (`shatter_c.cpp:1273-1277`). |

---

## 8. O que está bom

- **Regras do `CLAUDE.md`:** nenhuma exceção, RTTI, `static` mutável, RNG da STL, `unordered_map` iterado (só busca, `content.cpp:389`, `:433-434`) ou `pow/exp/log/sin` no golpe e no simulador. A trigonometria do escudo e do giro usa `DetCos/DetSin` (série de Taylor) e só `std::sqrt` (IEEE, resultado exato).
- **Determinismo:** `std::stable_sort` das fichas desempata pelo índice (`expedition.cpp:665`); os dois `std::sort` (`:1013-1014`) ordenam `double` só para percentis da previsão; o hash normaliza −0; o JSON recusa NaN e infinito; o sorteio do modificador de elite consome sempre 1 número do fluxo de eventos (`combat.cpp:448`). Simular em fatias dá o mesmo `resultHash` também com as regras novas (`content_real_idle_expedition_runs_the_new_rules_end_to_end`).
- **API C:** `BUFFER_TOO_SMALL` sem efeito colateral em `roll_boss_loot`, `collect_expedition_trusted`, `potions_info_json` e `boss_events` (trabalha em cópia e só confirma se couber); `needed` sempre preenchido; `dt` NaN/infinito recusado nas funções 1.1; `check_exports` passa com as funções novas.
- **Bug do Veloz** (R2.5 item 4) corrigido e coberto pelos dois caminhos (bloco com e sem os mods de elite).
- `summonAtFraction` e `wallStaggerSeconds` saíram do código para o CSV, como pedia o docs/13 R2.2.

---

## 9. Ordem sugerida de correção

1. C1 (uma linha) e A1 (uma variável no teste): o CI volta a ficar verde e passa a proteger o resto.
2. A2 e M2 (relógio e expedição guardada): integridade do idle.
3. M1, B6 (validação do save na leitura), M3 e M4 (obrigatoriedade de chaves e tabelas).
4. M5, B1, B2 e B3 (paridade manual × idle), M6 (layout), M7 (testes que fixam CSV).
5. O resto (B4, B5, B7, B8, B9).
