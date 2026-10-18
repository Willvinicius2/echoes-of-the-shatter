# 15 — Etapas do projeto

Projeto: **Echoes of the Shatter** · Documento criado em 16/10/2026 · Dono: william

Este documento divide o projeto em 5 etapas, na ordem em que acontecem. Ele não traz datas: uma etapa só começa a ser medida em prazo depois que a anterior fechar e o tempo real dela for conhecido (regra de `docs/design/00_plano_existente.md`, seção 11).

Fontes: `docs/design/00_plano_existente.md` (regras e escopo do jogo), `docs/requisitos-qa/01_plano_execucao.md` (agentes e donos de arquivo), `docs/requisitos-qa/02_requisitos.md` (RF, RNF e critérios), `docs/requisitos-qa/07_proximos_passos.md` (estado da equipe), `docs/arte/03_design_system.md` e `docs/tecnico/04_arquitetura.md` (arte e orçamentos).

## Convenções

- **[SC]** teste automático no ShatterCore (`ctest`). **[UE]** é o rótulo antigo de `docs/requisitos-qa/02_requisitos.md` para "conferido no motor"; vale hoje para o editor Unity ou um build. Neste documento, "[Unity]" substitui "[UE]".
- Um critério só conta como atendido com evidência registrada (comando e saída, captura de tela ou roteiro anotado). Quem registra: QA em `docs/requisitos-qa/10_qa.md`, Release & Verification em `docs/13_aceite.md`.
- Regra do `CLAUDE.md`: toda arte nova vai para aprovação do dono antes de entrar no jogo. Em todas as etapas, "o dono aprova" inclui isso.
- Agentes de design do jogo (conteúdo, narrativa, UI, revisões de design) usam no máximo Sonnet 5.5.
- Mapa de agentes e arquivos: tabela de `docs/requisitos-qa/01_plano_execucao.md`. Além dela, existe o engenheiro de **Integração ShatterCore ↔ Unity** (prompt em `docs/requisitos-qa/07_proximos_passos.md`) e a função de **Arte técnica** (graybox, modelos, rig).

## Visão geral

| # | Etapa | Estado | Prova de que fechou |
|---|---|---|---|
| 1 | Base técnica | Concluída em 16/10/2026 | Itens entregues listados abaixo |
| 2 | Fatia jogável da Cripta | Em andamento | O dono joga a Cripta inteira, com o Guerreiro final, e vence o Guardião |
| 3 | Ciclo completo do protótipo | Não iniciada | O dono completa o ciclo jogar, salvar, expedição, relatório e loot |
| 4 | Elenco e Ato I | Não iniciada | Três classes e 8 áreas, 4 chefes do Ato I jogáveis de ponta a ponta |
| 5 | Acesso Antecipado | Não iniciada | Build na Steam, validado no Steam Deck, com página da loja pronta para revisão |

---

## Etapa 1 — Base técnica (concluída em 16/10/2026)

**Objetivo:** ter o motor de regras, os dados e o projeto Unity de pé, com as decisões de câmera e escala tomadas, para que a produção de conteúdo comece sobre chão firme.

### Escopo
**Dentro (entregue):**
- **ShatterCore** em C++17 puro, com a **API C** (`shatter_c.h`) e a DLL que o Unity chama por P/Invoke. Cobre atributos e modificadores, golpe, RNG por fluxos, simulador de expedição, regras do idle, relógio offline e save com checksum e migração.
- **Tabelas de dados** em `EchoesOfTheShatter/Content/Data/` (CSV, localização pt_BR e en, esquemas) e o validador `tools/dados/validate_data.py`.
- **C# do protótipo** em `EchoesOfTheShatter/Assets/Scripts/` (módulos `Interop`, `Core`, `Gameplay`, `Presentation`, `UI`).
- **Cena base no Unity 6.3 LTS com URP** (`6000.3.26f1`), com os pacotes e o `.gitignore`/LFS configurados.
- **Câmera de 56 m** (pitch 55°, yaw 45°, FOV vertical 14,2°, faixa 48 a 66 m) e **escala de mapa** decididas (`docs/arte/03_design_system.md`, seção de escala; `docs/tecnico/04_arquitetura.md`, seção 3).
- **Graybox provisório** do herói, dos inimigos e do cenário (`art-src/graybox/`).
- Documentação de base: `docs/02` a `docs/10`, `docs/design/13_design_pendencias.md`.

