# 03 — Design system, especificação de arte 3D e interface

Projeto: **Echoes of the Shatter** · Responsável: Art Director · reescrito em 16/10/2026
Fontes: `docs/08_decisoes_visual_3d.md` (decisões fechadas), `docs/arte/referencias-geracao/` (folhas aprovadas 01 a 24), `docs/00_plano_existente.md` (seções 5, 6, 7, 9 e 10) e `docs/01_plano_execucao.md`.
Tokens em formato de máquina: `docs/03_design_tokens.json` (este documento manda; se os dois divergirem, corrigir o JSON).
Motor: **Unreal Engine 5.8**, Forward Shading com MSAA, interface em **UMG** (widgets em C++ + Widget Blueprint).

> Nota de substituição (16/10/2026): este documento substitui a versão de 15/10/2026, que era pixel art com Paper2D, sprites, viewport interno de 960 × 540, filtro nearest, escala inteira, fonte pixel e paleta ocre. Nada disso vale mais. A seção 9 lista as chaves de token renomeadas ou removidas.

> Convenção de medidas da UI: o layout é desenhado no espaço de referência **1920 × 1080** (escala de DPI 1,0 em 1080 de lado menor) e roda em resolução nativa com a curva de DPI padrão do UE (seção 3.9). Posições de tela no formato `(x, y, l, a)` = canto superior esquerdo, largura, altura, sempre com a **âncora** indicada; toda posição é um deslocamento a partir da âncora, nunca coordenada absoluta. Arte 3D: 1 uu = 1 cm.

> Cores medidas: os hex deste documento foram medidos nas folhas aprovadas (mediana de regiões; núcleo = percentil 93 de brilho, meio = percentil 45–75, borda = percentil 8–30) e ajustados para contraste de texto. Onde o valor medido ficou fosco por sombra (névoas), o token traz a cor corrigida e a medida bruta.

---

## 1. Princípios visuais

1. **Base de pedra escura, acento quente só onde importa.** A UI e o cenário vivem em pedra violeta-escura (`#161117` a `#2A222F`); ouro (`#D9A441`) fica na moldura, carmesim/lava no que é vida e ação principal, e o resto da cor pertence à magia, ao loot e às névoas das áreas. Se tudo brilha, nada é lido.
2. **Pintado à mão, não fotográfico.** Formas grossas e chanfradas, luz e sombra pintadas na textura, sombra que muda de matiz (violeta) em vez de só escurecer, sem preto puro. A UI repete a linguagem: pedra com molduras orgânicas espinhosas e preenchimento "lava" nas barras (folhas 10, 11 e 12).
3. **Ameaça antes do espetáculo.** Telegraph, vida baixa e elite são entendidos pela forma e pela cor antes do texto, em menos de 0,5 s (telegraph de 0,7–1,2 s, sempre com forma no chão e som). Efeitos do jogador são finos e translúcidos; ameaças são opacas e quentes (seção 3.8).
4. **Recompensa, não castigo.** A interface do idle mostra bônus e faixas de previsão, nunca números negativos ("+200% XP" com o Fervor, nunca "-65% XP"). Vermelho é perigo real, não "você ganhou menos".
5. **Ornamento na moldura, clareza no conteúdo.** Molduras de pedra com ornamento nos cantos; dentro delas, texto claro sobre fundo liso, desenhado para o português (≈ 30% mais longo que o inglês).
6. **Legível no Steam Deck.** Nenhum texto abaixo de 12 px efetivos em 1280 × 800; nenhuma informação só por cor.

---

## 2. Tokens

### 2.1 Cores base e superfícies

**Paleta base** (pedra medida nas folhas 10 e 12; ouro e carmesim das molduras e do preenchimento de vida):

| Token | Hex | Papel |
|---|---|---|
| `base.pedra_noite` | `#0F0B14` | Fundo do jogo, contornos de texto, vão da moldura |
| `base.pedra_escura` | `#161117` | Fundo de menu; sombra da pedra da moldura |
| `base.pedra_media` | `#2A222F` | Corpo da pedra da moldura, cartões |
| `base.pedra_clara` | `#6A606E` | Aresta iluminada da pedra, borda padrão |
| `base.dourado` | `#D9A441` | Filete e cantos das molduras, selos |
| `base.dourado_claro` | `#FCD58A` | Brilho do dourado, foco, títulos |
| `base.carmesim` | `#B82A1E` | Botão primário, preenchimento "lava", pluma do Guerreiro |
| `base.perigo` | `#E0301E` | Telegraph, avisos de risco (matiz 0–15°, reservado a ameaça) |
| `base.pergaminho` | `#F0E6D6` | Texto primário |

**Superfícies e bordas:**

| Token | Hex | Uso |
|---|---|---|
| `surface.bg_deep` | `#0F0B14` | Fundo de modal, sombra, vão |
| `surface.bg_base` | `#161117` | Fundo de telas de menu |
| `surface.panel` | `#1F1922` | Fundo de painel |
| `surface.panel_raised` | `#2A222F` | Cartão dentro de painel, linha selecionada, botão secundário |
| `surface.panel_hover` | `#3A2F42` | Hover de linha ou botão secundário |
| `surface.slot_inset` | `#120E16` | Fundo de slot (afundado) |
| `surface.lava_fill_dark` | `#5A1410` | Fundo escuro do preenchimento lava das barras |
| `surface.scrim` | `#0F0B14` a 78% | Escurecer o jogo atrás de modal ou pausa |
| `border.subtle` | `#4A3F52` | Divisórias, borda de slot vazio |
| `border.default` | `#6A606E` | Borda de painel simples, slot com item |
| `border.gold` | `#D9A441` | Moldura ornamentada |
| `border.gold_highlight` / `border.focus` | `#FCD58A` | Brilho de moldura, **anel de foco**, hover de slot |

**Texto** (contraste medido sobre `surface.panel` `#1F1922`):

| Token | Hex | Contraste | Uso |
|---|---|---|---|
| `text.primary` | `#F0E6D6` | 13,9:1 | Corpo, valores |
| `text.secondary` | `#BFB2A6` | 8,3:1 | Rótulos, tipo do item |
| `text.muted` | `#9A8D97` | 5,4:1 | Dicas, sabor, versão |
| `text.disabled` | `#6B6170` | 2,9:1 | Só em controle desabilitado, sempre com cadeado ou motivo |
| `text.title` | `#FCD58A` | 12,3:1 | Títulos de tela e faixa de área |
| `text.on_gold` | `#1A1209` | 8,2:1 | Texto sobre dourado (selo de nível) |

**Ações:** `action.primary` `#B82A1E` (texto `#F0E6D6` sobre ele: 5,0:1), `_hover` `#C22E22`, `_pressed` `#7C1A14` (8,4:1). `action.secondary` / `_hover` / `_pressed`: `#2A222F` / `#3A2F42` / `#161117`, borda `border.default`.

### 2.2 Vida, recursos e semânticas de jogo

| Token | Hex (claro / escuro) | Uso |
|---|---|---|
| `semantic.life` | `#D8381F` / `#5A1410`, brilho `#FF7A52` | Orbe e barra de vida (lava vermelha, medida no orbe da folha 10: `#CA2C0C`–`#E7350D`) |
| `semantic.impeto` | `#F58A25` / `#6E3410` | Recurso do Guerreiro (Ímpeto; barra âmbar da folha 10) |
| `semantic.foco` | `#7FD04A` / `#2C5A1E` | Recurso do Arqueiro (Foco) |
| `semantic.mana` | `#4A9CF0` / `#1E3F7A` | Recurso do Mago (Mana) |
| `semantic.xp` | `#B48CF0` / `#3E2E66` | Barra de XP |
| `semantic.vigor` | `#9CBF6A` / `#3F5226` | Barra de Vigor da patrulha |
| `semantic.fervor` | `#FCD58A` | Ícone e texto "+200% XP" do Fervor |
| `semantic.eco` / `marco_charge` | `#4FE0D0` | Fragmentos de Eco e Cargas do Marco ("cor da memória") |
| `semantic.danger` | `#E0301E` (forma) · `#FF7B66` (texto, 6,8:1) | Perigo, erro, contrapartida de Único |
| `semantic.success` | `#8FD06A` | Sucesso, comparação melhor, cura |
| `semantic.warning` | `#F2B23A` | Aviso não bloqueante |
| `semantic.info` | `#8FD6EA` | Dica do Tico, informação neutra |

Vida (vermelho) e Ímpeto (âmbar) ficam próximos; por isso o orbe de vida é sempre o da esquerda, o de recurso o da direita, e cada um tem ícone-gema na moldura (gota para vida; losango da classe para recurso) e texto no hover. Regra de classe em `color.class_gem`: Guerreiro `#E0301E`, Arqueiro `#5FD04A`, Mago `#4A9CF0`, item `#F2B23A` (as gemas das folhas 11).

### 2.3 Raridades

"Normal" = Comum no plano. Contraste sobre `#1F1922`.

| Raridade | Token | Hex | Contraste | Feixe no chão |
|---|---|---|---|---|
| Comum (Normal) | `rarity.normal` | `#D9D2C8` | 11,5:1 | Nenhum |
| Mágico | `rarity.magic` | `#6FA8FF` | 7,1:1 | Brilho no item, raio 20 cm |
| Raro | `rarity.rare` | `#FFD24A` | 11,9:1 | Coluna de raio 15 cm × 250 cm |
| Único | `rarity.unique` | `#FF8A2E` | 7,3:1 | Coluna de raio 25 cm × 500 cm, pulso de 800 ms + som próprio |

Raridade **nunca** é só cor: o tooltip escreve a raridade ("Raro · Espada Longa"), a moldura do slot muda de forma (Mágico: cantos simples; Raro: cantos duplos; Único: cantos espinhosos com filete dourado) e o rótulo no chão usa o mesmo padrão. Raro e Único são próximos em matiz (amarelo e laranja); a forma e o som os separam.

**Texto de item e dano:** afixo `#8FB8FF`; efeito de Único `#FF8A2E`; contrapartida de Único `#FF7B66` com marcador `▼`; requisito não cumprido `#FF7B66`; comparação melhor `#8FD06A` `▲` / pior `#FF7B66` `▼`.
Dano: físico `#E8E0D4`, fogo `#FF9A2E`, gelo `#7FD6FF`, raio `#A9C4FF`, ácido `#A6E04A`, sombra `#C07BFF`, crítico `#FFE066`, recebido pelo jogador `#FF7B66`, cura `#8FD06A`, bloqueado `#9A8D97`.

### 2.4 Elementos (núcleo, meio, borda)

Medidos na folha 09 e nos ícones da 11. **Jogador** (`color.element.*`), usado em habilidades do jogador: núcleo quase branco, meio saturado, borda escura e fria.

