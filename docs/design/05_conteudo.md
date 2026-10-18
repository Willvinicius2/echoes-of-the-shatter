# 05 — Conteúdo do protótipo (Narrative & Content)

Fonte de regras: `docs/design/00_plano_existente.md` (seções 3 a 8), `docs/requisitos-qa/02_requisitos.md` (seção 2, escopo) e `docs/tecnico/06_dados.md`. Os números vêm do plano quando ele define; o que o plano não define está marcado **PROVISÓRIO** (seção 5). A história principal é do dono do projeto: nada aqui cria arco, revelação ou lore novo. Os textos de NPC são funcionais e provisórios.

## 1. O que foi preenchido

| Tabela (`Content/Data/`) | Linhas | Conteúdo |
|---|---|---|
| `classes.csv` | 1 | Guerreiro, recurso Ímpeto (ganha 10 ao acertar e 15 ao bloquear; perde 5/s fora de combate) |
| `class_stats.csv` | 5 | vida 120 (+12/nível), recurso 100, regeneração de vida 1 (+0,1), armadura 20 (+2), crítico 5% |
| `skills.csv` | 10 | 4 do Guerreiro (Corte de Ferro nv 1, Investida nv 2, Fenda de Pedra nv 3, Escudada nv 5) e 6 ataques de inimigo |
| `effects.csv` | 3 | Quebra de Guarda (até 3 acúmulos), Atordoamento, Brio do Trono Vazio (efeito do Único) |
| `enemies.csv` | 7 | 4 comuns, 2 elites (Escudada e Veloz) e o Guardião da Cripta |
| `enemy_attacks.csv` | 8 | um ataque por inimigo; o Guardião tem martelo em cone e golpe de escudo |
| `affixes.csv` | 8 | 4 prefixos (Robusto, Afiado, Blindado, Rachado) e 4 sufixos (Restauro, Presteza, Fornalha, Passos Leves) |
| `item_bases.csv` | 6 | espada, martelo, elmo, peitoral, luvas, botas (5 posições do protótipo) |
| `uniques.csv` | 1 | Martelo do Trono Vazio (só do Guardião, só no jogo manual) |
| `loot_tables.csv` | 4 | área, comum, elite, Guardião (Comum, Mágico e Raro por peso) |
| `loot_entries.csv` | 26 | Ouro, Lascas, 6 bases e 1 Único com `manualOnly = true` |
| `encounters.csv` | 8 | 7 encontros de patrulha e 1 de chefe |
| `maps.csv` | 1 | `map.act1.crypt` (Cripta Partida, monstro nível 3, tier 0) |

O Refúgio do Marco é hub sem combate, por isso não tem linha em `maps.csv` (que exige encontros). Ele existe só em localização (`area.refuge.name`).

`Loc/`: `ui.csv` (menus, HUD, inventário, opções, save), `content.csv` (classe, habilidades, efeitos, inimigos, áreas, itens, afixos, Único, estatísticas, raridades, posições), `expedition.csv` (configuração e relatório do Tico), `dialogue.csv` (NPCs e falas de Ilsa e Tico). Colunas: `key,pt_BR,en,es,context,gender`. `es` fica vazia (espanhol fora do protótipo). `context` guarda a área da UI, o limite de caracteres (`max=N`, vale para pt_BR e en) e a marca `provisório`. `gender` é `m` ou `f` do termo.

## 2. Tom de voz

- Português do Brasil, frases curtas, sóbrio e levemente melancólico; a ironia fica com a Ilsa e a energia com o Tico.
- Imperativo de UI direto ("Coletar", "Equipar"). Sem gíria datada e sem exclamação fora do Tico.
- Em inglês, o mesmo registro, sem trocadilhos que dependam do português.
- Habilidades descrevem só o que o GDD diz (seção 4 do plano). Números aparecem pela UI, vindos dos dados, não no texto.
- Nunca mostrar percentual negativo nas telas de expedição e no HUD (RF-45). O cansaço aparece como Vigor, e o Fervor como "+200% XP".

## 3. Glossário (termos fixos)

| pt_BR | en | Observação |
|---|---|---|
| Echoes of the Shatter | Echoes of the Shatter | nome único, nunca traduzido |
| o Shatter | the Shatter | evento que partiu o Arquivo; sem artigo de gênero em inglês |
| Arquivo Vivo | Living Archive | |
| Aural | Aural | o mundo |
| Recuperador | Recoverer | o jogador |
| Ímpeto | Momentum | recurso do Guerreiro (m) |
| Ouro | Gold | moeda |
| Lascas | Shards | material (f, plural) |
| Marco de Retorno / Marco | Return Marker / Marker | |
| Cargas do Marco | Marker Charges | custo de expedição |
| Fervor (do Recuperador) | Fervor | bônus de jogar na mão |
| Vigor | Vigor | barra de cansaço da patrulha |
| Expedição / patrulha | Expedition / patrol | "patrulha" é a execução idle |
| Relatório de expedição | Expedition report | entregue pelo Tico |
| Quebra de Guarda | Guard Break | efeito |
| Comum, Mágico, Raro, Único | Common, Magic, Rare, Unique | maiúscula inicial |
| Refúgio do Marco | Marker Refuge | hub |
| Cripta Partida | Broken Crypt | área |

