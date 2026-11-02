extends SceneTree
## Mede FPS e tempos reais COM JANELA (nao use --headless): cena Run2D, arqueiro com habilidades ativas.
##   godot --path godot --script res://scripts2d/tools/fps_janela_2d.gd -- [segundos=30] [id=hollow_sentinel] [vsync=0]
## Fases: inicio da fase, horda de 200, horda de 500 (acumulada). Imprime por fase: FPS medio, p99,
## ms de processo/fisica, draw calls, nos. Vsync desligado por padrao para ver o custo real do quadro.
const RunScene = preload("res://scenes2d/Run2D.tscn")
const ConsoleDev = preload("res://scripts2d/console_dev_2d.gd")
const SKILLS := ["power_shot", "shock_arrow", "chain_lightning", "poison_arrow", "frost_arrow", "flecha_ardente",
	"lightning_rod", "toxic_tornado", "ice_comet", "frost_nova", "fire_serpent", "herald_thunder", "herald_plague", "herald_ice", "arauto_cinzas"]

func _initialize() -> void:
	await _executar()

func _executar() -> void:
	var args := OS.get_cmdline_user_args()
	var seg := float(args[0]) if args.size() > 0 else 30.0
	var id: String = args[1] if args.size() > 1 else "hollow_sentinel"
	var vsync := (int(args[2]) if args.size() > 2 else 0) != 0
	if not vsync:
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	var run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	for i in 30:
		await process_frame
	run.player.god_mode = true
	var h: RefCounted = run.player.habilidades
	h.ganhar_pontos(500)
	var slot := 0
	for s in SKILLS:
		if not h.defs.has(s):
			continue
		_aprender(h, s)
		if h.defs[s]["tipo"] == "ativa" and slot < 4:
			h.equipar(slot, s)
			slot += 1
	if run.player.has_method("_atualizar_heralds"):
		run.player.call("_atualizar_heralds")
	print("RENDERER: %s | %s | janela %s | vsync %s" % [RenderingServer.get_current_rendering_method(), RenderingServer.get_video_adapter_name(), DisplayServer.window_get_size(), vsync])
	print("BUILD: %s" % ("debug" if OS.is_debug_build() else "release"))
	if args.size() > 3:
		for nome in args[3].split(","):
			var alvo: Node = run.get("room").get_node_or_null(nome) if nome != "ATORES" else run.get("atores")
			if nome == "ROOM": run.get("room").visible = false
			elif nome == "ROOMOFF": run.get("room").process_mode = Node.PROCESS_MODE_DISABLED
			elif alvo != null: alvo.visible = false
			print("oculto: ", nome, " ", alvo)
	await _fase("1 inicio", seg)
	ConsoleDev.spawnar_horda(run, id, 200)
	await _fase("2 horda 200", seg)
	ConsoleDev.spawnar_horda(run, id, 300)
	await _fase("3 horda 500", seg)
	quit()

func _fase(nome: String, seg: float) -> void:
	for i in 60:   # aquecimento (shaders, quadros de sprite)
		await process_frame
	var dts: Array[float] = []
	var t_ini := Time.get_ticks_usec()
	var t_ant := t_ini
	var proc := 0.0
	var fis := 0.0
	var dc := 0.0
	var n := 0
	while (Time.get_ticks_usec() - t_ini) < seg * 1e6:
		paused = false   # painéis de nível pausam o jogo: a medição quer o jogo rodando
		await process_frame
		var t := Time.get_ticks_usec()
		dts.append((t - t_ant) / 1000.0)
		t_ant = t
		proc += Performance.get_monitor(Performance.TIME_PROCESS)
		fis += Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)
		dc += Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
		n += 1
	var soma := 0.0
	for d in dts:
		soma += d
	var media := soma / dts.size()
	var ord := dts.duplicate()
	ord.sort()
	var p99: float = ord[int(ord.size() * 0.99)]
	var n33 := 0
	var n50 := 0
	for d in dts:
		if d > 33.4: n33 += 1
		if d > 50.0: n50 += 1
	print("FASE %s: FPS medio %.1f | quadro medio %.2f ms | p99 %.2f ms (%.1f FPS) | pior %.1f ms | >33ms: %d | >50ms: %d | processo %.2f ms | fisica %.2f ms | draw calls %d | nos %d | inimigos %d" % [
		nome, 1000.0 / media, media, p99, 1000.0 / p99, ord[-1], n33, n50, proc / n * 1000.0, fis / n * 1000.0, int(dc / n),
		int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)), get_nodes_in_group("hurtable").size()])

func _aprender(h: RefCounted, id: String) -> void:
	var pai: String = h.defs[id]["pai"]
	if pai != "" and h.nivel(pai) == 0:
		_aprender(h, pai)
	if h.nivel(id) == 0:
		h.aprender(id)



