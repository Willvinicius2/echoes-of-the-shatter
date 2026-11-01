# 33. Direção visual dos efeitos (VFX) das habilidades

Dono: thread "Dirigir o visual das habilidades". Vale para as quatro árvores do Arqueiro (docs 32_*) e para as próximas classes. Arte final passa pela revisora "Agente escolhedor de ferramentas" antes de ir ao Will. Números de balanceamento ficam nos CSV; aqui só ficam regras visuais e a tabela de como cada modificador aparece.

## 0. Problemas reais encontrados (feedback do Will + leitura do código)
1. **Flecha não sai do arco.** `player_2d.gd::lancar_flecha` nasce em `global_position + dir * arrow_spawn_dist` (36 px **a partir dos pés**, `player.csv`). O arco está na altura da mão e muda com a direção do sprite. Resultado: o tiro nasce no chão, ao lado do corpo.
2. **Aura corta o personagem.** As auras são sprites filhos soltos: fogo usa `show_behind_parent` e altura -20; veneno usa -30 sem ficar atrás; gelo e raio não têm regra. Quando a aura é desenhada por cima do arqueiro, ela "fatia" o sprite.
3. **Falta física.** Projéteis são linhas retas sem ancoragem, sem sombra, sem recuo e sem reação do alvo. Zonas e quedas (meteoro, chuva, bola de veneno) não têm sombra de aviso nem ponto de impacto lido no chão.
4. **Formatos de folha inconsistentes.** Os quadros variam (96, 128, 241, 256, 464 px) e as escalas se contradizem entre árvores; um mesmo elemento muda de tamanho entre efeitos.

## 1. Camadas (z) e ordem de desenho
Do fundo para a frente. Todo efeito escolhe uma só camada; nenhuma aura atravessa o personagem.

| Camada | z_index | O que vai aqui |
|---|---|---|
| C0 Decalque de chão | -1 (abaixo dos atores) | poças, brasas, cratera, rachadura de gelo, marca de queda, sombra de aviso |
| C1 Atrás do ator | 0 com `show_behind_parent = true` (ou y-sort do ator -1) | aura de Herald, brilho de fundo, rabo do projétil quando sobe |
| C2 Ator | y-sort normal | arqueiro, inimigos |
| C3 Em cima do ator | z 3 | overlay de status no inimigo (choque, frio, queimadura, veneno), faíscas |
| C4 Projétil e impacto | z 4 | flecha, raio, explosão no alvo |
| C5 Céu | z 5 | colunas que descem do alto (raio, meteoro), sombra de queda não, só o corpo caindo |

Regras:
- **Aura é C1, nunca C3.** Sempre atrás do arqueiro, centrada no tronco (≈ -34 px dos pés), diâmetro entre 1,1× e 1,4× a altura do sprite, alfa máximo 0,45. Se a leitura exigir algo à frente, vira **partículas pequenas orbitando** (≤ 8 px), nunca um quadro grande por cima.
- Nada em C3/C4 cobre o rosto do arqueiro por mais de 1 quadro (corte do disparo).
- Decalques (C0) ficam sob a sombra dos atores; o inimigo pisando numa poça não some sob ela.

## 2. Origem e saída do tiro (física coerente)
- Cada direção do sprite do arqueiro (5 direções + flip, doc 25) ganha um **ponto de boca do arco** `muzzle[dir]` em px a partir dos pés, medido na pose de disparo (vem do arquivo de ancoragem, não do código). O tiro nasce **ali**, nunca em `pés + 36`.
- Sequência de disparo (para o arqueiro e para o efeito): 1) puxar (carga, 80–120 ms, brilho do elemento cresce na ponta da flecha); 2) soltar: **flash de boca** 2 quadros no `muzzle` + recuo de 2–3 px do sprite; 3) voo.
- Projétil herda a direção e a **rotação** da mira; o rabo (rastro) cresce com a velocidade. Sombra no chão sob o projétil só para projéteis que sobem (parábola): sombra segue o chão, corpo sobe.
- Projétil em arco (bola de veneno, meteoro, flecha para o alto): sobe com ease-out, fica no pico ≤ 1 quadro, cai com ease-in; **a sombra de aviso cresce no ponto de impacto desde o disparo** (círculo escuro com borda do elemento, 0,4 s antes de cair no mínimo).
- Impacto: 1º quadro é o mais brilhante; o alvo reage no mesmo quadro (flash branco 60 ms, empurrão ≤ 4 px na direção do golpe). Sem reação do alvo, o golpe "não aconteceu".
- Zonas: nascem com anel de entrada (0,15 s), pulsam no ritmo do dano (um pulso visual por tick), saem com fade de 0,3 s. Nunca somem de uma vez.

