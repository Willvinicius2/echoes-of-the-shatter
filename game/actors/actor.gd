class_name Actor
extends CharacterBody2D
## Base de jogador e inimigos. Só apresentação + ponte para o motor de regras:
## todo dano passa por DamageCalc (via strike()).

var combatant: Combatant
var facing: Vector2 = Vector2.RIGHT
var radius: float = 10.0
## Hitstop POR ENTIDADE: só quem bateu e quem apanhou pausam.
var hitstop_left: float = 0.0
var flash_left: float = 0.0
var kb_vel: Vector2 = Vector2.ZERO


func _ready() -> void:
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	var cs: CollisionShape2D = CollisionShape2D.new()
	var c: CircleShape2D = CircleShape2D.new()
	c.radius = radius
	cs.shape = c
	add_child(cs)


func _physics_process(delta: float) -> void:
	_poll()
	if hitstop_left > 0.0:
		hitstop_left -= delta
		return
	_tick(delta)


func _process(delta: float) -> void:
	flash_left = maxf(0.0, flash_left - delta)
	queue_redraw()


## Lido mesmo durante o hitstop (ex.: buffer de input).
func _poll() -> void:
	pass


func _tick(_delta: float) -> void:
	pass


func apply_hitstop(seconds: float) -> void:
	hitstop_left = maxf(hitstop_left, seconds)


func flash(seconds: float = 0.1) -> void:
	flash_left = maxf(flash_left, seconds)


func on_hit_received(_res: HitResult, _spec: HitSpec, _dir: Vector2) -> void:
	pass


func on_hit_dealt(_res: HitResult, _spec: HitSpec) -> void:
	pass


## Resolve um golpe contra `target` pelo motor de regras e dispara os efeitos.
func strike(target: Actor, spec: HitSpec) -> HitResult:
	if target == null or not is_instance_valid(target) or target.combatant == null:
		return null
	if target.combatant.is_dead():
		return null
	var to_attacker: Vector2 = global_position - target.global_position
	if target.combatant.shield_arc_degrees > 0.0:
		spec.from_front = Geo.in_front(target.facing, to_attacker, target.combatant.shield_arc_degrees)
	var rng: RandomNumberGenerator = Game.rng.stream(RngStreams.COMBAT)
	var res: HitResult = DamageCalc.resolve(combatant, target.combatant, spec, rng)
	target.combatant.take(res)
	var dir: Vector2 = (target.global_position - global_position).normalized()
	EventBus.damage_dealt.emit(combatant.id, target.combatant.id, res, target.global_position, target is Player)
	target.on_hit_received(res, spec, dir)
	on_hit_dealt(res, spec)
	if not res.evaded and not res.invulnerable:
		var hs: float = spec.hitstop_s
		if res.crit:
			hs = maxf(hs, 0.06)
		if hs > 0.0:
			apply_hitstop(hs)
			target.apply_hitstop(hs)
		var sh: float = spec.shake
		if res.crit:
			sh = maxf(sh, 2.0)
		if sh > 0.0:
			EventBus.screen_shake.emit(sh, 0.18)
	return res


## Consulta de forma na física. Retorna os corpos dentro da máscara.
func query_shape(shape: Shape2D, xform: Transform2D, mask: int) -> Array[Node]:
	var out: Array[Node] = []
	var params: PhysicsShapeQueryParameters2D = PhysicsShapeQueryParameters2D.new()
	params.shape = shape
	params.transform = xform
	params.collision_mask = mask
	params.collide_with_bodies = true
	params.exclude = [get_rid()]
	var hits: Array[Dictionary] = get_world_2d().direct_space_state.intersect_shape(params, 32)
	for h in hits:
		var c: Node = h["collider"] as Node
		if c != null:
			out.append(c)
	return out


func tint(c: Color) -> Color:
	return Color.WHITE if flash_left > 0.0 else c


func draw_shadow(rx: float, ry: float) -> void:
	var pts: PackedVector2Array = PackedVector2Array()
	for i in range(14):
		var a: float = TAU * float(i) / 14.0
		pts.append(Vector2(cos(a) * rx, sin(a) * ry + 2.0))
	draw_colored_polygon(pts, Color(0, 0, 0, 0.35))
