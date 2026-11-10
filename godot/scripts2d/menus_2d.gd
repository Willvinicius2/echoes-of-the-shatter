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
const PrologoScript = preload("res://scripts2d/prologo_2d.gd")
const SpriteLoader = preload("res://scripts2d/sprite_loader.gd")
const Fase = preload("res://scripts2d/fase_2d.gd")
const Arte = preload("res://scripts2d/hud_arte_2d.gd")
const FUNDO_TITULO := "res://art2d/ui/titulo_fundo.png"   # cena do próprio jogo em pixel art (tools/captura_titulo_2d.gd), 320 x 180 mostrada em 4x
const FONTE_TITULO := "res://art2d/ui/DejaVuSerif-Bold.ttf"

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
var prologo: CanvasLayer    # prologo_2d.gd; Ilsa e Tico no primeiro Jogar
var _voltar_opcoes := Callable()   # tela que abriu as opções (título ou pausa)
var _esperando := ""   # ação aguardando a próxima tecla (remapeamento)
var _fundo: ColorRect
var _arte: TextureRect          # key art atrás do título e das telas do hub
var _no_hub := false            # telas abertas a partir do título (Forja, Melhorias, Opções)
var _retrato_classe: TextureRect   # idle da classe escolhida, animado no cartão do título
var _retrato_t := 0.0
var _caixa: VBoxContainer
var _painel: PanelContainer
var _centro: CenterContainer
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
	_arte = TextureRect.new()
	_arte.texture = load(FUNDO_TITULO)
	_arte.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_arte.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_arte.set_anchors_preset(Control.PRESET_FULL_RECT)
	_arte.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_arte.modulate = Color(0.82, 0.82, 0.9)
	_arte.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fundo.add_child(_arte)
	_centro = CenterContainer.new()
	_centro.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fundo.add_child(_centro)
	_painel = PanelContainer.new()
	_painel.add_theme_stylebox_override("panel", Tema.caixa(Color(Tema.cor("pedra"), 0.94), Tema.cor("borda"), 3, 6, 24))
	_centro.add_child(_painel)
	_caixa = VBoxContainer.new()
	_caixa.add_theme_constant_override("separation", 14)
	_caixa.custom_minimum_size = Vector2(380, 0)
	_painel.add_child(_caixa)
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
	prologo = PrologoScript.new()
	prologo.concluido.connect(_prologo_concluido)
	add_child(prologo)
	jogar.connect(_ao_jogar)
	ao_titulo.connect(tutorial.parar)

func _process(delta: float) -> void:
	steam.tick()
	if _retrato_classe != null and is_instance_valid(_retrato_classe) and _retrato_classe.is_visible_in_tree():
		_retrato_t += delta
		var sf: SpriteFrames = SpriteLoader.frames_for(Classe.atual)
		if sf.has_animation("idle_1"):
			var n := sf.get_frame_count("idle_1")
			_retrato_classe.texture = sf.get_frame_texture("idle_1", int(_retrato_t * sf.get_animation_speed("idle_1")) % n)

## Jogar no título: na primeira vez passa pelo prólogo antes de começar a corrida.
func _jogar_do_titulo() -> void:
	if opcoes.prologo_visto:
		jogar.emit()
	else:
		prologo.iniciar()

func _prologo_concluido() -> void:
	var primeira: bool = not opcoes.prologo_visto
	opcoes.prologo_visto = true
	opcoes.salvar()
	if primeira:
		jogar.emit()

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
	_no_hub = false
	_fundo.visible = false

## Título e hub entre corridas: saldo, amuleto equipado e as estações (Forja, Melhorias).
func mostrar_titulo() -> void:
	var linhas := []
	if meta != null:
		linhas = _resumo_hub()
		if linhas.size() > 1 and not meta.materiais.is_empty() and not str(linhas[1]).begins_with(Csv.t("menu.forge_equipped").split("%")[0]):
			linhas.remove_at(1)   # os materiais aparecem na Forja; no título a lista comprida empurrava os botões para fora da tela
	_no_hub = true
	var botoes := [["menu.play", _jogar_do_titulo, jogar_bloqueado()], ["menu.forge", mostrar_forja], ["menu.meta", mostrar_meta]]
	if opcoes.prologo_visto:
		botoes.append(["menu.prologue", prologo.iniciar])
	botoes.append_array([["menu.options", func() -> void: mostrar_opcoes(mostrar_titulo)], ["menu.quit", sair]])
	var cartoes := VBoxContainer.new()
	cartoes.add_theme_constant_override("separation", 10)
	cartoes.add_child(_cartao_classe())
	if not Fase.ids().is_empty():
		cartoes.add_child(_cartao_fase())
	_montar(Tela.TITULO, "menu.title", "menu.subtitle", botoes, linhas, cartoes)

