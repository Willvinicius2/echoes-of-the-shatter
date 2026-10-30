extends Node2D
## Sala da Cripta montada de um texto (data2d/rooms/*.txt) com TileMapLayer.
## Legenda: # parede, . piso, r piso com runas, q piso escuro, B braseiro, O pilar, D porta,
## P início do jogador, E ponto de inimigo, p laje de caminho (só com `@piso grama`).
## `@caminho largura x,y x,y ...` e `@riacho largura x,y ...` (células; curva suave) desenham caminho de pedra
## e riacho; o riacho bloqueia jogador e inimigos (camada 8) menos onde o caminho o cruza.
## A linha `@piso grama` antes de `@props` troca o piso padrão por gramado (atlas cripta_grama.png).
## Depois da grade, a linha `@props` abre a lista de props: `id coluna linha [flip]` (coluna e linha
## podem ser fracionárias; ids em data2d/props_2d.csv, arte em props_manifest.csv).

signal porta_usada

const Csv = preload("res://scripts2d/csv2d.gd")
const Placeholders = preload("res://scripts2d/placeholders.gd")
const Terreno = preload("res://scripts2d/terreno_2d.gd")
const ATLAS := "res://art2d/tiles/cripta_tiles.png"
const ATLAS_GRAMA := "res://art2d/tiles/cripta_grama.png"
const T_PISO := 0
const T_PISO_ESCURO := 6
const T_PORTA_FECHADA := 7
const T_PAREDE_FACE := 8
const T_PAREDE_TOPO := 9
const T_PILAR := 12
const T_PORTA_ABERTA := 13
const T_BRASEIRO := 15
const T_RUNAS := [4, 41, 42, 43, 44, 45, 46, 47]

var tile := 64
var colunas := 0
var linhas := 0
var spawn_jogador := Vector2.ZERO
var spawns_inimigos: Array[Vector2] = []
var celulas_porta: Array[Vector2i] = []
var props: Array = []  # {id, pos (pé do prop em px), flip}
var _props_def := {}
var _props_arte := {}
var _layer: TileMapLayer
var _piso: TileMapLayer
var piso_grama := false
var braseiros: Array[Vector2] = []
var caminhos: Array = []  # {larg (células), pts (px)}
var riachos: Array = []
var _porta_area: Area2D
var _porta_corpo: StaticBody2D
var _grade: Array = []

func tamanho_px() -> Vector2:
	return Vector2(colunas * tile, linhas * tile)

func carregar(caminho: String) -> bool:
	tile = int(Csv.kv("res://data2d/run_settings.csv")["tile"])
	var f := FileAccess.open(caminho, FileAccess.READ)
	if f == null:
		push_error("Sala ausente: " + caminho)
		return false
	var em_props := false
	while not f.eof_reached():
		var l := f.get_line().strip_edges(false, true)
		if l == "":
			continue
		if l == "@props":
			em_props = true
		elif l == "@piso grama":
			piso_grama = true
		elif l.begins_with("@caminho ") or l.begins_with("@riacho "):
			var q := l.split(" ", false)
			var pts: Array = []
			for ponto in q.slice(2):
				var xy := ponto.split(",")
				pts.append(Vector2((float(xy[0]) + 0.5) * tile, (float(xy[1]) + 0.5) * tile))
			(caminhos if q[0] == "@caminho" else riachos).append({"larg": float(q[1]), "pts": pts})
		elif em_props:
			var p := l.split(" ", false)
			props.append({"id": p[0], "pos": Vector2((float(p[1]) + 0.5) * tile, (float(p[2]) + 0.5) * tile), "flip": p.size() > 3 and p[3] == "flip"})
		else:
			_grade.append(l)
	linhas = _grade.size()
	colunas = _grade[0].length()
	for l in _grade:
		if l.length() != colunas:
			push_error("Sala com linhas de tamanhos diferentes: " + caminho)
			return false
	for r in Csv.rows("res://data2d/props_2d.csv"):
		_props_def[r["id"]] = r
	for r in Csv.rows("res://data2d/props_manifest.csv"):
		_props_arte[r["id"]] = r
	_montar()
	return true

func _centro(x: int, y: int) -> Vector2:
	return Vector2((x + 0.5) * tile, (y + 0.5) * tile)

