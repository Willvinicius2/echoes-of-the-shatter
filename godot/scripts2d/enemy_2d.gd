extends "res://scripts2d/actor_2d.gd"
## Inimigo 2D. Comportamento por `kind` em data2d/enemies.csv: melee, ranged, boss.

signal died(enemy)

const Csv = preload("res://scripts2d/csv2d.gd")
const ArrowScript = preload("res://scripts2d/arrow_2d.gd")
const Feel = preload("res://scripts2d/feel_2d.gd")

enum Estado { PERSEGUE, TELEGRAFA, ATACANDO, MORTO }

var stats := {}
var hp := 0.0
var hp_max := 0.0
var alvo: Node2D
var estado := Estado.PERSEGUE
var _cd := 0.0
var _burst_cd := 0.0
var _acertou := false
var _wind := 0.0                # tempo restante do aviso antes do golpe
var _wind_total := 0.0
var _kb := Vector2.ZERO         # empurrão por golpe recebido

func setup(id: String, jogador: Node2D, pos: Vector2) -> void:
	stats = Csv.enemy(id)
	alvo = jogador
	global_position = pos
	hp = stats["hp"]
	hp_max = hp
	_burst_cd = stats["burst_interval"]
	_cd = stats["attack_cooldown"] * 0.5
	collision_layer = 4
	collision_mask = 1 | 4 | 8
	add_to_group("hurtable")
	shadow_radius = stats["radius"] * 1.2
	setup_sprite(id)
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = stats["radius"]
	cs.shape = sh
	add_child(cs)
	play("idle", true)

func _physics_process(delta: float) -> void:
	if estado == Estado.MORTO or alvo == null:
		return
	_cd = maxf(0.0, _cd - delta)
	var para := alvo.global_position - global_position
	var dist := para.length()
	var dir := para.normalized() if dist > 0.01 else Vector2.DOWN
	_kb = _kb.move_toward(Vector2.ZERO, Feel.cfg()["knockback_decay"] * delta)
	if estado == Estado.TELEGRAFA:
		facing = dir
		_wind -= delta
		if _wind <= 0.0:
			_golpear()
		velocity = _kb
		move_and_slide()
		return
	if estado == Estado.ATACANDO:
		velocity = _kb
		move_and_slide()
		return
	facing = dir
	var mover := Vector2.ZERO
	if dist <= stats["aggro"]:
		if stats["kind"] == "ranged":
			if dist < stats["keep_distance"] * 0.8:
				mover = -dir
			elif dist > stats["attack_range"] * 0.9:
				mover = dir
			if dist <= stats["attack_range"] and _cd <= 0.0 and not alvo_morto():
				_atacar()
		else:
			if dist > stats["attack_range"] * 0.8:
				mover = dir
			if dist <= stats["attack_range"] and _cd <= 0.0 and not alvo_morto():
				_atacar()
		if stats["burst_interval"] > 0.0:
			_burst_cd -= delta
			if _burst_cd <= 0.0:
				_burst_cd = stats["burst_interval"]
				_rajada()
	velocity = mover * stats["speed"] + _kb
	move_and_slide()
	if estado == Estado.PERSEGUE:
		play("run" if mover != Vector2.ZERO else "idle")

func alvo_morto() -> bool:
	return alvo.has_method("esta_morto") and alvo.esta_morto()

## Começa o aviso (telégrafo); o golpe só sai quando `windup` acaba, dando tempo de esquivar.
func _atacar() -> void:
	_cd = stats["attack_cooldown"]
	_wind_total = stats.get("windup", 0.0)
	_wind = _wind_total
	if _wind <= 0.0:
		_golpear()
		return
	estado = Estado.TELEGRAFA
	play("idle")

func _golpear() -> void:
	estado = Estado.ATACANDO
	_acertou = false
	play("attack", true)

