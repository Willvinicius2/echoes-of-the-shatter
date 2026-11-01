# 33. Árvore de passivos do Arqueiro e como ela muda as skills (01/11/2026)

Pedido do Will: planejar a árvore de passivos (inspirada no Path of Exile 2) e **quanto ela impacta o jogo**: mudar a forma da skill, o tamanho, a velocidade, o dano, a quantidade de projéteis. Este documento é só o plano; nenhum número vai ao código (tudo em CSV). Foco no Arqueiro; Guerreiro e Mago herdam o mesmo formato depois. Mecânicas de referência: `analises/poe2-arco-referencias.md` (só a ideia, nomes e números são nossos).

Parte dos docs 29 (base de habilidades), 30 (skills do Arqueiro), 31 (hordas, autocast, gemas) e 32 (quatro árvores elementais e Heralds). Números abaixo são **propostas de ponto de partida**; confiança baixa até o bot de corridas (H4) medir.

## 1. O que já existe e o que falta
| Já existe (master) | Limite hoje |
|---|---|
| Árvore de **habilidades** em pontos (`habilidades_arqueiro.csv`: ramo, tier, pai, `nivel_max`, `escala` de 15% por nível), tecla T | Aprender uma skill e subir o nível dela é a única forma de a mudar. Não há nó que mude *forma*, *quantidade* ou *velocidade*. |
| Passivas simples (`tipo=passiva`, `stat/modo/valor`) somam em stats do jogador (`arrow_damage`, `crit_chance`, `poison_dps`) | Só mexem no jogador, nunca numa skill específica nem num grupo de skills (todas as de projétil, todas de raio...). |
| 4 ramos elementais e 4 Heralds (doc 32), autocast pela coluna `mira` (doc 31) | Heralds têm números fixos; nada os melhora. |
| Gemas de XP e cartas de nível na corrida (H4) | As cartas ainda não têm um destino comum com a árvore. |

Falta: (a) um **pipeline único de modificadores** que qualquer fonte (nó, carta, gema, item) usa para alterar uma skill; (b) uma **árvore em grafo** (nós ligados por vizinhança, como no PoE 2) que distribui esses modificadores; (c) **formas alternativas** de skill escolhidas na árvore.

## 2. Três camadas de poder (quem mexe em quê)
| Camada | Quando muda | Quem escolhe | Efeito típico |
|---|---|---|---|
| **Gema** (nível 1 a 5) | Drop, fusão | Sorte e jogador | Escala a skill inteira (`escala` do CSV, já existe) |
| **Árvore de passivos** (meta, permanente) | Entre corridas, com pontos | Jogador (a "build") | Muda forma, área, quantidade, velocidade, status, gatilhos de **grupos** de skills ou de **uma** skill |
| **Cartas da corrida** (temporárias) | A cada nível dentro da fase | Jogador, 1 de 3 | Pequenos incrementos, ou escolher entre dois nós "da árvore" já desbloqueados |

Regra de ouro: **a árvore define o estilo de jogo; a gema define a potência; a carta define a sorte da corrida.** Uma skill nunca depende de nó para funcionar; o nó a especializa.

## 3. Pipeline de modificadores
Toda skill é uma linha base (CSV) mais uma lista de modificadores. Função pura `resolver(skill, mods, nivel_gema) -> def`, que devolve o mesmo `def` que os efeitos já recebem (`efeitos_arqueiro_*_2d.gd`), então **nenhum efeito precisa mudar de contrato**. Ordem de cálculo por campo:

`final = (base + soma(add)) × (1 + escala × (nivel_gema − 1)) × (1 + soma(inc)) × produto(1 + mais_i)`, depois aplica os tetos (seção 3.3).

