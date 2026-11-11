extends CanvasLayer
## Tela de escolha entre cartas (nível, baú de elite, gema de habilidade, Eco do arco, sala limpa). Pausa a árvore enquanto aberta.
## Clique na carta, teclas 1 a 4, ou setas/controle e Enter. Textos por chave de localização; medidas e cores em
## data2d/cartas_layout.csv e data2d/tema.csv.
## Cada carta: tecla e etiqueta (ramo e tipo, ou raridade) no topo, ícone pintado, nome em serifa, descrição e os
## losangos de nível (os já ganhos apagados, o que a carta dá agora aceso).

const Csv = preload("res://scripts2d/csv2d.gd")
const Tema = preload("res://scripts2d/tema_2d.gd")
const Icones = preload("res://scripts2d/icones_2d.gd")
const Audio = preload("res://scripts2d/audio_2d.gd")
const Afinidades = preload("res://scripts2d/afinidades_2d.gd")
const FONTE_TITULO := "res://art2d/ui/DejaVuSerif-Bold.ttf"

signal escolhido(id: String)

var upgrades: RefCounted
var aberta := false
var modo := "sala"        # "sala" (sala limpa), "level" (subiu de nível), "chest" (baú de elite), "gem" (gema de habilidade) ou "afinidade"
var _fonte: RefCounted    # de onde vêm `defs` e `nivel(id)` das cartas abertas (upgrades ou a árvore de habilidades)
var _titulo: Label
var _sub: Label
var _ids: Array = []
var _caixa: HBoxContainer
var _fundo: ColorRect
var _lay := {}
var _raridade := {}       # id da carta de reforço -> raridade (upgrades.csv)
var _tween: Tween

func _ready() -> void:
	layer = 10
	process_mode = Node.PROCESS_MODE_ALWAYS
	_lay = Csv.kv("res://data2d/cartas_layout.csv")
	for r in Csv.rows("res://data2d/upgrades.csv"):
		_raridade[r["id"]] = str(r.get("raridade", "comum"))
	_fundo = ColorRect.new()
	_fundo.color = Color(Tema.cor("fundo_escuro"), float(_lay.get("fundo_alfa", 0.82)))
	_fundo.theme = Tema.tema()
	_fundo.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_fundo)
	var centro := CenterContainer.new()
	centro.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fundo.add_child(centro)
	var col := VBoxContainer.new()
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.add_theme_constant_override("separation", 6)
	centro.add_child(col)
	_titulo = _rotulo(col, Csv.t("upgrade.title"), int(_lay.get("titulo_fonte", 30)), Tema.cor("destaque"), true)
	_titulo.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	_titulo.add_theme_constant_override("outline_size", 6)
	col.add_child(_enfeite(float(_lay.get("enfeite_largura", 320))))
	_sub = _rotulo(col, "", int(_lay.get("sub_fonte", 15)), Tema.cor("texto_suave"))
	var respiro := Control.new()
	respiro.custom_minimum_size.y = float(_lay.get("respiro", 14))
	col.add_child(respiro)
	_caixa = HBoxContainer.new()
	_caixa.alignment = BoxContainer.ALIGNMENT_CENTER
	_caixa.add_theme_constant_override("separation", int(_lay.get("carta_espaco", 22)))
	col.add_child(_caixa)
	_fundo.visible = false

func _rotulo(pai: Control, texto: String, tam: int, cor: Color, serifa := false) -> Label:
	var l := Label.new()
	l.text = texto
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", tam)
	l.add_theme_color_override("font_color", cor)
	if serifa:
		l.add_theme_font_override("font", load(FONTE_TITULO))
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	pai.add_child(l)
	return l

## Fio dourado com um losango no meio, sob o título.
func _enfeite(largura: float) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(largura, 12)
	c.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var cor := Tema.cor("destaque")
	c.draw.connect(func() -> void:
		var m := c.size / 2.0
		c.draw_line(Vector2(0, m.y), Vector2(m.x - 10, m.y), Color(cor, 0.55), 1.0)
		c.draw_line(Vector2(m.x + 10, m.y), Vector2(c.size.x, m.y), Color(cor, 0.55), 1.0)
		c.draw_colored_polygon(PackedVector2Array([m + Vector2(0, -5), m + Vector2(5, 0), m + Vector2(0, 5), m + Vector2(-5, 0)]), cor))
	return c

