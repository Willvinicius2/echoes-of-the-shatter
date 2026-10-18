# 19. Itens e habilidades do Ato I (Game Designer)

Data: 18/10/2026. Autor: Game Designer. Origem: o dono pediu "detalhar a parte de itens e de habilidades" e dar prosseguimento ao jogo. Este documento **não altera nenhum CSV, código ou outro doc**: as linhas de dados da seção 3 são proposta pronta para o Data Engineer aplicar, e a seção 4 lista o que o core precisa ler de novo (Backend e Tech Lead decidem o formato final).

A história é do dono. Nada aqui cria personagem, lugar ou lore: os nomes são **provisórios e funcionais**, vivem em chaves de Loc (`item_base.<id>.name`, `affix.<id>.name`, `unique.<id>.name`) e podem ser trocados sem tocar em regra. Os nomes de área (Estrada das Lanternas, Cripta Partida, Pedreira dos Ecos, Ponte do Sino) já estão no plano (`docs/00`, seção 3).

Tudo marcado `[HIPÓTESE]` precisa de playtest ou de simulação. Nenhum número vai para o código: tudo vira linha de CSV.

Fontes lidas: `CLAUDE.md`; `docs/00` (seções 4 e 6); `docs/02` (pilares, RF-26/27/43); `docs/03` (3.4, 3.11, 4.2); `docs/04` (17.4, 17.5); `docs/16` (4.5, 4.7, 11); `docs/18`; `ShatterCore` (`stats.h`, `loot.cpp`, `combat.cpp`, `inventory.cpp`, `content.cpp`, `effects.h`); os CSV da `master` e os da worktree `D:\openclaude\_trabalho-claude\wt\backend`, que já tem `basic_kits.csv`, as colunas `pierce` e `explosionRadius` e as linhas de Arqueiro e Mago. (Não consegui rodar `git show etapa3/combate-core` neste ambiente; a worktree `backend` é a cópia mais nova que achei. Conferir se ela é mesmo a ponta da branch.)

IDs deste documento: `IT-` (item), `AF-` (afixo), `UQ-` (Único), `H19-` (hipótese), `Q19-` (pergunta), `N` (necessidade do core). Não mudam depois de publicados.

---

## 0. Resumo e pilares

### 0.1 O que este documento decide

1. **Itens:** três degraus de equipamento no Ato I (inicial, reforçado, de placas) para as 3 classes, 4 armas por classe no máximo, um slot novo (`off_hand`: escudo, aljava, tomo), 18 afixos em 2 faixas de nível (T1 e T2), 3 Únicos novos (um por classe) e uma curva de drop que sobe pelo **nível da área**, não pela raridade.
2. **Habilidades:** tabela de desbloqueio e de rank por nível do herói, o que muda no rank 3 de cada habilidade, uma habilidade nova de slot R para o Arqueiro (Marca da Trilha) e outra para o Mago (Passagem Arcana), a sinergia dos afixos de arma com o kit e o que o simulador idle precisa ler.
3. **Dois achados que o dono precisa saber** (detalhe nas seções 1.3 e 4):
   - **`attackTime` da arma só aparece no tooltip.** Em combate o tempo do golpe vem da habilidade (`windup + impact + recovery`), então o Martelo de Pedra (16 de dano, "1,4 s") é hoje **78% mais forte que a Espada (9) sem ser mais lento**. É a necessidade **N0** (alta).
   - **O Arqueiro e o Mago não têm onde buscar item de classe.** As tabelas de loot não sabem a classe do herói (N1). Para o protótipo (só Guerreiro) isso não importa; antes de abrir as outras duas classes importa.

### 0.2 Fases de entrega

| Fase | Quando | O que entra | Core novo exigido |
|---|---|---|---|
| **F1** | Etapa 3 (Cripta, só Guerreiro) | Bases `iron_guard` do Guerreiro, escudo, calça e Martelo nas tabelas da Cripta; afixos universais e de Guerreiro; `off_hand` ligado | N0, N7 (pequenos) |
| **F2** | Etapa 4 (Arqueiro, Mago, Pedreira, Ponte) | Bases e afixos de Arqueiro e Mago, conjunto `stone_plate`, pool único de bases, 3 Únicos, ranks com perks, Marca e Passagem | N1 a N6, N8 a N11 |

Cada linha das tabelas da seção 3 traz a fase. **Onde a fase é F2, o dado fica pronto mas não deve ser aplicado antes do core.**

### 0.3 Pilares (de `docs/02`, seção 1) e o que cada parte serve

| Parte | Pilar | Por quê |
|---|---|---|
| Degraus de equipamento por nível de área | P2 Build com identidade; P4 Respeitar o tempo | O boneco muda já na 2ª ou 3ª corrida; 15 minutos de jogo trazem um item que se vê |
| Afixos de tempo (`cadence`), área (`reach`), crítico (`ruthless`, `cracked`) | P2 | Cada um muda **como** se joga o kit, não só o tamanho do número (seção 2.5) |
| `of_the_flask` (poção mais forte) | P3 Planejar o retorno | Poção forte é o que a regra de IA da expedição usa; o relatório pode recomendar a troca |
| Únicos de classe (escudo, arco, cajado) | P2; P1 | Cada um muda um **verbo** (bloquear, matar em sequência, acertar crítico) e custa algo; só caem jogando na mão |
| Rank 3 com perk | P1 Conquistar pela ação | O perk recompensa uso (nível), não sorte de livro |
| Marca da Trilha e Passagem Arcana | P2 | Preenchem o R vazio com uma decisão nova por classe |

Mecânica que não servir a pilar foi cortada: **não** proponho resistências a frio e raio nem afixos de dano elemental agora (nenhum inimigo do Ato I usa), nem armas de duas mãos (o Guerreiro tem escudo no `off_hand`).

### 0.4 Inspiração (tabelas obrigatórias)

| No jogo de referência | No nosso | Por quê |
|---|---|---|
| Diablo e Path of Exile: afixos em tiers (T1, T2...) liberados pelo nível do item | Dois tiers no Ato I; o tier vem do **nível da área** (`areaLevel` vira `itemLevel` do item); sem `T3` ainda | Uma única regra (nível da área) controla base, afixo e drop; menos tabelas |
| Diablo 4: "smart loot" (a maior parte do drop é da sua classe) | Bases têm classe; o drop só rola bases da classe do herói (N1) | Jogador solo com uma classe por save: item de outra classe é lixo, e lixo não é decisão |
| Path of Exile: Únicos com contrapartida | Cada Único novo tem 1 efeito que muda um verbo e 1 penalidade que o torna uma troca real | Plano, seção 6: "atributos fixos + 1 efeito que muda a build + 1 contrapartida" |
| Diablo e WoW: "Marca do Caçador" (alvo marcado sofre mais dano) | Marca da Trilha é um **tiro** com recarga **maior que a duração**, rank sobe a duração e o bônus | O jogador paga Foco e cadência de tiro para ter 80% de marca; vira decisão "marcar ou encher de flechas?" |
| Wizard do Diablo 3 e Flame Dash do PoE: teletransporte curto | Passagem Arcana é um salto de 500 uu com 0,3 s de invulnerabilidade e uma explosão **na chegada**; gasta a Mana que também alimenta a Barreira | A fuga vira ataque, mas disputa a mesma Mana da defesa do Mago |

---

## 1. Itens do Ato I

### 1.1 Princípios

1. **Três degraus de armadura** (`G0` inicial, `G1` reforçado, `G2` placas) e **dois de arma** (`W0`, `W1`) e de `off_hand` (`O0`, `O1`). O degrau vem da **janela de nível de área** da entrada de loot (`minAreaLevel`, `maxAreaLevel`, que o core já lê).
2. **A base tem classe** (proposta, N1). Armadura, arma e `off_hand` são da classe do herói. O visual do conjunto continua `vset.*` neutro; o catálogo de cada herói resolve a peça (`docs/04` 17.4).
3. **Cada degrau sobe cerca de um terço do poder do anterior** `[HIPÓTESE]`: a arma +33% em dano base, a armadura +60% no implícito. Mantém o tempo para matar de um inimigo comum perto de 3 s ao longo do Ato I (a vida de inimigo sobe ~20% de um nível de área para o próximo).
4. **O implícito é a identidade da peça**: o implícito do escudo é armadura, o da aljava é dano de projétil, o do tomo é Mana. O afixo é variação.
5. **Item de outro degrau nunca é lixo imediato**: janelas se sobrepõem (G1 vale da Cripta à Ponte), então o "reforçado" continua caindo quando o "placas" aparece.

### 1.2 Áreas e níveis

| Área (plano) | Níveis do herói | `areaLevel` (= `itemLevel` do item) | Degraus que caem | Afixos |
|---|---|---|---|---|
| Estrada das Lanternas | 1 a 2 | 2 `[HIPÓTESE]` | G0, W0, O0 | T1 |
| Cripta Partida | 2 a 4 | **3** (`maps.csv`) | G0 + G1, W0, O0 | T1 |
| Pedreira dos Ecos | 4 a 6 | 5 `[HIPÓTESE]` | G1 + G2, W1, O1 | T1 + T2 |
| Ponte do Sino | 6 a 7 | 6 `[HIPÓTESE]` | G1 + G2, W1, O1 | T1 + T2 |

`areaLevel` das duas últimas e da Estrada é proposta (os níveis do plano são faixas). O dono ou o Data fixa o número em `maps.csv`; o resto deste doc depende só das **janelas** `[1,4]`, `[3,7]`, `[5,999]`.

### 1.3 Bases por slot

Legenda: **Nível** é o `itemLevel` da base (ordena e sugere requisito; o nível que vale para afixo é o da área). **Dano** é `weaponDamagePhysical` (campo único; o CSV não tem mínimo e máximo). **DPS** é `dano / attackTime`, o que o tooltip mostra hoje. **Faixa por golpe do kit** é o dano de um acerto sem crítico e sem afixo, do golpe mais fraco (por exemplo `combo_2` ou a flecha do Leque) ao forte de carga máxima (`coeficiente × dano × heavyMaxMult`), rank 1. IDs com `=` já existem.

**Achado (N0).** `ComputeActionTiming` (`combat.cpp:161`) usa só a habilidade e a velocidade de ataque; `attackTime` é lido apenas em `inventory.cpp:66` (DPS do tooltip). Sem N0, o Martelo (16) bate 78% mais forte que a Espada (9) **sem custo de tempo**, e o Arco do Arqueiro (0,8 s) não é "mais rápido" de verdade. A correção proposta (N0): para as habilidades do kit básico (`lightChain` e `heavySkill`), a duração da ação é multiplicada por `refAttackTime / attackTime`, onde `refAttackTime` é o `attackTime` da arma inicial da classe. Com isso a espada e o arco iniciais ficam **exatamente como em `docs/18`** (fator 1,0), o Martelo fica 36% mais lento e a tabela abaixo passa a valer. As habilidades Q/E/R mantêm a própria duração.

#### 1.3.1 Armas (`main_hand`)

| ID | Nome (pt-BR provisório) | Classe | Nível | Implícito | Dano | `attackTime` | DPS tooltip | Faixa por golpe do kit | Janela de área | Fase |
|---|---|---|---|---|---|---|---|---|---|---|
| `item_base.iron_sword` = | Espada de Ferro | Guerreiro | 1 | crítico +2% | 9 | 0,9 | 10,0 | 9 a 32 | [1,4] | existente |
| `item_base.stone_maul` = | Martelo de Pedra | Guerreiro | 2 | nenhum | 16 | 1,4 | 11,4 | 16 a 58 | [1,4] | existente |
| `item_base.steel_sword` | Espada de Aço | Guerreiro | 4 | crítico +2% | 12 | 0,9 | 13,3 | 12 a 43 | [5,999] | F1 |
| `item_base.quarry_maul` | Martelo de Cantaria | Guerreiro | 5 | nenhum | 21 | 1,4 | 15,0 | 21 a 76 | [5,999] | F1 |
| `item_base.hunter_bow` = | Arco de Caçador | Arqueiro | 1 | crítico +2% | 8 | 0,8 | 10,0 | 5 a 24 | [1,4] | existente |
| `item_base.recurve_bow` | Arco Recurvo | Arqueiro | 4 | crítico +2% | 11 | 0,8 | 13,8 | 7 a 33 | [5,999] | F2 |
| `item_base.crystal_staff` | Cajado de Cristal | Mago | 1 | dano de feitiço +20% | 2 (nominal) | 1,0 | n/a | 10 a 48 | [1,4] | F2 |
| `item_base.runed_staff` | Cajado Rúnico | Mago | 4 | dano de feitiço +60% e velocidade de conjuração +4% | 3 (nominal) | 1,0 | n/a | 13 a 64 | [5,999] | F2 |

Intenções `[HIPÓTESE]`:

- **Espada contra Martelo** (já existe): a espada é a opção de ritmo (combo em 1,6 s, crítico +2%); o Martelo vence em dano por golpe e perde em ritmo. Com N0 o Martelo gasta 2,5 s por combo, mas cada golpe de fecho vale 27 de dano contra 15 da espada. O Guerreiro escolhe entre "sempre perto, sempre batendo" e "bate pouco e forte, empurra mais" (o empurrão dos golpes é fixo da habilidade, mas golpe lento é mais fácil de errar). `quarry_maul` repete a lógica um degrau acima.
- **Cajado:** o Mago não escala com arma (`scalesWithWeapon=false`). A arma dele dá **dano de feitiço aumentado** como implícito, para a progressão de poder acompanhar a do Guerreiro (+44% no dano base da espada de W0 para W1 equivale a +33% de multiplicador: 1,6 contra 1,2). O "dano nominal" 2 e 3 só existe porque o validador exige `weaponDamage > 0` e `weaponTags` igual a `melee` ou `projectile` (`content.cpp:1455-1460`). O tooltip do cajado **não pode mostrar DPS** (N8).
- **Arqueiro com uma linha só** (arco): a decisão do Arqueiro vem do afixo e da aljava, não de duas famílias de arma. Um arco longo lento (`attackTime` 1,2) fica para depois.
- **Faixa de dano do Mago** inclui o implícito do cajado: Dardo 8 × 1,2 = 9,6 e Bola de Fogo carga máxima 20 × 2 × 1,2 = 48 (cajado inicial); 12,8 e 64 com o rúnico.

#### 1.3.2 `off_hand` (slot novo)

