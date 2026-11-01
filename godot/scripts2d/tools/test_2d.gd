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
const AutocastTestes = preload("res://scripts2d/tools/test_autocast_2d.gd")
const HordaTestes = preload("res://scripts2d/tools/test_horda_2d.gd")

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
	preload("res://scripts2d/run_2d.gd").modo_etapas = true   # fluxo antigo de etapas; o modo horda tem o teste dele
	preload("res://scripts2d/habilidades_2d.gd").caminho = "user://teste_habilidades_geral_2d.json"
	DirAccess.remove_absolute("user://teste_habilidades_geral_2d.json")
	preload("res://scripts2d/passivos_2d.gd").caminho = "user://passivos_teste_geral_2d.json"
	DirAccess.remove_absolute("user://passivos_teste_geral_2d.json")
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
	await _testar_habilidades()
	await _testar_passivos()
	await _testar_forja()
	await _testar_opcoes_steam_tutorial()
	await _testar_abertura()
	await _testar_status()
	await _testar_mago()
	await GuerreiroTestes.new(self, check).rodar()
	await _testar_habilidades_arqueiro()
	await _testar_fisica_habilidades()
	await AutocastTestes.new(self, check).rodar()
	await HordaTestes.new(self, check).rodar()

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
	check(up.niveis.is_empty(), "corrida nova começa sem níveis")
	# As cartas vêm do core ao limpar a sala; só as oferecidas podem ser escolhidas.
	var n: Object = up.nucleo
	for i in 3:
		var morto := false
		for e in n.corrida_estado()["node"]["enemies"]:
			for _k in int(e["count"]):
				morto = n.corrida_inimigo_morto(e["id"])["sala_limpa"]
		check(morto, "sala %d limpa pelo core" % (i + 1))
		var oferta: Array = up.oferta()
		check(oferta.size() == 3 and oferta[0] != oferta[1] and oferta[1] != oferta[2] and oferta[0] != oferta[2], "sorteio de 3 cartas distintas")
		var id: String = oferta[0]
		var st: String = up.defs[id]["stat"]
		var antes: float = p.stats[st]
		var fora := ""
		for k in up.defs:
			if not oferta.has(k):
				fora = k
		check(not up.escolher(fora, p), "carta fora da oferta é recusada")
		check(up.escolher(id, p), "escolhe %s" % id)
		check(not is_equal_approx(p.stats[st], antes), "%s muda %s" % [id, st])
		if st == "hp_max":
			check(is_equal_approx(p.hp, p.stats["hp_max"]), "vigor cura o ganho")
		if n.corrida_porta() == 2:
			n.corrida_escolher_caminho(0)
		check(n.corrida_fase() == 1, "porta leva à próxima sala (luta)")
	n.corrida_iniciar(7, base)
	up.restaurar(p)
	check(p.stats == base and up.niveis.is_empty(), "restaurar volta a base")
	p.free()

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
		var aberta: bool = sala.aberta()
		if aberta:   # fase aberta: mapa grande, sem porta, com portal X e chão livre para as ondas
			check(sala.colunas >= 80 and sala.linhas >= 45, "%s: fase aberta grande (%dx%d)" % [r["room"], sala.colunas, sala.linhas])
			check(sala.posicao_portal != Vector2.ZERO and sala.posicao_chefe != Vector2.ZERO, "%s tem lugar do chefe G e portal X" % r["room"])
			check(sala.celulas_livres.size() > sala.colunas * sala.linhas * 0.35, "%s: ao menos 35%% do mapa livre para nascer" % r["room"])
			check(sala.colunas * sala.linhas >= 24 * 13 * 25 * 2, "%s: área de ao menos 50 salas antigas" % r["room"])
		else:
			check(sala.colunas == 24 and sala.linhas == 13, "%s tem 24x13" % r["room"])
			check(sala.celulas_porta.size() > 0, "%s tem porta" % r["room"])
		check(sala.spawn_jogador != Vector2.ZERO and sala.spawns_inimigos.size() > 0, "%s tem P e E" % r["room"])
		check(sala.props.size() > 0, "%s tem props" % r["room"])
		var ok_props := true
		for pr in sala.props:
			var c := Vector2i(int(pr["pos"].x / sala.tile), int(pr["pos"].y / sala.tile))
			ok_props = ok_props and sala._props_def.has(pr["id"]) and sala._props_arte.has(pr["id"])
			ok_props = ok_props and FileAccess.file_exists(sala._props_arte[pr["id"]]["arquivo"])
			# a coluna da porta (11 a 13) fica livre nas linhas 2 a 4
			var solido: bool = float(sala._props_def[pr["id"]]["solido_l"]) > 0.0
			ok_props = ok_props and (aberta or not (solido and c.x >= 11 and c.x <= 13 and c.y >= 2 and c.y <= 4))
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
	p.autocast = false   # o teste é do telégrafo do inimigo: o jogador não pode matá-lo atirando sozinho (e vazar o mundo)
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
	if not niveis.is_empty():
		# Níveis de upgrade direto no estado do core (restaurar o estado é o caminho de teste; a sorte das cartas não conta).
		var est: Dictionary = JSON.parse_string(up.nucleo.estado_texto())
		for id in niveis:
			est["run"]["levels"][id] = niveis[id]
		up.nucleo.estado_restaurar(JSON.stringify(est))
		p.stats = up.nucleo.corrida_stats()
		p.hp = p.stats["hp_max"]
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

	# Fase aberta: a câmera segue o jogador e para na borda do mapa.
	if run.room.aberta():
		check(run.room.colunas * run.room.tile > run.get_viewport_rect().size.x * 2.0, "mapa maior que duas telas")
		run.camera.position_smoothing_enabled = false
		for alvo_cam in [run.room._centro(45, 25), run.room._centro(3, 4)]:
			p.global_position = alvo_cam
			await physics_frame
			await physics_frame
			await process_frame
			alvo_cam = p.global_position
			var meia: Vector2 = run.get_viewport_rect().size / run.camera.zoom / 2.0
			var esperado := Vector2(clampf(alvo_cam.x, meia.x, run.room.tamanho_px().x - meia.x), clampf(alvo_cam.y, meia.y, run.room.tamanho_px().y - meia.y))
			check(run.camera.get_screen_center_position().distance_to(esperado) < 8.0, "câmera segue o jogador e para na borda do mapa (%s)" % str(alvo_cam))
		p.global_position = run.room.spawn_jogador
		check(run.room.bordas_jogaveis().has_point(run.room.empurrar_para_dentro(Vector2(-500, -500))), "ponto fora do mapa é empurrado para dentro")
		run._ajustar_camera()
	# Percorre todas as etapas: mata tudo, espera a saída (porta antiga ou onda seguinte e portal no fim).
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
			check(run.estado in [run.Estado.LIMPA, run.Estado.PROXIMA] and run.upgrades.niveis.size() > 0, "carta escolhida e saída aberta")
		else:
			check(run.estado == run.Estado.LIMPA, "sala do chefe não oferece cartas")
			check(run.posicao_saida() != Vector2.ZERO, "portal aberto depois do chefe")
		_ir_para_saida(run, p)
		await _esperar(func(): return run.estado != run.Estado.LIMPA and run.estado != run.Estado.PROXIMA, 4.0)
		p.auto_move = Vector2.ZERO
		if i < run.salas.size() - 1:
			if run.caminhos_da_etapa(i + 1).size() > 1:
				await _esperar(func(): return run.estado == run.Estado.ROTA, 4.0)
				check(run.estado == run.Estado.ROTA and paused and run.menus.tela == run.menus.Tela.ROTA, "etapa %d abre a escolha de caminho" % (i + 2))
				run.escolher_rota(run.opcoes_rota[0])
				check(not paused, "escolher o caminho despausa")
			await _esperar(func(): return run.estado == run.Estado.LUTA, 4.0)
			check(run.indice == i + 1 and run.estado == run.Estado.LUTA, "segue para a etapa %d" % (i + 2))
			if run.room.aberta():
				var v: Rect2 = run.vista()
				var fora := true
				for e in get_nodes_in_group("hurtable"):
					fora = fora and not v.has_point(e.global_position)
				check(fora, "onda %d nasce fora da vista" % (i + 2))
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

