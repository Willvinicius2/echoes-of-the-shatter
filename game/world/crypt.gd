class_name Crypt
extends Node2D
## A Cripta: sala de entrada (2 ondas de Sentinelas), corredor e arena do Guardião.
## Orquestra o fluxo do encontro; os números (ondas, atrasos, cura) vêm de EncounterData.

enum Stage { WAIT_START, WAVE, BETWEEN, CLEARED, BOSS, VICTORY }

const ROOM_A: Rect2 = Rect2(0, 0, 800, 480)
const CORRIDOR: Rect2 = Rect2(800, 200, 100, 80)
const ARENA: Rect2 = Rect2(900, -40, 800, 560)
const PLAYER_START: Vector2 = Vector2(120, 240)
const ARENA_START: Vector2 = Vector2(980, 240)
const BOSS_POS: Vector2 = Vector2(1500, 240)
const ARENA_TRIGGER_X: float = 950.0
const CAMERA_Y: float = 240.0

var stage: int = Stage.WAIT_START
var wave: int = 0
var stage_t: float = 0.0
var checkpoint_pos: Vector2 = PLAYER_START
var player: Player
var boss: Enemy = null

var _enc: EncounterData
var _floor: CryptFloor
var _fx: FxLayer
var _hud: Hud
var _cam: Camera2D
var _enemies_root: Node2D
var _doors: Array[StaticBody2D] = []
var _shake: float = 0.0
var _shake_t: float = 0.0
var _respawn_serial: int = 0
var _watch_t: float = 0.0
var _rng_vis: RandomNumberGenerator = RandomNumberGenerator.new()


func _ready() -> void:
	_enc = DataDB.get_encounter("encounter.crypt")
	if _enc == null:
		push_error("EncounterData 'encounter.crypt' não encontrado")
		return
	_build_world()
	_enemies_root = Node2D.new()
	_enemies_root.name = "Enemies"
	add_child(_enemies_root)
	_spawn_player()
	_fx = FxLayer.new()
	add_child(_fx)
	_cam = Camera2D.new()
	add_child(_cam)
	_cam.make_current()
	_cam.global_position = Vector2(PLAYER_START.x + 360.0, CAMERA_Y)
	var layer: CanvasLayer = CanvasLayer.new()
	layer.layer = 10
	add_child(layer)
	_hud = Hud.new()
	layer.add_child(_hud)
	_hud.player = player
	EventBus.screen_shake.connect(_on_shake)
	EventBus.player_died.connect(_on_player_died)
	EventBus.boss_defeated.connect(_on_boss_defeated)
	EventBus.boss_phase_changed.connect(_on_boss_phase)
	EventBus.summon_requested.connect(_on_summon)
	EventBus.checkpoint_reached.emit("cripta.entrada")


# ---------------------------------------------------------------- construção

func _build_world() -> void:
	_floor = CryptFloor.new()
	add_child(_floor)
	_floor.floors = [ROOM_A, CORRIDOR, ARENA]
	var walls: Array[Rect2] = [
		Rect2(-32, -32, 864, 32), Rect2(-32, 0, 32, 480), Rect2(-32, 480, 864, 32),
		Rect2(800, 0, 32, 200), Rect2(800, 280, 32, 200),
		Rect2(832, 168, 36, 32), Rect2(832, 280, 36, 32),
		Rect2(868, -72, 864, 32), Rect2(868, 520, 864, 32),
		Rect2(868, -40, 32, 240), Rect2(868, 280, 32, 240),
		Rect2(1700, -72, 32, 656),
	]
	_floor.walls = walls
	for w in walls:
		_add_solid(w)
	# Portas: 0 = entre a sala e o corredor, 1 = entre o corredor e a arena.
	var door_rects: Array[Rect2] = [Rect2(832, 200, 16, 80), Rect2(852, 200, 16, 80)]
	_floor.doors = door_rects
	_floor.door_closed = [true, false]
	for d in door_rects:
		_doors.append(_add_solid(d))
	_set_door(1, false)
	_floor.queue_redraw()


