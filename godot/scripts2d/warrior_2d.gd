extends "res://scripts2d/actor_2d.gd"
## Guerreiro 2D: combo de espada em 3 golpes, esquiva e até 4 habilidades ativas da árvore comum (habilidades_2d.gd).
## Números em data2d/guerreiro.csv e data2d/habilidades_guerreiro.csv; custo das ativas é ímpeto, não mana. Mesma interface do player_2d.gd (arqueiro).

signal died
signal hp_changed(hp: float, hp_max: float)

const Csv = preload("res://scripts2d/csv2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")
const Efeitos = preload("res://scripts2d/efeitos_guerreiro_2d.gd")
const HabilidadesScript = preload("res://scripts2d/habilidades_2d.gd")

enum Estado { LIVRE, ATACANDO, CONJURANDO, INVESTIDA, SALTO, ESQUIVA, MORTO }

const TECLAS_SKILL := {"skill_1": KEY_Q, "skill_2": KEY_E, "skill_3": KEY_F, "skill_4": KEY_R}
const COR_LAMINA := Color(0.95, 0.92, 0.8)
const COR_FOGO := Color(1.0, 0.55, 0.2)
const COR_ESCUDO := Color(0.35, 0.65, 0.95)
const COR_FURIA := Color(0.9, 0.25, 0.2)

var stats := {}
var hp := 0.0
var estado := Estado.LIVRE
var invencivel := 0.0
var god_mode := false          # testes automáticos
var auto_aim := Vector2.ZERO   # testes: mira forçada (e ataque contínuo)
var auto_move := Vector2.ZERO  # testes: movimento forçado
var dodge_cd := 0.0
var habilidades: RefCounted    # árvore e slots (habilidades_2d.gd); recargas das ativas ficam em habilidades.recargas
var impeto := 0.0
var guardando := false
var combo := 0
var _aim := Vector2.DOWN
var _atk_cd := 0.0
var _combo_t := 0.0
var _golpeou := false
var _dodge_t := 0.0
var _dodge_dir := Vector2.DOWN
var _cast := {}                # conjuração em curso: id, espera, resta, aplicou
var _dash_t := 0.0
var _dash := {}                # investida/salto em curso: def, nivel, mira, hit
var _furia_taxa := 0.0
var _salto_t := 0.0
var _salto_total := 0.0
var _buff_cry := 0.0
var _buff_cry_dano := 0.0
var _buff_furia := 0.0
var _sem_dano := 0.0
var _sem_acerto := 0.0
var _guarda_ativa_antes := false
var _resistiu := false         # Última Resistência já usada nesta corrida
var _fx: Array = []            # efeitos visuais: {tipo, ang, r, arco, t, dur, cor, comp, larg}

func _ready() -> void:
	stats = Csv.kv("res://data2d/guerreiro.csv")
	_registrar_acoes()
	if habilidades == null:
		habilidades = HabilidadesScript.new()
		habilidades.carregar_classe("guerreiro")
	collision_layer = 2
	collision_mask = 1 | 8
	add_to_group("guerreiro")
	setup_sprite("guerreiro")
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = stats["radius"]
	cs.shape = sh
	add_child(cs)
	reset()

static func _registrar_acoes() -> void:
	for a in TECLAS_SKILL:
		if not InputMap.has_action(a):
			InputMap.add_action(a)
			var ev := InputEventKey.new()
			ev.physical_keycode = TECLAS_SKILL[a]
			InputMap.action_add_event(a, ev)

func reset() -> void:
	hp = stats["hp_max"]
	estado = Estado.LIVRE
	invencivel = 0.0
	dodge_cd = 0.0
	impeto = 0.0
	guardando = false
	combo = 0
	_atk_cd = 0.0
	_combo_t = 0.0
	habilidades.limpar_recargas()
	_cast = {}
	_dash = {}
	_buff_cry = 0.0
	_buff_furia = 0.0
	_fx.clear()
	_sem_dano = 0.0
	_sem_acerto = 0.0
	_resistiu = false
	velocity = Vector2.ZERO
	modulate = Color.WHITE
	if sprite != null:
		sprite.position = Vector2.ZERO
		sprite.speed_scale = 1.0
	play("idle", true)
	hp_changed.emit(hp, stats["hp_max"])

# ---------------------------------------------------------------- laço principal

