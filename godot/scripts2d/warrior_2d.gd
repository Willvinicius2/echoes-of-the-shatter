extends "res://scripts2d/actor_2d.gd"
## Guerreiro 2D: combo de espada em 3 golpes, esquiva e até 4 habilidades ativas da árvore comum (habilidades_2d.gd).
## Autocast: o combo e as ativas saem sozinhos no inimigo certo (data2d/habilidades_mira.csv); a ult e a postura de
## guarda ficam na tecla. Na partida ele progride como o arqueiro: cartas de nível do core (os stats usam os mesmos
## nomes, `arrow_damage` e `shoot_cooldown`), gemas de habilidade, Arautos e o Eco da lâmina (afinidade do golpe
## básico, data2d/afinidades_guerreiro.csv), que muda o que o corte faz.
## Números em data2d/guerreiro.csv e data2d/habilidades_guerreiro.csv; custo das ativas é ímpeto, não mana. Mesma interface do player_2d.gd (arqueiro).

signal died
signal hp_changed(hp: float, hp_max: float)

const Csv = preload("res://scripts2d/csv2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")
const Efeitos = preload("res://scripts2d/efeitos_guerreiro_2d.gd")
const HabilidadesScript = preload("res://scripts2d/habilidades_2d.gd")
const Alvos = preload("res://scripts2d/alvos_2d.gd")
const Afinidades = preload("res://scripts2d/afinidades_2d.gd")
const Fx = preload("res://scripts2d/fx_guerreiro_2d.gd")
const Vfx = preload("res://scripts2d/vfx_2d.gd")
const VenenoFx = preload("res://scripts2d/efeitos_arqueiro_veneno_2d.gd")
const GeloFx = preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd")
const FogoFx = preload("res://scripts2d/efeitos_arqueiro_fogo_2d.gd")
const RaioFx = preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd")

enum Estado { LIVRE, ATACANDO, CONJURANDO, INVESTIDA, SALTO, ESQUIVA, MORTO }

const TECLAS_SKILL := {"skill_1": KEY_Q, "skill_2": KEY_E, "skill_3": KEY_F, "skill_4": KEY_R}
const COR_ESCUDO := Color(0.35, 0.65, 0.95)

var stats := {}
var hp := 0.0
var classe := "guerreiro"
## Eco da lâmina: id de data2d/afinidades_guerreiro.csv ou vazio (golpe neutro). Escolhido na primeira gema da corrida.
var afinidade := ""
var estado := Estado.LIVRE
var invencivel := 0.0
var god_mode := false          # testes automáticos
var auto_aim := Vector2.ZERO   # testes: mira forçada (e ataque contínuo)
var auto_move := Vector2.ZERO  # testes: movimento forçado
var autocast := true           # combo e ativas disparam sozinhos (falso: só tecla, como antes)
var _alvo_basico := {}         # alvo do combo no autocast ({} = ninguém no alcance)
var dodge_cd := 0.0
var habilidades: RefCounted    # árvore e slots (habilidades_2d.gd); recargas das ativas ficam em habilidades.recargas
# Experiência do modo horda, preenchida a cada quadro pela barra de XP (hud_xp_2d.gd) a partir do core; a HUD lê daqui.
var nivel_jogador := 1
var xp := 0.0
var xp_proximo := 1.0
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
var _rng := RandomNumberGenerator.new()
var _critico := false          # o último golpe calculado foi crítico
var _prox_autocast := 0.0      # espera entre dois autocasts seguidos
var _rastro_t := 0.0           # poeira da investida

func _ready() -> void:
	stats = Csv.kv("res://data2d/guerreiro.csv")
	_registrar_acoes()
	HabilidadesScript.registrar_tecla_ult()
	if habilidades == null:
		habilidades = HabilidadesScript.new()
		habilidades.carregar_classe("guerreiro")
	habilidades.mudou.connect(_atualizar_heralds)
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

