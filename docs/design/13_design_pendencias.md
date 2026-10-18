# 13 — Decisões de design que travavam o protótipo (Game Designer)

Escopo: protótipo jogável do Guerreiro na Cripta Partida (`docs/requisitos-qa/02_requisitos.md`, seção 2). Este documento só decide e especifica; nenhum CSV, esquema ou header foi editado. Onde um dado precisa existir, a seção "Impacto em dados" diz qual tabela ou coluna, e o fechamento lista o pedido ao Data Engineer e ao Tech Lead.

Convenções: unidades de distância em uu (1 uu = 1 cm no Unreal; o Guerreiro anda a ~450 uu/s, ver item 12). Tempos em segundos. Valores marcados **[HIPÓTESE]** precisam de playtest. "Provisório: sim" quer dizer que o plano não fecha o número e a decisão vale até o primeiro playtest. A história não é tocada: nada aqui cria lore.

Pilares usados (plano, seção 1): P1 Conquistar pela ação, P2 Build com identidade, P3 Planejar o retorno, P4 Respeitar o tempo.

## Resumo das decisões

| # | Item | Decisão em uma linha | Provisório |
|---|---|---|---|
| 1 | Esquiva | 3 cargas, 1,5 s por carga (uma de cada vez), 0,35 s, 400 uu, i-frames 0–0,2 s, custo só a carga | Plano fecha tempos e cargas; distância é hipótese |
| 2 | Poções | Poção de Vida (40%, 3 cargas, 40 s) e Poção de Resguardo (barreira de 30%, 2 cargas, 60 s) | Sim |
| 3 | Escudada e stun | Stun 0,8 s só em comuns; elite, Arauto e chefe imunes e sofrem Quebra de Guarda (3 acúmulos = atordoamento de guarda 1,5 s) | Sim |
| 4 | Guardião | Vida 800 no nível 3 (400 por fase), fase 2 aos 50%, martelo 1,1 s / 0,9 s, escudo ±60° | Sim |
| 5 | Elites | Escudo = barreira de 40%; Veloz = +30% velocidade, +25% ataque; Volátil = explosão de 0,8 s | Sim |
| 6 | IA Cão e Arqueiro | Estados e alcances nas tabelas 6.1 e 6.2 | Sim |
| 7 | Nível de liberação | Corte 1, Investida 2, Fenda 3, Escudada 4 (protótipo); plano volta quando entrarem os livros | Sim |
| 8 | idleSupported / meta 35% | As 4 habilidades e o Único entram como "estimativa manual"; meta 30–40% pela regra de ritmo, sem constante nova | Sim |
| 9 | Único do Guardião | 1ª vitória garantida, depois 20% por vitória, garantido na 5ª sem drop | Sim |
| 10 | Valores de `rules.csv` | Manter 4 dos 5; `retreat_life_fraction` 0,20 para 0,25 | Sim |

**Respostas do dono (16/10/2026).** Escudada no nível 4 (o dono não teve preferência; vale a recomendação deste documento). Segunda poção = Poção de Resguardo. Arena do Guardião com pilares, então o bônus da investida no item 4 fica. Guardião obrigatório nesta rodada (P-2 do `docs/requisitos-qa/02_requisitos.md`). Os números continuam provisórios até o playtest.

**Câmera e escala de mapa (dono, 16/10/2026, depois de jogar a cena base `Base_Escala`).** Câmera a 56 m (ver `docs/tecnico/04_arquitetura.md`, seção 3.2). Escala de mapa da zona A: arena do Guardião de 40 × 40 m com pilares, salas de 24 a 32 m e corredores de 6 m de largura. Todo layout de área parte dessas medidas; distâncias em uu deste documento (1 uu = 1 cm) continuam válidas.

**Checkpoint e arena (dono, 16/10/2026).** Ao voltar ao checkpoint (por morte ou saída), os inimigos já mortos REAPARECEM, no estilo Souls. A porta da arena do Guardião fecha atrás do herói e só reabre quando a luta acaba (vitória ou morte). Ver `docs/tecnico/14_layout_cripta.md`.

---

## 1. Esquiva

**Decisão.**

| Parâmetro | Valor | Observação |
|---|---|---|
| Cargas máximas | 3 | plano seção 5 |
| Recarga | 1,5 s por carga, um relógio só (recarrega uma carga por vez, em série) | plano seção 5; 3 cargas vazias levam 4,5 s |
| Duração total | 0,35 s | plano seção 5 |
| Invulnerabilidade | de 0,00 a 0,20 s (inclui 0,00, exclui 0,20) | plano seção 5; RF-15 testa 0,1 s e 0,3 s |
| Distância | 400 uu (~0,9 s de caminhada) com curva de saída suave | **[HIPÓTESE]** |
| Custo | 1 carga; 0 de Ímpeto; 0 de vida | esquiva não compete com habilidades |
| Direção | direção do movimento; parado, para trás da mira | |
| Cancelamento | só a partir da metade final da recuperação de uma habilidade (nunca na preparação ou no impacto) | **[HIPÓTESE]** |
| Buffer de entrada | 0,10 s antes de a ação atual terminar | **[HIPÓTESE]** |
| Atravessa inimigos | comuns sim; Arauto, elites e chefes não | evita esquiva "por dentro" do chefe |
| Esquiva perfeita (opcional) | se um golpe teria acertado durante os i-frames: +10 de Ímpeto | **[HIPÓTESE]**; cortar se atrapalhar a leitura |

**Motivo.** A esquiva é a resposta ao telegraph (plano seção 5: "telegraph de chefe 0,7–1,2 s"). Telegraph de 0,7 s e janela de 0,2 s fazem o jogador sair antes, não no último frame. 3 cargas permitem esquivar de duas ações seguidas do Guardião e ainda sobrar uma. A recarga em série impede spam (P1). Para o idle, a esquiva da IA gasta carga, senão `ai_base_dodge` vira dano zero.

**Impacto em dados.** Chaves novas em `rules.csv` (item único, sem tabela): `dodge_max_charges`, `dodge_recharge`, `dodge_duration`, `dodge_iframes`, `dodge_distance`, `dodge_cost_resource`, `dodge_buffer`, `dodge_perfect_resource`. Estado `ExpeditionProgress` guarda cargas e relógio de recarga.

**Provisório:** tempos e cargas não (vêm do plano); distância, cancelamento, buffer e esquiva perfeita sim.

**Spec audiovisual (Art Director).** 2 imagens residuais a 50% e 25% de alpha durante os 0,2 s (design system seção de VFX); vento curto no início; recarga visível nos 3 pontos do HUD (`dodge_slot`).

---

## 2. Poções

**Decisão: 2 tipos, um por tecla.**

| Campo | `potion.life` Poção de Vida (tecla 1) | `potion.ward` Poção de Resguardo (tecla 2) |
|---|---|---|
| Efeito | cura 40% da vida máxima | barreira de 30% da vida máxima por 6 s (defesa: barreira vem antes da vida, plano seção 10) |
| Cargas máximas | 3 | 2 |
| Recarga por tempo | 40 s por carga (em série) | 60 s por carga (em série) |
| Tempo de uso | 0,4 s bebendo, andando a 50% | 0,4 s, igual |
| Trava entre usos | 1,0 s global (as duas poções) | idem |
| Acúmulo da barreira | não acumula; reaplicar renova | |