## Leva o jogador à saída aberta (porta da sala antiga ou portal da fase aberta). Sem saída (fase aberta no meio), a onda seguinte vem sozinha.
func _ir_para_saida(run, p) -> void:
	var s: Vector2 = run.posicao_saida()
	if s != Vector2.ZERO:
		p.global_position = s
		p.auto_move = Vector2.UP

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
	_ir_para_saida(run, p)
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
	_ir_para_saida(run, p)
	await _esperar(func(): return run.estado == run.Estado.ROTA, 4.0)
	p.auto_move = Vector2.ZERO
	check(run.opcoes_rota.size() == 2 and run.opcoes_rota[1]["tipo"] == "descanso", "etapa 3 oferece combate ou descanso")
	run.escolher_rota(run.opcoes_rota[1])
	await _esperar(func(): return run.estado == run.Estado.LIMPA and run.no_atual["tipo"] == "descanso", 4.0)
	check(run.vivos == 0 and run.no_atual["tipo"] == "descanso", "descanso não tem inimigos")
	await _esperar(func(): return run._timer <= 0.0, 3.0)
	await physics_frame
	await physics_frame
	check(run.estado in [run.Estado.LIMPA, run.Estado.PROXIMA, run.Estado.LUTA] and not run.ui.aberta and p.hp > 10.0 and p.hp <= p.stats["hp_max"], "descanso cura e segue sem cartas")
	_ir_para_saida(run, p)
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
	for r in Csv.rows("res://data2d/drops.csv"):
		check(Csv.t("material." + r["material"]) != "material." + r["material"], "texto do material de %s" % r["inimigo"])
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
		total += m.drop_de(e)["material_qty"]
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

