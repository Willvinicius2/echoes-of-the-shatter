# 11. Revisão de código — protótipo C# (Unity) e API C do ShatterCore

Data: 16/10/2026. Base: `master` @ `e1df5c4`. Outras pessoas mexem no Interop e no core em branches separados; esta revisão olha só o estado do `master`.

## 0. Escopo, método e limites

Revisado, só leitura:
- C#: `EchoesOfTheShatter/Assets/Scripts/` inteiro (Interop com Stub, Core, Gameplay com Logic, Presentation com Dev, UI, EditorTools) e os testes de `Assets/Tests/EditMode/`.
- API C: `ShatterCore/include/shatter/shatter_c.h`, `ShatterCore/src/c_api/shatter_c.cpp` (1806 linhas), `shatter_c.map` e `tests/test_c_api.cpp`. Para confirmar comportamento, li também trechos de `damage.cpp`, `effects.cpp`, `save.cpp`, `expedition.cpp`, `content.cpp`, `file_io.cpp` e `rng.h`.
- Referência: `CLAUDE.md` e `docs/tecnico/04_arquitetura.md` seções 4, 9, 10 e 13.

Não executei nada: nem os testes do Unity (EditMode), nem o build e o `ctest` do ShatterCore. As conclusões vêm de leitura de código; onde um cenário depende de execução, escrevi "pela leitura". Não há wrapper P/Invoke no `master` (nenhum `DllImport`, `SafeHandle` nem `Assets/Plugins/`), então a fronteira C# ↔ C ainda não foi exercitada de ponta a ponta.

### Contagem

| Prioridade | Achados |
|---|---|
| Crítico | 0 |
| Alto | 6 |
| Médio | 11 |
| Baixo | 26 |

Nenhum achado crítico: não vi perda de dados, crash certo nem falha de segurança no estado atual. Os altos são de contrato e arquitetura, que pioram quando a DLL entrar.

### Para a decisão do orquestrador (integridade, tempo e dados do jogador)

Nada aqui é autenticação nem pagamento. Dois pontos tocam a integridade do save e do relógio e pedem decisão de produto, não só de código:
1. A-05: `shatter_save_collect_expedition` confia no resultado enviado pelo C#.
2. M-03: `start_utc` e `seed` da expedição vêm do chamador, não do relógio confiável do core.

Como o checksum do save é SHA-256 sem segredo, um jogador consegue forjar o save de qualquer jeito. A decisão é se o core deve ser a barreira contra erro do próprio C# (recomendo que sim) e se há alguma promessa anticheat (não vi no plano).

---

## 1. Crítico

Nenhum.

---

## 2. Alto

### A-01. `IRulesCore` e `CombatRules` não têm contrapartida na API C: trocar o stub pela DLL obriga a calcular regra em C#

- Onde: `Interop/IRulesCore.cs:57-108`, `Interop/CombatRules.cs:1-33`, `Interop/Stub/StubRulesCore.cs:140-250`, contra `include/shatter/shatter_c.h:98-110` e `:259-518`.
- Problema: a fachada `IRulesCore` promete `TickVitals`, `CreateVitals`, `ResolvePotion`, `GainResource`/`TrySpendResource`, `GetActionTiming`, `GetEffectiveCost`, `GetMoveSpeedUu`, `CanAct`/`CanMove`, `PickAttack`, os dados de `PotionInfo`, `ClassInfo`, `EnemyInfo` e as constantes de `CombatRules` (esquiva, buffer, poção, fora de combate). Nada disso existe em `shatter_c.h`. Em `shatter_rules` faltam `dodge_*`, `potion_lockout`, `out_of_combat_seconds` e `dodge_buffer`. Não há `shatter_resolve_potion`, regeneração, nem consulta de tempos de ação com velocidade de ataque (só `shatter_effective_cooldown`). `CanAct` é "velocidade de ataque > 0": o core não tem o conceito de atordoamento.
- Cenário: o agente de Integração implementa `IRulesCore` sobre o header. Para cada método sem função C ele tem duas saídas: copiar a fórmula do stub para dentro do wrapper (viola "o C# não calcula regra", 04 seção 10.2 e `CLAUDE.md`) ou abrir mudança no contrato da API C, que está sendo editada em outro branch. Se escolher a primeira, o jogo manual e o simulador passam a divergir sem ninguém notar.
- Correção: antes de escrever o wrapper, decidir método a método (tabela em 04 seção 9.2): ou o core ganha a função (`shatter_vitals_*`, `shatter_potion_resolve`, `shatter_skill_timing`, `shatter_rules` com os campos de combate), ou o método sai da interface e vira dado de leitura (`shatter_db_lookup_json`). Subir `SHATTER_C_API_VERSION` e `SHATTER_LAYOUT_COUNT` junto. Registrar a lista em `docs/tecnico/09_mudancas_contrato.md`.

### A-02. O stub é um segundo motor de regras sem teste de paridade com o C++

