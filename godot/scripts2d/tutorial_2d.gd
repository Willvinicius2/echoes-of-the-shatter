extends CanvasLayer
## Tutorial da primeira corrida: dicas de mover, atirar e esquivar, uma por vez, no rodapé da tela.
## Cada passo (data2d/tutorial.csv) termina quando o jogador usa a ação ou quando o tempo máximo passa.
## As teclas mostradas seguem o remapeamento. Não mexe na HUD: é uma camada própria, e só roda sem pausa.

const Csv = preload("res://scripts2d/csv2d.gd")
const Tema = preload("res://scripts2d/tema_2d.gd")

signal concluido

var opcoes: RefCounted   # opcoes_2d.gd; fornece os nomes das teclas
var passos: Array = []
var indice := -1
var ativo := false
var _tempo := 0.0
var _rotulo: Label

func _ready() -> void:
	layer = 15
	passos = Csv.rows("res://data2d/tutorial.csv")
	_rotulo = Label.new()
	_rotulo.theme = Tema.tema()
	_rotulo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_rotulo.add_theme_font_size_override("font_size", 22)
	_rotulo.add_theme_color_override("font_color", Tema.cor("destaque"))
	_rotulo.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	_rotulo.add_theme_constant_override("outline_size", 6)
	_rotulo.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_rotulo.anchor_top = 0.72
	_rotulo.anchor_bottom = 0.72
	_rotulo.offset_left = -400
	_rotulo.offset_right = 400
	_rotulo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_rotulo)
	_rotulo.visible = false

func iniciar() -> void:
	if passos.is_empty():
		return
	ativo = true
	_ir(0)

func parar() -> void:
	ativo = false
	_rotulo.visible = false

func _ir(i: int) -> void:
	indice = i
	_tempo = 0.0
	if i >= passos.size():
		parar()
		concluido.emit()
		return
	_rotulo.text = _texto(passos[i])
	_rotulo.visible = true

func _texto(p: Dictionary) -> String:
	var teclas := []
	for a in String(p["acoes"]).split("|"):
		var n := _nome(a)
		if n != "" and not teclas.has(n):
			teclas.append(n)
	return Csv.t(p["loc"]) % " ".join(teclas)

func _nome(acao: String) -> String:
	if opcoes != null and opcoes.acoes.has(acao):
		return opcoes.nome_tecla(acao)
	return Csv.t("tutorial.key_" + acao)   # mouse e controle: nome em loc

func _process(delta: float) -> void:
	if not ativo or indice < 0 or indice >= passos.size():
		return
	_tempo += delta
	var p: Dictionary = passos[indice]
	for a in String(p["acoes"]).split("|"):
		if Input.is_action_just_pressed(a):
			_ir(indice + 1)
			return
	if _tempo >= float(p["segundos_max"]):
		_ir(indice + 1)