O slot `off_hand` hoje está desligado (`rules.csv: equip_slot_off_hand,false`). A defesa do Guerreiro (botão direito) continua sendo do **kit**, não do item: tirar o escudo não tira a defesa, só o bônus de status. O herói **começa com o `off_hand` do degrau O0** (7 peças em vez de 6; muda A3-02 de `docs/16`).

| ID | Nome | Classe | Nível | Implícito | Janela | Fase |
|---|---|---|---|---|---|---|
| `item_base.wooden_shield` | Escudo de Madeira | Guerreiro | 1 | armadura +10 | [1,4] | F1 |
| `item_base.guard_shield` | Escudo de Guarda | Guerreiro | 4 | armadura +18, vida +12 | [5,999] | F2 |
| `item_base.leather_quiver` | Aljava de Couro | Arqueiro | 1 | dano de projétil +4% | [1,4] | F2 |
| `item_base.hunter_quiver` | Aljava de Caçador | Arqueiro | 4 | dano de projétil +8%, crítico +1% | [5,999] | F2 |
| `item_base.worn_tome` | Tomo Gasto | Mago | 1 | Mana máxima +10 | [1,4] | F2 |
| `item_base.scribe_tome` | Tomo de Escriba | Mago | 4 | Mana máxima +18, velocidade de conjuração +3% | [5,999] | F2 |

Por que não um slot só de escudo: cada classe ganha um segundo eixo de equipamento ligado ao **recurso** dela (armadura para quem aguenta golpe, projétil para quem atira, Mana para quem conjura).

#### 1.3.3 Armadura (`head`, `body`, `hands`, `legs`, `feet`)

Todos os valores são implícitos de uma linha, `[HIPÓTESE]`. Janelas: `G0` [1,4], `G1` [3,7], `G2` [5,999]. `vset`: G0 `vset.starter`, G1 `vset.iron_guard`, G2 `vset.stone_plate`. O nível de cada degrau é 1, 2 e 4.

**Guerreiro** (vida 120, armadura 20): o implícito protege e acelera.

| Slot | G0 (nível 1) | G1 (nível 2) | G2 (nível 4) |
|---|---|---|---|
| `head` | `iron_helm` = Elmo de Ferro, armadura +8 | `guard_helm` Elmo de Guarda, +14 | `plate_helm` Elmo de Placas, +22 |
| `body` | `leather_vest` = Peitoral de Couro, vida +12 | `guard_cuirass` Couraça de Guarda, +22 | `plate_cuirass` Couraça de Placas, +36 |
| `hands` | `leather_gloves` = Luvas de Couro, velocidade de ataque +3% | `guard_gauntlets` Manoplas de Guarda, +5% | `plate_gauntlets` Manoplas de Placas, +7% |
| `legs` | `worn_trousers` = Calça Gasta, armadura +4 | `guard_greaves` Grevas de Guarda, +8 | `plate_greaves` Grevas de Placas, +14 |
| `feet` | `worn_boots` = Botas Gastas, velocidade de movimento +5% | `guard_sabatons` Escarpes de Guarda, +6% | `plate_sabatons` Escarpes de Placas, +7% |

**Arqueiro** (vida 90, armadura 10, crítico 8%, anda a 470): o implícito favorece mobilidade e crítico.

| Slot | G0 | G1 | G2 |
|---|---|---|---|
| `head` | `hunter_hood` Capuz de Caçador, armadura +3 | `ranger_hood` Capuz de Batedor, armadura +5 e crítico +1% | `stalker_hood` Capuz de Rastreador, armadura +8 e crítico +1,5% |
| `body` | `hunter_jerkin` Gibão de Caçador, vida +10 | `ranger_jerkin` Gibão de Batedor, +18 | `stalker_jerkin` Gibão de Rastreador, +30 |
| `hands` | `hunter_bracers` Braçadeiras de Caçador, velocidade de ataque +3% | `ranger_bracers` Braçadeiras de Batedor, +5% | `stalker_bracers` Braçadeiras de Rastreador, +7% |
| `legs` | `hunter_breeches` Calças de Caçador, armadura +2 | `ranger_breeches` Calças de Batedor, +4 | `stalker_breeches` Calças de Rastreador, +7 |
| `feet` | `hunter_boots` Botas de Caçador, movimento +6% | `ranger_boots` Botas de Batedor, +8% | `stalker_boots` Botas de Rastreador, +10% |

**Mago** (vida 70, armadura 5, Mana 150, regeneração 5): o implícito é recurso e conjuração.

| Slot | G0 | G1 | G2 |
|---|---|---|---|
| `head` | `novice_hood` Capuz de Noviço, Mana +10 | `scholar_hood` Capuz de Estudioso, +16 | `adept_hood` Capuz de Adepto, +24 |
| `body` | `novice_robe` Túnica de Noviço, vida +8 | `scholar_robe` Túnica de Estudioso, +14 | `adept_robe` Túnica de Adepto, +24 |
| `hands` | `novice_wraps` Ataduras de Noviço, velocidade de conjuração +3% | `scholar_wraps` Ataduras de Estudioso, +5% | `adept_wraps` Ataduras de Adepto, +7% |
| `legs` | `novice_leggings` Calças de Noviço, regeneração de Mana +0,2/s | `scholar_leggings` Calças de Estudioso, +0,35/s | `adept_leggings` Calças de Adepto, +0,5/s |
| `feet` | `novice_shoes` Sapatos de Noviço, movimento +4% | `scholar_shoes` Sapatos de Estudioso, +5% | `adept_shoes` Sapatos de Adepto, +6% |

Soma de um conjunto completo, para conferir a escala `[HIPÓTESE]`: Guerreiro G0 = armadura 12, vida 12; G1 = armadura 22, vida 22; G2 = armadura 36, vida 36 (mais 5% a 7% de velocidade de ataque e movimento). Em G2 o Guerreiro de nível 6 tem ~210 de vida e ~66 de armadura contra ~170 e ~40 em G0. Mago: G2 dá +24 de Mana (+16%) e +0,5 de regeneração (+10%).

`resource` flat no `head` do Mago sobe a reserva, não a regeneração: o Mago que gasta Mana para ficar vivo (Barreira) compra sustentação.

### 1.4 Pool de afixos

**Regras do core que valem aqui** (`loot.cpp:186`): Mágico 1 a 2 afixos, Raro 3 a 4; no máximo 2 prefixos e 2 sufixos; um afixo por `group`; só entram afixos com `minItemLevel ≤ itemLevel`; o valor é sorteado uniforme na faixa; o peso decide a chance entre os candidatos do slot. **Tiers:** o T2 é uma linha nova com o mesmo `group` e `minItemLevel` 5; a partir da Pedreira o afixo sai 50% T1 e 50% T2 (mesmo peso). T3 (`minItemLevel` 9, faixa = T2 × 1,5) fica para as áreas seguintes e **não** está nas tabelas.

#### 1.4.1 Tabela de afixos

`Classe` vazio = todas. Os 2 afixos de arma **aprovados em Q3-5 A** não tinham definição no repositório; esta entrega usa `ruthless` (prefixo, multiplicador de crítico) e `of_cadence` (sufixo, recarga de habilidades). Se o Data já escolheu outros, o orquestrador reconcilia.

| ID | Tipo | Stat e modo | Tags | T1 (nível 1) | T2 (nível 5) | Peso | Slots | Classe | Grupo | Fase |
|---|---|---|---|---|---|---|---|---|---|---|
| `affix.sturdy` = | prefixo | vida flat | | 10 a 25 | 24 a 45 | 10 | todos os de armadura, `off_hand` | | `life` | F1 |
| `affix.plated` = | prefixo | armadura flat | | 5 a 12 | 11 a 22 | 10 | todos os de armadura, `off_hand` | | `armor` | F1 |
| `affix.resolute` | prefixo | vida aumentada | | 3% a 6% | 6% a 10% | 6 | todos os de armadura, `off_hand` | | `life_pct` | F1 |
| `affix.deep` | prefixo | recurso máximo flat | | 10 a 25 | 22 a 40 | 6 | `head`, `off_hand` | Arqueiro, Mago | `resource` | F2 |
| `affix.honed` = | prefixo | dano aumentado | `attack` | 8% a 15% | 14% a 24% | 10 | `main_hand` | Guerreiro, Arqueiro | `damage` | F1 |
| `affix.arcane` | prefixo | dano aumentado | `spell` | 8% a 15% | 14% a 24% | 10 | `main_hand` | Mago | `damage` | F2 |
| `affix.cracked` = | prefixo | chance de crítico flat | | 1% a 3% | 2,5% a 5% | 6 | `main_hand` | | `crit` | F1 |
| `affix.ruthless` (**aprovado**) | prefixo | multiplicador de crítico flat | | +0,15 a +0,35 | +0,30 a +0,60 | 6 | `main_hand` | | `crit_mult` | F1 |
| `affix.of_mending` = | sufixo | regeneração de vida flat | | 0,5 a 1,5 | 1,2 a 2,4 | 8 | todos os de armadura, `off_hand` | | `regen` | F1 |
| `affix.of_the_furnace` = | sufixo | resistência a fogo flat | | 5% a 15% | 12% a 25% | **5** (era 8) | todos os de armadura, `off_hand` | | `resist_fire` | F1 |
| `affix.of_the_flask` | sufixo | potência de poção aumentada | | 10% a 20% | 18% a 30% | 5 | `head`, `body`, `hands`, `legs`, `feet` | | `potion` | F1 |
| `affix.of_light_steps` = | sufixo | velocidade de movimento aumentada | | 3% a 7% | 6% a 11% | 6 | `feet` | | `move_speed` | F1 |
| `affix.of_swiftness` = | sufixo | velocidade de ataque aumentada | | 4% a 8% | 7% a 12% | 8 | `main_hand`, `hands` | Guerreiro, Arqueiro | `attack_speed` | F1 |
| `affix.of_the_channel` | sufixo | velocidade de conjuração aumentada | | 4% a 8% | 7% a 12% | 8 | `main_hand`, `hands` | Mago | `attack_speed` | F2 |
| `affix.of_cadence` (**aprovado**) | sufixo | recarga de habilidades aumentada | | 5% a 10% | 9% a 16% | 6 | `main_hand` | | `cooldown` | F1 |
| `affix.of_reach` | sufixo | área de efeito aumentada | | 5% a 10% | 9% a 16% | 5 | `main_hand` | | `area` | F1 |
| `affix.of_the_wall` | sufixo | chance de bloqueio flat | | 3% a 8% | 7% a 12% | 6 | `off_hand` | Guerreiro | `block` | F1 |
| `affix.of_the_spring` | sufixo | regeneração de recurso flat | | 0,4 a 1,0 | 0,9 a 1,6 | 6 | `off_hand`, `legs` | Arqueiro, Mago | `resource_regen` | F2 |

Intenções dos números `[HIPÓTESE]`:

- **Tamanho dos tiers.** T2 sobe cerca de 1,6 vez o T1, o mesmo passo da base (+33% a +60%). T1 máximo (15%) quase encontra T2 mínimo (14%) de propósito: o jogador não joga fora o item do degrau anterior por causa de um bom rolo.
- **`of_the_furnace` com peso 5.** Nenhum inimigo do Ato I causa dano de fogo. Resistência sem dano correspondente é afixo morto; peso menor evita que 1 em 4 afixos de armadura seja inútil até haver dano de fogo (Ato II).
- **`of_the_wall` (chance de bloqueio).** Dispara `on_block`, a mesma condição do Único `bulwark_shield` e do `resourceOnBlock` do Guerreiro (+15 Ímpeto). Teto em `block_cap` 0,5.
- **Crítico:** ver 2.5; o valor de EV do crítico no Ato I é baixo sem habilitador.
- **Armas dos dois lados.** Guerreiro e Arqueiro têm `honed` e `of_swiftness`; o Mago tem `arcane` e `of_the_channel`. Sem o filtro de classe (N2) cada classe rola afixo morto do outro lado. Em F1 (só Guerreiro) não há problema.

#### 1.4.2 Quem rola o quê, por slot

Combinações distintas de um Raro de 4 afixos (2 prefixos + 2 sufixos, sem ordem) é o que alimenta Reforjar e Adicionar afixo (`docs/16` 11.5). Meta: pelo menos 9 por slot.

| Slot | Prefixos | Sufixos | Raros de 4 afixos |
|---|---|---|---|
| `main_hand` (Guerreiro, Arqueiro) | `honed`, `cracked`, `ruthless` | `of_swiftness`, `of_cadence`, `of_reach` | 9 |
| `main_hand` (Mago) | `arcane`, `cracked`, `ruthless` | `of_the_channel`, `of_cadence`, `of_reach` | 9 |
| `off_hand` (Guerreiro) | `sturdy`, `plated`, `resolute` | `of_mending`, `of_the_furnace`, `of_the_wall` | 9 |
| `off_hand` (Arqueiro, Mago) | `sturdy`, `plated`, `resolute`, `deep` | `of_mending`, `of_the_furnace`, `of_the_spring` | 18 |
| `head` (Guerreiro) | `sturdy`, `plated`, `resolute` | `of_mending`, `of_the_furnace`, `of_the_flask` | 9 |
| `head` (Arqueiro, Mago) | + `deep` | igual | 18 |
| `body` | `sturdy`, `plated`, `resolute` | `of_mending`, `of_the_furnace`, `of_the_flask` | 9 |
| `hands` | `sturdy`, `plated`, `resolute` | `of_mending`, `of_the_furnace`, `of_the_flask`, `of_swiftness` (ou `of_the_channel` no Mago) | 18 |
| `legs` (Guerreiro) | `sturdy`, `plated`, `resolute` | `of_mending`, `of_the_furnace`, `of_the_flask` | 9 |
| `legs` (Arqueiro, Mago) | igual | + `of_the_spring` | 18 |
| `feet` | `sturdy`, `plated`, `resolute` | `of_mending`, `of_the_furnace`, `of_the_flask`, `of_light_steps` | 18 |

Hoje (8 afixos), `main_hand` de Raro tem 3 afixos possíveis e **sempre** os três (Q3-5). Com a tabela acima o Raro de arma deixa de ser determinístico.

### 1.5 Únicos do Ato I

Além do `unique.empty_throne_maul` (Guerreiro, Guardião, já existe). Os três são de classe diferente, para cada herói ter um Único novo; todos `idleSupported=false` (o simulador não modela `on_block`, `on_kill` nem `on_crit` em arma de Arqueiro e Mago; equipar um deles avisa "incompatível com expedição" em vez de fingir paridade). Todos são **fixos + 1 efeito + 1 contrapartida**, sem texto de sabor novo (o sabor é do dono).

