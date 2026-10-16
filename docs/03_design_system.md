# 03 — Design system e especificações de interface

Projeto: **Echoes of the Shatter** · Responsável: Art Director · 15/10/2026
Fontes: `docs/00_plano_existente.md` (seções 5, 6, 7, 9 e 10) e `docs/01_plano_execucao.md`.
Tokens em formato de máquina: `docs/03_design_tokens.json` (este documento manda; se os dois divergirem, corrigir o JSON).
Motor: **Unreal Engine 5**, interface em **UMG** (widgets em C++ + Widget Blueprint).

> Convenção de medidas: toda medida está em **pixels do viewport interno 960 × 540** (escala 1). Em tempo de execução tudo é multiplicado pela escala inteira N (×2 em 1080p, ×4 em 4K). Nunca usar meio pixel, nunca usar escala fracionária em sprite, ícone ou fonte.
> Posições de tela no formato `(x, y, l, a)` = canto superior esquerdo, largura, altura, sempre com a **âncora** indicada. Em resoluções que não são múltiplos exatos (ex.: 1440p), o espaço lógico fica maior que 960 × 540; por isso toda posição é um deslocamento a partir de uma âncora, nunca uma coordenada absoluta.

---

## 1. Princípios visuais

1. **Base escura, acento quente só onde importa.** O cenário e os painéis vivem em carvão, pedra e ocre; carmesim, laranja e dourado ficam reservados para perigo, loot, fogo, vida e ações principais (seção 9, "Paleta da referência"). Se tudo brilha, nada é lido.
2. **Pixel honesto.** Um pixel do jogo é sempre um bloco de N × N pixels da tela. Nada é filtrado, girado em ângulo arbitrário, escalado por fração ou desfocado. Bordas de 1 px, contornos de 1 px, sombras deslocadas de 1 px, sem blur.
3. **Leitura de perigo em menos de meio segundo.** Telegraph de chefe, vida baixa e inimigo de elite precisam ser entendidos pela forma e pela cor antes do texto (seção 5: telegraph de 0,7–1,2 s, sempre com forma no chão e som; seção 9: cone laranja com grade e brasas como padrão).
4. **Recompensa, não castigo.** A interface do idle mostra bônus e faixas de previsão, nunca números negativos ("+200% XP" com o Fervor, nunca "-65% XP"; seção 7, "Como apresentar"). Vermelho é para perigo real, não para "você ganhou menos".
5. **Ornamento na moldura, clareza no conteúdo.** Molduras douradas e cantos ornamentados como na referência; dentro delas, texto pergaminho sobre fundo liso, alinhado à grade de 4 px, desenhado para o texto em português (≈ 30% maior que o inglês).

---

## 2. Tokens

### 2.1 Cores

**Paleta base do plano (seção 9)** — imutável:

| Token | Hex | Papel |
|---|---|---|
| `base.carvao` | `#16130F` | Fundo do jogo, contornos de texto |
| `base.ocre` | `#9B713E` | Bordas padrão, pedra do Ato I, poeira |
| `base.dourado` | `#C7963C` | Molduras, botões secundários em destaque |
| `base.carmesim` | `#8C2326` | Botão primário, capa do herói, vinheta de vida baixa |
| `base.perigo` | `#D74437` | Telegraph, avisos de risco |
| `base.pergaminho` | `#EAD9B5` | Texto primário |

**Superfícies e bordas** (derivadas do carvão e do ocre):

| Token | Hex | Uso |
|---|---|---|
| `surface.bg_deep` | `#0E0C0A` | Barras laterais (letterbox), fundo de modal, sombra |
| `surface.bg_base` | `#16130F` | Fundo de telas de menu |
| `surface.panel` | `#211B15` | Fundo de painel |
| `surface.panel_raised` | `#2C241B` | Cartão dentro de painel, linha selecionada, botão secundário |
| `surface.panel_hover` | `#3A2F23` | Hover de linha/botão secundário |
| `surface.slot_inset` | `#110E0B` | Fundo de slot de item/habilidade (afundado) |
| `surface.scrim` | `#0E0C0A` a 75% | Escurecer o jogo atrás de modal/pausa |
| `border.subtle` | `#4A3D2E` | Divisórias, borda de slot vazio |
| `border.default` | `#9B713E` | Borda de painel simples, slot com item |
| `border.gold` | `#C7963C` | Moldura ornamentada |
| `border.gold_highlight` / `border.focus` | `#E8C06A` | Brilho de moldura, **anel de foco**, hover de slot |

**Texto** (contraste medido sobre `surface.panel` `#211B15`):

| Token | Hex | Contraste | Uso |
|---|---|---|---|
| `text.primary` | `#EAD9B5` | 12,3:1 | Corpo, valores |
| `text.secondary` | `#B8A583` | 7,1:1 | Rótulos, tipo do item |
| `text.muted` | `#9A8A6E` | 5,1:1 | Dicas, texto de sabor, versão |
| `text.disabled` | `#6B5E4B` | 2,7:1 | Só em controle desabilitado (sempre acompanhado de ícone de cadeado ou motivo) |
| `text.title` | `#E8C06A` | 9,9:1 | Títulos de tela e faixa de área |
| `text.on_gold` | `#16130F` | 6,9:1 | Texto sobre fundo dourado (selo de nível) |

**Ações:**

| Token | Hex | Notas |
|---|---|---|
| `action.primary` | `#8C2326` | Texto pergaminho sobre ele: 6,3:1 |
| `action.primary_hover` | `#A63036` | 4,9:1 |
| `action.primary_pressed` | `#5E171A` | 9,4:1 |
| `action.secondary` / `_hover` / `_pressed` | `#2C241B` / `#3A2F23` / `#16130F` | Borda `border.default` |

**Semânticas de jogo:**

| Token | Hex (claro / escuro) | Uso |
|---|---|---|
| `semantic.life` | `#C8323A` / `#6E1418`, brilho `#E86A5C` | Orbe e barra de vida |
| `semantic.mana` | `#5B8FD6` / `#23406E` | Recurso do Mago |
| `semantic.impeto` | `#E07B33` / `#6E3412` | Recurso do Guerreiro (Ímpeto) |
| `semantic.foco` | `#5FB08A` / `#22513C` | Recurso do Arqueiro (Foco) |
| `semantic.xp` | `#A78BE0` / `#3E2E66` | Barra de XP |
| `semantic.vigor` | `#9CBF6A` / `#3F5226` | Barra de Vigor da patrulha |
| `semantic.fervor` | `#E8C06A` | Ícone e texto "+200% XP" do Fervor |
| `semantic.eco` / `marco_charge` | `#6FD6C8` | Fragmentos de Eco e Cargas do Marco (a "cor da memória") |
| `semantic.danger` | `#D74437` (forma) · `#E86A5C` (texto, 5,4:1) | Perigo, erro, contrapartida de Único |
| `semantic.success` | `#7DB356` | Sucesso, comparação melhor, cura |
| `semantic.warning` | `#E8A33D` | Aviso não bloqueante (risco de recuo médio) |
| `semantic.info` | `#9FC9E0` | Dica do Tico, informação neutra |

**Raridades** (seção 6; "Normal" = Comum no plano):

| Raridade | Token | Hex | Contraste | Feixe no chão |
|---|---|---|---|---|
| Comum (Normal) | `rarity.normal` | `#D8CDB6` | 10,8:1 | Nenhum |
| Mágico | `rarity.magic` | `#7FA6F0` | 7,0:1 | Brilho de 2 px no item |
| Raro | `rarity.rare` | `#EBD25A` | 11,3:1 | Coluna 6 × 64 px |
| Único | `rarity.unique` | `#E5822E` | 6,1:1 | Coluna 10 × 128 px com pulso de 800 ms + som próprio |

Regra de acessibilidade: raridade **nunca** é só cor. O tooltip escreve a raridade ("Raro · Espada Longa"), a moldura do slot muda de forma (Mágico: cantos simples; Raro: cantos duplos; Único: cantos ornamentados), e o rótulo no chão usa o mesmo padrão.

**Texto de item e dano:** afixo `#8FB0F0`; efeito de Único `#E5822E`; contrapartida de Único `#E86A5C` com marcador `▼`; requisito não cumprido `#E86A5C`; comparação melhor `#7DB356` `▲` / pior `#E86A5C` `▼`. Dano físico `#E6E0D4`, fogo `#F0782E`, frio `#8FD3F0`, raio `#B9C8FF`, crítico `#F2E266`, dano recebido pelo jogador `#E86A5C`, cura `#7DB356`, bloqueado `#9A8A6E`.

