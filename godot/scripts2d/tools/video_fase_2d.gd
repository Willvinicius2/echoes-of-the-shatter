extends SceneTree
## Vídeo da fase aberta com a câmera seguindo o jogador pelo caminho principal (precisa de janela; use xvfb):
##   godot --path godot --write-movie saida.avi --fixed-fps 30 --script res://scripts2d/tools/video_fase_2d.gd -- 40
## O argumento é a duração em segundos de física (com --fixed-fps 30 o vídeo dura a metade).
const RunScene = preload("res://scenes2d/Run2D.tscn")
const ROTA := [Vector2(14, 86), Vector2(22, 82), Vector2(32, 78), Vector2(44, 74), Vector2(56, 68), Vector2(68, 62),
	Vector2(78, 58), Vector2(90, 54), Vector2(102, 50), Vector2(114, 46), Vector2(126, 40), Vector2(136, 33), Vector2(146, 27)]

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var duracao: float = float(args[0]) if args.size() > 0 else 40.0
	var run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	var p = run.player
	p.god_mode = true
	var i := 1
	var t := 0.0
	while t < duracao:
		if run.ui.aberta:
			run.ui.escolher(0)   # o vídeo mostra o mapa: carta escolhida na hora
		if run.estado == run.Estado.ROTA:
			run.escolher_rota(run.opcoes_rota[0])
		if i < ROTA.size():
			var alvo: Vector2 = run.room._centro(int(ROTA[i].x), int(ROTA[i].y))
			if p.global_position.distance_to(alvo) < 40.0:
				i += 1
			p.auto_move = (alvo - p.global_position).normalized()
		else:
			p.auto_move = Vector2.ZERO
		await physics_frame
		t += 1.0 / 30.0
	quit()
