class_name FxLayer
extends Node2D
## Partículas e números de dano em POOLS de tamanho fixo (sem alocação por golpe).
## Reage aos sinais do EventBus; não calcula nada de regras.

const MAX_PARTICLES: int = 400
const MAX_NUMBERS: int = 48
const NUMBER_LIFE: float = 0.8

var _p_pos: PackedVector2Array = PackedVector2Array()
var _p_vel: PackedVector2Array = PackedVector2Array()
var _p_life: PackedFloat32Array = PackedFloat32Array()
var _p_max: PackedFloat32Array = PackedFloat32Array()
var _p_size: PackedFloat32Array = PackedFloat32Array()
var _p_grav: PackedFloat32Array = PackedFloat32Array()
var _p_col: PackedColorArray = PackedColorArray()
var _p_cursor: int = 0

var _n_pos: PackedVector2Array = PackedVector2Array()
var _n_life: PackedFloat32Array = PackedFloat32Array()
var _n_size: PackedInt32Array = PackedInt32Array()
var _n_col: PackedColorArray = PackedColorArray()
var _n_text: Array[String] = []
var _n_cursor: int = 0

var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _font: Font


func _ready() -> void:
	z_index = 50
	_font = ThemeDB.fallback_font
	_p_pos.resize(MAX_PARTICLES)
	_p_vel.resize(MAX_PARTICLES)
	_p_life.resize(MAX_PARTICLES)
	_p_max.resize(MAX_PARTICLES)
	_p_size.resize(MAX_PARTICLES)
	_p_grav.resize(MAX_PARTICLES)
	_p_col.resize(MAX_PARTICLES)
	_n_pos.resize(MAX_NUMBERS)
	_n_life.resize(MAX_NUMBERS)
	_n_size.resize(MAX_NUMBERS)
	_n_col.resize(MAX_NUMBERS)
	_n_text.resize(MAX_NUMBERS)
	_rng.randomize()
	EventBus.damage_dealt.connect(_on_damage)
	EventBus.enemy_dissolved.connect(_on_dissolved)
	EventBus.fx_dust.connect(_on_dust)
	EventBus.guard_broken.connect(_on_guard_broken)
	EventBus.player_blocked.connect(_on_blocked)


func _process(delta: float) -> void:
	for i in range(MAX_PARTICLES):
		if _p_life[i] <= 0.0:
			continue
		_p_life[i] -= delta
		_p_vel[i].y += _p_grav[i] * delta
		_p_pos[i] += _p_vel[i] * delta
	for i in range(MAX_NUMBERS):
		if _n_life[i] > 0.0:
			_n_life[i] -= delta
			_n_pos[i].y -= 28.0 * delta
	queue_redraw()


func _draw() -> void:
	for i in range(MAX_PARTICLES):
		if _p_life[i] <= 0.0:
			continue
		var c: Color = _p_col[i]
		c.a = clampf(_p_life[i] / _p_max[i], 0.0, 1.0)
		var s: float = _p_size[i]
		draw_rect(Rect2(_p_pos[i].round(), Vector2(s, s)), c)
	for i in range(MAX_NUMBERS):
		if _n_life[i] <= 0.0:
			continue
		var c2: Color = _n_col[i]
		c2.a = clampf(_n_life[i] / NUMBER_LIFE * 1.6, 0.0, 1.0)
		var o: Color = Palette.CARVAO
		o.a = c2.a
		var p: Vector2 = _n_pos[i].round()
		draw_string_outline(_font, p, _n_text[i], HORIZONTAL_ALIGNMENT_CENTER, 120.0, _n_size[i], 4, o)
		draw_string(_font, p, _n_text[i], HORIZONTAL_ALIGNMENT_CENTER, 120.0, _n_size[i], c2)


func emit_particle(pos: Vector2, vel: Vector2, life: float, size: float, col: Color, grav: float) -> void:
	var i: int = _p_cursor
	for n in range(MAX_PARTICLES):
		var j: int = (_p_cursor + n) % MAX_PARTICLES
		if _p_life[j] <= 0.0:
			i = j
			break
	_p_pos[i] = pos
	_p_vel[i] = vel
	_p_life[i] = life
	_p_max[i] = life
	_p_size[i] = size
	_p_col[i] = col
	_p_grav[i] = grav
	_p_cursor = (i + 1) % MAX_PARTICLES


