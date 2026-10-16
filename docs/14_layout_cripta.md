# 14 — Layout jogável da Cripta Partida (Game Designer)

Escopo: protótipo do Guerreiro em `map.act1.crypt` (`maps.csv`), na escala aprovada pelo dono em 16/10/2026 (`13_design_pendencias.md`, bloco "Câmera e escala de mapa"): arena do Guardião de 40 × 40 m com pilares, salas de 24 a 32 m e corredores de 6 m. Este documento só especifica geometria e posições. Nenhum CSV, esquema ou código foi editado, e nenhuma lore foi criada: os nomes de sala abaixo são funcionais e provisórios.

Valores marcados **[HIPÓTESE]** precisam de playtest. Pilares usados (plano, seção 1): P1 Conquistar pela ação, P2 Build com identidade, P3 Planejar o retorno, P4 Respeitar o tempo.

## 1. Premissas e convenções

| Item | Valor | Fonte |
|---|---|---|
| Unidade | metro (1 uu = 1 cm, então 900 uu = 9 m) | `13`, cabeçalho |
| Origem | porta de entrada da Cripta, no centro da parede sul do Átrio: `(X=0, Z=0)` | pedido |
| Eixos | X = direita na tela, Z = "para cima" na tela (norte). O herói entra olhando para +Z | **[HIPÓTESE]**: confirmar com o Tech Lead que a câmera não tem rotação (yaw) própria |
| Câmera | 56 m; chão visível ≈ 24,8 m (X) × 17 m (Z) | dono, 16/10/2026 |
| Retângulo visível | centrado no herói: ±12,4 m em X e ±8,5 m em Z; diagonal até o canto ≈ 15,0 m | **[HIPÓTESE]** herói no centro da tela |
| Herói | 4,5 m/s; esquiva 4 m em 0,35 s | `13` itens 1 e 12 |
| Velocidades de inimigo | Sentinela 2,2 · Cão 3,8 · Cão Veloz 4,8 · Arqueiro 2,0 · Arauto 1,3 · Guardião 1,8 m/s | `enemies.csv` / `13` item 12 |
| Aggro | Sentinela e Arauto 9 · Elite Escudada 10 · Cão 11 · Cão Veloz 12 · Arqueiro 14 m | `enemies.csv` |
| Parede | sem espessura nos números; as retas abaixo são a face interna do chão jogável | |
| Largura de porta | 6 m (igual ao corredor) | pedido |
| Comprimento de corredor | 12 m entre salas; o do atalho tem 16 m | **[HIPÓTESE]**: o pedido só fixa a largura |

Consequência de design da câmera: o jogador só enxerga 8,5 m à frente (para cima) e 12,4 m para os lados. Nada além disso aparece na tela. Por isso as "vistas" são verticais e próximas (seção 6), e o perigo é lido por forma no chão, não por distância.

## 2. Mapa geral (esquemático, sem escala)

```
                 [ R09 ARENA 40x40 ]        (x 56..96, z 119..159)
                        | C09
 [R06]--C07--[R07]--C08--[R08 antecâmara]   (z 80..110)
   | C06
 [R05]--C05--[R04]--C04--[R03]              (z 40..68)
   :                      | C03
   : atalho A             |
 [R00]--C01--[R01]--C02--[R02]              (z 0..28)
 entrada
```

Serpentina de três fileiras mais a arena. O herói anda para leste na fileira 1, sobe pelo canto leste (C03), anda para oeste na fileira 2, sobe pelo canto oeste (C06), anda para leste na fileira 3 e sobe para a arena. Pegada total: X de -20 a 96 m, Z de -12 (sala secreta) a 159 m. O atalho A liga a fileira 2 de volta ao Átrio.

## 3. Salas e corredores

Retângulo = `x0,z0 → x1,z1`. Todas as salas ficam alinhadas pela parede sul (z0) na própria fileira.

| ID | Nome funcional (provisório) | Retângulo (m) | Tamanho X × Z | Centro | Papel |
|---|---|---|---|---|---|
| `room.crypt.r00_entry` | Átrio | -12,0 → 12,24 | 24 × 24 | (0,12) | entrada, Checkpoint 0, portal ao Refúgio, sem inimigos |
| `room.crypt.r01_patrol_a` | Sala da Patrulha A | 24,0 → 52,28 | 28 × 28 | (38,14) | `enc.crypt.patrol_a` |
| `room.crypt.r02_hounds` | Sala dos Cães | 64,0 → 96,28 | 32 × 28 | (80,14) | `enc.crypt.hounds` |
| `room.crypt.r03_herald` | Sala do Arauto | 64,40 → 96,68 | 32 × 28 | (80,54) | `enc.crypt.herald` |
| `room.crypt.r04_patrol_b` | Sala da Patrulha B | 24,40 → 52,68 | 28 × 28 | (38,54) | `enc.crypt.patrol_b` |
| `room.crypt.r05_firing_line` | Sala da Linha de Tiro | -20,40 → 12,68 | 32 × 28 | (-4,54) | `enc.crypt.firing_line`, início do atalho A |
| `room.crypt.r06_elite_shield` | Sala da Elite Escudada | -18,80 → 10,108 | 28 × 28 | (-8,94) | `enc.crypt.elite_shield` |
| `room.crypt.r07_elite_swift` | Sala da Elite Veloz | 22,80 → 52,110 | 30 × 30 | (37,95) | `enc.crypt.elite_swift` |
| `room.crypt.r08_antechamber` | Antecâmara | 64,83 → 88,107 | 24 × 24 | (76,95) | Checkpoint 3, respiro antes do chefe |
| `room.crypt.r09_arena` | Arena do Guardião | 56,119 → 96,159 | 40 × 40 | (76,139) | `enc.crypt.guardian` |
| `room.crypt.s01_niche` | Nicho (secreta) | 76,-12 → 88,0 | 12 × 12 | (82,-6) | baú secreto |