func _testar_habilidades() -> void:
	var Hab = preload("res://scripts2d/habilidades_2d.gd")
	Hab.caminho = "user://save_teste_hab_2d.json"
	DirAccess.remove_absolute(Hab.caminho)
	var Efeitos = preload("res://scripts2d/tools/efeitos_teste_2d.gd")
	var csv := "res://data2d/testes/habilidades_teste.csv"
	var fx := "res://scripts2d/tools/efeitos_teste_2d.gd"
	var cls: Dictionary = Hab.classes()
	for c in ["arqueiro", "guerreiro", "mago"]:
		check(cls.has(c), "classes_2d.csv tem " + c)
		check(Csv.t("class." + c) != "class." + c, "texto da classe " + c)
	var h = Hab.new()
	h.carregar_classe("teste", csv, fx)
	check(h.ordem.size() == 4 and h.ramos() == ["fogo", "vida"], "carrega 4 skills em 2 ramos")
	check(not h.aprender("t_golpe"), "sem pontos não aprende")
	h.ganhar_pontos(6)
	check(not h.aprender("t_nova"), "filho exige o pai aprendido")
	check(h.aprender("t_golpe") and h.nivel("t_golpe") == 1 and h.pontos == 5, "aprende a raiz e gasta 1 ponto")
	check(h.slots[0] == "t_golpe", "ativa nova entra no primeiro slot livre")
	check(h.aprender("t_nova") and h.slots[1] == "t_nova" and h.pontos == 3, "filho aprende depois do pai")
	check(h.aprender("t_golpe") and h.aprender("t_golpe") and not h.aprender("t_golpe"), "respeita nivel_max")
	check(is_equal_approx(h.def_nivel("t_golpe")["dano"], 40.0), "escala por nível: 20*(1+0.5*2)=40")

	# Uso: mana, recarga e efeito.
	var j := Node2D.new()
	j.set_script(preload("res://scripts2d/tools/jogador_falso_2d.gd"))
	root.add_child(j)
	j.mana = 100.0
	check(h.usar(0, j, Vector2(3, 0)) and Efeitos.ultimo["efeito"] == "golpe" and Efeitos.ultimo["mira"] == Vector2.RIGHT, "usa o slot e normaliza a mira")
	check(is_equal_approx(j.mana, 90.0), "cobra o custo de mana")
	check(not h.usar(0, j, Vector2.RIGHT) and h.recarga_slot(0) > 0.99, "em recarga não dispara de novo")
	h.tick(2.0)
	check(h.recarga_slot(0) == 0.0 and h.usar(0, j, Vector2.RIGHT), "recarga acaba e libera")
	j.mana = 5.0
	check(not h.usar(1, j, Vector2.RIGHT), "sem mana suficiente não dispara")
	check(not h.usar(3, j, Vector2.RIGHT), "slot vazio não dispara")

	# Passivas e equipar.
	h.ganhar_pontos(4)
	h.aprender("t_vigor")
	h.aprender("t_passo")
	var s: Dictionary = h.aplicar_passivas({"hp_max": 100.0, "speed": 200.0})
	check(is_equal_approx(s["hp_max"], 120.0) and is_equal_approx(s["speed"], 210.0), "passivas somam sobre a base")
	check(h.equipar(3, "t_golpe") and h.slots[3] == "t_golpe" and h.slots[0] == "", "equipar move a skill de slot")
	check(not h.equipar(0, "t_vigor"), "passiva não vai a slot")

	# Save e respec.
	var h2 = Hab.new()
	h2.carregar_classe("teste", csv, fx)
	check(h2.nivel("t_golpe") == 3 and h2.slots[3] == "t_golpe" and h2.pontos == h.pontos, "níveis, slots e pontos voltam do save")
	check(FileAccess.file_exists(Hab.caminho) and JSON.parse_string(FileAccess.get_file_as_string(Hab.caminho)).get("habilidades", {}).has("teste"), "o save do core guarda a árvore")
	var gasto := 0
	for id in h.niveis:
		gasto += int(h.defs[id]["pontos"]) * h.niveis[id]
	var antes: int = h.pontos
	h.redistribuir()
	check(h.pontos == antes + gasto and h.niveis.is_empty() and h.slots == ["", "", "", ""], "redistribuir devolve todos os pontos")

	# Árvores reais das classes que já entregaram dados: pais existem, textos existem, ativas têm efeito.
	for c in cls:
		var hc = Hab.new()
		hc.carregar_classe(c)
		for id in hc.ordem:
			var d: Dictionary = hc.defs[id]
			check(d["pai"] == "" or hc.defs.has(d["pai"]), "%s: pai de %s existe" % [c, id])
			check(Csv.t("skill.%s.name" % id) != "skill.%s.name" % id, "%s: texto de %s" % [c, id])
			check(d["tipo"] in ["ativa", "passiva"] and (d["tipo"] == "passiva" or d["efeito"] != ""), "%s: %s tem tipo e efeito válidos" % [c, id])
		if not hc.ordem.is_empty():
			check(hc._efeitos != null, "%s: tem script de efeitos" % c)

	# Integração com o jogador e a corrida: mana, classe e pontos por sala.
	DirAccess.remove_absolute(Hab.caminho)
	var run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	var p = run.player
	check(p.classe == "arqueiro" and p.stats["mana_max"] == 80.0 and p.mana == 80.0, "arqueiro começa com mana cheia")
	run.player.god_mode = true
	var pts: int = p.habilidades.pontos
	run.matar_todos()
	await _esperar(func(): return run.estado == run.Estado.LIMPA, 5.0)
	check(p.habilidades.pontos == pts + 1, "limpar sala rende 1 ponto de habilidade")
	p.gastar_mana(30.0)
	await create_timer(0.5).timeout
	check(p.mana > 50.0, "mana regenera com o tempo")
	run.queue_free()
	j.queue_free()
	DirAccess.remove_absolute(Hab.caminho)