- Onde: `Interop/Stub/*` (cerca de 1.900 linhas: `StubDamage`, `StubStatBlock`, `StubEffectSet`, `StubPcg32`, `StubContent`, `StubCsvTable`), `Tests/EditMode/StubRulesCoreTests.cs:58-70`.
- Problema: a única verificação cruzada com o C++ é um vetor de 5 números do PCG (`Pcg32MatchesTheCppHeader`). `ResolveHit`, StatBlock, efeitos e o parser de CSV não têm golden compartilhado. Já há divergências pequenas e visíveis: `PickAttack` (`StubRulesCore.cs:123-135`) não ignora peso ≤ 0, devolve o último ataque em vez de `-1` com soma zero e cai no último elemento (não no último de peso positivo) em arredondamento, ao contrário de `PickWeighted` (`loot.cpp:124-141`); o stub não implementa `triggeredBy`/cadeia de gatilhos nem a barreira por efeito (`StubEffectSet.cs` comentário do cabeçalho).
- Cenário: o designer ajusta um efeito ou uma habilidade e o jogo manual (stub) dá um resultado diferente do simulador (core) para a mesma seed. O teste de paridade noturno (04 seção 13.2, `Parity.*`) só vai achar isso depois de a DLL entrar, tarde demais para dizer qual lado está certo.
- Correção: gerar do C++ um arquivo golden de golpes (seed, atributos, entrada, saída completa de `HitResult`, 3 números de RNG consumidos) e de efeitos (sequência de `Apply`/`Tick`), e fazer o EditMode ler o mesmo arquivo; trocar `PickAttack` para a mesma semântica de `PickWeighted`. Enquanto isso, deixar o stub marcado como fora do caminho de decisões de balanceamento.

### A-03. Números de balanceamento fixos no código C#

- Onde: `Interop/Stub/StubPendingRules.cs:19-31` (11 chaves de esquiva, buffer, poção, fora de combate), `:35` (`ClassMoveSpeedUu = 450`), `:38-62` (ângulos de cone 90/100, velocidade de projétil 1400, giro 60/720, efeito de stun, família imune), `:72-97` (duas poções: 40%/30%, 3/2 cargas, 40/60 s, 6 s); `Gameplay/Logic/ProjectileSystem.cs:11` (`MaxActive = 300`); `Gameplay/CombatFeelSettings.cs:18-34` (hitstop, knockback e a lista de golpes pesados por ID de habilidade); `Gameplay/HeroController.cs:21-42` (nível 5, equipamento e barra por ID).
- Problema: `CLAUDE.md` proíbe número de balanceamento no código. O arquivo `StubPendingRules` assume o papel de segunda fonte de verdade e reconhece isso no próprio cabeçalho. O hitstop congela o tempo da entidade e o knockback muda posição, então afetam o combate, não só o visual. A lista de "golpes pesados" é uma propriedade da habilidade e hoje vive num `ScriptableObject` com IDs de conteúdo copiados à mão.
- Cenário: o Data Engineer põe `dodge_recharge` no `rules.csv` (o CSV vence, certo) mas esquece `dodge_cancel_recovery_fraction`: o jogo segue com 0,5 do C# e só um aviso no log ("valor provisório em uso") mostra isso. Uma habilidade nova pesada fica sem hitstop porque ninguém lembra de editar o SO.
- Correção: pedir ao Data Engineer as colunas e chaves listadas em `docs/13` (`rules.csv` com as 11 chaves, `potions.csv`, `coneAngle`, `projectileSpeed`, `turnRateDegPerSec`, `interruptsAction`, `stunImmune`, `heavy`), e fazer a carga **falhar** (e não avisar) quando a chave obrigatória faltar, em build de release. Apagar `StubPendingRules.cs` assim que as colunas entrarem. `MaxActive` pode ficar como limite técnico se o 04 seção 10.4 o mantiver.

### A-04. Movimento e posição ficam fora do passo fixo: o resultado depende do FPS

- Onde: `Gameplay/HeroController.cs:150-168` (`LateUpdate` move com `Time.deltaTime` e `CurrentVelocity()`), `Gameplay/EnemyController.cs:100-132`, `Gameplay/Logic/HeroCombatLogic.cs:80-95` (`CurrentVelocity`), `:200-225` (esquiva), `:350-358` (Investida); teste `Tests/EditMode/CombatSystemTests.cs:174-203`.
- Problema: as fases e os acertos rodam em passos de 1/60 s, mas o deslocamento do herói é aplicado uma vez por quadro com a velocidade que vale no instante do `LateUpdate`. A distância da esquiva e da Investida passa a ser `velocidade × soma dos dt dos quadros em que a fase estava ativa no LateUpdate`, e não `velocidade × duração da fase`. O `CombatSystem` lê `Position` atualizada no quadro anterior.
- Cenário: a Investida tem impacto de 0,2 s e 30 m/s (`skills.csv`: impacto 0,2, alcance 600 uu). A 30 FPS o herói anda em 6 ou 7 quadros, ±1 m conforme o alinhamento; em um quadro lento com vários passos (até 8 por quadro), a fase inteira pode acabar dentro dos passos, a velocidade lida no `LateUpdate` já é 0 e o herói não sai do lugar, mas `HitAroundSelf` roda no `ImpactEnded` na posição antiga. O README promete "mesma cena e mesma seed repetem a luta" (README seção 1), o que só vale com entrada parada.
- Por que os testes não pegam: `SameScriptSameDamageAt30And144Fps` deixa o herói e o Arauto parados (`CombatSystemTests.cs:185-200`); `TestWorld` não tem movimento nem esquiva com deslocamento.
- Correção: o `HeroCombatLogic`/`EnemyCombatLogic` devem integrar a posição no passo fixo (`Position += velocity * dt` dentro do `FixedTick`) e o MonoBehaviour só aplica `Position - posição anterior` ao `CharacterController`/agente, interpolando o visual com `FixedStepAccumulator.Alpha` (hoje sem uso). Adicionar teste de esquiva e Investida a 30/60/144 FPS comparando posição final.

