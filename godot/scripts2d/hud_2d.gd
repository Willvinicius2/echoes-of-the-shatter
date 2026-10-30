extends CanvasLayer
## HUD: vida, esquiva, sala atual, vida do chefe e mensagem central. Textos por chave de localização.

const Csv = preload("res://scripts2d/csv2d.gd")
const Tema = preload("res://scripts2d/tema_2d.gd")
const Icones = preload("res://scripts2d/icones_2d.gd")

var jogador: Node2D
var sala := 1
var total_salas := 1
var mensagem := ""
var chefe: Node2D
var upgrades: RefCounted
var tempo := 0.0
var _ctl: Control
var _lay := {}

func _ready() -> void:
	_lay = Csv.kv("res://data2d/hud_layout.csv")
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
		_desenhar_barras(fonte)
		_desenhar_habilidades(fonte, vp)
	if upgrades != null and not upgrades.niveis.is_empty():
		var y: float = _lay["lista_y"]
		for id in upgrades.ordem:
			var nv: int = upgrades.nivel(id)
			if nv > 0:
				_ctl.draw_texture_rect(Icones.textura(id), Rect2(_lay["margem"], y - 16, 20, 20), false)
				_ctl.draw_string(fonte, Vector2(_lay["margem"] + 28, y), "%s x%d" % [Csv.t("upgrade.%s.name" % id), nv], HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Tema.cor("texto"))
				y += 24.0
	_ctl.draw_string(fonte, Vector2(vp.x - 200, 40), Csv.t("hud.room") % [sala, total_salas], HORIZONTAL_ALIGNMENT_LEFT, -1, 22)
	_ctl.draw_string(fonte, Vector2(vp.x - 200, 66), Csv.t("hud.time") % _tempo_texto(), HORIZONTAL_ALIGNMENT_LEFT, -1, 18)
	_ctl.draw_string(fonte, Vector2(0, vp.y - 12), Csv.t("hud.help"), HORIZONTAL_ALIGNMENT_RIGHT, vp.x - _lay["margem"], 13, Tema.cor("texto_suave"))
	if chefe != null and is_instance_valid(chefe) and chefe.hp > 0.0:
		_barra(Vector2(vp.x / 2 - 300, 44), Vector2(600, 16), chefe.hp / chefe.hp_max, Color(0.6, 0.2, 0.7))
		_ctl.draw_string(fonte, Vector2(vp.x / 2 - 300, 34), Csv.t("hud.boss"), HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Tema.cor("destaque"))
	if mensagem != "":
		_ctl.draw_string(fonte, Vector2(0, vp.y * 0.3), mensagem, HORIZONTAL_ALIGNMENT_CENTER, vp.x, 32)

func _tempo_texto() -> String:
	var total := int(tempo)
	return "%02d:%02d" % [total / 60, total % 60]

func _barra(pos: Vector2, tam: Vector2, frac: float, cor: Color) -> void:
	_ctl.draw_style_box(Tema.caixa(Color(0.03, 0.03, 0.05, 0.92), Tema.cor("borda"), 2, 3, 0), Rect2(pos - Vector2(3, 3), tam + Vector2(6, 6)))
	var f := clampf(frac, 0.0, 1.0)
	if f > 0.0:
		_ctl.draw_rect(Rect2(pos, Vector2(tam.x * f, tam.y)), cor)
		_ctl.draw_rect(Rect2(pos, Vector2(tam.x * f, tam.y * 0.4)), Color(1, 1, 1, 0.14))

## Vida, estamina (recarga da esquiva) e mana (reservada, vazia e desativada).
func _desenhar_barras(fonte: Font) -> void:
	var m: float = _lay["margem"]
	var larg: float = _lay["barra_largura"]
	var y := m
	var hmax: float = jogador.stats.get("hp_max", 1.0)
	var hh: float = _lay["vida_altura"]
	_barra(Vector2(m, y), Vector2(larg, hh), jogador.hp / hmax, Tema.cor("vida"))
	_ctl.draw_string(fonte, Vector2(m + 8, y + hh - 5), Csv.t("hud.hp"), HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Tema.cor("texto"))
	_ctl.draw_string(fonte, Vector2(m, y + hh - 5), "%d/%d" % [ceili(jogador.hp), int(hmax)], HORIZONTAL_ALIGNMENT_RIGHT, larg - 8, 14, Tema.cor("texto"))
	y += hh + _lay["barra_espaco"] + 6.0
	var eh: float = _lay["estamina_altura"]
	var cdmax: float = jogador.stats.get("dodge_cooldown", 1.0)
	_barra(Vector2(m, y), Vector2(larg, eh), 1.0 - jogador.dodge_cd / cdmax, Tema.cor("estamina"))
	_ctl.draw_string(fonte, Vector2(m + larg + 10, y + eh), Csv.t("hud.stamina"), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Tema.cor("texto_suave"))
	y += eh + _lay["barra_espaco"] + 6.0
	var mh: float = _lay["mana_altura"]
	_barra(Vector2(m, y), Vector2(larg, mh), 0.0, Tema.cor("mana"))
	_ctl.draw_rect(Rect2(Vector2(m, y), Vector2(larg, mh)), Color(0, 0, 0, 0.45))
	_ctl.draw_string(fonte, Vector2(m + larg + 10, y + mh), Csv.t("hud.mana"), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Tema.cor("texto_suave"))

## Barra de habilidades: slots 0 e 1 = tiro e esquiva (lêem a recarga do jogador); o resto fica bloqueado.
func _desenhar_habilidades(fonte: Font, vp: Vector2) -> void:
	var lado: float = _lay["slot_tamanho"]
	var esp: float = _lay["slot_espaco"]
	var total := int(_lay["slot_total"])
	var largura := total * lado + (total - 1) * esp
	var x0 := (vp.x - largura) * 0.5
	var y0: float = vp.y - _lay["slot_base"] - lado
	var slots := [
		{"icone": "tiro", "tecla": "hud.key.shoot", "recarga": jogador.recarga_tiro() if jogador.has_method("recarga_tiro") else 0.0},
		{"icone": "esquiva", "tecla": "hud.key.dodge", "recarga": clampf(jogador.dodge_cd / jogador.stats.get("dodge_cooldown", 1.0), 0.0, 1.0)},
	]
	for i in total:
		var r := Rect2(x0 + i * (lado + esp), y0, lado, lado)
		var ativo := i < slots.size()
		_ctl.draw_style_box(Tema.caixa(Tema.cor("pedra") if ativo else Color(0.08, 0.08, 0.1, 0.9), Tema.cor("borda"), 3, 5, 0), r)
		if not ativo:
			_ctl.draw_texture_rect(Icones.textura("bloqueado"), r.grow(-lado * 0.22), false)
			continue
		var sl: Dictionary = slots[i]
		_ctl.draw_texture_rect(Icones.textura(sl["icone"]), r.grow(-lado * 0.16), false)
		var rec: float = sl["recarga"]
		if rec > 0.0:
			var h := (lado - 6.0) * rec
			_ctl.draw_rect(Rect2(r.position.x + 3, r.end.y - 3 - h, lado - 6.0, h), Color(0, 0, 0, 0.62))
		_ctl.draw_string(fonte, Vector2(r.position.x, r.end.y + 16), Csv.t(sl["tecla"]), HORIZONTAL_ALIGNMENT_CENTER, lado, 12, Tema.cor("texto_suave"))
