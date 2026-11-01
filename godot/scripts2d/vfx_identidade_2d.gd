extends RefCounted
## Identidade visual por elemento nas flechas e nos acertos do Arqueiro (doc 33, seção 9).
## Cada elemento tem forma, rastro, impacto e movimento próprios, para a flecha não virar "uma flecha colorida":
##   raio   = zigue-zague elétrico que treme, faíscas e galhos curtos; acerto = estrela de arcos.
##   veneno = rastro de gosma que ondula e pingos que caem; acerto = respingo e poça no chão.
##   gelo   = lascas de cristal que se soltam e giram, geada no rastro; acerto = estilhaços radiais e anel de geada.
##   fogo   = língua de chama afilada que treme, brasas que sobem; acerto = onda de fogo, brasas e marca queimada.
## Tudo é desenho vetorial em UM nó por flecha (um `_draw`), sem textura nova, sem partícula de GPU.
## Orçamento: no máximo MAX_FLECHAS + MAX_IMPACTOS nós vivos ao mesmo tempo (grupo `vfx_ident`);
## acima disso a flecha só perde o enfeite. Números daqui são só de aparência (tempos, tamanhos); nada de balanceamento.

const MAX_FLECHAS := 10
const MAX_IMPACTOS := 8
const GRUPO := "vfx_ident"

const PAL := {
	"raio": [Color("F4FBFF"), Color("5FA8FF"), Color("14284F")],
	"veneno": [Color("E6FF8A"), Color("5CD12B"), Color("123D1A")],
	"gelo": [Color("F0FBFF"), Color("7FD3F2"), Color("123A5C")],
	"fogo": [Color("FFE27A"), Color("FF7A1F"), Color("5A1408")],
}

## Pendura o rastro de identidade na flecha. Chamar logo depois de `lancar_flecha` (e de definir `cor_fx`).
static func anexar(flecha: Node, elemento: String) -> void:
	if flecha == null or not PAL.has(elemento) or not flecha.is_inside_tree():
		return
	if flecha.get_tree().get_nodes_in_group(GRUPO).size() >= MAX_FLECHAS + MAX_IMPACTOS:
		return
	var n := Rastro.new()
	n.iniciar(flecha, elemento)
	flecha.add_child(n)
	flecha.body_entered.connect(func(corpo: Node):
		if is_instance_valid(flecha) and flecha.is_inside_tree() and corpo != null:
			impacto(flecha.get_parent(), flecha.global_position + Vector2(0, -30), elemento, flecha.velocity.normalized()))

## Impacto avulso (também serve para zonas e arautos).
static func impacto(cena: Node, pos: Vector2, elemento: String, dir := Vector2.ZERO, escala := 1.0) -> void:
	if cena == null or not cena.is_inside_tree() or not PAL.has(elemento):
		return
	if cena.get_tree().get_nodes_in_group(GRUPO).size() >= MAX_FLECHAS + MAX_IMPACTOS:
		return
	var n := Impacto.new()
	n.iniciar(elemento, dir, escala)
	n.global_position = pos
	cena.add_child.call_deferred(n)

static func _aditivo() -> CanvasItemMaterial:
	var m := CanvasItemMaterial.new()
	m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	return m

# ---------------------------------------------------------------------------------------------------------------------