## Árvore de passivos (passivos_2d.gd, doc 33): resolução (add/inc/mais/set), tetos, grafo, keystone, save e os dados
## reais do arqueiro; a flecha lê vel, perfura e proj_extra do def resolvido.
func _testar_passivos() -> void:
	var Hab = preload("res://scripts2d/habilidades_2d.gd")
	var Pas = preload("res://scripts2d/passivos_2d.gd")
	Hab.caminho = "user://save_teste_pas_hab_2d.json"
	Pas.caminho = "user://save_teste_pas_2d.json"
	DirAccess.remove_absolute(Hab.caminho)
	DirAccess.remove_absolute(Pas.caminho)
	var csv := "res://data2d/testes/habilidades_teste.csv"
	var fx := "res://scripts2d/tools/efeitos_teste_2d.gd"
	var csv_pas := "res://data2d/testes/passivas_teste.csv"
	var csv_tags := "res://data2d/testes/habilidades_tags_teste.csv"
	var h = Hab.new()
	h.carregar_classe("teste", csv, fx, csv_pas, csv_tags)
	var p = h.passivos
	check(p.ordem.size() == 12 and p.ativo("raiz") and p.pontos == 0, "carrega 12 nós e a raiz nasce ativa")
	check(p.validar(h.ordem).is_empty(), "fixture válida: %s" % str(p.validar(h.ordem)))
	check(h.tags_de("t_nova") == ["area", "multi", "fogo", "ativa"], "tags do CSV mais ramo e tipo: %s" % str(h.tags_de("t_nova")))
	check(not p.pode_ativar("a1") and not p.ativar("a1"), "sem pontos não ativa")
	p.ganhar_pontos(20)
	check(not p.pode_ativar("a2"), "nó sem vizinho ativo fica bloqueado")
	check(p.ativar("a1") and p.ativar("a2") and p.ativar("a3") and p.pontos == 16, "ativa a corrente e gasta 1+1+2")
	var d: Dictionary = p.resolver("t_golpe", {"dano": 20.0}, ["projetil"])
	check(is_equal_approx(d["dano"], 39.0), "dano = (20 + 0) × (1 + 0,1 + 0,2) × 1,5 = 39 (%s)" % str(d["dano"]))
	check(d["perfura"] == 1.0 and d["vel"] == 1.0 and d["proj_extra"] == 0.0 and d["forma"] == "", "campos padrão presentes: perfura 1")
	check(is_equal_approx(p.resolver("t_nova", {"dano": 40.0}, ["area", "multi"])["dano"], 40.0), "modificador de outra tag não vaza")
	p.ativar("b1")
	check(is_equal_approx(p.resolver("t_nova", {"raio": 120.0}, ["area"])["raio"], 300.0), "aumento de área preso ao teto de 150%% (%s)" % str(p.resolver("t_nova", {"raio": 120.0}, ["area"])["raio"]))
	p.ativar("c1")
	check(p.resolver("t_golpe", {"dano": 1.0}, ["projetil"])["proj_extra"] == 6.0, "projéteis em tiro simples viram cópias, presas ao teto 6")
	p.ativar("b2")
	check(p.resolver("t_nova", {"qtd": 2.0}, ["area", "multi"])["qtd"] == 3.0, "projéteis em habilidade multi somam em qtd")
	p.ativar("b3")
	var dn: Dictionary = p.resolver("t_nova", {"qtd": 2.0}, ["area", "multi"])
	check(dn["forma"] == "anel" and dn["qtd"] == 7.0, "set troca a forma e fixa qtd")
	# def do core passa pelos passivos
	h.ganhar_pontos(3)
	h.aprender("t_golpe")
	check(is_equal_approx(h.def_nivel("t_golpe")["dano"], 39.0) and is_equal_approx(h.def_base("t_golpe")["dano"], 20.0), "def_nivel aplica os passivos sobre o def do core")
	# globais, keystone e tetos de recarga
	p.ativar("g1")
	p.ativar("g2")
	var s: Dictionary = h.aplicar_passivas({"hp_max": 100.0, "skill_cd_mult": 1.0})
	check(is_equal_approx(s["hp_max"], 165.0), "global: (100 + 10) × 1,5 = 165 (%s)" % str(s["hp_max"]))
	check(p.ativar("k1") and is_equal_approx(h.aplicar_passivas({"skill_cd_mult": 1.0})["skill_cd_mult"], 0.35), "keystone -90%% de recarga para no piso de 35%%")
	check(not p.pode_ativar("k2"), "segundo keystone bloqueado (teto e exclusão)")
	var previa: Array = p.previa("a1", {"t_golpe": {"dano": 20.0}}, {"t_golpe": ["projetil"]})
	check(previa.is_empty(), "prévia de nó já ativo não muda nada")
	p.redistribuir()
	check(p.pontos == 20 and p.ativos.size() == 1 and p.ativo("raiz"), "redistribuir devolve tudo e deixa a raiz")
	previa = p.previa("a1", {"t_golpe": {"dano": 20.0}}, {"t_golpe": ["projetil"]})
	check(previa.size() == 1 and previa[0]["campo"] == "dano" and is_equal_approx(previa[0]["depois"], 22.0), "prévia antes → depois: 20 → 22")
	p.ativar("a1")
	var h2 = Hab.new()
	h2.carregar_classe("teste", csv, fx, csv_pas, csv_tags)
	check(h2.passivos.ativo("a1") and h2.passivos.pontos == 19, "nós e pontos voltam do save")
	check(h.para_dicionario()["passivos"]["ativos"] == ["a1"], "para_dicionario inclui os passivos")

	# Dados reais do arqueiro: grafo válido, textos, setores, e cada transforma mexe numa forma que o efeito conhece.
	var ha = Hab.new()
	ha.carregar_classe("arqueiro")
	var pa = ha.passivos
	check(pa.ordem.size() >= 60, "arqueiro tem ao menos 60 nós de passivo (%d)" % pa.ordem.size())
	var erros: Array = pa.validar(ha.ordem)
	check(erros.is_empty(), "passivas_arqueiro.csv válida: %s" % str(erros))
	for id in pa.ordem:
		check(Csv.t("passivo.%s.name" % id) != "passivo.%s.name" % id and Csv.t("passivo.%s.desc" % id) != "passivo.%s.desc" % id, "texto do passivo %s" % id)
	for setor in pa.setores():
		check(Csv.t("setor." + setor) != "setor." + setor, "texto do setor " + setor)
	check(pa.contar_tipo("raiz") == 1 and pa.setores().size() == 8, "1 raiz e 8 setores")
	var formas := {"espiral": true, "lanca": true, "anel": true, "bifurcado": true, "errante": true, "brasas": true, "pustulas": true}
	for id in pa.ordem:
		for m in pa.defs[id]["mods"]:
			if m["campo"] == "forma":
				check(formas.has(m["forma"]), "forma conhecida em %s: %s" % [id, m["forma"]])
	var limites := Csv.kv("res://data2d/passivas_limites.csv")
	check(limites.has("qtd_add_max") and limites.has("max_projeteis") and limites.has("keystones_max"), "passivas_limites.csv tem os tetos")
	for id in ha.ordem:
		if ha.eh_ativa(id):
			check(not ha.tags_de(id).is_empty(), "ativa %s tem tags" % id)

	# A flecha do jogador lê o def resolvido: velocidade, perfuração e cópias em leque.
	var run = RunScene.instantiate()
	run.com_menu = false
	root.add_child(run)
	await physics_frame
	var jog = run.player
	var vel_base: float = jog.stats["arrow_speed"]
	var f = jog.lancar_flecha(Vector2.RIGHT, 1.0, 0, 1.0, {"vel": 2.0, "perfura": 3, "proj_extra": 2})
	await physics_frame
	check(is_equal_approx(f.velocity.length(), vel_base * 2.0) and f.pierce == 3, "flecha usa vel e perfura do def")
	check(jog.get_tree().get_nodes_in_group("flecha_jogador").size() == 3, "proj_extra 2 lança 3 flechas em leque")
	var antes_pts: int = jog.habilidades.passivos.pontos
	run._pontos_passivos(false)
	check(jog.habilidades.passivos.pontos == antes_pts + int(run.config["passive_points_wave"]), "onda vencida rende pontos de passivo")
	run.queue_free()
	DirAccess.remove_absolute(Hab.caminho)
	DirAccess.remove_absolute(Pas.caminho)
	Pas.caminho = "user://passivos_teste_geral_2d.json"

