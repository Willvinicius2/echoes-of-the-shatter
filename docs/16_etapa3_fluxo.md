# 16 — Etapa 3: fluxo do protótipo, telas, loot e aceite (Game Designer)

Projeto: **Echoes of the Shatter** · Documento criado em 17/10/2026 · Dono do texto: Game Designer · Escopo: Etapa 3 de `docs/15_etapas.md` ("Ciclo completo do protótipo").

Este documento só especifica. Nenhum CSV, esquema, header ou código foi alterado. Onde um dado ou uma API precisa existir, a seção 9 lista o pedido ao Data Engineer, ao Backend e ao Tech Lead (propostas, não imposições). A história é do dono do projeto: nada aqui cria personagem, arco ou lore; todo texto de NPC já existe em `Loc/dialogue.csv` e continua provisório.

Fontes lidas: `CLAUDE.md`, `docs/15_etapas.md` (Etapa 3), `docs/00_plano_existente.md` (seções 3, 6, 7), `docs/02_requisitos.md` (RF-25 a RF-65), `docs/03_design_system.md` (2.3, 3.11, 4.1 a 4.6), `docs/04_arquitetura.md` (17.4), `docs/05_conteudo.md`, `docs/06_dados.md`, `docs/13_design_pendencias.md`, `docs/14_layout_cripta.md` (portais, baús), `Content/Data/*.csv` e o código em `Assets/Scripts` e `ShatterCore/include`.

Convenções: **[SC]** teste automático no ShatterCore, **[Unity]** conferido no editor ou num build, **[Manual]** roteiro anotado. **[HIPÓTESE]** = número ou regra que só o playtest valida. IDs deste documento: `F-xx` (passos do fluxo), `S-xx` (telas), `A3-xx` (critérios de aceite), `H3-xx` (hipóteses), `Q3-x` (perguntas ao dono). Eles não mudam depois de publicados.

Pilares (de `docs/02`, seção 1): **P1** Conquistar pela ação, **P2** Build com identidade, **P3** Planejar o retorno, **P4** Respeitar o tempo. Cada mecânica abaixo diz a que pilar serve.

---

## 1. O loop em resumo

**Loop de 2 linhas.** O jogador sai do Refúgio, abre a Cripta na mão, vence o Guardião (domínio, cargas do Marco e o Único), volta, configura uma expedição e fecha o jogo. Ao reabrir, o Tico entrega um relatório com a dica de uma decisão (trocar peça, ajustar regra), o jogador veste o loot (o boneco muda de visual) e escolhe entre outra expedição ou "Jogar esta rota agora".

```
Boot -> Menu inicial -> Slots de save -> (Novo jogo: nome) -> REFÚGIO
   ^                                                            |
   |                                  portal.crypt.entry (sempre ativo)
   |                                                            v
   |                           CRIPTA (combate, loot no chão, checkpoints)
   |                               morte -> "Você caiu" -> checkpoint (sem perda)
   |                                                            |
   |                                         Guardião vencido (1ª vez: Único garantido)
   |                                  domínio gravado + 5 cargas + portal.crypt.exit
   |                                                            v
   +<-------------------- REFÚGIO <------------------------------+
        Ilsa: configurar e iniciar expedição ---> fechar o jogo (ou acelerador de debug)
        reabrir -> "O Tico está voltando..." -> Relatório (selo "Estimativa") -> Coletar
        Inventário: equipar, comparar, vender, descartar -> boneco muda
        "Jogar esta rota agora" -> CRIPTA (Fervor, Únicos)    |   ou nova expedição
```

**Pilares servidos.** P1: a expedição só abre depois do Guardião vencido na mão. P3: o relatório fecha com uma dica acionável e a previsão em faixa pede uma decisão antes de iniciar. P4: sessão curta rende (checkpoints, autosave, coleta em um clique) e expedição de 1 h existe. P2: o inventário só importa se o loot muda a forma de jogar, por isso o Único (efeito + contrapartida) e afixos que mexem em dano, crítico, velocidade e vida estão no recorte.

---

## 2. Fluxo passo a passo

Cada passo diz a tela, o que o jogador faz, o que o jogo grava e o RF. Auto-save segue RF-54: ao trocar de área, ao coletar expedição, ao sair e a cada 5 min no jogo manual.

| ID | Passo | Jogador | Jogo | Grava | RF |
|---|---|---|---|---|---|
| F-01 | Abrir o jogo | Inicia o executável | Carrega a DLL e o conteúdo (`S-00`); confere versão do conteúdo; abre o menu | Nada | RF-12, RNF-10, RNF-11 |
| F-02 | Menu inicial (`S-01`) | Continuar, Novo jogo, Carregar, Opções ou Sair | "Continuar" abre o slot com `last_seen` mais recente; sem save, só "Novo jogo" | Nada | RF-58 |
| F-03 | Escolher slot (`S-02`) | Seleciona um cartão vazio ou ocupado | Slot ocupado carrega; backup usado mostra aviso; versão nova de save recusa sem alterar o arquivo | Nada | RF-53, RF-56, RNF-10 |
| F-04 | Criar personagem (`S-03`) | Digita o nome (1 a 16 caracteres) e confirma "Guerreiro" | Cria `CharacterState` nível 1, kit inicial (6 peças Comuns `vset.starter`), poções cheias, 0 cargas, 0 Ouro | Primeiro save do slot | RF-51 |
| F-05 | Refúgio (`S-04`) | Anda (WASD), fala com Ilsa e Tico (ainda sem função), abre o inventário (`I`) | Sem combate; poções enchem ao entrar; dica de controle em toast só na primeira vez | Auto-save ao entrar | RF-57, RF-64 |
| F-06 | Entrar na Cripta | Atravessa o portal da Cripta no Refúgio | Troca de cena com fade; `portal.crypt.entry` na volta; faixa com o nome da área por 3 s | Auto-save (troca de área) | RF-54 |
| F-07 | Combate e loot | Luta; passa por checkpoints; abre baús; anda sobre os itens para pegá-los | Inimigos largam loot com a tabela do inimigo (seção 4.5); feixe e rótulo por raridade; XP; Ímpeto; poções | Auto-save a cada 5 min e ao passar em checkpoint | RF-13 a RF-19, RF-25, RF-29 |
| F-08 | Morrer | Vê "Você caiu" e volta | Volta ao checkpoint, sem perder XP nem itens; inimigos reaparecem; na arena a luta reinicia em menos de 2 s | Auto-save | RF-18 |
| F-09 | Vencer o Guardião (`S-13`) | Mata o Guardião | Banner de vitória; **1ª vitória: Único garantido**; chama `RecordAreaRun` (domínio, +5 cargas, teto 12); `portal.crypt.exit` aparece; Ilsa muda de fala | Domínio, cargas, contador do chefe e loot, **antes** de entregar o Único | RF-27, RF-35, RF-50, RF-55 |
| F-10 | Voltar ao Refúgio | Pega o loot e entra em `portal.crypt.exit` | Troca de cena; poções cheias; HUD sem Fervor | Auto-save (troca de área) | RF-54 |
| F-11 | Configurar e iniciar expedição (`S-08`) | Fala com Ilsa; escolhe Cripta, objetivo, até 6 regras, duração | Previsão em faixa com o selo "Estimativa"; confirma "build e regras ficam congeladas"; desconta cargas | Expedição `Running` com snapshot, seed, início, duração | RF-31, RF-35 a RF-40, RF-43 |
| F-12 | Esperar | Fecha o jogo (ou usa o acelerador de debug: 1 h = 10 s) | Com expedição ativa o herói está em rota: portal da Cripta bloqueado com a fala `dlg.ilsa.busy` (Q3-2) | `last_seen` ao sair | RF-46, RF-48 |
| F-13 | Reabrir e coletar (`S-09`) | Abre o jogo, fala com o Tico ou vê o relatório direto | "O Tico está voltando..." (simulação fora da thread de jogo, meta < 2 s); relatório com 6 campos, dica e convite; selo "Estimativa" | Coleta e status `Collected` no mesmo salvamento | RF-44, RF-47, RF-55, RF-60 |
| F-14 | Vestir o loot (`S-05`) | Abre o inventário, compara, equipa, vende ou descarta | Atributos mudam no mesmo quadro; o boneco troca a peça (visual por `visualSetId`, tinta por raridade) | Auto-save ao fechar o inventário | RF-29, RF-30 |
| F-15 | Fechar o ciclo | "Jogar esta rota agora" ou "Coletar e nova expedição" | Vai à Cripta (Fervor ativo, Único possível) ou reabre `S-08` com a última configuração | Auto-save | RF-32, RF-44 |

Notas do fluxo:

1. **Corrida (run) e domínio.** Uma corrida começa ao entrar na Cripta pelo Refúgio e termina ao voltar a ele. Morrer e voltar ao checkpoint **não** encerra a corrida. O domínio exige chegar à arena e vencer o Guardião **na mesma corrida** (RF-50, `RecordAreaRun`). `reachedEnd` = o herói cruzou o gatilho da arena [HIPÓTESE H3-01, ver 4.6 sobre farm de cargas].
2. **Salvar antes de entregar.** O contador de vitórias do chefe é gravado antes de o item cair no chão (RF-55); se o jogo cair entre o golpe final e o save, o Único não é perdido nem duplicado.
3. **Cargas do primeiro ciclo.** A primeira conquista dá +5 cargas (2 do chefe, 3 de área nova; nota de `docs/13` R2.4 e `save.h`). Logo a primeira expedição vai de 1 a 5 h. Isso é desejado: a decisão "5 h agora ou 2 h e guardar cargas?" aparece cedo (P3) [HIPÓTESE H3-02].
4. **Descanso diário** (+4 cargas por dia UTC, sem acumular) é aplicado ao abrir o jogo e avisado por toast `ui.hud.charges`.

---

## 3. Telas

Medidas em 1920 × 1080, estilo UI de pedra escura e tokens de `docs/03` (`nine_panel_ornate`, cores de `03_design_tokens.json`). A posição de cada bloco já está em `docs/03`, seção 4; aqui ficam objetivo, informação, ação e estado. Toda string vem de chave de localização (RF-61); chaves **novas** estão marcadas com (nova).

### S-00 Carregando
- **Objetivo:** esconder a carga da DLL e do conteúdo e dar erro legível se algo falhar.
- **Informação:** logo, barra indeterminada, `ui.loading.generic`.
- **Ações:** nenhuma. Se `Rules.LoadContent` falhar: tela de erro com "Abrir pasta de logs" e "Sair" (nova: `ui.error.content_load`).
- **Regras:** carregamento da área da Cripta < 3 s (RNF-04).

### S-01 Menu inicial (`MainMenuView`, `docs/03` 4.5)
- **Objetivo:** levar o jogador ao jogo em um clique.
- **Informação:** logo; botões; legenda do "Continuar" (nome, classe, nível, área); selo "Expedição pronta" quando houver relatório; versão no canto (`ui.menu.version`, RNF-11); link "Abrir pasta de logs".
- **Ações:** Continuar (primário se existir save), Novo jogo, Carregar (abre S-02), Opções (S-11), Sair. **Créditos** fica fora do protótipo.
- **Estados:** primeira execução (sem Continuar e sem Carregar; "Novo jogo" primário); save recuperado de backup (toast `ui.save.backup_loaded`); todos corrompidos (modal `ui.save.all_corrupt`, nunca sobrescreve sem confirmar); `content_version` maior que o do jogo (modal `ui.save.too_new`, arquivo intacto).
- **Teclado:** setas, Enter, Esc não faz nada no menu raiz.

### S-02 Seleção de slot (`SaveSlotsView`, `docs/03` 4.5)
- **Objetivo:** escolher, carregar ou apagar um save sem medo de perder progresso.
- **Informação por cartão:** retrato, nome, "Guerreiro · Nível N", área, tempo de jogo, data do último save, "Em expedição · faltam X h" ou "Expedição pronta para coletar", aviso de backup.
- **Ações:** Carregar, Apagar (modal; exige **segurar 1 s**), Novo jogo em cartão vazio (vai a S-03).
- **Número de slots:** 3 cartões na UI, 1 arquivo por slot (`slot_N`, já suportado por `WriteSaveFile`). Isso difere de `docs/02` 2.2 ("fora: mais de um slot") e de `docs/15` ("1 slot"): ver **Q3-1**. Com 1 slot, a tela mostra um cartão só.
- **Selo de nuvem** (Steam Cloud) não aparece nesta etapa.

### S-03 Criar personagem
- **Objetivo:** nomear o herói e começar. Não há escolha de classe no protótipo (só Guerreiro).
- **Informação:** retrato 3D do Guerreiro com o kit inicial (boneco modular), campo de nome, ícone do recurso Ímpeto.
- **Ações:** Confirmar (cria o save e vai ao Refúgio), Voltar. Nome padrão `Guerreiro` (chave nova `ui.create.default_name`); nome vazio recebe o padrão; limite de 16 caracteres; aceita acentos.
- **Regra:** o nome é só rótulo; não entra em nenhuma regra.

### S-04 Refúgio do Marco (cena de hub + HUD)
- **Objetivo:** ser o ponto de partida e de retorno do ciclo, com tudo a poucos passos.
- **Cena:** área pequena, sem inimigos, dimensionada na escala de `docs/03` (corredores de 6 m; **[HIPÓTESE H3-03]** cerca de 40 × 30 m). Pontos de interação a no máximo 12 m uns dos outros:
  1. **Portal da Cripta** (entrada).
  2. **Ilsa** (expedição, abre S-08).
  3. **Tico** (relatório e entrega, abre S-09; se não há expedição: `dlg.tico.nothing`; se em curso: `dlg.tico.waiting`).
  4. **Baú compartilhado** (abre S-05 na aba Baú).
  5. **Vendedor** (abre S-14) e 6. **Encantador** (abre S-15), funções com nome provisório (seção 11). A venda sai da mesa de troca e passa ao Vendedor.
  Bram e Irmã Odete: ausentes ou só cenário sem interação (`docs/05`; sem função no protótipo).
