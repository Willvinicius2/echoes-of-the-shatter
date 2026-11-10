extends RefCounted
## Anéis de runas e sigilo do chão das salas, tirados de room_2d.gd. `aneis` e `lajes` vêm do mapa carregado.

## Anéis de runas: um sulco de pedra escuro com fio dourado dentro e glifos desenhados (losango, triângulo, cruz,
## círculo, ampulheta, setas) sobre plaquetas escuras, espaçados por igual. Com `sigilo` o anel vira um círculo
## fechado de glifos com halo, sem sulco (marca o centro da arena).
static func desenhar(raiz: Node2D, aneis: Array, lajes: Array) -> void:
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	for a in aneis:
		var idx: int = a["laje"]
		if idx < 0 or idx >= lajes.size():
			continue
		var m: Dictionary = lajes[idx]
		var raio_anel: float = m["raio"] * float(a["fator"])
		var pts := contorno(m["centro"], raio_anel, 11 + idx, 0.0)
		var sigilo: bool = a.get("sigilo", false)
		var n := pts.size()
		pts.append(pts[0])
		if sigilo:
			var halo := Sprite2D.new()
			halo.texture = _halo_dourado()
			halo.position = m["centro"]
			halo.scale = Vector2.ONE * (raio_anel * 2.8 / 128.0)
			halo.material = mat
			raiz.add_child(halo)
			for escala in [1.0, 0.62]:   # dois círculos fechados: o sigilo lê como um círculo, não como fragmentos
				var circ := Line2D.new()
				circ.points = contorno(m["centro"], raio_anel * escala, 11 + idx, 0.0)
				circ.closed = true
				circ.width = 2.0
				circ.default_color = Color(1.0, 0.8, 0.35, 0.6)
				circ.material = mat
				raiz.add_child(circ)
		else:
			var sulco := Line2D.new()   # sulco escavado na pedra
			sulco.points = pts
			sulco.width = 11.0
			sulco.default_color = Color(0.05, 0.04, 0.04, 0.75)
			raiz.add_child(sulco)
			var brilho := Line2D.new()
			brilho.points = pts
			brilho.width = 7.0
			brilho.default_color = Color(1.0, 0.7, 0.22, 0.14)
			brilho.material = mat
			raiz.add_child(brilho)
			var fio := Line2D.new()
			fio.points = pts
			fio.width = 2.0
			fio.default_color = Color(1.0, 0.8, 0.35, 0.5)
			fio.material = mat
			raiz.add_child(fio)
		var comprimento := 0.0
		for k in n:
			comprimento += pts[k].distance_to(pts[k + 1])
		var qtd := 8 if sigilo else maxi(int(comprimento / 70.0), 8)
		var passo := comprimento / qtd
		var andou := passo * 0.5
		var cont := 0
		for k in n:
			var seg := pts[k].distance_to(pts[k + 1])
			while andou < seg:
				var c := pts[k].lerp(pts[k + 1], andou / maxf(seg, 0.001))
				var ang: float = (pts[k + 1] - pts[k]).angle() if not sigilo else (c - m["centro"]).angle() - PI * 0.5
				_glifo(raiz, c, ang, 11.0 if not sigilo else 9.0, cont % 6, mat)
				cont += 1
				andou += passo
			andou -= seg

## Um glifo de runa em traços dourados aditivos sobre uma plaqueta escura. `tam` é a meia-altura em px.
static func _glifo(raiz: Node2D, pos: Vector2, ang: float, tam: float, tipo: int, mat: CanvasItemMaterial) -> void:
	var no := Node2D.new()
	no.position = pos
	no.rotation = ang
	raiz.add_child(no)
	var placa := Polygon2D.new()
	placa.polygon = PackedVector2Array([Vector2(-tam, -tam * 1.25), Vector2(tam, -tam * 1.25), Vector2(tam, tam * 1.25), Vector2(-tam, tam * 1.25)])
	placa.color = Color(0.05, 0.04, 0.04, 0.6)
	no.add_child(placa)
	var t := tam * 0.75
	var tracos: Array = []
	match tipo:
		0:   # losango com ponto
			tracos = [[Vector2(0, -t), Vector2(t * 0.7, 0), Vector2(0, t), Vector2(-t * 0.7, 0), Vector2(0, -t)], [Vector2(0, -2), Vector2(0, 2)]]
		1:   # triângulo com barra
			tracos = [[Vector2(0, -t), Vector2(t * 0.8, t * 0.8), Vector2(-t * 0.8, t * 0.8), Vector2(0, -t)], [Vector2(0, -t * 0.2), Vector2(0, t * 0.8)]]
		2:   # cruz com travessa
			tracos = [[Vector2(0, -t), Vector2(0, t)], [Vector2(-t * 0.7, -t * 0.2), Vector2(t * 0.7, -t * 0.2)], [Vector2(-t * 0.4, t * 0.6), Vector2(t * 0.4, t * 0.6)]]
		3:   # círculo cortado
			var circ: Array = []
			for q in 9:
				circ.append(Vector2(cos(TAU * q / 8.0), sin(TAU * q / 8.0)) * t * 0.7)
			tracos = [circ, [Vector2(0, -t), Vector2(0, t)]]
		4:   # ampulheta
			tracos = [[Vector2(-t * 0.7, -t), Vector2(t * 0.7, -t), Vector2(-t * 0.7, t), Vector2(t * 0.7, t), Vector2(-t * 0.7, -t)]]
		_:   # setas empilhadas
			tracos = [[Vector2(-t * 0.7, -t * 0.2), Vector2(0, -t), Vector2(t * 0.7, -t * 0.2)], [Vector2(-t * 0.7, t * 0.7), Vector2(0, t * 0.1), Vector2(t * 0.7, t * 0.7)]]
	for tr in tracos:
		var l := Line2D.new()
		l.points = PackedVector2Array(tr)
		l.width = 2.0
		l.default_color = Color(1.0, 0.84, 0.4, 0.95)
		l.material = mat
		no.add_child(l)

static func _halo_dourado() -> Texture2D:
	var g := Gradient.new()
	g.set_color(0, Color(1.0, 0.75, 0.3, 0.32))
	g.set_color(1, Color(1.0, 0.6, 0.2, 0.0))
	var t := GradientTexture2D.new()
	t.gradient = g
	t.width = 128
	t.height = 128
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	return t

## Círculo ondulado (raio em px) para as manchas de laje; a mesma semente dá o mesmo contorno.
static func contorno(centro: Vector2, raio: float, semente: int, serrilha := 0.0, n_pts := 0) -> PackedVector2Array:
	var pts := PackedVector2Array()
	var n := n_pts if n_pts > 0 else maxi(48, int(raio / 2.5))
	var f1 := 2.0 + posmod(semente * 7, 3)
	var f2 := 5.0 + posmod(semente * 13, 4)
	for k in n:
		var a := k * TAU / n
		var onda := 0.12 * sin(a * f1 + semente) + 0.06 * sin(a * f2 + semente * 2.3) + 0.03 * sin(a * 11.0 + semente * 0.7)
		onda += serrilha * (float(posmod(hash(Vector2i(k, semente)), 100)) / 100.0 - 0.5)   # beira irregular, sem curva lisa
		pts.append(centro + Vector2(cos(a), sin(a)) * raio * (1.0 + onda))
	return pts