**Como enchem.** (a) Tempo: a recarga acima, em combate e no idle. (b) Matar uma elite: +1 carga na poção com menos cargas (empate: Vida). (c) Encher tudo ao chegar ao Refúgio, ao passar num checkpoint, ao reiniciar a luta do Guardião depois de morrer. Não enchem ao matar comuns.

**Motivo.** Cura e proteção respondem a problemas diferentes: Vida repara dano já tomado, Resguardo prepara um golpe grande do Guardião (martelo de 30, ver item 4) ou entra numa regra de IA do idle. Isso cria decisão de rota/regra (P3: "poção abaixo de 35%" contra "Resguardo se há elite"). A recarga lenta de 40 s é mais dura que os 20 s sugeridos em `docs/design/05_conteudo.md` porque 3 cargas + 20 s dariam ~9 curas de 40% numa luta de 150 s e esvaziariam o chefe. Com 40 s o chefe dá 3 + ~3 curas. A fonte de carga por elite premia ler o modificador (plano seção 5) e dá ao idle um jeito de "gastar menos" quando a rota tem elites. O 2º tipo é Resguardo (e não mana, que o Guerreiro não tem): usa a regra de barreira que já está no cálculo de defesa.

**Impacto em dados.** Tabela nova `potions.csv`: `id,kind(heal|barrier),fractionOfMaxLife,duration,maxCharges,rechargeSeconds,useTime,moveSpeedWhileUsing,globalLockout,refillOnEliteKill,hotkeySlot`. `potion_heal_fraction` do `ExpeditionRequest` sai do pedido e vem desta tabela. `AiRule.use_potion` precisa de `ref_id` (qual poção). Save: `potions` (int) vira `potion_slots` (ver pendência P10: o exemplo `migrate_1_to_2` serve de base: `{potion_id, charges, recharge_remaining}`).

**Provisório:** sim, todos os números. Segunda opção se Resguardo não pegar: segunda Poção de Vida com 2 cargas (corta a decisão; não recomendado).

**Spec audiovisual.** Vida: frasco vermelho (cor de vida do token). Resguardo: frasco ocre/dourado (azul já é mana e o Guerreiro não tem mana). Barreira: casca translúcida dourada em volta do herói, estala ao quebrar. Som de beber 0,4 s sincronizado.

---

## 3. Escudada, atordoamento (stun) e quebra de guarda

**Decisão: a Escudada continua sendo "golpe que acumula quebra de guarda e atordoa comuns" (plano seção 4).**

| Parâmetro | Valor |
|---|---|
| Escudada (já em `skills.csv`) | custo 25 Ímpeto, recarga 4 s, preparação 0,25 s, impacto 0,1 s, recuperação 0,3 s, coef. 1,3/1,45/1,6 (manter) |
| Efeito `effect.stun` | 0,8 s; **interrompe** a preparação/telegraph em andamento; só em alvo comum |
| Imunidade ao stun | elite (fixa ou sorteada), Arauto de Pedra (família constructo), chefe |
| `effect.guard_break` | +10% de dano recebido por acúmulo, até 3 acúmulos, 8 s; novo acúmulo renova a duração de todos (manter o CSV; regra de timer único) |
| Ao chegar a 3 acúmulos (alvos imunes ao stun) | **Guarda Quebrada**: consome os acúmulos, o alvo fica atordoado 1,5 s ("stagger"; interrompe o golpe em preparação), perde barreira/escudo; +30% de dano recebido durante o stagger (os 3 acúmulos contam até ele terminar) |
| Escudo frontal do Guardião durante a Guarda Quebrada | cai por 5 s |
| Imunidade a nova Guarda Quebrada | 8 s no chefe, 4 s em elite e Arauto (evita lock) |
| Comuns | recebem os acúmulos (+dano), mas já têm o stun; aos 3 acúmulos não há stagger extra |

**Motivo.** Cada tipo de inimigo tem uma resposta diferente (plano seção 5): comuns -> stun (agrupar e usar área), constructos -> quebra de guarda no tempo certo, elites com escudo -> quebra remove a barreira, chefe -> abre a janela. Isso dá à Escudada um papel que a Fenda e o Corte não cobrem (P2). Como a recarga é 4 s e o timer único dura 8 s, três Escudadas cabem na janela (0, 4, 8). Alternativa sem Escudada: contornar o escudo por trás (item 4), então a Escudada é um atalho, não um bloqueio. O stun de 0,8 s e a ausência de stun no chefe vêm de `docs/design/05_conteudo.md` (seção 4) e do plano ("atordoa comuns").

**Impacto em dados.**
- `enemies.csv`: colunas `stunImmune` (bool), `guardBreakStaggerSeconds`, `guardBreakImmunitySeconds`.
- `effects.csv`: o stun deixa de ser modelado só por `move_speed`/`attack_speed more -1`; precisa de flag `interrupts` (cancela preparação). Proposta: coluna `isStun` ou `interruptsAction`.
- `rules.csv`: `guard_break_stagger_seconds` (1,5), `guard_break_stagger_damage_taken` (0,30), `guard_break_immunity_boss` (8), `guard_break_immunity_other` (4), `boss_shield_down_seconds` (5).

**Provisório:** sim, tudo exceto "stun só em comuns" e "3 acúmulos" (CSV atual e plano).

**Spec audiovisual.** Impacto de escudo com onda seca; estrelas de atordoamento só em comuns; Guarda Quebrada: faísca dourada, escudo do chefe cai no chão e some por 5 s (silhueta clara), som de metal rachando.

---

## 4. Guardião da Cripta (chefe)

**Decisão: 2 fases, nível de chefe = nível do mapa (3).**

### 4.1 Atributos

| Campo | Hoje (`enemies.csv`) | Recomendado | Motivo |
|---|---|---|---|
| Vida | `1000:100` (1200 no nível 3) | `700:50` (800 no nível 3) | Dano do jogador no nível 4: Corte de Ferro 9 × coef 1 = 9, armadura do chefe ~34 reduz ~43%, ou seja ~5 por golpe, ~11 dps contínuos. Com 50% de uso do tempo (esquivas, escudo) são ~5,7 dps: 800 de vida = ~140 s. Meta: 120–180 s (plano: "combate gostoso em 30 s", chefe sem encher) **[HIPÓTESE]** |
| Armadura | `40:4` | `30:2` | idem; com 40:4 a luta passaria de 4 min |
| Vida por fase | — | Fase 1: 100% a 50% (400); Fase 2: 50% a 0% (400) | |
| Dano dos golpes | martelo 30, escudada 14 | manter | o jogador no nível 4 tem ~156 de vida + ~12 do peitoral; martelo líquido ~25 (6–7 martelos) |

### 4.2 Escudo frontal

| Parâmetro | Valor |
|---|---|
| Arco | ±60° em torno da frente do chefe (120° total) |
| Efeito do golpe no arco | 0 de dano à vida; faísca + "clang"; sem Ímpeto; sem knockback |
| O ponto de origem do golpe | posição do atacante (para área, o centro do alvo atingido) |
| Cai por | atacar de fora do arco; Guarda Quebrada (item 3), por 5 s |
| Giro do chefe | 60°/s parado/perseguindo na fase 1, 75°/s na fase 2; **0°/s da preparação até o fim do impacto** (a direção do telegraph é travada) |

