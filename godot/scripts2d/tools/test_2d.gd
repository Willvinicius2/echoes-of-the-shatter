extends SceneTree
## Teste headless do cliente 2D:
##   godot --headless --path godot --script res://scripts2d/tools/test_2d.gd
## Sai com código 1 se algo falhar.

const Csv = preload("res://scripts2d/csv2d.gd")
const SpriteLoader = preload("res://scripts2d/sprite_loader.gd")
const RoomScript = preload("res://scripts2d/room_2d.gd")
const MetaScript = preload("res://scripts2d/meta_2d.gd")
const RunScene = preload("res://scenes2d/Run2D.tscn")
const GuerreiroTestes = preload("res://scripts2d/tools/test_guerreiro_2d.gd")

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
	_testar_feel()
	_testar_audio_e_ui()
	await _testar_telegrafo()
	_testar_chefe_csv()
	await _testar_chefe_fases()
	await _testar_chefe_luta()
	await _testar_corrida()
	await _testar_rotas()
	await _testar_meta()
	await _testar_forja()
	await _testar_opcoes_steam_tutorial()
	await _testar_status()
	await GuerreiroTestes.new(self, check).rodar()

func _testar_audio_e_ui() -> void:
	var Audio = preload("res://scripts2d/audio_2d.gd")
	var Tema = preload("res://scripts2d/tema_2d.gd")
	var Icones = preload("res://scripts2d/icones_2d.gd")
	var eventos := ["shoot", "hit_enemy", "kill_enemy", "player_hurt", "dodge", "card_open", "card_pick", "door_open", "ui_click", "victory", "defeat", "music_cripta"]
	for ev in eventos:
		var s = Audio.fluxo(ev)
		check(s != null and s.data.size() > 100 and s.mix_rate > 0, "audio.csv: %s carrega" % ev)
	check(Audio.fluxo("music_cripta").loop_mode == AudioStreamWAV.LOOP_FORWARD, "musica em laco")
	check(Audio.fluxo("evento_que_nao_existe") == null, "evento desconhecido nao quebra")
	Audio.tocar("evento_que_nao_existe")
	for r in Csv.rows("res://data2d/audio.csv"):
		check(eventos.has(r["evento"]), "evento %s do audio.csv e usado" % r["evento"])
	check(Tema.tema().has_stylebox("normal", "Button") and Tema.tema().has_stylebox("panel", "PanelContainer"), "tema de pedra tem botao e painel")
	check(Tema.cor("vida") != Color.MAGENTA and Tema.cor("pedra") != Color.MAGENTA, "cores do tema.csv")
	var ids := ["tiro", "esquiva", "bloqueado"]
	for r in Csv.rows("res://data2d/upgrades.csv"):
		ids.append(r["id"])
	for id in ids:
		var tx = Icones.textura(id)
		check(tx != null and tx.get_width() > 0, "icone %s existe" % id)
	for k in ["hud.stamina", "hud.mana", "hud.key.shoot", "hud.key.dodge"]:
		check(Csv.t(k) != k, "loc %s" % k)

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

func _testar_feel() -> void:
	var Feel = load("res://scripts2d/feel_2d.gd")
	for k in ["hit_stop_hit_ms", "hit_stop_kill_ms", "shake_player_amp", "enemy_knockback", "dmg_number_time"]:
		check(Feel.cfg().has(k), "feel.csv tem " + k)
	for r in Csv.rows("res://data2d/enemies.csv"):
		check(float(r["windup"]) >= 0.0 and float(r["windup"]) <= 1.0, "%s: windup entre 0 e 1 s" % r["id"])

## O inimigo corpo a corpo avisa antes de bater: o dano só sai depois do windup, e a esquiva a tempo evita o golpe.
func _testar_telegrafo() -> void:
	var mundo := Node2D.new()
	root.add_child(mundo)
	var p = load("res://scripts2d/player_2d.gd").new()
	mundo.add_child(p)
	var e = load("res://scripts2d/enemy_2d.gd").new()
	mundo.add_child(e)
	e.setup("hollow_sentinel", p, p.global_position + Vector2(40, 0))
	var wind: float = e.stats["windup"]
	check(wind >= 0.3, "sentinela tem telégrafo de %.2f s" % wind)
	var hp0: float = p.hp
	await _esperar(func(): return e.estado == e.Estado.TELEGRAFA, 2.0)
	check(e.estado == e.Estado.TELEGRAFA, "inimigo entra em telégrafo antes de atacar")
	check(p.hp == hp0, "jogador ileso durante o telégrafo")
	await _esperar(func(): return p.hp < hp0, 3.0)
	check(p.hp < hp0, "golpe acerta depois do telégrafo")
	var vida: float = e.hp
	e.take_damage(5.0, e.global_position - Vector2(10, 0))
	check(e.hp == vida - 5.0 and e._kb.length() > 0.0, "flecha fere e empurra o inimigo")
	mundo.queue_free()
	await physics_frame