| ID | Base | Classe | Atributos fixos | Efeito que muda o verbo | Contrapartida |
|---|---|---|---|---|---|
| `unique.bulwark_shield` | `item_base.guard_shield` | Guerreiro | armadura +40, vida +30 | **Cada golpe bloqueado dá +6% de dano corpo a corpo por 6 s, até 4 acúmulos** (×1,26 no máximo). `effect.unique.bulwark_stack` | Velocidade de ataque -10% |
| `unique.relentless_bow` | `item_base.recurve_bow` | Arqueiro | crítico +4% | **Cada morte dá +6% de dano de projétil e +3% de velocidade de movimento por 5 s, até 5 acúmulos** (×1,34 e +15%). `effect.unique.relentless_tempo` | Vida máxima -15% |
| `unique.cinder_staff` | `item_base.runed_staff` | Mago | dano de feitiço +20%, crítico +4% | **Cada crítico dá +15% de velocidade de conjuração e +15% de recarga por 3 s** (renova; recarga interna 0,5 s). `effect.unique.crit_surge` | Mana máxima -25% |

Por que muda uma decisão (não só um número):

- **Baluarte (Guerreiro).** Hoje o jogador esquiva ou defende. O Único paga **ficar na frente do golpe**: defender vale dano. A esquiva não empilha. A penalidade (-10% de ataque) encarece o combo e empurra o jogador para golpes pesados e Q/E/R, o que combina com a Fenda e a Escudada (ambas já têm recarga). É a pergunta "arrisco o aparo?" de `docs/18` com recompensa maior. Empilha também com a defesa perfeita (conta como bloqueio).
- **Arco do Ritmo (Arqueiro).** Premia **encadear mortes** (Chuva, Leque e Perfurante em grupo) e **andar**, o inverso da fantasia "pare para atirar" (Foco regenera parado). Custo: vida -15%, num herói que já tem 90. Os 0,25 s de recarga interna mínima (`trigger_icd_min`) significam que um Tiro Perfurante que mata 3 de uma vez dá **1 acúmulo**, não 3: decisão consciente para o Único não saturar em 1 disparo.
- **Cajado de Surto (Mago).** Constrói um laço: crítico acelera, acelerar produz mais tentativas de crítico. A penalidade de 25% de Mana (150 vira 112) faz o Mago cair no ritmo de regeneração em cerca de 8 s menos de combo contínuo. É uma build de crítico: precisa de `cracked` e `ruthless` para valer (seção 2.5).

Fontes: ver 1.7. Os três são `manualOnly` e nunca caem na expedição (RF-27).

Referência da tabela "No jogo de referência | No nosso | Por quê": ver 0.4, linha de Path of Exile.

### 1.6 Visual do item (`docs/03` 3.11 e `docs/04` 17.4)

#### 1.6.1 Tinta de raridade (regra do `docs/03` 3.11, aplicada ao Ato I)

| Peça | Normal | Mágico | Raro | Único |
|---|---|---|---|---|
| Armadura (`head`, `body`, `hands`, `legs`, `feet`) | cores pintadas | tinta azul `#6FA8FF` (força 0,70) e rim `#A9CBFF` **só na máscara B** | tinta dourada `#FFD24A` (0,85), rim `#FFE493`, emissão de acento 0,35 **só na máscara R** | malha própria; um traço `#FF8A2E` ≤ 4% da peça; sem tinta |
| Arma e `off_hand` | cores pintadas | rim `#A9CBFF` 0,65 | rim `#FFE493` 0,80 e acento emissivo 0,35 em runa ou ouro (máscara R), **sem tinta de cor** | malha própria por `uniqueId` |

A regra de arma (rim e acento, sem tinta) é a hipótese H3-15 de `docs/16`; **proponho oficializá-la**: metal e madeira não "tingem" sem parecer outro material, e a leitura vem do brilho. O Art Director confirma.

#### 1.6.2 Capuz na cor da classe (Arqueiro e Mago)

O capuz é o elemento de 1 bit da classe (`docs/03` 3.4 item 9): verde `#5FD04A` no Arqueiro, azul `#4A9CF0` no Mago. Regras do conjunto:

1. **O corpo do capuz nunca entra na máscara B.** A tinta de raridade só age em: franja de folhas e fitas (Arqueiro), pontas e bainha de pergaminho creme do lenço (Mago). Um `head` Raro tem franja dourada, **capuz continua verde ou azul**.
2. **Todo conjunto não Único mantém a matiz da classe dentro de ±30°.** `iron_guard` e `stone_plate` mudam acabamento (couro, fivela, metal, pano), não a cor-assinatura.
3. **Único de `head` pode redesenhar o capuz, nunca trocar a identidade** (bico de osso, capuz azul pontudo com rosto visível, pluma vermelha). Nenhum Único de `head` entra neste doc.
4. **O Guerreiro:** o elmo é metal (B vazia); a pluma vermelha fica fora da máscara. A raridade lê pela faixa do tabardo no `body` e na calça (B). Por isso um Guerreiro de capacete Raro **não parece diferente** a 88 px: o dono vê o Raro no peitoral e na calça. Aceito, e é o motivo de `plate_helm` pedir um detalhe de pano (nota do Art Director em 5.3).

#### 1.6.3 Conjuntos visuais (`visualSetId`)

Os IDs são neutros; o catálogo `SO_HeroPartCatalog_<Heroi>` resolve a peça para o herói. **Cada `vset.*` novo precisa ter peça para os 3 heróis** (teste de EditMode de `docs/04` 17.4); ver N10 e Q19-8.

| `vset` | Guerreiro | Arqueiro | Mago | Aparece em | Direção para o Art Director (sem lore) |
|---|---|---|---|---|---|
| `vset.starter` | aprovado (`mod_a01`) | aprovado (`mod_a02`) | aprovado (`mod_a03`) | início, G0 | folhas aprovadas |
| `vset.iron_guard` | 5 peças | 5 peças | 5 peças | G1: Cripta em diante | "reforçado": placa de ombro e gorjal (Guerreiro), couro com rebites e capuz com debrum de ferro (Arqueiro), túnica com cinto, ombreira de pano e debrum creme largo (Mago) |
| `vset.stone_plate` | 5 peças | 5 peças | 5 peças | G2: Pedreira e Ponte | "placas": peças mais volumosas, aço mais escuro e detalhe dourado (Guerreiro), couro com placas de osso (Arqueiro), manto cinza sobre os ombros (Mago) |

Cada peça nova declara máscara B e R (`docs/03` 3.11); cada conjunto precisa de B em pelo menos uma entre `head`, `body`, `legs`. Orçamento por peça em `docs/04` 17.4: `head` 500 a 900 triângulos, `body` 900 a 1.500, `hands` 300 a 500, `legs` 500 a 800, `feet` 300 a 500; arma, escudo, aljava e tomo ficam **fora** da soma (props).

`off_hand` não usa `visualSetId` (`docs/04`: só vale nos 5 slots visuais). O escudo usa o socket `shield_face` já previsto; a aljava e o tomo precisam de **sockets novos** (`back_quiver` nas costas, `hip_tome` na cintura), em 5.2.

#### 1.6.4 O que o dono vê em cada corrida (critério A3-11)

Com a F1, o Guerreiro troca de peça **sem esperar Raro**: 55% dos itens que a Cripta larga já são G1 (seção 1.7), então duas a três corridas trazem 2 ou 3 peças `iron_guard` visíveis. A tinta Mágica e Rara entra por cima e é rara (0,6 e 0,5 por corrida).

### 1.7 Curva de drop

**Desenho.** A raridade fica por **tipo de fonte** (comum, elite, chefe), como já está. A subida por área vem de **três alavancas que os dados já têm**: (1) a janela de nível de área da entrada de base, (2) o tier do afixo (`minItemLevel`) e (3) quais tabelas existem. Os inimigos do Ato I que se repetem (Sentinela, Cão-de-Cinza) usam a mesma `lootTableId` em qualquer área, então **o nível da área** é o que escolhe o degrau.

#### 1.7.1 Tabelas e raridade (Fervor desligado, jogo manual)

Pesos de raridade vêm de `loot_tables.csv` (Comum / Mágico / Raro, em pesos relativos; o Fervor dobra o peso do Raro). `P(item)` = `dropChance × peso do item / soma dos pesos`.

| Tabela | Quem usa | Sorteios | Chance | Comum / Mágico / Raro (peso) | Raridade final com Fervor | Fase |
|---|---|---|---|---|---|---|
| `loot.crypt.area` | cada encontro | 1 | 10% | 80 / 18 / 2 | só Ouro e Lascas | existente |
| `loot.crypt.common` | comum, Sentinela, Cão, Arqueiro Fantasma | 1 | 35% | 80 / 18 / 2 | 78% / 18% / 4% | existente |
| `loot.crypt.heavy` | Arauto de Pedra | 1 | 50% | 70 / 26 / 4 | 65% / 24% / 8% | **F2 (novo)** |
| `loot.crypt.elite` | elite | 2 | 60% | 50 / 40 / 10 | 45% / 36% / 18% | existente |
| `loot.act1.chest` | baús 01 a 03 da Cripta e das áreas | 1 | 50% | 60 / 35 / 5 | 56% / 33% / 9% | **F2 (novo)** |
| `loot.crypt.guardian` | Guardião | 2 | 100% | 0 / 60 / 40 | 0% / 43% / 57% | existente |
| `loot.bridge.boss` | Tecelã de Cascalho (Ponte do Sino) | 2 | 100% | 0 / 55 / 45 | 0% / 38% / 62% | **F2 (novo)** |
| `loot.pool.act1.gear` | sub-tabela de bases (todas as tabelas acima apontam para ela) | 1 | 100% | 0 / 0 / 0 (herda do chamador, N3) | herdada | **F2 (novo)** |

`loot.crypt.heavy` responde ao ponto 4 de `docs/16` 4.5 ("o Arauto, a luta mais cara, larga como comum"): 0,15 item por morte contra 0,07. Os baús ganham item porque `docs/16` 4.5 ponto 3 apontou que o desvio de risco só dava Ouro.

#### 1.7.2 Fatia de item e degrau por janela de área

Peso de cada degrau dentro do sorteio de base (dentro de uma classe; o filtro de classe vem de N1):

| Degrau | Janela de área | Peso (cada peça) | Cripta (area 3) | Pedreira (area 5) |
|---|---|---|---|---|
| Armadura G0 | [1,4] | 1,0 | 5 de 19,5 (26%) | fora |
| Armadura G1 | [3,7] | 2,0 | 10 (51%) | 10 de 30 (33%) |
| Armadura G2 | [5,999] | 2,5 | fora | 12,5 (42%) |
| Armas W0 | [1,4] | 1,5 cada (3,0 se a classe tem 1 linha) | 3 (15%) | fora |
| Armas W1 | [5,999] | 2,5 cada (5,0 se 1 linha) | fora | 5 (17%) |
| `off_hand` O0 / O1 | [1,4] / [5,999] | 1,5 / 2,5 | 1,5 (8%) | 2,5 (8%) |

**Para a F1** (Guerreiro, só Cripta, sem sub-tabela) os pesos entram direto nas três tabelas existentes, mantendo a fatia de item de `docs/16` (20, 28 e 24 de 100, 93 e 89):

| Tabela | Fatia de item | G0 (cada) | Espada | Martelo | Escudo O0 | G1 (cada) | Soma |
|---|---|---|---|---|---|---|---|
| `loot.crypt.common` | 20 | 1,0 (5 peças) | 1,5 | 1,0 (novo) | 1,5 | 2,2 | 20,0 |
| `loot.crypt.elite` | 28 | 1,2 (5 peças) | 1,5 | 3,0 | 2,0 | 3,0 | 27,5 |
| `loot.crypt.guardian` | 24 | 1,0 (5 peças) | 1,5 | 4,0 | 2,0 | 2,3 | 24,0 |

Resultado esperado `[HIPÓTESE]`: **55% dos itens de um comum e 55% dos de elite na Cripta já são G1**; o Martelo cai também de comum (pedido de `docs/16` 4.5 ponto 2); o Escudo e a Calça passam a cair (ponto 1).

#### 1.7.3 Expectativa por corrida e por área

Premissas `[HIPÓTESE]`: nenhuma contagem real de inimigos além da Cripta. Cripta usa os números de `docs/16` 4.5 e 11.9. As outras áreas usam um mix típico de área aberta. Valores são esperanças com Fervor (jogo manual), calculadas à mão com as tabelas da 1.7.1.

| Área | Mix por corrida | Itens | Mágicos | Raros | Único |
|---|---|---|---|---|---|
| Estrada | 12 comuns | 0,8 | 0,15 | 0,03 | nenhum |
| Cripta | 20 comuns, 2 elites, Guardião, 5 baús | 3,4 | 0,6 | 0,5 | Martelo do Trono Vazio: 1ª vitória garantida, depois 20% / pity 5 |
| Pedreira | 30 comuns, 3 elites, 2 Arautos | 3,5 | 0,84 | 0,30 | 3% por elite (Único de classe): ~9% por corrida |
| Ponte | 25 comuns, 3 elites, Tecelã | 4,1 | 1,0 | 0,50 | 3% por elite; Tecelã: 20% / pity 5 |

Leitura: a Pedreira (sem chefe) fica ~40% abaixo da Cripta em Raros, e a Ponte volta ao patamar porque tem chefe. O jogador não vê "menos loot" ao avançar porque o **degrau** sobe (G2, W1, T2); a raridade é a mesma. Se o playtest mostrar corrida vazia na Pedreira, subir `dropChance` de `loot.crypt.elite` de 60% para 70% antes de mexer em pesos.

#### 1.7.4 Únicos: de onde vêm

| Único | Fonte | Chance | Garantia | Condição |
|---|---|---|---|---|
| `unique.empty_throne_maul` | `loot.crypt.guardian` | 20% | 1ª vitória; pity 5 | existente |
| `unique.bulwark_shield` | `loot.crypt.elite` e `loot.bridge.boss` | 3% por elite; 20% no chefe | pity 5 só no chefe | só Guerreiro (N4), `areaLevel` ≥ 5, `manualOnly` |
| `unique.relentless_bow` | idem | idem | idem | só Arqueiro |
| `unique.cinder_staff` | idem | idem | idem | só Mago |

Isso muda duas regras que `docs/16` (RF-27, A3-05) escreveu para o protótipo: "Único só nas tabelas do Guardião" passa a "só em entrada `unique` com `manualOnly`" (o plano já diz "chefes e elites", `docs/00` seção 6). Ver Q19-6.