func _physics_process(delta: float) -> void:
	if estado == Estado.MORTO:
		velocity = Vector2.ZERO
		return
	_tick(delta)
	_aim = _ler_mira()
	var entrada := auto_move if auto_move != Vector2.ZERO else Input.get_vector("move_left", "move_right", "move_up", "move_down")
	match estado:
		Estado.ESQUIVA:
			_dodge_t -= delta
			velocity = _dodge_dir * stats["dodge_speed"]
			if _dodge_t <= 0.0:
				estado = Estado.LIVRE
		Estado.INVESTIDA:
			_dash_t -= delta
			velocity = _dash["mira"] * _investida_vel()
			_investida_acertar()
			if _dash_t <= 0.0:
				estado = Estado.LIVRE
		Estado.SALTO:
			_salto_t -= delta
			var k := clampf(1.0 - _salto_t / maxf(_salto_total, 0.01), 0.0, 1.0)
			sprite.position.y = -sin(PI * k) * 46.0
			if _salto_t <= 0.0:
				sprite.position.y = 0.0
				_pousar()
		Estado.CONJURANDO:
			velocity = velocity.move_toward(Vector2.ZERO, stats["friction"] * delta)
			_conjurar_passo(delta)
		_:
			var vmax: float = _velocidade()
			if estado == Estado.ATACANDO:
				vmax *= stats["attack_move_mult"]
			elif guardando:
				vmax *= stats["guard_move_mult"]
			var alvo_v := entrada * vmax
			var taxa: float = stats["accel"] if entrada != Vector2.ZERO else stats["friction"]
			velocity = velocity.move_toward(alvo_v, taxa * delta)
			if estado == Estado.LIVRE:
				_decidir_acao(entrada)
	move_and_slide()
	_animar(entrada)

func _tick(delta: float) -> void:
	_atk_cd = maxf(0.0, _atk_cd - delta)
	dodge_cd = maxf(0.0, dodge_cd - delta)
	invencivel = maxf(0.0, invencivel - delta)
	_combo_t = maxf(0.0, _combo_t - delta)
	_buff_cry = maxf(0.0, _buff_cry - delta)
	_buff_furia = maxf(0.0, _buff_furia - delta)
	_sem_dano += delta
	_sem_acerto += delta
	habilidades.tick(delta)
	if _sem_acerto > stats["impeto_decay_delay"]:
		impeto = maxf(0.0, impeto - stats["impeto_decay"] * delta)
	if stats["regen"] > 0.0 and _sem_dano >= stats["regen_delay"] and hp < stats["hp_max"]:
		hp = minf(stats["hp_max"], hp + stats["regen"] * delta)
		hp_changed.emit(hp, stats["hp_max"])
	for f in _fx:
		f["t"] -= delta
	_fx = _fx.filter(func(f): return f["t"] > 0.0)

func _decidir_acao(entrada: Vector2) -> void:
	var guarda_id := _slot_de("w_guard_stance")
	var guarda_tecla := guarda_id != "" and Input.is_action_pressed("skill_%d" % (_indice_slot(guarda_id) + 1))
	guardando = guarda_tecla and _cd(guarda_id) <= 0.0
	if not guardando and guarda_id != "" and _cd(guarda_id) <= 0.0 and _guarda_ativa_antes:
		_iniciar_recarga(guarda_id)
	_guarda_ativa_antes = guardando
	if Input.is_action_just_pressed("dodge") and dodge_cd <= 0.0:
		guardando = false
		_comecar_esquiva(entrada if entrada != Vector2.ZERO else _aim)
		return
	if guardando:
		facing = _aim
		return
	if habilidades != null:
		for i in mini(habilidades.slots.size(), TECLAS_SKILL.size()):
			var id: String = habilidades.slots[i]
			if id != "" and id != "w_guard_stance" and Input.is_action_just_pressed("skill_%d" % (i + 1)):
				if usar(id):
					return
	if _quer_atacar() and _atk_cd <= 0.0:
		_comecar_golpe()

func _quer_atacar() -> bool:
	return Input.is_action_pressed("shoot") or auto_aim != Vector2.ZERO

func _ler_mira() -> Vector2:
	if auto_aim != Vector2.ZERO:
		return auto_aim.normalized()
	var stick := Input.get_vector("aim_left", "aim_right", "aim_up", "aim_down")
	if stick.length() > 0.3:
		return stick.normalized()
	var d := get_global_mouse_position() - global_position
	return d.normalized() if d.length() > 4.0 else _aim