| ID | Liga | Retângulo (m) | Eixo | Comprimento |
|---|---|---|---|---|
| `cor.crypt.c01` | r00 → r01 | 12,10 → 24,16 | X | 12 |
| `cor.crypt.c02` | r01 → r02 | 52,10 → 64,16 | X | 12 |
| `cor.crypt.c03` | r02 → r03 | 77,28 → 83,40 | Z | 12 |
| `cor.crypt.c04` | r03 → r04 | 52,51 → 64,57 | X | 12 |
| `cor.crypt.c05` | r04 → r05 | 12,51 → 24,57 | X | 12 |
| `cor.crypt.c06` | r05 → r06 | -7,68 → -1,80 | Z | 12 |
| `cor.crypt.c07` | r06 → r07 | 10,91 → 22,97 | X | 12 |
| `cor.crypt.c08` | r07 → r08 | 52,91 → 64,97 | X | 12 |
| `cor.crypt.c09` | r08 → r09 | 73,107 → 79,119 | Z | 12 |
| `cor.crypt.sa` | r05 → r00 (atalho A, só abre pelo lado de r05) | -3,24 → 3,40 | Z | 16 |

Regra de combate: nenhum encontro nasce em corredor. Corredor de 6 m é zona de respiro (12 m = 2,7 s de caminhada) e de fuga em fila. Perseguidores seguem o herói pelo corredor (leash 20 m, `13` item 6).

## 4. Encontros (IDs de `encounters.csv`)

O mapa tem 7 encontros de patrulha e 1 de chefe, e cada um aparece uma vez no layout. Os intervalos de quantidade vêm do CSV; as posições listam `max` espaços, e um grupo de `n` inimigos usa os `n` primeiros espaços. `chanceElite` (0,05–0,10 do CSV) troca um comum por elite no mesmo espaço. A tabela de peso/`travelTime` do CSV só vale para o simulador idle: a ordem abaixo é a ordem fixa do jogo manual.

Dificuldade crescente: aprender área (1, 2), aprender telegraph lento e Guarda Quebrada (3), aprender atiradores (4, 5), aprender a ler modificador (6, 7), depois o chefe.

| # | Encontro | Sala | Chegada do herói | Inimigos (CSV) e espaços (x,z) | Patrulha | O que ensina |
|---|---|---|---|---|---|---|
| 1 | `enc.crypt.patrol_a` | r01 | de oeste, ao longo de z=13 | Sentinela Oca 2–3: (40,19) (43,21) (43,17) | vai e volta (40,19) ↔ (47,19), 1,1 m/s **[HIPÓTESE]** | agrupar e usar área; primeira fila de Sentinelas |
| 2 | `enc.crypt.hounds` | r02 | de oeste, z=13 | Cão-de-Cinza 3–5: (84,6) (86,7) (87,5) (89,9) (91,7) | parado (bando alerta junto, raio 15 m) | priorizar alvos; cerco com 2 fichas |
| 3 | `enc.crypt.herald` | r03 | de sul, ao longo de x=80 | Arauto de Pedra 1: (87,55). Sentinela 1–2: (88,49) (91,53) | parado | esquiva no tempo; Escudada/Guarda Quebrada no Arauto |
| 4 | `enc.crypt.patrol_b` | r04 | de leste, z=54 | Sentinela 1–2: (38,53) (36,56). Arqueiro Fantasma 1–2: (34,61.5) (42,46.5) | Sentinelas (36,56) ↔ (42,53) | primeiro atirador, fechar distância |
| 5 | `enc.crypt.firing_line` | r05 | de leste, z=54 | Sentinela 1–2: (-6,55) (-8,53). Arqueiro 2–3: (-2,61.5) (-2,46.5) (-12,61.5) | parado | usar pilares de cobertura; atiradores em cruz |
| 6 | `enc.crypt.elite_shield` | r06 | de sul, ao longo de x=-4 | Sentinela Escudada 1: (4,99). Sentinela 1–2: (1,100) (7,102) | parado | ler a casca dourada; Escudada quebra a barreira |
| 7 | `enc.crypt.elite_swift` | r07 | de oeste, z=94 | Cão Veloz 1: (45,101). Cão-de-Cinza 2–3: (41,101) (47,99) (44,102) | parado | o Veloz não se foge (4,8 > 4,5 m/s): esquivar e usar pilares |
| B | `enc.crypt.guardian` | r09 | de sul, pelo corredor C09 | Guardião da Cripta: (76,147), olhando para sul | n/a | tudo acima, mais a Investida do Escudo |

Regra para pesos e idle: o simulador sorteia pelos pesos do CSV, sem posição. Se um dia o jogo manual passar a sortear encontros por sala, os espaços acima servem de gabarito de formação.

## 5. Checkpoints, portal, baús, segredos e atalhos

### 5.1 Checkpoints e portal

| ID | Posição (x,z) | Onde | Quantos encontros já passaram | Observação |
|---|---|---|---|---|
| `cp.crypt.0` | (0,8) | Átrio | 0 | ponto de partida; enche poções (`13` item 2) |
| `cp.crypt.1` | (58,54) | corredor C04, logo depois do Arauto | 3 | ponto "difícil" já vencido |
| `cp.crypt.2` | (16,94) | corredor C07, depois da Elite Escudada | 6 | só falta a Elite Veloz e o chefe |
| `cp.crypt.3` | (76,92) | Antecâmara | 7 | volta ao chefe em ~8 s de caminhada |
| `spawn.crypt.arena` | (76,121) | início da arena (reinício da luta) | 7 | morte no chefe reinicia a luta na hora (plano seção 5) |
| `portal.crypt.entry` | (-8,6) | Átrio | n/a | portal de volta ao Refúgio do Marco |
| `marker.crypt.return` | (76,139) | centro da arena, aparece ao vencer o Guardião | n/a | Marco de Retorno (plano seção 3) |
| `portal.crypt.exit` | (76,149) | arena, aparece junto do Marco | n/a | portal ao Refúgio depois do chefe |

