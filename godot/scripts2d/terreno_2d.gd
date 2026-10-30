extends RefCounted
## Caminho de pedra, riacho e vaga-lumes de uma sala, desenhados por cima do piso.
## Os pontos vêm do arquivo de sala (`@caminho largura x,y ...` e `@riacho largura x,y ...`, em células).

const Csv = preload("res://scripts2d/csv2d.gd")
const Ambiente = preload("res://scripts2d/ambiente_2d.gd")

const AGUA_SHADER := """
shader_type canvas_item;
uniform vec4 fundo : source_color = vec4(0.06, 0.2, 0.24, 1.0);
uniform vec4 brilho : source_color = vec4(0.62, 0.86, 0.86, 1.0);
void fragment() {
	vec2 uv = UV;
	float fluxo = sin(uv.y * 5.0 + TIME * 0.7) * 0.5 + 0.5;
	vec4 base = fundo * (0.85 + 0.25 * fluxo);
	float onda = sin(uv.x * 16.0 + sin(uv.y * 11.0 + TIME * 1.1) * 2.2 + TIME * 1.6);
	float esparso = sin(uv.x * 2.7 + uv.y * 4.1 + TIME * 0.35) * sin(uv.x * 1.3 - uv.y * 3.3 + 1.7);
	float risco = smoothstep(0.93, 1.0, onda) * smoothstep(0.0, 0.5, esparso);
	COLOR = mix(base, brilho, risco * 0.85);
}
""" 

## Curva suave (Catmull-Rom) por pontos em px, com passo aproximado `passo` px.
static func spline(pts: Array, passo := 10.0) -> PackedVector2Array:
	var out := PackedVector2Array()
	for i in pts.size() - 1:
		var p0: Vector2 = pts[maxi(i - 1, 0)]
		var p1: Vector2 = pts[i]
		var p2: Vector2 = pts[i + 1]
		var p3: Vector2 = pts[mini(i + 2, pts.size() - 1)]
		var n := maxi(int(p1.distance_to(p2) / passo), 2)
		for k in n:
			var t := float(k) / n
			out.append(0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t * t * t))
	out.append(pts[pts.size() - 1])
	return out

## Contorno da faixa de largura `larg` em volta da curva, com borda irregular (determinística).
static func faixa(linha: PackedVector2Array, larg: float, ruido: float, semente: int) -> PackedVector2Array:
	var polis := Geometry2D.offset_polyline(linha, larg * 0.5, Geometry2D.JOIN_ROUND, Geometry2D.END_BUTT)
	if polis.is_empty():
		return PackedVector2Array()
	var poli: PackedVector2Array = polis[0]
	for i in poli.size():
		var f := float(i)
		poli[i] += Vector2(sin(f * 0.37 + semente) * 0.6 + sin(f * 1.1 + semente * 1.7) * 0.4, cos(f * 0.43 + semente * 0.5) * 0.6 + cos(f * 0.9 + semente) * 0.4) * ruido
	# a borda irregular pode se cruzar; offset_polygon limpa e o Polygon2D só triangula contornos simples
	var limpos := Geometry2D.offset_polygon(poli, 0.01, Geometry2D.JOIN_ROUND)
	var melhor := PackedVector2Array()
	var area := 0.0
	for c in limpos:
		var a := absf(_area(c))
		if a > area:
			area = a
			melhor = c
	return melhor

static func _area(p: PackedVector2Array) -> float:
	var a := 0.0
	for i in p.size():
		var q := p[(i + 1) % p.size()]
		a += p[i].x * q.y - q.x * p[i].y
	return a * 0.5

static func _poligono(parent: Node2D, pts: PackedVector2Array, cor: Color) -> Polygon2D:
	var pg := Polygon2D.new()
	pg.polygon = pts
	pg.color = cor
	parent.add_child(pg)
	return pg