**Efeitos:** flash de acerto `#FFFFFF`; telegraph preenchimento `#D74437` a 35% → 60%, borda `#F0782E`; brasa `#F0782E`; poeira `#9B713E`; faísca `#F2E266`; estilhaço dourado `#E8C06A`; vinheta de vida baixa `#8C2326` a 25%.

### 2.2 Tipografia

Requisito do plano (seção 10): fonte pixel testada com **ç ã õ á ñ ¿** desde o primeiro dia. Fontes escolhidas (todas gratuitas para uso comercial):

| Papel | Fonte | Licença | Grade | Alternativa |
|---|---|---|---|---|
| Corpo e números | **Pixel Operator** (Jayvee Enaguas) — Regular e Bold | CC0 1.0 | 16 px | **Pixelify Sans** (OFL 1.1, variável 400–700) |
| Micro (teclas, contadores) | **Pixel Operator 8** | CC0 1.0 | 8 px | Pixel Operator em 16 px |
| Títulos e faixa de área | **Jacquard 12** (serifada gótica pixel, Google Fonts) | OFL 1.1 | 12 px | Pixel Operator Bold 16 |

Por que: Pixel Operator tem Latin‑1 completo e desenho neutro, legível em 16 px; Jacquard 12 dá a "fonte serifada clara sobre faixa escura" da referência (item 2 da leitura da referência) sem perder o caráter pixel. **Teste obrigatório no dia 1** (Frontend + Narrative): renderizar a frase-teste abaixo em todos os estilos, em ×1, ×2 e ×4, e anexar a captura ao `docs/10_qa.md`. Se faltar qualquer glifo, trocar para a alternativa antes de construir qualquer tela.

Frase-teste: `Ação, coração e põe; Ñandú: ¿Qué pasó? ¡Olé! ÁÉÍÓÚ ÂÊÔ ÃÕ Çç àü ºª «» – — … 1.234,56 × ÷ % ▲▼`

Glifos `▲▼` e `×` podem faltar em algumas fontes: nesse caso desenhar como ícone de 8 px (`ico_arrow_up_8`, `ico_arrow_down_8`).

**Escala tipográfica** (tamanho só em múltiplos inteiros da grade da fonte):

| Estilo | Fonte | Tamanho (px) | Tamanho UMG (pt) | Entrelinha | Uso |
|---|---|---|---|---|---|
| `micro` | Pixel Operator 8 | 8 | 6 | 10 | Tecla no slot, contador de pilha, versão do build |
| `body` | Pixel Operator | 16 | 12 | 16 (+2 entre parágrafos) | Texto padrão, botões, tooltip, listas |
| `body_bold` | Pixel Operator Bold | 16 | 12 | 16 | Nome de item, cabeçalho de seção |
| `title` | Jacquard 12 | 24 | 18 | 28 | Título de tela, faixa de área |
| `display` | Jacquard 12 | 48 | 36 | 52 | Nome de chefe ao entrar, "Você caiu" |
| `damage` | Pixel Operator Bold | 16 | 12 | — | Número de dano normal |
| `damage_crit` | Pixel Operator Bold | 32 | 24 | — | Número de dano crítico |

Conversão: o Slate desenha fontes a 96 DPI, então **pt = px × 0,75**. Com a escala de DPI inteira (seção 3.4), o tamanho físico fica 16 × N px, sempre nítido.

**Largura média para orçamento de texto:** contar ≈ 7 px por caractere em `body` (≈ 8 px em `body_bold`; ≈ 5 px em `micro`). Todo campo nesta especificação traz o número máximo de caracteres por linha derivado disso. O Frontend mede a largura real com a fonte final e atualiza esta tabela se a média passar de 7,5 px.

**Regras de texto:** sem itálico (a fonte não tem; usar `text.muted` para sabor); sem caixa-alta automática (quebra acentos em algumas fontes; escrever o texto já em maiúsculas quando necessário); números com formato pt-BR (`1.234`, `1,20`, `8–12 mil`); quebrar por palavra, nunca por caractere; truncar com `…` só em nomes de save e áreas, nunca em afixos.

### 2.3 Espaçamento

Escala em px internos (grade base de 4 px; 2 px só para ajuste fino dentro de componentes):

| Token | px | Uso típico |
|---|---|---|
| `s0` | 0 | — |
| `s1` | 2 | Espaço entre slots do inventário, ícone ↔ borda do slot |
| `s2` | 4 | Espaço entre slots da barra, padding interno de chip |
| `s3` | 8 | Margem segura da tela, padding de botão, gap entre grupos |
| `s4` | 12 | Padding de tooltip, cursor ↔ tooltip |
| `s5` | 16 | Padding de painel |
| `s6` | 24 | Separação entre seções |
| `s7` | 32 | Margem de modal |
| `s8` | 48 | Respiro de menu principal |

Margem segura: 8 px em todos os lados (nada interativo fora dela).

### 2.4 Tamanhos-padrão

| Token | Valor | Token | Valor |
|---|---|---|---|
| `icon_sm` | 16 × 16 (moeda, buff, tecla, inline no texto) | `button_h` | 24 (mín. largura 96) |
| `icon_md` | 24 × 24 (status no painel, abas, regras de IA) | `row_h` | 24 (lista); 40 (linha de regra) |
| `icon_lg` | 32 × 32 (itens e habilidades — seção 9) | `tab_h` | 20 |
| `item_slot` / `skill_slot` | 36 × 36 (ícone 32 + 2 de borda) | `orb` | 56 × 56 |
| `potion_slot` | 28 × 36 | `portrait` | 40 × 40 |
| `dodge_slot` | 24 × 36 | `minimap` | 128 × 96 |
| `bar_xp_h` / `bar_thin_h` / `bar_boss_h` | 4 / 6 / 8 | `tooltip_max_w` | 224 (288 com texto grande) |
| `toast` | 240 × 28 | `scrollbar_w` | 6 |

### 2.5 Bordas, molduras e 9-slice

Sem cantos arredondados vetoriais: "raio" é desenhado no pixel art do 9-slice. Todas as molduras são texturas 9-slice em UMG (`Draw As = Box`). A margem do Box no UMG é **fração** da textura: margem = px do canto ÷ tamanho da textura.

| Peça | Textura | Canto (px) | Margem UMG | Visual |
|---|---|---|---|---|
| `nine_panel_ornate` | 24 × 24 | 8 | 0,333 | Borda dourada 2 px + filete ocre 1 px interno; canto com ornamento em losango (como a barra inferior da referência) |
| `nine_panel_plain` | 12 × 12 | 4 | 0,333 | Borda ocre 1 px, canto chanfrado de 1 px |
| `nine_button` | 16 × 16 | 4 | 0,25 | Borda 1 px + luz de 1 px em cima / sombra de 1 px embaixo |
| `nine_slot` | 36 × 36 | 3 | 0,083 | Inset: sombra 1 px em cima/esquerda, luz 1 px embaixo/direita; 3 variantes de canto por raridade |
| `nine_tooltip` | 16 × 16 | 4 | 0,25 | Fundo `#16130F` a 95%, borda na cor da raridade |
| `nine_bar_frame` | 12 × 12 | 3 | 0,25 | Moldura de barra |
| `nine_toast` | 12 × 12 | 4 | 0,333 | Faixa escura com filete na cor semântica à esquerda (2 px) |

**Regra do 9-slice:** o Slate **estica** as bordas e o centro. Portanto as bordas devem ser uniformes no eixo do estiramento (linhas retas); ornamentos ficam **só nos cantos**. Ornamento repetido ao longo da borda exige peça separada (`Image` com `Tiling = Horizontal`) sobreposta.

### 2.6 Ícones

| Tamanho | Onde | Regras |
|---|---|---|
| 32 × 32 | Itens, habilidades, sigilos, livros (seção 9) | Silhueta legível em 1 bit (testar em preto puro); contorno escuro `#0E0C0A` de 1 px por fora; luz vinda de cima-esquerda; até 12 cores por ícone, sempre da paleta |
| 24 × 24 | Abas, objetivo da expedição (XP/Ouro/Materiais), condições de regra de IA, status no relatório | Mesmas regras; desenhados à mão, nunca reduzidos do 32 |
| 16 × 16 | Ouro, Carga do Marco, Fragmento de Eco, buffs/debuffs no HUD, glifos de tecla e mouse (`LMB`, `RMB`), alerta | 2–4 cores; contorno de 1 px obrigatório |

Glifos de entrada: `ico_key_<tecla>_16` (tecla com moldura) e `ico_mouse_left_16`, `ico_mouse_right_16`, gerados a partir do mapeamento atual (mudam quando o jogador remapeia).

Nomes de arquivo: `T_Icon_<categoria>_<id>_<tam>` (ex.: `T_Icon_Skill_warrior_iron_cut_32`), usando o ID estável de conteúdo.