Inimigos já vencidos ficam mortos depois de morrer e voltar a um checkpoint **[HIPÓTESE]** (o plano só diz "volta ao último checkpoint sem perder itens nem XP"). Se o dono preferir respawn, o atalho A e CP2 passam a valer mais.

### 5.2 Baús

Todos usam `loot.crypt.area`, exceto os de recompensa de elite, que usam `loot.crypt.elite` **[HIPÓTESE]**.

| ID | Posição (x,z) | Sala | Como se chega | Tabela |
|---|---|---|---|---|
| `chest.crypt.01` | (50,3) | r01, canto sudeste | ao lado do caminho, desvio ~11 m | `loot.crypt.area` |
| `chest.crypt.02` | (82,-8) | r02 → nicho secreto | parede rachada (5.3) | `loot.crypt.area` |
| `chest.crypt.03` | (26,66) | r04, canto noroeste | depois dos atiradores | `loot.crypt.area` |
| `chest.crypt.04` | (-15,106) | r06, canto noroeste | depois da Elite Escudada | `loot.crypt.elite` |
| `chest.crypt.05` | (50,108) | r07, canto nordeste | depois da Elite Veloz | `loot.crypt.elite` |

O Único do Guardião não está em baú: cai do chefe (`13` item 9).

### 5.3 Segredos leves e atalho

| ID | O quê | Onde | Como abre | Pilar | Dica visual (Art) |
|---|---|---|---|---|---|
| `secret.crypt.cracked_wall` | parede rachada com nicho de 12 × 12 m e baú 02 | face sul de r02, em x 80..83, z=0 | um golpe de Investida, Fenda de Pedra ou Escudada (não o Corte de Ferro) | P2: dá um uso fora do combate às habilidades | rachadura clara e poeira dourada caindo, legível a 8 m |
| `shortcut.crypt.a` | portão ligando r05 a r00 (corredor `cor.crypt.sa`) | (0,40) em r05 | alavanca/interação do lado de r05; do lado do Átrio fica fechado | P4: depois do 5º encontro, o jogador volta ao portal em ~25 s em vez de 70 s | portão de grade com luz do Átrio vazando |

Segredo e atalho não têm texto de lore. Nenhum dos dois é obrigatório para vencer.

## 6. Arena do Guardião (40 × 40 m) e a Investida do Escudo

Coordenadas locais da arena (`rx, rz`) têm origem no centro (76,139): `mundo = (76 + rx, 139 + rz)`. A entrada está em `rz = -20` (porta de 6 m), vista do lado de fora por C09.

### 6.1 Pilares (docs/13 item 4: "Investida do Escudo que bate na parede da arena" e arena com pilares confirmada pelo dono)

Pilar: cilindro de 2,5 m de diâmetro (raio 1,25 m) e 4 m de altura **[HIPÓTESE]**, colisor sólido, dá cobertura contra flecha e contra a Investida, não bloqueia o cone do martelo.

| ID | Local (rx,rz) | Mundo (x,z) | Dist. ao centro | Dist. ao Guardião inicial (0,8) | Papel |
|---|---|---|---|---|---|
| `pil.arena.1` | (-6,-6) | (70,133) | 8,5 | 15,2 | anel interno, sudoeste |
| `pil.arena.2` | (6,-6) | (82,133) | 8,5 | 15,2 | anel interno, sudeste |
| `pil.arena.3` | (-6,6) | (70,145) | 8,5 | 6,3 | anel interno, noroeste |
| `pil.arena.4` | (6,6) | (82,145) | 8,5 | 6,3 | anel interno, nordeste |
| `pil.arena.5` | (-14,0) | (62,139) | 14,0 | 16,1 | anel externo oeste |
| `pil.arena.6` | (14,0) | (90,139) | 14,0 | 16,1 | anel externo leste |
| `pil.arena.7` | (0,15) | (76,154) | 15,0 | 7,0 | fundo, atrás do chefe |
| `pil.arena.8` | (0,-13) | (76,126) | 13,0 | 21,0 | "para-vento" de quem entra: quebra a linha reta porta-chefe |

### 6.2 Por que a Investida bate

Dados do item 4: investida de 7 m a ~10 m/s (~0,7 s), corredor de 1,5 m, recarga própria de 12 s, só na fase 2. Considerando o corpo do Guardião com raio de ~1,2 m **[HIPÓTESE]**, a investida para no pilar quando a distância centro a centro é menor ou igual a 7 + 1,25 + 1,2 = **9,45 m**. O anel interno fica a 8,5 m do centro e o chefe passa a maior parte da luta dentro dele; qualquer pilar do anel interno alcança o chefe parado no centro (8,5 < 9,45). Os pilares externos e as paredes cobrem quem arrasta o chefe para a borda. Resultado: de qualquer ponto da arena, o chefe está a menos de 9,45 m de um pilar ou a menos de ~8,2 m de uma parede.

Como o jogador usa: ficar com o pilar entre o chefe e ele, esperar o telegraph de 0,9 s e esquivar para o lado. O Guardião para a 2,45 m do centro do pilar, então quem está atrás do pilar fica fora do corredor. O impacto abre o escudo por 5 s e atordoa 2,0 s (`13` item 4.3). A investida **não é o único jeito** de abrir o escudo (Guarda Quebrada e contornar por trás continuam), então o pilar é um atalho que recompensa leitura, não uma exigência (P1).

Pedido de ajuste ao item 4.3 do `13` **[HIPÓTESE]**: a Investida só é escolhida quando o jogador está entre 3 e 7,5 m do chefe (assim o jogador sempre está na tela, ver seção 8, e a Investida nunca é usada colado ao herói, onde o Golpe de Escudo já cobre).

