extends SceneTree
## Testes headless sem addons.
## Uso: <godot_console> --headless --path <projeto> -s res://tests/run_tests.gd
## Sai com código != 0 se algo falhar.

const SMOKE_FRAMES: int = 900
const BOSS_FRAME: int = 420

class ErrorCatcher extends Logger:
	var errors: Array[String] = []

	func _log_error(function: String, file: String, line: int, code: String, rationale: String, _editor_notify: bool, error_type: int, _script_backtraces: Array[ScriptBacktrace]) -> void:
		if error_type == 1:
			return # avisos não contam
		errors.append("%s:%d [%s] %s %s" % [file, line, function, code, rationale])

	func _log_message(_message: String, _error: bool) -> void:
		pass

var _pass: int = 0
var _fail: int = 0
var _catcher: ErrorCatcher = ErrorCatcher.new()
var _crypt: Node2D = null
var _frames: int = 0
var _smoke_done: bool = false
var _phase: int = 0


func check(cond: bool, name: String) -> void:
	if cond:
		_pass += 1
	else:
		_fail += 1
		print("  FALHOU: ", name)


func approx(a: float, b: float, eps: float = 0.01) -> bool:
	return absf(a - b) <= eps


func _initialize() -> void:
	OS.add_logger(_catcher)
	print("== Echoes of the Shatter: testes ==")
	test_stat_block()
	test_damage_calc()
	test_effects_triggers()
	test_guard_and_pool()
	test_rng()
	test_data()


## Roda no primeiro frame: autoloads já estão na árvore e o InputMap registrado.
func _process(_delta: float) -> bool:
	if _phase == 0:
		_phase = 1
		test_input_actions()
		print("Unitários: %d ok, %d falhas" % [_pass, _fail])
		_start_smoke()
	return false


# ------------------------------------------------------------------ helpers

func make_combatant(stats: Dictionary) -> Combatant:
	var c: Combatant = Combatant.new()
	for k: String in stats.keys():
		c.stats.set_base(k, float(stats[k]))
	if not stats.has("max_life"):
		c.stats.set_base("max_life", 1000.0)
	c.reset()
	return c


func spec(coef: float = 1.0, tags: PackedStringArray = PackedStringArray(["ataque"]), dtype: int = 0, is_attack: bool = true) -> HitSpec:
	var s: HitSpec = HitSpec.new()
	s.tags = tags
	s.coefficient = coef
	s.damage_type = dtype
	s.is_attack = is_attack
	return s


# ------------------------------------------------------------------ StatBlock

func test_stat_block() -> void:
	var sb: StatBlock = StatBlock.new()
	sb.set_base("dano", 10.0)
	check(approx(sb.get_value("dano"), 10.0), "StatBlock: só base")
	sb.add("dano", StatMod.Kind.FLAT, 5.0)
	sb.add("dano", StatMod.Kind.INCREASED, 0.2)
	sb.add("dano", StatMod.Kind.INCREASED, 0.3)
	check(approx(sb.get_value("dano"), 22.5), "StatBlock: (10+5)*(1+0.5)=22.5")
	sb.add("dano", StatMod.Kind.MORE, 0.5)
	sb.add("dano", StatMod.Kind.MORE, 0.2)
	check(approx(sb.get_value("dano"), 40.5), "StatBlock: × 1.5 × 1.2 = 40.5")
	# tags
	sb.add("dano", StatMod.Kind.INCREASED, 1.0, PackedStringArray(["fogo"]), "fogo_src")
	check(approx(sb.get_value("dano", PackedStringArray(["ataque"])), 40.5), "StatBlock: mod de fogo não vale em ataque")
	var with_fire: float = sb.get_value("dano", PackedStringArray(["ataque", "fogo"]))
	check(approx(with_fire, (15.0 * 2.5) * 1.8), "StatBlock: mod de fogo vale com tag fogo")
	check(sb.remove_source("fogo_src") == 1, "StatBlock: remove por fonte")
	check(approx(sb.get_value("dano", PackedStringArray(["fogo"])), 40.5), "StatBlock: após remover volta ao normal")
	# cache
	sb.get_value("dano")
	var before: int = sb.recompute_count
	sb.get_value("dano")
	sb.get_value("dano")
	check(sb.recompute_count == before, "StatBlock: cache evita recálculo")
	sb.add("dano", StatMod.Kind.FLAT, 1.0)
	sb.get_value("dano")
	check(sb.recompute_count == before + 1, "StatBlock: cache invalidado ao mudar")
	# nunca negativo
	var neg: StatBlock = StatBlock.new()
	neg.set_base("x", 5.0)
	neg.add("x", StatMod.Kind.FLAT, -100.0)
	check(neg.get_value("x") == 0.0, "StatBlock: valor final nunca negativo")
	neg.add("x", StatMod.Kind.INCREASED, -5.0)
	check(neg.get_value("x") >= 0.0, "StatBlock: aumentado muito negativo não inverte sinal")
	check(Rules.clamp_cooldown(0.0) == 0.1 and Rules.clamp_cooldown(-3.0) == 0.1, "Recarga mínima 0,1 s")


