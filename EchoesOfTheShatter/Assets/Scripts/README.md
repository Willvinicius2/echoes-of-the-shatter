# Scripts do protótipo — Guerreiro na Cripta

Código C# do protótipo jogável (docs/02_requisitos.md, seção 2): o Guerreiro com movimento WASD e mira no mouse, ataque básico e as 4 habilidades, esquiva com 3 cargas, 2 poções, inimigos com a máquina de estados parado → perseguir → telegraph → atacar → recuperar, hitstop por entidade, números de dano e o HUD em UI Toolkit.

Nenhuma cena, prefab, `.asset` ou `.meta` foi criado fora do editor. Este README diz como montar a cena de teste no editor.

## 1. O que tem aqui

| Pasta | asmdef / namespace | Conteúdo |
|---|---|---|
| `Interop/` | `Echoes.Interop` (sem UnityEngine) | Fachada `IRulesCore` que o jogo usa para pedir regras ao ShatterCore, e tipos espelhados dos headers (`StatId`, `SkillTags`, `HitRequest`, `HitResult`, `RngState`...). |
| `Interop/Native/` | `Echoes.Interop` | **`NativeRulesCore`**: `IRulesCore` sobre `shattercore.dll` (API C v1) com P/Invoke (`ShatterNative`), `SafeHandle`, conferência de versão e layout e o padrão de duas chamadas para buffers. É o que o `RulesCoreFactory.CreateDefault()` devolve. |
| `Interop/Stub/` | `Echoes.Interop` | **`StubRulesCore`: implementação PROVISÓRIA em C# puro.** Lê os mesmos CSV do core e porta `ResolveHit`, `StatBlock`, efeitos e o PCG32 do `rng.h`. Fallback se a DLL não carregar, e dona do que a API C v1 ainda não oferece (seção 8). |
| `Core/` | `Echoes.Core` | `GameRoot`, `EventBus` sem alocação, `RulesService`, `LocalizationService` (CSV de `Loc/`), `ContentPaths`. |
| `Gameplay/Logic/` | `Echoes.Gameplay` (sem UnityEngine) | Lógica pura e testável: `CombatSystem` (passo fixo de 60 Hz), `HeroCombatLogic`, `EnemyCombatLogic`, `EnemyBrainLogic`, `DodgeLogic`, `ChargeTimer`, `CooldownTimer`, `ActionTimeline`, `ShapeQuery`, projéteis e eventos. |
| `Gameplay/` | `Echoes.Gameplay` | Componentes de cena: `CombatSystemHost`, `HeroController`, `EnemyController`, `AttributeComponent`, `PlayerInputHandler`, `CombatFeelSettings`. |
| `Presentation/` | `Echoes.Presentation` | `FollowCamera` + `RenderSettingsAsset`, `PresentationController`, `SkillPresentationSet`, `TelegraphPresenter`/`TelegraphView`, `ProjectilePresenter`, `VfxPool`. |
| `UI/` | `Echoes.UI` | `HudView`, `DamageNumberLayer`, `LocLabel` (UI Toolkit). UXML e USS ficam em `Assets/UI/`. |
| `../Tests/EditMode/` | `Echoes.Tests.EditMode` | testes de lógica pura (stub) e de paridade com a DLL nativa (esquiva, recargas, máquina de estados, passo fixo, combate com o stub e os CSV reais). |

Outros arquivos novos:
- `Assets/Settings/Echoes.inputactions`: mapa `Gameplay` com `Move`, `Aim`, `BasicAttack`, `Skill1..5`, `Dodge`, `Potion1..2`, `Inventory`, `PassiveTree`, `Map`, `Pause` (teclas do RF-64).
- `Assets/UI/Views/HudView.uxml`, `Assets/UI/Styles/Components.uss`, `Screens.uss` e `Tokens.uss`.
- `tools/gen_tokens.py`: gera `Tokens.uss` a partir de `docs/03_design_tokens.json`. Não edite o `Tokens.uss` à mão: mude o JSON e rode `python3 tools/gen_tokens.py`.

Direção das dependências: `Interop ← Core ← Gameplay ← Presentation ← UI` (docs/04_arquitetura.md, seção 4.3). A ordem de execução vem de `[DefaultExecutionOrder]` no código (GameRoot −1000, entrada −950, herói −940, inimigos −930, combate −900); não é preciso mexer em Project Settings. A ordem em que as entidades rodam no passo fixo (e consomem o RNG) é: herói, depois inimigos pela posição na hierarquia da cena; com `Fixed Run Seed` fixo, a mesma cena repete a mesma luta.