| Elemento | Núcleo | Meio | Borda | Origem na referência |
|---|---|---|---|---|
| Fogo | `#FFE9B0` | `#FF9A2E` | `#B8420F` | Golpe e investida do Guerreiro; bola de fogo do Mago (na folha aprovada é vermelho-laranja; âmbar é **proposta pendente de aprovação do dono**, a arte aprovada não muda) |
| Gelo | `#D8F6FF` | `#4FA8E8` | `#2B4F92` | Lança e esfera de gelo do Mago |
| Raio | `#F2F6FF` | `#7FA8FF` | `#3A4FB8` | Corrente do Mago |
| Ácido | `#E6FF8A` | `#8FD43A` | `#3E7A1E` | Flechas e rede do Arqueiro (verde medido `#BFDC62` núcleo) |
| Sombra | `#F0D0FF` | `#9A4BD6` | `#3E1766` | Corrompidos e Mago arcano; roxo medido `#503871`–`#8C3656` nas folhas 05 e 09 |
| Ouro sagrado | `#FFF2A8` | `#F2B23A` | `#8F5A12` | Elite, loot, impactos de pedra e ouro; feixe medido `#FEF591`/`#C0843C` |
| Físico | `#FFFFFF` | `#E8E0D4` | `#8A7F78` | Faíscas e poeira |

**Ameaça** (`color.threat.*`), usado em ataques e projéteis inimigos: núcleo menos branco, meio mais escuro e saturado, borda quase preta (para se separar do cenário), e sempre a **faixa vermelha** `#E0301E`.

| Elemento | Núcleo | Meio | Borda |
|---|---|---|---|
| Fogo | `#FF7A45` | `#E0301E` | `#4A0B0E` |
| Gelo | `#9FE6FF` | `#3F86E8` | `#12214F` |
| Raio | `#C9D8FF` | `#5A7CF0` | `#161F5C` |
| Ácido | `#C8F060` | `#6EB82A` | `#1C3A12` |
| Sombra | `#E58AD8` | `#8C3A9E` | `#2A0F3A` |
| Físico | `#FFD2A0` | `#E0301E` | `#3A0A0C` |

**Regra de matiz:** a faixa vermelha (matiz 0–15°) é reservada a ameaça. Fogo do jogador fica no âmbar (28–50°). O Guerreiro e o Mago usam âmbar e dourado, nunca vermelho puro, nos efeitos.

### 2.5 Perigo e telegraph

| Token | Valor | Uso |
|---|---|---|
| `telegraph.fill` | `#D8432F` a 40% | Preenchimento da zona no chão (início) |
| `telegraph.fill_final` | `#E0301E` a 65% | Preenchimento nos últimos 200 ms |
| `telegraph.edge` | `#FF6A4A` | Borda, largura 12 cm |
| `telegraph.edge_hot` | `#FFB27A` | Linha interna quente da borda, runas |
| `telegraph.outline_dark` | `#3A0A0C` | Contorno escuro externo de 8 cm |
| `telegraph.final_flash` | `#FFFFFF` | Pisca nos últimos 100 ms |
| `telegraph.alt_colorblind_edge` | `#FFE066` | Opção "Daltonismo": borda amarela com listras (período 40 cm) |

Medido na folha 09: núcleo do círculo `#EF5A43`, meio `#703338` sobre piso escuro. **Variante `dark_outline`:** nas áreas de névoa vermelha ou laranja (Pátio dos Marcos, Ponte do Sino, Trilha de Cinza, Salão do Martelo) o telegraph ganha contorno escuro de 8 cm, alpha de preenchimento +0,15 e a linha `edge_hot` mais larga (16 cm), para não se perder no fundo.

### 2.6 Cor-assinatura da névoa por área

A cor do Exponential Height Fog de cada área é a sua assinatura. Valores em `color.fog.*` (cor corrigida, bruma medida, acento de luz, densidade de partida):

| Área | Fog | Medido | Acento | Descrição | Folha |
|---|---|---|---|---|---|
| Estrada das Lanternas | `#5B4B8E` | `#4D497B` | `#FFB347` | Crepúsculo violeta, luz de lanterna âmbar | 13 |
| Cripta Partida | `#463C78` | `#383252` | `#3FE0D0` | Violeta profundo, portal ciano e ouro | 07 |
| Armazém de Cinzas | `#5A4862` | `#624D51` | `#FF9A3C` | Malva empoeirado, feixes azulados, tochas | 14 |
| Pedreira dos Ecos | `#2A7F8E` | `#276673` | `#36D6E8` | Abismo ciano | 08 |
| Pátio dos Marcos | `#8A2E4C` | `#3B3E47` | `#2A8088` | Carmesim com borda azul-esverdeada | 15 |
| Túneis do Voto | `#1F7C78` | `#533322` | `#36D6C0` | Teal sobre rocha marrom e tochas | 16 |
| Ponte do Sino | `#B83454` | `#54222A` | `#FFB347` | Rosa-carmesim, sinos de bronze | 08 |
| Mirante Partido | `#A9A3D6` | `#35313F` | `#FFD27A` | Nuvem lilás clara, único cenário claro | 17 |
| Endgame: Ossário do Marco | `#1E5560` | `#173337` | `#3FE0B8` | Verde-azulado escuro, chama fantasma, rachaduras roxas | 18 |
| Endgame: Trilha de Cinza | `#8A3524` | `#572E23` | `#FF6A2A` | Brasa vermelha, floresta queimada | 19 |
| Endgame: Salão do Martelo | `#9A3E1C` | `#4B2926` | `#FF7A1E` | Lava laranja, forja | 20 |

Regras: a névoa cobre distância e fundo, nunca o jogador nem o telegraph (Inscattering baixo a menos de 15 m da câmera); o Mirante é o teto de luminosidade do jogo, nenhum outro cenário passa de luma média 0,45; cada área mantém **um** acento quente (luz de tocha, lava ou lanterna) para o jogador se orientar.

### 2.7 Tipografia

Fontes escolhidas (Google Fonts, todas **OFL 1.1**, uso comercial livre, com acentos do português; **nunca** a fonte do Spell Brigade):

| Papel | Fonte | Pesos | Alternativa |
|---|---|---|---|
| Corpo, rótulos, micro | **Source Sans 3** | 400, 600, 700 | Noto Sans |
| Títulos e faixa de área | **Cinzel** | 600, 700 | Cormorant SC |
| Números de dano e de moeda | **Lilita One** | 400 | Source Sans 3 Bold |

Por que: Source Sans 3 tem Latin estendido completo, algarismos tabulares e abre bem em 12–14 px efetivos no Steam Deck. Cinzel dá a serifa gravada em pedra da faixa de área. Lilita One é gorda e legível em movimento, boa para dano.

**Teste obrigatório no dia 1** (Frontend + Narrative): renderizar a frase-teste em todos os estilos, a 1080p e a 800p (escala 0,74), e anexar a captura ao `docs/10_qa.md`. Se faltar glifo, trocar pela alternativa antes de construir tela.
Frase-teste: `Ação, coração e põe; Ñandú: ¿Qué pasó? ¡Olé! ÁÉÍÓÚ ÂÊÔ ÃÕ Çç àü ºª «» – — … 1.234,56 × ÷ % ▲▼`
`▲▼` podem faltar: usar ícones `T_Icon_UI_arrow_up_32` e `_down_32`. Cinzel é pensada para maiúsculas e versaletes; confirmar que as minúsculas acentuadas aparecem bem em 32 px.

**Escala tipográfica** (tamanho no espaço de 1080p; efetivo = × escala de DPI):

| Estilo | Fonte | px | pt UMG | Entrelinha | Efetivo no Deck (0,74) | Uso |
|---|---|---|---|---|---|---|
| `micro` | Source Sans 3 SemiBold | 16 | 12 | 20 | 11,8 | Tecla no slot, contador de pilha, versão. Mínimo permitido |
| `body` | Source Sans 3 | 20 | 15 | 26 | 14,8 | Texto padrão, botões, tooltip, listas |
| `body_bold` | Source Sans 3 Bold | 20 | 15 | 26 | 14,8 | Nome de item, cabeçalho de seção |
| `title` | Cinzel Bold | 32 | 24 | 40 | 23,7 | Título de tela, faixa de área |
| `display` | Cinzel Bold | 64 | 48 | 72 | 47,4 | Nome de chefe ao entrar, "Você caiu" |
| `damage` | Lilita One | 28 | 21 | — | 20,7 | Número de dano normal |
| `damage_crit` | Lilita One | 44 | 33 | — | 32,6 | Número de dano crítico |

Conversão: pt = px × 0,75 (Slate). Em 800p o `micro` fica em 11,8 px efetivos: é o piso; nenhum estilo novo abaixo disso.

**Largura média para orçamento de texto:** ≈ 9,5 px por caractere em `body` (≈ 10,5 em `body_bold`; ≈ 7,5 em `micro`). Todo campo traz o número máximo de caracteres por linha derivado disso. O Frontend mede com a fonte final e atualiza a tabela se a média passar de 10 px.

**Regras de texto:** itálico só em texto de sabor (Source Sans 3 Italic); sem caixa-alta automática; números em pt-BR (`1.234`, `1,20`, `8–12 mil`); quebra por palavra; truncar com `…` só em nomes de save e áreas, nunca em afixos. Texto grande (acessibilidade): corpo +25% (`body` 25 px; tooltip 576 de largura; painéis de texto com `ScrollBox`).

### 2.8 Espaçamento

Escala em unidades de 1080p (grade base de 8; 4 só para ajuste fino):

| Token | Valor | Uso típico |
|---|---|---|
| `s0` | 0 | — |
| `s1` | 4 | Espaço entre slots do inventário, ícone ↔ borda do slot |
| `s2` | 8 | Espaço entre slots da barra, padding interno de chip |
| `s3` | 16 | Padding de botão, gap entre grupos |
| `s4` | 24 | Padding de tooltip, cursor ↔ tooltip |
| `s5` | 32 | Padding de painel, margem segura |
| `s6` | 48 | Separação entre seções |
| `s7` | 64 | Margem de modal |
| `s8` | 96 | Respiro de menu principal |

Margem segura: 32 em todos os lados (nada interativo fora dela).

### 2.9 Tamanhos-padrão

| Token | Valor | Token | Valor |
|---|---|---|---|
| `icon_sm` | 32 (moeda, buff, tecla, inline) | `button_h` | 56 (mín. largura 192) |
| `icon_md` | 48 (status, abas, regras de IA) | `row_h` | 56 (lista); 80 (linha de regra) |
| `icon_lg` | 80 (itens e habilidades dentro do slot) | `tab_h` | 48 |
| `item_slot` / `skill_slot` | 88 × 88 | `orb` | 144 × 144 |
| `potion_slot` | 64 × 88 | `portrait` | 96 × 96 |
| `dodge_slot` | 72 × 88 | `minimap` | 240 × 240, redondo |
| `bar_xp_h` / `bar_thin_h` / `bar_boss_h` | 8 / 16 / 28 | `tooltip_max_w` | 480 (576 com texto grande) |
| `toast` | 480 × 64 | `scrollbar_w` | 12 |

Alvo de toque e de gamepad no Deck: nenhum controle interativo abaixo de 48 de altura.

### 2.10 Molduras de pedra e 9-slice

Molduras de pedra escura com arestas orgânicas e espinhos nos cantos (folhas 10, 11 e 12). Cada moldura é um 9-slice (`Draw As = Box`) exportado em PNG com alpha, 2× de resolução do uso (retina para 4K). A margem do Box no UMG é fração da textura (margem ÷ tamanho).

