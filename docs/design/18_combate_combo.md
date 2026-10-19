# 18. Combate com combo, ataque forte e defesa (Guerreiro, Arqueiro e Mago)

Data: 17/10/2026. Autor: Game Designer. Origem: decisões do dono depois de jogar o build e decisões do orquestrador (ver o pedido). Este documento não altera `docs/16` nem os CSV: as linhas dos CSV aparecem aqui prontas para o Data Engineer aplicar (seção 2).

Tudo marcado `[HIPÓTESE]` precisa de playtest. Nenhum número fica no código: tudo vira linha de CSV.

## 0. Resumo

- Clique esquerdo: combo de 3 golpes (clicar de novo dentro da janela). Segurar o esquerdo: ataque forte carregado. Direito: defesa (segurar), igual para as 3 classes. Q, E e R: habilidades (a Investida do Guerreiro vai para o Q).
- Cada classe tem a mesma estrutura (3 leves, 1 forte, 1 defesa, 3 habilidades), mas com **verbo diferente** (pilar "Build com identidade"): o Guerreiro troca risco por Ímpeto e atordoa com a defesa perfeita; o Arqueiro troca Foco por distância e perfuração; o Mago troca Mana por área e usa a defesa como gasto de Mana.
- Pilares atendidos: "Conquistar pela ação" (timing da janela do combo, da defesa perfeita e da carga) e "Build com identidade" (kit básico distinto por classe). Nada aqui toca o idle (seção 4.1): o simulador continua usando só o Corte de Ferro.

### 0.1 Inspiração (tabela obrigatória)

| No jogo de referência | No nosso | Por quê |
|---|---|---|
| Dark Souls e Sekiro: golpe leve encadeado, bloqueio segurado, aparo no instante certo | Combo de 3 golpes, defesa segurada, defesa perfeita só nos primeiros 0,2 s depois de apertar (não ao segurar desde antes) | O jogador precisa ler o telegraph de 0,7 a 1,2 s e apertar no tempo, em vez de ficar sempre com a guarda erguida |
| Souls: o aparo só aturde quem pode ser aturdido | Contra alvo imune ao atordoamento (elite, Arauto, chefe), a defesa perfeita aplica 1 acúmulo de Quebra de Guarda (regra que já existe) | Nenhuma defesa perfeita fica sem efeito; com 3 acertos perfeitos o chefe quebra. É a decisão nova: "arrisco o aparo no martelo do Guardião?" |
| ARPGs de PC (Diablo, Path of Exile): botão direito vira habilidade principal | Botão direito vira defesa; as habilidades descem para Q, E, R | Decisão do dono; liberta a mão do mouse para mirar e proteger |
| Hades e Diablo 4: ataque carregado com custo de mobilidade | Carregar reduz a velocidade de movimento e pode ser cancelado de graça pela esquiva ou pela defesa | Carregar é uma aposta de posição, não um botão de dano grátis |

## 1. Regras de entrada

### 1.1 Mapa de teclas (padrão, tudo remapeável)

| Entrada | Ação | Observação |
|---|---|---|
| Botão esquerdo, clique | Golpe leve (combo) | Decidido ao soltar, se segurou menos de `heavy_hold_threshold` |
| Botão esquerdo, segurar | Ataque forte | Começa a carregar em `heavy_hold_threshold` (0,35 s) |
| Botão direito, segurar | Defesa | Igual para as 3 classes; a mira continua no cursor |
| Q, E, R | Habilidades 1, 2, 3 | Guerreiro: Q Investida, E Fenda de Pedra, R Escudada |
| Espaço | Esquiva | Inalterada (docs/13 item 1) |
| 1, 2 | Poções | Inalteradas |

Regra de barra do plano (4 habilidades no demo): esquerdo + Q + E + R = 4. Arqueiro e Mago ficam com o R vazio (reservado para o primeiro livro).

### 1.2 Chaves novas de `rules.csv` (globais)

| Chave | Valor | Intenção |
|---|---|---|
| `combo_window` | 0,40 s `[HIPÓTESE]` | Tempo depois do fim da recuperação de um golpe em que um clique ainda continua o combo. Folgada de propósito: o combo deve fluir sem exigir ritmo de jogo musical |
| `combo_window_after_dodge` | 0,30 s `[HIPÓTESE]` | Janela que reabre ao fim da esquiva. Premia "esquivar e voltar ao combo" sem perder o 2º/3º golpe |
| `attack_buffer` | 0,15 s `[HIPÓTESE]` | Um clique entra na fila se chegar nos últimos 0,15 s da recuperação (ou depois). Clique mais cedo é ignorado (evita golpe acidental ao martelar) |
| `heavy_hold_threshold` | 0,35 s | Decisão do orquestrador. Abaixo disso é clique leve |
| `light_windup_credit_max` | 0,7 `[HIPÓTESE]` | O tempo que o botão ficou apertado desconta da preparação do golpe leve, até 70% dela. Sem isso, decidir "clique ou segurar" só ao soltar adicionaria ~0,1 s de atraso em todo golpe |
| `guard_lower_time` | 0,10 s `[HIPÓTESE]` | Depois de soltar a defesa, o herói não pode atacar por 0,10 s (impede alternar guarda e golpe sem custo) |
| `dash_shot_range` | 1000 uu `[HIPÓTESE]` | Alcance do tiro de uma habilidade `dash` com tag `projectile` (Salto do Arqueiro) |

### 1.3 Máquina de estados do jogador (quem pode virar o quê)

| Estado atual | Entrada | Resultado |
|---|---|---|
| Livre | Clique | Golpe 1 (índice 0) |
| Livre | Segurar esquerdo ≥ 0,35 s | Carregando |
| Livre | Direito | Defendendo |
| Golpe N, preparação ou impacto | Qualquer botão (exceto esquiva) | Ignorado (compromisso do golpe, igual docs/13) |
| Golpe N, recuperação | Clique nos últimos `attack_buffer` s | Fila: golpe N+1 começa no fim da recuperação |
| Golpe N, recuperação | Esquiva, na metade final (`dodge_cancel_recovery_fraction`, já existe = 0,5) | Cancela a recuperação; o combo guarda o índice por `combo_window_after_dodge` |
| Golpe N, recuperação | Q/E/R ou direito, na metade final | Cancela a recuperação; **o combo zera** |
| Depois do fim da recuperação | Clique em até `combo_window` | Golpe N+1. Depois do 3º golpe o índice volta a 0 e não há janela |
| Depois do fim da recuperação | Nada em `combo_window` | Índice volta a 0 |
| Carregando | Soltar | Golpe forte com o multiplicador da carga (seção 1.4) |
| Carregando | Chegar ao máximo da carga | Solta sozinho (decisão do orquestrador) |
| Carregando | Esquiva, direito, Q/E/R | Cancela a carga sem custo e sem recarga. **Desvia de docs/13** ("esquiva nunca na preparação"): carregar não é a preparação do golpe, a preparação real começa ao soltar. `[HIPÓTESE]` |
| Golpe forte, recuperação | Esquiva na metade final | Cancela a recuperação (igual ao leve) |
| Defendendo | Esquiva | Cancela a defesa |
| Defendendo | Clique ou Q/E/R | Ignorado enquanto segura (o herói não ataca); vale depois de `guard_lower_time` |
| Qualquer | Atordoamento (`effect.stun` ou stagger) | Cancela tudo e zera o combo |
| Qualquer | Dano comum | Não interrompe (o herói não leva stagger de golpe comum no protótipo) |

