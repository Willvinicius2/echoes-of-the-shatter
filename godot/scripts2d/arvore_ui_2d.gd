extends CanvasLayer
## Árvore da classe (tecla T), com duas abas:
## - Habilidades (doc 29): uma coluna por ramo, nós por tier. Clique esquerdo aprende/sobe de nível; clique direito num
##   nó ativo gira o slot em que ele fica; botão redistribui.
## - Passivos (doc 33): grafo de nós (passivos_2d.gd) desenhado nas posições x,y do CSV, com linhas entre vizinhos.
##   Clique ativa o nó; a dica mostra custo, efeito e a pré-visualização "antes → depois" nas habilidades aprendidas.
##   Arrastar com o mouse (ou as setas) move o mapa.
## Pausa a árvore de cena enquanto aberta. Textos por chave de localização; nenhum número de balanceamento aqui.

const Csv = preload("res://scripts2d/csv2d.gd")
const Tema = preload("res://scripts2d/tema_2d.gd")
const Icones = preload("res://scripts2d/icones_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")

const TAM_NO := {"raiz": 44.0, "pequeno": 30.0, "notavel": 40.0, "transforma": 44.0, "keystone": 52.0}   # px (só layout)
const ESCALA_MAPA := 1.45   # px de tela por unidade x,y do CSV (só layout)

signal fechada

var habilidades: RefCounted
var aberta := false
var aba := "skills"   # "skills" | "passives"
var _fundo: ColorRect
var _colunas: HBoxContainer
var _titulo: Label
var _slots: HBoxContainer
var _abas: HBoxContainer
var _mapa: Control
var _mapa_desloc := Vector2.ZERO
var _arrastando := false
var _nos_ui := {}   # id -> Button

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
	col.add_theme_constant_override("separation", 10)
	_fundo.add_child(col)
	_titulo = Label.new()
	_titulo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_titulo.add_theme_font_size_override("font_size", 28)
	_titulo.add_theme_color_override("font_color", Tema.cor("destaque"))
	col.add_child(_titulo)
	_abas = HBoxContainer.new()
	_abas.alignment = BoxContainer.ALIGNMENT_CENTER
	_abas.add_theme_constant_override("separation", 12)
	col.add_child(_abas)
	_colunas = HBoxContainer.new()
	_colunas.alignment = BoxContainer.ALIGNMENT_CENTER
	_colunas.add_theme_constant_override("separation", 30)
	_colunas.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(_colunas)
	_mapa = Control.new()
	_mapa.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_mapa.clip_contents = true
	_mapa.mouse_filter = Control.MOUSE_FILTER_STOP
	_mapa.draw.connect(_desenhar_mapa)
	_mapa.gui_input.connect(_input_mapa)
	col.add_child(_mapa)
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

func mostrar_aba(nome: String) -> void:
	aba = nome
	_montar()

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
	elif aberta and aba == "passives" and ev is InputEventKey and ev.pressed:
		var passo := Vector2.ZERO
		if ev.is_action("ui_left"):
			passo.x = 60
		elif ev.is_action("ui_right"):
			passo.x = -60
		elif ev.is_action("ui_up"):
			passo.y = 60
		elif ev.is_action("ui_down"):
			passo.y = -60
		if passo != Vector2.ZERO:
			_mapa_desloc += passo
			_posicionar_nos()
			get_viewport().set_input_as_handled()

func _montar() -> void:
	if not aberta:
		return
	for c in _colunas.get_children():
		c.queue_free()
	for c in _slots.get_children():
		c.queue_free()
	for c in _abas.get_children():
		c.queue_free()
	for c in _mapa.get_children():
		c.queue_free()
	_nos_ui.clear()
	var passivos: RefCounted = habilidades.passivos
	var tem_passivos: bool = passivos != null and not passivos.defs.is_empty()
	if tem_passivos:
		for nome in ["skills", "passives"]:
			var b := Button.new()
			b.text = Csv.t("tree.tab_skills" if nome == "skills" else "tree.tab_passives")
			b.disabled = aba == nome
			b.pressed.connect(mostrar_aba.bind(nome))
			_abas.add_child(b)
	if aba == "passives" and not tem_passivos:
		aba = "skills"
	_colunas.visible = aba == "skills"
	_mapa.visible = aba == "passives"
	if aba == "skills":
		_titulo.text = "%s  —  %s: %d" % [Csv.t("class." + habilidades.classe), Csv.t("tree.points"), habilidades.pontos]
		_montar_habilidades()
	else:
		_titulo.text = "%s  —  %s: %d" % [Csv.t("class." + habilidades.classe), Csv.t("tree.passive_points"), passivos.pontos]
		_montar_passivos()
	var r := Button.new()
	r.text = Csv.t("tree.respec")
	r.pressed.connect(func() -> void:
		if aba == "skills":
			habilidades.redistribuir()
		else:
			habilidades.passivos.redistribuir())
	_slots.add_child(r)
	var f := Button.new()
	f.text = Csv.t("tree.close")
	f.pressed.connect(fechar)
	_slots.add_child(f)

# ---- aba Habilidades (doc 29) ----------------------------------------------------------------------------------------

func _montar_habilidades() -> void:
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

# ---- aba Passivos (doc 33) -------------------------------------------------------------------------------------------

