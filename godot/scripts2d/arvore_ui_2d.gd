extends CanvasLayer
## Árvore de habilidades da classe (tecla T). Uma coluna por ramo, nós ordenados por tier.
## Clique esquerdo aprende/sobe de nível; clique direito num nó ativo gira o slot em que ele fica; botão redistribui.
## Pausa a árvore de cena enquanto aberta. Textos por chave de localização.

const Csv = preload("res://scripts2d/csv2d.gd")
const Tema = preload("res://scripts2d/tema_2d.gd")
const Icones = preload("res://scripts2d/icones_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")

signal fechada

var habilidades: RefCounted
var aberta := false
var _fundo: ColorRect
var _colunas: HBoxContainer
var _titulo: Label
var _slots: HBoxContainer

func _ready() -> void:
	layer = 11
	process_mode = Node.PROCESS_MODE_ALWAYS
	_fundo = ColorRect.new()
	_fundo.color = Color(0.03, 0.03, 0.05, 0.9)
	_fundo.theme = Tema.tema()
	_fundo.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_fundo)
	var col := VBoxContainer.new()
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	col.add_theme_constant_override("separation", 14)
	_fundo.add_child(col)
	_titulo = Label.new()
	_titulo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_titulo.add_theme_font_size_override("font_size", 28)
	_titulo.add_theme_color_override("font_color", Tema.cor("destaque"))
	col.add_child(_titulo)
	_colunas = HBoxContainer.new()
	_colunas.alignment = BoxContainer.ALIGNMENT_CENTER
	_colunas.add_theme_constant_override("separation", 30)
	_colunas.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(_colunas)
	_slots = HBoxContainer.new()
	_slots.alignment = BoxContainer.ALIGNMENT_CENTER
	_slots.add_theme_constant_override("separation", 12)
	col.add_child(_slots)
	_fundo.visible = false

## Liga a árvore a um runtime de habilidades (ou a nenhum, para classes com sistema próprio).
func definir(h: RefCounted) -> void:
	if habilidades != null and habilidades.mudou.is_connected(_montar):
		habilidades.mudou.disconnect(_montar)
	habilidades = h
	if habilidades != null:
		habilidades.mudou.connect(_montar)

func abrir() -> void:
	if aberta or habilidades == null:
		return
	aberta = true
	_fundo.visible = true
	get_tree().paused = true
	_montar()

func fechar() -> void:
	if not aberta:
		return
	aberta = false
	_fundo.visible = false
	get_tree().paused = false
	fechada.emit()

func _unhandled_input(ev: InputEvent) -> void:
	if ev.is_action_pressed("skill_tree"):
		if aberta:
			fechar()
		elif not get_tree().paused:
			abrir()
		get_viewport().set_input_as_handled()
	elif aberta and ev.is_action_pressed("ui_cancel"):
		fechar()
		get_viewport().set_input_as_handled()

func _montar() -> void:
	if not aberta:
		return
	_titulo.text = "%s  —  %s: %d" % [Csv.t("class." + habilidades.classe), Csv.t("tree.points"), habilidades.pontos]
	for c in _colunas.get_children():
		c.queue_free()
	for c in _slots.get_children():
		c.queue_free()
	if habilidades.ordem.is_empty():
		var vazio := Label.new()
		vazio.text = Csv.t("tree.empty")
		_colunas.add_child(vazio)
	for ramo in habilidades.ramos():
		var v := VBoxContainer.new()
		v.add_theme_constant_override("separation", 6)
		var nome := Label.new()
		nome.text = Csv.t("ramo." + ramo)
		nome.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		nome.add_theme_color_override("font_color", Tema.cor("destaque"))
		v.add_child(nome)
		var ids: Array = habilidades.ids_do_ramo(ramo)
		ids.sort_custom(func(a, b): return habilidades.defs[a]["tier"] < habilidades.defs[b]["tier"])
		for id in ids:
			v.add_child(_botao_no(id))
		_colunas.add_child(v)
	for i in habilidades.SLOTS:
		var b := Label.new()
		var id: String = habilidades.slots[i]
		b.text = "[%d] %s" % [i + 1, Csv.t("skill.%s.name" % id) if id != "" else Csv.t("tree.slot_empty")]
		_slots.add_child(b)
	var r := Button.new()
	r.text = Csv.t("tree.respec")
	r.pressed.connect(habilidades.redistribuir)
	_slots.add_child(r)
	var f := Button.new()
	f.text = Csv.t("tree.close")
	f.pressed.connect(fechar)
	_slots.add_child(f)

func _botao_no(id: String) -> Button:
	var d: Dictionary = habilidades.defs[id]
	var b := Button.new()
	b.custom_minimum_size = Vector2(230, 40)
	b.text = "%s  %d/%d" % [Csv.t("skill.%s.name" % id), habilidades.nivel(id), int(d["nivel_max"])]
	b.tooltip_text = Csv.t("skill.%s.desc" % id)
	b.disabled = habilidades.nivel(id) == 0 and not habilidades.pode_aprender(id)
	b.gui_input.connect(func(ev: InputEvent) -> void:
		if ev is InputEventMouseButton and ev.pressed:
			if ev.button_index == MOUSE_BUTTON_LEFT and habilidades.aprender(id):
				Audio.tocar("card_pick")
			elif ev.button_index == MOUSE_BUTTON_RIGHT and habilidades.eh_ativa(id) and habilidades.nivel(id) > 0:
				habilidades.equipar((maxi(0, habilidades.slots.find(id)) + 1) % habilidades.SLOTS if habilidades.slots.has(id) else 0, id))
	return b
