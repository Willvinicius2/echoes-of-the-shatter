class_name Player
extends Actor
## Guerreiro. Lê input por ações nomeadas, mira com o mouse e delega todo
## cálculo de dano ao motor de regras.

enum Act { NONE, SKILL, DODGE, DEAD }

const SKILL_ACTIONS: PackedStringArray = ["attack_basic", "skill_1", "skill_2", "skill_3"]
const BUFFER_TIME: float = 0.18

var hero: ClassData
var skills: Array[SkillData] = []
var impeto: ResourcePool
var cds: Array[float] = [0.0, 0.0, 0.0, 0.0]
var cd_max: Array[float] = [0.1, 0.1, 0.1, 0.1]
var act: int = Act.NONE
var act_skill: SkillData = null
var act_t: float = 0.0
var act_dir: Vector2 = Vector2.RIGHT
var dodge_charges: int = 0
var dodge_progress: float = 0.0
## Para bots/testes: posição de mira forçada (null = usa o mouse).
var aim_override: Variant = null

var _act_hit_done: bool = false
var _dash_len: float = 0.0
var _hit_set: Dictionary = {}
var _dodge_dir: Vector2 = Vector2.RIGHT
var _buffer_idx: int = -1
var _buffer_t: float = 0.0
var _dodge_buffer: float = 0.0
var _last_pts: int = -1
var _slash_t: float = 0.0
var _slash_dir: Vector2 = Vector2.RIGHT
var _slash_skill: SkillData = null
var _rift_t: float = 0.0
var _rift_dir: Vector2 = Vector2.RIGHT


func setup(h: ClassData) -> void:
	hero = h
	radius = h.radius
	combatant = Combatant.new()
	combatant.id = "player"
	var s: StatBlock = combatant.stats
	s.set_base("max_life", h.max_life)
	s.set_base("damage", h.damage)
	s.set_base("armour", h.armour)
	s.set_base("evasion", h.evasion)
	s.set_base("block", h.block)
	s.set_base("block_reduction", h.block_reduction)
	s.set_base("crit_chance", h.crit_chance)
	s.set_base("crit_multiplier", h.crit_multiplier)
	s.set_base("res_fire", h.res_fire)
	s.set_base("res_cold", h.res_cold)
	s.set_base("res_lightning", h.res_lightning)
	combatant.reset()
	impeto = ResourcePool.new(h.max_impeto, h.impeto_decay_delay, h.impeto_decay_rate)
	skills.clear()
	for sid in h.skill_ids:
		var sk: SkillData = DataDB.get_skill(sid)
		if sk == null:
			push_error("Skill não encontrada: %s" % sid)
		else:
			skills.append(sk)
	dodge_charges = h.dodge_charges


func _ready() -> void:
	collision_layer = 1
	collision_mask = 4
	add_to_group("player")
	super._ready()


func respawn(pos: Vector2) -> void:
	global_position = pos
	combatant.reset()
	impeto.current = 0.0
	act = Act.NONE
	act_skill = null
	velocity = Vector2.ZERO
	kb_vel = Vector2.ZERO
	hitstop_left = 0.0
	dodge_charges = hero.dodge_charges
	dodge_progress = 0.0
	for i in range(cds.size()):
		cds[i] = 0.0
	_buffer_idx = -1
	EventBus.player_respawned.emit()


func is_dead() -> bool:
	return act == Act.DEAD


func cooldown_fraction(i: int) -> float:
	if i >= cds.size() or cd_max[i] <= 0.0:
		return 0.0
	return clampf(cds[i] / cd_max[i], 0.0, 1.0)


func can_use_skill(i: int) -> bool:
	return i < skills.size() and skills[i] != null and cds[i] <= 0.0 and impeto.can_afford(skills[i].impeto_cost)


func _aim_pos() -> Vector2:
	if aim_override != null:
		return aim_override as Vector2
	return get_global_mouse_position()