---

## 2. Habilidades

### 2.1 Barra e desbloqueio

Regra de barra de `docs/18`: clique esquerdo (kit) + Q + E + R = 4 ativas; botão direito é a defesa do kit. Em F2 o R do Arqueiro e do Mago deixa de ser vazio.

| Slot | Guerreiro | Arqueiro | Mago | `unlockLevel` | Rank 2 em | Rank 3 em |
|---|---|---|---|---|---|---|
| Kit (esquerdo: leve, leve, leve, forte) | Corte de Ferro, Golpe de Volta, Golpe de Fecho, Golpe Pesado | Disparo Reto, Flechas em Leque, Tiro Perfurante | Dardo Arcano, Orbe Arcano, Bola de Fogo | 1 | nível 5 | nível 9 |
| Q | `charge` Investida | `back_leap` Salto para Trás | `frost_nova` Nova de Gelo | 2 | 6 | 10 |
| E | `stone_rift` Fenda de Pedra | `arrow_rain` Chuva de Flechas | `arcane_ray` Raio Arcano | 3 | 7 | 11 |
| R | `shield_bash` Escudada | **`hunters_mark` Marca da Trilha (nova)** | **`arcane_passage` Passagem Arcana (nova)** | 4 | 8 | 12 |

**Regra de rank (provisória, até haver livro e Página).** O plano (`docs/00` seção 6) sobe rank por Páginas (livros repetidos), que ficou **fora** do protótipo (`docs/02` 2.2). Enquanto isso o rank vem do nível do herói: `rank 2 = unlockLevel + 4`, `rank 3 = unlockLevel + 8` (chaves de `rules.csv`, seção 3.7). Os golpes do kit sobem juntos (o rank do kit é o de `startingSkill`). O protótipo (nível máximo 6) chega a rank 2 no kit e na Investida; o Ato I completo (nível 15) tem tudo no rank 3 desde o nível 12. Quando os livros entrarem, a regra é trocada por Páginas sem mudar a tabela de perks.

### 2.2 Progressão por rank

**Princípio.** Rank 1 → 2: poder puro (+10% a +12,5% de coeficiente, já nos CSV), para o jogador sentir o ganho. Rank 3: o **mesmo** ganho de coeficiente **mais um perk que muda como se usa a habilidade**, nunca só número. Perk é uma lista de colunas de `skills.csv` que mudam (recarga, custo, raio, projéteis, perfuração, efeito); o mecanismo é uma tabela de sobrescrita por rank (N5, `skill_ranks.csv`).

| Habilidade (ID) | Coeficientes R1 / R2 / R3 | Perk de rank 3 | Decisão que o perk muda |
|---|---|---|---|
| Kit do Guerreiro (`combo_2`, `combo_3`, `heavy_slash`) | 1,1 / 1,2 / 1,3; 1,7 / 1,85 / 2,0; 1,8 / 2,0 / 2,2 | **`heavy_slash` atordoa comuns** (`guard_break` + `stun`) | O golpe forte vira controle de grupo contra Sentinela e Cão: segurar o botão passa a ser resposta, não só dano |
| `skill.warrior.charge` | 1,2 / 1,35 / 1,5 | Recarga 6 → 5 s e **aplica Quebra de Guarda** na chegada | A Investida abre o escudo do inimigo que a recebe: investir no Guardião e na Sentinela Escudada vale um acúmulo |
| `skill.warrior.stone_rift` | 0,9 / 1,0 / 1,1 | Raio 220 → 270 uu e custo 40 → 35 | Limpa grupo em corredor mais largo; encurta o espaço necessário |
| `skill.warrior.shield_bash` | 1,3 / 1,45 / 1,6 | Recarga 4 → 3 s e custo 25 → 20 | Quebra de Guarda e atordoamento ficam disponíveis a cada ciclo de combo |
| Kit do Arqueiro (`quick_shot`, `fan_shot`, `piercing_shot`) | 0,85 / 0,95 / 1,05; 0,65 / 0,7 / 0,75 por flecha; 1,5 / 1,65 / 1,8 | **Leque dispara 5 flechas em 40°** (era 3 em 28°); Perfurante custa 10 Foco (era 12) | O Leque deixa de ser "só de perto": 5 flechas a 40° acertam grupo a 300 uu; o jogador pode ficar um passo mais longe |
| `skill.archer.back_leap` | 1,2 / 1,3 / 1,4 | Recarga 6 → 4,5 s | O Salto vira ferramenta de ritmo, não só de fuga |
| `skill.archer.arrow_rain` | 1,8 / 2,0 / 2,2 | Raio 300 → 360 uu e custo 35 → 30 | Escapar da zona exige andar mais; a H18-09 (inimigo foge) melhora |
| `skill.archer.hunters_mark` (nova) | 0,6 / 0,7 / 0,8 | Rank 2: marca 10 s e +25%; rank 3: marca 12 s e +30%, recarga 10 → 8 s | Rank 3 mantém a marca no chefe o tempo todo; o Foco vira o limite |
| Kit do Mago (`arcane_dart`, `arcane_orb`, `fireball`) | 1,0 / 1,1 / 1,2; 1,4 / 1,55 / 1,7; 1,0 / 1,15 / 1,3 | **Orbe explode em 170 uu** (era 130) e **Bola de Fogo em 270 uu** (era 220) | Os dois golpes de área viram resposta a grupo maior |
| `skill.mage.frost_nova` | 1,0 / 1,15 / 1,3 | Raio 340 → 400 uu e lentidão forte (`effect.chill_r3`: -50% por 4,5 s) | Fecha o espaço em torno do Mago com mais folga; uma Nova segura 3 inimigos por quase 5 s |
| `skill.mage.arcane_ray` | 1,0 / 1,1 / 1,2 | Alcance 900 → 1100 uu e recarga 6 → 5 s | O Raio acerta a fila inteira de longe; dá para agendar de fora do alcance do Arqueiro Fantasma |
| `skill.mage.arcane_passage` (nova) | 0,8 / 0,9 / 1,0 | Recarga 10 → 8 s e **deixa o inimigo lento** (`effect.chill`) | A Passagem vira ferramenta de controle, não só de fuga |

Intenções `[HIPÓTESE]`:

- **Por que só o rank 3 tem perk.** O rank 2 chega aos níveis 5 a 8, dentro do protótipo; o jogador sente +10% sem ler tooltip. O rank 3 chega aos níveis 9 a 12, onde o jogador já tem hábitos: o perk os desafia.
- **Cada perk toca uma coluna que o afixo também toca.** Raio e área já são o que `of_reach` mexe; recarga é o que `of_cadence` mexe (2.5). Os afixos e o rank somam, e o piso de recarga é `cooldown_min` (0,1 s).
- **`heavy_slash` atordoante no rank 3** é o único perk que acrescenta efeito de controle ao kit de um clique. Atordoamento já tem limite (imunidade de elite, Arauto e chefe) e dura 0,8 s, então não vira controle infinito.

### 2.3 Habilidades novas (fichas)

#### Marca da Trilha (`skill.archer.hunters_mark`)

- **Dono:** Arqueiro. **Slot:** R.
- **Fantasia:** escolher o alvo que vai morrer e saber que cada flecha dali em diante vale mais.
- **Função no kit:** utilidade e dano em alvo único (preparação para chefe e elite).
- **Input:** R, mira no cursor (projétil em linha).
- **Mira:** skillshot em linha, alcance 1400 uu, projétil a 3000 uu/s.
- **Custo e recarga:** 20 Foco; 10 s (rank 3: 8 s).
- **Tempos:** preparação 150 ms | impacto 50 ms | recuperação 250 ms (total 0,45 s). Cancela na metade final da recuperação pela esquiva (regra global).
- **Efeito:** o projétil causa 0,6 do dano da arma (físico) e aplica `effect.hunter_mark` ao primeiro alvo atingido: **dano recebido +20% por 8 s**, renovado ao reaplicar; rank 2 `effect.hunter_mark_r2` (+25%, 10 s); rank 3 `effect.hunter_mark_r3` (+30%, 12 s). Soma com Quebra de Guarda (ambos usam `damage_taken` aumentado, aditivo).
- **Escala:** coeficiente 0,6 / 0,7 / 0,8 do rank; a marca é o ganho principal.
- **Interações:** Tiro Perfurante e Chuva de Flechas contra um grupo ganham valor quando o alvo marcado está dentro da linha ou da zona. Com o Único `relentless_bow`, matar o marcado dá acúmulo igual a qualquer morte. `of_cadence` aproxima a marca de 100% de presença.
- **Counterplay (o que limita o jogador):** a marca **não cobre o tempo todo no rank 1** (8 s de efeito para 10 s de recarga: 80%); custa 20 dos 100 Foco; **a marca não pula para outro alvo** quando o marcado morre; um segundo disparo sobre alvo já marcado só renova. O jogador marca o chefe e não marca o comum. Não existe resposta do inimigo (a marca não é dissipável nesta versão).
- **Telegraph (para o alvo):** não se aplica; a marca é leitura para o jogador.
- **Spec audiovisual:**
  - Animação: `Ranged_Bow_Draw` mais lenta que o Disparo Reto, `Ranged_Bow_Release`; a antecipação de 150 ms é visível.
  - VFX: flecha com ponta clara (ácido `#E6FF8A` / `#8FD43A` / `#3E7A1E`); no acerto, anel fino de 60 cm no chão do alvo e um glifo de 30 cm acima da cabeça em `#8FD43A` alfa 0,75 durante toda a marca; o anel **encolhe** nos últimos 2 s (aviso de fim). Nunca vermelho (reservado para ameaça).
  - SFX: corda seca na saída; "toc" metálico no acerto; um tom ascendente curto; no fim da marca, um "pip" grave.
  - Feedback: flash branco de 80 ms no alvo; sem tremor; número de dano normal.
- **Hipóteses:** `[HIPÓTESE]` 80% de presença no rank 1 deixa a decisão "marcar agora?" viva; no rank 3 (12 s para 8 s de recarga) a presença é 100% e o custo de Foco vira o limite; H19-05.

#### Passagem Arcana (`skill.mage.arcane_passage`)

- **Dono:** Mago. **Slot:** R.
- **Fantasia:** sumir do lugar errado e reaparecer onde o inimigo não esperava, deixando um estalo.
- **Função no kit:** mobilidade e defesa; dano curto de chegada.
- **Input:** R, direção do cursor.
- **Mira:** direção do cursor, alcance 500 uu (o salto cabe em uma esquiva e meia); termina antes de parede (comportamento de `dash`).
- **Custo e recarga:** 25 Mana; 10 s (rank 3: 8 s).
- **Tempos:** preparação 50 ms | impacto 100 ms | recuperação 200 ms (total 0,35 s).
- **Efeito:** o herói se move 500 uu com `effect.arcane_phase` (**dano recebido -100% por 0,3 s**); na chegada, explosão de raio 160 uu que causa 10 de dano de raio × coeficiente 0,8 (0,9 / 1,0) e empurra 100 uu. No rank 3 a explosão aplica `effect.chill` (-40% por 3 s).
- **Escala:** coeficiente; o dano de base (10) não depende de arma.
- **Interações:** Nova de Gelo logo antes ou depois: a Nova prende e a Passagem escapa; o Raio Arcano pede 0,35 s de preparação parado, e a Passagem cobre esse risco. A Barreira Arcana drena a mesma Mana: **o jogador escolhe entre 25 Mana de fuga e ~25 pontos de dano absorvido**.
- **Counterplay (o que limita o jogador):** 10 s de recarga é longo comparado à esquiva (3 cargas, 1,5 s); 25 Mana são 17% da reserva; a Passagem **não passa por parede**; a invulnerabilidade é só 0,3 s: um telegraph que dura mais que isso exige sair do alcance, não "atravessar" o golpe.
- **Telegraph:** não se aplica (habilidade do jogador).
- **Spec audiovisual:**
  - Animação: `Ranged_Magic_Summon` encurtado na saída (50 ms); o herói some; reaparece na chegada em `Ranged_Magic_Raise` por 200 ms.
  - VFX: paleta de raio (`#F2F6FF` / `#7FA8FF` / `#3A4FB8`); saída com resíduo (cópia translúcida do herói por 250 ms) e um anel de 60 cm no chão; chegada com onda de 160 uu em 250 ms e 3 faíscas de sombra `#9A4BD6`. Durante os 0,3 s o corpo fica a 40% de alfa. Legível sobre o chão da Cripta; alfa máximo 0,75.
  - SFX: "zip" elétrico curto na saída; estalo grave na chegada.
  - Feedback: hitstop 40 ms só se a chegada acerta 3 ou mais inimigos; sem tremor.
- **Hipóteses:** `[HIPÓTESE]` 0,3 s de invulnerabilidade cobre o telegraph de 0,7 s da Sentinela apenas se o jogador apertar R durante o último terço do aviso; H19-06 mede quantas Passagens "salvam" um golpe.

### 2.4 Defesa e outros ajustes do kit

Nada muda na defesa (botão direito). O `off_hand` do Guerreiro não altera a defesa: o escudo item só soma status e é gancho do Único Baluarte. O Arqueiro e o Mago equipam aljava e tomo sem efeito na defesa.

### 2.5 Sinergia dos afixos de arma com o kit

O que cada afixo muda em **como o jogador age**, e o ganho aproximado `[HIPÓTESE]` (T1 médio; entre parênteses o T2 máximo). Contas em cima de `docs/18` (coeficientes) e dos CSV.

