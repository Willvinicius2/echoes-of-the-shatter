extends "res://scripts2d/actor_2d.gd"
## Arqueiro 2D: corre, atira na direção do mouse/analógico e esquiva. Números em data2d/player.csv.

signal died
signal hp_changed(hp: float, hp_max: float)

const Csv = preload("res://scripts2d/csv2d.gd")
const ArrowScript = preload("res://scripts2d/arrow_2d.gd")

enum Estado { LIVRE, ATIRANDO, ESQUIVA, MORTO }

var stats := {}
var hp := 0.0
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
	collision_layer = 2
	collision_mask = 1
	add_to_group("arqueiro")
	setup_sprite("arqueiro")
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = stats["radius"]
	cs.shape = sh
	add_child(cs)
	reset()

func reset() -> void:
	hp = stats["hp_max"]
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
			if Input.is_action_just_pressed("dodge") and dodge_cd <= 0.0:
				_comecar_esquiva(entrada if entrada != Vector2.ZERO else _aim)
			elif _quer_atirar() and _shoot_cd <= 0.0:
				_comecar_tiro()
	move_and_slide()
	_animar(entrada)

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
	hp_changed.emit(hp, stats["hp_max"])
	if hp <= 0.0:
		estado = Estado.MORTO
		play("death", true)
		died.emit()