| Peça | Textura | Canto | Margem UMG | Visual |
|---|---|---|---|---|
| `nine_panel_ornate` | 128 × 128 | 48 | 0,375 | Pedra `#2A222F` com aresta `#6A606E`, filete dourado `#D9A441` de 3 px interno, espinhos e cristais nos cantos |
| `nine_panel_plain` | 64 × 64 | 20 | 0,3125 | Pedra lisa, aresta `#6A606E` de 2 px, canto chanfrado |
| `nine_button` | 64 × 64 | 20 | 0,3125 | Placa de pedra com luz no topo e sombra embaixo |
| `nine_slot` | 96 × 96 | 16 | 0,167 | Moldura quadrada chanfrada, vão `#120E16`; 4 variantes de canto por raridade; gema inferior central |
| `nine_tooltip` | 64 × 64 | 20 | 0,3125 | Fundo `#161117` a 95%, borda na cor da raridade |
| `nine_bar_frame` | 64 × 64 | 16 | 0,25 | Moldura de barra com pontas espinhosas (barra de chefe tem cabeça de demônio central, imagem à parte) |
| `nine_toast` | 64 × 64 | 20 | 0,3125 | Faixa de pedra com filete na cor semântica à esquerda (4 px) |

**Regra do 9-slice:** o Slate estica bordas e centro; as bordas devem ser uniformes no eixo do estiramento e o ornamento fica **só nos cantos**. Ornamento repetido ao longo da borda (correntes, espinhos) é peça separada com `Tiling`.
**Orbes e barras:** orbe é um vidro esférico 144 × 144 com moldura de pedra e caveira/cristais; preenchimento "lava" animado por material (ver 5.4), não por textura fixa. Barras têm preenchimento lava com gradiente de `life` para `life_dark` e brilho `life_highlight` no topo.

### 2.11 Ícones

Ícones de habilidade e de item são pinturas quadradas com cena (herói em ação, objeto) como na folha 11; a moldura e a gema são **overlay do widget**, não fazem parte da imagem.

| Exportação | Onde | Regras |
|---|---|---|
| **128 × 128** PNG RGBA | Itens, habilidades, sigilos, livros (exibidos a 80 no slot de 88; 96 de moldura no tooltip) | Fundo escuro quase preto-violeta `#161117`, cantos até a borda; centro de interesse a ≤ 60% do quadro; sem preto puro; luz do alto-esquerda; legível reduzido a 48 |
| **64 × 64** | Abas, objetivo da expedição, condições de regra, status, buffs, moedas | Desenhados a parte, não reduzidos do 128; silhueta clara sem fundo |
| **32 × 32** | Glifos de tecla, ícones inline, setas, alerta | 2–4 cores, contorno escuro `#0F0B14` de 2 px |

**Moldura por categoria** (overlay `nine_slot`): pedra `#2A222F` com aresta `#6A606E` em todos; a **gema** do losango inferior segue `color.class_gem` (habilidade: classe; item: `#F2B23A`); a **raridade** do item altera o canto: Normal chanfrado liso, Mágico canto com filete azul `#6FA8FF`, Raro canto duplo dourado `#FFD24A`, Único canto espinhoso laranja `#FF8A2E` com brilho. **Elemento** da habilidade aparece como filete interno de 3 px na cor `element.*.mid` e como emblema de 32 px no tooltip.

Glifos de entrada: `T_Icon_Key_<tecla>_32`, `T_Icon_MouseLeft_32`, `T_Icon_MouseRight_32`, mais glifos de gamepad (Steam Deck) gerados do mapeamento atual.
Nomes: `T_Icon_<categoria>_<id>_<tam>` (ex.: `T_Icon_Skill_warrior_iron_cut_128`), usando o ID estável de conteúdo.

### 2.12 Sombras e contornos de interface

- **Texto de UI sobre painel:** sombra `#0F0B14` a 90%, deslocamento (0, 2), sem blur.
- **Texto no mundo** (dano, nome de item no chão, nome de elite): contorno de 3 px `#0F0B14` (`Outline Size = 3`), mais sombra (0, 2).
- **Painel flutuante** (tooltip, modal): sombra suave de imagem (textura de sombra 9-slice, deslocamento (0, 8), 50%), não efeito de pós-processo.
- Proibido: Background Blur do UMG e glow de tela cheia. Brilho de UI é textura aditiva pequena (gema, filete, lava).

### 2.13 Movimento da interface

- Abrir/fechar painel: alpha 0→1 em 140 ms + deslocamento de 24 com ease-out cúbico; escala até 0,97→1 é permitida.
- Tooltip: atraso de 150 ms, aparece sem animação. Toast: entra com deslocamento de 24, fica 3 s, some em 200 ms. Faixa de área: 3 s, some em 200 ms.
- Animação 3D de personagens autorada a 30 fps; UI roda a taxa de quadro livre (animações por tempo).
- Lava das barras e orbes: ondulação lenta (período 4 s, amplitude 3%), desligada com "Reduzir movimento".

---

## 3. Especificação de arte 3D e renderização

Esta seção é a referência de arte (escala, proporções, texel, pintura, cores) citada pelo `docs/04_arquitetura.md`; orçamentos técnicos ficam no 04 (seções 17.3 e 18). Valores sob "Tech Lead" são propostas que ele confirma.

### 3.1 Escala e proporções

Unidade: 1 uu = 1 cm. Tile de cenário = 200 cm. Câmera 3/4 fixa (yaw 45°, pitch entre −50° e −60°, FOV estreito; Tech Lead fixa).

| Tipo | Altura | Proporção | Relativo ao herói |
|---|---|---|---|
| **Herói** (Guerreiro, Arqueiro, Mago) | 150 cm | **Chibi, 3 cabeças** (cabeça com elmo/capuz/chapéu ≈ 50 cm; cabeça ≈ 1/3 da altura); mãos e armas ampliadas (arma ≈ 60–70% do tronco) | 1,0 |
| Inimigo pequeno (corvo, cão) | 90 cm | Mesma linguagem chibi | 0,6 |
| **Inimigo comum** | 110–195 cm | Humanoides 3–3,5 cabeças; golens e bestas com massa maior | 0,75–1,3 |
| **Elite** | ×1,15 do comum, mesma malha | Escala uniforme + halo dourado (seção 3.7) | 0,85–1,5 |
| **Chefe do Ato I** | 450–700 cm | 2,5–3,5 cabeças; massa blocada, chanfros grossos | 3–4,7 |
| **Chefe do endgame** (Predador dos Marcos) | 600–800 cm | Quadrúpede ou colosso | 4–5,3 |

Largura de silhueta do herói ≈ 0,7 da altura (ombros, escudo e arma contam). A silhueta de chefe deve caber em 1/3 da altura da tela a 8 m de câmera; chefe que passa disso é recortado pela câmera e precisa de versão de enquadramento (Tech Lead).

### 3.2 Orçamento técnico por asset e por cena

O **`docs/04_arquitetura.md` é o dono dos orçamentos técnicos**: triângulos, ossos, slots e texturas por tipo de asset na seção 17.3, e orçamento por cena (triângulos visíveis, draw calls, pool de textura, Steam Deck e PC de entrada) na seção 18. Este documento não os repete. Valores reconciliados com o 04, só para orientar a arte (em caso de divergência vale o 04):

| Asset | Tris LOD0 | Ossos | Notas de arte |
|---|---|---|---|
| Herói | 7.000 a 10.000 | 55 | Rosto e mãos legíveis; capa e cabelo em malha |
| Inimigo comum | 3.500 a 5.000 | 35 | |
| Elite | **mesma malha do comum**, com tinta, halo e escala até ×1,15 | 35 | Sem textura nova (3.4, item 8) |
| Chefe | 15.000 a 25.000 | 100 | 2048² em um slot ou 2 slots de 1024² |
| Props, kits, folhagem | seção 17.3 do 04 | — | Chanfros grossos, sem normal map |

LOD: trocas a 18 m e 32 m. O que fica **aqui** é a escala, as proporções, a densidade de texel e as regras de pintura.

### 3.3 Texturas e densidade de texel

**Sem normal maps** em personagens, props e kits: a forma vem da malha chanfrada e a luz vem pintada. Cada personagem usa **albedo pintado** + **máscara** (R = rim, G = emissivo, B = AO assada, A = reservado).

| Tipo | Albedo | Máscara | Densidade de texel (mip 0) |
|---|---|---|---|
| Herói | 1024² | 512² | **4,0 texel/cm** (≈ 600 texels de altura) |
| Inimigo | 512² | 256² | **3,0 texel/cm** |
| Chefe | 2048² | 1024² | **2,5 texel/cm** |
| Prop | 256² (máx. 512²) | — | **3,0 texel/cm** |
| Trimsheet de kit | 2048² por kit | — | **2,5 texel/cm** |
| Terreno (tile de 200 cm) | 512² (tileable) | — | **2,56 texel/cm** |

Tolerância de ±20% entre peças da mesma cena; o auditor usa o modo Texture Density do editor. Compressão: albedo BC7 (sRGB), máscara BC1 linear, folhagem BC3. Mipmaps ligados, filtro trilinear com anisotropia 4× (8× em PC), LOD Group próprio por tipo. No Deck o streaming usa um mip a menos que no PC; em jogo, o herói a 110 px de altura raramente precisa do mip 0 (ele existe para retrato, galeria e zoom).
Texturas de UI: UserInterface2D (RGBA), sRGB, mipmaps ligados nas molduras 9-slice de 128 e desligados nos ícones de 32.

### 3.4 Regras de pintura à mão

1. **Luz assada.** O albedo já traz a luz e a sombra pintadas, com a **luz principal vinda do alto-esquerda da tela** (cor quente `#FFB86B`) e a sombra com matiz **violeta-azulado** (`#2C2A4A`). Sombra não é só mais escura: muda de matiz.
2. **Sem preto puro.** O valor mais escuro de qualquer textura é `#0F0B14`; contorno interno de armadura e fendas usam `#161117`. Branco puro só no núcleo de VFX e no flash de acerto.
3. **Rim por fresnel.** Todo personagem recebe rim em runtime: potência 3,0, intensidade 0,5, cor = mistura da cor da névoa da área com 25% de branco, modulado pelo canal R da máscara. Props não têm rim, exceto interativos (baú, portal, altar).
4. **Emissivo para magia e luz.** Chamas, cristais, olhos de inimigo, runas e vidro usam o canal G da máscara com cor de elemento (seção 2.4) e intensidade 2–4; o resto é opaco.
5. **Saturação por plano:** piso e paredes ≤ 35%; personagens ≤ 70%; VFX até 100%. Isso empurra o olhar do chão para os personagens e dos personagens para a magia.
6. **Contraste herói × piso.** A luminância média do herói é ≥ 1,25× a do piso sob ele. O topo da silhueta (cabeça, pluma, chapéu) carrega o acento de cor da classe (pluma `#E0301E`, capuz `#5FD04A`, chapéu azul `#4A9CF0`), porque da câmera é a parte mais visível.
7. **Formas grossas e chanfradas.** Chanfro mínimo de 3 cm em blocos de pedra; sem detalhe menor que 1,5 cm; rachaduras grandes pintadas, não modeladas. Listras de ouro (`#D9A441`) marcam o que é "Marco" (pedra do plano), como nas folhas 07, 15 e 17.
8. **Elite e corrompido por parâmetro.** Elite = tom dourado `#F2B23A` no albedo (lerp de material) + halo; corrompido = tom roxo `#9A4BD6` + chama `#C07BFF`. Nenhuma textura nova; as versões nascem de parâmetros do material (folha 05 e 23 como referência).
9. **Cada herói reconhecível em 1 bit:** Guerreiro (pluma + martelo de bloco + escudo largo), Arqueiro (capuz com bico de osso + arco), Mago (chapéu pontudo + cajado com anel). Não alterar esses elementos sem aprovar (folhas 02 a 04 são a fonte de verdade).

