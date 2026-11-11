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

## Golpes da Tecelã (11/11/2026)
A Tecelã (`godot/scripts2d/tecela_2d.gd`, ligada em `run_2d.gd` por `IaChefePortao`) mantém o corpo a corpo do inimigo comum e ganha três golpes próprios, em ciclo, cada um com aviso no chão antes de sair. Ficam no cliente (GDScript, números em CSV) e não no ShatterCore: o core ainda não tem chefes com padrões (o Guardião também vive no cliente, em `boss_2d.gd`); quando a migração chegar, os três golpes viram linhas de padrão como as do `boss_patterns_2d.csv`.

| Golpe | Aviso | Efeito | Como escapar |
|---|---|---|---|
| Teia | fio que ela lança até o ponto (travado no início do aviso) e círculo claro que enche, 1,1 s | mancha de teia por 5,5 s que tira 55% da velocidade de corrida de quem está dentro (o Arqueiro fica azulado) | sair do círculo antes de cair, ou esquivar (a esquiva não é freada) |
| Badalada | anéis âmbar se fechando sobre o sino e o contorno do alcance, 1,4 s | onda em anel (520 px) a 420 px/s, dano uma vez, 90% do dano base | esquiva com invulnerabilidade na hora em que o anel passa |
| Filhotes | fendas âmbar em 3 pontos em volta dela com fios até lá, 1,25 s | 3 Filhotes de Cascalho (5 na fase 2), no máximo 7 vivos; saem da conta do spawner e morrem junto com ela | matar os filhotes ou atirar nela de longe |

Abaixo de 50% de vida entra a fase 2: avisos 15% mais curtos, pausas 35% menores e ninhadas com 2 a mais. Tempos, raios e dano: `data2d/tecela_golpes_2d.csv` e as chaves `tecela_*` de `run_settings.csv`. Teste: `test_ponte_2d.gd` (`_testar_tecela`). Capturas dos avisos e dos efeitos: `godot --path godot --resolution 1280x720 --script res://scripts2d/tools/captura_tecela_2d.gd -- pasta` (precisa de janela).

## Acabamento (11/11/2026)
- **Abismo**: a névoa deixou de ser mancha radial macia: `tools/mapas/ponte_nevoa.py` pinta `nevoa_0..2.png` (três tons de azul frio, degraus em pontilhado Bayer, bordas em degraus irregulares) e dois arcos distantes (`arco_distante_0..1.png`, outra ponte no fundo que some na névoa), colocados por `terreno_2d.gd` (`_nevoa_do_abismo`; o fundo liso do abismo agora fica em z -5, sob a névoa).
- **Sentinela Oca em bronze escurecido** só nesta área: `tools/sprites2d/recolorir_sentinela_bronze.py` recolore as folhas (comum e elite) e `data2d/arte_fase_2d.csv` (fase, inimigo, arte) troca a folha ao nascer; a Cripta e a Pedreira ficam no dourado.
- **Filhotes 15% menores**: folha regerada com `esc=8,9` (era 10,5) e raio de colisão 11 (era 13).

## Enquadramento da chefe
O corpo da Tecelã (uns 300 px acima do pé) cortava no alto. Perto dela (até `camera_chefe_raio`, 900 px) a câmera se afasta (`camera_chefe_zoom_bell_weaver`, 0,78) e mira a meio caminho entre o jogador e o meio do corpo dela (`camera_chefe_vies_...` e `camera_chefe_dy_...`), em transição de uns 0,8 s (`run_2d.gd`, `_alvo_camera`). Só vale para chefes de portão com essas chaves por id: as outras áreas ficam como estavam. Se o jogador foge para longe (mais de uns 450 px), a cabeça ainda pode cortar: o jogador sempre fica na tela.

## Regras e números (tudo em CSV)
- `enemies.csv`: `gravel_spiderling` (30 de vida, rápido, dano 7) e `bell_weaver` (300 de vida de base).
- `ondas.csv` e `ondas_fases.csv`: 7 ondas; filhotes, morcegos e fantasmas errantes desde o começo, arqueiros fantasmas a partir da 2, sentinela oca como elite a partir da 4 e o Carcereiro do Ossuário como mini-chefe na 7. O Arauto de Pedra não entra nesta área.
- A Tecelã é chefe do tipo elite do portão (inimigo comum com `gate_elite_*`), como o Capitão na Pedreira, com a IA de golpes própria acima. Duas chaves novas por inimigo em `run_settings.csv`: `gate_elite_scale_<id>` e `gate_elite_hp_mult_<id>` (a folha dela já nasce no tamanho de chefe, então a escala é 1).

## Como ver
```
godot --path godot --resolution 1600x900 --script res://scripts2d/tools/captura_marcos_2d.gd -- saida sala=res://data2d/rooms/fase_3.txt elite=bell_weaver 1_inicio:12:26:d 2_praca:50:24.2:g:cy-150 6_sino_maior:160:19:e:cx180:cy-200
godot --path godot --resolution 1280x720 --script res://scripts2d/tools/partida_2d.gd -- pasta 5 1 110 ponte 6
```
Capturas e vídeo desta entrega: `/mnt/project-files/capturas/ponte_do_sino/`.

## O que ficou para depois
- O sino caído é pequeno perto do sino do pórtico; vale redesenhar maior numa próxima passada de arte.
- Som dos sinos e música da área.
