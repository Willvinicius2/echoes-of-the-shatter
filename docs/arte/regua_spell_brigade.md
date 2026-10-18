# Régua técnica dos modelos do Spell Brigade (referência para Echoes of the Shatter)

Status: medição feita em 16/10/2026. Os dados são **só referência**: nenhum arquivo do Spell Brigade foi copiado para este repositório. Esta página é texto; nada aqui é asset final.

Fonte (somente leitura): `D:\openclaude\spell-brigade-re\unity-project\ExportedProject\Assets`, exportação do AssetRipper de um projeto Unity 6000.0.74 com URP.
Amostra: as 467 malhas de `Mesh/` foram lidas por script (campos `m_SubMeshes`, `m_VertexData`, `m_LocalAABB`, `m_BindPose`); os materiais (7.406), os controladores de animação (394) e os prefabs de herói, inimigo e chefe foram cruzados por GUID. Os 17 heróis jogáveis, os inimigos e os chefes foram medidos por inteiro, não por amostra.

## 0. Limites da medição (ler antes de usar os números)

- **Triângulos** = soma de `indexCount / 3` de todos os submeshes; **vértices** = `m_VertexCount` do buffer. É o LOD0 (os personagens não têm LOD; só as árvores têm LOD0/1/2).
- **Tamanho** = `m_LocalAABB` da malha, em unidades do modelo. Inclui chapéu, cajado, cauda e outros apêndices fundidos no mesmo mesh. Para chefes, a escala do prefab foi aplicada (Hydra ×0,01; Squid ×1,6). Presume-se 1 unidade = 1 m (não confirmado).
- **Ossos** = tamanho de `m_BindPose`. Conta ossos de IK, de pano/cabelo, dedos e props. Não é o número de ossos que deformam de fato. Inimigos de "animação baked" (seção 5) têm bind pose guardado, mas **não usam esqueleto em runtime**.
- **Proporção cabeça/corpo é inferência**: não há nomes de ossos no mesh; os nomes vieram do `m_Bones` do prefab cruzado com a bind pose. A "junta da cabeça" é a origem do osso `Head`, não o topo do crânio. A tabela dá a fração da altura **acima** dessa junta (cabeça + chapéu/cabelo/acessório): é um limite superior da cabeça.
- Os shaders vieram do AssetRipper como esqueleto (`DummyShaderTextExporter`): temos **lista de propriedades**, não o código HLSL. Afirmações sobre "como o rim é calculado" são inferidas pelos nomes e valores.
- Não foi medido: contagem de pixels de textura por área de UV, densidade de texel efetiva, tempo de CPU de animação, pesos de pele por vértice.

## 1. Heróis (17 jogáveis, malha `*_0` = skin base)

Todos têm 1 `SkinnedMeshRenderer`, 1 submesh, 1 material (`Shader Graphs/Base`) e um único controlador de 2 clipes (seção 6).

| Herói | Tri | Vért. | Ossos | Altura (m) | Largura (m) | Prof. (m) | Acima da junta da cabeça* | Quadril/altura** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BellMage | 5.348 | 3.892 | 72 | 2,08 | 2,16 | 1,14 | 51% | 24% |
| BirdMage | 4.772 | 3.530 | 79 | 1,81 | 1,76 | 1,32 | 43% | 37% |
| Campanelli | 3.794 | 2.547 | 82 | 1,81 | 2,05 | 1,49 | 30% | 27% |
| FluteMage | 4.836 | 3.365 | 59 | 1,93 | 0,97 | 1,25 | 39% | 36% |
| Hatty | 2.670 | 1.858 | 44 | 2,61 | 1,32 | 0,62 | 56% | 22% |
| IllusionMage | 4.896 | 3.336 | 58 | 2,06 | 1,37 | 1,80 | 41% | 31% |
| KeyMage | 3.406 | 2.600 | 51 | 1,95 | 1,83 | 1,37 | 44% | 31% |
| Ludwig | 3.616 | 2.492 | 46 | 2,12 | 1,63 | 2,12 | 47% | 28% |
| MoonMage | 2.622 | 2.055 | 37 | 1,94 | 1,90 | 0,89 | 44% | 29% |
| PlantMage | 5.650 | 4.396 | 67 | 2,30 | 1,34 | 1,11 | 56% | 25% |
| PotatoMage | 3.414 | 2.385 | 57 | 1,60 | 1,16 | 0,82 | 48% | 29% |
| Reginald | 2.504 | 1.743 | 46 | 1,51 | 1,70 | 0,84 | 25% | 39% |
| Smithy | 4.540 | 3.432 | 58 | 2,26 | 2,08 | 1,14 | 41% | 33% |
| StarMage | 3.406 | 2.310 | 57 | 1,94 | 2,80 | 1,29 | 41% | 28% |
| SunMage | 2.704 | 1.870 | 37 | 1,91 | 1,43 | 0,61 | 39% | 32% |
| VampireMage | 3.922 | 2.572 | 65 | 1,83 | 1,24 | 0,92 | 20% | 32% |
| WizardKing | 4.200 | 2.866 | 49 | 1,95 | 2,49 | 0,91 | 36% | 34% |

