class_name Enemy
extends Actor
## Inimigo com FSM simples: parado -> perseguir -> telegraph -> atacar -> recuperar.
## Também atordoado (guarda quebrada), pausa de fase (chefe) e morte.

enum St { IDLE, CHASE, TELEGRAPH, ATTACK, RECOVER, STUNNED, PHASE, DYING }

const STUCK_SECONDS: float = 10.0

var data: EnemyData
var state: int = St.IDLE
var state_t: float = 0.0
var group_id: int = 0
var phase: int = 1

var _home: Vector2 = Vector2.ZERO
var _attack_cd: float = 0.0
var _wander_t: float = 0.0
var _wander_target: Vector2 = Vector2.ZERO
var _hit_done: bool = false
var _speed_mult: float = 1.0
var _player: Player = null


func setup(d: EnemyData, pos: Vector2, group: int) -> void:
	data = d
	position = pos
	_home = pos
	_wander_target = pos
	group_id = group
	radius = d.radius
	facing = Vector2.LEFT
	combatant = Combatant.new()
	combatant.id = d.id
	var s: StatBlock = combatant.stats
	s.set_base("max_life", d.max_life)
	s.set_base("damage", d.damage)
	s.set_base("armour", d.armour)
	s.set_base("evasion", d.evasion)
	s.set_base("block", d.block)
	s.set_base("block_reduction", d.block_reduction)
	s.set_base("res_fire", d.res_fire)
	s.set_base("res_cold", d.res_cold)
	s.set_base("res_lightning", d.res_lightning)
	combatant.reset()
	combatant.frontal_shield_reduction = d.frontal_shield_reduction
	combatant.shield_arc_degrees = d.shield_arc_degrees
	combatant.guard.configure(d.guard_max, d.guard_stun, d.guard_decay)


func _ready() -> void:
	collision_layer = 2
	collision_mask = 4
	add_to_group("enemies")
	super._ready()


func is_dying() -> bool:
	return state == St.DYING


func is_stuck() -> bool:
	return state in [St.TELEGRAPH, St.ATTACK, St.RECOVER, St.STUNNED, St.PHASE] and state_t > STUCK_SECONDS


## Usado pelo vigia da cena: destrava um inimigo preso.
func force_reset() -> void:
	combatant.invulnerable = false
	_set_state(St.CHASE)


func alert_group(gid: int) -> void:
	if gid == group_id and state == St.IDLE:
		_set_state(St.CHASE)


func alert_now() -> void:
	if state == St.IDLE:
		_set_state(St.CHASE)


func _set_state(s: int) -> void:
	state = s
	state_t = 0.0
	if s == St.ATTACK:
		_hit_done = false


func _find_player() -> void:
	if _player == null or not is_instance_valid(_player):
		_player = get_tree().get_first_node_in_group("player") as Player


func _player_alive() -> bool:
	return _player != null and is_instance_valid(_player) and not _player.combatant.is_dead()


func _tick(delta: float) -> void:
	if data == null or combatant == null:
		queue_free()
		return
	state_t += delta
	_attack_cd = maxf(0.0, _attack_cd - delta)
	if state == St.DYING:
		_tick_dying(delta)
		return
	combatant.update(delta)
	if combatant.is_dead():
		_die()
		return
	_find_player()
	var desired: Vector2 = Vector2.ZERO
	match state:
		St.IDLE:
			desired = _tick_idle(delta)
		St.CHASE:
			desired = _tick_chase()
		St.TELEGRAPH:
			if state_t >= data.attack_windup:
				_set_state(St.ATTACK)
		St.ATTACK:
			_tick_attack()
		St.RECOVER:
			if state_t >= data.attack_recover:
				_set_state(St.CHASE)
		St.STUNNED:
			if not combatant.guard.is_broken():
				_set_state(St.CHASE)
		St.PHASE:
			if state_t >= data.phase_pause:
				combatant.invulnerable = false
				_set_state(St.CHASE)
	velocity = desired + kb_vel
	kb_vel = kb_vel.move_toward(Vector2.ZERO, data.kb_decay * delta)
	move_and_slide()


func _tick_idle(delta: float) -> Vector2:
	if _player_alive() and global_position.distance_to(_player.global_position) <= data.aggro_range:
		get_tree().call_group("enemies", "alert_group", group_id)
		_set_state(St.CHASE)
		return Vector2.ZERO
	_wander_t -= delta
	if _wander_t <= 0.0:
		var rng: RandomNumberGenerator = Game.rng.stream(RngStreams.EVENTS)
		_wander_target = _home + Vector2(rng.randf_range(-1.0, 1.0), rng.randf_range(-1.0, 1.0)) * data.patrol_radius
		_wander_t = rng.randf_range(1.5, 3.0)
	var to: Vector2 = _wander_target - global_position
	if to.length() < 4.0:
		return Vector2.ZERO
	facing = to.normalized()
	return facing * data.move_speed * data.patrol_speed_mult