Mouse-up, 60 Hz e determinismo: o core mede janelas e carga em **ticks** de 1/60 s (valores em segundos arredondados para cima). O Frontend manda eventos de apertar e soltar com o número do tick, nunca tempo em float.

### 1.4 Ataque forte: carga e multiplicador

- A carga começa em `heavy_hold_threshold` e dura `heavyChargeTime` (por classe, tabela `basic_kits.csv`, seção 4.6).
- Progresso `p = clamp((tempo_apertado - 0,35) / heavyChargeTime, 0, 1)`. Multiplicador de dano do golpe = `1 + (heavyMaxMult - 1) * p`, aplicado como `more` naquele acerto (conta linear, sem `pow`).
- O coeficiente da linha do golpe forte é o dano com carga mínima. Soltar com carga mínima sempre vale mais que um leve (o jogador não é punido por segurar pouco).
- Enquanto carrega, o herói leva o efeito de movimento lento da classe (`chargeEffect`, reaplicado a cada tick). Custo de recurso: cobrado ao soltar; se não houver recurso no limiar de 0,35 s, o botão solta como golpe leve (nada de carga vazia).
- Máximo de carga = auto-soltura. O jogador não "segura no máximo" (decisão do orquestrador): carregar demais é decisão, não vantagem.

## 2. Golpes por classe e dados

Legenda de tempo: preparação / impacto / recuperação, em segundos. O golpe acerta em preparação + impacto. Coeficiente é o do rank 1. Dano base: arma (`scalesWithWeapon`) para Guerreiro e Arqueiro; fixo por elemento para o Mago (sem escala por arma; a progressão vem de afixos de dano, ver Q18-1).

### 2.1 Guerreiro (Ímpeto)

| Slot | ID | Nome | Coef. R1 | Prep / imp / rec (total) | Alcance / forma | Custo | Recarga |
|---|---|---|---|---|---|---|---|
| Clique 1 | `skill.warrior.iron_cut` (existente, sem mudança) | Corte de Ferro | 1,0 | 0,15 / 0,10 / 0,20 (0,45) | 180 uu, cone | 0 | 0 |
| Clique 2 | `skill.warrior.combo_2` | Golpe de Volta | 1,1 | 0,12 / 0,10 / 0,22 (0,44) | 190 uu, cone 140° | 0 | 0 |
| Clique 3 | `skill.warrior.combo_3` | Golpe de Fecho | 1,7 | 0,22 / 0,12 / 0,40 (0,74) | 210 uu, cone 160°, empurra 120 uu | 0 | 0 |
| Segurar | `skill.warrior.heavy_slash` | Golpe Pesado | 1,8 (carga mín.) a 3,6 (máx.) | 0,10 / 0,12 / 0,50 (0,72), depois de soltar | 220 uu, cone 150°, empurra 160 uu, +1 Quebra de Guarda | 0 | 0 |
| Direito | (kit) `effect.guarding.warrior` | Defesa com Escudo | n/a | n/a | frente 120° | 0 | 0 |
| Q | `skill.warrior.charge` (existente) | Investida | 1,2 | 0,15 / 0,20 / 0,30 | 600 uu, avanço | 20 | 6 |
| E | `skill.warrior.stone_rift` (existente) | Fenda de Pedra | 0,9 | 0,35 / 0,15 / 0,40 | 450 uu, cone | 40 | 5 |
| R | `skill.warrior.shield_bash` (existente) | Escudada | 1,3 | 0,25 / 0,10 / 0,30 | 200 uu | 25 | 4 |

Intenção dos números `[HIPÓTESE]`:

- **DPS do combo ≈ DPS do Corte de Ferro repetido.** Combo: coeficientes 1,0 + 1,1 + 1,7 = 3,8 em 1,63 s = 2,33 por segundo. Corte de Ferro sozinho: 1,0 em 0,45 s = 2,22 por segundo (+5%). Assim a calibração do idle (`manual_estimate`) continua válida e o combo ganha valor pelo empurrão e pelo ritmo, não por DPS.
- O 3º golpe concentra o dano (1,7) e tem recuperação longa (0,40 s): o jogador escolhe se "fecha" o combo perto de um inimigo ou se esquiva antes dele.
- O golpe forte tem DPS menor que o combo (carga mínima: 1,8 em 1,07 s = 1,7 por segundo; carga máxima: 3,6 em 1,97 s = 1,8 por segundo) e paga com o que o combo não dá: Quebra de Guarda, cone maior e empurrão 160 uu. É a ferramenta contra a Sentinela com escudo e contra elite.
- Ímpeto: não há custo nos golpes básicos. O ganho é o `resourceOnHit` (10) e `resourceOnBlock` (15) já existentes; golpes fortes e leves dão o mesmo por acerto.
- Empurrão em unidades de mundo (uu, 1 uu = 1 cm): comuns sofrem o valor cheio, elites 30%, chefes 0 (docs/03 seção 6; fator de elite `[HIPÓTESE]`).

### 2.2 Arqueiro (Foco)

| Slot | ID | Nome | Coef. R1 | Prep / imp / rec (total) | Alcance / forma | Custo | Recarga |
|---|---|---|---|---|---|---|---|
| Clique 1 e 2 | `skill.archer.quick_shot` | Disparo Reto | 0,85 | 0,10 / 0,05 / 0,20 (0,35) | 1300 uu, projétil 2400 uu/s | 0 | 0 |
| Clique 3 | `skill.archer.fan_shot` | Flechas em Leque | 0,65 por flecha (3 flechas) | 0,18 / 0,05 / 0,32 (0,55) | 1100 uu, leque de 28° | 0 | 0 |
| Segurar | `skill.archer.piercing_shot` | Tiro Perfurante | 1,5 (carga mín.) a 3,0 (máx.) | 0,06 / 0,04 / 0,35 (0,45), depois de soltar | 1500 uu, projétil 3200 uu/s, atravessa tudo | 12 Foco | 0 |
| Direito | (kit) `effect.guarding.archer` | Guarda do Arco | n/a | n/a | frente 90°, no máximo 1,2 s, recarga 1,0 s | 0 | n/a |
| Q | `skill.archer.back_leap` | Salto para Trás | 1,2 | 0,05 / 0,25 / 0,20 (0,50) | pula 450 uu para trás e atira em `dash_shot_range`; empurra 120 uu | 15 Foco | 6 |
| E | `skill.archer.arrow_rain` | Chuva de Flechas | 1,8 | 0,25 / 0,70 / 0,25 (1,20) | área de raio 300 uu no cursor (até 1100 uu do herói) | 35 Foco | 8 |

Intenção `[HIPÓTESE]`:

- Foco: 100 máximo, regeneração de 8 por segundo parado e 2,4 em movimento (`regenMultWhileMoving` 0,3). Ou seja, atirar parado reabastece Q e E; fugir cobra o preço. Os disparos básicos são grátis para que o clique nunca fique "sem munição".
- Leque: três flechas a 0,65 = 1,95 de coeficiente se as três acertarem, contra 0,85 de um disparo reto. Só acerta as três quando o alvo está perto (a 190 uu do herói, a separação lateral das flechas já passa de 40 uu) ou quando há grupo. É a recompensa por encurtar a distância (risco) ou por mirar em grupo.
- Perfurante: valor está em fileira de inimigos, não em dano individual (carga máxima: 3,0 em 1,6 s = 1,9 por segundo no alvo único, o mais baixo dos básicos).
- Guarda curta: o arco reduz 30% (contra 65% do escudo), anda a 65%, e acaba sozinha em 1,2 s com 1,0 s de espera. É uma ferramenta para absorver um golpe, não para ficar parado.
- Salto: sem invulnerabilidade (diferente da esquiva) e com 6 s de recarga; o jogador troca 15 de Foco por distância e um tiro de afastamento.
- Chuva: acerta uma vez, no impacto, 0,70 s depois da preparação. O inimigo comum que anda para fora da zona (o círculo mostra a área) escapa, o parado ou preso em corredor não. Uma zona de 3 s com vários golpes pede uma coluna nova (pergunta Q18-3).

