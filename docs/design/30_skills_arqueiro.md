# Habilidades do Arqueiro (cliente 2D)

18 habilidades em 3 ramos, dados em `godot/data2d/habilidades_arqueiro.csv` (contrato comum às 3 classes, definido com a thread da base de skills). Textos em `loc_2d.csv` (`skill.<id>.name/desc`, `ramo.<id>.name/desc`). Efeitos ativos em `godot/scripts2d/efeitos_arqueiro_2d.gd`; zonas no chão em `zona_2d.gd`; status em `enemy_2d.gd` (`aplicar_status`). Teste: `_testar_habilidades_arqueiro` em `test_2d.gd`.

Decisões técnicas tomadas sem o Will (ele dorme; o Jev decide o resto): números são ponto de partida para teste, ajustáveis só no CSV.

| Ramo | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Precisão | Mira Firme (passiva, +12% dano), Disparo Carregado (ativa) | Ponta Perfurante (passiva, pai Disparo), Olho de Águia (passiva, crítico, pai Mira Firme), Salva Veloz (ativa, pai Disparo) | Tiro Certeiro (ativa, pai Olho de Águia) |
| Caça | Leque de Flechas, Chuva de Flechas (ativas) | Armadilha de Espinhos (pai Leque), Flecha Explosiva (pai Chuva) | Marca do Caçador (pai Explosiva), Pontas Venenosas (passiva, pai Armadilha) |
| Sombra | Salto Atrás (ativa), Pés de Vento (passiva) | Bomba de Fumaça (pai Salto), Dança das Sombras (passiva, pai Pés de Vento) | Adrenalina (ativa, pai Fumaça), Vigor do Andarilho (passiva, pai Dança) |

11 ativas e 7 passivas. Níveis: 1 a 3 (2 para Ponta Perfurante); custo em pontos = tier (1, 2 ou 3 por nível). Ativas escalam 15% por nível (`escala`).

## Efeitos
`tiro_forte` (flecha pesada com perfuração e velocidade), `rajada` (N flechas em sequência), `leque` (N flechas em cone), `chuva` (zona com pulsos de dano), `armadilha` (zona que atordoa uma vez), `explosiva` (flecha que explode em área), `marca` (status de dano extra no inimigo mais alinhado à mira; sem alvo cancela sem gastar recarga), `salto` (recua invulnerável e atira ao pousar), `fumaca` (zona de lentidão), `furia` (buff de velocidade e cadência).

## Stats novos do jogador (`player.csv`)
`crit_chance`, `crit_mult`, `poison_dps`, `poison_time`; passivas somam neles via `stat/modo/valor`.

## Ícones
Reaproveitam os 10 aprovados (PR 117); vários repetem. Faltam ícones próprios para as 18 (pedido para a thread de ícones).