### 2.7 Sombras e contornos

- **Texto de interface sobre painel:** sombra sólida `#0E0C0A`, deslocamento (1, 1), sem blur (`Shadow Offset = (1,1)` no `FSlateFontInfo`, cor opaca).
- **Texto no mundo** (dano, nome de item no chão, nome de elite): contorno de 1 px `#0E0C0A` (`Outline Size = 1`, `Outline Color = #0E0C0A`). Contorno de fonte no Slate é em pixels físicos: usar `OutlineSize = N` para dar 1 px interno.
- **Painel flutuante** (tooltip, modal): sombra sólida `#0E0C0A` a 60%, deslocamento (2, 2) — desenhada como uma segunda imagem 9-slice atrás, não como efeito.
- **Sprites:** contorno escuro de 1 px já pintado no sprite; elite ganha contorno extra de 1 px na cor do modificador (shader de contorno, sem blur).
- Proibido: blur, glow suave, sombra com degradê, Background Blur do UMG.

### 2.8 Movimento da interface

- Abrir/fechar painel: alpha 0→1 em 120 ms + deslocamento inteiro de 8 px (passos de 1 px). **Nunca animar escala** (gera tamanhos fracionários).
- Tooltip: atraso de 150 ms, aparece sem animação.
- Toast: aparece com deslocamento de 8 px, fica 3 s, some em 200 ms.
- Faixa de área ("Cripta Partida"): 3 s visível, depois some em 200 ms.
- Sprites a 12 fps (10–12 aceitável); interpolação de posição na UI sempre em degraus de 1 px interno.

---

## 3. Pixel-perfect no Unreal Engine 5

### 3.1 Texturas

| Tipo | Compression | Mip Gen | Filter | LOD Group | Outros |
|---|---|---|---|---|---|
| Sprites, tiles, efeitos (Paper2D) | `UserInterface2D (RGBA)` (ou `Default` só se o tamanho de build apertar, validando artefatos) | `NoMipmaps` | `Nearest` | `2D Pixels (unfiltered)` | sRGB ligado; `Never Stream` ligado; usar a ação **Sprite Actions → Apply Paper2D Texture Settings** ao importar |
| UI (molduras, ícones, slots) | `UserInterface2D (RGBA)` | `NoMipmaps` | `Nearest` | `UI` | sRGB ligado; `Never Stream`; sem potência de 2 obrigatória |
| Fontes | (Font Face) | — | — | — | ver 3.5 |

- Garantir o filtro por grupo também em `Config/DefaultDeviceProfiles.ini` (grupos `TEXTUREGROUP_Pixels2D` e `TEXTUREGROUP_UI` com `MinMagFilter=point`, `MipFilter=point`), para que nenhuma textura escape com filtro linear.
- PNG de origem sem perfil de cor e sem pré-multiplicação de alpha; alpha só 0 ou 255 em sprites (máscara), alpha parcial só em efeitos.

### 3.2 Paper2D e mundo

- **Pixels per unit = 1** (Project Settings → Paper2D → Default Pixels Per Unreal Unit = 1): 1 px de sprite = 1 uu. Todo sprite com pivô nos **pés** (`Pivot Mode = Bottom Center`, ajustado ao contato com o chão para personagens de 64 × 96 e inimigos de 48 × 72).
- Material de sprite: `MaskedUnlitSpriteMaterial` (Paper2D) para personagens e tiles; `TranslucentUnlitSpriteMaterial` só para efeitos. **Unlit** em tudo: a iluminação dramática é pintada no sprite e em camadas de luz 2D (sprites aditivos), não calculada.
- Recomendação para o Tech Lead: plano do jogo no eixo XZ com a câmera olhando ao longo de Y; ordenação de profundidade pela posição dos pés (quem está mais abaixo na tela fica na frente). Tiles isométricos 64 × 32 alinhados à grade de 1 uu.
- **Snap de render:** a lógica pode usar float, mas a posição desenhada (componente de sprite, câmera, números de dano) é arredondada para inteiro de 1 uu a cada frame. Câmera segue o jogador com arredondamento inteiro (sem "tremer" sub-pixel).

### 3.3 Câmera e resolução interna

- `CameraComponent`: **Projection Mode = Orthographic**, `Ortho Width = 960` (com 1 px = 1 uu, mostra exatamente 960 px internos de largura), `Constrain Aspect Ratio` ligado em 16:9.
- **Caminho principal (1080p, 4K, 540p — múltiplos exatos):** renderizar a cena com resolução interna e ampliar com vizinho mais próximo:
  - `r.ScreenPercentage = 100 / N` (50 em 1080p, 25 em 4K), calculado pelo jogo ao mudar de resolução;
  - `r.Upscale.Quality = 0` (ampliação Nearest);
  - `r.TemporalAA.Upsampling = 0` e sem TSR/DLSS/FSR.
  - A UI (Slate) é desenhada **depois** da ampliação, na resolução nativa, com escala de DPI = N (3.4). Resultado: mundo em 960 × 540 nítido e texto nítido.
- **Resoluções não múltiplas (1440p, 1366 × 768, ultrawide):** opção em Vídeo → "Escala de pixels":
  - **Inteira com bordas** (padrão): `N = floor(min(L/960, A/540))`; desenhar o mundo num Render Target de 960 × 540 (filtro Nearest, via `SceneCapture2D` ortográfica) exibido num `Image` centralizado de 960N × 540N; o resto da tela em `surface.bg_deep`.
  - **Preencher (suave):** mesma imagem esticada para caber, filtro Nearest + um passo de suavização 1 px (aceito pelo plano: "1440p com barras ou escala suave").
- Validar no editor no primeiro dia qual dos dois métodos tem melhor custo; o critério é o teste de pixel da seção 7.

### 3.4 Escala da UI (DPI)

- Project Settings → Engine → User Interface:
  - `DPI Scale Rule = Shortest Side`;
  - **Curva de DPI em degraus** (chaves com interpolação **Constant**): 0 → 1,0; 540 → 1,0; 1080 → 2,0; 1620 → 3,0; 2160 → 4,0. Resultado: a UI sempre usa escala inteira (1440p → ×2, com mais espaço lógico; 4K → ×4).
  - `Application Scale = 1,0`.
  - `Render Focus Rule = Never` (o foco é desenhado pelos próprios widgets, ver 5.1).
- No UMG Designer, pré-visualizar em **960 × 540 com DPI 1,0**, e conferir também em 1280 × 720 (caso 1440p).
- Todos os widgets usam âncoras; nada de `Scale Box` com escala livre nem `Render Transform` com escala não inteira.
- **Texto grande** (acessibilidade): o corpo passa a ser desenhado com cada pixel da fonte ocupando N+1 pixels físicos: tamanho lógico = 16 × (N+1)/N px (×1 → 32; ×2 → 24; ×3 → 21,33; ×4 → 20). Continua nítido em qualquer N. Tooltip passa a 288 px de largura e painéis de texto ganham `ScrollBox`.

### 3.5 Fontes no UE5

- Importar TTF como **Font Face**: `Hinting = Monochrome` (sem antialiasing), `Loading Policy = Inline` (pequenas), e, se a versão do motor oferecer, `Rasterization Mode = Bitmap` (não Distance Field).
- Composite Font com subfamílias Regular/Bold; fallback para a fonte alternativa da tabela 2.2.
- Tamanho só de 6/12/18/24/36 pt (equivalentes 8/16/24/32/48 px); proibido outro valor fora do "texto grande".
- Sombra/contorno conforme 2.7.

### 3.6 Pós-processamento (Post Process Volume com `Infinite Extent (Unbound)` + Project Settings)

| Configuração | Valor |
|---|---|
| Anti-Aliasing Method (Project) | **None** (`r.AntiAliasingMethod 0`) |
| Motion Blur | Desligado (Project → `Motion Blur` off; PPV Amount 0) |
| Auto Exposure | Desligado (Project → `Auto Exposure` off; PPV Metering Mode **Manual**, Exposure Compensation 0, Min/Max EV100 = 0) |
| Bloom, Lens Flare, Vignette, Film Grain, Chromatic Aberration | 0 / desligados (brilhos são pintados) |
| Local Exposure | Highlight/Shadow Contrast = 1 (neutro) |
| Dynamic GI / Reflections | None (Lumen desligado; tudo unlit) |
| Shadows | Desligadas no mundo 2D |
| Tonemapper | Cores do sprite devem sair iguais ao PNG. Usar um material de pós-processo com `Blendable Location = Replacing the Tonemapper` que só aplica sRGB à cor da cena; ou `ShowFlag.Tonemapper 0` como teste rápido |
| Screen Space AO, Depth of Field, Contact Shadows | Desligados |
| Sharpen (`r.Tonemapper.Sharpen`) | 0 |