## 2. Primeira abertura

1. Abra o projeto `EchoesOfTheShatter/` na Unity 6.3 (6000.3.26f1). O editor gera os `.meta` dos arquivos novos; faça commit deles depois.
2. Espere a compilação. Se aparecer erro, veja a seção 7 (riscos já mapeados).
3. Rode os testes: **Window ▸ General ▸ Test Runner ▸ EditMode ▸ Run All**. Todos devem passar.
   Pela CLI (docs/04_arquitetura.md, seção 13.2):
   ```
   "%UNITY_EDITOR_PATH%" -batchmode -nographics -projectPath EchoesOfTheShatter ^
      -runTests -testPlatform EditMode -testResults TestResults/editmode.xml -logFile -
   ```
   Os testes acham os CSV em `Content/Data` a partir da pasta do projeto. Em outra pasta, defina `ECHOES_CONTENT_DIR`.

Os CSV continuam em `EchoesOfTheShatter/Content/Data` (fora de `Assets`). No editor, o `GameRoot` lê de lá; quando os CSV forem para `Assets/StreamingAssets/Data` (docs/04, seção 4.2), ele passa a ler de lá sem mudar código.

## 3. Assets a criar no editor

Crie a pasta `Assets/Data/Presentation/` e, nela:

| Asset | Como criar | Ajustes |
|---|---|---|
| `SO_RenderSettings` | Create ▸ Echoes ▸ Render Settings | Nada: os padrões são os da seção 3.2 (pitch 55°, yaw 45°, FOV vertical 14,2°, 56 m, suavização 7). Tremor: amplitudes em metros a 42 m (`shakeReferenceDistance`), escaladas por distância/42; raio do fade de oclusão `occlusionFadeRadiusMeters` = 4 m (seção 3.7). |
| `SO_CombatFeel` | Create ▸ Echoes ▸ Combat Feel Settings | Nada: hitstop 60/80/80/40 ms e knockback 20/6/0 cm dos tokens. A lista de golpes pesados já vem preenchida. |
| `SO_SkillPresentation_Warrior` | Create ▸ Echoes ▸ Skill Presentation Set | Opcional enquanto não houver Animator Controller (seção 5). |

Em `Assets/UI/`:

| Asset | Como criar | Ajustes |
|---|---|---|
| `ShatterPanelSettings` | Create ▸ UI Toolkit ▸ Panel Settings Asset | Scale Mode = **Scale With Screen Size**; Reference Resolution = **1920 × 1080**; Screen Match Mode = **Match Width Or Height**; Match = **1** (altura). Theme Style Sheet: o tema padrão de runtime que o editor cria junto. |

Materiais de graybox (em `Assets/Art/Materials/Graybox/`, todos com o shader **Universal Render Pipeline/Unlit** ou **Lit**):

| Material | Uso | Ajustes |
|---|---|---|
| `M_Graybox_Floor` | Chão | Lit, cinza-violeta escuro. |
| `M_Graybox_Hero` | Corpo do herói | Lit, carmesim. |
| `M_Graybox_Enemy` | Corpo dos inimigos | Lit, cinza claro. |
| `M_Telegraph_Placeholder` | Aviso no chão | Unlit, Surface Type **Transparent**, cor `#D8432F` com alfa 0,4 (token `telegraph.fill`). O `SG_VFX` com `_Progress` substitui depois. |

Opcional: um prefab `P_Projectile_Placeholder` (esfera de 0,2 m **sem colisor**) para ver as flechas do Arqueiro Fantasma.

## 4. Cena de teste: `Assets/Scenes/Test/Cripta_Test.unity`

File ▸ New Scene ▸ **Basic (URP)**, salve como `Assets/Scenes/Test/Cripta_Test.unity`. Mantenha a Directional Light.

### 4.1 Chão
1. 3D Object ▸ **Plane**, nome `Floor`, posição (0, 0, 0), escala (4, 1, 4) = 40 × 40 m. Material `M_Graybox_Floor`. Mantenha o MeshCollider (o CharacterController pisa nele).
2. Opcional: 4 a 6 **Cube** como pilares (escala 1 × 3 × 1) para ver a câmera e o NavMesh contornando.

