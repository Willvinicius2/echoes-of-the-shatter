extends SceneTree
## Cena do título: o arqueiro parado no início da fase (estrada e braseiros), tirada do próprio jogo na grade de
## pixel art (SubViewport do mundo, sem HUD e sem inimigos). Precisa de janela (xvfb).
##   godot --path godot --resolution 1280x720 --script res://scripts2d/tools/captura_titulo_2d.gd -- saida.png [dx] [dy] [fx] [fy]
## dx, dy: deslocamento do jogador a partir do ponto de início, em px do mundo. A saída é um recorte de 320 x 180
## (o título mostra em 4x, sem suavizar) com o arqueiro em fx, fy do quadro (0..1; padrão 0,64 e 0,52), à direita
## do painel. Grave em art2d/ui/titulo_fundo.png.
const MainScene = preload("res://scenes2d/Main2D.tscn")
const RECORTE := Vector2i(320, 180)

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	var run = main.run
	run.menus.opcoes.prologo_visto = true
	run.menus.opcoes.tutorial_visto = true
	run.menus.jogar.emit()
	for i in 5: await physics_frame
	run.player.god_mode = true
	if args.size() >= 3:
		run.player.global_position += Vector2(float(args[1]), float(args[2]))
	run.player.facing = Vector2(-1, 0.4).normalized()
	for i in 240:   # o clima (fogo, névoa) assenta; quem nascer sai de cena antes da foto
		await physics_frame
		for e in root.get_tree().get_nodes_in_group("hurtable"):
			if e != run.player:
				e.queue_free()
		for g in root.get_tree().get_nodes_in_group("coletaveis"):
			g.queue_free()
	await RenderingServer.frame_post_draw
	var sv: SubViewport = main._cont.get_child(0)
	var img: Image = sv.get_texture().get_image()
	var fx := float(args[3]) if args.size() >= 5 else 0.64
	var fy := float(args[4]) if args.size() >= 5 else 0.52
	var no_quadro: Vector2 = run.player.get_global_transform_with_canvas().origin
	var x0 := clampi(roundi(no_quadro.x - RECORTE.x * fx), 0, img.get_width() - RECORTE.x)
	var y0 := clampi(roundi(no_quadro.y - RECORTE.y * fy), 0, img.get_height() - RECORTE.y)
	img.get_region(Rect2i(Vector2i(x0, y0), RECORTE)).save_png(args[0])
	quit()
