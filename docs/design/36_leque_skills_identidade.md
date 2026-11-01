# 36. Leque de skills com identidade própria (afinidade do básico + catálogo por forma)

Pedido do Will (01/11/2026): "quero várias skills com visuais diferentes": o ataque básico vira flecha de **um** elemento (raio, veneno, gelo ou fogo, escolha única), e a árvore oferece formas bem distintas (tornado de raio ou de veneno, bola de fogo ou de gelo caindo do céu, ataque que acerta todas as direções, flecha que acerta um alvo e espalha o dano aos vizinhos...). Cada uma com mecânica, silhueta, rastro, impacto e animação próprios, "nunca só uma flecha de outra cor".

Este documento é a fonte de verdade do **catálogo**: o que cada habilidade é, como se lê na tela e quais tags a árvore de passivos usa. Regras visuais gerais (camadas, origem no arco, escala, orçamento, modificadores) continuam em `docs/arte/33_direcao_vfx_habilidades.md`; números de balanceamento ficam só nos CSV (`godot/data2d/`). Direção visual feita com a revisora "Agente escolhedor de ferramentas" (Jev); o Will recebe só o resultado.

## 0. Decisões deste documento
1. **Afinidade** (seção 2): a primeira gema de habilidade da corrida oferece as **quatro** afinidades (não três sorteadas); escolher uma troca o ataque básico de verdade (comportamento + visual) pelo resto da corrida. As outras três somem. A afinidade também garante uma skill do seu elemento em cada oferta de gema seguinte (quando houver).
2. **Identidade por forma, cor por elemento** (regra do doc 33 seção 4): cada skill pertence a uma **família de forma** (seção 3). Duas skills do mesmo elemento nunca repetem a família; a mesma família em elementos diferentes muda movimento e impacto, não só a paleta.
3. **Cinco skills novas** completam o leque pedido (seção 4): Haste Elétrica (raio), Ciclone Pestilento (veneno), Cometa Gélido e Nova Gélida (gelo), Serpente de Brasa (fogo). As demais já existem no `master` e entram no catálogo com a ficha de identidade conferida.
4. **Orçamento**: toda skill nova é **um nó** que desenha a si mesmo (`_draw`) e no máximo 8 sprites auxiliares curtos; sem partícula de GPU; o rastro e o impacto por elemento usam `vfx_identidade_2d.gd` (vetorial, teto de 18 nós). Folhas pintadas novas só onde a forma não cabe (seção 6).

## 1. Ficha de identidade (o que toda skill precisa responder)
| Eixo | Pergunta | Exemplo (Tornado de Tempestade) |
|---|---|---|
| **Silhueta** | Que forma o jogador reconhece a 3/4, parado, em 0,2 s? | Funil alto e torcido, mais largo em cima |
| **Movimento** | Como entra, anda e sai? | Flecha sobe em arco, cai, o funil nasce no chão e gira no lugar |
| **Rastro** | O que fica para trás enquanto age? | Faíscas que caem e pó no pé do funil |
| **Impacto** | O 1º quadro do dano e a reação do alvo | Coluna de raio na queda; inimigos puxados ao centro |
| **Som/gesto do arqueiro** | O que o arqueiro faz | Mira para cima (linha N da folha), recuo de 3 px |
| **Cor** | Paleta do elemento (doc 33 seção 6) | azul-branco com ponta amarela |
| **Tags** | Para a árvore de passivos | `area+raio` |

## 2. Afinidade do ataque básico (escolha única por corrida)
O básico continua gratuito e sem recarga; a afinidade muda **o que a flecha faz ao voar e ao acertar**, com a mesma cadência. Números em `godot/data2d/afinidades_arqueiro.csv` (novo). Nome do grupo: "Ecos" (combina com os Arautos e com o nome do jogo).

