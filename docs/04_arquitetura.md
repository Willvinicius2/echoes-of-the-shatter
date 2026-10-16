# 04 — Arquitetura e contratos técnicos (Tech Lead)

Projeto: **Echoes of the Shatter**. Fonte de design: `docs/00_plano_existente.md` (Plano Steam v2.0). Motor: **Unreal Engine 5** (decisão do dono em 15/10/2026), substituindo o Godot 4 da seção 10 do plano.

Este documento é o contrato técnico de todos os agentes. Os headers em `ShatterCore/include/shatter/` são a parte executável deste contrato: se o texto e o header discordarem, **vale o header** e este documento deve ser corrigido.

---

## 1. Princípio central (preservado do plano)

> Um único motor de regras, independente de cenas e do motor gráfico, usado pelo combate em tempo real **e** pelo simulador idle. Mesma seed + mesmos dados + mesmo snapshot = mesmo resultado.

Como isso fica no UE5:

1. **ShatterCore** é uma biblioteca C++17 pura (só STL) com todas as regras: atributos, golpe, efeitos, loot, simulador de expedição, relógio, save. Compila e testa **sem o Unreal** (CMake + mini framework próprio).
2. O jogo UE5 **nunca calcula regra**. Atores e componentes só pedem ao ShatterCore e desenham o resultado.
3. **Dados fora do código**: todo número de balanceamento está em `EchoesOfTheShatter/Content/Data/*.csv`, lido diretamente pelo ShatterCore (o mesmo CSV nos testes, no bench e no jogo).
4. **RNG em fluxos separados** (`Combat`, `Loot`, `Events`), cada um com seed `DeriveSeed(seed_expedição, fluxo, índice_encontro)` (`rng.h`). Simular 1 vez ou em 10 partes dá resultado idêntico, e mexer no combate não muda o loot.

---

## 2. Decisões de base

| Tema | Decisão | Por quê |
|---|---|---|
| Motor | **UE 5.8** (decisão do dono em 16/10/2026, no lugar do 5.4), último hotfix disponível na F1, fixado até o Acesso Antecipado. Upgrade só entre fases, com todos os testes passando | Igual ao plano: atualizar o motor no meio quebra coisas. Conferir na instalação do 5.8 o Enhanced Input, `UEnhancedInputUserSettings` (remapeamento) e se o Paper2D continua incluído |
| Linguagem | C++ para regras e sistemas; Blueprint só para montagem de assets, animação de UI e ajustes visuais | Regras testáveis fora do editor; BP não pode divergir do motor |
| Padrão C++ | ShatterCore em **C++17**, que também precisa compilar como **C++20** (o UE 5.8 compila módulos em C++20) | Contrato do pedido e compatibilidade com UBT |
| Módulos UE | `ShatterCore` (wrapper que compila a biblioteca pura) e `EchoesOfTheShatter` (jogo). Ver seção 9 | Fronteira física: o módulo de regras não depende de `Engine` |
| Plugins ativos | `Paper2D`, `EnhancedInput`, `OnlineSubsystem`, `OnlineSubsystemSteam`, `OnlineSubsystemUtils` | Só o necessário; desligar plugins padrão não usados (Chaos Vehicles, Water, etc.) para reduzir o build (meta < 500 MB) |
| Plugins **não** adotados | PaperZD, CommonUI, GAS | PaperZD: dependência externa do Fab por versão de motor e quebra CI; nossa animação é simples (8 direções × 8 estados, seção 4 do plano) e é dirigida pelo combate em C++. GAS: duplicaria o motor de regras (atributos e efeitos já estão no ShatterCore) |
| Renderização | Sprites Paper2D em **planos no mundo 3D** com **câmera ortográfica** (seção 3) | Colisão, consultas de forma, navegação e ordenação por profundidade vêm de graça do 3D; a arte continua 2D |
| Pipeline gráfico | Forward Shading, sem Lumen, sem Nanite, sem Virtual Shadow Maps, sem TSR/TAA, materiais **Unlit + Masked** | Alvo de PC de entrada com GPU integrada e Steam Deck; pixel art não precisa de iluminação global |
| Entrada | **Enhanced Input**: `UInputAction` por ação nomeada, `IMC_Default`, remapeamento por `UEnhancedInputUserSettings` | Equivalente ao InputMap do plano; controle no 1.0 = só um novo Mapping Context |
| Localização | **String Tables** geradas de CSV + `.po` por cultura (seção 7) | Nenhum texto no código; mesma planilha `chave, pt_BR, en, es` do plano |
| Save | **JSON próprio** no ShatterCore (`save.h`), não `USaveGame` | Ver justificativa na seção 8 |
| Steam | `OnlineSubsystemSteam` (conquistas, overlay, presença) + chamadas diretas ao **Steamworks SDK** do UE (`ISteamUtils::GetServerRealTime`) atrás de `UShatterPlatformSubsystem` | O OSS não expõe a hora do servidor; o wrapper permite builds sem Steam (dev, CI) |
| Versionamento | Git + GitHub, **Git LFS** para `*.uasset *.umap *.png *.aseprite *.wav *.ogg *.ttf` | Igual ao plano |
| Plataforma | Windows x64 (D3D12, SM5; fallback D3D11). Steam Deck via Proton (mesmo binário) | Igual ao plano; um binário só = mesmo resultado de simulação no Deck |

---

## 3. Renderização pixel-perfect (isométrica 3/4)

**Decisão:** sprites como `UPaperFlipbookComponent` (Paper2D) colocados em planos no mundo 3D, câmera `UCameraComponent` em `ECameraProjectionMode::Orthographic`. Paper2D sozinho em modo "2D puro" com `TileMap` isométrico foi descartado: ordenação por Y, colisão em losango e navegação teriam de ser escritas à mão.

