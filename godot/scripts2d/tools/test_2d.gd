extends SceneTree
## Teste headless do cliente 2D:
##   godot --headless --path godot --script res://scripts2d/tools/test_2d.gd
## Sai com código 1 se algo falhar.

const Csv = preload("res://scripts2d/csv2d.gd")
const SpriteLoader = preload("res://scripts2d/sprite_loader.gd")
const RoomScript = preload("res://scripts2d/room_2d.gd")
const RunScene = preload("res://scenes2d/Run2D.tscn")

var falhas := 0

func check(cond: bool, msg: String) -> void:
	if cond:
		print("ok   ", msg)
	else:
		print("FALHA ", msg)
		falhas += 1

func _initialize() -> void:
	await _testar()
	print("\n", "TUDO OK" if falhas == 0 else "%d FALHA(S)" % falhas)
	quit(0 if falhas == 0 else 1)

func _testar() -> void:
	_testar_manifesto()
	_testar_salas()
	await _testar_upgrades()
	await _testar_corrida()

func _testar_upgrades() -> void:
	var UpScript = preload("res://scripts2d/upgrades_2d.gd")
	var PlayerScript = preload("res://scripts2d/player_2d.gd")
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var up = UpScript.new()
	check(up.defs.size() >= 6 and up.defs.size() <= 8, "pool de 6 a 8 upgrades")
	for id in up.defs:
		check(Csv.t("upgrade.%s.name" % id) != "upgrade.%s.name" % id and Csv.t("upgrade.%s.desc" % id) != "upgrade.%s.desc" % id, "texto de %s" % id)
		var p = PlayerScript.new()
		root.add_child(p)
		await physics_frame
		up.restaurar(p)
		p.reset()
		var base: Dictionary = p.stats.duplicate()
		var st: String = up.defs[id]["stat"]
		check(up.escolher(id, p), "escolhe %s" % id)
		check(not is_equal_approx(p.stats[st], base[st]), "%s muda %s" % [id, st])
		if st == "hp_max":
			check(is_equal_approx(p.hp, p.stats["hp_max"]), "vigor cura o ganho")
		for _i in up.defs[id]["nivel_max"] - 1:
			up.escolher(id, p)
		check(not up.escolher(id, p), "%s para no nível máximo" % id)
		up.restaurar(p)
		check(is_equal_approx(p.stats[st], base[st]) and up.niveis.is_empty(), "restaurar volta a base de %s" % id)
		p.free()
	var cartas: Array = up.sortear(rng, 3)
	check(cartas.size() == 3 and cartas[0] != cartas[1] and cartas[1] != cartas[2] and cartas[0] != cartas[2], "sorteio de 3 cartas distintas")

func _esperar(cond: Callable, limite: float) -> void:
	var t := 0.0
	while not cond.call() and t < limite:
		await physics_frame
		t += 1.0 / 60.0

func _testar_manifesto() -> void:
	var ids := {}
	for r in Csv.rows("res://data2d/sprites_manifest.csv"):
		ids[r["id"]] = true
		if FileAccess.file_exists(r["arquivo"]):
			var img := Image.load_from_file(ProjectSettings.globalize_path(r["arquivo"]))
			var esp := Vector2i(int(r["quadro"]) * int(r["quadros"]), int(r["quadro"]) * int(r["direcoes"]))
			check(img != null and img.get_size() == esp, "folha %s tem %s" % [r["arquivo"], esp])
	for id in ids:
		var sf := SpriteLoader.frames_for(id)
		check(sf.has_animation("idle_0") and sf.has_animation("run_4") and sf.has_animation("death_0"), "frames de %s" % id)
	for r in Csv.rows("res://data2d/run.csv"):
		for p in r["enemies"].split("|"):
			var id: String = p.split(":")[0]
			check(ids.has(id) and not Csv.enemy(id).is_empty(), "inimigo %s com sprite e stats" % id)
	var d = SpriteLoader.dir_for(Vector2.LEFT, 5)
	check(d[0] == 2 and d[1], "oeste = linha leste espelhada")
	d = SpriteLoader.dir_for(Vector2.UP, 5)
	check(d[0] == 4 and not d[1], "norte = linha 4")