## Mesma interface do arqueiro (run_2d.gd): stats da classe e a árvore dela.
func definir_classe(id: String) -> void:
	classe = id
	stats = Csv.kv("res://data2d/guerreiro.csv")
	habilidades.carregar_classe(id)

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
	_sem_dano = 0.0
	_sem_acerto = 0.0
	_resistiu = false
	_prox_autocast = 0.0
	for nome in ["AuraFuria", "LaminasTempestade"]:
		_tirar_no(nome)
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
	var entrada := auto_move if auto_move != Vector2.ZERO else Input.get_vector("move_left", "move_right", "move_up", "move_down")
	_aim = _ler_mira(entrada)
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
			_rastro_t -= delta
			if _rastro_t <= 0.0:
				_rastro_t = 0.06
				Fx.tocar(get_parent(), "poeira", global_position, 0.0, 0.0, Color.WHITE, 0)
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
	_prox_autocast = maxf(0.0, _prox_autocast - delta)
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
				if usar(id, _dir_auto(id)):
					return
		if InputMap.has_action("ult") and Input.is_action_just_pressed("ult") and usar_ult():
			return
		if autocast and _autocast_habilidades():
			return
	if _quer_atacar() and _atk_cd <= 0.0:
		_comecar_golpe()

func mira_atual() -> Vector2:
	return _aim

func _quer_atacar() -> bool:
	return Input.is_action_pressed("shoot") or auto_aim != Vector2.ZERO or not _alvo_basico.is_empty()

## Direção do inimigo que o autocast escolheria para `id` (ou a mira atual se não há alvo ou a mira é no cursor).
func _dir_auto(id: String) -> Vector2:
	if not autocast or Alvos.mira_mouse:
		return _aim
	var a: Dictionary = habilidades.alvo_auto(id, get_tree(), global_position, stats["attack_range"])
	return _aim if a.is_empty() else a["dir"]

## Autocast: a primeira ativa equipada pronta, com ímpeto e com alvo, sai agora. A ult e a guarda não entram.
func _autocast_habilidades() -> bool:
	if _prox_autocast > 0.0:
		return false
	for id in habilidades.slots:
		if not habilidades.automatica(id) or _cd(id) > 0.0:
			continue
		var a: Dictionary = habilidades.alvo_auto(id, get_tree(), global_position, stats["attack_range"])
		if not a.is_empty() and usar(id, _aim if Alvos.mira_mouse else a["dir"]):
			_prox_autocast = stats.get("autocast_intervalo", 0.25)
			return true
	return false

## Ult: a ativa marcada como ult no slot sai só na tecla de ult.
func usar_ult() -> bool:
	var slot: int = habilidades.slot_ult()
	if slot < 0:
		return false
	var id: String = habilidades.slots[slot]
	return usar(id, _dir_auto(id))

## Mira: a forçada dos testes; no autocast, o inimigo do combo (ou a direção do movimento); senão analógico e cursor.
func _ler_mira(entrada := Vector2.ZERO) -> Vector2:
	_alvo_basico = {}
	if auto_aim != Vector2.ZERO:
		return auto_aim.normalized()
	if autocast and habilidades != null:
		_alvo_basico = habilidades.alvo_auto("basico", get_tree(), global_position, stats["attack_range"])
		if not Alvos.mira_mouse:
			if not _alvo_basico.is_empty():
				return _alvo_basico["dir"]
			if entrada != Vector2.ZERO:
				return entrada.normalized()
			return _aim
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
	_atk_cd = stats["shoot_cooldown"] * (1.4 if combo == 3 else 1.0) / taxa
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

## Def do Eco escolhido ({} = golpe neutro).
func _eco() -> Dictionary:
	return Afinidades.defs(classe).get(afinidade, {}) if afinidade != "" else {}

## Alcance e arco do golpe básico: a carta Lâmina Longa (`arrow_pierce` no core) estica os dois.
func _alcance_basico() -> float:
	return stats["attack_range"] * (1.0 + stats.get("reach_per_pierce", 0.0) * stats.get("arrow_pierce", 0.0))

func _golpe_basico() -> void:
	var eco := _eco()
	var el := str(eco.get("elemento", ""))
	var mult := 1.0
	var arco: float = stats["attack_arc"] * (1.0 + stats.get("reach_per_pierce", 0.0) * stats.get("arrow_pierce", 0.0))
	if combo == 2:
		mult = stats["combo2_mult"]
	elif combo == 3:
		mult = stats["combo3_mult"]
		arco *= stats["combo3_arc_mult"]
	if not eco.is_empty():
		mult *= eco.get("dano", 1.0)
		if el == "veneno":
			arco *= 1.25   # Eco da Peste: corte mais largo
	arco = minf(arco, 300.0)
	var alcance := _alcance_basico()
	_cortar(mult, arco, alcance, combo, eco)
	# Lâmina Dupla (carta `multishot`): cada golpe extra é um eco atrasado do mesmo corte, mais fraco.
	var ecos := int(stats.get("arrow_count", 1)) - 1
	for k in ecos:
		var mira := _aim
		var golpe := combo
		get_tree().create_timer(stats.get("echo_delay", 0.12) * (k + 1), false).timeout.connect(func():
			if estado != Estado.MORTO:
				_cortar(mult * stats.get("echo_mult", 0.5), arco, alcance, golpe, eco, mira, true))
	velocity += _aim * stats["combo_lunge"]
	Audio.tocar("shoot")
	var c := Feel.cfg()
	Feel.shake(self, c["shake_shot_amp"] * (2.0 if combo == 3 else 1.0), c["shake_shot_time"])

