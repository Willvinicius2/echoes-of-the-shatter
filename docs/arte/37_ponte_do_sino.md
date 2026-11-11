# 37. Ponte do Sino (área 3)

Registro de 11/11/2026. Terceira área jogável, depois da Cripta e da Pedreira dos Ecos. Tema, elenco e medidas decididos pela thread de direção visual (Jev). Toda a arte foi feita por código, sem PixelLab e sem custo (método do `docs/arte/36_animacao_por_codigo.md`).

## O que é
Uma ponte de pedra muito longa sobre um abismo com névoa, cortada por praças onde ficam os sinos. No fim, a arena do Sino Maior, onde a Tecelã de Cascalho fez o ninho. Abre ao vencer a Pedreira (`fases_2d.csv`, coluna `requer`).

- **Paleta**: azul-acinzentado frio. Os únicos acentos quentes são o bronze dos sinos, os lampiões e os olhos âmbar das aranhas. A Cripta é verde e a Pedreira é ocre, então as três áreas se distinguem pela cor.
- **Abismo**: só cenário e barreira. As células `f` bloqueiam quem anda e deixam a flecha passar (camada 8, como o fosso da Pedreira). Não existe queda que mata.
- **Medidas**: o trecho mais estreito tem 8 células jogáveis; as praças têm 18x15 e 20x14 e a arena 21x24 (o mínimo pedido era 16x12). O teste `test_ponte_2d.gd` trava essas medidas.

## Mapa (`godot/data2d/rooms/fase_3.txt`, 180x50 células)
Gerado por `tools/mapas/gerar_fase_3.py` (não editar o `.txt` à mão). Da esquerda para a direita:

| Trecho | O que tem | Encontro adormecido (`@guarda`) |
|---|---|---|
| Cabeceira | início, lampiões | nenhum |
| Primeiro vão | ponte estreita | 3 filhotes |
| Praça dos Vigias | sino inteiro no pórtico | 3 filhotes e 1 arqueiro fantasma |
| Vão dos atiradores | ponte estreita | 2 arqueiros fantasmas e 1 fantasma errante |
| Praça do Sino Caído | sino rachado no chão; balcão ao sul com o baú | 5 filhotes e 1 sentinela; 4 filhotes no baú |
| Terceiro vão | ponte | 2 arqueiros fantasmas e 3 morcegos |
| Descanso e último vão | respiro antes do chefe | 2 sentinelas e 3 filhotes |
| Arena do Sino Maior | o Sino Maior com as teias, G (Tecelã) e X (portal) | chefe |

`@piso ponte` liga o tema no `room_2d.gd`: atlas `godot/art2d/tiles/cripta_ponte.png`, fundo de abismo, névoa nas células `f`, estrada e lajes frias, e os props herdados da Cripta esfriados por cor. As bordas da ponte (parapeito ao norte, face com fiadas, arcos e pilares ao sul) são decalques em `godot/art2d/ponte/borda_NN.png`, pintados por `tools/mapas/ponte_pixel.py`.

## Arte nova
| O quê | Arquivo | Como regerar |
|---|---|---|
| Piso e props (3 sinos, casulo, 2 teias, entulho) | `godot/art2d/tiles/cripta_ponte.png`, `godot/art2d/props/ponte_*.png` | `python3 -I tools/sprites2d/montar_ponte.py [--previas PASTA]` |
| Mapa e bordas | `godot/data2d/rooms/fase_3.txt`, `godot/art2d/ponte/` | `python3 -I tools/mapas/gerar_fase_3.py [--visao PNG]` |
| Tecelã de Cascalho (`bell_weaver`) e Filhote de Cascalho (`gravel_spiderling`) | `godot/art2d/sprites/<id>/<id>_<anim>.png` | `python3 tools/sprites2d/tecela_de_cascalho/montar_folhas.py [tecela\|filhote\|todas]` |

- **Tecelã de Cascalho**: aranha de bronze de sino com pátina verde-azulada, fios de teia luminosos nas pernas, olhos âmbar e o abdômen em forma de sino quebrado (faltam três gomos e dá para ver o badalo). Quadro de 256 px, pivô (128, 164), 5 animações em 5 direções, contato do golpe no quadro 5.
- **Filhote de Cascalho**: aranha pequena de cascalho cinza, pernas bem abertas e pontos âmbar nas costas. Quadro de 96 px, pivô (48, 58), mesmas 5 animações.
- Folhas de contato para revisão (fora do Git): `python3 tools/sprites2d/tecela_de_cascalho/contato.py <tecela|filhote> <anim> <direcoes|todas> <escala> <png>`.

## Regras e números (tudo em CSV)
- `enemies.csv`: `gravel_spiderling` (30 de vida, rápido, dano 7) e `bell_weaver` (300 de vida de base).
- `ondas.csv` e `ondas_fases.csv`: 7 ondas; filhotes, morcegos e fantasmas errantes desde o começo, arqueiros fantasmas a partir da 2, sentinela oca como elite a partir da 4 e o Carcereiro do Ossuário como mini-chefe na 7. O Arauto de Pedra não entra nesta área.
- A Tecelã é chefe do tipo elite do portão (inimigo comum com `gate_elite_*`), como o Capitão na Pedreira. Duas chaves novas por inimigo em `run_settings.csv`: `gate_elite_scale_<id>` e `gate_elite_hp_mult_<id>` (a folha dela já nasce no tamanho de chefe, então a escala é 1).

## Como ver
```
godot --path godot --resolution 1600x900 --script res://scripts2d/tools/captura_marcos_2d.gd -- saida sala=res://data2d/rooms/fase_3.txt elite=bell_weaver 1_inicio:12:26:d 2_praca:50:24.2:g:cy-150 6_sino_maior:160:19:e:cx180:cy-200
godot --path godot --resolution 1280x720 --script res://scripts2d/tools/partida_2d.gd -- pasta 5 1 110 ponte 6
```
Capturas e vídeo desta entrega: `/mnt/project-files/capturas/ponte_do_sino/`.

## O que ficou para depois
- A Tecelã usa a IA de corpo a corpo comum. Golpes próprios (teia que prende, chamar filhotes, badalada em área) pedem regra nova e ficam para a migração ao ShatterCore.
- O sino caído é pequeno perto do sino do pórtico; vale redesenhar maior numa próxima passada de arte.
- Som dos sinos e música da área.
