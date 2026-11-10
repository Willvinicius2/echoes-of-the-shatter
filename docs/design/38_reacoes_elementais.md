# 38. Reações elementais (habilidades que conversam entre si)

Pedido do Will (10/11/2026): mais diversidade de habilidades e mais interação delas com o mapa e com os inimigos. O arqueiro já tem 28 ativas (7 a 8 por elemento, docs 36 e 37) que se comportavam cada uma por si. Agora, quando um elemento atinge um inimigo que já está sob outro, os dois reagem. Quem monta a build escolhe combinações (veneno antes do fogo, gelo antes do raio) em vez de só somar dano.

Código: `godot/scripts2d/reacoes_2d.gd` (chamado por `enemy_2d.aplicar_status`, antes de gravar o status novo). Números: `godot/data2d/reacoes_elementais.csv`. Testes: `scripts2d/tools/test_reacoes_2d.gd`. Cada reação tem visual próprio em `_draw` (sem sprite nem partícula de GPU).

| Reação | Gatilho + estado do alvo | Efeito | Visual |
|---|---|---|---|
| Vapor | Fogo em alvo com frio | dano em área, apaga o frio | nuvens brancas subindo |
| Choque Térmico | Gelo em alvo queimando | dano em área, apaga a queimadura | fendas vermelhas e azuis |
| Gás Inflamado | Fogo em alvo envenenado | explosão em área proporcional ao veneno, consome o veneno | bola de fogo verde e laranja |
| Quebra Gélida | Raio em alvo congelado | estilhaça o gelo: dano grande em área e frio nos vizinhos | cristais voando |
| Corrente Tóxica | Raio em alvo envenenado | o veneno pula por arcos para até 3 vizinhos | arcos verde-amarelos |
| Condução na Água | Raio em alvo na margem de um riacho | a corrente corre pela água e choca até 2 vizinhos que também estão na água | arcos azuis e brilho na poça |
| Apagar Fogo | Fogo em alvo na margem de um riacho | a água apaga a chama (a queimadura não pega) | vapor |

Regras: cada inimigo tem recarga de reação (0,8 a 1 s) para evitar cadeias infinitas; o dano parte do dano da flecha do arqueiro (coluna `dano` do CSV, 10 = 1x); frio só conta quando vem dos acúmulos de frio do arqueiro.

## Terreno
Os riachos do mapa (`@riacho`) contam como água: a sala entra no grupo `sala_2d` e responde `perto_agua(pos, dist)` (margem de 70 px). Hoje isso vale nas salas e na fase 1, que têm riacho.

## Resistências por inimigo
`data2d/resistencias_elementais.csv` (multiplicador do valor e da duração do status; 0 = imune, aparece um 0 cinza). Exemplos: esqueletos e Herald de pedra são imunes a veneno, Cão de Cinzas e Arqueiro de Brasas resistem ao fogo e sofrem mais com gelo, fantasmas e morcegos conduzem mais o raio, o Guardião resiste a tudo um pouco. Só afeta os status das habilidades, não o dano direto.

## Ainda não feito
Dica visual do que cada inimigo resiste (ícone junto à barra de vida), mesmo sistema para Mago e Guerreiro, braseiros e pilares do mapa reagindo a fogo e raio.
