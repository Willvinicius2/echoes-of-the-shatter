# 04 — Arquitetura e contratos técnicos (Tech Lead)

Projeto: **Echoes of the Shatter**. Fonte de design: `docs/00_plano_existente.md` (Plano Steam v2.0). Motor: **Unreal Engine 5.8** (decisão do dono em 15/10/2026, versão em 16/10/2026), substituindo o Godot 4 da seção 10 do plano.

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
| Motor | **UE 5.8** (decisão do dono em 16/10/2026), último hotfix disponível na F1, fixado até o Acesso Antecipado. Upgrade só entre fases, com todos os testes passando | Igual ao plano: atualizar o motor no meio quebra coisas. Conferir na instalação do 5.8 o Enhanced Input, `UEnhancedInputUserSettings` (remapeamento), o Niagara e o IKRig (**confirmar no 5.8**) |
| Linguagem | C++ para regras e sistemas; Blueprint só para montagem de assets, animação de UI e ajustes visuais | Regras testáveis fora do editor; BP não pode divergir do motor |
| Padrão C++ | ShatterCore em **C++17**, que também precisa compilar como **C++20** (o UE 5.8 compila módulos em C++20) | Contrato do pedido e compatibilidade com UBT |
| Módulos UE | `ShatterCore` (wrapper que compila a biblioteca pura) e `EchoesOfTheShatter` (jogo). Ver seção 9 | Fronteira física: o módulo de regras não depende de `Engine` |
| Plugins ativos | `EnhancedInput`, `Niagara`, `OnlineSubsystem`, `OnlineSubsystemSteam`, `OnlineSubsystemUtils` (+ `IKRig` só no editor, para retargeting; **confirmar no 5.8**) | Só o necessário; desligar plugins padrão não usados (Chaos Vehicles, Water, etc.) para reduzir o build (meta < 500 MB). Nenhum plugin 2D (a apresentação é 3D, ver `docs/08_decisoes_visual_3d.md` e a tabela de desvios) |
| Plugins **não** adotados | CommonUI, GAS, Motion Matching, plugins de animação de terceiros | Animação: ~8 clipes por classe, dirigida pelo combate em C++ com Animation Blueprint simples (seção 3.3). GAS: duplicaria o motor de regras (atributos e efeitos já estão no ShatterCore) |
| Renderização | Malhas 3D low/mid poly com textura pintada à mão (luz e sombra no albedo), câmera em perspectiva de FOV estreito, pitch −55° e yaw 45° (seção 3) | Decisão do orquestrador (`docs/08_decisoes_visual_3d.md`). Colisão, consultas de forma e navegação continuam no 3D, no plano XY |
| Pipeline gráfico | Forward Shading + **MSAA**, sem Lumen, sem Nanite, sem Virtual Shadow Maps, sem lightmaps; CSM curto só para personagens; 4 materiais mestres (seção 3.5); VFX em Niagara; UI em UMG com curva de DPI padrão | Alvo de PC de entrada e Steam Deck (RNF-04, orçamentos na seção 18); o estilo pintado pede bordas limpas (MSAA) e não precisa de iluminação global |
| Entrada | **Enhanced Input**: `UInputAction` por ação nomeada, `IMC_Default`, remapeamento por `UEnhancedInputUserSettings` | Equivalente ao InputMap do plano; controle no 1.0 = só um novo Mapping Context |
| Localização | **String Tables** geradas de CSV + `.po` por cultura (seção 7) | Nenhum texto no código; mesma planilha `chave, pt_BR, en, es` do plano |
| Save | **JSON próprio** no ShatterCore (`save.h`), não `USaveGame` | Ver justificativa na seção 8 |
| Steam | `OnlineSubsystemSteam` (conquistas, overlay, presença) + chamadas diretas ao **Steamworks SDK** do UE (`ISteamUtils::GetServerRealTime`) atrás de `UShatterPlatformSubsystem` | O OSS não expõe a hora do servidor; o wrapper permite builds sem Steam (dev, CI) |
| Versionamento | Git + GitHub, **Git LFS** para `*.uasset *.umap *.png *.tga *.psd *.blend *.fbx *.wav *.ogg *.ttf` | Igual ao plano; `art-src/` (fontes de arte) também no LFS |
| Plataforma | Windows x64 (D3D12, SM5; fallback D3D11). Steam Deck via Proton (mesmo binário) | Igual ao plano; um binário só = mesmo resultado de simulação no Deck |

---

## 3. Renderização 3D estilizada (câmera 3/4, forward + MSAA)

Fonte das decisões: `docs/08_decisoes_visual_3d.md` (fechadas, não reabertas aqui). Esta seção só fixa números e mecanismos. Paleta, densidade de texel, cores-assinatura de área e estilo da UI vêm de `docs/03_design_system.md` e `docs/03_design_tokens.json`; aqui não são definidos. Itens marcados **confirmar no 5.8** dependem de checagem na instalação do motor antes de virarem contrato.

**Princípio:** a renderização só desenha. Nenhuma regra, tempo de fase ou número de balanceamento mora na apresentação; animação, VFX e hitstop seguem os eventos e as fases do `UShatterCombatSubsystem`/`UShatterSkillComponent` (seção 6.2), nunca o contrário.

### 3.1 Escala do mundo e eixos