### 3.5 Legibilidade da silhueta a partir da câmera

- Herói com altura mínima de tela de **110 px em 1080p** e **80 px em 800p** (zoom mínimo permitido; Tech Lead).
- **Teste de silhueta:** preencher o personagem de preto sobre piso neutro `#6A5A55`, reduzido a 64 px de altura, em ângulo de câmera de jogo (yaw 45°, pitch −55°). Cada classe e cada arquétipo de inimigo tem de ser identificável. Reprovou: simplificar o interior e exagerar um elemento da silhueta.
- **Inimigos:** 8 arquétipos do Ato I e 9 do endgame com silhuetas distintas (soldado com escudo, lanceiro, cão, corvo, golem de pedra, aríete/prensa, arqueiro espectral, lanterneiro; folhas 05 e 23). Dois inimigos no mesmo plano nunca compartilham a mesma silhueta.
- **Outline:** não há contorno global (o estilo pintado depende de bordas limpas por MSAA). Há **contorno seletivo de 2 px por stencil só quando o herói do jogador ou um elite está oculto atrás de cenário** (herói `#FCD58A`, elite `#F2B23A`, alpha 0,8), para nunca perder o personagem. Inimigo sob o cursor ganha o mesmo contorno em branco-pergaminho.
- Flash de acerto: lerp do albedo para `#FFFFFF` por 83 ms (parâmetro de material), 50% com "Reduzir flashes".

### 3.6 Materiais e renderização

Poucos materiais mestres parametrizados (decisão 4 de `docs/08_decisoes_visual_3d.md`):

| Material mestre | Parâmetros |
|---|---|
| `M_Character` | albedo, máscara, RimColor/Power/Intensity, EmissiveColor/Intensity, HitFlash, TintLerp e TintColor (elite/corrompido), Dissolve (morte), ocluído |
| `M_Environment` | albedo (trimsheet/terreno), cor de vértice (AO e variação), tinta de área, blend de neblina |
| `M_VFX_Player` / `M_VFX_Threat` | aditivo translúcido (jogador); translúcido normal e opaco com contorno (ameaça) |
| `M_UI` | moldura, lava (preenchimento animado), ícone com gema |

Forward Shading com **MSAA 4×** (ver seção 18 do 04 para o Deck), sem Lumen, Nanite nem Virtual Shadow Maps. Sombras: CSM de 1 cascata curta (≈ 25 m) ou sombra de contato/blob; o Tech Lead decide e justifica. Anti-aliasing temporal e TSR desligados; sharpen 0. Pós-processo: tonemapper filmic leve, **sem** exposição automática (exposição manual fixa por área), **bloom leve** (limiar alto, intensidade ≈ 0,25) opcional no Deck, sem vinheta, grão nem aberração cromática (vinheta de vida baixa é widget). Exponential Height Fog com a cor-assinatura da área (2.6); sem volumetric fog. Luz direcional única por cena, sem luzes dinâmicas de ponto exceto até 4 por vista (tochas) com atenuação curta e sem sombra; o resto da luz de tocha é pintado.
Tinta de área (opcional): um LUT de 16³ por área, gerado a partir da cor-assinatura, aplicado no pós-processo.

### 3.7 Kits de cenário

- **Módulo-base 200 cm**, alturas de parede em múltiplos de 100 cm (200, 300, 400). Todo kit tem piso, parede reta, canto, pilar, arco/porta, escada, borda de abismo, ruína (blocos soltos) e 6–10 props de ambientação (folhas 07, 13 a 20).
- **Um kit por área** (11 no total) com a paleta local; blocos de pedra compartilham a trimsheet de pedra para economizar memória, e variam só o material de tinta e os props.
- Terrenos: 4 texturas por área (folha 21) e 4 por mapa de endgame (folha 22), 512² tileable, com variantes de borda para abismo. Marcas de perigo no chão são decals separados.
- Pontos de luz: toda área tem 1 luz de acento (tocha, lanterna, lava, cristal) por 6–8 m de caminho jogável. Elementos de ouro de "Marco" (runas, círculos) são emissivos fracos (intensidade 0,6) para guiar o jogador.
- **Halo de elite:** anel dourado com 2 espinhos, 60–80 cm de diâmetro, 20 cm acima da cabeça, 120 triângulos, material emissivo `#FBD176`, girando 20°/s.

### 3.8 VFX: jogador versus ameaça

Niagara; a spec por habilidade fica fora deste documento (esta seção fixa a linguagem).

| | **Efeitos do jogador** | **Ameaças inimigas** |
|---|---|---|
| Material | Aditivo ou translúcido leve, alpha ≤ 0,75 | Translúcido normal ou opaco, alpha 0,4–1,0, com contorno escuro |
| Forma | Fina: traços, arcos, feixes de 5–25 cm de espessura | Grossa: massas, zonas, cones e círculos preenchidos |
| Cor | `element.*` com núcleo quase branco, meio saturado, borda fria | `threat.*` com núcleo menos branco, borda quase preta e **faixa vermelha** `#E0301E` |
| Onde | No ar, na mão, na linha do projétil | **No chão** (telegraph) antes do impacto, e no corpo do inimigo ao carregar |
| Camadas | 3: núcleo, brilho, partículas (≤ 150) | 4: telegraph no chão, forma opaca, contorno, resíduo (brasa ou crateras) |
| Cobertura de tela | ≤ 12% da tela por efeito (≤ 25% somando) | Telegraph sempre completo e visível, nunca menos de 100% da área |
| Prioridade | Ordem de translucência abaixo | Ordem de translucência acima; desenhado **depois** dos efeitos do jogador |
| Som | Sutil, grave no impacto | Aviso obrigatório no início do telegraph |

**Por elemento (jogador / ameaça):**

| Elemento | Jogador | Ameaça |
|---|---|---|
| **Fogo** | Arco âmbar e dourado, faíscas; faixa de 15 cm | Círculo ou cone de lava vermelho-carmim no chão com borda e brasas; massa opaca |
| **Gelo** | Cristais finos e translúcidos, lança com núcleo `#D8F6FF` | Cristais sólidos azul-escuro com contorno quase preto, zona no chão com geada |
| **Raio** | Fio de 5–10 cm com ramificações, núcleo branco | Raio grosso com aviso no chão (círculo vermelho) antes da descarga |
| **Ácido** | Flechas e rede em verde-limão translúcido | Poça opaca verde-escura com bolhas, borda vermelha de alerta |
| **Sombra** | Fumaça roxa translúcida, só do Mago | Cristais roxos opacos, chama `#C07BFF` do corrompido, zona escura com anel vermelho |

**Regras de legibilidade:**
1. Nenhum efeito do jogador cobre o telegraph: se a zona de ameaça e o efeito do jogador se sobrepõem, o telegraph vence na ordem; o efeito do jogador mantém só o núcleo.
2. Opção de acessibilidade **"Reduzir efeitos do jogador"** (100 / 60 / 30% de alpha e de partículas).
3. Opção **"Daltonismo"** do telegraph: borda amarela `#FFE066` com listras (40 cm) e hachura interna; a forma do telegraph já distingue cone, círculo, linha e estrela.
4. Orçamento: 300 projéteis ativos no máximo e 150 partículas por efeito; a soma de partículas visíveis ≤ 2.500 (Deck ≤ 1.500). Overdraw: no máximo 4 camadas translúcidas sobrepostas no mesmo ponto de tela.
5. Hitstop, shake e flash seguem a seção 6.

### 3.9 UI no motor

- **DPI:** Project Settings → Engine → User Interface: `DPI Scale Rule = Shortest Side` com a curva padrão do UE (480 → 0,444; 1080 → 1,0; 2160 → 2,0). A UI é desenhada em 1080p de referência e escala de forma contínua: 800p (Steam Deck) → 0,74; 1440p → 1,33; 4K → 2,0. `Application Scale = 1,0`.
- No UMG Designer: pré-visualizar em 1920 × 1080 e em 1280 × 800 (Deck). Âncoras em tudo; `Scale Box` só para as imagens de moldura. O piso de legibilidade (12 px efetivos) vale na menor resolução.
- **Texturas de UI:** compressão `UserInterface2D (RGBA)`, sRGB, mipmaps ligados em molduras, filtro bilinear/trilinear, `Never Stream` ligado. PNG de origem em sRGB sem pré-multiplicar alpha.
- **Fontes:** TTF importado como Font Face, `Hinting = Auto`, rasterização padrão com antialiasing; `Loading Policy = Inline` para as três famílias; Composite Font com fallback (2.7). Tamanhos só os da tabela 2.7.
- **Cursor por hardware:** 32 × 32, em ×1, ×1,5 e ×2. Variantes: padrão, ataque, coletar, conversar, arrastar item. Estilo: ponta de pedra com filete dourado.
- **Frame:** 60 fps alvo; animações de UI baseadas em tempo.
- **Rendering do projeto:** Virtual Shadow Maps e Nanite desligados; Lumen desligado.

---

## 4. Especificações de interface

Telas do protótipo: HUD de combate (4.1), inventário e tooltip (4.2), Expedição (4.3), Relatório de expedição (4.4), menu principal e slots de save (4.5), pausa e opções com remapeamento (4.6), mapa do Ato I (4.7). Toda string vem de chave de localização (String Table / `FText`, pt_BR e en), nunca escrita no widget.

Atalhos globais: `Esc` fecha o painel do topo da pilha; sem painel aberto, abre a Pausa. `Enter` confirma o botão primário do painel ativo. `Tab`/`Shift+Tab` e setas movem o foco. Duplo clique = ação principal. No Steam Deck, o gamepad espelha tudo isso (A confirma, B volta, bumpers trocam abas).

### 4.1 HUD de combate — `WBP_HUD` / `UShatterHUDWidget`

Layout a partir da folha 10: retrato e barras no canto superior esquerdo, barra de chefe no centro com cabeça de demônio, minimapa redondo à direita, e uma barra inferior de pedra com orbes nas pontas, poções, 6 habilidades e esquiva.

```
 ┌[retrato][vida ▬▬▬▬][recurso ▬▬]──────────[ Tecelã de Cascalho ═══════ ]────(minimapa redondo)┐
 │[buffs..][Fervor +200% XP]                                                  [Ouro][Cargas]    │
 │                                          (mundo)                                [toasts ↓]    │
 │      ┌─────────────────────────────────────────────────────────────────────────────┐          │
 │      │(VIDA)[P1][P2]  [LMB][RMB][ Q ][ E ][ R ][ F ]  [⤳]            (RECURSO)     │          │
 └──────┴──────────────────────── XP ═══════════════════════════════════──────────────┴──────────┘
```