- **HUD no Refúgio:** retrato, barras, Ouro, Cargas do Marco `n/12`; sem barra de chefe, sem Fervor; ataque e habilidades desligados (a barra fica visível e sem recarga, como em `docs/03` 4.1). Poções enchem ao entrar.
- **Ações:** andar, interagir, `I` inventário, `Esc` pausa. **Interagir** = ação nova `Interact` (padrão `F`, remapeável, RF-65); conflito futuro com Habilidade 5 em `F` fica para a Etapa 4 (mapas de ação separados por cena) [ver 9.3].
- **Estados do Ilsa/Tico:** a fala segue `Loc/dialogue.csv` (`dlg.ilsa.*`, `dlg.tico.*`). Antes do Guardião vencido: `dlg.ilsa.not_dominated`; depois, uma vez: `dlg.ilsa.crypt_done`; sem cargas: `dlg.ilsa.no_charges`; expedição ativa: `dlg.ilsa.busy`.

### S-05 Inventário e equipamento (paper doll) (`InventoryView`, tecla `I`)
- **Objetivo:** ver o que o herói veste, trocar peças e decidir o que guardar, vender ou descartar, com o efeito no boneco e nos números imediatamente visível.
- **Layout:** painel à direita (`docs/03` 4.2); o herói 3D fica visível à esquerda e **gira com arrastar do mouse** (render do `ModularCharacter` ao vivo, idle em loop; sem giro automático com "Reduzir movimento").
- **Posições de equipamento (6 ativas):** Arma, Elmo, Peitoral, Luvas, **Calça** (nova, decisão do dono 16/10), Botas. Amuleto, Anel e Mão secundária **não aparecem** (sem conteúdo; `docs/03` mostrava cadeados da demo, aqui saem). Atualiza RF-30 e `docs/03` 4.2 (ver seção 5, "Divergências").
- **Mochila:** 40 posições (8 × 5), com rolagem. **Baú compartilhado:** 100 posições, só utilizável no Refúgio. Contador `n/40`; cheio = `semantic.warning`.
- **Painel de atributos:** vida, armadura, dano da arma por segundo, chance de crítico, velocidade de ataque, velocidade de movimento, resistência a fogo, regeneração. **Todos os números vêm do core** (não calcular no C#; seção 9).
- **Recursos:** Ouro, Lascas, Cargas do Marco.
- **Ações:**
  - Clique esquerdo pega e solta; clique direito equipa/desequipa (se a posição estiver ocupada, troca); duplo clique = clique direito.
  - `Shift` mostra a comparação lado a lado (S-06).
  - `Alt+Clique` marca como "lixo" (ícone 32). Botão "Vender marcados" no Refúgio.
  - Menu de contexto no item (clique direito longo ou `Del`): **Vender** (Refúgio), **Descartar** (qualquer lugar), **Mover para o Baú/Mochila** (`Ctrl+Clique`).
  - Peça equipada pode ser desequipada para a Mochila; posição vazia mostra o corpo base nu e um ícone-fantasma.
- **Estados:** normal; item preso ao cursor; Mochila cheia (toast `Mochila cheia` e o item fica no chão se veio do chão); Baú cheio; item com requisito de nível não cumprido (hachura `danger` e toast "Requer nível N"); Único protegido (vender/descartar pedem segurar 1 s).
- **Tempo real:** o inventário não pausa o jogo na Cripta [HIPÓTESE H3-04: abrir o inventário na Cripta **pausa** o combate; mais simples de testar e mais seguro para o jogador]. No Refúgio não há o que pausar.
- **Equipar na Cripta:** permitido (P4). O ModularCharacter nunca troca peça no meio de um hitstop (`docs/04` 17.4).

### S-06 Tooltip de item com afixos e raridade (`ShatterItemTooltip`, `docs/03` 4.2)
- **Objetivo:** responder em 2 segundos "esse item é melhor que o meu?".
- **Conteúdo, nesta ordem:**
  1. Nome na cor da raridade (até 2 linhas) montado por `item.pattern.*` com gênero da base (RF-28): "Espada de Ferro Afiada de Presteza".
  2. Linha de raridade e posição: "Raro · Espada" (a raridade em **texto**, nunca só cor).
  3. Propriedades da base: dano físico, ataques por segundo (arma), ou o implícito da base (armadura, vida, velocidade).
  4. Afixos, um por linha, cor `item_text.affix`, com o valor sorteado; ordem: prefixos, depois sufixos.
  5. Só Único: efeito (`item_text.unique_effect`) e contrapartida com `▼` (`item_text.unique_drawback`).
  6. "Requer nível N" (se houver) e `itemLevel`.
  7. Rodapé de teclas: `[RMB] Equipar  [Shift] Comparar  [Alt] Marcar`, glifos atuais.
  8. Preço de venda ("Vale N Ouro") quando o Refúgio está disponível.
- **Comparação (`Shift`):** segundo tooltip à esquerda, cabeçalho "Equipado". No novo item, cada atributo do painel mostra `▲ +6` (verde) ou `▼ −4` (vermelho). Sem item equipado na posição: compara com "vazio". **Quem calcula** a diferença é o core (monta o `StatBlock` do herói com e sem o item); a UI só exibe.
- **Comparação automática:** ao passar o mouse sobre um item da Mochila, a seta de melhora/piora aparece no canto do slot **sem** segurar `Shift` (`▲` verde se a soma ponderada dos atributos melhora [HIPÓTESE H3-05: critério = dano da arma por segundo para armas; armadura + vida para peças; empate neutro]).
- **Moldura por raridade:** Comum sem moldura especial; Mágico cantos simples; Raro cantos duplos; Único cantos espinhosos e filete dourado (`docs/03` 2.3).
- **Texto mais longo para teste:** nome "Luvas de Couro Robustas de Presteza" (35 caracteres, 2 linhas); afixo "+8% de dano aumentado de ataque" (cabe em 1); efeito de Único com 3 linhas. Altura máxima 800 px.

### S-07 Confirmações de venda e descarte
- **Vender:** disponível só no Refúgio. Venda de 1 item Comum ou Mágico: sem confirmação (desfazer por 5 s via toast "Vendido · Desfazer"). Raro: confirmação simples. Único: segurar 1 s.
- **Descartar:** destrói o item. Comum: sem confirmação (desfazer por 5 s). Mágico e Raro: modal "Descartar X? Não dá para recuperar." com Confirmar/Cancelar. Único: segurar 1 s.
- **Em lote:** "Vender marcados" mostra o total de Ouro e a contagem por raridade; Raros e Únicos marcados são listados separados e exigem confirmar.
- **Preço:** seção 4.4.

### S-08 Expedição (`ExpeditionView`, falar com a Ilsa, `docs/03` 4.3)
- **Objetivo:** montar um plano, ver o que se espera dele e comprometer cargas. É o quebra-cabeça do pilar P3.
- **Informação:** Cargas do Marco `n/12` e Vigor; coluna de áreas (só **Cripta Partida · Níveis 2–4**; a Cripta tem monstros nível 3 em `maps.csv`, conferir o texto do nível); objetivo (XP, Ouro, Materiais); duração 1 a 12 h com Vigor por hora (100% até 4 h, 70% 5 a 8 h, 40% 9 a 12 h); regras de IA (até 6, em ordem); **previsão em faixa** (XP, Ouro, Raros "até 4", risco de recuo com o motivo); **selo "Estimativa"** (`ui.exp.estimate.badge`, com `ui.exp.estimate.desc` no hover) enquanto os IdleProfiles forem `manual_estimate`; aviso de compatibilidade.
- **Ações:** escolher objetivo; deslizar a duração (limitada pelas cargas: o slider para no máximo possível, com a mensagem de cargas); adicionar, ordenar (▲▼, `Ctrl+↑/↓`) e remover regras (desfazer por 5 s); "Iniciar expedição" (modal "A build e as regras ficam congeladas até o fim. Iniciar?"); Cancelar.
- **Bloqueios com mensagem localizada:** área não dominada (RF-31); sem cargas; habilidade sem IdleProfile (RF-43); outra expedição em curso (RF-37); regra 7 ou duração fora de 1 a 12 h impossível de salvar (RF-39).
- **Nunca** mostrar percentual negativo nem comparação com o manual (RF-45). A previsão é absoluta.
- **Regras de IA do protótipo:** condições e ações que o core já aceita (`AiCondition`, `AiAction`: vida abaixo de X%, usar poção de Vida ou de Resguardo, usar habilidade, etc.). A UI lista só o que o core expõe; a lista exata sai de `expedition.h` (pedido em 9.2).
- **Depois de iniciar:** "Feche o jogo quando quiser; o Tico traz o relatório." O herói fica em rota (Q3-2).

### S-09 Relatório da expedição (`ExpeditionReportView`, `docs/03` 4.4)
- **Objetivo:** mostrar o que aconteceu e levar o jogador a uma decisão.
- **Estado "calculando":** o Tico correndo em loop e `ui.loading.generic`/"O Tico está voltando..."; a animação continua durante a simulação (RF-60, RNF-03); sem botões.
- **Informação (6 campos, RF-44):** tempo efetivo ("7 h 40 min de 8 h"), encontros vencidos, poções gastas, motivo da parada (`report.stop.*`), XP e Ouro, loot. Mais: **selo "Estimativa"** ao lado do título enquanto os IdleProfiles não forem calibrados, Vigor por hora, recibos por hora, **dica** (`report.tip.*`) e **convite** (`report.invite` + botão `report.play_route`).
- **Loot na tela:** Raros primeiro, depois Mágicos, em grade; Comuns agregados numa linha ("98 itens Comuns"); materiais e Ouro em linha própria (seção 4.9).
- **Ações:** "Coletar tudo"; "Coletar e nova expedição" (abre S-08 com a última configuração); "Ajustar regra" (abre S-08 na regra da dica); "Jogar esta rota agora" (leva à Cripta; exige coletar antes). `Esc` não fecha antes de coletar (toast).
- **Estados:** relógio voltou (aviso neutro, `report.stop.clock_back`); conteúdo mudou (`report.stop.content_mismatch`); Baú sem espaço (modal, seção 4.9); coletado (botões viram "Fechar" e não coleta de novo, RF-55); sem expedição (`report.empty`).
- **Tom:** nenhum vermelho para quantidades pequenas; vermelho só para recuo por falta de recurso.

### S-10 Pausa (`PauseMenuView`, `Esc`)
- **Objetivo:** pausar, ajustar e sair com segurança.
- **Ações:** Continuar; Opções (S-11); Abrir pasta de logs; Menu principal; Sair do jogo. Menu principal e Sair mostram "O jogo é salvo automaticamente. Sair agora?" e **salvam** antes de sair.
- **Regras:** o jogo pausa (single-player). No Refúgio e na Cripta. Durante a luta do Guardião a pausa também congela o chefe.

### S-11 Opções (`OptionsView`, `docs/03` 4.6)
- **Objetivo:** o mínimo exigido por RF-58, RF-62, RF-65.
- **Abas do protótipo:** **Jogo** (idioma pt_BR/en; mostrar valores nos orbes; rótulos de itens no chão: Mágico+/Raro+/Todos), **Controles** (remapeamento), **Acessibilidade** (tremor de tela: Normal/Reduzido/Desligado; reduzir flashes). Vídeo e Áudio ficam para a Etapa 5, exceto "Modo de tela" e "Resolução" se o build de playtest precisar [HIPÓTESE H3-06].
- **Idioma:** trocar atualiza todas as telas sem reiniciar e persiste em arquivo de configurações separado (RF-62).
- **Remapeamento:** tabela Ação / Principal / Alternativa; clique entra em "Pressione uma tecla…"; conflito pergunta "Trocar as duas?"; `Esc` não é remapeável; ação sem tecla avisa no rodapé; **esquiva para Shift persiste e o Espaço deixa de esquivar** (RF-65). Inclui a ação nova Interagir.
- **Botões:** Restaurar padrão, Cancelar, Aplicar.

### S-12 "Você caiu" (`HudView`, estado de morte)
- **Objetivo:** dizer sem drama que nada se perdeu e devolver o controle rápido.
- **Informação:** título `ui.death.title`; linha curta "Nada foi perdido" (nova: `ui.death.nothing_lost`); botão `ui.death.checkpoint`.
- **Comportamento comum:** HUD some em 200 ms; XP e itens iguais ao de antes; inimigos reaparecem (regra Souls de `docs/13` R2.4); poções cheias.
- **Na arena do Guardião:** a luta reinicia sozinha em menos de 2 s (RF-18) com `ui.death.boss_restart`; **sem** botão; a porta reabre e o chefe volta à fase 1.
- **Fora da arena:** o botão "Voltar ao checkpoint" (Enter) ou, sem input em 5 s, volta sozinho [HIPÓTESE H3-07].
- Em ambos, auto-save logo depois.

### S-13 Vitória sobre o Guardião
- **Objetivo:** marcar o ponto alto do ciclo e deixar claro o que o jogador ganhou e o que fazer agora.
- **Sequência:** (1) o Guardião cai; hitstop e câmera lenta curtos; (2) banner `ui.boss.defeated` (nova) por 3 s; (3) o loot cai com espalhamento; **o Único cai com coluna laranja de 500 cm, pulso de 800 ms e som próprio** (RF-29); (4) toasts: "Marco de Retorno instalado" (nova) e "+5 Cargas do Marco" (`ui.hud.charges`); (5) `portal.crypt.exit` aparece perto do Marco.
- **Regras:** a luta termina no mesmo quadro em que a vida chega a 0 (sem cinemática bloqueante); o jogador pode andar em seguida. Se a Mochila estiver cheia, o **Único vai direto ao Baú** (nunca fica no chão sem dono) com toast.
- **Primeira vez:** Único garantido (docs/13 item 9); depois 20% por vitória, garantido na 5ª sem Único.

### HUD (já existe)
`HudView.uxml/.cs` cobre vida, Ímpeto, 6 espaços de habilidade (4 ativos), esquiva, 2 poções, números de dano e a morte. Falta nele: Ouro e Cargas (`ui.hud.charges`), faixa de área, Fervor (`+200% XP`), rótulos de itens no chão, toasts de pickup e a barra de XP. Ver seção 5.

---

## 4. Regras de loot e de inventário do protótipo

### 4.1 Recipientes e tamanhos

| Recipiente | Tamanho | Onde se usa | Origem do número |
|---|---|---|---|
| Equipamento | 6 posições (arma, elmo, peitoral, luvas, calça, botas) | sempre | `item.h` (`Legs` existe); RF-30 diz 5 e sai de data |
| Mochila | 40 posições | sempre | `docs/03` 4.2; **[HIPÓTESE H3-08]** suficiente para uma corrida |
| Baú compartilhado | 100 posições | só no Refúgio | `SaveData::stash` existe; tamanho **[HIPÓTESE H3-09]** |
| Pilhas | sem limite (Ouro, Lascas) | HUD e inventário | `StackEntry` |

- Ouro e Lascas **não** ocupam espaço. Pilhas somam direto.
- A Mochila hoje não existe no save: só há `stash`. Proposta no 9.2 (`backpack` por personagem).
- Itens não empilham.

### 4.2 Pegar itens
- Ouro e Lascas: ímã a 3 m, entram sozinhos.
- Itens: pega ao andar até 1,2 m **[HIPÓTESE H3-10]**. Mochila cheia: o item fica no chão e aparece o toast "Mochila cheia".
- Rótulo no chão só para Mágico ou melhor; `Alt` mostra todos; configurável nas opções (`docs/03` 4.1).
- O item no chão persiste até o jogador sair da Cripta (portal). Ao sair com Mágico, Raro ou Único no chão: confirmação "Há itens no chão. Sair mesmo assim?". Morrer e voltar ao checkpoint **não** apaga o chão.
- Baús da Cripta usam a tabela do JSON de `docs/14` (`loot.crypt.area` nos 01 a 03; `loot.crypt.elite` nos 04 e 05).

### 4.3 Comparar item
Ver S-06: `Shift` abre o tooltip duplo; setas `▲/▼` no slot ao passar o mouse; diferença calculada pelo core. Para armas compara-se o **dano por segundo** (dano da arma × velocidade de ataque, com o implícito e os afixos); para peças, os atributos que mudam. Um item sem afixo e com a mesma base da peça equipada é neutro (o kit inicial usa as mesmas bases que caem).

### 4.4 Vender ou descartar

| Ação | Onde | Efeito | Confirmação |
|---|---|---|---|
| Vender | Refúgio (mesa de troca) | Item some, entra Ouro | Comum/Mágico: nenhuma (desfazer 5 s). Raro: simples. Único: segurar 1 s |
| Descartar | Em qualquer lugar | Item destruído | Comum: nenhuma (desfazer 5 s). Mágico/Raro: modal. Único: segurar 1 s |
| Vender Comuns ao coletar | Relatório da expedição | Comuns da coleta viram Ouro | Opção marcada por padrão **[HIPÓTESE H3-11]** |

Preço de venda por raridade (valores em `rules.csv`, proposta no 9.1), **[HIPÓTESE H3-12]**:

| Raridade | Preço (Ouro) | Por quê |
|---|---|---|
| Comum | 4 | Um Comum custa menos do que o ouro médio de um drop (5 a 15) |
| Mágico | 12 | ~3× o Comum |
| Raro | 35 | Raro é ~2% a 4% dos itens: precisa pesar |
| Único | 100 | Só para tirar duplicatas; protegido |

**Atualização de 17/10/2026 (decisão do dono):** o Ouro passa a ter dois usos no protótipo, um Vendedor no Refúgio (compra itens, vende frascos de recarga) e Melhorias de equipamento com um Encantador. A mesa de troca abaixo vira o Vendedor. Ver a seção 11; ela substitui a versão anterior deste parágrafo ("o Ouro não tem uso") e fecha **Q3-3**.

### 4.5 O que cai de cada inimigo (tabelas existentes)

Os drops usam `lootTableId` de `enemies.csv`. Cada sorteio: chance de cair (`dropChance`) × entrada ponderada × raridade por peso. No jogo manual o Fervor multiplica o peso do Raro por 2 e Ouro/Lascas por 1,25 (RF-32). Valores "por inimigo" são esperanças calculadas dos CSV atuais, **[HIPÓTESE H3-13]** de que o ritmo é bom.

| Quem | Tabela | Sorteios | Chance de cair | Ouro / Lascas / Item (pesos) | Itens esperados por morte | Raridade do item (com Fervor) |
|---|---|---|---|---|---|---|
| Sentinela Oca, Cão-de-Cinza, Arauto de Pedra, Arqueiro Fantasma | `loot.crypt.common` | 1 | 35% | 55 / 25 / 20 (espada, elmo, peitoral, luvas, botas, 4 cada) | 0,07 | Comum 78%, Mágico 18%, Raro 4% |
| Elites (Sentinela Escudada, Cão Veloz e elites sorteadas) | `loot.crypt.elite` | 2 | 60% | 40 / 25 / 28 (as 5 bases mais o Martelo de Pedra: 5, 3, 5, 5, 5, 5) | 0,36 | Comum 45%, Mágico 36%, Raro 18% |
| Guardião | `loot.crypt.guardian` | 2 | 100% | 40 / 25 / 24 (6 bases, 4 cada) + Único à parte | 0,54 | Comum 0%, Mágico 43%, Raro 57% |
| Cada encontro (extra) | `loot.crypt.area` | 1 por encontro | 10% | 70 / 30 / 0 | 0 | Só Ouro e Lascas |
| Baús 01 a 03 | `loot.crypt.area` | 1 | 10% (como tabela) | Só Ouro e Lascas | 0 | — |
| Baús 04 e 05 | `loot.crypt.elite` | 2 | 60% | como elite | 0,36 | como elite |

Quantidades: Ouro 5 a 15 (comuns), 15 a 35 (elites), 30 a 60 (Guardião), 3 a 8 (área); Lascas 1 a 3, 2 a 5, 4 a 8 e 1 a 2.

**Único:** vem de `fixedChance` na tabela do Guardião (1ª vitória garantida, depois 20%, garantido na 5ª sem Único) e **só no jogo manual** (`manualOnly = true`). Nenhum Único em outra tabela (RF-27).

**Esperança por corrida completa** [HIPÓTESE H3-13]: ~3 a 4 itens, ~0,6 Mágico, ~0,5 Raro e o Único na 1ª vez. O esperado é que 3 corridas deem pelo menos um Mágico ou Raro que valha a troca.

**Pontos de dado que o playtest vai cobrar (e que este documento registra):**
1. As tabelas **não largam calça** (`item_base.worn_trousers`): a 6ª posição só tem a peça inicial. Pedir ao Data Engineer a entrada (seção 9.1).
2. `loot.crypt.common` não larga o Martelo de Pedra (`item_base.stone_maul`); só elites e Guardião. Intencional? O Único é um maul: o jogador precisa ver a base antes de desejar o Único.
3. Os baús 01 a 03 dão só Ouro e Lascas: a recompensa de desvio de risco (`docs/14` 5.2) é fraca. Proposta: entradas de item na `loot.crypt.area` com peso baixo.
4. O Arauto de Pedra (28 de XP, a luta mais cara do encontro) larga a mesma tabela dos comuns. Proposta [HIPÓTESE]: tabela própria `loot.crypt.heavy` com 1 sorteio a 50% de chance.
5. Hoje existem só 6 bases e todas de `itemLevel` 1 ou 2, e as armaduras são todas `vset.starter`: as Comuns que caem **repetem** o kit inicial. A troca por base melhor só existe com Mágico e Raro (afixos) ou pelo maul. Ver 4.7 e Q3-4.

### 4.6 Único: Martelo do Trono Vazio
- Base `item_base.stone_maul` (16 de dano físico, 1,4 s por ataque); `damage:increased:0.25:melee` e `move_speed:increased:-0.1`; efeito `effect.empty_throne_resolve` (+20% de dano corpo a corpo por 4 s ao derrotar inimigo). Texto do sabor sem lore novo (já em `Loc/content.csv`).
- Cai com coluna laranja de 500 cm, 30 cm de raio, pulso de 800 ms e som próprio. Cores: laranja `#FF8A2E` exclusivo do Único.
- Cópias repetidas (20% e garantia) são vendáveis por 100 Ouro, com confirmação. **[HIPÓTESE H3-14]** Como só existe 1 Único e o Ouro não tem uso, a caça depois da 1ª vitória perde incentivo. Isso é um achado de design: confirmar no playtest se o dono quer o Fragmento de Eco/Codex já na Etapa 3 ou aceita esse buraco.
- **Farm de cargas (H3-01):** como `reachedEnd` conta ao cruzar o gatilho da arena, e morrer reinicia a luta, a corrida dá +1 carga por entrada na arena. Custo ~5 min por carga (1 h de expedição). Aceitável como "gasto de tempo para ganhar tempo" **[HIPÓTESE]**; se virar farm, trocar `reachedEnd` por "percorrer a rota até o fim com X% de encontros vencidos" (pedido ao Backend/Tech Lead).

### 4.7 Como a raridade aparece (docs/03 §2.3 e §3.11)

| Superfície | Comum | Mágico | Raro | Único |
|---|---|---|---|---|
| **Cor** | `#D9D2C8` | `#6FA8FF` | `#FFD24A` | `#FF8A2E` |
| **Feixe no chão** | nenhum | brilho no item, raio 25 cm | coluna 20 cm × 250 cm | coluna 30 cm × 500 cm, pulso 800 ms |
| **Som no drop** | nenhum | curto agudo | médio | próprio, grave e longo |
| **Rótulo no chão** | só com `Alt` | sim | sim | sim, maior |
| **Moldura do slot** | lisa | cantos simples | cantos duplos | cantos espinhosos + filete dourado |
| **Tooltip** | texto "Comum · ..." | texto "Mágico · ..." | texto "Raro · ..." | texto "Único · ..." |
| **Boneco (peças modulares)** | cores pintadas (`_TintStrength` 0) | tinta azul `_TintStrength` 0,70; rim `#A9CBFF`, intensidade 0,65 | tinta dourada 0,85; rim `#FFE493`, intensidade 0,80; acento emissivo 0,35 nas runas/ouro (máscara R) | malha e textura **próprias** (`vset.unq_<id>`), um traço emissivo `#FF8A2E` ≤ 4% da peça com pulso de 2400 ms; sem tinta |
| **Daltonismo** | — | forma da moldura + texto | forma + emissão | forma + som |

Regras do boneco (fonte: `docs/03` 3.11 e `docs/04` 17.4):
- Tinta só em **tecido**, no máximo 40% da área visível da peça; metal, couro, pele e o "bit da classe" (a pluma vermelha do Guerreiro) **nunca** recebem tinta.
- A emissão somada de todas as peças vestidas fica em ≤ 6% da silhueta.
- Misturar peças Normal, Mágica e Rara no mesmo herói tem que parecer pano tingido em cores diferentes sobre o mesmo metal e couro.
- A raridade vem de `ItemInstance.rarity`, o conjunto visual de `visualSetId` (Único prevalece sobre a base; sem conjunto cai em `vset.starter`; peça ausente no catálogo usa a `starter` do slot e registra aviso).
- Armas: o modelo da arma (espada ou maul) troca por `baseId`; o tratamento de raridade na arma **não está definido** em `docs/03` 3.11 (só peças modulares). Proposta [HIPÓTESE H3-15]: mesmo `_RimTint` e `_AccentEmissive` na malha da arma, sem tinta de cor. O Art Director decide.
- Exigência da Etapa 3: o dono deve **ver** a troca. Com um só conjunto visual (`vset.starter`) só mudam a tinta, a arma e a nudez do slot vazio. Recomendação: **um segundo conjunto visual** (5 peças do Guerreiro) ligado a bases novas de nível 2 (Q3-4). Toda peça nova vai à aprovação do dono antes de entrar (CLAUDE.md).

### 4.8 Nome do item
Montado pelo `item.pattern.*` com o gênero da base (`m`/`f`) e a forma flexionada do prefixo (`.name`, `.name_f`, `.name_mp`, `.name_fp`); nunca concatenar frases no C#. Exemplos que a Etapa 3 deve renderizar certo: "Espada de Ferro Afiada de Presteza" (f), "Luvas de Couro Robustas" (f, plural), "Martelo de Pedra Afiado" (m). Revisão humana de amostra de 20 nomes (RF-28).

### 4.9 Loot da expedição
- O loot sai do mesmo `RollLootTable` em modo `Idle`: sem `manualOnly`; Raros com metade da chance e no máximo 4 por expedição; sem Único, livro de especialização, Sigilo raro nem entrada de mapa (RF-34). As mesmas tabelas da seção 4.5; os encontros de expedição vêm de `maps.csv` (sem o chefe).
- **Volume:** uma expedição de 12 h tem centenas de encontros; com 0,07 item por morte comum, o volume esperado é de dezenas a poucas centenas de itens, quase todos Comuns **[HIPÓTESE H3-16]**. Por isso: Comuns aparecem **agregados** no relatório e são vendidos por padrão na coleta (opção marcada; H3-11). Mágicos e Raros aparecem um a um.
- **Espaço:** itens vão para a Mochila; o excedente vai para o Baú com aviso "N itens foram para o Baú compartilhado". Se nem o Baú comporta: a coleta **não** acontece até o jogador liberar espaço ou vender; modal com os botões "Vender Comuns" e "Abrir o Baú". **Nunca** destruir Mágico, Raro ou Único para caber. A coleta continua atômica: status `Collected` e itens no mesmo salvamento (RF-55).

---

## 5. O que existe e o que falta, por tela

Estado conferido em 17/10/2026 no repositório. "Core" = ShatterCore (C++); "C#" = `Assets/Scripts`; "Dados" = `Content/Data`.

| Tela / sistema | O que existe | O que falta |
|---|---|---|
| **S-00 Carregando** | Chave `ui.loading.generic`; `RulesService`/`GameRoot` carregam conteúdo; DLL real ligada (`NativeRulesCore`). | Tela e UXML; erro de carga legível; bind de `shatter_save_*`, `shatter_expedition_*` e `shatter_loot_roll` no C# (`NativeRulesCore.cs` lista "não há camada de save/expedição no C# ainda"). |
| **S-01 Menu inicial** | Chaves `ui.menu.new_game`, `continue`, `options`, `quit`, `version`; spec em `docs/03` 4.5. | UXML, `MainMenuView`, cena de menu (fundo do Refúgio à noite), leitura do sumário do save (`shatter_save_summary_get`), versão visível, logo, "Abrir pasta de logs". Chaves: Carregar, Créditos (fora), "Expedição pronta". |
| **S-02 Slots** | Core: `WriteSaveFile` (`.tmp`, 3 backups, SHA-256), `ReadSaveFile` com `LoadReport.usedBackup`, migração 1→2, `SaveContentVersionSupported`; chaves `ui.save.backup_loaded`, `too_new`, `all_corrupt`. | `SaveSlotsView`, `SaveService` no C# (caminho `Saved/` por slot, thread de E/S), cartões, apagar com 1 s de segurar, decisão do número de slots (Q3-1). |
| **S-03 Criar personagem** | Core cria `CharacterState` (nome, classe, nível, `equipment`); `class.warrior`, dados do Guerreiro. | Tela; função "novo save" (kit inicial: 6 peças Comuns, poções cheias, 0 cargas); validação do nome. Chaves de tela. |
| **S-04 Refúgio** | Só texto: `area.refuge.name`, nomes e falas de Ilsa e Tico, `dlg.*`. Em `maps.csv` não há Refúgio. `PortalZone` tem `targetArea="area.refuge"` e **hoje devolve ao checkpoint** (`TODO area.refuge`). Arte aprovada: folha 14 e a cena de menu do Refúgio descrita em `docs/03`. | **Cena do Refúgio** (graybox e depois cenário), troca de cena e fade, ação `Interact`, NPCs com marcador e diálogo simples, mesa de troca, Baú, entrada/saída do portal, HUD de hub (sem skills). |
| **S-05 Inventário e paper doll** | Core: `ItemInstance`, `SaveData::stash`, `CharacterState::equipment` (11 posições incluindo `Legs`), `BuildStatBlock`, afixos, nomes por padrão; Dados: 7 bases, 8 afixos, `visualSetId`; chaves `ui.inventory.*`, `ui.item.*`; doc 17.4 do `ModularCharacter`. C#: nenhuma classe de inventário nem `ModularCharacter` (busca textual sem resultado). | `InventoryView` + UXML, `ModularCharacter`, `SO_HeroPartCatalog_Warrior`, `SO_HeroPart_*`, `SO_RarityTint`, render do herói na UI com giro, **corpo base e 5 peças `starter` em modelos separados**, contêiner Mochila no save, compra/venda, chaves novas (menu de contexto, Baú, vender, descartar, preços), painel de atributos com valores do core, hover com setas de comparação. |
| **S-06 Tooltip** | Spec completa (`docs/03` 4.2); padrões de nome e rarity em `Loc/content.csv`; afixos com `stat.*.name`. | `ShatterItemTooltip` com montagem de nome e afixos pelo Loc, comparação com diferença vinda do core (API de "equipar hipotético"), preço de venda. |
| **S-07 Vender/descartar** | Nada de vender em docs, dados ou código; `Alt+Clique` "lixo" só no `docs/03`. | Regras de preço em `rules.csv`, comandos de venda/descarte no core ou no serviço de inventário, modais, desfazer 5 s, hold de 1 s. |
| **S-08 Expedição** | Core completo: `CanStartExpedition`, `StartExpedition`, `ExpeditionRequest`, simulador, previsão em faixa (`shatter_expedition_forecast`), cargas, relógio, snapshot; dados: `idleSupported` das 4 habilidades e do Único com `manual_estimate`; chaves `ui.exp.*`, selo `ui.exp.estimate.*`, falas da Ilsa; spec em `docs/03` 4.3 e `ShatterRuleRow`. | `ExpeditionView` + UXML, `ShatterRuleRow`, serviço de expedição no C# (monta o pedido, chama o core, simula fora da thread), acelerador de debug (1 h = 10 s), lista de condições/ações exposta pelo core, mensagens de bloqueio por motivo. |
| **S-09 Relatório** | Core: `shatter_expedition_simulate`/`finalize`, `CollectExpedition` idempotente por `resultHash`; chaves `report.*`; dica; convite; selo. | `ExpeditionReportView`, animação do Tico (modelo e correr em loop), contagem animada, agregação de Comuns, "Vender Comuns ao coletar", fluxo do Baú cheio. |
| **S-10 Pausa** | Ação `Pause` mapeada em `InputActionNames`; spec em `docs/03` 4.6. | `PauseMenuView`, pausa do tempo (inclusive do chefe), salvar ao sair. |
| **S-11 Opções** | Chaves `ui.options.*` (idioma, tremor, teclas); `CombatFeelSettings` (tremor); `LocalizationService`. | `OptionsView`, persistência em arquivo separado, troca de idioma em tempo real, remapeamento (`PerformInteractiveRebinding`) e a ação `Interact`. |
| **S-12 Você caiu** | `HudView` já tem "Você caiu", `ui.death.*`, morte e retorno ao checkpoint; `ArenaController` reinicia o chefe; `CombatantRevivedEvent`. | `ui.death.nothing_lost`; cronômetro de 5 s fora da arena; auto-save depois da morte; conferir os 2 s da luta (critério RF-18). |
| **S-13 Vitória** | `BossEvents`/`ArenaStateEvent` (`Won`); core: `RecordAreaRun`, contador do chefe, `fixedChance`/`guaranteeFirstKill`/`pityKills` em `loot_entries.csv` (já com 0,2 / true / 5). | Banner e chaves (`ui.boss.defeated`, "Marco instalado"), ligação do evento `Won` a `RecordAreaRun` e a `shatter_loot_roll`, `portal.crypt.exit` ativo só depois da vitória, drop físico no chão, feixe e som do Único. |
| **Loot no chão** | Core: `RollLootTable`, `RollAffixes`, `ItemModifiers`; `ChestPickup` e `ChestOpenedEvent` ("o loot de verdade entra com o inventário; por enquanto só o evento"). | Item no chão (prefab, rótulo, feixes por raridade, som), pegar por proximidade, seed de loot por morte (derivada), `ItemInstance` com uid, mochila cheia, ícones de item. |
| **HUD** | `HudView` (vida, recurso, 6 skills, esquiva, poções, números de dano, morte). | Ouro, Cargas, faixa de área, XP, Fervor, toasts de item, rótulos de chão. |
| **Save/relógio** | Tudo no core (checksum, backups, migração, `last_seen`, descanso diário). | Camada C# de save: caminho, autosave de 5 min, hook de saída, aviso de backup. |

### Divergências que este documento registra
1. **RF-30 e `docs/03` 4.2** falam em 5 posições e em 8 slots com cadeado; o dono acrescentou `legs` (6 posições de equipamento) e a Etapa 3 não tem Amuleto, Anel nem Mão secundária.
2. **Número de slots de save:** `docs/02` 2.2 e `docs/15` dizem 1; `docs/03` 4.5 desenha 3. Q3-1.
3. **Nível da Cripta:** `maps.csv` diz `monsterLevel = 3`; `docs/02` RF-33 e `docs/15` usam "nível 6 na Cripta (nível 4)". O teste de teto de nível deve derivar o número do CSV (3 + 2).
4. **Chave `F`:** em `docs/03` 4.6 a tecla `F` é a Habilidade 5; a ação nova `Interact` propõe `F` no Refúgio.

---

## 6. Critérios de aceite da Etapa 3

Todos verificáveis; **[SC]** roda em `ctest`, **[Unity]** exige editor ou build, **[Manual]** é roteiro do dono. Os critérios de `docs/15` Etapa 3 continuam valendo; abaixo ficam os ligados a este documento (fluxo, telas, loot e inventário).

| ID | Critério | RF/RNF | Verificação |
|---|---|---|---|
| A3-01 | Do executável ao Refúgio: Menu → Novo jogo → nome → Refúgio sem erro, em menos de 60 s e com no máximo 3 cliques de confirmação. Com save existente, "Continuar" leva ao Refúgio em até 2 cliques | RF-58 | [Unity] |
| A3-02 | O personagem novo começa nível 1 com 6 peças Comuns `vset.starter` equipadas, poções cheias, 0 Ouro e 0 cargas | RF-51 | [SC] + [Unity] |
| A3-03 | O portal do Refúgio leva à Cripta e `portal.crypt.entry` leva de volta; a troca salva (auto-save) e não perde estado | RF-54 | [Unity] |
| A3-04 | Matar cada tipo de inimigo larga Ouro, Lascas ou item conforme a tabela da seção 4.5: em 100 mil mortes simuladas por tabela, a frequência de cada entrada fica a ±1% relativo do peso | RF-25 | [SC] |
| A3-05 | Mágico tem no máximo 2 afixos, Raro no máximo 4, sem afixo repetido; em 1 milhão de sorteios das tabelas que não são do Guardião: 0 Únicos | RF-26, RF-27 | [SC] |
| A3-06 | Cada raridade tem feixe distinto no chão (Comum nenhum, Mágico brilho, Raro coluna, Único coluna maior com pulso e som próprio); capturas lado a lado anexadas | RF-29 | [Unity] |
| A3-07 | Andar até o item o pega; com a Mochila cheia o item fica no chão e aparece o aviso; o Único com a Mochila cheia vai ao Baú | RF-30 | [Unity] |
| A3-08 | Vencer o Guardião pela primeira vez grava domínio, +5 cargas (respeita teto 12), o contador de vitórias e entrega 1 Único; o `portal.crypt.exit` só existe depois da vitória; derrotar o Guardião sem percorrer a área (cheat de teste) não grava domínio | RF-27, RF-35, RF-50 | [SC] + [Unity] |
| A3-09 | Morrer mantém XP e itens; na arena a luta reinicia em menos de 2 s; fora dela "Você caiu" volta ao checkpoint | RF-18 | [Unity] |
| A3-10 | O inventário mostra 6 posições e a Mochila de 40; equipar e desequipar muda os atributos no mesmo quadro; os números vêm do core (busca textual sem fórmula no C#) | RF-12, RF-30 | [Unity] + revisão |
| A3-11 | O boneco troca de peça ao equipar: com `vset.starter` o dono vê a tinta, a arma e o slot nu; **com o segundo conjunto visual** (se aprovado), a malha troca; toda `visualSetId` do CSV tem peça para o Guerreiro (teste EditMode falha se faltar) | RF-59, `docs/04` 17.4 | [Unity] + EditMode |
| A3-12 | Peça Mágica e Rara têm tinta azul e dourada distinguíveis do Normal a 88 px (captura lado a lado), com luminância das áreas B a ±15% do Normal; nenhum pixel de metal, couro ou pele tingido | RF-29 | [Unity] + revisão do dono |
| A3-13 | Tooltip: nome na cor da raridade, raridade escrita, afixos, requisitos; `Shift` mostra comparação com `▲/▼`; a diferença bate com a do core em 20 amostras | RF-28, RF-30 | [Unity] + [SC] |
| A3-14 | Nomes de itens com concordância correta em uma amostra de 20 nomes pt_BR | RF-28 | Revisão humana |
| A3-15 | Vender no Refúgio entrega o Ouro da tabela (4/12/35/100); Raro pede confirmação; Único pede segurar 1 s; descartar destrói; desfazer em 5 s restaura | RF-30 (inventário) | [Unity] |
| A3-16 | Expedição recusada sem domínio da Cripta, inclusive com a área limpa sem vencer o Guardião; com domínio e 5 cargas, o slider só chega a 5 h | RF-31, RF-35, RF-39 | [SC] + [Unity] |
| A3-17 | A tela de configuração mostra previsão em faixa e o selo "Estimativa" enquanto houver IdleProfile `manual_estimate`; nenhuma string de expedição ou HUD tem percentual negativo | RF-40, RF-45, P-3 | [Unity] + [SC] busca nas strings |
| A3-18 | Com expedição ativa o Refúgio mostra o herói em rota e o portal da Cripta bloqueado; sem expedição ele abre | RF-37 | [Unity] |
| A3-19 | Fechar o jogo com expedição de 4 h iniciada há 10 h e reabrir: simula 4 h, mostra "O Tico está voltando..." com animação rodando, e abre o relatório com os 6 campos, a dica, o convite e o selo "Estimativa" | RF-44, RF-47, RF-60 | [SC] + [Unity] |
| A3-20 | Coletar entrega o loot uma única vez; queda entre cálculo e gravação não duplica; coletar de novo não faz nada; Mochila cheia manda o excedente ao Baú com aviso; Baú cheio bloqueia a coleta sem perder item | RF-55 | [SC] + [Unity] |
| A3-21 | "Vender Comuns ao coletar" (se mantido) converte exatamente os Comuns da coleta em Ouro pela tabela de preço e não toca Mágico, Raro nem Único | RF-55 | [SC] + [Unity] |
| A3-22 | "Jogar esta rota agora" leva à Cripta com Fervor visível (`+200% XP`) e a coleta já feita | RF-32, RF-44, RF-45 | [Unity] |
| A3-23 | Pausa e Opções abrem e fecham por mouse e `Esc`; trocar o idioma atualiza todas as telas sem reiniciar e persiste; remapear a esquiva para Shift persiste e o Espaço deixa de esquivar | RF-58, RF-62, RF-65 | [Unity] |
| A3-24 | Todas as telas em pt_BR sem texto cortado a 1920 × 1080 e a 1280 × 800; `ç ã õ á é ê` corretos | RF-63 | [Unity] captura |
| A3-25 | Fechar, reabrir e continuar mantém personagem, equipamento, Mochila, Baú, Ouro, cargas, domínio e contador do chefe iguais; 1000 ciclos salvar/carregar sem divergência | RF-51, RNF-05 | [SC] + [Unity] |
| A3-26 | O ciclo inteiro roda com a rede desligada | RNF-06 | [Unity] |
| A3-27 | Playtest do dono: completa o ciclo (menu → Cripta → Guardião → Refúgio → expedição → relatório → coleta → vestir o loot) e anota o que não entendeu; roteiro novo em `docs/10_qa.md` | Pilar P3 | [Manual] |

---

## 7. Hipóteses que dependem de playtest

| ID | Hipótese | Como medir |
|---|---|---|
| H3-01 | `reachedEnd` = cruzar o gatilho da arena. Farm de cargas por morte na arena é aceitável (~5 min por carga) | Contar quantas vezes o dono entra na arena sem vencer |
| H3-02 | 5 cargas na primeira conquista dão uma primeira escolha interessante (1 a 5 h) | O dono configura a 1ª expedição e verbaliza o motivo |
| H3-03 | Refúgio de ~40 × 30 m, pontos a ≤ 12 m | Tempo para chegar a Ilsa, Tico, mesa e portal |
| H3-04 | Abrir o inventário na Cripta pausa o combate | Pergunta ao dono depois da 1ª luta com troca |
| H3-05 | Seta de melhora/piora automática usa dano por segundo (armas) e armadura + vida (peças) | O dono equipa algo pior por engano? |
| H3-06 | Vídeo e Áudio ficam fora do protótipo | O sócio reclama de resolução ou volume? |
| H3-07 | Auto-retorno em 5 s após "Você caiu" fora da arena | Taxa de clique antes do tempo |
| H3-08 | Mochila de 40 posições basta para uma corrida | Mochila cheia em quantas corridas |
| H3-09 | Baú de 100 posições aguenta 3 expedições sem bloquear | Espaço livre depois de 3 coletas |
| H3-10 | Pegar item andando a 1,2 m, sem apertar tecla | Itens pegos sem querer |
| H3-11 | "Vender Comuns ao coletar" marcado por padrão | O dono desmarca? |
| H3-12 | Preços 4/12/35/100 Ouro | O Ouro acumula sem uso; ajustar quando houver sumidouro |
| H3-13 | ~3 a 4 itens, ~0,6 Mágico e ~0,5 Raro por corrida completa | Contagem real em 10 corridas |
| H3-14 | Depois da 1ª vitória o Único perde atrativo (só 1 Único, sem Fragmento) | O dono repete a luta? |
| H3-15 | Raridade na arma usa rim e acento emissivo, sem tinta | Revisão do Art Director |
| H3-16 | Uma expedição de 12 h larga dezenas a centenas de itens, quase todos Comuns | Contagem real num relatório de 12 h com o acelerador |

---

## 8. Perguntas abertas para o dono

Formato de `CLAUDE.md`: pergunta inteira, contexto completo, opções com efeito. Uma escolha por pergunta.

### Q3-1 — O protótipo tem 1 slot de save ou 3?
**Pergunta:** O protótipo deve oferecer um único slot de save (como pedem `docs/02` e `docs/15`) ou 3 slots (como desenha `docs/03` 4.5 e como o core já suporta)?
**Contexto:** `docs/02` seção 2.2 põe "mais de um slot de save" fora do escopo; a Etapa 3 em `docs/15` diz "1 slot". O desenho de tela em `docs/03` 4.5 tem 3 cartões e o core grava `slot_N.json` com backups por slot, então o custo de ter 3 é só de interface. A tela de seleção que você pediu só faz sentido com mais de um slot.
**Opções:**
- **A (recomendada). 3 slots.** Efeito: "Novo jogo" nunca apaga um save existente; o sócio testa em paralelo; custo: 3 cartões e 3 testes de save a mais.
- **B. 1 slot.** Efeito: menos telas e menos testes; "Novo jogo" com save existente pede confirmar apagar o único save; a tela de slots vira um modal de confirmação.

### Q3-2 — Durante a expedição, o herói pode jogar na mão?
**Pergunta:** Com a expedição em andamento, o único personagem do protótipo fica bloqueado de entrar na Cripta ("em rota"), ou pode jogar normalmente enquanto a expedição corre?
**Contexto:** A regra 7 do plano diz que só um personagem por vez pode estar em expedição; o protótipo tem um só. O plano pede "fechar o jogo" enquanto se espera. A fala da Ilsa já escrita (`dlg.ilsa.busy`: "Seu herói ainda está na rota. Fale com o Tico depois.") sugere bloqueio. Sem bloqueio, o jogador ganharia XP manual e XP de expedição ao mesmo tempo, o que enfraquece o limite do idle.
**Opções:**
- **A (recomendada). Bloqueado até a coleta.** Efeito: expedição e jogo manual não somam; espera real exige fechar o jogo ou usar o acelerador de debug no playtest; o Refúgio continua navegável (inventário, mesa de troca).
- **B. Livre para jogar.** Efeito: nenhum tempo morto; precisa de regra nova que impeça somar XP (por exemplo, o XP manual não conta enquanto houver expedição) e quebra a premissa de "congelar".
- **C. Bloqueado, com "Chamar de volta".** Efeito: o jogador encerra a expedição quando quiser e recebe só o simulado até agora; as cargas gastas não voltam; exige confirmar no Backend se o core aceita coleta parcial (RF-47 já define `min(agora − início, duração)`).

### Q3-3 — Para que serve o Ouro na Etapa 3 e quem compra os itens? (RESOLVIDA em 17/10/2026: Vendedor e Melhorias, ver seção 11; texto original abaixo mantido como histórico)
**Pergunta:** Como o Ouro entra no ciclo, já que Bram (crafting) e Irmã Odete (livros) estão fora do protótipo, e quem fica com a função de comprar os itens que o jogador vende?
**Contexto:** Hoje o Ouro só entra (drops, venda) e não sai: poções são grátis, respec é grátis até o nível 10, não há loja. Para vender é preciso alguém ou algo que compre; `docs/05` diz que Bram e Odete aparecem "sem função". Não quero criar personagem ou lore, então a decisão é sua.
**Opções:**
- **A (recomendada). Mesa de troca no Refúgio, sem NPC, e Ouro como contador.** Efeito: nenhuma história nova; vender serve só para liberar espaço; o Ouro passa a ter uso na Etapa 4.
- **B. A Ilsa compra.** Efeito: reaproveita uma personagem existente, mas dá a ela um papel que o plano não deu.
- **C. Sem venda; só descartar.** Efeito: corta a ação "vender"; o Ouro vira só um número do HUD; menos telas, mas sem a recompensa de limpar a Mochila.
- **D. Incluir um sumidouro simples já na Etapa 3** (por exemplo, comprar cargas de poção). Efeito: o Ouro tem decisão real, mas sai do escopo e pede design e testes novos.

### Q3-4 — Fazer um segundo conjunto visual de armadura para o Guerreiro?
**Pergunta:** Para o dono "ver o boneco mudar" ao equipar, vale encomendar já um segundo conjunto de armadura (5 peças do Guerreiro, `vset.iron_guard`, com bases de nível 2 que caem na Cripta)?
**Contexto:** Hoje as 5 peças do dados usam o mesmo `vset.starter`; as Comuns que caem repetem o kit inicial. Sem um segundo conjunto, a única mudança visível ao equipar é a tinta de Mágico e Raro, a arma e o slot vazio (corpo nu). `docs/04` 17.4 já prevê o mecanismo e cita `vset.iron_guard` como exemplo. Toda peça nova passa por sua aprovação antes de entrar.
**Opções:**
- **A (recomendada). Um segundo conjunto.** Efeito: a troca de peça fica evidente desde a primeira corrida; custo: 5 modelos (≈ 2.500 a 4.200 triângulos somados) e 5 bases novas nas tabelas.
- **B. Só tinta de raridade, arma e slot vazio.** Efeito: zero modelo novo; a troca aparece só para Mágico e Raro, que são raros (~0,6 e ~0,5 por corrida); o aceite A3-11 fica fraco.

---

## 9. Pedidos de dados e de código (propostas)

### 9.1 Data Engineer (CSV)
1. `rules.csv` (chaves novas, tipo número, valores H3): `backpack_capacity` 40, `stash_capacity` 100, `sell_price_normal` 4, `sell_price_magic` 12, `sell_price_rare` 35, `sell_price_unique` 100, `ground_pickup_radius` 120 (uu), `currency_magnet_radius` 300 (uu), `ground_item_label_min_rarity` (magic).
2. `loot_entries.csv`: entrada de `item_base.worn_trousers` nas tabelas `common`, `elite` e `guardian` (peso 4, 5 e 4); `item_base.stone_maul` na `common` (peso baixo, a decidir); itens de baixo peso na `loot.crypt.area` (baús).
3. Se Q3-4 for A: 5 bases novas (`item_base.guard_helm`, `guard_cuirass`, `guard_gauntlets`, `guard_greaves`, `guard_sabatons`; nomes provisórios, funcionais) com `visualSetId = vset.iron_guard`, `itemLevel` 2 e implícito um passo acima do `starter`; entradas nas tabelas de elite e Guardião.
4. Opcional: `loot.crypt.heavy` para o Arauto (item 4 da seção 4.5).
5. Loc: as chaves marcadas "(nova)" desta tela (`ui.create.*`, `ui.death.nothing_lost`, `ui.boss.defeated`, Baú, vender, descartar, desfazer, Mochila cheia, Marco instalado) e as falas em `docs/05` continuam provisórias.

### 9.2 Backend / Tech Lead (core e API)
1. **Contêiner Mochila** no save (proposta: lista `backpack` no `CharacterState` ou no `SaveData`; `stash` fica como Baú), com capacidade vinda de `rules.csv`. Migração para `save_version` 3 só se não couber na v2 sem publicação.
2. **Equipar hipotético:** função que devolve os atributos do herói com e sem um item (para a comparação); nada de fórmula no C#.
3. **Venda e descarte** como operações do core (idempotentes, no mesmo salvamento) ou serviço de inventário que só chama o core; "Vender Comuns ao coletar" na coleta atômica.
4. **Expedição:** expor ao C# a lista de condições e ações de IA aceitas, a previsão em faixa com o selo de calibração e os motivos de bloqueio (RF-31, RF-37, RF-43) como códigos estáveis.
5. **Seed do loot manual:** derivada da corrida e do índice da morte (RNG de loot separado), com o contador do chefe gravado antes de entregar o item (RF-55).
6. Revisar `reachedEnd` (H3-01).

### 9.3 Frontend / Integração
1. Camada C# de **save**, **expedição** e **loot** sobre a API C (`shatter_save_*`, `shatter_expedition_*`, `shatter_loot_roll`).
2. Ação `Interact` em `Echoes.inputactions`; mapas de ação por cena.
3. `ModularCharacter` conforme `docs/04` 17.4 (catálogo, máscara de regiões, tinta por `SO_RarityTint`).
4. Troca de cena Refúgio ↔ Cripta no lugar do `TODO(area.refuge)` do `PortalZone`.

---

## 10. Referências de design (tabela "No jogo de referência | No nosso | Por quê")

| No jogo de referência | No nosso | Por quê |
|---|---|---|
| ARPGs de loot (Diablo, Path of Exile): rótulo de todos os itens e filtros de loot | Rótulo só de Mágico+ por padrão, `Alt` mostra todos; sem filtros; ~3 a 4 itens por corrida e Comuns viram Ouro na coleta | O protótipo prova P1 e P3, não a economia de loot; pouco loot e leitura rápida |
| ARPGs de loot: o item raro é uma surpresa só do chão | O Único sai de uma garantia (1ª vitória) mais proteção contra azar, e o relatório da expedição **ensina** uma troca (dica) | "Nenhuma build depende de sorte" (plano, seção 6); a decisão muda por causa do relatório, não só do drop |
| Souls: fogueira restaura tudo | Checkpoint restaura inimigos mortos, mas XP e itens ficam | P4: sessão curta rende; já decidido em `docs/13` R2.4 |
| Idle games: coletar ao abrir | Expedição só em área dominada, com cargas ganhas jogando, e o relatório empurra de volta para "Jogar esta rota agora" | P1 e P3; o idle nunca substitui o jogo |

O **twist** que muda decisões: a expedição só existe depois de o jogador vencer o Guardião na mão; as cargas vêm de jogar; o relatório sugere uma troca de item ou de regra. Quem pula a Cripta não tem o que configurar.

---

## 11. Economia do protótipo: vendedor e encantamentos

Criada em 17/10/2026 a partir da decisão do dono: no protótipo o Ouro serve para (1) um **Vendedor** no Refúgio, que compra itens e vende frascos de recarga, e (2) **Melhorias** de equipamento feitas por um **Encantador**. A história é do dono: o Vendedor e o Encantador são **funções**, sem nome próprio, sem fala nova e sem lore. Aparecem só por chave de Loc provisória (`npc.vendor.name` = "Vendedor", `npc.enchanter.name` = "Encantador"); trocar nome ou rosto depois é trocar a chave. Bram e Irmã Odete continuam sem função (docs/05). Todo número daqui é **[HIPÓTESE]**.

**Pilares.** P2 (build com identidade): o Ouro e as Lascas viram escolhas sobre o *seu* equipamento, não só números maiores. P3 (planejar o retorno): a expedição rende o material, e o jogador decide em que peça gastá-lo antes da próxima. P4 (respeitar o tempo): uma corrida de 8 minutos já paga uma melhoria; nada exige farm. P1 (conquistar pela ação): o frasco de recarga não funciona na arena do Guardião nem na expedição, e a melhoria nunca cria Único (o item de topo continua vindo só do chefe).

### 11.1 O que o plano já previa (e o que o core já tem)

| Fonte | O que diz | Como entra aqui |
|---|---|---|
| `docs/00` seção 6, "Crafting com o Bram" | Refinar (Comum + Lascas vira Mágico), Reforjar (sorteia os afixos de novo; usa Cinzas de Memória), Fixar Inscrição (Raro + Inscrição, 1 por item), Lapidar (Item + Ouro melhora valores dentro da faixa), Reciclar (devolve Lascas e Cinzas). "Crafting nunca destrói o item; a tela avisa antes." "O Ouro vira poder só por crafting e escolhas." | Cinco operações do protótipo, com as trocas da tabela 11.4 |
| `ItemInstance.hasInscription` | Já existe: "Fixar Inscrição, no máximo 1 por item" | Reaproveitado como trava de **Adicionar afixo** (1 por item) |
| `affixes.csv`, coluna `craftInscription` | Existe e está `false` em todos os 8 afixos | Define a lista de candidatos de Adicionar afixo (pedido ao Data em 11.8) |
| `RollAffixes` | Mágico 1 a 2, Raro 3 a 4, no máximo 2 prefixos e 2 sufixos, grupos exclusivos, `allowedSlots`, `minItemLevel` | Toda melhoria que sorteia afixo obedece às mesmas regras |
| `RngStream` | Só `Combat`, `Loot`, `Events`; **não há fluxo de crafting** | Fluxo novo `Crafting = 4` (pedido ao Backend em 11.9) |
| Materiais | Só **Lascas** (`material.shards`) existem nos dados. **Cinzas de Memória e Inscrições não existem** | Nenhum material novo: Lascas fazem o papel de todos |

### 11.2 Vendedor

**Compra: qualquer item da Mochila ou do Baú, não equipado**, pelo valor do core (`shatter_inventory_sell_value`: preço da raridade x (1 + `sell_level_factor` x (itemLevel − 1)), arredondado; hoje 4/12/35/100). Sem número novo de compra: um único preço evita que o jogador compare Vendedor com "mesa de troca". As confirmações da S-07 (Raro simples, Único segurar 1 s, desfazer 5 s para Comum e Mágico) continuam valendo. Equipado não vende (core).

**Vende: um item, o Frasco de Recarga (`consumable.refill_flask`). Não vende poção extra.** Motivo: `docs/13` item 2 fixa Vida em 3 cargas e Resguardo em 2, calibradas para a luta do Guardião ("3 + ~3 curas") e para o idle; as poções já enchem de graça ao entrar no Refúgio, ao passar num checkpoint e ao reiniciar a luta. Vender mais carga no Refúgio seria comprar o que já é de graça, e vender carga máxima estouraria o limite. O frasco **não aumenta o máximo**: é um consumível que o jogador leva na Cripta e usa para restaurar **1 carga** da poção com menos cargas (empate: Vida), respeitando o máximo e a trava global de 1 s. Regras:
- Carrega no máximo **3** (`carry cap`); Pilha sem ocupar espaço, como Ouro e Lascas.
- **Bloqueado na arena do Guardião** (a luta continua testando as cargas do `docs/13`) e **fora do idle** (a expedição não usa frasco; as regras de IA continuam só com as poções).
- Não vira Fervor, não conta como poção em `refillOnEliteKill`.
- Preço 50 Ouro [HIPÓTESE H3-17]: com ~200 Ouro por corrida, 4 frascos por corrida é o teto, e o limite de 3 evita estocar.
- Serve ao P4: errar num trecho longo entre checkpoints custa 50 Ouro, não 5 minutos.

**Recompra: sim.** O Vendedor guarda os **10 últimos itens comprados do jogador** (`vendor_buyback_slots`); recomprar custa 1,25 x o valor pago ao jogador, arredondado para cima [H3-18]. Motivo: o desfazer de 5 s da S-07 cobre o clique errado; a recompra cobre o "vendi o Raro e só vi no relatório" sem tornar a venda grátis de desfazer. A lista é gravada no save (não some ao fechar o jogo). O 11º item vendido expulsa o mais antigo (que deixa de existir); se o mais antigo é Raro ou Único, a venda do 11º pede confirmação extra com aviso. Único vendido não sai da recompra a não ser por expulsão ou recompra.

### 11.3 S-14 Vendedor (`VendorView`, falar com o Vendedor no Refúgio)

- **Objetivo:** esvaziar a Mochila e abastecer frascos em menos de 30 s.
- **Layout:** à esquerda a Mochila (a mesma grade 8 x 5 da S-05), à direita três abas: **Vender**, **Recomprar**, **Frascos**. Rodapé: Ouro atual e Lascas.
- **Aba Vender:** clicar em um item mostra "Vale N Ouro" e o botão "Vender"; `Alt+Clique` marca como "lixo" e o botão "Vender marcados" mostra o total e a contagem por raridade (Raro e Único listados à parte, exigem confirmar). Equipado aparece cinza com tooltip "Equipado".
- **Aba Recomprar:** os 10 itens com o preço de recompra; "Recomprar" se há Mochila livre e Ouro; senão botão cinza com o motivo.
- **Aba Frascos:** o Frasco de Recarga, preço, quantos o jogador tem (`n/3`), botão "Comprar 1" e "Encher até 3".
- **Estados:** Mochila vazia ("Nada a vender"); sem Ouro (botão cinza `semantic.warning`); frasco no máximo (botão cinza); recompra vazia.
- **Teclado:** `Esc` fecha; `Enter` confirma; tooltip S-06 em todos os itens.
- **Texto:** todo por chave `ui.vendor.*` (11.10). Nenhuma fala de personagem; só rótulos.

### 11.4 Encantamentos (Melhorias)

Cinco operações, todas no Refúgio, todas em item que o jogador possui (Mochila, Baú ou equipado; o chão não). Cada uma tem o custo em Ouro e Lascas da tabela 11.6, **cobrado e aplicado de forma atômica** (se não há Ouro ou Lascas, nada muda). Nenhuma operação destrói o item (exceto Desmontar, que é explícita e pede confirmação).

| ID | Operação | Entrada | Resultado | Pilar | Diferença do plano |
|---|---|---|---|---|---|
| `craft.refine` | **Refinar** | Item **Comum** | Vira **Mágico** com 1 a 2 afixos sorteados (mesma regra de `RollAffixes`) | P4 | Igual ao plano |
| `craft.reforge` | **Reforjar** | Item Mágico ou Raro | **Sorteia de novo todos os afixos, mantendo a quantidade** que o item já tem e o `hasInscription`; zera a lapidação dos afixos novos. Opcional: **travar 1 afixo** (ele fica como está, com valor e lapidação; os outros são sorteados). Travar custa mais Lascas | P2 | O plano usa Cinzas de Memória (não existem); aqui só Lascas. A trava é nova (ver o twist abaixo) |
| `craft.add` | **Adicionar afixo** | Item Mágico com 1 afixo, ou Raro com menos de 4, **sem** `hasInscription` | O sistema sorteia até **3 candidatos** elegíveis (`craftInscription = true`, respeitando slot, grupo, nível e o limite 2 prefixos + 2 sufixos); o jogador **escolhe 1**; entra um afixo com valor sorteado; `hasInscription = true` | P2 | O plano usa Inscrição como item e lista fixa; aqui o custo é Lascas e a lista é sorteada. "1 por item" mantido |
| `craft.polish` | **Lapidar** | Um afixo de um item Mágico ou Raro | Sobe o valor 25% da faixa em direção ao máximo (`valor = min(máx, valor + 0,25 x (máx − mín))`; inteiros arredondados); até **3 passos por afixo**; **sem sorteio** | P2 | Igual ao plano; determinístico para o jogador poder planejar |
| `craft.dismantle` | **Desmontar** | Item Comum, Mágico ou Raro (não equipado) | Some e devolve Lascas (2 / 5 / 12) | P4 | Plano: "Reciclar" (Lascas e Cinzas) |

**"Encantar com Lascas"** não é uma operação a mais: as Lascas são o **custo** de Refinar, Reforjar, Adicionar afixo e a **receita** de Desmontar. Isso evita um quinto botão que repetiria Reforjar.

**Twist (decisão que muda por causa da mecânica).** Reforjar com trava transforma "joga fora tudo" em "protege o que presta": o jogador decide qual afixo é a coluna da peça e paga para guardá-lo. A referência (Path of Exile, Last Epoch) deixa travar afixos em fluxos de crafting; aqui o limite é **1 afixo travado**, o custo de Lascas dobra, e o preço sobe a cada Reforjar da mesma peça (11.6), então "reforjar até acertar" tem teto de gasto razoável, não infinito.

| No jogo de referência | No nosso | Por quê |
|---|---|---|
| Path of Exile: orbes de crafting dão resultado totalmente aleatório e há mercado/stash de itens para refazer | 5 operações, **um só material** (Lascas) mais Ouro; preço sobe a cada Reforjar da peça; travar 1 afixo; lapidar sem sorteio | O protótipo prova que Ouro e Lascas viram *escolha*, não que existe um jogo de crafting inteiro. Menos operações, mais clareza |
| Last Epoch: afixos têm "tiers" e o jogador sobe a qualidade com material | Lapidar sobe a qualidade em 3 passos até o máximo da faixa | Mesma decisão ("vale a pena investir nesta peça?") sem tabela de tiers nova |
| Diablo 3/4 (Encantadora, Ocultista): rerrola 1 propriedade | Reforjar com 1 afixo travado = o inverso (guarda 1, rerrola o resto) | O Guerreiro tem poucos afixos (8): rerrolar 1 só dá pouca variação; guardar o bom e rerrolar o resto muda mais a peça |

### 11.5 Limites e o que nunca pode acontecer

**Limites de uso**

1. **Raridade só sobe uma vez e só por Refinar:** Comum vira Mágico. Mágico **nunca** vira Raro e Raro **nunca** vira Único (nenhuma operação muda a raridade além de Refinar).
2. **Único é intocável:** nenhuma operação de melhoria aceita Único (nem Desmontar). Pode vender (segurar 1 s) e descartar.
3. **Limite de afixos por raridade:** Mágico até 2, Raro até 4, Comum 0 (`docs/06`). Adicionar afixo recusa quando o item já está no limite ou quando `hasInscription` é verdadeiro.
4. **1 Adicionar por item** (`hasInscription`).
5. **Lapidar:** máximo 3 passos por afixo (`polish_max_steps`); recusa se o valor já está no máximo da faixa.
6. **Reforjar:** sem limite de vezes, mas o preço sobe (11.6, teto de 3 x).
7. Só no Refúgio. Equipado pode ser melhorado, mas com expedição `Running` aparece o aviso "Vale a partir da próxima expedição" (a build está congelada no snapshot).
8. A pool de afixos do protótipo é pequena (**armas: 3; botas: 5; elmo, peitoral, luvas, calça: 4 a 5**). Raro de arma tem 3 e **não tem o que adicionar**; Raro com 4 afixos só existe em armadura. A UI explica o motivo do botão cinza: "Sem afixo disponível". Ver **Q3-5**.

**Nunca pode acontecer (cada item tem teste [SC])**

- Subir raridade além da regra de cima; criar Único; mudar `uniqueId`; mudar `baseId`, `itemLevel` ou `uid`.
- Afixo repetido ou do mesmo `group`; afixo fora de `allowedSlots` ou com `minItemLevel` maior que o do item; valor fora de [`minValue`, `maxValue`] do afixo; mais de 2 prefixos ou 2 sufixos.
- Gastar Ouro ou Lascas que o jogador não tem (saldo nunca negativo); cobrar sem aplicar, ou aplicar sem cobrar; aplicar duas vezes se o jogo cair depois de gravar.
- Perder o item por falha (queda, buffer pequeno, erro): a operação é tudo ou nada no mesmo salvamento (como RF-55).
- Qualquer sorteio fora do fluxo `Crafting` (mexer em melhoria nunca desloca o loot nem o combate).
- Reforjar mudar a quantidade de afixos do item.
- O C# decidir, calcular ou sortear custo, resultado ou candidato.

### 11.6 Determinismo

- **Fluxo próprio:** `RngStream::Crafting` (novo), separado de `Loot`, `Combat` e `Events`.
- **Semente por operação:** função pura de (`craft_seed` do save, `uid` do item, `craft_steps` do item, tipo da operação). Nenhum "contador global": o mesmo item, no mesmo estado, na mesma etapa, dá o mesmo resultado. Consequência: **recarregar o save antes de confirmar não muda o sorteio**; o jogador não ganha nada com "salvar e recarregar até sair bom". `craft_seed` nasce no "Novo jogo" a partir da semente do personagem; `craft_steps` (uint16) sobe a cada Refinar, Reforjar e Adicionar da peça, na gravação.
- **Prévia sem custo:** a UI mostra faixa e custo antes de confirmar, **nunca o resultado**. Os candidatos de Adicionar afixo só são sorteados ao abrir a escolha e são os mesmos se o jogador fechar e reabrir (mesma semente). Escolher um dos 3 consome o passo.
- **Brecha aceita [H3-19]:** o resultado de uma peça depende do seu `craft_steps`, então a ordem das operações *nessa peça* muda o resultado (Adicionar antes de Reforjar não sorteia o mesmo que o inverso). Operações em outras peças não mudam nada. Como cada passo custa Lascas e Ouro, o jogador não vê o futuro sem pagar. Documentado, sem mitigação extra.
- **Lapidar** não tem sorteio e não consome o fluxo.
- **Testes [SC]:** mesmo save + mesma operação = mesmo resultado byte a byte; 1 milhão de Reforjar em itens de cada raridade e slot sem violar nenhuma regra de "Nunca pode acontecer"; operação interrompida no meio (injeção de falha) deixa o save igual ao de antes.

**Fórmula de custo (resumo, números na 11.8):** custo final = custo base x (1 + `craft_cost_level_factor` x (itemLevel − 1)), arredondado para cima; Reforjar multiplica por `1 + reforge_step_mult x (reforges anteriores da peça)`, com teto `reforge_mult_cap`; travar 1 afixo multiplica **só as Lascas** por `reforge_lock_cost_mult`.

### 11.7 S-15 Encantador (`EnchantView`, falar com o Encantador no Refúgio)

- **Objetivo:** escolher uma peça, ver o que cada melhoria custa e o que ela pode fazer, e decidir sem medo de clicar errado.
- **Layout:** à esquerda a Mochila e o equipamento (a grade da S-05) e o boneco; ao centro o **item escolhido** com seus afixos (cada afixo mostra barra de qualidade `valor entre mín e máx` e os passos de lapidação `●●○`); à direita uma lista vertical das 5 operações; rodapé: Ouro e Lascas.
- **Fluxo:** (1) clicar no item; (2) clicar na operação; (3) o painel central troca para a **confirmação**: custo em Ouro e Lascas (com o que o jogador tem; vermelho `semantic.warning` se falta), faixa do resultado, aviso quando perde algo; (4) Confirmar (segurar 0,5 s para Reforjar e Desmontar; clique simples nas outras) ou Voltar.
- **Reforjar:** lista os afixos atuais com um **cadeado** por afixo (1 no máximo); o botão mostra o custo com e sem trava. Aviso fixo: "Todos os afixos não travados serão sorteados de novo. Não dá para desfazer." (Q3-6).
- **Adicionar afixo:** abre 3 cartões (nome, faixa); o jogador escolhe 1 e confirma. Se não há candidato: botão cinza com "Sem afixo disponível".
- **Lapidar:** o jogador clica no afixo; a tela mostra "valor atual → valor novo" e o custo do passo (1º, 2º, 3º).
- **Desmontar:** modal com as Lascas devolvidas; Raro pede segurar 1 s; Único não aparece (botão cinza com "Item único não pode ser melhorado").
- **Resultado:** o item muda no mesmo quadro com um destaque no afixo alterado (cor `item_text.affix` mais brilho, sem som novo); toast "Item melhorado"; **auto-save** (RF-54: "ao crafting").
- **Estados e botões cinza com motivo:** item Único; limite de afixos; já lapidado no máximo; sem Ouro ou Lascas; sem afixo elegível; `hasInscription`.
- **Teclado:** setas, `Enter`, `Esc` volta; `Tab` troca de coluna.
- **Texto:** chaves `ui.enchant.*`. Nenhum nome de personagem, nenhuma fala.
- **Pausa e tempo real:** é tela de Refúgio; nada a pausar.

### 11.8 Tabelas de dados e chaves novas

IDs `craft.*` e chaves são estáveis depois de publicados. **Todos os números são [HIPÓTESE]**.

**`rules.csv`: chaves novas** (tipo `number`, exceto onde dito).

| Chave | Valor | Intenção |
|---|---|---|
| `vendor_buyback_slots` | 10 | Recompra cobre o erro de uma sessão sem virar estoque |
| `vendor_buyback_price_factor` | 1.25 | Recomprar custa um pouco mais do que se recebeu: o erro dói pouco, mas a venda não é grátis de desfazer |
| `refill_flask_carry_cap` | 3 | Teto de frascos levados; evita estocar para a arena |
| `refill_flask_charges` | 1 | Cada frasco restaura 1 carga |
| `craft_cost_level_factor` | 0.1 | Custo cresce 10% por nível de item acima de 1 (mesma ideia de `sell_level_factor`) |
| `reforge_step_mult` | 0.5 | Cada Reforjar da mesma peça soma 50% do custo-base ao próximo |
| `reforge_mult_cap` | 3.0 | Teto do multiplicador: o gasto não sobe para sempre |
| `reforge_lock_cost_mult` | 2.0 | Travar 1 afixo dobra só as Lascas |
| `reforge_lock_max` | 1 | Só 1 afixo travado por Reforjar |
| `add_affix_candidates` | 3 | Quantidade de cartões de Adicionar afixo |
| `polish_step_fraction` | 0.25 | Cada passo de Lapidar sobe 25% da faixa |
| `polish_max_steps` | 3 | Máximo de passos por afixo |
| `dismantle_shards_normal` | 2 | Receita do Comum (menos que Refinar custa: sem ciclo infinito) |
| `dismantle_shards_magic` | 5 | Receita do Mágico |
| `dismantle_shards_rare` | 12 | Receita do Raro |

**Tabela nova `craft_costs.csv`**

- Cabeçalho exato: `id,op,rarity,step,goldCost,shardCost`
- Esquema/validador: o Data Engineer ajusta. Propostas de regra: `id` com prefixo `craft.`; `op` em `refine|reforge|add|polish`; `rarity` em `normal|magic|rare|any`; `step` inteiro ≥ 0 (só a Lapidar usa 1 a 3; as outras usam 0); `goldCost` e `shardCost` inteiros ≥ 0; par (`op`, `rarity`, `step`) único; toda operação de 11.4 tem pelo menos uma linha (Desmontar não tem custo).

| id | op | rarity | step | goldCost | shardCost | Intenção |
|---|---|---|---|---|---|---|
| `craft.refine.normal` | refine | normal | 0 | 40 | 10 | Barato: o Comum é abundante; ~1 corrida para uma peça Mágica |
| `craft.reforge.magic` | reforge | magic | 0 | 60 | 12 | Rerrolar Mágico é decisão leve |
| `craft.reforge.rare` | reforge | rare | 0 | 120 | 20 | Raro é a coluna da build: custa claramente mais |
| `craft.add.magic` | add | magic | 0 | 90 | 15 | Sobe a peça de 1 para 2 afixos |
| `craft.add.rare` | add | rare | 0 | 200 | 25 | Sobe o Raro para o 4º afixo (só armadura) |
| `craft.polish.1` | polish | any | 1 | 60 | 0 | 1º passo: sumidouro de Ouro, sem Lascas |
| `craft.polish.2` | polish | any | 2 | 120 | 0 | Dobra |
| `craft.polish.3` | polish | any | 3 | 240 | 0 | Dobra de novo: fechar o afixo no máximo é caro |

**Tabela nova `vendor_stock.csv`**

- Cabeçalho exato: `id,refId,kind,priceGold,carryCap`
- Regras propostas: `kind` em `stack`; `refId` aponta para um ID de material ou consumível já cadastrado; `priceGold` inteiro ≥ 0; `carryCap` inteiro ≥ 1.

| id | refId | kind | priceGold | carryCap |
|---|---|---|---|---|
| `vendor.refill_flask` | `consumable.refill_flask` | stack | 50 | 3 |

**Mudança em `affixes.csv`:** coluna `craftInscription` = `true` nos 8 afixos do protótipo (hoje todos `false`). Quando houver mais afixos, o Data decide quais ficam disponíveis. **Pedido ao Data:** pelo menos 2 afixos novos de `main_hand` (ex.: dano de elemento, vida por acerto, escolha do Data) para que o Raro de arma possa chegar a 4 afixos e Reforjar tenha variação real (Q3-5).

**Mudança em `item_bases.csv`/`ItemInstance`:** nenhuma coluna; campos novos de save na 11.9.

### 11.9 Conta do ritmo: quanto Ouro e Lascas o jogador ganha

Fontes: `loot_entries.csv`, `encounters.csv`, `maps.csv` e a seção 4.5. Fervor no jogo manual: Ouro e Lascas x 1,25. Todas as contas são **esperanças** [H3-20] e foram feitas à mão; a medição fica para o `tools/batch_sim`.

**Corrida manual completa** (7 encontros, ~20 inimigos comuns, 2 elites, Guardião, 5 baús):

| Origem | Ouro | Lascas | Itens |
|---|---|---|---|
| ~20 comuns (35% x 55/100 x 10 de Ouro; 35% x 25/100 x 2 de Lascas) | 38,5 | 3,5 | 1,4 |
| 2 elites (2 sorteios x 60% x 40/93 x 25; idem Lascas 25/93 x 3,5) | 25,8 | 2,3 | 0,7 |
| Guardião (2 sorteios x 40/89 x 45; Lascas 25/89 x 6) | 40,4 | 3,4 | 0,5 |
| 7 encontros de área + 3 baús de área | 3,9 | 0,4 | 0 |
| 2 baús de elite | 25,8 | 2,3 | 0,7 |
| **Subtotal** | **134** | **11,9** | **3,4** |
| **x 1,25 (Fervor)** | **168** | **14,9** | |
| Venda dos ~3,4 itens (~2 Comuns x 4, ~1 Mágico x 12, ~0,4 Raro x 35, ~0,1 por Único) | ~35 | | |
| **Total por corrida** | **~200 Ouro** | **~15 Lascas** | |

Tempo: primeira vitória 8 a 12 min (`docs/14`), depois ~6 a 8 min. **Em 10 min de jogo manual: ~200 Ouro e ~15 Lascas.**

**Expedição** (idle: sem Fervor; ~3,0 comuns e 0,17 elite por encontro; ~8,3 Ouro e ~0,76 Lascas por encontro; ~0,27 item por encontro; **60 encontros por hora** [H3-20]: 6 s de viagem + ~25 s de luta (`docs/14`) cortados por recuperação e poções):

| Duração | Vigor efetivo (`vigor_h1_4` 1,0; 5 a 8 h 0,7) | Ouro (inclui Comuns vendidos na coleta) | Lascas |
|---|---|---|---|
| 1 h | 1,0 h | ~560 | ~46 |
| 5 h (o primeiro ciclo) | 4,7 h | ~2.630 | ~216 |
| 12 h (futuro, com 12 cargas) | 4 + 2,8 + 1,6 = 8,4 h | ~4.700 | ~385 |

Relação: 1 h de expedição ~ 2,8 corridas em Ouro e ~3 corridas em Lascas. Isso é coerente com o plano (a expedição rende cerca de 35% do jogo manual; aqui o Ouro por hora é ~28% do manual, 560 contra ~2.000 em 10 corridas/h): **o jogo manual rende mais por hora e o idle rende enquanto o jogador está fora.** Se o `batch_sim` mostrar mais que ~800 Ouro/h de idle, subir os custos ou baixar `drop` em vez de cortar o idle.

**Os custos contra a renda** (tabela 11.8, itemLevel 1):

| Meta do jogador | Custo | Em corridas | Em horas de expedição | Leitura |
|---|---|---|---|---|
| 1 Refinar (Comum vira Mágico) | 40 Ouro, 10 Lascas | 0,7 (Lascas) | 0,2 | A primeira melhoria sai de **uma corrida** |
| 1 Reforjar de Mágico | 60 Ouro, 12 Lascas | 0,8 | 0,3 | Uma corrida paga uma rerrolagem |
| 1 Reforjar de Raro | 120 Ouro, 20 Lascas | 1,3 | 0,4 | |
| Reforjar um Raro até acertar: 4 tentativas (multiplicador 1 + 1,5 + 2 + 2,5 = 7) | 840 Ouro, 140 Lascas | 9,3 (Lascas) | 3,0 | Meio dia de expedição por uma peça-chave |
| Reforjar com trava (Lascas x 2) 3 tentativas (mult. 1 + 1,5 + 2 = 4,5) | 540 Ouro, 180 Lascas | 12 | 3,9 | Mais caro em Lascas: o preço de proteger o bom afixo |
| Adicionar afixo a um Mágico | 90 Ouro, 15 Lascas | 1,0 | 0,3 | |
| Adicionar afixo a um Raro | 200 Ouro, 25 Lascas | 1,7 | 0,5 | |
| Lapidar 1 afixo até o máximo (3 passos) | 420 Ouro | 2,1 | 0,75 | Sumidouro de Ouro puro |
| **Projeto Mágico** (Refinar + Adicionar + Lapidar 2 passos) | 40 + 90 + 180 = 310 Ouro, 25 Lascas | 1,7 | 0,55 | Um Comum vira uma peça decente em ~2 corridas |
| **Projeto Raro** (4 Reforjar + Lapidar 1 afixo) | 840 + 420 = 1.260 Ouro, 140 Lascas | 9,3 | 3,0 | |
| Equipar as 6 peças (1 projeto Mágico cada) | 1.860 Ouro, 150 Lascas | 10 | 3,3 | Cabe nas **primeiras 5 h de expedição**, mas só vira Raro bom com tempo |
| Frasco de Recarga | 50 Ouro | 0,25 | 0,09 | 4 frascos por corrida é o teto |

**Leitura de ritmo (por que faz sentido):**
- Cada operação cabe em **uma corrida** de 8 a 10 min, então o P4 se cumpre: sessão curta rende uma melhoria.
- As **Lascas** limitam Refinar, Reforjar e Adicionar (custos na razão ~5 Ouro por Lascas; a renda é ~13 Ouro por Lascas), e o **Ouro** sobrante vai para Lapidar e frascos. Duas moedas, dois sumidouros: nenhum acumula sem uso.
- O primeiro ciclo (1 corrida + 5 cargas ~ 5 h de expedição + corridas intermediárias) dá ~2.800 Ouro e ~230 Lascas: dá para fazer o Projeto Mágico em 3 a 4 peças **ou** 1 Projeto Raro e sobra. O dono tem que **escolher onde investir**, que é o objetivo de P2.
- O teto é fixo: Lapidar fecha o afixo no máximo da faixa, Adicionar é 1 por item e Reforjar tem preço teto 3 x. A melhoria nunca ultrapassa o que um bom drop de Raro já pode dar; o objetivo é **aproximar** o loot comum do ótimo, não superá-lo.
- Venda e Desmontar competem: um Comum vale 4 Ouro ou 2 Lascas; um Mágico vale 12 Ouro ou 5 Lascas; um Raro, 35 Ouro ou 12 Lascas. Com 1 Lasca ~ 13 Ouro de renda, desmontar vale mais quando o jogador está travado em Lascas (esperado).
- Sem ciclo infinito: Refinar custa 10 Lascas, e Desmontar o Mágico devolve 5.

### 11.10 Chaves de Loc novas (provisórias, funcionais, sem lore)

| Chave | pt_BR (provisório) |
|---|---|
| `npc.vendor.name` | Vendedor |
| `npc.enchanter.name` | Encantador |
| `ui.vendor.title`, `ui.vendor.tab.sell`, `.tab.buyback`, `.tab.flasks` | Vendedor, Vender, Recomprar, Frascos |
| `ui.vendor.sell`, `ui.vendor.sell_marked`, `ui.vendor.buyback`, `ui.vendor.buy_flask`, `ui.vendor.fill_flasks` | Vender, Vender marcados, Recomprar, Comprar 1, Encher até 3 |
| `ui.vendor.value`, `ui.vendor.empty`, `ui.vendor.no_gold`, `ui.vendor.flask_max` | Vale {0} Ouro, Nada a vender, Ouro insuficiente, Já tem o máximo |
| `ui.vendor.buyback_warn_evict` | Esta venda expulsa da recompra um item {0}. Continuar? |
| `consumable.refill_flask.name` / `.desc` | Frasco de Recarga / Restaura 1 carga de poção. Não funciona na arena do Guardião |
| `ui.enchant.title`, `ui.enchant.op.refine/.reforge/.add/.polish/.dismantle` | Encantador, Refinar, Reforjar, Adicionar afixo, Lapidar, Desmontar |
| `ui.enchant.cost`, `ui.enchant.confirm`, `ui.enchant.lock`, `ui.enchant.step`, `ui.enchant.result` | Custo, Confirmar, Travar, Passo {0} de {1}, Item melhorado |
| `ui.enchant.warn_reforge` | Todos os afixos não travados serão sorteados de novo. Não dá para desfazer. |
| `ui.enchant.err.unique`, `.err.max_affixes`, `.err.max_polish`, `.err.no_gold`, `.err.no_shards`, `.err.no_candidate`, `.err.inscribed`, `.err.expedition_running` | Item único não pode ser melhorado; Limite de afixos; Já no máximo; Ouro insuficiente; Lascas insuficientes; Sem afixo disponível; Já recebeu um afixo adicionado; Vale a partir da próxima expedição |

Máximo de 12 caracteres em rótulos de moeda (regra `max=12` de `content.csv`).

### 11.11 Para o Backend (API C nova e dados de save)

Proposta; o contrato final é do Backend e do Tech Lead. Padrão da seção 11 do docs/09: o resultado vai em `*result`, a função devolve OK, recusa não muda nada, itens achados por `uid`. Sugestão de versão: `SHATTER_C_API_MINOR` 5 (só adições).

1. **Fluxo de RNG:** `RngStream::Crafting = 4` em `rng.h`; semente por operação = função pura de (`craft_seed`, `uid`, `craft_steps`, op). Nenhum consumo de `Loot`.
2. **Save** (sem quebrar a v2 se couber como opcional): `SaveData.craft_seed` (uint64), `ItemInstance.craft_steps` (uint16), `RolledAffix.polish` (uint8, 0 a 3), lista `vendor_buyback` (até 10 `{ItemInstance, valor pago}`), pilha `consumable.refill_flask` em `currency`/`stacks`.
3. **Funções de Encantador:**
   - `shatter_craft_quote(db, save, ci, uid, op, arg, shatter_craft_quote*)`: custo em Ouro e Lascas, flags de bloqueio por motivo (código estável) e faixa do resultado; **não altera**.
   - `shatter_craft_refine(db, save, ci, uid, *result)`
   - `shatter_craft_reforge(db, save, ci, uid, locked_affix_index (-1 = nenhum), *result)`
   - `shatter_craft_add_affix_offer(db, save, ci, uid, buf...)`: JSON com até 3 candidatos `{affix_id, min, max}`; **não altera**, mesma saída se repetida.
   - `shatter_craft_add_affix_apply(db, save, ci, uid, candidate_index, *result)`
   - `shatter_craft_polish(db, save, ci, uid, affix_index, *result)`
   - `shatter_craft_dismantle(db, save, ci, uid, *shards, *result)`
   - Resultados: `SHATTER_CRAFT_OK, NOT_FOUND, UNIQUE, WRONG_RARITY, AFFIX_LIMIT, ALREADY_INSCRIBED, POLISH_MAX, NO_CANDIDATE, NO_GOLD, NO_SHARDS, EQUIPPED_DISMANTLE, UNKNOWN_CONTENT`.
   - Atomicidade: cobra e aplica no mesmo estado do save; falha não muda nada; `RollAffixes` ganha variante que aceita **quantidade fixa** e **afixo travado**.
4. **Funções de Vendedor:** `shatter_vendor_sell` já é `shatter_inventory_sell` (docs/09); acrescentar `shatter_vendor_buyback_list_json`, `shatter_vendor_buyback(db, save, ci, index, int64* paid, *result)` (cobra e põe na Mochila; `FULL`, `NO_GOLD`), `shatter_vendor_buy(db, save, ci, stock_id, qty, *result)` (checa `carryCap`) e `shatter_vendor_sell` passa a gravar na lista de recompra (expulsa o mais antigo). `shatter_inventory_sell` continua como está para vendas sem Vendedor (ex.: "Vender Comuns ao coletar").
5. **Frasco:** `shatter_potion_use_flask(save, ci, *result)` restaura 1 carga da poção com menos cargas (empate: Vida), respeita o máximo e a trava de 1 s; recusa na arena do Guardião (`ARENA_LOCKED`) e fora do jogo manual (`IDLE_FORBIDDEN`).
6. **Dados:** carregar `craft_costs.csv`, `vendor_stock.csv` e as chaves novas de `rules.csv` no `ContentDB`, validar (prefixos, `op` e `rarity` válidos, todas as operações com linha). Nenhum número no código.
7. **Testes [SC]:** a lista de "Nunca pode acontecer" (11.5) como testes de propriedade (1 milhão de operações aleatórias, sem violar nenhuma regra); determinismo (mesmo estado, mesma saída; 1000 ciclos salvar/carregar no meio); atomicidade com falha injetada; idempotência do `uid` (repetir não cobra de novo).
8. `shatter_inventory_info_get`/`compare` já cobrem o tooltip; **nada de fórmula de custo no C#**.

### 11.12 Para o Frontend (telas)

1. **S-14 Vendedor** (`VendorView`) e **S-15 Encantador** (`EnchantView`) em UI Toolkit, tokens de `docs/03` (`nine_panel_ornate`), com todos os estados da 11.3 e da 11.7.
2. **Refúgio (S-04):** dois pontos de interação novos (Vendedor e Encantador), a no máximo 12 m do portal, de Ilsa e do Tico [H3-03]; marcador provisório (silhueta graybox) e rótulo `npc.vendor.name`/`npc.enchanter.name`; usar a ação `Interact`. Sem diálogo.
3. **Tooltip (S-06):** em Refúgio, mostrar "Vale N Ouro" (já previsto) e, no Encantador, a barra de qualidade e os passos `●●○` por afixo.
4. **HUD:** contador do Frasco de Recarga `n/3` ao lado das poções (só na Cripta, não na arena) e tecla nova `UseFlask` (padrão `3`, remapeável).
5. **Inventário (S-05):** as ações "Vender" e "Vender marcados" apontam para o Vendedor; no inventário, o menu de contexto ganha "Melhorar" (abre S-15 com o item).
6. **Camada C#** `VendorService` e `CraftingService` só chamam a API C (11.11); nenhuma fórmula, custo, sorteio ou regra no C#.
7. **Arte:** só marcadores graybox para o Vendedor e o Encantador; qualquer modelo de personagem novo passa pelo dono antes de entrar (CLAUDE.md).

### 11.13 Critérios de aceite

| ID | Critério | Verificação |
|---|---|---|
| A3-28 | O Vendedor compra qualquer item não equipado pelo valor do core; Raro pede confirmação; Único, segurar 1 s; equipado fica cinza | [SC] + [Unity] |
| A3-29 | Frasco de Recarga: máx. 3 carregados; restaura 1 carga sem passar do máximo; recusado na arena do Guardião e no idle | [SC] + [Unity] |
| A3-30 | Recompra: os 10 últimos itens vendidos persistem após fechar o jogo; recomprar custa 1,25 x o valor pago; o 11º expulsa o mais antigo | [SC] + [Unity] |
| A3-31 | Refinar só aceita Comum e entrega Mágico com 1 a 2 afixos válidos; Único, Mágico e Raro recusam | [SC] |
| A3-32 | Reforjar mantém a quantidade de afixos, não muda a raridade e respeita a trava de 1 afixo; o custo sobe 50% por Reforjar até 3 x | [SC] |
| A3-33 | Adicionar afixo oferece até 3 candidatos válidos, respeita o limite da raridade e `hasInscription`; fechar e reabrir mostra os mesmos candidatos | [SC] + [Unity] |
| A3-34 | Lapidar sobe 25% da faixa, no máximo 3 passos, sem sair da faixa; não consome o fluxo `Crafting` | [SC] |
| A3-35 | Em 1 milhão de operações aleatórias nenhuma regra de "Nunca pode acontecer" (11.5) é violada; nenhum Único é criado; saldo nunca fica negativo | [SC] |
| A3-36 | Mesmo save, mesmo item, mesma operação: mesmo resultado; recarregar antes de confirmar não muda o sorteio; falha injetada não cobra nem aplica | [SC] |
| A3-37 | O ritmo mede perto da conta da 11.9: em 10 corridas, 200 Ouro e 15 Lascas por corrida (±40%); 1 h de acelerador de debug dá Ouro e Lascas da faixa da expedição | [Manual] + `batch_sim` |
| A3-38 | O dono faz um Projeto Mágico (Refinar, Adicionar, Lapidar) com os recursos do primeiro ciclo e diz o que ganhou; anota o que não entendeu | [Manual] |

### 11.14 Hipóteses novas

| ID | Hipótese | Como medir |
|---|---|---|
| H3-17 | Frasco a 50 Ouro, máximo 3, não afrouxa a Cripta nem o Guardião | Quantos frascos por corrida; mortes antes e depois |
| H3-18 | Recompra de 10 itens a 1,25 x cobre o erro sem virar loja | Quantas recompras por sessão; o dono se sente seguro vendendo |
| H3-19 | Semente por (`uid`, `craft_steps`) impede "salvar e recarregar" e a brecha de trocar a ordem das operações é tolerável | O dono reclama de "azar fixo" ou tenta forçar |
| H3-20 | ~200 Ouro e ~15 Lascas por corrida; ~560 Ouro e ~46 Lascas por hora de expedição (60 encontros/h) | `batch_sim` 10 mil expedições e 10 corridas reais do dono |
| H3-21 | Os custos da tabela 11.8 dão uma melhoria por corrida e um projeto de peça por ~3 h de expedição | Quantas melhorias o dono faz até a 3ª expedição; Ouro/Lascas parados |
| H3-22 | Travar 1 afixo (Lascas x 2) mantém Reforjar como decisão e não como jogo de azar | O dono usa a trava; quantas Reforjar por peça |
| H3-23 | Lapidar em 25% da faixa e 3 passos fecha o afixo no máximo sem tornar o Raro de drop obsoleto | Valor dos Raros de drop vs. peças melhoradas |
| H3-24 | Desmontar (2 / 5 / 12 Lascas) compete bem com vender | Proporção de itens desmontados e vendidos |

### 11.15 Perguntas abertas para o dono

> **Decididas em 18/10/2026** pelo orquestrador, com autonomia dada pelo dono: Q3-5 opção A (2 afixos novos de arma) e Q3-6 opção A (sem desfazer, com trava e aviso).

### Q3-5 — Podemos acrescentar afixos novos para arma?
**Pergunta:** Os 8 afixos atuais só dão 3 opções para arma (dano aumentado, crítico, velocidade de ataque); posso pedir ao Data Engineer pelo menos 2 afixos novos de arma para as melhorias fazerem sentido?
**Contexto:** `RollAffixes` sorteia Mágico com 1 a 2 e Raro com 3 a 4 afixos. Como a arma só tem 3 afixos possíveis, o Raro de arma sempre tem os 3 e não pode receber "Adicionar afixo"; Reforjar de arma só embaralha valores, sem trocar afixos. Armadura tem 4 a 5 e funciona bem. Não é lore: são só números e rótulos.
**Opções:**
- **A (recomendada). Pedir 2 afixos novos de arma agora.** Efeito: Reforjar e Adicionar afixo viram decisões reais na arma; custo: 2 linhas de dados e 2 chaves de Loc para o Data.
- **B. Aceitar a limitação.** Efeito: zero dado novo; a arma só se melhora por Lapidar; o Encantador parece pobre para quem foca em arma.

### Q3-6 — Reforjar tem "desfazer"?
**Pergunta:** Quando o jogador reforja uma peça e o resultado é pior, ele pode voltar ao estado anterior ou não?
**Contexto:** O plano diz que o crafting nunca destrói o item e que "o risco é perder uma combinação boa, e a tela avisa antes". Um desfazer de 1 passo (guardar a versão anterior até o próximo Reforjar) tira o risco; sem desfazer o risco é real, e a trava de 1 afixo existe para esse medo. Como o sorteio é determinístico por peça e passo, recarregar o save não ajuda.
**Opções:**
- **A (recomendada). Sem desfazer, com trava e aviso.** Efeito: a decisão pesa; a trava dá controle; zero estado novo no save.
- **B. Desfazer o último Reforjar, grátis.** Efeito: menos medo, mas o jogador reforja sempre e desfaz até acertar, o que quebra o custo crescente; exige guardar a versão anterior no item.
- **C. Desfazer pagando metade do custo.** Efeito: meio-termo; ainda guarda estado e precisa de regra de custo e de tela.

### 11.16 Resumo das mudanças em seções anteriores
- 4.4: o parágrafo "O Ouro não tem uso" foi substituído por uma nota que aponta esta seção.
- S-04 (Refúgio): os pontos de interação 4 a 6 (Baú, Vendedor, Encantador) substituem "Baú e mesa de troca".
- Q3-3: marcada como resolvida.
- Pendência para outros documentos (não editados aqui): `docs/02` (RF para Vendedor e Melhorias), `docs/05` (nomes provisórios), `docs/06` (`craft_costs.csv`, `vendor_stock.csv`, chaves novas de `rules.csv`), `docs/09` (nova seção de API C 1.5).