### 3.7 Outros

- **Cursor por hardware** (Project → User Interface → Hardware Cursors): cursor 16 × 16 desenhado em pixel art, exportado em ×1, ×2, ×3, ×4 (`Cursor_Default@1x.png` etc.). Variantes: padrão, ataque (sobre inimigo), coletar (sobre item), conversar (sobre NPC), arrastar item.
- **Fixed frame / VSync:** 60 FPS como alvo; animações de UI baseadas em tempo, não em frame.
- **Rendering:** desligar `Mobile HDR` não se aplica; desligar `Virtual Shadow Maps` e `Nanite` para o projeto 2D (economia de memória).

---

## 4. Especificações de interface

Telas do protótipo: HUD de combate (4.1), inventário e tooltip (4.2), Expedição (4.3), Relatório de expedição (4.4), menu principal e slots de save (4.5), pausa e opções com remapeamento (4.6). Toda string vem de chave de localização (String Table / `FText`), nunca escrita no widget.

Atalhos globais: `Esc` fecha o painel do topo da pilha; sem painel aberto, abre a Pausa. `Enter` confirma o botão primário do painel ativo. `Tab`/`Shift+Tab` e setas movem o foco. Duplo clique = ação principal.

### 4.1 HUD de combate — `WBP_HUD` / `UShatterHUDWidget`

```
 0                                                                         960
 ┌[retrato][Lv12][Fervor +200% XP]──────────[ Tecelã de Cascalho ═══════ ]──[ minimapa ]┐
 │[vida ▬▬▬▬][recurso ▬▬▬][buffs..]                                         [ 128 × 96  ]│
 │                                                                     [Ouro][Cargas]  │
 │                              (mundo)                                    [toasts ↓]   │
 │                                                                                      │
 │            ┌─────────────────────────────────────────────────┐                       │
 │            │(VIDA)  [LMB][RMB][ Q ][ E ][ R ][ F ] [⤳] [1][2] (RECURSO)│              │
 │            │═══════════════════ XP ══════════════════════════│                       │
 └────────────┴─────────────────────────────────────────────────┴───────────────────────┘540
```

| Bloco | Âncora | Posição `(x, y, l, a)` | Conteúdo |
|---|---|---|---|
| Retrato | Topo-esquerda | (8, 8, 40, 40) | Retrato da classe em moldura dourada; selo de nível 16 × 12 sobreposto em (36, 40) com texto `micro` `text.on_gold` sobre dourado |
| Barras finas | Topo-esquerda | vida (52, 12, 96, 6); recurso (52, 22, 96, 4) | Redundantes com os orbes (referência, item 1); some com a opção "HUD compacto" |
| Fervor | Topo-esquerda | (52, 30, 120, 16) | Ícone 16 + "+200% XP" em `semantic.fervor`; só aparece no jogo manual. Hover: tooltip "Fervor do Recuperador: XP ×3, Ouro e materiais ×1,25, chance de Raro ×2, Únicos e Fragmentos de Eco" |
| Buffs/debuffs | Topo-esquerda | a partir de (8, 52), ícones 16 com gap 2, até 10 por linha, 2 linhas | Contador de segundos `micro` no canto inferior direito; debuff com borda `semantic.danger` |
| Barra de chefe | Topo-centro | nome (280, 8, 400, 16) em `body_bold`; barra (280, 28, 400, 8) | Vida em `semantic.life`; marcas de fase (1 px `border.gold_highlight`) em 66% e 33%; só em arena de chefe |
| Faixa de área | Topo-centro | (240, 64, 480, 40) | Ao entrar na área: nome em `title` `text.title` sobre faixa escura com filete dourado; 3 s; depois o nome fica em `micro` sob o minimapa |
| Minimapa | Topo-direita | (824, 8, 128, 96) | Isométrico, moldura ornamentada; `M` abre o mapa grande |
| Moedas | Topo-direita | Ouro (824, 108, 64, 16); Cargas (892, 108, 60, 16) | Ícone 16 + número `body`; Cargas em `semantic.marco_charge` com formato `7/12` |
| Toasts | Topo-direita | coluna em (712, 132, 240, —), até 4 empilhados, gap 4 | Ver componente 5.7 |
| Barra inferior | Base-centro | moldura (240, 460, 480, 72) | Moldura `nine_panel_ornate` |
| Orbe de vida | Base-centro | (248, 464, 56, 56) | Preenchimento de baixo para cima em `semantic.life` sobre `life_dark`; linha de nível 1 px `life_highlight`; valor `142/180` em `micro` sob o orbe ao passar o mouse ou com "Sempre mostrar valores" |
| Habilidades | Base-centro | 6 slots 36 × 36 a partir de (312, 474), gap 4 → LMB, RMB, Q, E, R, F | Ver `WBP_SkillSlot` (5.5). No demo, R e F aparecem com cadeado |
| Esquiva | Base-centro | (556, 474, 24, 36) | Ícone de esquiva + 3 pips de carga 4 × 4 embaixo (cheio = `text.primary`, vazio = `border.subtle`, recarregando = preenchimento vertical) ; tecla `Espaço` em `micro` |
| Poções | Base-centro | P1 (588, 474, 28, 36); P2 (620, 474, 28, 36) | Ícone + quantidade `micro` no canto superior direito; tecla `1`/`2` embaixo; vazio = ícone em 40% e número `semantic.danger` |
| Orbe de recurso | Base-centro | (656, 464, 56, 56) | Cor por classe: Ímpeto, Foco ou Mana |
| XP | Base-centro | (248, 524, 464, 4) | `semantic.xp`; marcas a cada 10%; hover: "Nível 12 · 3.420 / 5.100 XP (67%)" |
| Vinheta de vida baixa | Tela toda | — | Abaixo de 30% de vida: borda `#8C2326` a 25%, 24 px, pulso de 1 s (alpha 15–25%); desligável com "Reduzir flashes" |

**Estados do HUD:** combate (completo); Refúgio (sem barra de chefe; habilidades visíveis mas sem cooldown); arena de chefe (barra de chefe + nome em `display` por 2 s na entrada); morte (HUD some em 200 ms; tela "Você caiu" em `display`, botão "Voltar ao checkpoint" — sem penalidade, seção 5); painel aberto (HUD continua visível; painéis não cobrem a barra inferior); cinemática (HUD oculto).

**Números de dano** (mundo projetado na tela, `WBP_DamageNumber` em pool de 64):

| Tipo | Estilo | Cor | Movimento |
|---|---|---|---|
| Normal | `damage` 16 px | Pelo tipo (físico/fogo/frio/raio) | Sobe 12 px em 600 ms em degraus de 1 px; some nos últimos 200 ms |
| Crítico | `damage_crit` 32 px + "!" | `#F2E266` | Fica parado 120 ms, depois sobe 12 px; deslocamento lateral aleatório de ±8 px |
| Dano recebido | `damage` 16 px | `#E86A5C` | Sobe sobre o jogador |
| Cura | `damage` 16 px com "+" | `#7DB356` | Igual |
| Bloqueado / Evadido | `body` 16 px "Bloqueado" / "Evadido" | `#9A8A6E` | Igual |

Golpes no mesmo alvo dentro de 100 ms somam num único número. Formato: `1.234` (pt-BR), sem casas decimais. Contorno 1 px `#0E0C0A`.

**Texto mais longo (pt-BR):** "Fervor do Recuperador" (tooltip), "+200% XP" (16 px de ícone + 8 caracteres ≈ 72 px; cabe em 120). Nome de chefe mais longo: "Tecelã de Cascalho" (18 caracteres ≈ 144 px em `body_bold`; cabe em 400). Faixa de área mais longa: "Armazém de Cinzas" / "Túneis do Voto" (≤ 18 caracteres em `title` ≈ 13 px/caractere ≈ 234 px; cabe em 480).

**Interação:** clique no orbe/barra = nada; hover em habilidade = tooltip da habilidade (nome, custo, recarga, tags, sigilos); arrastar habilidade do livro para o slot (painel de habilidades, fora deste escopo). Itens no chão mostram rótulo (Mágico ou acima) e `Alt` mostra todos.

### 4.2 Inventário — `WBP_Inventory` / `UShatterInventoryWidget` (tecla `I`)

Painel lateral à direita, deixando o personagem visível à esquerda e a barra inferior livre.