\* (altura - Y da junta da cabeça) / altura. \*\* Y do osso `Pelvis` / altura. Ambos inferidos (seção 0).

Resumo dos 17 heróis (skin base):

| Métrica | Mín. | Mediana | Média | Máx. |
|---|---:|---:|---:|---:|
| Triângulos | 2.504 | **3.794** | 3.900 | 5.650 |
| Vértices | 1.743 | 2.572 | 2.779 | 4.396 |
| Ossos (bind pose) | 37 | **57** | 57 | 82 |
| Altura (m) | 1,51 | 1,94 | 2,00 | 2,61 |
| Largura (m) | 0,97 | 1,70 | 1,70 | 2,80 |

Observações:
- Razão vértices/triângulos ≈ 0,71 (sombreamento suave, poucas quebras de UV/normal).
- **Skins** (124 malhas `*_Skin_*`): skins comuns 2.724 a 8.670 tri (mediana 4.836; a de 8.670 é a SunMage_Skin_4, com 154 ossos e 4 submeshes, exceção); skins "Sketchy" 5.008 a 11.316 tri (mediana 7.642), perto de 2× a base. O teto do herói base é ~5,7 mil.
- Corpo **chibi**: a fração acima da junta da cabeça tem mediana ≈ 41% da altura (20% a 56%, com chapéus e apêndices grandes empurrando para cima). Leitura: cabeça + chapéu ocupa cerca de 35% a 50% da altura total (≈ 2 a 3 cabeças de altura). Quadril a ~22% a 39% da altura: pernas curtas e grossas, pés no nível do chão (osso `Foot` a 0,03 a 0,10 m).
- Ossos extras comuns: IK de pé/joelho, 3 a 5 ossos de rabo/cabelo/pano, 8 a 10 ossos por mão (dedos e polegar), 10+ ossos de acessórios (sinos, pavios). Exemplo BellMage (72): 8 de perna + 4 de IK, ~20 de braço/mão, 20 de sinos, 10 de cabeça/cabelo/pavio, ~8 de tronco.
- Existe variante "BigHead" (prefab `*_SkinBigHead`) que só escala o osso da cabeça (valores 2,0/1,8/2,0 vistos em BellMage): a cabeça é um osso isolado, o que permite o efeito sem outra malha.
- Escala em jogo: prefab do herói com escala 1 na raiz; sem colisor na malha. Só 1 renderer do herói projeta sombra (os ~48 outros renderers do prefab são VFX com `CastShadows = 0`).

## 2. Inimigos comuns, elites e mini-chefe