## boss_patterns_2d.csv: fases em ordem, limiares decrescentes e golpes justos (dano, aviso, folga entre padrões).
func _testar_chefe_csv() -> void:
	var BossScript = load("res://scripts2d/boss_2d.gd")
	var d: Dictionary = BossScript.carregar_padroes()
	var hp_jogador: float = Csv.kv("res://data2d/player.csv")["hp_max"]
	var dano: float = Csv.enemy("crypt_guardian")["damage"]
	check(d["entrada"] > 0.0, "chefe tem animação de entrada (%.1f s)" % d["entrada"])
	var fases: Array = d.keys().filter(func(k): return k is int)
	fases.sort()
	check(fases.size() >= 2 and fases.size() <= 3 and fases[0] == 1, "chefe tem 2 ou 3 fases (%d)" % fases.size())
	var pct_ant := 101.0
	for f in fases:
		check(d[f]["pct"] < pct_ant, "fase %d começa com menos vida que a anterior (%d%%)" % [f, d[f]["pct"]])
		pct_ant = d[f]["pct"]
		check(f == 1 or d[f]["trans"] > 0.0, "fase %d tem transição" % f)
		check(d[f]["passos"].size() >= 3, "fase %d tem pelo menos 3 padrões" % f)
		for p in d[f]["passos"]:
			var golpe: float = dano * p["dano_mult"]
			check(golpe <= hp_jogador * 0.25, "fase %d %s: golpe de %d <= 25%% da vida" % [f, p["padrao"], golpe])
			check(p["aviso"] >= 0.4 and p["pausa"] >= 0.6, "fase %d %s: aviso >= 0,4 s e pausa >= 0,6 s" % [f, p["padrao"]])
			if p["padrao"] == "anel":
				# vão entre dois tiros a 250 px do chefe precisa deixar o arqueiro (raio 14) passar
				var vao: float = TAU * 250.0 / p["qtd"]
				check(vao >= 90.0, "fase %d anel de %d tem vão de %d px" % [f, p["qtd"], vao])

func _novo_duelo(niveis: Dictionary) -> Array:
	var mundo := Node2D.new()
	root.add_child(mundo)
	var p = load("res://scripts2d/player_2d.gd").new()
	mundo.add_child(p)
	var cam := Camera2D.new()
	mundo.add_child(cam)
	var up = load("res://scripts2d/upgrades_2d.gd").new()
	up.restaurar(p)
	p.reset()
	for id in niveis:
		for _i in niveis[id]:
			up.escolher(id, p)
	var b = load("res://scripts2d/boss_2d.gd").new()
	mundo.add_child(b)
	p.global_position = Vector2(0, 0)
	b.setup("crypt_guardian", p, Vector2(0, -320))
	return [mundo, p, b]

