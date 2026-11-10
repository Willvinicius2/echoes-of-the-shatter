# Animação por código dos inimigos (sem serviço pago)

Estado em 10/11/2026. O saldo do PixelLab acabou e o dono decidiu **não pagar nada**: a arte que dependia dele (as animações do Cão de Cinza e do Arauto de Pedra, depois os ícones, que estão no doc 29) passa a sair de ferramentas gratuitas, rodando na própria máquina. Este documento registra os dois métodos usados até agora: o do **Cão de Cinza** (a base aprovada é recortada e só se move) e o do **Arauto de Pedra** (modelo de pedra feito por código e desenhado em pixel art). Os outros inimigos entram aqui quando existirem.

## Cão de Cinza

### O que é
A base aprovada do Cão de Cinza (5 vistas de 64 px do PixelLab, em `art-src/pixellab/cao_de_cinza/base/jogo_<S|SE|E|NE|N>.png`, aprovada pelo Jev) é recortada em peças e **só se move**: nenhum pixel é pintado de novo, a não ser a boca, os dentes, as cinzas e as fagulhas. Contorno de 1 px, olhos de 2x2, luz quente de lado e a paleta ficam como foram aprovados.

Tudo é deslocamento de pixel inteiro (translação, cisalhamento por linha ou coluna, reamostragem de linhas pelo vizinho mais próximo). Rotação com reamostragem não entra: quebraria o contorno de 1 px.

### Peças (por direção)
- **pernas**: cada vista tem 2 ou 3 janelas de perna (`partes.py`, tabela `CFG`); a perna é presa no quadril, o pé desloca (`deformar_perna`) e 3 linhas de sobreposição por baixo do corpo escondem a emenda;
- **caudas** (`cA` a grande, `cB` a pequena): onda por cisalhamento, peso 0 na raiz e 1 na ponta;
- **mandíbula** (vistas S, SE, E e NE): a parte de baixo do focinho desce, e o vão ganha contorno preto, interior vermelho e dentes (a vista N, de costas, não mostra a boca: só o bote);
- **corpo**: o resto, com respiração, balanço (sobe e desce 2 px na corrida) e inclinação por cisalhamento de colunas;
- **brasas**: o olho e as brasas apagam em degraus da paleta (`DEGRAU`) na morte e piscam de leve no idle; fagulhas sobem das brasas soltas.

### Animações (folhas de 92 px, 5 linhas S, SE, E, NE, N; as outras 3 direções o jogo espelha)
| Animação | Quadros | FPS | Como |
|---|---|---|---|
| `idle` | 6 | 8 | respira, cauda balança, brilho do olho pulsa, fagulhas sobem |
| `run` | 8 | 12 | trote em tesoura: as patas de grupos opostos vão uma à frente e outra atrás (passada aberta nos quadros 2 e 6), a pata sobe enquanto avança, corpo sobe e desce 2 px |
| `attack` | 8 | 16 | agacha e recua (quadros 0 e 1), bote de 10 a 12 px com a mandíbula aberta até 5 px (quadros 3 e 4; **contato no quadro 4**), recolhe (5 a 7) |
| `hit` | 3 | 12 | recuo de 3 px, agacha, cabeça cai |
| `death` | 8 | 10 | afunda, patas abrem, cabeça cai, olhos apagam; do quadro 4 em diante vira cinza e brasa de cima para baixo e sobra um montinho de cinzas, que o jogo dissolve em seguida |

Paleta: 25 cores no conjunto (22 da base + vermelho da boca, osso dos dentes e o vermelho-brasa do olho apagando), alfa binário. Os pés de todas as direções ficam na linha 74 do quadro (pivô (46, 74)); o bote chega a 87 px de largura e a morte não passa de 75, sem encostar na borda. O teste `_testar_arte_do_cao` (`test_pedreira_2d.gd`) confere o pivô, o alfa, a paleta, os quadros vazios e a borda.

