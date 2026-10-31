# 29. Habilidades e árvore de skills (31/10/2026)

Base comum para as três classes (arqueiro, guerreiro, mago). Decisões do Jev (`jev-latest`, `POST /v1/systemone`, consulta de 31/10): pontos **híbridos** (77%: pontos permanentes que liberam nós; o jogador escolhe os 4 slots equipados), recurso **recarga mais mana** (56%, confiança 0,34, provisória), **4 slots** ativos (100%), redistribuição gratuita (56%, provisória).

## Fluxo
- Ganho de pontos: 1 por sala limpa e +3 com o chefe (`run_settings.csv`: `skill_points_room`, `skill_points_boss`). O saldo e os níveis aprendidos ficam no save da meta (`meta_2d.gd`, campo `habilidades`, por classe).
- Árvore: tecla **T** abre/fecha (pausa o jogo). Clique esquerdo aprende ou sobe o nível; clique direito num nó ativo gira o slot em que ele fica; o botão redistribui todos os pontos de graça.
- Slots: **Q, E, F, R** (`skill_1..4`). A ativa recém-aprendida entra no primeiro slot livre. Ataque básico e esquiva seguem como estão.
- Mana: `mana_max` e `mana_regen` em `player.csv`, sobrescritos por classe em `classes_2d.csv`. A recarga das skills é multiplicada por `skill_cd_mult`.

## Formato dos dados (por classe)
`godot/data2d/habilidades_<classe>.csv`, colunas:
`id,ramo,tipo,tier,pai,pontos,nivel_max,efeito,cd,custo,dano,qtd,angulo,raio,duracao,alcance,valor,escala,stat,modo,icone`

- `tipo`: `ativa` ou `passiva`. `pai` vazio = raiz do ramo; o nó só abre com o pai no nível 1 ou mais. `pontos` = custo por nível.
- `escala`: fração somada por nível acima do 1 em `dano, qtd, raio, duracao, alcance, valor` (`base*(1+escala*(n-1))`). `cd` e `custo` não escalam.
- Passivas usam `stat`, `modo` (`add` ou `mult`) e `valor` por nível; entram nos stats via `habilidades_2d.aplicar_passivas`.
- Textos em `loc_2d.csv`: `skill.<id>.name`, `skill.<id>.desc`, `ramo.<id>`, `class.<classe>`. Ícone: id de `data2d/icones.csv` ou `art2d/ui/icone_<id>.png`.

## Efeitos ativos
Cada classe tem `godot/scripts2d/efeitos_<classe>_2d.gd` (`extends RefCounted`) com
`static func executar(efeito: String, jogador: Node2D, def: Dictionary, nivel: int, mira: Vector2) -> bool`.
O `def` já vem escalonado pelo nível. Retornar `false` cancela sem gastar mana nem recarga. Status em inimigos: `aplicar_status(tipo, dur, valor)`.

## Classes
`godot/data2d/classes_2d.csv`: `id, nome, sprite, habilidades, efeitos` e sobrescritas de `player.csv` (`hp_max, speed, mana_max, mana_regen, shoot_cooldown, arrow_damage`; vazio = igual ao padrão). A classe da próxima corrida é `meta.classe` (seletor no hub: pendente).

## Código
`scripts2d/habilidades_2d.gd` (runtime), `arvore_ui_2d.gd` (UI), integração em `player_2d.gd`, `upgrades_2d.gd`, `run_2d.gd`, `hud_2d.gd`. Teste: `_testar_habilidades` em `scripts2d/tools/test_2d.gd` com a fixture `data2d/testes/habilidades_teste.csv`.