| Item | Valor |
|---|---|
| Unidade | 1 uu = 1 cm; 1 m no Blender = 100 uu |
| Herói (proporções: `docs/03_design_system.md`) | altura **150 uu**; cápsula de gameplay raio **30 uu**, meia-altura **75 uu** |
| Módulo de chão | grade de **100 uu**; peças de 200 e 400 uu (múltiplos da grade) |
| Eixos | Gameplay no plano XY, Z para cima; o personagem "olha" para +X; pivô nos pés |
| Plano de mira e movimento | Plano Z fixo por sala; a mira do mouse é a interseção raio × plano (`AShatterPlayerController::GetAimPointOnPlane`), sem trace contra a malha |

### 3.2 Câmera

Montagem no `AShatterCharacter`: `UShatterFollowCameraComponent` (subclasse de `USpringArmComponent`, configurada pelo `UShatterRenderSettings`) com um `UCameraComponent` filho. Projeção em perspectiva de FOV estreito (pseudo-isométrica). Valores em `Config/DefaultGame.ini`, seção `[/Script/EchoesOfTheShatter.ShatterRenderSettings]` (apresentação, fora do CSV de balanceamento).

| Parâmetro | Valor | Observação |
|---|---|---|
| Pitch | **−55°** | Meio da faixa decidida (−50° a −60°) |
| Yaw | **45°** fixo | Rotação absoluta (`SetUsingAbsoluteRotation`), `bUsePawnControlRotation = false`, sem rotação pelo jogador |
| FOV | **25° horizontal a 16:9** (≈ 14,2° vertical) | Estreito o bastante para quase não deformar; largo o bastante para o chão ter profundidade. Eixo mantido: `AspectRatio_MaintainYFOV`, para 16:9 e 16:10 (Deck) mostrarem a mesma altura (**confirmar no 5.8** que o valor de FOV vira vertical nesse modo e ajustar o número) |
| Distância (braço) | **4200 uu** | Mostra ~1860 × 1046 uu perpendiculares à câmera, ~6,4 módulos de 200 uu de profundidade no chão; o herói (150 uu) ocupa ~14% da altura da tela (~155 px em 1080p). **Distância mantida em 4200 uu** (não ajustada): é legível; se a F1 mostrar o herói pequeno demais, reduzir para 3800 dentro da faixa de zoom |
| Zoom | Padrão 4200; faixa permitida **3600 a 5000** (passo 200) | No Acesso Antecipado o jogador **não** tem zoom; a faixa é usada só pelo `UShatterAreaProfile` (arenas de chefe podem afastar até +15%) |
| Alvo | Deslocamento de alvo (0, 0, 52) uu | Enquadra o tronco (~35% da altura do herói), não os pés |
| Suavização | `bEnableCameraLag = true`, `CameraLagSpeed = 7`, `CameraLagMaxDistance = 200 uu`, `bUseCameraLagSubstepping = true`; **sem** lag de rotação | A câmera nunca perde o herói na esquiva |
| Colisão da câmera | `bDoCollisionTest = false` | Paredes que cobrem o herói são tratadas por fade (3.7), não por colisão |
| Planos de corte | Near 100 uu, far 15000 uu | Sem profundidade relevante fora disso |
| Tremor | `UCameraShakeBase` aditivo, máx. 8 uu, opção de desligar | Só em chefes e impactos grandes |

### 3.3 Malhas e animação

- **Personagens:** `USkeletalMeshComponent` (o `Mesh` do `ACharacter`), sem colisão no mesh (`NoCollision`); o gameplay usa só a cápsula e as consultas de overlap no plano (seção 6.2). Sem ragdoll: morte é animação.
- **Esqueleto:** um esqueleto humanoide chibi **compartilhado** pelas três classes (`SKEL_Humanoid_Chibi`), para as 2 animações de habilidade reaproveitáveis (golpe e conjuração) servirem a todas. Cada família de inimigo tem esqueleto próprio. Retargeting entre esqueletos fica no editor (IK Retargeter; **confirmar no 5.8** o plugin IKRig habilitado por padrão). Sockets padrão: `socket_weapon_r`, `socket_weapon_l`, `socket_cast`, `socket_head`, `socket_fx_ground`.
- **Animation Blueprint (decidido):** um `ABP_Hero` por classe herdando de `UShatterAnimInstance` (C++) e um `ABP_Enemy_Base` simples para inimigos. O C++ expõe só variáveis de leitura (`Speed`, `bIsDead`, `bIsStaggered`, `bInHitstop`); o ABP tem uma máquina de estados de locomoção (Parado ↔ Andar, esquiva como montagem) e **slots** `FullBody` e `Additive` para montagens. Alternativa descartada: tocar `UAnimSequence` direto por C++ sem ABP (menos peças, mas sem mistura de entrada/saída e sem slot aditivo para o tomar dano). Sem Motion Matching nem plugins de animação de terceiros (dependência externa por versão de motor, ou pesado demais para um conjunto de 8 animações).
- **Montagens por habilidade:** `AM_<Dono>_<Acao>` com 3 seções nomeadas `Windup`, `Impact`, `Recovery`, alinhadas às fases do `SkillData`. Ao mudar de fase, o `UShatterSkillComponent` chama `Montage_JumpToSection` e ajusta a taxa: `taxa = duração_autoral_da_seção / duração_da_fase_no_CSV`. Assim a animação **se adapta** aos tempos do CSV e o Game Designer rebalanceia sem reanimar. Root motion desligado: esquiva e avanço movem a cápsula pelo comportamento da habilidade.
- **Mapeamento habilidade → montagem + VFX:** `UShatterSkillPresentationSet` (`UPrimaryDataAsset`, um por classe/família), chave = ID de conteúdo da habilidade (`skill.warrior.iron_cut`) → montagem, sistema Niagara, socket, som. É dado de apresentação (arte), não de balanceamento; habilidade sem entrada cai em `AM_Generic_Strike` ou `AM_Generic_Cast` pela forma (`SkillShape`) e é registrada no log.
- **AnimNotify:** servem só para VFX, som e passos (`UShatterAnimNotify_Fx`, `_Footstep`). **Nunca** causam dano nem avançam estado de regra: o impacto é a fase `impact` do passo fixo.
- **Conjunto mínimo por classe** (do plano): `AS_Idle`, `AS_Walk`, `AS_Dodge`, `AS_BasicAttack`, `AS_Skill_Strike`, `AS_Skill_Cast`, `AS_Hit`, `AS_Death`. Inimigos: `AS_Idle`, `AS_Walk`, `AS_Attack` (+ telegraph como seção do ataque), `AS_Hit` opcional, `AS_Death`; chefes acrescentam um `AS_` por padrão de ataque.
- **Hitstop por entidade (apresentação):** quando o core congela os timers da entidade, o `UShatterPresentationComponent` define `Mesh->GlobalAnimRateScale = 0` (e restaura ao fim) e aplica `CustomTimeDilation` baixo no ator. Os sistemas Niagara presos à entidade são pausados pelo mesmo componente; o VFX do impacto **não** pausa. **Confirmar no 5.8** se `CustomTimeDilation` do ator alcança componentes Niagara anexados; senão, pausar cada `UNiagaraComponent` explicitamente. Nunca congela o jogo todo.
- **Reações visuais:** flash de dano por parâmetro de material `HitFlash` (MID criado uma vez por mesh e reutilizado), dissolução da morte por `Dissolve` (dithered, sem translucidez), tomar dano na slot `Additive`.
- **Custo de animação:** `bEnableUpdateRateOptimizations` nos inimigos; ABP sem nós caros (sem IK, sem física). **Confirmar no 5.8** o Animation Budget Allocator se o orçamento da seção 18 estourar na game thread.