| Bloco | Âncora | Posição `(x, y, l, a)` | Conteúdo |
|---|---|---|---|
| Retrato | Topo-esquerda | (32, 32, 96, 96) | Retrato da classe na moldura de pedra; selo de nível 48 × 32 em (104, 100) com texto `micro` `text.on_gold` sobre dourado |
| Barras finas | Topo-esquerda | vida (140, 40, 240, 16); recurso (140, 62, 240, 12) | Preenchimento lava (vida) e cor do recurso; redundantes com os orbes; somem com "HUD compacto" |
| Fervor | Topo-esquerda | (140, 84, 280, 40) | Ícone 32 + "+200% XP" em `semantic.fervor`; só no jogo manual. Hover: tooltip "Fervor do Recuperador: XP ×3, Ouro e materiais ×1,25, chance de Raro ×2, Únicos e Fragmentos de Eco" |
| Buffs/debuffs | Topo-esquerda | a partir de (32, 140), ícones 48 com gap 4, até 10 por linha, 2 linhas | Contador `micro` no canto; debuff com borda `semantic.danger` |
| Barra de chefe | Topo-centro | cabeça (840, 16, 96, 96) acima da barra; nome (640, 20, 640, 32) em `body_bold`; barra (640, 56, 640, 28) | Vida lava em `semantic.life`; marcas de fase (3 px `border.gold_highlight`) em 66% e 33%; só em arena de chefe |
| Faixa de área | Topo-centro | (488, 140, 944, 80) | Nome em `title` `text.title` sobre faixa de pedra com filete dourado; 3 s; depois o nome fica em `micro` sob o minimapa |
| Minimapa | Topo-direita | (1648, 32, 240, 240) | Redondo, moldura espinhosa; mostra caveira vermelha (chefe) e seta (jogador); `M` abre o mapa grande |
| Moedas | Topo-direita | Ouro (1648, 284, 128, 32); Cargas (1784, 284, 104, 32) | Ícone 32 + número `body`; Cargas em `semantic.marco_charge` com formato `7/12` |
| Toasts | Topo-direita | coluna em (1408, 332, 480, —), até 4 empilhados, gap 8 | Ver 5.8 |
| Barra inferior | Base-centro | moldura (360, 896, 1200, 168) | `nine_panel_ornate`, pedra com caveiras nos cantos |
| Orbe de vida | Base-centro | (376, 904, 144, 144) | Preenchimento lava de baixo para cima; linha de superfície ondulada `life_highlight`; valor `142/180` em `micro` ao passar o mouse ou com "Sempre mostrar valores" |
| Poções | Base-centro | P1 (536, 920, 64, 88); P2 (608, 920, 64, 88) | Frasco (vermelho vida, azul mana) + quantidade `micro` no canto; ponto de tecla embaixo; vazio = ícone a 40% e número `semantic.danger` |
| Habilidades | Base-centro | 6 slots 88 × 88 a partir de (696, 920), gap 8 → LMB, RMB, Q, E, R, F | Ver 5.5. No demo, R e F aparecem com cadeado |
| Esquiva | Base-centro | (1288, 920, 72, 88) | Ícone de corrida + 3 pontos de carga embaixo (cheio `semantic.warning`, vazio `border.subtle`, recarregando = preenchimento); tecla `Espaço` |
| Orbe de recurso | Base-centro | (1400, 904, 144, 144) | Cor por classe: Ímpeto, Foco ou Mana; vazio mostra vidro escuro (`#211F26`) |
| XP | Base-centro | (696, 1036, 568, 8) | `semantic.xp`; marcas a cada 10%; hover: "Nível 12 · 3.420 / 5.100 XP (67%)" |
| Vinheta de vida baixa | Tela toda | — | Abaixo de 30% de vida: borda `#8C1A12` a 30%, 64 de largura, pulso de 1 s (alpha 20–30%); desligável com "Reduzir flashes" |

**Estados do HUD:** combate (completo); Refúgio (sem barra de chefe; habilidades sem cooldown); arena de chefe (barra de chefe + nome em `display` por 2 s na entrada); morte (HUD some em 200 ms; tela "Você caiu" em `display`, botão "Voltar ao checkpoint", sem penalidade); painel aberto (HUD visível; painéis não cobrem a barra inferior); cinemática (HUD oculto).

**Números de dano** (mundo projetado na tela, `WBP_DamageNumber` em pool de 64):

| Tipo | Estilo | Cor | Movimento |
|---|---|---|---|
| Normal | `damage` 28 | Pelo tipo (físico/fogo/gelo/raio/ácido/sombra) | Sobe 40 em 700 ms (ease-out); some nos últimos 200 ms |
| Crítico | `damage_crit` 44 + "!" | `#FFE066` | Pulsa a 120% por 120 ms, depois sobe 40; deslocamento lateral aleatório de ±24 |
| Dano recebido | `damage` 28 | `#FF7B66` | Sobe sobre o jogador |
| Cura | `damage` 28 com "+" | `#8FD06A` | Igual |
| Bloqueado / Evadido | `body` 20 "Bloqueado" / "Evadido" | `#9A8D97` | Igual |

Golpes no mesmo alvo dentro de 100 ms somam num número. Formato `1.234` (pt-BR). Contorno de 3 px `#0F0B14`.

**Texto mais longo (pt-BR):** "+200% XP" (ícone 32 + 8 caracteres ≈ 120; cabe em 280). Nome de chefe mais longo: "Tecelã de Cascalho" (18 caracteres ≈ 190 px em `body_bold`; cabe em 640). Faixa de área mais longa: "Armazém de Cinzas" / "Túneis do Voto" (≤ 18 caracteres em `title` ≈ 20 px/caractere ≈ 360; cabe em 944).

**Interação:** clique no orbe ou barra = nada; hover em habilidade = tooltip (nome, custo, recarga, tags, sigilos); itens no chão mostram rótulo (Mágico ou acima) e `Alt` mostra todos.

### 4.2 Inventário — `WBP_Inventory` / `UShatterInventoryWidget` (tecla `I`)

Painel lateral à direita, personagem visível à esquerda e barra inferior livre.

| Bloco | Âncora | Posição | Conteúdo |
|---|---|---|---|
| Painel | Direita (topo-direita) | (1056, 32, 832, 840) | `nine_panel_ornate` |
| Cabeçalho | — | (1088, 56, 768, 48) | "Inventário" em `title`; botão fechar 48 × 48 em (1792, 56) |
| Equipamento | — | (1088, 112, 768, 328) | Silhueta 3D da classe (render do herói) ao centro e 8 slots 88 × 88 ao redor: Arma (esq.-meio), Mão secundária (dir.-meio), Elmo (topo), Peitoral (centro abaixo do elmo), Luvas (esq.-baixo), Botas (base), Amuleto (dir.-topo), Anel (dir.-baixo). Demo: 5 posições ativas (Arma, Elmo, Peitoral, Botas, Anel), as outras com cadeado. Slot vazio mostra ícone-fantasma da posição em `border.subtle` |
| Abas | — | (1088, 452, 768, 48) | "Mochila" · "Baú compartilhado" (só no Refúgio; fora dele fica desabilitada com tooltip "Disponível no Refúgio do Marco") |
| Grade | — | (1096, 508, 752, 280) | 8 × 3 slots de 88 × 88 gap 4 na vista padrão; a Mochila tem 40 posições, rolagem vertical com `ScrollBox` (5 linhas de 8) |
| Recursos | — | (1088, 796, 768, 72) | Linha 1: Ouro, Lascas, Cinzas de Memória; linha 2: Fragmentos de Eco `12/50`, Cargas do Marco. Ícone 32 + número; hover com nome e explicação |

**Interação (teclado, mouse e gamepad):**
- Clique esquerdo: pega o item (preso ao cursor, slot de origem a 40%); clique em outro slot troca; clique fora do painel pergunta "Largar Lâmina do Voto Quebrado no chão?".
- Clique direito: equipar/desequipar (vai para a posição certa; se ocupada, troca).
- `Shift` segurado: tooltip de comparação lado a lado. `Ctrl+Clique`: mover entre Mochila e Baú. `Alt+Clique`: marcar como lixo (ícone 32), "Reciclar marcados" no Bram.
- Teclado: setas movem o foco; `Enter` = clique direito; `Espaço` = pegar/soltar; `Esc`/`I` fecha.
- Requisito não cumprido: slot com hachura diagonal `semantic.danger` a 25% e toast "Requer nível 12".

**Estados:** normal; item preso ao cursor; mochila cheia (toast "Mochila cheia" + contador `40/40` em `semantic.warning`); Baú indisponível; slot bloqueado (demo).

**Tooltip de item — `WBP_ItemTooltip` / `UShatterItemTooltip`:**

```
┌───────────────────────────────┐  largura máx. 480 (≈ 50 caracteres por linha)
│ Lâmina do Voto Quebrado       │  body_bold, cor da raridade, até 2 linhas
│ Único · Espada Longa          │  text.secondary
├───────────────────────────────┤  divisória 2 px border.subtle
│ Dano físico: 14–22            │  text.primary (propriedades da base)
│ Ataques por segundo: 1,20     │
├───────────────────────────────┤
│ +18% de dano físico aumentado │  item_text.affix, um afixo por linha
│ +24 de vida máxima            │
│ Acertos atordoados geram 1    │  item_text.unique_effect (Único)
│ carga de Ímpeto               │
│ ▼ Você não pode bloquear      │  item_text.unique_drawback (contrapartida)
├───────────────────────────────┤
│ Requer nível 12               │  text.secondary; danger_text se não cumprido
│ "Jurou proteger um rei que…"  │  text.muted itálico (sabor, só Único)
├───────────────────────────────┤
│ [RMB] Equipar  [Shift] Comparar│ micro + glifos de tecla atuais
└───────────────────────────────┘
```

- Fundo `#161117` a 95%, borda 2 px na cor da raridade, cantos conforme a raridade (2.3), padding 24, gap de 8 entre linhas de grupos, 16 entre grupos. Ícone do item de 128 no topo à direita do nome (96 efetivos).
- Posição: 24 à direita e abaixo do cursor; se passar da margem segura, vira para a esquerda/acima; nunca cobre o slot de origem; com foco por teclado ou gamepad, ancora ao lado do slot focado.
- Comparação (`Shift`): segundo tooltip à esquerda com cabeçalho "Equipado" em `micro`; no novo, cada atributo mostra a diferença: `▲ +6` em `compare_better`, `▼ −4` em `compare_worse`.
- Nome com gênero gramatical correto: exemplos "Espada Flamejante", "Lança Sombria".
- **Texto mais longo para testar:** nome "Anel Flamejante do Recuperador Paciente" (40 caracteres → 2 linhas), afixo "+18% de dano de projétil contra inimigos atordoados" (51 caracteres → 2 linhas), efeito de Único com 3 linhas. Altura máxima do tooltip: 800; acima disso, o sabor é cortado primeiro.

### 4.3 Expedição — `WBP_Expedition` / `UShatterExpeditionWidget` (falar com a Ilsa)

Painel modal sobre `surface.scrim`. Fluxo: área dominada → objetivo → regras de IA → duração → previsão → iniciar.