## Início do jogo: prólogo de Ilsa e Tico no primeiro Jogar, cartão da classe no título e primeira sala adormecida.
func _testar_abertura() -> void:
	var OpcoesScript = preload("res://scripts2d/opcoes_2d.gd")
	OpcoesScript.caminho = "user://teste_abertura_opcoes.json"
	MetaScript.caminho = "user://teste_abertura_meta.json"
	DirAccess.remove_absolute(OpcoesScript.caminho)
	var falas := Csv.rows("res://data2d/prologo.csv")
	check(falas.size() >= 4, "prologo: falas no csv")
	for f in falas:
		check(Csv.t(f["loc"]) != f["loc"] and Csv.t("npc.%s.name" % f["quem"]) != "npc.%s.name" % f["quem"], "prologo: %s tem texto e nome" % f["loc"])
		check(ResourceLoader.exists("res://art2d/ui/retrato_%s.png" % f["quem"]), "prologo: retrato de %s" % f["quem"])
	var run = RunScene.instantiate()
	run.com_menu = true
	root.add_child(run)
	await physics_frame
	var m = run.menus
	check(m.tela == m.Tela.TITULO and m._arte.visible and m._retrato_classe != null, "titulo: key art e cartao da classe")
	var corridas_antes: int = run.corridas
	m._jogar_do_titulo()
	check(m.prologo.ativo and m.prologo.visible and run.corridas == corridas_antes, "prologo: abre no primeiro Jogar sem comecar a corrida")
	m.prologo.avancar()
	check(m.prologo.indice == 0 and m.prologo._texto.visible_characters == -1, "prologo: primeiro clique completa a fala")
	for i in falas.size():
		m.prologo.avancar()
		m.prologo.avancar()
	check(not m.prologo.ativo and m.opcoes.prologo_visto and run.corridas == corridas_antes + 1, "prologo: termina e comeca a corrida")
	var o2 = OpcoesScript.new()
	check(o2.carregar() and o2.prologo_visto, "prologo: visto fica salvo")
	m.mostrar_titulo()
	m._jogar_do_titulo()
	check(not m.prologo.ativo and run.corridas == corridas_antes + 2, "prologo: nao repete depois de visto")
	m.mostrar_titulo()
	m.prologo.iniciar()
	m.prologo.pular()
	check(not m.prologo.ativo and m.tela == m.Tela.TITULO and run.corridas == corridas_antes + 2, "prologo: rever pelo titulo e pular volta ao titulo")
	m.fechar()
	paused = false
	await physics_frame   # inimigos das corridas anteriores saem da árvore
	var adormecidos := get_nodes_in_group("inimigos_adormecidos").filter(func(e): return is_instance_valid(e) and not e.is_queued_for_deletion())
	check(run.indice == 0 and adormecidos.size() == run.vivos and run.vivos > 0, "sala 1: inimigos comecam adormecidos")
	var longe := INF
	for e in adormecidos:
		longe = minf(longe, e.global_position.distance_to(run.player.global_position))
	check(longe > Csv.kv("res://data2d/run_settings.csv")["first_room_wake_radius"], "sala 1: jogador nasce fora do alcance dos inimigos")
	run.player.autocast = false   # o tiro automático acordaria a sala; aqui só importa que eles não se mexem sozinhos
	var e0 = adormecidos[0]
	var pos0: Vector2 = e0.global_position
	for i in 60:
		await physics_frame
	check(e0.global_position.distance_to(pos0) < 1.0 and run.player.hp == run.player.stats["hp_max"], "sala 1: adormecidos nao atacam nem andam")
	e0.take_damage(1.0)
	check(adormecidos.all(func(e): return e.raio_despertar == 0.0), "sala 1: ferir um acorda a sala toda")
	run.queue_free()
	await process_frame
	DirAccess.remove_absolute(OpcoesScript.caminho)
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