| Malha | Papel | Tri | Vért. | Ossos (bind pose) | Altura (m) | Larg. (m) | Prof. (m) | Animação |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Crabling | enxame | 284 | 204 | 14 | 0,67 | 0,80 | 0,86 | baked (25 quadros) |
| BabyWorm | enxame | 421 | 303 | 10 | 0,84 | 0,49 | 1,36 | baked (64 q) |
| FleshCrab | enxame | 450 | 354 | 22 | 0,84 | 1,11 | 1,36 | baked (40 q) |
| BabyWormFast | enxame | 463 | 332 | 10 | 0,93 | 0,49 | 1,36 | baked |
| ExplodingTick | enxame | 592 | 391 | 23 | 2,46 | 1,15 | 1,36 | baked (32 q) |
| Tripod | comum | 600 | 447 | 23 | 1,42 | 1,31 | 1,54 | não verif. |
| Spitter | atirador | 630 | 470 | 32 | 1,30 | 1,24 | 1,80 | não verif. |
| TeethyWorm | comum | 782 | 550 | 11 | 1,69 | 1,07 | 2,57 | baked |
| ExplodingTickFast | comum | 796 | 519 | 29 | 1,78 | 1,28 | 2,16 | baked |
| TeethyWormFast | comum | 826 | 580 | 11 | 1,89 | 1,07 | 2,57 | baked (64 q) |
| Bouncer | comum | 911 | 637 | 12 | 1,57 | 1,93 | 1,93 | não verif. |
| Snipjaw | atirador | 922 | 695 | 35 | 1,63 | 1,29 | 1,91 | não verif. |
| StaticShooter | torre | 950 | 647 | 19 | 2,85 | 1,55 | 1,54 | esqueleto, 4 estados |
| Minion (Hydra) | adds | 1.084 | 662 | 12 | 2,63 | 2,74 | 2,83 | esqueleto |
| StinkBug | comum | 1.296 | 819 | 27 | 1,51 | 1,03 | 1,83 | não verif. |
| PregnantCrab | comum | 1.296 | 835 | 24 | 1,43 | 1,81 | 2,58 | esqueleto |
| SneakyBug | comum | 1.604 | 1.195 | 33 | 1,58 | 1,42 | 2,89 | esqueleto |
| Mole | comum | 1.676 | 1.280 | 33 | 1,21 | 1,06 | 2,28 | esqueleto |
| ShieldCrab | comum | 1.841 | 1.387 | 35 | 1,81 | 2,49 | 3,28 | baked (49 q) |
| Spawner | gerador | 2.124 | 1.342 | 59 | 3,67 | 6,74 | 3,33 | esqueleto |
| Buffer | suporte | 2.368 | 1.640 | 43 | 1,82 | 3,45 | 2,51 | esqueleto, 2 camadas (corpo/braços) |
| BufferFast | suporte | 2.904 | 2.044 | 45 | 1,97 | 3,81 | 2,52 | esqueleto |
| TeethyWormElite | elite | 2.593 | 1.678 | 29 | 3,26 | 2,68 | 4,41 | esqueleto |
| ExplodingTickElite | elite | 2.672 | 1.773 | 35 | 4,79 | 2,50 | 3,38 | esqueleto |
| BufferElite | elite | 4.892 | 3.578 | 72 | 3,65 | 4,35 | 3,75 | esqueleto |
| Hoarder | mini-chefe | 4.126 | 2.716 | 55 | 3,32 | 2,73 | 1,96 | esqueleto, 2 materiais |
| Crabladon | mini-chefe | 2.458 | 2.119 | 39 | 2,55 | 4,14 | 4,44 | baked (97 q) |

Resumo dos 22 inimigos comuns/enxame (sem elites, Hoarder e Crabladon): mediana ≈ **0,9 mil tri**, máximo 2,9 mil (BufferFast); vértices 204 a 2.044. **Elites têm malha própria** (2,6 a 4,9 mil tri), 2 a 6 vezes a versão comum (diferente do plano do Echoes, que usa a malha do comum com tinta).

Notas:
- Cada família tem rig próprio (sem rig compartilhado como o `Rig_Humanoid_Chibi` do Echoes). Eles têm 3 variantes de velocidade/elite por família (comum / Fast / Elite) com malhas ligeiramente distintas.
- Tamanhos em jogo variam de 0,7 m (Crabling) a 3,7 m (Spawner); inimigos comuns ficam em 1,2 a 2,0 m de altura e 1 a 4 m de comprimento: o corpo é largo e baixo, legível de cima na câmera 3/4.

## 3. Chefes

| Chefe (malha) | Tri | Vért. | Ossos | Tamanho em jogo (m) A × L × P | Material | Textura de albedo | Clipes |
|---|---:|---:|---:|---|---|---|---:|
| Hydra (`Hydra`) | 9.812 | 6.307 | 76 | 6,0 × 8,2 × 12,0 (escala ×0,01 no prefab) | 1 (`Base`) | 2048² + emissivo 2048² + "dark" 2048² | 19 estados |
| Toad (`Toad`) | 8.100 | 5.497 | 65 | 4,4 × 3,7 × 3,9 | 1 (`Base`) | 2048² + normal 2048² + emissivo 2048² + dark 2048² | 19 estados |
| Squid (`Boss`) | 7.152 | 4.500 | 111 | 6,1 × 5,7 × 8,1 (escala ×1,6) | 1 (`Base`) | 2048² + emissivo 2048² + dark 2048² | ~18 estados (3 camadas: corpo, tentáculos de trás e da frente) + 3 de ataque |

Notas:
- O Squid divide o corpo em 3 conjuntos de animação (corpo, tentáculos de trás e de frente), por isso os 111 ossos. Boa referência para chefe com "membros" independentes.
- Peças auxiliares dos chefes são malhas separadas e minúsculas: `Hydra_Spike` 110 tri, `HydraPiece` 56, `HydraBeam` 408 (feixe de 19 m), `ToadTongue` 430, `SquidMissile` 692 (13 ossos).
- A Hydra tem uma malha só para as 3 fases (1, 2 e 3 cabeças), animada por clipes (`Idle1Head`, `Idle2Heads`, `Idle3Heads`...); o AABB cru da malha é 824 × 598 × 1.201 por causa da importação em centímetros.
- Teto dos 3 chefes: 9,8 mil tri e 111 ossos; nenhum se aproxima de 15 mil.

## 4. Materiais, shaders e texturas

