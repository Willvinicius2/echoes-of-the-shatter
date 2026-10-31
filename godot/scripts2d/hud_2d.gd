extends CanvasLayer
## HUD de ARPG sombrio: globos de vida e recurso, barra de habilidades de pedra e ferro, plaqueta da sala, barra do chefe
## e mensagem central. Peças em hud_arte_2d.gd; medidas em data2d/hud_layout.csv; textos por chave de localização.

const Csv = preload("res://scripts2d/csv2d.gd")
const Tema = preload("res://scripts2d/tema_2d.gd")
const Icones = preload("res://scripts2d/icones_2d.gd")
const Arte = preload("res://scripts2d/hud_arte_2d.gd")

var jogador: Node2D
var sala := 1
var total_salas := 1
var mensagem := ""
var chefe: Node2D
var upgrades: RefCounted
var tempo := 0.0
var _ctl: Control
var _lay := {}
var _rel := 0.0         # relógio da animação (líquido, pulso)
var _hp_fantasma := 1.0 # fração antiga de vida, desce devagar depois de um golpe

func _ready() -> void:
	_lay = Csv.kv("res://data2d/hud_layout.csv")
	_ctl = Control.new()
	_ctl.set_anchors_preset(Control.PRESET_FULL_RECT)
	_ctl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ctl.draw.connect(_desenhar)
	add_child(_ctl)

func _process(d: float) -> void:
	_rel += d
	if jogador != null and "hp" in jogador:
		var f: float = clampf(jogador.hp / jogador.stats.get("hp_max", 1.0), 0.0, 1.0)
		_hp_fantasma = f if f >= _hp_fantasma else maxf(f, _hp_fantasma - d * 0.35)
	_ctl.queue_redraw()

func _desenhar() -> void:
	var vp := _ctl.size
	_fundo_inferior(vp)
	if jogador != null and "hp" in jogador:
		_desenhar_base(vp)
		_desenhar_habilidades(vp)
		_desenhar_globos(vp)
	_desenhar_upgrades()
	Arte.plaqueta(_ctl, Rect2(vp.x - 8 - _lay["plaqueta_largura"], 8, _lay["plaqueta_largura"], 58), Csv.t("hud.room") % [sala, total_salas], Csv.t("hud.time") % _tempo_texto())
	if _rel < 8.0 and estado_ajuda_visivel():
		var al := clampf((8.0 - _rel) / 2.0, 0.0, 1.0)
		var cor := Color(Tema.cor("texto").r, Tema.cor("texto").g, Tema.cor("texto").b, al)
		Arte.texto(_ctl, Vector2(0, vp.y - 135), Csv.t("hud.help"), 15, cor, HORIZONTAL_ALIGNMENT_CENTER, vp.x)
	if chefe != null and is_instance_valid(chefe) and chefe.hp > 0.0:
		var w: float = _lay["chefe_largura"]
		var r := Rect2(vp.x * 0.5 - w * 0.5, 62, w, 18)
		Arte.barra(_ctl, r, chefe.hp / chefe.hp_max, Tema.cor("chefe_escura"), Tema.cor("chefe_clara"))
		Arte.texto(_ctl, Vector2(r.position.x, r.position.y - 12), Csv.t("hud.boss"), 18, Tema.cor("destaque"), HORIZONTAL_ALIGNMENT_CENTER, w)
	if mensagem != "":
		Arte.texto(_ctl, Vector2(0, vp.y * 0.3), mensagem, 32, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_CENTER, vp.x)

## A lista completa de controles só aparece nos primeiros segundos (os slots já têm as plaquinhas de tecla).
func estado_ajuda_visivel() -> bool:
	return mensagem == ""

func _tempo_texto() -> String:
	var total := int(tempo)
	return "%02d:%02d" % [total / 60, total % 60]

## Sombra suave no rodapé para os globos e os slots lerem sobre qualquer sala (curta e leve: o combate continua visível).
func _fundo_inferior(vp: Vector2) -> void:
	var h: float = _lay.get("rodape_altura", 90.0)
	var al: float = _lay.get("rodape_alfa", 0.25)
	_ctl.draw_polygon(PackedVector2Array([Vector2(0, vp.y - h), Vector2(vp.x, vp.y - h), Vector2(vp.x, vp.y), Vector2(0, vp.y)]), PackedColorArray([Color(0, 0, 0, 0), Color(0, 0, 0, 0), Color(0, 0, 0, al), Color(0, 0, 0, al)]))

