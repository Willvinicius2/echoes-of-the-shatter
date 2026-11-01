# 33 — Como o personagem adquire habilidades na corrida de hordas

Pedido do Will (01/11/2026): o personagem começa no mapa cru, só com o ataque básico, e ganha habilidades
conforme sobe de nível e dropa gemas. Vale para as sete árvores do Arqueiro (precisão, caça, sombra, veneno,
gelo, fogo, raio) e para os Heralds, e depois para o Mago e o Guerreiro com as árvores deles.

## Regras

1. **Começo cru.** Toda corrida de hordas começa sem nenhuma habilidade aprendida e com os 4 slots vazios.
   Só o ataque básico dispara (autocast). A árvore da corrida é nova a cada corrida (núcleo próprio, sem
   o saldo de pontos do hub, sem gravar save). Chave: `skill_from_scratch` em `run_settings.csv`.
2. **Subir de nível.** As gemas de XP enchem o Cristal de Eco. Cada nível dá um reforço de atributo (carta,
   como antes). A cada `skill_gem_every_levels` níveis (hoje 2) o jogador ganha uma gema de habilidade.
   Os pontos por nível do core ficam desligados (`skill_points_every_levels = 0`).
3. **Gema de habilidade por drop.** Elite (`skill_gem_elite`) e Guardião (`skill_gem_boss`) soltam uma gema
   no chão, que voa até o jogador como as gemas de XP.
4. **O que a gema faz.** Abre a escolha entre `skill_gem_cards` (hoje 3) habilidades sorteadas entre as que a
   árvore já libera: raiz sem pré-requisito, ou filha cujo pai já foi aprendido, ainda abaixo do `nivel_max`.
   Escolher uma já aprendida sobe um nível dela. Ativa nova entra no primeiro slot livre; passivas e Heralds
   valem na hora. A gema guarda só o `id` de `habilidades_<classe>.csv`, sem duplicar dados. Se já há uma
   tela aberta (carta de nível ou outra gema), a gema espera na fila e abre quando a atual fechar.
5. **Cartas continuam** como reforço de atributo (vida, dano, velocidade), independentes das gemas.

## Efeito no ritmo

Com `skill_gem_every_levels = 2`, um jogador que chega ao nível 8 escolheu 4 habilidades por nível, mais as
dos elites. As primeiras ondas são só de ataque básico, o que deixa o começo legível e faz cada gema pesar.
Como a escolha é entre 3, dá para montar build (ir fundo numa árvore) ou espalhar.

## O que fica no CSV (`run_settings.csv`)

| chave | hoje | o que faz |
|---|---|---|
| `skill_from_scratch` | 1 | corrida começa sem habilidades |
| `skill_gem_every_levels` | 2 | gema de habilidade a cada N níveis |
| `skill_gem_elite` | 1.0 | chance de o elite soltar gema |
| `skill_gem_boss` | 1.0 | chance de o Guardião soltar gema |
| `skill_gem_cards` | 3 | quantas habilidades a gema oferece |
| `skill_points_every_levels` | 0 | pontos por nível do core (desligado) |

## Pendências de design (para o Will)

- O sorteio das 3 opções usa o RNG do cliente, então não é reproduzível por semente. Mover para o core se
  quisermos replays e bot determinístico.
- Raridade de gema (Heralds só em elite/Guardião) e custo de slot, como no Path of Exile.
- Os 4 slots: quando enchem, uma ativa nova não entra em slot nenhum. Falta a troca de slot na tela da gema.
- Balanceamento dos números acima é provisório e fica só nos CSV.