### A-05. `shatter_save_collect_expedition` aceita qualquer resultado do chamador

- Onde: `src/c_api/shatter_c.cpp:755-779` (`CollectableFromJson`), `:1786-1804`; `src/save.cpp:575-600` (`CollectExpedition`).
- Problema: o core lê itens, pilhas e `xp_gained` direto do JSON do chamador. Só exige `result_hash != 0`. Não confere: que o `result_hash` bate com a expedição guardada no save (pedido e seed), que a expedição terminou (`status == Running` basta), que os itens existem no `ContentDB` (`ItemFromJson` valida formato, não conteúdo), nem limites de quantidade ou XP (`ApplyXp` aceita negativo e NaN).
- Cenário: bug no `ExpeditionService` do C# (resultado de outra expedição, resultado velho, JSON editado, ou coleta antes de o tempo passar) vira XP, itens e moedas no save, e a expedição fica `Collected`, sem volta. O requisito RF-55 ("coleta sem duplicar") fica cumprido; a integridade não.
- Correção: o core guarda no `SavedExpedition` o `result_hash` esperado só depois de a simulação do mesmo pedido terminar (ou refaz a simulação do `request` do save na coleta e compara com o hash recebido); validar itens e pilhas contra o `db`; recusar `xp_gained < 0` ou não finito; recusar coleta de expedição que o relógio ainda não considera encerrada, ou torná-la um caminho explícito de "recolher antes". Subir a versão da API.

### A-06. A fronteira C ainda não tem dono no C# e a API depende de convenções não verificáveis

- Onde: `src/c_api/shatter_c.cpp:1264-1332` (efeitos), `:1209-1245` (golpe), `include/shatter/shatter_c.h:355-390`; `Interop/RulesCoreFactory.cs:10`.
- Problema: três regras de posse existem só em comentário. (1) `shatter_effects_*` recebe o `shatter_statblock* target` a cada chamada; nada impede passar um bloco diferente do que recebeu os modificadores `fx:` (modificadores órfãos ficam no outro). (2) `shatter_resolve_hit` recebe `shatter_rules*` do chamador em vez do `shatter_db`, então o C# pode mandar constantes velhas, zeradas ou mexidas (viola "números vêm do banco"). (3) `shatter_db_load_directory` devolve um handle mesmo com erro (por desenho): quem esquecer de destruir vaza um banco inteiro. Como o `SafeHandle` ainda não existe, nenhum desses contratos tem teste do lado C#.
- Cenário: ao ligar efeitos e blocos de atributos de cada inimigo, um erro de índice passa o `target` do vizinho; a lentidão do Guerreiro Fantasma passa a valer no Cão. Ou um `shatter_rules` com campos zerados (struct mal preenchida) dá evasão máxima 0 e resistência máxima 0 sem nenhum erro.
- Correção: (1) criar `shatter_effects` já ligado a um `shatter_statblock` (contar uso para impedir destruir o bloco antes) ou conferir um id de dono; (2) trocar o parâmetro `rules` por `const shatter_db*` em `shatter_resolve_hit` e `shatter_effective_cooldown` (manter a struct só para testes); (3) o wrapper P/Invoke entra com `SafeHandle` por tipo e testes `Interop.*` antes de qualquer outro código chamar a DLL.

---

## 3. Médio

### M-01. Falha de um assinante do `EventBus` deixa o combate em estado quebrado

- Onde: `Core/EventBus.cs:44-70`, `Gameplay/Logic/CombatSystem.cs:236-241` (`Events.Publish(in hit)` seguido de `HandleDeath`).
- Problema: `Publish` não isola exceções. Uma exceção em qualquer assinante interrompe os seguintes e sobe pelo `ApplySkillHit`.
- Cenário: o `HudView.OnHit` ou o `PresentationController.OnHit` lança `NullReferenceException` com um alvo destruído. O `HandleDeath` do inimigo morto nunca roda: a vida já foi zerada, então o inimigo para de agir (`IsDead`), mas o telegraph em andamento nunca é encerrado (`EndTelegraph` só roda em `OnDeath`), o `CombatantDiedEvent` não sai (sem dissolução, sem drop futuro) e o resto do passo fixo é abortado.
- Correção: capturar por assinante em `Publish` (`try/catch` com `Debug.LogException`, mesmo padrão para o editor e o jogador) ou publicar o evento depois de aplicar o estado completo (morte incluída). Teste: assinante que lança.
- Nota para quando houver `Task.Run`: o `EventBus` não é thread-safe; `ExpeditionFinished` precisa ser reenfileirado para a main thread.