| Bloco | Posição (âncora: centro) | Conteúdo |
|---|---|---|
| Painel | (160, 48, 1600, 984) | `nine_panel_ornate` |
| Cabeçalho | (192, 64, 1536, 56) | "Expedição" em `title`; à direita: "Cargas do Marco: 7/12" com ícone e "Vigor: descansado" |
| Coluna A — Áreas dominadas | (192, 136, 480, 784) | `ScrollBox`, linhas de 80: nome da área (`body_bold`), "Níveis 2–4 · Dominada" (`text.secondary`), selo. Áreas não dominadas desabilitadas com cadeado e "Vença a área na mão, com o chefe, para liberar" |
| Coluna B — Plano | (704, 136, 512, 784) | **Objetivo**: 3 botões segmentados com ícone 48 (XP · Ouro · Materiais). **Duração**: slider 1–12 h em passos de 1 h, rótulo "4 h · gasta 4 cargas"; abaixo, 12 barrinhas 32 × 16 por Vigor (h1–4 `vigor` 100%, h5–8 a 70%, h9–12 a 40%) com legenda "Descansado até 4 h, depois cansa". **Previsão** (cartão `panel_raised`): "8–12 mil de XP", "1,1–1,6 mil de Ouro", "Raros: até 4"; "Risco de recuo: Médio" com selo `semantic.warning` e motivo "Falta resistência a fogo" |
| Coluna C — Regras de IA | (1248, 136, 480, 784) | Título "Regras (em ordem)" + contador `4/6`. Até 6 `WBP_RuleRow` (80, gap 8). Botão "+ Adicionar regra" (desabilitado com 6). Última linha fixa: "Senão: ataque básico" em `text.muted` |
| Aviso de compatibilidade | (192, 936, 944, 80) | Faixa `panel_raised` com filete `semantic.danger` (bloqueia) ou `semantic.warning`. Ex.: "Raio do Arquivo ainda não funciona em patrulha. Troque a habilidade para iniciar." |
| Botões | (1184, 952, 544, 56) | "Cancelar" (secundário, 192) · "Iniciar expedição" (primário, 336) |

**Linha de regra (`WBP_RuleRow`):** número de ordem (32) · linha 1: "Se: Vida abaixo de 35%" (combo de condição + valor) · linha 2: "Faça: Usar poção" (combo de ação) · alças ▲▼ e "×" à direita (32 cada). Condições usam ícone 48 (vida, recurso, inimigos próximos, elite, chefe). Valores percentuais em passos de 5%.

**Estados:**
- Nenhuma área dominada: colunas B e C desabilitadas; mensagem central "Vença o Guardião da Cripta para instalar o primeiro Marco de Retorno."
- Cargas insuficientes: o slider para no máximo possível; "Cargas para até 3 h. Jogue na mão para ganhar mais (+1 por área limpa, +2 por chefe)".
- Incompatível: "Iniciar expedição" desabilitado + aviso vermelho com o nome da habilidade/Único.
- Outro personagem em expedição: só o card da expedição em andamento ("Bram está patrulhando a Cripta Partida · faltam 2 h 14 min") e o botão "Ver relatório quando voltar".
- Confirmação: modal curto "A build e as regras ficam congeladas até o fim. Iniciar?" com "Iniciar" e "Voltar". Depois: "Feche o jogo quando quiser; o Tico traz o relatório."
- Nunca mostrar "−65%" ou comparação negativa com o manual; a previsão é absoluta.

**Interação:** setas/Tab percorrem as colunas A → B → C → botões; `Enter` seleciona; na coluna C, `Ctrl+↑/↓` move a regra, `Delete` remove (com desfazer por 5 s via toast "Regra removida · Desfazer (Ctrl+Z)"); arrastar pela alça com o mouse; roda do mouse no slider muda 1 h.

**Texto mais longo:** regra "Se: 3 ou mais inimigos a até 4 m / Faça: Usar Fenda de Pedra" (cada linha ≤ 30 caracteres ≈ 285 px; combo com 392 úteis cabe; em pt-BR longo quebra em 2 linhas e a linha cresce para 112); aviso de 80 caracteres ≈ 760 px → 2 linhas em 928 úteis; nome de área "Armazém de Cinzas".

### 4.4 Relatório de expedição — `WBP_ExpeditionReport` / `UShatterExpeditionReportWidget`

Aparece ao abrir o jogo (ou ao falar com o Tico) quando há expedição terminada. Coletar é obrigatório antes de fechar (a coleta é o salvamento).

| Bloco | Posição (âncora: centro) | Conteúdo |
|---|---|---|
| Painel | (160, 48, 1600, 984) | `nine_panel_ornate` |
| Cabeçalho | (192, 64, 1536, 56) | Retrato do Tico 48 + "Relatório · Cripta Partida" em `title` |
| Resumo | (192, 136, 736, 208) | Grade 2 × 3 de números grandes (`body_bold`) com rótulo `text.secondary`: Tempo efetivo "7 h 40 min de 8 h"; Encontros vencidos "212"; Poções gastas "31"; XP "+9.840"; Ouro "+1.312"; Motivo da parada (ícone + "Duração concluída" / "Recuou: sem poções" / "Relógio do PC voltou; encerrada no último ponto") |
| Vigor por hora | (192, 360, 736, 96) | 12 colunas 48 × 64 (uma por hora), altura = XP da hora, cor `semantic.xp`; hora sem patrulha em `border.subtle`; hover mostra o recibo da hora |
| Recibos | (192, 472, 736, 448) | Lista agrupada por hora (`ScrollBox`): "Hora 3 · 27 encontros · 4 poções · 1 recuo parcial"; clique expande ("Sentinela Oca ×3 · vencido em 18 s · 1 poção") |
| Loot | (976, 136, 768, 392) | Grade 8 × 4 de slots 88 (rolagem se exceder): Raros primeiro, depois Mágicos, Comuns, Páginas, Sigilos; materiais e Ouro em linha própria. Tooltip igual ao inventário |
| Dica | (976, 544, 768, 144) | Cartão com filete `semantic.info`: "Sua cura falhou 3 vezes; tente subir o limiar para 45%." + botão terciário "Ajustar regra" |
| Convite | (976, 704, 768, 144) | Cartão dourado: "Jogando esta rota você teria Fervor e chance de Únicos." + botão secundário "Jogar esta rota agora" |
| Botões | (1184, 952, 544, 56) | "Coletar tudo" (primário); "Coletar e nova expedição" (secundário) |

**Estados:**
- Calculando: o Tico (modelo 3D correndo em loop, 8 s) e "O Tico está voltando…"; barra indeterminada; meta < 2 s; botões ocultos.
- Pronto: contagem animada dos números (0 → valor em 600 ms); Raros ganham brilho na moldura por 400 ms ao aparecer.
- Mochila cheia: excedente vai para o Baú; aviso `semantic.info` "12 itens foram para o Baú compartilhado".
- Relógio voltou: aviso `semantic.warning` em linguagem neutra.
- Coletado: botões trocam para "Fechar"; não coleta de novo.
- Nunca usar vermelho para quantidades menores; só para recuo por falta de recurso.

**Texto mais longo:** motivo "Recuou: faltou resistência a fogo" (33 caracteres ≈ 350 px ocupa a célula inteira de 736 em duas colunas, por isso a célula de motivo tem largura total na 3ª linha); dica com até 3 linhas (≤ 150 caracteres).
**Interação:** `Enter` = Coletar tudo; Tab percorre loot → dica → convite → botões; `Esc` não fecha antes de coletar (toast "Colete os itens antes de sair").

### 4.5 Menu principal e slots de save

**Menu principal — `WBP_MainMenu` / `UShatterMainMenuWidget`**

| Bloco | Âncora | Posição | Conteúdo |
|---|---|---|---|
| Fundo | Tela toda | — | Cena 3D do Refúgio do Marco à noite (lanterna e sino animados, câmera com leve órbita), mais escura à esquerda; os 3 heróis da key art (folha 01) |
| Logo | Topo-esquerda | (96, 96, 640, 192) | Logo "Echoes of the Shatter" (arte própria, não fonte) |
| Menu | Esquerda-centro | coluna em (96, 400, 400, —), botões 56 de altura, gap 16 | "Continuar" (primário, com legenda `micro` "Guerreiro · Nível 12 · Pátio dos Marcos"), "Novo jogo", "Carregar", "Opções", "Créditos", "Sair" |
| Selo de expedição | Ao lado de "Continuar" | +16 à direita | Ícone 32 + "Expedição pronta" em `semantic.eco` quando houver relatório |
| Versão | Base-direita | (1504, 1040, 384, 24) | `micro` `text.muted` "0.3.1-ea+a1b2c3" |
| Pasta de logs | Base-esquerda | (32, 1020, 320, 40) | Link terciário "Abrir pasta de logs" |

Estados: primeira execução (sem "Continuar" e sem "Carregar"; "Novo jogo" é primário); save danificado recuperado (toast `semantic.warning` "O save principal estava danificado. Carregamos o backup de 15/10/2026 21:35.").

**Slots de save — `WBP_SaveSlots` / `UShatterSaveSlotsWidget`**: painel centralizado (400, 128, 1120, 824) com título "Carregar jogo" e 3 cartões `WBP_SaveSlotCard` de 1120 × 224 (gap 16).
Cartão (padding 24): retrato 96 × 96 à esquerda; à direita:
- Linha 1: nome do personagem (`body_bold`) + selo de nuvem 32 ("Steam Cloud").
- Linha 2: "Guerreiro · Nível 12" · "Pátio dos Marcos".
- Linha 3: "Tempo de jogo: 14 h 32 min" · "Salvo em 15/10/2026 21:40" (formato do idioma; pt-BR `dd/MM/aaaa HH:mm`).
- Linha 4 (se houver): "Em expedição · faltam 3 h 05 min" (`text.secondary`) ou "Expedição pronta para coletar" (`semantic.eco`).
- Botões à direita: "Carregar" (primário), "Apagar" (texto, `semantic.danger_text`).

Estados do cartão: normal; hover/foco (borda `border.focus`); vazio ("Espaço vazio" + "Novo jogo"); danificado com backup ("Recuperado do backup de 15/10 21:35" com ícone de aviso); danificado sem backup (desabilitado, "Não foi possível ler este save. Abra a pasta de logs para relatar."); versão nova de save (migração automática, sem aviso).
Apagar: modal "Apagar Bram, Guerreiro nível 12? Isto não pode ser desfeito." com botão "Apagar" que exige **segurar 1 s** (barra de preenchimento lava no botão).
Interação: ↑/↓ entre cartões, `Enter` carrega, `Delete` apaga (abre confirmação), `Esc` volta.
**Texto mais longo:** "Expedição pronta para coletar" (29 caracteres ≈ 275 px); "Arqueiro · Nível 30 · Mirante Partido" (37 caracteres ≈ 350 px); área útil do texto 760.

### 4.6 Pausa e opções

**Pausa — `WBP_PauseMenu` / `UShatterPauseMenuWidget`** (`Esc`): `surface.scrim` sobre o jogo (single-player, o jogo pausa). Coluna central (760, 320, 400, —): "Continuar" (primário), "Opções", "Abrir pasta de logs", "Menu principal", "Sair do jogo". Sair e Menu principal mostram "O jogo é salvo automaticamente. Sair agora?" com "Sair" e "Ficar". Esc fecha a pausa.

**Opções — `WBP_Options` / `UShatterOptionsWidget`**: painel (160, 48, 1600, 984); abas no topo (192, 64): Jogo · Vídeo · Áudio · Controles · Acessibilidade. Conteúdo em lista de linhas de 56: rótulo à esquerda (largura 640), controle à direita (800). Rodapé: "Restaurar padrão" (texto), "Cancelar" (secundário), "Aplicar" (primário). Mudanças de vídeo pedem confirmação com contagem regressiva de 15 s ("Manter estas configurações?").

