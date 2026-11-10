extends SceneTree
## Capturas das telas da partida pela cena principal (precisa de janela; use xvfb): título, cartas de Eco, gema, nível
## e baú, jogo, pausa, chefe, portal, vitória e derrota.  godot --path godot --resolution 1280x720 --script res://scripts2d/tools/captura_telas_2d.gd -- pasta
const MainScene = preload("res://scenes2d/Main2D.tscn")
func _initialize() -> void:
	var pasta: String = OS.get_cmdline_user_args()[0]
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	var run = main.run
	for i in 30: await process_frame
	await foto(pasta + "/titulo.png")
	run.menus.opcoes.prologo_visto = true
	run.menus.mostrar_titulo()
	for i in 10: await process_frame
	await foto(pasta + "/titulo2.png")
	run.menus.jogar.emit()
	for i in 30: await process_frame
	run._usar_gema_habilidade()
	for i in 40: await process_frame
	await foto(pasta + "/afinidade.png")
	run.ui.escolher(3)
	for i in 5: await process_frame
	run._usar_gema_habilidade()
	for i in 40: await process_frame
	await foto(pasta + "/gema.png")
	run.ui.escolher(0)
	run.nucleo.nivel_ganhar_xp(8)
	run._checar_oferta_nivel()
	for i in 40: await process_frame
	await foto(pasta + "/nivel.png")
	run.ui.escolher(0)
	run.nucleo.nivel_abrir_bau()
	run._checar_oferta_nivel()
	for i in 40: await process_frame
	await foto(pasta + "/bau.png")
	run.ui.escolher(0)
	for i in 30: await process_frame
	await foto(pasta + "/jogo.png")
	run._on_pausa_pedida()
	for i in 10: await process_frame
	await foto(pasta + "/pausa.png")
	run._on_retomar()
	# Fim de verdade: adianta o spawner até a última onda, acorda o Guardião, derruba-o e entra no portal.
	run.player.god_mode = true
	while int(run.nucleo.ondas_estado().get("wave", 0)) < int(run.nucleo.ondas_estado().get("waves_total", 1)):
		for sp in run.nucleo.ondas_tick(0.5):
			run.nucleo.ondas_morto(int(sp["id"]))
		run.tempo += 0.5
	run.player.global_position = run.room.empurrar_para_dentro(run.room.posicao_chefe + Vector2(0, 220))
	for i in 20: await physics_frame
	run.acordar_chefe()
	for i in 150: await physics_frame
	await foto(pasta + "/chefe.png")
	run.matar_todos()
	var espera := 0
	while run.posicao_saida() == Vector2.ZERO and espera < 600:
		await physics_frame
		espera += 1
	for i in 90:
		await physics_frame
		if run.ui.aberta:   # a gema que o Guardião solta
			run.ui.escolher(0)
	await foto(pasta + "/portal.png")
	run.player.global_position = run.posicao_saida()
	espera = 0
	while run.menus.tela != run.menus.Tela.FIM and espera < 900:
		await physics_frame
		espera += 1
		if run.ui.aberta:
			run.ui.escolher(0)
	for i in 10: await process_frame
	await foto(pasta + "/fim.png")
	# Derrota: outra corrida, o jogador cai na primeira onda.
	run.menus.jogar.emit()
	for i in 60: await physics_frame
	run.player.god_mode = false
	run.player.take_damage(1.0e9)
	espera = 0
	while run.menus.tela != run.menus.Tela.FIM and espera < 900:
		await physics_frame
		espera += 1
	for i in 10: await process_frame
	await foto(pasta + "/derrota.png")
	quit()
func foto(c: String) -> void:
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(c)
