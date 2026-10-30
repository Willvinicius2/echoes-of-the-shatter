extends CanvasLayer
## HUD: vida, esquiva, sala atual, vida do chefe e mensagem central. Textos por chave de localização.

const Csv = preload("res://scripts2d/csv2d.gd")

var jogador: Node2D
var sala := 1
var total_salas := 1
var mensagem := ""
var chefe: Node2D
var upgrades: RefCounted
var tempo := 0.0
var _ctl: Control

func _ready() -> void:
	_ctl = Control.new()
	_ctl.set_anchors_preset(Control.PRESET_FULL_RECT)
	_ctl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ctl.draw.connect(_desenhar)
	add_child(_ctl)

func _process(_d: float) -> void:
	_ctl.queue_redraw()

func _desenhar() -> void:
	var fonte := ThemeDB.fallback_font
	var vp := _ctl.size
	if jogador != null and "hp" in jogador:
		var hmax: float = jogador.stats.get("hp_max", 1.0)
		_barra(Vector2(24, 24), Vector2(300, 22), jogador.hp / hmax, Color(0.75, 0.15, 0.15))
		_ctl.draw_string(fonte, Vector2(30, 41), Csv.t("hud.hp"), HORIZONTAL_ALIGNMENT_LEFT, -1, 14)
		var cdmax: float = jogador.stats.get("dodge_cooldown", 1.0)
		_barra(Vector2(24, 52), Vector2(300, 10), 1.0 - jogador.dodge_cd / cdmax, Color(0.3, 0.7, 0.9))
	if upgrades != null and not upgrades.niveis.is_empty():
		var y := 86.0
		for id in upgrades.ordem:
			var nv: int = upgrades.nivel(id)
			if nv > 0:
				_ctl.draw_string(fonte, Vector2(24, y), "%s x%d" % [Csv.t("upgrade.%s.name" % id), nv], HORIZONTAL_ALIGNMENT_LEFT, -1, 16)
				y += 20.0
	_ctl.draw_string(fonte, Vector2(vp.x - 200, 40), Csv.t("hud.room") % [sala, total_salas], HORIZONTAL_ALIGNMENT_LEFT, -1, 22)
	_ctl.draw_string(fonte, Vector2(vp.x - 200, 66), Csv.t("hud.time") % _tempo_texto(), HORIZONTAL_ALIGNMENT_LEFT, -1, 18)
	_ctl.draw_string(fonte, Vector2(24, vp.y - 20), Csv.t("hud.help"), HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(1, 1, 1, 0.6))
	if chefe != null and is_instance_valid(chefe) and chefe.hp > 0.0:
		_barra(Vector2(vp.x / 2 - 300, vp.y - 60), Vector2(600, 16), chefe.hp / chefe.hp_max, Color(0.6, 0.2, 0.7))
		_ctl.draw_string(fonte, Vector2(vp.x / 2 - 300, vp.y - 66), Csv.t("hud.boss"), HORIZONTAL_ALIGNMENT_LEFT, -1, 16)
	if mensagem != "":
		_ctl.draw_string(fonte, Vector2(0, vp.y * 0.3), mensagem, HORIZONTAL_ALIGNMENT_CENTER, vp.x, 32)

func _tempo_texto() -> String:
	var total := int(tempo)
	return "%02d:%02d" % [total / 60, total % 60]

func _barra(pos: Vector2, tam: Vector2, frac: float, cor: Color) -> void:
	_ctl.draw_rect(Rect2(pos - Vector2(2, 2), tam + Vector2(4, 4)), Color(0.05, 0.05, 0.07, 0.9))
	_ctl.draw_rect(Rect2(pos, Vector2(tam.x * clampf(frac, 0.0, 1.0), tam.y)), cor)
