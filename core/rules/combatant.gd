class_name Combatant
extends RefCounted
## Estado de combate de uma entidade (sem Node): atributos, vida, barreira,
## guarda, efeitos e gatilhos. Cenas apenas leem e desenham este estado.

var id: String = ""
var stats: StatBlock = StatBlock.new()
var life: float = 1.0
var barrier: float = 0.0
var guard: GuardMeter = GuardMeter.new()
var effects: EffectSet
var triggers: TriggerSet = TriggerSet.new()
var invulnerable: bool = false
## Escudo frontal (percentual de redução) e arco de cobertura em graus.
var frontal_shield_reduction: float = 0.0
var shield_arc_degrees: float = 0.0


func _init() -> void:
	effects = EffectSet.new(stats)


func max_life() -> float:
	return stats.get_value("max_life")


func reset() -> void:
	life = max_life()
	barrier = 0.0
	invulnerable = false
	guard.reset()


func is_dead() -> bool:
	return life <= 0.0


func heal(amount: float) -> void:
	if is_dead():
		return
	life = clampf(life + maxf(0.0, amount), 0.0, max_life())


## Aplica um resultado de golpe já calculado.
func take(r: HitResult) -> void:
	if r.invulnerable or r.evaded:
		return
	barrier = maxf(0.0, barrier - r.barrier_absorbed)
	life = maxf(0.0, life - r.life_damage)
	if r.guard_added > 0.0:
		r.guard_broken = guard.add(r.guard_added)
	r.killed = life <= 0.0


func update(delta: float) -> void:
	guard.update(delta)
	triggers.update(delta)
	for t: Dictionary in effects.update(delta):
		take(DamageCalc.resolve_dot(self, float(t["amount"]), int(t["damage_type"])))
	life = minf(life, max_life())