func _centro_globo(vp: Vector2, direita: bool) -> Vector2:
	var r: float = _lay["globo_raio"]
	var m: float = _lay["globo_margem"]
	return Vector2(vp.x - m - r if direita else m + r, vp.y - m - r)

## Retângulos da barra de slots: 2 pequenos (ataque e esquiva) à esquerda e as ativas (Q E F R), o grupo centrado.
func retangulos_slots(vp: Vector2) -> Dictionary:
	var lado: float = _lay["slot_tamanho"]
	var esp: float = _lay["slot_espaco"]
	var peq: float = _lay.get("slot_pequeno", 52.0)
	var gap: float = _lay.get("slot_grupo_espaco", 18.0)
	var total := int(_lay["slot_total"])
	var largura := 2.0 * peq + esp * 0.8 + gap + total * lado + (total - 1) * esp
	var x := (vp.x - largura) * 0.5
	var base: float = vp.y - _lay["slot_base"]
	var basicos: Array = []
	for i in 2:
		basicos.append(Rect2(x, base - peq, peq, peq))
		x += peq + esp * 0.8
	x += gap - esp * 0.8
	var ativas: Array = []
	for i in total:
		ativas.append(Rect2(x, base - lado, lado, lado))
		x += lado + esp
	var grupo := Rect2((vp.x - largura) * 0.5, base - lado, largura, lado)
	return {"basicos": basicos, "ativas": ativas, "grupo": grupo}

## Fundo da barra de slots, conforme `faixa_modo` em hud_layout.csv: faixa pintada justa aos slots (9-slice),
## slots soltos com sombra ou friso fino de ferro.
func _desenhar_base(vp: Vector2) -> void:
	var rs := retangulos_slots(vp)
	var g: Rect2 = rs["grupo"]
	var modo := int(_lay.get("faixa_modo", 0.0))
	var faixa := Arte.tex("hud_faixa_pedra")
	if modo == 0 and faixa != null:
		var esc: float = _lay.get("faixa_escala", 0.5)
		var r := Rect2(g.position.x - 30.0, g.position.y - 12.0, g.size.x + 60.0, vp.y - g.position.y + 12.0)
		Arte.nove_fatias(_ctl, faixa, r, 48.0, 48.0, 20.0, 20.0, esc)
	elif modo == 2:
		for sr in rs["basicos"] + rs["ativas"]:
			Arte.sombra(_ctl, sr, 6.0, 0.3)
		Arte.friso(_ctl, g.position.x - 24.0, g.end.x + 24.0, vp.y - 6.0)
	else:
		for sr in rs["basicos"] + rs["ativas"]:
			Arte.sombra(_ctl, sr, 8.0, 0.4)