| Afixo | Guerreiro | Arqueiro | Mago | O que muda na decisão |
|---|---|---|---|---|
| `honed` / `arcane` (+8% a 15% de dano) | Soma em todos os golpes, inclusive Q, E e R | Idem | `arcane` soma em Dardo, Orbe, Bola de Fogo, Nova, Raio (`spell`) | É a escolha segura e a **linha de base**: +15% de dano (+24% em T2) é o que os outros afixos precisam alcançar |
| `cracked` (+1% a 3% crítico) | Crítico base 7% (5% classe + 2% espada) vira 10% | Base 10% (8% + 2%) vira 13%; o **Leque** (3 flechas) e a **Chuva** testam crítico em cada acerto | Base 5% vira 8% | Mais acertos por golpe = mais testes de crítico; sozinho vale pouco |
| `ruthless` (+0,15 a +0,35 no multiplicador) | Crítico do **Golpe Pesado em carga máxima** sai de 3,6 × 1,5 = 5,4 para 3,6 × 1,85 = 6,7 de coeficiente | Perfurante em carga máxima: 3,0 × 1,85 = 5,6 | Bola de Fogo em carga máxima: 40 × 1,85 | Recompensa **carregar até o fim** (o auto-solta de `docs/18`) e o Raio Arcano (já tem 0,35 s de preparação visível): é o afixo de quem arrisca |
| `of_swiftness` / `of_the_channel` (+4% a 8% de velocidade) | Combo de 1,63 s cai para 1,51 s (-0,12 s) com 8%; o Q/E/R também encurta (a recarga não) | Disparo Reto de 0,35 s vai a 0,32 s; o Leque de 0,55 s a 0,51 s | Raio: preparação 0,35 s vai a 0,32 s | Mais ciclos de combo por segundo = mais Ímpeto no Guerreiro, mais Foco gasto no Arqueiro; faz **a janela de defesa perfeita caber** no ritmo |
| `of_cadence` (+5% a 10% de recarga) | Fenda 5 s → 4,5 s; Escudada 4 s → 3,6 s; Investida 6 s → 5,5 s | Salto 6 → 5,5 s; Chuva 8 → 7,3 s; **Marca 10 → 9,1 s** (presença de 80% a 88%) | Nova 7 → 6,4 s; Raio 6 → 5,5 s; Passagem 10 → 9,1 s | Não rende dano contínuo no alvo único (o combo já é 2,3 de coeficiente por segundo e as habilidades gastam tempo de ação); rende **utilidade mais disponível**: Quebra de Guarda a cada 3 s e mais Salto. É a arma de quem joga o kit inteiro |
| `of_reach` (+5% a 10% de área) | Fenda 220 → 242 uu (+21% de área); Investida e Escudada não mudam | Chuva 300 → 330 uu; Leque não muda | Nova 340 → 374 uu; Orbe 130 → 143; Bola de Fogo 220 → 242 | Só vale para habilidades de **área**; um jogador de combo puro não o quer. É a escolha de quem enfrenta grupo (Pedreira, Ponte) |

**Alerta de balanceamento (H19-01).** Com esses números o crítico perde para `honed` em quase todo cenário do Ato I:

| Cenário (Guerreiro, T2 máximo) | Ganho de dano médio |
|---|---|
| `honed` T2 (+24%) | +24% |
| `cracked` T2 (+5%) + `ruthless` T2 (+0,60), crítico base 7% | crítico 12% e multiplicador 2,1: 1 + 0,12 × 1,1 = 1,13 contra 1,035 (+9%) |
| mesmo, Arqueiro (crítico 10% + arco 2%, + `relentless_bow` 4%) | crítico 21% e multiplicador 2,1: 1,23 contra 1,06 (+16%) |

Ou seja, **dois afixos de crítico valem menos que um `honed`**. Isso é aceitável como regra (o dano puro é a linha segura e o crítico precisa de habilitador), mas fere o pilar P2 se o jogador sempre acaba com `honed` e `swiftness`. Os habilitadores previstos são o Único do Mago, a Marca (que não dá crítico, mas fecha o dano no chefe) e, a definir, nós de árvore passiva. Alternativas em Q19-9.

### 2.6 Tags e campos que o idle precisa

O simulador (`expedition.cpp`) já usa `StatBlock` com as mesmas tags do combate, então afixos e Únicos de stat (`cooldown_recovery`, `area_of_effect`, crítico) **entram sem trabalho extra**. O que falta para as habilidades novas:

1. **Nenhuma tag nova.** O conjunto fechado de 9 tags (`attack`, `spell`, `melee`, `projectile`, `area`, `fire`, `cold`, `lightning`, `physical`) cobre as 5 habilidades novas e as 13 de `docs/18`. O que o idle lê de cada tag: `melee` (tempo de aproximação), `projectile` (sem aproximação; usa alcance), `area` (fração do grupo atingida), `spell` contra `attack` (qual velocidade usa: conjuração ou ataque), tipo de dano (resistência do alvo).
2. **Habilidades no R.** `IsIdleCompatible` hoje olha o R do Guerreiro. Marca e Passagem entram na regra; sem perfil elas **bloqueiam a expedição** (RF-43). Proponho: `hunters_mark` com perfil de utilidade (aplica o efeito no primeiro inimigo de cada encontro, sem dano relevante); `arcane_passage` com **perfil nulo** (`idleSupported=true`, sem alvos), isto é, o simulador **ignora** a habilidade em vez de bloquear. O validador atual pode recusar `idleAvgTargetsHit=0`; ver N11.
3. **Recurso.** Foco e Mana são limitantes: o simulador precisa de `resource_regen` e `regenMultWhileMoving` (o campo `idleUptime` representa o tempo parado) para decidir quando atirar. O core lê o regime do Foco em `class.archer.regenMultWhileMoving` (0,3); falta confirmar que o simulador o aplica (nota 7 do Backend em `docs/18`).
4. **Gatilhos de Único (`on_block`, `on_kill`, `on_crit`).** O simulador não os modela; por isso os 3 Únicos novos têm `idleSupported=false`. O efeito do maul (`on_kill`) já aparece em `manual_estimate`.
5. **Perfis propostos para a Etapa 4** (todos `idleCalibration=manual_estimate`, `idleParitySampleSize=20`, `[HIPÓTESE]` até o teste de paridade; as habilidades de Arqueiro e Mago continuam `idleSupported=false` no protótipo, Q18-2):

| Habilidade | `idleAvgTargetsHit` | `idleFractionOfGroupHit` | `idleApproachTime` | `idleUptime` | `idleDamageTakenMult` | Por quê |
|---|---|---|---|---|---|---|
| `quick_shot` | 1,0 | 0 | 0 | 0,75 | 0,70 | Atira de longe, mas precisa reposicionar; leva menos dano que o Guerreiro (0,80) por kitar |
| `arrow_rain` | 2,5 | 0,6 | 0 | 0,80 | 0,70 | Área grande, pode errar o inimigo que anda |
| `piercing_shot` | 2,0 | 0 | 0 | 0,75 | 0,70 | Linha: acerta em média 2 |
| `hunters_mark` | 1,0 | 0 | 0 | 0,80 | 0,70 | Perfil de utilidade: aplica efeito, dano baixo |
| `arcane_dart` | 1,0 | 0 | 0 | 0,90 | 0,75 | Mago fica parado e conjura |
| `frost_nova` | 3,0 | 0,7 | 0 | 0,85 | 0,75 | Área em torno do herói |
| `arcane_ray` | 2,0 | 0 | 0 | 0,85 | 0,75 | Linha |
| `arcane_passage` | 0 | 0 | 0 | 0 | 1 | Perfil nulo (ignorada) |

---

## 3. Tabelas exatas de dados

Todas as linhas são `[HIPÓTESE]`. Colunas iguais às atuais (`item_bases.csv`, `affixes.csv`, `uniques.csv`, `loot_tables.csv`, `loot_entries.csv`, `skills.csv` com 39 campos da worktree `backend`). Número com ponto decimal. A coluna de fase (F1 ou F2) é comentário, **não** coluna do CSV. Onde diz "alterada", a linha existente é substituída.

### 3.1 `item_bases.csv`

Cabeçalho: `id,slot,itemLevel,implicitMods,weaponDamagePhysical,weaponDamageFire,weaponDamageCold,weaponDamageLightning,attackTime,weaponTags,grammaticalGender,visualSetId`

**F1 (Guerreiro, Etapa 3):**

```csv
item_base.steel_sword,main_hand,4,crit_chance:flat:0.02,12,,,,0.9,melee,f,
item_base.quarry_maul,main_hand,5,,21,,,,1.4,melee,m,
item_base.wooden_shield,off_hand,1,armor:flat:10,,,,,,,m,
item_base.guard_helm,head,2,armor:flat:14,,,,,,,m,vset.iron_guard
item_base.guard_cuirass,body,2,life:flat:22,,,,,,,f,vset.iron_guard
item_base.guard_gauntlets,hands,2,attack_speed:increased:0.05,,,,,,,f,vset.iron_guard
item_base.guard_greaves,legs,2,armor:flat:8,,,,,,,f,vset.iron_guard
item_base.guard_sabatons,feet,2,move_speed:increased:0.06,,,,,,,m,vset.iron_guard
item_base.guard_shield,off_hand,4,armor:flat:18|life:flat:12,,,,,,,m,
item_base.plate_helm,head,4,armor:flat:22,,,,,,,m,vset.stone_plate
item_base.plate_cuirass,body,4,life:flat:36,,,,,,,f,vset.stone_plate
item_base.plate_gauntlets,hands,4,attack_speed:increased:0.07,,,,,,,f,vset.stone_plate
item_base.plate_greaves,legs,4,armor:flat:14,,,,,,,f,vset.stone_plate
item_base.plate_sabatons,feet,4,move_speed:increased:0.07,,,,,,,m,vset.stone_plate
```

(As cinco `plate_*` e o `guard_shield` e o `steel_sword`/`quarry_maul` ficam no CSV na F1 mesmo que só cheguem ao drop na Pedreira, para o teste de cobertura de `vset` e os ícones não esperarem a F2. Eles só caem quando houver entrada de loot, 3.5.)

**F2 (Arqueiro e Mago; exigem N1 para o drop e N8 para o cajado):**

```csv
item_base.recurve_bow,main_hand,4,crit_chance:flat:0.02,11,,,,0.8,projectile,m,
item_base.crystal_staff,main_hand,1,damage:increased:0.2:spell,2,,,,1,projectile,m,
item_base.runed_staff,main_hand,4,damage:increased:0.6:spell|cast_speed:increased:0.04,3,,,,1,projectile,m,
item_base.leather_quiver,off_hand,1,damage:increased:0.04:projectile,,,,,,,f,
item_base.hunter_quiver,off_hand,4,damage:increased:0.08:projectile|crit_chance:flat:0.01,,,,,,,f,
item_base.worn_tome,off_hand,1,resource:flat:10,,,,,,,m,
item_base.scribe_tome,off_hand,4,resource:flat:18|cast_speed:increased:0.03,,,,,,,m,
item_base.hunter_hood,head,1,armor:flat:3,,,,,,,m,vset.starter
item_base.hunter_jerkin,body,1,life:flat:10,,,,,,,m,vset.starter
item_base.hunter_bracers,hands,1,attack_speed:increased:0.03,,,,,,,f,vset.starter
item_base.hunter_breeches,legs,1,armor:flat:2,,,,,,,f,vset.starter
item_base.hunter_boots,feet,1,move_speed:increased:0.06,,,,,,,f,vset.starter
item_base.ranger_hood,head,2,armor:flat:5|crit_chance:flat:0.01,,,,,,,m,vset.iron_guard
item_base.ranger_jerkin,body,2,life:flat:18,,,,,,,m,vset.iron_guard
item_base.ranger_bracers,hands,2,attack_speed:increased:0.05,,,,,,,f,vset.iron_guard
item_base.ranger_breeches,legs,2,armor:flat:4,,,,,,,f,vset.iron_guard
item_base.ranger_boots,feet,2,move_speed:increased:0.08,,,,,,,f,vset.iron_guard
item_base.stalker_hood,head,4,armor:flat:8|crit_chance:flat:0.015,,,,,,,m,vset.stone_plate
item_base.stalker_jerkin,body,4,life:flat:30,,,,,,,m,vset.stone_plate
item_base.stalker_bracers,hands,4,attack_speed:increased:0.07,,,,,,,f,vset.stone_plate
item_base.stalker_breeches,legs,4,armor:flat:7,,,,,,,f,vset.stone_plate
item_base.stalker_boots,feet,4,move_speed:increased:0.1,,,,,,,f,vset.stone_plate
item_base.novice_hood,head,1,resource:flat:10,,,,,,,m,vset.starter
item_base.novice_robe,body,1,life:flat:8,,,,,,,f,vset.starter
item_base.novice_wraps,hands,1,cast_speed:increased:0.03,,,,,,,f,vset.starter
item_base.novice_leggings,legs,1,resource_regen:flat:0.2,,,,,,,f,vset.starter
item_base.novice_shoes,feet,1,move_speed:increased:0.04,,,,,,,m,vset.starter
item_base.scholar_hood,head,2,resource:flat:16,,,,,,,m,vset.iron_guard
item_base.scholar_robe,body,2,life:flat:14,,,,,,,f,vset.iron_guard
item_base.scholar_wraps,hands,2,cast_speed:increased:0.05,,,,,,,f,vset.iron_guard
item_base.scholar_leggings,legs,2,resource_regen:flat:0.35,,,,,,,f,vset.iron_guard
item_base.scholar_shoes,feet,2,move_speed:increased:0.05,,,,,,,m,vset.iron_guard
item_base.adept_hood,head,4,resource:flat:24,,,,,,,m,vset.stone_plate
item_base.adept_robe,body,4,life:flat:24,,,,,,,f,vset.stone_plate
item_base.adept_wraps,hands,4,cast_speed:increased:0.07,,,,,,,f,vset.stone_plate
item_base.adept_leggings,legs,4,resource_regen:flat:0.5,,,,,,,f,vset.stone_plate
item_base.adept_shoes,feet,4,move_speed:increased:0.06,,,,,,,m,vset.stone_plate
```

Nenhuma linha existente é alterada (`iron_sword`, `stone_maul`, `iron_helm`, `leather_vest`, `leather_gloves`, `worn_boots`, `worn_trousers`, `hunter_bow` ficam como estão). Estes `weaponDamagePhysical` de cajado (2 e 3) são nominais (1.3.1).

**Coluna proposta para N1 (não está no CSV atual):** `classId` por base. Valores: `class.warrior` para `iron_sword`, `stone_maul`, `steel_sword`, `quarry_maul`, `wooden_shield`, `guard_shield`, `iron_helm`, `leather_vest`, `leather_gloves`, `worn_boots`, `worn_trousers`, `guard_*`, `plate_*`; `class.archer` para `hunter_bow`, `recurve_bow`, `leather_quiver`, `hunter_quiver`, `hunter_*`, `ranger_*`, `stalker_*`; `class.mage` para `crystal_staff`, `runed_staff`, `worn_tome`, `scribe_tome`, `novice_*`, `scholar_*`, `adept_*`.

### 3.2 `affixes.csv`

Cabeçalho: `id,kind,stat,modKind,requiredTags,minValue,maxValue,minItemLevel,weight,allowedSlots,group,craftInscription`