Com 450 uu/s, a 200 uu do chefe o jogador gira ao redor a ~129°/s, mais que o giro do chefe, então circular perto funciona; mas o Golpe de Escudo (alcance 200 uu) pune quem fica grudado. A 400 uu a velocidade angular é ~64°/s e não vence o giro de 75°: de longe não dá para contornar. É o equilíbrio de risco entre perto e longe (P1).

### 4.3 Padrões

| ID | Fase | Habilidade | Telegraph | Impacto | Recuperação | Forma | Dano | Peso |
|---|---|---|---|---|---|---|---|---|
| `pattern.guardian.hammer` | 1 | `skill.enemy.guardian_hammer` | 1,1 s | 0,15 s | 1,0 s | cone 100°, alcance 380 | 30 | 3 |
| `pattern.guardian.shield_bash` | 1 e 2 | `skill.enemy.guardian_shield_bash` | 0,7 s | 0,1 s | 0,6 s | frontal 90°, alcance 200, knockback 200 uu | 14 | 2 (x2 se o jogador está a menos de 200 uu na frente; 0 se está atrás) |
| `pattern.guardian.hammer` (versão fase 2) | 2 | idem | 0,9 s | 0,15 s | 0,8 s | idem | 30 | 3 |
| `pattern.guardian.shield_charge` | 2 | nova `skill.enemy.guardian_shield_charge` | 0,9 s | investida de 700 uu a ~1000 uu/s (~0,7 s) | 1,0 s | corredor de 150 uu de largura | 20 | 2; recarga própria 12 s |

Regras de escolha (RF-24, determinístico por seed do fluxo de eventos): atraso entre ações sorteado em 0,8–1,4 s (fase 1) e 0,6–1,1 s (fase 2); o mesmo padrão não repete mais de 2 vezes seguidas; primeira ação só 1,5 s depois de o jogador entrar na arena. Todo telegraph é uma forma no chão que enche durante a preparação, com som no início. Investida do Escudo que bate na parede da arena: stagger de 2,0 s e escudo caído por 5 s **[HIPÓTESE]** (a arena tem pilares: confirmado pelo dono em 16/10/2026).

### 4.4 Transição e invocação

- Aos 50% de vida: o chefe termina o golpe em curso (sem interromper no impacto), então entra em rugido de 2,0 s, invulnerável (dano que passaria de 50% é cortado em 50%).
- No 1,0 s do rugido, 2 Sentinelas Ocas surgem nos dois marcos no chão (flancos do chefe, ~600 uu), com marca de 0,8 s antes. Exatamente 2; não há reinvocação; morrem se o chefe morrer.
- Sentinelas invocadas: dados da Sentinela Oca do nível do mapa; **sem XP e sem loot** (não dá farm) **[HIPÓTESE]**.
- Morte do jogador: a luta reinicia em até 2 s (RF-18), chefe cheio na fase 1, Sentinelas removidas, poções cheias.

**Motivo.** Plano seção 5 (mecânica central, 2 fases, 2 Sentinelas) e RF-23. O telegraph fica dentro de 0,7–1,2 s e na fase 2 só encurta o martelo para 0,9 s (ainda legível). A fase 2 combina escudo + Sentinelas: o jogador precisa decidir entre limpar as adds (Fenda, Escudada) e perseguir o flanco (P1, P2). O Guardião é parte do domínio (RF-50), então o ponto de rotina tem que ser aprendido, não decorado.

**Impacto em dados.**
- `enemies.csv`: ajustar `crypt_guardian` vida/armadura; colunas novas `shieldArcDegrees`, `turnRateDegPerSec`, `turnRateDegPerSecPhase2`.
- Tabela nova `boss_phases.csv`: `bossId,phase,lifeThreshold,transitionSeconds,summonEnemyId,summonCount,shieldSeconds,turnRate,decisionDelayMin,decisionDelayMax`.
- Tabela nova `boss_patterns.csv`: `id,bossId,phase,skillId,weight,telegraphSeconds,recoverySeconds,cooldown,maxRepeat,playerNearWeightMult,ignoreIfBehind`.
- `skills.csv`: coluna `coneAngle` (graus) e `knockback` (uu); novo `skill.enemy.guardian_shield_charge`; `telegraphSeconds` por ataque (o `windup` hoje faz o papel; confirmar que windup = telegraph para inimigos).
- `enemy_attacks.csv`: nada além do novo ataque.

**Provisório:** sim (vida, armadura, tempos de pausa e investida). Não provisório: 2 fases, 2 Sentinelas, cone, escudo, telegraph 0,7–1,2 s (plano).

**Spec audiovisual.** Telegraph: cone laranja com grade e brasas, enchendo (design system, referência 6 do plano); som grave no início; outro "tick" curto 0,2 s antes do impacto. Escudo: placa grande de metal levantada na frente; some do braço ao quebrar. Rugido da fase 2: tremor leve e marcas de luz onde as Sentinelas vão surgir. Barra de chefe com marca no meio (50%).

---

## 5. Modificadores de elite

**Decisão.** Elite sorteada = inimigo comum com **vida x2,0, dano x1,2, XP x3, tabela `loot.crypt.elite`** (bate com os elites fixos de `enemies.csv`: Sentinela Escudada 120 contra 60 e Cão Veloz 80 contra 40) e 1 modificador no protótipo (plano: "1 ou 2" no jogo completo). Peso de sorteio no protótipo: Escudo 50, Veloz 50, Volátil 0 (desligado).

| ID | Nome | Efeito | Telegraph / leitura | Contra-jogo |
|---|---|---|---|---|
| `modifier.elite.shield` | Escudo | barreira = 40% da vida máxima, não regenera; imune a stun e knockback (regra de elite); 3 acúmulos de Guarda Quebrada removem a barreira inteira | casca dourada translúcida e anel no chão; estala ao quebrar | Escudada, dano concentrado, evitar gastar Fenda na barreira |
| `modifier.elite.swift` | Veloz | velocidade +30%, velocidade de ataque +25% (recuperação -20%); a preparação/telegraph não encurta | rastro de vento; nome "Veloz" | esquiva no tempo, não fugir (ele é mais rápido); Escudada para interromper |
| `modifier.elite.volatile` | Volátil (fora do protótipo, número pronto) | ao morrer, marca de 0,8 s no chão e explosão de raio 250 uu, 25 de dano físico (~16% da vida no nível 4); só atinge o jogador | círculo vermelho pulsando no corpo; rachaduras de brasa antes de morrer | matar à distância; esquivar para fora do círculo |

Os elites fixos (`enemy.shielded_sentinel`, `enemy.swift_ash_hound`) continuam como atalho de teste; os encontros usam `chanceElite` (0 a 0,1) e elites fixos nos encontros `enc.crypt.elite_*`.

**Motivo.** Plano seção 5: elite = "mais vida e um truque; ler o modificador antes de atacar". Barreira (Escudo) usa a regra de defesa existente (barreira antes da vida) e liga com a Quebra de Guarda do item 3; Veloz muda a distância e o ritmo, o oposto do Escudo (um é parede, outro é pressão); Volátil ensina o jogador a olhar para o chão, a mesma leitura do telegraph do chefe.

