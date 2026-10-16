# Echoes of the Shatter — Protótipo F1

ARPG pixel art, single-player offline. A F1 prova que o **combate do Guerreiro na Cripta** é gostoso em 30 segundos.
Godot 4.7.2 (GL Compatibility), GDScript tipado. Toda a arte é placeholder desenhada em código.

## Como abrir e rodar

- **Editor:** abra o Godot 4.7.2, "Importar" e selecione `project.godot`. A cena principal é `res://scenes/crypt.tscn` (F5).
- **Linha de comando:** `Godot_v4.7.2-stable_win64.exe --path D:\openclaude\EchoesOfTheShatter`
- Primeira vez (gera o cache de classes globais): `<godot_console> --headless --path <projeto> --import`

## Testes (headless, sem addons)

```
<godot_console> --headless --path D:\openclaude\EchoesOfTheShatter -s res://tests/run_tests.gd
```

Sai com código diferente de zero se algo falhar. Cobre: fórmula do StatBlock e tags, ordem de cálculo e tetos
(evasão 70, bloqueio 50, resistência 75), crítico determinístico, fluxos de RNG, valores nunca negativos,
efeitos/gatilhos/guarda, validação dos `.tres`, ações de input e um teste de fumaça (900 frames de física com um
bot que anda e ataca, incluindo o chefe; falha se houver qualquer erro/`push_error`, capturado por `Logger`).

## Controles

| Ação | Entrada |
|---|---|
| Mover | WASD |
| Mirar | Mouse |
| Corte de Ferro (básico) | Botão esquerdo (segure para repetir) |
| Investida | Botão direito |
| Escudada | Q |
| Fenda de Pedra | E |
| Esquiva | Espaço (3 cargas) |
| Reservadas (sem função na F1) | R, F, 1, 2 |

As ações são registradas pelo autoload `InputSetup` caso não existam no InputMap.

## Estrutura

```
autoload/        EventBus (sinais), InputSetup (ações), Game (seed, RNG, flag de tremor)
core/data/       Resources tipados: ClassData, SkillData, EnemyData, EffectData, EncounterData
core/rules/      Motor de regras (RefCounted puro, sem Node): StatBlock, DamageCalc, Combatant,
                 EffectSet, TriggerSet, GuardMeter, ResourcePool, RngStreams, Geo, DataDB...
data/            Instâncias .tres (heroes, skills, enemies, effects, encounters) com IDs estáveis
game/actors/     Actor, Player, Enemy (apresentação + ponte para o motor)
game/world/      Crypt (fluxo do encontro), CryptFloor (chão isométrico, paredes, portas)
game/fx/         FxLayer (pools de partículas e números de dano)
game/ui/         Hud
scenes/          crypt.tscn (cena principal)
tests/           run_tests.gd
```

## Regras de arquitetura

- Lógica separada da apresentação: todo cálculo de dano passa por `DamageCalc` (futuro simulador idle usará o mesmo motor).
- Nenhum número de balanceamento em script: tudo em `data/*.tres`. (Em `Rules` ficam só os tetos/mínimos de design.)
- RNG determinístico por fluxo: seed = hash(seed, fluxo, índice). Opcional: `-- --seed=123` na linha de comando.
- Hitstop é por entidade (nunca congela o jogo todo). Tremor de tela pode ser desligado com `Game.shake_enabled = false`.

## Simplificações da F1

- Sem poções, loot, inventário, menu ou salvar; R/F/1/2 só registrados.
- Sprites são formas desenhadas em `_draw`; sem animação por quadros.
- Vitória exibe uma mensagem e o jogo continua; não há tela de reinício.
