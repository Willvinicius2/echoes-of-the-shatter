# 35 — Pedreira dos Ecos (área 2 do Ato I)

Estado em 08/11/2026: **terreno aprovado, inimigos pendentes (PixelLab sem saldo)**. O mapa, o chão, os props, a luz, o portão de pedra e o elite do portão estão prontos e rodando no motor. Os dois inimigos novos que a fase pedia (`ash_hound` e `stone_herald`) ainda não têm folha de sprite, então a fase **não usa nenhum inimigo sem arte** (ver "Inimigos e ondas"). O fluxo de fases (escolha no título, desbloqueio, elite do portão) está em `docs/design/34_fases_e_desbloqueio.md`.

Direção: Jev (direção visual) e o crítico de arte, thread "Terminar o mapa da área 1 do arqueiro". Regras de trabalho: o Will não revisa; as dúvidas de design vão por `docs/progresso/estado.json`.

## O mapa
`godot/data2d/rooms/fase_2.txt`, 160 x 72 tiles (tile de 64 px), **gerado** por `tools/mapas/gerar_fase_2.py` (sai igual a cada execução, semente 2202; não edite o `.txt` à mão). O gerador também grava os PNG dos fossos e da ponte (`godot/art2d/fosso/`, desenhados por `tools/mapas/fosso_pixel.py`) e imprime os pontos de captura.

- Estrada de pedra de **156 tiles** (cerca de 39 s a 4 tiles/s) do pátio de partida ao portão, 2 tiles de largura, lajes 16% mais claras que o piso (`brilho_estrada`), borda irregular de terra.
- **9 encontros** adormecidos (`@guarda`): 8 na estrada e 1 no bolsão. O primeiro vem a menos de 24 tiles do início, com 2 a 3 inimigos, e há 135 células andáveis para recuar atrás dele; a rampa não tem matilha de mais de 3 (as maiores ficam nos trechos 2 e 3). O maior trecho sem encontro nem marco é de 20 tiles (5 s; a regra é no máximo 24, 6 s).
- Trechos: **pátio do início** (carrinho, blocos, andaime e dois braseiros, com a dica de controles), **A Rampa** (estreita, primeiro encontro), **bifurcação do bolsão** (trilha de 1,2 tile que sai da estrada em (57,4; 41,3), dois lampiões na boca com luz, velas e o guindaste do outro lado; ao fim, a clareira do baú), **Campo de Fossos** (6 fossos, 128 células, e a ponte de tábuas de 7 tiles; a reta da ponte tem 15 tiles e a estrada curva logo depois, com um lampião em cada cabeceira), **Os Andaimes** (terraço com pórtico de guindaste fora da estrada, andaimes, blocos e carrinhos, matilhas mais densas), **descanso** (clareira de laje em (139,5; 21,6) com dois braseiros) e a **avenida do portão**.
- **Portão de pedra** em (146; 11): o elite do portão (G) espera 2 tiles à frente dele, dentro de um poço de luz laranja, e o portal (X) fica atrás. A rocha (`m`) fecha a clareira dos dois lados dos bastiões, então só se chega ao portal pelo vão de 2 tiles do portão (o teste confere isso com os colisores de verdade).
- Fossos: corpo `CorpoFossos` na camada 8 (arqueiro e inimigos terrestres não passam; flecha e magia passam por cima); as células `=` da ponte ficam andáveis. Nenhum prop cai sobre `f`/`=`, e o fundo do fosso não leva lasca nem prop (a arte pintada é o fundo).
- Colisão e visão: a rocha `m` bloqueia o passo; a câmera mostra cerca de 10 x 5,6 tiles, então as peças altas (pórticos, andaimes, bastiões) ficam ao sul da estrada e as baixas ao norte. Os props aéreos (`pedreira_portico`, `pedreira_portao`) usam a `Ancoragem` em modo `aereo`: a profundidade vem do pé e eles somem (50%) quando o arqueiro passa atrás.

## Arte feita por código (sem IA generativa)
Grade de 1 px de mundo, alfa binário, contorno preto de 1 px, paleta curta por material, luz de cima à esquerda. Pivô sempre no centro da borda de baixo. Scripts: `tools/sprites2d/montar_pedreira.py` (props), `recolorir_piso_pedreira.py` e `manchas_piso_pedreira.py` (piso) e `tools/mapas/fosso_pixel.py` (fossos e ponte).

