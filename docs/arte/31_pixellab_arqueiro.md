# Arqueiro e cenário no PixelLab (05/11/2026)

Substitui o v7 feito à mão (Will achou ruim). Plano grátis (40 gerações; usadas ~28 de 40). Termos: arte do usuário, uso comercial permitido; proibido treinar modelo com as saídas.

- Arqueiro: `create-character-v3`, 8 direções, 64 px, vista "low top-down" (2 gerações). Andar: template `walking` (1 geração por direção). Atacar: modo v3 com texto (arco puxado e solto). Morrer: template `falling-back-death`.
- Brutos em `art-src/pixellab/arqueiro/` (rotações e animações por direção). `tools/sprites2d/montar_arqueiro_pixellab.py` monta as folhas (quadro 92, pivô 46,76; linhas S, SE, E, NE, N). idle, hit e dodge são derivados (respiração de 1 px, flash branco, andar com salto).
- Piso: `create-tileset` 32 px, ampliado 2x para as células 0..3 e 6 do atlas (`tools/sprites2d/aplicar_piso_pixellab.py`). Braseiro 48x64 via `create-image-pixflux`, em `godot/art2d/pixellab/`, ainda não ligado (o tile do braseiro tem a chama tratada por `clima_2d.gd`).

Segunda rodada (05/11): ataque regerado ("attack2", sem flecha no prompt; o modelo ainda desenha uma flecha pequena em S/E/NE/N, a flecha de verdade sai como projétil do motor) e arco vermelho de E corrigido para marrom; piso recolorido para cinza-arroxeado do atlas; cena de teste em `tools/sprites2d/cena_teste_pixellab.py`.

Limitações conhecidas (antes da 2ª rodada, a do piso azulado está resolvida): a animação de ataque gerada atira para o lado direito do quadro nas direções S/SE/E e esconde a flecha em NE/N (a âncora de disparo fica na mão do arco); o piso azul-esverdeado destoa das paredes cinzas do atlas pintado; idle quase parado.
