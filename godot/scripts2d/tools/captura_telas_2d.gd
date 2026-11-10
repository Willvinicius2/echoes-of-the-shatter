extends SceneTree
## Capturas das telas da partida pela cena principal (precisa de janela; use xvfb): título, cartas de Eco, gema, nível
## e baú, jogo, pausa e fim.  godot --path godot --resolution 1280x720 --script res://scripts2d/tools/captura_telas_2d.gd -- pasta
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
	run.estado = run.Estado.VENCEU
	run._mostrar_fim()
	for i in 10: await process_frame
	await foto(pasta + "/fim.png")
	quit()
func foto(c: String) -> void:
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(c)
