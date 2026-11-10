extends SceneTree
## Captura do Arqueiro com Arauto de Pedra, Carcereiro do Ossuário e Guardião lado a lado na Pedreira (mundo em pixel art
## do Main2D, câmera de 640x360 escalada para a janela). Precisa de janela:
##   godot --path godot --resolution 1920x1080 --script res://scripts2d/tools/captura_chefes_2d.gd -- prefixo
const MainScene = preload("res://scenes2d/Main2D.tscn")
const Enemy = preload("res://scripts2d/enemy_2d.gd")
const Boss = preload("res://scripts2d/boss_2d.gd")
const Fase = preload("res://scripts2d/fase_2d.gd")

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
	await _foto(run, p, base, [["stone_herald", 300.0], ["ossuary_warden", 640.0]], 380.0, "%s_arauto_carcereiro.png" % prefixo)
	await _foto(run, p, base, [["crypt_guardian", 360.0]], 180.0, "%s_guardiao.png" % prefixo)
	# segunda rodada num ponto da sala longe de qualquer braseiro: confere o tom da pedra e do osso sem a luz do fogo
	var longe := _ponto_longe_de_braseiros(run, base)
	if longe.distance_to(base) > 1.0:
		base = longe
		p.global_position = base
		await _foto(run, p, base, [["stone_herald", 300.0], ["ossuary_warden", 640.0]], 380.0, "%s_arauto_carcereiro_sem_braseiro.png" % prefixo)
		await _foto(run, p, base, [["crypt_guardian", 360.0]], 180.0, "%s_guardiao_sem_braseiro.png" % prefixo)
	quit()

## Cria os chefes de `lista` ([id, deslocamento x]) ao lado do jogador, centra a câmera em `base + cam_x` e grava a imagem.
func _foto(run, p, base: Vector2, lista: Array, cam_x: float, arquivo: String) -> void:
	var criados: Array = []
	for it in lista:
		var e = (Boss if it[0] == "crypt_guardian" else Enemy).new()
		run.atores.add_child(e)
		e.setup(it[0], p, base + Vector2(float(it[1]), 0))
		e.set_physics_process(false)
		criados.append(e)
	run.camera.position = base + Vector2(cam_x, 0)
	run.camera.reset_smoothing()
	for i in 40:
		await physics_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(arquivo)
	for e in criados:
		e.queue_free()

## Ponto da sala (grade de candidatos) mais distante dos braseiros, com folga para os quatro personagens; `padrao` se não achar.
func _ponto_longe_de_braseiros(run, padrao: Vector2) -> Vector2:
	var clima = get_first_node_in_group("clima_2d")
	if clima == null:
		return padrao
	var pos: Array = []
	for b in clima._braseiros:
		pos.append(b["pos"])
	if pos.is_empty():
		return padrao
	var tam: Vector2 = run.room.tamanho_px()
	var melhor := padrao
	var melhor_d := 0.0
	for ix in range(2, 15):
		for iy in range(2, 8):
			var c := Vector2(tam.x * ix / 16.0, tam.y * iy / 9.0)
			var d := 1.0e9
			for q in pos:
				d = minf(d, c.distance_to(q))
			if d > melhor_d and c.x < tam.x - 1500.0:
				melhor_d = d
				melhor = c
	return melhor
