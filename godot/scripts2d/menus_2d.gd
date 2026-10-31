extends CanvasLayer
## Telas do fluxo da corrida: título, pausa (Esc), fim da corrida (derrota/vitória) e fade entre salas.
## Funciona com a árvore pausada. Textos por chave de localização; a corrida decide quando abrir cada tela.

const Csv = preload("res://scripts2d/csv2d.gd")
const Classe = preload("res://scripts2d/classe_2d.gd")
const Tema = preload("res://scripts2d/tema_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")
const OpcoesScript = preload("res://scripts2d/opcoes_2d.gd")
const SteamScript = preload("res://scripts2d/steam_2d.gd")
const TutorialScript = preload("res://scripts2d/tutorial_2d.gd")

signal jogar          # começa uma corrida nova (título e fim)
signal retomar        # sai da pausa
signal ao_titulo      # volta ao título
signal pausa_pedida   # jogador apertou Esc durante a luta
signal sair

enum Tela { NENHUMA, TITULO, PAUSA, FIM, META, FORJA, ROTA, OPCOES, TECLAS }

var tela := Tela.NENHUMA
var meta: RefCounted   # meta_2d.gd; a loja de melhorias do título
var opcoes: RefCounted   # opcoes_2d.gd; volume, vídeo e teclas (carregadas do disco no _ready)
var steam: RefCounted    # steam_2d.gd; conquistas, sem efeito quando a Steam não está disponível
var tutorial: CanvasLayer   # tutorial_2d.gd; dicas da primeira corrida
var _voltar_opcoes := Callable()   # tela que abriu as opções (título ou pausa)
var _esperando := ""   # ação aguardando a próxima tecla (remapeamento)
var _fundo: ColorRect
var _caixa: VBoxContainer
var _fade: ColorRect
var _tween: Tween

func _ready() -> void:
	layer = 20
	process_mode = Node.PROCESS_MODE_ALWAYS
	_fundo = ColorRect.new()
	_fundo.color = Color(0.03, 0.03, 0.05, 0.86)
	_fundo.theme = Tema.tema()
	_fundo.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_fundo)
	var centro := CenterContainer.new()
	centro.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fundo.add_child(centro)
	var painel := PanelContainer.new()
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
	opcoes = OpcoesScript.new()
	opcoes.carregar()
	steam = SteamScript.new()
	steam.iniciar()
	tutorial = TutorialScript.new()
	tutorial.opcoes = opcoes
	tutorial.concluido.connect(_tutorial_concluido)
	add_child(tutorial)
	jogar.connect(_ao_jogar)
	ao_titulo.connect(tutorial.parar)

func _process(_delta: float) -> void:
	steam.tick()

func _ao_jogar() -> void:
	if not opcoes.tutorial_visto:
		tutorial.iniciar()

func _tutorial_concluido() -> void:
	opcoes.tutorial_visto = true
	opcoes.salvar()

func esta_aberta() -> bool:
	return tela != Tela.NENHUMA

func fechar() -> void:
	tela = Tela.NENHUMA
	_fundo.visible = false

## Título e hub entre corridas: saldo, amuleto equipado e as estações (Forja, Melhorias).
func mostrar_titulo() -> void:
	var linhas := []
	if meta != null:
		linhas = _resumo_hub()
	_montar(Tela.TITULO, "menu.title", "menu.subtitle", [
		["menu.play", jogar], [Csv.t("menu.class") % Csv.t("class.%s.name" % Classe.atual), func() -> void:
			Classe.alternar()
			mostrar_titulo()], ["menu.forge", mostrar_forja], ["menu.meta", mostrar_meta],
		["menu.options", func() -> void: mostrar_opcoes(mostrar_titulo)], ["menu.quit", sair]], linhas)

func _resumo_hub() -> Array:
	var linhas := [Csv.t("menu.meta_balance") % meta.fragmentos]
	var mats := []
	for m in meta.materiais:
		if int(meta.materiais[m]) > 0:
			mats.append("%s x%d" % [Csv.t("material." + m), meta.materiais[m]])
	if not mats.is_empty():
		linhas.append(", ".join(mats))
	if meta.equipado != "":
		linhas.append(Csv.t("menu.forge_equipped") % Csv.t("recipe.%s.name" % meta.equipado))
	return linhas