**Fora:** qualquer regra nova de combate, arte final, conteúdo além do recorte do protótipo.

### Critérios de aceite (já verificados no fechamento; Release reconfere ao final da etapa 2)
| Critério | Ligação | Como verificar |
|---|---|---|
| ShatterCore compila e testa sem nenhum header do Unity | RNF-08 | `tools\core\build_core.cmd Release --werror` e `ctest` passam |
| Mesma seed + dados + snapshot = mesmo `resultHash`; 1 parte = N partes | RNF-01, RNF-02 | Testes de determinismo e de partes no `ctest` |
| Dados validados (IDs, referências, faixas, pesos) | RNF-07 | `python tools/dados/validate_data.py` passa; fixtures inválidos falham |
| Unity chama o core pela DLL (versão e layout conferidos) | RF-12 | Testes EditMode `Interop.VersionAndLayout` e `Rules.LoadContent` |
| Câmera e escala de mapa registradas | RF-59 | Valores presentes em `docs/03` e `docs/04`; `RenderSettingsAsset` rejeita valor fora de 48 a 66 m |

### Agentes e dependências
Fase 1 de `docs/01`: Vision Lead, Tech Lead, Art Director. Fase 2: Data Engineer, Backend Engineer, Frontend Engineer, Integração, Arte técnica. Sem dependências anteriores além de `docs/design/00_plano_existente.md`.

### O que o dono aprovou
Motor (Unity 6.3 LTS), direção visual 3D (folhas em `docs/arte/referencias-geracao/`), câmera de 56 m e escala de mapa.

---

## Etapa 2 — Fatia jogável da Cripta (em andamento)

**Objetivo:** o dono joga a Cripta Partida do início ao Guardião, no Unity, com o Guerreiro e os inimigos finais, e o combate passa no teste de fogo do pilar 1.

### Em produção agora
Todas as frentes abaixo estão abertas. Nenhuma está marcada como concluída neste documento; o fechamento de cada uma é registrado em `docs/requisitos-qa/10_qa.md` e `docs/13_aceite.md`.

| Frente | O que é | Responsável | RF/RNF |
|---|---|---|---|
| Core | Regras novas no ShatterCore: poções, Guarda Quebrada (quebra de guarda), Guardião com fases e invocação, elites com modificador, IA por família de inimigo | Backend | RF-06 a RF-10, RF-14, RF-19, RF-20 a RF-24, RNF-01, RNF-02 |
| Dados | CSV do Guerreiro, 3 habilidades, esquiva, poções, 4 inimigos, elites, Guardião, encontros da Cripta, com números do plano e o que for provisório marcado | Data Engineer, Narrative & Content | RNF-07, RNF-10 |
| DLL real | Substituir o `FakeShatterNative` pela DLL `shattercore_dll` real na Unity, com os testes de Interop e do golden | Integração | RF-12, RNF-01, RNF-08 |
| Layout da Cripta | Cripta montada na escala aprovada, com início, salas, checkpoints, arena do Guardião e encontros posicionados | Frontend, Art Director | RF-18, RF-20 a RF-24, RF-50 (evento de vitória) |
| Textos | Chaves pt_BR e en de HUD, habilidades, inimigos, avisos e falas; sem texto literal em C# ou UXML | Narrative & Content (Sonnet 5.5) | RF-61, RF-63 |
| QA | Testes `qa_*` para as regras novas; matriz requisito, teste e resultado | QA Engineer | todos os [SC] da etapa |
| Revisão | Revisão de código do core, da DLL e do C# contra `docs/04` | Code Reviewer | RF-12, RNF-07, RNF-08 |
| Modelos 3D | Guerreiro e inimigos da Cripta (Sentinela Oca, Cão-de-Cinza, Arauto de Pedra, Arqueiro Fantasma, Guardião): gerados por IA a partir das folhas aprovadas, pintados à mão, com esqueleto | Arte técnica, Art Director | RF-59 |
| Cenário | Cenário da Cripta (módulos, materiais, névoa, iluminação) no estilo aprovado | Arte técnica, Art Director | RF-59 |

