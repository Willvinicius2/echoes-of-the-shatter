class_name ResourcePool
extends RefCounted
## Recurso do jogador (Ímpeto): enche em combate, esvazia fora de combate.

var current: float = 0.0
var max_value: float = 100.0
var decay_delay: float = 3.0
var decay_rate: float = 8.0
var _idle: float = 0.0


func _init(p_max: float = 100.0, p_delay: float = 3.0, p_rate: float = 8.0) -> void:
	max_value = maxf(0.0, p_max)
	decay_delay = p_delay
	decay_rate = p_rate


func gain(amount: float) -> void:
	current = clampf(current + maxf(0.0, amount), 0.0, max_value)
	_idle = 0.0


func can_afford(cost: float) -> bool:
	return current >= cost


func spend(cost: float) -> bool:
	if cost <= 0.0:
		return true
	if not can_afford(cost):
		return false
	current -= cost
	_idle = 0.0
	return true


## Marca que houve combate (adia o esvaziamento).
func mark_combat() -> void:
	_idle = 0.0


func update(delta: float) -> void:
	_idle += delta
	if _idle > decay_delay:
		current = maxf(0.0, current - decay_rate * delta)
