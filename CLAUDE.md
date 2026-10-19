# Echoes of the Shatter — instruções para o Claude Code

ARPG single-player em 3D estilizado (câmera fixa 3/4) com expedições idle, para Steam (Acesso Antecipado).
Motor: **Unity 6.3 LTS (6000.3.26f1) com URP, C#** (decisão do dono em 16/10/2026; antes UE 5.8 e, no plano original, Godot 4). O ShatterCore (C++17) vira DLL nativa chamada por P/Invoke.

## Máquina e disco
- O disco C está cheio: tudo do projeto fica no disco D. Repositório em `D:\openclaude\EchoesOfTheShatter`, arquivos de trabalho em `D:\openclaude\_trabalho-claude`.
- Unity: editor em `D:\Unity\Editors\6000.3.26f1`, Unity CLI em `D:\Unity\cli\bin` (versão do script oficial, não a do winget), cache de downloads em `D:\Unity\downloads`. Licença Unity Personal ativa.
- Projeto Unity: `EchoesOfTheShatter/` (Assets, Packages, ProjectSettings), com o pacote `com.unity.pipeline` para a CLI e o MCP controlarem o editor.

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
- `docs/arte/03_design_system.md` + `docs/arte/03_design_tokens.json` — especificação de arte 3D, paleta, tokens (com mapeamento para USS), telas e componentes em UI Toolkit.
- `docs/tecnico/04_arquitetura.md` — arquitetura Unity 6 + URP: renderização (seção 3), estrutura do projeto e asmdefs (seção 4), integração ShatterCore ↔ Unity (seção 9), testes (seção 13), pipeline Blender → FBX → Unity (seção 17), orçamentos (seção 18).
- `docs/design/05_conteudo.md`, `docs/tecnico/06_dados.md` — conteúdo do protótipo e formato das tabelas.
- `docs/arte/08_decisoes_visual_3d.md` — decisões de motor e renderização e quem é dono de cada número (03 = arte, 04 = orçamentos técnicos).
- `docs/requisitos-qa/10_qa.md` — matriz de rastreabilidade, roteiros de playtest e testes planejados.
- `docs/design/15_etapas.md` — as 5 etapas do jogo (base técnica, fatia jogável da Cripta, ciclo do protótipo, elenco e Ato I, Acesso Antecipado) com critérios de aceite.
- `docs/pesquisa/` — pesquisas de referência externas.
- `ShatterCore/` — motor de regras em C++17 puro, sem Unity. Headers em `include/shatter/`; `src/` e testes em andamento.
- `EchoesOfTheShatter/Content/Data/` — CSV de conteúdo, `Loc/` e esquemas (destino previsto: `Assets/StreamingAssets/Data`, ver 04 seção 4.2).
- `art-src/graybox/` — malhas provisórias do Blender (scripts, .blend, .fbx no Git LFS, prévias).
- `tools/dados/validate_data.py` — validador de dados; `tools/core/build_core.cmd` — build e testes do ShatterCore no Windows.
- `.claude/agents/` — agentes do projeto: `painel-progresso`, `guardiao-github`, `pesquisador-referencias`.
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

Cliente C# sem o editor da Unity (Linux/WSL, precisa de dotnet 8): `tools/cliente/checar_cliente.sh` compila `Assets/Scripts` contra as referências UnityEngine 2021.3 e roda os testes EditMode puros contra a shattercore real; roda no CI (`cliente.yml`). Não substitui o editor (sem Input System, URP nem Unity 6; falhas esperadas em `tools/cliente/LISTA_ESPERADA.txt`).

O MSVC local não acusa vários avisos que o GCC e o Clang do CI tratam como erro (`-Werror`): `-Wmissing-field-initializers` (agregado sem `{}`), `-Wtype-limits` (comparar tipo sem sinal com `< 0`, inclusive enum de base `uint8_t` convertido para `int`) e `-Wrange-loop-construct` (`for (const std::string x : ...)` em vez de `const std::string&`). Revise esses padrões antes de enviar mudanças no core e confira o CI depois do push.

## Perguntas ao dono
- Toda pergunta ou dúvida para o dono, em `docs/` ou nas `pendencias_dono` de `docs/progresso/estado.json`, traz: a pergunta inteira (não um título), o contexto completo para entender sem abrir outro arquivo, e as opções com o efeito de cada uma. Quem lê pode ser o dono ou o sócio dele.
- Em `estado.json`, cada pendência tem `id` (fixo, nunca reaproveitado), `titulo`, `detalhe` (resumo de uma linha), `pergunta`, `contexto` (lista de parágrafos), `opcoes` (`id` = letra, `nome` e `efeito`) e `origem`. Uma pergunta = uma escolha; dois assuntos viram duas pendências. O painel e o roteiro (`tools/roteiro/gerar_roteiro.py`) mostram esses campos.
- O painel (https://claude.ai/artifact/7Kzo46Eyy8cQjF9HhuWMXg) tem votação e comentários por pergunta: componente `tools/votacao/` (embutido pelo `gerar_painel.py`), gravado no banco do artifact (coleção `votos`, um documento por pessoa com `respostas.<id da pergunta>` = `{opcao, comentario, em}`). Para ler: ArtifactData `list` em `votos` no link do painel. Ao republicar o painel, omitir `capabilities` para manter o banco. O roteiro só mostra as perguntas, com link para votar no painel. Ao decidir, a pendência sai do `estado.json` e entra em `decisoes`.
- Depois de mudar docs, artes aprovadas ou pendências, regerar e republicar o roteiro do sócio no mesmo link: https://claude.ai/artifact/5G5WBocgrp8NAeLKiF9FP8

## Pendências de decisão
- **PRIORIDADE MÁXIMA — Alinhamento de Contexto, Dupla e Escopo (`docs/design/20_alinhamento_ia_e_escopo.md`):** Antes de iniciar qualquer nova frente ou disparar subagentes, leia `docs/design/20_alinhamento_ia_e_escopo.md` e peça ao dono para decidir as duas pendências prioritárias em `docs/progresso/estado.json` (`fluxo-agentes-contexto` e `foco-fatia-vertical`). Não aprove artes nem decisões de design em nome do dono.
- Itens "confirmar na instalação" do `docs/tecnico/04_arquitetura.md`: conferir na Unity 6.3 instalada antes de o Frontend depender deles.
- O protótipo Godot F1 fica em `prototipos/godot-f1/` (`project.godot`, `autoload/`, `core/`, `data/`, `game/`, `scenes/`, `tests/`) como referência de game feel. Ele não faz parte do jogo Unity. Como rodar: `prototipos/godot-f1/COMO_RODAR.md`.

## Próximo passo
Etapa 2, fatia jogável da Cripta (ver `docs/design/15_etapas.md`): regras novas no core, tabelas novas, DLL real na Unity, layout da Cripta na escala A (`docs/tecnico/14_layout_cripta.md`), modelos 3D gerados pelo TripoSG a partir de `docs/arte/referencias-geracao/aprovadas/modelagem/` e cenário da Cripta.