**Impacto em dados.** Tabela nova `elite_modifiers.csv`: `id,weightPrototype,lifeMult,damageMult,xpMult,barrierFractionOfLife,moveSpeedMult,attackSpeedMult,recoveryMult,deathExplosionRadius,deathExplosionDamage,deathExplosionFuse`. Multiplicadores base de elite em `rules.csv`: `elite_life_mult`, `elite_damage_mult`, `elite_xp_mult`. `encounters.csv`: `chanceElite` passa a sortear modificador (RNG de eventos). `enemies.csv`: o elite fixo pode ganhar coluna `modifierId` e perder os números aproximados.

**Provisório:** sim.

---

## 6. IA dos inimigos comuns (RF-20, RF-21)

Todos usam a base parado -> perseguir -> telegraph -> atacar -> recuperar (plano seção 10) e acrescentam estados próprios. Distâncias em uu.

### 6.1 Cão-de-Cinza (`enemy.ash_hound`) — fauna alterada: "rápidos, cercam, fogem com pouca vida"

| Estado | Entrada | Comportamento | Saída |
|---|---|---|---|
| Parado | spawn | fica no ponto; o bando todo é alertado se um passa de aggro | jogador a menos de 1100 (aggro, de `enemies.csv`) ou aliado alertado (raio 1500) |
| Perseguir | alerta | corre a 380 até 500 do jogador | a 500: Cercar |
| Cercar | a 350–500 do jogador | gira em volta a 300 uu/s; só 2 cães por vez podem atacar (fichas de ataque); o resto circula | ficha livre (sorteio de 1,8–2,8 s por cão) -> Telegraph |
| Telegraph | ficha | agacha 0,3 s (é o "aviso", não telegrafado para a IA do idle: `telegraphed=false`) | -> Atacar |
| Atacar | fim do agacho | investida de mordida (alcance 150, 6 de dano, impacto 0,1 s) | -> Recuperar |
| Recuperar | após a mordida | 0,4 s, depois pula para trás 250 uu em 0,3 s | -> Cercar |
| Fugir | vida abaixo de 25% (uma vez por cão) | corre do jogador por 4,0 s a 380 uu/s | volta a Cercar, sem regenerar |
| Volta ao ponto | jogador a mais de 2000 uu por 5 s | volta ao ponto, vida cheia | Parado |

Cão Veloz (elite fixo): velocidade 480, intervalo de ficha x0,8, mesmo resto. **Motivo:** o cerco com 2 fichas ensina "priorizar alvos e controlar distância" (plano) sem virar dano impossível de ler; fugir 4 s e voltar premia Fenda/Investida para finalizar. Idle: a fuga soma ~4 s ao encontro por cão que fugiu; entra como `idleApproachTime` e não como regra nova.

### 6.2 Arqueiro Fantasma (`enemy.ghost_archer`) — atirador: "fechar distância ou interromper"

| Estado | Entrada | Comportamento | Saída |
|---|---|---|---|
| Parado | spawn | sentinela no ponto | jogador a menos de 1400 (aggro e alcance) |
| Posicionar | alerta | anda a 200 uu/s para a faixa ideal de 700–1100 do jogador | na faixa: Telegraph se a cadência permitir |
| Telegraph | recarga pronta (2,0 s) | mira por 0,6 s com linha fina no chão até o jogador | -> Atacar |
| Atacar | fim da mira | flecha de 7 de dano, velocidade ~1400 uu/s (1 s a 1400 uu) **[HIPÓTESE]** | -> Recuperar |
| Recuperar | após o disparo | 0,8 s | -> Posicionar |
| Recuar | jogador a menos de 500 uu | anda para trás a 200 uu/s por no máximo 1,5 s | recuperou a faixa -> Posicionar; passou 1,5 s ou parede -> **Encurralado**: atira com a mesma preparação de 0,6 s, sem recuar |

Interrompem a mira: stun (Escudada) e o impacto da Investida. Golpes comuns não interrompem. No máximo 2 arqueiros disparam no mesmo intervalo de 0,8 s. **Motivo:** o arqueiro mais lento (200) que o jogador (450) torna "fechar distância" sempre possível, e o recuo curto evita jogo de pega infinito (RF-21: mantém distância mínima de 500).

**Impacto em dados (6.1 e 6.2).** Tabela nova `enemy_ai.csv`: `enemyId,aggroRange,alertRadius,leashRange,leashSeconds,preferredMin,preferredMax,retreatBelow,retreatMaxSeconds,circleMin,circleMax,circleSpeed,attackTokens,tokenIntervalMin,tokenIntervalMax,fleeLifeFraction,fleeSeconds,fleeOncePerLife,attackCooldown,maxSimultaneousShooters`. `enemies.csv` já tem `moveSpeed` e `aggroRange` (manter; a tabela de IA os reutiliza). Mais `projectileSpeed` em `skills.csv`.

**Provisório:** sim, todos.

---

## 7. Nível de liberação das habilidades

**Decisão (protótipo, nível máximo 6):**

| Habilidade | Plano (livro) | `02_requisitos` | Protótipo (esta decisão) |
|---|---|---|---|
| Corte de Ferro | inicial | 1 | **1** |
| Investida | 2 | 2 | **2** |
| Fenda de Pedra | 5 | 3 | **3** |
| Escudada | 3 | fora do protótipo | **4** (confirmado pelo dono; CSV atualizado em 16/10/2026) |

Barra de 4 espaços: fica cheia no nível 4. Níveis 5 e 6 só dão vida e XP para testar o teto de nível do idle (RF-33).

**Motivo.** O `02` fixou Fenda no 3 porque os encontros de grupo (hounds de 3 a 5, patrulhas de 2 a 3) pedem área e o idle precisa de um perfil de área. O plano pôs a Escudada antes da Fenda (3 contra 5). A Escudada é o contra do escudo do Guardião e precisa existir antes do chefe: no nível 5 ela chegaria depois dele. No nível 4 ela chega a tempo, porque o jogador chega ao Guardião em torno do nível 4 (XP: 12 a 28 por inimigo e ~530 XP acumulados para o nível 4, ~40 inimigos, **[HIPÓTESE]**). O chefe tem recomendação "nível 4" na arena; quem chega sem Escudada ainda vence contornando o escudo. É uma simplificação do protótipo: `unlockLevel` some quando existirem os livros e volta o nível do plano (Fenda 5, Escudada 3), registrado como regra de produto.

**Impacto em dados.** `skills.csv`: `skill.warrior.shield_bash.unlockLevel` de 5 para 4; `stone_rift` fica em 3. Sugestão: renomear a coluna futura para `bookMinLevel` quando os livros entrarem.

**Provisório:** sim.

---

## 8. idleSupported e a meta de idle ≈ 35%

### 8.1 O que entra no simulador agora

Sem isso a expedição fica bloqueada (RF-43), o que mata o pilar P3 do protótipo. Como o teste de paridade foi adiado (P-3), a decisão é **calibração manual estimada**:

