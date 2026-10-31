extends SceneTree
## Captura de combate (precisa de janela): godot --path godot --script res://scripts2d/tools/captura_combate_2d.gd -- prefixo sala [quadros]
## Joga a sala com a mira automática e salva `prefixo_1.png`.. em quadros espaçados; `sala` 4 = chefe.
const RunScene = preload("res://scenes2d/Run2D.tscn")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var pref: String = args[0] if args.size() > 0 else "combate"
	var sala: int = int(args[1]) if args.size() > 1 else 0
	var quadros: PackedInt32Array = PackedInt32Array([110, 150, 190])
	if args.size() > 2:
		quadros = PackedInt32Array()
		for s in args[2].split(","):
			quadros.append(int(s))
	var run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	if sala > 0:
		run.indice = sala
		run._carregar_sala(sala)
	run.player.god_mode = true
	print('estado=', run.estado, ' paused=', paused, ' hurtable=', get_nodes_in_group('hurtable').size())
	var f := 0
	for n in quadros.size():
		while f < quadros[n]:
			f += 1
			var alvo: Node2D = null
			var melhor := 1.0e9
			for e in get_nodes_in_group("hurtable"):
				var d: float = e.global_position.distance_to(run.player.global_position)
				if d < melhor:
					melhor = d
					alvo = e
			if alvo != null:
				run.player.auto_aim = (alvo.global_position - run.player.global_position).normalized()
			await physics_frame
		await RenderingServer.frame_post_draw
		root.get_viewport().get_texture().get_image().save_png("%s_%d.png" % [pref, n + 1])
	quit()
