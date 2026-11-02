extends SceneTree
## Captura pela cena principal (Main2D), ou seja, com o mundo no SubViewport de pixel art (precisa de janela):
##   godot --path godot --resolution 2560x1440 --script res://scripts2d/tools/captura_pixel_2d.gd -- saida.png [sala] [quadros]
const MainScene = preload("res://scenes2d/Main2D.tscn")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var saida: String = args[0] if args.size() > 0 else "captura_pixel.png"
	var sala: int = int(args[1]) if args.size() > 1 else 0
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	var run = main.run
	if sala > 0:
		run.indice = sala
		run._carregar_sala(sala)
	run.player.god_mode = true
	run.player.auto_aim = Vector2(1, 0.4)
	var espera: int = int(args[2]) if args.size() > 2 else 120
	for i in espera:
		await physics_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(saida)
	quit()