- `add`: soma plana (ex.: +1 projétil, +2 saltos).
- `inc` ("aumentado"): percentuais **somados entre si** (ex.: +15% e +20% = +35%). É o que a maioria dos nós pequenos dá.
- `mais` ("mais"): multiplicador **separado**, raro (nós notáveis e keystones); é o que faz um nó parecer grande.
- `set`: troca de valor ou de **forma** (seção 5); no máximo um por campo.

### 3.1 Campos que um modificador pode alterar
| Eixo (pedido do Will) | Campo no `def` | Existe? | Exemplo de nó |
|---|---|---|---|
| Dano | `dano` | sim | +12% dano de projétil |
| Quantidade de projéteis | `qtd` | sim | +1 flecha no Leque |
| Tamanho / área | `raio`, `angulo` | sim | +20% de área; cone de 50° para 70° |
| Alcance | `alcance` | sim | +15% alcance de projétil |
| Duração | `duracao` | sim | +25% duração das zonas |
| Recarga | `cd` | sim | −10% recarga de ativas de raio |
| **Velocidade do projétil** | `vel` (px/s) | **novo** | +20% velocidade (acerta mais, esquiva menos) |
| **Perfuração / ricochete / salto** | `perfura`, `ricochete`, `saltos` | **novo** (`perfura` já é stat `arrow_pierce`) | +2 saltos no Raio Encadeado |
| **Chance de status** | `chance_status` (0 a 1) | **novo** | +15% de chance de congelar |
| **Força do status** | `valor` (já guarda choque/lentidão) e `dano_status` | parcial | choque dá +30% dano recebido |
| **Forma** | `forma` (id de variante) | **novo** | Flecha Gélida passa de cone para anel |
| **Gatilho (Heralds)** | `cargas`, `fracao`, `min_overkill_pct` | parcial | Trovão: 3 para 5 cargas |
| Crítico | `crit_chance`, `crit_mult` | sim (jogador) | passa a valer só para projétil de raio |

### 3.2 Tags e alvo do modificador
Cada linha de `habilidades_arqueiro.csv` ganha a coluna `tags` (lista com `+`): `projetil`, `area`, `zona`, `cone`, `salto`, `ativa`, `herald`, `basico`, mais o elemento (`raio`, `gelo`, `fogo`, `veneno`, `fisico`). O modificador mira em **um** destes alvos:
- `skill:<id>` — só aquela skill (ex.: `skill:chain_lightning`).
- `tag:<tag>` — todas as skills com a tag (ex.: `tag:projetil`, `tag:gelo`, `tag:area`).
- `global` — o jogador (stats que já existem).

Isso dá a sensação de PoE 2: um nó "+1 projétil" vale mais em um build com muitas skills de projétil; "+área" vale mais para quem tem chuva, tornado e meteoro.

### 3.3 Tetos (para o jogo continuar legível com ~40 inimigos vivos, doc 31)
Valores no CSV `passivas_limites.csv` (novo): `qtd` máx. = base + 6; `raio`/`angulo` até +150% (cone nunca passa de 360°); `cd` mínimo = 35% da base; `vel` até +100%; projéteis simultâneos na tela `max_projeteis` = 120 (excedentes são descartados do mais antigo); pulsos de zona por frame limitados. Nó que estoura o teto não dá erro; o excesso some e a UI mostra "no limite".

## 4. A árvore (grafo)
Formato à moda PoE 2, mas pequeno: **~76 nós na v1**, uma região central e sete setores. O início é a base do Arqueiro; cada região se liga às vizinhas por caminhos de nós pequenos, então especializar em dois elementos custa pontos de passagem (a escolha do jogador).

