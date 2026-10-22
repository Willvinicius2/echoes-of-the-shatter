# 24 — Direção visual da Cripta (escala, luz, andares)

Guia curto para a Cripta do Godot. Dono: agente `diretor-visual`. Ele junta as partes aprovadas (estandarte v2, coluna v3, pilar v6, braseiro, velas, estátua, entulho, pisos e tapetes) para nada ficar grande ou pequeno demais. Vale para os cenários e para a montagem em `godot/` (PR 70). Os números marcados **[PROPOSTA]** entram em vigor quando a montagem os aplica e o Will vê no jogo.

Medidas de origem: caixas reais dos `.glb` de `godot/art/models/` (eixo Y para cima, em metros) e `docs/tecnico/14_layout_cripta.md` (salas, corredores, arena).

## 1. Escala-mestra

- **Herói: 1,8 m** (chibi de 3 cabeças; a cabeça tem ~0,6 m). Os tokens antigos (`03_design_tokens.json`, `art3d`) falam em 1,5 m: o valor de 1,8 m passa a mandar, e os tokens devem ser atualizados.
- Unidade do Godot: 1 uu = 1 m. Régua de leitura na câmera 3/4: **uma lajota = 1 m (0,55 herói)**, três lajotas cobrem a largura de um corredor de combate estreito, um herói ocupa meia lajota de largura.
- Inimigo comum 0,6 a 1,3 × herói (1,1 a 2,3 m); elite ×1,15; chefe 3 a 5,3 × herói (5,4 a 9,5 m; o Guardião da arena fica em ~5,4 m).

| Elemento | Medida alvo | Em heróis |
|---|---|---|
| Pé-direito de sala (altura da parede) | 5,4 m | 3,0 |
| Pé-direito de corredor | 4,5 m | 2,5 |
| Parede (espessura visível) | 1,2 m | 0,7 |
| Porta/arco de passagem | 6 m de largura (igual ao corredor, aprovado em `14`) × 4,8 m de altura | 3,3 × 2,7 |
| Corredor | 6 m de largura, 12 m de comprimento | |
| Sala | 24 a 32 m de lado; Arena 40 × 40 m | |
| Degrau | 0,18 m de altura × 0,32 m de piso | 0,1 |
| Corrimão | 0,9 m de altura (meio herói) | 0,5 |

A câmera mostra ~24,8 × 17 m do chão (doc 14). Em uma tela cabem cerca de 14 heróis na horizontal: se um objeto passar de 1/4 da tela, está grande demais.

## 2. Objetos aprovados: escala de montagem **[PROPOSTA]**

Tamanho do `.glb` como exportado, escala uniforme sugerida e tamanho final. O `diretor-visual` mede de novo no Godot antes de fechar.

| Objeto | Caixa do .glb (X × Y × Z, m) | Escala | Tamanho final | Regra de uso |
|---|---|---|---|---|
| Pilar v6 | 3,4 × 6,25 × 3,4 | 0,70 | 2,4 × 4,4 × 2,4 | Cobertura de arena; não encosta no teto (pé-direito 5,4). Em corredor de 6 m, só em nicho |
| Coluna com corrente v3 | 5,56 × 3,55 × 2,46 | 0,90 | 5,0 × 3,2 × 2,2 | Peça de efeito, no máximo 1 por sala; conferir orientação antes |
| Braseiro | 1,46 × 1,76 × 1,46 | 0,75 | 1,1 × 1,3 × 1,1 | Altura de cintura (0,73 do herói); fonte de luz quente |
| Velas | 0,76 × 0,68 × 0,66 | 1,00 | 0,76 × 0,68 | Só em altar, nicho ou junto à base da estátua (oferenda); nunca soltas no chão |
| Estandarte v2 | 2,33 × 3,56 × 1,38 | 0,90 | 2,1 × 3,2 × 1,2 | Pendurado na parede, base a 1,6 m do chão |
| Estátua encapuzada | 2,38 × 3,22 × 2,16 | 0,80 | 1,9 × 2,6 × 1,7 | Em nicho; 1,45 × herói, impõe sem competir com o chefe |
| Entulho | 2,22 × 0,92 × 2,07 | 0,60 | 1,3 × 0,55 × 1,2 | Só em cantos de sala, colado à parede; nunca no tapete nem na passagem de 6 m |
| Tapete corredor | 3,58 × 0,14 × 6,38 | 0,65 | 2,3 × 4,1 | Largura = 2/5 do corredor, centralizado |
| Tapete grande | 8,0 × 0,25 × 16,39 | 1,00 | 8 × 16,4 | Só Átrio, Antecâmara e Arena |
| Piso (módulo) | 8 × 0,23 × 8 | 1,00 | 8 × 8 | Lajota de 1 m; junta e desgaste variam por módulo |