Parâmetros fixos (constantes de apresentação, ficam em `Config/DefaultGame.ini` na seção `[/Script/EchoesOfTheShatter.ShatterRenderSettings]`, não no CSV de balanceamento):

| Item | Valor | Observação |
|---|---|---|
| Resolução interna | 960 × 540 | Do plano |
| Câmera | Ortográfica, **pitch −30°, yaw 45°**, `OrthoWidth = 960` | Elevação de 30° faz um quadrado no chão virar losango **2:1** exato (tile 64 × 32) |
| Escala do mundo | 1 unidade UE = 1 pixel interno no plano da câmera | Lado da célula de chão = 32·√2 ≈ 45,2548 uu |
| Eixos | Gameplay no plano XY (Z para cima); pivô dos sprites nos pés | Colisão por cápsulas e sweeps no plano |
| Planos de sprite | Rotação fixa **perpendicular à direção da câmera** (não é billboard por frame) | Projeção ortográfica mostra o sprite 1:1, sem deformar |
| Ordenação | Profundidade real do 3D: todos os pixels de um plano têm a profundidade do pivô, o que equivale ao "Y-sort" isométrico. Materiais **Masked** (alfa binário) escrevem profundidade, sem problemas de ordenação de translúcidos | Chão e paredes de fundo são planos com deslocamento de profundidade fixo para trás |
| Texturas | `TextureGroup = 2D Pixels (unfiltered)`, sem mipmaps, sem compressão com perda (`TC_EditorIcon`/`UserInterface2D` RGBA8) | Pixels nítidos |
| Escala de tela | Inteira: ×2 em 1080p, ×4 em 4K; 1440p = ×2 com barras (padrão) ou "escala suave" (opção) | Do plano |
| Como escalar | `UShatterViewportClient` (subclasse de `UGameViewportClient`) calcula a escala inteira N = ⌊altura/540⌋ (mín. 1), restringe a área de jogo a 960N × 540N centralizada (barras pretas no resto) e define `r.ScreenPercentage = 100/N`, de modo que a cena é renderizada em exatamente 960 × 540 e ampliada com **`r.Upscale.Quality=0` (vizinho mais próximo)** | Evita SceneCapture (caro). Validar no protótipo da F1; plano B: SceneCapture 960×540 + `UImage` com filtro nearest |
| Câmera sem tremer | Posição da câmera arredondada para a grade de 1 uu no plano de visão (`UShatterPixelCameraComponent`) | Sem "shimmer" de pixel |
| Pós-processo | `r.AntiAliasingMethod=0`, motion blur, auto exposure, bloom e lens flare desligados por padrão | Bloom só em efeito pontual, se a direção de arte pedir |
| Interface (UMG) | Renderizada na resolução **nativa**, com escala de DPI inteira via `UShatterDPIScalingRule` (mesmo N) e fonte pixel | Texto nítido e legível; acentos testados desde o início |

---

## 4. Estrutura de pastas do repositório

```
/                                   raiz do repositório (Git + LFS)
├─ docs/                            documentos (este arquivo é o 04)
├─ ShatterCore/                     motor de regras C++17 puro (sem Unreal)
│  ├─ CMakeLists.txt                lib estática shattercore, testes, bench
│  ├─ include/shatter/*.h           CONTRATOS públicos (Tech Lead)
│  ├─ src/*.cpp                     implementação (Backend Engineer)
│  ├─ tests/test_framework.h        mini framework (TEST, EXPECT_*)
│  ├─ tests/*.cpp                   testes unitários, determinismo, idle, loot, save
│  ├─ tests/qa_*.cpp                testes do QA
│  ├─ tests/data/                   CSV mínimos de teste, saves de cada versão (saves/save_vN.json), golden/
│  └─ bench/*.cpp                   benchmark (Performance Engineer)
├─ EchoesOfTheShatter/              projeto UE 5.8
│  ├─ EchoesOfTheShatter.uproject
│  ├─ Config/                       DefaultEngine.ini, DefaultGame.ini, DefaultInput.ini, Localization/*.ini
│  ├─ Source/
│  │  ├─ EchoesOfTheShatter.Target.cs, EchoesOfTheShatterEditor.Target.cs
│  │  ├─ ShatterCore/               módulo UE que compila ../../../ShatterCore/src (seção 9)
│  │  │  ├─ ShatterCore.Build.cs
│  │  │  └─ Private/ShatterCoreModule.cpp, Private/Generated/*.gen.cpp (gerados pelo Build.cs)
│  │  └─ EchoesOfTheShatter/        módulo do jogo (Frontend Engineer)
│  │     ├─ EchoesOfTheShatter.Build.cs
│  │     ├─ Public/ e Private/ com subpastas: Core/ Rules/ Combat/ Characters/ Enemies/
│  │     │  Skills/ Expedition/ Save/ Platform/ Render/ Input/ UI/
│  │     └─ Private/Tests/          Automation Tests (EchoesOfTheShatter.*)
│  ├─ Content/
│  │  ├─ Data/*.csv                 balanceamento e conteúdo (fonte da verdade, empacotado como arquivo solto)
│  │  ├─ Data/schemas/              esquemas das tabelas (Data Engineer)
│  │  ├─ Localization/              String Tables e .po gerados
│  │  ├─ Art/ Audio/ UI/ Blueprints/ Maps/ Input/
│  └─ Plugins/                      vazio no AA
├─ tools/                           validate_data.py, build_loc.py (scripts sem dependências externas)
└─ .github/workflows/               CI (seção 13)
```

---

## 5. Camadas