| id | Nome | Mecânica (diferente, não só cor) | Silhueta e rastro | Impacto | Status |
|---|---|---|---|---|---|
| `eco_trovao` | Eco do Trovão | Flecha **mais rápida** (×1,2); ao acertar, um arco salta para **1 vizinho** (`raio`) com fração do dano (`valor`) | Haste reta e fina com ponta em zigue-zague; rastro elétrico que treme (vfx_identidade `raio`) | Estrela de arcos no alvo + segmento até o vizinho | choque (`duracao`) |
| `eco_peste` | Eco da Peste | Flecha **mais lenta e gorda** (×0,85), **atravessa 1 corpo** e envenena todos que toca | Ponta em gota, rastro de gosma que pinga | Respingo e poça pequena no chão (C0) | veneno (`valor` dps, `duracao`) |
| `eco_gelo` | Eco do Gelo | Cada acerto soma **1 acúmulo de frio**; no 4º o alvo congela e estilhaça (regra do gelo) | Cristal facetado, lascas que se soltam e giram | Estilhaços radiais + anel de geada | frio/lentidão (`valor` por acúmulo) |
| `eco_cinzas` | Eco das Cinzas | Dano **+10%**; ao acertar deixa uma **brasa** no chão (`raio`) que queima quem pisar por 1 s | Língua de chama afilada, brasas que sobem | Onda de fogo + marca queimada | queimadura (`valor` dps, `duracao`) |

Como escolher: no modo horda "do zero", a **primeira** gema de habilidade (nível 2) abre a tela de cartas com as 4 afinidades (título `upgrade.afinidade`). Fora do modo horda a afinidade fica vazia (básico neutro). A escolha vive no jogador (`afinidade`) e zera a cada corrida. HUD: o ícone do slot de tiro troca para o da afinidade.

Tags para a árvore: a afinidade **não** é skill (não entra em `habilidades_arqueiro.csv`), mas o `def` dela passa por `passivos.resolver("basico", def, ["basico", "projetil", <elemento>])`, então nós de `tag:raio` etc. valem para ela.

## 3. Catálogo por família de forma
Legenda do estado: **M** = já no master, **N** = nova neste pacote, **F** = forma alternativa por passivo (`forma`), **B** = backlog.

### 3.1 Projétil (sai do arco, voa reto)
| Skill | El. | Est. | O que a distingue | Rastro / impacto |
|---|---|---|---|---|
| Flecha Pesada `power_shot` | físico | M | 1 flecha grossa que perfura 2 | rastro grosso e curto; faísca branca |
| Rajada `rapid_volley` | físico | M | 5 flechas em sequência de 90 ms do mesmo arco | flashes de boca seguidos |
| Tiro Certeiro `sniper_shot` | físico | M | 1 flecha que atravessa tudo (`qtd` 99) | rastro reto longo, "atravessa" com faísca do outro lado |
| Flecha Elétrica `shock_arrow` | raio | M | aplica choque forte (recarga) | zigue-zague que treme |
| Flecha Peçonhenta `poison_arrow` | veneno | M | 3 acúmulos de veneno de uma vez | gosma |
| Flecha Gélida `frost_arrow` | gelo | M | 1 acúmulo de frio; forma `anel` solta lascas em volta | cristais |
| Flecha Ardente `flecha_ardente` | fogo | M | queima e acende impacto em área pequena | chama afilada |
| Flecha Explosiva `explosive_arrow` | físico/fogo | M | explode em `raio` ao acertar | clarão laranja em área |
| Salto Atrás `backstep_shot` | físico | M | recua e atira | rastro do salto |

### 3.2 Corrente e dispersão ("acerta um e espalha")
| Skill | El. | Est. | O que a distingue | Rastro / impacto |
|---|---|---|---|---|
| Raio Encadeado `chain_lightning` | raio | M | salta entre `qtd` alvos, 20% a menos por salto; forma `bifurcado` divide em 2 ramos | segmento elétrico entre alvos, cada salto 15% mais fraco |
| Estilhaço Glacial `glacial_shard` | gelo | M | ao acertar, `qtd` lascas voam para os vizinhos (`raio`) | lascas retas, impacto de cristal em cada vizinho |
| Leque `fan_of_arrows` | físico | M | `qtd` flechas abertas em `angulo`; forma `espiral` = 360° | leque do mesmo arco |

### 3.3 Queda do céu (sombra de aviso, corpo cai de C5)
| Skill | El. | Est. | O que a distingue | Rastro / impacto |
|---|---|---|---|---|
| Flecha Meteoro `flecha_meteoro` | fogo | M | bola de fogo cai, explode e deixa brasas (`duracao`); forma `brasas` = 3 quedas | cauda de fogo; cratera com brasas |
| **Cometa Gélido** `ice_comet` | gelo | **N** | bola de gelo cai, **congela/soma 2 acúmulos** e deixa **chão gelado** (lentidão `valor`, `duracao`) com rachaduras | cauda de cristais e faísca branca; explosão de gelo + decalque de rachaduras hexagonais |
| Chuva de Flechas `arrow_rain` | físico | M | `qtd` pulsos em área; forma `muro` (B) | flechas finas caindo, impactos no chão |
| Chuva Corrosiva `corrosive_rain` | veneno | M | pulsos que aplicam corrosão (recebe mais dano) | gotas ácidas, poça que cresce |
| Tornados (abaixo) também chegam pelo céu | | | | |

