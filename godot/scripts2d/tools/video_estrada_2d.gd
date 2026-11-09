extends SceneTree
## Vídeo da corrida de ponta a ponta pela estrada da fase aberta, na cena principal (mundo em pixel art, HUD, horda e
## encontros do mapa de verdade). O arqueiro anda sozinho pela estrada principal (o primeiro `@caminho` da sala) até o
## portão, atira no que aparece (autocast) e fica invencível para o vídeo não terminar na primeira surra. Precisa de
## janela (xvfb):
##   godot --rendering-driver opengl3 --path godot --write-movie saida.avi --fixed-fps 30 --resolution 1280x720 \
##         --script res://scripts2d/tools/video_estrada_2d.gd -- [segundos=60] [inicio_em_tiles=0]
## `inicio_em_tiles`: quantos tiles da estrada o arqueiro já andou quando o vídeo começa (0 = o início da fase).
const MainScene = preload("res://scenes2d/Main2D.tscn")
const Terreno = preload("res://scripts2d/terreno_2d.gd")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var duracao: float = float(args[0]) if args.size() > 0 else 60.0
	var inicio: float = float(args[1]) if args.size() > 1 else 0.0
	var main = MainScene.instantiate()
	root.add_child(main)
	await physics_frame
	var run = main.run
	run._on_jogar()   # o botão Jogar do título: corrida nova na horda de verdade
	await physics_frame
	var p = run.player
	p.god_mode = true
	var rota: PackedVector2Array = Terreno.spline(run.room.caminhos[0]["pts"], 24.0)
	var i := 0
	if inicio > 0.0:
		var andado := 0.0
		while i < rota.size() - 1 and andado < inicio * float(run.room.tile):
			andado += rota[i].distance_to(rota[i + 1])
			i += 1
		p.global_position = rota[i]
		run.camera.position = p.global_position
		run.camera.reset_smoothing()
	else:
		for k in rota.size():
			if rota[k].distance_to(p.global_position) < rota[i].distance_to(p.global_position):
				i = k
	var t := 0.0
	var dt := 1.0 / float(Engine.physics_ticks_per_second)   # o laço anda por passo de física, não por quadro do filme
	while t < duracao and i < rota.size() - 1:
		if run.ui.aberta:
			run.ui.escolher(0)   # cartas e gemas: sempre a primeira opção
		while i < rota.size() - 1 and p.global_position.distance_to(rota[i]) < 48.0:
			i += 1
		p.auto_move = (rota[i] - p.global_position).normalized()
		await physics_frame
		t += dt
	p.auto_move = Vector2.ZERO
	for k in 90:   # 1,5 s parado no fim, a tempo de a câmera assentar
		await physics_frame
	quit()
