extends CanvasLayer
## Tela de escolha entre cartas de upgrade (aparece ao limpar a sala). Pausa a árvore enquanto aberta.
## Clique na carta ou teclas 1, 2, 3. Textos por chave de localização.

const Csv = preload("res://scripts2d/csv2d.gd")

signal escolhido(id: String)

var upgrades: RefCounted
var aberta := false
var _ids: Array = []
var _caixa: HBoxContainer
var _fundo: ColorRect

func _ready() -> void:
	layer = 10
	process_mode = Node.PROCESS_MODE_ALWAYS
	_fundo = ColorRect.new()
	_fundo.color = Color(0.03, 0.03, 0.05, 0.8)
	_fundo.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_fundo)
	var col := VBoxContainer.new()
	col.set_anchors_preset(Control.PRESET_CENTER)
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.add_theme_constant_override("separation", 28)
	_fundo.add_child(col)
	var titulo := Label.new()
	titulo.text = Csv.t("upgrade.title")
	titulo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	titulo.add_theme_font_size_override("font_size", 34)
	col.add_child(titulo)
	_caixa = HBoxContainer.new()
	_caixa.add_theme_constant_override("separation", 24)
	col.add_child(_caixa)
	_fundo.visible = false

func abrir(ids: Array) -> void:
	_ids = ids
	for c in _caixa.get_children():
		c.queue_free()
	for i in ids.size():
		var id: String = ids[i]
		var b := Button.new()
		b.custom_minimum_size = Vector2(260, 190)
		b.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		var nv: int = upgrades.nivel(id) + 1
		b.text = "[%d]\n%s\n\n%s\n\n%s" % [i + 1, Csv.t("upgrade.%s.name" % id), Csv.t("upgrade.%s.desc" % id),
			Csv.t("upgrade.level") % [nv, upgrades.defs[id]["nivel_max"]]]
		b.pressed.connect(escolher.bind(i))
		_caixa.add_child(b)
	_fundo.visible = true
	aberta = true
	get_tree().paused = true

func escolher(i: int) -> void:
	if not aberta or i < 0 or i >= _ids.size():
		return
	aberta = false
	_fundo.visible = false
	get_tree().paused = false
	escolhido.emit(_ids[i])

func _input(ev: InputEvent) -> void:
	if aberta and ev is InputEventKey and ev.pressed and not ev.echo:
		var i: int = ev.keycode - KEY_1
		if i >= 0 and i < _ids.size():
			escolher(i)
			get_viewport().set_input_as_handled()
