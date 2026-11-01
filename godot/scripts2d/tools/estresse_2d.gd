extends SceneTree
## Teste de estresse de horda (headless): nasce N inimigos em volta do jogador e mede o custo
## de física/lógica por quadro. Não mede desenho (headless não desenha): serve para comparar
## versões e achar o limite da lógica, não o FPS final.
##   godot --headless --fixed-fps 60 --path godot --script res://scripts2d/tools/estresse_2d.gd -- [n=500] [quadros=300] [id=hollow_sentinel]
## Imprime "ms/quadro" e o número de nós; sai com 1 se a média passar de 16,6 ms.

const RunScene = preload("res://scenes2d/Run2D.tscn")
const ConsoleDev = preload("res://scripts2d/console_dev_2d.gd")

const LIMITE_MS := 16.6

func _initialize() -> void:
	await _executar()

func _executar() -> void:
	var args := OS.get_cmdline_user_args()
	var n := int(args[0]) if args.size() > 0 else 500
	var quadros := int(args[1]) if args.size() > 1 else 300
	var id: String = args[2] if args.size() > 2 else "hollow_sentinel"
	var run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	run.player.god_mode = true
	var nasceram := ConsoleDev.spawnar_horda(run, id, n)
	await physics_frame
	var total_us := 0
	var pior_us := 0
	var spawn_us := 0
	for i in 20:   # aquecimento: o pico do nascimento (shaders, quadros de sprite) não conta na média
		var t1 := Time.get_ticks_usec()
		await physics_frame
		spawn_us = maxi(spawn_us, Time.get_ticks_usec() - t1)
	for i in quadros:
		var t0 := Time.get_ticks_usec()
		await physics_frame
		var dt := Time.get_ticks_usec() - t0
		total_us += dt
		pior_us = maxi(pior_us, dt)
	var media_ms := float(total_us) / quadros / 1000.0
	print("estresse: %d x %s, %d quadros" % [nasceram, id, quadros])
	print("ms/quadro: media %.2f, pior %.2f  (limite %.1f)" % [media_ms, pior_us / 1000.0, LIMITE_MS])
	print("pico de aquecimento: %.1f ms" % (spawn_us / 1000.0))
	print("fisica %.1f ms, processo %.1f ms (ultimo quadro)" % [Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0, Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0])
	print("nos: %d, objetos: %d" % [int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)), int(Performance.get_monitor(Performance.OBJECT_COUNT))])
	quit(1 if media_ms > LIMITE_MS else 0)