func _testar_chefe_fases() -> void:
	var duelo := _novo_duelo({})
	var p = duelo[1]
	var b = duelo[2]
	check(b.invulneravel() and b.ciclo == b.Ciclo.ENTRADA, "chefe nasce em entrada")
	b.take_damage(100.0)
	check(b.hp == b.hp_max, "chefe é invulnerável durante a entrada")
	await _esperar(func(): return b.ciclo != b.Ciclo.ENTRADA, b.entrada_dur + 1.0)
	check(b.ciclo == b.Ciclo.PAUSA and not b.invulneravel(), "entrada termina e o chefe fica vulnerável")
	var vistas: Array = []
	b.fase_mudou.connect(func(f): vistas.append(f))
	p.god_mode = true
	var limiar: float = b.fases[2]["pct"]
	b.take_damage(b.hp_max * (1.0 - limiar / 100.0) + 1.0)
	check(b.fase == 2 and b.ciclo == b.Ciclo.FASE and vistas == [2], "cruzar %d%% da vida abre a fase 2" % limiar)
	var hp: float = b.hp
	b.take_damage(50.0)
	check(b.hp == hp, "chefe é invulnerável na transição de fase")
	await _esperar(func(): return b.ciclo != b.Ciclo.FASE, 3.0)
	check(b.ciclo == b.Ciclo.PAUSA, "transição termina")
	b.take_damage(b.hp_max * (limiar - b.fases[3]["pct"]) / 100.0 + 1.0)
	check(b.fase == 3 and vistas == [2, 3], "fase 3 depois de cruzar %d%%" % b.fases[3]["pct"])
	await _esperar(func(): return b.ciclo != b.Ciclo.FASE, 3.0)
	var vistos := {}
	var t := 0.0
	while t < 40.0 and vistos.size() < 4:
		await physics_frame
		t += 1.0 / 60.0
		if b.ciclo == b.Ciclo.ACAO:
			vistos[b.passo["padrao"]] = true
	check(vistos.size() == 4, "fase 3 executa golpe, anel, leque e investida (%s)" % str(vistos.keys()))
	b.take_damage(1.0e6)
	check(b.estado == b.Estado.MORTO and b.ciclo == b.Ciclo.FIM, "chefe morre")
	await _esperar(func(): return not is_instance_valid(duelo[2]), 4.0)
	check(not is_instance_valid(duelo[2]), "chefe some depois da animação de morte")
	check(get_nodes_in_group("proj_chefe").is_empty(), "tiros do chefe somem quando ele morre")
	duelo[0].queue_free()
	await physics_frame

func _hit_stop_acabou() -> bool:
	return load("res://scripts2d/feel_2d.gd").hit_stop_acabou()

## Arqueiro-robô: mantém distância, circula, atira e esquiva de tiros e golpes avisados.
func _simular_duelo(niveis: Dictionary, limite: float) -> Dictionary:
	var duelo := _novo_duelo(niveis)
	var p = duelo[1]
	var b = duelo[2]
	var t := 0.0
	var lado := 1.0
	var troca := 0.0
	var esquivas := 0
	Engine.time_scale = 4.0
	while is_instance_valid(b) and b.estado != b.Estado.MORTO and not p.esta_morto() and t < limite:
		await physics_frame
		if _hit_stop_acabou():
			Engine.time_scale = 4.0
		t += 1.0 / 60.0
		troca += 1.0 / 60.0
		if troca > 2.2:
			troca = 0.0
			lado = -lado
		var d: Vector2 = p.global_position - b.global_position
		p.auto_aim = (b.global_position - p.global_position) if b.ciclo != b.Ciclo.ENTRADA else Vector2.ZERO
		var rad := 0.0
		if d.length() < 250.0:
			rad = 1.0
		elif d.length() > 380.0:
			rad = -1.0
		p.auto_move = (d.normalized() * rad + d.normalized().orthogonal() * lado * 0.8).normalized()
		if p.dodge_cd <= 0.0 and p.estado != p.Estado.ESQUIVA:
			var fuga := Vector2.ZERO
			for pr in get_nodes_in_group("proj_chefe"):
				var rel: Vector2 = p.global_position - pr.global_position
				if rel.length() < 120.0 and rel.dot(pr.velocity) > 0.0:
					fuga = pr.velocity.normalized().orthogonal() * lado
			if b.ciclo == b.Ciclo.AVISO and b._t < 0.2 and not b.passo.is_empty():
				if b.passo["padrao"] == "investida":
					fuga = b._dir_para_alvo().orthogonal() * lado
				elif b.passo["padrao"] == "golpe" and d.length() < b.passo["alcance"] * 1.3 + 40.0:
					fuga = d.normalized()
			if fuga != Vector2.ZERO:
				esquivas += 1
				p._comecar_esquiva(fuga)
	Engine.time_scale = 1.0
	var r := {"venceu": is_instance_valid(b) and b.estado == b.Estado.MORTO, "tempo": t, "vida": p.hp, "esquivas": esquivas}
	duelo[0].queue_free()
	await physics_frame
	return r