## Vida (esquerda) e recurso (direita, reservado e vazio). Vida baixa pulsa no aro.
func _desenhar_globos(vp: Vector2) -> void:
	var raio: float = _lay["globo_raio"]
	var hmax: float = jogador.stats.get("hp_max", 1.0)
	var frac: float = clampf(jogador.hp / hmax, 0.0, 1.0)
	var pulso := (0.4 + 0.6 * (0.5 + 0.5 * sin(_rel * 5.0))) if frac < 0.3 and frac > 0.0 else 0.0
	var ev := _centro_globo(vp, false)
	Arte.globo(_ctl, ev, raio, frac, _hp_fantasma, Tema.cor("vida_escura"), Tema.cor("vida_clara"), _rel, pulso)
	Arte.texto(_ctl, ev + Vector2(-raio, 4), "%d/%d" % [ceili(jogador.hp), int(hmax)], 18, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_CENTER, raio * 2.0)
	Arte.texto(_ctl, Vector2(ev.x + raio + 10, ev.y + 30), Csv.t("hud.hp"), 14, Tema.cor("texto_suave"))
	var ed := _centro_globo(vp, true)
	var rotulo := Csv.t("hud.mana")
	if "mana" in jogador:   # mana real (runtime de habilidades das classes)
		var mmax: float = maxf(1.0, jogador.stats.get("mana_max", 1.0))
		Arte.globo(_ctl, ed, raio, clampf(jogador.mana / mmax, 0.0, 1.0), 0.0, Tema.cor("mana_escura"), Tema.cor("mana_clara"), _rel)
		Arte.texto(_ctl, ed + Vector2(-raio, 4), "%d/%d" % [floori(jogador.mana), int(mmax)], 18, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_CENTER, raio * 2.0)
	elif jogador.has_method("recurso_frac"):   # guerreiro: ímpeto
		Arte.globo(_ctl, ed, raio, jogador.recurso_frac(), 0.0, Tema.cor("impeto_escura"), Tema.cor("impeto_clara"), _rel)
		if "impeto" in jogador:
			Arte.texto(_ctl, ed + Vector2(-raio, 4), "%d/%d" % [floori(jogador.impeto), int(jogador.stats.get("impeto_max", 0.0))], 18, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_CENTER, raio * 2.0)
		rotulo = Csv.t("hud.fury")
	else:   # recurso ainda trancado: vidro vazio, corrente em X e cadeado
		Arte.globo(_ctl, ed, raio, 0.0, 0.0, Tema.cor("mana_escura"), Tema.cor("mana_clara"), _rel, 0.0, true)
		_ctl.draw_circle(ed + Vector2(0, raio * 0.3), raio * 0.55, Color(0.2, 0.3, 0.9, 0.12))
		var rr := raio * 0.5
		Arte.corrente(_ctl, ed + Vector2(-rr, -rr), ed + Vector2(rr, rr), 7)
		Arte.corrente(_ctl, ed + Vector2(rr, -rr), ed + Vector2(-rr, rr), 7)
		Arte.cadeado(_ctl, ed + Vector2(0, -8), 20.0)
	Arte.texto(_ctl, Vector2(ed.x - raio - 150, ed.y + 30), rotulo, 14, Tema.cor("texto_suave"), HORIZONTAL_ALIGNMENT_RIGHT, 140.0)

func _desenhar_upgrades() -> void:
	if upgrades == null or upgrades.niveis.is_empty():
		return
	var x: float = _lay["margem"] - 8
	var y: float = _lay["lista_y"]
	var lado := 38.0
	var mouse := _ctl.get_local_mouse_position()
	var dica := ""
	var dica_pos := Vector2.ZERO
	for id in upgrades.ordem:
		var nv: int = upgrades.nivel(id)
		if nv <= 0:
			continue
		var r := Rect2(x, y, lado, lado)
		Arte.placa(_ctl, r, Tema.cor("pedra").darkened(0.15), 2.0, false)
		_ctl.draw_texture_rect(Icones.textura(id), r.grow(-6), false)
		var sel := r.has_point(mouse)
		if sel:
			_ctl.draw_rect(r, Tema.cor("destaque"), false, 2.0)
			var chave := "skill.%s.name" if upgrades.defs[id].has("ramo") else "upgrade.%s.name"  # habilidades têm ramo
			dica = "%s x%d" % [Csv.t(chave % id), nv]
			dica_pos = Vector2(r.position.x, r.end.y + 6)
		if nv > 1:
			var tag := Rect2(r.end.x - 20, r.end.y - 14, 22, 16)
			Arte.placa(_ctl, tag, Tema.cor("metal_escuro"), 1.0, false)
			Arte.texto(_ctl, Vector2(tag.position.x, tag.position.y + 12), "x%d" % nv, 12, Tema.cor("destaque").lightened(0.25), HORIZONTAL_ALIGNMENT_CENTER, tag.size.x)
		x += lado + 8.0
	if dica != "":
		var fonte := ThemeDB.fallback_font
		var larg := fonte.get_string_size(dica, HORIZONTAL_ALIGNMENT_LEFT, -1, 15).x + 20.0
		var rd := Rect2(dica_pos, Vector2(larg, 26))
		Arte.placa(_ctl, rd, Tema.cor("pedra"), 2.0, false)
		Arte.texto(_ctl, rd.position + Vector2(0, 19), dica, 15, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_CENTER, larg)