Contornar pilar: com raio de órbita de 3,5 m o herói gira a 4,5 / 3,5 ≈ 74°/s; o giro do chefe é 60°/s (fase 1) e 75°/s (fase 2). Na fase 1 o pilar dá a janela de "por trás" do escudo; na fase 2 ela fecha. É a intenção (a fase 2 pede a Investida ou a Escudada). Tudo **[HIPÓTESE]**.

Alvo de playtest: 30% a 50% das Investidas terminam em pilar ou parede. Abaixo de 20%, mover os pilares externos 2 m para dentro; acima de 60%, tirar `pil.arena.5` e `pil.arena.6`.

### 6.3 Outros pontos da arena

| ID | Posição (x,z) | Uso |
|---|---|---|
| `boss.start` | (76,147) | Guardião parado, olhando para sul |
| `trigger.arena.start` | retângulo 71,121 → 81,125 | herói entra: porta C09 fecha em z=119,5 **[HIPÓTESE]**, primeira ação do chefe 1,5 s depois (item 4.3) |
| `summon.mark.1` / `.2` | (66,137) / (86,137) | marcas das 2 Sentinelas da fase 2, ±10 m do centro. O item 4.4 diz "~600 uu nos flancos do chefe": usar o flanco relativo (±6 m do chefe) e cair nestas marcas se o ponto ficar dentro de um pilar |
| `spawn.crypt.arena` | (76,121) | reinício da luta |

A arena de 40 m não cabe na tela (24,8 × 17 m). A luta é lida pelo chão: cone de martelo de 3,8 m, corredor da Investida de 7 m, marcas de invocação. Se o enquadramento atrapalhar, avaliar deslocar a câmera até 2 m para o chefe durante a luta, sem mudar a altura de 56 m (Tech Lead e Art Director decidem) **[HIPÓTESE]**.

Oclusão: pilares de 4 m podem esconder o herói da câmera 3/4. Pedido ao Art Director: pilar vira translúcido (fade) quando o herói está atrás dele.

## 7. Ritmo

Premissas: herói a 4,5 m/s; combates de 15–30 s e respiro de 5–10 s (plano seção 5). Todos os tempos **[HIPÓTESE]** até o playtest.

### 7.1 Caminho principal (do (0,0) até a porta da arena)

Linha do caminho: (0,0) → (0,13) → (80,13) → (80,54) → (-4,54) → (-4,94) → (76,94) → (76,119). Comprimento = 13 + 80 + 41 + 84 + 40 + 80 + 25 = **363 m = 81 s** de caminhada. Mais 20 m até o centro da arena.

| Trecho | Distância aprox. | Caminhada | Combate previsto | Intervalo sem luta (caminhada + coleta) |
|---|---|---|---|---|
| Entrada → gatilho do encontro 1 | 55 m | 12 s | n/a | 12 s (aprender movimento e esquiva no Átrio) |
| Encontro 1 → 2 | 34 m | 7,6 s | E1: ~18 s | 8–13 s |
| Encontro 2 → 3 | 38 m | 8,4 s | E2: ~22 s | 8–14 s |
| Encontro 3 → 4 | 32 m | 7,1 s | E3: ~30 s | 7–12 s (passa por CP1) |
| Encontro 4 → 5 | 30 m | 6,7 s | E4: ~25 s | 7–12 s |
| Encontro 5 → 6 | 37 m | 8,1 s | E5: ~30 s | 8–13 s |
| Encontro 6 → 7 | 31 m | 6,9 s | E6: ~32 s | 7–12 s (passa por CP2) |
| Encontro 7 → gatilho da arena | 61 m | 13,6 s | E7: ~28 s | 14–20 s (Antecâmara e CP3) |

Totais **[HIPÓTESE]**: combate 185 s; caminhada 81 s; coleta e respiro extra ~30 s. **Até a porta da arena: ~5 min** no caminho direto. Com os 5 baús e o segredo: +35 s de desvio. Primeira partida com exploração: 7–9 min. Chefe: 2–3 min (item 4.1: 120–180 s). Primeira vitória completa: 8–12 min. Isso cabe na sessão curta do P4 (5 min já rendem um encontro-chefe tentado) e na demo de 30–45 min (Estrada + Cripta).

Retorno depois de morrer (caminhada pura): CP3 → chefe 8 s; CP2 → chefe ~16 s mais a Elite Veloz se ainda viva; CP1 → chefe ~50 s; CP0 → chefe 81 s. O atalho A corta a volta ao portal depois do encontro 5 de ~70 s para ~25 s.

### 7.2 O que ocupa o espaço maior (sem lore)

Com salas de 24–32 m e só 7 encontros, a caminhada vazia seria de cerca de 25 s entre lutas. O espaço é usado assim:

1. **Distância como mecânica.** Atiradores a ±7,5 m do eixo (seção 8) pedem que o herói feche a distância pelo lado; o Cão Veloz (4,8 m/s) pede cobertura em vez de fuga.
2. **Pilares de cobertura** em todas as salas de combate (lista no JSON): bloqueiam flecha, criam cantos para quebrar o cerco dos cães.
3. **Desvios de baú** de 8–12 s cada, sempre depois do combate, para o jogador escolher risco (voltar com a vida baixa) ou ritmo (P1, P4).
4. **Segredo de habilidade** (parede rachada) que dá uso a Investida/Fenda fora do combate.
5. **Atalho A** que recompensa a primeira passagem e respeita o tempo de quem volta.
6. **Corredores de 12 m** como respiro obrigatório (2,7 s), com Checkpoints 1 e 2 dentro deles.
7. **Vistas verticais** dentro dos 8 m visíveis (itens abaixo). A câmera não alcança vistas longas.