func _eh_parede(x: int, y: int) -> bool:
	if x < 0 or y < 0 or x >= colunas or y >= linhas:
		return true
	return _grade[y][x] in ["#", "D"]

func _montar() -> void:
	var ts := _tileset()
	_piso = TileMapLayer.new()  # piso sob os objetos, para o fundo transparente de braseiro e pilar não ficar preto
	_piso.tile_set = ts
	add_child(_piso)
	_layer = TileMapLayer.new()
	_layer.tile_set = ts
	add_child(_layer)
	var corpo := StaticBody2D.new()
	corpo.collision_layer = 1
	corpo.collision_mask = 0
	add_child(corpo)
	for y in linhas:
		var inicio := -1
		for x in colunas + 1:
			var bloqueia: bool = x < colunas and (_grade[y][x] in ["#", "O"])
			if bloqueia and inicio < 0:
				inicio = x
			elif not bloqueia and inicio >= 0:
				var cs := CollisionShape2D.new()
				var r := RectangleShape2D.new()
				r.size = Vector2((x - inicio) * tile, tile)
				cs.shape = r
				cs.position = Vector2((inicio + (x - inicio) / 2.0) * tile, (y + 0.5) * tile)
				corpo.add_child(cs)
				inicio = -1
		for x in colunas:
			var c: String = _grade[y][x]
			var idx := T_PISO + posmod(hash(Vector2i(x, y)), 4)
			match c:
				"#":
					idx = T_PAREDE_TOPO if _eh_parede(x, y + 1) else T_PAREDE_FACE
					if idx == T_PAREDE_FACE:
						_pintar(Vector2i(x, y), T_PAREDE_TOPO, _piso)  # sob o muro, no lugar do preto
				"D":
					idx = T_PORTA_FECHADA
					celulas_porta.append(Vector2i(x, y))
				"r":
					idx = T_RUNAS[posmod(hash(Vector2i(x * 7, y * 13)), T_RUNAS.size())]
				"q":
					idx = T_PISO_ESCURO
				"O":
					idx = T_PILAR
				"B":
					idx = T_BRASEIRO
					braseiros.append(_centro(x, y))
				"P":
					spawn_jogador = _centro(x, y)
				"E":
					spawns_inimigos.append(_centro(x, y))
			if piso_grama and c != "#" and c != "D":
				_pintar_grama(Vector2i(x, y), posmod(hash(Vector2i(x, y)), 4), 1 if c == "p" else 0)
			elif c != "#" and c != "D":
				_pintar(Vector2i(x, y), T_PISO + posmod(hash(Vector2i(x, y)), 4), _piso)
			if c != "." and c != "p" and not (c in ["P", "E"]):
				_pintar(Vector2i(x, y), idx)
	for p in props:
		var d: Dictionary = _props_def.get(p["id"], {})
		if d.is_empty() or float(d["solido_l"]) <= 0.0:
			continue
		var cp := CollisionShape2D.new()
		var rp := RectangleShape2D.new()
		rp.size = Vector2(float(d["solido_l"]), float(d["solido_a"]))
		cp.shape = rp
		cp.position = p["pos"] + Vector2(0, tile * 0.5 - float(d["solido_a"]) * 0.5)
		corpo.add_child(cp)
	Terreno.montar(self, caminhos, riachos, piso_grama, tile)
	_porta_corpo = StaticBody2D.new()
	_porta_corpo.collision_layer = 1
	_porta_corpo.collision_mask = 0
	add_child(_porta_corpo)
	for c in celulas_porta:
		var cd := CollisionShape2D.new()
		var rd := RectangleShape2D.new()
		rd.size = Vector2(tile, tile)
		cd.shape = rd
		cd.position = _centro(c.x, c.y)
		_porta_corpo.add_child(cd)
	_porta_area = Area2D.new()
	_porta_area.collision_layer = 0
	_porta_area.collision_mask = 2
	_porta_area.monitoring = false
	add_child(_porta_area)
	for c in celulas_porta:
		var cs := CollisionShape2D.new()
		var r := RectangleShape2D.new()
		r.size = Vector2(tile, tile)
		cs.shape = r
		cs.position = _centro(c.x, c.y) + Vector2(0, tile * 0.5)
		_porta_area.add_child(cs)
	_porta_area.body_entered.connect(func(_c): porta_usada.emit())