### 2.3 Mago (Mana)

| Slot | ID | Nome | Coef. R1 | Prep / imp / rec (total) | Alcance / forma | Custo | Recarga |
|---|---|---|---|---|---|---|---|
| Clique 1 e 2 | `skill.mage.arcane_dart` | Dardo Arcano | 1,0 (base 8 raio) | 0,12 / 0,06 / 0,22 (0,40) | 1200 uu, projétil 2000 uu/s | 4 Mana | 0 |
| Clique 3 | `skill.mage.arcane_orb` | Orbe Arcano | 1,4 (base 11 raio) | 0,20 / 0,08 / 0,38 (0,66) | 1000 uu, projétil 1300 uu/s, explode raio 130 uu, empurra 60 uu | 8 Mana | 0 |
| Segurar | `skill.mage.fireball` | Bola de Fogo | 1,0 (base 20 fogo, carga mín.) a 2,0 (máx.) | 0,10 / 0,06 / 0,45 (0,61), depois de soltar | 1300 uu, projétil 1100 uu/s, explode raio 220 uu, empurra 80 uu | 18 Mana | 0 |
| Direito | (kit) `effect.guarding.mage` | Barreira Arcana | n/a | n/a | 360° (cúpula) | gasta 1,0 Mana por ponto de dano evitado | n/a |
| Q | `skill.mage.frost_nova` | Nova de Gelo | 1,0 (base 12 gelo) | 0,25 / 0,08 / 0,35 (0,68) | raio 340 uu em volta do herói, empurra 80 uu, `effect.chill` | 25 Mana | 7 |
| E | `skill.mage.arcane_ray` | Raio Arcano | 1,0 (base 26 raio) | 0,35 / 0,05 / 0,40 (0,80) | linha de 900 uu, instantâneo, atravessa tudo | 30 Mana | 6 |

Intenção `[HIPÓTESE]`:

- Mana: 150 máximo, regeneração constante de 5 por segundo (plano: "regeneração constante, reserva alta"). Combo completo: 4 + 4 + 8 = 16 de Mana em 1,46 s, ou seja 11 por segundo contra 5 de regeneração: dá cerca de 25 s de combo contínuo antes de o Mago cair no ritmo da regeneração (um Dardo a cada 0,8 s). Q e E e a barreira disputam a mesma Mana.
- DPS do combo do Mago ≈ 21,5 por segundo (8 + 8 + 15,4 em 1,46 s), na faixa do Guerreiro (≈ 21 por segundo com arma de 9), mas com alcance e sem escudo.
- Fogo carregado: carga mínima (20 em área, ≈ 1,0 s de ciclo) rende mais que um Dardo e menos que o combo; carga máxima (40, raio 220 uu) é a resposta a grupo. O fogo usa a paleta de fogo vermelho-laranja aprovada.
- Dardo e Orbe são elétricos (tipo `lightning` na regra) com estética de arcano: o jogo ainda não tem dano arcano. Se o dono quiser o tipo arcano, vira trabalho do Backend (novo tipo de dano, resistência e paleta).
- E é o Raio Arcano (escolha do Game Designer): linha instantânea que atravessa tudo, parecida em geometria com o Tiro Perfurante, mas com preparação de 0,35 s visível, custo 30 e recarga 6, enquanto o Perfurante é grátis em recarga e custa Foco. A identidade é: o Arqueiro carrega, o Mago agenda.

### 2.4 Defesa (direito) por classe

| Classe | Redução de dano | Velocidade ao defender | Área | Limite | Defesa perfeita | Ganho |
|---|---|---|---|---|---|---|
| Guerreiro | -65% `[HIPÓTESE]` | -60% (180 uu/s; a Sentinela anda a 220) | frente 120° | ilimitado | 0,2 s depois de apertar, re-liberada só 0,8 s depois do último aperto | +15 Ímpeto por bloqueio; +25 por perfeita |
| Arqueiro | -30% `[HIPÓTESE]` | -35% | frente 90° | 1,2 s, depois 1,0 s de espera | nenhuma | nenhum |
| Mago | -50% `[HIPÓTESE]` | -50% | 360° | só enquanto houver Mana (1,0 por ponto evitado) | nenhuma | nenhum |

**Defesa perfeita do Guerreiro** (primeiros 0,2 s `[HIPÓTESE]`, faixa de teste 0,15 a 0,30 s):

1. O golpe que chegar nesse intervalo causa **0 de dano** (qualquer atacante, corpo a corpo ou projétil).
2. Se o atacante for corpo a corpo (tag `melee` na habilidade que acertou): aplica `effect.stun` e `effect.guard_break`. Alvos imunes ao atordoamento (elite, Arauto, chefe) ignoram o atordoamento pela regra que já existe e **recebem 1 acúmulo de Quebra de Guarda**. Em alvo comum, o jogador ganha as duas coisas.
3. Projétil: 0 de dano, sem atordoamento; o ganho de Ímpeto (+25) vale igual.
4. O ganho de Ímpeto da perfeita substitui o do bloqueio comum (não soma).

Por que apertar e não segurar: se a janela valesse "enquanto a guarda estiver erguida", segurar sempre seria a melhor jogada e a defesa perfeita viraria o estado padrão. Com 0,2 s depois do aperto, o jogador lê o telegraph de 0,7 a 1,2 s e aperta perto do impacto. Se errar, ainda recebe a redução normal (a perfeita é um bônus, não um risco).

## 3. Defesa como efeito (decisão do Game Designer)

- A redução e a lentidão são efeitos de `effects.csv` (`effect.guarding.*`, duração curta, reaplicados a cada tick enquanto o botão está apertado). O core já aplica efeitos e modificadores. Ao soltar, o efeito some em até 0,1 s: aceito como margem de perdão.
- O que os efeitos não expressam e vai para `basic_kits.csv` (seção 4.6): arco da defesa, janela perfeita, limite de tempo, dreno de Mana, efeitos da perfeita.
- **Arco: só a frente, 120° (Guerreiro) e 90° (Arqueiro); 360° só o Mago.** Motivos: (1) com câmera fixa e mira no cursor, a frente é uma decisão de posição; uma defesa em 360° faria o Cão-de-Cinza (que cerca) e o escudo frontal do Guardião (que só cai por trás) deixarem de importar; (2) a cúpula do Mago é a característica dele, e só faz sentido se as outras não forem 360°; (3) o custo é um teste de ângulo no momento do dano, que o core já faz para o escudo de inimigos (`shieldArcDegrees`).
- **Plano B sem código novo:** se o Backend não entregar o teste de ângulo na etapa, o protótipo roda com `guardArc = 360` em todas as classes (mesmos números). Ajustar o arco depois é só mudar o dado.

## 4. Dados