func _poll() -> void:
	if act == Act.DEAD:
		return
	if Input.is_action_just_pressed("dodge"):
		_dodge_buffer = BUFFER_TIME
	for i in range(SKILL_ACTIONS.size()):
		var a: String = SKILL_ACTIONS[i]
		if i == 0:
			# Botão segurado repete o ataque básico sem atropelar uma skill em buffer.
			if Input.is_action_pressed(a) and (_buffer_idx < 0 or _buffer_idx == 0):
				_buffer_idx = 0
				_buffer_t = BUFFER_TIME
		elif Input.is_action_just_pressed(a):
			_buffer_idx = i
			_buffer_t = BUFFER_TIME


func _tick(delta: float) -> void:
	combatant.update(delta)
	impeto.update(delta)
	_sync_impeto_bonus()
	for i in range(cds.size()):
		cds[i] = maxf(0.0, cds[i] - delta)
	_update_dodge_charges(delta)
	_slash_t = maxf(0.0, _slash_t - delta)
	_rift_t = maxf(0.0, _rift_t - delta)
	_buffer_t = maxf(0.0, _buffer_t - delta)
	_dodge_buffer = maxf(0.0, _dodge_buffer - delta)
	if act == Act.DEAD:
		velocity = Vector2.ZERO
		return

	var aim: Vector2 = _aim_pos()
	var mv: Vector2 = Input.get_vector("move_left", "move_right", "move_up", "move_down")

	if _dodge_buffer > 0.0 and dodge_charges > 0 and act != Act.DODGE:
		_dodge_buffer = 0.0
		_start_dodge(mv)
	if act == Act.NONE and _buffer_idx >= 0 and _buffer_t > 0.0 and can_use_skill(_buffer_idx):
		var idx: int = _buffer_idx
		_buffer_idx = -1
		_start_skill(idx, aim)
	if _buffer_t <= 0.0:
		_buffer_idx = -1

	var move_vel: Vector2 = Vector2.ZERO
	match act:
		Act.NONE:
			var to_aim: Vector2 = aim - global_position
			if to_aim.length() > 4.0:
				facing = to_aim.normalized()
			move_vel = mv * hero.move_speed
		Act.SKILL:
			move_vel = _tick_skill(delta, mv)
		Act.DODGE:
			move_vel = _tick_dodge(delta)
	velocity = move_vel + kb_vel
	kb_vel = kb_vel.move_toward(Vector2.ZERO, hero.kb_decay * delta)
	move_and_slide()


func _sync_impeto_bonus() -> void:
	var pts: int = int(impeto.current)
	if pts == _last_pts:
		return
	_last_pts = pts
	combatant.stats.remove_source("impeto")
	if pts > 0:
		combatant.stats.add("damage", StatMod.Kind.INCREASED, float(pts) * hero.impeto_damage_per_point, PackedStringArray(), "impeto")


func _update_dodge_charges(delta: float) -> void:
	if dodge_charges >= hero.dodge_charges:
		dodge_progress = 0.0
		return
	dodge_progress += delta
	if dodge_progress >= hero.dodge_recharge:
		dodge_progress = 0.0
		dodge_charges += 1


func _start_skill(i: int, aim: Vector2) -> void:
	var sk: SkillData = skills[i]
	impeto.spend(sk.impeto_cost)
	cds[i] = Rules.clamp_cooldown(sk.cooldown)
	cd_max[i] = cds[i]
	act = Act.SKILL
	act_skill = sk
	act_t = 0.0
	_act_hit_done = false
	_hit_set.clear()
	var d: Vector2 = aim - global_position
	act_dir = d.normalized() if d.length() > 1.0 else facing
	facing = act_dir
	if sk.shape == SkillData.Shape.DASH:
		_dash_len = clampf(d.length(), sk.dash_min, sk.dash_distance)
	if sk.shape == SkillData.Shape.CONE:
		_rift_dir = act_dir
	EventBus.skill_used.emit(sk.id)


