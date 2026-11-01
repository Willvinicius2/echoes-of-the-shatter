# 33 — Como o personagem adquire habilidades

Decisão do Will (01/11/2026, refinada no mesmo dia): o jogo tem **duas camadas** de progressão de habilidade.

## Camada 1 — árvore fixa (permanente)

É a árvore de habilidades de hoje (tecla T), que fica no personagem para sempre, como a árvore de passivas do
Path of Exile. O que o jogador deixa pronto nela vale em **toda** corrida: ela guarda as passivas que ele escolheu
fixar, e os pontos gastos nela não zeram. Vive no core do hub (com save). As passivas dela entram nos stats por
`corrida_stats` do core, como sempre.

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
4. **Passivas de partida em carta** (reforços de atributo em `upgrades.csv`, sem código novo): dano, velocidade de
   ataque, vida, esquiva, projéteis, perfuração, **chance de crítico** (`crit`), **dano crítico** (`crit_power`) e
   **recarga de habilidades** (`focus`, `skill_cd_mult`). Aumentar o tamanho da habilidade depende de um stat de área
   que os efeitos ainda não leem (pendente com a thread das habilidades do Arqueiro).

As duas camadas se somam: uma passiva fixada na árvore e a mesma ganha na partida valem as duas.

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
- Stat de tamanho da habilidade (área) para as passivas de partida e a fixa.
- Balanceamento provisório; tudo nos CSV.