| ID | Vista | Local | Descrição para o Art Director |
|---|---|---|---|
| `vista.crypt.pit` | abismo parcial não caminhável | r03, retângulo 66,42 → 74,50 | buraco no chão com andar inferior em ruínas e névoa subindo, legível da câmera 3/4 |
| `vista.crypt.colonnade` | colunata alta decorativa | r06, ao longo da parede oeste (x=-18) | colunas de até 12 m cortadas pelo topo da tela, dão escala sem ocupar chão |
| `vista.crypt.gate` | portão gradeado e luz vazando | r08 norte e C09 | brilho âmbar no fim de C09 anuncia a arena sem mostrá-la |

## 8. Leitura na câmera de 56 m

Retângulo visível (centrado no herói **[HIPÓTESE]**): ±12,4 m em X, ±8,5 m em Z, canto a ~15,0 m. O raio de aggro (círculo) só cabe inteiro na tela se for menor que 8,5 m. Nenhum inimigo cabe nessa condição, então a regra tem que ser de geometria mais regra de IA.

### 8.1 Alcance de aggro contra a área visível

| Inimigo | Aggro | Cabe em X (12,4)? | Cabe em Z (8,5)? | Primeiro dano real | Risco de "ataque fora da tela" |
|---|---|---|---|---|---|
| Sentinela Oca / Arauto | 9 m | sim | excede em 0,5 m | golpe corpo a corpo de ≤ 2 m | nenhum: o ataque ocorre perto do herói |
| Elite Escudada | 10 m | sim | excede 1,5 m | corpo a corpo | nenhum |
| Cão-de-Cinza | 11 m | sim | excede 2,5 m | mordida a 1,5 m, depois de cercar a 3,5–5 m (`13` item 6.1) | acordar fora da tela: sim; atacar: não. Entra na tela em ≥ 0,66 s (2,5 m / 3,8 m/s) antes de cercar |
| Cão Veloz | 12 m | sim por 0,4 m | excede 3,5 m | mordida a 1,5 m | idem; entra na tela em ~0,7 s (3,5 m / 4,8 m/s) |
| Arqueiro Fantasma | **14 m** | **não (excede 1,6 m)** | **não (excede 5,5 m)** | flecha de ~14 m/s, alcance 14 m | **sim**, se nada for feito |
| Guardião | 14 m | n/a | n/a | gatilho de entrada, não aggro | nenhum (ver abaixo) |

### 8.2 Regras para garantir "nenhum inimigo ataca de fora da tela"

R-VIS-1 (regra de IA, pedido ao Tech Lead e ao Data Engineer, **[HIPÓTESE]**): atirador só inicia a mira (Telegraph) se o próprio atirador estiver dentro do retângulo visível do herói reduzido em 1 m (|dx| ≤ 11,4 e |dz| ≤ 7,5). Fora disso fica em Posicionar andando para dentro dele. O retângulo deve vir do frustum da câmera (não de números fixos), para continuar certo se o FOV ou a altura mudarem. Como o retângulo é convexo e a flecha vai ao herói no centro, uma flecha disparada desta posição nunca atravessa a tela vinda de fora. Isto é um atributo novo do `enemy_ai.csv` (coluna sugerida `requireOnScreen`, para o Data Engineer decidir o nome).

R-VIS-2: nenhuma habilidade de chefe começa com o chefe fora da tela. Na fase 1 isso é automático (martelo 3,8 m, Golpe de Escudo 2 m). A Investida só é escolhida com o herói entre 3 e 7,5 m (seção 6.2).

R-VIS-3 (geometria, esta seção): cada espaço de inimigo está posto de modo que, na rota principal, o **primeiro aggro aconteça com o inimigo visível**. Para a chegada ao longo de uma linha, o primeiro aggro ocorre no deslocamento ao longo da linha `d = sqrt(R² − o²)`, onde `o` é a distância do inimigo à linha. O inimigo está visível quando `d` ≤ 12,4 (chegada em X) ou ≤ 8,5 (chegada em Z), e `o` ≤ 8,5 (X) ou ≤ 12,4 (Z). Arqueiros ficam a **o = 7,5 m** da linha de chegada em X: `d = sqrt(14² − 7,5²) = 11,8 m`, dentro de 12,4 com folga de 0,6 m em X e de 1,0 m em Z. Linha de visão: parede bloqueia aggro (um arqueiro atrás da parede de um corredor não acorda).

Resultado por encontro (rota principal, herói centrado):

| Encontro | Inimigo crítico (espaço) | Aggro | Linha | `o` (m) | `d` (m) | Margem em X | Margem em Z | Primeiro a acordar |
|---|---|---|---|---|---|---|---|---|
| 1 | Sentinela (43,21) | 9 | z=13 | 8,0 | 4,1 | 8,3 | 0,5 | Sentinela (40,19), herói em x=33,3 |
| 2 | Cão (87,5) | 11 | z=13 | 8,0 | 7,6 | 4,8 | 0,5 | Cão (84,6), herói em x=75,5 |
| 3 | Sentinela (88,49) | 9 | x=80 | 8,0 | 4,1 | 4,4 | 4,4 | Sentinela (88,49), herói em z=44,9 |
| 3 | Arauto (87,55) | 9 | x=80 | 7,0 | 5,7 | 5,4 | 2,8 | depois da Sentinela |
| 4 | Arqueiro (34,61.5) | 14 | z=54 | 7,5 | 11,8 | 0,6 | 1,0 | herói em x=45,8 |
| 4 | Arqueiro (42,46.5) | 14 | z=54 | 7,5 | 11,8 | 0,6 | 1,0 | herói em x=53,8, na linha de visão da abertura de C04 |
| 5 | Arqueiros (-2,61.5) e (-2,46.5) | 14 | z=54 | 7,5 | 11,8 | 0,6 | 1,0 | herói em x=9,8 |
| 6 | Sentinela (1,100) | 9 | x=-4 | 5,0 | 7,5 | 4,9 | 1,0 | herói em z=92,5 |
| 6 | Elite Escudada (4,99) | 10 | x=-4 | 8,0 | 6,0 | 6,4 | 2,5 | depois da Sentinela |
| 7 | Cão Veloz (45,101) | 12 | z=94 | 7,0 | 9,7 | 2,7 | 1,5 | herói em x=35,3 |
| 7 | Cão (44,102) | 11 | z=94 | 8,0 | 7,6 | 4,8 | 0,5 | herói em x=36,5; o mais cedo é o Cão (41,101), em x=32,5 |

