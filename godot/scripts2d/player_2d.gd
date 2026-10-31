extends "res://scripts2d/actor_2d.gd"
## Arqueiro 2D: corre, atira na direção do mouse/analógico e esquiva. Números em data2d/player.csv.

signal died
signal hp_changed(hp: float, hp_max: float)
signal mana_changed(mana: float, mana_max: float)

const Csv = preload("res://scripts2d/csv2d.gd")
const ArrowScript = preload("res://scripts2d/arrow_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")
const HabilidadesScript = preload("res://scripts2d/habilidades_2d.gd")

enum Estado { LIVRE, ATIRANDO, ESQUIVA, MORTO }

var stats := {}
var hp := 0.0
var mana := 0.0
var classe := "arqueiro"
var habilidades: RefCounted   # árvore e slots da classe (habilidades_2d.gd)
var estado := Estado.LIVRE
var invencivel := 0.0
var god_mode := false          # testes automáticos
var auto_aim := Vector2.ZERO   # testes: mira forçada
var auto_move := Vector2.ZERO  # testes: movimento forçado
var dodge_cd := 0.0
var _shoot_cd := 0.0
var _dodge_t := 0.0
var _dodge_dir := Vector2.DOWN
var _aim := Vector2.DOWN
var _disparou := false

func _ready() -> void:
	stats = Csv.kv("res://data2d/player.csv")
	habilidades = HabilidadesScript.new()
	definir_classe(classe)
	collision_layer = 2
	collision_mask = 1 | 8
	add_to_group("arqueiro")
	setup_sprite("arqueiro")
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = stats["radius"]
	cs.shape = sh
	add_child(cs)
	reset()

## Troca a classe: stats de player.csv mais as sobrescritas de classes_2d.csv, e carrega a árvore dela.
func definir_classe(id: String) -> void:
	classe = id
	stats = Csv.kv("res://data2d/player.csv")
	var cl: Dictionary = HabilidadesScript.classes().get(id, {})
	for k in cl:
		if stats.has(k) and str(cl[k]) != "":
			stats[k] = float(cl[k])
	habilidades.carregar_classe(id)
	mana = stats["mana_max"]

func gastar_mana(n: float) -> void:
	mana = maxf(0.0, mana - n)
	mana_changed.emit(mana, stats["mana_max"])

## Usa a habilidade do slot 0..3 mirando no cursor (ou na mira forçada dos testes).
func usar_habilidade(slot: int) -> bool:
	if estado == Estado.MORTO or estado == Estado.ESQUIVA:
		return false
	return habilidades.usar(slot, self, _aim)

func reset() -> void:
	hp = stats["hp_max"]
	mana = stats["mana_max"]
	mana_changed.emit(mana, stats["mana_max"])
	habilidades.recargas.clear()
	estado = Estado.LIVRE
	invencivel = 0.0
	dodge_cd = 0.0
	_shoot_cd = 0.0
	velocity = Vector2.ZERO
	modulate = Color.WHITE
	play("idle", true)
	hp_changed.emit(hp, stats["hp_max"])

func _physics_process(delta: float) -> void:
	if estado == Estado.MORTO:
		velocity = Vector2.ZERO
		return
	_shoot_cd = maxf(0.0, _shoot_cd - delta)
	dodge_cd = maxf(0.0, dodge_cd - delta)
	invencivel = maxf(0.0, invencivel - delta)
	habilidades.tick(delta)
	if mana < stats["mana_max"]:
		mana = minf(stats["mana_max"], mana + stats["mana_regen"] * delta)
		mana_changed.emit(mana, stats["mana_max"])
	_aim = _ler_mira()
	var entrada := auto_move if auto_move != Vector2.ZERO else Input.get_vector("move_left", "move_right", "move_up", "move_down")

	match estado:
		Estado.ESQUIVA:
			_dodge_t -= delta
			velocity = _dodge_dir * stats["dodge_speed"]
			if _dodge_t <= 0.0:
				estado = Estado.LIVRE
		_:
			var vmax: float = stats["speed"] * (stats["attack_move_mult"] if estado == Estado.ATIRANDO else 1.0)
			var alvo := entrada * vmax
			var taxa: float = stats["accel"] if entrada != Vector2.ZERO else stats["friction"]
			velocity = velocity.move_toward(alvo, taxa * delta)
			for i in HabilidadesScript.SLOTS:
				if Input.is_action_just_pressed("skill_%d" % (i + 1)):
					usar_habilidade(i)
			if Input.is_action_just_pressed("dodge") and dodge_cd <= 0.0:
				_comecar_esquiva(entrada if entrada != Vector2.ZERO else _aim)
			elif _quer_atirar() and _shoot_cd <= 0.0:
				_comecar_tiro()
	move_and_slide()
	_animar(entrada)