func _testar_salas() -> void:
	for r in Csv.rows("res://data2d/run.csv"):
		var sala = RoomScript.new()
		check(sala.carregar(r["room"]), "carrega " + r["room"])
		check(sala.colunas == 24 and sala.linhas == 13, "%s tem 24x13" % r["room"])
		check(sala.spawn_jogador != Vector2.ZERO and sala.spawns_inimigos.size() > 0, "%s tem P e E" % r["room"])
		check(sala.celulas_porta.size() > 0, "%s tem porta" % r["room"])
		check(sala.props.size() > 0, "%s tem props" % r["room"])
		var ok_props := true
		for pr in sala.props:
			var c := Vector2i(int(pr["pos"].x / sala.tile), int(pr["pos"].y / sala.tile))
			ok_props = ok_props and sala._props_def.has(pr["id"]) and sala._props_arte.has(pr["id"])
			ok_props = ok_props and FileAccess.file_exists(sala._props_arte[pr["id"]]["arquivo"])
			# a coluna da porta (11 a 13) fica livre nas linhas 2 a 4
			var solido: bool = float(sala._props_def[pr["id"]]["solido_l"]) > 0.0
			ok_props = ok_props and not (solido and c.x >= 11 and c.x <= 13 and c.y >= 2 and c.y <= 4)
		check(ok_props, "%s: props com arte, definição e porta livre" % r["room"])
		sala.free()

func _testar_corrida() -> void:
	var run = RunScene.instantiate()
	root.add_child(run)
	await physics_frame
	var p = run.player
	check(run.estado == run.Estado.LUTA and run.vivos == 3, "sala 1 começa com 3 inimigos")

	# Combate real: o arqueiro mira no inimigo mais próximo e as flechas o derrubam.
	p.god_mode = true
	var alvo = get_nodes_in_group("hurtable")[0]
	var antes: float = alvo.hp
	var t := 0.0
	while is_instance_valid(alvo) and alvo.hp > 0.0 and t < 12.0:
		p.auto_aim = alvo.global_position - p.global_position
		await physics_frame
		t += 1.0 / 60.0
	p.auto_aim = Vector2.ZERO
	check(not is_instance_valid(alvo) or alvo.hp < antes, "flechas ferem inimigo")

	# Percorre todas as salas: mata tudo, espera a porta, atravessa.
	for i in run.salas.size():
		check(run.indice == i, "estando na sala %d" % (i + 1))
		run.matar_todos()
		await _esperar(func(): return run.estado == run.Estado.LIMPA, 5.0)
		check(run.estado == run.Estado.LIMPA, "sala %d limpa" % (i + 1))
		await _esperar(func(): return run._timer <= 0.0, 3.0)
		await physics_frame
		await physics_frame
		if i < run.salas.size() - 1:
			check(run.estado == run.Estado.ESCOLHA and run.ui.aberta, "sala %d oferece cartas" % (i + 1))
			run.ui.escolher(0)
			check(run.estado == run.Estado.LIMPA and run.upgrades.niveis.size() > 0, "carta escolhida e porta aberta")
		else:
			check(run.estado == run.Estado.LIMPA, "sala do chefe não oferece cartas")
		p.global_position = run.room._centro(12, 3)
		p.auto_move = Vector2.UP
		await _esperar(func(): return run.estado != run.Estado.LIMPA, 4.0)
		p.auto_move = Vector2.ZERO
		if i < run.salas.size() - 1:
			check(run.indice == i + 1, "porta leva à sala %d" % (i + 2))
		else:
			check(run.estado == run.Estado.VENCEU, "vitória após o chefe")

	await _esperar(func(): return run.estado == run.Estado.LUTA, 5.0)
	check(run.estado == run.Estado.LUTA and run.indice == 0, "corrida reinicia após vencer")

	# Morte e reinício.
	p.god_mode = false
	p.invencivel = 0.0
	p.take_damage(1.0e6)
	check(run.estado == run.Estado.MORTO and p.esta_morto(), "morte do jogador")
	await _esperar(func(): return run.estado == run.Estado.LUTA, 5.0)
	check(run.estado == run.Estado.LUTA and p.hp == p.stats["hp_max"], "reinicia com vida cheia")
	run.queue_free()