func _pintar(c: Vector2i, idx: int, camada: TileMapLayer = null) -> void:
	var l := camada if camada != null else _layer
	var cols: int = l.tile_set.get_source(0).texture.get_width() / tile
	l.set_cell(c, 0, Vector2i(idx % cols, idx / cols))

func _pintar_grama(c: Vector2i, variante: int, linha: int) -> void:
	_piso.set_cell(c, 1, Vector2i(variante, linha))

func _tileset() -> TileSet:
	var tex: Texture2D
	if ResourceLoader.exists(ATLAS):
		tex = load(ATLAS)
	elif FileAccess.file_exists(ATLAS):
		tex = ImageTexture.create_from_image(Image.load_from_file(ProjectSettings.globalize_path(ATLAS)))
	else:
		tex = Placeholders.tiles(tile, 8, 2)
	var ts := TileSet.new()
	ts.tile_size = Vector2i(tile, tile)
	var src := TileSetAtlasSource.new()
	src.texture = tex
	src.texture_region_size = Vector2i(tile, tile)
	for y in tex.get_height() / tile:
		for x in tex.get_width() / tile:
			src.create_tile(Vector2i(x, y))
	ts.add_source(src, 0)
	var tg := _carregar_textura(ATLAS_GRAMA)
	if tg != null:
		var sg := TileSetAtlasSource.new()
		sg.texture = tg
		sg.texture_region_size = Vector2i(tile, tile)
		for y in tg.get_height() / tile:
			for x in tg.get_width() / tile:
				sg.create_tile(Vector2i(x, y))
		ts.add_source(sg, 1)
	return ts

func abrir_porta() -> void:
	for c in celulas_porta:
		_pintar(c, T_PORTA_ABERTA)
	_porta_corpo.queue_free()
	_porta_area.set_deferred("monitoring", true)

## Cria os sprites dos props dentro de `alvo` (Node2D com y_sort_enabled, o mesmo dos atores).
## O pé do prop fica na base da célula, então jogador e inimigos passam na frente ou atrás pela ordem em Y.
func colocar_props(alvo: Node2D) -> void:
	for p in props:
		var arte: Dictionary = _props_arte.get(p["id"], {})
		var d: Dictionary = _props_def.get(p["id"], {})
		if arte.is_empty() or d.is_empty():
			push_warning("Prop sem arte ou definição: " + p["id"])
			continue
		var tex: Texture2D = _carregar_textura(arte["arquivo"])
		if tex == null:
			continue
		var spr := Sprite2D.new()
		spr.texture = tex
		spr.centered = false
		spr.offset = -Vector2(float(arte["pivo_x"]), float(arte["pivo_y"]))
		spr.scale = Vector2.ONE * float(d["escala"])
		spr.flip_h = p["flip"]
		if p["id"] in ["tree_dry_orange", "bush_dry_red"]:
			spr.modulate = Color(0.86, 0.82, 0.82)  # laranja e vermelho um pouco mais calmos no piso escuro
		if spr.flip_h:
			spr.offset.x = -(tex.get_width() - float(arte["pivo_x"]))
		var no := Node2D.new()
		no.position = p["pos"] + Vector2(0, tile * 0.5)
		no.add_child(spr)
		var sombra := Node2D.new()
		sombra.z_index = -1
		var arvore: bool = String(p["id"]).begins_with("tree_")
		sombra.draw.connect(func():
			sombra.draw_set_transform(Vector2(16, 0) if arvore else Vector2.ZERO, 0.0, Vector2(1.0, 0.35))
			sombra.draw_circle(Vector2.ZERO, tex.get_width() * float(d["escala"]) * (0.5 if arvore else 0.35), Color(0, 0, 0, 0.5 if arvore else 0.35)))
		no.add_child(sombra)
		sombra.queue_redraw()
		alvo.add_child(no)

func _carregar_textura(caminho: String) -> Texture2D:
	if ResourceLoader.exists(caminho):
		return load(caminho)
	if FileAccess.file_exists(caminho):
		return ImageTexture.create_from_image(Image.load_from_file(ProjectSettings.globalize_path(caminho)))
	return null