## Chefe derrotável e justo: o robô vence sem upgrades e com upgrades, e a luta não é trivial.
func _testar_chefe_luta() -> void:
	var sem: Dictionary = await _simular_duelo({}, 240.0)
	print("duelo sem upgrades: ", sem)
	check(sem["venceu"], "robô derrota o chefe sem upgrades em %.0f s" % sem["tempo"])
	check(sem["tempo"] >= 15.0, "luta sem upgrades não é trivial (>= 15 s)")
	var com: Dictionary = await _simular_duelo({"power": 2, "haste": 1, "vitality": 1, "multishot": 1}, 240.0)
	print("duelo com upgrades: ", com)
	check(com["venceu"], "robô derrota o chefe com upgrades em %.0f s" % com["tempo"])
	check(com["tempo"] < sem["tempo"], "upgrades encurtam a luta")

func _testar_corrida() -> void:
	var run = RunScene.instantiate()
	run.com_menu = false
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
			if run.caminhos_da_etapa(i + 1).size() > 1:
				await _esperar(func(): return run.estado == run.Estado.ROTA, 4.0)
				check(run.estado == run.Estado.ROTA and paused and run.menus.tela == run.menus.Tela.ROTA, "etapa %d abre a escolha de caminho" % (i + 2))
				run.escolher_rota(run.opcoes_rota[0])
				check(not paused, "escolher o caminho despausa")
			await _esperar(func(): return run.estado == run.Estado.LUTA, 4.0)
			check(run.indice == i + 1 and run.estado == run.Estado.LUTA, "porta leva à sala %d (com fade)" % (i + 2))
		else:
			check(run.estado == run.Estado.VENCEU, "vitória após o chefe")

	await _esperar(func(): return run.menus.tela == run.menus.Tela.FIM, 5.0)
	check(run.menus.tela == run.menus.Tela.FIM and paused, "tela de vitória aparece e pausa o jogo")
	check(run.tempo > 0.0, "contador de corrida andou")
	run.menus.jogar.emit()
	check(not paused and run.estado == run.Estado.LUTA and run.indice == 0 and run.tempo == 0.0, "jogar de novo reinicia após vencer")

	# Pausa com Esc: congela a luta e retoma.
	run._on_pausa_pedida()
	check(run.estado == run.Estado.PAUSA and paused and run.menus.tela == run.menus.Tela.PAUSA, "pausa abre")
	run.menus.retomar.emit()
	check(run.estado == run.Estado.LUTA and not paused and not run.menus.esta_aberta(), "retomar volta à luta")

	# Morte e reinício.
	p.god_mode = false
	p.invencivel = 0.0
	p.take_damage(1.0e6)
	check(run.estado == run.Estado.MORTO and p.esta_morto(), "morte do jogador")
	await _esperar(func(): return run.menus.tela == run.menus.Tela.FIM, 5.0)
	check(run.menus.tela == run.menus.Tela.FIM, "tela de game over aparece")
	run.menus.jogar.emit()
	check(run.estado == run.Estado.LUTA and p.hp == p.stats["hp_max"], "reinicia com vida cheia")

	# Volta ao título: corrida pronta mas parada.
	run.menus.ao_titulo.emit()
	check(run.estado == run.Estado.MENU and paused and run.menus.tela == run.menus.Tela.TITULO, "volta ao título")
	paused = false
	run.queue_free()

