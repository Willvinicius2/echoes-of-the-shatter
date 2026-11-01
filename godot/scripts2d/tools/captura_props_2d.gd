extends SceneTree
## Captura só da sala (piso, terreno e props) com bonecos parados do Arqueiro, sem precisar do core:
##   godot --path godot --script res://scripts2d/tools/captura_props_2d.gd -- saida.png [sala.txt] [zoom cx cy]
## Usada para conferir ancoragem dos props e a ponte (precisa de janela; xvfb-run na nuvem).
const RoomScript = preload("res://scripts2d/room_2d.gd")
const Csv = preload("res://scripts2d/csv2d.gd")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var saida: String = args[0] if args.size() > 0 else "captura_props.png"
	var sala: String = args[1] if args.size() > 1 else "res://data2d/rooms/sala_1.txt"
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
	# bonecos parados: na ponte, atrás de uma árvore, ao lado de uma tumba e no gramado
	var pontos := [Vector2(12.0, 6.3), Vector2(2.1, 2.9), Vector2(3.7, 8.6), Vector2(16.0, 9.0), Vector2(12.2, 8.6)]
	var extra: String = OS.get_environment("BONECOS")  # "x,y;x,y" em células, para testar na frente e atrás dos props
	if extra != "":
		pontos.clear()
		for par in extra.split(";"):
			var xy := par.split(",")
			pontos.append(Vector2(float(xy[0]), float(xy[1])))
	var primeiro := true
	for p in pontos:
		var spr := _boneco()
		if spr != null:
			spr.position = Vector2(p) * tile
			if primeiro:
				spr.add_to_group("arqueiro")  # o primeiro boneco conta como o jogador para os arbustos semitransparentes
				primeiro = false
			atores.add_child(spr)
	var cam := Camera2D.new()
	mundo.add_child(cam)
	await process_frame
	var vp := Vector2(root.get_window().size)
	var tam: Vector2 = room.tamanho_px()
	if args.size() > 4:
		var z := float(args[2])
		cam.zoom = Vector2(z, z)
		cam.position = Vector2(float(args[3]), float(args[4])) * tile
	else:
		cam.position = tam / 2.0
		var z := minf(vp.x / tam.x, vp.y / tam.y)
		cam.zoom = Vector2(z, z)
	cam.enabled = true
	cam.make_current()
	for i in 45:
		await physics_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(saida)
	quit()

func _boneco() -> Sprite2D:
	for r in Csv.rows("res://data2d/sprites_manifest.csv"):
		if r["id"] == "arqueiro" and r["anim"] == "idle":
			var tex: Texture2D = load(r["arquivo"])
			if tex == null:
				return null
			var q := int(r["quadro"])
			var spr := Sprite2D.new()
			spr.texture = tex
			spr.region_enabled = true
			spr.region_rect = Rect2(0, 0, q, q)
			spr.offset = Vector2(q * 0.5 - float(r["pivo_x"]), q * 0.5 - float(r["pivo_y"]))
			return spr
	return null