### M-02. `shatter_expedition_forecast` não pode ser chamada antes de iniciar, e o teto de amostras bloqueia

- Onde: `src/c_api/shatter_c.cpp:1760-1784` (teto 100000 em `:1765`), `include/shatter/shatter_c.h:507-511`; `src/save.cpp:~561` (`effectiveSeconds = 0.0` ao iniciar), `src/expedition.cpp:823-860`, `:99-103`.
- Problema: a previsão (RF-40, tela da Ilsa) vem antes de iniciar. A única função que monta o JSON de pedido é `shatter_save_expedition_request`, que exige uma expedição `Running` já gravada. O `ExpeditionRequest` criado ao iniciar tem `effective_seconds = 0`, e `BuildSetup` usa esse valor como limite de simulação: pela leitura, a previsão de um pedido recém-iniciado simula 0 s. Cada amostra é uma expedição completa (até 12 h) e o teto é 100 mil amostras, sem cancelamento.
- Cenário: o C# monta o pedido à mão, preenchendo `effective_seconds = horas × 3600` (reinterpretando campo do core) para conseguir uma previsão; ou chama com um pedido de 0 s e mostra "XP 0" na faixa. Uma chamada com `samples = 100000` congela a thread por minutos.
- Correção: aceitar na própria função `forecast` os parâmetros de início (`params_json` como em `shatter_expedition_check`) e o `save`, montar o pedido internamente com `effective_seconds = duration × 3600` e sem mudar o save; reduzir o teto (ex. 2000, vindo de `rules.csv`) ou aceitar `first_sample/count` para fatiar como o `simulate_range`. Teste de API para a previsão antes de iniciar.

### M-03. Início de expedição aceita `start_utc` e `seed` do chamador

- Onde: `src/c_api/shatter_c.cpp:846-850` (leitura), `:1640-1654`, `include/shatter/shatter_c.h:463-478`.
- Problema: o relógio confiável do core (`shatter_clock_resolve_now`, `shatter_trusted_now`) não é usado ao iniciar; `start_utc` vem do JSON. A `seed` também vem do C#, e o forecast aceita `base_seed` arbitrário.
- Cenário: bug ou ajuste manual põe `start_utc` no passado: a janela offline (`ComputeExpeditionWindow`) considera a expedição já terminada. Com a seed escolhida pelo chamador, dá para provar várias seeds com `shatter_expedition_forecast` e iniciar a melhor.
- Correção: `shatter_save_start_expedition` recebe `const shatter_trusted_now*` e a seed sai de um fluxo derivado do `next_item_uid`/seed da sessão no core. Ver "decisão do orquestrador" no topo.

### M-04. `shatter_save_add_loot` aceita uid duplicado e não valida contra o banco

- Onde: `src/c_api/shatter_c.cpp:1586-1615` (uids em `:1598-1602`).
- Problema: se o JSON traz `uid` diferente de zero, o item entra no baú sem checar que o uid já existe no baú ou no equipamento; só empurra o contador. Itens e pilhas também não são conferidos contra o `ContentDB`.
- Cenário: o C# repete `shatter_save_add_loot` com o mesmo JSON (retry depois de falha de gravação). O baú passa a ter dois itens com o mesmo uid; equipar, vender ou remover "por uid" age no item errado.
- Correção: recusar (ou reatribuir) uid que já exista; `PARSE_ERROR`/`INVALID_ARGUMENT` com o uid no erro. Teste de API para o retry.

### M-05. O herói é recadastrado e curado ao reativar o componente

- Onde: `Gameplay/HeroController.cs:113-117` (`OnEnable`), `:119-122` (`OnDisable`); `Gameplay/Logic/CombatSystem.cs:71-90` (`Register` chama `SetVitals(CreateVitals)`).
- Problema: `OnDisable` chama `Unregister`; `OnEnable` chama `Register` de novo, que dá novo `Id`, zera a "vida cheia" e o recurso, e cria um novo `Actor`. Não é um estado lido do herói.
- Cenário: um menu de pausa, uma cutscene ou o `DevZoneTeleport` desativa o componente por um quadro: o herói volta com vida cheia e recurso zerado no meio da luta.
- Correção: separar "entrar no combate" de "reiniciar vitais": `Register` só cria vitais se o `Combatant` nunca teve; ou o `OnDisable` não desregistra (o herói desativado já para de agir via `enabled`).

### M-06. A habilidade ignora o rank aprendido