```
┌──────────────────────────────────────────────────────────────────────┐
│  Blueprints / UMG  (WBP_HUD, WBP_Expedition, WBP_Report, BP_Enemy_*)  │  só apresentação
│  lê getters BlueprintPure, assina delegates, chama ações do jogo      │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ depende de (nunca o contrário)
┌──────────────────────────────▼───────────────────────────────────────┐
│  Módulo UE "EchoesOfTheShatter" (C++)                                 │  adaptadores
│  subsistemas, atores, componentes; converte FString↔UTF-8,            │
│  tempo real → passo fixo; nenhuma fórmula de regra aqui               │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ #include "shatter/*.h"
┌──────────────────────────────▼───────────────────────────────────────┐
│  ShatterCore (C++17 puro, só STL) — compilado pelo módulo UE          │  regras
│  "ShatterCore" e pelo CMake. Não conhece Unreal, cenas, tempo real    │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ lê
                    Content/Data/*.csv   (+ saves JSON)
```

Direção das dependências: `ShatterCore ← EchoesOfTheShatter ← Blueprints/UMG`. Uma camada só conhece a de baixo.

---

## 6. Fluxo de dados

### 6.1 Inicialização
1. `UShatterGameInstance::Init` → `UShatterRulesSubsystem::Initialize` lê `Content/Data/*.csv` (arquivos soltos empacotados) → `ContentDB::LoadTableCsv` em cada um → `ContentDB::Finalize()`.
   - Erros: build de desenvolvimento mostra lista na tela e no log; build Shipping abre tela de erro fatal ("dados corrompidos, verifique a integridade dos arquivos na Steam").
2. `USaveSubsystem` lê o slot ativo (`ReadSaveFile`). Se `LoadReport.usedBackup > 0`, a UI avisa o jogador.
3. `UShatterPlatformSubsystem` monta o `ClockInput` (UTC local + hora do servidor Steam, se houver) → `ResolveNow`.
4. `UExpeditionSubsystem` verifica expedição `Running`: `ComputeExpeditionWindow` → preenche `request.effectiveSeconds` → `SimulateExpedition` em `UE::Tasks::Launch` (fora da game thread; `ContentDB` é imutável e seguro para leitura concorrente) → o Tico mostra "voltando..." → relatório.
5. Coleta: `CollectExpedition(db, save, i, result)` + **um único** `WriteSaveFile`. `last_seen` = `NextLastSeen`.

### 6.2 Combate em tempo real (um golpe)
```
Enhanced Input → AShatterPlayerController → UShatterSkillComponent (fases: windup → impact → recovery, tempos do SkillData)
  → comportamento de forma (cone/projétil/área/avanço) faz a consulta de overlap no plano
  → para cada alvo atingido (no máx. 1 vez por golpe):
     UShatterCombatSubsystem::ApplySkillHit(atacante, alvo, skill)
        monta HitInput a partir dos StatBlocks dos dois UShatterAttributeComponent
        → shatter::ResolveHit(...)          ← A MESMA função do simulador
        → aplica HitResult (vida, barreira) e efeitos ao acertar (EffectContainer::Apply)
        → publica eventos no UShatterEventSubsystem (OnHit, OnKill, OnLoot)
  → apresentação reage aos eventos: número de dano, flash branco, hitstop, som, partícula
```
- Lógica de combate em **passo fixo de 1/60 s** com acumulador no `UShatterCombatSubsystem` (`UTickableWorldSubsystem`), independente do FPS (equivale ao `_physics_process` do plano).
- Hitstop por entidade: a entidade em hitstop não avança timers no passo fixo; o visual usa `CustomTimeDilation` do ator. Nunca congela o jogo todo.
- RNG no jogo manual: ao entrar numa área, `runSeed` novo; combate usa `Pcg32::ForStream(runSeed, Combat, 0)`; loot de cada abate usa `ForStream(runSeed, Loot, killIndex)`; eventos de área (elites, rastros do Predador) usam `ForStream(runSeed, Events, roomIndex)`.

### 6.3 Expedição (idle)
```
WBP_Expedition (Ilsa) → UExpeditionSubsystem::TryStart(mapa, duração, regras)
   → CanStartExpedition(...)            (domínio, cargas, 1 por vez, 1–12 h, ≤6 regras, IdleProfile)
   → ExpeditionRequest {snapshot congelado, seed, startUtc, duração, regras, content_version}
   → SaveData.expeditions[...] = Running → WriteSaveFile
   → ForecastExpedition para a previsão em faixa ("8–12 mil de XP, risco de recuo médio")
... jogo fechado ...
abrir → janela offline (clock.h) → SimulateExpedition → FinalizeExpedition → relatório → CollectExpedition → save
```

---

## 7. Localização

- Fonte: `Content/Data/Loc*.csv` com colunas `key, pt_BR, en, es, context, gender` (Narrative & Content). Chaves no formato do plano: `ui.inventory.title`, `skill.warrior.iron_cut.name`.
- `tools/build_loc.py` (Python, só biblioteca padrão) gera:
  1. `Content/Localization/StringTables/ST_<Grupo>.csv` no formato de importação de String Table do UE (`Key,SourceString,Comment`), com a cultura fonte **en**;
  2. `Content/Localization/Game/<cultura>/Game.po` para `pt-BR` e `es`.
  O commandlet `GatherText` (configs em `Config/Localization/Game_*.ini`) importa os `.po` e compila os `.locres`. Roda no CI.
- C++ e BP usam `FText::FromStringTable(TEXT("/Game/Localization/StringTables/ST_UI.ST_UI"), Key)` ou `LOCTABLE`. **Nenhum texto literal visível ao jogador** em C++ ou BP.
- ShatterCore não tem texto: só IDs e chaves (`ExpeditionResult::tipKeys`).
- Nomes de item com gênero: a base tem `grammaticalGender` (`content.h`); a UI passa `ETextGender` no `FText::FormatNamed` e o texto do afixo usa `{Gender}|gender(Flamejante,Flamejante)`. Nunca concatenar pedaços.

---

## 8. Save

**Decisão:** arquivo JSON próprio, gerado e lido pelo ShatterCore (`save.h`, `json.h`, `sha256.h`), **não** `USaveGame`.

