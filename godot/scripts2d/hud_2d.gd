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
	if jogador != null and "hp" in jogador:
		_desenhar_habilidades(vp)
		_desenhar_globos(vp)
		_desenhar_xp(vp)
	_desenhar_upgrades()
	Arte.placa_mini(_ctl, Rect2(vp.x - 6 - _lay["plaqueta_largura"], 6, _lay["plaqueta_largura"], 36), Csv.t("hud.room") % [sala, total_salas], Csv.t("hud.time") % _tempo_texto())
	if _rel < 5.0 and estado_ajuda_visivel():
		var al := clampf((5.0 - _rel) / 2.0, 0.0, 1.0)
		var cor := Color(Tema.cor("texto").r, Tema.cor("texto").g, Tema.cor("texto").b, al)
		Arte.texto(_ctl, Vector2(0, vp.y - 94), Csv.t("hud.help"), 12, cor, HORIZONTAL_ALIGNMENT_CENTER, vp.x)
	if chefe != null and is_instance_valid(chefe) and chefe.hp > 0.0:
		var w: float = _lay["chefe_largura"]
		var r := Arte.barra_chefe_fina(_ctl, vp.x * 0.5, 22.0, w, _lay["chefe_altura"], chefe.hp / chefe.hp_max, Tema.cor("chefe_clara"), [])
		Arte.texto(_ctl, Vector2(r.position.x, r.position.y - 6.0), Csv.t("hud.boss"), 13, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_LEFT, w)
	if mensagem != "":
		Arte.texto(_ctl, Vector2(0, vp.y * 0.3), mensagem, 32, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_CENTER, vp.x)

## A lista completa de controles só aparece nos primeiros segundos (os slots já têm as plaquinhas de tecla).
func estado_ajuda_visivel() -> bool:
	return mensagem == ""

func _tempo_texto() -> String:
	var total := int(tempo)
	return "%02d:%02d" % [total / 60, total % 60]

## Os dois globos ficam juntos no canto inferior esquerdo: vida (`direita` = false) e recurso (`direita` = true, ao lado).
func _centro_globo(vp: Vector2, direita: bool) -> Vector2:
	var r: float = _lay["globo_raio"]
	var m: float = _lay["globo_margem"]
	var x: float = m + r + ((2.0 * r + _lay.get("globo_espaco", 6.0)) if direita else 0.0)
	return Vector2(x, vp.y - m - r)

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

## Barra fina de XP acima da fileira de slots, com o nível. Só aparece no modo horda (o upgrades expõe `nivel_estado`).
func _desenhar_xp(vp: Vector2) -> void:
	var e := dados_xp()
	if e.is_empty():
		return
	var g: Rect2 = retangulos_slots(vp)["grupo"]
	var r := Rect2(g.position.x, g.position.y - 14.0, g.size.x, _lay.get("xp_altura", 6.0))
	var prox := maxf(1.0, float(e.get("xp_next", 1)))
	var frac := clampf(float(e.get("xp", 0)) / prox, 0.0, 1.0)
	_ctl.draw_rect(r.grow(1.5), Color(0, 0, 0, 0.7))
	_ctl.draw_rect(r, Color(0.05, 0.05, 0.08, 0.9))
	if frac > 0.0:
		_ctl.draw_rect(Rect2(r.position, Vector2(r.size.x * frac, r.size.y)), Tema.cor("destaque"))
		_ctl.draw_rect(Rect2(r.position, Vector2(r.size.x * frac, 2.0)), Color(1, 1, 1, 0.25))
	_ctl.draw_rect(r.grow(1.5), Tema.cor("metal_claro"), false, 1.0)
	Arte.texto(_ctl, Vector2(r.position.x, r.position.y - 4.0), Csv.t("hud.nivel") % int(e.get("level", 1)), 13, Tema.cor("texto"))
	Arte.texto(_ctl, Vector2(r.position.x, r.position.y - 4.0), Csv.t("hud.xp_valor") % [int(e.get("xp", 0)), int(prox)], 12, Tema.cor("texto_suave"), HORIZONTAL_ALIGNMENT_RIGHT, r.size.x)