func _velocidade() -> float:
	var v: float = stats["speed"]
	if _buff_furia > 0.0:
		v *= 1.2
	return v

func _taxa_ataque() -> float:
	var r := 1.0
	if _buff_cry > 0.0:
		r += 0.15
	if _buff_furia > 0.0:
		r += _furia_taxa
	return r

# ---------------------------------------------------------------- combo básico

func _comecar_golpe() -> void:
	estado = Estado.ATACANDO
	combo = (combo % 3) + 1 if _combo_t > 0.0 else 1
	_combo_t = stats["combo_window"]
	var taxa := _taxa_ataque()
	_atk_cd = stats["attack_cooldown"] * (1.4 if combo == 3 else 1.0) / taxa
	_golpeou = false
	facing = _aim
	sprite.speed_scale = taxa
	play("attack", true)

func _on_frame_changed() -> void:
	if estado != Estado.ATACANDO or anim_base() != "attack" or _golpeou:
		return
	if sprite.frame >= evento("attack"):
		_golpeou = true
		_golpe_basico()

func _golpe_basico() -> void:
	var mult := 1.0
	var arco: float = stats["attack_arc"]
	if combo == 2:
		mult = stats["combo2_mult"]
	elif combo == 3:
		mult = stats["combo3_mult"]
		arco *= stats["combo3_arc_mult"]
	var alcance: float = stats["attack_range"]
	var alvos := alvos_cone(global_position, _aim, alcance, arco)
	for a in alvos:
		acertar(a, mult)
	_fx.append({"tipo": "arco", "ang": _aim.angle(), "r": alcance, "arco": deg_to_rad(arco), "t": 0.16, "dur": 0.16, "cor": COR_LAMINA if combo < 3 else COR_FOGO})
	velocity += _aim * stats["combo_lunge"]
	Audio.tocar("shoot")
	var c := Feel.cfg()
	Feel.shake(self, c["shake_shot_amp"] * (2.0 if combo == 3 else 1.0), c["shake_shot_time"])

func _on_anim_finished() -> void:
	if estado == Estado.ATACANDO:
		estado = Estado.LIVRE
		sprite.speed_scale = 1.0

# ---------------------------------------------------------------- habilidades ativas

func _slot_de(id: String) -> String:
	return id if habilidades != null and habilidades.nivel(id) > 0 and habilidades.slots.has(id) else ""

func _indice_slot(id: String) -> int:
	return habilidades.slots.find(id) if habilidades != null else -1

func _cd(id: String) -> float:
	return habilidades.recargas.get(id, 0.0)

## Fração 0..1 da recarga da ativa `id` (0 = pronta).
func recarga_skill(id: String) -> float:
	if habilidades == null or habilidades.nivel(id) <= 0:
		return 0.0
	return clampf(_cd(id) / maxf(habilidades.defs[id]["cd"] * _cd_mult(), 0.01), 0.0, 1.0)

func _cd_mult() -> float:
	return stats.get("skill_cd_mult", 1.0)

## A recarga é do core (habilidades_2d.gd); o ímpeto já foi conferido e gasto aqui, então o recurso passado só precisa cobrir o custo.
func _iniciar_recarga(id: String) -> void:
	habilidades.iniciar_recarga(id, INF)

## Usa a ativa `id` se estiver aprendida, pronta e o jogador livre. Retorna se começou.
func usar(id: String) -> bool:
	if habilidades == null or habilidades.nivel(id) <= 0 or not habilidades.defs.has(id) or estado != Estado.LIVRE:
		return false
	var d: Dictionary = habilidades.def_nivel(id)
	if _cd(id) > 0.0 or d["efeito"] == "postura_guarda" or d["custo"] > impeto:
		return false
	if not Efeitos.executar(d["efeito"], self, d, habilidades.nivel(id), _aim):
		return false
	impeto -= d["custo"]
	_iniciar_recarga(id)
	facing = _aim
	return true

func comecar_conjuracao(efeito: String, d: Dictionary, mira: Vector2, nivel: int) -> void:
	_cast = {"efeito": efeito, "def": d, "nivel": nivel, "mira": mira, "espera": d["espera"], "resta": d["espera"] + d["recup"], "aplicou": false}
	estado = Estado.CONJURANDO
	sprite.speed_scale = 1.0
	play("attack", true)