### 3.4 Pipeline gráfico

Forward Shading com **MSAA**, sem Lumen, sem Nanite, sem Virtual Shadow Maps, sem Distance Fields, sem iluminação estática (`r.AllowStaticLighting=0`: nenhum lightmap é gerado, toda a luz de cenário está pintada no albedo, como decidido).

| Config (`DefaultEngine.ini`) | Valor |
|---|---|
| `r.ForwardShading` | `1` (exige reiniciar o editor) |
| `r.AntiAliasingMethod` / `r.DefaultFeature.AntiAliasing` | `3` (MSAA); sem TAA/TSR |
| `r.MSAACount` | **4** no PC de entrada; **2** no Steam Deck (opção de vídeo: Off/2x/4x) |
| `r.DynamicGlobalIlluminationMethod`, `r.ReflectionMethod` | `0` (nenhum) |
| `r.Shadow.Virtual.Enable` | `0` |
| Nanite, Lumen, Substrate | Desligados nas Project Settings. **Confirmar no 5.8** o padrão do Substrate e se é compatível com Forward + MSAA; se for padrão, desligar explicitamente |
| `r.DefaultFeature.AutoExposure`, `MotionBlur`, `AmbientOcclusion`, `LensFlare` | `0`; bloom só em efeito pontual definido pela direção de arte |
| `r.PSOPrecaching` | Ligado (evita engasgo de shader na primeira cena; **confirmar no 5.8** o nome do cvar e o fluxo de cook do PSO cache) |
| RHI | D3D12 (D3D11 de fallback no Windows); Steam Deck via Proton com o mesmo binário. **Confirmar no 5.8** o shader model padrão (SM5 × SM6) e que o alvo escolhido roda no Proton |

Iluminação por cena: 1 `DirectionalLight` (cor, intensidade e rotação vêm do `UShatterAreaProfile`), 1 `SkyLight` de ambiente fraco (captura estática), e no máximo 4 luzes pontuais dinâmicas **sem sombra** (tochas e cristais perto do herói; o brilho de longe é emissivo no material). Como a cena é pintada, a luz dinâmica só modula e dá sombra aos personagens, não define o visual.

### 3.5 Materiais mestres

Quatro mestres, todos parametrizados; ativos reais são `MI_` (instâncias). Switches estáticos limitados (máx. 16 permutações por mestre) para conter o tempo de shader e o cook. Instruções de base pass visadas: personagem ≤ 150, cenário ≤ 100, VFX ≤ 80 (medir em Shader Complexity; os números são metas iniciais).

| Mestre | Domínio / blend | Entradas principais |
|---|---|---|
| `M_Master_Character` | Surface, Opaque (+ dissolução por dither, sem translucidez), Lit com roughness fixo alto e specular 0 | `T_*_BC` (albedo pintado), `T_*_M` (máscara: R = emissivo, G = rim, B = região de tinta para variantes/skins, A reservado), cor/potência/intensidade do rim (fresnel), `HitFlash`, `Dissolve`, `DitherFade` |
| `M_Master_Environment` | Surface, Opaque ou Masked (switch) | Albedo pintado, máscara de emissivo, `DitherFade` por oclusão (3.7), parâmetro de tremulação para chamas/cristais, cor de vértice opcional (AO pintada) |
| `M_Master_VFX` | Switches: Additive, Translucent, Masked/Opaque "quente", Telegraph | Textura de forma/ruído, núcleo claro (emissivo > 1) + borda colorida, profundidade suave opcional, parâmetros de partícula via Niagara |
| `M_Master_UI` | User Interface | Moldura/preenchimento "lava" animado; sem dependência de cena |