# ------------------------------------------------------------------ DamageCalc

func test_damage_calc() -> void:
	var rng: RandomNumberGenerator = RandomNumberGenerator.new()
	rng.seed = 1
	var atk: Combatant = make_combatant({"damage": 100.0, "crit_chance": 0.0, "crit_multiplier": 150.0})
	var dummy: Combatant = make_combatant({})
	var r: HitResult = DamageCalc.resolve(atk, dummy, spec(1.5), rng)
	check(approx(r.final_damage, 150.0), "Dano: base × coeficiente = 150")
	check(not r.crit, "Dano: sem crítico com 0%")

	# Planos entram depois do coeficiente
	atk.stats.add("damage", StatMod.Kind.FLAT, 50.0)
	r = DamageCalc.resolve(atk, dummy, spec(1.5), rng)
	check(approx(r.final_damage, 200.0), "Dano: (100×1.5 + 50) = 200")
	atk.stats.remove_source("")

	# Crítico determinístico por seed
	var crit_atk: Combatant = make_combatant({"damage": 100.0, "crit_chance": 50.0, "crit_multiplier": 150.0})
	var rng_a: RandomNumberGenerator = RandomNumberGenerator.new()
	var rng_b: RandomNumberGenerator = RandomNumberGenerator.new()
	rng_a.seed = 777
	rng_b.seed = 777
	var seq_a: Array[bool] = []
	var seq_b: Array[bool] = []
	for i in range(40):
		seq_a.append(DamageCalc.resolve(crit_atk, dummy, spec(), rng_a).crit)
		seq_b.append(DamageCalc.resolve(crit_atk, dummy, spec(), rng_b).crit)
	check(seq_a == seq_b, "Crítico: mesma seed => mesma sequência")
	check(seq_a.has(true) and seq_a.has(false), "Crítico: 50% produz ambos os resultados")
	var always: Combatant = make_combatant({"damage": 100.0, "crit_chance": 100.0, "crit_multiplier": 150.0})
	r = DamageCalc.resolve(always, dummy, spec(), rng)
	check(r.crit and approx(r.final_damage, 150.0), "Crítico: 100% causa ×1.5")

	# Ordem: crítico ANTES da armadura
	var armoured: Combatant = make_combatant({"armour": 100.0})
	r = DamageCalc.resolve(always, armoured, spec(), rng)
	var expect: float = 150.0 * (1.0 - 100.0 / (100.0 + 5.0 * 150.0))
	check(approx(r.final_damage, expect), "Ordem: crítico antes da armadura (%.2f)" % expect)
	check(r.after_mods <= r.after_crit and r.after_armour <= r.after_crit, "Ordem: etapas monotônicas")

	# Armadura só físico e reduz menos golpes grandes
	var small: HitResult = DamageCalc.resolve(atk_with(10.0), armoured, spec(), rng)
	var big: HitResult = DamageCalc.resolve(atk_with(1000.0), armoured, spec(), rng)
	check(approx(small.final_damage / 10.0, 1.0 - 100.0 / 150.0, 0.001), "Armadura: golpe pequeno (redução 100/150)")
	check(big.final_damage / 1000.0 > small.final_damage / 10.0, "Armadura: reduz menos golpes grandes")
	var fire_hit: HitResult = DamageCalc.resolve(atk_with(100.0), armoured, spec(1.0, PackedStringArray(["ataque", "fogo"]), 1), rng)
	check(approx(fire_hit.final_damage, 100.0), "Armadura não afeta dano elemental")

	# Resistência com teto 75%
	var resist: Combatant = make_combatant({"res_fire": 200.0})
	r = DamageCalc.resolve(atk_with(100.0), resist, spec(1.0, PackedStringArray(["fogo"]), 1), rng)
	check(approx(r.final_damage, 25.0), "Resistência: teto de 75%")
	var res_cold: Combatant = make_combatant({"res_fire": 75.0})
	r = DamageCalc.resolve(atk_with(100.0), res_cold, spec(1.0, PackedStringArray(["frio"]), 2), rng)
	check(approx(r.final_damage, 100.0), "Resistência a fogo não vale contra frio")

	# Evasão (só ataques, teto 70%)
	var evader: Combatant = make_combatant({"evasion": 500.0})
	var r_ev: RandomNumberGenerator = RandomNumberGenerator.new()
	r_ev.seed = 99
	var evaded: int = 0
	var trials: int = 4000
	for i in range(trials):
		if DamageCalc.resolve(atk_with(10.0), evader, spec(), r_ev).evaded:
			evaded += 1
	var ev_rate: float = float(evaded) / float(trials)
	check(ev_rate > 0.66 and ev_rate < 0.74, "Evasão: teto 70%% (obtido %.3f)" % ev_rate)
	var spell_ev: int = 0
	for i in range(500):
		if DamageCalc.resolve(atk_with(10.0), evader, spec(1.0, PackedStringArray(["feitiço"]), 0, false), r_ev).evaded:
			spell_ev += 1
	check(spell_ev == 0, "Evasão: não vale contra feitiços")

	# Bloqueio (teto 50%)
	var blocker: Combatant = make_combatant({"block": 400.0, "block_reduction": 100.0})
	var r_bl: RandomNumberGenerator = RandomNumberGenerator.new()
	r_bl.seed = 5
	var blocked: int = 0
	for i in range(trials):
		if DamageCalc.resolve(atk_with(10.0), blocker, spec(), r_bl).blocked:
			blocked += 1
	var bl_rate: float = float(blocked) / float(trials)
	check(bl_rate > 0.46 and bl_rate < 0.54, "Bloqueio: teto 50%% (obtido %.3f)" % bl_rate)

	# Barreira e vida
	var shielded: Combatant = make_combatant({"max_life": 200.0})
	shielded.barrier = 30.0
	r = DamageCalc.resolve(atk_with(100.0), shielded, spec(), rng)
	check(approx(r.barrier_absorbed, 30.0) and approx(r.life_damage, 70.0), "Barreira absorve antes da vida")
	shielded.take(r)
	check(approx(shielded.life, 130.0) and shielded.barrier == 0.0, "Combatant.take aplica barreira e vida")
	var tiny: Combatant = make_combatant({"max_life": 10.0})
	tiny.take(DamageCalc.resolve(atk_with(500.0), tiny, spec(), rng))
	check(tiny.life == 0.0 and tiny.is_dead(), "Vida nunca fica negativa")

	# Escudo frontal
	var boss: Combatant = make_combatant({})
	boss.frontal_shield_reduction = 80.0
	boss.shield_arc_degrees = 140.0
	var front: HitSpec = spec()
	front.from_front = true
	r = DamageCalc.resolve(atk_with(100.0), boss, front, rng)
	check(approx(r.final_damage, 20.0) and r.shield_reduced, "Escudo frontal reduz golpe da frente")
	var back: HitSpec = spec()
	back.from_front = false
	r = DamageCalc.resolve(atk_with(100.0), boss, back, rng)
	check(approx(r.final_damage, 100.0), "Golpe por trás ignora o escudo")
	boss.guard.configure(100.0, 2.0, 5.0)
	boss.guard.add(100.0)
	r = DamageCalc.resolve(atk_with(100.0), boss, front, rng)
	check(approx(r.final_damage, 100.0), "Guarda quebrada ignora o escudo")

	# Invulnerável
	var inv: Combatant = make_combatant({})
	inv.invulnerable = true
	r = DamageCalc.resolve(atk_with(100.0), inv, spec(), rng)
	check(r.invulnerable and r.final_damage == 0.0, "Invulnerável não sofre dano")

	# Nada negativo
	var weird: Combatant = make_combatant({"armour": 99999.0, "res_fire": -50.0})
	var vals: Array[float] = []
	r = DamageCalc.resolve(atk_with(0.0), weird, spec(), rng)
	vals.append_array([r.base_damage, r.after_mods, r.after_crit, r.after_block, r.after_shield, r.after_armour, r.after_resist, r.final_damage, r.life_damage, r.barrier_absorbed])
	var all_pos: bool = true
	for v in vals:
		if v < 0.0:
			all_pos = false
	check(all_pos, "Resultado do golpe nunca tem valores negativos")


