# Cliente 2D (corrida top-down)

Cena principal: `scenes2d/Run2D.tscn` (GDScript, sem C#). Código em `scripts2d/`, dados em `data2d/` (CSV e salas em texto), arte em `art2d/`. O cliente só apresenta: meta, Forja, cartas e fluxo da corrida são do módulo `rogue` do ShatterCore, chamado pela GDExtension `ShatterRogue` (`godot/gdextension/`).

- Controles: WASD move, mouse mira, clique atira, Espaço esquiva, R reinicia ao morrer.
- Corrida: 4 salas (`data2d/run.csv`), a última com o Guardião. Limpou, a porta abre; morreu, recomeça em 2 s.
- Chefe: `data2d/boss_patterns_2d.csv` (fases por limiar de vida, padrões golpe/leque/anel/investida, entrada e transição) e `scripts2d/boss_2d.gd`.
- Números: `data2d/player.csv`, `enemies.csv` (inclui `windup` e `kb_resist`), `feel.csv` (hit stop, tremor, números de dano), `run_settings.csv`. Textos: `loc_2d.csv`. Salas: `data2d/rooms/*.txt` (legenda no topo de `scripts2d/room_2d.gd`).
- Arte: o manifesto `data2d/sprites_manifest.csv` aponta para `art2d/sprites/<id>/<id>_<anim>.png`; sem o PNG o cliente gera placeholders. Formato em `docs/arte/25_formato_folhas_sprites_2d.md`.

## GDExtension do ShatterCore (obrigatória)
O cliente 2D chama o core pela classe `ShatterRogue` (`scripts2d/nucleo_2d.gd`). Sem a biblioteca compilada o jogo não abre. Compilar (CMake, godot-cpp 4.4):
```
git clone --depth 1 -b godot-4.4-stable https://github.com/godotengine/godot-cpp D:\openclaude\_ferramentas\godot-cpp
cmake -S godot/gdextension -B D:\openclaude\_trabalho-claude\build-ext -DGODOT_CPP_DIR=D:\openclaude\_ferramentas\godot-cpp
cmake --build D:\openclaude\_trabalho-claude\build-ext --config Release
```
A biblioteca sai em `godot/gdextension/bin/` (ignorada pelo Git) e o Godot a acha por `godot/shatter_rogue.gdextension`. No CI, `cliente2d.yml` compila a de Linux e a de Windows (artifacts `gdextension-linux` e `gdextension-windows`); para jogar no PC sem compilar, baixe a `gdextension-windows` do último run e solte a `.dll` em `godot/gdextension/bin/`. Os CSV de `data2d` são copiados para `user://dados_core` ao abrir o jogo (o core lê de uma pasta real, inclusive no executável exportado).

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
