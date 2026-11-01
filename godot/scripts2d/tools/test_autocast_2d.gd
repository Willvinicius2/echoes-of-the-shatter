extends RefCounted
## Testes do autocast (pacote H2 de docs/design/31_plano_hordas.md), chamado por test_2d.gd:
## básico e ativas disparam sozinhos no inimigo certo, a ult só na tecla, nada dispara sem alvo.

const Csv = preload("res://scripts2d/csv2d.gd")
const HabScript = preload("res://scripts2d/habilidades_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const PlayerScript = preload("res://scripts2d/player_2d.gd")
const MagoScript = preload("res://scripts2d/mago_2d.gd")
const WarriorScript = preload("res://scripts2d/warrior_2d.gd")
const EnemyScript = preload("res://scripts2d/enemy_2d.gd")

const MIRAS_VALIDAS := ["proximo", "grupo", "si", "fuga", "manual"]

var t: SceneTree
var check: Callable

func _init(arvore: SceneTree, verifica: Callable) -> void:
	t = arvore
	check = verifica

func rodar() -> void:
	_dados()
	await _sem_alvo_nao_dispara()
	await _arqueiro()
	await _mago()
	await _guerreiro()
	await _mira_mouse()

func _esperar(cond: Callable, max_s: float) -> void:
	var t0 := Time.get_ticks_msec()
	while not cond.call() and (Time.get_ticks_msec() - t0) < max_s * 1000.0:
		await t.physics_frame

## Toda ativa das 3 classes tem mira no CSV, cada classe tem básico e uma ult.
func _dados() -> void:
	var miras: Array = Csv.rows(HabScript.MIRAS)
	check.call(miras.size() > 0, "habilidades_mira.csv carrega")
	for c in ["arqueiro", "guerreiro", "mago"]:
		var m: Dictionary = HabScript.carregar_miras(c)
		check.call(m.has("basico") and m["basico"]["alcance"] > 0.0, "%s: básico tem mira e alcance" % c)
		var ults := 0
		var cl: Dictionary = HabScript.classes().get(c, {})
		for r in Csv.rows(cl.get("habilidades", "")):
			if r["tipo"] != "ativa":
				continue
			check.call(m.has(r["id"]) and MIRAS_VALIDAS.has(m[r["id"]]["mira"]), "%s: %s tem mira válida" % [c, r["id"]])
			if m.has(r["id"]) and m[r["id"]]["ult"]:
				ults += 1
		check.call(ults == 1, "%s tem uma ult manual (%d)" % [c, ults])
		for id in m:
			check.call(id == "basico" or Csv.rows(cl.get("habilidades", "")).any(func(r): return r["id"] == id), "%s: %s do csv de miras existe na árvore" % [c, id])

func _mundo() -> Node2D:
	var mundo := Node2D.new()
	t.root.add_child(mundo)
	return mundo

func _inimigo(mundo: Node2D, alvo: Node2D, pos: Vector2) -> Node2D:
	var e = EnemyScript.new()
	mundo.add_child(e)
	e.setup("hollow_sentinel", alvo, pos)
	e.hp = 5000.0
	e.hp_max = 5000.0
	e.stats["aggro"] = 0.0   # parado
	e.stats["damage"] = 0.0
	return e

## Ensina e equipa `ids` (na ordem dos slots), com pontos de sobra.
func _equipar(j: Node2D, ids: Array) -> void:
	var h: RefCounted = j.habilidades
	h.ganhar_pontos(200)
	for id in ids:
		_aprender_com_pais(h, id)
	for i in ids.size():
		h.equipar(i, ids[i])

func _aprender_com_pais(h: RefCounted, id: String) -> void:
	var pai: String = h.defs[id]["pai"]
	if pai != "" and h.nivel(pai) == 0:
		_aprender_com_pais(h, pai)
	if h.nivel(id) == 0:
		h.aprender(id)

## Sem inimigo por perto ninguém atira nem gasta recarga.
func _sem_alvo_nao_dispara() -> void:
	var mundo := _mundo()
	var p = PlayerScript.new()
	p.god_mode = true
	mundo.add_child(p)
	await t.physics_frame
	_equipar(p, ["power_shot"])
	for _i in 30:
		await t.physics_frame
	check.call(p.habilidades.nivel("power_shot") > 0 and p.habilidades.slots[0] == "power_shot", "autocast: power_shot aprendido e no slot 1")
	check.call(not p.habilidades.recargas.has("power_shot") and p.estado != p.Estado.ATIRANDO, "autocast: sem inimigo não dispara nada")
	mundo.queue_free()
	await t.physics_frame

func _arqueiro() -> void:
	var mundo := _mundo()
	var p = PlayerScript.new()
	p.god_mode = true
	mundo.add_child(p)
	await t.physics_frame
	# o motivo do "não ataca": sem autocast, nada sai sem tecla; com autocast o básico sai sozinho
	p.autocast = false
	var e := _inimigo(mundo, p, p.global_position + Vector2(0, 300))
	for _i in 40:
		await t.physics_frame
	check.call(is_equal_approx(e.hp, 5000.0), "sem autocast e sem tecla o arqueiro não ataca (comportamento antigo)")
	p.autocast = true
	await _esperar(func(): return e.hp < 5000.0, 4.0)
	check.call(e.hp < 5000.0, "arqueiro: tiro básico sai sozinho e acerta o inimigo abaixo")
	check.call(p.mira_atual().dot(Vector2.DOWN) > 0.95, "arqueiro: mira vira para o inimigo mais próximo")
	_equipar(p, ["power_shot", "arrow_rain", "fan_of_arrows", "adrenaline"])
	await _esperar(func(): return p.habilidades.recargas.has("power_shot") and p.habilidades.recargas.has("arrow_rain"), 4.0)
	check.call(p.habilidades.recargas.has("power_shot"), "arqueiro: Tiro Forte sai sozinho")
	check.call(p.habilidades.recargas.has("arrow_rain"), "arqueiro: Chuva de Flechas sai sozinha no grupo")
	check.call(not p.habilidades.recargas.has("fan_of_arrows"), "arqueiro: Leque espera o inimigo chegar perto (alcance do CSV)")
	check.call(not p.habilidades.recargas.has("adrenaline"), "arqueiro: a ult não dispara sozinha")
	check.call(p.usar_ult() and p.habilidades.recargas.has("adrenaline") and p.cad_buff > 1.0, "arqueiro: a ult sai na tecla")
	check.call(InputMap.has_action("ult"), "tecla de ult registrada")
	mundo.queue_free()
	await t.physics_frame

func _mago() -> void:
	var mundo := _mundo()
	var m = MagoScript.new()
	m.god_mode = true
	mundo.add_child(m)
	await t.physics_frame
	var e := _inimigo(mundo, m, m.global_position + Vector2(-260, 0))
	_equipar(m, ["skill.mage.frost_bolt", "skill.mage.meteor"])
	await _esperar(func(): return m.habilidades.recargas.has("skill.mage.frost_bolt") and m.habilidades.recargas.has("skill.mage.meteor"), 4.0)
	check.call(m.habilidades.recargas.has("skill.mage.frost_bolt"), "mago: Raio de Gelo sai sozinho")
	check.call(m.habilidades.recargas.has("skill.mage.meteor"), "mago: Meteoro sai sozinho")
	await _esperar(func(): return e.hp < 5000.0 and e.tem_status("lentidao"), 4.0)
	check.call(e.hp < 5000.0 and e.tem_status("lentidao"), "mago: o raio acerta e lentifica o inimigo à esquerda")
	mundo.queue_free()
	await t.physics_frame
	# Meteoro cai no inimigo, não no cursor
	var mundo2 := _mundo()
	var m2 = MagoScript.new()
	m2.god_mode = true
	mundo2.add_child(m2)
	await t.physics_frame
	var e2 := _inimigo(mundo2, m2, m2.global_position + Vector2(0, -400))
	_equipar(m2, ["skill.mage.meteor"])
	await _esperar(func(): return e2.hp < 5000.0, 4.0)
	check.call(e2.hp < 5000.0, "mago: Meteoro cai em cima do inimigo")
	mundo2.queue_free()
	await t.physics_frame

func _guerreiro() -> void:
	var mundo := _mundo()
	var w = WarriorScript.new()
	var h = HabScript.new()
	h.persistir = false
	h.carregar_classe("guerreiro")
	w.habilidades = h
	w.god_mode = true
	mundo.add_child(w)
	await t.physics_frame
	var e := _inimigo(mundo, w, w.global_position + Vector2(60, 0))
	await _esperar(func(): return e.hp < 5000.0, 3.0)
	check.call(e.hp < 5000.0, "guerreiro: combo sai sozinho no inimigo encostado")
	e.global_position = w.global_position + Vector2(0, 250)
	_equipar(w, ["w_charge", "w_rampage"])
	await _esperar(func(): return h.recargas.has("w_charge"), 3.0)
	check.call(h.recargas.has("w_charge"), "guerreiro: Investida sai sozinha no inimigo a distância")
	check.call(not h.recargas.has("w_rampage"), "guerreiro: a ult (Fúria) não sai sozinha")
	mundo.queue_free()
	await t.physics_frame

## Opção de acessibilidade: dispara sozinho, mas mira no cursor/mira forçada.
func _mira_mouse() -> void:
	var mundo := _mundo()
	var p = PlayerScript.new()
	p.god_mode = true
	mundo.add_child(p)
	await t.physics_frame
	_inimigo(mundo, p, p.global_position + Vector2(300, 0))
	Alvos.mira_mouse = true
	_equipar(p, ["power_shot"])
	var alvo: Dictionary = p.habilidades.alvo_auto("power_shot", t, p.global_position, 1000.0)
	check.call(not alvo.is_empty() and alvo["dir"].dot(Vector2.RIGHT) > 0.95, "alvo_auto acha o inimigo à direita")
	Alvos.mira_mouse = false
	mundo.queue_free()
	await t.physics_frame