func atk_with(dmg: float) -> Combatant:
	return make_combatant({"damage": dmg, "crit_chance": 0.0})


# ------------------------------------------------------------------ efeitos e gatilhos

func test_effects_triggers() -> void:
	var stats: StatBlock = StatBlock.new()
	stats.set_base("dano", 100.0)
	var fx: EffectSet = EffectSet.new(stats)

	var refresh: EffectData = EffectData.new()
	refresh.id = "effect.t_refresh"
	refresh.duration = 2.0
	refresh.stack_rule = EffectData.StackRule.REFRESH
	check(fx.apply(refresh), "Efeito: aplica")
	fx.update(1.5)
	check(approx(fx.remaining_of("effect.t_refresh"), 0.5), "Efeito: contagem regressiva")
	fx.apply(refresh)
	check(approx(fx.remaining_of("effect.t_refresh"), 2.0) and fx.stacks_of("effect.t_refresh") == 1, "Efeito: renovar reinicia sem acumular")
	fx.update(2.1)
	check(not fx.has("effect.t_refresh"), "Efeito: expira")

	var stack: EffectData = EffectData.new()
	stack.id = "effect.t_stack"
	stack.duration = 5.0
	stack.stack_rule = EffectData.StackRule.STACK
	stack.max_stacks = 3
	stack.stat = "dano"
	stack.mod_kind = StatMod.Kind.INCREASED
	stack.magnitude = 0.1
	for i in range(5):
		fx.apply(stack)
	check(fx.stacks_of("effect.t_stack") == 3, "Efeito: acumula até o máximo (3)")
	check(approx(stats.get_value("dano"), 130.0), "Efeito: modificador escala com acúmulos (+30%)")
	fx.update(6.0)
	check(approx(stats.get_value("dano"), 100.0), "Efeito: modificador some ao expirar")

	var strong: EffectData = EffectData.new()
	strong.id = "effect.t_strong"
	strong.duration = 4.0
	strong.stack_rule = EffectData.StackRule.STRONGEST
	fx.apply(strong, 2.0)
	check(not fx.apply(strong, 1.0), "Efeito: mais forte ignora o mais fraco")
	check(fx.apply(strong, 3.0), "Efeito: mais forte substitui o mais fraco")

	# Tick de dano
	var burn: EffectData = DataDB.get_effect("effect.burn")
	var victim: Combatant = make_combatant({"max_life": 100.0})
	victim.effects.apply(burn)
	for i in range(60):
		victim.update(0.05)
	check(approx(victim.life, 76.0, 1.5), "Efeito: queimadura causa dano periódico (vida %.1f)" % victim.life)

	# Gatilhos com recarga interna mínima de 0,25 s
	var ts: TriggerSet = TriggerSet.new()
	var counter: Array[int] = [0]
	ts.add("t", "on_hit", func(_ctx: Dictionary) -> void: counter[0] += 1, 0.0)
	check(ts.fire("on_hit") == 1, "Gatilho: dispara")
	check(ts.fire("on_hit") == 0, "Gatilho: recarga interna impede repetir")
	ts.update(0.2)
	check(ts.fire("on_hit") == 0, "Gatilho: 0,2 s ainda < 0,25 s mínimo")
	ts.update(0.1)
	check(ts.fire("on_hit") == 1, "Gatilho: dispara após 0,25 s")
	check(counter[0] == 2, "Gatilho: callback executado 2 vezes")