## Jogar fica desativado na fase escolhida trancada ou sem mapa ainda ("em breve").
func jogar_bloqueado() -> bool:
	return not Fase.ids().is_empty() and not Fase.pode_jogar(Fase.atual)

## Cartão da fase no título (mesma moldura do cartão da classe): nome, uma linha de descrição e setas para trocar
## (mouse ou ← →). Trancada: cadeado e a dica de qual fase vencer; sem mapa ainda: a dica "em breve".
func _cartao_fase() -> Control:
	var id := Fase.atual
	var d: Dictionary = Fase.dados(id)
	var aberta := Fase.desbloqueada(id)
	var cartao := PanelContainer.new()
	cartao.name = "CartaoFase"
	cartao.add_theme_stylebox_override("panel", Tema.caixa(Tema.cor("pedra_clara"), Tema.cor("borda"), 2, 5, 10))
	var linha := HBoxContainer.new()
	linha.add_theme_constant_override("separation", 10)
	cartao.add_child(linha)
	linha.add_child(_seta_fase("SetaAnterior", "menu.fase_ant", -1))
	var col := VBoxContainer.new()
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.add_theme_constant_override("separation", 4)
	linha.add_child(col)
	var ids := Fase.ids()
	var conta := Label.new()
	conta.text = Csv.t("menu.fase") % [ids.find(id) + 1, ids.size()]
	conta.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	conta.add_theme_font_size_override("font_size", 13)
	conta.add_theme_color_override("font_color", Tema.cor("texto_suave"))
	col.add_child(conta)
	var topo := HBoxContainer.new()
	topo.alignment = BoxContainer.ALIGNMENT_CENTER
	topo.add_theme_constant_override("separation", 8)
	col.add_child(topo)
	if not aberta:
		var cad := Control.new()
		cad.name = "Cadeado"
		cad.custom_minimum_size = Vector2(26, 30)
		cad.draw.connect(func() -> void: Arte.cadeado(cad, Vector2(13, 11), 20.0))
		topo.add_child(cad)
	var nome := Label.new()
	nome.name = "NomeFase"
	nome.text = Csv.t(str(d.get("nome", id)))
	nome.add_theme_font_size_override("font_size", 24)
	nome.add_theme_color_override("font_color", Tema.cor("destaque") if aberta else Tema.cor("texto_suave"))
	topo.add_child(nome)
	var desc := Label.new()
	desc.text = Csv.t(str(d.get("descricao", "")))
	desc.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc.custom_minimum_size = Vector2(320, 0)
	desc.add_theme_font_size_override("font_size", 15)
	desc.add_theme_color_override("font_color", Tema.cor("texto_suave"))
	col.add_child(desc)
	var dica := ""
	if not aberta:
		dica = Csv.t("fase.trancada") % Csv.t(str(Fase.dados(Fase.requer(id)).get("nome", Fase.requer(id))))
	elif not Fase.disponivel(id):
		dica = Csv.t("fase.em_breve")
	if dica != "":
		var l := Label.new()
		l.name = "DicaFase"
		l.text = dica
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.custom_minimum_size = Vector2(320, 0)
		l.add_theme_font_size_override("font_size", 15)
		l.add_theme_color_override("font_color", Tema.cor("destaque"))
		col.add_child(l)
	linha.add_child(_seta_fase("SetaProxima", "menu.fase_prox", 1))
	return cartao

func _seta_fase(nome: String, chave: String, passo: int) -> Button:
	var b := Button.new()
	b.name = nome
	b.text = Csv.t(chave)
	b.custom_minimum_size = Vector2(40, 0)
	b.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	b.add_theme_font_override("font", load(FONTE_TITULO))
	b.add_theme_font_size_override("font_size", 20)
	b.disabled = Fase.ids().size() < 2
	b.pressed.connect(func() -> void: trocar_fase(passo))
	return b

## Passa para a fase seguinte (`passo` 1) ou anterior (-1) da tabela, grava a escolha e redesenha o título.
func trocar_fase(passo: int) -> void:
	Audio.tocar("ui_click")
	Fase.alternar(passo)
	if meta != null and meta.has_method("escolher_fase"):
		meta.escolher_fase(Fase.atual)
	mostrar_titulo()

