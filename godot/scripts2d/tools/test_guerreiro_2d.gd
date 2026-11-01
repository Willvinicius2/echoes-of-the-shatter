extends RefCounted
## Testes do Guerreiro e da sua árvore de habilidades (chamado por test_2d.gd).

const Csv = preload("res://scripts2d/csv2d.gd")
const Icones = preload("res://scripts2d/icones_2d.gd")
const HabScript = preload("res://scripts2d/habilidades_2d.gd")
const CorridaScript = preload("res://scripts2d/corrida_guerreiro_2d.gd")
const WarriorScript = preload("res://scripts2d/warrior_2d.gd")
const EnemyScript = preload("res://scripts2d/enemy_2d.gd")
const Classe = preload("res://scripts2d/classe_2d.gd")
const RunScene = preload("res://scenes2d/Run2D.tscn")

var t: SceneTree
var check: Callable

func _init(arvore: SceneTree, verifica: Callable) -> void:
	t = arvore
	check = verifica

func rodar() -> void:
	_dados()
	await _arvore()
	await _combate()
	await _ativas()
	await _corrida()

## Árvore do guerreiro sem save em disco e com pontos de sobra.
func _hab(pontos := 60) -> RefCounted:
	var h = HabScript.new()
	h.persistir = false
	h.carregar_classe("guerreiro")
	h.ganhar_pontos(pontos)
	return h

func _novo_guerreiro(pontos := 0) -> Node2D:
	var j: Node2D = WarriorScript.new()
	j.habilidades = _hab(pontos)
	t.root.add_child(j)
	await t.physics_frame
	return j

func _dados() -> void:
	var sk = _hab()
	check.call(sk.defs.size() >= 15 and sk.defs.size() <= 20, "guerreiro: 15 a 20 habilidades (%d)" % sk.defs.size())
	var ramos := {}
	var ativas := 0
	for id in sk.defs:
		var d: Dictionary = sk.defs[id]
		ramos[d["ramo"]] = true
		if d["tipo"] == "ativa":
			ativas += 1
			check.call(d["efeito"] != "" and d["cd"] > 0.0, "%s: efeito e recarga" % id)
		else:
			check.call(sk.defs[id]["stat"] != "" and d["valor"] != 0.0, "%s: passiva com stat e valor" % id)
		check.call(d["pai"] == "" or sk.defs.has(d["pai"]), "%s: pai existe" % id)
		check.call(Csv.t("skill.%s.name" % id) != "skill.%s.name" % id and Csv.t("skill.%s.desc" % id) != "skill.%s.desc" % id, "%s: textos" % id)
		check.call(Icones.textura(id) != null, "%s: icone" % id)
	check.call(ramos.size() == 3, "guerreiro: 3 ramos")
	check.call(ativas >= 8, "guerreiro: pelo menos 8 ativas (%d)" % ativas)
	var raizes := 0
	for id in sk.defs:
		if sk.defs[id]["pai"] == "":
			raizes += 1
	check.call(raizes >= 3, "cada ramo tem raiz")
	var stats := Csv.kv("res://data2d/guerreiro.csv")
	for id in sk.defs:
		if sk.defs[id]["tipo"] == "passiva":
			check.call(stats.has(sk.defs[id]["stat"]), "%s: stat %s existe em guerreiro.csv" % [id, sk.defs[id]["stat"]])

func _arvore() -> void:
	var j = await _novo_guerreiro(60)
	var sk = j.habilidades
	var run = CorridaScript.new()
	run.habilidades = sk
	run.restaurar(j)
	j.reset()
	check.call(sk.pode_aprender("w_keen_edge") and sk.pode_aprender("w_charge") and not sk.pode_aprender("w_heavy_slash"), "arvore: só raízes no começo")
	var dano0: float = j.stats["damage"]
	check.call(sk.aprender("w_keen_edge"), "aprende Fio Afiado")
	run.reaplicar(j)
	check.call(is_equal_approx(j.stats["damage"], dano0 * 1.2), "Fio Afiado: +20% de dano")
	check.call(sk.pode_aprender("w_heavy_slash"), "Fio Afiado libera Talho Pesado")
	check.call(not sk.aprender("w_stone_rift"), "não pula a árvore")
	var hp0: float = j.stats["hp_max"]
	sk.aprender("w_vigor")
	run.reaplicar(j)
	check.call(j.stats["hp_max"] == hp0 + 30.0 and is_equal_approx(j.hp, j.stats["hp_max"]), "Vigor: +30 de vida e cura")
	sk.aprender("w_iron_skin")
	for id in ["w_heavy_slash", "w_whirlwind", "w_charge", "w_shield_bash"]:
		check.call(sk.aprender(id), "aprende %s" % id)
	check.call(sk.slots.count("") == 0 and sk.slots[0] == "w_heavy_slash", "4 ativas ocupam 4 teclas")
	check.call(sk.aprender("w_flame_brand") and not sk.slots.has("w_flame_brand"), "quinta ativa fica sem tecla até equipar")
	check.call(sk.aprender("w_heavy_slash"), "ativa já aprendida ainda sobe de nível")
	check.call(sk.def_nivel("w_heavy_slash")["dano"] > sk.defs["w_heavy_slash"]["dano"], "nível 2 aumenta o dano da ativa")
	check.call(sk.def_nivel("w_heavy_slash")["espera"] == sk.defs["w_heavy_slash"]["espera"], "espera e recup chegam à definição")
	sk.redistribuir()
	run.reaplicar(j)
	check.call(sk.niveis.is_empty() and is_equal_approx(j.stats["damage"], dano0), "redistribuir zera a árvore")
	j.queue_free()