### 4.1 `skills.csv`

Passo 0 (mecânico, Data Engineer): acrescentar ao cabeçalho a coluna opcional `pierce` (inteiro, 0 ou vazio = nenhuma perfuração, 99 = atravessa todos) como **última** coluna e uma vírgula final em cada uma das 11 linhas existentes. As colunas opcionais já têm esse caminho no parser (`optionalColumns`).

Linhas a acrescentar (38 campos cada, ordem do cabeçalho com `pierce` no fim):

```csv
skill.warrior.combo_2,class.warrior,,attack|melee|physical,cone,true,,,,,1.1,1.2,1.3,0,0,0.12,0.1,0.22,190,120,1,,,false,,,,,,,,1,140,,,,,
skill.warrior.combo_3,class.warrior,,attack|melee|physical,cone,true,,,,,1.7,1.85,2,0,0,0.22,0.12,0.4,210,130,1,,,false,,,,,,,,1,160,120,,,,
skill.warrior.heavy_slash,class.warrior,,attack|melee|physical,cone,true,,,,,1.8,2,2.2,0,0,0.1,0.12,0.5,220,140,1,effect.guard_break,,false,,,,,,,,1,150,160,,,,
skill.archer.quick_shot,class.archer,,attack|projectile|physical,projectile,true,,,,,0.85,0.95,1.05,0,0,0.1,0.05,0.2,1300,,1,,,false,,,,,,,,1,,,2400,,,
skill.archer.fan_shot,class.archer,,attack|projectile|physical,projectile,true,,,,,0.65,0.7,0.75,0,0,0.18,0.05,0.32,1100,,3,,,false,,,,,,,,1,28,,2400,,,
skill.archer.piercing_shot,class.archer,,attack|projectile|physical,projectile,true,,,,,1.5,1.65,1.8,12,0,0.06,0.04,0.35,1500,,1,,,false,,,,,,,,1,,,3200,,,99
skill.archer.back_leap,class.archer,,attack|projectile|physical,dash,true,,,,,1.2,1.3,1.4,15,6,0.05,0.25,0.2,450,,1,,,false,,,,,,,,2,,120,2400,,,
skill.archer.arrow_rain,class.archer,,attack|projectile|area|physical,area,true,,,,,1.8,2,2.2,35,8,0.25,0.7,0.25,1100,300,1,,,false,,,,,,,,3,,,,,,
skill.mage.arcane_dart,class.mage,,spell|projectile|lightning,projectile,false,,,,8,1,1.1,1.2,4,0,0.12,0.06,0.22,1200,,1,,,false,,,,,,,,1,,,2000,,,
skill.mage.arcane_orb,class.mage,,spell|projectile|area|lightning,projectile,false,,,,11,1.4,1.55,1.7,8,0,0.2,0.08,0.38,1000,130,1,,,false,,,,,,,,1,,60,1300,,,
skill.mage.fireball,class.mage,,spell|projectile|area|fire,projectile,false,,20,,,1,1.15,1.3,18,0,0.1,0.06,0.45,1300,220,1,,,false,,,,,,,,1,,80,1100,,,
skill.mage.frost_nova,class.mage,,spell|area|cold,area,false,,,12,,1,1.15,1.3,25,7,0.25,0.08,0.35,0,340,1,effect.chill,,false,,,,,,,,2,,80,,,,
skill.mage.arcane_ray,class.mage,,spell|projectile|lightning,projectile,false,,,,26,1,1.1,1.2,30,6,0.35,0.05,0.4,900,,1,,,false,,,,,,,,3,,,9000,,,99
```

Conferência de campos (para o Data Engineer): entre `false` (idleSupported) e o `unlockLevel` há 7 campos vazios (idle) e o `unlockLevel` fica no campo 32; `coneAngle` = 33, `knockback` = 34, `projectileSpeed` = 35, `idleCalibration` = 36, `wallStaggerSeconds` = 37, `pierce` = 38. `tools/dados/validate_data.py` deve checar a contagem.

Escolhas de dado explicadas:

- `idleSupported=false` em todas. O idle continua usando o Corte de Ferro (único golpe básico com `IdleProfile`); os golpes de combo, forte e todas as habilidades de Arqueiro e Mago não têm perfil e não precisam de um no protótipo. Arqueiro e Mago ficam, por isso, **sem expedição** (RF-43 já bloqueia habilidade sem perfil). Pergunta Q18-2.
- `unlockLevel` 1 para o kit básico; Q em 2 e E em 3 (espelha Investida 2 e Fenda 3 do Guerreiro).
- `skill.warrior.iron_cut` não muda. Observação: `coneAngle` está vazio no CSV atual; o Frontend usa o valor padrão do cone. Sugestão ao Data Engineer: 150.
- `coefficientRank2/3` seguem o padrão do Guerreiro (+10% por rank).
- `scalesWithWeapon=true` no Arqueiro: precisa de arco equipado (seção 4.7). Sem arma, o core usa `unarmed_weapon_damage_physical` (3) e o dano cai a um terço.
- `back_leap`: `range` = 450 é o pulo; o tiro no pico usa `dash_shot_range`. `arrow_rain` e `frost_nova`: `impact` é o atraso até acertar (a Chuva 0,70 s).

### 4.2 `effects.csv`

```csv
effect.guarding.warrior,0.1,0,refresh,1,,,,,damage_taken:more:-0.65|move_speed:more:-0.6,0,none,1,0,,false
effect.guarding.archer,0.1,0,refresh,1,,,,,damage_taken:more:-0.3|move_speed:more:-0.35,0,none,1,0,,false
effect.guarding.mage,0.1,0,refresh,1,,,,,damage_taken:more:-0.5|move_speed:more:-0.5,0,none,1,0,,false
effect.charging.heavy,0.1,0,refresh,1,,,,,move_speed:more:-0.5,0,none,1,0,,false
effect.charging.archer,0.1,0,refresh,1,,,,,move_speed:more:-0.3,0,none,1,0,,false
effect.chill,3,0,refresh,1,,,,,move_speed:more:-0.4,0,none,1,0,,false
```

- `effect.stun` e `effect.guard_break` já existem e são reaproveitados (defesa perfeita, golpe forte do Guerreiro).
- Redução e lentidão usam o mesmo padrão de sinal de `effect.stun` (`move_speed:more:-1`) e de `effect.guard_break` (`damage_taken`).
- `effect.chill` é o único efeito de controle novo: -40% de velocidade por 3 s (a Nova de Gelo fecha o espaço do Mago; é o oposto do atordoamento: o inimigo continua agindo).

### 4.3 `classes.csv`

```csv
class.archer,resource.focus,skill.archer.quick_shot,,0,0,0,0.3
class.mage,resource.mana,skill.mage.arcane_dart,,0,0,0,1
```

Padrão copiado de `class.warrior,resource.momentum,skill.warrior.iron_cut,,10,15,5,1`: Foco e Mana não ganham por acerto nem por bloqueio, não decaem fora de combate (começam cheios; `CreateVitals` só zera o recurso se `resourceDecayOutOfCombat` > 0) e regeneram. Só o Foco tem `regenMultWhileMoving` abaixo de 1 (0,3, o comentário do `content.h`).

### 4.4 `class_stats.csv`