### 4.2 Sistemas
1. Objeto vazio `GameRoot` → **Add Component ▸ GameRoot**. Deixe `Data Directory Override` vazio. Para repetir uma luta igual, ponha `Fixed Run Seed` = 12345. `Culture Override`: vazio (idioma do sistema), `pt_BR` ou `en`.
2. Objeto vazio `Combat` → **CombatSystemHost**: `Root` = GameRoot, `Feel` = `SO_CombatFeel`, `Max Steps Per Frame` = 8.
3. Objeto vazio `Presentation` → **VfxPool**, **TelegraphPresenter** (`Root` = GameRoot, `Fallback Material` = `M_Telegraph_Placeholder`) e **ProjectilePresenter** (`Root` = GameRoot, `Combat Host` = Combat, `Prefab` = `P_Projectile_Placeholder` se existir, `Height` = 1).

### 4.3 Herói (1,50 m; docs/04, seção 3.1)
1. Objeto vazio `Hero` em (0, 0, 0).
2. **Add Component ▸ Character Controller**: Radius **0.3**, Height **1.5**, Center **(0, 0.75, 0)**, Slope Limit 45, Step Offset 0.3.
3. **Add Component ▸ AttributeComponent**, **HeroController**, **PlayerInputHandler**, **PresentationController**.
4. `PlayerInputHandler`: `Actions` = `Assets/Settings/Echoes.inputactions`. `Load Saved Bindings` ligado.
5. `HeroController`:
   - `Combat Host` = Combat; `Input` = o próprio Hero; `Aim Camera` = Main Camera (ou vazio = Camera.main).
   - `Class Id` = `class.warrior`; `Level` = **5** (libera as 4 habilidades pelo `unlockLevel` do skills.csv; a Escudada está em 5 no CSV, docs/13 pede 4).
   - `Equipment` = `item_base.iron_sword` (a espada define o dano das habilidades que escalam com arma).
   - `Skill Bar` = `skill.warrior.iron_cut` (botão esquerdo, ataque básico), `skill.warrior.charge` (botão direito), `skill.warrior.stone_rift` (Q), `skill.warrior.shield_bash` (E), vazio (R), vazio (F).
   - `Checkpoint` = objeto `Checkpoint` (item 4.6); `Respawn Delay` = 1.5.
6. `PresentationController`: `Root` = GameRoot; `Animator` vazio por enquanto; `Skill Set` = `SO_SkillPresentation_Warrior` (opcional).
7. Filho visual `Body`: 3D Object ▸ **Capsule**, **remova o CapsuleCollider**, posição local (0, 0.75, 0), escala (0.6, 0.75, 0.6), material `M_Graybox_Hero`.
8. Filho `Nose`: **Cube** sem colisor, posição local (0, 1.1, 0.35), escala (0.15, 0.15, 0.3), para ver para onde o herói olha.

### 4.4 Inimigos
Para cada inimigo, objeto vazio na posição indicada, com **AttributeComponent**, **EnemyController** e **PresentationController** (`Root` = GameRoot). Filho visual: Capsule sem colisor, posição local (0, 0.9, 0), escala (1, 0.9, 1), material `M_Graybox_Enemy`.

| Objeto | Posição | `Enemy Id` | `Level` | Observação |
|---|---|---|---|---|
| `Sentinel_A` | (6, 0, 6) | `enemy.hollow_sentinel` | 3 | Ligue `Log State Changes` para ver os 5 estados no Console (RF-20). |
| `Sentinel_B` | (8, 0, 5) | `enemy.hollow_sentinel` | 3 | |
| `Hound` | (-7, 0, 8) | `enemy.ash_hound` | 3 | Rápido; sem telegraph no chão (`telegraphed = false`). |
| `Herald` | (0, 0, 12) | `enemy.stone_herald` | 3 | Lento, armadura alta, golpe em cone; imune ao atordoamento. |
| `Archer` | (-10, 0, -6) | `enemy.ghost_archer` | 3 | Dispara projétil (linha no chão no telegraph). |
| `Elite` | (10, 0, -8) | `enemy.shielded_sentinel` | 3 | Elite: knockback reduzido; matar dá +1 carga de poção. |

