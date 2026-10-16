# Referências gráficas aprovadas

Imagens de conceito geradas com o gpt-image (ChatGPT, via Codex CLI). São referência de direção de arte, não assets finais do jogo. O @william aprovou o visual em 16/10/2026 e, no mesmo dia, a rodada de consistência que trouxe o Mago novo e deixou heróis, inimigos e chefes iguais em todas as cenas.

## Direção

- **Visual:** o estilo do Spell Brigade. É um 3D estilizado pintado à mão, com sombra pintada na textura e formas grossas chanfradas. Os heróis são chibi (cerca de 3 cabeças de altura), com cores quentes e frias. A magia é em neon com núcleo quase branco, cada mundo tem a sua névoa colorida e a UI é de pedra escura com molduras orgânicas espinhosas.
- **Conteúdo:** vem do roteiro do jogo (`EchoesOfTheShatter_base_para_Code.html`): Guerreiro, Arqueiro e Mago e as habilidades deles, os inimigos e chefes do Ato I, as áreas do Ato I, o HUD e o mapa de Aural.
- **Substitui:** a direção em pixel art escura e a paleta ocre do design system do HTML não valem mais para o visual.
- **Referências usadas:** todas as 1.424 texturas extraídas do Spell Brigade, agrupadas em 28 pranchas-mosaico por categoria e anexadas aos prompts. Os prompts pedem o estilo com os nossos personagens e proíbem reproduzir 1:1 os personagens e os logos do Spell Brigade. As pranchas ficaram fora do repositório, porque são assets de terceiros.

## Folhas oficiais

Elas são a fonte de verdade de cada personagem. Toda imagem nova em que eles aparecem deve anexá-las e copiá-las exatamente.

- **Guerreiro (02):** elmo dourado com viseira e pluma vermelha, tabardo vermelho, escudo com pedra incrustada e martelo de bloco de pedra.
- **Arqueiro (03):** capuz verde com máscara de bico de osso, manto de penas e arco de osso.
- **Mago (04):** capuz azul pontudo com o rosto visível e cajado de madeira com cristal azul num anel dourado. Não tem lanterna.
- **Inimigos (05):** os 8 inimigos do Ato I, cada um nas versões normal, elite e corrompida.
- **Chefes (06):** Guardião da Cripta, Tecelã de Cascalho, Carrasco do Voto e Vigia do Sino.
- **Cenários (07 e 08):** a Cripta Partida, a Pedreira dos Ecos e a Ponte do Sino.
- **Ícones (11):** os ícones de habilidade e de item.

## Imagens (`aprovadas/`)

| Arquivo | Conteúdo |
|---|---|
| 01_key_art.png | Key art com os 3 heróis e uma faixa de estilo |
| 02_guerreiro.png | Guerreiro: turnaround, poses de habilidade e skins |
| 03_arqueiro.png | Arqueiro: turnaround, poses de habilidade e skins |
| 04_mago.png | Mago: turnaround, poses de habilidade e skins |
| 05_inimigos_ato1.png | 8 inimigos do Ato I nas versões normal, elite e corrompida |
| 06_chefes_ato1.png | Os 4 chefes do Ato I, cada um enfrentando um herói |
| 07_cripta_tileset.png | Cripta Partida: arena com o Guerreiro e kit modular |
| 08_pedreira_ponte.png | Pedreira dos Ecos com o Arqueiro e Ponte do Sino com o Mago |
| 09_vfx_habilidades.png | Efeitos das habilidades das 3 classes contra inimigos do Ato I e os telegraphs dos inimigos |
| 10_hud_mockup.png | HUD em combate: o Guerreiro contra o Guardião da Cripta |
| 11_icones.png | Ícones de habilidades (com o herói de cada classe) e de itens |
| 12_mapa_mundi.png | Mapa do Ato I e seleção de área com o Vigia do Sino |

## Prompts e scripts

- **Prompts:**
  - [prompts_spell_brigade.json](prompts_spell_brigade.json) gerou 02, 03 e 05.
  - [prompts_consistencia.json](prompts_consistencia.json) gerou as outras 9 imagens.
  - Os caminhos de referência dentro deles apontam para uma pasta temporária. Para gerar de novo, recrie as pranchas e as folhas oficiais.
- **Scripts:** ficam em `scripts/` e rodam com o Python de um venv que tenha o Pillow (o `pranchas.py` precisa dele).
  1. `pranchas.py <Assets do Spell Brigade> <pasta das pranchas>` monta as pranchas.
  2. `prompts_sb.py <pasta das pranchas> <prompts.json>` gera os prompts de estilo.
  3. `prompts_herois.py` e `prompts_consistencia.py` acrescentam as folhas oficiais e as regras de consistência. Os parâmetros estão no cabeçalho de cada script.
  4. `gerar.py <prompts.json> <pasta de saída> [ids...]` chama o Codex, 4 imagens por vez.

## Pontos em aberto

- **Inimigos genéricos no HUD (10):** os soldados ao redor do Guardião estão próximos da Sentinela Oca e do Lanceiro Repetido da folha 05, mas não idênticos.
- **Animações:** as poses das folhas 02 a 04 são quadros-chave de conceito, não animações. As sprites e animações finais ainda precisam ser produzidas a partir dessas folhas.
