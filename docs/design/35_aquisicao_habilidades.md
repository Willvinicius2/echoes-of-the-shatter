# 35 — Como o personagem adquire habilidades (skills e Heralds da partida)

Decisão do Will (01/11/2026, refinada no mesmo dia): o jogo tem **duas camadas** de progressão de habilidade.

## Camada 1 — árvore fixa (permanente)

Fica no personagem para sempre, como a árvore de passivas do Path of Exile: a árvore de passivos que modifica as
skills (`33_arvore_passivos_arqueiro.md`, `passivos_2d.gd`) e a árvore de habilidades de hoje (tecla T, core do hub,
com save). O que o jogador deixa pronto nelas vale em **toda** corrida e os pontos gastos não zeram. As passivas
entram nos stats por `corrida_stats` do core e por `aplicar_passivos_stats`, como sempre.

## Camada 2 — habilidades da partida (zeram a cada corrida)

A corrida de hordas começa **só com o ataque básico**: nenhuma ativa, nenhum Herald, 4 slots vazios. Dentro da
partida o jogador sobe o que **muda a cada corrida**: skills (ativas), Heralds (Herald of Thunder, Herald of Ashes,
Peste, Gelo) e passivas de partida. Esta camada vive num core próprio, sem save, criado de novo no início da corrida
(`skill_from_scratch`), e é a que o combate usa (`player.habilidades`). Os stats finais são
`base + meta + cartas + árvore fixa + passivas da partida`.

## Como a partida ganha habilidades

1. **Subir de nível** (gemas de XP enchem o Cristal de Eco): cada nível dá um reforço de atributo (carta). A cada
   `skill_gem_every_levels` níveis (2) o jogador ganha uma **gema de habilidade**.
2. **Elite e Guardião** soltam uma gema de habilidade no chão (`skill_gem_elite`, `skill_gem_boss`).
3. **A gema abre uma escolha** entre `skill_gem_cards` (3) habilidades sorteadas entre as que a árvore da classe
   libera: raiz sem pré-requisito, ou filha cujo pai já foi aprendido na partida, abaixo do `nivel_max`. Escolher
   uma já aprendida sobe o nível dela. Ativa nova entra no primeiro slot livre; passivas e Heralds valem na hora
   (os stats são recalculados). A gema guarda só o `id` de `habilidades_<classe>.csv`.
4. **Passivas de partida** (área, velocidade, projéteis, duração, dano por elemento, Heralds, crítico, recarga) são as
   cartas de nível e baú e os nós de preparo de `34_passivas_da_partida.md` (`run_*` em `upgrades.csv`). Esta
   doc cuida só de **skills e Heralds**, que vêm pela gema.

As camadas se somam: o que está fixo na árvore, o que a gema ensinou na partida e as cartas `run_*` valem juntos.

## Números (todos em `run_settings.csv`)

| chave | hoje | o que faz |
|---|---|---|
| `skill_from_scratch` | 1 | corrida começa só com o ataque básico |
| `skill_gem_every_levels` | 2 | gema de habilidade a cada N níveis |
| `skill_gem_elite` | 1.0 | chance de o elite soltar gema |
| `skill_gem_boss` | 1.0 | chance de o Guardião soltar gema |
| `skill_gem_cards` | 3 | quantas habilidades a gema oferece |
| `skill_points_every_levels` | 0 | pontos por nível do core para a árvore fixa (desligado) |

## Pendências de design (para o Will)

- Como a árvore fixa ganha pontos: hoje só o Guardião derrotado dá pontos (`skill_points_boss`). Dar também XP de
  conta por corrida é uma decisão de meta-progressão.
- O sorteio das opções usa o RNG do cliente (não reproduzível por semente); mover para o core se quisermos replays.
- Com os 4 slots cheios uma ativa nova não entra em slot nenhum: falta a troca de slot na tela da gema.
- Balanceamento provisório; tudo nos CSV.