func _add_solid(r: Rect2) -> StaticBody2D:
	var body: StaticBody2D = StaticBody2D.new()
	body.collision_layer = 4
	body.collision_mask = 0
	body.position = r.get_center()
	var cs: CollisionShape2D = CollisionShape2D.new()
	var rs: RectangleShape2D = RectangleShape2D.new()
	rs.size = r.size
	cs.shape = rs
	body.add_child(cs)
	add_child(body)
	return body


func _set_door(index: int, closed: bool) -> void:
	_floor.door_closed[index] = closed
	var cs: CollisionShape2D = _doors[index].get_child(0) as CollisionShape2D
	cs.set_deferred("disabled", not closed)
	_floor.queue_redraw()


func _spawn_player() -> void:
	var hero: ClassData = DataDB.get_hero("class.warrior")
	player = Player.new()
	player.setup(hero)
	player.position = PLAYER_START
	add_child(player)


func _spawn_enemy(id: String, pos: Vector2, group: int, alerted: bool) -> Enemy:
	var d: EnemyData = DataDB.get_enemy(id)
	if d == null:
		push_error("EnemyData não encontrado: %s" % id)
		return null
	var e: Enemy = Enemy.new()
	e.setup(d, pos, group)
	_enemies_root.add_child(e)
	if alerted:
		e.alert_now()
	return e


# ---------------------------------------------------------------- fluxo

func _process(delta: float) -> void:
	if _enc == null:
		return
	_update_camera(delta)
	_update_flow(delta)
	_watchdog(delta)


func _update_flow(delta: float) -> void:
	match stage:
		Stage.WAIT_START:
			stage_t += delta
			if stage_t >= _enc.wave_start_delay:
				_start_wave(1)
		Stage.WAVE:
			if not player.is_dead() and _alive_enemies() == 0:
				_finish_wave()
		Stage.BETWEEN:
			stage_t += delta
			if stage_t >= _enc.between_waves_delay:
				_start_wave(wave + 1)
		Stage.CLEARED:
			if player.global_position.x > ARENA_TRIGGER_X:
				_start_boss()
	_hud.status_line = _status_text()


func _status_text() -> String:
	match stage:
		Stage.WAVE:
			return "Onda %d / %d · inimigos: %d" % [wave, _enc.waves.size(), _alive_enemies()]
		Stage.CLEARED:
			return "A porta está aberta. Siga para a arena."
	return ""


func _alive_enemies() -> int:
	var n: int = 0
	for c in _enemies_root.get_children():
		var e: Enemy = c as Enemy
		if e != null and not e.is_dying() and not e.is_queued_for_deletion():
			n += 1
	return n


func _clear_enemies() -> void:
	for c in _enemies_root.get_children():
		c.queue_free()


func _start_wave(index: int) -> void:
	wave = index
	stage = Stage.WAVE
	var count: int = _enc.waves[index - 1]
	var rng: RandomNumberGenerator = Game.rng.stream(RngStreams.EVENTS)
	for i in range(count):
		var col: int = i % 2
		var row: int = i / 2
		var pos: Vector2 = Vector2(480.0 + col * 120.0, 120.0 + row * 120.0) + Vector2(rng.randf_range(-20.0, 20.0), rng.randf_range(-20.0, 20.0))
		_spawn_enemy(_enc.wave_enemy_id, pos, index, false)
	EventBus.wave_started.emit(index, _enc.waves.size())
	_hud.show_banner("Onda %d" % index, 1.4)


func _finish_wave() -> void:
	EventBus.wave_cleared.emit(wave)
	player.combatant.heal(player.combatant.max_life() * _enc.heal_on_wave_clear)
	if wave >= _enc.waves.size():
		stage = Stage.CLEARED
		_set_door(0, false)
		checkpoint_pos = Vector2(700, 240)
		EventBus.checkpoint_reached.emit("cripta.sala_limpa")
		_hud.show_banner("Sala limpa", 1.8)
	else:
		stage = Stage.BETWEEN
		stage_t = 0.0


