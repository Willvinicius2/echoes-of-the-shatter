# Props e inimigos novos da Cripta (rascunho para aprovação)
- `props/*.png`: 48 props recortados (fundo transparente, tamanho original ~250 px; o cliente escala). Origem: folhas `p01`/`p02` em `docs/arte/sprites2d/props_fantasmas/brutos/`. Pivô: base do objeto (centro-inferior).
- `../sprites_novos/g0*.png`: folhas dos inimigos (6x4 células de 256, mesma grade do PR 95): fantasma errante, espectro de correntes, esqueleto soldado, morcego da cripta. Fundo já transparente.
- Regerar: `python tools/sprites2d/recortar_props.py docs/arte/sprites2d/props_fantasmas/brutos godot/art2d/props godot/art2d/sprites_novos`.

## Atualização
- Inimigos montados em 128 px, 5 direções (S, SE, E, NE, N), pivô (64,104): `godot/art2d/sprites/<id>/<id>_<anim>.png`, ids `wandering_ghost`, `chain_wraith`, `skeleton_soldier`, `crypt_bat`. Linhas em `godot/data2d/sprites_manifest_novos.csv` (juntar ao manifesto principal ao integrar).
- Limitações: SE e NE reaproveitam a vista E; ataque, hit e morte usam a vista E em todas as direções; morte tem só 2 poses repetidas.
- Props: pivô no centro da base em `godot/data2d/props_manifest.csv`.
- Rebuild: `python tools/sprites2d/montar_inimigos_novos.py godot/art2d/sprites_novos godot/art2d/sprites`.