Movimento, escolha uma das duas opções:
- **Sem NavMesh (mais rápido para testar):** em cada inimigo, **Character Controller** com Radius 0.5, Height 1.8, Center (0, 0.9, 0). Ele anda reto até o herói.
- **Com NavMesh:** no `Floor`, **Add Component ▸ NavMesh Surface** (AI Navigation) ▸ **Bake**. Em cada inimigo, **Nav Mesh Agent** (Radius 0.5, Height 1.8, Acceleration 50, Stopping Distance 0, Auto Braking ligado) e **nenhum** CharacterController. Velocidade e giro vêm do CSV; o script desliga o giro do agente.

`Body Radius` = 0 usa o raio do agente ou do CharacterController.

### 4.5 Câmera 3/4 (docs/04, seção 3.2)
1. Objeto vazio `CameraRig` → **FollowCamera**: `Target` = Hero, `View Camera` = Main Camera, `Settings` = `SO_RenderSettings`, `Root` = GameRoot, `Shake Enabled` ligado.
2. Arraste a **Main Camera** (tag MainCamera) para dentro de `CameraRig`. O script põe a câmera a −56 m (`distance` do asset) no Z local, FOV vertical 14,2°, planos 1 a 150 m, e gira o rig para pitch 55° / yaw 45°.
3. Não use Cinemachine.

### 4.6 Checkpoint
Objeto vazio `Checkpoint` em (0, 0, 0). Ligue em `HeroController ▸ Checkpoint`.

### 4.7 HUD
1. Objeto vazio `HUD` → **UI Document**: `Panel Settings` = `ShatterPanelSettings`, `Source Asset` = `Assets/UI/Views/HudView.uxml`.
2. **Add Component ▸ HudView**: `Root` = GameRoot, `Hero` = Hero, `World Camera` = Main Camera. `Skill Icons` fica vazio até existirem os ícones `T_Icon_Skill_<id>_128`; sem ícone, o slot mostra o nome da habilidade (texto do Loc).

Salve a cena e adicione-a em File ▸ Build Profiles ▸ Scene List.

## 5. Animação (quando houver Animator Controller)
O `PresentationController` funciona sem Animator. Quando o `AC_Hero_Warrior` existir (docs/04, seção 3.3):
- Parâmetros: `Speed` (float), `IsDead` (bool), `IsStaggered` (bool), `ActionSpeed` (float; use como multiplicador de velocidade dos estados da camada Action).
- Camadas: `Base` (Idle ↔ Walk por `Speed`), `Action` com um estado vazio `Empty` e os estados de ação, `Hit` (aditiva, estado `Hit`).
- No `SO_SkillPresentation_Warrior`, uma entrada por habilidade: `skillId`, `animatorState`, duração do clipe e as frações `windupEnd`/`impactEnd`. Habilidade sem entrada usa `SkillStrike` (ou `SkillCast` em feitiço). A esquiva toca o estado `Dodge`.
- Flash e dissolução: o material do personagem precisa das propriedades `_HitFlash` e `_Dissolve` (o `SG_Character`). Sem elas, nada acontece.

## 6. Roteiro rápido no Play

| Verificar | Como | Requisito |
|---|---|---|
| Andar e mirar | WASD anda relativo à câmera; o herói olha para o mouse | RF-64 |
| Ataque básico | Botão esquerdo (segurar repete). Ciclo de 0,45 s (CSV) | RF-13 |
| Investida | Botão direito: avança até o mouse (máx. 6 m) e bate na chegada | RF-13 |
| Fenda de Pedra | Q: cone à frente; pega o grupo | RF-13 |
| Escudada | E: atordoa comuns por 0,8 s (o Arauto e a elite são imunes) | docs/13 item 3 |
| Ímpeto | Enche ao acertar; começa a esvaziar 3 s depois de sair de combate (valor provisório, falta no CSV) | RF-14 |
| Esquiva | Espaço: 3 pontos no HUD; a 4ª seguida é negada; 1 carga volta em 1,5 s; esquivar no fim do telegraph evita o golpe | RF-15 |
| Poções | 1 cura 40%; 2 dá barreira de 30% por 6 s; sem carga mostra o aviso | RF-19, docs/13 item 2 |
| Hitstop | Crítico e golpes pesados congelam só quem bateu e quem apanhou | RF-17 |
| Números de dano | Normal, crítico maior e amarelo, dano recebido em vermelho | RF-17 |
| IA | Com `Log State Changes`, o Console mostra Idle → Chase → Telegraph → Attack → Recover | RF-20 |
| Morte | Morrer mostra "Você caiu" e volta ao checkpoint em 1,5 s com vida e poções cheias | RF-18 |