### 4.1 Personagens (herói, chefe, inimigo esqueletal)

- **Shader principal: `Shader Graphs/Base`** (URP, Shader Graph, opaco, `_Cull = 2`, `ZWrite = 1`, `_Surface = 0`, `_ReceiveShadows = 1`, `_CastShadows = 1`). 127 materiais usam esse shader.
- Variantes por finalidade: `SketchySkin` (skin "rabisco", textura única, sem normal), `MagicGold` (skin dourada: ruído de brilho + `EdgeColor` HDR + fresnel), `BaseDisolve` (decoy de IllusionMage: mapa de dissolução), `GhostSkin`/`PlayerGhost`, `BaseEliteExplodingTick` (dissolve emissivo), `CrystalTrail` (cristais das skins Prestige), `BakedVertexAnimation_Lit` (inimigos de enxame, seção 5).
- **Propriedades do `Base`** (do esqueleto do shader):

| Grupo | Propriedades | Valores típicos |
|---|---|---|
| Albedo | `_Color` (textura 2D), `_DarkColor` (variante "corrompida") | herói: mesma textura nos dois |
| Normal | `_Normal`, `_NormalIntensity` | normal opcional (presente em ~15% dos heróis: BellMage, PotatoMage, Smithy Demon, Reginald Skin 3/Prestige); 1024² ou 2048² |
| **Rim/fresnel** | `_FresnelStrength`, `_FresnelBlend`, `_FresnelSmoothStepRange` (x,y) | força **2,5** (2,51 a 3,9), mistura 0,5, faixa smoothstep **(0,2; 0,05)**, ou (0,3; 0,05) em alguns; rim de borda dura (smoothstep estreito), não suave |
| Emissão | `_Emmision` (textura), `_Emmision_color` (HDR), `_Emmision_intensity` | 0 na skin base; 512² a 2048² nas skins especiais e nos inimigos |
| Acerto | `_HitFlash` (liga/desliga), `_HitColor` | cor de acerto rosada-clara (0,60; 0,35; 0,39) |
| Congelamento | `_FreezeFresnelStrength`, `_FreezeFresnelFactor`, `_FreezeContrast` | fresnel invertido + contraste para efeito de gelo |
| "Dark world" | `_DarkCorruption`, `_DarkGlow` (HDR roxo-azul 0,09/0/1), `_DarkGlowNoiseTiling/AnimateSpeed`, `_DarkSmoothStep` (0,05; 0,2), `_DarkFresnelStrenght`, `_DarkEmmision` | cada inimigo/chefe tem textura `*_dark_em` própria |
| Ruído auxiliar | duas texturas anônimas (`Noise_023` 1024², `Tx_Noise_36` 512²) | usadas no brilho "dark" |

- **Contorno (outline): não existe.** Nenhum shader do projeto (exceto TextMeshPro) tem passe de contorno nem propriedade com "outline". A leitura da silhueta vem do rim (fresnel de borda dura), da cor saturada do albedo pintado e da sombra no chão.
- **Rampa de toon (cel): não há textura de rampa.** Os shaders não declaram `_Ramp`. Alguns materiais herdados trazem `_Cellshading_intensity = 0,65` (SketchySkin e alguns Base) mas a propriedade não existe no shader atual (resto de versão antiga). O visual "cel" parece vir do **albedo pintado à mão com sombras já assadas** + iluminação URP simples + fresnel duro. Inferência; não confirmada por falta do HLSL.
- Cor base: `_BaseColor`/`_Color` é um **multiplicador de tinta** (ex.: BellMage rosa-lilás 0,89/0,69/0,82; BirdMage verde-limão 0,96/1,0/0,59), usado para variar skins com a mesma textura.

### 4.2 Texturas de personagem

| Item | Valor encontrado |
|---|---|
| Albedo do herói | **2048²** em 100% dos heróis (um atlas só, 1 material). Importação com `maxTextureSize 2048`, `textureCompression 2` (alta qualidade), sem crunch, mipmap ligado, sRGB |
| Normal do herói | opcional, 1024² (às vezes 2048²) |
| Emissivo do herói | só em skins especiais: 1024² a 2048² |
| Albedo de inimigo comum esqueletal | 1024² (Buffer, BufferElite, TeethyWormElite, BufferFast) ou 2048² (Mole, Spawner, Hoarder, PregnantCrab) |
| Albedo de inimigo de enxame (baked) | 512² (Crabling, BabyWormFast, TeethyWormFast), 1024² (BabyWorm) ou 2048² (Tick, FleshCrab, Crabladon) |
| Albedo de chefe | 2048² (Hydra, Squid) + emissivo 2048² + textura "dark" 2048² |
| Texturas por personagem | 1 albedo + 0 a 1 normal + 0 a 2 emissivas (normal + "dark") |
| Ruído compartilhado | 2 texturas de ruído (1024² e 512²) iguais para todos |