## Mago: dados de habilidades coerentes e efeitos que de fato ferem, lentificam, queimam e protegem.
func _testar_mago() -> void:
	var Efeitos = preload("res://scripts2d/efeitos_mago_2d.gd")
	var Icones = preload("res://scripts2d/icones_2d.gd")
	var defs := {}
	for r in Csv.rows("res://data2d/habilidades_mago.csv"):
		defs[r["id"]] = r
	var mstats := Csv.kv("res://data2d/mago.csv")
	check(defs.size() >= 15 and defs.size() <= 20, "mago tem 15 a 20 habilidades (%d)" % defs.size())
	var ramos := {}
	for id in defs:
		var d: Dictionary = defs[id]
		ramos[d["ramo"]] = true
		check(Csv.t("skill.%s.name" % id) != "skill.%s.name" % id and Csv.t("skill.%s.desc" % id) != "skill.%s.desc" % id, "%s tem nome e descricao" % id)
		check(Icones.textura(d["icone"]) != null, "%s tem icone" % id)
		check(d["pai"] == "" or (defs.has(d["pai"]) and int(defs[d["pai"]]["tier"]) < int(d["tier"]) and defs[d["pai"]]["ramo"] == d["ramo"]), "%s: pai valido no mesmo ramo" % id)
		check(d["pai"] != "" or d["tier"] == "1", "%s: raiz so no tier 1" % id)
		if d["tipo"] == "passiva":
			check(mstats.has(d["stat"]) and (d["modo"] == "add" or d["modo"] == "mult"), "%s: passiva mexe em stat existente" % id)
		else:
			check(float(d["cd"]) > 0.0 or float(d["custo"]) == 0.0, "%s: tem recarga" % id)
	check(ramos.size() == 3, "3 ramos de habilidade")
	# cena com mago e inimigos
	var mundo := Node2D.new()
	root.add_child(mundo)
	var m = load("res://scripts2d/mago_2d.gd").new()
	mundo.add_child(m)
	m.auto_aim = Vector2.RIGHT
	m.god_mode = true
	await physics_frame
	check(m.mana == mstats["mana_max"] and m.stats["hp_max"] == mstats["hp_max"], "mago comeca com mana e vida do mago.csv")
	check(m.gastar_mana(30.0) and not m.gastar_mana(1000.0) and absf(m.mana - 70.0) < 0.5, "gastar mana")
	var antes: float = m.mana
	await _esperar(func(): return m.mana > antes + 3.0, 2.0)
	check(m.mana > antes + 3.0, "mana regenera")
	var funcionou := {}
	for id in defs:
		var d: Dictionary = defs[id].duplicate()
		if d["tipo"] != "ativa":
			continue
		var def := {}
		for k in ["cd", "custo", "dano", "qtd", "angulo", "raio", "duracao", "alcance", "valor"]:
			def[k] = float(d[k])
		var inimigos := _alvos_mago(mundo, m)
		var hp_antes := 0.0
		for e in inimigos:
			hp_antes += e.hp
		var ok: bool = m.lancar_efeito(d["efeito"], def, 1)
		check(ok, "%s (%s) executa" % [id, d["efeito"]])
		await _esperar(func(): return false, 1.3)   # projétil voa, marca de meteoro cai
		var hp_depois := 0.0
		for e in inimigos:
			if is_instance_valid(e):
				hp_depois += maxf(0.0, e.hp)
		funcionou[d["efeito"]] = hp_depois < hp_antes
		for e in inimigos:
			if is_instance_valid(e):
				e.queue_free()
		await physics_frame
	for ef in ["bola_fogo", "raio_gelo", "sopro_chamas", "meteoro", "nova_fogo", "nova_gelo", "nova_raio", "corrente_raios", "estacas_gelo", "salto_arcano"]:
		check(funcionou.get(ef, false), "efeito %s causa dano" % ef)
	# muralha, nevasca e tempestade são zonas: dano por ticks no ponto mirado (a frente do mago)
	for ef in ["muralha_fogo", "nevasca", "tempestade"]:
		check(funcionou.has(ef), "zona %s executou sem erro" % ef)
	var inimigos := _alvos_mago(mundo, m)
	# status
	var alvo = inimigos[0]
	alvo.hp = alvo.hp_max
	alvo.global_position = m.global_position + Vector2(150, 0)
	m.lancar_efeito("raio_gelo", {"dano": 10.0, "raio": 0.0, "alcance": 900.0, "valor": 600.0}, 1)
	await _esperar(func(): return alvo.tem_status("lentidao"), 1.5)
	check(alvo.tem_status("lentidao"), "raio de gelo lentifica")
	alvo.hp = alvo.hp_max
	m.lancar_efeito("bola_fogo", {"dano": 20.0, "raio": 90.0, "alcance": 900.0, "valor": 640.0}, 1)
	await _esperar(func(): return alvo.tem_status("queimadura"), 1.5)
	check(alvo.tem_status("queimadura"), "bola de fogo queima")
	m.lancar_efeito("nova_gelo", {"dano": 5.0, "raio": 300.0}, 1)
	check(alvo.tem_status("atordoamento"), "nova glacial congela")
	# escudo, surto e salto
	m.god_mode = false
	m.invencivel = 0.0
	m.lancar_efeito("barreira_gelo", {"valor": 40.0, "duracao": 5.0}, 1)
	var hp0: float = m.hp
	m.take_damage(25.0)
	check(m.hp == hp0 and m.escudo == 15.0, "barreira absorve dano")
	m.invencivel = 0.0
	m.take_damage(25.0)
	check(m.hp == hp0 - 10.0 and m.escudo == 0.0, "dano acima do escudo passa")
	m.lancar_efeito("surto_mana", {"valor": 3.0, "duracao": 2.0}, 1)
	m.mana = 10.0
	var mana0: float = m.mana
	await _esperar(func(): return false, 0.5)
	check(m.mana - mana0 > m.stats["mana_regen"] * 0.5 * 2.0, "surto de mana acelera a regeneracao")
	var pos0: Vector2 = m.global_position
	m.lancar_efeito("salto_arcano", {"dano": 5.0, "raio": 80.0, "alcance": 200.0}, 1)
	check(m.global_position.distance_to(pos0 + Vector2(200, 0)) < 40.0, "salto arcano teleporta na direcao da mira")
	mundo.queue_free()
	await physics_frame

func _alvos_mago(mundo: Node, m: Node) -> Array:
	var out := []
	for i in 5:
		var e = load("res://scripts2d/enemy_2d.gd").new()
		mundo.add_child(e)
		e.setup("hollow_sentinel", m, m.global_position + Vector2(120 + i * 30, (i - 2) * 25))
		e.stats["speed"] = 0.0   # fica parado para a medição
		out.append(e)
	return out
## habilidades_arqueiro.csv: árvore coerente, textos, ícones e efeitos ativos funcionando.
## Física e camadas das habilidades (docs/arte/33_direcao_vfx_habilidades.md): a flecha nasce na boca do arco da
## direção mirada (CSV de ancoragem, espelhado à esquerda), desce até a altura de voo; a aura de Herald fica atrás do
## ator, como elipse no chão, com alfa limitado; o projétil em arco cria a sombra de aviso no destino e chama o impacto ao cair.
func _testar_fisica_habilidades() -> void:
	var HabScript = load("res://scripts2d/habilidades_2d.gd")
	var caminho_antes: String = HabScript.caminho
	HabScript.caminho = "user://teste_fisica_habilidades_2d.json"   # save próprio: o que este teste aprende não vaza para os outros
	DirAccess.remove_absolute(HabScript.caminho)
	await _fisica_habilidades()
	DirAccess.remove_absolute(HabScript.caminho)
	HabScript.caminho = caminho_antes

