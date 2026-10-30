extends CanvasLayer
## Telas do fluxo da corrida: título, pausa (Esc), fim da corrida (derrota/vitória) e fade entre salas.
## Funciona com a árvore pausada. Textos por chave de localização; a corrida decide quando abrir cada tela.

const Csv = preload("res://scripts2d/csv2d.gd")

signal jogar          # começa uma corrida nova (título e fim)
signal retomar        # sai da pausa
signal ao_titulo      # volta ao título
signal pausa_pedida   # jogador apertou Esc durante a luta
signal sair

enum Tela { NENHUMA, TITULO, PAUSA, FIM }

var tela := Tela.NENHUMA
var _fundo: ColorRect
var _caixa: VBoxContainer
var _fade: ColorRect
var _tween: Tween

func _ready() -> void:
	layer = 20
	process_mode = Node.PROCESS_MODE_ALWAYS
	_fundo = ColorRect.new()
	_fundo.color = Color(0.03, 0.03, 0.05, 0.86)
	_fundo.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_fundo)
	var centro := CenterContainer.new()
	centro.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fundo.add_child(centro)
	var painel := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.11, 0.11, 0.14, 0.95)
	sb.set_border_width_all(3)
	sb.border_color = Color(0.32, 0.30, 0.36)
	sb.set_corner_radius_all(6)
	sb.set_content_margin_all(36)
	painel.add_theme_stylebox_override("panel", sb)
	centro.add_child(painel)
	_caixa = VBoxContainer.new()
	_caixa.add_theme_constant_override("separation", 14)
	_caixa.custom_minimum_size = Vector2(380, 0)
	painel.add_child(_caixa)
	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 0)
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_fade)
	_fundo.visible = false

func esta_aberta() -> bool:
	return tela != Tela.NENHUMA

func fechar() -> void:
	tela = Tela.NENHUMA
	_fundo.visible = false

func mostrar_titulo() -> void:
	_montar(Tela.TITULO, "menu.title", "menu.subtitle", [
		["menu.play", jogar], ["menu.quit", sair]])

func mostrar_pausa() -> void:
	_montar(Tela.PAUSA, "menu.paused", "", [
		["menu.resume", retomar], ["menu.restart", jogar], ["menu.to_title", ao_titulo]])

## `resumo` é um Array de linhas já formatadas (tempo, salas, upgrades).
func mostrar_fim(venceu: bool, resumo: Array) -> void:
	_montar(Tela.FIM, "menu.victory" if venceu else "menu.game_over", "", [
		["menu.play_again", jogar], ["menu.to_title", ao_titulo]], resumo)

func _montar(t: Tela, titulo: String, subtitulo: String, botoes: Array, linhas: Array = []) -> void:
	for c in _caixa.get_children():
		_caixa.remove_child(c)
		c.queue_free()
	_rotulo(Csv.t(titulo), 40)
	if subtitulo != "":
		_rotulo(Csv.t(subtitulo), 16, Color(1, 1, 1, 0.6))
	for l in linhas:
		_rotulo(l, 20)
	var primeiro: Button = null
	for b in botoes:
		var btn := Button.new()
		btn.text = Csv.t(b[0])
		btn.custom_minimum_size = Vector2(0, 46)
		btn.pressed.connect((b[1] as Signal).emit)
		_caixa.add_child(btn)
		if primeiro == null:
			primeiro = btn
	tela = t
	_fundo.visible = true
	if primeiro != null:
		primeiro.grab_focus.call_deferred()

func _rotulo(texto: String, tam: int, cor := Color.WHITE) -> void:
	var l := Label.new()
	l.text = texto
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", tam)
	l.modulate = cor
	_caixa.add_child(l)

## Escurece a tela, chama `no_escuro` e clareia. Usado entre salas.
func transicao(duracao: float, no_escuro: Callable) -> void:
	if _tween != null and _tween.is_valid():
		_tween.kill()
	_tween = create_tween()
	_tween.tween_property(_fade, "color:a", 1.0, duracao)
	_tween.tween_callback(no_escuro)
	_tween.tween_property(_fade, "color:a", 0.0, duracao)

func limpar_fade() -> void:
	if _tween != null and _tween.is_valid():
		_tween.kill()
	_fade.color.a = 0.0

func _input(ev: InputEvent) -> void:
	if not (ev is InputEventKey and ev.pressed and not ev.echo):
		return
	if tela == Tela.FIM and ev.physical_keycode == KEY_R:
		jogar.emit()
		get_viewport().set_input_as_handled()
		return
	if ev.keycode == KEY_ESCAPE:
		match tela:
			Tela.PAUSA:
				retomar.emit()
			Tela.NENHUMA:
				pausa_pedida.emit()
			_:
				return
		get_viewport().set_input_as_handled()
