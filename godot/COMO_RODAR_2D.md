# Cliente 2D (corrida top-down)

Cena principal: `scenes2d/Run2D.tscn` (GDScript, sem C#). Código em `scripts2d/`, dados em `data2d/` (CSV e salas em texto), arte em `art2d/`. O cliente só apresenta; as regras da corrida migram para o módulo `run` do ShatterCore (pacote 2 de `/design/plano_migracao_roguelike.md`).

- Controles: WASD move, mouse mira, clique atira, Espaço esquiva, R reinicia ao morrer.
- Corrida: 4 salas (`data2d/run.csv`), a última com o Guardião. Limpou, a porta abre; morreu, recomeça em 2 s.
- Chefe: `data2d/boss_patterns_2d.csv` (fases por limiar de vida, padrões golpe/leque/anel/investida, entrada e transição) e `scripts2d/boss_2d.gd`.
- Números: `data2d/player.csv`, `enemies.csv` (inclui `windup` e `kb_resist`), `feel.csv` (hit stop, tremor, números de dano), `run_settings.csv`. Textos: `loc_2d.csv`. Salas: `data2d/rooms/*.txt` (legenda no topo de `scripts2d/room_2d.gd`).
- Arte: o manifesto `data2d/sprites_manifest.csv` aponta para `art2d/sprites/<id>/<id>_<anim>.png`; sem o PNG o cliente gera placeholders. Formato em `docs/arte/25_formato_folhas_sprites_2d.md`.

## Testes e captura
```
godot --headless --path godot --script res://scripts2d/tools/test_2d.gd     # corrida completa, salas, manifesto (CI: cliente2d.yml)
godot --path godot --script res://scripts2d/tools/captura_2d.gd -- saida.png [indice_sala]
```

## Áudio e UI (P5)
- Áudio: `data2d/audio.csv` (evento, arquivo, volume, variação de pitch) e `scripts2d/audio_2d.gd` (`Audio.tocar("evento")`, `Audio.musica(...)`). Os WAV de `art2d/audio/` são gerados por `python3 tools/audio/gerar_audio.py` (síntese própria, CC0; ver `art2d/audio/LICENCA.md`).
- Tema de pedra escura: `scripts2d/tema_2d.gd` + `data2d/tema.csv` (cores). HUD: `hud_2d.gd` com medidas em `data2d/hud_layout.csv`. Ícones geométricos provisórios: `icones_2d.gd` + `data2d/icones.csv`; um PNG em `art2d/ui/icone_<id>.png` substitui o provisório.
- HUD: vida, estamina (recarga da esquiva, sem recurso novo), mana (reservada, vazia) e barra de habilidades (tiro, esquiva e slots bloqueados). A barra do chefe subiu para o topo central.