static func montar(sala: Node2D, caminhos: Array, riachos: Array, grama: bool, tile: int) -> void:
	var raiz := Node2D.new()
	sala.add_child(raiz)
	if grama:
		_manchas_de_chao(raiz, sala, tile)
	var corpo_agua := StaticBody2D.new()
	corpo_agua.collision_layer = 8
	corpo_agua.collision_mask = 0
	sala.add_child(corpo_agua)
	var lajes := _textura_lajes()
	var aguas: Array = []
	var margens: Array = []
	for i in riachos.size():
		var r: Dictionary = riachos[i]
		var linha := spline(r["pts"])
		var margem := faixa(linha, r["larg"] * tile + 26.0, 4.0, 31 + i)
		var agua := faixa(linha, r["larg"] * tile, 3.0, 41 + i)
		if agua.is_empty():
			continue
		aguas.append(agua)
		margens.append(margem)
		_poligono(raiz, margem, Color(0.24, 0.2, 0.13))  # lama úmida, mais clara que a margem escura de antes
		_poligono(raiz, faixa(linha, r["larg"] * tile + 10.0, 3.0, 51 + i), Color(0.15, 0.13, 0.09))
		var pg := _poligono(raiz, agua, Color.WHITE)
		var mat := ShaderMaterial.new()
		mat.shader = Shader.new()
		mat.shader.code = AGUA_SHADER
		pg.material = mat
		pg.uv = agua
		pg.texture = lajes  # a UV só precisa de uma textura qualquer; o shader ignora a cor
	# Caminho: contorno limpo fora da água; dentro dela, pedras de travessia.
	var travessias: Array = []
	for i in caminhos.size():
		var c: Dictionary = caminhos[i]
		var linha := spline(c["pts"])
		var fc := faixa(linha, c["larg"] * tile, 4.0, 11 + i)
		var borda := faixa(linha, c["larg"] * tile + 16.0, 5.0, 21 + i)
		if fc.is_empty():
			continue
		var fora_agua_fc: Array = [fc]
		var fora_agua_borda: Array = [borda]
		for m in margens:
			fora_agua_fc = _subtrair(fora_agua_fc, m)
			fora_agua_borda = _subtrair(fora_agua_borda, m)
		for b in fora_agua_borda:
			_poligono(raiz, b, Color(0.14, 0.15, 0.09, 0.9))
		for q in fora_agua_fc:
			var pg := _poligono(raiz, q, Color(1, 1, 1))
			pg.texture = lajes
			pg.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
			pg.uv = q
			_lajes_soltas(raiz, q, 11 + i)
		var trecho := PackedVector2Array()
		for p in spline(c["pts"], 6.0):
			for ag in aguas:
				if Geometry2D.is_point_in_polygon(p, ag):
					trecho.append(p)
					break
		if trecho.size() >= 2:
			travessias.append(trecho)
			_pedras_de_travessia(raiz, trecho, lajes)
	# Colisão da água: livre só no corredor das pedras de travessia.
	var corredores: Array = []
	for t in travessias:
		var ext := PackedVector2Array([t[0] - (t[1] - t[0]).normalized() * 30.0])
		ext.append_array(t)
		ext.append(t[t.size() - 1] + (t[t.size() - 1] - t[t.size() - 2]).normalized() * 30.0)
		var polis := Geometry2D.offset_polyline(ext, 36.0, Geometry2D.JOIN_ROUND, Geometry2D.END_ROUND)
		if not polis.is_empty():
			corredores.append(polis[0])
	for agua in aguas:
		var blocos: Array = [agua]
		for cor in corredores:
			blocos = _subtrair(blocos, cor)
		for b in blocos:
			var cp := CollisionPolygon2D.new()
			cp.polygon = b
			corpo_agua.add_child(cp)
	_luz(sala, riachos, grama, tile)
	if grama:
		_vagalumes(sala, tile)

static func _subtrair(polis: Array, tira: PackedVector2Array) -> Array:
	var out: Array = []
	for p in polis:
		for q in Geometry2D.clip_polygons(p, tira):
			if not Geometry2D.is_polygon_clockwise(q):  # ignora buracos
				out.append(q)
	return out

## Pedra de travessia: laje irregular escura com borda clara, 4 ao longo do trecho que cruza a água.
static func _pedras_de_travessia(raiz: Node2D, trecho: PackedVector2Array, lajes: Texture2D) -> void:
	var n := 5
	for k in n:
		var p := trecho[int((trecho.size() - 1) * (k + 0.5) / n)]
		var raio := 31.0 + posmod(hash(Vector2i(k, 5)), 7)
		var pts := PackedVector2Array()
		for a in 9:
			var ang := TAU * a / 9.0
			var rr := raio * (0.85 + 0.3 * float(posmod(hash(Vector2i(a, k + 3)), 100)) / 100.0)
			pts.append(p + Vector2(cos(ang) * rr, sin(ang) * rr * 0.78))
		_poligono(raiz, _expandir(pts, p, 4.0), Color(0.1, 0.12, 0.12, 0.9)).z_index = 1
		var pg := _poligono(raiz, pts, Color(0.85, 0.88, 0.95))
		pg.texture = lajes
		pg.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
		pg.uv = pts
		pg.z_index = 1

