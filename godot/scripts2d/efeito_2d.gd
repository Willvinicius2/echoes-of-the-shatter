extends Node2D
## Efeito visual e de área das habilidades: anel que expande, disco/linha persistente com ticks,
## cone, raio em zigue-zague e marca de impacto atrasado. Desenho por código (sem arte).
## `ao_tick` roda a cada `tick` s; `ao_fim` roda quando acaba (marca de meteoro).

var forma := "anel"
var cor := Color.WHITE
var dur := 0.4
var raio := 100.0
var a := Vector2.ZERO          # linha: ponto inicial; raio: pontos
var b := Vector2.ZERO
var dir := Vector2.RIGHT       # cone
var angulo := 70.0             # cone, graus
var pts: PackedVector2Array = []
var tick := 0.0
var ao_tick := Callable()
var ao_fim := Callable()
var _t := 0.0
var _acc := 0.0

static func _novo(pai: Node, pos: Vector2, forma_: String, cor_: Color, dur_: float) -> Node2D:
	var e := load("res://scripts2d/efeito_2d.gd").new()
	e.forma = forma_
	e.cor = cor_
	e.dur = dur_
	e.global_position = pos
	e.z_index = -1
	pai.add_child(e)
	return e

static func anel(pai: Node, pos: Vector2, raio_: float, cor_: Color, dur_ := 0.35) -> Node2D:
	var e := _novo(pai, pos, "anel", cor_, dur_)
	e.raio = raio_
	return e

static func disco(pai: Node, pos: Vector2, raio_: float, cor_: Color, dur_: float, tick_: float, cb: Callable) -> Node2D:
	var e := _novo(pai, pos, "disco", cor_, dur_)
	e.raio = raio_
	e.tick = tick_
	e.ao_tick = cb
	return e

static func linha(pai: Node, de: Vector2, para: Vector2, espessura: float, cor_: Color, dur_: float, tick_: float, cb: Callable) -> Node2D:
	var e := _novo(pai, (de + para) * 0.5, "linha", cor_, dur_)
	e.a = de - e.global_position
	e.b = para - e.global_position
	e.raio = espessura
	e.tick = tick_
	e.ao_tick = cb
	return e

static func cone(pai: Node, pos: Vector2, dir_: Vector2, compr: float, ang: float, cor_: Color, dur_ := 0.25) -> Node2D:
	var e := _novo(pai, pos, "cone", cor_, dur_)
	e.dir = dir_.normalized()
	e.raio = compr
	e.angulo = ang
	return e

static func raio_zigue(pai: Node, de: Vector2, para: Vector2, cor_: Color, dur_: float) -> Node2D:
	var e := _novo(pai, de, "raio", cor_, dur_)
	e.pts = PackedVector2Array([Vector2.ZERO])
	var v := para - de
	var n := 6
	var perp := v.normalized().orthogonal()
	for i in range(1, n):
		var k := float(i) / n
		e.pts.append(v * k + perp * randf_range(-14.0, 14.0))
	e.pts.append(v)
	e.z_index = 5
	return e

## Marca de aviso que cresce até `raio_` e chama `cb` ao fim (meteoro).
static func marca(pai: Node, pos: Vector2, raio_: float, cor_: Color, dur_: float, cb: Callable) -> Node2D:
	var e := _novo(pai, pos, "marca", cor_, dur_)
	e.raio = raio_
	e.ao_fim = cb
	return e

func _physics_process(delta: float) -> void:
	_t += delta
	if tick > 0.0 and ao_tick.is_valid():
		_acc += delta
		while _acc >= tick:
			_acc -= tick
			ao_tick.call()
	queue_redraw()
	if _t >= dur:
		if ao_fim.is_valid():
			ao_fim.call()
		queue_free()

func _draw() -> void:
	var f := clampf(_t / dur, 0.0, 1.0)
	match forma:
		"anel":
			var r := raio * (0.25 + 0.75 * f)
			draw_circle(Vector2.ZERO, r, Color(cor, 0.22 * (1.0 - f)))
			draw_arc(Vector2.ZERO, r, 0.0, TAU, 48, Color(cor, 1.0 - f), 6.0 * (1.0 - f) + 1.0)
		"disco":
			var pulso := 0.5 + 0.5 * sin(_t * 6.0)
			var apaga := minf(1.0, (dur - _t) * 2.0)
			draw_circle(Vector2.ZERO, raio, Color(cor, (0.14 + 0.08 * pulso) * apaga))
			draw_arc(Vector2.ZERO, raio, 0.0, TAU, 48, Color(cor, 0.7 * apaga), 3.0)
		"linha":
			var apaga2 := minf(1.0, (dur - _t) * 2.0)
			var perp := (b - a).normalized().orthogonal() * raio
			var pol := PackedVector2Array([a + perp, b + perp, b - perp, a - perp])
			draw_colored_polygon(pol, Color(cor, 0.35 * apaga2))
			draw_polyline(PackedVector2Array([a + perp, b + perp, b - perp, a - perp, a + perp]), Color(cor.lightened(0.3), 0.8 * apaga2), 2.0)
		"cone":
			var pol2 := PackedVector2Array([Vector2.ZERO])
			var n := 12
			for i in n + 1:
				var ang := dir.angle() + deg_to_rad(angulo) * (float(i) / n - 0.5)
				pol2.append(Vector2.RIGHT.rotated(ang) * raio)
			draw_colored_polygon(pol2, Color(cor, 0.5 * (1.0 - f)))
		"raio":
			var linha_pts := pts
			draw_polyline(linha_pts, Color(cor, 0.35 * (1.0 - f)), 9.0)
			draw_polyline(linha_pts, Color(1, 1, 1, 1.0 - f), 3.0)
		"marca":
			draw_arc(Vector2.ZERO, raio, 0.0, TAU, 48, Color(cor, 0.9), 3.0)
			draw_circle(Vector2.ZERO, raio * f, Color(cor, 0.35))
