# Formato das folhas de sprites 2D (cliente 2D no Godot)

Contrato entre a arte (threads de sprites) e o cliente 2D (`godot/scripts2d/`). O jogo carrega as folhas pelo manifesto `godot/data2d/sprites_manifest.csv`. Enquanto a arte não chega, o cliente gera placeholders no **mesmo formato**: trocar é só colocar o PNG no caminho certo, sem mexer em código.

## Visão e luz
- Câmera de cima, estilo ARPG 3/4 achatado (como nos vídeos de referência): o personagem é visto de frente/cima, o chão é um plano.
- Luz principal vindo do alto à esquerda. Sombra de chão NÃO entra na folha (o motor desenha uma elipse).
- Pintura à mão, contorno escuro consistente de 2 a 3 px, fundo **transparente** (PNG RGBA). Sem pixel art duro; sem glow que vaze do quadro.
- Arqueiro: roupa verde, arco e aljava (PR 91/93/94). Mago com capuz e cajado de cristal (nunca lanterna). Referências em `docs/arte/referencias-geracao/aprovadas/`.

## Quadro e pivô
| Classe de tamanho | Quadro | Pé (pivô) | Quem |
|---|---|---|---|
| M | 128 x 128 px | x=64, y=104 | arqueiro, sentinela oca, cão de cinza, arqueiro fantasma |
| G | 192 x 192 px | x=96, y=156 | arauto de pedra |
| XG | 256 x 256 px | x=128, y=208 | Guardião da Cripta (chefe) |

O personagem em pé ocupa ~96 px de altura no quadro M (cabeça perto de y=8, pés em y=104). Sobra espaço embaixo para a sombra e para poses de esquiva.

## Direções
Cada folha de animação tem **5 linhas**, de cima para baixo, no sentido anti-horário a partir de baixo da tela:

| Linha | Direção | 
|---|---|
| 0 | S (para baixo da tela, de frente) |
| 1 | SE |
| 2 | E |
| 3 | NE |
| 4 | N (de costas) |

As direções SW, W e NW são o espelho horizontal de SE, E e NE; o cliente espelha em código. Por isso o arco fica sempre na mesma mão na folha, e o espelho cabe no estilo. (Se a arte entregar 8 linhas — S, SE, E, NE, N, NW, W, SW — o manifesto aceita `direcoes=8`.)

## Animações
Uma folha PNG por animação: colunas = quadros, linhas = direções. Largura = quadros x lado; altura = 5 x lado.

| Animação | Quadros | FPS | Loop | Observação |
|---|---|---|---|---|
| idle | 6 | 8 | sim | respiração, arco baixo |
| run | 8 | 12 | sim | ciclo de corrida; pés tocam o chão nos quadros 0 e 4 |
| attack | 6 | 14 | não | arqueiro: puxar corda e soltar; **a flecha sai no quadro 4** (evento definido no manifesto) |
| dodge | 6 | 14 | não | rolamento/salto curto |
| hit | 3 | 12 | não | recuo ao levar dano |
| death | 8 | 10 | não | último quadro fica parado no chão |

Inimigos usam `idle`, `run` (andar), `attack`, `hit` e `death`; sem `dodge`. O quadro de impacto/disparo de `attack` é a coluna `evento_quadro` do manifesto. Cão de cinza: `attack` = bote (8 quadros).

## Arquivos
```
godot/art2d/sprites/<id>/<id>_<animacao>.png      # ex.: arqueiro/arqueiro_run.png (1024 x 640)
godot/art2d/tiles/cripta_tiles.png                # atlas do cenário
godot/art2d/fx/<nome>.png                         # projéteis e efeitos
```
`<id>` em inglês e minúsculas: `arqueiro`, `hollow_sentinel`, `ash_hound`, `stone_herald`, `ghost_archer`, `crypt_guardian`. Elites reaproveitam a folha do inimigo base com cor de contorno trocada por shader.

## Cenário: atlas de tiles
- Tile de **64 x 64 px**, atlas de 8 colunas (512 px de largura), numeração em linhas da esquerda para a direita.
- Vista de cima/3/4: piso mostra só a face de cima; parede mostra topo + face frontal (o tile de parede tem 64 x 64 de face, o topo é um tile separado).
- Tiles obrigatórios (índice = linha x 8 + coluna):

| Índice | Tile |
|---|---|
| 0, 1, 2, 3 | piso de pedra (4 variações, sem borda visível ao repetir) |
| 4 | piso com rachadura |
| 5 | piso com tapete (centro) |
| 6 | piso com sangue/cinza |
| 7 | porta fechada (selo) |
| 8 | parede, face frontal |
| 9 | parede, topo |
| 10 | parede, canto externo |
| 11 | parede, canto interno |
| 12 | pilar (base) |
| 13 | porta aberta |
| 14 | braseiro apagado |
| 15 | braseiro aceso (frame 0; os quadros extras vão em `fx/braseiro.png`) |

Salas da corrida têm 24 x 13 tiles (1536 x 832 px) e são montadas a partir de textos em `godot/data2d/rooms/*.txt`.

## Efeitos e projéteis
- `fx/arrow.png`: flecha 64 x 16, apontando para a direita (o motor gira).
- `fx/arrow_hit.png`: 4 quadros de 64 x 64, faísca no impacto.
- `fx/braseiro.png`: 4 quadros de 64 x 64, chama.

## Manifesto
`godot/data2d/sprites_manifest.csv`: `id,anim,arquivo,quadro,quadros,fps,loop,direcoes,pivo_x,pivo_y,evento_quadro`. Mudou um valor da tabela acima na arte? Mude o CSV, nunca o código.

## Como entregar
1. Gerar cada folha no tamanho exato da tabela (a IA costuma errar a grade: conferir e recortar/ajustar por script em Python/Pillow, alinhando o pé de cada quadro ao pivô).
2. Mandar ao Will para o ok antes de entrar no jogo (passa pela revisora).
3. Aprovada, salvar em `godot/art2d/sprites/...` no repositório (PNG pequeno, sem LFS) e rodar `godot --headless --script res://scripts2d/tools/test_2d.gd` para validar tamanho e grade.
