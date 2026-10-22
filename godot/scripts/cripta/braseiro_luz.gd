# Tremulação da luz âmbar do braseiro (OmniLight3D). Equivalente em GDScript do BraseiroLuz.cs.
extends OmniLight3D

@export var variacao := 0.35
var _base := 3.2
var _t := 0.0
var _fase := 0.0

func _ready() -> void:
	_fase = randf() * 100.0
	_base = light_energy

func _process(delta: float) -> void:
	_t += delta
	var n := sin((_t + _fase) * 9.1) * 0.5 + sin((_t + _fase) * 23.7) * 0.3 + sin((_t + _fase) * 4.3) * 0.2
	light_energy = _base * (1.0 + variacao * n)