| Prop | O que é | Colisão |
| --- | --- | --- |
| `pedreira_blocos` | pilha de blocos de calcário com marcas de cunha | base sólida de 98 x 34 px |
| `pedreira_andaime` | andaime de madeira quebrado, plataforma meio caída, corda | base de 93 x 8 px |
| `pedreira_carrinho` | carrinho de pedra tombado, blocos derramados | base de 99 x 22 px |
| `pedreira_portico` | pórtico de guindaste (marco): pés em A, viga, roldana, corrente, bloco pendurado | só os 4 pés |
| `pedreira_poste_lanterna` | poste com braço, corrente e lanterna de ferro acesa | base do poste (9 x 6 px) |
| `pedreira_portao` | 416 x 254 px: dois bastiões de blocos, vão livre de 2 tiles, verga com pedra-chave, **grade de ferro levantada por correntes** e **guindaste de madeira com contrapeso** no bastião direito; as caveiras são só detalhe | só os dois pés dos bastiões (nada no vão) |
| `pedreira_lasca_0/1/2` | lascas angulares de bloco cortado (1, 2 e 3 fragmentos), no lugar das pedrinhas redondas da área 1 | nenhuma |

Fossos e ponte: pintados por código com borda de pedra, fundo escuro com **3 a 4 montes de entulho com sombra** (não pedrinhas espalhadas) e a ponte de tábuas com guarda-corpo e vigas.

## Terreno e luz
- `@piso pedreira` liga o tema (`tema == "pedreira"` em `room_2d.gd`, `terreno_2d.gd`): atlas `cripta_pedreira.png` (ocre acinzentado, sem o azul da Cripta), manchas de poeira, terra e ferrugem, sem vaga-lumes, lajes da estrada em calcário claro pouco saturado, poeira (não musgo) na junta.
- **Luz quente, nada de verde nem branco estourado**: braseiros em `(1,00; 0,42; 0,12; 0,34)`, velas em `(1,00; 0,55; 0,20; 0,28)`, lampiões em laranja. O teste exige que todas as luzes do mapa tenham vermelho >= verde e azul <= metade do vermelho.
- **Luz própria do elite do portão**: um poço de luz laranja nos pés do G (`@luz` de 3 tiles e 0,28 de intensidade) e, quando ele nasce, um halo aditivo preso a ele que pulsa entre 70% e 100% (`gate_elite_luz_tamanho` 380 px e `gate_elite_luz_alfa` 0,38 em `run_settings.csv`, `Run2D._luz_do_elite`). O halo fica **atrás** do sprite (`show_behind_parent`): ele acende o chão e recorta o elite contra ele, sem pintar o osso de laranja. Revisão do crítico: com o poço de 3,8 tiles e 0,4 centrado no peito, a luz somada ao sprite era de +72 a +86 de vermelho e apagava os olhos ciano; medido com e sem luz na mesma foto, hoje são +14 a +25 e os olhos voltam a ser ciano (o chão em volta segue brilhando, +52).
- **Barra e nome do elite**: a barra grande da HUD desce da faixa do topo (`chefe_elite_y` = 44 em `hud_layout.csv`, a do Guardião fica em 22) e o nome ("Capitão do Ossuário", com acentos) ganha uma placa escura de cantos chanfrados (`Arte.placa_nome`), para ler sobre a verga clara do portão.
- **Guardas variados** (`Run2D._variar_guarda`): os guardas de um mesmo encontro nascem olhando para lados diferentes (a folha já espelha), em quadros diferentes da respiração, e o segundo esqueleto leva um tom a mais de ferrugem (`self_modulate`, soma com o azulado do frio). Tudo sai do ponto do encontro, então a cena é igual a cada execução; ao acordar eles voltam a olhar para o jogador.

## Orla de terra da rocha (`scripts2d/orla_terra_2d.gd`)
A massa de rocha da Pedreira (`m`) não termina mais num corte reto contra o chão aberto. Um `ColorRect` do tamanho do mapa, logo abaixo da camada dos objetos, roda um shader que lê uma textura de 1 px por célula (rocha ou não) e pinta em px inteiros de mundo, sem gradiente:
- do lado aberto: um pé escuro de 2 a 4 px e terra em manchas que rareiam até 6 a 22 px da emenda (largura que varia devagar, borda em blocos de 3 px, salpicos mais claros e mais escuros);
- do lado da rocha: o pé morde 0 a 3 px, em trechos, e uma sombra de contato em dither de Bayer 4x4 fecha a emenda.
O chão da rocha é o próprio tile do piso, escurecido em **marrom** por `Room2D.COR_MASSA_PEDREIRA` (0,56; 0,54; 0,62), nunca o preto da sombra da mata da Cripta (que segue como estava: a área 1 não ganha a orla). Armadilha do shader: `return;` dentro de `fragment()` é erro em Godot (o retângulo vira branco); por isso a lógica é um `if/else` só.

