extends SceneTree
## Captura uma sala sem inimigos (precisa de janela; use xvfb no CI):
##   godot --path godot --script res://scripts2d/tools/captura_sala_2d.gd -- saida.png res://data2d/rooms/sala_1.txt
const RunScene = preload("res://scenes2d/Run2D.tscn")

func _initialize() -> void:
	# Vigia: se algo travar ou der erro depois de um await, o Godot ficaria vivo para sempre.
	create_timer(60.0).timeout.connect(func():
		push_error("captura_sala_2d: tempo esgotado (60 s)")
		quit(2))
	var args := OS.get_cmdline_user_args()
	var saida: String = args[0] if args.size() > 0 else "captura_sala.png"
	var sala: String = args[1] if args.size() > 1 else "res://data2d/rooms/sala_1.txt"
	var run = RunScene.instantiate()
	root.add_child(run)
	await physics_frame
	run.menus.fechar()  # a corrida abre no título; fecha o menu para ver a sala
	root.get_tree().paused = false
	run._carregar_sala(0, {"room": sala, "enemies": [], "tipo": "combate"})
	run.player.god_mode = true
	for i in 60:
		await physics_frame
	await RenderingServer.frame_post_draw
	root.get_viewport().get_texture().get_image().save_png(saida)
	quit()