Famílias de inimigo (IDs em `family.*`, sem tabela): `soldier_echo` (Ecos de soldado), `altered_fauna` (Fauna alterada), `construct` (Constructos), `shooter` (Atiradores).

Concordância de itens: `gender` da base (`m`/`f`) e `context` com `plural` (Luvas, Botas, Lascas). Prefixos têm quatro formas (`.name`, `.name_f`, `.name_mp`, `.name_fp`); sufixos são invariáveis. Raridade tem `.name` e `.name_f`. Padrões de montagem em `item.pattern.*`; nunca concatenar pedaços de frase no código. Exemplos: "Espada de Ferro Afiada de Presteza"; "Luvas de Couro Robustas".

Placeholders de localização: `{nome}` entre chaves, sempre com nome (`{value}`, `{stat}`, `{pct}`, `{hours}`).

## 4. Fidelidade ao GDD

- Descrições das 4 habilidades repetem a coluna "O que faz" do plano (seção 4). Escudada atordoa "inimigos comuns": os dados aplicam `effect.stun` sempre; a restrição a comuns precisa do ShatterCore (elite e chefe imunes).
- Um Único tem "atributos fixos + 1 efeito + 1 contrapartida" (plano seção 6): +25% de dano corpo a corpo, efeito ao derrotar inimigo (+20% de dano corpo a corpo por 4 s) e contrapartida de movimento (reduzida em 10%). O texto `.desc` bate com `uniques.csv` e `effects.csv`.

## 5. Provisório

Todos os valores numéricos abaixo foram escolhidos aqui porque o plano não os define. Servem para testar; balancear no playtest.

1. Vida, armadura, XP, velocidade, aggro e dano de todos os inimigos e do Guardião; vida e atributos do Guerreiro; peso e dano das armas; valores e faixas dos afixos; pesos e quantidades do loot; chances de queda (chefe ≈ 19% de Único por morte).
2. Custos de Ímpeto, recargas, tempos (preparação, impacto, recuperação), alcance e raio das habilidades; coeficientes de rank.
3. Ganho de Ímpeto por bloqueio (15) e decaimento (5/s).
4. Efeitos `guard_break` (+10% de dano recebido por acúmulo, 8 s) e `stun` (0,8 s, modelado por `move_speed`/`attack_speed` `more -1`, porque o esquema não tem atordoamento).
5. Nome, efeito e contrapartida do Único; ele só usa a imagem do cavaleiro que protege "um rei que não está mais lá" (plano seção 3).
6. Todos os diálogos de Ilsa e Tico, a fala de fase 2 do chefe, a dica de relatório e os nomes de elites.
7. Nomes das 8 afixos e das 6 bases.
8. Perfil idle: `idleAvgTargetsHit`/`idleApproachTime` são estimativas e nenhuma habilidade tem `idleSupported = true` (falta amostra de paridade). Isso bloqueia a expedição (RF-43) até a calibração.
9. Poção de Vida e Esquiva: textos prontos (`potion.life.*`, `dodge.*`), mas sem tabela de dados (ver pendências).

## 6. Divergências e pendências

- **Nível de liberação.** O plano põe Fenda de Pedra no nível 5 e Escudada no 3; o `docs/requisitos-qa/02_requisitos.md` (seção 2.1) põe Fenda no 3 e deixa a barra com 3 habilidades. Os dados seguem o 02: Fenda nv 3. Escudada, fora do protótipo, ficou em nv 5.
- **Poções (P1).** Sem tabela nem chaves em `rules.csv`. Valores sugeridos: 2 poções, cura de 40% da vida máxima, 3 cargas e recarga de 20 s por carga (todos provisórios). Textos em `potion.life.*`.
- **Esquiva (P4).** Sem tabela. Valores do plano para quem implementar: 0,35 s, invulnerável nos primeiros 0,2 s, 3 cargas, 1,5 s por carga. Texto em `dodge.*`.
- **Padrões de fase do Guardião (P4)** (invocar 2 Sentinelas na fase 2, escudo frontal) e modificadores de elite (escudo, veloz) não têm dados. As elites fixas aproximam o "escudo" com armadura e o "veloz" com `moveSpeed`.
- **Único só do Guardião (P5).** Garantido hoje só pelo conteúdo: o Único está apenas em `loot.crypt.guardian`.
- **`chanceElite` dos encontros** (0 a 0,1) é provisória e não substitui as elites fixas.
- **Validador.** O agente de conteúdo não tinha como executar shell nesta rodada. As tabelas foram conferidas à mão contra os esquemas e o `validate_data.py` (cabeçalhos, nº de colunas, IDs, referências, chaves de localização). Rodar `python tools/dados/validate_data.py` antes de integrar.
