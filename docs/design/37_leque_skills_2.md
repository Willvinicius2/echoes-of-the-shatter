# 37. Segundo leque de skills (12 novas, 3 por elemento)

Pedido do Will (02/11/2026): "tem poucas ainda, a gente tem vários elementos, tem que ter mais diversidade". Continua o doc 36 (regras de identidade, orçamento e hierarquia de brilho valem aqui). Cada skill é um nó com `_draw` (sem sprite sheet nova e sem partícula de GPU); código em `godot/scripts2d/efeitos_extra_<elemento>_2d.gd`, números só em `godot/data2d/habilidades_arqueiro.csv`.

Regra mantida: duas skills do mesmo elemento nunca repetem a família de forma.

| Elemento | Skill (`id`) | Família | Mecânica | Silhueta / leitura |
|---|---|---|---|---|
| Raio | Trovoada `thunder_burst` | estrela radial | 8 raios saem do arqueiro em todas as direções; fere e choca quem está no corredor | estrela de relâmpagos (a Nova Gélida é anel, esta é estrela) |
| Raio | Tempestade de Raios `sky_storm` | queda do céu | nuvem no ponto mirado derruba `qtd` colunas, uma por vez, cada uma com sombra de aviso | nuvem escura + colunas altas |
| Raio | Orbes Tempestuosos `storm_orbs` | orbital | `qtd` esferas giram em volta do arqueiro, ligadas por arcos; ferem quem encosta | esferas e triângulo elétrico |
| Veneno | Contágio `plague_spread` | contágio | flecha infecta o alvo; o veneno pula a todos no raio e, se o foco morre, passa ao mais perto | filetes de esporos ligando os infectados |
| Veneno | Minas Tóxicas `toxic_mines` | armadilha | `qtd` minas se armam e estouram em nuvem ao aproximar inimigo | casco com espinhos e luz que pisca |
| Veneno | Gêiser Ácido `acid_geyser` | erupção em alvos | jatos sob os `qtd` inimigos mais perto, com aviso; envenena e atordoa | coluna de ácido com gotas |
| Gelo | Lança de Gelo `icicle_lance` | feixe | lança instantânea atravessa a linha, `qtd` acúmulos de frio, estilhaça | haste comprida + lascas laterais |
| Gelo | Espinhos de Gelo `ice_spikes` | erupção em linha | onda de `qtd` espinhos brota em fila; fere, gela e atordoa curto | cachos de cristais subindo em sequência |
| Gelo | Nevasca `blizzard` | aura móvel | tempestade de neve acompanha o arqueiro, pulsa dano e 1 de frio | flocos em espiral e anel de pulso |
| Fogo | Sopro Flamejante `flame_breath` | cone | cone de chamas que segue a mira por `duracao`, queima | línguas de fogo abrindo em cone |
| Fogo | Anel de Fogo `ring_of_fire` | anel parado | círculo de chamas no chão; queima quem cruza a faixa | coroa de chamas e chão chamuscado |
| Fogo | Bomba-Rastilho `fuse_bomb` | contágio explosivo | flecha vira bomba de pavio; ao explodir arma as vizinhas, `qtd` gerações, `valor` do dano por geração | esfera preta com pavio aceso |

Campos do CSV: `dano` multiplicador; `qtd` (raios, orbes, minas, jatos, acúmulos, espinhos, gerações); `raio` (área); `duracao` (vida); `alcance`; `valor` (choque/dps de veneno/queima/lentidão/fração por geração). Anel de Fogo usa `alcance` como largura da faixa; Sopro usa `angulo` como abertura do cone.

## Ícones
`icones_2d.gd` ganhou 12 formas próprias (estrela, gota, cristal, bomba, tornado, nuvem, espinhos, orbes, sopro, cometa, serpente, geiser, floco) e as cinco skills do doc 36 deixaram de reutilizar formas genéricas (tornado, cometa, cristal, serpente).

## Verificação
`_testar_leque_skills` (test_2d.gd) executa cada skill nova contra 3 inimigos e confere o status e o dano esperados. `captura_skills_2d.gd` aceita os 12 ids para gerar capturas/GIF.