### Como gerar
```
python3 tools/sprites2d/cao_de_cinza/montar_folhas.py            # grava godot/art2d/sprites/ash_hound/ash_hound_<anim>.png
python3 tools/sprites2d/cao_de_cinza/contato.py <pasta_das_folhas> <pasta_de_saida>   # folhas de contato para revisão (fora do Git)
python3 tools/sprites2d/cao_de_cinza/partes.py <pasta_de_saida> [direção]            # recortes coloridos sobre a base
```
Use `python3` simples (não `-I`: o script importa os módulos vizinhos). A saída é determinística (as sementes das cinzas vêm de `zlib.crc32`), então rodar de novo regrava os mesmos bytes. Os arquivos: `rig.py` (deslocamentos e deformações), `partes.py` (recortes por direção), `animacao.py` (poses e animações), `montar_folhas.py` (monta e confere as folhas).

### Revisão
Prévia vista pelo Jev em 10/11/2026: aprovada para integrar (contorno, olhos, luz e paleta batem; silhueta preservada nas 5 direções; morte a melhor das animações; escala de 0,85x a 1x do arqueiro). Dois refinos pedidos e feitos: corrida com passada mais aberta e balanço do corpo (o trote anterior quase não se distinguia entre os quadros) e mordida com avanço maior e boca aberta em mais quadros e mais larga.

### Limites
- Depende de uma base aprovada de 5 vistas; peça nova de outro inimigo pede uma entrada em `partes.py` (caixas das pernas, caudas e mandíbula) e outra em `animacao.py`.
- Não inventa pose que a base não permite (virar de lado, levantar patas dianteiras); serve para quadrúpedes e figuras de silhueta simples.
- Inimigo sem base aprovada segue o outro caminho gratuito, o do Arauto de Pedra logo abaixo.

## Arauto de Pedra

O Arauto não tinha base de pixel art: só a folha de conceito e o giro `docs/arte/referencias-geracao/aprovadas/modelagem/m06`. Em vez de pedir quadros a um serviço pago, o golem é um **modelo 3D de pedra montado por código** (peças chanfradas, juntas de terra e um olho âmbar), desenhado quadro a quadro por um renderizador em numpy, sem GPU, e reduzido a pixel art no mesmo padrão dos inimigos aprovados (contorno de 1 px, luz quente de lado, paleta curta, alfa binário).

### Ferramenta (`tools/sprites2d/arauto_de_pedra/`)
- `golem.py`: as peças do golem (pelve e quadril, pernas, tronco com crista de lajes, ombreiras com musgo, braços, punhos, cabeça) e a árvore de juntas (`JUNTAS`).
- `render.py`: câmera ortográfica de cima (35 graus, 31 px por metro, quadro de 176 px, pivô (88, 132) no centro dos pés), peças como poliedros convexos e esferas, 3x3 amostras por pixel com a cor mais frequente da paleta (nunca meio-tom), sombreado em 5 degraus a partir de uma luz fixa quente, musgo nas faces viradas para cima, rachaduras, linhas internas entre peças e contorno externo de 1 px. A pedra é cinza-areia, o musgo verde, as juntas de terra e o olho âmbar (o ponto mais claro do desenho).
- `animacao.py`: cinemática direta (ângulos por junta e quadro) para as 5 animações e as 5 direções (o modelo gira em torno do eixo vertical: S, SE, E, NE, N; o jogo espelha as outras três). A poeira da martelada e dos desmoronamentos é desenhada em 2D só nos pixels vazios.
- `montar_folhas.py`: monta as folhas (processos em paralelo) e confere alfa binário, no máximo 24 cores, quadro vazio e folga de 2 px da borda.
- `contato.py`: folhas de contato para revisão (fora do Git).

