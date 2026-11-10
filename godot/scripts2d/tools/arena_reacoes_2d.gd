extends Node2D
## Arena do vídeo das reações: chão escuro, um riacho (água) e um braseiro e um pilar do mapa, tudo desenhado em _draw.
## Responde como a room_2d: perto_agua e estruturas_perto (reacoes_2d.gd).
const U = preload("res://scripts2d/efeitos_extra_util_2d.gd")
const Y_AGUA := Rect2(160, 470, 960, 90)
var _estruturas: Array = [{"tipo": "braseiro", "pos": Vector2(300, 255), "ate": 0}, {"tipo": "pilar", "pos": Vector2(960, 255), "ate": 0}]
var _t := 0.0

func _process(delta: float) -> void:
	_t += delta
	queue_redraw()

func perto_agua(p: Vector2, dist: float) -> bool:
	return Y_AGUA.grow(dist).has_point(p)

func estruturas_perto(p: Vector2, dist: float) -> Array:
	return _estruturas.filter(func(e): return e["pos"].distance_to(p) <= dist)

func _draw() -> void:
	z_index = -10
	draw_rect(Rect2(-400, -300, 2100, 1300), Color(0.09, 0.1, 0.11))
	for i in 22:   # lajes do chão
		draw_line(Vector2(160 + i * 45, 120), Vector2(160 + i * 45, 640), Color(0.13, 0.14, 0.15), 1.0)
	draw_rect(Y_AGUA, Color(0.1, 0.25, 0.42))
	for i in 12:
		var x := 190.0 + i * 80.0
		draw_line(Vector2(x, 495 + sin(_t * 2.0 + i) * 4.0), Vector2(x + 40, 495 + sin(_t * 2.0 + i + 1.0) * 4.0), Color(0.45, 0.7, 0.9, 0.6), 2.0)
		draw_line(Vector2(x + 30, 530 + sin(_t * 2.0 + i * 2.0) * 4.0), Vector2(x + 70, 530), Color(0.45, 0.7, 0.9, 0.5), 2.0)
	for e in _estruturas:
		var pos: Vector2 = e["pos"]
		if e["tipo"] == "braseiro":
			draw_rect(Rect2(pos + Vector2(-16, -4), Vector2(32, 12)), Color(0.25, 0.22, 0.2))
			draw_rect(Rect2(pos + Vector2(-22, -14), Vector2(44, 12)), Color(0.35, 0.3, 0.27))
			if Time.get_ticks_msec() >= int(e.get("apagado", 0)):
				U.chama(self, pos + Vector2(0, -14), 34.0, 22.0, _t * 8.0)
			else:
				draw_circle(pos + Vector2(0, -16), 5.0, Color(0.3, 0.3, 0.32))
		else:
			draw_rect(Rect2(pos + Vector2(-14, -70), Vector2(28, 80)), Color(0.4, 0.42, 0.46))
			draw_rect(Rect2(pos + Vector2(-20, -78), Vector2(40, 12)), Color(0.5, 0.52, 0.56))
			draw_rect(Rect2(pos + Vector2(-20, 6), Vector2(40, 10)), Color(0.32, 0.33, 0.37))
