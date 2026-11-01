# 32. Arqueiro elemental (inspirado no Path of Exile 2): plano das 4 árvores

Pedido do Will (01/11/2026): o Arqueiro ganha tiros elementais, habilidades de efeito grande e passivas "Herald", em quatro árvores: **raio, veneno, gelo e fogo**. Aqui fica só o plano; nenhum número de balanceamento vai ao código (tudo em `godot/data2d/habilidades_arqueiro.csv`). Os nomes e mecânicas são do nosso jogo, só a ideia vem do PoE 2.

## 1. Encaixe com o que já existe
- **Autocast** (doc 31): toda ativa dispara sozinha pela coluna `mira` de `habilidades_mira.csv`; só a **ult** é manual. As novas ativas entram como linhas novas desse CSV.
- **Gemas dropadas, sem nível de personagem**: cada habilidade nova é uma **gema** (item que cai de inimigo, elite ou baú). Gema de habilidade ativa ou Herald ocupa 1 dos 4 slots; o nível da habilidade vem do nível da gema (`nivel_max` do CSV), não do personagem. A árvore atual de pontos (doc 30) vira a "estante" de gemas conhecidas por ramo. Como o core hoje trabalha com pontos (`habilidade_aprender`), a ligação gema → habilidade aprendida é uma decisão técnica da thread de integração, sem mexer em regra do core além do que o doc 31 (H4) já prevê.
- **Efeitos** seguem o contrato de `efeitos_arqueiro_2d.gd` (`executar(efeito, jogador, def, nivel, mira)`), zonas em `zona_2d.gd`, status em `enemy_2d.gd` (`aplicar_status`). Stats novos de passivas já existem (`crit_chance`, `poison_dps`).
- **Arte**: estilo pintado à mão do doc 26 (não pixel art). Folhas 5 direções só para personagem; **efeitos são folhas simples** (quadros em linha, fundo transparente).

## 2. As quatro árvores
Cada árvore tem 4 peças: um **tiro elemental** (substitui/enfeita o básico, efeito de status), duas **ativas** (uma de projétil, uma de área ou combo) e um **Herald** (passiva de gatilho). Tier e pais seguem a lógica do doc 30.

| Árvore | Tiro (T1) | Ativa A (T2) | Ativa B (T3) | Herald (passiva) |
|---|---|---|---|---|
| **Raio** | **Flecha Elétrica**: acerta e aplica *choque* (+dano recebido curto) | **Raio Encadeado**: a flecha vira raio que salta entre N inimigos próximos, cada salto perde dano | **Tornado de Tempestade** (ult candidata): atira para o alto, a flecha cai no alvo e vira tornado que arrasta e fere em área por alguns segundos | **Arauto do Trovão**: inimigo que morre sob *choque* solta um raio que fere vizinhos |
| **Veneno** | **Flecha Peçonhenta**: acerta e empilha veneno (dano contínuo) | **Bola de Veneno**: lança para o alto, cai e vira poça que fere e lentifica; ao fim estoura em nuvem | **Chuva Corrosiva**: zona grande de pulsos que reduz defesa | **Arauto da Peste**: veneno em inimigo morto se espalha a vizinhos |
| **Gelo** | **Flecha Gélida**: acerta e aplica *frio* (lentidão que acumula até congelar) | **Estilhaço Glacial**: ao acertar, racha em N lascas que se espalham para outros alvos | **Prisão de Gelo** (ult candidata): cone/área que congela tudo por pouco tempo | **Arauto do Gelo**: inimigo congelado que morre explode em estilhaços |
| **Fogo** | **Flecha Ardente**: acerta e *queima* (dano contínuo) | **Flecha Meteoro**: sobe e cai em área, deixa chão em brasas | **Muralha de Brasas**: linha de fogo no chão que queima quem cruza | **Arauto das Cinzas**: dano que sobra num abate (overkill) vira explosão de fogo em volta |

Regras de projeto:
- Raio e fogo causam dano direto alto; veneno e gelo controlam. Cada árvore tem 1 ult candidata (manual): o Will escolhe uma ou mais depois de ver tudo animado (decisão da thread de integração, não do Will agora).
- Status distintos e legíveis: choque (azul-branco, faíscas), veneno (verde, bolhas), frio (azul claro, cristais), queimadura (laranja, brasas). Cada um tem um overlay curto no inimigo.
- Reaproveitar: `fan_of_arrows`, `arrow_rain`, `explosive_arrow`, `venom_tips`, `spike_trap` já cobrem "leque", "chuva", "explosão" e "veneno passivo". A thread de cada árvore decide se vira variante elemental desses (mesmo efeito, outro elemento e VFX) antes de criar efeito novo.

