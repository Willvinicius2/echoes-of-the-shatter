class_name GuardMeter
extends RefCounted
## Quebra de guarda: acumula; ao encher, o alvo fica vulnerável/atordoado por um tempo.

var max_value: float = 0.0
var current: float = 0.0
var stun_duration: float = 1.0
var decay_rate: float = 10.0
var decay_delay: float = 1.5
var broken_remaining: float = 0.0
var _since_hit: float = 0.0


func configure(p_max: float, p_stun: float, p_decay: float) -> void:
	max_value = maxf(0.0, p_max)
	stun_duration = maxf(0.0, p_stun)
	decay_rate = maxf(0.0, p_decay)
	reset()


func reset() -> void:
	current = 0.0
	broken_remaining = 0.0
	_since_hit = 0.0


func is_broken() -> bool:
	return broken_remaining > 0.0


func fraction() -> float:
	if max_value <= 0.0:
		return 0.0
	return clampf(current / max_value, 0.0, 1.0)


## Retorna true se este acúmulo quebrou a guarda.
func add(amount: float) -> bool:
	if max_value <= 0.0 or amount <= 0.0 or is_broken():
		return false
	current += amount
	_since_hit = 0.0
	if current >= max_value:
		current = 0.0
		broken_remaining = stun_duration
		return true
	return false


func update(delta: float) -> void:
	_since_hit += delta
	if broken_remaining > 0.0:
		broken_remaining = maxf(0.0, broken_remaining - delta)
	elif _since_hit > decay_delay:
		current = maxf(0.0, current - decay_rate * delta)