| Bloco | Âncora | Posição | Conteúdo |
|---|---|---|---|
| Painel | Direita (topo-direita) | (528, 8, 424, 444) | `nine_panel_ornate` |
| Cabeçalho | — | (544, 16, 392, 24) | "Inventário" em `title`; botão fechar 16 × 16 em (920, 20) |
| Equipamento | — | (544, 48, 392, 168) | Silhueta da classe ao centro (64 × 96) e 8 slots 36 × 36 ao redor: Arma (esq.-meio), Mão secundária (dir.-meio), Elmo (topo), Peitoral (centro abaixo do elmo), Luvas (esq.-baixo), Botas (base), Amuleto (dir.-topo), Anel (dir.-baixo). Demo: 5 posições ativas (Arma, Elmo, Peitoral, Botas, Anel), as outras com cadeado. Slot vazio mostra ícone-fantasma da posição em `border.subtle` |
| Abas | — | (544, 224, 392, 20) | "Mochila" · "Baú compartilhado" (só no Refúgio; fora dele aparece desabilitada com tooltip "Disponível no Refúgio do Marco") |
| Grade | — | (551, 248, 378, 150) | 10 × 4 slots de 36 × 36, gap 2 (itens ocupam 1 slot) |
| Recursos | — | (544, 404, 392, 40) | Linha 1: Ouro, Lascas, Cinzas de Memória; linha 2: Fragmentos de Eco `12/50`, Cargas do Marco. Ícone 16 + número; hover com nome e explicação |

**Interação (teclado e mouse):**
- Clique esquerdo: pega o item (fica preso ao cursor, slot de origem a 40%); clique em outro slot: troca; clique fora do painel sobre o mundo: pergunta "Largar Lâmina do Voto Quebrado no chão?".
- Clique direito: equipar/desequipar (vai para a posição certa; se ocupada, troca).
- `Shift` segurado: tooltip de comparação lado a lado. `Ctrl+Clique`: mover entre Mochila e Baú. `Alt+Clique`: marcar como lixo (ícone 8 px), "Reciclar marcados" no Bram.
- Teclado: setas movem o foco pela grade e pelos slots de equipamento; `Enter` = clique direito; `Espaço` = pegar/soltar; `Shift` segurado também compara com foco por teclado; `Esc`/`I` fecha.
- Requisito não cumprido: slot com hachura diagonal `semantic.danger` a 25% e equipar recusado com toast "Requer nível 12".

**Estados:** normal; item preso ao cursor; mochila cheia (toast "Mochila cheia" + contador `40/40` em `semantic.warning`); Baú indisponível; slot bloqueado (demo).

**Tooltip de item — `WBP_ItemTooltip` / `UShatterItemTooltip`:**

```
┌───────────────────────────────┐  largura máx. 224 (≈ 28 caracteres por linha)
│ Lâmina do Voto Quebrado       │  body_bold, cor da raridade, até 2 linhas
│ Único · Espada Longa          │  text.secondary
├───────────────────────────────┤  divisória 1 px border.subtle
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
│ "Jurou proteger um rei que…"  │  text.muted (sabor, só Único)
├───────────────────────────────┤
│ [RMB] Equipar  [Shift] Comparar│ micro + glifos de tecla atuais
└───────────────────────────────┘
```

- Fundo `#16130F` a 95%, borda 1 px na cor da raridade, cantos conforme a raridade (2.1), padding 12, gap de 4 entre linhas de grupos, 8 entre grupos.
- Posição: 12 px à direita e abaixo do cursor; se passar da margem segura, vira para a esquerda/acima; nunca cobre o slot de origem; com foco por teclado, ancora ao lado do slot focado.
- Comparação (`Shift`): segundo tooltip à esquerda com cabeçalho "Equipado" em `micro`; no tooltip do item novo, cada atributo mostra a diferença: `▲ +6` em `compare_better`, `▼ −4` em `compare_worse`.
- Nome com gênero gramatical correto (seção 10, localização): exemplos de teste "Espada Flamejante", "Lança Sombria".
- **Texto mais longo para testar:** nome "Anel Flamejante do Recuperador Paciente" (40 caracteres → 2 linhas), afixo "+18% de dano de projétil contra inimigos atordoados" (51 caracteres → 2 linhas), efeito de Único com 3 linhas. Altura máxima do tooltip: 400 px; acima disso, o texto de sabor é cortado primeiro.

### 4.3 Expedição — `WBP_Expedition` / `UShatterExpeditionWidget` (falar com a Ilsa)

Painel modal sobre `surface.scrim`. Fluxo da seção 7: área dominada → objetivo → regras de IA → duração → previsão → iniciar.

| Bloco | Posição (âncora: centro) | Conteúdo |
|---|---|---|
| Painel | (80, 24, 800, 492) | `nine_panel_ornate` |
| Cabeçalho | (96, 32, 768, 28) | "Expedição" em `title`; à direita: "Cargas do Marco: 7/12" com ícone e "Vigor: descansado" |
| Coluna A — Áreas dominadas | (96, 68, 240, 392) | Lista com `ScrollBox`, linhas de 40 px: nome da área (`body_bold`), "Níveis 2–4 · Dominada" (`text.secondary`), ícone de selo. Áreas não dominadas aparecem desabilitadas com cadeado e "Vença a área na mão, com o chefe, para liberar" |
| Coluna B — Plano | (352, 68, 256, 392) | **Objetivo**: 3 botões segmentados com ícone 24 (XP · Ouro · Materiais). **Duração**: slider 1–12 h em passos de 1 h, rótulo "4 h · gasta 4 cargas"; abaixo, 12 barrinhas 16 × 8 coloridas por Vigor (h1–4 `vigor` 100%, h5–8 a 70% de alpha, h9–12 a 40%) com legenda "Descansado até 4 h, depois cansa". **Previsão** (cartão `panel_raised`): "8–12 mil de XP", "1,1–1,6 mil de Ouro", "Raros: até 4"; "Risco de recuo: Médio" com selo `semantic.warning` e motivo "Falta resistência a fogo" |
| Coluna C — Regras de IA | (624, 68, 240, 392) | Título "Regras (em ordem)" + contador `4/6`. Até 6 `WBP_RuleRow` (40 px, gap 4). Botão "+ Adicionar regra" (desabilitado com 6). Última linha fixa, não removível: "Senão: ataque básico" em `text.muted` |
| Aviso de compatibilidade | (96, 468, 480, 40) | Faixa `panel_raised` com filete `semantic.danger` (bloqueia) ou `semantic.warning` (não bloqueia). Ex.: "Raio do Arquivo ainda não funciona em patrulha. Troque a habilidade para iniciar." |
| Botões | (592, 476, 272, 24) | "Cancelar" (secundário, 96) · "Iniciar expedição" (primário, 168) |

**Linha de regra (`WBP_RuleRow`):** número de ordem (16 px) · linha 1: "Se: Vida abaixo de 35%" (combo de condição + valor) · linha 2: "Faça: Usar poção" (combo de ação) · alças ▲▼ e "×" à direita (16 px cada). Condições usam ícone 24 (vida, recurso, inimigos próximos, elite, chefe). Valores percentuais em passos de 5%.

**Estados:**
- Nenhuma área dominada: colunas B e C desabilitadas; mensagem central "Vença o Guardião da Cripta para instalar o primeiro Marco de Retorno."
- Cargas insuficientes: o slider para no máximo possível; texto "Cargas para até 3 h. Jogue na mão para ganhar mais (+1 por área limpa, +2 por chefe)".
- Incompatível: "Iniciar expedição" desabilitado + aviso vermelho com o nome da habilidade/Único.
- Outro personagem já em expedição: tela mostra só o card da expedição em andamento ("Bram está patrulhando a Cripta Partida · faltam 2 h 14 min") e o botão "Ver relatório quando voltar".
- Confirmação: ao iniciar, modal curto "A build e as regras ficam congeladas até o fim. Iniciar?" com "Iniciar" e "Voltar". Depois: "Feche o jogo quando quiser; o Tico traz o relatório."
- Nunca mostrar "−65%" ou comparação negativa com o manual; a previsão é absoluta.

**Interação:** setas/Tab percorrem as colunas A → B → C → botões; `Enter` seleciona; na coluna C, `Ctrl+↑/↓` move a regra, `Delete` remove (com desfazer por 5 s via toast "Regra removida · Desfazer (Ctrl+Z)"); arrastar a linha pela alça com o mouse; roda do mouse no slider muda 1 h.

**Texto mais longo:** regra "Se: 3 ou mais inimigos a até 4 m / Faça: Usar Fenda de Pedra" (cada linha ≤ 30 caracteres ≈ 210 px; combo com 196 px úteis → quebra em 2 linhas: a linha de regra cresce para 56 px); aviso "Raio do Arquivo ainda não funciona em patrulha. Troque a habilidade para iniciar." (80 caracteres ≈ 560 px → 2 linhas em 464 px úteis); nome de área "Armazém de Cinzas".