Regras de montagem: nenhum objeto repete com a mesma rotação lado a lado; variar escala em ±8% (menos o tapete); sempre deixar 3 m livres de cada lado do eixo do corredor para a esquiva (4 m em 0,35 s).

## 3. Paleta, luz e névoa

A régua de qualidade e de cor são o **estandarte v2, a coluna v3 e o pilar v6**: pedra fria azul-violeta, bordas claras quebradas, calor só no metal e na brasa.

| Papel | Valor | Observação |
|---|---|---|
| Pedra (sombra → luz) | `#0F0B14` → `#2A222F` → `#6A606E` | tokens `pedra_*`; nada abaixo de `#0F0B14`, nada de branco puro |
| Matiz da sombra | `#2C2A4A` (violeta-azul) | sombra muda de matiz, nunca só escurece |
| Ambiente | azul-noite `(0,20; 0,25; 0,38)`, energia 0,55 | já no PR 70 |
| Luar frio (direcional) | `(0,55; 0,65; 1,0)`, energia 0,28, de cima | dá forma às paredes; sombra suave |
| Luz-chave quente (fogo) | `#FFB86B` | só braseiros, velas e tochas; raio útil 6 a 8 m, para a sala ter poças de luz e zonas escuras |
| Neon mágico | dourado `#D9A441`/`#FCD58A` (runas, marcos); ciano eco `#4FE0D0` (portais, subsolo) | só onde a folha pede; núcleo emissivo, nunca superfície inteira |
| Perigo | `#E0301E` | só telégrafos e brasa do chefe |
| Névoa | cor `(0,09; 0,13; 0,24)`; volumétrica fina de 0,006 (andar 0) | sobe a cada andar (seção 4) |

Regras de luz: 1 foco quente por ~60 m² de sala; o herói nunca anda mais que 8 m sem luz quente à vista; o chefe e os telégrafos sempre mais claros que o piso ao redor; contraste de silhueta do herói com o piso é prioridade sobre atmosfera.

## 4. Estrutura do mapa em andares **[PROPOSTA]**

Ideia do Will (22/10/2026): descer por escadas; cada andar abaixo é mais difícil. Usa as três âncoras de escadaria do PR 70 e as salas do layout de `14`.

| Andar | Cota (piso) | Salas (`14`) | Entrada | Clima visual |
|---|---|---|---|---|
| A0 Superfície | 0 m | R00 Átrio, R01, R02 | porta da Cripta | azul-noite, névoa 0,006, 1 braseiro por sala |
| A1 Subsolo | −4 m | R03, R04, R05 (e o atalho A) | escada ao fim de R02/R03 | azul-violeta, névoa 0,008, pedra mais úmida, ciano nas poças |
| A2 Profundeza | −8 m | R06, R07, R08 Antecâmara | escada saindo de R05 | violeta escuro, névoa 0,011, runas douradas nas paredes, menos braseiros |
| A3 Arena | −12 m | R09 Arena do Guardião (40 × 40 m) | escada saindo de R08 | pedra quase preta, brasa vermelha de contorno, névoa 0,014 |

Escada: desnível de 4 m = 22 degraus de 0,18 m (~7 m de comprimento), largura de 4 m, corrimão de 0,9 m nos dois lados, patamar de 3 × 4 m no meio; nunca em combate (zona segura de 6 m antes e depois). Descer é sempre num só sentido na leitura da tela (para baixo e à esquerda em yaw 45°), para o jogador saber onde fica "mais fundo".

### Ligação com os dados (só proposta, sem mexer no core C)