- Onde: `Gameplay/Logic/CombatSystem.cs:197` (`skill.Coefficient(1)`), `Interop/SkillInfo.cs:48-55`.
- Problema: o coeficiente é sempre o do rank 1. O core usa o rank do `LearnedSkill` (`expedition.cpp:63-73`).
- Cenário: quando a árvore de rank entrar, o jogador sobe a Investida para o rank 3 e o dano manual continua o do rank 1, enquanto o idle usa o rank 3: paridade quebrada (04 seção 13.2, `Parity.*`).
- Correção: o `Combatant` carrega o rank por habilidade (vindo do save) e `ApplySkillHit` usa esse rank.

### M-07. Toasts de negação somem em silêncio porque as chaves de localização não existem

- Onde: `UI/HudView.cs:33-41` (`DenyKeys`), `UI/HudView.cs:418-427`; `Content/Data/Loc/ui.csv` (só `ui.hud.no_resource` e `ui.hud.potion_empty` existem); `Tests/EditMode/LocalizationTests.cs:69-81`.
- Problema: `ui.hud.cooldown`, `ui.hud.no_dodge_charges` e `ui.hud.locked` não existem; `OnDenied` faz `TryGet` e sai sem aviso. O teste `HudKeysExistInPtBrAndEn` não inclui essas três chaves, por isso passa.
- Cenário: o jogador aperta a esquiva sem carga ou usa uma habilidade em recarga e não recebe nenhum feedback (RF-15 e RF-19 pedem aviso).
- Correção: criar as três chaves em `ui.csv` (pt_BR e en) e listar **todas** as chaves de `DenyKeys` no teste, lendo o próprio array (tornar `DenyKeys` `internal`).

### M-08. O teste de layout da API C não cobre todos os campos das structs

- Onde: `src/c_api/shatter_c.cpp:72-119` (`kLayout`), `include/shatter/shatter_c.h:98-110` e `:267`.
- Problema: de `shatter_rules` (40 campos) só entram o tamanho e 3 offsets (`crit_multiplier_base`, `max_ai_rules`, `sim_fast_enabled`); em `shatter_forecast` e `shatter_save_summary` também faltam campos do meio. Duas `double` trocadas de ordem na struct espelhada do C# têm o mesmo tamanho e passam em `shatter_layout_check`.
- Cenário: o C# espelha `shatter_rules` com `block_cap` e `block_mitigation` trocados: o `Interop.VersionAndLayout` passa e o golpe usa 100% de mitigação de bloqueio como teto de chance.
- Correção: gerar a lista com macro X por campo (todos os `offsetof`) para as structs com mais de 6 campos e subir `SHATTER_LAYOUT_COUNT`.

### M-09. Cobertura fraca dos testes novos

- Onde: `Tests/EditMode/*` e `ShatterCore/tests/test_c_api.cpp`.
- Lacunas no Unity: nenhuma cobertura de `ProjectileSystem`, `EnemyCombatLogic` (telegraph, impacto por forma, `StateChanged`), `HeroCombatLogic` com movimento (A-04), `HeroController`/`EnemyController`, `PlayerInputHandler`, `GameRoot` (falha de carga), `ContentPaths`, `Presentation` e `UI` (README seção 1 promete "93 testes de lógica pura"). `DodgeNumbersMatchTheDesign` (`StubRulesCoreTests.cs:43-55`) fixa os números do stub no teste, copiando o dado em outro lugar. `SameScriptSameDamageAt30And144Fps` não testa movimento nem esquiva (A-04). Nenhum teste de exceção em assinante (M-01) nem de `Register` durante um passo.
- Lacunas na API C: nunca chamadas em `test_c_api.cpp`: `shatter_save_create`, `shatter_statblock_from_save`, `shatter_statblock_get_base`, `shatter_statblock_apply_tagged`, `shatter_statblock_clear_modifiers`. Sem teste de NaN/infinito em `dt`, `magnitude`, `defender_life`, `coefficient` (ver B-12), de retry em `add_loot` (M-04), de forecast antes de iniciar (M-02), de coleta com resultado de outro pedido (A-05) nem de `simulate_range` com `first_encounter` diferente de `next_encounter` do progresso.
- Correção: um teste por lacuna; priorizar A-04, A-05, M-01, M-04.

### M-10. Build de jogador não acha dados nem a DLL

- Onde: `Core/ContentPaths.cs:14-26`, `Interop/RulesCoreFactory.cs:10`; ausência de `Assets/Plugins/x86_64/` e de `Assets/StreamingAssets/Data/`.
- Problema: `ResolveDataDirectory` procura `StreamingAssets/Data` e cai para `Content/Data` ao lado de `Assets` (existe só no editor); se nenhum existir devolve o caminho de `StreamingAssets` mesmo inexistente. Ainda não há DLL.
- Cenário: um build de teste abre e `GameRoot` loga "Regras não carregaram"; a tela fica sem herói e sem tela de erro (04 seção 6.1 pede erro fatal visível).
- Correção: mover os CSV (04 seção 4.2, um único commit), copiar via `IPreprocessBuildWithReport` se o movimento adiar, e fazer o `GameRoot` mostrar a lista de erros em build de desenvolvimento e erro fatal em release.

