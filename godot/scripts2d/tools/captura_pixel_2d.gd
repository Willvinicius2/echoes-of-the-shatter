extends SceneTree
## Captura pela cena principal (Main2D), ou seja, com o mundo no SubViewport de pixel art (precisa de janela):
##   godot --path godot --resolution 2560x1440 --script res://scripts2d/tools/captura_pixel_2d.gd -- prefixo
## Grava <prefixo>_<ponto>.png em quatro pontos da fase aberta (início, riacho, ruínas, arena do Guardião).
const MainScene = preload("res://scenes2d/Main2D.tscn")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var prefixo: String = args[0] if args.size() > 0 else "captura_pixel"
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	var run = main.run
	run.menus.fechar()
	run.estado = run.Estado.LUTA   # a corrida abre no título; a câmera só segue fora do menu
	paused = false
	run.player.god_mode = true
	var room = run.room
	var pontos := {
		"1_inicio": room.spawn_jogador,
		"2_riacho": room._centro(82, 57),
		"3_ruinas": room._centro(124, 52),
		"4_arena": room.posicao_chefe + Vector2(0, 200),
	}
	for nome in pontos:
		run.player.global_position = pontos[nome]
		for i in 40:
			await physics_frame
		await RenderingServer.frame_post_draw
		root.get_viewport().get_texture().get_image().save_png("%s_%s.png" % [prefixo, nome])
	quit()
