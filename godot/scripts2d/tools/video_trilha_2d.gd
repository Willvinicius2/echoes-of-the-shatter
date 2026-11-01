extends SceneTree
## Vídeo do Arqueiro andando pela trilha principal da fase, passando ao lado de arbustos, árvores e tumbas,
## sem precisar do core (só a sala, os props e um boneco animado com a folha de corrida):
##   godot --path godot --write-movie saida.avi --fixed-fps 30 --script res://scripts2d/tools/video_trilha_2d.gd -- 40 [sala.txt]
## Rota: pontos do primeiro `@caminho` da sala. O boneco entra no grupo `arqueiro` para os arbustos ficarem
## semitransparentes quando ele passa atrás (room_2d._process).
const RoomScript = preload("res://scripts2d/room_2d.gd")
const Csv = preload("res://scripts2d/csv2d.gd")
const Terreno = preload("res://scripts2d/terreno_2d.gd")
const SpriteLoader = preload("res://scripts2d/sprite_loader.gd")

var _spr: Sprite2D
var _rota: PackedVector2Array
var _i := 1
var _quadro := 0.0
var _vel := 220.0

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var duracao: float = float(args[0]) if args.size() > 0 else 40.0
	var sala: String = args[1] if args.size() > 1 else "res://data2d/rooms/fase_1.txt"
	var mundo := Node2D.new()
	root.add_child(mundo)
	var room = RoomScript.new()
	mundo.add_child(room)
	room.carregar(sala)
	var atores := Node2D.new()
	atores.y_sort_enabled = true
	mundo.add_child(atores)
	room.colocar_props(atores)
	var tile: float = room.tile
	var c: Dictionary = room.caminhos[0]
	_rota = Terreno.spline(c["pts"], 24.0)
	var desvio := OS.get_environment("DESVIO")  # "x,y;x,y" em células: desvios pela beira da trilha
	if desvio != "":
		_rota = PackedVector2Array()
		for par in desvio.split(";"):
			var xy := par.split(",")
			_rota.append(Vector2(float(xy[0]) + 0.5, float(xy[1]) + 0.5) * tile)
	_spr = _boneco()
	_spr.position = _rota[0]
	_spr.add_to_group("arqueiro")
	atores.add_child(_spr)
	var cam := Camera2D.new()
	cam.zoom = Vector2(1.5, 1.5)
	cam.position_smoothing_enabled = true
	cam.position_smoothing_speed = 6.0
	_spr.add_child(cam)
	await process_frame
	cam.enabled = true
	cam.make_current()
	var t := 0.0
	while t < duracao and _i < _rota.size():
		await physics_frame
		var dt := 1.0 / Engine.physics_ticks_per_second
		t += dt
		var alvo := _rota[_i]
		var d := alvo - _spr.position
		if d.length() < 6.0:
			_i += 1
			continue
		var passo := d.normalized() * _vel * dt
		_spr.position += passo
		_quadro += dt * 12.0
		var dir := SpriteLoader.dir_for(d.normalized(), 5)
		_spr.region_rect = Rect2(int(_quadro) % 8 * 128, dir[0] * 128, 128, 128)
		_spr.flip_h = dir[1]
	quit()

func _boneco() -> Sprite2D:
	for r in Csv.rows("res://data2d/sprites_manifest.csv"):
		if r["id"] == "arqueiro" and r["anim"] == "run":
			var spr := Sprite2D.new()
			spr.texture = load(r["arquivo"])
			spr.region_enabled = true
			spr.region_rect = Rect2(0, 0, 128, 128)
			spr.offset = Vector2(0, 64 - float(r["pivo_y"]))
			return spr
	return null