func _inimigo(pos: Vector2, id := "hollow_sentinel", hp := 100000.0) -> Node2D:
	var e: Node2D = EnemyScript.new()
	t.root.add_child(e)
	e.setup(id, null, pos)
	e.hp = hp
	e.hp_max = hp
	e.set_physics_process(false)  # parado: o teste mede só o dano
	return e

func _combate() -> void:
	var j = await _novo_guerreiro()
	j.global_position = Vector2(500, 500)
	j.god_mode = true
	var e := _inimigo(Vector2(560, 500))
	var longe := _inimigo(Vector2(500, 900))
	check.call(e.is_in_group("hurtable"), "inimigo de teste é alvo")
	j.auto_aim = Vector2.RIGHT
	for _i in 60:
		await t.physics_frame
	j.auto_aim = Vector2.ZERO
	check.call(e.hp < 100000.0, "combo de espada fere o inimigo a frente")
	check.call(longe.hp == 100000.0, "golpe não atinge quem está longe")
	check.call(j.impeto > 0.0, "acertar gera ímpeto")
	var combo_visto: int = j.combo
	check.call(combo_visto >= 1 and combo_visto <= 3, "combo de 1 a 3")
	# cone: alvo atrás não leva dano
	e.hp = 100000.0
	var atras := _inimigo(Vector2(440, 500))
	var cone: Array = j.alvos_cone(j.global_position, Vector2.RIGHT, 88.0, 110.0)
	check.call(cone.has(e) and not cone.has(atras), "cone acerta a frente e não as costas")
	# dano com ímpeto cheio é maior
	j.impeto = 0.0
	var d0: float = j._dano_para(e, 1.0)
	j.impeto = j.stats["impeto_max"]
	check.call(j._dano_para(e, 1.0) > d0, "ímpeto aumenta o dano")
	# execução: +40% contra alvo com menos de 30% de vida
	j.stats["exec_bonus"] = 0.4
	e.hp = 100000.0
	var cheio: float = j._dano_para(e, 1.0)
	e.hp = 20000.0
	check.call(is_equal_approx(j._dano_para(e, 1.0), cheio * 1.4), "Carrasco: +40% contra alvo quase morto")
	# roubo de vida
	j.stats["lifesteal"] = 0.5
	j.hp = 10.0
	j.acertar(e, 1.0)
	check.call(j.hp > 10.0, "roubo de vida cura")
	# dano recebido
	j.god_mode = false
	j.hp = j.stats["hp_max"]
	j.invencivel = 0.0
	j.take_damage(20.0, Vector2(800, 500))
	check.call(is_equal_approx(j.hp, j.stats["hp_max"] - 20.0), "dano recebido sem guarda")
	j.invencivel = 0.0
	j.stats["damage_taken"] = 0.5
	j.hp = j.stats["hp_max"]
	j.take_damage(20.0, Vector2(800, 500))
	check.call(is_equal_approx(j.hp, j.stats["hp_max"] - 10.0), "Pele de Ferro reduz o dano")
	# Última Resistência: volta uma vez
	j.stats["last_stand"] = 1.0
	j.invencivel = 0.0
	j.take_damage(1.0e6, Vector2(800, 500))
	check.call(not j.esta_morto() and j.hp > 0.0 and j.invencivel > 0.0, "Última Resistência salva da morte")
	j.invencivel = 0.0
	j.take_damage(1.0e6, Vector2(800, 500))
	check.call(j.esta_morto(), "segunda queda mata")
	for n in [e, longe, atras, j]:
		n.queue_free()
	await t.physics_frame

