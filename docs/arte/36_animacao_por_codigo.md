# Animação por código dos inimigos (sem serviço pago)

Estado em 10/11/2026. O saldo do PixelLab acabou e o dono decidiu **não pagar nada**: a arte que dependia dele (as animações do Cão de Cinza e do Arauto de Pedra, depois os ícones) passa a sair de ferramentas gratuitas, rodando na própria máquina. Este documento registra o método do **Cão de Cinza**, o primeiro inimigo feito assim; os outros entram aqui quando existirem.

## O que é
A base aprovada do Cão de Cinza (5 vistas de 64 px do PixelLab, em `art-src/pixellab/cao_de_cinza/base/jogo_<S|SE|E|NE|N>.png`, aprovada pelo Jev) é recortada em peças e **só se move**: nenhum pixel é pintado de novo, a não ser a boca, os dentes, as cinzas e as fagulhas. Contorno de 1 px, olhos de 2x2, luz quente de lado e a paleta ficam como foram aprovados.

Tudo é deslocamento de pixel inteiro (translação, cisalhamento por linha ou coluna, reamostragem de linhas pelo vizinho mais próximo). Rotação com reamostragem não entra: quebraria o contorno de 1 px.

## Peças (por direção)
- **pernas**: cada vista tem 2 ou 3 janelas de perna (`partes.py`, tabela `CFG`); a perna é presa no quadril, o pé desloca (`deformar_perna`) e 3 linhas de sobreposição por baixo do corpo escondem a emenda;
- **caudas** (`cA` a grande, `cB` a pequena): onda por cisalhamento, peso 0 na raiz e 1 na ponta;
- **mandíbula** (vistas S, SE, E e NE): a parte de baixo do focinho desce, e o vão ganha contorno preto, interior vermelho e dentes (a vista N, de costas, não mostra a boca: só o bote);
- **corpo**: o resto, com respiração, balanço (sobe e desce 2 px na corrida) e inclinação por cisalhamento de colunas;
- **brasas**: o olho e as brasas apagam em degraus da paleta (`DEGRAU`) na morte e piscam de leve no idle; fagulhas sobem das brasas soltas.

## Animações (folhas de 92 px, 5 linhas S, SE, E, NE, N; as outras 3 direções o jogo espelha)
| Animação | Quadros | FPS | Como |
|---|---|---|---|
| `idle` | 6 | 8 | respira, cauda balança, brilho do olho pulsa, fagulhas sobem |
| `run` | 8 | 12 | trote em tesoura: as patas de grupos opostos vão uma à frente e outra atrás (passada aberta nos quadros 2 e 6), a pata sobe enquanto avança, corpo sobe e desce 2 px |
| `attack` | 8 | 16 | agacha e recua (quadros 0 e 1), bote de 10 a 12 px com a mandíbula aberta até 5 px (quadros 3 e 4; **contato no quadro 4**), recolhe (5 a 7) |
| `hit` | 3 | 12 | recuo de 3 px, agacha, cabeça cai |
| `death` | 8 | 10 | afunda, patas abrem, cabeça cai, olhos apagam; do quadro 4 em diante vira cinza e brasa de cima para baixo e sobra um montinho de cinzas, que o jogo dissolve em seguida |

Paleta: 25 cores no conjunto (22 da base + vermelho da boca, osso dos dentes e o vermelho-brasa do olho apagando), alfa binário. Os pés de todas as direções ficam na linha 74 do quadro (pivô (46, 74)); o bote chega a 87 px de largura e a morte não passa de 75, sem encostar na borda. O teste `_testar_arte_do_cao` (`test_pedreira_2d.gd`) confere o pivô, o alfa, a paleta, os quadros vazios e a borda.

## Como gerar
```
python3 tools/sprites2d/cao_de_cinza/montar_folhas.py            # grava godot/art2d/sprites/ash_hound/ash_hound_<anim>.png
python3 tools/sprites2d/cao_de_cinza/contato.py <pasta_das_folhas> <pasta_de_saida>   # folhas de contato para revisão (fora do Git)
python3 tools/sprites2d/cao_de_cinza/partes.py <pasta_de_saida> [direção]            # recortes coloridos sobre a base
```
Use `python3` simples (não `-I`: o script importa os módulos vizinhos). A saída é determinística (as sementes das cinzas vêm de `zlib.crc32`), então rodar de novo regrava os mesmos bytes. Os arquivos: `rig.py` (deslocamentos e deformações), `partes.py` (recortes por direção), `animacao.py` (poses e animações), `montar_folhas.py` (monta e confere as folhas).

## Revisão
Prévia vista pelo Jev em 10/11/2026: aprovada para integrar (contorno, olhos, luz e paleta batem; silhueta preservada nas 5 direções; morte a melhor das animações; escala de 0,85x a 1x do arqueiro). Dois refinos pedidos e feitos: corrida com passada mais aberta e balanço do corpo (o trote anterior quase não se distinguia entre os quadros) e mordida com avanço maior e boca aberta em mais quadros e mais larga.

## Limites
- Depende de uma base aprovada de 5 vistas; peça nova de outro inimigo pede uma entrada em `partes.py` (caixas das pernas, caudas e mandíbula) e outra em `animacao.py`.
- Não inventa pose que a base não permite (virar de lado, levantar patas dianteiras); serve para quadrúpedes e figuras de silhueta simples.
- Inimigos sem base (Arauto de Pedra e Carcereiro) seguem outro caminho gratuito: modelo 3D feito por código e renderizado em pixel art (ver o histórico do PR e este documento quando entrarem).