| Setor | Nós | O que mexe | Skills do doc 32/30 que ele serve |
|---|---|---|---|
| **Centro (Arqueiro)** | 8 | dano geral, crítico, cadência do básico | tudo |
| **Precisão** | 8 | perfuração, crítico, velocidade de projétil, dano longe/perto | Disparo Carregado, Tiro Certeiro, básico |
| **Caça** | 8 | quantidade e área (leque, chuva, armadilha, explosiva) | skills de área |
| **Sombra** | 8 | esquiva, salto, cadência por acerto, vento | Salto Atrás, Adrenalina |
| **Raio** | 11 | saltos, choque, Trovão | Flecha Elétrica, Raio Encadeado, Tornado |
| **Veneno** | 11 | stacks, propagação, zonas | Flecha Peçonhenta, Bola, Chuva Corrosiva |
| **Gelo** | 11 | frio, lascas, congelar | Flecha Gélida, Estilhaço, Prisão |
| **Fogo** | 11 | queima, overkill, explosões | Flecha Ardente, Meteoro, Muralha |

Tipos de nó (e orçamento de poder, ver 7):
| Tipo | Quantidade (v1) | Efeito |
|---|---|---|
| **Pequeno** | ~48 | 1 modificador `inc` ou `add` pequeno de um grupo (por tag) |
| **Notável** | ~18 | 2 modificadores ou 1 `mais`; sempre específico de **uma** skill ou de um status |
| **Transforma** | ~6 | muda a **forma** de uma skill (seção 5); um por skill, exclusivos entre si |
| **Keystone** | ~4 | grande ganho com **custo real** (seção 6) |
Pontos de passiva: 1 por onda concluída e +3 com o Guardião (reaproveita a ideia de `skill_points_room/boss`; chaves novas em `run_settings.csv`, valores provisórios); meta de ~35 pontos numa build completa depois de ~10 corridas. Redistribuir é de graça (decisão do doc 29). A UI é a mesma tecla T, com duas abas: **Habilidades** (doc 29) e **Passivos**.

## 5. Formas alternativas ("Transforma")
Uma skill tem uma `forma` base e até 2 formas alternativas, cada uma um valor da coluna `forma` que o script do efeito trata num `match`. A forma **reaproveita o mesmo VFX** (escala, rotação, cor) sempre que der, para não custar arte nova.
| Skill | Forma base | Forma alternativa (nó "Transforma") | Muda | Arte nova? |
|---|---|---|---|---|
| Flecha Gélida | cone de lascas à frente | **Anel Gélido**: nova de gelo em volta do alvo | `angulo` 360°, dano −25%, `raio` +40% | não (mesma lasca em anel) |
| Chuva de Flechas | zona circular | **Muro de Flechas**: faixa larga e estreita | `raio` vira largura x profundidade | não |
| Raio Encadeado | salta entre inimigos | **Raio Bifurcado**: divide em 2 ramos no primeiro alvo | `saltos` −2, ramos +1, dano por ramo −30% | pouca (reuso do segmento) |
| Bola de Veneno | poça + nuvem final | **Pústulas**: 3 bolhas menores que estouram em sequência | `qtd` 3, `raio` por bolha −45% | pouca |
| Flecha Meteoro | 1 queda em área | **Chuva de Brasas**: 3 quedas menores em linha | `qtd` 3, área individual −35% | não |
| Tornado de Tempestade | tornado parado que puxa | **Tornado Errante**: o tornado persegue o inimigo mais próximo | `vel` do tornado, `duracao` −30% | não |
| Leque de Flechas | cone de 5 flechas | **Salva em Espiral**: 8 flechas em 360° | `qtd` 8, `angulo` 360°, dano −35% | não |
Regras: uma forma alternativa **não some** com o nível da gema; trocar de forma é redistribuição gratuita; cada nó "Transforma" mostra na UI "antes → depois" com números.

