# 29. Guerreiro jogável e árvore de habilidades (31/10/2026)

Segunda classe do cliente 2D (a primeira é o Arqueiro). Combate corpo a corpo: combo de espada em 3 golpes, esquiva e até 4 habilidades ativas. Números em `godot/data2d/guerreiro.csv` (personagem) e `godot/data2d/habilidades_guerreiro.csv` (árvore, no formato combinado com o sistema de habilidades). Textos em `loc_2d.csv` (`skill.<id>.name/desc`, `ramo.<id>`).

## Personagem
- Clique: golpe em cone (alcance 88 px, 110°). O 3º golpe do combo (janela de 0,7 s) é mais forte (1,5x), mais largo e queima mais devagar de recuperar.
- **Ímpeto** (recurso, 0 a 100): +8 por golpe que acerta (+12 ao bloquear), cai depois de 3 s sem acertar. Cada ponto aumenta o dano (até +30% cheio). A habilidade final gasta ímpeto.
- Esquiva (Espaço): 0,22 s invulnerável, recarga 0,9 s.
- Teclas: Q, E, F, R usam as ativas na ordem em que foram aprendidas (máximo 4 ativas por corrida).
- Na corrida, cada sala limpa oferece cartas de habilidade (uma habilidade só aparece se o pai da árvore já foi aprendido).

## Árvore (20 habilidades, 3 ramos)
| Ramo | Raízes | Habilidades |
|---|---|---|
| Lâmina (dano) | Fio Afiado | Talho Pesado (ativa), Redemoinho (ativa), Carrasco, Lâmina Ardente, Fenda de Pedra (ativa) |
| Baluarte (defesa) | Pele de Ferro, Vigor | Escudada (ativa), Postura de Guarda (ativa, segurar), Fôlego, Revide, Última Resistência |
| Ímpeto (mobilidade e fúria) | Investida (ativa), Passo de Guerra | Grito de Guerra (ativa), Ímpeto Crescente, Sede de Sangue, Salto Sísmico (ativa), Fúria Descontrolada (ativa, gasta 50 de ímpeto) |

Passivas somam por nível sobre os stats; ativas crescem por nível pela coluna `escala` (dano, raio, duração, alcance, valor). Atordoamento e queimadura usam `aplicar_status` dos inimigos (chefes resistem ao atordoamento pelo próprio sistema de status).

## Arte
Sprites provisórios em pixel art gerados por `tools/sprites/gerar_guerreiro.py` (formato do doc 25). **Esperam aprovação do Will**; a arte final entra no mesmo caminho sem mudar código.

## Testes
`godot/scripts2d/tools/test_guerreiro_2d.gd`, chamado pelo `test_2d.gd` (dados, árvore, combate, ativas, corrida com guerreiro).