static func _expandir(pts: PackedVector2Array, centro: Vector2, d: float) -> PackedVector2Array:
	var out := PackedVector2Array()
	for p in pts:
		out.append(p + (p - centro).normalized() * d)
	return out

## Lajes soltas e musgo espalhados pela borda do caminho.
static func _lajes_soltas(raiz: Node2D, contorno: PackedVector2Array, semente: int) -> void:
	var i := 2
	while i < contorno.size():
		var h := hash(Vector2i(i, semente + 5))
		var raio := 7.0 + posmod(h, 7)
		var c := contorno[i] + Vector2(posmod(h / 11, 11) - 5, posmod(h / 97, 9) - 4)
		var pts := PackedVector2Array()
		for a in 7:
			var ang := TAU * a / 7.0 + posmod(h, 6)
			pts.append(c + Vector2(cos(ang) * raio * (0.8 + 0.4 * posmod(h / (a + 2), 5) / 5.0), sin(ang) * raio * 0.7))
		var tom := 0.42 + 0.22 * float(posmod(h / 5, 100)) / 100.0
		var musgo: bool = posmod(h / 13, 4) == 0
		var cor := Color(0.28, 0.4, 0.2) if musgo else Color(tom, tom + 0.02, tom + 0.07)
		_poligono(raiz, _expandir(pts, c, 1.8), Color(0.08, 0.09, 0.08, 0.8)).z_index = 1
		_poligono(raiz, pts, cor).z_index = 1
		i += 7 + posmod(h / 3, 6)

## Manchas grandes e suaves de terra e grama amarelada sob tudo, para o gramado não ser textura chapada.
static func _manchas_de_chao(raiz: Node2D, sala: Node2D, tile: int) -> void:
	var tex := _radial(Color(1, 1, 1, 0.55), 128)
	for k in 26:
		var h := hash(Vector2i(k, 903))
		var x: float = (1 + posmod(h, (sala.colunas - 2) * 100) / 100.0) * tile
		var y: float = (2 + posmod(h / 7919, (sala.linhas - 3) * 100) / 100.0) * tile
		var terra: bool = posmod(h / 31, 3) != 0
		var sp := Sprite2D.new()
		sp.texture = tex
		sp.position = Vector2(x, y)
		sp.scale = Vector2(1.6 + posmod(h / 17, 20) / 10.0, 1.1 + posmod(h / 13, 12) / 10.0)
		sp.modulate = Color(0.34, 0.25, 0.14, 0.7) if terra else Color(0.62, 0.58, 0.24, 0.5)
		raiz.add_child(sp)

static var _lajes_tex: Texture2D

## Textura de lajes de pedra (128 px, repete sem emenda): células irregulares em cinza-azulado, junta escura, rachaduras e musgo.
static func _textura_lajes() -> Texture2D:
	if _lajes_tex != null:
		return _lajes_tex
	var n := 128
	var pts: Array[Vector2] = []
	var tons: Array[Color] = []
	for gy in 4:
		for gx in 4:
			var h := hash(Vector2i(gx, gy + 40))
			pts.append(Vector2((gx + 0.2 + 0.6 * posmod(h, 100) / 100.0) * n / 4.0, (gy + 0.2 + 0.6 * posmod(h / 101, 100) / 100.0) * n / 4.0))
			var t := 0.78 + 0.5 * float(posmod(h / 7, 100)) / 100.0
			var quente := 0.04 * float(posmod(h / 3, 100)) / 100.0
			tons.append(Color(0.43 * t + quente, 0.46 * t, 0.52 * t))
	var img := Image.create(n, n, false, Image.FORMAT_RGB8)
	for y in n:
		for x in n:
			var d1 := 1e9
			var d2 := 1e9
			var idx := 0
			for k in pts.size():
				var dx := absf(x - pts[k].x)
				var dy := absf(y - pts[k].y)
				dx = minf(dx, n - dx)
				dy = minf(dy, n - dy)
				var d := sqrt(dx * dx + dy * dy)
				if d < d1:
					d2 = d1
					d1 = d
					idx = k
				elif d < d2:
					d2 = d
			var borda := d2 - d1
			var gr := 0.93 + 0.14 * float(posmod(hash(Vector2i(x, y)), 100)) / 100.0
			var c: Color = tons[idx] * gr
			if borda < 2.4:
				c = Color(0.1, 0.1, 0.11)
			elif borda < 5.5:
				c = c * (0.62 + 0.38 * (borda - 2.4) / 3.1)
			elif posmod(hash(Vector2i(x / 3, y / 3 + idx)), 53) == 0:
				c = c * 0.7  # rachadura
			if borda < 6.0 and posmod(hash(Vector2i(x, y + 7)), 9) == 0:
				c = c.lerp(Color(0.25, 0.36, 0.17), 0.7)  # musgo na junta
			c.a = 1.0
			img.set_pixel(x, y, c)
	_lajes_tex = ImageTexture.create_from_image(img)
	return _lajes_tex