### M-11. Número de balanceamento no código do core

- Onde: `ShatterCore/src/save.cpp:259` (`potion_heal_fraction` com padrão 0,35 em `ExpeditionRequestFromJson`).
- Problema: a fração de cura da poção no idle é lida com um padrão 0,35 no código, fora dos CSV (`CLAUDE.md`: "Nenhum número de balanceamento no código"). O campo também não aparece no formato documentado em `shatter_c.h:463-468` nem em `potions.csv`. Dois pedidos sem o campo e um com 0,35 explícito dão o mesmo resultado, mas mudar o CSV não muda o idle.
- Cenário: o Game Designer muda a poção de vida para 40% (docs/13 já fala em 40% para o jogo manual): o manual passa a curar 40% e o idle continua 35%, e a paridade 10% quebra sem aviso.
- Correção: mover para a tabela de poções (`potions.csv`, coluna `fractionOfMaxLife`) lida pelo `ContentDB`, remover o campo do `ExpeditionRequest` ou torná-lo obrigatório com erro.

---

## 4. Baixo

### Gameplay, Interop e Core C#

- **B-01. `Math.Acos/Asin/Sin/Cos` na lógica de combate** — `Gameplay/Logic/PlanarVector.cs:60-86` e `Gameplay/Logic/ShapeQuery.cs:34-38`. O .NET/Mono/IL2CPP não garante resultado idêntico em CPUs diferentes; um golpe na borda do cone pode acertar ou errar de forma diferente entre máquinas, mudando quem consome o RNG. Para replays na mesma máquina não importa; para uma suíte de paridade em CI entre Mono e IL2CPP, sim. Correção: comparar cone com produto escalar e `cos(metade do ângulo)` pré-calculado, e girar com `Vector` unitário em vez de `Math.Cos/Sin` por quadro.
- **B-02. Projétil some ao ser evitado** — `Gameplay/Logic/ProjectileSystem.cs:58-59`: `hit = true` mesmo quando `ApplySkillHit` devolve `false` (herói em invulnerabilidade da esquiva ou golpe evadido). Decisão de design: a flecha atravessa o herói que esquiva? Se sim, só marcar `hit` quando `Landed`.
- **B-03. `Step` itera uma lista que pode mudar** — `Gameplay/Logic/CombatSystem.cs:135-136`. `Register`/`Unregister` por MonoBehaviour acontecem fora do `Step` hoje, mas um `FixedTick` que desative um combatente (futura invocação) pula ou repete um elemento. Documentar a regra ou enfileirar registro/remoção para o fim do passo.
- **B-04. Alocação de string por efeito** — `Interop/Stub/StubEffectSet.cs:190,232,248` (`"fx:" + id` a cada `Apply`, expiração e `Clear`). Guardar a fonte já formada em `StubEffectData`. Some quando a DLL entrar.
- **B-05. `PickAttack` com semântica diferente de `PickWeighted`** (ver A-02) e `Potions.Sort` instável com `HotkeySlot` igual (`Interop/Stub/StubContent.cs:449`): duas poções sem tecla definida trocam de lugar entre execuções. Usar ordem do CSV como desempate.
- **B-06. Duas implementações do leitor de CSV** — `Core/CsvReader.cs` e `Interop/Stub/StubCsvTable.cs:119-186`. Diferenças: o do Core ignora aspas não fechadas e descarta um último campo `""` sem quebra de linha (`CsvReader.cs:70-73`); o do Stub reporta erro. `double.TryParse` do stub aceita "NaN" e "Infinity" (`StubCsvTable.cs:108-111`). Como o `Interop` não pode referenciar o `Core`, o certo é o stub sair com a DLL; até lá, copiar os mesmos casos de teste para os dois.
- **B-07. Exceções para falha esperada na carga** — `Interop/Stub/StubContent.cs:47` (`File.ReadAllText` sem proteção), `StubRulesCore.cs:36-40`: pasta sem permissão ou arquivo bloqueado lança `IOException` em vez de `RulesStatus.IoError` (04 seção 10.2). Capturar e devolver o status.
- **B-08. Descarte no encerramento** — `Core/GameRoot.cs:58-63` descarta o `RulesService` no `OnDestroy`; `StubRulesCore.Combat` lança `InvalidOperationException` quando o conteúdo é nulo (`StubRulesCore.cs:31`, `:279`). Se `CombatSystemHost.Update` ou `HudView.Update` rodarem depois no mesmo quadro de saída, a exceção polui o log. Garantir ordem de destruição (o host se desliga antes) ou checar `root.IsReady`.
- **B-09. Gravação de remapeamento não atômica** — `Gameplay/PlayerInputHandler.cs:99` (`File.WriteAllText`): queda de energia no meio deixa `bindings.json` truncado (a leitura já ignora o erro, `:109-112`, então só perde o remapeamento). Gravar em `.tmp` e renomear.
- **B-10. `RunSeed` por `DateTime.UtcNow.Ticks`** — `Core/GameRoot.cs:52`: duas cenas carregadas no mesmo tick (testes em lote) repetem a seed; a derivação de `DeriveSeed` espalha bem, então o risco é só repetição de teste. Usar um gerador do sistema na criação do slot, salvo no save.