## Um corte do combo: acerta o cone, aplica o Eco e desenha a meia-lua (o 3º golpe é o corte pesado).
func _cortar(mult: float, arco: float, alcance: float, golpe: int, eco: Dictionary, mira := Vector2.ZERO, eco_duplo := false) -> void:
	if mira == Vector2.ZERO:
		mira = _aim
	var alvos := alvos_cone(global_position, mira, alcance, arco)
	for a in alvos:
		acertar(a, mult)
	var el := str(eco.get("elemento", ""))
	if not eco.is_empty():
		Efeitos.eco_golpe(self, alvos, golpe, eco, mira, alcance)
	var cor: Color = Efeitos.TINTAS.get(el, Efeitos.COR_LAMINA if golpe < 3 else Efeitos.COR_PESADO)
	var s := Fx.tocar(get_parent(), "corte_pesado" if golpe == 3 else "corte", global_position + Efeitos.PEITO, alcance * (0.9 if eco_duplo else 1.0), mira.angle() + (0.35 if eco_duplo else 0.0), cor)
	if golpe == 2 and s is AnimatedSprite2D:
		s.flip_v = true   # o segundo golpe volta pelo outro lado

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

## Usa a ativa `id` se estiver aprendida, pronta e o jogador livre, mirando em `mira` (vazio = a mira atual).
## Retorna se começou.
func usar(id: String, mira := Vector2.ZERO) -> bool:
	if habilidades == null or habilidades.nivel(id) <= 0 or not habilidades.defs.has(id) or estado != Estado.LIVRE:
		return false
	var d: Dictionary = habilidades.def_nivel(id)
	if _cd(id) > 0.0 or d["efeito"] == "postura_guarda" or d["custo"] > impeto:
		return false
	if mira != Vector2.ZERO:
		_aim = mira.normalized()
	if not Efeitos.executar(d["efeito"], self, d, habilidades.nivel(id), _aim):
		return false
	impeto -= d["custo"]
	_iniciar_recarga(id)
	facing = _aim
	return true

func comecar_conjuracao(efeito: String, d: Dictionary, mira: Vector2, nivel: int, ponto := Vector2.INF) -> void:
	_cast = {"efeito": efeito, "def": d, "nivel": nivel, "mira": mira, "ponto": ponto, "espera": d["espera"], "resta": d["espera"] + d["recup"], "aplicou": false}
	estado = Estado.CONJURANDO
	sprite.speed_scale = 1.0
	play("attack", true)

func _conjurar_passo(delta: float) -> void:
	_cast["resta"] -= delta
	_cast["espera"] -= delta
	if not _cast["aplicou"] and _cast["espera"] <= 0.0:
		_cast["aplicou"] = true
		Efeitos.aplicar(_cast["efeito"], self, _cast["def"], _cast["nivel"], _cast["mira"], _cast["ponto"])
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

## Dano base do guerreiro vezes `mult`, sem crítico nem bônus de alvo (pulsos e saltos de raio das habilidades).
func dano_base(mult: float) -> float:
	return stats["arrow_damage"] * mult

func _dano_para(alvo: Node, mult: float) -> float:
	var m: float = stats["arrow_damage"] * mult * (1.0 + impeto / maxf(stats["impeto_max"], 1.0) * stats["impeto_damage"])
	_critico = stats.get("crit_chance", 0.0) > 0.0 and _rng.randf() < stats["crit_chance"]
	if _critico:
		m *= stats.get("crit_mult", 2.0)
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

# ---------------------------------------------------------------- Arautos (mesmos gatilhos do arqueiro)