func _montar_passivos() -> void:
	var p: RefCounted = habilidades.passivos
	for id in p.ordem:
		var d: Dictionary = p.defs[id]
		var b := Button.new()
		var tam: float = TAM_NO.get(d["tipo"], 30.0)
		b.custom_minimum_size = Vector2(tam, tam)
		b.text = ""
		b.tooltip_text = _dica_passivo(id)
		b.disabled = not p.ativo(id) and not p.pode_ativar(id)
		b.modulate = _cor_no(id)
		b.pressed.connect(func() -> void:
			if p.ativar(id):
				Audio.tocar("card_pick"))
		_mapa.add_child(b)
		_nos_ui[id] = b
		var rotulo := Label.new()
		rotulo.text = Csv.t("passivo.%s.name" % id)
		rotulo.add_theme_font_size_override("font_size", 11)
		rotulo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		rotulo.mouse_filter = Control.MOUSE_FILTER_IGNORE
		rotulo.add_theme_color_override("font_color", Tema.cor("texto") if p.ativo(id) or p.pode_ativar(id) else Tema.cor("texto_suave"))
		rotulo.name = "Rotulo_" + id
		_mapa.add_child(rotulo)
	_posicionar_nos()

func _pos_no(id: String) -> Vector2:
	var d: Dictionary = habilidades.passivos.defs[id]
	return _mapa.size * 0.5 + _mapa_desloc + Vector2(d["x"], d["y"]) * ESCALA_MAPA

func _posicionar_nos() -> void:
	for id in _nos_ui:
		var b: Button = _nos_ui[id]
		var c := _pos_no(id)
		b.position = c - b.custom_minimum_size * 0.5
		var r: Label = _mapa.get_node_or_null("Rotulo_" + id)
		if r != null:
			r.position = c + Vector2(-70, b.custom_minimum_size.y * 0.5 + 2)
			r.size = Vector2(140, 14)
	_mapa.queue_redraw()

func _cor_no(id: String) -> Color:
	var p: RefCounted = habilidades.passivos
	var d: Dictionary = p.defs[id]
	var base := Tema.cor("destaque") if d["tipo"] in ["keystone", "transforma"] else Tema.cor("texto")
	if d["tipo"] == "notavel":
		base = Tema.cor("borda_foco")
	if p.ativo(id):
		return base
	if p.pode_ativar(id):
		return base.darkened(0.25)
	return Tema.cor("texto_suave").darkened(0.35)

func _desenhar_mapa() -> void:
	var p: RefCounted = habilidades.passivos
	if p == null:
		return
	for id in p.ordem:
		for v in p.defs[id]["vizinhos"]:
			if not p.defs.has(v):
				continue
			var ligado: bool = p.ativo(id) and p.ativo(v)
			var cor := Tema.cor("destaque") if ligado else Tema.cor("borda")
			_mapa.draw_line(_pos_no(id), _pos_no(v), cor, 3.0 if ligado else 1.5)

func _input_mapa(ev: InputEvent) -> void:
	if ev is InputEventMouseButton and ev.button_index == MOUSE_BUTTON_LEFT:
		_arrastando = ev.pressed
	elif ev is InputEventMouseMotion and _arrastando and (ev.button_mask & MOUSE_BUTTON_MASK_LEFT) != 0:
		_mapa_desloc += ev.relative
		_posicionar_nos()

## Dica do nó: nome, tipo, custo, descrição e a pré-visualização nas habilidades aprendidas.
func _dica_passivo(id: String) -> String:
	var p: RefCounted = habilidades.passivos
	var d: Dictionary = p.defs[id]
	var linhas := [Csv.t("passivo.%s.name" % id), Csv.t("passivo.%s.desc" % id)]
	if d["tipo"] == "keystone":
		linhas.append(Csv.t("tree.passive_keystone"))
	elif d["tipo"] == "transforma":
		linhas.append(Csv.t("tree.passive_transform"))
	if d["tipo"] != "raiz":
		linhas.append(Csv.t("tree.passive_cost") % int(d["custo"]))
	if p.ativo(id):
		linhas.append(Csv.t("tree.passive_active"))
	elif not p.pode_ativar(id):
		linhas.append(Csv.t("tree.passive_locked"))
	else:
		var defs_hab := {}
		var tags_hab := {}
		for hid in habilidades.niveis:
			if habilidades.eh_ativa(hid) or habilidades.defs[hid]["tipo"] == "passiva":
				defs_hab[hid] = habilidades.def_base(hid)
				tags_hab[hid] = habilidades.tags_de(hid)
		var stats: Dictionary = {}
		var jogadores := get_tree().get_nodes_in_group("arqueiro")
		if not jogadores.is_empty() and "stats" in jogadores[0]:
			stats = jogadores[0].stats
		var previa: Array = p.previa(id, defs_hab, tags_hab, stats)
		if not previa.is_empty():
			linhas.append(Csv.t("tree.passive_preview"))
			for m in previa:
				var quem: String = Csv.t("skill.%s.name" % m["skill"]) if m["skill"] != "" else Csv.t("tree.passive_stats")
				linhas.append("  %s · %s: %s → %s" % [quem, m["campo"], _fmt(m["antes"]), _fmt(m["depois"])])
	return "\n".join(linhas)

static func _fmt(v) -> String:
	if typeof(v) == TYPE_FLOAT:
		return str(snappedf(v, 0.01))
	return str(v)