### Vem depois dentro da etapa (depende das frentes acima)
- **HUD completo** (RF-57, RF-45 na parte do ícone de Fervor): depende de poções, cargas de esquiva e recursos do core e dos textos.
- Integração dos modelos finais com Animator, hitstop, telegraph e números de dano sobre o esqueleto real (RF-13, RF-15, RF-17).
- Passagem de desempenho na Cripta com 30 inimigos (RNF-04) e do simulador (RNF-03), pelo Performance Engineer.
- Aceite da etapa pelo Release & Verification.

### Escopo
**Dentro:** tudo o que está nas duas listas acima, mais Corte de Ferro, Investida e Fenda de Pedra funcionando com juice mínimo (RF-17), morte e retorno ao checkpoint (RF-18), os 4 inimigos e o Guardião com 2 fases (RF-21 a RF-24).
**Fora:** save/load, Ilsa e Tico funcionais, expedição na interface, inventário e loot na interface, Único (tabela e drop), menus, áudio final, qualquer área além da Cripta, Arqueiro e Mago.

### Critérios de aceite
| Critério | RF/RNF | Verificação |
|---|---|---|
| Fórmula de atributos, ordem do golpe e tetos 70/50/75% passam nos testes | RF-01, RF-06 | [SC] `ctest` |
| Poção com 0 cargas não faz nada e avisa; cargas e recarga batem com o CSV | RF-19 | [SC] + [Unity] |
| Esquiva: dano 0 aos 0,1 s, dano aos 0,3 s, 4ª esquiva seguida negada, carga volta em 1,5 s | RF-15 | [SC] + [Unity] |
| Guardião: todo ataque com telegraph de 0,7 a 1,2 s com forma no chão e som; golpe frontal no escudo erguido causa 0 de dano à vida; fase 2 invoca exatamente 2 Sentinelas | RF-23 | [SC] + [Unity] |
| Mesma seed gera a mesma sequência de padrões; seeds diferentes divergem em 90% ou mais de 100 seeds | RF-24 | [SC] |
| Cada um dos 4 inimigos passa pelos 5 estados; Cão-de-Cinza foge abaixo do limiar; Arqueiro Fantasma mantém distância mínima | RF-20, RF-21 | [Unity] com log de debug |
| Elite "escudo" e "veloz" com realce, nome e mais vida que o comum | RF-22 | [Unity] |
| Morrer na Cripta volta ao checkpoint sem perder XP nem itens; morrer no Guardião reinicia a luta em menos de 2 s | RF-18 | [Unity] |
| Mesmo roteiro de entrada a 30 e a 144 FPS dá o mesmo dano total | RF-11 | [SC+Unity] |
| Nenhum cálculo de dano no C# fora de chamadas ao core | RF-12 | Revisão de código + busca textual |
| DLL real: `Interop.VersionAndLayout`, `Rules.LoadContent`, `Rules.GoldenExpedition` passam na CLI do Unity com o mesmo `resultHash` do `ctest` | RNF-01, RNF-08 | Testes EditMode |
| HUD com os 7 elementos em 1080p, sem sobreposição; texto pt_BR sem corte | RF-57, RF-63 | [Unity] captura em 1920x1080 |
| Guerreiro e inimigos reconhecíveis pelas folhas oficiais; cores da UI batem com os tokens; capturas em 1920x1080 e 1280x800 legíveis | RF-59 | [Unity] captura + revisão do dono |
| Herói com 88 px (1080p) e 65 px (800p) de altura de tela na câmera de 56 m, com tolerância do doc 03 | RF-59 | Medição em captura |
| 60 FPS estáveis na Cripta com 30 inimigos no PC de entrada; carregamento da área abaixo de 3 s | RNF-04 | Profiler, registrado em `docs/12_performance.md` |
| Simulação de 12 h abaixo de 2 s (Release) | RNF-03 | Benchmark do core |
| Teste de fogo do pilar 1: o dono joga 30 s contra Sentinelas e descreve o combate como satisfatório | Portão de `docs/02`, seção 5.8 | Playtest do dono, anotado em `docs/13_aceite.md` |

