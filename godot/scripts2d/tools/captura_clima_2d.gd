extends SceneTree
## Grava quadros de uma sala sem inimigos para ver o clima vivo (vento, folhas, fogo, fumaça, nuvens).
## Precisa de janela (xvfb no Linux):
##   godot --path godot --script res://scripts2d/tools/captura_clima_2d.gd -- pasta_saida res://data2d/rooms/sala_1.txt 90 3
## Argumentos: pasta, sala, número de quadros, intervalo em quadros de física entre capturas.
const RunScene = preload("res://scenes2d/Run2D.tscn")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var pasta: String = args[0] if args.size() > 0 else "captura_clima"
	var sala: String = args[1] if args.size() > 1 else "res://data2d/rooms/sala_1.txt"
	var quadros: int = int(args[2]) if args.size() > 2 else 90
	var passo: int = int(args[3]) if args.size() > 3 else 3
	DirAccess.make_dir_recursive_absolute(pasta)
	var run = RunScene.instantiate()
	root.add_child(run)
	await physics_frame
	run.menus.fechar()
	root.get_tree().paused = false
	run._carregar_sala(0, {"room": sala, "enemies": "", "tipo": "combate"})
	run.player.god_mode = true
	for i in 240:  # deixa folhas e fumaça se espalharem antes de gravar
		await physics_frame
	for q in quadros:
		for i in passo:
			await physics_frame
		await RenderingServer.frame_post_draw
		root.get_viewport().get_texture().get_image().save_png("%s/q%03d.png" % [pasta, q])
	quit()