func _conjurar_passo(delta: float) -> void:
	_cast["resta"] -= delta
	_cast["espera"] -= delta
	if not _cast["aplicou"] and _cast["espera"] <= 0.0:
		_cast["aplicou"] = true
		Efeitos.aplicar(_cast["efeito"], self, _cast["def"], _cast["nivel"], _cast["mira"])
	if _cast["resta"] <= 0.0:
		_cast = {}
		estado = Estado.LIVRE

func buff_grito(duracao: float, dano: float) -> void:
	_buff_cry = duracao
	_buff_cry_dano = dano

func buff_furia(duracao: float, taxa: float) -> void:
	_buff_furia = duracao
	_furia_taxa = taxa

# ---------------------------------------------------------------- investida e salto

func comecar_investida(d: Dictionary, mira: Vector2, nivel: int) -> void:
	estado = Estado.INVESTIDA
	_dash = {"def": d, "nivel": nivel, "mira": mira, "hit": {}}
	_dash_t = d["duracao"]
	invencivel = maxf(invencivel, d["duracao"])
	play("dodge", true)
	Audio.tocar("dodge")

func _investida_vel() -> float:
	var d: Dictionary = _dash["def"]
	return d["alcance"] / maxf(d["duracao"], 0.01)

func _investida_acertar() -> void:
	var d: Dictionary = _dash["def"]
	for a in get_tree().get_nodes_in_group("hurtable"):
		if _dash["hit"].has(a) or global_position.distance_to(a.global_position) > 44.0:
			continue
		_dash["hit"][a] = true
		acertar(a, d["dano"], 0.5)
		Efeitos.aplicar("investida", self, d, _dash["nivel"], _dash["mira"])

func comecar_salto(d: Dictionary, mira: Vector2, nivel: int) -> void:
	estado = Estado.SALTO
	_dash = {"def": d, "nivel": nivel, "mira": mira}
	_salto_total = d["duracao"]
	_salto_t = d["duracao"]
	invencivel = maxf(invencivel, d["duracao"] + 0.1)
	velocity = mira * (d["alcance"] / maxf(d["duracao"], 0.01))
	play("dodge", true)

func _pousar() -> void:
	estado = Estado.LIVRE
	velocity = Vector2.ZERO
	Efeitos.aplicar("salto_sismico", self, _dash["def"], _dash["nivel"], _dash["mira"])
	Audio.tocar("hit_enemy")

# ---------------------------------------------------------------- esquiva

func _comecar_esquiva(dir: Vector2) -> void:
	estado = Estado.ESQUIVA
	_dodge_dir = dir.normalized()
	_dodge_t = stats["dodge_time"]
	dodge_cd = stats["dodge_cooldown"]
	invencivel = maxf(invencivel, stats["dodge_time"])
	facing = _dodge_dir
	play("dodge", true)
	Audio.tocar("dodge")

# ---------------------------------------------------------------- acerto, dano e efeitos

func alvos_cone(origem: Vector2, dir: Vector2, alcance: float, arco_graus: float) -> Array:
	var out := []
	var meio := deg_to_rad(arco_graus) * 0.5
	for n in get_tree().get_nodes_in_group("hurtable"):
		var v: Vector2 = n.global_position - origem
		var raio_alvo: float = n.stats.get("radius", 14.0) if "stats" in n else 14.0
		var dist := v.length()
		if dist > alcance + raio_alvo:
			continue
		if arco_graus >= 359.0 or dist <= raio_alvo + 12.0 or absf(angle_difference(dir.angle(), v.angle())) <= meio:
			out.append(n)
	return out

func alvos_retangulo(origem: Vector2, dir: Vector2, comprimento: float, largura: float) -> Array:
	var out := []
	var lado := dir.orthogonal()
	for n in get_tree().get_nodes_in_group("hurtable"):
		var v: Vector2 = n.global_position - origem
		var frente := v.dot(dir)
		if frente >= -10.0 and frente <= comprimento and absf(v.dot(lado)) <= largura * 0.5:
			out.append(n)
	return out

func _lifesteal() -> float:
	return stats["lifesteal"] + (0.1 if _buff_furia > 0.0 else 0.0)