## Cartão da classe no título: retrato animado, nome, estilo de jogo e o botão que troca a classe.
func _cartao_classe() -> Control:
	var cartao := PanelContainer.new()
	cartao.add_theme_stylebox_override("panel", Tema.caixa(Tema.cor("pedra_clara"), Tema.cor("borda"), 2, 5, 10))
	var linha := HBoxContainer.new()
	linha.add_theme_constant_override("separation", 14)
	cartao.add_child(linha)
	_retrato_classe = TextureRect.new()
	_retrato_classe.custom_minimum_size = Vector2(96, 96)
	_retrato_classe.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_retrato_classe.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_retrato_classe.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	linha.add_child(_retrato_classe)
	var col := VBoxContainer.new()
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	linha.add_child(col)
	var nome := Label.new()
	nome.text = Csv.t("class.%s.name" % Classe.atual)
	nome.add_theme_font_size_override("font_size", 26)
	nome.add_theme_color_override("font_color", Tema.cor("destaque"))
	col.add_child(nome)
	var desc := Label.new()
	desc.text = Csv.t("class.%s.desc" % Classe.atual)
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc.custom_minimum_size = Vector2(300, 0)
	desc.add_theme_font_size_override("font_size", 16)
	desc.add_theme_color_override("font_color", Tema.cor("texto_suave"))
	col.add_child(desc)
	var trocar := Button.new()
	trocar.text = Csv.t("menu.class_change")
	trocar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	trocar.pressed.connect(func() -> void:
		Audio.tocar("ui_click")
		Classe.alternar()
		mostrar_titulo())
	linha.add_child(trocar)
	_retrato_t = 0.0
	return cartao

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
	_no_hub = false
	_montar(Tela.ROTA, "menu.route_title", "menu.route_hint", opcoes)

func mostrar_pausa() -> void:
	_no_hub = false
	_montar(Tela.PAUSA, "menu.paused", "", [
		["menu.resume", retomar], ["menu.restart", jogar],
		["menu.options", func() -> void: mostrar_opcoes(mostrar_pausa)], ["menu.to_title", ao_titulo]])

## `resumo` é um Array de linhas já formatadas (tempo, salas, upgrades). `avisos`: linhas em destaque (ex. fase nova aberta).
func mostrar_fim(venceu: bool, resumo: Array, avisos: Array = []) -> void:
	_no_hub = false
	steam.evento("corrida_fim")
	if venceu:
		steam.evento("vitoria")
	var extra: VBoxContainer = null
	if not avisos.is_empty():
		extra = VBoxContainer.new()
		extra.name = "AvisosFim"
		for a in avisos:
			var l := Label.new()
			l.text = a
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			l.add_theme_font_size_override("font_size", 26)
			l.add_theme_color_override("font_color", Tema.cor("destaque"))
			l.add_theme_font_override("font", load(FONTE_TITULO))
			l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
			l.add_theme_constant_override("outline_size", 6)
			extra.add_child(l)
	_montar(Tela.FIM, "menu.victory" if venceu else "menu.game_over", "", [
		["menu.play_again", jogar], ["menu.to_title", ao_titulo]], resumo, extra)

## Resumo da corrida em duas colunas: cada linha "Rótulo: valor" vira uma célula (rótulo pequeno em cima, valor em
## destaque embaixo). Linha comprida (materiais) ocupa a largura toda, abaixo da grade, para o painel não ficar alto.
func _resumo_fim(linhas: Array) -> Control:
	var col := VBoxContainer.new()
	col.name = "ResumoFim"
	col.add_theme_constant_override("separation", 10)
	var grade := GridContainer.new()
	grade.name = "Grade"
	grade.columns = 2
	grade.add_theme_constant_override("h_separation", 10)
	grade.add_theme_constant_override("v_separation", 8)
	col.add_child(grade)
	for l in linhas:
		var partes: PackedStringArray = str(l).split(": ", true, 1)
		var longa: bool = partes.size() < 2 or str(l).length() > 34
		var celula := PanelContainer.new()
		celula.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		celula.add_theme_stylebox_override("panel", Tema.caixa(Tema.cor("pedra_pressionada"), Tema.cor("borda"), 1, 4, 8))
		var v := VBoxContainer.new()
		v.add_theme_constant_override("separation", 0)
		celula.add_child(v)
		for i in partes.size():
			var rot := Label.new()
			rot.text = partes[i]
			rot.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			rot.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			var valor: bool = i == partes.size() - 1 and partes.size() > 1
			rot.add_theme_font_size_override("font_size", (16 if longa else 22) if valor else 14)
			rot.add_theme_color_override("font_color", Tema.cor("texto") if valor else Tema.cor("texto_suave"))
			v.add_child(rot)
		if longa:
			col.add_child(celula)
		else:
			grade.add_child(celula)
	if grade.get_child_count() % 2 == 1:   # número ímpar: a última célula ocupa a linha inteira, logo abaixo da grade
		var ultima := grade.get_child(grade.get_child_count() - 1)
		grade.remove_child(ultima)
		col.add_child(ultima)
		col.move_child(ultima, 1)
	return col

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

