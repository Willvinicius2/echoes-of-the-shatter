extends SceneTree
## Capturas dos marcos da fase aberta pela cena principal (Main2D, com o mundo no SubViewport de pixel art; precisa de
## janela, use xvfb no CI):
##   godot --path godot --resolution 1600x900 --script res://scripts2d/tools/captura_marcos_2d.gd -- prefixo [sala=<arquivo>] nome:x:y[:g][:d][:cx<px>][:cy<px>] ...
## Cada ponto é "nome:x:y" (células do mapa, aceita fração): o jogador vai para lá e grava <prefixo>_<nome>.png. A
## corrida fica parada (sem horda nem tiro automático); o sufixo ":g" faz os encontros (`@guarda`) ao alcance
## nascerem adormecidos, e eles seguem dormindo na foto; os sufixos ":cx<px>" e ":cy<px>" deslocam só a câmera (px do mundo;
## cx positivo vai para a direita, cy positivo desce) para o marco ficar acima do HUD e o jogador não tapar a cena; a dica de
## controles dos primeiros segundos fica escondida, a não ser que o ponto peça ":d". `sala=<arquivo>` (logo depois do prefixo)
## troca o mapa antes das fotos (por exemplo `sala=res://data2d/rooms/fase_2.txt`); sem ele fica a fase 1 e, sem pontos, captura o início, a ruína (de
## longe e de perto), a bifurcação, a trilha do bolsão, o trecho 3, o bolsão, o respiro, a estrada com a luz do respiro ao
## fundo, a aproximação do portão, o portão e a entrada da arena (as coordenadas vêm de tools/mapas/marcos_fase1.py, notas `capturas`).
const MainScene = preload("res://scenes2d/Main2D.tscn")
const PONTOS_PADRAO := ["1_inicio:14:86:d", "2_ruina:92.2:56.4:cy40", "2a_ruina_perto:90.8:59:cy-105", "3_bifurcacao:99.2:53.9:g", "3b_trilha_bolsao:100.9:43.6:g:cy-60",
		"3a_trecho3:116.8:49.5:g", "4_bolsao:100:39:g", "5_respiro:125.5:47.6", "5a_estrada_luz:121.5:48.6:cx200", "6a_aproximacao:140.6:37.6", "6_portao:140.6:34.5", "7_arena:141:30.5"]

func _initialize() -> void:
	create_timer(240.0).timeout.connect(func():
		push_error("captura_marcos_2d: tempo esgotado (240 s)")
		quit(2))
	var args := OS.get_cmdline_user_args()
	var prefixo: String = args[0] if args.size() > 0 else "captura_marcos"
	var resto: Array = Array(args.slice(1))
	var sala := ""
	if resto.size() > 0 and String(resto[0]).begins_with("sala="):
		sala = String(resto[0]).substr(5)
		resto = resto.slice(1)
	var pontos: Array = resto if resto.size() > 0 else PONTOS_PADRAO
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	var run = main.run
	run.menus.fechar()
	if sala != "":
		run._carregar_sala(0, {"id": "captura", "tipo": "combate", "room": sala, "enemies": ""})
	run.estado = run.Estado.LIMPA   # sem horda nem encontros por conta própria; a câmera segue o jogador fora do menu
	paused = false
	run.player.god_mode = true
	run.player.autocast = false   # sem tiro automático: a foto não acorda nem fere ninguém
	run.camera.position_smoothing_enabled = false   # a câmera chega ao ponto na hora: o suavizado ainda estaria a caminho depois de um salto de 100 células
	var tile: float = run.room.tile
	for ponto in pontos:
		var q := String(ponto).split(":")
		run.player.global_position = Vector2((float(q[1]) + 0.5) * tile, (float(q[2]) + 0.5) * tile)
		run.player.velocity = Vector2.ZERO
		for e in get_nodes_in_group("hurtable"):
			if e.has_meta("guarda"):
				e.queue_free()   # cada foto começa limpa: só nascem os encontros do ponto que pede ":g"
		run._guardas_pend = run.room.guardas.duplicate()
		var camera_dx := 0.0
		var camera_dy := 0.0
		var com_guardas := false
		var com_dica := false
		for sufixo in q.slice(3):
			if sufixo == "g":
				com_guardas = true
			elif sufixo == "d":
				com_dica = true
			elif sufixo.begins_with("cx"):
				camera_dx = float(sufixo.substr(2))
			elif sufixo.begins_with("cy"):
				camera_dy = float(sufixo.substr(2))
		if com_guardas:
			run._mult_onda = {"hp": 1.0, "damage": 1.0, "speed": 1.0, "xp": 1.0}
			run._guardas_t = 1.0
			run._tick_guardas(0.0)
			for e in get_nodes_in_group("hurtable"):
				if e.has_meta("guarda"):
					e.raio_despertar = 1.0   # dorme durante a foto, mesmo com o jogador dentro do raio de acordar
		run.hud._rel = 0.0 if com_dica else 99.0   # a lista de controles cobre o cenário nos primeiros 5 s: só a foto do início a leva
		run.set_physics_process(true)
		var centro: Vector2 = run.player.global_position
		if camera_dx != 0.0 or camera_dy != 0.0:
			# só a câmera anda (o jogador e o spawn dos encontros ficam onde estão): a corrida recentraria a câmera e a vinheta
			# no jogador a cada passo, então ela fica parada e a vinheta vai junto com a câmera
			run.set_physics_process(false)
			centro += Vector2(camera_dx, camera_dy)
			run.room.seguir_vinheta(centro, run.vista().size)
		run.camera.position = centro
		run.camera.position_smoothing_enabled = false   # a corrida religa o suavizado ao ajustar a câmera: sem isto a foto sai deslocada depois de um salto longo
		run.camera.reset_smoothing()
		for i in 40:
			await physics_frame
		await RenderingServer.frame_post_draw
		root.get_viewport().get_texture().get_image().save_png("%s_%s.png" % [prefixo, q[0]])
	quit()
