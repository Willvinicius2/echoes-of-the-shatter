extends SceneTree
## Captura de tela do cliente 2D (precisa de janela, não roda em --headless):
##   godot --path godot --script res://scripts2d/tools/captura_2d.gd -- saida.png [sala]
const RunScene = preload("res://scenes2d/Run2D.tscn")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var saida: String = args[0] if args.size() > 0 else "captura_2d.png"
	var sala: int = int(args[1]) if args.size() > 1 else 0
	var run = RunScene.instantiate()
	root.add_child(run)
	await physics_frame
	if sala > 0:
		run.indice = sala
		run._carregar_sala(sala)
	run.player.god_mode = true
	run.player.auto_aim = Vector2(1, 0.4)
	for i in 90:
		await physics_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(saida)
	quit()