### 4.4 Relatório de expedição — `WBP_ExpeditionReport` / `UShatterExpeditionReportWidget`

Aparece ao abrir o jogo (ou ao falar com o Tico) quando há expedição terminada. Coletar é obrigatório antes de fechar (a coleta é o salvamento; seção 10).

| Bloco | Posição (âncora: centro) | Conteúdo |
|---|---|---|
| Painel | (80, 24, 800, 492) | `nine_panel_ornate` |
| Cabeçalho | (96, 32, 768, 28) | Retrato do Tico 24 + "Relatório · Cripta Partida" em `title` |
| Resumo | (96, 68, 368, 104) | Grade 2 × 3 de números grandes (`body_bold`) com rótulo `text.secondary`: Tempo efetivo "7 h 40 min de 8 h"; Encontros vencidos "212"; Poções gastas "31"; XP "+9.840"; Ouro "+1.312"; Motivo da parada (ícone + "Duração concluída" / "Recuou: sem poções" / "Relógio do PC voltou; encerrada no último ponto") |
| Vigor por hora | (96, 180, 368, 48) | 12 colunas 24 × 32 (uma por hora), altura = XP da hora, cor `semantic.xp`; hora sem patrulha em `border.subtle`; hover mostra o recibo da hora |
| Recibos | (96, 236, 368, 224) | Lista resumida agrupada por hora (`ScrollBox`): "Hora 3 · 27 encontros · 4 poções · 1 recuo parcial"; clique expande os encontros ("Sentinela Oca ×3 · vencido em 18 s · 1 poção") |
| Loot | (480, 68, 384, 196) | Grade 10 × 5 de slots 36 (rolagem se exceder): Raros primeiro, depois Mágicos, Comuns, Páginas, Sigilos; materiais e Ouro em linha própria. Tooltip de item igual ao inventário |
| Dica | (480, 272, 384, 72) | Cartão com filete `semantic.info`: "Sua cura falhou 3 vezes; tente subir o limiar para 45%." + botão terciário "Ajustar regra" (abre a Expedição com a regra focada) |
| Convite | (480, 352, 384, 72) | Cartão dourado: "Jogando esta rota você teria Fervor e chance de Únicos." + botão secundário "Jogar esta rota agora" |
| Botões | (592, 476, 272, 24) | "Coletar tudo" (primário); "Coletar e nova expedição" (secundário) |

**Estados:**
- Calculando: painel com a animação do Tico correndo (sprite 32 × 32, 8 quadros) e "O Tico está voltando…"; barra indeterminada; meta < 2 s; botões ocultos.
- Pronto: contagem animada dos números (0 → valor em 600 ms, em passos inteiros); Raros ganham brilho de 2 px por 400 ms ao aparecer.
- Mochila cheia: loot excedente vai para o Baú; aviso `semantic.info` "12 itens foram para o Baú compartilhado".
- Relógio voltou: aviso `semantic.warning` em linguagem neutra, sem tom de acusação.
- Coletado: botões trocam para "Fechar"; não é possível coletar de novo.
- Nunca usar vermelho para quantidades menores; só para recuo por falta de recurso.

**Texto mais longo:** motivo "Recuou: faltou resistência a fogo" (33 caracteres ≈ 231 px — ocupa a célula inteira de 368, por isso a célula de motivo tem largura total na 3ª linha); dica com até 3 linhas (≤ 150 caracteres).

**Interação:** `Enter` = Coletar tudo; Tab percorre loot → dica → convite → botões; `Esc` não fecha antes de coletar (mostra toast "Colete os itens antes de sair").

### 4.5 Menu principal e slots de save

**Menu principal — `WBP_MainMenu` / `UShatterMainMenuWidget`**

| Bloco | Âncora | Posição | Conteúdo |
|---|---|---|---|
| Fundo | Tela toda | — | Cena pixel art do Refúgio do Marco à noite (lanterna e sino animados a 12 fps), mais escura à esquerda |
| Logo | Topo-esquerda | (48, 48, 320, 96) | Logo "Echoes of the Shatter" (arte própria, não fonte) |
| Menu | Esquerda-centro | coluna em (48, 200, 200, —), botões 24 de altura, gap 8 | "Continuar" (primário, com legenda `micro` "Guerreiro · Nível 12 · Pátio dos Marcos"), "Novo jogo", "Carregar", "Opções", "Créditos", "Sair" |
| Selo de expedição | Ao lado de "Continuar" | +8 px à direita | Ícone 16 + "Expedição pronta" em `semantic.eco` quando houver relatório |
| Versão | Base-direita | (752, 524, 200, 8) | `micro` `text.muted` "0.3.1-ea+a1b2c3" |
| Pasta de logs | Base-esquerda | (8, 516, 160, 16) | Link terciário "Abrir pasta de logs" |

Estados: primeira execução (sem "Continuar" e sem "Carregar"; "Novo jogo" é primário); save danificado recuperado (toast `semantic.warning` "O save principal estava danificado. Carregamos o backup de 15/10/2026 21:35.").

**Slots de save — `WBP_SaveSlots` / `UShatterSaveSlotsWidget`**: painel centralizado (200, 64, 560, 412) com título "Carregar jogo" e 3 cartões `WBP_SaveSlotCard` de 560 × 112 (gap 8).

Cartão (padding 12): retrato 40 × 40 à esquerda; à direita:
- Linha 1: nome do personagem (`body_bold`) + selo de nuvem 16 ("Steam Cloud").
- Linha 2: "Guerreiro · Nível 12" · "Pátio dos Marcos".
- Linha 3: "Tempo de jogo: 14 h 32 min" · "Salvo em 15/10/2026 21:40" (formato do idioma; em pt-BR `dd/MM/aaaa HH:mm`).
- Linha 4 (se houver): "Em expedição · faltam 3 h 05 min" (`text.secondary`) ou "Expedição pronta para coletar" (`semantic.eco`).
- Botões à direita: "Carregar" (primário), "Apagar" (texto, `semantic.danger_text`).

Estados do cartão: normal; hover/foco (borda `border.focus`); vazio ("Espaço vazio" + botão "Novo jogo"); danificado com backup ("Recuperado do backup de 15/10 21:35" com ícone de aviso); danificado sem backup (desabilitado, "Não foi possível ler este save. Abra a pasta de logs para relatar."); versão nova de save (migração automática, sem aviso).

Apagar: modal de confirmação "Apagar Bram, Guerreiro nível 12? Isto não pode ser desfeito." com botão "Apagar" que exige **segurar 1 s** (barra de preenchimento no botão) — evita apagar por acidente.

Interação: ↑/↓ entre cartões, `Enter` carrega, `Delete` apaga (abre confirmação), `Esc` volta.

**Texto mais longo:** "Expedição pronta para coletar" (29 caracteres ≈ 203 px); "Arqueiro · Nível 30 · Mirante Partido" (37 caracteres ≈ 259 px); área útil do texto 380 px.

### 4.6 Pausa e opções

**Pausa — `WBP_PauseMenu` / `UShatterPauseMenuWidget`** (`Esc`): `surface.scrim` sobre o jogo (o jogo pausa; single-player). Coluna central (380, 160, 200, —): "Continuar" (primário), "Opções", "Abrir pasta de logs", "Menu principal", "Sair do jogo". Sair e Menu principal mostram "O jogo é salvo automaticamente. Sair agora?" com "Sair" e "Ficar". Esc fecha a pausa.

**Opções — `WBP_Options` / `UShatterOptionsWidget`**: painel (80, 24, 800, 492); abas no topo (96, 32): Jogo · Vídeo · Áudio · Controles · Acessibilidade. Conteúdo em lista de linhas de 24 px: rótulo à esquerda (largura 320), controle à direita (largura 400). Rodapé: "Restaurar padrão" (texto), "Cancelar" (secundário), "Aplicar" (primário). Mudanças de vídeo pedem confirmação com contagem regressiva de 15 s ("Manter estas configurações?").

| Aba | Itens |
|---|---|
| Jogo | Idioma (Português (Brasil), English, Español); Mostrar valores nos orbes; HUD compacto; Mostrar números de dano; Rótulos de itens no chão (Mágico+ / Raro+ / Todos) |
| Vídeo | Modo de tela (Janela, Tela cheia sem bordas, Tela cheia); Resolução; Escala de pixels (Inteira com bordas / Preencher suave); VSync; Limite de FPS (30/60/120/Sem limite) |
| Áudio | Geral, Música, Efeitos, Interface (sliders 0–100 em passos de 5) |
| Controles | Remapeamento (abaixo) |
| Acessibilidade | Texto grande; Tremor de tela (Normal / Reduzido / Desligado); Reduzir flashes; Reduzir sangue; Daltonismo: reforço de forma nas raridades (sempre ligado) e paleta alternativa de telegraph (laranja → amarelo com hachura) |