```csv
class.archer,life,90,9
class.archer,resource,100,0
class.archer,resource_regen,8,0
class.archer,life_regen,0.8,0.08
class.archer,armor,10,1
class.archer,crit_chance,0.08,0
class.archer,move_speed,470,0
class.mage,life,70,7
class.mage,resource,150,0
class.mage,resource_regen,5,0
class.mage,life_regen,0.6,0.06
class.mage,armor,5,0.5
class.mage,crit_chance,0.05,0
class.mage,move_speed,450,0
```

`[HIPÓTESE]`: vida 120 (Guerreiro) / 90 (Arqueiro) / 70 (Mago) segue o plano ("pouca defesa; distância é a armadura", "frágil"). O Guerreiro não tem `resource_regen` (o Ímpeto vem de acertar). Arqueiro anda 4% mais rápido que o Guerreiro para sustentar a fuga.

### 4.5 `rules.csv`

```csv
combo_window,0.4
combo_window_after_dodge,0.3
attack_buffer,0.15
heavy_hold_threshold,0.35
light_windup_credit_max,0.7
guard_lower_time,0.1
dash_shot_range,1000
```

O Backend registra as 7 chaves na tabela de chaves de `content.cpp` (faixa 0 a 5 s para os tempos; `light_windup_credit_max` entre 0 e 1) e no `rules.schema.json`.

### 4.6 Proposta: tabela nova `basic_kits.csv` (uma linha por classe, tabela opcional como `potions.csv`)

O combo, a carga e a defesa são propriedade da **classe**, não de uma habilidade, e as colunas atuais de `skills.csv` não os expressam. A proposta mínima é uma tabela de 15 colunas (o Tech Lead e o Data Engineer decidem o formato final):

| Coluna | Tipo | Significado |
|---|---|---|
| `classId` | ID → `classes.csv` | Chave primária |
| `lightChain` | lista (`\|`) de 1 a 3 IDs → `skills.csv` | Golpes leves em ordem; o mesmo ID pode repetir |
| `heavySkill` | ID → `skills.csv` | Golpe forte |
| `heavyChargeTime` | s, > 0 | Duração da carga depois do limiar |
| `heavyMaxMult` | ≥ 1 | Multiplicador de dano na carga máxima |
| `chargeEffect` | ID → `effects.csv` | Efeito reaplicado enquanto carrega |
| `guardEffect` | ID → `effects.csv` | Efeito reaplicado enquanto defende |
| `guardArc` | graus, 0 a 360 | Arco da defesa (total) |
| `guardMaxHold` | s | 0 = ilimitado; senão a defesa cai sozinha |
| `guardCooldown` | s | Espera depois de soltar (ou depois de cair sozinha) |
| `guardPerfectWindow` | s | 0 = sem defesa perfeita |
| `guardPerfectCooldown` | s | Tempo mínimo desde o último aperto para a janela abrir de novo |
| `guardPerfectEffects` | lista (`\|`) de IDs → `effects.csv` | Aplicados no atacante corpo a corpo |
| `guardPerfectResource` | número | Recurso ganho pela perfeita (substitui `resourceOnBlock`) |
| `guardDrainPerDamage` | número | Recurso gasto por ponto de dano evitado (0 = não gasta) |

Linhas (`basic_kits.csv`):

```csv
classId,lightChain,heavySkill,heavyChargeTime,heavyMaxMult,chargeEffect,guardEffect,guardArc,guardMaxHold,guardCooldown,guardPerfectWindow,guardPerfectCooldown,guardPerfectEffects,guardPerfectResource,guardDrainPerDamage
class.warrior,skill.warrior.iron_cut|skill.warrior.combo_2|skill.warrior.combo_3,skill.warrior.heavy_slash,0.9,2,effect.charging.heavy,effect.guarding.warrior,120,0,0.25,0.2,0.8,effect.stun|effect.guard_break,25,0
class.archer,skill.archer.quick_shot|skill.archer.quick_shot|skill.archer.fan_shot,skill.archer.piercing_shot,0.8,2,effect.charging.archer,effect.guarding.archer,90,1.2,1,0,0,,0,0
class.mage,skill.mage.arcane_dart|skill.mage.arcane_dart|skill.mage.arcane_orb,skill.mage.fireball,1,2,effect.charging.heavy,effect.guarding.mage,360,0,0.4,0,0,,0,1
```

Tempos de carga e carga máxima (do clique ao disparo automático): Guerreiro 0,35 + 0,9 = 1,25 s; Arqueiro 0,35 + 0,8 = 1,15 s; Mago 0,35 + 1,0 = 1,35 s `[HIPÓTESE]`.

### 4.7 Itens (proposta, fora do pedido, para o Data Engineer)

O Arqueiro depende de arma de projétil (`weaponTags` já aceita `projectile`). Linha sugerida para `item_bases.csv`:

```csv
item_base.hunter_bow,main_hand,1,crit_chance:flat:0.02,8,,,,0.8,projectile,m,
```

O Mago não precisa de item (dano fixo por elemento); um cajado entra depois como visual e como fonte de `cast_speed` e `damage` (pergunta Q18-1).

## 5. Animação (só clipes KayKit CC0 já listados)

Regra geral para o Frontend: cada golpe é um clipe cujo ponto de impacto (medido no editor, `[HIPÓTESE]` ~35 a 45% do clipe nos ataques de uma mão) cai em `preparação + impacto` do core. `velocidade do Animator = tempo do clipe até o impacto / (preparação + impacto)` para a primeira parte; a recuperação toca o resto do clipe, cortado se a esquiva cancelar. Braço da arma/arco em camada superior, pernas em camada inferior.

Direção da esquiva: ângulo entre o movimento e a mira no cursor: até 45° `Dodge_Forward`, de 135° em diante `Dodge_Backward`, o resto `Dodge_Left` ou `Dodge_Right`.

### 5.1 Guerreiro

| Golpe | Clipe(s) | Uso |
|---|---|---|
| Clique 1, Corte de Ferro | `Melee_1H_Attack_Slice_Horizontal` | Varredura da direita para a esquerda |
| Clique 2 | `Melee_1H_Attack_Slice_Diagonal` | Volta em diagonal (sentido oposto) |
| Clique 3 | `Melee_1H_Attack_Jump_Chop` | Fecho: salto curto com golpe de cima, aproveita o empurrão |
| Forte, carregando | `Melee_2H_Attack_Slice`, congelado no frame de arma atrás (parâmetro `holdAt`, a medir) | Pose parada enquanto carrega |
| Forte, soltar | `Melee_2H_Attack_Slice`, do frame congelado até o fim | Golpe largo de 150° |
| Defesa: erguer | `Melee_Block` | 1 a 6 frames de entrada, nunca mais que `guard_lower_time` |
| Defesa: segurando | `Melee_Blocking` (loop) | Camada superior; pernas em `Walking_A` (frente), `Walking_Backwards` (recuando) e `Running_Strafe_Left` / `Running_Strafe_Right` a 55% de velocidade (laterais) |
| Defesa: golpe recebido | `Melee_Block_Hit` | Sobreposição de 0,2 s |
| Defesa perfeita | `Melee_Block_Hit` com hitstop de 60 ms e flash | Sem clipe novo |
| Q, Investida | `Running_A` no avanço + `Melee_1H_Attack_Stab` na chegada | |
| E, Fenda de Pedra | `Melee_2H_Attack_Chop` | |
| R, Escudada | `Melee_Block_Attack` | |
| Carregando andando | `Walking_B` nas pernas | Pose do clipe forte nos braços |
| Movimento livre | `Running_A` (padrão) | |

### 5.2 Arqueiro

