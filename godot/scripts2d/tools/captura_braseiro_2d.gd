extends SceneTree
## Captura de perto cada braseiro da fase aberta, pela Main2D (pixel art; precisa de janela, use xvfb):
##   godot --path godot --resolution 1600x900 --script res://scripts2d/tools/captura_braseiro_2d.gd -- prefixo [quantos=2]
const MainScene = preload("res://scenes2d/Main2D.tscn")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var prefixo: String = args[0] if args.size() > 0 else "braseiro"
	var quantos: int = int(args[1]) if args.size() > 1 else 2
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	var run = main.run
	run.menus.fechar()
	run.estado = run.Estado.LUTA
	paused = false
	run.player.god_mode = true
	var bs: Array = run.room.braseiros
	for i in mini(quantos, bs.size()):
		run.player.global_position = bs[i] + Vector2(70, 40)
		for k in 50:
			await physics_frame
		await RenderingServer.frame_post_draw
		root.get_viewport().get_texture().get_image().save_png("%s_%d.png" % [prefixo, i])
	quit()