Para conferir que o stub está em uso, o Console mostra `[Rules] Motor de regras PROVISÓRIO (stub em C#)` e a lista de valores de docs/13 que ainda faltam nos CSV.

## 7. Riscos de compilação a conferir no editor

O código foi compilado fora do Unity contra os assemblies de referência do UnityEngine 2021.3 (mesmas APIs usadas aqui) e os testes rodaram com NUnit no .NET 8. O que não deu para checar sem o editor:

1. **Input System 1.20**: `InputAction.WasPressedThisFrame()`, `IsPressed()`, `GetBindingDisplayString()`, `LoadBindingOverridesFromJson`, `SaveBindingOverridesAsJson` e o JSON do `Echoes.inputactions` (gerado no formato do `InputSystem_Actions` do template).
2. **`[UxmlElement]` e `[UxmlAttribute]`** (Unity 6) em `LocLabel` e `DamageNumberLayer`; no UXML eles aparecem como `<Echoes.UI.LocLabel loc-key="..."/>` e `<Echoes.UI.DamageNumberLayer/>`.
3. **USS**: `rotate`, `translate: -50% -50%`, `transition-*` e variáveis em `:root, .echoes-theme`. Se o UI Builder reclamar de alguma propriedade, o resto da folha continua valendo.
4. **asmdefs por nome**: as referências usam nomes (`Unity.InputSystem`, `Unity.AI.Navigation`, `UnityEngine.TestRunner`). Se o editor converter para GUID, aceite.
5. **`InternalsVisibleTo`** do stub para `Echoes.Tests.EditMode` (`Interop/Stub/StubAssemblyInfo.cs`).
6. **Project-wide actions**: o template liga o `InputSystem_Actions` como ações do projeto. Não atrapalha (o jogo lê o `Echoes.inputactions`), mas pode ser desligado em Project Settings ▸ Input System Package.

## 8. DLL nativa e o que ainda é do stub

`Assets/Plugins/x86_64/shattercore.dll` (Git LFS; `.meta` só para Windows x64, carregada na inicialização). Gerada por `tools\build_core.cmd Release` (saída em `build\Release\shattercore.dll`) e copiada para a pasta do plugin. O editor trava a DLL carregada: feche-o antes de trocar o arquivo.

`RulesCoreFactory.CreateDefault()` devolve o `NativeRulesCore`. Se a DLL não carregar (ausente, ponteiro do LFS, versão ou layout diferentes) cai no `StubRulesCore` e escreve um aviso no Console com o motivo (`RulesCoreFactory.LastFallbackReason`). O `GameRoot` loga `shattercore-native` quando o nativo está em uso.

**Nativo (API C 1.1, `NativeRulesCore`)**: carga e validação dos CSV, versão do conteúdo, constantes de combate por `shatter_db_rules_ext` (esquiva, buffer, trava de poção, fora de combate), atributos (herói, inimigo, vazio), golpe e recarga lendo o BANCO (`_db`), vida/recurso/barreira (`shatter_vitals_*`), tempos e custo (`shatter_skill_timing`), velocidade (`shatter_move_speed`; herói em uu/s), `CanAct`/`CanMove` com o `shatter_actor`, `PickAttack`, poção (`shatter_potion_resolve`), RNG por fluxo e efeitos (stun e Guarda Quebrada pelo actor; `IEffectSet.LastApply` traz as ordens do core). Além do `IRulesCore`: `CreatePotionBelt`, `CreateDodge`, `RollElite`/`GetEliteProfile`/`ApplyElite` e `CreateBoss`. Aceita `shatter_api_minor() >= 1` e confere `shatter_layout_check_ext` (37 valores).

**Segue no stub** (`NativeRulesCore.StillInStub`, logada ao iniciar): registros tipados de conteúdo (`Find*`, `Potions`; a API só tem `lookup_json`); `NextBelow` e `NextUnit`; tags dos efeitos de DoT; e a ligação do gameplay (`HeroCombatLogic`, `DodgeLogic`, `PotionSlot`, `EnemyBrainLogic`) ao cinto, esquiva, elite e chefe nativos, que o `IRulesCore` ainda não expõe. Expedição e save (`shatter_save_*`, `_trusted`) não têm camada no C# ainda.