### 3.4 Tornado (flecha para cima, funil que age por `duracao`)
| Skill | El. | Est. | O que a distingue | Rastro / impacto |
|---|---|---|---|---|
| Tornado de Tempestade `storm_tornado` | raio | M | **puxa** os inimigos ao centro e fere em pulsos; forma `errante` persegue | funil azul alto, faíscas; coluna de raio na queda |
| **Ciclone Pestilento** `toxic_tornado` | veneno | **N** | **não puxa**: anda sozinho atrás do grupo mais denso (`valor` px/s), **empurra** para fora, envenena quem toca e **deixa poças** no caminho | funil verde baixo e largo, bolhas orbitando; rastro de poças (C0) que somem em 1,5 s |

### 3.5 Nova e anel (sai do arqueiro em todas as direções)
| Skill | El. | Est. | O que a distingue | Rastro / impacto |
|---|---|---|---|---|
| **Nova Gélida** `frost_nova` | gelo | **N** | anel de gelo cresce do arqueiro até `raio` em 0,3 s; todos levam dano + **2 acúmulos de frio**; `qtd` lascas voam para fora até 1,6× o raio | anel com borda cristalina (polígono com pontas), chão fica branco por 0,6 s; lascas giram |
| Prisão de Gelo `ice_prison` | gelo | M | área no ponto mirado, congela tudo por `duracao` | bloco de gelo em área (folha) |
| Leque em espiral (forma de `fan_of_arrows`) | físico | F | 360° de flechas | |
| Nova de raio / fogo | | B | só se a Nova Gélida provar a família: Trovoada (raios radiais) e Rajada de Brasas (anel de fogo) | |

### 3.6 Zona (marca no chão que pulsa)
| Skill | El. | Est. | O que a distingue | Rastro / impacto |
|---|---|---|---|---|
| Armadilha de Espinhos `spike_trap` | físico | M | dispara uma vez quando pisam, atordoa | |
| Bomba de Fumaça `smoke_bomb` | físico | M | lentidão, sem dano | |
| Bola de Veneno `venom_orb` | veneno | M | parábola, poça que lentifica, estoura em nuvem; forma `pustulas` (B) | bola verde, sombra no chão, nuvem no fim |
| Muralha de Brasas `muralha_brasas` | fogo | M | linha de chamas à frente | |
| **Haste Elétrica** `lightning_rod` | raio | **N** | a flecha **finca no ponto** e vira um para-raios: a cada `valor` s descarrega em `qtd` inimigos no `raio`; dura `duracao` | haste vertical com ponta brilhante, anel de glifo no chão pulsando a cada descarga; arcos até os alvos |

### 3.7 Rastejante (anda pelo chão)
| Skill | El. | Est. | O que a distingue | Rastro / impacto |
|---|---|---|---|---|
| **Serpente de Brasa** `fire_serpent` | fogo | **N** | uma chama **serpenteia pelo chão** até o inimigo mais próximo, muda de alvo quando ele cai, por `alcance` px; fere e queima quem toca; **deixa brasas** no caminho | cabeça de chama, corpo ondulante feito do rastro, brasas que apagam atrás (C0) |

### 3.8 Buff, marca e gatilhos
Marca do Caçador, Adrenalina e os quatro Arautos (Trovão, Peste, Gelo, Cinzas) seguem como estão; a identidade deles é a aura C1 e o gatilho (doc 33 seção 5).

**Cobertura do pedido do Will:** tornado de raio (M) e de veneno (N); bola de fogo (M) e de gelo (N) do céu; ataque em todas as direções de gelo (N); flecha que espalha dano (gelo M, raio M); flecha de raio/veneno/gelo/fogo como básico de escolha única (N).

## 4. Fichas das skills novas (números propostos, só CSV)
Colunas de `habilidades_arqueiro.csv`: `cd, dano, qtd, angulo, raio, duracao, alcance, valor, escala` (dano = multiplicador de `arrow_damage`).

