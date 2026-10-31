extends CanvasLayer
## Prólogo do primeiro "Jogar": Ilsa e Tico recebem o Caçador no Refúgio (cena 1 do roteiro da Região 1, doc 21).
## Caixa de diálogo com retrato e nome sobre a arte de fundo; o texto aparece letra a letra.
## Clique, Espaço ou Enter: completa a fala ou passa à próxima. Esc: pula o prólogo.
## Falas em data2d/prologo.csv (ordem, quem, loc); nomes e textos em loc_2d.csv; retratos em art2d/ui/retrato_<quem>.png.

const Csv = preload("res://scripts2d/csv2d.gd")
const Tema = preload("res://scripts2d/tema_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")
const FUNDO := "res://art2d/ui/titulo_fundo.jpg"
const FONTE := "res://art2d/ui/DejaVuSerif-Bold.ttf"
const LETRAS_POR_SEG := 55.0

signal concluido

var falas: Array = []
var indice := -1
var ativo := false
var _letras := 0.0
var _fundo: TextureRect
var _caixa: PanelContainer
var _retrato_esq: TextureRect
var _retrato_dir: TextureRect
var _nome: Label
var _titulo: Label
var _texto: Label
var _dica: Label
var _retratos := {}

func _ready() -> void:
	layer = 30
	process_mode = Node.PROCESS_MODE_ALWAYS
	falas = Csv.rows("res://data2d/prologo.csv")
	var raiz := Control.new()
	raiz.theme = Tema.tema()
	raiz.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(raiz)
	var preto := ColorRect.new()
	preto.color = Color.BLACK
	preto.set_anchors_preset(Control.PRESET_FULL_RECT)
	raiz.add_child(preto)
	_fundo = TextureRect.new()
	_fundo.texture = load(FUNDO)
	_fundo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_fundo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_fundo.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fundo.modulate = Color(0.42, 0.42, 0.5)
	raiz.add_child(_fundo)
	var veu := ColorRect.new()   # escurece o pé da tela atrás da caixa de diálogo
	veu.set_anchors_preset(Control.PRESET_FULL_RECT)
	veu.material = _material_veu()
	raiz.add_child(veu)
	_retrato_esq = _criar_retrato(raiz, true)
	_retrato_dir = _criar_retrato(raiz, false)
	_caixa = PanelContainer.new()
	_caixa.add_theme_stylebox_override("panel", Tema.caixa(Color(Tema.cor("pedra"), 0.94), Tema.cor("borda_foco"), 2, 6, 26))
	_caixa.anchor_left = 0.16
	_caixa.anchor_right = 0.84
	_caixa.anchor_top = 0.72
	_caixa.anchor_bottom = 0.95
	raiz.add_child(_caixa)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 6)
	_caixa.add_child(col)
	var cabeca := HBoxContainer.new()
	cabeca.add_theme_constant_override("separation", 12)
	col.add_child(cabeca)
	_nome = _label(cabeca, 30, Tema.cor("destaque"))
	_nome.add_theme_font_override("font", load(FONTE))
	_titulo = _label(cabeca, 18, Tema.cor("texto_suave"))
	_titulo.size_flags_vertical = Control.SIZE_SHRINK_END
	_texto = _label(col, 24, Tema.cor("texto"))
	_texto.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_texto.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_dica = _label(col, 15, Tema.cor("texto_suave"))
	_dica.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_dica.text = Csv.t("prologue.hint")
	visible = false

func _material_veu() -> ShaderMaterial:
	var sh := Shader.new()
	sh.code = "shader_type canvas_item;\nvoid fragment(){ float t = smoothstep(0.35, 1.0, UV.y); COLOR = vec4(0.0, 0.0, 0.0, t * 0.85); }"
	var m := ShaderMaterial.new()
	m.shader = sh
	return m

## O recorte do retrato some num degradê na base, em vez de terminar numa linha reta.
func _material_retrato() -> ShaderMaterial:
	var sh := Shader.new()
	sh.code = "shader_type canvas_item;\nvoid fragment(){ vec4 c = texture(TEXTURE, UV); c.a *= 1.0 - smoothstep(0.72, 1.0, UV.y); COLOR = c * COLOR; }"
	var m := ShaderMaterial.new()
	m.shader = sh
	return m

func _criar_retrato(raiz: Control, esquerda: bool) -> TextureRect:
	var r := TextureRect.new()
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT
	r.anchor_top = 0.28
	r.anchor_bottom = 0.80
	r.anchor_left = 0.02 if esquerda else 0.70
	r.anchor_right = 0.30 if esquerda else 0.98
	r.flip_h = not esquerda
	r.material = _material_retrato()
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	raiz.add_child(r)
	return r

func _label(pai: Control, tam: int, cor: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", tam)
	l.add_theme_color_override("font_color", cor)
	pai.add_child(l)
	return l

func _retrato(quem: String) -> Texture2D:
	if not _retratos.has(quem):
		var caminho := "res://art2d/ui/retrato_%s.png" % quem
		_retratos[quem] = load(caminho) if ResourceLoader.exists(caminho) else null
	return _retratos[quem]

func iniciar() -> void:
	if falas.is_empty():
		concluido.emit()
		return
	ativo = true
	visible = true
	_ir(0)

func _ir(i: int) -> void:
	indice = i
	if i >= falas.size():
		_terminar()
		return
	var f: Dictionary = falas[i]
	var quem: String = f["quem"]
	var esquerda: bool = f.get("lado", "esq") != "dir"
	_nome.text = Csv.t("npc.%s.name" % quem)
	_titulo.text = Csv.t("npc.%s.title" % quem)
	_texto.text = Csv.t(f["loc"])
	_texto.visible_characters = 0
	_letras = 0.0
	var ativo_r := _retrato_esq if esquerda else _retrato_dir
	var outro_r := _retrato_dir if esquerda else _retrato_esq
	ativo_r.texture = _retrato(quem)
	ativo_r.modulate = Color.WHITE
	if outro_r.texture != null:
		outro_r.modulate = Color(0.45, 0.45, 0.5)   # quem não fala fica na sombra
	Audio.tocar("ui_click")

func _terminar() -> void:
	ativo = false
	visible = false
	_retrato_esq.texture = null
	_retrato_dir.texture = null
	concluido.emit()

## Completa a fala que está aparecendo ou passa para a próxima.
func avancar() -> void:
	if not ativo:
		return
	if _texto.visible_characters >= 0 and _texto.visible_characters < _texto.text.length():
		_texto.visible_characters = -1
	else:
		_ir(indice + 1)

func pular() -> void:
	if ativo:
		_terminar()

func _process(delta: float) -> void:
	if not ativo or _texto.visible_characters < 0:
		return
	_letras += delta * LETRAS_POR_SEG
	_texto.visible_characters = int(_letras)
	if _texto.visible_characters >= _texto.text.length():
		_texto.visible_characters = -1

func _input(ev: InputEvent) -> void:
	if not ativo:
		return
	var avanca := false
	if ev is InputEventMouseButton and ev.pressed and ev.button_index == MOUSE_BUTTON_LEFT:
		avanca = true
	elif ev is InputEventKey and ev.pressed and not ev.echo:
		if ev.keycode == KEY_ESCAPE:
			pular()
			get_viewport().set_input_as_handled()
			return
		avanca = ev.keycode in [KEY_SPACE, KEY_ENTER, KEY_KP_ENTER]
	if avanca:
		avancar()
		get_viewport().set_input_as_handled()
