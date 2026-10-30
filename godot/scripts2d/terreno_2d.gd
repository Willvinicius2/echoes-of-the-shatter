extends RefCounted
## Caminho de pedra, riacho e vaga-lumes de uma sala, desenhados por cima do piso.
## Os pontos vêm do arquivo de sala (`@caminho largura x,y ...` e `@riacho largura x,y ...`, em células).

const Csv = preload("res://scripts2d/csv2d.gd")
const ATLAS := "res://art2d/tiles/cripta_tiles.png"

const AGUA_SHADER := """
shader_type canvas_item;
uniform vec4 fundo : source_color = vec4(0.07, 0.22, 0.27, 1.0);
uniform vec4 brilho : source_color = vec4(0.38, 0.75, 0.78, 1.0);
void fragment() {
	vec2 p = UV * 2.4;
	float a = sin(p.x * 1.3 + TIME * 1.6) * sin(p.y * 1.1 - TIME * 1.2);
	float b = sin((p.x + p.y) * 0.9 + TIME * 0.9);
	float v = smoothstep(0.55, 0.95, a * 0.6 + b * 0.4);
	COLOR = mix(fundo, brilho, v * 0.7);
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
		var h := hash(Vector2i(i, semente))
		poli[i] += Vector2(posmod(h, 2001) - 1000, posmod(h / 2001, 2001) - 1000) / 1000.0 * ruido
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
	var corpo_agua := StaticBody2D.new()
	corpo_agua.collision_layer = 8
	corpo_agua.collision_mask = 0
	sala.add_child(corpo_agua)
	var faixas_caminho: Array = []
	for i in caminhos.size():
		var c: Dictionary = caminhos[i]
		var linha := spline(c["pts"])
		faixas_caminho.append(faixa(linha, c["larg"] * tile, 5.0, 11 + i))
	var pedra := _textura_pedra()
	for i in riachos.size():
		var r: Dictionary = riachos[i]
		var linha := spline(r["pts"])
		var margem := faixa(linha, r["larg"] * tile + 16.0, 4.0, 31 + i)
		var agua := faixa(linha, r["larg"] * tile, 3.0, 41 + i)
		if agua.is_empty():
			continue
		_poligono(raiz, margem, Color(0.12, 0.13, 0.08))
		var pg := _poligono(raiz, agua, Color.WHITE)
		var mat := ShaderMaterial.new()
		mat.shader = Shader.new()
		mat.shader.code = AGUA_SHADER
		pg.material = mat
		pg.uv = agua
		pg.texture = pedra  # a UV só precisa de uma textura qualquer; o shader ignora a cor
		# Colisão da água: livre onde o caminho cruza (vau).
		var blocos: Array = [agua]
		for fc in faixas_caminho:
			var novos: Array = []
			for b in blocos:
				novos.append_array(Geometry2D.clip_polygons(b, fc))
			blocos = novos
		for b in blocos:
			if Geometry2D.is_polygon_clockwise(b):
				continue  # buracos
			var cp := CollisionPolygon2D.new()
			cp.polygon = b
			corpo_agua.add_child(cp)
	for i in caminhos.size():
		var fc: PackedVector2Array = faixas_caminho[i]
		if fc.is_empty():
			continue
		var borda := faixa(spline(caminhos[i]["pts"]), caminhos[i]["larg"] * tile + 14.0, 5.0, 21 + i)
		_poligono(raiz, borda, Color(0.13, 0.15, 0.09, 0.85))
		var pg := _poligono(raiz, fc, Color(0.92, 0.88, 0.84))
		pg.texture = pedra
		pg.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
		pg.uv = fc
		# Ranhuras entre lajes: linhas escuras atravessando o caminho, em passo irregular.
		var linha := spline(caminhos[i]["pts"], 6.0)
		var j := 3
		while j < linha.size() - 3:
			var dir := (linha[j + 1] - linha[j - 1]).normalized()
			var n: Vector2 = Vector2(-dir.y, dir.x) * float(caminhos[i]["larg"]) * tile * 0.5
			var l := Line2D.new()
			l.points = PackedVector2Array([linha[j] - n * 0.95, linha[j] + n * 0.95])
			l.width = 2.5
			l.default_color = Color(0.1, 0.1, 0.09, 0.55)
			raiz.add_child(l)
			j += 7 + posmod(hash(Vector2i(j, i)), 5)
		_tufos_na_borda(sala, fc, i)
	_luz(sala, riachos, grama, tile)
	if grama:
		_vagalumes(sala, tile)

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

static func _mancha(sala: Node2D, pos: Vector2, tam: Vector2, tex: Texture2D, z: int, aditivo := false) -> void:
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

## Vinheta, halo das tochas, névoa baixa na água e musgo na base do muro.
static func _luz(sala: Node2D, riachos: Array, grama: bool, tile: int) -> void:
	var larg: float = sala.colunas * tile
	var alt: float = sala.linhas * tile
	_mancha(sala, Vector2(larg, alt) * 0.5, Vector2(larg * 1.5, alt * 1.5), _radial(Color(0, 0, 0, 0), 256, Color(0.02, 0.02, 0.05, 0.62)), 20)
	for b in sala.braseiros:
		_mancha(sala, b + Vector2(0, -10), Vector2(300, 300), _radial(Color(1.0, 0.55, 0.18, 0.3), 256), 3, true)
	for r in riachos:
		var linha := spline(r["pts"], 90.0)
		for k in linha.size():
			_mancha(sala, linha[k] + Vector2(0, -6), Vector2(380, 140), _radial(Color(0.78, 0.84, 0.84, 0.07), 256), 6)
	if grama:
		var musgo := Polygon2D.new()
		var y0: float = 2 * tile
		musgo.polygon = PackedVector2Array([Vector2(tile, y0), Vector2(larg - tile, y0), Vector2(larg - tile, y0 + 34), Vector2(tile, y0 + 34)])
		musgo.vertex_colors = PackedColorArray([Color(0.2, 0.28, 0.12, 0.75), Color(0.2, 0.28, 0.12, 0.75), Color(0.2, 0.28, 0.12, 0.0), Color(0.2, 0.28, 0.12, 0.0)])
		sala.add_child(musgo)

static func _textura_pedra() -> Texture2D:
	var img: Image
	if ResourceLoader.exists(ATLAS):
		img = (load(ATLAS) as Texture2D).get_image()
	else:
		img = Image.load_from_file(ProjectSettings.globalize_path(ATLAS))
	return ImageTexture.create_from_image(img.get_region(Rect2i(64, 0, 64, 64)))

static func _vagalumes(sala: Node2D, tile: int) -> void:
	var p := CPUParticles2D.new()
	p.amount = 26
	p.lifetime = 5.0
	p.preprocess = 5.0
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2(sala.colunas * tile * 0.5, sala.linhas * tile * 0.5)
	p.position = Vector2(sala.colunas * tile * 0.5, sala.linhas * tile * 0.5)
	p.gravity = Vector2.ZERO
	p.initial_velocity_min = 4.0
	p.initial_velocity_max = 14.0
	p.direction = Vector2(0, -1)
	p.spread = 180.0
	p.scale_amount_min = 2.0
	p.scale_amount_max = 3.5
	var g := Gradient.new()
	g.set_color(0, Color(0.85, 1.0, 0.45, 0.0))
	g.add_point(0.5, Color(0.85, 1.0, 0.45, 0.9))
	g.set_color(g.get_point_count() - 1, Color(0.85, 1.0, 0.45, 0.0))
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
