extends Node2D
## Faísca de impacto: anel que expande e raios curtos.

var cor := Color.WHITE
var tempo := 0.14
var _t := 0.0
var _raios := []

func _ready() -> void:
	z_index = 150
	for i in 6:
		_raios.append(randf() * TAU)

func _process(delta: float) -> void:
	_t += delta
	if _t >= tempo:
		queue_free()
		return
	queue_redraw()

func _draw() -> void:
	var p := clampf(_t / tempo, 0.0, 1.0)
	var c := cor
	c.a = 1.0 - p
	draw_arc(Vector2.ZERO, 6.0 + 14.0 * p, 0.0, TAU, 20, c, 2.0)
	for a in _raios:
		var d := Vector2.from_angle(a)
		draw_line(d * (8.0 + 10.0 * p), d * (14.0 + 18.0 * p), c, 2.0)