## Inimigos e ondas
O que a fase realmente usa (todos com folha de sprite e stats): `skeleton_soldier`, `hollow_sentinel`, `crypt_bat`, `wandering_ghost`, `ghost_archer` e `chain_wraith`; o elite do portão é o `ossuary_captain` (reaproveita a folha do `skeleton_soldier`, em escala 1,5). As 7 ondas da Pedreira (`ondas.csv`, `ondas_fases.csv`) e o enxame só têm esses tipos, e os 9 encontros do mapa também. O teste `test_pedreira_2d.gd` falha se aparecer um inimigo cuja folha não exista.

**Pendente (PixelLab sem saldo):** `ash_hound` (matilha da fase), `stone_herald` (bruto de pedra) e `ossuary_warden` (que reusa a folha do `stone_herald`). Têm linha em `sprites_manifest.csv` e stats em `enemies.csv`, mas os PNG não existem: o cliente mostra uma caixa marrom provisória. Quando houver saldo, gerar as folhas (formato em `docs/arte/25_formato_folhas_sprites_2d.md`), pôr de volta nas ondas da Pedreira (matilhas de `ash_hound` em todas as ondas e `stone_herald` da 2 em diante, como no desenho original) e nos encontros do gerador. A prévia dos três pendentes, com a caixa provisória que o motor mostra hoje ao lado do arqueiro, está em `docs/arte/sprites2d/capturas_pedreira/12_inimigos_pendentes_caixas_provisorias.png`.

**Atenção na Cripta:** as ondas 3 a 8 da Cripta (`ondas.csv`, fase `cripta`) ainda sorteiam `ash_hound` (3 a 8), `stone_herald` (6 e 7) e `ossuary_warden` (8), então hoje elas mostram a caixa provisória. Isso já era assim antes da Pedreira e não foi mexido aqui.

## Capturas
Pontos do mapa, rodados pela ferramenta do cliente (precisa de janela; no CI e na nuvem use `xvfb-run`):

```
python3 -I tools/mapas/gerar_fase_2.py --visao visao_geral.png      # regrava o mapa e imprime as linhas "captura ..."
xvfb-run -a -s "-screen 0 1600x900x24" godot --path godot --rendering-driver opengl3 --resolution 1600x900 \
  --script res://scripts2d/tools/captura_marcos_2d.gd -- prefixo sala=res://data2d/rooms/fase_2.txt nome:x:y[:g][:e][:d][:cx<px>][:cy<px>] ...
```
Sufixos: `:g` os encontros ao alcance nascem adormecidos; `:e` nasce o elite do portão, parado, dormindo, com a luz própria; `:d` mantém a dica de controles; `:cx` e `:cy` deslocam só a câmera (para o marco ficar acima da HUD). Os guardas de um encontro nascem em anel em volta do ponto dele, então o arqueiro da captura dos andaimes fica 4 tiles atrás do anel (o gerador já calcula isso) e nenhum guarda cola atrás do capuz. Rode um ponto de aquecimento antes (o primeiro quadro pode sair incompleto) e só um Godot por vez. As capturas finais (1600 x 900) estão em `docs/arte/sprites2d/capturas_pedreira/` (início, rampa, bifurcação com os dois lampiões, fosso com o lampião inteiro, ponte, curva depois da ponte, andaimes, descanso, portão com o elite, portão de perto e bolsão) e `00_visao_geral_do_mapa.png`; `12_inimigos_pendentes_caixas_provisorias.png` mostra os inimigos que faltam.

## Testes
`godot --headless --path godot --script res://scripts2d/tools/test_2d.gd` roda `scripts2d/tools/test_pedreira_2d.gd`, que confere: o tema e o tamanho do mapa; P, G, X e o bolsão; todo prop com arte e definição; nenhum `arco_portal` (o portão não repete o da área 1); as lascas; os fossos na camada 8 e a ponte andável; o portão (dois pés, vão de 129 px no centro, aéreo e oculto, sem colisor central, elite à frente e portal atrás, rocha fechando os lados); a máscara da orla de terra e o marrom da rocha; a estrada (156 tiles, ponte, reta de 15 tiles com curva depois, bolsão com lampiões, ritmo dos encontros); a **passagem** com os colisores reais (grade de 32 px, o jogador de 12 px de raio): o G, o X, o baú e todos os encontros são alcançáveis, a linha central da estrada fica livre e, tapando o vão, o portal fecha; e as ondas só com inimigos que têm arte.

## Decisões em aberto (design)
- **Vida e dano do elite do portão:** como chefe do core o `ossuary_captain` fica limitado a no máximo 600 de vida (2,5 vezes a base de 240) e bate com o dano base de 20; pode morrer em poucos segundos no fim da corrida. Ajustar pede vida própria do capitão como chefe ou limites por fase no core (ver `docs/design/34_fases_e_desbloqueio.md`).
- **Inimigos novos da Pedreira:** `ash_hound` e `stone_herald` dependem de saldo no PixelLab. Enquanto isso a fase fica só com os seis inimigos que existem.
