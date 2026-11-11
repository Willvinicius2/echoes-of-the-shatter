# 39. Habilidades físicas com identidade própria e escalada de poder por nível (Arqueiro)

Pedidos do Will (11/11/2026): nenhuma habilidade pode ser só uma flecha de outra cor, e subir de nível tem de mudar a tela até virar caos (ecos, ricochetes, orbitais). Continua os docs 36 e 37. Código em `godot/scripts2d/efeitos_arqueiro_fisico_2d.gd` e `efeitos_arqueiro_sombra_2d.gd`; números só nos CSV de `godot/data2d/`.

## 1. As 11 físicas (Precisão, Caçada, Sombra)
| Skill (`id`) | Nome | Mecânica própria | Leitura na tela |
|---|---|---|---|
| `power_shot` | Virote de Cerco | atravessa `qtd` corpos, ARRASTA cada um na direção do voo e crava no chão com onda que atordoa (`raio`, `duracao`) | dardo de balista grande, poeira, rachaduras |
| `sniper_shot` | Tiro Certeiro | trava a mira no inimigo de maior vida (retículo fecha), tiro instantâneo atravessa a linha; o travado leva crítico | retículo dourado, feixe branco, corte em X |
| `rapid_volley` | Revoada | flechas saem para os lados e fazem a curva, cada uma atrás de um inimigo diferente | curvas douradas teleguiadas |
| `fan_of_arrows` | Leque de Lâminas | lâminas giram para fora, param e VOLTAM ao arqueiro, ferindo nas duas passagens | discos de aço girando |
| `arrow_rain` | Chuva de Flechas | flechas de verdade caem e cravam no chão; quem é atingido fica lento (`valor`) | campo de flechas cravadas |
| `spike_trap` | Armadilha de Mandíbulas | voa, abre os dentes, e ao ser pisada FECHA: fere, atordoa e puxa todos do raio para o centro | mandíbulas de aço |
| `explosive_arrow` | Flecha de Estilhaços | pote que estoura ao cair e semeia `qtd` bombas em anel, cada uma explode em seguida (`valor` = dano por bomba) | bombas vermelhas quicando |
| `hunters_mark` | Marca do Caçador | falcão mergulha e marca o alvo; se o marcado morre, o falcão leva a marca ao vizinho (`raio`) | falcão e retículo girando |
| `backstep_shot` | Salto das Sombras | salta e atira; no lugar fica um duplo de sombra que estoura em quem encosta (`raio`, `valor`) | silhueta violeta e penas de corvo |
| `smoke_bomb` | Bomba de Fumaça | nuvem espessa: inimigos lentos e o arqueiro dentro dela não leva dano | bolhas roxas em três tons |
| `adrenaline` | Adrenalina (ult) | onda de choque empurra quem está em volta (`raio`), depois vultos e vento âmbar | anel branco, vultos do herói |

## 2. Escalada por nível do jogador (`poder_nivel_2d.gd`, `data2d/poder_nivel.csv`)
- **Ecos**: nos níveis 6, 12 e 18 cada ativa disparada solta 1, 2 ou 3 cópias sobre OUTROS inimigos, a 70% do dano.
- **Ricochete**: toda flecha pula de inimigo em inimigo, 1 pulo a cada 4 níveis (teto 6), 80% do dano por pulo, com arco de luz entre os alvos.
- **Recarga**: 2,5% menos recarga por nível (teto 50%).
- **Orbitais** (`orbitais_poder_2d.gd`): 1 lâmina espectral em órbita a cada 3 níveis (teto 6), ferem quem encosta; anel tracejado no chão.
Reutilizável por Guerreiro e Mago (a classe só precisa chamar `PoderNivel`).

## 3. Verificação
`test_fisico_2d.gd` confere a mecânica de cada uma (arrasto, mira no mais forte, revoada repartida, volta da lâmina, puxão, marca que salta, duplo que estoura...). Capturas: `godot/scripts2d/tools/video_fisico_2d.gd` (uma skill por vez) e `video_poder_2d.gd` (níveis 1, 8 e 15 no jogo real).

## 4. Falta (próximas etapas pedidas)
Progressão de `qtd`/ricochete/cadeia por nível de cada habilidade e evolução no nível máximo, Eco do básico mais forte por nível, pool de nós e teto de partículas medidos na partida do bot no chefe.