func _testar_rotas() -> void:
	for r in Csv.rows("res://data2d/rota.csv"):
		var sala = RoomScript.new()
		check(sala.carregar(r["room"]), "rota %s: sala carrega" % r["id"])
		check(r["tipo"] in ["elite", "descanso"] and int(r["etapa"]) > 1 and int(r["etapa"]) < Csv.rows("res://data2d/run.csv").size(), "rota %s: tipo e etapa válidos" % r["id"])
		sala.free()
	var run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	var p = run.player
	p.god_mode = true
	check(run.caminhos_da_etapa(0).size() == 1 and run.caminhos_da_etapa(3).size() == 1, "sala 1 e chefe não têm bifurcação")
	# etapa 2: combate ou elite
	run.matar_todos()
	await _esperar(func(): return run._timer <= 0.0 and run.estado == run.Estado.ESCOLHA, 5.0)
	run.ui.escolher(0)
	p.global_position = run.room._centro(12, 3)
	p.auto_move = Vector2.UP
	await _esperar(func(): return run.estado == run.Estado.ROTA, 4.0)
	p.auto_move = Vector2.ZERO
	check(run.opcoes_rota.size() == 2 and run.opcoes_rota[1]["tipo"] == "elite", "etapa 2 oferece combate ou elite")
	run.escolher_rota(run.opcoes_rota[1])
	await _esperar(func(): return run.estado == run.Estado.LUTA, 4.0)
	check(run.no_atual["tipo"] == "elite" and run.vivos == 7 and run.hud.sala == 2, "elite: sala com 7 inimigos")
	var antes: int = run.ganhos["fragmentos"]
	run.matar_todos()
	await _esperar(func(): return run.estado == run.Estado.ESCOLHA, 5.0)
	check(run.ganhos["fragmentos"] - antes >= int(run.config["room_clear_fragments"] + run.config["elite_fragments"]), "elite paga fragmentos extras")
	check(run.ui._ids.size() == int(run.config["upgrade_cards"] + run.config["elite_extra_cards"]), "elite oferece carta extra")
	run.ui.escolher(0)
	# etapa 3: combate ou descanso
	p.hp = 10.0
	p.global_position = run.room._centro(12, 3)
	p.auto_move = Vector2.UP
	await _esperar(func(): return run.estado == run.Estado.ROTA, 4.0)
	p.auto_move = Vector2.ZERO
	check(run.opcoes_rota.size() == 2 and run.opcoes_rota[1]["tipo"] == "descanso", "etapa 3 oferece combate ou descanso")
	run.escolher_rota(run.opcoes_rota[1])
	await _esperar(func(): return run.estado == run.Estado.LIMPA and run.no_atual["tipo"] == "descanso", 4.0)
	check(run.vivos == 0 and run.no_atual["tipo"] == "descanso", "descanso não tem inimigos")
	await _esperar(func(): return run._timer <= 0.0, 3.0)
	await physics_frame
	await physics_frame
	check(run.estado == run.Estado.LIMPA and not run.ui.aberta and p.hp > 10.0 and p.hp <= p.stats["hp_max"], "descanso cura e abre a porta sem cartas")
	p.global_position = run.room._centro(12, 3)
	p.auto_move = Vector2.UP
	await _esperar(func(): return run.estado == run.Estado.LUTA and run.indice == 3, 4.0)
	p.auto_move = Vector2.ZERO
	check(run.indice == 3 and run.estado == run.Estado.LUTA, "do descanso direto ao chefe")
	run.queue_free()

func _testar_meta() -> void:
	MetaScript.caminho = "user://save_teste_2d.json"
	DirAccess.remove_absolute(MetaScript.caminho)
	var m = MetaScript.new()
	check(not m.carregar() and m.fragmentos == 0, "sem save: começa zerado")
	check(not m.liberada("multishot") and m.liberada("power"), "multishot nasce bloqueado, power liberado")
	for id in m.defs:
		check(Csv.t("meta.%s.name" % id) != "meta.%s.name" % id, "texto de %s" % id)
	for e in m.drops:
		check(Csv.t("material." + m.drops[e]["material"]) != "material." + m.drops[e]["material"], "texto do material de %s" % e)
	check(not m.comprar("unlock_multishot"), "sem fragmentos não compra")
	m.creditar({"fragmentos": 200, "materiais": {"pedra_cinza": 2}})
	check(m.comprar("unlock_multishot") and m.liberada("multishot") and m.fragmentos == 200 - m.defs["unlock_multishot"]["custo"], "compra desbloqueia e gasta")
	check(not m.comprar("unlock_multishot"), "habilidade só compra uma vez")
	m.comprar("meta_vida")
	var base := {"hp_max": 100.0, "arrow_damage": 12.0}
	check(is_equal_approx(m.aplicar(base)["hp_max"], 115.0), "melhoria soma vida máxima")

	# Round-trip do save: a morte e o fechamento do jogo não perdem nada.
	var m2 = MetaScript.new()
	check(m2.carregar() and m2.fragmentos == m.fragmentos and m2.materiais["pedra_cinza"] == 2 and m2.nivel("meta_vida") == 1, "save volta idêntico do disco")
	var f := FileAccess.open(MetaScript.caminho, FileAccess.WRITE)
	f.store_string("{lixo")
	f.close()
	check(not MetaScript.new().carregar(), "save corrompido é ignorado sem travar")

	# Upgrades da corrida respeitam desbloqueios e bônus permanentes.
	var up = preload("res://scripts2d/upgrades_2d.gd").new()
	up.meta = m
	check("multishot" in up.disponiveis() and not ("pierce" in up.disponiveis()), "pool só oferece habilidades liberadas")

	# Integração: a corrida rende fragmentos e materiais, que sobrevivem à morte e ao novo carregamento.
	DirAccess.remove_absolute(MetaScript.caminho)
	var run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	run.player.god_mode = true
	run.matar_todos()
	await _esperar(func(): return run.estado == run.Estado.LIMPA, 5.0)
	check(run.ganhos["fragmentos"] > 0 and not run.ganhos["materiais"].is_empty(), "inimigos mortos dropam fragmentos e materiais")
	run.player.god_mode = false
	run.player.invencivel = 0.0
	run.player.take_damage(1.0e6)
	await _esperar(func(): return run.menus.tela == run.menus.Tela.FIM, 5.0)
	var ganho: int = run.meta.fragmentos
	check(ganho > 0 and run.ganhos["fragmentos"] == 0, "morte credita os ganhos ao saldo")
	check(MetaScript.new().carregar(), "save existe em disco após a corrida")
	var depois = MetaScript.new()
	depois.carregar()
	check(depois.fragmentos == ganho, "fragmentos persistem entre sessões")
	run.menus.ao_titulo.emit()
	run.menus.mostrar_meta()
	check(run.menus.tela == run.menus.Tela.META, "tela de melhorias abre")
	paused = false
	run.queue_free()
	DirAccess.remove_absolute(MetaScript.caminho)