## Gatilhos de morte dos Arautos aprendidos na partida. `sobra` = dano que passou da vida do inimigo no golpe fatal.
func herald_morte(inimigo: Node2D, sobra := 0.0) -> void:
	if habilidades == null:
		return
	if habilidades.nivel("herald_plague") > 0 and inimigo.tem_status("veneno"):
		VenenoFx.arauto_peste_morte(inimigo, habilidades.def_nivel("herald_plague"))
		Vfx.aura_acender(self, "AuraPeste")
	if habilidades.nivel("herald_ice") > 0:
		GeloFx.arauto_vigiar(inimigo, self, habilidades.def_nivel("herald_ice"))
		if GeloFx.esta_congelado(inimigo):
			Vfx.aura_acender(self, "AuraGelo")
	if habilidades.nivel("herald_thunder") > 0:
		RaioFx.ao_morrer(inimigo)
		if inimigo.tem_status("choque"):
			Vfx.aura_acender(self, "AuraArauto")
	if habilidades.nivel("arauto_cinzas") > 0:
		var d: Dictionary = habilidades.def_nivel("arauto_cinzas").duplicate()
		d["minimo"] = float(inimigo.hp_max) * float(d.get("qtd", 0.0)) / 100.0
		if FogoFx.ao_abate(self, inimigo.global_position, sobra, d):
			Vfx.aura_acender(self, "AuraCinzas")

## Auras dos Arautos seguem o que está aprendido (liga e desliga quando a árvore muda).
func _atualizar_heralds() -> void:
	if habilidades == null or not is_inside_tree():
		return
	if habilidades.nivel("herald_plague") > 0:
		VenenoFx.aura_arauto(self)
	else:
		_tirar_no("AuraPeste")
	RaioFx.ativar_arauto(self, habilidades.def_nivel("herald_thunder") if habilidades.nivel("herald_thunder") > 0 else {})
	if habilidades.nivel("herald_ice") > 0:
		if not has_node("AuraGelo"):
			GeloFx.aura(self)
	else:
		_tirar_no("AuraGelo")
	if habilidades.nivel("arauto_cinzas") > 0:
		if not has_node("AuraCinzas"):
			FogoFx.aura(self).name = "AuraCinzas"
	else:
		_tirar_no("AuraCinzas")

func _tirar_no(nome: String) -> void:
	if has_node(nome):
		get_node(nome).queue_free()

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
		var lado := (origem - global_position).normalized()
		Fx.tocar(get_parent(), "escudada", global_position + Efeitos.PEITO + lado * 18.0, 40.0, lado.angle())
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
		Fx.tocar(get_parent(), "onda", global_position, 90.0, 0.0, Color(0.6, 0.82, 1.0), 0)
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
			a.take_damage(stats["arrow_damage"] * stats["revide"], global_position)
	Fx.tocar(get_parent(), "onda", global_position, stats["revide_radius"], 0.0, Efeitos.COR_FURIA, 0)

# ---------------------------------------------------------------- HUD e animação

## Fração 0..1 da recarga do golpe básico (0 = pronto).
func recarga_tiro() -> float:
	return clampf(_atk_cd / maxf(stats["shoot_cooldown"], 0.01), 0.0, 1.0)

## Barra do recurso (ímpeto), 0..1.
func recurso_frac() -> float:
	return clampf(impeto / maxf(stats["impeto_max"], 1.0), 0.0, 1.0)

## Slots da barra de habilidades: golpe, esquiva e as ativas aprendidas (tecla Q, E, F, R).
func slots_hud() -> Array:
	var out := [
		{"icone": afinidade if afinidade != "" else "golpe", "tecla": "hud.key.shoot", "recarga": recarga_tiro()},
		{"icone": "esquiva", "tecla": "hud.key.dodge", "recarga": clampf(dodge_cd / stats["dodge_cooldown"], 0.0, 1.0)},
	]
	if habilidades != null:
		for i in habilidades.slots.size():
			var id: String = habilidades.slots[i]
			if id == "":
				continue
			out.append({"icone": id, "tecla": "hud.key.skill_%d" % (i + 1), "recarga": recarga_skill(id)})
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
	if guardando:
		var meio: float = deg_to_rad(stats["guard_arc"]) * 0.5
		draw_arc(Vector2(0, -30), 44.0, _aim.angle() - meio, _aim.angle() + meio, 20, COR_ESCUDO, 5.0)