## XP do jogador: `upgrades.nivel_estado()` ({level, xp, xp_next}) no modo horda; vazio fora dele. `xp_demo` serve às capturas.
var xp_demo := {}
func dados_xp() -> Dictionary:
	if not xp_demo.is_empty():
		return xp_demo
	if upgrades != null and upgrades.has_method("nivel_estado"):
		var e = upgrades.nivel_estado()
		if e is Dictionary and e.has("xp_next"):
			return e
	return {}

## Vida (esquerda) e recurso (direita, reservado e vazio). Vida baixa pulsa no aro.
func _desenhar_globos(vp: Vector2) -> void:
	var raio: float = _lay["globo_raio"]
	var hmax: float = jogador.stats.get("hp_max", 1.0)
	var frac: float = clampf(jogador.hp / hmax, 0.0, 1.0)
	var pulso := (0.4 + 0.6 * (0.5 + 0.5 * sin(_rel * 5.0))) if frac < 0.3 and frac > 0.0 else 0.0
	var ev := _centro_globo(vp, false)
	var ed := _centro_globo(vp, true)
	Arte.globo_mini(_ctl, ev, raio, frac, _hp_fantasma, Tema.cor("vida_escura"), Tema.cor("vida_clara"), _rel, pulso)
	_texto_globo(ev, raio, "%d/%d" % [ceili(jogador.hp), int(hmax)])
	if "mana" in jogador:   # mana real (runtime de habilidades das classes)
		var mmax: float = maxf(1.0, jogador.stats.get("mana_max", 1.0))
		Arte.globo_mini(_ctl, ed, raio, clampf(jogador.mana / mmax, 0.0, 1.0), 0.0, Tema.cor("mana_escura"), Tema.cor("mana_clara"), _rel)
		_texto_globo(ed, raio, "%d/%d" % [floori(jogador.mana), int(mmax)])
	elif jogador.has_method("recurso_frac"):   # guerreiro: ímpeto
		Arte.globo_mini(_ctl, ed, raio, jogador.recurso_frac(), 0.0, Tema.cor("impeto_escura"), Tema.cor("impeto_clara"), _rel)
		if "impeto" in jogador:
			_texto_globo(ed, raio, "%d/%d" % [floori(jogador.impeto), int(jogador.stats.get("impeto_max", 0.0))])
	else:   # recurso ainda trancado: vidro vazio com cadeado
		Arte.globo_mini(_ctl, ed, raio, 0.0, 0.0, Tema.cor("mana_escura"), Tema.cor("mana_clara"), _rel, 0.0, true)
		Arte.cadeado(_ctl, ed + Vector2(0, -6), 14.0)

func _texto_globo(centro: Vector2, raio: float, s: String) -> void:
	Arte.texto(_ctl, centro + Vector2(-raio, 6), s, 15, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_CENTER, raio * 2.0)

func _desenhar_upgrades() -> void:
	if upgrades == null or upgrades.niveis.is_empty():
		return
	var raio := 14.0
	var x: float = _lay["margem"] - 8 + raio
	var y: float = _lay["lista_y"] - 6 + raio
	var mouse := _ctl.get_local_mouse_position()
	var dica := ""
	var dica_pos := Vector2.ZERO
	for id in upgrades.ordem:
		var nv: int = upgrades.nivel(id)
		if nv <= 0:
			continue
		var ctr := Vector2(x, y)
		var sel := absf(mouse.x - ctr.x) + absf(mouse.y - ctr.y) <= raio
		Arte.buff_losango(_ctl, ctr, raio, Icones.textura(id), nv, sel)
		if sel:
			var chave := "skill.%s.name" if upgrades.defs[id].has("ramo") else "upgrade.%s.name"  # habilidades têm ramo
			dica = "%s x%d" % [Csv.t(chave % id), nv]
			dica_pos = Vector2(ctr.x - raio, ctr.y + raio + 18)
		x += raio * 2.0 + 5.0
	if dica != "":
		var fonte := ThemeDB.fallback_font
		var larg := fonte.get_string_size(dica, HORIZONTAL_ALIGNMENT_LEFT, -1, 15).x + 20.0
		var rd := Rect2(dica_pos, Vector2(larg, 26))
		Arte.placa(_ctl, rd, Tema.cor("pedra"), 2.0, false)
		Arte.texto(_ctl, rd.position + Vector2(0, 19), dica, 15, Tema.cor("texto"), HORIZONTAL_ALIGNMENT_CENTER, larg)

