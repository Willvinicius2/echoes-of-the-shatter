# Catálogo de ferramentas do Echoes of the Shatter

Mapa **atividade → skills, repositórios, ferramentas, subagente e método**. O agente `escolhedor-ferramentas` lê este arquivo; toda tarefa começa por ele (ver `CLAUDE.md`). Skills ficam em `.claude/skills/` (26 do awesome-gamedev-agent-skills, PR 41, vindas do post https://x.com/doncoderlione/status/2112638459089150151; origem em `.claude/skills/ORIGEM.md`). Atualize este arquivo quando algo novo funcionar ou falhar.

## Modelos de subagente (regra do dono)
Haiku: Git, LFS, conferir envio, rodar script pronto. Sonnet 5.5: padrão (modelagem por script, C#, CSV, textos, UI, revisão). Opus: contrato novo da API C, bug de memória, revisão final antes do merge. Fable: só se o Will pedir.

## Tabela principal
| Atividade | Skills (ordem) | Repos / referências | Ferramentas | Subagente |
|---|---|---|---|---|
| Modelagem 3D por partes no Blender (cenário/prop) | `create-game-assets`, `level-design`, `performance-optimization` | `art-src/graybox/`, `art-src/cenario/` (scripts de pilar e piso, `modulos/braseiro.py`), folhas em `docs/arte/referencias-geracao/` | Blender com Python (`bpy`), um `build_<peça>.py` por peça, exporta `.glb` para `godot/` | 1 Sonnet por parte, um render por vez |
| Modelagem de personagem/inimigo por partes | `create-game-assets`, `godot-animation` | folhas oficiais de heróis/inimigos; pose neutra (A/T, mãos relaxadas) para TripoSG | Blender Python; `D:\openclaude\_ferramentas\TripoSG` só para malha base | 1 Sonnet por parte (corpo, capacete, peitoral, braços, luvas, botas) |
| Materiais, textura pintada, bake | `shader-programming`, `godot-shaders`, `create-game-assets` | `art-src/cenario/gen_pedra_pilar.py`, `gen_piso_*.py`; decisões em `docs/arte/08_decisoes_visual_3d.md` | nós procedurais do Blender, bake em PNG; baixa amostragem para iterar, Cycles só no final | Sonnet |
| Direção visual da Cripta (escala, proporção, luz, paleta, andares) | `level-design`, `camera-systems`, `godot-3d-essentials` | `docs/arte/24_direcao_visual_cripta.md`, `docs/tecnico/14_layout_cripta.md`, pranchas aprovadas | Godot MCP, capturas 3/4, medida dos `.glb` | `diretor-visual` (Sonnet) |
| Iluminação, câmera 3/4, render de revisão | `camera-systems`, `godot-3d-essentials` | `docs/arte/03_design_system.md` | Blender EEVEE rápido; Godot headless para print | Sonnet |
| Godot: cena, nós, importação | `godot-nodes-scenes`, `godot-3d-essentials`, `godot-resources`, `godot-signals-groups` | `docs/tecnico/23_migracao_godot.md`, `docs/tecnico/14_layout_cripta.md` | Godot MCP (disco D) | Sonnet |
| Godot: shader/VFX/neon | `godot-shaders`, `shader-programming`, `game-feel` | `prototipos/godot-f1/` (game feel) | Godot MCP | Sonnet |
| Godot: UI de pedra escura | `godot-ui-control`, `game-ui-ux` | `docs/arte/03_design_system.md` + tokens | Theme do Godot | Sonnet |
| Arte 2D de UI/HUD (ícones, globos, molduras) | `game-ui-ux`, `godot-ui-control` | `docs/arte/29_arte_ui_gpt_image.md`, capturas em `docs/arte/sprites2d/capturas_cripta/` | Codex CLI com gpt-image via `docs/arte/referencias-geracao/scripts/gerar.py`; fundo magenta + `tools/arte/ui_gpt_image/key.py`; Jev para decisão de estilo | Sonnet |
| Efeitos pixel art 2D em código (ui/, fire/, ice/, impacts/) | skill `pixelfx` (patch-gg/pixelfx, MIT) | clone em `D:\openclaude\_trabalho-claude\pixelfx-src`; `node tools/render.mjs <cat>/<fx> --sheet` exporta sprite sheet para o Godot | Node 18+; código lido antes de rodar (só fs local, ffmpeg opcional). 244 efeitos em 21 categorias (moves, fire, ice, lightning, melee, projectiles, status, nature, holy, shadow...) + 12 golpes completos com pose de personagem (`tools/act.mjs`). Licença MIT (Patch + Hugo Duprez); a fonte de `gallery/fonts` NÃO é MIT, não usar. Sprite sheet pré-renderizada = custo de runtime de um `AnimatedSprite2D` | Sonnet |
| VFX pixel art para Godot 4.7 (oficina no editor, sprite sheet, SpriteFrames) | `Smidle/Jeff-FX-forge` (MIT; texturas originais CC0) | plugin `addons/fx_forge/` (só ele é importável; o projeto de demo traz personagem e headshot de terceiros, não copiar); 38 efeitos de pixel por código (corte de fogo, impacto, explosão, círculo, status) + 44 clássicos 3D gravados em 2D; exporta PNG, SpriteFrames e cena pronta | Godot 4.7.2 testado só em macOS/Compatibility. Exportar para sprite sheet e tocar com `AnimatedSprite2D`: custo de runtime quase zero. Evitar os "clássicos 3D" ao vivo e muitas instâncias dos efeitos procedurais (CPU) | Sonnet |
| Geração de VFX/habilidade em pixel art (navegador, determinístico) | `GameDev-Toolkit/pixel-ability-fx-generator` (Apache-2.0) | `index.html` abre local, sem build; 48 formações (impacto, barreira, aura), 10 paletas elementais, seed reproduzível; exporta atlas PNG, sequência ou GIF em 128 a 256 px | Loops perfeitos (fase periódica). Bom para auras e barreiras de gema; os elementos do jogo (Trovão, Veneno, Gelo, Fogo) mapeiam nas paletas Storm, Nature, Frost, Fire | Sonnet |
| Gameplay C# e ligação ao core | `godot-csharp`, `input-systems`, `physics-tuning`, `godot-physics`, `game-ai` | `ShatterCore/bindings/csharp/` | `dotnet`, Godot | Sonnet |
| Animação e feel de combate | `godot-animation`, `game-feel`, `physics-tuning` | `docs/arte/animacao_mixamo.md` (Mixamo, KayKit CC0) | Blender, Godot | Sonnet |
| Core C++ (ShatterCore) | nenhuma skill de Godot; seguir regras do `CLAUDE.md` (sem exceções, RTTI, estado global, `std::rand`) | `ShatterCore/include/shatter/`, `docs/tecnico/09_mudancas_contrato.md` | CMake + ctest (ver CLAUDE.md); olhar os avisos do GCC/Clang | Sonnet; Opus só para contrato da API C ou bug de memória |
| Dados CSV/JSON | `rpg`, `roguelike` (design de itens, afixos, loot) | `EchoesOfTheShatter/Content/Data/`, `docs/tecnico/06_dados.md` | `tools/dados/validate_data.py` | Sonnet |
| Textos, diálogos, localização | `dialogue-systems`, `rpg` | `Content/Data/Loc/`, `docs/design/05_conteudo.md` | só chaves de loc no código | Sonnet (teto dos agentes de design) |
| Itens/habilidades/ARPG | `rpg`, `roguelike`, `game-ai` | `docs/design/18_combate_combo.md`, `19_itens_e_habilidades.md` | validador de dados | Sonnet |
| Save/progressão | `save-systems` | `save_v2.schema.json` | validador | Sonnet |
| Áudio | `godot-audio` | — | Godot | Sonnet |
| Testes e QA | `godot-gdscript-headless-testing`, `performance-optimization` | `docs/requisitos-qa/10_qa.md` | ctest, Godot headless | Sonnet |
| Export / Steam | `godot-export`, `steam-publish` | `docs/design/15_etapas.md` (etapa 5) | Godot export | Sonnet |
| Git, LFS, PR | nenhuma | `.gitattributes` (LFS para `.blend`, `.fbx`, `.dll`) | `guardiao-github`; branch temporária, PR, CI verde, merge, apagar branch | Haiku |
| Pesquisa de referência | — | `pesquisador-referencias` | WebSearch/WebFetch | Sonnet |
| Painel/roteiro | — | `docs/progresso/estado.json` | `painel-progresso` | Sonnet |

## Método de arte 3D (artefato do sócio + RafaxLab)
0. Siga `art-src/cenario/METODO_MODELAGEM_3D.md` (método do estandarte v2).
1. **Árvore de agentes**: uma thread por objeto; dentro dela, um subagente por parte (personagem: corpo, capacete, peitoral, braços, luvas, botas; cenário: piso primeiro, depois o resto). Um script por peça (`build_<peça>.py`) reconstrói o `.blend` do zero e exporta o `.glb`; o Git LFS guarda só o resultado.
2. **Ciclos curtos de render**: muitas chamadas pequenas de renderizar, olhar e corrigir (o vencedor do concurso fez 243; o ganho veio do número de ciclos, não do modelo). Iterar em baixa amostragem; Cycles caro só no final (render acima de 5 min expira o cache de contexto). **Um render por vez** no PC.
3. Cada ciclo entrega: render principal, vistas ortográficas, wireframe e close da parte, lado a lado com a folha aprovada.
4. **Pedidos pequenos, um commit por passo**, com o objetivo final dito em uma frase.
5. **Piloto aprovado vira régua**: o primeiro objeto bom define o nível de detalhe das demais peças.
6. **Agente revisor crítico** (este agente) confere contra a folha e a régua antes do Will ver.
7. TripoSG: referência em pose neutra, de frente, fundo liso; malha base vai para retopo/detalhe por script, nunca direto ao jogo.
8. Fraquezas conhecidas: rosto e mãos; pedra limpa demais; fundo simples. Corrigir de propósito.

## Régua de qualidade (o que o revisor exige)
- Silhueta legível a distância 3/4 e fiel à folha oficial.
- Pedra com desgaste **assimétrico**: rachaduras, sujeira e musgo/cinza diferentes por face; variação de escala; sem simetria perfeita.
- Mais de um material por peça (pedra, metal, brasa/neon); bordas com bisel e quebra; pintura à mão, contorno consistente.
- Detalhe médio e pequeno (não só formas grandes), sem aspecto de "massinha" nem plástico.
- Neon mágico só onde a folha pede; Mago com capuz e cajado de cristal, nunca lanterna.
- Orçamentos técnicos de `docs/tecnico/04_arquitetura.md`. Nada do Spell Brigade.
- Só passa ao Will o que estiver bonito; o Will aprova a arte, nunca o revisor.

## Repositórios do post do X (https://x.com/doncoderlione/status/2112638459089150151)
| Repositório | Status | Uso |
|---|---|---|
| gamedev-skills/awesome-gamedev-agent-skills | instalado (26 skills em `.claude/skills/`, PR 41) | tabela principal acima |
| Coding-Solo/godot-mcp | já em uso | montar cenas, nós, rodar o projeto e ler o debug no Godot |
| VAST-AI-Research/TripoSR | não usar | só protótipo e exige GPU de ~6 GB; usamos o TripoSG, mais novo |
| CoderGamester/mcp-unity | descartado | o projeto saiu da Unity |
| pmndrs/drei, react-three-rapier, react-postprocessing; Alchemist0823/three.quarks | descartados | bibliotecas React/three.js; bloom e partículas saem nativos no Godot (`godot-shaders`, `game-feel`) |
| Mugen87/yuka | descartado | IA de NPC em JS; a nossa fica no ShatterCore (`game-ai` só para o cliente) |
| colyseus/colyseus | descartado | multiplayer; o jogo é single-player |

Ferramentas de Blender não vieram do post: o ciclo é Blender com Python (`bpy`) em modo sem janela, como nos scripts de `art-src/`. Se surgir um MCP de Blender útil, o `pesquisador-referencias` avalia e o Will decide antes de instalar.

## Outras fontes
- Artefato do sócio: https://claude.ai/artifact/RYEaZih9sQMAiYu8HNJ9D2 (concurso de 10 agentes, pilar gótico no Blender).
- Processo RafaxLab: piloto pequeno, refino por rodadas, crítico, referência neutra.
- **Método de modelagem (obrigatório para arte 3D)**: `art-src/cenario/METODO_MODELAGEM_3D.md` (PR 53), documentado a partir do estandarte v2.
- **Régua interna**: o estandarte v2 (PR 48) foi aprovado pelo Will; é o modelo de método (3 agentes, textura e normal pintadas, 6 a 8 ciclos) e de qualidade para os demais objetos.
- Referência de estilo apenas: Spell Brigade (nunca entra no build).

## Mods do Claude Code (custo de tokens, conflitos, contexto)
Mods rodam só no Claude Code local do Will (v2.1.287+, liberados na conta; teste com `claude plugin test`). Fontes baixadas em `D:\openclaude\_trabalho-claude\mods-video\`. Instalação (um chat novo carrega o mod):
```
claude plugin marketplace add nateherkai/claude-code-mods
claude plugin install cache-keeper@nateherk-mods     # cache quente/frio, /board, /handoff
claude plugin install collision-guard@nateherk-mods  # avisa antes de editar arquivo mexido por outro chat
claude plugin install goal-meter@nateherk-mods       # progresso do /goal
claude plugin install recording-mode@nateherk-mods   # mascara dados ao gravar (opcional)
```
Segunda leva, se precisar: `VedantAndhale/claude-pro-kit` (budget-guard, read-cap, reread-guard, compact-keeper, turn-budget) e `hamzafer/claude-code-mods` (context-bar, token-weather, usage-meter, session-saver). Estado da instalação: ver o relatório da thread "Mods instalados no Claude".

## Pesquisa de VFX em pixel art (01/11/2026)
Critério: licença que permita uso comercial, estilo pixel art, custo de desempenho baixo (jogo 2D leve, FPS alto) e encaixe no Godot 4.7. Regra de desempenho comum: **pré-renderizar em sprite sheet e tocar com `AnimatedSprite2D` ou `GPUParticles2D` com poucas partículas**; nada de gerar pixel por código a cada quadro durante a partida.

| Repositório | Veredito | Observação |
|---|---|---|
| patch-gg/pixelfx (MIT, 2,5 mil estrelas, ativo) | **usar** (já na tabela) | O "pixel fx" que o Will citou. Melhor fonte de referência de identidade por habilidade (cada efeito é código legível e recolorível) e de sprite sheets prontas via `render.mjs --sheet` |
| Smidle/Jeff-FX-forge (MIT + CC0 nos efeitos) | **usar o plugin** | Feito para Godot 4.7, exporta SpriteFrames direto. Ressalvas: interface em chinês, testado só em macOS; personagem e retrato da demo têm licença própria, não importar |
| GameDev-Toolkit/pixel-ability-fx-generator (Apache-2.0) | **usar como gerador de aura/barreira/impacto** | Sem build, determinístico, loops perfeitos; só 5 estrelas, então validar o resultado a olho |
| jess-hammer/2d-pixel-water-shader-godot (MIT) | reserva | Shader de água pixel art; útil só se a Cripta ganhar água |
| Mairon31/ppae-engine (Apache-2.0, 1 estrela) | acompanhar | Gerador TypeScript determinístico de personagens e efeitos; imaturo |
| audoraemon/vfxProve | descartado | Sem licença declarada |
| NullTale/LutLight2D, PixelationFx | descartados | Unity |
| hardc0l2e/VFXForge (MIT) | acompanhar | Ferramenta Godot de VFX 2D/3D, 0 estrelas, sem evidência de maturidade |