func _custo_txt(r: Dictionary) -> String:
	var partes := []
	for m in r["custo"]:
		partes.append("%d %s" % [r["custo"][m], Csv.t("material." + m)])
	partes.append(Csv.t("menu.forge_fragments") % r["fragmentos"])
	return ", ".join(partes)

## Forja: criar amuletos e consumíveis com materiais; amuleto criado vira botão de equipar.
func mostrar_forja() -> void:
	var botoes := []
	for id in meta.ordem_receitas:
		var r: Dictionary = meta.receitas[id]
		var nome := Csv.t("recipe.%s.name" % id)
		var txt: String
		if r["tipo"] == "amuleto" and meta.amuletos.has(id):
			txt = Csv.t("menu.forge_unequip" if meta.equipado == id else "menu.forge_equip") % nome
			botoes.append([txt, func() -> void:
				meta.equipar(id)
				mostrar_forja()])
			continue
		if r["tipo"] == "consumivel":
			txt = Csv.t("menu.forge_craft_stock") % [nome, meta.estoque.get(id, 0), r["estoque_max"], _custo_txt(r)]
		else:
			txt = Csv.t("menu.forge_craft") % [nome, _custo_txt(r)]
		botoes.append([txt, func() -> void:
			if meta.criar(id) and r["tipo"] == "amuleto":
				steam.evento("amuleto_criado")
			mostrar_forja(), not meta.pode_criar(id)])
	botoes.append(["menu.back", mostrar_titulo])
	_montar(Tela.FORJA, "menu.forge_title", "menu.forge_hint", botoes, _resumo_hub().slice(0, 2))

## Bifurcação da cripta: `opcoes` é um Array de [texto, Callable]; sem Esc, o jogador precisa escolher.
func mostrar_rota(opcoes: Array) -> void:
	_montar(Tela.ROTA, "menu.route_title", "menu.route_hint", opcoes)

func mostrar_pausa() -> void:
	_montar(Tela.PAUSA, "menu.paused", "", [
		["menu.resume", retomar], ["menu.restart", jogar],
		["menu.options", func() -> void: mostrar_opcoes(mostrar_pausa)], ["menu.to_title", ao_titulo]])

## `resumo` é um Array de linhas já formatadas (tempo, salas, upgrades).
func mostrar_fim(venceu: bool, resumo: Array) -> void:
	steam.evento("corrida_fim")
	if venceu:
		steam.evento("vitoria")
	_montar(Tela.FIM, "menu.victory" if venceu else "menu.game_over", "", [
		["menu.play_again", jogar], ["menu.to_title", ao_titulo]], resumo)

## Loja de melhorias permanentes: cada botão compra um nível; o saldo vem do save.
func mostrar_meta() -> void:
	var botoes := []
	for id in meta.ordem:
		var d: Dictionary = meta.defs[id]
		var nome := Csv.t("meta.%s.name" % id)
		var txt: String
		if meta.nivel(id) >= d["nivel_max"]:
			txt = Csv.t("menu.meta_item_owned" if d["tipo"] == "habilidade" else "menu.meta_item_max") % nome
		else:
			txt = Csv.t("menu.meta_item") % [nome, meta.nivel(id), d["custo"]]
		botoes.append([txt, func() -> void:
			if meta.comprar(id):
				steam.evento("melhoria_comprada")
			mostrar_meta(), not meta.pode_comprar(id)])
	botoes.append(["menu.back", mostrar_titulo])
	_montar(Tela.META, "menu.meta_title", "", botoes, [Csv.t("menu.meta_balance") % meta.fragmentos])