Justificativa:
1. O plano exige JSON legível, migração explícita `vN→vN+1`, checksum SHA-256, 3 backups e gravação tmp→rename; `USaveGame` é binário por serialização de `UPROPERTY`, preso à versão do motor, e difícil de depurar e migrar.
2. A coleta "sem duplicar" depende de recalcular a expedição a partir do save. Com o save no ShatterCore, o teste de migração e o teste de determinismo rodam no CMake, sem editor.
3. Os saves de cada versão publicada ficam em `ShatterCore/tests/data/saves/` e são testados a cada commit.

Detalhes:
- Caminho: `FPaths::ProjectSavedDir()/SaveGames/slot_N` → no Windows, `%LOCALAPPDATA%\EchoesOfTheShatter\Saved\SaveGames\slot_1.json` (+ `.tmp`, `.bak1..3`).
- Envelope: `{format, save_version, sha256, data}`; hash sobre a forma **compacta canônica** de `data`.
- Seeds e UIDs (`uint64`) vão como **string decimal** no JSON.
- Quando salvar: ao trocar de área, coletar expedição, crafting, sair e a cada 5 min (timer do `USaveSubsystem`).
- Configurações (vídeo, áudio, teclas) ficam fora do save: `GameUserSettings.ini` e `UEnhancedInputUserSettings`, ambos em `Saved/Config` e `Saved/SaveGames/EnhancedInputUserSettings.sav` — **fora** do Steam Cloud.
- Steam Auto-Cloud: raiz `WinAppDataLocal`, subpasta `EchoesOfTheShatter/Saved/SaveGames`, padrão **`slot_*.json`** (backups e configurações ficam locais).

---

## 9. Como o ShatterCore é compilado dentro do UE

**Decisão:** fontes compiladas por um módulo UE próprio, **não** biblioteca pré-compilada em ThirdParty.

- Caminho exato do módulo: `EchoesOfTheShatter/Source/ShatterCore/ShatterCore.Build.cs`.
- O código continua em um só lugar (`/ShatterCore/include` e `/ShatterCore/src`). O Build.cs:
  1. adiciona `ShatterCore/include` a `PublicIncludePaths`;
  2. para cada `ShatterCore/src/*.cpp` (ordem alfabética), gera `Source/ShatterCore/Private/Generated/<nome>.gen.cpp` contendo só o cabeçalho de ponto flutuante abaixo e `#include "<caminho absoluto>"`; reescreve o arquivo só se o conteúdo mudar e apaga `.gen.cpp` órfãos;
  3. registra os `.cpp` em `ExternalDependencies` para o UBT reavaliar quando mudarem.
  Arquivo novo em `src/` exige rodar o UBT de novo (abrir o editor ou "Generate Project Files").
- Por que não ThirdParty com `.lib` pronta: exigiria CMake na máquina de cada dev, CRT e flags iguais às do UE (/MD, LTCG) e um `.lib` por configuração; qualquer diferença vira erro de link difícil.

Conteúdo de referência do Build.cs (o Frontend Engineer cria o arquivo com este conteúdo):

```csharp
using System;
using System.IO;
using System.Linq;
using UnrealBuildTool;

public class ShatterCore : ModuleRules
{
    public ShatterCore(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.NoPCHs;
        bUseUnity = false;              // cada .cpp do core é uma unidade separada
        bEnableExceptions = false;      // o core não usa exceções
        bUseRTTI = false;               // o core não usa dynamic_cast/typeid
        ShadowVariableWarningLevel = WarningLevel.Error;
        PublicDependencyModuleNames.Add("Core");   // só para IMPLEMENT_MODULE

        string CoreRoot = Path.GetFullPath(Path.Combine(ModuleDirectory, "..", "..", "..", "ShatterCore"));
        PublicIncludePaths.Add(Path.Combine(CoreRoot, "include"));

        string GenDir = Path.Combine(ModuleDirectory, "Private", "Generated");
        Directory.CreateDirectory(GenDir);
        string[] Sources = Directory.GetFiles(Path.Combine(CoreRoot, "src"), "*.cpp")
                                    .OrderBy(f => f, StringComparer.Ordinal).ToArray();
        var Wanted = new System.Collections.Generic.HashSet<string>();
        foreach (string Src in Sources)
        {
            string Gen = Path.Combine(GenDir, Path.GetFileNameWithoutExtension(Src) + ".gen.cpp");
            Wanted.Add(Path.GetFullPath(Gen));
            string Text =
                "// GERADO por ShatterCore.Build.cs — não editar.\n" +
                "#if defined(_MSC_VER) && !defined(__clang__)\n" +
                "#pragma float_control(precise, on)\n#pragma fp_contract(off)\n#endif\n" +
                "#if defined(__clang__)\n#pragma clang fp contract(off)\n#endif\n" +
                "#include \"" + Src.Replace('\\', '/') + "\"\n";
            if (!File.Exists(Gen) || File.ReadAllText(Gen) != Text) File.WriteAllText(Gen, Text);
            ExternalDependencies.Add(Src);
        }
        foreach (string Old in Directory.GetFiles(GenDir, "*.gen.cpp"))
            if (!Wanted.Contains(Path.GetFullPath(Old))) File.Delete(Old);
    }
}
```

`Private/ShatterCoreModule.cpp` contém apenas `IMPLEMENT_MODULE(FDefaultModuleImpl, ShatterCore)`. O módulo de jogo declara `PublicDependencyModuleNames.Add("ShatterCore")` e o `.uproject` lista os dois módulos (`ShatterCore` com `LoadingPhase: PreDefault`).