## 3. Sprites e VFX que faltam (por árvore)
O que existe hoje: sprites do arqueiro e inimigos, 10 ícones de HUD, `godot/art2d/fx/` vazio. Então **toda arte de efeito é nova**. Lista mínima por árvore:
1. Projétil do tiro (cabeça + rastro, 4 a 6 quadros em loop) e impacto (6 a 8 quadros).
2. Ativa A: o efeito próprio (raio encadeado = segmentos de arco; bola de veneno = bola no ar + poça; estilhaço = cristal + lascas; meteoro = bola + cratera).
3. Ativa B: animação de área (tornado 8 quadros em loop; chuva; prisão; muralha).
4. Overlay de status no inimigo (4 a 6 quadros em loop) e Herald: aura leve no arqueiro mais o gatilho (raio, nuvem, explosão de gelo, explosão de cinzas).
5. Ícones 128 px das 4 peças, no molde do doc 29.

Como gerar:
- **ChatGPT (gpt-image) pelo Codex CLI**, como nas threads de ícones e HUD: `docs/arte/referencias-geracao/scripts/gerar.py`, fundo magenta e `tools/arte/ui_gpt_image/key.py`. Prompt em folha de quadros em linha, mesma luz (alto à esquerda) e contorno do doc 26. Prompts versionados em `tools/arte/fx_arqueiro/`.
- **pixelfx** (catálogo, linha 20): é pixel art em código; serve para referência de tempo e forma de partículas (`fire/`, `ice/`, `impacts/`), não como arte final, porque o visual aprovado é pintado.
- Animação do arqueiro (pose de disparo para cima, lançar): quadros pintados da própria folha; Mixamo/KayKit (`docs/arte/animacao_mixamo.md`) só como referência de pose. O repositório de animações que o Will citou antes: a thread de cada árvore deve conferir o histórico do projeto e o `catalogo-ferramentas.md`; o que consta lá hoje é `pixelfx`, `kimodo`, Mixamo e KayKit.
- Toda arte final passa pela revisora "Agente escolhedor de ferramentas" antes do Will; régua: estandarte v2 (sem aspecto de massinha).

## 4. Divisão de trabalho
Recomendação: **4 threads, uma por árvore** (Raio, Veneno, Gelo, Fogo), mais esta thread como integradora. Cada thread é dona só destes arquivos novos:
- `godot/scripts2d/efeitos_arqueiro_<elemento>_2d.gd` (efeitos da árvore; o `efeitos_arqueiro_2d.gd` só delega por `match`, edição mínima feita **só pela integradora**)
- `godot/art2d/fx/<elemento>/*.png` e `tools/arte/fx_arqueiro/<elemento>/`
- `docs/design/32_<elemento>.md` (números propostos e notas)

Arquivos compartilhados, donos únicos (evita conflito): `habilidades_arqueiro.csv`, `habilidades_mira.csv`, `loc_2d.csv`, `enemy_2d.gd` (status) e `test_2d.gd` ficam com a integradora; as threads entregam as linhas em `docs/design/32_<elemento>.md` e a integradora aplica. Ordem: (1) tiros elementais + status (base comum), (2) ativas A e B, (3) Heralds, (4) ícones e polimento, (5) decisão das ults.

## 5. Critério de pronto
Os 4 tiros, 8 ativas e 4 Heralds carregam sem erro no `test_2d.gd`, disparam sozinhos pelo autocast (ult manual), cada um com animação própria aprovada pela revisora, números só no CSV, textos só por chave em `loc_2d.csv`, CI `cliente2d` verde.

## 6. Notas da pesquisa de PoE 2 (thread de pesquisa, 01/11/2026)
Fonte completa: `analises/poe2-arco-referencias.md` na pasta do projeto. Decisões técnicas tomadas aqui:
- **Heralds são gatilhos de morte com status.** Coluna nova `gatilha_em` em `habilidades_arqueiro.csv` (dono: integradora), com os valores `choque_morte`, `congelado_morte`, `overkill`, `veneno_morte`. Trovão: morte de chocado solta raios; Gelo: morte de congelado explode; Cinzas: overkill explode e queima; Peste: morte de envenenado espalha veneno.
- **Overkill** (Arauto das Cinzas) exige o dano que sobra no abate. O cliente calcula a partir da vida restante do inimigo no golpe fatal; só vai ao core se a regra precisar de determinismo (decidir na integração).
- **Sinergias cruzadas** entram na fase de polimento, depois das 4 árvores base: Raio×Gelo (Trovão e Gelo ativam um ao outro) e Veneno×Fogo (nuvem de veneno detona com fogo).
- Canalização vira autocast com salto curto. "Ritmo" (inspirado nas Frenzy Charges) e passivas de ascendência (dano perto/longe, munição, vento) ficam como backlog opcional.