## `m`: "sala", "level", "chest", "gem" ou "afinidade"; `nivel` aparece no título da carta de nível. `fonte` (opcional) é de
## onde vêm as definições e o nível das cartas: a árvore de habilidades no modo "gem", senão `upgrades`.
func abrir(ids: Array, m := "sala", nivel := 0, fonte: RefCounted = null) -> void:
	_ids = ids
	modo = m
	_fonte = fonte if fonte != null else upgrades
	match m:
		"level":
			_titulo.text = Csv.t("upgrade.level_up") % nivel
		"chest":
			_titulo.text = Csv.t("upgrade.chest")
		"gem":
			_titulo.text = Csv.t("upgrade.gem")
		"afinidade":   # título por classe quando existe (upgrade.afinidade.<classe>), senão o comum
			var chave := "upgrade.afinidade." + (Afinidades.classe_de(str(ids[0])) if not ids.is_empty() else "")
			_titulo.text = Csv.t(chave) if Csv.t(chave) != chave else Csv.t("upgrade.afinidade")
		_:
			_titulo.text = Csv.t("upgrade.title")
	_sub.text = Csv.t("carta.dica") % ids.size()
	for c in _caixa.get_children():
		_caixa.remove_child(c)
		c.queue_free()
	if _tween != null:
		_tween.kill()
	_tween = create_tween().set_parallel(true)
	var primeira: Button = null
	for i in ids.size():
		var b := _carta(i, ids[i])
		_caixa.add_child(b)
		if primeira == null:
			primeira = b
		# Entrada: cada carta aparece um instante depois da anterior.
		b.modulate.a = 0.0
		_tween.tween_property(b, "modulate:a", 1.0, float(_lay.get("entrada_tempo", 0.18))).set_delay(i * float(_lay.get("entrada_atraso", 0.06)))
	_fundo.visible = true
	_fundo.modulate.a = 0.0
	_tween.tween_property(_fundo, "modulate:a", 1.0, float(_lay.get("entrada_tempo", 0.18)))
	aberta = true
	Audio.tocar("card_open")
	get_tree().paused = true
	if primeira != null:
		primeira.grab_focus.call_deferred()

## Cor de destaque da carta: a do elemento ou ramo (habilidade, Eco) ou a da raridade (reforço).
func _cor_da_carta(id: String, d: Dictionary) -> Color:
	var ramo := str(d.get("ramo", ""))
	if ramo == "afinidade":
		ramo = Afinidades.elemento(id)
	if ramo != "":
		return Tema.cor("ramo_" + ramo) if Tema.tem("ramo_" + ramo) else Tema.cor("destaque")
	return Tema.cor("carta_rara") if _raridade.get(id, "comum") == "rara" else Tema.cor("carta_comum")

func _etiqueta(id: String, d: Dictionary) -> String:
	var ramo := str(d.get("ramo", ""))
	if ramo == "afinidade":
		return Csv.t("ramo.%s.name" % Afinidades.elemento(id))
	if ramo != "":
		return "%s · %s" % [Csv.t("ramo.%s.name" % ramo), Csv.t("carta.tipo_" + str(d.get("tipo", "ativa")))]
	return Csv.t("carta.raridade_" + str(_raridade.get(id, "comum")))

func _moldura(fundo: Color, borda: Color, largura: int) -> StyleBoxFlat:
	var sb := Tema.caixa(fundo, borda, largura, 6, int(_lay.get("carta_margem", 14)))
	sb.shadow_color = Color(0, 0, 0, 0.55)
	sb.shadow_size = 10
	sb.shadow_offset = Vector2(0, 4)
	return sb