func _tick_skill(delta: float, mv: Vector2) -> Vector2:
	var sk: SkillData = act_skill
	if sk == null:
		act = Act.NONE
		return Vector2.ZERO
	act_t += delta
	var vel: Vector2 = mv * hero.move_speed * hero.action_move_mult
	var dash_time: float = 0.0
	if sk.shape == SkillData.Shape.DASH:
		dash_time = sk.dash_time
		if act_t < sk.windup:
			vel = Vector2.ZERO
		elif act_t < sk.windup + dash_time:
			vel = act_dir * (_dash_len / dash_time)
			if randf() < 0.5:
				EventBus.fx_dust.emit(global_position, 1)
		if not _act_hit_done and act_t >= sk.windup + dash_time:
			_act_hit_done = true
			_do_hit(sk)
			EventBus.fx_dust.emit(global_position, 12)
	elif not _act_hit_done and act_t >= sk.windup:
		_act_hit_done = true
		_do_hit(sk)
	if act_t >= sk.windup + dash_time + sk.recovery:
		act = Act.NONE
		act_skill = null
	return vel


func _start_dodge(mv: Vector2) -> void:
	dodge_charges -= 1
	act = Act.DODGE
	act_skill = null
	act_t = 0.0
	_dodge_dir = mv.normalized() if mv.length() > 0.1 else facing
	combatant.invulnerable = true
	EventBus.fx_dust.emit(global_position, 6)


func _tick_dodge(delta: float) -> Vector2:
	act_t += delta
	if act_t >= hero.dodge_invuln:
		combatant.invulnerable = false
	if act_t >= hero.dodge_duration:
		combatant.invulnerable = false
		act = Act.NONE
	return _dodge_dir * (hero.dodge_distance / hero.dodge_duration)


## Aplica o golpe da skill: consulta de forma na física + motor de regras.
func _do_hit(sk: SkillData) -> void:
	_slash_t = 0.18
	_slash_dir = act_dir
	_slash_skill = sk
	if sk.shape == SkillData.Shape.CONE:
		_rift_t = 0.6
	var shape: Shape2D
	var xf: Transform2D
	if sk.shape == SkillData.Shape.ARC or sk.shape == SkillData.Shape.CONE:
		var cv: ConvexPolygonShape2D = ConvexPolygonShape2D.new()
		cv.points = Geo.sector_points(sk.range_px, sk.arc_degrees, 10)
		shape = cv
		xf = Transform2D(act_dir.angle(), global_position)
	else:
		var circ: CircleShape2D = CircleShape2D.new()
		circ.radius = sk.radius_px
		shape = circ
		xf = Transform2D(0.0, global_position)
	for b in query_shape(shape, xf, 2):
		var e: Enemy = b as Enemy
		if e == null or e.is_dying():
			continue
		var uid: int = e.get_instance_id()
		if _hit_set.has(uid):
			continue
		_hit_set[uid] = true
		strike(e, HitSpec.from_skill(sk))


func on_hit_dealt(res: HitResult, spec: HitSpec) -> void:
	if res.evaded or res.invulnerable:
		return
	impeto.gain(spec.impeto_gain)
	impeto.mark_combat()


func on_hit_received(res: HitResult, spec: HitSpec, dir: Vector2) -> void:
	if res.invulnerable:
		return
	impeto.mark_combat()
	if res.evaded:
		return
	flash(0.12)
	if res.blocked:
		impeto.gain(hero.impeto_on_block)
		EventBus.player_blocked.emit(global_position)
	if spec.knockback > 0.0:
		kb_vel += dir * spec.knockback * 0.4
	if combatant.is_dead() and act != Act.DEAD:
		act = Act.DEAD
		combatant.invulnerable = true
		velocity = Vector2.ZERO
		EventBus.player_died.emit()


# ---------------------------------------------------------------- desenho

