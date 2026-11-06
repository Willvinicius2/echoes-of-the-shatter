# Arqueiro e cenário no PixelLab (05/11/2026)

Substitui o v7 feito à mão (Will achou ruim). Plano grátis (40 gerações; usadas ~28 de 40). Termos: arte do usuário, uso comercial permitido; proibido treinar modelo com as saídas.

- Arqueiro: `create-character-v3`, 8 direções, 64 px, vista "low top-down" (2 gerações). Andar: template `walking` (1 geração por direção). Atacar: modo v3 com texto (arco puxado e solto). Morrer: template `falling-back-death`.
- Brutos em `art-src/pixellab/arqueiro/` (rotações e animações por direção). `tools/sprites2d/montar_arqueiro_pixellab.py` monta as folhas (quadro 92, pivô 46,76; linhas S, SE, E, NE, N). idle, hit e dodge são derivados (respiração de 1 px, flash branco, andar com salto).
- Piso: `create-tileset` 32 px, ampliado 2x para as células 0..3 e 6 do atlas (`tools/sprites2d/aplicar_piso_pixellab.py`). Braseiro 48x64 via `create-image-pixflux`, em `godot/art2d/pixellab/`, ainda não ligado (o tile do braseiro tem a chama tratada por `clima_2d.gd`).

Segunda rodada (05/11): ataque regerado ("attack2", sem flecha no prompt; o modelo ainda desenha uma flecha pequena em S/E/NE/N, a flecha de verdade sai como projétil do motor) e arco vermelho de E corrigido para marrom; piso recolorido para cinza-arroxeado do atlas; cena de teste em `tools/sprites2d/cena_teste_pixellab.py`.

Limitações conhecidas (antes da 2ª rodada, a do piso azulado está resolvida): a animação de ataque gerada atira para o lado direito do quadro nas direções S/SE/E e esconde a flecha em NE/N (a âncora de disparo fica na mão do arco); o piso azul-esverdeado destoa das paredes cinzas do atlas pintado; idle quase parado.

Nota: o arqueiro agora é um ranger de capuz verde (capa verde-musgo, armadura prateada), não mais o capuz escuro do v7.

## Etapa 1 do roteiro (06/11): fechar o arqueiro no jogo
Linha única combinada com o Will: 1) arqueiro em pixel art no jogo, 2) fase completa jogável com o arqueiro até o chefe, 3) só então guerreiro, mago e mapas novos. Pendências do arqueiro herdadas do PR 205: capturas no Godot (CI, rótulo `capturas-pixel`), corrida de S com passada mais aberta, braseiro novo ligado ao tile, variantes de laje (o glifo se repete no piso).

## Etapa 2 (06/11): fase jogável com o arqueiro em pixel art
- Corrida de frente (S) regerada no PixelLab (modo v3, 8 quadros, `corrida_s_loop`; a geração com `template running-6-frames` perdeu o arco e foi descartada). Usa os quadros 3 a 8; os antigos ficam em `art-src/pixellab/arqueiro/animations/walking_s_antigo/`. Plano grátis: sobram 2 gerações das 40. O host `backblaze.pixellab.ai` não é liberado no container; as imagens vêm em base64 pelo `GET /v2/background-jobs/<id>`.
- Props e vegetação: `tools/sprites2d/pixelar_props.py [passo=2] [cores=14]` lê os originais HD de `art-src/props-hd-originais/` e grava em `godot/art2d/props/` com grade de 1 px de mundo (a mesma do arqueiro; `pixelar_props.py 1 18`, parecer do Jev), 18 cores, teto de altura para vegetação baixa (30 a 40 px), pilha de caveiras menor e menos saturada por prop, contorno escuro de 1 px de grade e alfa binário; ajusta `props_manifest.csv` (tamanho e pivô na base opaca) e a `escala` em `props_2d.csv` (= passo / ampliação inteira), sem mudar o tamanho na tela. `altar_candles` fica como era (velas animadas por código).
- Braseiro: `tools/sprites2d/aplicar_braseiro_pixellab.py` troca a célula 15 do atlas pelo braseiro de pedra do PixelLab em 1:1; o `clima_2d.gd` tira a chama pintada e põe o fogo animado (`clima.csv`: fogo 26x36, `tigela_borda` 0,31 serve para esta arte). Captura de perto: `scripts2d/tools/captura_braseiro_2d.gd`.
- Braseiro: 25% maior (vizinho mais próximo), sem a chama pintada.

## Polimento da fase (06/11, follow-ups da etapa 2)
- Sombra de contato dos props (`ancoragem_2d.gd`): 1 tom chapado (alfa 0.55) com borda e laterais em dither ordenado Bayer 4x4, sem o blur de 5 px; a sombra projetada usa `step(0.5, alfa)` para não esmaecer ao inclinar.
- Cascalho no fim dos caminhos e lajes soltas (`terreno_2d.gd`): contorno quase preto e duas facetas (clara em cima à esquerda, sombra de 1 tom embaixo à direita), no lugar de 2 tons chapados.
- Tronco seco grande (`tree_dead_large`) conferido: grade de 1 px (escala 1), sem blocos ampliados.
- Dica de controles do HUD: sem faixa escura (tapava galhos do chão), contorno de 1 px em 4 direções.
- Follow-ups da revisão (PR 210): sombra projetada de sólidos 30% mais curta e mais fraca, com a ponta serrilhada em dither; terra pisada sob arbustos num anel só de 1 tom (eram 3 com alfa em degradê); pedras do cascalho e lajes soltas em cinza quente (antes azulado).
- Inimigos (PR 210): as folhas HD pintadas dos inimigos da Cripta (sentinela, soldado esqueleto, morcego, arqueiro fantasma, espectro acorrentado, fantasma errante, Guardião e as variantes elite) passaram por `tools/sprites2d/pixelar_inimigos.py`: quadro reduzido (fator 0.72; 0.7 nos grandes), 20 cores por folha, alfa binário e contorno de 1 px, na mesma densidade do arqueiro (escala 2.5 em `sprites_escala.csv`). Os HD originais ficam em `art-src/sprites-hd-originais/` (fonte da rodada, que é repetível). A barra de vida do inimigo agora acompanha o topo do sprite pixelado. Captura de conferência: `scripts2d/tools/captura_inimigos_2d.gd`. Não foram gastas gerações do PixelLab.