func _carta(i: int, id: String) -> Button:
	var d: Dictionary = _fonte.defs[id]
	var cor := _cor_da_carta(id, d)
	var habilidade: bool = d.has("ramo")   # habilidades (árvore) e Ecos têm ramo; reforços não
	var pre := "skill" if habilidade else "upgrade"
	var ja: int = _fonte.nivel(id)
	var maximo := int(d.get("nivel_max", 1))
	var b := Button.new()
	b.custom_minimum_size = Vector2(float(_lay.get("carta_largura", 250)), float(_lay.get("carta_altura", 356)))
	b.add_theme_stylebox_override("normal", _moldura(Tema.cor("pedra"), cor.darkened(0.45), 2))
	b.add_theme_stylebox_override("hover", _moldura(Tema.cor("pedra_clara"), cor, 3))
	b.add_theme_stylebox_override("pressed", _moldura(Tema.cor("pedra_pressionada"), cor, 3))
	b.add_theme_stylebox_override("focus", _moldura(Color(0, 0, 0, 0), cor, 3))
	b.pressed.connect(escolher.bind(i))
	b.mouse_entered.connect(b.grab_focus)
	var margem := MarginContainer.new()
	margem.set_anchors_preset(Control.PRESET_FULL_RECT)
	margem.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for lado in ["left", "right", "top", "bottom"]:
		margem.add_theme_constant_override("margin_" + lado, int(_lay.get("carta_margem", 14)))
	b.add_child(margem)
	var col := VBoxContainer.new()
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_theme_constant_override("separation", 6)
	margem.add_child(col)
	# Topo: tecla à esquerda, etiqueta à direita.
	var topo := HBoxContainer.new()
	topo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(topo)
	var tecla := PanelContainer.new()
	tecla.mouse_filter = Control.MOUSE_FILTER_IGNORE
	tecla.add_theme_stylebox_override("panel", Tema.caixa(Tema.cor("pedra_pressionada"), Tema.cor("borda"), 1, 3, 2))
	tecla.custom_minimum_size = Vector2(22, 22)
	_rotulo(tecla, str(i + 1), 13, Tema.cor("texto"))
	topo.add_child(tecla)
	var etiqueta := _rotulo(topo, _etiqueta(id, d), 13, cor)
	etiqueta.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	etiqueta.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	etiqueta.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	# Ícone
	var icone := TextureRect.new()
	icone.texture = Icones.textura(id)
	if icone.texture == null and d.has("icone"):
		icone.texture = Icones.textura(str(d["icone"]))
	var lado_icone := float(_lay.get("icone_lado", 112))
	icone.custom_minimum_size = Vector2(lado_icone, lado_icone)
	icone.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icone.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	icone.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST   # pixel art de 48 px: sobe em escala inteira, sem suavizar
	icone.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	icone.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(icone)
	# Nome e descrição
	var nome := _rotulo(col, Csv.t("%s.%s.name" % [pre, id]), int(_lay.get("nome_fonte", 19)), Tema.cor("destaque"), true)
	nome.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	var fio := ColorRect.new()
	fio.color = Color(cor, 0.5)
	fio.custom_minimum_size = Vector2(float(_lay.get("fio_largura", 120)), 1)
	fio.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	fio.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(fio)
	var desc := _rotulo(col, Csv.t("%s.%s.desc" % [pre, id]), int(_lay.get("desc_fonte", 14)), Tema.cor("texto"))
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	desc.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	# Rodapé: losangos de nível e o texto do nível (habilidade nova diz "Nova").
	col.add_child(_losangos(ja, maximo, cor))
	var txt_nivel: String = Csv.t("carta.nova") if habilidade and ja == 0 and modo != "afinidade" else Csv.t("upgrade.level") % [ja + 1, maximo]
	if modo == "afinidade":
		txt_nivel = Csv.t("carta.corrida")
	_rotulo(col, txt_nivel, 12, Tema.cor("texto_suave"))
	return b

## Losangos de nível: os `ja` ganhos em tom apagado, o que a carta dá agora na cor cheia, os restantes vazados.
func _losangos(ja: int, maximo: int, cor: Color) -> Control:
	var c := Control.new()
	var passo := 16.0
	c.custom_minimum_size = Vector2(passo * maximo, 14)
	c.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.draw.connect(func() -> void:
		for k in maximo:
			var m := Vector2(passo * (k + 0.5), 7)
			var pts := PackedVector2Array([m + Vector2(0, -5), m + Vector2(5, 0), m + Vector2(0, 5), m + Vector2(-5, 0)])
			if k < ja:
				c.draw_colored_polygon(pts, cor.darkened(0.4))
			elif k == ja:
				c.draw_colored_polygon(pts, cor)
			pts.append(pts[0])
			c.draw_polyline(pts, cor if k <= ja else Color(Tema.cor("borda"), 0.9), 1.0))
	return c

func escolher(i: int) -> void:
	if not aberta or i < 0 or i >= _ids.size():
		return
	aberta = false
	if _tween != null:
		_tween.kill()
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