static func _radial(cor: Color, lado: int, borda := Color(0, 0, 0, 0)) -> GradientTexture2D:
	var g := Gradient.new()
	g.set_color(0, cor)
	g.set_color(1, borda)
	var t := GradientTexture2D.new()
	t.gradient = g
	t.width = lado
	t.height = lado
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	return t

static func _mancha(sala: Node2D, pos: Vector2, tam: Vector2, tex: Texture2D, z: int, aditivo := false) -> Sprite2D:
	var sp := Sprite2D.new()
	sp.texture = tex
	sp.position = pos
	sp.scale = tam / float(tex.get_width())
	sp.z_index = z
	if aditivo:
		var m := CanvasItemMaterial.new()
		m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		sp.material = m
	sala.add_child(sp)
	return sp

## Vinheta, halo das tochas, névoa baixa na água e musgo na base do muro.
static var _tex_cache := {}

static func _radial_cache(chave: String, cor: Color, lado: int, borda := Color(0, 0, 0, 0)) -> GradientTexture2D:
	if not _tex_cache.has(chave):
		_tex_cache[chave] = _radial(cor, lado, borda)
	return _tex_cache[chave]

## Vinheta, halo oscilante das tochas e velas, névoa em deriva, folhas na água e musgo na base do muro.
static func _luz(sala: Node2D, riachos: Array, grama: bool, tile: int) -> void:
	var larg: float = sala.colunas * tile
	var alt: float = sala.linhas * tile
	var amb := Ambiente.new()
	sala.add_child(amb)
	_mancha(sala, Vector2(larg, alt) * 0.5, Vector2(larg * 1.5, alt * 1.5), _radial_cache("vinheta", Color(0, 0, 0, 0), 256, Color(0.02, 0.02, 0.05, 0.7)), 20)
	for b in sala.braseiros:
		var h := _mancha(sala, b + Vector2(0, -10), Vector2(400, 400), _radial_cache("tocha_grama" if grama else "tocha", Color(1.0, 0.55, 0.18, 0.62 if grama else 0.4), 256), 3, true)
		amb.add_halo(h)
	for p in sala.props:
		if String(p["id"]).contains("candles"):
			var h := _mancha(sala, p["pos"] + Vector2(0, 10), Vector2(230, 230), _radial_cache("vela", Color(1.0, 0.72, 0.3, 0.34), 256), 3, true)
			amb.add_halo(h)
	var folha := _arte_prop("leaves_scattered")
	var n_riacho := 0
	for r in riachos:
		var linha := spline(r["pts"], 90.0)
		for k in linha.size():
			var m := _mancha(sala, linha[k] + Vector2(0, -6), Vector2(380, 140), _radial_cache("nevoa", Color(0.78, 0.84, 0.84, 0.025), 256), 6)
			amb.add_nevoa(m, 28.0)
		n_riacho += 1
	if grama:
		var musgo := Polygon2D.new()
		var y0: float = 2 * tile
		musgo.polygon = PackedVector2Array([Vector2(tile, y0), Vector2(larg - tile, y0), Vector2(larg - tile, y0 + 34), Vector2(tile, y0 + 34)])
		musgo.vertex_colors = PackedColorArray([Color(0.2, 0.28, 0.12, 0.75), Color(0.2, 0.28, 0.12, 0.75), Color(0.2, 0.28, 0.12, 0.0), Color(0.2, 0.28, 0.12, 0.0)])
		sala.add_child(musgo)