func test_guard_and_pool() -> void:
	var g: GuardMeter = GuardMeter.new()
	g.configure(100.0, 2.0, 10.0)
	check(not g.add(60.0), "Guarda: acumula sem quebrar")
	check(g.add(50.0) and g.is_broken(), "Guarda: quebra ao encher")
	check(not g.add(50.0), "Guarda: não acumula enquanto quebrada")
	g.update(2.1)
	check(not g.is_broken(), "Guarda: recupera após a duração")
	g.add(50.0)
	g.update(5.0)
	check(g.current < 50.0, "Guarda: decai com o tempo")
	var p: ResourcePool = ResourcePool.new(100.0, 3.0, 10.0)
	p.gain(150.0)
	check(p.current == 100.0, "Ímpeto: limitado ao máximo")
	check(p.spend(30.0) and p.current == 70.0 and not p.spend(80.0), "Ímpeto: gasta e recusa se insuficiente")
	p.update(2.0)
	check(p.current == 70.0, "Ímpeto: não decai antes do atraso")
	p.update(2.0)
	check(p.current < 70.0, "Ímpeto: esvazia fora de combate")


# ------------------------------------------------------------------ RNG

func test_rng() -> void:
	var a: RngStreams = RngStreams.new(1234)
	var b: RngStreams = RngStreams.new(1234)
	var same: bool = true
	for i in range(20):
		if a.stream(RngStreams.COMBAT).randf() != b.stream(RngStreams.COMBAT).randf():
			same = false
	check(same, "RNG: mesma seed => mesma sequência de combate")
	var c: RngStreams = RngStreams.new(1234)
	var d: RngStreams = RngStreams.new(1234)
	for i in range(50):
		c.stream(RngStreams.LOOT).randf()
	check(c.stream(RngStreams.COMBAT).randf() == d.stream(RngStreams.COMBAT).randf(), "RNG: consumir 'saque' não altera 'combate'")
	var e: RngStreams = RngStreams.new(1234)
	check(e.stream(RngStreams.COMBAT).randf() != RngStreams.new(1234).stream(RngStreams.EVENTS).randf(), "RNG: fluxos diferentes divergem")
	check(RngStreams.derive_seed(1, "x", 0) != RngStreams.derive_seed(1, "x", 1), "RNG: índice altera a seed")
	check(RngStreams.derive_seed(1, "x", 0) != RngStreams.derive_seed(2, "x", 0), "RNG: seed altera o fluxo")