## Opções: volumes, vídeo, teclas e tutorial. `voltar` reabre a tela que chamou (título ou pausa).
func mostrar_opcoes(voltar: Callable = Callable()) -> void:
	if voltar.is_valid():
		_voltar_opcoes = voltar
	var botoes := []
	for tipo in ["master", "musica", "efeitos"]:
		botoes.append([Csv.t("opt.vol_" + tipo) % int(round(opcoes.vol[tipo] * 100.0)), func() -> void:
			opcoes.ciclar_volume(tipo)
			opcoes.salvar()
			mostrar_opcoes()])
	botoes.append([Csv.t("opt.fullscreen") % Csv.t("opt.on" if opcoes.tela_cheia else "opt.off"), func() -> void:
		opcoes.set_tela_cheia(not opcoes.tela_cheia)
		opcoes.salvar()
		mostrar_opcoes()])
	botoes.append([Csv.t("opt.vsync") % Csv.t("opt.on" if opcoes.vsync else "opt.off"), func() -> void:
		opcoes.set_vsync(not opcoes.vsync)
		opcoes.salvar()
		mostrar_opcoes()])
	botoes.append(["opt.keys", mostrar_teclas])
	botoes.append([Csv.t("opt.tutorial") % Csv.t("opt.off" if opcoes.tutorial_visto else "opt.on"), func() -> void:
		opcoes.tutorial_visto = not opcoes.tutorial_visto
		opcoes.salvar()
		mostrar_opcoes()])
	botoes.append(["menu.back", _fechar_opcoes])
	_montar(Tela.OPCOES, "opt.title", "", botoes)

func _fechar_opcoes() -> void:
	opcoes.salvar()
	if _voltar_opcoes.is_valid():
		_voltar_opcoes.call()
	else:
		mostrar_titulo()

## Remapeamento: clicar numa ação espera a próxima tecla (Esc cancela). Teclas repetidas trocam de lugar.
func mostrar_teclas() -> void:
	var botoes := []
	for a in opcoes.acoes:
		var nome := Csv.t("keys." + a)
		var valor: String = Csv.t("opt.press_key") if _esperando == a else opcoes.nome_tecla(a)
		botoes.append([Csv.t("opt.key_item") % [nome, valor], func() -> void:
			_esperando = a
			mostrar_teclas()])
	botoes.append(["opt.keys_reset", func() -> void:
		_esperando = ""
		opcoes.restaurar_teclas()
		opcoes.salvar()
		mostrar_teclas()])
	botoes.append(["menu.back", func() -> void:
		_esperando = ""
		mostrar_opcoes()])
	_montar(Tela.TECLAS, "opt.keys_title", "opt.keys_hint", botoes)

func _montar(t: Tela, titulo: String, subtitulo: String, botoes: Array, linhas: Array = []) -> void:
	for c in _caixa.get_children():
		_caixa.remove_child(c)
		c.queue_free()
	_rotulo(Csv.t(titulo), 40, Tema.cor("destaque"))
	if subtitulo != "":
		_rotulo(Csv.t(subtitulo), 16, Tema.cor("texto_suave"))
	for l in linhas:
		_rotulo(l, 20)
	var primeiro: Button = null
	for b in botoes:
		var btn := Button.new()
		btn.text = Csv.t(b[0])   # texto já formatado (loja) volta como veio: chave ausente devolve a própria string
		btn.custom_minimum_size = Vector2(0, 46)
		btn.disabled = b.size() > 2 and b[2]
		btn.pressed.connect(func() -> void:
			Audio.tocar("ui_click")
			if b[1] is Signal:
				(b[1] as Signal).emit()
			else:
				(b[1] as Callable).call())
		_caixa.add_child(btn)
		if primeiro == null and not btn.disabled:
			primeiro = btn
	tela = t
	_fundo.visible = true
	if primeiro != null:
		primeiro.grab_focus.call_deferred()

func _rotulo(texto: String, tam: int, cor := Color(0.9, 0.88, 0.84)) -> void:
	var l := Label.new()
	l.text = texto
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", tam)
	l.add_theme_color_override("font_color", cor)
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
	if _esperando != "" and tela == Tela.TECLAS:
		var acao := _esperando
		_esperando = ""
		if ev.keycode != KEY_ESCAPE:
			opcoes.remapear(acao, ev.physical_keycode)
			opcoes.salvar()
		mostrar_teclas()
		get_viewport().set_input_as_handled()
		return
	if tela == Tela.FIM and ev.physical_keycode == KEY_R:
		jogar.emit()
		get_viewport().set_input_as_handled()
		return
	if ev.keycode == KEY_ESCAPE:
		match tela:
			Tela.PAUSA:
				retomar.emit()
			Tela.META, Tela.FORJA:
				mostrar_titulo()
			Tela.OPCOES:
				_fechar_opcoes()
			Tela.TECLAS:
				mostrar_opcoes()
			Tela.NENHUMA:
				pausa_pedida.emit()
			_:
				return
		get_viewport().set_input_as_handled()