| id | ramo | tier / pai | cd | dano | qtd | angulo | raio | duracao | alcance | valor | significado dos campos |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `lightning_rod` | raio | 2 / shock_arrow | 11 | 0.8 | 2 | | 220 | 5 | 600 | 0.4 | qtd = alvos por descarga; valor = s entre descargas |
| `toxic_tornado` | veneno | 3 / venom_orb | 15 | 0.5 | 3 | | 130 | 5 | 600 | 70 | dano por pulso de 0,5 s; qtd = dps do veneno; valor = px/s que anda |
| `ice_comet` | gelo | 2 / frost_arrow | 10 | 2.6 | 2 | | 130 | 3 | 600 | 0.35 | qtd = acúmulos de frio; duracao = chão gelado; valor = lentidão do chão |
| `frost_nova` | gelo | 3 / glacial_shard | 12 | 1.8 | 8 | 360 | 200 | 3 | 0 | 0.2 | qtd = lascas; duracao = frio; valor = lentidão por acúmulo |
| `fire_serpent` | fogo | 2 / flecha_ardente | 9 | 1.0 | 3 | 40 | 36 | 2.2 | 520 | 4 | raio = largura; duracao = vida (velocidade = alcance/duracao); qtd = s de queimadura; valor = dps; angulo = amplitude da onda |

Autocast (`habilidades_mira.csv`): `lightning_rod` grupo 600 min 2; `toxic_tornado` grupo 600 min 2; `ice_comet` grupo 600 min 1; `frost_nova` si 200 min 2; `fire_serpent` proximo 520 min 1.
Tags (`habilidades_tags.csv`): `lightning_rod` zona+area+raio+status; `toxic_tornado` area+zona+veneno+status; `ice_comet` area+gelo+status; `frost_nova` area+gelo+status; `fire_serpent` area+fogo+status.
Afinidades (`afinidades_arqueiro.csv`): colunas `id, elemento, dano, vel, perfura, qtd, raio, duracao, valor, icone`; valores iniciais: trovão 1.0/1.2/0/1/160/2.0/0.5; peste 0.9/0.85/1/1/0/3.0/3; gelo 1.0/1.0/0/1/0/3.0/0.15; cinzas 1.1/1.0/0/1/40/2.5/3.

## 5. Como cada família reage aos modificadores (complemento à tabela do doc 33 seção 5.1)
| Família | `raio` | `qtd` | `duracao` | `vel` | `forma` possível (backlog) |
|---|---|---|---|---|---|
| Queda do céu | sombra de aviso e explosão escalam juntas | mais quedas (cometa: 2 cometas menores, escala 0,7) | chão gelado/brasas duram mais | queda mais rápida (cauda mais longa) | `brasas` já existe no meteoro |
| Tornado | funil maior e mais grosso | pestilento: mais poças por segundo | mais voltas; último segundo afina | anda mais rápido | `errante` (tempestade) |
| Nova | anel maior, mais lascas na borda | mais lascas | frio dura mais | expansão mais rápida | `dupla` (dois anéis) |
| Zona (haste) | anel do glifo maior; arcos mais longos | mais alvos por descarga | haste dura mais | descargas mais rápidas | `tripla` (3 hastes em triângulo) |
| Rastejante | corpo mais largo | duas serpentes | anda mais longe | mais rápida | `bifurcada` |

## 6. Arte: o que se reaproveita e o que é novo
- **Rastro e impacto por elemento**: `godot/scripts2d/vfx_identidade_2d.gd` (vetorial, herdado da thread de direção visual), ligado ao básico com afinidade e às flechas elementais.
- **Recolor por shader** (doc 33, "elemento convertido"): shader único em `godot/scripts2d/recolor_2d.gd`. Parecer do Jev (01/11): recolor sozinho não muda a silhueta, então ele só entra junto com forma própria. Hoje: o funil do Ciclone Pestilento usa `raio/tornado_tempestade.png` com matiz para o verde ácido **mais** o funil achatado, o anel de lama e as bolhas em espiral desenhadas por código; o Cometa Gélido é **todo desenhado por código** (núcleo facetado hexagonal, cauda de cristais, halo), e só a explosão reaproveita `gelo/gelo_explosao.png`.
- **Arte provisória**: o funil do Ciclone e o corpo do Cometa são provisórios até as folhas pintadas chegarem. A revisora aprova a leitura da mecânica e a paleta; a arte final vem do backlog abaixo.
- **Folhas já existentes**: `gelo/gelo_lasca.png` (Nova), `raio/raio_arco.png`, `raio/raio_coluna.png`, `raio/raio_impacto.png` (Haste), `fogo/muralha_chama.png` e `fogo/brasas_chao.png` (Serpente).
- **Novas folhas pintadas** (backlog para o pipeline gpt-image no PC, prompts em `tools/arte/fx_arqueiro/leque/prompts_leque.json`): funil do ciclone verde próprio, cometa de gelo com cauda de cristal, cabeça da serpente, e **Trovoada** (nova de raio: estrela radial de relâmpagos saindo do arqueiro, nunca um anel, para não repetir a Nova Gélida). Até lá valem recolor e código, que a revisora aprova como arte de jogo ou devolve.
- **Serpente × Muralha de Brasas**: a serpente rasteja (corpo afilado, brasas vermelho-escuro `COR_BRASA_SERP` baixas no chão) e a muralha sobe (chamas altas e claras). Mesma paleta, silhuetas opostas.
- Ícones: geométricos de `icones.csv` até a leva de ícones pintados (doc 28).