class Rastro extends Node2D:
	var _el := ""
	var _flecha: Node2D
	var _t := 0.0
	var _hist: Array = []        # pontos do mundo, do mais velho ao mais novo
	var _part: Array = []        # [pos, vel, vida, vida_max, tam, rot, vrot]
	var _jit := PackedFloat32Array()
	var _acc := 0.0
	var _vivo := true
	var _fade := 0.0
	var _rng := RandomNumberGenerator.new()

	static func _add() -> CanvasItemMaterial:
		var m := CanvasItemMaterial.new()
		m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		return m

	func iniciar(f: Node2D, el: String) -> void:
		_flecha = f
		_el = el
		_rng.randomize()
		top_level = true
		z_index = 4
		add_to_group("vfx_ident")
		if el != "veneno":
			material = _add()
		f.tree_exiting.connect(_soltar, CONNECT_ONE_SHOT)
		_jit.resize(24)
		_sortear()

	func _sortear() -> void:
		for i in _jit.size():
			_jit[i] = _rng.randf_range(-1.0, 1.0)

	func _soltar() -> void:
		# a flecha some; o enfeite termina de esvanecer sozinho na cena
		if not _vivo:
			return
		_vivo = false
		var cena := get_parent().get_parent() if get_parent() != null else null
		if cena != null:
			reparent.call_deferred(cena)

	func _process(delta: float) -> void:
		_t += delta
		global_position = Vector2.ZERO
		if _vivo and is_instance_valid(_flecha):
			var p := _flecha.global_position + Vector2(0, -30)
			if _hist.is_empty() or _hist.back().distance_to(p) > 5.0:
				_hist.append(p)
				if _hist.size() > 14:
					_hist.pop_front()
			_acc += delta
			_soltar_particulas(p)
			if _el == "raio" and fmod(_t, 0.045) < delta:
				_sortear()
		else:
			_fade += delta
			if _hist.size() > 0:
				_hist.pop_front()
		for q in _part:
			q[2] -= delta
			q[0] += q[1] * delta
			q[5] += q[6] * delta
			match _el:
				"veneno":
					q[1].y += 420.0 * delta
				"fogo":
					q[1].y -= 60.0 * delta
					q[1].x *= 0.97
				"gelo":
					q[1] *= 0.94
		_part = _part.filter(func(q): return q[2] > 0.0)
		queue_redraw()
		if not _vivo and _part.is_empty() and _hist.is_empty():
			queue_free()

	func _soltar_particulas(p: Vector2) -> void:
		var taxa: float = {"raio": 26.0, "veneno": 11.0, "gelo": 18.0, "fogo": 30.0}[_el]
		var v: Vector2 = _flecha.velocity.normalized()
		var perp := v.orthogonal()
		while _acc >= 1.0 / taxa and _part.size() < 22:
			_acc -= 1.0 / taxa
			match _el:
				"raio":
					_part.append([p - v * _rng.randf_range(2, 22), perp * _rng.randf_range(-90, 90) - v * 40.0, _rng.randf_range(0.10, 0.2), 0.2, _rng.randf_range(2.0, 4.0), 0.0, 0.0])
				"veneno":
					_part.append([p - v * _rng.randf_range(4, 26) + perp * _rng.randf_range(-4, 4), Vector2(_rng.randf_range(-12, 12), _rng.randf_range(-30, 0)), _rng.randf_range(0.28, 0.42), 0.4, _rng.randf_range(2.0, 3.5), 0.0, 0.0])
				"gelo":
					_part.append([p - v * _rng.randf_range(2, 20) + perp * _rng.randf_range(-6, 6), perp * _rng.randf_range(-55, 55) - v * 25.0, _rng.randf_range(0.35, 0.6), 0.6, _rng.randf_range(2.5, 5.0), _rng.randf() * TAU, _rng.randf_range(-7.0, 7.0)])
				"fogo":
					_part.append([p - v * _rng.randf_range(2, 24) + perp * _rng.randf_range(-5, 5), Vector2(_rng.randf_range(-20, 20), _rng.randf_range(-50, -15)), _rng.randf_range(0.4, 0.75), 0.75, _rng.randf_range(1.8, 3.6), 0.0, 0.0])

	func _draw() -> void:
		var c: Array = PAL[_el]
		var n := _hist.size()
		var fade := clampf(1.0 - _fade * 3.0, 0.0, 1.0)
		if n >= 2:
			match _el:
				"raio": _rastro_raio(c, n, fade)
				"veneno": _rastro_veneno(c, n, fade)
				"gelo": _rastro_gelo(c, n, fade)
				"fogo": _rastro_fogo(c, n, fade)
		for q in _part:
			var a := clampf(q[2] / q[3], 0.0, 1.0)
			match _el:
				"raio":
					draw_line(q[0], q[0] + q[1].normalized() * q[4] * 2.5, Color(c[0], a), 1.5)
				"veneno":
					draw_circle(q[0], q[4], Color(c[1], a * 0.9))
					draw_circle(q[0] + Vector2(-0.6, -0.8), q[4] * 0.45, Color(c[0], a))
				"gelo":
					_cristal(q[0], q[4], q[5], Color(c[1], a), Color(c[0], a))
				"fogo":
					var cor: Color = c[0].lerp(c[1], 1.0 - a).lerp(c[2], clampf(1.0 - a * 1.6, 0.0, 1.0))
					draw_circle(q[0], q[4] * (0.4 + a), Color(cor, a))

	func _dir(i: int, n: int) -> Vector2:
		return (_hist[mini(i + 1, n - 1)] - _hist[maxi(i - 1, 0)]).normalized()

	func _cristal(p: Vector2, r: float, rot: float, cor: Color, brilho: Color) -> void:
		var pts := PackedVector2Array([p + Vector2(0, -r * 1.7).rotated(rot), p + Vector2(r, 0).rotated(rot), p + Vector2(0, r * 1.7).rotated(rot), p + Vector2(-r, 0).rotated(rot)])
		draw_colored_polygon(pts, cor)
		draw_line(pts[0], pts[2], brilho, 1.0)

	func _rastro_raio(c: Array, n: int, fade: float) -> void:
		var pts := PackedVector2Array()
		for i in n:
			var k := float(i) / float(maxi(1, n - 1))
			pts.append(_hist[i] + _dir(i, n).orthogonal() * _jit[i % _jit.size()] * 7.0 * (0.3 + k))
		draw_polyline(pts, Color(c[1], 0.45 * fade), 5.0)
		draw_polyline(pts, Color(c[0], 0.95 * fade), 1.6)
		if n > 4:
			var i2 := 1 + int(absf(_jit[3]) * float(n - 3))
			draw_line(pts[i2], pts[i2] + Vector2(_jit[5], _jit[7]).normalized() * 12.0, Color(c[0], 0.8 * fade), 1.2)

	func _rastro_veneno(c: Array, n: int, fade: float) -> void:
		for i in n:
			var k := float(i + 1) / float(n)
			var p: Vector2 = _hist[i] + _dir(i, n).orthogonal() * sin(_t * 14.0 + float(i) * 0.9) * 3.5 * k
			draw_circle(p, 1.5 + 4.2 * k, Color(c[2], 0.35 * k * fade))
			draw_circle(p, 0.8 + 2.6 * k, Color(c[1], 0.6 * k * fade))

	func _rastro_gelo(c: Array, n: int, fade: float) -> void:
		var pts := PackedVector2Array()
		for i in n:
			pts.append(_hist[i])
		draw_polyline(pts, Color(c[1], 0.25 * fade), 6.0)
		draw_polyline(pts, Color(c[0], 0.7 * fade), 1.4)
		for i in range(0, n, 3):
			draw_circle(_hist[i], 1.4, Color(c[0], 0.7 * float(i) / float(n) * fade))

	func _rastro_fogo(c: Array, n: int, fade: float) -> void:
		# língua de fogo: segmentos cada vez mais grossos até a ponta, tremendo
		for i in range(1, n):
			var k := float(i) / float(maxi(1, n - 1))
			var w := (2.0 + 12.0 * k) * (0.85 + 0.2 * sin(_t * 30.0 + float(i)))
			draw_line(_hist[i - 1], _hist[i], Color(c[2].lerp(c[1], k), 0.55 * fade), w)
			draw_line(_hist[i - 1], _hist[i], Color(c[0], 0.8 * k * fade), w * 0.35)

