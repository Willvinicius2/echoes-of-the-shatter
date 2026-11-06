# Passagem de bastão: mapa da primeira área (arqueiro)

## Feito
- PRs 209 a 212 mergeados (sombras, cascalho, inimigos em pixel art, olhos, números de dano).
- PR 213 (números de dano menores, golpe forte laranja, barra de vida com borda, olho do morcego 2x2) aberto, revisores aprovaram; faltava só o CI terminar (export, corridas-bot, teste-headless) para o merge squash.
- Nesta branch: 6 novos pontos de inimigo (E) ao longo da estrada em `godot/data2d/rooms/fase_1.txt` e `_spawn_inimigos` em `godot/scripts2d/run_2d.gd` atribuindo a primeira onda por ordem de x (esqueletos no início, morcegos no meio, sentinelas no portão). test_2d sem FALHA. Capturas em /mnt/project-files/pixellab/etapa2/mapa_*.png.

## Falta (ordem do coordenador)
1. Estrada de pedra visível até a arena, 2 curvas e 1 bifurcação curta para um bolso com recompensa.
2. Trecho 3 denso e um respiro (braseiro ou clareira) antes do chefe; estrada nunca vazia por mais de ~6 s.
3. Marcos: pilar com símbolo e braseiro no início, ruína no meio, árvore seca grande na bifurcação, portal com caveiras e brasas antes da arena.
4. Tamanho do mapa fica como está; capturas de início, meio e entrada da arena para revisão.
Opcionais: barra de vida do morcego 4 px mais alta, fonte bitmap para números, elites/chefe em escala 1.5 a 2x.

## Atenção
- Depois do merge do PR 213, esta branch precisa de rebase/merge do master.
- Push forçado é negado: use merge normal.