| Golpe | Clipe(s) | Uso |
|---|---|---|
| Clique 1 e 2 | `Ranged_Bow_Draw` (acelerado para a preparação) + `Ranged_Bow_Release` | Disparo curto |
| Clique 3, leque | `Ranged_Bow_Draw` na velocidade normal + `Ranged_Bow_Release` | Puxada completa; o atraso maior (0,18 s) diferencia do leve |
| Forte, carregando | `Ranged_Bow_Draw` → `Ranged_Bow_Aiming_Idle` (loop) | |
| Forte, soltar | `Ranged_Bow_Release` | |
| Defesa | `Melee_Blocking` (levanta o arco na frente do corpo) `[HIPÓTESE: se ficar estranho com o arco, plano B é `Ranged_Bow_Idle` mais o efeito de guarda]` | `Melee_Block_Hit` quando absorve |
| Q, Salto | `Dodge_Backward` com tiro `Ranged_Bow_Release` na camada superior no pico (momento do impacto) | |
| E, Chuva | `Ranged_Bow_Draw_Up` → `Ranged_Bow_Release_Up` | A única que mira para cima (flechas caem do alto) |
| Movimento livre | `Running_HoldingBow` | |
| Carregando andando | `Walking_C` | |

### 5.3 Mago

| Golpe | Clipe(s) | Uso |
|---|---|---|
| Clique 1 e 2, Dardo | `Ranged_Magic_Shoot` | |
| Clique 3, Orbe | `Ranged_Magic_Spellcasting` (preparação) + `Ranged_Magic_Shoot` | |
| Forte, carregando | `Ranged_Magic_Spellcasting_Long` (loop do trecho final) | A bola de fogo cresce na frente do cristal |
| Forte, soltar | `Ranged_Magic_Shoot` | |
| Defesa: erguer | `Ranged_Magic_Raise` | Congela no frame final enquanto segura |
| Defesa: segurando | `Ranged_Magic_Raise` congelado; pernas `Walking_A` / `Walking_Backwards` | |
| Q, Nova | `Ranged_Magic_Summon` | Mãos ao chão; a onda sai no impacto |
| E, Raio | `Ranged_Magic_Spellcasting` (preparação de 0,35 s) + `Ranged_Magic_Shoot` | O raio sai do cristal |
| Movimento livre | `Running_B` | |
| Carregando andando | `Walking_B` | |

Esquivas de todas as classes: `Dodge_Forward`, `Dodge_Backward`, `Dodge_Left`, `Dodge_Right` (docs/13 item 1, duração 0,35 s).

## 6. Efeitos visuais

Paleta de `docs/03` seção 6 (VFX do jogador: aditivo, fino, alfa de até 0,75, núcleo claro, sem contorno escuro; **nunca** `#E0301E` como massa no chão). Todos desligam com "Reduzir efeitos do jogador". "Tremor" segue as regras de `docs/03` seção 6 (só impactos grandes; opção Normal / Reduzido / Desligado). Tempos em milissegundos. Sockets sugeridos no modelo: `weapon_tip`, `bow_nock`, `staff_crystal`, `shield_face`, `root_feet`, `chest`.

| ID | Efeito | Golpe | Cor (núcleo / meio / borda) | Duração | Nasce em | Tremor |
|---|---|---|---|---|---|---|
| `fx.trail.warrior_1` | Rastro da arma, arco horizontal | Clique 1 | Fogo `#FFE2B0` / `#F2642C` / `#B8361A` | 180 | `weapon_tip` (fita seguindo a ponta) | não |
| `fx.trail.warrior_2` | Rastro, diagonal | Clique 2 | Fogo, igual | 180 | `weapon_tip` | não |
| `fx.trail.warrior_3` | Rastro largo (×1,4) com fio dourado `#FFF2A8` no núcleo | Clique 3 | Fogo + ouro | 240 | `weapon_tip` | não |
| `fx.trail.warrior_heavy` | Rastro largo e longo | Forte | Fogo + ouro | 300 | `weapon_tip` | sim se carga ≥ 80% e atinge 3 ou mais alvos: 3 cm, 150 ms |
| `fx.hit.spark` | Faísca de impacto: poeira `#8A7F78` 6 a 10 e faíscas `#FFE066` 4 a 8 (docs/03); no forte, o dobro e um anel curto | Todo acerto físico | Físico `#FFFFFF` / `#E8E0D4` / `#8A7F78` | 300 a 700 | Ponto de contato no alvo | não (golpe pesado ganha hitstop de 60 ms, regra existente) |
| `fx.charge.glow.warrior` | Brilho de carga na lâmina, cresce de 0 a 100% e pisca no máximo (80 ms em branco) | Forte | Fogo | durante a carga, loop de 150 ms de pulso no máximo | `weapon_tip` | não |
| `fx.charge.glow.archer` | Ponta da flecha acende, linhas de tensão no arco | Forte (Arqueiro) | Ácido `#E6FF8A` / `#8FD43A` / `#3E7A1E` | durante a carga | `bow_nock` | não |
| `fx.charge.glow.mage` | Orbe de fogo cresce de 10 a 70 cm na frente do cristal | Forte (Mago) | Fogo `#FFE2B0` / `#F2642C` / `#B8361A` | durante a carga | `staff_crystal` | não |
| `fx.charge.ring` | Anel fino no chão que fecha com a carga (leitura sem olhar o personagem); some no soltar | Forte, todas | `#FCD58A` alfa 0,5 (borda do dourado, nunca vermelho) | durante a carga | `root_feet` | não |
| `fx.guard.arc_hint` | Arco de 4 cm de largura no chão mostrando a frente protegida (120° ou 90°); a cúpula do Mago usa `fx.barrier.mage` | Defesa | `#FCD58A` alfa 0,45 | enquanto segura | `root_feet`, voltado para a mira | não |
| `fx.guard.block_spark` | Faísca de defesa normal: lascas e faíscas curtas | Defesa, golpe absorvido | `#E8E0D4` / `#FFE066` | 150 | Ponto de contato na frente | não |
| `fx.guard.perfect` | Faísca de defesa perfeita: anel dourado que se expande até raio 120 cm + estrela de 6 pontas branca no contato; hitstop de 60 ms nos dois lados | Defesa perfeita do Guerreiro | Ouro sagrado `#FFF2A8` / `#F2B23A` / `#8F5A12` | 220 | Ponto de contato em `shield_face` | não (o hitstop faz o trabalho) |
| `fx.stun.stars` | Estrelas girando sobre o atacante | Defesa perfeita | `#FFF2A8` | 800 (igual ao `effect.stun`) | Cabeça do alvo | não |
| `fx.arrow` | Flecha em malha curta + fita de rastro fina | Disparo Reto, Leque, Perfurante, Salto | Ácido `#E6FF8A` / `#8FD43A` / `#3E7A1E` | rastro de 120; voo conforme alcance / velocidade | `bow_nock` (+ clarão de saída de 80 ms) | não |
| `fx.arrow.pierce` | Flecha mais grossa com rastro longo de 250 ms e faíscas em cada alvo atravessado | Tiro Perfurante | Ácido com núcleo `#FFFFFF` | 250 | `bow_nock` | não |
| `fx.arrow.fan` | Três flechas; clarão em leque de 80 ms na saída | Clique 3 do Arqueiro | Ácido | 120 | `bow_nock` | não |
| `fx.leap.dust` | Anel de poeira nos pés + 3 linhas de vento atrás | Salto | Físico `#8A7F78` | 250 | `root_feet` | não |
| `fx.rain` | 12 a 16 flechas caem em 0,6 s dentro do círculo; círculo de marcação fino 0,25 s antes de cair; poeira no impacto | Chuva | Ácido; marcação em `#8FD43A` alfa 0,5, nunca vermelha | 700 | Centro no cursor (altura de 6 m para as flechas) | não |
| `fx.dart` | Dardo: esfera de 20 cm + rastro de 150 ms + fagulhas sombra `#9A4BD6` | Dardo Arcano | Raio `#F2F6FF` / `#7FA8FF` / `#3A4FB8` | 150 (rastro); explosão no acerto 200 | `staff_crystal` | não |
| `fx.orb` | Orbe: esfera de 45 cm que pulsa; explosão de 130 uu com onda curta | Orbe Arcano | Raio + sombra | explosão 350 | `staff_crystal`; explosão no ponto de impacto | não |
| `fx.fireball` | Bola de fogo de 70 cm com rastro de brasas 300 ms; explosão de 220 uu com clarão, anel e brasas | Bola de Fogo | Fogo vermelho-laranja `#FFE2B0` / `#F2642C` / `#B8361A` | explosão 450 | `staff_crystal`; explosão no ponto de impacto | sim se carga ≥ 80%: 3 cm, 150 ms |
| `fx.nova` | Anel de gelo cresce do herói até 340 uu em 350 ms; cristais no chão por 600 ms | Nova de Gelo | Gelo `#D8F6FF` / `#4FA8E8` / `#2B4F92` | 350 + 600 | `root_feet` | não |
| `fx.chill` | Cristais pequenos nos pés e tom azulado nos inimigos lentos | `effect.chill` | Gelo | 3000 (duração do efeito) | Pés do alvo | não |
| `fx.ray` | Feixe de 40 uu: clarão de 80 ms mais brilho residual de 250 ms; faíscas em cada alvo | Raio Arcano | Raio `#F2F6FF` / `#7FA8FF` / `#3A4FB8` | 330 | `staff_crystal` até o fim do alcance | não |
| `fx.barrier.mage` | Cúpula translúcida de 110 uu de raio com ondas hexagonais nos pontos de impacto; transparência diminui conforme a Mana baixa; estilhaça em 300 ms quando acaba a Mana | Barreira Arcana | Raio (`#3A4FB8` borda, `#7FA8FF` preenchimento alfa 0,25) | enquanto segura | `chest` (centro) | não |
| `fx.guard.archer` | Brilho curto verde no arco ao absorver | Guarda do Arco | Ácido | 150 | `bow_nock` | não |