# ---------------------------------------------------------------------------------------------------------------------

class Impacto extends Node2D:
	var _el := ""
	var _t := 0.0
	var _dur := 0.4
	var _esc := 1.0
	var _rng := RandomNumberGenerator.new()
	var _raios: Array = []   # [angulo, comprimento, extra]

	static func _add() -> CanvasItemMaterial:
		var m := CanvasItemMaterial.new()
		m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		return m

	func iniciar(el: String, _dir: Vector2, esc: float) -> void:
		_el = el
		_esc = esc
		_rng.randomize()
		_dur = {"raio": 0.28, "veneno": 1.1, "gelo": 0.5, "fogo": 0.55}[el]
		add_to_group("vfx_ident")
		z_index = 4
		if el != "veneno":
			material = _add()
		var qtd: int = {"raio": 6, "veneno": 7, "gelo": 9, "fogo": 8}[el]
		for i in qtd:
			_raios.append([TAU * float(i) / float(qtd) + _rng.randf_range(-0.3, 0.3), _rng.randf_range(0.6, 1.0), _rng.randf()])

	func _process(delta: float) -> void:
		_t += delta
		if _t >= _dur:
			queue_free()
		else:
			queue_redraw()

	func _draw() -> void:
		var c: Array = PAL[_el]
		var k := _t / _dur
		var a := 1.0 - k
		var s := _esc
		match _el:
			"raio":
				draw_circle(Vector2.ZERO, 10.0 * s * a, Color(c[0], 0.9 * a))
				for r in _raios:
					var d := Vector2.from_angle(r[0])
					var reach: float = 34.0 * s * r[1] * minf(1.0, k * 3.5)
					var meio: Vector2 = d * reach * 0.5 + d.orthogonal() * (r[2] - 0.5) * 12.0
					var linha := PackedVector2Array([Vector2.ZERO, meio, d * reach])
					draw_polyline(linha, Color(c[1], 0.8 * a), 3.0)
					draw_polyline(linha, Color(c[0], a), 1.2)
			"veneno":
				var dentro := minf(1.0, k * 4.0)
				for r in _raios:
					var d := Vector2.from_angle(r[0])
					var alt: float = sin(minf(1.0, k * 2.2) * PI) * 16.0 * r[1]
					var p: Vector2 = d * 26.0 * s * dentro * r[1] + Vector2(0, -alt * 0.5)
					draw_circle(p, 2.6 * (1.0 - k * 0.5), Color(c[1], a))
				draw_set_transform(Vector2(0, 14), 0.0, Vector2(1.0, 0.5))
				draw_circle(Vector2.ZERO, 22.0 * s * dentro, Color(c[2], 0.55 * minf(1.0, a * 2.0)))
				draw_circle(Vector2.ZERO, 15.0 * s * dentro, Color(c[1], 0.45 * minf(1.0, a * 2.0)))
				draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
			"gelo":
				var reach := 8.0 + 42.0 * s * (1.0 - pow(1.0 - k, 2.0))
				for r in _raios:
					var d := Vector2.from_angle(r[0])
					var p: Vector2 = d * reach * r[1]
					var rot: float = r[0] + k * 6.0
					var tam: float = (3.0 + 3.0 * r[2]) * a
					var pts := PackedVector2Array([p + Vector2(0, -tam * 1.8).rotated(rot), p + Vector2(tam, 0).rotated(rot), p + Vector2(0, tam * 1.8).rotated(rot), p + Vector2(-tam, 0).rotated(rot)])
					draw_colored_polygon(pts, Color(c[1], a))
					draw_line(pts[0], pts[2], Color(c[0], a), 1.0)
				draw_arc(Vector2.ZERO, reach * 0.7, 0.0, TAU, 24, Color(c[0], 0.7 * a), 2.0)
			"fogo":
				draw_set_transform(Vector2(0, 14), 0.0, Vector2(1.0, 0.5))
				draw_circle(Vector2.ZERO, 20.0 * s, Color(c[2], 0.5 * a))
				draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
				var reach2 := 10.0 + 34.0 * s * (1.0 - pow(1.0 - k, 2.0))
				draw_circle(Vector2.ZERO, reach2 * 0.6, Color(c[1], 0.55 * a))
				draw_circle(Vector2.ZERO, reach2 * 0.35, Color(c[0], 0.9 * a))
				draw_arc(Vector2.ZERO, reach2, 0.0, TAU, 28, Color(c[1], 0.8 * a), 2.5)
				for r in _raios:
					var d := Vector2.from_angle(r[0])
					var p: Vector2 = d * reach2 * r[1] + Vector2(0, -k * 26.0 * r[2])
					draw_circle(p, 2.2 * a + 0.5, Color(c[0].lerp(c[1], k), a))