### Agentes e dependências
- **Backend** (core) e **Data Engineer** + **Narrative & Content** (dados e textos) começam juntos; os dados dependem dos nomes de campo do core.
- **Integração** depende do core estável na API C; qualquer mudança de contrato vai em `docs/tecnico/09_mudancas_contrato.md`.
- **Frontend** (layout, HUD, controle de personagem) depende da DLL real e dos textos.
- **Arte técnica** (modelos e cenário) depende das folhas aprovadas; a integração dos modelos no Frontend só começa depois da aprovação do dono.
- **QA**, **Code Reviewer** e **Performance** entram sobre o que cada frente entregar; **Release & Verification** fecha a etapa.

### O que o dono aprova
1. Modelos 3D finais do Guerreiro e de cada inimigo da Cripta (antes de entrarem no jogo).
2. Cenário da Cripta (arte e atmosfera).
3. Layout da Cripta (ordem das salas, encontros, arena).
4. Teste de fogo do combate (30 s contra Sentinelas) e o aceite final da etapa.
5. Decisões provisórias do core ainda abertas em `docs/requisitos-qa/07_proximos_passos.md`: fórmula de armadura, se o bloqueio anula o golpe inteiro, limiar de recuo do idle.

---

## Etapa 3 — Ciclo completo do protótipo

**Objetivo:** o jogador completa o ciclo inteiro do jogo (lutar, dominar a Cripta, sair, voltar, coletar a expedição, usar o loot) em um save que sobrevive a fechar o jogo.

### Escopo
**Dentro:**
- **Save/load** em 1 slot, com gravação segura, 3 backups, checksum, migração e autosave (RF-51 a RF-56), e a linha do tempo UTC (RF-46 a RF-49).
- **Domínio da Cripta** gravado ao vencer o Guardião, com cargas do Marco (RF-50, RF-35).
- **Expedição idle**: configuração na Ilsa com regras de IA, previsão em faixa com o **selo "Estimativa"** (IdleProfiles não calibrados), simulação ao abrir o jogo fora da thread de jogo, relatório do Tico (RF-31 a RF-45, RF-60).
- **Menus**: principal, opções (idioma, remapeamento, tremor de tela), inventário, configuração e relatório (RF-58, RF-62, RF-64, RF-65, RNF-11).
- **Loot e inventário**: tabelas, afixos, nomes com gênero, feixes por raridade, 5 posições de equipamento, comparação (RF-25 a RF-30).
- **Único do Guardião** (RF-27) com coluna de luz e som próprios.
- **Playtest do dono** com roteiro (docs/requisitos-qa/10_qa.md).

**Fora:** Steam, Arqueiro, Mago, áreas além da Cripta, crafting com o Bram, livros e Sigilos, árvore passiva, espanhol, teste de paridade com bot (adiado em P-3 de `docs/02`, seção 7).

