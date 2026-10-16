extends Node
## Barramento de eventos global. Sistemas se comunicam por sinais em vez de chamadas diretas.

signal damage_dealt(attacker_id: String, target_id: String, result: HitResult, position: Vector2, target_is_player: bool)
signal enemy_died(enemy_id: String, position: Vector2, is_boss: bool)
## O corpo terminou de se desfazer (efeito de estilhaços).
signal enemy_dissolved(position: Vector2, is_boss: bool)
signal player_died()
signal player_respawned()
signal player_blocked(position: Vector2)
signal guard_broken(target_id: String, position: Vector2)
signal skill_used(skill_id: String)
signal boss_spawned(boss: Node)
signal boss_phase_changed(boss_id: String, phase: int)
signal boss_defeated(boss_id: String)
signal summon_requested(enemy_id: String, count: int, around: Vector2)
signal wave_started(index: int, total: int)
signal wave_cleared(index: int)
signal checkpoint_reached(checkpoint_id: String)
signal screen_shake(strength: float, duration: float)
signal fx_dust(position: Vector2, amount: int)
