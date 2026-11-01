extends SceneTree
## Capturas da fase aberta (precisa de janela; use xvfb): visão do mapa inteiro e da câmera em cada zona.
##   godot --path godot --script res://scripts2d/tools/captura_fase_2d.gd -- pasta_de_saida
const RunScene = preload("res://scenes2d/Run2D.tscn")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var pasta: String = args[0] if args.size() > 0 else "capturas_fase"
	DirAccess.make_dir_recursive_absolute(pasta)
	var run = RunScene.instantiate()
	root.add_child(run)
	await physics_frame
	run.menus.fechar()
	run.estado = run.Estado.LUTA   # a corrida abre no título; a câmera só segue fora do menu
	paused = false
	run.player.god_mode = true
	var room = run.room
	# Câmera do jogo em cada zona: início, travessia do riacho, ruínas e arena do Guardião.
	var pontos := {
		"1_inicio": room.spawn_jogador,
		"2_riacho": room._centro(82, 57),
		"3_ruinas": room._centro(124, 52),
		"6_bosque_e_borda": room._centro(30, 12),
		"4_arena_guardiao": room.posicao_chefe + Vector2(0, 200),
	}
	for nome in pontos:
		run.player.global_position = pontos[nome]
		for i in 30:
			await physics_frame
		run.camera.reset_smoothing()
		await _salvar(pasta.path_join(nome + ".png"))
	# Portal aberto na arena.
	run.player.global_position = room.posicao_portal + Vector2(0, 160)
	run._abrir_portal()
	for i in 40:
		await physics_frame
	run.camera.reset_smoothing()
	await _salvar(pasta.path_join("5_portal.png"))
	# Mapa inteiro.
	for n in get_nodes_in_group("hurtable"):
		n.visible = false
	run.set_physics_process(false)
	var vp: Vector2 = run.get_viewport_rect().size
	var tam: Vector2 = room.tamanho_px()
	var z := minf(vp.x / tam.x, vp.y / tam.y)
	run.camera.limit_left = -100000
	run.camera.limit_top = -100000
	run.camera.limit_right = 100000
	run.camera.limit_bottom = 100000
	run.camera.zoom = Vector2(z, z)
	run.camera.position_smoothing_enabled = false
	run.camera.position = tam / 2.0
	run.hud.visible = false
	for i in 5:
		await physics_frame
	await _salvar(pasta.path_join("0_mapa_inteiro.png"))
	quit()

func _salvar(caminho: String) -> void:
	await process_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(caminho)
	print("captura: ", caminho)