**Remapeamento — `WBP_KeyBindRow` / `UShatterKeyBindRow`**: tabela com colunas Ação (240) · Principal (120) · Alternativa (120). Ações e padrão do plano (seção 10): Mover para cima/baixo/esquerda/direita (W/S/A/D), Ataque básico (botão esquerdo), Habilidade 1–5 (botão direito, Q, E, R, F), Esquiva (Espaço), Poção 1 e 2 (1, 2), Inventário (I), Árvore passiva (P), Mapa (M), Mostrar itens no chão (Alt), Comparar item (Shift).
- Clicar na célula (ou `Enter` com foco): célula vira "Pressione uma tecla… (Esc cancela)" com borda `border.focus` piscando a 2 Hz.
- Conflito: "Q já está em Habilidade 2. Trocar as duas?" → "Trocar" / "Cancelar".
- `Esc` não é remapeável (fica sempre como pausa/voltar); "Mirar" é sempre o mouse.
- Ação sem tecla: célula com "—" em `semantic.warning` e aviso no rodapé "Ação sem tecla: Poção 2".
- Glifos de tecla do HUD e dos tooltips atualizam na hora.
- Recomendação ao Frontend: Enhanced Input com *Player Mappable Key Settings* e salvar no arquivo de configuração (fora do Steam Cloud).

**Texto mais longo:** "Mostrar itens no chão" (21 caracteres), "Tela cheia sem bordas" (21 ≈ 147 px no controle de 400), "Daltonismo: reforço de forma nas raridades" (43 ≈ 301 px → coluna de rótulo de 320 comporta).

---

## 5. Componentes reutilizáveis

Cada componente tem uma classe C++ base (lógica, estados, eventos) e um Widget Blueprint de visual. Estilos de cor e textura vêm de uma única Data Asset `DA_ShatterUIStyle` (ou `USlateWidgetStyleAsset`) preenchida com os tokens.

### 5.1 Estados comuns

| Estado | Regra visual |
|---|---|
| Normal | Cores de repouso do componente |
| Hover | Fundo um passo mais claro (`panel_hover` ou `action.primary_hover`); borda `border.gold_highlight`; som de interface curto |
| Pressionado | Fundo um passo mais escuro (`pressed`); **conteúdo desce 1 px** (sem escala) |
| Desabilitado | Texto `text.disabled`, ícone a 40% de alpha, borda `border.subtle`; tooltip obrigatório com o motivo ("Requer 6 cargas") |
| Foco (teclado) | Anel de 1 px `border.focus` a 1 px por fora da borda, mais marcadores de canto 2 × 2; nunca depende só da cor de fundo |
| Selecionado | Para abas, linhas e segmentos: fundo `panel_raised` + filete de 2 px `border.gold` à esquerda (linhas) ou embaixo (abas) |

Hover e foco podem coexistir; o foco nunca some quando o mouse sai.

### 5.2 Botão — `WBP_Button` / `UShatterButton`

Variantes: **Primário** (`action.primary`, texto pergaminho; 1 por tela), **Secundário** (`action.secondary`, borda `border.default`), **Terciário/Texto** (sem fundo, texto `text.title`, sublinhado de 1 px no hover), **Ícone** (24 × 24, só ícone, tooltip obrigatório), **Perigoso** (secundário com texto `semantic.danger_text`; opção "segurar para confirmar" com barra de 1 s).
Medidas: altura 24, padding horizontal 8, largura mínima 96, texto `body` centralizado; ícone opcional 16 à esquerda com gap 4. Glifo de tecla opcional à direita (`micro`).

### 5.3 Painel — `WBP_Panel` / `UShatterPanel`

Variantes: **Ornamentado** (`nine_panel_ornate`, telas principais), **Simples** (`nine_panel_plain`, cartões e sub-seções), **Cartão** (`panel_raised` + filete semântico 2 px à esquerda: info, aviso, perigo, dourado). Slots: cabeçalho opcional (título `title` + botão fechar), corpo, rodapé. Padding 16. Sem estado de hover (cartões clicáveis usam a variante Botão).

### 5.4 Barra — `WBP_Bar` / `UShatterBar` e `WBP_Orb` / `UShatterOrb`

- Barra: moldura `nine_bar_frame`, fundo cor escura do token, preenchimento cor clara; **preenchimento arredondado para pixel inteiro**; "rastro" de perda (parte perdida fica em `life_highlight` por 400 ms antes de cair, em degraus); texto opcional `micro` centralizado. Variantes de altura: 4 (XP), 6 (fina), 8 (chefe).
- Orbe: máscara circular pixelada 56 × 56 pintada à mão, preenchimento vertical por linhas inteiras, linha de superfície 1 px mais clara.
- Estados: normal, cheio (brilho de 1 px no topo), baixo (< 30%: pulso de alpha 1 s), bloqueado (cinza `text.disabled`).

### 5.5 Slot de item — `WBP_ItemSlot` / `UShatterItemSlot` · Slot de habilidade — `WBP_SkillSlot` / `UShatterSkillSlot`

- Item: 36 × 36, `nine_slot`, ícone 32 centralizado; cantos pela raridade; número de pilha `micro` no canto inferior direito. Estados: vazio (ícone-fantasma da posição), com item, hover (borda `border.gold_highlight`), arrastando (origem a 40%), alvo de soltura válido (borda `semantic.success`) ou inválido (`semantic.danger`), requisito não cumprido (hachura), bloqueado (cadeado 16), novo (pip 4 × 4 `semantic.eco` até o primeiro hover).
- Habilidade: 36 × 36; tecla em `micro` no canto inferior esquerdo sobre placa escura 1 px; recarga = escurecimento `#0E0C0A` a 60% varrendo de cima para baixo em linhas inteiras + segundos restantes em `body` ("3", "0,8" abaixo de 1 s); recurso insuficiente = ícone tingido com `mana_dark`/cor do recurso a 50%; pronta após recarga = brilho de borda 1 px por 150 ms; bloqueada (demo) = cadeado.

### 5.6 Tooltip — `WBP_Tooltip` / `UShatterTooltip` (e `UShatterItemTooltip` para itens)

Fundo `#16130F` a 95%, `nine_tooltip`, sombra (2, 2); padding 12; largura máxima 224 (288 com texto grande); atraso 150 ms; segue as regras de posição de 4.2. Variantes: simples (título + texto), habilidade (nome, custo, recarga, tags como chips `micro`, sigilos), item (4.2).

### 5.7 Linha de regra — `WBP_RuleRow` / `UShatterRuleRow`

40 px (56 com quebra), fundo `panel_raised`; número de ordem em `text.title`; dois combos (`WBP_Dropdown` / `UShatterComboBox`) de condição e ação; alças ▲▼ e ×. Estados: normal, hover, foco, arrastando (sombra 2 px + linha-guia dourada de 2 px no destino), inválida (borda `semantic.danger` + texto "Habilidade não equipada"), incompatível com idle (filete `semantic.danger` + nome da habilidade), fixa ("Senão: ataque básico", sem alças).

### 5.8 Toast — `WBP_Toast` / `UShatterToast` (fila em `UShatterToastSubsystem`)

240 × 28, `nine_toast`, filete 2 px à esquerda na cor do tipo; ícone 16 + texto `body` (1 linha, ≤ 30 caracteres; 2 linhas → 44 px de altura). Tipos: info, sucesso, aviso, perigo, loot (cor da raridade; ex.: "Raro: Elmo do Vigia"), especial Fragmento de Eco (`semantic.eco` + som próprio, seção 7). Máximo 4 visíveis; o mais novo em cima; 3 s; hover pausa o tempo; ação opcional ("Desfazer").

### 5.9 Outros componentes