func _fisica_habilidades() -> void:
	var Vfx = load("res://scripts2d/vfx_2d.gd")
	var Feel = load("res://scripts2d/feel_2d.gd")
	for k in ["aura_diametro", "aura_alfa", "aura_altura", "muzzle_flash_time", "shot_recoil_px", "arc_shadow_alpha", "zone_ring_time", "zone_fade_time"]:
		check(Feel.cfg().has(k), "feel.csv tem " + k)
	var linhas := {}
	for r in Csv.rows("res://data2d/ancoras_2d.csv"):
		if r["id"] == "arqueiro" and r["anim"] == "attack":
			linhas[int(r["linha"])] = true
			check(float(r["y"]) < -30.0, "boca do arco da linha %s fica acima do peito" % r["linha"])
	check(linhas.size() == 5, "ancoras_2d.csv tem as 5 linhas do ataque do arqueiro (%d)" % linhas.size())
	var m := Node2D.new()
	root.add_child(m)
	var p = load("res://scripts2d/player_2d.gd").new()
	m.add_child(p)
	await physics_frame
	var dir_e: Dictionary = p.boca_do_arco(Vector2.RIGHT)
	var dir_o: Dictionary = p.boca_do_arco(Vector2.LEFT)
	var dir_n: Dictionary = p.boca_do_arco(Vector2.UP)
	check(dir_e["chao"].x > p.global_position.x and dir_e["altura"] > 40.0, "mirando à direita a flecha nasce do lado do arco, na altura da mão")
	check(is_equal_approx(dir_o["chao"].x - p.global_position.x, -(dir_e["chao"].x - p.global_position.x)), "mirando à esquerda a boca do arco é o espelho da direita")
	check(dir_n["chao"].x < p.global_position.x, "de costas (norte) o arco fica do outro lado")
	var f = p.lancar_flecha(Vector2.RIGHT)
	check(f.global_position.is_equal_approx(dir_e["origem"]) and is_equal_approx(f.altura, dir_e["altura"]), "a colisão da flecha nasce na linha da mira")
	check(f.vis.global_position.is_equal_approx(dir_e["chao"] + Vector2(0.0, -dir_e["altura"])), "o desenho da flecha nasce na boca do arco")
	check(f.vis.position.y < -40.0, "o desenho da flecha começa na altura do arco")
	var flashes := 0
	for n in m.get_children():
		if n is Sprite2D and n.get_script() != null and n.z_index == 4:
			flashes += 1
	check(flashes >= 1, "disparo cria o flash de boca")
	f.cor_fx = Color(1.0, 0.2, 0.2)
	check(f.cor_atual().is_equal_approx(Color(1.0, 0.2, 0.2)), "a cor do elemento repinta o brilho e o rastro da flecha")
	for i in 20:
		await physics_frame
	if is_instance_valid(f):
		check(f.altura < dir_e["altura"], "em voo a flecha desce da altura do arco para a de voo")
		check(absf(f.vis.position.x) < absf(dir_e["desloc"].x), "em voo o desenho converge para a linha da mira")
	# aura C1: atrás do ator, centrada no tronco, alfa limitado, diâmetro do feel.csv
	var desenho := Sprite2D.new()
	desenho.texture = Feel.ponto()
	desenho.modulate.a = 1.0
	var aura = Vfx.aura_c1(p, desenho, 32.0, "AuraTeste")
	check(aura.get_parent() == p and aura.show_behind_parent and aura.position.y <= 0.0 and aura.scale.y < aura.scale.x, "aura é uma elipse no chão, atrás do ator")
	check(aura.modulate.a <= Feel.cfg()["aura_alfa"] + 0.001, "aura respeita o alfa máximo")
	check(is_equal_approx(aura.scale.x * 32.0, Feel.cfg()["aura_diametro"]), "aura tem o diâmetro do feel.csv")
	var aura2 = Vfx.aura_c1(p, Sprite2D.new(), 32.0, "AuraTeste")
	check(aura2.name == "AuraTeste" and aura2 != aura, "aura nova substitui a antiga de mesmo nome")
	# Heralds equipados põem as quatro auras na mesma camada
	var h = p.habilidades
	h.ganhar_pontos(400)
	for id in ["herald_plague", "herald_ice", "herald_thunder", "arauto_cinzas"]:
		var cadeia := []   # aprende da raiz do ramo até o Herald
		var cur: String = id
		while cur != "":
			cadeia.push_front(cur)
			cur = h.defs[cur]["pai"]
		for c in cadeia:
			if h.nivel(c) < 1:
				h.aprender(c)
		check(h.nivel(id) >= 1, "teste aprende %s" % id)
	await physics_frame
	for nome in ["AuraPeste", "AuraGelo", "AuraArauto", "AuraCinzas"]:
		var a := p.get_node_or_null(nome) as Node2D
		check(a != null and a.show_behind_parent and a.position.y <= 0.0 and a.modulate.a <= Feel.cfg()["aura_alfa"] + 0.001, "Herald equipado: %s atrás do arqueiro" % nome)
	# projétil em arco: sombra de aviso no destino, cai e chama o impacto
	var caiu := []
	var corpo := Node2D.new()
	var destino: Vector2 = p.global_position + Vector2(300, 0)
	var arco = Vfx.arco(m, p.global_position, 50.0, destino, 200.0, 0.2, corpo, Color.GREEN, 80.0, func(pt: Vector2): caiu.append(pt))
	await physics_frame
	var avisos := 0
	for n in m.get_children():
		if n.has_method("concluir"):
			avisos += 1
	check(avisos >= 1, "projétil em arco cria a sombra de aviso no ponto de queda")
	check(arco.altura() > 50.0 and corpo.position.y < -50.0, "no começo do voo o corpo sobe e o nó fica no chão")
	await _esperar(func(): return not caiu.is_empty(), 1.0)
	check(caiu.size() == 1 and caiu[0].is_equal_approx(destino), "o projétil em arco cai no destino e chama o impacto uma vez")
	m.queue_free()
	await physics_frame

func _def_arqueiro(r: Dictionary) -> Dictionary:
	var d := {}
	for k in ["cd", "custo", "dano", "qtd", "angulo", "raio", "duracao", "alcance", "valor", "escala"]:
		if r[k] != "":
			d[k] = float(r[k])
	return d