### Critérios de aceite
| Critério | RF/RNF | Verificação |
|---|---|---|
| Expedição recusada sem domínio da Cripta (inclusive se a área foi limpa sem vencer o Guardião) | RF-31 | [SC+Unity] |
| Idle sem Fervor rende 35% do XP/hora do manual (±5 p.p.); Ouro e materiais ×1,25 com Fervor | RF-32 | [SC] |
| Teto de nível: personagem 2 níveis acima da área não ganha XP no idle | RF-33 | [SC] |
| Em 10 mil expedições de 12 h: 0 Únicos, 0 livros de especialização, 0 Sigilos raros, 0 entradas de mapa, no máximo 4 Raros | RF-34 | [SC] |
| Cargas (teto 12, +1/+2/+3, descanso +4 por dia UTC sem acumular) e Vigor 100/70/40% | RF-35, RF-36 | [SC] |
| Uma expedição por vez; configuração com 7 regras ou duração fora de 1 a 12 h é impossível | RF-37, RF-39 | [SC+Unity] |
| Snapshot congelado; recuo por falta de vida ou poção; loot do que foi vencido é entregue | RF-38 | [SC] |
| Faixa prevista contém o resultado real em 80% ou mais de 1000 expedições | RF-40 | [SC] |
| Habilidade sem IdleProfile bloqueia a expedição com mensagem localizada | RF-43 | [SC+Unity] |
| Selo "Estimativa" visível na previsão e no relatório enquanto os IdleProfiles não forem calibrados | P-3 de `docs/02` | [Unity] |
| Relatório mostra os 6 campos, a dica e o botão "Jogar esta rota agora" | RF-44 | [Unity] |
| Nenhum percentual negativo nas strings de UI; HUD manual mostra o ícone do Fervor e "+200% XP" | RF-45 | [SC+Unity] |
| Relógio: expedição de 4 h iniciada há 10 h simula 4 h; relógio voltando mais de 5 min encerra sem tempo extra; adiantar o relógio não rende mais que a duração | RF-46 a RF-49, RNF-09 | [SC] |
| Save: queda após `.tmp` mantém o anterior; 3 backups; 1 byte alterado falha o checksum; corrompido carrega o backup e avisa | RF-52, RF-53 | [SC+Unity] |
| Coleta sem duplicar mesmo com queda entre cálculo e gravação | RF-55 | [SC] |
| Migração v1 para v2 sem perda de campos; save com `content_version` maior é recusado sem ser alterado | RF-56, RNF-10 | [SC] |
| 1000 ciclos salvar/carregar sem divergência | RNF-05 | [SC] |
| Loot: pesos dentro de ±1% em 1 milhão de sorteios; Mágico até 2 afixos, Raro até 4; 0 Únicos fora do Guardião | RF-25 a RF-27 | [SC] |
| Nomes com concordância correta em amostra de 20 nomes pt_BR | RF-28 | Revisão humana |
| Equipar e desequipar muda atributos no mesmo quadro; cada raridade com feixe distinto | RF-29, RF-30 | [Unity] |
| Telas abrem e fecham por mouse e Esc; trocar idioma sem reiniciar; remapear esquiva persiste | RF-58, RF-62, RF-65 | [Unity] |
| Simulação de 12 h ao abrir o jogo não congela a tela | RF-60, RNF-03 | [Unity] |
| Jogo funciona com a rede desligada | RNF-06 | [Unity] |
| Playtest do dono: completa o ciclo e anota o que não entendeu | Pilar "planejar o retorno" | Roteiro de `docs/requisitos-qa/10_qa.md` |

### Agentes e dependências
Depende da etapa 2 fechada (domínio só existe se o Guardião estiver vencível). **Backend** (save, relógio, loot), **Data Engineer** + **Narrative & Content** (tabelas de loot, afixos, textos de relatório), **Frontend** (menus, inventário, expedição), **Arte técnica** (ícones, feixes, Único), **QA**, **Code Reviewer**, **Performance** e **Release & Verification**.

### O que o dono aprova
Telas de menu, inventário e relatório; ícones; modelo e efeito do Único; texto do selo "Estimativa"; resultado do playtest; decisão de calibrar ou não os IdleProfiles já nesta etapa (hoje adiada).

---

## Etapa 4 — Elenco e Ato I

**Objetivo:** o jogo cobre o Ato I inteiro com as três classes e os quatro chefes, no ritmo do plano (8 a 12 h de campanha, em conjunto com o endgame inicial a decidir).

### Escopo
**Dentro** (fonte: `docs/design/00_plano_existente.md`, seções 2 a 5):
- **Arqueiro** (Foco) e **Mago** (Mana), com as habilidades de cada classe, e IdleProfiles de cada habilidade jogável.
- **Demais inimigos** das 4 famílias do Ato I e elites.
- **Chefes do Ato I**: Tecelã de Cascalho, Carrasco do Voto e Vigia do Sino (o Guardião vem da etapa 2).
- **Áreas do Ato I**: Estrada das Lanternas, Pedreira dos Ecos, Ponte do Sino, Armazém de Cinzas, Pátio dos Marcos, Túneis do Voto, Mirante Partido (e a Cripta já feita).
- Elementos que o Ato I exige: livros, Sigilos, Bram (crafting), Irmã Odete, árvore passiva, especializações no nível 10, nível máximo do Ato I (15).
- Música das áreas do Ato I e efeitos-chave.