func _dano_para(alvo: Node, mult: float) -> float:
	var m: float = stats["damage"] * mult * (1.0 + impeto / maxf(stats["impeto_max"], 1.0) * stats["impeto_damage"])
	if _buff_cry > 0.0:
		m *= 1.0 + _buff_cry_dano
	if _buff_furia > 0.0:
		m *= 1.3
	if stats["exec_bonus"] > 0.0 and "hp" in alvo and "hp_max" in alvo and alvo.hp_max > 0.0 \
			and alvo.hp / alvo.hp_max <= stats["exec_threshold"]:
		m *= 1.0 + stats["exec_bonus"]
	return m

## Aplica um golpe: dano com todos os bônus, ímpeto, roubo de vida, queimadura e atordoamento.
func acertar(alvo: Node, mult: float, stun := 0.0, _forte := false) -> void:
	if not is_instance_valid(alvo) or not alvo.is_in_group("hurtable"):
		return
	var dano := _dano_para(alvo, mult)
	alvo.take_damage(dano, global_position)
	_sem_acerto = 0.0
	impeto = minf(stats["impeto_max"], impeto + stats["impeto_gain"])
	var ls := _lifesteal()
	if ls > 0.0:
		curar(dano * ls)
	aplicar_status(alvo, "atordoamento", stun)
	if stats["burn_dps"] > 0.0:
		aplicar_status(alvo, "queimadura", stats["burn_time"], stats["burn_dps"])

func curar(qtd: float) -> void:
	if qtd <= 0.0 or hp <= 0.0:
		return
	var antes := hp
	hp = minf(stats["hp_max"], hp + qtd)
	if hp > antes:
		hp_changed.emit(hp, stats["hp_max"])

## Status nos inimigos (API aplicar_status do inimigo: atordoamento, queimadura, marca, lentidão, veneno).
func aplicar_status(alvo: Node, tipo: String, dur: float, valor := 0.0) -> void:
	if dur > 0.0 and is_instance_valid(alvo) and alvo.has_method("aplicar_status"):
		alvo.aplicar_status(tipo, dur, valor)

func fx_arco(ang: float, r: float, arco: float, dur: float, cor: Color) -> void:
	_fx.append({"tipo": "arco", "ang": ang, "r": r, "arco": arco, "t": dur, "dur": dur, "cor": cor})

func fx_faixa(ang: float, comp: float, larg: float, dur: float, cor: Color) -> void:
	_fx.append({"tipo": "faixa", "ang": ang, "comp": comp, "larg": larg, "t": dur, "dur": dur, "cor": cor})

# ---------------------------------------------------------------- dano recebido

func esta_morto() -> bool:
	return estado == Estado.MORTO

func _na_guarda(origem: Vector2) -> bool:
	var v := origem - global_position
	return absf(angle_difference(_aim.angle(), v.angle())) <= deg_to_rad(stats["guard_arc"]) * 0.5

func take_damage(amount: float, origem := Vector2.ZERO) -> void:
	if estado == Estado.MORTO or invencivel > 0.0 or god_mode:
		return
	var final: float = amount * stats["damage_taken"]
	var bloqueou := false
	if guardando and origem != Vector2.ZERO and _na_guarda(origem):
		bloqueou = true
		final *= 1.0 - stats["guard_reduction"]
		impeto = minf(stats["impeto_max"], impeto + stats["guard_impeto"])
		_fx.append({"tipo": "arco", "ang": (origem - global_position).angle(), "r": 40.0, "arco": 1.2, "t": 0.18, "dur": 0.18, "cor": COR_ESCUDO})
	hp = maxf(0.0, hp - final)
	_sem_dano = 0.0
	invencivel = stats["hit_iframes"] * (0.5 if bloqueou else 1.0)
	flash()
	Audio.tocar("player_hurt")
	var c := Feel.cfg()
	Feel.hit_stop(c["hit_stop_player_ms"])
	Feel.shake(self, c["shake_player_amp"], c["shake_player_time"])
	Feel.numero(self, final, COR_ESCUDO if bloqueou else Color(1.0, 0.35, 0.3), true)
	if stats["revide"] > 0.0:
		_revidar()
	if hp <= 0.0 and stats["last_stand"] > 0.0 and not _resistiu:
		_resistiu = true
		hp = stats["hp_max"] * stats["last_stand_heal"] * stats["last_stand"]
		invencivel = stats["last_stand_time"] * stats["last_stand"]
		_fx.append({"tipo": "arco", "ang": 0.0, "r": 90.0, "arco": TAU, "t": 0.6, "dur": 0.6, "cor": COR_ESCUDO})
	hp_changed.emit(hp, stats["hp_max"])
	if hp <= 0.0:
		estado = Estado.MORTO
		guardando = false
		sprite.position = Vector2.ZERO
		play("death", true)
		died.emit()