## Fração 0..1 da recarga do tiro (0 = pronto), para a barra de habilidades.
func recarga_tiro() -> float:
	return clampf(_shoot_cd / stats["shoot_cooldown"], 0.0, 1.0)

func esta_morto() -> bool:
	return estado == Estado.MORTO

func _quer_atirar() -> bool:
	return Input.is_action_pressed("shoot") or auto_aim != Vector2.ZERO

func _ler_mira() -> Vector2:
	if auto_aim != Vector2.ZERO:
		return auto_aim.normalized()
	var stick := Input.get_vector("aim_left", "aim_right", "aim_up", "aim_down")
	if stick.length() > 0.3:
		return stick.normalized()
	var d := get_global_mouse_position() - global_position
	return d.normalized() if d.length() > 4.0 else _aim

func _comecar_esquiva(dir: Vector2) -> void:
	estado = Estado.ESQUIVA
	_dodge_dir = dir.normalized()
	_dodge_t = stats["dodge_time"]
	dodge_cd = stats["dodge_cooldown"]
	invencivel = maxf(invencivel, stats["dodge_time"])
	facing = _dodge_dir
	play("dodge", true)
	Audio.tocar("dodge")

func _comecar_tiro() -> void:
	estado = Estado.ATIRANDO
	_shoot_cd = stats["shoot_cooldown"]
	_disparou = false
	facing = _aim
	play("attack", true)

func _animar(entrada: Vector2) -> void:
	match estado:
		Estado.ATIRANDO, Estado.ESQUIVA:
			if estado == Estado.ATIRANDO:
				facing = _aim
		_:
			if entrada != Vector2.ZERO:
				facing = _aim if _aim != Vector2.ZERO else entrada
				play("run")
			else:
				facing = _aim
				play("idle")

func _on_frame_changed() -> void:
	if estado != Estado.ATIRANDO or anim_base() != "attack" or _disparou:
		return
	var ev: int = evento("attack")
	if sprite.frame >= ev:
		_disparou = true
		_soltar_flecha()

func _soltar_flecha() -> void:
	var n := int(stats["arrow_count"])  # gancho de upgrades: multishot abre as flechas em leque
	for i in n:
		var dir := _aim.rotated(deg_to_rad(stats["multishot_spread"]) * (i - (n - 1) * 0.5))
		var f := ArrowScript.new()
		f.setup("player", global_position + dir * stats["arrow_spawn_dist"], dir,
			stats["arrow_speed"], stats["arrow_damage"], stats["arrow_range"])
		f.pierce = int(stats["arrow_pierce"])  # gancho de upgrades
		get_parent().add_child(f)
	Audio.tocar("shoot")
	var c := Feel.cfg()
	velocity -= _aim * c["player_recoil"]
	Feel.shake(self, c["shake_shot_amp"], c["shake_shot_time"])

func _on_anim_finished() -> void:
	if estado == Estado.ATIRANDO:
		estado = Estado.LIVRE
	elif estado == Estado.MORTO:
		return

func take_damage(amount: float, _origem := Vector2.ZERO) -> void:
	if estado == Estado.MORTO or invencivel > 0.0 or god_mode:
		return
	hp = maxf(0.0, hp - amount)
	invencivel = stats["hit_iframes"]
	flash()
	Audio.tocar("player_hurt")
	var c := Feel.cfg()
	Feel.hit_stop(c["hit_stop_player_ms"])
	Feel.shake(self, c["shake_player_amp"], c["shake_player_time"])
	Feel.numero(self, amount, Color(1.0, 0.35, 0.3), true)
	hp_changed.emit(hp, stats["hp_max"])
	if hp <= 0.0:
		estado = Estado.MORTO
		play("death", true)
		died.emit()
