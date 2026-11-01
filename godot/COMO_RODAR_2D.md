# Cliente 2D (corrida top-down)

Cena principal: `scenes2d/Run2D.tscn` (GDScript, sem C#). Código em `scripts2d/`, dados em `data2d/` (CSV e salas em texto), arte em `art2d/`. O cliente só apresenta: meta, Forja, cartas e fluxo da corrida são do módulo `rogue` do ShatterCore, chamado pela GDExtension `ShatterRogue` (`godot/gdextension/`).

- Controles: WASD move, mouse mira, clique atira, Espaço esquiva, R reinicia ao morrer.
- Guerreiro: no título, o botão "Classe" alterna Arqueiro/Guerreiro (ou `-- --classe=guerreiro` na linha de comando). Clique = combo de espada em 3 golpes; Q, E, F, R usam as habilidades ativas na ordem em que foram aprendidas (cartas ao limpar a sala; segurar a tecla da Postura de Guarda). Árvore em `data2d/habilidades_guerreiro.csv`; regras do personagem em `data2d/guerreiro.csv`.
- Início do jogo: o título mostra a key art aprovada (`art2d/ui/titulo_fundo.jpg`) e o cartão da classe (retrato animado do idle, descrição e "Trocar classe"). No primeiro "Jogar" abre o prólogo (`scripts2d/prologo_2d.gd`): Ilsa e Tico no Refúgio, falas em `data2d/prologo.csv` e `loc_2d.csv`, retratos recortados das folhas aprovadas `n01_ilsa`/`n02_tico` (`art2d/ui/retrato_*.png`). Clique ou Espaço avança, Esc pula; "Rever o prólogo" fica no título. O estado `prologo_visto` vai no save de opções.
- Primeira sala calma: o jogador nasce abaixo do riacho e os inimigos da sala 1 dormem até ele chegar a `first_room_wake_radius` (`run_settings.csv`) ou ferir um deles; aí a sala toda acorda.
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

## Clima vivo das salas
`scripts2d/clima_2d.gd` (criado pelo `ambiente_2d.gd` de cada sala) dá movimento ao cenário: vento com rajadas, árvores, arbustos e capim balançando por shader, folhas caindo das copas e atravessando a sala nas rajadas, fogo em línguas, brasas e fumaça nos braseiros, sombra de nuvem (grama) ou névoa rasteira (pedra), poeira no ar e ondas de vento no gramado. Só visual. Números em `data2d/clima.csv`. Para ver em movimento: `godot --path godot --script res://scripts2d/tools/captura_clima_2d.gd -- pasta res://data2d/rooms/sala_1.txt 90 2` grava quadros (junte com ffmpeg).

## Testes e captura
```
godot --headless --path godot --script res://scripts2d/tools/test_2d.gd     # corrida completa, salas, manifesto (CI: cliente2d.yml)
godot --path godot --script res://scripts2d/tools/captura_2d.gd -- saida.png [indice_sala]
```

## Build jogável (Windows e Linux)
`tools/build/build_2d.sh [saida] [godot]` monta um projeto só com o cliente 2D e exporta `EcosDosEstilhacos.exe` (Windows) e `.x86_64` (Linux), com os export templates 4.4.1 instalados. Os CSV entram crus (importador `keep`); sem isso o executável não acha `loc_2d.csv` nem os demais dados. Todo CSV novo em `data2d/` precisa de um `.csv.import` com `importer="keep"` (o CI confere com `tools/build/checar_csv_keep.sh`). Importado como tradução, cada coluna vira um `Translation` criado numa thread de importação; o `set_locale` deixa na fila da thread principal uma chamada para um objeto que já foi liberado quando a fila roda, e o `--import` do Godot 4.4 cai às vezes com `double free or corruption`.

## Áudio e UI (P5)
- Áudio: `data2d/audio.csv` (evento, arquivo, volume, variação de pitch) e `scripts2d/audio_2d.gd` (`Audio.tocar("evento")`, `Audio.musica(...)`). Os WAV de `art2d/audio/` são gerados por `python3 tools/audio/gerar_audio.py` (síntese própria, CC0; ver `art2d/audio/LICENCA.md`).
- Tema de pedra escura: `scripts2d/tema_2d.gd` + `data2d/tema.csv` (cores). HUD: `hud_2d.gd` com medidas em `data2d/hud_layout.csv`. Ícones geométricos provisórios: `icones_2d.gd` + `data2d/icones.csv`; um PNG em `art2d/ui/icone_<id>.png` substitui o provisório.
- HUD de ARPG sombrio (peças em `scripts2d/hud_arte_2d.gd`, desenhadas por código, arte original): globo de vida e globo de recurso (mana, reservado), faixa de pedra com barra de habilidades, plaqueta da sala e barra do chefe ornamentada (desenhada pelo próprio `boss_2d.gd`). Captura só da HUD: `scripts2d/tools/captura_hud_2d.gd` (capturas em `docs/arte/sprites2d/capturas_hud/`). Antes: vida, estamina (recarga da esquiva, sem recurso novo), mana (reservada, vazia) e barra de habilidades (tiro, esquiva e slots bloqueados). A barra do chefe subiu para o topo central.

## Ferramentas de desenvolvimento (addons e CI)
Origem: `docs`/relatório `analises/godot-plugins-ferramentas-20261101.md` (projeto compartilhado).

- **Versão do Godot:** o CI e as builds usam **4.4.1** (godot-cpp 4.4). O `project.godot` diz 4.7 só porque o cliente 3D/C# foi aberto no 4.7; o CI troca para 4.4 ao montar o projeto. Não suba o Godot do CI sem testar a GDExtension. O **gdUnit4 v7 exige Godot 4.5+** (classe `Logger`) e o v6.0.3 não carregou em modo headless no 4.4.1; por isso o gdUnit4 não foi adotado. Reavaliar quando o CI subir para 4.5 ou mais.
- **Lint:** `pip install "gdtoolkit==4.*"` e, em `godot/`, `gdlint scripts2d`. A configuração (`godot/.gdlintrc`) desliga regras de estilo que o código atual não segue; o job `lint-gdscript` do CI roda isso e acusa erro de sintaxe. Não usar `gdformat` ainda (reformataria 58 arquivos).
- **Console de playtest (LimboConsole, MIT, `godot/addons/limbo_console`):** tecla `` ` `` abre o console. Comandos (`scripts2d/console_dev_2d.gd`): `god`, `curar`, `matar`, `horda <id> <n>`, `sala <n>`, `status`. Só em build de debug; em release o `run_2d.gd` desliga o console. Addons ficam commitados no repositório, nunca baixados no CI; a origem de cada um está em `ORIGEM_EOTS.txt` na pasta dele.
- **Teste de estresse de horda:** `godot --headless --fixed-fps 60 --path <projeto> --script res://scripts2d/tools/estresse_2d.gd -- [n=500] [quadros=300] [id=hollow_sentinel]`. Mede só a lógica/física (headless não desenha). Medição no container de desenvolvimento (Godot 4.4.1): 0 inimigos = 0,6 ms/quadro, 500 = ~37 ms, 2000 = >1 s. Ou seja, o limite da lógica atual está bem abaixo de 500 inimigos juntos; antes de hordas grandes, trocar um nó por inimigo por MultiMesh e checagem em grade espacial. O CI roda 300 inimigos só como informação no resumo do job.