## 6. Keystones (trocas de verdade)
| Keystone (nome provisório) | Ganho | Custo | Interação |
|---|---|---|---|
| **Mãos Rápidas** | `cd` de tudo −30%, cadência do básico +25% | `dano` −20% em tudo | Bom para status e Heralds, ruim para chefes |
| **Tiro Único** | `dano` +60% no básico e Disparo Carregado, `perfura` +2 | `qtd` fixa em 1 (leque, rajada e salva ficam com 1) | Build de precisão/crítico |
| **Mar de Flechas** | `qtd` +2 em skills de projétil | `dano` por projétil −25%, `angulo` +15° | Sinergia com Heralds de choque/veneno (mais acertos, mais status) |
| **Tempestade Perpétua** | Heralds ganham +2 cargas ou +50% `raio`; abate com status recarrega 1 s da ult | status dura −40% | Obriga a *matar* os alvos com o status certo |
Máximo de **1 keystone** por build na v1 (ou 2 depois do Guardião da Região 1); bloqueio por exclusão mútua no CSV (coluna `exclui`).

## 7. Interação com o resto do jogo
- **Autocast (doc 31)**: mais `qtd` abre o leque em vez de empilhar na mesma linha (cada projétil extra soma +6° de `angulo`); `vel` alta pede menos antecipação da mira (`alvo_auto` usa a velocidade do `def`); `min_alvos` de `habilidades_mira.csv` não muda.
- **Mana/recarga**: nós de `cd` alteram só a recarga, não o `custo`; um nó que diminui mana vira `custo` `inc` negativo, nunca abaixo de 0.
- **Status e Heralds (doc 32)**: nós de status mexem em `chance_status`, `valor` (força), `duracao` e nos números do gatilho (`cargas`, `raio`, `fracao`). Os Heralds podem ganhar *formas* próprias no futuro (backlog).
- **Cartas e gemas**: uma carta de nível pode ser "ativar o nó N da árvore para esta corrida" (se já desbloqueado) ou um incremento pequeno; gema de skill dá `escala` e, no nível 5, destrava 1 slot extra de nó "Transforma" (proposta).
- **Hordas e orçamento de poder**: calibração com o `curva_horda.csv` do H4. Meta de design (provisória, a confirmar pelo bot): build de ~35 pontos ≈ **3× a 4×** o DPS da mesma build sem árvore; um nó pequeno ≈ +4% do DPS efetivo da skill-alvo, um notável ≈ +10%, um Transforma ≈ troca de papel (não é sempre mais dano), um keystone ≈ +25% com custo. Número final fica no CSV; revisão a cada mudança de `curva_horda.csv`.
- **Desempenho e leitura**: projéteis simultâneos limitados (3.3); VFX usam o `escala` do `def` (nunca arte nova por tamanho); zonas grandes mantêm o telégrafo de 0,6 s (doc 32).
- **Determinismo**: o `resolver` é uma função pura de (CSV, nós ativos, nível), então a mesma build dá o mesmo `def`. Primeiro em GDScript no cliente 2D (como `escala`, `habilidades_2d.def_nivel`); migrar para o ShatterCore só se o `resultHash` do simulador idle precisar da build (decisão do pacote P1).

## 8. Dados (propostas de formato)
`godot/data2d/passivas_arqueiro.csv` (um nó por linha):
`id,setor,tipo,x,y,vizinhos,custo,alvo,campo,op,valor,forma,exclui,icone`
- `vizinhos`: ids separados por `+`; o nó só abre se um vizinho está ativo (o centro começa ativo).
- `alvo`: `skill:<id>`, `tag:<tag>` ou `global`; `campo`: coluna do `def` (3.1); `op`: `add`, `inc`, `mais`, `set`.
- Nó com dois efeitos usa duas linhas com o mesmo `id` (`campo` diferente).
- Textos por chave: `passivo.<id>.name` e `passivo.<id>.desc` em `loc_2d.csv`; sem texto no código.
Exemplos (propostas):
```
p_proj_vel_1,precisao,pequeno,..,..,centro,1,tag:projetil,vel,inc,0.10,,,
p_chain_saltos,raio,notavel,..,..,p_raio_2,2,skill:chain_lightning,saltos,add,2,,,
p_chain_bifurcado,raio,transforma,..,..,p_chain_saltos,3,skill:chain_lightning,forma,set,,bifurcado,p_chain_longo,
p_area_1,caca,pequeno,..,..,centro,1,tag:area,raio,inc,0.12,,,
p_gelo_anel,gelo,transforma,..,..,p_gelo_2,3,skill:frost_arrow,forma,set,,anel,,
k_mar_flechas,centro,keystone,..,..,p_proj_qtd_2,4,tag:projetil,qtd,add,2,,k_tiro_unico,
k_mar_flechas,centro,keystone,..,..,p_proj_qtd_2,4,tag:projetil,dano,mais,-0.25,,k_tiro_unico,
```
Estado salvo: `meta.passivos = [ids]` por classe (migração da `meta_2d.gd`, ao lado de `habilidades`).