Hoje `maps.csv` tem um mapa só: `map.act1.crypt`, `monsterLevel=3`, 7 encontros e o chefe. O nível dos inimigos escala pelos pares `base:porNível` de `enemies.csv` (ex.: Sentinela `life:60:8`), então **não precisa de linha nova em `enemies.csv`**: basta o `monsterLevel` de cada andar.

| Andar | `monsterLevel` | Encontros do andar (`encounters.csv`) | Observação |
|---|---|---|---|
| A0 | 3 | `patrol_a`, `hounds` | aprender a área |
| A1 | 5 | `patrol_b`, `firing_line`, `herald` | atiradores e telégrafo lento |
| A2 | 7 | `elite_shield`, `elite_swift` e `patrol_a`/`hounds` repetidos | elites e leitura de modificador |
| A3 | 9 | `guardian` (chefe) | nível do chefe sobe: rebalancear `crypt_guardian` com o balanceamento |

Como fica nos dados: ou 4 linhas em `maps.csv` (`map.act1.crypt.a0` … `.a3`, mesmo conteúdo, `idleAllowed` só no que o idle puder simular), ou um campo novo de andar (`floor`) em `maps.csv`; a segunda opção muda o esquema `maps.schema.json` e a API C. Recomendação: 4 linhas em `maps.csv` (não muda o core). Um pacote de dados e o designer de balanceamento decidem os números finais; este guia só fixa a ordem e a progressão +2 níveis por andar.


## 5. Regras de composição (revisão de 22/10/2026, após o teste do Will)

Cada objeto precisa de um motivo para estar onde está e de espaço livre. As regras abaixo são verificadas pelo `build_terreno.gd` (funções `_livre`, `_reservar`, `_zonas_proibidas`).

| Peça | Motivo (onde pode ficar) | Proibido |
|---|---|---|
| Piso e tapete | Piso em toda praça; tapete grande só em Átrio, Antecâmara e Arena; tapete de corredor no centro do trecho reto. Sempre sobre chão plano, 5 cm acima | Tapete sobre relevo; qualquer peça em cima do tapete |
| Braseiro | Em par ladeando o tapete (a 5,9 m do eixo), na parede alternado com estandarte, um por corredor e no contorno da Arena | Perto de outro braseiro (0,8 m de folga), em cima de tapete |
| Estandarte | Pendurado na parede, entre braseiros | Solto no meio da sala |
| Pilar | Pilastra na parede (alterna com braseiro); cobertura de combate só em Arena (anel de 8, raio 13 m), R05 (4), R06 e R07 (2 cada), sempre com chão aberto entre eles | Na frente de escada ou boca de corredor (5 m de folga), no eixo do tapete |
| Coluna com corrente | Uma por sala de peso: no Átrio encostada à parede lateral, deixando a boca da escada livre; na Arena atrás do chefe | No eixo de escada ou porta |
| Estátua | Em nicho na parede (Átrio, Antecâmara, nicho S01) | Em passagem |
| Velas | Três em volta da base da estátua ou do altar | Em qualquer outro lugar, especialmente soltas no chão |
| Entulho | Só em cantos de sala (parede cercando >58% do entorno), colado à parede | Em tapete, na passagem, perto de peça |
| Poça (decal v7) | Em chão plano, fora de tapete e de peças | Em parede, pilar ou boca de corredor |

Zonas proibidas para qualquer peça: raio de 5 m nas pontas dos corredores, 6 m nos topos e fundos de escada, 4 m no ponto inicial e 3 m na posição do chefe.

Chão: o relevo foi reduzido a 15% (ondulação de ~4 cm) para a textura planar do piso não esticar; só a rocha das paredes e as rampas das escadas têm inclinação.
Colisão: toda peça tem `StaticBody3D` na camada Mundo com forma simples tirada da caixa da malha (cilindro para pilar, braseiro e velas; caixa para coluna, estátua, entulho e estandarte); cada escada tem uma rampa lisa de colisão pela ponta dos degraus.
Luz de fogo: braseiro 2,0 de energia e 6 m de alcance, brilho de bacia 0,7 e 2,2 m, tremulação suave de 12%, chama aditiva a 0,65 e bloom com limiar 1,3 (antes 8,0 de energia e 1,6 de chama, que estourava a tela).
