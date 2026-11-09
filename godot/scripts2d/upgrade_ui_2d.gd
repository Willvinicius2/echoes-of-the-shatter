extends CanvasLayer
## Tela de escolha entre cartas de upgrade (aparece ao limpar a sala). Pausa a árvore enquanto aberta.
## Clique na carta ou teclas 1, 2, 3. Textos por chave de localização.

const Csv = preload("res://scripts2d/csv2d.gd")
const Tema = preload("res://scripts2d/tema_2d.gd")
const Icones = preload("res://scripts2d/icones_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")

signal escolhido(id: String)

var upgrades: RefCounted
var aberta := false
var modo := "sala"        # "sala" (sala limpa), "level" (subiu de nível), "chest" (baú de elite) ou "gem" (gema de habilidade)
var _fonte: RefCounted    # de onde vêm `defs` e `nivel(id)` das cartas abertas (upgrades ou a árvore de habilidades)
var _titulo: Label
var _ids: Array = []
var _caixa: HBoxContainer
var _fundo: ColorRect

func _ready() -> void:
	layer = 10
	process_mode = Node.PROCESS_MODE_ALWAYS
	_fundo = ColorRect.new()
	_fundo.color = Color(0.03, 0.03, 0.05, 0.8)
	_fundo.theme = Tema.tema()
	_fundo.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_fundo)
	var centro := CenterContainer.new()
	centro.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fundo.add_child(centro)
	var col := VBoxContainer.new()
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.add_theme_constant_override("separation", 28)
	centro.add_child(col)
	var titulo := Label.new()
	_titulo = titulo
	titulo.text = Csv.t("upgrade.title")
	titulo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	titulo.add_theme_font_size_override("font_size", 34)
	titulo.add_theme_color_override("font_color", Tema.cor("destaque"))
	col.add_child(titulo)
	_caixa = HBoxContainer.new()
	_caixa.add_theme_constant_override("separation", 24)
	col.add_child(_caixa)
	_fundo.visible = false

## `m`: "sala", "level", "chest" ou "gem"; `nivel` aparece no título da carta de nível. `fonte` (opcional) é de onde
## vêm as definições e o nível das cartas: a árvore de habilidades no modo "gem", senão `upgrades`.
func abrir(ids: Array, m := "sala", nivel := 0, fonte: RefCounted = null) -> void:
	_ids = ids
	modo = m
	_fonte = fonte if fonte != null else upgrades
	if _titulo != null:
		match m:
			"level":
				_titulo.text = Csv.t("upgrade.level_up") % nivel
			"chest":
				_titulo.text = Csv.t("upgrade.chest")
			"gem":
				_titulo.text = Csv.t("upgrade.gem")
			"afinidade":
				_titulo.text = Csv.t("upgrade.afinidade")
			_:
				_titulo.text = Csv.t("upgrade.title")
	for c in _caixa.get_children():
		c.queue_free()
	for i in ids.size():
		var id: String = ids[i]
		var b := Button.new()
		b.custom_minimum_size = Vector2(260, 260)
		b.icon = Icones.textura(id)
		b.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
		b.vertical_icon_alignment = VERTICAL_ALIGNMENT_TOP
		b.expand_icon = true
		b.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		var nv: int = _fonte.nivel(id) + 1
		var pre := "skill" if _fonte.defs[id].has("ramo") else "upgrade"  # habilidades (árvore) têm ramo
		b.text = "[%d]\n%s\n\n%s\n\n%s" % [i + 1, Csv.t("%s.%s.name" % [pre, id]), Csv.t("%s.%s.desc" % [pre, id]),
			Csv.t("upgrade.level") % [nv, _fonte.defs[id]["nivel_max"]]]
		b.pressed.connect(escolher.bind(i))
		_caixa.add_child(b)
	_fundo.visible = true
	aberta = true
	Audio.tocar("card_open")
	get_tree().paused = true

func escolher(i: int) -> void:
	if not aberta or i < 0 or i >= _ids.size():
		return
	aberta = false
	_fundo.visible = false
	Audio.tocar("card_pick")
	get_tree().paused = false
	escolhido.emit(_ids[i])

func _input(ev: InputEvent) -> void:
	if aberta and ev is InputEventKey and ev.pressed and not ev.echo:
		var i: int = ev.keycode - KEY_1
		if i >= 0 and i < _ids.size():
			escolher(i)
			get_viewport().set_input_as_handled()