**Linhas alteradas** (as 8 existentes; mudam `craftInscription` para `true` conforme `docs/16` 11.8, `allowedSlots` com `off_hand` onde indicado e o peso de `of_the_furnace`):

```csv
affix.sturdy,prefix,life,flat,,10,25,1,10,head|body|hands|legs|feet|off_hand,life,true
affix.honed,prefix,damage,increased,attack,0.08,0.15,1,10,main_hand,damage,true
affix.plated,prefix,armor,flat,,5,12,1,10,head|body|hands|legs|feet|off_hand,armor,true
affix.cracked,prefix,crit_chance,flat,,0.01,0.03,1,6,main_hand,crit,true
affix.of_mending,suffix,life_regen,flat,,0.5,1.5,1,8,head|body|hands|legs|feet|off_hand,regen,true
affix.of_swiftness,suffix,attack_speed,increased,,0.04,0.08,1,8,main_hand|hands,attack_speed,true
affix.of_the_furnace,suffix,resist_fire,flat,,0.05,0.15,1,5,head|body|hands|legs|feet|off_hand,resist_fire,true
affix.of_light_steps,suffix,move_speed,increased,,0.03,0.07,1,6,feet,move_speed,true
```

**Linhas novas, T1, F1:**

```csv
affix.ruthless,prefix,crit_multiplier,flat,,0.15,0.35,1,6,main_hand,crit_mult,true
affix.of_cadence,suffix,cooldown_recovery,increased,,0.05,0.1,1,6,main_hand,cooldown,true
affix.of_reach,suffix,area_of_effect,increased,,0.05,0.1,1,5,main_hand,area,true
affix.resolute,prefix,life,increased,,0.03,0.06,1,6,head|body|hands|legs|feet|off_hand,life_pct,true
affix.of_the_flask,suffix,potion_effect,increased,,0.1,0.2,1,5,head|body|hands|legs|feet,potion,true
affix.of_the_wall,suffix,block_chance,flat,,0.03,0.08,1,6,off_hand,block,true
```

**Linhas novas, T1, F2 (exigem o filtro de classe, N2):**

```csv
affix.arcane,prefix,damage,increased,spell,0.08,0.15,1,10,main_hand,damage,true
affix.of_the_channel,suffix,cast_speed,increased,,0.04,0.08,1,8,main_hand|hands,attack_speed,true
affix.deep,prefix,resource,flat,,10,25,1,6,head|off_hand,resource,true
affix.of_the_spring,suffix,resource_regen,flat,,0.4,1,1,6,off_hand|legs,resource_regen,true
```

**Linhas novas, T2 (`minItemLevel` 5; mesmo `group`; ficam dormentes até existir área de nível 5 ou mais):**

```csv
affix.sturdy_t2,prefix,life,flat,,24,45,5,10,head|body|hands|legs|feet|off_hand,life,true
affix.honed_t2,prefix,damage,increased,attack,0.14,0.24,5,10,main_hand,damage,true
affix.plated_t2,prefix,armor,flat,,11,22,5,10,head|body|hands|legs|feet|off_hand,armor,true
affix.cracked_t2,prefix,crit_chance,flat,,0.025,0.05,5,6,main_hand,crit,true
affix.of_mending_t2,suffix,life_regen,flat,,1.2,2.4,5,8,head|body|hands|legs|feet|off_hand,regen,true
affix.of_swiftness_t2,suffix,attack_speed,increased,,0.07,0.12,5,8,main_hand|hands,attack_speed,true
affix.of_the_furnace_t2,suffix,resist_fire,flat,,0.12,0.25,5,5,head|body|hands|legs|feet|off_hand,resist_fire,true
affix.of_light_steps_t2,suffix,move_speed,increased,,0.06,0.11,5,6,feet,move_speed,true
affix.ruthless_t2,prefix,crit_multiplier,flat,,0.3,0.6,5,6,main_hand,crit_mult,true
affix.of_cadence_t2,suffix,cooldown_recovery,increased,,0.09,0.16,5,6,main_hand,cooldown,true
affix.of_reach_t2,suffix,area_of_effect,increased,,0.09,0.16,5,5,main_hand,area,true
affix.resolute_t2,prefix,life,increased,,0.06,0.1,5,6,head|body|hands|legs|feet|off_hand,life_pct,true
affix.of_the_flask_t2,suffix,potion_effect,increased,,0.18,0.3,5,5,head|body|hands|legs|feet,potion,true
affix.of_the_wall_t2,suffix,block_chance,flat,,0.07,0.12,5,6,off_hand,block,true
affix.arcane_t2,prefix,damage,increased,spell,0.14,0.24,5,10,main_hand,damage,true
affix.of_the_channel_t2,suffix,cast_speed,increased,,0.07,0.12,5,8,main_hand|hands,attack_speed,true
affix.deep_t2,prefix,resource,flat,,22,40,5,6,head|off_hand,resource,true
affix.of_the_spring_t2,suffix,resource_regen,flat,,0.9,1.6,5,6,off_hand|legs,resource_regen,true
```

Os três T2 de `arcane`, `of_the_channel`, `deep` e `of_the_spring` são F2. Os demais T2 acompanham a F1 dormentes.

**Chaves de Loc (funcionais, sem lore):** `affix.<id>.name` para os 10 novos (e `affix.<id>_t2.name` repete o texto do T1; pedir ao Data uma coluna `nameKey` opcional evita as 18 linhas). Prefixos precisam das 4 formas (`.name`, `.name_f`, `.name_mp`, `.name_fp`):

| ID | pt-BR (m / f / m plural / f plural) |
|---|---|
| `affix.ruthless` | Impiedoso / Impiedosa / Impiedosos / Impiedosas |
| `affix.resolute` | Resoluto / Resoluta / Resolutos / Resolutas |
| `affix.arcane` | Arcano / Arcana / Arcanos / Arcanas |
| `affix.deep` | Profundo / Profunda / Profundos / Profundas |
| `affix.of_cadence` | de Cadência (invariável) |
| `affix.of_reach` | de Alcance |
| `affix.of_the_flask` | do Frasco |
| `affix.of_the_wall` | do Muro |
| `affix.of_the_channel` | do Canal |
| `affix.of_the_spring` | da Fonte |

**Coluna proposta para N2:** `classIds` (lista `|`, vazio = todas): `honed` e `of_swiftness` e `of_swiftness_t2` = `class.warrior|class.archer`; `arcane`, `of_the_channel` e T2 = `class.mage`; `deep`, `of_the_spring` e T2 = `class.archer|class.mage`; `of_the_wall` e T2 = `class.warrior`; os demais vazio.

### 3.3 `uniques.csv`

Cabeçalho: `id,baseId,fixedMods,ruleEffectId,idleSupported,idleParitySampleSize,idleCalibration,visualSetId`

**F2, três linhas novas** (`visualSetId` vazio, como o do Martelo; o modelo da arma resolve por `uniqueId`, ver 5.2):

```csv
unique.bulwark_shield,item_base.guard_shield,armor:flat:40|life:flat:30|attack_speed:increased:-0.1,effect.unique.bulwark_stack,false,0,none,
unique.relentless_bow,item_base.recurve_bow,crit_chance:flat:0.04|life:increased:-0.15,effect.unique.relentless_tempo,false,0,none,
unique.cinder_staff,item_base.runed_staff,damage:increased:0.2:spell|crit_chance:flat:0.04|resource:increased:-0.25,effect.unique.crit_surge,false,0,none,
```

Chaves de Loc provisórias: `unique.bulwark_shield.name` = "Escudo Único de Guerreiro (provisório)" e `.desc` conforme o efeito (a descrição **deve bater com `effects.csv` e `uniques.csv`**, como a do Martelo); `.flavor` fica vazio até o dono escrever. Idem para `unique.relentless_bow` ("Arco Único de Arqueiro") e `unique.cinder_staff` ("Cajado Único de Mago").

### 3.4 `effects.csv` (apoio; fora da lista pedida, mas as linhas acima dependem)

Cabeçalho: `id,duration,tickInterval,stackRule,maxStacks,damagePerTickPhysical,damagePerTickFire,damagePerTickCold,damagePerTickLightning,modifiers,barrier,trigger,triggerChance,internalCooldown,tags,interruptsAction`

```csv
effect.unique.bulwark_stack,6,0,stack_n,4,,,,,damage:more:0.06:melee,0,on_block,1,0,,false
effect.unique.relentless_tempo,5,0,stack_n,5,,,,,damage:more:0.06:projectile|move_speed:more:0.03,0,on_kill,1,0,,false
effect.unique.crit_surge,3,0,refresh,1,,,,,cast_speed:more:0.15|cooldown_recovery:more:0.15,0,on_crit,1,0.5,,false
effect.hunter_mark,8,0,refresh,1,,,,,damage_taken:increased:0.2,0,none,1,0,,false
effect.hunter_mark_r2,10,0,refresh,1,,,,,damage_taken:increased:0.25,0,none,1,0,,false
effect.hunter_mark_r3,12,0,refresh,1,,,,,damage_taken:increased:0.3,0,none,1,0,,false
effect.arcane_phase,0.3,0,refresh,1,,,,,damage_taken:more:-1,0,none,1,0,,false
effect.chill_r3,4.5,0,refresh,1,,,,,move_speed:more:-0.5,0,none,1,0,,false
```

`internalCooldown` 0 vira 0,25 s (`trigger_icd_min`). `effect.chill` (rank 3 da Passagem) já existe.

### 3.5 `loot_tables.csv` e `loot_entries.csv`

`loot_tables.csv` (cabeçalho `id,rolls,dropChance,rarityWeightNormal,rarityWeightMagic,rarityWeightRare`), **F2**:

```csv
loot.crypt.heavy,1,0.5,70,26,4
loot.act1.chest,1,0.5,60,35,5
loot.bridge.boss,2,1,0,55,45
loot.pool.act1.gear,1,1,0,0,0
```

`loot.pool.act1.gear` com 0 / 0 / 0 herda a raridade da tabela que o chama (N3); hoje o validador recusa (`content.cpp:1485`). Plano B sem core: três cópias do pool (`.low`, `.mid`, `.top`) com os pesos da tabela chamadora; as linhas de 3.5.3 se replicam por script.

`loot_entries.csv` (cabeçalho `tableId,kind,refId,weight,minAmount,maxAmount,minAreaLevel,maxAreaLevel,manualOnly,fixedChance,guaranteeFirstKill,pityKills`):

#### 3.5.1 F1: Cripta, Guerreiro, entradas diretas

**Linhas alteradas** (só o peso muda; o resto fica):

```csv
loot.crypt.common,item_base,item_base.iron_sword,1.5,1,1,1,999,false,,,
loot.crypt.common,item_base,item_base.iron_helm,1,1,1,1,999,false,,,
loot.crypt.common,item_base,item_base.leather_vest,1,1,1,1,999,false,,,
loot.crypt.common,item_base,item_base.leather_gloves,1,1,1,1,999,false,,,
loot.crypt.common,item_base,item_base.worn_boots,1,1,1,1,999,false,,,
loot.crypt.elite,item_base,item_base.iron_sword,1.5,1,1,1,999,false,,,
loot.crypt.elite,item_base,item_base.iron_helm,1.2,1,1,1,999,false,,,
loot.crypt.elite,item_base,item_base.leather_vest,1.2,1,1,1,999,false,,,
loot.crypt.elite,item_base,item_base.leather_gloves,1.2,1,1,1,999,false,,,
loot.crypt.elite,item_base,item_base.worn_boots,1.2,1,1,1,999,false,,,
loot.crypt.guardian,item_base,item_base.iron_sword,1.5,1,1,1,999,false,,,
loot.crypt.guardian,item_base,item_base.iron_helm,1,1,1,1,999,false,,,
loot.crypt.guardian,item_base,item_base.leather_vest,1,1,1,1,999,false,,,
loot.crypt.guardian,item_base,item_base.leather_gloves,1,1,1,1,999,false,,,
loot.crypt.guardian,item_base,item_base.worn_boots,1,1,1,1,999,false,,,
```

`stone_maul` em `elite` (peso 3) e em `guardian` (peso 4) ficam como estão.

**Linhas novas:**

```csv
loot.crypt.common,item_base,item_base.worn_trousers,1,1,1,1,999,false,,,
loot.crypt.common,item_base,item_base.stone_maul,1,1,1,1,999,false,,,
loot.crypt.common,item_base,item_base.wooden_shield,1.5,1,1,1,999,false,,,
loot.crypt.common,item_base,item_base.guard_helm,2.2,1,1,3,7,false,,,
loot.crypt.common,item_base,item_base.guard_cuirass,2.2,1,1,3,7,false,,,
loot.crypt.common,item_base,item_base.guard_gauntlets,2.2,1,1,3,7,false,,,
loot.crypt.common,item_base,item_base.guard_greaves,2.2,1,1,3,7,false,,,
loot.crypt.common,item_base,item_base.guard_sabatons,2.2,1,1,3,7,false,,,
loot.crypt.elite,item_base,item_base.worn_trousers,1.2,1,1,1,999,false,,,
loot.crypt.elite,item_base,item_base.wooden_shield,2,1,1,1,999,false,,,
loot.crypt.elite,item_base,item_base.guard_helm,3,1,1,3,7,false,,,
loot.crypt.elite,item_base,item_base.guard_cuirass,3,1,1,3,7,false,,,
loot.crypt.elite,item_base,item_base.guard_gauntlets,3,1,1,3,7,false,,,
loot.crypt.elite,item_base,item_base.guard_greaves,3,1,1,3,7,false,,,
loot.crypt.elite,item_base,item_base.guard_sabatons,3,1,1,3,7,false,,,
loot.crypt.guardian,item_base,item_base.worn_trousers,1,1,1,1,999,false,,,
loot.crypt.guardian,item_base,item_base.wooden_shield,2,1,1,1,999,false,,,
loot.crypt.guardian,item_base,item_base.guard_helm,2.3,1,1,3,7,false,,,
loot.crypt.guardian,item_base,item_base.guard_cuirass,2.3,1,1,3,7,false,,,
loot.crypt.guardian,item_base,item_base.guard_gauntlets,2.3,1,1,3,7,false,,,
loot.crypt.guardian,item_base,item_base.guard_greaves,2.3,1,1,3,7,false,,,
loot.crypt.guardian,item_base,item_base.guard_sabatons,2.3,1,1,3,7,false,,,
```

#### 3.5.2 F2: trocar as entradas diretas por uma sub-tabela

