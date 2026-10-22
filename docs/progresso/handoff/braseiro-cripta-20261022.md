# Passagem de bastão: braseiro da Cripta (22/10/2026)

Estado: aprovado pelo Will (prancha). Está em `claude/godot-cripta`, commit bda63eb.

- Fonte: `art-src/cenario/modulos/braseiro_godot.py` (orquestrador) e `braseiro/` (`_lib`, `pernas`, `bacia`, `gaiola`, `correntes`, `brasas`).
- Roda com `pip install bpy==5.2.3 pillow`: `SAMPLES=24 python braseiro_godot.py -- saida.glb pasta_previas` (gera prancha e prévias; `PARTES=` filtra).
- Saída: `godot/art/models/SM_Cripta_Braseiro.glb` (~65 mil triângulos, 12 MB; texturas embutidas, vertex color de desgaste).
- Chama, faíscas, fumaça e `LuzBacia` ficam no `godot/scripts/tools/build_cripta.gd` e em `art/shaders/chama.gdshader`. Não foram testados no Godot (sem Godot na nuvem): conferir ao rodar `build_cripta.gd`.
- Pendente: o Will pediu mais ângulos de peças que ainda não têm; recorte irregular leve na base da chama no close.