| Item | `idleSupported` | Perfil (todos **[HIPÓTESE]**, `idleParitySampleSize` = 20 encontros jogados e medidos pelo dono) |
|---|---|---|
| `skill.warrior.iron_cut` | true | `idleAvgTargetsHit` 1,3; `idleApproachTime` 0,5; `idleUptime` 0,85 |
| `skill.warrior.charge` | true | alvos 1,0; aproximação 0,3 (o avanço já fecha a distância); `idleUptime` 0,9 |
| `skill.warrior.stone_rift` | true | `idleFractionOfGroupHit` 0,6 (grupos de 2–5); aproximação 0,6; `idleUptime` 0,8 |
| `skill.warrior.shield_bash` | true | alvos 1,0; aproximação 0,5; efeitos de stun/guard_break ignorados no idle (conservador); `idleUptime` 0,9 |
| `unique.empty_throne_maul` | true | o efeito (+20% de dano corpo a corpo por 4 s ao matar) é só atributo e roda no passo de 0,1 s; Regra 4 do plano vale só para o drop (o Único cai só no manual, mas pode ser equipado no idle) |
| Chefe e `modifier.elite.volatile` | n/a | o chefe não entra em patrulha (RF-31 e `bossEncounter`); Volátil desligado no protótipo |

`idleDodgeTelegraphedBonus` 0 e `idleDamageTakenMult` 1 para todas até haver medida. Esquiva da IA: sorteio com probabilidade `ai_base_dodge` (0,5) se houver carga (item 1); sem carga, o golpe acerta.

**Porta de acesso (regra nova).** O simulador aceita `idleSupported=true` com `idleParitySampleSize` > 0 e o selo de calibração **estimativa manual**; a tela de configuração mostra "estimativa" na previsão. Quando o bot de paridade existir, os 4 perfis sobem para `bot_parity` e a previsão perde o selo. O mesmo vale para o Único (P2): sem o campo de amostra em `uniques.csv`, o validador não consegue checar.

### 8.2 Meta ≈ 35%

`docs/tecnico/06_dados.md` D2 mostra que, com Fervor x3, o equilíbrio natural é 33,3% (idle igual ao manual sem Fervor). A meta de 35% quer dizer **idle ~1,05x o ritmo manual sem Fervor**, medido nas horas 1–4 (Vigor 100%). Nenhuma constante nova: o ritmo vem de quanto dura o encontro simulado (que depende dos perfis) e de `travelTime` dos encontros (4 a 8 s). Estimativa do plano: ciclo manual 15–30 s de combate + 5–10 s de respiro ≈ 33 s; o simulador luta ~25–30% mais devagar que um humano e soma ~6 s de travessia ≈ 32 s, que dá ~33–37%. Ordem de ajuste se fugir de 30–40% (critério RF-32 ±5 p.p.): 1) `travelTime` dos encontros, 2) `idleUptime`/`idleApproachTime` das habilidades, 3) `idleDamageTakenMult`. Não ajustar o Fervor (x3 é regra fechada).

**Provisório:** sim.

**Impacto em dados.** `skills.csv`: coluna `idleCalibration` (`none|manual_estimate|bot_parity`); `uniques.csv`: `idleParitySampleSize` e `idleCalibration`; os `idleParitySampleSize` e `idleSupported` das 4 habilidades. Tech Lead: o validador passa a aceitar `manual_estimate` com amostra > 0.

---

## 9. O Único do Guardião

**Decisão.** `unique.empty_throne_maul` (Martelo do Trono Vazio):
- **1ª vitória sobre o Guardião: garantido** (também grava o domínio, RF-50).
- **Vitórias seguintes: 20% por vitória.**
- **Proteção contra azar: garantido na 5ª vitória seguida sem Único.** Contador zera ao dropar.
- Só no jogo manual (`manualOnly=true`, mantido); nunca no idle (Regra 4).

**Motivo.** Hoje a chance é ~19% por morte (peso 10 de 99 em 2 sorteios), nem garantida nem protegida. No protótipo há um único Único e nenhum Fragmento de Eco (fora do escopo) para compensar azar: o plano diz "nenhuma build depende de sorte" (seção 6). A primeira vitória garantida mostra o feixe de luz e o efeito (RF-29, o maior teste de juice do drop) a todo testador. Depois dela, 20% mantém a "caça" (P1: jogar de novo é melhor que só coletar), e a 5ª garantida limita a sequência de azar a 4 lutas (~10 min). **[HIPÓTESE]**: o ritmo de 3 min por luta e a vontade de repetir só se sabem em playtest.

**Impacto em dados.**
- `loot_entries.csv`: coluna `fixedChance` (0 a 1, independe do peso) e `guaranteeFirstKill` (bool), `pityKills` (int). A linha do Único deixa de entrar no sorteio ponderado (tirar o peso 10 para não diluir as outras entradas).
- Save: `boss_progress` com `{enemy_id, kills, kills_since_unique}` por personagem.
- Cobre também P5: o validador pode exigir que `kind=unique` só apareça em tabela ligada a encontro de chefe.

**Provisório:** sim.

---

## 10. Valores provisórios de `rules.csv`

| Chave | Atual | Recomendado | Mantém? | Motivo |
|---|---|---|---|---|
| `block_mitigation` | 1,0 | **1,0** | Sim, sem efeito no protótipo | O Guerreiro do protótipo não tem fonte de bloqueio (`block_chance` não existe em `class_stats` nem em afixos). Revisar quando entrar o Bastião; ao entrar, testar 0,7 (bloqueio com teto de 50% e anulação total daria -50% de dano esperado, mais forte que qualquer armadura) |
| `armor_damage_factor` | 5,0 | **5,0** | Sim | Com armadura 34 do jogador (20 + 2/nível + elmo) o golpe de 8 da Sentinela perde ~46%, o martelo de 30 perde ~18%: os golpes pequenos são mitigados mais, o grande (que se esquiva) continua doendo. É a intenção do plano (seção 10) |
| `armor_max_reduction` | 0,9 | **0,9** | Sim | Nenhum equipamento do protótipo chega perto do teto; reavaliar com a Pedreira e o crafting |
| `ai_base_dodge` | 0,5 | **0,5** | Sim | O plano já fecha: "base de 50%, pior que um bom jogador" (seção 10, Perfil idle). Deixa de ser provisório |
| `retreat_life_fraction` | 0,20 | **0,25** | **Mudar** | O maior golpe da Cripta fora do chefe é o do Arauto (22, ~14% da vida no nível 4); dois golpes juntos passam de 25% em encontros com bando. Recuar aos 25% (e só se não houver poção, regra da arquitetura 04) dá margem para um golpe duplo sem morrer **[HIPÓTESE]** |

---

## 11. Itens de design que dependem de outros arquivos de dados (resumo)

- A luta do Guardião reinicia com poções cheias (item 4). Se parecer fácil demais, mudar para manter as cargas de antes da morte.
- Texto de UI novo: "Guarda Quebrada", "Poção de Resguardo", "Esquiva perfeita" (opcional), "Estimativa" (selo de calibração) para Narrative & Content.

## 12. Assunção usada nos cálculos: velocidade do jogador

`class_stats.csv` não tem `move_speed`. Os cálculos usam 450 uu/s (Cão 380, Cão Veloz 480, Sentinela 220, Arqueiro 200, Arauto 130, Guardião 180). **[HIPÓTESE]**: o Cão normal fica mais lento que o jogador (dá para fugir) e o Veloz mais rápido (não dá).