Em F2, **apagar** as linhas `item_base` das três tabelas (as 15 alteradas, as 22 novas e as 2 de `stone_maul` de elite e Guardião da F1) e acrescentar uma entrada `table` com a mesma fatia de item de antes (20, 28 e 24):

```csv
loot.crypt.common,table,loot.pool.act1.gear,20,1,1,1,999,false,,,
loot.crypt.elite,table,loot.pool.act1.gear,28,1,1,1,999,false,,,
loot.crypt.guardian,table,loot.pool.act1.gear,24,1,1,1,999,false,,,
loot.crypt.heavy,stack,currency.gold,45,10,20,1,999,false,,,
loot.crypt.heavy,stack,material.shards,25,2,4,1,999,false,,,
loot.crypt.heavy,table,loot.pool.act1.gear,30,1,1,1,999,false,,,
loot.act1.chest,stack,currency.gold,40,8,20,1,999,false,,,
loot.act1.chest,stack,material.shards,25,2,4,1,999,false,,,
loot.act1.chest,table,loot.pool.act1.gear,35,1,1,1,999,false,,,
loot.bridge.boss,stack,currency.gold,40,40,70,5,999,false,,,
loot.bridge.boss,stack,material.shards,25,5,9,5,999,false,,,
loot.bridge.boss,table,loot.pool.act1.gear,24,1,1,5,999,false,,,
loot.bridge.boss,unique,unique.bulwark_shield,,1,1,5,999,true,0.2,true,5
loot.bridge.boss,unique,unique.relentless_bow,,1,1,5,999,true,0.2,true,5
loot.bridge.boss,unique,unique.cinder_staff,,1,1,5,999,true,0.2,true,5
loot.crypt.elite,unique,unique.bulwark_shield,,1,1,5,999,true,0.03,false,
loot.crypt.elite,unique,unique.relentless_bow,,1,1,5,999,true,0.03,false,
loot.crypt.elite,unique,unique.cinder_staff,,1,1,5,999,true,0.03,false,
```

As entradas `unique` por classe só valem com N4 (sem ele, o herói sortearia as três).

#### 3.5.3 F2: o pool de bases (`loot.pool.act1.gear`), 59 linhas

Pesos: G0 1; G1 2; G2 2,5; armas W0 1,5 (3 se a classe tem 1 linha) e W1 2,5 (5); `off_hand` O0 1,5 e O1 2,5. Janelas G0 [1,4], G1 [3,7], G2 [5,999], W0 e O0 [1,4], W1 e O1 [5,999].

```csv
loot.pool.act1.gear,item_base,item_base.iron_sword,1.5,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.stone_maul,1.5,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.steel_sword,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.quarry_maul,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.wooden_shield,1.5,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.guard_shield,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.iron_helm,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.leather_vest,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.leather_gloves,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.worn_trousers,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.worn_boots,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.guard_helm,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.guard_cuirass,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.guard_gauntlets,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.guard_greaves,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.guard_sabatons,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.plate_helm,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.plate_cuirass,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.plate_gauntlets,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.plate_greaves,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.plate_sabatons,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.hunter_bow,3,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.recurve_bow,5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.leather_quiver,1.5,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.hunter_quiver,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.hunter_hood,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.hunter_jerkin,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.hunter_bracers,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.hunter_breeches,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.hunter_boots,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.ranger_hood,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.ranger_jerkin,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.ranger_bracers,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.ranger_breeches,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.ranger_boots,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.stalker_hood,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.stalker_jerkin,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.stalker_bracers,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.stalker_breeches,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.stalker_boots,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.crystal_staff,3,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.runed_staff,5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.worn_tome,1.5,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.scribe_tome,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.novice_hood,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.novice_robe,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.novice_wraps,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.novice_leggings,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.novice_shoes,1,1,1,1,4,false,,,
loot.pool.act1.gear,item_base,item_base.scholar_hood,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.scholar_robe,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.scholar_wraps,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.scholar_leggings,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.scholar_shoes,2,1,1,3,7,false,,,
loot.pool.act1.gear,item_base,item_base.adept_hood,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.adept_robe,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.adept_wraps,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.adept_leggings,2.5,1,1,5,999,false,,,
loot.pool.act1.gear,item_base,item_base.adept_shoes,2.5,1,1,5,999,false,,,
```

(São 59 linhas: Guerreiro 21, Arqueiro 19, Mago 19.)

**Mudança fora dos CSV pedidos:** `enemies.csv`, `enemy.stone_herald`, `lootTableId` passa de `loot.crypt.common` para `loot.crypt.heavy` (F2).

### 3.6 `skills.csv`

Cabeçalho da worktree (39 campos): `id,classId,specId,tags,shape,scalesWithWeapon,baseDamagePhysical,baseDamageFire,baseDamageCold,baseDamageLightning,coefficientRank1,coefficientRank2,coefficientRank3,cost,cooldown,windup,impact,recovery,range,radius,projectiles,onHitEffects,selfEffects,idleSupported,idleAvgTargetsHit,idleFractionOfGroupHit,idleApproachTime,idleUptime,idleDodgeTelegraphedBonus,idleDamageTakenMult,idleParitySampleSize,unlockLevel,coneAngle,knockback,projectileSpeed,idleCalibration,wallStaggerSeconds,pierce,explosionRadius`

**F2, duas linhas novas** (R do Arqueiro e do Mago; `idleSupported=false` até a Etapa 4, 2.6):

```csv
skill.archer.hunters_mark,class.archer,,attack|projectile|physical,projectile,true,,,,,0.6,0.7,0.8,20,10,0.15,0.05,0.25,1400,,1,effect.hunter_mark,,false,,,,,,,,4,,,3000,,,,
skill.mage.arcane_passage,class.mage,,spell|area|lightning,dash,false,,,,10,0.8,0.9,1,25,10,0.05,0.1,0.2,500,160,1,,effect.arcane_phase,false,,,,,,,,4,,100,,,,,
```

**Nenhuma linha existente muda** (os rank 2 e 3 dos coeficientes já estão nos CSV). Os perks de rank 3 vão para a tabela nova 3.8.

### 3.7 `rules.csv` (apoio)

```csv
equip_slot_off_hand,true
skill_rank2_levels_after_unlock,4
skill_rank3_levels_after_unlock,8
smart_loot_other_class_weight,0
```

`equip_slot_off_hand` é **alteração** da linha existente (`false` → `true`), F1. As outras três são novas: `smart_loot_other_class_weight` (peso das bases de outra classe; 0 = excluir) é F2 (N1).

### 3.8 `skill_ranks.csv` (tabela nova proposta, N5)

Colunas: `skillId,rank,cooldown,cost,range,radius,explosionRadius,projectiles,coneAngle,pierce,onHitEffects`. Célula vazia = herda a linha de `skills.csv`. O `rank` do kit é o de `startingSkill`. Linhas (todas F2):

```csv
skill.warrior.heavy_slash,3,,,,,,,,,effect.guard_break|effect.stun
skill.warrior.charge,3,5,,,,,,,,effect.guard_break
skill.warrior.stone_rift,3,,35,,270,,,,,
skill.warrior.shield_bash,3,3,20,,,,,,,
skill.archer.fan_shot,3,,,,,,5,40,,
skill.archer.piercing_shot,3,,10,,,,,,,
skill.archer.back_leap,3,4.5,,,,,,,,
skill.archer.arrow_rain,3,,30,,360,,,,,
skill.archer.hunters_mark,2,,,,,,,,,effect.hunter_mark_r2
skill.archer.hunters_mark,3,8,,,,,,,,effect.hunter_mark_r3
skill.mage.arcane_orb,3,,,,,170,,,,
skill.mage.fireball,3,,,,,270,,,,
skill.mage.frost_nova,3,,,,400,,,,,effect.chill_r3
skill.mage.arcane_ray,3,5,,1100,,,,,,
skill.mage.arcane_passage,3,8,,,,,,,,effect.chill
```

---

## 4. O que o core precisa ler de novo

Prioridade: **A** bloqueia o balanceamento; **M** bloqueia uma entrega de F2; **B** melhora a experiência.

