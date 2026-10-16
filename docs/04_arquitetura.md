# 04 — Arquitetura e contratos técnicos (Tech Lead)

Projeto: **Echoes of the Shatter**. Fonte de design: `docs/00_plano_existente.md` (Plano Steam v2.0). Motor: **Unity 6 LTS com URP, C#** (decisão do dono em 16/10/2026, ver `docs/08_decisoes_visual_3d.md`), que substitui o Godot 4 da seção 10 do plano (houve uma escolha intermediária de outro motor, registrada na seção 15).

Este documento é o contrato técnico de todos os agentes. Os headers em `ShatterCore/include/shatter/` são a parte executável deste contrato: se o texto e o header discordarem, **vale o header** e este documento deve ser corrigido. Itens marcados **confirmar na instalação** dependem da versão do Unity instalada e não devem ser tratados como contrato até serem testados.

---

## 1. Princípio central (preservado do plano)

> Um único motor de regras, independente de cenas e do motor gráfico, usado pelo combate em tempo real **e** pelo simulador idle. Mesma seed + mesmos dados + mesmo snapshot = mesmo resultado.

Como isso fica no Unity:

1. **ShatterCore** é uma biblioteca C++17 pura (só STL) com todas as regras: atributos, golpe, efeitos, loot, simulador de expedição, relógio, save. Compila e testa **sem o Unity** (CMake + mini framework próprio). Para o jogo, ela é compilada também como **DLL nativa** e chamada pelo C# por uma API C estável (seção 9).
2. O jogo Unity **nunca calcula regra**. MonoBehaviours e serviços C# só pedem ao ShatterCore e desenham o resultado.
3. **Dados fora do código**: todo número de balanceamento está em CSV (`Data/*.csv`, seção 4.2), lido diretamente pelo ShatterCore (o mesmo CSV nos testes, no bench e no jogo).
4. **RNG em fluxos separados** (`Combat`, `Loot`, `Events`), cada um com seed `DeriveSeed(seed_expedição, fluxo, índice_encontro)` (`rng.h`). Simular 1 vez ou em 10 partes dá resultado idêntico, e mexer no combate não muda o loot.

---

## 2. Decisões de base

| Tema | Decisão | Por quê |
|---|---|---|
| Motor | **Unity 6 LTS** (linha 6000.x LTS mais recente na instalação). Fixar a versão exata em `ProjectSettings/ProjectVersion.txt` e não atualizar até o Acesso Antecipado; upgrade só entre fases, com todos os testes passando. **Confirmar na instalação** a versão e o suporte de cada item deste documento | Atualizar o motor no meio quebra coisas. Cenas, prefabs e ScriptableObjects são texto (YAML), e a CLI compila e testa: bom para trabalho com agentes |
| Linguagem | C# (C# 9 e .NET Standard 2.1 como padrão do Unity 6; **confirmar na instalação**) para jogo e apresentação; C++17 só no ShatterCore | Regras testáveis fora do editor; o C# não pode divergir do motor de regras |
| Scripting backend | **IL2CPP** nos builds de release e de teste de jogador; **Mono** no editor e nos testes de editor | IL2CPP: desempenho e menos superfície de engenharia reversa; Mono: iteração rápida. O P/Invoke precisa ser validado nos dois (seção 9.8) |
| Render pipeline | **URP** (Universal Render Pipeline), Forward, MSAA, SRP Batcher ligado, sem iluminação global em tempo real e sem lightmaps (seção 3.4) | Leve para PC de entrada e Steam Deck; a referência visual foi feita em URP. Forward+ só se faltarem luzes por objeto (o Forward aceita até 8) |
| Pacotes adotados | `com.unity.render-pipelines.universal` (inclui Shader Graph), `com.unity.inputsystem`, `com.unity.ai.navigation`, `com.unity.test-framework` (a UI é UI Toolkit, que já vem no editor). Versões exatas: **confirmar na instalação** | Só o necessário. Remover do manifesto os pacotes padrão sem uso (Timeline, Visual Scripting, Analytics, Ads, Multiplayer Center, IDE plugins que não forem usados) para reduzir import e build |
| Pacotes **não** adotados | **Cinemachine** (câmera própria, seção 3.2), **Animation Rigging** (sem IK), **Addressables** (cenas por área via `SceneManager`; reavaliar se a carga de área passar de 3 s ou o limite de 120 MB), **VFX Graph** (Particle System basta; só se um efeito passar de ~500 partículas), **Timeline**, **Unity Localization** (leitor de CSV próprio, seção 7), **DOTS/ECS e Burst** (30 inimigos não justificam), **Mirror/Netcode** (jogo offline, RNF-06) | Cada dependência custa build, import e manutenção. A câmera é fixa e de ~60 linhas; Cinemachine entra só se a F1 pedir impulso de tremor ou transições que a câmera própria não cobre |
| Entrada | **Input System**: um `Echoes.inputactions` com um mapa `Gameplay` e uma ação nomeada por comando; remapeamento por `InputActionRebindingExtensions` salvo em JSON | Equivalente ao InputMap do plano; controle no 1.0 = novo esquema de controle no mesmo asset |
| Localização | CSV `Data/Loc/*.csv` lidos em C# (seção 7) | Nenhum texto no código; mesma planilha `chave, pt_BR, en, es` do plano |
| Save | **JSON próprio** no ShatterCore (`save.h`), lido e gravado pela DLL; o C# nunca grava o save | Ver seção 8 |
| Steam | `Steamworks.NET` (MIT) atrás de `IPlatformService` (conquistas, overlay, presença e `GetServerRealTime`), com implementação nula para dev e CI. **Decisão do orquestrador na F3**: alternativa `Facepunch.Steamworks` | O wrapper permite builds sem Steam; é dependência externa, por isso a decisão fica registrada |
| Versionamento | Git + GitHub, **Git LFS** para binários: `*.fbx *.png *.tga *.psd *.blend *.exr *.hdr *.wav *.ogg *.ttf *.otf *.dll *.so`. Cenas, prefabs, materiais, controllers e ScriptableObjects (YAML) **não** vão no LFS; `.gitattributes` aponta o `UnityYAMLMerge` para eles | Igual ao plano; arquivos de texto mesclam e revisam em diff |
| Configuração do projeto | Asset Serialization = **Force Text**; Version Control = **Visible Meta Files**; `.gitignore` de `Library/ Temp/ Logs/ obj/ UserSettings/ Builds/` | Revisão por diff e merge confiáveis |
| Plataforma | Windows x64 (D3D11 padrão, D3D12 opcional; **confirmar na instalação** o padrão do Unity 6). Steam Deck via Proton com o mesmo binário Windows | Um binário só = mesmo resultado de simulação no Deck. Build Linux nativo fica como alternativa a medir na F1 |

---

## 3. Renderização 3D estilizada (URP, câmera 3/4, forward + MSAA)

Fonte das decisões: `docs/08_decisoes_visual_3d.md` (fechadas, não reabertas aqui). Esta seção só fixa números e mecanismos. Proporções, densidade de texel, cores-assinatura de área e estilo da UI são do `docs/03_design_system.md` e de `docs/03_design_tokens.json`; aqui não são repetidos.

**Princípio:** a renderização só desenha. Nenhuma regra, tempo de fase ou número de balanceamento mora na apresentação; animação, VFX e hitstop seguem os eventos e as fases do `CombatSystem`/`SkillComponent` (seção 6.2), nunca o contrário.

### 3.1 Escala do mundo e eixos

| Item | Valor |
|---|---|
| Unidade | **1 unidade Unity = 1 m** (importação 1:1 do Blender, seção 17.1) |
| Herói | altura **1,50 m** (proporções: `docs/03_design_system.md`); `CharacterController` com raio **0,30 m**, altura 1,50 m e centro (0, 0,75, 0) |
| Grade de cenário | **1 m**; peças de 2 e 4 m |
| Eixos | Y para cima; gameplay no plano **XZ**; o personagem "olha" para **+Z**; pivô nos pés |
| Física | Sem Rigidbody de gameplay. `Physics.simulationMode = Script` (nunca simulada); só consultas (`Overlap*NonAlloc`, `Raycast`) e `CharacterController`/`NavMeshAgent` para movimento. **Confirmar na instalação** que o `CharacterController` anda sem simulação automática |
| Mira | Raio do mouse × plano horizontal do piso da sala (`Plane.Raycast`), sem raycast contra a malha |

### 3.2 Câmera

**Decisão:** câmera própria, sem Cinemachine. Uma `FollowCamera` (MonoBehaviour, `LateUpdate`) move uma raiz `CameraRig` com rotação fixa; a `Camera` é filha a −42 m no eixo local Z. Valores num ScriptableObject `RenderSettingsAsset` (apresentação, fora do CSV de balanceamento).

| Parâmetro | Valor | Observação |
|---|---|---|
| Pitch | **55°** (rotação X do rig; olha para baixo) | Meio da faixa decidida (50° a 60°) |
| Yaw | **45°** fixo | Sem rotação pelo jogador |
| FOV | **14,2° vertical** (≡ 25° horizontal a 16:9) | O `Camera.fieldOfView` do Unity é vertical, então 16:9 e 16:10 (Deck) mostram a mesma altura |
| Distância | **42 m** | Mostra ~18,6 × 10,5 m perpendiculares à câmera, ~6,4 módulos de 2 m de profundidade no chão; o herói (1,5 m) ocupa ~14% da altura da tela (~155 px em 1080p). Distância **mantida** em relação ao herói de 1,5 m: é legível; se a F1 mostrar herói pequeno, reduzir para 38 m |
| Zoom | Padrão 42 m; faixa **36 a 50 m** (passo 2) | Sem zoom do jogador no Acesso Antecipado; a faixa é usada pelo `AreaProfile` (arenas de chefe podem afastar até +15%) |
| Alvo | Posição do herói + (0, 0,52, 0) m | Enquadra o tronco |
| Suavização | Exponencial independente de FPS: `pos = Lerp(pos, alvo, 1 − exp(−7·dt))`, distância máxima de atraso 2 m; **sem** atraso de rotação | A câmera não perde o herói na esquiva |
| Planos de corte | Near 1 m, far 150 m | |
| Colisão da câmera | Nenhuma | Paredes que cobrem o herói são tratadas por fade (3.7) |
| Tremor | Deslocamento aditivo do rig, máx. 0,08 m, opção de desligar | Só em chefes e impactos grandes |