### Animações (folhas de 176 px, 5 linhas S, SE, E, NE, N)
| Animação | Quadros | FPS | Como |
|---|---|---|---|
| `idle` | 6 | 8 | respira (tronco e ombros), cabeça acompanha, o olho pulsa |
| `run` | 8 | 8 | passada larga e pesada (um ciclo por segundo, o que bate com a velocidade 65), tronco inclinado para a frente, braços balançam pouco |
| `attack` | 8 | 10 | ergue os dois punhos (quadros 1 a 3, com giro do tronco e braços um pouco abertos para não virarem um poste visto de lado), martelada no chão (**contato no quadro 5**, com poeira e seixos), recolhe (6 e 7) |
| `hit` | 3 | 12 | recua o tronco e a cabeça, braços abrem |
| `death` | 8 | 10 | o olho apaga, as peças se soltam e desabam num monte de pedras com juntas de terra e seixos; o jogo dissolve o monte em seguida |

O aviso do golpe soma o `windup` de 0,7 s (idle com a área vermelha enchendo) e os 0,5 s da animação até o contato; os dois valores já estavam em `enemies.csv` e no manifesto, do plano original, e não mudaram.

### No jogo
- Escala 2,5 (1 px da arte = 1 px da grade), cerca de 1,45x a Sentinela Oca. O pé da frente cai até 16 px abaixo do pivô, conforme a direção.
- O quadro tem folga em cima (punhos erguidos e pilha da morte), então `hp_bar_dy` do Arauto é **-64** em `enemies.csv`: `enemy_2d.gd` (`topo_visual`) desce a barra de vida e os números de dano para perto da cabeça, a cerca de 8 px acima do topo da cabeça (mais baixo a barra se confundia com o ombro e o musgo). Valor negativo só existe para ele e para o Carcereiro; os positivos continuam subindo só a barra. A coluna `hp_bar` é o múltiplo da largura padrão de 40 px (`largura_barra()`): 1,5 no Arauto e no Carcereiro, e será o valor dos próximos mini-chefes, porque a barra comum fica pequena para um inimigo desse tamanho (revisão da Direção visual com o Jev, 10/11/2026).
- Paleta: 20 cores no conjunto (pedra 5, musgo 4, terra 4, olho 4, pupila, linha interna e contorno). O teste `_testar_arte_do_arauto` (`test_pedreira_2d.gd`, compartilha o auxiliar com o do cão) confere o pivô e o tamanho do quadro, o pé e o centro do idle nas 5 direções, o alfa, a paleta, os quadros vazios, a borda e o contato do golpe no quadro 5.
- O Carcereiro do Ossuário (`ossuary_warden`) continua pendente: o manifesto aponta para a mesma folha do Arauto, mas ele só volta às ondas com uma prévia própria aprovada pelo Jev.

### Como gerar
```
python3 tools/sprites2d/arauto_de_pedra/montar_folhas.py [pasta_saida] [anim,anim]   # padrão: godot/art2d/sprites/stone_herald
python3 tools/sprites2d/arauto_de_pedra/contato.py <anim> <direcoes|todas> <escala> <arquivo_png>   # folha de contato (fora do Git)
```
Use `python3` simples (não `-I`). A saída é determinística (sementes fixas), cerca de 1 a 2 minutos em 4 núcleos.

### Revisão
Prévia vista pelo Jev em 10/11/2026: aprovada para integrar (escala boa, corrida aprovada nas 5 direções, morte aprovada, martelada lê bem em S, SE e NE). Dois ajustes pedidos e feitos: a pedra estava clara demais e brilhava mais que a Sentinela Oca na Pedreira (hoje as luzes da pedra são cerca de 19% mais escuras, menos creme e mais cinza-areia, com o musgo mais escuro e saturado; o olho âmbar segue o ponto mais claro) e, vistos de lado (direção E), os dois braços erguidos pareciam um poste nos quadros 2 e 3 (o tronco gira 13 graus e os braços se abrem 10 graus nesses quadros).

### Limites
- Estilo de pedra lascada e peças grandes; o que pede detalhe fino (rosto, tecido, mão com dedos) fica fora do alcance do renderizador.
- Peça ou animação nova pede mexer em `golem.py` e `animacao.py` e conferir as 5 direções nas folhas de contato antes de gerar.
- Inimigo de outra silhueta (como o Carcereiro, de ossos) pede um modelo próprio, não só outra paleta.