### Regras que o código do ShatterCore precisa seguir por causa do UE
- **Sem exceções** (`throw`/`try`) em `src/`; erros por `bool`/enum + `std::string* error`. (Só o framework de testes usa exceção, e ele não entra no UE.)
- **Sem RTTI** (`dynamic_cast`, `typeid`).
- Compila como C++17 e C++20, com `-Wshadow` e `/W4` sem avisos.
- Evitar nomes que colidem com macros do UE: `check`, `verify`, `ensure`, `TEXT`, `PI`, `INDEX_NONE`, `UE_*`.
- Sem estado global mutável (`static` não-const). Nada de `std::rand`, `std::random_device`, `<chrono>` de relógio, distribuições da STL.

---

## 10. Contratos entre camadas

### 10.1 ShatterCore (contrato da biblioteca)
| Regra | Detalhe |
|---|---|
| Pureza | Não lê relógio, não cria threads, não tem singletons. E/S só em `ContentDB::LoadDirectory`, `ReadSaveFile`/`WriteSaveFile` (via `IFileIO`) |
| Entrada/saída | Funções recebem `const ContentDB&` e structs por valor/referência; devolvem structs. `ResolveHit` não altera os StatBlocks |
| Imutabilidade | `ContentDB` é imutável depois de `Finalize()`; leitura concorrente é segura |
| RNG | Só `Pcg32` recebido por parâmetro. `ResolveHit` consome **sempre 3** números (crítico, evasão, bloqueio) |
| Determinismo de ponto flutuante | Sem `-ffast-math`/`/fp:fast` (CMake e `.gen.cpp` garantem). Em caminhos que afetam resultado, **só + − × ÷ e `std::sqrt`** (corretamente arredondados em IEEE-754). Proibido `pow/exp/log/sin` no simulador e no golpe; `x^1.5 = x·sqrt(x)` |
| Ordem estável | Iterar sempre `std::vector` em ordem do CSV/inserção; `unordered_map` só para lookup, **nunca** para iterar em código que afeta resultado |
| Números em texto | Parse e escrita de números independentes de locale: `std::from_chars`/`std::to_chars` (o Windows em pt-BR usa vírgula decimal em `strtod`/`printf`) |
| Texto | UTF-8 em `std::string`. Nenhum texto para o jogador; só IDs e chaves |
| IDs | `IsValidContentId`: minúsculas, `[a-z0-9_]`, segmentos com ponto, nunca renomeados |

### 10.2 Módulo UE `EchoesOfTheShatter`
- É o **único** cliente do ShatterCore. Converte `FString ↔ std::string` com `FTCHARToUTF8`/`FUTF8ToTCHAR`; IDs viram `FName` na interface (IDs são minúsculos, então a comparação sem diferenciar maiúsculas do `FName` não causa problema).
- Nenhuma constante de balanceamento em C++ ou BP: tudo vem do `ContentDB` (inclusive `RulesConstants`).
- Só o `UShatterCombatSubsystem` chama `ResolveHit` e `EffectContainer`; atores nunca mexem em vida diretamente.
- Tempo real → passo fixo antes de chegar ao core.

### 10.3 Blueprints / UMG
- Leem por funções `BlueprintPure` e eventos (`BlueprintAssignable`); agem por funções `BlueprintCallable` dos subsistemas (`TryStartExpedition`, `EquipItem`, `CollectExpedition`).
- Não guardam estado de regra, não calculam números, não chamam o core.

### 10.4 Classes UE previstas (contrato com o Frontend Engineer)

| Classe | Base | Responsabilidade |
|---|---|---|
| `UShatterGameInstance` | `UGameInstance` | Ponto de entrada; ordem de inicialização dos subsistemas |
| `UShatterRulesSubsystem` | `UGameInstanceSubsystem` | Lê `Content/Data/*.csv` (empacotados com `+DirectoriesToAlwaysStageAsUFS=(Path="Data")` em `DefaultGame.ini`), dono do `TUniquePtr<shatter::ContentDB>`; `GetDB()`; getters BP de exibição (nome/ícone/tooltip de skill, afixo, item) |
| `USaveSubsystem` | `UGameInstanceSubsystem` | Dono do `shatter::SaveData`; `Load/Save` via `ReadSaveFile/WriteSaveFile` + `MakeStdFileIO`; autosave de 5 min; delegate `OnLoadedFromBackup` |
| `UExpeditionSubsystem` | `UGameInstanceSubsystem` | `CanStart`, `TryStart`, previsão, simulação assíncrona (`UE::Tasks`), `Collect`; delegates `OnExpeditionReady(Result)` |
| `UShatterPlatformSubsystem` | `UGameInstanceSubsystem` | Steam: conquistas (OSS), hora do servidor (`ISteamUtils::GetServerRealTime`), Rich Presence; implementação nula sem Steam |
| `UShatterEventSubsystem` | `UGameInstanceSubsystem` | Barramento de eventos do plano: `OnEnemyKilled`, `OnItemDropped`, `OnHit`, `OnExpeditionFinished`, `OnLevelUp` |
| `UShatterCombatSubsystem` | `UTickableWorldSubsystem` | Passo fixo 60 Hz, RNG da sessão, `ApplySkillHit`, ticks de efeitos, hitstop por entidade |
| `UShatterPoolSubsystem` | `UWorldSubsystem` | Pools de projéteis, números de dano, partículas e itens no chão (limite de 300 projéteis) |
| `AShatterCharacter` | `ACharacter` | Personagem jogável: `UPaperFlipbookComponent`, `UShatterAttributeComponent`, `UShatterSkillComponent`, `UShatterSpriteAnimComponent` |
| `AShatterEnemy` | `ACharacter` | Inimigo: mesmos componentes + `UShatterEnemyBrainComponent` |
| `AShatterPlayerController` | `APlayerController` | Enhanced Input (`IMC_Default`, ações `IA_Move`, `IA_Aim`, `IA_BasicAttack`, `IA_Skill1..5`, `IA_Dodge`, `IA_Potion1..2`, `IA_Inventory`, `IA_PassiveTree`, `IA_Map`) |
| `UShatterAttributeComponent` | `UActorComponent` | Espelha o `shatter::StatBlock` + `EffectContainer` + vida/recurso/barreira atuais; relê quando `StatBlock::Revision()` muda; delegates `OnLifeChanged`, `OnDeath` |
| `UShatterSkillComponent` | `UActorComponent` | Barra de 6 habilidades, fases windup/impact/recovery, recargas (`EffectiveCooldown`), custo de recurso |
| `UShatterSkillBehavior` (+ `Cone`, `Projectile`, `Area`, `Dash`, `Self`, `Channel`, `Trap`) | `UObject` | Forma espacial escolhida por `SkillShape`; só faz consultas de overlap e entrega alvos |
| `UShatterEnemyBrainComponent` | `UActorComponent` | Máquina de estados parado → perseguir → telegraph → atacar → recuperar; chefes com tabela de padrões por fase |
| `UShatterSpriteAnimComponent` | `UActorComponent` | Escolhe flipbook por estado × 8 direções (4 + espelho no demo) |
| `AShatterProjectile` | `AActor` | Projétil em pool |
| `UShatterPixelCameraComponent` | `UCameraComponent` | Ortográfica, −30°/45°, arredondamento para a grade |
| `UShatterViewportClient` | `UGameViewportClient` | Escala inteira, barras, `ScreenPercentage` |
| `UShatterHUDWidget` | `UUserWidget` | Base C++ do `WBP_HUD`: vida, recurso, barra de habilidades, poções, Fervor, Cargas, Ouro |
| `UShatterExpeditionWidget`, `UShatterReportWidget`, `UShatterInventoryWidget` | `UUserWidget` | Bases C++ das telas de Ilsa, relatório do Tico e inventário |