### 4.3 Cenário

- **Shader principal: URP Lit padrão** (`Universal Render Pipeline/Lit`) nas rochas, muros, pilares, arcos e tijolos; `Shader Graphs/Base` nos props quebráveis (cercas); `Shader Graphs/Bushes` (vento + `_fresnel`, `_Leafshadow`, `_Alpha_Clip`) nas árvores e arbustos; `Shader Graphs/Grass` (vento, `_Intensity`, `_Speed`, recorte alfa 0,5) na grama e flores; `Shader Graphs/Ground`/`GroundPatch` (mistura de 2 texturas com ruído) no chão.
- Texturas de cenário: **atlas de 2048²** (`World1 Additional props_b` + normal 2048², todos os muros/pilares/arcos/tijolos/pisos compartilham); rochas `world1_rocks_mossy_b` 2048² + normal 1024²; árvore 512²; grama/flor 128² a 256².
- Sombras: no cenário de teste (VerdantMeadows) **rochas, muros e árvores projetam sombra (`CastShadows = 1`); grama e flores não**. Isso é o contrário da decisão do Echoes (só personagens projetam).
- LOD só nas árvores: `FirTree1` 320 / 136 / 77 tri (100% / 43% / 24%); `FirTree2` 278 / 150 / 49; `FirTree3` 102 / 68 / 34.

| Prop de cenário | Tri | Tamanho (m) A × L × P |
|---|---:|---|
| World1Tile1 (piso modular) | 13 | 0,13 × 0,87 × 0,87 |
| World1Brick1 | 32 | 0,41 × 0,84 × 0,47 |
| World1Pillar | 128 | 1,87 × 0,93 × 0,94 |
| World1Rock1 (rocha grande) | 231 | 3,55 × 6,15 × 5,62 |
| World1Wall1 | 290 | 2,32 × 3,55 × 0,44 |
| Vase | 454 | 0,76 × 0,40 × 0,40 |
| Tree1 | 544 | 6,00 × 2,22 × 1,77 |
| World4Coral1 | 642 | 3,05 × 1,21 × 0,75 |
| World2Statue | 962 | 8,11 × 4,09 × 3,36 |
| Pumpkin1 | 984 | 0,86 × 0,73 × 0,70 |
| Fence1 | 1.270 | 1,36 × 2,84 × 0,48 |
| CrablodonStatue | 2.718 | 3,22 × 3,64 × 3,96 |
| Pillar.001 | 2.846 | 4,41 × 1,27 × 1,26 |
| Chapel (peça de destaque) | 6.588 | 3,84 × 1,13 × 1,29 |

Rochas e pilares têm dezenas a poucas centenas de triângulos: o volume vem da textura (atlas pintado) e do normal map, não da geometria.

## 5. Animação baked (VAT) nos inimigos de enxame

Nove inimigos (BabyWorm, BabyWormFast, TeethyWormFast, Crabling, FleshCrab, ExplodingTick, ExplodingTickFast, ShieldCrab e o mini-chefe Crabladon) usam `BakedVertexAnimation_Lit`: a animação é uma textura onde cada coluna é um vértice e cada linha um quadro. **Sem esqueleto, sem Animator em custo de CPU.**

| Inimigo | Quadros | Framerate | Duração do laço | Vértices |
|---|---:|---:|---:|---:|
| Crabling | 25 | 90 | 0,28 s | 204 |
| ExplodingTick | 32 | 80 | 0,40 s | 391 |
| FleshCrab | 40 | 100 | 0,40 s | 354 |
| TeethyWormFast | 64 | 70 | 0,91 s | 580 |
| BabyWorm | 64 | 60 | 1,07 s | 303 |
| ShieldCrab | 49 | n/v | n/v | 1.387 |
| Crabladon | 97 | 90 | 1,08 s | 2.119 |

Textura de animação = largura igual ao número de vértices (de 204 a 2.119 px), altura igual aos quadros (25 a 97): é minúscula. Só funciona para laços curtos (mover). Ataques e mortes desses inimigos são feitos por escala/shader/VFX.

## 6. Clipes de animação

### 6.1 Heróis: 2 clipes

Todos os 17 heróis têm um controlador com **apenas Idle e Run**, sem camadas extras. Golpes e feitiços não têm animação de corpo (efeito sai por VFX/código).