func _on_frame_changed() -> void:
	if estado != Estado.ATACANDO or anim_base() != "attack" or _acertou:
		return
	if sprite.frame < evento("attack"):
		return
	_acertou = true
	if stats["kind"] == "ranged":
		_projetil((alvo.global_position - global_position).normalized(), stats["damage"])
	elif alvo.global_position.distance_to(global_position) <= stats["attack_range"] * 1.3:
		alvo.take_damage(stats["damage"], global_position)

func _on_anim_finished() -> void:
	if estado == Estado.ATACANDO:
		estado = Estado.PERSEGUE
	elif estado == Estado.MORTO:
		queue_free()

func _rajada() -> void:
	var n := int(stats["burst_count"])
	for i in n:
		_projetil(Vector2.RIGHT.rotated(TAU * i / n), stats["damage"])

func _projetil(dir: Vector2, dano: float) -> void:
	var f := ArrowScript.new()
	f.setup("enemy", global_position + dir * 30.0, dir, stats["projectile_speed"], dano, 1400.0)
	get_parent().add_child(f)

func take_damage(amount: float, _origem := Vector2.ZERO) -> void:
	if estado == Estado.MORTO:
		return
	var mostrado := minf(amount, hp)
	hp -= amount
	flash()
	var morreu := hp <= 0.0
	_feedback_golpe(mostrado, _origem, morreu)
	if morreu:
		estado = Estado.MORTO
		velocity = Vector2.ZERO
		remove_from_group("hurtable")
		set_deferred("collision_layer", 0)
		died.emit(self)
		if has_anim("death"):
			play("death", true)
		else:
			queue_free()

func _feedback_golpe(amount: float, origem: Vector2, morreu: bool) -> void:
	var c := Feel.cfg()
	Feel.hit_stop(c["hit_stop_kill_ms" if morreu else "hit_stop_hit_ms"])
	Feel.shake(self, c["shake_kill_amp" if morreu else "shake_hit_amp"], c["shake_kill_time" if morreu else "shake_hit_time"])
	Feel.numero(self, amount, Color(1.0, 0.85, 0.2) if morreu else Color.WHITE, morreu)
	Feel.impacto(get_parent(), global_position + Vector2(0, -30), Color(1.0, 0.9, 0.5))
	if origem != Vector2.ZERO:
		var dir := (global_position - origem).normalized()
		_kb = dir * c["enemy_knockback"] * (1.0 - stats.get("kb_resist", 0.0))

func _draw() -> void:
	super._draw()
	if estado == Estado.TELEGRAFA and _wind_total > 0.0:
		_desenhar_aviso()
	if stats.get("hp_bar", 0.0) > 0.0 and estado != Estado.MORTO and hp < hp_max:
		var larg := 40.0
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		var topo := -90.0 * (escala_sprite())
		draw_rect(Rect2(-larg / 2.0, topo, larg, 5.0), Color(0, 0, 0, 0.7))
		draw_rect(Rect2(-larg / 2.0, topo, larg * hp / hp_max, 5.0), Color(0.8, 0.15, 0.15))

## Aviso de ataque: área vermelha que enche até o golpe (melee) ou linha de mira (ranged/chefe).
func _desenhar_aviso() -> void:
	var p := clampf(1.0 - _wind / _wind_total, 0.0, 1.0)
	var a: float = Feel.cfg()["telegraph_alpha"]
	if stats["kind"] == "ranged":
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		var fim := (alvo.global_position - global_position).normalized() * minf(stats["attack_range"], 600.0)
		draw_line(Vector2(0, -30), Vector2(0, -30) + fim, Color(1, 0.2, 0.2, a * p), 2.0 + 3.0 * p)
		return
	var r: float = stats["attack_range"] * 1.3
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, 0.6))
	draw_circle(Vector2.ZERO, r, Color(1, 0.15, 0.1, a * 0.35))
	draw_circle(Vector2.ZERO, r * p, Color(1, 0.15, 0.1, a))
	draw_arc(Vector2.ZERO, r, 0.0, TAU, 32, Color(1, 0.3, 0.2, a + 0.3), 2.0)
