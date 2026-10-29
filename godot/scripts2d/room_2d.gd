extends Node2D
## Sala da Cripta montada de um texto (data2d/rooms/*.txt) com TileMapLayer.
## Legenda: # parede, . piso, B braseiro, O pilar, D porta, P início do jogador, E ponto de inimigo.

signal porta_usada

const Csv = preload("res://scripts2d/csv2d.gd")
const Placeholders = preload("res://scripts2d/placeholders.gd")
const ATLAS := "res://art2d/tiles/cripta_tiles.png"
const T_PISO := 0
const T_PORTA_FECHADA := 7
const T_PAREDE_FACE := 8
const T_PAREDE_TOPO := 9
const T_PILAR := 12
const T_PORTA_ABERTA := 13
const T_BRASEIRO := 15

var tile := 64
var colunas := 0
var linhas := 0
var spawn_jogador := Vector2.ZERO
var spawns_inimigos: Array[Vector2] = []
var celulas_porta: Array[Vector2i] = []
var _layer: TileMapLayer
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
	while not f.eof_reached():
		var l := f.get_line().strip_edges(false, true)
		if l != "":
			_grade.append(l)
	linhas = _grade.size()
	colunas = _grade[0].length()
	for l in _grade:
		if l.length() != colunas:
			push_error("Sala com linhas de tamanhos diferentes: " + caminho)
			return false
	_montar()
	return true

func _centro(x: int, y: int) -> Vector2:
	return Vector2((x + 0.5) * tile, (y + 0.5) * tile)

func _eh_parede(x: int, y: int) -> bool:
	if x < 0 or y < 0 or x >= colunas or y >= linhas:
		return true
	return _grade[y][x] in ["#", "D"]

func _montar() -> void:
	_layer = TileMapLayer.new()
	_layer.tile_set = _tileset()
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
				"D":
					idx = T_PORTA_FECHADA
					celulas_porta.append(Vector2i(x, y))
				"O":
					idx = T_PILAR
				"B":
					idx = T_BRASEIRO
				"P":
					spawn_jogador = _centro(x, y)
				"E":
					spawns_inimigos.append(_centro(x, y))
			_pintar(Vector2i(x, y), idx)
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

func _pintar(c: Vector2i, idx: int) -> void:
	var cols: int = _layer.tile_set.get_source(0).texture.get_width() / tile
	_layer.set_cell(c, 0, Vector2i(idx % cols, idx / cols))

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
	return ts

func abrir_porta() -> void:
	for c in celulas_porta:
		_pintar(c, T_PORTA_ABERTA)
	_porta_corpo.queue_free()
	_porta_area.set_deferred("monitoring", true)