| Clipe | Duração típica | Observações |
|---|---|---|
| Idle | **0,98 a 1,0 s** (extremos: KeyMage 0,70 s, SunMage 0,80 s, Reginald 1,27 s, WizardKing 2,0 s) | laço |
| Run/Move | **0,52 a 0,53 s** (extremos: Smithy 0,60 s, FluteMage 1,33 s) | laço; `speed` do estado 1,0 a 1,2 (em geral 1,1) |
| Extras raros | FluteMage: 4 clipes de música (3 a 8 s); PotatoMage: `eyes` (9,85 s); Hatty/SunMage/StarMage: clipes de skin Prestige (1 a 4 s) | opcionais, por skin |

Taxa de amostragem 60 quadros/s (59,94). Controlador de herói fantasma: Idle 1,5 s, Run 0,83 s, Spawn 2,0 s, Despawn 0,5 s.

### 6.2 Inimigos esqueletais

| Tipo | Clipes (nome: duração) |
|---|---|
| Buffer (suporte) | move 0,53 s, idle 0,53 s, heal 1,07 s (corpo e braços em clipes separados) |
| BufferElite | move inferior 1,0 s, move superior 1,0 s, heal 1,17 s, heal_effects 1,33 s |
| Mole | Move 1,33 s, ChargeAnticipation 2,0 s, Charge, Dive 0,83 s, Impact 0,67 s, Idle 1,0 s |
| StaticShooter | spawn 1,0 s, shoot_telegraph 1,0 s, shoot 1,0 s, idle 1,0 s |
| SneakyBug | hide 0,33 s, hidden 0,33 s, attack 0,42 s |
| Spawner | move 2,0 s, pulse 2,33 s, egg 0,5 s, grow 4,5 s |
| Hoarder (mini-chefe) | idle 0,60 s, run 0,70 s + 11 clipes de tamanho do orbe (0 a 0,17 s) |
| TeethyWormElite | Move 2,0 s |
| ExplodingTickElite | move 2,0 s (×1,2), 8 clipes de dano progressivo (0,53 a 0,62 s e um de 4,5 s) |

Padrão: laço de movimento de 0,5 a 2,0 s; telegráfico explícito de **0,33 a 2,0 s** (anticipation/charge) antes do golpe; ataque em 0,4 a 1,0 s.

### 6.3 Chefes

| Chefe | Nº de clipes | Exemplos e durações |
|---|---:|---|
| Hydra | 19 estados | Idle (laço 1,0 s) por fase; Swipe 12,0 s (velocidade 1,25 a 1,75); NegativeSpace 8 a 11 s; Spike 4,0 s; Transition (nova cabeça) 6,3 s; Healing 1,0 s; Spawn 0,55 s; Dying 6,0 s |
| Toad | 19 estados | TornadoCharge 0,93 s + Tornado 0,82 s; PushCharge 1,75 s + Push 1,0 s (laço); DiveTongueCharge 1,0 s + DiveTongue 1,0 s; Dive 0,83 s; DiveImpact 0,83 s; PullCharge 1,75 s + Pull 1,0 s; Ascend/Land 1,33 s; Hit 1,33 s; Flying 1,33 s (laço); Dying 5,17 s |
| Squid | ~18 estados em 3 camadas + 3 de ataque | move 1,67 s (×1,2); Pillar Attack 1,67 s; Homing Projectile 2,33 s; Bullet Hell Charge 1,0 s + Attack 1,67 s (laço); stagger 1,67 s; staggered 1,0 a 1,67 s; defeated 5,0 s; attack_begin 1,5 s, attack_move 0,33 s, attack_end 3,0 s |

Padrão de chefe: todo golpe tem **par Charge + Ação** (carga 0,9 a 1,75 s, ação 0,8 a 1,0 s); morte de 5 a 6 s; Hit/stagger de ~1,3 a 1,7 s; 18 a 19 clipes por chefe. Taxa 60 quadros/s.

## 7. Comparação com os orçamentos do Echoes (`docs/tecnico/04_arquitetura.md`)

Os orçamentos por tipo de asset estão na seção 17.2; a seção 18 traz os totais por cena e por `SkinnedMeshRenderer`. Compararam-se as duas.

