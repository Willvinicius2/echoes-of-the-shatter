# Echoes of the Shatter — instruções para o Claude Code

ARPG single-player em 3D estilizado (câmera fixa 3/4) com expedições idle, para Steam (Acesso Antecipado).
Motor: **Unity 6.3 LTS (6000.3.26f1) com URP, C#** (decisão do dono em 16/10/2026; antes UE 5.8 e, no plano original, Godot 4). O ShatterCore (C++17) vira DLL nativa chamada por P/Invoke.

## Máquina e disco
- O disco C está cheio: tudo do projeto fica no disco D. Repositório em `D:\openclaude\EchoesOfTheShatter`, arquivos de trabalho em `D:\openclaude\_trabalho-claude`.
- Unity: editor em `D:\Unity\Editors\6000.3.26f1`, Unity CLI em `D:\Unity\cli\bin` (versão do script oficial, não a do winget), cache de downloads em `D:\Unity\downloads`. Licença Unity Personal ativa.
- Projeto Unity: `EchoesOfTheShatter/` (Assets, Packages, ProjectSettings), com o pacote `com.unity.pipeline` para a CLI e o MCP controlarem o editor.

## Direção de arte (aprovada em 16/10/2026)
- O visual segue o estilo do Spell Brigade: 3D estilizado pintado à mão, heróis chibi, magia em neon e UI de pedra escura. As decisões de renderização estão em `docs/08_decisoes_visual_3d.md`.
- As referências aprovadas e as folhas oficiais de heróis, inimigos, chefes, cenários e ícones estão em `docs/arte/referencias-geracao/` (ver o README dessa pasta). Todo personagem novo deve seguir essas folhas.
- Os assets extraídos do Spell Brigade (`D:\openclaude\spell-brigade-re`) servem só de referência de estilo. Nunca entram no projeto nem no build.
- O Mago usa capuz e cajado com cristal, e nunca lanterna.
- Toda arte nova vai para aprovação do dono antes de entrar no jogo.

## Onde está cada coisa
- `docs/00_plano_existente.md` — plano de design aprovado (Plano Steam v2.0). Fonte de verdade de regras, conteúdo e escopo; as partes de pixel art e Godot ficaram como histórico.
- `docs/01_plano_execucao.md` — equipe de agentes, fases e quem é dono de cada arquivo.
- `docs/02_requisitos.md` — escopo do protótipo, RF-01..RF-65, RNF, critérios de aceite ([SC] = teste automático, os demais manuais no editor).
- `docs/03_design_system.md` + `docs/03_design_tokens.json` — especificação de arte 3D, paleta, tokens (com mapeamento para USS), telas e componentes em UI Toolkit.
- `docs/04_arquitetura.md` — arquitetura Unity 6 + URP: renderização (seção 3), estrutura do projeto e asmdefs (seção 4), integração ShatterCore ↔ Unity (seção 9), testes (seção 13), pipeline Blender → FBX → Unity (seção 17), orçamentos (seção 18).
- `docs/05_conteudo.md`, `docs/06_dados.md` — conteúdo do protótipo e formato das tabelas.
- `docs/08_decisoes_visual_3d.md` — decisões de motor e renderização e quem é dono de cada número (03 = arte, 04 = orçamentos técnicos).
- `docs/10_qa.md` — matriz de rastreabilidade, roteiros de playtest e testes planejados.
- `docs/15_etapas.md` — as 5 etapas do jogo (base técnica, fatia jogável da Cripta, ciclo do protótipo, elenco e Ato I, Acesso Antecipado) com critérios de aceite.
- `docs/pesquisa/` — pesquisas de referência externas.
- `ShatterCore/` — motor de regras em C++17 puro, sem Unity. Headers em `include/shatter/`; `src/` e testes em andamento.
- `EchoesOfTheShatter/Content/Data/` — CSV de conteúdo, `Loc/` e esquemas (destino previsto: `Assets/StreamingAssets/Data`, ver 04 seção 4.2).
- `art-src/graybox/` — malhas provisórias do Blender (scripts, .blend, .fbx no Git LFS, prévias).
- `tools/validate_data.py` — validador de dados; `tools/build_core.cmd` — build e testes do ShatterCore no Windows.
- `.claude/agents/` — agentes do projeto (ex.: `pesquisador-referencias`).

## Regras do projeto
- Texto em português do Brasil; código, IDs de conteúdo e chaves em inglês (`skill.warrior.iron_cut`).
- Um único motor de regras (ShatterCore) para combate e simulador idle. O C# da Unity não calcula regra.
- Determinismo: mesma seed + dados + snapshot = mesmo resultado. Simular em 1 ou N partes dá o mesmo `resultHash`.
- Proibido em `ShatterCore/src/`: exceções, RTTI, estado global mutável, `std::rand`/`random_device`/distribuições da STL, iterar `unordered_map` em código que afeta resultado, `pow/exp/log/sin` no golpe e no simulador, `-ffast-math`.
- Números em CSV/JSON com `std::from_chars`/`std::to_chars` (ponto decimal).
- Nenhum número de balanceamento no código: tudo nos CSV de conteúdo.
- Nenhum texto visível ao jogador no código: só chaves de localização.
- Git LFS ligado para `.blend`, `.fbx`, `.dll` e outros binários (ver `.gitattributes`).
- **Agentes de design do jogo (conteúdo, narrativa, UI, revisões de design) usam no máximo o modelo Sonnet 5.5.**

## Como compilar e testar o ShatterCore
Windows: `tools\build_core.cmd Release --werror` (MSVC 14.50 e CMake do Visual Studio Build Tools).
Linux ou nuvem:
```
cmake -S ShatterCore -B build -DCMAKE_BUILD_TYPE=Release -DSHATTER_WERROR=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

## Pendências de decisão
- Itens "confirmar na instalação" do `docs/04_arquitetura.md`: conferir na Unity 6.3 instalada antes de o Frontend depender deles.
- O protótipo Godot F1 continua na raiz (`project.godot`, `autoload/`, `core/`, `data/`, `game/`, `scenes/`, `tests/`) como referência de game feel. Ele não faz parte do jogo Unity.

## Próximo passo
Etapa 2, fatia jogável da Cripta (ver `docs/15_etapas.md`): regras novas no core, tabelas novas, DLL real na Unity, layout da Cripta na escala A (`docs/14_layout_cripta.md`), modelos 3D gerados pelo TripoSG a partir de `docs/arte/referencias-geracao/aprovadas/modelagem/` e cenário da Cripta.
