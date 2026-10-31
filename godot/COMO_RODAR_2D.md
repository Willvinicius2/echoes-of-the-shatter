# Cliente 2D (corrida top-down)

Cena principal: `scenes2d/Run2D.tscn` (GDScript, sem C#). Código em `scripts2d/`, dados em `data2d/` (CSV e salas em texto), arte em `art2d/`. O cliente só apresenta; as regras da corrida migram para o módulo `run` do ShatterCore (pacote 2 de `/design/plano_migracao_roguelike.md`).

- Controles: WASD move, mouse mira, clique atira, Espaço esquiva, R reinicia ao morrer.
- Guerreiro: no título, o botão "Classe" alterna Arqueiro/Guerreiro (ou `-- --classe=guerreiro` na linha de comando). Clique = combo de espada em 3 golpes; Q, E, F, R usam as habilidades ativas na ordem em que foram aprendidas (cartas ao limpar a sala; segurar a tecla da Postura de Guarda). Árvore em `data2d/habilidades_guerreiro.csv`; regras do personagem em `data2d/guerreiro.csv`.
- Início do jogo: o título mostra a key art aprovada (`art2d/ui/titulo_fundo.jpg`) e o cartão da classe (retrato animado do idle, descrição e "Trocar classe"). No primeiro "Jogar" abre o prólogo (`scripts2d/prologo_2d.gd`): Ilsa e Tico no Refúgio, falas em `data2d/prologo.csv` e `loc_2d.csv`, retratos recortados das folhas aprovadas `n01_ilsa`/`n02_tico` (`art2d/ui/retrato_*.png`). Clique ou Espaço avança, Esc pula; "Rever o prólogo" fica no título. O estado `prologo_visto` vai no save de opções.
- Primeira sala calma: o jogador nasce abaixo do riacho e os inimigos da sala 1 dormem até ele chegar a `first_room_wake_radius` (`run_settings.csv`) ou ferir um deles; aí a sala toda acorda.
- Corrida: 4 salas (`data2d/run.csv`), a última com o Guardião. Limpou, a porta abre; morreu, recomeça em 2 s.
- Chefe: `data2d/boss_patterns_2d.csv` (fases por limiar de vida, padrões golpe/leque/anel/investida, entrada e transição) e `scripts2d/boss_2d.gd`.
- Números: `data2d/player.csv`, `enemies.csv` (inclui `windup` e `kb_resist`), `feel.csv` (hit stop, tremor, números de dano), `run_settings.csv`. Textos: `loc_2d.csv`. Salas: `data2d/rooms/*.txt` (legenda no topo de `scripts2d/room_2d.gd`).
- Arte: o manifesto `data2d/sprites_manifest.csv` aponta para `art2d/sprites/<id>/<id>_<anim>.png`; sem o PNG o cliente gera placeholders. Formato em `docs/arte/25_formato_folhas_sprites_2d.md`.

## Testes e captura
```
godot --headless --path godot --script res://scripts2d/tools/test_2d.gd     # corrida completa, salas, manifesto (CI: cliente2d.yml)
godot --path godot --script res://scripts2d/tools/captura_2d.gd -- saida.png [indice_sala]
```

## Build jogável (Windows e Linux)
`tools/build/build_2d.sh [saida] [godot]` monta um projeto só com o cliente 2D e exporta `EcosDosEstilhacos.exe` (Windows) e `.x86_64` (Linux), com os export templates 4.4.1 instalados. Os CSV entram crus (importador `keep`); sem isso o executável não acha `loc_2d.csv` nem os demais dados.

## Áudio e UI (P5)
- Áudio: `data2d/audio.csv` (evento, arquivo, volume, variação de pitch) e `scripts2d/audio_2d.gd` (`Audio.tocar("evento")`, `Audio.musica(...)`). Os WAV de `art2d/audio/` são gerados por `python3 tools/audio/gerar_audio.py` (síntese própria, CC0; ver `art2d/audio/LICENCA.md`).
- Tema de pedra escura: `scripts2d/tema_2d.gd` + `data2d/tema.csv` (cores). HUD: `hud_2d.gd` com medidas em `data2d/hud_layout.csv`. Ícones geométricos provisórios: `icones_2d.gd` + `data2d/icones.csv`; um PNG em `art2d/ui/icone_<id>.png` substitui o provisório.
- HUD de ARPG sombrio (peças em `scripts2d/hud_arte_2d.gd`, desenhadas por código, arte original): globo de vida e globo de recurso (mana, reservado), faixa de pedra com barra de habilidades, plaqueta da sala e barra do chefe ornamentada (desenhada pelo próprio `boss_2d.gd`). Captura só da HUD: `scripts2d/tools/captura_hud_2d.gd` (capturas em `docs/arte/sprites2d/capturas_hud/`). Antes: vida, estamina (recarga da esquiva, sem recurso novo), mana (reservada, vazia) e barra de habilidades (tiro, esquiva e slots bloqueados). A barra do chefe subiu para o topo central.
