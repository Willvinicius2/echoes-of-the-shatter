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
  4. **Baú compartilhado e mesa de troca** (abre S-05 na aba Baú; é onde se vende; ver Q3-3 sobre quem compra).
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

**O Ouro não tem uso no protótipo** (sem Bram, sem Odete, sem respec pago, poção grátis). Ele é contador até a Etapa 4. Isso torna "vender" uma ação de gestão de espaço, não de economia. Ver **Q3-3**.

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

### Q3-3 — Para que serve o Ouro na Etapa 3 e quem compra os itens?
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
