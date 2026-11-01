# 34. Passivas da partida (cartas de nível e preparos da árvore)

Decisão do Will (01/11/2026), encaixe técnico em `33_arvore_passivos_arqueiro.md` seção 13. Este doc diz **como ficou**.

## 1. Três camadas, um pipeline
| Camada | Muda quando | Dura | Onde mora |
|---|---|---|---|
| Árvore fixa | entre corridas, com pontos de passivo | para sempre | `passivas_<classe>.csv` |
| Cartas de nível | a cada nível da corrida (1 de 3 cartas) | até o fim da corrida | `upgrades.csv` (o core sorteia e soma) |
| Preparos | ao começar a corrida | até o fim da corrida | nós da árvore `global run_* add` |

Tudo passa por `passivos_2d.resolver`: `final = (base + add) × (1 + Σinc) × Π(1 + mais)`. Cartas e árvore **somam no mesmo `inc`**, então os tetos de `passivas_limites.csv` valem para as duas juntas.

## 2. Como funciona sem mexer no core
- O core só altera stats que já existem em `player.csv`. Declaramos `run_area`, `run_proj`, `run_vel`, `run_dur`, `run_pierce`, `run_dmg_fogo|gelo|raio|veneno|herald` com valor base 0. Uma carta `run_area add 0.15` sobe o stat; um nó de preparo soma no mesmo stat ao começar.
- `data2d/passivas_partida.csv` liga cada `run_*` a um modificador de habilidade por tag (`run_area` → `tag:area raio inc`, `run_dmg_fogo` → `tag:fogo dano inc`...). `habilidades_2d.aplicar_passivos_globais` lê os `run_*` dos stats finais (`definir_partida`) e o resolver os trata como nós sintéticos.
- Reiniciar a corrida volta os stats à base, então as cartas zeram sozinhas; a árvore (e os preparos) vem de novo do save.

## 3. Cartas (upgrades.csv)
Área (`wide_reach`), projétil extra (`extra_shot`), velocidade do projétil (`swift_shots`), duração (`lingering`), perfuração (`piercing_skills`), dano por elemento (`flame_lore`, `frost_lore`, `storm_lore`, `venom_lore`), Arautos (`herald_might`), crítico (`keen_eye`, `deadly_aim`) e recarga (`focus`). As três últimas usam os stats que o core já lê (`crit_chance`, `crit_mult`, `skill_cd_mult`).

## 4. Preparos (setor `centro` da árvore do Arqueiro)
`pre_area`, `pre_proj` (notável, +1 projétil), `pre_vel`, `pre_dur`, `pre_herald`, `pre_elem` (notável, +8% nos quatro elementos). Custam 1 ou 2 pontos e valem menos que uma carta, para a carta continuar sendo o prêmio da corrida.

## 5. Correção de recarga
O `skill_cd_mult` de nós `global` da árvore nunca chegava às recargas, porque o core só lê o das cartas. Agora `habilidades_2d.cd_extra` (razão entre o valor do core e o final) acelera o tick das ativas.

## 6. Limites conhecidos (backlog)
- O baralho de cartas é único para as classes com core; Mago pode ver cartas que só o Arqueiro aproveita (tags dele). Baralho por classe pede contrato novo na API C (decisão Opus).
- A HUD ainda não lista as passivas ativas da partida.
- Cartas de Arauto por nível (subir o Arauto em si) seguem na thread de progressão (doc 33_aquisicao_habilidades).