| Aba | Itens |
|---|---|
| Jogo | Idioma (Português (Brasil), English); Mostrar valores nos orbes; HUD compacto; Mostrar números de dano; Rótulos de itens no chão (Mágico+ / Raro+ / Todos) |
| Vídeo | Modo de tela (Janela, Tela cheia sem bordas, Tela cheia); Resolução; Escala de renderização (50–100%, padrão 100%); Qualidade (Deck / Baixa / Média / Alta: MSAA 2×/4×, sombra, bloom); VSync; Limite de FPS (30/40/60/120/Sem limite) |
| Áudio | Geral, Música, Efeitos, Interface (sliders 0–100 em passos de 5) |
| Controles | Remapeamento (abaixo), glifos de gamepad |
| Acessibilidade | Texto grande; Tremor de tela (Normal / Reduzido / Desligado); Reduzir flashes; Reduzir sangue; Reduzir efeitos do jogador (100/60/30%); Reduzir movimento da interface; Daltonismo: reforço de forma nas raridades (sempre ligado) e telegraph alternativo (laranja → amarelo com listras) |

**Remapeamento — `WBP_KeyBindRow` / `UShatterKeyBindRow`**: tabela com colunas Ação (480) · Principal (240) · Alternativa (240). Padrões do plano: Mover (W/S/A/D), Ataque básico (botão esquerdo), Habilidade 1–5 (botão direito, Q, E, R, F), Esquiva (Espaço), Poção 1 e 2 (1, 2), Inventário (I), Árvore passiva (P), Mapa (M), Mostrar itens no chão (Alt), Comparar item (Shift).
- Clicar na célula (ou `Enter`): vira "Pressione uma tecla… (Esc cancela)" com borda `border.focus` piscando a 2 Hz.
- Conflito: "Q já está em Habilidade 2. Trocar as duas?" → "Trocar" / "Cancelar".
- `Esc` não é remapeável; "Mirar" é sempre o mouse (ou o analógico direito no gamepad).
- Ação sem tecla: "—" em `semantic.warning` e aviso no rodapé "Ação sem tecla: Poção 2".
- Glifos do HUD e dos tooltips atualizam na hora. Recomendação ao Frontend: Enhanced Input com *Player Mappable Key Settings*, salvo fora do Steam Cloud.
**Texto mais longo:** "Mostrar itens no chão" (21 caracteres), "Tela cheia sem bordas" (21 ≈ 200 px no controle de 800), "Daltonismo: reforço de forma nas raridades" (43 ≈ 410 px; a coluna de rótulo de 640 comporta).

### 4.7 Mapa do Ato I — `WBP_WorldMap` / `UShatterWorldMapWidget`

Folha 12: ilhas flutuantes ligadas por uma trilha, nó de área com 3 losangos de dificuldade, painel lateral de pedra com a área selecionada.

| Bloco | Posição | Conteúdo |
|---|---|---|
| Mapa | Tela toda | Ilustração 2D pintada do Ato I (8 áreas) com os nós; área dominada = losangos dourados; bloqueada = escudo cinza com cadeado; selecionada = brilho dourado e pulso |
| Painel de área | Direita (1360, 64, 528, 952) | `nine_panel_ornate`; imagem da área (com a névoa-assinatura), losangos, 3 inimigos típicos, chefe, recompensas (moeda, cristal, minério, pergaminho) e botão "Entrar" (primário, 336 × 56) |
| Herói | Base-esquerda | Modelo 3D do herói em primeiro plano, só decoração |

Estados: área nova (pulso dourado), dominada (selo), bloqueada (cadeado e motivo). Entradas: setas/gamepad entre nós, `Enter` abre o painel, `Esc` volta. Texto: nome da área em `title`, até 18 caracteres.

---

## 5. Componentes reutilizáveis

Cada componente tem uma classe C++ base (lógica, estados, eventos) e um Widget Blueprint de visual. Cores e texturas vêm de uma única Data Asset `DA_ShatterUIStyle` (ou `USlateWidgetStyleAsset`) preenchida com os tokens.

### 5.1 Estados comuns

| Estado | Regra visual |
|---|---|
| Normal | Cores de repouso do componente |
| Hover | Fundo um passo mais claro (`panel_hover` ou `action.primary_hover`); borda `border.gold_highlight`; som curto |
| Pressionado | Fundo um passo mais escuro; **conteúdo desce 2** |
| Desabilitado | Texto `text.disabled`, ícone a 40%, borda `border.subtle`; tooltip obrigatório com o motivo ("Requer 6 cargas") |
| Foco (teclado, gamepad) | Anel de 3 `border.focus` a 3 por fora da borda, mais marcadores de canto 8 × 8; nunca só cor de fundo |
| Selecionado | Abas, linhas e segmentos: fundo `panel_raised` + filete de 4 `border.gold` à esquerda (linhas) ou embaixo (abas) |

Hover e foco podem coexistir; o foco nunca some quando o mouse sai.

### 5.2 Botão — `WBP_Button` / `UShatterButton`

Variantes: **Primário** (`action.primary`, texto pergaminho; 1 por tela), **Secundário** (`action.secondary`, borda `border.default`), **Terciário/Texto** (sem fundo, texto `text.title`, sublinhado de 2 no hover), **Ícone** (48 × 48, tooltip obrigatório), **Perigoso** (secundário com texto `semantic.danger_text`; opção "segurar 1 s").
Medidas: altura 56, padding horizontal 16, largura mínima 192, texto `body` centralizado; ícone opcional 32 à esquerda com gap 8. Glifo de tecla opcional à direita (`micro`).

### 5.3 Painel — `WBP_Panel` / `UShatterPanel`

Variantes: **Ornamentado** (`nine_panel_ornate`, telas principais), **Simples** (`nine_panel_plain`, cartões), **Cartão** (`panel_raised` + filete semântico de 4 à esquerda: info, aviso, perigo, dourado). Slots: cabeçalho opcional (título `title` + fechar), corpo, rodapé. Padding 32.

### 5.4 Barra — `WBP_Bar` / `UShatterBar` e `WBP_Orb` / `UShatterOrb`

- Barra: moldura `nine_bar_frame`, fundo cor escura do token, preenchimento **lava** (gradiente do token claro ao escuro, brilho no topo, ondulação lenta); "rastro" de perda (parte perdida em `life_highlight` por 400 ms antes de cair); texto opcional `micro`. Alturas: 8 (XP), 16 (fina), 28 (chefe).
- Orbe: esfera de vidro 144 × 144 com máscara circular; preenchimento por material (altura do líquido) com linha de superfície ondulada; reflexo estático.
- Estados: normal, cheio (brilho no topo), baixo (< 30%: pulso de alpha 1 s), bloqueado (cinza `text.disabled`).

### 5.5 Slot de item — `WBP_ItemSlot` / `UShatterItemSlot` · Slot de habilidade — `WBP_SkillSlot` / `UShatterSkillSlot`

- Item: 88 × 88, `nine_slot`, ícone 80 centralizado; canto pela raridade; gema inferior `#F2B23A`; número de pilha `micro` no canto inferior direito. Estados: vazio (ícone-fantasma), com item, hover (borda `border.gold_highlight`), arrastando (origem a 40%), alvo válido (borda `semantic.success`) ou inválido (`semantic.danger`), requisito não cumprido (hachura), bloqueado (cadeado 32), novo (ponto 8 `semantic.eco` até o primeiro hover).
- Habilidade: 88 × 88, gema da classe embaixo; tecla em `micro` no canto inferior esquerdo sobre placa escura; recarga = escurecimento `#0F0B14` a 60% varrendo de cima para baixo + segundos restantes em `body` ("3", "0,8" abaixo de 1 s); recurso insuficiente = ícone tingido com a cor escura do recurso a 50%; pronta após recarga = brilho de borda por 150 ms; bloqueada (demo) = cadeado.

### 5.6 Tooltip — `WBP_Tooltip` / `UShatterTooltip` (e `UShatterItemTooltip` para itens)

Fundo `#161117` a 95%, `nine_tooltip`, sombra suave; padding 24; largura máxima 480 (576 com texto grande); atraso 150 ms; regras de posição de 4.2. Variantes: simples, habilidade (nome, custo, recarga, tags como chips `micro`, sigilos, emblema do elemento), item (4.2).

### 5.7 Linha de regra — `WBP_RuleRow` / `UShatterRuleRow`

80 (112 com quebra), fundo `panel_raised`; número de ordem em `text.title`; dois combos (`WBP_Dropdown` / `UShatterComboBox`) de condição e ação; alças ▲▼ e ×. Estados: normal, hover, foco, arrastando (sombra + linha-guia dourada de 4 no destino), inválida (borda `semantic.danger` + "Habilidade não equipada"), incompatível com idle (filete `semantic.danger` + nome da habilidade), fixa ("Senão: ataque básico", sem alças).

### 5.8 Toast — `WBP_Toast` / `UShatterToast` (fila em `UShatterToastSubsystem`)

480 × 64, `nine_toast`, filete de 4 à esquerda na cor do tipo; ícone 32 + texto `body` (1 linha, ≤ 40 caracteres; 2 linhas → 96 de altura). Tipos: info, sucesso, aviso, perigo, loot (cor da raridade; ex.: "Raro: Elmo do Vigia"), especial Fragmento de Eco (`semantic.eco` + som próprio). Máximo 4 visíveis; o mais novo em cima; 3 s; hover pausa o tempo; ação opcional ("Desfazer").

### 5.9 Outros componentes

| Componente | Widget / Classe | Nota |
|---|---|---|
| Abas | `WBP_Tabs` / `UShatterTabBar` | 48 de altura; `Ctrl+Tab`, clique e bumpers do gamepad (Q/E são habilidades) |
| Combo | `WBP_Dropdown` / `UShatterComboBox` | Lista abre para baixo, máx. 8 itens visíveis, rolagem |
| Slider | `WBP_Slider` / `UShatterSlider` | Trilho 8, alça 24 × 32, passos discretos, valor à direita |
| Alternador | `WBP_Toggle` / `UShatterToggle` | Caixa 32 × 32 com marca de ouro; "Ligado/Desligado" escrito |
| Segmentado | `WBP_Segmented` / `UShatterSegmentedControl` | Objetivo da expedição |
| Diálogo | `WBP_ConfirmDialog` / `UShatterConfirmDialog` | 720 de largura, scrim 78%, foco inicial no botão seguro |
| Cartão de save | `WBP_SaveSlotCard` / `UShatterSaveSlotCard` | 4.5 |
| Linha de tecla | `WBP_KeyBindRow` / `UShatterKeyBindRow` | 4.6 |
| Número de dano | `WBP_DamageNumber` / `UShatterDamageNumber` | Pool de 64, posição projetada |
| Rótulo de item no chão | `WBP_LootLabel` / `UShatterLootLabel` | Placa de pedra + borda 2 da raridade + nome; empilhamento sem sobreposição (desloca 24) |
| Glifo de tecla | `WBP_KeyGlyph` / `UShatterKeyGlyph` | Lê o mapeamento atual |
| Mapa de área | `WBP_WorldMap` / `UShatterWorldMapWidget` | 4.7 |

---

## 6. Feedback de combate ("juice")

Valores alinhados à seção 5 do plano. Todos configuráveis em dados (`Content/Data/`), não no código.