---

## 11. Ordem de cálculo do golpe (`damage.h`)

Função única `shatter::ResolveHit(HitInput, RulesConstants, Pcg32& combatRng)`:

| Passo | Regra | Constante (CSV `rules.csv`) |
|---|---|---|
| 1 | `baseDamage[tipo] × coefficient` (se a skill escala com arma, `baseDamage` = dano da arma) | — |
| 2 | Mods por tag: `attacker.ApplyTagged(Damage, skillTags \| TagOf(tipo), base)` → `(base+Σflat)×(1+Σincreased)×Π(1+more)` | — |
| 3 | Crítico: `Chance(CritChance)`; multiplica por `ApplyTagged(CritMultiplier, tags, 1.5)` | `crit_multiplier_base = 1.5` |
| 4 | Evasão: **só ataques**; `min(EvasionChance, 0.70)`; evadiu → 0 | `evasion_cap = 0.70` |
| 5 | Bloqueio: `min(BlockChance, 0.50)`; bloqueou → `× (1 − block_mitigation)` | `block_cap = 0.50`, `block_mitigation = 1.0` (**provisório**) |
| 6 | Armadura, **só físico**: `redução = min(0.90, A / (A + k·D))`, `D' = D·(1 − redução)` | `armor_damage_factor k = 5`, `armor_max_reduction = 0.90` |
| 7 | Resistência por elemento: `clamp(res, −1.00, 0.75)`; `× (1 − res)` | `resist_cap = 0.75`, `resist_floor = −1.0` |
| 8 | `× DamageTaken` do defensor (Postura Firme etc.) | — |
| 9 | Barreira absorve primeiro; o resto sai da vida (mínimo 0) | — |
| depois | Efeitos ao acertar (queimadura, lentidão, quebra de guarda, recurso), só se `landed` | `trigger_icd_min = 0.25 s` |

**Fórmula de armadura.** A seção 10 do plano diz que a armadura "reduz menos os golpes grandes" mas a fórmula não veio no texto. Adotada `A/(A + 5·D)` (equivale a `D²/(D + A/5)` sem o teto). Exemplo com A = 500: golpe de 100 → 50% de redução; golpe de 1.000 → 9%. Teto de 90%. O Vision Lead e o balanceamento confirmam `k` em playtest; mudar `k` é só mudar o CSV.

**Consumo de RNG.** Sempre 3 números (crítico, evasão, bloqueio), mesmo quando a regra não se aplica. Ticks de DoT (`isDamageOverTime`) não rolam nada e pulam os passos 3–5.

---

## 12. Simulador de expedição (`expedition.h`)

- Encontro `i` usa `Pcg32::ForStream(seed, Combat|Loot|Events, i)`. O estado entre encontros fica em `ExpeditionProgress` (vida, poções, raros, tempo), explícito e copiável.
- Passo de **0,1 s** (`sim_step`). Se o bench passar de 2 s em 12 h, liga `sim_fast_enabled` (0,25 s em encontros sem chefe), como diz o plano.
- A cada passo: a política avalia até 6 `AiRule` em ordem; vale a primeira válida; senão, ataque básico. Inimigos atacam conforme `EnemyAttack` (peso, telegrafado). Golpes telegrafados são esquivados com chance `ai_base_dodge (0,5) + IdleProfile.dodgeTelegraphedBonus`.
- Um encontro que terminaria depois de `effectiveSeconds` não entra. Recuo: vida < `retreat_life_fraction` (20%, **provisório**) sem poção → `StopReason::Retreat`; o loot obtido fica.
- `FinalizeExpedition` aplica **uma vez**: Vigor (100/70/40% por faixa de 4 h, sobre XP e stacks; itens não), teto de XP (área + 2 níveis), agregação, dicas e `resultHash`.
- Regras de topo: `LootMode::Idle` nunca entrega Únicos, livros de especialização, pedras de rota nem Fragmentos de Eco (dupla checagem: `manualOnly` e o tipo da entrada); no máximo 4 Raros (o excedente vira Mágico).
- Habilidade, Sigilo ou Único sem `IdleProfile.supported` bloqueia o início (`StartCheck::IdleIncompatible`).
- `content_version` diferente entre início e coleta: simula com o conteúdo atual; ID removido → `StopReason::ContentMismatch` (encerra com o loot até ali). A coleta continua protegida contra duplicação pelo `status` + `collectedResultHash`.