**Fora:** Steam, Assassino e Necromante, Atos II e III, endgame (Carta dos Marcos, Predador dos Marcos) a menos que o dono decida incluí-lo nesta etapa (pergunta aberta abaixo), coop, espanhol.

### Critérios de aceite
Os RF/RNF de `docs/requisitos-qa/02_requisitos.md` cobrem só o protótipo. **Antes de a etapa começar, o Vision Lead estende `docs/requisitos-qa/02_requisitos.md`** com RF novos para classes, livros, Sigilos, crafting, árvore e chefes; a lista abaixo é o que já se sabe verificar.

| Critério | Origem | Verificação |
|---|---|---|
| Cada classe com recurso próprio (Ímpeto, Foco, Mana) e 8 habilidades (6 espaços na barra) | Plano, seção 4 | [Unity] + [SC] nos custos |
| Cada habilidade jogável tem IdleProfile testado, ou a expedição é bloqueada com mensagem | RF-43 | [SC] |
| Cada chefe tem a mecânica central e o número de fases da tabela do plano (2, 2... conforme seção 5), telegraph de 0,7 a 1,2 s com forma e som | RF-23 estendido | [SC+Unity] |
| Cada área com checkpoint, encontros e domínio gravado só ao vencer a área e o chefe, quando houver | RF-31, RF-50 | [SC+Unity] |
| Três builds da mesma classe se jogam de forma visivelmente diferente | Pilar "build com identidade" | Playtest do dono |
| Nenhuma build acima de 50% de uso por classe (métrica do plano) | Plano, seção 12 | Telemetria de playtest, se houver |
| Proteção contra azar: todo livro básico comprável da Irmã Odete depois de visto | Plano, seção 6 | [Unity] |
| Crafting nunca destrói o item e avisa antes de perder uma combinação | Plano, seção 6 | [Unity] |
| Orçamento por área mantido (memória, batches, triângulos, 80 inimigos na tela com 60 FPS no PC de entrada) | RNF-04 e `docs/04` seção 18 | Profiler |
| Teste de paridade combate x simulador implementado e dentro de 10% (meta de 5% no Acesso Antecipado) | Plano, seção 10; P-3 | [SC] com bot headless |
| Modelos de classes e inimigos reconhecíveis pelas folhas aprovadas | RF-59 | Revisão do dono |

### Agentes e dependências
Depende da etapa 3 (save, expedição, loot e menus existentes, porque as áreas novas reutilizam todos). **Vision Lead** (novos RF), **Narrative & Content** (Sonnet 5.5; textos, falas, livros, Sigilos), **Data Engineer**, **Backend** (classes, chefes, paridade), **Frontend**, **Arte técnica** e **Art Director** (modelos, cenários), **QA**, **Code Reviewer**, **Performance**, **Release & Verification**.
Dentro da etapa, a ordem sugerida é uma classe ou área por vez, com portão de QA a cada uma, para a regra "nenhuma fase começa antes do portão da anterior" valer em escala menor.

### O que o dono aprova
Cada classe nova (modelo, habilidades, sensação), cada chefe, cada área (arte e layout), balanceamento da curva de XP (hoje "ajustada em playtest"), decisão sobre incluir o endgame, valores finais das regras do idle (35% de XP, cargas, teto de nível) após o playtest.

---

## Etapa 5 — Acesso Antecipado

**Objetivo:** publicar o jogo na Steam em Acesso Antecipado, funcionando no PC de entrada e no Steam Deck, com página da loja aprovada pelo dono.

### Escopo
**Dentro:**
- **Steamworks.NET**: conquistas (as de expedição só contam as de expedição, as demais só no jogo manual), Steam Cloud (Auto-Cloud com a pasta de saves), conferência de relógio com a Steam (`GetServerRealTime`, diferença de 10 min), Rich Presence e overlay.
- **Steam Deck**: controle com ações nomeadas, UI legível em 1280x800, desempenho medido à parte.
- **Desempenho**: metas finais de `docs/04` seção 18 e do plano (60 FPS, 80 inimigos, carga abaixo de 3 s, 12 h de idle abaixo de 2 s, build abaixo de 500 MB).
- **Build** Windows IL2CPP, SteamPipe, branches `default`, `beta` e `playtest`, versão visível no menu.
- **Página da loja**: pitch em inglês reescrito para 3D (o do plano ainda diz pixel art), cápsulas, trailer, capturas, classificação indicativa, declaração de uso de IA, política de privacidade.
- Registros e conformidade do checklist F3 a F5 de `docs/design/00_plano_existente.md`, seção 13.