## Poucas folhas laranja caindo devagar pela sala.
static func _folhas_caindo(sala: Node2D, tex: Texture2D, larg: float, alt: float) -> void:
	var p := CPUParticles2D.new()
	p.texture = tex
	p.amount = 7
	p.lifetime = 11.0
	p.preprocess = 11.0
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2(larg * 0.45, 20.0)
	p.position = Vector2(larg * 0.5, 140.0)
	p.direction = Vector2(0.25, 1.0)
	p.spread = 15.0
	p.gravity = Vector2(4.0, 6.0)
	p.initial_velocity_min = 14.0
	p.initial_velocity_max = 24.0
	p.angle_min = 0.0
	p.angle_max = 360.0
	p.angular_velocity_min = -60.0
	p.angular_velocity_max = 60.0
	p.scale_amount_min = 0.05
	p.scale_amount_max = 0.08
	p.color = Color(1.0, 0.8, 0.6, 0.9)
	var g := Gradient.new()
	g.set_color(0, Color(1, 1, 1, 0.0))
	g.add_point(0.15, Color(1, 1, 1, 1.0))
	g.add_point(0.85, Color(1, 1, 1, 1.0))
	g.set_color(g.get_point_count() - 1, Color(1, 1, 1, 0.0))
	p.color_ramp = g
	p.z_index = 11
	sala.add_child(p)

static func _vagalumes(sala: Node2D, tile: int) -> void:
	# poucos, só nas faixas laterais da sala, longe do centro de combate
	var g := Gradient.new()
	g.set_color(0, Color(0.85, 1.0, 0.45, 0.0))
	g.add_point(0.5, Color(0.85, 1.0, 0.45, 0.8))
	g.set_color(g.get_point_count() - 1, Color(0.85, 1.0, 0.45, 0.0))
	for lado in [0.13, 0.87]:
		var p := CPUParticles2D.new()
		p.amount = 3
		p.lifetime = 6.0
		p.preprocess = 6.0
		p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
		p.emission_rect_extents = Vector2(sala.colunas * tile * 0.1, sala.linhas * tile * 0.38)
		p.position = Vector2(sala.colunas * tile * lado, sala.linhas * tile * 0.5)
		p.gravity = Vector2.ZERO
		p.initial_velocity_min = 4.0
		p.initial_velocity_max = 12.0
		p.direction = Vector2(0, -1)
		p.spread = 180.0
		p.scale_amount_min = 2.0
		p.scale_amount_max = 3.0
		p.color_ramp = g
		p.z_index = 10
		sala.add_child(p)

## Capim, cardos, folhas e pedrinhas soltos na margem do caminho, para a borda não parecer um corte reto.
static func _tufos_na_borda(sala: Node2D, contorno: PackedVector2Array, semente: int) -> void:
	var ids := ["grass_dry_tall", "thistles_dry", "leaves_scattered", "rock_rubble", "grass_dry_patch"]
	var escalas := [0.2, 0.2, 0.22, 0.2, 0.2]
	var i := 0
	while i < contorno.size():
		var h := hash(Vector2i(i, semente + 77))
		var k := posmod(h, ids.size())
		var arte := _arte_prop(ids[k])
		if arte != null:
			var sp := Sprite2D.new()
			sp.texture = arte[0]
			sp.centered = false
			sp.offset = -Vector2(arte[1], arte[2])
			sp.scale = Vector2.ONE * escalas[k]
			sp.position = contorno[i] + Vector2(posmod(h / 7, 9) - 4, posmod(h / 63, 7) - 3)
			sp.z_index = 1
			sala.add_child(sp)
		i += 9 + posmod(h / 3, 8)

static var _cache_props := {}

static func _arte_prop(id: String) -> Array:
	if not _cache_props.has(id):
		var achado := []
		for r in Csv.rows("res://data2d/props_manifest.csv"):
			if r["id"] == id:
				var tex: Texture2D = load(r["arquivo"]) if ResourceLoader.exists(r["arquivo"]) else null
				if tex == null and FileAccess.file_exists(r["arquivo"]):
					tex = ImageTexture.create_from_image(Image.load_from_file(ProjectSettings.globalize_path(r["arquivo"])))
				if tex != null:
					achado = [tex, float(r["pivo_x"]), float(r["pivo_y"])]
		_cache_props[id] = achado
	return _cache_props[id]
