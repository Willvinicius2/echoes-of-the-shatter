# Props e inimigos novos da Cripta (rascunho para aprovação)
- `props/*.png`: 48 props recortados (fundo transparente, tamanho original ~250 px; o cliente escala). Origem: folhas `p01`/`p02` em `docs/arte/sprites2d/props_fantasmas/brutos/`. Pivô: base do objeto (centro-inferior).
- `../sprites_novos/g0*.png`: folhas dos inimigos (6x4 células de 256, mesma grade do PR 95): fantasma errante, espectro de correntes, esqueleto soldado, morcego da cripta. Fundo já transparente.
- Regerar: `python tools/sprites2d/recortar_props.py docs/arte/sprites2d/props_fantasmas/brutos godot/art2d/props godot/art2d/sprites_novos`.