Todas as margens são positivas, então na rota central nenhum inimigo acorda fora da tela. Margens de 0,5 m (Z) são apertadas: o herói que anda rente a uma parede muda `o` e pode acordar o inimigo fora da tela. Para isso valem R-VIS-1 (atiradores) e a tabela de tempos abaixo (melee).

Tempo entre "acordar" e "primeiro dano" (herói parado, pior caso) **[HIPÓTESE]**:

| Inimigo | Acorda a | Chega ao herói | Telegraph | Tempo na tela antes de ferir |
|---|---|---|---|---|
| Cão (em Z, 11 m) | 11 m | cerco a 3,5–5 m em ~1,6 s | agacho 0,3 s | ≥ 1,2 s |
| Cão Veloz (em Z, 12 m) | 12 m | cerco em ~1,5 s | agacho 0,24 s | ≥ 0,9 s |
| Arqueiro | tela (R-VIS-1) | n/a | mira 0,6 s | 0,6 s de mira + ~0,8 s de voo = ≥ 1,4 s |
| Sentinela / Elite Escudada | 9 / 10 m | ~4 s | pelo CSV | ≥ 3 s |

Guardião: usa volume de gatilho (`trigger.arena.start`), não o aggro de 14 m, para a porta fechar e a luta começar com ele já à vista do herói (entrada a ~26 m dele; o Guardião só aparece na tela depois de o herói passar de rz=-9, o que acontece dentro da arena e depois do gatilho). Primeira ação 1,5 s depois do gatilho (item 4.3).

## 9. Hipóteses que precisam de playtest

1. Herói centrado na tela (sem deslocamento do enquadramento) e câmera sem yaw. Se o retângulo for um trapézio por causa da perspectiva (mais largo ao fundo), as margens de Z crescem para cima e diminuem para baixo.
2. Comprimento de corredor de 12 m (e 16 m no atalho). Mais curto deixa o jogo apertado em 24–32 m de sala; mais longo aumenta a caminhada vazia.
3. Tempos de combate por encontro (18–32 s) e o total de ~5 min até a porta (seção 7).
4. Mortos continuam mortos após morrer, fora do chefe.
5. Pilares: diâmetro 2,5 m, altura 4 m, 8 pilares na arena; taxa de Investida que bate (alvo 30–50%).
6. Raio do corpo do Guardião (1,2 m) e distância de seleção da Investida (3–7,5 m).
7. Patrulha a 1,1 m/s (metade da velocidade de perseguição).
8. Baús de elite com `loot.crypt.elite`.
9. Porta da arena fechando atrás do herói.
10. Nível esperado ao chegar ao chefe: 4 (`13` item 7), com XP dos 7 encontros (~12–40 por inimigo); a conferir.

## 10. Perguntas abertas

1. **Tech Lead:** a regra R-VIS-1 (atirador exige estar na tela) é viável com `enemy_ai.csv` e o frustum da câmera do protótipo? Há yaw na câmera?
2. **Data Engineer:** onde colocar posições de espaço (`x,z`) e geometria: em tabela nova (`layouts.csv`/JSON) ou em cena? O bloco JSON abaixo é uma proposta e não impõe formato.
3. **Dono:** inimigos mortos reaparecem depois de voltar ao checkpoint? E a porta do chefe fecha atrás do herói?
4. **Art Director:** o fade de pilar e a altura de 4 m são aceitáveis? A colunata de 12 m é viável no orçamento de malha?
5. **Game Designer (próxima rodada):** se a Investida bater demais, reduzir o bônus (stagger de 2,0 s para 1,5 s) em vez de mexer na geometria?

## 11. Bloco legível por máquina

Proposta de formato para um gerador de cena. Unidades em metros, `rect = [x0, z0, x1, z1]`. IDs são estáveis (não renomear depois de publicados). Posições são `[x, z]`. Os campos `enemyId` e as quantidades `min`/`max` repetem `encounters.csv`; se o CSV mudar, o CSV vale.