| Item | Echoes (meta do 04) | Spell Brigade (medido) | Leitura |
|---|---|---|---|
| Herói, triângulos | 7.000 a 10.000 | 2.504 a 5.650 (mediana 3.794) | O piso do Echoes já passa do teto do SB: **1,2× a 4× mais denso**. Cabe no orçamento de cena, mas o estilo SB não exige essa densidade |
| Herói, ossos | ≤ 55 | 37 a 82 (mediana 57) | ≤ 55 fica na mediana. Os 55 do Echoes precisam contar só ossos de deformação; IK e dedos do SB inflam a contagem deles |
| Herói, materiais | 1 (máx. 2) | 1 | igual |
| Herói, textura | 1024² albedo (BC7) + 512² máscara (BC1), sem normal | 2048² albedo (+ normal 1024² em parte) | Echoes usa 1/4 dos pixels e não tem normal; ver recomendação 6 |
| Inimigo comum, triângulos | 3.500 a 5.000 | mediana ~900; máx. 2.900 (esqueletal) | Echoes **4× a 10× mais denso** no enxame. É o maior desvio |
| Inimigo, ossos | ≤ 35 | esqueletais 12 a 59 (mediana ~33); enxame baked: 0 ossos em runtime | ≤ 35 coincide com o SB esqueletal |
| Inimigo, textura | 512² albedo + 256² máscara | 512² a 2048² (mediana 1024²–2048² nos esqueletais) | Echoes mais econômico |
| Elite | sem malha própria (tinta + halo + escala ×1,15) | malha própria 2.593 a 4.892 tri | decisão do Echoes mais barata; SB gasta modelo novo |
| Chefe, triângulos | 15.000 a 25.000 | 7.152 a 9.812 | Echoes **1,5× a 3,5× mais denso** |
| Chefe, ossos | ≤ 100 | 65 a 111 | coincide (o Squid chega a 111 com 3 conjuntos) |
| Chefe, textura | 2048² (ou 2×1024² + máscara) | 2048² albedo + 2048² emissivo + 2048² dark | alinhado |
| Peça modular de chão | 200 a 600 | 13 a ~290 | Echoes mais folgado |
| Parede/pilar/arco | 800 a 2.500 | 128 a 290 (muro/pilar); chapéu de destaque 2.846 a 6.588 | idem |
| Prop pequeno | 100 a 800 | 32 a 984 | compatível |
| Sombra de cenário | só personagens projetam | rochas/muros/árvores projetam | Echoes mais econômico |
| Cenário, textura | até 4 folhas 2048² BC1 por kit | atlas 2048² + normal 2048² por kit, rochas 2048² | compatível |
| Animação do herói | (golpe e conjuração compartilhados via `Rig_Humanoid_Chibi`) | só Idle + Run | ver recomendação 8 |

Total por cena (seção 18): 30 inimigos × 4.250 tri médios ≈ 128 mil + herói 8,5 mil + chefe 20 mil ≈ 157 mil tri de personagem, bem abaixo de 1,2 M. Ossos: 30 × 35 + 55 + 100 ≈ 1.205, dentro de 1.600 (PC) e **no limite de 1.200 do Steam Deck**; com inimigos de enxame abaixo de 25 ossos (ou baked) a folga é real.

## 8. Recomendações para a especificação dos nossos modelos

Contexto: modelos serão **gerados por IA a partir das artes aprovadas e limpos no Blender**. Isso pesa para cima em triângulos (malha gerada tende a ser densa e irregular) e é a razão de manter tetos, mas os alvos devem seguir o que o SB prova ser suficiente para este estilo e esta câmera.