**Fora:** Atos II e III, Assassino, Necromante, coop, marketplace, microtransações, cosméticos pagos.

### Critérios de aceite
| Critério | Origem | Verificação |
|---|---|---|
| Conquistas aparecem na Steam e respeitam a regra manual x expedição | Plano, seção 7 | Teste manual no app de testes |
| Save sobe e desce pelo Steam Cloud entre dois PCs; conflito mostra data, nível e tempo de jogo | Plano, seção 10 | Teste manual |
| Relógio da Steam sobrepõe o do PC quando a diferença passa de 10 min | Plano, seção 10; RNF-09 | [SC] com relógio simulado + manual |
| Sem rede, o jogo continua funcionando (Steam opcional) | RNF-06 | Manual com rede desligada |
| 60 FPS estáveis no PC de entrada (GTX 1050 Ti / RX 570, 4 núcleos, 8 GB, 1080p); meta separada medida no Steam Deck | RNF-04, P-4 | Profiler e `docs/12_performance.md` |
| Carregamento de área abaixo de 3 s; simulação de 12 h abaixo de 2 s; build abaixo de 500 MB | Plano, seção 10 | Medição registrada |
| Controle e Steam Deck: todas as ações mapeadas; texto legível em 1280x800 | RF-59, RF-65 | Captura e teste no aparelho |
| Teste de paridade e de saves de todas as versões publicadas passam em CI | Plano, seção 10 | CI |
| Questionário de classificação indicativa preenchido; uso de IA declarado; política de privacidade publicada | Plano, seção 13 | Checklist de Release |
| Todo asset do jogo e da página é original ou tem licença registrada; nenhum asset do Spell Brigade | `CLAUDE.md` | Auditoria de assets |
| Build candidato passa em `ctest`, validador de dados, EditMode e PlayMode, e o teste de jogador IL2CPP tem `resultHash` igual ao golden | `docs/13_aceite.md` | Evidência em `docs/13_aceite.md` |
| Telemetria (se houver) é opt-in, sem IP nem ID da Steam | Plano, seções 10 e 13 | Revisão |

### Agentes e dependências
Depende da etapa 4 fechada (o conteúdo vendido tem que existir). **Frontend** e **Integração** (Steamworks.NET, entrada), **Performance Engineer** (Deck e orçamentos), **Release & Verification** (build, SteamPipe, aceite), **Art Director** + **Arte técnica** (cápsulas, capturas), **Narrative & Content** (texto da loja, pt_BR e en), **Code Reviewer** (segurança do save e da Steam).
Itens do dono que não são de agente: CNPJ, taxa do Steam Direct, formulário fiscal, registro de marca (INPI/USPTO) e revisão jurídica. Eles bloqueiam a publicação, não o código.

### O que o dono aprova
Página da loja (textos, capturas, cápsulas, trailer), preço final, declaração de uso de IA, classificação indicativa, nome e marca, o build candidato e a promoção da branch `beta` para `default` (sempre manual, no painel do Steamworks).

---

## Perguntas abertas para o dono

As perguntas deste documento, cada uma com o contexto completo e as opções, ficam em `pendencias_dono` de `docs/progresso/estado.json`. Elas aparecem em "Perguntas para decidir" no roteiro e em "Aguardando você" no painel:

1. Endgame na etapa 4 ou numa etapa própria.
2. Vencer o Guardião sem loot na etapa 2.
3. Demo para o Steam Next Fest.
4. Calibração do idle na etapa 4 ou antes.
5. Quem faz a capa e as cápsulas da Steam.
6. CNPJ, Steam Direct e registros: quem cuida.
7. CNPJ e página na Steam: quando começar.