func _testar_forja() -> void:
	const BASE := {"hp_max": 100.0, "speed": 100.0, "arrow_damage": 10.0, "dodge_cooldown": 1.0, "shoot_cooldown": 0.4}
	MetaScript.caminho = "user://save_teste_forja_2d.json"
	DirAccess.remove_absolute(MetaScript.caminho)
	var m = MetaScript.new()
	m.carregar()
	check(m.receitas.size() >= 6, "receitas.csv carrega")
	for id in m.receitas:
		check(Csv.t("recipe.%s.name" % id) != "recipe.%s.name" % id, "texto da receita %s" % id)
		for mat in m.receitas[id]["custo"]:
			check(Csv.t("material." + mat) != "material." + mat, "material %s de %s existe" % [mat, id])
	check(not m.criar("amuleto_osso"), "sem materiais não cria")
	m.creditar({"fragmentos": 200, "materiais": {"osso_antigo": 10, "pedra_cinza": 1, "essencia_etera": 4}})
	check(m.criar("amuleto_osso") and m.amuletos.has("amuleto_osso") and m.equipado == "amuleto_osso", "cria e equipa o primeiro amuleto")
	check(m.materiais["osso_antigo"] == 7 and m.materiais["pedra_cinza"] == 0 and m.fragmentos == 170, "gasta materiais e fragmentos")
	check(not m.criar("amuleto_osso"), "amuleto só se cria uma vez")
	check(is_equal_approx(m.aplicar(BASE)["arrow_damage"], 10.5), "amuleto equipado soma o bônus")
	check(m.criar("amuleto_essencia") and m.equipado == "amuleto_osso", "segundo amuleto não troca o slot sozinho")
	check(m.equipar("amuleto_essencia") and m.equipado == "amuleto_essencia", "equipar troca o slot")
	check(m.criar("tonico_vida") and m.estoque["tonico_vida"] == 1, "consumível vai ao estoque")
	check(is_equal_approx(m.aplicar(BASE)["hp_max"], 100.0), "consumível guardado ainda não vale")
	var m2 = MetaScript.new()
	check(m2.carregar() and m2.equipado == "amuleto_essencia" and m2.amuletos.has("amuleto_osso") and m2.estoque["tonico_vida"] == 1, "forja volta idêntica do disco")
	m2.preparar_corrida()
	check(is_equal_approx(m2.aplicar(BASE)["hp_max"], 125.0) and m2.estoque["tonico_vida"] == 0, "partir gasta o consumível e aplica o bônus")
	m2.preparar_corrida()
	check(is_equal_approx(m2.aplicar(BASE)["hp_max"], 100.0), "sem estoque, a próxima corrida não tem o bônus")
	# Balanceamento: uma corrida completa rende ~15 materiais; a 1ª receita sai em até uma corrida.
	var total := 0
	for e in ["hollow_sentinel", "skeleton_soldier", "skeleton_soldier", "skeleton_soldier", "wandering_ghost", "wandering_ghost", "crypt_bat", "crypt_bat", "chain_wraith", "chain_wraith", "ghost_archer", "ghost_archer", "skeleton_soldier"]:
		total += m.drop_de(e)["material_qtd"]
	check(total >= 12, "corrida até a sala 3 rende ao menos 12 materiais (%d)" % total)
	var custo1 := 0
	for q in m.receitas["amuleto_osso"]["custo"].values():
		custo1 += q
	check(custo1 <= 4, "primeira receita custa até 4 materiais")
	var run = RunScene.instantiate()
	run.com_menu = true
	root.add_child(run)
	await physics_frame
	check(run.menus.tela == run.menus.Tela.TITULO, "título abre como hub")
	run.menus.mostrar_forja()
	check(run.menus.tela == run.menus.Tela.FORJA, "forja abre pelo hub")
	paused = false
	run.queue_free()
	DirAccess.remove_absolute(MetaScript.caminho)