func burst(pos: Vector2, count: int, speed: float, life: float, size: float, colors: Array[Color], grav: float, dir: Vector2 = Vector2.ZERO, spread: float = PI) -> void:
	for n in range(count):
		var base: float = dir.angle() if dir != Vector2.ZERO else _rng.randf() * TAU
		var a: float = base + _rng.randf_range(-spread, spread)
		var v: Vector2 = Vector2.RIGHT.rotated(a) * speed * _rng.randf_range(0.4, 1.0)
		emit_particle(pos, v, life * _rng.randf_range(0.6, 1.0), size, colors[_rng.randi() % colors.size()], grav)


func add_number(pos: Vector2, text: String, size: int, col: Color) -> void:
	var i: int = _n_cursor
	_n_pos[i] = pos + Vector2(_rng.randf_range(-6.0, 6.0), 0.0)
	_n_life[i] = NUMBER_LIFE
	_n_size[i] = size
	_n_col[i] = col
	_n_text[i] = text
	_n_cursor = (i + 1) % MAX_NUMBERS


func _on_damage(_a: String, _t: String, res: HitResult, pos: Vector2, target_is_player: bool) -> void:
	if res.invulnerable:
		return
	var head: Vector2 = pos + Vector2(0, -34)
	if res.evaded:
		add_number(head, "esquivou", 11, Palette.PERGAMINHO)
		return
	var amount: int = int(round(res.final_damage))
	var txt: String = str(amount)
	var size: int = 14
	var col: Color = Palette.PERGAMINHO
	if target_is_player:
		col = Palette.PERIGO
		size = 16
	elif res.crit:
		col = Palette.DOURADO
		size = 24
		txt += "!"
	elif res.shield_reduced:
		col = Palette.OCRE
		size = 11
	elif amount >= 40:
		size = 18
	if res.blocked:
		txt = "bloq. " + txt
	add_number(head, txt, size, col)
	var sparks: Array[Color] = [Palette.DOURADO, Palette.PERGAMINHO, Palette.PERIGO]
	if target_is_player:
		sparks = [Palette.PERIGO, Palette.CARMESIM]
	var n: int = 10 if res.crit else (7 if res.final_damage >= 40.0 else 4)
	burst(pos + Vector2(0, -12), n, 150.0, 0.3, 2.0, sparks, 200.0)
	var dust: Array[Color] = [Palette.OCRE, Palette.CHAO_LINHA]
	burst(pos + Vector2(0, -2), 3, 60.0, 0.45, 3.0, dust, -20.0)


func _on_dissolved(pos: Vector2, is_boss: bool) -> void:
	var golds: Array[Color] = [Palette.DOURADO, Palette.PERGAMINHO, Palette.OCRE]
	burst(pos + Vector2(0, -12), 60 if is_boss else 24, 170.0 if is_boss else 110.0, 0.9, 3.0, golds, 140.0, Vector2.UP, PI * 0.8)


func _on_dust(pos: Vector2, amount: int) -> void:
	var dust: Array[Color] = [Palette.OCRE, Palette.CHAO_LINHA, Palette.PERGAMINHO]
	burst(pos, amount, 70.0, 0.5, 3.0, dust, -30.0)


func _on_guard_broken(_id: String, pos: Vector2) -> void:
	add_number(pos + Vector2(0, -50), "guarda quebrada", 11, Palette.DOURADO)
	var golds: Array[Color] = [Palette.DOURADO, Palette.PERGAMINHO]
	burst(pos + Vector2(0, -14), 14, 130.0, 0.5, 2.0, golds, 120.0)


func _on_blocked(pos: Vector2) -> void:
	var sp: Array[Color] = [Palette.PERGAMINHO, Palette.DOURADO]
	burst(pos + Vector2(0, -14), 8, 140.0, 0.3, 2.0, sp, 100.0)