`MPC_Global` (Material Parameter Collection) leva: posição do herói (fade de paredes), tempo de tremulação e cor de fog de borda. Texturas: mipmaps ligados, filtro padrão (trilinear/anisotrópico do grupo de textura do projeto), sRGB para `_BC`, linear para `_M`. Densidade de texel: ver `docs/03_design_system.md`; limites de tamanho na seção 17.

### 3.6 Sombras

**Decisão:** CSM curto da luz direcional, **só os personagens projetam**; o cenário não projeta sombra dinâmica (já está pintada) e só recebe. Motivo: o custo de sombra fica limitado a ~31 malhas de 3,5 a 10 mil triângulos, em vez de todo o cenário; a sombra do herói no chão é o que ancora o personagem na câmera 3/4.

- `Dynamic Shadow Distance` 2500 uu, **2 cascatas**, resolução máxima 1024 (`r.Shadow.MaxResolution`), `r.Shadow.CSM.MaxCascades=2`. Props altos que precisem de sombra projetada ativam `CastShadow` por exceção, no checklist da seção 17.
- **Plano B (escalabilidade "Baixo", Steam Deck se faltar GPU):** sombra falsa em blob (quad escuro suave sob os pés, material do mestre VFX) e CSM desligado. Chave de qualidade: `sg.ShadowQuality`.
- Sem sombra de contato nem Distance Field Shadows (fora do escopo; reavaliar só se a medição pedir).

### 3.7 Oclusão da câmera

Paredes entre a câmera e o herói não podem esconder o combate. **Decisão:** fade com dither (`DitherFade` no `M_Master_Environment`) dirigido pelo `MPC_Global` (posição do herói): peças marcadas com a tag de componente `OccluderFade` desaparecem num cone de ~300 uu de raio na linha câmera-herói. Sem colisão de câmera. Silhueta do herói atrás de objetos: Custom Depth/Stencil + 1 passe de pós-processo simples **(confirmar no 5.8 que o passe funciona em Forward + MSAA; senão, material de silhueta no próprio mestre)**. Contorno geral (outline) **não** é adotado: o estilo pintado já traz a borda no albedo; contorno extra só em chefes/elites se o Art Director pedir, por casco invertido (segundo slot de material), pago apenas nesses meshes.

### 3.8 Névoa por área

`UShatterAreaProfile` (`UDataAsset`, um por área: `DA_Area_<Area>`) guarda cor-assinatura (valores do `docs/03_design_system.md`), densidade, queda de altura e início da `ExponentialHeightFog`, além de cor, intensidade e rotação da luz direcional, intensidade do skylight, distância de zoom permitida e música. O `AShatterAreaVisuals` (um por mapa) aplica o perfil no `BeginPlay` e interpola ao cruzar portais de área. O perfil é dado de apresentação (fora do CSV de balanceamento); a ligação área → perfil é por ID de conteúdo da área.

### 3.9 VFX (Niagara)

- Plugin **Niagara**. Sistemas `NS_<Dono>_<Efeito>`; emissores de CPU por padrão (baixa contagem de partículas); GPU só para emissores acima de ~500 partículas (poucos). Todos disparados por eventos do `UShatterEventSubsystem` ou por `AnimNotify` (visual), com **pool de componentes** (`ENCPoolMethod::AutoRelease` na criação do sistema, sem destruir/criar por golpe; **confirmar no 5.8** a API do pool).
- **Linguagem visual (decisão 5):** efeitos do jogador finos e translúcidos, com núcleo claro (emissivo acima de 1) e borda na cor da classe; ameaças inimigas opacas e quentes (laranja/vermelho), legíveis sobre qualquer fundo.
- Todo VFX respeita o orçamento da seção 18 e a ordem de desenho de 3.10. O número de partículas e a duração de cada efeito não podem mudar a regra: o efeito acaba quando a apresentação acaba, a regra já terminou.

### 3.10 Telegraphs e ordem de desenho

**Telegraph de inimigo** (aviso no chão antes do golpe): `AShatterTelegraphActor` em pool (`UShatterPoolSubsystem`), um mesh plano (quad ou ribbon) a **+2 uu** do chão, material do mestre VFX na variante Telegraph: **Masked** (borda definida por SDF analítica no material, `progress` 0→1 pelo tempo de windup do `EnemyAttack`), cor quente opaca, escrevendo profundidade. Forma por parâmetro (cone, círculo, linha, anel), dimensões vindas do `SkillData`/`EnemyAttack` (alcance e ângulo reais da consulta, para o aviso não mentir). Bordas suaves por alpha-to-coverage com MSAA **(confirmar no 5.8)**. Decals não são usados (o suporte em Forward + MSAA é restrito; o mesh plano é mais previsível).

Ordem de desenho, de trás para frente:

| # | Camada | Mecanismo |
|---|---|---|
| 1 | Cenário (chão, paredes, props) | Opaque/Masked, profundidade real |
| 2 | Telegraphs de inimigo | Masked, +2 uu, escreve profundidade (personagens à frente os ocultam corretamente) |
| 3 | Personagens (heróis, inimigos) | Opaque |
| 4 | VFX quente de inimigo (projéteis, impactos) | Masked/Opaque, escreve profundidade |
| 5 | VFX do jogador | Translucent/Additive, `TranslucencySortPriority` 10 |
| 6 | Pós-processo (silhueta, se existir) e fog | Fog na ordem do motor |
| 7 | Números de dano e UMG | Camada de UI por cima de tudo |

Nenhum VFX translucente do jogador esconde um telegraph inimigo: a prioridade de ordenação do jogador só afeta translucentes, e o telegraph não é translucente.

### 3.11 Interface (UMG)

UMG na resolução **nativa**, sem camada de escala própria. Escala de DPI pela curva padrão do motor: Project Settings → Engine → User Interface → DPI Scaling, regra "Shortest Side", curva padrão (referência de projeto 1080p = 1,0; **confirmar no 5.8** os pontos da curva padrão e usá-los sem alteração). Layout por âncoras, testado em 16:9 (1080p, 1440p, 4K) e 16:10 (Deck, 1280×800). Estilo (pedra escura, molduras orgânicas, preenchimento "lava"), fonte e acentos: `docs/03_design_system.md`. Números de dano: camada `UShatterDamageNumberLayer` (`UUserWidget`) com widgets em pool posicionados por `ProjectWorldLocationToScreen`; sem `UWidgetComponent` por inimigo (custo alto com 30 inimigos). Barras de vida de inimigos: mesma camada.

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
│  │     │  Skills/ Expedition/ Save/ Platform/ Render/ Animation/ Presentation/ Input/ UI/
│  │     └─ Private/Tests/          Automation Tests (EchoesOfTheShatter.*)
│  ├─ Content/
│  │  ├─ Data/*.csv                 balanceamento e conteúdo (fonte da verdade, empacotado como arquivo solto)
│  │  ├─ Data/schemas/              esquemas das tabelas (Data Engineer)
│  │  ├─ Localization/              String Tables e .po gerados
│  │  ├─ Characters/ Enemies/ Bosses/ Environments/ VFX/ UI/ Materials/ Blueprints/ Maps/ Audio/ Input/   (convenção na seção 17.1)
│  └─ Plugins/                      vazio no AA
├─ art-src/                         fontes de arte (.blend, pinturas, presets de exportação), Git LFS, fora do projeto UE
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
  → apresentação reage aos eventos: número de dano, flash de dano, hitstop, som, VFX Niagara
```
- Lógica de combate em **passo fixo de 1/60 s** com acumulador no `UShatterCombatSubsystem` (`UTickableWorldSubsystem`), independente do FPS (equivale ao `_physics_process` do plano).
- Hitstop por entidade: a entidade em hitstop não avança timers no passo fixo; o visual congela a animação da entidade (`GlobalAnimRateScale` do mesh, seção 3.3). Nunca congela o jogo todo.
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
| `UShatterPoolSubsystem` | `UWorldSubsystem` | Pools de projéteis, telegraphs, números de dano, componentes Niagara e itens no chão (limite de 300 projéteis) |
| `AShatterCharacter` | `ACharacter` | Personagem jogável: `USkeletalMeshComponent` (herdado), `UShatterFollowCameraComponent` + `UCameraComponent`, `UShatterAttributeComponent`, `UShatterSkillComponent`, `UShatterPresentationComponent` |
| `AShatterEnemy` | `ACharacter` | Inimigo: mesmos componentes + `UShatterEnemyBrainComponent` |
| `AShatterPlayerController` | `APlayerController` | Enhanced Input (`IMC_Default`, ações `IA_Move`, `IA_Aim`, `IA_BasicAttack`, `IA_Skill1..5`, `IA_Dodge`, `IA_Potion1..2`, `IA_Inventory`, `IA_PassiveTree`, `IA_Map`) |
| `UShatterAttributeComponent` | `UActorComponent` | Espelha o `shatter::StatBlock` + `EffectContainer` + vida/recurso/barreira atuais; relê quando `StatBlock::Revision()` muda; delegates `OnLifeChanged`, `OnDeath` |
| `UShatterSkillComponent` | `UActorComponent` | Barra de 6 habilidades, fases windup/impact/recovery, recargas (`EffectiveCooldown`), custo de recurso |
| `UShatterSkillBehavior` (+ `Cone`, `Projectile`, `Area`, `Dash`, `Self`, `Channel`, `Trap`) | `UObject` | Forma espacial escolhida por `SkillShape`; só faz consultas de overlap e entrega alvos |
| `UShatterEnemyBrainComponent` | `UActorComponent` | Máquina de estados parado → perseguir → telegraph → atacar → recuperar; chefes com tabela de padrões por fase |
| `UShatterPresentationComponent` | `UActorComponent` | Reage aos eventos do core: flash (`HitFlash`), hitstop por entidade (`GlobalAnimRateScale`), morte (`Dissolve`), toca montagens e Niagara via `UShatterSkillPresentationSet`; nunca decide regra |
| `UShatterAnimInstance` | `UAnimInstance` | Base C++ dos `ABP_*`: expõe `Speed`, `bIsDead`, `bIsStaggered`, `bInHitstop`; slots `FullBody`/`Additive`; ajuste de taxa por fase da montagem |
| `UShatterSkillPresentationSet` | `UPrimaryDataAsset` | ID de habilidade → montagem, Niagara, socket, som (dado de apresentação) |
| `UShatterAreaProfile` + `AShatterAreaVisuals` | `UDataAsset` + `AActor` | Fog, luz, skylight e zoom por área; aplicado ao carregar o mapa |
| `UShatterOcclusionFadeComponent` | `UActorComponent` | Atualiza o `MPC_Global` com a posição do herói para o fade de paredes |
| `AShatterTelegraphActor` | `AActor` | Mesh plano de telegraph no chão, em pool, parametrizado por forma e progresso |
| `UShatterDamageNumberLayer` | `UUserWidget` | Números de dano e barras de vida de inimigos, widgets em pool |
| `UShatterRenderSettings` | `UDeveloperSettings` | Câmera, MSAA e opções de apresentação (`DefaultGame.ini`) |
| `AShatterProjectile` | `AActor` | Projétil em pool |
| `UShatterFollowCameraComponent` | `USpringArmComponent` | Câmera 3/4 fixa (pitch −55°, yaw 45°, braço 4200 uu, lag 7), sem rotação do jogador |
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
| Renderer Compatibility (OpenGL) | Forward Shading + MSAA, sem Lumen/Nanite/VSM, sem lightmaps, materiais Lit simples com luz pintada no albedo | Equivalente leve; risco em GPU integrada e Deck → medir na F1 (seção 18) |
| Viewport 960×540, stretch viewport, nearest | Renderização na resolução nativa com MSAA; UMG com curva de DPI padrão do UE. A resolução interna fixa, o filtro nearest e a escala inteira saem junto com o pixel art (`docs/08_decisoes_visual_3d.md`, decisão 1) | Troca de visual 2D para 3D; o `UShatterViewportClient` deixa de existir |
| Tabela de plugins: Paper2D e PaperZD fora; Niagara dentro | Paper2D (e PaperZD, já descartado) removidos do `.uproject` e do `Build.cs`; Niagara adicionado | Sem sprites; VFX em Niagara |
| 2D com Area2D | Pawns 3D (Skeletal Mesh) com cápsula, câmera em perspectiva estreita −55°/45°, colisão e consultas de overlap no plano XY; antes do 3D o plano previa sprites Paper2D e câmera ortográfica −30°/45° | Ordenação, colisão e navegação nativas; troca de apresentação, regras intactas |
| InputMap | Enhanced Input + `UEnhancedInputUserSettings` | Mesmo conceito de ação nomeada |
| GodotSteam (GDExtension) | OnlineSubsystemSteam + Steamworks SDK direto | `getServerRealTime` → `ISteamUtils::GetServerRealTime` |
| `tr()` + CSV de tradução | String Tables + `.po` gerados de CSV por `tools/build_loc.py` | A planilha continua a mesma |
| Resources `.tres` + `tools/import_tables.gd` | CSV lido em tempo de execução pelo `ContentDB` (sem conversão); validação no CI por `Finalize()` + `validate_data.py`. DataTables do UE só se alguém quiser visualizar no editor | Uma única fonte da verdade, igual nos testes e no jogo |
| EventBus por sinais | `UShatterEventSubsystem` com delegates | — |
| `_physics_process` 60 Hz | Acumulador de passo fixo 60 Hz no `UShatterCombatSubsystem` | O tick do UE é variável |
| Hitstop por entidade | Timers congelados no passo fixo + animação congelada por entidade (`GlobalAnimRateScale`, seção 3.3) | — |
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

---

## 17. Convenções de Content e pipeline de assets 3D

### 17.1 Pastas e nomes (`EchoesOfTheShatter/Content/`)

```
Content/
├─ Characters/Heroes/<Classe>/        SK_, ABP_, AS_, AM_, MI_, T_  (Warrior, Archer, Mage)
├─ Characters/Shared/                 SKEL_Humanoid_Chibi, AS_/AM_ genéricos (golpe, conjuração), ABP_ base
├─ Enemies/<Familia>/                 SK_, SKEL_, ABP_, AS_, AM_, MI_, T_  (uma pasta por inimigo ou família)
├─ Bosses/<Chefe>/                    idem, mais padrões de ataque
├─ Environments/<Area>/               SM_, MI_, T_, DA_Area_<Area>; um kit modular por área (Refugio, Cripta, ...)
├─ Environments/Shared/               props reutilizáveis entre áreas
├─ VFX/<Dono>/                        NS_, MI_, T_ (Warrior, Archer, Mage, Enemies, World)
├─ UI/                                WBP_, T_UI_, fontes, estilos; ícones em UI/Icons
├─ Materials/Masters/                 M_Master_Character, _Environment, _VFX, _UI, MPC_Global
├─ Materials/Functions/               MF_ (funções compartilhadas: rim, dither, flash)
├─ Blueprints/                        BP_ (GameMode, atores de gameplay); Blueprints/Presentation/ (SkillPresentationSet)
├─ Maps/                              L_<Area> (um mapa por área); Maps/Test/ para mapas de teste
├─ Input/  Audio/  Localization/  Data/  Data/schemas/
```

A pasta `Art/` do esqueleto antigo deixa de existir. Pastas por **área** (`<Area>` = ID de conteúdo da área sem prefixo, em PascalCase ASCII: `Refugio`, `Cripta`) e por **dono** facilitam o cook por área e o trabalho em paralelo sem conflito de `.uasset`.

Prefixos (estilo Epic): `SK_` skeletal mesh, `SKEL_` skeleton, `PHYS_` physics asset (só se usado), `SM_` static mesh, `ABP_` animation blueprint, `AS_` animation sequence, `AM_` montage, `BS_` blend space, `M_` material, `MI_` instância, `MF_` função, `MPC_` coleção de parâmetros, `T_<Nome>_BC` albedo, `_M` máscara empacotada, sem normal map no projeto, `NS_` Niagara system, `NE_` emissor, `WBP_` widget, `DA_` data asset, `L_` mapa. Nome = `Prefixo_Dono_Descricao_Variante` (ex.: `SM_Cripta_Pillar_A`, `T_Warrior_BC`, `AM_Warrior_IronCut`). Pastas e assets em inglês/ASCII sem espaços; IDs de conteúdo (`skill.warrior.iron_cut`) vivem nos CSV e nos data assets, nunca no nome do arquivo.

### 17.2 Pipeline de importação (Blender → UE)

| Passo | Regra |
|---|---|
| Fontes | `art-src/` na raiz do repositório (`.blend`, pinturas, exportadores), no Git LFS, **fora** do projeto UE. O que entra no `Content/` é só o exportado |
| Formato | **FBX** como padrão (Skeletal Mesh, Static Mesh, animações). glTF só se a importação via Interchange no 5.8 se mostrar equivalente em esqueleto/animação (**confirmar no 5.8**); até lá, nenhum asset em glTF |
| Escala | Blender em metros, unidade 1.0; 1 m = 100 uu. Cubo de 1 m deve importar com 100 uu; o herói, 150 uu (seção 3.1) |
| Eixos | Z para cima, personagem olhando para +X no UE. Preset de exportação do Blender (frente/cima, "Apply Scalings", conversão de unidade) fixado num `art-src/export_presets/` depois de testar com um cubo e um esqueleto de teste: **confirmar no 5.8** os valores exatos do importador (Interchange) e registrá-los aqui |
| Transformações | Aplicadas (escala 1, rotação 0) antes de exportar; pivô nos pés (personagens) e no canto/centro de base da grade (módulos) |
| Esqueleto | Hierarquia e nomes de ossos iguais aos de `SKEL_Humanoid_Chibi`; `root` na origem; ≤ 55 ossos (herói), ≤ 35 (inimigo), ≤ 100 (chefe), 4 influências por vértice no máximo |
| Animação | 30 fps autoral; um FBX por clipe ou um por personagem com várias takes; sem root motion; seções do montage marcadas depois no UE |
| UVs | UV0 para o albedo pintado (sem sobreposição em personagens); UV1 não é necessária (sem lightmaps) |
| LODs | Personagens: LOD0 + LOD1 (≈ 50% dos triângulos) + LOD2 (≈ 25%); transições a **18 m** e **32 m** do herói (1800 e 3200 uu; como a câmera fica a 42 m, a distância usada é a do herói, não a da câmera: aplicar por `UShatterPresentationComponent`, **confirmar no 5.8**), geradas pela redução do motor ou à mão. Cenário: LOD0 só para peças ≤ 1000 tri; LOD1 (≈ 50%) para peças acima de 1500 tri. Com câmera fixa o ganho de LOD é pequeno; ele serve de escala de qualidade (`sg.ViewDistanceQuality`) e para o Deck |
| Colisão | Cenário: só **colisão simples** (`UBX_`, `UCX_`) no FBX ou no editor; `Use Complex Collision As Simple` desligado; um piso de colisão por sala em vez de um por tile. Personagens: mesh sem colisão, só cápsula. Props decorativos pequenos: sem colisão |
| Navegação | `NavMeshBoundsVolume` por mapa, gerado a partir da colisão simples; props só visuais não afetam |
| Instâncias | Peças repetidas (chão, parede, pilar) colocadas como instâncias (`ISM`/`HISM`) por kit, para reduzir draw calls |
| Sombras | `CastShadow` desligado em cenário por padrão (3.6) |
| Materiais | Todo mesh usa um `MI_` filho de um mestre (3.5); material solto proibido |
| Checklist | Auditoria automática (17.4) roda no CI; reprova asset fora do orçamento |

### 17.3 Orçamento por tipo de asset

Triângulos (LOD0) e texturas. Os tamanhos máximos assumem a câmera da seção 3.2 (herói com ~155 px de altura em 1080p); a **densidade de texel** vem do `docs/03_design_system.md`. Metas iniciais, revisadas pela medição da F1.

| Tipo | Triângulos | Material slots | Texturas (por asset) | Observação |
|---|---|---|---|---|
| Herói (corpo + equipamento) | 7.000 a 10.000 | 1 (máx. 2) | 1024² albedo BC7 + 512² máscara BC1 | Variantes de cor por `MI_` e região B da máscara |
| Inimigo comum | 3.500 a 5.000 | 1 | 512² albedo + 256² máscara | Fixa o teto de 30 ativos. **Elite não tem malha própria**: usa a malha do comum com tinta (região B da máscara), halo e escala até ×1,15, só por `MI_` e parâmetros |
| Chefe | 15.000 a 25.000 | 1 a 2 | 2048² albedo num slot, **ou** 2 slots de 1024² + 512² máscara | |
| Peça modular de chão | 200 a 600 | 1 (kit) | Atlas do kit (abaixo) | |
| Parede, pilar, arco | 800 a 2.500 | 1 (kit) | Atlas do kit | |
| Estátua / prop de destaque | 3.000 a 5.000 | 1 | 512² a 1024² | Só 1 a 3 por sala |
| Prop pequeno (vaso, osso, caixão) | 100 a 800 | 1 (kit) | Atlas do kit | Sem colisão quando decorativo |
| Kit de área (atlas) | — | — | até 4 folhas de 2048² (albedo BC1) + 1 máscara de emissivo 1024² BC1 | Todas as peças da área compartilham as folhas |
| Textura de VFX | — | — | 256² a 512², canal único (BC4) sempre que possível | Reutilizada entre sistemas |
| Ícones e UI | — | — | Segundo `docs/03_design_system.md` | Grupo de textura de UI, sem mip |

Sem normal map em nenhum tipo de asset. Formato: BC7 em albedo de personagem (gradiente pintado sem faixas), BC1 em cenário e máscaras; mipmaps ligados; streaming ligado. Teto de assets de uma área carregada: ≤ 120 MB cooked (também garante carga < 3 s, RNF-04, e ajuda na meta de instalador < 500 MB; **confirmar no 5.8** o tamanho base do motor empacotado).

### 17.4 Auditoria automática

`EchoesOfTheShatter.Art.Budgets` (Automation Test no módulo de jogo, só no editor): percorre o Asset Registry por prefixo/pasta e confere triângulos do LOD0, número de ossos, material slots, tamanho máximo de textura, formato de compressão, mesh de cenário com `CastShadow` e material fora dos mestres. Falha lista asset e limite. Os limites vêm da tabela 17.3, num `DA_ArtBudgets` (dado, não código).

---

## 18. Orçamentos de desempenho por cena (RNF-04)

Alvo: 60 FPS estáveis (quadro ≤ 16,6 ms) na Cripta com 30 inimigos ativos, e carga da área < 3 s. **Hardware de referência pendente (P-4 do `docs/02_requisitos.md`)**: até o dono indicar a máquina, assume-se como "PC de entrada" uma GPU de 4 GB do nível de uma GTX 1050 Ti/RX 570 (ou GPU integrada moderna), CPU de 4 núcleos, 8 GB de RAM, 1080p. O Steam Deck é medido como alvo próprio. Os números abaixo são **metas iniciais a validar na F1** com `stat unit`, `stat scenerendering`, `stat niagara` e CSV Profiler, não resultados medidos.

| Recurso (cena de combate, pico) | PC de entrada (1080p, MSAA 4x) | Steam Deck (1280×800, MSAA 2x) |
|---|---|---|
| Tempo de quadro | ≤ 16,6 ms | ≤ 16,6 ms (limite de 60 FPS) |
| Game thread | ≤ 6 ms | ≤ 7 ms |
| Render thread | ≤ 6 ms | ≤ 6 ms |
| GPU | ≤ 13 ms | ≤ 14 ms |
| Draw calls | ≤ 1.200 | ≤ 800 |
| Triângulos visíveis (passe principal) | ≤ 1,2 M | ≤ 600 mil |
| Triângulos no passe de sombra | ≤ 200 mil | ≤ 100 mil (ou blob, sem passe) |
| Skeletal meshes ativos | ≤ 40 (30 inimigos + herói + chefe/aliados) | ≤ 40, com LOD1 forçado nos inimigos distantes |
| Ossos atualizados por quadro | ≤ 1.600 | ≤ 1.200 |
| Luzes dinâmicas | 1 direcional + ≤ 4 pontuais sem sombra | 1 direcional + ≤ 2 pontuais |
| Cascatas de sombra | 2 | 1 ou blob |
| Partículas Niagara ativas | ≤ 3.000 | ≤ 1.500 |
| Sistemas Niagara ativos | ≤ 40 | ≤ 24 |
| Área de tela com translucência (pico) | ≤ 25% | ≤ 15% |
| Memória de textura (pool de streaming) | ≤ 1,5 GB | ≤ 1 GB (`r.Streaming.PoolSize`) |
| VRAM total | ≤ 2,5 GB | ≤ 2 GB (memória compartilhada com a CPU) |
| RAM do processo | ≤ 3 GB | ≤ 3 GB |
| Assets carregados por área | ≤ 120 MB cooked | ≤ 120 MB cooked |
| Carga da área | < 3 s | < 3 s (leitura de SSD; medir em cartão SD) |

Meta de quadro: 60 FPS em PC e Deck. Piso aceitável no Deck: **40 FPS (modo de 40 Hz da tela)**, a adotar só se a medição da F1 mostrar que o orçamento acima não fecha; nesse caso o limite de quadro vira 25 ms e a decisão volta ao orquestrador. Escalabilidade (`sg.*` e opções de vídeo): Alto (PC): MSAA 4x, 2 cascatas; Médio (padrão no Deck): MSAA 2x, 1 cascata ou blob; Baixo: MSAA off, blob, partículas ×0,5. A opção persiste em `GameUserSettings.ini` (seção 8).

Como medir e proteger: (1) `ue-nightly` ganha um job de desempenho (self-hosted com GPU) que roda o bot do `EchoesOfTheShatter.Smoke` na Cripta por 60 s com 30 inimigos, captura CSV Profiler e falha se p95 do quadro > 16,6 ms ou algum limite da tabela estourar; (2) cada mudança de arte grande passa pela auditoria 17.4; (3) o Performance Engineer inclui UE em `docs/12_performance.md` (PC de entrada e Deck, frio e quente). Se um limite estourar, a ordem de corte é: partículas, sombras, MSAA, triângulos de props, nunca a regra do jogo.