# ------------------------------------------------------------------ dados

func test_data() -> void:
	DataDB.reload()
	check(DataDB.load_errors.is_empty(), "Dados: todos os .tres carregam %s" % str(DataDB.load_errors))
	check(DataDB.duplicate_ids.is_empty(), "Dados: IDs únicos %s" % str(DataDB.duplicate_ids))
	var needed: PackedStringArray = [
		"class.warrior", "skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.shield_bash",
		"skill.warrior.stone_rift", "enemy.hollow_sentinel", "enemy.crypt_guardian", "effect.burn", "encounter.crypt",
	]
	for id in needed:
		check(DataDB.get_res(id) != null, "Dados: existe %s" % id)
	for res in DataDB.all_resources():
		var problems: PackedStringArray = PackedStringArray()
		if res is SkillData:
			problems = (res as SkillData).validate()
		elif res is ClassData:
			problems = (res as ClassData).validate()
		elif res is EnemyData:
			problems = (res as EnemyData).validate()
		elif res is EffectData:
			problems = (res as EffectData).validate()
		elif res is EncounterData:
			problems = (res as EncounterData).validate()
		check(problems.is_empty(), "Dados: validação %s %s" % [str(res.get("id")), str(problems)])
	var w: ClassData = DataDB.get_hero("class.warrior")
	for sid in w.skill_ids:
		check(DataDB.get_skill(sid) != null, "Dados: guerreiro referencia %s" % sid)
	var cut: SkillData = DataDB.get_skill("skill.warrior.iron_cut")
	check(cut.total_time() >= 0.4 and cut.total_time() <= 0.6, "Corte de Ferro dura 0,4–0,6 s")
	var rift: SkillData = DataDB.get_skill("skill.warrior.stone_rift")
	check(rift.windup >= 0.8 and rift.windup <= 1.2, "Fenda de Pedra: preparação 0,8–1,2 s")
	check(w.dodge_duration == 0.35 and w.dodge_invuln == 0.2 and w.dodge_charges == 3 and w.dodge_recharge == 1.5, "Esquiva: 0,35 s / 0,2 s / 3 cargas / 1,5 s")
	var g: EnemyData = DataDB.get_enemy("enemy.crypt_guardian")
	check(g.attack_windup >= 0.7 and g.attack_windup <= 1.2 and g.is_boss, "Guardião: telegraph 0,7–1,2 s")
	check(g.phase2_threshold == 0.5 and g.summon_count == 2, "Guardião: fase 2 em 50% invoca 2")
	var enc: EncounterData = DataDB.get_encounter("encounter.crypt")
	check(enc.waves[0] == 3 and enc.waves[1] == 4, "Encontro: ondas de 3 e 4")