| Efeito | Quando | Valor |
|---|---|---|
| **Hitstop** | Golpe pesado / crítico / golpe pesado de chefe no jogador / jogador atingido | 60 / 80 / 80 / 40 ms; nenhum em golpe leve. Só pausa quem bateu e quem apanhou (`CustomTimeDilation` = 0 na entidade), nunca o jogo todo |
| **Flash branco** | Inimigo atingido | Malha inteira em `#FFFFFF` por 83 ms via parâmetro de material (lerp, sem aditivo). Com "Reduzir flashes": 50% |
| **Knockback** | Inimigo comum / elite / chefe | 20 / 6 / 0 cm em 100 ms |
| **Tremor de câmera** | Só impactos grandes (golpe pesado que mata 3+, impacto de chefe, Golpe do Shatter) | Amplitude 3 cm (pesado), 5 cm (chefe), teto 8 cm; 120–250 ms; ruído a 30 Hz decaindo linearmente; só translação. Opções: Normal / Reduzido (50%) / Desligado |
| **Partículas de contato** | Todo acerto | Poeira `#8A7F78` 6–10 e faíscas `#FFE066` 4–8 (metal/pedra); 2–8 cm, vida 300–700 ms. Carne/osso: lascas `#D8381F`/`#D9D2C8` (desligadas com "Reduzir sangue") |
| **Morte de inimigo** | Ao morrer | Animação de morte curta + corpo que se desfaz em 12–20 estilhaços de pedra e ouro `#FCD58A` subindo 20–40 cm e sumindo em 500 ms (dissolve no material) |
| **Números de dano** | Todo acerto | 4.1; crítico maior e amarelo |
| **Telegraph de chefe** | 700–1200 ms antes do golpe | Forma no chão (cone, círculo, linha, estrela) com preenchimento `#D8432F` subindo de 40% a 65%, borda `#FF6A4A` de 12 cm, runas internas e brasas subindo; nos últimos 100 ms a borda pisca branco. Sempre com som |
| **Drop** | Item cai | Comum: som simples; Mágico: brilho de 20 cm de raio; Raro: coluna `#FFD24A`; Único: coluna `#FF8A2E` com pulso de 800 ms + som próprio |
| **Fragmento de Eco** | Ganho no jogo manual | Partículas `#4FE0D0` em espiral até o contador do HUD (400 ms) + toast especial + som próprio |
| **Esquiva** | Espaço | 2 imagens residuais do herói a 50% e 25% de alpha nos primeiros 200 ms (janela de invulnerabilidade) |
| **Vida baixa** | < 30% | Vinheta 4.1 + batimento sonoro |

Regras: nenhum efeito usa blur de tela cheia; bloom só leve (3.6); limite de 300 projéteis ativos e partículas em pool; Niagara com sistemas pequenos e GPU emitters apenas quando passar de 200 partículas.

---

## 7. Checklist de qualidade visual (QA / Release)

**Arte 3D e render**
- [ ] Cada tipo de asset dentro do orçamento da seção 17.3 do `docs/04_arquitetura.md`; auditoria no editor (17.4).
- [ ] Densidade de texel dentro de ±20% da meta (3.3), medida com Texture Density.
- [ ] Nenhuma textura de personagem, prop ou kit com normal map; nenhum preto puro na paleta (valor mínimo `#0F0B14`).
- [ ] Teste de silhueta (3.5) aprovado para as 3 classes, 8 inimigos do Ato I e 9 do endgame.
- [ ] Contorno seletivo aparece só quando herói ou elite está oculto; nenhum outline global.
- [ ] Captura em hardware real conforme o orçamento por cena da seção 18 do `docs/04_arquitetura.md`.
- [ ] Cada área exibe sua cor-assinatura de névoa (2.6); telegraph legível em todas, incluindo as de névoa vermelha (variante `dark_outline`).
- [ ] MSAA ativo, sem serrilhado visível em borda de pedra e arma; sem TSR, sem exposição automática.

**Texto e localização**
- [ ] Frase-teste da 2.7 renderiza todos os glifos nos 7 estilos, em 1080p e em 800p; nenhum texto abaixo de 12 px efetivos no Deck.
- [ ] Todas as telas da seção 4 verificadas com as strings mais longas em pt-BR e en; nenhum texto cortado, sobreposto ou fora da margem segura de 32.
- [ ] Texto grande ligado: tooltip, relatório e opções continuam legíveis e com rolagem quando precisa.
- [ ] Nomes de item com gênero correto ("Lança Sombria", não "Lança Sombrio").
- [ ] Números em formato do idioma (1.234 / 1,20 em pt-BR); datas dos saves no formato local.

**Cor e leitura**
- [ ] Contraste de texto ≥ 4,5:1 sobre o fundo real (exceto `text.disabled`, sempre com motivo).
- [ ] Raridade identificável sem cor (texto no tooltip e forma do canto do slot) com filtro de daltonismo (deuteranopia e protanopia); Vida × Ímpeto distinguíveis por posição e ícone.
- [ ] Telegraph de chefe visível sobre todos os pisos e névoas e lido em < 0,5 s por testador.
- [ ] Efeito do jogador nunca esconde telegraph; "Reduzir efeitos do jogador" funciona.
- [ ] Nenhum número negativo nas telas de expedição/relatório; "+200% XP" do Fervor presente no jogo manual.

**Interação**
- [ ] Todas as telas operáveis só com teclado, só com mouse e só com gamepad; anel de foco sempre visível.
- [ ] Cinco estados de cada componente da seção 5 conferidos na galeria `WBP_UIGallery`.
- [ ] Remapear todas as ações; conflitos tratados; glifos do HUD atualizados; configuração persiste.
- [ ] Expedição: estados vazio, cargas insuficientes, incompatível e "outro personagem em expedição" reproduzidos.
- [ ] Relatório: não fecha sem coletar; não coleta duas vezes.

**Combate e acessibilidade**
- [ ] Hitstop 40–80 ms, flash 83 ms, knockback por tipo, partículas e morte em estilhaços conferidos em vídeo a 60 fps.
- [ ] Tremor Desligado zera todo tremor; Reduzir flashes e Reduzir sangue funcionam.
- [ ] Pool de números de dano não aloca durante o combate (80 inimigos na tela).

**Assets e licenças**
- [ ] Todas as fontes com licença registrada (Source Sans 3, Cinzel, Lilita One: OFL 1.1) e arquivo de licença no build.
- [ ] Modelos, texturas, ícones e molduras finais feitos ou refeitos por artista; nenhum asset do Spell Brigade no projeto ou no build; imagens geradas por IA são só conceito e o uso de IA é declarado na Steam (decisão 7 de `docs/08_decisoes_visual_3d.md`).
- [ ] Toda cor usada nas telas existe em `03_design_tokens.json`.

---

## 8. Desvios do plano

| Plano (Godot 4) | Agora (UE5.8) | Motivo |
|---|---|---|
| Viewport interno de resolução fixa com escala inteira | UMG em resolução nativa com curva de DPI padrão do UE; mundo em 3D com Forward + MSAA | Decisões 1, 4 e 6 de `docs/08_decisoes_visual_3d.md` |
| Imagens 2D e tiles | Skeletal Mesh e kits Static Mesh modulares com albedo pintado | Decisões 1 e 2 |
| `tr()` e CSV de tradução | `FText` com String Tables (CSV exportado pelo Narrative) | Equivalente no UE5 |
| Fonte não definida | Source Sans 3, Cinzel e Lilita One (OFL 1.1) | Decisão deste documento; validar glifos no dia 1 |
| Posições de equipamento sem nome | 8 posições nomeadas (5 no demo) | Necessário para desenhar o inventário; Vision Lead pode renomear |
| Painel de build sem tecla | Proposta: `C` (Personagem) | Q/E/R/F/I/P/M já usados; fora do escopo |
| Cor-assinatura de área só em texto | Cor de névoa por área (2.6) | Necessário para Exponential Height Fog e telegraph |

---

## 9. Nota de substituição (16/10/2026) e chaves de token alteradas

A versão 0.1.0 (15/10/2026) usava pixel art, Paper2D, sprites de 64 × 96, viewport interno de 960 × 540, filtro nearest, escala inteira, fonte pixel e a paleta ocre (`#9B713E`, `#C7963C`, `#16130F`) como paleta principal. Isso foi substituído pelo 3D estilizado pintado à mão aprovado em 16/10/2026. O ocre sobrevive só como cor de poeira/terra dentro de cenários (por exemplo, o piso da Estrada das Lanternas, medido `#A86841`), nunca como paleta de UI.

**Chaves renomeadas** (valor novo, mesma finalidade):

| Antes | Agora |
|---|---|
| `color.base.carvao` | `color.base.pedra_noite` |
| `viewport.internal_width` / `internal_height` | `viewport.reference_width` / `reference_height` (1920 × 1080) |
| `viewport.safe_margin` | mantida, 8 → 32 |
| `motion.sprite_fps` | `motion.anim_authoring_fps` (30) |
| `juice.knockback_px` | `juice.knockback_cm` |
| `juice.shake.heavy_px` / `boss_px` / `max_px` | `juice.shake.heavy_cm` / `boss_cm` / `max_cm` |
| `juice.particles.size_px` | `juice.particles.size_cm` |
| `juice.loot_beam.*.w` / `.h` / `glow_px` | `radius_cm` / `height_cm` / `glow_radius_cm` |
| `juice.telegraph.grid_px` | `juice.telegraph.stripe_period_cm` (e novo `edge_width_cm`) |
| `color.fx.telegraph_fill` / `telegraph_fill_final` / `telegraph_edge` | movidas para `color.telegraph.fill` / `fill_final` / `edge` |
| `color.base.perigo` | mantida, `#D74437` → `#E0301E` |

**Chaves removidas:**

| Chave | Motivo |
|---|---|
| `color.base.ocre` | Paleta ocre substituída; use `color.base.pedra_clara` |
| `viewport.integer_scales`, `viewport.scale_rule` | Escala inteira deixou de existir; usar `viewport.dpi_curve` |
| `font.families.*.grid_px` | Fontes não têm mais grade |
| `color.fx.dust` (ocre `#9B713E`) | Valor trocado por `#8A7F78` (mantida a chave) |
| `color.fx.telegraph_*`, `color.fx.spark` (valor) | Telegraph em grupo próprio; `spark` trocado para `#FFE066` |

**Chaves novas:** `color.base.pedra_*`, `color.base.dourado_claro`, `color.surface.lava_fill_dark`, `color.class_gem`, `color.damage.acid/shadow`, `color.element.*`, `color.threat.*`, `color.telegraph.*`, `color.character.*`, `color.fog.*`, `color.item_frame.*`, `color.fx.player_vfx_*`, `font.families.numeric`, `viewport.dpi_*`, `icon_export.*`, `art3d.*`, `motion.interpolation` (valor novo).
**Mantidas com valores novos (mesmas chaves):** `color.surface.*`, `color.border.*`, `color.text.*`, `color.action.*`, `color.semantic.*`, `color.rarity.*`, `color.item_text.*`, `color.damage.*`, `size.*` (valores ×1,5 a ×2), `space.*` (×2), `nine_slice.*`, `elevation.*`, `z_order.*`, `motion.*`, `juice.hitstop_ms`, `juice.hit_flash_ms`, `juice.damage_number`.