func _testar_habilidades_arqueiro() -> void:
	var rows: Array = Csv.rows("res://data2d/habilidades_arqueiro.csv")
	check(rows.size() >= 15 and rows.size() <= 60, "arqueiro tem de 15 a 60 habilidades (%d)" % rows.size())
	var por_id := {}
	var icones := {}
	for r in Csv.rows("res://data2d/icones.csv"):
		icones[r["id"]] = true
	var player_stats := Csv.kv("res://data2d/player.csv")
	var ramos := {}
	var ativas := 0
	for r in rows:
		por_id[r["id"]] = r
	for r in rows:
		var id: String = r["id"]
		ramos[r["ramo"]] = true
		check(Csv.t("skill.%s.name" % id) != "skill.%s.name" % id and Csv.t("skill.%s.desc" % id) != "skill.%s.desc" % id, "texto de %s" % id)
		check(icones.has(r["icone"]), "ícone de %s existe" % id)
		check(int(r["nivel_max"]) >= 1 and int(r["pontos"]) >= 1 and int(r["tier"]) >= 1, "%s: níveis, pontos e tier válidos" % id)
		if r["pai"] != "":
			check(por_id.has(r["pai"]) and por_id[r["pai"]]["ramo"] == r["ramo"] and int(por_id[r["pai"]]["tier"]) < int(r["tier"]), "%s: pai no mesmo ramo e tier menor" % id)
		else:
			check(int(r["tier"]) == 1, "%s: raiz é tier 1" % id)
		if r["tipo"] == "passiva" and r["efeito"] != "stat":
			check(r["efeito"] in ["arauto", "herald_gelo", "herald_cinzas"], "%s: passiva de gatilho (Herald) conhecida" % id)
		elif r["tipo"] == "passiva":
			check(player_stats.has(r["stat"]) and (r["modo"] == "add" or r["modo"] == "mult") and r["valor"] != "", "%s: passiva muda stat existente" % id)
		else:
			ativas += 1
			check(float(r["cd"]) > 0.0, "%s: ativa tem recarga" % id)
	for ramo in ["precisao", "cacada", "sombra", "veneno", "gelo", "fogo", "raio"]:
		check(ramos.has(ramo) and Csv.t("ramo.%s.name" % ramo) != "ramo.%s.name" % ramo, "ramo %s tem skills e texto" % ramo)
	check(ativas >= 8, "ao menos 8 ativas (%d)" % ativas)
	print("DBG paused ", paused, " ts ", Engine.time_scale)
	var Efeitos = load("res://scripts2d/efeitos_arqueiro_2d.gd")
	for r in rows:
		if r["tipo"] != "ativa":
			continue
		var mundo := Node2D.new()
		root.add_child(mundo)
		var p = load("res://scripts2d/player_2d.gd").new()
		p.god_mode = true
		p.auto_aim = Vector2.RIGHT
		mundo.add_child(p)
		var es: Array = []
		for k in 3:
			var e = load("res://scripts2d/enemy_2d.gd").new()
			mundo.add_child(e)
			e.setup("hollow_sentinel", p, p.global_position + Vector2(160 + 40 * k, 0))
			e.hp = 1000.0
			e.hp_max = 1000.0
			e.stats["aggro"] = 0.0   # parados
			es.append(e)
		await physics_frame
		var antes: Array = es.map(func(e): return e.hp)
		var ok: bool = Efeitos.executar(r["efeito"], p, _def_arqueiro(r), 1, Vector2.RIGHT)
		check(ok, "%s (%s) executa" % [r["id"], r["efeito"]])
		await _esperar(func(): return es.any(func(e): return e.hp < 1000.0 or e.tem_status("marca") or e.tem_status("lentidao") or e.tem_status("veneno") or e.tem_status("choque") or e.tem_status("queimadura")), 4.0)
		var afetado: bool = es.any(func(e): return e.hp < 1000.0 or e.tem_status("marca") or e.tem_status("lentidao") or e.tem_status("veneno") or e.tem_status("choque") or e.tem_status("queimadura") or e.atordoado > 0.0)
		match r["efeito"]:
			"salto":
				check(p.global_position.x < -50.0 or p.estado == p.Estado.ESQUIVA or p.invencivel > 0.0, "salto recua com invulnerabilidade")
			"furia":
				check(p.cad_buff > 1.0 and p.vel_buff > 1.0, "adrenalina acelera tiro e corrida")
			"armadilha":
				for e in es:
					e.global_position = p.global_position + Vector2(160, 0)
				await _esperar(func(): return es.any(func(e): return e.atordoado > 0.0), 2.0)
				check(es.any(func(e): return e.atordoado > 0.0), "armadilha atordoa quem pisa")
			_:
				check(afetado, "%s afeta os inimigos à frente" % r["id"])
		mundo.queue_free()
		await physics_frame
	# Herald da Peste: inimigo envenenado que morre passa o veneno ao vizinho dentro do raio
	var VenenoFx = load("res://scripts2d/efeitos_arqueiro_veneno_2d.gd")
	var mh := Node2D.new()
	root.add_child(mh)
	var ph = load("res://scripts2d/player_2d.gd").new()
	mh.add_child(ph)
	var morto = load("res://scripts2d/enemy_2d.gd").new()
	var perto = load("res://scripts2d/enemy_2d.gd").new()
	var longe = load("res://scripts2d/enemy_2d.gd").new()
	for e in [morto, perto, longe]:
		mh.add_child(e)
	morto.setup("hollow_sentinel", ph, Vector2(400, 0))
	perto.setup("hollow_sentinel", ph, Vector2(450, 0))
	longe.setup("hollow_sentinel", ph, Vector2(1500, 0))
	morto.aplicar_status("veneno", 3.0, 4.0)
	VenenoFx.arauto_peste_morte(morto, {"raio": 140.0, "duracao": 3.0, "valor": 4.0})
	check(perto.tem_status("veneno") and not longe.tem_status("veneno"), "Arauto da Peste passa o veneno só a quem está no raio")
	mh.queue_free()
	await physics_frame
	# leque do autocast: 1º disparo reto, os seguintes abrem +d, -d, +2d
	var pl = load("res://scripts2d/player_2d.gd").new()
	pl.stats = {"leque_graus": 10.0, "leque_janela": 0.4}
	var graus: Array = []
	for k in 4:
		graus.append(snappedf(rad_to_deg(pl._desvio_leque(1000 + k * 50)), 0.1))
		pl._leque_disparos.append(1000 + k * 50)
	check(graus == [0.0, 10.0, -10.0, 20.0], "leque do autocast abre +d, -d, +2d (%s)" % str(graus))
	check(is_equal_approx(pl._desvio_leque(5000), 0.0), "disparo isolado depois da janela sai reto")
	pl.free()
	# passiva de crítico e veneno: a flecha carrega os dados
	var m2 := Node2D.new()
	root.add_child(m2)
	var p2 = load("res://scripts2d/player_2d.gd").new()
	m2.add_child(p2)
	await physics_frame
	p2.stats["crit_chance"] = 1.0
	p2.stats["poison_dps"] = 5.0
	var f = p2.lancar_flecha(Vector2.RIGHT)
	check(is_equal_approx(f.damage, p2.stats["arrow_damage"] * p2.stats["crit_mult"]), "crítico multiplica o dano")
	check(is_equal_approx(f.veneno_dps, 5.0), "flecha carrega veneno")
	m2.queue_free()
	await physics_frame