func _tick_chase() -> Vector2:
	if not _player_alive():
		_set_state(St.IDLE)
		return Vector2.ZERO
	var to: Vector2 = _player.global_position - global_position
	var dist: float = to.length()
	if dist > 1.0:
		facing = to / dist
	if dist <= data.attack_range * data.attack_start_ratio and _attack_cd <= 0.0:
		_set_state(St.TELEGRAPH)
		return Vector2.ZERO
	var move: Vector2 = Vector2.ZERO
	if dist > data.attack_range * data.attack_start_ratio * 0.9:
		move = facing * data.move_speed * _speed_mult
	return move + _separation()


func _separation() -> Vector2:
	var push: Vector2 = Vector2.ZERO
	for o in get_tree().get_nodes_in_group("enemies"):
		var e: Enemy = o as Enemy
		if e == null or e == self or e.is_dying():
			continue
		var d: Vector2 = global_position - e.global_position
		var min_d: float = radius + e.radius + 4.0
		var l: float = d.length()
		if l > 0.01 and l < min_d:
			push += d / l * (min_d - l) * 6.0
	return push


func _tick_attack() -> void:
	if not _hit_done:
		_hit_done = true
		_do_attack_hit()
	if state_t >= data.attack_active:
		_attack_cd = data.attack_cooldown
		_set_state(St.RECOVER)


func _do_attack_hit() -> void:
	var cv: ConvexPolygonShape2D = ConvexPolygonShape2D.new()
	cv.points = Geo.sector_points(data.attack_range, data.attack_arc, 10)
	var xf: Transform2D = Transform2D(facing.angle(), global_position)
	for b in query_shape(cv, xf, 1):
		var p: Player = b as Player
		if p != null:
			strike(p, HitSpec.from_enemy(data))
			break
	if data.is_boss:
		EventBus.fx_dust.emit(global_position + facing * data.attack_range * 0.6, 14)
		if data.attack_shake > 0.0:
			EventBus.screen_shake.emit(data.attack_shake, 0.2)


func on_hit_received(res: HitResult, spec: HitSpec, dir: Vector2) -> void:
	if res.invulnerable or res.evaded or state == St.DYING:
		return
	flash(0.1)
	get_tree().call_group("enemies", "alert_group", group_id)
	if spec.knockback > 0.0:
		kb_vel += dir * spec.knockback * (1.0 - data.knockback_resist)
	if combatant.is_dead():
		_die()
		return
	if data.is_boss and phase == 1 and data.phase2_threshold > 0.0 \
			and combatant.life <= combatant.max_life() * data.phase2_threshold:
		_begin_phase2()
		return
	if res.guard_broken:
		_set_state(St.STUNNED)
		EventBus.guard_broken.emit(data.id, global_position)


func _begin_phase2() -> void:
	phase = 2
	_speed_mult = data.phase2_speed_mult
	combatant.invulnerable = true
	_set_state(St.PHASE)
	EventBus.boss_phase_changed.emit(data.id, 2)
	if data.summon_count > 0:
		EventBus.summon_requested.emit(data.summon_enemy_id, data.summon_count, global_position)


func _die() -> void:
	if state == St.DYING:
		return
	_set_state(St.DYING)
	velocity = Vector2.ZERO
	set_deferred("collision_layer", 0)
	EventBus.enemy_died.emit(data.id, global_position, data.is_boss)
	if data.is_boss:
		EventBus.boss_defeated.emit(data.id)


func _tick_dying(delta: float) -> void:
	velocity = kb_vel
	kb_vel = kb_vel.move_toward(Vector2.ZERO, data.kb_decay * delta)
	move_and_slide()
	if state_t >= data.death_time:
		EventBus.enemy_dissolved.emit(global_position, data.is_boss)
		queue_free()


# ---------------------------------------------------------------- desenho

