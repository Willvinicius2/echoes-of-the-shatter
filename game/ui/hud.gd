class_name Hud
extends Control
## HUD desenhado em código: vida, Ímpeto, cargas de esquiva, 4 skills e barra do chefe.

const KEY_LABELS: PackedStringArray = ["M1", "M2", "Q", "E"]

var player: Player = null
var boss: Enemy = null
var banner: String = ""
var banner_t: float = 0.0
var hint_t: float = 10.0
var status_line: String = ""
var _font: Font


func _ready() -> void:
	_font = ThemeDB.fallback_font
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)


func show_banner(text: String, seconds: float) -> void:
	banner = text
	banner_t = seconds


func _process(delta: float) -> void:
	banner_t = maxf(0.0, banner_t - delta)
	hint_t = maxf(0.0, hint_t - delta)
	if boss != null and not is_instance_valid(boss):
		boss = null
	queue_redraw()


func _text(pos: Vector2, s: String, size: int, col: Color, align: int = HORIZONTAL_ALIGNMENT_LEFT, width: float = -1.0) -> void:
	draw_string_outline(_font, pos, s, align, width, size, 3, Palette.CARVAO)
	draw_string(_font, pos, s, align, width, size, col)


func _bar(r: Rect2, frac: float, col: Color) -> void:
	draw_rect(r.grow(2.0), Palette.CARVAO)
	draw_rect(r, Color(0.12, 0.1, 0.08))
	draw_rect(Rect2(r.position, Vector2(r.size.x * clampf(frac, 0.0, 1.0), r.size.y)), col)
	draw_rect(r.grow(1.0), Palette.DOURADO, false, 1.0)


func _draw() -> void:
	if player == null or not is_instance_valid(player) or player.combatant == null:
		return
	var cb: Combatant = player.combatant
	# Vida e Ímpeto
	_bar(Rect2(16, 490, 220, 14), cb.life / cb.max_life(), Palette.CARMESIM)
	_text(Vector2(20, 502), "Vida %d / %d" % [int(ceil(cb.life)), int(cb.max_life())], 11, Palette.PERGAMINHO)
	_bar(Rect2(16, 512, 220, 8), player.impeto.current / player.impeto.max_value, Palette.DOURADO)
	_text(Vector2(244, 520), "Ímpeto %d" % int(player.impeto.current), 11, Palette.DOURADO)
	# Cargas de esquiva
	for i in range(player.hero.dodge_charges):
		var r: Rect2 = Rect2(16 + i * 22, 470, 18, 8)
		draw_rect(r.grow(1.0), Palette.CARVAO)
		var f: float = 0.0
		if i < player.dodge_charges:
			f = 1.0
		elif i == player.dodge_charges:
			f = player.dodge_progress / player.hero.dodge_recharge
		draw_rect(Rect2(r.position, Vector2(r.size.x * f, r.size.y)), Palette.PERGAMINHO if f >= 1.0 else Palette.OCRE)
		draw_rect(r, Palette.OCRE, false, 1.0)
	_text(Vector2(86, 478), "Esquiva (Espaço)", 10, Palette.OCRE)
	# Skills
	var n: int = player.skills.size()
	var x0: float = 480.0 - (n * 46.0) * 0.5
	for i in range(n):
		var sk: SkillData = player.skills[i]
		var r2: Rect2 = Rect2(x0 + i * 46.0, 484, 40, 40)
		var usable: bool = player.can_use_skill(i)
		draw_rect(r2.grow(2.0), Palette.CARVAO)
		draw_rect(r2, Color(0.2, 0.15, 0.1) if usable else Color(0.12, 0.09, 0.07))
		draw_rect(r2.grow(1.0), Palette.DOURADO if usable else Palette.OCRE, false, 1.0)
		_text(Vector2(r2.position.x, r2.position.y + 25), sk.short_name, 16, sk.color if usable else Palette.OCRE, HORIZONTAL_ALIGNMENT_CENTER, r2.size.x)
		var cdf: float = player.cooldown_fraction(i)
		if cdf > 0.0:
			draw_rect(Rect2(r2.position, Vector2(r2.size.x, r2.size.y * cdf)), Color(0, 0, 0, 0.65))
		elif not player.impeto.can_afford(sk.impeto_cost):
			draw_rect(r2, Color(0.55, 0.14, 0.15, 0.35))
		_text(Vector2(r2.position.x, r2.position.y + 52), KEY_LABELS[i], 10, Palette.PERGAMINHO, HORIZONTAL_ALIGNMENT_CENTER, r2.size.x)
		if sk.impeto_cost > 0.0:
			_text(Vector2(r2.position.x + 2, r2.position.y + 10), str(int(sk.impeto_cost)), 9, Palette.DOURADO)
	# Chefe
	if boss != null and is_instance_valid(boss) and boss.combatant != null and not boss.is_dying():
		var br: Rect2 = Rect2(280, 24, 400, 12)
		_bar(br, boss.combatant.life / boss.combatant.max_life(), Palette.PERIGO)
		_text(Vector2(280, 18), boss.data.display_name, 13, Palette.PERGAMINHO, HORIZONTAL_ALIGNMENT_CENTER, 400.0)
		var g: float = boss.combatant.guard.fraction()
		draw_rect(Rect2(280, 40, 400.0 * g, 3), Palette.DOURADO)
	# Status e dicas
	if status_line != "" and boss == null:
		_text(Vector2(0, 16), status_line, 12, Palette.PERGAMINHO, HORIZONTAL_ALIGNMENT_CENTER, 960.0)
	if hint_t > 0.0:
		_text(Vector2(0, 440), "WASD mover · mouse mira · M1 Corte · M2 Investida · Q Escudada · E Fenda de Pedra · Espaço esquiva", 11, Palette.PERGAMINHO, HORIZONTAL_ALIGNMENT_CENTER, 960.0)
	if banner_t > 0.0:
		var c: Color = Palette.DOURADO
		c.a = clampf(banner_t, 0.0, 1.0)
		_text(Vector2(0, 250), banner, 28, c, HORIZONTAL_ALIGNMENT_CENTER, 960.0)