## 9. Exemplos de impacto (leitura rápida)
Raio Encadeado (base do doc 32: dano 1,6, `qtd` 4 alvos, `raio` 220, cd 9) com nó "+2 saltos", "+20% área de salto" e Transforma Bifurcado: 6 alvos, `raio` 264, dois ramos; o dano por ramo cai 30%, o total por conjuração sobe porque dobra o alcance de alvos. Flecha Elétrica base → com "+20% velocidade" e "+1 perfura" → mais acertos em linha, o que alimenta o choque e o Arauto do Trovão. Leque com Mar de Flechas: de 5 para 7 flechas, cada uma −25% de dano, cone 50° → 65°. Chuva de Flechas com 2 nós de área e 1 de duração: raio 170 → 214, zona 2,4 s → 3,0 s.

## 10. Plano de execução (pacotes, uma thread cada; Sonnet 5.5, Opus só se mudar o contrato do core)
| # | Pacote | Entrega | Dono dos arquivos | Depende de |
|---|---|---|---|---|
| P1 | Pipeline de modificadores | `resolver`, tags, tetos, testes em `test_2d.gd`; `habilidades_2d.def_nivel` passa a usar | `habilidades_2d.gd`, `passivas_limites.csv` | — |
| P2 | Dados da árvore v1 | `passivas_arqueiro.csv` (~76 nós), `loc_2d.csv`, validação do grafo (sem nó órfão, sem ciclo de exclusão) | CSV e loc | P1 |
| P3 | UI da árvore de passivos | aba Passivos (zoom, arrastar, pré-visualização antes→depois, redistribuir) | `arvore_ui_2d.gd`, `hud_*` | P2 |
| P4 | Formas e campos novos nos efeitos | `vel`, `saltos`, `ricochete`, `chance_status`, `forma` lidos pelos efeitos | `efeitos_arqueiro_*_2d.gd` | P1 |
| P5 | Cartas + save | ligação às cartas do H4, `meta.passivos`, migração | `upgrades_2d.gd`, `meta_2d.gd` | P1, H4 |
| P6 | Balanceamento | bot de corridas mede DPS por build tipo (precisão, leque, raio, gelo, veneno, fogo), calibra o orçamento | `tools/corridas_2d.gd`, números dos CSV | P2 a P5 |
Critério de pronto: CSV validado, `test_2d.gd` com testes do resolver (ordem add/inc/mais, tetos, exclusões), pelo menos 2 builds tipo atravessam a fase de ~8 min no bot, nenhum número no código, CI `cliente2d` verde.

## 11. Decisões tomadas e pontos abertos
Decididas aqui (técnicas): grafo pequeno (76 nós) em vez de uma árvore gigante; `inc` somado e `mais` separado (como PoE 2); tags para alvo; uma forma por skill; resolver em GDScript no cliente; keystone limitado a 1; formas reaproveitam VFX. Abertas para a revisão final do Will, sem bloquear P1 a P4: (a) quantos pontos por onda (provisório); (b) se os keystones ficam na v1 ou entram depois do Guardião; (c) se gemas no nível 5 destravam slot extra de "Transforma"; (d) nomes finais dos nós (os daqui são provisórios).