---

## 13. Estratégia de testes

### 13.1 ShatterCore (CMake, sem UE, a cada commit)
Framework próprio `ShatterCore/tests/test_framework.h`: `TEST(nome)`, `EXPECT_EQ/NE/TRUE/FALSE/NEAR/ENUM_EQ`, `ASSERT_TRUE/EQ`, filtro por substring, `--list`, código de saída ≠ 0 em falha. `main` em `tests/main.cpp` com `SHATTER_TEST_MAIN()`.

| Suíte (arquivo) | Cobre |
|---|---|
| `test_rng.cpp` | Sequências conhecidas (valores fixos gravados), fluxos diferentes, `NextBelow` sem viés |
| `test_stats.cpp` | Fórmula, tags, cache/dirty, nunca negativo, ordem de inserção |
| `test_damage.cpp` | Cada passo isolado, tetos (70/50/75%), armadura com os exemplos da seção 11, 3 números de RNG por golpe |
| `test_effects.cpp` | Refresh, StackN, StrongestOnly, recarga interna 0,25 s, cadeia de gatilhos bloqueada |
| `test_content.cpp` | CSV de `tests/data/` e o CSV real (`SHATTER_CONTENT_DIR`) passam em `Finalize`; CSV quebrado falha com linha certa |
| `test_loot.cpp` | `PickWeighted` estatístico (100 mil sorteios por commit; 1 milhão no noturno), nada fora do tier, idle sem itens de topo, teto de Raros |
| `test_expedition.cpp` | **Determinismo**: 1 parte × 10 partes × partes de tamanho aleatório → `resultHash` igual; regras do idle; Vigor; teto de nível |
| `test_clock.cpp` | Relógio voltando, adiantado, teto de 12 h, Steam × local, descanso diário |
| `test_json.cpp`, `test_sha256.cpp` | Ida e volta, saída canônica, vetores do NIST |
| `test_save.cpp` | Ida e volta, checksum adulterado → backup, tmp→rename, migração de cada `tests/data/saves/save_vN.json` |
| `test_golden.cpp` | Expedições de referência com seeds fixas comparadas com `tests/data/golden/*.txt` (o mesmo arquivo é usado no UE) |

### 13.2 UE (Automation Tests, `Private/Tests/`)
- `EchoesOfTheShatter.Rules.LoadContent`: o `UShatterRulesSubsystem` carrega o CSV empacotado sem erro.
- `EchoesOfTheShatter.Rules.GoldenExpedition`: o core compilado pelo UBT gera o **mesmo `resultHash`** do golden do CMake (pega diferença de flags de ponto flutuante entre os dois builds).
- `EchoesOfTheShatter.Save.RoundTrip`: o `USaveSubsystem` grava e lê na pasta real.
- `EchoesOfTheShatter.Parity.*` (noturno): bot joga os encontros reais em modo headless (`-nullrhi`) com a mesma política e seeds; compara XP/min, abates/min, dano recebido e poções/encontro com o simulador; tolerância 10% (5% no AA).
- `EchoesOfTheShatter.Smoke`: carrega Refúgio e Cripta, 60 s de bot.

---

## 14. CI (GitHub Actions)

| Job | Runner | Quando | Passos |
|---|---|---|---|
| `core-linux` | `ubuntu-latest` (GCC e Clang) | todo push/PR | `cmake -DSHATTER_WERROR=ON` → build → `ctest`; variante com `SHATTER_SANITIZE=ON` |
| `core-windows` | `windows-latest` (MSVC) | todo push/PR | mesmo, com MSVC (o compilador do jogo) |
| `data` | `ubuntu-latest` | todo push/PR | `python3 tools/validate_data.py` + teste `test_content` sobre o CSV real |
| `bench` | `ubuntu-latest` | noturno | `SHATTER_BUILD_BENCH=ON`; falha se 12 h de expedição > 2 s |
| `ue-build` | **self-hosted Windows** com UE 5.8 instalado | todo push na `main` | `RunUAT BuildCookRun` (Development), Automation `EchoesOfTheShatter.Rules+Save` com `-nullrhi`, `GatherText` |
| `ue-nightly` | self-hosted | noturno | Paridade + Smoke + loot de 1 milhão |
| `steam-upload` | self-hosted | push na branch `release` | Shipping → `steamcmd` sobe para a branch **beta**; promover para default é manual no Steamworks |

O UE precisa de runner próprio (o motor é grande e a licença não permite imagem pública com ele). Versão visível no menu: `0.3.1-ea+<hash>` (injetada pelo CI em `DefaultGame.ini` → `ProjectVersion`).

---

## 15. Desvios do plano (Godot → UE5)