```json
{
  "layoutVersion": 1,
  "mapId": "map.act1.crypt",
  "units": "m",
  "origin": "entrance door, south wall of room.crypt.r00_entry",
  "axes": { "x": "screen right", "z": "screen up (north)" },
  "camera": { "heightMeters": 56, "visibleHalfX": 12.4, "visibleHalfZ": 8.5, "centeredOnHero": true },
  "hero": { "speed": 4.5, "spawn": [0, 3], "facing": "+z" },
  "corridorWidth": 6,
  "rooms": [
    { "id": "room.crypt.r00_entry", "rect": [-12, 0, 12, 24], "role": "entry" },
    { "id": "room.crypt.r01_patrol_a", "rect": [24, 0, 52, 28], "role": "combat" },
    { "id": "room.crypt.r02_hounds", "rect": [64, 0, 96, 28], "role": "combat" },
    { "id": "room.crypt.r03_herald", "rect": [64, 40, 96, 68], "role": "combat" },
    { "id": "room.crypt.r04_patrol_b", "rect": [24, 40, 52, 68], "role": "combat" },
    { "id": "room.crypt.r05_firing_line", "rect": [-20, 40, 12, 68], "role": "combat" },
    { "id": "room.crypt.r06_elite_shield", "rect": [-18, 80, 10, 108], "role": "combat" },
    { "id": "room.crypt.r07_elite_swift", "rect": [22, 80, 52, 110], "role": "combat" },
    { "id": "room.crypt.r08_antechamber", "rect": [64, 83, 88, 107], "role": "rest" },
    { "id": "room.crypt.r09_arena", "rect": [56, 119, 96, 159], "role": "boss" },
    { "id": "room.crypt.s01_niche", "rect": [76, -12, 88, 0], "role": "secret" }
  ],
  "corridors": [
    { "id": "cor.crypt.c01", "rect": [12, 10, 24, 16], "from": "room.crypt.r00_entry", "to": "room.crypt.r01_patrol_a" },
    { "id": "cor.crypt.c02", "rect": [52, 10, 64, 16], "from": "room.crypt.r01_patrol_a", "to": "room.crypt.r02_hounds" },
    { "id": "cor.crypt.c03", "rect": [77, 28, 83, 40], "from": "room.crypt.r02_hounds", "to": "room.crypt.r03_herald" },
    { "id": "cor.crypt.c04", "rect": [52, 51, 64, 57], "from": "room.crypt.r03_herald", "to": "room.crypt.r04_patrol_b" },
    { "id": "cor.crypt.c05", "rect": [12, 51, 24, 57], "from": "room.crypt.r04_patrol_b", "to": "room.crypt.r05_firing_line" },
    { "id": "cor.crypt.c06", "rect": [-7, 68, -1, 80], "from": "room.crypt.r05_firing_line", "to": "room.crypt.r06_elite_shield" },
    { "id": "cor.crypt.c07", "rect": [10, 91, 22, 97], "from": "room.crypt.r06_elite_shield", "to": "room.crypt.r07_elite_swift" },
    { "id": "cor.crypt.c08", "rect": [52, 91, 64, 97], "from": "room.crypt.r07_elite_swift", "to": "room.crypt.r08_antechamber" },
    { "id": "cor.crypt.c09", "rect": [73, 107, 79, 119], "from": "room.crypt.r08_antechamber", "to": "room.crypt.r09_arena" },
    { "id": "cor.crypt.sa", "rect": [-3, 24, 3, 40], "from": "room.crypt.r05_firing_line", "to": "room.crypt.r00_entry", "gate": "shortcut.crypt.a" }
  ],
  "route": [[0,0],[0,13],[80,13],[80,54],[-4,54],[-4,94],[76,94],[76,119],[76,139]],
  "encounters": [
    {
      "id": "enc.crypt.patrol_a", "order": 1, "room": "room.crypt.r01_patrol_a",
      "groups": [
        { "enemyId": "enemy.hollow_sentinel", "min": 2, "max": 3, "slots": [[40,19],[43,21],[43,17]], "patrol": [[40,19],[47,19]] }
      ]
    },
    {
      "id": "enc.crypt.hounds", "order": 2, "room": "room.crypt.r02_hounds",
      "groups": [
        { "enemyId": "enemy.ash_hound", "min": 3, "max": 5, "slots": [[84,6],[86,7],[87,5],[89,9],[91,7]] }
      ]
    },
    {
      "id": "enc.crypt.herald", "order": 3, "room": "room.crypt.r03_herald",
      "groups": [
        { "enemyId": "enemy.stone_herald", "min": 1, "max": 1, "slots": [[87,55]] },
        { "enemyId": "enemy.hollow_sentinel", "min": 1, "max": 2, "slots": [[88,49],[91,53]] }
      ]
    },
    {
      "id": "enc.crypt.patrol_b", "order": 4, "room": "room.crypt.r04_patrol_b",
      "groups": [
        { "enemyId": "enemy.hollow_sentinel", "min": 1, "max": 2, "slots": [[38,53],[36,56]], "patrol": [[36,56],[42,53]] },
        { "enemyId": "enemy.ghost_archer", "min": 1, "max": 2, "slots": [[34,61.5],[42,46.5]], "requireOnScreen": true }
      ]
    },
    {
      "id": "enc.crypt.firing_line", "order": 5, "room": "room.crypt.r05_firing_line",
      "groups": [
        { "enemyId": "enemy.hollow_sentinel", "min": 1, "max": 2, "slots": [[-6,55],[-8,53]] },
        { "enemyId": "enemy.ghost_archer", "min": 2, "max": 3, "slots": [[-2,61.5],[-2,46.5],[-12,61.5]], "requireOnScreen": true }
      ]
    },
    {
      "id": "enc.crypt.elite_shield", "order": 6, "room": "room.crypt.r06_elite_shield",
      "groups": [
        { "enemyId": "enemy.shielded_sentinel", "min": 1, "max": 1, "slots": [[4,99]] },
        { "enemyId": "enemy.hollow_sentinel", "min": 1, "max": 2, "slots": [[1,100],[7,102]] }
      ]
    },
    {
      "id": "enc.crypt.elite_swift", "order": 7, "room": "room.crypt.r07_elite_swift",
      "groups": [
        { "enemyId": "enemy.swift_ash_hound", "min": 1, "max": 1, "slots": [[45,101]] },
        { "enemyId": "enemy.ash_hound", "min": 2, "max": 3, "slots": [[41,101],[47,99],[44,102]] }
      ]
    },
    {
      "id": "enc.crypt.guardian", "order": 8, "room": "room.crypt.r09_arena", "isBoss": true,
      "groups": [
        { "enemyId": "enemy.crypt_guardian", "min": 1, "max": 1, "slots": [[76,147]], "facing": "-z" }
      ],
      "trigger": { "rect": [71, 121, 81, 125] },
      "respawn": [76, 121],
      "summonMarks": [[66,137],[86,137]]
    }
  ],
  "checkpoints": [
    { "id": "cp.crypt.0", "pos": [0, 8], "room": "room.crypt.r00_entry" },
    { "id": "cp.crypt.1", "pos": [58, 54], "room": "cor.crypt.c04" },
    { "id": "cp.crypt.2", "pos": [16, 94], "room": "cor.crypt.c07" },
    { "id": "cp.crypt.3", "pos": [76, 92], "room": "room.crypt.r08_antechamber" }
  ],
  "portals": [
    { "id": "portal.crypt.entry", "pos": [-8, 6], "target": "area.refuge", "active": "always" },
    { "id": "portal.crypt.exit", "pos": [76, 149], "target": "area.refuge", "active": "after enc.crypt.guardian" }
  ],
  "markers": [
    { "id": "marker.crypt.return", "pos": [76, 139], "active": "after enc.crypt.guardian" }
  ],
  "chests": [
    { "id": "chest.crypt.01", "pos": [50, 3], "lootTable": "loot.crypt.area" },
    { "id": "chest.crypt.02", "pos": [82, -8], "lootTable": "loot.crypt.area", "secret": "secret.crypt.cracked_wall" },
    { "id": "chest.crypt.03", "pos": [26, 66], "lootTable": "loot.crypt.area" },
    { "id": "chest.crypt.04", "pos": [-15, 106], "lootTable": "loot.crypt.elite" },
    { "id": "chest.crypt.05", "pos": [50, 108], "lootTable": "loot.crypt.elite" }
  ],
  "secrets": [
    { "id": "secret.crypt.cracked_wall", "rect": [80, -0.5, 83, 0.5], "opensWith": ["skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash"], "leadsTo": "room.crypt.s01_niche" }
  ],
  "gates": [
    { "id": "shortcut.crypt.a", "pos": [0, 40], "width": 6, "opensFrom": "room.crypt.r05_firing_line" },
    { "id": "gate.crypt.arena", "pos": [76, 119.5], "width": 6, "closesOn": "trigger.arena.start" }
  ],
  "pillars": [
    { "id": "pil.r01.1", "pos": [32, 7], "radius": 1.0, "height": 4 },
    { "id": "pil.r01.2", "pos": [32, 19], "radius": 1.0, "height": 4 },
    { "id": "pil.r01.3", "pos": [46, 8], "radius": 1.0, "height": 4 },
    { "id": "pil.r02.1", "pos": [72, 7], "radius": 1.0, "height": 4 },
    { "id": "pil.r02.2", "pos": [72, 21], "radius": 1.0, "height": 4 },
    { "id": "pil.r02.3", "pos": [90, 21], "radius": 1.0, "height": 4 },
    { "id": "pil.r03.1", "pos": [72, 61], "radius": 1.0, "height": 4 },
    { "id": "pil.r03.2", "pos": [84, 63], "radius": 1.0, "height": 4 },
    { "id": "pil.r04.1", "pos": [30, 48], "radius": 1.0, "height": 4 },
    { "id": "pil.r04.2", "pos": [30, 60], "radius": 1.0, "height": 4 },
    { "id": "pil.r05.1", "pos": [4, 49], "radius": 1.0, "height": 4 },
    { "id": "pil.r05.2", "pos": [4, 59], "radius": 1.0, "height": 4 },
    { "id": "pil.r05.3", "pos": [-8, 47], "radius": 1.0, "height": 4 },
    { "id": "pil.r05.4", "pos": [-8, 61], "radius": 1.0, "height": 4 },
    { "id": "pil.r06.1", "pos": [-12, 88], "radius": 1.0, "height": 4 },
    { "id": "pil.r06.2", "pos": [-12, 100], "radius": 1.0, "height": 4 },
    { "id": "pil.r07.1", "pos": [34, 88], "radius": 1.0, "height": 4 },
    { "id": "pil.r07.2", "pos": [34, 100], "radius": 1.0, "height": 4 },
    { "id": "pil.r07.3", "pos": [48, 88], "radius": 1.0, "height": 4 },
    { "id": "pil.r08.1", "pos": [68, 88], "radius": 1.0, "height": 4 },
    { "id": "pil.r08.2", "pos": [84, 88], "radius": 1.0, "height": 4 },
    { "id": "pil.r08.3", "pos": [68, 102], "radius": 1.0, "height": 4 },
    { "id": "pil.r08.4", "pos": [84, 102], "radius": 1.0, "height": 4 },
    { "id": "pil.arena.1", "pos": [70, 133], "radius": 1.25, "height": 4 },
    { "id": "pil.arena.2", "pos": [82, 133], "radius": 1.25, "height": 4 },
    { "id": "pil.arena.3", "pos": [70, 145], "radius": 1.25, "height": 4 },
    { "id": "pil.arena.4", "pos": [82, 145], "radius": 1.25, "height": 4 },
    { "id": "pil.arena.5", "pos": [62, 139], "radius": 1.25, "height": 4 },
    { "id": "pil.arena.6", "pos": [90, 139], "radius": 1.25, "height": 4 },
    { "id": "pil.arena.7", "pos": [76, 154], "radius": 1.25, "height": 4 },
    { "id": "pil.arena.8", "pos": [76, 126], "radius": 1.25, "height": 4 }
  ],
  "vistas": [
    { "id": "vista.crypt.pit", "rect": [66, 42, 74, 50], "walkable": false },
    { "id": "vista.crypt.colonnade", "rect": [-18, 82, -16, 106], "walkable": false },
    { "id": "vista.crypt.gate", "rect": [73, 104, 79, 107], "walkable": false }
  ],
  "arenaCharge": { "chargeLengthMeters": 7, "stopDistanceToPillarCenter": 9.45, "selectDistanceMeters": [3, 7.5], "wallStaggerSeconds": 2.0 }
}
```

Observação para o gerador: os espaços de inimigo são `max` posições; o gerador instancia os `n` primeiros, onde `n` sai do sorteio do CSV. Posições de patrulha são waypoints em ordem, em ciclo de ida e volta.