Nenhum efeito do jogador bloqueia a leitura de telegraph de inimigo (docs/03): o `fx.rain` e o `fx.nova` usam alfa até 0,75 e nunca preenchem o chão com vermelho.

## 7. Lista curta "Para o Frontend"

1. Entrada: esquerdo (apertar, soltar, tempo apertado), direito (apertar, soltar), Q, E, R, Espaço. Enviar ao core eventos com número de tick, nunca tempo em float. Remapeável (RF do design system).
2. Detecção de clique ou segurar fica no core (seção 1.3); o Frontend só mostra o estado devolvido (leve, carregando, defendendo).
3. Animator em camadas: braços (ataque, carga, defesa) e pernas (movimento). Parâmetro `holdAt` por clipe para congelar a pose de carga. Velocidade do clipe = tempo do core.
4. HUD: ícones de LMB e RMB no lugar do slot do botão direito; Q, E, R como habilidades; anel de carga (`fx.charge.ring`) e barra pequena de combo (3 pontos) junto ao herói; indicador de defesa perfeita (flash curto).
5. Modelos: Arqueiro e Mago com `bow_nock` e `staff_crystal`; Arqueiro com arco (`item_base.hunter_bow`); Guerreiro com `shield_face`.
6. VFX da seção 6 em pool; limite de 300 projéteis ativos.
7. Hitstop de 60 ms só em golpe forte, fecho do combo e defesa perfeita; respeitar "Reduzir flashes".
   Decisão de 19/10/2026 (prototipo): o golpe 2 do combo (`skill.warrior.combo_2`) leva um tranco leve de 35 ms (`lightHitstopSkills` do `SO_CombatFeel`) e a câmera treme um terço do golpe pesado; o golpe 1 segue sem hitstop, para a abertura do combo manter a cadência e o crescendo ser 0, 35 e 60 ms. Reversível pela lista do asset.
8. Seleção de classe do protótipo: as linhas de Arqueiro e Mago ficam acessíveis por uma opção de debug até o dono aprovar a seleção.

## 8. Lista curta "Para o Backend"

1. Ler `basic_kits.csv` (tabela opcional) e as 7 chaves novas de `rules.csv`; validar referências (habilidades, efeitos, classe), `lightChain` de 1 a 3, `guardArc` entre 0 e 360, `heavyMaxMult` ≥ 1.
2. Coluna opcional `pierce` em `skills.csv` (0, vazio ou 99): perfuração; cada projétil acerta o mesmo alvo uma vez (RF-16). Várias flechas do mesmo leque podem acertar o mesmo alvo (cada projétil é uma regra explícita).
3. Semântica de `skills.csv` que precisa ser confirmada: (a) `projectile` com `radius` > 0 explode no impacto, acertando todos os alvos uma vez; (b) `projectile` com `projectiles` > 1 e `coneAngle` > 0 dispara em leque de `coneAngle` graus; (c) `area` com `range` 0 é centrada em quem usa; (d) `area` com `impact` longo (Chuva) escolhe o círculo no cursor, limitado por `range`; (e) `dash` com tag `projectile` pula `range` uu para trás e atira em `dash_shot_range` no pico.
4. Máquina de combate básica no **core** (a Unity não calcula regra): índice do combo, janelas em ticks, buffer, limiar de segurar, carga com multiplicador linear, crédito de preparação, cancelamentos da seção 1.3. API C sugerida: eventos de entrada (apertar/soltar por botão, com tick) e eventos de saída (`HitStarted(skillId, comboIndex, chargeMult)`, `GuardUp`, `GuardBroke`, `PerfectGuard`, `ChargeStarted`, `ChargeFull`).
5. Defesa: reaplicar `guardEffect` a cada tick enquanto segurado, respeitando `guardMaxHold` e `guardCooldown`; teste de ângulo no dano recebido (golpe fora de `guardArc`: o `damage_taken` do efeito não vale naquele golpe); janela perfeita contada em ticks desde o aperto (e `guardPerfectCooldown`); em perfeita, 0 de dano, `guardPerfectEffects` no atacante com tag `melee`, `guardPerfectResource` no lugar de `resourceOnBlock`; dreno de recurso por ponto evitado (`guardDrainPerDamage`), parcial se faltar.
6. `resourceOnHit` e `resourceOnBlock` hoje só são lidos em `expedition.cpp`; confirmar que o caminho de tempo real também os aplica.
7. `regenMultWhileMoving` não é lido em `TickVitals` (só vai ao C API): o Foco precisa de um parâmetro "em movimento".
8. `IsIdleCompatible` deve olhar só as habilidades equipadas nos slots Q/E/R mais o golpe 1; não pode exigir perfil idle de `combo_2`, `combo_3`, `heavy_slash` nem do kit do Arqueiro e do Mago. Arqueiro e Mago ficam bloqueados para expedição por RF-43 (esperado).
9. `ComputeActionTiming`: confirmar que `cast_speed` tem valor base neutro (1) quando a classe não o define (Mago).
10. Rodar `ctest` e `tools/dados/validate_data.py` com 3 classes: testes que assumem classe única (por exemplo `test_balance_probe`) podem precisar de ajuste.
11. Empurrão por tipo de alvo (comum / elite / chefe) e ajuste de `knockback` em habilidades; o `shield_arc` do inimigo já tem o teste de ângulo que a defesa pode reaproveitar.
12. Efeitos `effect.guarding.*` e `effect.charging.*` duram 0,1 s e são renovados a cada tick: confirmar custo (um efeito `refresh` por tick por herói é barato; só o herói usa).

