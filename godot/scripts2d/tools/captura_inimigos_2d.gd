extends SceneTree
## Captura do arqueiro com os inimigos da Cripta ao lado, para comparar a densidade de pixel (precisa de janela):
##   godot --path godot --resolution 1600x900 --script res://scripts2d/tools/captura_inimigos_2d.gd -- prefixo
const MainScene = preload("res://scenes2d/Main2D.tscn")
const Enemy = preload("res://scripts2d/enemy_2d.gd")
const IDS := ["skeleton_soldier", "hollow_sentinel", "crypt_bat", "ghost_archer", "chain_wraith", "wandering_ghost"]

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var prefixo: String = args[0] if args.size() > 0 else "captura_inimigos"
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	var run = main.run
	run.menus.fechar()
	run.estado = run.Estado.LUTA
	paused = false
	run.player.god_mode = true
	run.player.global_position = run.room._centro(124, 52)
	for i in IDS.size():
		var e = Enemy.new()
		run.atores.add_child(e)
		e.setup(IDS[i], run.player, run.player.global_position + Vector2(-260 + i * 110, 110))
		e.set_physics_process(false)
	for i in 40:
		await physics_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png("%s_inimigos.png" % prefixo)
	quit()