| Plano (seção 10) | Agora | Motivo / impacto |
|---|---|---|
| Godot 4, GDScript tipado | UE 5.8, C++ (core C++17 puro) + BP para apresentação | Decisão do dono |
| Regras como `RefCounted` puras | Biblioteca `ShatterCore` sem Unreal, compilada por CMake e por módulo UE | Mesmo princípio, fronteira mais forte (testa sem editor) |
| Renderer Compatibility (OpenGL) | Forward Shading, sem Lumen/Nanite/VSM, materiais Unlit+Masked | Equivalente leve; risco maior em GPU integrada → medir na F1 |
| Viewport 960×540, stretch viewport, nearest | `ScreenPercentage` + upscale nearest + `UShatterViewportClient` com escala inteira | Mesmo resultado visual |
| 2D com Area2D | Sprites Paper2D em planos 3D, câmera ortográfica −30°/45°, colisão 3D no plano | Ordenação e colisão nativas |
| InputMap | Enhanced Input + `UEnhancedInputUserSettings` | Mesmo conceito de ação nomeada |
| GodotSteam (GDExtension) | OnlineSubsystemSteam + Steamworks SDK direto | `getServerRealTime` → `ISteamUtils::GetServerRealTime` |
| `tr()` + CSV de tradução | String Tables + `.po` gerados de CSV por `tools/build_loc.py` | A planilha continua a mesma |
| Resources `.tres` + `tools/import_tables.gd` | CSV lido em tempo de execução pelo `ContentDB` (sem conversão); validação no CI por `Finalize()` + `validate_data.py`. DataTables do UE só se alguém quiser visualizar no editor | Uma única fonte da verdade, igual nos testes e no jogo |
| EventBus por sinais | `UShatterEventSubsystem` com delegates | — |
| `_physics_process` 60 Hz | Acumulador de passo fixo 60 Hz no `UShatterCombatSubsystem` | O tick do UE é variável |
| Hitstop por entidade | Timers congelados no passo fixo + `CustomTimeDilation` visual | — |
| WorkerThreadPool | `UE::Tasks::Launch` | — |
| GUT | Mini framework próprio (CMake) + UE Automation Tests | Sem downloads |
| `use_custom_user_dir` → `%APPDATA%/EchoesOfTheShatter` | `%LOCALAPPDATA%\EchoesOfTheShatter\Saved\SaveGames` (padrão do UE) | Auto-Cloud aponta para `WinAppDataLocal` |
| `Time.get_unix_time_from_system()` | `FDateTime::UtcNow().ToUnixTimestamp()` | — |
| Sentry SDK para Godot | `sentry-unreal` (opt-in) ou CrashReportClient com endpoint próprio — decidir na F3 | — |
| `tools/batch_sim.gd` | Executável `shattercore_bench` / modo lote no `bench/` (CSV de saída) | Roda sem o UE |
| Tamanho < 500 MB | Mantido como meta; exige desligar plugins não usados e compressão de pak | UE base é maior que Godot: medir na F1 |

### Regras que o plano não fechava (decididas aqui, provisórias e em dados)
1. **Fórmula da armadura**: `A/(A + 5·D)`, teto 90% (seção 11).
2. **Bloqueio** anula o golpe inteiro (`block_mitigation = 1.0`).
3. **Recuo no idle**: vida < 20% sem poção (`retreat_life_fraction`).
4. **Vigor** afeta XP, Ouro e materiais, não a chance de item.
5. **Sem ponto flutuante transcendental** no golpe e no simulador (determinismo entre compiladores).

Todas ficam em `rules.csv` e podem mudar sem tocar no código.

---

## 16. Mapa dos headers (`ShatterCore/include/shatter/`)

| Header | Conteúdo | Implementação (`src/`) |
|---|---|---|
| `types.h` | `ContentId`, `IsValidContentId`, `Tag` (bitmask), `DamageType`, `Rarity`, `Seconds`, `UnixSeconds` | `types.cpp` (parse/ToString) |
| `rng.h` | `RngStream`, `SplitMix64Next`, `Mix64`, `DeriveSeed`, `Pcg32` | **inline completo** |
| `constants.h` | `RulesConstants` (valores do plano + chave do CSV) | — |
| `stats.h` | `StatId`, `ModKind`, `Modifier`, `ComputeStatValue`, `StatBlock` | `stats.cpp` |
| `damage.h` | `HitInput`, `HitResult`, `ResolveHit`, `ArmorReduction`, `ClampResistance` | `damage.cpp` |
| `effects.h` | `StackRule`, `TriggerKind`, `EffectData`, `ActiveEffect`, `EffectContainer`, `EffectiveCooldown` | `effects.cpp` |
| `item.h` | `ItemSlot`, `RolledAffix`, `ItemInstance`, `StackEntry` | `types.cpp` ou `item.cpp` |
| `content.h` | `ClassData`, `SkillData` + `IdleProfile`, `EnemyData`, `AffixData`, `ItemBaseData`, `UniqueData`, `LootTableData`, `EncounterTemplate`, `MapData`, `ContentDB` | `content.cpp`, `csv.cpp` |
| `character.h` | `CharacterState`, `CharacterSnapshot`, `BuildStatBlock`, `IsIdleCompatible` | `character.cpp` |
| `loot.h` | `LootContext`, `LootDrop`, `RollLootTable`, `RollAffixes`, `PickWeighted`, `ItemModifiers` | `loot.cpp` |
| `expedition.h` | `AiRule`, `ExpeditionRequest`, `EncounterReceipt`, `ExpeditionProgress`, `ExpeditionResult`, `CanStartExpedition`, `SimulateExpedition`, `SimulateRange`, `FinalizeExpedition`, `ForecastExpedition` | `expedition.cpp` |
| `clock.h` | `ResolveNow`, `ComputeExpeditionWindow`, `ApplyDailyRest`, `NextLastSeen` | **inline completo** |
| `json.h` | `json::Value`, `Parse`, `Serialize` | `json.cpp` |
| `sha256.h` | `Sha256` | `sha256.cpp` |
| `save.h` | `SaveData`, `SavedExpedition`, `SerializeJson`, `ParseJson`, `Migrate`, `IFileIO`, `WriteSaveFile`, `ReadSaveFile`, `CollectExpedition` | `save.cpp`, `save_migrations.cpp`, `file_io.cpp` |
| `shatter.h` | Inclui tudo | — |

Verificação: todo header compila sozinho com `g++ -std=c++17 -fsyntax-only -Wall -Wextra -Wpedantic -Wshadow -Wconversion` e com `clang++` (o CMake tem o alvo `shattercore_header_check`, que faz isso em todo build).