### 3.3 Malhas e animação

- **Personagens:** `SkinnedMeshRenderer` com **Animator** (Animator Controller). Sem colisor no mesh; o gameplay usa só o `CharacterController` e as consultas de overlap no plano. Sem ragdoll: morte é animação. Skin Weights = 4 ossos; GPU Skinning ligado; `updateWhenOffscreen = false`.
- **Rig (decidido): Generic**, com a mesma hierarquia e os mesmos nomes de ossos para as três classes (`Rig_Humanoid_Chibi`), de modo que os clipes de golpe e conjuração sirvam a todas sem retargeting. Alternativa descartada: Humanoid (retargeting e passe de IK custam CPU e só valem se vierem animações de bibliotecas externas). Cada família de inimigo tem rig próprio. Pontos de ancoragem: Transforms filhos `socket_weapon_r`, `socket_weapon_l`, `socket_cast`, `socket_head`, `socket_fx_ground`.
- **Animator Controller:** um `AC_Hero_<Classe>` e um `AC_Enemy_Base`. Camada **Base** (máquina Parado ↔ Andar, parâmetro `Speed`), camada **Action** (um estado por clipe de ação: ataque básico, golpe, conjuração, esquiva), camada **Hit** (aditiva, tomar dano) e estado de morte. Parâmetros de leitura vindos do C#: `Speed`, `IsDead`, `IsStaggered`, `ActionSpeed`. Alternativa descartada: Playables API direta (mais código, sem editor visual); fica para o caso de o controller ficar complexo demais.
- **Ações por habilidade (equivalente a montagens):** cada clipe de ação tem 3 fases (`Windup`, `Impact`, `Recovery`) definidas por **frações do clipe** (`windupEnd`, `impactEnd`) no `SkillPresentationSet` (ScriptableObject de apresentação, validado por teste de editor). Ao mudar de fase, o `SkillComponent` chama `Animator.Play(estado, camada, fraçãoDeInício)` e ajusta `ActionSpeed` com `velocidade = duração_autoral_da_fase / duração_da_fase_no_CSV`. A animação **se adapta** aos tempos do CSV e o Game Designer rebalanceia sem reanimar. Root motion desligado: esquiva e avanço movem o personagem pelo comportamento da habilidade.
- **Mapeamento habilidade → clipe + VFX:** `SkillPresentationSet` (um por classe/família), chave = ID de conteúdo (`skill.warrior.iron_cut`) → estado do Animator, frações de fase, prefab de VFX, âncora, som. É dado de apresentação, não de balanceamento; habilidade sem entrada cai no clipe genérico de golpe ou conjuração pela forma (`SkillShape`) e é registrada no log.
- **Animation Events:** só para VFX, som e passos, recebidos por um `AnimationEventRelay` no mesmo GameObject. **Nunca** causam dano nem avançam estado de regra: o impacto é a fase `impact` do passo fixo.
- **Conjunto mínimo por classe** (do plano): `AN_<Dono>_Idle`, `_Walk`, `_Dodge`, `_BasicAttack`, `_SkillStrike`, `_SkillCast`, `_Hit`, `_Death`. Inimigos: `_Idle`, `_Walk`, `_Attack` (com o telegraph como início do clipe), `_Hit` opcional, `_Death`; chefes acrescentam um clipe por padrão de ataque.
- **Hitstop por entidade (apresentação):** quando o core congela os timers da entidade, o `PresentationController` faz `Animator.speed = 0` (restaura ao fim) e `ParticleSystem.main.simulationSpeed = 0` nos sistemas de partículas presos à entidade (lista em cache); o VFX do impacto **não** pausa. `Time.timeScale` **nunca** é usado, para não congelar o jogo todo.
- **Reações visuais:** flash de dano por propriedade `_HitFlash`, dissolução da morte por `_Dissolve` (alpha clip com ruído/dither, sem translucidez). Cada entidade tem **uma instância de material** criada uma vez (em pool) e atualizada com `SetFloat` por ID em cache; **`MaterialPropertyBlock` não é usado**, porque quebra o SRP Batcher.
- **Custo de animação:** `Animator.cullingMode = CullUpdateTransforms` nos inimigos; Controller sem camadas extras nem IK; **confirmar na instalação** se o limite de ossos e inimigos da seção 18 fecha em CPU.

### 3.4 Pipeline gráfico (URP)

Forward com **MSAA**, sem iluminação global em tempo real, sem lightmaps (Lighting Settings: Baked GI e Realtime GI desligados, ambiente em cor fixa vinda do `AreaProfile`): toda a luz de cenário está pintada no albedo, como decidido.

| Configuração (URP Asset e Project Settings) | Valor |
|---|---|
| Renderer | Forward (um `UniversalRendererData`); Forward+ só se a medição pedir mais luzes |
| Anti-aliasing | MSAA **4x** no PC de entrada, **2x** no Steam Deck (opção de vídeo Off/2x/4x, trocada pelo URP Asset de cada nível de qualidade); sem TAA/FXAA |
| SRP Batcher | Ligado; GPU Instancing nos materiais de props repetidos; Dynamic Batching desligado; Static Batching nas peças estáticas do cenário |
| Depth Texture, Opaque Texture | Desligadas (ligar só se um efeito comprovadamente precisar) |
| HDR | Ligado, para o núcleo de VFX acima de 1; Tonemapping e Bloom definidos pelo Art Director (Bloom leve, só em meio-resolução; desligável no Deck) |
| Pós-processo | Volume global mínimo; sem motion blur, SSAO, depth of field ou lens flare por padrão |
| Luzes | 1 luz direcional principal + ≤ 4 pontuais **sem sombra** (tochas, cristais) |
| Qualidade | Três níveis (Baixo, Médio, Alto) com URP Assets próprios; Médio é o padrão do Deck. A escolha vai para `settings.json`, não para o save de jogo |
| Texturas | Mipmap Streaming ligado; sem normal map no projeto; formatos na seção 17.1 |
| Vsync e quadro | `Application.targetFrameRate = 60` com Vsync desligado e limitador próprio, ou Vsync ligado (opção do jogador); **confirmar na instalação** o comportamento no Deck |

Como a cena é pintada, a luz dinâmica só modula e dá sombra aos personagens, não define o visual.

### 3.5 Shaders mestres (Shader Graph)

Quatro mestres em **Shader Graph** (alvo URP), todos parametrizados; os assets reais são materiais (`M_`) filhos de um mestre. Instruções e variantes limitadas (máx. 8 combinações de keywords por mestre) para conter o tempo de compilação e o tamanho do build. Todos compatíveis com o SRP Batcher (propriedades só em materiais, nunca por MaterialPropertyBlock). Metas de custo: fragmento de personagem leve, cenário mais leve, VFX mais leve ainda (medir no Frame Debugger e no Profiler; os números são metas iniciais).

| Mestre | Tipo de grafo | Entradas principais |
|---|---|---|
| `SG_Character` | Lit, opaco, Smoothness 0, Metallic 0; alpha clip só para a dissolução | `_BaseMap` (albedo pintado), `_MaskMap` (R = emissivo, G = rim, B = região de tinta para variantes/skins, A reservado), cor/potência/intensidade do rim (nó Fresnel Effect), `_HitFlash`, `_Dissolve`, `_DitherFade` |
| `SG_Environment` | Lit, opaco ou alpha clip (keyword) | Albedo pintado, máscara de emissivo, fade por oclusão (3.7, keyword `OCCLUDER_FADE`), tremulação para chamas e cristais, cor de vértice opcional (AO pintada) |
| `SG_VFX` | Unlit; keywords para Additive, Translucent, Masked/opaco "quente" e Telegraph | Forma/ruído, núcleo claro (emissivo > 1) + borda colorida, soft particles opcional, cor por partícula (Vertex Color) |
| UI | UI Toolkit (sem Shader Graph) | Moldura e preenchimento "lava" por 9-slice e uma textura animada (3.11) |

Propriedades globais (`Shader.SetGlobal*`): `_EchoesHeroPos`, `_EchoesTime` (tremulação), `_EchoesFadeRadius`. Texturas: mipmaps ligados, sRGB para albedo, linear para máscara, filtro Trilinear com Aniso 4 (padrão). Densidade de texel: `docs/03_design_system.md`; tamanhos máximos na seção 17.2.

### 3.6 Sombras

**Decisão:** sombras da luz direcional principal, **só os personagens projetam**; o cenário não projeta (`ShadowCastingMode = Off`) e só recebe. Motivo: o custo de sombra fica limitado a ~31 malhas de 3,5 a 10 mil triângulos, em vez de todo o cenário; a sombra do herói no chão é o que ancora o personagem na câmera 3/4.

- URP Asset: Max Distance **25 m**, **2 cascatas**, resolução 1024, Soft Shadows desligado no nível Baixo. Luzes adicionais sem sombra. Props altos que precisem de sombra projetada ligam `ShadowCastingMode` por exceção, no checklist da seção 17.3.
- **Plano B (nível Baixo, Steam Deck se faltar GPU):** sombra falsa em blob (quad escuro suave sob os pés, material do `SG_VFX`) e sombras do URP desligadas.
- Sem sombra de contato nem sombras de luzes adicionais (fora do escopo; reavaliar só se a medição pedir).

### 3.7 Oclusão da câmera

Paredes entre a câmera e o herói não podem esconder o combate. **Decisão:** fade com dither no `SG_Environment` (keyword `OCCLUDER_FADE`), dirigido por `_EchoesHeroPos` e `_EchoesFadeRadius` (~3 m) atualizados por um `OcclusionFadeDriver`: só os materiais de peças marcadas como "occluder" usam a keyword. Sem colisão de câmera. Silhueta do herói atrás de objetos: **Render Objects** (Renderer Feature nativa do URP) na layer do herói, com teste de profundidade "Greater" e material de silhueta de cor sólida; **confirmar na instalação** que funciona em Forward + MSAA. Contorno geral (outline) **não** é adotado: o estilo pintado já traz a borda no albedo; contorno em chefes e elites só se o Art Director pedir, por casco invertido (segundo material), pago só nesses meshes.

### 3.8 Névoa por área