func _testar_opcoes_steam_tutorial() -> void:
	var OpcoesScript = preload("res://scripts2d/opcoes_2d.gd")
	var SteamScript = preload("res://scripts2d/steam_2d.gd")
	OpcoesScript.caminho = "user://teste_opcoes.json"
	SteamScript.caminho = "user://teste_steam.json"
	DirAccess.remove_absolute(OpcoesScript.caminho)
	DirAccess.remove_absolute(SteamScript.caminho)
	var o = OpcoesScript.new()
	check(not o.carregar() and is_equal_approx(o.vol["musica"], 0.8) and not o.tutorial_visto, "opcoes: sem arquivo usa os padroes")
	o.ciclar_volume("master")
	check(is_equal_approx(o.vol["master"], 0.0), "opcoes: volume 100% volta a 0")
	o.set_volume("efeitos", 0.5)
	check(AudioServer.get_bus_index("Musica") >= 0 and AudioServer.get_bus_index("Efeitos") >= 0, "opcoes: barramentos de musica e efeitos")
	check(AudioServer.is_bus_mute(AudioServer.get_bus_index("Master")) and absf(AudioServer.get_bus_volume_db(AudioServer.get_bus_index("Efeitos")) - linear_to_db(0.5)) < 0.1, "opcoes: volume chega ao AudioServer")
	o.set_volume("master", 1.0)
	var antes: int = o.tecla("dodge")
	check(antes == KEY_SPACE, "opcoes: esquiva comeca no Espaco")
	check(o.remapear("dodge", KEY_SHIFT) and o.tecla("dodge") == KEY_SHIFT, "opcoes: remapear esquiva")
	var ev_ok := false
	for ev in InputMap.action_get_events("dodge"):
		if ev is InputEventKey and ev.physical_keycode == KEY_SHIFT:
			ev_ok = true
	check(ev_ok, "opcoes: InputMap recebe a nova tecla")
	var joy := false
	for ev in InputMap.action_get_events("dodge"):
		joy = joy or ev is InputEventJoypadButton
	check(joy, "opcoes: remapear preserva o controle")
	check(not o.remapear("dodge", KEY_ESCAPE), "opcoes: Esc e reservado")
	check(o.remapear("move_up", KEY_SHIFT) and o.tecla("dodge") == KEY_W and o.tecla("move_up") == KEY_SHIFT, "opcoes: tecla repetida troca de lugar")
	o.set_tela_cheia(true)
	o.tutorial_visto = true
	check(o.salvar(), "opcoes: salva em disco")
	o.restaurar_padroes()
	check(o.tecla("dodge") == KEY_SPACE and o.tecla("move_up") == KEY_W and o.eh_padrao("dodge"), "opcoes: restaurar teclas")
	var o2 = OpcoesScript.new()
	check(o2.carregar() and o2.tecla("dodge") == KEY_W and o2.tecla("move_up") == KEY_SHIFT and o2.tela_cheia and o2.tutorial_visto, "opcoes: volta identica do disco")
	o2.set_tela_cheia(false)
	o2.restaurar_teclas()
	DirAccess.remove_absolute(OpcoesScript.caminho)
	var corrompido := FileAccess.open(OpcoesScript.caminho, FileAccess.WRITE)
	corrompido.store_string("{ isto nao e json")
	corrompido.close()
	check(not OpcoesScript.new().carregar(), "opcoes: arquivo corrompido nao quebra")
	DirAccess.remove_absolute(OpcoesScript.caminho)
	for a in Csv.rows("res://data2d/teclas.csv"):
		check(Csv.t(a["loc"]) != a["loc"], "texto da acao %s" % a["acao"])
	# Steam: sem plugin o jogo segue, conquistas ficam no registro local e voltam depois do reinicio.
	var st = SteamScript.new()
	check(not st.iniciar() and not st.disponivel, "steam: sem plugin fica indisponivel sem quebrar")
	st.tick()
	check(not st.nuvem_ativa(), "steam: nuvem inativa sem Steam")
	check(st.evento("evento_que_nao_existe").is_empty(), "steam: evento desconhecido nao desbloqueia")
	check(st.evento("corrida_fim") == ["primeira_corrida"] and st.evento("corrida_fim").is_empty(), "steam: conquista desbloqueia uma vez")
	check(SteamScript.new().desbloqueadas.has("primeira_corrida"), "steam: registro local sobrevive ao reinicio")
	for c in st.conquistas:
		check(Csv.t(c["loc"]) != c["loc"] and c["steam_id"] != "", "conquista %s tem texto e id da Steam" % c["id"])
	# Menus e tutorial.
	MetaScript.caminho = "user://teste_opcoes_meta.json"
	var run = RunScene.instantiate()
	run.com_menu = true
	root.add_child(run)
	await physics_frame
	var m = run.menus
	check(m.opcoes != null and m.steam != null, "menus: opcoes e steam ligadas")
	m.mostrar_opcoes(m.mostrar_titulo)
	check(m.tela == m.Tela.OPCOES, "menus: opcoes abrem")
	m.mostrar_teclas()
	check(m.tela == m.Tela.TECLAS, "menus: tela de teclas abre")
	m.mostrar_opcoes()
	m._fechar_opcoes()
	check(m.tela == m.Tela.TITULO, "menus: voltar das opcoes reabre o titulo")
	m.opcoes.tutorial_visto = false
	m.jogar.emit()
	check(m.tutorial.ativo and m.tutorial.indice == 0, "tutorial: abre na primeira corrida")
	check(m.tutorial._rotulo.text.contains(m.opcoes.nome_tecla("move_up")), "tutorial: mostra as teclas atuais")
	Input.action_press("move_up")
	await process_frame
	await process_frame
	Input.action_release("move_up")
	check(m.tutorial.indice >= 1, "tutorial: avanca ao mover")
	m.tutorial._ir(m.tutorial.passos.size())
	check(not m.tutorial.ativo and m.opcoes.tutorial_visto, "tutorial: termina e nao volta")
	m.jogar.emit()
	check(not m.tutorial.ativo, "tutorial: nao repete depois de visto")
	paused = false
	run.queue_free()
	DirAccess.remove_absolute(OpcoesScript.caminho)
	DirAccess.remove_absolute(SteamScript.caminho)
	DirAccess.remove_absolute(MetaScript.caminho)

