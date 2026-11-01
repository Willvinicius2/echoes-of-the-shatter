extends RefCounted
## Testes do modo horda (pacote H4 de docs/design/31_plano_hordas.md), chamado por test_2d.gd: o spawner do core
## enche a fase aberta fora da vista com a curva da onda, cada morte solta gema de XP, o nível abre cartas (ao menos uma
## de ataque), o elite solta baú com carta rara, o Guardião acorda no altar com a vida adaptativa e o portal dá a vitória.

const Csv = preload("res://scripts2d/csv2d.gd")
const RunScript = preload("res://scripts2d/run_2d.gd")
const RunScene = preload("res://scenes2d/Run2D.tscn")

var t: SceneTree
var check: Callable

func _init(arvore: SceneTree, verifica: Callable) -> void:
	t = arvore
	check = verifica

func _esperar(cond: Callable, max_s: float) -> void:
	var t0 := Time.get_ticks_msec()
	while not cond.call() and (Time.get_ticks_msec() - t0) < max_s * 1000.0:
		await t.physics_frame

func _ataque(id: String) -> bool:
	for r in Csv.rows("res://data2d/upgrades.csv"):
		if r["id"] == id:
			return r["tipo"] == "ataque"
	return false

func _escolher_tudo(run) -> int:
	var n := 0
	while run.ui.aberta and n < 50:
		run.ui.escolher(0)
		n += 1
	return n

