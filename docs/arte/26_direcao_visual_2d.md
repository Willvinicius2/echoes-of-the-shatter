# Direção visual 2D da Cripta (definitiva a partir de 29/10/2026)

O Will aprovou o visual 2D top-down montado no PR 99 como base definitiva. Daqui em diante o jogo evolui em cima dele. O cliente 3D antigo (`godot/scenes`, `godot/scripts`) fica só como histórico.

## O que está aprovado
- Salas 24x13 tiles de 64 px, câmera fixa que enquadra a sala inteira, arqueiro e inimigos em sprites de 128 px com 5 direções (formato em `25_formato_folhas_sprites_2d.md`).
- Vegetação seca (árvores, arbustos, capim, folhas) e props da Cripta (pilares, tumbas, sarcófagos, caveiras, ossos, pedras) como sprites com ordem em Y, sombra e colisão só na base.
- Capturas de referência: `sprites2d/capturas_cripta/`.

## Como montar uma sala
- Arquivo `godot/data2d/rooms/*.txt`: grade de caracteres (legenda no topo de `godot/scripts2d/room_2d.gd`), depois `@props` com linhas `id coluna linha [flip]`.
- Cada prop tem arte e pivô em `godot/data2d/props_manifest.csv`, e escala e área sólida em `godot/data2d/props_2d.csv` (`solido_l` 0 = só decoração).
- Regras: a coluna da porta (11 a 13) fica livre nas linhas 2 a 4; árvores grandes ficam nas bordas e só as pequenas perto do caminho; teste `test_2d.gd` confere arte, definição e porta livre.

## Próximas direções (pedidas pelo Will)
1. Chão de gramado com caminho de pedras no lugar do piso de laje.
2. Riacho atravessando algum mapa (depois).
3. Um passe de direção de arte (luz, cor, composição), feito junto com o Will, passando pela revisora antes de ele ver.