---

## Para o Data Engineer

1. **`rules.csv` (chaves novas):** `dodge_max_charges` 3, `dodge_recharge` 1.5, `dodge_duration` 0.35, `dodge_iframes` 0.2, `dodge_distance` 400, `dodge_cost_resource` 0, `dodge_buffer` 0.1, `dodge_perfect_resource` 10; `guard_break_stagger_seconds` 1.5, `guard_break_stagger_damage_taken` 0.3, `guard_break_immunity_boss` 8, `guard_break_immunity_other` 4, `boss_shield_down_seconds` 5; `elite_life_mult` 2.0, `elite_damage_mult` 1.2, `elite_xp_mult` 3.0; `potion_lockout` 1.0. Alterar `retreat_life_fraction` para 0.25.
2. **Tabela nova `potions.csv`** (item 2) com `potion.life` e `potion.ward`.
3. **Tabela nova `elite_modifiers.csv`** (item 5) com shield, swift e volatile (peso 0).
4. **Tabelas novas `boss_phases.csv`, `boss_patterns.csv`** (item 4) e **`enemy_ai.csv`** (item 6).
5. **`skills.csv`:** colunas `coneAngle`, `knockback`, `projectileSpeed`, `idleCalibration`; novo `skill.enemy.guardian_shield_charge`; `shield_bash.unlockLevel` 5 -> 4; perfis idle da seção 8 com `idleSupported=true`, `idleParitySampleSize=20`, `idleCalibration=manual_estimate`.
6. **`enemies.csv`:** `crypt_guardian` vida `700:50`, armadura `30:2`; colunas `stunImmune`, `shieldArcDegrees`, `turnRateDegPerSec`, `turnRateDegPerSecPhase2`, `guardBreakStaggerSeconds`, `guardBreakImmunitySeconds`, `modifierId` (elite fixo).
7. **`effects.csv`:** flag de interrupção para `effect.stun` (`interruptsAction`); novo `effect.potion_ward` (barreira) ou a barreira gerada pela tabela de poções.
8. **`uniques.csv`:** `idleParitySampleSize`, `idleCalibration`; `unique.empty_throne_maul.idleSupported` -> true (P2).
9. **`loot_entries.csv`:** `fixedChance`, `guaranteeFirstKill`, `pityKills`; remover a linha de peso do Único em `loot.crypt.guardian` (item 9) e validar que Único só aparece em tabela de chefe (P5).
10. **`class_stats.csv`:** `class.warrior,move_speed,450,0`.
11. **Save (`save_v1` -> proposta v2):** `potion_slots` (substitui `potions`), `boss_progress`; as cargas de esquiva não são salvas (reiniciam cheias ao carregar). Não aprovo `tutorial_flags` do exemplo de migração; só `potion_slots`.
12. **Loc:** chaves de poções, Guarda Quebrada, selo de estimativa; `potion.life.*` já existe em `docs/design/05_conteudo.md`.

## Para o Tech Lead

1. **`AiRule.use_potion`** precisa de `ref_id` (`potion.life` ou `potion.ward`; vazio = Vida). `ExpeditionRequest.potion_heal_fraction` sai e a cura vem de `potions.csv`.
2. **Estado de combate e `ExpeditionProgress`:** cargas e relógio de recarga da esquiva (em série) e de cada poção; recarga por tempo e +1 carga ao matar elite; trava global de poção de 1 s; barreira por poção antes da vida.
3. **Esquiva do IA no simulador:** probabilidade `ai_base_dodge + idleDodgeTelegraphedBonus` só se houver carga; a carga gasta recarrega a 1,5 s.
4. **Stun real:** `effect.stun` precisa interromper preparação; hoje é só `move_speed`/`attack_speed more -1`. Regras de imunidade (comum/elite/Arauto/chefe) e Guarda Quebrada (3 acúmulos -> stagger de 1,5 s, imunidade de 8 s/4 s, queda do escudo por 5 s). Timer único de acúmulos do `guard_break`.
5. **Escudo frontal do chefe:** arco ±60° calculado pela posição do atacante; 0 de dano à vida, sem Ímpeto; giro travado da preparação ao fim do impacto.
6. **Máquina de fases do chefe:** limiar de 50% com corte do dano excedente, rugido invulnerável de 2,0 s, invocação exata de 2 Sentinelas sem XP/loot, reset total ao morrer; escolha de padrões por seed do fluxo de eventos (sem 3 repetições, atrasos sorteados) lendo `boss_phases`/`boss_patterns`.
7. **Elite sorteada:** multiplicadores base e modificador sorteado no RNG de eventos; Volátil com explosão de fusível 0,8 s (desligado no protótipo).
8. **Calibração do idle:** o validador aceita `idleSupported=true` com `idleCalibration=manual_estimate` e `idleParitySampleSize` > 0; o relatório e a previsão mostram "estimativa". Único passa a ter o mesmo campo (P2).
9. **Drop do Único:** primeira vitória garantida, 20% depois, garantido na 5ª vitória seguida sem drop; contador por chefe no save; usa o fluxo de RNG de loot. Persistir o contador antes de entregar o item (coleta sem duplicar, RF-55).
10. **Recuo do idle:** `retreat_life_fraction` 0,25, avaliado depois das regras de poção no mesmo passo de 0,1 s.
11. **Perfil de fuga do Cão:** o simulador soma ~4 s por cão que fugiu (via `idleApproachTime` da habilidade que o finaliza ou o `fleeSeconds` de `enemy_ai`), sem simular posição.

---

## Balanceamento e dados — rodada 2 (16/10/2026)

Origem: `docs/tecnico/09_mudancas_contrato.md` seção 7 (7.2 item 5, 7.6) e os pedidos do Frontend. Base: CSV de `Content/Data/` e a leitura de `ShatterCore/src/expedition.cpp`, `damage.cpp`, `combat.cpp`. **Não rodei o simulador**: as contas abaixo são à mão e todo número derivado é **[HIPÓTESE]** até o Backend rodar as sementes pedidas em R2.1.4.

### R2.1 Por que o Guerreiro nível 4 sem equipamento recua em cerca de 1 minuto

**R2.1.1 O que o código e os CSV dizem (lido, não estimado).**