## Pulso de Revide: machuca quem está perto quando o guerreiro é atingido.
func _revidar() -> void:
	for a in alvos_cone(global_position, _aim, stats["revide_radius"], 360.0):
		if is_instance_valid(a) and a.is_in_group("hurtable"):
			a.take_damage(stats["damage"] * stats["revide"], global_position)
	_fx.append({"tipo": "arco", "ang": 0.0, "r": stats["revide_radius"], "arco": TAU, "t": 0.25, "dur": 0.25, "cor": COR_FURIA})

# ---------------------------------------------------------------- HUD e animação

## Fração 0..1 da recarga do golpe básico (0 = pronto).
func recarga_tiro() -> float:
	return clampf(_atk_cd / maxf(stats["attack_cooldown"], 0.01), 0.0, 1.0)

## Barra do recurso (ímpeto), 0..1.
func recurso_frac() -> float:
	return clampf(impeto / maxf(stats["impeto_max"], 1.0), 0.0, 1.0)

## Slots da barra de habilidades: golpe, esquiva e as ativas aprendidas (tecla Q, E, F, R).
func slots_hud() -> Array:
	var out := [
		{"icone": "golpe", "tecla": "hud.key.shoot", "recarga": recarga_tiro()},
		{"icone": "esquiva", "tecla": "hud.key.dodge", "recarga": clampf(dodge_cd / stats["dodge_cooldown"], 0.0, 1.0)},
	]
	if habilidades != null:
		for i in habilidades.slots.size():
			var id: String = habilidades.slots[i]
			if id == "":
				continue
			out.append({"icone": id, "tecla": "hud.key.skill%d" % (i + 1), "recarga": recarga_skill(id)})
	return out

func _animar(entrada: Vector2) -> void:
	match estado:
		Estado.ATACANDO, Estado.ESQUIVA, Estado.CONJURANDO, Estado.INVESTIDA, Estado.SALTO:
			if estado == Estado.ATACANDO or estado == Estado.CONJURANDO:
				facing = _aim
		_:
			facing = _aim if _aim != Vector2.ZERO else facing
			play("run" if entrada != Vector2.ZERO else "idle")

func _draw() -> void:
	super._draw()
	var centro := Vector2(0, -30)
	if guardando:
		draw_arc(centro, 44.0, _aim.angle() - deg_to_rad(stats["guard_arc"]) * 0.5, _aim.angle() + deg_to_rad(stats["guard_arc"]) * 0.5, 20, COR_ESCUDO, 5.0)
	if _buff_furia > 0.0 or _buff_cry > 0.0:
		draw_arc(Vector2.ZERO, 22.0, 0.0, TAU, 24, COR_FURIA if _buff_furia > 0.0 else Color(1.0, 0.8, 0.3), 2.0)
	for f in _fx:
		var a: float = clampf(f["t"] / f["dur"], 0.0, 1.0)
		var cor: Color = f["cor"]
		cor.a = a * 0.9
		if f["tipo"] == "arco":
			var meio: float = f["arco"] * 0.5
			draw_arc(centro, f["r"], f["ang"] - meio, f["ang"] + meio, 28, cor, 7.0 * a + 1.0)
			draw_arc(centro, f["r"] * 0.7, f["ang"] - meio, f["ang"] + meio, 28, Color(cor.r, cor.g, cor.b, cor.a * 0.5), 3.0)
		else:
			var dir := Vector2.RIGHT.rotated(f["ang"])
			var larg: float = f["larg"]
			var comp: float = f["comp"]
			var lado: Vector2 = dir.orthogonal() * larg * 0.5
			var fim: Vector2 = dir * comp
			draw_colored_polygon(PackedVector2Array([lado, fim + lado * 0.4, fim - lado * 0.4, -lado]), Color(cor.r, cor.g, cor.b, a * 0.35))