`AreaProfile` (`ScriptableObject`, um por área: `SO_Area_<Area>`) guarda a cor-assinatura (valores do `docs/03_design_system.md`), o modo e a densidade da névoa (`RenderSettings.fog`, `FogMode.ExponentialSquared`), cor, intensidade e rotação da luz direcional, cor de ambiente, faixa de zoom permitida e música. Um `AreaVisuals` (um por cena de área) aplica o perfil em `Start` e interpola ao cruzar portais de área. A névoa do Unity é de distância; névoa de altura, se a arte pedir, é feita com planos de névoa (quads com `SG_VFX`) por área. O perfil é dado de apresentação (fora do CSV de balanceamento); a ligação área → perfil é por ID de conteúdo da área.

### 3.9 VFX (Particle System)

- **Particle System** (Shuriken) com materiais do `SG_VFX`; prefabs `FX_<Dono>_<Efeito>` em pool (`UnityEngine.Pool.ObjectPool<T>`), sem `Instantiate`/`Destroy` por golpe. Módulos caros (colisão, luzes, trails em excesso) proibidos por padrão; `maxParticles` explícito em cada sistema. **VFX Graph não adotado** (só se um efeito passar de ~500 partículas e a medição justificar). Disparo por eventos do `EventBus` ou por Animation Event (visual).
- **Linguagem visual (decisão 5):** efeitos do jogador finos e translúcidos, com núcleo claro (emissivo acima de 1) e borda na cor da classe; ameaças inimigas opacas e quentes (laranja/vermelho), legíveis sobre qualquer fundo.
- Todo VFX respeita o orçamento da seção 18 e a ordem de desenho de 3.10. A duração do efeito não muda a regra: o efeito acaba quando a apresentação acaba, a regra já terminou.

### 3.10 Telegraphs e ordem de desenho

**Telegraph de inimigo** (aviso no chão antes do golpe): `TelegraphView` em pool, um mesh plano (quad ou ribbon) a **+0,02 m** do chão, material do `SG_VFX` na variante Telegraph: **alpha clip** (borda por SDF analítica no material, `_Progress` 0→1 pelo tempo de windup do `EnemyAttack`), cor quente opaca, escrevendo profundidade, fila Geometry/AlphaTest. Forma por parâmetro (cone, círculo, linha, anel), dimensões vindas do `SkillData`/`EnemyAttack` (alcance e ângulo reais da consulta, para o aviso não mentir). Bordas suaves por alpha-to-coverage com MSAA (opção "Alpha to Mask" do Shader Graph; **confirmar na instalação**). O Decal Renderer Feature do URP não é usado (o mesh plano é mais previsível em Forward + MSAA).

Ordem de desenho, de trás para frente (filas do URP):

| # | Camada | Mecanismo |
|---|---|---|
| 1 | Cenário (chão, paredes, props) | Geometry (2000), profundidade real |
| 2 | Telegraphs de inimigo | AlphaTest (2450), +0,02 m, escreve profundidade (personagens à frente os ocultam corretamente) |
| 3 | Personagens (heróis, inimigos) | Geometry |
| 4 | VFX quente de inimigo (projéteis, impactos) | AlphaTest/opaco, escreve profundidade |
| 5 | VFX do jogador | Transparent (3000), `sortingOrder` 10 no `ParticleSystemRenderer` |
| 6 | Silhueta (Render Objects) e névoa | Névoa por fragmento, na ordem do pipeline |
| 7 | Números de dano e UI | UI Toolkit por cima de tudo |

Nenhum VFX translúcido do jogador esconde um telegraph inimigo: o telegraph não é translúcido e é desenhado antes.

### 3.11 Interface (UI Toolkit)

UI Toolkit (UXML e USS) com um `UIDocument` e um `PanelSettings` em resolução **nativa**, sem escala inteira nem fonte de pixel. Escala do painel: **Scale With Screen Size**, referência 1920×1080, casamento pela altura (1080p = 1,0; 16:9 e 16:10 testados, 1440p, 4K e Deck 1280×800). O modo "Constant Physical Size" (DPI do sistema) **não** é o padrão, porque o DPI reportado no Windows e no Proton é pouco confiável; **confirmar na instalação** e na F1 qual dos dois escala melhor, mantendo a decisão 6 (resolução nativa, sem escala inteira). Tokens: `Assets/UI/Theme/tokens.uss` é **gerado** de `docs/03_design_tokens.json` pelo script `tools/gen_tokens.py` (variáveis USS `--color-...`, `--space-...`); ninguém edita à mão. Estilo (pedra escura, molduras orgânicas, preenchimento "lava"), fonte e acentos: `docs/03_design_system.md`. Textos por chave de localização via `LocLabel` (seção 7). Números de dano e barras de vida de inimigos: `DamageNumberLayer`, um único `VisualElement` de tela cheia com elementos em pool, posicionados por `RuntimePanelUtils.CameraTransformWorldToPanel`; sem um painel por inimigo.

---

## 4. Estrutura do repositório e do projeto Unity

### 4.1 Raiz do repositório

```
/                                   raiz do repositório (Git + LFS)
├─ docs/                            documentos (este arquivo é o 04)
├─ ShatterCore/                     motor de regras C++17 puro (sem Unity)
│  ├─ CMakeLists.txt                lib estática shattercore, DLL shattercore (SHARED), testes, bench
│  ├─ include/shatter/*.h           CONTRATOS públicos (Tech Lead); shatter_c.h é a API C
│  ├─ src/*.cpp                     implementação (Backend Engineer)
│  ├─ src/c_api/shatter_c.cpp       implementação da API C (agente de Integração, seção 9)
│  ├─ tests/test_framework.h        mini framework (TEST, EXPECT_*)
│  ├─ tests/*.cpp                   testes unitários, determinismo, idle, loot, save, API C
│  ├─ tests/qa_*.cpp                testes do QA
│  ├─ tests/data/                   CSV mínimos de teste, saves de cada versão (saves/save_vN.json), golden/
│  └─ bench/*.cpp                   benchmark (Performance Engineer)
├─ EchoesOfTheShatter/              projeto Unity 6 (raiz do projeto: Assets/, Packages/, ProjectSettings/)
├─ art-src/                         fontes de arte (.blend, pinturas, presets de exportação), Git LFS, fora do projeto Unity
├─ tools/                           validate_data.py, gen_tokens.py, build_native.* (scripts sem dependências externas)
└─ .github/workflows/               CI (seção 14)
```

A pasta `EchoesOfTheShatter/` já existe com `Content/Data/` (CSV e esquemas). Ela vira a raiz do projeto Unity (proposta; **nenhum arquivo é movido por este documento**). Os protótipos Godot da raiz (`project.godot`, `core/`, `scenes/` etc.) continuam só como referência de game feel.

### 4.2 Projeto Unity (`EchoesOfTheShatter/`)

```
EchoesOfTheShatter/
├─ Assets/
│  ├─ Plugins/x86_64/               shattercore.dll (+ .meta com as configurações do plugin), seção 9.3
│  ├─ StreamingAssets/Data/         *.csv de balanceamento e conteúdo (fonte da verdade, arquivos soltos)
│  ├─ StreamingAssets/Data/Loc/     Loc*.csv (chave, pt_BR, en, es, context, gender)
│  ├─ Scripts/
│  │  ├─ Interop/                   Echoes.Interop      (P/Invoke, SafeHandles, structs blittable)
│  │  ├─ Core/                      Echoes.Core         (serviços, EventBus, save, localização, plataforma)
│  │  ├─ Gameplay/                  Echoes.Gameplay     (combate, personagens, inimigos, habilidades, expedição, input)
│  │  ├─ Presentation/              Echoes.Presentation (câmera, animação, VFX, telegraphs, áreas)
│  │  ├─ UI/                        Echoes.UI           (controladores de tela, LocLabel, camada de dano)
│  │  └─ Editor/                    Echoes.EditorTools  (auditoria de arte, build, gerador de tokens se feito no editor)
│  ├─ Tests/EditMode/               Echoes.Tests.EditMode
│  ├─ Tests/PlayMode/               Echoes.Tests.PlayMode
│  ├─ Art/
│  │  ├─ Characters/Heroes/<Classe>/   FBX, AC_, AN_, M_, T_, P_  (Warrior, Archer, Mage)
│  │  ├─ Characters/Shared/            Rig_Humanoid_Chibi, clipes genéricos (golpe, conjuração)
│  │  ├─ Enemies/<Familia>/            idem, uma pasta por inimigo ou família
│  │  ├─ Bosses/<Chefe>/               idem, mais padrões de ataque
│  │  ├─ Environments/<Area>/          SM_, M_, T_, P_ do kit modular da área (Refugio, Cripta, ...)
│  │  ├─ Environments/Shared/          props reutilizáveis entre áreas
│  │  ├─ VFX/<Dono>/                   FX_ (prefabs), M_, T_  (Warrior, Archer, Mage, Enemies, World)
│  │  ├─ Materials/Masters/            SG_Character, SG_Environment, SG_VFX
│  │  └─ Shaders/SubGraphs/            SGS_ (rim, dither, flash)
│  ├─ UI/                           UXML, USS, Theme/tokens.uss (gerado), Fonts, Icons, PanelSettings
│  ├─ Data/Presentation/            SO_ (SkillPresentationSet, AreaProfile, RenderSettingsAsset, ArtBudgets)
│  ├─ Prefabs/                      P_ de gameplay (herói, inimigo, projétil, pools) e de sistema (GameRoot)
│  ├─ Scenes/                       Boot.unity, MainMenu.unity, Areas/<Area>.unity, Test/
│  ├─ Settings/                     URP Assets (Low/Med/High), Renderer, Volume profile, Echoes.inputactions
│  └─ Audio/
├─ Packages/manifest.json           pacotes (seção 2)
├─ ProjectSettings/                 em texto
└─ DataSchemas/                     esquemas das tabelas (Data Engineer); fora de Assets para não irem ao build
```

**Destino dos CSV (proposta, sem mover agora):** `Content/Data/*.csv` → `EchoesOfTheShatter/Assets/StreamingAssets/Data/`, `Content/Data/Loc/` → `.../StreamingAssets/Data/Loc/`, `Content/Data/schemas/` → `EchoesOfTheShatter/DataSchemas/`. Motivo: `StreamingAssets` é copiado cru para o build (arquivos soltos que a DLL lê por caminho, sem importação nem conversão), e o Game Designer edita o CSV sem abrir o editor. A mudança é um único commit com `git mv`, seguido de ajuste de `SHATTER_CONTENT_DIR`, `tools/validate_data.py` e do `README_dados.md` (Data Engineer). Até lá, a fonte continua em `EchoesOfTheShatter/Content/Data/`. O Unity gera um `.meta` para cada arquivo em `Assets/`: aceitável, mas o validador deve ignorá-los.