func test_input_actions() -> void:
	var acts: PackedStringArray = ["move_up", "move_down", "move_left", "move_right", "attack_basic", "skill_1", "skill_2", "skill_3", "skill_4", "skill_5", "dodge", "potion_1", "potion_2"]
	for a in acts:
		check(InputMap.has_action(a), "Input: ação %s registrada" % a)


# ------------------------------------------------------------------ fumaça

func _start_smoke() -> void:
	var packed: PackedScene = load("res://scenes/crypt.tscn")
	check(packed != null, "Fumaça: cena da Cripta carrega")
	if packed == null:
		_finish()
		return
	_crypt = packed.instantiate()
	root.add_child(_crypt)
	print("Teste de fumaça: %d frames de física..." % SMOKE_FRAMES)


func _physics_process(_delta: float) -> bool:
	if _crypt == null or _smoke_done:
		return false
	_frames += 1
	var player: Node2D = _crypt.get("player") as Node2D
	if player == null:
		return false
	if _frames == BOSS_FRAME:
		_crypt.call("debug_start_boss")
	_bot(player)
	if _frames >= SMOKE_FRAMES:
		_smoke_done = true
		_finish()
		return true
	return false


func _bot(player: Node2D) -> void:
	for a in ["move_up", "move_down", "move_left", "move_right", "attack_basic", "skill_1", "skill_2", "skill_3", "dodge"]:
		Input.action_release(a)
	if bool(player.call("is_dead")):
		return
	var target: Node2D = null
	var best: float = INF
	for n in get_nodes_in_group("enemies"):
		var e: Node2D = n as Node2D
		if e == null or bool(e.call("is_dying")):
			continue
		var d: float = e.global_position.distance_to(player.global_position)
		if d < best:
			best = d
			target = e
	if target == null:
		# Sem inimigos: anda para a direita.
		Input.action_press("move_right")
		player.set("aim_override", player.global_position + Vector2(100, 0))
		return
	player.set("aim_override", target.global_position)
	var dir: Vector2 = target.global_position - player.global_position
	if best > 50.0:
		if dir.x > 6.0:
			Input.action_press("move_right")
		elif dir.x < -6.0:
			Input.action_press("move_left")
		if dir.y > 6.0:
			Input.action_press("move_down")
		elif dir.y < -6.0:
			Input.action_press("move_up")
	Input.action_press("attack_basic")
	var f: int = _frames % 120
	if f == 10 and best < 200.0:
		Input.action_press("skill_1")
	elif f == 40 and best < 70.0:
		Input.action_press("skill_2")
	elif f == 70 and best < 200.0:
		Input.action_press("skill_3")
	elif f == 100:
		Input.action_press("dodge")


func _finish() -> void:
	for a in ["move_up", "move_down", "move_left", "move_right", "attack_basic", "skill_1", "skill_2", "skill_3", "dodge"]:
		Input.action_release(a)
	if _crypt != null:
		var stage: int = int(_crypt.get("stage"))
		print("Fumaça: estágio final=%d, frames=%d" % [stage, _frames])
	check(_catcher.errors.is_empty(), "Fumaça: nenhum erro/push_error durante a execução")
	for e in _catcher.errors:
		print("  erro capturado: ", e)
	OS.remove_logger(_catcher)
	print("== Resultado: %d ok, %d falhas ==" % [_pass, _fail])
	quit(1 if _fail > 0 else 0)