### 6.1 Hierarquia de brilho (ajuste do Jev)
- Só o **primeiro alvo** de uma descarga ou salto recebe impacto cheio; alvos seguintes ficam em 40 a 60% (Haste: arco do 2º alvo a 60% e sem impacto; Eco do Trovão: impacto do salto a 70%).
- **Teto global de decalques** no chão: `fx_max_decalques` em `feel.csv` (12). Poças, brasas e chão gelado passam por `Vfx.decalque_cabe()` antes de nascer.
- Afinidade do básico é discreta: rastro curto e impacto pequeno; a skill ativa é sempre a mais brilhante da tela.
- Teste obrigatório: capturas com **1 e 20 inimigos** e versão em **escala de cinza**. As quatro afinidades precisam diferir sem cor: arco que salta (Trovão), flecha lenta e longa que atravessa (Peste), anel de cristais no alvo (Gelo), explosão curta com brasa no chão (Cinzas).

## 7. Orçamento (FPS; PR 188 é a base)
- Cada skill nova = 1 nó com `_draw`; sprites auxiliares ≤ 8 e curtos (lascas da Nova, arcos da Haste).
- Nada de `CPUParticles2D` novo; partículas são pontos desenhados no mesmo `_draw` (≤ 24 por efeito, regra do doc 33).
- Decalques (poças, brasas, rachaduras) ficam na lista interna do próprio nó (≤ 12) e não viram nós.
- Busca de alvos por `get_nodes_in_group("hurtable")` só nos pulsos (0,4 a 0,5 s), nunca por quadro, exceto a serpente (1 busca a cada 0,2 s).
- `Vfx.lotado()` / `registrar_animado` do PR 186 para os funis e a haste.

## 8. Plano de execução
1. Este documento + parecer do Jev (famílias, nomes, paletas).
2. PR único `feat/leque-skills` sobre o master já com o PR 186: afinidades (CSV, UI de escolha, `efeitos_arqueiro_afinidade_2d.gd`, teste), cinco skills (CSV, loc, ícones, efeitos por elemento, testes no `_testar_habilidades_arqueiro`), `recolor_2d.gd`, `vfx_identidade_2d.gd`, ferramenta de captura `tools/captura_skills_2d.gd` estendida às skills novas e às afinidades.
3. Capturas por skill (xvfb, 1 inimigo / 20 inimigos / escala de cinza) para a revisora; ajustes; CI verde; merge.
4. Backlog: folhas pintadas da seção 6, formas da seção 5, novas da família 3.5.

## 9. Checklist da revisora (Jev)
- [ ] Silhueta de cada skill nova reconhecível em captura parada a 3/4, sem ler texto.
- [ ] Duas skills do mesmo elemento nunca têm a mesma família de forma.
- [ ] Área desenhada = raio do CSV; sombra de aviso antes de toda queda.
- [ ] Nada cobre o arqueiro (C1 para auras, decalques em C0).
- [ ] Com 20 inimigos a tela continua legível (hierarquia de brilho do doc 33 seção 4).
- [ ] Afinidade: as quatro flechas diferem em velocidade, forma da ponta e impacto, não só em cor (teste em escala de cinza).
- [ ] Rastros e impactos vetoriais com acabamento pintado: miolo claro, halo, espessura variável e faíscas; nenhuma linha ou ponto chapado.
- [ ] Recolor por shader só com paleta aprovada (azul-gelo, verde-ácido, azul elétrico, laranja-brasa) e junto com silhueta própria.