### 4.3 Assembly definitions e namespaces

| asmdef / namespace | Referencia | Regras |
|---|---|---|
| `Echoes.Interop` | nada (`noEngineReferences: true`, `allowUnsafeCode: true`) | Único lugar com `DllImport`. Sem `UnityEngine`, testável em EditMode puro |
| `Echoes.Core` | Interop | Serviços de jogo e `EventBus`; usa `UnityEngine` só para caminhos e tempo; sem regra de jogo |
| `Echoes.Gameplay` | Core, Interop, Unity.InputSystem, Unity.AI.Navigation | Comportamento de jogo: converte entre mundo Unity e chamadas ao core. **Não** referencia Presentation nem UI |
| `Echoes.Presentation` | Core, Gameplay | Reage a eventos; nunca altera estado de regra |
| `Echoes.UI` | Core, Gameplay, Presentation (só leitura) | UI Toolkit |
| `Echoes.EditorTools` | todos, só Editor | Auditoria, build, menus |
| `Echoes.Tests.EditMode` / `.PlayMode` | todos + `UnityEngine.TestRunner` | Seção 13.2 |

A direção das dependências é `Interop ← Core ← Gameplay ← Presentation ← UI`: a camada de cima conhece a de baixo, nunca o contrário. Comunicação para cima é por eventos (`EventBus`, seção 10.4). Namespaces iguais aos asmdefs. Um asmdef novo exige aprovação do Tech Lead.

### 4.4 Convenção de nomes de assets

Prefixos: `SM_` malha estática, `SK_` malha com esqueleto (FBX), `Rig_` esqueleto compartilhado, `AC_` Animator Controller, `AN_` clipe de animação, `M_` material, `SG_` Shader Graph mestre, `SGS_` sub-grafo, `T_<Nome>_BC` albedo, `_M` máscara empacotada, `P_` prefab, `FX_` prefab de VFX, `SO_` ScriptableObject, `L_`/nome simples para cenas (`Cripta.unity`). Sem normal map no projeto. Nome = `Prefixo_Dono_Descricao_Variante` (ex.: `SM_Cripta_Pillar_A`, `T_Warrior_BC`, `AN_Warrior_IronCut`). Pastas e assets em inglês/ASCII sem espaços; `<Area>` é o ID de conteúdo da área sem prefixo, em PascalCase (`Refugio`, `Cripta`). IDs de conteúdo (`skill.warrior.iron_cut`) vivem nos CSV e nos ScriptableObjects, nunca no nome do arquivo. Classes C# em PascalCase, um tipo por arquivo, nome do arquivo = nome do tipo.

---

## 5. Camadas

```
┌──────────────────────────────────────────────────────────────────────┐
│  Prefabs / Cenas / UXML+USS  (HUD, Expedição, Relatório, P_Enemy_*)   │  só apresentação
│  lê estado de serviços, assina eventos, chama ações do jogo           │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ Presentation, UI (Echoes.Presentation, Echoes.UI)
┌──────────────────────────────▼───────────────────────────────────────┐
│  C# do jogo  (Echoes.Gameplay, Echoes.Core)                           │  adaptadores
│  serviços, MonoBehaviours, EventBus; converte string↔UTF-8,           │
│  tempo real → passo fixo; nenhuma fórmula de regra aqui               │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ Echoes.Interop: P/Invoke sobre shatter_c.h
┌──────────────────────────────▼───────────────────────────────────────┐
│  ShatterCore (C++17 puro, só STL) — DLL nativa shattercore.dll        │  regras
│  Não conhece Unity, cenas, tempo real                                 │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ lê
                    StreamingAssets/Data/*.csv   (+ saves JSON)
```

Direção das dependências: `ShatterCore ← Interop ← Core ← Gameplay ← Presentation ← UI`. Uma camada só conhece a de baixo.

---

## 6. Fluxo de dados

### 6.1 Inicialização
1. Cena `Boot` → `GameRoot.Awake` cria os serviços em ordem fixa (sem localizador de serviços global: `GameRoot` os guarda e os passa por construtor/referência). `RulesService.Initialize` verifica `shatter_api_version()` e o layout de structs (9.2), chama `shatter_db_load_directory(Application.streamingAssetsPath + "/Data")` (a DLL lê os CSV e executa `Finalize`) e guarda o `ShatterDb` (SafeHandle).
   - Erros: build de desenvolvimento mostra a lista (linha, arquivo, motivo) na tela e no log; build de release abre tela de erro fatal ("dados corrompidos, verifique a integridade dos arquivos na Steam").
2. `SaveService` lê o slot ativo (`shatter_save_read`). Se o relatório de carga indicar uso de backup, a UI avisa o jogador.
3. `PlatformService` monta o `ClockInput` (UTC local + hora do servidor Steam, se houver) → `ResolveNow`.
4. `ExpeditionService` verifica expedição `Running`: `ComputeExpeditionWindow` → preenche `effectiveSeconds` → simula em thread de segundo plano (9.5) → o Tico mostra "voltando..." → relatório.
5. Coleta: `CollectExpedition` + **um único** gravação do save. `last_seen` = `NextLastSeen`.

### 6.2 Combate em tempo real (um golpe)
```
Input System → PlayerInputHandler → SkillComponent (fases: windup → impact → recovery, tempos do SkillData)
  → comportamento de forma (cone/projétil/área/avanço) faz a consulta de overlap no plano XZ
  → para cada alvo atingido (no máx. 1 vez por golpe):
     CombatSystem.ApplySkillHit(atacante, alvo, skill)
        monta HitInput (struct blittable) a partir dos StatBlocks dos dois AttributeComponent
        → shatter_resolve_hit(...)          ← A MESMA função do simulador
        → aplica HitResult (vida, barreira) e efeitos ao acertar (efeitos do core)
        → publica eventos no EventBus (OnHit, OnKill, OnLoot)
  → apresentação reage aos eventos: número de dano, flash de dano, hitstop, som, VFX
```
- Lógica de combate em **passo fixo de 1/60 s** com acumulador próprio no `CombatSystem` (chamado do `Update`, com teto de passos por quadro), independente do FPS (equivale ao `_physics_process` do plano). Não se usa `FixedUpdate`: o acumulador é explícito e testável.
- Hitstop por entidade: a entidade em hitstop não avança timers no passo fixo; o visual congela a animação da entidade (`Animator.speed`, seção 3.3). Nunca congela o jogo todo.
- RNG no jogo manual: ao entrar numa área, `runSeed` novo; combate usa `Pcg32::ForStream(runSeed, Combat, 0)`; loot de cada abate usa `ForStream(runSeed, Loot, killIndex)`; eventos de área (elites, rastros do Predador) usam `ForStream(runSeed, Events, roomIndex)`. O estado do RNG é uma struct de 2 `ulong` guardada no C# e passada por ponteiro (9.2).

### 6.3 Expedição (idle)
```
ExpeditionScreen (Ilsa) → ExpeditionService.TryStart(mapa, duração, regras)
   → CanStartExpedition(...)            (domínio, cargas, 1 por vez, 1–12 h, ≤6 regras, IdleProfile)
   → ExpeditionRequest {snapshot congelado, seed, startUtc, duração, regras, content_version}   (JSON)
   → SaveData.expeditions[...] = Running → gravação do save
   → ForecastExpedition para a previsão em faixa ("8–12 mil de XP, risco de recuo médio")
... jogo fechado ...
abrir → janela offline (clock.h) → SimulateExpedition → FinalizeExpedition → relatório → CollectExpedition → save
```

---

## 7. Localização

- Fonte: `StreamingAssets/Data/Loc/Loc*.csv` com colunas `key, pt_BR, en, es, context, gender` (Narrative & Content). Chaves no formato do plano: `ui.inventory.title`, `skill.warrior.iron_cut.name`.
- O `LocalizationService` (Echoes.Core) lê os CSV na inicialização com um leitor próprio (RFC 4180, UTF-8, `CultureInfo.InvariantCulture`) e guarda um dicionário por cultura. **Sem `build_loc.py` e sem `.po`**: o Unity Localization não é adotado (dependência e tabelas extras sem ganho para 3 idiomas). `tools/validate_data.py` continua validando chaves duplicadas, chaves referenciadas pelos CSV de conteúdo e colunas vazias.
- UXML e C# **não** têm texto literal visível ao jogador: `LocLabel` (`Label` com atributo `loc-key`) e `LocalizationService.Get(key)`. Fallback: cultura → `en` → a própria chave (com aviso no log de desenvolvimento).
- ShatterCore não tem texto: só IDs e chaves (`ExpeditionResult::tipKeys`).
- Nomes de item com gênero: a base tem `grammaticalGender` (`content.h`); `LocalizationService.Format(key, args)` aceita `{nome}` e a forma `{gender:Flamejante|Flamejante}` (variantes separadas por `|`, escolhidas pelo gênero). Nunca concatenar pedaços. Se a F1 mostrar que isso não basta (plurais), reavaliar o Unity Localization (decisão do orquestrador).
- Fontes e acentos: `docs/03_design_system.md`; teste automático de EditMode garante que todos os glifos pt-BR/es existem na fonte.

---

## 8. Save

**Decisão:** arquivo JSON próprio, gerado e lido pelo ShatterCore (`save.h`, `json.h`, `sha256.h`) **dentro da DLL**; o C# não serializa nem grava o save. Não se usa `PlayerPrefs` nem `BinaryFormatter`.

Justificativa:
1. O plano exige JSON legível, migração explícita `vN→vN+1`, checksum SHA-256, 3 backups e gravação tmp→rename; isso já está no core e é testado sem o motor.
2. A coleta "sem duplicar" depende de recalcular a expedição a partir do save. Com o save no ShatterCore, o teste de migração e o de determinismo rodam no CMake, sem editor.
3. Os saves de cada versão publicada ficam em `ShatterCore/tests/data/saves/` e são testados a cada commit.