func _montar(t: Tela, titulo: String, subtitulo: String, botoes: Array, linhas: Array = [], extra: Control = null) -> void:
	for c in _caixa.get_children():
		_caixa.remove_child(c)
		c.queue_free()
	_caixa.custom_minimum_size.x = 560 if t == Tela.TITULO else (500 if t == Tela.FIM else 420)
	_caixa.add_theme_constant_override("separation", 10 if t == Tela.TITULO else 14)
	_centro.anchor_right = 0.52 if t == Tela.TITULO else 1.0   # título: o painel fica à esquerda e deixa o arqueiro e os braseiros da cena à vista
	# título: painel levemente translúcido, a cena aparece por trás; nas demais telas ele é quase opaco
	(_painel.get_theme_stylebox("panel") as StyleBoxFlat).bg_color = Color(Tema.cor("pedra"), 0.84 if t == Tela.TITULO else 0.94)
	var titulo_l := _rotulo(Csv.t(titulo), 46 if t == Tela.TITULO else 40, Tema.cor("destaque"))
	titulo_l.add_theme_font_override("font", load(FONTE_TITULO))
	if t == Tela.TITULO:
		titulo_l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
		titulo_l.add_theme_constant_override("outline_size", 8)
	if subtitulo != "":
		_rotulo(Csv.t(subtitulo), 16, Tema.cor("texto_suave"))
	if t == Tela.FIM:
		_caixa.add_child(_resumo_fim(linhas))
	else:
		for l in linhas:
			_rotulo(l, 20)
	if extra != null:
		_caixa.add_child(extra)
	var primeiro: Button = null
	# Título: Jogar em destaque e as demais opções em duas colunas (a lista em fila única não cabia em 720 px de altura).
	var grade: GridContainer = null
	if t == Tela.TITULO:
		grade = GridContainer.new()
		grade.columns = 2
		grade.add_theme_constant_override("h_separation", 10)
		grade.add_theme_constant_override("v_separation", 8)
	for i in botoes.size():
		var b: Array = botoes[i]
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
		if grade != null and i == 0:
			btn.custom_minimum_size.y = 52
			btn.add_theme_font_size_override("font_size", 22)
			btn.add_theme_font_override("font", load(FONTE_TITULO))
			btn.add_theme_color_override("font_color", Tema.cor("destaque"))
			btn.add_theme_color_override("font_focus_color", Tema.cor("destaque"))
			_caixa.add_child(btn)
			_caixa.add_child(grade)
		elif grade != null:
			btn.custom_minimum_size.y = 44
			btn.add_theme_font_size_override("font_size", 18)
			btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			grade.add_child(btn)
		else:
			_caixa.add_child(btn)
		if primeiro == null and not btn.disabled:
			primeiro = btn
	if grade != null and grade.get_child_count() % 2 == 1:   # número ímpar: o último ocupa a linha inteira, fora da grade
		var ultimo := grade.get_child(grade.get_child_count() - 1)
		grade.remove_child(ultimo)
		_caixa.add_child(ultimo)
	tela = t
	_arte.visible = _no_hub
	_fundo.visible = true
	if primeiro != null:
		_focar.call_deferred(primeiro)

## Foco no botão, se ele ainda está na tela (ela pode ter sido remontada no mesmo quadro, ex. setas do cartão de fase).
func _focar(b) -> void:   # sem tipo: o botão pode já ter sido liberado
	if is_instance_valid(b) and b.is_inside_tree():
		b.grab_focus()

func _rotulo(texto: String, tam: int, cor := Color(0.9, 0.88, 0.84)) -> Label:
	var l := Label.new()
	l.text = texto
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", tam)
	l.add_theme_color_override("font_color", cor)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size.x = _caixa.custom_minimum_size.x   # sem largura mínima, uma linha comprida quebra palavra por palavra e estica o painel para fora da tela
	_caixa.add_child(l)
	return l

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
	if tela == Tela.TITULO and (ev.keycode == KEY_LEFT or ev.keycode == KEY_RIGHT) and not prologo.ativo and Fase.ids().size() > 1:
		trocar_fase(-1 if ev.keycode == KEY_LEFT else 1)   # ← → trocam a fase no título
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
