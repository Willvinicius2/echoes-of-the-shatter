# Echoes of the Shatter — instruções para o Claude Code

ARPG single-player em 3D estilizado (câmera fixa 3/4) com expedições idle, para Steam (Acesso Antecipado).
Motor: **Godot 4 (.NET, C#)** (decisão do dono em 20/10/2026; antes Unity 6.3, UE 5.8 e o Godot 4 do plano original). O ShatterCore (C++17) vira biblioteca nativa chamada por P/Invoke. Plano e o que mudou: `docs/tecnico/23_migracao_godot.md`. O último estado da Unity está no branch `arquivo/unity-final`; não restaure Unity no `master`.

## Máquina e disco
- O disco C está cheio: tudo do projeto fica no disco D. Repositório em `D:\openclaude\EchoesOfTheShatter`, arquivos de trabalho em `D:\openclaude\_trabalho-claude`.
- Godot e MCP do Godot ficam no disco D. O projeto Godot fica em `godot/` (criado pela migração). A pasta Unity antiga do PC só é apagada quando o dono confirmar.

## Direção de arte (aprovada em 16/10/2026)
- O visual segue o estilo do Spell Brigade: 3D estilizado pintado à mão, heróis chibi, magia em neon e UI de pedra escura. As decisões de renderização estão em `docs/arte/08_decisoes_visual_3d.md`.
- As referências aprovadas e as folhas oficiais de heróis, inimigos, chefes, cenários e ícones estão em `docs/arte/referencias-geracao/` (ver o README dessa pasta). Todo personagem novo deve seguir essas folhas.
- Os assets extraídos do Spell Brigade (`D:\openclaude\spell-brigade-re`) servem só de referência de estilo. Nunca entram no projeto nem no build.
- O Mago usa capuz e cajado com cristal, e nunca lanterna.
- Toda arte nova vai para aprovação do dono antes de entrar no jogo.

## Onde está cada coisa
- `docs/design/00_plano_existente.md` — plano de design aprovado (Plano Steam v2.0). Fonte de verdade de regras, conteúdo e escopo; as partes de pixel art e Godot ficaram como histórico.
- `docs/requisitos-qa/01_plano_execucao.md` — equipe de agentes, fases e quem é dono de cada arquivo.
- `docs/requisitos-qa/02_requisitos.md` — escopo do protótipo, RF-01..RF-65, RNF, critérios de aceite ([SC] = teste automático, os demais manuais no editor).
- `docs/arte/24_direcao_visual_cripta.md` — direção visual da Cripta (escala, luz, andares); agente `diretor-visual`.
- `docs/arte/03_design_system.md` + `docs/arte/03_design_tokens.json` — especificação de arte 3D, paleta, tokens (telas e componentes; o mapeamento para USS é histórico, no Godot vira Theme).
- `docs/tecnico/04_arquitetura.md` — arquitetura do core, dados e contratos (partes de Unity/URP são histórico). `docs/tecnico/23_migracao_godot.md` — migração para o Godot: o que fica, o que sai, pastas e ordem.
- `docs/design/05_conteudo.md`, `docs/tecnico/06_dados.md` — conteúdo do protótipo e formato das tabelas.
- `docs/arte/08_decisoes_visual_3d.md` — decisões de motor e renderização e quem é dono de cada número (03 = arte, 04 = orçamentos técnicos).
- `docs/requisitos-qa/10_qa.md` — matriz de rastreabilidade, roteiros de playtest e testes planejados.
- `docs/design/15_etapas.md` — as 5 etapas do jogo (base técnica, fatia jogável da Cripta, ciclo do protótipo, elenco e Ato I, Acesso Antecipado) com critérios de aceite.
- `docs/pesquisa/` — pesquisas de referência externas.
- `ShatterCore/` — motor de regras em C++17 puro, sem Unity. Headers em `include/shatter/`; `src/` e testes em andamento.
- `EchoesOfTheShatter/Content/Data/` — CSV de conteúdo, `Loc/` e esquemas (destino previsto: `godot/Data`, ver 23).
- `ShatterCore/bindings/csharp/` — P/Invoke em C# puro (herdado da Unity), usado pelo Godot .NET.
- `art-src/herdado-unity/` — modelos FBX, texturas e JSON do kit da Cripta tirados da Unity, para importar no Godot.
- `art-src/graybox/` — malhas provisórias do Blender (scripts, .blend, .fbx no Git LFS, prévias).
- `tools/dados/validate_data.py` — validador de dados; `tools/core/build_core.cmd` — build e testes do ShatterCore no Windows. Mapa das pastas de ferramentas em `tools/README.md`.
- `.claude/agents/` — agentes do projeto: `escolhedor-ferramentas`, `painel-progresso`, `guardiao-github`, `pesquisador-referencias`. `.claude/catalogo-ferramentas.md` — catálogo atividade → skills/repos/ferramentas/modelo.
- `prototipos/godot-f1/` — protótipo Godot F1 inteiro (histórico, referência de game feel); como rodar em `COMO_RODAR.md`.
- `docs/README.md` — índice dos documentos por assunto (`design/`, `tecnico/`, `requisitos-qa/`, `arte/`, `pesquisa/`, `progresso/`).

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

## Modelo certo para cada tarefa (regra do dono, 18/10/2026)
Não use o modelo mais caro para trabalho que o mais barato resolve: isso gasta o limite de uso à toa. Na dúvida, comece pelo menor e suba só se falhar.
- **Haiku** (`model: haiku`): tarefa mecânica de terminal. Git, LFS, `guardiao-github`, conferir envio, listar arquivos, rodar script pronto.
- **Sonnet 5.5** (`model: sonnet`): o padrão do projeto. Implementar C++/C# com regra já especificada, CSV e dados, localização, UI Toolkit, `painel-progresso`, pesquisa de referências, revisão de design e texto. É também o teto dos agentes de design.
- **Opus**: só para decisão difícil. Contrato novo da API C, bug de memória ou comportamento indefinido, revisão final de uma branch antes do merge no `master`.
- **Fable**: só quando o dono pedir. Nunca para agentes, subagentes, revisões rotineiras ou tarefas de arquivo e Git.
- Todo agente em `.claude/agents/` declara `model:` no cabeçalho. Subagente disparado sem modelo herdaria o da sessão principal, então sempre informe o modelo ao disparar.
- A sessão principal (orquestrador) também deve rodar em Sonnet no dia a dia. Subir de modelo é decisão pontual do dono.

## Git e GitHub
- Repositório: https://github.com/Willvinicius2/echoes-of-the-shatter (privado, com Git LFS), branch principal `master`. O sócio do dono também acompanha e trabalha por ele, então o GitHub precisa ter sempre o estado real do projeto.
- O dono autorizou enviar ao GitHub todo commit do projeto. Ao fechar uma tarefa, faça o commit na branch da tarefa (Conventional Commits, mensagem em português) e o `git push` em seguida (`git push -u origin <branch>` na primeira vez). Trabalho terminado não fica só no PC.
- Uma frente de trabalho = uma branch (`etapaN/<frente>`), de preferência numa worktree em `D:\openclaude\_trabalho-claude\wt\`. O merge no `master` vem depois dos testes, e o `master` também vai para o GitHub logo depois do merge.
- Faça commit só do que é seu: `git commit -- <caminhos>`. Não leve junto alterações de outra sessão nem arquivos gerados de que outro agente é dono.
- Nunca use `--force` no `master`, nunca reescreva histórico já enviado e nunca apague branch sem o ok do dono.
- O hook Stop de `.claude/settings.json` (`tools/git/checar_envio.py`) não deixa a sessão encerrar a vez com commit que não está no GitHub.
- Ao fechar uma etapa, ou quando o dono pedir, rode o agente `guardiao-github` (confere todas as worktrees e envia o que faltar) e depois o `painel-progresso`.
- Ficam fora do GitHub de propósito: caches, `venv`, saídas brutas do TripoSG em `_trabalho-claude/modelos3d/`, imagens de trabalho do Codex, packs KayKit e os assets do Spell Brigade. A arte aprovada entra no repositório.

## Como compilar e testar o ShatterCore
Windows: `tools\core\build_core.cmd Release --werror` (MSVC 14.50 e CMake do Visual Studio Build Tools).
Linux ou nuvem:
```
cmake -S ShatterCore -B build -DCMAKE_BUILD_TYPE=Release -DSHATTER_WERROR=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

Visual 2D top-down é o definitivo desde 29/10/2026 (`docs/arte/26_direcao_visual_2d.md`; capturas em `docs/arte/sprites2d/capturas_cripta/`).

Cliente 2D (corrida top-down, `godot/scripts2d/`): teste headless `godot --headless --path godot --script res://scripts2d/tools/test_2d.gd` (CI `cliente2d.yml`; ver `godot/COMO_RODAR_2D.md` e `docs/arte/25_formato_folhas_sprites_2d.md`). O cliente 3D antigo continua em `godot/scenes` e `godot/scripts`. O `checar_cliente.sh` e o CI `cliente.yml` da Unity foram removidos.

O MSVC local não acusa vários avisos que o GCC e o Clang do CI tratam como erro (`-Werror`): `-Wmissing-field-initializers` (agregado sem `{}`), `-Wtype-limits` (comparar tipo sem sinal com `< 0`, inclusive enum de base `uint8_t` convertido para `int`) e `-Wrange-loop-construct` (`for (const std::string x : ...)` em vez de `const std::string&`). Revise esses padrões antes de enviar mudanças no core e confira o CI depois do push.

## Perguntas ao dono
- Toda pergunta ou dúvida para o dono, em `docs/` ou nas `pendencias_dono` de `docs/progresso/estado.json`, traz: a pergunta inteira (não um título), o contexto completo para entender sem abrir outro arquivo, e as opções com o efeito de cada uma. Quem lê pode ser o dono ou o sócio dele.
- Em `estado.json`, cada pendência tem `id` (fixo, nunca reaproveitado), `titulo`, `detalhe` (resumo de uma linha), `pergunta`, `contexto` (lista de parágrafos), `opcoes` (`id` = letra, `nome` e `efeito`) e `origem`. Uma pergunta = uma escolha; dois assuntos viram duas pendências. O painel e o roteiro (`tools/roteiro/gerar_roteiro.py`) mostram esses campos.
- O painel (https://claude.ai/artifact/7Kzo46Eyy8cQjF9HhuWMXg) tem votação e comentários por pergunta: componente `tools/votacao/` (embutido pelo `gerar_painel.py`), gravado no banco do artifact (coleção `votos`, um documento por pessoa com `respostas.<id da pergunta>` = `{opcao, comentario, em}`). Para ler: ArtifactData `list` em `votos` no link do painel. Ao republicar o painel, omitir `capabilities` para manter o banco. O roteiro só mostra as perguntas, com link para votar no painel. Ao decidir, a pendência sai do `estado.json` e entra em `decisoes`.
- Depois de mudar docs, artes aprovadas ou pendências, regerar e republicar o roteiro do sócio no mesmo link: https://claude.ai/artifact/5G5WBocgrp8NAeLKiF9FP8

## Escolha de ferramentas (automática)
- **Toda tarefa começa consultando `.claude/catalogo-ferramentas.md`** (ou disparando o agente `escolhedor-ferramentas`, Sonnet) para saber, sem o dono pedir, quais skills de `.claude/skills/`, repositórios, ferramentas, subagentes e modelo usar. No relatório final, diga quais usou.
- Arte 3D: o `escolhedor-ferramentas` também é o revisor crítico; o que ia para aprovação do dono passa antes por ele, e só chega ao dono o que estiver bonito. O dono continua sendo quem aprova a arte.

## Pendências de decisão
- **PRIORIDADE MÁXIMA — Alinhamento de Contexto, Dupla e Escopo (`docs/design/20_alinhamento_ia_e_escopo.md`):** Antes de iniciar qualquer nova frente ou disparar subagentes, leia `docs/design/20_alinhamento_ia_e_escopo.md` e peça ao dono para decidir as duas pendências prioritárias em `docs/progresso/estado.json` (`fluxo-agentes-contexto` e `foco-fatia-vertical`). Não aprove artes nem decisões de design em nome do dono.
- Versão do Godot 4.x/.NET e o carregamento da biblioteca nativa no export: definir ao criar o projeto (doc 23).
- O protótipo Godot F1 fica em `prototipos/godot-f1/` como referência de game feel (2D, GDScript). Não é a base do jogo atual. Como rodar: `prototipos/godot-f1/COMO_RODAR.md`.

## Próximo passo
Etapa 2, fatia jogável da Cripta, agora no Godot (ver `docs/design/15_etapas.md` e `docs/tecnico/23_migracao_godot.md`): primeiro a Cripta montada no Godot via MCP, depois o Guerreiro, ligados ao core. Layout da Cripta na escala A (`docs/tecnico/14_layout_cripta.md`), modelos 3D gerados pelo TripoSG a partir de `docs/arte/referencias-geracao/aprovadas/modelagem/` e cenário da Cripta.