func _draw() -> void:
	if hero == null:
		return
	var alpha: float = 0.5 if combatant.invulnerable and act == Act.DODGE else 1.0
	if act == Act.DEAD:
		alpha = 0.45
	# Preparação visível da Fenda de Pedra.
	if act == Act.SKILL and act_skill != null and act_skill.shape == SkillData.Shape.CONE and act_t < act_skill.windup:
		_draw_cone(act_skill, act_t / act_skill.windup)
	if _rift_t > 0.0:
		_draw_fissures()
	draw_shadow(radius + 2.0, radius * 0.55)
	var f: Vector2 = facing
	var body: Color = tint(Palette.OCRE)
	var cloth: Color = tint(Palette.CARMESIM)
	var skin: Color = tint(Palette.PERGAMINHO)
	var metal: Color = tint(Palette.DOURADO)
	body.a = alpha
	cloth.a = alpha
	skin.a = alpha
	metal.a = alpha
	draw_rect(Rect2(-6, -22, 12, 16), body)
	draw_rect(Rect2(-6, -9, 12, 3), cloth)
	draw_rect(Rect2(-4, -30, 8, 8), skin)
	draw_rect(Rect2(-5, -31, 10, 3), metal)
	draw_rect(Rect2(-6, -6, 4, 6), cloth)
	draw_rect(Rect2(2, -6, 4, 6), cloth)
	# Espada à frente e escudo atrás do braço.
	var hand: Vector2 = Vector2(0, -15) + f * 8.0
	draw_line(hand, hand + f * 16.0, metal, 3.0)
	draw_rect(Rect2(hand - f * 12.0 - Vector2(3, 3), Vector2(6, 8)), cloth)
	if _slash_t > 0.0 and _slash_skill != null and _slash_skill.shape != SkillData.Shape.CONE:
		_draw_slash()


func _draw_slash() -> void:
	var sk: SkillData = _slash_skill
	var a: float = _slash_t / 0.18
	var col: Color = sk.color
	col.a = a * 0.9
	if sk.shape == SkillData.Shape.ARC:
		var half: float = deg_to_rad(sk.arc_degrees * 0.5)
		draw_arc(Vector2(0, -12), sk.range_px * 0.85, _slash_dir.angle() - half, _slash_dir.angle() + half, 14, col, 5.0)
	else:
		draw_arc(Vector2(0, -6), sk.radius_px * (1.1 - a * 0.3), 0.0, TAU, 24, col, 4.0)


func _draw_cone(sk: SkillData, progress: float) -> void:
	var pts: PackedVector2Array = PackedVector2Array()
	for p in Geo.sector_points(sk.range_px, sk.arc_degrees, 12):
		pts.append(p.rotated(act_dir.angle()))
	var fill: Color = Palette.PERIGO
	fill.a = lerpf(0.10, 0.35, progress)
	draw_colored_polygon(pts, fill)
	var line: Color = Palette.PERIGO
	line.a = 0.8
	draw_polyline(pts + PackedVector2Array([pts[0]]), line, 1.0)
	# Linha de preenchimento da preparação.
	var inner: PackedVector2Array = PackedVector2Array()
	for p in Geo.sector_points(sk.range_px * progress, sk.arc_degrees, 12):
		inner.append(p.rotated(act_dir.angle()))
	var core: Color = Palette.DOURADO
	core.a = 0.3
	draw_colored_polygon(inner, core)


func _draw_fissures() -> void:
	var k: float = _rift_t / 0.6
	var col: Color = Palette.PERGAMINHO
	col.a = k
	var dark: Color = Palette.CARVAO
	dark.a = k
	for i in range(5):
		var ang: float = _rift_dir.angle() + deg_to_rad(lerpf(-28.0, 28.0, float(i) / 4.0))
		var d: Vector2 = Vector2.RIGHT.rotated(ang)
		var n: Vector2 = d.orthogonal()
		var pts: PackedVector2Array = PackedVector2Array()
		var len: float = _slash_skill.range_px * 0.95 * minf(1.0, (1.0 - k) * 4.0 + 0.2)
		var t: float = 12.0
		while t < len:
			pts.append(d * t + n * (sin(t * 0.21 + float(i)) * 6.0))
			t += 14.0
		if pts.size() >= 2:
			draw_polyline(pts, dark, 5.0)
			draw_polyline(pts, col, 2.0)