func _ativas() -> void:
	var j = await _novo_guerreiro(0)
	var sk = j.habilidades
	var run = CorridaScript.new()
	run.habilidades = sk
	run.restaurar(j)
	j.reset()
	j.global_position = Vector2(500, 500)
	j.god_mode = true
	j.autocast = false   # aqui cada ativa é usada à mão; o autocast tem os testes dele (test_autocast_2d.gd)
	for id in ["w_keen_edge", "w_heavy_slash", "w_whirlwind", "w_stone_rift", "w_flame_brand", "w_shield_bash", "w_charge", "w_battle_cry", "w_leap_slam", "w_rampage"]:
		var cadeia := _cadeia(sk, id)
		cadeia.reverse()   # cada ativa é testada isolada: a cadeia é aprendida no core, pais primeiro
		for pai in cadeia:
			if sk.nivel(pai) == 0:
				sk.ganhar_pontos(int(sk.defs[pai]["pontos"]))
				check.call(sk.aprender(pai), "aprende %s" % pai)
	var e := _inimigo(Vector2(580, 500))
	var vida := 100000.0
	var testes := {
		"w_heavy_slash": 1, "w_whirlwind": 1, "w_stone_rift": 1, "w_shield_bash": 1, "w_charge": 1, "w_leap_slam": 1,
	}
	for id in testes:
		e.hp = vida
		e.global_position = Vector2(760, 500) if id == "w_leap_slam" else Vector2(580, 500)  # o salto pousa a 260 px
		j.global_position = Vector2(500, 500)
		j.velocity = Vector2.ZERO
		j.estado = j.Estado.LIVRE
		sk.equipar(0, id)
		sk.limpar_recargas()
		j._aim = Vector2.RIGHT
		j.invencivel = 0.0
		check.call(j.usar(id), "%s: usar começa" % id)
		check.call(j.recarga_skill(id) > 0.9, "%s: entra em recarga" % id)
		check.call(not j.usar(id), "%s: não usa em recarga" % id)
		for _i in 90:
			await t.physics_frame
		check.call(e.hp < vida, "%s: causa dano" % id)
		check.call(j.estado == j.Estado.LIVRE, "%s: termina e libera o jogador" % id)
	# buffs
	sk.equipar(0, "w_battle_cry")
	sk.equipar(1, "w_rampage")
	sk.limpar_recargas()
	j.estado = j.Estado.LIVRE
	check.call(j.usar("w_battle_cry"), "Grito de Guerra")
	for _i in 30:
		await t.physics_frame
	check.call(j._buff_cry > 0.0, "Grito de Guerra liga o bônus de dano")
	var base_dano: float = j._dano_para(e, 1.0)
	j._buff_cry = 0.0
	check.call(base_dano > j._dano_para(e, 1.0), "bônus do Grito aumenta o dano")
	j.estado = j.Estado.LIVRE
	j.impeto = 10.0
	check.call(not j.usar("w_rampage"), "Fúria exige ímpeto")
	j.impeto = 100.0
	check.call(j.usar("w_rampage"), "Fúria com ímpeto")
	for _i in 30:
		await t.physics_frame
	check.call(j._buff_furia > 0.0 and j._taxa_ataque() > 1.4, "Fúria acelera os golpes")
	# HUD
	var slots: Array = j.slots_hud()
	check.call(slots.size() == 2 + sk.slots.size() - sk.slots.count("") and slots[0]["icone"] == "golpe", "slots do HUD: golpe, esquiva e ativas")
	# morte e reset
	j.god_mode = false
	j.invencivel = 0.0
	j.take_damage(1.0e6, Vector2(900, 500))
	check.call(j.esta_morto(), "guerreiro morre")
	j.reset()
	check.call(not j.esta_morto() and j.impeto == 0.0 and j.habilidades.recargas.is_empty(), "reset limpa o estado")
	e.queue_free()
	j.queue_free()
	await t.physics_frame

func _cadeia(sk, id: String) -> Array:
	var out := [id]
	var p: String = sk.defs[id]["pai"]
	while p != "":
		out.append(p)
		p = sk.defs[p]["pai"]
	return out

func _corrida() -> void:
	Classe.atual = "guerreiro"
	var run = RunScene.instantiate()
	run.com_menu = false
	t.root.add_child(run)
	await t.physics_frame
	var p = run.player
	check.call(p.has_method("slots_hud") and p.habilidades.defs.has("w_keen_edge") and run.upgrades.habilidades == p.habilidades, "corrida com guerreiro usa a árvore comum")
	p.god_mode = true
	check.call(run.estado == run.Estado.LUTA and run.vivos == 3, "sala 1 começa com 3 inimigos")
	var alvo = t.get_nodes_in_group("hurtable")[0]
	var antes: float = alvo.hp
	p.global_position = alvo.global_position + Vector2(0, 90)   # a sala 1 tem o riacho no meio e começa adormecida
	var tempo := 0.0
	while is_instance_valid(alvo) and alvo.hp > 0.0 and tempo < 12.0:
		p.auto_aim = alvo.global_position - p.global_position
		p.auto_move = p.auto_aim.normalized() if p.auto_aim.length() > 70.0 else Vector2.ZERO
		await t.physics_frame
		tempo += 1.0 / 60.0
	p.auto_aim = Vector2.ZERO
	p.auto_move = Vector2.ZERO
	check.call(not is_instance_valid(alvo) or alvo.hp < antes, "espada derruba inimigo na corrida")
	# sala limpa: ganha ponto de habilidade (sem cartas) e a saída abre (porta antiga ou onda seguinte na fase aberta)
	var pontos0: int = p.habilidades.pontos
	run.matar_todos()
	var espera := 0.0
	while not (run.estado in [run.Estado.LIMPA, run.Estado.PROXIMA] and run.hud.mensagem != "") and espera < 8.0:
		await t.physics_frame
		espera += 1.0 / 60.0
	check.call(p.habilidades.pontos > pontos0, "sala limpa dá ponto de habilidade ao guerreiro")
	check.call(not run.ui.aberta, "guerreiro não recebe cartas do core")
	# volta ao arqueiro
	Classe.atual = "arqueiro"
	run.queue_free()
	await t.physics_frame
