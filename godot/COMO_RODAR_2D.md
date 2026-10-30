# Cliente 2D (corrida top-down)

Cena principal: `scenes2d/Run2D.tscn` (GDScript, sem C#). Código em `scripts2d/`, dados em `data2d/` (CSV e salas em texto), arte em `art2d/`. O cliente só apresenta; as regras da corrida migram para o módulo `run` do ShatterCore (pacote 2 de `/design/plano_migracao_roguelike.md`).

- Controles: WASD move, mouse mira, clique atira, Espaço esquiva, R reinicia ao morrer.
- Corrida: 4 salas (`data2d/run.csv`), a última com o Guardião. Limpou, a porta abre; morreu, recomeça em 2 s.
- Números: `data2d/player.csv`, `enemies.csv`, `run_settings.csv`. Textos: `loc_2d.csv`. Salas: `data2d/rooms/*.txt` (legenda no topo de `scripts2d/room_2d.gd`).
- Arte: o manifesto `data2d/sprites_manifest.csv` aponta para `art2d/sprites/<id>/<id>_<anim>.png`; sem o PNG o cliente gera placeholders. Formato em `docs/arte/25_formato_folhas_sprites_2d.md`.

## Testes e captura
```
godot --headless --path godot --script res://scripts2d/tools/test_2d.gd     # corrida completa, salas, manifesto (CI: cliente2d.yml)
godot --path godot --script res://scripts2d/tools/captura_2d.gd -- saida.png [indice_sala]
```

## Build jogável (Windows e Linux)
`tools/build/build_2d.sh [saida] [godot]` monta um projeto só com o cliente 2D e exporta `EcosDosEstilhacos.exe` (Windows) e `.x86_64` (Linux), com os export templates 4.4.1 instalados. Os CSV entram crus (importador `keep`); sem isso o executável não acha `loc_2d.csv` nem os demais dados.