1. **Faixa-alvo × teto.** Manter os tetos do 04 (herói 10 mil, inimigo 5 mil, chefe 25 mil) como **limites duros** e fixar **alvos de produção** perto do SB: herói **4.000 a 6.500** tri, inimigo comum **1.500 a 3.500**, inimigo de enxame **500 a 1.500**, elite **3.000 a 5.000**, chefe **10.000 a 16.000**. O retopo no Blender deve mirar o alvo; o teto é só para exceções justificadas. Cada tri a menos libera orçamento de sombra (só personagens projetam).
2. **Enxame barato e sem custo de osso.** Nove inimigos do SB, incluindo os mais numerosos, usam animação baked (VAT, 0 ossos, 25 a 97 quadros, 200 a 600 vértices). Adotar essa técnica para os 2 ou 3 tipos mais numerosos do Echoes (se o 04 aceitar) ou, no mínimo, ≤ 20 ossos de deformação nesses tipos. Resolve o limite do Deck (1.200 ossos).
3. **Ossos.** Orçar **ossos de deformação**, não bind pose: herói 40 a 55, inimigo 15 a 35, chefe 70 a 100. IK, sockets e cloth/rabo separados em lista à parte. 4 influências por vértice. Para ficar abaixo de 55, limitar dedos a 1 osso por mão (mitten) e acessórios a poucos ossos.
4. **Proporções chibi (régua de silhueta).** Altura total do herói 1,5 a 2,6 m (alvo 1,9 a 2,1 m); **cabeça + chapéu/cabelo ≈ 35% a 50% da altura** (≈ 2 a 3 cabeças de altura); quadril a 22% a 35% da altura (pernas curtas e grossas); pés ao nível do chão. A cabeça é um osso isolado com chapéu/acessório fundido na mesma malha (permite variantes de cabeça grande sem malha nova). Cada herói deve ser identificável **só pela silhueta**: um apêndice grande e distinto (chapéu, cauda, instrumento, asas) e a largura 1,0 a 2,8 m, nunca 3 heróis com o mesmo contorno.
5. **Chefes: grande, largo, legível por partes.** Altura 4 a 6 m e largura 4 a 8+ m (Hydra 12 m de comprimento) para ocupar a tela vista de cima. Dividir em conjuntos animáveis (SB Squid: corpo / tentáculos de trás / tentáculos da frente) em vez de um único esqueleto; peças auxiliares (espinhos, projéteis, línguas) como malhas separadas pequenas (50 a 700 tri).
6. **Textura e shading.** O SB entrega pintura à mão em 2048² + rim de borda dura; para a nossa câmera (herói a ~155 px, seção 17.2) 1024² funciona: manter 1024² para herói e inimigo e 2048² para chefe. **Sem normal map** (decisão do 04) é viável; o SB só usa normal em ~15% dos heróis e como complemento. Compensar com albedo com luz/sombra pintadas (volume assado), 4 a 6 valores de cor por região e paleta saturada. Reservar canal de emissão para olhos/gemas (região B/máscara) e um segundo conjunto "corrompido" (`Dark*` no SB) só se o Echoes tiver estado de corrupção no mesmo mestre.
7. **Mestre de shader.** Um único shader de personagem com: albedo + tinta (multiplicador), rim/fresnel de **borda dura** (`smoothstep(0,2; 0,05)`, força ≈ 2,5), emissão HDR, `HitFlash` (liga/desliga + cor), congelamento (fresnel invertido) e dissolução. **Sem passe de contorno** (o SB não usa); silhueta via rim + sombra no chão. Elite do Echoes por tinta/halo/escala segue válido e é mais barato que o SB.
8. **Animação.** O SB prova que o herói precisa de **só Idle (≈ 1,0 s) + Run (≈ 0,53 s, speed 1,1)** em laço a 60 q/s, com golpe e conjuração resolvidos por VFX. Recomendação: fixar o pacote mínimo do herói em Idle, Run, Hit e Death (e um clipe de conjuração curto, 0,3 a 0,5 s, aditivo, se o 04 mantiver golpe/conjuração); não gastar orçamento em dezenas de clipes por classe. Inimigos esqueletais: Move em laço 0,5 a 2,0 s + telegráfico 0,3 a 2,0 s + ataque 0,4 a 1,0 s. Chefes: par Charge (0,9 a 1,75 s) + Ação (0,8 a 1,0 s) por golpe, morte de 5 a 6 s, stagger de ~1,5 s; 15 a 20 clipes por chefe. O telegráfico com antecipação longa é o que dá legibilidade (ameaça mais visível que o efeito do jogador).
9. **Cenário.** O SB constrói áreas com atlas de 2048² (+ normal) e peças de 13 a 300 tri, com a riqueza na textura; árvores com LOD de 100% / 43% / 24%. O Echoes (peças de 200 a 2.500 tri) está folgado; sugere-se mirar a metade desses valores nas peças modulares e usar LOD só em vegetação. Rochas grandes: 200 a 700 tri com 1 atlas. Decisão pendente: o SB deixa rochas e árvores projetarem sombra; o Echoes decidiu que não. Manter a decisão do Echoes (mais barato) e usar sombra pintada/blob no cenário.
10. **Checagens de pipeline (IA + Blender).** Para cada modelo gerado: (a) contar triângulos e **ossos de deformação** com script de Blender e reprovar acima do teto; (b) 1 material, UV única sem sobreposição, atlas 1024² (2048² chefe); (c) topologia que deforme em ombro/quadril sem desfazer a silhueta chibi; (d) normais suaves (razão vértices/triângulos alvo ≈ 0,7); (e) pés no plano y = 0, origem entre os pés, escala 1 unidade = 1 m; (f) cabeça como osso próprio; (g) sockets nomeados conforme o 04.

## 9. Perguntas em aberto

- A relação 1 unidade do modelo = 1 m não está confirmada no SB (o prefab dos heróis tem escala 1, mas a câmera e a escala do mundo não foram medidas). Medir pela câmera/cena antes de copiar a altura.
- O HLSL dos shaders não foi exportado; "rampa de toon" e "contorno" foram inferidos pela ausência de propriedades. Se o dono quiser o efeito idêntico, é preciso observar o jogo rodando.
- Quais inimigos do SB além dos 9 confirmados (Snipjaw, Spitter, StinkBug, Tripod, Bouncer) usam animação baked: marcado "não verif." na seção 2.
- Aceitar animação baked (VAT) no Echoes? Afeta `Rig_Humanoid_Chibi` por família, o Animator e o orçamento de ossos (04 seções 17.2 e 18).
- Elite por tinta (Echoes) × malha própria (SB): manter a decisão do 04?