1. **Sem arma o herói causa 0 de dano.** `expedition.cpp` (linhas 75 a 78) só preenche `weaponDamage` se existir item em `equipment[MainHand]`. Os 4 golpes têm `scalesWithWeapon=true` e `baseDamage*` vazio; `ResolveHit` ignora tipos com base 0. Nenhum inimigo morre, o encontro só termina por recuo ou por estourar o orçamento. Com 156 de vida e 3 poções (3 x 62 = 187 de cura) o herói tem ~340 de "vida total" contra 2 a 16 de dano por segundo dos grupos (conta em R2.1.3): dá de 20 s a ~80 s, que é o "cerca de 1 minuto" do Backend. **Este caso não se resolve com número de balanceamento**: é falta de dano base desarmado (ver R2.5, pergunta ao Tech Lead). O resto desta seção trata do herói com a Espada de Ferro (`item_base.iron_sword`, 9 de dano), que é o mínimo para existir expedição.
2. **No idle todo inimigo do encontro ataca ao mesmo tempo, sem pausa.** O ciclo de cada inimigo é `windup+impact+recovery` e recomeça na hora (`EnemyAct`). O `attackTokens`=2 e o cerco de `enemy_ai.csv` não existem no simulador: 5 Cães mordem juntos, quando no jogo manual só 2 mordem por vez (docs/13 item 6.1).
3. **O Cão não é esquivável no idle** (`enemy_attacks.csv`: `telegraphed=false`), então `ai_base_dodge` 0,5 e as 3 cargas de esquiva só protegem contra Sentinela, Arauto e Arqueiro. O encontro de Cães é o de maior dano médio depois do Arauto e da Elite Escudada.
4. **`idleDamageTakenMult` é 1 nas 4 habilidades**, ou seja, o idle não tem nenhuma folga sobre o humano, e o humano esquiva mais que 50% e fica atrás de pilar. É a alavanca prevista em docs/13 item 8.2 (passo 3).
5. **A armadura agrava o problema pelo jeito que é calculada:** `redução = armadura / (armadura + 5 x dano)` aplicada ao dano do golpe. Sem elmo e calça o herói tem 26 de armadura (20 + 2 x 3 níveis; com elmo e calça, 38) e o golpe de 8 da Sentinela perde só 39% (4,85 de dano líquido).

**R2.1.2 Premissas da conta (todas [HIPÓTESE]).** Herói nível 4: vida 156 (120 + 12 x 3), regen 1,3/s, armadura 26, crítico 7% (5% base + 2% da espada), barra com os 4 golpes e a regra "poção de Vida se vida < 35%". Dano do Corte: 9 x 1,035 (crítico) = 9,3 bruto, ciclo de 0,53 s (0,45 s / `idleUptime` 0,85), 1,3 alvos por golpe, ~22 dps bruto; golpe de área e Investida dão a mesma ordem de grandeza e não mudam o resultado. Inimigos no nível 3 da Cripta (`maps.csv` `monsterLevel`=3): Sentinela vida 76 / armadura 10; Cão 50 / 0; Arauto 186 / 36; Arqueiro 45 / 0; Sentinela Escudada 152 / 31 + barreira 61; Cão Veloz 80 / 0. Esquiva efetiva contra golpes telegrafados ~40% (a IA acerta o sorteio de 50%, mas a recarga em série de 1,5 s limita a 0,67 esquivas por segundo). Ciclo de expedição: travessia média 6,2 s (pesos 3,2,2,1,2,1,1 de `encounters.csv`) + luta média 11,5 s = **17,7 s por encontro**.

**R2.1.3 Dano médio por encontro (herói com espada, sem armadura de equipamento).**

| Encontro | Peso | Luta | Dano recebido | % da vida (156) | O que pesa |
|---|---|---|---|---|---|
| `enc.crypt.patrol_a` | 3 | ~9,5 s | ~40 | 26% | 2 a 3 Sentinelas, 40% esquivadas |
| `enc.crypt.patrol_b` | 2 | ~9 s | ~27 | 17% | |
| `enc.crypt.hounds` | 2 | ~9 s | ~91 (3 Cães 53, 4 Cães 88, 5 Cães 132) | 58% (85% com 5) | todos mordem juntos, sem esquiva |
| `enc.crypt.herald` | 1 | ~19 s | ~150 | 96% | Arauto 186 de vida e armadura 36, golpe de 22; as Sentinelas ficam vivas até o fim |
| `enc.crypt.firing_line` | 2 | ~11,5 s | ~50 | 32% | |
| `enc.crypt.elite_shield` | 1 | ~20 s | ~100 | 64% | barreira 61 + vida 152 |
| `enc.crypt.elite_swift` | 1 | ~12 s | ~89 | 57% | |
| **Média ponderada** | 12 | 11,5 s | **~66** | 42% | |

**R2.1.4 Equilíbrio por ciclo de 17,7 s e tempo até o recuo.**

Ganho por ciclo = regen 1,3 x 17,7 = 23 + poção de Vida (62,4 / 40 s x 17,7 = 27,6) = **~51**. Dano médio = **~66**. Saldo = -15 por ciclo. Reserva antes de recuar = (156 - 39) de vida acima de 25% + 3 poções (187) = ~304. Tempo médio até recuar = reserva / |saldo| (passeio com deriva, conta grosseira):

| Caso | Dano/ciclo | Ganho/ciclo | Saldo | Tempo até recuar (antes) | Depois de m = 0,85 |
|---|---|---|---|---|---|
| Sem arma (0 de dano) | n/a | 51 | n/a | **20 a 80 s** (bate com o relato) | 30 a 110 s (não se resolve por número) |
| Espada, sem equipamento | 66 | 51 | -15 | **~6 min** | dano 52 (saldo -2): **~43 min** |
| Kit inicial (espada, elmo, peitoral, luvas, calça, botas: vida 168, armadura 38) | 55 | 53 | -2 | ~48 min | dano 43 (saldo +10): probabilidade de algum dia recuar ~1% |

Leitura: o problema real com o conteúdo atual é uma margem de ~0 (dano ≈ ganho), com variância alta (Arauto, bando de 5 Cães, Elite Escudada tiram 60 a 96% da vida de uma vez). Um encontro ruim sem poção disponível faz o herói recuar. Para uma expedição de 1 a 12 h (`min/max_expedition_hours`) o saldo precisa ser claramente positivo com o kit inicial.

**R2.1.5 Ajuste mínimo (uma mudança de dado, quatro células).**

`skills.csv`, coluna `idleDamageTakenMult`: **1 -> 0,85** em `skill.warrior.iron_cut`, `charge`, `stone_rift` e `shield_bash` (o simulador usa o multiplicador da habilidade em execução, então as 4 têm que ter o mesmo valor). Pela fórmula da armadura o dano líquido cai ~20% (não 15%): Sentinela 4,85 -> 3,85; Cão 3,21 -> 2,53; Arauto 17,8 -> 14,6. Justificativa de design, não de ajuste de sorte: (a) o simulador não aplica o limite de 2 atacantes dos Cães (vale ~8% do dano total); (b) o humano esquiva golpes que o idle chama de não esquiváveis (agacho do Cão de 0,3 s); (c) é o passo 3 já previsto em 8.2. Não toca o ritmo de abates, então a meta de 30 a 40% do manual (RF-32) não muda. **Critério de pronto (Backend roda 20 sementes de 1 h, antes e depois):** kit inicial, probabilidade de recuo em 1 h <= 10% e mediana sem recuo; só espada, mediana >= 30 min; sem arma, ver R2.5. Se o Kit inicial ficar sem nenhum recuo em 20 sementes de 4 h, a margem ficou grande demais para o pilar P3 e `m` sobe para 0,9.

**Alavancas descartadas.** `potion.life.fractionOfMaxLife` ou `rechargeSeconds`: são compartilhadas com a luta do Guardião (item 2 deste documento). `retreat_life_fraction` menor: só adia o recuo e passa a matar o herói no idle. Vida ou dano de inimigos: mexem no jogo manual e no chefe. Armadura do herói: é decisão de equipamento.

**Quando o simulador respeitar `attackTokens`** (pedido ao Tech Lead em R2.5), `m` pode subir para 0,92.

