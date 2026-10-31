# 28 — Ícones de habilidades e cartas (31/10/2026)

Os ícones geométricos provisórios (`godot/scripts2d/icones_2d.gd`) são substituídos por PNG em `godot/art2d/ui/icone_<id>.png` (128 px, a tela escala). O `icones_2d.gd` já dá prioridade ao PNG; os polígonos ficam só como reserva.

## Decisão de estilo (Jev, `jev-latest`)
Pintado à mão com glifo central, brilho colorido e moldura de pedra/metal escuro: 76% (contra 21% glifo monocromático gravado e 3% silhueta chapada). Sem quadrados chapados: fundo de pedra com vinheta, halo da cor da habilidade, glifo com gradiente, luz e contorno, moldura chanfrada com fio dourado/colorido e rebites, cantos arredondados. A codificação por cor e os motivos foram consultados, mas o Jev ficou indeciso (q2 59% contra, q3 51% a favor, confiança baixa); valeu a proposta abaixo, e o Will ou o Jev ajustam na revisão.

## Conjunto
| id | habilidade | motivo | cor |
|---|---|---|---|
| tiro | Tiro (slot de clique) | flecha em voo | marfim |
| esquiva | Esquiva (Espaço) | seta circular robusta | ciano |
| bloqueado | slot sem habilidade | cadeado de ferro, brilho apagado | cinza |
| multishot | Salva de Flechas | três flechas em leque | dourado |
| pierce | Ponta Afiada | flecha atravessando escudo | azul gelo |
| evasion | Passo Rápido | bota leve com rastro de vento | verde-água (diferente da esquiva) |
| power | Flecha Pesada (carta) | flecha grossa em chama | laranja |
| haste | Mão Ágil (carta) | raio | amarelo |
| swift | Pés Leves (carta) | bota alada | verde |
| vitality | Vigor (carta) | coração com runa | vermelho |

Gerador: `python3 tools/arte/gen_icones_habilidade.py` (Pillow; reproduz os PNG). Prévia: `docs/arte/sprites2d/icones_habilidades_previa.png`. Os `.import` do Godot nascem na primeira abertura do projeto.