## Status de inimigo (aplicar_status): marca, lentidão, atordoamento, veneno e queimadura.
func _testar_status() -> void:
	var mundo := Node2D.new()
	root.add_child(mundo)
	var p = load("res://scripts2d/player_2d.gd").new()
	p.god_mode = true
	mundo.add_child(p)
	var e = load("res://scripts2d/enemy_2d.gd").new()
	mundo.add_child(e)
	e.setup("hollow_sentinel", p, p.global_position + Vector2(600, 0))
	e.aplicar_status("marca", 2.0, 0.5)
	var hp0: float = e.hp
	e.take_damage(10.0)
	check(is_equal_approx(hp0 - e.hp, 15.0), "marca: +50% de dano recebido")
	e.aplicar_status("lentidao", 0.3, 0.6)
	check(is_equal_approx(e.vel_mult, 0.4), "lentidão reduz a velocidade")
	e.aplicar_status("atordoamento", 0.3, 0.0)
	check(e.atordoado > 0.0, "atordoamento para o inimigo")
	var hp1: float = e.hp
	e.aplicar_status("veneno", 1.5, 10.0)
	await _esperar(func(): return e.hp < hp1 - 5.0, 3.0)
	check(e.hp < hp1 - 5.0, "veneno causa dano ao longo do tempo")
	await _esperar(func(): return not e.tem_status("lentidao") and not e.tem_status("atordoamento"), 2.0)
	check(is_equal_approx(e.vel_mult, 1.0) and e.atordoado == 0.0, "status expiram e a velocidade volta")
	mundo.queue_free()
	await physics_frame