### 8.1 Decisões do orquestrador sobre este documento (17/10/2026)

- **A máquina de combate básica fica no C#**, em `HeroCombatLogic`. O item 4 acima não vale. A máquina roda no passo fixo de 60 Hz e é determinística. Ela já é dona do buffer, da linha do tempo da ação e do cancelamento pela esquiva. O core fornece os valores (`basic_kits.csv` e as chaves novas de `rules.csv`, lidos e validados pelo core e expostos pela API C) e continua resolvendo dano, efeitos, defesa e recurso. A Unity não inventa número.
- **Teste de ângulo da defesa:** o C# já tem a geometria (`ShapeQuery`) e diz ao core, a cada golpe recebido, se o golpe veio de dentro do arco. O core aplica os modificadores dos efeitos com a tag `guard` só quando o golpe vem de dentro do arco.
- **Q18-1:** opção (a). O Arqueiro começa com `item_base.hunter_bow` e o Mago fica sem arma por enquanto.
- **Q18-2:** opção (a). Arqueiro e Mago ficam sem expedição no protótipo.
- **Q18-3:** opção (a). A Chuva de Flechas é um golpe único com atraso.
- **Q18-4:** opção (a). A defesa do Guerreiro não tem limite e o H18-05 confere.
- Essas decisões valem até o dono vetar; elas vão no relatório final para ele.

## 9. Hipóteses que precisam de playtest

| ID | Hipótese | Como testar | Aprovado se |
|---|---|---|---|
| H18-01 | `combo_window` 0,40 s e `attack_buffer` 0,15 s deixam o combo fluir sem exigir ritmo | 5 jogadores, 3 minutos na Cripta, contar quantos terminam o 3º golpe sem querer | ≥ 70% dos combos iniciados chegam ao 3º golpe quando o jogador quer; < 10% chegam "sem querer" |
| H18-02 | Decidir o golpe leve ao soltar, com crédito de preparação, não atrasa a sensação | Comparar com versão que dispara no aperto | Jogadores não percebem diferença de atraso; sem queixa de "demora" |
| H18-03 | Carga mínima 0,35 s e carga máxima ~1,25 s dão uso ao forte | Observar quantos fortes saem por sala | O forte é usado em ≥ 15% dos golpes do Guerreiro e < 60% |
| H18-04 | Defesa perfeita de 0,2 s é acertável pelo telegraph de 0,7 s da Sentinela | Medir % de acerto em 30 tentativas por jogador | Entre 40% e 70% de acerto após 3 minutos de prática |
| H18-05 | Defesa do Guerreiro a -65% sem limite não vira "ficar parado" | Medir tempo médio em guarda e vida perdida | Guerreiro que defende o tempo todo perde vida na Cripta (a regeneração de 1/s não cobre) |
| H18-06 | Arco de 120° dá leitura de posição sem frustrar | Comparar 120° com 360° | Jogadores citam "contornar" como decisão, não como falha |
| H18-07 | Mana 150 / regeneração 5 por segundo cria decisão sem travar o Mago | Cronometrar quanto tempo até zerar | O Mago esvazia a Mana em 20 a 35 s de luta contínua |
| H18-08 | Foco 100 / regeneração 8 (2,4 em movimento) faz o jogador "parar para atirar" | Cronometrar tempo parado vs. em movimento | O Arqueiro para pelo menos 25% do tempo |
| H18-09 | A Chuva de Flechas de 1 acerto em 0,7 s é aceitável | Observar se inimigos escapam sempre | Acerta ≥ 50% dos comuns; se < 30%, pedir zona com vários golpes (Q18-3) |
| H18-10 | O Leque (3 × 0,65) vale a pena de perto | Comparar DPS efetivo | Mais dano que 2 Disparos Retos quando o alvo está a menos de 300 uu |
| H18-11 | Esquivar e retomar o combo (`combo_window_after_dodge` 0,3 s) é fluido | Observar uso | Jogadores reportam que a esquiva "não quebra o combo" |

## 10. Perguntas abertas

**Q18-1. O Mago usa cajado como item? E o Arqueiro, arco comprado ou inicial?**
Contexto: o Arqueiro precisa de arma de projétil para causar dano normal (sem arma, o core usa 3 de dano físico base e o dano cai a um terço). O Mago não depende de arma porque o dano dele é fixo por elemento. A tabela de itens atual só tem espada e maça.
Opções: (a) Arqueiro começa com `item_base.hunter_bow` e Mago sem arma: funciona hoje, o Mago nunca melhora com item de arma. (b) Criar também `item_base.crystal_staff` com bônus de feitiço: o Mago ganha progressão de arma, exige regra nova de `weaponTags` para cajado. (c) Arqueiro sem arco inicial: perde um terço do dano, só para teste de falha.

**Q18-2. Arqueiro e Mago ficam sem expedição no protótipo?**
Contexto: expedição exige perfil idle calibrado por habilidade (RF-43). Só o Corte de Ferro do Guerreiro tem perfil. Criar perfis para Arqueiro e Mago exige o teste de paridade de cada habilidade.
Opções: (a) Sem expedição para as duas classes no protótipo: nenhum trabalho extra, o pilar "Planejar o retorno" só vale para o Guerreiro. (b) Perfil `manual_estimate` só do Disparo Reto e do Dardo Arcano: libera expedição básica, menos precisa. (c) Esperar a Etapa 4 (elenco): igual a (a) e documentado.

**Q18-3. A Chuva de Flechas é um golpe único ou uma zona de 3 s?**
Contexto: o plano descreve "saraivada numa área por 3 s". O formato atual de `skills.csv` não tem golpes repetidos numa área.
Opções: (a) Golpe único com atraso de 0,7 s (como está aqui): sem código novo, o jogador prende inimigos parados. (b) Zona com golpes a cada 0,5 s: exige colunas novas (`ticks`, `tickInterval`) e regra de "mesmo alvo mais de uma vez" no core.

**Q18-4. A defesa do Guerreiro pode ficar erguida sem limite?**
Contexto: o Arqueiro tem limite de 1,2 s e o Mago gasta Mana. O Guerreiro não gasta nada e só anda devagar; a vida dele cai 35% do dano em vez de 100%.
Opções: (a) Sem limite (como está): defesa simples; risco de o jogador ficar parado em Sentinela (testar em H18-05). (b) Fôlego de defesa que esvazia por golpe absorvido: acrescenta um recurso novo e uma barra. (c) Limite de tempo como o Arqueiro, só que maior (3 s): mantém a leitura, exige o mesmo campo `guardMaxHold` que já existe.

Observação de escopo: nada neste documento muda `docs/16`, os CSV ou o código; as linhas aqui são proposta para quem é dono de cada arquivo.