func _draw() -> void:
	if data == null:
		return
	if state == St.TELEGRAPH:
		_draw_telegraph(clampf(state_t / data.attack_windup, 0.0, 1.0))
	var k: float = 1.0 if not data.is_boss else 1.9
	var alpha: float = 1.0
	var squash: float = 1.0
	if state == St.DYING:
		var f: float = clampf(state_t / data.death_time, 0.0, 1.0)
		alpha = 1.0 - f
		squash = 1.0 - 0.6 * f
	draw_shadow((radius + 2.0), radius * 0.55)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(k, k * squash))
	var body: Color = tint(data.body_color)
	var accent: Color = tint(data.accent_color)
	var dark: Color = tint(Palette.CARVAO)
	body.a = alpha
	accent.a = alpha
	dark.a = alpha
	draw_rect(Rect2(-7, -20, 14, 16), body)
	draw_rect(Rect2(-5, -28, 10, 9), body.lightened(0.15))
	draw_rect(Rect2(-4, -26, 3, 3), dark)
	draw_rect(Rect2(1, -26, 3, 3), dark)
	draw_rect(Rect2(-7, -5, 5, 5), body.darkened(0.2))
	draw_rect(Rect2(2, -5, 5, 5), body.darkened(0.2))
	var hand: Vector2 = Vector2(0, -13) + facing * 7.0
	var raise: float = 0.0
	if state == St.TELEGRAPH:
		raise = 6.0 * clampf(state_t / data.attack_windup, 0.0, 1.0)
	draw_line(hand + Vector2(0, -raise), hand + facing * 14.0 + Vector2(0, -raise), accent, 3.0)
	if data.is_boss:
		draw_rect(Rect2(-9, -22, 18, 3), accent)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	if data.shield_arc_degrees > 0.0 and state != St.DYING:
		var half: float = deg_to_rad(data.shield_arc_degrees * 0.5)
		var sc: Color = Palette.OCRE if not combatant.guard.is_broken() else Palette.PERIGO
		sc.a = 0.9 if not combatant.guard.is_broken() else 0.4
		draw_arc(Vector2(0, -14), radius * k + 6.0, facing.angle() - half, facing.angle() + half, 14, sc, 4.0)
	if state == St.STUNNED:
		for i in range(3):
			var a: float = state_t * 5.0 + TAU * float(i) / 3.0
			draw_rect(Rect2(Vector2(cos(a) * 10.0, -34.0 * k + sin(a) * 3.0), Vector2(3, 3)), Palette.DOURADO)
	if not data.is_boss and state != St.DYING:
		var w: float = 22.0
		var fr: float = clampf(combatant.life / combatant.max_life(), 0.0, 1.0)
		draw_rect(Rect2(-w * 0.5, -38, w, 3), Palette.CARVAO)
		draw_rect(Rect2(-w * 0.5, -38, w * fr, 3), Palette.CARMESIM)


func _draw_telegraph(progress: float) -> void:
	var ang: float = facing.angle()
	var pts: PackedVector2Array = PackedVector2Array()
	for p in Geo.sector_points(data.attack_range, data.attack_arc, 12):
		pts.append(p.rotated(ang))
	var fill: Color = Palette.TELEGRAPH
	fill.a = lerpf(0.16, 0.45, progress)
	draw_colored_polygon(pts, fill)
	# Grade: arcos concêntricos + linhas radiais.
	var grid: Color = Palette.PERIGO
	grid.a = 0.55
	var half: float = deg_to_rad(data.attack_arc * 0.5)
	for i in range(1, 5):
		draw_arc(Vector2.ZERO, data.attack_range * float(i) / 4.0, ang - half, ang + half, 14, grid, 1.0)
	for i in range(0, 5):
		var a: float = ang + lerpf(-half, half, float(i) / 4.0)
		draw_line(Vector2.ZERO, Vector2.RIGHT.rotated(a) * data.attack_range, grid, 1.0)
	# Preenchimento que cresce até o impacto.
	var inner: PackedVector2Array = PackedVector2Array()
	for p in Geo.sector_points(data.attack_range * progress, data.attack_arc, 12):
		inner.append(p.rotated(ang))
	var core: Color = Palette.PERIGO
	core.a = 0.35
	draw_colored_polygon(inner, core)
	# Brasas subindo.
	var t: float = Time.get_ticks_msec() / 1000.0
	var seed_off: float = float(get_instance_id() % 97) * 0.013
	for i in range(14):
		var h: float = fmod(float(i) * 0.618034 + seed_off, 1.0)
		var rr: float = data.attack_range * (0.15 + 0.85 * h)
		var aa: float = ang + (fmod(h * 7.3, 1.0) - 0.5) * 2.0 * half * 0.9
		var rise: float = fmod(t * 0.9 + h, 1.0) * 14.0
		var pos: Vector2 = Vector2.RIGHT.rotated(aa) * rr + Vector2(0, -rise)
		var ec: Color = Palette.DOURADO if i % 2 == 0 else Palette.PERIGO
		ec.a = 1.0 - rise / 14.0
		draw_rect(Rect2(pos.round(), Vector2(2, 2)), ec)