## 3. Escala (referência: arqueiro = 128 px de quadro, ≈ 72 px de corpo)
| Elemento | Tamanho em px (jogo) | Observação |
|---|---|---|
| Projétil básico (flecha elemental) | 30–40 de comprimento, 6–10 de espessura | base do projeto; modificadores partem daqui |
| Impacto | 56–80 | ≈ 1× o corpo do inimigo pequeno |
| Overlay de status no inimigo | 0,9× a largura do inimigo | cola no inimigo, segue o y-sort |
| Aura de Herald | 80–100 | regra da seção 1 |
| Zona/explosão (usa `raio` do CSV) | **diâmetro = 2 × raio do CSV**, exato | o desenho **tem de bater com a área de dano**; cada árvore escala o quadro para isso por código |
| Coluna/queda | 1,2× o raio da área, altura até o topo da tela | |

Padrão de arquivo de folha: quadros **quadrados**, potência de 2 (64, 128 ou 256), um quadro por célula, fundo transparente, manifesto com `quadros`, `fps`, `loop`, `ancora` (centro, base ou ponta) e `escala_ref`. Folhas existentes que fogem disso são normalizadas na fase de polimento por script (sem redesenhar).

## 4. Leitura em hordas (500+ inimigos em tela)
- **Hierarquia de brilho**: 1) perigo ao jogador (telégrafos inimigos, vermelho/laranja forte) fica sempre acima; 2) ult e Herald do jogador; 3) ativas; 4) tiro básico; 5) status. Um efeito de menor nível nunca tem mais brilho que o de maior.
- **Orçamento**: no máximo 24 efeitos animados ao mesmo tempo; passou disso, o mais antigo e o mais distante do jogador encolhe para só o 1º e o último quadro. Status em inimigo fora da tela não anima. Partículas por efeito ≤ 24.
- **Redução em massa**: com ≥ 12 inimigos com o mesmo status, o overlay vira **um pontinho colorido no pé** (4 px) em vez do quadro completo, e só o inimigo mais próximo mostra o overlay cheio. A cor continua dizendo o status.
- **Cor identifica o elemento, forma identifica a habilidade**: raio = azul-branco com ponta amarela e linhas quebradas; veneno = verde ácido, formas redondas e bolhas; gelo = azul claro, formas angulares e cristais; fogo = laranja e vermelho com núcleo amarelo, formas ondulantes. Duas árvores nunca dividem tom principal. Contorno escuro de 1–2 px em tudo (doc 26) para destacar do capim.
- **Contraste com o cenário**: o piso é verde-seco/laje cinza; evite verde-oliva no veneno (some no capim): use verde ácido saturado com núcleo claro. Sempre um miolo claro + borda escura.
- **Telégrafo antes do dano grande**: qualquer coisa que machuque em área mostra o anel/sombra antes, nos efeitos do jogador também (ajuda a ler a própria zona entre hordas).
- Números de dano: efeitos nunca cobrem os números de dano (z maior que todos).

## 5. Como cada modificador aparece
Princípio: **o jogador reconhece o modificador sem ler texto**. Cada modificador muda uma propriedade visual específica e a mesma regra vale para todas as árvores. Eles se somam; quando muitos se acumulam, vale o limite do final da seção.