Detalhes:
- Caminho: `Application.persistentDataPath/saves/slot_N.json` (+ `.tmp`, `.bak1..3`) → no Windows, `%USERPROFILE%\AppData\LocalLow\<Empresa>\<Produto>\saves\`. O C# passa o caminho em UTF-8 e a DLL faz a E/S (`IFileIO`). Empresa e produto ficam fixos em `ProjectSettings` antes do primeiro save publicado (mudar depois orfana saves): **confirmar na instalação** o caminho exato e o comportamento sob Proton.
- Envelope: `{format, save_version, sha256, data}`; hash sobre a forma **compacta canônica** de `data`.
- Seeds e UIDs (`uint64`) vão como **string decimal** no JSON.
- Quando salvar: ao trocar de área, coletar expedição, crafting, sair e a cada 5 min (timer do `SaveService`).
- Configurações (vídeo, áudio, qualidade) em `settings.json` e remapeamento de teclas em `bindings.json`, ambos em `persistentDataPath` e **fora** do Steam Cloud.
- Steam Auto-Cloud: raiz `WinAppDataLocalLow`, subpasta `<Empresa>/<Produto>/saves`, padrão **`slot_*.json`** (backups e configurações ficam locais). **Confirmar** no Steamworks que a raiz está disponível para o app.

---

## 9. Integração do ShatterCore com o Unity (DLL nativa + P/Invoke)

**Decisão:** o ShatterCore continua em C++17 e é compilado também como **DLL nativa x64** (`shattercore.dll`), chamada pelo C# por P/Invoke sobre uma **API C estável**. Este capítulo é só desenho; a implementação é do agente de Integração (prompt em `docs/07_proximos_passos.md`).

Alternativas consideradas: (a) portar as regras para C# (descartada: duplica o motor, perde os testes e o determinismo já definidos em C++); (b) C++/CLI ou ponte COM (descartadas: só Windows e sem ganho); (c) processo separado com IPC (descartada: latência por golpe e mais um binário). P/Invoke para uma DLL C é o caminho nativo do Unity.

### 9.1 CMake

- `shattercore` continua `STATIC` (testes, bench). Novo alvo `shattercore_dll` do tipo `SHARED`, nome de saída `shattercore`, com as mesmas fontes mais `src/c_api/shatter_c.cpp`, ligado à biblioteca estática (com `POSITION_INDEPENDENT_CODE`), controlado por `SHATTER_BUILD_SHARED` (ligado no CI e no script local de build).
- Mesmas flags de determinismo da biblioteca (`shatter_set_warnings`): `/fp:precise`, `-ffp-contract=off`, nunca `fast-math`; sem `/arch` além do padrão x64; CRT estático (`/MT`) para a DLL não depender de runtime instalado (**confirmar** com o build de release e no Proton). Visibilidade oculta por padrão; só os símbolos `SHATTER_API` são exportados (`__declspec(dllexport)`).
- Destino da DLL: o script `tools/build_native.*` compila em Release e copia para `EchoesOfTheShatter/Assets/Plugins/x86_64/`.

### 9.2 A API C (`include/shatter/shatter_c.h`)

Contrato de forma, não de conteúdo: a lista completa de funções é escrita pelo agente de Integração e revisada pelo Tech Lead; este é o desenho que ela deve seguir.

| Regra | Detalhe |
|---|---|
| Linguagem | C puro no header (`extern "C"`, `#include <stdint.h>`, `<stddef.h>`); funções `SHATTER_API` com convenção cdecl; **nenhuma exceção** cruza a fronteira |
| Versão | `uint32_t shatter_api_version(void)` devolve `SHATTER_C_API_VERSION` (inteiro, incrementa a cada mudança incompatível) e `shatter_layout_check(const uint32_t* sizes, size_t n)` compara tamanhos e offsets das structs blittable. O C# confere os dois na inicialização e aborta com mensagem clara |
| Handles opacos | `typedef struct shatter_db shatter_db;` (imutável, `ContentDB`), `shatter_save`, `shatter_statblock`, `shatter_effects`. Criados por `*_create`/`*_load*`, liberados por `*_destroy`; o dono é sempre o C# (SafeHandle). Handle nulo é erro de argumento, nunca crash |
| Status e erro | Toda função devolve `int32_t shatter_status`: `OK = 0`, `INVALID_ARGUMENT`, `BUFFER_TOO_SMALL`, `PARSE_ERROR`, `CONTENT_INVALID`, `IO_ERROR`, `VERSION_MISMATCH`, `NOT_FOUND`, `INTERNAL`. Detalhe por parâmetro de saída `shatter_error* err` (struct alocada pelo chamador: `code`, `line`, `char message[256]` UTF-8): **sem erro global e sem `thread_local`** |
| Memória | **Nenhuma alocação cruza a fronteira sem dono.** Saída de tamanho variável = buffer do chamador (`uint8_t* out, size_t cap, size_t* needed`): se `cap < needed`, devolve `BUFFER_TOO_SMALL` com `needed` preenchido e o C# repete a chamada (padrão de duas chamadas). Handles são a única memória que a DLL aloca e o C# libera |
| Texto | UTF-8 com comprimento explícito (`const char* s, size_t len`), sem depender de terminador NUL |
| Tipos | Largura fixa (`int32_t`, `uint32_t`, `uint64_t`, `double`); `bool` como `uint8_t`; seeds e UIDs como `uint64_t` (C# `ulong`); structs **blittable** com `static_assert(sizeof/offsetof)` |
| Caminho quente (POD) | `shatter_resolve_hit(const shatter_hit_input*, const shatter_rules*, shatter_rng* rng, shatter_hit_result*)`; o `shatter_rng` é uma struct de 2 `uint64_t` do chamador. Sem alocação, sem handle, dezenas de chamadas por passo |
| Caminho frio (JSON) | Estruturas grandes (`ExpeditionRequest`, `ExpeditionResult`, `CharacterSnapshot`, `SaveData`, relatório) atravessam como **JSON UTF-8** pelo `json.h` do core: `shatter_expedition_simulate(db, req_json, req_len, out, cap, &needed, &err)`. Evita layout de struct frágil e mantém o hash de resultado idêntico ao dos testes |
| Estado de entidade | `shatter_statblock` e `shatter_effects` são handles por entidade (criados do snapshot/modificadores, recalculados quando o core indicar `Revision()` novo); leitura de valores por funções pontuais |
| Save | `shatter_save_read(path, len, &save, &report_json_buf...)`, `shatter_save_write(save, path, len)`, `shatter_save_to_json`, `shatter_collect_expedition(db, save, index, result_json, len)`; o handle `shatter_save` é mutável e **não** é seguro entre threads |
| Sem estado global | A DLL pode ser carregada uma vez no processo do editor e usada por várias sessões de Play: nenhum `static` mutável, nenhum cache global |

Regras de código do core por causa da DLL e do P/Invoke (substituem as antigas regras de integração; as regras de determinismo de `CLAUDE.md` continuam valendo):
- Sem exceções (`throw`/`try`) e sem RTTI em `src/`; erros por status. Falha de alocação é fatal, como no resto do core.
- Compila como C++17 com `-Wshadow` e `/W4` sem avisos; funções exportadas `noexcept`.
- Nada de `std::string`, `std::vector` ou ponteiros do core na assinatura exportada.
- Evitar nomes que colidem com macros: `min`, `max` (Windows), `check`, `verify`.

### 9.3 Onde fica a DLL e como o Unity a carrega

- Arquivo: `Assets/Plugins/x86_64/shattercore.dll`. O `.meta` fixa o **Plugin Inspector**: só Windows x64, "Any Platform" desligado, "Load on startup" ligado; Editor: Windows x64 apenas. Linux (`libshattercore.so`) só se o build nativo para o Deck entrar (alternativa da seção 2).
- A DLL é produzida pelo CI e **versionada no Git LFS** (`*.dll`), para que artistas e designers abram o projeto sem toolchain C++; o script local `tools/build_native.*` gera a mesma DLL. O teste de EditMode `Interop.VersionMatchesSource` falha se `shatter_api_version()` da DLL difere do `SHATTER_C_API_VERSION` do header versionado.
- P/Invoke: `[DllImport("shattercore", CallingConvention = CallingConvention.Cdecl)]` em uma única classe estática `ShatterNative` (Echoes.Interop), com ponteiros (`byte*`, `void*`) e `unsafe`; strings convertidas à mão para UTF-8 (`Encoding.UTF8.GetBytes` em buffer de pilha ou do pool) para não depender do marshaling padrão. **Sem callbacks da DLL para o C#** (evita `MonoPInvokeCallback` e problemas de IL2CPP).

### 9.4 Recarga no editor

- Uma DLL nativa carregada pelo editor **fica travada** até fechar o editor; recarga de domínio (compilação C#, entrada no Play) **não** a descarrega. Fluxo: (1) o desenvolvimento das regras acontece no CMake e nos testes, não no editor; (2) `tools/build_native.*` detecta o arquivo travado e pede para fechar o editor, em vez de tentar sobrescrever; (3) o `ShatterNative` confere a versão no `[InitializeOnLoad]` (editor) e no `RuntimeInitializeOnLoadMethod` (jogo), com erro claro se não bater. Alternativa, só se isso virar atrito: copiar a DLL para um nome com hash (`shattercore_<hash>.dll`) e carregá-la com `NativeLibrary.Load`, o que permite trocar sem fechar o editor (**confirmar na instalação**).
- Handles têm dono: `GameRoot.OnDestroy`, `Application.quitting` e `EditorApplication.playModeStateChanged` descartam os `SafeHandle`. Com "Enter Play Mode Options" (sem recarga de domínio) ligado, nenhum `static` do C# pode guardar handle entre sessões.

### 9.5 Threads

- `shatter_db` (ContentDB imutável) é seguro para leitura concorrente. `shatter_save`, `shatter_statblock` e `shatter_effects` **pertencem à main thread** e não são thread-safe.
- A simulação de expedição (RNF-03, fora da thread de jogo) recebe só o `shatter_db` e um **JSON de requisição** (cópia por valor), então roda em `Task.Run`; o resultado volta pelo `SynchronizationContext` da Unity ao `await`. Código fora da main thread **não** toca em `UnityEngine`.
- Cancelamento: a DLL não tem token; a simulação em partes (`SimulateRange`) é chamada em fatias e o C# checa o `CancellationToken` entre elas. O `SafeHandle` do `shatter_db` mantém contagem de uso: sair do Play durante uma simulação só libera o banco quando a chamada termina.

### 9.6 Como o C# lê os dados

- Os CSV de balanceamento são lidos **pela DLL** (`shatter_db_load_directory` com o caminho de `Application.streamingAssetsPath/Data`); o C# não reinterpreta número de balanceamento. Em Windows e Linux desktop o `StreamingAssets` é uma pasta real, então a E/S por caminho funciona (**confirmar na instalação**; não vale em Android/WebGL, que não são alvo).
- O C# lê por conta própria apenas os `Loc*.csv` (seção 7) e os ScriptableObjects de apresentação. Para exibir nomes, ícones e tooltips, o C# consulta o `RulesService` (getters sobre dados do core devolvidos em JSON ou structs simples), nunca o CSV direto.

### 9.7 Testes da fronteira

- No CMake: `test_c_api.cpp` (ida e volta de cada função, `BUFFER_TOO_SMALL`, argumento nulo, layout das structs).
- No Unity EditMode: `Interop.*` (versão, layout, carga do CSV real) e `Rules.GoldenExpedition`, com o **mesmo `resultHash`** do golden do CMake (`ShatterCore/tests/data/golden/*.txt`).

### 9.8 Mono × IL2CPP

O P/Invoke é validado nos dois backends: EditMode e PlayMode rodam em Mono; um **teste de jogador** (build IL2CPP com a cena `Test/Smoke`, rodado em `-batchmode`) executa o golden de expedição e imprime o `resultHash`, que o CI compara. Pontos de atenção: structs blittable com `[StructLayout(LayoutKind.Sequential)]` e `Pack` explícito; nada de `bool`/`string`/arrays gerenciados na assinatura; `[DllImport]` sem `SetLastError`; stripping de código gerenciado não remove o P/Invoke chamado (se remover, `link.xml`).

---

## 10. Contratos entre camadas

### 10.1 ShatterCore (contrato da biblioteca)
| Regra | Detalhe |
|---|---|
| Pureza | Não lê relógio, não cria threads, não tem singletons. E/S só em `ContentDB::LoadDirectory`, `ReadSaveFile`/`WriteSaveFile` (via `IFileIO`) |
| Entrada/saída | Funções recebem `const ContentDB&` e structs por valor/referência; devolvem structs. `ResolveHit` não altera os StatBlocks |
| Imutabilidade | `ContentDB` é imutável depois de `Finalize()`; leitura concorrente é segura |
| RNG | Só `Pcg32` recebido por parâmetro. `ResolveHit` consome **sempre 3** números (crítico, evasão, bloqueio) |
| Determinismo de ponto flutuante | Sem `-ffast-math`/`/fp:fast` (CMake garante, inclusive para a DLL). Em caminhos que afetam resultado, **só + − × ÷ e `std::sqrt`** (corretamente arredondados em IEEE-754). Proibido `pow/exp/log/sin` no simulador e no golpe; `x^1.5 = x·sqrt(x)` |
| Ordem estável | Iterar sempre `std::vector` em ordem do CSV/inserção; `unordered_map` só para lookup, **nunca** para iterar em código que afeta resultado |
| Números em texto | Parse e escrita de números independentes de locale: `std::from_chars`/`std::to_chars` (o Windows em pt-BR usa vírgula decimal em `strtod`/`printf`) |
| Texto | UTF-8 em `std::string`. Nenhum texto para o jogador; só IDs e chaves |
| IDs | `IsValidContentId`: minúsculas, `[a-z0-9_]`, segmentos com ponto, nunca renomeados |

### 10.2 Camada C# do jogo (Echoes.Core, Gameplay)
- É o **único** cliente do ShatterCore, e só por `Echoes.Interop`. Converte `string ↔ UTF-8`; IDs de conteúdo são `string` (ou um `struct ContentId` com comparação ordinal; **nunca** `ToLower`/cultura).
- Nenhuma constante de balanceamento em C# ou em prefab: tudo vem do `ContentDB` (inclusive `RulesConstants`).
- Só o `CombatSystem` chama `shatter_resolve_hit` e os efeitos; MonoBehaviours nunca mexem em vida diretamente.
- Tempo real → passo fixo antes de chegar ao core.
- C# idiomático na borda do jogo: exceções só para erro de programação (argumento inválido, versão errada da DLL); falhas esperadas (save corrompido, CSV inválido) viram resultado tipado (`Result`/status), nunca exceção.
- Sem alocação por quadro no passo de combate: structs, `NonAlloc`, listas reutilizadas, `ObjectPool`.

### 10.3 Cenas, prefabs e UI Toolkit
- Leem estado por propriedades dos serviços e eventos do `EventBus`; agem por métodos públicos dos serviços (`TryStartExpedition`, `EquipItem`, `CollectExpedition`).
- Não guardam estado de regra, não calculam números, não chamam o core.

### 10.4 Classes C# previstas (contrato com o Frontend Engineer)

| Tipo | Assembly / base | Responsabilidade |
|---|---|---|
| `GameRoot` | Core, `MonoBehaviour` | Ponto de entrada da cena `Boot`; ordem de inicialização dos serviços; descarte dos handles |
| `RulesService` | Core, classe C# | Dono do `ShatterDb`; carga do CSV; consultas de exibição (nome/ícone/tooltip de skill, afixo, item) |
| `SaveService` | Core | Dono do `ShatterSave`; `Load/Save`; autosave de 5 min; evento `LoadedFromBackup` |
| `ExpeditionService` | Core | `CanStart`, `TryStart`, previsão, simulação em `Task.Run`, `Collect`; evento `ExpeditionReady(Result)` |
| `PlatformService` (`IPlatformService`, `NullPlatformService`, `SteamPlatformService`) | Core | Steam: conquistas, hora do servidor, Rich Presence; implementação nula sem Steam |
| `EventBus` | Core | Barramento tipado e sem alocação (`Publish<T>(in T)`, `Subscribe<T>`): `EnemyKilled`, `ItemDropped`, `Hit`, `ExpeditionFinished`, `LevelUp` |
| `LocalizationService`, `SettingsService` | Core | Textos por chave (seção 7); `settings.json` |
| `CombatSystem` | Gameplay, classe C# (chamada pelo `GameRoot`) | Passo fixo 60 Hz, RNG da sessão, `ApplySkillHit`, ticks de efeitos, hitstop por entidade |
| `PoolService` | Gameplay | Pools (`ObjectPool<T>`) de projéteis, telegraphs, números de dano, VFX e itens no chão (limite de 300 projéteis) |
| `HeroController`, `EnemyController` | Gameplay, `MonoBehaviour` | Personagem jogável e inimigo: `CharacterController`/`NavMeshAgent`, `AttributeComponent`, `SkillComponent`; o inimigo acrescenta o `EnemyBrain` |
| `PlayerInputHandler` | Gameplay, `MonoBehaviour` | Input System (`Echoes.inputactions`: `Move`, `Aim`, `BasicAttack`, `Skill1..5`, `Dodge`, `Potion1..2`, `Inventory`, `PassiveTree`, `Map`) |
| `AttributeComponent` | Gameplay, `MonoBehaviour` | Espelha o `shatter_statblock` + efeitos + vida/recurso/barreira atuais; relê quando a revisão do core muda; eventos `LifeChanged`, `Died` |
| `SkillComponent` | Gameplay, `MonoBehaviour` | Barra de 6 habilidades, fases windup/impact/recovery, recargas (`EffectiveCooldown`), custo de recurso |
| `SkillBehavior` (+ `Cone`, `Projectile`, `Area`, `Dash`, `Self`, `Channel`, `Trap`) | Gameplay, classe abstrata | Forma espacial escolhida por `SkillShape`; só faz consultas de overlap e entrega alvos |
| `EnemyBrain` | Gameplay, `MonoBehaviour` | Máquina de estados parado → perseguir → telegraph → atacar → recuperar; chefes com tabela de padrões por fase |
| `Projectile` | Gameplay, `MonoBehaviour` | Projétil em pool |
| `FollowCamera` + `RenderSettingsAsset` | Presentation | Câmera 3/4 fixa (pitch 55°, yaw 45°, 42 m, suavização 7), sem rotação do jogador |
| `PresentationController` | Presentation, `MonoBehaviour` | Reage aos eventos do core: flash (`_HitFlash`), hitstop (`Animator.speed`), morte (`_Dissolve`), toca ações e VFX via `SkillPresentationSet`; nunca decide regra |
| `SkillPresentationSet` | Presentation, `ScriptableObject` | ID de habilidade → estado do Animator, frações de fase, prefab de VFX, âncora, som (dado de apresentação) |
| `AreaProfile` + `AreaVisuals` | Presentation, `ScriptableObject` + `MonoBehaviour` | Névoa, luz, ambiente e zoom por área; aplicado ao carregar a cena |
| `OcclusionFadeDriver` | Presentation, `MonoBehaviour` | Atualiza as globais de shader com a posição do herói para o fade de paredes |
| `TelegraphView` | Presentation, `MonoBehaviour` | Mesh plano de telegraph no chão, em pool, por forma e progresso |
| `AnimationEventRelay`, `LodDriver` | Presentation, `MonoBehaviour` | Recebe eventos de animação (VFX/som/passos); troca de LOD por distância ao herói (seção 17.1) |
| `HudController`, `ExpeditionScreen`, `ReportScreen`, `InventoryScreen` | UI, `MonoBehaviour` sobre `UIDocument` | Telas de HUD (vida, recurso, barra de habilidades, poções, Fervor, Cargas, Ouro), Ilsa, relatório do Tico e inventário |
| `LocLabel`, `DamageNumberLayer` | UI, elementos do UI Toolkit | Texto por chave; números de dano e barras de vida em pool |

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

### 13.1 ShatterCore (CMake, sem Unity, a cada commit)
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
| `test_golden.cpp` | Expedições de referência com seeds fixas comparadas com `tests/data/golden/*.txt` (o mesmo arquivo é usado no teste do Unity) |

### 13.2 Unity (Test Framework, a cada commit e noturno)

Testes em `Assets/Tests/EditMode` e `Assets/Tests/PlayMode` (asmdefs da seção 4.3). Nomes por categoria (`[Category("Interop")]` etc.) para filtrar na CLI.

| Teste | Modo | Cobre |
|---|---|---|
| `Interop.VersionAndLayout` | EditMode | `shatter_api_version` e o layout das structs batem com o C# |
| `Rules.LoadContent` | EditMode | `RulesService` carrega o CSV de `StreamingAssets/Data` sem erro |
| `Rules.GoldenExpedition` | EditMode | A DLL gera o **mesmo `resultHash`** do golden do CMake (pega diferença de flags e de ABI) |
| `Save.RoundTrip` | EditMode | O `SaveService` grava e lê numa pasta temporária real; checksum adulterado cai no backup |
| `Loc.*` | EditMode | Leitor de CSV (aspas, vírgulas, UTF-8), fallback de cultura, glifos pt-BR/es na fonte |
| `Presentation.Data` | EditMode | Todo `SkillPresentationSet` aponta para habilidades existentes no CSV, estados existentes no Controller e frações de fase em ordem |
| `Art.Budgets` | EditMode | Auditoria de assets (seção 17.3) |
| `Gameplay.FixedStep` | PlayMode | O acumulador executa o número certo de passos para FPS variados; mesmo resultado em 30, 60 e 144 FPS simulados |
| `Smoke` | PlayMode | Carrega Refúgio e Cripta, 60 s de bot, sem exceção nem erro no log |
| `Parity.*` (noturno) | PlayMode, `-batchmode -nographics` | Bot joga os encontros reais com a mesma política e seeds; compara XP/min, abates/min, dano recebido e poções/encontro com o simulador; tolerância 10% (5% no AA) |
| `Player.Smoke` | Build IL2CPP | Cena `Test/Smoke` em jogador: executa o golden e imprime o `resultHash` (seção 9.8) |

**Como rodar pela CLI** (sem abrir o editor; `UNITY_EDITOR_PATH` aponta para o executável da versão fixada):
```
"%UNITY_EDITOR_PATH%" -batchmode -nographics -projectPath EchoesOfTheShatter ^
   -runTests -testPlatform EditMode -testResults TestResults/editmode.xml -logFile -
"%UNITY_EDITOR_PATH%" -batchmode -nographics -projectPath EchoesOfTheShatter ^
   -runTests -testPlatform PlayMode -testResults TestResults/playmode.xml -logFile -
```
Notas: não passar `-quit` junto com `-runTests`; o código de saída é diferente de 0 se algum teste falhar; filtro por `-testCategory "Interop"` ou `-testFilter`. Verificação só de compilação: `-batchmode -nographics -quit -projectPath ... -logFile -` (erro de compilação = saída diferente de 0). **Confirmar na instalação** as opções da CLI da versão fixada.

---
## 14. CI (GitHub Actions)

| Job | Runner | Quando | Passos |
|---|---|---|---|
| `core-linux` | `ubuntu-latest` (GCC e Clang) | todo push/PR | `cmake -DSHATTER_WERROR=ON` → build → `ctest`; variante com `SHATTER_SANITIZE=ON` |
| `core-windows` | `windows-latest` (MSVC) | todo push/PR | mesmo, com MSVC (o compilador da DLL do jogo); gera `shattercore.dll` como artefato |
| `data` | `ubuntu-latest` | todo push/PR | `python3 tools/validate_data.py` + teste `test_content` sobre o CSV real |
| `bench` | `ubuntu-latest` | noturno | `SHATTER_BUILD_BENCH=ON`; falha se 12 h de expedição > 2 s |
| `unity-tests` | **self-hosted Windows** com o Unity instalado | todo push na `main` e PR | Confere que a DLL do repositório é a do artefato `core-windows` (versão e hash); EditMode e PlayMode pela CLI (13.2) |
| `unity-build` | self-hosted | todo push na `main` | Build Windows IL2CPP em batchmode (`-executeMethod Echoes.EditorTools.Build.Windows`) + `Player.Smoke` |
| `unity-nightly` | self-hosted com GPU | noturno | Paridade + Smoke longo + teste de desempenho da seção 18 + loot de 1 milhão |
| `steam-upload` | self-hosted | push na branch `release` | Build de release → `steamcmd` sobe para a branch **beta**; promover para default é manual no Steamworks |

Runner próprio para o Unity: a licença (Personal) é ativada na máquina, sem depender de ação de terceiros no workflow. Alternativa: imagens do GameCI em runner hospedado (exige ativação de licença por segredo; **decisão do orquestrador** se o custo de manter a máquina pesar). Versão visível no menu: `0.3.1-ea+<hash>` (injetada pelo CI em `PlayerSettings.bundleVersion` pelo script de build).

---

## 15. Desvios do plano (Godot → motor intermediário → Unity 6)

O plano original usava Godot 4 (seção 10). Uma revisão intermediária adotou outro motor (segunda coluna, mantida só como registro). Em 16/10/2026 o dono decidiu por **Unity 6 LTS com URP e C#** (`docs/08_decisoes_visual_3d.md`): ativos em texto e CLI para agentes, build e editor mais leves, referência visual feita em URP e custo.

| Plano (seção 10) | UE 5.8 (superado) | Agora (Unity 6) | Motivo / impacto |
|---|---|---|---|
| Godot 4, GDScript tipado | UE 5.8, C++ + Blueprint | Unity 6 LTS, C# + core C++17 em DLL | Decisão do dono; ativos em texto revisáveis por agentes |
| Regras como `RefCounted` puras | Biblioteca compilada por CMake e por módulo do motor | Biblioteca C++17 pura: estática no CMake e **DLL + API C** chamada por P/Invoke | Mesmo princípio, fronteira mais forte e testável sem editor; o custo novo é manter a API C estável (seção 9) |
| Renderer Compatibility (OpenGL) | Forward Shading + MSAA, sem Lumen/Nanite/VSM, materiais Unlit+Masked (pixel art 2D) | URP Forward + MSAA, SRP Batcher, sem GI em tempo real nem lightmaps, materiais Lit simples com luz pintada no albedo | Equivalente leve; o visual passou de pixel art 2D para 3D pintado; risco em GPU integrada e Deck → medir na F1 (seção 18) |
| Viewport 960×540, stretch viewport, nearest | `ScreenPercentage` + upscale nearest + viewport próprio de escala inteira (pixel-perfect) | Resolução nativa com MSAA; UI Toolkit com escala do painel por altura (seção 3.11) | A resolução interna fixa, o filtro nearest e a escala inteira saem junto com o pixel art (decisão 1) |
| 2D com Area2D | Sprites Paper2D em planos 3D, câmera ortográfica −30°/45° | Personagens 3D (SkinnedMeshRenderer) com `CharacterController`, câmera perspectiva estreita 55°/45°, consultas de overlap no plano XZ | Colisão e navegação nativas; troca de apresentação, regras intactas |
| Paper2D (plugin) | Fora, Niagara dentro | Nenhum plugin 2D; Particle System e Shader Graph nativos | Sem sprites; VFX nativo do Unity |
| InputMap | Enhanced Input | Input System (`Echoes.inputactions`) | Mesmo conceito de ação nomeada |
| GodotSteam (GDExtension) | OnlineSubsystemSteam + Steamworks SDK | `Steamworks.NET` atrás de `IPlatformService` | `getServerRealTime` → `SteamUtils.GetServerRealTime`; decisão registrada na seção 2 |
| `tr()` + CSV de tradução | String Tables + `.po` por `build_loc.py` | CSV lido em C# (`LocalizationService`) | A planilha continua a mesma; sem etapa de conversão |
| Resources `.tres` + `tools/import_tables.gd` | CSV lido em tempo de execução pelo `ContentDB` | Igual: o CSV em `StreamingAssets` é lido pela DLL (sem conversão); validação no CI por `Finalize()` + `validate_data.py` | Uma única fonte da verdade, igual nos testes e no jogo |
| EventBus por sinais | Delegates em subsistema | `EventBus` C# tipado e sem alocação | — |
| `_physics_process` 60 Hz | Acumulador de passo fixo no subsistema de combate | Acumulador de passo fixo 60 Hz no `CombatSystem` (sem `FixedUpdate`) | O tick do motor é variável |
| Hitstop por entidade | Timers congelados + `CustomTimeDilation` | Timers congelados no passo fixo + `Animator.speed = 0` e partículas pausadas por entidade | Nunca usa `Time.timeScale` |
| WorkerThreadPool | `UE::Tasks::Launch` | `Task.Run` com a DLL (só `shatter_db` e JSON atravessam threads) | — |
| GUT | Mini framework próprio + Automation Tests | Mini framework próprio (CMake) + Unity Test Framework (EditMode/PlayMode) pela CLI | Sem downloads extras |
| `use_custom_user_dir` → `%APPDATA%/EchoesOfTheShatter` | `%LOCALAPPDATA%\...\Saved\SaveGames` | `Application.persistentDataPath/saves` (`AppData\LocalLow` no Windows); Auto-Cloud em `WinAppDataLocalLow` | Padrão do Unity; **confirmar** a raiz no Steamworks |
| `Time.get_unix_time_from_system()` | `FDateTime::UtcNow().ToUnixTimestamp()` | `DateTimeOffset.UtcNow.ToUnixTimeSeconds()` | — |
| Sentry SDK para Godot | `sentry-unreal` ou CrashReportClient próprio | Sentry para Unity (opt-in) ou relatório de falha próprio — decidir na F3 | — |
| `tools/batch_sim.gd` | Executável `shattercore_bench` | Igual: `shattercore_bench` / modo lote no `bench/` (CSV de saída) | Roda sem o motor |
| Tamanho < 500 MB | Meta mantida, exigia desligar plugins | Meta mantida: remover pacotes sem uso, IL2CPP com stripping, compressão de texturas | Unity é mais leve que o motor anterior; medir na F1 |

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
| `shatter_c.h` | API C estável para P/Invoke (seção 9.2): handles opacos, status, buffers do chamador | `c_api/shatter_c.cpp` (+ `c_api/shatter_c.map`, exports no Linux) |
| `shatter.h` | Inclui tudo (C++) | — |

Mudanças nos headers depois da entrega do Tech Lead (adições em `save.h`, `expedition.h`, `character.h`, `rng.h` e a API C) estão registradas, com o motivo, em `docs/09_mudancas_contrato.md`.

Verificação: todo header compila sozinho com `g++ -std=c++17 -fsyntax-only -Wall -Wextra -Wpedantic -Wshadow -Wconversion` e com `clang++` (o CMake tem o alvo `shattercore_header_check`, que faz isso em todo build).

---

---

## 17. Pipeline de assets 3D (Blender → FBX → Unity)

A estrutura de pastas e os prefixos estão nas seções 4.2 e 4.4. Esta seção fixa o pipeline e os orçamentos por tipo de asset. Os números de arte (proporções, texel, pintura) são do `docs/03_design_system.md`; aqui ficam só os orçamentos técnicos.

### 17.1 Pipeline de importação

| Passo | Regra |
|---|---|
| Fontes | `art-src/` na raiz do repositório (`.blend`, pinturas, presets de exportação), no Git LFS, **fora** do projeto Unity. Só o exportado entra em `Assets/`. Arquivos `.blend` **não** são importados direto pelo Unity (exigiria o Blender instalado em cada máquina e no CI) |
| Formato | **FBX** (malhas, esqueletos, animações). glTF não é usado |
| Escala | Blender em metros, unidade 1.0; **1 unidade Unity = 1 m**. Cubo de 1 m deve importar com escala 1 e herói de 1,50 m (seção 3.1). Importador: Scale Factor 1, "Convert Units" ligado |
| Eixos | Y para cima, personagem olhando para **+Z** no Unity. Preset de exportação do Blender (Apply Scalings = "FBX Units Scale", frente e cima conforme o preset, transformações aplicadas) fixado em `art-src/export_presets/` depois de testar com um cubo e um esqueleto de teste: **confirmar na instalação** que a rotação importada é (0, 0, 0) e a escala 1, e registrar os valores |
| Transformações | Aplicadas (escala 1, rotação 0) antes de exportar; pivô nos pés (personagens) e no canto/centro de base da grade (módulos) |
| Rig | Generic, hierarquia e nomes de ossos iguais aos de `Rig_Humanoid_Chibi`; `root` na origem; ≤ 55 ossos (herói), ≤ 35 (inimigo), ≤ 100 (chefe), 4 influências por vértice no máximo; Optimize Game Objects ligado (expor só os sockets) |
| Animação | 30 fps autoral; um FBX por personagem com várias takes (ou um por clipe); sem root motion; frações de fase registradas no `SkillPresentationSet` |
| UVs | UV0 para o albedo pintado (sem sobreposição em personagens); sem segunda UV (sem lightmaps) |
| Normais e tangentes | Importar normais; **sem normal map** e sem cálculo de tangentes (economiza memória e tempo de importação) |
| LODs | `LODGroup` em personagens: LOD0 + LOD1 (≈ 50% dos triângulos) + LOD2 (≈ 25%); trocas a **18 m** e **32 m** do herói (ponto de partida a medir na F1). Como a câmera fica a ~42 m de tudo, o `LODGroup` por tamanho na tela quase não varia: o `LodDriver` usa `LODGroup.ForceLOD` por **distância ao herói**, atualizado a cada ~0,25 s. Cenário: LOD0 só para peças ≤ 1000 tri; LOD1 (≈ 50%) para peças acima de 1500 tri |
| Colisão | Cenário: **colisores simples** (`BoxCollider`, `CapsuleCollider`, `MeshCollider` convexo só quando indispensável) no prefab, nunca o mesh visual como colisor; um colisor de piso por sala em vez de um por tile. Personagens: só `CharacterController`; mesh sem colisor. Props decorativos pequenos: sem colisor |
| Navegação | `NavMeshSurface` (pacote AI Navigation) por cena de área, gerado a partir dos colisores simples; props só visuais não entram (layer própria) |
| Instâncias | Peças repetidas (chão, parede, pilar) como prefabs com materiais compartilhados e GPU Instancing; peças estáticas marcadas `Static` para Static Batching |
| Sombras | `ShadowCastingMode = Off` em cenário por padrão (3.6) |
| Materiais | Todo renderer usa um `M_` filho de um mestre em Shader Graph (3.5); material solto proibido |
| Texturas | sRGB no albedo, linear na máscara; Mipmap Streaming ligado; compressão: "High Quality" (BC7) em albedo de personagem, "Normal Quality" (BC1) em cenário e máscaras; `Read/Write` desligado |
| Checklist | A auditoria automática (17.3) roda no CI e reprova asset fora do orçamento |

### 17.2 Orçamento por tipo de asset

Triângulos (LOD0) e texturas. Os tamanhos máximos assumem a câmera da seção 3.2 (herói com ~155 px de altura em 1080p); a **densidade de texel** vem do `docs/03_design_system.md`. Metas iniciais, revisadas pela medição da F1.

| Tipo | Triângulos | Materiais | Texturas (por asset) | Observação |
|---|---|---|---|---|
| Herói (corpo + equipamento) | 7.000 a 10.000 | 1 (máx. 2) | 1024² albedo (BC7) + 512² máscara (BC1) | Variantes de cor por material e região B da máscara |
| Inimigo comum | 3.500 a 5.000 | 1 | 512² albedo + 256² máscara | Fixa o teto de 30 ativos. **Elite não tem malha própria**: usa a malha do comum com tinta (região B da máscara), halo e escala até ×1,15, só por material e parâmetros |
| Chefe | 15.000 a 25.000 | 1 a 2 | 2048² albedo num material, **ou** 2 materiais de 1024² + 512² máscara | |
| Peça modular de chão | 200 a 600 | 1 (kit) | Atlas do kit (abaixo) | |
| Parede, pilar, arco | 800 a 2.500 | 1 (kit) | Atlas do kit | |
| Estátua / prop de destaque | 3.000 a 5.000 | 1 | 512² a 1024² | Só 1 a 3 por sala |
| Prop pequeno (vaso, osso, caixão) | 100 a 800 | 1 (kit) | Atlas do kit | Sem colisor quando decorativo |
| Kit de área (atlas) | — | — | até 4 folhas de 2048² (albedo BC1) + 1 máscara de emissivo 1024² BC1 | Todas as peças da área compartilham as folhas |
| Textura de VFX | — | — | 256² a 512², canal único sempre que possível | Reutilizada entre sistemas |
| Ícones e UI | — | — | Segundo `docs/03_design_system.md` | Sem mipmap |

Sem normal map em nenhum tipo de asset. Teto de assets de uma área carregada: ≤ 120 MB no build (também garante carga < 3 s, RNF-04, e ajuda na meta de instalador < 500 MB; **confirmar na instalação** o tamanho base do player IL2CPP).

### 17.3 Auditoria automática

`Art.Budgets` (teste de EditMode) e um `AssetPostprocessor` de aviso na importação percorrem o `AssetDatabase` por pasta/prefixo e conferem triângulos do LOD0, número de ossos, número de materiais, tamanho máximo de textura, compressão, renderer de cenário com sombra projetada ligada e material fora dos mestres. Falha lista asset e limite. Os limites vêm da tabela 17.2, num `SO_ArtBudgets` (dado, não código).

---

## 18. Orçamentos de desempenho por cena (RNF-04)

Alvo: 60 FPS estáveis (quadro ≤ 16,6 ms) na Cripta com 30 inimigos ativos, e carga da área < 3 s. **Hardware de referência pendente (P-4 do `docs/02_requisitos.md`)**: até o dono indicar a máquina, assume-se como "PC de entrada" uma GPU de 4 GB do nível de uma GTX 1050 Ti/RX 570 (ou GPU integrada moderna), CPU de 4 núcleos, 8 GB de RAM, 1080p. O Steam Deck é medido como alvo próprio. Os números abaixo são **metas iniciais a validar na F1** com Profiler, Frame Debugger e Stats, não resultados medidos.

| Recurso (cena de combate, pico) | PC de entrada (1080p, MSAA 4x) | Steam Deck (1280×800, MSAA 2x) |
|---|---|---|
| Tempo de quadro | ≤ 16,6 ms | ≤ 16,6 ms (limite de 60 FPS) |
| Main thread (scripts + animação) | ≤ 6 ms | ≤ 7 ms |
| Render thread | ≤ 6 ms | ≤ 6 ms |
| GPU | ≤ 13 ms | ≤ 14 ms |
| Batches (draw calls, no Frame Debugger) | ≤ 1.200 | ≤ 800 |
| SetPass calls (com SRP Batcher) | ≤ 200 | ≤ 120 |
| Triângulos visíveis (passe principal) | ≤ 1,2 M | ≤ 600 mil |
| Triângulos no passe de sombra | ≤ 200 mil | ≤ 100 mil (ou blob, sem passe) |
| `SkinnedMeshRenderer` ativos | ≤ 40 (30 inimigos + herói + chefe/aliados) | ≤ 40, com LOD1 forçado nos inimigos distantes |
| Ossos atualizados por quadro | ≤ 1.600 | ≤ 1.200 |
| Luzes | 1 direcional + ≤ 4 pontuais sem sombra | 1 direcional + ≤ 2 pontuais |
| Cascatas de sombra | 2 | 1 ou blob |
| Partículas ativas | ≤ 3.000 | ≤ 1.500 |
| `ParticleSystem` ativos | ≤ 40 | ≤ 24 |
| Área de tela com translucência (pico) | ≤ 25% | ≤ 15% |
| Memória de textura (`streamingMipmapsMemoryBudget`) | ≤ 1,5 GB | ≤ 1 GB |
| VRAM total | ≤ 2,5 GB | ≤ 2 GB (memória compartilhada com a CPU) |
| RAM do processo | ≤ 3 GB | ≤ 3 GB |
| Alocação gerenciada por quadro (GC) no combate | 0 B em regime | 0 B em regime |
| Assets carregados por área | ≤ 120 MB no build | ≤ 120 MB no build |
| Carga da área | < 3 s | < 3 s (leitura de SSD; medir em cartão SD) |

Meta de quadro: 60 FPS em PC e Deck. Piso aceitável no Deck: **40 FPS (modo de 40 Hz da tela)**, a adotar só se a medição da F1 mostrar que o orçamento acima não fecha; nesse caso o limite de quadro vira 25 ms e a decisão volta ao orquestrador. Escalabilidade (níveis de qualidade, cada um com seu URP Asset): Alto (PC): MSAA 4x, 2 cascatas; Médio (padrão no Deck): MSAA 2x, 1 cascata ou blob; Baixo: MSAA off, blob, partículas ×0,5. A opção persiste em `settings.json` (seção 8).

Como medir e proteger: (1) `unity-nightly` roda um teste de PlayMode de desempenho (bot do `Smoke` na Cripta por 60 s com 30 inimigos, em runner com GPU) e falha se o p95 do quadro passar de 16,6 ms ou algum limite da tabela estourar; usa `FrameTimingManager`/`ProfilerRecorder` e, se valer a pena, o pacote Performance Testing (**confirmar na instalação** o que está disponível); (2) cada mudança de arte grande passa pela auditoria 17.3; (3) o Performance Engineer inclui o Unity em `docs/12_performance.md` (PC de entrada e Deck, frio e quente), com Development Build e Autoconnect Profiler. Se um limite estourar, a ordem de corte é: partículas, sombras, MSAA, triângulos de props, nunca a regra do jogo.