| Componente | Widget / Classe | Nota |
|---|---|---|
| Abas | `WBP_Tabs` / `UShatterTabBar` | 20 px de altura; `Q`/`E` não, use `Ctrl+Tab` e clique (Q/E são habilidades) |
| Combo | `WBP_Dropdown` / `UShatterComboBox` | Lista abre para baixo, máx. 8 itens visíveis, rolagem |
| Slider | `WBP_Slider` / `UShatterSlider` | Trilho 4 px, alça 8 × 12, passos discretos, valor à direita |
| Alternador | `WBP_Toggle` / `UShatterToggle` | Caixa 12 × 12 com marca pixel; "Ligado/Desligado" escrito |
| Segmentado | `WBP_Segmented` / `UShatterSegmentedControl` | Objetivo da expedição |
| Diálogo | `WBP_ConfirmDialog` / `UShatterConfirmDialog` | 360 de largura, scrim 75%, foco inicial no botão seguro |
| Cartão de save | `WBP_SaveSlotCard` / `UShatterSaveSlotCard` | 4.5 |
| Linha de tecla | `WBP_KeyBindRow` / `UShatterKeyBindRow` | 4.6 |
| Número de dano | `WBP_DamageNumber` / `UShatterDamageNumber` | Pool de 64, posição projetada e arredondada |
| Rótulo de item no chão | `WBP_LootLabel` / `UShatterLootLabel` | Placa escura + borda 1 px da raridade + nome; empilhamento sem sobreposição (desloca 12 px) |
| Glifo de tecla | `WBP_KeyGlyph` / `UShatterKeyGlyph` | Lê o mapeamento atual |

---

## 6. Feedback de combate ("juice")

Valores alinhados à seção 5 do plano. Todos configuráveis em dados (`Content/Data/`), não no código.

| Efeito | Quando | Valor |
|---|---|---|
| **Hitstop** | Golpe pesado / crítico / golpe pesado de chefe no jogador / jogador atingido | 60 / 80 / 80 / 40 ms; nenhum em golpe leve. Só pausa quem bateu e quem apanhou (`CustomTimeDilation` = 0 na entidade), nunca o jogo todo |
| **Flash branco** | Inimigo atingido | Sprite inteiro em `#FFFFFF` por **1 quadro de animação** (83 ms a 12 fps), via parâmetro de material (lerp para branco, sem aditivo). Com "Reduzir flashes": 50% |
| **Knockback** | Inimigo comum / elite / chefe | 12 / 4 / 0 px em 100 ms, em degraus de 1 px |
| **Tremor de câmera** | Só impactos grandes (golpe pesado que mata 3+, impacto de chefe, Golpe do Shatter) | Amplitude 2 px (pesado), 3 px (chefe), teto 4 px; 120–250 ms; deslocamentos **inteiros** sorteados a 30 Hz e decaindo linearmente. Opções: Normal / Reduzido (50%) / Desligado (seção 5: "com opção de desligar") |
| **Partículas de contato** | Todo acerto | Poeira `#9B713E` 4–6 partículas e faíscas `#F2E266` 3–5 (metal/pedra); quadrados de 1–2 px, vida 300–600 ms, sem blur. Carne/osso: lascas `#C8323A`/`#D8CDB6` (desligadas com "Reduzir sangue") |
| **Morte de inimigo** | Ao morrer | Animação curta de 4–6 quadros + corpo que se desfaz em 12–20 estilhaços `#E8C06A` subindo 8–16 px e sumindo em 500 ms (seção 5) |
| **Números de dano** | Todo acerto | 4.1; crítico 2× maior e amarelo |
| **Telegraph de chefe** | 700–1200 ms antes do golpe | Forma no chão (cone/círculo/linha) com preenchimento `#D74437` subindo de 35% a 60%, borda `#F0782E` 1 px, grade de 4 px e brasas subindo; nos últimos 100 ms a borda pisca branco. Sempre com som (seção 5 e 9, item 6) |
| **Drop** | Item cai | Comum: som simples; Mágico: brilho 2 px; Raro: coluna 6 × 64 `#EBD25A`; Único: coluna 10 × 128 `#E5822E` com pulso de 800 ms + som próprio (seção 5) |
| **Fragmento de Eco** | Ganho no jogo manual | Partículas `#6FD6C8` em espiral até o contador do HUD (400 ms) + toast especial + som próprio (seção 7) |
| **Esquiva** | Espaço | 2 "fantasmas" do sprite a 50% e 25% de alpha nos primeiros 200 ms (janela de invulnerabilidade, seção 5) |
| **Vida baixa** | < 30% | Vinheta 4.1 + batimento sonoro |

Regras: nenhum efeito usa blur, bloom ou escala fracionária; toda partícula é sprite de 1–2 px com filtro Nearest (Niagara com sprites `Pixels2D`, tamanho inteiro, alinhado à câmera); limite de 300 projéteis ativos e partículas em pool (seção 10).

---

## 7. Checklist de qualidade visual (QA / Release)

**Pixel-perfect**
- [ ] Captura em 1920 × 1080 e 3840 × 2160: cada pixel do sprite é bloco exato de 2 × 2 / 4 × 4 (zoom de 800% sem bordas suaves). Teste com a cena `L_PixelTest` (grade xadrez de 1 px + cartela de cores).
- [ ] Cartela de 32 cores da paleta sai na captura com diferença ≤ 2 por canal (tonemapper, exposição e bloom realmente desligados).
- [ ] Nenhuma textura com filtro diferente de Nearest nem com mipmaps (consulta no Asset Audit / `Size Map`).
- [ ] Câmera e personagem andando não "tremem" (snap inteiro); sem costura entre tiles.
- [ ] 1440p e 1366 × 768: modo "Inteira com bordas" mostra bordas `#0E0C0A` e pixels inteiros; modo "Preencher" não corta a UI.

**Texto e localização**
- [ ] Frase-teste da 2.2 renderiza todos os glifos em todos os estilos e escalas.
- [ ] Todas as telas da seção 4 verificadas com as strings mais longas em pt-BR (e es, quando houver); nenhum texto cortado, sobreposto ou fora da margem segura de 8 px.
- [ ] Texto grande ligado: tooltip, relatório e opções continuam legíveis e com rolagem quando precisa.
- [ ] Nomes de item com gênero correto ("Lança Sombria", não "Lança Sombrio").
- [ ] Números em formato do idioma (1.234 / 1,20 em pt-BR); datas dos saves no formato local.

**Cor e leitura**
- [ ] Contraste de texto ≥ 4,5:1 sobre o fundo real (exceto `text.disabled`, sempre com motivo).
- [ ] Raridade identificável sem cor (texto no tooltip e forma do canto do slot) — testar com filtro de daltonismo (deuteranopia/protanopia).
- [ ] Telegraph de chefe visível sobre todos os pisos do Ato I e lido em < 0,5 s por testador.
- [ ] Nenhum número negativo nas telas de expedição/relatório; "+200% XP" do Fervor presente no jogo manual.

**Interação**
- [ ] Todas as telas operáveis só com teclado (Tab/setas/Enter/Esc) e só com mouse; anel de foco sempre visível.
- [ ] Cinco estados de cada componente da seção 5 conferidos na galeria `WBP_UIGallery` (tela de teste com todos os componentes).
- [ ] Remapear todas as ações; conflitos tratados; glifos do HUD atualizados; configuração persiste após reiniciar.
- [ ] Expedição: estados vazio, cargas insuficientes, incompatível e "outro personagem em expedição" reproduzidos.
- [ ] Relatório: não fecha sem coletar; não coleta duas vezes.

**Combate e acessibilidade**
- [ ] Hitstop 40–80 ms, flash 1 quadro, knockback por tipo, partículas e morte em estilhaços conferidos em vídeo a 60 fps.
- [ ] Tremor Desligado zera todo tremor; Reduzir flashes e Reduzir sangue funcionam.
- [ ] Pool de números de dano não aloca durante o combate (80 inimigos na tela, 60 FPS).

**Assets e licenças**
- [ ] Todas as fontes com licença registrada (Pixel Operator CC0, Jacquard 12 OFL, Pixelify Sans OFL) e arquivo de licença no build.
- [ ] Sprites, tiles e ícones finais feitos por artista; nenhum asset gerado por IA no jogo sem declaração (política de IA, seção 9).
- [ ] Toda cor usada nas telas existe em `03_design_tokens.json`.

---

## 8. Desvios do plano

| Plano (Godot 4) | Agora (UE5) | Motivo |
|---|---|---|
| Stretch mode viewport, escala inteira, filtro nearest | `r.ScreenPercentage = 100/N` + `r.Upscale.Quality 0` (ou Render Target 960 × 540) e curva de DPI em degraus | Equivalente no UE5 |
| `tr()` e CSV de tradução | `FText` com String Tables (CSV exportado pelo Narrative) | Equivalente no UE5 |
| Sprites em Godot 2D | Paper2D com PPU = 1, materiais unlit | Equivalente no UE5 |
| Fonte não definida | Pixel Operator (CC0) + Jacquard 12 (OFL) | Decisão deste documento; validar glifos no dia 1 |
| Posições de equipamento sem nome | 8 posições nomeadas (5 no demo) | Necessário para desenhar o inventário; Vision Lead pode renomear |
| Painel de build sem tecla | Proposta: `C` (Personagem) | Q/E/R/F/I/P/M já usados; fora do escopo das telas deste protótipo |