**Posse dos handles (A-06)**: `DbHandle`, `StatBlockHandle` e `EffectsHandle` são `SafeHandle`; quem cria descarta (`RulesService` o núcleo, `AttributeComponent`/`Combatant` o statblock e os efeitos). O conjunto de efeitos segura o banco até ser descartado. `NativeLifetime` (Core) descarta os núcleos que sobrarem ao fechar o jogo, ao sair do Play e antes da recarga de domínio; com "Enter Play Mode Options" nenhum static guarda handle entre sessões. Efeitos e statblocks são da main thread.

**Posição no passo fixo (A-04)**: andar, esquiva, Investida, perseguição sem NavMeshAgent e knockback integram `Combatant.Position` dentro do `CombatSystem.Step`. `HeroController`/`EnemyController` só seguem a posição interpolada (`InterpolatedPosition(Clock.Alpha)`) no `LateUpdate`; colisão devolve a posição real à lógica. Com NavMeshAgent, o agente anda e a lógica copia a posição dele.

Testes: `NativeRulesCoreTests` roda os mesmos cenários nos dois motores (atributos, 1000 golpes com a mesma seed, efeitos, combate em passo fixo) e confere `Interop.VersionMatchesSource`.

## 9. Cena base de escala (`Assets/Scenes/Sandbox/Base_Escala.unity`)

Cena jogável para comparar distância da câmera e tamanho de mapa. Gerada por código: menu **Echoes ▸ Montar cena base** (ou `-executeMethod Echoes.EditorTools.SandboxBuilder.BuildFromCommandLine`). Pode rodar de novo a qualquer momento: recria a cena e atualiza materiais e assets pelos mesmos caminhos. Só primitivas da Unity (nada de FBX ou de assets do Spell Brigade).

- **Zona A (ARPG de PC)**, origem (0, 0, 0): sala 24 × 24, corredor de 6 m × 20 m, sala 32 × 32, corredor, arena do Guardião 40 × 40 com 8 pilares.
- **Zona B (MMO)**, origem (300, 0, 0): sala 32 × 32, corredor de 8 m × 20 m, sala 40 × 40, corredor, arena 56 × 56 com 8 pilares. Fica a mais de 160 m da zona A.
- Paredes de 3 m × 0,6 m, piso xadrez de 2 m (`M_Graybox_Floor_A/B`) e caixas de 1 × 1 × 2 m (sarcófago) para escala. Por zona: 3 cães, 2 sentinelas, 2 arqueiros e o Guardião (`enemy.crypt_guardian`, cápsula grande). O herói nasce na zona A, na sala 1.
- NavMesh assada nas duas zonas (asset em `Assets/Art/Generated/Sandbox/`). Dados de apresentação em `Assets/Data/Presentation/` (`SO_RenderSettings`, `SO_CombatFeel`, `SO_CameraDistancePresets`).

Teclas de desenvolvimento (não colidem com o `Echoes.inputactions`, que usa WASD, mouse, Q/E/R/F, 1/2, Espaço, I/P/M e Esc):

| Tecla | Ação |
|---|---|
| F1 / F2 / F3 / F4 | Câmera a 42 m (atual) / 56 m / 66 m / 80 m (começa em 56 m) |
| Roda do mouse, PageUp / PageDown | Afasta/aproxima 2 m por passo, entre 30 e 100 m |
| F5 / F6 | Teleporta o herói para a zona A / B (o checkpoint vai junto) |

O painel no canto superior esquerdo (abaixo do bloco de vida do HUD) mostra a distância, a largura × profundidade de chão visíveis e a altura do herói em pixels. FOV vertical fixo em 14,2°; o plano de corte distante é a distância + 80 m. Código em `Presentation/Dev/` (`CameraDistanceTuner`, `DevZoneTeleport`, `CameraFootprint`); a conta tem teste em `CameraFootprintTests`. Distância de sombra dos URP Assets (`PC_RPAsset`, `Mobile_RPAsset`) subiu de 50 para 120 m para cobrir o preset de 80 m (a seção 3.6 do docs/04 ainda diz 25 m).