| ID | Pedido | Onde | Fase | Prioridade | Plano B se não vier |
|---|---|---|---|---|---|
| **N0** | `attackTime` da arma vira velocidade do kit: duração dos golpes de `lightChain` e `heavySkill` × `refAttackTime / attackTime`. `refAttackTime` = `attackTime` da arma inicial da classe (coluna nova de `basic_kits.csv`: 0,9, 0,8, 1,0) | `combat.cpp` `ComputeActionTiming`, `basic_kits.csv` | F1 | A | Normalizar o dano do Martelo (16 → ~10) e do Único; perde-se a identidade "lento e pesado" |
| **N1** | Coluna `classId` em `item_bases.csv` + validação de equipar por classe + sorteio de base só da classe do herói (`LootContext.heroClassId`); chave `smart_loot_other_class_weight` | `content.cpp`, `loot.cpp`, `inventory.cpp` | F2 | M | Tabelas de loot por classe (3 conjuntos) e travar equipar pela interface (proibido pelo C# calcular regra) |
| **N2** | Coluna `classIds` em `affixes.csv`: `RollAffixes` ignora afixo cuja lista não contém a classe da base | `loot.cpp:186` | F2 | M | Aceitar afixo morto (cerca de 1 de 3 em arma e luva) |
| **N3** | Sub-tabela com raridade 0 / 0 / 0 herda a raridade da tabela que a chama; validador aceita só se for referenciada por `table` | `loot.cpp` `EmitEntry`, `content.cpp:1485` | F2 | B | Três cópias do pool (`.low`, `.mid`, `.top`), gerado por script |
| **N4** | Entrada `unique` com classe: `loot_entries.csv` lê o `classId` do Único (via `item_bases.classId` da base) e ignora o de outra classe | `loot.cpp` | F2 | M | Um único Único por tabela de chefe (o do Guardião, por classe, fica fora desta entrega) |
| **N5** | `skill_ranks.csv` (sobrescrita por rank) e regra de rank por nível (`skill_rank2/3_levels_after_unlock`); o rank do kit segue `startingSkill` | `content.cpp`, `character.h` (`rank` já existe) | F2 | M | Rank 3 só com o coeficiente dos CSV atuais (sem perks) |
| **N6** | `TriggerKind::OnBlock` dispara também em **defesa ativa** (e na defesa perfeita), não só em `block_chance` passivo; conferir se `stack_n` soma o modificador por acúmulo e se `internalCooldown` 0 vira 0,25 | `effects.h`, `combat.cpp` | F2 | M | Sem isso `bulwark_shield` vira peça sem efeito |
| **N7** | Ligar o slot `off_hand` (regra `equip_slot_off_hand`), kit inicial de 7 peças, tooltip sem "dano por segundo" para `off_hand` | `rules.csv`, save de novo jogo | F1 | M | Manter o escudo fora do jogo |
| **N8** | Cajado: `weaponTags` aceita `spell` (ou o validador aceita `projectile` com dano nominal); tooltip de arma de classe com `scalesWithWeapon=false` mostra "poder de feitiço" em vez de DPS | `content.cpp:1459`, `inventory.cpp:66` | F2 | M | Cajado com `projectile` e DPS nominal de 2: o tooltip engana |
| **N9** | `hunter_mark` e `arcane_phase`: confirmar que `onHitEffects` pode aplicar `damage_taken:increased` em **elite e chefe** (sem imunidade) e que `damage_taken:more:-1` zera o dano | `effects.cpp` | F2 | M | Marca só em comum |
| **N10** | Teste de EditMode de `docs/04` 17.4 ("todo `vset` do CSV tem peça para os **3** heróis") passa a exigir peça só dos heróis jogáveis na etapa; senão `iron_guard` e `stone_plate` ficam presos a 30 modelos | testes C# | F1 | A | Entregar os 3 heróis juntos (30 peças) antes de usar o conjunto |
| **N11** | Perfil nulo no idle: `IsIdleCompatible` aceita `idleAvgTargetsHit=0` como "ignorar" para habilidade de movimento; considerar o slot R | `content.cpp`, `expedition.cpp` | F2 | B | Passagem Arcana bloqueia a expedição do Mago (aceitável: o Mago está sem expedição, Q18-2) |
| **N12** | `area_of_effect` multiplica `radius` **e** `explosionRadius` (conferir); `cooldown_recovery` divide a recarga (confirmado em `combat.cpp:183`) | `combat.cpp` | F1 | B | `of_reach` não funciona em Orbe e Bola de Fogo |

N0 e N10 são os que o orquestrador deve decidir **antes** da Etapa 3 fechar: N0 porque muda o resultado do combate com o Martelo e com o Único, N10 porque o teste de cobertura quebra assim que a primeira linha de `iron_guard` entrar em CSV.

---

## 5. Lista de arte

Toda arte nova passa pela aprovação do dono antes de entrar (CLAUDE.md). Estilo, paleta e tamanhos seguem `docs/03` e as folhas em `docs/arte/referencias-geracao/`. Contagens por **fase**.

### 5.1 Ícones

| Item | Quantidade | Nota |
|---|---|---|
| Ícone de base de equipamento | **F1: 14** (Guerreiro: 2 armas, 1 `off_hand` O0, 5 `guard_*`, 5 `plate_*`, 1 `guard_shield`). **F2: 40** (Arqueiro: 2 armas, 2 `off_hand`, 15 armaduras; Mago: idem) | Mesmo tamanho e moldura dos ícones aprovados (folha 11 de ícones); a raridade vai na **moldura**, não no ícone |
| Ícone de Único | **F2: 3** | Cantos espinhosos e filete dourado da moldura; fundo com acento `#FF8A2E` |
| Ícone de habilidade | **F2: 2** (Marca da Trilha, Passagem Arcana) | Mais selos de rank (3 pontos); os ícones das 13 habilidades de `docs/18` já são necessários independentemente |
| Selo de rank | 3 variantes (1, 2, 3 pontos), pequeno, sobre qualquer ícone | A UI mostra o rank atual |
| Ícones inline de afixo | **0** | O tooltip mostra texto; nada a desenhar |
| Silhueta de item no chão por slot | 8 (arma, `off_hand`, `head`, `body`, `hands`, `legs`, `feet`, Único) | O feixe de luz por raridade já existe na spec de `docs/03` |

### 5.2 Modelos 3D

**Armas e `off_hand` (props, fora da soma de triângulos do herói).** A raridade é **material** (rim e acento emissivo da 1.6.1), então há **uma malha por base**, não uma por raridade:

| Fase | Peças |
|---|---|
| F1 | `steel_sword`, `quarry_maul`, `wooden_shield`, `guard_shield` (Guerreiro) = 4 (além de `iron_sword` e `stone_maul`, que existem) |
| F2 | `recurve_bow`, `crystal_staff`, `runed_staff`, `leather_quiver`, `hunter_quiver`, `worn_tome`, `scribe_tome` = 7 (o `hunter_bow` existe) |
| F2, Únicos | `unique.bulwark_shield`, `unique.relentless_bow`, `unique.cinder_staff` = 3 malhas próprias, com **um traço `#FF8A2E`** (pulso de 2400 ms; fixo com "Reduzir movimento"); o maul Único também precisa da malha própria (hoje `visualSetId` vazio) |

Sockets novos do modelo do herói (Art Director): `back_quiver` (aljava nas costas), `hip_tome` (tomo na cintura); `weapon_tip`, `bow_nock`, `staff_crystal` e `shield_face` já estão em `docs/18` seção 6. **Vazio de resolução:** o modelo de arma e de `off_hand` é resolvido por `baseId` (e por `uniqueId` nos Únicos), não por `visualSetId`; cabe ao Frontend (Q19-7).

**Conjuntos de armadura (modulares).** Raridade é **tinta** (máscara B) e acento (máscara R), **sem malha nova**: um conjunto serve às 3 raridades não Únicas.

| Conjunto | Guerreiro | Arqueiro | Mago | Total |
|---|---|---|---|---|
| `vset.starter` | existe | 5 peças (`mod_a02`) | 5 peças (`mod_a03`) | 10 peças novas (F2) |
| `vset.iron_guard` | **5 peças (F1)** | 5 peças (F2) | 5 peças (F2) | 15 |
| `vset.stone_plate` | 5 peças (F1 de dados, F2 de drop) | 5 peças (F2) | 5 peças (F2) | 15 |

Total: **15 peças na F1 se o N10 for resolvido** (`iron_guard` e `stone_plate` do Guerreiro, 10), **40 ao todo** (30 das duas coleções e 10 do `starter` das outras classes). Cada peça traz textura de albedo, máscara RGB (R emissão, G rim, B tinta), nos tamanhos de `docs/04` 17.4. Opção barata a decidir pelo Art Director: `stone_plate` como **repintura** de `iron_guard` (mesma malha, outro albedo e máscara), o que corta 15 malhas e perde silhueta (Q19-8).

Nota do Art Director sobre a leitura: o elmo do Guerreiro (B vazia) não carrega raridade; `plate_helm` deveria ter uma faixa de pano ou plumagem de ombro para o Raro aparecer no topo (1.6.2, item 4).

### 5.3 VFX e áudio novos

Paleta de `docs/18` seção 6 e `docs/03` 6. VFX do jogador: aditivo, fino, alfa até 0,75, núcleo claro, **nunca** `#E0301E` como massa. Desligam com "Reduzir efeitos do jogador".

| ID | Efeito | Quando | Cor | Duração | Nasce em |
|---|---|---|---|---|---|
| `fx.mark.hit` | Anel de 60 cm no chão do alvo e glifo de 30 cm sobre a cabeça; o anel encolhe nos últimos 2 s | Marca da Trilha, enquanto durar o efeito | Ácido `#8FD43A` alfa 0,75 | 8, 10 ou 12 s | Alvo marcado |
| `fx.mark.shot` | Flecha da Marca com ponta clara e rastro de 150 ms | Marca da Trilha | Ácido | voo | `bow_nock` |
| `fx.passage.out` | Resíduo do herói a 40% de alfa e anel de 60 cm no chão | Passagem, saída | Raio `#F2F6FF` / `#7FA8FF` / `#3A4FB8` | 250 ms | `root_feet` |
| `fx.passage.in` | Onda de 160 uu que cresce em 250 ms e 3 faíscas de sombra `#9A4BD6` | Passagem, chegada | Raio | 250 ms | Ponto de chegada |
| `fx.unique.bulwark_stack` | Anel dourado fino em volta do escudo, mais um segmento por acúmulo (4) | `bulwark_shield`, bloqueio | `#FFF2A8` / `#F2B23A` | enquanto durar | `shield_face` |
| `fx.unique.relentless_tempo` | Linhas de vento atrás do herói e brilho verde-ácido na ponta da flecha, mais fortes por acúmulo (5) | `relentless_bow`, morte | Ácido | enquanto durar | `bow_nock`, `root_feet` |
| `fx.unique.crit_surge` | Clarão de 80 ms no cristal e anel azul que gira no cajado por 3 s | `cinder_staff`, crítico | Raio | 3 s | `staff_crystal` |
| `fx.crit.hit` | Faísca maior no ponto de contato e `fx.hit.spark` em dobro (crítico) | Crítico | por tipo de dano | 300 ms | Alvo |
| `fx.fan.5` | Cinco flechas e clarão de 100 ms | Leque, rank 3 | Ácido | 120 ms | `bow_nock` |
| `fx.rank.up` | Brilho curto no ícone do slot e toast "Rank N" | Subir de rank | `#FCD58A` | 600 ms | HUD |

Ajustes de escala (sem asset novo): `fx.rain`, `fx.nova`, `fx.orb`, `fx.fireball` e a Fenda de Pedra escalam com o raio do rank 3 e com `of_reach`; `fx.chill` ganha uma variante mais densa para `effect.chill_r3`.

Áudio (referência curta): Marca (corda seca, "toc", tom ascendente, "pip" grave no fim), Passagem (zip elétrico, estalo grave), bloqueio com Baluarte (clangor mais cheio a cada acúmulo), surto de crítico (tom agudo curto), subir de rank (tom ascendente curto) e um som próprio para cada soltura de Único (já existe um para o Martelo).

---

## 6. Hipóteses que precisam de playtest ou de simulação

| ID | Hipótese | Como testar | Aprovado se |
|---|---|---|---|
| H19-01 | Os afixos de crítico perdem para `honed`; ver 2.5 | `tools/batch_sim` com 6 combinações de afixos T2 por classe | Nenhuma combinação supera a melhor em mais de 25%; cada afixo aparece em ao menos 15% dos Raros que um jogador de teste monta |
| H19-02 | Três degraus de armadura trocam o boneco em 2 a 3 corridas | Contar peças G1 vestidas após 3 corridas na Cripta | Pelo menos 2 peças `iron_guard` e o jogador diz que viu a mudança |
| H19-03 | +33% de dano de base por degrau de arma mantém o tempo para matar de comum perto de 3 s | Cronometrar TTK de uma Sentinela com `steel_sword` na Pedreira | Entre 2 e 4 s |
| H19-04 | O Martelo com N0 (36% mais lento) continua uma escolha, não uma armadilha | Comparar escolhas de arma no playtest | Entre 30% e 70% dos jogadores ficam com o Martelo |
| H19-05 | A Marca (80% de presença no rank 1) cria a decisão "marcar agora?" | Observar quantas marcas por luta de chefe | Entre 2 e 6 marcas por luta do Guardião de teste |
| H19-06 | A Passagem salva um golpe em pelo menos 40% das vezes que o jogador a usa em reação | Registrar uso e dano evitado | 40% a 70% |
| H19-07 | `bulwark_shield` não vira "ficar parado" | Tempo médio em guarda e vida perdida com o Único | Vida cai mais com o Único que sem ele em 20% ou mais; jogador esquiva ao menos 30% das vezes |
| H19-08 | `cinder_staff` mantém ≥ 40% de presença do surto num Mago com 15% de crítico | Medir presença do `crit_surge` | 40% a 60% |
| H19-09 | 55% de peças G1 nos drops da Cripta não inunda a Mochila | Itens por corrida e espaço livre | ≤ 4 itens por corrida (como em H3-13) |
| H19-10 | `heavy_slash` atordoante (rank 3) não torna o forte dominante | Fração de golpes fortes após o nível 9 | Entre 15% e 45% |
| H19-11 | `of_the_furnace` (peso 5) e `of_the_flask` (peso 5) não são ignorados | Frequência em Raros de armadura | Cada um entre 10% e 25% |

---

## 7. Perguntas abertas
> **Decididas em 18/10/2026** pelo orquestrador, com autonomia dada pelo dono: todas as recomendações abaixo foram aceitas (Q19-1 A antes de fechar a Etapa 3; Q19-2 A na Etapa 4; Q19-3 A; Q19-4 B na F2 e A depois; Q19-5 A; Q19-6 A; Q19-7 A; Q19-8 C na F1 e B para Arqueiro e Mago; Q19-9 C com batch_sim; Q19-10 A; Q19-11 A).


Formato de `CLAUDE.md`: pergunta inteira, contexto, opções com efeito, recomendação. O dono deu autonomia ao orquestrador.

**Q19-1. O `attackTime` da arma deve mudar o tempo dos golpes do kit (N0)?**
Contexto: hoje o `attackTime` só aparece no tooltip. O Martelo de Pedra bate 78% mais forte que a Espada sem ser mais lento, e o Arco "mais rápido" não é mais rápido.
Opções: **A.** Aplicar `refAttackTime / attackTime` ao kit básico (combo, forte): o Martelo fica 36% mais lento e a Espada e o Arco iniciais não mudam; custo: uma coluna em `basic_kits.csv` e uma multiplicação em `ComputeActionTiming`. **B.** Ignorar: o Martelo vira a arma única e o Único do Guardião fica ainda mais forte; zero código. **C.** Reduzir o dano do Martelo para ~10: perde a identidade.
Recomendação: **A**, antes de a Etapa 3 fechar.

**Q19-2. Bases de equipamento passam a ter classe e o drop só rola a classe do herói (N1, N2, N4)?**
Contexto: o save tem um herói; item de outra classe é lixo, e a tabela de loot hoje não sabe quem joga. Só importa quando Arqueiro e Mago forem jogáveis.
Opções: **A.** Coluna `classId` em bases e afixos, filtro no sorteio e na hora de equipar. **B.** Tabelas de loot por classe e sem trava de equipar. **C.** Sem filtro: mais lixo e afixo morto.
Recomendação: **A** na Etapa 4; a F1 (só Guerreiro) não precisa.

**Q19-3. Ativar o slot `off_hand` agora e começar com 7 peças?**
Contexto: o Guerreiro já tem escudo no modelo e na defesa, mas não como item; Arqueiro e Mago ganham aljava e tomo.
Opções: **A.** Ativar na F1 só com o escudo do Guerreiro: o inventário ganha uma posição e a Cripta larga escudos. **B.** Esperar a Etapa 4. **C.** Cortar: menos itens, sem o Único Baluarte.
Recomendação: **A**; custa uma linha de regra, um modelo e o ajuste de A3-02.

**Q19-4. O cajado entra como arma de verdade (N8)?**
Contexto: o validador exige `melee` ou `projectile` e dano de arma positivo; o dano do Mago não escala com a arma.
Opções: **A.** Aceitar `spell` em `weaponTags` e tratar o tooltip como "poder de feitiço". **B.** Manter `projectile` com dano nominal 2 e esconder o DPS. **C.** Sem cajado: o Mago nunca progride por arma.
Recomendação: **B** na F2 para não esperar o core; **A** depois.

**Q19-5. O rank 3 deve ter perk (N5) ou só número?**
Contexto: a tabela de coeficientes dos CSV já cobre números. Perks exigem uma tabela nova de sobrescrita.
Opções: **A.** Perks na F2 (`skill_ranks.csv`). **B.** Só números. **C.** Perks só para o Guerreiro.
Recomendação: **A**; sem perk o rank 3 é só um número maior e o jogador deixa de ter motivo para subir a habilidade.

**Q19-6. Os Únicos de Ato I podem cair de elite e de chefe de outra área, além do Guardião (RF-27)?**
Contexto: `docs/16` escreveu "Único só no Guardião"; o plano já diz "chefes e elites". O teste A3-05 vira "só entrada `unique` com `manualOnly`".
Opções: **A.** Sim, em elites (3%) e no Tecelã (20% com pity). **B.** Só chefe. **C.** Só Guardião, e os outros Únicos esperam.
Recomendação: **A**; elite com 3% dá motivo para voltar à Pedreira, e o pity do chefe garante que ninguém depende de sorte.

**Q19-7. De onde sai o modelo de uma arma Única?**
Contexto: `docs/04` limita `visualSetId` aos 5 slots visuais; o maul Único está com `visualSetId` vazio.
Opções: **A.** O Frontend resolve por `uniqueId` quando existir. **B.** Aceitar `visualSetId` em arma. **C.** Usar a malha da base com um traço emissivo (menos arte).
Recomendação: **A**.

**Q19-8. O `stone_plate` é malha nova ou repintura de `iron_guard`?**
Contexto: 15 malhas a menos se for repintura; a silhueta é idêntica, o que o `docs/03` 3.5 não proíbe, mas enfraquece a leitura a 88 px.
Opções: **A.** Malha nova nas 3 classes (15 peças). **B.** Repintura (mesma malha, nova textura e máscara). **C.** Só Guerreiro agora, outras classes depois.
Recomendação: **C** para a F1 e **B** para Arqueiro e Mago; a Pedreira ganha um degrau novo visível por 5 peças de Guerreiro novas e não por 30.

**Q19-9. O que fazer com o crítico, que perde para `honed`?**
Contexto: seção 2.5; dois afixos de crítico valem menos que um de dano em todos os cenários do Ato I.
Opções: **A.** Subir `ruthless` e `cracked` (T2 de 0,60 para 0,90; crítico 5% para 7%). **B.** Dar habilitadores (nós de árvore, efeito de Marca). **C.** Aceitar e tratar o crítico como estilo do Mago e do Único.
Recomendação: **C** agora e simular em `batch_sim` (H19-01) antes de decidir A ou B.

**Q19-10. Requisito de nível nos itens?**
Contexto: `itemLevel` da base existe; nada o aplica como requisito.
Opções: **A.** Nenhum requisito no Ato I. **B.** Requisito = `itemLevel` da base.
Recomendação: **A**: o nível da área já filtra o que cai.

**Q19-11. A Marca e a Passagem substituem as habilidades do plano?**
Contexto: o plano põe Marca da Trilha no nível 5 do Arqueiro, mas a Passagem Arcana no nível 7 do Mago e outras no R. O CSV põe R no nível 4.
Opções: **A.** Aprovar as duas como R no nível 4. **B.** Esperar o desenho de livros (Etapa 4).
Recomendação: **A**; o Pulso de Tempestade e a Barreira de Vidro do plano ficam como habilidades futuras.