| Modificador (fonte: passiva/gema) | O que muda no visual | Regra |
|---|---|---|
| **Mais projéteis** (`qtd`, múltiplos, leque) | Mais cópias na saída, com leve espalhamento angular e atraso de 30–50 ms entre elas, saindo **do mesmo `muzzle`** | Até 5: todos visíveis. De 6 a 12: o projétil central é cheio e os laterais com 70% de alfa. Acima de 12: vira "chuva" (cortina de rastro) com 8 cópias visíveis |
| **Perfuração** (pierce) | Ponta alongada e afiada, rastro mais reto e longo; impacto "atravessa" (faísca sai do outro lado) | O projétil não some no primeiro alvo |
| **Ricochete / encadeamento** | Linha de arco visível entre alvos (ligação elétrica, fio de gelo etc.) com número de saltos legível pelo brilho decrescente | Cada salto 15% mais fraco em alfa e espessura |
| **Área maior** (`raio`) | O desenho **escala exatamente** com o raio (seção 3); anel de borda mais grosso; mais partículas na borda, não no centro | Nunca aumentar só o brilho para "parecer" maior |
| **Duração maior** | Mais pulsos visíveis; fade final começa mais tarde; sem mudar tamanho | O último segundo pisca/afina para avisar o fim |
| **Velocidade do projétil** | Rastro mais longo e fino, esticamento do corpo (squash and stretch até 1,3×); flash de boca menor | Lento: corpo gordo, rastro curto, brilho forte |
| **Tamanho do projétil** | Escala do corpo e do impacto juntos; espessura sobe antes do comprimento | Máximo 2× o base, depois só ganha halo |
| **Dano maior** (por nível/gema) | **Intensidade, não tamanho**: núcleo mais branco, halo mais largo, mais faíscas, impacto com 1 quadro extra e *screen shake* leve; **cor mais saturada e quente** | Nível 1 = cor base; nível 2 = núcleo branco; nível 3 = núcleo branco + halo + partículas extras |
| **Crítico** | Impacto com anel branco, número de dano maior, sem mudar o projétil | Só no instante do acerto |
| **Elemento convertido** (gema troca elemento) | Muda **paleta e forma de ponta/rastro**, mantém a silhueta da habilidade | Reaproveita a mesma folha pintada com *recolor* por shader quando a forma serve; folha nova só se a forma não serve |
| **Cadência maior** | Flash de boca menor e mais curto, rastro mais fino; **nunca** aumentar o brilho por tiro | Evita fogo de artifício em hordas |
| **Status aplicado** | Overlay do status no inimigo (C3) com a cor do elemento; ver redução em massa (seção 4) | |
| **Herald equipado** | Aura de C1 (seção 1); ao disparar o gatilho, o efeito sai do inimigo morto (C4), nunca da aura | A aura acende por 0,3 s quando o gatilho dispara |
| **Sinergia cruzada** (Raio×Gelo, Veneno×Fogo) | Mistura as duas paletas só no ponto de contato (faísca azul numa explosão de gelo; nuvem verde que vira chama), cada elemento mantém sua forma | |

**Limite de acúmulo**: um efeito nunca ocupa mais de 3× a área base, nunca passa de 24 partículas, e o brilho total dele não passa de 1,5× o base. O que exceder vira cor mais saturada, não mais coisas na tela.

## 6. Cores base por elemento (tokens, ajustáveis pela revisora)
| Elemento | Miolo | Corpo | Borda/contorno |
|---|---|---|---|
| Raio | #F4FBFF | #5FA8FF | #14284F |
| Veneno | #E6FF8A | #5CD12B | #123D1A |
| Gelo | #F0FBFF | #7FD3F2 | #123A5C |
| Fogo | #FFE27A | #FF7A1F | #5A1408 |
Saturação sobe e o miolo ganha branco conforme o nível do dano (seção 5).

## 7. Passo a passo para as threads de arte
1. Ler este doc e o `32_<elemento>.md`. Não mexer em arquivos de outras árvores.
2. Lista de entrega por habilidade: (a) projétil + rastro, (b) flash de boca, (c) impacto, (d) efeito próprio, (e) overlay de status, (f) variações de intensidade nível 1/2/3 (recolor por shader quando possível), (g) manifesto com `ancora`, `fps`, `loop`.
3. Conferir na tela: arqueiro em 3 direções, 1 inimigo, 20 inimigos e 100 inimigos. Capturas antes/depois no PR.
4. Revisora confere: camada correta, origem no `muzzle`, tamanho = área do CSV, leitura na horda, mesma régua de pintura do estandarte v2. Só então o Will vê.

## 8. Pedidos técnicos (donos: integradora e thread do Arqueiro)
1. **Ponto de boca por direção** (`muzzle[dir]`) e uso em `lancar_flecha` no lugar de `arrow_spawn_dist` dos pés. Dono: thread "Criar habilidades e animações do arqueiro" (medir na folha do arqueiro, gravar em CSV).
2. **Auras**: um helper único `aura_c1(jogador, folha, escala)` que aplica a seção 1 (atrás do ator, alfa, centro no tronco), e as quatro árvores o usam no lugar de cada `aura()` própria.
3. **Sombra de aviso** para projéteis em arco e quedas (helper compartilhado).
4. **Recolor por shader** (paleta por elemento e nível) para variações de intensidade e elemento convertido, evitando uma folha nova por gema.
5. **Orçamento de efeitos** (seção 4): contador global de efeitos ativos e o modo "pontinho" do status em massa.
6. Normalizar as folhas existentes (potência de 2, manifesto) por script.
7. Quando a árvore de passivas/gemas definir os modificadores reais, esta tabela (seção 5) é conferida contra a lista final; o que não tiver linha aqui ganha uma.
