# Ancoragem dos props e ponte de pedra (pacote H5, 31/10/2026)

Capturas do cliente 2D feitas com `godot --path godot --script res://scripts2d/tools/captura_props_2d.gd` (sala sem inimigos, bonecos parados do Arqueiro; na nuvem, com `xvfb-run`). `antes_*` é o `master` de 31/10 (PR 151 já aplicado); `depois_*` é esta branch. As pranchas `prancha_*.jpg` mostram antes à esquerda e depois à direita.

## O que o Will viu
Tumbas, pedras e árvores pareciam flutuar: cada prop tinha só uma elipse preta de 42% sob o pé, sem contato com o sprite. A travessia do riacho eram 5 lajes cinzas sobrepostas em zigue-zague, e o personagem parecia passar por baixo (as lajes estavam com `z_index = 1`, corrigido no PR 151).

## Direção visual (Jev, `jev-latest`, `POST /v1/systemone`)
| Pergunta | Decisão | Probabilidades | Conf. |
|---|---|---|---|
| Tipo de ponte | Ponte de pedra com lajes contínuas, muretas baixas e sombra na água | pedra 76%, madeira 21%, pedras de passo 3% | 0,64 |
| Luz principal | De cima-esquerda, sombra para baixo-direita | 39% (zenital 38%, braseiros 23%) | 0,09 (provisória: as três eram parecidas; ficou a mais comum em jogos top-down pintados) |
| Base dos props | Sombra de contato escura encostada no pé + anel de terra pisada + tufos de capim na base | 94% | 0,91 |
| Árvores | Raízes curtas por código saindo do tronco, mais terra e sombra longa | 80% | 0,60 |
| Água junto da ponte | Sombra escura da ponte na água e reflexo claro tremido | 72% | 0,58 |

## O que mudou no código
- `scripts2d/ancoragem_2d.gd` (novo): para cada prop, sombra projetada com a silhueta do próprio sprite (espelhada no pé, achatada e inclinada para baixo-direita, shader que só usa o alfa), sombra de contato em dois níveis sob a base, anel de terra pisada (só no gramado), 2 ou 3 tufos de capim/folhas encostados no pé (um deles na frente do sprite) e, nas árvores, quatro raízes afiladas na cor da casca. A base do tronco é medida na própria textura (as folhas caídas descem abaixo do tronco). Os decalques de chão ficam num nó `ChaoProps` da sala, sob todos os atores; só os tufos ficam no nó do prop, para o y-sort continuar valendo.
- `room_2d.gd` (`colocar_props`): monta o nó do prop com `atras` + sprite + `frente` e chama a ancoragem.
- `terreno_2d.gd` (`_ponte`, `_pilarete`, `_textura_tabuleiro`): a travessia virou ponte de pedra no z do chão, centrada na trilha e com a mesma largura dela: tabuleiro com textura própria de lajes retangulares em fiadas (diferente das lajes redondas da trilha, para não sobrepor duas texturas), soleira escura só na junta com a trilha, muretas com espessura (base de 14 px, topo 12 px acima, faces em sombra), blocos de pedra nas quatro pontas, anel de sombra na água em volta da ponte inteira mais sombra deslocada para baixo-direita e reflexo claro nas beiradas. Segunda rodada depois da revisão da thread revisora (alinhar à trilha, uma textura só, espessura das muretas, sombra dos dois lados); terceira: eixo entre os pontos em que a trilha entra e sai da água, sombra na água em camadas translúcidas e mais curta, antialias em todos os polígonos da ponte. A ponte segue a direção do caminho; se ele cruzar de lado demais (mais de 40° em relação à perpendicular do riacho), fica perpendicular à água e as rampas fazem a ligação. A colisão da água abre o corredor sobre o eixo da ponte.
- `_lajes_soltas`: pedrinhas menores, com sombra curta para baixo-direita (a mesma luz dos props) em vez do contorno escuro que as fazia parecer seixos flutuando.

## Pendente para a próxima rodada
- Y-sort das muretas: nas salas atuais o riacho é horizontal e a ponte vertical, então as muretas ficam ao lado do jogador e tudo pode ficar no chão. Se o mapa grande (H1) tiver ponte horizontal, a mureta de baixo precisa virar sprite no nó dos atores.
- A sombra projetada não é suavizada (borda dura); dá para trocar por uma segunda passada com desfoque se o Will achar dura demais.