func _start_boss() -> void:
	stage = Stage.BOSS
	_set_door(1, true)
	checkpoint_pos = ARENA_START
	EventBus.checkpoint_reached.emit("cripta.arena")
	_spawn_boss()


func _spawn_boss() -> void:
	boss = _spawn_enemy(_enc.boss_id, BOSS_POS, 100, true)
	if boss != null:
		_hud.boss = boss
		EventBus.boss_spawned.emit(boss)
		_hud.show_banner("Guardião da Cripta", 2.0)


func _on_boss_phase(_id: String, p: int) -> void:
	_hud.show_banner("O Guardião invoca ecos!", 2.0)
	_shake_it(4.0, 0.3)


func _on_summon(enemy_id: String, count: int, around: Vector2) -> void:
	for i in range(count):
		var side: float = -1.0 if i % 2 == 0 else 1.0
		var pos: Vector2 = around + Vector2(side * 90.0, 70.0 * (float(i) - 0.5))
		pos.x = clampf(pos.x, ARENA.position.x + 40.0, ARENA.end.x - 40.0)
		pos.y = clampf(pos.y, ARENA.position.y + 40.0, ARENA.end.y - 40.0)
		_spawn_enemy(enemy_id, pos, 101, true)


func _on_boss_defeated(_id: String) -> void:
	stage = Stage.VICTORY
	_hud.show_banner("Vitória! O Guardião da Cripta caiu.", 6.0)
	_hud.status_line = ""


# ---------------------------------------------------------------- morte e checkpoint

func _on_player_died() -> void:
	_respawn_serial += 1
	var serial: int = _respawn_serial
	_hud.show_banner("Você caiu...", _enc.respawn_delay)
	await get_tree().create_timer(_enc.respawn_delay).timeout
	if serial != _respawn_serial or not is_inside_tree():
		return
	_respawn()


func _respawn() -> void:
	match stage:
		Stage.BOSS:
			# Arena do chefe: reinicia a luta na hora, sem perder nada.
			_clear_enemies()
			player.respawn(ARENA_START)
			_spawn_boss()
		Stage.WAVE, Stage.BETWEEN, Stage.WAIT_START:
			_clear_enemies()
			player.respawn(checkpoint_pos)
			wave = maxi(wave - 1, 0) if stage == Stage.WAVE else wave
			stage = Stage.WAIT_START if wave == 0 else Stage.BETWEEN
			stage_t = 0.0
		_:
			player.respawn(checkpoint_pos)


## Gancho de teste: pula direto para a luta contra o chefe.
func debug_start_boss() -> void:
	_clear_enemies()
	wave = _enc.waves.size()
	_set_door(0, false)
	player.respawn(ARENA_START)
	_start_boss()


# ---------------------------------------------------------------- câmera e robustez

func _on_shake(strength: float, duration: float) -> void:
	_shake_it(strength, duration)


func _shake_it(strength: float, duration: float) -> void:
	if not Game.shake_enabled:
		return
	_shake = maxf(_shake, strength)
	_shake_t = maxf(_shake_t, duration)


func _update_camera(delta: float) -> void:
	var target: Vector2 = Vector2(clampf(player.global_position.x, 480.0, 1220.0), CAMERA_Y)
	var base: Vector2 = _cam.global_position.lerp(target, clampf(8.0 * delta, 0.0, 1.0))
	var off: Vector2 = Vector2.ZERO
	if _shake_t > 0.0:
		_shake_t -= delta
		off = Vector2(_rng_vis.randf_range(-1.0, 1.0), _rng_vis.randf_range(-1.0, 1.0)) * _shake
		if _shake_t <= 0.0:
			_shake = 0.0
	_cam.global_position = (base + off).round()


## Um erro/estado preso em um inimigo não pode travar o encontro.
func _watchdog(delta: float) -> void:
	_watch_t += delta
	if _watch_t < 1.0:
		return
	_watch_t = 0.0
	for c in _enemies_root.get_children():
		var e: Enemy = c as Enemy
		if e != null and e.is_stuck():
			push_warning("Inimigo preso em estado %d; reiniciando." % e.state)
			e.force_reset()
