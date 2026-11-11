extends RefCounted
## Efeitos no chão dos golpes da Tecelã de Cascalho (tecela_2d.gd): a teia que desacelera e a onda da badalada. Tudo desenhado por
## código (sem arte nova, doc 36). Números vêm de data2d/tecela_golpes_2d.csv; a elipse achatada (0,6) é a mesma dos avisos de
## golpe dos outros inimigos, para o círculo do chão parecer assentado na perspectiva do jogo.

const Feel = preload("res://scripts2d/feel_2d.gd")

const ACHATA := 0.6
const COR_TEIA := Color(0.78, 0.92, 1.0)
const COR_SINO := Color(1.0, 0.72, 0.3)

## Teia no chão: nasce com um estalo, segura `duracao` s e desfaz nos últimos 0,6 s. Quem está dentro (o alvo) perde `lentidao`
## da velocidade de corrida; a esquiva sai dela sem perda.
class Teia extends Node2D:
	var alvo: Node2D
	var raio := 150.0
	var duracao := 5.0
	var lentidao := 0.5
	var _t := 0.0
	var _dentro := false
	func _ready() -> void:
		z_index = -1
	func _dist_chao(p: Vector2) -> float:   # distância no chão achatado (a mesma elipse do desenho)
		var d := p - global_position
		return Vector2(d.x, d.y / ACHATA).length()
	func _physics_process(delta: float) -> void:
		_t += delta
		if _t >= duracao:
			queue_free()
			return
		_dentro = alvo != null and is_instance_valid(alvo) and not alvo.esta_morto() and _dist_chao(alvo.global_position) <= raio
		if _dentro and alvo.has_method("aplicar_lentidao"):
			alvo.aplicar_lentidao(lentidao, 0.3)
		queue_redraw()
	func _draw() -> void:
		var fade := clampf((duracao - _t) / 0.6, 0.0, 1.0)
		var abre := clampf(_t / 0.18, 0.0, 1.0)   # estalo: a teia abre do centro para fora em 0,18 s
		var r := raio * (1.0 - pow(1.0 - abre, 3.0))
		var pulso := 0.85 + 0.15 * sin(_t * 5.0)
		var a := fade * (0.95 if _dentro else 0.8) * pulso
		draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, ACHATA))
		draw_circle(Vector2.ZERO, r, Color(0.35, 0.5, 0.62, 0.22 * fade))   # véu azulado: o chão pegajoso
		var raios := 9
		for i in raios:
			var ang := TAU * i / raios + 0.2
			draw_line(Vector2.ZERO, Vector2.from_angle(ang) * r, Color(COR_TEIA.r, COR_TEIA.g, COR_TEIA.b, a), 2.0)
		for k in [0.3, 0.52, 0.76, 1.0]:   # fios em volta, caídos entre os raios (corda entre dois pontos)
			var pts := PackedVector2Array()
			for i in raios + 1:
				var ang := TAU * i / raios + 0.2
				var rr: float = r * k * (0.93 if i % 2 == 1 and k < 1.0 else 1.0)
				pts.append(Vector2.from_angle(ang) * rr)
			draw_polyline(pts, Color(COR_TEIA.r, COR_TEIA.g, COR_TEIA.b, a * 0.9), 2.0 if k == 1.0 else 1.0)
		draw_arc(Vector2.ZERO, r, 0.0, TAU, 48, Color(1, 1, 1, a * 0.5), 1.0)

## Onda da badalada: anel de choque que sai do sino (centro) até `raio_max` a `vel` px/s. O anel fere uma vez quem estiver na faixa
## de `espessura` px quando ele passa; a esquiva (quadros de invulnerabilidade) atravessa sem dano.
class Onda extends Node2D:
	var alvo: Node2D
	var raio_max := 560.0
	var vel := 420.0
	var dano := 20.0
	var espessura := 46.0
	var _r := 0.0
	var _acertou := false
	func _ready() -> void:
		z_index = 5
	func _physics_process(delta: float) -> void:
		var antes := _r
		_r += vel * delta
		if _r - espessura * 0.5 >= raio_max:
			queue_free()
			return
		if not _acertou and alvo != null and is_instance_valid(alvo) and alvo.has_method("take_damage") and not (alvo.has_method("esta_morto") and alvo.esta_morto()):
			var d := alvo.global_position - global_position
			var dist := Vector2(d.x, d.y / ACHATA).length()
			if dist >= antes - espessura * 0.5 and dist <= _r + espessura * 0.5:
				_acertou = true   # uma vez só: se estava na esquiva, o anel passa e não fere mais
				alvo.take_damage(dano, global_position)
		queue_redraw()
	func _draw() -> void:
		var f := clampf(_r / raio_max, 0.0, 1.0)
		var a := 1.0 - pow(f, 2.0) * 0.85
		draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, ACHATA))
		draw_arc(Vector2.ZERO, _r, 0.0, TAU, 72, Color(COR_SINO.r, COR_SINO.g, COR_SINO.b, 0.28 * a), espessura)
		draw_arc(Vector2.ZERO, _r, 0.0, TAU, 72, Color(COR_SINO.r, COR_SINO.g, COR_SINO.b, 0.85 * a), espessura * 0.35)
		draw_arc(Vector2.ZERO, _r, 0.0, TAU, 72, Color(1.0, 0.95, 0.8, a), 3.0)
		draw_arc(Vector2.ZERO, maxf(_r - espessura * 0.8, 1.0), 0.0, TAU, 72, Color(COR_SINO.r, COR_SINO.g, COR_SINO.b, 0.4 * a), 2.0)   # eco logo atrás