## Conteúdo dos slots: `basicos` (ataque e esquiva) e `ativas` (4 entradas; {} = encaixe vazio). Lê, por duck typing,
## o jogador (`slots_hud` para os ícones do ataque e da esquiva) e o runtime comum de habilidades (`habilidades` com
## slots, defs, recargas, recarga_slot e def_nivel); o recurso é o ímpeto (guerreiro) ou a mana.
func conteudo_slots() -> Dictionary:
	var total := int(_lay["slot_total"])
	var cdmax: float = jogador.stats.get("dodge_cooldown", 1.0)
	var basicos: Array = [
		{"icone": "tiro", "tecla": "hud.key.shoot", "recarga": jogador.recarga_tiro() if jogador.has_method("recarga_tiro") else 0.0, "cor": Tema.cor("destaque")},
		{"icone": "esquiva", "tecla": "hud.key.dodge", "recarga": clampf(jogador.dodge_cd / maxf(cdmax, 0.01), 0.0, 1.0), "cor": Tema.cor("estamina")},
	]
	if jogador.has_method("slots_hud"):   # guerreiro: ícone do golpe
		var sl: Array = jogador.slots_hud()
		basicos[0]["icone"] = sl[0]["icone"]
		basicos[0]["recarga"] = sl[0]["recarga"]
	var ativas: Array = []
	ativas.resize(total)
	ativas.fill({})
	if "habilidades" in jogador and jogador.habilidades != null and jogador.habilidades.has_method("recarga_slot"):
		var hab = jogador.habilidades
		var recurso := -1.0
		if "impeto" in jogador:
			recurso = jogador.impeto
		elif "mana" in jogador:
			recurso = jogador.mana
		for i in mini(total, hab.slots.size()):
			var id: String = hab.slots[i]
			if id == "" or not hab.defs.has(id):
				continue
			var icone: String = hab.defs[id].get("icone", id)
			ativas[i] = {"icone": icone if Icones.textura(icone) != null else "tiro", "tecla": "hud.key.skill%d" % (i + 1),
				"recarga": hab.recarga_slot(i), "segundos": float(hab.recargas.get(id, 0.0)),
				"cor": Tema.cor("destaque") if "impeto" in jogador else Tema.cor("mana_clara"),
				"sem_recurso": recurso >= 0.0 and float(hab.def_nivel(id)["custo"]) > recurso}
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
		Arte.slot_mini(_ctl, rs["basicos"][i], Icones.textura(sl["icone"]), sl["recarga"], Csv.t(sl["tecla"]), sl["cor"])
	for i in rs["ativas"].size():
		var r: Rect2 = rs["ativas"][i]
		var sl: Dictionary = cs["ativas"][i]
		if sl.is_empty():
			Arte.encaixe_mini(_ctl, r, Csv.t("hud.key.skill%d" % (i + 1)))
		else:
			Arte.slot_mini(_ctl, r, Icones.textura(sl["icone"]), sl["recarga"], Csv.t(sl["tecla"]), sl["cor"], sl.get("segundos", -1.0), sl.get("sem_recurso", false))
