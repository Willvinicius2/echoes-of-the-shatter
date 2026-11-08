extends SceneTree
## Capturas dos marcos da fase aberta pela cena principal (Main2D, com o mundo no SubViewport de pixel art; precisa de
## janela, use xvfb no CI):
##   godot --path godot --resolution 1600x900 --script res://scripts2d/tools/captura_marcos_2d.gd -- prefixo nome:x:y[:g] ...
## Cada ponto é "nome:x:y" (células do mapa, aceita fração): o jogador vai para lá e grava <prefixo>_<nome>.png. A
## corrida fica parada (sem horda nem tiro automático); o sufixo ":g" faz os encontros (`@guarda`) ao alcance
## nascerem adormecidos, e eles seguem dormindo na foto. Sem pontos, captura o início, a ruína (de longe e de perto), a bifurcação, o trecho 3, o bolsão, o respiro, a aproximação do
## portão, o portão e a entrada da arena (as coordenadas vêm de tools/mapas/marcos_fase1.py, notas `capturas`).
const MainScene = preload("res://scenes2d/Main2D.tscn")
const PONTOS_PADRAO := ["1_inicio:14:86", "2_ruina:90.5:55.2", "2a_ruina_perto:91.4:56.8", "3_bifurcacao:99.2:53.9:g", "3a_trecho3:116.8:49.5:g", "4_bolsao:100:39:g", "5_respiro:125.5:47.6", "6a_aproximacao:140.6:37.6", "6_portao:140.6:34.5", "7_arena:141:30.5"]

func _initialize() -> void:
	create_timer(150.0).timeout.connect(func():
		push_error("captura_marcos_2d: tempo esgotado (150 s)")
		quit(2))
	var args := OS.get_cmdline_user_args()
	var prefixo: String = args[0] if args.size() > 0 else "captura_marcos"
	var pontos: Array = Array(args.slice(1)) if args.size() > 1 else PONTOS_PADRAO
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	var run = main.run
	run.menus.fechar()
	run.estado = run.Estado.LIMPA   # sem horda nem encontros por conta própria; a câmera segue o jogador fora do menu
	paused = false
	run.player.god_mode = true
	run.player.autocast = false   # sem tiro automático: a foto não acorda nem fere ninguém
	var tile: float = run.room.tile
	for ponto in pontos:
		var q := String(ponto).split(":")
		run.player.global_position = Vector2((float(q[1]) + 0.5) * tile, (float(q[2]) + 0.5) * tile)
		run.player.velocity = Vector2.ZERO
		for e in get_nodes_in_group("hurtable"):
			if e.has_meta("guarda"):
				e.queue_free()   # cada foto começa limpa: só nascem os encontros do ponto que pede ":g"
		run._guardas_pend = run.room.guardas.duplicate()
		if q.size() > 3 and q[3] == "g":
			run._mult_onda = {"hp": 1.0, "damage": 1.0, "speed": 1.0, "xp": 1.0}
			run._guardas_t = 1.0
			run._tick_guardas(0.0)
			for e in get_nodes_in_group("hurtable"):
				if e.has_meta("guarda"):
					e.raio_despertar = 1.0   # dorme durante a foto, mesmo com o jogador dentro do raio de acordar
		run.camera.position = run.player.global_position
		run.camera.reset_smoothing()
		for i in 40:
			await physics_frame
		await RenderingServer.frame_post_draw
		root.get_viewport().get_texture().get_image().save_png("%s_%s.png" % [prefixo, q[0]])
	quit()