### Apresentação e UI

- **B-11. Ferramentas de desenvolvimento entram no build** — `Presentation/Dev/CameraDistanceTuner.cs:101-124` (`OnGUI` com interpolação de string a cada evento de IMGUI, aloca por quadro), `Presentation/Dev/DevZoneTeleport.cs:23-31`: F1–F6 e o painel funcionam no jogador. Envolver em `#if UNITY_EDITOR || DEVELOPMENT_BUILD`. O `FollowCamera` e o `CameraDistanceTuner` também escrevem a mesma câmera (`RenderSettingsAsset.distance` é `[Range(48,66)]`, o preset "atual" é 42, fora da faixa documentada).
- **B-12. Sem validação de números não finitos na fronteira C** — `src/c_api/shatter_c.cpp:1284-1294` (`dt` em `shatter_effects_tick`; o core só testa `dt <= 0`), `:1209-1245` (`base_damage`, `coefficient`, `defender_life`), `:1264-1282` (`magnitude`), `:1138-1143` (`set_base`). Um NaN faz o efeito nunca expirar (`remaining <= kTimeEps` falso) e contamina vida e barreira. Recusar `!std::isfinite` com `INVALID_ARGUMENT`.
- **B-13. Layout do UI Toolkit a cada quadro** — `UI/DamageNumberLayer.cs:128-134`: `style.left/top` por rótulo ativo força recálculo de layout (até 64 por quadro). Trocar por `style.translate` (que não invalida layout).
- **B-14. Busca quadrática no desenho de projéteis** — `Presentation/ProjectilePresenter.cs:61-73`: para cada projétil vivo percorre todos os ativos (até 300 × 300 por quadro no pior caso) e a posição só muda a 60 Hz, sem interpolação (`FixedStepAccumulator.Alpha` não é usado). Indexar por `Id` e interpolar com `Alpha`.
- **B-15. Pool de VFX** — `Presentation/VfxPool.cs:44`: `systemsByInstance` guarda instâncias que o pool já destruiu (acima do máximo de 32) e só é limpo no `OnDestroy`; a reutilização chama `Play(true)` sem `Clear`, deixando partículas da vez anterior.
- **B-16. Tremor só em golpe pesado** — `Presentation/FollowCamera.cs:134-137`: o teste `!evt.IsHeavy` no topo vale também para o ramo de crítico do herói, então crítico de ataque leve nunca balança a tela (provável intenção: só pesado ou crítico). Confirmar com a ficha de juice (docs/03 seção 6).

### Textos e Loc

- **B-17. Número duplicado em texto localizado** — `Content/Data/Loc/content.csv:60` (`dodge.desc`: "Tem 3 cargas") repete `dodge_max_charges` do `rules.csv`. Trocar por `{value}` com número vindo do banco.
- **B-18. Aviso de chave duplicada por coluna** — `Core/LocalizationTable.cs:60-66`: a mesma chave duplicada gera um aviso por coluna de cultura. Contar uma vez por chave.
- **B-19. Painel de desenvolvimento com texto fixo** — `CameraDistanceTuner.cs:117` ("cam", "chao", "heroi"), aceitável por ser ferramenta (o código já avisa no comentário); fica resolvido com B-11.

### API C

- **B-20. `shatter_statblock_for_enemy` sem `shatter_error`** — `src/c_api/shatter_c.cpp:1120-1136` e `include/shatter/shatter_c.h:325-327`: o nível não é validado (negativo, zero, enorme) e o chamador não recebe mensagem. Mesma observação para `shatter_statblock_add_modifier` (`:1167`) e as funções de efeito: o contrato 9.2 pede `err` em toda função. Adicionar `err` na próxima mudança de versão.
- **B-21. `Text()` aceita byte NUL no meio** — `src/c_api/shatter_c.cpp:172-181`: um caminho `"a\0b"` com `len` cobrindo o NUL vira `std::string` com NUL e o Windows corta o nome no NUL. Recusar `\0` em caminhos e IDs.
- **B-22. `shatter_db_finalize` pode ser chamada de novo** — `src/c_api/shatter_c.cpp:967-975`: sem guarda de estado, e `shatter_db_load_table` depois de `finalize` retorna erro mas `finalize` repetido refaz o trabalho sobre um banco que outra thread talvez já esteja lendo. Recusar `finalize` duplicado.
- **B-23. `simulate_range` reserializa o progresso inteiro** — `src/c_api/shatter_c.cpp:679-724`, `:1714-1736`: cada fatia reescreve e relê todos os recibos acumulados (cerca de 1 MB em 12 h com `RECEIPTS`). Custo O(n²) no total, tolerável na primeira versão; manter o estado no core (handle) quando a fatia virar gargalo. `first_encounter` também não é conferido com `progress.next_encounter`.
- **B-24. `shatter_expedition_check` copia o save inteiro** — `src/c_api/shatter_c.cpp:1631`: custo proporcional ao baú a cada chamada (a tela de seleção chama a cada mudança de regra). Se a lista de itens crescer, mover a decisão para uma função const do core.
- **B-25. Cache mutável sob `const`** — `include/shatter/shatter_c.h:332-338` e `include/shatter/stats.h:115-116`: `shatter_statblock_get` e `shatter_resolve_hit` recebem `const shatter_statblock*` mas escrevem no cache interno. Está documentado, mas o tipo `const` convida a ler de duas threads. Tirar o `const` dos parâmetros ou documentar no tipo do wrapper C# (`ThreadAffinity`).
- **B-26. Mapa de exportação só para Linux** — `src/c_api/shatter_c.map`: no Windows a exposição depende de `__declspec(dllexport)` em `SHATTER_API`, que funciona; sem `.def`/teste de exportação para a DLL no CI do Windows (`tests/check_exports.cmake` só cobre Linux). Pouco provável de falhar, fácil de verificar com `dumpbin /exports`.

