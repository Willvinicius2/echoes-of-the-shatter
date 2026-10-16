# 01 — Plano de execução (Orchestrator)

Projeto: **Echoes of the Shatter** — ARPG single-player em pixel art com expedições idle.
Fonte de verdade de design: `docs/00_plano_existente.md` (Plano Steam v2.0, 13/10/2026).
Decisão do usuário em 15/10/2026: **motor Unreal Engine 5** (substitui Godot 4 do plano), entrega = **documento + protótipo**.

## Objetivo desta rodada: "a base do jogo"
1. Documentação de base adaptada a UE5 (requisitos, design system, arquitetura, conteúdo, dados).
2. Protótipo em duas camadas:
   - **ShatterCore** — motor de regras em C++17 puro (sem dependência do Unreal): atributos e modificadores, cálculo de golpe, RNG determinístico por fluxos, simulador de expedição, regras do idle, save JSON com checksum e migração. Compilado e testado no workspace (CMake + testes).
   - **Projeto UE5** (`EchoesOfTheShatter/`) — módulo de jogo C++ que usa o ShatterCore: personagem jogável, inimigo com máquina de estados, HUD/UMG, subsistema de save e de expedição, DataTables. Não compila aqui (sem o editor); revisado por leitura.

## Fases e dependências
| Fase | Agentes (em paralelo) | Depende de |
|---|---|---|
| 1. Definição | Vision Lead, Tech Lead, Art Director | plano existente |
| 2. Construção | Data Engineer, Narrative & Content, Backend Engineer, Frontend Engineer | Fase 1 |
| 3. Verificação | QA Engineer, Code Reviewer, Performance Engineer | Fase 2 |
| 4. Correções | Backend/Frontend (se houver defeito bloqueante) | Fase 3 |
| 5. Aceite | Release & Verification | Fases 1–4 |

## Regras de trabalho para todos os agentes
- Escrever em português do Brasil; identificadores de código e IDs de conteúdo em inglês (`skill.warrior.iron_cut`).
- Não inventar regra de design que contradiga `00_plano_existente.md`; quando UE5 exigir mudança, registrar em "Desvios do plano".
- Cada agente só escreve nos seus arquivos (tabela abaixo) e lê os dos outros.
- Números de balanceamento nunca no código: vão em `EchoesOfTheShatter/Content/Data/*.csv`.

## Responsáveis e arquivos
| Agente | Entrega | Arquivos |
|---|---|---|
| Orchestrator | Plano e estado das tarefas | `docs/01_plano_execucao.md` |
| Vision Lead | Requisitos e critérios de aceite | `docs/02_requisitos.md` |
| Art Director | Design system e specs de interface | `docs/03_design_system.md` |
| Tech Lead | Arquitetura e contratos técnicos | `docs/04_arquitetura.md`, headers públicos em `ShatterCore/include/` |
| Narrative & Content | Textos, localização, conteúdo estruturado | `docs/05_conteudo.md`, `Content/Data/Loc*.csv` e linhas de conteúdo |
| Data Engineer | Esquemas, migrações, validações | `docs/06_dados.md`, `tools/validate_data.py`, `Content/Data/schemas/` |
| Backend Engineer | Motor de regras, persistência e testes | `ShatterCore/src/`, `ShatterCore/tests/` |
| Frontend Engineer | Interface e jogo no UE5 | `EchoesOfTheShatter/Source/EchoesOfTheShatter/` |
| QA Engineer | Testes reproduzíveis e defeitos | `docs/10_qa.md`, `ShatterCore/tests/qa_*` |
| Code Reviewer | Problemas e recomendações | `docs/11_code_review.md` |
| Performance Engineer | Medições e otimizações | `docs/12_performance.md`, `ShatterCore/bench/` |
| Release & Verification | Checklist de aceite e evidências | `docs/13_aceite.md` |

## Estado das tarefas
Ver `docs/07_proximos_passos.md` (Fase 1 concluída; Fase 2 interrompida em 15/10/2026 para migração ao Claude Code).

Ajustes do dono durante a execução: equipe com os 12 papéis da tabela (não 10); motor Unreal Engine 5; agentes de design do jogo usam no máximo Sonnet 5.5.
