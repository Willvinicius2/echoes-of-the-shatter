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

## Marcos da fase 1: o baú do bolsão fica no lugar (sem ímã, nem no fim da onda) e cada encontro `@guarda` nasce
## adormecido quando o jogador chega perto, acorda junto, vale a curva da onda atual vezes a força do mapa e fica fora
## da conta do spawner.
func _testar_marcos(run) -> void:
	var p = run.player
	var room = run.room
	var baus: Array = t.get_nodes_in_group("coletaveis").filter(func(g): return g.fixo)
	check.call(room.bolsoes.size() == 1 and baus.size() == 1, "marcos: o baú do bolsão está no chão desde o começo")
	if baus.size() == 1:
		var onde: Vector2 = baus[0].global_position
		run.atrair_coletaveis()
		await t.physics_frame
		check.call(not baus[0].atraida and baus[0].global_position == onde, "marcos: o baú do bolsão não voa atrás do jogador")
	check.call(not run._mult_onda.is_empty() and run._guardas_pend.size() == room.guardas.size(), "marcos: encontros à espera e curva da onda copiada do core")
	var g0: Dictionary = room.guardas[0]
	var partes: Array = String(g0["spec"]).split("|", false)
	var esperados := 0
	for parte in partes:
		esperados += int(parte.split(":")[1])
	p.global_position = g0["pos"] + Vector2(0, 700)   # dentro do alcance de nascer, fora do raio de acordar
	run._guardas_t = 1.0
	run._tick_guardas(0.0)
	var meus: Array = t.get_nodes_in_group("hurtable").filter(func(e): return e.has_meta("guarda") and e.grupo_despertar == "guarda_0")   # o primeiro da lista nasce primeiro
	check.call(meus.size() == esperados, "marcos: o encontro nasce com %d integrantes (%d)" % [esperados, meus.size()])
	if meus.size() != esperados:
		return
	check.call(meus.all(func(e): return e.global_position.distance_to(g0["pos"]) <= float(run.config["guard_spread"]) + 32.0), "marcos: os integrantes nascem em volta do ponto do mapa")
	# nenhum ponto sorteado, em nenhum dos encontros do mapa, cai sob o sprite alto de árvore, pilar, tumba ou verga
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	var sob := 0
	var sorteados := 0
	for g in room.guardas:
		var n := 0
		for parte in String(g["spec"]).split("|", false):
			n += int(parte.split(":")[1])
		for q in room.pontos_livres_perto(g["pos"], float(run.config["guard_spread"]), n, rng):
			sorteados += 1
			if room.sob_sprite_alto(q):
				sob += 1
	check.call(room._sprites_altos.size() > 50 and sorteados > 0 and sob == 0, "marcos: os encontros nascem fora do sprite de árvores, pilares e vergas (%d de %d sob um sprite, %d sprites altos)" % [sob, sorteados, room._sprites_altos.size()])
	var dorme: bool = meus.all(func(e): return e.raio_despertar > 0.0)
	var vizinhos_dormem: bool = t.get_nodes_in_group("hurtable").filter(func(e): return e.has_meta("guarda") and not meus.has(e)).all(func(e): return e.raio_despertar > 0.0)
	check.call(dorme and vizinhos_dormem, "marcos: o encontro nasce adormecido")
	var e0 = meus[0]
	var base: Dictionary = Csv.enemy(e0.stats["id"])
	var mult: Dictionary = run._mult_onda
	check.call(absf(e0.hp_max - float(base["hp"]) * float(mult["hp"]) * float(g0["forca"])) < 0.01, "marcos: vida do encontro = curva da onda x força do mapa (%.1f)" % e0.hp_max)
	check.call(not run._guardas_pend.has(g0), "marcos: o encontro que nasceu sai da lista")
	e0.take_damage(0.001)   # ferir um acorda o grupo dele
	check.call(meus.all(func(e): return e.raio_despertar == 0.0), "marcos: ferir um acorda o encontro todo")
	var outros: Array = t.get_nodes_in_group("hurtable").filter(func(e): return e.has_meta("guarda") and not meus.has(e))
	check.call(outros.all(func(e): return e.raio_despertar > 0.0), "marcos: os outros encontros seguem dormindo")
	var vivos_core := int(run.nucleo.ondas_estado()["alive"])
	e0.take_damage(1.0e9)
	check.call(int(run.nucleo.ondas_estado()["alive"]) == vivos_core, "marcos: morte de encontro não conta no spawner")
	if baus.size() == 1:   # o baú do bolsão abre ao encostar: carta de baú, e ele some do chão
		p.global_position = baus[0].global_position
		await _esperar(func(): return run.ui.aberta, 3.0)
		check.call(run.ui.aberta and run.ui.modo == "chest", "marcos: encostar no baú do bolsão abre a carta de baú")
		_escolher_tudo(run)
		await t.physics_frame
		check.call(not is_instance_valid(baus[0]), "marcos: o baú do bolsão some depois de aberto")
	p.global_position = room.spawn_jogador

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
	# Barra de XP e nível no topo da tela, ligada ao core.
	check.call(run.hud_xp != null and run.hud_xp.ativo, "horda: barra de XP e nível ligada")
	run.hud_xp._process(0.016)
	check.call(run.hud_xp._nivel == 1 and run.hud_xp._xp_prox > 1.0, "horda: barra de XP lê nível 1 e o XP do próximo do core")
	check.call(p.nivel_jogador == 1 and p.xp_proximo > 1.0 and p.xp >= 0.0, "horda: jogador expõe nivel_jogador, xp e xp_proximo para a HUD")
	# Camadas: a árvore fixa (core do hub) é outra que a da partida, e passiva de gema entra nos stats na hora.
	check.call(run.arvore_fixa != null and run.arvore_fixa != p.habilidades, "horda: a camada de partida é separada da árvore fixa")
	var dano0: float = p.stats["arrow_damage"]
	run._aprender_gema("steady_aim")
	check.call(p.habilidades.nivel("steady_aim") == 1 and p.stats["arrow_damage"] > dano0, "horda: passiva ganha na gema aumenta os stats (%.1f -> %.1f)" % [dano0, p.stats["arrow_damage"]])
	check.call(run.arvore_fixa.nivel("steady_aim") == 0, "horda: a árvore fixa não muda com a gema da partida")
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
	await _testar_marcos(run)
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
	# A primeira gema do arqueiro é a escolha do Eco do básico (doc 36): quatro afinidades, e a escolha fica no jogador.
	var gemas_nivel := 0
	if run.ui.aberta and run.ui.modo == "afinidade":
		check.call(run.ui._ids.size() == 4, "horda: a primeira gema oferece as quatro afinidades (%d)" % run.ui._ids.size())
		gemas_nivel += 1
		run.ui.escolher(1)
		await t.physics_frame
		check.call("afinidade" in run.player and run.player.afinidade == "eco_peste", "horda: o Eco escolhido fica no jogador (%s)" % str(run.player.get("afinidade")))
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
	var nivel_antes: int = h.nivel(escolhida)
	run.ui.escolher(0)
	var soma1 := 0
	for id in h.ordem:
		soma1 += h.nivel(id)
	check.call(soma1 == soma0 + 1 and h.nivel(escolhida) == nivel_antes + 1, "horda: a habilidade escolhida na gema é aprendida")
	check.call(not h.eh_ativa(escolhida) or h.slots.has(escolhida), "horda: ativa nova da gema entra num slot livre")
	run.queue_free()
	await t.process_frame
	RunScript.modo_etapas = antes
