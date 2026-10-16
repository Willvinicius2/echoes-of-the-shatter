class_name EffectSet
extends RefCounted
## Efeitos ativos com duração, tick e regra de acúmulo (renovar, acumular, mais forte).
## Se houver StatBlock, efeitos com `stat` aplicam um modificador enquanto durarem.

class Active extends RefCounted:
	var def: EffectData
	var remaining: float = 0.0
	var stacks: int = 1
	var magnitude: float = 1.0
	var tick_acc: float = 0.0

var _stats: StatBlock
var _active: Dictionary = {}


func _init(stats: StatBlock = null) -> void:
	_stats = stats


func has(effect_id: String) -> bool:
	return _active.has(effect_id)


func stacks_of(effect_id: String) -> int:
	if not _active.has(effect_id):
		return 0
	var a: Active = _active[effect_id]
	return a.stacks


func remaining_of(effect_id: String) -> float:
	if not _active.has(effect_id):
		return 0.0
	var a: Active = _active[effect_id]
	return a.remaining


## Aplica o efeito segundo a regra de acúmulo. Retorna true se algo mudou.
func apply(def: EffectData, magnitude: float = -1.0) -> bool:
	var mag: float = def.magnitude if magnitude < 0.0 else magnitude
	var dur: float = maxf(def.duration, 0.0)
	if not _active.has(def.id):
		var n: Active = Active.new()
		n.def = def
		n.remaining = dur
		n.magnitude = mag
		_active[def.id] = n
		_sync_mod(n)
		return true
	var a: Active = _active[def.id]
	match def.stack_rule:
		EffectData.StackRule.REFRESH:
			a.remaining = dur
			a.magnitude = mag
		EffectData.StackRule.STACK:
			a.stacks = mini(a.stacks + 1, maxi(def.max_stacks, 1))
			a.remaining = dur
			a.magnitude = maxf(a.magnitude, mag)
		EffectData.StackRule.STRONGEST:
			if mag < a.magnitude:
				return false
			a.magnitude = mag
			a.remaining = dur
	_sync_mod(a)
	return true


func remove(effect_id: String) -> void:
	if not _active.has(effect_id):
		return
	if _stats != null:
		_stats.remove_source("effect:" + effect_id)
	_active.erase(effect_id)


## Avança o tempo. Retorna os ticks de dano: {effect_id, amount, damage_type}.
func update(delta: float) -> Array[Dictionary]:
	var ticks: Array[Dictionary] = []
	var expired: Array[String] = []
	for id: String in _active.keys():
		var a: Active = _active[id]
		var step: float = minf(delta, a.remaining)
		a.remaining -= delta
		if a.def.tick_interval > 0.0 and a.def.tick_damage > 0.0:
			a.tick_acc += step
			while a.tick_acc >= a.def.tick_interval - 0.000001:
				a.tick_acc -= a.def.tick_interval
				ticks.append({
					"effect_id": id,
					"amount": a.def.tick_damage * a.magnitude * float(a.stacks),
					"damage_type": a.def.damage_type,
				})
		if a.remaining <= 0.0:
			expired.append(id)
	for id in expired:
		remove(id)
	return ticks


func _sync_mod(a: Active) -> void:
	if _stats == null or a.def.stat == "":
		return
	var src: String = "effect:" + a.def.id
	_stats.remove_source(src)
	_stats.add(a.def.stat, a.def.mod_kind, a.magnitude * float(a.stacks), a.def.tags, src)