## Conteúdo dos slots: `basicos` (ataque e esquiva) e `ativas` (4 entradas; {} = encaixe vazio). Lê, por duck typing,
## o guerreiro (`slots_hud`, `skills`, `impeto`) ou o runtime comum de habilidades (`habilidades` com slots,
## defs, recargas, recarga_slot e def_nivel; `mana`).
func conteudo_slots() -> Dictionary:
	var total := int(_lay["slot_total"])
	var cdmax: float = jogador.stats.get("dodge_cooldown", 1.0)
	var basicos: Array = [
		{"icone": "tiro", "tecla": "hud.key.shoot", "recarga": jogador.recarga_tiro() if jogador.has_method("recarga_tiro") else 0.0, "cor": Tema.cor("destaque")},
		{"icone": "esquiva", "tecla": "hud.key.dodge", "recarga": clampf(jogador.dodge_cd / maxf(cdmax, 0.01), 0.0, 1.0), "cor": Tema.cor("estamina")},
	]
	var ativas: Array = []
	ativas.resize(total)
	ativas.fill({})
	if jogador.has_method("slots_hud"):   # guerreiro: golpe, esquiva e as ativas aprendidas
		var sl: Array = jogador.slots_hud()
		basicos[0] = sl[0]
		basicos[1] = sl[1]
		basicos[0]["cor"] = Tema.cor("destaque")
		basicos[1]["cor"] = Tema.cor("estamina")
		var sk = jogador.skills if "skills" in jogador else null
		for i in mini(total, sl.size() - 2):
			var e: Dictionary = sl[i + 2]
			var id: String = e["icone"]
			if id == "":
				continue
			e["cor"] = Tema.cor("destaque")
			e["tecla"] = "hud.key.skill%d" % (i + 1)
			if sk != null and sk.defs.has(id):
				e["segundos"] = e["recarga"] * sk.recarga(id)
				e["sem_recurso"] = "impeto" in jogador and sk.def(id)["custo"] > jogador.impeto
			ativas[i] = e
	elif "habilidades" in jogador and jogador.habilidades != null and jogador.habilidades.has_method("recarga_slot"):
		var hab = jogador.habilidades
		for i in mini(total, hab.slots.size()):
			var id: String = hab.slots[i]
			if id == "" or not hab.defs.has(id):
				continue
			var icone: String = hab.defs[id].get("icone", id)
			ativas[i] = {"icone": icone if Icones.textura(icone) != null else "tiro", "tecla": "hud.key.skill%d" % (i + 1),
				"recarga": hab.recarga_slot(i), "segundos": float(hab.recargas.get(id, 0.0)), "cor": Tema.cor("mana_clara"),
				"sem_recurso": "mana" in jogador and float(hab.def_nivel(id)["custo"]) > jogador.mana}
	return {"basicos": basicos, "ativas": ativas}

## Barra de habilidades: ataque e esquiva em slots menores à esquerda e as 4 ativas (Q E F R) em slots grandes; encaixe
## vazio mostra só a tecla. A barra fina de estamina é opcional (`estamina_barra`), porque o slot de esquiva já mostra a recarga.
func _desenhar_habilidades(vp: Vector2) -> void:
	var rs := retangulos_slots(vp)
	var cs := conteudo_slots()
	if _lay.get("estamina_barra", 0.0) > 0.0:
		var cdmax: float = jogador.stats.get("dodge_cooldown", 1.0)
		var bw: float = _lay["estamina_barra_largura"]
		var g: Rect2 = rs["grupo"]
		Arte.barra(_ctl, Rect2(g.get_center().x - bw * 0.5, g.position.y - 18.0, bw, 6.0), 1.0 - clampf(jogador.dodge_cd / cdmax, 0.0, 1.0), Tema.cor("estamina").darkened(0.5), Tema.cor("estamina_clara"), 0)
	for i in 2:
		var sl: Dictionary = cs["basicos"][i]
		Arte.slot(_ctl, rs["basicos"][i], Icones.textura(sl["icone"]), sl["recarga"], Csv.t(sl["tecla"]), true, sl["cor"], -1.0, false, true)
	for i in rs["ativas"].size():
		var r: Rect2 = rs["ativas"][i]
		var sl: Dictionary = cs["ativas"][i]
		if sl.is_empty():
			Arte.encaixe_vazio(_ctl, r, Csv.t("hud.key.skill%d" % (i + 1)))
		else:
			Arte.slot(_ctl, r, Icones.textura(sl["icone"]), sl["recarga"], Csv.t(sl["tecla"]), true, sl["cor"], sl.get("segundos", -1.0), sl.get("sem_recurso", false))
