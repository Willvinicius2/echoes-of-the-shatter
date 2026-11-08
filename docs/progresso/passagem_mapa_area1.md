# Passagem de bastão: mapa da primeira área (arqueiro)

Atualizado em 08/11/2026 (thread "Terminar o mapa da área 1 do arqueiro"). O detalhe técnico do mapa está em `docs/arte/31_pixellab_arqueiro.md` (seção "Mapa da área 1").

## Feito
- PRs 209 a 213 mergeados (sombras, cascalho, inimigos em pixel art, olhos, números de dano, barra de vida).
- Estrada de pedra principal do arqueiro até a arena (160 tiles, 2 curvas, 1 bifurcação curta para o bolsão com baú), com os marcos pedidos: pilares com símbolo e braseiros no início, ruína no meio, árvore seca grande na bifurcação, respiro com braseiros e portão de caveiras e brasas antes da arena, cada um com luz própria.
- Encontros adormecidos ao longo da estrada (um a cada ~20 tiles até o respiro), trecho 3 denso, respiro e avenida final calmos.
- Mapa continua 180 x 100. Capturas, visão geral e vídeo da estrada em `/mnt/project-files/pixellab/etapa2/area1/` (a primeira entrega) e `.../area1/v2/` (depois do acabamento).
- Acabamento pedido pelas duas revisões da PR 214 (trilha solta fora, cemitério em clareiras, ruína com 2 pilares, sombra e borda escura nos arcos, encontros fora dos sprites, +10% de luz na estrada, dica de controles mais alta, árvore de folhas ciano menos saturada): detalhe em `docs/arte/31_pixellab_arqueiro.md`, seção "Acabamento da área 1".

## Falta (opcionais, nesta ordem)
1. ~~Barra de vida do morcego 4 px mais alta~~ (feito no polimento depois da PR 215: `hp_bar_dy` em `enemies.csv`).
2. ~~Fonte bitmap para os números de dano~~ (feito: Jersey 15, 20 e 25, SIL OFL, em `godot/art2d/fonts/`).
3. Elites e chefe em escala 1,5 a 2x (decisão de arte: a escala 1,5 deixa os pixels maiores que a grade; 2 inteiro fica "grosso").
4. Segunda área: reaproveitar `marcos_fase1.py` como modelo (estrada, marcos com luz, encontros por trecho) e puxar o piso para um cinza mais quente, com o ciano só de acento.

## Atenção
- Push forçado é negado: use merge normal.
- Regerar o mapa: `python3 tools/mapas/gerar_fase_1.py` (sai igual a cada vez); conferir com `python3 tools/mapas/visao_geral_fase1.py saida.png` e `godot --path godot --script res://scripts2d/tools/captura_marcos_2d.gd -- prefixo` (precisa de janela/xvfb).
