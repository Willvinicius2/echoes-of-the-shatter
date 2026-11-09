# Passagem de bastão: etapa 2 (fase jogável com o arqueiro) → etapa 3

Feito na etapa 2 (06/11/2026): corrida de frente nova do arqueiro (PixelLab v3), props e vegetação com o tratamento do piso (`tools/sprites2d/pixelar_props.py`), braseiro do PixelLab no tile (`aplicar_braseiro_pixellab.py`). Detalhes e limites em `docs/arte/31_pixellab_arqueiro.md`. A fase (modo horda com Guardião) já era jogável de ponta a ponta; o bot `corridas_2d.gd` e o `test_2d.gd` confirmam. Vídeo e capturas: `/mnt/project-files/pixellab/etapa2/`.

Para a etapa 3 (guerreiro, mago e mapas novos):
1. Plano grátis do PixelLab: restam 2 gerações de 40. Guerreiro e mago em pixel art precisam de plano pago ou outra fonte; decidir antes de começar.
2. O token do PixelLab foi colado no chat na etapa 1: gerar outro no site.
3. Props com grade de 2 px e arqueiro com 1 px: se os personagens novos forem de 1 px, considerar `pixelar_props.py 1`.
4. Os originais HD dos props ficam em `art-src/props-hd-originais/`; nunca rodar o script sobre `godot/art2d/props/`.
5. O teste `armadilha atordoa quem pisa` do `test_2d.gd` falhou uma vez e passou na seguinte: é instável, não é da arte.