### R2.2 Números que estavam no código e passam a ser dado

| Número | Onde estava | Tabela | Coluna ou chave | Valor | Observação |
|---|---|---|---|---|---|
| Momento da invocação do Guardião (fração do rugido) | `kSummonAtFractionOfTransition` em `combat.cpp` | `boss_phases.csv` | `summonAtFraction` (nova, 0 < x < 1) | fase 2: **0,5** (1,0 s de 2,0 s, docs/13 item 4.4); fase 1: vazio | obrigatória quando `summonCount` > 0 |
| Stagger da Investida do Escudo que bate em pilar ou parede | só no texto (docs/13 item 4.3, [HIPÓTESE]) | `skills.csv` | `wallStaggerSeconds` (nova, s) | `skill.enemy.guardian_shield_charge`: **2,0**; vazio nas demais | a queda do escudo por 5 s já é `rules.csv` `boss_shield_down_seconds` (5). O valor sai do JSON de `docs/tecnico/14_layout_cripta.md` (`arenaCharge.wallStaggerSeconds`) para ter um dono só |
| Velocidade de patrulha | 0,5 da perseguição, no código | `enemies.csv` | `patrolSpeedMult` (nova) | `enemy.hollow_sentinel`: **0,5** (110 uu/s = 1,1 m/s, docs/14); vazio nos demais = não patrulha | só as Sentinelas patrulham (`patrol_a`, `patrol_b`); Sentinela Escudada fica parada |
| R-VIS-1: atirador só mira dentro da tela | só no texto (docs/14 8.2) | `enemy_ai.csv` | `requireOnScreen` (nova, bool) | `enemy.ghost_archer`: **true**; Cães: vazio (false) | |
| Margem interna da área visível de R-VIS-1 | 1 m no texto | `rules.csv` | `require_on_screen_margin` (nova, uu) | **100** | margem sobre o retângulo do frustum, medida na tela (ver docs/14 seção 8.2) |

### R2.3 Câmera com yaw de 45 graus (docs/14)

Correção em `docs/tecnico/14_layout_cripta.md`: seção 1 (eixos e retângulo visível), 8.2 (R-VIS-1 e R-VIS-3), 9 (itens 1 e 4), 10 (itens 1 e 3) e o bloco JSON. Resumo: o retângulo visível (±12,4 m na horizontal da tela, ±8,5 m na vertical) está **girado 45 graus em relação aos eixos do mundo**, então o limite no mundo é `|dx+dz| <= 12,0` e `|dx-dz| <= 17,5` (ou os dois trocados, conforme o sinal do yaw). Um critério que vale para os dois sinais: **`|dx| + |dz| <= 12,0 m`** cabe sempre na tela. Os arqueiros continuam a +-7,5 m da linha de chegada, mas deixam de ser posicionados para "acordar visíveis" (impossível com aggro 14 m); a garantia passa a ser só R-VIS-1.

### R2.4 Voltar ao checkpoint: reset total (confirmação da interpretação do Frontend)

**Confirmado, com um esclarecimento de escopo.** O dono decidiu "estilo Souls" (bloco "Checkpoint e arena" no topo deste documento). Em Souls o descanso na fogueira restaura todos os inimigos, mortos e vivos. A regra de design, que vale para voltar por morte, por saída e pelo portal:

1. **Todos os inimigos comuns e elites do mapa voltam ao estado de nascimento**, não só os da sala: vivos, com vida cheia, na posição de espaço (ou ponta inicial da patrulha), sem aggro e sem efeitos. O reset acontece durante o fade do teletransporte, fora da vista do jogador.
2. **A composição não é sorteada de novo:** mesma quantidade, mesmos elites e mesmos modificadores da primeira vez nesta visita ao mapa (evita jogar de novo só para sortear elite). Ela só muda ao sair do mapa e entrar de novo.
3. **Não reaparecem nem voltam:** o chefe vencido (fica morto até sair do mapa), baús abertos, o segredo aberto e o atalho A aberto. XP e itens nunca se perdem (plano seção 3).
4. **O chefe não vencido** volta à fase 1 com vida cheia (regra já existente de reset da luta) e a porta da arena reabre.
5. **XP:** os inimigos que reaparecem dão XP, sujeito ao limite `xp_cap_levels_above_area`. É o custo de uma regra simples e o motivo de o dono ter escolhido esse estilo; vigiar no playtest se vira farm fácil.

Efeito de design: os checkpoints passam a valer como pontos de poção cheia e de segurança, não como "limpar o mapa por partes". Isso aumenta o valor do atalho A e de CP3 (docs/14 seção 5). Não há número novo; é regra de estado do jogo manual (Tech Lead). O idle não usa checkpoint.

### R2.5 Pedidos fora de CSV

- **Tech Lead / Backend:** (1) decidir o dano desarmado. Proposta mínima: `rules.csv` `unarmed_weapon_damage_physical` = 3 e o core usar quando não houver arma; ou o fixture e o cliente nunca iniciam expedição sem arma. (2) Rodar as 20 sementes de R2.1.5 antes e depois. (3) Respeitar `attackTokens` do `enemy_ai.csv` no simulador (no máximo N atacantes de cada família por vez); então `m` = 0,92. (4) **Possível erro:** em `combat.cpp` `ComputeActionTiming`, `windupSpeed = speed / attackSpeedMult` ALONGA o telegraph do elite Veloz (0,3 s -> 0,375 s) em vez de mantê-lo; com `recoveryMult` 0,8 o ciclo do Cão Veloz fica igual ao do Cão comum (0,80 s). O texto do item 5 pede telegraph inalterado: usar `windup / speed`. (5) Ler as colunas novas de R2.2 e a regra de reset de R2.4. (6) Confirmar o sinal do yaw da câmera (+45 ou -45).
- **Frontend:** R-VIS-1 usa o frustum real da câmera (retângulo na tela menos `require_on_screen_margin`), não números fixos.

### Para o Data Engineer

1. `skills.csv`: `idleDamageTakenMult` = 0,85 em `skill.warrior.iron_cut`, `skill.warrior.charge`, `skill.warrior.stone_rift`, `skill.warrior.shield_bash` (era 1 nas quatro).
2. `skills.csv`: coluna nova `wallStaggerSeconds` (número, s, opcional); `skill.enemy.guardian_shield_charge` = 2,0; as demais linhas vazias.
3. `boss_phases.csv`: coluna nova `summonAtFraction` (0 < x < 1; obrigatória se `summonCount` > 0); `enemy.crypt_guardian` fase 2 = 0,5; fase 1 vazia. Validador: erro se `summonCount` > 0 e a coluna estiver vazia.
4. `enemies.csv`: coluna nova `patrolSpeedMult` (0 < x <= 1, opcional); `enemy.hollow_sentinel` = 0,5; todas as outras linhas vazias.
5. `enemy_ai.csv`: coluna nova `requireOnScreen` (bool, opcional); `enemy.ghost_archer` = true; Cães vazios.
6. `rules.csv`: chave nova `require_on_screen_margin` = 100 (uu).
7. Nada mais muda. Não mexer em `potions.csv`, `class_stats.csv` nem `retreat_life_fraction` (0,25). `unarmed_weapon_damage_physical` só entra se o Tech Lead aprovar R2.5 (1).