---

## 5. Checagens pedidas

| Checagem | Resultado |
|---|---|
| Handles e posse na fronteira C | O lado C++ está correto na leitura: `unique_ptr` + `release()` só ao fim, `*out = nullptr` antes de falhar, `destroy(NULL)` seguro, nenhuma alocação cruza a fronteira sem dono, nenhuma exceção declarada. O lado C# não existe ainda (A-06). `load_directory` devolve handle mesmo com erro, por desenho: precisa de `SafeHandle` com teste. |
| Condições de corrida | Nenhuma thread no C# hoje. Riscos futuros: `EventBus` sem sincronização (M-01), cache mutável em `const` (B-25), `finalize` repetido (B-22), destruição do `shatter_db` durante `Task.Run` (depende do `SafeHandle` com contagem, ainda não escrito). |
| Determinismo | PCG e `ResolveHit` do stub batem com o core pelo código lido (`StubDamage` ↔ `damage.cpp`). Quebras: posição fora do passo fixo (A-04), trigonometria em `float` (B-01), `PickAttack` divergente (A-02), `Potions.Sort` instável (B-05). Core sem `unordered_map` iterado em caminho de resultado (efeitos usam vetor, `EffectLookup` só para busca). |
| C# calculando regra | Sim, de forma provisória e documentada, no `Interop/Stub`. O desvio real é o buraco entre `IRulesCore` e `shatter_c.h` (A-01) e o ranking de habilidade (M-06). Fora do Stub, `HudView` decide só "sem recurso" por comparação (`HudView.cs:329`) e `HeroCombatLogic` calcula direção, distância da Investida e dos efeitos de forma (geometria, aceitável). |
| Números de balanceamento no código | A-03 (C#) e M-11 (core). |
| Textos visíveis fora da localização | Nenhum no jogo: UXML só com `LocLabel` e labels vazios preenchidos por código; `Debug.Log` não é visível ao jogador. Exceção: painel de desenvolvimento (B-11, B-19). Chaves faltando: M-07. |
| Alocação por quadro | Passo de combate sem alocação relevante (`EventBus.Publish` e structs). Exceções: `SourceOf` (B-04), `OnGUI` do tuner (B-11), layout do número de dano (B-13). `HudView` só reescreve texto quando o valor muda (boa prática). |
| Eventos desinscritos e objetos destruídos | `HudView`, `FollowCamera`, `ProjectilePresenter`, `TelegraphPresenter`, `PresentationController` assinam em `Start` e desinscrevem em `OnDestroy`; `AttributeComponent` libera os handles; materiais instanciados são destruídos. Um inimigo morto fica ativo e assinado até o `SetActive(false)` (2,5 s) e nunca é destruído (aceitável no protótipo). |
| Testes cobrindo a lógica nova | Parcial (M-09). A lógica pura de tempo e estados está bem coberta; movimento, projéteis, IA com forma de ataque, MonoBehaviours e a API C têm lacunas. |

---

## 6. O que está bom

- A API C segue o contrato: duas chamadas com `BUFFER_TOO_SMALL` que não muda RNG nem save (`shatter_loot_roll`, `:1388-1419`), `needed` sempre preenchido, validação UTF-8 forte, `shatter_error` do chamador sem `thread_local`, `static_assert` de tamanho e offsets das structs principais, `layout_check` com mensagem do primeiro campo diferente.
- `ResolveHit` do stub segue a mesma ordem do core, com 3 números de RNG por golpe e DoT sem RNG.
- O `FixedStepAccumulator`, o `ActionTimeline` (sobra de tempo passa para a fase seguinte) e a ordem estável de registro (`CombatOrderKey`) foram bem pensados para o determinismo.
- UI sem texto literal, números de dano em pool e atualização do HUD só na mudança de valor.
