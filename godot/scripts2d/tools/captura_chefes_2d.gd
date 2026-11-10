extends SceneTree
## Captura do Arqueiro com Arauto de Pedra, Carcereiro do Ossuário e Guardião lado a lado na Pedreira (mundo em pixel art
## do Main2D, câmera de 640x360 escalada para a janela). Precisa de janela:
##   godot --path godot --resolution 1920x1080 --script res://scripts2d/tools/captura_chefes_2d.gd -- prefixo
const MainScene = preload("res://scenes2d/Main2D.tscn")
const Enemy = preload("res://scripts2d/enemy_2d.gd")
const Boss = preload("res://scripts2d/boss_2d.gd")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var prefixo: String = args[0] if args.size() > 0 else "captura_chefes"
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	var run = main.run
	Fase.definir("pedreira")
	run.menus.fechar()
	run._on_jogar()
	await physics_frame
	run.estado = run.Estado.LUTA
	paused = false
	run.matar_todos()
	var p = run.player
	p.god_mode = true
	p.autocast = false
	var base: Vector2 = run.room.spawn_jogador + Vector2(0, 40)
	p.global_position = base
	var lista := [["stone_herald", 150.0], ["ossuary_warden", 330.0], ["crypt_guardian", 560.0]]
	for it in lista:
		var e = (Boss if it[0] == "crypt_guardian" else Enemy).new()
		run.atores.add_child(e)
		e.setup(it[0], p, base + Vector2(float(it[1]), 0))
		e.set_physics_process(false)
	run.camera.position = base + Vector2(280, 0)
	run.camera.reset_smoothing()
	for i in 40:
		await physics_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png("%s_chefes.png" % prefixo)
	quit()