func rodar() -> void:
	var antes: bool = RunScript.modo_etapas
	RunScript.modo_etapas = false
	var run = RunScene.instantiate()
	run.com_menu = false
	t.root.add_child(run)
	await t.physics_frame
	var p = run.player
	p.god_mode = true
	var cru: bool = p.habilidades.ordem.size() > 0
	for id in p.habilidades.ordem:
		cru = cru and p.habilidades.nivel(id) == 0
	for sl in p.habilidades.slots:
		cru = cru and sl == ""
	check.call(cru, "horda: a corrida começa só com o ataque básico (nada aprendido, slots vazios)")
	p.autocast = false
	check.call(run.horda and run.room.aberta() and run.fase_horda != "", "horda: fase aberta usa o spawner do core")
	await _esperar(func(): return t.get_nodes_in_group("hurtable").size() > 0, 3.0)
	var inimigos: Array = t.get_nodes_in_group("hurtable")
	check.call(inimigos.size() > 0 and run.onda == 1, "horda: a onda 1 nasce sozinha")
	var v: Rect2 = run.vista()
	var fora := true
	for e in inimigos:
		fora = fora and not v.has_point(e.global_position)
	check.call(fora, "horda: inimigos nascem fora da vista")
	var c1: Dictionary = run.nucleo.curva(run.fase_horda, 1)
	var curva_ok := true
	for e in inimigos:
		if not e.has_meta("elite"):
			curva_ok = curva_ok and absf(e.hp_max - Csv.enemy(e.stats["id"])["hp"] * float(c1["hp"])) < 0.01
	check.call(curva_ok, "horda: vida com a curva da onda")
	# Mortes soltam gemas; coletar sobe o nível e abre as cartas com ao menos uma de ataque.
	var xp_total := 0
	var n0: Dictionary = run.upgrades.nivel_estado()
	for i in 6:
		run.matar_todos()
		await t.physics_frame
		await t.physics_frame
		for g in t.get_nodes_in_group("coletaveis"):
			xp_total += int(g.valor)
		run.atrair_coletaveis()
		await _esperar(func(): return t.get_nodes_in_group("coletaveis").is_empty() or run.ui.aberta, 3.0)
		if run.ui.aberta:
			break
		await _esperar(func(): return t.get_nodes_in_group("hurtable").size() > 0, 4.0)
	check.call(xp_total > 0, "horda: mortes soltam gemas de XP")
	await _esperar(func(): return run.ui.aberta, 3.0)
	# A cada `skill_gem_every_levels` níveis vem uma gema de habilidade antes da carta de nível: escolhe e segue.
	var gemas_nivel := 0
	while run.ui.aberta and run.ui.modo == "gem" and gemas_nivel < 10:
		gemas_nivel += 1
		run.ui.escolher(0)
		await t.physics_frame
	check.call(gemas_nivel > 0, "horda: subir de nível também dá gema de habilidade")
	check.call(run.ui.aberta and run.ui.modo == "level" and t.paused, "horda: subir de nível abre as cartas e pausa")
	var tem_ataque := false
	for id in run.ui._ids:
		tem_ataque = tem_ataque or _ataque(id)
	check.call(run.ui._ids.size() == int(run.config["level_cards"]) and tem_ataque, "horda: %d cartas com ao menos uma de ataque" % run.ui._ids.size())
	var escolhidas := _escolher_tudo(run)
	check.call(escolhidas >= 1 and run.upgrades.niveis.size() > 0 and not t.paused and run.estado == run.Estado.LUTA, "horda: carta escolhida e a luta segue")
	check.call(int(run.upgrades.nivel_estado()["level"]) > int(n0["level"]), "horda: nível subiu no core")
	# Baú de elite: carta rara.
	run._soltar("bau", 0, p.global_position + Vector2(200, 0))
	await t.physics_frame
	run.atrair_coletaveis()
	await _esperar(func(): return run.ui.aberta, 3.0)
	check.call(run.ui.aberta and run.ui.modo == "chest", "horda: baú abre a carta de baú")
	_escolher_tudo(run)
	# Ondas andam: adianta o relógio do spawner e limpa até poder acordar o Guardião.
	await _esperar(func():
		run._tick_horda(2.0)
		run.matar_todos()
		_escolher_tudo(run)
		return int(run.nucleo.ondas_estado()["can_wake"]) == 0, 40.0)
	check.call(int(run.nucleo.ondas_estado()["can_wake"]) == 0 and run.onda >= int(run.nucleo.ondas_estado()["wake_wave"]), "horda: altar liberado na onda %d" % run.onda)
	_escolher_tudo(run)
	p.global_position = run.room.posicao_chefe + Vector2(0, 120)
	await _esperar(func(): return run.nucleo.ondas_estado()["boss_spawned"], 3.0)
	var chefe = null
	for e in t.get_nodes_in_group("hurtable"):
		if e.stats.get("kind", "") == "boss":
			chefe = e
	check.call(chefe != null and chefe.global_position.distance_to(run.room.posicao_chefe) < 1.0, "horda: chegar ao altar acorda o Guardião no lugar dele")
	var base: float = Csv.enemy("crypt_guardian")["hp"]
	check.call(chefe != null and is_equal_approx(chefe.hp_max, run.nucleo.vida_chefe(base, run.dps_medido)) and chefe.hp_max >= base * float(run.config["boss_hp_min"]) - 0.01, "horda: vida do chefe adaptativa (%.0f, DPS %.1f)" % [chefe.hp_max if chefe else 0.0, run.dps_medido])
	if chefe != null:
		chefe.take_damage(1.0e9)
	run.matar_todos()
	await _esperar(func(): return run.estado == run.Estado.LIMPA, 4.0)
	_escolher_tudo(run)
	check.call(run.estado == run.Estado.LIMPA and run.posicao_saida() != Vector2.ZERO, "horda: Guardião morto abre o portal")
	await t.physics_frame
	p.global_position = run.posicao_saida()
	await _esperar(func(): return run.estado == run.Estado.VENCEU, 4.0)
	check.call(run.estado == run.Estado.VENCEU, "horda: portal dá a vitória")
	await _esperar(func(): return run.menus.tela == run.menus.Tela.FIM, 5.0)
	t.paused = false
	# Gema de habilidade: ensina ou melhora uma habilidade e ocupa um slot livre.
	var h = p.habilidades
	var soma0 := 0
	for id in h.ordem:
		soma0 += h.nivel(id)
	run._usar_gema_habilidade()
	check.call(run.ui.aberta and run.ui.modo == "gem" and run.ui._ids.size() == int(run.config["skill_gem_cards"]), "horda: gema de habilidade abre a escolha entre %d habilidades" % run.ui._ids.size())
	var escolhida: String = run.ui._ids[0] if run.ui._ids.size() > 0 else ""
	run.ui.escolher(0)
	var soma1 := 0
	for id in h.ordem:
		soma1 += h.nivel(id)
	check.call(soma1 == soma0 + 1 and h.nivel(escolhida) == 1, "horda: a habilidade escolhida na gema é aprendida")
	check.call(not h.eh_ativa(escolhida) or h.slots.has(escolhida), "horda: ativa nova da gema entra num slot livre")
	run.queue_free()
	await t.process_frame
	RunScript.modo_etapas = antes
