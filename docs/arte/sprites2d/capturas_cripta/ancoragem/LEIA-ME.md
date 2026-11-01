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

## Ordem de desenho (y-sort) pelo ponto de apoio (1/11/2026)
O Will viu, no mapa grande, o prop cobrindo a cabeça do personagem que passava ao lado dele. Causa: o nó do prop entrava no y-sort pela borda de baixo do sprite; nas árvores essa borda são as folhas caídas, 20 a 30 px abaixo do pé do tronco, e nas tumbas é a aresta da frente da base. Quem estava ao lado do tronco, com os pés no mesmo nível dele, ficava "atrás" da árvore e a copa cobria a cabeça. Correção: `Ancoragem.apoio()` devolve a altura do centro da base que toca o chão (nas árvores, o pé do tronco medido na textura mais meia profundidade da base); `colocar_props` posiciona o nó nesse ponto (o sprite desce o mesmo tanto, então nada muda no desenho) e a colisão do prop vai para o mesmo ponto. Vale para todos os props, inclusive os da orla de mata e dos bosques da `fase_1`. `prancha_ysort.jpg`: antes e depois com o boneco ao lado do tronco; `ysort_depois_fase1.jpg`: mapa grande.

Pendente fora deste pacote: alguns sprites de inimigos (`skeleton_soldier`, `ossuary_captain`, `chain_wraith`, `wandering_ghost`, `fallen_echo`, `crypt_bat`) têm os pés 10 a 20 px abaixo do pivô do manifesto (`sprites_manifest.csv`, `pivo_y` 104 num quadro de 128), então também entram no y-sort um pouco antes do que deveriam; o Arqueiro, o Guerreiro e o Mago estão certos.

## Pendente para a próxima rodada
- Y-sort das muretas: nas salas atuais o riacho é horizontal e a ponte vertical, então as muretas ficam ao lado do jogador e tudo pode ficar no chão. Se o mapa grande (H1) tiver ponte horizontal, a mureta de baixo precisa virar sprite no nó dos atores.
- A sombra projetada não é suavizada (borda dura); dá para trocar por uma segunda passada com desfoque se o Will achar dura demais.

## Arbustos na beira da trilha e vida no mapa (1/11/2026, 3º pedido do Will)
O Will viu os arbustos ao lado do caminho de pedra "atravessando a cabeça" do personagem e achou o mapa sem vida. O Jev decidiu (`jev-latest`): props rasteiros (folhas, ossos, caveiras soltas, galhos, flores, capim, raízes, samambaias, juncos, cardos) saem do y-sort e ficam no chão, sob todos os atores (99%); arbustos e moitas continuam ordenados pelo centro da base, mas ficam semitransparentes enquanto o personagem está atrás deles, para o corpo não sumir atrás de uma moita de meio corpo (80%; o Jev sugeriu 45%, a revisora achou a moita apagada demais e ficou em 55%); árvores, pilares e tumbas altas não mudam (72%); "vida" = aglomerados de cenário nos trechos vazios, mais ou menos 30% a mais de props só onde não há nada (73% e 85%).
- `ancoragem_2d.gd`: `tipo()` distingue `raso` e `folhagem`; `room_2d.gd` coloca os rasos como filhos da sala (fora do y-sort) e guarda os arbustos em `_ocultaveis`; `_process` baixa o alfa do arbusto quando o jogador (o `player` da corrida ou o grupo `arqueiro` nas ferramentas) está atrás e dentro da largura dele.
- `tools/mapa/aglomerados_fase1.py`: gera aglomerados (moitas, pedras, tronco caído, cemitério, ruína, ossuário, arvoredo) nos vazios da `fase_1.txt`, longe de trilhas, riachos, mata e marcadores; idempotente pelo sidecar `tools/mapa/fase_1.gerados.txt`. Rodada de 1/11: 2117 props antes, 558 gerados, 2675 no total.
- `tools/video_trilha_2d.gd`: grava o Arqueiro andando pela trilha (`--write-movie`), com desvio opcional pela beira (`DESVIO`).
Capturas: `arbusto_lado.jpg` (boneco ao lado do arbusto `bush_dry_round` da trilha principal), `arbusto_atras.jpg` (boneco atrás: arbusto a 45%, antes do ajuste para 55%), `aglomerado_ossuario.jpg` (aglomerado gerado perto do pilar caído), `video_quadro_arbusto.jpg` (quadro do vídeo `trilha_arbustos.mp4`, entregue na Library do projeto).

## Assentamento como padrão do spawner (1/11/2026, 4º pedido do Will: "objetos parecem voar")
Causa: nos pisos de pedra (sala do chefe, ossuário, arenas) o pilar ou a tumba ficava claro até a última linha de pixels e a sombra de contato morria escondida sob o próprio sprite; no gramado, moitas e folhas tinham contato quase invisível. Tudo é feito em `ancoragem_2d.gd` e `colocar_props`, então vale para todo prop novo de qualquer mapa sem configurar nada:
- **Base afundada**: `material_base()` põe no sprite de props sólidos e arbustos um shader que escurece a faixa de baixo (altura proporcional à profundidade da base, medida na linha de baixo opaca da textura).
- **Sombra na silhueta**: `_sombra_borda()` desenha, sob o prop, a faixa de baixo da própria silhueta em preto, maior e deslocada para baixo-direita; é o que sobra visível em volta da aresta da frente.
- **Contato mais forte e deslocado para a frente**; terra pisada mais escura e também sob props rasos (folhas, ossos) no gramado.
- **Entulho** (`_entulho()`): lascas de pedra com sombra junto da base em piso de pedra.
- **Checagem automática** (`_testar_ancoragem` em `test_2d.gd`, roda no CI): o pivô de todo prop do manifesto fica na base opaca do sprite (±6 px), e em toda sala todo prop tem decalques de contato e, se sólido ou arbusto, o material de base.
Capturas: `prancha_pedra.jpg` (sala do chefe, antes à esquerda e depois à direita) e `prancha_fase.jpg` (fase aberta).
