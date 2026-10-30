extends Node2D
## Número de dano que sobe e some.

var texto := ""
var cor := Color.WHITE
var tamanho := 20.0
var tempo := 0.65
var subida := 42.0
var _t := 0.0

func _ready() -> void:
	z_index = 200

func _process(delta: float) -> void:
	_t += delta
	if _t >= tempo:
		queue_free()
		return
	queue_redraw()

func _draw() -> void:
	var p := clampf(_t / tempo, 0.0, 1.0)
	var sobe := -subida * (1.0 - pow(1.0 - p, 2.0))
	var escala := 1.0 + 0.5 * maxf(0.0, 1.0 - p * 6.0)   # estoura no começo
	var fonte := ThemeDB.fallback_font
	var tam := int(tamanho * escala)
	var larg := fonte.get_string_size(texto, HORIZONTAL_ALIGNMENT_LEFT, -1, tam).x
	var c := cor
	c.a = 1.0 - maxf(0.0, (p - 0.55) / 0.45)
	var sombra := Color(0, 0, 0, c.a)
	var pos := Vector2(-larg / 2.0, sobe)
	fonte.draw_string(get_canvas_item(), pos + Vector2(2, 2), texto, HORIZONTAL_ALIGNMENT_LEFT, -1, tam, sombra)
	fonte.draw_string(get_canvas_item(), pos, texto, HORIZONTAL_ALIGNMENT_LEFT, -1, tam, c)
